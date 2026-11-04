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

import dil  # noqa: E402  (ortak dil katmani: ortak/dil.py)
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
    """CAROTOS_DIL > sistem dili (etkin diller arasindan, ortak/dil.py) > locale > en."""
    d = os.environ.get("CAROTOS_DIL")
    if d in dil.KODLAR:
        return d
    if any(os.environ.get(a, "").strip() not in ("", "C", "POSIX")
           for a in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")):
        return dil.varsayilan_dil()
    try:
        kod = (locale.getdefaultlocale()[0] or "")
    except Exception:  # noqa: BLE001
        kod = ""
    return dil.varsayilan_dil({"LANG": kod}) if kod else "en"


def _ayar_dosyasi():
    return os.path.join(GLib.get_user_config_dir(), "carotos-magaza", "ayarlar.json")


def ayarlari_oku():
    veri = {"lang": _sistem_dili(), "theme": "dark"}
    try:
        with open(_ayar_dosyasi(), encoding="utf-8") as f:
            k = json.load(f)
        if k.get("lang") in dil.KODLAR:
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
    "sepete_ekle": {"tr": "Sepete ekle", "en": "Add to basket"},
    "sepette": {"tr": "Sepette ✓", "en": "In basket ✓"},
    "sepeti_kur": {"tr": "Sepeti kur ({n})", "en": "Install basket ({n})"},
    "sepet_kuruluyor": {"tr": "{n} uygulama kuruluyor", "en": "Installing {n} apps"},
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


METIN = dil.zenginlestir(METIN)      # tr/en sozlukleri her dil icin yedekli (ortak/dil.py)


def M(anahtar, **b):
    return dil.T(METIN.get(anahtar), DIL, anahtar, **b)


def metin(sozluk):
    """Katalog/arayuz metni: iki dilli sozluk ya da duz metin. Eksik dilde en, tr."""
    if isinstance(sozluk, dict):
        return dil.metin(sozluk, DIL)
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
    # LC_ALL=C: pkexec yerel ayari korur; Turkce'de bazi paketlerin kurulum
    # betikleri bozulur (rkhunter: tr '[:upper:]' '[:lower:]' "I" harfini
    # kucultmez, betik 10 koduyla duser, paket yari kurulu kalir). Bu yuzden
    # apt dil ayarindan bagimsiz calistirilir (cikti Ingilizce olur).
    ortam = ["env", "DEBIAN_FRONTEND=noninteractive", "LC_ALL=C"]
    if eylem == "upgrade":
        return [yetki, *ortam, "apt-get", "upgrade", "-y"]
    return [yetki, *ortam, "apt-get", eylem, "-y", *paketler]


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
        islem = Gtk.Box(spacing=6)
        islem.set_halign(Gtk.Align.END)
        self.sepet_dugme = tema.dugme("", None, self._sepet)
        self.sepet_dugme.set_no_show_all(True)
        islem.pack_start(self.sepet_dugme, False, False, 0)
        self.dugme = tema.dugme("", None, self._eylem)
        islem.pack_start(self.dugme, False, False, 0)
        self.sag.pack_start(islem, False, False, 0)
        ic.pack_start(self.sag, False, False, 0)
        self.guncelle()

    def guncelle(self):
        kurulu = self.uygulama.get("paket") in self.p.kurulu
        ctx = self.dugme.get_style_context()
        ctx.remove_class("ana")
        ctx.remove_class("duz")
        sepet_ctx = self.sepet_dugme.get_style_context()
        sepet_ctx.remove_class("ana")
        sepet_ctx.remove_class("duz")
        if kurulu:
            self.rozet.show()
            self.dugme.set_label(M("kaldir"))
            ctx.add_class("duz")
            self.sepet_dugme.hide()
        else:
            self.rozet.hide()
            self.dugme.set_label(M("kur"))
            ctx.add_class("ana")
            sepette = self.uygulama.get("paket") in self.p.sepet
            self.sepet_dugme.set_label(M("sepette") if sepette else M("sepete_ekle"))
            sepet_ctx.add_class("ana" if sepette else "duz")
            self.sepet_dugme.show()
        self.dugme.set_sensitive(self.p.mesgul is None)
        self.sepet_dugme.set_sensitive(self.p.mesgul is None)

    def _eylem(self):
        self.p.eylem(self.uygulama, "remove" if self.uygulama.get("paket") in self.p.kurulu
                     else "install")

    def _sepet(self):
        self.p.sepet_degistir(self.uygulama.get("paket"))
        self.guncelle()


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
        self.sepet = set()      # toplu kurulum icin secilen paketler
        self.aktif = "anasayfa"
        self.arama = ""
        self.detay_app = None

        self.ui = ayarlari_oku()
        global DIL
        DIL = self.ui["lang"]
        self.set_title("CarotOS " + M("baslik"))   # "CarotOS" oneki her dilde kalir
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
        self.sepet_kur_dugme = tema.dugme("", None, self.sepeti_kur)
        self.sepet_kur_dugme.get_style_context().add_class("ana")
        self.sepet_kur_dugme.set_no_show_all(True)
        self.kabuk.ust_sag.pack_start(self.sepet_kur_dugme, False, False, 0)

        alt = Gtk.Box(spacing=8)
        self.dil_kutu = Gtk.ComboBoxText()
        for kod, ad, taslak in dil.etkin_diller():       # yalniz cevirisi hazir diller
            self.dil_kutu.append(kod, dil.secici_adi(kod, ad, taslak))
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
        self._sepet_guncelle()
        self._guncelleme_rozeti()

    def _guncelleme_rozeti(self):
        n = len([u for u in self.uygulamalar
                 if u.get("paket") in self.guncellenebilir])
        self.kabuk.rozet("guncelleme", n or None)

    # -- dil / tema ----------------------------------------------------------
    def _dil_degisti(self, kutu):
        global DIL
        yeni = kutu.get_active_id()
        if yeni in dil.KODLAR and yeni != DIL:
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
        for cls in (self.yenile_dugme, self.sepet_kur_dugme):
            cls.set_sensitive(ad is None)
        # görünen sayfadaki düğmeler sayfa yeniden kurulunca güncellenir

    # -- sepet (toplu kurulum) -----------------------------------------------
    def sepet_degistir(self, paket):
        if paket in self.sepet:
            self.sepet.discard(paket)
        else:
            self.sepet.add(paket)
        self._sepet_guncelle()

    def _sepet_guncelle(self):
        n = len(self.sepet)
        self.sepet_kur_dugme.set_label(M("sepeti_kur", n=n))
        if n:
            self.sepet_kur_dugme.show()
        else:
            self.sepet_kur_dugme.hide()

    def sepeti_kur(self):
        """Sepetteki tum paketleri TEK apt-get cagrisiyla kurar (tek parola istemi)."""
        if self.mesgul or not self.sepet:
            return
        paketler = sorted(self.sepet)
        komut = apt_komutu("install", *paketler)
        if komut is None:
            self._pkexec_yok("install", " ".join(paketler))
            return
        self._mesgul_ayarla("install:sepet")

        def bitince(_basarili):
            # Paketlerden biri dusse (ornegin kurulum betigi hatasi) digerleri
            # kurulmus olabilir; gercek durum dpkg'den okunur. Kurulamayanlar
            # sepette kalir, kullanici yeniden deneyebilir.
            self.kurulu = kurulu_paketler()
            self.sepet -= self.kurulu
            self._mesgul_ayarla(None)
            self._sepet_guncelle()
            self._guncelleme_rozeti()
            if self.detay_app is not None:
                self.detay_goster(self.detay_app)
            else:
                self.sayfa_secildi(self.aktif)
        IslemPenceresi(self, M("sepet_kuruluyor", n=len(paketler)), komut, bitince).baslat()

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
                    self.sepet.discard(u["paket"])
                else:
                    self.kurulu.discard(u["paket"])
                    self.guncellenebilir.discard(u["paket"])
            self._mesgul_ayarla(None)
            self._sepet_guncelle()
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
    pencere = MagazaPenceresi(katalog)
    pencere.show_all()
    if "--paket" in sys.argv:
        try:
            ad = sys.argv[sys.argv.index("--paket") + 1]
            uygulama = next((u for u in pencere.uygulamalar
                             if u.get("paket") == ad), None)
            if uygulama:
                # pencere yerleştikten sonra aç; açılış sırasındaki sayfa
                # kurulumu ayrıntı sayfasının üzerine yazmasın
                def ac():
                    pencere.detay_goster(uygulama)
                    return False
                GLib.timeout_add(600, ac)
        except (IndexError, ValueError):
            pass
    Gtk.main()


if __name__ == "__main__":
    main()
