#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Magaza guvenlik denetimi duzeltmeleri (M-01..M-07; docs/denetim/carotene-magaza.md).

GTK gerektirmeyen testler kaynaktaki ilgili islevleri ayristirip calistirir; arayuz testleri
ekran yoksa atlanir. Hicbir test pkexec/apt-get'i gercekten calistirmaz.

Calistirma:  xvfb-run -a python3 tests/test_magaza_denetim.py
"""
import ast
import importlib.machinery
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPT = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
KOD = os.path.join(OPT, "magaza", "carotos-magaza.py")
KATALOG = os.path.join(OPT, "magaza", "katalog.json")
sys.path.insert(0, os.path.join(OPT, "ortak"))

import dil  # noqa: E402
import yetkili  # noqa: E402

with open(KOD, "rb") as _f:
    KAYNAK = _f.read().decode("utf-8")
AGAC = ast.parse(KAYNAK)

_ISLEVLER = {"paket_adi_gecerli", "apt_komutu", "kilit_iletisi", "_arac_etkisi",
             "kaldirma_simulasyonu_coz", "kaldirma_simulasyonu", "korunan_etkiler",
             "yardimci_komutu", "paket_argumani"}
_DEGISKENLER = {"PAKET_ADI", "APT_EYLEMLERI", "EK_PAKETLER", "_ARAC_ETKI", "KORUNAN", "YARDIMCI",
                "FAZ_ISARETI", "IPTAL_ISARETI", "IPTAL_KODU"}


def gtk_siz_yukle(sistem_yolu=None):
    """apt/kaldirma islevlerini gi olmadan calistirilabilir yapar."""
    secilen = []
    for n in AGAC.body:
        if isinstance(n, ast.FunctionDef) and n.name in _ISLEVLER:
            secilen.append(n)
        elif isinstance(n, ast.Assign) and any(getattr(t, "id", "") in _DEGISKENLER
                                               for t in n.targets):
            secilen.append(n)
        elif (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
              and ast.get_source_segment(KAYNAK, n).startswith("KORUNAN.update")):
            secilen.append(n)
    import subprocess
    ad_alani = {"re": re, "os": os, "subprocess": subprocess, "dil": dil,
                "sistem_yolu": sistem_yolu or yetkili.sistem_yolu,
                "temiz_ortam": yetkili.temiz_ortam}
    exec(compile(ast.Module(body=secilen, type_ignores=[]), KOD, "exec"), ad_alani)
    return ad_alani


def sahte_yol(ad):
    return "/usr/bin/" + ad


def katalog_adlari():
    with open(KATALOG, encoding="utf-8") as f:
        return {u["paket"] for u in json.load(f)["uygulamalar"]}


def yontem_govdesi(sinif_adi, yontem_adi):
    sinif = next(n for n in AGAC.body if isinstance(n, ast.ClassDef) and n.name == sinif_adi)
    yontem = next(n for n in sinif.body
                  if isinstance(n, ast.FunctionDef) and n.name == yontem_adi)
    return ast.get_source_segment(KAYNAK, yontem)


# --- M-04: root programlari yalnizca sistem dizinlerinden ----------------------------
class M04SistemYoluTesti(unittest.TestCase):
    def test_kaynakta_which_yok(self):
        self.assertNotIn("shutil.which", KAYNAK)
        self.assertIn("from yetkili import sistem_yolu", KAYNAK)

    def test_komuttaki_programlar_mutlak(self):
        a = gtk_siz_yukle(sahte_yol)
        for eylem, paketler in (("install", ["nmap"]), ("remove", ["nmap"]),
                                ("upgrade", []), ("update", [])):
            with self.subTest(eylem=eylem):
                k = a["apt_komutu"](eylem, *paketler)
                self.assertEqual(k[0], "/usr/bin/pkexec")
                self.assertEqual(k[1], "/usr/bin/env")
                self.assertIn("/usr/bin/apt-get", k)
                self.assertNotIn("env", k)
                self.assertNotIn("apt-get", k)

    def test_path_basindaki_sahte_programlar_kullanilmaz(self):
        a = gtk_siz_yukle()          # gercek sistem_yolu
        with tempfile.TemporaryDirectory() as d:
            for ad in ("pkexec", "env", "apt-get"):
                yol = os.path.join(d, ad)
                with open(yol, "w") as f:
                    f.write("#!/bin/sh\nexit 0\n")
                os.chmod(yol, 0o755)
            with mock.patch.dict(os.environ, {"PATH": d + os.pathsep + os.environ.get("PATH", "")}):
                k = a["apt_komutu"]("install", "nmap")
        if k is None:                # bu makinede pkexec yok: komut kurulmaz, sahte de kullanilmaz
            return
        for oge in k:
            self.assertFalse(oge.startswith(d), oge)
        self.assertTrue(k[0].startswith(yetkili.SISTEM_DIZINLERI))

    def test_program_eksikse_none(self):
        for eksik in ("pkexec", "env", "apt-get"):
            with self.subTest(eksik=eksik):
                a = gtk_siz_yukle(lambda ad, e=eksik: None if ad == e else sahte_yol(ad))
                self.assertIsNone(a["apt_komutu"]("install", "nmap"))

    def test_dpkg_query_ve_apt_list_temiz_ortamla(self):
        for islev in ("kurulu_paketler", "guncellenebilir_paketler"):
            govde = ast.get_source_segment(KAYNAK, next(
                n for n in AGAC.body if isinstance(n, ast.FunctionDef) and n.name == islev))
            with self.subTest(islev=islev):
                self.assertIn("sistem_yolu(", govde)
                self.assertIn("env=temiz_ortam()", govde)


# --- M-05: paket adi dogrulamasi ve '--' -----------------------------------------------
class M05PaketAdiTesti(unittest.TestCase):
    def setUp(self):
        self.a = gtk_siz_yukle(sahte_yol)

    def test_katalogdaki_butun_adlar_gecerli(self):
        for ad in katalog_adlari():
            with self.subTest(ad=ad):
                self.assertTrue(self.a["paket_adi_gecerli"](ad))

    def test_gecersiz_adlar_reddedilir(self):
        for ad in ("-oAPT::Update::Pre-Invoke::=x", "--allow-remove-essential", "./x.deb",
                   "/tmp/x.deb", "nmap=7.0", "nmap/trixie", "Nmap", "", "a", "nmap;id",
                   "nmap rkhunter", "nmap\n", None, 5):
            with self.subTest(ad=ad):
                with self.assertRaises(ValueError):
                    self.a["apt_komutu"]("install", ad)
                with self.assertRaises(ValueError):
                    self.a["apt_komutu"]("remove", ad)

    def test_katalog_uyeligi(self):
        izinli = frozenset({"nmap"})
        self.assertIsNotNone(self.a["apt_komutu"]("install", "nmap", izinli=izinli))
        with self.assertRaises(ValueError):
            self.a["apt_komutu"]("install", "netcat-traditional", izinli=izinli)

    def test_gecersiz_eylem_ve_fazla_arguman(self):
        for eylem in ("purge", "autoremove", "-o", "source", ""):
            with self.subTest(eylem=eylem):
                with self.assertRaises(ValueError):
                    self.a["apt_komutu"](eylem, "nmap")
        # upgrade/update'e verilen ad root komutuna hic girmez
        for eylem in ("upgrade", "update"):
            with self.subTest(eylem=eylem):
                k = self.a["apt_komutu"](eylem, "-oAPT::x=y", "nmap")
                self.assertNotIn("nmap", k)
                self.assertNotIn("-oAPT::x=y", k)
        with self.assertRaises(ValueError):
            self.a["apt_komutu"]("install")

    def test_adlar_cift_tire_ardinda(self):
        k = self.a["apt_komutu"]("remove", "nmap", "hydra")
        self.assertEqual(k[k.index("--"):], ["--", "nmap", "hydra"])
        self.assertLess(k.index("remove"), k.index("--"))

    def test_magaza_eylemleri_katalogla_sinirli(self):
        self.assertIn("izinli=self.katalog_adlari", yontem_govdesi("MagazaPenceresi", "eylem"))
        self.assertIn("in self.katalog_adlari", yontem_govdesi("MagazaPenceresi", "sepeti_kur"))


# --- M-06 ve conffile: kilit bekleme, anlasilir ileti, stdin yok -------------------------
class M06KilitTesti(unittest.TestCase):
    def setUp(self):
        self.a = gtk_siz_yukle(sahte_yol)

    def test_kilit_bekleme_secenegi(self):
        for eylem, p in (("install", ["nmap"]), ("remove", ["nmap"]), ("upgrade", []),
                         ("update", [])):
            with self.subTest(eylem=eylem):
                self.assertIn("DPkg::Lock::Timeout=60", self.a["apt_komutu"](eylem, *p))

    def test_conffile_sorusu_beklenmez(self):
        for eylem, p in (("install", ["nmap"]), ("remove", ["nmap"]), ("upgrade", [])):
            k = self.a["apt_komutu"](eylem, *p)
            with self.subTest(eylem=eylem):
                self.assertIn("Dpkg::Options::=--force-confold", k)
                self.assertIn("Dpkg::Options::=--force-confdef", k)
        # dogrudan apt yolunda stdin yok; yardimci yolunda apt'i yardimci stdin'siz calistirir
        self.assertIn("subprocess.PIPE if self.yardimci else subprocess.DEVNULL",
                      yontem_govdesi("IslemPenceresi", "_calis"))
        self.assertIn("stdin=subprocess.DEVNULL", YARDIMCI_KAYNAK)

    def test_kilit_iletisi_tanima(self):
        f = self.a["kilit_iletisi"]
        self.assertEqual(f("E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by "
                           "process 812 (apt-get)\nE: Unable to acquire the dpkg frontend lock "
                           "(/var/lib/dpkg/lock-frontend), is another process using it?"),
                         "kilit_mesgul")
        self.assertEqual(f("E: Unable to lock directory /var/lib/apt/lists/"), "kilit_mesgul")
        self.assertEqual(f("E: Could not get lock /var/lib/apt/lists/lock"), "kilit_mesgul")
        self.assertEqual(f("E: dpkg was interrupted, you must manually run 'dpkg --configure "
                           "-a' to correct the problem."), "dpkg_yarim")
        self.assertIsNone(f("E: Unable to locate package xyz"))
        self.assertIsNone(f("unlocked the clock block"))
        self.assertIsNone(f(""))


# --- M-03: kaldirma onayi ---------------------------------------------------------------
SIMULASYON = """NOTE: This is only a simulation!
      apt-get needs root privileges for real execution.
      Keep also in mind that locking is deactivated,
      so don't depend on the relevance to the real current situation!
