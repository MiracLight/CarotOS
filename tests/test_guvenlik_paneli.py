#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guvenlik Paneli testleri (GTK gerektirmez).

Modul en ustte gi/Gtk iceri aktardigi icin dogrudan import edilmez; test,
kaynagi ayristirip yalnizca ilgili islevleri / sozlugu cikarir.

Calistirma:  python3 tests/test_guvenlik_paneli.py
"""
import ast
import os
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOD = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos",
                   "security-panel", "carotos-security-panel.py")


def kaynak_agaci():
    with open(KOD, "rb") as f:
        return ast.parse(f.read().decode("utf-8"))


def islev(ad):
    secilen = [n for n in kaynak_agaci().body if isinstance(n, ast.FunctionDef) and n.name == ad]
    assert secilen, "islev bulunamadi: " + ad
    ad_alani = {}
    exec(compile(ast.Module(body=secilen, type_ignores=[]), KOD, "exec"), ad_alani)
    return ad_alani[ad]


def sabit(ad):
    for n in kaynak_agaci().body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == ad for t in n.targets):
            return ast.literal_eval(n.value)
    raise AssertionError(ad + " bulunamadi")


class KokArgumanTesti(unittest.TestCase):
    """pkexec parola penceresi argumanlari gostermez; kullanici metni root'ta secenek olmamali."""

    def setUp(self):
        self.guvenli = islev("root_icin_guvenli_mi")

    def test_secenek_gibi_degerler_reddedilir(self):
        for degerler in (
            {"iface": "eth0", "count": "50", "filter": "-z /bin/sh"},     # tcpdump: root komut calistirir
            {"iface": "eth0", "count": "50", "filter": "port 80 -w /etc/passwd"},
            {"iface": "-w", "count": "5"},
            {"target": "--script=/tmp/kotu.nse"},                         # nmap NSE
            {"filter": "  -G 1  "},
        ):
            with self.subTest(degerler=degerler):
                self.assertFalse(self.guvenli(degerler))

    def test_normal_degerler_kabul_edilir(self):
        for degerler in (
            {"iface": "eth0", "count": "50", "filter": "port 80"},
            {"iface": "wlan0", "count": "10", "filter": "not port 22 and host 192.168.1.1"},
            {"target": "192.168.1.0/24"},
            {"action_key": 1, "port": "22"},                              # combo indeksi int
            {"iface": "eth0", "filter": ""},
        ):
            with self.subTest(degerler=degerler):
                self.assertTrue(self.guvenli(degerler))

    def test_hata_metni_iki_dilde(self):
        metin = sabit("STRINGS")["root_arg_hata"]
        self.assertTrue(metin["tr"] and metin["en"])


class MetinTesti(unittest.TestCase):
    def test_tr_ve_en_anahtarlari_ayni(self):
        for anahtar, deger in sabit("STRINGS").items():
            with self.subTest(anahtar=anahtar):
                self.assertEqual(set(deger), {"tr", "en"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
