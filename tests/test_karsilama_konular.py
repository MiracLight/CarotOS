#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Karşılama konu kartları (yeni sıra) ve güvenlik duvarı anahtarı.

* Konu sırası: sistem, yazilim, arac, koruma, guvenlik_duvari, ag, disk, etik, ogrenme
  (etik sondan bir önceki, ogrenme son). Her konunun sayfaları gerçek PAGES kimliği.
* Eski "gizlilik" bitti kaydı yeni yapıda hata vermeden elenir.
* carotos-ufw-ayar: argüman doğrulaması, sahte ufw ile ac/kapat/durum, ufw yoksa hata kodu,
  ufw'nin sabit ortam / stdin kapalı / kabuksuz çağrılması.
* Karşılama: ufw durumunun /etc/ufw/ufw.conf'tan okunması; GUI anahtarı (ekran varsa).

Calistirma:  xvfb-run -a python3 tests/test_karsilama_konular.py
"""
import ast
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)

KOK = os.path.dirname(BURASI)
INC = os.path.join(KOK, "config", "includes.chroot")
WELCOME = os.path.join(INC, "opt", "carotos", "welcome")
WELCOME_PY = os.path.join(WELCOME, "carotos-welcome.py")
BETIK = os.path.join(INC, "usr", "local", "sbin", "carotos-ufw-ayar")
sys.path.insert(0, WELCOME)

import gezinme as G  # noqa: E402
from test_karsilama_gezinme import pages_kimlikleri  # noqa: E402

BEKLENEN_SIRA = ["sistem", "yazilim", "arac", "koruma", "guvenlik_duvari", "ag", "disk", "etik", "ogrenme"]


def oku(yol):
    with open(yol, "rb") as f:
        return f.read().replace(b"\r\n", b"\n").decode("utf-8")


def welcome_agaci():
    return ast.parse(oku(WELCOME_PY))


def welcome_islevi(ad):
    """carotos-welcome.py'deki modul duzeyi bir islevi GTK yuklemeden alir."""
    agac = welcome_agaci()
    dugum = next(n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == ad)
    ad_alani = {}
    exec(compile(ast.Module(body=[dugum], type_ignores=[]), WELCOME_PY, "exec"), ad_alani)
    return ad_alani[ad]


def welcome_sayfasi(kimlik):
    """PAGES icindeki bir sayfa sozlugu (literal oldugu surece) GTK yuklemeden."""
    for n in welcome_agaci().body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "PAGES":
            for e in n.value.elts:
                d = dict(zip([k.value for k in e.keys], e.values))
                if d["id"].value == kimlik:
                    return ast.literal_eval(e)
    raise AssertionError(kimlik)


def betigi_yukle():
    yukleyici = importlib.machinery.SourceFileLoader("carotos_ufw_ayar", BETIK)
    spec = importlib.util.spec_from_loader("carotos_ufw_ayar", yukleyici)
    modul = importlib.util.module_from_spec(spec)
    yukleyici.exec_module(modul)
    return modul


class KonuSirasiTesti(unittest.TestCase):
    def test_sira(self):
        self.assertEqual([k["id"] for k in G.KONULAR], BEKLENEN_SIRA)

    def test_etik_sondan_bir_onceki_ogrenme_son(self):
        kimlikler = [k["id"] for k in G.KONULAR]
        self.assertEqual(kimlikler[-2], "etik")
        self.assertEqual(kimlikler[-1], "ogrenme")

    def test_bagimsiz_konular_tek_sayfa(self):
        konular = {k["id"]: k["sayfalar"] for k in G.KONULAR}
        self.assertEqual(konular["guvenlik_duvari"], ["guvenlik_duvari"])
        self.assertEqual(konular["ag"], ["network"])
        self.assertEqual(konular["disk"], ["disk"])
        self.assertEqual(konular["etik"], ["etik"])
        self.assertNotIn("guvenlik_duvari", konular["koruma"])
        self.assertEqual(konular["koruma"], ["usb", "carotpot", "carotene", "health", "dogrula"])

    def test_her_konu_sayfasi_gercek_sayfa(self):
        gercek = set(pages_kimlikleri())
        for k in G.KONULAR:
            for s in k["sayfalar"]:
                self.assertIn(s, gercek, (k["id"], s))

    def test_basliklar_iki_dilde(self):
        for k in G.KONULAR:
            for alan in ("baslik", "aciklama"):
                self.assertEqual(set(k[alan]), {"tr", "en"}, k["id"])
                self.assertTrue(k[alan]["tr"].strip() and k[alan]["en"].strip(), k["id"])

    def test_eski_gizlilik_kaydi_sessizce_elenir(self):
        g = G.Gezinme(bitenler=["gizlilik", "etik", 5, None])
        self.assertEqual(g.biten_konular(), ["etik"])
        self.assertFalse(g.konuyu_ac("gizlilik"))

    def test_mac_anahtari_ag_konusunda_gizlilik_anlatimi_orada(self):
        ag = welcome_sayfasi("network")
        turler = [t for t, _ in ag["body"]]
        self.assertIn("mac_anahtar", turler)
        self.assertIn("bullets", turler)                       # gizlilik varsayilanlari
        self.assertNotIn("mac_anahtar", [t for t, _ in welcome_sayfasi("disk")["body"]])


