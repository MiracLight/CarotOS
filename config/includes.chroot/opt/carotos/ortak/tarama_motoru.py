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

import errno
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

# Ortak yetki yardimcisi (ayni klasorde): root'a giden programlar yalnizca
# sistem dizinlerinde aranir (T-03, O-01).
_ORTAK = os.path.dirname(os.path.abspath(__file__))
if _ORTAK not in sys.path:
    sys.path.insert(0, _ORTAK)
from yetkili import sistem_yolu  # noqa: E402

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
KISMI = "__KISMI__"                    # bazi dosyalar taranamadi; sonuc eksik (T-02)
YARIDA = "__YARIDA__"                  # clamscan sinyalle oldu (orn. bellek); sonuc eksik
DOSYA_DEGISTI = "__DOSYA_DEGISTI__"    # dosya taramadan sonra degisti (T-01)
DOGRULANAMADI = "__DOGRULANAMADI__"    # bulgunun hangi dosya oldugu dogrulanamadi (T-01)
KAYNAK_SILINEMEDI = "__KAYNAK_SILINEMEDI__"  # kopyalandi ama ozgun silinemedi (T-05)
YER_YOK = "__YER_YOK__"                # diskte yer yok (T-05)
KAYIT_HATASI = "__KAYIT_HATASI__"      # karantina kaydi yazilamadi (T-04)
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
    # Root olarak calisir: kullanicinin PATH'ine bakilmaz (T-03)
    return sistem_yolu("freshclam")


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
        # "x: FOUND" gibi bicimsiz satirlar istisna atmasin (U-05)
        yol, ayrac, imza = satir[:-len(" FOUND")].rpartition(": ")
        if not (ayrac and yol and imza.strip()):
            return "uyari", satir
        return "bulgu", (yol, imza)
    if satir.endswith(": OK"):
        return "temiz", satir[:-len(": OK")]
    if ": " in satir:
        return "atlandi", satir.rsplit(": ", 1)[0]
    return "uyari", satir


def _kimlik_bilgisi(bilgi):
    return [bilgi.st_dev, bilgi.st_ino, bilgi.st_size, bilgi.st_mtime_ns]


def dosya_kimligi(yol):
    """Duz dosyanin kimligi [aygit, inode, boyut, mtime_ns]; degilse None."""
    try:
        bilgi = os.lstat(yol)
    except (OSError, ValueError):
        return None
    return _kimlik_bilgisi(bilgi) if stat.S_ISREG(bilgi.st_mode) else None


def satir_sonlu_ad_var(yollar):
    """Taranan koklerde adinda satir sonu (\\n, \\r) olan bir girdi var mi?"""
    for kok in yollar:
        if "\n" in kok or "\r" in kok:
            return True
        if not os.path.isdir(kok) or os.path.islink(kok):
            continue
        for _dizin, dizinler, dosyalar in os.walk(kok, followlinks=False,
                                                  onerror=lambda _h: None):
            if any("\n" in ad or "\r" in ad for ad in dizinler + dosyalar):
                return True
    return False


