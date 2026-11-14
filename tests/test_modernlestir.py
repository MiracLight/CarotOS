#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""""Carot Sleek": carotos-tema-kur (root yardimcisi) ve carotos-modernlestir (kullanici betigi).

Sahte xfconf-query / gsettings / pgrep / pkill (Python icinde, argv birebir ayristirilir), sahte
apt-get ve dpkg-query (gecici kabuk betikleri) ve gecici HOME ile calisir; sisteme dokunmaz.

Calistirma:  python3 tests/test_modernlestir.py
"""
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROOT = os.path.join(KOK, "config", "includes.chroot")
TEMA_KUR = os.path.join(CHROOT, "usr", "local", "sbin", "carotos-tema-kur")
MODERN = os.path.join(CHROOT, "usr", "local", "bin", "carotos-modernlestir")
POSIX = os.name == "posix"


def _yukle(ad, yol):
    yukleyici = importlib.machinery.SourceFileLoader(ad, yol)
    spec = importlib.util.spec_from_loader(ad, yukleyici)
    mod = importlib.util.module_from_spec(spec)
    yukleyici.exec_module(mod)
    return mod


tk = _yukle("carotos_tema_kur", TEMA_KUR)
md = _yukle("carotos_modernlestir", MODERN)


# ---------------------------------------------------------------------------
# carotos-tema-kur
# ---------------------------------------------------------------------------

class TemaKurStatikTesti(unittest.TestCase):
    def setUp(self):
        with open(TEMA_KUR, encoding="utf-8") as f:
            self.kaynak = f.read()

    def test_sertlik(self):
        self.assertTrue(self.kaynak.startswith("#!/usr/bin/python3 -I\n"))
        self.assertIn("sys.dont_write_bytecode = True", self.kaynak)
        self.assertNotIn("shell=True", self.kaynak)
        self.assertNotIn("os.system", self.kaynak)
        self.assertEqual(tk.APT_GET, "/usr/bin/apt-get")
        self.assertEqual(tk.ORTAM["LC_ALL"], "C")
        self.assertEqual(tk.ORTAM["DEBIAN_FRONTEND"], "noninteractive")

    def test_sabit_paket_listesi(self):
        self.assertEqual(tk.PAKETLER, ("orchis-gtk-theme", "papirus-icon-theme",
                                       "fonts-inter", "fonts-jetbrains-mono", "picom", "plank", "rofi"))
        self.assertNotIn("xfce4-appmenu-plugin", tk.PAKETLER)

    def test_komutlar_sabit_ve_update_yok(self):
        indir, kur = tk.komutlar("/usr/bin/apt-get")
        for k in (indir, kur):
            self.assertEqual(k[0], "/usr/bin/apt-get")
            self.assertIn("--no-install-recommends", k)
            self.assertIn("DPkg::Lock::Timeout=60", k)
            self.assertNotIn("update", k)
            i = k.index("--")
            self.assertEqual(tuple(k[i + 1:]), tk.PAKETLER)
            self.assertEqual(k[i - 1], "install")
        self.assertIn("--download-only", indir)
        self.assertNotIn("--download-only", kur)

    def test_arguman_dogrulamasi(self):
        for argv in (["x"], ["kur", "fazla"], ["install"], ["--", "picom"], ["durum", "picom"]):
            self.assertEqual(tk.main(argv, root_mu=True, akis=io.StringIO()), tk.KOD_KULLANIM, argv)

    def test_root_degilse_reddedilir(self):
        self.assertEqual(tk.main(["kur"], root_mu=False, akis=io.StringIO()), tk.KOD_ROOT)
        self.assertEqual(tk.main([], root_mu=False, akis=io.StringIO()), tk.KOD_ROOT)

    def test_hata_turu(self):
        self.assertEqual(tk.hata_turu(["E: Unable to locate package picom"]), tk.KOD_BULUNAMADI)
        self.assertEqual(tk.hata_turu(["Package plank has no installation candidate"]), tk.KOD_BULUNAMADI)
        self.assertEqual(tk.hata_turu(["Err:1 http://deb.debian.org trixie InRelease",
                                       "  Temporary failure resolving 'deb.debian.org'"]), tk.KOD_AG)
        self.assertEqual(tk.hata_turu(["E: Could not get lock /var/lib/dpkg/lock-frontend"]), tk.KOD_KILIT)
        self.assertEqual(tk.hata_turu(["E: Sub-process /usr/bin/dpkg returned an error code (1)"]), tk.KOD_APT)


@unittest.skipUnless(POSIX, "sahte apt-get icin POSIX gerekir")
class TemaKurSahteAptTesti(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.kayit = os.path.join(self.d, "apt.log")
        self.ortam = dict(tk.ORTAM)

    def betik(self, ad, govde):
        yol = os.path.join(self.d, ad)
        with open(yol, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n" + govde)
        os.chmod(yol, 0o755)
        return yol

    def apt(self, cikti="", kod=0, yalniz_kurulumda=False):
        kosul = 'case "$*" in *--download-only*) exit 0;; esac\n' if yalniz_kurulumda else ""
        return self.betik("apt-get", 'echo "$*" >> "%s"\n%sprintf "%%s\\n" "%s"\nexit %d\n'
                          % (self.kayit, kosul, cikti, kod))

    def dpkg(self, kurulu):
        if kurulu:
            return self.betik("dpkg-query", 'printf "install ok installed"\n')
        return self.betik("dpkg-query", "exit 1\n")

    def calistir(self, apt, dpkg, argv=("kur",)):
        akis = io.StringIO()
        kod = tk.main(list(argv), apt_get=apt, dpkg_query=dpkg, ortam=self.ortam, root_mu=True, akis=akis)
        return kod, akis.getvalue()

    def apt_satirlari(self):
        if not os.path.exists(self.kayit):
            return []
        with open(self.kayit, encoding="utf-8") as f:
            return f.read().splitlines()

    def test_basarili_kurulum_iki_faz(self):
        kod, cikti = self.calistir(self.apt("Setting up picom"), self.dpkg(False))
        self.assertEqual(kod, 0)
        self.assertIn("@@CAROTOS-FAZ indirme", cikti)
        self.assertIn("@@CAROTOS-FAZ kurulum", cikti)
        self.assertLess(cikti.index("indirme"), cikti.index("kurulum"))
        self.assertIn("Setting up picom", cikti)
        satirlar = self.apt_satirlari()
        self.assertEqual(len(satirlar), 2)
        self.assertIn("--download-only", satirlar[0])
        for s in satirlar:
            self.assertTrue(s.endswith("install -- " + " ".join(tk.PAKETLER)), s)
            self.assertNotIn("update", s.split())

    def test_paket_bulunamadi(self):
        kod, cikti = self.calistir(self.apt("E: Unable to locate package bibata-cursor-theme", 100),
                                   self.dpkg(False))
        self.assertEqual(kod, tk.KOD_BULUNAMADI)
        self.assertNotIn("@@CAROTOS-FAZ kurulum", cikti)

    def test_ag_yok(self):
        kod, _ = self.calistir(self.apt("Temporary failure resolving 'deb.debian.org'", 100), self.dpkg(False))
        self.assertEqual(kod, tk.KOD_AG)

    def test_kilit(self):
        kod, _ = self.calistir(self.apt("E: Could not get lock /var/lib/dpkg/lock-frontend", 100,
                                        yalniz_kurulumda=True), self.dpkg(False))
        self.assertEqual(kod, tk.KOD_KILIT)

    def test_zaten_kuruluysa_apt_calismaz(self):
        kod, cikti = self.calistir(self.apt("x"), self.dpkg(True))
        self.assertEqual(kod, 0)
        self.assertIn("zaten kurulu", cikti)
        self.assertEqual(self.apt_satirlari(), [])

    def test_durum_root_gerektirmez(self):
        akis = io.StringIO()
        kod = tk.main(["durum"], dpkg_query=self.dpkg(True), ortam=self.ortam, root_mu=False, akis=akis)
        self.assertEqual(kod, 0)
        self.assertEqual(akis.getvalue().splitlines(), ["%s kurulu" % p for p in tk.PAKETLER])

    def test_apt_get_yoksa(self):
        kod, _ = self.calistir(os.path.join(self.d, "yok"), self.dpkg(False))
        self.assertEqual(kod, tk.KOD_APT_YOK)


# ---------------------------------------------------------------------------
# carotos-modernlestir: sahte masaustu
# ---------------------------------------------------------------------------

class SahteMasaustu:
    """xfconf-query, gsettings, pgrep, pkill, xfce4-panel, systemd-detect-virt, fc-list taklidi."""

    def __init__(self, xfconf, sanal=False, yazi_tipleri=("Inter", "JetBrains Mono")):
        self.xfconf = {k: list(v) if isinstance(v, list) else v for k, v in xfconf.items()}
        self.gsettings = {}
        self.calisan = {"xfce4-panel", "xfwm4"}
        self.baslatilan = []
        self.sanal = sanal
        self.yazi_tipleri = set(yazi_tipleri)
        self.gsettings_hata = False
        self.picom_hata = False
        self.komutlar = []

    def calistir(self, argv):
        self.komutlar.append(argv)
        ad = os.path.basename(argv[0])
        assert argv[0] == "/usr/bin/" + ad, argv           # yalniz tam yol
        return getattr(self, "_" + ad.replace("-", "_"))(argv[1:])

    def baslat(self, argv):
        assert argv[0].startswith("/usr/bin/"), argv
        if self.picom_hata and argv[0] == "/usr/bin/picom":
            return False
        self.baslatilan.append(argv)
        self.calisan.add(os.path.basename(argv[0]))
        return True

    # xfconf-query -c K -p P [-n] [-a] [-t T -s V]... | -r | -l
    def _xfconf_query(self, a):
        kanal = a[a.index("-c") + 1]
        if "-l" in a:
            ozl = sorted(p for (k, p) in self.xfconf if k == kanal)
            return (0, "\n".join(ozl) + "\n") if ozl else (1, "")
        ozellik = a[a.index("-p") + 1]
        anahtar = (kanal, ozellik)
        if "-r" in a:
            self.xfconf.pop(anahtar, None)
            return 0, ""
        if "-s" not in a:
            if anahtar not in self.xfconf:
                return 1, ""
            d = self.xfconf[anahtar]
            if isinstance(d, list):
                return 0, "Value is an array with %d items:\n\n%s\n" % (len(d), "\n".join(d))
            return 0, d + "\n"
        degerler, turler = [], []
        for i, x in enumerate(a):
            if x == "-s":
                degerler.append(a[i + 1])
            if x == "-t":
                turler.append(a[i + 1])
        assert len(degerler) == len(turler), a
        if anahtar not in self.xfconf and "-n" not in a:
            return 1, ""
        for t, d in zip(turler, degerler):
            if t == "bool":
                assert d in ("true", "false"), a
            if t in ("int", "uint"):
                int(d)
        self.xfconf[anahtar] = list(degerler) if ("-a" in a or len(degerler) > 1) else degerler[0]
        return 0, ""

    def _gsettings(self, a):
        dock = a[1].rstrip("/").rsplit("/", 1)[-1]
        assert dock in ("dock1", "dock2"), a
        anahtar = a[2] if dock == "dock1" else dock + "/" + a[2]      # dock2 anahtarlari "dock2/<ad>"
        if a[0] == "get":
            return 0, self.gsettings.get(anahtar, "@as []" if a[2] == "dock-items" else "'varsayilan'") + "\n"
        if a[0] == "set":
            if self.gsettings_hata:
                return 1, ""
            self.gsettings[anahtar] = a[3]
            return 0, ""
        if a[0] == "reset":
            self.gsettings.pop(anahtar, None)
            return 0, ""
        return 1, ""

    def _pgrep(self, a):
        return (0, "1\n") if a[-1] in self.calisan else (1, "")

    def _pkill(self, a):
        self.calisan.discard(a[-1])
        return 0, ""

    def _xfce4_panel(self, a):
        if a == ["--quit"]:
            self.calisan.discard("xfce4-panel")
        return 0, ""

    def _systemd_detect_virt(self, a):
        assert a == ["--vm", "--quiet"], a
        return (0, "") if self.sanal else (1, "")

    def _fc_list(self, a):
        aile = a[0].split("=", 1)[1]
        return (0, aile + "\n") if aile in self.yazi_tipleri else (0, "")


BASLANGIC_XFCONF = {
    ("xsettings", "/Net/ThemeName"): "Arc-Dark",
    ("xsettings", "/Net/IconThemeName"): "Papirus-Dark",
    ("xsettings", "/Gtk/CursorThemeName"): "Breeze_Light",
    ("xfwm4", "/general/theme"): "Arc-Dark",
    ("xfwm4", "/general/title_alignment"): "center",
    ("xfwm4", "/general/use_compositing"): "true",
    ("xfce4-panel", "/panels"): ["1", "2"],
    ("xfce4-panel", "/panels/panel-1/plugin-ids"): ["1", "8"],
    ("xfce4-panel", "/panels/panel-1/size"): "32",
    ("xfce4-panel", "/panels/panel-1/background-style"): "0",
    ("xfce4-panel", "/panels/panel-2/plugin-ids"): ["11", "12", "13"],
    ("xfce4-panel", "/plugins/plugin-1"): "applicationsmenu",
    ("xfce4-panel", "/plugins/plugin-8"): "clock",
    ("xfce4-panel", "/plugins/plugin-8/mode"): "2",
    ("xfce4-panel", "/plugins/plugin-11"): "showdesktop",
    ("xfce4-panel", "/plugins/plugin-12"): "separator",
    ("xfce4-panel", "/plugins/plugin-13"): "launcher",
    ("xfce4-panel", "/plugins/plugin-13/items"): ["1786.desktop"],
    ("xfce4-keyboard-shortcuts", "/commands/custom/<Super>r"): "xfce4-appfinder -c",
}

UYGULAMALAR = ("carotos-magaza.desktop", "carotos-security-panel.desktop", "carotos-carotene.desktop",
               "thunar.desktop", "xfce4-terminal.desktop", "xfce4-web-browser.desktop")
GTK_CSS = "/* kullanicinin kendi kurali */\nbutton { color: red; }\n"
TERMINALRC = "[Configuration]\nMiscDefaultGeometry=100x30\nFontName=Monospace 12\n"


class ModernlestirTabani(unittest.TestCase):
    sanal = False

    def setUp(self):
        self.kok = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.ev = os.path.join(self.kok, "ev")
        sistem = os.path.join(self.kok, "sistem")
        self.uyg = os.path.join(sistem, "applications")
        self.temalar = os.path.join(sistem, "themes")
        self.simgeler = os.path.join(sistem, "icons")
        for d in (os.path.join(self.temalar, "Orchis-Dark-Compact", "gtk-3.0"),
                  os.path.join(self.temalar, "Orchis-Dark", "gtk-3.0"),
                  os.path.join(self.temalar, "Orchis-Dark", "xfwm4"),
                  os.path.join(self.simgeler, "Bibata-Modern-Ice", "cursors"),
                  os.path.join(self.simgeler, "Papirus-Dark"), self.uyg):
            os.makedirs(d)
        self.yaz(os.path.join(self.temalar, "Orchis-Dark", "xfwm4", "themerc"), "x\n")
        self.yaz(os.path.join(self.simgeler, "Papirus-Dark", "index.theme"), "[Icon Theme]\n")
        for ad in UYGULAMALAR:
            self.yaz(os.path.join(self.uyg, ad), "[Desktop Entry]\nName=%s\n" % ad)
        self.config = os.path.join(self.ev, ".config")
        self.yaz(os.path.join(self.config, "xfce4", "panel", "launcher-13", "1786.desktop"),
                 "[Desktop Entry]\nExec=exo-open --launch WebBrowser\n"
                 "X-XFCE-Source=file://%s\n" % os.path.join(self.uyg, "xfce4-web-browser.desktop"))
        self.yaz(os.path.join(self.config, "gtk-3.0", "gtk.css"), GTK_CSS)
        self.yaz(os.path.join(self.config, "xfce4", "terminal", "terminalrc"), TERMINALRC)
        self.masa = SahteMasaustu(BASLANGIC_XFCONF, sanal=self.sanal)
        self.o = md.Ortam(self.ev, uygulamalar=self.uyg, temalar=self.temalar, simgeler=self.simgeler,
                          calistir=self.masa.calistir, baslat=self.masa.baslat,
                          program_var=lambda ad: True, bekle=lambda s: None, dil="tr")
        self.ciktilar = []

    def yaz(self, yol, metin):
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)

    def oku(self, yol):
        with open(yol, encoding="utf-8") as f:
            return f.read()

    def calistir(self, komut):
        return md.main([komut], o=self.o, cikti=self.ciktilar.append)

    def ev_dosyalari(self):
        sonuc = {}
        for kok, _d, dosyalar in os.walk(self.ev):
            for ad in dosyalar:
                yol = os.path.join(kok, ad)
                sonuc[os.path.relpath(yol, self.ev)] = self.oku(yol)
        return sonuc

    def x(self, kanal, ozellik):
        return self.masa.xfconf.get((kanal, ozellik))


class ModernlestirUygulaTesti(ModernlestirTabani):
    def test_uygula_beklenen_anahtarlar(self):
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        self.assertEqual(self.x("xsettings", "/Net/ThemeName"), "Orchis-Dark-Compact")
        self.assertEqual(self.x("xfwm4", "/general/theme"), "Orchis-Dark")      # Compact'ta xfwm4 yok
        self.assertEqual(self.x("xsettings", "/Net/IconThemeName"), "Papirus-Dark")
        self.assertEqual(self.x("xsettings", "/Gtk/CursorThemeName"), "Breeze_Light")   # imlec DEGISMEZ
        self.assertEqual(self.x("xsettings", "/Gtk/FontName"), "Inter 10")
        self.assertEqual(self.x("xsettings", "/Gtk/MonospaceFontName"), "JetBrains Mono 10")
        self.assertEqual(self.x("xfwm4", "/general/title_alignment"), "center")
        self.assertEqual(self.x("xfwm4", "/general/use_compositing"), "false")
        self.assertEqual(self.x("xfce4-panel", "/panels/panel-1/size"), "30")
        self.assertEqual(self.x("xfce4-panel", "/panels/panel-1/background-style"), "0")
        self.assertEqual(self.x("xfce4-panel", "/plugins/plugin-8/digital-time-format"), "%a %d %b  %H:%M")
        # eklenti yerlesimi degismedi; yalniz baslaticidan olusan alt panel listeden cikti
        self.assertEqual(self.x("xfce4-panel", "/panels/panel-1/plugin-ids"), ["1", "8"])
        self.assertEqual(self.x("xfce4-panel", "/panels/panel-2/plugin-ids"), ["11", "12", "13"])
        self.assertEqual(self.x("xfce4-panel", "/panels"), ["1"])
        kisayol = self.x("xfce4-keyboard-shortcuts", "/commands/custom/<Super>space")
        self.assertTrue(kisayol.startswith("/usr/bin/rofi -show drun -theme "), kisayol)
        self.assertIn("carotos.rasi", kisayol)
        # baslatilan surecler
        adlar = [a[0] for a in self.masa.baslatilan]
        self.assertIn("/usr/bin/picom", adlar)
        self.assertIn("/usr/bin/plank", adlar)
        self.assertIn("/usr/bin/xfce4-panel", adlar)
        picom = [a for a in self.masa.baslatilan if a[0] == "/usr/bin/picom"][0]
        self.assertEqual(picom, ["/usr/bin/picom", "--config", os.path.join(self.config, "picom", "picom.conf")])
        # plank
        g = self.masa.gsettings
        self.assertEqual(g["position"], "'bottom'")
        self.assertEqual(g["hide-mode"], "'intelligent'")
        self.assertEqual(g["zoom-enabled"], "true")

    def test_dosyalar_ve_yedek(self):
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        for yol in (("picom", "picom.conf"), ("autostart", "carotos-picom.desktop"),
                    ("autostart", "carotos-plank.desktop"), ("rofi", "carotos.rasi")):
            self.assertTrue(os.path.isfile(os.path.join(self.config, *yol)), yol)
        oto = self.oku(os.path.join(self.config, "autostart", "carotos-picom.desktop"))
        self.assertIn("Exec=/usr/bin/picom --config ", oto)
        self.assertIn(md.DESKTOP_ISARETI, oto)
        css = self.oku(os.path.join(self.config, "gtk-3.0", "gtk.css"))
        self.assertTrue(css.startswith(GTK_CSS))
        self.assertIn(md.CSS_BAS, css)
        trc = self.oku(os.path.join(self.config, "xfce4", "terminal", "terminalrc"))
        self.assertIn("MiscDefaultGeometry=100x30", trc)
        self.assertIn("FontName=JetBrains Mono 11", trc)
        self.assertNotIn("Monospace 12", trc)
        self.assertIn("BackgroundMode=TERMINAL_BACKGROUND_TRANSPARENT", trc)
        yedek = self.o.yedek_yolu
        self.assertTrue(os.path.isfile(yedek))
        if POSIX:
            self.assertEqual(stat.S_IMODE(os.stat(yedek).st_mode), 0o600)
        veri = json.loads(self.oku(yedek))
        kayitlar = {(x["kanal"], x["ozellik"]): x for x in veri["xfconf"]}
        self.assertEqual(kayitlar[("xsettings", "/Net/ThemeName")]["deger"], "Arc-Dark")
        self.assertFalse(kayitlar[("xsettings", "/Gtk/FontName")]["var"])          # "yoktu" isareti
        self.assertEqual(kayitlar[("xfce4-panel", "/panels")]["deger"], ["1", "2"])
        self.assertEqual(veri["terminalrc"]["anahtarlar"]["FontName"], "Monospace 12")
        self.assertIsNone(veri["terminalrc"]["anahtarlar"]["BackgroundMode"])

    def test_dock_ogeleri(self):
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        alt = os.path.join(self.config, "plank", "dock1", "launchers")
        yan = os.path.join(self.config, "plank", "dock2", "launchers")
        # ALT dock: yalnizca sistem (dosyalar, terminal, tarayici); CarotOS uygulamalari yok
        self.assertEqual(sorted(os.listdir(alt)), sorted([
            "carotos-thunar.dockitem", "carotos-xfce4-terminal.dockitem",
            "carotos-xfce4-web-browser.dockitem"]))
        # SOL yan dock: butun CarotOS uygulamalari (welcome bu sahte sistemde yok: konmadi)
        self.assertEqual(sorted(os.listdir(yan)), sorted([
            "carotos-carotos-magaza.dockitem", "carotos-carotos-security-panel.dockitem",
            "carotos-carotos-carotene.dockitem"]))
        self.assertEqual(self.masa.gsettings["dock2/position"], "'left'")
        self.assertEqual(self.masa.gsettings["position"], "'bottom'")
        self.assertEqual(self.masa.gsettings["dock2/hide-mode"], "'intelligent'")   # tam ekranda iceri girer
        self.assertEqual(self.masa.gsettings["dock2/pinned-only"], "true")          # yalniz CarotOS uygulamalari
        icerik = self.oku(os.path.join(yan, "carotos-carotos-magaza.dockitem"))
        self.assertTrue(icerik.startswith("[PlankDockItemPreferences]\nLauncher=file://"))
        self.assertIn(os.path.join(self.uyg, "carotos-magaza.desktop").replace(os.sep, "/").split(":")[-1],
                      icerik.replace("%3A", ":"))
        self.assertIn("carotos-carotos-magaza.dockitem", self.masa.gsettings["dock2/dock-items"])
        self.assertIn("carotos-thunar.dockitem", self.masa.gsettings["dock-items"])
        self.assertIn(("autostart", "carotos-plank-yan.desktop"),
                      [tuple(os.path.relpath(p, self.config).split(os.sep)) for p in
                       (os.path.join(self.config, "autostart", "carotos-plank-yan.desktop"),)
                       if os.path.exists(p)])

    def test_geri_al_tam_eski_duruma(self):
        once_dosya = self.ev_dosyalari()
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        self.assertNotEqual(self.masa.xfconf, BASLANGIC_XFCONF)
        self.assertEqual(self.calistir("geri-al"), 0, self.ciktilar)
        self.assertEqual(self.masa.xfconf, BASLANGIC_XFCONF)
        self.assertEqual(self.ev_dosyalari(), once_dosya)
        self.assertFalse(os.path.exists(self.o.yedek_yolu))
        self.assertNotIn("picom", self.masa.calisan)
        self.assertNotIn("plank", self.masa.calisan)
        # plank anahtarlari uygulamadan once okunan degerlere doner
        for anahtar, deger in self.masa.gsettings.items():
            self.assertEqual(deger, "@as []" if anahtar.endswith("dock-items") else "'varsayilan'", anahtar)

    def test_ikinci_uygulama_yedegi_ezmez(self):
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        ilk = self.oku(self.o.yedek_yolu)
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        self.assertEqual(self.oku(self.o.yedek_yolu), ilk)
        css = self.oku(os.path.join(self.config, "gtk-3.0", "gtk.css"))
        self.assertEqual(css.count(md.CSS_BAS), 1)
        self.assertEqual(self.calistir("geri-al"), 0, self.ciktilar)
        self.assertEqual(self.masa.xfconf, BASLANGIC_XFCONF)
        self.assertEqual(self.oku(os.path.join(self.config, "gtk-3.0", "gtk.css")), GTK_CSS)
        self.assertEqual(self.oku(os.path.join(self.config, "xfce4", "terminal", "terminalrc")), TERMINALRC)

    def test_dolu_kisayol_ezilmez(self):
        self.masa.xfconf[("xfce4-keyboard-shortcuts", "/commands/custom/<Super>space")] = "xfce4-popup-whiskermenu"
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        self.assertEqual(self.x("xfce4-keyboard-shortcuts", "/commands/custom/<Super>space"),
                         "xfce4-popup-whiskermenu")
        self.assertTrue(any("Super+Space" in c for c in self.ciktilar), self.ciktilar)
        self.assertEqual(self.calistir("geri-al"), 0)
        self.assertEqual(self.x("xfce4-keyboard-shortcuts", "/commands/custom/<Super>space"),
                         "xfce4-popup-whiskermenu")

    def test_yarida_kalirsa_her_sey_eski_halinde(self):
        once_dosya = self.ev_dosyalari()
        self.masa.picom_hata = True                  # son adimlardan biri basarisiz
        self.assertEqual(self.calistir("uygula"), md.KOD_HATA)
        self.assertEqual(self.x("xfwm4", "/general/use_compositing"), "true")   # birlestirici geri acik
        self.assertEqual(self.masa.xfconf, BASLANGIC_XFCONF)
        self.assertEqual(self.ev_dosyalari(), once_dosya)
        self.assertFalse(os.path.exists(self.o.yedek_yolu))

    def test_eksik_program_hicbir_sey_degistirmez(self):
        once_dosya = self.ev_dosyalari()
        self.o._program_var = lambda ad: ad != "plank"
        self.assertEqual(self.calistir("uygula"), md.KOD_EKSIK)
        self.assertEqual(self.masa.xfconf, BASLANGIC_XFCONF)
        self.assertEqual(self.ev_dosyalari(), once_dosya)
        self.assertTrue(any("carotos-tema-kur" in c for c in self.ciktilar))

    def test_yedek_yoksa_geri_al(self):
        self.assertEqual(self.calistir("geri-al"), md.KOD_YEDEK_YOK)

    def test_bozuk_yedek_kenara_alinir(self):
        self.yaz(self.o.yedek_yolu, "{bozuk")
        self.assertEqual(self.calistir("uygula"), md.KOD_YEDEK_BOZUK)
        self.assertFalse(os.path.exists(self.o.yedek_yolu))
        self.assertEqual(self.oku(self.o.yedek_yolu + ".bozuk"), "{bozuk")
        self.assertEqual(self.masa.xfconf, BASLANGIC_XFCONF)

    def test_yazi_tipi_yoksa_dokunulmaz(self):
        self.masa.yazi_tipleri = set()
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        self.assertIsNone(self.x("xsettings", "/Gtk/FontName"))
        trc = self.oku(os.path.join(self.config, "xfce4", "terminal", "terminalrc"))
        self.assertIn("FontName=Monospace 12", trc)

    def test_terminal_xfconf_kanali_doluysa_yazilir(self):
        self.masa.xfconf[("xfce4-terminal", "/misc-default-geometry")] = "100x30"
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        self.assertEqual(self.x("xfce4-terminal", "/font-name"), "JetBrains Mono 11")
        self.assertEqual(self.x("xfce4-terminal", "/background-mode"), "TERMINAL_BACKGROUND_TRANSPARENT")
        self.assertEqual(self.calistir("geri-al"), 0)
        self.assertIsNone(self.x("xfce4-terminal", "/font-name"))
        self.assertEqual(self.x("xfce4-terminal", "/misc-default-geometry"), "100x30")

    def test_durum_ve_arguman(self):
        self.assertEqual(self.calistir("durum"), 0)
        self.assertIn("sleek uygulanmadi", self.ciktilar)
        for argv in ([], ["uygula", "fazla"], ["sil"], ["--help"]):
            self.assertEqual(md.main(argv, o=self.o, cikti=self.ciktilar.append), md.KOD_KULLANIM)

    def test_picom_gercek_makine(self):
        self.assertEqual(self.calistir("uygula"), 0)
        conf = self.oku(os.path.join(self.config, "picom", "picom.conf"))
        self.assertIn('backend = "glx";', conf)
        self.assertIn('blur-method = "dual_kawase";', conf)
        self.assertIn("fading = true;", conf)


class ModernlestirSanalMakineTesti(ModernlestirTabani):
    sanal = True

    def test_picom_sanal_makine(self):
        self.assertEqual(self.calistir("uygula"), 0, self.ciktilar)
        conf = self.oku(os.path.join(self.config, "picom", "picom.conf"))
        self.assertIn('backend = "xrender";', conf)
        self.assertNotIn("blur-method", conf)
        self.assertIn("blur-background = false;", conf)
        self.assertIn("fading = false;", conf)
        self.assertIn("corner-radius = 12;", conf)
        self.assertIn("shadow = true;", conf)
        self.assertTrue(any("sanal makine" in c for c in self.ciktilar))


# ---------------------------------------------------------------------------
# Saf fonksiyonlar
# ---------------------------------------------------------------------------

class MetinUreticiTesti(unittest.TestCase):
    def _picom_gecerli(self, conf):
        """libconfig kabaca: parantez dengesi, tirnak cifti, her atama ';' ile biter."""
        govde = "\n".join(s for s in conf.splitlines() if not s.lstrip().startswith("#"))
        self.assertEqual(govde.count("["), govde.count("]"))
        self.assertEqual(govde.count("{"), govde.count("}"))
        for s in govde.splitlines():
            self.assertEqual(s.count('"') % 2, 0, s)
            st = s.strip()
            if "=" in st and not st.startswith('"') and not st.endswith(("[", "{")) and "{" not in st:
                self.assertTrue(st.endswith(";"), s)
        for anahtar in ("corner-radius", "shadow-radius", "shadow-opacity", "rounded-corners-exclude",
                        "shadow-exclude", "wintypes"):
            self.assertIn(anahtar, govde)
        self.assertNotIn("rules", govde)                 # yeni tip kurallar eski tiple karistirilmaz
        self.assertNotIn("animations", govde)

    def test_picom_iki_varyant_gecerli(self):
        for sanal in (True, False):
            self._picom_gecerli(md.picom_conf(sanal))
        self.assertIn("class_g != 'Xfce4-terminal'", md.picom_conf(False))

    def test_css_blok_ekle_kaldir(self):
        blok = md.css_blogu()
        for ilk in ("", GTK_CSS, "son satir sonsuz", GTK_CSS + "\n\n"):
            eklenmis = md.css_blok_ekle(ilk, blok)
            self.assertTrue(eklenmis.startswith(ilk.rstrip("\n")) if ilk else eklenmis.startswith(md.CSS_BAS))
            self.assertEqual(eklenmis.count(md.CSS_BAS), 1)
            self.assertEqual(md.css_blok_ekle(eklenmis, blok), eklenmis)          # tekrar: ayni
            geri = md.css_blok_kaldir(eklenmis)
            beklenen = ilk if ilk.endswith("\n") or not ilk else ilk + "\n"
            self.assertEqual(geri, beklenen, repr(ilk))
        # blogun ardina kullanici kural eklediyse o kural kalir
        arada = md.css_blok_ekle(GTK_CSS, blok) + "label { color: blue; }\n"
        self.assertEqual(md.css_blok_kaldir(arada), GTK_CSS + "label { color: blue; }\n")

    def test_yarim_css_blogu(self):
        yarim = GTK_CSS + md.CSS_BAS + "\nx {}\n"
        with self.assertRaises(md.UygulamaHatasi):
            md.css_blok_ekle(yarim, md.css_blogu())
        self.assertEqual(md.css_blok_kaldir(yarim), yarim)

    def test_terminalrc_gidis_donus(self):
        ilk = "[Configuration]\nFontName=Mono 9\nMiscX=1\n\n[Diger]\nColorPalette=dokunma\n"
        yeni, eski = md.terminalrc_ayarla(ilk, md.TERMINALRC_ANAHTARLARI)
        self.assertEqual(eski["FontName"], "Mono 9")
        self.assertIsNone(eski["ColorPalette"])
        self.assertIn("ColorPalette=dokunma", yeni)                    # baska bolum degismez
        self.assertLess(yeni.index("ColorPalette=#"), yeni.index("[Diger]"))
        self.assertEqual(md.terminalrc_geri(yeni, eski), ilk)
        bos, eski2 = md.terminalrc_ayarla(None, md.TERMINALRC_ANAHTARLARI)
        self.assertTrue(bos.startswith("[Configuration]\n"))
        self.assertEqual(md.terminalrc_geri(bos, eski2).strip(), "[Configuration]")

    def test_desktop_exec_alintilama(self):
        self.assertEqual(md.desktop_exec_alintila("/usr/bin/picom"), "/usr/bin/picom")
        self.assertEqual(md.desktop_exec_alintila("/home/a b/$x"), '"/home/a b/\\$x"')

    def test_rofi_temasi(self):
        for dil, yer in (("tr", "Uygulama ara"), ("en", "Search apps")):
            r = md.rofi_temasi(dil)
            self.assertIn(yer, r)
            self.assertEqual(r.count("{"), r.count("}"))
            self.assertIn("#5196d6", r)

    def test_kaynak_sertligi(self):
        with open(MODERN, encoding="utf-8") as f:
            kaynak = f.read()
        self.assertTrue(kaynak.startswith("#!/usr/bin/python3 -I\n"))
        self.assertIn("sys.dont_write_bytecode = True", kaynak)
        self.assertNotIn("shell=True", kaynak)
        self.assertNotIn("os.system", kaynak)
        ortam = md.temiz_ortam(kaynak={"HOME": "/h", "LD_PRELOAD": "x", "PYTHONPATH": "y", "DISPLAY": ":0"})
        self.assertEqual(ortam["PATH"], "/usr/bin:/bin")
        self.assertNotIn("LD_PRELOAD", ortam)
        self.assertNotIn("PYTHONPATH", ortam)
        self.assertEqual(ortam["LC_ALL"], "C")


@unittest.skipUnless(POSIX, "gercek alt surec testi icin POSIX gerekir")
class GercekAltSurecTesti(unittest.TestCase):
    """xfconf-query argv bicimi gercek bir sahte programla da calisir."""

    def test_xq_oku_yaz(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        kayit = os.path.join(d, "argv.log")
        with open(os.path.join(d, "xfconf-query"), "w", encoding="utf-8") as f:
            f.write('#!/bin/sh\necho "$*" >> "%s"\ncase "$*" in *-s*) exit 0;; esac\n'
                    'printf "Value is an array with 2 items:\\n\\n1\\n2\\n"\n' % kayit)
        os.chmod(os.path.join(d, "xfconf-query"), 0o755)
        o = md.Ortam(d, bin_dizini=d)
        self.assertEqual(md.xq_oku(o, "xfce4-panel", "/panels"), (True, ["1", "2"]))
        md.xq_yaz(o, "xfce4-panel", "/panels", "dizi:int", ["1"])
        md.xq_yaz(o, "xfwm4", "/general/use_compositing", "bool", False)
        with open(kayit, encoding="utf-8") as f:
            satirlar = f.read().splitlines()
        self.assertEqual(satirlar[1], "-c xfce4-panel -p /panels -n -a -t int -s 1")
        self.assertEqual(satirlar[2], "-c xfwm4 -p /general/use_compositing -n -t bool -s false")


if __name__ == "__main__":
    unittest.main()
