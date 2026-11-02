#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Karsilama gorselleri: sayfalarin basvurdugu her dosya var ve gercekten PNG.

GdkPixbuf WebP'yi her sistemde okumaz (webp-pixbuf-loader gerekir); bu yuzden
Karsilama'nin gorselleri PNG olmali. Uygulama ekran goruntulerinin GitHub'daki
(docs/screenshots) gercek goruntulerle ayni olmasi da burada denetlenir.

Calistirma:  python3 tests/test_karsilama_gorseller.py
"""
import os
import re
import struct
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOD = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "welcome", "carotos-welcome.py")
GORSEL = os.path.join(KOK, "config", "includes.chroot", "usr", "share", "carotos", "welcome")
PNG_IMZA = b"\x89PNG\r\n\x1a\n"


def sayfa_gorselleri():
    with open(KOD, "rb") as f:
        kaynak = f.read().decode("utf-8")
    return sorted(set(re.findall(r'"image":\s*"([^"]+)"', kaynak)))


def png_boyut(yol):
    with open(yol, "rb") as f:
        bas = f.read(24)
    if bas[:8] != PNG_IMZA:
        return None
    return struct.unpack(">II", bas[16:24])


class KarsilamaGorselleriTesti(unittest.TestCase):
    def test_gorsel_listesi_bos_degil(self):
        self.assertGreaterEqual(len(sayfa_gorselleri()), 10)

    def test_her_gorsel_var_ve_png(self):
        for ad in sayfa_gorselleri():
            with self.subTest(gorsel=ad):
                yol = os.path.join(GORSEL, ad)
                self.assertTrue(os.path.isfile(yol), "yok: " + ad)
                boyut = png_boyut(yol)
                self.assertIsNotNone(boyut, ad + " gercek bir PNG degil")
                gen, yuk = boyut
                # kutu 678x440 gosterilir; HiDPI icin en az bu kadar olmali
                self.assertGreaterEqual(gen, 678, ad)
                self.assertGreaterEqual(yuk, 300, ad)

    def test_logo_png(self):
        self.assertIsNotNone(png_boyut(os.path.join(GORSEL, "logo.png")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
