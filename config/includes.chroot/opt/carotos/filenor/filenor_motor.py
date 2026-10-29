# -*- coding: utf-8 -*-
"""
Filenor motoru -- arayüzden bağımsız (GTK yok).

Özgün Filenor (MiracLight) fikrinin CarotOS için yeniden yazılmış çekirdeği.
Hem GTK arayüzü hem `filenor-cli` bu modülü kullanır.

Tasarım ilkeleri
  * Dönüşüm yolları TEK bir tabloda (rota) tanımlıdır; arayüz seçenekleri,
    doğrulama ve dönüştürme aynı tablodan beslenir -> "listede var ama
    çalışmıyor" durumu olmaz.
  * Çıktı asla ezilmez: ad.ext doluysa "ad (1).ext". Ara dosyalar çıktı
    klasöründeki gizli bir iş klasörüne yazılır, bitince atomik taşınır, her
    durumda temizlenir.
  * Harici araçlar (ffmpeg, LibreOffice, poppler, qpdf, tesseract) liste
    argümanıyla çağrılır (kabuk yok), zaman aşımı ve iptal desteklidir.
  * Modül yoksa/araç yoksa neyin eksik olduğu ve nasıl kurulacağı söylenir.
"""

from __future__ import annotations

import csv
import functools
import glob
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field, fields
from typing import Callable, Iterable, Optional

import filenor_sistem as S
from filenor_dil import FilenorHata, Iptal, hata_metni, mesaj  # noqa: F401

S.ortam_hazirla()      # PATH'te olmayan ama kurulu araclari (Windows) bu surece tanit

SURUM = "1.0"

# ---------------------------------------------------------------------------
# Biçim tabloları
# ---------------------------------------------------------------------------
HAM = {"cr2", "nef", "arw", "dng", "orf", "sr2", "rw2", "raf"}
GORSEL = {"jpg", "png", "webp", "gif", "bmp", "tiff", "ico", "avif", "heic", "heif"}
GORSEL_YAZ = ["jpg", "png", "webp", "avif", "gif", "bmp", "tiff", "ico"]
VIDEO = {"mp4", "mkv", "webm", "mov", "avi", "m4v", "flv", "wmv", "ts", "mpg", "3gp"}
VIDEO_YAZ = ["mp4", "mkv", "webm", "mov", "avi"]
SES = {"mp3", "wav", "opus", "ogg", "m4a", "flac", "aac", "wma", "aiff"}
SES_YAZ = ["mp3", "m4a", "opus", "ogg", "flac", "wav", "aac"]
YAZIDOC = {"docx", "doc", "odt", "rtf"}
TABLO = {"xlsx", "xls", "ods", "csv"}
SUNUM = {"pptx", "ppt", "odp"}
YAZITIPI = ["ttf", "otf", "woff", "woff2"]

_TAKMA = {"jpeg": "jpg", "jfif": "jpg", "jpe": "jpg", "tif": "tiff", "htm": "html",
          "aif": "aiff", "mpeg": "mpg", "text": "txt"}

# Arayüz kategorileri (sıra = gösterim sırası)
KATEGORILER = ["gorsel", "video", "ses", "belge", "tablo", "sunum", "yazitipi"]


# Arayüzde hedef düğmelerinin kategori içi sırası
HEDEF_SIRASI = ["jpg", "png", "webp", "avif", "gif", "bmp", "tiff", "ico",
                "mp4", "mkv", "webm", "mov", "avi",
                "mp3", "m4a", "opus", "ogg", "flac", "wav", "aac",
                "pdf", "docx", "odt", "rtf", "txt", "html",
                "xlsx", "ods", "csv", "pptx", "odp",
                "ttf", "otf", "woff", "woff2"]


def norm(ext: str) -> str:
    ext = (ext or "").lower().lstrip(".")
    return _TAKMA.get(ext, ext)


def uzanti(yol: str) -> str:
    return norm(os.path.splitext(yol)[1])


def tur(ext: str) -> str:
    """Kaynak uzantısının ailesi: gorsel|ham|svg|video|ses|pdf|yazidoc|txt|html|tablo|sunum|yazitipi|''."""
    ext = norm(ext)
    if ext in HAM:
        return "ham"
    if ext == "svg":
        return "svg"
    if ext in GORSEL:
        return "gorsel"
    if ext in VIDEO:
        return "video"
    if ext in SES:
        return "ses"
    if ext == "pdf":
        return "pdf"
    if ext in YAZIDOC:
        return "yazidoc"
    if ext == "txt":
        return "txt"
    if ext == "html":
        return "html"
    if ext in TABLO:
        return "tablo"
    if ext in SUNUM:
        return "sunum"
    if ext in YAZITIPI:
        return "yazitipi"
    return ""


def hedef_kategorisi(hedef: str) -> str:
    """Hedef biçimin arayüz kategorisi."""
    h = norm(hedef)
    if h in GORSEL_YAZ:
        return "gorsel"
    if h in VIDEO_YAZ:
        return "video"
    if h in SES_YAZ:
        return "ses"
    if h in YAZITIPI:
        return "yazitipi"
    if h in ("xlsx", "ods", "csv"):
        return "tablo"
    if h in ("pptx", "odp"):
        return "sunum"
    return "belge"


def hedefler(ext: str) -> list[str]:
    """Bir kaynak uzantısından üretilebilen hedef biçimler (sıralı)."""
    ext = norm(ext)
    t = tur(ext)
    sec: list[str] = []
    if t == "gorsel":
        sec = [x for x in GORSEL_YAZ if x != ext] + ["pdf"]
        if ext == "gif":
            sec += ["mp4", "webm"]
    elif t == "ham":
        sec = ["jpg", "png", "webp", "tiff", "pdf"]
    elif t == "svg":
        sec = ["png", "jpg", "webp", "pdf"]
    elif t == "video":
        sec = [x for x in VIDEO_YAZ if x != ext] + ["gif"] + SES_YAZ
    elif t == "ses":
        sec = [x for x in SES_YAZ if x != ext]
    elif t == "pdf":
        sec = ["png", "jpg", "webp", "txt", "docx", "odt", "pptx", "odp"]
    elif t == "yazidoc":
        sec = [x for x in ("pdf", "docx", "odt", "rtf", "txt", "html") if x != ext]
    elif t == "txt":
        sec = ["pdf", "docx", "odt", "rtf", "html"]
    elif t == "html":
        sec = ["pdf", "docx", "odt", "rtf", "txt"]
    elif t == "tablo":
        sec = [x for x in ("pdf", "xlsx", "ods", "csv", "html") if x != ext]
    elif t == "sunum":
        sec = [x for x in ("pdf", "pptx", "odp", "png", "jpg") if x != ext]
    elif t == "yazitipi":
        sec = [x for x in YAZITIPI if x != ext]
    return sec


def kaynak_uzantilari() -> list[str]:
    tum = set(HAM) | GORSEL | {"svg"} | VIDEO | SES | {"pdf", "txt", "html"} | YAZIDOC | TABLO | SUNUM | set(YAZITIPI)
    return sorted(tum)


# ---------------------------------------------------------------------------
# Seçenekler
# ---------------------------------------------------------------------------
KALITELER = ("yuksek", "dengeli", "kucuk")


