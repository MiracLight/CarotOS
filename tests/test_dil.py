#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ortak/dil.py testleri (GTK gerektirmez).

Dil secimi, yedek zinciri (dil -> en -> tr), bozuk ceviri korumasi, dil
dosyasi yukleme ve {"tr","en"} sozluklerini zenginlestirme.

Calistirma (depo kokunden):  python3 tests/test_dil.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "ortak"))

import dil  # noqa: E402


class DilTabani(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.gecici, True)
        self.eski = dil.DIZIN
        dil.DIZIN = self.gecici
        dil.onbellegi_temizle()
        self.addCleanup(self._geri)

    def _geri(self):
        dil.DIZIN = self.eski
        dil.onbellegi_temizle()

    def dosya(self, kod, metinler, etkin=True, durum="taslak"):
        with open(os.path.join(self.gecici, kod + ".json"), "w", encoding="utf-8") as f:
            json.dump({"_meta": {"ad": kod, "etkin": etkin, "durum": durum}, "metinler": metinler}, f)
        dil.onbellegi_temizle()


class TanimTesti(unittest.TestCase):
    def test_dokuz_dil_dogru_sirada(self):
        self.assertEqual(dil.KODLAR, ("tr", "en", "de", "ru", "es", "pt", "ja", "zh", "fr"))
        self.assertEqual(len(set(dil.KODLAR)), 9)
        self.assertEqual(dict(dil.DILLER)["es"], "Español")

    def test_gecerli(self):
        self.assertEqual(dil.gecerli("de"), "de")
        self.assertEqual(dil.gecerli("it"), "en")
        self.assertEqual(dil.gecerli(None), "en")
        self.assertEqual(dil.gecerli("xx", "tr"), "tr")


class VarsayilanDilTesti(DilTabani):
    def test_kaynak_diller_her_zaman(self):
        self.assertEqual(dil.varsayilan_dil({"LANG": "tr_TR.UTF-8"}), "tr")
        self.assertEqual(dil.varsayilan_dil({"LANG": "en_US.UTF-8"}), "en")

    def test_etkin_olmayan_dil_ingilizceye_duser(self):
        # Almanca dosyasi yokken Almanca sistem dili Ingilizce acar
        self.assertEqual(dil.varsayilan_dil({"LANG": "de_DE.UTF-8"}), "en")

    def test_etkin_dil_secilir(self):
        self.dosya("de", {"Run": "Ausführen"})
        self.assertEqual(dil.varsayilan_dil({"LANG": "de_DE.UTF-8"}), "de")
        self.assertEqual(dil.varsayilan_dil({"LANG": "de_AT@euro"}), "de")

    def test_c_posix_atlanir(self):
        self.assertEqual(dil.varsayilan_dil({"LC_ALL": "C", "LANG": "tr_TR.UTF-8"}), "tr")
        self.assertEqual(dil.varsayilan_dil({"LC_ALL": "POSIX", "LANG": "C"}), "en")
        self.assertEqual(dil.varsayilan_dil({}), "en")

    def test_language_listesi(self):
        self.dosya("de", {"Run": "Ausführen"})
        self.assertEqual(dil.varsayilan_dil({"LANGUAGE": "it:de:en"}), "de")
        self.assertEqual(dil.varsayilan_dil({"LANGUAGE": "it:fr"}), "en")

    def test_desteklenmeyen_dil_ve_cince_varyantlari(self):
        self.assertEqual(dil.varsayilan_dil({"LANG": "it_IT.UTF-8"}), "en")
        self.dosya("zh", {"Run": "运行"})
        for v in ("zh_CN.UTF-8", "zh_TW.UTF-8", "zh-Hans"):
            self.assertEqual(dil.varsayilan_dil({"LANG": v}), "zh", v)

    def test_ilk_dolu_degisken_karar_verir(self):
        # LC_ALL=it (desteklenmiyor) -> LANG=tr'ye bakilmaz
        self.assertEqual(dil.varsayilan_dil({"LC_ALL": "it_IT.UTF-8", "LANG": "tr_TR.UTF-8"}), "en")


