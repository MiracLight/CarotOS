#!/usr/bin/env python3
"""CarotOS Mağaza — CarotOS için native uygulama mağazası.

Küratörlü bir katalog (katalog.json) üzerinden apt paketlerini kurar/kaldırır.
Tasarım ve davranış olarak CarotOS'un diğer uygulamalarıyla (Poligon, USB
Denetimi) tutarlıdır: koyu tema, aynı aksan rengi, iki dilli (tr/en) arayüz.

Dil: varsayılan olarak sistem diline (greeter'da seçilen) göre gelir; sağ
üstteki TR/EN düğmesiyle tek tıkla değiştirilebilir, arayüz anında yeniden
kurulur. Kurulum/kaldırma `pkexec apt-get` ile yapılır; pkexec yoksa elle
komut gösterilir. Kurulu olup olmadığı tek bir `dpkg-query` çağrısıyla
belirlenir.
"""
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango  # noqa: E402

import base64
import json
import locale
import os
import shutil
import subprocess
import sys
import threading

APP_VERSION = "1.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KATALOG_YOLU = os.path.join(BASE_DIR, "katalog.json")
IKON_YOLU = os.path.join(BASE_DIR, "ikonlar.json")
LOGO_B64 = (
    "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"
)

# Hakkında bölümü bağlantıları (CarotOS projesi)
GITHUB_URL = "https://github.com/MiracLight/CarotOS"
WEB_URL = "https://carotos.org"

# --- CarotOS paleti (diğer uygulamalarla aynı) ------------------------------
# --- CarotOS paleti: koyu ve açık; sistem temasına göre seçilir ------------
KOYU_PALET = {
    "accent": "#87979B", "zemin": "#1b1f20", "kart": "#242a2b",
    "kart_ustu": "#2b3233", "kenar": "#333b3c", "metin": "#e6ebec",
    "metin_soft": "#9aa7a9", "yesil": "#4c9a6a", "kirmizi": "#c2554f",
    "kur_hover": "#97a7ab",
}
ACIK_PALET = {
    "accent": "#6c7e82", "zemin": "#eef1f1", "kart": "#ffffff",
    "kart_ustu": "#e7ecec", "kenar": "#d2d9da", "metin": "#1b2122",
    "metin_soft": "#5f6d6f", "yesil": "#3f8b5f", "kirmizi": "#b5453f",
    "kur_hover": "#5c6e72",
}


def _sistem_koyu_mu():
    """Sistem GTK teması koyu mu? Tema arka planının parlaklığına bakar."""
    try:
        ayar = Gtk.Settings.get_default()
        if ayar.get_property("gtk-application-prefer-dark-theme"):
            return True
        pencere = Gtk.Window()
        ok, c = pencere.get_style_context().lookup_color("theme_bg_color")
        pencere.destroy()
        if ok:
            parlaklik = 0.2126 * c.red + 0.7152 * c.green + 0.0722 * c.blue
            return parlaklik < 0.5
        ad = (ayar.get_property("gtk-theme-name") or "").lower()
        return "dark" in ad
    except Exception:  # noqa: BLE001 -- belirlenemezse koyu varsay
        return True


def tema_paleti():
    """CAROTOS_TEMA (koyu/acik) ile zorlanabilir; yoksa sistemden algılanır."""
    tercih = os.environ.get("CAROTOS_TEMA", "").lower()
    if tercih in ("koyu", "dark"):
        return KOYU_PALET
    if tercih in ("acik", "açık", "light"):
        return ACIK_PALET
    return KOYU_PALET if _sistem_koyu_mu() else ACIK_PALET


# --- Dil --------------------------------------------------------------------
def _sistem_dili():
    """Greeter sistem dilini belirler; locale onu yansıtır. tr/en döner."""
    d = os.environ.get("CAROTOS_DIL")
    if d in ("tr", "en"):
        return d
    for anahtar in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        deger = os.environ.get(anahtar, "")
        if deger:
            return "tr" if deger.lower().startswith("tr") else "en"
    try:
        kod = (locale.getdefaultlocale()[0] or "")
    except Exception:  # noqa: BLE001
        kod = ""
    return "tr" if kod.lower().startswith("tr") else "en"


DIL = _sistem_dili()

