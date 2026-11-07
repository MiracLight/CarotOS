#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon: tema.AcilirSecim (uzun listeler icin kaydirmali acilir secim) ve
ogretmen penceresinde varyant bolumunun yalniz varyantli gorevlerde gorunmesi.

GTK gerektirir (xvfb-run ile):  xvfb-run -a python3 tests/test_poligon_acilir_secim.py
"""
import json
import os
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot/opt/carotos")
_EV = tempfile.mkdtemp()
os.environ["HOME"] = _EV
os.environ["XDG_CONFIG_HOME"] = os.path.join(_EV, ".config")
os.makedirs(os.path.join(_EV, ".config/carotos-poligon"), exist_ok=True)
json.dump({"gorunum": "dark"}, open(os.path.join(_EV, ".config/carotos-poligon/ayar.json"), "w"))
for _y in (os.path.join(INC, "poligon"), os.path.join(INC, "carotpot"), os.path.join(INC, "ortak")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

import tema  # noqa: E402


def pompala(sn=0.2):
    t = time.time()
    while time.time() - t < sn:
        while Gtk.events_pending():
            Gtk.main_iteration()
        time.sleep(0.01)


class AcilirSecimTesti(unittest.TestCase):
    def setUp(self):
        self.s = tema.AcilirSecim()
        self.olaylar = []
        self.s.connect("changed", lambda _w: self.olaylar.append(self.s.get_active_id()))

    def test_bos(self):
        self.assertIsNone(self.s.get_active_id())
        self.assertIsNone(self.s.get_active_text())
        self.assertEqual(self.s.get_active(), -1)

    def test_secim_ve_sinyal(self):
        for i in range(30):
            self.s.append(str(i), f"oge {i}")
        self.s.set_active(0)
        self.assertEqual(self.s.get_active_text(), "oge 0")
        self.assertTrue(self.s.set_active_id("17"))
        self.assertEqual((self.s.get_active(), self.s.get_active_id(), self.s.get_active_text()),
                         (17, "17", "oge 17"))
        self.assertFalse(self.s.set_active_id("yok"))
        self.assertEqual(self.s.get_active_id(), "17")
        self.assertEqual(self.olaylar, ["0", "17"])
        self.s.set_active_id("17")                      # ayni secim: sinyal yok
        self.assertEqual(self.olaylar, ["0", "17"])

    def test_satira_tiklama(self):
        for i in range(5):
            self.s.append(str(i), f"oge {i}")
        self.s.set_active(0)
        self.s._satir_secildi(self.s._liste, self.s._liste.get_row_at_index(3))
        self.assertEqual(self.s.get_active_id(), "3")

    def test_remove_all(self):
        self.s.append("a", "A")
        self.s.set_active(0)
        self.s.remove_all()
        self.assertIsNone(self.s.get_active_id())
        self.assertEqual(self.s._yazi.get_text(), "")
        self.s.append("b", "B")
        self.s.set_active_id("b")
        self.assertEqual(self.s._yazi.get_text(), "B")

    def test_metin_degistir_sinyalsiz(self):
        self.s.append("a", "Bir")
        self.s.append("b", "Iki")
        self.s.set_active(1)
        n = len(self.olaylar)
        self.s.metni_degistir("b", "Two")
        self.assertEqual(self.s.get_active_text(), "Two")
        self.assertEqual(self.s._yazi.get_text(), "Two")
        self.assertEqual(len(self.olaylar), n)

    def test_popover_acilir_ve_yukseklik_sinirli(self):
        pencere = Gtk.Window()
        pencere.add(self.s)
        for i in range(60):
            self.s.append(str(i), f"oge {i}")
        self.s.set_active(0)
        pencere.show_all()
        pompala()
        self.s._dugme.clicked()
        pompala(0.4)
        self.assertTrue(self.s._acilir.get_visible())
        self.assertLessEqual(self.s._kaydirma.get_allocated_height(),
                             tema.AcilirSecim.EN_COK_YUKSEKLIK + 12)
        self.s._satir_secildi(self.s._liste, self.s._liste.get_row_at_index(7))
        pompala(0.2)
        self.assertFalse(self.s._acilir.get_visible())
        pencere.destroy()


class OgretmenVaryantBolumu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import ogretmen_uygulama as O
        sys.argv = ["ogretmen_uygulama.py"]
        cls.w = O.OgretmenPenceresi("nmap-01")
        cls.w.show_all()
        pompala(0.4)
        cls.w.kabuk.sec("soru_ata")
        pompala(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.w.sunucu.shutdown()
        cls.w.sunucu.server_close()
        cls.w.destroy()

    def _sec(self, gid):
        self.w._gorev_anahtarlari[gid].set_active(True)
        pompala(0.2)

    def test_varyantsiz_gorevde_bolum_gizli(self):
        for gid in ("nmap-01", "john-01", "hydra-01", "hash-02"):
            self._sec(gid)
            self.assertFalse(self.w.varyant_combo.get_visible(), gid)
            self.assertFalse(self.w.varyant_baslik_etiketi.get_visible(), gid)
            self.assertIsNone(self.w._secili_varyant())

    def test_varyantli_gorevde_bolum_gorunur(self):
        import varyantlar
        for gid in ("kodlama-02", "kodlama-01", "loganaliz-03"):
            self._sec(gid)
            self.assertTrue(self.w.varyant_combo.get_visible(), gid)
            self.assertTrue(self.w.varyant_baslik_etiketi.get_visible(), gid)
            n = varyantlar.gorev_varyant_sayisi(gid)
            self.assertEqual(len(self.w.varyant_combo._ogeler), n + 1)   # + "Otomatik"
            self.assertEqual(self.w.varyant_combo.get_active_id(), "0")
            self.assertIsNone(self.w._secili_varyant())

    def test_elle_secim_ve_atama(self):
        self._sec("kodlama-02")
        self.w.varyant_combo.set_active_id("9")
        self.assertEqual(self.w._secili_varyant(), 9)
        self.w._secili_goreve_gec(None)
        self.assertEqual(self.w.oda.gorev_varyantlari, {"kodlama-02": 9})
        self.w.varyant_combo.set_active_id("0")
        self.w._secili_goreve_gec(None)
        self.assertIn(self.w.oda.gorev_varyantlari["kodlama-02"], range(1, 21))

    def test_gorev_degisince_secim_sifirlanir(self):
        self._sec("kodlama-02")
        self.w.varyant_combo.set_active_id("5")
        self._sec("loganaliz-01")
        self.assertEqual(self.w.varyant_combo.get_active_id(), "0")
        self._sec("kodlama-02")
        self.assertEqual(self.w.varyant_combo.get_active_id(), "0")


class AcilirYonuTesti(unittest.TestCase):
    """Dil seciciler pencerenin altindaysa liste yukari, ustundeyse asagi acilir (ustte bos alan birakmaz)."""

    def _pencere(self, secim_y):
        pencere = Gtk.Window()
        pencere.set_default_size(300, 600)
        sabit = Gtk.Fixed()
        secim = tema.AcilirSecim()
        for i in range(9):
            secim.append(str(i), "dil %d" % i)
        sabit.put(secim, 10, secim_y)
        pencere.add(sabit)
        pencere.show_all()
        pompala(0.4)
        self.addCleanup(pencere.destroy)
        return secim

    def test_altta_yukari_ustte_asagi(self):
        self.assertEqual(self._pencere(540)._yon(), Gtk.PositionType.TOP)
        self.assertEqual(self._pencere(20)._yon(), Gtk.PositionType.BOTTOM)

    def test_pencereye_eklenmemisse_cokmez(self):
        self.assertEqual(tema.AcilirSecim()._yon(), Gtk.PositionType.BOTTOM)

    def test_get_model_metinleri_verir(self):
        s = tema.AcilirSecim()
        s.append("tr", "Türkçe")
        s.append("en", "English")
        self.assertEqual([r[0] for r in s.get_model()], ["Türkçe", "English"])


class DilSeciciKaynakTesti(unittest.TestCase):
    """Hicbir uygulamada dil secici eski ComboBoxText olmamali (9 dilde ustte buyuk bosluk birakiyordu)."""

    def test_dil_secicileri_acilir_secim(self):
        import re
        desen = re.compile(r"(?:lang_combo|dil_kutu|dil_dugmesi|dil_sec) = Gtk\.ComboBoxText")
        kotu = []
        for kok, _d, dosyalar in os.walk(INC):
            if "__pycache__" in kok:
                continue
            for ad in dosyalar:
                if ad.endswith(".py"):
                    yol = os.path.join(kok, ad)
                    with open(yol, encoding="utf-8") as f:
                        if desen.search(f.read()):
                            kotu.append(os.path.relpath(yol, INC))
        self.assertEqual(kotu, [], "dil seciciler tema.AcilirSecim olmali")


if __name__ == "__main__":
    unittest.main()
