#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Etik koruma katmani testleri (GTK gerektirmez).

ortak/etik_koruma.py (hedef siniflama, onay mantigi, gunluk) ve Guvenlik
Paneli'ne baglanisi (hangi araclar, metin kurallari) denenir.

Calistirma (depo kokunden):  python3 tests/test_etik_koruma.py
"""
import ast
import os
import re
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
sys.path.insert(0, os.path.join(INC, "ortak"))
PANEL = os.path.join(INC, "security-panel", "carotos-security-panel.py")

import etik_koruma as E  # noqa: E402


def degerlendir(metin, onayli=(), kendi_ad="carotos"):
    return E.degerlendir(metin, onayli, kendi_ad)


class SiniflamaTesti(unittest.TestCase):
    def test_yerel_hedeflerde_surtunme_yok(self):
        for m in ("127.0.0.1", "localhost", "http://localhost:8080/x?id=1", "::1",
                  "[::1]:80", "127.0.0.0/8", "0.0.0.0", "127.0.0.1:8899", "carotos",
                  "LOCALHOST", "web.localhost"):
            with self.subTest(m=m):
                k = degerlendir(m)
                self.assertFalse(k["gerek"], k)
                self.assertEqual(k["sinif"], E.YEREL)

    def test_acik_adresler_ve_adlar_elle_yazim_ister(self):
        for m, beklenen in (("8.8.8.8", "8.8.8.8"),
                            ("scanme.nmap.org", "scanme.nmap.org"),
                            ("https://Example.com/p?id=1", "example.com"),
                            ("8.8.8.8:443", "8.8.8.8"),
                            ("2001:4860:4860::8888", "2001:4860:4860::8888"),
                            ("172.32.0.1", "172.32.0.1")):
            with self.subTest(m=m):
                k = degerlendir(m)
                self.assertTrue(k["gerek"])
                self.assertEqual(k["tur"], "yaz")
                self.assertEqual(k["sinif"], E.DISARI)
                self.assertEqual(k["onay_metni"], beklenen)

    def test_genis_ozel_bloklar_disari_sayilir(self):
        for m in ("192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"):
            with self.subTest(m=m):
                k = degerlendir(m, onayli=("192.168.1.0/24",))
                self.assertEqual(k["tur"], "yaz")
                self.assertEqual(k["onay_metni"], m)

    def test_karisik_hedefte_en_siki_sinif_gecer_ve_tum_metin_yazilir(self):
        k = degerlendir("127.0.0.1 8.8.8.8")
        self.assertEqual(k["tur"], "yaz")
        self.assertEqual(k["onay_metni"], "127.0.0.1 8.8.8.8")
        k = degerlendir("8.8.8.8 1.1.1.1")
        self.assertEqual(k["onay_metni"], "8.8.8.8 1.1.1.1")

    def test_ayristirilamayan_girdi_temkinli(self):
        for m in ("-iL hosts.txt", "--script=/tmp/x.nse", "", "   "):
            with self.subTest(m=m):
                k = degerlendir(m)
                self.assertTrue(k["gerek"])
                self.assertEqual(k["tur"], "yaz")

    def test_secenek_jetonlari_hedef_sayilmaz(self):
        k = degerlendir("-p 80 127.0.0.1")
        self.assertFalse(k["gerek"])

    def test_aralik_her_iki_ucu_denetlenir(self):
        self.assertEqual(degerlendir("192.168.1.1-50")["sinif"], E.OZEL)
        self.assertEqual(degerlendir("8.8.8.1-50")["tur"], "yaz")
        self.assertEqual(degerlendir("192.168.1.*")["sinif"], E.OZEL)
        # alt uc ozel, ust uc acik adres: temkinli (disari)
        self.assertEqual(degerlendir("10.255.255.250-9.1.1.1")["sinif"], E.DISARI)


class OzelAgTesti(unittest.TestCase):
    def test_ozel_ag_bir_kez_sorulur(self):
        k = degerlendir("192.168.1.5")
        self.assertTrue(k["gerek"])
        self.assertEqual(k["tur"], "ozel")
        self.assertEqual(k["aglar"], ["192.168.1.0/24"])

    def test_onayli_agda_ayni_ag_icin_sorulmaz(self):
        onayli = ("192.168.1.0/24",)
        self.assertFalse(degerlendir("192.168.1.5", onayli)["gerek"])
        self.assertFalse(degerlendir("192.168.1.200:80", onayli)["gerek"])
        self.assertFalse(degerlendir("http://192.168.1.9/x", onayli)["gerek"])

    def test_baska_ozel_ag_yine_sorulur(self):
        k = degerlendir("192.168.2.1", ("192.168.1.0/24",))
        self.assertTrue(k["gerek"])
        self.assertEqual(k["aglar"], ["192.168.2.0/24"])

    def test_ozel_adres_turleri(self):
        for m in ("10.1.2.3", "172.16.0.1", "172.31.255.255", "100.64.0.1",
                  "169.254.1.1", "fd00::1", "fe80::1", "router", "nas.local",
                  "yazici.lan", "pc.home.arpa"):
            with self.subTest(m=m):
                self.assertEqual(degerlendir(m)["sinif"], E.OZEL)

    def test_kendi_makine_adi_yerel_baskasi_ozel(self):
        self.assertEqual(degerlendir("carotos", kendi_ad="carotos")["sinif"], E.YEREL)
        self.assertEqual(degerlendir("pc", kendi_ad="carotos")["sinif"], E.OZEL)

    def test_ag_anahtari(self):
        self.assertEqual(E.ag_anahtari("10.20.30.40"), "10.20.30.0/24")
        self.assertEqual(E.ag_anahtari("fd00::1"), "fd00::/64")
        self.assertEqual(E.ag_anahtari("Router.Local"), "ad:router.local")

    def test_hedefler_dns_cozumlemesi_yapmaz(self):
        # Sinifla, ag erisimi olmadan calismali (cevrimdisi, deterministik).
        import socket
        eski = socket.getaddrinfo

        def yasak(*a, **k):
            raise AssertionError("DNS sorgusu yapildi")
        socket.getaddrinfo = yasak
        try:
            degerlendir("scanme.nmap.org")
            degerlendir("router.local")
        finally:
            socket.getaddrinfo = eski


class OnayTesti(unittest.TestCase):
    def test_elle_yazim_kontrolu(self):
        self.assertTrue(E.onay_dogru("8.8.8.8", "8.8.8.8"))
        self.assertTrue(E.onay_dogru("example.com", "  EXAMPLE.com "))
        self.assertFalse(E.onay_dogru("example.com", "example.org"))
        self.assertFalse(E.onay_dogru("", ""))
        self.assertFalse(E.onay_dogru("8.8.8.8", ""))


class GunlukTesti(unittest.TestCase):
    def test_satir_yazilir_ve_kontrol_karakterleri_temizlenir(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "alt", "etik.log")
            self.assertTrue(E.gunluge_yaz(yol, "nmap", "8.8.8.8\nsahte\tsatir", "disari", "onayladi"))
            self.assertTrue(E.gunluge_yaz(yol, "nikto", "127.0.0.1", "yerel", "otomatik"))
            satirlar = open(yol, encoding="utf-8").read().splitlines()
            self.assertEqual(len(satirlar), 2)
            alanlar = satirlar[0].split("\t")
            self.assertEqual(len(alanlar), 5)
            self.assertEqual(alanlar[1:], ["nmap", "8.8.8.8 sahte satir", "disari", "onayladi"])
            if os.name == "posix":
                self.assertEqual(os.stat(yol).st_mode & 0o777, 0o600)

    def test_yazilamayan_yolda_sessizce_false(self):
        with tempfile.TemporaryDirectory() as d:
            dosya = os.path.join(d, "dosya")
            open(dosya, "w").close()
            self.assertFalse(E.gunluge_yaz(os.path.join(dosya, "alt", "x.log"), "a", "b", "c", "d"))

    def test_buyuyen_gunluk_kirpilir(self):
        eski = E._GUNLUK_SINIR
        E._GUNLUK_SINIR = 2000
        try:
            with tempfile.TemporaryDirectory() as d:
                yol = os.path.join(d, "etik.log")
                for i in range(700):
                    E.gunluge_yaz(yol, "nmap", f"host{i}", "disari", "onayladi")
                satirlar = open(yol, encoding="utf-8").read().splitlines()
                self.assertLessEqual(len(satirlar), 501)   # son 500 + yeni satir
                self.assertIn("host699", satirlar[-1])      # en yeni kayit korunur
        finally:
            E._GUNLUK_SINIR = eski


def _panel_agaci():
    with open(PANEL, "rb") as f:
        return ast.parse(f.read().decode("utf-8"))


class PanelBaglantisiTesti(unittest.TestCase):
    """Guvenlik Paneli kaynagi: hangi araclar kapida, metinler, calisma sirasi."""

    def test_yalniz_baska_sisteme_dokunan_dort_arac_kapida(self):
        kapili = {}
        for dugum in _panel_agaci().body:
            # TOOLS sonradan dil.zenginlestir(TOOLS) ile yeniden atanir; yalniz liste degerini al
            if (isinstance(dugum, ast.Assign) and isinstance(dugum.value, ast.List)
                    and any(getattr(t, "id", "") == "TOOLS" for t in dugum.targets)):
                for arac in dugum.value.elts:
                    anahtarlar = {k.value: v for k, v in zip(arac.keys, arac.values)
                                  if isinstance(k, ast.Constant)}
                    ad = anahtarlar["name"].value
                    alan_anahtarlari = [e.elts[0].value for e in anahtarlar["fields"].elts]
                    if "hedef_alani" in anahtarlar:
                        kapili[ad] = anahtarlar["hedef_alani"].value
                        self.assertIn(kapili[ad], alan_anahtarlari, ad)
        self.assertEqual(kapili, {"nmap": "target", "nikto": "target", "sqlmap": "url", "hydra": "target"})

    def test_etik_kontrol_komut_kurulmadan_once_calisir(self):
        kaynak = open(PANEL, encoding="utf-8").read()
        run = kaynak[kaynak.index("    def run(self, as_root):"):kaynak.index("    def _etik_onay")]
        self.assertIn("self._etik_onay(values)", run)
        self.assertLess(run.index("self._etik_onay(values)"), run.index('self.tool["build"](values)'))

    def test_metinler_iki_dilde_ve_yasa_atfi_yok(self):
        metinler = None
        for dugum in _panel_agaci().body:
            if (isinstance(dugum, ast.Assign) and isinstance(dugum.value, ast.Dict)
                    and any(getattr(t, "id", "") == "STRINGS" for t in dugum.targets)):
                metinler = ast.literal_eval(dugum.value)
        etik = {k: v for k, v in metinler.items() if k.startswith("etik_")}
        self.assertGreaterEqual(len(etik), 8)
        yasak = re.compile(r"TCK|StGB|CFAA|Misuse|§|\bmadde\b|\barticle\b|\bsection \d", re.I)
        for anahtar, d in etik.items():
            with self.subTest(anahtar=anahtar):
                self.assertEqual(set(d), {"tr", "en"})
                self.assertEqual(set(re.findall(r"\{(\w+)\}", d["tr"])),
                                 set(re.findall(r"\{(\w+)\}", d["en"])))
                for metin in d.values():
                    self.assertFalse(yasak.search(metin), metin)
        for dil in ("tr", "en"):   # hukuki tavsiye degildir uyarisi her dilde var
            self.assertRegex(etik["etik_metin"][dil], r"hukuki tavsiye|legal advice")


if __name__ == "__main__":
    unittest.main()
