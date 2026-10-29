#!/usr/bin/env python3
"""CarotPot testleri (GTK ve root gerektirmez; ISO'ya girmez).

Kullanim (depo kokunden):  python3 tests/test_carotpot.py

Hizmet testi CarotPot'u gecici portlarda gercekten calistirir ve yerelden
baglanir; SSH kismi yalnizca python3-asyncssh kuruluysa calisir.
"""
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIZIN = os.path.join(KOK, "config/includes.chroot/opt/carotos/carotpot")
INC = os.path.join(KOK, "config/includes.chroot")


def yukle(ad, yol):
    yukleyici = importlib.machinery.SourceFileLoader(ad, yol)
    spec = importlib.util.spec_from_loader(ad, yukleyici)
    mod = importlib.util.module_from_spec(spec)
    yukleyici.exec_module(mod)
    return mod


CP = yukle("carotpot_test", os.path.join(DIZIN, "carotpot.py"))
Y = yukle("carotpot_yonet_test", os.path.join(DIZIN, "carotpot-yonet"))


def bos_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class AdresTesti(unittest.TestCase):
    def test_ozel_adresler(self):
        for ip in ("192.168.1.5", "10.0.0.1", "172.20.1.1", "127.0.0.1", "::1",
                   "fe80::1%eth0", "::ffff:192.168.1.9", "fd00::5"):
            self.assertTrue(CP.ozel_adres_mi(ip), ip)
        for ip in ("8.8.8.8", "203.0.113.5", "2001:4860::8888", "bozuk", ""):
            self.assertFalse(CP.ozel_adres_mi(ip), ip)


class AyarTesti(unittest.TestCase):
    def test_varsayilan_gecerli(self):
        self.assertEqual(CP.ayar_dogrula(CP.VARSAYILAN), CP.VARSAYILAN)
        with open(os.path.join(INC, "etc/carotpot/ayarlar.json")) as fh:
            self.assertEqual(CP.ayar_dogrula(json.load(fh)), CP.VARSAYILAN)

    def test_reddedilenler(self):
        kotu = [
            {"portlar": {"ssh": 22}},                       # ayricalikli port
            {"portlar": {"ssh": 2222, "telnet": 2222}},     # cakisma
            {"portlar": {"bilinmeyen": 4000}},
            {"portlar": {"ssh": "2222"}},
            {"portlar": {"ssh": True}},
            {"portlar": {k: 0 for k in CP.HIZMETLER}},      # hepsi kapali
            {"yoksay": ["192.168.1.1; rm -rf /"]},
            {"bekleme": 1},
            {"webhook": "http://ornek.com/x"},
            {"webhook": "javascript:alert(1)"},
            [],
        ]
        for veri in kotu:
            with self.assertRaises(ValueError, msg=str(veri)):
                CP.ayar_dogrula(veri)

    def test_normallestirme(self):
        a = CP.ayar_dogrula({"portlar": {"ssh": 0, "http": 9000},
                             "yoksay": ["::ffff:192.168.1.9", "192.168.1.9"]})
        self.assertEqual(a["portlar"]["ssh"], 0)
        self.assertEqual(a["portlar"]["telnet"], 0)
        self.assertEqual(a["portlar"]["http"], 9000)
        self.assertEqual(a["yoksay"], ["192.168.1.9"])


