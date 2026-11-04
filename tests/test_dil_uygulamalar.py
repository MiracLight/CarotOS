#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Uygulamalarin ortak dil katmanina gecisi (ekran yoksa atlanir).

Her baglanmis uygulama dokuz dilin hepsinde acilip gezilir: eksik ceviri
Ingilizceye duser, KeyError/cokme olmaz; dil seciciye yalniz cevirisi hazir
diller girer; bozuk kayitli dil Ingilizceye doner.

Calistirma:  xvfb-run -a python3 tests/test_dil_uygulamalar.py
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
sys.path.insert(0, os.path.join(INC, "ortak"))

EKRAN = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

# GLib kullanici klasorlerini ILK cagrida onbellege alir: sahte HOME surec basina
# bir kez kurulur (sinif basina degil), testler arasi yalniz ayar klasoru temizlenir.
_EV = None


def _sahte_ev():
    global _EV
    if _EV is None:
        _EV = tempfile.TemporaryDirectory()
        os.environ["HOME"] = _EV.name
        os.environ["XDG_CONFIG_HOME"] = os.path.join(_EV.name, ".config")
        os.environ["XDG_DATA_HOME"] = os.path.join(_EV.name, ".local", "share")
        import atexit
        atexit.register(_EV.cleanup)
    return _EV

UYGULAMALAR = {
    "health": "health/carotos-health.py",
    "usb": "usb/carotos-usb-check.py",
    "magaza": "magaza/carotos-magaza.py",
    "carotene": "carotene/carotene.py",
    "welcome": "welcome/carotos-welcome.py",
    "gsd": "gsd/carotos-gsd.py",
    "former": "former/carotos-former.py",
}

