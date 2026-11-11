# -*- coding: utf-8 -*-
"""CarotOS sistem dili hazirligi: bir dilin oturum dili olarak kullanilabilmesi icin gerekenler.

ISO'ya tum dillerin paketlerini koymamak icin (boyut) dil paketleri istenince kurulur:
locale'in uretilmesi (locale-gen), Japonca/Cince icin CJK yazi tipi, kurulu Firefox/LibreOffice
icin dil paketi ve yazim denetimi sozlugu. CarotOS uygulamalarinin kendi cevirileri zaten
ortak/diller/*.json icindedir; bunlar icin paket gerekmez.

GTK'siz, yalniz standart kutuphane. Yetki gerektiren kisim /usr/local/sbin/carotos-dil-hazirla
(pkexec ile); o betik BU modulun tablolarini kullanir ve yalnizca tablodaki degerleri yazar.
/etc/default/locale (sistem geneli varsayilan) degistirilmez.
"""
import os
import subprocess

HAZIRLA_BETIGI = "/usr/local/sbin/carotos-dil-hazirla"

# kod -> locale, ek paketler, Firefox ESR dil eki, LibreOffice dil eki (kurulu ise eklenir)
HAZIRLIK = {
    "tr": {"locale": "tr_TR.UTF-8", "paketler": (), "firefox": "tr", "ofis": "tr"},
    "en": {"locale": "en_US.UTF-8", "paketler": (), "firefox": None, "ofis": None},
    "de": {"locale": "de_DE.UTF-8", "paketler": ("hunspell-de-de",), "firefox": "de", "ofis": "de"},
    "ru": {"locale": "ru_RU.UTF-8", "paketler": ("hunspell-ru",), "firefox": "ru", "ofis": "ru"},
    "es": {"locale": "es_ES.UTF-8", "paketler": ("hunspell-es",), "firefox": "es-es", "ofis": "es"},
    "pt": {"locale": "pt_BR.UTF-8", "paketler": ("hunspell-pt-br",), "firefox": "pt-br", "ofis": "pt-br"},
    # Japonca/Cince: yazi tipi + girdi yontemi (fcitx5; Japonca icin Mozc). Yalniz bu dili secen kurar;
    # im-config oturum acilisinda fcitx5'i baslatir (calisirken ~70-100 MB RAM, diger dillerde sifir).
    "ja": {"locale": "ja_JP.UTF-8", "firefox": "ja", "ofis": "ja",
           "paketler": ("fonts-noto-cjk", "fcitx5", "fcitx5-mozc", "fcitx5-frontend-gtk3", "im-config")},
    "zh": {"locale": "zh_CN.UTF-8", "firefox": "zh-cn", "ofis": "zh-cn",
           "paketler": ("fonts-noto-cjk", "fcitx5", "fcitx5-chinese-addons", "fcitx5-frontend-gtk3", "im-config")},
    "fr": {"locale": "fr_FR.UTF-8", "paketler": ("hunspell-fr",), "firefox": "fr", "ofis": "fr"},
}
# Dil paketi kurulu mu diye bakilacak ana paketler: biri kuruluysa onun dil paketi de eklenir
FIREFOX_ANA = "firefox-esr"
OFIS_ANA = "libreoffice-core"


def locale_adi(kod):
    """'de' -> 'de_DE.UTF-8'; bilinmeyen kod icin None."""
    k = HAZIRLIK.get(kod)
    return k["locale"] if k else None


def paket_listesi(kod, kurulu):
    """`kod` dili icin kurulmasi gereken tum paketler (zaten kurulu olanlar dahil), sirali.
    `kurulu`: kurulu paket adlari kumesi (Firefox/LibreOffice dil paketi yalniz ana paket varsa)."""
    k = HAZIRLIK.get(kod)
    if not k:
        return []
    sonuc = list(k["paketler"])
    if k["firefox"] and FIREFOX_ANA in kurulu:
        sonuc.append("firefox-esr-l10n-" + k["firefox"])
    if k["ofis"] and OFIS_ANA in kurulu:
        sonuc.append("libreoffice-l10n-" + k["ofis"])
    return sorted(set(sonuc))


def eksik_paketler(kod, kurulu):
    return [p for p in paket_listesi(kod, kurulu) if p not in kurulu]


def _normal(locale):
    """'de_DE.UTF-8' ve 'de_DE.utf8' ayni sayilir."""
    ad, _, kodlama = locale.partition(".")
    return ad.lower() + "." + kodlama.lower().replace("-", "")


def locale_var_mi(kod, locale_a_ciktisi):
    """`locale -a` satirlari arasinda dilin locale'i uretilmis mi."""
    loc = locale_adi(kod)
    if not loc:
        return False
    return _normal(loc) in {_normal(s.strip()) for s in locale_a_ciktisi if "." in s}


def kurulu_paketler():
    try:
        r = subprocess.run(["dpkg-query", "-W", "-f=${Package} ${Status}\n"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {s.split(" ", 1)[0] for s in r.stdout.splitlines() if s.endswith("install ok installed")}


def locale_a():
    try:
        r = subprocess.run(["locale", "-a"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return []
    return r.stdout.splitlines()


def hazirlik_gerekli_mi(kod, kurulu=None, locales=None):
    """True: locale uretilmemis ya da dil paketleri eksik. tr/en icin her zaman False
    (locale'leri ISO'da var)."""
    if kod in ("tr", "en") or kod not in HAZIRLIK:
        return False
    kurulu = kurulu_paketler() if kurulu is None else kurulu
    locales = locale_a() if locales is None else locales
    return (not locale_var_mi(kod, locales)) or bool(eksik_paketler(kod, kurulu))


def hazirla_komutu(kod):
    """Karsilama'nin calistiracagi komut (yetki pkexec ile istenir)."""
    return ["pkexec", HAZIRLA_BETIGI, kod]


def locale_gen_satiri(kod):
    """/etc/locale.gen satiri: 'de_DE.UTF-8 UTF-8'."""
    loc = locale_adi(kod)
    return f"{loc} UTF-8" if loc else None
