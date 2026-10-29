#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon: gorevler/ klasorundeki uretec gorevlerinin hepsi, her zorlukta
istemci uzerinden baslatilir; metinlerde doldurulmamis yer tutucu kalmadigi,
dogru cevabin kabul edildigi ve temizligin yapildigi dogrulanir (GTK'siz).

Kullanim (depo kokunden):  python3 tests/test_poligon_gorevler_tum.py
"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot/opt/carotos")
GOREVLER = Path(INC) / "poligon" / "gorevler"
for _y in (os.path.join(INC, "poligon"), os.path.join(INC, "carotpot"),
           os.path.join(INC, "ortak")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import gecmis_defteri  # noqa: E402
import gorev_dogrulayici  # noqa: E402
import ogrenci_istemci  # noqa: E402
import soru_sablonlari  # noqa: E402

BIREBIR_KALAN = {"http_code"}     # ipucunda gercek kabuk degiskeni olarak gecenler
KALAN = re.compile(r"\{([a-z_]+)\}")


def uretec_gorevleri():
    sonuc = []
    for yol in sorted(GOREVLER.glob("*.json")):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if veri.get("flag_uretimi", {}).get("yontem") == "uretec":
            sonuc.append(veri["id"])
    return sonuc


class TumUretecGorevleri(unittest.TestCase):
    def setUp(self):
        self._eski = gecmis_defteri.GECMIS_DOSYASI
        gecmis_defteri.GECMIS_DOSYASI = Path(tempfile.mkdtemp()) / "gecmis.json"

    def tearDown(self):
        gecmis_defteri.GECMIS_DOSYASI = self._eski

    def test_gorev_sayisi_ve_gecerlilik(self):
        self.assertGreaterEqual(len(uretec_gorevleri()), 12)
        for yol in GOREVLER.glob("*.json"):
            self.assertEqual(gorev_dogrulayici.dogrula(yol), [], yol.name)

    def test_her_gorev_her_zorluk(self):
        for gid in uretec_gorevleri():
            for zorluk in ("kolay", "orta", "zor"):
                with self.subTest(gorev=gid, zorluk=zorluk):
                    ist = ogrenci_istemci.PoligonIstemci("", "", "", "test")
                    ist.zorluk = zorluk
                    ist.gorevi_yukle(gid)
                    ist.gorevi_baslat()
                    try:
                        for dil in ("tr", "en"):
                            metin = ist.metni_doldur(ist.gorev["senaryo"][dil])
                            ipucu = ist.metni_doldur(
                                ist.aktif_ipucu(dil) or ist.gorev["ipucu"][dil])
                            for parca in (metin, ipucu):
                                kalan = set(KALAN.findall(parca)) - BIREBIR_KALAN
                                self.assertEqual(kalan, set(), f"{dil}: {parca[:120]}")
                        self.assertTrue(ist._dogru_cevap)
                        self.assertFalse(ist.cevabi_kontrol_et("yanlis-cevap"))
                        self.assertTrue(ist.cevabi_kontrol_et(f"  {ist._dogru_cevap} "))
                        yol = ist.dosya_yolu
                        if yol:
                            self.assertTrue(os.path.exists(yol))
                    finally:
                        ist.gorevi_durdur()
                    if yol:
                        self.assertFalse(os.path.exists(yol), "gecici dosya silinmeli")

    def test_john_ipucunda_gercek_dosya_yolu(self):
        ist = ogrenci_istemci.PoligonIstemci("", "", "", "test")
        ist.gorevi_yukle("john-01")
        ist.gorevi_baslat()
        try:
            ipucu = ist.metni_doldur(ist.gorev["ipucu"]["tr"])
            self.assertIn(ist.dosya_yolu, ipucu)
            self.assertNotIn("<dosya_yolu>", ipucu)
        finally:
            ist.gorevi_durdur()

    def test_durumlar_sizmaz(self):
        ist = ogrenci_istemci.PoligonIstemci("", "", "", "test")
        ist.gorevi_yukle("loganaliz-01")
        ist.gorevi_baslat()
        self.assertIn("{dosya}", ist.metin_degiskenleri())
        ist.gorevi_durdur()
        ist.gorevi_yukle("nmap-01")
        ist.gorevi_baslat()
        try:
            self.assertEqual(ist.metin_degiskenleri(), {})
        finally:
            ist.gorevi_durdur()


class SoruSablonlari(unittest.TestCase):
    def test_sablon_gorev_ve_alanlari_gecerli(self):
        for gid in soru_sablonlari.arac_listesi():
            self.assertTrue((GOREVLER / f"{gid}.json").is_file(), gid)
            for alan in soru_sablonlari.SABLONLAR[gid]["alanlar"]:
                varsayilan = soru_sablonlari.varsayilan(gid, alan["anahtar"])
                self.assertNotEqual(varsayilan, "", f"{gid}.{alan['anahtar']}")
            # varsayilan degerlerle parametre uretilebilmeli
            ham = {a["anahtar"]: soru_sablonlari.varsayilan(gid, a["anahtar"])
                   for a in soru_sablonlari.SABLONLAR[gid]["alanlar"]}
            soru_sablonlari.parametreleri_ayristir(gid, ham)

    def test_sablonlu_gorevler_ozel_parametreyle_calisir(self):
        for gid in soru_sablonlari.arac_listesi():
            with self.subTest(gorev=gid):
                ham = {a["anahtar"]: soru_sablonlari.varsayilan(gid, a["anahtar"])
                       for a in soru_sablonlari.SABLONLAR[gid]["alanlar"]}
                ist = ogrenci_istemci.PoligonIstemci("", "", "", "test")
                ist.ozel_parametreler = soru_sablonlari.parametreleri_ayristir(gid, ham)
                ist.gorevi_yukle(gid)
                ist.gorevi_baslat()
                try:
                    self.assertTrue(ist._dogru_cevap is not None or ist.tuzak_kullanici)
                finally:
                    ist.gorevi_durdur()

    def test_yeni_gorevler_sablonlu(self):
        beklenen = {"carotpot-01"} | set(uretec_gorevleri())
        self.assertLessEqual(beklenen - set(soru_sablonlari.arac_listesi()), set())

    def test_carotpot_hizmet_listesi(self):
        p = soru_sablonlari.parametreleri_ayristir(
            "carotpot-01", {"hizmetler": "ftp,telnet", "tuzak_port_araligi": "21000-21999",
                            "gerekli_giris": "2"})
        self.assertEqual(p["hizmetler"], ["ftp", "telnet"])
        self.assertIn("ftp,telnet", soru_sablonlari.etiket_uret("carotpot-01", p))
        with self.assertRaises(soru_sablonlari.GecersizDeger):
            soru_sablonlari.parametreleri_ayristir("carotpot-01", {"hizmetler": "ssh"})


if __name__ == "__main__":
    unittest.main()
