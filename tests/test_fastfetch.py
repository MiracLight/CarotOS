# -*- coding: utf-8 -*-
"""fastfetch: logo + bilgi sutunu hizasi.

Gercek fastfetch 2.40.4 ile olculdu: bilgi metni logonun hemen yanindan (logo genisligi + 4 bosluk = 44. sutun)
baslar ve fastfetch uzun degerleri KESMEZ; terminal genisligini asan satir sarilir ve sonraki satirlar kayar.
Onlem: (1) uzun degerler (Host, GPU) bicimle kisaltilir, (2) terminal 100 sutundan darsa bashrc'deki fonksiyon
logosuz calistirir. Bu testler o iki kurali ve logo dosyasinin genisligini korur.
"""
import json
import os
import re
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
CONFIG = os.path.join(INC, "etc", "skel", ".config", "fastfetch", "config.jsonc")
LOGO = os.path.join(INC, "usr", "share", "carotos", "carotos_ascii.txt")
BASHRC = os.path.join(INC, "etc", "skel", ".bashrc")
PADDING = 4          # fastfetch'in logo ile metin arasindaki varsayilan boslugu
ESIK = 100           # varsayilan terminal genisligi (MiscDefaultGeometry=100x30)


def oku(yol):
    with open(yol, "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


class FastfetchTesti(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads(oku(CONFIG))
        self.logo_satirlari = oku(LOGO).rstrip("\n").split("\n")

    def test_logo_yalniz_ascii_ve_40_sutundan_dar(self):
        metin = oku(LOGO)
        self.assertTrue(all(ord(c) < 128 for c in metin), "logoda ASCII disi karakter var")
        self.assertNotIn("\t", metin)
        self.assertLessEqual(max(len(s) for s in self.logo_satirlari), 40)
        self.assertLessEqual(len(self.logo_satirlari), 22)

    def test_uzun_degerler_kisaltilir(self):
        bicim = {m["type"]: m.get("format", "") for m in self.cfg["modules"] if isinstance(m, dict)}
        for tur in ("host", "gpu"):
            m = re.search(r"~0,(\d+)\}", bicim.get(tur, ""))
            self.assertIsNotNone(m, tur + " bicimi kisaltmiyor (uzun donanim adi satiri sarar)")
            self.assertLessEqual(int(m.group(1)), 40)

    def test_dar_terminalde_logosuz_calistirir(self):
        rc = oku(BASHRC)
        self.assertRegex(rc, r"(?m)^fastfetch\(\) \{")
        self.assertIn("tput cols", rc)
        self.assertIn("-lt %d" % ESIK, rc)
        self.assertIn("--logo none", rc)

    def test_esik_aritmetigi(self):
        # logo + bosluk + 56 sutunluk bilgi alani = esik: Host/GPU icin 6 + 40 bu alana sigar
        genislik = max(len(s) for s in self.logo_satirlari)
        self.assertLessEqual(genislik + PADDING + 56, ESIK)


if __name__ == "__main__":
    unittest.main()
