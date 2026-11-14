#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Yan Panel (opt/carotos/yanpanel): uygulama listesi ve siralamasi; GTK varsa acilis dumani.

Calistirma:  python3 tests/test_yanpanel.py   (arayuz dumani icin xvfb-run ile)
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BETIK = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "yanpanel", "carotos-yanpanel.py")


def yukle():
    spec = importlib.util.spec_from_file_location("carotos_yanpanel", BETIK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ListeTesti(unittest.TestCase):
    def setUp(self):
        self.mod = yukle()
        self.kok = tempfile.mkdtemp(prefix="yanpanel-")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.uyg = os.path.join(self.kok, "applications")
        os.makedirs(self.uyg)

    def yaz(self, ad, ek=""):
        with open(os.path.join(self.uyg, ad), "w", encoding="utf-8") as f:
            f.write("[Desktop Entry]\nType=Application\nName=%s\nExec=true\n%s" % (ad, ek))

    def test_yalniz_carotos_uygulamalari_ve_belirlenen_sira(self):
        for ad in ("carotos-filenor.desktop", "carotos-welcome.desktop", "carotos-magaza.desktop",
                   "carotos-yeni-arac.desktop", "carotos-security-panel.desktop", "firefox-esr.desktop",
                   "thunar.desktop", "carotos-zzz.desktop"):
            self.yaz(ad)
        self.assertEqual(self.mod.girdileri_bul(self.uyg), [
            "carotos-welcome.desktop", "carotos-magaza.desktop", "carotos-security-panel.desktop",
            "carotos-filenor.desktop", "carotos-yeni-arac.desktop", "carotos-zzz.desktop"])

    def test_gizli_olanlar_listelenmez(self):
        self.yaz("carotos-magaza.desktop")
        self.yaz("carotos-gizli.desktop", "NoDisplay=true\n")
        self.yaz("carotos-silik.desktop", "Hidden=true\n")
        self.assertEqual(self.mod.girdileri_bul(self.uyg), ["carotos-magaza.desktop"])

    def test_gecersiz_adlar_ve_eksik_klasor(self):
        self.yaz("carotos-.desktop.bak")
        self.yaz("carotos-bosluk var.desktop")
        self.assertEqual(self.mod.girdileri_bul(self.uyg), [])
        self.assertEqual(self.mod.girdileri_bul(os.path.join(self.kok, "yok")), [])

    def test_sira_listesi_gercek_dosya_adlariyla_ayni(self):
        gercek = os.path.join(KOK, "config", "includes.chroot", "usr", "share", "applications")
        mevcut = {a for a in os.listdir(gercek) if a.startswith("carotos-") and a.endswith(".desktop")}
        mevcut -= {"carotos-tarayici.desktop"}
        self.assertEqual(set(self.mod.SIRA), mevcut)            # her uygulama listede, olmayan ad yok

    def test_ayni_anda_5_simge(self):
        self.assertEqual(self.mod.GORUNEN, 5)


class BetikTesti(unittest.TestCase):
    def test_kaynak_kurallari(self):
        with open(BETIK, encoding="utf-8") as f:
            kaynak = f.read()
        self.assertTrue(kaynak.startswith("#!/usr/bin/python3 -I\n"))
        for yasak in ("shell=True", "os.system", "subprocess", "eval(", "exec("):
            self.assertNotIn(yasak, kaynak, yasak)
        compile(kaynak, BETIK, "exec")

    def test_liste_komutu_gtk_acmaz(self):
        kok = tempfile.mkdtemp(prefix="yanpanel-")
        self.addCleanup(shutil.rmtree, kok, True)
        with open(os.path.join(kok, "carotos-magaza.desktop"), "w") as f:
            f.write("[Desktop Entry]\nType=Application\nName=M\nExec=true\n")
        s = subprocess.run([sys.executable, "-I", BETIK, "--liste", "--dizin", kok], capture_output=True,
                           text=True, timeout=20, stdin=subprocess.DEVNULL)
        self.assertEqual(s.returncode, 0, s.stderr)
        self.assertEqual(s.stdout.split(), ["carotos-magaza.desktop"])


@unittest.skipUnless(os.environ.get("DISPLAY"), "ekran yok (xvfb-run ile calistirin)")
class AcilisDumaniTesti(unittest.TestCase):
    def test_panel_acilir_ve_cokmez(self):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
        except (ImportError, ValueError) as exc:
            self.skipTest("GTK yok: %s" % exc)
        kok = tempfile.mkdtemp(prefix="yanpanel-")
        self.addCleanup(shutil.rmtree, kok, True)
        uyg = os.path.join(kok, "applications")
        os.makedirs(uyg)
        for i in range(7):                                    # 5'ten fazla: kaydirma yolu da kurulur
            with open(os.path.join(uyg, "carotos-test%d.desktop" % i), "w") as f:
                f.write("[Desktop Entry]\nType=Application\nName=T%d\nExec=true\nIcon=application-x-executable\n" % i)
        ortam = dict(os.environ, XDG_DATA_DIRS=kok + ":/usr/local/share:/usr/share", XDG_RUNTIME_DIR=kok)
        # --dene: panel acilir (kayarak girer), bir kez kaydirilir, ~1 sn sonra duzgunce cikar
        s = subprocess.run([sys.executable, "-I", BETIK, "--dizin", uyg, "--dene"], env=ortam,
                           capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL)
        self.assertEqual(s.returncode, 0, s.stderr)
        self.assertNotIn("Traceback", s.stderr, s.stderr)


if __name__ == "__main__":
    unittest.main()
