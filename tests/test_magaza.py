#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Magaza testleri (GTK gerektirmez): apt komutu ve metin sozlugu.

Magaza modulu en ustte gi/Gtk iceri aktardigi icin dogrudan import edilmez;
test, kaynagi ayristirip yalnizca ilgili islevleri / sozlugu cikarir.

Calistirma:  python3 tests/test_magaza.py
"""
import ast
import os
import shutil
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAGAZA = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "magaza")
KOD = os.path.join(MAGAZA, "carotos-magaza.py")


def kaynak_agaci():
    with open(KOD, "rb") as f:
        return ast.parse(f.read().decode("utf-8"))


def islevleri_yukle(*adlar):
    """Modulden yalnizca adi verilen islevleri, gi olmadan calistirilabilir yapar."""
    secilen = [n for n in kaynak_agaci().body
               if isinstance(n, ast.FunctionDef) and n.name in adlar]
    assert {n.name for n in secilen} == set(adlar), "islev bulunamadi"
    ad_alani = {"shutil": shutil}
    exec(compile(ast.Module(body=secilen, type_ignores=[]), KOD, "exec"), ad_alani)
    return ad_alani


def metin_sozlugu():
    for n in kaynak_agaci().body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "METIN" for t in n.targets):
            return ast.literal_eval(n.value)
    raise AssertionError("METIN bulunamadi")


class AptKomutuTesti(unittest.TestCase):
    def setUp(self):
        self.ad_alani = islevleri_yukle("_yetki", "apt_komutu")
        yama = mock.patch.object(shutil, "which", lambda ad: "/usr/bin/" + ad)
        yama.start()
        self.addCleanup(yama.stop)

    def test_yerel_ayar_c_olur(self):
        # Turkce yerelde rkhunter gibi paketlerin kurulum betigi dusuyordu
        for eylem in ("install", "remove", "upgrade"):
            with self.subTest(eylem=eylem):
                komut = self.ad_alani["apt_komutu"](eylem, "rkhunter")
                self.assertIn("LC_ALL=C", komut)
                self.assertIn("DEBIAN_FRONTEND=noninteractive", komut)

    def test_komut_pkexec_ile_baslar_ve_apt_get_cagirir(self):
        komut = self.ad_alani["apt_komutu"]("install", "nmap")
        self.assertEqual(komut[0], "/usr/bin/pkexec")
        self.assertIn("apt-get", komut)
        self.assertEqual(komut[komut.index("install") + 1:], ["-y", "nmap"])

    def test_birden_cok_paket_tek_komutta(self):
        komut = self.ad_alani["apt_komutu"]("install", "nmap", "rkhunter", "htop")
        self.assertEqual(komut[-3:], ["nmap", "rkhunter", "htop"])
        self.assertEqual(komut.count("apt-get"), 1)

    def test_pkexec_yoksa_none(self):
        with mock.patch.object(shutil, "which", lambda ad: None):
            self.assertIsNone(self.ad_alani["apt_komutu"]("install", "nmap"))


class SepetTesti(unittest.TestCase):
    """Birden fazla uygulama tek seferde kurulabilmeli (sepet)."""

    def setUp(self):
        with open(KOD, "rb") as f:
            self.kaynak = f.read().decode("utf-8")

    def test_sepet_metinleri_iki_dilde(self):
        sozluk = metin_sozlugu()
        for anahtar in ("sepete_ekle", "sepette", "sepeti_kur", "sepet_kuruluyor"):
            with self.subTest(anahtar=anahtar):
                self.assertIn(anahtar, sozluk)
        self.assertIn("{n}", sozluk["sepeti_kur"]["tr"])
        self.assertIn("{n}", sozluk["sepet_kuruluyor"]["en"])

    def test_sepet_tek_apt_komutuyla_kurulur(self):
        # Paketler ayri ayri degil, tek apt-get cagrisinda (tek parola istemi)
        sinif = next(n for n in kaynak_agaci().body
                     if isinstance(n, ast.ClassDef) and n.name == "MagazaPenceresi")
        yontem = next(n for n in sinif.body
                      if isinstance(n, ast.FunctionDef) and n.name == "sepeti_kur")
        govde = ast.get_source_segment(self.kaynak, yontem)
        self.assertIn('apt_komutu("install", *paketler)', govde)

    def test_sepet_basarisizlikta_gercek_durum_okunur(self):
        # Paketlerden biri dusse (ornegin kurulum betigi hatasi) digerleri kurulmus
        # olabilir; kurulu listesi dpkg'den yeniden okunmali.
        sinif = next(n for n in kaynak_agaci().body
                     if isinstance(n, ast.ClassDef) and n.name == "MagazaPenceresi")
        yontem = next(n for n in sinif.body
                      if isinstance(n, ast.FunctionDef) and n.name == "sepeti_kur")
        # dpkg okumasi ana is parcacigini dondurmasin: dogrudan degil, _kurulu_oku (thread) uzerinden
        govde = ast.get_source_segment(self.kaynak, yontem)
        self.assertIn("self._kurulu_oku(", govde)
        self.assertNotIn("kurulu_paketler()", govde)
        oku = next(n for n in sinif.body if isinstance(n, ast.FunctionDef) and n.name == "_kurulu_oku")
        oku_govde = ast.get_source_segment(self.kaynak, oku)
        self.assertIn("kurulu_paketler()", oku_govde)
        self.assertIn("threading.Thread", oku_govde)


class MetinSozluguTesti(unittest.TestCase):
    def test_tr_ve_en_anahtarlari_ayni(self):
        for anahtar, deger in metin_sozlugu().items():
            with self.subTest(anahtar=anahtar):
                self.assertEqual(set(deger), {"tr", "en"})
                self.assertTrue(deger["tr"] and deger["en"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