Reading package lists...
Building dependency tree...
The following packages will be REMOVED:
  clamav clamav-freshclam
0 upgraded, 0 newly installed, 2 to remove and 0 not upgraded.
Remv clamav [1.4.3+dfsg-1]
Remv clamav-freshclam [1.4.3+dfsg-1]
Remv libfoo:i386 [1.0]
"""


class M03KaldirmaTesti(unittest.TestCase):
    def setUp(self):
        self.a = gtk_siz_yukle(sahte_yol)

    def test_simulasyon_ayristirma(self):
        s = self.a["kaldirma_simulasyonu_coz"](0, SIMULASYON)
        self.assertEqual(s, {"paketler": ["clamav", "clamav-freshclam", "libfoo"],
                             "temel": False})

    def test_temel_paket_ve_hata(self):
        s = self.a["kaldirma_simulasyonu_coz"](
            0, "WARNING: The following essential packages will be removed.\nRemv bash [5.2]\n")
        self.assertTrue(s["temel"])
        self.assertIsNone(self.a["kaldirma_simulasyonu_coz"](100, "E: Unable to locate package x"))
        self.assertEqual(self.a["kaldirma_simulasyonu_coz"](
            0, "Package 'nmap' is not installed, so not removed\n")["paketler"], [])

    def test_bozulan_uygulama_adiyla_soylenir(self):
        tr = self.a["korunan_etkiler"](["clamav", "htop"], "tr")
        self.assertEqual(len(tr), 1)
        self.assertIn("Carotene", tr[0])
        self.assertIn("CarotOS USB Denetimi", tr[0])
        en = self.a["korunan_etkiler"](["clamav"], "en")
        self.assertIn("CarotOS USB Check", en[0])
        self.assertIn("CarotOS Security Panel", self.a["korunan_etkiler"](["nmap"], "en")[0])
        self.assertIn("CarotOS Güvenlik Paneli", self.a["korunan_etkiler"](["nmap"], "tr")[0])

    def test_korunan_paketler_ve_metinler(self):
        korunan = self.a["KORUNAN"]
        for p in ("clamav", "rkhunter", "john", "nmap", "hydra", "sqlmap", "tcpdump",
                  "aircrack-ng", "firefox-esr", "tshark", "nikto"):
            with self.subTest(p=p):
                self.assertIn(p, korunan)
        for p, m in korunan.items():
            with self.subTest(p=p):
                self.assertEqual(set(m), {"tr", "en"})
                self.assertIn(p, m["tr"])
                self.assertIn(p, m["en"])
        # CarotOS uygulamalarinin kullanmadigi paketler korunan sayilmaz
        self.assertNotIn("git", korunan)
        self.assertNotIn("htop", korunan)

    def test_simulasyon_root_olmadan_ve_cift_tireyle(self):
        with tempfile.TemporaryDirectory() as d:
            kayit = os.path.join(d, "argv")
            sahte = os.path.join(d, "apt-get")
            with open(sahte, "w") as f:
                f.write('#!/bin/sh\nprintf "%%s\\n" "$@" > "%s"\ncat <<"SON"\n%sSON\n'
                        % (kayit, SIMULASYON))
            os.chmod(sahte, 0o755)
            a = gtk_siz_yukle(lambda ad: sahte if ad == "apt-get" else None)
            s = a["kaldirma_simulasyonu"]("clamav")
            with open(kayit) as f:
                argv = f.read().split()
        self.assertEqual(argv, ["-s", "remove", "--", "clamav"])
        self.assertEqual(s["paketler"], ["clamav", "clamav-freshclam", "libfoo"])
        self.assertIsNone(a["kaldirma_simulasyonu"]("-oX=y"))

    def test_kaldirma_onaysiz_baslamaz(self):
        govde = yontem_govdesi("MagazaPenceresi", "eylem")
        self.assertIn('if islem == "remove":', govde)
        self.assertIn("self._kaldirma_onayi(", govde)
        self.assertIn("_kaldirma_sor(", yontem_govdesi("MagazaPenceresi", "_kaldirma_onayi"))

    def test_yeni_metinler_iki_dilde(self):
        for n in AGAC.body:
            if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "METIN" for t in n.targets):
                metin = ast.literal_eval(n.value)
                break
        for anahtar in ("iptal_edilemez", "kilit_mesgul", "dpkg_yarim", "kaldir_onay_baslik",
                        "kaldir_liste", "kaldir_hesaplanamadi", "kaldir_korunan",
                        "kaldir_anladim", "kaldir_temel"):
            with self.subTest(anahtar=anahtar):
                self.assertEqual(set(metin[anahtar]), {"tr", "en"})


# --- M-02: sonuc her zaman dpkg'den -------------------------------------------------
class M02SonucTesti(unittest.TestCase):
    def test_tek_kurulum_sonucu_dpkgden(self):
        govde = yontem_govdesi("MagazaPenceresi", "_eylem_baslat")
        self.assertIn("self._kurulu_oku(", govde)

    def test_toplu_guncelleme_sonucu_kosulsuz(self):
        govde = yontem_govdesi("MagazaPenceresi", "tumunu_guncelle")
        self.assertNotIn("if basarili:", govde)


# --- Arayuz testleri -----------------------------------------------------------------
_EV = tempfile.mkdtemp(prefix="magaza-denetim-")
os.environ["HOME"] = _EV
os.environ["XDG_CONFIG_HOME"] = os.path.join(_EV, "c")
os.environ["XDG_CACHE_HOME"] = os.path.join(_EV, "k")
os.environ["XDG_DATA_HOME"] = os.path.join(_EV, "d")
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GLib
    GTK_VAR = Gtk.init_check()[0]
except (ImportError, ValueError):
    GTK_VAR = False

magaza = None
if GTK_VAR:
    _spec = importlib.util.spec_from_file_location("magaza_denetim_modulu", KOD)
    magaza = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(magaza)


def olaylari_isle(kosul, sure=30):
    bit = time.time() + sure
    while not kosul() and time.time() < bit:
        while Gtk.events_pending():
            Gtk.main_iteration()
        time.sleep(0.01)
    while Gtk.events_pending():
        Gtk.main_iteration()


def pencere_ac(komut):
    sonuc = []
    p = magaza.IslemPenceresi(Gtk.Window(), "deneme", komut, lambda b: sonuc.append(b))
    p.baslat()
    return p, sonuc


def tampon_metni(p):
    return p.tampon.get_text(p.tampon.get_start_iter(), p.tampon.get_end_iter(), False)


@unittest.skipUnless(GTK_VAR, "ekran/GTK yok")
class M01OkuyucuTesti(unittest.TestCase):
    def test_utf8_olmayan_bayt_okuyucuyu_oldurmez(self):
        # Eskiden: \377 okuyucuyu olduruyor, surec boru dolunca takiliyordu, sonuc False
        p, sonuc = pencere_ac(["sh", "-c", "printf 'a\\377b\\n'; i=0; while [ $i -lt 9000 ]; "
                                           "do echo satir$i; i=$((i+1)); done; exit 0"])
        olaylari_isle(lambda: sonuc, 60)
        self.assertEqual(sonuc, [True])
        self.assertIsNotNone(p.surec.poll())
        metin = tampon_metni(p)
        self.assertIn("a�b", metin)
        self.assertTrue(metin.rstrip().endswith("satir8999"))

    def test_satir_sonu_olmayan_dev_cikti(self):
        p, sonuc = pencere_ac(["sh", "-c", "head -c 300000 /dev/zero | tr '\\0' x; exit 4"])
        olaylari_isle(lambda: sonuc, 60)
        self.assertEqual(sonuc, [False])
        self.assertEqual(tampon_metni(p).count("x"), 300000)

    def test_kilit_iletisi_durumda(self):
        p, sonuc = pencere_ac(["sh", "-c", "echo 'E: Could not get lock "
                                           "/var/lib/dpkg/lock-frontend.'; exit 100"])
        olaylari_isle(lambda: sonuc)
        self.assertEqual(sonuc, [False])
        self.assertEqual(p.durum.get_text(), magaza.M("kilit_mesgul"))


@unittest.skipUnless(GTK_VAR, "ekran/GTK yok")
class M07TamponTesti(unittest.TestCase):
    def test_tampon_sinirli(self):
        n = magaza.IslemPenceresi.SATIR_SINIRI + 3000
        p, sonuc = pencere_ac(["sh", "-c", f"i=0; while [ $i -lt {n} ]; do echo satir$i; "
                                           f"i=$((i+1)); done"])
        olaylari_isle(lambda: sonuc, 60)
        self.assertEqual(sonuc, [True])
        self.assertLessEqual(p.tampon.get_line_count(), magaza.IslemPenceresi.SATIR_SINIRI + 1)
        self.assertTrue(tampon_metni(p).rstrip().endswith(f"satir{n - 1}"))


@unittest.skipUnless(GTK_VAR, "ekran/GTK yok")
class M02IptalTesti(unittest.TestCase):
    def test_yetki_verildikten_sonra_iptal_durust(self):
        p, sonuc = pencere_ac(["sh", "-c", "sleep 1; exit 0"])
        olaylari_isle(lambda: p.surec is not None, 5)

        def izin_yok():
            raise PermissionError(1, "Operation not permitted")
        p.surec.terminate = izin_yok      # root olmus pkexec surecinin davranisi
        p._kapat()
        self.assertTrue(p.durdurulamaz)
        self.assertFalse(p.iptal_edildi)
        self.assertFalse(p._yok_edildi)
        self.assertEqual(p.durum.get_text(), magaza.M("iptal_edilemez"))
        p._kapat()                         # ikinci tiklama yalnizca gizler
        self.assertFalse(p.get_visible())
        self.assertFalse(p._yok_edildi)
        olaylari_isle(lambda: sonuc, 10)
        self.assertEqual(sonuc, [True])   # islem bitti ve basarili sayildi

    def test_yetki_beklerken_iptal_gercekten_iptal(self):
        p, sonuc = pencere_ac(["sleep", "30"])
        olaylari_isle(lambda: p.surec is not None, 5)
        p._kapat()
        olaylari_isle(lambda: sonuc, 10)
        self.assertEqual(sonuc, [False])
        self.assertTrue(p.iptal_edildi)
        self.assertTrue(p._yok_edildi)

    def test_carpi_dugmesi_gizler(self):
        p, sonuc = pencere_ac(["sh", "-c", "sleep 1; exit 0"])
        olaylari_isle(lambda: p.surec is not None, 5)
        self.assertTrue(p._kapatiliyor())
        self.assertFalse(p.get_visible())
        self.assertFalse(p._yok_edildi)
        olaylari_isle(lambda: sonuc, 10)
        self.assertEqual(sonuc, [True])

    def test_gizli_pencere_one_getirilir(self):
        sunulan = []
        p = types.SimpleNamespace(_yok_edildi=False, present=lambda: sunulan.append(1))
        ben = types.SimpleNamespace(islem_penceresi=p)
        magaza.MagazaPenceresi._mesgul_uyar(ben)
        self.assertEqual(sunulan, [1])


@unittest.skipUnless(GTK_VAR, "ekran/GTK yok")
class M03OnayPenceresiTesti(unittest.TestCase):
    def _sor(self, sonuc, eylem):
        magaza.DIL = "tr"
        kayit = {}

        def bul(kok, tur):
            bulunan = []

            def gez(w):
                if isinstance(w, tur):
                    bulunan.append(w)
                if isinstance(w, Gtk.Container):
                    for c in w.get_children():
                        gez(c)
            gez(kok)
            return bulunan

        def isle():
            d = next((w for w in Gtk.Window.list_toplevels()
                      if isinstance(w, Gtk.Dialog) and w.get_visible()), None)
            if d is None:
                return True
            dugmeler = {b.get_label(): b for b in bul(d, Gtk.Button)
                        if not isinstance(b, Gtk.CheckButton)}
            kutular = bul(d, Gtk.CheckButton)
            yazilar = " ".join(e.get_text() for e in bul(d, Gtk.Label))
            kayit.update(dugmeler=dugmeler, kutular=kutular, yazilar=yazilar)
            eylem(d, dugmeler, kutular, kayit)
            return False
        GLib.timeout_add(100, isle)
        u = {"paket": "clamav", "ad": {"tr": "ClamAV", "en": "ClamAV"}}
        cevap = magaza.MagazaPenceresi._kaldirma_sor(Gtk.Window(), u, sonuc)
        return cevap, kayit

    def test_korunan_pakette_ek_onay(self):
        def eylem(d, dugmeler, kutular, kayit):
            kaldir = dugmeler[magaza.M("kaldir")]
            kayit["once"] = kaldir.get_sensitive()
            kutular[0].set_active(True)
            kayit["sonra"] = kaldir.get_sensitive()
            kaldir.clicked()
        cevap, kayit = self._sor({"paketler": ["clamav", "clamav-freshclam"], "temel": False},
                                 eylem)
        self.assertTrue(cevap)
        self.assertFalse(kayit["once"])
        self.assertTrue(kayit["sonra"])
        self.assertIn("Carotene", kayit["yazilar"])
        self.assertIn("CarotOS USB Denetimi", kayit["yazilar"])
        self.assertIn("clamav-freshclam", kayit["yazilar"])

    def test_iptal_kaldirmaz(self):
        def eylem(d, dugmeler, kutular, kayit):
            dugmeler[magaza.M("iptal")].clicked()
        cevap, _ = self._sor({"paketler": ["clamav"], "temel": False}, eylem)
        self.assertFalse(cevap)

    def test_korunmayan_pakette_tek_onay(self):
        def eylem(d, dugmeler, kutular, kayit):
            kayit["kutu_sayisi"] = len(kutular)
            dugmeler[magaza.M("kaldir")].clicked()
        cevap, kayit = self._sor({"paketler": ["htop"], "temel": False}, eylem)
        self.assertTrue(cevap)
        self.assertEqual(kayit["kutu_sayisi"], 0)

    def test_temel_pakette_kaldirma_yok(self):
        def eylem(d, dugmeler, kutular, kayit):
            kayit["kaldir_var"] = magaza.M("kaldir") in dugmeler
            dugmeler[magaza.M("kapat")].clicked()
        cevap, kayit = self._sor({"paketler": ["bash"], "temel": True}, eylem)
        self.assertFalse(cevap)
        self.assertFalse(kayit["kaldir_var"])

    def test_hesaplanamazsa_uyari(self):
        def eylem(d, dugmeler, kutular, kayit):
            kutular[0].set_active(True)
            dugmeler[magaza.M("kaldir")].clicked()
        cevap, kayit = self._sor(None, eylem)
        self.assertTrue(cevap)
        self.assertIn(magaza.M("kaldir_hesaplanamadi"), kayit["yazilar"])


# --- M-02 karari: root yardimcisi carotos-magaza-apt ---------------------------------
YARDIMCI_YOL = os.path.join(KOK, "config", "includes.chroot", "usr", "sbin",
                            "carotos-magaza-apt")
with open(YARDIMCI_YOL, "rb") as _f:
    YARDIMCI_KAYNAK = _f.read().decode("utf-8")
_yspec = importlib.util.spec_from_loader(
    "carotos_magaza_apt", importlib.machinery.SourceFileLoader("carotos_magaza_apt",
                                                               YARDIMCI_YOL))
yardimci = importlib.util.module_from_spec(_yspec)
_yspec.loader.exec_module(yardimci)

# Sahte apt-get: cagrilari kayit dosyasina yazar; --download-only'de SAHTE_INDIRME'ye gore
# bekler/duser. Gercek apt hic calismaz.
SAHTE_APT = """#!/bin/sh
echo "$*" >> "$SAHTE_KAYIT"
case "$*" in
  *--download-only*)
    case "$SAHTE_INDIRME" in
      bekle) trap 'echo durdu >> "$SAHTE_KAYIT"; exit 130' INT TERM
             i=0; while [ $i -lt 300 ]; do sleep 0.1; i=$((i+1)); done; exit 0 ;;
      dus) exit 100 ;;
    esac ;;
