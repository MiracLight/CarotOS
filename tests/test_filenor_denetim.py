#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filenor guvenlik denetimi duzeltmeleri (F-01 ... F-11).

Calistirma:  python3 tests/test_filenor_denetim.py
Eksik arac/modul olan testler atlanir. GTK yoksa arayuz testleri atlanir.
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filenor_yollar as Y  # noqa: E402
_EV = tempfile.mkdtemp(prefix="fn-den-ev-")
os.environ["HOME"] = _EV
os.environ["XDG_CONFIG_HOME"] = os.path.join(_EV, ".config")

import filenor_motor as M  # noqa: E402
import filenor_araclar as A  # noqa: E402
from filenor_dil import FilenorHata, hata_metni  # noqa: E402

D = M.araclar_durumu()
POSIX = os.name == "posix"


def gerek(*a):
    return unittest.skipUnless(all(D.get(x, False) for x in a), "eksik: " + ",".join(a))


def png(yol, boyut=(16, 12)):
    from PIL import Image
    Image.new("RGB", boyut, (200, 30, 30)).save(yol, "PNG")


class Temel(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="fn-den-")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.cikti = os.path.join(self.kok, "cikti")
        os.makedirs(self.cikti)

    def yol(self, ad):
        return os.path.join(self.kok, ad)


# ---------------------------------------------------------------------------
@gerek("pillow")
class F01(Temel):
    PS = b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 10 10\n0 0 moveto 10 10 lineto stroke\nshowpage\n"

    def test_postscript_jpg_adli_reddedilir_ve_gs_cagrilmaz(self):
        bin_ = os.path.join(self.kok, "bin")
        os.makedirs(bin_)
        iz = os.path.join(self.kok, "gs_izi")
        sahte = os.path.join(bin_, "gs")
        with open(sahte, "w") as f:
            f.write(f"#!/bin/sh\necho cagrildi >> '{iz}'\nexit 1\n")
        os.chmod(sahte, 0o755)
        ps = self.yol("tatil.jpg")
        with open(ps, "wb") as f:
            f.write(self.PS)
        eski = os.environ["PATH"]
        os.environ["PATH"] = bin_ + os.pathsep + eski
        try:
            with self.assertRaises(FilenorHata) as c:
                M.donustur(ps, "png", self.cikti)
        finally:
            os.environ["PATH"] = eski
        self.assertEqual(c.exception.kod, "okunamadi")
        self.assertFalse(os.path.exists(iz), "Ghostscript cagrildi")

    def test_uzantisi_yanlis_png_calismaya_devam_eder(self):
        p = self.yol("foto.jpg")
        png(p)
        s = M.donustur(p, "png", self.cikti)
        self.assertEqual(len(s), 1)
        self.assertTrue(os.path.getsize(s[0]) > 0)

    def test_eps_eklentisi_gs_ikilisi_kapali(self):
        from PIL import EpsImagePlugin
        self.assertFalse(EpsImagePlugin.gs_binary)

    def test_araclar_da_ayni_sinir(self):
        ps = self.yol("a.png")
        with open(ps, "wb") as f:
            f.write(self.PS)
        with self.assertRaises(FilenorHata) as c:
            M._gorsel_ac(M.Oturum(), ps, "png")
        self.assertEqual(c.exception.kod, "okunamadi")


