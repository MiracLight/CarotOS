#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS GRUB ayar denemesi (tools/grub-test): sure betigi ve kurulum betigi (Debian temasi, ozel tema yok).

GRUB'in kendisi yok: grub-mkfont, grub-mkconfig, grub-script-check ve os-prober sahte komutlarla taklit edilir,
betikler sahte bir kok dizinde (CAROT_KOK) calistirilir. Gercek GRUB cikisi VM'de elle denenir.
`sh` yoksa (Windows) atlanir.

Calistirma:  python3 tests/test_grub_tema.py
"""
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLASOR = os.path.join(KOK, "tools", "grub-test")
TEMA = os.path.join(KLASOR, "tema")
BETIK = os.path.join(KLASOR, "grub-tema.sh")
SURE = os.path.join(KLASOR, "grub.d", "99_carotos_sure")
SH = shutil.which("sh")

PNG_ADLARI = ("background.png", "select_c.png", "select_w.png", "select_e.png")


@unittest.skipUnless(SH, "sh yok")
class SureBetigiTesti(unittest.TestCase):
    def _calistir(self, prober_satir, env_ek=None):
        with tempfile.TemporaryDirectory() as d:
            if prober_satir is not None:
                p = os.path.join(d, "os-prober")
                with open(p, "w") as f:
                    f.write("#!/bin/sh\n" + "".join("echo '%s'\n" % s for s in prober_satir))
                os.chmod(p, 0o755)
            env = {"PATH": d + ":/usr/bin:/bin", "GRUB_DISABLE_OS_PROBER": "false"}
            env.update(env_ek or {})
            r = subprocess.run([SH, SURE], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_yalniz_carotos_5_sn(self):
        self.assertIn("set timeout=5\n", self._calistir([]))

    def test_baska_sistem_varsa_30_sn(self):
        out = self._calistir(["/dev/sda1@/efi/Microsoft/Boot/bootmgfw.efi:Windows Boot Manager:Windows:efi"])
        self.assertIn("set timeout=30\n", out)
        self.assertIn("sayisi: 1", out)

    def test_birden_cok_sistem(self):
        out = self._calistir(["/dev/sda1::Windows:efi", "/dev/sdb2:Ubuntu:Ubuntu:linux"])
        self.assertIn("sayisi: 2", out)
        self.assertIn("set timeout=30\n", out)

    def test_os_prober_kapaliysa_aranmaz(self):
        out = self._calistir(["/dev/sda1::Windows:efi"], {"GRUB_DISABLE_OS_PROBER": "true"})
        self.assertIn("set timeout=5\n", out)

    def test_os_prober_yoksa_cokmez(self):
        self.assertIn("set timeout=5\n", self._calistir(None))


@unittest.skipUnless(SH, "sh yok")
class KurulumBetigiTesti(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="grub-kok-")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.bin = tempfile.mkdtemp(prefix="grub-bin-")
        self.addCleanup(shutil.rmtree, self.bin, True)
        self.yazi = tempfile.mkdtemp(prefix="grub-yazi-")
        self.addCleanup(shutil.rmtree, self.yazi, True)
        for ad in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
            open(os.path.join(self.yazi, ad), "w").close()
        os.makedirs(os.path.join(self.kok, "boot", "grub"))
        self.grubcfg = os.path.join(self.kok, "boot", "grub", "grub.cfg")
        with open(self.grubcfg, "w") as f:
            f.write("# eski grub.cfg\n")
        self._sahte("grub-mkfont", '#!/bin/sh\nwhile [ $# -gt 0 ]; do [ "$1" = "-o" ] && echo font > "$2"; shift; done\n')
        self._sahte("grub-mkconfig", '#!/bin/sh\nwhile [ $# -gt 0 ]; do [ "$1" = "-o" ] && echo "# yeni grub.cfg" > "$2"; shift; done\n')
        self._sahte("grub-script-check", '#!/bin/sh\n[ -z "$STUB_CHECK_FAIL" ]\n')
        self._sahte("os-prober", "#!/bin/sh\nexit 0\n")

    def _sahte(self, ad, govde):
        p = os.path.join(self.bin, ad)
        with open(p, "w") as f:
            f.write(govde)
        os.chmod(p, 0o755)

    def _calistir(self, *arg, env_ek=None, yol=None):
        env = {"PATH": (yol or self.bin) + ":/usr/bin:/bin", "CAROT_KOK": self.kok, "CAROT_YAZI_DIZINI": self.yazi}
        env.update(env_ek or {})
        return subprocess.run([SH, BETIK] + list(arg), env=env, capture_output=True, text=True, timeout=60)

    def yol(self, *p):
        return os.path.join(self.kok, *p)

    def test_kur_ayar_ve_sure_betigini_yazar_ozel_tema_koymaz(self):
        r = self._calistir("kur")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(self.yol("etc", "default", "grub.d", "zz-carotos-grub.cfg"), encoding="utf-8") as f:
            cfg = f.read()
        self.assertNotIn("GRUB_THEME", cfg.replace("tema ayari", ""))                 # Debian temasi: tema ayari yok
        self.assertNotIn("GRUB_BACKGROUND", cfg)
        self.assertNotIn("GRUB_GFXPAYLOAD_LINUX", cfg)
        self.assertIn("GRUB_DISABLE_OS_PROBER=false", cfg)
        sat = [x for x in cfg.splitlines() if x.startswith("GRUB_CMDLINE_LINUX_DEFAULT")][0]
        self.assertLess(sat.index("quiet"), sat.index("loglevel=3"))       # loglevel quiet'ten sonra gelmeli
        self.assertIn("systemd.show_status=error", sat)
        self.assertIn("noresume", sat)
        self.assertFalse(os.path.exists(self.yol("boot", "grub", "themes")))
        sure = self.yol("etc", "grub.d", "99_carotos_sure")
        self.assertTrue(os.stat(sure).st_mode & stat.S_IXUSR)
        with open(self.grubcfg) as f:
            self.assertEqual(f.read(), "# yeni grub.cfg\n")
        with open(self.grubcfg + ".carotos-yedek") as f:
            self.assertEqual(f.read(), "# eski grub.cfg\n")
        self.assertFalse(os.path.exists(self.yol("etc", "default", "grub")))       # /etc/default/grub'a dokunulmaz

    def test_systemd_sessiz_ayari_yazilir_ve_geri_alinir(self):
        self._calistir("kur")
        yol = self.yol("etc", "systemd", "system.conf.d", "zz-carotos-sessiz.conf")
        with open(yol, encoding="utf-8") as f:
            icerik = f.read()
        self.assertIn("[Manager]", icerik)
        self.assertIn("ShowStatus=error", icerik)
        self._calistir("geri-al")
        self.assertFalse(os.path.exists(yol))

    def test_ayar_dosyasi_en_son_okunur(self):
        """/etc/default/grub.d/*.cfg alfabetik okunur; 'zz' hicbir pakete ait parcanin ardinda kalmaz."""
        self._calistir("kur")
        grubd = self.yol("etc", "default", "grub.d")
        for ornek in ("00_init.cfg", "05_debian_theme.cfg", "carotos.cfg", "desktop-base.cfg", "init-select.cfg"):
            self.assertLess(ornek, "zz-carotos-grub.cfg", ornek)
        self.assertEqual(sorted(os.listdir(grubd))[-1], "zz-carotos-grub.cfg")

    def test_onceki_denemenin_ozel_temasi_ve_ayari_temizlenir(self):
        hedef = self.yol("boot", "grub", "themes", "carotos")
        os.makedirs(hedef)
        open(os.path.join(hedef, "theme.txt"), "w").close()
        eski = self.yol("etc", "default", "grub.d", "90-carotos-tema.cfg")
        os.makedirs(os.path.dirname(eski))
        with open(eski, "w") as f:
            f.write('GRUB_THEME="/boot/grub/themes/carotos/theme.txt"\n')
        self.assertEqual(self._calistir("kur").returncode, 0)
        self.assertFalse(os.path.exists(hedef))
        self.assertFalse(os.path.exists(eski))

    def test_ikinci_kurulum_ilk_yedegi_ezmez(self):
        self._calistir("kur")
        self._calistir("kur")
        with open(self.grubcfg + ".carotos-yedek") as f:
            self.assertEqual(f.read(), "# eski grub.cfg\n")

    def test_kuru_mod_hicbir_sey_degistirmez(self):
        r = self._calistir("kur", "--kuru")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("grub-mkconfig", r.stdout)
        self.assertFalse(os.path.exists(self.yol("boot", "grub", "themes")))
        self.assertFalse(os.path.exists(self.yol("etc")))
        with open(self.grubcfg) as f:
            self.assertEqual(f.read(), "# eski grub.cfg\n")

    def test_gecersiz_grub_cfg_eskiyi_korur(self):
        r = self._calistir("kur", env_ek={"STUB_CHECK_FAIL": "1"})
        self.assertNotEqual(r.returncode, 0)
        with open(self.grubcfg) as f:
            self.assertEqual(f.read(), "# eski grub.cfg\n")
        self.assertFalse(os.path.exists(self.grubcfg + ".yeni"))

    def test_os_prober_yoksa_apt_ipucu_verip_durur(self):
        os.remove(os.path.join(self.bin, "os-prober"))
        r = self._calistir("kur", yol=self.bin)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sudo apt install os-prober", r.stderr)
        self.assertFalse(os.path.exists(self.yol("boot", "grub", "themes")))

    def test_geri_al_kaldirir(self):
        self._calistir("kur")
        r = self._calistir("geri-al")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(self.yol("etc", "default", "grub.d", "zz-carotos-grub.cfg")))
        self.assertFalse(os.path.exists(self.yol("etc", "default", "grub.d", "90-carotos-tema.cfg")))
        self.assertFalse(os.path.exists(self.yol("etc", "grub.d", "99_carotos_sure")))

    def test_durum_ve_bilinmeyen_komut(self):
        r = self._calistir("durum")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Ayar parcasi", r.stdout)
        self.assertNotEqual(self._calistir("sil-hepsini").returncode, 0)


class KaynakGuvenligiTesti(unittest.TestCase):
    def test_onyukleyiciye_ve_ana_grub_dosyasina_dokunmaz(self):
        with open(BETIK, encoding="utf-8") as f:
            k = f.read()
        kod = "\n".join(s for s in k.splitlines() if not s.lstrip().startswith("#"))
        for yasak in ("grub-install", "shim", "efibootmgr", "/etc/default/grub\"", "/etc/default/grub '", "apt-get", "apt install -y"):
            self.assertNotIn(yasak, kod, yasak)

    def test_kabuk_hatasi_yok(self):
        sc = shutil.which("shellcheck")
        if not sc:
            self.skipTest("shellcheck yok")
        r = subprocess.run([sc, "-s", "sh", "-S", "warning", BETIK, SURE], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
