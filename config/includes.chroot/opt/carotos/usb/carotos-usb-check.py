#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CarotOS USB Denetimi

Takilan cikarilabilir aygitlari algilar ve hizli bir guvenlik kontrolu yapar.
Otomatik kontrol dosya ICERIKLERINI OKUMAZ — yalnizca dosya adlarina,
uzantilarina, izinlerine ve konumlarina bakar. Bu yuzden buyuk bir bellekte
bile saniyeler surer.

Ayrintili tarama (ClamAV) icerigi okur ve YALNIZCA kullanici pencereden
baslattiginda calisir (karar D7). Ortak tarama motoru kullanilir (karar D2);
bulunan dosyalara dokunulmaz, yalnizca raporlanir.

Kullanim:
    carotos-usb-check --monitor     Arka planda izler (oturum acilisinda)
    carotos-usb-check --scan YOL    Verilen yolu denetler
    carotos-usb-check               Bagli tum cikarilabilir aygitlari denetler
"""

import json
import os
import re
import subprocess
import sys
import threading
import time

APP_VERSION = "1.1"

# Tarama sinirlari — cok buyuk aygitlarda takilmamak icin
MAX_FILES = 60000
MAX_SECONDS = 8.0
MAX_DEPTH = 6
COOLDOWN_SECONDS = 15
MONITOR_POLL_SECONDS = 1   # baglama tablosu bu araliklarla yoklanir

# Bulgu onem dereceleri
HIGH = "high"
MEDIUM = "medium"
LOW = "low"

# Windows'ta calisabilen dosya turleri
EXEC_EXT = {
    ".exe", ".scr", ".com", ".pif", ".bat", ".cmd", ".vbs", ".vbe",
    ".js", ".jse", ".wsf", ".wsh", ".ps1", ".jar", ".msi", ".hta",
    ".cpl", ".reg",
}

# Zararsiz gorunup calistirilabilir olan ikinci uzanti tuzagi icin
DOC_EXT = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".mp3", ".mp4", ".avi",
    ".mkv", ".zip", ".rar", ".csv", ".odt", ".ods", ".rtf",
}

MOUNT_PREFIXES = ("/media/", "/run/media/", "/mnt/")
OPTICAL_FS = {"iso9660", "udf"}
SKIP_FS = {"squashfs", "tmpfs", "devtmpfs", "proc", "sysfs", "overlay",
           "cgroup", "cgroup2", "efivarfs", "fuse.gvfsd-fuse"}

# Sistemin kendi olusturdugu, supheli olmayan adlar
BENIGN_NAMES = {
    "system volume information", "$recycle.bin", "recycler",
    ".trash-1000", "found.000", ".spotlight-v100", ".fseventsd",
    ".trashes", "lost+found", ".temporaryitems", ".documentrevisions-v100",
}

# Sag-sola yazim / gorunmez yon isaretleri (uzanti gizlemede kullanilir)
BIDI_CHARS = ("\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
              "\u200e", "\u200f", "\u061c", "\u2066", "\u2067",
              "\u2068", "\u2069")


# ---------------------------------------------------------------------------
# Sistem yardimcilari
# ---------------------------------------------------------------------------

def read_file(path, limit=200000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def block_sys_path(device):
    """Aygitin /sys altindaki gercek yolunu bulur.

    /dev/sdb1 -> /sys/.../block/sdb/sdb1
    Bolumler icin ust aygita (diskin kendisine) cikilir, cunku
    'removable' bayragi orada durur. mmcblk0p1 gibi adlar da dogru
    cozulur — duz metin kesme yontemi bunlarda hatali sonuc verir.
    """
    if not device or not device.startswith("/dev/"):
        return None
    name = os.path.basename(device)
    link = f"/sys/class/block/{name}"
    if not os.path.exists(link):
        return None
    real = os.path.realpath(link)

    # Once kendisi tam disk mi diye bak
    if os.path.exists(os.path.join(real, "removable")):
        return real
    # Degilse ust dizin (disk) olmali
    parent = os.path.dirname(real)
    if os.path.exists(os.path.join(parent, "removable")):
        return parent
    return None


def is_removable(device):
    """Aygit cikarilabilir mi?

    Iki olcut kullanilir: cekirdegin 'removable' bayragi ve aygitin USB
    yoluna bagli olup olmadigi. Harici USB diskler cogu zaman removable=0
    bildirir; yalnizca bayraga bakmak onlari kacirir.
    """
    sys_path = block_sys_path(device)
    if not sys_path:
        return False
    if read_file(os.path.join(sys_path, "removable")).strip() == "1":
        return True
    return "/usb" in sys_path


def device_uuid(device):
    """Aygitin benzersiz kimligi — ayni bellegi tekrar taramamak icin."""
    for folder in ("/dev/disk/by-uuid", "/dev/disk/by-partuuid"):
        if not os.path.isdir(folder):
            continue
        try:
            target = os.path.realpath(device)
            for name in os.listdir(folder):
                if os.path.realpath(os.path.join(folder, name)) == target:
                    return name
        except OSError:
            continue
    return device


def mount_entries():
    """/proc/mounts icerigini cozumler."""
    entries = []
    for line in read_file("/proc/mounts").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        entries.append({
            "device": parts[0],
            "mount": parts[1].replace("\\040", " "),
            "fstype": parts[2],
        })
    return entries


def is_live_medium(mount_point):
    """CarotOS canli moddayken kendi kurulum ortamini taramasin."""
    for marker in ("live/filesystem.squashfs", "live/vmlinuz", ".disk/info"):
        if os.path.exists(os.path.join(mount_point, marker)):
            return True
    return False


def removable_mounts():
    """Taranmasi anlamli, bagli cikarilabilir aygitlar."""
    found = []
    for entry in mount_entries():
        if entry["fstype"] in SKIP_FS or entry["fstype"] in OPTICAL_FS:
            continue
        if not entry["mount"].startswith(MOUNT_PREFIXES):
            continue
        if not is_removable(entry["device"]):
            continue
        if is_live_medium(entry["mount"]):
            continue
        found.append(entry)
    return found


def entry_for_mount(mount_point):
    for entry in mount_entries():
        if entry["mount"] == mount_point:
            return entry
    return None


def volume_label(mount_point):
    return os.path.basename(mount_point.rstrip("/")) or mount_point


def human_size(num):
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


# ---------------------------------------------------------------------------
# Sezgisel denetim yardimcilari
# ---------------------------------------------------------------------------

def is_windows_hidden(path):
    """Windows'un 'gizli' dosya ozniteligini okumaya calisir.

    ONEMLI: USB solucanlari klasorleri Linux'taki gibi basina nokta koyarak
    degil, Windows'un gizli ozniteligiyle saklar. NTFS'te bu oznitelik
    genisletilmis oznitelik olarak okunabilir. FAT32'de okunamaz; orada
    tespit, karsiligi olmayan kisayol dosyalarina dayanir.
    """
    for attr in ("system.ntfs_attrib_be", "system.ntfs_attrib"):
        try:
            raw = os.getxattr(path, attr)
        except (OSError, AttributeError):
            continue
        try:
            order = "big" if attr.endswith("_be") else "little"
            return bool(int.from_bytes(raw, order) & 0x2)
        except (ValueError, TypeError):
            continue
    return False


def has_bidi_trick(name):
    """Adi ekranda farkli gostermek icin kullanilan yon isaretleri."""
    return any(ch in name for ch in BIDI_CHARS)


def split_extensions(name):
    """Dosya adindaki son iki uzantiyi dondurur."""
    lowered = name.lower()
    parts = lowered.rsplit(".", 2)
    if len(parts) == 3:
        return "." + parts[1], "." + parts[2]
    if len(parts) == 2:
        return None, "." + parts[1]
    return None, None


# ---------------------------------------------------------------------------
# Denetim
# ---------------------------------------------------------------------------

def metin(deger, lang):
    """Bulgu metni iki dilli sozluk ya da (eski kayitlarda) duz metindir."""
    if isinstance(deger, dict):
        return deger.get(lang) or deger.get("tr") or ""
    return deger or ""


def scan_path(root, cancel=None):
    """Verilen dizini denetler. Dosya iceriklerini OKUMAZ.

    cancel: set() edilirse tarama erken biter (threading.Event).
    Dondurur: {"findings": [...], "stats": {...}}
    """
    findings = []
    started = time.time()
    file_count = 0
    dir_count = 0
    total_size = 0
    truncated = False
    cancelled = False

    exec_in_root = []
    lnk_files = []
    hidden_dirs = []
    visible_dirs = set()
    unreadable = []

    def on_error(err):
        unreadable.append(getattr(err, "filename", str(err)))

    def add(level, kind, title, detail, path):
        findings.append({"level": level, "kind": kind, "title": title,
                         "detail": detail, "path": path})

    for current, dirs, files in os.walk(root, followlinks=False,
                                        onerror=on_error):
        if cancel is not None and cancel.is_set():
            cancelled = True
            break
        if time.time() - started > MAX_SECONDS or file_count > MAX_FILES:
            truncated = True
            break

        depth = current[len(root):].count(os.sep)
        at_root = os.path.abspath(current) == os.path.abspath(root)
        if depth >= MAX_DEPTH:
            dirs[:] = []

        for name in list(dirs):
            dir_count += 1
            lowered = name.lower()
            if lowered in BENIGN_NAMES:
                dirs.remove(name)
                continue
            full_dir = os.path.join(current, name)
            if at_root:
                if name.startswith(".") or is_windows_hidden(full_dir):
                    hidden_dirs.append(name)
                else:
                    visible_dirs.add(lowered)
            if has_bidi_trick(name):
                add(HIGH, "bidi",
                    {"tr": "Adı gizlenmiş klasör", "en": "Folder with a disguised name"},
                    {"tr": "Klasör adında, adı ekranda farklı göstermek için "
                           "kullanılan görünmez bir karakter var.",
                     "en": "The folder name contains an invisible character "
                           "used to make the name look different on screen."},
                    full_dir)

        for name in files:
            file_count += 1
            if file_count > MAX_FILES:
                truncated = True
                break

            full = os.path.join(current, name)
            lowered = name.lower()

            try:
                total_size += os.path.getsize(full)
            except OSError:
                pass

            first_ext, last_ext = split_extensions(lowered)

            if lowered == "autorun.inf" and at_root:
                add(HIGH, "autorun",
                    {"tr": "Otomatik çalıştırma dosyası", "en": "Autorun file"},
                    {"tr": "Bu dosya, bellek takıldığında Windows'ta bir "
                           "programın kendiliğinden çalışmasını sağlamak için "
                           "kullanılır. Zararlı yazılımların en bilinen "
                           "yayılma yöntemidir.",
                     "en": "This file is used to make a program start by "
                           "itself on Windows when the device is plugged in. "
                           "It is the best-known way malware spreads."},
                    full)
                continue

            if has_bidi_trick(name):
                add(HIGH, "bidi",
                    {"tr": "Adı gizlenmiş dosya", "en": "File with a disguised name"},
                    {"tr": "Dosya adında, gerçek uzantıyı ekranda farklı "
                           "göstermek için kullanılan görünmez bir karakter "
                           "var. Belge gibi görünen dosya aslında "
                           "çalıştırılabilir olabilir.",
                     "en": "The file name contains an invisible character used "
                           "to make the real extension look different on "
                           "screen. A file that looks like a document may "
                           "actually be executable."}, full)
                continue

            if first_ext in DOC_EXT and last_ext in EXEC_EXT:
                add(HIGH, "double_ext",
                    {"tr": "Çift uzantılı dosya", "en": "Double extension"},
                    {"tr": f"Dosya adı belge gibi görünüyor ama gerçek "
                           f"uzantısı {last_ext}; yani çalıştırılabilir bir "
                           f"programdır. Kullanıcıyı yanıltmak için sık "
                           f"kullanılan bir yöntemdir.",
                     "en": f"The file name looks like a document, but its real "
                           f"extension is {last_ext}, so it is an executable "
                           f"program. This is a common way to mislead users."},
                    full)
                continue

            if last_ext == ".lnk":
                lnk_files.append((name, full))
                continue

            if last_ext in EXEC_EXT:
                if at_root:
                    exec_in_root.append((name, full))
                elif os.path.basename(current).startswith("."):
                    add(MEDIUM, "hidden_exec",
                        {"tr": "Gizli klasörde çalıştırılabilir dosya",
                         "en": "Executable file in a hidden folder"},
                        {"tr": "Gizlenmiş bir klasörün içinde "
                               "çalıştırılabilir bir dosya bulundu. Olağan bir "
                               "yerleşim değildir.",
                         "en": "An executable file was found inside a hidden "
                               "folder. This is not a usual layout."}, full)

        if truncated or cancelled:
            break

    # --- toplu degerlendirmeler -------------------------------------------

    disguised = [(n, p) for n, p in lnk_files
                 if n[:-4].lower() not in visible_dirs]

    # Karsiligi olmayan kisayoplar: gercek klasorler gizlenmis demektir.
    # FAT32'de gizli oznitelik okunamadigi icin bu tek basina yeterli
    # kanittir; gizli klasor GORULMESINI sart kosmayiz.
    if disguised and (hidden_dirs or len(disguised) >= 2):
        names = ", ".join(n for n, _ in disguised[:4])
        add(HIGH, "lnk_worm",
            {"tr": "Klasörler kısayolla değiştirilmiş olabilir",
             "en": "Folders may have been replaced by shortcuts"},
            {"tr": f"Görünür bir klasöre karşılık gelmeyen kısayol dosyaları "
                   f"bulundu ({names}). Bu, gerçek klasörleri gizleyip "
                   f"yerlerine zararlı kısayol koyan yaygın bir USB zararlısı "
                   f"davranışıdır. Kısayollara tıklamayın.",
             "en": f"Shortcut files that do not match any visible folder were "
                   f"found ({names}). This is common USB malware behaviour: "
                   f"real folders are hidden and replaced by malicious "
                   f"shortcuts. Do not click the shortcuts."},
            disguised[0][1])
    elif disguised:
        add(MEDIUM, "lnk_single",
            {"tr": f"{len(disguised)} karşılıksız kısayol dosyası",
             "en": f"{len(disguised)} unmatched shortcut files"},
            {"tr": "Bir klasöre karşılık gelmeyen kısayol dosyası bulundu. "
                   "Kısayollar tek başına zararlı değildir, ancak gizlenmiş "
                   "bir klasörün yerine geçmiş olabilirler.",
             "en": "A shortcut file that does not match any folder was found. "
                   "Shortcuts are not harmful by themselves, but they may "
                   "have replaced a hidden folder."}, disguised[0][1])

    if exec_in_root:
        names = ", ".join(n for n, _ in exec_in_root[:5])
        level = MEDIUM if len(exec_in_root) < 4 else HIGH
        add(level, "root_exec",
            {"tr": f"Ana dizinde {len(exec_in_root)} çalıştırılabilir dosya",
             "en": f"{len(exec_in_root)} executable files in the top folder"},
            {"tr": f"{names}. Bunlar Windows'ta çalışabilen programlardır. "
                   f"Kaynağını bilmediğiniz programları çalıştırmayın.",
             "en": f"{names}. These are programs that can run on Windows. Do "
                   f"not run programs whose source you do not know."},
            exec_in_root[0][1])

    if hidden_dirs and not disguised:
        add(LOW, "hidden_dirs",
            {"tr": f"{len(hidden_dirs)} gizli klasör",
             "en": f"{len(hidden_dirs)} hidden folders"},
            {"tr": "Gizli klasörler çoğu zaman normaldir (sistem dosyaları), "
                   "ancak içeriğine bakmakta fayda var.",
             "en": "Hidden folders are often normal (system files), but it is "
                   "worth looking at their contents."},
            os.path.join(root, hidden_dirs[0]))

    if unreadable:
        add(LOW, "unreadable",
            {"tr": f"{len(unreadable)} klasör okunamadı",
             "en": f"{len(unreadable)} folders could not be read"},
            {"tr": "Bazı klasörlere erişim izni olmadığı için içerikleri "
                   "denetlenemedi. Sonuç eksik olabilir.",
             "en": "Some folders could not be checked because access was "
                   "denied. The result may be incomplete."}, unreadable[0])

    order = {HIGH: 0, MEDIUM: 1, LOW: 2}
    findings.sort(key=lambda f: order.get(f["level"], 3))

    return {
        "findings": findings,
        "stats": {
            "files": file_count,
            "dirs": dir_count,
            "size": total_size,
            "seconds": round(time.time() - started, 2),
            "truncated": truncated,
            "cancelled": cancelled,
            "empty": file_count == 0 and dir_count == 0,
            "unreadable": len(unreadable),
        },
    }


def worst_level(findings):
    for level in (HIGH, MEDIUM, LOW):
        if any(f["level"] == level for f in findings):
            return level
    return None


def enrich(result, mount_point):
    """Sonuca aygit bilgilerini ekler."""
    entry = entry_for_mount(mount_point)
    result["root"] = mount_point
    result["device"] = entry["device"] if entry else None
    result["fstype"] = entry["fstype"] if entry else None
    result["label"] = volume_label(mount_point)
    return result


if __name__ == "__main__" and "--audit-json" in sys.argv:
    index = sys.argv.index("--audit-json")
    target = sys.argv[index + 1] if index + 1 < len(sys.argv) else None
    if target:
        print(json.dumps(enrich(scan_path(target), target), ensure_ascii=False))
    else:
        print(json.dumps([enrich(scan_path(e["mount"]), e["mount"])
                          for e in removable_mounts()], ensure_ascii=False))
    sys.exit(0)


# ===========================================================================
# Arayuz
# ===========================================================================
#
# BELLEK NOTU: Gtk/Gdk/Notify ice aktarmalari BILEREK burada degil,
# _gtk_araclari() icinde yapiliyor. --monitor modu cogu zaman hicbir
# pencere acmadan bekler; GLib disinda GTK'nin tamami (widget, tema,
# CSS motoru) onceden yuklenirse bosuna ~15-45 MB tutulur. Pencere
# GERCEKTEN acilacagi an GTK yuklenir, once degil.
#
# GLib ayri: monitor donguisu (GLib.MainLoop, GLib.timeout_add) icin
# gerekli ve Gtk'ye gore cok daha hafif, o yuzden ust seviyede kaliyor.

import gi  # noqa: E402
gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402

Gtk = None
Gdk = None
Notify = None
HAVE_NOTIFY = False
_notify_denendi = False
_ResultWindowClass = None


def _notify_araclari():
    """libnotify'i ilk gercek ihtiyacta yukler.

    Gtk'den BAGIMSIZ: bildirim gondermek per gorev cok daha sik olan
    yoldur (temiz aygit bildirimi, tehdit bildirimi + eylem dugmesi)
    ve pencere acmayi GEREKTIRMEZ. libnotify D-Bus uzerinden calisir,
    Gtk widget/tema motorunu ice aktarmaz — bu yuzden ayrildi.
    """
    global Notify, HAVE_NOTIFY, _notify_denendi
    if _notify_denendi:
        return HAVE_NOTIFY
    _notify_denendi = True
    try:
        gi.require_version("Notify", "0.7")
        from gi.repository import Notify as _Notify
        Notify = _Notify
        HAVE_NOTIFY = True
    except (ValueError, ImportError):
        HAVE_NOTIFY = False
    return HAVE_NOTIFY


def _gtk_araclari():
    """Gtk/Gdk'yi ilk gercek pencere ihtiyacinda yukler ve ResultWindow
    sinifini dondurur. Ikinci cagrida tekrar yuklemez.

    Notify BURADA YUKLENMEZ; ayri ve daha hafif olan _notify_araclari
    kullanir, cunku bildirim gondermek pencere acmaktan cok daha sik."""
    global Gtk, Gdk, _ResultWindowClass
    if _ResultWindowClass is not None:
        return _ResultWindowClass

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk as _Gtk, Gdk as _Gdk
    Gtk, Gdk = _Gtk, _Gdk

    # Ortak grafit tema yalnizca pencere gerektiginde yuklenir; izleme modu
    # (--monitor) Gtk'ye hic dokunmaz.
    sys.dont_write_bytecode = True       # ortak klasore __pycache__ yazilmasin
    if ORTAK_DIZIN not in sys.path:
        sys.path.insert(0, ORTAK_DIZIN)
    import tema
    from bekleme_cubugu import SweepBar

    _ResultWindowClass = _tanimla_result_window(Gtk, Gdk, tema, SweepBar)
    return _ResultWindowClass


_motor = None


def tarama_motoru():
    """Ortak tarama motorunu ilk ayrintili taramada yukler. Izleme modunda
    hic yuklenmez. Bulunamazsa None doner."""
    global _motor
    if _motor is None:
        ortak = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "ortak")
        if ortak not in sys.path:
            sys.path.insert(0, ortak)
        sys.dont_write_bytecode = True   # ortak klasore __pycache__ yazilmasin
        try:
            import tarama_motoru as _tm
            _motor = _tm
        except ImportError:
            return None
    return _motor


def clamav_bulgusu(bulgu):
    """Ayrintili tarama bulgusunu mevcut bulgu bicimine cevirir."""
    return {"level": HIGH, "kind": "clamav", "path": bulgu["yol"],
            "title": {dil: UI["deep_finding_title"][dil].format(imza=bulgu["imza"])
                      for dil in ("tr", "en")},
            "detail": dict(UI["deep_finding_detail"])}


CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "carotos-usb")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
def _varsayilan_dil():
    """Ilk acilis dili: sistem dili Turkce ise 'tr', baska HERHANGI bir dilse
    'en'. Sabit 'tr' yazmak, kurulumda baska dil secen kullanicinin
    uygulamalari Turkce gormesine yol aciyordu. C/POSIX dil bilgisi
    tasimaz, o yuzden atlanir. Kayitli bir ayar varsa o yine onceliklidir."""
    import os
    for degisken in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        deger = os.environ.get(degisken, "").strip()
        if deger and deger not in ("C", "POSIX"):
            return "tr" if deger.lower().startswith("tr") else "en"
    return "en"


DEFAULTS = {"lang": _varsayilan_dil(), "theme": "dark", "notify_when_clean": True}

VURGU = "usb"             # ortak/tema.py: camgobegi

# Ortak modullerin klasoru: kurulu sistemde /opt/carotos/ortak, depoda kardes
ORTAK_DIZIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "ortak")
_KOK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", ".."))
LOGO_CANDIDATES = [
    os.path.join(_KOK, "usr/share/icons/hicolor/256x256/apps/carotos-usb-check.png"),
    "/usr/share/icons/hicolor/256x256/apps/carotos-usb-check.png",
    os.path.join(_KOK, "usr/share/carotos/welcome/logo.png"),
    "/usr/share/carotos/welcome/logo.png",
]


def find_logo():
    for yol in LOGO_CANDIDATES:
        if os.path.isfile(yol):
            return yol
    return None


UI = {
    "app_title": {"tr": "CarotOS USB Denetimi", "en": "CarotOS USB Check"},
    "header_sub": {"tr": "Çıkarılabilir aygıt denetimi", "en": "Removable device check"},
    "status_clean": {"tr": "Temiz", "en": "Clean"},
    "status_found": {"tr": "Şüpheli", "en": "Suspicious"},
    "sec_check": {"tr": "Kontrol", "en": "Check"},
    "sec_scan": {"tr": "Tarama", "en": "Scan"},
    "page_result": {"tr": "Özet", "en": "Summary"},
    "page_deep": {"tr": "Ayrıntılı tarama", "en": "Detailed scan"},
    "k_files": {"tr": "Dosya", "en": "Files"},
    "k_dirs": {"tr": "Klasör", "en": "Folders"},
    "k_size": {"tr": "Boyut", "en": "Size"},
    "k_time": {"tr": "Süre", "en": "Time"},
    "k_scanned": {"tr": "Taranan dosya", "en": "Files scanned"},
    "k_found": {"tr": "Bulgu", "en": "Findings"},
    "cancel": {"tr": "Vazgeç", "en": "Cancel"},
    "pick_ok": {"tr": "Seç", "en": "Select"},
    "ok_btn": {"tr": "Tamam", "en": "OK"},
    "clean_title": {"tr": "USB kontrol edildi", "en": "USB checked"},
    "clean_body": {"tr": "{label}: şüpheli bir şey bulunmadı.",
                   "en": "{label}: nothing suspicious found."},
    "found_title": {"tr": "{label}: {n} şüpheli bulgu",
                    "en": "{label}: {n} suspicious findings"},
    "details": {"tr": "Ayrıntılar", "en": "Details"},
    "close": {"tr": "Kapat", "en": "Close"},
    "open_location": {"tr": "Konumu aç", "en": "Open location"},
    "open_device": {"tr": "Aygıtı aç", "en": "Open device"},
    "rescan": {"tr": "Yeniden tara", "en": "Re-scan"},
    "save_report": {"tr": "Raporu kaydet", "en": "Save report"},
    "level_high": {"tr": "YÜKSEK", "en": "HIGH"},
    "level_medium": {"tr": "ORTA", "en": "MEDIUM"},
    "level_low": {"tr": "BİLGİ", "en": "INFO"},
    "summary_clean": {"tr": "Şüpheli bir şey bulunmadı.",
                      "en": "Nothing suspicious found."},
    "summary_found": {"tr": "{n} şüpheli bulgu", "en": "{n} suspicious findings"},
    "scanning": {"tr": "Deneniyor…", "en": "Checking…"},
    "count_high": {"tr": "yüksek", "en": "high"},
    "count_medium": {"tr": "orta", "en": "medium"},
    "count_low": {"tr": "bilgi", "en": "info"},
    "truncated": {"tr": "Aygıt çok büyük olduğu için tarama sınırlandı; "
                        "sonuç eksik olabilir.",
                  "en": "The device is large, so the check was limited; "
                        "results may be incomplete."},
    "empty_device": {"tr": "Aygıt boş görünüyor.",
                     "en": "The device appears to be empty."},
    "clean_detail": {
        "tr": "Bilinen şüpheli desenlerden hiçbiri bulunmadı: otomatik "
              "çalıştırma dosyası, çift uzantılı dosya, gizlenmiş uzantı, "
              "klasör yerine konmuş kısayol.",
        "en": "None of the known suspicious patterns were found: autorun "
              "files, double extensions, disguised extensions, or shortcuts "
              "placed where folders should be.",
    },
    "no_device": {"tr": "Bağlı çıkarılabilir aygıt bulunamadı.",
                  "en": "No removable device is mounted."},
    "gone": {"tr": "Aygıt artık bağlı değil.",
             "en": "The device is no longer mounted."},
    "saved": {"tr": "Rapor kaydedildi: {path}", "en": "Report saved: {path}"},
    "save_failed": {"tr": "Rapor kaydedilemedi.",
                    "en": "Could not save the report."},
    "files_dirs": {"tr": "{files} dosya · {dirs} klasör · {size}",
                   "en": "{files} files · {dirs} folders · {size}"},
    "duration": {"tr": "{seconds} saniyede tarandı",
                 "en": "checked in {seconds} seconds"},
    "note": {
        "tr": "Otomatik kontrol dosya adlarına ve konumlarına bakar, dosya "
              "içeriklerini okumaz. İçerik, yalnızca siz ayrıntılı taramayı "
              "başlattığınızda okunur. Bulunan zararlılar genellikle Windows'a "
              "yöneliktir ve CarotOS'ta çalışamaz; ancak belleği başka bir "
              "bilgisayara taktığınızda oraya bulaşabilirler.",
        "en": "The automatic check looks at file names and locations and does "
              "not read file contents. Contents are read only when you start "
              "the detailed scan. Threats found are usually aimed at Windows "
              "and cannot run on CarotOS, but they can infect another computer "
              "when you plug the device in there.",
    },
    "deep_title": {"tr": "Ayrıntılı tarama (ClamAV)", "en": "Detailed scan (ClamAV)"},
    "deep_desc": {
        "tr": "Dosya içerikleri bilinen zararlı yazılım imzalarına karşı "
              "taranır. İçerik yalnızca bu taramayı başlattığınızda okunur. "
              "Bulunan dosyalara dokunulmaz; yalnızca raporlanır.",
        "en": "File contents are scanned against known malware signatures. "
              "Contents are read only when you start this scan. Files that "
              "are found are not touched; they are only reported."},
    "deep_all": {"tr": "Tüm aygıtı tara", "en": "Scan whole device"},
    "deep_pick": {"tr": "Klasör seç", "en": "Choose folder"},
    "deep_stop": {"tr": "Durdur", "en": "Stop"},
    "deep_running": {"tr": "Taranan dosya: {n} · Bulgu: {b}",
                     "en": "Files scanned: {n} · Findings: {b}"},
    "deep_loading": {
        "tr": "Virüs tanımları belleğe yükleniyor. Bu adım yaklaşık 10 saniye "
              "sürer.",
        "en": "Loading virus definitions into memory. This step takes about "
              "10 seconds."},
    "deep_clean": {"tr": "Bilinen bir tehdide rastlanmadı. {n} dosya tarandı, "
                         "{s} sn sürdü.",
                   "en": "No known threat was found. {n} files scanned in "
                         "{s} s."},
    "deep_found": {"tr": "{b} dosyada bilinen tehdit bulundu. {n} dosya "
                         "tarandı, {s} sn sürdü. Bulgular Özet "
                         "sayfasında listelenmiştir.",
                   "en": "A known threat was found in {b} files. {n} files "
                         "scanned in {s} s. The findings are listed on the "
                         "Summary page."},
    "deep_cancelled": {"tr": "Tarama durduruldu. Sonuç eksiktir.",
                       "en": "The scan was stopped. The result is incomplete."},
    "deep_removed": {"tr": "Aygıt tarama sırasında çıkarıldı; tarama "
                           "durduruldu. Sonuç eksiktir.",
                     "en": "The device was removed during the scan; the scan "
                           "was stopped. The result is incomplete."},
    "deep_error": {"tr": "Tarama tamamlanamadı.",
                   "en": "The scan could not be completed."},
    "deep_no_clamav": {"tr": "ClamAV kurulu değildir; ayrıntılı tarama "
                             "yapılamaz.",
                       "en": "ClamAV is not installed; the detailed scan "
                             "cannot run."},
    "deep_no_defs": {"tr": "Virüs tanımları bulunamadı. Tanımları Carotene "
                           "uygulamasından güncelleyin.",
                     "en": "No virus definitions were found. Update them in "
                           "the Carotene application."},
    "deep_old_defs": {"tr": "Virüs tanımları {gun} günlüktür; yeni tehditler "
                            "bulunamayabilir. Tanımlar Carotene'den "
                            "güncellenebilir.",
                      "en": "Virus definitions are {gun} days old; new threats "
                            "may not be found. They can be updated in "
                            "Carotene."},
    "deep_outside": {"tr": "Seçilen klasör bu aygıtın içinde değil.",
                     "en": "The selected folder is not on this device."},
    "deep_mem_title": {"tr": "Bellek az", "en": "Low memory"},
    "deep_mem_body": {
        "tr": "Kullanılabilir bellek {mb} MB. Tarama sırasında virüs tanımları "
              "yaklaşık 1 GB bellek kullanır; sistem yavaşlayabilir. Tarama "
              "başlatılsın mı?",
        "en": "Available memory is {mb} MB. Virus definitions use about 1 GB "
              "of memory during a scan; the system may slow down. Start the "
              "scan?"},
    "deep_finding_title": {"tr": "Zararlı yazılım imzası: {imza}",
                           "en": "Malware signature: {imza}"},
    "deep_finding_detail": {
        "tr": "ClamAV bu dosyada bilinen bir zararlı yazılım imzası buldu. "
              "Dosya aygıtta yerinde bırakıldı; açılmamalı ve başka bir "
              "bilgisayara kopyalanmamalıdır.",
        "en": "ClamAV found a known malware signature in this file. The file "
              "was left in place on the device; it should not be opened or "
              "copied to another computer."},
}


def load_settings():
    data = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
        if isinstance(stored, dict):
            for key in DEFAULTS:
                if key in stored:
                    data[key] = stored[key]
    except (OSError, ValueError):
        pass
    return data


def save_settings(data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def build_report(result, lang):
    stats = result["stats"]
    lines = [
        UI["app_title"][lang],
        "=" * 58,
        time.strftime("%Y-%m-%d %H:%M:%S"),
        f"{result.get('label', '?')}  ({result.get('device') or '?'}, "
        f"{result.get('fstype') or '?'})",
        UI["files_dirs"][lang].format(
            files=stats["files"], dirs=stats["dirs"],
            size=human_size(stats["size"])),
        "",
    ]
    if not result["findings"]:
        lines.append(UI["summary_clean"][lang])
    for finding in result["findings"]:
        tag = {HIGH: UI["level_high"], MEDIUM: UI["level_medium"],
               LOW: UI["level_low"]}[finding["level"]][lang]
        lines.append(f"[{tag}] {metin(finding['title'], lang)}")
        lines.append(f"    {metin(finding['detail'], lang)}")
        if finding.get("path"):
            lines.append(f"    {finding['path']}")
        lines.append("")
    return "\n".join(lines)


def _tanimla_result_window(Gtk, Gdk, tema, SweepBar):
    """ResultWindow sinifini Gtk/Gdk ve ortak tema hazir olduktan sonra
    tanimlar."""
    from gi.repository import Pango

    class ResultWindow(Gtk.Window):
        """Bulgu penceresi: sol menude iki sayfa (Ozet, Ayrintili tarama).

        Icerik yeniden kurulabilir; yeniden tarama yeni bir pencere acmaz,
        ayni pencereyi tazeler. (Eski surumde yeni pencere acilip eskisi
        kapatiliyordu ve kapanma olayi uygulamayi sonlandiriyordu.)
        """

        def __init__(self, result, settings, on_destroy=None):
            self.settings = settings
            self.lang = settings["lang"]
            self.theme = settings["theme"] if settings["theme"] in ("dark", "light") else "dark"
            self.result = result
            self.on_destroy_cb = on_destroy
            self.scan_thread = None
            self.cancel = None
            self.page = "sonuc"
            # ayrintili tarama durumu
            self.deep = {"durum": None}
            self.tarama = None
            self.deep_sayac = {"n": 0, "b": 0, "son": ""}
            self.deep_ui_bekliyor = False
            self.deep_count = None
            self.deep_found = None
            self.deep_path = None
            self.deep_bar = None
            self.sweep_id = 0
            self.sweep_step = 0
            self.watch_id = 0
            self.deep_bagli_mi = False
            self.deep_cikarildi = False

            super().__init__(title=UI["app_title"][self.lang])
            self.set_default_size(1000, 660)
            self.set_size_request(860, 540)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.connect("destroy", self._destroyed)
            self.connect("key-press-event", self._on_key)

            tema.uygula(self.theme, VURGU)
            logo = find_logo()
            if logo:
                try:
                    self.set_icon_from_file(logo)
                except Exception:  # noqa: BLE001
                    pass

            bolumler = [("kontrol", [("sonuc", "kalkan")]),
                        ("tarama", [("deep", "hedef")])]
            self.kabuk = tema.Kabuk(logo, bolumler, self._sayfa_secildi)
            self.add(self.kabuk)

            self.hap = tema.DurumHapi()
            self.open_btn = tema.dugme("", None, self.on_open_device)
            self.rescan_btn = tema.dugme("", "ana", self.on_rescan)
            self.save_btn = tema.dugme("", None, self.on_save)
            for parca in (self.hap, self.open_btn, self.save_btn, self.rescan_btn):
                self.kabuk.ust_sag.pack_start(parca, False, False, 0)

            # sol alt: dil ve gorunum
            alt = Gtk.Box(spacing=8)
            self.lang_combo = Gtk.ComboBoxText()
            self.lang_combo.append("tr", "Türkçe")
            self.lang_combo.append("en", "English")
            self.lang_combo.set_active_id(self.lang)
            self.lang_combo.connect("changed", self.on_lang_changed)
            alt.pack_start(self.lang_combo, True, True, 0)
            self.theme_btn = tema.dugme("", None, self.on_theme_toggled)
            alt.pack_start(self.theme_btn, False, False, 0)
            self.kabuk.yan_alt.pack_start(alt, False, False, 0)

            self.refresh()
            self.kabuk.sec("sonuc")

        # -- yardimcilar -------------------------------------------------------

        def bildir(self, metin, tur="bilgi"):
            self.kabuk.bildir(metin, tur)

        def _mesgul(self):
            return self.tarama is not None or bool(
                self.scan_thread and self.scan_thread.is_alive())

        def _mesgul_guncelle(self):
            """Bekleme cubugunu ve dugmeleri duruma gore ayarlar."""
            mesgul = self._mesgul()
            if self.tarama is not None and not self.sweep_id:
                self.sweep_id = GLib.timeout_add(45, self._sweep)
            self.rescan_btn.set_sensitive(not mesgul)
            self.save_btn.set_sensitive(not (self.scan_thread and self.scan_thread.is_alive()))
            self._hap_guncelle()

        def _hap_guncelle(self):
            findings = self.result["findings"]
            if self._mesgul():
                self.hap.ayarla(UI["scanning"][self.lang], "acik")
                return
            worst = worst_level(findings)
            if worst is None:
                self.hap.ayarla(UI["status_clean"][self.lang], "acik")
            else:
                self.hap.ayarla(UI["status_found"][self.lang],
                                "hata" if worst == HIGH else "uyari")

        def _sweep(self):
            if self.tarama is None:
                self.sweep_id = 0
                return False
            self.sweep_step += 1
            if self.deep_bar is not None:
                self.deep_bar.adim(self.sweep_step)
            return True

        # -- sayfa kurulumu ----------------------------------------------------

        def _sayfa_secildi(self, anahtar):
            self.page = anahtar
            self.refresh()

        def refresh(self):
            """Menuyu, basligi ve gecerli sayfanin icerigini sonuca gore
            yeniden kurar."""
            findings = self.result["findings"]
            self.kabuk.marka_ayarla(UI["app_title"][self.lang], UI["header_sub"][self.lang])
            self.kabuk.bolum_metni("kontrol", UI["sec_check"][self.lang])
            self.kabuk.bolum_metni("tarama", UI["sec_scan"][self.lang])
            self.kabuk.menu_metni("sonuc", UI["page_result"][self.lang])
            self.kabuk.menu_metni("deep", UI["page_deep"][self.lang])
            self.kabuk.rozet("sonuc", str(len(findings)) if findings else None)
            self.kabuk.rozet("deep", "…" if self.tarama is not None else None, sakin=True)
            self.open_btn.set_label(UI["open_device"][self.lang])
            self.rescan_btn.set_label(UI["rescan"][self.lang])
            self.save_btn.set_label(UI["save_report"][self.lang])
            self.theme_btn.set_label("☀" if self.theme == "dark" else "☾")
            self.set_title(UI["app_title"][self.lang])

            if self.page == "deep":
                self.kabuk.baslik_ayarla(UI["page_deep"][self.lang], self._aygit_metni())
                govde = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
                govde.pack_start(self._build_deep_card(), False, False, 0)
            else:
                if findings:
                    baslik = UI["summary_found"][self.lang].format(n=len(findings))
                else:
                    baslik = UI["summary_clean"][self.lang]
                self.kabuk.baslik_ayarla(self.result.get("label") or "?",
                                         baslik + "  ·  " + self._aygit_ayrinti())
                govde = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
                self._build_result(govde)
            self.kabuk.icerik(govde)
            self._mesgul_guncelle()

        def _aygit_ayrinti(self):
            parcalar = []
            if self.result.get("device"):
                parcalar.append(self.result["device"])
            if self.result.get("fstype"):
                parcalar.append(self.result["fstype"])
            return "  ·  ".join(parcalar) or "—"

        def _aygit_metni(self):
            return "  ·  ".join([self.result.get("label") or "?", self._aygit_ayrinti()])

        def _build_result(self, govde):
            findings = self.result["findings"]
            stats = self.result["stats"]

            ozet = Gtk.Box(spacing=12)
            ozet.set_homogeneous(True)
            for anahtar, deger, orta in (
                    ("k_files", f"{stats['files']:,}".replace(
                        ",", "." if self.lang == "tr" else ","), False),
                    ("k_dirs", f"{stats['dirs']:,}".replace(
                        ",", "." if self.lang == "tr" else ","), False),
                    ("k_size", human_size(stats["size"]), True),
                    ("k_time", f"{stats['seconds']} s", True)):
                kpi = tema.KpiKutusu(UI[anahtar][self.lang])
                kpi.ayarla(deger, orta=orta)
                ozet.pack_start(kpi, True, True, 0)
            govde.pack_start(ozet, False, False, 0)

            if stats.get("truncated"):
                kutu, _ = tema.not_kutusu(UI["truncated"][self.lang], "uyari")
                govde.pack_start(kutu, False, False, 0)

            sayilar = {level: sum(1 for f in findings if f["level"] == level)
                       for level in (HIGH, MEDIUM, LOW)}
            if findings:
                pill = Gtk.Box(spacing=8)
                for level, anahtar, renk in ((HIGH, "count_high", "kirmizi"),
                                             (MEDIUM, "count_medium", "sari"),
                                             (LOW, "count_low", "gri")):
                    if sayilar[level]:
                        pill.pack_start(tema.rozet(
                            f"{sayilar[level]} {UI[anahtar][self.lang]}", renk),
                            False, False, 0)
                govde.pack_start(pill, False, False, 0)
            else:
                govde.pack_start(self._build_clean_card(), False, False, 0)
            for finding in findings:
                govde.pack_start(self._build_card(finding), False, False, 0)

            kutu, _ = tema.not_kutusu(UI["note"][self.lang], "bilgi")
            govde.pack_start(kutu, False, False, 0)

        def _build_clean_card(self):
            bos = self.result["stats"].get("empty")
            dis, ic = tema.kart(18, 10)
            satir = Gtk.Box(spacing=14)
            satir.pack_start(tema.ikon_kutusu("onay", "yesil", 44), False, False, 0)
            satir.pack_start(tema.etiket(
                UI["empty_device"][self.lang] if bos else UI["clean_detail"][self.lang],
                None, sar=True, genislik=80), True, True, 0)
            ic.pack_start(satir, False, False, 0)
            return dis

        def _build_card(self, finding):
            level = finding["level"]
            renk = {HIGH: "kirmizi", MEDIUM: "sari", LOW: "gri"}[level]
            etiket = {HIGH: UI["level_high"], MEDIUM: UI["level_medium"],
                      LOW: UI["level_low"]}[level][self.lang]
            dis, ic = tema.kart(16, 8, "tehlikeli" if level == HIGH else "")
            ust = Gtk.Box(spacing=11)
            ust.pack_start(tema.rozet(etiket, renk), False, False, 0)
            ust.pack_start(tema.etiket(metin(finding["title"], self.lang), "kart-baslik",
                                       sar=True), True, True, 0)
            if finding.get("path"):
                ust.pack_end(tema.dugme(UI["open_location"][self.lang], "kucuk",
                                        self.on_open_path, finding["path"]),
                             False, False, 0)
            ic.pack_start(ust, False, False, 0)
            ic.pack_start(tema.etiket(metin(finding["detail"], self.lang), "soluk",
                                      sar=True, genislik=90), False, False, 0)
            if finding.get("path"):
                ic.pack_start(tema.etiket(finding["path"], "mono", sar=True, sec=True),
                              False, False, 0)
            return dis

        # -- ayrintili tarama (ClamAV) ----------------------------------------

        def _build_deep_card(self):
            dis, ic = tema.kart(18, 12, "vurgulu" if self.tarama is not None else "")
            self.deep_bar = None
            if self.tarama is not None:
                sag = Gtk.Box(spacing=14)
                self.deep_bar = SweepBar(tema.AKTIF["vurgu"])
                self.deep_bar.show()
                sag.pack_start(self.deep_bar, False, False, 0)
                sag.pack_start(tema.dugme(UI["deep_stop"][self.lang], "tehlike",
                                          lambda: self.tarama and self.tarama.iptal()),
                               False, False, 0)
            else:
                etkin = not self._mesgul()
                sag = Gtk.Box(spacing=8)
                tum = tema.dugme(UI["deep_all"][self.lang], "ana", self.start_deep, None)
                sec = tema.dugme(UI["deep_pick"][self.lang], None, self.on_deep_pick)
                for btn in (sec, tum):
                    btn.set_sensitive(etkin)
                    sag.pack_start(btn, False, False, 0)
            tema.kart_basligi(ic, UI["deep_title"][self.lang], None, sag)
            ic.pack_start(tema.etiket(UI["deep_desc"][self.lang], "soluk", sar=True,
                                      genislik=90), False, False, 0)

            durum = self.deep.get("durum")
            self.deep_count = self.deep_found = self.deep_path = None
            if self.tarama is not None:
                sayilar = Gtk.Box(spacing=48)
                kolonlar = []
                for anahtar in ("k_scanned", "k_found"):
                    kolon = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    deger = tema.etiket("0", "kpi-deger")
                    kolon.pack_start(deger, False, False, 0)
                    kolon.pack_start(tema.etiket(UI[anahtar][self.lang], "kpi-ad"),
                                     False, False, 0)
                    sayilar.pack_start(kolon, False, False, 0)
                    kolonlar.append(deger)
                self.deep_count, self.deep_found = kolonlar
                ic.pack_start(sayilar, False, False, 0)
                self.deep_path = tema.etiket("", "mono")
                self.deep_path.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
                ic.pack_start(self.deep_path, False, False, 0)
                self._deep_sayac_yaz()
            elif durum:
                tur = {"temiz": "basari", "bulgu": "hata"}.get(durum, "uyari")
                mesaj = UI[self.deep["anahtar"]][self.lang].format(**self.deep["kw"])
                kutu, _ = tema.not_kutusu(mesaj, tur)
                ic.pack_start(kutu, False, False, 0)
            uyari = self.deep.get("tanim_uyarisi")
            if uyari and self.tarama is None:
                kutu, _ = tema.not_kutusu(uyari, "uyari")
                ic.pack_start(kutu, False, False, 0)
            return dis

        def _deep_sayac_yaz(self):
            self.deep_ui_bekliyor = False
            if self.tarama is None or self.deep_count is None:
                return False
            try:
                self.deep_count.set_text(f"{self.deep_sayac['n']:,}".replace(
                    ",", "." if self.lang == "tr" else ","))
                self.deep_found.set_text(str(self.deep_sayac["b"]))
                self.deep_path.set_text(self.deep_sayac["son"]
                                        or UI["deep_loading"][self.lang])
            except Exception:  # noqa: BLE001
                pass
            return False

        def on_deep_pick(self):
            root = self.result.get("root")
            if not self._device_present():
                self.bildir(UI["gone"][self.lang], "hata")
                return
            dialog = Gtk.FileChooserDialog(
                title=UI["deep_pick"][self.lang], transient_for=self,
                action=Gtk.FileChooserAction.SELECT_FOLDER)
            dialog.add_buttons(UI["cancel"][self.lang], Gtk.ResponseType.CANCEL,
                               UI["pick_ok"][self.lang], Gtk.ResponseType.OK)
            dialog.set_current_folder(root)
            secilen = (dialog.get_filename()
                       if dialog.run() == Gtk.ResponseType.OK else None)
            dialog.destroy()
            if not secilen:
                return
            gercek = os.path.realpath(secilen)
            kok = os.path.realpath(root)
            if gercek != kok and not gercek.startswith(kok + os.sep):
                self.bildir(UI["deep_outside"][self.lang], "hata")
                return
            self.start_deep([gercek])

        def start_deep(self, yollar):
            if self.tarama is not None:
                return
            if self.scan_thread and self.scan_thread.is_alive():
                return
            root = self.result.get("root")
            if not self._device_present():
                self.bildir(UI["gone"][self.lang], "hata")
                return
            motor = tarama_motoru()
            if motor is None or not motor.clamscan_yolu():
                self.bildir(UI["deep_no_clamav"][self.lang], "hata")
                return
            bilgi = motor.tanim_bilgisi()
            if bilgi["durum"] == motor.TANIM_YOK:
                self.bildir(UI["deep_no_defs"][self.lang], "hata")
                return
            self.deep["tanim_uyarisi"] = (
                UI["deep_old_defs"][self.lang].format(gun=bilgi["yas_gun"])
                if bilgi["durum"] == motor.TANIM_ESKI else None)
            yeterli, mb = motor.bellek_yeterli()
            if not yeterli and not tema.onay_sor(
                    self, UI["deep_mem_title"][self.lang],
                    UI["deep_mem_body"][self.lang].format(mb=mb),
                    UI["ok_btn"][self.lang], UI["cancel"][self.lang]):
                return
            # Tarama suresince aygitin cikarilip cikarilmadigi izlenir
            self.deep_bagli_mi = os.path.ismount(root)
            self.deep_sayac = {"n": 0, "b": 0, "son": ""}
            self.deep = {"durum": None,
                         "tanim_uyarisi": self.deep.get("tanim_uyarisi")}
            self.deep_cikarildi = False
            self.tarama = motor.Tarama(yollar or [root], olay=self._deep_olay)
            threading.Thread(target=self._deep_isi, args=(self.tarama,),
                             daemon=True).start()
            self.watch_id = GLib.timeout_add(1000, self._aygit_izle)
            self.page = "deep"
            self.kabuk.sec("deep")
            self.refresh()

        def _deep_olay(self, tur, veri):
            # is parcaciginda calisir
            if tur in ("temiz", "bulgu"):
                self.deep_sayac["n"] += 1
                self.deep_sayac["son"] = veri if tur == "temiz" else veri[0]
                if tur == "bulgu":
                    self.deep_sayac["b"] += 1
            if not self.deep_ui_bekliyor:
                self.deep_ui_bekliyor = True
                GLib.timeout_add(150, self._deep_sayac_yaz)

        def _deep_isi(self, tarama):
            sonuc = tarama.calistir()
            GLib.idle_add(self._deep_done, tarama, sonuc)

        def _aygit_izle(self):
            if self.tarama is None:
                self.watch_id = 0
                return False
            root = self.result.get("root")
            gitti = not root or not os.path.isdir(root) or (
                self.deep_bagli_mi and not os.path.ismount(root))
            if gitti:
                self.deep_cikarildi = True
                self.tarama.iptal()
                self.watch_id = 0
                return False
            return True

        def _deep_done(self, tarama, sonuc):
            if tarama is not self.tarama:
                return False
            self.tarama = None
            if self.watch_id:
                GLib.source_remove(self.watch_id)
                self.watch_id = 0
            motor = tarama_motoru()
            durum = sonuc["durum"]
            n, sure = sonuc["taranan"], sonuc["sure"]
            if self.deep_cikarildi:
                self.deep.update(durum="cikarildi", anahtar="deep_removed", kw={})
            elif durum == motor.IPTAL:
                self.deep.update(durum="iptal", anahtar="deep_cancelled", kw={})
            elif durum == motor.BULGU:
                self.deep.update(durum="bulgu", anahtar="deep_found",
                                 kw={"b": len(sonuc["bulgular"]), "n": n, "s": sure})
            elif durum == motor.TEMIZ:
                self.deep.update(durum="temiz", anahtar="deep_clean",
                                 kw={"n": n, "s": sure})
            else:
                self.deep.update(durum="hata", anahtar="deep_error", kw={})
            # Yeni ClamAV bulgulari mevcut listeye eklenir (eskileri yenilenir)
            bulgular = [f for f in self.result["findings"] if f.get("kind") != "clamav"]
            bulgular = [clamav_bulgusu(b) for b in sonuc["bulgular"]] + bulgular
            self.result["findings"] = bulgular
            self.refresh()
            return False

        # -- olaylar -----------------------------------------------------------

        def _on_key(self, _widget, event):
            if event.keyval == Gdk.KEY_Escape:
                self.destroy()
                return True
            return False

        def _destroyed(self, _widget):
            if self.cancel is not None:
                self.cancel.set()
            if self.tarama is not None:
                self.tarama.iptal()
            for kaynak in ("sweep_id", "watch_id"):
                if getattr(self, kaynak):
                    GLib.source_remove(getattr(self, kaynak))
                    setattr(self, kaynak, 0)
            if self.on_destroy_cb:
                self.on_destroy_cb(self)

        def _device_present(self):
            """Taranan konum hala erisilebilir mi?

            Yalnizca dizinin var olup olmadigina bakilir. Daha once burada
            /proc/mounts'ta bir baglama noktasi araniyordu; bu, --scan ile
            verilen siradan klasorleri ve baglama noktasi adi farkli yazilmis
            aygitlari yanlislikla "bagli degil" saydigi icin kaldirildi.
            """
            root = self.result.get("root")
            return bool(root) and os.path.isdir(root)

        def on_open_device(self):
            root = self.result.get("root")
            if not self._device_present():
                self.bildir(UI["gone"][self.lang], "hata")
                return
            try:
                subprocess.Popen(["xdg-open", root])
            except OSError:
                pass

        def on_open_path(self, path):
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            if not os.path.isdir(folder):
                self.bildir(UI["gone"][self.lang], "hata")
                return
            try:
                subprocess.Popen(["xdg-open", folder])
            except OSError:
                pass

        def on_rescan(self):
            """Ayni pencerede yeniden tarar; yeni pencere ACMAZ."""
            if self._mesgul():
                return
            root = self.result.get("root")
            if not self._device_present():
                self.bildir(UI["gone"][self.lang], "hata")
                return

            self.cancel = threading.Event()

            def worker():
                fresh = enrich(scan_path(root, self.cancel), root)
                GLib.idle_add(self._scan_done, fresh)

            self.scan_thread = threading.Thread(target=worker, daemon=True)
            self.scan_thread.start()
            self._mesgul_guncelle()

        def _scan_done(self, fresh):
            self.scan_thread = None
            if not fresh["stats"].get("cancelled"):
                # Hizli kontrol yenilendi; onceki ayrintili tarama sonucu
                # artik bu listeye ait degil
                self.result = fresh
                self.deep = {"durum": None}
            self.refresh()
            return False

        def on_save(self):
            path = os.path.join(
                GLib.get_home_dir(),
                time.strftime("carotos-usb-%Y%m%d-%H%M.txt"))
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(build_report(self.result, self.lang))
                self.bildir(UI["saved"][self.lang].format(path=path), "basari")
            except OSError:
                self.bildir(UI["save_failed"][self.lang], "hata")

        def on_lang_changed(self, combo):
            secilen = combo.get_active_id()
            if secilen and secilen != self.lang:
                self.lang = self.settings["lang"] = secilen
                save_settings(self.settings)
                self.refresh()

        def on_theme_toggled(self):
            self.theme = "light" if self.theme == "dark" else "dark"
            self.settings["theme"] = self.theme
            save_settings(self.settings)
            tema.uygula(self.theme, VURGU)
            self.refresh()
            self.queue_draw()

    return ResultWindow


# ===========================================================================
# Bildirim ve izleyici
# ===========================================================================

def server_supports_actions():
    """Bildirim sunucusu tiklanabilir dugme destekliyor mu?

    Destekliyorsa pencereyi kendiligimizden acmayiz — kullanici isterse
    "Ayrintilar" dugmesine basar. Desteklemiyorsa pencereyi acmak
    zorundayiz, yoksa uyari ulasilamaz kalir.
    """
    if not _notify_araclari():
        return False
    try:
        if not Notify.is_initted():
            Notify.init("CarotOS USB")
        caps = Notify.get_server_caps() or []
        return "actions" in caps
    except Exception:
        return False


def send_notification(result, settings, on_details=None):
    """Bildirim gonderir.

    Dondurur: (bildirim_nesnesi, dugme_kondu_mu)
    Bildirim nesnesi CAGIRAN TARAFTA tutulmalidir; tutulmazsa cop toplayici
    siler ve dugmeye basildiginda hicbir sey olmaz.
    """
    lang = settings["lang"]
    findings = result["findings"]
    label = result.get("label", "USB")
    count = len(findings)

    if count == 0:
        summary = UI["clean_title"][lang]
        body = UI["clean_body"][lang].format(label=label)
        icon = "drive-removable-media"
        # DUSUK oncelik: kisa surede kendiliginden kaybolur
        urgency = 0
        timeout = 5000
    else:
        summary = UI["found_title"][lang].format(label=label, n=count)
        body = metin(findings[0]["title"], lang)
        if count > 1:
            body += f"  ·  +{count - 1}"
        worst = worst_level(findings)
        icon = "dialog-error" if worst == HIGH else "dialog-warning"
        # NORMAL oncelik. "Kritik" verilirse standarda gore bildirim
        # kullanici kapatana kadar ekranda kalir — istenmiyor.
        urgency = 1
        timeout = 12000

    if _notify_araclari():
        try:
            if not Notify.is_initted():
                Notify.init("CarotOS USB")
            note = Notify.Notification.new(summary, body, icon)
            note.set_urgency(urgency)
            note.set_timeout(timeout)

            has_button = False
            if count and on_details and server_supports_actions():
                def on_clicked(_notification, _action, _data=None):
                    on_details()
                note.add_action("details", UI["details"][lang], on_clicked)
                # Geri cagirma islevi de tutulmali
                note._carotos_callback = on_clicked
                has_button = True

            note.show()
            return note, has_button
        except Exception:
            pass

    try:
        subprocess.Popen(["notify-send", "-i", icon,
                          "-t", str(timeout), summary, body])
    except OSError:
        print(f"{summary}: {body}")
    return None, False


class Monitor:
    """Bagli aygit degisikliklerini /proc/mounts uzerinden izler."""

    def __init__(self, settings):
        self.settings = settings
        self.known = {e["mount"] for e in removable_mounts()}
        self.recent = {}
        self.windows = {}        # mount -> ResultWindow
        self.notifications = []  # cop toplayiciya karsi tutulur
        self.pending = None      # debounce zamanlayici kimligi
        self.snapshot = set()    # bagli aygitlarin son goruntusu

    # -- baslatma ---------------------------------------------------------

    def start(self):
        """Bagli aygit degisikliklerini DUZENLI YOKLAMA ile izler.

        Eski surum /proc/mounts'u GLib.IOChannel ile olay-tabanli izliyordu;
        bu desen bazi cekirdek/PyGObject surumlerinde ya hic tetiklenmez ya da
        POLLERR yuzunden bosa dongu yapip islemciyi mesgul eder — kararsizligin
        ana nedeni buydu. Kucuk bir dosyayi saniyede bir okumanin maliyeti
        ihmal edilebilir ve bu yontem her cekirdekte guvenilir calisir.
        """
        self.snapshot = self._snapshot()
        GLib.timeout_add_seconds(MONITOR_POLL_SECONDS, self._poll)
        return True

    def _snapshot(self):
        try:
            return {(e["device"], e["mount"]) for e in mount_entries()}
        except Exception:  # noqa: BLE001 -- gecici okuma hatasi izleyiciyi dusurmesin
            return self.snapshot

    def _poll(self):
        """Baglama tablosu degistiyse degerlendirmeyi tetikler. Tek bir hata
        bile izleyiciyi durdurmasin diye bastan sona korumali."""
        try:
            current = self._snapshot()
            if current != self.snapshot:
                self.snapshot = current
                self._schedule()
        except Exception as exc:  # noqa: BLE001
            print(f"[usb-check] izleme hatasi: {exc}", file=sys.stderr)
        return True  # yoklama surekli devam etsin

    def _schedule(self):
        # Bir baglama islemi birden cok olay uretebilir; son olaydan
        # kisa bir sure sonra tek seferde degerlendirilir.
        if self.pending is not None:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(500, self._settled)

    def _settled(self):
        self.pending = None
        try:
            self.snapshot = self._snapshot()
            current = removable_mounts()
            points = {e["mount"] for e in current}

            # Cikarilan aygitlarin penceresi kapanmaz ama kaydi temizlenir
            for mount in list(self.windows):
                if mount not in points:
                    self.windows.pop(mount, None)

            for entry in current:
                if entry["mount"] not in self.known:
                    self._handle(entry)

            self.known = points
        except Exception as exc:  # noqa: BLE001 -- degerlendirme izleyiciyi dusurmesin
            print(f"[usb-check] degerlendirme hatasi: {exc}", file=sys.stderr)
        return False

    # -- tarama -----------------------------------------------------------

    def _handle(self, entry):
        uuid = device_uuid(entry["device"])
        now = time.time()
        if now - self.recent.get(uuid, 0) < COOLDOWN_SECONDS:
            return
        self.recent[uuid] = now
        # Uzun calismada sinirsiz buyumesin: cok eski kayitlari at.
        cutoff = now - COOLDOWN_SECONDS * 40
        self.recent = {k: v for k, v in self.recent.items() if v > cutoff}

        mount = entry["mount"]

        # Tarama ayri is parcaciginda; masaustu donmasin.
        def worker():
            try:
                result = enrich(scan_path(mount), mount)
                GLib.idle_add(self._scan_done, result)
            except Exception as exc:  # noqa: BLE001 -- tarama hatasi izleyiciyi dusurmesin
                print(f"[usb-check] tarama hatasi ({mount}): {exc}", file=sys.stderr)

        threading.Thread(target=worker, daemon=True).start()

    def _scan_done(self, result):
        findings = result["findings"]
        has_button = False

        if findings or self.settings.get("notify_when_clean", True):
            note, has_button = send_notification(
                result, self.settings,
                on_details=lambda: self.show_window(result))
            if note is not None:
                # Nesne tutulmazsa cop toplayici siler ve dugme olu kalir.
                self.notifications.append(note)
                if len(self.notifications) > 12:
                    self.notifications = self.notifications[-12:]

        # Pencere yalnizca "Ayrintilar" dugmesi KONULAMADIYSA acilir.
        # Dugme varsa kararı kullaniciya birakiriz.
        if findings and not has_button:
            self.show_window(result)
        return False

    def show_window(self, result):
        mount = result.get("root")
        existing = self.windows.get(mount)
        if existing is not None:
            existing.present()
            return
        window = _gtk_araclari()(result, self.settings, on_destroy=self._forget)
        self.windows[mount] = window
        window.show_all()
        window.present()

    def _forget(self, window):
        for mount, candidate in list(self.windows.items()):
            if candidate is window:
                self.windows.pop(mount, None)


# ===========================================================================
# Giris noktalari
# ===========================================================================

def run_monitor(settings):
    monitor = Monitor(settings)
    if not monitor.start():
        return 1
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    return 0


def run_windows(results, settings):
    """Verilen sonuclar icin pencere acar; SON pencere kapaninca cikar."""
    if not results:
        print(UI["no_device"][settings["lang"]])
        return 1

    open_windows = []

    def forget(window):
        if window in open_windows:
            open_windows.remove(window)
        if not open_windows:
            Gtk.main_quit()

    RW = _gtk_araclari()
    for result in results:
        window = RW(result, settings, on_destroy=forget)
        open_windows.append(window)
        window.show_all()

    Gtk.main()
    return 0


def run_scan(path, settings):
    if not os.path.isdir(path):
        print(f"Dizin bulunamadi: {path}", file=sys.stderr)
        return 1
    return run_windows([enrich(scan_path(path), path)], settings)


def run_all(settings):
    mounts = removable_mounts()
    results = [enrich(scan_path(e["mount"]), e["mount"]) for e in mounts]
    return run_windows(results, settings)


def main():
    settings = load_settings()
    args = sys.argv[1:]

    if "--monitor" in args:
        return run_monitor(settings)
    if "--scan" in args:
        index = args.index("--scan")
        if index + 1 < len(args):
            return run_scan(args[index + 1], settings)
        print("--scan bir yol bekliyor", file=sys.stderr)
        return 1
    return run_all(settings)


if __name__ == "__main__":
    sys.exit(main())
