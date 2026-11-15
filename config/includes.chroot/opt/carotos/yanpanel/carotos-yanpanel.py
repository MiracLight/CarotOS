#!/usr/bin/python3 -I
# -*- coding: utf-8 -*-
"""CarotOS Yan Panel: sol kenarda gizli duran, CarotOS uygulamalarini 5'erli gosteren kaydirmali panel.

  - Imlec ekranin SOL kenarina gidince panel cikar, imlec cekilince kendiliginden gizlenir
    (tam ekran uygulamalarin ustunde de cikar; bu yuzden "tam ekranda iceri girmiyor" sorunu yoktur).
  - Ayni anda GORUNEN (5) simge; fare tekeri ya da ustteki/alttaki oklarla kaydirilir.
  - Yalniz CarotOS uygulamalari: /usr/share/applications altindaki carotos-*.desktop dosyalari
    (NoDisplay=true olanlar haric), belirli bir sirayla; kalanlar alfabetik.
  - Simgeye tiklayinca uygulama baslar (Gio.DesktopAppInfo), panel gizlenir.

Disaridan girdi almaz, ag kullanmaz, kabuk calistirmaz. Tek dosya, yalnizca PyGObject (GTK3).
Tek ornek: ikinci baslatma sessizce cikar.

Kullanim:  carotos-yanpanel.py            paneli baslatir
           carotos-yanpanel.py --liste    gorunecek uygulamalari yazar (GTK acmaz)
           (--dizin <klasor>, --dene: yalniz testler icin)
"""
import os
import re
import sys

sys.dont_write_bytecode = True

UYGULAMALAR = "/usr/share/applications"
GORUNEN = 5                 # ayni anda gorunen simge
SIMGE_BOYU = 40
OGE_YUKSEKLIGI = 56
KENAR_GENISLIGI = 6         # imlecin yakalandigi gorunmez serit
GIZLEME_GECIKMESI_MS = 700  # imlec panelden bu kadar suredir uzaksa gizlenir
YAKLASMA_PAYI = 28          # panelin cevresinde imlecin "hala yakin" sayildigi alan (piksel)
ANIMASYON_MS = 170          # kayarak girme/cikma suresi
KONTROL_MS = 80             # imlec konumu denetim araligi
# mantik: baslangic/yonetim -> koruma ve denetim -> ogrenme -> yardimci araclar
SIRA = (
    "carotos-welcome.desktop", "carotos-magaza.desktop",
    "carotos-security-panel.desktop", "carotos-health.desktop", "carotos-usb-check.desktop",
    "carotos-kurtarma.desktop",
    "carotos-carotene.desktop", "carotos-carotpot.desktop",
    "carotos-poligon-ogrenci.desktop", "carotos-poligon-ogretmen.desktop",
    "carotos-former.desktop", "carotos-gsd.desktop", "carotos-filenor.desktop",
)
_AD = re.compile(r"carotos-[A-Za-z0-9._-]+\.desktop\Z")


def girdileri_bul(dizin=UYGULAMALAR):
    """Panelde gosterilecek .desktop dosya adlari, gosterim sirasiyla."""
    try:
        adlar = [a for a in os.listdir(dizin) if _AD.match(a)]
    except OSError:
        return []
    gorunur = []
    for ad in adlar:
        try:
            with open(os.path.join(dizin, ad), encoding="utf-8", errors="replace") as f:
                metin = f.read(65536)
        except OSError:
            continue
        if re.search(r"^NoDisplay=true", metin, re.M | re.I) or re.search(r"^Hidden=true", metin, re.M | re.I):
            continue
        gorunur.append(ad)
    sirali = [a for a in SIRA if a in gorunur]
    sirali += sorted(a for a in gorunur if a not in SIRA)
    return sirali


CSS = """
#yanpanel { background-color: rgba(0, 18, 57, 0.88); border: 1px solid rgba(81, 150, 214, 0.40);
            border-radius: 18px; }
#yanpanel button { background: transparent; background-image: none; border: none; box-shadow: none;
                   border-radius: 12px; padding: 4px; }
#yanpanel button:hover { background-color: rgba(81, 150, 214, 0.30); }
#yanpanel button.ok { min-height: 30px; padding: 0; margin: 3px 0; font-size: 16px; font-weight: bold;
                      color: #ffffff; background-color: rgba(81, 150, 214, 0.40); border-radius: 10px; }
#yanpanel button.ok:hover { background-color: rgba(81, 150, 214, 0.70); }
#yanpanel button.ok:disabled { color: rgba(255, 255, 255, 0.22); background-color: rgba(81, 150, 214, 0.10); }
#yanserit { background-color: rgba(0, 18, 57, 0.01); }
"""


