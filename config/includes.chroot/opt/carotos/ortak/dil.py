# -*- coding: utf-8 -*-
"""CarotOS ortak dil katmani (GTK'siz, yalniz standart kutuphane).

Uygulamalarin metinleri kodda {"tr": "...", "en": "..."} sozlukleri olarak
yazilir (kaynak diller: Turkce ve Ingilizce). Diger diller (de, ru, es, pt, ja,
zh, fr) kodu degistirmeden, `ortak/diller/<kod>.json` dosyalarindan gelir:

    {
      "_meta": {"ad": "Espanol", "etkin": true, "durum": "taslak"},
      "metinler": {"<Ingilizce metin>": "<ceviri>", ...}
    }

Anahtar, sozlukteki INGILIZCE metindir (gettext'teki msgid gibi): ayni Ingilizce
metin tum uygulamalarda tek ceviri paylasir, kodda anahtar uydurmak gerekmez.
Ceviri yoksa Ingilizceye, o da yoksa Turkceye dusulur; hicbir yerde KeyError
cikmaz. Bozuk (yer tutucusu degismis) bir ceviri uygulamayi cokertmez, Ingilizce
metne dusulur.

Kullanim:
    import dil
    STRINGS = dil.zenginlestir(STRINGS)        # {"tr","en"} sozluklerini Metin yapar
    STRINGS["run"][lang]                       # her dil icin calisir (eksikse yedek)
    dil.metin(sozluk, lang)                    # ayni, .get gibi sorgularda
    dil.T(sozluk, lang, tool="nmap")           # yer tutucu doldurma (guvenli)
    dil.etkin_diller()                         # dil secici icin [(kod, ad), ...]
    dil.varsayilan_dil()                       # sistem dilinden ilk acilis dili
"""
import json
import os
import re

