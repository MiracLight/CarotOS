# -*- coding: utf-8 -*-
"""Pil gostergesi: dizustunde sag ustte (sistem tepsisi) gorunur, masaustunde cikmaz.

Calistirma:  python3 tests/test_pil_gostergesi.py
"""
import os
import unittest
import xml.etree.ElementTree as ET

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROOT = os.path.join(KOK, "config", "includes.chroot")


class PilGostergesiTesti(unittest.TestCase):
    def test_paket_listede(self):
        with open(os.path.join(KOK, "config", "package-lists", "carotos.list.chroot"), encoding="utf-8") as f:
            self.assertIn("xfce4-power-manager", f.read().split())

    def test_tepsi_simgesi_acik(self):
        yol = os.path.join(CHROOT, "etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-power-manager.xml")
        kok = ET.parse(yol).getroot()
        ozel = {e.get("name"): e.get("value") for e in kok.iter("property")}
        self.assertEqual(ozel.get("show-tray-icon"), "true")

    def test_panelde_sistem_tepsisi_var(self):
        yol = os.path.join(CHROOT, "etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml")
        with open(yol, encoding="utf-8") as f:
            self.assertIn('value="systray"', f.read())


if __name__ == "__main__":
    unittest.main()
