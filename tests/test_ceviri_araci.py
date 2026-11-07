#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ceviri.py testleri (GTK gerektirmez): kaynak taramasi, durum, eksik
parti, ekleme dogrulamasi (yer tutucu), kontrol ve dil dosyasi bicimi.

Calistirma (depo kokunden):  python3 tests/test_ceviri_araci.py
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "ceviri.py")


def yukle():
    spec = importlib.util.spec_from_file_location("ceviri_araci_test", ARAC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def calistir(mod, *argv):
    """(cikis_kodu, stdout_metni)"""
    cikti = io.StringIO()
    with contextlib.redirect_stdout(cikti):
        kod = mod.main(list(argv))
    return kod, cikti.getvalue()


ORNEK = '''
STRINGS = {
    "run": {"tr": "Çalıştır", "en": "Run"},
    "running": {"tr": "{tool} çalışıyor…", "en": "{tool} running…"},
    "dinamik": {"tr": "a" + "b", "en": f"x{1}"},
    "tek": {"tr": "Sadece Türkçe"},
}
ETIKET = T("Dosya seç", "Choose file")
BASKA = T("run", lang)
'''


class AracTabani(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.gecici, True)
        self.mod = yukle()
        self.mod.KOK = self.gecici
        uyg = os.path.join(self.gecici, *self.mod.UYG.split("/"))
        os.makedirs(os.path.join(uyg, "ornek"))
        os.makedirs(os.path.join(uyg, "ortak"))
        with open(os.path.join(uyg, "ornek", "uygulama.py"), "w", encoding="utf-8") as f:
            f.write(ORNEK)
        with open(os.path.join(uyg, "ortak", "dil.py"), "w", encoding="utf-8") as f:
            f.write('ORNEK = {"tr": "dil katmani", "en": "language layer"}\n')
        self.mod.DIZIN = os.path.join(uyg, "ortak", "diller")


class TaramaTesti(AracTabani):
    def test_duz_metinler_ve_T_cagrilari_bulunur(self):
        metinler, dinamik = self.mod.cikar()
        self.assertEqual(set(metinler), {"Run", "{tool} running…", "Choose file"})
        self.assertEqual(metinler["Run"]["tr"], {"Çalıştır"})

    def test_dinamik_ve_tek_dilli_sozlukler(self):
        _, dinamik = self.mod.cikar()
        self.assertEqual([d[0].endswith("ornek/uygulama.py") for d in dinamik], [True])  # f-string'li olan
        # {"tr": ...} yalniz Turkce olan sozluk ne metin ne dinamik sayilir
        self.assertEqual(len(dinamik), 1)

    def test_dil_katmaninin_kendi_ornekleri_sayilmaz(self):
        metinler, _ = self.mod.cikar()
        self.assertNotIn("language layer", metinler)

    def test_T_anahtar_cagrisi_metin_degil(self):
        metinler, _ = self.mod.cikar()          # T("run", lang): ikinci arguman duz metin degil
        self.assertNotIn("run", metinler)

    def test_poligon_json_gorev_paketleri_taranir(self):
        uyg = os.path.join(self.gecici, *self.mod.UYG.split("/"))
        for alt in ("gorevler", "ctf", "baska"):
            os.makedirs(os.path.join(uyg, "poligon", alt))
        paket = {"gorevler": [{"id": "x", "baslik": {"tr": "Başlık", "en": "Title"},
                               "ipuclari": [{"tr": "İpucu", "en": "Hint", "ceza": 5}],
                               "tek_dilli": {"tr": "Yalnız Türkçe"},
                               "dil_tablosu": {"tr": "Türkçe", "en": "English", "de": "Deutsch"}}]}
        for alt in ("gorevler", "ctf", "baska"):
            with open(os.path.join(uyg, "poligon", alt, "p.json"), "w", encoding="utf-8") as f:
                json.dump(paket, f)
        metinler, _ = self.mod.cikar()
        self.assertEqual(metinler["Title"]["tr"], {"Başlık"})
        self.assertEqual(metinler["Hint"]["tr"], {"İpucu"})
        self.assertEqual(metinler["Title"]["yer"] & {"config/includes.chroot/opt/carotos/poligon/gorevler/p.json",
                                                      "config/includes.chroot/opt/carotos/poligon/ctf/p.json"},
                         {"config/includes.chroot/opt/carotos/poligon/gorevler/p.json",
                          "config/includes.chroot/opt/carotos/poligon/ctf/p.json"})
        self.assertFalse(any("baska" in y for k in metinler.values() for y in k["yer"]))    # yalniz gorevler/ ve ctf/
        self.assertNotIn("English", metinler)            # baska dil kodu tasiyan tablo ceviri cifti degil
        self.assertNotIn("Yalnız Türkçe", [t for k in metinler.values() for t in k["tr"]])


class KomutlarTesti(AracTabani):
    def test_durum_kapsami(self):
        self.mod.yaz("es", {"ad": "Español", "etkin": False, "durum": "taslak"}, {"Run": "Ejecutar"})
        kod, cikti = calistir(self.mod, "durum")
        self.assertEqual(kod, 0)
        self.assertIn("Taranan benzersiz metin: 3", cikti)
        satir = [s for s in cikti.splitlines() if s.startswith("es ")][0]
        self.assertIn("33.3%", satir)

    def test_eksik_parti_kisadan_uzuna_ve_limit(self):
        self.mod.yaz("es", {"ad": "Español", "etkin": False, "durum": "taslak"}, {"Run": "Ejecutar"})
        kod, cikti = calistir(self.mod, "eksik", "es")
        liste = json.loads(cikti)
        self.assertEqual([x["en"] for x in liste], ["Choose file", "{tool} running…"])   # Run zaten ceviride
        self.assertEqual(liste[0]["tr"], "Dosya seç")
        kod, cikti = calistir(self.mod, "eksik", "es", "--limit", "1")
        self.assertEqual(len(json.loads(cikti)), 1)
        kod, cikti = calistir(self.mod, "eksik", "es", "--uygulama", "yok")
        self.assertEqual(json.loads(cikti), [])

    def test_ekle_dogru_ceviriyi_yazar_biçimi_sirali(self):
        parti = os.path.join(self.gecici, "parti.json")
        with open(parti, "w", encoding="utf-8") as f:
            json.dump({"{tool} running…": "{tool} se está ejecutando…", "Run": "Ejecutar"}, f)
        kod, cikti = calistir(self.mod, "ekle", "es", parti)
        self.assertEqual(kod, 0)
        with open(os.path.join(self.mod.DIZIN, "es.json"), encoding="utf-8") as f:
            ham = f.read()
        veri = json.loads(ham)
        self.assertEqual(veri["_meta"], {"ad": "Español", "etkin": False, "durum": "taslak"})
        self.assertEqual(list(veri["metinler"]), ["Run", "{tool} running…"])   # anahtara gore sirali
        self.assertIn("se está", ham)                                           # UTF-8, \u kacisi yok
        self.assertTrue(ham.endswith("\n"))

    def test_ekle_bozuk_yer_tutucuyu_ve_bilinmeyen_metni_reddeder(self):
        parti = os.path.join(self.gecici, "parti.json")
        with open(parti, "w", encoding="utf-8") as f:
            json.dump({"{tool} running…": "{herramienta} corriendo…",   # yer tutucu cevrilmis
                       "Run": "   ",                                     # bos
                       "Hic yok": "x"}, f)                                # kaynakta yok
        kod, cikti = calistir(self.mod, "ekle", "es", parti)
        self.assertEqual(kod, 1)
        self.assertIn("REDDEDILDI", cikti)
        self.assertIn("ATLANDI", cikti)
        with open(os.path.join(self.mod.DIZIN, "es.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["metinler"], {})

    def test_ekle_liste_bicimini_de_kabul_eder(self):
        parti = os.path.join(self.gecici, "parti.json")
        with open(parti, "w", encoding="utf-8") as f:
            json.dump([{"en": "Run", "ceviri": "Ejecutar"}], f)
        self.assertEqual(calistir(self.mod, "ekle", "es", parti)[0], 0)

    def test_gecersiz_dil_reddedilir(self):
        self.assertEqual(calistir(self.mod, "eksik", "en")[0], 2)

    def test_kontrol(self):
        self.assertEqual(calistir(self.mod, "kontrol")[0], 0)           # dosya yok: temiz
        self.mod.yaz("es", {"ad": "Español", "etkin": False, "durum": "taslak"},
                     {"{tool} running…": "{x} corriendo", "Eski metin": "viejo"})
        kod, cikti = calistir(self.mod, "kontrol")
        self.assertEqual(kod, 1)
        self.assertIn("yer tutucular farkli", cikti)
        self.assertIn("yetim", cikti)
        self.mod.yaz("es", {"ad": "Español", "etkin": True, "durum": "taslak"}, {})
        self.assertEqual(calistir(self.mod, "kontrol")[0], 1)           # etkin ama bos


class DepoTesti(unittest.TestCase):
    def test_gercek_depo_taranir_ve_temiz(self):
        mod = yukle()
        metinler, dinamik = mod.cikar()
        self.assertGreater(len(metinler), 1500)
        self.assertIn("Run", metinler)                                   # Guvenlik Paneli
        self.assertEqual(calistir(mod, "kontrol")[0], 0)

    def test_depodaki_dil_dosyalari_gecerli(self):
        mod = yukle()
        for kod in mod.CEVRILEN:
            yol, meta, dosya = mod.dil_dosyasi(kod)
            for en, ceviri in dosya.items():
                self.assertEqual(mod.dogrula(en, ceviri), [], (kod, en))


if __name__ == "__main__":
    unittest.main()
