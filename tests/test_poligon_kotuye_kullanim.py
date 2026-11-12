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


class P03BaglantiSinirlari(Taban):
    """P-03: her baglantiya sinirsiz is parcacigi aciliyor, yavas bayt gonderen baglanti suresiz acik kaliyordu."""

    YARIM = b"POST /katil HTTP/1.0\r\nContent-Length: 60000\r\n\r\n"

    def _ac(self, veri=None):
        import socket
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        self.addCleanup(s.close)
        if veri:
            s.sendall(veri)
        return s

    def _bekle(self, kosul, sure=5.0):
        import time
        bitis = time.time() + sure
        while time.time() < bitis:
            if kosul():
                return True
            time.sleep(0.05)
        return kosul()

    def _kapandi_mi(self, s):
        """Karsi taraf baglantiyi kapattiysa True (okuma bos doner ya da sifirlanir)."""
        import socket
        s.settimeout(0.2)
        try:
            return s.recv(1) == b""
        except socket.timeout:
            return False
        except OSError:
            return True

    def test_adres_basina_eszamanli_baglanti_sinirlidir(self):
        self.sunucu.adres_basina_baglanti = 8
        acik = [self._ac(self.YARIM) for _ in range(8)]
        self.assertTrue(self._bekle(lambda: self.sunucu.aktif_baglanti() == 8))
        fazla = [self._ac(self.YARIM) for _ in range(20)]
        self.assertTrue(self._bekle(lambda: self.sunucu.reddedilen == 20))
        self.assertEqual(self.sunucu.aktif_baglanti(), 8)            # fazlasi icin is parcacigi acilmadi
        self.assertTrue(all(self._kapandi_mi(s) for s in fazla))
        self.assertFalse(any(self._kapandi_mi(s) for s in acik))
        for s in acik:
            s.close()
        self.assertTrue(self._bekle(lambda: self.sunucu.aktif_baglanti() == 0))
        self.katil_tamam("Ali")                                      # yer acilinca sunucu normal calisir

    def test_toplam_baglanti_sinirlidir(self):
        self.sunucu.maks_baglanti = 5
        [self._ac(self.YARIM) for _ in range(5)]
        self.assertTrue(self._bekle(lambda: self.sunucu.aktif_baglanti() == 5))
        s = self._ac(self.YARIM)
        self.assertTrue(self._bekle(lambda: self._kapandi_mi(s)))
        self.assertEqual(self.sunucu.aktif_baglanti(), 5)

    def test_yavas_bayt_gonderen_baglanti_toplam_surede_kapatilir(self):
        import time
        self.sunucu.istek_toplam_sure = 1.0
        s = self._ac(self.YARIM)
        bas = time.time()
        kapandi = False
        while time.time() - bas < 6:
            try:
                s.sendall(b"x")                                      # okuma zaman asimini (10 sn) hic doldurmaz
            except OSError:
                kapandi = True
                break
            if self._kapandi_mi(s):
                kapandi = True
                break
            time.sleep(0.2)
        self.assertTrue(kapandi, "yavas baglanti toplam sure dolmasina ragmen acik kaldi")
        self.assertLess(time.time() - bas, 4)
        self.assertTrue(self._bekle(lambda: self.sunucu.aktif_baglanti() == 0))
        self.katil_tamam("Ali")

    def test_varsayilanlar_ve_normal_yuk(self):
        self.assertEqual((self.sunucu.maks_baglanti, self.sunucu.adres_basina_baglanti), (256, 32))
        self.assertEqual(self.sunucu.istek_toplam_sure, 20.0)
        import threading
        sonuc = []

        def is_(i):
            sonuc.append(self.katil("Ogrenci %d" % i)[0])
        isler = [threading.Thread(target=is_, args=(i,)) for i in range(30)]
        for t in isler:
            t.start()
        for t in isler:
            t.join(10)
        self.assertEqual(sonuc, [200] * 30)                          # 30 es zamanli gercek ogrenci reddedilmez
        self.assertTrue(self._bekle(lambda: self.sunucu.aktif_baglanti() == 0))
        self.assertEqual(self.sunucu.reddedilen, 0)