def main(argv):
    dizin = UYGULAMALAR
    if "--dizin" in argv[1:]:                # yalniz testler icin: baska bir applications klasoru
        i = argv.index("--dizin")
        dizin = argv[i + 1] if i + 1 < len(argv) else dizin
    girdiler = girdileri_bul(dizin)
    if "--liste" in argv[1:]:
        print("\n".join(girdiler))
        return 0
    if not girdiler:
        return 0

    import fcntl
    kilit_yolu = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", "carotos-yanpanel-%d.lock" % os.getuid())
    kilit = open(kilit_yolu, "w")
    try:
        fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0                                            # zaten calisiyor

    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, Gio, GLib, Gtk

    ekran = Gdk.Screen.get_default()
    saglayici = Gtk.CssProvider()
    saglayici.load_from_data(CSS.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_screen(ekran, saglayici, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    bilgiler = []
    for ad in girdiler:
        bilgi = Gio.DesktopAppInfo.new(ad)
        if bilgi is not None and bilgi.should_show():
            bilgiler.append(bilgi)
    if not bilgiler:
        return 0

    def calisma_alani():
        ekr = Gdk.Display.get_default()
        mon = ekr.get_primary_monitor() or ekr.get_monitor(0)
        return mon.get_workarea()

    class Panel:
        def __init__(self):
            self.gorunur = False
            self.anim = None
            self.denetim = None
            self.uzak_ms = 0
            self.gorunen = min(GORUNEN, len(bilgiler))
            self.x_gizli = -400
            self.x_acik = 6
            self.y = 0
            self.genislik = 80
            self.yukseklik = 300
            # imleci yakalayan gorunmez serit (override-redirect: tam ekranin ustunde de calisir)
            self.serit = Gtk.Window(type=Gtk.WindowType.POPUP)
            self.serit.set_name("yanserit")
            self.serit.set_app_paintable(True)
            self._rgba(self.serit)
            self.serit.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
            self.serit.connect("enter-notify-event", self.goster)
            self.serit.connect("draw", lambda w, cr: True)
            # panel
            self.pencere = Gtk.Window(type=Gtk.WindowType.POPUP)
            self.pencere.set_name("yanpanel")
            self.pencere.set_app_paintable(True)
            self._rgba(self.pencere)
            self.pencere.set_keep_above(True)
            kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            kutu.set_border_width(8)
            self.yukari = self._ok("\u25b2", -1)
            self.asagi = self._ok("\u25bc", 1)
            liste = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            for bilgi in bilgiler:
                liste.pack_start(self._oge(bilgi), False, False, 0)
            self.kaydirici = Gtk.ScrolledWindow()
            self.kaydirici.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
            self.kaydirici.set_kinetic_scrolling(False)
            self.kaydirici.set_size_request(OGE_YUKSEKLIGI + 8, OGE_YUKSEKLIGI * self.gorunen)
            self.kaydirici.add(liste)
            self.kaydirici.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            self.kaydirici.connect("scroll-event", self.tekerlek)
            self.ayar = self.kaydirici.get_vadjustment()
            self.ayar.connect("value-changed", lambda *_: self.oklari_guncelle())
            kutu.pack_start(self.yukari, False, False, 0)
            kutu.pack_start(self.kaydirici, False, False, 0)
            kutu.pack_start(self.asagi, False, False, 0)
            self.pencere.add(kutu)
            kutu.show_all()
            self.olc()

        @staticmethod
        def _rgba(pencere):
            gorsel = pencere.get_screen().get_rgba_visual()
            if gorsel is not None:
                pencere.set_visual(gorsel)

        def _ok(self, metin, yon):
            d = Gtk.Button(label=metin)
            d.get_style_context().add_class("ok")
            d.set_relief(Gtk.ReliefStyle.NONE)
            d.set_can_focus(False)
            d.connect("clicked", lambda *_: self.kaydir(yon))
            return d

        def _oge(self, bilgi):
            d = Gtk.Button()
            d.set_relief(Gtk.ReliefStyle.NONE)
            d.set_can_focus(False)
            d.set_size_request(OGE_YUKSEKLIGI, OGE_YUKSEKLIGI)
            resim = Gtk.Image.new_from_gicon(bilgi.get_icon() or Gio.ThemedIcon.new("application-x-executable"),
                                             Gtk.IconSize.DIALOG)
            resim.set_pixel_size(SIMGE_BOYU)
            d.add(resim)
            d.set_tooltip_text(bilgi.get_name())
            d.connect("clicked", lambda *_: self.baslat(bilgi))
            return d

        def olc(self):
            """Boyut ve konumlar (calisma alani degisebilir: her gosterimde yeniden hesaplanir)."""
            alan = calisma_alani()
            self.genislik = self.pencere.get_preferred_width()[1]
            self.yukseklik = self.pencere.get_preferred_height()[1]
            self.serit.resize(KENAR_GENISLIGI, max(1, alan.height))
            self.serit.move(alan.x, alan.y)
            self.pencere.resize(self.genislik, self.yukseklik)
            self.x_acik = alan.x + 6
            self.x_gizli = alan.x - self.genislik - 12
            self.y = alan.y + max(0, (alan.height - self.yukseklik) // 2)

        # --- gorunurluk: kayarak girer/cikar; gizleme imlec konumuna bakar (GTK enter/leave olaylarina degil) ---
        def kay(self, hedef_x, bitince=None):
            if self.anim is not None:
                GLib.source_remove(self.anim)
            basla_x = self.pencere.get_position()[0]
            t0 = GLib.get_monotonic_time()

            def adim():
                oran = min(1.0, (GLib.get_monotonic_time() - t0) / 1000.0 / ANIMASYON_MS)
                yumusak = 1 - (1 - oran) ** 3                     # ease-out
                self.pencere.move(int(basla_x + (hedef_x - basla_x) * yumusak), self.y)
                if oran >= 1.0:
                    self.anim = None
                    if bitince:
                        bitince()
                    return False
                return True
            self.anim = GLib.timeout_add(8, adim)

        def goster(self, *_):
            self.uzak_ms = 0
            if self.gorunur:
                return
            self.olc()
            self.gorunur = True
            self.pencere.move(self.x_gizli, self.y)
            self.pencere.show()
            self.oklari_guncelle()
            self.kay(self.x_acik)
            if self.denetim is None:
                self.denetim = GLib.timeout_add(KONTROL_MS, self.imlec_denetle)

        def gizle(self):
            if not self.gorunur:
                return

            def bitti():
                self.pencere.hide()
            self.gorunur = False
            self.kay(self.x_gizli, bitti)

        def imlec_yakin_mi(self):
            _, x, y = Gdk.Display.get_default().get_default_seat().get_pointer().get_position()
            alan = calisma_alani()
            sol = alan.x
            sag = self.x_acik + self.genislik + YAKLASMA_PAYI
            ust = self.y - YAKLASMA_PAYI
            alt = self.y + self.yukseklik + YAKLASMA_PAYI
            return sol <= x <= sag and ust <= y <= alt

        def imlec_denetle(self):
            if not self.gorunur:
                self.denetim = None
                return False
            if self.imlec_yakin_mi():
                self.uzak_ms = 0
            else:
                self.uzak_ms += KONTROL_MS
                if self.uzak_ms >= GIZLEME_GECIKMESI_MS:
                    self.denetim = None
                    self.gizle()
                    return False
            return True

        # --- kaydirma ---
        def kaydir(self, yon):
            self.uzak_ms = 0
            hedef = self.ayar.get_value() + yon * OGE_YUKSEKLIGI
            ust = max(0.0, self.ayar.get_upper() - self.ayar.get_page_size())
            self.ayar.set_value(max(0.0, min(ust, hedef)))

        def tekerlek(self, _w, olay):
            if olay.direction == Gdk.ScrollDirection.UP:
                self.kaydir(-1)
            elif olay.direction == Gdk.ScrollDirection.DOWN:
                self.kaydir(1)
            elif olay.direction == Gdk.ScrollDirection.SMOOTH:
                self.kaydir(1 if olay.delta_y > 0 else -1 if olay.delta_y < 0 else 0)
            return True

        def oklari_guncelle(self):
            ust = max(0.0, self.ayar.get_upper() - self.ayar.get_page_size())
            self.yukari.set_sensitive(self.ayar.get_value() > 0.5)
            self.asagi.set_sensitive(self.ayar.get_value() < ust - 0.5)

        def baslat(self, bilgi):
            try:
                bilgi.launch([], Gdk.Display.get_default().get_app_launch_context())
            except GLib.Error:
                pass
            self.gizle()

    panel = Panel()
    panel.serit.show_all()
    if "--dene" in argv[1:]:                 # yalniz testler icin: ac, kaydir, birkac kare ciz, cik
        GLib.timeout_add(100, lambda: (panel.goster(), False)[1])
        GLib.timeout_add(500, lambda: (panel.kaydir(1), False)[1])
        GLib.timeout_add(1000, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
