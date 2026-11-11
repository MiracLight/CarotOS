#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISO dogrulama: parmak izi her yerde anahtarin kendisinden hesaplananla ayni; imzalama betigi uctan uca calisir.

Parmak izi elle yazildigi icin (README, Karsilama, Former) yanlis bir harf kullaniciyi sahte anahtara
yonlendirebilir. Bu test parmak izini anahtar dosyasindan (OpenPGP v4: SHA-1(0x99 + uzunluk + govde)) hesaplar.

Calistirma:  python3 tests/test_iso_imza.py   (uctan uca bolum gpg/gpgv ister; WSL/Debian)
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANAHTAR = os.path.join(KOK, "tools", "apt", "keyring-paketi", "usr", "share", "keyrings", "carotos-archive-keyring.gpg")
INC = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
BETIK = os.path.join(KOK, "tools", "iso", "imzala-iso.sh")


def paketler(ham):
    """OpenPGP paketlerini (etiket, govde) olarak dolasir (eski ve yeni bicim, tek parca uzunluk)."""
    i = 0
    while i < len(ham):
        b = ham[i]
        assert b & 0x80, "OpenPGP paketi degil"
        if b & 0x40:                                # yeni bicim
            etiket, u = b & 0x3F, ham[i + 1]
            if u < 192:
                bas, uz = i + 2, u
            elif u < 224:
                bas, uz = i + 3, ((u - 192) << 8) + ham[i + 2] + 192
            else:
                bas, uz = i + 6, int.from_bytes(ham[i + 2:i + 6], "big")
        else:                                       # eski bicim
            etiket, n = (b >> 2) & 0x0F, {0: 1, 1: 2, 2: 4}[b & 0x03]
            bas, uz = i + 1 + n, int.from_bytes(ham[i + 1:i + 1 + n], "big")
        yield etiket, ham[bas:bas + uz]
        i = bas + uz


def _fpr(govde):
    assert govde[0] == 4, "v4 anahtar bekleniyor"
    return hashlib.sha1(b"\x99" + len(govde).to_bytes(2, "big") + govde).hexdigest().upper()


def parmak_izleri(yol):
    """(ana anahtar, [alt anahtarlar]) parmak izleri."""
    with open(yol, "rb") as f:
        ham = f.read()
    ana, altlar = None, []
    for etiket, govde in paketler(ham):
        if etiket == 6:
            ana = _fpr(govde)
        elif etiket == 14:
            altlar.append(_fpr(govde))
    assert ana, "genel anahtar paketi yok"
    return ana, altlar


def parmak_izi(yol):
    return parmak_izleri(yol)[0]


def bicimli(fpr):
    gruplar = [fpr[i:i + 4] for i in range(0, 40, 4)]
    return " ".join(gruplar)


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


class ParmakIziTesti(unittest.TestCase):
    def setUp(self):
        self.fpr, self.altlar = parmak_izleri(ANAHTAR)

    def test_beklenen_anahtar(self):
        self.assertEqual(self.fpr, "30E6D4B0C05EF0021309A1A09F935CD4D5D0A1F5")
        self.assertEqual(self.altlar, ["05F7D6A57B27FF88339EC9DCD71E9B987D57C088"])   # imzalama alt anahtari

    def test_her_yerde_ayni_parmak_izi(self):
        tek_bosluk = bicimli(self.fpr)                                        # 30E6 D4B0 ... A1F5
        iki_bosluk = tek_bosluk[:24] + " " + tek_bosluk[24:]                  # gpg'nin ortadaki cift boslugu
        yerler = {
            "README.md": oku(os.path.join(KOK, "README.md")),
            "Karsilama": oku(os.path.join(INC, "welcome", "carotos-welcome.py")),
            "Former": oku(os.path.join(INC, "former", "konular", "dogrula.py")),
        }
        for ad, metin in yerler.items():
            self.assertTrue(tek_bosluk in metin or iki_bosluk in metin, ad + ": parmak izi yok ya da yanlis")
            # 40 hanelik her parmak izi bu anahtara (ana ya da alt) ait olmali: yanlis kopya yakalanir
            for aday in re.findall(r"(?:[0-9A-F]{4} {0,2}){9}[0-9A-F]{4}|[0-9A-F]{40}", metin):
                temiz = aday.replace(" ", "")
                if len(temiz) == 40:
                    self.assertIn(temiz, [self.fpr] + self.altlar, ad)

    def test_karsilama_ve_former_ayni_komutlari_gosterir(self):
        sys.path.insert(0, os.path.join(INC, "ortak"))
        sys.path.insert(0, os.path.join(INC, "former"))
        import importlib
        d = importlib.import_module("konular.dogrula")
        k = oku(os.path.join(INC, "welcome", "carotos-welcome.py"))
        self.assertIn(d.KOMUT_1, k)
        self.assertIn(d.KOMUT_2, k)
        self.assertIn("/usr/share/keyrings/carotos-archive-keyring.gpg", d.KOMUT_1)
        # sistem ciktisi metinleri gercek cevirilerle ayni (coreutils/gnupg2 tr)
        self.assertIn("imza iyi", k)
        self.assertIn("imza KÖTÜ", k)
        f = oku(os.path.join(INC, "former", "konular", "dogrula.py"))
        self.assertIn('"CarotOS Archive <archive@carotos.org>" konumundaki imza iyi', f)   # gnupg2 tr ceviri
        self.assertIn("BAŞARISIZ", k)
        self.assertIn("Tamam", k)


