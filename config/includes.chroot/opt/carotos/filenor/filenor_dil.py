# -*- coding: utf-8 -*-
"""
Filenor -- motor mesajlari (TR/EN). GTK'siz.

Motor hatalari koduyla atilir (FilenorHata); arayuz metni burada, kullanicinin
diliyle kurulur. Boylece motor dilden bagimsiz kalir, testler kodu dener.
"""

from __future__ import annotations

import os
import sys

# Ortak dil katmani (ortak/dil.py): 9 dil icin ceviri dosyalarindan metin. Filenor tek basina
# (ortak/ olmadan) calisirsa yalniz tr/en bilinir; burasi onu sessizce karsilar.
try:
    import dil as _dil
except ImportError:
    _ORTAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ortak")
    if os.path.isdir(_ORTAK) and _ORTAK not in sys.path:
        sys.path.insert(0, _ORTAK)
    try:
        import dil as _dil
    except ImportError:
        _dil = None


def sec(sozluk, kod: str) -> str:
    """{"tr","en",..} sozlugunden `kod` dilindeki metin; yoksa dil dosyasi, en, tr siralamasiyla."""
    if _dil is not None:
        return _dil.metin(sozluk, kod)
    return sozluk.get(kod) or sozluk.get("en") or sozluk.get("tr", "")


def T(sozluk, kod: str, **kw) -> str:
    """sec() + str.format; bozuk ceviri yer tutucusunda Ingilizce/Turkce metne duser, istisna atmaz."""
    if _dil is not None:
        return _dil.T(sozluk, kod, None, **kw)
    sablon = sec(sozluk, kod)
    try:
        return sablon.format(**kw)
    except (KeyError, IndexError, ValueError):
        return sablon


def zengin(veri):
    """Ic ice {"tr","en"} sozluklerini `[kod]` ile her dilde guvenle okunur yapar."""
    return _dil.zenginlestir(veri) if _dil is not None else veri


def etkin_diller():
    """Dil seciciye girecek [(kod, ad, taslak_mi)]; ortak katman yoksa yalniz tr/en."""
    if _dil is not None:
        return _dil.etkin_diller()
    return [("tr", "Türkçe", False), ("en", "English", False)]


def secici_adi(kod: str, ad: str, taslak: bool) -> str:
    """Dil seciciye yazilacak ad (yazi tipi yoksa Latin ad; taslak ise '(beta)')."""
    if _dil is not None:
        return _dil.secici_adi(kod, ad, taslak)
    return f"{ad} (beta)" if taslak else ad


def gecerli_dil(kod: str):
    """Ayardaki dil seciciye girebiliyorsa kod, degilse None."""
    return kod if kod in {k for k, _, _ in etkin_diller()} else None


def varsayilan_dil():
    """Sistem dilinden ilk acilis dili (ortak katman yoksa None)."""
    return _dil.varsayilan_dil() if _dil is not None else None


