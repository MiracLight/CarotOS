#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel ayar ve yazi tipi testleri: Japonca (CJK) karakterler.

Sistem dili Japonca secildiginde karakterler kutu (tofu) olarak gorunmemeli:
CJK yazi tipi pakette olmali ve ja_JP yerel ayari uretilmeli.

Calistirma:  python3 tests/test_yerel.py
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAKETLER = os.path.join(KOK, "config", "package-lists", "carotos.list.chroot")
LOCALE_GEN = os.path.join(KOK, "config", "includes.chroot", "etc", "locale.gen")


def satirlar(yol):
    with open(yol, "rb") as f:
        ham = f.read().replace(b"\r\n", b"\n").decode("utf-8")
    return [s.strip() for s in ham.split("\n") if s.strip() and not s.lstrip().startswith("#")]


class JaponcaTesti(unittest.TestCase):
    def test_cjk_yazi_tipi_paketi_var(self):
        self.assertIn("fonts-noto-cjk", satirlar(PAKETLER))

    def test_ja_locale_uretilir_ve_varsayilanlar_korunur(self):
        locale_gen = satirlar(LOCALE_GEN)
        self.assertIn("ja_JP.UTF-8 UTF-8", locale_gen)
        # mevcut diller bozulmamali
        self.assertIn("tr_TR.UTF-8 UTF-8", locale_gen)
        self.assertIn("en_US.UTF-8 UTF-8", locale_gen)


CANLI_AYAR = os.path.join(KOK, "config", "includes.chroot", "etc", "live", "config.conf.d", "carotos.conf")


def canli_ayarlar():
    ayarlar = {}
    for satir in satirlar(CANLI_AYAR):
        if "=" in satir:
            ad, deger = satir.split("=", 1)
            ayarlar[ad.strip()] = deger.strip().strip('"')
    return ayarlar


class SaatDilimiTesti(unittest.TestCase):
    """live-config varsayilan saat dilimi UTC'dir: Turkiye'de (UTC+3) saatin saat kismi
    3 saat geri gorunur, dakika dogru kalir."""

    def test_canli_oturum_saat_dilimi_ayarli(self):
        ayarlar = canli_ayarlar()
        self.assertIn("LIVE_TIMEZONE", ayarlar)
        self.assertEqual(ayarlar["LIVE_TIMEZONE"], "Europe/Istanbul")

    def test_hostname_ayari_korunur(self):
        self.assertEqual(canli_ayarlar().get("LIVE_HOSTNAME"), "carotos")


if __name__ == "__main__":
    unittest.main(verbosity=2)
