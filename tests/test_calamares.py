#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Calamares (canlidan kurulum) yapilandirma testleri.

PyYAML yok: dosyalar satir/regex denetimiyle okunur.
Calistirma:  python3 tests/test_calamares.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(KOK, "config")
CHROOT = os.path.join(CONFIG, "includes.chroot")
CALAMARES = os.path.join(CHROOT, "etc", "calamares")
MODULLER = os.path.join(CALAMARES, "modules")
HOOK = os.path.join(CONFIG, "hooks", "live", "9979-carotos-calamares.hook.chroot")


def oku(*parca):
    with open(os.path.join(*parca), "rb") as f:
        return f.read().replace(b"\r\n", b"\n").decode("utf-8")


def kod_satirlari(metin):
    return [s for s in metin.split("\n") if s.strip() and not s.lstrip().startswith("#")]


def dizi_ogeleri(metin, bolum):
    """settings.conf'ta `- exec:` ya da `- show:` bolumunun (sira ile) `  - ad` ogeleri."""
    sonuc = []
    icinde = False
    for s in metin.split("\n"):
        if re.match(r"^- %s:\s*$" % bolum, s):
            icinde = True
            sonuc.append([])
            continue
        if icinde:
            m = re.match(r"^  - (\S+)\s*$", s)
            if m:
                sonuc[-1].append(m.group(1))
            elif s.strip() and not s.startswith("  "):
                icinde = False
    return sonuc


class SettingsTesti(unittest.TestCase):
    def setUp(self):
        self.s = oku(CALAMARES, "settings.conf")
        self.exec = dizi_ogeleri(self.s, "exec")[0]

    def test_branding_carotos(self):
        self.assertRegex(self.s, r"(?m)^branding: carotos$")

    def test_sources_final_yok(self):
        self.assertNotIn("sources-final", "\n".join(kod_satirlari(self.s)))

    def test_iki_shellprocess_ornegi_tanimli(self):
        for ad in ("carotos_once", "carotos_sonra"):
            with self.subTest(ornek=ad):
                self.assertRegex(self.s, r"(?m)^- id:\s+%s\s*$" % ad)
                self.assertRegex(self.s, r"(?m)^  module:\s+shellprocess\s*$")
                self.assertRegex(self.s, r"(?m)^  config:\s+shellprocess_%s\.conf\s*$" % ad)
                self.assertTrue(os.path.isfile(os.path.join(MODULLER, "shellprocess_%s.conf" % ad)))

    def test_sira(self):
        e = self.exec
        for ad in ("shellprocess@carotos_once", "shellprocess@carotos_sonra"):
            self.assertEqual(e.count(ad), 1, ad)
        once = e.index("shellprocess@carotos_once")
        sonra = e.index("shellprocess@carotos_sonra")
        self.assertGreater(once, e.index("unpackfs"))
        self.assertLess(once, e.index("sources-media"))
        self.assertGreater(sonra, e.index("sources-media-unmount"))
        self.assertLess(sonra, e.index("umount"))
        self.assertEqual(e[-1], "umount")

    def test_arastirma_dizisi_birebir(self):
        beklenen = ("partition mount unpackfs luksbootkeyfile dpkg-unsafe-io shellprocess@carotos_once "
                    "sources-media machineid fstab locale keyboard localecfg users displaymanager networkcfg "
                    "hwclock services-systemd bootloader-config grubcfg bootloader packages plymouthcfg "
                    "initramfscfg initramfs dpkg-unsafe-io-undo sources-media-unmount "
                    "shellprocess@carotos_sonra umount").split()
        self.assertEqual(self.exec, beklenen)

    def test_gosterim_sirasi(self):
        goster = dizi_ogeleri(self.s, "show")
        self.assertEqual(goster[0], ["welcome", "locale", "keyboard", "partition", "users", "summary"])
        self.assertEqual(goster[1], ["finished"])


