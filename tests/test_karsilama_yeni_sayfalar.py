#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Karşılama yeni konu sayfaları (Komut Açıklayıcı, Etik, Disk şifreleme): iki dilli, kodla tutarlı (GTK'siz).

Sayfalardaki somut iddialar (kısayol, günlük yolu, denetim adı, düğme etiketi, komut) koddaki gerçeklerle eşleşmeli.

Calistirma:  python3 tests/test_karsilama_yeni_sayfalar.py
"""
import ast
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
WELCOME = os.path.join(INC, "opt", "carotos", "welcome", "carotos-welcome.py")
sys.path.insert(0, os.path.join(INC, "opt", "carotos", "welcome"))
import gezinme  # noqa: E402


YENI = ("acikla", "etik", "disk", "dogrula", "windows")


def sayfalar():
    with open(WELCOME, "rb") as f:
        agac = ast.parse(f.read().decode("utf-8"))
    for n in agac.body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "PAGES" and isinstance(n.value, ast.List):
            # Bazi sayfalarda f-string var (literal_eval edemez): yalniz yeni sayfalar degerlendirilir
            sonuc = {}
            for e in n.value.elts:
                kimlik = dict(zip([k.value for k in e.keys], e.values))["id"].value
                if kimlik in YENI:
                    sonuc[kimlik] = ast.literal_eval(e)
            return sonuc
    raise AssertionError("PAGES yok")


def metinler(sayfa):
    cikti = [sayfa["title"], sayfa["subtitle"]]
    for tur, yuk in sayfa["body"]:
        if tur in ("p", "note"):
            cikti.append(yuk)
        elif tur == "bullets":
            cikti.extend(yuk)
    return cikti


def tum_metin(sayfa, dil):
    return "\n".join(m[dil] for m in metinler(sayfa)) + "\n" + "\n".join(
        y for t, y in sayfa["body"] if t == "code")


def oku(*yol):
    with open(os.path.join(INC, *yol), encoding="utf-8") as f:
        return f.read()



class YeniSayfaTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = sayfalar()

    def test_sayfalar_var_ve_konulara_bagli(self):
        for kimlik in YENI:
            self.assertIn(kimlik, self.s)
            self.assertTrue(any(kimlik in k["sayfalar"] for k in gezinme.KONULAR), kimlik)

    def test_iki_dilli_ve_dolu(self):
        for kimlik in YENI:
            for m in metinler(self.s[kimlik]):
                with self.subTest(sayfa=kimlik):
                    self.assertEqual(set(m), {"tr", "en"})
                    self.assertTrue(m["tr"].strip() and m["en"].strip())

    def test_yer_tutucu_ya_da_ham_kacis_kalmadi(self):
        for kimlik in YENI:
            for dil in ("tr", "en"):
                metin = tum_metin(self.s[kimlik], dil)
                self.assertNotIn("\\\"", metin, f"{kimlik}/{dil}: kacis dizisi metne sizmis")

    def test_komut_aciklayici_iddialari(self):
        for dil in ("tr", "en"):
            self.assertIn("Alt+E", tum_metin(self.s["acikla"], dil))
        bash = oku("usr", "share", "carotos", "acikla.bash")
        self.assertIn(r'"\ee"', bash)                               # Alt+E = ESC e
        self.assertTrue(os.path.isfile(os.path.join(INC, "usr", "local", "bin", "carotos-acikla")))
        kodlar = [y for t, y in self.s["acikla"]["body"] if t == "code"]
        self.assertIn("carotos-acikla tar xzf arsiv.tar.gz", kodlar)
        self.assertIn("sudo ufw status verbose", kodlar)

    def test_etik_iddialari(self):
        panel = oku("opt", "carotos", "security-panel", "carotos-security-panel.py")
        self.assertIn('ETIK_GUNLUGU = os.path.join(CONFIG_DIR, "etik-gunlugu.log")', panel)
        self.assertIn('"carotos-panel"', panel)                      # CONFIG_DIR = ~/.config/carotos-panel
        for dil in ("tr", "en"):
            metin = tum_metin(self.s["etik"], dil)
            self.assertIn("~/.config/carotos-panel/etik-gunlugu.log", metin)
            self.assertIn("127.0.0.1", metin)
            for arac in ("nmap", "nikto", "sqlmap", "hydra"):
                self.assertIn(arac, metin)
            # kendi etik metnimiz: yasa/madde atfi yok
            self.assertIsNone(re.search(r"\b(TCK|StGB|CFAA|Art\.|madde \d|§)", metin))

    def test_disk_iddialari(self):
        saglik = oku("opt", "carotos", "health", "carotos-health.py")
        self.assertIn('"title": {"tr": "Swap şifreleme", "en": "Swap encryption"}', saglik)
        self.assertIn("Disk swap\\'ını kapat", saglik)              # eylem etiketi
        metin_tr = tum_metin(self.s["disk"], "tr")
        self.assertIn("Swap şifreleme", metin_tr)
        self.assertIn("Disk swap'ını kapat", metin_tr)
        self.assertIn("Disable disk swap", tum_metin(self.s["disk"], "en"))
        zram = oku("etc", "systemd", "zram-generator.conf.d", "90-carotos.conf")
        self.assertIn("swap-priority", zram)


    def test_windows_iddialari(self):
        # sayfadaki 30/5 sn, os-prober ve saat komutu koddaki ayarlarla ayni olmali
        sure = oku("etc", "grub.d", "99_carotos_sure")
        self.assertIn("SURE_TEK=${CAROT_SURE_TEK:-5}", sure)
        self.assertIn("SURE_COK=${CAROT_SURE_COK:-30}", sure)
        cfg = oku("etc", "default", "grub.d", "carotos.cfg")
        self.assertIn("GRUB_DISABLE_OS_PROBER=false", cfg)
        with open(os.path.join(KOK, "config", "package-lists", "carotos.list.chroot"), encoding="utf-8") as f:
            self.assertIn("os-prober", f.read().split())
        for dil, (cok, tek) in (("tr", ("30 saniye", "5 saniye")), ("en", ("30 seconds", "5 seconds"))):
            metin = tum_metin(self.s["windows"], dil)
            self.assertIn(cok, metin)
            self.assertIn(tek, metin)
            self.assertIn("BitLocker", metin)
        kodlar = [y for t, y in self.s["windows"]["body"] if t == "code"]
        self.assertEqual(kodlar, ["sudo timedatectl set-local-rtc 1 --adjust-system-clock"])

    def test_dogrula_iddialari(self):
        kodlar = [y for t, y in self.s["dogrula"]["body"] if t == "code"]
        anahtar = "/usr/share/keyrings/carotos-archive-keyring.gpg"
        self.assertIn("gpgv --keyring %s SHA256SUMS.sign SHA256SUMS" % anahtar, kodlar)
        self.assertIn("sha256sum -c SHA256SUMS --ignore-missing", kodlar)
        # anahtar yolu, ISO'ya giren keyring paketinin getirdigi yol
        self.assertTrue(os.path.isfile(os.path.join(KOK, "tools", "apt", "keyring-paketi") + anahtar))
        # imzalama betigi ayni dosya adlarini uretir
        with open(os.path.join(KOK, "tools", "iso", "imzala-iso.sh"), encoding="utf-8") as f:
            betik = f.read()
        self.assertIn("SHA256SUMS.sign", betik)
        self.assertIn("> SHA256SUMS", betik)


class KonuKartiTesti(unittest.TestCase):
    def test_konular_ve_sayfa_sayilari(self):
        konular = {k["id"]: k["sayfalar"] for k in gezinme.KONULAR}
        self.assertEqual(konular["arac"], ["panel", "tools", "terminal", "acikla"])
        self.assertEqual(konular["etik"], ["etik"])
        self.assertEqual(konular["gizlilik"], ["network", "disk"])
        self.assertEqual(konular["sistem"][-1], "windows")
        self.assertEqual(konular["koruma"][-1], "dogrula")

    def test_her_sayfa_tam_bir_konuda(self):
        sayac = {}
        for k in gezinme.KONULAR:
            for s in k["sayfalar"]:
                sayac[s] = sayac.get(s, 0) + 1
        self.assertTrue(all(v == 1 for v in sayac.values()))


if __name__ == "__main__":
    unittest.main()
