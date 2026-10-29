# -*- coding: utf-8 -*-
"""
Filenor araçları -- biçim değiştirmeyen işlemler (PDF birleştir/böl/döndür/küçült/
kilitle, OCR, görsel küçült, medya kırp). GTK'siz; motorla aynı güvenlik kurallarını
(ezme yok, iş klasörü, iptal, zaman aşımı) kullanır.
"""

from __future__ import annotations

import functools
import glob
import os
import re
import shutil
from typing import Optional

import filenor_motor as M
import filenor_sistem as S
from filenor_dil import FilenorHata
from filenor_motor import Oturum, Secenek, calistir, tur, uzanti

# id -> tanım. UI bu tablodan Araçlar sayfasını kurar.
ARACLAR: dict[str, dict] = {
    "pdf_birlestir": {
        "ad": {"tr": "PDF birleştir", "en": "Merge PDFs"},
        "ac": {"tr": "PDF ve görselleri sırayla tek PDF'te toplar", "en": "Combine PDFs and images into one PDF"},
        "girdi": {"pdf", "gorsel", "ham"}, "min": 2, "sec": [], "gerekli": ["qpdf", "pillow"], "cikti": "pdf",
    },
    "pdf_bol": {
        "ad": {"tr": "PDF böl", "en": "Split PDF"},
        "ac": {"tr": "PDF'i her N sayfada bir ayrı dosyaya böler", "en": "Split a PDF every N pages"},
        "girdi": {"pdf"}, "min": 1, "sec": ["parca", "parola"], "gerekli": ["qpdf"], "cikti": "pdf",
    },
    "pdf_sayfa_sec": {
        "ad": {"tr": "Sayfa seç / sırala", "en": "Extract pages"},
        "ac": {"tr": "1-3,5,8- gibi aralıktaki sayfalardan yeni PDF yapar", "en": "Make a new PDF from pages like 1-3,5,8-"},
        "girdi": {"pdf"}, "min": 1, "sec": ["sayfa_araligi", "parola"], "gerekli": ["qpdf"], "cikti": "pdf",
    },
    "pdf_dondur": {
        "ad": {"tr": "PDF döndür", "en": "Rotate PDF"},
        "ac": {"tr": "Tüm sayfaları ya da seçili aralığı 90/180/270° çevirir", "en": "Rotate all or some pages by 90/180/270°"},
        "girdi": {"pdf"}, "min": 1, "sec": ["derece", "sayfa_araligi", "parola"], "gerekli": ["qpdf"], "cikti": "pdf",
    },
    "pdf_kucult": {
        "ad": {"tr": "PDF küçült", "en": "Shrink PDF"},
        "ac": {"tr": "Dosya boyutunu azaltır (Ghostscript varsa görselleri de sıkıştırır)", "en": "Reduce file size (also recompresses images if Ghostscript exists)"},
        "girdi": {"pdf"}, "min": 1, "sec": ["kalite", "parola"], "gerekli": ["qpdf"], "cikti": "pdf",
    },
    "pdf_kilit_ac": {
        "ad": {"tr": "PDF parolasını kaldır", "en": "Remove PDF password"},
        "ac": {"tr": "Parolayı bildiğiniz PDF'in korumasız kopyasını yapar", "en": "Make an unprotected copy of a PDF whose password you know"},
        "girdi": {"pdf"}, "min": 1, "sec": ["parola"], "gerekli": ["qpdf"], "cikti": "pdf",
    },
    "pdf_kilitle": {
        "ad": {"tr": "PDF'e parola koy", "en": "Password-protect PDF"},
        "ac": {"tr": "256 bit AES ile açma parolası ekler", "en": "Add an open password using 256-bit AES"},
        "girdi": {"pdf"}, "min": 1, "sec": ["yeni_parola", "parola"], "gerekli": ["qpdf"], "cikti": "pdf",
    },
    "ocr": {
        "ad": {"tr": "OCR (yazıya çevir)", "en": "OCR (recognize text)"},
        "ac": {"tr": "Taranmış PDF/görselden metin ya da aranabilir PDF üretir", "en": "Extract text or a searchable PDF from scans"},
        "girdi": {"pdf", "gorsel", "ham"}, "min": 1, "sec": ["ocr_dil", "ocr_cikti", "dpi", "sayfa_araligi", "parola"],
        "gerekli": ["tesseract", "pillow"], "cikti": "txt",
    },
    "gorsel_kucult": {
        "ad": {"tr": "Görsel küçült / temizle", "en": "Optimize image"},
        "ac": {"tr": "Aynı biçimde kaliteyi/boyutu düşürür, istenirse EXIF-GPS'i siler", "en": "Same format, lower quality/size, optionally strip EXIF/GPS"},
        "girdi": {"gorsel"}, "min": 1, "sec": ["kalite", "max_kenar", "meta_temizle"], "gerekli": ["pillow"], "cikti": "",
    },
    "medya_kirp": {
        "ad": {"tr": "Ses/video kırp", "en": "Trim audio/video"},
        "ac": {"tr": "Başlangıç–bitiş saniyeleri arasını keser", "en": "Cut between start and end seconds"},
        "girdi": {"video", "ses"}, "min": 1, "sec": ["baslangic", "bitis", "kalite"], "gerekli": ["ffmpeg", "ffprobe"], "cikti": "",
    },
}


