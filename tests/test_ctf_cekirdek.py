#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon CTF cekirdegi (GTK'siz): bayrak turetme, puanlama, bekleme, dondurma, cozulebilirlik.

Calistirma:  python3 tests/test_ctf_cekirdek.py
"""
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLIGON = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "poligon")
sys.path.insert(0, POLIGON)

import ctf_cekirdek as C  # noqa: E402
import ctf_uretici as U  # noqa: E402


class Saat:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def ilerle(self, sn):
        self.t += sn


def oturum(saat=None, azalma=10, sure_dk=60, dondurma_dk=0, idler=None):
    saat = saat or Saat()
    o = C.CtfOturumu(saat=saat, azalma=azalma)
    o.baslat(sure_dk, idler, dondurma_dk)
    return o, saat


def coz(o, ogrenci, gid):
    """Referans cozucuyle bayragi bulur (ogrencinin kendi dosyasindan)."""
    ad, icerik = o.dosya(ogrenci, gid)
    g = o.gorevler[gid]
    return U.COZUCULAR[g["uretici"]](icerik, g.get("parametreler") or {})


class GorevPaketiTesti(unittest.TestCase):
    def test_paket_yuklenir_ve_dogrulanir(self):
        g = C.gorevleri_yukle()
        self.assertGreaterEqual(len(g), 12)
        self.assertEqual(set(x["kategori"] for x in g.values()), set(C.KATEGORILER))
        self.assertEqual(set(x["zorluk"] for x in g.values()), set(C.ZORLUKLAR))

    def test_bozuk_gorev_reddedilir(self):
        with self.assertRaises(ValueError):
            C._gorev_dogrula({"id": "x"})
        iyi = dict(next(iter(C.gorevleri_yukle().values())))
        for degisim in ({"kategori": "yok"}, {"uretici": "yok"}, {"puan": 0}, {"zorluk": "cok"}):
            with self.assertRaises(ValueError):
                C._gorev_dogrula({**iyi, **degisim})

    def test_her_gorevin_metni_iki_dilli(self):
        for g in C.gorevleri_yukle().values():
            for alan in ("baslik", "aciklama"):
                self.assertEqual(set(g[alan]), {"tr", "en"}, g["id"])
            for ip in g.get("ipuclari", []):
                self.assertEqual(set(ip) - {"ceza"}, {"tr", "en"}, g["id"])


class CozulebilirlikTesti(unittest.TestCase):
    """Her gorev, ogrencinin eline gecen dosyadan akil yoluyla cozulebilmeli."""

    def test_her_gorev_birden_cok_ogrenci_icin_cozulur(self):
        o, _ = oturum()
        for gid in o.acik_idler:
            for ogr in ("ali", "ayse", "Zeynep Ç", "x" * 40):
                with self.subTest(gorev=gid, ogrenci=ogr):
                    bayrak = coz(o, ogr, gid)
                    self.assertTrue(bayrak.startswith("CAROT{") and bayrak.endswith("}"), bayrak)
                    self.assertEqual(o.gonder(ogr, gid, bayrak)["sonuc"], "dogru")

    def test_ayni_ogrenciye_ayni_dosya_ogrenciler_arasinda_farkli(self):
        o, _ = oturum()
        for gid in o.acik_idler:
            self.assertEqual(o.dosya("ali", gid), o.dosya("ali", gid), gid)
            self.assertNotEqual(o.dosya("ali", gid)[1], o.dosya("veli", gid)[1], gid)
            self.assertNotEqual(coz(o, "ali", gid), coz(o, "veli", gid), gid)

    def test_baska_ogrencinin_bayragi_gecmez(self):
        o, saat = oturum()
        for gid in o.acik_idler:
            veli = coz(o, "veli", gid)
            self.assertEqual(o.gonder("ali", gid, veli)["sonuc"], "yanlis", gid)
            saat.ilerle(30)                                # bekleme sinirina takilmasin

    def test_yeni_yarisma_yeni_bayrak_uretir(self):
        o, saat = oturum()
        eski = coz(o, "ali", "kodlama-1")
        o.bitir()
        o.baslat(30)
        self.assertNotEqual(coz(o, "ali", "kodlama-1"), eski)

    def test_ureticiler_yan_etki_icermez(self):
        with open(os.path.join(POLIGON, "ctf_uretici.py"), encoding="utf-8") as f:
            kaynak = f.read()
        for yasak in ("subprocess", "socket", "os.system", "eval(", "exec(", "open(", "import os"):
            self.assertNotIn(yasak, kaynak, yasak)

    def test_log_adresleri_belgeleme_araliginda(self):
        o, _ = oturum()
        for ogr in ("a", "b", "c", "d"):
            for gid in ("log-1", "log-2"):
                ip = coz(o, ogr, gid)[6:-1]
                self.assertTrue(ip.startswith(("192.0.2.", "198.51.100.", "203.0.113.")), ip)


class DogrulamaTesti(unittest.TestCase):
    def test_dogru_yanlis_ve_bosluk(self):
        o, _ = oturum()
        b = coz(o, "ali", "kodlama-1")
        self.assertEqual(o.gonder("ali", "kodlama-1", "CAROT{yanlis}")["sonuc"], "yanlis")
        self.assertEqual(o.gonder("ali", "kodlama-1", "  " + b + "\n")["sonuc"], "dogru")
        self.assertEqual(o.gonder("ali", "kodlama-1", b)["sonuc"], "zaten")

    def test_gecersiz_girdi_hata_atmaz(self):
        o, _ = oturum()
        for kotu in ("", "   ", None, 5, "x" * (C.MAKS_BAYRAK + 1), ["a"], b"CAROT{}"):
            self.assertEqual(o.gonder("ali", "kodlama-1", kotu)["sonuc"], "yanlis", repr(kotu))

    def test_bilinmeyen_gorev(self):
        o, _ = oturum(idler=["kodlama-1"])
        for gid in ("yok", "kodlama-2"):
            with self.assertRaises(C.CtfHata) as h:
                o.gonder("ali", gid, "x")
            self.assertEqual(h.exception.kod, "bilinmeyen_gorev")
            with self.assertRaises(C.CtfHata):
                o.dosya("ali", gid)

    def test_buyuk_kucuk_harf_ayrimi(self):
        o, _ = oturum()
        b = coz(o, "ali", "kripto-1")
        self.assertEqual(o.gonder("ali", "kripto-1", b.lower())["sonuc"], "yanlis" if b != b.lower() else "dogru")


class ZamanTesti(unittest.TestCase):
    def test_baslamadan_ve_bittikten_sonra_gonderim_olmaz(self):
        saat = Saat()
        o = C.CtfOturumu(saat=saat)
        self.assertEqual(o.durum(), "hazir")
        self.assertEqual(o.gonder("ali", "kodlama-1", "x")["sonuc"], "baslamadi")
        self.assertEqual(o.ogrenci_gorevleri("ali"), [])
        o.baslat(10)
        self.assertEqual(o.durum(), "surec")
        b = coz(o, "ali", "kodlama-1")
        saat.ilerle(10 * 60)
        self.assertEqual(o.durum(), "bitti")
        self.assertEqual(o.gonder("ali", "kodlama-1", b)["sonuc"], "bitti")
        self.assertEqual(o.kalan_sn(), 0)

    def test_elle_bitirme(self):
        o, _ = oturum()
        o.bitir()
        self.assertEqual(o.durum(), "bitti")

    def test_gecersiz_sure_ve_cift_baslatma(self):
        o, _ = oturum()
        with self.assertRaises(C.CtfHata) as h:
            o.baslat(5)
        self.assertEqual(h.exception.kod, "zaten_suruyor")
        o.bitir()
        for sure, don in ((0, 0), (-1, 0), (10, 10), (10, -1), (24 * 60 + 1, 0)):
            with self.assertRaises(C.CtfHata, msg=(sure, don)):
                o.baslat(sure, None, don)
        with self.assertRaises(C.CtfHata):
            o.baslat(10, ["yok"])


class BeklemeTesti(unittest.TestCase):
    def test_cok_yanlis_denemeden_sonra_bekletir(self):
        o, saat = oturum()
        b = coz(o, "ali", "kodlama-1")
        for _ in range(C.YANLIS_LIMIT):
            self.assertEqual(o.gonder("ali", "kodlama-1", "CAROT{x}")["sonuc"], "yanlis")
        r = o.gonder("ali", "kodlama-1", b)               # dogru bile olsa bekleme suresince reddedilir
        self.assertEqual(r["sonuc"], "bekle")
        self.assertGreater(r["bekleme_sn"], 0)
        saat.ilerle(C.YANLIS_BEKLEME + 1)
        self.assertEqual(o.gonder("ali", "kodlama-1", b)["sonuc"], "dogru")

    def test_bekleme_ogrenciye_ozel(self):
        o, _ = oturum()
        for _ in range(C.YANLIS_LIMIT):
            o.gonder("ali", "kodlama-1", "CAROT{x}")
        self.assertEqual(o.gonder("veli", "kodlama-1", "CAROT{x}")["sonuc"], "yanlis")

    def test_yavas_yanlis_denemeler_bekletmez(self):
        o, saat = oturum()
        for _ in range(C.YANLIS_LIMIT * 3):
            self.assertEqual(o.gonder("ali", "kodlama-1", "CAROT{x}")["sonuc"], "yanlis")
            saat.ilerle(C.YANLIS_PENCERE / C.YANLIS_LIMIT + 5)


class PuanTesti(unittest.TestCase):
    def test_puan_azalir_ve_tabana_iner(self):
        o, saat = oturum(azalma=5)
        taban = o.gorevler["kodlama-1"]["puan"]
        degerler = []
        for i in range(8):
            ogr = "o%d" % i
            degerler.append(o.puan_simdi("kodlama-1"))
            o.gonder(ogr, "kodlama-1", coz(o, ogr, "kodlama-1"))
            saat.ilerle(1)
        self.assertEqual(degerler[0], taban)
        self.assertEqual(degerler, sorted(degerler, reverse=True))
        self.assertEqual(degerler[-1], int(round(taban * C.MIN_ORAN)))
        self.assertGreater(degerler[0], degerler[-1])

    def test_ilk_cozum_bonusu_yalniz_birine(self):
        o, saat = oturum()
        for ogr in ("ali", "veli"):
            o.gonder(ogr, "kodlama-1", coz(o, ogr, "kodlama-1"))
            saat.ilerle(1)
        t = {s["ad"]: s for s in o.skor_tablosu()["satirlar"]}
        self.assertGreater(t["ali"]["bonus"], 0)
        self.assertEqual(t["veli"]["bonus"], 0)

    def test_ipucu_cezasi_puandan_dusulur(self):
        o, _ = oturum()
        ceza = o.ipucu_al("ali", "kodlama-1", 0)["ceza"]
        self.assertGreater(ceza, 0)
        r = o.gonder("ali", "kodlama-1", coz(o, "ali", "kodlama-1"))
        taban = o.gorevler["kodlama-1"]["puan"]
        self.assertEqual(r["ceza"], ceza)
        self.assertEqual(r["puan"], taban - ceza + r["bonus"])

    def test_ipuclari_sirayla_acilir_ve_tekrar_ceza_vermez(self):
        o, _ = oturum()
        with self.assertRaises(C.CtfHata) as h:
            o.ipucu_al("ali", "kodlama-1", 1)
        self.assertEqual(h.exception.kod, "once_oncekini_ac")
        o.ipucu_al("ali", "kodlama-1", 0)
        o.ipucu_al("ali", "kodlama-1", 0)                  # tekrar acmak ceza eklemez
        self.assertEqual(sum(1 for i in o.ipuclari if i["ogrenci"] == "ali"), 1)
        o.ipucu_al("ali", "kodlama-1", 1)
        for kotu in (-1, 2, 99, True, "0", None):
            with self.assertRaises(C.CtfHata, msg=repr(kotu)):
                o.ipucu_al("ali", "kodlama-1", kotu)

    def test_cozulmus_gorevde_ipucu_alinmaz(self):
        o, _ = oturum()
        o.gonder("ali", "kodlama-1", coz(o, "ali", "kodlama-1"))
        with self.assertRaises(C.CtfHata) as h:
            o.ipucu_al("ali", "kodlama-1", 0)
        self.assertEqual(h.exception.kod, "zaten_cozuldu")

    def test_puan_asla_negatif_olmaz(self):
        o, _ = oturum()
        for k in range(len(o.gorevler["kodlama-3"]["ipuclari"])):
            o.ipucu_al("ali", "kodlama-3", k)
        o.gorevler["kodlama-3"]["ipuclari"][0]["ceza"] = 10 ** 6
        o.ipuclari[-1]["ceza"] = 10 ** 6
        r = o.gonder("ali", "kodlama-3", coz(o, "ali", "kodlama-3"))
        self.assertGreaterEqual(r["puan"], 0)

    def test_skor_tablosu_siralama_ve_esitlik(self):
        o, saat = oturum()
        o.gonder("ali", "kodlama-1", coz(o, "ali", "kodlama-1"))
        saat.ilerle(5)
        o.gonder("veli", "kodlama-1", coz(o, "veli", "kodlama-1"))
        saat.ilerle(5)
        o.gonder("veli", "kripto-1", coz(o, "veli", "kripto-1"))
        satirlar = o.skor_tablosu()["satirlar"]
        self.assertEqual([s["ad"] for s in satirlar], ["veli", "ali"])
        self.assertEqual([s["sira"] for s in satirlar], [1, 2])
        self.assertEqual(satirlar[0]["cozulen"], 2)


class DondurmaTesti(unittest.TestCase):
    def test_donuk_tablo_ogrenciye_eskiyi_ogretmene_gercegi_gosterir(self):
        o, saat = oturum(sure_dk=60, dondurma_dk=10)
        o.gonder("ali", "kodlama-1", coz(o, "ali", "kodlama-1"))
        saat.ilerle(55 * 60)                              # dondurma icinde
        self.assertTrue(o.donuk_mu())
        o.gonder("veli", "kripto-1", coz(o, "veli", "kripto-1"))
        ogr = o.skor_tablosu()
        self.assertTrue(ogr["donuk"])
        self.assertEqual([s["ad"] for s in ogr["satirlar"]], ["ali"])
        ogt = o.skor_tablosu(ogretmen=True)
        self.assertFalse(ogt["donuk"])
        self.assertEqual({s["ad"] for s in ogt["satirlar"]}, {"ali", "veli"})
        saat.ilerle(10 * 60)                              # yarisma bitti: ogrenci yine donuk tabloyu gorur
        self.assertEqual(o.durum(), "bitti")
        self.assertEqual([s["ad"] for s in o.skor_tablosu()["satirlar"]], ["ali"])

    def test_dondurma_yoksa_canli(self):
        o, _ = oturum()
        o.gonder("ali", "kodlama-1", coz(o, "ali", "kodlama-1"))
        self.assertFalse(o.skor_tablosu()["donuk"])


class GorunumSizintisiTesti(unittest.TestCase):
    def test_ogrenci_gorunumunde_bayrak_yok(self):
        o, _ = oturum()
        for gid in o.acik_idler:
            b = coz(o, "ali", gid)
            metin = json.dumps(o.ogrenci_gorevleri("ali"), ensure_ascii=False) + \
                json.dumps(o.skor_tablosu(), ensure_ascii=False)
            self.assertNotIn(b, metin, gid)
            self.assertNotIn(b[6:-1], metin, gid)

    def test_ogrenci_listesinde_cozum_bilgisi_kendine_ait(self):
        o, _ = oturum()
        o.gonder("ali", "kodlama-1", coz(o, "ali", "kodlama-1"))
        a = {g["id"]: g for g in o.ogrenci_gorevleri("ali")}
        v = {g["id"]: g for g in o.ogrenci_gorevleri("veli")}
        self.assertTrue(a["kodlama-1"]["cozuldu"])
        self.assertFalse(v["kodlama-1"]["cozuldu"])
        self.assertEqual(a["kodlama-1"]["cozen"], 1)


class DisaAktarimTesti(unittest.TestCase):
    def test_csv_basliklar_ve_formul_korumasi(self):
        o, _ = oturum()
        o.gonder("=1+1", "kodlama-1", coz(o, "=1+1", "kodlama-1"))
        o.gonder("normal", "kodlama-1", coz(o, "normal", "kodlama-1"))
        satirlar = o.csv_metni().strip().splitlines()
        self.assertEqual(satirlar[0].split(",")[0:3], ["sira", "ogrenci", "puan"])
        self.assertTrue(any(s.split(",")[1] == "'=1+1" for s in satirlar[1:]))
        self.assertFalse(any(s.split(",")[1].startswith("=") for s in satirlar[1:]))

    def test_gorev_istatistigi(self):
        o, _ = oturum()
        o.gonder("ali", "kodlama-1", "CAROT{x}")
        o.gonder("ali", "kodlama-1", coz(o, "ali", "kodlama-1"))
        st = {g["id"]: g for g in o.gorev_istatistigi()}
        self.assertEqual(st["kodlama-1"]["cozen"], 1)
        self.assertEqual(st["kodlama-1"]["deneme"], 2)


if __name__ == "__main__":
    unittest.main()
