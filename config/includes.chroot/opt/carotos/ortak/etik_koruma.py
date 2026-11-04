# -*- coding: utf-8 -*-
"""CarotOS etik koruma katmani (GTK'siz, yalniz standart kutuphane).

Guvenlik Paneli'nde baska bir sisteme dokunabilecek araclar (nmap, nikto,
sqlmap, hydra) calistirilmadan once hedefin kime ait olabilecegini siniflar:

  yerel   127.0.0.0/8, ::1, localhost, bu makinenin kendi adi -> surtunme yok
  ozel    ozel/yerel ag adresleri (RFC1918, link-local, CGNAT, ULA) ve
          tek etiketli/.local/.lan adlari -> "Bu ag sana mi ait?" bir kez
          sorulur, evet denirse ag hatirlanir
  disari  diger her sey (acik IP'ler, alan adlari, genis ozel bloklar, cozumlenemeyen
          girdi) -> etik islem metni gosterilir, hedef ELLE yazilarak onaylanir

Bu bir EGITICI SURTUNMEDIR, guvenlik denetimi degildir: komut satirindan
asilir. Metinler hukuki tavsiye degildir ve hicbir yasadan madde/ceza atfi
icermez. Siniflandirma DNS'e sormaz (cevrimdisi ve deterministiktir).
Her karar yerel bir gunluge yazilir.
"""
import ipaddress
import os
import re
import socket
import time
import urllib.parse

YEREL = "yerel"
OZEL = "ozel"
DISARI = "disari"

_OZEL_AGLAR = [ipaddress.ip_network(a) for a in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",   # RFC1918
    "169.254.0.0/16",                                  # link-local
    "100.64.0.0/10",                                   # CGNAT (servis saglayici agi)
    "fc00::/7", "fe80::/10",                           # ULA, link-local (IPv6)
)]
_OZEL_SONEKLER = (".local", ".lan", ".home.arpa", ".internal", ".intranet")
_ARALIK = re.compile(r"^(\d{1,3}|\*|\d{1,3}-\d{1,3})(\.(\d{1,3}|\*|\d{1,3}-\d{1,3})){3}$")
_GUNLUK_SINIR = 200_000


def _aralik_uclari(belirtec):
    """nmap'in '192.168.1.1-50', '10.0.*.1' gibi sekillerinin alt ve ust uc
    adresleri (yalnizca bu sekil icin); degilse None."""
    if not _ARALIK.match(belirtec):
        return None
    alt, ust = [], []
    for parca in belirtec.split("."):
        if parca == "*":
            alt.append("0")
            ust.append("255")
        elif "-" in parca:
            a, b = parca.split("-")
            alt.append(a)
            ust.append(b)
        else:
            alt.append(parca)
            ust.append(parca)
    try:
        return (ipaddress.ip_address(".".join(alt)), ipaddress.ip_address(".".join(ust)))
    except ValueError:
        return None


def _tek_hedef(jeton):
    """Bir bosluksuz girdiyi [(host_veya_ip, onek|None), ...] listesine cevirir;
    ayristirilamazsa []. Alan adlari kucuk harfe cevrilir."""
    if "://" in jeton:
        try:
            host = urllib.parse.urlparse(jeton).hostname
        except ValueError:
            return []
        return [(host.lower(), None)] if host else []
    # IP, CIDR (IPv4/IPv6)
    try:
        ag = ipaddress.ip_network(jeton, strict=False)
        onek = ag.prefixlen if "/" in jeton else None
        return [(str(ipaddress.ip_interface(jeton).ip), onek)]
    except ValueError:
        pass
    uclar = _aralik_uclari(jeton)
    if uclar:
        return [(str(uclar[0]), None), (str(uclar[1]), None)]
    # host, host:port, host/yol
    govde = jeton.lstrip("/").split("/")[0]
    if govde.count(":") == 1:
        govde = govde.split(":")[0]
    if govde.startswith("[") and "]" in govde:        # [::1]:80
        govde = govde[1:govde.index("]")]
    govde = govde.strip(".").lower()
    return [(govde, None)] if re.fullmatch(r"[a-z0-9_.\-]+|[0-9a-f:]+", govde or "") else []


def hedefleri_ayikla(metin):
    """Hedef alanindaki metinden [(host, onek|None)] cikarir. '-' ile baslayan
    jetonlar secenek sayilir ve atlanir."""
    sonuc = []
    for jeton in (metin or "").split():
        if jeton.startswith("-") or jeton.isdigit():   # secenek / port numarasi
            continue
        sonuc.extend(_tek_hedef(jeton))
    return sonuc


