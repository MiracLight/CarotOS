#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filenor tek tik kurulum mantigi (GTK'siz). Gercek apt/pkexec cagrilmaz:
sahte 'apt-get' betigi ve sahte yetki araci kullanilir; kabuk betigi GERCEKTIR.

Calistirma:  python3 tests/test_filenor_kurulum.py
"""
import os
import stat
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filenor_yollar as Y  # noqa: E402
KOK, FN = Y.KOK, Y.FN
_EV = tempfile.mkdtemp(prefix="fn-kur-ev-")
os.environ["HOME"] = _EV
os.environ["XDG_CONFIG_HOME"] = os.path.join(_EV, ".config")

import filenor_kurulum as K  # noqa: E402
from filenor_dil import FilenorHata  # noqa: E402

HEPSI_YOK = {k: False for k in list(K.APT) + list(K.PIP) + list(K.KURULAMAZ)}


def betik_yaz(yol, icerik):
    with open(yol, "w") as f:
        f.write("#!/bin/sh\n" + icerik)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR)


class PlanTesti(unittest.TestCase):
    def test_apt_plani_tekrarsiz(self):
        p = K.plan(["ffmpeg", "ffprobe", "pillow", "tesseract"], HEPSI_YOK, apt_kullan=True, pip_kullan=True)
        self.assertEqual(p.apt.count("ffmpeg"), 1)          # ffmpeg+ffprobe tek paket
        self.assertIn("python3-pil", p.apt)
        self.assertIn("tesseract-ocr-tur", p.apt)            # Turkce OCR dil paketi
        self.assertEqual(p.pip, [])
        self.assertEqual(p.elle, [])

    def test_kurulu_olan_atlanir(self):
        d = dict(HEPSI_YOK, pillow=True)
        p = K.plan(["pillow", "qpdf"], d, apt_kullan=True, pip_kullan=True)
        self.assertEqual(p.apt, ["qpdf"])
        self.assertEqual(p.anahtarlar, ["qpdf"])

    def test_kurulamayan_ozellik_elle(self):
        p = K.plan(["avif", "webp"], HEPSI_YOK, apt_kullan=True, pip_kullan=True)
        self.assertTrue(p.bos)
        self.assertEqual(p.elle, ["avif", "webp"])

    def test_rawpy_pip_ve_pip_paketi(self):
        yedek = K.pip_var
        K.pip_var = lambda: False
        try:
            p = K.plan(["rawpy"], HEPSI_YOK, apt_kullan=True)
        finally:
            K.pip_var = yedek
        self.assertEqual(p.pip, ["rawpy"])
        self.assertEqual(p.apt, ["python3-pip"])             # pip yoksa once o kurulur

    def test_apt_yok_pip_var(self):
        p = K.plan(["pillow", "ffmpeg"], HEPSI_YOK, apt_kullan=False, pip_kullan=True)
        self.assertEqual(p.pip, ["Pillow"])
        self.assertEqual(p.elle, ["ffmpeg"])                 # ffmpeg pip ile kurulmaz
        self.assertEqual(p.apt, [])

    def test_hicbiri_yok(self):
        p = K.plan(["pillow"], HEPSI_YOK, apt_kullan=False, pip_kullan=False)
        self.assertTrue(p.bos)
        self.assertEqual(p.elle, ["pillow"])

    def test_temel_eksikler_buyukleri_ve_kurulamayani_disarida_birakir(self):
        t = K.temel_eksikler(HEPSI_YOK)
        for dis in ("libreoffice", "gs", "avif"):
            self.assertNotIn(dis, t)
        self.assertIn("pillow", t)
        self.assertIn("rawpy", t)

    def test_tablolar_tutarli(self):
        for k in K.SIRA:
            self.assertTrue(k in K.APT or k in K.PIP or k in K.KURULAMAZ, k)
        for k, paketler in K.APT.items():
            self.assertTrue(all(isinstance(x, str) and x == x.strip() and " " not in x for x in paketler), k)
        for k in K.SADECE_PIP:
            self.assertIn(k, K.PIP)


class KurTesti(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="fn-kur-")
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        self.gunluk = os.path.join(self.d, "apt.log")
        # sahte apt-get: 'yok' iceren pakette kurulum basarisiz olur
        betik_yaz(os.path.join(self.bin, "apt-get"), f'''
echo "$@" >> "{self.gunluk}"
case "$*" in *yok*|*FAKE_YOK*) echo "E: Unable to locate package"; exit 100;; esac
case "$*" in *install*)
  echo "dlstatus:1:0.0000:Retrieving file 1 of 2"
  echo "dlstatus:1:50.0000:Retrieving file 1 of 2"
  echo "dlstatus:2:100.0000:Retrieving file 2 of 2"
  echo "pmstatus:dpkg-exec:0.0000:Running dpkg"
  echo "pmstatus:ffmpeg:25.0000:Unpacking ffmpeg (amd64)"
  echo "pmstatus:ffmpeg:100.0000:Installed ffmpeg (amd64)";;
esac
exit 0
''')
        self.env = dict(os.environ, PATH=self.bin + ":" + os.environ["PATH"])
        self.satirlar = []

    def kur(self, plan, yetki=()):
        return K.kur(plan, self.satirlar.append, yetki=list(yetki), env=self.env)

    def gunluk_satirlari(self):
        if not os.path.exists(self.gunluk):
            return []
        with open(self.gunluk) as f:
            return f.read().splitlines()

    def test_hepsi_tamam_tek_seferde(self):
        k = self.kur(K.Plan(apt=["ffmpeg", "qpdf"]))
        self.assertEqual(k, [])
        g = self.gunluk_satirlari()
        self.assertEqual(g[0], "update -qq")
        self.assertEqual(len(g), 2)                          # update + tek install
        self.assertIn("ffmpeg qpdf", g[1])
        self.assertIn("--no-install-recommends", g[1])

    def test_bir_paket_yoksa_digerleri_yine_kurulur(self):
        k = self.kur(K.Plan(apt=["ffmpeg", "python3-yok", "qpdf"]))
        self.assertEqual(k, ["python3-yok"])
        g = " | ".join(self.gunluk_satirlari())
        # once toplu deneme, sonra paket paket
        self.assertIn("install -y --no-install-recommends ffmpeg python3-yok qpdf", g)
        self.assertIn("install -y --no-install-recommends ffmpeg |", g)
        self.assertIn("install -y --no-install-recommends qpdf", g.split("python3-yok qpdf")[1])

    def test_ciktisi_geri_bildirilir(self):
        self.kur(K.Plan(apt=["python3-yok"]))
        self.assertTrue(any("Unable to locate" in s for s in self.satirlar))

    def test_yetki_reddi(self):
        pkexec = os.path.join(self.d, "pkexec")
        betik_yaz(pkexec, "exit 126\n")
        with self.assertRaises(FilenorHata) as h:
            self.kur(K.Plan(apt=["ffmpeg"]), yetki=[pkexec])
        self.assertEqual(h.exception.kod, "kurulum_yetki")
        self.assertEqual(self.gunluk_satirlari(), [])        # hicbir sey kurulmadi

    def test_beklenmeyen_cikis_kodu(self):
        pkexec = os.path.join(self.d, "pkexec")
        betik_yaz(pkexec, "exit 5\n")
        with self.assertRaises(FilenorHata) as h:
            self.kur(K.Plan(apt=["ffmpeg"]), yetki=[pkexec])
        self.assertEqual(h.exception.kod, "kurulum_basarisiz")
        self.assertEqual(h.exception.ayrinti["cikis"], 5)

    def test_yetki_araci_yok(self):
        yedek = K.yetki_komutu
        K.yetki_komutu = lambda: None
        try:
            with self.assertRaises(FilenorHata) as h:
                K.kur(K.Plan(apt=["ffmpeg"]), env=self.env)
        finally:
            K.yetki_komutu = yedek
        self.assertEqual(h.exception.kod, "kurulum_yonetici_yok")

    def test_yetki_araci_komutu_one_eklenir(self):
        # pkexec sahtesi: argumanlari kaydeder, sonra gercek komutu calistirir
        pkexec = os.path.join(self.d, "pkexec")
        betik_yaz(pkexec, f'echo "PKEXEC $1 $2" >> "{self.gunluk}"\nexec "$@"\n')
        self.kur(K.Plan(apt=["qpdf"]), yetki=[pkexec])
        self.assertTrue(self.gunluk_satirlari()[0].startswith("PKEXEC /bin/sh -c"))

    def test_bos_plan_hicbir_sey_calistirmaz(self):
        self.assertEqual(self.kur(K.Plan()), [])
        self.assertEqual(self.gunluk_satirlari(), [])

    def test_pip_externally_managed_ise_bayrakla_yeniden_dener(self):
        cagrilar = []

        def sahte(komut, cb, env=None, islem=None):
            cagrilar.append(list(komut))
            if "--break-system-packages" not in komut:
                return 1, "error: externally-managed-environment", []
            return 0, "Successfully installed rawpy", []

        yedek = K._calistir
        K._calistir = sahte
        try:
            self.assertEqual(K.kur(K.Plan(pip=["rawpy"])), [])
        finally:
            K._calistir = yedek
        self.assertEqual(len(cagrilar), 2)
        self.assertIn("--user", cagrilar[0])
        self.assertIn("--break-system-packages", cagrilar[1])

    def test_pip_basarisiz_listelenir(self):
        yedek = K._calistir
        K._calistir = lambda komut, cb, env=None, islem=None: (1, "ERROR: no matching distribution", [])
        try:
            self.assertEqual(K.kur(K.Plan(pip=["rawpy"])), ["rawpy"])
        finally:
            K._calistir = yedek

    def test_ilerleme_gercek_apt_satirlarindan_gelir(self):
        olaylar = []
        self.satirlar.clear()
        K.kur(K.Plan(apt=["ffmpeg"]), self.satirlar.append, yetki=[], env=self.env,
              ilerleme_cb=lambda o, a, d: olaylar.append((o, a, d)))
        oranlar = [o for o, _a, _d in olaylar if o is not None]
        self.assertEqual(oranlar, sorted(oranlar), "ilerleme geri gitmemeli")
        self.assertEqual(oranlar[-1], 1.0)
        asamalar = [a for _o, a, _d in olaylar]
        self.assertLess(asamalar.index("guncelle"), asamalar.index("indir"))
        self.assertLess(asamalar.index("indir"), asamalar.index("kur"))
        # indirme yarisi: 0.03 + 0.52*0.5 = 0.29 ; kurulum basi >= 0.55
        indir = [o for o, a, _d in olaylar if a == "indir"]
        self.assertAlmostEqual(max(indir), K.PAY_INDIR, places=2)
        self.assertTrue(any(a == "kur" and d == "ffmpeg" for _o, a, d in olaylar))
        # durum satirlari metin olarak gosterilmez
        self.assertFalse(any(s.startswith(("dlstatus:", "pmstatus:", "FILENOR_ASAMA")) for s in self.satirlar))

    def test_pip_yedegi_apt_paketi_yoksa(self):
        # Debian'da python3-pillow-heif yok: pip ile kurulmali, basarisiz sayilmamali
        gercek = K._calistir
        pip_cagrilari = []

        def ara(komut, cb, env=None, islem=None):
            if komut and komut[0] == sys.executable:
                pip_cagrilari.append(list(komut))
                return 0, "ok", []
            return gercek(komut, cb, env, islem)
        K._calistir = ara
        olaylar = []
        try:
            # paket adi sahte apt-get'te 'FAKE_YOK' ile basarisiz olsun
            yedek = dict(K.APT_PIP_YEDEK)
            K.APT_PIP_YEDEK["FAKE_YOK-heif"] = "pillow-heif"
            k = K.kur(K.Plan(apt=["FAKE_YOK-heif"]), self.satirlar.append, yetki=[], env=self.env,
                      ilerleme_cb=lambda o, a, d: olaylar.append((o, a, d)))
        finally:
            K._calistir = gercek
            K.APT_PIP_YEDEK.clear()
            K.APT_PIP_YEDEK.update(yedek)
        self.assertEqual(k, [])
        self.assertEqual(len(pip_cagrilari), 1)
        self.assertIn("pillow-heif", pip_cagrilari[0])
        self.assertTrue(any(o is None and a == "pip" for o, a, _d in olaylar))   # boyut bilinmez -> belirsiz

    def test_pip_yedegi_de_basarisizsa_listelenir(self):
        gercek = K._calistir
        K._calistir = lambda komut, cb, env=None, islem=None: (
            (1, "ERROR", []) if komut and komut[0] == sys.executable else gercek(komut, cb, env, islem))
        try:
            K.APT_PIP_YEDEK["FAKE_YOK-x"] = "yok-boyle-paket"
            k = K.kur(K.Plan(apt=["FAKE_YOK-x"]), self.satirlar.append, yetki=[], env=self.env)
        finally:
            K._calistir = gercek
            del K.APT_PIP_YEDEK["FAKE_YOK-x"]
        self.assertEqual(k, ["yok-boyle-paket"])

    def test_yedek_tablosu_gercek_paketler_icin(self):
        self.assertEqual(K.APT_PIP_YEDEK["python3-pillow-heif"], "pillow-heif")
        self.assertEqual(K.APT_PIP_YEDEK["python3-pil"], "Pillow")
        self.assertNotIn("tesseract-ocr", K.APT_PIP_YEDEK)

    def test_pip_ilerleme_satirlari(self):
        olaylar = []
        gercek = K._calistir

        def ara(komut, cb, env=None, islem=None):
            for sat in ("Progress 1000 of 4000", "Progress 4000 of 4000"):
                islem and islem(sat)
            return 0, "", []
        K._calistir = ara
        try:
            K.kur(K.Plan(pip=["rawpy"]), None, ilerleme_cb=lambda o, a, d: olaylar.append((o, a, d)))
        finally:
            K._calistir = gercek
        oranlar = [o for o, a, _d in olaylar if o is not None]
        self.assertEqual(oranlar, sorted(oranlar))
        self.assertTrue(any(0.2 < o < 0.3 for o in oranlar))      # 1000/4000 * 0.95
        self.assertEqual(oranlar[-1], 1.0)

    def test_betik_kabuk_sozdizimi(self):
        import subprocess
        subprocess.run(["/bin/sh", "-n", "-c", K.APT_BETIGI], check=True)


class YenileTesti(unittest.TestCase):
    def test_ortami_yenile_onbellegi_temizler(self):
        import filenor_motor as M
        M.araclar_durumu()
        self.assertGreater(M.araclar_durumu.cache_info().currsize, 0)
        K.ortami_yenile()
        self.assertEqual(M.araclar_durumu.cache_info().currsize, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
