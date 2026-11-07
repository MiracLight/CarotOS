#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS GRUB tema denemesi (tools/grub-test): tema dosyalari, sure betigi ve kurulum betigi.

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


class TemaDosyalariTesti(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(TEMA, "theme.txt"), encoding="utf-8") as f:
            self.tema = f.read()

    def test_gerekli_gorseller_var_ve_gecerli_png(self):
        for ad in PNG_ADLARI:
            yol = os.path.join(TEMA, ad)
            self.assertTrue(os.path.isfile(yol), ad)
            with open(yol, "rb") as f:
                self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n", ad)

    def test_temanin_basvurdugu_dosyalar_mevcut(self):
        adlar = set(re.findall(r'(?:file|desktop-image)\s*[=:]\s*"([^"]+)"', self.tema))
        self.assertEqual(adlar, {"background.png"})              # logo yok: minimal tema
        for ad in adlar:
            self.assertTrue(os.path.isfile(os.path.join(TEMA, ad)), ad)
        stil = re.search(r'selected_item_pixmap_style\s*=\s*"([^"]+)"', self.tema).group(1)
        for k in ("c", "w", "e"):
            self.assertTrue(os.path.isfile(os.path.join(TEMA, stil.replace("*", "select_" + k).replace("select_select_", "select_"))),
                            stil)

    def test_zamanlayici_ve_menu_bilesenleri(self):
        self.assertEqual(self.tema.count("+ boot_menu"), 1)
        self.assertEqual(self.tema.count('id = "__timeout__"'), 2)      # ilerleme cubugu + sayac yazisi
        self.assertIn('text = "%d"', self.tema)

    def test_yazi_tipleri_betigin_urettigiyle_ayni(self):
        with open(BETIK, encoding="utf-8") as f:
            betik = f.read()
        for ad, boyut, dosya in (("DejaVu Sans Regular", 14, "DejaVuSans.ttf"), ("DejaVu Sans Regular", 18, "DejaVuSans.ttf"),
                                 ("DejaVu Sans Bold", 18, "DejaVuSans-Bold.ttf")):
            self.assertIn("%s %d" % (ad, boyut), self.tema)
            self.assertIn("-s %d" % boyut, betik)
            self.assertIn(dosya, betik)
        kullanilan = set(re.findall(r'"(DejaVu Sans [A-Za-z]+ \d+)"', self.tema))
        self.assertEqual(kullanilan, {"DejaVu Sans Regular 14", "DejaVu Sans Regular 18", "DejaVu Sans Bold 18"})

    def test_konum_ve_boyutlar_yuzdedir_ekran_boyutuna_bagli_degil(self):
        """Piksel ofsetleri (50%-90, 7%+196 gibi) kucuk ekranlarda ogeleri ust uste bindiriyordu."""
        for ad in ("left", "top", "width", "height"):
            for deger in re.findall(r"^\s*%s\s*=\s*(\S+)\s*$" % ad, self.tema, re.M):
                if ad in ("height",) and deger.isdigit():              # progress_bar ince cizgi kalinligi (piksel) serbest
                    continue
                self.assertTrue(re.fullmatch(r"\d+%", deger) or deger == "0", "%s = %s" % (ad, deger))
        self.assertNotIn("+ image", self.tema)

    def test_ogeler_dikeyde_ust_uste_binmez(self):
        """top/height yuzdeleri sirayla cakismamali: baslik, menu, zamanlayici, ipucu."""
        bloklar = re.split(r"^\+ ", self.tema, flags=re.M)[1:]
        aralik = []
        for b in bloklar:
            top = re.search(r"top\s*=\s*(\d+)%", b)
            yuk = re.search(r"height\s*=\s*(\d+)%", b)
            if top and yuk:
                aralik.append((int(top.group(1)), int(top.group(1)) + int(yuk.group(1)), b.split()[0]))
        aralik.sort()
        for (a0, a1, an), (b0, b1, bn) in zip(aralik, aralik[1:]):
            self.assertLessEqual(a1, b0, "%s ile %s ust uste biniyor" % (an, bn))

    def test_renkler_mavi_beyaz_paletten(self):
        for h in re.findall(r'"(#[0-9a-fA-F]{6})"', self.tema):
            r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
            self.assertGreaterEqual(b, r, "mavi baskin olmali: " + h)


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

    def test_kur_dosyalari_yazar(self):
        r = self._calistir("kur")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for ad in ("theme.txt",) + PNG_ADLARI + ("dejavu-regular-14.pf2", "dejavu-regular-18.pf2", "dejavu-bold-18.pf2"):
            self.assertTrue(os.path.isfile(self.yol("boot", "grub", "themes", "carotos", ad)), ad)
        with open(self.yol("etc", "default", "grub.d", "90-carotos-tema.cfg"), encoding="utf-8") as f:
            cfg = f.read()
        self.assertIn('GRUB_THEME="/boot/grub/themes/carotos/theme.txt"', cfg)
        self.assertIn("GRUB_DISABLE_OS_PROBER=false", cfg)
        self.assertNotIn("GRUB_GFXPAYLOAD_LINUX", cfg)
        sat = [x for x in cfg.splitlines() if x.startswith("GRUB_CMDLINE_LINUX_DEFAULT")][0]
        self.assertLess(sat.index("quiet"), sat.index("loglevel=3"))       # loglevel quiet'ten sonra gelmeli
        self.assertIn("systemd.show_status=auto", sat)
        sure = self.yol("etc", "grub.d", "99_carotos_sure")
        self.assertTrue(os.stat(sure).st_mode & stat.S_IXUSR)
        with open(self.grubcfg) as f:
            self.assertEqual(f.read(), "# yeni grub.cfg\n")
        with open(self.grubcfg + ".carotos-yedek") as f:
            self.assertEqual(f.read(), "# eski grub.cfg\n")
        self.assertFalse(os.path.exists(self.yol("etc", "default", "grub")))       # /etc/default/grub'a dokunulmaz

    def test_eski_logo_temizlenir(self):
        hedef = self.yol("boot", "grub", "themes", "carotos")
        os.makedirs(hedef)
        open(os.path.join(hedef, "logo.png"), "w").close()
        self.assertEqual(self._calistir("kur").returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(hedef, "logo.png")))

    def test_ikinci_kurulum_ilk_yedegi_ezmez(self):
        self._calistir("kur")
        self._calistir("kur")
        with open(self.grubcfg + ".carotos-yedek") as f:
            self.assertEqual(f.read(), "# eski grub.cfg\n")

    def test_kuru_mod_hicbir_sey_degistirmez(self):
        r = self._calistir("kur", "--kuru")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("grub-mkfont", r.stdout)
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

    def test_dejavu_yoksa_apt_ipucu_verir(self):
        os.remove(os.path.join(self.yazi, "DejaVuSans.ttf"))
        r = self._calistir("kur")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fonts-dejavu-core", r.stderr)

    def test_geri_al_kaldirir(self):
        self._calistir("kur")
        r = self._calistir("geri-al")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(self.yol("boot", "grub", "themes", "carotos")))
        self.assertFalse(os.path.exists(self.yol("etc", "default", "grub.d", "90-carotos-tema.cfg")))
        self.assertFalse(os.path.exists(self.yol("etc", "grub.d", "99_carotos_sure")))

    def test_durum_ve_bilinmeyen_komut(self):
        r = self._calistir("durum")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Tema klasoru", r.stdout)
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
