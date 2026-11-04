#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bir dil dosyasi ETKINLESTIRILMEDEN once tum uygulamalarin ortak dil katmanina
bagli olmasi gerekir (GTK gerektirmez).

Baglanmamis bir uygulama {...}[lang] ile dogrudan indeksler; sistem dili etkin
dile gecince KeyError ile coker. Bu test, `ortak/diller/*.json` icinde
`_meta.etkin: true` olan bir dil varken hala baglanmamis uygulama kaldiysa
KIRMIZI olur. Etkin dil yokken (bugun) bagli olmayanlar yalniz raporlanir.

Calistirma (depo kokunden):  python3 tests/test_dil_etkin_kosulu.py
"""
import glob
import json
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")

# Ortak dil katmanina BAGLI olmasi gereken uygulama kaynaklari
UYGULAMALAR = {
    "security-panel": "security-panel/carotos-security-panel.py",
    "health": "health/carotos-health.py",
    "usb": "usb/carotos-usb-check.py",
    "magaza": "magaza/carotos-magaza.py",
    "carotene": "carotene/carotene.py",
    "welcome": "welcome/carotos-welcome.py",
    "gsd": "gsd/carotos-gsd.py",
    "former": "former/carotos-former.py",
    "carotpot": "carotpot/arayuz/pencere.py",
    "poligon-ogrenci": "poligon/ogrenci_uygulama.py",
    "poligon-ogretmen": "poligon/ogretmen_uygulama.py",
    "filenor": "filenor/filenor_uygulama.py",
}
BAGLI_DEGIL_SIMDILIK = {"poligon-ogrenci", "poligon-ogretmen", "filenor"}   # bkz. docs/CEVIRI.md
_BAGLANTI = re.compile(r"^\s*import dil( as \w+)?\b|^\s*from dil import", re.M)


def etkin_diller():
    sonuc = []
    for yol in glob.glob(os.path.join(INC, "ortak", "diller", "*.json")):
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
        if veri.get("_meta", {}).get("etkin") is True:
            sonuc.append(os.path.basename(yol)[:-5])
    return sonuc


def bagli_mi(yol):
    with open(os.path.join(INC, yol), encoding="utf-8") as f:
        return bool(_BAGLANTI.search(f.read()))


class EtkinKosuluTesti(unittest.TestCase):
    def test_baglanti_listesi_gercekle_uyumlu(self):
        # Listede "bagli degil" denen uygulama aslinda baglandiysa listeyi guncelle
        for ad, yol in UYGULAMALAR.items():
            if ad in BAGLI_DEGIL_SIMDILIK:
                continue
            self.assertTrue(bagli_mi(yol), f"{ad} ortak dil katmanina bagli degil: {yol}")
        yeni_baglananlar = [ad for ad in BAGLI_DEGIL_SIMDILIK if bagli_mi(UYGULAMALAR[ad])]
        self.assertEqual(yeni_baglananlar, [],
                         "Bu uygulamalar artik bagli: BAGLI_DEGIL_SIMDILIK listesinden cikar")

    def test_etkin_dil_varsa_hepsi_bagli_olmali(self):
        etkin = etkin_diller()
        if not etkin:
            self.skipTest("etkin dil dosyasi yok; baglanmamislar: " + ", ".join(sorted(BAGLI_DEGIL_SIMDILIK)))
        baglanmamis = [ad for ad, yol in UYGULAMALAR.items() if not bagli_mi(yol)]
        self.assertEqual(baglanmamis, [],
                         f"{', '.join(etkin)} etkin ama su uygulamalar ortak dil katmanina bagli degil")


if __name__ == "__main__":
    unittest.main()