def _kok_altinda(yol, kokler):
    for kok in kokler:
        kok = kok.rstrip("/") or "/"
        if yol == kok or yol.startswith(kok if kok == "/" else kok + "/"):
            return True
    return False


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
        try:
            for satir in self.surec.stdout:
                tur, veri = satir_coz(satir)
                if tur == "temiz":
                    sonuc["taranan"] += 1
                elif tur == "bulgu":
                    sonuc["taranan"] += 1
                    # Tarama anindaki dosya kimligi: islemden once yeniden
                    # denetlenir; degistiyse islem yapilmaz (T-01)
                    sonuc["bulgular"].append({"yol": veri[0], "imza": veri[1],
                                              "kimlik": dosya_kimligi(veri[0])})
                elif tur == "atlandi":
                    sonuc["atlanan"] += 1
                elif tur == "uyari":
                    if len(sonuc["uyarilar"]) < 50:
                        sonuc["uyarilar"].append(veri)
                if tur and self.olay:
                    self.olay(tur, veri)
        except Exception:  # noqa: BLE001 -- okuma/olay hatasi taramayi "calisiyor" birakmasin (U-05)
            sonuc["hata"] = True
            self._durdur()
        finally:
            try:
                self.surec.stdout.close()
            except OSError:
                pass
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
        if sonuc["bulgular"]:
            # Satir sonu iceren bir ad, clamscan satirini bolup bulguyu baska
            # (temiz) bir dosyaya gosterebilir. Boyle bir ad varsa ya da yol
            # taranan koklerin disindaysa bulgu dogrulanamaz sayilir (T-01).
            sonuc["satir_sonlu_ad"] = satir_sonlu_ad_var(self.yollar)
            for bulgu in sonuc["bulgular"]:
                if sonuc["satir_sonlu_ad"] or not _kok_altinda(bulgu["yol"], self.yollar):
                    bulgu["kimlik"] = None
        kod = sonuc["kod"]
        sonuc["eksik"] = kod not in (0, 1) or bool(sonuc.get("hata"))
        # TEMIZ yalnizca clamscan basariyla bittiyse verilir (T-02, U-03)
        if self.iptal_edildi:
            sonuc["durum"] = IPTAL
        elif sonuc["bulgular"]:
            sonuc["durum"] = BULGU
        elif sonuc.get("hata"):
            sonuc["durum"] = TARAMA_HATASI
        elif kod == 0 or (kod == 1 and sonuc["izinli"]):
            # kod 1 ve bulgu yok: yalnizca butun bulgular izin listesinden dustuyse
            sonuc["durum"] = TEMIZ
        elif kod is not None and kod < 0:
            sonuc["durum"] = YARIDA
        elif kod == 2 and sonuc["taranan"] > 0:
            sonuc["durum"] = KISMI
        else:
            # kod 2 ve hic dosya taranmadi, kod 1 ama bulgu ayristirilamadi,
            # ya da beklenmeyen bir cikis kodu
            sonuc["durum"] = TARAMA_HATASI
        self.sonuc = sonuc
        return sonuc

    def _durdur(self):
        if self.surec and self.surec.poll() is None:
            try:
                os.killpg(self.surec.pid, signal.SIGKILL)
            except OSError:
                pass

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
    """pkexec ile calisacak sabit komut; gerekli programlardan biri yoksa None.

    Kabuk yok ve butun programlar mutlak, yalnizca sistem dizinlerinden
    bulunan yollarla verilir (T-03, O-01): kullanici hesabindaki bir yazilim
    ~/.local/bin/freshclam birakarak root olamaz. Arka plandaki freshclam
    hizmeti ISO'da kapali (9991 kancasi); kullanici acmissa ve calisiyorsa
    freshclam kilit iletisi verir ve sonuc KILITLI olarak gosterilir."""
    pkexec, env, freshclam = (sistem_yolu("pkexec"), sistem_yolu("env"),
                              freshclam_yolu())
    if not (pkexec and env and freshclam):
        return None
    return [pkexec, env, "LC_ALL=C", "LANG=C", freshclam]


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


# Kayit defterleri (karantina, gecmis, izin listesi) ayni kurallarla okunur ve
# yazilir (T-04, O-04; Poligon P-20 deseni): bozuk ya da beklenmeyen bicimdeki
# defter sessizce bos sayilip EZILMEZ, "<ad>.bozuk-<zaman>" olarak kenara
# alinir; ogeler tur denetiminden gecer; yazma gecici dosya + fsync + replace.

def _sayi_mi(deger):
    return isinstance(deger, (int, float)) and not isinstance(deger, bool)


def _defter_oku(yol, gecerli):
    """(gecerli ogeler, bozuk_mu). bozuk_mu: dosya okunamadi, liste degil ya da
    gecersiz oge iceriyor."""
    try:
        with open(yol, encoding="utf-8") as fh:
            veri = json.load(fh)
    except FileNotFoundError:
        return [], False
    except (OSError, ValueError):
        return [], True
    if not isinstance(veri, list):
        return [], True
    ogeler = [k for k in veri if gecerli(k)]
    return ogeler, len(ogeler) != len(veri)