# ---------------------------------------------------------------------------
@unittest.skipUnless(D.get("ffmpeg") and D.get("ffprobe") and D.get("pillow"), "ffmpeg/Pillow yok")
class F02(Temel):
    def ses_uret(self, ad):
        p = self.yol(ad)
        subprocess.run([M.S.coz("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x48:d=1:r=10",
                        "-pix_fmt", "yuv420p", p], check=True, capture_output=True)
        return p

    def test_sinir_argumanlari(self):
        k = M.ffmpeg_girdi_siniri("/x/girdi.mp4")
        self.assertEqual(k[:2], ["-protocol_whitelist", "file"])
        self.assertIn("-format_whitelist", k)
        beyaz = k[k.index("-format_whitelist") + 1].split(",")
        for yasak in ("dash", "hls", "concat", "ffconcat", "sdp", "rtsp"):
            self.assertNotIn(yasak, beyaz)
        self.assertIn("mov", beyaz)
        self.assertIn("matroska", beyaz)

    def test_dash_manifestosu_mp4_adli_reddedilir(self):
        ozel = self.ses_uret("ozel_video.mp4")
        mpd = self.yol("komik.mp4")
        with open(mpd, "w") as f:
            f.write(textwrap.dedent(f"""\
                <?xml version="1.0"?>
                <MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT1S"
                     minBufferTime="PT1S" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011">
                 <Period><AdaptationSet mimeType="video/mp4"><Representation id="1" bandwidth="1000">
                  <BaseURL>file://{ozel}</BaseURL>
                  <SegmentBase indexRange="0-0"/>
                 </Representation></AdaptationSet></Period></MPD>
                """))
        with self.assertRaises(FilenorHata):
            M.donustur(mpd, "mkv", self.cikti)
        self.assertEqual([f for f in os.listdir(self.cikti) if not f.startswith(".")], [])

    def test_gercek_mp4_ve_mkv_adli_mp4_calisir(self):
        p = self.ses_uret("v.mp4")
        s = M.donustur(p, "mkv", self.cikti)
        self.assertTrue(os.path.getsize(s[0]) > 0)
        mkv_ama_mp4 = self.yol("mkv_gibi.mp4")
        shutil.copyfile(s[0], mkv_ama_mp4)
        s2 = M.donustur(mkv_ama_mp4, "webm" if D.get("ffmpeg") else "mkv", self.cikti)
        self.assertTrue(os.path.getsize(s2[0]) > 0)

    def test_gorselden_video(self):
        from PIL import Image
        g = self.yol("a.gif")
        kareler = [Image.new("RGB", (32, 32), (i * 20, 0, 0)) for i in range(4)]
        kareler[0].save(g, save_all=True, append_images=kareler[1:], duration=100)
        s = M.donustur(g, "mp4", self.cikti)
        self.assertTrue(os.path.getsize(s[0]) > 0)


# ---------------------------------------------------------------------------
@gerek("pillow")
class F03(Temel):
    def gif(self, kare, boyut):
        from PIL import Image
        g = self.yol("anim.gif")
        k = [Image.new("RGB", boyut, (i % 255, 0, 0)) for i in range(kare)]
        k[0].save(g, save_all=True, append_images=k[1:], duration=50)
        return g

    def test_buyuk_animasyon_reddedilir(self):
        g = self.gif(10, (20, 20))
        eski = M.ANIMASYON_PIKSEL_SINIRI
        M.ANIMASYON_PIKSEL_SINIRI = 3999        # 10*20*20 = 4000
        try:
            with self.assertRaises(FilenorHata) as c:
                M.donustur(g, "webp", self.cikti)
        finally:
            M.ANIMASYON_PIKSEL_SINIRI = eski
        self.assertEqual(c.exception.kod, "cok_buyuk")
        self.assertIn("10", hata_metni(c.exception, "tr"))
        self.assertIn("too large", hata_metni(c.exception, "en"))
        self.assertEqual([f for f in os.listdir(self.cikti) if f.startswith(".filenor")], [])

    def test_sinir_altindaki_animasyon_calisir(self):
        g = self.gif(5, (16, 16))
        if not D.get("webp"):
            self.skipTest("webp yok")
        s = M.donustur(g, "webp", self.cikti)
        self.assertTrue(os.path.getsize(s[0]) > 0)

    def test_kare_dongusunde_iptal(self):
        from PIL import Image
        g = self.gif(6, (16, 16))
        im = Image.open(g)
        sayac = {"n": 0}

        def kontrol():
            sayac["n"] += 1
            if sayac["n"] >= 2:
                raise M.Iptal()
        with self.assertRaises(M.Iptal):
            M.gorsel_isle(im, "gif", self.yol("o.gif"), M.Secenek(), hepsi=True, kontrol=kontrol)


# ---------------------------------------------------------------------------
@gerek("pillow")
class F04(Temel):
    def isler(self, *dizinler):
        out = []
        for i, d in enumerate(dizinler):
            p = os.path.join(d, f"r{i}.png")
            png(p)
            out.append(M.Is(p, "jpg"))
        return out

    def calistir(self, isler, **kw):
        bitti = threading.Event()
        k = M.Kosucu(isler, None, M.Secenek(zip_yap=True), bitti_cb=lambda _: bitti.set(), yanina=True, **kw)
        k.start()
        self.assertTrue(bitti.wait(60), "bitti_cb cagrilmadi")
        k.join(5)
        return k

    @unittest.skipUnless(POSIX and os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK)
                         and os.access("/tmp", os.W_OK) and os.geteuid() != 0, "POSIX/dev/shm/root degil gerekir")
    def test_yazilamaz_ortak_kokte_zip_yine_olusur(self):
        a = tempfile.mkdtemp(prefix="fn-den-", dir="/tmp")
        b = tempfile.mkdtemp(prefix="fn-den-", dir="/dev/shm")
        self.addCleanup(shutil.rmtree, a, True)
        self.addCleanup(shutil.rmtree, b, True)
        k = self.calistir(self.isler(a, b))
        self.assertEqual([i.durum for i in k.isler], ["tamam", "tamam"])
        self.assertIsNone(k.zip_hata)
        self.assertTrue(k.zip_yolu and os.path.isfile(k.zip_yolu), k.zip_yolu)
        import zipfile
        with zipfile.ZipFile(k.zip_yolu) as z:
            self.assertEqual(len(z.namelist()), 2)

    def test_zip_hatasi_bitti_cb_ve_zip_hata(self):
        a = os.path.join(self.kok, "a")
        os.makedirs(a)
        eski = M.benzersiz_yol

        def bozuk(dizin, ad, ext):
            if ext == "zip":
                raise OSError(28, "No space left on device")
            return eski(dizin, ad, ext)
        M.benzersiz_yol = bozuk
        try:
            k = self.calistir(self.isler(a, a))
        finally:
            M.benzersiz_yol = eski
        self.assertEqual([i.durum for i in k.isler], ["tamam", "tamam"])      # isler korunur
        self.assertIsNotNone(k.zip_hata)
        self.assertEqual(k.zip_hata.kod, "zip_hata")
        self.assertIsNone(k.zip_yolu)
        self.assertIn("ZIP", hata_metni(k.zip_hata, "en"))

    def test_beklenmeyen_hatada_bile_bitti_cb(self):
        a = os.path.join(self.kok, "a")
        os.makedirs(a)
        eski = M.Oturum

        class Patlak:
            def __init__(self, *a, **k):
                raise RuntimeError("oturum kurulamadi")
        M.Oturum = Patlak
        try:
            k = self.calistir(self.isler(a))
        finally:
            M.Oturum = eski
        self.assertEqual(k.isler[0].durum, "hata")
        self.assertEqual(k.isler[0].hata.kod, "bilinmeyen")


