# -*- coding: utf-8 -*-
"""Vurgu dolgulu dugme/secim yazisinin okunurlugu (WCAG kontrast orani).

Eskiden button.ana her vurguda beyaz yaziydi: limon (Poligon), camgobegi (USB),
kehribar (Guvenlik Paneli) uzerinde oran 1,5-2,4:1 kaliyordu.
Calistirma: python3 tests/test_tema_kontrast.py
"""
import os
import re
import sys
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "ortak"))

try:
    import tema
except (ImportError, ValueError) as e:  # GTK yoksa
    tema = None
    NEDEN = str(e)

# Kalin dugme yazisi icin WCAG AA "buyuk/kalin yazi" esigi 3:1; hedefimiz daha yuksek.
ESIK = 4.0


@unittest.skipIf(tema is None, "PyGObject yok")
class KontrastTesti(unittest.TestCase):
    def test_bilinen_oranlar(self):
        self.assertAlmostEqual(tema.kontrast("#ffffff", "#000000"), 21.0, places=2)
        self.assertAlmostEqual(tema.kontrast("#777777", "#777777"), 1.0, places=5)

    def test_her_vurguda_dugme_yazisi_okunur(self):
        for gorunum in ("dark", "light"):
            for ad in tema.VURGULAR:
                p = tema.palet(gorunum, ad)
                oran = tema.kontrast(p["vurgu"], p["ana_yazi"])
                self.assertGreaterEqual(oran, ESIK, f"{gorunum}/{ad}: {p['vurgu']} uzerinde {p['ana_yazi']} {oran:.2f}:1")
                oran2 = tema.kontrast(p["vurgu_koyu"], p["koyu_vurgu_yazi"])
                self.assertGreaterEqual(oran2, ESIK, f"{gorunum}/{ad} koyu: {oran2:.2f}:1")

    def test_acik_vurgularda_koyu_yazi(self):
        for ad in ("poligon", "usb", "guvenlik"):
            self.assertEqual(tema.palet("dark", ad)["ana_yazi"], tema.KOYU_YAZI, ad)
        self.assertEqual(tema.palet("dark", "gsd")["ana_yazi"], "#ffffff")   # indigo: beyaz kalir

    def test_css_sabit_beyaz_kullanmaz(self):
        css = tema.css(tema.palet("dark", "poligon"))
        for secici in ("button.ana label", "button.secim:checked label", "calendar:selected"):
            satir = next(s for s in css.splitlines() if s.startswith(secici))
            self.assertNotIn("#ffffff", satir, satir)
            self.assertIn(tema.KOYU_YAZI, satir, satir)

    def test_uygulamalarda_vurgu_ustunde_sabit_beyaz_yok(self):
        """Vurgu dolgusu uzerine elle beyaz yazi yazan CSS kalmasin."""
        kotu = re.compile(r"\{p\['vurgu(_koyu)?'\]\}[^}]*color:\s*#fff|color:\s*#fff[^}]*\{p\['vurgu(_koyu)?'\]\}")
        opt = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
        for kok, _, dosyalar in os.walk(opt):
            for ad in dosyalar:
                if ad.endswith(".py"):
                    yol = os.path.join(kok, ad)
                    with open(yol, encoding="utf-8") as f:
                        for no, satir in enumerate(f, 1):
                            self.assertIsNone(kotu.search(satir), f"{yol}:{no}: {satir.strip()}")


if __name__ == "__main__":
    unittest.main()
