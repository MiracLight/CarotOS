#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISO'ya giren onyukleme ayarlari: GRUB suresi, sessiz acilis, Plymouth temasi (dosyalar, hook, paketler).

Gercek derleme ve acilis VM'de denenir; bu test dosyalarin yerinde ve birbiriyle tutarli oldugunu denetler
(tools/ altindaki denenmis kopyalarla ISO kopyalari ayni olmali).

Calistirma:  python3 tests/test_iso_onyukleme.py
"""
import filecmp
import os
import re
import shutil
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(KOK, "config")
INC = os.path.join(CONFIG, "includes.chroot")
HOOK = os.path.join(CONFIG, "hooks", "live", "9996-carotos-onyukleme.hook.chroot")
TOOLS_TEMA = os.path.join(KOK, "tools", "plymouth-test", "tema", "carotos")
ISO_TEMA = os.path.join(INC, "usr", "share", "plymouth", "themes", "carotos")


def oku(yol):
    with open(yol, "rb") as f:
        return f.read().replace(b"\r\n", b"\n").decode("utf-8")


def kod_satirlari(metin):
    return [s for s in metin.splitlines() if s.strip() and not s.lstrip().startswith("#")]


class DosyalarTutarliTesti(unittest.TestCase):
    def test_plymouth_temasi_tools_ile_ayni(self):
        adlar = sorted(os.listdir(TOOLS_TEMA))
        self.assertEqual(sorted(os.listdir(ISO_TEMA)), adlar)
        for ad in adlar:
            self.assertTrue(filecmp.cmp(os.path.join(TOOLS_TEMA, ad), os.path.join(ISO_TEMA, ad), shallow=False), ad)

    def test_sure_betigi_tools_ile_ayni_ve_yerinde(self):
        iso = os.path.join(INC, "etc", "grub.d", "99_carotos_sure")
        arac = os.path.join(KOK, "tools", "grub-test", "grub.d", "99_carotos_sure")
        self.assertEqual(oku(iso), oku(arac))
        self.assertIn("set timeout=", oku(iso))

    def test_debian_logosu_temada_yok(self):
        for ad in os.listdir(ISO_TEMA):
            self.assertFalse(ad.startswith("debian"), ad)
        self.assertTrue(os.path.isfile(os.path.join(ISO_TEMA, "carotos.plymouth")))

    def test_systemd_sessiz_ayari(self):
        s = oku(os.path.join(INC, "etc", "systemd", "system.conf.d", "zz-carotos-sessiz.conf"))
        self.assertEqual(kod_satirlari(s), ["[Manager]", "ShowStatus=error"])


class GrubAyariTesti(unittest.TestCase):
    def setUp(self):
        self.cfg = oku(os.path.join(INC, "etc", "default", "grub.d", "carotos.cfg"))

    def test_ozel_tema_ve_arka_plan_yok(self):
        kod = "\n".join(kod_satirlari(self.cfg))
        for yasak in ("GRUB_THEME", "GRUB_BACKGROUND", "GRUB_GFXPAYLOAD_LINUX", "GRUB_GFXMODE"):
            self.assertNotIn(yasak, kod, yasak)

    def test_os_prober_acik_ve_sure(self):
        kod = "\n".join(kod_satirlari(self.cfg))
        self.assertIn("GRUB_DISABLE_OS_PROBER=false", kod)
        self.assertIn('GRUB_TIMEOUT="5"', kod)
        self.assertIn('GRUB_TIMEOUT_STYLE="menu"', kod)

    def test_cekirdek_parametre_sirasi(self):
        sat = [s for s in kod_satirlari(self.cfg) if s.startswith("GRUB_CMDLINE_LINUX_DEFAULT")][0]
        p = re.search(r'"([^"]*)"', sat).group(1).split()
        self.assertLess(p.index("quiet"), p.index("splash"))
        self.assertLess(p.index("quiet"), p.index("loglevel=3"))
        self.assertIn("systemd.show_status=error", p)
        self.assertNotIn("noresume", p)                            # hibernate sonrasi is kaybi riski
        self.assertNotIn("systemd.show_status=auto", p)

    def test_ana_grub_dosyasi_yok(self):
        self.assertFalse(os.path.exists(os.path.join(INC, "etc", "default", "grub")))


class HookTesti(unittest.TestCase):
    def setUp(self):
        self.hook = oku(HOOK)

    def test_adimlar_ve_dogrulamalar(self):
        for beklenen in ("chmod 755 /etc/grub.d/99_carotos_sure", "plymouth-set-default-theme carotos",
                         "update-initramfs -u -k all", "set -e", "exit 1"):
            self.assertIn(beklenen, self.hook, beklenen)
        self.assertIn("grep -q '^Theme=carotos' /etc/plymouth/plymouthd.conf", self.hook)

    def test_initramfs_cekirdek_adi_vermeden_yenilenmez(self):
        """chroot'ta `update-initramfs -u` uname -r'a (ana makinenin cekirdegi) bakar; -k all sart."""
        for s in kod_satirlari(self.hook):
            if "update-initramfs" in s and "echo" not in s:
                self.assertIn("-k all", s)

    def test_hook_calistirilabilir_olarak_kayitli(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("git yok")
        r = subprocess.run([git, "ls-files", "-s", HOOK], capture_output=True, text=True, cwd=KOK)
        if not r.stdout.strip():
            self.skipTest("hook henuz git'te degil")
        self.assertTrue(r.stdout.startswith("100755"), r.stdout)

    def test_hook_99_ve_setup_hookundan_once_calisir(self):
        adlar = sorted(os.listdir(os.path.dirname(HOOK)))
        self.assertLess(adlar.index(os.path.basename(HOOK)), adlar.index("9999-carotos-setup.hook.chroot"))

    def test_kabuk_sozdizimi(self):
        sh = shutil.which("sh")
        if not sh:
            self.skipTest("sh yok")
        r = subprocess.run([sh, "-n", HOOK], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class PaketlerTesti(unittest.TestCase):
    def test_plymouth_ve_os_prober_paket_listesinde(self):
        satirlar = [s.strip() for s in oku(os.path.join(CONFIG, "package-lists", "carotos.list.chroot")).splitlines()
                    if s.strip() and not s.lstrip().startswith("#")]
        self.assertIn("plymouth", satirlar)
        self.assertIn("os-prober", satirlar)

    def test_secure_boot_paketleri_yok(self):
        """shim-signed ve grub-efi-amd64-signed paket listesinde OLMAMALI (CLAUDE.md)."""
        for ad in os.listdir(os.path.join(CONFIG, "package-lists")):
            icerik = oku(os.path.join(CONFIG, "package-lists", ad))
            kod = "\n".join(kod_satirlari(icerik))
            self.assertNotIn("shim-signed", kod, ad)
            self.assertNotIn("grub-efi-amd64-signed", kod, ad)


class PreseedTesti(unittest.TestCase):
    def test_kurucu_parametreleri_grub_ile_uyumlu(self):
        m = re.search(r"^d-i debian-installer/add-kernel-opts string (.+)$",
                      oku(os.path.join(CONFIG, "includes.installer", "preseed.cfg")), re.M)
        self.assertIsNotNone(m)
        p = m.group(1).split()
        self.assertIn("systemd.show_status=error", p)
        self.assertNotIn("systemd.show_status=auto", p)


if __name__ == "__main__":
    unittest.main()