# GSD, Former, CarotPot kendi paketlerini (terimler, konular, arayuz...) kardes klasorden alir
for _p in ("gsd", "former", "carotpot"):
    if os.path.join(INC, _p) not in sys.path:
        sys.path.insert(0, os.path.join(INC, _p))


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class UygulamaDilTabani(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev = _sahte_ev()           # GTK/GLib iceri aktarilmadan ONCE (klasorleri onbellege alir)
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk, GLib
        except (ImportError, ValueError) as exc:
            raise unittest.SkipTest("GTK yok: %s" % exc)
        cls.Gtk, cls.GLib = Gtk, GLib
        import dil
        cls.dil = dil
        cls.diller = tempfile.mkdtemp()
        cls.eski_dizin = dil.DIZIN
        dil.DIZIN = cls.diller
        dil.onbellegi_temizle()
        cls.moduller = {}

    @classmethod
    def tearDownClass(cls):
        cls.dil.DIZIN = cls.eski_dizin
        cls.dil.onbellegi_temizle()
        shutil.rmtree(cls.diller, True)

    def setUp(self):
        shutil.rmtree(os.environ["XDG_CONFIG_HOME"], ignore_errors=True)   # her test temiz ayarla baslar

    def modul(self, ad):
        if ad not in self.moduller:
            spec = importlib.util.spec_from_file_location("dil_test_" + ad, os.path.join(INC, UYGULAMALAR[ad]))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.moduller[ad] = mod
        return self.moduller[ad]

    def dil_dosyasi(self, kod, metinler, etkin=True):
        with open(os.path.join(self.diller, kod + ".json"), "w", encoding="utf-8") as f:
            json.dump({"_meta": {"ad": kod, "etkin": etkin, "durum": "taslak"}, "metinler": metinler}, f)
        self.dil.onbellegi_temizle()

    def tearDown(self):
        for ad in os.listdir(self.diller):
            os.remove(os.path.join(self.diller, ad))
        self.dil.onbellegi_temizle()

    def pompala(self):
        for _ in range(30):
            while self.Gtk.events_pending():
                self.Gtk.main_iteration()

    def ayar_yaz(self, klasor, dosya, veri):
        yol = os.path.join(os.environ["XDG_CONFIG_HOME"], klasor, dosya)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(veri, f)
        return yol


class SaglikTesti(UygulamaDilTabani):
    def test_dokuz_dilde_gezinti(self):
        m = self.modul("health")
        pencere = m.HealthWindow(m.load_settings())
        self.addCleanup(pencere.destroy)
        sonuclar = [{"id": c["id"], "category": c["category"], "status": m.WARN,
                     "detail": {"tr": f"Ayrıntı {c['id']}", "en": f"Detail {c['id']}"}}
                    for c in m.CHECKS]
        pencere.results = self.dil.zenginlestir(sonuclar)    # run_all_checks'in yaptigi gibi
        anahtarlar = ["summary"] + [k for k, _ in m.CATEGORIES]
        for lang in self.dil.KODLAR:
            pencere.lang = lang
            pencere.retranslate_static()
            for anahtar in anahtarlar:
                pencere.show_category(anahtar)
                self.pompala()
        pencere.lang = "tr"

    def test_dil_secici_ve_bozuk_ayar(self):
        m = self.modul("health")
        self.assertEqual([r[0] for r in self._combo(m)], ["Türkçe", "English"])
        self.dil_dosyasi("de", {"Run": "x"})
        self.assertEqual([r[0] for r in self._combo(m)], ["Türkçe", "English", "Deutsch (beta)"])
        ayar = self.ayar_yaz("carotos-health", "settings.json", {"lang": "klingon", "theme": "dark"})
        pencere = m.HealthWindow(m.load_settings())
        self.addCleanup(pencere.destroy)
        self.assertEqual(pencere.lang, "en")
        os.remove(ayar)

    def _combo(self, m):
        pencere = m.HealthWindow(m.load_settings())
        self.addCleanup(pencere.destroy)
        return list(pencere.lang_combo.get_model())

    def test_yedek_zinciri(self):
        m = self.modul("health")
        self.assertEqual(m.UI["refresh"]["ja"], m.UI["refresh"]["en"])
        self.dil_dosyasi("de", {m.UI["refresh"]["en"]: "Aktualisieren"})
        self.assertEqual(m.UI["refresh"]["de"], "Aktualisieren")


class UsbTesti(UygulamaDilTabani):
    def test_rapor_ve_pencere_dokuz_dilde(self):
        m = self.modul("usb")
        kok = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, kok, True)
        for ad, icerik in (("kurulum.exe", b"MZ"), ("belge.docm", b"x"), ("normal.txt", b"merhaba"),
                           ("a‮txt.exe", b"x")):
            with open(os.path.join(kok, ad), "wb") as f:
                f.write(icerik)
        sonuc = m.enrich(m.scan_path(kok), kok)
        self.assertTrue(sonuc["findings"])
        for lang in self.dil.KODLAR:
            self.assertTrue(m.build_report(sonuc, lang).strip(), lang)
            for bulgu in sonuc["findings"]:
                self.assertTrue(m.metin(bulgu["title"], lang).strip(), (lang, bulgu))
        Pencere = m._gtk_araclari()
        ayar = dict(m.load_settings())
        pencere = Pencere(sonuc, ayar)
        self.addCleanup(pencere.destroy)
        for lang in self.dil.KODLAR:
            pencere.lang = lang
            pencere.refresh()
            self.pompala()

    def test_bozuk_ayar_ve_secici(self):
        m = self.modul("usb")
        self.ayar_yaz("carotos-usb", "settings.json", {"lang": "klingon"})
        self.assertEqual(m.load_settings()["lang"], "en")
        self.assertEqual(m.metin({"tr": "a", "en": "b"}, "fr"), "b")
        self.dil_dosyasi("fr", {"b": "c"})
        self.assertEqual(m.metin({"tr": "a", "en": "b"}, "fr"), "c")


class MagazaTesti(UygulamaDilTabani):
    def test_arayuz_metinleri_dokuz_dilde(self):
        m = self.modul("magaza")
        for lang in self.dil.KODLAR:
            m.DIL = lang
            for anahtar in m.METIN:
                try:
                    metin = m.M(anahtar, s="x", n=1, ad="y", paket="z", sayi=2, adet=3, toplam=4,
                                kategori="k", hata="e", surum="1")
                except (KeyError, IndexError):
                    metin = m.M(anahtar)           # baska yer tutucular: yedek yolu da cokmemeli
                self.assertTrue(isinstance(metin, str) and metin.strip(), (lang, anahtar))
        m.DIL = "tr"

    def test_katalog_metni_yedekli(self):
        m = self.modul("magaza")
        m.DIL = "ja"
        self.assertEqual(m.metin({"tr": "Merhaba", "en": "Hello"}), "Hello")
        self.dil_dosyasi("ja", {"Hello": "こんにちは"})
        self.assertEqual(m.metin({"tr": "Merhaba", "en": "Hello"}), "こんにちは")
        m.DIL = "tr"

    def test_sistem_dili_ve_ortam(self):
        m = self.modul("magaza")
        eski = {k: os.environ.get(k) for k in ("CAROTOS_DIL", "LC_ALL", "LANG")}
        try:
            os.environ["CAROTOS_DIL"] = "fr"
            self.assertEqual(m._sistem_dili(), "fr")
            os.environ["CAROTOS_DIL"] = "xx"
            os.environ["LC_ALL"] = "tr_TR.UTF-8"
            self.assertEqual(m._sistem_dili(), "tr")
        finally:
            for k, v in eski.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class CaroteneTesti(UygulamaDilTabani):
    def test_dokuz_dilde_gezinti(self):
        m = self.modul("carotene")
        pencere = m.CaroteneWindow(m.load_settings())
        self.addCleanup(pencere.destroy)
        for lang in self.dil.KODLAR:
            pencere.lang = lang
            pencere.retranslate()
            for sayfa in ("scan", "quarantine"):
                pencere.show_page(sayfa)
                self.pompala()
        for anahtar in m.METIN:
            for lang in self.dil.KODLAR:
                self.assertTrue(m.METIN[anahtar][lang].strip(), (lang, anahtar))

    def test_bozuk_ayar_ve_secici(self):
        m = self.modul("carotene")
        self.ayar_yaz("carotene", "settings.json", {"lang": "klingon", "theme": "dark"})
        self.assertEqual(m.load_settings()["lang"], "en")


