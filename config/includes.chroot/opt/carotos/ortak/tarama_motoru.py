# -*- coding: utf-8 -*-
"""
CarotOS ortak tarama motoru (ClamAV).

Carotene ve USB Denetimi bu modulu kullanir (karar D2). GTK'ya bagli
degildir; arayuz metni uretmez, dil bagimsiz kodlar dondurur. Uzun isler
cagiran tarafin is parcaciginda calisir.

Guvenlik kurallari:
- Kabuk kullanilmaz; yollar komuta liste argumani olarak ve "--"
  ayiracindan sonra verilir.
- Araclar LC_ALL=C ile calistirilir: ciktilari Ingilizce metinlere gore
  ayristirilir ve Turkce dil ayari bazi desenleri bozar.
- Karantina yalnizca kullanicinin kendi duz dosyalarina uygulanir.
"""

import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import time
import uuid

# --- dil bagimsiz kodlar -----------------------------------------------------
CLAMAV_YOK = "__CLAMAV_YOK__"          # clamscan kurulu degil
TANIM_YOK = "__TANIM_YOK__"            # tanim dosyasi bulunamadi
TANIM_ESKI = "__TANIM_ESKI__"          # tanimlar ESKI_GUN gunden eski
TANIM_GUNCEL = "__TANIM_GUNCEL__"
CEVRIMDISI = "__CEVRIMDISI__"          # guncelleme sunucusuna ulasilamadi
BEKLEME = "__BEKLEME__"                # sunucu gecici olarak reddetti
KILITLI = "__KILITLI__"                # baska bir guncelleme calisiyor
GUNCELLENDI = "__GUNCELLENDI__"
ZATEN_GUNCEL = "__ZATEN_GUNCEL__"
GUNCELLEME_HATASI = "__GUNCELLEME_HATASI__"
IPTAL = "__IPTAL__"
TEMIZ = "__TEMIZ__"
BULGU = "__BULGU__"
TARAMA_HATASI = "__TARAMA_HATASI__"
YETKI_YOK = "__YETKI_YOK__"
DOSYA_YOK = "__DOSYA_YOK__"
DUZ_DOSYA_DEGIL = "__DUZ_DOSYA_DEGIL__"
SAHIBI_DEGIL = "__SAHIBI_DEGIL__"
KLASOR_YOK = "__KLASOR_YOK__"
TAMAM = "__TAMAM__"

TANIM_DIZINI = "/var/lib/clamav"
TANIM_DOSYALARI = ("daily", "main", "bytecode")
ESKI_GUN = 7
# ClamAV tanimlari yuklerken yaklasik 1 GB bellek kullanir (olcum: 970 MB).
BELLEK_ESIK_MB = 1300

C_ORTAM = dict(os.environ, LC_ALL="C", LANG="C")


def clamscan_yolu():
    return shutil.which("clamscan")


def freshclam_yolu():
    return shutil.which("freshclam") or (
        "/usr/bin/freshclam" if os.path.exists("/usr/bin/freshclam") else None)


# --- veri klasorleri ----------------------------------------------------------

def veri_dizini():
    taban = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share")
    return os.path.join(taban, "carotene")


def karantina_dizini():
    return os.path.join(veri_dizini(), "karantina")


def _gizli_dizin(yol):
    os.makedirs(yol, mode=0o700, exist_ok=True)
    os.chmod(yol, 0o700)
    return yol


# --- tarama komutu ve cikti ayristirma ----------------------------------------

def tarama_komutu(yollar, haric_dizinler=()):
    """clamscan komutunu liste olarak kurar. Yollar mutlak olmalidir."""
    komut = [clamscan_yolu() or "clamscan", "-r", "--stdout", "--no-summary"]
    for dizin in haric_dizinler:
        komut.append("--exclude-dir=^" + re.escape(dizin.rstrip("/")) + "$")
    komut.append("--")
    komut.extend(yollar)
    return komut


def satir_coz(satir):
    """Bir clamscan satirini (tur, veri) olarak dondurur.

    tur: "temiz" (yol), "bulgu" ((yol, imza)), "uyari" (metin),
    "atlandi" (yol), None (bos satir)."""
    satir = satir.rstrip("\n")
    if not satir.strip():
        return None, None
    if satir.startswith(("WARNING:", "ERROR:", "LibClamAV")):
        return "uyari", satir
    if satir.endswith(" FOUND") and ": " in satir:
        yol, imza = satir[:-len(" FOUND")].rsplit(": ", 1)
        return "bulgu", (yol, imza)
    if satir.endswith(": OK"):
        return "temiz", satir[:-len(": OK")]
    if ": " in satir:
        return "atlandi", satir.rsplit(": ", 1)[0]
    return "uyari", satir


