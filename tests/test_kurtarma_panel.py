#!/usr/bin/env python3
"""CarotOS Kurtarma: ust panel (panel-1) baslaticisi tutarliligi."""
import os
import unittest
import xml.etree.ElementTree as ET

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROOT = os.path.join(KOK, "config", "includes.chroot")
PANEL = os.path.join(CHROOT, "etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml")
UYGULAMA = os.path.join(CHROOT, "usr/share/applications/carotos-kurtarma.desktop")


def exec_satiri(yol):
    with open(yol, encoding="utf-8") as fh:
        for s in fh.read().splitlines():
            if s.startswith("Exec="):
                return s.split("=", 1)[1]
    return None


class KurtarmaPanelTesti(unittest.TestCase):
    def setUp(self):
        self.kok = ET.parse(PANEL).getroot()
        panel1 = self.kok.find("./property[@name='panels']/property[@name='panel-1']")
        self.kimlikler = [v.get("value") for v in panel1.find("./property[@name='plugin-ids']")]

    def test_sistem_sagliginin_hemen_sonunda(self):
        self.assertEqual(self.kimlikler.count("33"), 1)
        self.assertEqual(self.kimlikler.index("33"), self.kimlikler.index("22") + 1)

    def test_eklenti_ve_baslatici(self):
        e = self.kok.find("./property[@name='plugins']/property[@name='plugin-33']")
        self.assertEqual(e.get("value"), "launcher")
        ogeler = [v.get("value") for v in e.find("./property[@name='items']")]
        self.assertEqual(len(ogeler), 1)
        yol = os.path.join(CHROOT, "etc/skel/.config/xfce4/panel/launcher-33", ogeler[0])
        self.assertTrue(os.path.isfile(yol))
        self.assertEqual(exec_satiri(yol), exec_satiri(UYGULAMA))
        with open(yol, encoding="utf-8") as fh:
            self.assertIn("X-XFCE-Source=file:///usr/share/applications/carotos-kurtarma.desktop",
                          fh.read())

    def test_kimlikler_benzersiz(self):
        self.assertEqual(len(self.kimlikler), len(set(self.kimlikler)))


if __name__ == "__main__":
    unittest.main()
