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


class IlerlemeTabani(Taban):
    def setUp(self):
        super().setUp()
        self.anahtar = self.katil_tamam("Ali")

    def ilerleme(self, **alanlar):
        govde = {"ogrenci": "Ali", "sifre": SIFRE, "anahtar": self.anahtar, "gorev_id": "hydra-01",
                 "durum": "basladi", "sure_sn": 1}
        govde.update(alanlar)
        return self.istek("POST", "/ilerleme", govde)

    def ham_ilerleme(self, ek):
        """ek: JSON nesnesinin sonuna eklenecek ham metin (NaN gibi json.dumps'in uretmeyecegi degerler icin)."""
        ham = ('{"ogrenci":"Ali","sifre":"%s","anahtar":"%s","gorev_id":"hydra-01","durum":"tamamlandi",%s}'
               % (SIFRE, self.anahtar, ek)).encode("utf-8")
        return self.istek("POST", "/ilerleme", ham=ham)


class P02SonluOlmayanSayilar(IlerlemeTabani):
    """P-02: sure_sn icin NaN kabul ediliyor, ogretmen panelindeki int() cokup liste zamanlayicisini durduruyordu."""

    def test_nan_ve_sonsuz_reddedilir(self):
        onceki = dict(self.oda.ogrenciler["Ali"])
        for ek in ('"sure_sn":NaN', '"sure_sn":Infinity', '"sure_sn":-Infinity', '"sure_sn":1e999',
                   '"sure_sn":1,"puan":1e999', '"sure_sn":1,"soru_no":NaN', '"sure_sn":1,"puan":-1e999'):
            kod, yanit = self.ham_ilerleme(ek)
            self.assertEqual(kod, 400, ek)
        self.assertEqual(self.oda.ogrenciler["Ali"], onceki)

    def test_sure_araliga_kirpilir(self):
        for gelen, beklenen in ((10 ** 12, ogretmen_sunucu.MAKS_SURE_SN), (-5, 0), (12.5, 12.5),
                                (10 ** 400, ogretmen_sunucu.MAKS_SURE_SN)):
            self.assertEqual(self.ilerleme(sure_sn=gelen)[0], 200, gelen)
            self.assertEqual(self.oda.ogrenciler["Ali"]["sure_sn"], beklenen)
            int(self.oda.ogrenciler["Ali"]["sure_sn"])          # ogretmen panelinin yaptigi cevrim

    def test_ogretmen_paneli_zamanlayicisi_istisnaya_dayanikli(self):
        k = kaynak("ogretmen_uygulama.py")
        govde = k.split("    def _listeyi_guncelle(self):", 1)[1].split("    def _listeyi_ciz(self):", 1)[0]
        self.assertIn("try:", govde)
        self.assertIn("except Exception", govde)
        self.assertIn("return True", govde)
        self.assertIn("GLib.timeout_add(800, self._listeyi_guncelle)", k)


class P06Sinirlar(IlerlemeTabani):
    """P-06: puan, soru_no, cevap kaydi ve ogrenci sayisinda ust sinir yoktu."""

    def test_puan_gorevin_en_yuksek_puaniyla_sinirlanir(self):
        no = self.oda.gorev_ata("hydra-01", "zor")
        self.assertEqual(self.ilerleme(durum="tamamlandi", cevap="x", soru_no=no, puan=10 ** 9)[0], 200)
        ozet = self.oda.sinif_ozeti()[0]
        sinir = ogretmen_sunucu.gorev_en_yuksek_puan("hydra-01")
        self.assertTrue(0 < sinir < ogretmen_sunucu.GENEL_PUAN_SINIRI)
        self.assertEqual((ozet["cozulen"], ozet["puan"]), (1, sinir))

    def test_atanmamis_soru_ve_yanlis_gorev_puanlanmaz(self):
        no = self.oda.gorev_ata("hydra-01", "orta")
        for alanlar in ({"soru_no": 999}, {"soru_no": no + 1}, {"soru_no": no, "gorev_id": "nmap-01"},
                        {"soru_no": no, "gorev_id": "../../etc/passwd"}, {"soru_no": 0}, {}):
            self.assertEqual(self.ilerleme(durum="tamamlandi", cevap="x", puan=100, **alanlar)[0], 200, alanlar)
        self.assertEqual(self.oda.cozulen_sorular.get("Ali", {}), {})
        self.assertEqual(self.oda.sinif_ozeti()[0]["puan"], 0)
        # cevap kayitlarindaki soru numarasi da atanan araligin disina cikamaz
        self.assertTrue(all(0 <= k["soru_no"] <= no for k in self.oda.cevaplar["Ali"]))

    def test_cozulen_kayit_sayisi_atanan_soru_sayisini_asamaz(self):
        for _ in range(3):
            self.oda.gorev_ata("hydra-01", "orta")
        for no in range(0, 300):
            self.ilerleme(durum="tamamlandi", cevap="x", soru_no=no, puan=10)
        self.assertEqual(sorted(self.oda.cozulen_sorular["Ali"]), [1, 2, 3])

    def test_cevap_kaydi_sinirlidir(self):
        eski = ogretmen_sunucu.MAKS_CEVAP_KAYDI
        ogretmen_sunucu.MAKS_CEVAP_KAYDI = 5
        self.addCleanup(setattr, ogretmen_sunucu, "MAKS_CEVAP_KAYDI", eski)
        for i in range(12):
            self.ilerleme(durum="yanlis_denedi", cevap="deneme%d" % i)
        self.assertEqual([k["cevap"] for k in self.oda.cevaplar["Ali"]], ["deneme%d" % i for i in range(7, 12)])

    def test_gecersiz_alan_turleri_400(self):
        for alanlar in ({"durum": "uydurma"}, {"durum": "x" * 70}, {"soru_no": "3"}, {"soru_no": 1.5},
                        {"puan": True}, {"puan": [1]}, {"sure_sn": "5"}, {"sure_sn": True}, {"gorev_id": 7},
                        {"gorev_id": "g" * 65}, {"cevap": 5}, {"cevap": "c" * 1001}):
            self.assertEqual(self.ilerleme(**alanlar)[0], 400, alanlar)

    def test_sinif_doludur(self):
        self.oda.maks_ogrenci = 3
        self.katil_tamam("Veli")
        self.katil_tamam("Ayşe")
        kod, yanit = self.katil("Can")
        self.assertEqual((kod, yanit["hata"]), (409, "sinif_dolu"))
        self.oda.ogrenciyi_at("Veli")
        self.katil_tamam("Can")

    def test_adres_basina_katilim_sinirlidir(self):
        self.oda.adres_basina = 2
        self.katil_tamam("Veli")                                    # Ali + Veli = 2 (hepsi 127.0.0.1)
        kod, yanit = self.katil("Can")
        self.assertEqual((kod, yanit["hata"]), (429, "adres_siniri"))
        self.assertNotIn("Can", self.oda.ogrenciler)
        self.oda.ogrenciyi_at("Ali")
        self.katil_tamam("Can")

    def test_varsayilan_sinirlar(self):
        self.assertEqual((self.oda.maks_ogrenci, self.oda.adres_basina), (200, 40))