def _defter_yaz(yol, liste, gecerli):
    dizin = _gizli_dizin(os.path.dirname(yol))
    _ogeler, bozuk = _defter_oku(yol, gecerli)
    if bozuk and os.path.lexists(yol):
        os.replace(yol, "%s.bozuk-%d" % (yol, time.time_ns()))
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=os.path.basename(yol) + ".",
                                  suffix=".yeni")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(liste, fh, ensure_ascii=False, indent=1)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


_KARANTINA_ID = re.compile(r"[0-9a-f]{32}\Z")


def _karantina_kaydi_gecerli(k):
    return (isinstance(k, dict)
            and isinstance(k.get("id"), str) and bool(_KARANTINA_ID.match(k["id"]))
            and isinstance(k.get("asil_yol"), str) and os.path.isabs(k["asil_yol"])
            and "\0" not in k["asil_yol"]
            and _sayi_mi(k.get("tarih"))
            and isinstance(k.get("imza", ""), str)
            and isinstance(k.get("sha256", ""), str)
            and isinstance(k.get("mod", 0), int) and not isinstance(k.get("mod", 0), bool))


def _kayitlari_oku():
    return _defter_oku(_kayit_yolu(), _karantina_kaydi_gecerli)[0]


def _kayitlari_yaz(kayitlar):
    _defter_yaz(_kayit_yolu(), kayitlar, _karantina_kaydi_gecerli)


def karantina_listesi():
    return _kayitlari_oku()


def kayitsiz_karantina_dosyalari():
    """Karantina klasorunde olup kaydi bulunmayan dosyalarin kimlikleri.
    Ozgun konumlari bilinmedigi icin geri yuklenemez, yalnizca silinebilir."""
    kayitli = {k["id"] for k in _kayitlari_oku()}
    try:
        adlar = sorted(os.listdir(karantina_dizini()))
    except OSError:
        return []
    sonuc = []
    for ad in adlar:
        kok, uzanti = os.path.splitext(ad)
        if uzanti == ".karantina" and _KARANTINA_ID.match(kok) and kok not in kayitli:
            sonuc.append(kok)
    return sonuc


def _sha256(yol):
    with open(yol, "rb") as fh:
        return _sha256_fd(fh.fileno())


def _sha256_fd(fd):
    ozet = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    for parca in iter(lambda: os.read(fd, 1 << 20), b""):
        ozet.update(parca)
    os.lseek(fd, 0, os.SEEK_SET)
    return ozet.hexdigest()


