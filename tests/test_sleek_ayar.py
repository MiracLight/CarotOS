#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Sleek Theme: gtk.css blogu, dogrulama, pencere dumani.

Calistirma:  xvfb-run -a python3 tests/test_sleek_ayar.py
"""
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader

sys.dont_write_bytecode = True
KOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "includes.chroot")
_EV = tempfile.mkdtemp(prefix="sleek-test-")
os.environ.update(HOME=_EV, XDG_CONFIG_HOME=os.path.join(_EV, "c"),
                  XDG_DATA_HOME=os.path.join(_EV, "d"), LANG="tr_TR.UTF-8")
for _k in ("LC_ALL", "LC_MESSAGES"):
    os.environ.pop(_k, None)
unittest.addModuleCleanup(shutil.rmtree, _EV, True)
os.makedirs(os.path.join(_EV, "d", "applications"))
for _k in "abc":
    with open(os.path.join(_EV, "d", "applications", _k + ".desktop"), "w") as _f:
        _f.write("[Desktop Entry]\nType=Application\nName=%s\nExec=true\n" % _k)

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk
    y = SourceFileLoader("sleek_ayar", os.path.join(KOK, "opt/carotos/sleek-ayar/carotos-sleek-ayar.py"))
    m = module_from_spec(spec_from_loader("sleek_ayar", y))
    y.exec_module(m)
    EKRAN = Gtk.init_check()[0]
except (ImportError, ValueError):
    m, EKRAN = None, False


@unittest.skipUnless(m, "GTK yok")
class Mantik(unittest.TestCase):
    def test_yazi_blogu_yaz_degistir_kaldir(self):
        for ilk in ("", "button { color: red; }\n", "a {}\n\n"):
            acik = m.yazi_blogu(ilk, "acik")
            self.assertTrue(acik.startswith(ilk))
            koyu = m.yazi_blogu(acik, "koyu")
            self.assertEqual(koyu.count(m.BAS), 1)
            self.assertIn("#14161d", koyu)
            self.assertNotIn("#e6e9ef", koyu)
            self.assertIn("menu label", koyu)
            self.assertEqual(m.yazi_blogu(koyu, None), ilk)
        for yarim in (m.BAS + "\nx", m.SON, m.SON + m.BAS):
            with self.assertRaises(ValueError):
                m.yazi_blogu(yarim, "acik")

    def test_yazi_kaydet_dosya(self):
        yol = os.path.join(_EV, "c", "gtk-3.0", "gtk.css")
        m.yazi_kaydet("koyu")
        self.assertEqual(stat.S_IMODE(os.stat(yol).st_mode), 0o644)
        m.yazi_kaydet(None)
        with open(yol) as f:
            self.assertEqual(f.read(), "")

    def test_panel_dogrula(self):
        v = m.PANEL_SLEEK
        for p in (None, [], {"renk": "red", "opaklik": 101, "yazi": "x"}, {"opaklik": True, "yazi": []}):
            self.assertEqual(m.panel_dogrula(p, v), v)
        iyi = {"renk": "#ABCDEF", "opaklik": 0, "yazi": "koyu"}
        self.assertEqual(m.panel_dogrula(iyi, v), iyi)

    def test_panel_oku_yaz(self):
        komutlar, asil = [], m.calistir
        self.addCleanup(setattr, m, "calistir", asil)

        def sahte(*a):
            komutlar.append(a)
            return 0, "1\n" if a[4].endswith("style") else \
                "Value is an array with 4 items:\n\n0.000000\n0.070588\n0.223529\n0.750000\n"
        m.calistir = sahte
        self.assertEqual(m.panel_oku(), {"renk": "#001239", "opaklik": 75})
        m.panel_yaz({"renk": "#ff0000", "opaklik": 50})
        self.assertEqual([komutlar[2][i + 1] for i, x in enumerate(komutlar[2]) if x == "-s"],
                         ["1.000000", "0.000000", "0.000000", "0.500000"])
        m.calistir = lambda *a: (0, "bozuk")
        self.assertEqual(m.panel_oku(), {})


@unittest.skipUnless(EKRAN, "ekran yok")
class PencereDumani(unittest.TestCase):
    def test_pencere(self):
        m.calistir, m.modernlestir = (lambda *a: (1, "")), (lambda komut: m.KOD_EKSIK)
        p = m.Pencere(None)
        p.show()
        dongu = GLib.MainLoop()

        def don(ms):
            GLib.timeout_add(ms, dongu.quit)
            dongu.run()

        def bul(w, tur):
            sonuc = [w] if isinstance(w, tur) else []
            return sonuc + [x for c in (w.get_children() if isinstance(w, Gtk.Container) else []) for x in bul(c, tur)]
        don(200)
        olcekler = bul(p, Gtk.Scale)
        self.assertEqual(len(olcekler), 4)
        for d in (50, 60, 70):
            olcekler[3].set_value(d)         # simge boyu: ust sinira kirpilir
        yol = m.yanpanel.ayar_yolu()
        self.assertFalse(os.path.exists(yol))            # debounce
        don(300)
        with open(yol) as f:
            veri = json.load(f)
        self.assertEqual(veri["yan"]["simge"], 64)
        self.assertNotIn("panel", veri)                  # dokunulmayan bolum yazilmaz
        self.assertIsNone(veri["yan"]["uygulamalar"])
        if os.environ.get("SLEEK_GORUNTU"):
            don(300)
            import cairo
            a = p.kutu.get_allocation()
            yuzey = cairo.ImageSurface(cairo.FORMAT_ARGB32, a.width, a.height)
            p.kutu.draw(cairo.Context(yuzey))
            yuzey.write_to_png(os.environ["SLEEK_GORUNTU"])
        p.anahtar.set_active(True)                       # paketler eksik: yonlendirme, anahtar geri doner
        don(300)
        self.assertFalse(p.anahtar.get_active())
        self.assertEqual(p.durum.get_text(), m.METIN["eksik"]["tr"])
        # uygulama listesi: asagi tasi, cikar (kaldirilmis uygulama listelenmez)
        p.veri["yan"]["uygulamalar"] = ["a.desktop", "yok.desktop", "b.desktop", "c.desktop"]
        p._ciz()

        def dugme(ipucu, sira):
            return [d for d in bul(p, Gtk.Button) if d.get_tooltip_text() == m.METIN[ipucu]["tr"]][sira]
        self.assertFalse(dugme("yukari", 0).get_sensitive())
        dugme("asagi", 0).clicked()
        dugme("cikar", 2).clicked()
        p._bekleyenleri_yap()
        with open(yol) as f:
            self.assertEqual(json.load(f)["yan"]["uygulamalar"], ["b.desktop", "a.desktop"])
        GLib.timeout_add(300, lambda: [w.response(Gtk.ResponseType.CLOSE) for w in Gtk.Window.list_toplevels()
                                       if isinstance(w, Gtk.Dialog)] and False)
        p._ekle_penceresi([], None)                      # secim penceresi acilir ve kapanir
        p._yan_sifirla()
        with open(yol) as f:
            self.assertEqual(json.load(f), {})
        p.destroy()


if __name__ == "__main__":
    unittest.main()
