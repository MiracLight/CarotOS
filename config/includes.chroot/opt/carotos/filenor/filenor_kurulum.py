# -*- coding: utf-8 -*-
"""
Filenor -- eksik araclari tek tikla kurma. GTK'siz.

Mantik burada, dugmeler arayuzdedir. Hata metinleri dilden bagimsiz kodla atilir
(filenor_dil.FilenorHata); arayuz kullanicinin diliyle gosterir.

Yontemler:
  * Debian/CarotOS: paketler "apt-get" ile, yonetici yetkisini "pkexec" ister.
    Once hepsi birden kurulur; biri bulunamazsa tek tek denenir, boylece bir
    paketin eksikligi ote kurulumlari engellemez.
  * Windows: harici araclar "winget" ile kurulur (kurucu gerekirse kendi yetki
    penceresini acar). Python modulleri paketle birlikte gelir; kaynak koddan
    calisirken "pip --user" kullanilir.
  * apt yoksa (macOS, baska dagitimlar) ya da pakette bulunmayan bir Python
    modulu ise (rawpy) "pip --user" kullanilir; yonetici yetkisi gerekmez.

Paket adlari sabit tablodadir; kullanici girdisi hicbir komuta karismaz.
"""

from __future__ import annotations

import importlib
import os
import re
import shutil
import site
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

import filenor_sistem as S
from filenor_dil import FilenorHata

# Arac anahtari -> Debian paketleri (filenor_motor.araclar_durumu anahtarlariyla ayni)
APT = {
    "ffmpeg": ["ffmpeg"],
    "ffprobe": ["ffmpeg"],
    "pdftoppm": ["poppler-utils"],
    "pdftotext": ["poppler-utils"],
    "pdfinfo": ["poppler-utils"],
    "qpdf": ["qpdf"],
    "tesseract": ["tesseract-ocr", "tesseract-ocr-tur", "tesseract-ocr-eng"],
    "pillow": ["python3-pil"],
    "reportlab": ["python3-reportlab"],
    "fonttools": ["python3-fonttools"],
    "brotli": ["python3-brotli"],
    "svg": ["python3-cairosvg"],
    "heif": ["python3-pillow-heif"],
    "pypdf": ["python3-pypdf"],
    "gs": ["ghostscript"],
    "libreoffice": ["libreoffice-writer", "libreoffice-calc", "libreoffice-impress"],
}

# Arac anahtari -> winget paket kimligi (Windows)
WINGET = {
    "ffmpeg": "Gyan.FFmpeg",
    "ffprobe": "Gyan.FFmpeg",
    "pdftoppm": "oschwartz10612.Poppler",
    "pdftotext": "oschwartz10612.Poppler",
    "pdfinfo": "oschwartz10612.Poppler",
    "qpdf": "QPDF.QPDF",
    "tesseract": "UB-Mannheim.TesseractOCR",
    "gs": "ArtifexSoftware.GhostScript",
    "libreoffice": "TheDocumentFoundation.LibreOffice",
}
# winget: 0x8A15002B (guncelleme gerekmiyor / zaten kurulu) basari sayilir
WINGET_TAMAM = (0, -1978335189)

# Arac anahtari -> pip paketi (apt'de olmayanlar ve apt'siz sistemler icin)
PIP = {
    "pillow": "Pillow",
    "reportlab": "reportlab",
    "fonttools": "fonttools",
    "brotli": "brotli",
    "svg": "cairosvg",
    "rawpy": "rawpy",
    "heif": "pillow-heif",
    "pypdf": "pypdf",
}
# Debian'da paketi olmayanlar yalniz pip'ten kurulur
SADECE_PIP = ("rawpy",)

# Bu Pillow surumunun ozelligi; kurulumla degismez
KURULAMAZ = ("avif", "webp")
# Buyuk ya da istege bagli: "Eksikleri kur"a girmez, satirdaki Kur ile ayri kurulur
ISTEGE_BAGLI = ("libreoffice", "gs")

# Ayarlar sayfasindaki siralama
SIRA = ("ffmpeg", "libreoffice", "pdftoppm", "qpdf", "tesseract", "pillow", "reportlab",
        "fonttools", "brotli", "svg", "avif", "rawpy", "heif", "gs")

PIP_PAKETI = "python3-pip"

# Debian surumunuzda bulunmayan bir python3-* paketi icin pip yedegi
APT_PIP_YEDEK = {APT[k][0]: PIP[k] for k in PIP if k in APT and len(APT[k]) == 1 and k not in SADECE_PIP}