class EtkinDillerTesti(DilTabani):
    def test_dosya_yokken_yalniz_tr_en(self):
        self.assertEqual([k for k, _, _ in dil.etkin_diller()], ["tr", "en"])

    def test_etkin_dosyali_dil_listeye_girer_sirayi_korur(self):
        self.dosya("fr", {"Run": "Lancer"})
        self.dosya("de", {"Run": "Ausführen"})
        self.assertEqual([k for k, _, _ in dil.etkin_diller()], ["tr", "en", "de", "fr"])

    def test_etkin_degil_ya_da_bos_dil_girmez(self):
        self.dosya("de", {"Run": "x"}, etkin=False)
        self.dosya("fr", {}, etkin=True)
        self.assertEqual([k for k, _, _ in dil.etkin_diller()], ["tr", "en"])

    def test_taslak_ve_gozden_gecirildi(self):
        self.dosya("de", {"Run": "x"}, durum="taslak")
        self.dosya("fr", {"Run": "x"}, durum="gozden-gecirildi")
        d = {k: t for k, _, t in dil.etkin_diller()}
        self.assertTrue(d["de"])
        self.assertFalse(d["fr"])
        self.assertFalse(d["tr"] or d["en"])
        self.assertEqual(dil.secici_adi("de", "Deutsch", True), "Deutsch (beta)")
        self.assertEqual(dil.secici_adi("fr", "Français", False), "Français")

    def test_bozuk_dosyalar_sessizce_yok_sayilir(self):
        with open(os.path.join(self.gecici, "de.json"), "w", encoding="utf-8") as f:
            f.write("{bozuk json")
        with open(os.path.join(self.gecici, "fr.json"), "w", encoding="utf-8") as f:
            f.write("[1, 2, 3]")
        with open(os.path.join(self.gecici, "es.json"), "w", encoding="utf-8") as f:
            json.dump({"_meta": {"etkin": True}, "metinler": {"a": 5, "b": "", "c": "  ", "d": "ok"}}, f)
        dil.onbellegi_temizle()
        self.assertEqual([k for k, _, _ in dil.etkin_diller()], ["tr", "en", "es"])
        self.assertEqual(dil.ceviri("d", "es"), "ok")
        self.assertIsNone(dil.ceviri("a", "es"))