METIN = {
    "baslik": {"tr": "CarotOS Mağaza", "en": "CarotOS Store"},
    "ara": {"tr": "Uygulama ara…", "en": "Search apps…"},
    "tumu": {"tr": "Tümü", "en": "All"},
    "kur": {"tr": "Kur", "en": "Install"},
    "kaldir": {"tr": "Kaldır", "en": "Remove"},
    "kurulu": {"tr": "Kurulu", "en": "Installed"},
    "kuruluyor": {"tr": "Kuruluyor…", "en": "Installing…"},
    "kaldiriliyor": {"tr": "Kaldırılıyor…", "en": "Removing…"},
    "yenile": {"tr": "Depoyu yenile", "en": "Refresh repos"},
    "yenileniyor": {"tr": "Depo yenileniyor…", "en": "Refreshing repos…"},
    "bos_kategori": {"tr": "Bu kategori yakında doldurulacak.",
                     "en": "This category is coming soon."},
    "sonuc_yok": {"tr": "Aramayla eşleşen uygulama bulunamadı.",
                  "en": "No apps match your search."},
    "kapat": {"tr": "Kapat", "en": "Close"},
    "iptal": {"tr": "İptal", "en": "Cancel"},
    "tamamlandi": {"tr": "Tamamlandı.", "en": "Done."},
    "hata_olustu": {"tr": "İşlem başarısız oldu.", "en": "The operation failed."},
    "otomatik_kapanis": {"tr": "Bu pencere birazdan kapanacak…",
                         "en": "This window will close shortly…"},
    "pkexec_yok_baslik": {"tr": "Yetki aracı bulunamadı",
                          "en": "Privilege tool not found"},
    "pkexec_yok": {
        "tr": ("pkexec bulunamadı, bu yüzden kurulum grafik arayüzden "
               "yapılamıyor. Aşağıdaki komutu bir terminalde çalıştır:"),
        "en": ("pkexec was not found, so installation can't run from the GUI. "
               "Run this command in a terminal:")},
    "uyg_sayisi": {"tr": "{n} uygulama", "en": "{n} apps"},
    "hakkinda_baslik": {"tr": "Hakkında", "en": "About"},
    "hakkinda_yapildi": {"tr": "CarotOS için geliştirildi.",
                         "en": "Made for CarotOS."},
    "hakkinda_yapimci": {"tr": "Geliştiren: Yusuf Miraç Üzümcüler",
                         "en": "By Yusuf Miraç Üzümcüler"},
    "hakkinda_github": {"tr": "GitHub", "en": "GitHub"},
    "hakkinda_web": {"tr": "İnternet sitesi", "en": "Website"},
    "hakkinda_mesaj": {
        "tr": "Yapılmış her şey insanlığa aittir.",
        "en": "Everything created belongs to humanity."},
}


def M(anahtar, **b):
    s = METIN[anahtar][DIL]
    return s.format(**b) if b else s


def metin(sozluk):
    """Katalogtaki {tr/en} alanından doğru dili döndürür."""
    if isinstance(sozluk, dict):
        return sozluk.get(DIL) or sozluk.get("tr") or sozluk.get("en") or ""
    return sozluk or ""


# Kategori ikonu temada yoksa kullanılacak genel ikon
GENEL_IKON = {
    "grafik": "applications-graphics",
    "guvenlik": "security-high",
    "ofis": "applications-office",
    "internet": "applications-internet",
    "medya": "applications-multimedia",
    "gelistirme": "applications-development",
    "sistem": "applications-utilities",
}


_ZENGIN_TEMA = None  # Papirus gibi, uygulama simgelerini kurulum gerekmeden taşıyan tema


def _zengin_tema():
    """Sistem teması seyrek olsa bile uygulama simgelerini bulabilmek için
    Papirus (ya da benzeri zengin) ikon temasını bir kez yükler. Yoksa None."""
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
    """Bir uygulama için denenecek ikon adları (katalogdaki + yaygın türevler)."""
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