@unittest.skipUnless(shutil.which("gpg") and shutil.which("gpgv") and shutil.which("bash") and os.name != "nt",
                     "gpg/gpgv/bash yok (WSL/Debian'da calistirin)")
class ImzalamaBetigiTesti(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="iso-imza-")
        self.addCleanup(shutil.rmtree, self.t, True)
        self.gh = os.path.join(self.t, "gnupg")
        os.mkdir(self.gh, 0o700)
        self.ortam = dict(os.environ, GNUPGHOME=self.gh)
        subprocess.run(["gpg", "--batch", "--pinentry-mode", "loopback", "--passphrase", "", "--quick-generate-key",
                        "Test <test@example.invalid>", "ed25519", "cert,sign", "1d"], env=self.ortam,
                       check=True, capture_output=True)
        self.iso = os.path.join(self.t, "iso")
        os.mkdir(self.iso)
        with open(os.path.join(self.iso, "carotos-1.4-amd64.iso"), "wb") as f:
            f.write(os.urandom(4096))

    def calistir(self):
        return subprocess.run(["bash", BETIK, self.iso], env=self.ortam, capture_output=True, text=True)

    def test_imzalar_ve_genel_anahtarla_dogrular(self):
        r = self.calistir()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ISO-IMZA-TAMAM", r.stdout)
        sums = oku(os.path.join(self.iso, "SHA256SUMS"))
        self.assertRegex(sums, r"^[0-9a-f]{64}  carotos-1\.4-amd64\.iso\n$")
        self.assertIn("BEGIN PGP SIGNATURE", oku(os.path.join(self.iso, "SHA256SUMS.sign")))
        # kullanicinin komutu: yalniz genel anahtar dosyasiyla gpgv
        genel = os.path.join(self.t, "genel.gpg")
        with open(genel, "wb") as f:
            f.write(subprocess.run(["gpg", "--export"], env=self.ortam, capture_output=True, check=True).stdout)
        v = subprocess.run(["gpgv", "--keyring", genel, "SHA256SUMS.sign", "SHA256SUMS"], cwd=self.iso,
                           capture_output=True, text=True, env=dict(os.environ, LC_ALL="C", GNUPGHOME=self.t))
        self.assertEqual(v.returncode, 0, v.stderr)
        c = subprocess.run(["sha256sum", "-c", "SHA256SUMS", "--ignore-missing"], cwd=self.iso, capture_output=True,
                           text=True, env=dict(os.environ, LC_ALL="C"))
        self.assertIn(": OK", c.stdout)

    def test_degistirilmis_iso_yakalanir(self):
        self.assertEqual(self.calistir().returncode, 0)
        with open(os.path.join(self.iso, "carotos-1.4-amd64.iso"), "ab") as f:
            f.write(b"x")
        c = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=self.iso, capture_output=True, text=True,
                           env=dict(os.environ, LC_ALL="C"))
        self.assertNotEqual(c.returncode, 0)
        self.assertIn("FAILED", c.stdout)

    def test_degistirilmis_ozet_listesi_imzayi_bozar(self):
        self.assertEqual(self.calistir().returncode, 0)
        with open(os.path.join(self.iso, "SHA256SUMS"), "a") as f:
            f.write("0" * 64 + "  sahte.iso\n")
        genel = os.path.join(self.t, "genel.gpg")
        with open(genel, "wb") as f:
            f.write(subprocess.run(["gpg", "--export"], env=self.ortam, capture_output=True, check=True).stdout)
        v = subprocess.run(["gpgv", "--keyring", genel, "SHA256SUMS.sign", "SHA256SUMS"], cwd=self.iso,
                           capture_output=True, text=True, env=dict(os.environ, LC_ALL="C", GNUPGHOME=self.t))
        self.assertNotEqual(v.returncode, 0)
        self.assertIn("BAD signature", v.stderr)

    def test_gnupghome_ve_iso_yoksa_durur(self):
        r = subprocess.run(["bash", BETIK, self.iso], env={k: v for k, v in self.ortam.items() if k != "GNUPGHOME"},
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        bos = os.path.join(self.t, "bos")
        os.mkdir(bos)
        r = subprocess.run(["bash", BETIK, bos], env=self.ortam, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(bos, "SHA256SUMS.sign")))


if __name__ == "__main__":
    unittest.main()
