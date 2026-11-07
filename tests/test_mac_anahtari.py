#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sahte MAC anahtari: yetkili betik (sahte kok dizinde), NetworkManager varsayilani ve Karşılama anahtari.

Sahte (sabit) MAC artik VARSAYILAN DEGIL: MAC filtreli aglarda baglanti kurdurmaz. Karşılama > Ag ve gizlilik'teki
anahtar `carotos-mac-ayar ac|kapat` ile 91-carotos-mac.conf dosyasini yazar/siler. Gercek root ve NetworkManager yok:
betik kok dizin parametresiyle gecici dizinde denenir; GUI testinde pkexec yerine sahte komut kullanilir.

Calistirma:  xvfb-run -a python3 tests/test_mac_anahtari.py
"""
import importlib.machinery
import importlib.util
import os
import stat
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_dil_uygulamalar import EKRAN, UygulamaDilTabani  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
BETIK = os.path.join(INC, "usr", "local", "sbin", "carotos-mac-ayar")
NM_90 = os.path.join(INC, "etc", "NetworkManager", "conf.d", "90-carotos-gizlilik.conf")


def betigi_yukle():
    yukleyici = importlib.machinery.SourceFileLoader("carotos_mac_ayar", BETIK)
    spec = importlib.util.spec_from_loader("carotos_mac_ayar", yukleyici)
    modul = importlib.util.module_from_spec(spec)
    yukleyici.exec_module(modul)
    return modul


def oku(yol):
    with open(yol, "rb") as f:
        return f.read().replace(b"\r\n", b"\n").decode("utf-8")


class AyarDosyalariTesti(unittest.TestCase):
    def test_varsayilan_parcada_sahte_mac_yok_digerleri_kaldi(self):
        kod = [s.strip() for s in oku(NM_90).splitlines() if s.strip() and not s.lstrip().startswith("#")]
        self.assertNotIn("wifi.cloned-mac-address=stable", kod)
        self.assertNotIn("ethernet.cloned-mac-address=stable", kod)
        for kalan in ("ipv4.dhcp-send-hostname=false", "ipv6.dhcp-send-hostname=false", "ipv6.ip6-privacy=2",
                      "wifi.scan-rand-mac-address=yes"):
            self.assertIn(kalan, kod)

    def test_anahtar_dosyasi_90dan_sonra_okunur(self):
        modul = betigi_yukle()
        self.assertGreater(modul.AD, "90-carotos-gizlilik.conf")          # sonraki dosya onceki degeri ezer
        self.assertIn("wifi.cloned-mac-address=stable", modul.ICERIK)
        self.assertIn("ethernet.cloned-mac-address=stable", modul.ICERIK)
        self.assertIn("[connection]", modul.ICERIK)

    def test_hook_betigi_calistirilabilir_yapar(self):
        hook = oku(os.path.join(KOK, "config", "hooks", "live", "9999-carotos-setup.hook.chroot"))
        self.assertIn("chmod 755 /usr/local/sbin/carotos-mac-ayar", hook)

    def test_betik_shebang_ve_kabuk_yok(self):
        k = oku(BETIK)
        self.assertTrue(k.startswith("#!/usr/bin/python3 -I"))
        self.assertNotIn("shell=True", k)
        self.assertNotIn("os.system", k)


class YetkiliBetikTesti(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="mac-kok-")
        import shutil
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.m = betigi_yukle()
        self.yol = self.m.yol(self.kok)
        # betigin print/usage ciktilari test sonuc satirlarini kirletmesin
        import contextlib
        import io
        for bag in (contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())):
            bag.__enter__()
            self.addCleanup(bag.__exit__, None, None, None)

    def test_ac_dosyayi_yazar_kapat_siler(self):
        self.assertEqual(self.m.main(["x", "durum"], self.kok), 0)
        self.assertEqual(self.m.durum(self.kok), "kapali")
        self.assertEqual(self.m.main(["x", "ac"], self.kok), 0)
        self.assertEqual(oku(self.yol), self.m.ICERIK)
        self.assertEqual(stat.S_IMODE(os.stat(self.yol).st_mode), 0o644)
        self.assertEqual(self.m.durum(self.kok), "ac")
        self.assertEqual(self.m.main(["x", "kapat"], self.kok), 0)
        self.assertFalse(os.path.exists(self.yol))
        self.assertEqual(self.m.main(["x", "kapat"], self.kok), 0)           # zaten yoksa hata vermez

    def test_ac_tekrar_cagrilinca_ayni_icerik(self):
        self.m.ac(self.kok)
        self.m.ac(self.kok)
        self.assertEqual(oku(self.yol), self.m.ICERIK)
        self.assertEqual(os.listdir(os.path.dirname(self.yol)), [self.m.AD])    # gecici dosya birakilmaz

    def test_gecersiz_argumanlar_reddedilir(self):
        for arg in ([], ["x"], ["x", "sil"], ["x", "ac", "fazla"], ["x", "AC"], ["x", "../etc/passwd"]):
            self.assertEqual(self.m.main(arg, self.kok), 2, arg)
        self.assertFalse(os.path.exists(self.yol))

    def test_sembolik_gecici_dosya_izlenmez(self):
        hedef = os.path.join(self.kok, "baska-dosya")
        with open(hedef, "w") as f:
            f.write("dokunulmamali")
        os.makedirs(os.path.dirname(self.yol))
        os.symlink(hedef, self.yol + ".yeni")
        with self.assertRaises(OSError):
            self.m.ac(self.kok)
        with open(hedef) as f:
            self.assertEqual(f.read(), "dokunulmamali")

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root olarak gercek dosya sistemine yazilmasin")
    def test_root_degilse_kok_vermeden_calismaz(self):
        self.assertEqual(self.m.main(["x", "ac"]), 3)
        self.assertEqual(self.m.main(["x", "kapat"]), 3)


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class KarsilamaAnahtariTesti(UygulamaDilTabani):
    def setUp(self):
        super().setUp()
        self.m = self.modul("welcome")
        self.gecici = tempfile.mkdtemp(prefix="mac-gui-")
        import shutil
        self.addCleanup(shutil.rmtree, self.gecici, True)
        self.dosya = os.path.join(self.gecici, "91-carotos-mac.conf")
        self.komutlar = []
        self.sonuc = 0
        W = self.m.WelcomeWindow
        self.eski = (W.MAC_DOSYASI, W.mac_yetkili_calistir)
        W.MAC_DOSYASI = self.dosya
        test = self

        def sahte(s, komut):
            test.komutlar.append(komut)
            if test.sonuc == 0:                                  # betigin yaptigini taklit et
                if komut[-1] == "ac":
                    open(test.dosya, "w").close()
                elif os.path.exists(test.dosya):
                    os.remove(test.dosya)
            return test.sonuc
        W.mac_yetkili_calistir = sahte
        self.addCleanup(lambda: (setattr(W, "MAC_DOSYASI", self.eski[0]), setattr(W, "mac_yetkili_calistir", self.eski[1])))

    def pencere(self):
        p = self.m.WelcomeWindow(self.m.load_settings())
        self.addCleanup(p.destroy)
        p.show_all()
        self.gez(0.4)
        return p

    def gez(self, sn):
        """Olay dongusunu sn saniye isletir (UygulamaDilTabani.pompala bekleme suresi almaz)."""
        from gi.repository import Gtk
        bitis = time.time() + sn
        while time.time() < bitis:
            while Gtk.events_pending():
                Gtk.main_iteration()
            time.sleep(0.01)

    def bekle(self, sn=1.2):
        self.gez(sn)

    def test_baslangic_durumu_dosyadan_gelir(self):
        p = self.pencere()
        self.assertFalse(p.mac_anahtari.get_active())
        open(self.dosya, "w").close()
        p2 = self.pencere()
        self.assertTrue(p2.mac_anahtari.get_active())

    def test_acinca_yetkili_betik_cagrilir_ve_durum_yazilir(self):
        p = self.pencere()
        p.mac_anahtari.set_active(True)
        self.bekle()
        self.assertEqual(self.komutlar, [["pkexec", self.m.WelcomeWindow.MAC_AYAR, "ac"]])
        self.assertTrue(p.mac_anahtari.get_active())
        self.assertTrue(p.mac_anahtari.get_state())
        self.assertTrue(p.mac_anahtari.get_sensitive())
        self.assertTrue(os.path.exists(self.dosya))
        p.mac_anahtari.set_active(False)
        self.bekle()
        self.assertEqual(self.komutlar[-1][-1], "kapat")
        self.assertFalse(os.path.exists(self.dosya))

    def test_basarisizsa_anahtar_geri_doner_ve_betik_tekrar_calismaz(self):
        self.sonuc = 1                                           # yetki verilmedi / hata
        p = self.pencere()
        p.mac_anahtari.set_active(True)
        self.bekle(1.5)
        self.assertEqual(len(self.komutlar), 1, "sonsuz dongu: basarisiz betik tekrar tekrar calistirildi")
        self.assertFalse(p.mac_anahtari.get_active())
        self.assertFalse(p.mac_anahtari.get_state())
        self.assertTrue(p.mac_anahtari.get_sensitive())
        self.assertFalse(os.path.exists(self.dosya))

    def test_metinler_dil_degisince_degisir(self):
        p = self.pencere()
        sayfa = [pg for pg in self.m.PAGES if pg["id"] == "network"][0]
        blok = [g for tur, g in sayfa["body"] if tur == "mac_anahtar"][0]
        for anahtar in ("baslik", "alt", "acik", "kapali", "hata"):
            self.assertTrue(blok[anahtar]["tr"].strip() and blok[anahtar]["en"].strip(), anahtar)


if __name__ == "__main__":
    unittest.main()
