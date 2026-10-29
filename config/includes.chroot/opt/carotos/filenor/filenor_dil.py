# -*- coding: utf-8 -*-
"""
Filenor -- motor mesajlari (TR/EN). GTK'siz.

Motor hatalari koduyla atilir (FilenorHata); arayuz metni burada, kullanicinin
diliyle kurulur. Boylece motor dilden bagimsiz kalir, testler kodu dener.
"""

from __future__ import annotations

import os

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


def ipucu_al(arac: str, dil: str = "tr") -> str:
    """Eksik arac icin kurulum ipucu; isletim sistemine gore (apt komutu / winget kimligi)."""
    if os.name == "nt":
        if arac in _WINGET_KIMLIK:
            k = _WINGET_KIMLIK[arac]
            return (f"Kurulum: winget install {k} (ya da Ayarlar'daki Kur düğmesi)" if dil == "tr"
                    else f"Install: winget install {k} (or the Install button in Settings)")
        if arac in ("avif", "webp"):
            pass
        elif arac in ARAC_IPUCU:
            return ("Bu Filenor sürümünde yok; en son sürümü indirin" if dil == "tr"
                    else "Not included in this Filenor build; download the latest release")
    ip = ARAC_IPUCU.get(arac, {})
    return ip.get(dil) or ip.get("tr", "")


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
    kalip = kayit.get(dil) or kayit["tr"]
    d = dict(h.ayrinti)
    if h.kod == "arac_eksik":
        d["ipucu"] = ipucu_al(d.get("arac", ""), dil)
    try:
        return kalip.format(**d).strip()
    except (KeyError, IndexError):
        return kalip


def mesaj(kod: str, dil: str = "tr", **d) -> str:
    return hata_metni(FilenorHata(kod, **d), dil)
