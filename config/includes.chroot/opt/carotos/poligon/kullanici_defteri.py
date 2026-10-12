#!/usr/bin/env python3
"""
CarotOS Poligon -- yerel kullanici defteri.

Ogrenci uygulamasindaki "Kullanici olustur / Kullanici giris yap" icindir.
Her kullanici KENDI makinesinde, KENDI dosyasinda saklanir:

    ~/.local/share/carotos-poligon/kullanicilar/<id>.json
    = {"ad": ..., "id": ..., "sifre": ...}

"sifre" alani ogrencinin OKUL NUMARASIDIR (en fazla 6 hane; daha az da
olabilir). DUZ METIN saklanir ve bu BILINCLIDIR:
  - sifre uygulama icinden degistirilemez; gerekirse ogretmen/ogrenci
    ilgili .json dosyasindan elle degistirir,
  - okul numarasi gizli bir sir degildir.
Ayni makineyi kullanan baska biri bu dosyalari okuyabilir; bu kullanim
senaryosunda kabul edilebilir bir durumdur.

GTK'dan BAGIMSIZ: butun mantik burada, arayuz katmani (ogrenci_uygulama.py)
sadece bu fonksiyonlari cagirir. Bu ayrim sayesinde GTK kurulu olmayan bir
ortamda da test edilebilir.
"""

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

DIZIN = Path.home() / ".local" / "share" / "carotos-poligon" / "kullanicilar"
AD_MAX = 20
SIFRE_MAX = 6


class IsimAlinmis(Exception):
    """Ayni ad baska bir kullanicida zaten var."""


def _dizini_hazirla() -> None:
    DIZIN.mkdir(parents=True, exist_ok=True)


def _oku_hepsi() -> list[dict]:
    """Kayitli tum kullanicilari okur. Bozuk/okunamayan bir dosya
    digerlerini engellemez (sessizce atlanir)."""
    if not DIZIN.exists():
        return []
    kullanicilar = []
    for yol in sorted(DIZIN.glob("*.json")):
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(veri, dict) and veri.get("ad"):
            kullanicilar.append(veri)
    return kullanicilar


def adlari_listele() -> list[str]:
    """Giris ekranindaki acilir listede gosterilecek kullanici adlari
    (alfabetik, tekil)."""
    return sorted({k["ad"] for k in _oku_hepsi()})


def ad_gecerli_mi(ad: str) -> bool:
    return 1 <= len(ad.strip()) <= AD_MAX


def sifre_gecerli_mi(sifre: str) -> bool:
    """En fazla 6 HANE (rakam). Daha az olabilir -- okul numaralari 6
    haneye kadar cikabildigi icin ust sinir 6."""
    return bool(re.fullmatch(r"\d{1,%d}" % SIFRE_MAX, sifre.strip()))


def _id_uret() -> str:
    """Makinenin atadigi, mevcut dosyalarla cakismayan rastgele id."""
    _dizini_hazirla()
    while True:
        yeni = secrets.token_hex(4)  # 8 hex karakter, orn. 'a1b2c3d4'
        if not (DIZIN / f"{yeni}.json").exists():
            return yeni


def olustur(ad: str, sifre: str) -> dict:
    """Yeni kullanici olusturur ve dosyasina yazar. Ayni ad zaten varsa
    IsimAlinmis firlatir. Donen sozluk: {"ad","id","sifre"}.

    Cagiran taraf ad/sifre gecerliligini ad_gecerli_mi/sifre_gecerli_mi
    ile ONCEDEN kontrol etmeli (arayuz boyle yapiyor); burada da son bir
    guvenlik kontrolu var."""
    ad = ad.strip()
    sifre = sifre.strip()
    if not ad_gecerli_mi(ad):
        raise ValueError("ad gecersiz")
    if not sifre_gecerli_mi(sifre):
        raise ValueError("sifre (okul no) gecersiz")
    _dizini_hazirla()
    if ad in adlari_listele():
        raise IsimAlinmis(ad)
    kullanici = {"ad": ad, "id": _id_uret(), "sifre": sifre}
    yol = DIZIN / f"{kullanici['id']}.json"
    yol.write_text(
        json.dumps(kullanici, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return kullanici


def dogrula(ad: str, sifre: str) -> dict | None:
    """Ad + sifre (okul no) eslesen kullaniciyi doner; eslesme yoksa None.
    Karsilastirma birebir yapilir (ad ve sifre strip'lenir)."""
    ad = ad.strip()
    sifre = sifre.strip()
    for k in _oku_hepsi():
        if k.get("ad") == ad and str(k.get("sifre", "")) == sifre:
            return k
    return None