class GsdTesti(UygulamaDilTabani):
    def test_dokuz_dilde_terimler(self):
        m = self.modul("gsd")
        pencere = m.Uygulama()
        self.addCleanup(pencere.destroy)
        ornek = [t["id"] for t in pencere.tumu][::12]
        for lang in self.dil.KODLAR:
            pencere.lang = lang
            pencere._arama_indeksi_kur()
            pencere._metinleri_uygula()
            for tid in ornek:
                pencere._detay_goster(tid)
            pencere._bos_goster()
            self.pompala()
        pencere.lang = "tr"

    def test_arama_secili_dilin_cevirisini_de_bulur(self):
        m = self.modul("gsd")
        pencere = m.Uygulama()
        self.addCleanup(pencere.destroy)
        tid = pencere.tumu[0]["id"]
        baslik_en = m.metin_al(pencere.tumu[0]["baslik"], "en")
        self.dil_dosyasi("de", {baslik_en: "Zzyzx-Begriff"})
        pencere.lang = "de"
        pencere._arama_indeksi_kur()
        self.assertIn("zzyzx-begriff", pencere._arama_metni[tid])
        pencere.lang = "tr"
        pencere._arama_indeksi_kur()
        self.assertNotIn("zzyzx-begriff", pencere._arama_metni[tid])

    def test_bozuk_kayitli_dil_ve_secici(self):
        m = self.modul("gsd")
        self.ayar_yaz("carotos-gsd", "settings.json", {"dil": "klingon", "tema": "dark"})
        pencere = m.Uygulama()
        self.addCleanup(pencere.destroy)
        self.assertEqual(pencere.lang, "en")
        self.assertEqual([r[0] for r in pencere.dil_kutu.get_model()], ["Türkçe", "English"])


class FormerTesti(UygulamaDilTabani):
    def test_dokuz_dilde_konular(self):
        m = self.modul("former")
        pencere = m.Uygulama()
        self.addCleanup(pencere.destroy)
        konular = list(pencere.konular)
        self.assertGreater(len(konular), 10)
        for lang in self.dil.KODLAR:
            pencere.lang = lang
            pencere._metinleri_uygula()
            for kid in konular[::3]:
                pencere._aktif_id = kid
                pencere._sayfayi_yeniden_kur(kid)
            pencere._bos_goster()
            self.pompala()
        pencere.lang = "tr"

    def test_zaman_cizelgesi_her_dilde(self):
        m = self.modul("former")
        pencere = m.Uygulama()
        self.addCleanup(pencere.destroy)
        for lang in self.dil.KODLAR:
            for kid, konu in list(pencere.konular.items())[::4]:
                cz = m.fz.derle(konu["sahne"], konu["adimlar"], lang)
                cz.durum(0)
                cz.durum(5000)

    def test_bozuk_kayitli_dil(self):
        m = self.modul("former")
        self.ayar_yaz("carotos-former", "settings.json", {"dil": "klingon", "tema": "dark"})
        pencere = m.Uygulama()
        self.addCleanup(pencere.destroy)
        self.assertEqual(pencere.lang, "en")