class BaslikOkumaTesti(DilTabani):
    """etkin_diller() dosyalarin tamamini yuklememeli (her CarotOS uygulamasinda ~7 MB RAM)."""

    def test_etkin_diller_tam_yukleme_yapmaz(self):
        self.dosya("de", {"Run": "Ausführen"})
        self.dosya("fr", {"Run": "Lancer"})
        dil.onbellegi_temizle()
        self.assertEqual([k for k, _, _ in dil.etkin_diller()], ["tr", "en", "de", "fr"])
        self.assertEqual(dil._onbellek, {})                 # hicbir dilin metinleri bellege alinmadi
        self.assertEqual(dil.ceviri("Run", "de"), "Ausführen")   # kullanilan dil istenince yuklenir
        self.assertEqual(len(dil._onbellek), 1)

    def test_baslik_tam_yuklemeyle_ayni_sonucu_verir(self):
        for kod, icerik in (("de", {"A": "a"}), ("fr", {}), ("es", {"A": 5, "B": ""}), ("pt", {"A": "", "B": "ok"}),
                            ("ru", {"A": "x"})):
            self.dosya(kod, icerik, etkin=(kod != "ru"))
        for kod in ("de", "fr", "es", "pt", "ru"):
            dil.onbellegi_temizle()
            tam = dil._dosya(kod)
            dil.onbellegi_temizle()
            self.assertEqual(dil._baslik(kod), (tam["meta"], bool(tam["metinler"])), kod)

    def test_beklenmeyen_bicimlerde_eski_davranis(self):
        yollar = {
            "de": '{"metinler": {"A": "a"}, "_meta": {"etkin": true}}',                    # sira ters
            "fr": '{"_meta":{"etkin":true},"metinler":{"A":"a"}}',                          # sikistirilmis
            "es": '{ "_meta" : { "etkin" : true } , "metinler" : { "A" : "a" } }',          # bosluklu
            "pt": '{"_meta": {"etkin": true}, "metinler": {"A": 5, "B": "ok"}}',           # ilk cift gecersiz
        }
        for kod, govde in yollar.items():
            with open(os.path.join(self.gecici, kod + ".json"), "w", encoding="utf-8") as f:
                f.write(govde)
        dil.onbellegi_temizle()
        self.assertEqual([k for k, _, _ in dil.etkin_diller()], ["tr", "en", "de", "es", "pt", "fr"])      # DILLER sirasi

    def test_buyuk_baslik_tam_yuklemeye_duser(self):
        meta = {"etkin": True, "not": "x" * 6000}
        with open(os.path.join(self.gecici, "de.json"), "w", encoding="utf-8") as f:
            json.dump({"_meta": meta, "metinler": {"A": "a"}}, f)
        dil.onbellegi_temizle()
        self.assertEqual([k for k, _, _ in dil.etkin_diller()], ["tr", "en", "de"])

    def test_gercek_dil_dosyalari_ayni_listeyi_verir(self):
        dil.DIZIN = self.eski                                # gercek ortak/diller klasoru (sonra setUp geri alir)
        dil.onbellegi_temizle()
        hizli = dil.etkin_diller()
        self.assertEqual(dil._onbellek, {})
        dil.onbellegi_temizle()
        tam = []
        for kod, ad in dil.DILLER:
            if kod in dil.KAYNAK_DILLER:
                tam.append((kod, ad, False))
                continue
            d = dil._dosya(kod)
            if d["meta"].get("etkin") is True and d["metinler"]:
                tam.append((kod, ad, d["meta"].get("durum", "taslak") != "gozden-gecirildi"))
        self.assertEqual(hizli, tam)


class MetinTesti(DilTabani):
    def test_dogrudan_ve_kaynak_diller(self):
        s = {"tr": "Çalıştır", "en": "Run"}
        self.assertEqual(dil.metin(s, "tr"), "Çalıştır")
        self.assertEqual(dil.metin(s, "en"), "Run")

    def test_yedek_zinciri(self):
        s = {"tr": "Çalıştır", "en": "Run"}
        self.assertEqual(dil.metin(s, "de"), "Run")                  # ceviri yok -> en
        self.assertEqual(dil.metin({"tr": "Merhaba"}, "de"), "Merhaba")   # en da yok -> tr
        self.assertEqual(dil.metin({"tr": "", "en": ""}, "de", "anahtar"), "anahtar")
        self.assertEqual(dil.metin(None, "de", "anahtar"), "anahtar")
        self.assertEqual(dil.metin("duz metin", "de"), "duz metin")

    def test_ceviri_dosyadan_gelir_ingilizce_anahtarla(self):
        self.dosya("de", {"Run": "Ausführen"})
        self.assertEqual(dil.metin({"tr": "Çalıştır", "en": "Run"}, "de"), "Ausführen")
        # ayni Ingilizce metin baska bir sozlukte de ayni ceviriyi kullanir
        self.assertEqual(dil.metin({"tr": "Koş", "en": "Run"}, "de"), "Ausführen")
        # sozlukte dogrudan yazili dil dosyadakini ezer
        self.assertEqual(dil.metin({"tr": "x", "en": "Run", "de": "Los"}, "de"), "Los")

    def test_baska_dilin_cevirisi_sizmaz(self):
        self.dosya("de", {"Run": "Ausführen"})
        self.assertEqual(dil.metin({"tr": "Çalıştır", "en": "Run"}, "fr"), "Run")

    def test_metin_sinifi_keyerror_atmaz(self):
        self.dosya("de", {"Run": "Ausführen"})
        m = dil.Metin({"tr": "Çalıştır", "en": "Run"})
        self.assertEqual(m["de"], "Ausführen")
        self.assertEqual(m["ja"], "Run")
        self.assertEqual(m["tr"], "Çalıştır")
        self.assertEqual(m, {"tr": "Çalıştır", "en": "Run"})
        self.assertEqual(json.loads(json.dumps(m)), {"tr": "Çalıştır", "en": "Run"})


