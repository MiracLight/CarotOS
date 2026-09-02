#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CarotOS USB Denetimi

Takilan cikarilabilir aygitlari algilar ve hizli bir guvenlik kontrolu yapar.
Dosya ICERIKLERINI OKUMAZ — yalnizca dosya adlarina, uzantilarina, izinlerine
ve konumlarina bakar. Bu yuzden buyuk bir bellekte bile saniyeler surer.

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
                add(HIGH, "bidi", "Adı gizlenmiş klasör",
                    "Klasör adında, adı ekranda farklı göstermek için "
                    "kullanılan görünmez bir karakter var.", full_dir)

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
                add(HIGH, "autorun", "Otomatik çalıştırma dosyası",
                    "Bu dosya, bellek takıldığında Windows'ta bir programın "
                    "kendiliğinden çalışmasını sağlamak için kullanılır. "
                    "Zararlı yazılımların en bilinen yayılma yöntemidir.",
                    full)
                continue

            if has_bidi_trick(name):
                add(HIGH, "bidi", "Adı gizlenmiş dosya",
                    "Dosya adında, gerçek uzantıyı ekranda farklı göstermek "
                    "için kullanılan görünmez bir karakter var. Belge gibi "
                    "görünen dosya aslında çalıştırılabilir olabilir.", full)
                continue

            if first_ext in DOC_EXT and last_ext in EXEC_EXT:
                add(HIGH, "double_ext", "Çift uzantılı dosya",
                    f"Dosya adı belge gibi görünüyor ama gerçek uzantısı "
                    f"{last_ext} — yani çalıştırılabilir bir programdır. "
                    f"Kullanıcıyı yanıltmak için sık kullanılan bir "
                    f"yöntemdir.", full)
                continue

            if last_ext == ".lnk":
                lnk_files.append((name, full))
                continue

            if last_ext in EXEC_EXT:
                if at_root:
                    exec_in_root.append((name, full))
                elif os.path.basename(current).startswith("."):
                    add(MEDIUM, "hidden_exec",
                        "Gizli klasörde çalıştırılabilir dosya",
                        "Gizlenmiş bir klasörün içinde çalıştırılabilir bir "
                        "dosya bulundu. Olağan bir yerleşim değildir.", full)

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
        add(HIGH, "lnk_worm", "Klasörler kısayolla değiştirilmiş olabilir",
            f"Görünür bir klasöre karşılık gelmeyen kısayol dosyaları "
            f"bulundu ({names}). Bu, gerçek klasörleri gizleyip yerlerine "
            f"zararlı kısayol koyan yaygın bir USB zararlısı davranışıdır. "
            f"Kısayollara tıklamayın.", disguised[0][1])
    elif disguised:
        add(MEDIUM, "lnk_single",
            f"{len(disguised)} karşılıksız kısayol dosyası",
            "Bir klasöre karşılık gelmeyen kısayol dosyası bulundu. "
            "Kısayollar tek başına zararlı değildir, ancak gizlenmiş bir "
            "klasörün yerine geçmiş olabilirler.", disguised[0][1])

    if exec_in_root:
        names = ", ".join(n for n, _ in exec_in_root[:5])
        level = MEDIUM if len(exec_in_root) < 4 else HIGH
        add(level, "root_exec",
            f"Ana dizinde {len(exec_in_root)} çalıştırılabilir dosya",
            f"{names}. Bunlar Windows'ta çalışabilen programlardır. "
            f"Kaynağını bilmediğiniz programları çalıştırmayın.",
            exec_in_root[0][1])

    if hidden_dirs and not disguised:
        add(LOW, "hidden_dirs", f"{len(hidden_dirs)} gizli klasör",
            "Gizli klasörler çoğu zaman normaldir (sistem dosyaları), "
            "ancak içeriğine bakmakta fayda var.",
            os.path.join(root, hidden_dirs[0]))

    if unreadable:
        add(LOW, "unreadable", f"{len(unreadable)} klasör okunamadı",
            "Bazı klasörlere erişim izni olmadığı için içerikleri "
            "denetlenemedi. Sonuç eksik olabilir.", unreadable[0])

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

    _ResultWindowClass = _tanimla_result_window(Gtk, Gdk)
    return _ResultWindowClass


CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "carotos-usb")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
DEFAULTS = {"lang": "tr", "theme": "dark", "notify_when_clean": True}

ACCENT = "#87979B"
C_HIGH = "#c2554f"
C_MED = "#c8952a"
C_LOW = "#6d7a7e"
C_OK = "#4c9a6a"

UI = {
    "app_title": {"tr": "CarotOS USB Denetimi", "en": "CarotOS USB Check"},
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
        "tr": "Bu kontrol dosya adlarına ve konumlarına bakar, dosya "
              "içeriklerini taramaz. Bulunan zararlılar genellikle Windows'a "
              "yöneliktir ve CarotOS'ta çalışamaz — ancak belleği başka bir "
              "bilgisayara taktığınızda oraya bulaşabilirler.",
        "en": "This check looks at file names and locations; it does not scan "
              "file contents. Threats found are usually aimed at Windows and "
              "cannot run on CarotOS — but they can infect another computer "
              "when you plug the device in there.",
    },
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
        lines.append(f"[{tag}] {finding['title']}")
        lines.append(f"    {finding['detail']}")
        if finding.get("path"):
            lines.append(f"    {finding['path']}")
        lines.append("")
    return "\n".join(lines)


def _tanimla_result_window(Gtk, Gdk):
    """ResultWindow sinifini Gtk/Gdk hazir olduktan sonra tanimlar."""
    class ResultWindow(Gtk.Window):
        """Bulgu penceresi.

        Icerik `self.body` icinde yeniden kurulabilir; yeniden tarama yeni bir
        pencere acmaz, ayni pencereyi tazeler. (Eski surumde yeni pencere acilip
        eskisi kapatiliyordu ve kapanma olayi uygulamayi sonlandiriyordu.)
        """

        def __init__(self, result, settings, on_destroy=None):
            self.settings = settings
            self.lang = settings["lang"]
            self.theme = settings["theme"]
            self.result = result
            self.on_destroy_cb = on_destroy
            self.scan_thread = None
            self.cancel = None

            super().__init__(title=UI["app_title"][self.lang])
            self.set_default_size(780, 580)
            self.set_size_request(660, 460)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.connect("destroy", self._destroyed)
            self.connect("key-press-event", self._on_key)

            self.provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), self.provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.apply_theme()

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.add(root)

            self.header_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.header_holder.get_style_context().add_class("header")
            root.pack_start(self.header_holder, False, False, 0)
            root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                            False, False, 0)

            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            root.pack_start(scroller, True, True, 0)
            self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            self.body.set_margin_top(22); self.body.set_margin_bottom(22)
            self.body.set_margin_start(24); self.body.set_margin_end(24)
            scroller.add(self.body)

            root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                            False, False, 0)
            root.pack_start(self._build_footer(), False, False, 0)

            self.refresh()

        # -- yapim ------------------------------------------------------------

        def _build_footer(self):
            footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            footer.set_border_width(13)

            self.open_btn = Gtk.Button(label=UI["open_device"][self.lang])
            self.open_btn.connect("clicked", self.on_open_device)
            footer.pack_start(self.open_btn, False, False, 0)

            self.rescan_btn = Gtk.Button(label=UI["rescan"][self.lang])
            self.rescan_btn.connect("clicked", self.on_rescan)
            footer.pack_start(self.rescan_btn, False, False, 0)

            self.save_btn = Gtk.Button(label=UI["save_report"][self.lang])
            self.save_btn.connect("clicked", self.on_save)
            footer.pack_start(self.save_btn, False, False, 0)

            self.status = Gtk.Label(xalign=0.0)
            self.status.get_style_context().add_class("sub-text")
            self.status.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            footer.pack_start(self.status, True, True, 6)

            self.spinner = Gtk.Spinner()
            footer.pack_end(self.spinner, False, False, 0)

            close = Gtk.Button(label=UI["close"][self.lang])
            close.get_style_context().add_class("suggested-action")
            close.connect("clicked", lambda *_: self.destroy())
            footer.pack_end(close, False, False, 0)
            return footer

        def _clear(self, container):
            for child in container.get_children():
                container.remove(child)

        def refresh(self):
            """Basligi ve bulgu listesini mevcut sonuca gore yeniden kurar."""
            self._clear(self.header_holder)
            self._clear(self.body)
            self.header_holder.pack_start(self._build_header(), True, True, 0)

            findings = self.result["findings"]
            if not findings:
                self.body.pack_start(self._build_clean_card(), False, False, 0)
            for finding in findings:
                self.body.pack_start(self._build_card(finding), False, False, 0)
            self.body.pack_start(self._build_note(), False, False, 0)

            self.header_holder.show_all()
            self.body.show_all()

        def _build_header(self):
            findings = self.result["findings"]
            stats = self.result["stats"]

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            box.set_margin_top(20); box.set_margin_bottom(20)
            box.set_margin_start(24); box.set_margin_end(24)

            worst = worst_level(findings)
            if worst is None:
                heading = UI["summary_clean"][self.lang]
                title_css, band_css = "title-ok", "band-ok"
            else:
                heading = UI["summary_found"][self.lang].format(n=len(findings))
                title_css = {HIGH: "title-high", MEDIUM: "title-med",
                             LOW: "title-low"}[worst]
                band_css = {HIGH: "band-high", MEDIUM: "band-med",
                            LOW: "band-low"}[worst]

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            stripe = Gtk.Box()
            stripe.set_size_request(4, -1)
            stripe.get_style_context().add_class(band_css)
            row.pack_start(stripe, False, False, 0)

            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            title = Gtk.Label(label=heading, xalign=0.0)
            title.get_style_context().add_class("big-title")
            title.get_style_context().add_class(title_css)
            title.set_line_wrap(True)
            col.pack_start(title, False, False, 0)

            pieces = [self.result.get("label") or "?"]
            if self.result.get("device"):
                pieces.append(self.result["device"])
            if self.result.get("fstype"):
                pieces.append(self.result["fstype"])
            device = Gtk.Label(label="  ·  ".join(pieces), xalign=0.0)
            device.get_style_context().add_class("sub-text")
            device.set_line_wrap(True)
            col.pack_start(device, False, False, 0)
            row.pack_start(col, True, True, 0)
            box.pack_start(row, False, False, 0)

            counts = {level: sum(1 for f in findings if f["level"] == level)
                      for level in (HIGH, MEDIUM, LOW)}
            if findings:
                pills = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
                pills.set_margin_start(18)
                for level, key, css in ((HIGH, "count_high", "pill-high"),
                                        (MEDIUM, "count_medium", "pill-med"),
                                        (LOW, "count_low", "pill-low")):
                    if counts[level]:
                        pill = Gtk.Label(label=f"{counts[level]} {UI[key][self.lang]}")
                        pill.get_style_context().add_class("pill")
                        pill.get_style_context().add_class(css)
                        pills.pack_start(pill, False, False, 0)
                box.pack_start(pills, False, False, 0)

            info = Gtk.Label(
                label=UI["files_dirs"][self.lang].format(
                    files=stats["files"], dirs=stats["dirs"],
                    size=human_size(stats["size"])) + "  ·  " +
                      UI["duration"][self.lang].format(seconds=stats["seconds"]),
                xalign=0.0)
            info.get_style_context().add_class("sub-text")
            info.set_margin_start(18)
            info.set_line_wrap(True)
            box.pack_start(info, False, False, 0)

            if stats.get("truncated"):
                warn = Gtk.Label(label=UI["truncated"][self.lang], xalign=0.0)
                warn.get_style_context().add_class("warn-text")
                warn.set_margin_start(18)
                warn.set_line_wrap(True)
                warn.set_max_width_chars(80)
                box.pack_start(warn, False, False, 0)

            return box

        def _card_shell(self):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            card.get_style_context().add_class("card")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            inner.set_margin_top(18); inner.set_margin_bottom(18)
            inner.set_margin_start(22); inner.set_margin_end(22)
            card.pack_start(inner, True, True, 0)
            return card, inner

        def _build_clean_card(self):
            card, inner = self._card_shell()
            text = (UI["empty_device"][self.lang]
                    if self.result["stats"].get("empty")
                    else UI["clean_detail"][self.lang])
            label = Gtk.Label(label=text, xalign=0.0)
            label.set_line_wrap(True)
            label.set_max_width_chars(84)
            inner.pack_start(label, False, False, 0)
            return card

        def _build_card(self, finding):
            level = finding["level"]
            badge_css = {HIGH: "badge-high", MEDIUM: "badge-med",
                         LOW: "badge-low"}[level]
            badge_text = {HIGH: UI["level_high"], MEDIUM: UI["level_medium"],
                          LOW: UI["level_low"]}[level][self.lang]

            card, inner = self._card_shell()

            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
            badge = Gtk.Label(label=badge_text)
            badge.get_style_context().add_class("badge")
            badge.get_style_context().add_class(badge_css)
            badge.set_valign(Gtk.Align.CENTER)
            top.pack_start(badge, False, False, 0)

            title = Gtk.Label(label=finding["title"], xalign=0.0)
            title.get_style_context().add_class("card-title")
            title.set_line_wrap(True)
            title.set_valign(Gtk.Align.CENTER)
            top.pack_start(title, True, True, 0)

            if finding.get("path"):
                btn = Gtk.Button(label=UI["open_location"][self.lang])
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", self.on_open_path, finding["path"])
                top.pack_end(btn, False, False, 0)
            inner.pack_start(top, False, False, 0)

            detail = Gtk.Label(label=finding["detail"], xalign=0.0)
            detail.set_line_wrap(True)
            detail.set_max_width_chars(84)
            inner.pack_start(detail, False, False, 0)

            if finding.get("path"):
                path = Gtk.Label(label=finding["path"], xalign=0.0)
                path.set_selectable(True)
                path.set_line_wrap(True)
                path.set_max_width_chars(84)
                path.get_style_context().add_class("path-text")
                inner.pack_start(path, False, False, 0)

            return card

        def _build_note(self):
            note = Gtk.Label(label=UI["note"][self.lang], xalign=0.0)
            note.set_line_wrap(True)
            note.set_max_width_chars(86)
            note.get_style_context().add_class("sub-text")
            inner = Gtk.Box()
            inner.set_margin_top(15); inner.set_margin_bottom(15)
            inner.set_margin_start(20); inner.set_margin_end(20)
            inner.pack_start(note, True, True, 0)
            box = Gtk.Box()
            box.get_style_context().add_class("note-box")
            box.pack_start(inner, True, True, 0)
            return box

        # -- olaylar -----------------------------------------------------------

        def _on_key(self, _widget, event):
            if event.keyval == Gdk.KEY_Escape:
                self.destroy()
                return True
            return False

        def _destroyed(self, _widget):
            if self.cancel is not None:
                self.cancel.set()
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

        def on_open_device(self, _button):
            root = self.result.get("root")
            if not self._device_present():
                self.status.set_text(UI["gone"][self.lang])
                return
            try:
                subprocess.Popen(["xdg-open", root])
            except OSError:
                pass

        def on_open_path(self, _button, path):
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            if not os.path.isdir(folder):
                self.status.set_text(UI["gone"][self.lang])
                return
            try:
                subprocess.Popen(["xdg-open", folder])
            except OSError:
                pass

        def on_rescan(self, _button):
            """Ayni pencerede yeniden tarar; yeni pencere ACMAZ."""
            if self.scan_thread and self.scan_thread.is_alive():
                return
            root = self.result.get("root")
            if not self._device_present():
                self.status.set_text(UI["gone"][self.lang])
                return

            self.cancel = threading.Event()
            self.rescan_btn.set_sensitive(False)
            self.save_btn.set_sensitive(False)
            self.status.set_text(UI["scanning"][self.lang])
            self.spinner.start()

            def worker():
                fresh = enrich(scan_path(root, self.cancel), root)
                GLib.idle_add(self._scan_done, fresh)

            self.scan_thread = threading.Thread(target=worker, daemon=True)
            self.scan_thread.start()

        def _scan_done(self, fresh):
            self.spinner.stop()
            self.rescan_btn.set_sensitive(True)
            self.save_btn.set_sensitive(True)
            self.status.set_text("")
            if not fresh["stats"].get("cancelled"):
                self.result = fresh
                self.refresh()
            return False

        def on_save(self, _button):
            path = os.path.join(
                GLib.get_home_dir(),
                time.strftime("carotos-usb-%Y%m%d-%H%M.txt"))
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(build_report(self.result, self.lang))
                self.status.set_text(UI["saved"][self.lang].format(path=path))
            except OSError:
                self.status.set_text(UI["save_failed"][self.lang])

        # -- tema --------------------------------------------------------------

        def apply_theme(self):
            if self.theme == "dark":
                bg = "#1f2325"; head = "#2b2f31"; fg = "#e6e6e6"; sub = "#9aa4a8"
                card = "#282d2f"; border = "#363c3e"; note = "#2c3134"
                btn = "#343a3c"; btn_h = "#3f4649"; bd = "#454b4e"; mono = "#8fd6c4"
            else:
                bg = "#f2f4f5"; head = "#e4e7e9"; fg = "#1f2325"; sub = "#5c666a"
                card = "#ffffff"; border = "#dde2e4"; note = "#eef1f2"
                btn = "#ffffff"; btn_h = "#eef0f1"; bd = "#c3c8ca"; mono = "#1f5f52"

            Gtk.Settings.get_default().set_property(
                "gtk-application-prefer-dark-theme", self.theme == "dark")

            css = f"""
            window {{ background-color: {bg}; color: {fg}; }}
            label {{ color: {fg}; }}
            .header {{ background-color: {head}; }}
            .big-title {{ font-size: 142%; font-weight: bold; }}
            .title-ok {{ color: {C_OK}; }}
            .title-high {{ color: {C_HIGH}; }}
            .title-med {{ color: {C_MED}; }}
            .title-low {{ color: {sub}; }}
            .sub-text {{ color: {sub}; font-size: 92%; }}
            .warn-text {{ color: {C_MED}; font-size: 92%; }}
            .path-text {{ font-family: monospace; font-size: 88%; color: {mono}; }}
            .card {{
                background-color: {card}; border: 1px solid {border};
                border-radius: 8px;
            }}
            .card-title {{ font-weight: bold; font-size: 106%; }}
            .badge {{
                color: #ffffff; font-size: 78%; font-weight: bold;
                border-radius: 4px; padding: 3px 8px;
            }}
            .badge-high {{ background-color: {C_HIGH}; }}
            .badge-med {{ background-color: {C_MED}; }}
            .badge-low {{ background-color: {C_LOW}; }}
            .band-ok {{ background-color: {C_OK}; border-radius: 2px; }}
            .band-high {{ background-color: {C_HIGH}; border-radius: 2px; }}
            .band-med {{ background-color: {C_MED}; border-radius: 2px; }}
            .band-low {{ background-color: {C_LOW}; border-radius: 2px; }}
            .pill {{
                border-radius: 999px; padding: 3px 13px;
                font-size: 88%; color: #ffffff;
            }}
            .pill-high {{ background-color: {C_HIGH}; }}
            .pill-med {{ background-color: {C_MED}; }}
            .pill-low {{ background-color: {C_LOW}; }}
            .note-box {{
                background-color: {note}; border: 1px solid {border};
                border-left: 3px solid {ACCENT}; border-radius: 8px;
            }}
            button {{
                background-image: none; background-color: {btn}; color: {fg};
                border: 1px solid {bd}; border-radius: 6px; padding: 4px 14px;
            }}
            button label {{ color: {fg}; }}
            button:hover {{ background-color: {btn_h}; }}
            button:disabled label {{ color: {sub}; }}
            button.suggested-action {{
                background-color: {ACCENT}; border-color: {ACCENT}; color: #ffffff;
            }}
            button.suggested-action label {{ color: #ffffff; }}
            separator {{ background-color: {bd}; }}
            """
            self.provider.load_from_data(css.encode())

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
        body = findings[0]["title"]
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
        self.fd = None
        self.snapshot = set()    # bagli aygitlarin son goruntusu

    # -- baslatma ---------------------------------------------------------

    def start(self):
        """Iki mekanizma birlikte kullanilir.

        1) /proc/mounts uzerinde olay izleme — anlik tepki verir.
           DIKKAT: Linux'ta bu dosya, baglama tablosu degistiginde POLLERR
           sinyali gonderir. Bu bir HATA DEGIL, degisiklik haberidir. Ayrica
           sinyalin tekrar gelmesi icin dosyanin yeniden okunmasi gerekir.
        2) Duzenli kontrol — olay izleme cekirdek surumune gore
           calismayabildigi icin yedek olarak her saniye bakilir.
           Maliyeti ihmal edilebilir (kucuk bir dosya okumasi).
        """
        try:
            self.fd = os.open("/proc/mounts", os.O_RDONLY)
        except OSError as exc:
            print(f"/proc/mounts okunamadi: {exc}", file=sys.stderr)
            self.fd = None
        else:
            self._drain()
            channel = GLib.IOChannel.unix_new(self.fd)
            channel.set_encoding(None)
            channel.set_buffered(False)
            GLib.io_add_watch(
                channel, GLib.PRIORITY_DEFAULT,
                GLib.IOCondition.PRI | GLib.IOCondition.ERR |
                GLib.IOCondition.HUP,
                self._on_change)

        self.snapshot = self._snapshot()
        GLib.timeout_add_seconds(1, self._poll)
        return True

    def _drain(self):
        """Bildirimin tekrar tetiklenebilmesi icin dosyayi bastan okur."""
        if self.fd is None:
            return
        try:
            os.lseek(self.fd, 0, os.SEEK_SET)
            while os.read(self.fd, 65536):
                pass
        except OSError:
            pass

    def _snapshot(self):
        return {(e["device"], e["mount"]) for e in mount_entries()}

    def _on_change(self, _channel, _condition):
        # POLLERR burada bir hata degil, degisiklik haberidir.
        self._drain()
        self._schedule()
        return True

    def _poll(self):
        """Olay izleme calismazsa devreye giren yedek yol."""
        current = self._snapshot()
        if current != self.snapshot:
            self.snapshot = current
            self._schedule()
        return True

    def _schedule(self):
        # Bir baglama islemi birden cok olay uretebilir; son olaydan
        # kisa bir sure sonra tek seferde degerlendirilir.
        if self.pending is not None:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(500, self._settled)

    def _settled(self):
        self.pending = None
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
        return False

    # -- tarama -----------------------------------------------------------

    def _handle(self, entry):
        uuid = device_uuid(entry["device"])
        now = time.time()
        if now - self.recent.get(uuid, 0) < COOLDOWN_SECONDS:
            return
        self.recent[uuid] = now

        mount = entry["mount"]

        # Tarama ayri is parcaciginda; masaustu donmasin.
        def worker():
            result = enrich(scan_path(mount), mount)
            GLib.idle_add(self._scan_done, result)

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