def arac_kullanilabilir(ad: str) -> list[str]:
    """Eksik bağımlılıkların listesi (boşsa kullanılabilir)."""
    d = M.araclar_durumu()
    ek = []
    for g in ARACLAR[ad]["gerekli"]:
        if not any(d.get(x, False) for x in g.split("|")):
            ek.append(g.split("|")[-1])
    if ad == "ocr" and "tesseract" not in ek:
        pass
    return ek


def arac_girdi_uygun(ad: str, yol: str) -> bool:
    return tur(uzanti(yol)) in ARACLAR[ad]["girdi"]


def arac_calistir(ad: str, dosyalar: list[str], cikti_dizin: str, sec: Optional[Secenek] = None,
                  oturum: Optional[Oturum] = None) -> list[str]:
    if ad not in ARACLAR:
        raise FilenorHata("desteklenmiyor", kaynak=ad, hedef="?")
    tanim = ARACLAR[ad]
    sec = sec or Secenek()
    dosyalar = [M.girdi_denetle(d) for d in dosyalar]
    if len(dosyalar) < tanim["min"]:
        raise FilenorHata("en_az_bir", n=tanim["min"])
    for d in dosyalar:
        if not arac_girdi_uygun(ad, d):
            raise FilenorHata("desteklenmiyor", kaynak=uzanti(d) or "?", hedef=ad)
    ek = arac_kullanilabilir(ad)
    if ek:
        raise FilenorHata("arac_eksik", arac=ek[0])
    cikti_dizin = M.cikti_dizini_hazirla(cikti_dizin)
    kendi = oturum is None
    o = oturum or Oturum()
    try:
        ilk = dosyalar[0]
        ext = uzanti(ilk)
        if ad == "gorsel_kucult":
            sonuc = []
            for d in dosyalar:
                e = uzanti(d)
                hedef = e if e in ("jpg", "png", "webp", "avif", "tiff", "bmp") else "png" if e != "gif" else "gif"
                sonuc += M._is_calistir(o, d, e, hedef, cikti_dizin, sec, _e_gorsel_kucult)
            return sonuc
        if ad == "medya_kirp":
            sonuc = []
            for d in dosyalar:
                e = uzanti(d)
                if sec.bitis <= 0 and sec.baslangic <= 0 or (sec.bitis > 0 and sec.bitis <= sec.baslangic):
                    raise FilenorHata("kirp_gecersiz")
                hedef = e if (e in M.VIDEO_YAZ or e in M.SES_YAZ) else ("mp4" if tur(e) == "video" else "mp3")
                sonuc += M._is_calistir(o, d, e, hedef, cikti_dizin, sec, M._e_medya)
            return sonuc
        if ad in ("pdf_birlestir",):
            return M._is_calistir(o, ilk, ext, "pdf", cikti_dizin, sec,
                                  functools.partial(_e_birlestir, dosyalar), stem="birlesik")
        if ad == "ocr":
            sonuc = []
            for d in dosyalar:
                cikis = "pdf" if sec.ocr_cikti == "pdf" else "txt"
                sonuc += M._is_calistir(o, d, uzanti(d), cikis, cikti_dizin, sec, _e_ocr)
            return sonuc
        motor = {"pdf_bol": _e_bol, "pdf_sayfa_sec": _e_sec, "pdf_dondur": _e_dondur, "pdf_kucult": _e_kucult,
                 "pdf_kilit_ac": _e_kilit_ac, "pdf_kilitle": _e_kilitle}[ad]
        sonuc = []
        for d in dosyalar:
            sonuc += M._is_calistir(o, d, uzanti(d), "pdf", cikti_dizin, sec, motor)
        return sonuc
    finally:
        if kendi:
            o.kapat()


