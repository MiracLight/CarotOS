#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon uretec gorevleri: her uretimin cevabi, ogrencinin yapacagi isi
BAGIMSIZ yapan cozucuyle yeniden bulunur ve karsilastirilir (GTK'siz).

Bu dosya her ailenin ILK (klasik) sorusunu sinar: varyant=1. Tum varyantlar
tests/test_poligon_varyantlar.py icinde denenir.

Kullanim (depo kokunden):  python3 tests/test_poligon_uretecler.py
"""
import base64
import gzip
import io
import json
import os
import re
import socket
import subprocess
import sys
import tarfile
import unittest
import urllib.parse
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot/opt/carotos")
for _y in (os.path.join(INC, "poligon"), os.path.join(INC, "carotpot"),
           os.path.join(INC, "ortak")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import uretilen_gorevler as U  # noqa: E402

TEKRAR = 12


def yukle(yol):
    return Path(yol).read_text(encoding="utf-8")


def en_cok(sayim):
    s = sorted(sayim.items(), key=lambda kv: -kv[1])
    assert len(s) == 1 or s[0][1] > s[1][1], f"belirsiz: {s[:3]}"
    return s[0][0]


V1 = {"varyant": 1}          # her ailenin ilk varyanti = klasik soru
KOLAY = {"satir_sayisi": 200, "saldirgan_sayisi": 1, **V1}
ORTA = {"satir_sayisi": 600, "saldirgan_sayisi": 3, **V1}
ZOR = {"satir_sayisi": 2000, "saldirgan_sayisi": 5, "yakin_rakip": 1, **V1}


class GunlukUretecleri(unittest.TestCase):
    def test_ssh_saldirgan(self):
        for p in (KOLAY, ORTA, ZOR):
            for _ in range(TEKRAR):
                u = U.uret("ssh_saldirgan", p)
                try:
                    sayim = {}
                    for s in yukle(u.dosya_yolu).splitlines():
                        m = re.search(r"Failed password for .* from (\S+) port", s)
                        if m:
                            sayim[m.group(1)] = sayim.get(m.group(1), 0) + 1
                    self.assertEqual(en_cok(sayim), u.dogru_cevap)
                    self.assertGreaterEqual(len(yukle(u.dosya_yolu).splitlines()), p["satir_sayisi"] - 5)
                finally:
                    u.durdur()
                self.assertFalse(os.path.exists(u.dosya_yolu))

    def test_ssh_giren(self):
        for p in (KOLAY, ORTA, {**ZOR, "sahte_basari": 1}):
            for _ in range(TEKRAR):
                u = U.uret("ssh_giren", p)
                try:
                    satirlar = yukle(u.dosya_yolu).splitlines()
                    sayim = {}
                    for s in satirlar:
                        m = re.search(r"Failed password for .* from (\S+) port", s)
                        if m:
                            sayim[m.group(1)] = sayim.get(m.group(1), 0) + 1
                    ip = en_cok(sayim)
                    girenler = [re.search(r"Accepted password for (\S+) from " + re.escape(ip) + " ", s)
                                for s in satirlar]
                    girenler = [m.group(1) for m in girenler if m]
                    self.assertEqual(girenler, [u.dogru_cevap])
                finally:
                    u.durdur()

    def test_web_tarayici(self):
        for soru in ("ip", "yol"):
            for p in ({"satir_sayisi": 300, "tarayici_sayisi": 1, **V1},
                      {"satir_sayisi": 800, "tarayici_sayisi": 2, "arac_ua": 0, **V1},
                      {"satir_sayisi": 2000, "tarayici_sayisi": 4, "arac_ua": 0, "yakin_rakip": 1, **V1}):
                for _ in range(TEKRAR):
                    u = U.uret("web_tarayici", p, {"soru": soru})
                    try:
                        s404, s200 = {}, {}
                        for s in yukle(u.dosya_yolu).splitlines():
                            m = re.match(r'(\S+) - - \[.*?\] "GET (\S+) HTTP/1.1" (\d+) ', s)
                            ip, yol, kod = m.group(1), m.group(2), m.group(3)
                            if kod == "404":
                                s404[ip] = s404.get(ip, 0) + 1
                            elif kod == "200":
                                s200.setdefault(ip, set()).add(yol)
                        ip = en_cok(s404)
                        if soru == "ip":
                            self.assertEqual(ip, u.dogru_cevap)
                        else:
                            normal = set(U._NORMAL_YOLLAR)
                            gizli = s200[ip] - normal
                            self.assertEqual(gizli, {u.dogru_cevap})
                    finally:
                        u.durdur()

    def test_carotpot_kayit(self):
        for p in ({"saldirgan_sayisi": 3, "satir_sayisi": 120, **V1},
                  {"saldirgan_sayisi": 8, "satir_sayisi": 500, "yakin_rakip": 1, **V1}):
            for _ in range(TEKRAR):
                u = U.uret("carotpot_kayit", p, {"soru": "kullanici"})
                try:
                    sayim = {}
                    for s in yukle(u.dosya_yolu).splitlines():
                        govde = json.loads(s.split(" | ", 1)[1])
                        if govde["tur"] == "giris":
                            sayim[govde["kullanici"]] = sayim.get(govde["kullanici"], 0) + 1
                    self.assertEqual(en_cok(sayim), u.dogru_cevap)
                    self.assertIn(" CAROTPOT kaynak=", yukle(u.dosya_yolu))
                finally:
                    u.durdur()
        for p in ({"saldirgan_sayisi": 3, "taranan_hizmet": 4, **V1},
                  {"saldirgan_sayisi": 6, "taranan_hizmet": 3, "cok_olayli_rakip": 1,
                   "satir_sayisi": 400, **V1}):
            for _ in range(TEKRAR):
                u = U.uret("carotpot_kayit", p, {"soru": "tarayici"})
                try:
                    hz = {}
                    for s in yukle(u.dosya_yolu).splitlines():
                        govde = json.loads(s.split(" | ", 1)[1])
                        hz.setdefault(govde["kaynak"], set()).add(govde["hizmet"])
                    self.assertEqual(en_cok({k: len(v) for k, v in hz.items()}), u.dogru_cevap)
                finally:
                    u.durdur()


def adim_coz(veri, ad):
    return {
        "base64": base64.b64decode, "base32": base64.b32decode,
        "hex": lambda b: bytes.fromhex(b.decode()), "gzip": gzip.decompress,
        "url": lambda b: urllib.parse.unquote_to_bytes(b.decode()),
        "rot13": U._rot13,
    }[ad](veri)


class KodlamaUretecleri(unittest.TestCase):
    # kodlama_zinciri varyantlari 1-8: katman sayisi / ad bilgisi degisen "coz" sorulari
    COZ = {1: (1, "sirali"), 2: (2, "sirali"), 3: (2, "karisik"), 4: (3, "sirali"),
           5: (3, "karisik"), 6: (3, "yok"), 7: (4, "karisik"), 8: (5, "yok")}

    def test_kodlama_zinciri(self):
        for no, (n, mod) in self.COZ.items():
            for _ in range(TEKRAR * 2):
                u = U.uret("kodlama_zinciri", {"varyant": no})
                try:
                    veri = Path(u.dosya_yolu).read_bytes()
                    self.assertEqual(U.cozucu_kodlama(veri), u.dogru_cevap.encode())
                    if mod == "sirali":
                        adlar = u.degiskenler["{katmanlar}"].split(" → ")
                        self.assertEqual(len(adlar), n)
                        for a in adlar:
                            veri = adim_coz(veri, a)
                        self.assertEqual(veri, u.dogru_cevap.encode())
                    elif mod == "karisik":
                        # SIRASIZ listede ayni ad bir kez gecer: en cok n, en az 1 ad
                        self.assertTrue(1 <= len(u.degiskenler["{katmanlar}"].split(", ")) <= n)
                    self.assertRegex(u.dogru_cevap, r"^CAROT\{[0-9a-f]{8}\}$")
                finally:
                    u.durdur()

    def test_sezar_klasik(self):
        """sezar varyanti 1: kaydirma = 3 sabit."""
        sozcuk = re.compile(r"\b([a-z]+\d{4})\b")
        for _ in range(TEKRAR * 2):
            u = U.uret("sezar", {"varyant": 1})
            try:
                sifreli = yukle(u.dosya_yolu).strip()
                acik = "".join(chr((ord(c) - 97 - 3) % 26 + 97) if "a" <= c <= "z" else c
                               for c in sifreli)
                self.assertEqual(sozcuk.search(acik).group(1), u.dogru_cevap)
                self.assertIn("{soru_en}", u.degiskenler)
            finally:
                u.durdur()



class DosyaUretecleri(unittest.TestCase):
    def test_dosya_adli(self):
        for gizleme in ("strings", "gzip", "tar"):
            for _ in range(TEKRAR):
                u = U.uret("dosya_adli", {"gizleme": gizleme})
                try:
                    veri = Path(u.dosya_yolu).read_bytes()
                    self.assertTrue(u.dosya_yolu.endswith("resim.jpg"))
                    if gizleme == "strings":
                        self.assertTrue(veri.startswith(b"\xff\xd8\xff\xe0"))
                        bulunan = re.findall(rb"CAROT\{[0-9a-f]{8}\}", veri)
                    elif gizleme == "gzip":
                        self.assertEqual(veri[:2], b"\x1f\x8b")
                        bulunan = re.findall(rb"CAROT\{[0-9a-f]{8}\}", gzip.decompress(veri))
                    else:
                        t = tarfile.open(fileobj=io.BytesIO(gzip.decompress(veri)))
                        bulunan = []
                        for uye in t.getmembers():
                            bulunan += re.findall(rb"CAROT\{[0-9a-f]{8}\}", t.extractfile(uye).read())
                    self.assertEqual(bulunan, [u.dogru_cevap.encode()])
                finally:
                    u.durdur()

    def test_hash_turu(self):
        def tani(h):
            if h.startswith("$1$"):
                return "md5crypt"
            if h.startswith("$5$"):
                return "sha256crypt"
            if h.startswith("$6$"):
                return "sha512crypt"
            if h.startswith("$2"):
                return "bcrypt"
            return {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}[len(h)]
        for cesit in ("temel", "unix", "karma"):
            for n in (1, 6, 10):
                for _ in range(TEKRAR):
                    u = U.uret("hash_turu", {"cesit": cesit, "kullanici_sayisi": n})
                    try:
                        satirlar = dict(s.split(":", 1) for s in yukle(u.dosya_yolu).splitlines())
                        self.assertEqual(len(satirlar), n)
                        self.assertEqual(tani(satirlar[u.degiskenler["{hedef_kullanici}"]]),
                                         u.dogru_cevap)
                        self.assertIn(u.dogru_cevap, u.degiskenler["{hash_turleri}"])
                    finally:
                        u.durdur()


def http_al(port, yol, basliklar=None):
    istek = urllib.request.Request(f"http://127.0.0.1:{port}{yol}", headers=basliklar or {})
    try:
        with urllib.request.urlopen(istek, timeout=3) as r:
            return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


class AgUretecleri(unittest.TestCase):
    def test_gizli_sayfa(self):
        for kesif in ("robots", "sozluk", "cerez"):
            for _ in range(4):
                u = U.uret("gizli_sayfa", {"kesif": kesif})
                port = int(u.degiskenler["{port}"])
                try:
                    kod, govde, _ = http_al(port, "/robots.txt")
                    self.assertEqual(kod, 200)
                    cerez = {}
                    if kesif == "cerez":
                        _, _, bas = http_al(port, "/")
                        cerez = {"Cookie": bas["Set-Cookie"].split(";")[0]}
                    if kesif == "robots":
                        aday = re.findall(r"Disallow: /(\w+)/", govde)
                    else:
                        aday = yukle(u.degiskenler["{sozluk}"]).split()
                        self.assertGreaterEqual(len(aday), 40)
                    bayrak = None
                    for a in aday:
                        k, g, bas = http_al(port, f"/{a}/", cerez)
                        if k == 200:
                            bayrak = bas.get("X-Carot-Bayrak") or re.search(r"CAROT\{\w+\}", g).group(0)
                    self.assertEqual(bayrak, u.dogru_cevap)
                    if kesif == "cerez":
                        # cerezsiz istek reddedilir
                        sozluk_gizli = [a for a in aday
                                        if http_al(port, f"/{a}/", cerez)[0] == 200][0]
                        self.assertEqual(http_al(port, f"/{sozluk_gizli}/")[0], 403)
                    if kesif != "robots":
                        # robots.txt gizli dizini ele vermez
                        self.assertNotIn(sozluk_gizli if kesif == "cerez" else
                                         [a for a in aday if http_al(port, f"/{a}/")[0] == 200][0],
                                         govde)
                finally:
                    u.durdur()
                with self.assertRaises(OSError):
                    socket.create_connection(("127.0.0.1", port), timeout=1)

    def test_banner_avi(self):
        for mod in ("hemen", "istek"):
            for n in (3, 8):
                u = U.uret("banner_avi", {"port_sayisi": n, "mod": mod,
                                          "port_araligi": [24000, 24099]})
                try:
                    bulunan = []
                    acik = 0
                    for port in range(24000, 24100):
                        try:
                            s = socket.create_connection(("127.0.0.1", port), timeout=0.3)
                        except OSError:
                            continue
                        acik += 1
                        s.settimeout(2)
                        if mod == "istek":
                            s.sendall(b"\r\n")
                        baslik = s.recv(200).decode().strip()
                        s.close()
                        m = re.match(r"CarotBox/(\d+\.\d+\.\d+) ready", baslik)
                        if m:
                            bulunan.append(m.group(1))
                    self.assertEqual(acik, n)
                    self.assertEqual(bulunan, [u.dogru_cevap])
                finally:
                    u.durdur()

    def test_tuzak_kayit_oku(self):
        for _ in range(2):
            u = U.uret("tuzak_kayit_oku", {"saldirgan_sayisi": 4, "hizmetler": ["ftp", "telnet"]})
            try:
                komut = u.degiskenler["{rapor_komutu}"].split()
                cikti = subprocess.run(komut, capture_output=True, text=True, timeout=20).stdout
                satirlar = [s for s in cikti.splitlines() if s.startswith("  ")]
                self.assertTrue(satirlar, cikti)
                siralama = [(s.split()[0], int(s.split()[1])) for s in satirlar]
                self.assertEqual(siralama[0][0], u.dogru_cevap)
                self.assertGreater(siralama[0][1], siralama[1][1])
                self.assertTrue(siralama[0][0].startswith("127."))
            finally:
                u.durdur()
            self.assertFalse(os.path.exists(u.degiskenler["{veri_dizini}"]))

    def test_loopback_disi_adres_reddedilir(self):
        for ad in ("gizli_sayfa", "banner_avi", "tuzak_kayit_oku"):
            for adres in ("0.0.0.0", "192.168.1.5"):
                with self.assertRaises(ValueError, msg=f"{ad} {adres}"):
                    U.uret(ad, {}, bind_adres=adres)

    def test_bilinmeyen_uretec(self):
        with self.assertRaises(ValueError):
            U.uret("yok", {})


if __name__ == "__main__":
    unittest.main()