class Tarama:
    """Iptal edilebilir clamscan calistirmasi.

    olay(tur, veri) her satirda cagrilir (cagiranin is parcaciginda);
    arayuz guncellemesi cagiranin sorumlulugundadir."""

    def __init__(self, yollar, haric_dizinler=(), olay=None):
        self.yollar = list(yollar)
        self.haric = list(haric_dizinler)
        self.olay = olay
        self.surec = None
        self.iptal_edildi = False
        self.sonuc = None

    def calistir(self):
        baslangic = time.time()
        sonuc = {"taranan": 0, "atlanan": 0, "bulgular": [], "uyarilar": [],
                 "izinli": [], "kod": None, "durum": None, "sure": 0.0,
                 "yollar": list(self.yollar)}
        if not clamscan_yolu():
            sonuc["durum"] = CLAMAV_YOK
            self.sonuc = sonuc
            return sonuc
        if self.iptal_edildi:
            sonuc["durum"] = IPTAL
            self.sonuc = sonuc
            return sonuc
        try:
            self.surec = subprocess.Popen(
                tarama_komutu(self.yollar, self.haric),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, env=C_ORTAM, text=True,
                errors="replace", start_new_session=True)
        except OSError:
            sonuc["durum"] = TARAMA_HATASI
            self.sonuc = sonuc
            return sonuc
        if self.iptal_edildi:
            # Iptal, surec baslarken geldiyse hemen durdur
            self.iptal()
        for satir in self.surec.stdout:
            tur, veri = satir_coz(satir)
            if tur == "temiz":
                sonuc["taranan"] += 1
            elif tur == "bulgu":
                sonuc["taranan"] += 1
                sonuc["bulgular"].append({"yol": veri[0], "imza": veri[1]})
            elif tur == "atlandi":
                sonuc["atlanan"] += 1
            elif tur == "uyari":
                if len(sonuc["uyarilar"]) < 50:
                    sonuc["uyarilar"].append(veri)
            if tur and self.olay:
                self.olay(tur, veri)
        self.surec.stdout.close()
        sonuc["kod"] = self.surec.wait()
        sonuc["sure"] = round(time.time() - baslangic, 1)
        # Kullanicinin "her zaman yok say" dedigi, ICERIGI degismemis dosyalar
        # bildirilmez; dosya degistiyse parmak izi tutmaz ve yine bildirilir.
        if sonuc["bulgular"]:
            izinliler = izin_listesi_ozetleri()
            kalan = []
            for bulgu in sonuc["bulgular"]:
                ozet = _dosya_ozeti(bulgu["yol"]) if izinliler else None
                (sonuc["izinli"] if ozet and ozet in izinliler else kalan).append(bulgu)
            sonuc["bulgular"] = kalan
        if self.iptal_edildi:
            sonuc["durum"] = IPTAL
        elif sonuc["bulgular"]:
            sonuc["durum"] = BULGU
        elif sonuc["kod"] == 0:
            sonuc["durum"] = TEMIZ
        elif sonuc["kod"] == 2 and sonuc["taranan"] == 0:
            sonuc["durum"] = TARAMA_HATASI
        else:
            # clamscan 2 doner ama bazi dosyalar okunamadiysa tarama yine
            # de yapilmistir; okunamayanlar uyari olarak listelenir.
            sonuc["durum"] = TEMIZ
        self.sonuc = sonuc
        return sonuc

    def iptal(self):
        self.iptal_edildi = True
        if self.surec and self.surec.poll() is None:
            try:
                os.killpg(self.surec.pid, signal.SIGTERM)
            except OSError:
                pass


# --- hizli tarama hedefleri -----------------------------------------------------

def xdg_dizini(anahtar, ev=None):
    """user-dirs.dirs icinden XDG_<ANAHTAR>_DIR degerini okur."""
    ev = ev or os.path.expanduser("~")
    dosya = os.path.join(os.environ.get("XDG_CONFIG_HOME")
                         or os.path.join(ev, ".config"), "user-dirs.dirs")
    try:
        with open(dosya, encoding="utf-8") as fh:
            for satir in fh:
                m = re.match(r'\s*XDG_%s_DIR="(.*)"' % anahtar, satir)
                if m:
                    deger = m.group(1).replace("$HOME", ev)
                    if os.path.isabs(deger) and os.path.normpath(deger) != ev:
                        return deger
    except OSError:
        pass
    return None