class UfwSayfasiTesti(unittest.TestCase):
    def setUp(self):
        self.s = welcome_sayfasi("guvenlik_duvari")

    def test_anahtar_ve_anlatim(self):
        turler = [t for t, _ in self.s["body"]]
        self.assertEqual(turler.count("ufw_anahtar"), 1)
        self.assertIn(("code", "sudo ufw enable"), self.s["body"])
        self.assertGreaterEqual(turler.count("p"), 2)          # ufw nedir + neden kapali gelir

    def test_anahtar_metinleri_iki_dilde(self):
        blok = next(g for t, g in self.s["body"] if t == "ufw_anahtar")
        self.assertEqual(set(blok), {"baslik", "alt", "acik", "kapali", "bilinmiyor", "hata"})
        for ad, m in blok.items():
            self.assertEqual(set(m), {"tr", "en"}, ad)
            self.assertTrue(m["tr"].strip() and m["en"].strip(), ad)
        self.assertIn("Poligon", blok["alt"]["tr"])
        self.assertIn("CarotPot", blok["alt"]["en"])

    def test_yardimci_yolu(self):
        k = oku(WELCOME_PY)
        self.assertIn('UFW_AYAR = "/usr/local/sbin/carotos-ufw-ayar"', k)
        self.assertIn('UFW_CONF = "/etc/ufw/ufw.conf"', k)
        self.assertIn('return ["pkexec", self.UFW_AYAR, "ac" if acik else "kapat"]', k)