class P08SifresizBilgiSizintisi(Taban):
    """P-08: sifresiz /durum butun ogrenci adlarini veriyor, /aktif_mi ad yoklamaya izin veriyordu."""

    def test_durum_yolu_kaldirildi(self):
        self.katil_tamam("Ali")
        kod, yanit = self.istek("GET", "/durum")
        self.assertEqual(kod, 404)
        self.assertNotIn("Ali", json.dumps(yanit))

    def test_sifresiz_yollar_ogrenci_adi_vermez(self):
        self.katil_tamam("Gizli Öğrenci")
        self.oda.gorev_ata("hydra-01", "orta")
        for yol in ("/gorevler", "/durum", "/", "/ogrenciler", "/sohbet", "/ctf/skor", "/aktif_mi?ogrenci=x"):
            kod, yanit = self.istek("GET", yol)
            self.assertNotIn("Gizli", json.dumps(yanit, ensure_ascii=False), yol)
        self.assertEqual(self.istek("GET", "/gorevler")[0], 200)

    def test_aktif_mi_sifre_ve_anahtar_ister(self):
        anahtar = self.katil_tamam("Ali")
        q = lambda **k: "/aktif_mi?" + urllib.parse.urlencode(k)   # noqa: E731
        self.assertEqual(self.istek("GET", q(ogrenci="Ali"))[0], 403)                         # sifresiz
        self.assertEqual(self.istek("GET", q(ogrenci="Ali", sifre="yanlis"))[0], 403)
        # dogru sifre, anahtar yok/yanlis: var olan ad ile olmayan ad AYNI yaniti verir (ad yoklanamaz)
        var = self.istek("GET", q(ogrenci="Ali", sifre=SIFRE, anahtar="0" * 32))
        yok = self.istek("GET", q(ogrenci="Yok", sifre=SIFRE, anahtar="0" * 32))
        self.assertEqual(var, yok)
        self.assertEqual(var, (200, {"aktif": False}))
        self.assertEqual(self.istek("GET", q(ogrenci="Ali", sifre=SIFRE, anahtar=anahtar)), (200, {"aktif": True}))

    def test_istemci_atilmayi_ve_gecici_hatayi_ayirir(self):
        ist = ogrenci_istemci.PoligonIstemci(self.adres, "1234", SIFRE, "Ali")
        self.assertEqual(ist.katil(), (True, ""))
        self.assertEqual(ist.sinif_baglanti_durumu(), "aktif")
        self.oda.ogrenciyi_at("Ali")
        self.assertEqual(ist.sinif_baglanti_durumu(), "atildi")
        # Sunucu 429/5xx donerse bu "atildim" anlamina gelmez
        ist2 = ogrenci_istemci.PoligonIstemci(self.adres, "1234", SIFRE, "Veli")
        self.assertEqual(ist2.katil(), (True, ""))
        ist2.oda_sifre = "yanlis"
        self.assertEqual(ist2.sinif_baglanti_durumu(), "belirsiz")

    def test_belge_kodla_uyumlu(self):
        """P-24: modul basligindaki protokol listesi gercek yollarla ayni."""
        k = kaynak("ogretmen_sunucu.py")
        baslik = k.split('"""', 2)[1]
        for yok in ("/ipucu_gonder", "GET  /ipucu?", "GET  /durum"):
            self.assertNotIn(yok, baslik)
        for var in ("/katil", "/ilerleme", "/mesaj", "/sohbet", "/aktif_mi", "/gorevler", "/ctf/durum"):
            self.assertIn(var, baslik)
            self.assertIn('"%s"' % var, k.split('"""', 2)[2], var)


class SahteSunucu:
    """Her baglantiya ayni ham yaniti veren (ya da hic yanit vermeyen) tek amacli sunucu."""

    def __init__(self, yanit=None, kapat=True):
        import socket
        import threading
        self.yanit, self.kapat, self.istek_sayisi = yanit, kapat, 0
        self._acik = []
        self.s = socket.socket()
        self.s.bind(("127.0.0.1", 0))
        self.s.listen(16)
        self.adres = "http://127.0.0.1:%d" % self.s.getsockname()[1]
        threading.Thread(target=self._dongu, daemon=True).start()

    def _dongu(self):
        while True:
            try:
                c, _ = self.s.accept()
            except OSError:
                return
            self.istek_sayisi += 1
            try:
                c.settimeout(2)
                c.recv(65536)
                if self.yanit is not None:
                    c.sendall(self.yanit)
                if self.kapat:
                    # Okunmamis istek verisi varken kapatmak RST gonderir ve istemci yaniti goremez:
                    # once yazma yonunu kapat, istemcinin gonderdiklerini tuket, sonra kapat.
                    import socket as _s
                    try:
                        c.shutdown(_s.SHUT_WR)
                        c.settimeout(0.5)
                        while c.recv(65536):
                            pass
                    except OSError:
                        pass
                    c.close()
                else:
                    self._acik.append(c)
            except OSError:
                pass

    def durdur(self):
        self.s.close()
        for c in self._acik:
            c.close()