def hizli_tarama_yollari(ev=None):
    """Indirilenler ve Masaustu (alt klasorleriyle) ile ev klasorunun ust
    duzeyindeki dosyalar. Var olmayanlar atlanir."""
    ev = ev or os.path.expanduser("~")
    yollar = []
    for anahtar, yedek in (("DOWNLOAD", ("İndirilenler", "Downloads")),
                           ("DESKTOP", ("Masaüstü", "Desktop"))):
        yol = xdg_dizini(anahtar, ev)
        adaylar = [yol] if yol else [os.path.join(ev, ad) for ad in yedek]
        for aday in adaylar:
            if aday and os.path.isdir(aday) and aday not in yollar:
                yollar.append(aday)
                break
    try:
        for ad in sorted(os.listdir(ev)):
            tam = os.path.join(ev, ad)
            if os.path.isfile(tam) and not os.path.islink(tam):
                yollar.append(tam)
    except OSError:
        pass
    return yollar


# --- bellek ---------------------------------------------------------------------

def kullanilabilir_bellek_mb(meminfo=None):
    if meminfo is None:
        try:
            with open("/proc/meminfo", encoding="ascii") as fh:
                meminfo = fh.read()
        except OSError:
            return None
    m = re.search(r"^MemAvailable:\s+(\d+)\s*kB", meminfo, re.M)
    return int(m.group(1)) // 1024 if m else None


def bellek_yeterli(meminfo=None):
    mb = kullanilabilir_bellek_mb(meminfo)
    return (mb is None or mb >= BELLEK_ESIK_MB), mb


# --- tanim dosyalari --------------------------------------------------------------

def cvd_basligi_coz(baslik):
    """CVD/CLD basligini cozer.

    Bicim: ClamAV-VDB:<tarih>:<surum>:<imza>:<f-level>:<md5>:<dsig>:<yapan>:<unix>
    Tarih alani ":" icerdigi icin alanlar sondan okunur."""
    if isinstance(baslik, bytes):
        baslik = baslik.decode("latin-1")
    baslik = baslik.split("\0")[0].strip()
    if not baslik.startswith("ClamAV-VDB:"):
        return None
    alanlar = baslik.split(":")
    if len(alanlar) < 9:
        return None
    try:
        return {"surum": int(alanlar[-7]), "imza": int(alanlar[-6]),
                "zaman": int(alanlar[-1])}
    except ValueError:
        return None


