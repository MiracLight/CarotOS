#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Mağaza 2 — CarotOS için yerel uygulama mağazası.

Küratörlü bir katalog (katalog.json) üzerinden apt paketlerini kurar, kaldırır
ve günceller. CarotOS'un ortak grafit temasını (ortak/tema.py) kullanır; her
uygulamanın kendi vurgu rengi vardır (mağazanınki pembe). İki dillidir (tr/en)
ve koyu/açık görünümü destekler.

Bölümler:
  * Anasayfa      — öne çıkanlar ve kategori kartları
  * Kurulu        — kataloğdan kurulu uygulamalar
  * Güncellemeler — güncellenebilir paketler; depoyu yenileme ve toplu güncelleme
  * Kategoriler   — her kategori ayrı bir liste
  * Ayrıntı       — bir uygulamanın tam açıklaması, boyutu, lisansı, sitesi

Yetki gereken işlemler (kur/kaldır/güncelle/yenile) `pkexec apt-get` ile
yapılır; pkexec yoksa elle çalıştırılacak komut gösterilir.
"""
import base64
import json
import locale
import os
import shutil
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORTAK = os.path.join(os.path.dirname(BASE_DIR), "ortak")
for _y in (ORTAK, BASE_DIR):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import tema  # noqa: E402

APP_VERSION = "2.0"
KATALOG_YOLU = os.path.join(BASE_DIR, "katalog.json")
IKON_YOLU = os.path.join(BASE_DIR, "ikonlar.json")
GITHUB_URL = "https://github.com/MiracLight/CarotOS"
WEB_URL = "https://carotos.org"
VURGU = "magaza"            # ortak/tema.py'deki pembe vurgu

LOGO_B64 = (
    "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"
)


# --- Dil --------------------------------------------------------------------
def _sistem_dili():
    d = os.environ.get("CAROTOS_DIL")
    if d in ("tr", "en"):
        return d
    for anahtar in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        deger = os.environ.get(anahtar, "")
        if deger and deger not in ("C", "POSIX"):
            return "tr" if deger.lower().startswith("tr") else "en"
    try:
        kod = (locale.getdefaultlocale()[0] or "")
    except Exception:  # noqa: BLE001
        kod = ""
    return "tr" if kod.lower().startswith("tr") else "en"


def _ayar_dosyasi():
    return os.path.join(GLib.get_user_config_dir(), "carotos-magaza", "ayarlar.json")


def ayarlari_oku():
    veri = {"lang": _sistem_dili(), "theme": "dark"}
    try:
        with open(_ayar_dosyasi(), encoding="utf-8") as f:
            k = json.load(f)
        if k.get("lang") in ("tr", "en"):
            veri["lang"] = k["lang"]
        if k.get("theme") in ("dark", "light"):
            veri["theme"] = k["theme"]
    except (OSError, ValueError):
        pass
    return veri


def ayarlari_kaydet(veri):
    try:
        os.makedirs(os.path.dirname(_ayar_dosyasi()), exist_ok=True)
        with open(_ayar_dosyasi(), "w", encoding="utf-8") as f:
            json.dump(veri, f)
    except OSError:
        pass


DIL = _sistem_dili()

METIN = {
    "baslik": {"tr": "Mağaza", "en": "Store"},
    "marka_alt": {"tr": "Uygulama mağazası · {s}", "en": "App store · {s}"},
    "ara": {"tr": "Uygulama ara…", "en": "Search apps…"},
    "yenile": {"tr": "Depoyu yenile", "en": "Refresh"},
    "gorunum_koyu": {"tr": "Koyu", "en": "Dark"},
    "gorunum_acik": {"tr": "Açık", "en": "Light"},
    "bolum_kesfet": {"tr": "Keşfet", "en": "Discover"},
    "bolum_kategoriler": {"tr": "Kategoriler", "en": "Categories"},
    "anasayfa": {"tr": "Anasayfa", "en": "Home"},
    "anasayfa_alt": {"tr": "Öne çıkan uygulamalar ve kategoriler",
                     "en": "Featured apps and categories"},
    "kurulu": {"tr": "Kurulu", "en": "Installed"},
    "kurulu_alt": {"tr": "Bu bilgisayarda kurulu, kataloğdaki uygulamalar",
                   "en": "Apps from the catalogue installed on this computer"},
    "guncelleme": {"tr": "Güncellemeler", "en": "Updates"},
    "guncelleme_alt": {"tr": "Güncellenebilir paketler", "en": "Upgradable packages"},
    "one_cikanlar": {"tr": "Öne çıkanlar", "en": "Featured"},
    "kategoriye_gozat": {"tr": "Kategorilere göz atın", "en": "Browse categories"},
    "uyg_sayisi": {"tr": "{n} uygulama", "en": "{n} apps"},
    "kur": {"tr": "Kur", "en": "Install"},
    "kaldir": {"tr": "Kaldır", "en": "Remove"},
    "ac": {"tr": "Aç", "en": "Open"},
    "kurulu_rozet": {"tr": "Kurulu", "en": "Installed"},
    "kuruluyor": {"tr": "Kuruluyor…", "en": "Installing…"},
    "kaldiriliyor": {"tr": "Kaldırılıyor…", "en": "Removing…"},
    "guncelleniyor": {"tr": "Güncelleniyor…", "en": "Updating…"},
    "yenileniyor": {"tr": "Depo yenileniyor…", "en": "Refreshing repositories…"},
    "geri": {"tr": "← Geri", "en": "← Back"},
    "siteyi_ac": {"tr": "İnternet sitesi", "en": "Website"},
    "bilgi_kategori": {"tr": "Kategori", "en": "Category"},
    "bilgi_boyut": {"tr": "Boyut", "en": "Size"},
    "bilgi_lisans": {"tr": "Lisans", "en": "Licence"},
    "bilgi_paket": {"tr": "Paket", "en": "Package"},
    "aciklama_baslik": {"tr": "Açıklama", "en": "Description"},
    "sonuc_yok": {"tr": "Aramayla eşleşen uygulama bulunamadı.",
                  "en": "No apps match your search."},
    "arama_basligi": {"tr": "“{s}” için sonuçlar", "en": "Results for “{s}”"},
    "arama_alt": {"tr": "Tüm kataloğda arama", "en": "Searching the whole catalogue"},
    "kurulu_bos_baslik": {"tr": "Kurulu uygulama yok", "en": "No apps installed"},
    "kurulu_bos": {"tr": "Kataloğdan kurduğunuz uygulamalar burada görünür.",
                   "en": "Apps you install from the catalogue appear here."},
    "guncel_baslik": {"tr": "Her şey güncel", "en": "Everything is up to date"},
    "guncel_alt": {"tr": "Güncellenecek paket yok. Son denetim: {z}",
                   "en": "No packages to update. Last checked: {z}"},
    "guncelleme_var": {"tr": "{n} paket güncellenebilir", "en": "{n} packages can be updated"},
    "tumunu_guncelle": {"tr": "Tümünü güncelle", "en": "Update all"},
    "katalog_guncel": {"tr": "Kataloğdaki uygulamalardan güncellenebilenler",
                       "en": "Updatable apps from the catalogue"},
    "diger_paketler": {"tr": "Ayrıca {n} sistem paketi daha güncellenebilir.",
                       "en": "Also {n} more system packages can be updated."},
    "denetleniyor": {"tr": "Güncellemeler denetleniyor…", "en": "Checking for updates…"},
    "simdi": {"tr": "az önce", "en": "just now"},
    "kapat": {"tr": "Kapat", "en": "Close"},
    "iptal": {"tr": "İptal", "en": "Cancel"},
    "tamamlandi": {"tr": "Tamamlandı.", "en": "Done."},
    "hata_olustu": {"tr": "İşlem başarısız oldu.", "en": "The operation failed."},
    "pkexec_yok_baslik": {"tr": "Yetki aracı bulunamadı", "en": "Privilege tool not found"},
    "pkexec_yok": {
        "tr": "pkexec bulunamadı, bu yüzden işlem grafik arayüzden yapılamıyor. "
              "Aşağıdaki komutu bir terminalde çalıştırın:",
        "en": "pkexec was not found, so this can't run from the GUI. Run this command "
              "in a terminal:"},
    "hakkinda": {"tr": "Hakkında", "en": "About"},
    "hakkinda_metin": {
        "tr": "CarotOS için geliştirildi. Küratörlü bir katalog üzerinden Debian "
              "paketlerini kurar ve günceller.",
        "en": "Made for CarotOS. Installs and updates Debian packages through a "
              "curated catalogue."},
    "hakkinda_github": {"tr": "GitHub", "en": "GitHub"},
    "hakkinda_web": {"tr": "İnternet sitesi", "en": "Website"},
    "hakkinda_mesaj": {"tr": "Yapılmış her şey insanlığa aittir.",
                       "en": "Everything created belongs to humanity."},
}

# Kategori -> ortak temadaki simge adı ve vurgu rengi (kart ikon kutusu için)
KAT_IKON = {
    "grafik": ("elmas", "pembe"), "ofis": ("rapor", "mavi"),
    "internet": ("ag", "camgobegi"), "medya": ("pano", "turuncu"),
    "gelistirme": ("liste", "vurgu"), "egitim": ("bilgi", "limon"),
    "oyun": ("hedef", "sari"), "araclar": ("arti", "yesil"),
    "sistem": ("ayar", "soluk"), "guvenlik": ("kalkan", "kirmizi"),
}
GENEL_IKON = {
    "grafik": "applications-graphics", "guvenlik": "security-high",
    "ofis": "applications-office", "internet": "applications-internet",
    "medya": "applications-multimedia", "gelistirme": "applications-development",
    "sistem": "applications-utilities", "egitim": "applications-science",
    "oyun": "applications-games", "araclar": "applications-accessories",
}


def M(anahtar, **b):
    s = METIN[anahtar][DIL]
    return s.format(**b) if b else s


def metin(sozluk):
    if isinstance(sozluk, dict):
        return sozluk.get(DIL) or sozluk.get("tr") or sozluk.get("en") or ""
    return sozluk or ""


# --- Uygulama simgeleri (gömülü / AppStream / tema / Papirus / yedek) -------
def _gomulu_ikonlar():
    try:
        with open(IKON_YOLU, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


GOMULU_IKON = _gomulu_ikonlar()
_ZENGIN_TEMA = None


def _zengin_tema():
    global _ZENGIN_TEMA
    if _ZENGIN_TEMA is None:
        _ZENGIN_TEMA = False
        for ad in ("Papirus-Dark", "Papirus", "Papirus-Light"):
            try:
                t = Gtk.IconTheme.new()
                t.set_custom_theme(ad)
                if t.has_icon("firefox") or t.has_icon("gimp") or t.has_icon("vlc"):
                    _ZENGIN_TEMA = t
                    break
            except Exception:  # noqa: BLE001
                continue
    return _ZENGIN_TEMA or None


def _ad_adaylari(uygulama):
    ad = uygulama.get("ikon")
    adaylar = []
    if ad:
        adaylar.append(ad)
        if ad.lower() != ad:
            adaylar.append(ad.lower())
    pak = uygulama.get("paket")
    if pak and pak not in adaylar:
        adaylar.append(pak)
        kok = pak.split("-")[0]
        if kok not in adaylar:
            adaylar.append(kok)
    return adaylar


def _gomulu_resim(paket, px):
    b64 = GOMULU_IKON.get(paket)
    if not b64:
        return None
    try:
        yk = GdkPixbuf.PixbufLoader.new_with_type("png")
        yk.set_size(px, px)
        yk.write(base64.b64decode(b64))
        yk.close()
        return Gtk.Image.new_from_pixbuf(yk.get_pixbuf())
    except Exception:  # noqa: BLE001
        return None


def uygulama_ikonu(uygulama, px, as_yol=None):
    img = _gomulu_resim(uygulama.get("paket"), px)
    if img is not None:
        return img
    if as_yol:
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(as_yol, px, px)
            return Gtk.Image.new_from_pixbuf(pb)
        except Exception:  # noqa: BLE001
            pass
    adaylar = _ad_adaylari(uygulama)
    try:
        varsayilan = Gtk.IconTheme.get_default()
    except Exception:  # noqa: BLE001
        varsayilan = None
    for ad in adaylar:
        try:
            if varsayilan and varsayilan.has_icon(ad):
                i = Gtk.Image.new_from_icon_name(ad, Gtk.IconSize.DND)
                i.set_pixel_size(px)
                return i
        except Exception:  # noqa: BLE001
            continue
    zengin = _zengin_tema()
    if zengin:
        for ad in adaylar:
            try:
                if zengin.has_icon(ad):
                    pb = zengin.load_icon(ad, px, 0)
                    if pb is not None:
                        return Gtk.Image.new_from_pixbuf(pb)
            except Exception:  # noqa: BLE001
                continue
    i = Gtk.Image.new_from_icon_name(
        GENEL_IKON.get(uygulama.get("kategori"), "package-x-generic"), Gtk.IconSize.DND)
    i.set_pixel_size(px)
    return i


def appstream_ikon_haritasi():
    harita = {}
    try:
        gi.require_version("AppStream", "1.0")
        from gi.repository import AppStream as As  # noqa: N814
    except Exception:  # noqa: BLE001
        return harita
    try:
        havuz = As.Pool()
        havuz.load()
        try:
            dizi = list(havuz.get_components())
        except TypeError:
            dizi = havuz.get_components().as_array()
        for b in dizi:
            try:
                paketler = list(b.get_pkgnames() or [])
            except Exception:  # noqa: BLE001
                paketler = []
            if not paketler:
                continue
            try:
                ikon = (b.get_icon_by_size(64, 64) or b.get_icon_by_size(48, 48))
                if ikon is None:
                    liste = b.get_icons()
                    ikon = liste[0] if liste else None
                yol = ikon.get_filename() if ikon is not None else None
            except Exception:  # noqa: BLE001
                yol = None
            if yol and os.path.isabs(yol) and os.path.exists(yol):
                for p in paketler:
                    harita.setdefault(p, yol)
    except Exception as exc:  # noqa: BLE001
        print(f"[magaza] AppStream okunamadi: {exc}", file=sys.stderr)
    return harita


IKON_ADAYLARI = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "../../../usr/share/icons/hicolor/256x256/apps/carotos-magaza.png"),
    "/usr/share/icons/hicolor/256x256/apps/carotos-magaza.png",
]


def ikon_yolu():
    """Magaza simgesinin dosya yolu; yoksa None (gomulu logoya duser)."""
    for y in IKON_ADAYLARI:
        if os.path.isfile(y):
            return os.path.normpath(y)
    return None


def logo_dosyasi():
    """Gömülü logoyu bir önbellek dosyasına yazar ve yolunu döndürür (Kabuk
    logo için dosya yolu bekler)."""
    yol = ikon_yolu()
    if yol:
        return yol
    try:
        yol = os.path.join(GLib.get_user_cache_dir(), "carotos-magaza-logo.png")
        if not os.path.exists(yol):
            os.makedirs(os.path.dirname(yol), exist_ok=True)
            with open(yol, "wb") as f:
                f.write(base64.b64decode(LOGO_B64))
        return yol
    except Exception:  # noqa: BLE001
        return None


def logo_pixbuf(px):
    yol = ikon_yolu()
    if yol:
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_size(yol, px, px)
        except Exception:  # noqa: BLE001
            pass
    try:
        yk = GdkPixbuf.PixbufLoader.new_with_type("png")
        yk.set_size(px, px)
        yk.write(base64.b64decode(LOGO_B64))
        yk.close()
        return yk.get_pixbuf()
    except Exception:  # noqa: BLE001
        return None


# --- apt / dpkg -------------------------------------------------------------
def kurulu_paketler():
    try:
        r = subprocess.run(["dpkg-query", "-W", "-f=${Package} ${Status}\n"],
                           capture_output=True, text=True, timeout=20)
    except Exception:  # noqa: BLE001
        return set()
    return {s.split(" ", 1)[0] for s in r.stdout.splitlines()
            if s.endswith("install ok installed")}


def guncellenebilir_paketler():
    """`apt list --upgradable` çıktısından güncellenebilir paket adları."""
    try:
        r = subprocess.run(["apt", "list", "--upgradable"],
                           capture_output=True, text=True, timeout=30,
                           env=dict(os.environ, LC_ALL="C"))
    except Exception:  # noqa: BLE001
        return set()
    adlar = set()
    for satir in r.stdout.splitlines():
        if "/" in satir and "upgradable" in satir:
            adlar.add(satir.split("/", 1)[0].strip())
    return adlar


def _yetki():
    return shutil.which("pkexec")


def apt_komutu(eylem, *paketler):
    """eylem: install | remove | upgrade | update."""
    yetki = _yetki()
    if not yetki:
        return None
    if eylem == "update":
        return [yetki, "apt-get", "update"]
    if eylem == "upgrade":
        return [yetki, "env", "DEBIAN_FRONTEND=noninteractive",
                "apt-get", "upgrade", "-y"]
    return [yetki, "env", "DEBIAN_FRONTEND=noninteractive",
            "apt-get", eylem, "-y", *paketler]


# --- İşlem penceresi (apt çıktısı) ------------------------------------------
class IslemPenceresi(Gtk.Window):
    def __init__(self, ebeveyn, baslik, komut, bitince, otomatik_kapan=False):
        super().__init__(title=baslik)
        self.set_transient_for(ebeveyn)
        self.set_modal(True)
        self.set_default_size(660, 440)
        self.komut = komut
        self.bitince = bitince
        self.otomatik_kapan = otomatik_kapan
        self.surec = None
        self.iptal_edildi = False

        dis = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        tema.sinif(dis, "arka")
        self.add(dis)
        ust = Gtk.Box(spacing=10)
        for k in ("top", "bottom", "start", "end"):
            getattr(ust, f"set_margin_{k}")(14)
        self.spinner = Gtk.Spinner()
        self.spinner.start()
        ust.pack_start(self.spinner, False, False, 0)
        self.durum = tema.etiket(baslik, "kart-baslik")
        self.durum.set_ellipsize(Pango.EllipsizeMode.END)
        ust.pack_start(self.durum, True, True, 0)
        dis.pack_start(ust, False, False, 0)

        kaydir = Gtk.ScrolledWindow()
        self.gorunum = Gtk.TextView(editable=False, cursor_visible=False, monospace=True)
        self.gorunum.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.gorunum.set_left_margin(10)
        self.gorunum.set_right_margin(10)
        self.tampon = self.gorunum.get_buffer()
        kaydir.add(self.gorunum)
        dis.pack_start(kaydir, True, True, 0)

        alt = Gtk.Box(spacing=8)
        for k in ("top", "bottom", "start", "end"):
            getattr(alt, f"set_margin_{k}")(12)
        alt.set_halign(Gtk.Align.END)
        self.kapat_dugme = tema.dugme(M("iptal"), None, self._kapat)
        alt.pack_start(self.kapat_dugme, False, False, 0)
        dis.pack_start(alt, False, False, 0)

    def baslat(self):
        self.show_all()
        threading.Thread(target=self._calis, daemon=True).start()

    def _calis(self):
        try:
            self.surec = subprocess.Popen(
                self.komut, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)
            for satir in self.surec.stdout:
                GLib.idle_add(self._ekle, satir)
            kod = self.surec.wait()
        except Exception as exc:  # noqa: BLE001
            GLib.idle_add(self._ekle, f"\n[hata] {exc}\n")
            kod = 1
        GLib.idle_add(self._bitti, kod)

    def _ekle(self, satir):
        self.tampon.insert(self.tampon.get_end_iter(), satir)
        GLib.idle_add(lambda: self.gorunum.scroll_to_iter(
            self.tampon.get_end_iter(), 0.0, False, 0, 0) and False)
        return False

    def _bitti(self, kod):
        self.spinner.stop()
        basarili = (kod == 0 and not self.iptal_edildi)
        self.durum.get_style_context().add_class("basari-yazi" if basarili else "hata-yazi")
        self.durum.set_text(M("tamamlandi") if basarili else M("hata_olustu"))
        self.kapat_dugme.set_label(M("kapat"))
        if self.bitince:
            self.bitince(basarili)
        if basarili and self.otomatik_kapan:
            GLib.timeout_add_seconds(2, lambda: self.get_realized() and self.destroy())
        return False

    def _kapat(self):
        if self.surec and self.surec.poll() is None:
            self.iptal_edildi = True
            try:
                self.surec.terminate()
            except Exception:  # noqa: BLE001
                pass
        self.destroy()


# --- Tıklanır sarıcı --------------------------------------------------------
def tiklanir(icerik, tik):
    kutu = Gtk.EventBox()
    tema.sinif(kutu, "tiklanir")
    kutu.add(icerik)
    kutu.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
    kutu.connect("button-press-event", lambda *_: tik())
    kutu.connect("realize", lambda w: w.get_window().set_cursor(
        Gdk.Cursor.new_from_name(w.get_display(), "pointer")))
    return kutu


# --- Uygulama satırı --------------------------------------------------------
class UygulamaSatiri(Gtk.Box):
    def __init__(self, pencere, uygulama):
        super().__init__(spacing=14)
        self.p = pencere
        self.uygulama = uygulama
        tema.sinif(self, "kart")
        for k in ("top", "bottom", "start", "end"):
            getattr(self, f"set_margin_{k}")(0)
        ic = Gtk.Box(spacing=14)
        for k, d in (("top", 10), ("bottom", 10), ("start", 14), ("end", 14)):
            getattr(ic, f"set_margin_{k}")(d)
        self.pack_start(ic, True, True, 0)

        ikon = uygulama_ikonu(uygulama, 46, pencere.as_harita.get(uygulama.get("paket")))
        ikon.set_valign(Gtk.Align.CENTER)
        ic.pack_start(ikon, False, False, 0)

        orta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        orta.set_valign(Gtk.Align.CENTER)
        ad = tema.etiket(metin(uygulama["ad"]), "kart-baslik")
        orta.pack_start(ad, False, False, 0)
        ozet = tema.etiket(metin(uygulama.get("ozet", "")), "kart-alt", sar=True, genislik=70)
        ozet.set_lines(2)
        ozet.set_ellipsize(Pango.EllipsizeMode.END)
        orta.pack_start(ozet, False, False, 0)
        ic.pack_start(orta, True, True, 0)

        self.sag = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.sag.set_valign(Gtk.Align.CENTER)
        self.rozet = tema.rozet(M("kurulu_rozet"), "yesil")
        self.rozet.set_halign(Gtk.Align.END)
        self.rozet.set_no_show_all(True)
        self.sag.pack_start(self.rozet, False, False, 0)
        self.dugme = tema.dugme("", None, self._eylem)
        self.dugme.set_halign(Gtk.Align.END)
        self.sag.pack_start(self.dugme, False, False, 0)
        ic.pack_start(self.sag, False, False, 0)
        self.guncelle()

    def guncelle(self):
        kurulu = self.uygulama.get("paket") in self.p.kurulu
        ctx = self.dugme.get_style_context()
        ctx.remove_class("ana")
        ctx.remove_class("duz")
        if kurulu:
            self.rozet.show()
            self.dugme.set_label(M("kaldir"))
            ctx.add_class("duz")
        else:
            self.rozet.hide()
            self.dugme.set_label(M("kur"))
            ctx.add_class("ana")
        self.dugme.set_sensitive(self.p.mesgul is None)

    def _eylem(self):
        self.p.eylem(self.uygulama, "remove" if self.uygulama.get("paket") in self.p.kurulu
                     else "install")


# --- Ana pencere ------------------------------------------------------------
BOLUMLER = [
    ("kesfet", [("anasayfa", "ev"), ("kurulu", "onay"), ("guncelleme", "indir")]),
]


class MagazaPenceresi(Gtk.Window):
    def __init__(self, katalog):
        super().__init__(title="CarotOS Mağaza")
        self.katalog = katalog
        self.kategoriler = katalog.get("kategoriler", [])
        self.uygulamalar = katalog.get("uygulamalar", [])
        self.kat_ad = {k["id"]: k["ad"] for k in self.kategoriler}
        self.kurulu = kurulu_paketler()
        self.as_harita = {}
        self.guncellenebilir = set()
        self.guncelleme_denetlendi = False
        self.mesgul = None
        self.aktif = "anasayfa"
        self.arama = ""
        self.detay_app = None

        self.ui = ayarlari_oku()
        global DIL
        DIL = self.ui["lang"]
        self.set_title("CarotOS Store" if str(DIL).lower().startswith("en") else "CarotOS Mağaza")
        tema.uygula(self.ui["theme"], VURGU)

        self.set_default_size(1120, 740)
        self.set_size_request(900, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        pb = logo_pixbuf(64)
        if pb is not None:
            self.set_icon(pb)
            Gtk.Window.set_default_icon(pb)
        self.connect("destroy", lambda *_: Gtk.main_quit())

        bolumler = list(BOLUMLER) + [
            ("kategoriler", [(k["id"], KAT_IKON.get(k["id"], ("liste", "vurgu"))[0])
                             for k in self.kategoriler])]
        self.kabuk = tema.Kabuk(logo_dosyasi(), bolumler, self.sayfa_secildi)
        self.add(self.kabuk)

        self.arama_girisi = Gtk.SearchEntry()
        self.arama_girisi.set_placeholder_text(M("ara"))
        self.arama_girisi.set_size_request(240, -1)
        self.arama_girisi.connect("search-changed", self._arama_degisti)
        self.kabuk.ust_sag.pack_start(self.arama_girisi, False, False, 0)
        self.yenile_dugme = tema.dugme(M("yenile"), None, self.depoyu_yenile)
        self.kabuk.ust_sag.pack_start(self.yenile_dugme, False, False, 0)

        alt = Gtk.Box(spacing=8)
        self.dil_kutu = Gtk.ComboBoxText()
        self.dil_kutu.append("tr", "Türkçe")
        self.dil_kutu.append("en", "English")
        self.dil_kutu.set_active_id(DIL)
        self.dil_kutu.connect("changed", self._dil_degisti)
        alt.pack_start(self.dil_kutu, True, True, 0)
        self.tema_dugme = tema.dugme("", None, self._tema_degistir)
        alt.pack_start(self.tema_dugme, False, False, 0)
        self.kabuk.yan_alt.pack_start(alt, False, False, 0)
        self.alt_bilgi = tema.etiket("", "marka-alt")
        self.kabuk.yan_alt.pack_start(self.alt_bilgi, False, False, 0)

        self.metinleri_uygula()
        self.show_all()
        self.kabuk.sec("anasayfa")

        threading.Thread(target=self._as_yukle, daemon=True).start()
        self._guncelleme_denetle()

    # -- metinler ------------------------------------------------------------
    def metinleri_uygula(self):
        self.kabuk.marka_ayarla(M("baslik"), M("marka_alt", s="v" + APP_VERSION))
        self.kabuk.bolum_metni("kesfet", M("bolum_kesfet"))
        self.kabuk.bolum_metni("kategoriler", M("bolum_kategoriler"))
        for anahtar in ("anasayfa", "kurulu", "guncelleme"):
            self.kabuk.menu_metni(anahtar, M(anahtar))
        for k in self.kategoriler:
            self.kabuk.menu_metni(k["id"], metin(k["ad"]))
        self.alt_bilgi.set_text(M("hakkinda_mesaj"))
        koyu = self.ui["theme"] == "dark"
        self.tema_dugme.set_label("☀" if koyu else "☾")
        self.yenile_dugme.set_label(M("yenile"))
        self.arama_girisi.set_placeholder_text(M("ara"))
        self._guncelleme_rozeti()

    def _guncelleme_rozeti(self):
        n = len([u for u in self.uygulamalar
                 if u.get("paket") in self.guncellenebilir])
        self.kabuk.rozet("guncelleme", n or None)

    # -- dil / tema ----------------------------------------------------------
    def _dil_degisti(self, kutu):
        global DIL
        yeni = kutu.get_active_id()
        if yeni in ("tr", "en") and yeni != DIL:
            DIL = self.ui["lang"] = yeni
            ayarlari_kaydet(self.ui)
            self.metinleri_uygula()
            self.sayfa_secildi(self.aktif)

    def _tema_degistir(self, gorunum=None):
        self.ui["theme"] = gorunum or ("light" if self.ui["theme"] == "dark" else "dark")
        ayarlari_kaydet(self.ui)
        tema.uygula(self.ui["theme"], VURGU)
        self.metinleri_uygula()
        self.sayfa_secildi(self.aktif)
        self.queue_draw()

    # -- arama ---------------------------------------------------------------
    def _arama_degisti(self, giris):
        self.arama = giris.get_text().strip().lower()
        if self.arama:
            self.detay_app = None
            self.kabuk.baslik_ayarla(M("arama_basligi", s=giris.get_text().strip()),
                                     M("arama_alt"))
            self.kabuk.icerik(self._liste_sayfasi(self._suzulmus()))
        else:
            self.sayfa_secildi(self.aktif)

    # -- gezinme -------------------------------------------------------------
    def sayfa_secildi(self, anahtar):
        self.aktif = anahtar
        self.detay_app = None
        if self.arama:
            self.arama = ""
            self.arama_girisi.set_text("")
        if anahtar == "anasayfa":
            self.kabuk.baslik_ayarla(M("anasayfa"), M("anasayfa_alt"))
            self.kabuk.icerik(self._anasayfa())
        elif anahtar == "kurulu":
            self.kabuk.baslik_ayarla(M("kurulu"), M("kurulu_alt"))
            self.kabuk.icerik(self._kurulu_sayfasi())
        elif anahtar == "guncelleme":
            self.kabuk.baslik_ayarla(M("guncelleme"), M("guncelleme_alt"))
            self.kabuk.icerik(self._guncelleme_sayfasi())
        else:
            self.kabuk.baslik_ayarla(metin(self.kat_ad.get(anahtar, anahtar)), "")
            uyg = [u for u in self.uygulamalar if u.get("kategori") == anahtar]
            self.kabuk.icerik(self._liste_sayfasi(uyg))

    def kategoriye_git(self, kat_id):
        self.kabuk.sec(kat_id)

    def _suzulmus(self):
        sonuc = []
        for u in self.uygulamalar:
            havuz = " ".join([metin(u.get("ad", "")), u.get("paket", ""),
                              metin(u.get("ozet", "")), metin(u.get("aciklama", "")),
                              metin(self.kat_ad.get(u.get("kategori"), ""))]).lower()
            if self.arama in havuz:
                sonuc.append(u)
        sonuc.sort(key=lambda u: metin(u.get("ad", "")).lower())
        return sonuc

    # -- sayfa parçaları -----------------------------------------------------
    def _liste_sayfasi(self, uygulamalar, bos_parca=None):
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        if not uygulamalar:
            if bos_parca is not None:
                kutu.pack_start(bos_parca, True, True, 0)
            else:
                kutu.pack_start(tema.bos_durum("arama", M("sonuc_yok")), True, True, 0)
            return kutu
        sayac = tema.etiket(M("uyg_sayisi", n=len(uygulamalar)), "silik")
        kutu.pack_start(sayac, False, False, 0)
        for u in sorted(uygulamalar, key=lambda u: metin(u.get("ad", "")).lower()):
            satir = UygulamaSatiri(self, u)
            kutu.pack_start(tiklanir(satir, lambda a=u: self.detay_goster(a)), False, False, 0)
        return kutu

    def _anasayfa(self):
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        one = [u for u in self.uygulamalar if u.get("one_cikan")]
        if one:
            kutu.pack_start(tema.etiket(M("one_cikanlar"), "buyuk-baslik"), False, False, 0)
            izgara = Gtk.FlowBox()
            izgara.set_selection_mode(Gtk.SelectionMode.NONE)
            izgara.set_max_children_per_line(3)
            izgara.set_min_children_per_line(1)
            izgara.set_column_spacing(14)
            izgara.set_row_spacing(14)
            izgara.set_homogeneous(True)
            for u in one:
                izgara.add(self._one_cikan_kart(u))
            kutu.pack_start(izgara, False, False, 0)
        kutu.pack_start(tema.etiket(M("kategoriye_gozat"), "buyuk-baslik"), False, False, 6)
        kizgara = Gtk.FlowBox()
        kizgara.set_selection_mode(Gtk.SelectionMode.NONE)
        kizgara.set_max_children_per_line(3)
        kizgara.set_min_children_per_line(1)
        kizgara.set_column_spacing(14)
        kizgara.set_row_spacing(14)
        kizgara.set_homogeneous(True)
        for k in self.kategoriler:
            kizgara.add(self._kategori_kart(k))
        kutu.pack_start(kizgara, False, False, 0)
        return kutu

    def _one_cikan_kart(self, u):
        dis, ic = tema.kart(16, 8)
        ust = Gtk.Box(spacing=12)
        ikon = uygulama_ikonu(u, 48, self.as_harita.get(u.get("paket")))
        ikon.set_valign(Gtk.Align.START)
        ust.pack_start(ikon, False, False, 0)
        bilgi = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        bilgi.pack_start(tema.etiket(metin(u["ad"]), "kart-baslik"), False, False, 0)
        bilgi.pack_start(tema.etiket(metin(self.kat_ad.get(u.get("kategori"), "")),
                                     "silik"), False, False, 0)
        ust.pack_start(bilgi, True, True, 0)
        if u.get("paket") in self.kurulu:
            r = tema.rozet(M("kurulu_rozet"), "yesil")
            r.set_valign(Gtk.Align.START)
            ust.pack_end(r, False, False, 0)
        ic.pack_start(ust, False, False, 0)
        ozet = tema.etiket(metin(u.get("ozet", "")), "kart-alt", sar=True, genislik=44)
        ozet.set_lines(2)
        ozet.set_ellipsize(Pango.EllipsizeMode.END)
        ic.pack_start(ozet, True, True, 0)
        return tiklanir(dis, lambda a=u: self.detay_goster(a))

    def _kategori_kart(self, k):
        ikon_ad, renk = KAT_IKON.get(k["id"], ("liste", "vurgu"))
        n = len([u for u in self.uygulamalar if u.get("kategori") == k["id"]])
        dis, ic = tema.kart(16, 6)
        satir = Gtk.Box(spacing=12)
        satir.pack_start(tema.ikon_kutusu(ikon_ad, renk, 34), False, False, 0)
        bilgi = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        bilgi.set_valign(Gtk.Align.CENTER)
        bilgi.pack_start(tema.etiket(metin(k["ad"]), "kart-baslik"), False, False, 0)
        bilgi.pack_start(tema.etiket(M("uyg_sayisi", n=n), "silik"), False, False, 0)
        satir.pack_start(bilgi, True, True, 0)
        ic.pack_start(satir, False, False, 0)
        return tiklanir(dis, lambda i=k["id"]: self.kategoriye_git(i))

    def _kurulu_sayfasi(self):
        uyg = [u for u in self.uygulamalar if u.get("paket") in self.kurulu]
        bos = tema.bos_durum("onay", M("kurulu_bos_baslik"), M("kurulu_bos"))
        return self._liste_sayfasi(uyg, bos_parca=bos)

    def _guncelleme_sayfasi(self):
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        katalog_g = [u for u in self.uygulamalar if u.get("paket") in self.guncellenebilir]
        if not self.guncelleme_denetlendi:
            kutu.pack_start(tema.bos_durum("yenile", M("denetleniyor")), True, True, 0)
            return kutu
        if not self.guncellenebilir:
            kutu.pack_start(tema.bos_durum("onay", M("guncel_baslik"),
                                           M("guncel_alt", z=M("simdi"))), True, True, 0)
            return kutu
        dis, ic = tema.kart(16, 6)
        satir = Gtk.Box(spacing=12)
        satir.pack_start(tema.Ikon("indir", 24, "vurgu"), False, False, 0)
        satir.pack_start(tema.etiket(M("guncelleme_var", n=len(self.guncellenebilir)),
                                     "kart-baslik"), True, True, 0)
        self.guncelle_dugme = tema.dugme(M("tumunu_guncelle"), "ana", self.tumunu_guncelle)
        self.guncelle_dugme.set_sensitive(self.mesgul is None)
        satir.pack_end(self.guncelle_dugme, False, False, 0)
        ic.pack_start(satir, False, False, 0)
        kutu.pack_start(dis, False, False, 0)
        if katalog_g:
            kutu.pack_start(tema.etiket(M("katalog_guncel"), "kart-baslik"), False, False, 4)
            for u in sorted(katalog_g, key=lambda u: metin(u["ad"]).lower()):
                satir = UygulamaSatiri(self, u)
                kutu.pack_start(tiklanir(satir, lambda a=u: self.detay_goster(a)),
                                False, False, 0)
        diger = len(self.guncellenebilir) - len(katalog_g)
        if diger > 0:
            k2, _ = tema.not_kutusu(M("diger_paketler", n=diger), "bilgi")
            kutu.pack_start(k2, False, False, 0)
        return kutu

    # -- ayrıntı -------------------------------------------------------------
    def detay_goster(self, u):
        self.detay_app = u
        self.kabuk.baslik_ayarla(metin(u["ad"]), metin(u.get("ozet", "")))
        self.kabuk.icerik(self._detay_sayfasi(u))

    def _geri(self):
        if self.arama:
            self._arama_degisti(self.arama_girisi)
        else:
            self.sayfa_secildi(self.aktif)

    def _detay_sayfasi(self, u):
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        geri = tema.dugme(M("geri"), "duz", self._geri)
        geri.set_halign(Gtk.Align.START)
        kutu.pack_start(geri, False, False, 0)

        dis, ic = tema.kart(20, 12)
        ust = Gtk.Box(spacing=18)
        ikon = uygulama_ikonu(u, 72, self.as_harita.get(u.get("paket")))
        ikon.set_valign(Gtk.Align.START)
        ust.pack_start(ikon, False, False, 0)
        bilgi = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        baslik = Gtk.Box(spacing=10)
        baslik.pack_start(tema.etiket(metin(u["ad"]), "sayfa-baslik"), False, False, 0)
        self.detay_rozet = tema.rozet(M("kurulu_rozet"), "yesil")
        self.detay_rozet.set_valign(Gtk.Align.CENTER)
        self.detay_rozet.set_no_show_all(True)
        baslik.pack_start(self.detay_rozet, False, False, 0)
        bilgi.pack_start(baslik, False, False, 0)
        bilgi.pack_start(tema.etiket(metin(u.get("ozet", "")), "kart-alt", sar=True,
                                     genislik=70), False, False, 0)
        eylem = Gtk.Box(spacing=8)
        self.detay_dugme = tema.dugme("", None, lambda: self.eylem(
            u, "remove" if u.get("paket") in self.kurulu else "install"))
        eylem.pack_start(self.detay_dugme, False, False, 0)
        if u.get("site"):
            eylem.pack_start(tema.dugme(M("siteyi_ac"), "duz", self._site_ac, u["site"]),
                             False, False, 0)
        bilgi.pack_start(eylem, False, False, 6)
        ust.pack_start(bilgi, True, True, 0)
        ic.pack_start(ust, False, False, 0)
        kutu.pack_start(dis, False, False, 0)
        self._detay_dugme_guncelle()

        bilgi_izgara = Gtk.FlowBox()
        bilgi_izgara.set_selection_mode(Gtk.SelectionMode.NONE)
        bilgi_izgara.set_max_children_per_line(4)
        bilgi_izgara.set_column_spacing(12)
        bilgi_izgara.set_row_spacing(12)
        bilgi_izgara.set_homogeneous(True)
        for etk, deger in ((M("bilgi_kategori"), metin(self.kat_ad.get(u.get("kategori"), ""))),
                           (M("bilgi_boyut"), u.get("boyut", "—")),
                           (M("bilgi_lisans"), u.get("lisans", "—")),
                           (M("bilgi_paket"), u.get("paket", "—"))):
            d2, i2 = tema.kart(14, 2)
            i2.pack_start(tema.etiket(etk, "silik"), False, False, 0)
            i2.pack_start(tema.etiket(deger, "kart-baslik"), False, False, 0)
            bilgi_izgara.add(d2)
        kutu.pack_start(bilgi_izgara, False, False, 0)

        dis2, ic2 = tema.kart()
        tema.kart_basligi(ic2, M("aciklama_baslik"))
        ic2.pack_start(tema.etiket(metin(u.get("aciklama", u.get("ozet", ""))), None,
                                   sar=True, genislik=100, sec=True), False, False, 0)
        kutu.pack_start(dis2, False, False, 0)
        return kutu

    def _detay_dugme_guncelle(self):
        u = self.detay_app
        if not u:
            return
        kurulu = u.get("paket") in self.kurulu
        ctx = self.detay_dugme.get_style_context()
        ctx.remove_class("ana")
        ctx.remove_class("tehlike")
        self.detay_dugme.set_label(M("kaldir") if kurulu else M("kur"))
        ctx.add_class("tehlike" if kurulu else "ana")
        self.detay_dugme.set_sensitive(self.mesgul is None)
        if kurulu:
            self.detay_rozet.show()
        else:
            self.detay_rozet.hide()

    def _site_ac(self, url):
        try:
            Gtk.show_uri_on_window(self, url, Gdk.CURRENT_TIME)
        except Exception:  # noqa: BLE001
            pass

    # -- işlemler ------------------------------------------------------------
    def _mesgul_ayarla(self, ad):
        self.mesgul = ad
        for cls in (self.yenile_dugme,):
            cls.set_sensitive(ad is None)
        # görünen sayfadaki düğmeler sayfa yeniden kurulunca güncellenir

    def eylem(self, u, islem):
        if self.mesgul:
            return
        komut = apt_komutu(islem, u["paket"])
        if komut is None:
            self._pkexec_yok(islem, u["paket"])
            return
        self._mesgul_ayarla(islem + ":" + u["paket"])
        baslik = "%s — %s" % (metin(u["ad"]),
                              M("kaldiriliyor") if islem == "remove" else M("kuruluyor"))

        def bitince(basarili):
            if basarili:
                if islem == "install":
                    self.kurulu.add(u["paket"])
                else:
                    self.kurulu.discard(u["paket"])
                    self.guncellenebilir.discard(u["paket"])
            self._mesgul_ayarla(None)
            self._guncelleme_rozeti()
            if self.detay_app is u:
                self.detay_goster(u)
            else:
                self.sayfa_secildi(self.aktif)
        IslemPenceresi(self, baslik, komut, bitince).baslat()

    def depoyu_yenile(self):
        if self.mesgul:
            return
        komut = apt_komutu("update")
        if komut is None:
            self._pkexec_yok("update", "apt")
            return
        self._mesgul_ayarla("update")

        def bitince(_b):
            self._mesgul_ayarla(None)
            self._guncelleme_denetle()
        IslemPenceresi(self, M("yenileniyor"), komut, bitince, otomatik_kapan=True).baslat()

    def tumunu_guncelle(self):
        if self.mesgul:
            return
        komut = apt_komutu("upgrade")
        if komut is None:
            self._pkexec_yok("upgrade", "apt")
            return
        self._mesgul_ayarla("upgrade")

        def bitince(basarili):
            self._mesgul_ayarla(None)
            if basarili:
                self.kurulu = kurulu_paketler()
            self._guncelleme_denetle()
        IslemPenceresi(self, M("guncelleniyor"), komut, bitince).baslat()

    def _pkexec_yok(self, islem, paket):
        komut = {"update": "sudo apt-get update",
                 "upgrade": "sudo apt-get upgrade -y"}.get(
            islem, "sudo apt-get %s -y %s" % (islem, paket))
        d = Gtk.MessageDialog(transient_for=self, modal=True,
                              message_type=Gtk.MessageType.WARNING,
                              buttons=Gtk.ButtonsType.CLOSE, text=M("pkexec_yok_baslik"))
        d.format_secondary_text(M("pkexec_yok") + "\n\n" + komut)
        d.run()
        d.destroy()

    # -- arka plan -----------------------------------------------------------
    def _as_yukle(self):
        harita = appstream_ikon_haritasi()
        if harita:
            GLib.idle_add(self._as_hazir, harita)

    def _as_hazir(self, harita):
        self.as_harita = harita
        if not self.arama and self.detay_app is None:
            self.sayfa_secildi(self.aktif)
        return False

    def _guncelleme_denetle(self):
        def is_():
            return guncellenebilir_paketler()

        def bitti(sonuc):
            self.guncellenebilir = sonuc if isinstance(sonuc, set) else set()
            self.guncelleme_denetlendi = True
            self._guncelleme_rozeti()
            if self.aktif == "guncelleme" and self.detay_app is None and not self.arama:
                self.sayfa_secildi("guncelleme")
            return False
        threading.Thread(
            target=lambda: GLib.idle_add(bitti, is_()), daemon=True).start()


def main():
    try:
        with open(KATALOG_YOLU, encoding="utf-8") as f:
            katalog = json.load(f)
    except Exception as exc:  # noqa: BLE001
        print(f"Katalog okunamadi ({KATALOG_YOLU}): {exc}", file=sys.stderr)
        sys.exit(1)
    MagazaPenceresi(katalog).show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
