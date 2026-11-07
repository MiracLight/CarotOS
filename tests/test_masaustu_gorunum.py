#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Masaustu gorunum ayarlari (skel): XML gecerli mi, gtk.css hatasiz ayristiriliyor mu,
ek RAM harcayan paketler (dock/kompozitor) karar verilmeden eklenmemis mi.

Calistirma (depo kokunden):  python3 tests/test_masaustu_gorunum.py
"""
import os
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
CONFIG = os.path.join(INC, "etc", "skel", ".config")
XFCONF = os.path.join(CONFIG, "xfce4", "xfconf", "xfce-perchannel-xml")
LISTELER = os.path.join(KOK, "config", "package-lists")

# 1.4 karari: maliyeti olmayan degisiklikler yapildi; bunlar RAM olcumu yapilmadan eklenmez.
RAM_MALIYETLI = ("plank", "picom", "compton", "cairo-dock", "latte-dock", "docky", "conky", "tint2", "polybar")


def ozellik(dosya, kanal_yolu):
    """xfconf XML'inde 'a/b/c' yolundaki property'nin value degerini dondurur."""
    kok = ET.parse(os.path.join(XFCONF, dosya)).getroot()
    dugum = kok
    for ad in kanal_yolu.split("/"):
        dugum = next(c for c in dugum.findall("property") if c.get("name") == ad)
    return dugum.get("value")


class XfconfTesti(unittest.TestCase):
    def test_xml_dosyalari_gecerli(self):
        for ad in sorted(os.listdir(XFCONF)):
            if ad.endswith(".xml"):
                with self.subTest(ad=ad):
                    ET.parse(os.path.join(XFCONF, ad))

    def test_pencere_ayarlari(self):
        self.assertEqual(ozellik("xfwm4.xml", "general/button_layout"), "O|HMC")
        self.assertEqual(ozellik("xfwm4.xml", "general/title_alignment"), "center")
        self.assertEqual(ozellik("xfwm4.xml", "general/use_compositing"), "true")
        # "auto" GLX deneyip Mesa/llvmpipe yukluyor (VM ve GPU'suz makinede xfwm4 gercek payi 76 MB); "xpresent" ayni
        # gorunumle 12 MB (dev VM olcumu, 8 Kasim 2026: kullanilan bellek 666 -> 630 MB). Gercek donanimda dogrulanmadi.
        self.assertEqual(ozellik("xfwm4.xml", "general/vblank_mode"), "xpresent")
        self.assertEqual(ozellik("xfwm4.xml", "general/theme"), "Arc-Dark")

    def test_ust_panel_tema_arka_planini_kullanir(self):
        # background-style 1 renk ister ama renk tanimli degil; 0 = GTK temasi + gtk.css
        self.assertEqual(ozellik("xfce4-panel.xml", "panels/panel-1/background-style"), "0")

    def test_thunar_ayarlari(self):
        self.assertEqual(ozellik("thunar.xml", "last-location-bar"), "ThunarLocationButtons")
        self.assertEqual(ozellik("thunar.xml", "last-side-pane"), "ThunarShortcutsPane")


class PaketTesti(unittest.TestCase):
    def test_ram_maliyetli_paket_yok(self):
        for ad in sorted(os.listdir(LISTELER)):
            with open(os.path.join(LISTELER, ad), encoding="utf-8") as f:
                paketler = {s.split("#")[0].strip() for s in f}
            with self.subTest(liste=ad):
                self.assertFalse(paketler & set(RAM_MALIYETLI), paketler & set(RAM_MALIYETLI))


class GtkCssTesti(unittest.TestCase):
    def test_gtk_css_hatasiz_ayristirilir(self):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            self.skipTest("GTK yok")
        yol = os.path.join(CONFIG, "gtk-3.0", "gtk.css")
        saglayici = Gtk.CssProvider()
        hatalar = []
        saglayici.connect("parsing-error", lambda _p, bolum, hata: hatalar.append((bolum.get_start_line() + 1, hata.message)))
        try:
            saglayici.load_from_path(yol)
        except Exception as e:  # GLib.Error
            hatalar.append((0, str(e)))
        self.assertEqual(hatalar, [])


if __name__ == "__main__":
    unittest.main()
