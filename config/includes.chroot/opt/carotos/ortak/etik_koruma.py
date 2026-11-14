# -*- coding: utf-8 -*-
"""CarotOS etik koruma katmani (GTK'siz, yalniz standart kutuphane).

Guvenlik Paneli'nde baska bir sisteme dokunabilecek araclar (nmap, nikto,
sqlmap, hydra) calistirilmadan once hedefin kime ait olabilecegini siniflar:

  yerel   127.0.0.0/8, ::1, localhost, bu makinenin kendi adi -> surtunme yok
          (ag/aralik yazimi ancak TAMAMI geri dongudeyse)
  ozel    ozel/yerel ag adresleri (RFC1918, link-local, CGNAT, ULA) ve
          tek etiketli/.local/.lan adlari -> "Bu ag sana mi ait?" sorulur, evet
          denirse ag hatirlanir; tek etiketli (noktasiz) adlar hatirlanmaz, her
          seferinde sorulur (hangi aga ait olduklari bilinemez)
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
_GERI_DONGU4 = ipaddress.ip_network("127.0.0.0/8")
_HICBIRI4 = ipaddress.ip_network("0.0.0.0/32")
_SAYISAL = re.compile(r"(0x[0-9a-f]*|\d+)(\.(0x[0-9a-f]*|\d+)){0,3}\Z")
_GUNLUK_SINIR = 200_000


def _aralik_agi(belirtec):
    """nmap'in '192.168.1.1-50', '10.0.*.1' gibi sekilleri icin araligin TAMAMINI
    kapsayan en kucuk ag; bu sekil degilse None.

    Yalniz iki ucu siniflamak yetmez (G-04): '10-127.0.0.1'in uclari ozel/yerel ama
    arasi acik internettir. Kapsayan ag araligin her adresini icerir; boylece adres
    sayisi (256'dan fazla adres -> /24'ten genis ag) ve tek blokta kalma denetimi,
    CIDR yazimiyla ayni kurallardan (sinifla) gecer: '10.*.*.*' de '10.0.0.0/8' de
    disari; '192.168.1.1-50' ozel kalir."""
    if not _ARALIK.match(belirtec):
        return None
    alt, ust = [], []
    for parca in belirtec.split("."):
        if parca == "*":
            a, b = 0, 255
        else:
            uclar = parca.split("-")
            if any(len(u) > 1 and u.startswith("0") for u in uclar):
                return None            # bastaki sifir (sekizlik?) belirsiz: ad gibi, en katiya duser
            a, b = sorted(int(u) for u in uclar) if len(uclar) == 2 else (int(parca), int(parca))
        if b > 255:
            return None
        alt.append(a)
        ust.append(b)
    lo = int(ipaddress.IPv4Address(".".join(map(str, alt))))
    hi = int(ipaddress.IPv4Address(".".join(map(str, ust))))
    return ipaddress.ip_network((lo, 32 - (lo ^ hi).bit_length()), strict=False)


def _cozumleyici_ip(ad):
    """Adres cozumleyicinin (glibc inet_aton) IP adresi saydigi kisa/sayisal yazimlar:
    '0x08080808', '134744072', '127.1', '8.8.2056', '010.0.0.1' (sekizlik). Bunlar ad
    degil IP adresidir (G-05); ad sanilirsa 'ozel ag' sorusuyla gecip hatirlanirdi.
    Standart dort sekizli yazim ipaddress ile zaten taninir. DNS'e sorulmaz."""
    if not ad or not _SAYISAL.match(ad):
        return None
    try:
        return socket.inet_ntoa(socket.inet_aton(ad))
    except (OSError, ValueError):
        return None