MESAJ = {
    "ayni_bicim": {
        "tr": "Kaynak ve hedef biçim aynı. Boyutu küçültmek için Araçlar bölümüne bakın",
        "en": "Source and target formats are the same. To shrink a file, see the Tools section"},
    "desteklenmiyor": {
        "tr": "'{kaynak}' dosyası '{hedef}' biçimine dönüştürülemez",
        "en": "A '{kaynak}' file cannot be converted to '{hedef}'"},
    "ses_video_degil": {
        "tr": "Ses dosyası videoya dönüştürülemez (görüntü akışı yok)",
        "en": "Audio cannot be converted to video (there is no picture stream)"},
    "arac_eksik": {
        "tr": "Bu dönüşüm için '{arac}' gerekli ve bulunamadı. {ipucu}",
        "en": "This conversion needs '{arac}', which was not found. {ipucu}"},
    "yazi_tur": {
        "tr": "Bu yazı tipi TrueType dış çizgili; OpenType (CFF) biçimine çevrilemez",
        "en": "This font has TrueType outlines and cannot be converted to OpenType (CFF)"},
    "dosya_yok": {
        "tr": "Dosya bulunamadı: {yol}", "en": "File not found: {yol}"},
    "dosya_bos": {
        "tr": "Dosya boş: {yol}", "en": "File is empty: {yol}"},
    "okunamadi": {
        "tr": "Dosya açılamadı ya da bozuk: {ayrinti}",
        "en": "The file could not be opened or is damaged: {ayrinti}"},
    "arac_hata": {
        "tr": "'{arac}' hata verdi: {ayrinti}", "en": "'{arac}' reported an error: {ayrinti}"},
    "cikti_yok": {
        "tr": "Dönüşüm bitti ama çıktı dosyası oluşmadı", "en": "The conversion finished but no output file was produced"},
    "zaman_asimi": {
        "tr": "'{arac}' belirlenen sürede bitmedi ve durduruldu",
        "en": "'{arac}' did not finish in time and was stopped"},
    "iptal": {"tr": "İptal edildi", "en": "Cancelled"},
    "sifreli_pdf": {
        "tr": "PDF parola korumalı; önce parolasını kaldırmalısınız",
        "en": "The PDF is password-protected; remove the password first"},
    "metin_yok": {
        "tr": "PDF'te seçilebilir metin yok (taranmış olabilir). OCR aracını deneyin",
        "en": "The PDF has no selectable text (it may be scanned). Try the OCR tool"},
    "en_az_bir": {
        "tr": "Bu işlem için en az {n} dosya gerekli", "en": "This operation needs at least {n} file(s)"},
    "sayfa_araligi": {
        "tr": "Sayfa aralığı geçersiz: '{aralik}' (örnek: 1-3,5,8-10)",
        "en": "Invalid page range: '{aralik}' (example: 1-3,5,8-10)"},
    "pdf_degil": {
        "tr": "Bu işlem yalnızca PDF dosyalarıyla çalışır: {ad}",
        "en": "This operation only works on PDF files: {ad}"},
    "cikti_yazilamaz": {
        "tr": "Çıktı klasörüne yazılamıyor: {yol} ({ayrinti})",
        "en": "Cannot write to the output folder: {yol} ({ayrinti})"},
    "kirp_gecersiz": {
        "tr": "Kırpma aralığı geçersiz (bitiş, başlangıçtan büyük olmalı)",
        "en": "Invalid trim range (end must be after start)"},
    "ocr_dil": {
        "tr": "Seçilen OCR dili kurulu değil. Kurulu diller: {diller}",
        "en": "The selected OCR language is not installed. Installed: {diller}"},
    "kurulum_yonetici_yok": {
        "tr": "Bu sistemde yönetici yetkisi aracı (pkexec) bulunamadı; araçları terminalden kurun",
        "en": "No privilege helper (pkexec) was found on this system; install the tools from a terminal"},
    "kurulum_yetki": {
        "tr": "Yönetici yetkisi alınamadı (parola penceresi kapatıldı ya da yetki aracı çalışmıyor)",
        "en": "Administrator rights were not granted (the password prompt was closed or the helper is not running)"},
    "kurulum_basarisiz": {
        "tr": "Kurulum tamamlanamadı (çıkış kodu {cikis}). İnternet bağlantısını ve paket kilidini kontrol edin",
        "en": "The installation did not finish (exit code {cikis}). Check the network and that no other package manager is running"},
    "bilinmeyen": {"tr": "Beklenmeyen hata: {ayrinti}", "en": "Unexpected error: {ayrinti}"},
}

