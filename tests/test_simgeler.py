#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Uygulama simgeleri tutarliligi (GTK gerektirmez).

tools/simge/*.svg kaynaklari "duz" dilde mi (gradyan/golge/bulaniklik yok),
uretilen PNG'ler dogru boyutta mi, ISO'ya gomulu kaynaklar (ikonlar.b64,
filenor_simge.py PNG_128, Magaza LOGO_B64) gecerli PNG mi, scalable SVG'ler
kaynakla ayni mi. Uretmek icin: tools/simge_uret.mjs (sharp gerekir).

Calistirma (depo kokunden):  python3 tests/test_simgeler.py
"""
import base64
import os
import re
import struct
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(KOK, "tools", "simge")
INC = os.path.join(KOK, "config", "includes.chroot")
HICOLOR = os.path.join(INC, "usr", "share", "icons", "hicolor")
OPT = os.path.join(INC, "opt", "carotos")
BOYUTLAR = (16, 22, 24, 32, 48, 64, 128, 256)

# kaynak adi -> scalable dosya adi (varsa)
SCALABLE = {"filenor": "filenor", "former": "carotos-former", "gsd": "carotos-gsd",
            "saglik": "carotos-health", "magaza": "carotos-magaza", "usb": "carotos-usb-check"}
GEREKLI_KAYNAKLAR = {"filenor", "former", "gsd", "saglik", "magaza", "carotene", "carotpot", "usb",
                     "poligon-ogrenci", "poligon-ogretmen", "panel"}
YASAK_ETIKET = {"linearGradient", "radialGradient", "filter", "feGaussianBlur", "feDropShadow",
                "feOffset", "mask", "image", "style", "script", "foreignObject", "text"}


def png_boyut(veri):
    assert veri[:8] == b"\x89PNG\r\n\x1a\n", "PNG degil"
    return struct.unpack(">II", veri[16:24])


def oku(yol, mod="rb"):
    with open(yol, mod, **({"encoding": "utf-8"} if "b" not in mod else {})) as f:
        return f.read()


class KaynakSvgTesti(unittest.TestCase):
    def kaynaklar(self):
        return sorted(f for f in os.listdir(KAYNAK) if f.endswith(".svg"))

    def test_gerekli_kaynaklar_var(self):
        # Yeni simge eklenebilir (panel, poligon-ogretmen...); onaylananlar eksik olmamali.
        self.assertLessEqual(GEREKLI_KAYNAKLAR, {f[:-4] for f in self.kaynaklar()})

    def test_gecerli_xml_256_ve_duz_dil(self):
        for ad in self.kaynaklar():
            with self.subTest(ad=ad):
                kok = ET.fromstring(oku(os.path.join(KAYNAK, ad)))
                self.assertEqual(kok.get("viewBox"), "0 0 256 256")
                etiketler = {e.tag.split("}")[-1] for e in kok.iter()}
                self.assertFalse(etiketler & YASAK_ETIKET, etiketler & YASAK_ETIKET)   # duz renk: gradyan/golge yok
                self.assertNotIn("url(#", oku(os.path.join(KAYNAK, ad), "r"))          # baska ogeye referans yok

    def test_scalable_kopyalar_kaynakla_ayni(self):
        for kaynak, hedef in SCALABLE.items():
            with self.subTest(kaynak=kaynak):
                self.assertEqual(oku(os.path.join(KAYNAK, kaynak + ".svg")),
                                 oku(os.path.join(HICOLOR, "scalable", "apps", hedef + ".svg")))


class UretilenDosyalarTesti(unittest.TestCase):
    def test_carotene_ve_carotpot_tum_boyutlar(self):
        for ad in ("carotene", "carotpot"):
            for b in BOYUTLAR:
                yol = os.path.join(HICOLOR, f"{b}x{b}", "apps", ad + ".png")
                self.assertEqual(png_boyut(oku(yol)), (b, b), yol)

    def test_256_png_saglik_magaza_usb_poligon(self):
        for ad in ("carotos-health", "carotos-magaza", "carotos-usb-check", "carotos-poligon-ogrenci",
                   "carotos-poligon-ogretmen", "carotos-security-panel"):
            yol = os.path.join(HICOLOR, "256x256", "apps", ad + ".png")
            self.assertEqual(png_boyut(oku(yol)), (256, 256), yol)

    def test_panel_simgesi_iki_konumda_ayni(self):
        # Uygulama kendi yedegini (icons/carotos) kullanir; hicolor ile ayni olmali.
        self.assertEqual(oku(os.path.join(HICOLOR, "256x256", "apps", "carotos-security-panel.png")),
                         oku(os.path.join(INC, "usr", "share", "icons", "carotos", "security-panel-icon.png")))

    def test_gomulu_b64_sekiz_boyut(self):
        for uyg in ("filenor", "former", "gsd"):
            with self.subTest(uyg=uyg):
                boyutlar = []
                for satir in oku(os.path.join(OPT, uyg, "ikonlar.b64"), "r").splitlines():
                    boyut, veri = satir.split()
                    self.assertEqual(png_boyut(base64.b64decode(veri)), (int(boyut), int(boyut)))
                    boyutlar.append(int(boyut))
                self.assertEqual(boyutlar, list(BOYUTLAR))

    def test_koda_gomulu_png_128(self):
        metin = oku(os.path.join(OPT, "filenor", "filenor_simge.py"), "r")
        blok = re.search(r'PNG_128 = \(\s*\n((?:\s*"[^"\n]*"\s*\n)+)\)', metin).group(1)
        self.assertEqual(png_boyut(base64.b64decode("".join(re.findall(r'"([^"\n]*)"', blok)))), (128, 128))
        metin = oku(os.path.join(OPT, "magaza", "carotos-magaza.py"), "r")
        b64 = re.search(r'LOGO_B64 = \(\s*\n\s*"([^"\n]*)"\s*\n\)', metin).group(1)
        self.assertEqual(png_boyut(base64.b64decode(b64)), (128, 128))

    def test_desktop_dosyalari_hala_ayni_simge_adini_kullanir(self):
        beklenen = {"carotos-carotene": "carotene", "carotos-carotpot": "carotpot", "carotos-filenor": "filenor",
                    "carotos-former": "carotos-former", "carotos-gsd": "carotos-gsd",
                    "carotos-health": "carotos-health", "carotos-magaza": "carotos-magaza",
                    "carotos-usb-check": "carotos-usb-check", "carotos-poligon-ogrenci": "carotos-poligon-ogrenci",
                    "carotos-poligon-ogretmen": "carotos-poligon-ogretmen",
                    "carotos-security-panel": "carotos-security-panel"}
        for dosya, simge in beklenen.items():
            icerik = oku(os.path.join(INC, "usr", "share", "applications", dosya + ".desktop"), "r")
            self.assertIn(f"\nIcon={simge}", icerik.replace("\r\n", "\n"), dosya)


if __name__ == "__main__":
    unittest.main()