def http_yaniti(govde, durum="200 OK", ek_baslik=""):
    if isinstance(govde, str):
        govde = govde.encode("utf-8")
    return ("HTTP/1.0 %s\r\nContent-Type: application/json\r\n%s\r\n" % (durum, ek_baslik)).encode() + govde


class P04IstemciDayanikliligi(unittest.TestCase):
    """P-04, P-18, P-19: _istek yalnizca BaglantiHatasi firlatir; ust duzey yontemler hicbir sunucu
    davranisinda istisna firlatmaz (aksi halde arayuzun 3 sn'lik zamanlayicisi kalici olarak dururdu)."""

    def setUp(self):
        eski = ogrenci_istemci.ISTEK_ZAMAN_ASIMI
        ogrenci_istemci.ISTEK_ZAMAN_ASIMI = 0.6
        self.addCleanup(setattr, ogrenci_istemci, "ISTEK_ZAMAN_ASIMI", eski)

    def sahte(self, *a, **k):
        s = SahteSunucu(*a, **k)
        self.addCleanup(s.durdur)
        return s

    def kotu_sunucular(self):
        return {
            "yanit vermiyor": self.sahte(None, kapat=False),
            "hemen kapatiyor": self.sahte(None),
            "html hata sayfasi": self.sahte(http_yaniti("<html>proxy</html>", "502 Bad Gateway")),
            "bos govde": self.sahte(http_yaniti("")),
            "json listesi": self.sahte(http_yaniti("[1,2,3]")),
            "json sayisi": self.sahte(http_yaniti("7")),
            "bozuk http": self.sahte(b"\x00\x01\x02 anlamsiz\r\n\r\n"),
            "yarim yanit": self.sahte(b"HTTP/1.0 200 OK\r\nContent-Length: 500\r\n\r\n{\"a\":"),
            "dev yanit": self.sahte(http_yaniti(b'{"a":"' + b"x" * (ogrenci_istemci.MAKS_YANIT + 10) + b'"}')),
            "derin json": self.sahte(http_yaniti("[" * 50000)),
            "utf8 degil": self.sahte(http_yaniti(b'{"a":"\xff\xfe"}')),
        }

    def test_istek_yalnizca_baglanti_hatasi_firlatir(self):
        for ad, sunucu in self.kotu_sunucular().items():
            ist = ogrenci_istemci.PoligonIstemci(sunucu.adres, "1", SIFRE, "Ali")
            for yontem, yol in (("GET", "/gorevler"), ("POST", "/katil")):
                with self.assertRaises(ogrenci_istemci.BaglantiHatasi, msg=ad):
                    ist._istek(yol, {}, yontem)

    def test_ust_duzey_yontemler_istisna_firlatmaz(self):
        for ad, sunucu in self.kotu_sunucular().items():
            ist = ogrenci_istemci.PoligonIstemci(sunucu.adres, "1", SIFRE, "Ali")
            ist.gorev = {"id": "x"}
            self.assertEqual(ist.katil(), (False, "__BAGLANTI_HATASI__"), ad)
            self.assertEqual(ist.sinif_baglanti_durumu(), "belirsiz", ad)
            self.assertIsNone(ist.gorev_degisti_mi(), ad)
            self.assertEqual(ist.yeni_mesajlari_getir(), [], ad)
            self.assertFalse(ist.mesaj_gonder("selam"), ad)
            ist._bildir("basladi")                                   # sessizce yutulur

    def test_kapali_port_oda_kapandi_sayilir(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        ist = ogrenci_istemci.PoligonIstemci("http://127.0.0.1:%d" % port, "1", SIFRE, "Ali")
        with self.assertRaises(ogrenci_istemci.OdaKapaliHatasi):
            ist._istek("/gorevler", {}, "GET")
        self.assertEqual(ist.sinif_baglanti_durumu(), "oda_kapandi")

    def test_bozuk_alanli_gorev_yaniti_cokertmez(self):
        govde = json.dumps({"acik_gorevler": ["nmap-01", 5, None, ["x"]], "zorluklar": {"nmap-01": 7, "a": "zor"},
                            "parametreler": {"nmap-01": "dizgi", "b": {"x": 1}}, "varyantlar": {"nmap-01": "abc", "c": 3,
                                                                                         "d": 1e400, "e": True},
                            "hedef_adres": "8.8.8.8", "ayar_surumu": "çok", "aktif_soru_no": [1]})
        ist = ogrenci_istemci.PoligonIstemci(self.sahte(http_yaniti(govde)).adres, "1", SIFRE, "Ali")
        self.assertEqual(ist.acik_gorevleri_getir(), ["nmap-01"])
        self.assertEqual(ist._acik_zorluklar, {"a": "zor"})
        self.assertEqual(ist._acik_ozel, {"b": {"x": 1}})
        self.assertEqual(ist._acik_varyantlar, {"c": 3})
        self.assertIsNone(ist.sinif_hedef_adres)                     # loopback olmayan hedef adres yok sayilir
        self.assertEqual((ist.ayar_surumu, ist.aktif_soru_no), (0, 0))
        for govde in ('{"acik_gorevler": "nmap-01"}', '{"varyantlar": [1]}', "{}"):
            ist = ogrenci_istemci.PoligonIstemci(self.sahte(http_yaniti(govde)).adres, "1", SIFRE, "Ali")
            self.assertEqual(ist.acik_gorevleri_getir(), [])

    def test_bozuk_mesaj_listesi_cokertmez(self):
        govde = json.dumps({"mesajlar": [{"metin": "no yok"}, "dizgi", {"no": "3", "metin": "x"}, {"no": True},
                                         {"no": 4, "metin": "gecerli", "kimden": "ogretmen"}]})
        ist = ogrenci_istemci.PoligonIstemci(self.sahte(http_yaniti(govde)).adres, "1", SIFRE, "Ali")
        self.assertEqual([m["no"] for m in ist.yeni_mesajlari_getir()], [4])
        ist = ogrenci_istemci.PoligonIstemci(self.sahte(http_yaniti('{"mesajlar": 5}')).adres, "1", SIFRE, "Ali")
        self.assertEqual(ist.yeni_mesajlari_getir(), [])

    def test_yonlendirme_izlenmez(self):
        hedef = self.sahte(http_yaniti('{"tamam": true, "anahtar": "calinti"}'))
        yonlendiren = self.sahte(http_yaniti("", "302 Found", "Location: %s/katil\r\n" % hedef.adres))
        ist = ogrenci_istemci.PoligonIstemci(yonlendiren.adres, "1", SIFRE, "Ali")
        self.assertEqual(ist.katil(), (False, "__BAGLANTI_HATASI__"))
        self.assertEqual(hedef.istek_sayisi, 0)                      # sifre ikinci adrese gitmedi

    def test_vekil_sunucu_kullanilmaz(self):
        vekil = self.sahte(http_yaniti('{"aktif": false}'))
        gercek = self.sahte(http_yaniti('{"aktif": true}'))
        for anahtar in ("http_proxy", "HTTP_PROXY", "all_proxy"):
            eski = os.environ.get(anahtar)
            os.environ[anahtar] = vekil.adres
            self.addCleanup(lambda a=anahtar, e=eski: os.environ.pop(a, None) if e is None else os.environ.__setitem__(a, e))
        ist = ogrenci_istemci.PoligonIstemci(gercek.adres, "1", SIFRE, "Ali")
        self.assertEqual(ist.sinif_baglanti_durumu(), "aktif")
        self.assertEqual((vekil.istek_sayisi, gercek.istek_sayisi), (0, 1))

    def test_http_disi_adres_reddedilir(self):
        for adres in ("file:///etc/passwd", "ftp://127.0.0.1", "https://127.0.0.1:8642", "127.0.0.1:8642"):
            ist = ogrenci_istemci.PoligonIstemci(adres, "1", SIFRE, "Ali")
            with self.assertRaises(ogrenci_istemci.BaglantiHatasi):
                ist._istek("/gorevler", {}, "GET")

    def test_arayuz_ag_cagrilarini_ana_is_parcaciginda_yapmaz(self):
        k = kaynak("ogrenci_uygulama.py")
        for cagri in ("self.istemci.sinif_baglanti_durumu()", "self.istemci.gorev_degisti_mi()",
                      "self.istemci.yeni_mesajlari_getir()", "self.istemci.acik_gorevleri_getir()",
                      "self.istemci.gorevi_degistir("):
            self.assertNotIn(cagri, k, cagri)
        for govde in (k.split("    def _ipucu_izlemeyi_baslat(self):", 1)[1].split("    def _mesajlari_ekle", 1)[0],
                      k.split("    def _bekleme_izlemeyi_baslat(self):", 1)[1].split("    def _beklemeden_goreve", 1)[0]):
            self.assertIn("threading.Thread(target=arka_plan", govde)
            self.assertIn("GLib.idle_add(uygula", govde)
            self.assertIn("except Exception", govde)
            kontrol = govde.split("        def kontrol_et():", 1)[1]
            self.assertNotIn("istemci.sinif", kontrol)
            self.assertIn("return True", kontrol)
        self.assertIn("istemci.eszamansiz_bildirim = True", k)


class P17AdresAlani(unittest.TestCase):
    """P-17: 'ip:port' gibi bir adres yakalanmayan InvalidURL ile ekrani 'Bağlanıyor…' yazisinda birakiyordu."""

    def test_gecerli_adresler(self):
        f = ogrenci_istemci.ogretmen_adresi
        for girdi, beklenen in (("192.168.1.5", "http://192.168.1.5:8642"), (" 192.168.1.5 ", "http://192.168.1.5:8642"),
                                ("192.168.1.5:8642", "http://192.168.1.5:8642"), ("http://10.0.0.7/", "http://10.0.0.7:8642"),
                                ("HTTP://10.0.0.7:8642/", "http://10.0.0.7:8642"), ("ogretmen-pc", "http://ogretmen-pc:8642"),
                                ("ogretmen.local", "http://ogretmen.local:8642"), ("localhost", "http://localhost:8642")):
            self.assertEqual(f(girdi), beklenen, girdi)

    def test_gecersiz_adresler(self):
        f = ogrenci_istemci.ogretmen_adresi
        for girdi in ("", "   ", "192.168.1.5:9999", "192.168.1.5:8642:8642", "999.1.1.1", "1.2.3", "1.2.3.4.5",
                      "evil.com/x?", "kullanici@evil.com", "a b", "192.168.1.5/yol", "[::1]", "::1", "ör.nek", "-a.com",
                      "a..b", "x" * 300, "http://", "file:///etc/passwd", "1.2.3.4#", "1.2.3.4\n5", None, 5):
            self.assertIsNone(f(girdi), repr(girdi))

    def test_arayuz_adresi_dogrular_ve_beklenmeyen_hatada_kilitlenmez(self):
        k = kaynak("ogrenci_uygulama.py")
        govde = k.split("    def _odaya_katil(self, _düğme):", 1)[1].split("\n    def ", 1)[0]
        self.assertIn("ogretmen_adresi(adres)", govde)
        self.assertIn('m["hata_adres"]', govde)
        self.assertIn("except Exception", govde)
        self.assertNotIn('f"http://{adres}:8642"', k)


class KatilimRetKodlari(Taban):
    """Sunucunun ret nedenleri kod olarak tasinir; ogrenci arayuzu kendi dilinde gosterir."""

    def test_istemci_ret_kodunu_saklar(self):
        self.katil_tamam("Ali")
        for ad, sifre, kod in (("Ali", SIFRE, "isim_alinmis"), ("tum_sinif", SIFRE, "geçersiz isim"),
                               ("Veli", "yanlis", "yanlış şifre")):
            ist = ogrenci_istemci.PoligonIstemci(self.adres, "1234", sifre, ad)
            self.assertFalse(ist.katil()[0])
            self.assertEqual(ist.son_hata_kodu, kod)
        self.oda.maks_ogrenci = 1
        ist = ogrenci_istemci.PoligonIstemci(self.adres, "1234", SIFRE, "Can")
        self.assertFalse(ist.katil()[0])
        self.assertEqual(ist.son_hata_kodu, "sinif_dolu")

    def test_her_ret_kodunun_iki_dilde_metni_var(self):
        import ast
        k = kaynak("ogrenci_uygulama.py")
        tablo = ast.literal_eval(k.split("KATIL_HATA_ANAHTARI = ", 1)[1].split("}\n", 1)[0] + "}")
        sunucu = kaynak("ogretmen_sunucu.py")
        self.assertEqual(set(tablo), {"yanlış şifre", "cok_fazla_deneme", "isim_alinmis", "geçersiz isim",
                                      "sinif_dolu", "adres_siniri"})
        for kod, anahtar in tablo.items():
            self.assertIn('"hata": "%s"' % kod, sunucu, kod)
            self.assertEqual(k.count('        "%s": "' % anahtar), 2, anahtar)      # tr + en


class EszamansizBildirim(IlerlemeTabani):
    """Arayuz bildirimleri arka planda gonderir; sira korunur ve cagiran beklemez."""

    def test_sira_korunur_ve_cagiran_beklemez(self):
        import time
        ist = ogrenci_istemci.PoligonIstemci(self.adres, "1234", SIFRE, "Veli")
        self.assertTrue(ist.katil()[0])
        ist.gorev = {"id": "hydra-01"}
        ist.eszamansiz_bildirim = True
        for i in range(20):
            ist._bildir("yanlis_denedi", i, cevap="deneme%d" % i)
        ist._bildir("tamamlandi", 99, cevap="son")
        self.assertTrue(ist.bildirimleri_bekle(10))
        self.assertEqual([k["cevap"] for k in self.oda.cevaplar["Veli"]], ["deneme%d" % i for i in range(20)] + ["son"])
        self.assertEqual(self.oda.ogrenciler["Veli"]["durum"], "tamamlandi")
        # ulasilamayan sunucuda cagri aninda doner
        s = SahteSunucu(None, kapat=False)
        self.addCleanup(s.durdur)
        ist2 = ogrenci_istemci.PoligonIstemci(s.adres, "1", SIFRE, "x")
        ist2.gorev = {"id": "hydra-01"}
        ist2.eszamansiz_bildirim = True
        bas = time.time()
        ist2._bildir("basladi")
        self.assertLess(time.time() - bas, 0.5)


class BireyselTabani(unittest.TestCase):
    """Ag kullanmayan (bireysel mod) istemci; gecmis defteri gecici dosyaya yazilir."""

    def setUp(self):
        import shutil
        import tempfile
        import gecmis_defteri
        from pathlib import Path
        dizin = tempfile.mkdtemp(prefix="poligon-test-")
        self.addCleanup(shutil.rmtree, dizin, True)
        eski = gecmis_defteri.GECMIS_DOSYASI
        gecmis_defteri.GECMIS_DOSYASI = Path(dizin) / "gecmis.json"
        self.addCleanup(setattr, gecmis_defteri, "GECMIS_DOSYASI", eski)
        self.ist = ogrenci_istemci.PoligonIstemci("", "", "", "bireysel")
        self.addCleanup(self.ist.gorevi_durdur)


class P05GorevKimligi(BireyselTabani):
    """P-05: sunucudan gelen gorev kimligi dogrulanmadan dosya yoluna ekleniyordu ('../', mutlak yol)."""

    def test_dizin_disi_kimlikler_reddedilir(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"id": "DISARIDAN", "hedef": {}, "flag_uretimi": {"yontem": "sistem_kontrolu"}}, f)
        self.addCleanup(os.remove, f.name)
        disarida = f.name[:-len(".json")]
        for kimlik in (disarida, "../" * 12 + disarida.lstrip("/"), "../nmap-01", "gorevler/nmap-01", "nmap-01.json",
                       "a\\b", "", " ", "NMAP-01", "nmap 01", "nmap-01\n", "x" * 65, "-nmap", ".", "..", None, 5,
                       ["nmap-01"]):
            with self.assertRaises(ValueError, msg=repr(kimlik)):
                self.ist.gorevi_yukle(kimlik)
        self.assertIsNone(self.ist.gorev)

    def test_gecerli_kimlikler_yuklenir(self):
        self.assertEqual(self.ist.gorevi_yukle("nmap-01")["id"], "nmap-01")
        # dosyasi olmayan gecerli kimlik: sablon gorev (eski davranis)
        self.assertEqual(self.ist.gorevi_yukle("hydra-01")["id"], "hydra-01")
        for dosya in os.listdir(os.path.join(POLIGON, "gorevler")):
            self.assertTrue(ogrenci_istemci.gorev_kimligi_gecerli_mi(dosya[:-len(".json")]), dosya)

    def test_sunucudan_gelen_gecersiz_kimlikler_elenir(self):
        govde = json.dumps({"acik_gorevler": ["/etc/passwd", "../../x", "nmap-01", "A", "john-01"]})
        s = SahteSunucu(http_yaniti(govde))
        self.addCleanup(s.durdur)
        ist = ogrenci_istemci.PoligonIstemci(s.adres, "1", SIFRE, "Ali")
        self.assertEqual(ist.acik_gorevleri_getir(), ["nmap-01", "john-01"])

    def test_gecersiz_jail_adi_sudo_calistirmaz(self):
        cagrilar = []
        eski = ogrenci_istemci.sudo_ile_calistir
        ogrenci_istemci.sudo_ile_calistir = lambda *a, **k: cagrilar.append(a) or (True, "Status for the jail: x", "")
        self.addCleanup(setattr, ogrenci_istemci, "sudo_ile_calistir", eski)
        for jail in ("-h", "--help", "-c/tmp/x", "sshd; rm -rf /", "a b", "", "../x", "x" * 65, None, 5, ["sshd"]):
            self.ist.gorev = {"id": "fail2ban-01", "hedef": {"jail": jail}}
            basarili, mesaj = self.ist.fail2ban_durumunu_dogrula("parola")
            self.assertFalse(basarili, repr(jail))
        self.assertEqual(cagrilar, [])
        self.ist.gorev = {"id": "fail2ban-01", "hedef": {"jail": "sshd"}, "puan": 10}
        self.assertTrue(self.ist.fail2ban_durumunu_dogrula("parola")[0])
        self.assertEqual(cagrilar, [(["fail2ban-client", "status", "sshd"], "parola")])

    def test_sudo_komutu_secenek_olarak_yorumlanamaz(self):
        import subprocess
        gorulen = []

        class Sonuc:
            returncode, stdout, stderr = 0, "", ""
        eski = subprocess.run
        subprocess.run = lambda argv, **k: gorulen.append(argv) or Sonuc()
        self.addCleanup(setattr, subprocess, "run", eski)
        ogrenci_istemci.sudo_ile_calistir(["ufw", "status"], "p")
        self.assertEqual(gorulen, [["sudo", "-S", "-k", "--", "ufw", "status"]])


