#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon savunmaci gorunumu: olay gunlugu, servis kancalari ve analiz kurallari (GTK'siz).

Calistirma:  python3 tests/test_savunma_gorunumu.py
"""
import os
import socket
import sys
import time
import unittest
import urllib.error
import urllib.request

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLIGON = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "poligon")
sys.path.insert(0, POLIGON)

import olay_gunlugu as G  # noqa: E402
import savunma_analiz as A  # noqa: E402
from servisler.sahte_ag import SahteAgOrtami  # noqa: E402
from servisler.sahte_banner import SahteBannerOrtami  # noqa: E402
from servisler.sahte_giris import SahteGirisServisi  # noqa: E402
from servisler.sahte_savunma_hedefi import BasitDinleyici  # noqa: E402
from servisler.sahte_web import SahteWebServisi  # noqa: E402


def bos_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def bekle(kosul, sn=3.0):
    bitis = time.time() + sn
    while time.time() < bitis:
        if kosul():
            return True
        time.sleep(0.02)
    return False


class GunlukTesti(unittest.TestCase):
    def test_halka_tampon_ve_sirali_no(self):
        g = G.OlayGunlugu(kapasite=3)
        for i in range(5):
            g.kaydet("giris", "baglanti", port=i + 1)
        son = g.son()
        self.assertEqual([o["no"] for o in son], [3, 4, 5])
        self.assertEqual([o["no"] for o in g.son(sonra_no=4)], [5])
        g.temizle()
        self.assertEqual(g.son(), [])

    def test_bilinmeyen_tur_yazilmaz_ve_ayrinti_kisalir(self):
        g = G.OlayGunlugu()
        g.kaydet("giris", "parola_kaydi", "x")
        g.kaydet("web", "http_istek", "/a" * 200 + "\x00\n")
        olay = g.son()
        self.assertEqual(len(olay), 1)
        self.assertLessEqual(len(olay[0]["ayrinti"]), G.MAKS_AYRINTI)
        self.assertTrue(olay[0]["ayrinti"].isprintable())

    def test_diske_yazmaz_ve_parola_alani_yok(self):
        with open(os.path.join(POLIGON, "olay_gunlugu.py"), encoding="utf-8") as f:
            kaynak = f.read()
        for yasak in ("open(", "subprocess", "socket", "os.system", "parola", "password"):
            self.assertNotIn(yasak, kaynak.replace("Parola, govde", "").replace("parola, govde", ""), yasak)


class ServisKancaTesti(unittest.TestCase):
    def setUp(self):
        G.GUNLUK.temizle()

    def test_giris_servisi_basarisiz_ve_basarili_girisi_yazar_parolayi_degil(self):
        port = bos_port()
        sv = SahteGirisServisi("admin", "GizliParola123", port)
        sv.baslat()
        self.addCleanup(sv.durdur)

        def dene(kullanici, parola):
            with socket.create_connection(("127.0.0.1", port), timeout=3) as c:
                c.recv(100)
                c.sendall(("USER %s\r\n" % kullanici).encode())
                c.recv(100)
                c.sendall(("PASS %s\r\n" % parola).encode())
                return c.recv(100)
        self.assertIn(b"530", dene("admin", "yanlis-parola-xyz"))
        self.assertIn(b"230", dene("admin", "GizliParola123"))
        self.assertTrue(bekle(lambda: len(G.GUNLUK.son()) >= 4))
        olaylar = G.GUNLUK.son()
        self.assertEqual([o["tur"] for o in olaylar if o["tur"] != "baglanti"],
                         ["giris_basarisiz", "giris_basarili"])
        self.assertEqual(olaylar[-1]["ayrinti"], "admin")
        self.assertNotIn("yanlis-parola-xyz", repr(olaylar))
        self.assertNotIn("GizliParola123", repr(olaylar))

    def test_ag_ortami_baglantiyi_porta_gore_yazar(self):
        ag = SahteAgOrtami(gizli_port_araligi=(31000, 31900), gurultu_sayisi=2)
        ag.baslat()
        self.addCleanup(ag.durdur)
        self.assertTrue(ag.bekle_hazir())
        with socket.create_connection(("127.0.0.1", ag.gizli_port), timeout=3):
            pass
        self.assertTrue(bekle(lambda: any(o["port"] == ag.gizli_port for o in G.GUNLUK.son())))

    def test_banner_ve_savunma_hedefi_baglantiyi_yazar(self):
        port = bos_port()
        b = SahteBannerOrtami("127.0.0.1", [port], port, "1.0")
        b.baslat()
        self.addCleanup(b.durdur)
        with socket.create_connection(("127.0.0.1", port), timeout=3) as c:
            c.recv(100)
        self.assertTrue(bekle(lambda: any(o["servis"] == "banner" and o["port"] == port for o in G.GUNLUK.son())))
        p2 = bos_port()
        d = BasitDinleyici(p2)
        d.baslat()
        self.addCleanup(d.durdur)
        with socket.create_connection(("127.0.0.1", p2), timeout=3) as c:
            c.recv(100)
        self.assertTrue(bekle(lambda: any(o["servis"] == "savunma" for o in G.GUNLUK.son())))

    def test_web_servisi_yol_ve_404_yazar(self):
        port = bos_port()
        w = SahteWebServisi("gizli", port)
        w.baslat()
        self.addCleanup(w.durdur)
        urllib.request.urlopen("http://127.0.0.1:%d/urun?id=1" % port, timeout=3).read()
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/yok" % port, timeout=3)
        except urllib.error.HTTPError as h:
            h.close()
        self.assertTrue(bekle(lambda: len([o for o in G.GUNLUK.son() if o["servis"] == "web"]) >= 2))
        web = [(o["tur"], o["ayrinti"]) for o in G.GUNLUK.son() if o["servis"] == "web"]
        self.assertIn(("http_istek", "/urun"), web)            # sorgu dizesi (id=...) yazilmaz
        self.assertIn(("http_404", "/yok"), web)


def olay(zaman, servis, tur, port=0, ayrinti=""):
    return {"no": 0, "zaman": zaman, "servis": servis, "tur": tur, "ayrinti": ayrinti, "port": port}


class AnalizTesti(unittest.TestCase):
    def test_sakin_trafik_bulgu_uretmez(self):
        ol = [olay(100, "giris", "baglanti", 21), olay(101, "giris", "giris_basarisiz"),
              olay(102, "giris", "giris_basarili")]
        self.assertEqual(A.analiz_et(ol, 103), [])

    def test_parola_deneme_esigi_ve_pencere(self):
        ol = [olay(100 + i, "giris", "giris_basarisiz") for i in range(A.PAROLA_ESIK)]
        b = A.analiz_et(ol, 110)
        self.assertEqual([x["tur"] for x in b], ["parola_deneme"])
        self.assertEqual(b[0]["adet"], A.PAROLA_ESIK)
        self.assertEqual(b[0]["konu"], "fail2ban")
        self.assertEqual(A.analiz_et(ol[:-1], 110), [])                      # bir eksik: bulgu yok
        self.assertEqual(A.analiz_et(ol, 100 + A.PAROLA_PENCERE + 60), [])  # pencere disina cikti

    def test_port_taramasi_farkli_port_sayar(self):
        ayni = [olay(100 + i * 0.1, "ag", "baglanti", 80) for i in range(20)]
        self.assertEqual(A.analiz_et(ayni, 103), [])                         # ayni porta cok baglanti tarama degil
        farkli = [olay(100 + i * 0.1, "ag", "baglanti", 20000 + i) for i in range(A.PORT_ESIK)]
        b = A.analiz_et(farkli, 102)
        self.assertEqual([x["tur"] for x in b], ["port_tarama"])
        self.assertEqual(b[0]["konu"], "ufw")

    def test_web_taramasi_istek_ya_da_404_sayisi(self):
        ol = [olay(100 + i, "web", "http_404", 8000, "/x%d" % i) for i in range(A.WEB_404_ESIK)]
        self.assertEqual([x["tur"] for x in A.analiz_et(ol, 106)], ["web_tarama"])
        cok = [olay(100 + i * 0.2, "web", "http_istek", 8000) for i in range(A.WEB_ESIK)]
        self.assertEqual([x["tur"] for x in A.analiz_et(cok, 103)], ["web_tarama"])

    def test_servisler_birbirine_karismaz(self):
        ol = [olay(100 + i, "giris", "giris_basarisiz") for i in range(3)] + \
             [olay(100 + i, "banner", "giris_basarisiz") for i in range(3)]
        self.assertEqual(A.analiz_et(ol, 106), [])                           # 3+3: hicbiri esige varmadi

    def test_her_bulgunun_metni_iki_dilli(self):
        for ad, b in A.BULGULAR.items():
            for alan in ("baslik", "ne", "savunma"):
                self.assertTrue(b[alan]["tr"].strip() and b[alan]["en"].strip(), (ad, alan))
            self.assertIn(b["konu"], ("ufw", "fail2ban"))

    def test_savunma_durumu_cokmez(self):
        d = A.savunma_durumu()
        self.assertEqual(set(d), {"ufw", "fail2ban"})
        for v in d.values():
            self.assertIn(v, ("aktif", "pasif", "bilinmiyor"))

    def test_analiz_kaynakta_kabuk_yok(self):
        with open(os.path.join(POLIGON, "savunma_analiz.py"), encoding="utf-8") as f:
            k = f.read()
        self.assertNotIn("shell=True", k)
        self.assertNotIn("os.system", k)
        self.assertNotIn("sudo", k)
        self.assertNotIn("pkexec", k)


EKRAN = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class PencereTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.ev = tempfile.TemporaryDirectory()
        os.environ["HOME"] = cls.ev.name
        sys.path.insert(0, os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "ortak"))
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
        except (ImportError, ValueError) as exc:
            raise unittest.SkipTest("GTK yok: %s" % exc)
        cls.Gtk = Gtk
        import savunma_pencere
        cls.mod = savunma_pencere

    def pompala(self, sn=0.2):
        bitis = time.time() + sn
        while time.time() < bitis:
            while self.Gtk.events_pending():
                self.Gtk.main_iteration()
            time.sleep(0.01)

    def setUp(self):
        self.g = G.OlayGunlugu(saat=lambda: self.simdi)
        self.simdi = 1000.0
        self.durum = {"ufw": "aktif", "fail2ban": "pasif"}
        self.p = self.mod.pencere_olustur("tr", "dark", gunluk=self.g, durum_fn=lambda: dict(self.durum),
                                          saat=lambda: self.simdi)
        self.addCleanup(self.p.destroy)
        self.p.show_all()
        self.pompala(0.4)

    def test_bos_durumda_aciklayici_metin_ve_durum_rozetleri(self):
        self.assertEqual(len(self.p.model), 0)
        self.assertEqual([c.get_text() for c in self.p.bulgu_kutusu.get_children()], [self.mod.BOS_BULGU["tr"]])
        self.assertEqual(self.p.ufw_rozet.get_text(), "ufw: açık")
        self.assertEqual(self.p.f2b_rozet.get_text(), "fail2ban: kapalı")

    def test_olaylar_yeniden_eskiye_ve_parola_bulgusu(self):
        for i in range(A.PAROLA_ESIK):
            self.simdi += 1
            self.g.kaydet("giris", "giris_basarisiz", "admin", 2121)
        self.p.yenile()
        self.assertEqual(len(self.p.model), A.PAROLA_ESIK)
        self.assertEqual(self.p.model[0][2], "Başarısız giriş")
        self.assertIn("admin", self.p.model[0][3])
        kartlar = self.p.bulgu_kutusu.get_children()
        self.assertEqual(len(kartlar), 1)
        self.assertEqual(kartlar[0].get_name() or "kart", kartlar[0].get_name() or "kart")

    def test_satirlar_yalniz_yeni_olaylarla_artar_ve_sinirlidir(self):
        for _ in range(self.mod.EN_COK_SATIR + 30):
            self.g.kaydet("ag", "baglanti", "", 20001)
        self.p.yenile()
        self.assertLessEqual(len(self.p.model), self.mod.EN_COK_SATIR)
        onceki = len(self.p.model)
        self.p.yenile()
        self.assertEqual(len(self.p.model), onceki)           # yeni olay yok: satir eklenmez

    def test_dil_degisimi_ve_temizle(self):
        self.g.kaydet("web", "http_404", "/yok", 8000)
        self.p.yenile()
        self.p.dil_ayarla("en")
        self.assertEqual(self.p.baslik.get_text(), "Defender view")
        self.assertEqual(self.p.model[0][2], "Web request (not found)")
        self.assertEqual(self.p.ufw_rozet.get_text().split(":")[0], "ufw")
        self.p._temizle()
        self.assertEqual(len(self.p.model), 0)
        self.assertEqual(self.g.son(), [])

    def test_satir_metni_saf_islev(self):
        o = {"no": 1, "zaman": 0, "servis": "giris", "tur": "baglanti", "ayrinti": "", "port": 2121}
        zaman, servis, tur, ayr = self.mod.satir_metni(o, "en")
        self.assertEqual((servis, tur, ayr), ("Login service", "Connection", ":2121"))
        self.assertRegex(zaman, r"^\d\d:\d\d:\d\d$")


if __name__ == "__main__":
    unittest.main()
