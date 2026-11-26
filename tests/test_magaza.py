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
    # Root programlari artik shutil.which (kullanici PATH'i) ile degil, ortak/yetkili.py
    # sistem_yolu ile bulunur (M-04); test sistem_yolu'nu sahteler.
    def setUp(self):
        import re
        agac = kaynak_agaci()
        secilen = [n for n in agac.body
                   if (isinstance(n, ast.FunctionDef) and n.name in ("apt_komutu", "paket_adi_gecerli"))
                   or (isinstance(n, ast.Assign)
                       and any(getattr(t, "id", "") in ("PAKET_ADI", "APT_EYLEMLERI", "EK_PAKETLER") for t in n.targets))]
        self.ad_alani = {"re": re, "sistem_yolu": lambda ad: "/usr/bin/" + ad}
        exec(compile(ast.Module(body=secilen, type_ignores=[]), KOD, "exec"), self.ad_alani)

    def test_yerel_ayar_c_olur(self):
        # Turkce yerelde rkhunter gibi paketlerin kurulum betigi dusuyordu
        for eylem in ("install", "remove", "upgrade"):
            with self.subTest(eylem=eylem):
                komut = self.ad_alani["apt_komutu"](eylem, "rkhunter")
                self.assertIn("LC_ALL=C", komut)
                self.assertIn("DEBIAN_FRONTEND=noninteractive", komut)

    def test_libreoffice_gtk_eklentisiyle_kurulur(self):
        # eklentisiz LibreOffice eski X11 gorunumuyle acilir, masaustu temasini izlemez
        k = self.ad_alani["apt_komutu"]
        self.assertEqual(k("install", "libreoffice")[-2:], ["libreoffice", "libreoffice-gtk3"])
        self.assertNotIn("libreoffice-gtk3", k("remove", "libreoffice"))
        self.assertEqual(k("install", "nmap")[-1], "nmap")

    def test_komut_pkexec_ile_baslar_ve_apt_get_cagirir(self):
        komut = self.ad_alani["apt_komutu"]("install", "nmap")
        self.assertEqual(komut[0], "/usr/bin/pkexec")
        self.assertIn("/usr/bin/apt-get", komut)
        self.assertEqual(komut[komut.index("install") + 1:], ["-y", "--", "nmap"])

    def test_birden_cok_paket_tek_komutta(self):
        komut = self.ad_alani["apt_komutu"]("install", "nmap", "rkhunter", "htop")
        self.assertEqual(komut[-3:], ["nmap", "rkhunter", "htop"])
        self.assertEqual(komut.count("/usr/bin/apt-get"), 1)

    def test_pkexec_yoksa_none(self):
        self.ad_alani["sistem_yolu"] = lambda ad: None
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

    def test_sepet_icerigi_gorunur_ve_cikarilabilir(self):
        sozluk = metin_sozlugu()
        for anahtar in ("sepeti_gor", "sepet_baslik", "sepet_bos_baslik", "sepetten_cikar",
                        "sepeti_bosalt", "islem_goster", "kismi_basari"):
            with self.subTest(anahtar=anahtar):
                self.assertIn(anahtar, sozluk)
        sinif = next(n for n in kaynak_agaci().body
                     if isinstance(n, ast.ClassDef) and n.name == "MagazaPenceresi")
        adlar = {n.name for n in sinif.body if isinstance(n, ast.FunctionDef)}
        for ad in ("_sepet_sayfasi", "_sepet_satiri", "_sepetten_cikar", "_sepeti_bosalt"):
            self.assertIn(ad, adlar)
        sayfa = next(n for n in sinif.body if n.name == "sayfa_secildi")
        self.assertIn('"sepet"', ast.get_source_segment(self.kaynak, sayfa))

    def test_gizlenen_islem_geri_getirilebilir(self):
        # Gizle/x ile gizlenen islem: ust bantta "Islem suruyor: goster" dugmesi ve
        # bitince (basarili da olsa) pencere kendiliginden one gelir
        sinif = next(n for n in kaynak_agaci().body
                     if isinstance(n, ast.ClassDef) and n.name == "MagazaPenceresi")
        ayarla = next(n for n in sinif.body if n.name == "_mesgul_ayarla")
        govde = ast.get_source_segment(self.kaynak, ayarla)
        self.assertIn("islem_dugme", govde)
        self.assertIn("self.present()", self.kaynak.split("def _bitti")[1].split("def calisiyor")[0])
        self.assertNotIn("if not basarili and not self.iptal_edildi and not self.get_visible()",
                         self.kaynak)

    def test_kismi_basari_isareti_okunur(self):
        self.assertIn("BASARISIZ_ISARETI", self.kaynak)
        self.assertIn('M("kismi_basari"', self.kaynak)

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