class UfwDurumOkumaTesti(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="ufw-durum-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.yol = os.path.join(self.d, "ufw.conf")
        self.welcome = welcome_islevi("ufw_durumu")
        self.betik = betigi_yukle()

    def yaz(self, metin):
        with open(self.yol, "w", encoding="utf-8") as f:
            f.write(metin)

    def test_durumlar(self):
        self.assertIsNone(self.welcome(self.yol))                 # dosya yok
        for metin, beklenen in (("ENABLED=yes\n", True), ("ENABLED=no\n", False),
                                ("# ENABLED=yes\nENABLED='no'\n", False),
                                ("ENABLED=no\nENABLED=\"YES\"\n", True),
                                ("ENABLED=belki\n", None), ("LOGLEVEL=low\n", None)):
            self.yaz(metin)
            self.assertIs(self.welcome(self.yol), beklenen, metin)

    def test_betik_durumu_ayni_kurali_kullanir(self):
        etc = os.path.join(self.d, "etc", "ufw")
        self.assertEqual(self.betik.durum(self.d), "bilinmiyor")
        os.makedirs(etc)
        for metin, beklenen in (("ENABLED=yes\n", "ac"), ("ENABLED=no\n", "kapali"), ("X=1\n", "bilinmiyor")):
            with open(os.path.join(etc, "ufw.conf"), "w") as f:
                f.write(metin)
            self.assertEqual(self.betik.durum(self.d), beklenen)


class UfwYardimciTesti(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="ufw-kok-")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.m = betigi_yukle()
        os.makedirs(os.path.join(self.kok, "etc", "ufw"))
        self.conf = os.path.join(self.kok, "etc", "ufw", "ufw.conf")
        with open(self.conf, "w") as f:
            f.write("ENABLED=no\nLOGLEVEL=low\n")
        self.gunluk = os.path.join(self.kok, "cagri.log")
        self.ufw = os.path.join(self.kok, "sahte-ufw")
        with open(self.ufw, "w") as f:
            f.write("#!%s -I\n" % sys.executable + (
                "import os, sys\n"
                "a = sys.argv[1:]\n"
                "with open(%r, 'a') as g:\n"
                "    g.write(' '.join(a) + '|' + os.environ.get('PATH', '') + '|' + os.environ.get('LC_ALL', '')"
                " + '|' + str(len(os.environ)) + '|' + repr(sys.stdin.read()) + '\\n')\n"
                "if a == ['--force', 'enable']: v = 'yes'\n"
                "elif a == ['disable']: v = 'no'\n"
                "else: sys.exit(1)\n"
                "open(%r, 'w').write('ENABLED=' + v + '\\n')\n") % (self.gunluk, self.conf))
        os.chmod(self.ufw, 0o755)
        for bag in (contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())):
            bag.__enter__()
            self.addCleanup(bag.__exit__, None, None, None)

    def cagrilar(self):
        if not os.path.exists(self.gunluk):
            return []
        with open(self.gunluk) as f:
            return [s.split("|") for s in f.read().splitlines()]

    def test_gecersiz_argumanlar_reddedilir(self):
        for arg in ([], ["x"], ["x", "sil"], ["x", "ac", "fazla"], ["x", "AC"], ["x", "allow"],
                    ["x", "--force"], ["x", "ac;reboot"], ["x", "../etc/passwd"]):
            self.assertEqual(self.m.main(arg, self.kok, self.ufw), 2, arg)
        self.assertEqual(self.cagrilar(), [])

    def test_ac_kapat_durum(self):
        self.assertEqual(self.m.main(["x", "durum"], self.kok, self.ufw), 0)
        self.assertEqual(self.cagrilar(), [])                     # durum ufw calistirmaz
        self.assertEqual(self.m.main(["x", "ac"], self.kok, self.ufw), 0)
        self.assertEqual(self.m.durum(self.kok), "ac")
        self.assertEqual(self.m.main(["x", "kapat"], self.kok, self.ufw), 0)
        self.assertEqual(self.m.durum(self.kok), "kapali")
        c = self.cagrilar()
        self.assertEqual([x[0] for x in c], ["--force enable", "disable"])   # varsayilan politika degismez
        for argv, path, lc_all, ortam_sayisi, stdin in c:
            self.assertEqual(path, "/usr/sbin:/usr/bin:/sbin:/bin")
            self.assertEqual(lc_all, "C")
            self.assertEqual(stdin, "''")                         # stdin kapali (DEVNULL)
            self.assertLessEqual(int(ortam_sayisi), 3)            # yalniz sabit ortam (+ olasi LC_CTYPE)

    def test_ufw_yoksa_anlasilir_hata(self):
        yok = os.path.join(self.kok, "yok", "ufw")
        self.assertEqual(self.m.main(["x", "ac"], self.kok, yok), 4)
        self.assertEqual(self.m.main(["x", "kapat"], self.kok, yok), 4)
        self.assertEqual(self.m.main(["x", "durum"], self.kok, yok), 0)      # durum ufw'siz de okunur
        os.chmod(self.ufw, 0o644)                                 # calistirilamaz dosya da "kurulu degil"
        self.assertEqual(self.m.main(["x", "ac"], self.kok, self.ufw), 4)

    def test_ufw_basarisizsa_kod_5(self):
        with open(self.ufw, "w") as f:
            f.write("#!%s -I\nimport sys\nsys.exit(1)\n" % sys.executable)
        self.assertEqual(self.m.main(["x", "ac"], self.kok, self.ufw), 5)
        self.assertEqual(self.m.durum(self.kok), "kapali")

    def test_cagri_bicimi(self):
        goruldu = []

        def sahte_run(komut, **kw):
            goruldu.append((komut, kw))
            return subprocess.CompletedProcess(komut, 0)
        eski = self.m.subprocess.run
        self.m.subprocess.run = sahte_run
        self.addCleanup(setattr, self.m.subprocess, "run", eski)
        self.assertEqual(self.m.ufw_calistir("ac"), 0)
        self.assertEqual(self.m.ufw_calistir("kapat"), 0)
        self.assertEqual([k for k, _ in goruldu], [["/usr/sbin/ufw", "--force", "enable"], ["/usr/sbin/ufw", "disable"]])
        for _, kw in goruldu:
            self.assertIs(kw["stdin"], subprocess.DEVNULL)
            self.assertEqual(kw["env"], {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"})
            self.assertFalse(kw.get("shell", False))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root olarak gercek ufw calistirilmasin")
    def test_root_degilse_kok_vermeden_calismaz(self):
        self.assertEqual(self.m.main(["x", "ac"]), 3)
        self.assertEqual(self.m.main(["x", "kapat"]), 3)

    def test_betik_sertligi(self):
        k = oku(BETIK)
        self.assertTrue(k.startswith("#!/usr/bin/python3 -I\n"))
        self.assertIn("sys.dont_write_bytecode = True", k)
        self.assertIn('UFW = "/usr/sbin/ufw"', k)
        for yasak in ("shell=True", "os.system", "os.popen", "default", "allow", "sh -c"):
            self.assertNotIn(yasak, k, yasak)
        for satir in k.splitlines():                              # yalniz standart kutuphane
            if satir.startswith(("import ", "from ")):
                self.assertIn(satir.split()[1].split(".")[0], {"os", "subprocess", "sys"}, satir)


try:
    from test_dil_uygulamalar import EKRAN, UygulamaDilTabani  # noqa: E402
except Exception:                                                  # GTK yoksa arayuz testleri atlanir
    EKRAN, UygulamaDilTabani = False, unittest.TestCase


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class UfwAnahtariArayuzTesti(UygulamaDilTabani):
    def setUp(self):
        super().setUp()
        self.m = self.modul("welcome")
        self.gecici = tempfile.mkdtemp(prefix="ufw-gui-")
        self.addCleanup(shutil.rmtree, self.gecici, True)
        self.conf = os.path.join(self.gecici, "ufw.conf")
        self.komutlar = []
        self.sonuc = 0
        W = self.m.WelcomeWindow
        eski = (W.UFW_CONF, W.ufw_yetkili_calistir)
        W.UFW_CONF = self.conf
        test = self

        def sahte(s, komut):
            test.komutlar.append(komut)
            if test.sonuc == 0:
                with open(test.conf, "w") as f:
                    f.write("ENABLED=%s\n" % ("yes" if komut[-1] == "ac" else "no"))
            return test.sonuc
        W.ufw_yetkili_calistir = sahte
        self.addCleanup(lambda: (setattr(W, "UFW_CONF", eski[0]), setattr(W, "ufw_yetkili_calistir", eski[1])))

    def gez(self, sn):
        from gi.repository import Gtk
        bitis = time.time() + sn
        while time.time() < bitis:
            while Gtk.events_pending():
                Gtk.main_iteration()
            time.sleep(0.01)

    def pencere(self):
        p = self.m.WelcomeWindow(self.m.load_settings())
        self.addCleanup(p.destroy)
        p.show_all()
        self.gez(0.4)
        return p

    def durum_metni(self, p):
        kart = p.ufw_anahtari.get_parent()
        etiketler = []

        def topla(w):
            from gi.repository import Gtk
            if isinstance(w, Gtk.Label):
                etiketler.append(w.get_text())
            elif hasattr(w, "get_children"):
                for c in w.get_children():
                    topla(c)
        topla(kart)
        return etiketler

    def test_durum_bilinmiyor_ve_dosyadan_okuma(self):
        p = self.pencere()                                        # dosya yok
        self.assertFalse(p.ufw_anahtari.get_active())
        blok = next(g for t, g in welcome_sayfasi("guvenlik_duvari")["body"] if t == "ufw_anahtar")
        self.assertIn(blok["bilinmiyor"][p.lang], self.durum_metni(p))
        with open(self.conf, "w") as f:
            f.write("ENABLED=yes\n")
        p2 = self.pencere()
        self.assertTrue(p2.ufw_anahtari.get_active())
        self.assertIn(blok["acik"][p2.lang], self.durum_metni(p2))

    def test_ac_kapat_yetkili_betigi_cagirir(self):
        p = self.pencere()
        p.ufw_anahtari.set_active(True)
        self.gez(1.2)
        self.assertEqual(self.komutlar, [["pkexec", self.m.WelcomeWindow.UFW_AYAR, "ac"]])
        self.assertTrue(p.ufw_anahtari.get_state())
        self.assertTrue(p.ufw_anahtari.get_sensitive())
        p.ufw_anahtari.set_active(False)
        self.gez(1.2)
        self.assertEqual(self.komutlar[-1][-1], "kapat")
        self.assertFalse(p.ufw_anahtari.get_state())

    def test_basarisizsa_geri_doner_tekrar_calismaz(self):
        self.sonuc = 1
        p = self.pencere()
        p.ufw_anahtari.set_active(True)
        self.gez(1.5)
        self.assertEqual(len(self.komutlar), 1)
        self.assertFalse(p.ufw_anahtari.get_active())
        self.assertFalse(p.ufw_anahtari.get_state())
        self.assertTrue(p.ufw_anahtari.get_sensitive())

    def test_hub_kartlari_yeni_sirada(self):
        p = self.pencere()
        self.assertEqual(list(p.hub_kartlari), BEKLENEN_SIRA)


if __name__ == "__main__":
    unittest.main()
