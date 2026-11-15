#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Kurtarma: carotos-kurtarma-yonet (root yardimcisi) testleri.

euid=0 sarti ve gercek calistir()/subprocess yerine motor fonksiyonlarini
sahteleyerek dispatch/dogrulama mantigini sinar; hicbir ayricalikli komut
GERCEKTEN calistirilmaz.

Calistirma (depo kokunden):  python3 tests/test_kurtarma_yonet.py
"""
import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KT = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "kurtarma")
YONET = os.path.join(KT, "carotos-kurtarma-yonet")


def yonet_yukle():
    import importlib.machinery
    # YONET uzantisiz bir dosya: spec_from_file_location turunu cikaramaz,
    # bu yuzden yukleyici dogrudan verilir (carotpot-yonet testiyle ayni desen).
    yukleyici = importlib.machinery.SourceFileLoader("carotos_kurtarma_yonet", YONET)
    spec = importlib.util.spec_from_loader(yukleyici.name, yukleyici)
    mod = importlib.util.module_from_spec(spec)
    yukleyici.exec_module(mod)
    return mod


class Taban(unittest.TestCase):
    def setUp(self):
        self.Y = yonet_yukle()
        self.Y.os.geteuid = lambda: 0   # testler root-disi calisiyor olabilir

    def calistir(self, argv, girdi_metni=None):
        cikti = io.StringIO()
        eski_stdin = sys.stdin
        if girdi_metni is not None:
            sys.stdin = io.StringIO(girdi_metni)
        try:
            with redirect_stdout(cikti):
                try:
                    self.Y.main(argv)
                except SystemExit:
                    pass
        finally:
            sys.stdin = eski_stdin
        satirlar = [s for s in cikti.getvalue().splitlines() if s.strip()]
        return json.loads(satirlar[-1]) if satirlar else None


class YetkiKontrolu(unittest.TestCase):
    def test_root_degilse_her_komut_reddedilir(self):
        Y = yonet_yukle()
        Y.os.geteuid = lambda: 1000
        cikti = io.StringIO()
        with redirect_stdout(cikti):
            with self.assertRaises(SystemExit):
                Y.main(["liste"])
        self.assertEqual(json.loads(cikti.getvalue().strip())["kod"], "__YETKI_YOK__")


class KomutDispatch(Taban):
    def test_bos_argv_gecersiz(self):
        self.assertEqual(self.calistir([])["kod"], "__GECERSIZ_KOMUT__")

    def test_bilinmeyen_komut(self):
        self.assertEqual(self.calistir(["boyle-bir-komut-yok"])["kod"], "__GECERSIZ_KOMUT__")

    def test_liste_motoru_cagirir(self):
        cagrildi = []
        self.Y.K.noktalari_listele = lambda: cagrildi.append(1) or [{"id": "x"}]
        sonuc = self.calistir(["liste"])
        self.assertEqual(sonuc, {"kod": "__TAMAM__", "noktalar": [{"id": "x"}]})
        self.assertEqual(cagrildi, [1])

    def test_olustur_etiketsiz(self):
        gorulen = {}

        def sahte_olustur(calistir, etiket=None, tetikleyici="elle"):
            gorulen["etiket"] = etiket
            gorulen["tetikleyici"] = tetikleyici
            return {"nokta": {"id": "20260101-000000"}, "silinen": []}

        self.Y.K.nokta_olustur = sahte_olustur
        sonuc = self.calistir(["olustur"])
        self.assertEqual(sonuc["kod"], "__TAMAM__")
        self.assertIsNone(gorulen["etiket"])
        self.assertEqual(gorulen["tetikleyici"], "elle")

    def test_olustur_etiketli(self):
        gorulen = {}
        self.Y.K.nokta_olustur = lambda calistir, etiket=None, tetikleyici="elle": (
            gorulen.__setitem__("etiket", etiket) or {"nokta": {}, "silinen": []})
        self.calistir(["olustur", "--etiket", "Güncelleme öncesi"])
        self.assertEqual(gorulen["etiket"], "Güncelleme öncesi")

    def test_olustur_hata_kodu_iletilir(self):
        def patlar(calistir, etiket=None, tetikleyici="elle"):
            raise self.Y.K.KurtarmaHatasi("gecersiz_etiket")

        self.Y.K.nokta_olustur = patlar
        sonuc = self.calistir(["olustur", "--etiket", "x"])
        self.assertEqual(sonuc["kod"], "gecersiz_etiket")

    def test_oto_guncelleme_oncesi_her_zaman_tamam(self):
        self.Y.K.oto_guncelleme_oncesi = lambda calistir: {"atlandi": "kapali"}
        sonuc = self.calistir(["oto-guncelleme-oncesi"])
        self.assertEqual(sonuc["kod"], "__TAMAM__")
        self.assertEqual(sonuc["atlandi"], "kapali")

    def test_geri_yukle_id_gerekir(self):
        self.assertEqual(self.calistir(["geri-yukle"])["kod"], "__GECERSIZ_KOMUT__")

    def test_geri_yukle_paket_bayragi_algilanir(self):
        gorulen = {}
        self.Y.K.nokta_geri_yukle = lambda calistir, nid, paketleri_de_kur=False: (
            gorulen.__setitem__("p", (nid, paketleri_de_kur)) or {"parcalar": {}})
        self.calistir(["geri-yukle", "20260101-000000", "--paketler"])
        self.assertEqual(gorulen["p"], ("20260101-000000", True))
        self.calistir(["geri-yukle", "20260101-000000"])
        self.assertEqual(gorulen["p"], ("20260101-000000", False))

    def test_sil_id_gerekir(self):
        self.assertEqual(self.calistir(["sil"])["kod"], "__GECERSIZ_KOMUT__")

    def test_sil_motoru_cagirir(self):
        gorulen = []
        self.Y.K.nokta_sil = lambda nid: gorulen.append(nid)
        sonuc = self.calistir(["sil", "20260101-000000"])
        self.assertEqual(sonuc["kod"], "__TAMAM__")
        self.assertEqual(gorulen, ["20260101-000000"])

    def test_ayar_yaz_gecerli_json(self):
        gorulen = {}
        self.Y.K.ayarlari_yaz = lambda ayar: gorulen.setdefault("ayar", ayar) or dict(ayar)
        sonuc = self.calistir(["ayar-yaz"], girdi_metni='{"sakla": 3}')
        self.assertEqual(sonuc["kod"], "__TAMAM__")
        self.assertEqual(gorulen["ayar"], {"sakla": 3})

    def test_ayar_yaz_gecersiz_json_reddedilir(self):
        sonuc = self.calistir(["ayar-yaz"], girdi_metni="{bozuk")
        self.assertEqual(sonuc["kod"], "__GECERSIZ_AYAR__")

    def test_ayar_yaz_liste_reddedilir(self):
        sonuc = self.calistir(["ayar-yaz"], girdi_metni="[1, 2]")
        self.assertEqual(sonuc["kod"], "__GECERSIZ_AYAR__")


class SabitKaynaklar(unittest.TestCase):
    """Betik, dosya yolu guvenligi kuralini (ortak/yetkili.py) gercekten kullaniyor mu?"""

    def test_calistir_sistem_disindaki_adi_reddeder(self):
        Y = yonet_yukle()
        kod, cikti = Y.calistir(["boyle-bir-sistem-komutu-yok-kesinlikle"])
        self.assertEqual(kod, 127)

    def test_calistir_mutlak_yolu_oldugu_gibi_kullanir(self):
        Y = yonet_yukle()
        kod, cikti = Y.calistir(["/boyle/bir/yol/da/yok"])
        self.assertEqual(kod, 127)

    def test_dosya_root_olarak_calistirilabilir_ve_kabuk_yok(self):
        icerik = open(YONET, encoding="utf-8").read()
        self.assertIn("os.geteuid() != 0", icerik)
        self.assertNotIn("shell=True", icerik)
        self.assertNotIn("os.system(", icerik)


if __name__ == "__main__":
    unittest.main(verbosity=1)
