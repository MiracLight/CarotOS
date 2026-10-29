"""
CarotOS Poligon -- uretec tabanli gorevler.

Her acilista RASTGELE icerik uretir (gunluk dosyalari, kodlanmis mesajlar,
sahte siteler...) ve dogru cevabi kendisi hesaplar. Gorev dosyasi
(gorevler/*.json) yalniz hangi uretecin hangi parametrelerle calisacagini
soyler: flag_uretimi = {"yontem": "uretec", "uretec": "<ad>",
"sabit_parametreler": {...}}; zorluga bagli parametreler 'zorluklar'
bolumunden gelir (ogretmenin "Soru Olustur" degerleri de ayni anahtarlari
kullanir).

Guvenlik: dosya tabanli uretecler yalniz gecici bir dizine yazar; ag tabanli
olanlar (site, banner, CarotPot laboratuvari) yalniz loopback'e (127.0.0.0/8)
baglanir -- ag_guvenlik.loopback_adres_mi.

GTK'dan bagimsizdir; testler bagimsiz "cozucu" fonksiyonlarla her uretimin
cevabini yeniden hesaplayip karsilastirir (tests/test_poligon_uretecler.py).
"""

from __future__ import annotations

import base64
import codecs
import gzip
import io
import json
import random
import re
import shutil
import socket
import tarfile
import tempfile
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import varyant_gunluk as _vg
import varyant_sifre as _vs
import varyantlar as _vy
from ag_guvenlik import loopback_adres_mi
from flag_uretici import flag_uret, parola_uret

_RNG = random.SystemRandom()

# Belge amacli ayrilmis (gercek aga ait olmayan) IP bloklari
_BELGE_IP_ONEKLERI = ("203.0.113.", "198.51.100.", "192.0.2.")
_AYLAR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_SALDIRGAN_KULLANICILAR = (
    "admin", "root", "test", "oracle", "postgres", "ubuntu", "pi", "guest", "user",
    "ftpuser", "mysql", "deploy", "support", "backup", "git", "jenkins", "tomcat", "nagios",
)
_MESRU_KULLANICILAR = ("ayse", "mehmet", "zeynep", "can", "elif", "burak", "deniz", "selin",
                       "kerem", "naz")


class Uretim:
    """Bir gorev acilisinin urunu: dogru cevap, metin degiskenleri, dosya yolu
    ve temizlik. Istemci _servis olarak tutar; durdur() her seyi kaldirir."""

    def __init__(self, dogru_cevap: str, degiskenler: dict | None = None,
                 dosya_yolu: str | None = None, dizin: Path | None = None,
                 kapat=None):
        self.dogru_cevap = dogru_cevap
        self.degiskenler = dict(degiskenler or {})
        self.dosya_yolu = dosya_yolu
        self._dizin = dizin
        self._kapat = list(kapat or [])

    def durdur(self) -> None:
        for f in self._kapat:
            try:
                f()
            except Exception:  # noqa: BLE001 -- temizlik asla gorevi bozmasin
                pass
        self._kapat = []
        if self._dizin is not None:
            shutil.rmtree(self._dizin, ignore_errors=True)
            self._dizin = None


# ----------------------------------------------------------------------------
# Ortak yardimcilar
# ----------------------------------------------------------------------------

def _dizin_ac() -> Path:
    return Path(tempfile.mkdtemp(prefix="poligon-uretim-"))


def _tam_sayi(p: dict, anahtar: str, varsayilan: int, alt: int, ust: int) -> int:
    try:
        d = int(p.get(anahtar, varsayilan))
    except (TypeError, ValueError):
        d = varsayilan
    return max(alt, min(ust, d))


def _bayrak(p: dict, anahtar: str, varsayilan: int = 0) -> bool:
    """0/1, True/False ya da formdan gelen "0"/"1"/"evet" metni."""
    v = p.get(anahtar, varsayilan)
    if isinstance(v, str):
        return v.strip().lower() in ("1", "evet", "true", "e", "var")
    return bool(v)


def _ip_uret(n: int) -> list[str]:
    havuz = [f"{o}{i}" for o in _BELGE_IP_ONEKLERI for i in range(1, 255)]
    _RNG.shuffle(havuz)
    return havuz[:n]


def _zaman_baslangici() -> datetime:
    return datetime.now().replace(microsecond=0) - timedelta(hours=_RNG.randint(3, 20))


def _sayac_dagilimi(n_sald: int, ust: int, yakin: bool) -> list[int]:
    """Saldirgan basina olay sayilari: ilki en cok (digerlerinden EN AZ 3 fazla)."""
    sayilar = [ust]
    for _ in range(n_sald - 1):
        if yakin:
            sayilar.append(_RNG.randint(max(1, ust - 8), ust - 3))
        else:
            sayilar.append(_RNG.randint(max(1, int(ust * 0.25)), max(1, int(ust * 0.7))))
    return sayilar


def _yaz(dizin: Path, ad: str, icerik) -> str:
    yol = dizin / ad
    if isinstance(icerik, bytes):
        yol.write_bytes(icerik)
    else:
        yol.write_text(icerik, encoding="utf-8")
    return str(yol)


