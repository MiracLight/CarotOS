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

Yetki gereken işlemler (kur/kaldır/güncelle/yenile) `pkexec carotos-magaza-apt`
(root yardımcısı; yoksa doğrudan `pkexec apt-get`) ile yapılır; pkexec yoksa elle
çalıştırılacak komut gösterilir. Tek örnek çalışır (Gtk.Application).
"""
import base64
import json
import locale
import os
import re
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, Pango  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORTAK = os.path.join(os.path.dirname(BASE_DIR), "ortak")
for _y in (ORTAK, BASE_DIR):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import dil  # noqa: E402  (ortak dil katmani: ortak/dil.py)
import tema  # noqa: E402
from yetkili import sistem_yolu, temiz_ortam  # noqa: E402

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
    "gizle": {"tr": "Gizle", "en": "Hide"},
    "guvenli_iptal": {"tr": "Güvenli iptal", "en": "Safe cancel"},
    "guvenli_iptal_suruyor": {"tr": "İndirme durduruluyor…", "en": "Stopping the download…"},
    "guvenli_iptal_bitti": {"tr": "İptal edildi, sistemde değişiklik yapılmadı.",
                            "en": "Cancelled. No changes were made to the system."},
    "tamamlandi": {"tr": "Tamamlandı.", "en": "Done."},
    "hata_olustu": {"tr": "İşlem başarısız oldu.", "en": "The operation failed."},
    "iptal_edilemez": {
        "tr": "Yetki verildi; işlem artık güvenle durdurulamaz. Pencereyi kapatabilirsiniz, "
              "işlem arka planda sürer ve bitince sonuç Mağaza'da görünür.",
        "en": "Permission was granted; the operation can no longer be stopped safely. You can "
              "close this window: it keeps running in the background and the Store shows the "
              "result when it finishes."},
    "kilit_mesgul": {
        "tr": "Başka bir paket işlemi sürüyor (başka bir Mağaza penceresi ya da sistem "
              "güncellemesi). O bitince yeniden deneyin.",
        "en": "Another package operation is running (another Store window or a system "
              "update). Try again when it finishes."},
    "dpkg_yarim": {
        "tr": "Önceki bir paket işlemi yarıda kalmış. Terminalde "
              "'sudo dpkg --configure -a' komutunu çalıştırıp yeniden deneyin.",
        "en": "A previous package operation was interrupted. Run "
              "'sudo dpkg --configure -a' in a terminal, then try again."},
    "kaldir_onay_baslik": {"tr": "{ad} kaldırılsın mı?", "en": "Remove {ad}?"},
    "kaldir_liste": {"tr": "Şu paketler kaldırılacak:", "en": "These packages will be removed:"},
    "kaldir_hesaplanamadi": {
        "tr": "Birlikte kaldırılacak paketler hesaplanamadı; apt, bu pakete bağlı başka "
              "paketleri de kaldırabilir.",
        "en": "Could not work out which other packages would be removed; apt may also "
              "remove packages that depend on this one."},
    "kaldir_korunan": {
        "tr": "CarotOS bu paketleri kullanıyor:",
        "en": "CarotOS uses these packages:"},
    "kaldir_anladim": {"tr": "Anladım, yine de kaldır", "en": "I understand, remove anyway"},
    "kaldir_temel": {
        "tr": "Bu işlem sistemin temel paketlerini de kaldırırdı; apt buna izin vermez.",
        "en": "This would also remove essential system packages; apt does not allow it."},
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
    dpkg_query = sistem_yolu("dpkg-query")
    if not dpkg_query:
        return set()
    try:
        r = subprocess.run([dpkg_query, "-W", "-f=${Package} ${Status}\n"],
                           capture_output=True, text=True, errors="replace", timeout=20,
                           stdin=subprocess.DEVNULL, env=temiz_ortam())
    except Exception:  # noqa: BLE001
        return set()
    return {s.split(" ", 1)[0] for s in r.stdout.splitlines()
            if s.endswith("install ok installed")}


def guncellenebilir_paketler():
    """`apt list --upgradable` çıktısından güncellenebilir paket adları."""
    apt = sistem_yolu("apt")
    if not apt:
        return set()
    try:
        r = subprocess.run([apt, "list", "--upgradable"],
                           capture_output=True, text=True, errors="replace", timeout=30,
                           stdin=subprocess.DEVNULL, env=temiz_ortam())
    except Exception:  # noqa: BLE001
        return set()
    adlar = set()
    for satir in r.stdout.splitlines():
        if "/" in satir and "upgradable" in satir:
            adlar.add(satir.split("/", 1)[0].strip())
    return adlar


# Debian paket adi bicimi (Policy 5.6.1). Root'a giden her ad bu bicime uymali (M-05):
# '-o', './x.deb', 'paket=surum', 'paket/depo' gibi apt'in baska anlam verdigi yazimlar reddedilir.
PAKET_ADI = re.compile(r"[a-z0-9][a-z0-9+.-]+\Z")
APT_EYLEMLERI = ("install", "remove", "upgrade", "update")


def paket_adi_gecerli(ad):
    return isinstance(ad, str) and bool(PAKET_ADI.match(ad))


def apt_komutu(eylem, *paketler, izinli=None):
    """pkexec ile root olarak calisacak apt-get komutu (liste; kabuk yok).

    eylem: install | remove | upgrade | update. Programlar yalnizca sistem dizinlerinden
    (M-04: kullanicinin PATH'indeki sahte pkexec/env/apt-get root olarak calismasin).
    Paket adlari bicim denetiminden gecer, verilirse `izinli` (katalog) icinde olmalidir;
    adlar '--' ardindan verilir. Gecersiz eylem ya da adda ValueError. Gerekli
    programlardan biri yoksa None (arayuz elle calistirilacak komutu gosterir)."""
    if eylem not in APT_EYLEMLERI:
        raise ValueError("gecersiz apt eylemi: %r" % (eylem,))
    if eylem in ("install", "remove"):
        if not paketler:
            raise ValueError("paket adi verilmedi")
        for ad in paketler:
            if not paket_adi_gecerli(ad):
                raise ValueError("gecersiz paket adi: %r" % (ad,))
            if izinli is not None and ad not in izinli:
                raise ValueError("katalogda olmayan paket: %r" % (ad,))
    # upgrade/update paket adi almaz: verilse de root komutuna hic eklenmez
    pkexec, env, apt_get = sistem_yolu("pkexec"), sistem_yolu("env"), sistem_yolu("apt-get")
    if not (pkexec and env and apt_get):
        return None
    # LC_ALL=C: pkexec yerel ayari korur; Turkce'de bazi paketlerin kurulum
    # betikleri bozulur (rkhunter: tr '[:upper:]' '[:lower:]' "I" harfini
    # kucultmez, betik 10 koduyla duser, paket yari kurulu kalir). Bu yuzden
    # apt dil ayarindan bagimsiz calistirilir (cikti Ingilizce olur; kilit iletisi
    # de bu sayede sabit metinle taninir).
    ortam = [env, "DEBIAN_FRONTEND=noninteractive", "LC_ALL=C", "LANGUAGE=C"]
    # Baska bir apt/dpkg kilidi tutuyorsa hemen dusme, bir sure bekle (M-06)
    kilit = ["-o", "DPkg::Lock::Timeout=60"]
    if eylem == "update":
        return [pkexec, *ortam, apt_get, *kilit, "update"]
    # stdin yok: dpkg degismis bir yapilandirma dosyasi icin soru sorarsa EOF alip paketi
    # yari yapilandirilmis birakmasin; yerel (CarotOS'un degistirdigi) dosya korunur.
    conf = ["-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold"]
    if eylem == "upgrade":
        return [pkexec, *ortam, apt_get, *kilit, *conf, "upgrade", "-y"]
    return [pkexec, *ortam, apt_get, *kilit, *conf, eylem, "-y", "--", *paketler]


# --- Root yardimcisi (M-02: guvenli iptal) -----------------------------------
# /usr/sbin/carotos-magaza-apt indirme asamasinda stdin'den "iptal" alir ve apt'i
# durdurur; faz satirlariyla Magaza'ya hangi asamada oldugunu soyler.
YARDIMCI = "/usr/sbin/carotos-magaza-apt"
FAZ_ISARETI = "@@CAROTOS-FAZ "
IPTAL_ISARETI = "@@CAROTOS-IPTAL"
IPTAL_KODU = 75


def yardimci_komutu(eylem, *paketler, yardimci=YARDIMCI):
    """Yardimci betik kuruluysa `pkexec <yardimci> <eylem> -- <paketler>`; yoksa None
    (eski kurulum: dogrudan apt_komutu yolu kullanilir, guvenli iptal sunulmaz).
    Adlar once apt_komutu ile ayni kurallarla denetlenmis olmalidir; burada da bicim
    denetlenir (ValueError)."""
    if eylem not in APT_EYLEMLERI:
        raise ValueError("gecersiz apt eylemi: %r" % (eylem,))
    if eylem in ("upgrade", "update"):
        paketler = ()
    for ad in paketler:
        if not paket_adi_gecerli(ad):
            raise ValueError("gecersiz paket adi: %r" % (ad,))
    pkexec = sistem_yolu("pkexec")
    if not pkexec or not os.path.isfile(yardimci) or not os.access(yardimci, os.X_OK):
        return None
    return [pkexec, yardimci, eylem, *(("--", *paketler) if paketler else ())]


def kilit_iletisi(cikti):
    """Basarisiz apt ciktisinda kilit/yarim dpkg nedenini tanir: metin anahtari ya da None.
    apt LC_ALL=C ile calistigi icin iletiler Ingilizcedir."""
    if not cikti:
        return None
    if "dpkg was interrupted" in cikti:
        return "dpkg_yarim"
    if re.search(r"Could not get lock|Unable to acquire the dpkg frontend lock|"
                 r"Unable to lock (the )?(administration |download |list )?directory", cikti):
        return "kilit_mesgul"
    return None


# --- Kaldirma onayi (M-03) ---------------------------------------------------
# CarotOS'un kendi uygulamalarinin dayandigi paketler. Kaldirma yasak DEGIL (karar: DENETIM.md
# 2.5); onay penceresi hangi CarotOS uygulamasinin bozulacagini adiyla soyler ve ek onay ister.
_ARAC_ETKI = {
    # paket: (Guvenlik Paneli araci mi, Poligon gorevi var mi)
    "nmap": (True, True), "tcpdump": (True, False), "tshark": (True, True),
    "john": (True, True), "hydra": (True, True), "sqlmap": (True, True),
    "aircrack-ng": (True, False), "nikto": (True, False),
}


def _arac_etkisi(paket, panel, poligon):
    tr = ["CarotOS Güvenlik Paneli'ndeki %s aracı" % paket] if panel else []
    en = ["the %s tool in CarotOS Security Panel" % paket] if panel else []
    if poligon:
        tr.append("CarotOS Poligon'daki %s görevleri" % paket)
        en.append("the CarotOS Poligon %s tasks" % paket)
    return {
        "tr": "%s kaldırılırsa %s çalışmaz; CarotOS Former'daki %s dersinin alıştırmaları "
              "yapılamaz." % (paket, " ve ".join(tr), paket),
        "en": "Without %s, %s stop working and the CarotOS Former %s lesson exercises "
              "cannot be done." % (paket, " and ".join(en), paket),
    }


KORUNAN = {
    "clamav": {
        "tr": "clamav kaldırılırsa Carotene ve CarotOS USB Denetimi virüs taraması yapamaz; "
              "CarotOS Sistem Sağlığı'nın virüs denetimi çalışmaz.",
        "en": "Without clamav, Carotene and CarotOS USB Check cannot scan for viruses and "
              "the CarotOS System Health virus check does not run."},
    "clamav-freshclam": {
        "tr": "clamav-freshclam kaldırılırsa Carotene virüs tanımlarını güncelleyemez.",
        "en": "Without clamav-freshclam, Carotene cannot update its virus definitions."},
    "rkhunter": {
        "tr": "rkhunter kaldırılırsa CarotOS Sistem Sağlığı'nın rootkit denetimi çalışmaz.",
        "en": "Without rkhunter, the CarotOS System Health rootkit check does not run."},
    "ufw": {
        "tr": "ufw kaldırılırsa güvenlik duvarı kalmaz; CarotPot'un güvenlik duvarı kuralları "
              "ve CarotOS Sistem Sağlığı'nın güvenlik duvarı denetimi çalışmaz.",
        "en": "Without ufw there is no firewall; CarotPot's firewall rules and the CarotOS "
              "System Health firewall check do not work."},
    "firefox-esr": {
        "tr": "firefox-esr sistemdeki tek internet tarayıcısıdır; kaldırılırsa CarotOS "
              "uygulamalarındaki internet bağlantıları açılmaz.",
        "en": "firefox-esr is the only web browser on the system; without it, web links in "
              "CarotOS apps do not open."},
    "python3-gi": {
        "tr": "python3-gi kaldırılırsa CarotOS uygulamalarının hiçbiri açılmaz.",
        "en": "Without python3-gi, none of the CarotOS apps open."},
    "gir1.2-gtk-3.0": {
        "tr": "gir1.2-gtk-3.0 kaldırılırsa CarotOS uygulamalarının hiçbiri açılmaz.",
        "en": "Without gir1.2-gtk-3.0, none of the CarotOS apps open."},
    "pkexec": {
        "tr": "pkexec kaldırılırsa CarotOS Mağaza ve yönetici yetkisi isteyen CarotOS "
              "işlemleri çalışmaz.",
        "en": "Without pkexec, CarotOS Store and CarotOS actions that need administrator "
              "rights do not work."},
    "polkitd": {
        "tr": "polkitd kaldırılırsa CarotOS Mağaza ve yönetici yetkisi isteyen CarotOS "
              "işlemleri çalışmaz.",
        "en": "Without polkitd, CarotOS Store and CarotOS actions that need administrator "
              "rights do not work."},
}
KORUNAN.update({p: _arac_etkisi(p, *e) for p, e in _ARAC_ETKI.items()})


def kaldirma_simulasyonu_coz(kod, cikti):
    """`apt-get -s remove` ciktisi -> {"paketler": [...], "temel": bool}; basarisizsa None."""
    if kod != 0:
        return None
    paketler = []
    for satir in (cikti or "").splitlines():
        if satir.startswith("Remv "):
            ad = satir.split()[1].split(":", 1)[0] if len(satir.split()) > 1 else ""
            if paket_adi_gecerli(ad) and ad not in paketler:
                paketler.append(ad)
    temel = "essential packages will be removed" in (cikti or "")
    return {"paketler": paketler, "temel": temel}


def kaldirma_simulasyonu(paket):
    """Kullanici yetkisiyle (root gerekmez) `apt-get -s remove`; None: hesaplanamadi."""
    apt_get = sistem_yolu("apt-get")
    if not apt_get or not paket_adi_gecerli(paket):
        return None
    try:
        r = subprocess.run([apt_get, "-s", "remove", "--", paket],
                           capture_output=True, text=True, errors="replace", timeout=60,
                           stdin=subprocess.DEVNULL, env=temiz_ortam())
    except (OSError, subprocess.SubprocessError):
        return None
    return kaldirma_simulasyonu_coz(r.returncode, r.stdout + "\n" + r.stderr)


def korunan_etkiler(paketler, dil_kodu):
    """Kaldirilacak paketlerden CarotOS'un dayandiklari icin, secili dilde etki cumleleri."""
    return [dil.metin(KORUNAN[p], dil_kodu) for p in paketler if p in KORUNAN]


# --- İşlem penceresi (apt çıktısı) ------------------------------------------
class IslemPenceresi(Gtk.Window):
    def __init__(self, ebeveyn, baslik, komut, bitince, otomatik_kapan=False, yardimci=False):
        super().__init__(title=baslik)
        # yardimci: komut carotos-magaza-apt'tir; faz satirlari okunur, indirmede guvenli
        # iptal sunulur (M-02). Faz satiri gelene kadar pkexec parola bekliyordur.
        self.yardimci = yardimci
        self.faz = None              # None (parola bekleniyor) | "indirme" | "kurulum"
        self.guvenli_iptal_istendi = False
        self._guvenli_iptal_oldu = False
        self.set_transient_for(ebeveyn)
        # Modal DEGIL: kurulum surerken magaza gezilebilir, sepete urun eklenebilir.
        # Ikinci bir apt islemi MagazaPenceresi.mesgul ile engellenir.
        self.set_modal(False)
        self.set_default_size(660, 440)
        self.komut = komut
        self.bitince = bitince
        self.otomatik_kapan = otomatik_kapan
        self.surec = None
        self.iptal_edildi = False
        self.durdurulamaz = False    # pkexec yetkiyi aldi: root surece sinyal gonderilemez (M-02)
        self.bitti_mi = False
        self._yok_edildi = False
        self._bekleyen = []          # okuyucu is parcaciginin biriktirdigi satirlar
        self._cikti_sonu = ""        # kilit iletisini tanimak icin ciktinin son kismi (M-06)
        self._kilit = threading.Lock()
        self._bosaltma_sayisi = 0    # test icin: arayuze kac kez yazildi
        self._zamanlayici = None
        self.connect("delete-event", self._kapatiliyor)
        self.connect("destroy", self._yok_ediliyor)

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
        self._son_isaret = self.tampon.create_mark("son", self.tampon.get_end_iter(), False)
        kaydir.add(self.gorunum)
        dis.pack_start(kaydir, True, True, 0)

        alt = Gtk.Box(spacing=8)
        for k in ("top", "bottom", "start", "end"):
            getattr(alt, f"set_margin_{k}")(12)
        alt.set_halign(Gtk.Align.END)
        self.guvenli_dugme = tema.dugme(M("guvenli_iptal"), None, self._guvenli_iptal)
        self.gizle_dugme = tema.dugme(M("gizle"), None, self.hide)
        self.kapat_dugme = tema.dugme(M("iptal"), None, self._kapat)
        for d in (self.guvenli_dugme, self.gizle_dugme):
            d.set_no_show_all(True)  # yalnizca parola girildikten sonra gorunur
            alt.pack_start(d, False, False, 0)
        alt.pack_start(self.kapat_dugme, False, False, 0)
        dis.pack_start(alt, False, False, 0)

    def baslat(self):
        self.show_all()
        # apt yuzlerce satir/sn yazabilir: satir basina arayuz guncellemek ana donguyu
        # bogar ("hicbir sey tiklanmiyor"). Satirlar biriktirilir, 150 ms'de bir yazilir.
        self._zamanlayici = GLib.timeout_add(150, self._bosalt)
        threading.Thread(target=self._calis, daemon=True).start()

    SATIR_SINIRI = 10000         # tamponda tutulan en fazla satir (M-07)
    _OKUMA_PARCASI = 65536       # satir sonu gelmeyen dev ciktida tek okumanin siniri

    def _ekle(self, metin):
        with self._kilit:
            self._bekleyen.append(metin)
            self._cikti_sonu = (self._cikti_sonu + metin)[-8192:]

    def _calis(self):
        """apt'i calistirir ve ciktisini sonuna kadar okur (M-01).

        Cikti bayt olarak okunup 'replace' ile cozulur: UTF-8 olmayan bir bayt okuyucuyu
        olduremez. Okuyucu ne olursa olsun boruyu bosaltmayi surdurur ve wait() cagirir;
        boylece root apt boru dolunca takilip dpkg kilidini tutmaz, _bitti yalnizca surec
        gercekten bittiginde gelir."""
        try:
            # Dogrudan apt'e stdin verilmez (conffile sorusu EOF alip takilmasin). Yardimcinin
            # stdin'i yalnizca "iptal" satiri icindir; apt'i o da stdin=DEVNULL ile calistirir.
            girdi = subprocess.PIPE if self.yardimci else subprocess.DEVNULL
            self.surec = subprocess.Popen(
                self.komut, stdin=girdi,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as exc:  # noqa: BLE001
            self._ekle(f"\n[hata] {exc}\n")
            GLib.idle_add(self._bitti, 1)
            return
        if self.iptal_edildi:        # Iptal, surec baslamadan once basildi
            try:
                self.surec.terminate()
            except OSError:
                pass
        akis = self.surec.stdout
        try:
            for satir in iter(lambda: akis.readline(self._OKUMA_PARCASI), b""):
                metin_ = satir.decode("utf-8", "replace")
                if self.yardimci and metin_.startswith("@@CAROTOS-"):
                    isaret = metin_.strip()
                    if isaret.startswith(FAZ_ISARETI):
                        GLib.idle_add(self._faz_degisti, isaret[len(FAZ_ISARETI):])
                        continue
                    if isaret == IPTAL_ISARETI:
                        self._guvenli_iptal_oldu = True
                        continue
                self._ekle(metin_)
        except Exception as exc:  # noqa: BLE001
            self._ekle(f"\n[hata] {exc}\n")
            try:                     # okumayi birak ama boruyu bosaltmayi surdur
                while akis.read(self._OKUMA_PARCASI):
                    pass
            except Exception:  # noqa: BLE001
                pass
        try:
            kod = self.surec.wait()
        except Exception:  # noqa: BLE001
            kod = 1
        for boru in (akis, self.surec.stdin):
            try:
                if boru is not None:
                    boru.close()
            except OSError:
                pass
        GLib.idle_add(self._bitti, kod)

    def _faz_degisti(self, faz):
        """Yardimci faz bildirdi: parola girildi, pkexec artik root (M-02 karari).
        indirme: Gizle + Guvenli iptal; kurulum: yalnizca Gizle."""
        if self.bitti_mi or self._yok_edildi:
            return False
        self.faz = faz
        self.durdurulamaz = True     # root surece sinyal gonderilemez; Iptal yerine Gizle
        self.kapat_dugme.hide()
        self.gizle_dugme.show()
        if faz == "indirme" and not self.guvenli_iptal_istendi:
            self.guvenli_dugme.show()
        else:
            self.guvenli_dugme.hide()
            if self.guvenli_iptal_istendi:   # iptal gec kaldi: indirme bitmisti
                self.durum.set_text(self.get_title() or "")
        return False

    def _guvenli_iptal(self):
        """Yalnizca indirme asamasinda: yardimciya "iptal" yazar; o apt'i durdurur ve
        sistemde degisiklik yapilmadan cikar. Kurulum basladiysa hicbir sey yapmaz."""
        if self.faz != "indirme" or self.guvenli_iptal_istendi or not self.calisiyor():
            return
        stdin = getattr(self.surec, "stdin", None)
        if stdin is None:
            return
        try:
            stdin.write(b"iptal\n")
            stdin.flush()
        except (OSError, ValueError):
            return
        self.guvenli_iptal_istendi = True
        self.guvenli_dugme.set_sensitive(False)
        self.durum.set_text(M("guvenli_iptal_suruyor"))

    def _bosalt(self):
        """Biriken satirlari tek seferde tampona yazar ve bir kez kaydirir."""
        with self._kilit:
            parca, self._bekleyen = "".join(self._bekleyen), []
        if parca and not self._yok_edildi:
            self._bosaltma_sayisi += 1
            self.tampon.insert(self.tampon.get_end_iter(), parca)
            fazla = self.tampon.get_line_count() - self.SATIR_SINIRI
            if fazla > 0:            # en eski satirlar atilir
                self.tampon.delete(self.tampon.get_start_iter(),
                                   self.tampon.get_iter_at_line(fazla))
            self.tampon.move_mark(self._son_isaret, self.tampon.get_end_iter())
            self.gorunum.scroll_mark_onscreen(self._son_isaret)
        return self._zamanlayici is not None

    def _bitti(self, kod):
        self.bitti_mi = True
        if self._zamanlayici is not None:
            GLib.source_remove(self._zamanlayici)
            self._zamanlayici = None
        guvenli = self.yardimci and self._guvenli_iptal_oldu and kod == IPTAL_KODU
        if guvenli:
            self.iptal_edildi = True     # sistemde degisiklik yok; basarisizlik sayilmaz
        basarili = (kod == 0 and not self.iptal_edildi)
        if not self._yok_edildi:
            self._bosalt()
            self.spinner.stop()
            neden = None if basarili or guvenli else kilit_iletisi(self._cikti_sonu)
            if guvenli:
                self.durum.set_text(M("guvenli_iptal_bitti"))
            else:
                self.durum.get_style_context().add_class(
                    "basari-yazi" if basarili else "hata-yazi")
                self.durum.set_text(M(neden) if neden else
                                    M("tamamlandi") if basarili else M("hata_olustu"))
            if neden or guvenli:
                self.durum.set_ellipsize(Pango.EllipsizeMode.NONE)
                self.durum.set_line_wrap(True)
            self.guvenli_dugme.hide()
            self.gizle_dugme.hide()
            self.kapat_dugme.set_label(M("kapat"))
            self.kapat_dugme.show()
            if not basarili and not self.iptal_edildi and not self.get_visible():
                self.present()       # gizlenmis islem basarisiz bitti: kullanici gorsun
        if self.bitince:
            self.bitince(basarili)
        if basarili and self.otomatik_kapan:
            GLib.timeout_add_seconds(2, lambda: (not self._yok_edildi) and self.destroy())
        return False

    def calisiyor(self):
        return not self.bitti_mi and not self._yok_edildi

    def _kapat(self):
        """Iptal / Kapat dugmesi.

        pkexec yetki beklerken surec hala kullanicinindir: sinyal ulasir, islem gercekten
        iptal edilir. Yetki verildikten sonra apt root olarak calisir; kullanici sureci ona
        sinyal gonderemez (PermissionError) ve dpkg'yi yarida kesmek de guvenli olmazdi.
        O durumda islem 'iptal edildi' sayilmaz, pencere yok edilmez: durum dürüstce
        yazilir, sonraki tiklama pencereyi yalnizca gizler (M-02)."""
        if self.calisiyor():
            if self.durdurulamaz:
                self.hide()
                return
            if self.surec is None:
                self.iptal_edildi = True     # _calis surec acilir acilmaz sonlandirir
            elif self.surec.poll() is None:
                try:
                    self.surec.terminate()
                except PermissionError:
                    self._durdurulamaz_goster()
                    return
                except OSError:
                    pass
                else:
                    self.iptal_edildi = True
        self.destroy()

    def _durdurulamaz_goster(self):
        self.durdurulamaz = True
        self.durum.set_ellipsize(Pango.EllipsizeMode.NONE)
        self.durum.set_line_wrap(True)
        self.durum.set_text(M("iptal_edilemez"))
        self.kapat_dugme.hide()          # yetki verildi: Iptal yerine Gizle (M-02 karari)
        self.gizle_dugme.show()

    def _kapatiliyor(self, *_):
        """Pencere yoneticisinin x dugmesi: islem suruyorsa pencere yok edilmez, gizlenir;
        cikti kaybolmaz ve Magaza onu yeniden one getirebilir (M-02)."""
        if self.calisiyor():
            self.hide()
            return True
        return False

    def _yok_ediliyor(self, *_):
        self._yok_edildi = True
        if self._zamanlayici is not None:
            GLib.source_remove(self._zamanlayici)
            self._zamanlayici = None


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
        # root'a gidecek paket adlari yalnizca bu kumeden olabilir (M-05)
        self.katalog_adlari = frozenset(u.get("paket") for u in self.uygulamalar
                                        if paket_adi_gecerli(u.get("paket")))
        self._onay_bekliyor = False
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
        # Gtk.Application altinda pencere kapaninca uygulama kendiliginden biter (M-06);
        # eski Gtk.main dongusuyle calisiliyorsa (testler) dongu bitirilir.
        self.connect("destroy", lambda *_: Gtk.main_level() > 0 and Gtk.main_quit())
        self.connect("delete-event", self._kapanirken)

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
        self.dil_kutu = tema.AcilirSecim()
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
        # Her tus vurusunda 150+ satirlik listeyi yeniden kurmak yazmayi geciktirir: 250 ms bekle.
        if getattr(self, "_arama_zamani", None):
            GLib.source_remove(self._arama_zamani)
        self._arama_zamani = GLib.timeout_add(250, self._arama_uygula, giris)

    def _arama_uygula(self, giris):
        self._arama_zamani = None
        self.arama = giris.get_text().strip().lower()
        if self.arama:
            self.detay_app = None
            self.kabuk.baslik_ayarla(M("arama_basligi", s=giris.get_text().strip()),
                                     M("arama_alt"))
            self.kabuk.icerik(self._liste_sayfasi(self._suzulmus()))
        else:
            self.sayfa_secildi(self.aktif)
        return False

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
        if self.mesgul:
            self._mesgul_uyar()
            return
        if not self.sepet:
            return
        # yalnizca katalogdaki adlar root'a gider (M-05); bicimi apt_komutu ayrica denetler
        paketler = sorted(p for p in self.sepet if p in self.katalog_adlari)
        if not paketler:
            return
        try:
            komut = apt_komutu("install", *paketler)
        except ValueError as exc:
            print(f"[magaza] {exc}", file=sys.stderr)
            return
        if komut is None:
            self._pkexec_yok("install", " ".join(paketler))
            return
        self._mesgul_ayarla("install:sepet")

        def bitince(_basarili):
            # Paketlerden biri dusse (ornegin kurulum betigi hatasi) digerleri
            # kurulmus olabilir; gercek durum dpkg'den okunur (arka planda: dpkg-query
            # yavas makinede arayuzu dondurmasin). Kurulamayanlar sepette kalir.
            def oku_bitti(kurulu):
                self.kurulu = kurulu
                self.sepet -= self.kurulu
                self._mesgul_ayarla(None)
                self._sepet_guncelle()
                self._guncelleme_rozeti()
                if self.detay_app is not None:
                    self.detay_goster(self.detay_app)
                else:
                    self.sayfa_secildi(self.aktif)
                return False
            self._kurulu_oku(oku_bitti)
        self._islem_baslat(M("sepet_kuruluyor", n=len(paketler)), komut, bitince,
                           eylem="install", paketler=paketler)

    def _islem_baslat(self, baslik, komut, bitince, otomatik_kapan=False, eylem=None,
                      paketler=()):
        """komut: apt_komutu ciktisi (adlar denetlenmis). Root yardimcisi kuruluysa onun
        yerine `pkexec carotos-magaza-apt` kullanilir (guvenli iptal, M-02)."""
        yk = None
        if eylem is not None:
            try:
                yk = yardimci_komutu(eylem, *paketler)
            except ValueError:
                yk = None
        self.islem_penceresi = IslemPenceresi(self, baslik, yk or komut, bitince,
                                              otomatik_kapan, yardimci=yk is not None)
        self.islem_penceresi.baslat()

    def _kapanirken(self, *_):
        """Islem suruyorken pencere kapanirsa apt'in cikti borusu kopar ve paket yari kurulu
        kalabilir. Bu yuzden kapatma engellenir, islem penceresi one getirilir (Iptal orada)."""
        if self.mesgul:
            self._mesgul_uyar()
            return True
        return False

    def _mesgul_uyar(self):
        """Is suruyorken yeni bir islem istenirse calisan islemin penceresini one getirir."""
        # Gizlenmis (x ya da Kapat ile) ama suren islemin penceresi de one getirilir (M-02)
        p = getattr(self, "islem_penceresi", None)
        if p is not None and not p._yok_edildi:
            p.present()

    def _kurulu_oku(self, sonra):
        """dpkg'den kurulu paketleri arka planda okur; sonuc ana is parcaciginda sonra(kume) ile verilir."""
        def is_():
            GLib.idle_add(sonra, kurulu_paketler())
        threading.Thread(target=is_, daemon=True).start()

    def eylem(self, u, islem):
        if self.mesgul:
            self._mesgul_uyar()
            return
        if self._onay_bekliyor:
            return
        try:
            komut = apt_komutu(islem, u.get("paket"), izinli=self.katalog_adlari)
        except ValueError as exc:
            print(f"[magaza] {exc}", file=sys.stderr)
            return
        if komut is None:
            self._pkexec_yok(islem, u["paket"])
            return
        if islem == "remove":
            self._kaldirma_onayi(u, komut)
            return
        self._eylem_baslat(u, islem, komut)

    def _kaldirma_onayi(self, u, komut):
        """Kaldirmadan once neyin kaldirilacagini gosterir (M-03).

        `apt-get -s remove` kullanici yetkisiyle arka planda calisir; onay penceresi
        birlikte kaldirilacak butun paketleri listeler. CarotOS'un dayandigi bir paket
        varsa hangi uygulamanin bozulacagi adiyla yazilir ve ek onay (onay kutusu) istenir."""
        self._onay_bekliyor = True

        def is_():
            sonuc = kaldirma_simulasyonu(u["paket"])
            GLib.idle_add(goster, sonuc)

        def goster(sonuc):
            self._onay_bekliyor = False
            if not self.mesgul and self._kaldirma_sor(u, sonuc):
                self._eylem_baslat(u, "remove", komut)
            return False
        threading.Thread(target=is_, daemon=True).start()

    def _kaldirma_sor(self, u, sonuc):
        """Onay penceresi; True: kaldir. sonuc: kaldirma_simulasyonu ciktisi ya da None."""
        paketler = sonuc["paketler"] if sonuc and sonuc["paketler"] else [u["paket"]]
        etkiler = korunan_etkiler(paketler, DIL)
        temel = bool(sonuc and sonuc["temel"])

        d = Gtk.Dialog(transient_for=self, modal=True)
        d.set_title(M("kaldir_onay_baslik", ad=metin(u["ad"])))
        d.set_resizable(False)
        alan = d.get_content_area()
        alan.set_spacing(10)
        for k in ("top", "bottom", "start", "end"):
            getattr(alan, f"set_margin_{k}")(18)
        alan.pack_start(tema.etiket(M("kaldir_onay_baslik", ad=metin(u["ad"])), "buyuk-baslik",
                                    sar=True, genislik=50), False, False, 0)
        alan.pack_start(tema.etiket(M("kaldir_liste"), "soluk", sar=True, genislik=56),
                        False, False, 0)
        liste = tema.etiket("\n".join(paketler), None, sar=True, sec=True, genislik=56)
        if len(paketler) > 8:
            kaydir = Gtk.ScrolledWindow()
            kaydir.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            kaydir.set_size_request(-1, 160)
            kaydir.add(liste)
            alan.pack_start(kaydir, False, False, 0)
        else:
            alan.pack_start(liste, False, False, 0)
        if sonuc is None:
            k, e = tema.not_kutusu(M("kaldir_hesaplanamadi"), "uyari")
            e.set_max_width_chars(56)
            alan.pack_start(k, False, False, 0)
        anladim = None
        if temel:
            k, e = tema.not_kutusu(M("kaldir_temel"), "hata")
            e.set_max_width_chars(56)
            alan.pack_start(k, False, False, 0)
        elif etkiler:
            k, e = tema.not_kutusu(M("kaldir_korunan") + "\n\n" + "\n".join(etkiler), "uyari")
            e.set_max_width_chars(56)
            alan.pack_start(k, False, False, 0)
            anladim = Gtk.CheckButton(label=M("kaldir_anladim"))
            alan.pack_start(anladim, False, False, 0)

        satir = Gtk.Box(spacing=8)
        satir.set_margin_top(8)
        if temel:
            satir.pack_end(tema.dugme(M("kapat"), None, d.response, Gtk.ResponseType.CANCEL),
                           False, False, 0)
        else:
            evet = tema.dugme(M("kaldir"), "tehlike", d.response, Gtk.ResponseType.OK)
            hayir = tema.dugme(M("iptal"), None, d.response, Gtk.ResponseType.CANCEL)
            satir.pack_end(evet, False, False, 0)
            satir.pack_end(hayir, False, False, 0)
            if anladim is not None:          # ek onay: kutu isaretlenmeden Kaldir basilmaz
                evet.set_sensitive(False)
                anladim.connect("toggled", lambda c: evet.set_sensitive(c.get_active()))
        alan.pack_start(satir, False, False, 0)
        d.show_all()
        cevap = d.run()
        onay = (cevap == Gtk.ResponseType.OK and not temel
                and (anladim is None or anladim.get_active()))
        d.destroy()
        return onay

    def _eylem_baslat(self, u, islem, komut):
        self._mesgul_ayarla(islem + ":" + u["paket"])
        baslik = "%s — %s" % (metin(u["ad"]),
                              M("kaldiriliyor") if islem == "remove" else M("kuruluyor"))

        def bitince(_basarili):
            # Sonuc her zaman dpkg'den okunur (M-02): islem penceresi gizlenmis olabilir, kod
            # basarisiz olsa da paket kurulmus/kaldirilmis olabilir.
            def oku_bitti(kurulu):
                self.kurulu = kurulu
                self.sepet -= kurulu
                if u["paket"] not in kurulu:
                    self.guncellenebilir.discard(u["paket"])
                self._mesgul_ayarla(None)
                self._sepet_guncelle()
                self._guncelleme_rozeti()
                if self.detay_app is u:
                    self.detay_goster(u)
                else:
                    self.sayfa_secildi(self.aktif)
                return False
            self._kurulu_oku(oku_bitti)
        self._islem_baslat(baslik, komut, bitince, eylem=islem, paketler=(u["paket"],))

    def depoyu_yenile(self):
        if self.mesgul:
            self._mesgul_uyar()
            return
        komut = apt_komutu("update")
        if komut is None:
            self._pkexec_yok("update", "apt")
            return
        self._mesgul_ayarla("update")

        def bitince(_b):
            self._mesgul_ayarla(None)
            self._guncelleme_denetle()
        self._islem_baslat(M("yenileniyor"), komut, bitince, otomatik_kapan=True,
                           eylem="update")

    def tumunu_guncelle(self):
        if self.mesgul:
            self._mesgul_uyar()
            return
        komut = apt_komutu("upgrade")
        if komut is None:
            self._pkexec_yok("upgrade", "apt")
            return
        self._mesgul_ayarla("upgrade")

        def bitince(basarili):
            def oku_bitti(kurulu):
                self.kurulu = kurulu     # basarisiz bitse de bazi paketler guncellenmis olabilir
                self._mesgul_ayarla(None)
                self._guncelleme_denetle()
                return False
            self._kurulu_oku(oku_bitti)
        self._islem_baslat(M("guncelleniyor"), komut, bitince, eylem="upgrade")

    def _pkexec_yok(self, islem, paket):
        komut = {"update": "sudo apt-get update",
                 "upgrade": "sudo apt-get upgrade -y"}.get(
            islem, "sudo apt-get %s -y -- %s" % (islem, paket))
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


UYGULAMA_KIMLIGI = "org.carotos.Magaza"


def paket_argumani(argv):
    """argv'deki `--paket <ad>` degeri; yoksa ya da bicimi gecersizse None."""
    if "--paket" not in argv:
        return None
    try:
        ad = argv[argv.index("--paket") + 1]
    except (IndexError, ValueError):
        return None
    return ad if paket_adi_gecerli(ad) else None


def paketi_ac(pencere, ad, gecikme=600):
    """Katalogdaki paketin ayrinti sayfasini acar (yalnizca katalogda secim yapar)."""
    if not ad:
        return
    uygulama = next((u for u in pencere.uygulamalar if u.get("paket") == ad), None)
    if uygulama is None:
        return

    def ac():
        pencere.detay_goster(uygulama)
        return False
    if gecikme:
        # pencere yerleştikten sonra aç; açılış sırasındaki sayfa
        # kurulumu ayrıntı sayfasının üzerine yazmasın
        GLib.timeout_add(gecikme, ac)
    else:
        ac()


class MagazaUygulamasi(Gtk.Application):
    """Tek ornek (M-06): ikinci baslatma yeni pencere acmaz, acik pencereyi one getirir;
    `--paket <ad>` acik pencereye iletilir."""

    def __init__(self, katalog):
        super().__init__(application_id=UYGULAMA_KIMLIGI,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.katalog = katalog
        self.pencere = None

    def do_command_line(self, komut_satiri):
        argv = komut_satiri.get_arguments()
        ad = paket_argumani(argv)
        if self.pencere is None:
            self.pencere = MagazaPenceresi(self.katalog)
            self.add_window(self.pencere)
            self.pencere.show_all()
            paketi_ac(self.pencere, ad)
        else:
            # islem surse de gezinme serbesttir (islem penceresi modal degil)
            paketi_ac(self.pencere, ad, gecikme=0)
            self.pencere.present()
        return 0


def main():
    try:
        with open(KATALOG_YOLU, encoding="utf-8") as f:
            katalog = json.load(f)
    except Exception as exc:  # noqa: BLE001
        print(f"Katalog okunamadi ({KATALOG_YOLU}): {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(MagazaUygulamasi(katalog).run(sys.argv))


if __name__ == "__main__":
    main()
