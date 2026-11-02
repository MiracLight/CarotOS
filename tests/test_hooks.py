#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hook testleri: config/hooks/live altindaki betiklerin sozdizimi.

Her hook icin:
  - ilk satir #!/bin/sh mi,
  - `sh -n` ile sozdizimi gecerli mi,
  - shellcheck kuruluysa hata (error) duzeyinde bulgu yok mu.

0010/0050 gibi live-build'in kendi hook'larina giden sembolik baglar
(icerigi tek satir yol) atlanir. sh yoksa (ornegin Windows) testler atlanir.

Calistirma:  python3 tests/test_hooks.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKLAR = os.path.join(KOK, "config", "hooks", "live")
SH = shutil.which("sh")
SHELLCHECK = shutil.which("shellcheck")


def hook_listesi():
    """(ad, icerik) cifti; satir sonlari LF'ye cevrilmis (CRLF kopyalar icin)."""
    sonuc = []
    for ad in sorted(os.listdir(HOOKLAR)):
        yol = os.path.join(HOOKLAR, ad)
        if not os.path.isfile(yol):
            continue
        with open(yol, "rb") as f:
            veri = f.read().replace(b"\r\n", b"\n")
        if not veri.startswith(b"#!"):
            # git'te sembolik bag: icerik yalnizca hedef yol
            if veri.strip().startswith(b"/") and veri.count(b"\n") <= 1:
                continue
        sonuc.append((ad, veri))
    return sonuc


class HookTesti(unittest.TestCase):
    def test_hook_var(self):
        self.assertTrue(hook_listesi(), "config/hooks/live altinda hook bulunamadi")

    def test_shebang(self):
        for ad, veri in hook_listesi():
            with self.subTest(hook=ad):
                self.assertTrue(veri.startswith(b"#!/bin/sh\n"),
                                f"{ad}: ilk satir #!/bin/sh olmali")

    @unittest.skipIf(SH is None, "sh bulunamadi")
    def test_sh_n_sozdizimi(self):
        for ad, veri in hook_listesi():
            with self.subTest(hook=ad):
                sonuc = subprocess.run([SH, "-n"], input=veri,
                                       capture_output=True, timeout=30)
                self.assertEqual(
                    sonuc.returncode, 0,
                    f"{ad}: sh -n basarisiz: {sonuc.stderr.decode('utf-8', 'replace')}")

    def test_www_browser_ayarlanmaz(self):
        # firefox-esr www-browser'i saglamaz; --set sessizce/gurultuyle duserdi.
        veri = dict(hook_listesi())["9999-carotos-setup.hook.chroot"].decode("utf-8")
        self.assertNotIn("--set www-browser", veri)
        self.assertIn("--set x-www-browser", veri)
        for satir in veri.split("\n"):
            if "x-www-browser" in satir:
                self.assertNotIn("|| true", satir)

    @unittest.skipIf(SH is None, "sh bulunamadi")
    def test_firstboot_sozdizimi_ve_gunluk(self):
        yol = os.path.join(KOK, "config", "includes.chroot", "usr", "local",
                           "sbin", "carotos-firstboot.sh")
        with open(yol, "rb") as f:
            veri = f.read().replace(b"\r\n", b"\n")
        sonuc = subprocess.run([SH, "-n"], input=veri, capture_output=True, timeout=30)
        self.assertEqual(sonuc.returncode, 0, sonuc.stderr.decode("utf-8", "replace"))
        # usermod hatasi gizlenmemeli: "|| true" yok, basari/hata ayri gunluge yazilir
        for satir in veri.decode("utf-8").split("\n"):
            if "usermod" in satir:
                self.assertNotIn("|| true", satir)
        self.assertIn("EKLENEMEDI", veri.decode("utf-8"))

    @unittest.skipIf(SHELLCHECK is None, "shellcheck kurulu degil")
    def test_shellcheck_hata_duzeyi(self):
        for ad, veri in hook_listesi():
            with self.subTest(hook=ad):
                sonuc = subprocess.run(
                    [SHELLCHECK, "-s", "sh", "-S", "error", "-"],
                    input=veri, capture_output=True, timeout=60)
                self.assertEqual(
                    sonuc.returncode, 0,
                    f"{ad}: shellcheck hatasi:\n{sonuc.stdout.decode('utf-8', 'replace')}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
