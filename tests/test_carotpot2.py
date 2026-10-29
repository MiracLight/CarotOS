#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotPot 2 testleri: tuzak modulleri ve personalar, kanarya dosyalar,
veri katmani (profil, risk, rapor), sureli engel, ag bilgisi, ortak tema
ve (ekran varsa) arayuzun butun sayfalari."""

import asyncio
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from contextlib import redirect_stdout

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot")
DIZIN = os.path.join(INC, "opt/carotos/carotpot")
ORTAK = os.path.join(INC, "opt/carotos/ortak")
for _y in (ORTAK, DIZIN):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import ag  # noqa: E402
import carotpot as CP  # noqa: E402
import kanarya  # noqa: E402
import tuzaklar  # noqa: E402
from arayuz import veri as V  # noqa: E402
from arayuz.metinler import M  # noqa: E402

from importlib.machinery import SourceFileLoader  # noqa: E402
import importlib.util  # noqa: E402

_y = SourceFileLoader("carotpot_yonet2", os.path.join(DIZIN, "carotpot-yonet"))
_s = importlib.util.spec_from_loader("carotpot_yonet2", _y)
Y = importlib.util.module_from_spec(_s)
_y.exec_module(Y)


def olay(ts, ip, hz, tur, kul=None, par=None, ayr=None):
    return {"ts": ts, "hizmet": hz, "kaynak": ip, "tur": tur, "kullanici": kul,
            "parola": par, "ayrinti": ayr}


class EvDizini(unittest.TestCase):
    """Her test icin gecici HOME / XDG dizinleri."""

    def setUp(self):
        self.ev = tempfile.mkdtemp(prefix="cp2-ev-")
        self.addCleanup(shutil.rmtree, self.ev, True)
        self._eski = {k: os.environ.get(k) for k in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")}
        os.environ["HOME"] = self.ev
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.ev, ".config")
        os.environ["XDG_DATA_HOME"] = os.path.join(self.ev, ".local/share")

        def geri():
            for k, v in self._eski.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.addCleanup(geri)


# ---------------------------------------------------------------------------
class TuzakModulTesti(unittest.TestCase):
    def test_moduller_eksiksiz(self):
        portlar = set()
        for ad in tuzaklar.SIRA:
            m = tuzaklar.MODULLER[ad]
            self.assertEqual(m.AD, ad)
            self.assertTrue(m.BASLIK)
            self.assertEqual(set(m.ACIKLAMA), {"tr", "en"}, ad)
            self.assertTrue(m.PERSONALAR, ad)
            for p, bilgi in m.PERSONALAR.items():
                self.assertTrue(bilgi["tr"] and bilgi["en"], (ad, p))
            self.assertTrue(hasattr(m, "isle") or hasattr(m, "baslat"), ad)
            self.assertTrue(1024 <= m.VARSAYILAN_PORT <= 65535, ad)
            portlar.add(m.VARSAYILAN_PORT)
        self.assertEqual(len(portlar), len(tuzaklar.SIRA))   # varsayilan portlar cakismaz

    def test_persona_dogrulama(self):
        a = CP.ayar_dogrula({"portlar": {"ssh": 2222}, "personalar": {"ssh": "raspi"}})
        self.assertEqual(a["personalar"]["ssh"], "raspi")
        self.assertEqual(a["personalar"]["http"], tuzaklar.varsayilan_persona("http"))
        for kotu in ({"personalar": {"ssh": "windows"}}, {"personalar": {"yok": "x"}},
                     {"personalar": []}):
            with self.assertRaises(ValueError, msg=str(kotu)):
                CP.ayar_dogrula(dict(kotu, portlar={"ssh": 2222}))

    def test_eski_ayar_dosyasi_okunur(self):
        # CarotPot 1 ayar dosyasi: persona ve yeni tuzaklar yok
        eski = {"portlar": {"ssh": 2222, "telnet": 2323, "http": 8080, "ftp": 2121,
                            "vnc": 5900, "rdp": 3390}, "yoksay": [], "bekleme": 300,
                "sakla_gun": 30, "dakikada_olay": 120, "webhook": ""}
        a = CP.ayar_dogrula(eski)
        self.assertEqual(a["portlar"]["mysql"], 0)
        self.assertEqual(a["portlar"]["redis"], 0)
        self.assertEqual(set(a["personalar"]), set(tuzaklar.SIRA))

    def test_protokol_yardimcilari(self):
        from tuzaklar import mysql, redis, telnet
        self.assertEqual(telnet.satir_coz(b"\xff\xfb\x01root\r\n"), "root")
        self.assertIsNone(telnet.satir_coz(b""))
        govde = b"\0" * 32 + b"pi\0" + b"x" * 10
        self.assertEqual(mysql.kullanici_coz(govde), "pi")
        self.assertIsNone(mysql.kullanici_coz(b"kisa"))
        paket = mysql.karsilama(b"8.0.36", 9)
        self.assertEqual(int.from_bytes(paket[:3], "little"), len(paket) - 4)

        async def oku(veri):
            r = asyncio.StreamReader()
            r.feed_data(veri)
            r.feed_eof()
            return [await redis.komut_oku(r, 1), await redis.komut_oku(r, 1)]
        self.assertEqual(asyncio.run(oku(b"*2\r\n$4\r\nAUTH\r\n$3\r\nabc\r\nPING\r\n")),
                         [["AUTH", "abc"], ["PING"]])


# ---------------------------------------------------------------------------
class KanaryaTesti(EvDizini):
    def test_sablonlar_gecerli_dosya_uretir(self):
        belge = os.path.join(self.ev, "Belgeler")
        os.makedirs(belge)
        for sablon in kanarya.SABLONLAR:
            k = kanarya.kanarya_olustur(sablon, belge)
            self.assertTrue(os.path.isfile(k["yol"]), sablon)
            self.assertLess(os.path.getmtime(k["yol"]), time.time() - 10 * 86400, sablon)
        yol = lambda ad: os.path.join(belge, ad)  # noqa: E731
        with zipfile.ZipFile(yol("sifreler.xlsx")) as z:
            self.assertIn("xl/worksheets/sheet1.xml", z.namelist())
            self.assertIn(b"<sheetData>", z.read("xl/worksheets/sheet1.xml"))
        with open(yol("hesap-ozeti.pdf"), "rb") as fh:
            pdf = fh.read()
        self.assertTrue(pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF"))
        self.assertIn(b"startxref", pdf)
        self.assertEqual(oct(os.stat(yol("id_rsa_yedek")).st_mode & 0o777), "0o600")
        with open(yol(".env")) as fh:
            self.assertIn("DB_PASSWORD=", fh.read())
        self.assertEqual(len(kanarya.liste_oku()), len(kanarya.SABLONLAR))
        with self.assertRaises(FileExistsError):
            kanarya.kanarya_olustur("parola", belge)
        with self.assertRaises(ValueError):
            kanarya.kanarya_olustur("parola", belge, "..")

    def test_izleyici_acilma_ve_kaldirma(self):
        izl0 = kanarya.Izleyici()
        if not izl0.calisiyor:
            self.skipTest("inotify yok")
        izl0.kapat()
        k = kanarya.kanarya_olustur("env", self.ev, "gizli.env")
        izl = kanarya.Izleyici()
        self.addCleanup(izl.kapat)
        self.assertTrue(izl.kanarya_var_mi())
        # baska bir surec dosyayi acip bir sure tutar
        p = subprocess.Popen([sys.executable, "-c",
                              f"f=open({k['yol']!r}); f.read(); import time; time.sleep(1.5)"])
        self.addCleanup(p.wait)
        olaylar = []
        for _ in range(10):
            olaylar += izl.bekle(0.3)
            if olaylar:
                break
        self.assertTrue(olaylar)
        self.assertEqual(olaylar[0]["tur"], "acildi")
        self.assertIn(str(p.pid), olaylar[0]["surec"])
        self.assertEqual(kanarya.durumlar()[0]["tetik"]["tur"], "acildi")
        # kullanici kaldirinca silme tetiklenme sayilmaz
        kanarya.kanarya_kaldir(k["yol"])
        self.assertFalse(os.path.exists(k["yol"]))
        self.assertEqual(izl.bekle(0.5), [])
        self.assertEqual(len(kanarya.olaylari_oku()), 1)

    def test_onizleme_surecleri_yok_sayilir(self):
        izl0 = kanarya.Izleyici()
        if not izl0.calisiyor:
            self.skipTest("inotify yok")
        izl0.kapat()
        k = kanarya.kanarya_olustur("yerimi", self.ev)
        izl = kanarya.Izleyici()
        self.addCleanup(izl.kapat)
        eski = kanarya.surec_bul
        kanarya.surec_bul = lambda yol: [("tumblerd", 999)]
        self.addCleanup(setattr, kanarya, "surec_bul", eski)
        with open(k["yol"]) as fh:
            fh.read()
        self.assertEqual(izl.bekle(0.5), [])

    def test_bildirim_metni_iki_dilli(self):
        o = {"yol": "/x/sifreler.xlsx", "tur": "acildi", "surec": "python3 (5)"}
        tr, en = kanarya.bildirim_metni(o, "tr"), kanarya.bildirim_metni(o, "en")
        self.assertIn("açıldı", tr[1])
        self.assertIn("opened", en[1])
        self.assertIn("python3", en[1])


# ---------------------------------------------------------------------------
class VeriTesti(EvDizini):
    def test_olay_akisi_artimli_ve_dondurme(self):
        g = os.path.join(self.ev, "olaylar.log")
        with open(g + ".1", "w") as fh:
            fh.write(CP.olay_satiri(olay(time.time() - 500, "192.168.1.9", "ftp", "tarama")) + "\n")
        with open(g, "w") as fh:
            fh.write(CP.olay_satiri(olay(time.time() - 60, "192.168.1.7", "ssh", "giris")) + "\n")
            fh.write("yarim satir")
        a = V.OlayAkisi(g)
        self.assertTrue(a.tazele())
        self.assertEqual(len(a.olaylar), 2)
        self.assertFalse(a.tazele())
        with open(g, "a") as fh:      # yarim satir tamamlanir, yenisi eklenir
            fh.write("\n" + CP.olay_satiri(olay(time.time(), "192.168.1.8", "http", "istek")) + "\n")
        self.assertTrue(a.tazele())
        self.assertEqual([o["kaynak"] for o in a.olaylar][-1], "192.168.1.8")
        os.replace(g, g + ".1")        # dondurme: yeni dosya, yeni inode
        with open(g, "w") as fh:
            fh.write(CP.olay_satiri(olay(time.time(), "192.168.1.5", "vnc", "baglanti")) + "\n")
        self.assertTrue(a.tazele())
        self.assertEqual(len(a.olaylar), 3)

    def test_davranis_ve_risk(self):
        t = time.time() - 600
        olaylar = [olay(t + i, "192.168.1.44", "ssh", "giris", u, "x") for i, u in
                   enumerate(["root", "pi", "admin", "user"] * 3)]
        olaylar += [olay(t + 50 + i, "192.168.1.103", "telnet", "giris", u, "y")
                    for i, u in enumerate(["root", "admin", "support"])]
        olaylar += [olay(t + 90, "192.168.1.71", "http", "istek", ayr="/.env UA=x"),
                    olay(t + 91, "192.168.1.71", "http", "istek", ayr="/wp-login.php UA=x")]
        olaylar += [olay(t + 99, "192.168.1.88", "redis", "komut", ayr="CONFIG SET dir /tmp")]
        olaylar += [olay(t + 99, "192.168.1.12", hz, "tarama") for hz in ("ftp", "vnc", "rdp")]
        oz = {k["kaynak"]: k for k in V.kaynak_ozeti(olaylar)}
        self.assertIn("kaba_kuvvet", oz["192.168.1.44"]["davranis"])
        self.assertIn("iot_botu", oz["192.168.1.103"]["davranis"])
        self.assertNotIn("iot_botu", oz["192.168.1.44"]["davranis"])   # telnet degil
        self.assertIn("web_tarama", oz["192.168.1.71"]["davranis"])
        self.assertIn("redis_istismar", oz["192.168.1.88"]["davranis"])
        self.assertIn("port_tarama", oz["192.168.1.12"]["davranis"])
        for k in oz.values():
            self.assertTrue(1 <= k["risk"] <= 100)
        self.assertEqual(V.seviye(oz["192.168.1.44"]["risk"])[0], "yuksek")
        self.assertEqual(V.seviye(10)[0], "dusuk")
        sirali = V.kaynak_ozeti(olaylar)
        self.assertEqual(sirali[0]["kaynak"], "192.168.1.44")

    def test_seriler(self):
        simdi = time.time()
        olaylar = [olay(simdi - 30, "192.168.1.1", "ssh", "giris"),
                   olay(simdi - 3 * 3600, "192.168.1.1", "ssh", "giris")]
        sayilar, etiketler = V.saatlik(olaylar, simdi)
        self.assertEqual(len(sayilar), 24)
        self.assertEqual(sayilar[-1], 1)
        self.assertEqual(sum(sayilar), 2)
        self.assertEqual(len(etiketler), 24)
        g, e = V.gunluk_seri(olaylar, simdi - 7 * 86400, simdi)
        self.assertEqual(sum(g), 2)
        self.assertEqual(len(g), len(e))

    def test_rapor_html_ve_csv_parola_icermez(self):
        simdi = time.time()
        olaylar = [olay(simdi - 100, "192.168.1.44", "ssh", "giris", "pi", "r********"),
                   olay(simdi - 90000, "192.168.1.50", "ftp", "tarama")]
        oz = V.donem_ozeti(olaylar, simdi - 86400, simdi + 1)
        self.assertEqual((oz["toplam"], oz["onceki_toplam"], oz["yeni_kaynak"]), (1, 1, 1))

        def t(k, **kw):
            return M[k]["tr"].format(**kw) if kw else M[k]["tr"]
        sayfa = V.rapor_html(oz, t, "tr", lambda ip: "pi-lab", ["<script>x</script>"])
        self.assertIn("<!doctype html>", sayfa)
        self.assertIn("192.168.1.44", sayfa)
        self.assertNotIn("<script>x", sayfa)              # kacirildi
        self.assertNotIn("r********", sayfa)              # parolalar rapora girmez
        self.assertIn("<svg", sayfa)
        csv_ = V.rapor_csv(olaylar, simdi - 86400, simdi + 1)
        self.assertTrue(csv_.startswith("zaman,kaynak,hizmet,tur"))
        self.assertEqual(len(csv_.strip().splitlines()), 2)

    def test_notlar(self):
        V.not_yaz("192.168.1.9", "  ogretmen yazicisi  ")
        self.assertEqual(V.notlar()["192.168.1.9"], "ogretmen yazicisi")
        V.not_yaz("192.168.1.9", "")
        self.assertNotIn("192.168.1.9", V.notlar())


# ---------------------------------------------------------------------------
class SureliEngelTesti(unittest.TestCase):
    AG = {("ip", "-j", "addr"): json.dumps([{"addr_info": [{"local": "192.168.1.20"}]}]),
          ("ip", "-4", "-j", "route", "show", "default"): json.dumps([{"gateway": "192.168.1.1"}]),
          ("ip", "-6", "-j", "route", "show", "default"): "[]",
          ("ufw", "status"): "Status: active\n"}

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
        eski_uid = Y.os.geteuid
        Y.os.geteuid = lambda: 0
        self.addCleanup(setattr, Y.os, "geteuid", eski_uid)

    def cagir(self, *arg):
        cikti = io.StringIO()
        with redirect_stdout(cikti), self.assertRaises(SystemExit):
            Y.main(list(arg))
        return json.loads(cikti.getvalue())

    def test_sureli_engel_ve_temizlik(self):
        sonuc = self.cagir("engelle", "192.168.1.66", "60")
        self.assertEqual(sonuc["kod"], "__TAMAM__")
        self.assertAlmostEqual(sonuc["bitis"], time.time() + 3600, delta=5)
        zamanlayici = [k for k in self.komutlar if k[0] == "systemd-run"]
        self.assertEqual(len(zamanlayici), 1)
        self.assertIn("--on-active=3605s", zamanlayici[0])
        self.assertEqual(zamanlayici[0][-1], "sure-denetle")
        for kotu in ("0", "-5", "abc", "99999999"):
            self.assertEqual(self.cagir("engelle", "192.168.1.67", kotu)["kod"],
                             "__GECERSIZ_SURE__", kotu)
        # suresi dolmus bir engel ve suresiz bir engel
        with open(Y.ENGELLILER, "w") as fh:
            json.dump([{"ip": "192.168.1.66", "tarih": 1, "bitis": time.time() - 5},
                       {"ip": "192.168.1.70", "tarih": 1}], fh)
        self.komutlar.clear()
        sonuc = self.cagir("sure-denetle")
        self.assertEqual(sonuc["kaldirilan"], ["192.168.1.66"])
        self.assertIn(["ufw", "delete", "deny", "from", "192.168.1.66", "to", "any"], self.komutlar)
        with open(Y.ENGELLILER) as fh:
            self.assertEqual([e["ip"] for e in json.load(fh)], ["192.168.1.70"])

    def test_parolalar(self):
        veri = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, veri, True)
        depo = CP.Depo(os.path.join(veri, "olaylar.db"))
        for par in ("raspberry", "raspberry", "123456"):
            depo.ekle({"ts": 1, "hizmet": "ssh", "kaynak": "192.168.1.44", "tur": "giris",
                       "kullanici": "pi", "parola": par})
        depo.db.close()
        eski = CP.VERI_DIZINI
        Y.CP.VERI_DIZINI = veri
        self.addCleanup(setattr, Y.CP, "VERI_DIZINI", eski)
        sonuc = self.cagir("parolalar", "192.168.1.44")
        self.assertEqual(sonuc["parolalar"][0], {"hizmet": "ssh", "kullanici": "pi",
                                                 "parola": "raspberry", "sayi": 2})
        self.assertEqual(self.cagir("parolalar", "x; rm")["kod"], "__GECERSIZ_IP__")
        self.assertEqual(self.cagir("parolalar", "192.168.1.99")["parolalar"], [])
        _ = sqlite3


# ---------------------------------------------------------------------------
class AgTesti(unittest.TestCase):
    def test_mac_ve_uretici(self):
        self.assertEqual(ag.mac_normal("B8-27-EB-12-34-56"), "b8:27:eb:12:34:56")
        self.assertIsNone(ag.mac_normal("bozuk"))
        self.assertTrue(ag.rastgele_mac_mi("da:11:22:33:44:55"))
        self.assertFalse(ag.rastgele_mac_mi("b8:27:eb:12:34:56"))
        self.assertEqual(ag.uretici("da:11:22:33:44:55"), "rastgele")
        self.assertIn("Raspberry", ag.uretici("b8:27:eb:00:00:01"))

    def test_komsular_ve_cihazlar(self):
        eski = (ag._komut, ag.ag_gecidi, ag.kendi_adresler)
        self.addCleanup(lambda: setattr(ag, "_komut", eski[0]) or setattr(ag, "ag_gecidi", eski[1])
                        or setattr(ag, "kendi_adresler", eski[2]))
        ag._komut = lambda komut: json.dumps([
            {"dst": "192.168.1.1", "lladdr": "50:c7:bf:01:02:03", "state": ["REACHABLE"]},
            {"dst": "192.168.1.44", "lladdr": "b8:27:eb:12:34:56", "state": ["STALE"]},
            {"dst": "192.168.1.99", "state": ["FAILED"]},
            {"dst": "192.168.1.20", "lladdr": "aa:bb:cc:dd:ee:ff", "state": ["REACHABLE"]}])
        ag.ag_gecidi = lambda: "192.168.1.1"
        ag.kendi_adresler = lambda: [("192.168.1.20", 24)]
        c = {x["ip"]: x for x in ag.cihazlar({"192.168.1.44": {}, "192.168.1.77": {}})}
        self.assertEqual(set(c), {"192.168.1.1", "192.168.1.44", "192.168.1.77"})
        self.assertTrue(c["192.168.1.1"]["gecit"])
        self.assertTrue(c["192.168.1.44"]["tuzak"])
        self.assertIn("Raspberry", c["192.168.1.44"]["uretici"])
        self.assertEqual(c["192.168.1.77"]["mac"], "")


# ---------------------------------------------------------------------------
class MetinTesti(unittest.TestCase):
    def test_iki_dilli_ve_yer_tutucular(self):
        for anahtar, sozluk in M.items():
            self.assertEqual(set(sozluk), {"tr", "en"}, anahtar)
            self.assertTrue(all(v.strip() for v in sozluk.values()), anahtar)
            self.assertEqual(set(re.findall(r"\{(\w+)\}", sozluk["tr"])),
                             set(re.findall(r"\{(\w+)\}", sozluk["en"])), anahtar)

    def test_koddaki_anahtarlar_tanimli(self):
        eksik = set()
        for kok, _d, dosyalar in os.walk(os.path.join(DIZIN, "arayuz")):
            for ad in dosyalar:
                if ad.endswith(".py"):
                    with open(os.path.join(kok, ad), encoding="utf-8") as fh:
                        icerik = fh.read()
                    for a in re.findall(r"""\bt\(\s*["']([a-z0-9_]+)["']""", icerik):
                        if a not in M and not a.endswith("_"):
                            eksik.add(a)
        self.assertFalse(eksik)
        for d in ("kaba_kuvvet", "giris_denemesi", "anahtar_denemesi", "port_tarama", "iot_botu",
                  "web_tarama", "redis_istismar", "veritabani"):
            self.assertIn("d_" + d, M)
        for tur in ("acildi", "degisti", "silindi", "tasindi"):
            self.assertIn("kt_" + tur, M)


# ---------------------------------------------------------------------------
class TemaTesti(unittest.TestCase):
    def test_palet_ve_css(self):
        try:
            import tema
        except (ImportError, ValueError) as h:
            self.skipTest(f"GTK yok: {h}")
        for gorunum in ("dark", "light"):
            for vurgu in tema.VURGULAR:
                p = tema.palet(gorunum, vurgu)
                for anahtar in ("zemin", "kart", "yazi", "vurgu", "vurgu_yazi", "kirmizi"):
                    self.assertRegex(p[anahtar], r"^#[0-9a-f]{6}$", (gorunum, vurgu, anahtar))
                css = tema.css(p)
                self.assertEqual(css.count("{"), css.count("}"))
        self.assertEqual(tema.palet("bilinmeyen", "#123456")["vurgu"], "#123456")


@unittest.skipUnless(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"),
                     "ekran yok (xvfb-run ile calistirin)")
class ArayuzDumanTesti(EvDizini):
    """Pencereyi sahte verilerle acar; butun sayfalari iki dilde ve iki
    gorunumde gezer. Yakalanmayan istisna olmamali."""

    def test_butun_sayfalar(self):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
            from arayuz import pencere as PW
        except (ImportError, ValueError) as h:
            self.skipTest(f"GTK yok: {h}")
        hatalar = []
        eski_kanca = sys.excepthook
        sys.excepthook = lambda *a: hatalar.append(a)
        self.addCleanup(setattr, sys, "excepthook", eski_kanca)
        g = os.path.join(self.ev, "olaylar.log")
        simdi = time.time()
        with open(g, "w") as fh:
            for i in range(40):
                fh.write(CP.olay_satiri(dict(olay(simdi - i * 900, f"192.168.1.{40 + i % 4}",
                                                  tuzaklar.SIRA[i % 8], ["giris", "tarama", "istek"][i % 3],
                                                  "root", "x****"), hedef_port=2222)) + "\n")
        eskiler = {}
        for ad, deger in (("hizmet_acik_mi", lambda: True),
                          ("hizmet_durumu", lambda yol=None: {"baslangic": simdi - 60, "acik": {"ssh": 2222},
                                                              "hatalar": {"rdp": "x"}}),
                          ("engeller", lambda yol=None: [{"ip": "192.168.1.40", "tarih": simdi,
                                                          "bitis": simdi + 600}]),
                          ("ufw_durumu", lambda: True)):
            eskiler[ad] = getattr(V, ad)
            setattr(V, ad, deger)
        for ad, deger in eskiler.items():
            self.addCleanup(setattr, V, ad, deger)
        eski_akis = V.OlayAkisi.__init__.__defaults__
        V.OlayAkisi.__init__.__defaults__ = (g, 60000)
        self.addCleanup(setattr, V.OlayAkisi.__init__, "__defaults__", eski_akis)
        eski_ag = (ag.komsular, ag.ad_coz, ag.kendi_adresler, ag.ag_gecidi)
        ag.komsular = lambda: [{"ip": "192.168.1.40", "mac": "b8:27:eb:00:00:01", "durum": "x"}]
        ag.ad_coz = lambda ip, zaman=1.5: ""
        ag.kendi_adresler = lambda: [("192.168.1.2", 24)]
        ag.ag_gecidi = lambda: "192.168.1.1"
        self.addCleanup(lambda: (setattr(ag, "komsular", eski_ag[0]), setattr(ag, "ad_coz", eski_ag[1]),
                                 setattr(ag, "kendi_adresler", eski_ag[2]),
                                 setattr(ag, "ag_gecidi", eski_ag[3])))
        kanarya.kanarya_olustur("env", self.ev)

        def pompala(sn):
            t = time.time()
            while time.time() - t < sn:
                while Gtk.events_pending():
                    Gtk.main_iteration()
                time.sleep(0.01)
        w = PW.Pencere(None)
        try:
            for dil, gorunum in (("tr", "dark"), ("en", "light")):
                w.dil_kutu.set_active_id(dil)
                if w.ui["theme"] != gorunum:
                    w.tema_degistir(gorunum)
                for anahtar in ("pano", "saldirgan", "tuzak", "kanarya", "engel", "rapor", "ag", "ayar"):
                    w.kabuk.sec(anahtar)
                    pompala(0.25)
                    w.tik()
                    pompala(0.1)
            # tuzak taslagi: bir tuzagi kapatinca degisiklik cubugu gorunur
            w.kabuk.sec("tuzak")
            s = w.sayfalar["tuzak"]
            s.kartlar["ssh"]["anahtar"].set_active(False)
            self.assertTrue(s.kirli())
            self.assertTrue(s.degisiklik.get_visible())
            s.geri_al_tik()
            self.assertFalse(s.kirli())
            w.gezin("saldirgan", ip="192.168.1.41")
            pompala(0.2)
            self.assertEqual(w.sayfalar["saldirgan"].secili, "192.168.1.41")
        finally:
            w.destroy()
        self.assertFalse(hatalar, hatalar)


if __name__ == "__main__":
    unittest.main()