def _gomulu_ikonlar():
    """Mağazayla birlikte gelen (paket -> base64 PNG) gerçek uygulama
    simgeleri. Hiçbir kuruluma/temaya bağlı değildir; her sistemde çalışır."""
    try:
        with open(IKON_YOLU, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


GOMULU_IKON = _gomulu_ikonlar()


def _gomulu_ikon_resmi(paket, px):
    b64 = GOMULU_IKON.get(paket)
    if not b64:
        return None
    try:
        veri = base64.b64decode(b64)
        yk = GdkPixbuf.PixbufLoader.new_with_type("png")
        yk.set_size(px, px)
        yk.write(veri)
        yk.close()
        return Gtk.Image.new_from_pixbuf(yk.get_pixbuf())
    except Exception:  # noqa: BLE001
        return None


def uygulama_ikonu(uygulama, px, as_yol=None):
    """Bir uygulama satırı için en iyi simgeyi Gtk.Image olarak döndürür.

    Sıra: (1) mağazaya GÖMÜLÜ gerçek simge (her sistemde çalışır), (2)
    AppStream dosyası, (3) sistemin varsayılan ikon teması, (4) Papirus gibi
    zengin tema, (5) kategori yedek simgesi. Böylece aynı kategorideki
    uygulamalar aynı genel simgeye düşmek yerine kendi gerçek simgeleriyle
    görünür — kurulu olmasalar bile."""
    gomulu = _gomulu_ikon_resmi(uygulama.get("paket"), px)
    if gomulu is not None:
        return gomulu
    if as_yol:
        try:
            return dosyadan_ikon(as_yol, px)
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
                img = Gtk.Image.new_from_icon_name(ad, Gtk.IconSize.DND)
                img.set_pixel_size(px)
                return img
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
    img = Gtk.Image.new_from_icon_name(
        GENEL_IKON.get(uygulama.get("kategori"), "package-x-generic"),
        Gtk.IconSize.DND)
    img.set_pixel_size(px)
    return img


def appstream_ikon_haritasi():
    """paket-adi -> yerel ikon dosyasi yolu.

    Debian'ın AppStream (DEP-11) verisinden okunur; bu sayede HENÜZ KURULU
    OLMAYAN uygulamaların bile gerçek simgesi gösterilebilir (GNOME Software'in
    yaptığı gibi). 'appstream' paketi ve 'apt update' ile inen simge önbelleği
    gerekir. Veri yoksa boş sözlük döner ve uygulama tema/kategori simgesine
    güvenle düşer. Yavaş olabileceği için arka planda çağrılır."""
    harita = {}
    try:
        gi.require_version("AppStream", "1.0")
        from gi.repository import AppStream as As  # noqa: N814
    except Exception:  # noqa: BLE001 -- AppStream yoksa sessizce bos don
        return harita
    try:
        havuz = As.Pool()
        havuz.load()
        bilesenler = havuz.get_components()
        try:
            dizi = list(bilesenler)
        except TypeError:
            dizi = bilesenler.as_array()
        for b in dizi:
            try:
                paketler = list(b.get_pkgnames() or [])
            except Exception:  # noqa: BLE001
                paketler = []
            if not paketler:
                continue
            yol = None
            try:
                ikon = (b.get_icon_by_size(64, 64)
                        or b.get_icon_by_size(48, 48))
                if ikon is None:
                    liste = b.get_icons()
                    ikon = liste[0] if liste else None
                if ikon is not None:
                    yol = ikon.get_filename()
            except Exception:  # noqa: BLE001
                yol = None
            if yol and os.path.isabs(yol) and os.path.exists(yol):
                for p in paketler:
                    harita.setdefault(p, yol)
    except Exception as exc:  # noqa: BLE001
        print(f"[magaza] AppStream okunamadi: {exc}", file=sys.stderr)
        return harita
    print(f"[magaza] AppStream: {len(harita)} paket icin gercek simge bulundu",
          file=sys.stderr)
    return harita


def dosyadan_ikon(yol, px):
    """Yerel bir ikon dosyasını px boyutunda Gtk.Image olarak yükler."""
    pb = GdkPixbuf.Pixbuf.new_from_file_at_size(yol, px, px)
    return Gtk.Image.new_from_pixbuf(pb)


def logo_pixbuf(px):
    """Gomulu (base64) PNG logoyu px boyutunda Pixbuf olarak cozer; yoksa None."""
    try:
        veri = base64.b64decode(LOGO_B64)
        yukleyici = GdkPixbuf.PixbufLoader.new_with_type("png")
        yukleyici.set_size(px, px)
        yukleyici.write(veri)
        yukleyici.close()
        return yukleyici.get_pixbuf()
    except Exception:  # noqa: BLE001
        return None


# --- apt / dpkg yardımcıları -----------------------------------------------
def kurulu_paketler():
    """Kurulu TÜM paket adlarını küme olarak döndürür (tek dpkg çağrısı)."""
    try:
        r = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package} ${Status}\n"],
            capture_output=True, text=True, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"[magaza] dpkg-query calismadi: {exc}", file=sys.stderr)
        return set()
    kurulu = set()
    for satir in r.stdout.splitlines():
        parcalar = satir.split(" ", 1)
        if len(parcalar) == 2 and parcalar[1].strip() == "install ok installed":
            kurulu.add(parcalar[0])
    return kurulu


def _yetki_komutu():
    return shutil.which("pkexec")


def apt_komutu(eylem, paket):
    """eylem: 'install' | 'remove'. Yükseltilmiş apt-get komutu ya da None."""
    temel = ["apt-get", eylem, "-y", paket]
    yetki = _yetki_komutu()
    if yetki:
        return [yetki, "env", "DEBIAN_FRONTEND=noninteractive"] + temel
    return None


def apt_yenile_komutu():
    yetki = _yetki_komutu()
    if yetki:
        return [yetki, "apt-get", "update"]
    return None


