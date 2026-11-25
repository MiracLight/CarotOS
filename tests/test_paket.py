#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paket Kurucu: saf mantık, pencere ve root yardımcısı (carotos-deb-kur). POSIX/GTK yoksa atlanır.

Calistirma:  xvfb-run -a python3 tests/test_paket.py
"""
import contextlib
import hashlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader

sys.dont_write_bytecode = True
KOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "includes.chroot")
_EV = tempfile.mkdtemp(prefix="paket-test-")
os.environ.update(HOME=_EV, XDG_CONFIG_HOME=os.path.join(_EV, "c"), XDG_CACHE_HOME=os.path.join(_EV, "k"))
unittest.addModuleCleanup(shutil.rmtree, _EV, True)


def yukle(ad, yol):
    y = SourceFileLoader(ad, os.path.join(KOK, *yol.split("/")))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(ad, y))
    y.exec_module(m)
    return m


deb = yukle("deb_kur", "usr/sbin/carotos-deb-kur") if os.name == "posix" else None
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    paket = yukle("paket_modulu", "opt/carotos/paket/carotos-paket.py") if deb else None
    EKRAN = Gtk.init_check()[0]
except (ImportError, ValueError):
    paket, EKRAN = None, False


class Gecici(unittest.TestCase):
    def setUp(self):
        self.d = os.path.realpath(tempfile.mkdtemp(dir=_EV))
        self.deb = os.path.join(self.d, "a b.deb")
        with open(self.deb, "wb") as f:
            f.write(b"icerik")
        self.oz = hashlib.sha256(b"icerik").hexdigest()


@unittest.skipUnless(paket, "POSIX + GTK gerekir")
class SafMantik(Gecici):
    def test_yol_coz(self):
        for arg in (self.deb, "file://" + self.deb.replace(" ", "%20"), "file://localhost" + self.deb):
            self.assertEqual(paket.yol_coz(arg), self.deb)
        self.assertEqual(paket.yol_coz("a b.deb", self.d), self.deb)
        bag = os.path.join(self.d, "bag.deb")
        os.symlink(self.deb, bag)
        self.assertEqual(paket.yol_coz(bag), self.deb)
        os.mkfifo(os.path.join(self.d, "f.deb"))
        for kotu in (None, "", "http://x/a.deb", "https://x/a.deb", "smb://x/a.deb", "file://sunucu" + self.deb,
                     "file:///a%00.deb", self.d, "/yok.deb", "/etc/passwd", "f.deb", "a\0.deb"):
            self.assertIsNone(paket.yol_coz(kotu, self.d), kotu)

    def test_bilgi_coz(self):
        b = paket.bilgi_coz("Package: ornek\nVersion: 1:2.0-1~x\nArchitecture: all\nMaintainer: A <a@b>\n"
                            "Installed-Size: 12\nDescription: kisa\n uzun‮ <b>x</b>\n .\n son\n")
        self.assertEqual((b["Package"], b["Version"], b["Installed-Size"], b["Depends"]), ("ornek", "1:2.0-1~x", 12, ""))
        self.assertEqual(b["Description"], "kisa\nuzun <b>x</b>\n\nson")
        uzun = paket.bilgi_coz("Package: a\nVersion: 1\nArchitecture: all\nMaintainer: %s\nInstalled-Size: x\n" % ("y" * 9999))
        self.assertEqual((len(uzun["Maintainer"]), uzun["Installed-Size"]), (200, 0))
        for kotu in ("", "Package: -o\nVersion: 1\nArchitecture: all\n", "Package: a\nVersion: -1\nArchitecture: all\n",
                     "Package: a\nVersion: 1\n"):
            self.assertIsNone(paket.bilgi_coz(kotu))

    def test_simulasyon_coz(self):
        self.assertEqual(paket.simulasyon_coz(0, "NOTE\nInst libx (1 Debian)\nInst a [1] (2)\nConf a (2)\n"),
                         (["libx", "a"], None))
        ekler, hata = paket.simulasyon_coz(100, "Inst z (1)\n a : Depends: yok but\nE: Unable\n")
        self.assertEqual((ekler, hata), ([], "a : Depends: yok but\nE: Unable"))
        self.assertTrue(paket.simulasyon_coz(1, "")[1])

    def test_durum_belirle(self):
        def k(a, i, b):
            return a == b if i == "eq" else int(a) > int(b)
        for kurulu, yeni, mim, bek in ((None, "1", "all", "yeni"), ("1", "2", "amd64", "guncelleme"), ("2", "2", "all", "ayni"),
                                       ("3", "2", "all", "eski"), (None, "1", "arm64", "mimari")):
            self.assertEqual(paket.durum_belirle(kurulu, yeni, mim, "amd64", k), bek)


    def test_desktop_coz(self):
        m, d = paket.magaza_yukle(), "/usr/share/applications/"
        self.assertEqual(m.desktop_coz(
            "vlc-bin: %(d)svlc.desktop\naa, bb:amd64, aa:i386: %(d)sx y.desktop\n"
            "diversion by aa from: %(d)sz.desktop\ndiversion by aa to: %(d)sz.desktop\n"
            "local diversion from: %(d)sz.desktop\n-o: %(d)sz.desktop\n"
            "cc: %(d)smimeinfo.cache\ncc: %(d)skde4/z.desktop\ncc: /opt/z.desktop\nbozuk\n" % {"d": d}),
            {"vlc-bin": [d + "vlc.desktop"], "aa": [d + "x y.desktop"], "bb": [d + "x y.desktop"]})
        self.assertEqual(m.desktop_coz(""), {})

    def test_uygulama_bul(self):
        m, yollar = paket.magaza_yukle(), []
        for ad, ek in (("gizli", "NoDisplay=true\n"), ("acik", "")):
            yollar.append(os.path.join(self.d, ad + ".desktop"))
            with open(yollar[-1], "w", encoding="utf-8") as f:
                f.write("[Desktop Entry]\nType=Application\nName=%s\nExec=/bin/true\n%s" % (ad, ek))
        self.assertIsNone(m.uygulama_bul(["/yok.desktop", yollar[0]]))
        self.assertEqual(m.uygulama_bul(yollar).get_name(), "acik")

    def test_kurulu_bilgi(self):
        m = paket.magaza_yukle()
        if shutil.which("dpkg-query"):
            self.assertTrue(m.kurulu_bilgi("dpkg")[1].isdigit())
        for ad in ("-o", "carotos-olmayan-paket", None):
            self.assertIsNone(m.kurulu_bilgi(ad))


@unittest.skipUnless(paket and EKRAN and shutil.which("dpkg-deb"), "ekran + dpkg gerekir")
class Pencere(Gecici):
    def don(self, kosul, sure=60):
        bit = time.time() + sure
        while not kosul() and time.time() < bit:
            while Gtk.events_pending():
                Gtk.main_iteration()
            time.sleep(0.02)
        self.assertTrue(kosul())

    def deb_uret(self, ad="carotos-deneme-x", mimari="all", bagimli="libc6"):
        kok = os.path.join(self.d, ad)
        os.makedirs(os.path.join(kok, "DEBIAN"))
        with open(os.path.join(kok, "DEBIAN", "control"), "w", encoding="utf-8") as f:
            f.write("Package: %s\nVersion: 1.0\nArchitecture: %s\nMaintainer: Deneme <a@example.org>\nDepends: %s\n"
                    "Installed-Size: 2048\nHomepage: https://example.org\nDescription: Deneme <b>paketi</b>\n Uzun aciklama.\n"
                    % (ad, mimari, bagimli))
        yol = os.path.join(self.d, ad + ".deb")
        subprocess.run(["dpkg-deb", "--root-owner-group", "-b", kok, yol], check=True, capture_output=True)
        return yol

    def test_pencere(self):
        p = paket.PaketPenceresi(paket.magaza_yukle())
        p.show_all()
        self.assertFalse(p.kur_dugme.get_sensitive())
        yol = self.deb_uret()
        p.ac("file://" + yol)
        self.don(lambda: p.bilgi)
        self.assertEqual((p.bilgi["durum"], p.bilgi["neden"], p.bilgi["hata"]), ("yeni", None, None))
        self.assertEqual(p.bilgi["sha256"], paket.ozet_al(yol))
        self.assertTrue(p.kur_dugme.get_sensitive())
        # onay kutusu isaretlenmeden "Kur" kapali
        goruldu = []

        def kullanici():
            d = next(w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.Dialog) and w.get_visible())
            alan = d.get_content_area().get_children()
            kutu = next(w for w in alan if isinstance(w, Gtk.CheckButton))
            ana = next(w for w in alan[alan.index(kutu) + 1].get_children() if w.get_style_context().has_class("ana"))
            goruldu.append(ana.get_sensitive())
            kutu.set_active(True)
            goruldu.append(ana.get_sensitive())
            ana.clicked()
            return False
        paket.GLib.timeout_add(300, kullanici)
        self.assertTrue(p._onay(p.bilgi))
        self.assertEqual(goruldu, [False, True])
        # islem: yardimci ve arguman sirasi; bitince durum yeniden okunur
        komutlar = []

        class Sahte:
            def __init__(self, _e, _b, komut, bitince):
                komutlar.append(komut)
                self.bitince = bitince

            def baslat(self):
                self.bitince(True)

            def calisiyor(self):
                return False
        eski = paket.YARDIMCI, paket.sistem_yolu
        paket.YARDIMCI, paket.sistem_yolu = "/bin/true", lambda ad: "/usr/bin/" + ad
        p._onay, p.magaza.IslemPenceresi = lambda _b: True, Sahte
        try:
            p._kur()
        finally:
            paket.YARDIMCI, paket.sistem_yolu = eski
        self.assertEqual(komutlar, [["/usr/bin/pkexec", "/bin/true", yol, paket.ozet_al(yol)]])
        self.don(lambda: p.bilgi)
        for ad, mimari, bagimli, neden in (("carotos-mim", "s390x", "libc6", "n_mimari"),
                                           ("carotos-bag", "all", "carotos-olmayan-paket", "n_hata"),
                                           ("dpkg", "all", "libc6", "n_eski")):
            p.ac(self.deb_uret(ad, mimari, bagimli))
            self.don(lambda: p.bilgi)
            self.assertEqual(p.bilgi["neden"], neden, ad)
            self.assertFalse(p.kur_dugme.get_sensitive())
        self.assertFalse(p.ac_dugme.get_visible())       # dpkg kurulu ama .desktop'u yok
        p.ac(self.deb)                       # .deb uzantili ama paket degil
        self.don(lambda: p._sira and p.bilgi is None and not p.kur_dugme.get_sensitive())
        self.assertIsNone(paket.incele(self.deb))
        p.destroy()


@unittest.skipUnless(deb, "POSIX gerekir")
class Yardimci(Gecici):
    def kos(self, *argv, kod=0):
        kayit, sahte = os.path.join(self.d, "kayit"), os.path.join(self.d, "apt-get")
        with open(sahte, "w", encoding="utf-8", newline="\n") as f:
            f.write('#!/bin/sh\nfor a; do echo "$a"; hedef="$a"; done > "%s"\ncat "$hedef" >> "%s"\nexit %d\n' % (kayit, kayit, kod))
        os.chmod(sahte, 0o755)
        with contextlib.redirect_stderr(io.StringIO()):
            sonuc = deb.main(list(argv), apt_get=sahte)
        return sonuc, open(kayit, encoding="utf-8").read().splitlines() if os.path.exists(kayit) else None

    def test_dogru(self):
        for kod in (0, 100):
            sonuc, satir = self.kos(self.deb, self.oz, kod=kod)
            self.assertEqual(sonuc, kod)
            self.assertEqual(satir[:len(deb.SECENEK)], deb.SECENEK)
            self.assertEqual(satir[len(deb.SECENEK):-2], ["install", "-y", "--no-remove"])
            self.assertRegex(satir[-2], r"/carotos-deb-[^/]+/paket\.deb$")
            self.assertEqual(satir[-1], "icerik")
            self.assertFalse(os.path.exists(satir[-2]))   # kopya temizlendi

    def test_red(self):
        bag, fifo, txt = (os.path.join(self.d, a) for a in ("bag.deb", "f.deb", "a.txt"))
        os.symlink(self.deb, bag)
        os.mkfifo(fifo)
        shutil.copy(self.deb, txt)
        for argv, kod in (((self.deb, "0" * 64), 65), ((bag, self.oz), 65), ((fifo, self.oz), 65),
                          ((self.d + "/yok.deb", self.oz), 65), (("a b.deb", self.oz), 64), ((txt, self.oz), 64),
                          ((self.deb, self.oz.upper()), 64), ((self.deb,), 64), ((self.deb, self.oz, "x"), 64)):
            self.assertEqual(self.kos(*argv), (kod, None), argv)

    def test_kopyala(self):
        hedef = os.path.join(self.d, "h")
        deb.kopyala(self.deb, hedef, self.oz)
        with open(hedef, "rb") as f:
            self.assertEqual(f.read(), b"icerik")
        with self.assertRaises(FileExistsError):
            deb.kopyala(self.deb, hedef, self.oz)
        with self.assertRaises(ValueError):
            deb.kopyala(self.deb, hedef + "2", "0" * 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
