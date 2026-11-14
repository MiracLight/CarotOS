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
           (--dizin <klasor>: yalniz testler icin baska bir applications klasoru)
"""
import os
import re
import sys

sys.dont_write_bytecode = True

UYGULAMALAR = "/usr/share/applications"
GORUNEN = 5                 # ayni anda gorunen simge
SIMGE_BOYU = 40
OGE_YUKSEKLIGI = 56
KENAR_GENISLIGI = 3         # imlecin yakalandigi gorunmez serit
GIZLEME_GECIKMESI_MS = 350
# mantik: baslangic/yonetim -> koruma ve denetim -> ogrenme -> yardimci araclar
SIRA = (
    "carotos-welcome.desktop", "carotos-magaza.desktop",
    "carotos-security-panel.desktop", "carotos-health.desktop", "carotos-usb-check.desktop",
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
#yanpanel button.ok { min-height: 22px; padding: 0; color: #a9d1f5; }
#yanpanel button.ok:disabled { color: rgba(169, 209, 245, 0.25); }
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
            self.zamanlayici = None
            self.gorunen = min(GORUNEN, len(bilgiler))
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
            self.pencere.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
            self.pencere.connect("enter-notify-event", self.imlec_girdi)
            self.pencere.connect("leave-notify-event", self.imlec_cikti)
            kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            kutu.set_border_width(8)
            self.yukari = self._ok("▲", -1)
            self.asagi = self._ok("▼", 1)
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
            self.konumla()

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

        def konumla(self):
            alan = calisma_alani()
            self.serit.resize(KENAR_GENISLIGI, max(1, alan.height))
            self.serit.move(alan.x, alan.y)
            self.pencere.resize(1, 1)
            ust = 2 * 22 + 2 * 2 + 16 + OGE_YUKSEKLIGI * self.gorunen
            self.pencere.move(alan.x + 6, alan.y + max(0, (alan.height - ust) // 2))

        # --- gorunurluk ---
        def goster(self, *_):
            self.konumla()
            self.iptal()
            self.pencere.show_all()
            self.oklari_guncelle()

        def gizle(self, *_):
            self.zamanlayici = None
            self.pencere.hide()
            return False

        def iptal(self):
            if self.zamanlayici is not None:
                GLib.source_remove(self.zamanlayici)
                self.zamanlayici = None

        def imlec_girdi(self, *_):
            self.iptal()

        def imlec_cikti(self, *_):
            self.iptal()
            self.zamanlayici = GLib.timeout_add(GIZLEME_GECIKMESI_MS, self.gizle)

        # --- kaydirma ---
        def kaydir(self, yon):
            self.iptal()
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
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
