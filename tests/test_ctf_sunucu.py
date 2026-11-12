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
        self.anahtar = {}
        for ad in ("ali", "veli"):
            kod, d = istek(self.port, "/katil", {"ogrenci": ad, "sifre": SIFRE})
            self.assertEqual(kod, 200)
            self.anahtar[ad] = d["anahtar"]

    def durum(self, ad="ali"):
        return istek(self.port, "/ctf/durum", sorgu={"ogrenci": ad, "sifre": SIFRE, "anahtar": self.anahtar[ad]})

    def dosya(self, ad, gorev):
        return istek(self.port, "/ctf/dosya", sorgu={"ogrenci": ad, "sifre": SIFRE, "anahtar": self.anahtar[ad],
                                                      "gorev": gorev})

    def gonder(self, ad, gorev, bayrak):
        return istek(self.port, "/ctf/gonder", {"ogrenci": ad, "sifre": SIFRE, "anahtar": self.anahtar[ad], "gorev": gorev,
                                          "bayrak": bayrak})

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
        kod, s = istek(self.port, "/ctf/skor", sorgu={"ogrenci": "veli", "sifre": SIFRE,
                                                      "anahtar": self.anahtar["veli"]})
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
        kod, d = istek(self.port, "/ctf/ipucu", {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"], "gorev": "kodlama-1", "no": 1})
        self.assertEqual((kod, d["hata"]), (400, "once_oncekini_ac"))
        kod, d = istek(self.port, "/ctf/ipucu", {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"], "gorev": "kodlama-1", "no": 0})
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
            {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"]},                                         # gorev yok
            {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"], "gorev": 5, "bayrak": "x"},
            {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"], "gorev": "x" * 500, "bayrak": "x"},
            {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"], "gorev": "kodlama-1", "bayrak": 5},
            {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"], "gorev": "kodlama-1", "bayrak": None},
            {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"], "gorev": "kodlama-1", "bayrak": "x" * 10000},
            {"ogrenci": 5, "sifre": SIFRE, "anahtar": "x", "gorev": "kodlama-1", "bayrak": "x"},
        ]
        for g in govdeler:
            kod, _ = istek(self.port, "/ctf/gonder", g)
            self.assertIn(kod, (200, 400, 404), g)
        kod, _ = istek(self.port, "/ctf/ipucu", {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"], "gorev": "kodlama-1", "no": "a"})
        self.assertEqual(kod, 400)
        self.assertEqual(self.dosya("ali", "x" * 500)[0], 404)
        self.assertEqual(self.durum()[0], 200)                                           # sunucu ayakta

    def test_yarisma_bitince_gonderim_kapanir(self):
        self.baslat()
        b = self.coz("ali", "kodlama-1")
        self.oda.ctf_oturumu().bitir()
        self.assertEqual(self.gonder("ali", "kodlama-1", b)[1]["sonuc"], "bitti")
        kod, d = istek(self.port, "/ctf/ipucu", {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["ali"], "gorev": "kodlama-1", "no": 0})
        self.assertEqual((kod, d["hata"]), (409, "surec_degil"))

    # -- ogrenci anahtari (oda sifresi tum sinifta ortak) ----------------------------------------------------------
    def test_baska_ogrenci_adina_islem_yapilamaz(self):
        self.baslat()
        sahte = {"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["veli"], "gorev": "kodlama-1"}
        for yol, ek in (("/ctf/gonder", {"bayrak": "CAROT{x}"}), ("/ctf/ipucu", {"no": 0})):
            kod, d = istek(self.port, yol, {**sahte, **ek})
            self.assertEqual((kod, d["hata"]), (403, "gecersiz_anahtar"), yol)
        for yol, ek in (("/ctf/durum", {}), ("/ctf/skor", {}), ("/ctf/dosya", {"gorev": "kodlama-1"})):
            kod, d = istek(self.port, yol, sorgu={"ogrenci": "ali", "sifre": SIFRE, "anahtar": self.anahtar["veli"], **ek})
            self.assertEqual((kod, d["hata"]), (403, "gecersiz_anahtar"), yol)
        # anahtarsiz / bos / sayi da reddedilir
        for anahtar in (None, "", 5):
            g = {"ogrenci": "ali", "sifre": SIFRE, "gorev": "kodlama-1", "no": 0, "anahtar": anahtar}
            self.assertEqual(istek(self.port, "/ctf/ipucu", g)[0], 403, repr(anahtar))
        g = {"ogrenci": "ali", "sifre": SIFRE, "gorev": "kodlama-1", "no": 0}
        self.assertEqual(istek(self.port, "/ctf/ipucu", g)[0], 403)
        # kurbanin puani ve hakki etkilenmedi
        self.assertEqual(self.oda.ctf_oturumu().ipuclari, [])
        self.assertEqual(self.oda.ctf_oturumu()._yanlislar, {})

    def test_anahtar_katilimda_yeniden_uretilir(self):
        eski = self.anahtar["ali"]
        self.oda.ogrenciyi_at("ali")
        self.assertFalse(self.oda.anahtar_dogru("ali", eski))
        kod, d = istek(self.port, "/katil", {"ogrenci": "ali", "sifre": SIFRE})
        self.assertEqual(kod, 200)
        self.assertNotEqual(d["anahtar"], eski)
        self.assertEqual(len(d["anahtar"]), 32)

    def test_yarim_kalan_istek_baglantiyi_sonsuza_dek_tutmaz(self):
        import socket
        import time
        sinif = S._sunucu_sinifi_olustur(self.oda)
        self.assertEqual(sinif.timeout, S.ISTEK_ZAMAN_ASIMI)
        sinif.timeout = 1                                       # testte beklemeyelim
        from http.server import ThreadingHTTPServer
        sunucu = ThreadingHTTPServer(("127.0.0.1", 0), sinif)
        sunucu.daemon_threads = True
        import threading
        threading.Thread(target=sunucu.serve_forever, daemon=True).start()
        self.addCleanup(sunucu.server_close)
        self.addCleanup(sunucu.shutdown)
        c = socket.create_connection(("127.0.0.1", sunucu.server_address[1]), timeout=5)
        self.addCleanup(c.close)
        c.sendall(b"POST /katil HTTP/1.1\r\nContent-Length: 50000\r\n\r\n{")     # govde hic tamamlanmaz
        t0 = time.monotonic()
        try:
            veri = c.recv(4096)                                 # sunucu kapatinca bos doner (ya da 4xx yaniti)
        except socket.timeout:
            self.fail("sunucu yarim kalan istegi zaman asimina ugratmadi")
        self.assertLess(time.monotonic() - t0, 4)
        self.assertTrue(veri == b"" or veri.startswith(b"HTTP/"))

    def test_ders_modu_ucnoktalari_bozulmadi(self):
        self.assertEqual(istek(self.port, "/durum")[0], 404)     # sifresiz ogrenci listesi kaldirildi (P-08)
        self.assertEqual(istek(self.port, "/gorevler")[0], 200)
        self.assertEqual(istek(self.port, "/yok")[0], 404)


if __name__ == "__main__":
    unittest.main()