# Eksik arac icin kullaniciya yol gosteren kisa ipucu.
ARAC_IPUCU = {
    "ffmpeg": {"tr": "Kurulum: sudo apt install ffmpeg", "en": "Install: sudo apt install ffmpeg"},
    "ffprobe": {"tr": "Kurulum: sudo apt install ffmpeg", "en": "Install: sudo apt install ffmpeg"},
    "libreoffice": {"tr": "Kurulum: sudo apt install libreoffice", "en": "Install: sudo apt install libreoffice"},
    "pdftoppm": {"tr": "Kurulum: sudo apt install poppler-utils", "en": "Install: sudo apt install poppler-utils"},
    "pdftotext": {"tr": "Kurulum: sudo apt install poppler-utils", "en": "Install: sudo apt install poppler-utils"},
    "pdfinfo": {"tr": "Kurulum: sudo apt install poppler-utils", "en": "Install: sudo apt install poppler-utils"},
    "qpdf": {"tr": "Kurulum: sudo apt install qpdf", "en": "Install: sudo apt install qpdf"},
    "tesseract": {"tr": "Kurulum: sudo apt install tesseract-ocr tesseract-ocr-tur", "en": "Install: sudo apt install tesseract-ocr"},
    "pillow": {"tr": "Kurulum: sudo apt install python3-pil", "en": "Install: sudo apt install python3-pil"},
    "reportlab": {"tr": "Kurulum: sudo apt install python3-reportlab", "en": "Install: sudo apt install python3-reportlab"},
    "fonttools": {"tr": "Kurulum: sudo apt install python3-fonttools", "en": "Install: sudo apt install python3-fonttools"},
    "brotli": {"tr": "Kurulum: sudo apt install python3-brotli", "en": "Install: sudo apt install python3-brotli"},
    "svg": {"tr": "Kurulum: sudo apt install python3-cairosvg", "en": "Install: sudo apt install python3-cairosvg"},
    "rawpy": {"tr": "Kurulum: pip install --user rawpy", "en": "Install: pip install --user rawpy"},
    "heif": {"tr": "Kurulum: sudo apt install python3-pillow-heif", "en": "Install: sudo apt install python3-pillow-heif"},
    "avif": {"tr": "Bu Pillow sürümü AVIF desteklemiyor", "en": "This Pillow build has no AVIF support"},
    "gs": {"tr": "Kurulum: sudo apt install ghostscript", "en": "Install: sudo apt install ghostscript"},
    "webp": {"tr": "Bu Pillow sürümü WebP desteklemiyor", "en": "This Pillow build has no WebP support"},
    "pypdf": {"tr": "Kurulum: sudo apt install python3-pypdf", "en": "Install: sudo apt install python3-pypdf"},
}


# Windows: harici araclar winget ile; Python modulleri uygulamayla birlikte gelir
_WINGET_KIMLIK = {
    "ffmpeg": "Gyan.FFmpeg", "ffprobe": "Gyan.FFmpeg",
    "pdftoppm": "oschwartz10612.Poppler", "pdftotext": "oschwartz10612.Poppler", "pdfinfo": "oschwartz10612.Poppler",
    "qpdf": "QPDF.QPDF", "tesseract": "UB-Mannheim.TesseractOCR", "gs": "ArtifexSoftware.GhostScript",
    "libreoffice": "TheDocumentFoundation.LibreOffice",
}


_WINGET_IPUCU = {
    "tr": "Kurulum: winget install {k} (ya da Ayarlar'daki Kur düğmesi)",
    "en": "Install: winget install {k} (or the Install button in Settings)"}
_WINDOWS_YOK = {
    "tr": "Bu Filenor sürümünde yok; en son sürümü indirin",
    "en": "Not included in this Filenor build; download the latest release"}


def ipucu_al(arac: str, dil: str = "tr") -> str:
    """Eksik arac icin kurulum ipucu; isletim sistemine gore (apt komutu / winget kimligi)."""
    if os.name == "nt":
        if arac in _WINGET_KIMLIK:
            k = _WINGET_KIMLIK[arac]
            return T(_WINGET_IPUCU, dil, k=k)
        if arac in ("avif", "webp"):
            pass
        elif arac in ARAC_IPUCU:
            return sec(_WINDOWS_YOK, dil)
    ip = ARAC_IPUCU.get(arac)
    return sec(ip, dil) if ip else ""


class FilenorHata(Exception):
    """Motorun kodlu hatasi. str(h) Turkce metni verir; arayuz hata_metni() kullanir."""

    def __init__(self, kod: str, **ayrinti):
        self.kod = kod
        self.ayrinti = ayrinti
        super().__init__(hata_metni(self, "tr"))


class Iptal(Exception):
    """Kullanici islemi iptal etti."""


def hata_metni(h: "FilenorHata", dil: str = "tr") -> str:
    kayit = MESAJ.get(h.kod)
    if not kayit:
        return f"{h.kod}: {h.ayrinti}"
    kalip = sec(kayit, dil)
    d = dict(h.ayrinti)
    if h.kod == "arac_eksik":
        d["ipucu"] = ipucu_al(d.get("arac", ""), dil)
    # ceviri yer tutucuyu bozmussa Ingilizce, o da olmazsa Turkce metne dusulur
    for aday in (kalip, kayit.get("en"), kayit.get("tr")):
        if not aday:
            continue
        try:
            return aday.format(**d).strip()
        except (KeyError, IndexError, ValueError):
            continue
    return kalip


def mesaj(kod: str, dil: str = "tr", **d) -> str:
    return hata_metni(FilenorHata(kod, **d), dil)
