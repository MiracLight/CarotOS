#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Karsilama "Ag ve gizlilik" sayfasi (GTK kurulu degilse atlanir).

Sayfa var, kurulum akisindaki yeri dogru, iki dilli ve verdigi nmcli komutlari
NetworkManager varsayilan dosyasindaki gercek anahtarlarla tutarli.

Calistirma (depo kokunden):  python3 tests/test_karsilama_ag.py
"""
import configparser
import importlib.util
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WELCOME = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos",
                       "welcome", "carotos-welcome.py")
NM = os.path.join(KOK, "config", "includes.chroot", "etc", "NetworkManager",
                  "conf.d", "90-carotos-gizlilik.conf")


def pages():
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk  # noqa: F401
    except (ImportError, ValueError) as exc:
        raise unittest.SkipTest("GTK yok: %s" % exc)
    spec = importlib.util.spec_from_file_location("carotos_welcome_test", WELCOME)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PAGES


def metinler(sayfa):
    """Sayfadaki tum {tr,en} metin sozlukleri (baslik, alt baslik, govde)."""
    out = [sayfa["title"], sayfa["subtitle"]]
    for tur, yuk in sayfa["body"]:
        if tur in ("p", "note"):
            out.append(yuk)
        elif tur == "bullets":
            out.extend(yuk)
    return out


class AgSayfasiTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = pages()
        cls.ids = [p["id"] for p in cls.pages]
        cls.sayfa = next(p for p in cls.pages if p["id"] == "network")

    def test_gizlilik_konusunun_sayfasi(self):
        # Yeni akis (merkez-kol): welcome -> appearance -> wallpaper -> hub; ag sayfasi "Ag ve gizlilik" konusunda.
        self.assertEqual(self.ids[:4], ["welcome", "appearance", "wallpaper", "hub"])
        self.assertEqual(len(self.ids), len(set(self.ids)))
        sys.path.insert(0, os.path.dirname(WELCOME))
        import gezinme
        konu = next(k for k in gezinme.KONULAR if "network" in k["sayfalar"])
        self.assertEqual(konu["id"], "gizlilik")

    def test_her_metin_iki_dilde_dolu(self):
        for m in metinler(self.sayfa):
            self.assertEqual(set(m), {"tr", "en"})
            self.assertTrue(m["tr"].strip() and m["en"].strip())

    def test_komutlar_nm_yapilandirmasindaki_anahtarlarla_tutarli(self):
        c = configparser.ConfigParser(interpolation=None)
        c.optionxform = str
        c.read(NM, encoding="utf-8")
        anahtarlar = set(c["connection"])
        komutlar = [y for t, y in self.sayfa["body"] if t == "code"]
        self.assertEqual(len(komutlar), 2)
        for k in komutlar:
            m = re.fullmatch(r'nmcli connection modify "[^"]+" (\S+) permanent', k)
            self.assertIsNotNone(m, k)
            self.assertIn(m.group(1), anahtarlar)       # sayfadaki anahtar gercekten varsayilan olarak ayarli
        self.assertEqual({re.search(r' (\S+) permanent', k).group(1) for k in komutlar},
                         {"wifi.cloned-mac-address", "ethernet.cloned-mac-address"})

    def test_yasa_atfi_ve_asiri_vaat_yok(self):
        yasak = re.compile(r"TCK|StGB|CFAA|§|\bmadde\b|tam gizlilik sağlar|completely anonymous", re.I)
        for m in metinler(self.sayfa):
            for metin in m.values():
                self.assertFalse(yasak.search(metin), metin)
        son = self.sayfa["body"][-1]
        self.assertEqual(son[0], "note")
        self.assertIn("garanti", son[1]["tr"])           # dürüst sınırlama notu
        self.assertIn("not guarantee", son[1]["en"])


if __name__ == "__main__":
    unittest.main()