# Ilerleme araligi: indirme ve kurulum payi (apt)
PAY_INDIR = 0.55
PAY_GUNCELLE = 0.03

# pkexec cikis kodlari: 126 = yetki verilmedi / pencere kapatildi, 127 = yetki alinamadi
YETKI_KODLARI = (126, 127)

# Yonetici yetkisiyle calisan betik. $@ = paket adlari.
# Cikis: 0 hepsi tamam, 3 en az bir paket kurulamadi.
APT_BETIGI = r"""
export LC_ALL=C DEBIAN_FRONTEND=noninteractive
echo "FILENOR_ASAMA guncelle"
apt-get update -qq || echo "FILENOR_UYARI guncelleme"
echo "FILENOR_ASAMA kur"
# APT::Status-Fd=1: indirme ve kurulum yuzdelerini 'dlstatus:' / 'pmstatus:' satirlari olarak yazar
if apt-get -o APT::Status-Fd=1 -o Dpkg::Use-Pty=0 install -y --no-install-recommends "$@"; then
    exit 0
fi
sonuc=0
for p in "$@"; do
    apt-get -o APT::Status-Fd=1 -o Dpkg::Use-Pty=0 install -y --no-install-recommends "$p" \
        || { echo "FILENOR_PAKET_YOK $p"; sonuc=3; }
done
exit $sonuc
"""


@dataclass
class Plan:
    apt: list = field(default_factory=list)      # kurulacak Debian paketleri
    winget: list = field(default_factory=list)   # kurulacak winget paketleri (Windows)
    pip: list = field(default_factory=list)      # kurulacak pip paketleri
    elle: list = field(default_factory=list)     # otomatik kurulamayan arac anahtarlari
    anahtarlar: list = field(default_factory=list)  # kurulmasi istenen (eksik) araclar

    @property
    def bos(self) -> bool:
        return not self.apt and not self.pip and not self.winget

    @property
    def paketler(self) -> list:
        return self.apt + self.winget + self.pip


def apt_var() -> bool:
    return sys.platform.startswith("linux") and bool(shutil.which("apt-get"))


def winget_var() -> bool:
    return S.WINDOWS and bool(shutil.which("winget"))


def pip_var() -> bool:
    if S.DONMUS:            # paketlenmis uygulamada sys.executable uygulamanin kendisidir; pip calismaz
        return False
    try:
        importlib.import_module("pip")
        return True
    except Exception:
        return False


def temel_eksikler(durum: dict) -> list:
    """'Eksikleri kur' dugmesinin kapsami: kurulabilen, buyuk olmayan eksikler."""
    return [k for k in SIRA
            if not durum.get(k) and k not in ISTEGE_BAGLI and k not in KURULAMAZ]


def plan(anahtarlar, durum: dict, apt_kullan: Optional[bool] = None,
         pip_kullan: Optional[bool] = None, winget_kullan: Optional[bool] = None) -> Plan:
    """Eksik araclar icin kurulum plani. Kurulu olanlar atlanir; kurulamayanlar 'elle'ye gider."""
    apt_ok = apt_var() if apt_kullan is None else apt_kullan
    wg_ok = winget_var() if winget_kullan is None else winget_kullan
    pip_ok = (pip_var() or apt_ok) if pip_kullan is None else pip_kullan
    p = Plan()
    for a in anahtarlar:
        if durum.get(a) or a in p.anahtarlar:
            continue
        p.anahtarlar.append(a)
        if a in KURULAMAZ:
            p.elle.append(a)
        elif wg_ok and a in WINGET:
            if WINGET[a] not in p.winget:
                p.winget.append(WINGET[a])
        elif apt_ok and a in APT and a not in SADECE_PIP:
            for pk in APT[a]:
                if pk not in p.apt:
                    p.apt.append(pk)
        elif a in PIP and pip_ok:
            if PIP[a] not in p.pip:
                p.pip.append(PIP[a])
        else:
            p.elle.append(a)
    # apt'te hic pip yoksa, pip gerekiyorsa once onu kur
    if p.pip and apt_ok and not pip_var() and PIP_PAKETI not in p.apt:
        p.apt.insert(0, PIP_PAKETI)
    return p


