#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ag gizliligi ve zram yapilandirma dosyalari (GTK/ag gerektirmez).

NetworkManager varsayilanlari (rastgele/sabit MAC, DHCP'de makine adi yok,
IPv6 gecici adres), sysctl, zram takas ayari ve paket listesi bildirilen
degerlerle uyumlu mu, yazim hatasi var mi denetlenir. Gercek davranis (MAC'in
degismesi, zram'in acilmasi) VM'de ayrica elle/ISO'da dogrulanir.

Calistirma (depo kokunden):  python3 tests/test_ag_gizliligi.py
"""
import configparser
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROOT = os.path.join(KOK, "config", "includes.chroot")
NM = os.path.join(CHROOT, "etc/NetworkManager/conf.d/90-carotos-gizlilik.conf")
SYSCTL = os.path.join(CHROOT, "etc/sysctl.d/90-carotos-gizlilik.conf")
ZRAM = os.path.join(CHROOT, "etc/systemd/zram-generator.conf.d/90-carotos.conf")
LISTE = os.path.join(KOK, "config", "package-lists", "carotos.list.chroot")


def ini(yol):
    p = configparser.ConfigParser(interpolation=None, strict=True)
    p.optionxform = str          # anahtarlarin buyuk/kucuk harfi korunur
    with open(yol, encoding="utf-8") as fh:
        p.read_file(fh)
    return p


class NetworkManagerTesti(unittest.TestCase):
    def setUp(self):
        self.c = ini(NM)

    def test_baglanti_varsayilanlari(self):
        b = self.c["connection"]
        self.assertIn(b["wifi.cloned-mac-address"], ("stable", "random"))
        self.assertIn(b["ethernet.cloned-mac-address"], ("stable", "random"))
        self.assertEqual(b["ipv4.dhcp-send-hostname"], "false")
        self.assertEqual(b["ipv6.dhcp-send-hostname"], "false")
        self.assertEqual(b["ipv6.ip6-privacy"], "2")

    def test_gercek_donanim_adresi_korunmuyor(self):
        # "preserve" (NetworkManager varsayilani) gercek MAC'i aga gosterir.
        for anahtar in ("wifi.cloned-mac-address", "ethernet.cloned-mac-address"):
            self.assertNotIn(self.c["connection"][anahtar], ("preserve", "permanent"))

    def test_tarama_rastgele_mac(self):
        self.assertEqual(self.c["device"]["wifi.scan-rand-mac-address"], "yes")

    def test_yalniz_bilinen_bolum_ve_anahtarlar(self):
        # NetworkManager.conf(5) [connection] ve [device] bolumlerinde gecerli
        # anahtarlar; yazim hatasi sessizce yok sayilirdi.
        self.assertEqual(set(self.c.sections()), {"connection", "device"})
        izinli_baglanti = {"wifi.cloned-mac-address", "ethernet.cloned-mac-address",
                           "ipv4.dhcp-send-hostname", "ipv6.dhcp-send-hostname",
                           "ipv6.ip6-privacy", "wifi.powersave"}
        self.assertLessEqual(set(self.c["connection"]), izinli_baglanti)
        self.assertLessEqual(set(self.c["device"]), {"wifi.scan-rand-mac-address"})

    def test_ana_yapilandirma_dosyasina_dokunulmuyor(self):
        # Paketin /etc/NetworkManager/NetworkManager.conf dosyasi (conffile)
        # ISO'ya konmaz; yalnizca conf.d parcasi (GRUB dersi: kurucu "yerel
        # degisiklik var" diye sormasin).
        self.assertFalse(os.path.exists(os.path.join(CHROOT, "etc/NetworkManager/NetworkManager.conf")))


class SysctlTesti(unittest.TestCase):
    def test_ipv6_gecici_adres(self):
        satirlar = {}
        for s in open(SYSCTL, encoding="utf-8"):
            s = s.strip()
            if s and not s.startswith("#"):
                k, _, v = s.partition("=")
                satirlar[k.strip()] = v.strip()
        self.assertEqual(satirlar, {"net.ipv6.conf.all.use_tempaddr": "2",
                                    "net.ipv6.conf.default.use_tempaddr": "2"})


class ZramTesti(unittest.TestCase):
    def setUp(self):
        self.c = ini(ZRAM)

    def test_zram0_ayarlari(self):
        z = self.c["zram0"]
        self.assertRegex(z["zram-size"], r"^min\(ram / \d+, \d+\)$")
        self.assertIn(z["compression-algorithm"], ("zstd", "lz4", "lzo-rle"))
        self.assertGreater(int(z["swap-priority"]), 0)   # disk takasindan (negatif) once dolsun

    def test_paketin_kendi_dosyasi_ezilmiyor(self):
        # /etc/systemd/zram-generator.conf yerine .conf.d parcasi kullanilir
        # (belgelenmis dropin yolu; ana dosyayi paket/yonetici sahipler).
        self.assertTrue(ZRAM.endswith("zram-generator.conf.d/90-carotos.conf"))
        self.assertFalse(os.path.exists(os.path.join(CHROOT, "etc/systemd/zram-generator.conf")))
        self.assertEqual(self.c.sections(), ["zram0"])


class PaketListesiTesti(unittest.TestCase):
    def setUp(self):
        self.paketler = [s.strip() for s in open(LISTE, encoding="utf-8") if s.strip() and not s.startswith("#")]

    def test_yeni_paketler_bir_kez_var(self):
        for ad in ("systemd-zram-generator", "libu2f-udev"):
            self.assertEqual(self.paketler.count(ad), 1, ad)

    def test_listede_tekrar_yok_ve_secure_boot_paketleri_yok(self):
        self.assertEqual(len(self.paketler), len(set(self.paketler)))
        for yasak in ("shim-signed", "grub-efi-amd64-signed"):   # CLAUDE.md: olmamali
            self.assertNotIn(yasak, self.paketler)

    def test_gecerli_paket_adlari(self):
        for ad in self.paketler:
            self.assertRegex(ad, r"^[a-z0-9][a-z0-9+.\-]+$")


if __name__ == "__main__":
    unittest.main()
