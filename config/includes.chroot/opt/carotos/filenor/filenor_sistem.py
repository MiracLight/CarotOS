# -*- coding: utf-8 -*-
"""
Filenor -- isletim sistemi katmani (Linux / Windows / macOS). GTK'siz.

Motorun isletim sistemine bagli her sey burada toplanir:
  * ayar klasoru, onbellek klasoru
  * harici arac bulma (PATH + Windows'ta bilinen kurulum yerleri + paketle gelen araclar)
  * surec baslatma ve oldurme (Linux: surec grubu; Windows: surec agaci)
  * dosya/klasor acma
  * sistem dili
  * yazi tipi adaylari (txt -> pdf)

Diger modullerde 'os.name' ya da platform denetimi yapilmaz; hepsi buraya sorulur.
"""

from __future__ import annotations

import glob
import os
import shutil
import signal
import subprocess
import sys
import time
from typing import Optional

WINDOWS = os.name == "nt"
MACOS = sys.platform == "darwin"
DONMUS = bool(getattr(sys, "frozen", False))        # PyInstaller vb. ile paketlenmis mi

# Windows'ta arac adlarinin alternatifleri (ilk bulunan kullanilir)
ARAC_ADLARI = {
    "gs": ("gs", "gswin64c", "gswin32c"),
    "soffice": ("soffice", "libreoffice"),
}


# ---------------------------------------------------------------------------
# Klasorler
# ---------------------------------------------------------------------------
def uygulama_dizini() -> str:
    """Kodun bulundugu klasor (paketlenmisse paketin acildigi klasor)."""
    if DONMUS:
        return getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def ayar_dizini() -> str:
    """Kullanici ayar klasoru. FILENOR_AYAR_DIZINI ile degistirilebilir (test, tasinabilir kurulum)."""
    ozel = os.environ.get("FILENOR_AYAR_DIZINI")
    if ozel:
        return ozel
    if WINDOWS:
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Filenor")
    kok = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    yeni = os.path.join(kok, "filenor")
    eski = os.path.join(kok, "carotos")             # CarotOS: ayarlar buradaydi
    if not os.path.exists(os.path.join(yeni, "filenor.json")) and os.path.exists(os.path.join(eski, "filenor.json")):
        return eski
    return yeni


def onbellek_dizini() -> str:
    if WINDOWS:
        return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Filenor", "onbellek")
    kok = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(kok, "filenor")


# ---------------------------------------------------------------------------
# Harici araclar
# ---------------------------------------------------------------------------
def _pf_dizinleri() -> list[str]:
    return [d for d in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                        os.environ.get("ProgramW6432")) if d]


def _win_arac_dizinleri() -> list[str]:
    """Windows'ta arac klasorleri: paketle gelenler, winget baglantilari, bilinen kurulum yerleri."""
    uyg = uygulama_dizini()
    yerel = os.environ.get("LOCALAPPDATA") or ""
    adaylar: list[str] = [os.path.join(uyg, "araclar"), os.path.join(uyg, "araclar", "bin"),
                          os.path.join(os.path.dirname(uyg), "araclar")]
    if yerel:
        wg = os.path.join(yerel, "Microsoft", "WinGet")
        adaylar.append(os.path.join(wg, "Links"))
        # tasinabilir winget paketleri (ffmpeg, poppler ...) kendi klasorlerine acilir
        for kalip in ("Packages/*/*/bin", "Packages/*/*", "Packages/*/*/Library/bin",
                      "Packages/*/*/*/bin", "Packages/*/*/*/Library/bin"):
            adaylar += sorted(glob.glob(os.path.join(wg, *kalip.split("/"))))
    for pf in _pf_dizinleri():
        for kalip in ("LibreOffice/program", "Tesseract-OCR", "qpdf*/bin", "gs/gs*/bin",
                      "poppler*/Library/bin", "poppler*/bin", "FFmpeg*/bin", "ffmpeg*/bin"):
            adaylar += sorted(glob.glob(os.path.join(pf, *kalip.split("/"))))
    for kalip in ("C:/ProgramData/chocolatey/bin", "C:/tools/*/bin", "C:/ffmpeg/bin"):
        adaylar += sorted(glob.glob(kalip))
    ek = os.environ.get("FILENOR_ARAC_DIZINLERI")        # ';' ile ayrilmis ek klasorler
    if ek:
        adaylar = [d for d in ek.split(os.pathsep) if d] + adaylar
    gorulen: set = set()
    sonuc = []
    for d in adaylar:
        if d and os.path.isdir(d) and d not in gorulen:
            gorulen.add(d)
            sonuc.append(d)
    return sonuc


def ortam_hazirla() -> None:
    """Kurulu ama PATH'te olmayan araclarin klasorlerini bu surecin PATH'ine ekler.
    Yeni arac kurulduktan sonra yeniden cagrilir (calisan program PATH degisikligini gormez)."""
    if not WINDOWS:
        ek = os.environ.get("FILENOR_ARAC_DIZINLERI")
        yeni = [d for d in (ek or "").split(os.pathsep) if d and os.path.isdir(d)]
    else:
        yeni = _win_arac_dizinleri()
    mevcut = os.environ.get("PATH", "").split(os.pathsep)
    eklenecek = [d for d in yeni if d not in mevcut]
    if eklenecek:
        os.environ["PATH"] = os.pathsep.join(mevcut + eklenecek)
    if WINDOWS:
        _win_yol_registry()