esac
exit 0
"""


class M02YardimciTesti(unittest.TestCase):
    def setUp(self):
        self.dizin = tempfile.mkdtemp(prefix="magaza-apt-")
        self.apt = os.path.join(self.dizin, "apt-get")
        with open(self.apt, "w") as f:
            f.write(SAHTE_APT)
        os.chmod(self.apt, 0o755)
        self.kayit = os.path.join(self.dizin, "kayit")

    def calistir(self, argv, indirme="", girdi=None):
        import io
        ortam = dict(yardimci.ORTAM, SAHTE_KAYIT=self.kayit, SAHTE_INDIRME=indirme)
        cikti = io.StringIO()
        with mock.patch.object(sys, "stdout", cikti):
            kod = yardimci.main(argv, girdi if girdi is not None else io.StringIO(""),
                                self.apt, ortam)
        cagrilar = []
        if os.path.exists(self.kayit):
            with open(self.kayit) as f:
                cagrilar = f.read().splitlines()
        return kod, cikti.getvalue().splitlines(), cagrilar

    def test_kaynak_kurallari(self):
        self.assertTrue(YARDIMCI_KAYNAK.startswith("#!/usr/bin/python3 -I\n"))
        self.assertIn("sys.dont_write_bytecode = True", YARDIMCI_KAYNAK)
        self.assertNotIn("shell=True", YARDIMCI_KAYNAK)
        self.assertNotRegex(YARDIMCI_KAYNAK, r"(?m)^\s*(from|import)\s+(yetkili|ortak|dil)\b")
        self.assertEqual(yardimci.APT_GET, "/usr/bin/apt-get")
        self.assertEqual(yardimci.ORTAM["LC_ALL"], "C")
        self.assertEqual(yardimci.ORTAM["DEBIAN_FRONTEND"], "noninteractive")
        self.assertEqual(yardimci.IPTAL_KODU, magaza_sabit("IPTAL_KODU"))

    def test_arguman_dogrulama(self):
        coz = yardimci.argumanlari_coz
        self.assertEqual(coz(["install", "--", "nmap", "htop"]), ("install", ["nmap", "htop"]))
        self.assertEqual(coz(["upgrade"]), ("upgrade", []))
        self.assertEqual(coz(["update"]), ("update", []))
        for kotu in ([], ["purge", "--", "nmap"], ["install"], ["install", "--"],
                     ["install", "nmap"], ["install", "--", "-oAPT::x=y"],
                     ["install", "--", "./x.deb"], ["install", "--", "nmap=1.0"],
                     ["install", "--", "Nmap"], ["remove", "--", "a/b"],
                     ["upgrade", "--", "nmap"], ["update", "x"],
                     ["install", "--", "nmap", "nmap"]):
            with self.subTest(argv=kotu):
                with self.assertRaises(ValueError):
                    coz(kotu)

    def test_sabit_secenekler(self):
        indir, asil = yardimci.komutlar("install", ["nmap"])
        self.assertEqual(asil[0], "/usr/bin/apt-get")
        for k in (indir, asil):
            self.assertIn("DPkg::Lock::Timeout=60", k)
            self.assertEqual(k[-2:], ["--", "nmap"])
        self.assertIn("--download-only", indir)
        self.assertIn("Dpkg::Options::=--force-confdef", asil)
        self.assertIn("Dpkg::Options::=--force-confold", asil)
        self.assertNotIn("--download-only", asil)
        indir, asil = yardimci.komutlar("upgrade", [])
        self.assertIn("--download-only", indir)
        self.assertIn("--force-confold", " ".join(asil))
        self.assertIsNone(yardimci.komutlar("remove", ["nmap"])[0])
        self.assertIsNone(yardimci.komutlar("update", [])[0])

    def test_gecersiz_arguman_apt_calismaz(self):
        kod, cikti, cagrilar = self.calistir(["install", "--", "-oAPT::x=y"])
        self.assertEqual(kod, yardimci.KULLANIM_KODU)
        self.assertEqual(cagrilar, [])
        self.assertEqual(cikti, [])

    def test_kurulum_fazlari(self):
        kod, cikti, cagrilar = self.calistir(["install", "--", "nmap"])
        self.assertEqual(kod, 0)
        self.assertEqual(cikti, ["@@CAROTOS-FAZ indirme", "@@CAROTOS-FAZ kurulum"])
        self.assertEqual(len(cagrilar), 2)
        self.assertIn("--download-only", cagrilar[0])
        self.assertNotIn("--download-only", cagrilar[1])

    def test_indirmede_iptal(self):
        import threading
        r, w = os.pipe()
        girdi = os.fdopen(r, "r")

        def yaz():
            time.sleep(0.5)
            os.write(w, b"iptal\n")
        threading.Thread(target=yaz, daemon=True).start()
        bas = time.time()
        kod, cikti, cagrilar = self.calistir(["install", "--", "nmap"], "bekle", girdi)
        os.close(w)
        girdi.close()
        self.assertLess(time.time() - bas, 15)
        self.assertEqual(kod, yardimci.IPTAL_KODU)
        self.assertEqual(cikti, ["@@CAROTOS-FAZ indirme", "@@CAROTOS-IPTAL"])
        self.assertEqual(len([c for c in cagrilar if c != "durdu"]), 1)   # asil islem yok
        self.assertIn("durdu", cagrilar)

    def test_indirme_hatasi_kuruluma_gecmez(self):
        kod, cikti, cagrilar = self.calistir(["upgrade"], "dus")
        self.assertEqual(kod, 100)
        self.assertEqual(cikti, ["@@CAROTOS-FAZ indirme"])
        self.assertEqual(len(cagrilar), 1)

    def test_kaldirma_ve_yenilemede_iptal_noktasi_yok(self):
        for argv in (["remove", "--", "nmap"], ["update"]):
            with self.subTest(argv=argv):
                if os.path.exists(self.kayit):
                    os.remove(self.kayit)
                kod, cikti, cagrilar = self.calistir(argv)
                self.assertEqual(kod, 0)
                self.assertEqual(cikti, ["@@CAROTOS-FAZ kurulum"])
                self.assertEqual(len(cagrilar), 1)


def magaza_sabit(ad):
    return gtk_siz_yukle(sahte_yol)[ad]


class M02YardimciKomutuTesti(unittest.TestCase):
    def setUp(self):
        self.a = gtk_siz_yukle(sahte_yol)

    def test_yardimci_varsa_tam_yolla(self):
        with mock.patch("os.path.isfile", return_value=True), \
                mock.patch("os.access", return_value=True):
            k = self.a["yardimci_komutu"]("install", "nmap", "htop")
            self.assertEqual(k, ["/usr/bin/pkexec", "/usr/sbin/carotos-magaza-apt",
                                 "install", "--", "nmap", "htop"])
            self.assertEqual(self.a["yardimci_komutu"]("upgrade", "x"),
                             ["/usr/bin/pkexec", "/usr/sbin/carotos-magaza-apt",
                              "upgrade"])
            with self.assertRaises(ValueError):
                self.a["yardimci_komutu"]("install", "-oAPT::x=y")
            with self.assertRaises(ValueError):
                self.a["yardimci_komutu"]("purge", "nmap")

    def test_yardimci_yoksa_none(self):
        with mock.patch("os.path.isfile", return_value=False):
            self.assertIsNone(self.a["yardimci_komutu"]("install", "nmap"))

    def test_magaza_eylemleri_yardimciyi_dener(self):
        for yontem, beklenen in (("sepeti_kur", 'eylem="install"'),
                                 ("_eylem_baslat", "eylem=islem"),
                                 ("depoyu_yenile", 'eylem="update"'),
                                 ("tumunu_guncelle", 'eylem="upgrade"')):
            with self.subTest(yontem=yontem):
                self.assertIn(beklenen, yontem_govdesi("MagazaPenceresi", yontem))

    def test_yeni_metinler_iki_dilde(self):
        metin = ast.literal_eval(ast.get_source_segment(KAYNAK, next(
            n for n in AGAC.body if isinstance(n, ast.Assign)
            and getattr(n.targets[0], "id", "") == "METIN")).split("=", 1)[1].strip())
        for anahtar in ("gizle", "guvenli_iptal", "guvenli_iptal_suruyor",
                        "guvenli_iptal_bitti"):
            with self.subTest(anahtar=anahtar):
                self.assertEqual(set(metin[anahtar]), {"tr", "en"})
        self.assertEqual(metin["guvenli_iptal_bitti"]["tr"],
                         "İptal edildi, sistemde değişiklik yapılmadı.")


# Sahte yardimci: faz satirlarini yazar; indirmede stdin'den "iptal" bekler.
SAHTE_YARDIMCI = r"""
import sys, time
kip = sys.argv[1]
def yaz(s):
    sys.stdout.write(s + "\n"); sys.stdout.flush()
