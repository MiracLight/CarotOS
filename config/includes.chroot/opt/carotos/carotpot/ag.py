# -*- coding: utf-8 -*-
"""
Yerel ag bilgisi (root gerekmez): komsu tablosu, ag gecidi, bu bilgisayarin
adresleri, MAC uretici adi ve ad cozumleme.

Uretici adlari nmap'in MAC onek listesinden okunur (CarotOS'ta nmap kurulu);
yoksa kucuk bir yerlesik tablo kullanilir. Yerel yonetimli (rastgele) MAC
adresleri ayrica belirtilir: telefonlar ve dizustu bilgisayarlar gizlilik
icin bunlari kullanir.
"""

import ipaddress
import json
import socket
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

ORTAM = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C", "LANG": "C"}

ONEK_DOSYALARI = ("/usr/share/nmap/nmap-mac-prefixes", "/usr/share/ieee-data/oui.txt")

# Yerlesik yedek: okul/ev aginda sik gorulen ureticiler
YEDEK_ONEKLER = {
    "B827EB": "Raspberry Pi", "DCA632": "Raspberry Pi", "E45F01": "Raspberry Pi",
    "28CDC1": "Raspberry Pi", "2CCF67": "Raspberry Pi", "D83ADD": "Raspberry Pi",
    "240AC4": "Espressif", "3C71BF": "Espressif", "84CCA8": "Espressif", "A4CF12": "Espressif",
    "ECFABC": "Espressif", "C8C9A3": "Espressif", "08002E": "Oracle VirtualBox",
    "080027": "Oracle VirtualBox", "525400": "QEMU/KVM", "000C29": "VMware", "005056": "VMware",
    "001C42": "Parallels", "F0D5BF": "Google", "3C5AB4": "Google", "001A11": "Google",
    "ACBC32": "Apple", "F0189B": "Apple", "A4B197": "Apple", "3C0754": "Apple",
    "001B63": "Apple", "F4F5D8": "Google", "B0BE76": "TP-Link", "50C7BF": "TP-Link",
    "C006C3": "TP-Link", "00E04C": "Realtek", "001E58": "D-Link", "3C1E04": "D-Link",
    "001018": "Broadcom", "00155D": "Microsoft Hyper-V", "000D3A": "Microsoft",
    "3863BB": "HP", "6C3BE5": "HP", "002481": "HP", "F8B156": "Dell", "B8CA3A": "Dell",
    "00215A": "HP", "8CDCD4": "HP", "00248C": "Asus", "1C872C": "Asus", "AC220B": "Asus",
    "001CDF": "Belkin", "E8DE27": "TP-Link", "70B3D5": "IEEE Kayıtlı", "B4FBE4": "Ubiquiti",
    "F09FC2": "Ubiquiti", "000E58": "Sonos", "18B430": "Nest", "D0737F": "Mini-Box",
    "4C11AE": "Espressif", "8C8590": "Apple", "E0D55E": "Gigabyte", "1C1B0D": "Gigabyte",
    "00D861": "Micro-Star (MSI)", "4CCC6A": "Micro-Star (MSI)", "00E018": "Asus",
    "0050F2": "Microsoft", "E4A7A0": "Intel", "001B21": "Intel", "3C970E": "Intel",
    "A0369F": "Intel", "001F3B": "Intel", "F81654": "Intel", "9C2976": "Intel",
}

_onekler = None
_onek_kilit = threading.Lock()


def _onekleri_yukle():
    global _onekler
    with _onek_kilit:
        if _onekler is not None:
            return _onekler
        tablo = dict(YEDEK_ONEKLER)
        for yol in ONEK_DOSYALARI:
            try:
                with open(yol, encoding="utf-8", errors="replace") as fh:
                    for satir in fh:
                        if satir.startswith("#") or len(satir) < 8:
                            continue
                        if "(base 16)" in satir:          # ieee oui.txt
                            onek, _, ad = satir.partition("(base 16)")
                            onek = onek.strip().replace("-", "")
                        else:                             # nmap-mac-prefixes
                            onek, _, ad = satir.partition(" ")
                        onek = onek.strip().upper()
                        if len(onek) == 6 and all(c in "0123456789ABCDEF" for c in onek):
                            tablo[onek] = ad.strip()
                break
            except OSError:
                continue
        _onekler = tablo
        return tablo


def mac_normal(mac):
    parca = str(mac or "").replace("-", ":").lower().split(":")
    if len(parca) != 6 or not all(len(p) == 2 for p in parca):
        return None
    try:
        [int(p, 16) for p in parca]
    except ValueError:
        return None
    return ":".join(parca)


def rastgele_mac_mi(mac):
    m = mac_normal(mac)
    return bool(m) and bool(int(m[:2], 16) & 0x02)


def uretici(mac):
    """MAC adresinin ureticisi. Bilinmiyorsa '' ; rastgele MAC ise
    'rastgele' (arayuz cevirir)."""
    m = mac_normal(mac)
    if not m:
        return ""
    if rastgele_mac_mi(m):
        return "rastgele"
    return _onekleri_yukle().get(m.replace(":", "")[:6].upper(), "")


