#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon ortak dil katmanina bagli: METIN her dilde okunur, gorev/sablon verisi her dilde
[kod] ile okunur, ipucu/bilgi ingilizce dilde Turkce'ye dusmez (GTK gerekmez).

Calistirma:  python3 tests/test_poligon_dil.py
"""
import ast
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPT = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
POLIGON = os.path.join(OPT, "poligon")
for _y in (os.path.join(OPT, "ortak"), POLIGON):
    sys.path.insert(0, _y)

import dil_koprusu as DK  # noqa: E402
import gorev_bilgi as GB  # noqa: E402
import soru_sablonlari as SS  # noqa: E402
import varyantlar as VR  # noqa: E402


def metin_tablosu(dosya):
    with open(os.path.join(POLIGON, dosya), "rb") as f:
        agac = ast.parse(f.read().decode("utf-8"))
    for n in agac.body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "_METIN_HAM":
            return ast.literal_eval(n.value)
    raise AssertionError(dosya + ": _METIN_HAM yok")


class Dilli(unittest.TestCase):
    def setUp(self):
        if DK._dil is None:
            self.skipTest("ortak dil katmani yok")
        self._eski = DK._dil.DIZIN
        self.gecici = tempfile.mkdtemp(prefix="poligon-dil-")
        DK._dil.DIZIN = self.gecici
        DK._dil.onbellegi_temizle()
        self.addCleanup(self._geri)

    def _geri(self):
        DK._dil.DIZIN = self._eski
        DK._dil.onbellegi_temizle()

    def dosya(self, kod, metinler):
        with open(os.path.join(self.gecici, kod + ".json"), "w", encoding="utf-8") as f:
            json.dump({"_meta": {"etkin": True, "durum": "taslak"}, "metinler": metinler}, f, ensure_ascii=False)
        DK._dil.onbellegi_temizle()


class MetinTablolariTesti(Dilli):
    def test_iki_arayuzde_tr_en_anahtarlari_ayni(self):
        for dosya in ("ogrenci_uygulama.py", "ogretmen_uygulama.py"):
            with self.subTest(dosya=dosya):
                t = metin_tablosu(dosya)
                self.assertEqual(set(t["tr"]), set(t["en"]))
                self.assertIn("baslik", t["tr"])

    def test_yeni_anahtar_ogrenci_gorev_yok(self):
        t = metin_tablosu("ogrenci_uygulama.py")
        self.assertIn("hata_gorev_yok", t["tr"])
        self.assertIn("hata_gorev_yok", t["en"])

    def test_her_dilde_metin_okunur(self):
        for dosya in ("ogrenci_uygulama.py", "ogretmen_uygulama.py"):
            m = DK.dil_once(metin_tablosu(dosya))
            for kod in DK._dil.KODLAR:
                for anahtar in metin_tablosu(dosya)["tr"]:
                    deger = m[kod][anahtar]
                    self.assertTrue(deger not in (None, ""), (dosya, kod, anahtar))

    def test_ceviri_dosyasi_kullanilir_digerleri_ingilizce(self):
        t = metin_tablosu("ogrenci_uygulama.py")
        en_baslik = t["en"]["baslik"]
        self.dosya("es", {en_baslik: "Poligon CarotOS (es)"})
        m = DK.dil_once(t)
        self.assertEqual(m["es"]["baslik"], "Poligon CarotOS (es)")
        self.assertEqual(m["de"]["baslik"], en_baslik)          # de dosyasi yok -> en


class VeriTesti(Dilli):
    def test_sablon_basliklari_her_dilde(self):
        for gid, tanim in SS.SABLONLAR.items():
            for kod in DK._dil.KODLAR:
                self.assertTrue(tanim["baslik"][kod], (gid, kod))
                for alan in tanim["alanlar"]:
                    self.assertTrue(alan["etiket"][kod], (gid, kod))

    def test_ince_etiketler_ve_cesitlilik(self):
        for kod in DK._dil.KODLAR:
            self.assertTrue(GB.CESITLILIK_ETIKETI[kod])
            for alan in ("amac", "kazanim", "kullanim"):
                self.assertTrue(GB.ALAN_ETIKETLERI[kod][alan])

    def test_bilgi_getir_hicbir_dilde_tr_ye_kacmaz(self):
        gid = next(iter(GB.BILGI))
        en = GB.bilgi_getir(gid, "en")
        de = GB.bilgi_getir(gid, "de")
        self.assertEqual(de, en)                # ceviri yok -> Ingilizce (Turkce degil)
        self.assertNotEqual(de, GB.bilgi_getir(gid, "tr"))

    def test_bilgi_getir_ceviri_dosyasi(self):
        gid = next(iter(GB.BILGI))
        en = GB.BILGI[gid]["en"]
        self.dosya("de", {en["amac"]: "Zweck-Test"})
        de = GB.bilgi_getir(gid, "de")
        self.assertEqual(de["amac"], "Zweck-Test")
        self.assertEqual(de["kazanim"], en["kazanim"])

    def test_cesitlilik_ingilizce_degilse_bile_tr_degil(self):
        gid = next(iter(GB.BILGI))
        self.assertEqual(GB.cesitlilik_getir(gid, "de"), GB.cesitlilik_getir(gid, "en"))

    def test_varyant_metni_en_den_gelir(self):
        v = {"soru": {"tr": "Soru?", "en": "Question?"}}
        self.assertEqual(VR._metin(v, "soru", "de"), "Question?")
        self.assertEqual(VR._metin(v, "soru", "tr"), "Soru?")
        self.assertEqual(VR._metin(v, "yok", "de"), "")


class IstemciTesti(Dilli):
    def test_gorev_her_dilde_okunur_ve_ipucu_tr_ye_dusmez(self):
        import ogrenci_istemci as OI
        ist = OI.PoligonIstemci.__new__(OI.PoligonIstemci)
        ist.gorev = None
        gorev = ist.gorevi_yukle("sablon-ve-ornek")
        for kod in DK._dil.KODLAR:
            self.assertTrue(gorev["baslik"][kod])
        # ipucu sozlugu olan bir gorev: en yoksa degil, de icin Ingilizce gelmeli
        ist.gorev = {"zorluk_parametreleri": {}}
        ist._zorluk_parametreleri = lambda: {"ipucu": {"tr": "Turkce ipucu", "en": "English hint"}}
        self.assertEqual(ist.aktif_ipucu("de"), "English hint")
        self.assertEqual(ist.aktif_ipucu("tr"), "Turkce ipucu")

    def test_tuzak_mesajlari_her_dilde(self):
        import ogrenci_istemci as OI
        for kod in DK._dil.KODLAR:
            for anahtar in OI._TUZAK_MESAJ:
                self.assertTrue(DK.T(OI._TUZAK_MESAJ[anahtar], kod, ozet="X", kullanici="u"))


class KopruTesti(Dilli):
    def test_baslangic_dili(self):
        self.assertEqual(DK.baslangic_dili("de"), DK._dil.varsayilan_dil() if DK.gecerli_dil("de") else DK.baslangic_dili(None))
        self.dosya("de", {"Cancel": "Abbrechen"})
        self.assertEqual(DK.baslangic_dili("de"), "de")           # kayitli ve etkin
        self.assertIn(DK.baslangic_dili("xx"), ("tr", "en", "de"))  # gecersiz kayit yoksayilir

    def test_secici(self):
        self.assertEqual([k for k, _, _ in DK.etkin_diller()][:2], ["tr", "en"])
        self.assertEqual(DK.secici_adi("de", "Deutsch", True), "Deutsch (beta)")


if __name__ == "__main__":
    unittest.main()
