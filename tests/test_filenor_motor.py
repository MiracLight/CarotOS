#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filenor motoru: GERCEK donusumlerle test (ffmpeg, LibreOffice, poppler, qpdf,
tesseract, Pillow, fontTools). Eksik arac/modul olan testler atlanir.

Calistirma:  python3 tests/test_filenor_motor.py
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filenor_yollar as Y  # noqa: E402
KOK, FN = Y.KOK, Y.FN
_EV = tempfile.mkdtemp(prefix="fn-ev-")
os.environ["HOME"] = _EV
os.environ["XDG_CONFIG_HOME"] = os.path.join(_EV, ".config")

import filenor_motor as M  # noqa: E402
import filenor_araclar as A  # noqa: E402
from filenor_dil import FilenorHata, Iptal, hata_metni  # noqa: E402

D = M.araclar_durumu()
VAR = lambda *a: all(D.get(x, False) for x in a)  # noqa: E731
need = lambda *a: unittest.skipUnless(VAR(*a), "eksik: " + ",".join(x for x in a if not D.get(x)))  # noqa: E731

DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
OTF_ORNEK = next(iter(sorted(glob.glob("/usr/share/texmf/fonts/opentype/public/lm/lmmono10-regular.otf")
                             + glob.glob("/usr/share/fonts/opentype/**/*.otf", recursive=True))), None)


def calis(*kom, **kw):
    return subprocess.run(list(kom), check=True, capture_output=True, **kw)