def _tek_hedef(jeton):
    """Bir bosluksuz girdiyi [(host_veya_ip, onek|None), ...] listesine cevirir;
    ayristirilamazsa []. Alan adlari kucuk harfe cevrilir."""
    if "://" in jeton:
        try:
            host = urllib.parse.urlparse(jeton).hostname
        except ValueError:
            return []
        if not host:
            return []
        host = host.lower()
        return [(_cozumleyici_ip(host) or host, None)]
    # IP, CIDR (IPv4/IPv6)
    try:
        ag = ipaddress.ip_network(jeton, strict=False)
        onek = ag.prefixlen if "/" in jeton else None
        return [(str(ipaddress.ip_interface(jeton).ip), onek)]
    except ValueError:
        pass
    sayisal = _cozumleyici_ip(jeton.lower())
    if sayisal:
        return [(sayisal, None)]
    aralik = _aralik_agi(jeton)
    if aralik is not None:
        return [(str(aralik.network_address), aralik.prefixlen)]
    # host, host:port, host/yol
    govde = jeton.lstrip("/").split("/")[0]
    if govde.count(":") == 1:
        govde = govde.split(":")[0]
    if govde.startswith("[") and "]" in govde:        # [::1]:80
        govde = govde[1:govde.index("]")]
    govde = govde.strip(".").lower()
    if not re.fullmatch(r"[a-z0-9_.\-]+|[0-9a-f:]+", govde or ""):
        return []
    return [(_cozumleyici_ip(govde) or govde, None)]          # '0x08080808:80'


def hedefleri_ayikla(metin):
    """Hedef alanindaki metinden [(host, onek|None)] cikarir. '-' ile baslayan
    jetonlar secenek, 65535'e kadar yalniz rakamli jetonlar port sayilip atlanir.
    Daha buyuk sayi ('134744072' = 8.8.8.8) cozumleyici icin IP adresidir (G-05)."""
    sonuc = []
    for jeton in (metin or "").split():
        if jeton.startswith("-"):                       # secenek
            continue
        if jeton.isascii() and jeton.isdigit() and len(jeton) <= 5 and int(jeton) <= 65535:
            continue                                    # port numarasi
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
    if ip is not None and onek is not None:
        # Ag yazimi: tek adrese degil agin TAMAMINA bakilir (G-03). '127.0.0.1/0',
        # '0.0.0.0/1', '::1/0' geri donguden tasar; bunlar butun adres uzayidir.
        ag = ipaddress.ip_network(f"{ip}/{onek}", strict=False)
        if ag.version == 4 and (ag.subnet_of(_GERI_DONGU4) or ag == _HICBIRI4):
            return YEREL
        if ag.version == 6 and ag.num_addresses == 1 and ip.is_loopback:
            return YEREL
        if onek < (24 if ip.version == 4 else 64):
            return DISARI
        if any(a.version == ag.version and ag.subnet_of(a) for a in _OZEL_AGLAR):
            return OZEL
        return DISARI
    if ip is not None:
        if ip.is_loopback or (ip.version == 4 and ip == ipaddress.ip_address("0.0.0.0")):
            return YEREL
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
            "hatirla": [onaylanirsa hatirlanabilecek ag anahtarlari],
            "onay_metni": yazilmasi gereken metin (yalniz tur=="yaz")}
    """
    hedefler = hedefleri_ayikla(metin)
    if not hedefler:
        # Hicbir hedef cikarilamadi: en temkinli yol, girdinin aynen yazilmasi.
        return {"gerek": True, "tur": "yaz", "sinif": DISARI, "hedefler": [],
                "aglar": [], "hatirla": [], "onay_metni": (metin or "").strip()}
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
                "aglar": [], "hatirla": [], "onay_metni": yaz}
    if ozel:
        aglar = sorted({ag_anahtari(h) for h in ozel})
        # Tek sozcuklu (noktasiz) makine adi hangi agda oldugunu soylemez: ayni ad baska
        # bir agda baska bir makine olabilir. Onayi hatirlanmaz, her seferinde sorulur (G-05).
        tek_sozcuk = {a for a in aglar if a.startswith("ad:") and "." not in a[3:]}
        yeni = [a for a in aglar if a in tek_sozcuk or a not in set(onayli_aglar)]
        return {"gerek": bool(yeni), "tur": "ozel" if yeni else None, "sinif": OZEL,
                "hedefler": adlar, "aglar": yeni,
                "hatirla": [a for a in yeni if a not in tek_sozcuk], "onay_metni": None}
    return {"gerek": False, "tur": None, "sinif": YEREL, "hedefler": adlar,
            "aglar": [], "hatirla": [], "onay_metni": None}


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
