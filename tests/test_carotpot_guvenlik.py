#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotPot guvenlik testleri: root yardimcisinin engel listesi.

carotpot-yonet root olarak /var/log/carotpot altina yazarsa, orasi
carotpot hizmet kullanicisinin dizini oldugundan (LogsDirectory=) sembolik
bag saldirisina acik olurdu. Engel listesi root'a ait dizinde durmali.

Calistirma:  python3 tests/test_carotpot_guvenlik.py
"""
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
CP = os.path.join(INC, "opt", "carotos", "carotpot")
YONET = os.path.join(CP, "carotpot-yonet")
VERI = os.path.join(CP, "arayuz", "veri.py")
SERVIS = os.path.join(INC, "etc", "systemd", "system", "carotpot-engel-temizle.service")

YOL = "/var/lib/carotos/carotpot/engelliler.json"


def oku(yol):
    with open(yol, "rb") as f:
        return f.read().replace(b"\r\n", b"\n").decode("utf-8")


class EngelListesiYoluTesti(unittest.TestCase):
    def test_yol_root_dizininde_ve_tutarli(self):
        yonet = re.search(r'^ENGELLILER = "([^"]+)"', oku(YONET), re.M).group(1)
        veri = re.search(r'^ENGELLILER = "([^"]+)"', oku(VERI), re.M).group(1)
        servis = re.search(r"^ConditionPathExists=(\S+engelliler\.json)", oku(SERVIS), re.M).group(1)
        for ad, deger in (("carotpot-yonet", yonet), ("veri.py", veri), ("servis", servis)):
            with self.subTest(dosya=ad):
                self.assertEqual(deger, YOL)
                self.assertFalse(deger.startswith("/var/log/"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