def _ac_ve_denetle(yol, kimlik=None, sahip_denetle=True):
    """Dosyayi sembolik bag izlemeden acar ve denetler: (kod, fd, fstat).

    kimlik verilmisse (tarama anindaki [aygit, inode, boyut, mtime_ns]) dosya
    o kimlikle ayni olmalidir; degilse DOSYA_DEGISTI (T-01, T-07)."""
    try:
        bilgi = os.lstat(yol)
    except FileNotFoundError:
        return DOSYA_YOK, None, None
    except (OSError, ValueError):
        return YETKI_YOK, None, None
    if not stat.S_ISREG(bilgi.st_mode):
        return DUZ_DOSYA_DEGIL, None, None
    if sahip_denetle and bilgi.st_uid != os.getuid():
        return SAHIBI_DEGIL, None, None
    try:
        fd = os.open(yol, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return DOSYA_YOK, None, None
    except OSError as hata:
        return (DUZ_DOSYA_DEGIL if hata.errno == errno.ELOOP else YETKI_YOK), None, None
    acik = os.fstat(fd)
    if (not stat.S_ISREG(acik.st_mode) or acik.st_uid != bilgi.st_uid
            or (acik.st_dev, acik.st_ino) != (bilgi.st_dev, bilgi.st_ino)):
        os.close(fd)
        return DOSYA_DEGISTI, None, None
    if kimlik is not None and list(kimlik) != _kimlik_bilgisi(acik):
        os.close(fd)
        return DOSYA_DEGISTI, None, None
    return TAMAM, fd, acik


def _kimlik_denetimi(kimlik):
    """_DENETIMSIZ: eski cagri bicimi (kimlik verilmedi); None: bulgu tarama
    sirasinda dogrulanamadi -> islem yapilmaz."""
    if kimlik is _DENETIMSIZ:
        return TAMAM, None
    if kimlik is None:
        return DOGRULANAMADI, None
    if (not isinstance(kimlik, (list, tuple)) or len(kimlik) != 4
            or not all(isinstance(x, int) for x in kimlik)):
        return DOGRULANAMADI, None
    return TAMAM, kimlik


_DENETIMSIZ = object()


def _hata_kodu(hata, varsayilan=YETKI_YOK):
    if hata.errno in (errno.ENOSPC, errno.EDQUOT):
        return YER_YOK
    return varsayilan


def _yeni_dosyaya_kopyala(kaynak_fd, hedef, kip):
    """kaynak_fd icerigini YENI bir dosyaya (O_EXCL, kip kopyalanmaz) yazar.
    Basarisizlikta yarim hedef silinir; hata OSError olarak yukari gider."""
    hedef_fd = os.open(hedef, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.lseek(kaynak_fd, 0, os.SEEK_SET)
        for parca in iter(lambda: os.read(kaynak_fd, 1 << 20), b""):
            while parca:
                yazilan = os.write(hedef_fd, parca)
                parca = parca[yazilan:]
        os.fsync(hedef_fd)
        os.fchmod(hedef_fd, kip)
    except BaseException:
        os.close(hedef_fd)
        try:
            os.unlink(hedef)
        except OSError:
            pass
        raise
    os.close(hedef_fd)


def _karantinaya_tasi(yol, hedef, fd, acik):
    """Dosyayi karantinaya tasir; kod dondurur (T-05). Ayni bolumde rename;
    yalnizca EXDEV'de kopya + ozgunu silme. Basarisizlikta karantinada
    calistirilabilir bir kopya kalmaz."""
    try:
        os.rename(yol, hedef)
    except OSError as hata:
        if hata.errno != errno.EXDEV:
            return KAYNAK_SILINEMEDI if hata.errno == errno.EROFS else _hata_kodu(hata)
    else:
        try:
            yeni = os.lstat(hedef)
            if (yeni.st_dev, yeni.st_ino) != (acik.st_dev, acik.st_ino):
                # Denetim ile tasima arasinda dosya degistirilmis: geri koy
                os.rename(hedef, yol)
                return DOSYA_DEGISTI
            os.chmod(hedef, 0o400)
        except OSError:
            try:
                os.rename(hedef, yol)
            except OSError:
                pass
            return YETKI_YOK
        return TAMAM
    # Baska bolum (orn. USB bellek): kopya, sonra ozgun silinir
    try:
        _yeni_dosyaya_kopyala(fd, hedef, 0o400)
    except OSError as hata:
        return _hata_kodu(hata)
    try:
        simdi = os.lstat(yol)
        if (simdi.st_dev, simdi.st_ino) != (acik.st_dev, acik.st_ino):
            raise FileExistsError(errno.EEXIST, "degisti")
        os.unlink(yol)
    except OSError as hata:
        try:
            os.chmod(hedef, 0o600)
            os.unlink(hedef)
        except OSError:
            pass
        if isinstance(hata, FileExistsError) or hata.errno == errno.ENOENT:
            return DOSYA_DEGISTI
        return KAYNAK_SILINEMEDI
    return TAMAM


def karantinaya_al(yol, imza, kimlik=_DENETIMSIZ):
    """Dosyayi karantinaya tasir; (kod, kayit) dondurur.

    kimlik: bulgunun tarama anindaki kimligi (Tarama sonucundaki "kimlik").
    Once kayit yazilir, sonra dosya tasinir; tasima basarisiz olursa kayit geri
    alinir (T-04)."""
    kod, kimlik = _kimlik_denetimi(kimlik)
    if kod != TAMAM:
        return kod, None
    kod, fd, acik = _ac_ve_denetle(yol, kimlik)
    if kod != TAMAM:
        return kod, None
    try:
        try:
            dizin = _gizli_dizin(karantina_dizini())
            ozet = _sha256_fd(fd)
        except OSError:
            return YETKI_YOK, None
        kimlik_id = uuid.uuid4().hex
        hedef = os.path.join(dizin, kimlik_id + ".karantina")
        kayit = {"id": kimlik_id, "asil_yol": os.path.abspath(yol), "imza": str(imza),
                 "tarih": int(time.time()), "boyut": acik.st_size,
                 "sha256": ozet, "mod": stat.S_IMODE(acik.st_mode)}
        kayitlar = _kayitlari_oku()
        try:
            _kayitlari_yaz(kayitlar + [kayit])
        except OSError:
            return KAYIT_HATASI, None
        kod = _karantinaya_tasi(yol, hedef, fd, acik)
        if kod != TAMAM:
            try:
                _kayitlari_yaz(kayitlar)
            except OSError:
                pass
            return kod, None
        return TAMAM, kayit
    finally:
        os.close(fd)


def _bos_ad(yol):
    if not os.path.lexists(yol):
        return yol
    kok, uzanti = os.path.splitext(yol)
    for n in range(1, 1000):
        aday = f"{kok} (geri yüklendi {n}){uzanti}"
        if not os.path.lexists(aday):
            return aday
    return None


def _geri_tasi(kaynak, fd, asil_yol, kip):
    """Karantina dosyasini var olan hicbir dosyanin uzerine yazmadan geri
    koyar (T-07): link (hedef varsa EEXIST) ya da O_EXCL kopya. (kod, yol)"""
    for _deneme in range(3):
        hedef = _bos_ad(asil_yol)
        if not hedef:
            return YETKI_YOK, None
        try:
            os.link(kaynak, hedef)
        except FileExistsError:
            continue
        except OSError:
            # Baska bolum ya da bagi desteklemeyen dosya sistemi: kopya
            try:
                _yeni_dosyaya_kopyala(fd, hedef, kip)
            except FileExistsError:
                continue
            except OSError as hata:
                return _hata_kodu(hata), None
            try:
                os.unlink(kaynak)
            except OSError:
                pass
            return TAMAM, hedef
        try:
            os.unlink(kaynak)
            os.chmod(hedef, kip)
        except OSError:
            pass
        return TAMAM, hedef
    return YETKI_YOK, None


def geri_yukle(kimlik):
    """(kod, geri yuklenen yol) dondurur. Ayni adda dosya varsa uzerine
    yazilmaz; yeni bir ad secilir. Karantinadaki dosyanin ozeti kayittakiyle
    ayni olmalidir (T-01). Once kayit guncellenir, tasima basarisiz olursa
    geri alinir (T-04)."""
    kayitlar = _kayitlari_oku()
    kayit = next((k for k in kayitlar if k["id"] == kimlik), None)
    if not kayit:
        return DOSYA_YOK, None
    kaynak = os.path.join(karantina_dizini(), kimlik + ".karantina")
    kod, fd, _acik = _ac_ve_denetle(kaynak)
    if kod != TAMAM:
        return (DOSYA_YOK if kod == DOSYA_YOK else kod), None
    try:
        try:
            ozet = _sha256_fd(fd)
        except OSError:
            return YETKI_YOK, None
        if kayit.get("sha256") and ozet != kayit["sha256"]:
            return DOSYA_DEGISTI, None
        if not os.path.isdir(os.path.dirname(kayit["asil_yol"])):
            return KLASOR_YOK, None
        kalan = [k for k in kayitlar if k["id"] != kimlik]
        try:
            _kayitlari_yaz(kalan)
        except OSError:
            return KAYIT_HATASI, None
        kod, hedef = _geri_tasi(kaynak, fd, kayit["asil_yol"],
                                int(kayit.get("mod", 0o644)) & 0o7777)
        if kod != TAMAM:
            try:
                _kayitlari_yaz(kayitlar)
            except OSError:
                pass
            return kod, None
        return TAMAM, hedef
    finally:
        os.close(fd)


def karantinadan_sil(kimlik):
    """Karantinadaki dosyayi kalici olarak siler. Kaydi olmayan (yetim)
    karantina dosyalari da kimlikleriyle silinebilir."""
    if not isinstance(kimlik, str) or not _KARANTINA_ID.match(kimlik):
        return DOSYA_YOK
    kayitlar = _kayitlari_oku()
    kaynak = os.path.join(karantina_dizini(), kimlik + ".karantina")
    kayitli = any(k["id"] == kimlik for k in kayitlar)
    if not kayitli and not os.path.lexists(kaynak):
        return DOSYA_YOK
    if kayitli:
        try:
            _kayitlari_yaz([k for k in kayitlar if k["id"] != kimlik])
        except OSError:
            return KAYIT_HATASI
    try:
        if os.path.lexists(kaynak):
            if not os.path.islink(kaynak):
                os.chmod(kaynak, 0o600)
            os.unlink(kaynak)
    except OSError:
        if kayitli:
            try:
                _kayitlari_yaz(kayitlar)
            except OSError:
                pass
        return YETKI_YOK
    return TAMAM


def dosyayi_sil(yol, kimlik=_DENETIMSIZ):
    """Bulunan dosyayi kalici olarak siler (yalnizca kullanicinin kendi duz
    dosyasi). kimlik verilmisse dosya tarama anindakiyle ayni olmalidir."""
    kod, kimlik = _kimlik_denetimi(kimlik)
    if kod != TAMAM:
        return kod
    kod, fd, acik = _ac_ve_denetle(yol, kimlik)
    if kod != TAMAM:
        return kod
    try:
        simdi = os.lstat(yol)
        if (simdi.st_dev, simdi.st_ino) != (acik.st_dev, acik.st_ino):
            return DOSYA_DEGISTI
        os.unlink(yol)
    except FileNotFoundError:
        return DOSYA_YOK
    except OSError:
        return YETKI_YOK
    finally:
        os.close(fd)
    return TAMAM


# --- gecmis ---------------------------------------------------------------------------

GECMIS_SINIRI = 50


def _gecmis_yolu():
    return os.path.join(veri_dizini(), "gecmis.json")


def _gecmis_kaydi_gecerli(k):
    return isinstance(k, dict) and _sayi_mi(k.get("tarih"))


def gecmis():
    return _defter_oku(_gecmis_yolu(), _gecmis_kaydi_gecerli)[0]


def gecmise_ekle(tur, sonuc, simdi=None):
    kayit = {"tarih": int(simdi or time.time()), "tur": tur,
             "taranan": sonuc.get("taranan", 0),
             "bulgu": len(sonuc.get("bulgular", [])),
             "sure": sonuc.get("sure", 0), "durum": sonuc.get("durum"),
             "yollar": sonuc.get("yollar", [])[:5]}
    kayitlar = ([kayit] + gecmis())[:GECMIS_SINIRI]
    try:
        _defter_yaz(_gecmis_yolu(), kayitlar, _gecmis_kaydi_gecerli)
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


def _izin_kaydi_gecerli(k):
    return (isinstance(k, dict) and isinstance(k.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", k["sha256"]) is not None)


def izin_listesi():
    return _defter_oku(_izin_yolu(), _izin_kaydi_gecerli)[0]


def izin_listesi_ozetleri():
    return {k["sha256"] for k in izin_listesi()}


def _izin_yaz(kayitlar):
    _defter_yaz(_izin_yolu(), kayitlar, _izin_kaydi_gecerli)


def izin_listesine_ekle(yol, imza, kimlik=_DENETIMSIZ):
    kod, kimlik = _kimlik_denetimi(kimlik)
    if kod != TAMAM:
        return kod
    if kimlik is not None:
        kod, fd, _acik = _ac_ve_denetle(yol, kimlik, sahip_denetle=False)
        if kod != TAMAM:
            return kod
        try:
            ozet = _sha256_fd(fd)
        except OSError:
            return YETKI_YOK
        finally:
            os.close(fd)
    else:
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
