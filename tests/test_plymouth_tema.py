#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Plymouth temasi (tools/plymouth-test): resimler, betik, kurulum betigi.

plymouth-set-default-theme ve update-initramfs sahte komutlarla taklit edilir, betik sahte kok dizinde (CAROT_KOK)
calisir. Gercek Plymouth ciktisi VM'de elle denenir. `sh` yoksa kurulum testleri atlanir.

Calistirma:  python3 tests/test_plymouth_tema.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLASOR = os.path.join(KOK, "tools", "plymouth-test")
TEMA = os.path.join(KLASOR, "tema", "carotos")
BETIK = os.path.join(KLASOR, "plymouth-tema.sh")
SH = shutil.which("sh")


class TemaDosyalariTesti(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(TEMA, "carotos.script"), encoding="utf-8") as f:
            self.betik = f.read()
        with open(os.path.join(TEMA, "carotos.plymouth"), encoding="utf-8") as f:
            self.tanim = f.read()

    def test_plymouth_tanimi(self):
        self.assertIn("Name=CarotOS", self.tanim)
        self.assertIn("ModuleName=script", self.tanim)
        self.assertIn("ImageDir=/usr/share/plymouth/themes/carotos", self.tanim)
        self.assertIn("ScriptFile=/usr/share/plymouth/themes/carotos/carotos.script", self.tanim)

    def test_betik_debianin_betigi_yalniz_renkler_degismis(self):
        """Parola penceresi ve animasyon mantigi Debian'inkiyle ayni kalmali; telif basligi korunmali."""
        self.assertIn("Copyright © 2010-2021 Aurélien Couderc", self.betik)
        self.assertIn("GPL-2.0-or-later", self.betik)
        for isim in ("password_dot_filename", "password_field_filename", "update_glow_anim", "frill_sprite",
                     "glow_sprite", "logo_sprite", "prompt_active"):
            self.assertIn(isim, self.betik, isim)
        self.assertNotIn("0.1484, 0.2266, 0.2773);", self.betik.split("CarotOS: Debian'in")[1][:400])   # eski Debian rengi gitti
        self.assertRegex(self.betik, r"SetBackgroundTopColor \(0\.0627, 0\.1020, 0\.1490\)")
        self.assertRegex(self.betik, r"SetBackgroundBottomColor \(0\.1020, 0\.1686, 0\.2431\)")

    def test_betigin_kullandigi_resimler_klasorde(self):
        kod = "\n".join(s for s in self.betik.splitlines() if not s.lstrip().startswith("#"))      # yorum satirlari sayilmaz
        adlar = set(re.findall(r'Image\s*\(\s*"([^"]+\.png)"\s*\)', kod))
        adlar |= set(re.findall(r'_filename\s*=\s*"([^"]+\.png)"', kod))
        adlar = {a for a in adlar if not a.startswith("debian")}
        for ad in adlar:
            self.assertTrue(os.path.isfile(os.path.join(TEMA, ad)), ad)
        self.assertTrue({"logo.png", "frill.png", "glow.png", "password_dot.png", "password_field.png"} <= adlar)

    def test_debian_logosu_yok(self):
        for ad in os.listdir(TEMA):
            self.assertFalse(ad.startswith("debian"), ad)

    def test_resim_boyutlari_ve_saydamlik(self):
        from PIL import Image
        boyutlar = {"frill.png": (1437, 1441), "glow.png": (1437, 1441), "logo.png": (459, 95)}
        for ad, boy in boyutlar.items():
            im = Image.open(os.path.join(TEMA, ad))
            self.assertEqual(im.size, boy, ad)
            self.assertEqual(im.mode, "RGBA", ad)
            alfa = im.getchannel("A")
            self.assertEqual(alfa.getpixel((0, 0)), 0, ad + " sol ust kose saydam olmali")
            self.assertGreater(alfa.getextrema()[1], 100, ad + " gorunur piksel icermeli")
        frill = Image.open(os.path.join(TEMA, "frill.png")).getchannel("A")
        self.assertGreater(frill.getpixel((1400, 1400)), 100)          # desen sag alt koseye dayali

    def test_logo_yazisi_mutevazi_ve_yeterince_buyuk(self):
        from PIL import Image
        alfa = Image.open(os.path.join(TEMA, "logo.png")).getchannel("A")
        kutu = alfa.getbbox()
        self.assertIsNotNone(kutu)
        genislik = kutu[2] - kutu[0]
        self.assertGreater(genislik, 459 * 0.6)            # %10 ekran genisligine olceklenince okunur kalir