# ---------------------------------------------------------------------------
def _pdf_hazir(o: Oturum, kaynak: str, isd: str, sec: Secenek) -> str:
    return M.pdf_hazirla(o, kaynak, isd, sec.parola)


def _qpdf(o: Oturum, kom: list[str]) -> None:
    # qpdf 3 = uyarılarla başarı
    calistir(o, ["qpdf"] + kom, "qpdf", kabul=(0, 3))


def _e_birlestir(dosyalar: list[str], o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek):
    parcalar: list[str] = []
    for i, d in enumerate(dosyalar):
        o.kontrol_iptal()
        t = tur(uzanti(d))
        if t == "pdf":
            try:
                M.pdf_bilgi(o, d)
            except FilenorHata as h:
                if h.kod == "sifreli_pdf":
                    raise FilenorHata("sifreli_pdf")
                raise
            parcalar.append(d)
        else:
            gecici = os.path.join(isd, f"g{i:03d}.pdf")
            img = M._gorsel_ac(o, d, uzanti(d))
            from PIL import ImageOps
            try:
                if img.getexif().get(0x0112, 1) not in (None, 1):
                    img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            M._duz_rgb(img).save(gecici, "PDF", resolution=150.0)
            parcalar.append(gecici)
        o.ilerle(80.0 * (i + 1) / len(dosyalar), "")
    cikti = os.path.join(isd, "cikti.pdf")
    _qpdf(o, ["--empty", "--pages"] + parcalar + ["--", cikti])
    return [cikti], ""


def _e_bol(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek):
    pdf = _pdf_hazir(o, kaynak, isd, sec)
    n = M.pdf_bilgi(o, pdf)["sayfa"]
    k = max(1, int(sec.parca))
    onek = os.path.join(isd, "b.pdf")
    _qpdf(o, [f"--split-pages={k}", pdf, onek])
    ham = sorted(glob.glob(os.path.join(isd, "b-*.pdf")))
    hane = max(3, len(str(n)))
    cikti = []
    for i, p in enumerate(ham):
        ilk = i * k + 1
        son = min(n, ilk + k - 1)
        ad = f"s{ilk:0{hane}d}.pdf" if ilk == son else f"s{ilk:0{hane}d}-{son:0{hane}d}.pdf"
        yeni = os.path.join(isd, ad)
        os.replace(p, yeni)
        cikti.append(yeni)
    return cikti, "_parcalar"


def _e_sec(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek):
    pdf = _pdf_hazir(o, kaynak, isd, sec)
    n = M.pdf_bilgi(o, pdf)["sayfa"]
    liste = M.sayfa_listesi(sec.sayfa_araligi, n)
    cikti = os.path.join(isd, "cikti.pdf")
    _qpdf(o, [pdf, "--pages", ".", M._qpdf_aralik(liste), "--", cikti])
    return [cikti], ""