class ModulTesti(unittest.TestCase):
    def test_bootloader_efi_kimligi(self):
        b = oku(MODULLER, "bootloader.conf")
        self.assertRegex(b, r'(?m)^efiBootloaderId: "debian"$')
        self.assertRegex(b, r"(?m)^installEFIFallback: false$")

    def test_users(self):
        u = oku(MODULLER, "users.conf")
        self.assertRegex(u, r"(?m)^setRootPassword: false$")
        self.assertRegex(u, r"(?m)^sudoersGroup:\s+sudo$")
        self.assertRegex(u, r"(?m)^    - sudo$")
        self.assertRegex(u, r'(?m)^    template: "carotos"$')
        self.assertRegex(u, r"(?m)^doAutologin:\s+false$")

    def test_packages_korunanlari_kaldirmaz(self):
        p = oku(MODULLER, "packages.conf")
        kaldirilan = set(re.findall(r"(?m)^        - (\S+)$", p))
        self.assertTrue({"live-boot", "live-config", "calamares-settings-debian", "calamares"} <= kaldirilan)
        for yasak in ("sudo", "systemd-sysv", "plymouth", "os-prober", "grub-pc", "grub-efi", "polkitd", "pkexec"):
            self.assertNotIn(yasak, kaldirilan)
        self.assertFalse([k for k in kaldirilan if k.startswith("carotos")], kaldirilan)
        self.assertRegex(p, r"(?m)^autoremove: false$")
        self.assertRegex(p, r"(?m)^backend: apt$")

    def test_shellprocess_adimlari(self):
        once = oku(MODULLER, "shellprocess_carotos_once.conf")
        sonra = oku(MODULLER, "shellprocess_carotos_sonra.conf")
        once_k = re.findall(r'command: "([^"]+)"', once)
        sonra_k = re.findall(r'command: "([^"]+)"', sonra)
        # once: hicbiri "-" onekli degil (tasima basarisiz olursa kurulum durur)
        self.assertTrue(once_k)
        for k in once_k:
            self.assertFalse(k.startswith("-"), k)
        self.assertTrue(any("mv /etc/apt/apt.conf.d/50carotos-kurtarma" in k for k in once_k))
        self.assertTrue(any("debian.sources" in k and k.startswith("mv ") for k in once_k))
        self.assertTrue(any("carotos.sources" in k and k.startswith("mv ") for k in once_k))
        # sonra: geri koyma adimlari "-" onekli degil
        geri = [k for k in sonra_k if k.startswith("mv ")]
        self.assertEqual(len(geri), 3)
        self.assertTrue(any(k.endswith("/etc/apt/apt.conf.d/50carotos-kurtarma") for k in geri))
        # mutlak yollar: goreli tasima/silme yok
        for k in once_k + sonra_k:
            for arac, *_ in [k.lstrip("-").split()]:
                self.assertIn(arac, ("mv", "mkdir", "rm", "test"), k)
            for yol in re.findall(r"\s(\S+/\S*)", k):
                self.assertTrue(yol.startswith("/"), k)
            self.assertNotIn("$", k)
        self.assertFalse(re.search(r"(?m)^dontChroot: true", once + sonra))

    def test_locale_zaman_dilimi(self):
        l = oku(MODULLER, "locale.conf")
        self.assertRegex(l, r'(?m)^region: "Europe"$')
        self.assertRegex(l, r'(?m)^zone:\s+"Istanbul"$')
        self.assertRegex(l, r'(?m)^    style: "none"$')

    def test_partition(self):
        p = oku(MODULLER, "partition.conf")
        self.assertRegex(p, r"(?m)^luksGeneration: luks1$")
        self.assertRegex(p, r'(?m)^defaultFileSystemType: "ext4"$')
        self.assertRegex(p, r'(?m)^efiSystemPartition: "/boot/efi"$')

    def test_yaml_baslangici(self):
        for ad in os.listdir(MODULLER):
            with self.subTest(modul=ad):
                self.assertIn("\n---\n", "\n" + oku(MODULLER, ad))
                self.assertNotIn("\t", oku(MODULLER, ad))
        self.assertIn("\n---\n", "\n" + oku(CALAMARES, "settings.conf"))

    def test_welcome_internet_zorunlu_degil(self):
        w = oku(MODULLER, "welcome.conf")
        zorunlu = w.split("required:")[1]
        self.assertNotIn("internet", zorunlu)