class P07SunucuParametreleri(BireyselTabani):
    """P-07: sunucudan gelen gorev parametreleri istemcide sinirlanmiyordu."""

    def test_parametreleri_temizle(self):
        f = ogrenci_istemci.parametreleri_temizle
        for bozuk in (None, 5, "x", [1, 2], [("a", 1)]):
            self.assertEqual(f(bozuk), {})
        girdi = {"gurultu": 3, "kodlama": "hex", "hizmetler": ["ftp", "telnet"], "gizli_port_araligi": [20000, 20999],
                 "ipucu": {"tr": "ipucu", "en": "hint"}, "_etiket": "soru", "bayrak": True, "oran": 0.5}
        self.assertEqual(f(girdi), girdi)
        atilan = {5: "sayi anahtar", "": "bos anahtar", "k" * 41: "uzun anahtar", "uzun": "x" * 501,
                  "dev": 10 ** 30, "nan": float("nan"), "sonsuz": float("inf"), "ic_ice": {"a": {"b": 1}},
                  "liste_ic": [[1]], "uzun_liste": list(range(17)), "nesne": object()}
        self.assertEqual(f(atilan), {})
        self.assertEqual(len(f({"p%d" % i: i for i in range(200)})), ogrenci_istemci.MAKS_PARAMETRE)

    def test_atanan_parametreler_temizlenir(self):
        self.ist._acik_ozel = {"nmap-01": {"gurultu_sayisi": 5, "kotu": {"a": {"b": 1}}}, "bos": {"x": object()}}
        self.assertEqual(self.ist.atanan_parametreler("nmap-01"), {"gurultu_sayisi": 5})
        self.assertIsNone(self.ist.atanan_parametreler("bos"))
        self.assertIsNone(self.ist.atanan_parametreler("yok"))

    def test_port_araligi(self):
        f = ogrenci_istemci.port_araligi
        self.assertEqual(f([20000, 20999]), (20000, 20999))
        self.assertEqual(f((1024, 65535)), (1024, 65535))
        for bozuk in ([80, 90], [1023, 2000], [2000, 2000], [3000, 2000], [20000, 65536], [70000, 70010], ["a", "b"],
                      [20000], [1, 2, 3], "20000-20999", None, 5, [True, 20000], [20000.0, 20999]):
            self.assertIsNone(f(bozuk), repr(bozuk))

    def test_servisler_kendi_sinirlarini_uygular(self):
        from servisler.sahte_ag import SahteAgOrtami
        from servisler.sahte_trafik import MAKS_GURULTU, SahteTrafik
        import flag_uretici
        self.assertEqual(SahteTrafik("f", 1, gurultu=100000).gurultu, MAKS_GURULTU)
        self.assertEqual(MAKS_GURULTU, 16)
        for bozuk in ("x", None, [1], float("inf")):
            self.assertEqual(SahteTrafik("f", 1, gurultu=bozuk).gurultu, 0)
        for bozuk in ((80, 80), (80, 90), (70000, 70010), ("a", "b"), (20000,), None, 5, (20999, 20000), (True, 30000)):
            with self.assertRaises(ValueError, msg=repr(bozuk)):
                SahteAgOrtami(gizli_port_araligi=bozuk)
        ortam = SahteAgOrtami(gizli_port_araligi=(20000, 20010), gurultu_sayisi="çok")
        self.assertTrue(20000 <= ortam.gizli_port < 20010)
        self.assertEqual(len(ortam.gurultu_portlari), 5)
        self.assertEqual(len(SahteAgOrtami(gurultu_sayisi=10 ** 9).gurultu_portlari), 12)
        import time
        bas = time.time()
        parola = flag_uretici.parola_uret(basamak=10 ** 7)
        self.assertLess(time.time() - bas, 1)
        self.assertEqual(len(parola.lstrip("abcdefghijklmnopqrstuvwxyz")), flag_uretici.MAKS_BASAMAK)
        for bozuk in ("3", None, 2.5, True, [3]):
            self.assertEqual(len(flag_uretici.parola_uret(basamak=bozuk).lstrip("abcdefghijklmnopqrstuvwxyz")), 4)

    def test_dusmanca_parametrelerle_gorev_baslar_ve_sinirli_kalir(self):
        dusmanca = {"gurultu": 10 ** 9, "kodlama": ["x"], "gizli_port_araligi": [1, 5], "gurultu_sayisi": 10 ** 9,
                    "tuzak_tablolar": "çok", "basamak": 10 ** 9, "gerekli_giris": "x", "hizmetler": 7,
                    "tuzak_port_araligi": "abc"}
        self.ist.ozel_parametreler = ogrenci_istemci.parametreleri_temizle(dusmanca)
        self.ist.gorevi_yukle("tshark-01")
        self.ist.gorevi_baslat()
        self.assertLessEqual(self.ist._servis.gurultu, 16)
        self.assertEqual(self.ist._servis.kodlama, "duz")
        self.ist.gorevi_durdur()
        self.ist.gorevi_yukle("nmap-01")
        self.ist.gorevi_baslat()
        self.assertLessEqual(len(self.ist._servis.gurultu_portlari), 12)
        self.assertTrue(1024 <= self.ist._servis.gizli_port <= 65535)
        self.assertEqual(self.ist.aralik_metni(), "")                # bozuk aralik metne dokulmez, cokertmez
        self.ist.gorevi_durdur()
        self.ist.gorevi_yukle("sqlmap-01")
        self.ist.gorevi_baslat()
        self.assertEqual(self.ist._servis.tuzak_tablolar, 0)
        self.ist.gorevi_durdur()
        self.ist.tuzak_kullanici = "ziyaretci"
        self.assertEqual(self.ist.metin_degiskenleri()["{tuzaklar}"], "")


class P13CevapKutusuOlmayanGorev(BireyselTabani):
    """P-13: dogru cevabi olmayan gorevde 'None' ya da onceki gorevin cevabi dogru sayiliyordu."""

    def test_cevap_yokken_hicbir_metin_dogru_degil(self):
        for metin in ("None", "", "none", " None "):
            self.assertFalse(self.ist.cevabi_kontrol_et(metin))

    def test_onceki_gorevin_cevabi_tasinmaz(self):
        self.ist.gorevi_yukle("nmap-01")
        self.ist.gorevi_baslat()
        eski = self.ist._dogru_cevap
        self.assertTrue(self.ist.cevabi_kontrol_et(eski))
        self.ist.gorevi_durdur()
        self.ist.gorevi_yukle("ufw-01")
        self.ist.gorevi_baslat()
        self.assertIsNone(self.ist._dogru_cevap)
        for metin in (eski, "None"):
            self.assertFalse(self.ist.cevabi_kontrol_et(metin))


if __name__ == "__main__":
    unittest.main()