@dataclass
class Secenek:
    kalite: str = "dengeli"        # yuksek | dengeli | kucuk
    max_kenar: int = 0             # görsel: en uzun kenar px; video: en büyük yükseklik (0 = değiştirme)
    meta_temizle: bool = False     # EXIF/GPS/ICC ve ses-video üstverisini sil
    dpi: int = 150                 # PDF/sunum -> görsel
    sayfa_araligi: str = ""        # "1-3,5,8-"
    parola: str = ""               # PDF açma parolası
    yeni_parola: str = ""          # PDF kilitleme
    ocr_dil: str = "tur+eng"
    ocr_cikti: str = "txt"         # txt | pdf
    gif_fps: int = 12
    gif_genislik: int = 480
    derece: int = 90               # PDF döndürme
    parca: int = 1                 # PDF bölme: kaç sayfada bir
    baslangic: float = 0.0         # medya kırpma (sn)
    bitis: float = 0.0
    zip_yap: bool = False

    @classmethod
    def sozlukten(cls, d: dict | None) -> "Secenek":
        d = d or {}
        ad = {f.name: f for f in fields(cls)}
        s = cls()
        for k, v in d.items():
            if k in ad:
                try:
                    setattr(s, k, type(getattr(s, k))(v))
                except (TypeError, ValueError):
                    pass
        if s.kalite not in KALITELER:
            s.kalite = "dengeli"
        return s

    def sozluk(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


JPG_KALITE = {"yuksek": 95, "dengeli": 85, "kucuk": 68}
WEBP_KALITE = {"yuksek": 92, "dengeli": 82, "kucuk": 65}
AVIF_KALITE = {"yuksek": 80, "dengeli": 62, "kucuk": 45}
CRF264 = {"yuksek": 18, "dengeli": 23, "kucuk": 28}
CRFVP9 = {"yuksek": 27, "dengeli": 33, "kucuk": 40}
MP3_Q = {"yuksek": "0", "dengeli": "2", "kucuk": "5"}
AAC_B = {"yuksek": "256k", "dengeli": "192k", "kucuk": "128k"}
OPUS_B = {"yuksek": "192k", "dengeli": "128k", "kucuk": "64k"}
VORBIS_Q = {"yuksek": "7", "dengeli": "5", "kucuk": "3"}


# ---------------------------------------------------------------------------
# Araç / modül durumu
# ---------------------------------------------------------------------------
def _modul_var(ad: str) -> bool:
    try:
        __import__(ad)
        return True
    except Exception:
        return False


def _soffice_bul() -> Optional[str]:
    yol = S.arac_yolu("soffice")
    if yol:
        return yol
    for yol in S.libreoffice_adaylari():
        if os.access(yol, os.X_OK):
            return yol
    return None


@functools.lru_cache(maxsize=1)
def araclar_durumu() -> dict:
    """Her bağımlılığın var/yok durumu. anahtarlar: dil.ARAC_IPUCU ile aynı."""
    d = {
        "ffmpeg": bool(S.arac_yolu("ffmpeg")),
        "ffprobe": bool(S.arac_yolu("ffprobe")),
        "libreoffice": _soffice_bul() is not None,
        "pdftoppm": bool(S.arac_yolu("pdftoppm")),
        "pdftotext": bool(S.arac_yolu("pdftotext")),
        "pdfinfo": bool(S.arac_yolu("pdfinfo")),
        "qpdf": bool(S.arac_yolu("qpdf")),
        "tesseract": bool(S.arac_yolu("tesseract")),
        "gs": bool(S.arac_yolu("gs")),
        "pillow": _modul_var("PIL"),
        "reportlab": _modul_var("reportlab"),
        "fonttools": _modul_var("fontTools"),
        "brotli": _modul_var("brotli"),
        "svg": _modul_var("cairosvg"),
        "rawpy": _modul_var("rawpy"),
        "heif": _modul_var("pillow_heif"),
        "pypdf": _modul_var("pypdf"),
        "avif": False,
        "webp": False,
    }
    if d["pillow"]:
        try:
            from PIL import features
            d["avif"] = bool(features.check("avif"))
            d["webp"] = bool(features.check("webp"))
        except Exception:
            pass
    return d


def araclari_yenile() -> None:
    S.ortam_hazirla()
    araclar_durumu.cache_clear()
    _ffmpeg_kodlayicilar.cache_clear()


@functools.lru_cache(maxsize=1)
def _ffmpeg_kodlayicilar() -> frozenset:
    if not S.arac_yolu("ffmpeg"):
        return frozenset()
    try:
        p = subprocess.run([S.coz("ffmpeg"), "-hide_banner", "-encoders"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30, **S.popen_ayarlari())
        return frozenset(m.group(1) for m in re.finditer(r"^\s*[VAS][\w.]{5}\s+(\S+)", p.stdout, re.M))
    except Exception:
        return frozenset()


def _kodlayici(ad: str) -> bool:
    return ad in _ffmpeg_kodlayicilar()


def gerekli(ext: str, hedef: str) -> list[str]:
    """Bir dönüşümün ihtiyaç duyduğu araçlar. 'a|b' = ikisinden biri yeter."""
    ext, hedef = norm(ext), norm(hedef)
    t = tur(ext)
    r: list[str] = []
    if t in ("gorsel", "ham", "svg"):
        r.append("pillow")
        if t == "ham":
            r.append("rawpy")
        if t == "svg":
            r.append("svg")
        if ext in ("heic", "heif"):
            r.append("heif")
        if hedef == "avif":
            r.append("avif")
        if hedef == "webp":
            r.append("webp")
        if hedef in ("mp4", "webm"):
            r += ["ffmpeg"]
    elif t in ("video", "ses"):
        r += ["ffmpeg", "ffprobe"]
    elif t == "pdf":
        if hedef in ("png", "jpg", "webp"):
            r += ["pdftoppm", "pdfinfo|qpdf"]
            if hedef == "webp":
                r += ["pillow", "webp"]
        elif hedef == "txt":
            r += ["pdftotext", "pdfinfo|qpdf"]
        else:
            r += ["libreoffice", "pdfinfo|qpdf"]
    elif t == "txt":
        r.append("reportlab|libreoffice" if hedef == "pdf" else "libreoffice")
    elif t in ("yazidoc", "html", "tablo", "sunum"):
        r.append("libreoffice")
        if t == "sunum" and hedef in ("png", "jpg"):
            r += ["pdftoppm"]
    elif t == "yazitipi":
        r.append("fonttools")
        if "woff2" in (ext, hedef):
            r.append("brotli")
    return r


def eksikler(ext: str, hedef: str) -> list[str]:
    d = araclar_durumu()
    eksik = []
    for g in gerekli(ext, hedef):
        secenekler = g.split("|")
        if not any(d.get(x, False) for x in secenekler):
            eksik.append(secenekler[-1])
    return eksik


def kontrol(ext: str, hedef: str) -> Optional[FilenorHata]:
    """Dönüşüm yapılabilir mi? Yapılabilirse None; değilse nedenini veren hata."""
    ext, hedef = norm(ext), norm(hedef)
    if not tur(ext) or hedef not in hedefler(ext):
        if ext == hedef and ext:
            return FilenorHata("ayni_bicim")
        if tur(ext) == "ses" and hedef in VIDEO_YAZ + ["gif"]:
            return FilenorHata("ses_video_degil")
        return FilenorHata("desteklenmiyor", kaynak=ext or "?", hedef=hedef)
    ek = eksikler(ext, hedef)
    if ek:
        return FilenorHata("arac_eksik", arac=ek[0])
    return None


# ---------------------------------------------------------------------------
# Oturum: iptal, ilerleme, zaman aşımı, geçici alan
# ---------------------------------------------------------------------------
class Oturum:
    """Bir dönüşüm grubunun ortak durumu. `with Oturum() as o:` olarak kullanın."""

    def __init__(self, ilerleme: Optional[Callable[[Optional[float], str], None]] = None,
                 iptal: Optional[threading.Event] = None, zaman_asimi: float = 1800.0):
        self.ilerleme_cb = ilerleme
        self.iptal = iptal or threading.Event()
        self.zaman_asimi = zaman_asimi
        self._taban: Optional[str] = None
        self._lo_sayac = 0
        self._lo_profil: Optional[str] = None

    @property
    def taban(self) -> str:
        if not self._taban:
            self._taban = tempfile.mkdtemp(prefix="filenor-")
        return self._taban

    def lo_profil(self, yeni: bool = False) -> str:
        if yeni or not self._lo_profil:
            self._lo_sayac += 1
            self._lo_profil = os.path.join(self.taban, f"lo{self._lo_sayac}")
        return self._lo_profil

    def ilerle(self, yuzde: Optional[float], metin: str = "") -> None:
        if self.ilerleme_cb:
            try:
                self.ilerleme_cb(None if yuzde is None else max(0.0, min(100.0, yuzde)), metin)
            except Exception:
                pass

    def kontrol_iptal(self) -> None:
        if self.iptal.is_set():
            raise Iptal()

    def kapat(self) -> None:
        if self._taban:
            shutil.rmtree(self._taban, ignore_errors=True)
            self._taban = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.kapat()


def _oldur(proc: subprocess.Popen) -> None:
    S.oldur(proc)


def calistir(o: Oturum, komut: list[str], arac: str, *, satir_cb: Optional[Callable[[str], None]] = None,
             cwd: Optional[str] = None, env: Optional[dict] = None, zaman: Optional[float] = None,
             kabul: Iterable[int] = (0,)) -> tuple[int, str, str]:
    """Harici aracı çalıştırır. İptal/zaman aşımında süreç grubunu öldürür."""
    o.kontrol_iptal()
    e = dict(os.environ)
    e.setdefault("LC_ALL", "C.UTF-8")
    if env:
        e.update(env)
    try:
        komut = [S.coz(komut[0])] + list(komut[1:])        # Windows: tam yol; 'gs' -> gswin64c
        proc = subprocess.Popen(komut, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace", cwd=cwd, env=e,
                                stdin=subprocess.DEVNULL, **S.popen_ayarlari())
    except FileNotFoundError:
        raise FilenorHata("arac_eksik", arac=arac)
    neden = {"v": None}
    bitti = threading.Event()
    sinir = zaman if zaman is not None else o.zaman_asimi

    def bekci():
        bas = time.monotonic()
        while not bitti.is_set():
            if o.iptal.is_set():
                neden["v"] = "iptal"
                _oldur(proc)
                return
            if sinir and time.monotonic() - bas > sinir:
                neden["v"] = "zaman"
                _oldur(proc)
                return
            bitti.wait(0.2)

    hata_parcalari: list[str] = []

    def hata_oku():
        for s in proc.stderr:
            hata_parcalari.append(s)
            if len(hata_parcalari) > 400:
                del hata_parcalari[:200]

    th_b = threading.Thread(target=bekci, daemon=True)
    th_e = threading.Thread(target=hata_oku, daemon=True)
    th_b.start()
    th_e.start()
    cikti: list[str] = []
    try:
        for s in proc.stdout:
            if satir_cb:
                satir_cb(s)
            else:
                cikti.append(s)
                if len(cikti) > 2000:
                    del cikti[:1000]
        proc.wait()
    finally:
        bitti.set()
        th_e.join(timeout=2)
        if proc.poll() is None:
            _oldur(proc)
        for akis in (proc.stdout, proc.stderr):
            try:
                akis.close()
            except Exception:
                pass
    out, err = "".join(cikti), "".join(hata_parcalari)
    if neden["v"] == "iptal":
        raise Iptal()
    if neden["v"] == "zaman":
        raise FilenorHata("zaman_asimi", arac=arac)
    if proc.returncode not in set(kabul):
        raise FilenorHata("arac_hata", arac=arac, ayrinti=_son_satirlar(err or out))
    return proc.returncode, out, err


def _son_satirlar(metin: str, n: int = 3) -> str:
    sat = [s.strip() for s in metin.strip().splitlines() if s.strip()]
    return " | ".join(sat[-n:])[:400] or "?"


# ---------------------------------------------------------------------------
# Dosya güvenliği ve adlandırma
# ---------------------------------------------------------------------------
def _dosya_adi_temizle(ad: str) -> str:
    """Yol ayiracini ve (Windows'ta) gecersiz karakterleri '_' yapar; sondaki nokta/bosluk atilir."""
    ad = ad.strip().replace("/", "_").replace("\x00", "")
    if S.WINDOWS:
        for c in '\\:*?"<>|':
            ad = ad.replace(c, "_")
        ad = ad.rstrip(". ")
    return ad


def benzersiz_yol(dizin: str, ad: str, ext: str) -> str:
    """dizin içinde ad.ext boşsa onu, doluysa 'ad (1).ext' ... yer ayırarak döndürür."""
    ext = ext.lstrip(".")
    ad = _dosya_adi_temizle(ad) or "dosya"
    ad = ad[:180]
    n = 0
    while True:
        son = f"{ad}.{ext}" if n == 0 else f"{ad} ({n}).{ext}"
        yol = os.path.join(dizin, son)
        try:
            fd = os.open(yol, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.close(fd)
            return yol
        except FileExistsError:
            n += 1
            if n > 9999:
                raise FilenorHata("bilinmeyen", ayrinti="adlandırma")


def benzersiz_klasor(dizin: str, ad: str) -> str:
    ad = _dosya_adi_temizle(ad) or "cikti"
    n = 0
    while True:
        yol = os.path.join(dizin, ad if n == 0 else f"{ad} ({n})")
        try:
            os.mkdir(yol)
            return yol
        except FileExistsError:
            n += 1
            if n > 9999:
                raise FilenorHata("bilinmeyen", ayrinti="adlandırma")


def girdi_denetle(yol: str) -> str:
    yol = os.path.abspath(os.path.expanduser(yol))
    if not os.path.isfile(yol):
        raise FilenorHata("dosya_yok", yol=yol)
    if os.path.getsize(yol) == 0:
        raise FilenorHata("dosya_bos", yol=yol)
    if not os.access(yol, os.R_OK):
        raise FilenorHata("okunamadi", ayrinti="izin yok")
    return yol


def cikti_dizini_hazirla(dizin: str) -> str:
    dizin = os.path.abspath(os.path.expanduser(dizin))
    try:
        os.makedirs(dizin, exist_ok=True)
    except OSError as e:
        raise FilenorHata("cikti_yazilamaz", yol=dizin, ayrinti=str(e))
    if not os.access(dizin, os.W_OK | os.X_OK):
        raise FilenorHata("cikti_yazilamaz", yol=dizin, ayrinti="izin yok")
    return dizin


def metin_oku(yol: str) -> str:
    """Düz metni kodlamayı tahmin ederek okur (UTF-8 -> CP1254 -> Latin-1)."""
    with open(yol, "rb") as f:
        ham = f.read()
    for kod in ("utf-8-sig", "utf-16") if ham[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig",):
        try:
            return ham.decode(kod)
        except UnicodeDecodeError:
            pass
    for kod in ("cp1254", "latin-1"):
        try:
            return ham.decode(kod)
        except UnicodeDecodeError:
            pass
    return ham.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Sayfa aralığı
# ---------------------------------------------------------------------------
def sayfa_listesi(aralik: str, toplam: int) -> list[int]:
    """'1-3,5,8-' -> [1,2,3,5,8,...,toplam]. Boş aralık = tüm sayfalar."""
    aralik = (aralik or "").strip()
    if not aralik:
        return list(range(1, toplam + 1))
    sonuc: list[int] = []
    for parca in aralik.replace(" ", "").split(","):
        m = re.fullmatch(r"(\d*)(?:(-)(\d*))?", parca)
        if not parca or not m or (not m.group(1) and not m.group(3)):
            raise FilenorHata("sayfa_araligi", aralik=aralik)
        a = int(m.group(1)) if m.group(1) else 1
        if m.group(2):
            b = int(m.group(3)) if m.group(3) else toplam
        else:
            b = a
        if a < 1 or b < a or a > toplam:
            raise FilenorHata("sayfa_araligi", aralik=aralik)
        sonuc += list(range(a, min(b, toplam) + 1))
    gor, tek = set(), []
    for s in sonuc:
        if s not in gor:
            gor.add(s)
            tek.append(s)
    return tek


def _qpdf_aralik(sayfalar: list[int]) -> str:
    return ",".join(str(s) for s in sayfalar)


# ---------------------------------------------------------------------------
# PDF yardımcıları
# ---------------------------------------------------------------------------
def pdf_bilgi(o: Oturum, yol: str, parola: str = "") -> dict:
    """{'sayfa': n, 'sifreli': bool}. Parola gerekiyorsa FilenorHata('sifreli_pdf')."""
    d = araclar_durumu()
    if d["qpdf"]:
        kom = ["qpdf", "--show-npages"]
        if parola:
            kom.append(f"--password={parola}")
        kom.append(yol)
        rc, out, err = calistir(o, kom, "qpdf", kabul=(0, 2, 3))
        if rc == 0:
            try:
                return {"sayfa": int(out.strip().splitlines()[-1]), "sifreli": bool(parola)}
            except (ValueError, IndexError):
                pass
        metin = (out + err).lower()
        if "password" in metin:
            raise FilenorHata("sifreli_pdf")
        raise FilenorHata("okunamadi", ayrinti=_son_satirlar(err or out))
    if d["pdfinfo"]:
        kom = ["pdfinfo"] + (["-upw", parola] if parola else []) + [yol]
        rc, out, err = calistir(o, kom, "pdfinfo", kabul=(0, 1))
        if rc != 0:
            if "password" in err.lower():
                raise FilenorHata("sifreli_pdf")
            raise FilenorHata("okunamadi", ayrinti=_son_satirlar(err))
        m = re.search(r"^Pages:\s+(\d+)", out, re.M)
        if m:
            return {"sayfa": int(m.group(1)), "sifreli": "yes" in (re.search(r"^Encrypted:\s+(\w+)", out, re.M) or [None, ""])[1]}
    raise FilenorHata("arac_eksik", arac="qpdf")


def pdf_hazirla(o: Oturum, kaynak: str, isd: str, parola: str = "") -> str:
    """Parola gerekirse çözülmüş bir kopya üretir; yoksa kaynağı döndürür."""
    try:
        pdf_bilgi(o, kaynak, "")
        return kaynak
    except FilenorHata as h:
        if h.kod != "sifreli_pdf":
            raise
    if not parola:
        raise FilenorHata("sifreli_pdf")
    pdf_bilgi(o, kaynak, parola)  # yanlış parola -> sifreli_pdf
    hedef = os.path.join(isd, "cozulmus.pdf")
    calistir(o, ["qpdf", f"--password={parola}", "--decrypt", kaynak, hedef], "qpdf", kabul=(0, 3))
    return hedef


# ---------------------------------------------------------------------------
# Dönüşüm motoru
# ---------------------------------------------------------------------------
Sonuc = tuple  # (dosyalar: list[str], klasor_eki: str)


def donustur(kaynak: str, hedef: str, cikti_dizin: str, secenek: Optional[Secenek] = None,
             oturum: Optional[Oturum] = None) -> list[str]:
    """Tek dosyayı dönüştürür; üretilen dosyaların son yollarını döndürür.

    Çok dosyalı sonuçlar (PDF sayfaları gibi) cikti_dizin içinde yeni klasöre yazılır.
    Hata: FilenorHata. İptal: Iptal.
    """
    sec = secenek or Secenek()
    kaynak = girdi_denetle(kaynak)
    ext, hedef = uzanti(kaynak), norm(hedef)
    h = kontrol(ext, hedef)
    if h:
        raise h
    cikti_dizin = cikti_dizini_hazirla(cikti_dizin)
    kendi = oturum is None
    o = oturum or Oturum()
    try:
        return _is_calistir(o, kaynak, ext, hedef, cikti_dizin, sec, _motor_sec(ext, hedef))
    finally:
        if kendi:
            o.kapat()


def _motor_sec(ext: str, hedef: str) -> Callable:
    t = tur(ext)
    if t in ("gorsel", "ham", "svg"):
        if hedef in ("mp4", "webm"):
            return _e_gif_video
        return _e_gorsel
    if t in ("video", "ses"):
        return _e_medya
    if t == "pdf":
        if hedef in ("png", "jpg", "webp"):
            return _e_pdf_gorsel
        if hedef == "txt":
            return _e_pdf_metin
        return _e_lo
    if t == "txt" and hedef == "pdf" and araclar_durumu()["reportlab"]:
        return _e_txt_pdf
    if t in ("txt", "yazidoc", "html", "tablo", "sunum"):
        if t == "sunum" and hedef in ("png", "jpg"):
            return _e_sunum_gorsel
        return _e_lo
    if t == "yazitipi":
        return _e_yazi
    raise FilenorHata("desteklenmiyor", kaynak=ext, hedef=hedef)


def _is_calistir(o: Oturum, kaynak: str, ext: str, hedef: str, cikti_dizin: str, sec: Secenek,
                 motor: Callable, stem: Optional[str] = None) -> list[str]:
    isd = tempfile.mkdtemp(prefix=".filenor-", dir=cikti_dizin)
    try:
        o.ilerle(0, os.path.basename(kaynak))
        dosyalar, ek = motor(o, kaynak, ext, hedef, isd, sec)
        o.kontrol_iptal()
        dosyalar = [d for d in dosyalar if os.path.isfile(d) and os.path.getsize(d) > 0]
        if not dosyalar:
            raise FilenorHata("cikti_yok")
        stem = stem or os.path.splitext(os.path.basename(kaynak))[0]
        sonuc: list[str] = []
        if len(dosyalar) == 1:
            son = benzersiz_yol(cikti_dizin, stem, hedef)
            os.replace(dosyalar[0], son)
            sonuc.append(son)
        else:
            kl = benzersiz_klasor(cikti_dizin, stem + (ek or "_sayfalar"))
            for d in dosyalar:
                son = os.path.join(kl, os.path.basename(d))
                os.replace(d, son)
                sonuc.append(son)
        o.ilerle(100, os.path.basename(kaynak))
        return sonuc
    finally:
        shutil.rmtree(isd, ignore_errors=True)


# --------------------------- görsel -----------------------------------------
def _gorsel_ac(o: Oturum, yol: str, ext: str):
    from PIL import Image, UnidentifiedImageError
    try:
        if ext in HAM:
            import rawpy  # type: ignore
            with rawpy.imread(yol) as r:
                rgb = r.postprocess(use_camera_wb=True)
            return Image.fromarray(rgb)
        if ext == "svg":
            import cairosvg  # type: ignore
            png = cairosvg.svg2png(url=yol, output_width=2048)
            im = Image.open(io.BytesIO(png))
            im.load()
            return im
        if ext in ("heic", "heif"):
            import pillow_heif  # type: ignore
            pillow_heif.register_heif_opener()
        im = Image.open(yol)
        im.load() if getattr(im, "n_frames", 1) <= 1 else im.seek(0)
        return im
    except FilenorHata:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError) as e:
        raise FilenorHata("okunamadi", ayrinti=str(e)[:200])
    except ImportError:
        raise FilenorHata("arac_eksik", arac={"svg": "svg", "heic": "heif", "heif": "heif"}.get(ext, "rawpy"))


def _duz_rgb(img):
    from PIL import Image
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        zemin = Image.new("RGB", rgba.size, (255, 255, 255))
        zemin.paste(rgba, mask=rgba.split()[3])
        return zemin
    if img.mode in ("I;16", "I;16L", "I;16B", "I"):
        img = img.point(lambda v: v / 256).convert("L") if img.mode.startswith("I;16") else img.convert("L")
    return img.convert("RGB")


def gorsel_isle(img, hedef: str, cikti: str, sec: Secenek, *, hepsi: bool = False, korunacak_exif=None,
                icc=None) -> None:
    """Pillow görüntüsünü hedef biçimde yazar (yeniden boyutlandırma dahil)."""
    from PIL import Image, ImageSequence
    kalite = sec.kalite
    cerceveler = None
    sureler = None
    if hepsi and getattr(img, "n_frames", 1) > 1 and hedef in ("gif", "webp"):
        cerceveler, sureler = [], []
        for fr in ImageSequence.Iterator(img):
            cerceveler.append(fr.copy())
            sureler.append(fr.info.get("duration", 80))
    if sec.max_kenar and sec.max_kenar > 0:
        def kucult(im):
            im = im.copy()
            im.thumbnail((sec.max_kenar, sec.max_kenar), Image.LANCZOS)
            return im
        if cerceveler:
            cerceveler = [kucult(c) for c in cerceveler]
        else:
            img = kucult(img)
    exif_b = None if sec.meta_temizle else korunacak_exif
    icc_b = None if sec.meta_temizle else icc

    def tek(im):
        if hedef in ("jpg", "bmp"):
            im = _duz_rgb(im)
        elif hedef == "ico":
            im = im.convert("RGBA")
        elif hedef == "avif":
            im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P", "PA") else im.convert("RGB")
        elif hedef == "tiff":
            if im.mode in ("P", "PA", "I;16", "I"):
                im = im.convert("RGBA" if "transparency" in im.info else "RGB")
        elif hedef in ("png", "webp"):
            if im.mode in ("P", "PA"):
                im = im.convert("RGBA")
            elif im.mode in ("CMYK", "I;16", "I", "F"):
                im = _duz_rgb(im)
        return im

    kw: dict = {}
    if hedef == "jpg":
        kw = dict(quality=JPG_KALITE[kalite], optimize=True, progressive=kalite != "yuksek")
        if kalite == "yuksek":
            kw["subsampling"] = 0
    elif hedef == "png":
        kw = dict(optimize=True, compress_level=9 if kalite == "kucuk" else 6)
    elif hedef == "webp":
        kw = dict(quality=WEBP_KALITE[kalite], method=4 if kalite != "yuksek" else 6)
        if kalite == "yuksek" and cerceveler is None:
            kw["lossless"] = False
    elif hedef == "avif":
        kw = dict(quality=AVIF_KALITE[kalite], speed=8)
    elif hedef == "tiff":
        kw = dict(compression="tiff_adobe_deflate")
    elif hedef == "bmp":
        kw = {}
    if exif_b and hedef in ("jpg", "webp", "png", "tiff", "avif"):
        kw["exif"] = exif_b
    if icc_b and hedef in ("jpg", "webp", "png", "tiff", "avif"):
        kw["icc_profile"] = icc_b

    if hedef == "ico":
        im = tek(img)
        kare = max(im.size)
        tuval = Image.new("RGBA", (kare, kare), (0, 0, 0, 0))
        tuval.paste(im, ((kare - im.width) // 2, (kare - im.height) // 2))
        if kare > 256:
            tuval = tuval.resize((256, 256), Image.LANCZOS)
        yan = tuval.width
        boy = [(s_, s_) for s_ in (16, 32, 48, 64, 128, 256) if s_ <= yan] or [(yan, yan)]
        tuval.save(cikti, format="ICO", sizes=boy)
        return
    if cerceveler:
        kareler = [tek(c) for c in cerceveler]
        if hedef == "gif":
            kareler = [k.convert("P", palette=Image.ADAPTIVE) if k.mode != "P" else k for k in kareler]
        kareler[0].save(cikti, save_all=True, append_images=kareler[1:], duration=sureler, loop=0,
                        **({"quality": kw["quality"]} if hedef == "webp" else {}))
        return
    biçim = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP", "gif": "GIF", "bmp": "BMP",
             "tiff": "TIFF", "avif": "AVIF", "pdf": "PDF"}[hedef]
    im = tek(img)
    if hedef == "gif" and im.mode not in ("P", "L"):
        im = im.convert("P", palette=Image.ADAPTIVE)
    im.save(cikti, format=biçim, **kw)


def _e_gorsel(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    orijinal = _gorsel_ac(o, kaynak, ext)
    try:
        return _e_gorsel_ic(o, orijinal, hedef, isd, sec)
    finally:
        try:
            orijinal.close()
        except Exception:
            pass


def _e_gorsel_ic(o: Oturum, img, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    from PIL import ImageOps
    exif = None
    icc = None
    try:
        ex = img.getexif()
        icc = img.info.get("icc_profile")
        # Yönlendirmeyi gerçek piksellere uygula (özgün sürümde döndürülmüş çıkıyordu)
        if ex.get(0x0112, 1) not in (None, 1) and getattr(img, "n_frames", 1) <= 1:
            img = ImageOps.exif_transpose(img)
            ex = img.getexif()
        if len(ex):
            exif = ex.tobytes()
        if img.mode == "CMYK":
            icc = None
    except Exception:
        pass
    o.ilerle(30, "")
    cikti = os.path.join(isd, "cikti." + ("tiff" if hedef == "tiff" else hedef))
    try:
        if hedef == "pdf":
            im = _duz_rgb(img)
            if sec.max_kenar > 0:
                from PIL import Image
                im.thumbnail((sec.max_kenar, sec.max_kenar), Image.LANCZOS)
            dpi = 150.0
            im.save(cikti, "PDF", resolution=dpi)
        else:
            gorsel_isle(img, hedef, cikti, sec, hepsi=True, korunacak_exif=exif, icc=icc)
    except FilenorHata:
        raise
    except (OSError, ValueError, KeyError) as e:
        raise FilenorHata("arac_hata", arac="Pillow", ayrinti=str(e)[:200])
    return [cikti], ""


def _e_gif_video(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    cikti = os.path.join(isd, "cikti." + hedef)
    kaynak = guvenli_girdi(isd, kaynak, ext)
    # tek kareli GIF/PNG/JPG de olsa çalışsın: çift boyutlu yap
    vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    if sec.max_kenar > 0:
        vf = f"scale=-2:'min({int(sec.max_kenar)},ih)',scale=trunc(iw/2)*2:trunc(ih/2)*2"
    kom = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", kaynak, "-an", "-vf", vf]
    if hedef == "mp4":
        kom += ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF264[sec.kalite]),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    else:
        kom += ["-c:v", "libvpx-vp9", "-crf", str(CRFVP9[sec.kalite]), "-b:v", "0", "-row-mt", "1",
                "-deadline", "good", "-cpu-used", "5", "-pix_fmt", "yuv420p"]
    kom.append(cikti)
    calistir(o, kom, "ffmpeg")
    return [cikti], ""


def guvenli_girdi(isd: str, kaynak: str, ext: str) -> str:
    """Kullanici dosya adini arac komut satirina vermeyiz: '%', ':' gibi karakterler ffmpeg'de
    ozel anlam tasir. Is klasorune sade adli bir baglanti (olmazsa kopya) koyar."""
    hedef = os.path.join(isd, "girdi." + (ext or "bin"))
    try:
        os.symlink(kaynak, hedef)
    except OSError:
        shutil.copyfile(kaynak, hedef)
    return hedef


# --------------------------- ses / video ------------------------------------
def medya_bilgi(o: Oturum, yol: str) -> dict:
    _, out, _ = calistir(o, ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", yol],
                         "ffprobe", zaman=60)
    try:
        j = json.loads(out)
    except ValueError:
        raise FilenorHata("okunamadi", ayrinti="ffprobe")
    akis = j.get("streams", [])
    v = [s for s in akis if s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic", 0) == 0]
    a = [s for s in akis if s.get("codec_type") == "audio"]
    try:
        sure = float(j.get("format", {}).get("duration") or 0)
    except ValueError:
        sure = 0.0
    return {"sure": sure, "video": bool(v), "ses": bool(a),
            "genislik": int(v[0].get("width", 0)) if v else 0, "yukseklik": int(v[0].get("height", 0)) if v else 0}


def _e_medya(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    kaynak = guvenli_girdi(isd, kaynak, ext)
    bilgi = medya_bilgi(o, kaynak)
    if not bilgi["video"] and not bilgi["ses"]:
        raise FilenorHata("okunamadi", ayrinti="ses/görüntü akışı yok")
    cikti = os.path.join(isd, "cikti." + hedef)
    ses_hedef = hedef in SES_YAZ
    kom = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-v", "error", "-progress", "pipe:1", "-nostats"]
    if sec.baslangic > 0:
        kom += ["-ss", f"{sec.baslangic:.3f}"]
    kom += ["-i", kaynak]
    if sec.bitis > 0 and sec.bitis > sec.baslangic:
        kom += ["-t", f"{sec.bitis - max(sec.baslangic, 0):.3f}"]
    meta = ["-map_metadata", "-1"] if sec.meta_temizle else ["-map_metadata", "0"]
    sure = bilgi["sure"]
    if sec.bitis > 0:
        sure = min(sure, sec.bitis) - max(sec.baslangic, 0)
    elif sec.baslangic > 0:
        sure -= sec.baslangic

    if ses_hedef:
        if not bilgi["ses"]:
            raise FilenorHata("okunamadi", ayrinti="ses akışı yok")
        kom += ["-vn", "-map", "0:a:0"] + meta
        k = sec.kalite
        if hedef == "mp3":
            kom += ["-c:a", "libmp3lame", "-q:a", MP3_Q[k]]
        elif hedef == "m4a":
            kom += ["-c:a", "aac", "-b:a", AAC_B[k], "-movflags", "+faststart"]
        elif hedef == "aac":
            kom += ["-c:a", "aac", "-b:a", AAC_B[k], "-f", "adts"]
        elif hedef == "opus":
            kom += ["-c:a", "libopus", "-b:a", OPUS_B[k]]
        elif hedef == "ogg":
            kom += (["-c:a", "libvorbis", "-q:a", VORBIS_Q[k]] if _kodlayici("libvorbis")
                    else ["-c:a", "libopus", "-b:a", OPUS_B[k]])
        elif hedef == "flac":
            kom += ["-c:a", "flac", "-compression_level", "8"]
        elif hedef == "wav":
            kom += ["-c:a", "pcm_s16le"]
    elif hedef == "gif":
        if not bilgi["video"]:
            raise FilenorHata("okunamadi", ayrinti="görüntü akışı yok")
        fps = max(1, min(30, sec.gif_fps))
        gen = max(32, min(1920, sec.gif_genislik))
        vf = (f"fps={fps},scale='min({gen},iw)':-2:flags=lanczos,split[a][b];"
              f"[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5")
        kom += ["-an", "-vf", vf, "-loop", "0"]
    else:  # video
        if not bilgi["video"]:
            raise FilenorHata("okunamadi", ayrinti="görüntü akışı yok")
        vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        if sec.max_kenar > 0:
            vf = f"scale=-2:'min({int(sec.max_kenar)},ih)',scale=trunc(iw/2)*2:trunc(ih/2)*2"
        kom += ["-map", "0:v:0", "-map", "0:a:0?"] + meta + ["-vf", vf]
        k = sec.kalite
        if hedef == "webm":
            kom += ["-c:v", "libvpx-vp9", "-crf", str(CRFVP9[k]), "-b:v", "0", "-row-mt", "1",
                    "-deadline", "good", "-cpu-used", "5", "-c:a", "libopus", "-b:a", OPUS_B["dengeli"]]
        else:
            kom += ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF264[k]), "-pix_fmt", "yuv420p"]
            if hedef == "avi":
                kom += ["-c:a", "libmp3lame", "-q:a", "3"] if _kodlayici("libmp3lame") else ["-c:a", "ac3"]
            else:
                kom += ["-c:a", "aac", "-b:a", "160k"]
            if hedef in ("mp4", "mov"):
                kom += ["-movflags", "+faststart"]
    kom.append(cikti)

    son = {"p": 0.0}

    def satir(s: str):
        s = s.strip()
        if s.startswith("out_time_us=") or s.startswith("out_time_ms="):
            try:
                us = int(s.split("=", 1)[1])
            except ValueError:
                return
            if sure > 0 and us >= 0:
                p = min(99.0, us / 1_000_000.0 / sure * 100.0)
                if p - son["p"] >= 0.5:
                    son["p"] = p
                    o.ilerle(p, "")
    calistir(o, kom, "ffmpeg", satir_cb=satir)
    return [cikti], ""


# --------------------------- PDF -> ... -------------------------------------
def _e_pdf_gorsel(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    return _pdf_sayfalari_gorsele(o, kaynak, hedef, isd, sec)


def _pdf_sayfalari_gorsele(o: Oturum, pdf: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    pdf = pdf_hazirla(o, pdf, isd, sec.parola)
    n = pdf_bilgi(o, pdf)["sayfa"]
    sayfalar = sayfa_listesi(sec.sayfa_araligi, n)
    dpi = max(36, min(600, int(sec.dpi)))
    # Bitişik değilse önce istenen sayfaları ayır
    bitisik = sayfalar == list(range(sayfalar[0], sayfalar[-1] + 1))
    islenecek = pdf
    if not bitisik:
        islenecek = os.path.join(isd, "secili.pdf")
        calistir(o, ["qpdf", pdf, "--pages", ".", _qpdf_aralik(sayfalar), "--", islenecek], "qpdf", kabul=(0, 3))
        f, l = 1, len(sayfalar)
    else:
        f, l = sayfalar[0], sayfalar[-1]
    bicim = "-jpeg" if hedef == "jpg" else "-png"
    onek = os.path.join(isd, "p")
    kom = ["pdftoppm", "-r", str(dpi), bicim, "-f", str(f), "-l", str(l)]
    if hedef == "jpg":
        kom += ["-jpegopt", f"quality={JPG_KALITE[sec.kalite]}"]
    kom += [islenecek, onek]
    calistir(o, kom, "pdftoppm", zaman=max(300.0, 5.0 * len(sayfalar)))
    ham = sorted(glob.glob(onek + "-*"), key=lambda s: int(re.search(r"-(\d+)\.\w+$", s).group(1)))
    if not ham:
        raise FilenorHata("cikti_yok")
    hane = max(3, len(str(sayfalar[-1])))
    cikti: list[str] = []
    for i, ph in enumerate(ham):
        o.kontrol_iptal()
        no = sayfalar[i] if i < len(sayfalar) else i + 1
        ad = os.path.join(isd, f"sayfa_{no:0{hane}d}.{hedef}")
        if hedef == "webp":
            from PIL import Image
            with Image.open(ph) as im:
                im.save(ad, "WEBP", quality=WEBP_KALITE[sec.kalite])
            os.remove(ph)
        else:
            os.replace(ph, ad)
        if sec.max_kenar > 0 and hedef != "webp":
            from PIL import Image
            with Image.open(ad) as im:
                im.load()
                im.thumbnail((sec.max_kenar, sec.max_kenar), Image.LANCZOS)
                im.save(ad)
        cikti.append(ad)
        o.ilerle(10 + 85.0 * (i + 1) / len(ham), "")
    return cikti, "_sayfalar"


def _e_pdf_metin(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    pdf = pdf_hazirla(o, kaynak, isd, sec.parola)
    n = pdf_bilgi(o, pdf)["sayfa"]
    sayfalar = sayfa_listesi(sec.sayfa_araligi, n)
    cikti = os.path.join(isd, "cikti.txt")
    kom = ["pdftotext", "-layout", "-enc", "UTF-8"]
    if sayfalar == list(range(sayfalar[0], sayfalar[-1] + 1)):
        kom += ["-f", str(sayfalar[0]), "-l", str(sayfalar[-1])]
    kom += [pdf, cikti]
    calistir(o, kom, "pdftotext")
    with open(cikti, "r", encoding="utf-8", errors="replace") as f:
        icerik = f.read()
    if not icerik.replace("\f", "").strip():
        raise FilenorHata("metin_yok")
    return [cikti], ""


# --------------------------- düz metin -> PDF --------------------------------
def _yazi_dosyasi(adaylar: list[str]) -> Optional[str]:
    for a in adaylar:
        if os.path.isfile(a):
            return a
    try:
        p = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Sans Mono"], capture_output=True, text=True, timeout=10)
        if p.returncode == 0 and os.path.isfile(p.stdout.strip()) and p.stdout.strip().lower().endswith(".ttf"):
            return p.stdout.strip()
    except Exception:
        pass
    return None


def _e_txt_pdf(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    metin = metin_oku(kaynak).replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    yazi = _yazi_dosyasi(S.sabit_genislikli_yazi_tipleri())
    ad = "Courier"
    if yazi:
        try:
            pdfmetrics.registerFont(TTFont("FilenorMono", yazi))
            ad = "FilenorMono"
        except Exception:
            ad = "Courier"
    boy = 10.0
    kenar = 56.0
    genislik, yukseklik = A4
    satir_h = boy * 1.4
    cikti = os.path.join(isd, "cikti.pdf")
    c = canvas.Canvas(cikti, pagesize=A4)
    c.setTitle(os.path.splitext(os.path.basename(kaynak))[0])
    c.setFont(ad, boy)
    y = yukseklik - kenar
    for ham in metin.split("\n"):
        o.kontrol_iptal()
        parcalar = simpleSplit(ham, ad, boy, genislik - 2 * kenar) or [""]
        for p in parcalar:
            if y < kenar:
                c.showPage()
                c.setFont(ad, boy)
                y = yukseklik - kenar
            if ad == "Courier":
                p = p.encode("latin-1", "replace").decode("latin-1")
            c.drawString(kenar, y, p)
            y -= satir_h
    c.save()
    return [cikti], ""


# --------------------------- LibreOffice -------------------------------------
LO_CIKIS = {
    # (kaynak ailesi, hedef) -> --convert-to değeri
    "docx": "docx:MS Word 2007 XML",
    "odt": "odt:writer8",
    "rtf": "rtf:Rich Text Format",
    "txt": "txt:Text (encoded):UTF8",
    "html": "html:HTML (StarWriter)",
}


def _lo_filtre(aile: str, hedef: str) -> str:
    if hedef == "pdf":
        return {"tablo": "pdf:calc_pdf_Export", "sunum": "pdf:impress_pdf_Export"}.get(aile, "pdf:writer_pdf_Export")
    if aile == "tablo":
        return {"xlsx": "xlsx:Calc MS Excel 2007 XML", "ods": "ods:calc8", "html": "html:HTML (StarCalc)",
                "csv": "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1"}[hedef]
    if aile == "sunum":
        return {"pptx": "pptx:Impress MS PowerPoint 2007 XML", "odp": "odp:impress8"}[hedef]
    if aile == "pdf" and hedef in ("pptx", "odp"):
        return {"pptx": "pptx:Impress MS PowerPoint 2007 XML", "odp": "odp:impress8"}[hedef]
    return LO_CIKIS[hedef]


def lo_calistir(o: Oturum, girdi: str, cikti_dizin: str, filtre: str, infilter: Optional[str] = None) -> list[str]:
    soffice = _soffice_bul()
    if not soffice:
        raise FilenorHata("arac_eksik", arac="libreoffice")
    onceki = set(os.listdir(cikti_dizin))
    son_hata = ""
    for deneme in (0, 1):
        profil = o.lo_profil(yeni=deneme == 1)
        kom = [soffice, f"-env:UserInstallation={pathlib.Path(profil).as_uri()}", "--headless", "--norestore", "--nologo",
               "--nodefault", "--nolockcheck"]
        if infilter:
            kom.append(f"--infilter={infilter}")
        kom += ["--convert-to", filtre, "--outdir", cikti_dizin, girdi]
        try:
            _, out, err = calistir(o, kom, "libreoffice", env={"HOME": o.taban, "SAL_USE_VCLPLUGIN": "svp"},
                                   zaman=min(o.zaman_asimi, 600.0 if deneme == 0 else 600.0))
            son_hata = (out + "\n" + err)
        except FilenorHata as h:
            if h.kod == "zaman_asimi" and deneme == 0:
                son_hata = "zaman aşımı"
                continue
            if h.kod == "arac_hata" and deneme == 0:
                son_hata = h.ayrinti.get("ayrinti", "")
                continue
            raise
        yeni = sorted(set(os.listdir(cikti_dizin)) - onceki)
        yeni = [os.path.join(cikti_dizin, y) for y in yeni if not y.startswith(".")]
        if yeni:
            return yeni
        if "no export filter" in son_hata.lower() or "error" in son_hata.lower():
            break
    raise FilenorHata("arac_hata", arac="LibreOffice", ayrinti=_son_satirlar(son_hata) or "çıktı üretilemedi")


def _csv_ayrac(metin: str) -> str:
    ornek = "\n".join(metin.splitlines()[:30])
    try:
        return csv.Sniffer().sniff(ornek, delimiters=",;\t|").delimiter
    except csv.Error:
        return ";" if ornek.count(";") > ornek.count(",") else ","


def _e_lo(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    aile = tur(ext)
    girdi = kaynak
    infilter = None
    calisma = os.path.join(isd, "lo")
    os.mkdir(calisma)
    if aile == "pdf":
        girdi = pdf_hazirla(o, kaynak, isd, sec.parola)
        infilter = "writer_pdf_import" if hedef in ("docx", "odt") else "impress_pdf_import"
        if hedef in ("docx", "odt"):
            # Metin yoksa (taranmış) kullanıcıyı uyar: LO görüntü olarak yerleştirir
            pass
    elif aile == "txt":
        girdi = os.path.join(isd, "girdi.txt")
        with open(girdi, "w", encoding="utf-8-sig") as f:
            f.write(metin_oku(kaynak))
    elif aile == "html":
        infilter = "HTML (StarWriter)"
    elif aile == "tablo" and ext == "csv":
        metin = metin_oku(kaynak)
        girdi = os.path.join(isd, "girdi.csv")
        with open(girdi, "w", encoding="utf-8", newline="") as f:
            f.write(metin)
        ayrac = ord(_csv_ayrac(metin))
        infilter = f"Text - txt - csv (StarCalc):{ayrac},34,76,1"
    o.ilerle(15, "LibreOffice")
    filtre = _lo_filtre("tablo" if aile == "tablo" else "sunum" if aile == "sunum" else
                        "pdf" if aile == "pdf" else "yazi", hedef)
    uretilen = lo_calistir(o, girdi, calisma, filtre, infilter)
    uretilen = [u for u in uretilen if os.path.isfile(u)]
    if not uretilen:
        raise FilenorHata("cikti_yok")
    # txt çıktısındaki BOM'u at
    if hedef == "txt":
        for u in uretilen:
            with open(u, "rb") as f:
                b = f.read()
            if b.startswith(b"\xef\xbb\xbf"):
                with open(u, "wb") as f:
                    f.write(b[3:])
    # html çıktısının yan dosyaları (resim) olabilir; yalnızca ana dosyayı al
    if hedef == "html":
        uretilen = [u for u in uretilen if u.endswith(".html")][:1] or uretilen
    # csv: tek sayfa -> tek dosya; çok sayfa -> klasör
    if hedef == "csv" and len(uretilen) > 1:
        uretilen.sort()
        return uretilen, "_sayfalar"
    if len(uretilen) > 1:
        uretilen = uretilen[:1]
    return uretilen, ""


def _e_sunum_gorsel(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    calisma = os.path.join(isd, "lo")
    os.mkdir(calisma)
    pdfler = lo_calistir(o, kaynak, calisma, "pdf:impress_pdf_Export")
    pdf = [p for p in pdfler if p.endswith(".pdf")][0]
    s = Secenek.sozlukten(sec.sozluk())
    s.sayfa_araligi = sec.sayfa_araligi
    dosyalar, _ = _pdf_sayfalari_gorsele(o, pdf, hedef, isd, s)
    yeniler = []
    for d in dosyalar:
        yeniler.append(os.path.join(isd, os.path.basename(d).replace("sayfa_", "slayt_")))
        os.replace(d, yeniler[-1])
    return yeniler, "_slaytlar"


# --------------------------- yazı tipi --------------------------------------
def _otf_ttf(font) -> None:
    """CFF (OpenType) dış çizgilerini TrueType'a çevirir (fontTools örnek kodu)."""
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.ttLib import newTable
    glyf_sirasi = font.getGlyphOrder()
    gs = font.getGlyphSet()
    yeni = {}
    for ad in glyf_sirasi:
        tt = TTGlyphPen(gs)
        gs[ad].draw(Cu2QuPen(tt, 1.0, reverse_direction=True))
        yeni[ad] = tt.glyph()
    font["loca"] = newTable("loca")
    font["glyf"] = glyf = newTable("glyf")
    glyf.glyphOrder = glyf_sirasi
    glyf.glyphs = yeni
    del font["CFF "]
    if "VORG" in font:
        del font["VORG"]
    glyf.compile(font)
    hmtx = font["hmtx"]
    for ad, g in glyf.glyphs.items():
        if hasattr(g, "xMin"):
            hmtx[ad] = (hmtx[ad][0], g.xMin)
    font["maxp"] = maxp = newTable("maxp")
    maxp.tableVersion = 0x00010000
    maxp.maxZones = 1
    maxp.maxTwilightPoints = 0
    maxp.maxStorage = 0
    maxp.maxFunctionDefs = 0
    maxp.maxInstructionDefs = 0
    maxp.maxStackElements = 0
    maxp.maxSizeOfInstructions = 0
    maxp.maxComponentElements = max((len(getattr(g, "components", []) or []) for g in glyf.glyphs.values()), default=0)
    maxp.compile(font)
    post = font["post"]
    post.formatType = 2.0
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = glyf_sirasi
    font.sfntVersion = "\000\001\000\000"


def _e_yazi(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek) -> Sonuc:
    from fontTools.ttLib import TTFont, TTLibError
    try:
        font = TTFont(kaynak, lazy=False)
    except (TTLibError, OSError, struct_error) as e:
        raise FilenorHata("okunamadi", ayrinti=str(e)[:200])
    cff = "CFF " in font or "CFF2" in font
    glyf = "glyf" in font
    if hedef == "otf" and not cff:
        raise FilenorHata("yazi_tur")
    if hedef == "ttf" and cff and "CFF " in font:
        try:
            _otf_ttf(font)
        except Exception as e:
            raise FilenorHata("arac_hata", arac="fontTools", ayrinti=str(e)[:200])
    elif hedef == "ttf" and not glyf:
        raise FilenorHata("yazi_tur")
    font.flavor = {"ttf": None, "otf": None, "woff": "woff", "woff2": "woff2"}[hedef]
    cikti = os.path.join(isd, "cikti." + hedef)
    try:
        font.save(cikti)
    except Exception as e:
        raise FilenorHata("arac_hata", arac="fontTools", ayrinti=str(e)[:200])
    return [cikti], ""


try:  # fontTools yapı hataları
    from struct import error as struct_error
except Exception:  # pragma: no cover
    struct_error = OSError


# ---------------------------------------------------------------------------
# Toplu iş koşucusu (arayüz ve CLI için)
# ---------------------------------------------------------------------------
@dataclass
class Is:
    kaynak: str
    hedef: str
    durum: str = "bekliyor"       # bekliyor | calisiyor | tamam | hata | iptal
    sonuc: list = field(default_factory=list)
    hata: Optional[FilenorHata] = None
    yuzde: float = 0.0
    sure: float = 0.0
    boyut_once: int = 0
    boyut_sonra: int = 0
    dosyalar: list = field(default_factory=list)   # çok girdili araçlar için (birleştir)


class Kosucu(threading.Thread):
    """İşleri sırayla çalıştırır. Geri çağrılar KOŞUCU iş parçacığından gelir
    (GTK tarafında GLib.idle_add ile ana döngüye aktarın)."""

    def __init__(self, isler: list[Is], cikti_dizin: Optional[str], secenek: Secenek,
                 is_cb: Optional[Callable[[int, Is], None]] = None,
                 bitti_cb: Optional[Callable[[list[Is]], None]] = None,
                 yanina: bool = False):
        super().__init__(daemon=True, name="filenor-kosucu")
        self.isler = isler
        self.cikti_dizin = cikti_dizin
        self.yanina = yanina
        self.secenek = secenek
        self.is_cb = is_cb
        self.bitti_cb = bitti_cb
        self.iptal = threading.Event()
        self.zip_yolu: Optional[str] = None

    def iptal_et(self) -> None:
        self.iptal.set()

    def _bildir(self, i: int) -> None:
        if self.is_cb:
            try:
                self.is_cb(i, self.isler[i])
            except Exception:
                pass

    def run(self) -> None:
        with Oturum(iptal=self.iptal) as o:
            for i, is_ in enumerate(self.isler):
                if self.iptal.is_set():
                    is_.durum = "iptal"
                    self._bildir(i)
                    continue
                is_.durum = "calisiyor"
                is_.yuzde = 0.0
                self._bildir(i)

                def ilerle(p, metin, i=i, is_=is_):
                    if p is not None:
                        is_.yuzde = p
                    self._bildir(i)
                o.ilerleme_cb = ilerle
                bas = time.monotonic()
                try:
                    hedef_dizin = (os.path.dirname(os.path.abspath(is_.kaynak)) if self.yanina or not self.cikti_dizin
                                   else self.cikti_dizin)
                    girdiler = is_.dosyalar or [is_.kaynak]
                    is_.boyut_once = sum(os.path.getsize(g) for g in girdiler if os.path.exists(g))
                    is_.sonuc = self._calistir_is(o, is_, hedef_dizin)
                    is_.boyut_sonra = sum(os.path.getsize(s) for s in is_.sonuc if os.path.exists(s))
                    is_.durum = "tamam"
                    is_.yuzde = 100.0
                except Iptal:
                    is_.durum = "iptal"
                except FilenorHata as h:
                    is_.durum = "hata"
                    is_.hata = h
                except Exception as e:  # beklenmeyen: uygulama çökmesin
                    is_.durum = "hata"
                    is_.hata = FilenorHata("bilinmeyen", ayrinti=f"{type(e).__name__}: {e}"[:300])
                is_.sure = time.monotonic() - bas
                self._bildir(i)
            if self.secenek.zip_yap and not self.iptal.is_set():
                self._zip_yap()
        if self.bitti_cb:
            try:
                self.bitti_cb(self.isler)
            except Exception:
                pass

    def _calistir_is(self, o: Oturum, is_: Is, hedef_dizin: str) -> list[str]:
        return donustur(is_.kaynak, is_.hedef, hedef_dizin, self.secenek, o)

    def _zip_yap(self) -> None:
        import zipfile
        tum = [s for i in self.isler if i.durum == "tamam" for s in i.sonuc]
        if len(tum) < 2:
            return
        kok = os.path.commonpath([os.path.dirname(t) for t in tum])
        self.zip_yolu = benzersiz_yol(kok, "filenor", "zip")
        with zipfile.ZipFile(self.zip_yolu, "w", zipfile.ZIP_DEFLATED) as z:
            for t in tum:
                z.write(t, os.path.relpath(t, kok))


# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------
def ayar_yolu() -> str:
    return os.path.join(S.ayar_dizini(), "filenor.json")


def ayar_oku() -> dict:
    try:
        with open(ayar_yolu(), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ayar_yaz(d: dict) -> None:
    yol = ayar_yolu()
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        gecici = yol + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(gecici, yol)
    except OSError:
        pass


def insan_boyut(n: int) -> str:
    v = float(n)
    for b in ("B", "KB", "MB", "GB"):
        if v < 1024 or b == "GB":
            return f"{int(v)} {b}" if b == "B" else f"{v:.1f} {b}"
        v /= 1024
    return f"{n} B"
