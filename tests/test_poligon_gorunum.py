#!/usr/bin/env python3
"""Poligon gorunum ayari ve arayuz dosyalari icin GTK'siz testler (ISO'ya girmez).

Kullanim (depo kokunden):  python3 tests/test_poligon_gorunum.py
"""
import ast
import importlib.util
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLIGON = os.path.join(KOK, "config/includes.chroot/opt/carotos/poligon")


def yukle(ad):
    yol = os.path.join(POLIGON, ad + ".py")
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = yukle("gorunum_ayari")


class GorunumAyari(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="poligon-test-")
        self.eski = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self.kok

    def tearDown(self):
        if self.eski is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self.eski

    def test_varsayilan_koyu(self):
        self.assertEqual(G.gorunum_oku(), "dark")

    def test_yaz_oku(self):
        G.gorunum_yaz("light")
        self.assertEqual(G.gorunum_oku(), "light")
        G.gorunum_yaz("dark")
        self.assertEqual(G.gorunum_oku(), "dark")

    def test_gecersiz_deger_koyuya_duser(self):
        G.gorunum_yaz("mor")
        self.assertEqual(G.gorunum_oku(), "dark")

    def test_bozuk_dosya_cokmez(self):
        yol = G._ayar_dosyasi()
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text("{bozuk", encoding="utf-8")
        self.assertEqual(G.gorunum_oku(), "dark")
        yol.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(G.gorunum_oku(), "dark")

    def test_diger_ayarlar_korunur(self):
        yol = G._ayar_dosyasi()
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps({"baska": 7}), encoding="utf-8")
        G.gorunum_yaz("light")
        veri = json.loads(yol.read_text(encoding="utf-8"))
        self.assertEqual(veri, {"baska": 7, "gorunum": "light"})

    def test_yazilamayan_yerde_cokmez(self):
        os.environ["XDG_CONFIG_HOME"] = "/proc/olmayan-yer"
        G.gorunum_yaz("light")   # sessizce basarisiz olur

    def test_logo_yolu_dosya_ya_da_none(self):
        for rol in ("ogrenci", "ogretmen"):
            yol = G.logo_bul(rol)
            self.assertTrue(yol is None or os.path.isfile(yol))


class ArayuzDosyalari(unittest.TestCase):
    DOSYALAR = ("ogrenci_uygulama.py", "ogretmen_uygulama.py")

    def kaynak(self, ad):
        with open(os.path.join(POLIGON, ad), encoding="utf-8") as f:
            return f.read()

    def test_sozdizimi(self):
        for ad in self.DOSYALAR:
            ast.parse(self.kaynak(ad), ad)

    def test_metin_sozlukleri_tr_en_ayni_anahtarlar(self):
        for ad in self.DOSYALAR:
            agac = ast.parse(self.kaynak(ad), ad)
            metin = None
            for dugum in agac.body:
                if (isinstance(dugum, ast.Assign) and len(dugum.targets) == 1
                        and getattr(dugum.targets[0], "id", "") == "METIN"):
                    metin = ast.literal_eval(dugum.value)
            self.assertIsNotNone(metin, ad)
            self.assertEqual(set(metin["tr"]), set(metin["en"]),
                             ad + ": TR/EN anahtarlari ayni olmali")

    def test_eski_sabit_palet_kalmadi(self):
        """Renkler ortak temadan (tema.AKTIF) gelir; elle yazilmis eski
        lacivert palet geri donmesin."""
        for ad in self.DOSYALAR:
            kaynak = self.kaynak(ad).lower()
            for renk in ("#0b2e52", "#123a63", "#eaf4fc", "#a8c6e0", "#7fa8cc"):
                self.assertNotIn(renk, kaynak, f"{ad}: {renk}")

    def test_ortak_tema_kullaniliyor(self):
        for ad in self.DOSYALAR:
            kaynak = self.kaynak(ad)
            self.assertIn("import tema", kaynak, ad)
            self.assertIn("tema.uygula(", kaynak, ad)


if __name__ == "__main__":
    unittest.main()
