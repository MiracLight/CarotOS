# -*- coding: utf-8 -*-
import gettext
import importlib.machinery
import importlib.util
import io
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
KOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "includes.chroot")


def yukle(yol):
    y = importlib.machinery.SourceFileLoader(os.path.basename(yol).replace("-", "_"), os.path.join(KOK, yol))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(y.name, y))
    y.exec_module(m)
    return m


P, C = yukle("usr/bin/carotos-panel-eslestir"), yukle("usr/sbin/carotos-ceviri-ek")
KOPYA = "[Desktop Entry]\nExec=a\nName=A\nName[tr]=E\nX-XFCE-Source=file:///usr/share/applications/a.desktop\n"
ASIL = "[Desktop Entry]\nName=A\nName[tr]=T\nName[de]=D\nExec=a\n\n[Desktop Action x]\nName=Z\nExec=z\n"


class Baslatici(unittest.TestCase):
    def test_adlar_yenilenir(self):
        y = P.yeni_metin(KOPYA, ASIL)
        self.assertIn("Name[de]=D", y)
        self.assertIn("X-XFCE-Source", y)
        self.assertNotIn("Name=Z", y)
        self.assertNotIn("Name[tr]=E", y)
        self.assertIsNone(P.yeni_metin(y, ASIL))            # ikinci kez degismez

    def test_kullanicinin_degistirdigine_dokunmaz(self):
        self.assertIsNone(P.yeni_metin(KOPYA.replace("Exec=a", "Exec=benim"), ASIL))


class Css(unittest.TestCase):
    def test_eski_blok_kalkar(self):
        eski = ("/* Paneller: yari saydam koyu zemin */\n.xfce4-panel.panel,\n#XfcePanelWindow {\n"
                "  background-color: rgba(30, 33, 41, 0.90);\n  border: none;\n}\n\n.benim { color: red; }\n")
        y = P.css_onar(eski)
        self.assertNotIn("0.90", y)
        self.assertIn(".benim", y)
        self.assertIn(".xfce4-panel menu", y)
        self.assertIsNone(P.css_onar(y))

    def test_skel_zemin_zorlamaz(self):
        with open(os.path.join(KOK, "etc/skel/.config/gtk-3.0/gtk.css"), encoding="utf-8") as f:
            s = f.read()
        self.assertIsNone(P.css_onar(s))
        self.assertIn(".xfce4-panel menu label", s)


    def test_yazi_rengi_temaya_doner(self):
        y = P.css_onar(".xfce4-panel label {\n  color: #e6e9ef;\n}\n")
        self.assertIn("@theme_fg_color", y)
        self.assertIsNone(P.css_onar(y))
        self.assertIsNone(P.css_onar(".xfce4-panel label { color: #e6e9ef; }"))      # Sleek blogu


class Tema(unittest.TestCase):
    def test_panel_temayla_degisir(self):
        self.assertEqual(P.panel_karari("1", list(P.KOYU), False, False), (P.ACIK, False))
        self.assertEqual(P.panel_karari("1", list(P.ACIK), True, False), (P.KOYU, True))
        self.assertEqual(P.panel_karari("1", list(P.ACIK), False, True), (None, False))

    def test_kullanici_rengi_korunur(self):
        self.assertEqual(P.panel_karari("1", [0.8, 0.1, 0.1, 1], False, True), (None, True))
        self.assertEqual(P.panel_karari("1", [1, 1, 0.9, 1], True, True), (None, False))
        self.assertEqual(P.panel_karari("2", None, False, True), (None, None))
        self.assertEqual(P.panel_karari("0", None, False, False), (None, None))
        self.assertEqual(P.panel_karari("0", None, False, True), (P.ACIK, False))

    def test_simge_paneli_izler(self):
        self.assertEqual(P.simge_adi("Papirus-Dark", False, False), "Papirus-Light")    # acik panel: koyu simgeler
        self.assertEqual(P.simge_adi("Papirus-Light", True, True), "Papirus-Dark")
        self.assertEqual(P.simge_adi("Papirus-Light", True, False), "Papirus")          # acik tema, koyu panel
        self.assertIsNone(P.simge_adi("Papirus-Dark", True, True))
        self.assertIsNone(P.simge_adi("elementary", False, False))

    def test_rgba(self):
        self.assertEqual(P.rgba_coz("Value is an array with 4 items:\n\n0.118000\n0,1\n0.2\n1"), [0.118, 0.1, 0.2, 1])
        self.assertIsNone(P.rgba_coz(""))

    def test_pil(self):
        with tempfile.TemporaryDirectory() as k:
            def ekle(ad, **d):
                os.makedirs(os.path.join(k, ad))
                for a, v in d.items():
                    with open(os.path.join(k, ad, a), "w") as f:
                        f.write(v + "\n")
            ekle("AC", type="Mains")
            ekle("hid", type="Battery", scope="Device")
            ekle("BAT1", type="Battery", present="0")
            self.assertFalse(P.pil_var(k))
            ekle("BAT0", type="Battery", present="1")
            self.assertTrue(P.pil_var(k))


class Ceviri(unittest.TestCase):
    def test_mo_yazilir_okunur(self):
        bas = "Content-Type: text/plain; charset=UTF-8\n"
        t = gettext.GNUTranslations(io.BytesIO(C.mo_yaz({"Select _All": "_Tümünü Seç", "a": "b"}, bas)))
        self.assertEqual(t.gettext("Select _All"), "_Tümünü Seç")
        self.assertEqual(t.gettext("a"), "b")


if __name__ == "__main__":
    unittest.main()
