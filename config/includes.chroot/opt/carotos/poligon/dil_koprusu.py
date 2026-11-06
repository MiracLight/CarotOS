# -*- coding: utf-8 -*-
"""Poligon -- ortak dil katmanina (ortak/dil.py) koprü. GTK'siz.

ISO'da ortak/ klasoru bu klasorun yanindadir. Poligon bagimsiz depodan (ortak/ olmadan)
calistirilirsa yalniz tr/en bilinir; bu modul onu sessizce karsilar.
"""
from __future__ import annotations

import os
import sys

try:
    import dil as _dil
except ImportError:
    _ORTAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ortak")
    if os.path.isdir(_ORTAK) and _ORTAK not in sys.path:
        sys.path.insert(0, _ORTAK)
    try:
        import dil as _dil
    except ImportError:
        _dil = None


def sec(sozluk, kod: str) -> str:
    """{"tr","en",..} sozlugunden `kod` dilindeki metin (dil dosyasi, en, tr siralamasiyla)."""
    if sozluk is None:
        return ""
    if _dil is not None:
        return _dil.metin(sozluk, kod)
    return sozluk.get(kod) or sozluk.get("en") or sozluk.get("tr", "")


def T(sozluk, kod: str, **kw) -> str:
    """sec() + str.format; bozuk ceviri yer tutucusunda en/tr metne duser, istisna atmaz."""
    if _dil is not None:
        return _dil.T(sozluk, kod, None, **kw)
    sablon = sec(sozluk, kod)
    try:
        return sablon.format(**kw)
    except (KeyError, IndexError, ValueError):
        return sablon


def zengin(veri):
    """Ic ice {"tr","en"} sozluklerini her dilde `[kod]` ile guvenle okunur yapar."""
    return _dil.zenginlestir(veri) if _dil is not None else veri


def dil_once(tablo):
    """{"tr": {anahtar: metin}, "en": {...}} tablosunu METIN[kod][anahtar] her dilde guvenli yapar."""
    if _dil is not None:
        return _dil.dil_once(tablo)
    return {**tablo, **{}}   # ortak katman yok: yalniz tr/en vardir, eski davranis


def etkin_diller():
    """Dil seciciye girecek [(kod, ad, taslak_mi)]; ortak katman yoksa yalniz tr/en."""
    if _dil is not None:
        return _dil.etkin_diller()
    return [("tr", "Türkçe", False), ("en", "English", False)]


def secici_adi(kod: str, ad: str, taslak: bool) -> str:
    if _dil is not None:
        return _dil.secici_adi(kod, ad, taslak)     # yazi tipi yoksa Latin ad (kutucuk gorunmesin)
    return f"{ad} (beta)" if taslak else ad


def gecerli_dil(kod):
    """Dil seciciye girebiliyorsa kod, degilse None."""
    return kod if kod in {k for k, _, _ in etkin_diller()} else None


def baslangic_dili(kayitli=None) -> str:
    """Ilk acilis dili: kayitli (gecerliyse) > sistem dili (etkinse) > tr (sistem Turkce ise) > en."""
    if gecerli_dil(kayitli):
        return kayitli
    if _dil is not None:
        return _dil.varsayilan_dil()
    for degisken in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        if os.environ.get(degisken, "").lower().startswith("tr"):
            return "tr"
    return "en"