class PaketListesiTesti(unittest.TestCase):
    def test_imzali_paketler_hicbir_listede_yok(self):
        d = os.path.join(CONFIG, "package-lists")
        for ad in os.listdir(d):
            kod = "\n".join(kod_satirlari(oku(d, ad)))
            with self.subTest(liste=ad):
                self.assertNotIn("shim-signed", kod)
                self.assertNotIn("grub-efi-amd64-signed", kod)

    def test_calamares_listesi(self):
        paketler = {s.strip() for s in kod_satirlari(oku(CONFIG, "package-lists", "calamares.list.chroot"))}
        self.assertIn("calamares-settings-debian", paketler)
        self.assertIn("sudo", paketler)


class SarmalayiciTesti(unittest.TestCase):
    def setUp(self):
        self.yol = os.path.join(CHROOT, "usr", "bin", "carotos-kur")
        self.k = oku(self.yol)

    def test_eval_yok(self):
        kod = "\n".join(kod_satirlari(self.k))
        self.assertNotRegex(kod, r"\beval\b")

    def test_medium_denetimi(self):
        self.assertIn("MEDIUM=/run/live/medium", self.k)
        self.assertRegex(self.k, r'\[ ! -d "\$MEDIUM" \]')

    def test_set_eu_ve_pkexec_env(self):
        self.assertTrue(self.k.startswith("#!/bin/bash\n"))
        self.assertRegex(self.k, r"(?m)^set -eu$")
        self.assertIn("/usr/bin/pkexec /usr/bin/env", self.k)
        for d in ("LANG=", "LC_ALL=", "LANGUAGE="):
            self.assertIn(d, self.k)
        self.assertIn(r"^[A-Za-z_]+(\.[A-Za-z0-9-]+)?(@[a-z]+)?$", self.k)
        self.assertIn("xhost +si:localuser:root", self.k)

    def test_ekran_aktarilir(self):
        # pkexec ortami temizler; DISPLAY aktarilmazsa Calamares "could not connect to display" ile coker
        self.assertIn('"DISPLAY=$EKRAN_T"', self.k)
        self.assertIn('ortam+=("XAUTHORITY=$XAUTH_T")', self.k)
        self.assertIn('pkexec /usr/bin/env "${ortam[@]}"', self.k)

    @unittest.skipIf(shutil.which("bash") is None, "bash yok")
    def test_ekran_temizleme(self):
        bas = self.k.index("temiz_ekran()")
        son = self.k.index('if [ ! -d "$MEDIUM" ]')
        betik = "set -eu\n" + self.k[bas:son] + 'temiz_ekran "$1"\n'
        for deger, beklenen in ((":0", ":0"), (":1.0", ":1.0"), ("", ""),
                                ("evil:0", ""), (":0;id", ""), ("localhost:10.0", "")):
            with self.subTest(deger=deger):
                r = subprocess.run([shutil.which("bash"), "-c", betik, "x", deger],
                                   capture_output=True, timeout=30)
                self.assertEqual(r.stdout.decode(), beklenen)

    def test_debian_modul_yolu(self):
        # Yolu eksik olunca canlida "Calamares Initialization Failed" (dpkg-unsafe-io vb. yuklenemez)
        ayar = oku(CALAMARES, "settings.conf")
        self.assertRegex(ayar, r"(?m)^modules-search: \[ local, /usr/lib/calamares/modules \]$")
        self.assertIn("/usr/lib/calamares/modules/$m/module.desc", oku(HOOK))

    def test_baglanti_araci_kullanici_tarayicisi(self):
        # Calamares (root) baglantiyi xdg-open ile acar; root Firefox oturumda acilmaz
        self.assertIn("PATH=/usr/lib/carotos/kur-bin:$PATH /usr/bin/calamares", self.k)
        arac = oku(CHROOT, "usr", "lib", "carotos", "kur-bin", "xdg-open")
        self.assertTrue(arac.startswith("#!/bin/sh\n"))
        self.assertIn('runuser -u "$kullanici"', arac)
        self.assertIn("env -i", arac)
        self.assertNotRegex("\n".join(kod_satirlari(arac)), r"\beval\b")
        sonra = oku(MODULLER, "shellprocess_carotos_sonra.conf")
        self.assertIn("rm -rf /usr/lib/carotos/kur-bin", sonra)

    @unittest.skipIf(shutil.which("sh") is None, "sh yok")
    def test_baglanti_araci_reddeder(self):
        yol = os.path.join(CHROOT, "usr", "lib", "carotos", "kur-bin", "xdg-open")
        betik = oku(yol)
        sh = shutil.which("sh")
        self.assertEqual(subprocess.run([sh, "-n"], input=betik.encode(), timeout=30).returncode, 0)
        durumlar = [
            ("file:///etc/shadow", {"PKEXEC_UID": "1000", "DISPLAY": ":0"}),
            ("https://ornek.org", {"DISPLAY": ":0"}),                       # PKEXEC_UID yok
            ("https://ornek.org", {"PKEXEC_UID": "0", "DISPLAY": ":0"}),    # root'a acmaz
            ("https://ornek.org", {"PKEXEC_UID": "1x", "DISPLAY": ":0"}),
            ("https://ornek.org x", {"PKEXEC_UID": "1000", "DISPLAY": ":0"}),
            ("https://ornek.org", {"PKEXEC_UID": "1000", "DISPLAY": "evil:0"}),
        ]
        for url, ortam in durumlar:
            with self.subTest(url=url, ortam=ortam):
                r = subprocess.run([sh, "-c", betik, "xdg-open", url], env=ortam,
                                   capture_output=True, timeout=30)
                self.assertNotEqual(r.returncode, 0)

    def test_klavye_adimi(self):
        # Klavye yalniz Calamares'te secilir; secim canliya ve kurulu sisteme yazilir
        k = oku(MODULLER, "keyboard.conf")
        self.assertRegex(k, r"(?m)^writeEtcDefaultKeyboard: true$")
        self.assertRegex(k, r'(?m)^xOrgConfFileName: "/etc/X11/xorg.conf.d/00-keyboard.conf"$')
        self.assertRegex(k, r"(?m)^guessLayout: true$")
        self.assertRegex(k, r"(?m)^useLocale1: false$")
        self.assertIn("/etc/calamares/modules/keyboard.conf", oku(HOOK))
        ayar = oku(CALAMARES, "settings.conf")
        self.assertRegex(ayar, r"(?s)- show:.*?- keyboard.*?- exec:.*?- keyboard")
        liste = oku(os.path.dirname(CHROOT), "package-lists", "calamares.list.chroot")
        self.assertRegex(liste, r"(?m)^console-setup$")      # /usr/bin/ckbcomp trixie: console-setup

    def test_xcb_cursor_paketi(self):
        liste = oku(os.path.dirname(CHROOT), "package-lists", "calamares.list.chroot")
        self.assertRegex(liste, r"(?m)^libxcb-cursor0$")

    @unittest.skipIf(shutil.which("bash") is None, "bash yok")
    def test_bash_sozdizimi(self):
        for ad in ("carotos-kur", "carotos-kur-simge"):
            with self.subTest(betik=ad):
                bash = shutil.which("bash")
                r = subprocess.run([bash, "-n"], input=oku(CHROOT, "usr", "bin", ad).encode(),
                                   capture_output=True, timeout=30)
                self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))

    @unittest.skipIf(shutil.which("bash") is None, "bash yok")
    def test_yerel_temizleme(self):
        # temiz_yerel / temiz_dil_listesi islevleri ayri calistirilir
        kaynak = self.k
        bas = kaynak.index("YEREL_RE=")
        son = kaynak.index('if [ ! -d "$MEDIUM" ]')
        parca = kaynak[bas:son]
        betik = "set -eu\n" + parca + """
temiz_yerel "$1"; printf '|'; temiz_dil_listesi "$2" "C.UTF-8"
"""
        def calistir(a, b):
            r = subprocess.run([shutil.which("bash"), "-c", betik, "x", a, b], capture_output=True, timeout=30)
            self.assertEqual(r.returncode, 0, r.stderr.decode())
            return r.stdout.decode()
        self.assertEqual(calistir("tr_TR.UTF-8", "tr:en_US"), "tr_TR.UTF-8|tr:en_US")
        self.assertEqual(calistir("de_DE.UTF-8@euro", "de"), "de_DE.UTF-8@euro|de")
        self.assertEqual(calistir("$(id)", "x;y"), "C.UTF-8|C.UTF-8")
        self.assertEqual(calistir("tr_TR.UTF-8; rm -rf /", ""), "C.UTF-8|C.UTF-8")
        self.assertEqual(calistir("", "en"), "C.UTF-8|en")

    def test_simge_betigi_yalniz_canli(self):
        s = oku(CHROOT, "usr", "bin", "carotos-kur-simge")
        self.assertIn("/run/live/medium", s)
        self.assertIn("metadata::trusted true", s)
        self.assertNotIn("eval", s)
        self.assertFalse(os.path.exists(os.path.join(CHROOT, "etc", "skel", "Desktop", "carotos-kur.desktop")))
        a = oku(CHROOT, "etc", "xdg", "autostart", "carotos-kur-simge.desktop")
        self.assertIn("Exec=/usr/bin/carotos-kur-simge", a)

    def test_desktop_dosyasi_sekiz_ceviri(self):
        d = oku(CHROOT, "usr", "share", "applications", "carotos-kur.desktop")
        self.assertIn("Icon=carotos-kur", d)
        self.assertIn("Exec=/usr/bin/carotos-kur", d)
        self.assertRegex(d, r"(?m)^Name=Install CarotOS$")
        self.assertRegex(d, r"(?m)^Name\[tr\]=CarotOS'u Kur$")
        for dil in ("tr", "de", "ru", "es", "pt", "ja", "zh", "fr", "ar", "hi"):
            with self.subTest(dil=dil):
                self.assertRegex(d, r"(?m)^Name\[%s\]=\S.*$" % dil)

    def test_simge_boyutlari(self):
        for b in (16, 22, 24, 32, 48, 64, 128, 256):
            yol = os.path.join(CHROOT, "usr", "share", "icons", "hicolor", "%dx%d" % (b, b), "apps", "carotos-kur.png")
            with self.subTest(boyut=b):
                with open(yol, "rb") as f:
                    self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")


