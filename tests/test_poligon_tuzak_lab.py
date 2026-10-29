#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon Tuzak Laboratuvari testleri (GTK'siz, ISO'ya girmez).

Gercek bir CarotPot sureci baslatir; yalniz 127.x uzerinde dinler.
Kullanim (depo kokunden):  python3 tests/test_poligon_tuzak_lab.py
"""
import json
import os
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot/opt/carotos")
for _y in (os.path.join(INC, "poligon"), os.path.join(INC, "carotpot"),
           os.path.join(INC, "ortak")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import carotpot as CP  # noqa: E402
import gecmis_defteri  # noqa: E402
import gorev_dogrulayici  # noqa: E402
import ogrenci_istemci  # noqa: E402
import tuzak_laboratuvari as TL  # noqa: E402

LINUX = sys.platform.startswith("linux")


def bekle(kosul, saniye=5.0):
    bitis = time.time() + saniye
    while time.time() < bitis:
        if kosul():
            return True
        time.sleep(0.05)
    return kosul()


def ftp_giris(adres, port, kullanici, parola="x"):
    with socket.create_connection((adres, port), timeout=3) as s:
        s.settimeout(3)
        s.recv(200)
        s.sendall(f"USER {kullanici}\r\n".encode())
        s.recv(200)
        s.sendall(f"PASS {parola}\r\n".encode())
        s.recv(200)
        s.sendall(b"QUIT\r\n")


class CarotPotDinleAyari(unittest.TestCase):
    def test_varsayilan_bos(self):
        self.assertEqual(CP.ayar_dogrula({"portlar": {"ftp": 2121}})["dinle"], "")

    def test_gecerli_adres(self):
        a = CP.ayar_dogrula({"portlar": {"ftp": 2121}, "dinle": "127.0.0.1"})
        self.assertEqual(a["dinle"], "127.0.0.1")

    def test_gecersiz_adres(self):
        for kotu in ("localhost", "999.1.1.1", "127.0.0.1; ls", 5, ["127.0.0.1"]):
            with self.assertRaises(ValueError, msg=str(kotu)):
                CP.ayar_dogrula({"portlar": {"ftp": 2121}, "dinle": kotu})

    def test_eski_ayar_dosyasi_dinlesiz_calisir(self):
        yol = Path(tempfile.mkdtemp()) / "a.json"
        yol.write_text(json.dumps({"portlar": {"ftp": 2121}}), encoding="utf-8")
        self.assertEqual(CP.ayar_oku(str(yol))["dinle"], "")


class LabKurallari(unittest.TestCase):
    def test_loopback_disi_adres_reddedilir(self):
        for adres in ("0.0.0.0", "192.168.1.5", "10.0.0.1", "", "::1", "abc"):
            with self.assertRaises(ValueError, msg=adres):
                TL.TuzakLab(bind_adres=adres)

    def test_gecersiz_hizmet_ve_aralik(self):
        with self.assertRaises(ValueError):
            TL.TuzakLab(hizmetler=("ssh",))
        with self.assertRaises(ValueError):
            TL.TuzakLab(hizmetler=())
        with self.assertRaises(ValueError):
            TL.TuzakLab(hizmetler=("ftp", "ftp"))
        with self.assertRaises(ValueError):
            TL.TuzakLab(port_araligi=(80, 90))
        with self.assertRaises(ValueError):
            TL.TuzakLab(hizmetler=("ftp", "telnet"), port_araligi=(21000, 21000))

    def test_gorev_dosyasi_gecerli(self):
        yol = Path(INC) / "poligon" / "gorevler" / "carotpot-01.json"
        self.assertEqual(gorev_dogrulayici.dogrula(yol), [])

    def test_gorev_dosyasi_kotu_hizmet_reddedilir(self):
        yol = Path(INC) / "poligon" / "gorevler" / "carotpot-01.json"
        veri = json.loads(yol.read_text(encoding="utf-8"))
        veri["zorluklar"]["kolay"]["hizmetler"] = ["ssh"]
        veri["zorluklar"]["orta"]["tuzak_port_araligi"] = [80, 90]
        gecici = Path(tempfile.mkdtemp()) / "carotpot-01.json"
        gecici.write_text(json.dumps(veri), encoding="utf-8")
        hatalar = gorev_dogrulayici.dogrula(gecici)
        self.assertTrue(any("hizmetler" in h for h in hatalar), hatalar)
        self.assertTrue(any("tuzak_port_araligi" in h for h in hatalar), hatalar)


class LabCalisiyor(unittest.TestCase):
    def test_baslat_kaydet_durdur(self):
        lab = TL.TuzakLab("127.0.0.1", ("ftp", "telnet", "http"), (21000, 21999))
        with lab:
            self.assertEqual(set(lab.portlar), {"ftp", "telnet", "http"})
            self.assertEqual(len(set(lab.portlar.values())), 3)
            self.assertTrue(all(21000 <= p <= 21999 for p in lab.portlar.values()))
            dizin = lab._dizin
            self.assertTrue(dizin.is_dir())
            ftp_giris("127.0.0.1", lab.portlar["ftp"], "ziyaretci-abcd", "parola1")
            self.assertTrue(bekle(lambda: lab.olaylar(kullanici="ziyaretci-abcd")))
            o = lab.olaylar(kullanici="ziyaretci-abcd")
            self.assertEqual(o[0]["hizmet"], "ftp")
            self.assertEqual(o[0]["parola"], "parola1")
            self.assertEqual(lab.olaylar(kullanici="baskasi"), [])
            if LINUX:
                # yalniz 127.0.0.1'e baglanmali: baska bir loopback adresi (127.0.0.2)
                # ve joker adres uzerinden ayni porta ULASILAMAMALI
                with self.assertRaises(OSError):
                    socket.create_connection(("127.0.0.2", lab.portlar["ftp"]), timeout=1)
            durum = json.loads((dizin / "durum.json").read_text(encoding="utf-8"))
            self.assertEqual(durum["dinle"], "127.0.0.1")
        self.assertFalse(dizin.exists(), "gecici dizin silinmeli")
        self.assertFalse(lab.calisiyor_mu())
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", list(lab.portlar.values())[0]), timeout=1)

    def test_sinif_adresi_127_x(self):
        if not LINUX:
            self.skipTest("127.x adresleri yalniz Linux'ta garanti")
        with TL.TuzakLab("127.45.0.1", ("ftp",), (21000, 21999)) as lab:
            ftp_giris("127.45.0.1", lab.portlar["ftp"], "ziyaretci-1234")
            self.assertTrue(bekle(lambda: lab.olaylar(kullanici="ziyaretci-1234")))
            with self.assertRaises(OSError):
                socket.create_connection(("127.0.0.1", lab.portlar["ftp"]), timeout=1)

    def test_sistem_carotpot_kayitlarina_dokunmaz(self):
        with TL.TuzakLab("127.0.0.1", ("ftp",), (21000, 21999)) as lab:
            self.assertNotEqual(str(lab.veritabani.parent), CP.VERI_DIZINI)
            self.assertTrue(str(lab.veritabani).startswith(tempfile.gettempdir()))


class IstemciAkisi(unittest.TestCase):
    def setUp(self):
        self._eski = gecmis_defteri.GECMIS_DOSYASI
        gecmis_defteri.GECMIS_DOSYASI = Path(tempfile.mkdtemp()) / "gecmis.json"

    def tearDown(self):
        gecmis_defteri.GECMIS_DOSYASI = self._eski

    def _istemci(self, zorluk):
        ist = ogrenci_istemci.PoligonIstemci("", "", "", "test")
        ist.zorluk = zorluk
        ist.gorevi_yukle("carotpot-01")
        ist.gorevi_baslat()
        return ist

    def test_kolay_gorev_kayitlardan_dogrulanir(self):
        ist = self._istemci("kolay")
        try:
            self.assertRegex(ist.tuzak_kullanici, r"^ziyaretci-[0-9a-f]{4}$")
            d = ist.metin_degiskenleri()
            self.assertEqual(d["{tuzaklar}"], "FTP")
            self.assertEqual(ist.aralik_metni(), "21000-21099")
            ok, mesaj = ist.tuzak_kaydini_dogrula("tr")
            self.assertFalse(ok)
            self.assertIn(ist.tuzak_kullanici, mesaj)
            # baska kullanici adi sayilmaz
            ftp_giris("127.0.0.1", ist._servis.portlar["ftp"], "baskasi")
            time.sleep(0.3)
            self.assertFalse(ist.tuzak_kaydini_dogrula("tr")[0])
            ftp_giris("127.0.0.1", ist._servis.portlar["ftp"], ist.tuzak_kullanici)
            self.assertTrue(bekle(lambda: ist.tuzak_kaydini_dogrula("en")[0]))
            kayitlar = gecmis_defteri.__dict__.get("GECMIS_DOSYASI").read_text(encoding="utf-8")
            self.assertIn("tamamlandi", kayitlar)
            self.assertIn('"puan": 60', kayitlar)
        finally:
            ist.gorevi_durdur()

    def test_orta_gorev_her_tuzak_icin_sayilir(self):
        ist = self._istemci("orta")
        try:
            lab = ist._servis
            self.assertEqual(ist.tuzak_gerekli, 2)
            for _ in range(2):
                ftp_giris("127.0.0.1", lab.portlar["ftp"], ist.tuzak_kullanici)
            time.sleep(0.3)
            ok, mesaj = ist.tuzak_kaydini_dogrula("tr")
            self.assertFalse(ok)          # telnet eksik
            self.assertIn("TELNET 0/2", mesaj)
            self.assertIn("FTP 2/2", mesaj)
        finally:
            ist.gorevi_durdur()
        self.assertFalse(lab.calisiyor_mu())

    def test_durmus_lab_dogrulanamaz(self):
        ist = self._istemci("kolay")
        ist.gorevi_durdur()
        self.assertFalse(ist.tuzak_kaydini_dogrula("tr")[0])

    def test_sinif_adresi_loopback_degilse_baslamaz(self):
        ist = ogrenci_istemci.PoligonIstemci("", "", "", "test")
        ist.gorevi_yukle("carotpot-01")
        ist.sinif_hedef_adres = "192.168.1.9"   # loopback degil -> gorevin kendi 127.0.0.1'i
        ist.gorevi_baslat()
        try:
            self.assertEqual(ist.gercek_bind_adres, "127.0.0.1")
            self.assertEqual(ist._servis.bind_adres, "127.0.0.1")
        finally:
            ist.gorevi_durdur()


class SinifModuPuani(unittest.TestCase):
    """Cevap kutusu olmayan gorevler de ogretmen skoruna puanla yansir."""

    def test_tuzak_gorevi_ogretmen_skoruna_puan_yazar(self):
        import ogretmen_sunucu as S
        oda = S.OdaDurumu("1111", "pw")
        srv = S.sunucu_baslat(oda, "127.0.0.1", 0)
        try:
            port = srv.server_address[1]
            ist = ogrenci_istemci.PoligonIstemci(f"http://127.0.0.1:{port}", "1111", "pw", "ali")
            self.assertTrue(ist.katil()[0])
            oda.gorev_ata("carotpot-01", "kolay")
            ist.acik_gorevleri_getir()
            ist.zorluk = ist.atanan_zorluk("carotpot-01")
            ist.gorevi_yukle("carotpot-01")
            ist.gorevi_baslat()
            try:
                self.assertEqual(oda.sinif_ozeti()[0]["puan"], 0)
                ftp_giris("127.0.0.1", ist._servis.portlar["ftp"], ist.tuzak_kullanici)
                self.assertTrue(bekle(lambda: ist.tuzak_kaydini_dogrula("tr")[0]))
            finally:
                ist.gorevi_durdur()
            ozet = oda.sinif_ozeti()[0]
            self.assertEqual(ozet["puan"], 60)
            self.assertEqual(ozet["cozulen"], 1)
            self.assertEqual(ozet["durum"], "tamamlandi")
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