def sinifla(host, onek=None, kendi_ad=None):
    """Tek bir (host, onek) icin YEREL / OZEL / DISARI dondurur."""
    if kendi_ad is None:
        try:
            kendi_ad = socket.gethostname()
        except OSError:
            kendi_ad = ""
    kendi_ad = (kendi_ad or "").strip().lower()
    ad = (host or "").strip().lower()
    try:
        ip = ipaddress.ip_address(ad)
    except ValueError:
        ip = None
    if ip is not None:
        genis = onek is not None and onek < (24 if ip.version == 4 else 64)
        if ip.is_loopback or (ip.version == 4 and ip == ipaddress.ip_address("0.0.0.0")):
            return YEREL
        if genis:
            return DISARI
        if any(ip in a for a in _OZEL_AGLAR):
            return OZEL
        return DISARI
    if ad == "localhost" or ad.endswith(".localhost") or (kendi_ad and ad == kendi_ad):
        return YEREL
    if ad.endswith(_OZEL_SONEKLER) or ("." not in ad and ad):
        return OZEL
    return DISARI


def ag_anahtari(host):
    """Hatirlanacak ag kimligi: IPv4 icin /24, IPv6 icin /64, adlar icin 'ad:...'."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "ad:" + host.lower()
    return str(ipaddress.ip_network(f"{host}/{24 if ip.version == 4 else 64}", strict=False))


def degerlendir(metin, onayli_aglar=(), kendi_ad=None):
    """Hedef metnini degerlendirir.

    Donus: {"gerek": bool, "tur": None|"ozel"|"yaz", "sinif": str,
            "hedefler": [host...], "aglar": [yeni/onaysiz ag anahtarlari],
            "onay_metni": yazilmasi gereken metin (yalniz tur=="yaz")}
    """
    hedefler = hedefleri_ayikla(metin)
    if not hedefler:
        # Hicbir hedef cikarilamadi: en temkinli yol, girdinin aynen yazilmasi.
        return {"gerek": True, "tur": "yaz", "sinif": DISARI, "hedefler": [],
                "aglar": [], "onay_metni": (metin or "").strip()}
    siniflar = [(h, sinifla(h, o, kendi_ad)) for h, o in hedefler]
    disari = [h for h, s in siniflar if s == DISARI]
    ozel = [h for h, s in siniflar if s == OZEL]
    adlar = sorted({h for h, _ in siniflar})
    if disari:
        farkli = sorted(set(disari))
        # Tek, onek/aralik icermeyen hedefse yalniz adi, degilse girdinin tamami yazilir.
        tek = len(farkli) == 1 and len(adlar) == 1 and all(o is None for _, o in hedefler)
        yaz = farkli[0] if tek else (metin or "").strip()
        return {"gerek": True, "tur": "yaz", "sinif": DISARI, "hedefler": adlar,
                "aglar": [], "onay_metni": yaz}
    if ozel:
        aglar = sorted({ag_anahtari(h) for h in ozel})
        yeni = [a for a in aglar if a not in set(onayli_aglar)]
        return {"gerek": bool(yeni), "tur": "ozel" if yeni else None, "sinif": OZEL,
                "hedefler": adlar, "aglar": yeni, "onay_metni": None}
    return {"gerek": False, "tur": None, "sinif": YEREL, "hedefler": adlar,
            "aglar": [], "onay_metni": None}


def onay_dogru(beklenen, yazilan):
    """Elle yazilan onay, beklenenle (bas/son bosluk ve buyuk-kucuk harf farksiz) ayni mi."""
    b = (beklenen or "").strip().casefold()
    return bool(b) and (yazilan or "").strip().casefold() == b


def gunluge_yaz(yol, arac, hedef, sinif, karar):
    """Karari tek satir olarak yerel gunluge ekler (dosya 0600). Hata verirse
    sessizce vazgecer: gunluk arac calismasini engellememeli."""
    def temiz(s):
        return re.sub(r"[\r\n\t]+", " ", str(s))[:200]
    satir = "\t".join((time.strftime("%Y-%m-%d %H:%M:%S"), temiz(arac), temiz(hedef),
                       temiz(sinif), temiz(karar))) + "\n"
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        try:
            if os.path.getsize(yol) > _GUNLUK_SINIR:
                with open(yol, "r", encoding="utf-8", errors="replace") as fh:
                    kuyruk = fh.readlines()[-500:]
                with open(yol, "w", encoding="utf-8") as fh:
                    fh.writelines(kuyruk)
        except OSError:
            pass
        fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(satir)
        return True
    except OSError:
        return False
