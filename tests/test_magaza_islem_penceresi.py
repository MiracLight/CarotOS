#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Magaza islem penceresi: kurulum sirasinda arayuz kilitlenmemeli (GTK + ekran gerekir).

- pencere modal degil (kurulum surerken magaza gezilebilir)
- cok satirli apt ciktisi satir satir degil, toplu yazilir (ana dongu bogulmaz)
- islem suruyorken ana pencere kapanmaz (apt borusu kopup paket yari kurulu kalmasin)

Ekran yoksa atlanir. Calistirma:  xvfb-run -a python3 tests/test_magaza_islem_penceresi.py
"""
import importlib.util
import os
import sys
import tempfile
import time
import types
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPT = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")

# GLib kullanici dizinlerini ilk cagrida onbellekler: GTK'dan once sahte HOME
_EV = tempfile.mkdtemp(prefix="magaza-test-")
os.environ["HOME"] = _EV
os.environ["XDG_CONFIG_HOME"] = os.path.join(_EV, "c")
os.environ["XDG_CACHE_HOME"] = os.path.join(_EV, "k")
os.environ["XDG_DATA_HOME"] = os.path.join(_EV, "d")

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GLib
    GTK_VAR = Gtk.init_check()[0]
except (ImportError, ValueError):
    GTK_VAR = False

magaza = None
if GTK_VAR:
    sys.path.insert(0, os.path.join(OPT, "ortak"))
    _spec = importlib.util.spec_from_file_location("magaza_modulu", os.path.join(OPT, "magaza", "carotos-magaza.py"))
    magaza = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(magaza)


def calistir(komut, bitis_suresi=30):
    ebeveyn = Gtk.Window()
    sonuc = []
    p = magaza.IslemPenceresi(ebeveyn, "deneme", komut, lambda basarili: sonuc.append(basarili))
    p.baslat()
    bit = time.time() + bitis_suresi
    while not sonuc and time.time() < bit:
        while Gtk.events_pending():
            Gtk.main_iteration()
        time.sleep(0.01)
    while Gtk.events_pending():
        Gtk.main_iteration()
    return p, sonuc


@unittest.skipUnless(GTK_VAR, "ekran/GTK yok")
class IslemPenceresiTesti(unittest.TestCase):
    def test_modal_degil(self):
        p = magaza.IslemPenceresi(Gtk.Window(), "deneme", ["true"], None)
        self.assertFalse(p.get_modal())

    def test_cok_satir_toplu_yazilir(self):
        n = 6000
        p, sonuc = calistir(["sh", "-c", f"i=0; while [ $i -lt {n} ]; do echo satir$i; i=$((i+1)); done"])
        self.assertEqual(sonuc, [True])
        metin = p.tampon.get_text(p.tampon.get_start_iter(), p.tampon.get_end_iter(), False)
        self.assertEqual(len(metin.splitlines()), n)
        self.assertTrue(metin.rstrip().endswith(f"satir{n - 1}"))
        # satir basina degil, toplu yazilmis olmali (150 ms aralikla en fazla birkac on kez)
        self.assertLess(p._bosaltma_sayisi, 200, p._bosaltma_sayisi)

    def test_hata_kodu_basarisiz_bildirilir(self):
        _p, sonuc = calistir(["sh", "-c", "echo x; exit 3"])
        self.assertEqual(sonuc, [False])

    def test_olmayan_komut_hata_verir(self):
        p, sonuc = calistir(["/olmayan/komut-xyz"])
        self.assertEqual(sonuc, [False])
        metin = p.tampon.get_text(p.tampon.get_start_iter(), p.tampon.get_end_iter(), False)
        self.assertIn("[hata]", metin)


@unittest.skipUnless(GTK_VAR, "ekran/GTK yok")
class KapanmaTesti(unittest.TestCase):
    def _sahte(self, mesgul):
        uyarildi = []
        return types.SimpleNamespace(mesgul=mesgul, _mesgul_uyar=lambda: uyarildi.append(1)), uyarildi

    def test_islem_suruyorken_kapanma_engellenir(self):
        ben, uyarildi = self._sahte("install:sepet")
        self.assertTrue(magaza.MagazaPenceresi._kapanirken(ben))
        self.assertEqual(uyarildi, [1])

    def test_bostayken_kapanir(self):
        ben, uyarildi = self._sahte(None)
        self.assertFalse(magaza.MagazaPenceresi._kapanirken(ben))
        self.assertEqual(uyarildi, [])


if __name__ == "__main__":
    unittest.main()
