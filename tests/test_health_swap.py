#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sistem Sagligi: diskte sifresiz swap denetimi (GTK gerektirmez, root gerektirmez).

Calistirma:  python3 tests/test_health_swap.py
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_health_faz1 as F  # noqa: E402

H = F.modulu_yukle()

BASLIK = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n"
ZRAM = "/dev/zram0                              partition\t1000000\t\t0\t\t100\n"
BOLUM = "/dev/sda5                               partition\t2000000\t\t0\t\t-2\n"
LVM = "/dev/mapper/vg-swap                      partition\t2000000\t\t0\t\t-2\n"
DOSYA = "/swapfile                               file\t\t2000000\t\t0\t\t-3\n"


class SwapAyristirmaTesti(unittest.TestCase):
    def test_baslik_atlanir_ve_cihazlar_okunur(self):
        self.assertEqual(H.swap_cihazlari(BASLIK + ZRAM + BOLUM),
                         [("/dev/zram0", "partition"), ("/dev/sda5", "partition")])
        self.assertEqual(H.swap_cihazlari(""), [])
        self.assertEqual(H.swap_cihazlari(None), [])
        self.assertEqual(H.swap_cihazlari(BASLIK + DOSYA), [("/swapfile", "file")])


class SwapDenetimiTesti(unittest.TestCase):
    def calistir(self, metin, sifreli):
        return H.check_swap_encryption(metin, lambda yol, tur: sifreli(yol, tur))

    def test_swap_yok_tamam(self):
        r = self.calistir(BASLIK, lambda y, t: self.fail("cagrilmamali"))
        self.assertEqual(r["status"], H.OK)

    def test_yalniz_zram_tamam_ve_disk_sorgulanmaz(self):
        r = self.calistir(BASLIK + ZRAM, lambda y, t: self.fail("zram icin sorulmamali"))
        self.assertEqual(r["status"], H.OK)
        self.assertIn("zram", r["detail"]["en"])

    def test_sifresiz_bolum_uyari(self):
        r = self.calistir(BASLIK + ZRAM + BOLUM, lambda y, t: False)
        self.assertEqual(r["status"], H.WARN)
        self.assertIn("/dev/sda5", r["detail"]["tr"])
        self.assertIn("/dev/sda5", r["detail"]["en"])

    def test_sifreli_tamam(self):
        r = self.calistir(BASLIK + LVM, lambda y, t: True)
        self.assertEqual(r["status"], H.OK)

    def test_karisik_biri_sifresizse_uyari(self):
        r = self.calistir(BASLIK + LVM + DOSYA, lambda y, t: y.startswith("/dev/mapper"))
        self.assertEqual(r["status"], H.WARN)
        self.assertIn("/swapfile", r["detail"]["en"])
        self.assertNotIn("/dev/mapper", r["detail"]["en"])

    def test_belirlenemezse_bilgi(self):
        r = self.calistir(BASLIK + BOLUM, lambda y, t: None)
        self.assertEqual(r["status"], H.INFO)

    def test_sifresiz_varsa_belirsiz_onde_gelmez(self):
        r = self.calistir(BASLIK + BOLUM + DOSYA, lambda y, t: False if t == "partition" else None)
        self.assertEqual(r["status"], H.WARN)


class SwapKayitTesti(unittest.TestCase):
    def kayit(self):
        return [c for c in H.CHECKS if c["id"] == "swap_crypt"][0]

    def test_kayit_ve_metinler(self):
        c = self.kayit()
        self.assertEqual(c["category"], "storage")
        for anahtar in ("title", "why"):
            self.assertEqual(set(c[anahtar]), {"tr", "en"})
            self.assertTrue(c[anahtar]["en"].strip() and c[anahtar]["tr"].strip())
        self.assertIs(c["func"], H.check_swap_encryption)

    def test_eylem_onay_ister_ve_zrami_kapatmaz(self):
        a = self.kayit()["action"]
        self.assertTrue(a["confirm"])
        self.assertEqual(set(a["label"]), {"tr", "en"})
        # yalniz zram olmayan swap kapatilir; fstab yedeklenir
        self.assertIn("!~ /zram/", a["cmd"])
        self.assertIn("sed -i.carotos-yedek", a["cmd"])
        self.assertNotIn("swapoff -a", a["cmd"])

    def test_gercek_sistemde_cokmez(self):
        # /proc/swaps okunabilir ya da degil: her durumda gecerli bir sonuc doner
        r = H.check_swap_encryption()
        self.assertIn(r["status"], (H.OK, H.WARN, H.INFO))
        self.assertTrue(r["detail"]["en"])


if __name__ == "__main__":
    unittest.main()