class GunlukTesti(unittest.TestCase):
    def test_satir_ve_maske(self):
        olay = {"ts": 1793000000.5, "hizmet": "ssh", "kaynak": "192.168.1.7",
                "kaynak_port": 5555, "hedef_port": 2222, "tur": "giris",
                "ozet": "SSH giris", "kullanici": "pi", "parola": "raspberry"}
        satir = CP.olay_satiri(olay)
        self.assertIn(" CAROTPOT kaynak=192.168.1.7 hizmet=ssh tur=giris | ", satir)
        self.assertNotIn("raspberry", satir)
        geri = CP.olay_satiri_coz(satir)
        self.assertEqual(geri["parola"], "r********")
        self.assertEqual(geri["kaynak"], "192.168.1.7")
        self.assertIsNone(CP.olay_satiri_coz("baska bir satir"))

    @unittest.skipUnless(shutil.which("fail2ban-regex"), "fail2ban-regex yok")
    def test_fail2ban_filtresi(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as fh:
            for i, ip in enumerate(("192.168.1.7", "fd00::5", "10.0.0.9")):
                fh.write(CP.olay_satiri({"ts": time.time() - i, "hizmet": "ftp",
                                         "kaynak": ip, "tur": "tarama",
                                         "ozet": "x"}) + "\n")
            fh.write("alakasiz satir\n")
            yol = fh.name
        self.addCleanup(os.unlink, yol)
        cikti = subprocess.run(
            ["fail2ban-regex", yol,
             os.path.join(INC, "etc/fail2ban/filter.d/carotos-carotpot.conf")],
            capture_output=True, text=True).stdout
        self.assertIn("3 matched", cikti)
        self.assertIn("1 missed", cikti)


class HizmetTesti(unittest.TestCase):
    """CarotPot'u gercekten calistirir ve tuzaklara baglanir."""

    @classmethod
    def setUpClass(cls):
        cls.dizin = tempfile.mkdtemp(prefix="carotpot-test-")
        cls.portlar = {ad: bos_port() for ad in CP.HIZMETLER}
        # rdp portunu baska bir program tutsun: digerleri yine acilmali
        cls.engel = socket.socket()
        cls.engel.bind(("0.0.0.0", cls.portlar["rdp"]))
        cls.engel.listen()
        ayar = os.path.join(cls.dizin, "ayar.json")
        with open(ayar, "w") as fh:
            json.dump({"portlar": cls.portlar}, fh)
        cls.gunluk = os.path.join(cls.dizin, "log", "olaylar.log")
        cls.durum = os.path.join(cls.dizin, "durum.json")
        cls.surec = subprocess.Popen(
            [sys.executable, "-I", os.path.join(DIZIN, "carotpot.py"), "--ayar", ayar,
             "--durum-dizini", os.path.join(cls.dizin, "veri"), "--gunluk", cls.gunluk,
             "--durum-dosyasi", cls.durum, "run"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if os.path.exists(cls.durum):
                break
            time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.surec.terminate()
        cls.surec.wait(10)
        cls.engel.close()
        shutil.rmtree(cls.dizin, ignore_errors=True)

    def olaylar(self):
        time.sleep(0.6)
        with open(self.gunluk, encoding="utf-8") as fh:
            return [CP.olay_satiri_coz(s) for s in fh if " CAROTPOT " in s]

    def baglan(self, ad, veri=b""):
        s = socket.create_connection(("127.0.0.1", self.portlar[ad]), timeout=5)
        if veri:
            s.sendall(veri)
        s.settimeout(1)
        yanit = b""
        try:
            while True:
                parca = s.recv(500)
                if not parca:
                    break
                yanit += parca
                if b"login:" in yanit or b"200 OK" in yanit and b"</html>" in yanit:
                    break
        except OSError:
            pass
        s.close()
        return yanit

    def test_durum_ve_port_cakismasi(self):
        with open(self.durum) as fh:
            d = json.load(fh)
        self.assertIn("rdp", d["hatalar"])
        self.assertNotIn("rdp", d["acik"])
        for ad in ("telnet", "http", "ftp", "vnc", "ssh"):
            self.assertIn(ad, d["acik"])

    def test_tuzaklar_kaydeder_ve_reddeder(self):
        self.assertIn(b"login:", self.baglan("telnet", b"root\r\ngizli123\r\n"))
        yanit = self.baglan("http", b"POST /login HTTP/1.1\r\nContent-Length: 30\r\n\r\n"
                                    b"username=admin&password=parola")
        self.assertIn(b"200 OK", yanit)
        self.assertIn(b"FTP", self.baglan("ftp"))
        self.assertIn(b"530", self.baglan("ftp", b"USER pi\r\nPASS gizli456\r\n"))
        olaylar = self.olaylar()
        turler = {(o["hizmet"], o["tur"]) for o in olaylar}
        self.assertIn(("telnet", "giris"), turler)
        self.assertIn(("http", "giris"), turler)
        self.assertIn(("ftp", "tarama"), turler)
        self.assertIn(("ftp", "giris"), turler)
        with open(self.gunluk, encoding="utf-8") as fh:
            metin = fh.read()
        self.assertNotIn("gizli123", metin)
        self.assertNotIn("gizli456", metin)
        self.assertNotIn("parola", metin.replace('"parola"', ""))
        self.assertEqual(oct(os.stat(self.gunluk).st_mode & 0o777), "0o644")
        veri = os.path.join(self.dizin, "veri")
        self.assertEqual(oct(os.stat(veri).st_mode & 0o777), "0o700")

    def test_mysql_kullanici_adini_kaydeder(self):
        import struct
        s = socket.create_connection(("127.0.0.1", self.portlar["mysql"]), timeout=5)
        bas = s.recv(4)
        karsilama = s.recv(int.from_bytes(bas[:3], "little"))
        self.assertEqual(karsilama[0], 10)                 # protokol 10
        self.assertIn(b"5.7.42", karsilama)               # varsayilan persona
        govde = struct.pack("<IIB", 0x000AA685, 1 << 24, 33) + b"\0" * 23 + b"yonetici\0" + \
            bytes([20]) + b"x" * 20
        s.sendall(struct.pack("<I", len(govde))[:3] + b"\x01" + govde)
        s.settimeout(3)
        yanit = s.recv(300)
        s.close()
        self.assertIn(b"Access denied for user 'yonetici'", yanit)
        olaylar = [o for o in self.olaylar() if o["hizmet"] == "mysql" and o["tur"] == "giris"]
        self.assertEqual(olaylar[-1]["kullanici"], "yonetici")

    def test_redis_parola_ve_komut(self):
        yanit = self.baglan("redis", b"*2\r\n$4\r\nAUTH\r\n$7\r\ngizli78\r\n"
                                     b"CONFIG SET dir /tmp\r\n")
        self.assertIn(b"WRONGPASS", yanit)
        olaylar = [o for o in self.olaylar() if o["hizmet"] == "redis"]
        self.assertIn("giris", {o["tur"] for o in olaylar})
        self.assertTrue(any(o["tur"] == "komut" and "CONFIG" in o["ayrinti"] for o in olaylar))
        with open(self.gunluk, encoding="utf-8") as fh:
            self.assertNotIn("gizli78", fh.read())

    def test_rdp_ve_vnc(self):
        self.baglan("vnc", b"RFB 003.008\n")
        istek = (b"\x03\x00\x00\x2b&\xe0\x00\x00\x00\x00\x00Cookie: mstshash=yonetici\r\n"
                 b"\x01\x00\x08\x00\x03\x00\x00\x00")
        try:      # rdp portu bu testte baska programda; yalniz vnc denetlenir
            self.baglan("rdp", istek)
        except OSError:
            pass
        turler = {(o["hizmet"], o["tur"]) for o in self.olaylar()}
        self.assertIn(("vnc", "baglanti"), turler)

    @unittest.skipUnless(CP.asyncssh, "python3-asyncssh yok")
    def test_ssh_her_zaman_reddeder(self):
        import asyncio
        asyncssh = CP.asyncssh

        async def dene():
            try:
                await asyncssh.connect("127.0.0.1", self.portlar["ssh"], username="pi",
                                       password="raspberry", known_hosts=None)
                return "girdi"
            except asyncssh.PermissionDenied:
                return "reddedildi"
        self.assertEqual(asyncio.run(dene()), "reddedildi")
        self.assertIn(("ssh", "giris"), {(o["hizmet"], o["tur"]) for o in self.olaylar()})


class BildiriciTesti(unittest.TestCase):
    def test_kaynak_basina_bir_bildirim(self):
        dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, dizin, True)
        kayit = os.path.join(dizin, "bildirimler.txt")
        sahte = os.path.join(dizin, "notify-send")
        with open(sahte, "w") as fh:
            fh.write(f"#!/bin/sh\necho \"$@\" >> {kayit}\n")
        os.chmod(sahte, 0o755)
        gunluk = os.path.join(dizin, "olaylar.log")
        open(gunluk, "w").close()
        eski_path = os.environ["PATH"]
        os.environ["PATH"] = dizin + os.pathsep + eski_path
        self.addCleanup(os.environ.__setitem__, "PATH", eski_path)
        sayac = {"n": 0}

        def calisiyor_mu():
            sayac["n"] += 1
            return sayac["n"] < 3          # ucuncu denetimde hizmet durmus olsun
        eski = CP.hizmet_calisiyor_mu
        CP.hizmet_calisiyor_mu = calisiyor_mu
        self.addCleanup(setattr, CP, "hizmet_calisiyor_mu", eski)
        eski_uyku = CP.time.sleep

        def uyku(_sn):
            # Ilk turdan sonra gunluge olaylar yazilir; zaman ilerletilir
            if not os.path.getsize(gunluk):
                with open(gunluk, "a") as fh:
                    for ip in ("192.168.1.7", "192.168.1.7", "192.168.1.8"):
                        fh.write(CP.olay_satiri({"ts": time.time(), "hizmet": "ftp",
                                                 "kaynak": ip, "tur": "tarama",
                                                 "hedef_port": 2121, "ozet": "x"}) + "\n")
            CP.time.time = lambda t=[time.time()]: t.__setitem__(0, t[0] + 20) or t[0]
        CP.time.sleep = uyku
        self.addCleanup(setattr, CP.time, "sleep", eski_uyku)
        gercek_time = time.time
        self.addCleanup(setattr, CP.time, "time", gercek_time)
        a = CP.ayrisici().parse_args(["--ayar", "/yok", "--gunluk", gunluk, "bildir"])
        self.assertEqual(CP.bildir(a), 0)
        with open(kayit) as fh:
            bildirimler = fh.read().splitlines()
        self.assertEqual(len(bildirimler), 2, bildirimler)   # 1.7 bir kez, 1.8 bir kez


class YoneticiTesti(unittest.TestCase):
    AG = {
        ("ip", "-j", "addr"): json.dumps([{"addr_info": [{"local": "192.168.1.20"},
                                                         {"local": "fe80::20"}]}]),
        ("ip", "-4", "-j", "route", "show", "default"): json.dumps([{"gateway": "192.168.1.1"}]),
        ("ip", "-6", "-j", "route", "show", "default"): "[]",
        ("ufw", "status"): "Status: active\n",
    }

    def setUp(self):
        self.komutlar = []
        eski = Y.calistir

        def sahte(komut, zaman=60):
            self.komutlar.append(komut)
            return 0, self.AG.get(tuple(komut), "")
        Y.calistir = sahte
        self.addCleanup(setattr, Y, "calistir", eski)
        self.dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dizin, True)
        for ad, dosya in (("AYAR", "ayarlar.json"), ("ACILAN", "acilan.json"),
                          ("ENGELLILER", "engelliler.json"), ("JAIL", "jail.local")):
            eski_deger = getattr(Y, ad)
            setattr(Y, ad, os.path.join(self.dizin, dosya))
            self.addCleanup(setattr, Y, ad, eski_deger)
        with open(Y.AYAR, "w") as fh:
            json.dump({"yoksay": ["192.168.1.50"]}, fh)

    def cagir(self, *arg):
        cikti = io.StringIO()
        with redirect_stdout(cikti), self.assertRaises(SystemExit):
            Y.main(list(arg)) if os.geteuid() == 0 else self.root_gibi(arg)
        return json.loads(cikti.getvalue())

    def root_gibi(self, arg):
        eski = Y.os.geteuid
        Y.os.geteuid = lambda: 0
        try:
            Y.main(list(arg))
        finally:
            Y.os.geteuid = eski

    def test_kendini_kilitleme_korumasi(self):
        for ip in ("192.168.1.1", "192.168.1.20", "fe80::20", "192.168.1.50"):
            self.assertEqual(self.cagir("engelle", ip)["kod"], "__KORUNAN_ADRES__", ip)
        for ip in ("127.0.0.1", "0.0.0.0", "224.0.0.1", "bozuk", "1.2.3.4; reboot"):
            self.assertEqual(self.cagir("engelle", ip)["kod"], "__GECERSIZ_IP__", ip)
        self.assertFalse([k for k in self.komutlar if k[0] == "ufw" and "deny" in k])

    def test_engelle_ve_kaldir(self):
        sonuc = self.cagir("engelle", "192.168.1.66")
        self.assertEqual(sonuc["kod"], "__TAMAM__")
        self.assertIn(["ufw", "prepend", "deny", "from", "192.168.1.66", "to", "any",
                       "comment", "carotpot-engel"], self.komutlar)
        with open(Y.ENGELLILER) as fh:
            self.assertEqual([e["ip"] for e in json.load(fh)], ["192.168.1.66"])
        self.assertEqual(self.cagir("kaldir", "192.168.1.66")["kod"], "__TAMAM__")
        with open(Y.ENGELLILER) as fh:
            self.assertEqual(json.load(fh), [])

    def test_baslat_portlari_acar_durdur_kapatir(self):
        self.assertEqual(self.cagir("baslat")["kod"], "__TAMAM__")
        izinler = [k for k in self.komutlar if k[:2] == ["ufw", "allow"]]
        self.assertEqual(len(izinler), len(CP.HIZMETLER))
        self.assertIn(["ufw", "allow", "2222/tcp", "comment", "carotpot"], self.komutlar)
        self.assertIn(["systemctl", "start", "carotpot.service"], self.komutlar)
        self.komutlar.clear()
        self.assertEqual(self.cagir("durdur")["kod"], "__TAMAM__")
        self.assertIn(["ufw", "delete", "allow", "2222/tcp"], self.komutlar)
        with open(Y.ACILAN) as fh:
            self.assertEqual(json.load(fh), [])

    def test_otomatik_engelleme(self):
        self.assertEqual(self.cagir("otomatik", "ac")["kod"], "__TAMAM__")
        with open(Y.JAIL) as fh:
            metin = fh.read()
        self.assertIn("enabled = true", metin)
        for ip in ("192.168.1.1", "192.168.1.20", "192.168.1.50", "127.0.0.0/8"):
            self.assertIn(ip, metin)
        self.assertIn(["systemctl", "enable", "--now", "fail2ban.service"], self.komutlar)
        self.assertEqual(self.cagir("otomatik", "kapat")["kod"], "__TAMAM__")
        with open(Y.JAIL) as fh:
            self.assertIn("enabled = false", fh.read())
        self.assertEqual(self.cagir("otomatik", "belki")["kod"], "__GECERSIZ_KOMUT__")

    def test_bilinmeyen_komut(self):
        self.assertEqual(self.cagir("rm", "-rf")["kod"], "__GECERSIZ_KOMUT__")


class PaketlemeTesti(unittest.TestCase):
    def oku(self, yol):
        with open(os.path.join(KOK, yol), encoding="utf-8") as fh:
            return fh.read()

    def test_birim_kisitli_ve_yetkisiz(self):
        birim = self.oku("config/includes.chroot/etc/systemd/system/carotpot.service")
        for satir in ("User=carotpot", "NoNewPrivileges=yes", "CapabilityBoundingSet=\n",
                      "ProtectSystem=strict", "ProtectHome=yes",
                      "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX"):
            self.assertIn(satir, birim)

    def test_hook_hizmeti_etkinlestirmez(self):
        hook = self.oku("config/hooks/live/9992-carotos-carotpot.hook.chroot")
        komutlar = [s for s in hook.splitlines() if s.strip() and not s.lstrip().startswith("#")]
        # Tuzak hizmeti etkinlestirilmez; yalniz acilistaki engel temizligi etkinlesir
        self.assertFalse([s for s in komutlar if "systemctl enable" in s and "carotpot.service" in s])
        self.assertIn("systemctl enable carotpot-engel-temizle.service", komutlar)
        kurulum = [s for s in komutlar if "apt-get install" in s][0]
        self.assertTrue(kurulum.startswith("LC_ALL=C "))
        self.assertIn("--no-install-recommends", kurulum)

    def test_jail_kapali_gelir(self):
        jail = self.oku("config/includes.chroot/etc/fail2ban/jail.d/carotos-carotpot.local")
        self.assertIn("enabled = false", jail)
        self.assertIn("banaction = ufw", jail)


def arayuzu_yukle():
    """Arayuz modulunu GTK olmadan yukler (GTK yalniz pencere acilirken)."""
    return yukle("carotpot_arayuz_test", os.path.join(DIZIN, "carotpot-arayuz.py"))


class ArayuzVeriTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.A = arayuzu_yukle()

    def test_metinler_iki_dilli(self):
        import re
        for anahtar, sozluk in self.A.METIN.items():
            self.assertEqual(set(sozluk), {"tr", "en"}, anahtar)
            self.assertTrue(all(v.strip() for v in sozluk.values()), anahtar)
            self.assertEqual(set(re.findall(r"\{(\w+)\}", sozluk["tr"])),
                             set(re.findall(r"\{(\w+)\}", sozluk["en"])), anahtar)

    def test_olay_aciklamasi_iki_dilli(self):
        for tur in ("giris", "baglanti", "istek", "tarama"):
            o = {"hizmet": "ssh", "tur": tur, "hedef_port": 2222, "kullanici": "pi"}
            tr, en = CP.olay_aciklamasi(o, "tr"), CP.olay_aciklamasi(o, "en")
            self.assertTrue(tr and en and tr != en, tur)
        self.assertIn("pi", CP.olay_aciklamasi({"hizmet": "ssh", "tur": "giris",
                                                "kullanici": "pi"}, "en"))

    def test_olaylar_ve_kaynaklar(self):
        dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, dizin, True)
        gunluk = os.path.join(dizin, "olaylar.log")
        simdi = time.time()
        with open(gunluk + ".1", "w") as fh:     # donmus eski dosya
            fh.write(CP.olay_satiri({"ts": simdi - 90000, "hizmet": "ftp",
                                     "kaynak": "192.168.1.9", "tur": "tarama"}) + "\n")
        with open(gunluk, "w") as fh:
            for ip, tur in (("192.168.1.7", "giris"), ("192.168.1.7", "tarama"),
                            ("192.168.1.8", "istek")):
                fh.write(CP.olay_satiri({"ts": simdi - 60, "hizmet": "ssh",
                                         "kaynak": ip, "tur": tur}) + "\n")
            fh.write("bozuk satir\n")
        olaylar = self.A.olaylari_oku(gunluk)
        self.assertEqual(len(olaylar), 4)
        ozet = self.A.kaynak_ozeti(olaylar, simdi)
        self.assertEqual([k["kaynak"] for k in ozet], ["192.168.1.7", "192.168.1.8"])
        self.assertEqual((ozet[0]["sayi"], ozet[0]["giris"]), (2, 1))
        self.assertEqual(self.A.olaylari_oku(os.path.join(dizin, "yok")), [])

    def test_otomatik_ve_engelliler(self):
        dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, dizin, True)
        jail = os.path.join(dizin, "jail.local")
        with open(jail, "w") as fh:
            fh.write(Y.jail_metni(True, {"192.168.1.1"}))
        self.assertTrue(self.A.otomatik_acik_mi(jail))
        with open(jail, "w") as fh:
            fh.write(Y.jail_metni(False, {"192.168.1.1"}))
        self.assertFalse(self.A.otomatik_acik_mi(jail))
        self.assertFalse(self.A.otomatik_acik_mi(os.path.join(KOK, "config/includes.chroot",
                                                              "etc/fail2ban/jail.d/carotos-carotpot.local")))
        eng = os.path.join(dizin, "e.json")
        with open(eng, "w") as fh:
            json.dump([{"ip": "192.168.1.66", "tarih": 1}], fh)
        self.assertEqual(self.A.engelli_ipler(eng), {"192.168.1.66"})
        self.assertEqual(self.A.engelli_ipler(os.path.join(dizin, "yok")), set())

    def test_yardimci_komutu_sabit(self):
        cagri = {}

        def sahte_run(cmd, **kw):
            cagri["cmd"], cagri["input"] = cmd, kw.get("input")
            return subprocess.CompletedProcess(cmd, 0, '{"kod": "__TAMAM__"}\n', "")
        eski = self.A.subprocess.run
        self.A.subprocess.run = sahte_run
        try:
            kod, _ = self.A.yardimci_cagir("ayar", girdi='{"bekleme": 60}')
        finally:
            self.A.subprocess.run = eski
        self.assertEqual(kod, "__TAMAM__")
        self.assertEqual(cagri["cmd"][0], "pkexec")
        self.assertTrue(cagri["cmd"][1].endswith("carotpot-yonet"))
        self.assertEqual(cagri["cmd"][2:], ["ayar"])
        self.assertEqual(cagri["input"], '{"bekleme": 60}')

    def test_masaustu_ve_simge(self):
        with open(os.path.join(INC, "usr/share/applications/carotos-carotpot.desktop")) as fh:
            icerik = fh.read()
        self.assertIn("Exec=/opt/carotos/carotpot/carotpot-arayuz.py\n", icerik)
        self.assertIn("Icon=carotpot\n", icerik)
        import struct
        for boyut in (16, 22, 24, 32, 48, 64, 128, 256):
            yol = os.path.join(INC, f"usr/share/icons/hicolor/{boyut}x{boyut}/apps/carotpot.png")
            with open(yol, "rb") as fh:
                bas = fh.read(24)
            self.assertEqual(struct.unpack(">II", bas[16:24]), (boyut, boyut), yol)


if __name__ == "__main__":
    unittest.main(verbosity=1)
