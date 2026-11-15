#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sistem denetimi (docs/denetim/sistem.md, S-01..S-07) duzeltme testleri.

Hook'lar ve root betikleri gercek sisteme dokunmadan, PATH'e konan taklit
komutlarla ve gecici dizinlerde calistirilir. root gerekmez. sh yoksa
(Windows) calistirma testleri atlanir.

Calistirma:  python3 tests/test_sistem_denetim.py
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import py_compile
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(KOK, "config")
HOOKLAR = os.path.join(CONFIG, "hooks", "live")
INC = os.path.join(CONFIG, "includes.chroot")
SH = shutil.which("sh")
POSIX = os.name == "posix"


def oku(yol):
    with open(yol, "rb") as f:
        return f.read().replace(b"\r\n", b"\n").decode("utf-8")


def hook(ad):
    return oku(os.path.join(HOOKLAR, ad))


class Taklit:
    """Gecici dizinde taklit komutlar; her cagri kayit dosyasina yazilir."""

    def __init__(self, test):
        self.kok = tempfile.mkdtemp(prefix="sistem-denetim-")
        test.addCleanup(shutil.rmtree, self.kok, True)
        self.bin = os.path.join(self.kok, "bin")
        os.makedirs(self.bin)
        self.kayit = os.path.join(self.kok, "kayit")
        open(self.kayit, "w").close()

    def komut(self, ad, govde="exit 0"):
        yol = os.path.join(self.bin, ad)
        with open(yol, "w", newline="\n") as f:
            f.write('#!/bin/sh\necho "%s $*" >> "%s"\n%s\n' % (ad, self.kayit, govde))
        os.chmod(yol, 0o755)

    def cagrilar(self):
        with open(self.kayit) as f:
            return f.read().splitlines()

    def ortam(self, **ek):
        e = dict(os.environ, PATH=self.bin + ":/usr/bin:/bin")
        e.update(ek)
        return e

    def calistir(self, betik, cwd=None, **ek):
        return subprocess.run([SH, "-s"], input=betik.encode("utf-8"), cwd=cwd or self.kok,
                              env=self.ortam(**ek), capture_output=True, timeout=60)