class P09AtilmaYarisi(IlerlemeTabani):
    """P-09: anahtar denetimi ile yazma ayri kilit bolumlerindeydi; atilan ogrenci anahtarsiz geri yazilabiliyordu."""

    def test_atilan_ogrenci_ilerleme_ile_geri_gelmez(self):
        self.oda.ogrenciyi_at("Ali")
        self.assertFalse(self.oda.ilerleme_bildir("Ali", self.anahtar, "hydra-01", "basladi", 0))
        self.assertEqual(self.ilerleme()[0], 403)
        self.assertNotIn("Ali", self.oda.ogrenciler)
        self.katil_tamam("Ali")                                     # ad kilitli kalmadi

    def test_yaris_altinda_hayalet_olusmaz(self):
        import threading
        dur = threading.Event()
        anahtarlar = [self.anahtar]

        def bildir():
            while not dur.is_set():
                self.oda.ilerleme_bildir("Ali", anahtarlar[-1], "hydra-01", "basladi", 0)
        isler = [threading.Thread(target=bildir, daemon=True) for _ in range(4)]
        for t in isler:
            t.start()
        try:
            for _ in range(300):
                self.oda.ogrenciyi_at("Ali")
                self.assertNotIn("Ali", self.oda.ogrenciler)
                self.assertEqual(self.oda.anahtar_ver("Ali"), "")
                self.oda.katil("Ali", SIFRE)
                anahtarlar.append(self.oda.anahtar_ver("Ali"))
        finally:
            dur.set()
            for t in isler:
                t.join(2)

    def test_yanlis_anahtar_hicbir_sey_yazmaz(self):
        onceki = dict(self.oda.ogrenciler["Ali"])
        for anahtar in ("", "0" * 32, None, 5, ["x"]):
            self.assertFalse(self.oda.ilerleme_bildir("Ali", anahtar, "hydra-01", "tamamlandi", 5, "x", 0, 50))
        self.assertEqual(self.oda.ogrenciler["Ali"], onceki)
        self.assertEqual(self.oda.cevaplar, {})


class P12YakalanmayanIstisnalar(Taban):
    """P-12: derin ic ice JSON ve Infinity yanitsiz baglanti kopmasina yol aciyordu."""

    def test_derin_json_400(self):
        for ham in (b"[" * 60000, b'{"a":' * 12000, b"9" * 5000):
            kod, yanit = self.istek("POST", "/katil", ham=ham)
            self.assertEqual(kod, 400)
            self.assertEqual(yanit["hata"], "geçersiz JSON")

    def test_beklenmeyen_hata_500_doner_sunucu_ayakta_kalir(self):
        def patla(*_a, **_k):
            raise RuntimeError("beklenmeyen")
        self.oda.katil = patla
        kod, yanit = self.katil("Veli")
        self.assertEqual((kod, yanit), (500, {"hata": "sunucu_hatasi"}))
        del self.oda.katil
        self.katil_tamam("Veli")


if __name__ == "__main__":
    unittest.main()