# ---------------------------------------------------------------------------
@unittest.skipUnless(POSIX and shutil.which("sleep"), "POSIX gerekir")
class F05(Temel):
    BETIK = textwrap.dedent("""\
        import os, sys, threading, time
        sys.dont_write_bytecode = True
        sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2])
        import filenor_motor as M
        cikti = sys.argv[3]
        def is_():
            try:
                with M.Oturum() as o:
                    isd = os.path.join(cikti, ".filenor-deneme")
                    os.mkdir(isd); M._kayit_ekle(M._AKTIF_DIZIN, isd)
                    M.calistir(o, ["sleep", "60"], "sleep")
            except BaseException:
                pass
        th = threading.Thread(target=is_, daemon=True); th.start()
        for _ in range(100):
            if M._AKTIF_SUREC:
                break
            time.sleep(0.05)
        pid = list(M._AKTIF_SUREC)[0].pid
        print(pid, flush=True)
        sys.exit(0)      # daemon is parcacigi calisirken cik
        """)

    def test_cikista_arac_oldurulur_is_klasoru_silinir(self):
        betik = self.yol("child.py")
        with open(betik, "w") as f:
            f.write(self.BETIK)
        p = subprocess.run([sys.executable, "-I", betik, Y.FN, Y.ORTAK, self.cikti], capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        pid = int(p.stdout.split()[0])
        for _ in range(60):
            try:
                with open(f"/proc/{pid}/stat") as f:
                    durum = f.read().rsplit(")", 1)[1].split()[0]
                if durum == "Z":
                    break
            except OSError:
                break
            time.sleep(0.1)
        else:
            os.kill(pid, 9)
            self.fail("sleep sureci cikista oldurulmedi")
        self.assertFalse(os.path.exists(os.path.join(self.cikti, ".filenor-deneme")))

    def test_kayit_normal_isten_sonra_bosalir(self):
        with M.Oturum() as o:
            M.calistir(o, ["sleep", "0"], "sleep")
            self.assertEqual(len(M._AKTIF_SUREC), 0)
            self.assertIn(o.taban, M._AKTIF_DIZIN)
        self.assertEqual(len(M._AKTIF_DIZIN & {o._taban or ""}), 0)


# ---------------------------------------------------------------------------
@gerek("qpdf", "pillow")
class F06(Temel):
    PAROLA = "Cok-Gizli parola 42"

    def pdf(self):
        from PIL import Image
        p = self.yol("a.pdf")
        Image.new("RGB", (30, 30)).save(p, "PDF")
        return p

    def izle(self):
        kayit = []
        asil = M.calistir

        def sar(o, komut, arac, **kw):
            kayit.append(list(komut))
            return asil(o, komut, arac, **kw)
        M.calistir = sar
        A.calistir = sar
        self.addCleanup(setattr, M, "calistir", asil)
        self.addCleanup(setattr, A, "calistir", asil)
        return kayit

    def test_parola_komut_satirinda_gecmez(self):
        kayit = self.izle()
        sec = M.Secenek(yeni_parola=self.PAROLA)
        s = A.arac_calistir("pdf_kilitle", [self.pdf()], self.cikti, sec)
        kilitli = s[0]
        sec2 = M.Secenek(parola=self.PAROLA)
        s2 = A.arac_calistir("pdf_kilit_ac", [kilitli], self.cikti, sec2)
        self.assertEqual(M.pdf_bilgi(M.Oturum(), s2[0])["sayfa"], 1)
        sec3 = M.Secenek(parola=self.PAROLA)
        s3 = A.arac_calistir("pdf_sayfa_sec", [kilitli], self.cikti, sec3)       # pdf_hazirla + pdf_bilgi
        self.assertTrue(os.path.getsize(s3[0]) > 0)
        self.assertTrue(kayit)
        for kom in kayit:
            self.assertFalse(any("Cok-Gizli" in x or x == "42" for x in kom), kom)
        self.assertTrue(any(k[1].startswith("@") for k in kayit if k[0] == "qpdf" and len(k) > 1))

    def test_yanlis_parola_hala_sifreli_pdf(self):
        sec = M.Secenek(yeni_parola=self.PAROLA)
        kilitli = A.arac_calistir("pdf_kilitle", [self.pdf()], self.cikti, sec)[0]
        with self.assertRaises(FilenorHata) as c:
            M.pdf_bilgi(M.Oturum(), kilitli, "yanlis")
        self.assertEqual(c.exception.kod, "sifreli_pdf")

    def test_arguman_dosyasi_0600_ve_silinir(self):
        gorulen = {}
        asil = M.calistir

        def sar(o, komut, arac, **kw):
            af = komut[1][1:]
            gorulen["kip"] = stat.S_IMODE(os.stat(af).st_mode)
            gorulen["yol"] = af
            return 0, "1\n", ""
        M.calistir = sar
        self.addCleanup(setattr, M, "calistir", asil)
        with M.Oturum() as o:
            M._qpdf_gizli(o, ["--password=x"], ["--show-npages", "/x.pdf"])
        if POSIX:
            self.assertEqual(gorulen["kip"], 0o600)
        self.assertFalse(os.path.exists(gorulen["yol"]))

    def test_satir_sonlu_parola_reddedilir(self):
        with M.Oturum() as o, self.assertRaises(FilenorHata) as c:
            M._qpdf_gizli(o, ["--password=a\nb"], ["--show-npages", "/x.pdf"])
        self.assertEqual(c.exception.kod, "parola_gecersiz")

    def test_pdfinfo_yedeginde_parola_komut_satirina_konmaz(self):
        d = dict(M.araclar_durumu())
        d["qpdf"] = False
        d["pdfinfo"] = True
        M.araclar_durumu.cache_clear()
        asil = M.araclar_durumu
        M.araclar_durumu = lambda: d
        self.addCleanup(setattr, M, "araclar_durumu", asil)
        with self.assertRaises(FilenorHata) as c:
            M.pdf_bilgi(M.Oturum(), "/x.pdf", "gizli")
        self.assertEqual(c.exception.kod, "arac_eksik")


# ---------------------------------------------------------------------------
@gerek("pillow")
class F07F08(Temel):
    def test_disk_dolu_baslamaz(self):
        p = self.yol("a.png")
        png(p)
        asil = shutil.disk_usage

        class Kullanim:
            total = used = 100
            free = 0
        shutil.disk_usage = lambda d: Kullanim()
        try:
            with self.assertRaises(FilenorHata) as c:
                M.donustur(p, "jpg", self.cikti)
        finally:
            shutil.disk_usage = asil
        self.assertEqual(c.exception.kod, "disk_yetersiz")
        self.assertEqual([f for f in os.listdir(self.cikti)], [])

    @gerek("pdftoppm", "qpdf")
    def test_cok_sayfa_sinirlanir(self):
        from PIL import Image
        p = self.yol("c.pdf")
        k = [Image.new("RGB", (20, 20)) for _ in range(4)]
        k[0].save(p, "PDF", save_all=True, append_images=k[1:])
        eski = M.SAYFA_SINIRI
        M.SAYFA_SINIRI = 3
        try:
            with self.assertRaises(FilenorHata) as c:
                M.donustur(p, "png", self.cikti)
            self.assertEqual(c.exception.kod, "cok_sayfa")
            s = M.donustur(p, "png", self.cikti, M.Secenek(sayfa_araligi="1-3"))
            self.assertEqual(len(s), 3)
        finally:
            M.SAYFA_SINIRI = eski

    def test_uzun_cok_baytli_ad(self):
        ad = "ğ" * 125
        p = self.yol(ad + ".png")
        try:
            png(p)
        except OSError:
            self.skipTest("dosya sistemi 254 bayt adi desteklemiyor")
        for _ in range(3):                                   # ikinci/ucuncu: " (n)" eki
            s = M.donustur(p, "jpg", self.cikti)
            self.assertLessEqual(len(os.path.basename(s[0]).encode()), 255)
        self.assertEqual(len(os.listdir(self.cikti)), 3)

    def test_uzun_adli_klasor(self):
        kl = M.benzersiz_klasor(self.cikti, "ğ" * 200 + "_sayfalar")
        self.assertLessEqual(len(os.path.basename(kl).encode()), 255)
        self.assertTrue(os.path.isdir(kl))

    def test_bayt_kirp_karakteri_bolmez(self):
        k = M._bayt_kirp("ğ" * 300, 201)
        self.assertEqual(k, "ğ" * 100)
        self.assertEqual(M._bayt_kirp("abc", 200), "abc")

    def test_yazma_hatasi_cikti_yazilamaz(self):
        asil = os.open

        def bozuk(*a, **k):
            raise OSError(36, "File name too long")
        os.open = bozuk
        try:
            with self.assertRaises(FilenorHata) as c:
                M.benzersiz_yol(self.cikti, "x", "pdf")
        finally:
            os.open = asil
        self.assertEqual(c.exception.kod, "cikti_yazilamaz")


# ---------------------------------------------------------------------------
@unittest.skipUnless(POSIX, "POSIX gerekir")
class F09(Temel):
    def test_nokta_onekli_belge_cikti_bulunur(self):
        sahte = self.yol("soffice")
        with open(sahte, "w") as f:
            f.write(textwrap.dedent(f"""\
                #!{sys.executable}
                import os, sys
                a = sys.argv
                out = a[a.index("--outdir") + 1]
                girdi = a[-1]
                ad = os.path.splitext(os.path.basename(girdi))[0]
                open(os.path.join(out, ad + ".pdf"), "wb").write(b"%PDF-1.4 sahte")
                """))
        os.chmod(sahte, 0o755)
        belge = self.yol(".rapor.docx")
        with open(belge, "wb") as f:
            f.write(b"x")
        asil = M._soffice_bul
        M._soffice_bul = lambda: sahte
        calisma = os.path.join(self.kok, "lo")
        os.makedirs(calisma)
        try:
            with M.Oturum() as o:
                s = M.lo_calistir(o, belge, calisma, "pdf:writer_pdf_Export")
        finally:
            M._soffice_bul = asil
        self.assertEqual([os.path.basename(x) for x in s], ["girdi.pdf"])


# ---------------------------------------------------------------------------
class F11(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
            if not Gtk.init_check()[0]:
                raise ImportError("ekran yok")
            import filenor_uygulama as F
            cls.F = F
        except Exception as e:
            raise unittest.SkipTest(f"GTK yok: {e}")

    def test_bakilacak_sinir(self):
        kok = tempfile.mkdtemp(prefix="fn-den-")
        self.addCleanup(shutil.rmtree, kok, True)
        for i in range(30):
            os.makedirs(os.path.join(kok, f"d{i}"))
            for j in range(10):
                open(os.path.join(kok, f"d{i}", f"x{j}.txt"), "w").close()
        hepsi = self.F.klasor_dosyalari(kok, sinir=10_000)
        self.assertEqual(len(hepsi), 300)
        az = self.F.klasor_dosyalari(kok, sinir=10_000, bakilacak=50)
        self.assertLess(len(az), 300)

    def test_sure_siniri(self):
        kok = tempfile.mkdtemp(prefix="fn-den-")
        self.addCleanup(shutil.rmtree, kok, True)
        os.makedirs(os.path.join(kok, "a"))
        open(os.path.join(kok, "a", "x.txt"), "w").close()
        self.assertEqual(self.F.klasor_dosyalari(kok, sure=-1.0), [])

    def test_normal_kullanim_degismedi(self):
        kok = tempfile.mkdtemp(prefix="fn-den-")
        self.addCleanup(shutil.rmtree, kok, True)
        open(os.path.join(kok, "a.png"), "w").close()
        open(os.path.join(kok, ".gizli.png"), "w").close()
        self.assertEqual([os.path.basename(x) for x in self.F.klasor_dosyalari(kok)], ["a.png"])


class F10(unittest.TestCase):
    """PyPI kurulumu: onay, sanal ortam, --break-system-packages yok."""

    def test_sanal_ortam_yolu_sona_eklenir_sistemi_golgelemez(self):
        import filenor_sistem as S
        if S.WINDOWS:
            self.skipTest("posix")
        site = os.path.join(S.sanal_ortam_dizini(), "lib",
                            "python%d.%d" % sys.version_info[:2], "site-packages")
        os.makedirs(site, exist_ok=True)
        self.addCleanup(shutil.rmtree, os.path.join(_EV, ".local"), True)
        self.addCleanup(lambda: site in sys.path and sys.path.remove(site))
        S.sanal_ortam_yolu_ekle()
        self.assertEqual(sys.path[-1], site)
        S.sanal_ortam_yolu_ekle()                       # tekrar eklenmez
        self.assertEqual(sys.path.count(site), 1)

    def test_cli_izin_bayragi_ve_tty_yoksa_none(self):
        import argparse
        import filenor_cli as C
        self.assertTrue(C._pypi_izni(argparse.Namespace(pypi_izin=True))(["x"]))
        eski = C.sys.stdin
        try:
            C.sys.stdin = open(os.devnull)               # tty degil
            self.assertIsNone(C._pypi_izni(argparse.Namespace(pypi_izin=False)))
        finally:
            C.sys.stdin.close()
            C.sys.stdin = eski

    def test_cli_izin_yoksa_kurmadan_hata_verir(self):
        import argparse
        import filenor_cli as C
        import filenor_kurulum as K
        gercek = K._calistir
        cagrilar = []
        K._calistir = lambda *a, **k: cagrilar.append(a) or (0, "", [])
        try:
            with self.assertRaises(FilenorHata) as h:
                K.kur(K.Plan(pip=["rawpy"]), pypi_izin=C._pypi_izni(argparse.Namespace(pypi_izin=False))
                      if C.sys.stdin is None or not C.sys.stdin.isatty() else None)
        finally:
            K._calistir = gercek
        self.assertEqual(h.exception.kod, "kurulum_pypi_izin_yok")
        self.assertIn("--pypi-izin", hata_metni(h.exception, "tr"))
        self.assertEqual(cagrilar, [])

    def test_metinler_tr_en(self):
        from filenor_dil import MESAJ
        from filenor_metin import METIN as T
        for k in ("kurulum_pypi_reddedildi", "kurulum_pypi_izin_yok"):
            self.assertTrue(MESAJ[k]["tr"] and MESAJ[k]["en"])
        self.assertIn("PyPI", T["kur_pypi_metin"]["tr"])
        self.assertIn("PyPI", T["kur_pypi_metin"]["en"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
