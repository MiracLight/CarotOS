#!/usr/bin/env python3
"""USB Denetimi Faz 3 testleri (GTK gerektirmez; ISO'ya girmez).

Kullanim (depo kokunden):  python3 tests/test_usb_faz3.py
"""
import importlib.util
import os
import re
import shutil
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOL = os.environ.get("USB_YOLU") or os.path.join(
    KOK, "config/includes.chroot/opt/carotos/usb/carotos-usb-check.py")


def modulu_yukle():
    glib = types.SimpleNamespace(get_user_config_dir=lambda: "/tmp",
                                 get_home_dir=lambda: "/tmp")
    repo = types.SimpleNamespace(GLib=glib)
    gi = types.ModuleType("gi")
    gi.require_version = lambda *a, **k: None
    gi.repository = repo
    eski = {k: sys.modules.get(k) for k in ("gi", "gi.repository")}
    sys.modules["gi"], sys.modules["gi.repository"] = gi, repo
    try:
        spec = importlib.util.spec_from_file_location("usb_test", YOL)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for k, v in eski.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


U = modulu_yukle()


class MetinTesti(unittest.TestCase):
    def test_ui_iki_dilli_ve_tutarli(self):
        for anahtar, sozluk in U.UI.items():
            self.assertEqual(set(sozluk), {"tr", "en"}, anahtar)
            for dil in ("tr", "en"):
                self.assertTrue(sozluk[dil].strip(), anahtar)
            self.assertEqual(set(re.findall(r"\{(\w+)\}", sozluk["tr"])),
                             set(re.findall(r"\{(\w+)\}", sozluk["en"])), anahtar)

    def test_metin_yardimcisi(self):
        self.assertEqual(U.metin({"tr": "a", "en": "b"}, "en"), "b")
        self.assertEqual(U.metin("eski duz metin", "en"), "eski duz metin")
        self.assertEqual(U.metin({"tr": "a"}, "en"), "a")

    def test_gizlilik_sozu(self):
        self.assertIn("yalnızca siz ayrıntılı taramayı başlattığınızda okunur",
                      U.UI["note"]["tr"])
        self.assertIn("only when you start the detailed scan", U.UI["note"]["en"])


class HizliKontrolTesti(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="usb-test-")
        self.addCleanup(shutil.rmtree, self.kok, True)

    def dosya(self, ad, icerik="x"):
        yol = os.path.join(self.kok, ad)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w") as fh:
            fh.write(icerik)

    def test_bulgular_iki_dilli(self):
        self.dosya("autorun.inf")
        self.dosya("fatura.pdf.exe")
        self.dosya("kur.exe")
        self.dosya(".gizli/a.exe")
        self.dosya("Belgeler.lnk")
        self.dosya("Resimler.lnk")
        os.makedirs(os.path.join(self.kok, ".sistem"))
        sonuc = U.scan_path(self.kok)
        turler = {b["kind"] for b in sonuc["findings"]}
        self.assertTrue({"autorun", "double_ext", "root_exec", "hidden_exec",
                         "lnk_worm"} <= turler, turler)
        for bulgu in sonuc["findings"]:
            for alan in ("title", "detail"):
                self.assertEqual(set(bulgu[alan]), {"tr", "en"}, bulgu["kind"])
                self.assertTrue(all(bulgu[alan].values()), bulgu["kind"])
        rapor_en = U.build_report(U.enrich(sonuc, self.kok), "en")
        self.assertIn("Autorun file", rapor_en)
        self.assertNotIn("Otomatik çalıştırma", rapor_en)

    def test_clamav_bulgusu(self):
        b = U.clamav_bulgusu({"yol": "/media/u/K/a.exe", "imza": "Win.Test.EICAR_HDB-1"})
        self.assertEqual(b["level"], U.HIGH)
        self.assertEqual(b["kind"], "clamav")
        self.assertIn("Win.Test.EICAR_HDB-1", b["title"]["en"])
        self.assertIn("Win.Test.EICAR_HDB-1", b["title"]["tr"])


class OrtakMotorTesti(unittest.TestCase):
    def test_motor_tembel_yuklenir(self):
        # Modul yuklenince motor yuklenmemis olmali (izleme modu bellegi)
        self.assertIsNone(U._motor)
        ortak = os.path.join(KOK, "config/includes.chroot/opt/carotos/ortak")
        motor = U.tarama_motoru()
        if os.path.isdir(ortak):
            self.assertIsNotNone(motor)
            self.assertTrue(hasattr(motor, "Tarama"))
            self.assertFalse(os.path.exists(os.path.join(ortak, "__pycache__")))


if __name__ == "__main__":
    unittest.main(verbosity=1)
