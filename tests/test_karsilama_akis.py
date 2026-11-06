#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Karşılama merkez-kol akışı gerçek pencerede (ekran yoksa atlanır).

Calistirma:  xvfb-run -a python3 tests/test_karsilama_akis.py
"""
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_dil_uygulamalar import EKRAN, UygulamaDilTabani  # noqa: E402


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class KarsilamaAkisTesti(UygulamaDilTabani):
    def setUp(self):
        super().setUp()
        self.m = self.modul("welcome")
        self.kayit = {"uygula": 0, "kapat": 0}
        self.p = self.m.WelcomeWindow(self.m.load_settings())
        self.addCleanup(self.p.destroy)
        self.p.apply_choices = lambda: self.kayit.__setitem__("uygula", self.kayit["uygula"] + 1)   # sisteme dokunma
        self.p.close = lambda: self.kayit.__setitem__("kapat", self.kayit["kapat"] + 1)
        self.p.show_all()
        self.p.refresh()
        self.pompala()

    # -- yardimcilar -----------------------------------------------------------------
    def tikla(self, dugme):
        dugme.emit("clicked")
        self.pompala()

    def sayfa(self):
        return self.p.stack.get_visible_child_name()

    def etiket(self, anahtar):
        return self.m.UI[anahtar][self.p.lang]

    def nokta_sayisi(self):
        return len(self.p.dots.get_children())

    def hub_a_git(self):
        for _ in range(3):
            self.tikla(self.p.next_btn)
        self.assertEqual(self.sayfa(), "hub")

    def ayar(self):
        with open(self.m.CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)

    # -- baslangic ---------------------------------------------------------------------
    def test_baslangic_zorunlu_ve_atlanamaz(self):
        self.assertEqual(self.sayfa(), "welcome")
        self.assertFalse(self.p.back_btn.get_sensitive())
        self.assertFalse(self.p.skip_btn.get_visible())
        self.assertEqual(self.nokta_sayisi(), 3)
        self.assertEqual(self.p.next_btn.get_label(), self.etiket("next"))
        self.tikla(self.p.next_btn)
        self.assertEqual(self.sayfa(), "appearance")
        self.assertTrue(self.p.back_btn.get_sensitive())
        self.tikla(self.p.next_btn)
        self.assertEqual(self.sayfa(), "wallpaper")
        self.assertFalse(self.p.skip_btn.get_visible())

    # -- hub ---------------------------------------------------------------------------------
    def test_hub_kartlar_ve_dugmeler(self):
        self.hub_a_git()
        self.assertTrue(self.p.skip_btn.get_visible())
        self.assertEqual(self.p.skip_btn.get_label(), self.etiket("skip_topics"))
        self.assertEqual(self.p.next_btn.get_label(), self.etiket("to_end"))
        self.assertEqual(self.nokta_sayisi(), 0)
        self.assertEqual(sorted(self.p.hub_kartlari), sorted(k["id"] for k in self.m.gezinme.KONULAR))

    def test_konu_acilir_bitirilir_ve_isaretlenir(self):
        self.hub_a_git()
        self.p._on_konu_tikla(None, None, "etik")
        self.pompala()
        self.assertEqual(self.sayfa(), "etik")
        self.assertEqual(self.p.next_btn.get_label(), self.etiket("finish_topic"))
        self.assertTrue(self.p.skip_btn.get_visible())
        self.assertEqual(self.nokta_sayisi(), 1)
        self.tikla(self.p.next_btn)                                   # konuyu bitir
        self.assertEqual(self.sayfa(), "hub")
        self.assertIn("etik", self.ayar()["biten_konular"])          # kalici
        alt, _ = self.p.hub_kartlari["etik"]
        self.assertTrue(alt.get_text().startswith("✓"))
        alt2, _ = self.p.hub_kartlari["sistem"]
        self.assertFalse(alt2.get_text().startswith("✓"))

    def test_cok_sayfali_konu_ilerler(self):
        self.hub_a_git()
        self.p._on_konu_tikla(None, None, "sistem")
        self.pompala()
        sayfalar = [k for k in self.m.gezinme.KONULAR if k["id"] == "sistem"][0]["sayfalar"]
        self.assertEqual(self.nokta_sayisi(), len(sayfalar))
        for n, kimlik in enumerate(sayfalar):
            self.assertEqual(self.sayfa(), kimlik)
            beklenen = "finish_topic" if n == len(sayfalar) - 1 else "next"
            self.assertEqual(self.p.next_btn.get_label(), self.etiket(beklenen))
            self.tikla(self.p.next_btn)
        self.assertEqual(self.sayfa(), "hub")

    def test_konudan_geri_hub_a_doner_ve_bitirmez(self):
        self.hub_a_git()
        self.p._on_konu_tikla(None, None, "yazilim")
        self.pompala()
        self.tikla(self.p.back_btn)
        self.assertEqual(self.sayfa(), "hub")
        self.assertNotIn("yazilim", self.ayar().get("biten_konular", []))

    # -- atla ve son ---------------------------------------------------------------------------
    def test_konulari_atla_son_sayfaya_goturur_ve_bitir_kapatir(self):
        self.hub_a_git()
        self.p._on_konu_tikla(None, None, "koruma")
        self.pompala()
        self.tikla(self.p.skip_btn)
        self.assertEqual(self.sayfa(), "resources")
        self.assertEqual(self.p.next_btn.get_label(), self.etiket("finish"))
        self.assertFalse(self.p.skip_btn.get_visible())
        self.assertEqual(self.kayit, {"uygula": 0, "kapat": 0})
        self.tikla(self.p.next_btn)
        self.assertEqual(self.kayit, {"uygula": 1, "kapat": 1})      # secimler uygulanir, pencere kapanir

    def test_sondan_geri_hub_a(self):
        self.hub_a_git()
        self.tikla(self.p.next_btn)                                   # hub'da "Sona gec"
        self.assertEqual(self.sayfa(), "resources")
        self.tikla(self.p.back_btn)
        self.assertEqual(self.sayfa(), "hub")

    # -- kalicilik ve dil -----------------------------------------------------------------------------
    def test_biten_konular_yeni_pencerede_gorunur(self):
        self.hub_a_git()
        self.p._on_konu_tikla(None, None, "etik")
        self.tikla(self.p.next_btn)
        yeni = self.m.WelcomeWindow(self.m.load_settings())
        self.addCleanup(yeni.destroy)
        yeni.show_all()
        yeni.sayfaya_git("hub")
        self.pompala()
        self.assertEqual(yeni.gezinme.biten_konular(), ["etik"])
        self.assertTrue(yeni.hub_kartlari["etik"][0].get_text().startswith("✓"))

    def test_dil_degisince_ayni_sayfada_kalir(self):
        self.hub_a_git()
        self.p._on_konu_tikla(None, None, "sistem")
        self.tikla(self.p.next_btn)
        self.assertEqual(self.sayfa(), "desktop")
        for kod in ("en", "tr"):
            self.p.lang_combo.set_active_id(kod)
            self.pompala()
            self.assertEqual(self.sayfa(), "desktop")
            self.assertEqual(self.p.next_btn.get_label(), self.etiket("next"))

    def test_bozuk_biten_konular_ayari_cokertmez(self):
        os.makedirs(os.path.dirname(self.m.CONFIG_FILE), exist_ok=True)
        with open(self.m.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"biten_konular": "bozuk"}, f)
        ayar = self.m.load_settings()
        self.assertEqual(ayar["biten_konular"], [])
        self.assertEqual(self.m.gezinme.Gezinme(ayar["biten_konular"]).biten_konular(), [])


if __name__ == "__main__":
    unittest.main()