@unittest.skipUnless(SH, "sh yok")
class KurulumTesti(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="ply-kok-")
        self.bin = tempfile.mkdtemp(prefix="ply-bin-")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.addCleanup(shutil.rmtree, self.bin, True)
        self.gunluk = os.path.join(self.bin, "gunluk.txt")
        self.secili = os.path.join(self.bin, "secili.txt")
        with open(self.secili, "w") as f:
            f.write("ceratopsian\n")
        self._sahte("plymouth-set-default-theme",
                    '#!/bin/sh\nif [ $# -eq 0 ]; then cat "%s"; else echo "$1" > "%s"; echo "set $1" >> "%s"; fi\n'
                    % (self.secili, self.secili, self.gunluk))
        self._sahte("update-initramfs", '#!/bin/sh\n[ -z "$STUB_INITRAMFS_FAIL" ] || exit 1\necho "initramfs $*" >> "%s"\n' % self.gunluk)

    def _sahte(self, ad, govde):
        p = os.path.join(self.bin, ad)
        with open(p, "w") as f:
            f.write(govde)
        os.chmod(p, 0o755)

    def _calistir(self, *arg, env_ek=None, yol=None):
        env = {"PATH": (yol or self.bin) + ":/usr/bin:/bin", "CAROT_KOK": self.kok}
        env.update(env_ek or {})
        return subprocess.run([SH, BETIK] + list(arg), env=env, capture_output=True, text=True, timeout=60)

    def hedef(self, *p):
        return os.path.join(self.kok, "usr", "share", "plymouth", "themes", "carotos", *p)

    def _gunluk(self):
        if not os.path.exists(self.gunluk):
            return []
        with open(self.gunluk) as f:
            return f.read().split("\n")[:-1]

    def test_kur_dosyalari_koyar_temayi_secer_initramfs_yeniler(self):
        r = self._calistir("kur")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for ad in os.listdir(TEMA):
            self.assertTrue(os.path.isfile(self.hedef(ad)), ad)
        with open(self.hedef(".onceki-tema")) as f:
            self.assertEqual(f.read().strip(), "ceratopsian")
        self.assertEqual(self._gunluk(), ["set carotos", "initramfs -u"])        # once tema secilir, sonra imaj yenilenir

    def test_ikinci_kurulum_onceki_temayi_carotos_ile_ezmez(self):
        self._calistir("kur")
        self._calistir("kur")
        with open(self.hedef(".onceki-tema")) as f:
            self.assertEqual(f.read().strip(), "ceratopsian")

    def test_geri_al_onceki_temaya_doner(self):
        self._calistir("kur")
        r = self._calistir("geri-al")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(self.hedef()))
        with open(self.secili) as f:
            self.assertEqual(f.read().strip(), "ceratopsian")
        self.assertEqual(self._gunluk()[-2:], ["set ceratopsian", "initramfs -u"])

    def test_geri_al_not_yoksa_ceratopsiana_doner(self):
        r = self._calistir("geri-al")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._gunluk()[0], "set ceratopsian")

    def test_kuru_mod_hicbir_sey_degistirmez(self):
        r = self._calistir("kur", "--kuru")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("plymouth-set-default-theme carotos", r.stdout)
        self.assertFalse(os.path.exists(self.hedef()))
        self.assertEqual(self._gunluk(), [])

    def test_komut_yoksa_apt_ipucu_verip_durur(self):
        os.remove(os.path.join(self.bin, "update-initramfs"))
        r = self._calistir("kur", yol=self.bin)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sudo apt install plymouth", r.stderr)
        self.assertFalse(os.path.exists(self.hedef()))

    def test_durum_ve_bilinmeyen_komut(self):
        r = self._calistir("durum")
        self.assertEqual(r.returncode, 0)
        self.assertIn("secili tema", r.stdout)
        self.assertIn("ceratopsian", r.stdout)
        self.assertNotEqual(self._calistir("hepsini-sil").returncode, 0)


class KaynakGuvenligiTesti(unittest.TestCase):
    def test_debianin_temasina_dokunmaz(self):
        with open(BETIK, encoding="utf-8") as f:
            kod = "\n".join(s for s in f.read().splitlines() if not s.lstrip().startswith("#"))
        self.assertNotIn("themes/ceratopsian", kod)
        self.assertNotIn("apt-get", kod)
        self.assertNotIn("rm -rf \"$TEMALAR\"", kod)

    def test_kabuk_hatasi_yok(self):
        sc = shutil.which("shellcheck")
        if not sc:
            self.skipTest("shellcheck yok")
        r = subprocess.run([sc, "-s", "sh", "-S", "warning", BETIK], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
