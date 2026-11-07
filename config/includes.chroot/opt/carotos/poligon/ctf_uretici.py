# -*- coding: utf-8 -*-
"""CarotOS Poligon CTF -- ogrenciye ozel gorev dosyasi ureticileri (GTK'siz, yalnizca standart kutuphane).

Her uretici, ogrenci basina FARKLI ama TEKRAR URETILEBILIR bir dosya ve o dosyanin bayragini dondurur:
    uretici(ctx, parametreler) -> (dosya_adi, icerik, bayrak)
`ctx.rng` oturum sirri ve ogrenciden tureyen bir Random'dur; `ctx.bayrak_hex` ayri bir HMAC'ten gelir.
Sunucu bayragi saklamaz: dogrulamada ayni dosyayi yeniden uretip bayragi karsilastirir.

Her uretici icin bir referans COZUCU vardir (cozucular sozlugu). Cozucu, ogrencinin eline gecen dosyadan
bayragi akil yoluyla cikarir; testler her gorevin gercekten cozulebildigini bununla kanitlar.

Hicbir uretici ag trafigi uretmez, dosya yazmaz, komut calistirmaz: yalnizca metin dondurur.
"""
from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import random

ON_EK, SON_EK = "CAROT{", "}"

KELIMELER = [
    "kaplumbaga", "guvenlik", "firewall", "sifreleme", "protokol", "yonlendirici", "anahtar", "erisim",
    "denetim", "izleme", "yetki", "dogrulama", "tarama", "kesif", "savunma", "sunucu", "paket", "baglanti",
    "oturum", "kimlik", "gunluk", "arsiv", "kaynak", "hedef", "zafiyet", "yama", "sizinti", "kalkan",
    "kule", "kopru", "sinyal", "dugum", "agac", "bellek", "islem", "sistem", "cekirdek", "surucu",
    "sozluk", "parola", "kasa", "kilit", "kapi", "duvar", "izci", "bekci", "nobetci", "karakol",
]


class Baglam:
    """Uretici girdisi: tekrar uretilebilir rastgelelik ve bayrak ham maddesi."""

    def __init__(self, rng: random.Random, bayrak_hex: str):
        self.rng = rng
        self.bayrak_hex = bayrak_hex


def bayrak_yap(govde: str) -> str:
    return f"{ON_EK}{govde}{SON_EK}"


def _rot13(s: str) -> str:
    return codecs.encode(s, "rot13")


# --- kodlama ----------------------------------------------------------------------------------------
def _kodla(metin: str, katman: str) -> str:
    if katman == "base64":
        return base64.b64encode(metin.encode()).decode()
    if katman == "hex":
        return metin.encode().hex()
    if katman == "rot13":
        return _rot13(metin)
    if katman == "ters":
        return metin[::-1]
    raise ValueError("bilinmeyen katman: " + katman)


def _coz(metin: str, katman: str) -> str:
    if katman == "base64":
        return base64.b64decode(metin.encode()).decode()
    if katman == "hex":
        return bytes.fromhex(metin).decode()
    if katman == "rot13":
        return _rot13(metin)
    if katman == "ters":
        return metin[::-1]
    raise ValueError("bilinmeyen katman: " + katman)


def kodlama_zinciri(ctx: Baglam, p: dict):
    katmanlar = list(p.get("katmanlar") or ["base64"])
    bayrak = bayrak_yap(ctx.bayrak_hex[:12])
    veri = bayrak
    for k in katmanlar:
        veri = _kodla(veri, k)
    ipucu = p.get("katmanlari_goster", True)
    govde = ["# CarotOS Poligon CTF: kodlanmis mesaj", "mesaj:", veri]
    if ipucu:
        govde.append("# katman sayisi: %d" % len(katmanlar))
    return "mesaj.txt", "\n".join(govde) + "\n", bayrak


def kodlama_zinciri_coz(icerik: str, p: dict) -> str:
    satirlar = icerik.splitlines()
    veri = satirlar[satirlar.index("mesaj:") + 1]
    for k in reversed(list(p.get("katmanlar") or ["base64"])):
        veri = _coz(veri, k)
    return veri


# --- kriptografi ---------------------------------------------------------------------------------------
def _sezar(metin: str, kayma: int) -> str:
    sonuc = []
    for c in metin:
        if "a" <= c <= "z":
            sonuc.append(chr((ord(c) - 97 + kayma) % 26 + 97))
        elif "A" <= c <= "Z":
            sonuc.append(chr((ord(c) - 65 + kayma) % 26 + 65))
        else:
            sonuc.append(c)
    return "".join(sonuc)