def _komut(komut):
    try:
        p = subprocess.run(komut, capture_output=True, text=True, timeout=5, env=ORTAM)
        return p.stdout if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def komsular():
    """Komsu tablosu: [{ip, mac, durum}]. Once 'ip neigh', yoksa /proc/net/arp."""
    sonuc = {}
    cikti = _komut(["ip", "-j", "neigh", "show"])
    try:
        for n in json.loads(cikti) if cikti else []:
            mac = mac_normal(n.get("lladdr"))
            ip = n.get("dst")
            durumlar = n.get("state") or []
            if not ip or not mac or "FAILED" in durumlar or "INCOMPLETE" in durumlar:
                continue
            if ip.startswith("fe80:") and ip in sonuc:
                continue
            sonuc[ip] = {"ip": ip, "mac": mac, "durum": ",".join(durumlar).lower()}
    except ValueError:
        pass
    if not sonuc:
        try:
            with open("/proc/net/arp", encoding="ascii", errors="replace") as fh:
                next(fh, None)
                for satir in fh:
                    p = satir.split()
                    if len(p) >= 4 and p[2] != "0x0" and mac_normal(p[3]) and p[3] != "00:00:00:00:00:00":
                        sonuc[p[0]] = {"ip": p[0], "mac": mac_normal(p[3]), "durum": "arp"}
        except OSError:
            pass
    return list(sonuc.values())


def ag_gecidi():
    """IPv4 varsayilan ag gecidi ya da None."""
    try:
        with open("/proc/net/route", encoding="ascii") as fh:
            next(fh, None)
            for satir in fh:
                p = satir.split()
                if len(p) > 2 and p[1] == "00000000" and p[2] != "00000000":
                    return socket.inet_ntoa(bytes.fromhex(p[2])[::-1])
    except (OSError, ValueError):
        pass
    return None


def kendi_adresler():
    """[(ip, onek_uzunlugu)] -- geri dongu haric."""
    sonuc = []
    cikti = _komut(["ip", "-j", "addr"])
    try:
        for arayuz in json.loads(cikti) if cikti else []:
            if arayuz.get("ifname") == "lo":
                continue
            for a in arayuz.get("addr_info", []):
                if a.get("local"):
                    sonuc.append((a["local"], int(a.get("prefixlen", 24))))
    except (ValueError, TypeError):
        pass
    return sonuc


def yerel_ag():
    """Bu bilgisayarin ilk ozel IPv4 agi (ipaddress.IPv4Network) ya da None."""
    for ip, onek in kendi_adresler():
        try:
            adr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if adr.version == 4 and adr.is_private:
            return ipaddress.ip_network(f"{ip}/{max(onek, 24)}", strict=False)
    return None


_ad_onbellek = {}
_ad_kilit = threading.Lock()


def ad_coz(ip, zaman=1.5):
    """Ters DNS / yerel ad (mDNS cozumleyici kuruluysa .local). Bulunamazsa ''."""
    with _ad_kilit:
        if ip in _ad_onbellek:
            return _ad_onbellek[ip]
    sonuc = {"ad": ""}

    def coz():
        try:
            sonuc["ad"] = socket.gethostbyaddr(ip)[0]
        except (OSError, UnicodeError):
            pass
    t = threading.Thread(target=coz, daemon=True)
    t.start()
    t.join(zaman)
    ad = sonuc["ad"] if sonuc["ad"] != ip else ""
    with _ad_kilit:
        _ad_onbellek[ip] = ad
    return ad


def yokla(ag=None, en_fazla=254, es_zamanli=48):
    """Yerel /24 agdaki adreslere birer ping gonderir; boylece komsu tablosu
    dolar. Yalnizca ozel aglarda ve en fazla 254 adres icin calisir. Yanit
    veren adres sayisini dondurur."""
    ag = ag or yerel_ag()
    if ag is None or not ag.is_private:
        return 0
    adresler = [str(a) for a in list(ag.hosts())[:en_fazla]]

    def ping(ip):
        try:
            return subprocess.run(["ping", "-c", "1", "-W", "1", "-q", ip],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  timeout=3, env=ORTAM).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    with ThreadPoolExecutor(es_zamanli) as havuz:
        return sum(havuz.map(ping, adresler))


def cihazlar(tuzak_kaynaklari=None):
    """Harita icin cihaz listesi. tuzak_kaynaklari: {ip: profil}.
    Her cihaz: {ip, mac, uretici, ad, gecit, tuzak}"""
    tuzak_kaynaklari = tuzak_kaynaklari or {}
    gecit = ag_gecidi()
    kendi = {ip for ip, _ in kendi_adresler()}
    gorulen = {}
    for k in komsular():
        if k["ip"] in kendi or k["ip"].startswith("fe80:"):
            continue
        gorulen[k["ip"]] = {"ip": k["ip"], "mac": k["mac"], "uretici": uretici(k["mac"]),
                            "ad": "", "gecit": k["ip"] == gecit,
                            "tuzak": k["ip"] in tuzak_kaynaklari}
    for ip in tuzak_kaynaklari:
        if ip not in gorulen and ip not in kendi and not ip.startswith("127."):
            gorulen[ip] = {"ip": ip, "mac": "", "uretici": "", "ad": "",
                           "gecit": ip == gecit, "tuzak": True}
    if gecit and gecit not in gorulen:
        gorulen[gecit] = {"ip": gecit, "mac": "", "uretici": "", "ad": "",
                          "gecit": True, "tuzak": gecit in tuzak_kaynaklari}
    return list(gorulen.values())


def mac_bul(ip):
    for k in komsular():
        if k["ip"] == ip:
            return k["mac"]
    return ""


if __name__ == "__main__":
    for c in cihazlar():
        print(c)
    print("gecit:", ag_gecidi(), "ag:", yerel_ag())
