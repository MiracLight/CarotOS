#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon CTF uc noktalari: gercek HTTP sunucusu (127.0.0.1, bos port).

Calistirma:  python3 tests/test_ctf_sunucu.py
"""
import json
import os
import sys
import unittest
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLIGON = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "poligon")
sys.path.insert(0, POLIGON)

import ctf_uretici as U  # noqa: E402
import ogretmen_sunucu as S  # noqa: E402

SIFRE = "abc123"


def istek(port, yol, veri=None, sorgu=None):
    url = "http://127.0.0.1:%d%s" % (port, yol)
    if sorgu is not None:
        url += "?" + urllib.parse.urlencode(sorgu)
    req = urllib.request.Request(url, data=None if veri is None else json.dumps(veri).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as h:
        try:
            return h.code, json.loads(h.read().decode())
        finally:
            h.close()


class CtfSunucuTesti(unittest.TestCase):
    def setUp(self):
        self.oda = S.OdaDurumu("1234", SIFRE)
        self.sunucu = S.sunucu_baslat(self.oda, "127.0.0.1", 0)
        self.addCleanup(self.sunucu.server_close)      # cleanup ters sirada calisir: once shutdown
        self.addCleanup(self.sunucu.shutdown)
        self.port = self.sunucu.server_address[1]
        for ad in ("ali", "veli"):
            self.assertEqual(istek(self.port, "/katil", {"ogrenci": ad, "sifre": SIFRE})[0], 200)

    def durum(self, ad="ali"):
        return istek(self.port, "/ctf/durum", sorgu={"ogrenci": ad, "sifre": SIFRE})

    def dosya(self, ad, gorev):
        return istek(self.port, "/ctf/dosya", sorgu={"ogrenci": ad, "sifre": SIFRE, "gorev": gorev})

    def gonder(self, ad, gorev, bayrak):
        return istek(self.port, "/ctf/gonder", {"ogrenci": ad, "sifre": SIFRE, "gorev": gorev, "bayrak": bayrak})

    def coz(self, ad, gorev):
        kod, d = self.dosya(ad, gorev)
        self.assertEqual(kod, 200, d)
        g = self.oda.ctf_oturumu().gorevler[gorev]
        return U.COZUCULAR[g["uretici"]](d["icerik"], g.get("parametreler") or {})

    def baslat(self, **kw):
        self.oda.ctf_oturumu().baslat(kw.pop("sure_dk", 30), kw.pop("idler", None), kw.pop("dondurma_dk", 0))

    # -- yetki -------------------------------------------------------------------------------------------
    def test_baslamadan_liste_bos_dosya_409(self):
        kod, d = self.durum()
        self.assertEqual((kod, d["durum"], d["gorevler"]), (200, "hazir", []))
        self.assertEqual(self.dosya("ali", "kodlama-1")[0], 404)       # henuz acik gorev yok

    def test_sifresiz_ya_da_yanlis_sifre_reddedilir(self):
        self.baslat()
        for yol in ("/ctf/durum", "/ctf/skor"):
            self.assertEqual(istek(self.port, yol, sorgu={"ogrenci": "ali", "sifre": "yanlis"})[0], 403)
            self.assertEqual(istek(self.port, yol, sorgu={"ogrenci": "ali"})[0], 403)
        self.assertEqual(istek(self.port, "/ctf/gonder", {"ogrenci": "ali", "sifre": "x", "gorev": "kodlama-1",
                                                           "bayrak": "x"})[0], 403)

    def test_katilmamis_ogrenci_reddedilir(self):
        self.baslat()
        for kimlik in ("yabanci", "", "x" * 200):
            kod, _ = istek(self.port, "/ctf/durum", sorgu={"ogrenci": kimlik, "sifre": SIFRE})
            self.assertEqual(kod, 404, repr(kimlik))
        kod, _ = istek(self.port, "/ctf/gonder", {"ogrenci": "yabanci", "sifre": SIFRE, "gorev": "kodlama-1",
                                                   "bayrak": "x"})
        self.assertEqual(kod, 404)

    # -- akis ----------------------------------------------------------------------------------------------
    def test_tam_akis_cozum_ve_skor(self):
        self.baslat()
        kod, d = self.durum()
        self.assertEqual((kod, d["durum"]), (200, "surec"))
        self.assertGreaterEqual(len(d["gorevler"]), 12)
        self.assertNotIn("CAROT{", json.dumps(d["gorevler"]).replace("CAROT{ ile", "").replace("CAROT{adres}", "")
                         .replace("CAROT{parola}", "").replace("CAROT{address}", "").replace("CAROT{password}", ""))
        bayrak = self.coz("ali", "kodlama-1")
        kod, r = self.gonder("ali", "kodlama-1", bayrak)
        self.assertEqual((kod, r["sonuc"]), (200, "dogru"))
        self.assertEqual(self.gonder("ali", "kodlama-1", bayrak)[1]["sonuc"], "zaten")
        kod, s = istek(self.port, "/ctf/skor", sorgu={"ogrenci": "veli", "sifre": SIFRE})
        self.assertEqual(s["satirlar"][0]["ad"], "ali")
        self.assertGreater(s["satirlar"][0]["puan"], 0)
        self.assertTrue({g["id"]: g for g in self.durum("ali")[1]["gorevler"]}["kodlama-1"]["cozuldu"])
        self.assertFalse({g["id"]: g for g in self.durum("veli")[1]["gorevler"]}["kodlama-1"]["cozuldu"])

    def test_dosyalar_ogrenciye_ozel_ve_baska_bayrak_gecmez(self):
        self.baslat()
        self.assertNotEqual(self.dosya("ali", "kripto-1")[1]["icerik"], self.dosya("veli", "kripto-1")[1]["icerik"])
        veli = self.coz("veli", "kripto-1")
        self.assertEqual(self.gonder("ali", "kripto-1", veli)[1]["sonuc"], "yanlis")

    def test_ipucu_siralama_ve_dosya_yaniti(self):
        self.baslat()
        kod, d = istek(self.port, "/ctf/ipucu", {"ogrenci": "ali", "sifre": SIFRE, "gorev": "kodlama-1", "no": 1})
        self.assertEqual((kod, d["hata"]), (400, "once_oncekini_ac"))
        kod, d = istek(self.port, "/ctf/ipucu", {"ogrenci": "ali", "sifre": SIFRE, "gorev": "kodlama-1", "no": 0})
        self.assertEqual(kod, 200)
        self.assertGreater(d["ceza"], 0)
        self.assertEqual(len(self.dosya("ali", "kodlama-1")[1]["ipuclari"]), 1)
        self.assertEqual(len(self.dosya("veli", "kodlama-1")[1]["ipuclari"]), 0)

    def test_cok_yanlis_deneme_beklemeye_alir(self):
        self.baslat()
        sonuclar = [self.gonder("ali", "kodlama-1", "CAROT{x}")[1]["sonuc"] for _ in range(8)]
        self.assertEqual(sonuclar[:5], ["yanlis"] * 5)
        self.assertEqual(sonuclar[5], "bekle")
        self.assertEqual(self.gonder("veli", "kodlama-1", "CAROT{x}")[1]["sonuc"], "yanlis")

    # -- bozuk girdi -------------------------------------------------------------------------------------------
    def test_bozuk_girdiler_cokertmez(self):
        self.baslat()
        govdeler = [
            {"ogrenci": "ali", "sifre": SIFRE},                                         # gorev yok
            {"ogrenci": "ali", "sifre": SIFRE, "gorev": 5, "bayrak": "x"},
            {"ogrenci": "ali", "sifre": SIFRE, "gorev": "x" * 500, "bayrak": "x"},
            {"ogrenci": "ali", "sifre": SIFRE, "gorev": "kodlama-1", "bayrak": 5},
            {"ogrenci": "ali", "sifre": SIFRE, "gorev": "kodlama-1", "bayrak": None},
            {"ogrenci": "ali", "sifre": SIFRE, "gorev": "kodlama-1", "bayrak": "x" * 10000},
            {"ogrenci": 5, "sifre": SIFRE, "gorev": "kodlama-1", "bayrak": "x"},
        ]
        for g in govdeler:
            kod, _ = istek(self.port, "/ctf/gonder", g)
            self.assertIn(kod, (200, 400, 404), g)
        kod, _ = istek(self.port, "/ctf/ipucu", {"ogrenci": "ali", "sifre": SIFRE, "gorev": "kodlama-1", "no": "a"})
        self.assertEqual(kod, 400)
        self.assertEqual(self.dosya("ali", "x" * 500)[0], 404)
        self.assertEqual(self.durum()[0], 200)                                           # sunucu ayakta

    def test_yarisma_bitince_gonderim_kapanir(self):
        self.baslat()
        b = self.coz("ali", "kodlama-1")
        self.oda.ctf_oturumu().bitir()
        self.assertEqual(self.gonder("ali", "kodlama-1", b)[1]["sonuc"], "bitti")
        kod, d = istek(self.port, "/ctf/ipucu", {"ogrenci": "ali", "sifre": SIFRE, "gorev": "kodlama-1", "no": 0})
        self.assertEqual((kod, d["hata"]), (409, "surec_degil"))

    def test_ders_modu_ucnoktalari_bozulmadi(self):
        self.assertEqual(istek(self.port, "/durum")[0], 200)
        self.assertEqual(istek(self.port, "/gorevler")[0], 200)
        self.assertEqual(istek(self.port, "/yok")[0], 404)


if __name__ == "__main__":
    unittest.main()