# ---------------------------------------------------------------------------
# S-02: hook'lar sonuclarini dogrular
# ---------------------------------------------------------------------------
@unittest.skipUnless(SH and POSIX, "sh gerekir")
class HookDogrulamaTesti(unittest.TestCase):
    def test_wireshark_yetki_yoksa_derleme_durur(self):
        betik = hook("9989-carotos-wireshark.hook.chroot")
        for getcap_cikti, stat_grup, beklenen in (
                ("", "wireshark", 1),                                          # setcap calismadi
                ("/usr/bin/dumpcap cap_net_admin,cap_net_raw=eip", "root", 1),   # grup yanlis
                ("/usr/bin/dumpcap cap_net_admin,cap_net_raw=eip", "wireshark", 0)):
            with self.subTest(getcap=getcap_cikti, grup=stat_grup):
                t = Taklit(self)
                for ad in ("apt-get", "debconf-set-selections", "dpkg-reconfigure", "getent", "ls"):
                    t.komut(ad)
                t.komut("getcap", "echo '%s'" % getcap_cikti)
                t.komut("stat", "echo '%s'" % stat_grup)
                s = t.calistir(betik.replace("/usr/bin/dumpcap", os.path.join(t.kok, "dumpcap")))
                self.assertEqual(s.returncode, beklenen, s.stderr.decode())
                if beklenen:
                    self.assertIn("CarotOS HATA", s.stderr.decode())

    def test_wireshark_setuid_kalirsa_derleme_durur(self):
        betik = hook("9989-carotos-wireshark.hook.chroot")
        t = Taklit(self)
        for ad in ("apt-get", "debconf-set-selections", "dpkg-reconfigure", "getent", "ls"):
            t.komut(ad)
        t.komut("getcap", "echo '/usr/bin/dumpcap cap_net_raw=eip'")
        t.komut("stat", "echo wireshark")
        dumpcap = os.path.join(t.kok, "dumpcap")
        open(dumpcap, "w").close()
        os.chmod(dumpcap, 0o4750)
        s = t.calistir(betik.replace("/usr/bin/dumpcap", dumpcap))
        self.assertEqual(s.returncode, 1, s.stderr.decode())

    def _carotene(self, etkin):
        t = Taklit(self)
        for ad in ("apt-get", "freshclam", "rm", "chmod", "gtk-update-icon-cache"):
            t.komut(ad)
        t.komut("systemctl", 'case "$1" in is-enabled) exit %d;; esac; exit 0' % (0 if etkin else 1))
        return t, t.calistir(hook("9991-carotos-carotene.hook.chroot"))

    def test_freshclam_etkin_kalirsa_derleme_durur(self):
        _, s = self._carotene(etkin=True)
        self.assertEqual(s.returncode, 1)
        self.assertIn("clamav-freshclam", s.stderr.decode())

    def test_freshclam_kapaliysa_devam_eder(self):
        t, s = self._carotene(etkin=False)
        self.assertEqual(s.returncode, 0, s.stderr.decode())
        self.assertIn("systemctl disable clamav-freshclam.service", t.cagrilar())

    def test_carotpot_birimleri_dogrulanir(self):
        betik = hook("9992-carotos-carotpot.hook.chroot")
        for engel, tuzak, beklenen in ((0, 1, 0), (1, 1, 1), (0, 0, 1)):
            with self.subTest(engel_etkin=engel == 0, tuzak_etkin=tuzak == 0):
                t = Taklit(self)
                for ad in ("apt-get", "getent", "adduser", "chmod", "find", "gtk-update-icon-cache"):
                    t.komut(ad)
                t.komut("systemctl", 'case "$*" in "is-enabled --quiet carotpot-engel-temizle.service") exit %d;; '
                                     '"is-enabled --quiet carotpot.service") exit %d;; esac; exit 0' % (engel, tuzak))
                s = t.calistir(betik)
                self.assertEqual(s.returncode, beklenen, s.stderr.decode())

    def test_ikon_servisi_etkinlesmezse_derleme_durur(self):
        betik = hook("9998-carotos-ikon-servis.hook.chroot")
        for kod, beklenen in ((1, 1), (0, 0)):
            with self.subTest(is_enabled=kod):
                t = Taklit(self)
                t.komut("chmod")
                t.komut("systemctl", 'case "$1" in is-enabled) exit %d;; esac; exit 0' % kod)
                s = t.calistir(betik)
                self.assertEqual(s.returncode, beklenen, s.stderr.decode())
                self.assertIn("systemctl enable carotos-ikon-onbellek.service", t.cagrilar())

    def test_splash_hedef_yoksa_derleme_durur(self):
        t = Taklit(self)
        os.makedirs(os.path.join(t.kok, "config"))
        with open(os.path.join(t.kok, "config", "carotos-splash.png"), "wb") as f:
            f.write(b"\x89PNG carotos")
        s = t.calistir(hook("9998-carotos-splash.hook.binary"))
        self.assertEqual(s.returncode, 1)
        self.assertIn("hedef dizini", s.stderr.decode())

    def test_splash_kopyalanir_ve_sayilir(self):
        t = Taklit(self)
        os.makedirs(os.path.join(t.kok, "config"))
        os.makedirs(os.path.join(t.kok, "isolinux"))
        os.makedirs(os.path.join(t.kok, "boot", "grub"))
        with open(os.path.join(t.kok, "boot", "grub", "splash.svg"), "w") as f:
            f.write("<svg/>")
        with open(os.path.join(t.kok, "config", "carotos-splash.png"), "wb") as f:
            f.write(b"\x89PNG carotos")
        s = t.calistir(hook("9998-carotos-splash.hook.binary"))
        self.assertEqual(s.returncode, 0, s.stderr.decode())
        self.assertIn("(2 dizin)", s.stdout.decode())
        for d in ("isolinux", "boot/grub"):
            with open(os.path.join(t.kok, d, "splash.png"), "rb") as f:
                self.assertEqual(f.read(), b"\x89PNG carotos")
        self.assertFalse(os.path.exists(os.path.join(t.kok, "boot", "grub", "splash.svg")))

    def test_liveuser_init_config_yoksa_derleme_durur(self):
        t = Taklit(self)
        yol = os.path.join(t.kok, "init-config.sh")
        betik = hook("9997-carotos-liveuser.hook.chroot").replace("/usr/lib/live/init-config.sh", yol)
        s = t.calistir(betik)
        self.assertEqual(s.returncode, 1)
        self.assertIn("CarotOS HATA", s.stderr.decode())
        # beklenen varsayilanlar: ikisi de degisir
        with open(yol, "w") as f:
            f.write('LIVE_HOSTNAME="debian"\nLIVE_USER_FULLNAME="Debian Live user"\n')
        s = t.calistir(betik)
        self.assertEqual(s.returncode, 0, s.stderr.decode())
        icerik = open(yol).read()
        self.assertIn('LIVE_HOSTNAME="carotos"', icerik)
        self.assertIn('LIVE_USER_FULLNAME="CarotOS Live User"', icerik)
        # live-config tam adi degistirdiyse sessizce "Debian" kalmaz
        with open(yol, "w") as f:
            f.write('LIVE_HOSTNAME="debian"\nLIVE_USER_FULLNAME="Debian Live User (yeni)"\n')
        self.assertEqual(t.calistir(betik).returncode, 1)