class MarkaTesti(unittest.TestCase):
    def test_surum_surum_json_ile_ayni(self):
        with open(os.path.join(KOK, "surum.json"), encoding="utf-8") as f:
            surum = json.load(f)["dagitim"]["surum"]
        b = oku(CALAMARES, "branding", "carotos", "branding.desc")
        self.assertRegex(b, r'(?m)^    version:\s+"%s"$' % re.escape(surum))
        self.assertRegex(b, r'(?m)^    shortVersion:\s+"%s"$' % re.escape(surum))
        self.assertRegex(b, r"(?m)^    versionedName:\s+CarotOS %s$" % re.escape(surum))
        self.assertRegex(b, r"(?m)^    productName:\s+CarotOS$")
        self.assertRegex(b, r"(?m)^componentName:\s+carotos$")
        self.assertRegex(b, r'(?m)^slideshow:\s+"show\.qml"$')
        self.assertNotRegex("\n".join(kod_satirlari(b)), r"(?i)debian")

    def test_branding_dosyalari(self):
        d = os.path.join(CALAMARES, "branding", "carotos")
        for ad in ("branding.desc", "show.qml", "logo.png", "welcome.png"):
            self.assertTrue(os.path.isfile(os.path.join(d, ad)), ad)
        self.assertFalse(os.path.exists(os.path.join(CALAMARES, "branding", "debian")))

    def test_yan_panel_renkleri_33(self):
        # Calamares 3.3 buyuk harfli anahtarlari okur; kucuk harfliler yok sayilir (siyah yazi kalir)
        b = oku(CALAMARES, "branding", "carotos", "branding.desc")
        for anahtar in ("SidebarBackground", "SidebarText", "SidebarTextCurrent", "SidebarBackgroundCurrent"):
            self.assertRegex(b, r'(?m)^    %s:\s+"#[0-9a-fA-F]{6}"$' % anahtar)
        self.assertNotRegex(b, r"(?m)^    sidebar[A-Z]")
        self.assertRegex(b, r"(?m)^welcomeStyleCalamares:\s+false$")

    def test_slayt_turkce_ingilizce(self):
        q = oku(CALAMARES, "branding", "carotos", "show.qml")
        # Dil yuklemede degil etkinlestirmede okunur (Karsilama'da secilen dil)
        self.assertRegex(q, r"function onActivate\(\) \{ diliOku\(\);")
        self.assertIn('=== "tr"', q)
        # Diger diller slayt-dilleri.js'te: her metnin 9 dilde karsiligi var
        js = oku(CALAMARES, "branding", "carotos", "slayt-dilleri.js")
        tablo = json.loads(js[js.index("{"):js.index("};") + 1])
        metinler = set(re.findall(r'\bt\("[^"]*",\s*"([^"]*)"\)', q))
        self.assertGreater(len(metinler), 25)
        for kod in ("de", "ru", "es", "pt", "ja", "zh", "fr", "ar", "hi"):
            self.assertEqual(metinler - set(tablo[kod]), set(), kod)
        self.assertNotRegex(q, r"\b(de|ru|ja|zh|fr|es|pt):\s*\"")
        self.assertEqual(q.count("{"), q.count("}"))
        self.assertEqual(q.count("("), q.count(")"))
        # Beyaz kenar kalmasin: tam ekran zemin
        self.assertRegex(q, r"id: zemin\s+anchors\.fill: parent\s+z: -1")

    def test_slayt_sayisi_ve_simgeler(self):
        d = os.path.join(CALAMARES, "branding", "carotos")
        q = oku(d, "show.qml")
        self.assertGreaterEqual(len(re.findall(r"(?m)^    CarotSlayt \{$", q)), 10)
        # Slaytin kullandigi her simge branding dizininde olmali (sistem simge yoluna baglanmaz)
        adlar = set(re.findall(r'"((?:s-[a-z]+|logo)\.png)"', q))
        self.assertIn("s-panel.png", adlar)
        for ad in adlar:
            with self.subTest(simge=ad):
                yol = os.path.join(d, ad)
                self.assertTrue(os.path.isfile(yol), ad)
                with open(yol, "rb") as f:
                    self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")
        self.assertNotIn("/usr/share/icons", q)
        self.assertIn("toLocaleUpperCase()", q)

    def test_qml_kenar_cubugu(self):
        # Widget kenar cubugu logoyu 80x80 sabit cizer (orantisiz); kendi QML kenar cubugumuz
        d = os.path.join(CALAMARES, "branding", "carotos")
        self.assertRegex(oku(d, "branding.desc"), r"(?m)^sidebar:\s+qml$")
        k = oku(d, "calamares-sidebar.qml")
        self.assertIn("import io.calamares.core 1.0", k)
        self.assertIn("model: ViewManager", k)
        self.assertIn("ViewManager.currentStepIndex", k)
        self.assertIn("text: display", k)
        self.assertIn('source: "logo.png"', k)
        self.assertIn("debug.about()", k)
        self.assertNotIn("Branding.", k)                       # enum adlarina baglanmaz
        self.assertEqual(k.count("{"), k.count("}"))
        self.assertIn("calamares-sidebar.qml", oku(HOOK))

    def test_qml_surumleri_qt6(self):
        # Qt 6.8 ozellikleri ithal surumune gore acar: "QtQuick 2.0" ile Image.mipmap reddedilir,
        # dosya hic yuklenmez (canlida bos/beyaz slayt alani). Kenar cubugu ViewManager'i ui'dan alir.
        d = os.path.join(CALAMARES, "branding", "carotos")
        for ad in ("show.qml", "calamares-sidebar.qml"):
            with self.subTest(dosya=ad):
                m = re.search(r"(?m)^import QtQuick (\d+)\.(\d+)", oku(d, ad))
                self.assertIsNotNone(m)
                self.assertGreaterEqual((int(m.group(1)), int(m.group(2))), (2, 15))
        self.assertIn("import io.calamares.ui 1.0", oku(d, "calamares-sidebar.qml"))

    def test_stil_dosyasi(self):
        d = os.path.join(CALAMARES, "branding", "carotos")
        q = oku(d, "stylesheet.qss")
        self.assertRegex(q, r"(?s)QWidget \{\s+background-color: #e9edf5;\s+color: #1c2236;")
        # Stil verilen onay kutusu/radyo dugmesi Fusion'da isaretsiz kaliyor: kural yazilmaz
        self.assertNotRegex(q, r"(?m)^\s*QCheckBox|^\s*QRadioButton")
        self.assertIn('url("/etc/calamares/branding/carotos/s-destek.png")', q)
        self.assertTrue(os.path.isfile(os.path.join(d, "s-destek.png")))
        self.assertEqual(q.count("{"), q.count("}"))
        self.assertIn("stylesheet.qss", oku(HOOK))

    def test_dil_listesi_yazi_tipleri(self):
        liste = oku(os.path.dirname(CHROOT), "package-lists", "calamares.list.chroot")
        for paket in ("fonts-lohit-deva", "fonts-lohit-mlym", "fonts-lklug-sinhala", "fonts-tlwg-garuda-ttf"):
            self.assertRegex(liste, r"(?m)^%s$" % re.escape(paket))

    def test_yeni_dosyalar_lf(self):
        for kok, _, dosyalar in os.walk(CALAMARES):
            for ad in dosyalar:
                if ad.endswith((".conf", ".desc", ".qml")):
                    with open(os.path.join(kok, ad), "rb") as f:
                        self.assertNotIn(b"\r", f.read(), ad)