def _e_dondur(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek):
    pdf = _pdf_hazir(o, kaynak, isd, sec)
    n = M.pdf_bilgi(o, pdf)["sayfa"]
    d = int(sec.derece) % 360
    if d not in (90, 180, 270):
        raise FilenorHata("sayfa_araligi", aralik=f"{sec.derece}°")
    kapsam = "" if not sec.sayfa_araligi.strip() else ":" + M._qpdf_aralik(M.sayfa_listesi(sec.sayfa_araligi, n))
    cikti = os.path.join(isd, "cikti.pdf")
    _qpdf(o, [f"--rotate=+{d}{kapsam}", pdf, cikti])
    return [cikti], ""


def _e_kucult(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek):
    pdf = _pdf_hazir(o, kaynak, isd, sec)
    cikti = os.path.join(isd, "cikti.pdf")
    d = M.araclar_durumu()
    if d["gs"] and sec.kalite != "yuksek":
        ayar = {"dengeli": "/ebook", "kucuk": "/screen"}[sec.kalite]
        ara = os.path.join(isd, "gs.pdf")
        calistir(o, ["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5", f"-dPDFSETTINGS={ayar}", "-dNOPAUSE",
                     "-dQUIET", "-dBATCH", f"-sOutputFile={ara}", pdf], "gs")
        pdf = ara
    _qpdf(o, ["--object-streams=generate", "--recompress-flate", "--compression-level=9",
              "--remove-unreferenced-resources=yes", pdf, cikti])
    # Büyüdüyse özgününü ver
    if os.path.getsize(cikti) >= os.path.getsize(kaynak):
        shutil.copyfile(kaynak, cikti)
    return [cikti], ""


def _e_kilit_ac(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek):
    if not sec.parola:
        # Parolasız açılabilen (yalnız sahip kısıtlı) PDF'i de temizleyebilir
        pass
    cikti = os.path.join(isd, "cikti.pdf")
    kom = ["--decrypt"] + ([f"--password={sec.parola}"] if sec.parola else []) + [kaynak, cikti]
    try:
        _qpdf(o, kom)
    except FilenorHata as h:
        if h.kod == "arac_hata" and "password" in str(h.ayrinti.get("ayrinti", "")).lower():
            raise FilenorHata("sifreli_pdf")
        raise
    return [cikti], ""


def _e_kilitle(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek):
    if not sec.yeni_parola:
        raise FilenorHata("sifreli_pdf")
    pdf = _pdf_hazir(o, kaynak, isd, sec)
    cikti = os.path.join(isd, "cikti.pdf")
    _qpdf(o, ["--encrypt", sec.yeni_parola, sec.yeni_parola, "256", "--", pdf, cikti])
    return [cikti], ""


# --------------------------- görsel / OCR ------------------------------------
def _e_gorsel_kucult(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek):
    orijinal = M._gorsel_ac(o, kaynak, ext)
    try:
        return _e_gorsel_kucult_ic(o, orijinal, kaynak, hedef, isd, sec)
    finally:
        try:
            orijinal.close()
        except Exception:
            pass


def _e_gorsel_kucult_ic(o: Oturum, img, kaynak: str, hedef: str, isd: str, sec: Secenek):
    from PIL import ImageOps
    exif = icc = None
    try:
        ex = img.getexif()
        icc = img.info.get("icc_profile")
        if ex.get(0x0112, 1) not in (None, 1) and getattr(img, "n_frames", 1) <= 1:
            img = ImageOps.exif_transpose(img)
            ex = img.getexif()
        if len(ex):
            exif = ex.tobytes()
        if img.mode == "CMYK":
            icc = None
    except Exception:
        pass
    cikti = os.path.join(isd, "cikti." + hedef)
    try:
        M.gorsel_isle(img, hedef, cikti, sec, hepsi=True, korunacak_exif=exif, icc=icc)
    except (OSError, ValueError, KeyError) as e:
        raise FilenorHata("arac_hata", arac="Pillow", ayrinti=str(e)[:200])
    # Yalnız kalite düşürme istendiyse ve büyüdüyse özgünü koru (meta silme/boyut değişimi hariç)
    if not sec.meta_temizle and sec.max_kenar <= 0 and os.path.getsize(cikti) >= os.path.getsize(kaynak):
        shutil.copyfile(kaynak, cikti)
    return [cikti], ""


