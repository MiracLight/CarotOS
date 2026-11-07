#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon ogretmen sunucusu ile ogrenci istemcisi: gercek yerel sunucuyla (GTK'siz).

Sunucu 127.0.0.1'de gecici bir portta calisir. Kapsam: Turkce karakterli
ogrenci adlarinin URL'de dogru tasinmasi, istek govdesi siniri, alan dogrulama,
/mesaj ve /sohbet icin oda sifresi, yanlis sifre denemesi siniri.

Calistirma:  python3 tests/test_poligon_sunucu.py
"""
import http.client
import json
import os
import sys
import unittest
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import parse_qs, urlparse

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
for _y in (os.path.join(INC, "poligon"), os.path.join(INC, "carotpot"), os.path.join(INC, "ortak")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import ogrenci_istemci  # noqa: E402
import ogretmen_sunucu  # noqa: E402

SIFRE = "a1b2c3"
AD = "Şule İpek"          # Turkce karakterler + bosluk


class SunucuTabani(unittest.TestCase):
    def setUp(self):
        self.oda = ogretmen_sunucu.OdaDurumu("1234", SIFRE)
        self.sunucu = ogretmen_sunucu.sunucu_baslat(self.oda, "127.0.0.1", 0)
        self.port = self.sunucu.server_address[1]
        self.adres = "http://127.0.0.1:%d" % self.port
        self.addCleanup(self._kapat)

    def _kapat(self):
        self.sunucu.shutdown()
        self.sunucu.server_close()

    def istek(self, yontem, yol, govde=None):
        veri = json.dumps(govde).encode("utf-8") if govde is not None else None
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

    def istemci(self, ad=AD):
        return ogrenci_istemci.PoligonIstemci(self.adres, "1234", SIFRE, ad)


class IstemciUrlTesti(unittest.TestCase):
    def test_turkce_ad_url_de_kodlanir(self):
        # Kodlanmazsa urllib ASCII disi URL'de UnicodeEncodeError verirdi ve
        # "Şule", "İpek" gibi adli ogrencilerin durum/sohbet sorgusu calismazdi.
        ad = "Şule İpek & Co=1"
        ist = ogrenci_istemci.PoligonIstemci("http://127.0.0.1:1", "1234", SIFRE, ad)
        yollar = []

        def sahte(yol, govde, yontem="POST"):
            yollar.append(yol)
            return 200, {"aktif": True, "mesajlar": []}
        ist._istek = sahte
        ist.sinif_baglanti_durumu()
        ist.yeni_mesajlari_getir()
        self.assertEqual(len(yollar), 2)
        for yol in yollar:
            with self.subTest(yol=yol):
                yol.encode("ascii")                      # ASCII disi karakter kalmamali
                self.assertEqual(parse_qs(urlparse(yol).query)["ogrenci"], [ad])


class TurkceAdUcAdan(SunucuTabani):
    def test_turkce_adli_ogrenci_katilir_durumu_okur(self):
        ist = self.istemci()
        self.assertEqual(ist.katil(), (True, ""))
        self.assertEqual(ist.sinif_baglanti_durumu(), "aktif")
        self.oda.ogrenciyi_at(AD)
        self.assertEqual(ist.sinif_baglanti_durumu(), "atildi")


class SohbetKimlikTesti(SunucuTabani):
    """/mesaj ve /sohbet yalnizca oda sifresini bilenlere acik."""

    def katil(self, ad=AD):
        durum, govde = self.istek("POST", "/katil", {"ogrenci": ad, "sifre": SIFRE})
        self.assertEqual(durum, 200)
        self.anahtar = govde["anahtar"]
        return self.anahtar

    def test_mesaj_sifresiz_reddedilir(self):
        self.katil()
        durum, _ = self.istek("POST", "/mesaj", {"ogrenci": AD, "metin": "merhaba"})
        self.assertEqual(durum, 403)
        self.assertEqual(self.oda.sohbet_getir(AD), [])

    def test_mesaj_gonderen_sunucuda_sabitlenir(self):
        # LAN'daki biri kimden='ogretmen' diyerek ogrencilere ogretmen adina yazamamali
        self.katil()
        durum, _ = self.istek("POST", "/mesaj", {
            "ogrenci": AD, "sifre": SIFRE, "anahtar": self.anahtar, "kimden": "ogretmen",
            "metin": "komut calistir"})
        self.assertEqual(durum, 200)
        self.assertEqual(self.oda.sohbet_getir(AD)[-1]["kimden"], "ogrenci")

    def test_mesaj_katilmamis_ogrenciye_yazilmaz(self):
        durum, _ = self.istek("POST", "/mesaj", {"ogrenci": "Hayalet", "sifre": SIFRE, "anahtar": "x", "metin": "x"})
        self.assertEqual(durum, 404)
        self.assertNotIn("Hayalet", self.oda.sohbetler)      # sozluk sismemeli

    def test_mesaj_gecersiz_metin_400(self):
        self.katil()
        for metin in ("", "   ", "a" * 1001, 5, ["x"]):
            with self.subTest(metin=metin):
                durum, _ = self.istek("POST", "/mesaj", {"ogrenci": AD, "sifre": SIFRE, "anahtar": self.anahtar,
                                                              "metin": metin})
                self.assertEqual(durum, 400)

    def test_sohbet_sifresiz_okunamaz(self):
        self.katil()
        self.oda.mesaj_ekle(AD, "ogretmen", "ozel mesaj")
        durum, govde = self.istek("GET", "/sohbet?ogrenci=" + urllib.parse.quote(AD, safe=""))
        self.assertEqual(durum, 403)
        self.assertNotIn("mesajlar", govde)

    def test_sohbet_sifreyle_okunur_ve_gecersiz_son_no_cokmez(self):
        self.katil()
        self.oda.mesaj_ekle(AD, "ogretmen", "ozel mesaj")
        yol = "/sohbet?ogrenci=%s&sifre=%s&anahtar=%s&son_no=%s" % (
            urllib.parse.quote(AD, safe=""), SIFRE, self.anahtar, "abc")
        durum, govde = self.istek("GET", yol)
        self.assertEqual(durum, 200)
        self.assertEqual([m["metin"] for m in govde["mesajlar"]], ["ozel mesaj"])

    def test_baska_ogrenci_adina_mesaj_ilerleme_sohbet_yapilamaz(self):
        self.katil()                                   # Şule İpek (kurban)
        saldirgan = self.katil("Ali")
        kurban = AD
        # kurbanin adina mesaj: saldirganin anahtariyla reddedilir
        durum, govde = self.istek("POST", "/mesaj", {"ogrenci": kurban, "sifre": SIFRE,
                                                      "anahtar": saldirgan, "metin": "sahte"})
        self.assertEqual((durum, govde["hata"]), (403, "gecersiz_anahtar"))
        self.assertEqual(self.oda.sohbet_getir(kurban), [])
        # kurbanin adina ilerleme/puan
        durum, _ = self.istek("POST", "/ilerleme", {
            "ogrenci": kurban, "sifre": SIFRE, "anahtar": saldirgan, "gorev_id": "ufw-01",
            "durum": "tamamlandi", "soru_no": 1, "puan": 999})
        self.assertEqual(durum, 403)
        self.assertEqual(self.oda.cozulen_sorular, {})
        # kurbanin sohbetini okuma
        self.oda.mesaj_ekle(kurban, "ogretmen", "ozel")
        yol = "/sohbet?ogrenci=%s&sifre=%s&anahtar=%s" % (urllib.parse.quote(kurban, safe=""), SIFRE, saldirgan)
        durum, govde = self.istek("GET", yol)
        self.assertEqual(durum, 403)
        self.assertNotIn("mesajlar", govde)
        # anahtarsiz da reddedilir
        durum, _ = self.istek("GET", "/sohbet?ogrenci=%s&sifre=%s" % (urllib.parse.quote(kurban, safe=""), SIFRE))
        self.assertEqual(durum, 403)

    def test_istemci_mesajlasma_uctan_uca(self):
        ist = self.istemci()
        self.assertEqual(ist.katil(), (True, ""))
        self.oda.mesaj_ekle(AD, "ogretmen", "selam")
        self.assertEqual([m["metin"] for m in ist.yeni_mesajlari_getir()], ["selam"])
        self.assertEqual(ist.yeni_mesajlari_getir(), [])            # her mesaj bir kez gelir
        self.assertTrue(ist.mesaj_gonder("merhaba hocam"))
        son = self.oda.sohbet_getir(AD)[-1]
        self.assertEqual((son["kimden"], son["metin"]), ("ogrenci", "merhaba hocam"))

    def test_istemci_yanlis_sifrede_mesaj_gonderemez(self):
        self.katil()
        yanlis = ogrenci_istemci.PoligonIstemci(self.adres, "1234", "yanlis", AD)
        self.assertFalse(yanlis.mesaj_gonder("merhaba"))             # eskiden hep True donerdi


class SunucuSertlestirmeTesti(SunucuTabani):
    def ham_istek(self, yontem, yol, basliklar, govde=b""):
        bag = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            bag.putrequest(yontem, yol)
            for ad, deger in basliklar.items():
                bag.putheader(ad, deger)
            bag.endheaders(govde)
            yanit = bag.getresponse()
            return yanit.status, json.loads(yanit.read())
        finally:
            bag.close()

    def test_cok_buyuk_govde_reddedilir(self):
        # Content-Length'e gore sinirsiz okunsaydi tek istek bellegi doldururdu
        durum, _ = self.ham_istek("POST", "/katil", {"Content-Length": str(10 ** 9)})
        self.assertEqual(durum, 413)

    def test_gecersiz_content_length(self):
        for deger in ("abc", "-5"):
            with self.subTest(deger=deger):
                durum, _ = self.ham_istek("POST", "/katil", {"Content-Length": deger})
                self.assertIn(durum, (400, 413))

    def test_json_nesnesi_degilse_400(self):
        govde = b"[1, 2, 3]"
        durum, _ = self.ham_istek("POST", "/katil", {"Content-Length": str(len(govde))}, govde)
        self.assertEqual(durum, 400)

    def test_gecersiz_alanlar_400(self):
        for govde in ({"ogrenci": ["x"], "sifre": SIFRE}, {"ogrenci": 123, "sifre": SIFRE},
                      {"ogrenci": "", "sifre": SIFRE}, {"ogrenci": "a" * 65, "sifre": SIFRE}):
            with self.subTest(govde=govde):
                durum, _ = self.istek("POST", "/katil", govde)
                self.assertEqual(durum, 400)
        durum, govde = self.istek("POST", "/katil", {"ogrenci": AD, "sifre": SIFRE})
        self.assertEqual(durum, 200)
        self.anahtar = govde["anahtar"]
        for sure in ("abc", [1], {"a": 1}):
            with self.subTest(sure_sn=sure):
                durum, _ = self.istek("POST", "/ilerleme", {
                    "ogrenci": AD, "sifre": SIFRE, "anahtar": self.anahtar, "gorev_id": "ufw-01",
                    "durum": "basladi", "sure_sn": sure})
                self.assertEqual(durum, 400)

    def test_ascii_disi_sifre_cokmez(self):
        # secrets.compare_digest ASCII disi str'de TypeError verirdi (baglanti kopar)
        durum, _ = self.istek("POST", "/katil", {"ogrenci": AD, "sifre": "şifre"})
        self.assertEqual(durum, 403)

    def test_yanlis_sifre_denemesi_sinirlanir(self):
        for _ in range(ogretmen_sunucu.DENEME_LIMITI):
            durum, _ = self.istek("POST", "/katil", {"ogrenci": AD, "sifre": "yanlis"})
            self.assertEqual(durum, 403)
        # sinir asildi: dogru sifre bile gecici olarak reddedilir
        durum, govde = self.istek("POST", "/katil", {"ogrenci": AD, "sifre": SIFRE})
        self.assertEqual(durum, 429)
        self.assertEqual(govde["hata"], "cok_fazla_deneme")

    def test_dogru_sifre_sayac_artirmaz(self):
        anahtar = self.istek("POST", "/katil", {"ogrenci": AD, "sifre": SIFRE})[1]["anahtar"]
        for i in range(ogretmen_sunucu.DENEME_LIMITI + 3):
            durum, _ = self.istek("POST", "/ilerleme", {
                "ogrenci": AD, "sifre": SIFRE, "anahtar": anahtar, "gorev_id": "ufw-01", "durum": "basladi"})
            self.assertEqual(durum, 200, "deneme %d" % i)


if __name__ == "__main__":
    unittest.main(verbosity=2)
