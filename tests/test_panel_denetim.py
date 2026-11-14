#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Güvenlik Paneli + etik koruma denetimi (docs/denetim/panel-ortak.md, G- bulguları)
için kalıcı testler. Sınıf adları bulgu numarasını taşır.

Mantık testleri GTK gerektirmez (panel kaynağından yalnızca ilgili işlevler AST ile
çıkarılır). Arayüz testleri GTK ve ekran ister; yoksa atlanır. Hiçbir test root, ağ
ya da gerçek nmap/tcpdump/pkexec gerektirmez: yetkili çağrılar sahte işlevlerle
yakalanır, hiçbir araç gerçek hedefe karşı çalıştırılmaz.

Çalıştırma:  xvfb-run -a python3 tests/test_panel_denetim.py
"""
import ast
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
PANEL = os.path.join(INC, "security-panel", "carotos-security-panel.py")
sys.path.insert(0, os.path.join(INC, "ortak"))

import etik_koruma as E  # noqa: E402

EKRAN = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


# ---------------------------------------------------------------------------
# GTK'siz yardimcilar: panel kaynagindan secilen ust duzey dugumleri calistirir
# ---------------------------------------------------------------------------

def panel_kaynagi():
    with open(PANEL, encoding="utf-8") as f:
        return f.read()


def _agac():
    return ast.parse(panel_kaynagi())


def panel_parcalari(*adlar, **ad_alani):
    """Panelden adi verilen islev/atamalari (TOOLS icin ilk liste atamasi) bir ad
    alaninda calistirir ve ad alanini dondurur."""
    secilen = []
    for dugum in _agac().body:
        if isinstance(dugum, ast.FunctionDef) and dugum.name in adlar:
            secilen.append(dugum)
        elif isinstance(dugum, ast.Assign):
            hedefler = {getattr(t, "id", "") for t in dugum.targets}
            if hedefler & set(adlar):
                if "TOOLS" in hedefler and not isinstance(dugum.value, ast.List):
                    continue                    # TOOLS = dil.zenginlestir(TOOLS)
                secilen.append(dugum)
    alan = {"shlex": shlex, "re": re, "os": os, "json": json}
    alan.update(ad_alani)
    exec(compile(ast.Module(body=secilen, type_ignores=[]), PANEL, "exec"), alan)
    return alan


MANTIK = panel_parcalari(
    "_v", "root_icin_guvenli_mi", "_SABLON_ON", "root_argv_guvenli_mi",
    "_SQLMAP_HEDEF_KISA", "_SQLMAP_ARGSIZ_KISA", "_SQLMAP_HEDEF_UZUN",
    "hedef_degistiren_secenek", "sayi_gecerli_mi", "guvenlik_duvari_durumu",
    "CIKTI_SATIR_SINIRI", "TOOLS")
ARAC = {t["name"]: t for t in MANTIK["TOOLS"]}


def kur(arac, **degerler):
    return [c for c in ARAC[arac]["build"](degerler) if c != ""]


def degerlendir(metin, onayli=(), kendi_ad="carotos"):
    return E.degerlendir(metin, onayli, kendi_ad)


# ---------------------------------------------------------------------------
# G-01  Root arguman denetimi araca giden argv uzerinde
# ---------------------------------------------------------------------------

class G01RootArgumanDenetimi(unittest.TestCase):
    RAPOR_FILTRESI = '"-Z" root "-w" /tmp/a "-C" 1 "-z" /home/u/x.sh'

    def setUp(self):
        self.guvenli = MANTIK["root_icin_guvenli_mi"]
        self.argv_guvenli = MANTIK["root_argv_guvenli_mi"]

    def tcpdump(self, **ek):
        d = {"iface": "eth0", "count": "50", "filter": ""}
        d.update(ek)
        return d

    def test_rapordaki_tirnakli_filtre_reddedilir(self):
        self.assertFalse(self.guvenli(self.tcpdump(filter=self.RAPOR_FILTRESI)))

    def test_tirnak_ters_bolu_sekme_satir_sonu_ilk_elekte_reddedilir(self):
        for filtre in ("'-w' /tmp/a", "\\-z /home/u/x.sh", '"-z" /x', "port 80\t-w /tmp/a",
                       "port 80\n-z /x", "a'-z' b", "port 80 \"--eval=x\""):
            with self.subTest(filtre=filtre):
                self.assertFalse(self.guvenli(self.tcpdump(filter=filtre)))
        self.assertFalse(self.guvenli({"extra": "'--batch' '--eval=import os'"}))

    def test_filtre_araca_tek_ifade_olarak_secenek_sonundan_sonra_gider(self):
        argv = kur("tcpdump", **self.tcpdump(filter=self.RAPOR_FILTRESI))
        self.assertEqual(argv, ["tcpdump", "-i", "eth0", "-c", "50", "--",
                                "-Z root -w /tmp/a -C 1 -z /home/u/x.sh"])
        # '--' ardindaki her sey yakalama ifadesidir; secenek olarak okunmaz
        self.assertTrue(self.argv_guvenli(ARAC["tcpdump"]["build"], self.tcpdump(filter=self.RAPOR_FILTRESI)))
        for filtre in ("'-w' /tmp/a", "\\-z /x", "port 80\t-w /x", "port 80\n-z /x"):
            with self.subTest(filtre=filtre):
                argv = kur("tcpdump", **self.tcpdump(filter=filtre))
                self.assertEqual(argv[:6], ["tcpdump", "-i", "eth0", "-c", "50", "--"])
                self.assertEqual(len(argv), 7)
        self.assertEqual(kur("tcpdump", **self.tcpdump(filter="port 80")),
                         ["tcpdump", "-i", "eth0", "-c", "50", "--", "port 80"])
        self.assertEqual(kur("tcpdump", **self.tcpdump(filter="'port 80'")),
                         ["tcpdump", "-i", "eth0", "-c", "50", "--", "port 80"])
        self.assertEqual(kur("tcpdump", **self.tcpdump()), ["tcpdump", "-i", "eth0", "-c", "50"])

    def test_kullanici_alani_secenek_olamaz_argv_duzeyinde(self):
        b = ARAC["tcpdump"]["build"]
        for d in (self.tcpdump(iface="-w"), self.tcpdump(iface="\t-w"), self.tcpdump(count="-z"),
                  self.tcpdump(iface="--")):
            with self.subTest(d=d):
                self.assertFalse(self.argv_guvenli(b, d))
        self.assertFalse(self.argv_guvenli(ARAC["nmap"]["build"],
                                           {"target": "--script=/tmp/kotu.nse", "scan_key": 3}))
        self.assertFalse(self.argv_guvenli(ARAC["ufw"]["build"], {"action_key": 3, "port": "--force"}))
        self.assertFalse(self.argv_guvenli(ARAC["sqlmap"]["build"],
                                           {"url": "http://127.0.0.1/?id=1", "extra": "--batch --eval=x"}))

    def test_normal_root_komutlari_gecer(self):
        self.assertTrue(self.argv_guvenli(ARAC["tcpdump"]["build"], self.tcpdump(filter="port 80")))
        self.assertTrue(self.argv_guvenli(ARAC["tcpdump"]["build"], self.tcpdump()))
        self.assertTrue(self.argv_guvenli(ARAC["tshark"]["build"], {"iface": "wlan0", "count": "10"}))
        for k in range(4):
            self.assertTrue(self.argv_guvenli(ARAC["nmap"]["build"], {"target": "127.0.0.1", "scan_key": k}))
        self.assertTrue(self.argv_guvenli(ARAC["ufw"]["build"], {"action_key": 3, "port": "22"}))
        self.assertTrue(self.argv_guvenli(ARAC["fail2ban"]["build"], {"action_key": 0}))

    def test_shlex_ile_bolen_kurucu_tirnakla_asilamaz(self):
        # Eski tcpdump kurucusu gibi bolen bir kurucuda da tirnak/ters bolu ise yaramaz
        eski = lambda v: ["tcpdump", "-i", v["iface"]] + shlex.split(v["filter"])  # noqa: E731
        for filtre in ('"-z" /x', "'-w' /a", "\\-z /x", '"-Z" root'):
            with self.subTest(filtre=filtre):
                self.assertFalse(self.argv_guvenli(eski, {"iface": "eth0", "filter": filtre}))

    def test_kurulamayan_ya_da_bicim_degistiren_komut_reddedilir(self):
        def bozuk(v):
            raise ValueError("kapanmamis tirnak")
        self.assertFalse(self.argv_guvenli(bozuk, {"x": "y"}))
        degisken = lambda v: ["arac", "-a", v["x"]] if v["x"] == "ok" else ["arac", "-b", v["x"]]  # noqa: E731
        self.assertFalse(self.argv_guvenli(degisken, {"x": "ok"}))


# ---------------------------------------------------------------------------
# G-03  Genis onekli geri dongu / 0.0.0.0 "yerel" sayilmaz
# ---------------------------------------------------------------------------

class G03GenisOnekliGeriDongu(unittest.TestCase):
    def test_rapordaki_bes_hedef_disari(self):
        for m in ("0.0.0.0/0", "0.0.0.0/1", "127.0.0.1/0", "127.1.2.3/1", "::1/0"):
            with self.subTest(m=m):
                k = degerlendir(m)
                self.assertEqual(k["sinif"], E.DISARI, k)
                self.assertEqual(k["tur"], "yaz")
                self.assertEqual(k["onay_metni"], m)

    def test_tamami_geri_dongude_olan_ag_yerel_kalir(self):
        for m in ("127.0.0.0/8", "127.0.0.1/24", "127.0.0.1/32", "::1/128", "0.0.0.0/32", "0.0.0.0", "::1"):
            with self.subTest(m=m):
                self.assertEqual(degerlendir(m)["sinif"], E.YEREL)

    def test_geri_donguden_tasan_diger_aglar(self):
        for m in ("0.0.0.0/24", "127.0.0.0/7", "::/0", "::1/64"):
            with self.subTest(m=m):
                self.assertEqual(degerlendir(m)["sinif"], E.DISARI)

    def test_ozel_ag_cidr_davranisi_degismedi(self):
        self.assertEqual(degerlendir("192.168.1.0/24")["sinif"], E.OZEL)
        self.assertEqual(degerlendir("192.168.1.77/24")["aglar"], ["192.168.1.0/24"])
        self.assertEqual(degerlendir("192.168.0.0/16")["sinif"], E.DISARI)
        self.assertEqual(degerlendir("8.8.8.0/24")["sinif"], E.DISARI)


# ---------------------------------------------------------------------------
# G-04  nmap aralik/joker yaziminda adres sayisi ve blok denetimi
# ---------------------------------------------------------------------------

class G04AralikYazimi(unittest.TestCase):
    def test_rapordaki_uc_aralik_disari(self):
        for m in ("10-127.0.0.1", "10-192.168.0.1", "10.*.*.*"):
            with self.subTest(m=m):
                k = degerlendir(m, onayli=("10.0.0.0/24", "10.255.255.0/24"))
                self.assertEqual(k["sinif"], E.DISARI, k)
                self.assertEqual(k["tur"], "yaz")
                self.assertEqual(k["onay_metni"], m)

    def test_dar_ozel_aralik_ozel_kalir(self):
        k = degerlendir("192.168.1.1-50")
        self.assertEqual(k["sinif"], E.OZEL)
        self.assertEqual(k["aglar"], ["192.168.1.0/24"])
        self.assertEqual(degerlendir("192.168.1.*")["aglar"], ["192.168.1.0/24"])
        self.assertFalse(degerlendir("192.168.1.1-50", ("192.168.1.0/24",))["gerek"])

    def test_cidr_ile_ayni_kurallar(self):
        self.assertEqual(degerlendir("192.168.1-2.1")["sinif"], E.DISARI)   # 192.168.0.0/22 gibi
        self.assertEqual(degerlendir("8.8.8.*")["sinif"], E.DISARI)
        self.assertEqual(degerlendir("127.*.*.*")["sinif"], E.YEREL)        # tamami geri dongu
        self.assertEqual(degerlendir("127.0.0.1-5")["sinif"], E.YEREL)
        self.assertEqual(degerlendir("126-127.0.0.1")["sinif"], E.DISARI)
        self.assertEqual(degerlendir("10.0.0.50-1")["sinif"], E.OZEL)       # ters yazilmis uclar

    def test_256_adresten_fazlasi_disari(self):
        for m in ("10.0.0-1.*", "192.168.*.*", "172.16.0-255.1"):
            with self.subTest(m=m):
                self.assertEqual(degerlendir(m)["sinif"], E.DISARI)


# ---------------------------------------------------------------------------
# G-05  Sayisal IP yazimlari IP; tek sozcuklu adlarin onayi hatirlanmaz
# ---------------------------------------------------------------------------

class G05TekSozcukVeSayisalIP(unittest.TestCase):
    def test_onaltilik_ve_kisa_yazimlar_ip_olarak_siniflanir(self):
        for m, ip in (("0x08080808", "8.8.8.8"), ("0x8080808", "8.8.8.8"), ("134744072", "8.8.8.8"),
                      ("8.8.2056", "8.8.8.8"), ("0X08080808", "8.8.8.8"), ("010.0.0.1", "8.0.0.1"),
                      ("http://0x08080808/p?id=1", "8.8.8.8"), ("0x08080808:80", "8.8.8.8")):
            with self.subTest(m=m):
                k = degerlendir(m)
                self.assertEqual(k["sinif"], E.DISARI, k)
                self.assertEqual(k["tur"], "yaz")
                self.assertEqual(k["onay_metni"], ip)

    def test_kisa_yazimla_yerel_ve_ozel(self):
        self.assertEqual(degerlendir("127.1")["sinif"], E.YEREL)
        self.assertEqual(degerlendir("0x7f000001")["sinif"], E.YEREL)
        self.assertEqual(degerlendir("http://127.1:8080/")["sinif"], E.YEREL)
        k = degerlendir("10.1")
        self.assertEqual((k["sinif"], k["aglar"], k["hatirla"]), (E.OZEL, ["10.0.0.0/24"], ["10.0.0.0/24"]))

    def test_tek_sozcuklu_ad_ozel_kalir_ama_hatirlanmaz(self):
        for ad in ("google", "router", "pc"):
            with self.subTest(ad=ad):
                k = degerlendir(ad, onayli=("ad:" + ad,))
                self.assertEqual(k["sinif"], E.OZEL)
                self.assertTrue(k["gerek"])            # daha once "evet" denmis olsa da sorulur
                self.assertEqual(k["tur"], "ozel")
                self.assertEqual(k["aglar"], ["ad:" + ad])
                self.assertEqual(k["hatirla"], [])

    def test_noktali_adlar_ve_ipler_hatirlanir(self):
        k = degerlendir("nas.local")
        self.assertEqual(k["hatirla"], ["ad:nas.local"])
        self.assertFalse(degerlendir("nas.local", ("ad:nas.local",))["gerek"])
        k = degerlendir("router 192.168.1.5")
        self.assertEqual(k["aglar"], ["192.168.1.0/24", "ad:router"])
        self.assertEqual(k["hatirla"], ["192.168.1.0/24"])

    def test_kendi_adi_ve_port_numarasi_degismedi(self):
        self.assertEqual(degerlendir("carotos")["sinif"], E.YEREL)
        self.assertFalse(degerlendir("-p 80 127.0.0.1")["gerek"])
        self.assertFalse(degerlendir("127.0.0.1 65535")["gerek"])
        self.assertEqual(degerlendir("127.0.0.1 134744072")["sinif"], E.DISARI)   # 8.8.8.8 port sanilmaz

    def test_her_donuste_hatirla_alani_var(self):
        for m in ("127.0.0.1", "8.8.8.8", "", "192.168.1.5"):
            with self.subTest(m=m):
                self.assertIsInstance(degerlendir(m)["hatirla"], list)


# ---------------------------------------------------------------------------
# G-06  sqlmap ek parametrelerinde hedef degistiren secenek
# ---------------------------------------------------------------------------

class G06SqlmapEkParametre(unittest.TestCase):
    def bul(self, ek, arac="sqlmap"):
        return MANTIK["hedef_degistiren_secenek"](arac, {"url": "http://127.0.0.1/?id=1", "extra": ek})

    def test_hedef_belirleyen_secenekler_reddedilir(self):
        for ek, beklenen in (("--batch -u http://baskasi.example/p?id=1", "-u"),
                             ("-m liste.txt", "-m"), ("-r istek.txt", "-r"), ("-g inurl:id=", "-g"),
                             ("--url=http://baskasi.example/", "--url"), ("--url http://x/", "--url"),
                             ("--ur http://x/", "--ur"), ("-uhttp://x/?id=1", "-uhttp://x/?id=1"),
                             ("-bu http://x/", "-bu"), ("-d mysql://u:p@x:3306/db", "-d"),
                             ("-l burp.log", "-l"), ("-c sqlmap.conf", "-c"),
                             ("-x http://x/sitemap.xml", "-x"), ("--batch '-u' http://x/", "-u"),
                             ("--batch \\-u http://x/", "-u")):
            with self.subTest(ek=ek):
                self.assertEqual(self.bul(ek), beklenen)

    def test_olagan_ek_parametreler_gecer(self):
        for ek in ("--batch", "--batch --level=3 --risk=2", "-p id --dbs", "-D users -T t --dump",
                   "--data 'id=1'", "--random-agent", "-v 3", "-a", "-hh", "--crawl=2", "", "  "):
            with self.subTest(ek=ek):
                self.assertIsNone(self.bul(ek))

    def test_baska_araclarda_bakilmaz_ve_bozuk_tirnak_cokertmez(self):
        self.assertIsNone(self.bul("-u http://x/", arac="nikto"))
        self.assertIsNone(self.bul("--batch 'kapanmamis"))


# ---------------------------------------------------------------------------
# G-08 / G-10 / G-13  GTK'siz parcalar
# ---------------------------------------------------------------------------

class G08SayiAlani(unittest.TestCase):
    def test_paket_sayisi_dogrulamasi(self):
        gecerli = MANTIK["sayi_gecerli_mi"]
        for m in ("1", "50", " 100 ", "100000"):
            self.assertTrue(gecerli(m), m)
        for m in ("", "  ", "0", "100001", "-5", "5e3", "abc", "１２", "1 2", None, 50):
            self.assertFalse(gecerli(m), m)

    def test_tcpdump_ve_tshark_sayi_alanini_dogrular(self):
        self.assertEqual(ARAC["tcpdump"].get("sayi_alanlari"), ["count"])
        self.assertEqual(ARAC["tshark"].get("sayi_alanlari"), ["count"])


class G10GuvenlikDuvariDurumu(unittest.TestCase):
    def durum(self, icerik):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "ufw.conf")
            if icerik is not None:
                with open(yol, "w", encoding="utf-8") as f:
                    f.write(icerik)
            return MANTIK["guvenlik_duvari_durumu"](yol)

    def test_ufw_conf_parolasiz_okunur(self):
        self.assertIs(self.durum("# ufw\nENABLED=yes\nLOGLEVEL=low\n"), True)
        self.assertIs(self.durum("ENABLED=no\n"), False)
        self.assertIs(self.durum("ENABLED='yes'\n"), True)
        self.assertIs(self.durum("ENABLED=no\nENABLED=yes\n"), True)    # son atama gecerli

    def test_okunamayan_ya_da_belirsiz_durum_bilinmiyor(self):
        self.assertIsNone(self.durum(None))
        self.assertIsNone(self.durum("LOGLEVEL=low\n"))
        self.assertIsNone(self.durum("ENABLED=belki\n"))
        self.assertIsNone(self.durum("\xff\xfe bozuk"))

    def test_acilista_pkexec_ufw_status_yok(self):
        kaynak = panel_kaynagi()
        govde = kaynak[kaynak.index("    def _check_firewall_worker"):kaynak.index("    def _apply_firewall_state")]
        self.assertNotIn("pkexec", govde)
        self.assertNotIn("subprocess", govde)


class G13AyarDosyasi(unittest.TestCase):
    def setUp(self):
        self.dizin = tempfile.TemporaryDirectory()
        self.addCleanup(self.dizin.cleanup)
        self.yol = os.path.join(self.dizin.name, "carotos-panel", "settings.json")
        self.ad = panel_parcalari("load_settings", "save_settings",
                                  CONFIG_DIR=os.path.dirname(self.yol), CONFIG_PATH=self.yol,
                                  DEFAULT_SETTINGS={"language": "en", "theme": "dark"})

    def yaz(self, veri):
        os.makedirs(os.path.dirname(self.yol), exist_ok=True)
        with open(self.yol, "w", encoding="utf-8") as f:
            f.write(veri if isinstance(veri, str) else json.dumps(veri))

    def test_bozuk_degerler_paneli_dusurmez(self):
        for veri in ({"onayli_aglar": 5}, {"onayli_aglar": "10.0.0.0/24"}, {"onayli_aglar": [1, 2]},
                     {"onayli_aglar": None}):
            with self.subTest(veri=veri):
                self.yaz(veri)
                ayar = self.ad["load_settings"]()
                self.assertNotIn("onayli_aglar", ayar)
                self.assertEqual(len(ayar.get("onayli_aglar", []) or []), 0)
        self.yaz({"language": 7, "theme": ["x"]})
        self.assertEqual(self.ad["load_settings"](), {"language": "en", "theme": "dark"})
        for bozuk in ("[1, 2]", "42", "{bozuk", ""):
            self.yaz(bozuk)
            self.assertEqual(self.ad["load_settings"](), {"language": "en", "theme": "dark"})

    def test_gecerli_degerler_korunur(self):
        self.yaz({"language": "tr", "theme": "light", "onayli_aglar": ["192.168.1.0/24"]})
        self.assertEqual(self.ad["load_settings"](),
                         {"language": "tr", "theme": "light", "onayli_aglar": ["192.168.1.0/24"]})

    def test_atomik_yazma_ve_izin(self):
        self.ad["save_settings"]({"language": "tr", "onayli_aglar": ["10.0.0.0/24"]})
        with open(self.yol, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["onayli_aglar"], ["10.0.0.0/24"])
        self.assertFalse(os.path.exists(self.yol + ".tmp"))
        if os.name == "posix":
            self.assertEqual(os.stat(self.yol).st_mode & 0o777, 0o600)


# ---------------------------------------------------------------------------
# Arayuz testleri (GTK + ekran)
# ---------------------------------------------------------------------------

_GTK = {}


def _gtk_hazirla():
    """Paneli bir kez, sahte HOME ile yukler. Ilk pencere kurulurken yapilan butun
    subprocess cagrilari kaydedilir (G-10: acilista parola penceresi acilmamali)."""
    if _GTK:
        return _GTK
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, GLib
    except (ImportError, ValueError) as exc:
        raise unittest.SkipTest("GTK yok: %s" % exc)
    ev = tempfile.TemporaryDirectory()
    os.environ["HOME"] = ev.name
    os.environ["XDG_CONFIG_HOME"] = os.path.join(ev.name, ".config")
    spec = importlib.util.spec_from_file_location("carotos_panel_denetim", PANEL)
    panel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(panel)
    ufw = os.path.join(ev.name, "ufw.conf")
    with open(ufw, "w", encoding="utf-8") as f:
        f.write("ENABLED=yes\n")
    panel.UFW_AYAR = ufw
    cagrilar = []
    asil_run, asil_popen = subprocess.run, subprocess.Popen

    def kaydedici(asil):
        def kaydet(args, *a, **k):
            if "pkexec" in " ".join(map(str, args if isinstance(args, (list, tuple)) else [args])):
                cagrilar.append(args)
                raise AssertionError("acilista yetki istenmemeli")
            return asil(args, *a, **k)
        return kaydet
    with mock.patch.object(subprocess, "run", kaydedici(asil_run)), \
            mock.patch.object(subprocess, "Popen", kaydedici(asil_popen)):
        app = panel.PanelApp()
        _pompala(GLib, 0.5)
    _GTK.update(Gtk=Gtk, GLib=GLib, panel=panel, app=app, ev=ev, acilis_cagrilari=cagrilar)
    return _GTK


def _pompala(GLib, sure=0.3, kosul=None):
    ctx = GLib.MainContext.default()
    son = time.time() + sure
    while True:
        while ctx.iteration(False):
            pass
        if kosul is not None and kosul():
            return True
        if time.time() >= son:
            return kosul() if kosul is not None else True
        time.sleep(0.01)


def tearDownModule():
    if _GTK:
        _GTK["app"].destroy()
        _GTK["ev"].cleanup()


class GtkTaban(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        g = _gtk_hazirla()
        cls.Gtk, cls.GLib, cls.panel, cls.app = g["Gtk"], g["GLib"], g["panel"], g["app"]

    def setUp(self):
        self.app.lang = "tr"
        self.app._calisan = 0

    def pompala(self, sure=0.3, kosul=None):
        return _pompala(self.GLib, sure, kosul)

    def metin(self, sayfa):
        b = sayfa.output_buffer
        return b.get_text(b.get_start_iter(), b.get_end_iter(), False)

    def T(self, anahtar, **kw):
        return self.panel.T(anahtar, self.app.lang, **kw)

    def calistir_yakala(self, sayfa, as_root, sistem=None):
        """run() cagrilir; arac yerine kurulan komut yakalanir. sistem: sahte sistem_yolu."""
        yakalanan = []
        sayfa._worker = lambda cmd: yakalanan.append(cmd)
        sayfa.output_buffer.set_text("")
        try:
            if sistem is not None:
                with mock.patch.object(self.panel.yetkili, "sistem_yolu", sistem):
                    sayfa.run(as_root)
            else:
                sayfa.run(as_root)
        finally:
            del sayfa._worker
            if yakalanan:
                sayfa._done()
        return yakalanan

    @staticmethod
    def sahte_sistem(ad):
        return "/sistem/" + ad


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G01RootArgumanArayuz(GtkTaban):
    def test_tirnakli_filtre_root_ile_calismaz(self):
        sayfa = self.app.pages["tcpdump"]
        sayfa.widgets["filter"]["widget"].set_text(G01RootArgumanDenetimi.RAPOR_FILTRESI)
        try:
            self.assertEqual(self.calistir_yakala(sayfa, True, self.sahte_sistem), [])
            self.assertIn(self.T("root_arg_hata"), self.metin(sayfa))
            sayfa.widgets["filter"]["widget"].set_text("port 80")
            cmd = self.calistir_yakala(sayfa, True, self.sahte_sistem)
            self.assertEqual(cmd, [["/sistem/pkexec", "/sistem/tcpdump", "-i", "eth0", "-c", "50", "--", "port 80"]])
        finally:
            sayfa.widgets["filter"]["widget"].set_text("")


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G02RootDugmesi(GtkTaban):
    ROOTSUZ = ("aircrack-ng", "nikto", "sqlmap", "john", "hydra")

    def test_root_gerekmeyen_araclarda_dugme_gorunmez(self):
        for ad in self.ROOTSUZ:
            with self.subTest(ad=ad):
                self.app.kabuk.sec(ad)
                self.pompala(0.05)
                self.assertFalse(self.app.pages[ad].root_btn.get_visible())
        for ad in ("nmap", "tcpdump", "tshark", "ufw", "fail2ban"):
            with self.subTest(ad=ad):
                self.app.kabuk.sec(ad)
                self.pompala(0.05)
                self.assertTrue(self.app.pages[ad].root_btn.get_visible())

    def test_run_true_hicbir_sey_baslatmaz(self):
        for ad in self.ROOTSUZ:
            with self.subTest(ad=ad):
                sayfa = self.app.pages[ad]
                self.assertEqual(self.calistir_yakala(sayfa, True, self.sahte_sistem), [])
                self.assertEqual(self.metin(sayfa), "")
                self.assertTrue(sayfa.run_btn.get_sensitive())


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G05TekSozcukArayuz(GtkTaban):
    def etik(self, sayfa, hedef, cevap):
        durum = {"acildi": False, "metin": ""}

        def bul():
            for w in self.Gtk.Window.list_toplevels():
                if isinstance(w, self.Gtk.Dialog) and w.get_visible():
                    return w
            return None

        def etiketler(w):
            if isinstance(w, self.Gtk.Label):
                yield w.get_text()
            if isinstance(w, self.Gtk.Container):
                for c in w.get_children():
                    yield from etiketler(c)

        def kontrol():
            p = bul()
            if p is None:
                return True
            durum["acildi"] = True
            durum["metin"] = "\n".join(etiketler(p.get_content_area()))
            p.response(cevap)
            return False
        self.GLib.timeout_add(50, kontrol)
        self.GLib.timeout_add(4000, lambda: (bul() and bul().response(self.Gtk.ResponseType.CANCEL)) and False)
        sonuc = sayfa._etik_onay({"target": hedef, "scan_key": 0})
        return sonuc, durum

    def test_tek_sozcuklu_ad_her_seferinde_sorulur_ve_kaydedilmez(self):
        sayfa = self.app.pages["nmap"]
        self.app.settings.pop("onayli_aglar", None)
        for _ in range(2):
            sonuc, durum = self.etik(sayfa, "router", self.Gtk.ResponseType.OK)
            self.assertTrue(sonuc)
            self.assertTrue(durum["acildi"])
            self.assertIn("hatırlanmaz", durum["metin"])
        self.assertNotIn("ad:router", self.app.settings.get("onayli_aglar", []))
        sonuc, durum = self.etik(sayfa, "nas.local", self.Gtk.ResponseType.OK)
        self.assertIn("bir daha sorulmaz", durum["metin"])
        self.assertEqual(self.app.settings["onayli_aglar"], ["ad:nas.local"])
        self.app.settings.pop("onayli_aglar", None)

    def test_onaltilik_ip_elle_yazim_ister(self):
        sayfa = self.app.pages["nmap"]
        sonuc, durum = self.etik(sayfa, "0x08080808", self.Gtk.ResponseType.CANCEL)
        self.assertFalse(sonuc)
        self.assertIn("8.8.8.8", durum["metin"])
        self.assertNotIn("onayli_aglar", self.app.settings)


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G06SqlmapArayuz(GtkTaban):
    def test_ek_alanda_hedef_secenegi_calismaz(self):
        sayfa = self.app.pages["sqlmap"]
        sayfa.widgets["url"]["widget"].set_text("http://127.0.0.1/?id=1")
        sayfa.widgets["extra"]["widget"].set_text("--batch -u http://baskasi.example/p?id=1")
        try:
            self.assertEqual(self.calistir_yakala(sayfa, False), [])
            self.assertIn(self.T("hedef_secenek_hata", secenek="-u"), self.metin(sayfa))
        finally:
            sayfa.widgets["url"]["widget"].set_text("")
            sayfa.widgets["extra"]["widget"].set_text("--batch")


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G07GecersizUTF8(GtkTaban):
    def test_bozuk_bayt_okumayi_durdurmaz(self):
        sayfa = self.app.pages["aircrack-ng"]
        sayfa.output_buffer.set_text("")
        betik = ("import sys; sys.stdout.buffer.write(b'ESSID: \\xff\\xfe\\n'); "
                 "sys.stdout.flush(); print('son satir')")
        sayfa._worker([sys.executable, "-c", betik])
        bitti = self.T("finished", code=0)
        self.assertTrue(self.pompala(3, lambda: bitti in self.metin(sayfa)), self.metin(sayfa))
        metin = self.metin(sayfa)
        self.assertIn("�", metin)
        self.assertIn("son satir", metin)
        self.assertEqual(sayfa.process.returncode, 0)
        self.assertTrue(sayfa.run_btn.get_sensitive())

    def test_okuma_hatasinda_arac_sonlandirilir(self):
        sayfa = self.app.pages["aircrack-ng"]
        asil = sayfa._kuyruga_ekle
        sayac = {"n": 0}

        def ilki_patlar(m):
            sayac["n"] += 1
            if sayac["n"] == 1:
                raise RuntimeError("okuyucu bozuldu")
            asil(m)
        sayfa._kuyruga_ekle = ilki_patlar
        try:
            bas = time.time()
            sayfa._worker([sys.executable, "-c", "import time; print('a', flush=True); time.sleep(60)"])
            self.assertLess(time.time() - bas, 15)
            self.assertIsNotNone(sayfa.process.poll())          # yetim kalmadi
        finally:
            del sayfa._kuyruga_ekle
        self.pompala(0.3)
        self.assertIn("okuyucu bozuldu", self.metin(sayfa))

    def test_popen_secenekleri(self):
        kaynak = panel_kaynagi()
        govde = kaynak[kaynak.index("    def _worker"):kaynak.index("    def _grubu_sonlandir")]
        self.assertIn('errors="replace"', govde)
        self.assertIn("stdin=subprocess.DEVNULL", govde)


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G08CiktiSiniri(GtkTaban):
    def test_her_satirda_yeni_isaret_acilmaz(self):
        sayfa = self.app.pages["nikto"]
        sayfa.output_buffer.set_text("")
        for i in range(2000):
            sayfa.append(f"satir {i}\n")
        b = sayfa.output_buffer
        toplam = len(b.get_end_iter().get_marks())
        it = b.get_start_iter()
        while True:
            toplam += len(it.get_marks())
            if not it.forward_line():
                break
        self.assertLess(toplam, 10)

    def test_tampon_kirpilir(self):
        sayfa = self.app.pages["nikto"]
        sayfa.output_buffer.set_text("")
        sinir = self.panel.CIKTI_SATIR_SINIRI
        for blok in range(70):
            sayfa.append("".join(f"satir {blok * 100 + i}\n" for i in range(100)))
        self.assertLessEqual(sayfa.output_buffer.get_line_count(), sinir + 1)
        self.assertTrue(self.metin(sayfa).endswith("satir 6999\n"))
        sayfa.output_buffer.set_text("")

    def test_is_parcacigi_satirlari_toplu_yazilir(self):
        sayfa = self.app.pages["nikto"]
        sayfa.output_buffer.set_text("")
        zamanlayici = []
        with mock.patch.object(self.panel.GLib, "timeout_add", lambda *a: zamanlayici.append(a) or 0):
            t = threading.Thread(target=lambda: [sayfa._kuyruga_ekle(f"s{i}\n") for i in range(1000)])
            t.start()
            t.join()
        self.assertEqual(len(zamanlayici), 1)
        sayfa._kuyrugu_bosalt()
        self.assertEqual(self.metin(sayfa).count("\n"), 1000)
        with mock.patch.object(self.panel.GLib, "timeout_add", lambda *a: 0):
            for i in range(7000):
                sayfa._kuyruga_ekle(f"t{i}\n")
        sayfa.output_buffer.set_text("")
        sayfa._kuyrugu_bosalt()
        self.assertLessEqual(sayfa.output_buffer.get_line_count(), self.panel.CIKTI_SATIR_SINIRI + 1)
        self.assertIn("t6999", self.metin(sayfa))
        sayfa.output_buffer.set_text("")

    def test_bos_ya_da_gecersiz_paket_sayisi_calismaz(self):
        sayfa = self.app.pages["tcpdump"]
        alan = sayfa.widgets["count"]["widget"]
        try:
            for deger in ("", "abc", "0", "100001", "-c"):
                with self.subTest(deger=deger):
                    alan.set_text(deger)
                    self.assertEqual(self.calistir_yakala(sayfa, True, self.sahte_sistem), [])
                    self.assertIn(self.T("sayi_hata", alan="Paket sayısı"), self.metin(sayfa))
        finally:
            alan.set_text("50")


class _SahteSurec:
    pid = os.getpid()

    def poll(self):
        return None


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G09RootDurdurma(GtkTaban):
    def durdur(self, kod, gecikme=0.0):
        sayfa = self.app.pages["tcpdump"]
        sayfa.output_buffer.set_text("")
        sayfa.process = _SahteSurec()
        sayfa.run_as_root = True
        sayfa.stop_btn.set_sensitive(True)
        cagri = []

        def sahte_run(args, **k):
            cagri.append(args)
            time.sleep(gecikme)
            return types.SimpleNamespace(returncode=kod)
        try:
            with mock.patch.object(self.panel.yetkili, "sistem_yolu", self.sahte_sistem), \
                    mock.patch.object(subprocess, "run", sahte_run):
                bas = time.time()
                sayfa.stop()
                sure = time.time() - bas
                self.pompala(3, lambda: self.metin(sayfa) != "")
        finally:
            sayfa.process = None
            sayfa.run_as_root = False
        return sayfa, cagri, sure

    def test_iptal_edilince_dogru_ileti(self):
        sayfa, cagri, sure = self.durdur(126, gecikme=0.4)
        self.assertLess(sure, 0.3)                  # arayuz donmaz
        self.assertEqual(cagri, [["/sistem/pkexec", "/sistem/kill", "-TERM", f"-{os.getpgid(os.getpid())}"]])
        self.assertIn(self.T("durdurma_iptal"), self.metin(sayfa))
        self.assertNotIn(self.T("stopped"), self.metin(sayfa))

    def test_basarida_durduruldu_hatada_kod(self):
        sayfa, _, _ = self.durdur(0)
        self.assertIn(self.T("stopped"), self.metin(sayfa))
        sayfa, _, _ = self.durdur(1)
        self.assertIn(self.T("durdurma_hata", code=1), self.metin(sayfa))


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G10GuvenlikDuvariArayuz(GtkTaban):
    def test_acilista_parola_istenmez_ve_durum_okunur(self):
        self.assertEqual(_GTK["acilis_cagrilari"], [])
        ayar = self.app.settings_page
        ayar.refresh_firewall()
        self.assertTrue(self.pompala(2, lambda: ayar.fw_status_label.get_text() == self.T("firewall_on")))
        self.assertTrue(ayar.fw_switch.get_active())

    def test_okunamazsa_bilinmiyor(self):
        ayar = self.app.settings_page
        eski = self.panel.UFW_AYAR
        self.panel.UFW_AYAR = os.path.join(_GTK["ev"].name, "yok.conf")
        try:
            ayar.refresh_firewall()
            self.assertTrue(self.pompala(2, lambda: ayar.fw_status_label.get_text() == self.T("firewall_unknown")))
            self.assertFalse(ayar.fw_switch.get_sensitive())
        finally:
            self.panel.UFW_AYAR = eski
            ayar.refresh_firewall()
            self.pompala(0.3)

    def test_degisiklikte_sistem_yolundan_yetki_istenir(self):
        ayar = self.app.settings_page
        cagri = []

        def sahte_run(args, **k):
            cagri.append(args)
            return types.SimpleNamespace(returncode=126, stdout="", stderr="")
        with mock.patch.object(self.panel.yetkili, "sistem_yolu", self.sahte_sistem), \
                mock.patch.object(subprocess, "run", sahte_run):
            ayar._set_firewall_worker(False)
        self.assertEqual(cagri, [["/sistem/pkexec", "/sistem/ufw", "disable"]])
        self.assertTrue(self.pompala(2, lambda: ayar.fw_status_label.get_text() == self.T("firewall_on")))


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G11PencereKapaninca(GtkTaban):
    def test_yetkisiz_arac_pencereyle_sonlanir(self):
        app2 = self.panel.PanelApp()
        cocuk = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                                 start_new_session=True)
        try:
            app2.pages["nmap"].process = cocuk
            app2.pages["nmap"].run_as_root = False
            app2.destroy()
            self.assertIsNotNone(cocuk.wait(timeout=5))
        finally:
            if cocuk.poll() is None:
                cocuk.kill()
                cocuk.wait()


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G12RootProgramYolu(GtkTaban):
    def test_root_programi_path_ten_bulunmaz(self):
        with tempfile.TemporaryDirectory() as d:
            sahte = os.path.join(d, "tcpdump")
            with open(sahte, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(sahte, 0o755)
            sayfa = self.app.pages["tcpdump"]
            with mock.patch.dict(os.environ, {"PATH": d + os.pathsep + os.environ.get("PATH", "")}):
                cmd = self.calistir_yakala(sayfa, True, self.sahte_sistem)
                self.assertEqual(cmd, [["/sistem/pkexec", "/sistem/tcpdump", "-i", "eth0", "-c", "50"]])
                # sistem dizinlerinde yoksa PATH'teki sahte dosyaya dusulmez
                cmd = self.calistir_yakala(sayfa, True, lambda ad: "/sistem/pkexec" if ad == "pkexec" else None)
                self.assertEqual(cmd, [])
                self.assertIn(self.T("not_found", cmd="tcpdump"), self.metin(sayfa))

    def test_kaynakta_goreli_pkexec_kalmadi(self):
        kaynak = panel_kaynagi()
        self.assertNotIn('["pkexec"', kaynak)
        self.assertNotIn('"kill", "-TERM"', kaynak)


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class G14CalisanSayaci(GtkTaban):
    def test_ilk_biten_arac_cubugu_gizlemez(self):
        self.app.calisiyor(True, "a")
        self.app.calisiyor(True, "b")
        self.app.calisiyor(False, "hazir")
        self.assertTrue(self.app.bar.get_visible())
        self.app.calisiyor(False, "hazir")
        self.assertFalse(self.app.bar.get_visible())
        self.assertEqual(self.app._calisan, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
