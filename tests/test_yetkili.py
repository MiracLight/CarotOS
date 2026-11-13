#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ortak/yetkili.py: root olarak calisacak programlar yalnizca sistem dizinlerinde aranir (GTK gerektirmez).

Calistirma:  python3 tests/test_yetkili.py
"""
import os
import shutil
import stat
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORTAK = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "ortak")
if ORTAK not in sys.path:
    sys.path.insert(0, ORTAK)

import yetkili  # noqa: E402


class SistemYoluTesti(unittest.TestCase):
    def setUp(self):
        self.dizin = tempfile.mkdtemp(prefix="yetkili-test-")
        self.addCleanup(shutil.rmtree, self.dizin, True)

    def program(self, dizin, ad, calisabilir=True):
        os.makedirs(dizin, exist_ok=True)
        yol = os.path.join(dizin, ad)
        with open(yol, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(yol, 0o755 if calisabilir else 0o644)
        return yol

    def test_yalnizca_verilen_dizinlerde_aranir_PATH_yok_sayilir(self):
        sistem = os.path.join(self.dizin, "usr", "bin")
        kullanici = os.path.join(self.dizin, "home", ".local", "bin")
        gercek = self.program(sistem, "tcpdump")
        self.program(kullanici, "tcpdump")
        self.program(kullanici, "yalnizkullanicida")
        eski = os.environ.get("PATH", "")
        os.environ["PATH"] = kullanici + os.pathsep + eski       # ~/.profile'in yaptigi gibi BASA eklenir
        self.addCleanup(os.environ.__setitem__, "PATH", eski)
        self.assertEqual(shutil.which("tcpdump"), os.path.join(kullanici, "tcpdump"))   # sorunun kendisi
        self.assertEqual(yetkili.sistem_yolu("tcpdump", (sistem,)), gercek)
        self.assertIsNone(yetkili.sistem_yolu("yalnizkullanicida", (sistem,)))

    def test_dizin_sirasi_ve_calistirilabilirlik(self):
        a, b = os.path.join(self.dizin, "a"), os.path.join(self.dizin, "b")
        self.program(a, "arac", calisabilir=False)
        ikinci = self.program(b, "arac")
        if os.name != "nt":
            self.assertEqual(yetkili.sistem_yolu("arac", (a, b)), ikinci)
        os.makedirs(os.path.join(b, "dizin"))
        self.assertIsNone(yetkili.sistem_yolu("dizin", (b,)))

    def test_gecersiz_adlar(self):
        sistem = os.path.join(self.dizin, "bin")
        self.program(sistem, "arac")
        for ad in ("", "../arac", "/bin/arac", "bin/arac", "-arac", "arac x", "arac\n", "a" * 65, None, 5, ["arac"],
                   "arac;id", "$(id)"):
            self.assertIsNone(yetkili.sistem_yolu(ad, (sistem,)), repr(ad))

    def test_varsayilan_dizinler_yalnizca_root_dizinleri(self):
        self.assertEqual(yetkili.SISTEM_DIZINLERI, ("/usr/sbin", "/usr/bin", "/sbin", "/bin"))
        for d in yetkili.SISTEM_DIZINLERI:
            self.assertFalse(d.startswith(("/usr/local", "/home", "/tmp", "/opt")), d)
        if os.name != "nt" and os.path.isdir("/usr/bin"):
            self.assertEqual(os.stat("/usr/bin").st_uid, 0)
            self.assertFalse(os.stat("/usr/bin").st_mode & stat.S_IWOTH)
            self.assertEqual(os.path.dirname(yetkili.sistem_yolu("sh") or "/bin/sh") in yetkili.SISTEM_DIZINLERI, True)

    def test_temiz_ortam(self):
        os.environ["LC_ALL"] = "tr_TR.UTF-8"
        self.addCleanup(os.environ.pop, "LC_ALL", None)
        ortam = yetkili.temiz_ortam({"EK": "1"})
        self.assertEqual(ortam["PATH"], "/usr/sbin:/usr/bin:/sbin:/bin" if os.pathsep == ":" else ortam["PATH"])
        self.assertEqual((ortam["LC_ALL"], ortam["LANGUAGE"], ortam["EK"]), ("C", "C", "1"))
        self.assertEqual(os.environ["LC_ALL"], "tr_TR.UTF-8")       # surecin kendi ortami degismez


if __name__ == "__main__":
    unittest.main()
