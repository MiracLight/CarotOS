#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Sleek Theme: Carot Sleek görünümünün ayarları (üst panel, yan panel, performans).

Ayarlar ~/.config/carotos/sleek.json dosyasındadır; yalnız değiştirilen bölümler yazılır. Üst panelin
zemini xfconf'a, yazı rengi gtk.css'teki tek işaretli bloğa gider. Root gerekmez."""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(BASE_DIR), "ortak"))
import dil  # noqa: E402
import tema  # noqa: E402
from yetkili import temiz_ortam  # noqa: E402

MODERNLESTIR = "/usr/bin/carotos-modernlestir"
KARSILAMA = "/opt/carotos/welcome/carotos-welcome.py"
KOD_EKSIK = 4                                # modernlestir: paketler kurulu değil
BAS, SON = "/* CAROTOS-PANEL-YAZI */", "/* CAROTOS-PANEL-YAZI-SON */"
YAZI_RENGI = {"acik": "#e6e9ef", "koyu": "#14161d"}
PANEL_OLAGAN = {"renk": "#1e2129", "opaklik": 90, "yazi": "acik"}     # Sleek kapalı (skel ile aynı)
PANEL_SLEEK = {"renk": "#001239", "opaklik": 75, "yazi": "acik"}      # Sleek açık (modernlestir ile aynı)
BASLIK = "CarotOS Sleek Theme"
DIL = "en"
METIN = dil.zenginlestir({
    "sleek_alt": {"tr": "Koyu tema, dock ve yan panel. Kapatınca eski görünümün geri gelir.",
                  "en": "Dark theme, dock and side panel. Turning it off restores your previous look."},
    "bekle": {"tr": "Uygulanıyor…", "en": "Applying…"},
    "hata": {"tr": "İşlem tamamlanamadı.", "en": "The operation could not be completed."},
    "eksik": {"tr": "Sleek paketleri kurulu değil. Karşılama'daki Sleek sayfasından kurabilirsin.",
              "en": "Sleek packages are not installed. You can install them from the Sleek page in Welcome."},
    "karsilama": {"tr": "Karşılama'yı aç", "en": "Open Welcome"},
    "performans": {"tr": "Performans", "en": "Performance"},
    "performans_alt": {"tr": "Hafif kipte gölge, bulanıklık ve yuvarlak köşe kapanır; eski bilgisayarlar hızlanır.",
                       "en": "Low effects turns off shadows, blur and rounded corners; faster on old computers."},
    "otomatik": {"tr": "Otomatik", "en": "Automatic"},
    "tam": {"tr": "Tam", "en": "Full effects"},
    "hafif": {"tr": "Hafif", "en": "Low effects"},
    "panel": {"tr": "Üst panel", "en": "Top panel"},
    "yan": {"tr": "Yan panel", "en": "Side panel"},
    "renk": {"tr": "Renk", "en": "Color"},
    "opaklik": {"tr": "Opaklık", "en": "Opacity"},
    "yazi": {"tr": "Yazı rengi", "en": "Text color"},
    "acik": {"tr": "Açık", "en": "Light"},
    "koyu": {"tr": "Koyu", "en": "Dark"},
    "gorunen": {"tr": "Görünen simge sayısı", "en": "Visible icons"},
    "simge": {"tr": "Simge boyu", "en": "Icon size"},
    "uygulamalar": {"tr": "Uygulamalar", "en": "Applications"},
    "ekle": {"tr": "Uygulama ekle", "en": "Add application"},
    "ara": {"tr": "Uygulama ara", "en": "Search applications"},
    "kapat": {"tr": "Kapat", "en": "Close"},
    "cikar": {"tr": "Çıkar", "en": "Remove"},
    "yukari": {"tr": "Yukarı taşı", "en": "Move up"},
    "asagi": {"tr": "Aşağı taşı", "en": "Move down"},
    "varsayilan": {"tr": "Varsayılana dön", "en": "Restore defaults"},
})


def M(anahtar):
    return dil.T(METIN.get(anahtar), DIL, anahtar)


def yukle(ad, *yol):
    yukleyici = SourceFileLoader(ad, os.path.join(BASE_DIR, "..", *yol))
    modul = module_from_spec(spec_from_loader(ad, yukleyici))
    yukleyici.exec_module(modul)
    return modul


yanpanel = yukle("carotos_yanpanel", "yanpanel", "carotos-yanpanel.py")     # doğrulama ve varsayılan liste


# --- Dosyalar ---------------------------------------------------------------
def json_oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.loads(f.read(65536))
    except (OSError, ValueError, RecursionError):
        veri = None
    return veri if isinstance(veri, dict) else {}


def atomik_yaz(yol, metin, izin):
    yol = os.path.realpath(yol)
    os.makedirs(os.path.dirname(yol), mode=0o700, exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".carotos-tmp-", dir=os.path.dirname(yol))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape") as f:
            os.fchmod(f.fileno(), izin)
            f.write(metin)
        os.replace(gecici, yol)
    except BaseException:
        os.unlink(gecici)
        raise


def panel_dogrula(p, varsayilan):
    p = p if isinstance(p, dict) else {}
    renk, opaklik, yazi = p.get("renk"), p.get("opaklik"), p.get("yazi")
    return {"renk": renk if isinstance(renk, str) and re.fullmatch("#[0-9a-fA-F]{6}", renk) else varsayilan["renk"],
            "opaklik": opaklik if type(opaklik) is int and 0 <= opaklik <= 100 else varsayilan["opaklik"],
            "yazi": yazi if yazi in ("acik", "koyu") else varsayilan["yazi"]}


def yazi_blogu(css, yazi):
    """gtk.css metninde yalnız bizim blok değişir; yazi None ise kalkar. Yarım blok: ValueError."""
    if (BAS in css) != (SON in css) or css.find(BAS) > css.find(SON):
        raise ValueError("gtk.css")
    temiz = re.sub(r"\n?" + re.escape(BAS) + ".*?" + re.escape(SON) + r"\n?", "", css, flags=re.S)
    if yazi is None:
        return temiz
    p = ".xfce4-panel.panel"
    blok = [BAS, "%s, %s button, %s label, %s image { color: %s; }" % (p, p, p, p, YAZI_RENGI[yazi]),
            # sağ tık menüleri panele bağlıdır: temanın menü rengi kalsın
            "%s menu { color: @theme_text_color; }" % p,
            "%s menu label, %s menu image { color: inherit; }" % (p, p), SON]
    return temiz + ("" if not temiz or temiz.endswith("\n") else "\n") + "\n" + "\n".join(blok) + "\n"


def yazi_kaydet(yazi):
    yol = os.path.join(GLib.get_user_config_dir(), "gtk-3.0", "gtk.css")
    try:
        with open(yol, encoding="utf-8", errors="surrogateescape") as f:
            eski = f.read()
    except FileNotFoundError:
        eski = ""
    yeni = yazi_blogu(eski, yazi)
    if yeni != eski:
        atomik_yaz(yol, yeni, 0o644)


# --- Komutlar ---------------------------------------------------------------
def calistir(*argv):
    """(çıkış kodu, çıktı); kabuksuz, temiz ortamla."""
    try:
        s = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           env=temiz_ortam(), timeout=10)
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return s.returncode, s.stdout.decode("utf-8", "replace")


def modernlestir(komut):
    # panel, dock gibi oturum parçalarını başlatır: oturumun dili korunsun diye temiz_ortam kullanılmaz
    try:
        return subprocess.run(["/usr/bin/python3", "-I", MODERNLESTIR, komut], stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300).returncode
    except (OSError, subprocess.SubprocessError):
        return 1


def panel_xfconf(*arg):
    return calistir("/usr/bin/xfconf-query", "-c", "xfce4-panel", *arg)


def panel_oku():
    """Üst panelin şu anki düz rengi: {"renk","opaklik"}; düz renk değilse {}."""
    if panel_xfconf("-p", "/panels/panel-1/background-style")[1].strip() != "1":
        return {}
    cikti = panel_xfconf("-p", "/panels/panel-1/background-rgba")[1]
    try:
        d = [min(1.0, max(0.0, float(x))) for x in cikti.split("\n\n", 1)[1].split()]
        return {"renk": "#%02x%02x%02x" % tuple(round(x * 255) for x in d[:3]), "opaklik": round(d[3] * 100)}
    except (IndexError, ValueError, TypeError):
        return {}


def panel_yaz(p):
    argv = []
    for x in [int(p["renk"][i:i + 2], 16) / 255 for i in (1, 3, 5)] + [p["opaklik"] / 100]:
        argv += ["-t", "double", "-s", "%.6f" % x]
    panel_xfconf("-p", "/panels/panel-1/background-rgba", "-n", "-a", *argv)
    panel_xfconf("-p", "/panels/panel-1/background-style", "-n", "-t", "uint", "-s", "1")


def sleek_acik():
    return os.path.isfile(os.path.join(os.path.expanduser("~"), ".local", "state", "carotos", "sleek-yedek.json"))


def uygulama(ad):
    try:
        return Gio.DesktopAppInfo.new(ad)
    except TypeError:                        # kurulu değil
        return None


# --- Pencere ----------------------------------------------------------------
class Pencere(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=BASLIK, icon_name="preferences-desktop-theme")
        global DIL
        ayar = json_oku(os.path.join(GLib.get_user_config_dir(), "carotos-magaza", "ayarlar.json"))
        DIL = ayar["lang"] if ayar.get("lang") in dil.KODLAR else dil.varsayilan_dil()
        tema.uygula("light" if ayar.get("theme") == "light" else "dark", "#5196d6")
        self.set_default_size(640, 720)
        self.veri = json_oku(yanpanel.ayar_yolu())
        self.zamanlayici, self.kapandi = {}, False
        self.kilit = threading.Lock()
        self.kaydir = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.add(tema.sinif(self.kaydir, "arka"))
        self.connect("destroy", self._kapan)
        self._ciz()

    # --- yardımcılar
    def _kapan(self, *_):
        self.kapandi = True
        self._bekleyenleri_yap()

    def _sonra(self, ad, is_):
        """Aynı adlı işler 150 ms içinde birleşir (kaydırıcı her pikselde yazmasın)."""
        if ad in self.zamanlayici:
            GLib.source_remove(self.zamanlayici[ad][0])

        def yap():
            del self.zamanlayici[ad]
            is_()
            return False
        self.zamanlayici[ad] = (GLib.timeout_add(150, yap), is_)

    def _bekleyenleri_yap(self):
        while self.zamanlayici:
            kimlik, is_ = self.zamanlayici.popitem()[1]
            GLib.source_remove(kimlik)
            is_()

    def _kaydet(self):
        try:
            atomik_yaz(yanpanel.ayar_yolu(), json.dumps(self.veri, ensure_ascii=False, indent=1) + "\n", 0o600)
        except OSError:
            self._hata()

    def _hata(self):
        if not self.kapandi:
            self.durum.set_text(M("hata"))

    def _modernlestir(self, komut, bitti=None):
        def son(kod):
            if bitti and not self.kapandi:
                bitti(kod)
            return False

        def calis():
            with self.kilit:                 # komutlar üst üste binmesin
                kod = modernlestir(komut)
            GLib.idle_add(son, kod)
        threading.Thread(target=calis).start()    # pencere kapansa da komut tamamlanır

    def _kart(self, baslik, alt=None, sag=None):
        dis, ic = tema.kart()
        tema.kart_basligi(ic, baslik, alt, sag)
        self.kutu.pack_start(dis, False, False, 0)
        return ic

    def _satir(self, ic, anahtar, w, genis=False):
        s = Gtk.Box(spacing=12)
        s.pack_start(tema.etiket(M(anahtar)), not genis, True, 0)
        s.pack_end(w, genis, True, 0)
        ic.pack_start(s, False, False, 0)

    def _renk(self, ic, deger, degisti):
        rgba = Gdk.RGBA()
        rgba.parse(deger)
        d = Gtk.ColorButton(rgba=rgba, use_alpha=False, title=M("renk"))

        def secildi(d):
            c = d.get_rgba()
            degisti("renk", "#%02x%02x%02x" % tuple(round(x * 255) for x in (c.red, c.green, c.blue)))
        d.connect("color-set", secildi)
        self._satir(ic, "renk", d)

    def _olcek(self, ic, anahtar, alt, ust, deger, degisti):
        o = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, alt, ust, 1)
        o.set_value(deger)
        o.set_value_pos(Gtk.PositionType.RIGHT)
        o.connect("value-changed", lambda o: degisti(anahtar, int(o.get_value())))
        # tekerlek sayfayı kaydırsın, değeri değiştirmesin
        o.connect("scroll-event", lambda o, _e: o.stop_emission_by_name("scroll-event"))
        self._satir(ic, anahtar, o, True)

    # --- içerik
    def _ciz(self):
        eski = self.kaydir.get_child()
        if eski:
            eski.destroy()
        self.kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=18)
        self._sleek_karti()
        self._performans_karti()
        self._panel_karti()
        self._yan_karti()
        self.kaydir.add(self.kutu)
        self.kaydir.show_all()
        self.karsilama.hide()

    def _sleek_karti(self):
        self.anahtar = Gtk.Switch(active=sleek_acik())
        ic = self._kart("Sleek", M("sleek_alt"), self.anahtar)
        self.durum = tema.etiket("", "kart-alt", sar=True)
        self.karsilama = tema.dugme(M("karsilama"), None, lambda: subprocess.Popen([KARSILAMA]))
        self.karsilama.set_halign(Gtk.Align.START)
        ic.pack_start(self.durum, False, False, 0)
        ic.pack_start(self.karsilama, False, False, 0)
        self.anahtar.connect("notify::active", self._sleek_degisti)

    def _sleek_degisti(self, anahtar, _p):
        self._bekleyenleri_yap()
        self.kutu.set_sensitive(False)
        self.durum.set_text(M("bekle"))

        def bitti(kod):
            self._ciz()
            if kod:
                self.durum.set_text(M("eksik" if kod == KOD_EKSIK else "hata"))
                self.karsilama.set_visible(kod == KOD_EKSIK and os.path.isfile(KARSILAMA))
        self._modernlestir("uygula" if anahtar.get_active() else "geri-al", bitti)

    def _performans_karti(self):
        ic = self._kart(M("performans"), M("performans_alt"))
        kipler = ("otomatik", "tam", "hafif")
        secili = self.veri.get("performans")

        def degisti(kip):
            self.veri["performans"] = kip
            self._kaydet()
            self._modernlestir("yeniden")
        ic.pack_start(tema.secim_grubu([(k, M(k)) for k in kipler],
                                       secili if secili in kipler else "otomatik", degisti)[0], False, False, 0)

    def _panel_karti(self):
        varsayilan = PANEL_SLEEK if sleek_acik() else PANEL_OLAGAN
        kayitli = self.veri.get("panel")
        p = panel_dogrula(dict(kayitli if isinstance(kayitli, dict) else {}, **panel_oku()), varsayilan)
        ic = self._kart(M("panel"), None, tema.dugme(M("varsayilan"), "kucuk", self._panel_sifirla, varsayilan))

        def yaz():
            panel_yaz(p)
            self._kaydet()

        def zemin(anahtar, deger):
            p[anahtar] = deger
            self.veri["panel"] = p
            self._sonra("panel", yaz)

        def yazi(deger):
            p["yazi"] = deger
            self.veri["panel"] = p
            self._kaydet()
            self._yazi(deger)
        self._renk(ic, p["renk"], zemin)
        self._olcek(ic, "opaklik", 0, 100, p["opaklik"], zemin)
        self._satir(ic, "yazi", tema.secim_grubu([(k, M(k)) for k in YAZI_RENGI], p["yazi"], yazi)[0])

    def _yazi(self, yazi):
        try:
            yazi_kaydet(yazi)
        except (OSError, ValueError):
            self._hata()
            return
        # gtk.css yalnız açılışta okunur: çalışan panel yeniden başlar
        if calistir("/usr/bin/pgrep", "-u", str(os.getuid()), "-x", "xfce4-panel")[0] == 0:
            calistir("/usr/bin/xfce4-panel", "-r")

    def _panel_sifirla(self, varsayilan):
        self._bekleyenleri_yap()
        self.veri.pop("panel", None)
        self._kaydet()
        panel_yaz(varsayilan)
        self._ciz()
        self._yazi(None)

    def _yan_karti(self):
        y = yanpanel.yan_dogrula(self.veri.get("yan"))
        ic = self._kart(M("yan"), None, tema.dugme(M("varsayilan"), "kucuk", self._yan_sifirla))

        def degisti(anahtar, deger):
            y[anahtar] = deger
            self.veri["yan"] = y
            self._sonra("yan", self._kaydet)
        self._renk(ic, y["renk"], degisti)
        for anahtar, alt, ust in (("opaklik", 20, 100), ("gorunen", 3, 9), ("simge", 24, 64)):
            self._olcek(ic, anahtar, alt, ust, y[anahtar], degisti)
        adlar = [a for a in y["uygulamalar"] or yanpanel.girdileri_bul() if uygulama(a)]
        liste = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        def yenile():
            for w in liste.get_children():
                w.destroy()
            for i, ad in enumerate(adlar):
                s = self._uygulama_satiri(uygulama(ad))
                for simge, ipucu, is_, etkin in (
                        ("list-remove-symbolic", "cikar", lambda i=i: adlar.pop(i), len(adlar) > 1),
                        ("go-down-symbolic", "asagi", lambda i=i: adlar.insert(i + 1, adlar.pop(i)), i + 1 < len(adlar)),
                        ("go-up-symbolic", "yukari", lambda i=i: adlar.insert(i - 1, adlar.pop(i)), i > 0)):
                    d = Gtk.Button(image=Gtk.Image.new_from_icon_name(simge, Gtk.IconSize.BUTTON),
                                   tooltip_text=M(ipucu), sensitive=etkin)
                    d.connect("clicked", lambda _d, is_=is_: (is_(), liste_degisti()))
                    s.pack_end(tema.sinif(d, "duz kucuk"), False, False, 0)
                liste.pack_start(s, False, False, 0)
            liste.show_all()

        def liste_degisti():
            degisti("uygulamalar", list(adlar))
            yenile()

        def ekle(ad):
            adlar.append(ad)
            liste_degisti()
        bas = Gtk.Box(spacing=12)
        bas.pack_start(tema.etiket(M("uygulamalar"), "kart-baslik"), True, True, 0)
        bas.pack_end(tema.dugme(M("ekle"), "kucuk", lambda: self._ekle_penceresi(adlar, ekle)), False, False, 0)
        ic.pack_start(bas, False, False, 0)
        ic.pack_start(liste, False, False, 0)
        yenile()

    def _yan_sifirla(self):
        self._bekleyenleri_yap()
        self.veri.pop("yan", None)
        self._kaydet()
        self._ciz()

    @staticmethod
    def _uygulama_satiri(bilgi):
        s = Gtk.Box(spacing=10)
        simge = Gtk.Image.new_from_gicon(bilgi.get_icon() or Gio.ThemedIcon.new("application-x-executable"),
                                         Gtk.IconSize.LARGE_TOOLBAR)
        simge.set_pixel_size(24)
        s.pack_start(simge, False, False, 0)
        s.pack_start(tema.etiket(bilgi.get_name(), sar=True, genislik=40), True, True, 0)
        return s

    def _ekle_penceresi(self, adlar, ekle):
        d = Gtk.Dialog(title=M("ekle"), transient_for=self, modal=True)
        d.add_button(M("kapat"), Gtk.ResponseType.CLOSE)
        d.set_default_size(420, 480)
        ara = Gtk.SearchEntry(placeholder_text=M("ara"), margin=10)
        liste = tema.sinif(Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE), "duz-liste")
        for b in sorted(Gio.AppInfo.get_all(), key=lambda b: b.get_name().casefold()):
            ad = b.get_id() or ""
            if b.should_show() and ad not in adlar and yanpanel.yan_dogrula({"uygulamalar": [ad]})["uygulamalar"]:
                satir = Gtk.ListBoxRow(child=self._uygulama_satiri(b))
                satir.ad, satir.metin = ad, (b.get_name() + " " + ad).casefold()
                liste.add(satir)
        liste.set_filter_func(lambda s: ara.get_text().casefold() in s.metin)
        ara.connect("search-changed", lambda *_: liste.invalidate_filter())
        liste.connect("row-activated", lambda _l, s: (ekle(s.ad), s.destroy()))
        kaydir = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        kaydir.add(liste)
        d.get_content_area().pack_start(ara, False, False, 0)
        d.get_content_area().pack_start(kaydir, True, True, 0)
        d.show_all()
        d.run()
        d.destroy()


class SleekAyar(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.carotos.SleekAyar")

    def do_activate(self):
        pencere = self.get_active_window() or Pencere(self)
        pencere.show()
        pencere.present()


if __name__ == "__main__":
    sys.exit(SleekAyar().run(sys.argv))