# --- İşlem (kurulum/kaldırma/yenileme) penceresi ----------------------------
class IslemPenceresi(Gtk.Window):
    """apt çıktısını canlı gösteren ilerleme penceresi.

    otomatik_kapan=True ise işlem başarıyla bitince pencere 3 sn sonra
    kendiliğinden kapanır (depo yenileme için)."""

    def __init__(self, ebeveyn, baslik, komut, bitince, otomatik_kapan=False):
        super().__init__(title=baslik)
        self.set_transient_for(ebeveyn)
        self.set_modal(True)
        self.set_default_size(640, 420)
        self.komut = komut
        self.bitince = bitince
        self.otomatik_kapan = otomatik_kapan
        self.surec = None
        self.iptal_edildi = False

        dis = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(dis)

        ust = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        ust.set_margin_top(14); ust.set_margin_bottom(14)
        ust.set_margin_start(16); ust.set_margin_end(16)
        self.spinner = Gtk.Spinner(); self.spinner.start()
        ust.pack_start(self.spinner, False, False, 0)
        self.durum = Gtk.Label(label=baslik, xalign=0)
        self.durum.get_style_context().add_class("islem-baslik")
        ust.pack_start(self.durum, True, True, 0)
        dis.pack_start(ust, False, False, 0)

        kaydir = Gtk.ScrolledWindow()
        kaydir.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.gorunum = Gtk.TextView()
        self.gorunum.set_editable(False)
        self.gorunum.set_cursor_visible(False)
        self.gorunum.set_monospace(True)
        self.gorunum.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.tampon = self.gorunum.get_buffer()
        kaydir.add(self.gorunum)
        dis.pack_start(kaydir, True, True, 0)

        alt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        alt.set_margin_top(10); alt.set_margin_bottom(12)
        alt.set_margin_start(16); alt.set_margin_end(16)
        alt.set_halign(Gtk.Align.END)
        self.kapat_dugme = Gtk.Button(label=M("iptal"))
        self.kapat_dugme.connect("clicked", self._kapat)
        alt.pack_start(self.kapat_dugme, False, False, 0)
        dis.pack_start(alt, False, False, 0)

    def baslat(self):
        self.show_all()
        threading.Thread(target=self._calis, daemon=True).start()

    def _calis(self):
        try:
            self.surec = subprocess.Popen(
                self.komut, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1)
            for satir in self.surec.stdout:
                GLib.idle_add(self._ekle, satir)
            kod = self.surec.wait()
        except Exception as exc:  # noqa: BLE001
            GLib.idle_add(self._ekle, f"\n[hata] {exc}\n")
            kod = 1
        GLib.idle_add(self._bitti, kod)

    def _ekle(self, satir):
        son = self.tampon.get_end_iter()
        self.tampon.insert(son, satir)
        GLib.idle_add(self._en_alta_kaydir)
        return False

    def _en_alta_kaydir(self):
        son = self.tampon.get_end_iter()
        self.gorunum.scroll_to_iter(son, 0.0, False, 0, 0)
        return False

    def _bitti(self, kod):
        self.spinner.stop()
        basarili = (kod == 0 and not self.iptal_edildi)
        self.durum.get_style_context().add_class(
            "islem-ok" if basarili else "islem-hata")
        self.kapat_dugme.set_label(M("kapat"))
        if self.bitince:
            self.bitince(basarili)
        if basarili and self.otomatik_kapan:
            self.durum.set_text(M("otomatik_kapanis"))
            GLib.timeout_add_seconds(3, self._otomatik_kapat)
        else:
            self.durum.set_text(M("tamamlandi") if basarili else M("hata_olustu"))
        return False

    def _otomatik_kapat(self):
        if self.get_realized():
            self.destroy()
        return False

    def _kapat(self, _dugme):
        if self.surec and self.surec.poll() is None:
            self.iptal_edildi = True
            try:
                self.surec.terminate()
            except Exception:  # noqa: BLE001
                pass
        self.destroy()


