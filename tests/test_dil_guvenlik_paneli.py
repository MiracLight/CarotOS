#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guvenlik Paneli'nin ortak dil katmanina gecisi (pilot). GTK ve ekran yoksa atlanir.

Dokuz dilin hepsinde tum metinler hatasiz gelir (eksik ceviri Ingilizceye
duser), dil seciciye yalniz cevirisi hazir diller girer, dosyadaki ceviri
panelde gorunur, bozuk ceviri paneli cokertmez.

Calistirma:  xvfb-run -a python3 tests/test_dil_guvenlik_paneli.py
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
PANEL = os.path.join(INC, "security-panel", "carotos-security-panel.py")
sys.path.insert(0, os.path.join(INC, "ortak"))

EKRAN = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class PanelDilTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
        except (ImportError, ValueError) as exc:
            raise unittest.SkipTest("GTK yok: %s" % exc)
        import dil
        cls.dil = dil
        cls.ev = tempfile.TemporaryDirectory()
        cls.diller = tempfile.mkdtemp()
        os.environ["HOME"] = cls.ev.name
        os.environ["XDG_CONFIG_HOME"] = os.path.join(cls.ev.name, ".config")
        cls.eski_dizin = dil.DIZIN
        dil.DIZIN = cls.diller
        dil.onbellegi_temizle()
        spec = importlib.util.spec_from_file_location("carotos_panel_dil_test", PANEL)
        cls.panel = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.panel)

    @classmethod
    def tearDownClass(cls):
        cls.dil.DIZIN = cls.eski_dizin
        cls.dil.onbellegi_temizle()
        shutil.rmtree(cls.diller, True)
        cls.ev.cleanup()

    def dil_dosyasi(self, kod, metinler, etkin=True):
        with open(os.path.join(self.diller, kod + ".json"), "w", encoding="utf-8") as f:
            json.dump({"_meta": {"ad": kod, "etkin": etkin, "durum": "taslak"}, "metinler": metinler}, f)
        self.dil.onbellegi_temizle()

    def tearDown(self):
        for ad in os.listdir(self.diller):
            os.remove(os.path.join(self.diller, ad))
        self.dil.onbellegi_temizle()

    def test_dokuz_dilde_tum_metinler_hatasiz(self):
        for lang in self.dil.KODLAR:
            for anahtar in self.panel.STRINGS:
                kw = {"tool": "nmap", "err": "x", "cmd": "y", "code": 0, "ag": "z"}
                metin = self.panel.T(anahtar, lang, **kw)
                self.assertTrue(isinstance(metin, str) and metin.strip(), (lang, anahtar))
            for arac in self.panel.TOOLS:
                for alan in ("tagline", "what", "when", "example"):
                    self.assertTrue(arac[alan][lang].strip(), (lang, arac["name"], alan))
                for _anahtar, etiket, _tur, varsayilan, *_ in arac["fields"]:
                    self.assertTrue(etiket[lang].strip())
                    if isinstance(varsayilan, list):
                        for secenek in varsayilan:
                            self.assertTrue(secenek[lang].strip())

    def test_eksik_ceviri_ingilizceye_duser(self):
        self.assertEqual(self.panel.T("run", "de"), "Run")
        self.assertEqual(self.panel.T("run", "ja"), "Run")
        self.assertEqual(self.panel.T("run", "tr"), "Çalıştır")

    def test_dosyadaki_ceviri_panelde_gorunur(self):
        self.dil_dosyasi("de", {"Run": "Ausführen", "{tool} running…": "{tool} läuft…"})
        self.assertEqual(self.panel.T("run", "de"), "Ausführen")
        self.assertEqual(self.panel.T("running", "de", tool="nmap"), "nmap läuft…")
        self.assertEqual(self.panel.T("run", "fr"), "Run")             # baska dile sizmaz

    def test_bozuk_ceviri_cokertmez(self):
        self.dil_dosyasi("de", {"{tool} running…": "{werkzeug} läuft…"})
        self.assertEqual(self.panel.T("running", "de", tool="nmap"), "nmap running…")

    def test_dil_secici_yalniz_hazir_dilleri_listeler(self):
        from gi.repository import Gtk
        combo = Gtk.ComboBoxText()
        self.panel._dil_secici_doldur(combo)
        kodlar = [r[1] for r in combo.get_model()]
        self.assertEqual(len(kodlar), 2)                                # yalniz tr + en
        self.dil_dosyasi("de", {"Run": "Ausführen"})
        combo = Gtk.ComboBoxText()
        self.panel._dil_secici_doldur(combo)
        adlar = [r[0] for r in combo.get_model()]
        self.assertEqual(adlar, ["Türkçe", "English", "Deutsch (beta)"])

    def test_pencere_hazir_ve_taslak_dilde_acilir(self):
        self.dil_dosyasi("de", {"Run": "Ausführen"})
        pencere = self.panel.PanelApp()
        self.addCleanup(pencere.destroy)
        pencere.set_language("de")
        self.assertEqual(pencere.lang, "de")
        self.assertEqual(pencere.settings["language"], "de")
        pencere.retranslate()
        for sayfa in pencere.pages.values():
            sayfa.retranslate()
        # Bilinen ama etkin olmayan dil: yine acilir, metinler yedekten gelir
        pencere.set_language("ja")
        pencere.retranslate()

    def test_bozuk_kayitli_dil_ingilizceye_doner(self):
        ayar = os.path.join(os.environ["XDG_CONFIG_HOME"], "carotos-panel", "settings.json")
        os.makedirs(os.path.dirname(ayar), exist_ok=True)
        with open(ayar, "w", encoding="utf-8") as f:
            json.dump({"language": "klingon", "theme": "dark"}, f)
        pencere = self.panel.PanelApp()
        self.addCleanup(pencere.destroy)
        self.assertEqual(pencere.lang, "en")
        os.remove(ayar)


if __name__ == "__main__":
    unittest.main()