class HookIcerikTesti(unittest.TestCase):
    def setUp(self):
        self.h9999 = hook("9999-carotos-setup.hook.chroot")

    def test_locale_gen_sessizce_gecmez(self):
        self.assertNotIn("locale-gen || true", self.h9999)
        self.assertIn("locale -a | grep -qi '^tr_TR", self.h9999)

    def test_uygulama_chmodlari_hatayi_yutmaz(self):
        for satir in self.h9999.splitlines():
            if satir.strip().startswith("chmod"):
                self.assertNotIn("|| true", satir)

    def test_root_dosyalari_root_ve_go_w(self):
        for parca in ("chown -R -h root:root", "chmod -R go-w", "-perm /022", "! -user root"):
            self.assertIn(parca, self.h9999)
        for yol in ("/opt/carotos", "/usr/local/sbin", "/etc/systemd/system"):
            self.assertIn(yol, self.h9999)
        # izin duzeltmesi hook'un en sonunda: diger adimlarin olusturdugu dosyalar da kapsanir
        self.assertGreater(self.h9999.index("chmod -R go-w"), self.h9999.index("carotos-archive-keyring"))

    def test_hooklarin_calistirilabilir_kipi_git_te(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("git yok")
        r = subprocess.run([git, "ls-files", "-s", "config/hooks/live"], capture_output=True, text=True, cwd=KOK)
        if not r.stdout.strip():
            self.skipTest("git kaydi yok")
        for satir in r.stdout.splitlines():
            kip, _, _, yol = satir.split(None, 3)
            if kip == "120000":
                continue                               # live-build'in kendi hook'larina sembolik bag
            self.assertEqual(kip, "100755", yol)


# ---------------------------------------------------------------------------
# S-01 (karar: ufw varsayilan kapali). Acilinca Debian varsayilani gelen = DROP
# olmali; CarotOS bunu ezen bir dosya ya da hook tasimamali.
# ---------------------------------------------------------------------------
class GuvenlikDuvariTesti(unittest.TestCase):
    def test_ufw_kurulu_ama_etkinlestirilmez(self):
        satirlar = [s.strip() for s in oku(os.path.join(CONFIG, "package-lists", "carotos.list.chroot")).splitlines()]
        self.assertIn("ufw", satirlar)
        for ad in os.listdir(HOOKLAR):
            yol = os.path.join(HOOKLAR, ad)
            if not os.path.isfile(yol) or os.path.islink(yol):
                continue
            icerik = oku(yol)
            if not icerik.startswith("#!"):
                continue
            with self.subTest(hook=ad):
                self.assertNotIn("ufw enable", icerik)
                self.assertNotIn("enable ufw", icerik)
                self.assertNotIn("ENABLED=yes", icerik)

    def test_ufw_varsayilanlarini_ezen_dosya_yok(self):
        # /etc/default/ufw (DEFAULT_INPUT_POLICY="DROP") ve /etc/ufw/* Debian paketinden gelir
        self.assertFalse(os.path.exists(os.path.join(INC, "etc", "default", "ufw")))
        self.assertFalse(os.path.exists(os.path.join(INC, "etc", "ufw")))
        for ad in os.listdir(HOOKLAR):
            yol = os.path.join(HOOKLAR, ad)
            if os.path.isfile(yol) and not os.path.islink(yol):
                icerik = oku(yol)
                if icerik.startswith("#!"):
                    self.assertNotIn("DEFAULT_INPUT_POLICY", icerik, ad)
                    self.assertNotIn("/etc/default/ufw", icerik, ad)


# ---------------------------------------------------------------------------
# S-03: ilk acilis
# ---------------------------------------------------------------------------
FIRSTBOOT = os.path.join(INC, "usr", "local", "sbin", "carotos-firstboot.sh")
FIRSTBOOT_BIRIM = os.path.join(INC, "etc", "systemd", "system", "carotos-firstboot.service")


@unittest.skipUnless(SH and POSIX, "sh gerekir")
class FirstbootTesti(unittest.TestCase):
    def calistir(self, kullanicilar, sudo_uyeleri="", usermod_hata=False, wireshark=True):
        t = Taklit(self)
        passwd = os.path.join(t.kok, "passwd")
        with open(passwd, "w") as f:
            f.write("root:x:0:0::/root:/bin/bash\nnobody:x:65534:65534::/:/usr/sbin/nologin\n")
            for i, k in enumerate(kullanicilar):
                f.write("%s:x:%d:%d::/home/%s:/bin/bash\n" % (k, 1000 + i, 1000 + i, k))
        t.komut("getent", 'case "$2" in sudo) echo "sudo:x:27:%s";; wireshark) %s;; *) exit 2;; esac'
                % (sudo_uyeleri, "echo wireshark:x:120:" if wireshark else "exit 2"))
        t.komut("usermod", "exit %d" % (1 if usermod_hata else 0))
        t.komut("logger")
        sources = os.path.join(t.kok, "sources.list")
        with open(sources, "w") as f:
            f.write("deb cdrom:[CarotOS 1.3]/ trixie main\ndeb http://deb.debian.org/debian trixie main\n")
        damga = os.path.join(t.kok, "lib")
        s = t.calistir(oku(FIRSTBOOT), CAROTOS_PASSWD=passwd, CAROTOS_DAMGA_DIZINI=damga, CAROTOS_SOURCES=sources)
        self.sources = open(sources).read()
        self.damga_var = os.path.exists(os.path.join(damga, "firstboot.done"))
        return s, [c for c in t.cagrilar() if c.startswith("usermod")]

    def test_tek_kullanici_sudo_ve_wireshark(self):
        s, u = self.calistir(["ayse"])
        self.assertEqual(s.returncode, 0, s.stderr.decode())
        self.assertEqual(u, ["usermod -aG sudo ayse", "usermod -aG wireshark ayse"])
        self.assertTrue(self.damga_var)
        self.assertIn("#deb cdrom:", self.sources)
        self.assertIn("\ndeb http://deb.debian.org", self.sources)

    def test_birden_cok_kullanici_sessizce_yonetici_olmaz(self):
        s, u = self.calistir(["ayse", "sinif2"])
        self.assertEqual(s.returncode, 0)
        self.assertNotIn("usermod -aG sudo ayse", u)
        self.assertNotIn("usermod -aG sudo sinif2", u)
        self.assertEqual(u, ["usermod -aG wireshark ayse", "usermod -aG wireshark sinif2"])

    def test_sudo_grubunda_uye_varsa_dokunulmaz(self):
        s, u = self.calistir(["ayse"], sudo_uyeleri="ayse")
        self.assertEqual(s.returncode, 0)
        self.assertEqual(u, ["usermod -aG wireshark ayse"])

    def test_hata_olursa_damga_yazilmaz(self):
        s, _ = self.calistir(["ayse"], usermod_hata=True)
        self.assertEqual(s.returncode, 1)
        self.assertFalse(self.damga_var)

    def test_kullanici_yoksa_bir_sey_yapmaz(self):
        s, u = self.calistir([])
        self.assertEqual(s.returncode, 0)
        self.assertEqual(u, [])
        self.assertTrue(self.damga_var)


class FirstbootBirimTesti(unittest.TestCase):
    def test_oturumdan_once_siralanir(self):
        birim = oku(FIRSTBOOT_BIRIM)
        satirlar = [s.strip() for s in birim.splitlines()]
        self.assertNotIn("After=multi-user.target", satirlar)
        onceki = [s for s in satirlar if s.startswith("Before=")]
        self.assertTrue(onceki)
        self.assertIn("display-manager.service", onceki[0])
        self.assertIn("systemd-user-sessions.service", onceki[0])
        self.assertIn("ConditionPathExists=!/var/lib/carotos/firstboot.done", satirlar)


# ---------------------------------------------------------------------------
# S-05: saat eslestirme oturumla biter
# ---------------------------------------------------------------------------
SAAT = os.path.join(INC, "usr", "bin", "carotos-saat-eslestir")


@unittest.skipUnless(SH and POSIX and shutil.which("pgrep") and shutil.which("sleep")
                     and os.path.isdir("/proc/self") and os.path.isdir("/usr/share/zoneinfo/Europe"),
                     "Linux, pgrep ve zoneinfo gerekir")
class SaatOturumTesti(unittest.TestCase):
    def test_oturum_sureci_bitince_izleme_biter(self):
        t = Taklit(self)
        t.komut("xfconf-query", "exit 0")
        t.komut("timedatectl", "echo Europe/Istanbul")
        ad = "carotsahteotr%d" % (os.getpid() % 100)          # comm 15 karakteri gecmesin
        sahte = os.path.join(t.bin, ad)
        shutil.copy(shutil.which("sleep"), sahte)
        os.chmod(sahte, 0o755)
        oturum = subprocess.Popen([sahte, "300"])
        self.addCleanup(lambda: (oturum.kill(), oturum.wait()))
        izlenen = os.path.join(t.kok, "localtime")
        open(izlenen, "w").close()
        surec = subprocess.Popen([SH, SAAT, "--izle"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 env=t.ortam(CAROTOS_SAAT_OTURUM=ad, CAROTOS_SAAT_ARALIK="1",
                                             CAROTOS_SAAT_IZLENEN=izlenen, HOME=t.kok,
                                             XDG_CONFIG_HOME=os.path.join(t.kok, "cfg")))
        self.addCleanup(lambda: (surec.poll() is None and surec.kill(), surec.wait()))
        time.sleep(3)
        self.assertIsNone(surec.poll(), "oturum surerken izleme devam etmeli")
        oturum.send_signal(signal.SIGTERM)
        oturum.wait()
        try:
            kod = surec.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.fail("oturum bittikten sonra izleme dongusu cikmadi")
        self.assertEqual(kod, 0)


# ---------------------------------------------------------------------------
# S-07: carotos-dil-hazirla modulu denetlenmis kaynaktan yukler
# ---------------------------------------------------------------------------
DIL_HAZIRLA = os.path.join(INC, "usr", "sbin", "carotos-dil-hazirla")
IYI = 'HAZIRLIK = {"de": {}}\nKAYNAK = "iyi"\n'
KOTU = 'HAZIRLIK = {"de": {}}\nKAYNAK = "kotu"\n'


def betigi_yukle():
    y = importlib.machinery.SourceFileLoader("carotos_dil_hazirla_denetim", DIL_HAZIRLA)
    spec = importlib.util.spec_from_loader("carotos_dil_hazirla_denetim", y)
    m = importlib.util.module_from_spec(spec)
    y.exec_module(m)
    return m


@unittest.skipUnless(POSIX and hasattr(os, "getuid") and hasattr(os, "O_NOFOLLOW"), "POSIX gerekir")
class DilHazirlaModulTesti(unittest.TestCase):
    def setUp(self):
        self.b = betigi_yukle()
        self.taban = tempfile.mkdtemp(prefix="dil-zincir-")
        self.addCleanup(shutil.rmtree, self.taban, True)
        os.chmod(self.taban, 0o755)
        self.dizin = os.path.join(self.taban, "opt", "carotos", "ortak")
        os.makedirs(self.dizin)
        for d in (os.path.join(self.taban, "opt"), os.path.join(self.taban, "opt", "carotos"), self.dizin):
            os.chmod(d, 0o755)
        self.modul = os.path.join(self.dizin, "sistem_dili.py")
        with open(self.modul, "w") as f:
            f.write(IYI)
        os.chmod(self.modul, 0o644)
        self.b.GUVENILIR_UID = os.getuid()
        self.b.ZINCIR_KOKU = self.taban
        self.b.MODUL_DIZINI = self.dizin
        self.b.bildir = lambda metin: None

    def reddedilir(self):
        with self.assertRaises(SystemExit) as c:
            self.b.modulu_yukle()
        self.assertEqual(c.exception.code, 3)

    def test_kaynaktan_yuklenir(self):
        m = self.b.modulu_yukle()
        self.assertEqual(m.KAYNAK, "iyi")
        self.assertEqual(m.__file__, os.path.realpath(self.modul))
        self.assertNotIn(os.path.realpath(self.dizin), [os.path.realpath(p) for p in sys.path if p])

    def test_pycache_bayt_kodu_calistirilmaz(self):
        # kaynagi denetlemeyen (unchecked-hash) bir .pyc: import olsaydi kaynak yerine bu calisirdi
        kotu = os.path.join(self.taban, "kotu.py")
        with open(kotu, "w") as f:
            f.write(KOTU)
        hedef = importlib.util.cache_from_source(self.modul)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        py_compile.compile(kotu, cfile=hedef, doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        self.assertEqual(self.b.modulu_yukle().KAYNAK, "iyi")

    def test_ust_dizin_grup_yazilabilirse_reddedilir(self):
        for d in (self.dizin, os.path.join(self.taban, "opt", "carotos"), self.taban):
            with self.subTest(dizin=d):
                os.chmod(d, 0o775)
                try:
                    self.reddedilir()
                finally:
                    os.chmod(d, 0o755)

    def test_dosya_herkesce_yazilabilirse_reddedilir(self):
        os.chmod(self.modul, 0o666)
        self.reddedilir()

    def test_baska_kullanicinin_dosyasi_reddedilir(self):
        self.b.GUVENILIR_UID = os.getuid() + 1
        self.reddedilir()

    def test_sembolik_bag_reddedilir(self):
        gercek = os.path.join(self.taban, "gercek.py")
        with open(gercek, "w") as f:
            f.write(IYI)
        os.chmod(gercek, 0o644)
        os.remove(self.modul)
        os.symlink(gercek, self.modul)
        self.reddedilir()

    def test_zincir_beklenen_kokte_bitmezse_reddedilir(self):
        self.b.ZINCIR_KOKU = os.path.join(self.taban, "baska")
        os.makedirs(self.b.ZINCIR_KOKU)
        self.reddedilir()

    def test_modul_yoksa_reddedilir(self):
        os.remove(self.modul)
        self.reddedilir()

    def test_import_yok_sabit_ortam(self):
        kaynak = oku(DIL_HAZIRLA)
        self.assertNotIn("import sistem_dili", kaynak)
        self.assertNotIn("sys.path.insert", kaynak)
        self.assertIn("os.O_NOFOLLOW", kaynak)
        self.assertIn("os.environ.update(ORTAM)", kaynak)
        # __pycache__ yazilmaz: modul exec ile yuklenir, ayrica dont_write_bytecode
        self.assertIn("sys.dont_write_bytecode = True", kaynak)
        self.assertIn("restore_signals=False", kaynak)

    def test_okuyucu_gidince_bildir_cokmez(self):
        b = betigi_yukle()
        r, w = os.pipe()
        os.close(r)
        eski = sys.stdout
        sys.stdout = os.fdopen(w, "w")
        try:
            b.bildir("deneme")              # BrokenPipeError yutulur
            b.bildir("ikinci")
        finally:
            try:
                sys.stdout.close()
            except OSError:
                pass
            sys.stdout = eski


class S06GrubOsProberTekSeferTesti(unittest.TestCase):
    """S-06: os-prober acik kalir ama update-grub basina yalniz BIR kez (30_os-prober) calisir."""

    SURE = os.path.join(INC, "etc", "grub.d", "99_carotos_sure")

    def test_sure_betigi_os_prober_komutunu_calistirmaz(self):
        kod = [s for s in oku(self.SURE).splitlines() if not s.lstrip().startswith("#")]
        for s in kod:
            self.assertNotRegex(s, r"(^|[\s;|&(`$])os-prober(\s|$|[;|&)`])", s)
        self.assertNotIn("timeout 90", "\n".join(kod))

    def test_os_prober_acik_kalir_ve_hook_755_yapar(self):
        cfg = oku(os.path.join(INC, "etc", "default", "grub.d", "carotos.cfg"))
        self.assertIn("GRUB_DISABLE_OS_PROBER=false", [s.strip() for s in cfg.splitlines()])
        self.assertIn("chmod 755 /etc/grub.d/99_carotos_sure", hook("9996-carotos-onyukleme.hook.chroot"))
        # dosya adi degismedi: 30_os-prober'dan sonra siralanir
        self.assertGreater("99_carotos_sure", "30_os-prober")

    def test_arac_kopyasi_ayni(self):
        self.assertEqual(oku(self.SURE), oku(os.path.join(KOK, "tools", "grub-test", "grub.d", "99_carotos_sure")))

    @unittest.skipUnless(SH and POSIX, "sh/posix yok")
    def test_mkconfig_taklidi_30_sonra_99_prober_tek_cagri(self):
        """grub-mkconfig gibi: stdout bir dosya, betikler sirayla; os-prober yalniz 30'da (taklit) bir kez."""
        with tempfile.TemporaryDirectory() as d:
            gunluk = os.path.join(d, "g")
            p = os.path.join(d, "os-prober")
            with open(p, "w") as f:
                f.write("#!/bin/sh\necho x >> '%s'\necho '/dev/sda1::Windows:efi'\n" % gunluk)
            os.chmod(p, 0o755)
            otuz = os.path.join(d, "30_os-prober")
            with open(otuz, "w") as f:
                f.write("#!/bin/sh\nos-prober >/dev/null\n"
                        "echo \"menuentry 'Windows' --id 'osprober-chain-1' {\"\necho '}'\n")
            os.chmod(otuz, 0o755)
            yeni = os.path.join(d, "grub.cfg.new")
            env = {"PATH": d + ":/usr/bin:/bin", "GRUB_DISABLE_OS_PROBER": "false"}
            with open(yeni, "w") as f:
                for betik in (otuz, self.SURE):
                    r = subprocess.run([SH, betik], env=env, stdout=f, stderr=subprocess.PIPE, text=True)
                    self.assertEqual(r.returncode, 0, r.stderr)
            with open(yeni) as f:
                cfg = f.read()
            with open(gunluk) as f:
                self.assertEqual(f.read().split(), ["x"])            # os-prober tam bir kez
            self.assertIn("set timeout=30\n", cfg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