# --- Uygulama satırı --------------------------------------------------------
class UygulamaSatiri(Gtk.Box):
    def __init__(self, uygulama, kurulu, eylem_cb, as_yol=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.uygulama = uygulama
        self.eylem_cb = eylem_cb
        self.get_style_context().add_class("uyg-satiri")
        self.set_margin_top(3); self.set_margin_bottom(3)

        ikon = uygulama_ikonu(uygulama, 48, as_yol)
        ikon.set_pixel_size(48)
        ikon.set_valign(Gtk.Align.CENTER)
        self.pack_start(ikon, False, False, 0)

        orta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        orta.set_valign(Gtk.Align.CENTER)
        ad = Gtk.Label(label=metin(uygulama["ad"]), xalign=0)
        ad.get_style_context().add_class("uyg-ad")
        orta.pack_start(ad, False, False, 0)
        ozet = Gtk.Label(label=metin(uygulama.get("ozet", "")), xalign=0)
        ozet.get_style_context().add_class("uyg-ozet")
        ozet.set_line_wrap(True)
        ozet.set_lines(2)
        ozet.set_ellipsize(Pango.EllipsizeMode.END)
        orta.pack_start(ozet, False, False, 0)
        self.pack_start(orta, True, True, 0)

        sag = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sag.set_valign(Gtk.Align.CENTER)
        sag.set_halign(Gtk.Align.END)
        self.rozet = Gtk.Label(xalign=1)
        self.rozet.get_style_context().add_class("rozet")
        sag.pack_start(self.rozet, False, False, 0)
        self.dugme = Gtk.Button()
        self.dugme.set_halign(Gtk.Align.END)
        self.dugme.connect("clicked", self._tiklandi)
        sag.pack_start(self.dugme, False, False, 0)
        self.pack_start(sag, False, False, 0)

        self.durumu_uygula(kurulu)

    def durumu_uygula(self, kurulu):
        self.kurulu = kurulu
        ctx = self.dugme.get_style_context()
        ctx.remove_class("kur-dugme")
        ctx.remove_class("kaldir-dugme")
        if kurulu:
            self.rozet.set_text("✓ " + M("kurulu"))
            self.rozet.get_style_context().add_class("rozet-kurulu")
            self.dugme.set_label(M("kaldir"))
            ctx.add_class("kaldir-dugme")
        else:
            self.rozet.set_text("")
            self.rozet.get_style_context().remove_class("rozet-kurulu")
            self.dugme.set_label(M("kur"))
            ctx.add_class("kur-dugme")
        self.dugme.set_sensitive(True)

    def mesgul(self, metin_):
        self.dugme.set_label(metin_)
        self.dugme.set_sensitive(False)

    def _tiklandi(self, _dugme):
        self.eylem_cb(self, "remove" if self.kurulu else "install")


# --- Ana pencere ------------------------------------------------------------
class MagazaPenceresi(Gtk.Window):
    def __init__(self, katalog):
        super().__init__(title=M("baslik"))
        self.katalog = katalog
        self.kategoriler = katalog.get("kategoriler", [])
        self.uygulamalar = katalog.get("uygulamalar", [])
        self.kurulu = kurulu_paketler()
        self.P = tema_paleti()       # sistem temasına göre renk paleti
        self.as_harita = {}          # paket -> gerçek simge yolu (AppStream)
        self.aktif_kategori = None   # None = tümü
        self.arama = ""
        self.satirlar = []

        self.set_default_size(980, 660)
        self.set_position(Gtk.WindowPosition.CENTER)
        # Uygulama logosu = pencere/gorev-cubugu ikonu (baslik cubugundaki
        # beyaz dikdortgenin yerini alir). Ayri bir basliga logo KONMAZ.
        pb = logo_pixbuf(64)
        if pb is not None:
            self.set_icon(pb)
            Gtk.Window.set_default_icon(pb)
        self._stil()

        self.kok = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.kok)
        self._insa()

        # Gerçek simgeleri AppStream'den arka planda yükle; hazır olunca
        # listeyi tazele (UI'yi bloke etmesin).
        threading.Thread(target=self._as_yukle, daemon=True).start()

    def _as_yukle(self):
        harita = appstream_ikon_haritasi()
        if harita:
            GLib.idle_add(self._as_hazir, harita)

    def _as_hazir(self, harita):
        self.as_harita = harita
        self.listeyi_kur()
        return False

    # -- stil ----------------------------------------------------------------
    def _stil(self):
        P = self.P
        ACCENT = P["accent"]; ZEMIN = P["zemin"]; KART = P["kart"]
        KART_USTU = P["kart_ustu"]; KENAR = P["kenar"]; METIN_RENK = P["metin"]
        METIN_SOFT = P["metin_soft"]; YESIL = P["yesil"]; KIRMIZI = P["kirmizi"]
        KUR_HOVER = P["kur_hover"]
        css = f"""
        window {{ background-color: {ZEMIN}; }}
        label {{ color: {METIN_RENK}; }}
        .ada {{
            background-color: {KART}; border: 1px solid {KENAR};
            border-radius: 10px; padding: 9px 22px;
        }}
        .uygulama-basligi {{ font-size: 16px; font-weight: 700; }}
        entry.arama {{
            background-color: {ZEMIN}; color: {METIN_RENK};
            border: 1px solid {KENAR}; border-radius: 7px;
            padding: 6px 12px; min-height: 0;
        }}
        .dil-secici {{
            background-color: {ZEMIN}; border-radius: 7px; padding: 2px;
            border: 1px solid {KENAR};
        }}
        .dil-secici button {{
            background: transparent; background-image: none; border: none;
            box-shadow: none; border-radius: 5px; padding: 3px 12px; margin: 0;
            min-height: 0; color: {METIN_SOFT};
        }}
        .dil-secici button label {{ color: {METIN_SOFT}; font-weight: 700;
            font-size: 12px; }}
        .dil-secici button:checked {{ background-color: {ACCENT}; }}
        .dil-secici button:checked label {{ color: white; }}
        .kenar {{ background-color: {KART}; border-right: 1px solid {KENAR}; }}
        .kat-dugme {{
            background: transparent; background-image: none; border: none;
            box-shadow: none; border-radius: 6px; padding: 8px 14px;
            margin: 1px 8px; color: {METIN_SOFT}; min-height: 0;
        }}
        .kat-dugme label {{ color: {METIN_SOFT}; font-weight: 600; }}
        .kat-dugme:hover {{ background-color: {KART_USTU}; }}
        .kat-dugme:checked {{ background-color: {ACCENT}; }}
        .kat-dugme:checked label {{ color: white; }}
        .uyg-satiri {{
            background-color: {KART}; border: 1px solid {KENAR};
            border-radius: 7px; padding: 10px 14px;
        }}
        .uyg-satiri:hover {{ background-color: {KART_USTU}; }}
        .uyg-ad {{ font-size: 14px; font-weight: 700; }}
        .uyg-ozet {{ color: {METIN_SOFT}; font-size: 12px; }}
        .rozet {{ font-size: 11px; }}
        .rozet-kurulu {{ color: {YESIL}; font-weight: 700; }}
        button.kur-dugme {{
            background: {ACCENT}; background-image: none; border: none;
            box-shadow: none; border-radius: 6px; padding: 6px 20px;
            color: white; font-weight: 700; min-height: 0;
        }}
        button.kur-dugme:hover {{ background: {KUR_HOVER}; }}
        button.kaldir-dugme {{
            background: transparent; background-image: none;
            border: 1px solid {KENAR}; box-shadow: none; border-radius: 6px;
            padding: 6px 18px; color: {METIN_SOFT}; min-height: 0;
        }}
        button.kaldir-dugme:hover {{ border-color: {KIRMIZI}; color: {KIRMIZI}; }}
        .yenile-dugme {{
            background: transparent; background-image: none;
            border: 1px solid {KENAR}; box-shadow: none; border-radius: 7px;
            padding: 6px 14px; color: {METIN_SOFT}; min-height: 0;
        }}
        .yenile-dugme:hover {{ background-color: {KART_USTU}; }}
        .bos-durum {{ color: {METIN_SOFT}; font-size: 14px; }}
        .sayac {{ color: {METIN_SOFT}; font-size: 12px; }}
        .hakkinda {{
            background-color: {KART}; border-top: 1px solid {KENAR};
            padding: 12px 16px;
        }}
        .hakkinda-baslik {{ font-size: 13px; font-weight: 700;
            color: {METIN_RENK}; }}
        .hakkinda-satir {{ font-size: 11px; color: {METIN_SOFT}; }}
        .hakkinda-mesaj {{ font-size: 11px; font-style: italic;
            color: {ACCENT}; }}
        .hakkinda-surum {{ font-size: 10px; color: {METIN_SOFT};
            opacity: 0.7; }}
        .hakkinda button {{ padding: 0 2px; margin: 0; min-height: 0;
            background: none; border: none; box-shadow: none; }}
        .hakkinda button label {{ font-size: 11px; }}
        .islem-baslik {{ font-weight: 700; }}
        .islem-ok {{ color: {YESIL}; }}
        .islem-hata {{ color: {KIRMIZI}; }}
        textview {{ background-color: {ZEMIN}; color: {METIN_SOFT};
                    padding: 8px; }}
        textview text {{ background-color: {ZEMIN}; }}
        """
        self.provider = Gtk.CssProvider()
        self.provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.connect("destroy", self._yok_edildi)

    def _yok_edildi(self, _w):
        try:
            Gtk.StyleContext.remove_provider_for_screen(
                Gdk.Screen.get_default(), self.provider)
        except Exception:  # noqa: BLE001
            pass
        Gtk.main_quit()

    # -- arayüz (dil değişince tümüyle yeniden kurulur) ----------------------
    def _insa(self):
        for c in self.kok.get_children():
            self.kok.remove(c)
        self.set_title(M("baslik"))
        self.kok.pack_start(self._baslik_cubugu(), False, False, 0)
        govde = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.kok.pack_start(govde, True, True, 0)
        govde.pack_start(self._kenar_cubugu(), False, False, 0)
        govde.pack_start(self._liste_alani(), True, True, 0)
        self.listeyi_kur()
        self.kok.show_all()

    # -- başlık çubuğu -------------------------------------------------------
    def _baslik_cubugu(self):
        # Başlık bir "ada" (yuvarlak köşeli kart): dış kenar boşluklarıyla
        # pencereden ayrılır, iç padding (bkz. .ada) ile yazı ve düğme
        # adanın kenarına yapışmaz.
        cubuk = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        cubuk.get_style_context().add_class("ada")
        cubuk.set_margin_top(10); cubuk.set_margin_bottom(4)
        cubuk.set_margin_start(10); cubuk.set_margin_end(10)

        # Logo baslikta DEGIL, pencere ikonunda (bkz. __init__).
        baslik = Gtk.Label(label=M("baslik"), xalign=0)
        baslik.get_style_context().add_class("uygulama-basligi")
        cubuk.pack_start(baslik, False, False, 0)

        self.arama_girisi = Gtk.SearchEntry()
        self.arama_girisi.get_style_context().add_class("arama")
        self.arama_girisi.set_placeholder_text(M("ara"))
        if self.arama:
            self.arama_girisi.set_text(self.arama)
        self.arama_girisi.connect("search-changed", self._arama_degisti)
        cubuk.pack_start(self.arama_girisi, True, True, 0)

        cubuk.pack_start(self._dil_secici(), False, False, 0)

        yenile = Gtk.Button(label=M("yenile"))
        yenile.get_style_context().add_class("yenile-dugme")
        yenile.connect("clicked", self._depoyu_yenile)
        cubuk.pack_start(yenile, False, False, 0)
        return cubuk

    def _dil_secici(self):
        kutu = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        kutu.get_style_context().add_class("linked")
        kutu.get_style_context().add_class("dil-secici")
        kutu.set_valign(Gtk.Align.CENTER)
        self.dil_tr = Gtk.RadioButton.new_with_label(None, "TR")
        self.dil_en = Gtk.RadioButton.new_with_label_from_widget(self.dil_tr, "EN")
        for d in (self.dil_tr, self.dil_en):
            d.set_mode(False)
        (self.dil_tr if DIL == "tr" else self.dil_en).set_active(True)
        self.dil_tr.connect("toggled", self._dil_degis, "tr")
        self.dil_en.connect("toggled", self._dil_degis, "en")
        kutu.pack_start(self.dil_tr, False, False, 0)
        kutu.pack_start(self.dil_en, False, False, 0)
        return kutu

    def _dil_degis(self, dugme, yeni_dil):
        global DIL
        if not dugme.get_active() or yeni_dil == DIL:
            return
        DIL = yeni_dil
        self._insa()

    # -- kenar çubuğu: kategoriler (kaydırılır) + Hakkında (altta sabit) -----
    def _kenar_cubugu(self):
        dis = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        dis.get_style_context().add_class("kenar")
        dis.set_size_request(226, -1)

        kaydir = Gtk.ScrolledWindow()
        kaydir.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        kutu.set_margin_top(10); kutu.set_margin_bottom(10)
        kaydir.add(kutu)

        self.kat_dugmeleri = {}
        ilk = Gtk.RadioButton.new_with_label(None, M("tumu"))
        self._kat_dugme_bicimle(ilk, None)
        kutu.pack_start(ilk, False, False, 0)

        for kat in self.kategoriler:
            d = Gtk.RadioButton.new_with_label_from_widget(ilk, metin(kat["ad"]))
            self._kat_dugme_bicimle(d, kat["id"])
            kutu.pack_start(d, False, False, 0)

        # önceki seçimi koru
        sec = self.kat_dugmeleri.get(self.aktif_kategori)
        if sec:
            sec.set_active(True)

        dis.pack_start(kaydir, True, True, 0)
        dis.pack_start(self._hakkinda_kutusu(), False, False, 0)
        return dis

    def _kat_dugme_bicimle(self, dugme, kat_id):
        dugme.set_mode(False)
        dugme.set_halign(Gtk.Align.FILL)
        for c in dugme.get_children():
            if isinstance(c, Gtk.Label):
                c.set_xalign(0)
        dugme.get_style_context().add_class("kat-dugme")
        dugme.connect("toggled", self._kategori_secildi, kat_id)
        self.kat_dugmeleri[kat_id] = dugme

    def _hakkinda_kutusu(self):
        # Minimal: baslik yok. Tek satir kimlik + tek satir bağlantılar +
        # imza mesaji + surum.
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        kutu.get_style_context().add_class("hakkinda")

        bas = Gtk.Label(label=M("hakkinda_baslik"), xalign=0)
        bas.get_style_context().add_class("hakkinda-baslik")
        bas.set_margin_bottom(4)
        kutu.pack_start(bas, False, False, 0)

        yapildi = Gtk.Label(label=M("hakkinda_yapildi"), xalign=0)
        yapildi.get_style_context().add_class("hakkinda-satir")
        yapildi.set_line_wrap(True)
        kutu.pack_start(yapildi, False, False, 0)

        baglantilar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        baglantilar.set_margin_top(4)
        gh = Gtk.LinkButton.new_with_label(GITHUB_URL, M("hakkinda_github"))
        ayrac = Gtk.Label(label="·")
        ayrac.get_style_context().add_class("hakkinda-satir")
        web = Gtk.LinkButton.new_with_label(WEB_URL, M("hakkinda_web"))
        for b in (gh, web):
            b.set_halign(Gtk.Align.START)
            b.get_style_context().add_class("hakkinda-satir")
        baglantilar.pack_start(gh, False, False, 0)
        baglantilar.pack_start(ayrac, False, False, 0)
        baglantilar.pack_start(web, False, False, 0)
        kutu.pack_start(baglantilar, False, False, 0)

        mesaj = Gtk.Label(label=M("hakkinda_mesaj"), xalign=0)
        mesaj.get_style_context().add_class("hakkinda-mesaj")
        mesaj.set_line_wrap(True)
        mesaj.set_margin_top(8)
        kutu.pack_start(mesaj, False, False, 0)

        surum = Gtk.Label(label="v" + APP_VERSION, xalign=0)
        surum.get_style_context().add_class("hakkinda-surum")
        surum.set_margin_top(6)
        kutu.pack_start(surum, False, False, 0)
        return kutu

    # -- liste alanı ---------------------------------------------------------
    def _liste_alani(self):
        kaydir = Gtk.ScrolledWindow()
        kaydir.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.liste_kutusu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.liste_kutusu.set_margin_top(14); self.liste_kutusu.set_margin_bottom(14)
        self.liste_kutusu.set_margin_start(16); self.liste_kutusu.set_margin_end(16)
        kaydir.add(self.liste_kutusu)
        return kaydir

    def _gorunur_uygulamalar(self):
        sonuc = []
        for u in self.uygulamalar:
            if self.aktif_kategori and u.get("kategori") != self.aktif_kategori:
                continue
            if self.arama:
                havuz = " ".join([
                    metin(u.get("ad", "")), u.get("paket", ""),
                    metin(u.get("ozet", "")), metin(u.get("aciklama", "")),
                ]).lower()
                if self.arama not in havuz:
                    continue
            sonuc.append(u)
        sonuc.sort(key=lambda u: metin(u.get("ad", "")).lower())
        return sonuc

    def listeyi_kur(self):
        for c in self.liste_kutusu.get_children():
            self.liste_kutusu.remove(c)
        self.satirlar = []

        uygulamalar = self._gorunur_uygulamalar()
        if not uygulamalar:
            bos = Gtk.Label()
            bos.get_style_context().add_class("bos-durum")
            bos.set_text(M("sonuc_yok") if self.arama else M("bos_kategori"))
            bos.set_margin_top(40)
            self.liste_kutusu.pack_start(bos, False, False, 0)
            self.liste_kutusu.show_all()
            return

        sayac = Gtk.Label(label=M("uyg_sayisi", n=len(uygulamalar)), xalign=0)
        sayac.get_style_context().add_class("sayac")
        self.liste_kutusu.pack_start(sayac, False, False, 0)

        for u in uygulamalar:
            satir = UygulamaSatiri(
                u, u.get("paket") in self.kurulu, self._eylem_istendi,
                as_yol=self.as_harita.get(u.get("paket")))
            self.satirlar.append(satir)
            self.liste_kutusu.pack_start(satir, False, False, 0)
        self.liste_kutusu.show_all()

    # -- olaylar -------------------------------------------------------------
    def _kategori_secildi(self, dugme, kat_id):
        if not dugme.get_active():
            return
        self.aktif_kategori = kat_id
        self.listeyi_kur()

    def _arama_degisti(self, giris):
        self.arama = giris.get_text().strip().lower()
        self.listeyi_kur()

    def _eylem_istendi(self, satir, eylem):
        komut = apt_komutu(eylem, satir.uygulama["paket"])
        if komut is None:
            self._pkexec_yok_uyar(eylem, satir.uygulama["paket"])
            return
        satir.mesgul(M("kaldiriliyor") if eylem == "remove" else M("kuruluyor"))
        baslik = "%s — %s" % (metin(satir.uygulama["ad"]),
                              M("kaldiriliyor") if eylem == "remove"
                              else M("kuruluyor"))

        def bitince(basarili):
            if basarili:
                if eylem == "install":
                    self.kurulu.add(satir.uygulama["paket"])
                else:
                    self.kurulu.discard(satir.uygulama["paket"])
            satir.durumu_uygula(satir.uygulama["paket"] in self.kurulu)

        IslemPenceresi(self, baslik, komut, bitince).baslat()

    def _depoyu_yenile(self, _dugme):
        komut = apt_yenile_komutu()
        if komut is None:
            self._pkexec_yok_uyar("update", "apt")
            return
        # Yenileme bitince pencere 3 sn sonra kendiliğinden kapansın.
        IslemPenceresi(self, M("yenileniyor"), komut, None,
                       otomatik_kapan=True).baslat()

    def _pkexec_yok_uyar(self, eylem, paket):
        if eylem == "update":
            komut_metni = "sudo apt-get update"
        else:
            komut_metni = "sudo apt-get %s -y %s" % (eylem, paket)
        d = Gtk.MessageDialog(
            transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.CLOSE, text=M("pkexec_yok_baslik"))
        d.format_secondary_text(M("pkexec_yok") + "\n\n" + komut_metni)
        d.run()
        d.destroy()


def katalogu_oku():
    with open(KATALOG_YOLU, encoding="utf-8") as f:
        return json.load(f)


def main():
    try:
        katalog = katalogu_oku()
    except Exception as exc:  # noqa: BLE001
        print(f"Katalog okunamadi ({KATALOG_YOLU}): {exc}", file=sys.stderr)
        sys.exit(1)
    pen = MagazaPenceresi(katalog)
    pen.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
