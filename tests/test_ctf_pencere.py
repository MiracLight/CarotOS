#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon CTF ogrenci penceresi: GTK'siz mantik + (ekran varsa) gercek pencere, gercek sunucu.

Calistirma:  xvfb-run -a python3 tests/test_ctf_pencere.py
"""
import os
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
POLIGON = os.path.join(INC, "poligon")
sys.path.insert(0, POLIGON)
sys.path.insert(0, os.path.join(INC, "ortak"))

# Sahte HOME: gercek kullanici dosyalarina dokunma (GTK'dan once)
_EV = tempfile.mkdtemp(prefix="ctf-pencere-ev-")
os.environ["HOME"] = _EV
os.environ["USERPROFILE"] = _EV

import ctf_pencere as P  # noqa: E402

EKRAN = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


class MantikTesti(unittest.TestCase):
    def test_sure_metni(self):
        self.assertEqual(P.sure_metni(0), "00:00")
        self.assertEqual(P.sure_metni(65), "01:05")
        self.assertEqual(P.sure_metni(3661), "1:01:01")
        self.assertEqual(P.sure_metni(-5), "00:00")
        self.assertEqual(P.sure_metni(None), "00:00")

    def test_sonuc_metinleri_iki_dilde(self):
        ornekler = [{"sonuc": "dogru", "puan": 90, "bonus": 10}, {"sonuc": "yanlis"},
                    {"sonuc": "bekle", "bekleme_sn": 12}, {"sonuc": "zaten"}, {"sonuc": "baslamadi"},
                    {"sonuc": "bitti"}, {"hata": "baglanti"}, {"hata": "once_oncekini_ac"}, {"hata": "bilinmeyen"},
                    {"sonuc": "ne_idi_bu"}]
        for s in ornekler:
            for dil in ("tr", "en"):
                metin, renk = P.sonuc_metni(s, dil)
                self.assertTrue(metin.strip(), (s, dil))
                self.assertNotIn("{", metin, (s, dil))                  # doldurulmamis yer tutucu yok
                self.assertIn(renk, ("yesil", "kirmizi", "sari", "gri"))
        self.assertIn("90", P.sonuc_metni(ornekler[0], "tr")[0])
        self.assertIn("12", P.sonuc_metni(ornekler[2], "en")[0])

    def test_gruplama_siralamasi(self):
        g = [{"id": "b", "kategori": "log", "zorluk": "zor"}, {"id": "a", "kategori": "kodlama", "zorluk": "orta"},
             {"id": "c", "kategori": "kodlama", "zorluk": "kolay"}, {"id": "d", "kategori": "yeni", "zorluk": "kolay"}]
        sonuc = P.gorevleri_grupla(g)
        self.assertEqual([k for k, _ in sonuc], ["kodlama", "log", "yeni"])
        self.assertEqual([x["id"] for x in sonuc[0][1]], ["c", "a"])

    def test_kendi_satirim(self):
        skor = {"satirlar": [{"ad": "ali", "sira": 2}, {"ad": "veli", "sira": 1}]}
        self.assertEqual(P.kendi_satirim(skor, "ali")["sira"], 2)
        self.assertIsNone(P.kendi_satirim(skor, "yok"))
        self.assertIsNone(P.kendi_satirim({}, "ali"))

    def test_dosya_adi_yol_kacirmaz(self):
        for kotu in ("../../etc/passwd", "..\\..\\x.txt", "/etc/shadow", "a/b/c.txt", "", "...", ".bashrc", "ad;rm -rf.txt"):
            ad = P.guvenli_dosya_adi(kotu)
            self.assertNotIn("/", ad)
            self.assertNotIn("\\", ad)
            self.assertFalse(ad.startswith("."), ad)
            self.assertTrue(ad)
        taban = os.path.join(tempfile.gettempdir(), "tb")
        self.assertEqual(os.path.dirname(P.kayit_yolu("../../x.txt", taban)), taban)

    def test_kategori_ve_zorluk_adlari_tum_paketi_kapsar(self):
        import ctf_cekirdek as C
        for k in C.KATEGORILER:
            self.assertIn(k, P.KATEGORI_AD)
        for z in C.ZORLUKLAR:
            self.assertIn(z, P.ZORLUK_AD)


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class PencereTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        cls.Gtk = Gtk
        import ctf_istemci
        import ogrenci_istemci
        import ogretmen_sunucu
        cls.mod = (ctf_istemci, ogrenci_istemci, ogretmen_sunucu)

    def pompala(self, sn=1.5):
        bitis = time.time() + sn
        while time.time() < bitis:
            while self.Gtk.events_pending():
                self.Gtk.main_iteration()
            time.sleep(0.02)

    def setUp(self):
        ctf_istemci, ogrenci_istemci, S = self.mod
        self.oda = S.OdaDurumu("1234", "abc123")
        self.sunucu = S.sunucu_baslat(self.oda, "127.0.0.1", 0)
        self.addCleanup(self.sunucu.server_close)
        self.addCleanup(self.sunucu.shutdown)
        adres = "http://127.0.0.1:%d" % self.sunucu.server_address[1]
        self.pi = ogrenci_istemci.PoligonIstemci(adres, "1234", "abc123", "ali")
        self.assertTrue(self.pi.katil()[0])
        self.ctf = ctf_istemci.CtfIstemci(self.pi)
        self.kayit = tempfile.mkdtemp(prefix="ctf-kayit-")
        self.p = P.pencere_olustur(self.ctf, "tr", "ali", kayit_taban=self.kayit)
        self.addCleanup(self.p.destroy)
        self.p.show_all()
        self.pompala()

    def test_baslamadan_bos_ve_baslayinca_dolar(self):
        self.assertEqual(self.p.gorevler, [])
        self.oda.ctf_oturumu().baslat(30)
        self.pompala(4.5)
        self.assertGreaterEqual(len(self.p.gorevler), 12)
        self.assertEqual(self.p.durum_rozeti.get_text(), "Sürüyor")

    def test_dosya_goster_kaydet_gonder(self):
        import ctf_uretici as U
        self.oda.ctf_oturumu().baslat(30)
        self.pompala(4.5)
        self.p.liste.select_row(self.p._satirlar["kodlama-1"])
        self.pompala(1.5)
        tampon = self.p.dosya_gorunumu.get_buffer()
        icerik = tampon.get_text(tampon.get_start_iter(), tampon.get_end_iter(), False)
        self.assertIn("mesaj:", icerik)
        self.p._dosyayi_kaydet(None)
        yol = os.path.join(self.kayit, "kodlama-1-mesaj.txt")
        self.assertTrue(os.path.isfile(yol), self.p.kayit_etiketi.get_text())
        # yanlis, sonra dogru bayrak
        self.p.bayrak_girisi.set_text("CAROT{yanlis}")
        self.p._bayrak_gonder(None)
        self.pompala(1.5)
        self.assertIn("Yanlış", self.p.sonuc_etiketi.get_text())
        g = self.oda.ctf_oturumu().gorevler["kodlama-1"]
        bayrak = U.COZUCULAR[g["uretici"]](icerik, g["parametreler"])
        self.p.bayrak_girisi.set_text(bayrak)
        self.p._bayrak_gonder(None)
        self.pompala(1.5)
        self.assertIn("Doğru", self.p.sonuc_etiketi.get_text())
        self.pompala(4.5)
        self.assertTrue(next(g for g in self.p.gorevler if g["id"] == "kodlama-1")["cozuldu"])
        self.assertIn("Puanın", self.p.puan_etiketi.get_text())
        self.assertFalse(self.p.gonder_dugmesi.get_sensitive() and self.p.bayrak_girisi.get_sensitive())

    def test_skorda_kendi_satirim_kalin(self):
        self.p._skoru_yaz({"satirlar": [
            {"sira": 1, "ad": "veli", "puan": 300, "cozulen": 2},
            {"sira": 2, "ad": "ali", "puan": 200, "cozulen": 1}]})
        agirlik = {r[1]: r[4] for r in self.p.skor_modeli}
        self.assertEqual(agirlik, {"veli": 400, "ali": 700})

    def test_ipucu_acilir(self):
        self.oda.ctf_oturumu().baslat(30)
        self.pompala(4.5)
        self.p.liste.select_row(self.p._satirlar["kodlama-1"])
        self.pompala(1.5)
        self.p._onayla = lambda metin: True                      # onay penceresini atla
        self.p._ipucu_ac(None)
        self.pompala(1.5)
        self.assertEqual(len(self.p.ipucu_kutusu.get_children()), 1)
        self.pompala(4.5)
        self.assertEqual(next(g for g in self.p.gorevler if g["id"] == "kodlama-1")["ipucu_acilan"], 1)

    def test_poligon_vurgusu_korunur(self):
        # tema.uygula ekran geneli: CTF penceresi baska vurgu verirse Poligon ana penceresinin rengi de degisir
        import tema
        from gorunum_ayari import VURGU
        self.assertEqual(tema.AKTIF["vurgu"], tema.VURGULAR[VURGU])
        import savunma_pencere
        s = savunma_pencere.pencere_olustur("tr", "dark")
        self.addCleanup(s.destroy)
        self.assertEqual(tema.AKTIF["vurgu"], tema.VURGULAR[VURGU])

    def test_sonuc_etiketi_tema_renk_sinifini_alir(self):
        ctx = self.p.sonuc_etiketi.get_style_context()
        self.p._sonuc_geldi(None, {"sonuc": "yanlis"})
        self.assertTrue(ctx.has_class("hata-yazi"))
        self.p._sonuc_geldi(None, {"sonuc": "dogru", "puan": 100})
        self.assertTrue(ctx.has_class("basari-yazi"))
        self.assertFalse(ctx.has_class("hata-yazi"))
        self.p._sonuc_geldi(None, {"sonuc": "bekle", "bekleme_sn": 30})
        self.assertTrue(ctx.has_class("uyari-yazi"))
        self.assertFalse(ctx.has_class("basari-yazi"))

    def test_onay_ortak_temadan_ve_elle_renk_yok(self):
        import inspect
        import re
        kaynak = inspect.getsource(P)
        self.assertNotIn("MessageDialog", kaynak)
        self.assertIn("tema.onay_sor", kaynak)
        import tema
        # renkler paletten gelir; ctf_css kaynaginda elle yazilmis renk olmamali (acik temada leke olur)
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}", inspect.getsource(P.ctf_css)), [])
        with open(tema.__file__, encoding="utf-8") as f:
            tema_kaynak = f.read()
        for s in P.SONUC_SINIFI.values():                       # siniflar ortak temada tanimli olmali
            self.assertIn("." + s, tema_kaynak)

    def test_dil_degisimi_ve_baglanti_hatasi_cokertmez(self):
        self.p.dil = "en"
        self.p._metinleri_uygula()
        self.assertEqual(self.p.gonder_dugmesi.get_label(), "Submit")
        self.p.uygula_durum({"hata": "baglanti"}, {"hata": "baglanti"})
        self.assertIn("Cannot reach", self.p.not_etiketi.get_text())


class EntegrasyonTesti(unittest.TestCase):
    """Ogretmen ve ogrenci uygulamalarina CTF baglantisi (kaynak duzeyi; uygulamalari acmadan)."""

    @staticmethod
    def _oku(ad):
        with open(os.path.join(POLIGON, ad), encoding="utf-8") as f:
            return f.read()

    def test_ogretmen_uygulamasina_baglandi(self):
        k = self._oku("ogretmen_uygulama.py")
        self.assertIn("import ctf_ogretmen", k)
        self.assertIn('("ctf", [("ctf", "kalkan")])', k)
        self.assertIn('"ctf": self._ctf_sekmesi_olustur()', k)
        self.assertIn('"ctf": "ctf_baslik"', k)
        for anahtar in ("bolum_ctf", "menu_ctf", "ctf_baslik"):
            self.assertEqual(k.count('"%s":' % anahtar), 2, anahtar)       # tr ve en

    def test_ogrenci_uygulamasina_baglandi(self):
        k = self._oku("ogrenci_uygulama.py")
        self.assertEqual(k.count('"ctf_dugme":'), 2)
        self.assertIn("def _ctf_ac", k)
        self.assertIn("self._ctf_penceresini_kapat()", k)                     # oturum bitince pencere kapanir
        self.assertIn("not self.bireysel_mod and self.istemci is not None", k)  # yalniz sinif modunda

    def test_csv_yardimcilari(self):
        import ctf_ogretmen as O
        self.assertRegex(O.csv_dosya_adi(0), r"^poligon-ctf-\d{8}-\d{4}\.csv$")
        yol = os.path.join(tempfile.mkdtemp(prefix="ctf-csv-"), "s.csv")
        O.csv_kaydet(yol, "sira,ogrenci\n1,Şule\n")
        with open(yol, "rb") as f:
            ham = f.read()
        self.assertTrue(ham.startswith(b"\xef\xbb\xbf"))             # BOM: Excel Turkce karakteri dogru acar
        self.assertIn("Şule".encode("utf-8"), ham)


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class OgretmenPaneliTesti(unittest.TestCase):
    def setUp(self):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        import ctf_ogretmen
        import ogretmen_sunucu
        import tema
        self.Gtk, self.tema = Gtk, tema
        self.oda = ogretmen_sunucu.OdaDurumu("1234", "abc123")
        self.panel = ctf_ogretmen.panel_olustur(self.oda, "tr", None)
        self.pencere = Gtk.Window()
        self.pencere.add(self.panel.widget)
        self.pencere.show_all()
        self.addCleanup(self.pencere.destroy)

    def test_baslat_ve_bitir(self):
        p = self.panel
        self.assertEqual(p.durum_rozeti.get_text(), "Hazır")
        self.assertFalse(p.bitir_dugmesi.get_sensitive())
        self.assertFalse(p.csv_dugmesi.get_sensitive())
        p.sure_girisi.set_value(30)
        p._baslat(None)
        self.assertEqual(self.oda.ctf_oturumu().durum(), "surec")
        self.assertEqual(p.durum_rozeti.get_text(), "Sürüyor")
        self.assertFalse(p.baslat_dugmesi.get_sensitive())
        self.assertTrue(p.bitir_dugmesi.get_sensitive())
        self.assertIn("Kalan", p.sure_etiketi.get_text())
        self.tema.onay_sor = lambda *a, **k: True               # onay penceresini atla
        p._bitir(None)
        self.assertEqual(p.durum_rozeti.get_text(), "Bitti")
        self.assertTrue(p.baslat_dugmesi.get_sensitive())
        self.assertTrue(p.csv_dugmesi.get_sensitive())
        # bittikten sonra yeniden gorev secilip yeni yarisma kurulabilir (uygulamayi kapatmadan)
        self.assertTrue(p.izgara.get_visible())
        self.assertEqual(p.baslat_dugmesi.get_label(), "Yeni yarışma başlat")
        for cb in p.secili.values():
            self.assertTrue(cb.get_sensitive())
        for cb in p.secili.values():
            cb.set_active(False)
        p.secili["log-1"].set_active(True)
        p._baslat(None)
        self.assertEqual(self.oda.ctf_oturumu().durum(), "surec")
        self.assertEqual(self.oda.ctf_oturumu().acik_idler, ["log-1"])
        self.assertFalse(p.izgara.get_visible())                  # yarisma surerken gizli

    def test_secilen_gorevler_yarismaya_girer_ve_bos_secim_reddedilir(self):
        p = self.panel
        for cb in p.secili.values():
            cb.set_active(False)
        p._baslat(None)
        self.assertEqual(self.oda.ctf_oturumu().durum(), "hazir")
        self.assertTrue(p.not_etiketi.get_text())
        p.secili["kodlama-1"].set_active(True)
        p.secili["log-1"].set_active(True)
        p._baslat(None)
        self.assertEqual(sorted(self.oda.ctf_oturumu().acik_idler), ["kodlama-1", "log-1"])

    def test_skor_canli_gorunur_ve_dil_degisir(self):
        import ctf_uretici as U
        o = self.oda.ctf_oturumu()
        self.panel._baslat(None)
        o.dondurma = None
        g = o.gorevler["kodlama-1"]
        ad, icerik = o.dosya("ali", "kodlama-1")
        o.gonder("ali", "kodlama-1", U.COZUCULAR[g["uretici"]](icerik, g["parametreler"]))
        self.panel.yenile()
        self.assertEqual(len(self.panel.skor_modeli), 1)
        self.assertEqual(self.panel.skor_modeli[0][1], "ali")
        self.panel.dil_ayarla("en")
        self.assertEqual(self.panel.baslat_dugmesi.get_label(), "Start the contest")
        self.assertEqual(self.panel.durum_rozeti.get_text(), "Running")


if __name__ == "__main__":
    unittest.main()