def _win_yol_registry() -> None:
    """Winget/kurucular PATH'i kayit defterine yazar; calisan surec bunu gormez. Buradan okuyup ekler."""
    try:
        import winreg
    except ImportError:
        return
    parcalar: list[str] = []
    for kok, anahtar in ((winreg.HKEY_CURRENT_USER, "Environment"),
                         (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
        try:
            with winreg.OpenKey(kok, anahtar) as k:
                deger, _tur = winreg.QueryValueEx(k, "Path")
                parcalar += [os.path.expandvars(p) for p in str(deger).split(";") if p]
        except OSError:
            continue
    mevcut = os.environ.get("PATH", "").split(os.pathsep)
    yeni = [p for p in parcalar if p not in mevcut and os.path.isdir(p)]
    if yeni:
        os.environ["PATH"] = os.pathsep.join(mevcut + yeni)


def arac_yolu(ad: str) -> Optional[str]:
    """Aracin tam yolu; yoksa None. 'gs' gibi adlarin Windows karsiliklarini da dener."""
    for a in ARAC_ADLARI.get(ad, (ad,)):
        yol = shutil.which(a)
        if yol:
            return yol
    return None


def coz(ad: str) -> str:
    """Komut adini tam yola cevirir (bulunamazsa ad aynen doner; cagiran FileNotFoundError'u yakalar)."""
    return arac_yolu(ad) or ad


# ---------------------------------------------------------------------------
# Surecler
# ---------------------------------------------------------------------------
def popen_ayarlari() -> dict:
    """subprocess.Popen/run icin: kendi surec grubunda, Windows'ta konsol penceresi acmadan."""
    if WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}


def oldur(proc: subprocess.Popen) -> None:
    """Sureci ve alt-sureclerini sonlandirir: once nazikce, 2 sn sonra zorla."""
    if WINDOWS:
        _win_oldur(proc)
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    for _ in range(20):
        if proc.poll() is not None:
            return
        time.sleep(0.1)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _win_oldur(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        # /T: alt surecler (ffmpeg, soffice.bin ...) de gider; /F: zorla
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        proc.kill()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Dosya acma, dil, yazi tipleri
# ---------------------------------------------------------------------------
def ac(yol: str) -> None:
    """Dosya ya da klasoru varsayilan uygulamayla acar; arayuzu bekletmez."""
    try:
        if WINDOWS:
            os.startfile(yol)  # type: ignore[attr-defined]  # noqa: S606
        elif MACOS:
            subprocess.Popen(["open", yol], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        else:
            subprocess.Popen(["xdg-open", yol], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def sistem_dili() -> str:
    """'tr' ya da 'en' (baska her sey 'en')."""
    for d in ("FILENOR_DIL", "LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(d, "").strip()
        if v and v not in ("C", "POSIX"):
            return "tr" if v.lower().startswith("tr") else "en"
    if WINDOWS:
        try:
            import ctypes
            tampon = ctypes.create_unicode_buffer(85)
            if ctypes.windll.kernel32.GetUserDefaultLocaleName(tampon, 85):  # type: ignore[attr-defined]
                return "tr" if tampon.value.lower().startswith("tr") else "en"
        except Exception:
            pass
    return "en"


def sabit_genislikli_yazi_tipleri() -> list[str]:
    """txt -> pdf icin Turkce karakterleri tasiyan sabit genislikli TTF adaylari."""
    uyg = uygulama_dizini()
    adaylar = [os.path.join(uyg, "yazi", "DejaVuSansMono.ttf")]
    if WINDOWS:
        win = os.environ.get("WINDIR") or r"C:\Windows"
        adaylar += [os.path.join(win, "Fonts", ad) for ad in ("consola.ttf", "lucon.ttf", "cour.ttf")]
        adaylar += ["C:/msys64/mingw64/share/fonts/TTF/DejaVuSansMono.ttf"]
    else:
        adaylar += ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
                    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
                    "/Library/Fonts/Courier New.ttf"]
    return adaylar


def libreoffice_adaylari() -> list[str]:
    """LibreOffice 'soffice' icin PATH disindaki olasi yollar."""
    if WINDOWS:
        sonuc: list[str] = []
        for pf in _pf_dizinleri():
            sonuc += sorted(glob.glob(os.path.join(pf, "LibreOffice*", "program", "soffice.exe")))
        return sonuc
    if MACOS:
        return ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]
    sonuc = []
    for kalip in ("/opt/libreoffice*/program/soffice", "/usr/lib/libreoffice/program/soffice",
                  "/opt/LibreOffice*/program/soffice"):
        sonuc += sorted(glob.glob(kalip))
    return sonuc
