#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apt deposu yapilandirmasi: imza yok, dogru kanal, anahtarlik paketi yalniz Signed-By kullanir."""
import os
import re
import stat
import sys
import unittest

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APT = os.path.join(KOK, "tools", "apt")


def oku(*p):
    with open(os.path.join(APT, *p), "rb") as f:
        return f.read().replace(b"\r\n", b"\n").decode("utf-8")


class DepoYapilandirmasi(unittest.TestCase):
    def test_distributions_alanlari(self):
        d = oku("conf", "distributions")
        self.assertIn("Codename: stable", d)
        self.assertIn("Components: main", d)
        self.assertIn("Architectures: amd64 source", d)
        self.assertRegex(d, r"(?m)^ValidFor: \d+d$")

    def test_distributions_imza_icermez(self):
        # imza canli oturumda elle atilir; yapilandirmada SignWith olursa otomatik/yanlis anahtarla imzalanir
        self.assertNotRegex(oku("conf", "distributions"), r"(?m)^SignWith")

    def test_sources_dosyasi_signed_by_kullanir(self):
        s = oku("keyring-paketi", "etc", "apt", "sources.list.d", "carotos.sources")
        self.assertIn("URIs: https://apt.carotos.org", s)
        self.assertIn("Suites: stable", s)
        self.assertIn("Signed-By: /usr/share/keyrings/carotos-archive-keyring.gpg", s)
        self.assertNotIn("trusted=yes", s)
        self.assertNotIn("http://", s)

    def test_keyring_trusted_gpg_d_ye_konmaz(self):
        for kok, _, dosyalar in os.walk(os.path.join(APT, "keyring-paketi")):
            self.assertNotIn("trusted.gpg.d", kok)
        self.assertTrue(os.path.exists(os.path.join(APT, "keyring-paketi", "usr", "share", "keyrings",
                                                    "carotos-archive-keyring.gpg")))

    def test_keyring_genel_anahtar_gizli_degil(self):
        with open(os.path.join(APT, "keyring-paketi", "usr", "share", "keyrings", "carotos-archive-keyring.gpg"),
                  "rb") as f:
            ham = f.read()
        self.assertEqual(ham[0] & 0xFC, 0x98)          # OpenPGP paket etiketi 6: genel anahtar (gizli = 5, 0x94)
        self.assertLess(len(ham), 2000)

    def test_control_dosyasi(self):
        c = oku("keyring-paketi", "DEBIAN", "control")
        self.assertIn("Package: carotos-archive-keyring", c)
        self.assertIn("Architecture: all", c)
        self.assertRegex(c, r"(?m)^Version: \d{4}\.\d{2}\.\d{2}$")

    def test_by_hash_betigi_imzadan_once_ve_dogru_calisir(self):
        import importlib.util
        import shutil
        import tempfile
        import hashlib
        bh = importlib.util.spec_from_file_location("by_hash", os.path.join(APT, "by_hash.py"))
        m = importlib.util.module_from_spec(bh)
        bh.loader.exec_module(m)
        depo = tempfile.mkdtemp(prefix="bh-")
        self.addCleanup(shutil.rmtree, depo, True)
        d = os.path.join(depo, "dists", "stable", "main", "binary-amd64")
        os.makedirs(d)
        icerik = b"Package: x\n"
        with open(os.path.join(d, "Packages"), "wb") as f:
            f.write(icerik)
        ozet = hashlib.sha256(icerik).hexdigest()
        with open(os.path.join(depo, "dists", "stable", "Release"), "w", newline="") as f:
            f.write("Origin: CarotOS\nCodename: stable\nSHA256:\n %s %d main/binary-amd64/Packages\n"
                    % (ozet, len(icerik)))
        self.assertEqual(m.calistir(depo), 1)
        with open(os.path.join(d, "by-hash", "SHA256", ozet), "rb") as f:
            self.assertEqual(f.read(), icerik)
        with open(os.path.join(depo, "dists", "stable", "Release"), encoding="utf-8") as f:
            r = f.read()
        self.assertEqual(r.count("Acquire-By-Hash: yes"), 1)
        self.assertLess(r.index("Acquire-By-Hash"), r.index("SHA256:"))
        m.calistir(depo)                                                       # ikinci calistirma alan eklemez
        with open(os.path.join(depo, "dists", "stable", "Release"), encoding="utf-8") as f:
            self.assertEqual(f.read().count("Acquire-By-Hash"), 1)
        self.assertIn("by_hash.py", oku("depo-uret.sh"))

    def test_paket_betigi_kurallari(self):
        p = oku("paket-yap.sh")
        self.assertIn("--root-owner-group", p)
        self.assertNotIn("usr/local", p)                       # paket /usr/local'e yazmaz (Debian politikasi)
        self.assertIn('rm -f "$S/opt/carotos/$PAKET/ikonlar.b64"', p)
        self.assertIn("gsd|former)", p)
        self.assertIn("keyring)", p)
        self.assertIn("SOURCE_DATE_EPOCH", p)                  # tekrarlanabilir derleme: ayni surum, ayni ozet
        self.assertIn("carotos-ortak (>=", p)                  # gsd, ortak katmana bagli
        self.assertNotIn("postinst", p)                        # postinst yok: simge/masaustu onbellegi trigger ile
        t = oku("test-paket.sh")
        for parca in ("yukseltmede eski dosya kaldi", "gsd kalintisi", "former kalintisi", "kalinti dosya var",
                      "tekrarlanabilir degil"):
            self.assertIn(parca, t)

    def test_betikler(self):
        for ad in ("depo-uret.sh", "imzala-yukle.sh", "test-bos-depo.sh", "paket-yap.sh", "test-paket.sh"):
            k = oku(ad)
            self.assertTrue(k.startswith("#!/bin/bash"), ad)
            self.assertIn("set -euo pipefail", k, ad)
        y = oku("imzala-yukle.sh")
        self.assertLess(y.index("carotos-apt/pool"), y.index("carotos-apt/dists"))     # pool once, dists en son
        self.assertIn("GNUPGHOME", y)


if __name__ == "__main__":
    unittest.main()
