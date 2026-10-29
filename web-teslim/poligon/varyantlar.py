"""
CarotOS Poligon -- soru varyantları.

Bir görev türü için birden çok FARKLI SORU tanımlıdır (örn. SSH günlüğünde
"en çok deneyen IP", "kaç farklı IP", "ilk deneme saat kaçta" ...). Öğretmen
yeni bir soru atadığında bilgisayar varyantlardan birini seçer ve numarası
tüm sınıfa duyurulur: sınıftaki herkes AYNI varyantı çözer. Öğrencilerin
verisi (IP, dosya, bayrak...) yine kendi makinelerinde ayrı üretilir.

Bu modül yalnız standart kütüphane kullanır (GTK, ağ, dosya üretimi yok);
öğretmen sunucusu da bunu kullanabilir. Varyant listeleri varyant_gunluk.py
ve varyant_sifre.py içinde kaydedilir.

Kayıt anahtarı: üreteç adı; aynı üreteç iki ayrı görevde farklı soru
kipiyle kullanılıyorsa "uretec:soru" (örn. "web_tarayici:ip").
"""

from __future__ import annotations

import json
import random
from pathlib import Path

_RNG = random.SystemRandom()

GOREVLER_DIZINI = Path(__file__).resolve().parent / "gorevler"

KAYIT: dict[str, list[dict]] = {}


def kaydet(anahtar: str, liste: list[dict]) -> None:
    KAYIT[anahtar] = list(liste)


def anahtar_bul(uretec: str, soru: str | None = None) -> str:
    """Üreteç (ve varsa soru kipi) için kayıt anahtarı; kayıt yoksa üreteç adı."""
    k = f"{uretec}:{soru}" if soru else uretec
    return k if k in KAYIT else uretec


def sayi(anahtar: str) -> int:
    return len(KAYIT.get(anahtar, ()))


def al(anahtar: str, no: int) -> dict:
    """1 tabanlı numaradan varyant; numara aralık dışındaysa başa sarar."""
    liste = KAYIT[anahtar]
    return liste[(int(no) - 1) % len(liste)]


def uygun_numaralar(anahtar: str, zorluk: str | None = None) -> list[int]:
    liste = KAYIT.get(anahtar, [])
    uygun = [i + 1 for i, v in enumerate(liste)
             if not v.get("zorluk") or zorluk in v["zorluk"]]
    return uygun or [i + 1 for i in range(len(liste))]


def sec(anahtar: str, zorluk: str | None = None, kullanilmis=()) -> int:
    """Rastgele bir varyant numarası; mümkünse daha önce kullanılmamış olandan.
    Hepsi kullanılmışsa uygun olanların tamamından seçer."""
    uygun = uygun_numaralar(anahtar, zorluk)
    kalan = [n for n in uygun if n not in set(kullanilmis)]
    return _RNG.choice(kalan or uygun)


_gorev_onbellek: dict[str, str | None] = {}


def gorev_anahtari(gorev_id: str) -> str | None:
    """Görev dosyasından varyant kayıt anahtarı (üreteç görevleri için);
    varyantı olmayan görevde None."""
    if gorev_id in _gorev_onbellek:
        return _gorev_onbellek[gorev_id]
    sonuc = None
    try:
        veri = json.loads((GOREVLER_DIZINI / f"{gorev_id}.json").read_text(encoding="utf-8"))
        fu = veri.get("flag_uretimi", {})
        if fu.get("yontem") == "uretec":
            k = anahtar_bul(fu.get("uretec", ""), (fu.get("sabit_parametreler") or {}).get("soru"))
            sonuc = k if sayi(k) > 1 else None
    except (OSError, ValueError):
        sonuc = None
    _gorev_onbellek[gorev_id] = sonuc
    return sonuc


def gorev_varyant_sayisi(gorev_id: str) -> int:
    k = gorev_anahtari(gorev_id)
    return sayi(k) if k else 0


def gorev_varyant_sec(gorev_id: str, zorluk: str | None = None, kullanilmis=()) -> int:
    """Görev için varyant seç; varyantı olmayan görevde 0."""
    k = gorev_anahtari(gorev_id)
    return sec(k, zorluk, kullanilmis) if k else 0


def _metin(v: dict, alan: str, dil: str) -> str:
    d = v.get(alan) or {}
    return d.get(dil) or d.get("tr", "")


def gorev_varyant_aciklamasi(gorev_id: str, no: int, dil: str = "tr") -> str:
    """Öğretmene gösterilen soru metni (cevabı içermez). Soru metni dosya yolu
    gibi yer tutucular içeriyorsa kısa özet kullanılır."""
    k = gorev_anahtari(gorev_id)
    if not k or not no:
        return ""
    v = al(k, no)
    soru = _metin(v, "soru", dil)
    if "{" in soru and v.get("ozet"):
        return _metin(v, "ozet", dil)
    return soru


def gorev_varyant_ozeti(gorev_id: str, no: int, dil: str = "tr", uzunluk: int = 58) -> str:
    """Açılır listede gösterilen kısa etiket."""
    k = gorev_anahtari(gorev_id)
    if not k:
        return ""
    v = al(k, no)
    metin = _metin(v, "ozet", dil) or _metin(v, "soru", dil)
    return metin if len(metin) <= uzunluk else metin[:uzunluk - 1].rstrip() + "…"


# Varyant listelerini kaydeden modüller (içe aktarma yan etkisiyle kaydeder)
from varyant_gunluk import KAYITLAR as _GUNLUK  # noqa: E402
from varyant_sifre import KAYITLAR as _SIFRE  # noqa: E402

for _a, _l in {**_GUNLUK, **_SIFRE}.items():
    kaydet(_a, _l)