def sezar_sifresi(ctx: Baglam, p: dict):
    bayrak = bayrak_yap(ctx.bayrak_hex[:12])
    kayma = ctx.rng.randint(1, 25)
    cumle = "Gizli mesaj: %s Bu mesaji baskasi okumamali." % bayrak
    return "sifreli.txt", _sezar(cumle, kayma) + "\n", bayrak


def sezar_sifresi_coz(icerik: str, p: dict) -> str:
    for kayma in range(26):
        aday = _sezar(icerik.strip(), kayma)
        i = aday.find(ON_EK)
        if i >= 0:
            return aday[i:aday.index(SON_EK, i) + 1]
    raise ValueError("cozulemedi")


def xor_tek_bayt(ctx: Baglam, p: dict):
    bayrak = bayrak_yap(ctx.bayrak_hex[:12])
    anahtar = ctx.rng.randint(1, 255)
    ham = bytes(b ^ anahtar for b in bayrak.encode())
    return "xor.hex", ham.hex() + "\n", bayrak


def xor_tek_bayt_coz(icerik: str, p: dict) -> str:
    ham = bytes.fromhex(icerik.strip())
    for anahtar in range(1, 256):
        aday = bytes(b ^ anahtar for b in ham)
        if aday.startswith(ON_EK.encode()) and aday.endswith(SON_EK.encode()):
            return aday.decode()
    raise ValueError("cozulemedi")


# --- hash ----------------------------------------------------------------------------------------------------
def _ozet(parola: str, algo: str) -> str:
    return hashlib.new(algo, parola.encode()).hexdigest()


def hash_kir(ctx: Baglam, p: dict):
    algo = p.get("algo", "sha256")
    hane = int(p.get("hane", 2))
    kelime = ctx.rng.choice(KELIMELER)
    sayi = ctx.rng.randrange(10 ** hane)
    parola = f"{kelime}{sayi:0{hane}d}"
    liste = ctx.rng.sample(KELIMELER, 30)
    if kelime not in liste:
        liste[ctx.rng.randrange(len(liste))] = kelime
    govde = ["# CarotOS Poligon CTF: hash kirma", "algoritma: %s" % algo, "hash: %s" % _ozet(parola, algo),
             "parola bicimi: kelime + %d haneli sayi" % hane, "kelime listesi:"] + liste
    return "hash.txt", "\n".join(govde) + "\n", bayrak_yap(parola)


def hash_kir_coz(icerik: str, p: dict) -> str:
    satirlar = icerik.splitlines()
    algo = satirlar[1].split(": ", 1)[1]
    hedef = satirlar[2].split(": ", 1)[1]
    hane = int(p.get("hane", 2))
    for kelime in satirlar[satirlar.index("kelime listesi:") + 1:]:
        for n in range(10 ** hane):
            parola = f"{kelime}{n:0{hane}d}"
            if _ozet(parola, algo) == hedef:
                return bayrak_yap(parola)
    raise ValueError("cozulemedi")


# --- gunluk analizi ---------------------------------------------------------------------------------------
_AG_ONEKLERI = ("192.0.2.", "198.51.100.", "203.0.113.")        # belgeleme aralıkları: gercek bir adres degil


def _ip(rng: random.Random) -> str:
    return "%s%d" % (rng.choice(_AG_ONEKLERI), rng.randint(2, 250))


