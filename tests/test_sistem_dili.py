#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sistem dili hazirligi: tablo, paket secimi, locale denetimi ve root betigi (GTK'siz, root'suz).

Calistirma:  python3 tests/test_sistem_dili.py
"""
import importlib.machinery
import importlib.util
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
ORTAK = os.path.join(INC, "opt", "carotos", "ortak")
BETIK = os.path.join(INC, "usr", "local", "sbin", "carotos-dil-hazirla")
sys.path.insert(0, ORTAK)

import dil  # noqa: E402
import sistem_dili as SD  # noqa: E402


def betigi_yukle():
    yukleyici = importlib.machinery.SourceFileLoader("carotos_dil_hazirla", BETIK)
    spec = importlib.util.spec_from_loader("carotos_dil_hazirla", yukleyici)
    m = importlib.util.module_from_spec(spec)
    yukleyici.exec_module(m)
    return m


class TabloTesti(unittest.TestCase):
    def test_dokuz_dil_icin_tanim_var(self):
        self.assertEqual(set(SD.HAZIRLIK), set(dil.KODLAR))

    def test_locale_adlari_bicimi(self):
        for kod, k in SD.HAZIRLIK.items():
            with self.subTest(kod=kod):
                self.assertRegex(k["locale"], r"^[a-z]{2}_[A-Z]{2}\.UTF-8$")
                self.assertTrue(k["locale"].startswith(kod + "_"), k["locale"])

    def test_paket_adlari_gecerli_karakter(self):
        # betik bu adlari apt'e liste olarak verir; kabuk kullanilmaz ama yine de duz paket adi olmali
        kurulu = {"firefox-esr", "libreoffice-core"}
        for kod in SD.HAZIRLIK:
            for p in SD.paket_listesi(kod, kurulu):
                self.assertRegex(p, r"^[a-z0-9][a-z0-9.+-]+$", (kod, p))

    def test_cjk_dilleri_yazi_tipi_ister(self):
        for kod in ("ja", "zh"):
            self.assertIn("fonts-noto-cjk", SD.paket_listesi(kod, set()))
        self.assertNotIn("fonts-noto-cjk", SD.paket_listesi("de", set()))

    def test_tr_en_paket_gerektirmez(self):
        for kod in ("tr", "en"):
            self.assertEqual(SD.paket_listesi(kod, set()), [])
            self.assertFalse(SD.hazirlik_gerekli_mi(kod, set(), []))


class SecimTesti(unittest.TestCase):
    def test_firefox_ofis_dil_paketi_yalniz_ana_paket_kuruluysa(self):
        self.assertEqual(SD.paket_listesi("de", set()), ["hunspell-de-de"])
        self.assertEqual(SD.paket_listesi("de", {"firefox-esr"}),
                         ["firefox-esr-l10n-de", "hunspell-de-de"])
        self.assertEqual(SD.paket_listesi("pt", {"firefox-esr", "libreoffice-core"}),
                         ["firefox-esr-l10n-pt-br", "hunspell-pt-br", "libreoffice-l10n-pt-br"])
        self.assertEqual(SD.paket_listesi("es", {"firefox-esr"}),
                         ["firefox-esr-l10n-es-es", "hunspell-es"])

    def test_eksik_paketler(self):
        kurulu = {"firefox-esr", "hunspell-de-de"}
        self.assertEqual(SD.eksik_paketler("de", kurulu), ["firefox-esr-l10n-de"])
        kurulu.add("firefox-esr-l10n-de")
        self.assertEqual(SD.eksik_paketler("de", kurulu), [])

    def test_locale_normalizasyonu(self):
        self.assertTrue(SD.locale_var_mi("de", ["C", "de_DE.utf8", "POSIX"]))
        self.assertTrue(SD.locale_var_mi("de", ["de_DE.UTF-8"]))
        self.assertFalse(SD.locale_var_mi("de", ["C", "tr_TR.utf8"]))
        self.assertFalse(SD.locale_var_mi("de", ["de_AT.utf8"]))
        self.assertFalse(SD.locale_var_mi("xx", ["de_DE.utf8"]))

    def test_hazirlik_gerekli(self):
        tam = {"hunspell-de-de"}
        self.assertTrue(SD.hazirlik_gerekli_mi("de", tam, []))                       # locale yok
        self.assertFalse(SD.hazirlik_gerekli_mi("de", tam, ["de_DE.utf8"]))          # her sey tamam
        self.assertTrue(SD.hazirlik_gerekli_mi("de", set(), ["de_DE.utf8"]))         # paket eksik
        self.assertFalse(SD.hazirlik_gerekli_mi("xx", set(), []))                    # bilinmeyen

    def test_komut(self):
        self.assertEqual(SD.hazirla_komutu("de"), ["pkexec", "/usr/local/sbin/carotos-dil-hazirla", "de"])
        self.assertEqual(SD.locale_gen_satiri("ja"), "ja_JP.UTF-8 UTF-8")
        self.assertIsNone(SD.locale_gen_satiri("xx"))


class BetikTesti(unittest.TestCase):
    def setUp(self):
        self.b = betigi_yukle()
        self.gecici = tempfile.mkdtemp(prefix="dil-hazirla-")
        self.locale_gen = os.path.join(self.gecici, "locale.gen")
        self.b.LOCALE_GEN = self.locale_gen
        self.komutlar = []
        self.b.calistir = lambda komut: (self.komutlar.append(list(komut)), 0)[1]
        self.b.modulu_yukle = lambda: SD

    def calis(self, *argv, root=True, locales=(), kurulu=()):
        with mock.patch.object(os, "geteuid", lambda: 0 if root else 1000, create=True), \
                mock.patch.object(SD, "locale_a", lambda: list(locales)), \
                mock.patch.object(SD, "kurulu_paketler", lambda: set(kurulu)):
            return self.b.main(["carotos-dil-hazirla", *argv])

    def test_root_degilse_reddeder(self):
        self.assertEqual(self.calis("de", root=False), 2)
        self.assertEqual(self.komutlar, [])

    def test_argumansiz_ya_da_fazla_arguman(self):
        self.assertEqual(self.calis(), 2)
        self.assertEqual(self.calis("de", "ru"), 2)
        self.assertEqual(self.komutlar, [])

    def test_bilinmeyen_kod_reddedilir(self):
        for kod in ("xx", "../etc/passwd", "de;reboot", "", "DE"):
            self.assertEqual(self.calis(kod), 2, kod)
        self.assertEqual(self.komutlar, [])

    def test_tr_en_bir_sey_yapmaz(self):
        self.assertEqual(self.calis("tr"), 0)
        self.assertEqual(self.calis("en"), 0)
        self.assertEqual(self.komutlar, [])
        self.assertFalse(os.path.exists(self.locale_gen))

    def test_locale_ve_paketler_kurulur(self):
        with open(self.locale_gen, "w", encoding="utf-8") as f:
            f.write("# de_DE.UTF-8 UTF-8\n# ja_JP.UTF-8 UTF-8\nen_US.UTF-8 UTF-8\n")
        self.assertEqual(self.calis("ja", locales=["C.utf8"], kurulu={"firefox-esr"}), 0)
        satirlar = open(self.locale_gen, encoding="utf-8").read().splitlines()
        self.assertIn("ja_JP.UTF-8 UTF-8", satirlar)               # yorumdan cikti
        self.assertIn("# de_DE.UTF-8 UTF-8", satirlar)             # digerlerine dokunulmadi
        self.assertIn("en_US.UTF-8 UTF-8", satirlar)
        self.assertEqual(self.komutlar[0], ["locale-gen"])
        self.assertEqual(self.komutlar[1], ["apt-get", "update"])
        self.assertEqual(self.komutlar[2][:4], ["apt-get", "install", "-y", "--no-install-recommends"])
        self.assertEqual(sorted(self.komutlar[2][4:]), ["firefox-esr-l10n-ja", "fonts-noto-cjk"])

    def test_locale_satiri_yoksa_eklenir(self):
        with open(self.locale_gen, "w", encoding="utf-8") as f:
            f.write("en_US.UTF-8 UTF-8\n")
        self.calis("fr", locales=[], kurulu={"hunspell-fr"})
        self.assertIn("fr_FR.UTF-8 UTF-8", open(self.locale_gen, encoding="utf-8").read().splitlines())

    def test_hazirsa_hicbir_sey_calistirmaz(self):
        self.assertEqual(self.calis("de", locales=["de_DE.utf8"], kurulu={"hunspell-de-de"}), 0)
        self.assertEqual(self.komutlar, [])

    def test_locale_gen_hatasinda_paket_kurmaz(self):
        self.b.calistir = lambda komut: (self.komutlar.append(list(komut)), 1)[1]
        self.assertEqual(self.calis("de", locales=[], kurulu=set()), 1)
        self.assertEqual(self.komutlar, [["locale-gen"]])

    def test_apt_hatasinda_hata_kodu(self):
        def calistir(komut):
            self.komutlar.append(list(komut))
            return 1 if komut[:2] == ["apt-get", "install"] else 0
        self.b.calistir = calistir
        self.assertEqual(self.calis("de", locales=["de_DE.utf8"], kurulu=set()), 1)

    def test_varsayilan_sistem_diline_dokunmaz(self):
        # /etc/default/locale hicbir yerde gecmemeli (sistem geneli degistirilmez)
        kaynak = open(BETIK, encoding="utf-8").read()
        kod = re.sub(r'"""[\s\S]*?"""', "", kaynak)           # aciklama metni sayilmaz
        self.assertNotIn("/etc/default/locale", kod)
        self.assertNotIn("update-locale", kod)
        self.assertNotIn("shell=True", kod)
        self.assertNotIn("os.system", kod)

    @unittest.skipIf(not hasattr(os, "geteuid") or os.geteuid() == 0, "root'ta anlamsiz")
    def test_guvensiz_modul_reddedilir(self):
        # root'a ait olmayan modulle betik cikar (gercek modulu_yukle, normal kullanici dosyasi)
        b = betigi_yukle()
        gecici = tempfile.mkdtemp(prefix="dil-modul-")
        open(os.path.join(gecici, "sistem_dili.py"), "w").close()
        b.MODUL_DIZINI = gecici
        with self.assertRaises(SystemExit) as c:
            b.modulu_yukle()
        self.assertEqual(c.exception.code, 3)


class DosyaTesti(unittest.TestCase):
    def test_betik_lf_ve_shebang(self):
        veri = open(BETIK, "rb").read()
        self.assertTrue(veri.startswith(b"#!/usr/bin/python3 -I\n"))
        self.assertNotIn(b"\r\n", veri)

    def test_hook_izin_veriyor(self):
        hook = open(os.path.join(KOK, "config", "hooks", "live", "9999-carotos-setup.hook.chroot"),
                    encoding="utf-8").read()
        self.assertIn("chmod 755 /usr/local/sbin/carotos-dil-hazirla", hook)

    def test_karsilama_hepsini_bagli(self):
        k = open(os.path.join(INC, "opt", "carotos", "welcome", "carotos-welcome.py"), encoding="utf-8").read()
        self.assertIn("import sistem_dili as sd", k)
        self.assertIn('LOCALE_FOR_LANG = {kod: v["locale"] for kod, v in sd.HAZIRLIK.items()}', k)
        for ad in ('"carotos-poligon", "ayar.json"', '"filenor", "filenor.json"', '"carotene", "settings.json"',
                   '"carotos-magaza", "ayarlar.json"', '"carotpot", "settings.json"'):
            self.assertIn(ad, k)
        self.assertIn("sd.hazirlik_gerekli_mi(self.lang)", k)


if __name__ == "__main__":
    unittest.main()