def yetki_komutu() -> Optional[list]:
    """apt icin on ek: root ise bos, degilse ['pkexec'], yetki araci yoksa None."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    yol = shutil.which("pkexec")
    return [yol] if yol else None


class _Ilerleme:
    """Ilerleme geri cagrisini tek yonlu (geri gitmeyen) tutar. oran None = belirsiz."""

    def __init__(self, cb):
        self.cb = cb
        self.son = 0.0

    def ver(self, oran, asama, ayrinti=""):
        if not self.cb:
            return
        if oran is not None:
            oran = max(self.son, min(1.0, oran))
            self.son = oran
        self.cb(oran, asama, ayrinti)


def _apt_satiri(satir, durum, ilerle, bas, son):
    """apt durum satirini yorumlar. True = ilerleme satiriydi (metin olarak gosterilmez).
    durum['asama']: guncelle | indir | kur. bas..son: bu adimin toplam ilerleme araligi."""
    if satir.startswith("FILENOR_ASAMA "):
        durum["asama"] = satir.split(" ", 1)[1]
        if durum["asama"] == "guncelle":
            ilerle.ver(bas + (son - bas) * 0.01, "guncelle")
        return True
    if satir.startswith(("dlstatus:", "pmstatus:")):
        alanlar = satir.split(":", 3)
        try:
            yuzde = float(alanlar[2]) / 100.0
        except (IndexError, ValueError):
            return True
        if alanlar[0] == "dlstatus":
            oran = PAY_GUNCELLE + (PAY_INDIR - PAY_GUNCELLE) * yuzde
            ilerle.ver(bas + (son - bas) * oran, "indir", "%d" % round(yuzde * 100))
        else:
            ad = alanlar[1] if alanlar[1] != "dpkg-exec" else ""
            oran = PAY_INDIR + (1.0 - PAY_INDIR) * yuzde
            ilerle.ver(bas + (son - bas) * oran, "kur", ad)
        return True
    return False


def _satirlari_oku(surec, satir_cb, apt_cb=None) -> list:
    yok = []
    for satir in surec.stdout:
        satir = satir.rstrip()
        if satir.startswith("FILENOR_PAKET_YOK "):
            yok.append(satir.split(" ", 1)[1])
        if apt_cb and apt_cb(satir):
            continue
        if satir and satir_cb:
            satir_cb(satir)
    return yok


def _calistir(komut, satir_cb, env=None, satir_islem=None):
    """(cikis_kodu, tum_cikti, yok_paketler). Kendi surec grubunda baslar.
    satir_islem(satir) True dondururse satir metin olarak bildirilmez."""
    s = subprocess.Popen(komut, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         bufsize=1, encoding="utf-8", errors="replace", env=env, **S.popen_ayarlari())
    cikti = []

    def cb(x):
        cikti.append(x)
        if satir_cb:
            satir_cb(x)

    try:
        yok = _satirlari_oku(s, cb, satir_islem)
    finally:
        s.stdout.close()
    kod = s.wait()
    return kod, "\n".join(cikti), yok


def _pip_kur(ad, satir_cb, env, ilerle, aralik):
    """Tek pip paketi (--user). aralik=(bas, son): pip'in 'Progress X of Y' satirlarindan
    ilerleme verilir; None ise boyut bilinmez (belirsiz ilerleme)."""
    taban = [sys.executable, "-m", "pip", "install", "--user", "--disable-pip-version-check", ad]

    def satir_islem(satir):
        if satir.startswith("Progress "):
            try:
                _p, x, _of, y = satir.split()
                if aralik:
                    bas, son = aralik
                    ilerle.ver(bas + (son - bas) * 0.95 * min(1.0, int(x) / max(1, int(y))), "pip", ad)
            except ValueError:
                pass
            return True
        return False

    ilerle.ver(aralik[0] if aralik else None, "pip", ad)
    ek = ["--progress-bar", "raw"]
    kod, cikti, _ = _calistir(taban + ek, satir_cb, env, satir_islem)
    if kod != 0 and "invalid choice" in cikti:          # eski pip: 'raw' yok
        ek = []
        kod, cikti, _ = _calistir(taban, satir_cb, env, satir_islem)
    if kod != 0 and "externally-managed-environment" in cikti:
        # Debian: --user kurulumu sistemi bozmaz, ama bayrak gerekir
        kod, cikti, _ = _calistir(taban + ek + ["--break-system-packages"], satir_cb, env, satir_islem)
    if aralik:
        ilerle.ver(aralik[1], "pip", ad)
    return kod == 0


def _winget_kur(kimlik, satir_cb, env, ilerle, aralik) -> bool:
    """Tek winget paketi. Ilerleme: winget'in yazdigi son '%' degeri; yoksa adim sonunda ilerler."""
    bas, son = aralik

    def satir_islem(satir):
        yuzdeler = re.findall(r"(\d{1,3})\s?%", satir)
        if yuzdeler:
            ilerle.ver(bas + (son - bas) * min(100, int(yuzdeler[-1])) / 100.0 * 0.97, "winget", kimlik)
            return True
        # bos/animasyon satirlari (|, /, -, \\) ve ilerleme cubugu bloklari metin olarak gosterilmez
        return not satir.strip(" |/\\-\u2588\u2592\u2593\u2591\r") or satir.lstrip().startswith(("\u2588", "\u2592"))

    ilerle.ver(bas, "winget", kimlik)
    kom = [S.coz("winget"), "install", "--id", kimlik, "-e", "--silent",
           "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"]
    kod, _cikti, _ = _calistir(kom, satir_cb, env, satir_islem)
    ilerle.ver(son, "winget", kimlik)
    return kod in WINGET_TAMAM


