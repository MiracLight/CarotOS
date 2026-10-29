#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon: her gorevin bilgi metni (gorev_bilgi.py) iki dilde tanimli olmali,
gorev basliklari benzersiz olmali ve gelistirici/yapay zeka agzi tasimamalidir.

Kullanim (depo kokunden):  python3 tests/test_poligon_gorev_bilgi.py
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot/opt/carotos")
GOREVLER = Path(INC) / "poligon" / "gorevler"
for _y in (os.path.join(INC, "poligon"), os.path.join(INC, "ortak")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import gorev_bilgi  # noqa: E402

ALANLAR = ("amac", "kazanim", "kullanim")


def _gorevler():
    return [json.loads(f.read_text(encoding="utf-8"))
            for f in sorted(GOREVLER.glob("*.json"))]


class GorevBilgiTesti(unittest.TestCase):
    def test_her_gorevin_bilgisi_iki_dilde_var(self):
        for g in _gorevler():
            for dil in ("tr", "en"):
                kayit = gorev_bilgi.bilgi_getir(g["id"], dil)
                self.assertIsNotNone(kayit, f"{g['id']} bilgisi yok")
                for alan in ALANLAR:
                    self.assertTrue(kayit.get(alan, "").strip(),
                                    f"{g['id']}/{dil}/{alan} bos")

    def test_fazladan_bilgi_kaydi_yok(self):
        idler = {g["id"] for g in _gorevler()}
        self.assertEqual(set(gorev_bilgi.BILGI) - idler, set())

    def test_basliklar_benzersiz(self):
        for dil in ("tr", "en"):
            basliklar = [g["baslik"][dil] for g in _gorevler()]
            self.assertEqual(len(basliklar), len(set(basliklar)), dil)

    def test_cesitlilik_metni(self):
        for g in _gorevler():
            for dil in ("tr", "en"):
                self.assertTrue(gorev_bilgi.cesitlilik_getir(g["id"], dil).strip())
        self.assertIn("20 farklı", gorev_bilgi.cesitlilik_getir("kodlama-02", "tr"))
        self.assertIn("20 different", gorev_bilgi.cesitlilik_getir("loganaliz-01", "en"))
        self.assertIn("Tek soru", gorev_bilgi.cesitlilik_getir("nmap-01", "tr"))

    def test_alan_etiketleri_tam(self):
        for dil in ("tr", "en"):
            self.assertEqual(set(gorev_bilgi.ALAN_ETIKETLERI[dil]), set(ALANLAR))

    def test_sablon_basliklari_gorev_basligini_icerir(self):
        import soru_sablonlari as ss
        gorevler = {g["id"]: g for g in _gorevler()}
        for gid, sablon in ss.SABLONLAR.items():
            for dil in ("tr", "en"):
                self.assertIn(gorevler[gid]["baslik"][dil], sablon["baslik"][dil])


if __name__ == "__main__":
    unittest.main()
