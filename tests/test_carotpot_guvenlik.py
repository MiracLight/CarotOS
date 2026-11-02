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


def yonet_yukle():
    import importlib.machinery
    import importlib.util
    yukleyici = importlib.machinery.SourceFileLoader("carotpot_yonet_guvenlik", YONET)
    spec = importlib.util.spec_from_loader(yukleyici.name, yukleyici)
    mod = importlib.util.module_from_spec(spec)
    yukleyici.exec_module(mod)
    return mod


@unittest.skipUnless(os.name == "posix", "sembolik bag davranisi yalnizca POSIX'te")
class JsonYazTesti(unittest.TestCase):
    def setUp(self):
        import shutil
        import tempfile
        self.Y = yonet_yukle()
        self.dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dizin, True)

    def test_normal_yazim_izin_ve_artik(self):
        yol = os.path.join(self.dizin, "e.json")
        self.Y.json_yaz(yol, [{"ip": "192.0.2.1"}])
        with open(yol, encoding="utf-8") as fh:
            self.assertIn("192.0.2.1", fh.read())
        self.assertEqual(oct(os.stat(yol).st_mode & 0o777), "0o644")
        self.assertEqual(os.listdir(self.dizin), ["e.json"], "gecici dosya kalmamali")

    def test_sembolik_bagi_takip_etmez(self):
        kurban = os.path.join(self.dizin, "kurban")
        with open(kurban, "w") as fh:
            fh.write("DOKUNMA")
        os.chmod(kurban, 0o600)
        yol = os.path.join(self.dizin, "e.json")
        os.symlink(kurban, "%s.%d.yeni" % (yol, os.getpid()))
        with self.assertRaises(OSError):
            self.Y.json_yaz(yol, [{"ip": "192.0.2.1"}])
        with open(kurban) as fh:
            self.assertEqual(fh.read(), "DOKUNMA")
        self.assertEqual(oct(os.stat(kurban).st_mode & 0o777), "0o600")


if __name__ == "__main__":
    unittest.main(verbosity=2)
