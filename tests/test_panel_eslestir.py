# -*- coding: utf-8 -*-
import gettext
import importlib.machinery
import importlib.util
import io
import os
import sys
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


class Ceviri(unittest.TestCase):
    def test_mo_yazilir_okunur(self):
        bas = "Content-Type: text/plain; charset=UTF-8\n"
        t = gettext.GNUTranslations(io.BytesIO(C.mo_yaz({"Select _All": "_Tümünü Seç", "a": "b"}, bas)))
        self.assertEqual(t.gettext("Select _All"), "_Tümünü Seç")
        self.assertEqual(t.gettext("a"), "b")


if __name__ == "__main__":
    unittest.main()
