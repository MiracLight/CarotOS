#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GSD testleri: terim sozlugunun yapisal dogrulugu (benzersiz kimlik,
iki dilli alanlar, capraz referanslar), uygulama dosyasinin logo/ayar
anahtarlari, karsilama sihirbazi ile senkronizasyon ve (ekran varsa)
arayuzun arama/kategori/terim gezintisinde hatasiz calismasi.

Calistirma:  python3 tests/test_gsd.py
"""
from __future__ import annotations

import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot")
GSD = os.path.join(INC, "opt/carotos/gsd")
ORTAK = os.path.join(INC, "opt/carotos/ortak")
for _y in (ORTAK, GSD):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import terimler  # noqa: E402


# ---------------------------------------------------------------------------
class IcerikTesti(unittest.TestCase):
    """terimler/ altindaki sozlugun yapisal dogrulugu."""

    @classmethod
    def setUpClass(cls):
        cls.tumu = terimler.tumu()
        cls.idler = {t["id"] for t in cls.tumu}

    def test_en_az_yuz_elli_terim(self):
        self.assertGreaterEqual(len(self.tumu), 150)

    def test_kimlikler_benzersiz(self):
        kimlikler = [t["id"] for t in self.tumu]
        self.assertEqual(len(kimlikler), len(set(kimlikler)))

    def test_her_terim_zorunlu_alanlari_tasir(self):
        for t in self.tumu:
            for alan in ("id", "baslik", "kisa", "aciklama", "kategori"):
                self.assertIn(alan, t, t.get("id"))
            self.assertIn(t["kategori"], terimler.SIRA, t["id"])

    def test_iki_dilli_alanlar_tam(self):
        for t in self.tumu:
            for alan in ("baslik", "kisa", "aciklama"):
                m = t[alan]
                self.assertIsInstance(m, dict, (t["id"], alan))
                self.assertEqual(set(m), {"tr", "en"}, (t["id"], alan))
                self.assertTrue(m["tr"].strip(), (t["id"], alan))
                self.assertTrue(m["en"].strip(), (t["id"], alan))

    def test_ornek_varsa_duz_metin_ve_dolu(self):
        for t in self.tumu:
            if "ornek" in t:
                self.assertIsInstance(t["ornek"], str, t["id"])
                self.assertTrue(t["ornek"].strip(), t["id"])

    def test_ilgili_referanslari_gecerli(self):
        for t in self.tumu:
            for ref in t.get("ilgili", []):
                self.assertIn(ref, self.idler, (t["id"], ref))

    def test_kategoriler_sira_ile_tutarli(self):
        self.assertEqual(set(terimler.KATEGORILER), set(terimler.SIRA))
        for kat, bilgi in terimler.KATEGORILER.items():
            self.assertEqual(set(bilgi["ad"]), {"tr", "en"}, kat)
            self.assertIn(bilgi["renk"], ("kirmizi", "sari", "yesil", "vurgu", "mavi", "gri"), kat)

    def test_her_kategoride_yeterli_terim_var(self):
        from collections import Counter
        sayim = Counter(t["kategori"] for t in self.tumu)
        for kat in terimler.SIRA:
            self.assertGreaterEqual(sayim[kat], 15, kat)

    def test_tekrar_cagrildiginda_ayni_sonuc(self):
        # tumu() her cagrildiginda yeniden hesaplanir; sonuclar tutarli olmali
        self.assertEqual(len(terimler.tumu()), len(self.tumu))


# ---------------------------------------------------------------------------
class UygulamaDosyasiTesti(unittest.TestCase):
    """carotos-gsd.py: logo_bul(), ayar anahtarlari, Turkce siralama."""

    @classmethod
    def setUpClass(cls):
        yol = os.path.join(GSD, "carotos-gsd.py")
        mod = {"__file__": yol, "__name__": "carotos_gsd_test_mod"}
        with open(yol, encoding="utf-8") as fh:
            kaynak = fh.read()
        kaynak = kaynak.replace('if __name__ == "__main__":\n    main()', "")
        exec(compile(kaynak, yol, "exec"), mod)
        cls.mod = mod

    def test_logo_bul_gercek_bir_dosyaya_erisir(self):
        logo = self.mod["logo_bul"]()
        self.assertIsNotNone(logo, "logo_bul() None dondu; SVG/PNG bulunamadi")
        self.assertTrue(os.path.isfile(logo), logo)

    def test_varsayilan_ayarlar_dil_tema_anahtarlarini_kullanir(self):
        self.assertEqual(set(self.mod["DEFAULT_SETTINGS"]), {"dil", "tema"})
        self.assertIn(self.mod["DEFAULT_SETTINGS"]["dil"], ("tr", "en"))
        self.assertIn(self.mod["DEFAULT_SETTINGS"]["tema"], ("dark", "light"))

    def test_turkce_siralama_anahtari_32_benzersiz_harf(self):
        harfler = self.mod["_TR_SIRA_HARF"]
        self.assertEqual(len(harfler), 32)
        self.assertEqual(len(set(harfler)), 32)

    def test_turkce_siralama_dogru_sirada(self):
        anahtar = self.mod["_tr_anahtar"]
        # Turkce alfabede doğru sira: ...s, ş, t... ve ...o, ö, p...
        self.assertLess(anahtar("sat"), anahtar("şat"))
        self.assertLess(anahtar("şat"), anahtar("tat"))
        self.assertLess(anahtar("ot"), anahtar("öt"))
        self.assertLess(anahtar("öt"), anahtar("pt"))

    def test_kucult_turkce_buyuk_harfleri_dogru_cevirir(self):
        kucult = self.mod["_kucult"]
        self.assertEqual(kucult("İSTANBUL"), "istanbul")
        self.assertEqual(kucult("IŞIK"), "ışık")
        self.assertEqual(kucult("VPN"), "vpn")


# ---------------------------------------------------------------------------
class SiblingAyarSenkronTesti(unittest.TestCase):
    """welcome/carotos-welcome.py: carotos-gsd SIBLING_CONFIGS'te, kendi
    dil/tema anahtarlariyla ve kaynaklar sayfasinda bir eylem karti ile."""

    @classmethod
    def setUpClass(cls):
        yol = os.path.join(INC, "opt/carotos/welcome/carotos-welcome.py")
        if not os.path.isfile(yol):
            raise unittest.SkipTest("carotos-welcome.py bulunamadi")
        with open(yol, encoding="utf-8") as fh:
            cls.kaynak = fh.read()

    def test_gsd_sibling_configs_icinde(self):
        m = re.search(r"SIBLING_CONFIGS\s*=\s*\[(.*?)\]", self.kaynak, re.S)
        self.assertIsNotNone(m)
        self.assertIn('"carotos-gsd"', m.group(1))

    def test_gsd_icin_dil_tema_anahtar_eslemesi_var(self):
        self.assertIn('folder == "carotos-gsd"', self.kaynak)
        blok = self.kaynak[self.kaynak.index('folder == "carotos-gsd"'):]
        blok = blok[:blok.index("\n\n")] if "\n\n" in blok else blok[:400]
        self.assertIn('data["dil"]', blok)
        self.assertIn('data["tema"]', blok)

    def test_resources_sayfasinda_gsd_eylemi_var(self):
        self.assertIn('"action"', self.kaynak)
        self.assertIn("/opt/carotos/gsd/carotos-gsd.py", self.kaynak)


# ---------------------------------------------------------------------------
class TemaVurgusuTesti(unittest.TestCase):
    """ortak/tema.py: VURGULAR sozlugunde 'gsd' anahtari tanimli mi."""

    @classmethod
    def setUpClass(cls):
        yol = os.path.join(ORTAK, "tema.py")
        if not os.path.isfile(yol):
            raise unittest.SkipTest("tema.py bulunamadi")
        with open(yol, encoding="utf-8") as fh:
            cls.kaynak = fh.read()

    def test_gsd_vurgusu_tanimli(self):
        m = re.search(r"VURGULAR\s*=\s*\{(.*?)\}", self.kaynak, re.S)
        self.assertIsNotNone(m)
        self.assertIn('"gsd"', m.group(1))


# ---------------------------------------------------------------------------
@unittest.skipUnless(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"),
                     "ekran yok (xvfb-run ile calistirin)")
class ArayuzDumanTesti(unittest.TestCase):
    """Pencereyi acar; arama, kategori filtresi, terim secimi, ilgili
    terime atlama ve dil/tema degisimini dener. Yakalanmayan istisna
    olmamali."""

    def test_arama_kategori_secim_hatasiz_calisir(self):
        import tempfile
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, GLib

        ev = tempfile.mkdtemp(prefix="gsd-ev-")
        eski_home = os.environ.get("HOME")
        os.environ["HOME"] = ev
        self.addCleanup(lambda: os.environ.__setitem__("HOME", eski_home) if eski_home else None)

        yol = os.path.join(GSD, "carotos-gsd.py")
        mod = {"__file__": yol, "__name__": "carotos_gsd_smoke_mod"}
        with open(yol, encoding="utf-8") as fh:
            kaynak = fh.read()
        kaynak = kaynak.replace('if __name__ == "__main__":\n    main()', "")
        exec(compile(kaynak, yol, "exec"), mod)
        Uygulama = mod["Uygulama"]

        app = Uygulama()
        self.assertIsNone(app._aktif_id)   # bos durumla acilir
        hatalar = []

        adimlar = [
            lambda: (app.arama.set_text("ssh"), app.arama.emit("search-changed")),
            lambda: (app.arama.set_text(""), app.arama.emit("search-changed")),
            lambda: app.kat_dugmeleri["algoritma"].set_active(True),
            lambda: app.kat_dugmeleri["tumu"].set_active(True),
            lambda: app._terime_git("rsa"),
            lambda: app.dil_kutu.set_active_id("en"),
            lambda: app._tema_degistir(),
        ]

        def adima_git(i=0):
            if i >= len(adimlar):
                GLib.timeout_add(150, lambda: Gtk.main_quit())
                return False
            try:
                adimlar[i]()
            except Exception as h:    # noqa: BLE001
                hatalar.append((i, repr(h)))
            GLib.timeout_add(40, lambda: adima_git(i + 1))
            return False

        GLib.timeout_add(100, lambda: adima_git())
        GLib.timeout_add(8000, Gtk.main_quit)
        Gtk.main()
        app.destroy()
        self.assertEqual(hatalar, [])


if __name__ == "__main__":
    unittest.main()