def tanim_bilgisi(dizin=TANIM_DIZINI, simdi=None):
    simdi = simdi or time.time()
    dosyalar = []
    for ad in TANIM_DOSYALARI:
        for uzanti in (".cld", ".cvd"):
            yol = os.path.join(dizin, ad + uzanti)
            try:
                with open(yol, "rb") as fh:
                    bilgi = cvd_basligi_coz(fh.read(512))
            except OSError:
                continue
            if bilgi:
                bilgi["ad"] = ad
                dosyalar.append(bilgi)
                break
    if not dosyalar:
        return {"durum": TANIM_YOK, "dosyalar": [], "imza": 0,
                "zaman": None, "yas_gun": None}
    zaman = max(d["zaman"] for d in dosyalar)
    yas = max(0, int((simdi - zaman) // 86400))
    return {"durum": TANIM_ESKI if yas > ESKI_GUN else TANIM_GUNCEL,
            "dosyalar": dosyalar, "imza": sum(d["imza"] for d in dosyalar),
            "zaman": zaman, "yas_gun": yas}


# --- tanim guncelleme ---------------------------------------------------------------

def guncelleme_komutu():
    """pkexec ile calisacak sabit komut. Arka plandaki freshclam hizmeti
    calisiyorsa tanim dosyalarini kilitler; once durdurulur."""
    return ["pkexec", "/bin/sh", "-c",
            "systemctl stop clamav-freshclam 2>/dev/null; "
            "LC_ALL=C " + (freshclam_yolu() or "/usr/bin/freshclam")]


def guncelleme_sonucu(kod, cikti):
    metin = cikti or ""
    if kod in (126, 127) and not metin.strip():
        return IPTAL
    if re.search(r"cool-?down|rate limit|too many requests|\b429\b", metin, re.I):
        return BEKLEME
    if re.search(r"lock|already running", metin, re.I) and kod != 0:
        return KILITLI
    if re.search(r"\b(updated|downloaded)\b", metin, re.I) and kod == 0:
        return GUNCELLENDI
    if re.search(r"up[- ]to[- ]date", metin, re.I) and kod in (0, 1):
        return ZATEN_GUNCEL
    if re.search(r"Can't (connect|resolve)|resolve host|Download failed|"
                 r"HTTP GET failed|timed? ?out|No route|Network is unreachable|"
                 r"Failure when receiving", metin, re.I):
        return CEVRIMDISI
    if kod == 0:
        return GUNCELLENDI
    return GUNCELLEME_HATASI


# --- karantina ------------------------------------------------------------------------

def _kayit_yolu():
    return os.path.join(karantina_dizini(), "kayitlar.json")


def _kayitlari_oku():
    try:
        with open(_kayit_yolu(), encoding="utf-8") as fh:
            veri = json.load(fh)
        return veri if isinstance(veri, list) else []
    except (OSError, ValueError):
        return []


def _kayitlari_yaz(kayitlar):
    _gizli_dizin(karantina_dizini())
    gecici = _kayit_yolu() + ".yeni"
    with open(gecici, "w", encoding="utf-8") as fh:
        json.dump(kayitlar, fh, ensure_ascii=False, indent=1)
    os.chmod(gecici, 0o600)
    os.replace(gecici, _kayit_yolu())


def karantina_listesi():
    return _kayitlari_oku()


def _sha256(yol):
    ozet = hashlib.sha256()
    with open(yol, "rb") as fh:
        for parca in iter(lambda: fh.read(1 << 20), b""):
            ozet.update(parca)
    return ozet.hexdigest()


def _tasi(kaynak, hedef):
    try:
        os.rename(kaynak, hedef)
    except OSError:
        shutil.copy2(kaynak, hedef)
        os.unlink(kaynak)


def karantinaya_al(yol, imza):
    """Dosyayi karantinaya tasir; (kod, kayit) dondurur."""
    try:
        bilgi = os.lstat(yol)
    except FileNotFoundError:
        return DOSYA_YOK, None
    except OSError:
        return YETKI_YOK, None
    if not stat.S_ISREG(bilgi.st_mode):
        return DUZ_DOSYA_DEGIL, None
    if bilgi.st_uid != os.getuid():
        return SAHIBI_DEGIL, None
    dizin = _gizli_dizin(karantina_dizini())
    kimlik = uuid.uuid4().hex
    hedef = os.path.join(dizin, kimlik + ".karantina")
    try:
        ozet = _sha256(yol)
        _tasi(yol, hedef)
        os.chmod(hedef, 0o400)
    except OSError:
        return YETKI_YOK, None
    kayit = {"id": kimlik, "asil_yol": os.path.abspath(yol), "imza": imza,
             "tarih": int(time.time()), "boyut": bilgi.st_size,
             "sha256": ozet, "mod": stat.S_IMODE(bilgi.st_mode)}
    kayitlar = _kayitlari_oku()
    kayitlar.append(kayit)
    _kayitlari_yaz(kayitlar)
    return TAMAM, kayit


def _bos_ad(yol):
    if not os.path.lexists(yol):
        return yol
    kok, uzanti = os.path.splitext(yol)
    for n in range(1, 1000):
        aday = f"{kok} (geri yüklendi {n}){uzanti}"
        if not os.path.lexists(aday):
            return aday
    return None


def geri_yukle(kimlik):
    """(kod, geri yuklenen yol) dondurur. Ayni adda dosya varsa uzerine
    yazilmaz; yeni bir ad secilir."""
    kayitlar = _kayitlari_oku()
    kayit = next((k for k in kayitlar if k.get("id") == kimlik), None)
    if not kayit:
        return DOSYA_YOK, None
    kaynak = os.path.join(karantina_dizini(), kimlik + ".karantina")
    if not os.path.isfile(kaynak):
        return DOSYA_YOK, None
    if not os.path.isdir(os.path.dirname(kayit["asil_yol"])):
        return KLASOR_YOK, None
    hedef = _bos_ad(kayit["asil_yol"])
    if not hedef:
        return YETKI_YOK, None
    try:
        os.chmod(kaynak, 0o600)
        _tasi(kaynak, hedef)
        os.chmod(hedef, int(kayit.get("mod", 0o644)) & 0o7777)
    except OSError:
        return YETKI_YOK, None
    _kayitlari_yaz([k for k in kayitlar if k.get("id") != kimlik])
    return TAMAM, hedef


def karantinadan_sil(kimlik):
    kayitlar = _kayitlari_oku()
    if not any(k.get("id") == kimlik for k in kayitlar):
        return DOSYA_YOK
    kaynak = os.path.join(karantina_dizini(), kimlik + ".karantina")
    try:
        if os.path.lexists(kaynak):
            os.chmod(kaynak, 0o600)
            os.unlink(kaynak)
    except OSError:
        return YETKI_YOK
    _kayitlari_yaz([k for k in kayitlar if k.get("id") != kimlik])
    return TAMAM


def dosyayi_sil(yol):
    """Bulunan dosyayi kalici olarak siler (yalnizca kullanicinin kendi duz
    dosyasi)."""
    try:
        bilgi = os.lstat(yol)
    except FileNotFoundError:
        return DOSYA_YOK
    except OSError:
        return YETKI_YOK
    if not stat.S_ISREG(bilgi.st_mode):
        return DUZ_DOSYA_DEGIL
    if bilgi.st_uid != os.getuid():
        return SAHIBI_DEGIL
    try:
        os.unlink(yol)
    except OSError:
        return YETKI_YOK
    return TAMAM


# --- gecmis ---------------------------------------------------------------------------

GECMIS_SINIRI = 50


def _gecmis_yolu():
    return os.path.join(veri_dizini(), "gecmis.json")


def gecmis():
    try:
        with open(_gecmis_yolu(), encoding="utf-8") as fh:
            veri = json.load(fh)
        return veri if isinstance(veri, list) else []
    except (OSError, ValueError):
        return []


def gecmise_ekle(tur, sonuc, simdi=None):
    kayit = {"tarih": int(simdi or time.time()), "tur": tur,
             "taranan": sonuc.get("taranan", 0),
             "bulgu": len(sonuc.get("bulgular", [])),
             "sure": sonuc.get("sure", 0), "durum": sonuc.get("durum"),
             "yollar": sonuc.get("yollar", [])[:5]}
    kayitlar = ([kayit] + gecmis())[:GECMIS_SINIRI]
    try:
        _gizli_dizin(veri_dizini())
        gecici = _gecmis_yolu() + ".yeni"
        with open(gecici, "w", encoding="utf-8") as fh:
            json.dump(kayitlar, fh, ensure_ascii=False, indent=1)
        os.replace(gecici, _gecmis_yolu())
    except OSError:
        pass
    return kayit


# --- izin listesi (her zaman yok sayilan dosyalar) -------------------------------
# Yol degil, dosyanin SHA-256 parmak izi saklanir: ayni dosya baska yere
# tasinsa da yok sayilir; icerigi degisirse yeniden bildirilir.

def _izin_yolu():
    return os.path.join(veri_dizini(), "izin_listesi.json")


def _dosya_ozeti(yol):
    try:
        if not os.path.isfile(yol) or os.path.islink(yol):
            return None
        return _sha256(yol)
    except OSError:
        return None


def izin_listesi():
    try:
        with open(_izin_yolu(), encoding="utf-8") as fh:
            veri = json.load(fh)
        return veri if isinstance(veri, list) else []
    except (OSError, ValueError):
        return []


def izin_listesi_ozetleri():
    return {k.get("sha256") for k in izin_listesi() if k.get("sha256")}


def _izin_yaz(kayitlar):
    _gizli_dizin(veri_dizini())
    gecici = _izin_yolu() + ".yeni"
    with open(gecici, "w", encoding="utf-8") as fh:
        json.dump(kayitlar, fh, ensure_ascii=False, indent=1)
    os.chmod(gecici, 0o600)
    os.replace(gecici, _izin_yolu())


def izin_listesine_ekle(yol, imza):
    ozet = _dosya_ozeti(yol)
    if not ozet:
        return DOSYA_YOK
    kayitlar = [k for k in izin_listesi() if k.get("sha256") != ozet]
    kayitlar.append({"sha256": ozet, "yol": os.path.abspath(yol), "imza": imza,
                     "tarih": int(time.time())})
    try:
        _izin_yaz(kayitlar)
    except OSError:
        return YETKI_YOK
    return TAMAM


def izin_listesinden_cikar(ozet):
    kayitlar = izin_listesi()
    kalan = [k for k in kayitlar if k.get("sha256") != ozet]
    if len(kalan) == len(kayitlar):
        return DOSYA_YOK
    try:
        _izin_yaz(kalan)
    except OSError:
        return YETKI_YOK
    return TAMAM


# --- dosya yoneticisinden gelen yollar ----------------------------------------------

def komut_satiri_yollari(argumanlar):
    """"--tara YOL..." argumanlarindan taranabilir mutlak yollari dondurur.
    Var olmayanlar ve goreli yollar atlanir; tekrarlar ayiklanir."""
    if "--tara" not in argumanlar:
        return None
    yollar = []
    for arg in argumanlar[argumanlar.index("--tara") + 1:]:
        if arg.startswith("file://"):
            from urllib.parse import unquote, urlparse
            arg = unquote(urlparse(arg).path)
        if not os.path.isabs(arg) or not os.path.exists(arg):
            continue
        gercek = os.path.realpath(arg)
        if gercek not in yollar:
            yollar.append(gercek)
    return yollar
