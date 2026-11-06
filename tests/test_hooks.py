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

    def test_usr_lib_os_release_carotos_olur(self):
        # hardinfo2 once /usr/lib/os-release'i okur (yalniz CachyOS icin /etc'e bakar): Debian'in dosyasi orada kalirsa
        # "Debian" gorunur. Hook bloku sahte bir kokte (dpkg-divert taklidiyle) calistirilir.
        import re
        import tempfile
        veri = dict(hook_listesi())["9999-carotos-setup.hook.chroot"].decode("utf-8")
        blok = re.search(r"(if \[ -f /etc/os-release \].*?\nfi\n)", veri, re.S).group(1)
        self.assertIn("dpkg-divert --local --rename --divert /usr/lib/os-release.debian --add /usr/lib/os-release", blok)
        kok = tempfile.mkdtemp(prefix="osrel-")
        os.makedirs(os.path.join(kok, "etc"))
        os.makedirs(os.path.join(kok, "usr", "lib"))
        os.makedirs(os.path.join(kok, "bin"))
        with open(os.path.join(kok, "etc", "os-release"), "w") as f:
            f.write('PRETTY_NAME="CarotOS 1.3 (Eggshell)"\nID=carotos\nID_LIKE=debian\n')
        with open(os.path.join(kok, "usr", "lib", "os-release"), "w") as f:
            f.write('PRETTY_NAME="Debian GNU/Linux 13 (trixie)"\nID=debian\n')
        # dpkg-divert taklidi: --rename ile hedef dosyayi --divert yoluna tasir
        stub = os.path.join(kok, "bin", "dpkg-divert")
        with open(stub, "w") as f:
            f.write('#!/bin/sh\nwhile [ $# -gt 0 ]; do case "$1" in --divert) d="$2"; shift;; --add) t="$2"; shift;; esac; shift; done\n'
                    'mv "$t" "$d"\n')
        os.chmod(stub, 0o755)
        yerel = blok.replace("/usr/lib/os-release", kok + "/usr/lib/os-release").replace("/etc/os-release", kok + "/etc/os-release")
        sonuc = subprocess.run([SH, "-e"], input=yerel.encode("utf-8"), capture_output=True, timeout=30,
                               env=dict(os.environ, PATH=kok + "/bin:" + os.environ.get("PATH", "")))
        self.assertEqual(sonuc.returncode, 0, sonuc.stderr.decode("utf-8", "replace"))
        yeni = open(os.path.join(kok, "usr", "lib", "os-release")).read()
        self.assertIn("ID=carotos", yeni)
        self.assertNotIn("ID=debian\n", yeni)
        eski = open(os.path.join(kok, "usr", "lib", "os-release.debian")).read()
        self.assertIn("ID=debian", eski)          # Debian'in dosyasi divert yoluna tasindi

    def test_etc_os_release_carotos(self):
        yol = os.path.join(KOK, "config", "includes.chroot", "etc", "os-release")
        icerik = open(yol, encoding="utf-8").read()
        self.assertIn("ID=carotos", icerik)
        self.assertIn("ID_LIKE=debian", icerik)

    def test_wireshark_hook(self):
        # dumpcap yetkileri ve wireshark grubu olusmali; olusmazsa derleme durmali
        veri = dict(hook_listesi())["9989-carotos-wireshark.hook.chroot"].decode("utf-8")
        self.assertIn("wireshark-common/install-setuid boolean true", veri)
        self.assertIn("libcap2-bin", veri)
        self.assertIn("dpkg-reconfigure", veri)
        self.assertIn("getent group wireshark", veri)
        self.assertIn("exit 1", veri)

    @unittest.skipIf(SH is None, "sh bulunamadi")
    def test_disk_info_hook_davranisi(self):
        # live-build binary_disk .disk/info'ya sabit "Debian GNU/Linux ..." yazar;
        # kurulu sistemdeki APT cdrom yorumu bu dosyadan gelir. Hook yeniden yazar.
        import tempfile
        betik = dict(hook_listesi())["9998-carotos-disk-info.hook.binary"]
        orijinal = 'Debian GNU/Linux 1.3 "Trixie" - Snapshot amd64 LIVE/INSTALL Binary 20261102-20:43\n'
        with tempfile.TemporaryDirectory() as kok:
            os.makedirs(os.path.join(kok, "binary", ".disk"))
            os.makedirs(os.path.join(kok, "chroot", "etc"))
            bilgi = os.path.join(kok, "binary", ".disk", "info")
            with open(bilgi, "w", encoding="utf-8", newline="\n") as f:
                f.write(orijinal)
            with open(os.path.join(kok, "chroot", "etc", "os-release"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write('VERSION="1.3 (Eggshell)"\n')
            sonuc = subprocess.run([SH, "-s"], input=betik, cwd=os.path.join(kok, "binary"),
                                   capture_output=True, timeout=30)
            self.assertEqual(sonuc.returncode, 0, sonuc.stderr.decode("utf-8", "replace"))
            with open(bilgi, encoding="utf-8") as f:
                icerik = f.read()
            self.assertEqual(
                icerik,
                "CarotOS 1.3 (Eggshell) - Snapshot amd64 LIVE/INSTALL Binary 20261102-20:43\n")
            self.assertNotIn("Debian", icerik)

    @unittest.skipIf(SH is None, "sh bulunamadi")
    def test_disk_info_hook_dosya_yoksa_sessizce_cikar(self):
        # iso/iso-hybrid disinda .disk/info olusmaz; hook derlemeyi durdurmamali
        import tempfile
        betik = dict(hook_listesi())["9998-carotos-disk-info.hook.binary"]
        with tempfile.TemporaryDirectory() as kok:
            os.makedirs(os.path.join(kok, "binary"))
            sonuc = subprocess.run([SH, "-s"], input=betik, cwd=os.path.join(kok, "binary"),
                                   capture_output=True, timeout=30)
            self.assertEqual(sonuc.returncode, 0)

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