def kur(plan_: Plan, satir_cb: Optional[Callable[[str], None]] = None,
        yetki: Optional[list] = None, env: Optional[dict] = None,
        ilerleme_cb: Optional[Callable] = None) -> list:
    """Plani uygular. Kurulamayan paket adlarinin listesini dondurur (bos = hepsi tamam).

    ilerleme_cb(oran, asama, ayrinti): oran 0..1 (geri gitmez) ya da None (belirsiz);
    asama: guncelle | indir | kur | pip | winget; ayrinti: yuzde ya da paket adi.
    Hata: FilenorHata('kurulum_yonetici_yok' | 'kurulum_yetki' | 'kurulum_basarisiz').
    Sonunda cagiran ortami_yenile() ve araclar_durumu() ile gercek durumu denetlemeli.
    """
    ilerle = _Ilerleme(ilerleme_cb)
    basarisiz: list = []
    planli_pip = list(plan_.pip)
    yedek_pip: list = []                    # apt'de bulunamayanlar icin pip yedegi

    # adimlar ve agirliklari: ilerleme araligi bunlara gore bolunur
    adimlar = []
    if plan_.apt:
        adimlar.append(("apt", None, 4.0))
    adimlar += [("winget", k, 3.0) for k in plan_.winget]
    adimlar += [("pip", k, 1.0) for k in planli_pip]
    toplam = sum(a[2] for a in adimlar) or 1.0
    araliklar = []
    konum = 0.0
    for tur_, ad, agirlik in adimlar:
        araliklar.append((tur_, ad, (konum / toplam, (konum + agirlik) / toplam)))
        konum += agirlik

    for tur_, ad, aralik in araliklar:
        if tur_ == "apt":
            on_ek = yetki_komutu() if yetki is None else yetki
            if on_ek is None:
                raise FilenorHata("kurulum_yonetici_yok")
            komut = on_ek + ["/bin/sh", "-c", APT_BETIGI, "sh"] + list(plan_.apt)
            durum = {"asama": "guncelle"}
            kod, _cikti, yok = _calistir(
                komut, satir_cb, env, lambda s_: _apt_satiri(s_, durum, ilerle, aralik[0], aralik[1]))
            if kod in YETKI_KODLARI and on_ek:
                raise FilenorHata("kurulum_yetki")
            if kod not in (0, 3):
                raise FilenorHata("kurulum_basarisiz", cikis=kod)
            for pk in yok:
                yedek = APT_PIP_YEDEK.get(pk)
                if yedek and yedek not in planli_pip and yedek not in yedek_pip:
                    yedek_pip.append(yedek)
                else:
                    basarisiz.append(pk)
            ilerle.ver(aralik[1], "kur")
        elif tur_ == "winget":
            if not _winget_kur(ad, satir_cb, env, ilerle, aralik):
                basarisiz.append(ad)
        else:
            if not _pip_kur(ad, satir_cb, env, ilerle, aralik):
                basarisiz.append(ad)
    for ad in yedek_pip:                     # boyut bilinmez: belirsiz ilerleme
        if not _pip_kur(ad, satir_cb, env, ilerle, None):
            basarisiz.append(ad)
    ilerle.ver(1.0, "kur")
    return basarisiz


def ortami_yenile() -> None:
    """Calisan surecin yeni kurulan modulleri ve programlari gormesini saglar."""
    importlib.invalidate_caches()
    S.ortam_hazirla()
    try:
        kullanici = site.getusersitepackages()
        if kullanici and os.path.isdir(kullanici):
            site.addsitedir(kullanici)
    except Exception:
        pass
    import filenor_motor as M
    M.araclari_yenile()
