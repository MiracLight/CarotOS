#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filenor isletim sistemi katmani (GTK'siz). Windows dallari, Linux'ta taklit edilerek
(WINDOWS=True, sahte APPDATA ...) denenir; gercek Windows testi GitHub Actions'ta calisir.

Calistirma:  python3 tests/test_filenor_sistem.py
"""
import os
import subprocess
import sys
import tempfile
import time
import types
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filenor_yollar as Y  # noqa: E402
KOK, FN = Y.KOK, Y.FN

import filenor_dil as Dd  # noqa: E402
import filenor_kurulum as K  # noqa: E402
import filenor_motor as M  # noqa: E402
import filenor_sistem as S  # noqa: E402


class Ortam:
    """Ortam degiskenlerini ve S.* degerlerini geri yukler."""

    def __init__(self, **env):
        self.env = env
        self.eski_env = {}
        self.eski_s = {}

    def __enter__(self):
        for k, v in self.env.items():
            self.eski_env[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def s(self, **kw):
        for k, v in kw.items():
            self.eski_s.setdefault(k, getattr(S, k))
            setattr(S, k, v)
        return self

    def __exit__(self, *a):
        for k, v in self.eski_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for k, v in self.eski_s.items():
            setattr(S, k, v)


class Klasorler(unittest.TestCase):
    def test_ayar_dizini_ozel(self):
        with Ortam(FILENOR_AYAR_DIZINI="/tmp/ozel-fn"):
            self.assertEqual(S.ayar_dizini(), "/tmp/ozel-fn")
            self.assertEqual(M.ayar_yolu(), "/tmp/ozel-fn/filenor.json")

    def test_ayar_dizini_linux_yeni_ve_eski(self):
        ev = tempfile.mkdtemp()
        with Ortam(FILENOR_AYAR_DIZINI=None, XDG_CONFIG_HOME=ev).s(WINDOWS=False):
            self.assertEqual(S.ayar_dizini(), os.path.join(ev, "filenor"))      # yeni kurulum
            os.makedirs(os.path.join(ev, "carotos"))
            with open(os.path.join(ev, "carotos", "filenor.json"), "w") as f:
                f.write("{}")
            self.assertEqual(S.ayar_dizini(), os.path.join(ev, "carotos"))      # CarotOS ayari korunur
            os.makedirs(os.path.join(ev, "filenor"))
            with open(os.path.join(ev, "filenor", "filenor.json"), "w") as f:
                f.write("{}")
            self.assertEqual(S.ayar_dizini(), os.path.join(ev, "filenor"))      # yeni olan oncelikli

    def test_ayar_dizini_windows(self):
        with Ortam(FILENOR_AYAR_DIZINI=None, APPDATA="/tmp/appdata-x").s(WINDOWS=True):
            self.assertEqual(S.ayar_dizini(), os.path.join("/tmp/appdata-x", "Filenor"))

    def test_onbellek_windows(self):
        with Ortam(LOCALAPPDATA="/tmp/la-x").s(WINDOWS=True):
            self.assertEqual(S.onbellek_dizini(), os.path.join("/tmp/la-x", "Filenor", "onbellek"))


class Araclar(unittest.TestCase):
    def test_ek_arac_dizini_path_e_eklenir(self):
        d = tempfile.mkdtemp()
        betik = os.path.join(d, "filenor-sahte-arac")
        with open(betik, "w") as f:
            f.write("#!/bin/sh\necho x\n")
        os.chmod(betik, 0o755)
        yedek = os.environ["PATH"]
        try:
            with Ortam(FILENOR_ARAC_DIZINLERI=d).s(WINDOWS=False):
                self.assertIsNone(S.arac_yolu("filenor-sahte-arac"))
                S.ortam_hazirla()
                self.assertEqual(S.arac_yolu("filenor-sahte-arac"), betik)
                self.assertEqual(S.coz("filenor-sahte-arac"), betik)
        finally:
            os.environ["PATH"] = yedek

    def test_coz_bulunamayani_aynen_dondurur(self):
        self.assertEqual(S.coz("yok-boyle-bir-arac-xyz"), "yok-boyle-bir-arac-xyz")

    def test_gs_alternatif_adlari(self):
        self.assertIn("gswin64c", S.ARAC_ADLARI["gs"])
        self.assertIn("soffice", S.ARAC_ADLARI["soffice"])

    def test_windows_arac_dizinleri_bilinen_yerleri_tarar(self):
        ev = tempfile.mkdtemp()
        lo = os.path.join(ev, "pf", "LibreOffice", "program")
        os.makedirs(lo)
        qp = os.path.join(ev, "pf", "qpdf 11.9", "bin")
        os.makedirs(qp)
        wg = os.path.join(ev, "local", "Microsoft", "WinGet", "Links")
        os.makedirs(wg)
        pk = os.path.join(ev, "local", "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg_x", "ffmpeg-7", "bin")
        os.makedirs(pk)
        with Ortam(ProgramFiles=os.path.join(ev, "pf"), LOCALAPPDATA=os.path.join(ev, "local"),
                   FILENOR_ARAC_DIZINLERI=None).s(WINDOWS=True):
            d = S._win_arac_dizinleri()
        for beklenen in (lo, qp, wg, pk):
            self.assertIn(beklenen, d)

    def test_libreoffice_adaylari_windows(self):
        ev = tempfile.mkdtemp()
        yol = os.path.join(ev, "LibreOffice 24", "program")
        os.makedirs(yol)
        open(os.path.join(yol, "soffice.exe"), "w").close()
        with Ortam(ProgramFiles=ev).s(WINDOWS=True):
            self.assertEqual(S.libreoffice_adaylari(), [os.path.join(yol, "soffice.exe")])

    def test_yazi_tipi_adaylari(self):
        with Ortam().s(WINDOWS=True):
            self.assertTrue(any(a.lower().endswith("consola.ttf") for a in S.sabit_genislikli_yazi_tipleri()))
        with Ortam().s(WINDOWS=False):
            self.assertTrue(any("DejaVuSansMono" in a for a in S.sabit_genislikli_yazi_tipleri()))


class Surecler(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "Linux sure grubu")
    def test_oldur_alt_surecleri_de_oldurur(self):
        # kabuk -> sleep: grup oldurulunce ikisi de gitmeli
        proc = subprocess.Popen(["/bin/sh", "-c", "sleep 60 & wait"], **S.popen_ayarlari())
        time.sleep(0.3)
        S.oldur(proc)
        self.assertIsNotNone(proc.poll())
        cocuk = subprocess.run(["pgrep", "-f", "^sleep 60$"], capture_output=True, text=True)
        # grup oldurulmus: bu testin baslattigi 'sleep 60' kalmamali
        self.assertEqual(cocuk.stdout.strip(), "", "alt surec kaldi")

    def test_popen_ayarlari_linux(self):
        with Ortam().s(WINDOWS=False):
            self.assertEqual(S.popen_ayarlari(), {"start_new_session": True})

    def test_calistir_utf8_cikti(self):
        o = M.Oturum()
        try:
            _, out, _ = M.calistir(o, [sys.executable, "-c", "print('ş ğ ı İ ö ü ç')"], "python")
            self.assertIn("ş ğ ı İ ö ü ç", out)
        finally:
            o.kapat()


class DilVeAd(unittest.TestCase):
    def test_sistem_dili(self):
        with Ortam(FILENOR_DIL="tr_TR.UTF-8", LC_ALL=None, LANG=None, LC_MESSAGES=None, LANGUAGE=None):
            self.assertEqual(S.sistem_dili(), "tr")
        with Ortam(FILENOR_DIL="de_DE", LC_ALL=None):
            self.assertEqual(S.sistem_dili(), "en")
        with Ortam(FILENOR_DIL=None, LC_ALL="tr_TR.UTF-8"):
            self.assertEqual(S.sistem_dili(), "tr")

    def test_windows_dosya_adi_temizleme(self):
        with Ortam().s(WINDOWS=True):
            self.assertEqual(M._dosya_adi_temizle('a:b*c?"d<e>f|g\\h/i. '), "a_b_c__d_e_f_g_h_i")
        with Ortam().s(WINDOWS=False):
            self.assertEqual(M._dosya_adi_temizle("a:b*c"), "a:b*c")           # Linux'ta ':' gecerli

    def test_benzersiz_yol_windows_adi(self):
        d = tempfile.mkdtemp()
        with Ortam().s(WINDOWS=True):
            yol = M.benzersiz_yol(d, "rapor: son?", "pdf")
        self.assertEqual(os.path.basename(yol), "rapor_ son_.pdf")

    def test_ipucu_platforma_gore(self):
        gercek = Dd.os
        try:
            Dd.os = types.SimpleNamespace(name="nt")
            self.assertIn("winget install Gyan.FFmpeg", Dd.ipucu_al("ffmpeg", "tr"))
            self.assertIn("winget install QPDF.QPDF", Dd.ipucu_al("qpdf", "en"))
            self.assertNotIn("apt", Dd.ipucu_al("pillow", "tr"))
            self.assertIn("AVIF", Dd.ipucu_al("avif", "en"))                    # Pillow ozelligi: ayni metin
            Dd.os = types.SimpleNamespace(name="posix")
            self.assertIn("sudo apt install ffmpeg", Dd.ipucu_al("ffmpeg", "tr"))
        finally:
            Dd.os = gercek

    def test_lo_profil_adresi(self):
        import pathlib
        self.assertTrue(pathlib.PurePosixPath("/tmp/x y").as_uri().startswith("file:///tmp/"))


class WingetPlani(unittest.TestCase):
    D = {k: False for k in list(K.APT) + list(K.PIP) + ["avif", "webp"]}

    def test_winget_kimlikleri_tekrarsiz(self):
        p = K.plan(["pdftoppm", "pdftotext", "pdfinfo", "ffmpeg", "ffprobe", "qpdf"], self.D,
                   apt_kullan=False, pip_kullan=False, winget_kullan=True)
        self.assertEqual(sorted(p.winget), ["Gyan.FFmpeg", "QPDF.QPDF", "oschwartz10612.Poppler"])
        self.assertEqual(p.apt, [])
        self.assertFalse(p.bos)

    def test_windows_donmus_python_modulleri_elle(self):
        p = K.plan(["pillow", "reportlab", "rawpy"], self.D, apt_kullan=False, pip_kullan=False, winget_kullan=True)
        self.assertTrue(p.bos)
        self.assertEqual(sorted(p.elle), ["pillow", "rawpy", "reportlab"])

    def test_windows_kaynak_koddan_pip(self):
        p = K.plan(["pillow", "libreoffice"], self.D, apt_kullan=False, pip_kullan=True, winget_kullan=True)
        self.assertEqual(p.pip, ["Pillow"])
        self.assertEqual(p.winget, ["TheDocumentFoundation.LibreOffice"])

    def test_winget_komutu_ve_ilerleme(self):
        komutlar = []
        olaylar = []
        gercek = K._calistir

        def sahte(komut, cb, env=None, islem=None):
            komutlar.append(list(komut))
            islem("  ██████░░░░  45%")
            islem("  ██████████ 100%")
            islem("   -")
            return 0, "", []
        K._calistir = sahte
        try:
            yok = K.kur(K.Plan(winget=["Gyan.FFmpeg", "QPDF.QPDF"]), None,
                        ilerleme_cb=lambda o, a, d: olaylar.append((o, a, d)))
        finally:
            K._calistir = gercek
        self.assertEqual(yok, [])
        self.assertEqual(len(komutlar), 2)
        for k in komutlar:
            self.assertIn("install", k)
            self.assertIn("--accept-package-agreements", k)
            self.assertIn("--silent", k)
        self.assertEqual(komutlar[0][komutlar[0].index("--id") + 1], "Gyan.FFmpeg")
        oranlar = [o for o, _a, _d in olaylar if o is not None]
        self.assertEqual(oranlar, sorted(oranlar))
        self.assertTrue(any(0.2 < o < 0.3 for o in oranlar))        # ilk paketin %45'i ~ 0.5*0.45
        self.assertEqual(oranlar[-1], 1.0)

    def test_winget_basarisiz_paket_listelenir(self):
        gercek = K._calistir
        K._calistir = lambda komut, cb, env=None, islem=None: (1, "", [])
        try:
            self.assertEqual(K.kur(K.Plan(winget=["Gyan.FFmpeg"]), None), ["Gyan.FFmpeg"])
        finally:
            K._calistir = gercek

    def test_winget_zaten_kurulu_basari_sayilir(self):
        gercek = K._calistir
        K._calistir = lambda komut, cb, env=None, islem=None: (-1978335189, "", [])
        try:
            self.assertEqual(K.kur(K.Plan(winget=["Gyan.FFmpeg"]), None), [])
        finally:
            K._calistir = gercek

    def test_donmus_uygulamada_pip_yok(self):
        with Ortam().s(DONMUS=True):
            self.assertFalse(K.pip_var())

    def test_karisik_plan_araliklari_toplam_bire_gider(self):
        olaylar = []
        gercek = K._calistir
        K._calistir = lambda komut, cb, env=None, islem=None: (0, "", [])
        try:
            K.kur(K.Plan(winget=["A.B"], pip=["x"]), None, ilerleme_cb=lambda o, a, d: olaylar.append(o))
        finally:
            K._calistir = gercek
        oranlar = [o for o in olaylar if o is not None]
        self.assertEqual(oranlar, sorted(oranlar))
        self.assertEqual(oranlar[-1], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
