#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Etik koruma onay pencereleri (GTK gerekir; ekran yoksa atlanir).

Guvenlik Paneli'nin gercek ToolPage._etik_onay akisi sahte bir HOME ile
denenir: yerel hedefte pencere yok, ozel agda bir kez soru, acik hedefte
elle yazim, vazgecme, gunluk ve hatirlanan aglar.

Calistirma:  xvfb-run -a python3 tests/test_etik_koruma_arayuz.py
"""
import importlib.util
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos",
                     "security-panel", "carotos-security-panel.py")

EKRAN = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class EtikPencereTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk, GLib
        except (ImportError, ValueError) as exc:
            raise unittest.SkipTest("GTK yok: %s" % exc)
        cls.Gtk, cls.GLib = Gtk, GLib
        cls.ev = tempfile.TemporaryDirectory()
        os.environ["HOME"] = cls.ev.name           # ayarlar/gunluk gercek HOME'a yazilmasin
        os.environ["XDG_CONFIG_HOME"] = os.path.join(cls.ev.name, ".config")
        spec = importlib.util.spec_from_file_location("carotos_panel_test", PANEL)
        cls.panel = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.panel)
        cls.app = cls.panel.PanelApp()
        cls.sayfa = cls.app.pages["nmap"]

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()
        cls.ev.cleanup()

    def setUp(self):
        self.app.settings.pop("onayli_aglar", None)
        if os.path.exists(self.panel.ETIK_GUNLUGU):
            os.remove(self.panel.ETIK_GUNLUGU)
        self.app.lang = "tr"
        self.sayfa.output_buffer.set_text("")

    def _pencere_bul(self):
        for w in self.Gtk.Window.list_toplevels():
            if isinstance(w, self.Gtk.Dialog) and w.get_visible():
                return w
        return None

    def _calistir(self, hedef, eylem):
        """_etik_onay'i cagirir; pencere acilinca eylem(pencere) uygulanir.
        Donus: (sonuc, pencere_acildi_mi)."""
        durum = {"acildi": False}

        def kontrol():
            pencere = self._pencere_bul()
            if pencere is None:
                return True        # henuz acilmadi, tekrar bak
            durum["acildi"] = True
            eylem(pencere)
            return False

        def guvenlik():            # takilmaya karsi: 4 sn sonra acik pencereyi kapat
            pencere = self._pencere_bul()
            if pencere is not None:
                pencere.response(self.Gtk.ResponseType.CANCEL)
            return False

        self.GLib.timeout_add(50, kontrol)
        self.GLib.timeout_add(4000, guvenlik)
        sonuc = self.sayfa._etik_onay({"target": hedef, "scan_key": 0})
        return sonuc, durum["acildi"]

    @staticmethod
    def _dugmeler(pencere, Gtk):
        ok = pencere.get_widget_for_response(Gtk.ResponseType.OK)
        iptal = pencere.get_widget_for_response(Gtk.ResponseType.CANCEL)
        return ok, iptal

    def _girdi(self, pencere):
        def bul(w):
            if isinstance(w, self.Gtk.Entry):
                return w
            if isinstance(w, self.Gtk.Container):
                for c in w.get_children():
                    r = bul(c)
                    if r is not None:
                        return r
            return None
        return bul(pencere.get_content_area())

    def test_yerel_hedefte_pencere_acilmaz(self):
        sonuc, acildi = self._calistir("127.0.0.1", lambda p: None)
        self.assertTrue(sonuc)
        self.assertFalse(acildi)

    def test_ozel_ag_bir_kez_sorulur_ve_hatirlanir(self):
        def evet(p):
            ok, _ = self._dugmeler(p, self.Gtk)
            self.assertTrue(ok.get_sensitive())           # yazim gerekmez
            self.assertIsNone(self._girdi(p))
            p.response(self.Gtk.ResponseType.OK)
        sonuc, acildi = self._calistir("192.168.1.5", evet)
        self.assertTrue(sonuc and acildi)
        self.assertEqual(self.app.settings["onayli_aglar"], ["192.168.1.0/24"])
        sonuc, acildi = self._calistir("192.168.1.77", lambda p: None)
        self.assertTrue(sonuc)
        self.assertFalse(acildi)                           # ayni ag: bir daha sorulmaz
        sonuc, acildi = self._calistir("192.168.2.1", lambda p: p.response(self.Gtk.ResponseType.CANCEL))
        self.assertFalse(sonuc)
        self.assertTrue(acildi)                            # baska ag: yine sorulur
        self.assertEqual(self.app.settings["onayli_aglar"], ["192.168.1.0/24"])

    def test_acik_hedef_elle_yazim_ister(self):
        gorulen = {}

        def yaz(p):
            ok, iptal = self._dugmeler(p, self.Gtk)
            girdi = self._girdi(p)
            gorulen["basta"] = ok.get_sensitive()
            girdi.set_text("8.8.8.9")
            gorulen["yanlis"] = ok.get_sensitive()
            girdi.set_text("8.8.8.8")
            gorulen["dogru"] = ok.get_sensitive()
            p.response(self.Gtk.ResponseType.OK)
        sonuc, acildi = self._calistir("8.8.8.8", yaz)
        self.assertTrue(sonuc and acildi)
        self.assertEqual(gorulen, {"basta": False, "yanlis": False, "dogru": True})
        self.assertNotIn("onayli_aglar", self.app.settings)  # acik hedef hatirlanmaz
        gunluk = open(self.panel.ETIK_GUNLUGU, encoding="utf-8").read()
        self.assertIn("\tnmap\t8.8.8.8\tdisari\tonayladi", gunluk)

    def test_vazgecince_calismaz_ve_gunluge_yazilir(self):
        sonuc, acildi = self._calistir("example.com", lambda p: p.response(self.Gtk.ResponseType.CANCEL))
        self.assertFalse(sonuc)
        self.assertTrue(acildi)
        self.assertIn("\tvazgecti", open(self.panel.ETIK_GUNLUGU, encoding="utf-8").read())
        buf = self.sayfa.output_buffer
        self.assertIn("araç çalıştırılmadı", buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False))

    def test_varsayilan_dugme_vazgec(self):
        yanit = {}

        def bak(p):
            yanit["varsayilan"] = p.get_widget_for_response(self.Gtk.ResponseType.CANCEL).has_default()
            p.response(self.Gtk.ResponseType.CANCEL)
        self._calistir("8.8.4.4", bak)
        self.assertTrue(yanit["varsayilan"])

    def test_ingilizce_pencere_metni(self):
        self.app.lang = "en"
        gorulen = {}

        def bak(p):
            gorulen["baslik"] = p.get_title()
            p.response(self.Gtk.ResponseType.CANCEL)
        self._calistir("8.8.8.8", bak)
        self.assertEqual(gorulen["baslik"], "This target doesn't look like yours")

    def test_ayarlarda_onayli_aglar_sifirlanir(self):
        ayar = self.app.settings_page
        self.app.settings["onayli_aglar"] = ["192.168.1.0/24", "10.0.0.0/24"]
        ayar.retranslate()
        self.assertIn("2", ayar.onayli_sayi.get_text())
        self.assertTrue(ayar.onayli_btn.get_sensitive())
        ayar.onayli_sifirla()
        self.assertEqual(self.app.settings["onayli_aglar"], [])
        self.assertFalse(ayar.onayli_btn.get_sensitive())
        # kalici: ayar dosyasina yazildi ve arac bir sonraki taramada yeniden sorar
        with open(self.panel.CONFIG_PATH, encoding="utf-8") as f:
            import json
            self.assertEqual(json.load(f).get("onayli_aglar"), [])
        self.app.lang = "en"
        ayar.retranslate()
        self.assertEqual(ayar.onayli_btn.get_label(), "Reset confirmed networks")
        self.app.lang = "tr"
        ayar.retranslate()


if __name__ == "__main__":
    unittest.main()