def log_saldirgan(ctx: Baglam, p: dict):
    rng = ctx.rng
    saldirgan = _ip(rng)
    digerleri = []
    while len(digerleri) < int(p.get("diger_adres", 6)):
        a = _ip(rng)
        if a != saldirgan and a not in digerleri:
            digerleri.append(a)
    satirlar = []
    n_saldiri = int(p.get("saldiri_sayisi", 40))
    for _ in range(n_saldiri):
        satirlar.append(("Failed password for root", saldirgan))
    for a in digerleri:
        for _ in range(rng.randint(1, max(2, n_saldiri // 5))):
            satirlar.append(("Failed password for admin", a))
    for a in digerleri:
        satirlar.append(("Accepted password for carot", a))
    rng.shuffle(satirlar)
    cikti = []
    for i, (olay, a) in enumerate(satirlar):
        cikti.append("Nov  7 %02d:%02d:%02d carotos sshd[%d]: %s from %s port %d ssh2" % (
            9 + i // 600, (i // 10) % 60, (i * 7) % 60, 1000 + i, olay, a, rng.randint(30000, 60000)))
    return "auth.log", "\n".join(cikti) + "\n", bayrak_yap(saldirgan)


def log_saldirgan_coz(icerik: str, p: dict) -> str:
    sayac: dict[str, int] = {}
    for satir in icerik.splitlines():
        if "Failed password" in satir:
            a = satir.split(" from ", 1)[1].split()[0]
            sayac[a] = sayac.get(a, 0) + 1
    return bayrak_yap(max(sayac, key=sayac.get))


def log_belirtec(ctx: Baglam, p: dict):
    rng = ctx.rng
    bayrak = bayrak_yap(ctx.bayrak_hex[:12])
    belirtec = base64.urlsafe_b64encode(bayrak.encode()).decode().rstrip("=")
    yollar = ["/", "/index.html", "/giris", "/hakkinda", "/iletisim", "/urunler", "/sepet", "/yardim"]
    n = int(p.get("satir", 60))
    gizli_sira = rng.randrange(n)
    cikti = []
    for i in range(n):
        a = _ip(rng)
        yol = rng.choice(yollar)
        if i == gizli_sira:
            yol = "/yonetim/ayar?belirtec=%s" % belirtec
        cikti.append('%s - - [07/Nov/2026:10:%02d:%02d +0000] "GET %s HTTP/1.1" %d %d' % (
            a, i // 60, i % 60, yol, rng.choice([200, 200, 200, 301, 404]), rng.randint(200, 9000)))
    return "access.log", "\n".join(cikti) + "\n", bayrak


def log_belirtec_coz(icerik: str, p: dict) -> str:
    for satir in icerik.splitlines():
        if "belirtec=" in satir:
            b = satir.split("belirtec=", 1)[1].split()[0]
            b += "=" * (-len(b) % 4)
            return base64.urlsafe_b64decode(b.encode()).decode()
    raise ValueError("cozulemedi")


# --- adli bilisim ---------------------------------------------------------------------------------------------
def adli_hexdump(ctx: Baglam, p: dict):
    rng = ctx.rng
    bayrak = bayrak_yap(ctx.bayrak_hex[:12])
    onde = bytes(rng.randrange(256) for _ in range(rng.randint(40, 90)))
    arkada = bytes(rng.randrange(256) for _ in range(rng.randint(40, 90)))
    veri = onde + b"\x00\x00" + bayrak.encode() + b"\x00\x00" + arkada
    satirlar = []
    for i in range(0, len(veri), 16):
        parca = veri[i:i + 16]
        hexs = " ".join("%02x" % b for b in parca).ljust(47)
        ascii_ = "".join(chr(b) if 32 <= b < 127 else "." for b in parca)
        satirlar.append("%08x  %s  |%s|" % (i, hexs, ascii_))
    return "dosya.hexdump", "\n".join(satirlar) + "\n", bayrak


def adli_hexdump_coz(icerik: str, p: dict) -> str:
    veri = b""
    for satir in icerik.splitlines():
        hexler = satir[10:57].split()
        veri += bytes(int(h, 16) for h in hexler)
    i = veri.find(ON_EK.encode())
    return veri[i:veri.index(SON_EK.encode(), i) + 1].decode()


def adli_meta(ctx: Baglam, p: dict):
    rng = ctx.rng
    bayrak = bayrak_yap(ctx.bayrak_hex[:12])
    gizli = binascii.hexlify(bayrak.encode()).decode()
    alanlar = [
        ("dosya", "rapor_%d.docx" % rng.randint(100, 999)),
        ("boyut", str(rng.randint(10000, 90000))),
        ("olusturan", rng.choice(["ayse", "mehmet", "zeynep", "can"])),
        ("program", "KofisOfis 4.%d" % rng.randint(0, 9)),
        ("yorum_kodu", gizli),
        ("dil", "tr-TR"),
        ("surum", str(rng.randint(1, 9))),
    ]
    rng.shuffle(alanlar)
    return "bilgi.meta", "\n".join("%s = %s" % a for a in alanlar) + "\n", bayrak


def adli_meta_coz(icerik: str, p: dict) -> str:
    for satir in icerik.splitlines():
        if satir.startswith("yorum_kodu"):
            return bytes.fromhex(satir.split("=", 1)[1].strip()).decode()
    raise ValueError("cozulemedi")


URETICILER = {
    "kodlama_zinciri": kodlama_zinciri, "sezar_sifresi": sezar_sifresi, "xor_tek_bayt": xor_tek_bayt,
    "hash_kir": hash_kir, "log_saldirgan": log_saldirgan, "log_belirtec": log_belirtec,
    "adli_hexdump": adli_hexdump, "adli_meta": adli_meta,
}
COZUCULAR = {
    "kodlama_zinciri": kodlama_zinciri_coz, "sezar_sifresi": sezar_sifresi_coz, "xor_tek_bayt": xor_tek_bayt_coz,
    "hash_kir": hash_kir_coz, "log_saldirgan": log_saldirgan_coz, "log_belirtec": log_belirtec_coz,
    "adli_hexdump": adli_hexdump_coz, "adli_meta": adli_meta_coz,
}