# Sira, dil seciciye girdigi siradir. Adlar kendi dilindedir.
DILLER = (
    ("tr", "Türkçe"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("ru", "Русский"),
    ("es", "Español"),
    ("pt", "Português"),
    ("ja", "日本語"),
    ("zh", "中文"),
    ("fr", "Français"),
)
KODLAR = tuple(k for k, _ in DILLER)
KAYNAK_DILLER = ("tr", "en")          # kodda yazili; her zaman etkin
DIZIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diller")

_onbellek = {}                        # (dizin, kod) -> {"meta": {...}, "metinler": {...}}


def gecerli(kod, varsayilan="en"):
    """Bilinen bir dil kodu degilse varsayilana doner."""
    return kod if kod in KODLAR else varsayilan


def _dosya(kod, dizin=None):
    dizin = dizin or DIZIN
    anahtar = (dizin, kod)
    if anahtar not in _onbellek:
        meta, metinler = {}, {}
        try:
            with open(os.path.join(dizin, kod + ".json"), encoding="utf-8") as f:
                veri = json.load(f)
            if isinstance(veri, dict):
                if isinstance(veri.get("_meta"), dict):
                    meta = veri["_meta"]
                ham = veri.get("metinler")
                if isinstance(ham, dict):
                    metinler = {k: v for k, v in ham.items()
                                if isinstance(k, str) and isinstance(v, str) and v.strip()}
        except (OSError, ValueError):
            pass
        _onbellek[anahtar] = {"meta": meta, "metinler": metinler}
    return _onbellek[anahtar]


def onbellegi_temizle():
    _onbellek.clear()


def etkin_diller(dizin=None):
    """Dil secicide gosterilecek diller: [(kod, ad, taslak_mi), ...].
    tr ve en her zaman vardir; digerleri yalniz dosyalari var, `_meta.etkin`
    dogru ve en az bir cevirisi varsa. `_meta.durum == "taslak"` ise taslak_mi
    True'dur (gozden gecirilmemis ceviri)."""
    sonuc = []
    for kod, ad in DILLER:
        if kod in KAYNAK_DILLER:
            sonuc.append((kod, ad, False))
            continue
        d = _dosya(kod, dizin)
        if d["meta"].get("etkin") is True and d["metinler"]:
            sonuc.append((kod, ad, d["meta"].get("durum", "taslak") != "gozden-gecirildi"))
    return sonuc


def secici_adi(kod, ad, taslak):
    """Dil seciciye yazilacak metin; gozden gecirilmemis dile 'beta' eklenir."""
    return f"{ad} (beta)" if taslak else ad


def varsayilan_dil(ortam=None, dizin=None):
    """Ilk acilis dili: sistem dilinin kodu etkin bir dilse o, degilse 'en'.
    Kayitli bir kullanici ayari varsa uygulama onu kullanir, bunu degil.
    C/POSIX dil bilgisi tasimaz, atlanir. LANGUAGE degiskeni 'de:en' gibi liste
    olabilir. Tum zh_* varyantlari 'zh' olur (yalniz yalin Cince vardir)."""
    ortam = os.environ if ortam is None else ortam
    etkin = {k for k, _, _ in etkin_diller(dizin)}
    for degisken in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        deger = (ortam.get(degisken) or "").strip()
        if not deger or deger in ("C", "POSIX"):
            continue
        for parca in deger.split(":"):
            kod = re.split(r"[_.@\-]", parca.strip().lower())[0]
            if kod in etkin:
                return kod
        return "en"
    return "en"


def ceviri(en_metin, kod, dizin=None):
    """Ingilizce metnin 'kod' dilindeki cevirisi; yoksa None."""
    if not en_metin or kod in KAYNAK_DILLER:
        return None
    return _dosya(kod, dizin)["metinler"].get(en_metin)


def metin(sozluk, kod, anahtar=None, dizin=None):
    """{"tr","en",...} sozlugunden 'kod' dilindeki metni verir. Sira: sozlukteki
    kod -> dil dosyasindaki ceviri -> en -> tr -> herhangi bir metin -> anahtar."""
    if sozluk is None:
        return anahtar or ""
    if isinstance(sozluk, str):
        return sozluk
    dogrudan = sozluk.get(kod)
    if isinstance(dogrudan, str) and dogrudan:
        return dogrudan
    en = sozluk.get("en")
    c = ceviri(en, kod, dizin) if isinstance(en, str) else None
    if c:
        return c
    for yedek in ("en", "tr"):
        v = sozluk.get(yedek)
        if isinstance(v, str) and v:
            return v
    for v in sozluk.values():
        if isinstance(v, str) and v:
            return v
    return anahtar or ""


def yer_tutucular(sablon):
    """Bir metindeki {ad} ve {} yer tutuculari (kume)."""
    return set(re.findall(r"\{(\w*)\}", sablon or ""))


def T(sozluk, kod, anahtar=None, dizin=None, **kw):
    """metin() + str.format. Ceviri yer tutucuyu bozmussa (KeyError vb.)
    Ingilizce, o da olmazsa Turkce/ham metin kullanilir; asla istisna atmaz."""
    sablon = metin(sozluk, kod, anahtar, dizin)
    if not kw:
        return sablon
    adaylar = [sablon]
    if isinstance(sozluk, dict):
        for yedek in ("en", "tr"):
            v = sozluk.get(yedek)
            if isinstance(v, str) and v not in adaylar:
                adaylar.append(v)
    for aday in adaylar:
        try:
            return aday.format(**kw)
        except (KeyError, IndexError, ValueError, AttributeError):
            continue
    return sablon


class Metin(dict):
    """{"tr","en"} sozlugu: bilinmeyen/eksik dil icin [] KeyError atmaz, yedek
    metni verir. Normal sozluk gibi davranir (json, kopya, karsilastirma)."""

    def __missing__(self, kod):
        return metin(self, kod)


def _iki_dilli_mi(d):
    return ("tr" in d and "en" in d and
            all(isinstance(k, str) and isinstance(v, str) for k, v in d.items()))


def zenginlestir(veri):
    """Ic ice sozluk/liste/demet yapisindaki tum {"tr","en"} sozluklerini Metin
    yapar (yeni bir yapi dondurur, girdiyi degistirmez). Lambda gibi diger
    degerlere dokunmaz."""
    if isinstance(veri, dict):
        if _iki_dilli_mi(veri):
            return Metin(veri)
        return {k: zenginlestir(v) for k, v in veri.items()}
    if isinstance(veri, list):
        return [zenginlestir(v) for v in veri]
    if isinstance(veri, tuple):
        return tuple(zenginlestir(v) for v in veri)
    return veri


class _DilTablosu:
    """METIN[kod] sonucu: `[anahtar]` o dilde metni verir (dil dosyasi, en, tr yedegiyle)."""

    def __init__(self, tablo, kod, dizin=None):
        self._t, self._kod, self._dizin = tablo, kod, dizin

    def __getitem__(self, anahtar):
        dogrudan = self._t.get(self._kod, {}).get(anahtar)
        if dogrudan is not None and not isinstance(dogrudan, str):
            return dogrudan                       # liste/sayi gibi cevrilmeyen degerler oldugu gibi
        sozluk = {k: v[anahtar] for k, v in self._t.items()
                  if isinstance(v.get(anahtar), str)}
        if not sozluk:
            if any(anahtar in v for v in self._t.values()):
                for v in self._t.values():
                    if anahtar in v:
                        return v[anahtar]
            raise KeyError(anahtar)
        return metin(sozluk, self._kod, anahtar, self._dizin)

    def get(self, anahtar, varsayilan=None):
        try:
            return self[anahtar]
        except KeyError:
            return varsayilan

    def __contains__(self, anahtar):
        return any(anahtar in v for v in self._t.values())

    def keys(self):
        return set().union(*[set(v) for v in self._t.values()])

    def __iter__(self):
        return iter(sorted(self.keys()))

    def __len__(self):
        return len(self.keys())

    def items(self):
        return [(k, self[k]) for k in sorted(self.keys())]


class DilOnce:
    """{"tr": {anahtar: metin}, "en": {...}} (dil-once) tablosunu her dil icin guvenli
    `METIN[kod][anahtar]` yapar. Var olan cagri yerleri degismez; bilinmeyen anahtar yine
    KeyError verir (gercek hatayi gizlemez), eksik DIL ise yedege duser."""

    def __init__(self, tablo, dizin=None):
        self._t, self._dizin = tablo, dizin

    def __getitem__(self, kod):
        return _DilTablosu(self._t, kod, self._dizin)


def dil_once(tablo, dizin=None):
    """DilOnce kisayolu (bkz. sinif)."""
    return DilOnce(tablo, dizin)