@functools.lru_cache(maxsize=1)
def ocr_dilleri() -> tuple:
    import subprocess
    try:
        p = subprocess.run([S.coz("tesseract"), "--list-langs"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30, **S.popen_ayarlari())
        return tuple(s.strip() for s in p.stdout.splitlines()[1:] if s.strip() and s.strip() != "osd")
    except Exception:
        return ()


def _ocr_dilleri_coz(istek: str) -> str:
    kurulu = set(ocr_dilleri())
    secilen = [x for x in re.split(r"[+,\s]+", istek or "") if x]
    var = [x for x in secilen if x in kurulu]
    if not var:
        if not kurulu:
            raise FilenorHata("arac_eksik", arac="tesseract")
        raise FilenorHata("ocr_dil", diller=", ".join(sorted(kurulu)))
    return "+".join(var)


def _e_ocr(o: Oturum, kaynak: str, ext: str, hedef: str, isd: str, sec: Secenek):
    dil = _ocr_dilleri_coz(sec.ocr_dil)
    t = tur(ext)
    sayfa_png: list[str] = []
    if t == "pdf":
        if not M.araclar_durumu()["pdftoppm"]:
            raise FilenorHata("arac_eksik", arac="pdftoppm")
        s2 = Secenek.sozlukten(sec.sozluk())
        s2.dpi = max(150, min(400, sec.dpi))
        dosyalar, _ = M._pdf_sayfalari_gorsele(o, kaynak, "png", isd, s2)
        sayfa_png = dosyalar
    else:
        img = M._gorsel_ac(o, kaynak, ext)
        from PIL import ImageOps
        try:
            if img.getexif().get(0x0112, 1) not in (None, 1):
                img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        p = os.path.join(isd, "tek.png")
        M._duz_rgb(img).save(p, "PNG")
        sayfa_png = [p]
    metinler: list[str] = []
    pdfler: list[str] = []
    for i, png in enumerate(sayfa_png):
        o.kontrol_iptal()
        taban = os.path.join(isd, f"o{i:04d}")
        if hedef == "pdf":
            calistir(o, ["tesseract", png, taban, "-l", dil, "pdf"], "tesseract")
            pdfler.append(taban + ".pdf")
        else:
            calistir(o, ["tesseract", png, taban, "-l", dil], "tesseract")
            with open(taban + ".txt", "r", encoding="utf-8", errors="replace") as f:
                metinler.append(f.read().strip())
        o.ilerle(10 + 85.0 * (i + 1) / len(sayfa_png), "")
    if hedef == "pdf":
        cikti = os.path.join(isd, "cikti.pdf")
        if len(pdfler) == 1:
            os.replace(pdfler[0], cikti)
        else:
            _qpdf(o, ["--empty", "--pages"] + pdfler + ["--", cikti])
        return [cikti], ""
    cikti = os.path.join(isd, "cikti.txt")
    with open(cikti, "w", encoding="utf-8") as f:
        f.write("\n\f\n".join(metinler).strip() + "\n")
    if not "".join(metinler).strip():
        raise FilenorHata("metin_yok")
    return [cikti], ""


class AracKosucu(M.Kosucu):
    """Kosucu ile ayni, ama donusum yerine bir arac calistirir. Is.hedef = arac kimligi;
    Is.dosyalar doluysa (birlestir) hepsi tek cagrida islenir."""

    def _calistir_is(self, o: Oturum, is_: "M.Is", hedef_dizin: str) -> list[str]:
        return arac_calistir(is_.hedef, is_.dosyalar or [is_.kaynak], hedef_dizin, self.secenek, o)
