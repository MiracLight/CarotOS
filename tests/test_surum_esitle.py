#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/surum_esitle.py testleri (GTK gerektirmez).

Depodaki surum bilgileri surum.json ile uyumlu mu; surum 1.4'e cevrilince ISO
dosya adi (config/common, BUILD.md) ve os-release dahil her yer
tek komutla guncelleniyor mu; LF ve CRLF (Windows) satir sonlarinda calisiyor mu.

Calistirma (depo kokunden):  python3 tests/test_surum_esitle.py
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "surum_esitle.py")


def yukle():
    spec = importlib.util.spec_from_file_location("surum_esitle_test", ARAC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sessiz(islev, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return islev(*a)


class DepoUyumuTesti(unittest.TestCase):
    def test_depo_surum_json_ile_uyumlu(self):
        mod = yukle()
        mod.KOK = KOK
        self.assertEqual(sessiz(mod.calistir, False), 0)

    def test_iso_adi_ve_birim_etiketi_kurallari_var(self):
        mod = yukle()
        with open(os.path.join(KOK, "surum.json"), encoding="utf-8") as f:
            veri = json.load(f)
        etiketler = {k[3] for k in mod.kurallar(veri)}
        for beklenen in ("config/common LB_IMAGE_NAME", "BUILD.md --image-name",
                         "BUILD.md --iso-volume"):
            self.assertIn(beklenen, etiketler)
        # CLAUDE.md yerel dosyadir (.git/info/exclude), depoda yok: arac ona baglanmamali.
        self.assertFalse([k for k in mod.kurallar(veri) if k[0] == "CLAUDE.md"])

    def test_eski_ara_surum_adi_derleme_ayarlarinda_kalmadi(self):
        for dosya in ("config/common", "BUILD.md"):
            with open(os.path.join(KOK, dosya), encoding="utf-8") as f:
                for satir in f:
                    if "image-name" in satir or "LB_IMAGE_NAME" in satir:
                        self.assertNotIn("1.3.1", satir, (dosya, satir))


class SurumGecisiTesti(unittest.TestCase):
    """Gecici bir kopyada surum 1.4'e cevrilir; dosyalar guncellenmeli."""

    DOSYALAR = ("surum.json", "config/common", "BUILD.md",
                "config/includes.chroot/etc/os-release",
                "config/includes.chroot/opt/carotos/health/carotos-health.py",
                "config/includes.chroot/opt/carotos/usb/carotos-usb-check.py",
                "config/includes.chroot/opt/carotos/welcome/carotos-welcome.py",
                "config/includes.chroot/opt/carotos/magaza/carotos-magaza.py")

    def _kopya(self, crlf):
        gecici = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, gecici, True)
        for d in self.DOSYALAR:
            hedef = os.path.join(gecici, d)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            with open(os.path.join(KOK, d), "rb") as f:
                veri = f.read().replace(b"\r\n", b"\n")
            if crlf:
                veri = veri.replace(b"\n", b"\r\n")
            with open(hedef, "wb") as f:
                f.write(veri)
        return gecici

    def _gec(self, crlf):
        gecici = self._kopya(crlf)
        yol = os.path.join(gecici, "surum.json")
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
        veri["dagitim"]["surum"] = "1.4"
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(veri, f, indent=2)
        mod = yukle()
        mod.KOK = gecici
        self.assertEqual(sessiz(mod.calistir, False), 1)     # uyusmazlik bulundu
        self.assertEqual(sessiz(mod.calistir, True), 0)      # duzeltildi
        self.assertEqual(sessiz(mod.calistir, False), 0)     # artik uyumlu

        def ham_oku(d):
            with open(os.path.join(gecici, d), "rb") as f:
                return f.read()

        def oku(d):
            return ham_oku(d).decode("utf-8")
        ayrac = "\r\n" if crlf else "\n"
        self.assertIn('LB_IMAGE_NAME="carotos-1.4"' + ayrac, oku("config/common"))
        build = oku("BUILD.md")
        self.assertIn('  --image-name "carotos-1.4" \\' + ayrac, build)
        self.assertIn('  --iso-volume "CarotOS 1.4" \\' + ayrac, build)
        self.assertIn('VERSION_ID="1.4"', oku("config/includes.chroot/etc/os-release"))
        # satir sonlari bozulmadi (karisik LF/CRLF olusmadi)
        for d in ("config/common", "BUILD.md"):
            ham = ham_oku(d)
            if crlf:
                self.assertEqual(ham.count(b"\n"), ham.count(b"\r\n"), d)
            else:
                self.assertNotIn(b"\r", ham, d)

    def test_gecis_lf(self):
        self._gec(False)

    def test_gecis_crlf_windows(self):
        self._gec(True)


if __name__ == "__main__":
    unittest.main()
