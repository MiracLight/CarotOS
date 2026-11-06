#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Karşılama merkez-kol gezinme modeli (GTK'siz).

Calistirma:  python3 tests/test_karsilama_gezinme.py
"""
import ast
import os
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WELCOME = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "welcome")
sys.path.insert(0, WELCOME)

import gezinme as G  # noqa: E402


def pages_kimlikleri():
    with open(os.path.join(WELCOME, "carotos-welcome.py"), "rb") as f:
        agac = ast.parse(f.read().decode("utf-8"))
    for n in agac.body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "PAGES" and isinstance(n.value, ast.List):
            return [dict(zip([k.value for k in e.keys], e.values))["id"].value for e in n.value.elts]
    raise AssertionError("PAGES yok")


class ModelTesti(unittest.TestCase):
    def setUp(self):
        self.g = G.Gezinme()

    def test_baslangic_zorunlu_sirayla(self):
        self.assertEqual(self.g.sayfa_id(), "welcome")
        self.assertFalse(self.g.geri_var())
        self.assertFalse(self.g.atla_gorunur())          # başlangıç atlanamaz
        self.assertFalse(self.g.atla())
        self.g.ileri()
        self.assertEqual(self.g.sayfa_id(), "appearance")
        self.assertTrue(self.g.geri_var())
        self.g.ileri()
        self.assertEqual(self.g.sayfa_id(), "wallpaper")
        self.assertEqual(self.g.ileri_etiketi(), "ileri")
        self.g.ileri()
        self.assertEqual(self.g.sayfa_id(), G.HUB)

    def test_hub_geri_baslangicin_sonuna(self):
        for _ in range(3):
            self.g.ileri()
        self.g.geri()
        self.assertEqual(self.g.sayfa_id(), "wallpaper")

    def test_hub_da_atla_gorunur_ve_sona_gec(self):
        for _ in range(3):
            self.g.ileri()
        self.assertTrue(self.g.atla_gorunur())
        self.assertEqual(self.g.ileri_etiketi(), "sona_gec")
        self.assertEqual(self.g.bolum_sayfalari(), [])
        self.g.ileri()
        self.assertEqual(self.g.sayfa_id(), G.SON)

    def test_konu_acilir_gezilir_ve_bitirilir(self):
        for _ in range(3):
            self.g.ileri()
        self.assertTrue(self.g.konuyu_ac("sistem"))
        sayfalar = [k for k in G.KONULAR if k["id"] == "sistem"][0]["sayfalar"]
        self.assertEqual(self.g.bolum_sayfalari(), sayfalar)
        for beklenen in sayfalar:
            self.assertEqual(self.g.sayfa_id(), beklenen)
            son_mu = beklenen == sayfalar[-1]
            self.assertEqual(self.g.ileri_etiketi(), "konuyu_bitir" if son_mu else "ileri")
            self.assertTrue(self.g.atla_gorunur())
            self.g.ileri()
        self.assertEqual(self.g.sayfa_id(), G.HUB)               # son sayfada ileri = konuyu bitir, hub'a dön
        self.assertEqual(self.g.biten_konular(), ["sistem"])

    def test_konudan_geri_bitirmez(self):
        for _ in range(3):
            self.g.ileri()
        self.g.konuyu_ac("yazilim")
        self.g.ileri()
        self.g.geri()
        self.assertEqual(self.g.sayfa_id(), "software")
        self.g.geri()
        self.assertEqual(self.g.sayfa_id(), G.HUB)               # ilk sayfada geri = hub'a dön
        self.assertEqual(self.g.biten_konular(), [])             # bitirilmedi

    def test_konulari_atla_her_yerden_son_sayfaya(self):
        for _ in range(3):
            self.g.ileri()
        self.g.konuyu_ac("koruma")
        self.g.ileri()
        self.assertTrue(self.g.atla())
        self.assertEqual(self.g.sayfa_id(), G.SON)
        self.assertEqual(self.g.biten_konular(), [])             # atlamak bitirmek değil
        self.assertEqual(self.g.ileri_etiketi(), "bitir")
        self.assertEqual(self.g.ileri(), "bitir")
        self.g.geri()
        self.assertEqual(self.g.sayfa_id(), G.HUB)               # son sayfadan geri = hub

    def test_istenen_sirayla_birden_cok_konu(self):
        for _ in range(3):
            self.g.ileri()
        for kimlik in ("gizlilik", "sistem"):
            self.g.konuyu_ac(kimlik)
            while self.g.durum == G.Gezinme.KONU_DURUMU:
                self.g.ileri()
        self.assertEqual(self.g.biten_konular(), ["gizlilik", "sistem"])

    def test_bilinmeyen_konu(self):
        self.assertFalse(self.g.konuyu_ac("yok"))
        self.assertEqual(self.g.sayfa_id(), "welcome")

    def test_noktalar_bolum_icinde(self):
        self.assertEqual(self.g.bolum_sayfalari(), G.BASLANGIC)
        self.assertEqual(self.g.bolum_indeksi(), 0)
        self.assertTrue(self.g.bolumde_sec(2))
        self.assertEqual(self.g.sayfa_id(), "wallpaper")
        self.assertFalse(self.g.bolumde_sec(3))

    def test_biten_konular_kayittan_gelir_gecersizler_atilir(self):
        g = G.Gezinme(bitenler=["sistem", "yok"])
        self.assertEqual(g.biten_konular(), ["sistem"])

    def test_sayfaya_git(self):
        for sayfa in G.sayfa_sirasi():
            with self.subTest(sayfa=sayfa):
                self.assertTrue(self.g.sayfaya_git(sayfa))
                self.assertEqual(self.g.sayfa_id(), sayfa)
        self.assertFalse(self.g.sayfaya_git("yok"))


class VeriTutarliligiTesti(unittest.TestCase):
    def test_her_pages_kaydi_gezinmede_yer_alir(self):
        # Unutulan sayfa, sihirbazda hiç görünmeyen sayfa demektir.
        self.assertEqual(sorted(pages_kimlikleri()), sorted(G.sayfa_sirasi()))

    def test_sayfa_hic_iki_yerde_degil(self):
        sira = G.sayfa_sirasi()
        self.assertEqual(len(sira), len(set(sira)))

    def test_konu_kimlikleri_ve_metinleri(self):
        kimlikler = [k["id"] for k in G.KONULAR]
        self.assertEqual(len(kimlikler), len(set(kimlikler)))
        for k in G.KONULAR:
            self.assertTrue(k["sayfalar"], k["id"])
            for alan in ("baslik", "aciklama"):
                self.assertEqual(set(k[alan]), {"tr", "en"})
                self.assertTrue(k[alan]["tr"].strip() and k[alan]["en"].strip())

    def test_son_ve_hub_sayfalari_var(self):
        kimlikler = pages_kimlikleri()
        self.assertEqual(kimlikler[-1], G.SON)
        self.assertIn(G.HUB, kimlikler)


if __name__ == "__main__":
    unittest.main()
