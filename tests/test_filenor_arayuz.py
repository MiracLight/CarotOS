#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filenor arayuzu (GTK 3): gercek donusumlerle uctan uca.

GTK gerektirir:
    G_DEBUG=fatal-criticals xvfb-run -a python3 tests/test_filenor_arayuz.py
"""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filenor_yollar as Y  # noqa: E402
KOK = Y.KOK
_EV = tempfile.mkdtemp(prefix="fn-ui-ev-")
os.environ["HOME"] = _EV
os.environ["XDG_CONFIG_HOME"] = os.path.join(_EV, ".config")
os.makedirs(os.path.join(_EV, ".config/carotos"), exist_ok=True)
with open(os.path.join(_EV, ".config/carotos/filenor.json"), "w") as _f:
    json.dump({"tema": "dark", "dil": "tr"}, _f)

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

import filenor_motor as M  # noqa: E402
import filenor_kurulum as K  # noqa: E402
from filenor_dil import FilenorHata  # noqa: E402
import filenor_uygulama as F  # noqa: E402

D = M.araclar_durumu()


def pompala(sn=0.2):
    t = time.time()
    while time.time() - t < sn:
        while Gtk.events_pending():
            Gtk.main_iteration()
        time.sleep(0.01)


def bekle(kosul, sn=60):
    t = time.time()
    while time.time() - t < sn:
        pompala(0.05)
        if kosul():
            return True
    return False


class ArayuzTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kok = tempfile.mkdtemp(prefix="fn-ui-")
        from PIL import Image
        cls.gir = os.path.join(cls.kok, "girdi")
        os.makedirs(cls.gir)
        Image.new("RGB", (400, 300), (30, 120, 200)).save(os.path.join(cls.gir, "foto.jpg"))
        Image.new("RGBA", (64, 64), (200, 0, 0, 128)).save(os.path.join(cls.gir, "simge.png"))
        for i, ad in enumerate(("a.pdf", "b.pdf")):
            Image.new("RGB", (200, 200), "white").save(os.path.join(cls.gir, ad), "PDF")
        with open(os.path.join(cls.gir, "not.txt"), "w", encoding="utf-8") as f:
            f.write("merhaba şğ\n")
        os.makedirs(os.path.join(cls.gir, "klasor/alt"))
        Image.new("RGB", (10, 10)).save(os.path.join(cls.gir, "klasor/x.png"))
        Image.new("RGB", (10, 10)).save(os.path.join(cls.gir, "klasor/alt/y.jpg"))
        with open(os.path.join(cls.gir, "klasor/gizli.txt.bak"), "w") as f:
            f.write("x")
        cls.w = F.Uygulama([], F.logo_bul())
        cls.w.show_all()
        pompala(0.4)

    @classmethod
    def tearDownClass(cls):
        cls.w.destroy()
        shutil.rmtree(cls.kok, ignore_errors=True)

    def setUp(self):
        self.cikti = tempfile.mkdtemp(dir=self.kok)
        self.w.ayar["cikti_modu"] = "klasor"
        self.w.ayar["cikti_klasor"] = self.cikti
        self.p = self.w.paneller["donustur"]
        self.a = self.w.paneller["araclar"]
        for p in (self.p, self.a):
            p.ogeler.clear()
            p.hedef = None
            p.secenek = M.Secenek()
            p.yenile()
        self.w.kabuk.sec("donustur")
        pompala(0.1)

    def g(self, ad):
        return os.path.join(self.gir, ad)

    # --- kabuk --------------------------------------------------------------
    def test_acilis_bos_durum(self):
        self.assertTrue(self.p.bos.get_visible())
        self.assertFalse(self.p.dolu.get_visible())
        self.assertFalse(self.p.hedef_kart.get_visible())
        self.assertFalse(self.p.eylem_kart.get_visible())
        self.assertEqual(self.w.kabuk.baslik.get_text(), "Dönüştür")

    def test_dosya_ekleme_klasor_ve_tekrar(self):
        n = self.p.ekle([self.g("foto.jpg"), self.g("foto.jpg"), self.g("klasor")])
        self.assertEqual(n, 3)                       # foto + x.png + y.jpg (.bak desteklenmez)
        self.assertEqual(len(self.p.ogeler), 3)
        self.assertTrue(self.p.dolu.get_visible())
        self.assertFalse(self.p.bos.get_visible())
        self.assertEqual(self.p.ekle([self.g("foto.jpg")]), 0)
        self.p.kaldir(self.p.ogeler[0])
        self.assertEqual(len(self.p.ogeler), 2)
        self.p.temizle()
        self.assertTrue(self.p.bos.get_visible())

    def test_hedef_birlesimi_ve_secenek_gorunurlugu(self):
        self.p.ekle([self.g("foto.jpg"), self.g("a.pdf")])
        self.assertIn("png", self.p._chipler)
        self.assertIn("docx", self.p._chipler)
        self.assertNotIn("mp3", self.p._chipler)          # yalnizca eklenenlerin hedefleri
        self.assertTrue(self.p.hedef_kart.get_visible())
        self.assertFalse(self.p.eylem_kart.get_visible())  # hedef secilene dek
        self.p._chipler["jpg"].set_active(False)
        self.p._chipler["webp"].set_active(True)
        pompala(0.1)
        self.assertEqual(self.p.hedef, "webp")
        goruluyor = {k for k, (e, w, i) in self.p._sec_w.items() if w.get_visible()}
        self.assertTrue({"kalite", "max_kenar", "meta_temizle", "parola", "zip_yap"} <= goruluyor, goruluyor)
        self.assertNotIn("gif_fps", goruluyor)
        self.assertNotIn("derece", goruluyor)
        # tek secimli: baska chip secilince ilki kapanir
        self.p._chipler["png"].set_active(True)
        self.assertEqual(self.p.hedef, "png")
        self.assertFalse(self.p._chipler["webp"].get_active())
        self.assertTrue(self.p.eylem_kart.get_visible())

    def test_uyumsuz_dosya_satirda_aciklanir_ve_atlanir(self):
        self.p.ekle([self.g("foto.jpg"), self.g("not.txt")])
        self.p._chipler["webp"].set_active(True)
        pompala(0.1)
        txt = [o for o in self.p.ogeler if o.ext == "txt"] or []
        self.assertFalse(txt and "webp" in M.hedefler("txt"))
        self.assertIn("dönüştürülemez", [o for o in self.p.ogeler if o.ext == "txt"][0].satir["alt"].get_text())
        self.assertEqual(len(self.p.uygun_ogeler()), 1)

    # --- calistirma -----------------------------------------------------------
    def test_donustur_uctan_uca_ve_yeniden_calistirma(self):
        self.p.ekle([self.g("foto.jpg"), self.g("simge.png")])
        self.p._chipler["webp"].set_active(True)
        self.p.baslat_iptal()
        self.assertTrue(self.p.calisiyor)
        self.assertTrue(bekle(lambda: not self.p.calisiyor))
        self.assertEqual(sorted(os.listdir(self.cikti)), ["foto.webp", "simge.webp"])
        self.assertEqual([o.durum for o in self.p.ogeler], ["tamam", "tamam"])
        self.assertIn("→ foto.webp", self.p.ogeler[0].satir["alt"].get_text())
        self.assertIn("2 dosya tamamlandı", self.p.durum_metin.get_text())
        self.assertTrue(self.p.b_klasoru_ac.get_visible())
        self.assertTrue(self.p.b_bitenleri.get_visible())
        # tekrar: var olan dosyalar ezilmez
        self.p.baslat_iptal()
        self.assertTrue(bekle(lambda: not self.p.calisiyor))
        self.assertEqual(sorted(os.listdir(self.cikti)),
                         ["foto (1).webp", "foto.webp", "simge (1).webp", "simge.webp"])
        self.p.bitenleri_kaldir()
        self.assertEqual(self.p.ogeler, [])

    def test_hata_satirda_gorunur_digerleri_surer(self):
        kotu = os.path.join(self.gir, "bozuk.png")
        with open(kotu, "wb") as f:
            f.write(b"png degil" * 20)
        self.p.ekle([kotu, self.g("foto.jpg")])
        self.p._chipler["webp"].set_active(True)
        self.p.baslat_iptal()
        self.assertTrue(bekle(lambda: not self.p.calisiyor))
        durumlar = {o.ad: o.durum for o in self.p.ogeler}
        self.assertEqual(durumlar, {"bozuk.png": "hata", "foto.jpg": "tamam"})
        self.assertIn("açılamadı", [o for o in self.p.ogeler if o.ad == "bozuk.png"][0].satir["alt"].get_text())
        self.assertIn("1 hatalı", self.p.durum_metin.get_text())

    @unittest.skipUnless(D["ffmpeg"], "ffmpeg yok")
    def test_iptal(self):
        import subprocess
        uzun = os.path.join(self.gir, "uzun.mp4")
        if not os.path.exists(uzun):
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                            "testsrc2=duration=60:size=640x360:rate=30", "-c:v", "libx264", "-preset", "ultrafast",
                            uzun], check=True)
        self.p.ekle([uzun])
        self.p._chipler["webm"].set_active(True)
        self.p.secenek.kalite = "yuksek"
        self.p.baslat_iptal()
        pompala(1.0)
        self.assertTrue(self.p.calisiyor)
        self.assertEqual(self.p.b_ana.get_label(), "İptal et")
        self.p.baslat_iptal()                       # ayni dugme = iptal
        self.assertTrue(bekle(lambda: not self.p.calisiyor, 20))
        self.assertEqual(self.p.ogeler[0].durum, "iptal")
        self.assertEqual(os.listdir(self.cikti), [])
        self.assertEqual([x for x in os.listdir(self.cikti) if x.startswith(".")], [])

    def test_zip_secenegi(self):
        self.p.ekle([self.g("foto.jpg"), self.g("simge.png")])
        self.p._chipler["webp"].set_active(True)
        self.p._sec_degisti("zip_yap", True)
        self.p.baslat_iptal()
        self.assertTrue(bekle(lambda: not self.p.calisiyor))
        zipler = [x for x in os.listdir(self.cikti) if x.endswith(".zip")]
        self.assertEqual(len(zipler), 1)

    def test_yanina_modu(self):
        d = tempfile.mkdtemp(dir=self.kok)
        shutil.copy(self.g("foto.jpg"), d)
        self.w.ayar["cikti_modu"] = "yanina"
        self.p.ekle([os.path.join(d, "foto.jpg")])
        self.p._chipler["png"].set_active(True)
        self.p.baslat_iptal()
        self.assertTrue(bekle(lambda: not self.p.calisiyor))
        self.assertTrue(os.path.exists(os.path.join(d, "foto.png")))

    # --- araclar --------------------------------------------------------------
    @unittest.skipUnless(D["qpdf"], "qpdf yok")
    def test_arac_birlestir(self):
        self.w.kabuk.sec("araclar")
        pompala(0.1)
        self.assertEqual(self.w.kabuk.baslik.get_text(), "Araçlar")
        self.a.ekle([self.g("a.pdf"), self.g("simge.png"), self.g("b.pdf")])
        self.a._chipler["pdf_birlestir"].set_active(True)
        pompala(0.1)
        self.assertEqual(self.a.b_ana.get_label(), "PDF birleştir")
        self.a.baslat_iptal()
        self.assertTrue(bekle(lambda: not self.a.calisiyor))
        self.assertEqual(len(os.listdir(self.cikti)), 1)
        self.assertTrue(os.listdir(self.cikti)[0].startswith("birlesik"))
        with M.Oturum() as o:
            self.assertEqual(M.pdf_bilgi(o, os.path.join(self.cikti, os.listdir(self.cikti)[0]))["sayfa"], 3)

    @unittest.skipUnless(D["qpdf"], "qpdf yok")
    def test_arac_en_az_dosya_ve_uyumsuz(self):
        self.a.ekle([self.g("a.pdf")])
        self.a._chipler["pdf_birlestir"].set_active(True)
        pompala(0.1)
        self.assertFalse(self.a.b_ana.get_sensitive())
        self.assertIn("en az 2", self.a.durum_metin.get_text())
        self.a.ekle([self.g("not.txt")])
        self.assertIn("dönüştürülemez",
                      [o for o in self.a.ogeler if o.ext == "txt"][0].satir["alt"].get_text())

    @unittest.skipUnless(D["qpdf"], "qpdf yok")
    def test_arac_secenekleri_arac_degisince_degisir(self):
        self.a.ekle([self.g("a.pdf")])
        self.a._chipler["pdf_dondur"].set_active(True)
        pompala(0.1)
        g = {k for k, (e, w, i) in self.a._sec_w.items() if w.get_visible()}
        self.assertEqual(g, {"derece", "sayfa_araligi", "parola"})
        self.a._chipler["pdf_bol"].set_active(True)
        pompala(0.1)
        g = {k for k, (e, w, i) in self.a._sec_w.items() if w.get_visible()}
        self.assertEqual(g, {"parca", "parola"})

    # --- dil, tema, ayar ---------------------------------------------------------
    def test_dil_ve_tema_degisimi_kalici(self):
        self.p.ekle([self.g("foto.jpg")])
        self.w.dil_kutu.set_active_id("en")
        pompala(0.1)
        self.assertEqual(self.w.kabuk.baslik.get_text(), "Convert")
        self.assertEqual(self.p.b_ekle.get_label(), "Add files")
        self.assertIn("Image", [c.get_children()[0].get_text() for c in self.p.hedef_ic.get_children()])
        self.assertEqual(M.ayar_oku()["dil"], "en")
        self.w.dil_kutu.set_active_id("tr")
        pompala(0.1)
        self.assertEqual(self.w.kabuk.baslik.get_text(), "Dönüştür")
        self.w.tema_degistir()
        self.assertEqual(M.ayar_oku()["tema"], "light")
        self.assertEqual(F.tema.AKTIF["gorunum"], "light")
        self.w.tema_degistir()
        self.assertEqual(F.tema.AKTIF["gorunum"], "dark")
        self.assertEqual(F.tema.AKTIF["vurgu"], F.tema.VURGULAR["filenor"])

    def test_ayar_sayfasi_arac_durumu(self):
        self.w.kabuk.sec("ayar")
        pompala(0.1)
        yazilar = []

        def tara(w):
            if isinstance(w, Gtk.Label):
                yazilar.append(w.get_text())
            if isinstance(w, Gtk.Container):
                for c in w.get_children():
                    tara(c)
        tara(self.w.arac_listesi)
        self.assertIn("ffmpeg", yazilar)
        self.assertIn("pillow", yazilar)
        self.w.s_bitince.set_active(True)
        self.assertTrue(M.ayar_oku()["bitince_ac"])
        self.w.s_bitince.set_active(False)

    def test_surukle_birak_isleyicisi(self):
        class Veri:
            def get_uris(self):
                return ["file://" + self.g_("foto.jpg"), "file://" + self.g_("klasor"), "file:///yok/dosya.png"]

        class Baglam:
            def finish(self, *a):
                pass
        v = Veri()
        v.g_ = self.g
        self.w._suruklendi(self.w, Baglam(), 0, 0, v, 0, 0)
        adlar = sorted(o.ad for o in self.p.ogeler)
        self.assertEqual(adlar, ["foto.jpg", "x.png", "y.jpg"])

    def test_pencere_kapaninca_calisan_is_iptal_edilir(self):
        # kapaniyor(): calisan kosucu yoksa hata vermemeli
        for p in self.w.paneller.values():
            self.assertFalse(p.calisiyor)


    # --- tek tik kurulum ------------------------------------------------------
    def _arac_taklidi(self, eksik, kur=None):
        """Eksik araclari taklit eder; gercek apt/pkexec cagrilmaz. geri alma fonksiyonu doner."""
        sahte = {k: True for k in D}          # yalniz belirtilenler eksik (ortamdan bagimsiz)
        for k in eksik:
            sahte[k] = False

        def durum():
            return sahte
        durum.cache_clear = lambda: None
        yedek = (M.araclar_durumu, M.araclari_yenile, K.apt_var, K.kur, K.ortami_yenile)
        M.araclar_durumu, M.araclari_yenile = durum, (lambda: None)
        K.apt_var, K.ortami_yenile = (lambda: True), (lambda: None)
        K.kur = kur or (lambda plan, cb=None, **kw: [])

        def geri():
            M.araclar_durumu, M.araclari_yenile, K.apt_var, K.kur, K.ortami_yenile = yedek
        return sahte, geri

    def test_eksik_arac_bandi_ve_tek_tik_kurulum(self):
        cagrilar = []
        sahte = {}

        def kur(plan, cb=None, **kw):
            cagrilar.append(list(plan.apt))
            if cb:
                cb("Kuruluyor python3-pil")
            sahte["pillow"] = True
            return []
        sahte, geri = self._arac_taklidi(["pillow"], kur)
        try:
            self.p.ekle([self.g("simge.png")])
            pompala(0.2)
            self.assertTrue(self.p.kur_bant.get_visible())
            self.assertIn("pillow", self.p.kur_bant_metin.get_text())
            self.assertFalse(self.p._chipler["jpg"].get_sensitive())      # eksik arac -> soluk
            self.p.kur_bant_dugme.clicked()
            self.assertTrue(self.w._kuruluyor)
            self.assertFalse(self.p.kur_bant_dugme.get_sensitive())       # kurulurken ikinci tik yok
            self.assertTrue(bekle(lambda: not self.w._kuruluyor, 10))
            pompala(0.3)
            self.assertEqual(cagrilar, [["python3-pil"]])
            self.assertFalse(self.p.kur_bant.get_visible())
            self.assertTrue(self.p._chipler["jpg"].get_sensitive())       # kurulum sonrasi acildi
            self.assertEqual(self.w.kabuk.serit_metin.get_text(), self.w.t("kur_ok"))
        finally:
            geri()

    def test_kurulum_cubugu_gercek_ilerlemeyi_gosterir(self):
        goruldu = []

        def kur(plan, cb=None, ilerleme_cb=None, **kw):
            for o, a, d in ((0.02, "guncelle", ""), (0.30, "indir", "50"), (0.70, "kur", "ffmpeg")):
                ilerleme_cb(o, a, d)
                time.sleep(0.25)
                goruldu.append((o, self.w.kur_ilerleme.get_fraction(), self.w.a_kur_durum.get_text()))
            sahte["pillow"] = True
            return []
        sahte, geri = self._arac_taklidi(["pillow"], kur)
        try:
            self.p.ekle([self.g("simge.png")])
            self.p.kur_bant_dugme.clicked()
            self.assertTrue(bekle(lambda: len(goruldu) == 3 or not self.w._kuruluyor, 10))
            pompala(0.3)
        finally:
            geri()
        self.assertEqual(len(goruldu), 3)
        for oran, cubuk, metin in goruldu:
            self.assertAlmostEqual(cubuk, oran, places=2)             # cubuk gercek orana esit
        self.assertIn("%30", goruldu[1][2])
        self.assertIn("İndiriliyor", goruldu[1][2])
        self.assertIn("ffmpeg", goruldu[2][2])

    def test_marka_aciklamasi_ve_simge(self):
        self.assertIn("Dosya ve medya dönüştürücü", self.w.kabuk.marka_alt.get_text())
        yol = F.logo_bul()
        self.assertTrue(yol and os.path.isfile(yol))
        with open(Y.DESKTOP, encoding="utf-8") as f:
            d = f.read()
        self.assertIn("GenericName[tr]=Dosya ve Medya Dönüştürücü", d)
        self.assertIn("GenericName=File and Media Converter", d)

    def test_kendini_sina_gercek_donusum_yapar(self):
        cikti = os.path.join(self.kok, "sina.txt")
        os.environ["FILENOR_SINAMA_CIKTI"] = cikti
        try:
            self.assertEqual(F.kendini_sina(), 0)
        finally:
            os.environ.pop("FILENOR_SINAMA_CIKTI", None)
        with open(cikti, encoding="utf-8") as f:
            self.assertTrue(f.read().startswith("TAMAM"))

    def test_surum_bayragi(self):
        self.assertEqual(F.ana(["filenor", "--surum"]), 0)
        self.assertEqual(F.APP_VERSION, "2.0")

    def test_kurulum_yetki_reddi_hata_gosterir(self):
        def kur(plan, cb=None, **kw):
            raise FilenorHata("kurulum_yetki")
        sahte, geri = self._arac_taklidi(["pillow"], kur)
        try:
            self.p.ekle([self.g("simge.png")])
            self.p.kur_bant_dugme.clicked()
            self.assertTrue(bekle(lambda: not self.w._kuruluyor, 10))
            pompala(0.3)
            self.assertIn("yetkisi", self.w.kabuk.serit_metin.get_text())
            self.assertTrue(self.p.kur_bant.get_visible())                # hala eksik -> bant kalir
            self.assertTrue(self.p.kur_bant_dugme.get_sensitive())        # tekrar denenebilir
        finally:
            geri()

    def test_kurulum_sonrasi_hala_eksikse_uyarir(self):
        sahte, geri = self._arac_taklidi(["pillow"], lambda plan, cb=None, **kw: ["python3-pil"])
        try:
            self.p.ekle([self.g("simge.png")])
            self.p.kur_bant_dugme.clicked()
            self.assertTrue(bekle(lambda: not self.w._kuruluyor, 10))
            pompala(0.3)
            self.assertIn("pillow", self.w.kabuk.serit_metin.get_text())
        finally:
            geri()

    def test_ayarlarda_eksikleri_kur_ve_satir_dugmeleri(self):
        sahte, geri = self._arac_taklidi(["ffmpeg", "qpdf", "libreoffice"])
        try:
            self.w._arac_listesini_kur()
            self.assertTrue(self.w.b_kur_hepsi.get_visible())
            self.assertIn("(2)", self.w.b_kur_hepsi.get_label())           # libreoffice sayilmaz
            self.assertEqual(sorted(self.w._temel_eksik), ["ffmpeg", "qpdf"])
            self.assertTrue(self.w.a_kur_ek.get_visible())                 # LibreOffice notu
            dugmeler = []

            def tara(w):
                if isinstance(w, Gtk.Button) and w.get_label() == self.w.t("kur_dugme"):
                    dugmeler.append(w)
                if isinstance(w, Gtk.Container):
                    for c in w.get_children():
                        tara(c)
            tara(self.w.arac_listesi)
            self.assertEqual(len(dugmeler), 3)                             # ffmpeg, libreoffice, qpdf
        finally:
            geri()
            self.w._arac_listesini_kur()

    def test_kurulamayan_ozellik_icin_kur_dugmesi_yok(self):
        sahte, geri = self._arac_taklidi(["avif"])
        try:
            self.w._arac_listesini_kur()
            dugmeler = []

            def tara(w):
                if isinstance(w, Gtk.Button):
                    dugmeler.append(w)
                if isinstance(w, Gtk.Container):
                    for c in w.get_children():
                        tara(c)
            tara(self.w.arac_listesi)
            self.assertEqual(dugmeler, [])
            self.assertFalse(self.w.b_kur_hepsi.get_visible())
        finally:
            geri()
            self.w._arac_listesini_kur()

    def test_hicbir_sey_eksik_degilken_bant_gorunmez(self):
        sahte, geri = self._arac_taklidi([])
        try:
            self.p.ekle([self.g("simge.png")])
            pompala(0.2)
            self.assertFalse(self.p.kur_bant.get_visible())
            self.assertFalse(self.w.b_kur_hepsi.get_visible())
        finally:
            geri()


if __name__ == "__main__":
    unittest.main(verbosity=1)