time.sleep(0.3)                       # parola penceresi
if kip == "indir_iptal":
    yaz("@@CAROTOS-FAZ indirme"); yaz("indiriliyor")
    if sys.stdin.readline().strip() == "iptal":
        yaz("@@CAROTOS-IPTAL"); sys.exit(75)
    sys.exit(0)
if kip == "fazlar":
    yaz("@@CAROTOS-FAZ indirme"); time.sleep(0.8)
    yaz("@@CAROTOS-FAZ kurulum"); time.sleep(0.8); sys.exit(0)
if kip == "kurulum_hata":
    yaz("@@CAROTOS-FAZ kurulum"); time.sleep(0.8); sys.exit(1)
"""


@unittest.skipUnless(GTK_VAR, "ekran/GTK yok")
class M02DugmeTesti(unittest.TestCase):
    def ac(self, kip):
        betik = os.path.join(tempfile.mkdtemp(prefix="sahte-yardimci-"), "y.py")
        with open(betik, "w") as f:
            f.write(SAHTE_YARDIMCI)
        sonuc = []
        p = magaza.IslemPenceresi(Gtk.Window(), "deneme", [sys.executable, betik, kip],
                                  lambda b: sonuc.append(b), yardimci=True)
        p.baslat()
        return p, sonuc

    def test_parola_beklerken_yalnizca_iptal(self):
        p, sonuc = self.ac("fazlar")
        self.assertTrue(p.kapat_dugme.get_visible())
        self.assertEqual(p.kapat_dugme.get_label(), magaza.M("iptal"))
        self.assertFalse(p.gizle_dugme.get_visible())
        self.assertFalse(p.guvenli_dugme.get_visible())
        olaylari_isle(lambda: sonuc, 15)

    def test_indirmede_gizle_ve_guvenli_iptal_kurulumda_yalnizca_gizle(self):
        p, sonuc = self.ac("fazlar")
        olaylari_isle(lambda: p.faz == "indirme", 10)
        self.assertTrue(p.gizle_dugme.get_visible())
        self.assertTrue(p.guvenli_dugme.get_visible())
        self.assertFalse(p.kapat_dugme.get_visible())
        self.assertTrue(p.durdurulamaz)
        olaylari_isle(lambda: p.faz == "kurulum", 10)
        self.assertTrue(p.gizle_dugme.get_visible())
        self.assertFalse(p.guvenli_dugme.get_visible())
        self.assertFalse(p.kapat_dugme.get_visible())
        p._guvenli_iptal()                 # kurulumda etkisiz
        self.assertFalse(p.guvenli_iptal_istendi)
        olaylari_isle(lambda: sonuc, 10)
        self.assertEqual(sonuc, [True])
        self.assertTrue(p.kapat_dugme.get_visible())
        self.assertEqual(p.kapat_dugme.get_label(), magaza.M("kapat"))
        self.assertFalse(p.gizle_dugme.get_visible())
        self.assertNotIn("@@CAROTOS", tampon_metni(p))

    def test_guvenli_iptal(self):
        p, sonuc = self.ac("indir_iptal")
        olaylari_isle(lambda: p.faz == "indirme", 10)
        p.guvenli_dugme.clicked()
        self.assertFalse(p.guvenli_dugme.get_sensitive())
        olaylari_isle(lambda: sonuc, 10)
        self.assertEqual(sonuc, [False])
        self.assertTrue(p.iptal_edildi)
        self.assertEqual(p.durum.get_text(), magaza.M("guvenli_iptal_bitti"))
        self.assertFalse(p.guvenli_dugme.get_visible())
        self.assertIn("indiriliyor", tampon_metni(p))
        self.assertNotIn("@@CAROTOS", tampon_metni(p))

    def test_gizle_ve_basarisizlikta_kendiliginden_acilir(self):
        p, sonuc = self.ac("kurulum_hata")
        olaylari_isle(lambda: p.faz == "kurulum", 10)
        p.gizle_dugme.clicked()
        self.assertFalse(p.get_visible())
        self.assertFalse(p._yok_edildi)
        olaylari_isle(lambda: sonuc, 10)
        self.assertEqual(sonuc, [False])
        self.assertTrue(p.get_visible())

    def test_yardimcisiz_yolda_guvenli_iptal_yok(self):
        p, sonuc = pencere_ac(["sh", "-c", "sleep 1; exit 0"])
        olaylari_isle(lambda: p.surec is not None, 5)

        def izin_yok():
            raise PermissionError(1, "Operation not permitted")
        p.surec.terminate = izin_yok
        p._kapat()
        self.assertTrue(p.gizle_dugme.get_visible())
        self.assertFalse(p.kapat_dugme.get_visible())
        self.assertFalse(p.guvenli_dugme.get_visible())
        p._guvenli_iptal()
        self.assertFalse(p.guvenli_iptal_istendi)
        olaylari_isle(lambda: sonuc, 10)
        self.assertEqual(sonuc, [True])

    def test_islem_baslat_yardimciyi_secer(self):
        with mock.patch.object(magaza, "yardimci_komutu",
                               return_value=["sh", "-c", "exit 0"]) as yk, \
                mock.patch.object(magaza.IslemPenceresi, "baslat"):
            magaza.MagazaPenceresi._islem_baslat(Gtk.Window(), "b", ["eski"], None,
                                                 eylem="install", paketler=("nmap",))
        yk.assert_called_once_with("install", "nmap")
        with mock.patch.object(magaza, "yardimci_komutu", return_value=None), \
                mock.patch.object(magaza.IslemPenceresi, "baslat"):
            w = Gtk.Window()
            magaza.MagazaPenceresi._islem_baslat(w, "b", ["eski"], None, eylem="remove",
                                                 paketler=("nmap",))
            self.assertEqual(w.islem_penceresi.komut, ["eski"])
            self.assertFalse(w.islem_penceresi.yardimci)


# --- M-06 karari: tek ornek -----------------------------------------------------------
class M06TekOrnekTesti(unittest.TestCase):
    def test_kaynakta_uygulama_kimligi(self):
        self.assertIn('UYGULAMA_KIMLIGI = "org.carotos.Magaza"', KAYNAK)
        self.assertIn("Gio.ApplicationFlags.HANDLES_COMMAND_LINE", KAYNAK)
        self.assertNotIn("Gtk.main()", yontem_govdesi_islev("main"))

    def test_paket_argumani(self):
        pa = gtk_siz_yukle(sahte_yol)["paket_argumani"]
        self.assertEqual(pa(["m", "--paket", "clamav"]), "clamav")
        self.assertIsNone(pa(["m"]))
        self.assertIsNone(pa(["m", "--paket"]))
        self.assertIsNone(pa(["m", "--paket", "-oAPT::x"]))


def yontem_govdesi_islev(ad):
    return ast.get_source_segment(KAYNAK, next(
        n for n in AGAC.body if isinstance(n, ast.FunctionDef) and n.name == ad))


@unittest.skipUnless(GTK_VAR, "ekran/GTK yok")
class M06KomutSatiriTesti(unittest.TestCase):
    def test_ikinci_baslatma_acik_pencereye_gider(self):
        sunulan, acilan = [], []
        u = {"paket": "clamav"}
        pencere = types.SimpleNamespace(uygulamalar=[u], present=lambda: sunulan.append(1),
                                        detay_goster=acilan.append)
        ben = types.SimpleNamespace(pencere=pencere, katalog={})
        ks = types.SimpleNamespace(get_arguments=lambda: ["magaza", "--paket", "clamav"])
        with mock.patch.object(magaza, "MagazaPenceresi") as yeni:
            self.assertEqual(magaza.MagazaUygulamasi.do_command_line(ben, ks), 0)
            yeni.assert_not_called()
        self.assertEqual(sunulan, [1])
        self.assertEqual(acilan, [u])

    def test_katalogda_olmayan_paket_acilmaz(self):
        acilan = []
        pencere = types.SimpleNamespace(uygulamalar=[{"paket": "clamav"}],
                                        present=lambda: None, detay_goster=acilan.append)
        magaza.paketi_ac(pencere, "nmap", gecikme=0)
        magaza.paketi_ac(pencere, None, gecikme=0)
        self.assertEqual(acilan, [])

    def test_uygulama_kimligi_ve_bayraklar(self):
        a = magaza.MagazaUygulamasi({})
        self.assertEqual(a.get_application_id(), "org.carotos.Magaza")
        self.assertTrue(a.get_flags() & magaza.Gio.ApplicationFlags.HANDLES_COMMAND_LINE)




# --- Sepet: toplu kurulum dusunce tek tek denenir ---------------------------------------
# Sahte apt-get: ayni komutta birden cok paket varsa ya da "kotu" paketi varsa duser.
SAHTE_APT_TEKTEK = """#!/bin/sh
echo "$*" >> "$SAHTE_KAYIT"
case "$*" in
  *--download-only*) exit 0 ;;