class SablonTesti(DilTabani):
    def test_yer_tutucu_doldurulur(self):
        s = {"tr": "{tool} çalışıyor…", "en": "{tool} running…"}
        self.assertEqual(dil.T(s, "en", tool="nmap"), "nmap running…")
        self.assertEqual(dil.T(s, "tr", tool="nmap"), "nmap çalışıyor…")

    def test_bozuk_ceviri_cokertmez_ingilizceye_duser(self):
        self.dosya("de", {"{tool} running…": "{werkzeug} läuft…"})   # yer tutucu cevrilmis: hata
        s = {"tr": "{tool} çalışıyor…", "en": "{tool} running…"}
        self.assertEqual(dil.T(s, "de", tool="nmap"), "nmap running…")

    def test_sagliklı_ceviri_kullanilir(self):
        self.dosya("de", {"{tool} running…": "{tool} läuft…"})
        s = {"tr": "{tool} çalışıyor…", "en": "{tool} running…"}
        self.assertEqual(dil.T(s, "de", tool="nmap"), "nmap läuft…")

    def test_kw_yoksa_metin_oldugu_gibi(self):
        self.assertEqual(dil.T({"tr": "a {x}", "en": "a {x}"}, "en"), "a {x}")

    def test_yer_tutucular(self):
        self.assertEqual(dil.yer_tutucular("{a} ve {b} ve {a}"), {"a", "b"})
        self.assertEqual(dil.yer_tutucular("yok"), set())
        self.assertEqual(dil.yer_tutucular("{}"), {""})


class ZenginlestirTesti(DilTabani):
    def test_ic_ice_yapi(self):
        self.dosya("de", {"Run": "Ausführen"})
        kaynak = {
            "run": {"tr": "Çalıştır", "en": "Run"},
            "liste": [({"tr": "a", "en": "b"}, 5), {"tr": "Çalıştır", "en": "Run"}],
            "build": lambda v: v,
            "sayi": 3,
            "diger": {"adi": "x", "tr": "y"},          # "en" yok -> iki dilli degil
        }
        z = dil.zenginlestir(kaynak)
        self.assertIsInstance(z["run"], dil.Metin)
        self.assertEqual(z["run"]["de"], "Ausführen")
        self.assertIsInstance(z["liste"][0][0], dil.Metin)
        self.assertIsInstance(z["liste"][1], dil.Metin)
        self.assertIsInstance(z["liste"][0], tuple)
        self.assertIs(z["build"], kaynak["build"])
        self.assertEqual(z["sayi"], 3)
        self.assertNotIsInstance(z["diger"], dil.Metin)
        self.assertNotIsInstance(kaynak["run"], dil.Metin)     # girdi degismedi

    def test_degerleri_metin_olmayan_sozluk_donusmez(self):
        z = dil.zenginlestir({"tr": ["a"], "en": ["b"]})
        self.assertNotIsInstance(z, dil.Metin)
        self.assertIsInstance(z["tr"], list)


