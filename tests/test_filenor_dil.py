#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filenor ortak dil katmanina bagli (GTK'siz): her dilde metin okunur, hic KeyError cikmaz,
ceviri dosyasi varsa kullanilir, bozuk ceviri Ingilizceye duser.

Calistirma:  python3 tests/test_filenor_dil.py
"""
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filenor_yollar as Y  # noqa: E402,F401

import filenor_araclar as A  # noqa: E402
import filenor_dil as D  # noqa: E402
from filenor_metin import METIN  # noqa: E402


def dil_dosyasi_ac(kod, metinler, etkin=True):
    """Gecici bir diller/ klasoru kurar ve ortak dil katmanini ona yonlendirir."""
    dizin = tempfile.mkdtemp(prefix="filenor-dil-")
    with open(os.path.join(dizin, kod + ".json"), "w", encoding="utf-8") as f:
        json.dump({"_meta": {"etkin": etkin, "durum": "taslak"}, "metinler": metinler}, f, ensure_ascii=False)
    D._dil.DIZIN = dizin
    D._dil.onbellegi_temizle()
    return dizin


class DilKatmaniTesti(unittest.TestCase):
    def setUp(self):
        if D._dil is None:
            self.skipTest("ortak dil katmani yok (Filenor tek basina)")
        self._eski = D._dil.DIZIN
        self.addCleanup(self._geri)
        # Gercek ceviri dosyalari artik dolu: yedek-zinciri testleri bos bir diller/ klasoruyle calisir
        D._dil.DIZIN = tempfile.mkdtemp(prefix="filenor-dil-bos-")
        D._dil.onbellegi_temizle()

    def _geri(self):
        D._dil.DIZIN = self._eski
        D._dil.onbellegi_temizle()

    def test_bagli(self):
        self.assertTrue(hasattr(D._dil, "zenginlestir"))

    def test_araclar_her_dilde_okunur(self):
        for kod in D._dil.KODLAR:
            for ad, tanim in A.ARACLAR.items():
                self.assertTrue(tanim["ad"][kod], (ad, kod))
                self.assertTrue(tanim["ac"][kod], (ad, kod))

    def test_arayuz_metni_diger_dilde_ingilizceye_duser(self):
        self.assertEqual(D.sec(METIN["dosya_ekle"], "de"), METIN["dosya_ekle"]["en"])

    def test_ceviri_dosyasi_kullanilir(self):
        dil_dosyasi_ac("es", {"Add files": "Añadir archivos", "Cancelled": "Cancelado"})
        self.assertEqual(D.sec(METIN["dosya_ekle"], "es"), "Añadir archivos")
        self.assertEqual(D.hata_metni(D.FilenorHata("iptal"), "es"), "Cancelado")
        # cevirisi olmayan metin Ingilizce kalir
        self.assertEqual(D.sec(METIN["klasor_ekle"], "es"), METIN["klasor_ekle"]["en"])

    def test_bozuk_yer_tutucu_ingilizceye_duser(self):
        dil_dosyasi_ac("es", {"File not found: {yol}": "Archivo no encontrado: {ruta}"})
        metin = D.hata_metni(D.FilenorHata("dosya_yok", yol="/x/y"), "es")
        self.assertEqual(metin, "File not found: /x/y")

    @unittest.skipIf(os.name == "nt", "Windows'ta ipucu winget yonergesidir")
    def test_ipucu_bilinmeyen_dilde_ingilizce(self):
        self.assertEqual(D.ipucu_al("ffmpeg", "ja"), "Install: sudo apt install ffmpeg")
        self.assertEqual(D.ipucu_al("ffmpeg", "tr"), "Kurulum: sudo apt install ffmpeg")

    def test_winget_ipucu_sozlugu_her_dilde(self):
        self.assertIn("winget install X", D.T(D._WINGET_IPUCU, "de", k="X"))
        self.assertIn("winget install X", D.T(D._WINGET_IPUCU, "tr", k="X"))

    def test_etkin_dil_yokken_secici_tr_en(self):
        dizin = tempfile.mkdtemp(prefix="filenor-dil-bos-")
        D._dil.DIZIN = dizin
        D._dil.onbellegi_temizle()
        self.assertEqual([k for k, _, _ in D.etkin_diller()], ["tr", "en"])
        self.assertIsNone(D.gecerli_dil("es"))
        self.assertEqual(D.gecerli_dil("tr"), "tr")

    def test_etkin_dil_secicide(self):
        dil_dosyasi_ac("es", {"Cancelled": "Cancelado"})
        self.assertIn("es", [k for k, _, _ in D.etkin_diller()])
        self.assertEqual(D.gecerli_dil("es"), "es")


class MesajTestleri(unittest.TestCase):
    def test_tum_hata_kodlari_tr_en_ve_yer_tutucu_eslesir(self):
        import re
        for kod, kayit in D.MESAJ.items():
            with self.subTest(kod=kod):
                tr = set(re.findall(r"\{(\w+)\}", kayit["tr"]))
                en = set(re.findall(r"\{(\w+)\}", kayit["en"]))
                self.assertEqual(tr, en)


if __name__ == "__main__":
    unittest.main()