class HookTesti(unittest.TestCase):
    def test_hook_var_ve_sozdizimi(self):
        self.assertTrue(os.path.isfile(HOOK))
        veri = oku(HOOK)
        self.assertTrue(veri.startswith("#!/bin/sh\nset -e\n"))
        sh = shutil.which("sh")
        if sh:
            r = subprocess.run([sh, "-n"], input=veri.encode(), capture_output=True, timeout=30)
            self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))

    def test_hook_icerigi(self):
        veri = oku(HOOK)
        for parca in ("calamares yapilandirmasi yerlestirildi", "command -v calamares",
                      "/usr/bin/calamares-install-debian", "/usr/bin/add-calamares-desktop-icon",
                      "/etc/xdg/autostart/calamares-desktop-icon.desktop",
                      "/usr/share/applications/calamares-install-debian.desktop",
                      "sources-final", "efiBootloaderId"):
            self.assertIn(parca, veri)

    def test_hook_git_dizininde_calistirilabilir(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("git yok")
        r = subprocess.run([git, "ls-files", "-s", "--",
                            "config/hooks/live/9979-carotos-calamares.hook.chroot",
                            "config/includes.chroot/usr/bin/carotos-kur",
                            "config/includes.chroot/usr/bin/carotos-kur-simge"],
                           cwd=KOK, capture_output=True, text=True, timeout=30)
        satirlar = [s for s in r.stdout.splitlines() if s.strip()]
        if len(satirlar) != 3:
            self.skipTest("dosyalar git dizininde degil (git add yapilmamis)")
        for s in satirlar:
            self.assertTrue(s.startswith("100755"), s)

    def test_9999_calamares_yollarini_denetler(self):
        v = oku(CONFIG, "hooks", "live", "9999-carotos-setup.hook.chroot")
        self.assertGreaterEqual(v.count("/etc/calamares /usr/share/calamares"), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