esac
paket_sayisi=0
for a in "$@"; do
  case "$a" in
    -*|install|-y|--|DPkg*|Acquire*|Dpkg*) ;;
    *) paket_sayisi=$((paket_sayisi+1)) ;;
  esac
done
case "$*" in
  *kotu*) echo "E: Unable to locate package kotu"; exit 100 ;;
esac
[ "$paket_sayisi" -gt 1 ] && exit 100
exit 0
"""


class SepetTekTekTesti(unittest.TestCase):
    def setUp(self):
        self.dizin = tempfile.mkdtemp(prefix="magaza-tektek-")
        self.apt = os.path.join(self.dizin, "apt-get")
        with open(self.apt, "w") as f:
            f.write(SAHTE_APT_TEKTEK)
        os.chmod(self.apt, 0o755)
        self.kayit = os.path.join(self.dizin, "kayit")

    def calistir(self, paketler):
        import io
        ortam = dict(yardimci.ORTAM, SAHTE_KAYIT=self.kayit)
        cikti = io.StringIO()
        with mock.patch.object(sys, "stdout", cikti), \
                mock.patch.object(yardimci, "DPKG", "/yok/dpkg"):
            kod = yardimci.main(["install", "--", *paketler], io.StringIO(""), self.apt, ortam)
        with open(self.kayit) as f:
            return kod, cikti.getvalue().splitlines(), f.read().splitlines()

    def test_toplu_dusunce_tek_tek_kurar(self):
        kod, cikti, cagrilar = self.calistir(["nmap", "htop", "tmux"])
        self.assertEqual(kod, 0)
        tek = [c for c in cagrilar if "--download-only" not in c and c.endswith(("nmap", "htop", "tmux"))]
        self.assertEqual(sum(1 for c in tek if c.split()[-1] in ("nmap", "htop", "tmux")
                             and " -f " in " " + c + " "), 3)
        self.assertNotIn("@@CAROTOS-BASARISIZ", "\n".join(cikti))

    def test_kurulamayan_bildirilir_digerleri_kurulur(self):
        kod, cikti, cagrilar = self.calistir(["nmap", "kotu", "htop"])
        self.assertEqual(kod, yardimci.KISMI_KODU)
        self.assertIn("@@CAROTOS-BASARISIZ kotu", cikti)
        self.assertTrue(any(c.endswith("-- nmap") for c in cagrilar))
        self.assertTrue(any(c.endswith("-- htop") for c in cagrilar))

    def test_tek_paket_dusunce_yedek_yok(self):
        kod, cikti, cagrilar = self.calistir(["kotu"])
        self.assertNotEqual(kod, 0)
        self.assertNotIn("@@CAROTOS-BASARISIZ", "\n".join(cikti))

    def test_kilit_hatasinda_tek_tek_denenmez(self):
        kilitli = os.path.join(self.dizin, "apt-kilit")
        with open(kilitli, "w") as f:
            f.write('#!/bin/sh\necho "$*" >> "$SAHTE_KAYIT"\ncase "$*" in *--download-only*) exit 0;; esac\n'
                    'echo "E: Could not get lock /var/lib/dpkg/lock-frontend"\nexit 100\n')
        os.chmod(kilitli, 0o755)
        import io
        ortam = dict(yardimci.ORTAM, SAHTE_KAYIT=self.kayit)
        with mock.patch.object(sys, "stdout", io.StringIO()), \
                mock.patch.object(yardimci, "DPKG", "/yok/dpkg"):
            kod = yardimci.main(["install", "--", "nmap", "htop"], io.StringIO(""), kilitli, ortam)
        self.assertEqual(kod, 100)
        with open(self.kayit) as f:
            tek = [c for c in f.read().splitlines() if "--download-only" not in c]
        self.assertEqual(len(tek), 2)      # toplu + ilk tek paket; kalanlar denenmedi

    def test_apt_yeniden_deneme_ayari(self):
        self.assertIn("Acquire::Retries=3", yardimci.KILIT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