class CarotPotTesti(UygulamaDilTabani):
    def _pencere_modulu(self):
        import importlib
        return importlib.import_module("arayuz.pencere")

    def test_dokuz_dilde_tum_sayfalar(self):
        pm = self._pencere_modulu()
        pencere = pm.Pencere()
        self.addCleanup(pencere.destroy)
        anahtarlar = [a for _, sayfalar in pm.BOLUMLER for a, _ in sayfalar]
        for lang in self.dil.KODLAR:
            pencere.lang = pencere.ui["lang"] = lang
            pencere.yeniden_kur()
            for anahtar in anahtarlar:
                pencere.sayfa_secildi(anahtar)
                self.pompala()
        pencere.lang = "tr"

    def test_olay_ve_bildirim_metinleri_her_dilde(self):
        import carotpot as CP
        import kanarya
        olaylar = [{"tur": "giris", "hizmet": "ssh", "kaynak": "10.0.0.5", "kullanici": "root"},
                   {"tur": "baglanti", "hizmet": "ftp", "kaynak": "10.0.0.5"},
                   {"tur": "istek", "hizmet": "http", "kaynak": "10.0.0.5"},
                   {"tur": "komut", "hizmet": "redis", "kaynak": "10.0.0.5", "ayrinti": "get x"},
                   {"tur": "tarama", "hizmet": "vnc", "kaynak": "10.0.0.5", "hedef_port": 5900}]
        for lang in self.dil.KODLAR:
            for olay in olaylar:
                self.assertTrue(CP.olay_aciklamasi(olay, lang).strip(), (lang, olay))
                baslik, govde = CP.bildirim_metni(olay, lang)
                self.assertTrue(baslik.strip() and govde.strip())
            for tur in ("acildi", "degisti", "silindi", "tasindi"):
                baslik, govde = kanarya.bildirim_metni(
                    {"yol": "/home/x/gizli.txt", "tur": tur, "surec": "cat (12)"}, lang)
                self.assertTrue(baslik.strip() and govde.strip(), (lang, tur))
        self.assertEqual(CP.olay_aciklamasi(olaylar[0], "de"), CP.olay_aciklamasi(olaylar[0], "en"))

    def test_bozuk_kayitli_dil(self):
        pm = self._pencere_modulu()
        self.ayar_yaz("carotpot", "settings.json", {"lang": "klingon", "theme": "dark"})
        self.assertEqual(pm.arayuz_ayarlari()["lang"], "en")


class KarsilamaTesti(UygulamaDilTabani):
    def _kardes_ayar_yolu(self, klasor):
        return os.path.join(os.environ["XDG_CONFIG_HOME"], klasor, "settings.json")

    def test_dokuz_dilde_tum_sayfalar(self):
        m = self.modul("welcome")
        pencere = m.WelcomeWindow(m.load_settings())
        self.addCleanup(pencere.destroy)
        for lang in self.dil.KODLAR:
            pencere.lang = lang
            pencere.rebuild()
            for i in range(len(m.PAGES)):
                pencere.index = i
                pencere.refresh()
                self.pompala()
        pencere.lang = "tr"

    def test_dil_kartlari_ve_secici_hazir_dilleri_gosterir(self):
        m = self.modul("welcome")
        pencere = m.WelcomeWindow(m.load_settings())
        self.addCleanup(pencere.destroy)
        self.assertEqual(sorted(pencere.lang_cards), ["en", "tr"])          # dosya yok: yalniz tr/en
        self.dil_dosyasi("de", {"Next": "Weiter"})
        self.dil_dosyasi("es", {"Next": "Siguiente"})
        pencere2 = m.WelcomeWindow(m.load_settings())
        self.addCleanup(pencere2.destroy)
        self.assertEqual(sorted(pencere2.lang_cards), ["de", "en", "es", "tr"])
        adlar = [r[0] for r in pencere2.lang_combo.get_model()]
        self.assertEqual(adlar, ["Türkçe", "English", "Deutsch (beta)", "Español (beta)"])

    def test_secilen_dil_kardes_uygulamalara_yazilir(self):
        m = self.modul("welcome")
        self.dil_dosyasi("de", {"Next": "Weiter"})
        m.apply_sibling_settings("de", "dark")
        for klasor, anahtar in (("carotos-panel", "language"), ("carotos-health", "lang"),
                                ("carotos-usb", "lang"), ("carotos-former", "dil"),
                                ("carotos-gsd", "dil")):
            with open(self._kardes_ayar_yolu(klasor), encoding="utf-8") as f:
                self.assertEqual(json.load(f)[anahtar], "de", klasor)

    def test_bozuk_kayitli_dil(self):
        m = self.modul("welcome")
        yol = self.ayar_yaz("carotos-welcome", "settings.json", {"lang": "klingon", "theme": "dark"})
        self.assertEqual(m.load_settings()["lang"], "en")
        os.remove(yol)


if __name__ == "__main__":
    unittest.main()