def _varyant(anahtar: str, p: dict) -> tuple[int, dict]:
    """Atanan varyantı (p['varyant']) ya da -- atanmamışsa (bireysel çalışma) --
    zorluğa uygun rastgele birini döner."""
    try:
        no = int(p.get("varyant") or 0)
    except (TypeError, ValueError):
        no = 0
    if no < 1:
        no = _vy.sec(anahtar, p.get("_zorluk"))
    return no, _vy.al(anahtar, no)


def _varyant_degiskenleri(anahtar: str, no: int, v: dict, yer: dict) -> dict:
    """Senaryo/ipucu metinlerindeki {soru_tr}, {ipucu_en}... yer tutucuları.
    Varyant metinlerinin içindeki {dosya}, {k} gibi yer tutucular burada doldurulur."""
    d = dict(yer)
    for dil in ("tr", "en"):
        d[f"{{soru_{dil}}}"] = _vs.metni_uyar(v["soru"][dil], yer)
        d[f"{{ipucu_{dil}}}"] = _vs.metni_uyar(v["ipucu"][dil], yer)
        d[f"{{bicim_{dil}}}"] = v.get("bicim_aciklama", {}).get(dil, "")
    d["{varyant}"] = f"{no}/{_vy.sayi(anahtar)}"
    return d


def _en_cok(sayim: dict[str, int]) -> str:
    """En yuksek sayili anahtar; esitlik varsa AssertionError (uretec duzeltmeli)."""
    sirali = sorted(sayim.items(), key=lambda kv: -kv[1])
    assert len(sirali) == 1 or sirali[0][1] > sirali[1][1], "belirsiz en cok"
    return sirali[0][0]


# ----------------------------------------------------------------------------
# 1) SSH gunlugu: saldirgan IP / ele gecirilen hesap
# ----------------------------------------------------------------------------

def _ssh_olaylari(p: dict, giren: bool, bicim: str = "syslog"):
    toplam = _tam_sayi(p, "satir_sayisi", 300, 60, 5000)
    n_sald = _tam_sayi(p, "saldirgan_sayisi", 1, 1, 6)
    yakin = _bayrak(p, "yakin_rakip")
    ips = _ip_uret(n_sald + 8)
    sald, mesru_ip = ips[:n_sald], ips[n_sald:]
    ust = max(10, toplam // 12)
    sayilar = _sayac_dagilimi(n_sald, ust, yakin)
    t0 = _zaman_baslangici()
    olaylar: list[tuple[datetime, str]] = []
    pid = [_RNG.randint(1000, 30000)]

    def satir(zaman, mesaj):
        pid[0] += _RNG.randint(1, 9)
        if bicim == "iso":
            onek = f"{zaman:%Y-%m-%dT%H:%M:%S}.{_RNG.randint(0, 999999):06d}+03:00"
        else:
            onek = f"{_AYLAR[zaman.month - 1]} {zaman.day:2d} {zaman:%H:%M:%S}"
        return (zaman, f"{onek} sunucu01 sshd[{pid[0]}]: {mesaj}")

    def basarisiz(zaman, kul, ip):
        gecersiz = "invalid user " if kul not in _MESRU_KULLANICILAR and kul != "root" else ""
        olaylar.append(satir(zaman, f"Failed password for {gecersiz}{kul} from {ip} "
                                    f"port {_RNG.randint(1024, 65000)} ssh2"))

    ele_gecirilen = ""
    for i, (ip, adet) in enumerate(zip(sald, sayilar)):
        zaman = t0 + timedelta(seconds=_RNG.randint(600, 40000))
        hedefler = _RNG.sample(_SALDIRGAN_KULLANICILAR, k=min(6, len(_SALDIRGAN_KULLANICILAR)))
        ele = None
        if giren and (i == 0 or (i == 1 and _bayrak(p, "sahte_basari"))):
            ele = _RNG.choice(_MESRU_KULLANICILAR)
            hedefler = hedefler[:4] + [ele]
            if i == 0:
                ele_gecirilen = ele
        for _ in range(adet):
            zaman += timedelta(seconds=_RNG.randint(1, 4))
            basarisiz(zaman, _RNG.choice(hedefler), ip)
        if ele:
            zaman += timedelta(seconds=_RNG.randint(1, 4))
            olaylar.append(satir(zaman, f"Accepted password for {ele} from {ip} "
                                        f"port {_RNG.randint(1024, 65000)} ssh2"))
            olaylar.append(satir(zaman, f"pam_unix(sshd:session): session opened for user "
                                        f"{ele}(uid=1001) by (uid=0)"))

    # mesru kullanicilar: anahtarla giris, ara sira parola hatasi
    kullanici_ip = list(zip(_RNG.sample(_MESRU_KULLANICILAR, k=min(5, len(_MESRU_KULLANICILAR))),
                            mesru_ip))
    for kul, ip in kullanici_ip:
        for _ in range(_RNG.randint(1, 3)):
            zaman = t0 + timedelta(seconds=_RNG.randint(0, 80000))
            if _RNG.random() < 0.4:
                basarisiz(zaman, kul, ip)
                zaman += timedelta(seconds=_RNG.randint(2, 9))
                olaylar.append(satir(zaman, f"Accepted password for {kul} from {ip} "
                                            f"port {_RNG.randint(1024, 65000)} ssh2"))
            else:
                olaylar.append(satir(zaman, f"Accepted publickey for {kul} from {ip} "
                                            f"port {_RNG.randint(1024, 65000)} ssh2: "
                                            f"RSA SHA256:{base64.b64encode(_RNG.randbytes(12)).decode()}"))
    # gurultu
    tum_ip = sald + mesru_ip
    while len(olaylar) < toplam:
        zaman = t0 + timedelta(seconds=_RNG.randint(0, 82000))
        ip = _RNG.choice(tum_ip)
        port = _RNG.randint(1024, 65000)
        olaylar.append(satir(zaman, _RNG.choice((
            f"Connection closed by {ip} port {port} [preauth]",
            f"Received disconnect from {ip} port {port}:11: Bye Bye [preauth]",
            f"Disconnected from {ip} port {port}",
            f"Connection reset by {ip} port {port} [preauth]",
            "Server listening on 0.0.0.0 port 22.",
        ))))
    olaylar.sort(key=lambda o: o[0])
    return sald, ele_gecirilen, [s for _, s in olaylar]


def _ssh_uret(ad: str, p: dict, giren: bool) -> Uretim:
    no, v = _varyant(ad, p)
    for _ in range(80):
        _sald, _ele, satirlar = _ssh_olaylari(p, giren, v["bicim"])
        try:
            cevap = _vg.ssh_cevap(v["tur"], satirlar)
        except _vg.Belirsiz:
            continue
        break
    else:
        raise RuntimeError(f"{ad}: belirsiz olmayan gunluk uretilemedi (varyant {no})")
    dizin = _dizin_ac()
    yol = _yaz(dizin, "auth.log", "\n".join(satirlar) + "\n")
    yer = {"{dosya}": yol, "{satir}": str(len(satirlar))}
    return Uretim(cevap, _varyant_degiskenleri(ad, no, v, yer), yol, dizin)


def uret_ssh_saldirgan(p: dict, **_) -> Uretim:
    return _ssh_uret("ssh_saldirgan", p, giren=False)


def uret_ssh_giren(p: dict, **_) -> Uretim:
    return _ssh_uret("ssh_giren", p, giren=True)


# ----------------------------------------------------------------------------
# 2) Web erisim gunlugu: tarayici IP / bulunan gizli yol
# ----------------------------------------------------------------------------

_NORMAL_YOLLAR = ("/", "/urunler", "/urunler/12", "/urunler/7", "/hakkimizda", "/iletisim",
                  "/static/app.css", "/static/logo.png", "/blog", "/blog/yeni-surum",
                  "/sepet", "/giris")
_TARAMA_YOLLARI = ("/admin", "/wp-login.php", "/.env", "/backup.zip", "/phpmyadmin",
                   "/config.php", "/server-status", "/.git/config", "/db.sql", "/test",
                   "/old", "/api/v1/users", "/console", "/manager/html", "/shell.php",
                   "/xmlrpc.php", "/upload", "/dashboard", "/panel", "/setup")
_GIZLI_SABLONLARI = ("/yonetim-{r}/giris", "/yedek-{r}/veritabani.sql", "/dahili-{r}/ayarlar",
                     "/gecici-{r}/rapor.pdf", "/eski-{r}/index.php")
_ARAC_UA = tuple(u for u, _ad in _vg.ARAC_UA)
_TARAYICI_UA = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15",
)


