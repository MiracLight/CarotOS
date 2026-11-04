#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon varyantlarinda dil sizintisi denetimi.

Ingilizce arayuzde Turkce ipucu/soru cikmamali (ve tersi: Turkce metin Ingilizce
kopyalanmamali). Gunluk ve sifre varyantlarinin TUM kayitlari taranir. GTK'siz.

Kullanim (depo kokunden):  python3 tests/test_poligon_dil_sizintisi.py
"""
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot/opt/carotos")
for _y in (os.path.join(INC, "poligon"), os.path.join(INC, "carotpot"),
           os.path.join(INC, "ortak")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import varyantlar as V  # noqa: E402

# Komutlardaki veri anahtarlari (kullanici, giris, hizmet, kaynak, kod...)
# bilerek Turkce kalir; bu yuzden yalnizca ACIKLAYICI sozcuklere bakilir.
TR_SOZCUK = re.compile(
    # {tablo}/{dosya} gibi yer tutucular ve komut sozcukleri yanlis alarm
    # vermesin diye "tablo", "ile", "ara" gibi kisa kelimeler listede yok.
    r"\b(bul|sonra|önce|tablonun|sıklık|satırı|satırındaki|satırlarında|sayı|"
    r"ikinci|ilk|bak|kaydırmayı|çözülmüş|satırlarda|başlayanı)\b",
    re.IGNORECASE)
TR_HARF = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
ALANLAR = ("soru", "ipucu", "bicim_aciklama", "ozet")


def _tum_varyantlar():
    for kaynak in (V._GUNLUK, V._SIFRE):
        for anahtar, liste in kaynak.items():
            for no, v in enumerate(liste):
                yield f"{anahtar}#{no}", v


class DilSizintisi(unittest.TestCase):
    def test_ingilizce_alanlarda_turkce_yok(self):
        hatalar = []
        for ad, v in _tum_varyantlar():
            for alan in ALANLAR:
                if alan not in v:  # sifre varyantlarinda bazi alanlar yok
                    continue
                en = v[alan]["en"]
                if TR_HARF.search(en) or TR_SOZCUK.search(en):
                    hatalar.append(f"{ad} {alan}.en: {en[:90]}")
        self.assertEqual(hatalar, [], "\n" + "\n".join(hatalar[:25]))

    def test_turkce_aciklama_ingilizceye_kopyalanmamis(self):
        hatalar = []
        for ad, v in _tum_varyantlar():
            tr, en = v["ipucu"]["tr"], v["ipucu"]["en"]
            if tr == en and (TR_HARF.search(tr) or TR_SOZCUK.search(tr)):
                hatalar.append(f"{ad}: {tr[:90]}")
        self.assertEqual(hatalar, [], "\n" + "\n".join(hatalar[:25]))

    def test_kayit_var(self):
        self.assertGreater(len(list(_tum_varyantlar())), 100)


if __name__ == "__main__":
    unittest.main()