class DilOnceTesti(DilTabani):
    """Poligon gibi dil-once (METIN[kod][anahtar]) tablolar."""

    TABLO = {"tr": {"a": "Merhaba {ad}", "b": "Yalniz TR", "liste": ["x", "y"]},
             "en": {"a": "Hello {ad}", "liste": ["x", "y"]}}

    def test_kaynak_diller_ve_yedek(self):
        m = dil.dil_once(self.TABLO)
        self.assertEqual(m["tr"]["a"], "Merhaba {ad}")
        self.assertEqual(m["en"]["a"], "Hello {ad}")
        self.assertEqual(m["en"]["b"], "Yalniz TR")          # en yok -> tr
        self.assertEqual(m["de"]["a"], "Hello {ad}")         # dil dosyasi yok -> en

    def test_ceviri_dosyasi_kullanilir(self):
        self.dosya("de", {"Hello {ad}": "Hallo {ad}"})
        m = dil.dil_once(self.TABLO)
        self.assertEqual(m["de"]["a"], "Hallo {ad}")
        self.assertEqual(m["de"]["b"], "Yalniz TR")

    def test_bilinmeyen_anahtar_keyerror(self):
        m = dil.dil_once(self.TABLO)
        for kod in ("tr", "de"):
            with self.assertRaises(KeyError):
                m[kod]["yok"]
        self.assertIsNone(m["de"].get("yok"))
        self.assertEqual(m["de"].get("yok", 1), 1)

    def test_liste_degerleri_oldugu_gibi(self):
        m = dil.dil_once(self.TABLO)
        self.assertEqual(m["tr"]["liste"], ["x", "y"])
        self.assertEqual(m["de"]["liste"], ["x", "y"])

    def test_icerme_ve_anahtarlar(self):
        m = dil.dil_once(self.TABLO)
        self.assertIn("b", m["de"])
        self.assertNotIn("yok", m["de"])
        self.assertEqual(m["de"].keys(), {"a", "b", "liste"})


class YaziTipiTesti(DilTabani):
    """Yazi tipi yoksa 日本語/中文 kutucuk (tofu) olmasin: Latin ad gosterilir."""

    def setUp(self):
        super().setUp()
        self._eski = dict(dil._yazi_onbellek)
        self.addCleanup(lambda: (dil._yazi_onbellek.clear(), dil._yazi_onbellek.update(self._eski)))

    def test_yazi_tipi_varsa_kendi_adi(self):
        dil._yazi_onbellek.update({"ja": True, "zh": True})
        self.assertEqual(dil.secici_adi("ja", "日本語", True), "日本語 (beta)")
        self.assertEqual(dil.gorunen_ad("zh", "中文"), "中文")

    def test_yazi_tipi_yoksa_latin_ad(self):
        dil._yazi_onbellek.update({"ja": False, "zh": False})
        self.assertEqual(dil.secici_adi("ja", "日本語", True), "Japanese (beta)")
        self.assertEqual(dil.secici_adi("zh", "中文", False), "Chinese")
        self.assertEqual(dil.gorunen_ad("ja", "日本語"), "Japanese")

    def test_latin_ve_kiril_diller_etkilenmez(self):
        dil._yazi_onbellek.update({"ja": False, "zh": False})
        for kod, ad in (("de", "Deutsch"), ("ru", "Русский"), ("es", "Español"), ("tr", "Türkçe")):
            self.assertEqual(dil.gorunen_ad(kod, ad), ad)

    def test_fc_list_yoksa_adi_degistirmez(self):
        from unittest import mock
        dil._yazi_onbellek.clear()
        with mock.patch("shutil.which", return_value=None):
            self.assertTrue(dil.yazi_tipi_var_mi("ja"))
        self.assertEqual(dil.gorunen_ad("ja", "日本語") if dil._yazi_onbellek.get("ja") else "x", "日本語")

    def test_fc_list_bos_cikarsa_yok_sayilir(self):
        from unittest import mock
        dil._yazi_onbellek.clear()
        sahte = mock.Mock(returncode=0, stdout="\n")
        with mock.patch("shutil.which", return_value="/usr/bin/fc-list"), mock.patch("subprocess.run", return_value=sahte):
            self.assertFalse(dil.yazi_tipi_var_mi("zh"))
        dil._yazi_onbellek.clear()
        sahte = mock.Mock(returncode=0, stdout="Noto Sans CJK JP\n")
        with mock.patch("shutil.which", return_value="/usr/bin/fc-list"), mock.patch("subprocess.run", return_value=sahte):
            self.assertTrue(dil.yazi_tipi_var_mi("zh"))


if __name__ == "__main__":
    unittest.main()