def _web_gunlugu(p: dict, soru: str, bicim: str = "combined"):
    toplam = _tam_sayi(p, "satir_sayisi", 400, 80, 6000)
    n_tar = _tam_sayi(p, "tarayici_sayisi", 1, 1, 4)
    arac_ua = _bayrak(p, "arac_ua", 1)
    ips = _ip_uret(n_tar + 10)
    tarayicilar, ziyaretciler = ips[:n_tar], ips[n_tar:]
    ust = max(12, toplam // 10)
    sayilar = _sayac_dagilimi(n_tar, ust, _bayrak(p, "yakin_rakip"))
    t0 = _zaman_baslangici()
    olaylar: list[tuple[datetime, str]] = []

    istekler: list[tuple[str, int]] = []   # (ip, durum kodu) -- bicimden bagimsiz sayim icin

    def kayit(zaman, ip, yol, kod, ua):
        boyut = _RNG.randint(120, 9000) if kod == 200 else 153
        istekler.append((ip, kod))
        if bicim == "json":
            olaylar.append((zaman, json.dumps(
                {"ts": f"{zaman:%Y-%m-%dT%H:%M:%S}+03:00", "ip": ip, "method": "GET",
                 "path": yol, "status": kod, "bytes": boyut, "ua": ua}, ensure_ascii=False)))
            return
        olaylar.append((zaman, f'{ip} - - [{zaman:%d/%b/%Y:%H:%M:%S} +0300] "GET {yol} HTTP/1.1" '
                               f'{kod} {boyut} "-" "{ua}"'))

    gizli_yollar: list[str] = []
    ana_ua = _RNG.choice(_ARAC_UA)
    for i, (ip, adet) in enumerate(zip(tarayicilar, sayilar)):
        ua = ana_ua if arac_ua else _RNG.choice(_TARAYICI_UA)
        zaman = t0 + timedelta(seconds=_RNG.randint(600, 40000))
        yollar = [_RNG.choice(_TARAMA_YOLLARI) for _ in range(adet)]
        for y in yollar:
            zaman += timedelta(seconds=_RNG.randint(0, 2))
            kayit(zaman, ip, y, 404, ua)
        gizli = _RNG.choice(_GIZLI_SABLONLARI).format(
            r="".join(_RNG.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(4)))
        gizli_yollar.append(gizli)
        for _ in range(_RNG.randint(1, 3)):
            zaman += timedelta(seconds=_RNG.randint(0, 2))
            kayit(zaman, ip, gizli, 200, ua)
    # normal ziyaretciler (sporadik 404 de olur)
    while len(olaylar) < toplam:
        zaman = t0 + timedelta(seconds=_RNG.randint(0, 82000))
        ip = _RNG.choice(ziyaretciler)
        if _RNG.random() < 0.05:
            kayit(zaman, ip, _RNG.choice(("/favicon.ico", "/eski-sayfa", "/apple-touch-icon.png")),
                  404, _RNG.choice(_TARAYICI_UA))
        else:
            kayit(zaman, ip, _RNG.choice(_NORMAL_YOLLAR), 200, _RNG.choice(_TARAYICI_UA))
    olaylar.sort(key=lambda o: o[0])
    satirlar = [s for _, s in olaylar]
    sayim: dict[str, int] = {}
    for ip, kod in istekler:
        if kod == 404:
            sayim[ip] = sayim.get(ip, 0) + 1
    hedef_ip = _en_cok(sayim)
    if soru == "ip":
        cevap = hedef_ip
    else:
        cevap = gizli_yollar[tarayicilar.index(hedef_ip)]
    return satirlar, cevap


def uret_web_tarayici(p: dict, soru: str = "ip", **_) -> Uretim:
    anahtar = _vy.anahtar_bul("web_tarayici", soru)
    no, v = _varyant(anahtar, p)
    p2 = {**p, **({"arac_ua": 1} if v.get("arac_ua") else {})}
    for _ in range(80):
        satirlar, _eski = _web_gunlugu(p2, soru, v["bicim"])
        try:
            cevap = _vg.web_cevap(soru, v["tur"], satirlar, v["bicim"])
        except _vg.Belirsiz:
            continue
        break
    else:
        raise RuntimeError(f"web_tarayici: belirsiz olmayan gunluk uretilemedi (varyant {no})")
    dizin = _dizin_ac()
    ad = "access.log" if v["bicim"] == "combined" else "access.jsonl"
    yol = _yaz(dizin, ad, "\n".join(satirlar) + "\n")
    yer = {"{dosya}": yol, "{satir}": str(len(satirlar))}
    return Uretim(cevap, _varyant_degiskenleri(anahtar, no, v, yer), yol, dizin)


# ----------------------------------------------------------------------------
# 3) CarotPot kayit gunlugu (gercek CarotPot gunluk bicimi)
# ----------------------------------------------------------------------------

_CP_PORTLAR = {"ssh": 2222, "http": 8080, "telnet": 2323, "ftp": 2121, "vnc": 5900,
               "rdp": 3389, "mysql": 3306, "redis": 6379}


def _cp_satir(zaman: datetime, ip: str, hizmet: str, tur: str, kullanici=None, parola=None,
              bicim: str = "carotpot") -> str:
    # carotpot.olay_satiri ile ayni bicim (parola maskeli)
    maske = (parola[0] + "*" * (len(parola) - 1)) if parola else None
    govde = {"ts": zaman.timestamp(), "hizmet": hizmet, "kaynak": ip,
             "kaynak_port": _RNG.randint(1024, 65000), "hedef_port": _CP_PORTLAR[hizmet],
             "tur": tur, "ozet": f"{hizmet} {tur}", "kullanici": kullanici, "ayrinti": None}
    if parola is not None:
        govde["parola"] = maske
    if bicim == "jsonl":
        return json.dumps(govde, ensure_ascii=False)
    return (f"{zaman:%Y-%m-%d %H:%M:%S} CAROTPOT kaynak={ip} hizmet={hizmet} tur={tur} | "
            + json.dumps(govde, ensure_ascii=False))


def _cp_gunlugu(p: dict, soru: str, bicim: str = "carotpot"):
    n_sald = _tam_sayi(p, "saldirgan_sayisi", 3, 2, 8)
    toplam = _tam_sayi(p, "satir_sayisi", 150, 40, 3000)
    ips = [f"192.168.1.{i}" for i in _RNG.sample(range(2, 250), n_sald + 4)]
    sald, gurultu_ip = ips[:n_sald], ips[n_sald:]
    t0 = _zaman_baslangici()
    satirlar: list[tuple[datetime, str]] = []
    hizmetler = list(_CP_PORTLAR)

    def ekle(zaman, ip, hizmet, tur, kullanici=None, parola=None):
        satirlar.append((zaman, _cp_satir(zaman, ip, hizmet, tur, kullanici, parola, bicim)))

    if soru == "kullanici":
        ust = max(12, toplam // 8)
        sayilar = _sayac_dagilimi(n_sald, ust, _bayrak(p, "yakin_rakip"))
        kullanicilar = _RNG.sample(_SALDIRGAN_KULLANICILAR, k=min(8, len(_SALDIRGAN_KULLANICILAR)))
        sayac = {k: 0 for k in kullanicilar}
        hedefler = []
        for k, adet in zip(kullanicilar, sayilar):
            hedefler += [k] * adet
        # en cok denenen kullanici = kullanicilar[0] (sayilar[0] en buyuk)
        for k in hedefler:
            sayac[k] += 1
        _RNG.shuffle(hedefler)
        for k in hedefler:
            ip = _RNG.choice(sald)
            zaman = t0 + timedelta(seconds=_RNG.randint(0, 82000))
            hizmet = _RNG.choice(("ssh", "ftp", "telnet", "http"))
            ekle(zaman, ip, hizmet, "baglanti")
            ekle(zaman + timedelta(seconds=1), ip, hizmet, "giris", k,
                 _RNG.choice(("123456", "password", "admin123", "qwerty", "letmein")))
        cevap = _en_cok(sayac)
    else:  # "tarayici": en cok FARKLI hizmete dokunan kaynak
        tarayici = sald[0]
        kac = min(len(hizmetler), _tam_sayi(p, "taranan_hizmet", 5, 3, 8))
        for h in _RNG.sample(hizmetler, k=kac):
            zaman = t0 + timedelta(seconds=_RNG.randint(0, 80000))
            ekle(zaman, tarayici, h, "tarama")
        # digerleri: az hizmet ama (zor) cok olay -- olay sayisiyla yanilmasin
        for ip in sald[1:]:
            h = _RNG.sample(hizmetler, k=_RNG.randint(1, 2))
            adet = _RNG.randint(8, 25) if _bayrak(p, "cok_olayli_rakip") else _RNG.randint(1, 4)
            for _ in range(adet):
                zaman = t0 + timedelta(seconds=_RNG.randint(0, 80000))
                hz = _RNG.choice(h)
                ekle(zaman, ip, hz, "giris", _RNG.choice(_SALDIRGAN_KULLANICILAR), "123456")
        cevap = tarayici
    while len(satirlar) < toplam:
        zaman = t0 + timedelta(seconds=_RNG.randint(0, 82000))
        ip = _RNG.choice(gurultu_ip)
        ekle(zaman, ip, "http", "istek")
    satirlar.sort(key=lambda s: s[0])
    return [s for _, s in satirlar], cevap


def uret_carotpot_kayit(p: dict, soru: str = "kullanici", **_) -> Uretim:
    anahtar = _vy.anahtar_bul("carotpot_kayit", soru)
    no, v = _varyant(anahtar, p)
    if v["tur"] == "ikinci_kullanici":
        # ikinci sira ancak en az 3 farkli kullanici adi varsa anlamli
        p = {**p, "saldirgan_sayisi": max(3, _tam_sayi(p, "saldirgan_sayisi", 3, 2, 8))}
    for _ in range(80):
        satirlar, _eski = _cp_gunlugu(p, soru, v["bicim"])
        try:
            cevap = _vg.cp_cevap(soru, v["tur"], satirlar, v["bicim"])
        except _vg.Belirsiz:
            continue
        break
    else:
        raise RuntimeError(f"carotpot_kayit: belirsiz olmayan kayit uretilemedi (varyant {no})")
    dizin = _dizin_ac()
    ad = "olaylar.log" if v["bicim"] == "carotpot" else "olaylar.jsonl"
    yol = _yaz(dizin, ad, "\n".join(satirlar) + "\n")
    yer = {"{dosya}": yol, "{satir}": str(len(satirlar))}
    return Uretim(cevap, _varyant_degiskenleri(anahtar, no, v, yer), yol, dizin)


# ----------------------------------------------------------------------------
# 4) Katmanli kodlama ve Sezar/Vigenere
# ----------------------------------------------------------------------------

def _rot13(b: bytes) -> bytes:
    return codecs.encode(b.decode("ascii"), "rot13").encode("ascii")


def _varyant_dosyalari(k: dict) -> tuple[str | None, dict, Path]:
    """kur_sezar/kur_kodlama sonucunu gecici dizine yazar; (ana dosya yolu,
    {ad: yol}, dizin) doner."""
    dizin = _dizin_ac()
    yollar = {ad: _yaz(dizin, ad, icerik) for ad, icerik in k["dosyalar"].items()}
    return (yollar.get(k["dosya"]) if k["dosya"] else None), yollar, dizin


def _uret_varyantli(anahtar: str, kur, p: dict) -> Uretim:
    no, v = _varyant(anahtar, p)
    k = kur(v)
    yol, yollar, dizin = _varyant_dosyalari(k)
    yer = {"{dosya}": yol or "-", **k["yer"]}
    if "{tablo}" in yer:
        yer["{tablo}"] = yollar[yer["{tablo}"]]
    # {komutlar} icindeki {dosya} da doldurulsun
    if "{komutlar}" in yer:
        yer["{komutlar}"] = yer["{komutlar}"].replace("{dosya}", yer["{dosya}"])
    return Uretim(k["cevap"], _varyant_degiskenleri(anahtar, no, v, yer), yol, dizin)


def uret_kodlama_zinciri(p: dict, **_) -> Uretim:
    return _uret_varyantli("kodlama_zinciri", _vs.kur_kodlama, p)


def _coz_adaylari(veri: bytes):
    """Bir katmani acabilecek tum cozuculer (hangisi dogru bilinmez, hepsi denenir)."""
    yield lambda: gzip.decompress(veri)
    yield lambda: base64.b64decode(veri, validate=True)
    yield lambda: base64.b32decode(veri)
    yield lambda: bytes.fromhex(veri.decode("ascii"))
    yield lambda: urllib.parse.unquote_to_bytes(veri.decode("ascii"))
    yield lambda: _rot13(veri)


def cozucu_kodlama(veri: bytes, derinlik: int = 8) -> bytes | None:
    """Testler icin: ogrencinin yaptigi isi (katmanlari tek tek acma) deneme-yanilmayla
    yapar; icinde CAROT{...} bulursa o metni doner."""
    if re.search(rb"CAROT\{[0-9a-f]{8}\}", veri):   # tam bayrak bicimi: sahte "CAROT{" kalintilari sayilmaz
        return veri.strip()
    if derinlik == 0:
        return None
    for aday in _coz_adaylari(veri):
        try:
            sonuc = aday()
        except Exception:  # noqa: BLE001
            continue
        if sonuc == veri:
            continue
        bulundu = cozucu_kodlama(sonuc, derinlik - 1)
        if bulundu:
            return bulundu
    return None


def uret_sezar(p: dict, **_) -> Uretim:
    return _uret_varyantli("sezar", _vs.kur_sezar, p)


# ----------------------------------------------------------------------------
# 5) Dosya adli analizi: uzantisi yalan soyleyen dosya
# ----------------------------------------------------------------------------

def uret_dosya_adli(p: dict, **_) -> Uretim:
    gizleme = str(p.get("gizleme", "strings"))
    bayrak = flag_uret()
    dizin = _dizin_ac()
    if gizleme == "strings":
        govde = bytearray(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00")
        parcalar = [_RNG.randbytes(_RNG.randint(300, 900)) for _ in range(3)]
        notlar = (b"Exif\x00Adobe Photoshop 25.0", b"ICC_PROFILE sRGB IEC61966-2.1",
                  b"NOTFLAG{decoy-" + secrets_hex(4) + b"}")
        govde += parcalar[0] + notlar[0] + parcalar[1] + b"\x00" + bayrak.encode() + b"\x00" \
            + notlar[1] + parcalar[2] + notlar[2]
        veri = bytes(govde)
    elif gizleme == "gzip":
        satirlar = [f"kayit {i}: durum normal" for i in range(_RNG.randint(8, 20))]
        satirlar.insert(_RNG.randint(1, len(satirlar) - 1), f"gizli kod: {bayrak}")
        veri = gzip.compress(("\n".join(satirlar) + "\n").encode(), mtime=0)
    elif gizleme == "tar":
        arsiv = io.BytesIO()
        with tarfile.open(fileobj=arsiv, mode="w") as t:
            adlar = _RNG.sample(["rapor", "notlar", "liste", "taslak", "ozet", "yedek", "plan"], k=5)
            hedef_ad = _RNG.choice(adlar)
            for ad in adlar:
                icerik = (f"{ad}: bos\n" if ad != hedef_ad
                          else f"{ad}: onemli kod {bayrak}\n").encode()
                bilgi = tarfile.TarInfo(f"belgeler/{ad}.txt")
                bilgi.size = len(icerik)
                bilgi.mtime = 0
                t.addfile(bilgi, io.BytesIO(icerik))
        veri = gzip.compress(arsiv.getvalue(), mtime=0)
    else:
        raise ValueError(f"gecersiz gizleme: {gizleme!r}")
    yol = _yaz(dizin, "resim.jpg", veri)
    return Uretim(bayrak, {"{dosya}": yol}, yol, dizin)


def secrets_hex(n: int) -> bytes:
    return _RNG.randbytes(n).hex().encode()


# ----------------------------------------------------------------------------
# 6) Hash turunu tanima
# ----------------------------------------------------------------------------

_HEX = "0123456789abcdef"
_CRYPT64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def _rast(alfabe: str, n: int) -> str:
    return "".join(_RNG.choice(alfabe) for _ in range(n))


_HASH_URETICI = {
    "md5": lambda: _rast(_HEX, 32),
    "sha1": lambda: _rast(_HEX, 40),
    "sha256": lambda: _rast(_HEX, 64),
    "sha512": lambda: _rast(_HEX, 128),
    "md5crypt": lambda: f"$1${_rast(_CRYPT64, 8)}${_rast(_CRYPT64, 22)}",
    "sha256crypt": lambda: f"$5${_rast(_CRYPT64, 8)}${_rast(_CRYPT64, 43)}",
    "sha512crypt": lambda: f"$6${_rast(_CRYPT64, 8)}${_rast(_CRYPT64, 86)}",
    "bcrypt": lambda: f"$2b$12${_rast(_CRYPT64, 53)}",
}
_HASH_GRUPLARI = {
    "temel": ("md5", "sha1", "sha256", "sha512"),
    "unix": ("md5crypt", "sha256crypt", "sha512crypt", "bcrypt"),
    "karma": tuple(_HASH_URETICI),
}


def uret_hash_turu(p: dict, **_) -> Uretim:
    n = _tam_sayi(p, "kullanici_sayisi", 4, 1, 10)
    grup = _HASH_GRUPLARI.get(str(p.get("cesit", "temel")))
    if grup is None:
        raise ValueError("gecersiz cesit")
    kullanicilar = _RNG.sample(_MESRU_KULLANICILAR, k=n)
    turler = [_RNG.choice(grup) for _ in kullanicilar]
    satirlar = [f"{k}:{_HASH_URETICI[t]()}" for k, t in zip(kullanicilar, turler)]
    i = _RNG.randrange(n)
    dizin = _dizin_ac()
    yol = _yaz(dizin, "hashler.txt", "\n".join(satirlar) + "\n")
    return Uretim(turler[i], {"{dosya}": yol, "{hedef_kullanici}": kullanicilar[i],
                              "{hash_turleri}": ", ".join(grup)}, yol, dizin)


# ----------------------------------------------------------------------------
# 7) Gizli web sayfasi (loopback sunucu)
# ----------------------------------------------------------------------------

_SOZLUK_KELIMELERI = (
    "admin", "yonetim", "panel", "yedek", "eski", "test", "dahili", "gizli", "portal", "api",
    "gecici", "arsiv", "belgeler", "dosyalar", "indir", "kayit", "rapor", "ayarlar", "sistem",
    "destek", "forum", "blog", "haber", "galeri", "medya", "resim", "veri", "mail", "ftp",
    "git", "dev", "stage", "beta", "demo", "kurulum", "guncelle", "log", "tmp", "private",
    "kullanici", "musteri", "satis", "muhasebe", "ik", "bilgi", "iletisim", "hakkimizda",
    "urunler", "sepet", "odeme",
)


def _bos_port(bind: str, alt: int, ust: int) -> int:
    adaylar = list(range(alt, ust + 1))
    _RNG.shuffle(adaylar)
    for p in adaylar[:200]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((bind, p))
            except OSError:
                continue
        return p
    raise RuntimeError("bos port bulunamadi")


def uret_gizli_sayfa(p: dict, bind_adres: str = "127.0.0.1", **_) -> Uretim:
    from servisler.sahte_site import SahteSite
    kesif = str(p.get("kesif", "robots"))
    bayrak = flag_uret()
    kelimeler = list(_SOZLUK_KELIMELERI)
    gizli = _RNG.choice(kelimeler)
    yemler = _RNG.sample([k for k in kelimeler if k != gizli], k=3)
    port = _bos_port(bind_adres, 30000, 39999)
    site = SahteSite(bind_adres, port, gizli, bayrak, kesif, yemler)
    site.baslat()
    dizin = _dizin_ac()
    degisken = {"{port}": str(port)}
    if kesif != "robots":
        _RNG.shuffle(kelimeler)
        yol = _yaz(dizin, "sozluk.txt", "\n".join(kelimeler) + "\n")
        degisken["{sozluk}"] = yol
    else:
        degisken["{sozluk}"] = "-"
    return Uretim(bayrak, degisken, None, dizin, kapat=[site.durdur])


# ----------------------------------------------------------------------------
# 8) Servis basligi (banner) avi
# ----------------------------------------------------------------------------

def uret_banner_avi(p: dict, bind_adres: str = "127.0.0.1", **_) -> Uretim:
    from servisler.sahte_banner import SahteBannerOrtami
    n = _tam_sayi(p, "port_sayisi", 5, 3, 15)
    ar = p.get("port_araligi") or [24000, 24099]
    alt, ust = int(ar[0]), int(ar[1])
    if not (1024 <= alt < ust <= 65535) or ust - alt + 1 < n:
        raise ValueError("gecersiz port araligi")
    adaylar = list(range(alt, ust + 1))
    _RNG.shuffle(adaylar)
    portlar = []
    for pt in adaylar:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((bind_adres, pt))
            except OSError:
                continue
        portlar.append(pt)
        if len(portlar) == n:
            break
    if len(portlar) < n:
        raise RuntimeError("aralikta yeterli bos port yok")
    surum = f"{_RNG.randint(1, 9)}.{_RNG.randint(0, 9)}.{_RNG.randint(0, 20)}"
    ortam = SahteBannerOrtami(bind_adres, portlar, _RNG.choice(portlar), surum,
                              str(p.get("mod", "hemen")))
    ortam.baslat()
    return Uretim(surum, {"{port_sayisi}": str(n)}, None, None, kapat=[ortam.durdur])


# ----------------------------------------------------------------------------
# 9) CarotPot kayitlarini oku (lab + benzetilmis saldirganlar)
# ----------------------------------------------------------------------------

def uret_tuzak_kayit_oku(p: dict, bind_adres: str = "127.0.0.1", **_) -> Uretim:
    from tuzak_laboratuvari import TuzakLab
    n_sald = _tam_sayi(p, "saldirgan_sayisi", 3, 2, 6)
    hizmetler = list(p.get("hizmetler") or ["ftp"])
    ar = p.get("tuzak_port_araligi") or [21000, 21999]
    lab = TuzakLab(bind_adres, hizmetler, tuple(ar))
    lab.baslat()
    try:
        # benzetilmis saldirganlar: kaynak adresleri 127.x.y.z (yalniz loopback)
        kaynaklar = [f"127.{_RNG.randint(1, 250)}.{_RNG.randint(1, 250)}.{_RNG.randint(1, 250)}"
                     for _ in range(n_sald)]
        kaynaklar = list(dict.fromkeys(k for k in kaynaklar if k != bind_adres))
        if len(kaynaklar) < 2:
            kaynaklar = ["127.10.0.1", "127.20.0.1"]
        ust = _tam_sayi(p, "en_cok_deneme", 8, 5, 30)
        sayilar = _sayac_dagilimi(len(kaynaklar), ust, False)
        for ip, adet in zip(kaynaklar, sayilar):
            for _ in range(adet):
                _tuzaga_giris_dene(lab, ip, _RNG.choice(hizmetler))
        # Dogru cevap tuzagin KENDI kaydindan hesaplanir: en cok olay ureten
        # kaynak. Kayitlarin yazilmasi bitene kadar beklenir; esitlik olursa
        # ilk kaynak birkac deneme daha yapar.
        cevap = ""
        for _tur in range(3):
            onceki, sabit = -1, 0
            sayim: dict[str, int] = {}
            bitis = time.time() + 6
            while time.time() < bitis and sabit < 3:
                sayim = {}
                for o in lab.olaylar(tur=None):
                    if o.get("kaynak") in kaynaklar:
                        sayim[o["kaynak"]] = sayim.get(o["kaynak"], 0) + 1
                toplam = sum(sayim.values())
                sabit = sabit + 1 if (toplam == onceki and toplam > 0) else 0
                onceki = toplam
                time.sleep(0.2)
            if not sayim:
                raise RuntimeError("tuzak hicbir olay kaydetmedi")
            try:
                cevap = _en_cok(sayim)
                break
            except AssertionError:
                for _ in range(3):
                    _tuzaga_giris_dene(lab, kaynaklar[0], _RNG.choice(hizmetler))
        if not cevap:
            raise RuntimeError("en cok olay ureten kaynak belirlenemedi")
    except BaseException:
        lab.durdur()
        raise
    veri_dizini = str(lab._dizin / "veri")
    rapor = f"python3 {lab._yol} report --durum-dizini {veri_dizini}"
    return Uretim(cevap, {"{rapor_komutu}": rapor, "{veri_dizini}": veri_dizini,
                          "{tuzaklar}": ", ".join(h.upper() for h in hizmetler)},
                  None, None, kapat=[lab.durdur])


def _tuzaga_giris_dene(lab, kaynak_ip: str, hizmet: str) -> None:
    kullanici = _RNG.choice(_SALDIRGAN_KULLANICILAR)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.bind((kaynak_ip, 0))
        s.connect((lab.bind_adres, lab.portlar[hizmet]))
        try:
            if hizmet == "ftp":
                s.recv(200)
                s.sendall(f"USER {kullanici}\r\n".encode())
                s.recv(200)
                s.sendall(b"PASS 123456\r\n")
                s.recv(200)
            elif hizmet == "telnet":
                s.recv(300)
                s.sendall(f"{kullanici}\r\n".encode())
                s.recv(300)
                s.sendall(b"123456\r\n")
                s.recv(300)
            else:  # http
                govde = f"username={kullanici}&password=123456".encode()
                s.sendall(b"POST /login HTTP/1.1\r\nHost: x\r\nContent-Length: "
                          + str(len(govde)).encode() + b"\r\n\r\n" + govde)
                s.recv(2000)
        finally:
            s.close()
    except OSError:
        pass


# ----------------------------------------------------------------------------
# Kayit defteri
# ----------------------------------------------------------------------------

URETECLER = {
    "ssh_saldirgan": uret_ssh_saldirgan,
    "ssh_giren": uret_ssh_giren,
    "web_tarayici": uret_web_tarayici,
    "carotpot_kayit": uret_carotpot_kayit,
    "kodlama_zinciri": uret_kodlama_zinciri,
    "sezar": uret_sezar,
    "dosya_adli": uret_dosya_adli,
    "hash_turu": uret_hash_turu,
    "gizli_sayfa": uret_gizli_sayfa,
    "banner_avi": uret_banner_avi,
    "tuzak_kayit_oku": uret_tuzak_kayit_oku,
}

# Ag baglayan uretecler: bind_adres loopback olmak ZORUNDA
AG_URETECLERI = {"gizli_sayfa", "banner_avi", "tuzak_kayit_oku"}


def uret(ad: str, parametreler: dict | None = None, sabit: dict | None = None,
         bind_adres: str = "127.0.0.1") -> Uretim:
    """Adi verilen uretecle bir gorev icerigi uretir. Ag uretecleri icin
    bind_adres loopback degilse ValueError."""
    fonk = URETECLER.get(ad)
    if fonk is None:
        raise ValueError(f"bilinmeyen uretec: {ad!r}")
    if ad in AG_URETECLERI and not loopback_adres_mi(bind_adres):
        raise ValueError(f"{ad}: yalniz loopback adresinde calisir: {bind_adres!r}")
    p = {**(sabit or {}), **(parametreler or {})}
    return fonk(p, bind_adres=bind_adres, **{k: v for k, v in p.items() if k == "soru"})
