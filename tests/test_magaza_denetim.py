#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Magaza guvenlik denetimi duzeltmeleri (M-01..M-07; docs/denetim/carotene-magaza.md).

GTK gerektirmeyen testler kaynaktaki ilgili islevleri ayristirip calistirir; arayuz testleri
ekran yoksa atlanir. Hicbir test pkexec/apt-get'i gercekten calistirmaz.

Calistirma:  xvfb-run -a python3 tests/test_magaza_denetim.py
"""
import ast
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
             "kaldirma_simulasyonu_coz", "kaldirma_simulasyonu", "korunan_etkiler"}
_DEGISKENLER = {"PAKET_ADI", "APT_EYLEMLERI", "_ARAC_ETKI", "KORUNAN"}


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
    ad_alani = {"re": re, "subprocess": subprocess, "dil": dil,
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
        self.assertIn("stdin=subprocess.DEVNULL", yontem_govdesi("IslemPenceresi", "_calis"))

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
