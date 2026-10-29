#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon soru varyantlari.

Her uretec ailesinin HER varyanti, kolay/orta/zor ayarlariyla uretilir ve
cevap, ogrencinin yapacagi isi BAGIMSIZ yapan bir cozucuyle yeniden bulunur
(uretecin kendi hesabina guvenilmez). Ayrica ogretmen tarafi (varyant secimi,
tekrar etmeme, sinifa duyuru) denenir. GTK'siz.

Kullanim (depo kokunden):  python3 tests/test_poligon_varyantlar.py
"""
import base64
import codecs
import collections
import gzip
import json
import os
import re
import sys
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

import ogretmen_sunucu as OS  # noqa: E402
import soru_sablonlari as SS  # noqa: E402
import uretilen_gorevler as U  # noqa: E402
import varyantlar as V  # noqa: E402

GOREVLER = Path(INC) / "poligon" / "gorevler"
ZORLUKLAR = ("kolay", "orta", "zor")

# (gorev id) -> (varyant kayit anahtari, uretec, sabit parametreler)
GUNLUK_GOREVLER = {
    "loganaliz-01": "ssh",
    "loganaliz-02": "ssh",
    "loganaliz-03": "web",
    "loganaliz-04": "web",
    "loganaliz-05": "cp",
    "loganaliz-06": "cp",
}


def gorev_json(gid):
    return json.loads((GOREVLER / f"{gid}.json").read_text(encoding="utf-8"))


def uret(gid, zorluk, no):
    """Ogrenci istemcisinin yaptigi gibi: zorluk on-ayari + varyant + _zorluk."""
    g = gorev_json(gid)
    fu = g["flag_uretimi"]
    p = dict(g["zorluklar"][zorluk])
    p.update({"varyant": no, "_zorluk": zorluk})
    return U.uret(fu["uretec"], p, fu.get("sabit_parametreler"))


def tek_en_cok(sayac, ikinci=False):
    """En cok (ya da ikinci en cok) gecen anahtar; esitlik varsa test basarisiz."""
    sirali = sayac.most_common()
    i = 1 if ikinci else 0
    assert len(sirali) > i + 1 or (len(sirali) == i + 1 and not ikinci) or ikinci is False
    if len(sirali) > i + 1:
        assert sirali[i][1] > sirali[i + 1][1], f"esitlik: {sirali[:4]}"
    return sirali[i][0]


# ----------------------------------------------------------------------------
# Bagimsiz cozuculer
# ----------------------------------------------------------------------------

def ssh_coz(tur, satirlar, bicim):
    def saat(s):
        if bicim == "iso":
            return s.split("T")[1][:8]
        return s.split()[2]               # "Oct 27 19:32:33 ..."

    fails, accs = [], []
    for s in satirlar:
        m = re.search(r"Failed password for (invalid user )?(\S+) from ([0-9.]+) port (\d+)", s)
        if m:
            fails.append((m.group(2), m.group(3), saat(s)))
        m = re.search(r"Accepted (\w+) for (\S+) from ([0-9.]+) port (\d+)", s)
        if m:
            accs.append((m.group(1), m.group(2), m.group(3), m.group(4), saat(s)))
    ips = collections.Counter(f[1] for f in fails)
    ust = tek_en_cok(ips)

    def giris():
        g = [a for a in accs if a[0] == "password" and a[2] == ust]
        assert len(g) == 1, g
        return g[0]

    if tur == "ip_en_cok":
        return ust
    if tur == "sayi_en_cok":
        return str(ips[ust])
    if tur == "farkli_ip":
        return str(len(ips))
    if tur == "toplam_basarisiz":
        return str(len(fails))
    if tur == "gecersiz_kullanici":
        return str(sum(1 for s in satirlar if re.search(r"Failed password for invalid user ", s)))
    if tur == "kullanici_en_cok":
        return tek_en_cok(collections.Counter(f[0] for f in fails))
    if tur == "kullanici_cesidi":
        return str(len({f[0] for f in fails if f[1] == ust}))
    if tur == "ikinci_ip":
        return tek_en_cok(ips, ikinci=True)
    if tur == "ilk_zaman":
        return next(f[2] for f in fails if f[1] == ust)
    if tur == "saat_en_cok":
        return tek_en_cok(collections.Counter(f[2][:2] for f in fails))
    if tur == "hesap":
        return giris()[1]
    if tur == "basarili_toplam":
        return str(len(accs))
    if tur == "parola_girisi":
        return str(sum(1 for a in accs if a[0] == "password"))
    if tur == "anahtar_girisi":
        return str(sum(1 for a in accs if a[0] == "publickey"))
    if tur == "giris_zamani":
        return giris()[4]
    if tur == "giris_port":
        return giris()[3]
    if tur == "giris_oncesi":
        return str(ips[giris()[2]])
    if tur == "hesap_ve_ip":
        return f"{giris()[2]}:{giris()[1]}"
    if tur == "oturum_sayisi":
        return str(sum(1 for s in satirlar if "session opened for user" in s))
    raise AssertionError(f"cozucu yok: {tur}")


ARAC_ADLARI = ("Nikto", "sqlmap", "gobuster", "DirBuster", "Wfuzz", "python-requests")


def web_oku(satirlar, bicim):
    kayitlar = []
    for s in satirlar:
        if bicim == "json":
            o = json.loads(s)
            kayitlar.append(dict(ip=o["ip"], saat=o["ts"].split("T")[1][:8], yol=o["path"],
                                 kod=o["status"], boyut=o["bytes"], ua=o["ua"]))
        else:
            m = re.match(r'(\S+) \S+ \S+ \[\d+/\w+/\d+:(\d\d:\d\d:\d\d) \S+\] "\w+ (\S+) [^"]*" '
                         r'(\d+) (\d+) "[^"]*" "(.*)"$', s)
            assert m, s
            kayitlar.append(dict(ip=m.group(1), saat=m.group(2), yol=m.group(3),
                                 kod=int(m.group(4)), boyut=int(m.group(5)), ua=m.group(6)))
    return kayitlar


def web_coz(tur, satirlar, bicim):
    k = web_oku(satirlar, bicim)
    h404 = [x for x in k if x["kod"] == 404]
    ips = collections.Counter(x["ip"] for x in h404)
    tar = tek_en_cok(ips)
    t_istek = [x for x in k if x["ip"] == tar]

    def gizli():
        g = [x for x in t_istek if x["kod"] == 200]
        assert g and len({x["yol"] for x in g}) == 1, g
        # tarayici gizli yolu bulmadan once yalniz 404 almis olmali
        ilk = next(i for i, x in enumerate(t_istek) if x["kod"] == 200)
        assert all(x["kod"] == 404 for x in t_istek[:ilk])
        return g

    if tur == "ip_en_cok_404":
        return tar
    if tur == "sayi_404_top":
        return str(ips[tar])
    if tur == "toplam_404":
        return str(len(h404))
    if tur == "farkli_yol_top":
        return str(len({x["yol"] for x in h404 if x["ip"] == tar}))
    if tur == "arac_adi":
        for ad in ARAC_ADLARI:
            if all(ad.lower() in x["ua"].lower() for x in t_istek):
                return ad
        raise AssertionError("arac bulunamadi")
    if tur == "ilk_zaman_top":
        return t_istek[0]["saat"]
    if tur == "yol_en_cok_404":
        return tek_en_cok(collections.Counter(x["yol"] for x in h404))
    if tur == "farkli_ip":
        return str(len({x["ip"] for x in k}))
    if tur == "yol_en_cok_200":
        return tek_en_cok(collections.Counter(x["yol"] for x in k if x["kod"] == 200))
    if tur == "saat_en_cok_404":
        return tek_en_cok(collections.Counter(x["saat"][:2] for x in h404))
    g = gizli() if tur not in ("oncesi_404", "son_oktet", "arac_adi") else None
    if tur == "gizli_yol":
        return g[0]["yol"]
    if tur == "gizli_200_sayisi":
        return str(len(g))
    if tur == "gizli_boyut":
        return str(g[0]["boyut"])
    if tur == "gizli_dizin":
        return g[0]["yol"].split("/")[1]
    if tur == "gizli_son_bolum":
        return g[0]["yol"].rstrip("/").rsplit("/", 1)[1]
    if tur == "gizli_zaman":
        return g[0]["saat"]
    if tur == "oncesi_404":
        gizli()
        return str(len([x for x in t_istek if x["kod"] == 404]))
    if tur == "son_oktet":
        return tar.rsplit(".", 1)[1]
    if tur == "toplam_boyut":
        return str(sum(x["boyut"] for x in g))
    raise AssertionError(f"cozucu yok: {tur}")


def cp_oku(satirlar, bicim):
    olaylar = []
    for s in satirlar:
        if bicim == "jsonl":
            o = json.loads(s)
            saat = None
        else:
            assert " CAROTPOT " in s
            onek, js = s.split(" | ", 1)
            o = json.loads(js)
            saat = onek.split()[1]
        o["saat"] = saat
        olaylar.append(o)
    return olaylar


def cp_coz(tur, satirlar, bicim):
    o = cp_oku(satirlar, bicim)
    giris = [x for x in o if x["tur"] == "giris"]
    tarama = sorted((x for x in o if x["tur"] == "tarama"), key=lambda x: x["ts"])
    hizmetler = collections.defaultdict(set)
    for x in o:
        hizmetler[x["kaynak"]].add(x["hizmet"])

    def tarayici():
        return tek_en_cok(collections.Counter({ip: len(h) for ip, h in hizmetler.items()}))

    kul = collections.Counter(x["kullanici"] for x in giris)
    if tur == "kullanici_en_cok":
        return tek_en_cok(kul)
    if tur == "en_cok_sayi":
        return str(kul[tek_en_cok(kul)])
    if tur == "farkli_kullanici":
        return str(len(kul))
    if tur == "toplam_giris":
        return str(len(giris))
    if tur == "hizmet_en_cok":
        return tek_en_cok(collections.Counter(x["hizmet"] for x in giris))
    if tur == "kaynak_en_cok":
        return tek_en_cok(collections.Counter(x["kaynak"] for x in giris))
    if tur == "http_giris":
        return str(sum(1 for x in giris if x["hizmet"] == "http"))
    if tur == "ikinci_kullanici":
        return tek_en_cok(kul, ikinci=True)
    if tur == "parola_en_cok":
        return tek_en_cok(collections.Counter(x["parola"] for x in giris))
    if tur == "ilk_zaman":
        return min(giris, key=lambda x: x["ts"])["saat"]
    if tur == "son_zaman":
        return max(giris, key=lambda x: x["ts"])["saat"]
    if tur == "tarayici_ip":
        return tarayici()
    if tur == "hizmet_sayisi":
        return str(len(hizmetler[tarayici()]))
    if tur == "hizmet_listesi":
        return ",".join(sorted(hizmetler[tarayici()]))
    if tur == "tarama_olay_sayisi":
        return str(len(tarama))
    if tur == "en_cok_olay_ip":
        return tek_en_cok(collections.Counter(x["kaynak"] for x in o))
    if tur == "farkli_kaynak":
        return str(len(hizmetler))
    if tur == "tarama_suresi":
        return str(int(round(tarama[-1]["ts"] - tarama[0]["ts"])))
    if tur == "ilk_tarama_hizmeti":
        assert tarama[0]["ts"] != tarama[1]["ts"]
        return tarama[0]["hizmet"]
    if tur == "son_tarama_zaman":
        assert tarama[-1]["ts"] != tarama[-2]["ts"]
        return tarama[-1]["saat"]
    if tur.startswith("hizmet_kaynak_"):
        h = tur.split("_")[-1]
        return str(len({x["kaynak"] for x in o if x["hizmet"] == h}))
    raise AssertionError(f"cozucu yok: {tur}")


COZUCULER = {"ssh": ssh_coz, "web": web_coz, "cp": cp_coz}


# ----------------------------------------------------------------------------
# Sezar ve kodlama cozuculeri (dosya + sorudaki goruntulenen bilgiyle)
# ----------------------------------------------------------------------------

def kay(metin, k):
    return "".join(chr((ord(c) - 97 + k) % 26 + 97) if "a" <= c <= "z"
                   else chr((ord(c) - 65 + k) % 26 + 65) if "A" <= c <= "Z" else c for c in metin)


def vig_coz(metin, anahtar):
    cikti, i = [], 0
    for c in metin:
        if "a" <= c <= "z":
            cikti.append(chr((ord(c) - ord(anahtar[i % len(anahtar)])) % 26 + 97))
            i += 1
        else:
            cikti.append(c)
    return "".join(cikti)


def cit_coz(metin, raylar=3):
    n = len(metin)
    desen, r, yon = [], 0, 1
    for _ in range(n):
        desen.append(r)
        if r == 0:
            yon = 1
        elif r == raylar - 1:
            yon = -1
        r += yon
    sirali = sorted(range(n), key=lambda i: (desen[i], i))
    cikti = [""] * n
    for sira, i in enumerate(sirali):
        cikti[i] = metin[sira]
    return "".join(cikti)


CUMLE_IPUCLARI = ("toplanti notu", "gizli kasa", "bugunku giris", "yedekleme", "sunucu odasi",
                  "acil durum")
PAROLA = re.compile(r"\b([a-z]+\d{4})\b")


def anlamli(metin):
    return any(i in metin for i in CUMLE_IPUCLARI)


def parola_bul(metin):
    m = PAROLA.search(metin)
    assert m, metin
    return m.group(1)


MORS_TERS = {}


def sezar_coz(tur, u, dizin):
    d = u.degiskenler
    dosya = Path(u.dosya_yolu).read_text(encoding="utf-8").strip() if u.dosya_yolu else ""
    k = int(d["{k}"]) if "{k}" in d else None
    if tur == "c3":
        return parola_bul(kay(dosya, -3))
    if tur == "ck":
        return parola_bul(kay(dosya, -k))
    if tur == "rot13":
        return parola_bul(codecs.decode(dosya, "rot13"))
    if tur == "atbash":
        return parola_bul("".join(chr(122 - (ord(c) - 97)) if "a" <= c <= "z" else c for c in dosya))
    if tur == "sifrele_c":
        return kay(d["{sozcuk}"], k)
    if tur == "ters":
        return parola_bul(dosya[::-1])
    if tur == "a1z26":
        sol, sag = dosya.split(" | ")
        return "".join(chr(int(x) + 96) for x in sol.split("-")) + sag
    if tur in ("c_bil", "c_buyuk"):
        for s in range(26):
            acik = kay(dosya, s).lower()
            if anlamli(acik):
                return parola_bul(acik)
        raise AssertionError("kaydirma bulunamadi")
    if tur == "c_satir":
        for s in range(26):
            acik = kay(dosya, s)
            if any(l.startswith("kod ") and PAROLA.search(l) for l in acik.splitlines()):
                return next(l for l in acik.splitlines() if l.startswith("kod ")).split()[1]
        raise AssertionError("kaydirma bulunamadi")
    if tur == "vig_anahtar":
        return parola_bul(vig_coz(dosya, d["{anahtar}"]))
    if tur == "afin":
        a, b = int(d["{a}"]), int(d["{b}"])
        ters = pow(a, -1, 26)
        acik = "".join(chr((ters * (ord(c) - 97 - b)) % 26 + 97) if "a" <= c <= "z" else c
                       for c in dosya)
        return parola_bul(acik)
    if tur == "rot47":
        acik = "".join(chr(33 + (ord(c) - 33 + 47) % 94) if 33 <= ord(c) <= 126 else c for c in dosya)
        return parola_bul(acik)
    if tur == "mors":
        tablo = (Path(dizin) / d["{tablo}"]).read_text(encoding="utf-8").split("\n")
        ters = {}
        for satir in tablo:
            if satir.strip():
                h, kod = satir.split()
                ters[kod] = h
        return "".join(ters[x] for x in dosya.split())
    if tur == "yerine":
        satirlar = Path(d["{tablo}"]).read_text(encoding="utf-8").splitlines() \
            if os.path.isabs(d["{tablo}"]) else \
            (Path(dizin) / d["{tablo}"]).read_text(encoding="utf-8").splitlines()
        duz = satirlar[0].split()[1]
        sif = satirlar[1].split()[1]
        acik = "".join(duz[sif.index(c)] if c in sif else c for c in dosya)
        return parola_bul(acik)
    if tur == "vig_bilinmeyen":
        # bilinen baslangic: "toplanti notu: sifre ..." -> ilk 3 harften anahtar
        anahtar = "".join(chr((ord(c) - ord(p)) % 26 + 97) for c, p in zip(dosya[:3], "top"))
        return parola_bul(vig_coz(dosya, anahtar))
    if tur == "vig_liste":
        tablo = d["{tablo}"]
        yol = Path(tablo) if os.path.isabs(tablo) else Path(dizin) / tablo
        for anahtar in yol.read_text(encoding="utf-8").split():
            acik = vig_coz(dosya, anahtar)
            if anlamli(acik):
                return parola_bul(acik)
        raise AssertionError("anahtar bulunamadi")
    if tur == "c_base64":
        return parola_bul(kay(base64.b64decode(dosya).decode(), -k))
    if tur == "cit":
        return parola_bul(cit_coz(dosya, 3))
    if tur == "ters_c":
        return parola_bul(kay(dosya, -k)[::-1])
    raise AssertionError(f"cozucu yok: {tur}")


def _adim(ad, veri):
    if ad == "base64":
        return base64.b64decode(veri, validate=True)
    if ad == "base32":
        return base64.b32decode(veri)
    if ad == "hex":
        return bytes.fromhex(veri.decode("ascii"))
    if ad == "gzip":
        return gzip.decompress(veri)
    if ad == "url":
        return urllib.parse.unquote_to_bytes(veri.decode("ascii"))
    if ad == "rot13":
        return codecs.encode(veri.decode("ascii"), "rot13").encode("ascii")
    raise AssertionError(ad)


ADIMLAR = ("base64", "base32", "hex", "gzip", "url", "rot13")


def yollar(veri, derinlik=8, yol=()):
    """Bayraga giden TUM kodlama yollari: [(yol, bayrak_metni)]."""
    if re.search(rb"CAROT\{[0-9a-f]{8}\}", veri):
        return [(yol, veri)]
    if derinlik == 0:
        return []
    bulunan = []
    for ad in ADIMLAR:
        try:
            s = _adim(ad, veri)
        except Exception:  # noqa: BLE001
            continue
        if s != veri:
            bulunan += yollar(s, derinlik - 1, yol + (ad,))
    return bulunan


def kodlama_coz(tur, par, u):
    d = u.degiskenler
    veri = Path(u.dosya_yolu).read_bytes() if u.dosya_yolu else b""
    bayrak = re.compile(rb"CAROT\{[0-9a-f]{8}\}")
    if tur in ("coz", "sarili"):
        if tur == "sarili":
            veri = veri.replace(b"\n", b"")
        bulunan = yollar(veri)
        assert bulunan, "yol yok"
        if par["adlar"] == "sirali":
            adlar = d["{katmanlar}"].split(" → ")
            s = veri
            for a in adlar:
                s = _adim(a, s)
            assert s in {b for _, b in bulunan}
        return bayrak.search(bulunan[0][1]).group(0).decode()
    if tur in ("say", "ilk"):
        # rot13 kendi tersi oldugundan daha derin sahte yollar da bulunur;
        # ogrencinin yaptigi gibi en KISA yol sayilir
        tum = yollar(veri)
        en_az = min(len(y) for y, _ in tum)
        kisa = [y for y, _ in tum if len(y) == en_az]
        if tur == "say":
            return str(en_az)
        assert len({y[0] for y in kisa}) == 1, kisa
        return kisa[0][0]
    if tur == "dis":
        return _adim(d["{dis}"], veri).decode("ascii")
    if tur == "json":
        bulunan = yollar(veri)
        return json.loads(bulunan[0][1])["token"]
    if tur == "url":
        return urllib.parse.parse_qs(veri.decode())["sifre"][0]
    if tur == "satir":
        sonuclar = set()
        for satir in veri.split(b"\n"):
            for _, b in yollar(satir):
                m = bayrak.search(b)
                if m and b.startswith(b"CAROT{"):
                    sonuclar.add(m.group(0).decode())   # rot13 dongusu ayni bayragi tekrarlar
        assert len(sonuclar) == 1, sonuclar
        return sonuclar.pop()
    if tur == "kodla":
        s = d["{sozcuk}"].encode()
        for ad in par["zincir"]:
            if ad == "base64":
                s = base64.b64encode(s)
            elif ad == "base32":
                s = base64.b32encode(s)
            elif ad == "hex":
                s = s.hex().encode()
            elif ad == "rot13":
                s = codecs.encode(s.decode(), "rot13").encode()
        return s.decode()
    raise AssertionError(f"cozucu yok: {tur}")


# ----------------------------------------------------------------------------
# Testler
# ----------------------------------------------------------------------------

class KayitYapisi(unittest.TestCase):
    ANAHTARLAR = ("ssh_saldirgan", "ssh_giren", "web_tarayici:ip", "web_tarayici:yol",
                  "carotpot_kayit:kullanici", "carotpot_kayit:tarayici", "sezar", "kodlama_zinciri")

    def test_her_ailede_en_az_yirmi_varyant(self):
        for a in self.ANAHTARLAR:
            self.assertGreaterEqual(V.sayi(a), 20, a)

    def test_varyant_metinleri_tam(self):
        for a in self.ANAHTARLAR:
            for no, v in enumerate(V.KAYIT[a], 1):
                for alan in ("soru", "ipucu", "ozet"):
                    for dil in ("tr", "en"):
                        self.assertTrue(v[alan][dil].strip(), f"{a} #{no} {alan}.{dil}")
                self.assertLessEqual(len(v["ozet"]["tr"]), 70, f"{a} #{no}")
                self.assertNotIn("((", v["soru"]["tr"])

    def test_gunluk_varyantlari_ayirt_edilir(self):
        # ayni (soru turu, bicim) ikilisi iki kez bulunmamali
        for a in self.ANAHTARLAR[:6]:
            cift = [(v["tur"], v["bicim"]) for v in V.KAYIT[a]]
            self.assertEqual(len(cift), len(set(cift)), a)

    def test_numara_basa_sarar(self):
        self.assertIs(V.al("sezar", 1), V.al("sezar", V.sayi("sezar") + 1))

    def test_gorev_anahtarlari(self):
        for gid in list(GUNLUK_GOREVLER) + ["kodlama-01", "kodlama-02"]:
            self.assertGreaterEqual(V.gorev_varyant_sayisi(gid), 20, gid)
        self.assertEqual(V.gorev_varyant_sayisi("nmap-01"), 0)
        self.assertEqual(V.gorev_varyant_sayisi("yok-99"), 0)

    def test_ozet_ve_aciklama(self):
        for gid in ("loganaliz-03", "kodlama-02", "kodlama-01"):
            for no in range(1, V.gorev_varyant_sayisi(gid) + 1):
                for dil in ("tr", "en"):
                    ozet = V.gorev_varyant_ozeti(gid, no, dil)
                    self.assertTrue(ozet)
                    self.assertLessEqual(len(ozet), 58)
                    self.assertNotIn("{", V.gorev_varyant_aciklamasi(gid, no, dil))


class GunlukVaryantlari(unittest.TestCase):
    def _dene(self, gid):
        aile = GUNLUK_GOREVLER[gid]
        n = V.gorev_varyant_sayisi(gid)
        for no in range(1, n + 1):
            v = V.al(V.gorev_anahtari(gid), no)
            for zorluk in ZORLUKLAR:
                for _ in range(2):
                    with self.subTest(gorev=gid, varyant=no, zorluk=zorluk):
                        u = uret(gid, zorluk, no)
                        try:
                            satirlar = Path(u.dosya_yolu).read_text(encoding="utf-8").splitlines()
                            beklenen = COZUCULER[aile](v["tur"], satirlar, v["bicim"])
                            self.assertEqual(beklenen, u.dogru_cevap)
                            self.assertTrue(u.dogru_cevap.strip())
                            self.assertEqual(u.degiskenler["{varyant}"], f"{no}/{n}")
                            for anahtar in ("{soru_tr}", "{ipucu_tr}", "{soru_en}", "{ipucu_en}"):
                                self.assertNotRegex(u.degiskenler[anahtar],
                                                    r"\{(dosya|tablo|k|sozcuk|h|tur|gizli)\}")
                            self.assertIn(u.dosya_yolu, u.degiskenler["{ipucu_tr}"] + u.degiskenler["{soru_tr}"])
                        finally:
                            u.durdur()

    def test_ssh_saldirgan(self):
        self._dene("loganaliz-01")

    def test_ssh_giren(self):
        self._dene("loganaliz-02")

    def test_web_ip(self):
        self._dene("loganaliz-03")

    def test_web_yol(self):
        self._dene("loganaliz-04")

    def test_carotpot_kullanici(self):
        self._dene("loganaliz-05")

    def test_carotpot_tarayici(self):
        self._dene("loganaliz-06")

    def test_bicim_gercekten_farkli(self):
        """syslog/iso ve combined/json varyantlari gercekten ayri bicim uretir."""
        u1, u2 = uret("loganaliz-01", "orta", 1), uret("loganaliz-01", "orta", 2)
        try:
            a = Path(u1.dosya_yolu).read_text().splitlines()[0]
            b = Path(u2.dosya_yolu).read_text().splitlines()[0]
            self.assertRegex(a, r"^[A-Z][a-z]{2} +\d+ \d\d:\d\d:\d\d ")
            self.assertRegex(b, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d")
        finally:
            u1.durdur()
            u2.durdur()

    def test_ayni_varyant_her_seferinde_farkli_veri(self):
        a, b = uret("loganaliz-01", "orta", 3), uret("loganaliz-01", "orta", 3)
        try:
            self.assertEqual(a.degiskenler["{soru_tr}"], b.degiskenler["{soru_tr}"])
            self.assertNotEqual(Path(a.dosya_yolu).read_text(), Path(b.dosya_yolu).read_text())
        finally:
            a.durdur()
            b.durdur()

    def test_varyantsiz_bireysel_calisma(self):
        """Varyant verilmezse (bireysel mod) rastgele uygun bir varyant secilir."""
        gorulen = set()
        for _ in range(30):
            u = uret("loganaliz-02", "orta", 0)
            try:
                gorulen.add(u.degiskenler["{varyant}"])
                self.assertTrue(u.dogru_cevap)
            finally:
                u.durdur()
        self.assertGreater(len(gorulen), 5)


class SezarKodlamaVaryantlari(unittest.TestCase):
    def test_sezar(self):
        n = V.sayi("sezar")
        for no in range(1, n + 1):
            v = V.al("sezar", no)
            for zorluk in ZORLUKLAR:
                for _ in range(3):
                    with self.subTest(varyant=no, tur=v["tur"], zorluk=zorluk):
                        u = uret("kodlama-02", zorluk, no)
                        try:
                            dizin = Path(u.dosya_yolu).parent if u.dosya_yolu else \
                                Path(u.degiskenler.get("{tablo}", "/")).parent
                            self.assertEqual(sezar_coz(v["tur"], u, dizin), u.dogru_cevap)
                            for anahtar in ("{soru_tr}", "{ipucu_tr}", "{soru_en}", "{ipucu_en}"):
                                self.assertNotRegex(u.degiskenler[anahtar],
                                                    r"\{(dosya|tablo|k|sozcuk|anahtar|a|b)\}")
                        finally:
                            u.durdur()

    def test_kodlama(self):
        n = V.sayi("kodlama_zinciri")
        for no in range(1, n + 1):
            v = V.al("kodlama_zinciri", no)
            for zorluk in ZORLUKLAR:
                for _ in range(3):
                    with self.subTest(varyant=no, tur=v["tur"], zorluk=zorluk):
                        u = uret("kodlama-01", zorluk, no)
                        try:
                            self.assertEqual(kodlama_coz(v["tur"], v["par"], u), u.dogru_cevap)
                            for anahtar in ("{soru_tr}", "{ipucu_tr}", "{soru_en}", "{ipucu_en}"):
                                self.assertNotRegex(
                                    u.degiskenler[anahtar],
                                    r"\{(dosya|katmanlar|komutlar|sozcuk|dis|katman_sayisi)\}")
                        finally:
                            u.durdur()

    def test_zorluga_uygun_secim(self):
        """Kolay seviyede yalniz 'kolay' etiketli varyantlar secilir."""
        for _ in range(60):
            no = V.sec("sezar", "kolay")
            self.assertIn("kolay", V.al("sezar", no)["zorluk"])
        for _ in range(60):
            no = V.sec("kodlama_zinciri", "zor")
            self.assertIn("zor", V.al("kodlama_zinciri", no)["zorluk"])
        # hicbir varyant secilemeyen zorlukta tumune dusulur
        self.assertIn(V.sec("sezar", "yok-boyle-zorluk"), range(1, V.sayi("sezar") + 1))


class OgretmenTarafi(unittest.TestCase):
    def test_otomatik_secim_tur_bitmeden_tekrar_etmez(self):
        oda = OS.OdaDurumu("T1", "s")
        n = V.gorev_varyant_sayisi("loganaliz-01")
        verilen = []
        for _ in range(n):
            oda.gorev_ata("loganaliz-01", "orta")
            verilen.append(oda.gorev_varyantlari["loganaliz-01"])
        self.assertEqual(len(set(verilen)), n)
        # tur sinirinda ayni soru art arda gelmez
        for _ in range(3 * n):
            onceki = oda.gorev_varyantlari["loganaliz-01"]
            oda.gorev_ata("loganaliz-01", "orta")
            self.assertNotEqual(onceki, oda.gorev_varyantlari["loganaliz-01"])

    def test_zorluga_gore_secim(self):
        oda = OS.OdaDurumu("T2", "s")
        n = V.gorev_varyant_sayisi("kodlama-02")
        for _ in range(2 * n):
            oda.gorev_ata("kodlama-02", "kolay")
            self.assertIn("kolay", V.al("sezar", oda.gorev_varyantlari["kodlama-02"])["zorluk"])

    def test_elle_secilen_varyant(self):
        oda = OS.OdaDurumu("T3", "s")
        oda.gorev_ata("loganaliz-03", "orta", varyant=7)
        self.assertEqual(oda.gorev_varyantlari, {"loganaliz-03": 7})
        oda.gorev_ata("loganaliz-03", "orta", varyant=7)         # elle seçim tekrar edebilir
        self.assertEqual(oda.gorev_varyantlari, {"loganaliz-03": 7})

    def test_varyantsiz_gorev(self):
        oda = OS.OdaDurumu("T4", "s")
        self.assertEqual(oda.gorev_ata("nmap-01", "orta"), 1)
        self.assertEqual(oda.gorev_varyantlari, {})
        self.assertEqual(oda.varyant_oner("nmap-01"), 0)

    def test_yeni_soru_numara_ve_varyant_birlikte(self):
        oda = OS.OdaDurumu("T5", "s")
        a = oda.gorev_ata("loganaliz-05", "orta")
        v1 = oda.gorev_varyantlari["loganaliz-05"]
        b = oda.gorev_ata("loganaliz-05", "orta")
        self.assertEqual(b, a + 1)
        self.assertNotEqual(v1, oda.gorev_varyantlari["loganaliz-05"])

    def test_gorev_kapatinca_varyant_silinir(self):
        oda = OS.OdaDurumu("T6", "s")
        oda.gorev_ata("loganaliz-01", "orta")
        oda.gorev_kapat("loganaliz-01")
        self.assertEqual(oda.gorev_varyantlari, {})

    def test_ozel_soru_varyanti(self):
        oda = OS.OdaDurumu("T7", "s")
        oda.ozel_soru_ata("loganaliz-01", {"satir_sayisi": 300, "varyant": 5})
        self.assertEqual(oda.gorev_varyantlari, {"loganaliz-01": 5})
        self.assertNotIn("varyant", oda.gorev_parametreleri["loganaliz-01"])
        oda.ozel_soru_ata("loganaliz-01", {"satir_sayisi": 300, "varyant": 0})
        self.assertIn(oda.gorev_varyantlari["loganaliz-01"], range(1, 21))
        oda.ozel_soru_ata("loganaliz-01", {"satir_sayisi": 300})
        self.assertIn(oda.gorev_varyantlari["loganaliz-01"], range(1, 21))

    def test_sinifa_duyuru_http(self):
        oda = OS.OdaDurumu("T8", "s")
        srv = OS.sunucu_baslat(oda, "127.0.0.1", 0)
        try:
            port = srv.server_address[1]
            oda.gorev_ata("loganaliz-04", "zor", varyant=11)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/gorevler", timeout=5) as r:
                veri = json.loads(r.read())
            self.assertEqual(veri["varyantlar"], {"loganaliz-04": 11})
            self.assertEqual(veri["aktif_soru_no"], 1)
            self.assertEqual(oda.anlik_goruntu()["varyantlar"], {"loganaliz-04": 11})
        finally:
            srv.shutdown()
            srv.server_close()


class SoruOlusturSablonu(unittest.TestCase):
    def test_varyant_alani(self):
        for gid in list(GUNLUK_GOREVLER) + ["kodlama-01", "kodlama-02"]:
            alanlar = {a["anahtar"]: a for a in SS.SABLONLAR[gid]["alanlar"]}
            self.assertIn("varyant", alanlar, gid)
            a = alanlar["varyant"]
            self.assertEqual((a["min"], a["max"]), (0, V.gorev_varyant_sayisi(gid)))
            self.assertEqual(SS.varsayilan(gid, "varyant"), "0")
        self.assertNotIn("varyant", {a["anahtar"] for a in SS.SABLONLAR["nmap-01"]["alanlar"]})

    def test_ayristirma(self):
        p = SS.parametreleri_ayristir("kodlama-02", {"varyant": "7"})
        self.assertEqual(p, {"varyant": 7})
        self.assertEqual(SS.parametreleri_ayristir("kodlama-02", {}), {"varyant": 0})
        with self.assertRaises(SS.GecersizDeger):
            SS.parametreleri_ayristir("kodlama-02", {"varyant": "99"})
        with self.assertRaises(SS.GecersizDeger):
            SS.parametreleri_ayristir("kodlama-02", {"varyant": "-1"})
        self.assertNotIn("Soru varyantı", SS.etiket_uret("kodlama-02", {"varyant": 3}))

    def test_ozel_soru_uretimi_varyantla_calisir(self):
        p = SS.parametreleri_ayristir("loganaliz-02", {"satir_sayisi": "400", "saldirgan_sayisi": "2",
                                                       "varyant": "9"})
        oda = OS.OdaDurumu("T9", "s")
        oda.ozel_soru_ata("loganaliz-02", p)
        no = oda.gorev_varyantlari["loganaliz-02"]
        self.assertEqual(no, 9)
        g = gorev_json("loganaliz-02")
        prm = dict(oda.gorev_parametreleri["loganaliz-02"])
        prm.update({"varyant": no})
        u = U.uret(g["flag_uretimi"]["uretec"], prm)
        try:
            v = V.al("ssh_giren", no)
            satirlar = Path(u.dosya_yolu).read_text().splitlines()
            self.assertEqual(ssh_coz(v["tur"], satirlar, v["bicim"]), u.dogru_cevap)
        finally:
            u.durdur()


if __name__ == "__main__":
    unittest.main()
