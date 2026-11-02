#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kurulu sistemin onyukleme ayarlari: GRUB cekirdek parametreleri.

Kurucu preseed'deki add-kernel-opts degerini okuyor ama /etc/default/grub'a
yazmiyor; ayar /etc/default/grub.d/carotos.cfg ile verilir. Preseed ile bu
dosya ayni parametreleri tasimali, ve basarisiz servisler gizlenmemeli.

Calistirma:  python3 tests/test_onyukleme.py
"""
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRUB_CFG = os.path.join(KOK, "config", "includes.chroot", "etc", "default", "grub.d", "carotos.cfg")
GRUB_ANA = os.path.join(KOK, "config", "includes.chroot", "etc", "default", "grub")
PRESEED = os.path.join(KOK, "config", "includes.installer", "preseed.cfg")


def oku(yol):
    with open(yol, "rb") as f:
        return f.read().replace(b"\r\n", b"\n").decode("utf-8")


def grub_parametreleri(yol=GRUB_CFG):
    m = re.search(r'^GRUB_CMDLINE_LINUX_DEFAULT="([^"]*)"', oku(yol), re.M)
    assert m, "GRUB_CMDLINE_LINUX_DEFAULT tanimli degil"
    return m.group(1).split()


def preseed_parametreleri():
    m = re.search(r"^d-i debian-installer/add-kernel-opts string (.+)$", oku(PRESEED), re.M)
    assert m, "add-kernel-opts tanimli degil"
    return m.group(1).split()


class GrubAyariTesti(unittest.TestCase):
    def test_sessiz_acilis_parametreleri(self):
        p = grub_parametreleri()
        for beklenen in ("quiet", "loglevel=3", "systemd.show_status=auto"):
            self.assertIn(beklenen, p)

    def test_basarisiz_servisler_gizlenmez(self):
        # show_status=false/no bir servis hatasini da gizler
        for liste in (grub_parametreleri(), preseed_parametreleri()):
            self.assertNotIn("systemd.show_status=false", liste)
            self.assertNotIn("systemd.show_status=0", liste)

    def test_preseed_ve_grub_ayni_parametreleri_tasir(self):
        fark = set(preseed_parametreleri()) - set(grub_parametreleri())
        self.assertEqual(fark, set(), "preseed'de olup grub.d'de olmayan: %s" % sorted(fark))

    def test_etc_default_grub_ship_edilmez(self):
        # /etc/default/grub grub paketinin yapilandirma dosyasidir (ucf). ISO'ya biz
        # koyarsak kurucu grub paketini kurarken "yerel degisiklik var, ne yapayim?"
        # diye sorar (ve her grub guncellemesinde kullanici ayni soruyu gorur).
        # Ayarlar grub.d altindaki parcada tutulur.
        self.assertFalse(os.path.exists(GRUB_ANA),
                         "includes.chroot/etc/default/grub kaldirilmali; ayar grub.d/carotos.cfg'de")

    def test_dagitici_adi_os_release_den(self):
        # Menu girisleri "Debian GNU/Linux" degil dagitimin adini (CarotOS) tasimali
        m = re.search(r"^GRUB_DISTRIBUTOR=(.+)$", oku(GRUB_CFG), re.M)
        self.assertIsNotNone(m, "GRUB_DISTRIBUTOR grub.d/carotos.cfg'de tanimli olmali")
        self.assertIn("/etc/os-release", m.group(1))
        self.assertIn("${NAME}", m.group(1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
