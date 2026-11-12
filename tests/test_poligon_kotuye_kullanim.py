#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon kotuye kullanim testleri: docs/DENETIM.md'deki bulgularin (P-01...) kalici karsiliklari.

Gercek yerel sunucuyla (127.0.0.1, gecici port) calisir; GTK gerektirmez. Her sinif bir bulguyu
kapatir ve o bulgunun numarasini adinda tasir.

Calistirma:  python3 tests/test_poligon_kotuye_kullanim.py
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
INC = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
POLIGON = os.path.join(INC, "poligon")
for _y in (POLIGON, os.path.join(INC, "carotpot"), os.path.join(INC, "ortak")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import ogrenci_istemci  # noqa: E402
import ogretmen_sunucu  # noqa: E402

SIFRE = "a1b2c3"


def kaynak(ad):
    with open(os.path.join(POLIGON, ad), encoding="utf-8") as f:
        return f.read()


class Taban(unittest.TestCase):
    def setUp(self):
        self.oda = ogretmen_sunucu.OdaDurumu("1234", SIFRE)
        self.sunucu = ogretmen_sunucu.sunucu_baslat(self.oda, "127.0.0.1", 0)
        self.port = self.sunucu.server_address[1]
        self.adres = "http://127.0.0.1:%d" % self.port
        self.addCleanup(self._kapat)

    def _kapat(self):
        self.sunucu.shutdown()
        self.sunucu.server_close()

    def istek(self, yontem, yol, govde=None, ham=None):
        veri = ham if ham is not None else (json.dumps(govde).encode("utf-8") if govde is not None else None)
        r = urllib.request.Request(self.adres + yol, data=veri, method=yontem,
                                   headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read())
            finally:
                e.close()

    def katil(self, ad):
        """(durum, yanit)"""
        return self.istek("POST", "/katil", {"ogrenci": ad, "sifre": SIFRE})

    def katil_tamam(self, ad):
        kod, yanit = self.katil(ad)
        self.assertEqual(kod, 200, (ad, yanit))
        return yanit["anahtar"]

    def sohbet(self, ad, anahtar):
        q = urllib.parse.urlencode({"ogrenci": ad, "sifre": SIFRE, "anahtar": anahtar, "son_no": 0})
        return self.istek("GET", "/sohbet?" + q)[1]["mesajlar"]


class P01YayinYalnizOgretmene(Taban):
    """P-01: 'tum_sinif' adiyla katilan ogrenci butun sinifa ogretmen notu gibi gorunen mesaj yazabiliyordu."""

    def test_ayrilmis_adlarla_katilinamaz(self):
        for ad in ("tum_sinif", "TUM_SINIF", "Tüm Sınıf", "tum sinif", "Öğretmen", "ogretmen", "TEACHER",
                   "Sistem", "admin", "root"):
            kod, yanit = self.katil(ad)
            self.assertEqual(kod, 400, ad)
            self.assertEqual(yanit["hata"], "geçersiz isim", ad)
        self.assertEqual(self.oda.ogrenciler, {})

    def test_ogrenci_mesaji_baska_ogrenciye_dusmez(self):
        a_ali = self.katil_tamam("Ali")
        a_veli = self.katil_tamam("Veli")
        # Dogrudan cekirdek cagrisi bile (ag yolu yok) ogrenci adina yayin yapamaz
        self.oda.mesaj_ekle("tum_sinif", "ogrenci", "sahte duyuru")
        self.assertEqual(self.sohbet("Ali", a_ali), [])
        self.assertEqual(self.sohbet("Veli", a_veli), [])
        # Ogrencinin kendi mesaji yalnizca kendi sohbetinde ve 'ogrenci' olarak durur
        kod, _ = self.istek("POST", "/mesaj", {"ogrenci": "Veli", "sifre": SIFRE, "anahtar": a_veli, "metin": "selam"})
        self.assertEqual(kod, 200)
        self.assertEqual(self.sohbet("Ali", a_ali), [])
        self.assertEqual([(m["kimden"], m["metin"]) for m in self.sohbet("Veli", a_veli)], [("ogrenci", "selam")])

    def test_ogretmen_yayini_herkese_ulasir(self):
        a_ali = self.katil_tamam("Ali")
        a_veli = self.katil_tamam("Veli")
        self.oda.tum_sinifa_yaz("5 dakika kaldı")
        for ad, anahtar in (("Ali", a_ali), ("Veli", a_veli)):
            m = self.sohbet(ad, anahtar)
            self.assertEqual([(x["kimden"], x["metin"], x.get("tum_sinif")) for x in m],
                             [("ogretmen", "5 dakika kaldı", True)])

    def test_gecersiz_gonderen_reddedilir(self):
        self.katil_tamam("Ali")
        with self.assertRaises(ValueError):
            self.oda.mesaj_ekle("Ali", "mudur", "x")

    def test_ogrenci_arayuzu_gondereni_denetler(self):
        """Arayuz yalnizca kimden == 'ogretmen' olan mesajlari ogretmen notu olarak gosterir."""
        k = kaynak("ogrenci_uygulama.py")
        self.assertIn('msj.get("kimden") != "ogretmen"', k)
        self.assertNotIn('self._sohbet_mesajlari.append({"metin": msj["metin"]', k)
        self.assertIn("self.oda.tum_sinifa_yaz(metin)", kaynak("ogretmen_uygulama.py"))


class P14AdKurallari(Taban):
    """P-14: adda yalnizca uzunluk denetimi vardi; gorunmez/yon karakterleri ve gorsel ikizler kabul ediliyordu."""

    def test_denetim_ve_yon_karakterleri_reddedilir(self):
        for ad in ("Ali\nVeli", "Ali\x00", "Ali‮ilA", "Ali​", "⁦Ali", "A\tB\x1b[31m", "", "   ",
                   "x" * 65, 42, None, ["Ali"]):
            kod, yanit = self.katil(ad)
            self.assertEqual(kod, 400, repr(ad))
        self.assertEqual(self.oda.ogrenciler, {})

    def test_buyuk_kucuk_harf_ve_bosluk_ikizleri_ayni_ad_sayilir(self):
        self.katil_tamam("Ali Işık")
        for ikiz in ("ALİ IŞIK", "ali ışık", "ALI ISIK", "  Ali   Işık  ", "Ａｌｉ Işık"):
            kod, yanit = self.katil(ikiz)
            self.assertEqual((kod, yanit.get("hata")), (409, "isim_alinmis"), ikiz)
        self.assertEqual(list(self.oda.ogrenciler), ["Ali Işık"])

    def test_ad_normallestirilir_ve_istemci_benimser(self):
        ist = ogrenci_istemci.PoligonIstemci(self.adres, "1234", SIFRE, "  Şule   İpek ")
        self.assertEqual(ist.katil(), (True, ""))
        self.assertEqual(ist.ogrenci_adi, "Şule İpek")
        self.assertEqual(list(self.oda.ogrenciler), ["Şule İpek"])
        self.assertEqual(ist.sinif_baglanti_durumu(), "aktif")
        self.assertTrue(ist.mesaj_gonder("merhaba"))
        # Normallestirilmemis adla gelen istek de ayni ogrenciye cozulur (eski istemciler)
        kod, _ = self.istek("POST", "/mesaj", {"ogrenci": " Şule  İpek", "sifre": SIFRE, "anahtar": ist.anahtar,
                                              "metin": "yine ben"})
        self.assertEqual(kod, 200)

    def test_turkce_ve_diger_alfabeler_kabul_edilir(self):
        for ad in ("Çağrı Öztürk", "Ümit Şahin", "José Peña", "Jürgen Müller", "Ольга", "田中 太郎", "王小明", "O'Brien-Smith"):
            self.katil_tamam(ad)
        self.assertEqual(len(self.oda.ogrenciler), 8)

    def test_atilan_ogrencinin_adi_yeniden_alinabilir(self):
        self.katil_tamam("Ali")
        self.oda.ogrenciyi_at("Ali")
        self.katil_tamam("ALI")
        self.assertEqual(list(self.oda.ogrenciler), ["ALI"])


if __name__ == "__main__":
    unittest.main()
