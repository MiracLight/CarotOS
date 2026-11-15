#!/usr/bin/env python3
"""Bosta bellek azaltma kararlari (ISO duzeyi): ModemManager varsayilan kapali,
xiccd (ve onunla colord) oturumda baslamaz, USB izleyici GLib'siz kalir.

Kullanim (depo kokunden):  python3 tests/test_bellek_azaltma.py
"""
import os
import re
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = os.path.join(KOK, "config", "includes.chroot")


def oku(*parca):
    with open(os.path.join(*parca), encoding="utf-8") as fh:
        return fh.read()


class ModemManagerKancasi(unittest.TestCase):
    def setUp(self):
        self.hook = oku(KOK, "config", "hooks", "live", "9999-carotos-setup.hook.chroot")

    def test_varsayilan_kapatilir_ve_dogrulanir(self):
        self.assertIn("systemctl disable ModemManager.service", self.hook)
        # karar sessizce bozulmasin: hala etkinse derleme durur
        self.assertRegex(self.hook, r"is-enabled --quiet ModemManager\.service[^\n]*\n\s*echo \"CarotOS HATA")

    def test_maskelenmez(self):
        # mask edilirse Sistem Sagligi'ndaki "ac" dugmesi calismaz
        self.assertNotRegex(self.hook, r"systemctl\s+mask\s+ModemManager")


class XiccdOturumda(unittest.TestCase):
    def test_skel_gizli_autostart(self):
        d = oku(CH, "etc", "skel", ".config", "autostart", "xiccd.desktop")
        self.assertIn("[Desktop Entry]", d)
        self.assertRegex(d, r"(?m)^Hidden=true$")


class UsbIzleyici(unittest.TestCase):
    def test_autostart_hala_monitor(self):
        d = oku(CH, "etc", "xdg", "autostart", "carotos-usb-check.desktop")
        self.assertRegex(d, r"(?m)^Exec=.*carotos-usb-check\.py --monitor$")

    def test_ust_seviyede_gi_ice_aktarilmaz(self):
        kod = oku(CH, "opt", "carotos", "usb", "carotos-usb-check.py")
        self.assertIsNone(re.search(r"(?m)^(import gi|from gi)", kod))
        self.assertIsNone(re.search(r"(?m)^gi\.require_version", kod))


if __name__ == "__main__":
    unittest.main(verbosity=1)