class Temel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kok = tempfile.mkdtemp(prefix="fn-test-")
        cls.girdi = os.path.join(cls.kok, "girdi")
        os.makedirs(cls.girdi)
        cls.oturum = M.Oturum()
        cls._fixtures()

    @classmethod
    def tearDownClass(cls):
        cls.oturum.kapat()
        shutil.rmtree(cls.kok, ignore_errors=True)

    def setUp(self):
        self.cikti = tempfile.mkdtemp(prefix="cikti-", dir=self.kok)

    def g(self, ad):
        return os.path.join(self.girdi, ad)

    def don(self, ad, hedef, **sec):
        return M.donustur(self.g(ad), hedef, self.cikti, M.Secenek.sozlukten(sec), self.oturum)

    def bir(self, ad, hedef, **sec):
        s = self.don(ad, hedef, **sec)
        self.assertEqual(len(s), 1, s)
        self.assertTrue(os.path.getsize(s[0]) > 0)
        return s[0]

    def gizli_kalinti_yok(self):
        self.assertEqual(glob.glob(os.path.join(self.cikti, ".filenor-*")), [])

    @classmethod
    def _fixtures(cls):
        g = cls.g.__get__(cls) if False else (lambda ad: os.path.join(cls.girdi, ad))
        if D["pillow"]:
            from PIL import Image
            im = Image.new("RGBA", (200, 100), (255, 0, 0, 0))   # tam saydam kirmizi
            for x in range(100):
                for y in range(100):
                    im.putpixel((x, y), (0, 0, 255, 255))         # sol yari opak mavi
            im.save(g("alfa.png"))
            # EXIF yonlendirmeli JPEG (orientation=6 -> 90 derece)
            j = Image.new("RGB", (200, 100), (10, 200, 10))
            ex = Image.Exif()
            ex[0x0112] = 6
            ex[0x010F] = "FilenorTest"
            j.save(g("yon.jpg"), exif=ex.tobytes())
            kareler = [Image.new("RGB", (64, 48), c) for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
            kareler[0].save(g("anim.gif"), save_all=True, append_images=kareler[1:], duration=100, loop=0)
            Image.new("RGB", (63, 47), (200, 100, 50)).save(g("tek.gif"))   # tek sayili boyut
            # OCR icin buyuk yazi
            from PIL import ImageDraw, ImageFont
            ocr = Image.new("RGB", (900, 220), "white")
            d = ImageDraw.Draw(ocr)
            try:
                f = ImageFont.truetype(DEJAVU, 90)
            except OSError:
                f = ImageFont.load_default()
            d.text((30, 50), "HELLO WORLD", fill="black", font=f)
            ocr.save(g("yazi.png"))
        if D["ffmpeg"]:
            calis("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", g("ses.wav"))
            calis("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
                  "-f", "lavfi", "-i", "sine=frequency=330:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                  "-c:a", "aac", "-shortest", g("video.mp4"))
            calis("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=1:size=161x121:rate=10",
                  "-c:v", "libx264", "-pix_fmt", "yuv444p", g("tuhaf.mkv"))
        if D["reportlab"]:
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(g("belge.pdf"))
            for i in range(1, 4):
                c.drawString(100, 700, f"Sayfa numarasi {i} merhaba")
                c.showPage()
            c.save()
            c = canvas.Canvas(g("diger.pdf"))
            c.drawString(100, 700, "Diger belge")
            c.showPage()
            c.save()
        with open(g("not.txt"), "w", encoding="cp1254") as f:      # Windows-Turkce kodlama
            f.write("Merhaba dünya ğüşiöç İĞÜŞÖÇ\nİkinci satır\n")
        with open(g("sayfa.html"), "w", encoding="utf-8") as f:
            f.write("<html><body><h1>Başlık ğ</h1><p>Paragraf ışık</p></body></html>")
        with open(g("tablo.csv"), "w", encoding="cp1254") as f:     # ; ayracli + Turkce
            f.write("ad;yaş;şehir\nAli;30;İstanbul\nAyşe;25;Çanakkale\n")
        if os.path.isfile(DEJAVU):
            shutil.copy(DEJAVU, g("font.ttf"))
        if OTF_ORNEK:
            shutil.copy(OTF_ORNEK, g("font.otf"))


# ---------------------------------------------------------------------------
class TabloVeKurallar(unittest.TestCase):
    def test_norm_ve_tur(self):
        self.assertEqual(M.norm(".JPEG"), "jpg")
        self.assertEqual(M.norm("TIF"), "tiff")
        self.assertEqual(M.tur("heic"), "gorsel")
        self.assertEqual(M.tur("cr2"), "ham")
        self.assertEqual(M.tur("xyz"), "")

    def test_hedefler_kendini_icermez_ve_tutarli(self):
        for e in M.kaynak_uzantilari():
            h = M.hedefler(e)
            self.assertTrue(h, e)
            self.assertNotIn(e, h, e)
            self.assertEqual(len(h), len(set(h)), e)
            for x in h:
                # her (kaynak, hedef) icin bir motor secilebilmeli
                self.assertTrue(callable(M._motor_sec(e, x)), (e, x))

    def test_ses_videoya_donmez(self):
        h = M.kontrol("mp3", "mp4")
        self.assertEqual(h.kod, "ses_video_degil")
        self.assertEqual(M.kontrol("png", "png").kod, "ayni_bicim")
        self.assertEqual(M.kontrol("png", "docx").kod, "desteklenmiyor")
        self.assertEqual(M.kontrol("xyz", "png").kod, "desteklenmiyor")

    def test_ozgun_surumde_yanlis_vaat_edilenler_artik_yok(self):
        # docx->pptx ve pdf->xlsx LibreOffice'te hic calismiyordu; listede olmamali
        self.assertNotIn("pptx", M.hedefler("docx"))
        self.assertNotIn("xlsx", M.hedefler("pdf"))
        self.assertNotIn("xlsx", M.hedefler("ppt"))

    def test_sayfa_listesi(self):
        self.assertEqual(M.sayfa_listesi("", 4), [1, 2, 3, 4])
        self.assertEqual(M.sayfa_listesi("1-2,4", 5), [1, 2, 4])
        self.assertEqual(M.sayfa_listesi("3-", 5), [3, 4, 5])
        self.assertEqual(M.sayfa_listesi("-2", 5), [1, 2])
        self.assertEqual(M.sayfa_listesi("3,1,3", 5), [3, 1])
        self.assertEqual(M.sayfa_listesi("2-9", 5), [2, 3, 4, 5])
        for kotu in ("0", "x", "5-2", "9", "1,,2", "--"):
            with self.assertRaises(FilenorHata, msg=kotu) as c:
                M.sayfa_listesi(kotu, 5)
            self.assertEqual(c.exception.kod, "sayfa_araligi")

    def test_benzersiz_yol_ezmez(self):
        d = tempfile.mkdtemp()
        try:
            a = M.benzersiz_yol(d, "x", "pdf")
            b = M.benzersiz_yol(d, "x", "pdf")
            c = M.benzersiz_yol(d, "x/../y", "pdf")
            self.assertEqual(os.path.basename(a), "x.pdf")
            self.assertEqual(os.path.basename(b), "x (1).pdf")
            self.assertEqual(os.path.dirname(c), d)
        finally:
            shutil.rmtree(d)

    def test_hata_metinleri_iki_dilde(self):
        h = FilenorHata("arac_eksik", arac="qpdf")
        self.assertIn("sudo apt install qpdf", hata_metni(h, "tr"))
        self.assertIn("needs", hata_metni(h, "en"))
        self.assertIn("1-3", hata_metni(FilenorHata("sayfa_araligi", aralik="x"), "tr"))

    def test_secenek_sozlukten_gecersizi_atar(self):
        s = M.Secenek.sozlukten({"kalite": "garip", "dpi": "abc", "bilinmeyen": 1, "max_kenar": "640"})
        self.assertEqual(s.kalite, "dengeli")
        self.assertEqual(s.dpi, 150)
        self.assertEqual(s.max_kenar, 640)


class Girdiler(Temel):
    def test_olmayan_bos_dosya(self):
        with self.assertRaises(FilenorHata) as c:
            M.donustur(os.path.join(self.kok, "yok.png"), "jpg", self.cikti)
        self.assertEqual(c.exception.kod, "dosya_yok")
        bos = os.path.join(self.girdi, "bos.png")
        open(bos, "w").close()
        with self.assertRaises(FilenorHata) as c:
            M.donustur(bos, "jpg", self.cikti)
        self.assertEqual(c.exception.kod, "dosya_bos")

    @need("pillow")
    def test_bozuk_gorsel_okunamadi_ve_kalinti_yok(self):
        kotu = os.path.join(self.girdi, "bozuk.png")
        with open(kotu, "wb") as f:
            f.write(b"bu bir png degil" * 10)
        with self.assertRaises(FilenorHata) as c:
            M.donustur(kotu, "jpg", self.cikti, None, self.oturum)
        self.assertEqual(c.exception.kod, "okunamadi")
        self.gizli_kalinti_yok()
        self.assertEqual(os.listdir(self.cikti), [])

    def test_yazilamaz_cikti(self):
        if os.geteuid() == 0:
            self.skipTest("root her yere yazar")
        d = os.path.join(self.kok, "salt")
        os.makedirs(d)
        os.chmod(d, 0o500)
        try:
            with self.assertRaises(FilenorHata) as c:
                M.donustur(self.g("not.txt"), "docx", d)
            self.assertEqual(c.exception.kod, "cikti_yazilamaz")
        finally:
            os.chmod(d, 0o700)


@need("pillow")
class Gorsel(Temel):
    def test_alfa_jpg_beyaz_zemin(self):
        from PIL import Image
        s = self.bir("alfa.png", "jpg")
        with Image.open(s) as im:
            self.assertEqual(im.mode, "RGB")
            r, g_, b = im.getpixel((150, 50))         # saydam bolge -> beyaz
            self.assertTrue(r > 240 and g_ > 240 and b > 240, (r, g_, b))
            r, g_, b = im.getpixel((50, 50))          # opak mavi korunmali
            self.assertTrue(b > 200 and r < 60, (r, g_, b))

    def test_exif_yonlendirme_piksellere_uygulanir(self):
        from PIL import Image
        s = self.bir("yon.jpg", "png")
        with Image.open(s) as im:
            self.assertEqual(im.size, (100, 200))     # 200x100 + orientation 6 -> 100x200

    def test_meta_korunur_ya_da_silinir(self):
        from PIL import Image
        korun = self.bir("yon.jpg", "webp")
        with Image.open(korun) as im:
            self.assertEqual(im.getexif().get(0x010F), "FilenorTest")
            self.assertEqual(im.getexif().get(0x0112, 1), 1)  # yonlendirme tekrar uygulanmasin
        temiz = self.bir("yon.jpg", "webp", meta_temizle=True)
        with Image.open(temiz) as im:
            self.assertNotIn(0x010F, dict(im.getexif()))

    def test_hedefler_dogru_bicimde(self):
        from PIL import Image
        for hedef, beklenen in (("jpg", "JPEG"), ("webp", "WEBP"), ("bmp", "BMP"),
                                ("tiff", "TIFF"), ("gif", "GIF"), ("ico", "ICO")):
            if hedef == "webp" and not D["webp"]:
                continue
            s = self.bir("alfa.png", hedef)
            with Image.open(s) as im:
                self.assertEqual(im.format, beklenen, hedef)
            self.assertTrue(s.endswith("." + hedef))

    @need("avif")
    def test_avif(self):
        from PIL import Image
        s = self.bir("alfa.png", "avif")
        with Image.open(s) as im:
            self.assertEqual(im.format, "AVIF")

    def test_ico_kare_ve_boyutlu(self):
        from PIL import Image
        s = self.bir("alfa.png", "ico")
        with Image.open(s) as im:
            self.assertEqual(im.size[0], im.size[1])
            self.assertTrue(max(im.info["sizes"])[0] <= 256)
            self.assertIn((16, 16), im.info["sizes"])

    def test_max_kenar_kucultur_buyutmez(self):
        from PIL import Image
        s = self.bir("alfa.png", "jpg", max_kenar=50)
        with Image.open(s) as im:
            self.assertEqual(max(im.size), 50)
        s2 = self.bir("alfa.png", "jpg", max_kenar=5000)
        with Image.open(s2) as im:
            self.assertEqual(im.size, (200, 100))

    def test_kalite_boyutu_etkiler(self):
        a = os.path.getsize(self.bir("yazi.png", "jpg", kalite="yuksek"))
        b = os.path.getsize(self.bir("yazi.png", "jpg", kalite="kucuk"))
        self.assertGreater(a, b)

    def test_animasyon_korunur_gif_webp(self):
        from PIL import Image
        if not D["webp"]:
            self.skipTest("webp yok")
        s = self.bir("anim.gif", "webp")
        with Image.open(s) as im:
            self.assertEqual(getattr(im, "n_frames", 1), 3)
        t = self.bir("anim.gif", "png")        # PNG'de ilk kare
        with Image.open(t) as im:
            self.assertEqual(im.size, (64, 48))

    def test_ayni_adli_kaynaklar_ezilmez(self):
        # alfa.png ve alfa.png.jpg degil; ayni govde adli iki farkli kaynak ayni hedefe
        shutil.copy(self.g("alfa.png"), os.path.join(self.girdi, "ayni.png"))
        shutil.copy(self.g("yon.jpg"), os.path.join(self.girdi, "ayni.jpg"))
        a = self.bir("ayni.png", "pdf")
        b = self.bir("ayni.jpg", "pdf")
        self.assertNotEqual(a, b)
        self.assertTrue(os.path.exists(a) and os.path.exists(b))

    def test_gorsel_pdf(self):
        s = self.bir("alfa.png", "pdf")
        self.assertEqual(M.pdf_bilgi(self.oturum, s)["sayfa"], 1)

    @need("ffmpeg")
    def test_gif_mp4_tek_sayili_boyut(self):
        s = self.bir("tek.gif", "mp4")          # 63x47 -> ozgun surumde ffmpeg hatasi
        self.assertGreater(M.medya_bilgi(self.oturum, s)["genislik"], 0)
        self.assertEqual(M.medya_bilgi(self.oturum, s)["genislik"] % 2, 0)
        self.bir("anim.gif", "webm")

    @need("svg")
    def test_svg(self):
        yol = os.path.join(self.girdi, "sekil.svg")
        with open(yol, "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"><rect width="100" height="50" fill="red"/></svg>')
        from PIL import Image
        s = M.donustur(yol, "png", self.cikti, None, self.oturum)[0]
        with Image.open(s) as im:
            self.assertEqual(im.format, "PNG")


@need("ffmpeg", "ffprobe")
class Medya(Temel):
    def test_ses_hedefleri(self):
        for hedef in ("mp3", "m4a", "opus", "flac", "ogg", "aac"):
            s = self.bir("ses.wav", hedef)
            b = M.medya_bilgi(self.oturum, s)
            self.assertTrue(b["ses"] and not b["video"], hedef)
            self.assertAlmostEqual(b["sure"], 2.0, delta=0.3, msg=hedef)

    def test_videodan_ses_ve_wav(self):
        s = self.bir("video.mp4", "mp3")
        self.assertFalse(M.medya_bilgi(self.oturum, s)["video"])
        self.bir("video.mp4", "wav")

    def test_video_hedefleri_ve_tek_sayili_boyut(self):
        s = self.bir("video.mp4", "mkv")
        self.assertTrue(M.medya_bilgi(self.oturum, s)["video"])
        t = self.bir("tuhaf.mkv", "mp4")            # 161x121 yuv444 -> ozgun surumde hata
        b = M.medya_bilgi(self.oturum, t)
        self.assertEqual((b["genislik"] % 2, b["yukseklik"] % 2), (0, 0))
        self.bir("video.mp4", "webm")

    def test_max_yukseklik(self):
        s = self.bir("video.mp4", "mkv", max_kenar=60)
        self.assertEqual(M.medya_bilgi(self.oturum, s)["yukseklik"], 60)

    def test_video_gif(self):
        from PIL import Image
        s = self.bir("video.mp4", "gif", gif_genislik=80, gif_fps=5)
        with Image.open(s) as im:
            self.assertEqual(im.format, "GIF")
            self.assertGreater(im.n_frames, 3)
            self.assertLessEqual(im.size[0], 80)

    def test_ilerleme_bildirilir(self):
        gelen = []
        with M.Oturum(ilerleme=lambda p, m: gelen.append(p)) as o:
            M.donustur(self.g("video.mp4"), "mkv", self.cikti, None, o)
        sayilar = [p for p in gelen if p is not None]
        self.assertEqual(sayilar[0], 0)
        self.assertEqual(sayilar[-1], 100)
        self.assertEqual(sayilar, sorted(sayilar))

    def test_iptal(self):
        uzun = os.path.join(self.girdi, "uzun.mp4")
        calis("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=duration=60:size=640x360:rate=30",
              "-c:v", "libx264", "-preset", "ultrafast", uzun)
        ev = threading.Event()
        threading.Timer(0.8, ev.set).start()
        t0 = time.time()
        with M.Oturum(iptal=ev) as o:
            with self.assertRaises(Iptal):
                M.donustur(uzun, "webm", self.cikti, M.Secenek(kalite="yuksek"), o)
        self.assertLess(time.time() - t0, 15)
        self.gizli_kalinti_yok()
        self.assertEqual(os.listdir(self.cikti), [])

    def test_zaman_asimi(self):
        uzun = os.path.join(self.girdi, "uzun2.mp4")
        calis("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=duration=60:size=640x360:rate=30",
              "-c:v", "libx264", "-preset", "ultrafast", uzun)
        with M.Oturum(zaman_asimi=1.0) as o:
            with self.assertRaises(FilenorHata) as c:
                M.donustur(uzun, "webm", self.cikti, M.Secenek(kalite="yuksek"), o)
        self.assertEqual(c.exception.kod, "zaman_asimi")
        self.gizli_kalinti_yok()

    def test_garip_dosya_adlari(self):
        for ad in ("100%d ses:a b'c.wav", "-tire basli.wav", "\u00e7\u011f \u015f\u0131.wav"):
            yol = os.path.join(self.girdi, ad)
            shutil.copy(self.g("ses.wav"), yol)
            s = M.donustur(yol, "mp3", self.cikti, None, self.oturum)[0]
            self.assertTrue(os.path.basename(s).endswith(".mp3"), s)
            self.assertAlmostEqual(M.medya_bilgi(self.oturum, s)["sure"], 2.0, delta=0.3)

    def test_bozuk_medya(self):
        kotu = os.path.join(self.girdi, "bozuk.mp3")
        with open(kotu, "wb") as f:
            f.write(os.urandom(2048))
        with self.assertRaises(FilenorHata) as c:
            M.donustur(kotu, "wav", self.cikti, None, self.oturum)
        self.assertIn(c.exception.kod, ("okunamadi", "arac_hata"))
        self.gizli_kalinti_yok()


@need("pdftoppm", "pdftotext", "qpdf", "pillow", "reportlab")
class Pdf(Temel):
    def test_pdf_png_sayfalar_klasore(self):
        s = self.don("belge.pdf", "png")
        self.assertEqual(len(s), 3)
        self.assertEqual(len({os.path.dirname(x) for x in s}), 1)
        self.assertTrue(os.path.basename(s[0]).startswith("sayfa_001"))
        self.assertTrue(os.path.basename(os.path.dirname(s[0])).startswith("belge"))

    def test_aralik_ve_tek_sayfa_dogrudan_dosya(self):
        s = self.don("belge.pdf", "jpg", sayfa_araligi="2")
        self.assertEqual(len(s), 1)
        self.assertEqual(os.path.dirname(s[0]), self.cikti)
        s = self.don("belge.pdf", "png", sayfa_araligi="1,3")
        self.assertEqual([os.path.basename(x)[:10] for x in s], ["sayfa_001.", "sayfa_003."])

    def test_pdf_webp(self):
        if not D["webp"]:
            self.skipTest("webp yok")
        self.assertEqual(len(self.don("belge.pdf", "webp", dpi=72)), 3)

    def test_pdf_metin(self):
        s = self.bir("belge.pdf", "txt")
        with open(s, encoding="utf-8") as f:
            self.assertIn("Sayfa numarasi 2", f.read())
        s = self.bir("belge.pdf", "txt", sayfa_araligi="3")
        with open(s, encoding="utf-8") as f:
            t = f.read()
        self.assertIn("numarasi 3", t)
        self.assertNotIn("numarasi 1", t)

    def test_metinsiz_pdf_anlamli_hata(self):
        # yalniz resim iceren PDF
        yol = os.path.join(self.girdi, "taranmis.pdf")
        from PIL import Image
        Image.new("RGB", (200, 200), "white").save(yol, "PDF")
        with self.assertRaises(FilenorHata) as c:
            M.donustur(yol, "txt", self.cikti, None, self.oturum)
        self.assertEqual(c.exception.kod, "metin_yok")

    def test_parola_korumali(self):
        kor = os.path.join(self.girdi, "kilitli.pdf")
        calis("qpdf", "--encrypt", "gizli", "gizli", "256", "--", self.g("belge.pdf"), kor)
        with self.assertRaises(FilenorHata) as c:
            M.donustur(kor, "png", self.cikti, None, self.oturum)
        self.assertEqual(c.exception.kod, "sifreli_pdf")
        with self.assertRaises(FilenorHata) as c:
            M.donustur(kor, "png", self.cikti, M.Secenek(parola="yanlis"), self.oturum)
        self.assertEqual(c.exception.kod, "sifreli_pdf")
        s = M.donustur(kor, "txt", self.cikti, M.Secenek(parola="gizli"), self.oturum)
        with open(s[0], encoding="utf-8") as f:
            self.assertIn("Sayfa numarasi 1", f.read())
        self.gizli_kalinti_yok()

    @need("libreoffice")
    def test_pdf_docx_pptx_odt_odp(self):
        for hedef in ("docx", "odt", "pptx", "odp"):
            s = self.bir("belge.pdf", hedef)
            self.assertTrue(zipfile.is_zipfile(s), hedef)
        with zipfile.ZipFile(self.bir("belge.pdf", "docx")) as z:
            self.assertIn("word/document.xml", z.namelist())
        with zipfile.ZipFile(self.bir("belge.pdf", "pptx")) as z:
            self.assertTrue(any(n.startswith("ppt/slides/slide") for n in z.namelist()))


@need("libreoffice")
class Ofis(Temel):
    def metin_ara(self, yol, aranan):
        """zip tabanli ofis dosyasinda aranan metni bul"""
        with zipfile.ZipFile(yol) as z:
            return any(aranan in z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))

    def test_txt_docx_odt_rtf_html_turkce(self):
        d = self.bir("not.txt", "docx")
        self.assertTrue(self.metin_ara(d, "ğüşiöç"))
        self.assertTrue(self.metin_ara(d, "İĞÜŞÖÇ"))
        o = self.bir("not.txt", "odt")
        self.assertTrue(self.metin_ara(o, "ğüşiöç"))
        r = self.bir("not.txt", "rtf")
        with open(r, "rb") as f:
            self.assertTrue(f.read(5).startswith(b"{\\rtf"))
        h = self.bir("not.txt", "html")
        with open(h, encoding="utf-8", errors="replace") as f:
            self.assertIn("dünya", f.read())

    def test_docx_txt_gidis_donus_bom_yok(self):
        d = self.bir("not.txt", "docx")
        kopya = os.path.join(self.girdi, "gidis.docx")
        shutil.copy(d, kopya)
        t = M.donustur(kopya, "txt", self.cikti, None, self.oturum)[0]
        with open(t, "rb") as f:
            ham = f.read()
        self.assertFalse(ham.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Merhaba dünya".encode(), ham)

    def test_docx_pdf(self):
        d = self.bir("not.txt", "docx")
        kopya = os.path.join(self.girdi, "yazi.docx")
        shutil.copy(d, kopya)
        p = M.donustur(kopya, "pdf", self.cikti, None, self.oturum)[0]
        self.assertEqual(M.pdf_bilgi(self.oturum, p)["sayfa"], 1)

    def test_html_pdf_docx(self):
        p = self.bir("sayfa.html", "pdf")
        self.assertEqual(M.pdf_bilgi(self.oturum, p)["sayfa"], 1)
        d = self.bir("sayfa.html", "docx")        # ozgun surumde NameError
        self.assertTrue(self.metin_ara(d, "Paragraf"))
        t = self.bir("sayfa.html", "txt")
        with open(t, encoding="utf-8") as f:
            self.assertIn("Başlık", f.read())

    def test_csv_noktalivirgul_turkce_xlsx_ods_pdf_html(self):
        x = self.bir("tablo.csv", "xlsx")
        self.assertTrue(self.metin_ara(x, "İstanbul"))
        self.assertTrue(self.metin_ara(x, "Çanakkale"))
        self.bir("tablo.csv", "ods")
        p = self.bir("tablo.csv", "pdf")
        self.assertGreaterEqual(M.pdf_bilgi(self.oturum, p)["sayfa"], 1)
        h = self.bir("tablo.csv", "html")
        with open(h, encoding="utf-8", errors="replace") as f:
            self.assertIn("stanbul", f.read())

    def test_xlsx_csv_tek_sayfa_tek_dosya(self):
        x = self.bir("tablo.csv", "xlsx")
        kopya = os.path.join(self.girdi, "tam.xlsx")
        shutil.copy(x, kopya)
        c = self.bir("tam.xlsx", "csv")
        with open(c, encoding="utf-8") as f:
            self.assertIn("İstanbul", f.read())

    def test_txt_pdf_reportlab_turkce_cok_sayfa(self):
        uzun = os.path.join(self.girdi, "uzun.txt")
        with open(uzun, "w", encoding="utf-8") as f:
            for i in range(200):
                f.write(f"Satır {i}: şğıİöç " + "uzun " * 30 + "\n")
        p = M.donustur(uzun, "pdf", self.cikti, None, self.oturum)[0]
        self.assertGreater(M.pdf_bilgi(self.oturum, p)["sayfa"], 3)     # tek sayfaya sigmaz
        if D["pdftotext"]:
            t = subprocess.run(["pdftotext", p, "-"], capture_output=True, text=True).stdout
            self.assertIn("şğıİöç", t)

    @need("pdftoppm")
    def test_pptx_slayt_gorselleri(self):
        # sunum uret: pdf -> pptx
        pp = M.donustur(self.g("belge.pdf"), "pptx", self.cikti, None, self.oturum)[0]
        kopya = os.path.join(self.girdi, "sunum.pptx")
        shutil.copy(pp, kopya)
        s = M.donustur(kopya, "png", self.cikti, M.Secenek(dpi=60), self.oturum)
        self.assertEqual(len(s), 3)
        self.assertIn("slayt_001", os.path.basename(s[0]))
        p = M.donustur(kopya, "pdf", self.cikti, None, self.oturum)[0]
        self.assertEqual(M.pdf_bilgi(self.oturum, p)["sayfa"], 3)

    def test_lo_eszamanli_profil_kilidi_yok(self):
        # iki ayri oturum ayni anda: kendi profilleri var
        sonuc = {}

        def is_(ad):
            with M.Oturum() as o:
                try:
                    sonuc[ad] = M.donustur(self.g("not.txt"), "docx", self.cikti, None, o)
                except Exception as e:  # noqa: BLE001
                    sonuc[ad] = e
        ts = [threading.Thread(target=is_, args=(i,)) for i in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        for v in sonuc.values():
            self.assertIsInstance(v, list, v)
        self.assertEqual(len({x for v in sonuc.values() for x in v}), 2)


@need("fonttools")
class Yazi(Temel):
    def setUp(self):
        super().setUp()
        if not os.path.isfile(self.g("font.ttf")):
            self.skipTest("DejaVu yok")

    def test_ttf_woff_ve_geri(self):
        from fontTools.ttLib import TTFont
        w = self.bir("font.ttf", "woff")
        self.assertEqual(TTFont(w).flavor, "woff")
        kopya = os.path.join(self.girdi, "w.woff")
        shutil.copy(w, kopya)
        t = M.donustur(kopya, "ttf", self.cikti, None, self.oturum)[0]
        f = TTFont(t)
        self.assertIsNone(f.flavor)
        self.assertIn("glyf", f)
        self.assertEqual(len(f.getGlyphOrder()), len(TTFont(self.g("font.ttf")).getGlyphOrder()))

    @need("brotli")
    def test_woff2(self):
        from fontTools.ttLib import TTFont
        self.assertEqual(TTFont(self.bir("font.ttf", "woff2")).flavor, "woff2")

    def test_ttf_otf_durust_hata(self):
        # Ozgun surum TTF'i .otf adiyla kaydediyordu (gecersiz). Artik acik hata.
        with self.assertRaises(FilenorHata) as c:
            M.donustur(self.g("font.ttf"), "otf", self.cikti, None, self.oturum)
        self.assertEqual(c.exception.kod, "yazi_tur")
        self.assertEqual(os.listdir(self.cikti), [])

    def test_otf_ttf_gercek_donusum(self):
        if not os.path.isfile(self.g("font.otf")):
            self.skipTest("OTF ornegi yok")
        from fontTools.ttLib import TTFont
        t = self.bir("font.otf", "ttf")
        f = TTFont(t)
        self.assertIn("glyf", f)
        self.assertNotIn("CFF ", f)
        self.assertEqual(f.sfntVersion, "\x00\x01\x00\x00")
        f.getGlyphSet()["A"] if "A" in f.getGlyphOrder() else None
        # yeniden kaydedilip okunabiliyor mu
        f.save(os.path.join(self.cikti, "tekrar.ttf"))
        TTFont(os.path.join(self.cikti, "tekrar.ttf"))

    def test_bozuk_font(self):
        kotu = os.path.join(self.girdi, "bozuk.ttf")
        with open(kotu, "wb") as f:
            f.write(b"\x00\x01\x00\x00" + os.urandom(100))
        with self.assertRaises(FilenorHata) as c:
            M.donustur(kotu, "woff", self.cikti, None, self.oturum)
        self.assertIn(c.exception.kod, ("okunamadi", "arac_hata"))


# ---------------------------------------------------------------------------
@need("qpdf", "pdfinfo", "pillow", "reportlab")
class Araclar(Temel):
    def sayfa(self, yol):
        return M.pdf_bilgi(self.oturum, yol)["sayfa"]

    def test_birlestir_pdf_ve_gorsel(self):
        s = A.arac_calistir("pdf_birlestir", [self.g("belge.pdf"), self.g("alfa.png"), self.g("diger.pdf")],
                            self.cikti, None, self.oturum)
        self.assertEqual(len(s), 1)
        self.assertTrue(os.path.basename(s[0]).startswith("birlesik"))
        self.assertEqual(self.sayfa(s[0]), 3 + 1 + 1)
        with self.assertRaises(FilenorHata) as c:
            A.arac_calistir("pdf_birlestir", [self.g("belge.pdf")], self.cikti, None, self.oturum)
        self.assertEqual(c.exception.kod, "en_az_bir")

    def test_bol(self):
        s = A.arac_calistir("pdf_bol", [self.g("belge.pdf")], self.cikti, M.Secenek(parca=1), self.oturum)
        self.assertEqual(len(s), 3)
        self.assertTrue(all(self.sayfa(x) == 1 for x in s))
        s2 = A.arac_calistir("pdf_bol", [self.g("belge.pdf")], self.cikti, M.Secenek(parca=2), self.oturum)
        self.assertEqual(sorted(self.sayfa(x) for x in s2), [1, 2])

    def test_sayfa_sec_ve_sirala(self):
        s = A.arac_calistir("pdf_sayfa_sec", [self.g("belge.pdf")], self.cikti, M.Secenek(sayfa_araligi="3,1"), self.oturum)
        self.assertEqual(self.sayfa(s[0]), 2)
        t = subprocess.run(["pdftotext", s[0], "-"], capture_output=True, text=True).stdout
        self.assertLess(t.index("numarasi 3"), t.index("numarasi 1"))
        with self.assertRaises(FilenorHata) as c:
            A.arac_calistir("pdf_sayfa_sec", [self.g("belge.pdf")], self.cikti, M.Secenek(sayfa_araligi="7"), self.oturum)
        self.assertEqual(c.exception.kod, "sayfa_araligi")

    def test_dondur(self):
        from pypdf import PdfReader
        s = A.arac_calistir("pdf_dondur", [self.g("belge.pdf")], self.cikti, M.Secenek(derece=90, sayfa_araligi="2"), self.oturum)
        r = PdfReader(s[0])
        self.assertEqual([p.get("/Rotate", 0) for p in r.pages], [0, 90, 0])

    def test_kucult_asla_buyutmez(self):
        s = A.arac_calistir("pdf_kucult", [self.g("belge.pdf")], self.cikti, None, self.oturum)
        self.assertLessEqual(os.path.getsize(s[0]), os.path.getsize(self.g("belge.pdf")))
        self.assertEqual(self.sayfa(s[0]), 3)

    def test_kilitle_ve_ac(self):
        k = A.arac_calistir("pdf_kilitle", [self.g("belge.pdf")], self.cikti, M.Secenek(yeni_parola="abc123"), self.oturum)[0]
        with self.assertRaises(FilenorHata) as c:
            M.pdf_bilgi(self.oturum, k)
        self.assertEqual(c.exception.kod, "sifreli_pdf")
        kopya = os.path.join(self.girdi, "k.pdf")
        shutil.copy(k, kopya)
        with self.assertRaises(FilenorHata) as c:
            A.arac_calistir("pdf_kilit_ac", [kopya], self.cikti, M.Secenek(parola="yanlis"), self.oturum)
        self.assertEqual(c.exception.kod, "sifreli_pdf")
        a = A.arac_calistir("pdf_kilit_ac", [kopya], self.cikti, M.Secenek(parola="abc123"), self.oturum)[0]
        self.assertEqual(self.sayfa(a), 3)
        self.gizli_kalinti_yok()

    def test_yanlis_girdi_turu_reddedilir(self):
        with self.assertRaises(FilenorHata):
            A.arac_calistir("pdf_dondur", [self.g("not.txt")], self.cikti, None, self.oturum)

    @need("tesseract")
    def test_ocr_gorsel_ve_pdf(self):
        if "eng" not in A.ocr_dilleri():
            self.skipTest("tesseract eng yok")
        sec = M.Secenek(ocr_dil="eng")
        t = A.arac_calistir("ocr", [self.g("yazi.png")], self.cikti, sec, self.oturum)[0]
        with open(t, encoding="utf-8") as f:
            self.assertIn("HELLO", f.read().upper())
        p = A.arac_calistir("ocr", [self.g("yazi.png")], self.cikti, M.Secenek(ocr_dil="eng", ocr_cikti="pdf"), self.oturum)[0]
        self.assertEqual(self.sayfa(p), 1)
        # aranabilir PDF'ten metin cikmali
        txt = subprocess.run(["pdftotext", p, "-"], capture_output=True, text=True).stdout.upper()
        self.assertIn("HELLO", txt)

    @need("tesseract")
    def test_ocr_olmayan_dil(self):
        with self.assertRaises(FilenorHata) as c:
            A.arac_calistir("ocr", [self.g("yazi.png")], self.cikti, M.Secenek(ocr_dil="klingon"), self.oturum)
        self.assertEqual(c.exception.kod, "ocr_dil")

    def test_gorsel_kucult(self):
        s = A.arac_calistir("gorsel_kucult", [self.g("yon.jpg")], self.cikti, M.Secenek(meta_temizle=True, max_kenar=80), self.oturum)[0]
        from PIL import Image
        with Image.open(s) as im:
            self.assertEqual(max(im.size), 80)
            self.assertNotIn(0x010F, dict(im.getexif()))
        self.assertTrue(s.endswith(".jpg"))
        # buyuk jpg'yi kucuk kaliteyle yazinca asla buyumemeli
        s2 = A.arac_calistir("gorsel_kucult", [self.g("yazi.png")], self.cikti, M.Secenek(), self.oturum)[0]
        self.assertLessEqual(os.path.getsize(s2), os.path.getsize(self.g("yazi.png")))

    @need("ffmpeg", "ffprobe")
    def test_medya_kirp(self):
        s = A.arac_calistir("medya_kirp", [self.g("video.mp4")], self.cikti, M.Secenek(baslangic=0.5, bitis=1.5), self.oturum)[0]
        self.assertAlmostEqual(M.medya_bilgi(self.oturum, s)["sure"], 1.0, delta=0.35)
        with self.assertRaises(FilenorHata) as c:
            A.arac_calistir("medya_kirp", [self.g("video.mp4")], self.cikti, M.Secenek(baslangic=2, bitis=1), self.oturum)
        self.assertEqual(c.exception.kod, "kirp_gecersiz")


# ---------------------------------------------------------------------------
@need("pillow")
class KosucuTesti(Temel):
    def test_toplu_karisik_basari_hata_ve_zip(self):
        kotu = os.path.join(self.girdi, "kotu2.png")
        with open(kotu, "wb") as f:
            f.write(b"x" * 100)
        isler = [M.Is(self.g("alfa.png"), "jpg"), M.Is(kotu, "jpg"), M.Is(self.g("yon.jpg"), "png")]
        olaylar = []
        bitti = threading.Event()
        k = M.Kosucu(isler, self.cikti, M.Secenek(zip_yap=True), is_cb=lambda i, is_: olaylar.append((i, is_.durum)),
                     bitti_cb=lambda _: bitti.set())
        k.start()
        self.assertTrue(bitti.wait(60))
        self.assertEqual([i.durum for i in isler], ["tamam", "hata", "tamam"])
        self.assertEqual(isler[1].hata.kod, "okunamadi")
        self.assertTrue(k.zip_yolu and zipfile.is_zipfile(k.zip_yolu))
        with zipfile.ZipFile(k.zip_yolu) as z:
            self.assertEqual(len(z.namelist()), 2)
        self.assertIn((0, "calisiyor"), olaylar)
        self.assertGreater(isler[0].boyut_sonra, 0)
        self.gizli_kalinti_yok()

    def test_yanina_kaydet(self):
        d = tempfile.mkdtemp(dir=self.kok)
        shutil.copy(self.g("alfa.png"), os.path.join(d, "yan.png"))
        isler = [M.Is(os.path.join(d, "yan.png"), "jpg")]
        bitti = threading.Event()
        M.Kosucu(isler, None, M.Secenek(), bitti_cb=lambda _: bitti.set(), yanina=True).start()
        self.assertTrue(bitti.wait(30))
        self.assertTrue(os.path.exists(os.path.join(d, "yan.jpg")))

    def test_iptal_kalan_isler_iptal(self):
        isler = [M.Is(self.g("alfa.png"), "jpg") for _ in range(3)]
        bitti = threading.Event()
        k = M.Kosucu(isler, self.cikti, M.Secenek(), bitti_cb=lambda _: bitti.set())
        k.iptal_et()
        k.start()
        self.assertTrue(bitti.wait(10))
        self.assertEqual([i.durum for i in isler], ["iptal"] * 3)

    def test_ayarlar_gidis_donus(self):
        M.ayar_yaz({"dil": "en", "x": [1, 2]})
        self.assertEqual(M.ayar_oku()["dil"], "en")
        os.remove(M.ayar_yolu())
        self.assertEqual(M.ayar_oku(), {})


@need("pillow")
class KomutSatiri(Temel):
    CLI = os.path.join(FN, "filenor-cli")

    def cli(self, *a, env=None):
        e = dict(os.environ)
        e.update(env or {})
        return subprocess.run([sys.executable, self.CLI] + list(a), capture_output=True, text=True, env=e, timeout=300)

    def test_durum_ve_formatlar(self):
        r = self.cli("durum", "--json")
        self.assertEqual(r.returncode, 0)
        import json
        self.assertIn("ffmpeg", json.loads(r.stdout))
        r = self.cli("formatlar", "jpeg")
        self.assertIn("webp", r.stdout.split())
        self.assertEqual(self.cli("formatlar", "xyz").returncode, 2)
        self.assertIn("pdf_birlestir", self.cli("araclar").stdout)

    def test_kur_komutu_deneme_ve_hatalar(self):
        r = self.cli("kur", "--deneme")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.cli("kur", "olmayan-arac").returncode, 2)
        # kurulu bir arac icin kurulacak bir sey yok
        if D.get("qpdf"):
            r = self.cli("kur", "qpdf", "--deneme", env={"LANG": "en_US.UTF-8"})
            self.assertEqual(r.returncode, 0)
            self.assertNotIn("qpdf", r.stdout.split("to install:")[-1] if "to install" in r.stdout else "")

    def test_donustur_cikis_kodlari_ve_json(self):
        import json
        r = self.cli("donustur", "-t", "webp", "-o", self.cikti, self.g("alfa.png"), self.g("yon.jpg"), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        veri = json.loads(r.stdout)
        self.assertEqual([x["durum"] for x in veri], ["tamam", "tamam"])
        self.assertEqual(sorted(os.listdir(self.cikti)), ["alfa.webp", "yon.webp"])
        # bir hatali + bir basarili -> kod 1, basarili olan yine uretilir
        r = self.cli("donustur", "-t", "png", "-o", self.cikti, self.g("alfa.png"), self.g("yon.jpg"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("yon.png", " ".join(os.listdir(self.cikti)))
        self.assertIn("HATA", r.stderr)

    def test_arac_ve_ortam_parolasi(self):
        if not (D["qpdf"] and D["pdfinfo"]):
            self.skipTest("qpdf yok")
        kilitli = os.path.join(self.girdi, "cli_kilitli.pdf")
        calis("qpdf", "--encrypt", "pw1", "pw1", "256", "--", self.g("belge.pdf") if os.path.exists(self.g("belge.pdf"))
              else self._pdf(), kilitli)
        r = self.cli("arac", "pdf_kilit_ac", kilitli, "-o", self.cikti, env={"FILENOR_PAROLA": "pw1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.cli("arac", "pdf_kilit_ac", kilitli, "-o", self.cikti, env={"FILENOR_PAROLA": "yanlis"})
        self.assertEqual(r.returncode, 1)
        r = self.cli("arac", "pdf_birlestir", kilitli, "-o", self.cikti)
        self.assertEqual(r.returncode, 2)               # en az 2 dosya
        self.assertEqual(self.cli("arac", "yok", "x").returncode, 2)

    def _pdf(self):
        from PIL import Image
        yol = os.path.join(self.girdi, "cli_tek.pdf")
        Image.new("RGB", (50, 50), "white").save(yol, "PDF")
        return yol


class MetinTutarli(unittest.TestCase):
    """filenor_metin: iki dil, ayni anahtar, ayni yer tutucular; kodda kullanilan her anahtar var."""

    def test_diller_ve_yer_tutucular(self):
        import re
        import filenor_metin
        for k, v in filenor_metin.M.items():
            self.assertEqual(set(v), {"tr", "en"}, k)
            yt = lambda m: sorted(re.findall(r"\{(\w+)\}", m))  # noqa: E731
            self.assertEqual(yt(v["tr"]), yt(v["en"]), k)
            self.assertTrue(v["tr"].strip() and v["en"].strip(), k)

    def test_kodda_kullanilan_anahtarlar_var(self):
        import re
        import filenor_metin
        M_ = filenor_metin.M
        with open(os.path.join(FN, "filenor_uygulama.py"), encoding="utf-8") as f:
            kod = f.read()
        for k in set(re.findall(r'\bt\("([a-z_0-9]+)"', kod)):
            if k.endswith("_") or k in ("changed", "destroy", "toggled"):
                continue
            self.assertIn(k, M_, k)
        # dinamik onekler
        for s_ in ("donustur", "araclar", "ayar"):
            self.assertIn("baslik_" + s_, M_)
            self.assertIn("alt_" + s_, M_)
        for kat in M.KATEGORILER:
            self.assertIn("kat_" + kat, M_)
        for ad, d in A.ARACLAR.items():
            self.assertEqual(set(d["ad"]), {"tr", "en"}, ad)
            self.assertEqual(set(d["ac"]), {"tr", "en"}, ad)
            for o in d["sec"]:
                self.assertIn("sec_" + o, M_, (ad, o))
        for k in ("ffmpeg", "libreoffice", "pdftoppm", "qpdf", "tesseract", "pillow", "reportlab", "fonttools",
                  "brotli", "svg", "avif", "rawpy", "heif", "gs"):
            self.assertIn("ar_" + k, M_)

    def test_hata_mesajlari_tam(self):
        import filenor_dil as Dd
        for k, v in Dd.MESAJ.items():
            self.assertEqual(set(v), {"tr", "en"}, k)
        for k, v in Dd.ARAC_IPUCU.items():
            self.assertEqual(set(v), {"tr", "en"}, k)
        # motorun attigi her kod tanimli
        import re
        for dosya in ("filenor_motor.py", "filenor_araclar.py"):
            with open(os.path.join(FN, dosya), encoding="utf-8") as f:
                kod = f.read()
            for k in set(re.findall(r'FilenorHata\("([a-z_]+)"', kod)):
                self.assertIn(k, Dd.MESAJ, k)
        # her arac_eksik ipucu anahtari var
        for g in ("ffmpeg", "ffprobe", "libreoffice", "pdftoppm", "pdftotext", "pdfinfo", "qpdf", "tesseract",
                  "pillow", "reportlab", "fonttools", "brotli", "svg", "rawpy", "heif", "avif", "pypdf", "gs"):
            self.assertIn(g, Dd.ARAC_IPUCU, g)
        for ext in M.kaynak_uzantilari():
            for h in M.hedefler(ext):
                for g in M.gerekli(ext, h):
                    for x in g.split("|"):
                        self.assertIn(x, M.araclar_durumu(), (ext, h, x))
                        self.assertIn(x, Dd.ARAC_IPUCU, (ext, h, x))


if __name__ == "__main__":
    unittest.main(verbosity=1)
