#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CarotOS Karşılama Sihirbazı
İlk açılışta çalışır, CarotOS'u ve Linux'un temellerini tanıtır.

Kullanım:
    carotos-welcome              Normal açılış
    carotos-welcome --autostart  Oturum açılışında (tercih kapalıysa sessizce çıkar)
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

import json
import shutil
import subprocess
import os
import sys

APP_VERSION = "1.1"
APP_CODENAME = "Eggshell"

CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "carotos-welcome")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

IMG_DIR = "/usr/share/carotos/welcome"

# Logo icin sirayla denenecek yollar (ilk bulunan kullanilir)
LOGO_CANDIDATES = [
    os.path.join(IMG_DIR, "logo.png"),
    "/usr/share/icons/carotos/security-panel-icon.png",
    "/usr/share/carotos/login.png",
]


# ---------------------------------------------------------------------------
# Metinler
# ---------------------------------------------------------------------------

UI = {
    "window_title": {"tr": "CarotOS'a Hoş Geldiniz", "en": "Welcome to CarotOS"},
    "back": {"tr": "Geri", "en": "Back"},
    "next": {"tr": "İleri", "en": "Next"},
    "finish": {"tr": "Bitir", "en": "Finish"},
    "dont_show": {
        "tr": "Açılışta bir daha gösterme",
        "en": "Don't show this at startup again",
    },
    "language": {"tr": "Dil", "en": "Language"},
    "theme_light": {"tr": "Açık tema", "en": "Light theme"},
    "theme_dark": {"tr": "Koyu tema", "en": "Dark theme"},
    "image_missing": {
        "tr": "(görsel bulunamadı)",
        "en": "(image not found)",
    },
}


# Sayfa icerigi veri olarak tutulur; boylece metin duzenlemek icin
# arayuz koduna dokunmak gerekmez.
#
# Govde ogeleri:
#   ("p",       {tr, en})                      paragraf
#   ("bullets", [ {tr, en}, ... ])             madde listesi
#   ("pairs",   [ (sol, {tr, en}), ... ])      iki sutunlu tablo
#   ("code",    "metin")                       tek satirlik komut kutusu
#   ("note",    {tr, en})                      vurgulu not kutusu

PAGES = [
    {
        "id": "welcome",
        "hero": True,
        "title": {
            "tr": f"CarotOS {APP_VERSION} \u201c{APP_CODENAME}\u201d",
            "en": f"CarotOS {APP_VERSION} \u201c{APP_CODENAME}\u201d",
        },
        "subtitle": {
            "tr": "Siber güvenlik eğitimi için hazırlanmış Linux dağıtımı",
            "en": "A Linux distribution built for cybersecurity education",
        },
        "body": [
            ("p", {
                "tr": "Bu kısa tanıtım, sisteminizi tanımanıza yardımcı olur. "
                      "Linux'u ilk kez kullanıyorsanız buradaki sayfalar "
                      "başlamanız için yeterlidir.",
                "en": "This short tour will help you get to know your system. "
                      "If this is your first time using Linux, these pages are "
                      "enough to get you started.",
            }),
            ("p", {
                "tr": "İstediğiniz zaman Uygulamalar menüsünden tekrar açabilirsiniz.",
                "en": "You can reopen it any time from the Applications menu.",
            }),
        ],
    },
    {
        "id": "appearance",
        "custom": "appearance",
        "title": {"tr": "Görünüm ve dil", "en": "Appearance and language"},
        "subtitle": {
            "tr": "Sisteminizin görünümünü ve dilini seçin",
            "en": "Choose how your system looks and which language it uses",
        },
    },
    {
        "id": "linux",
        "title": {"tr": "Linux ve dağıtımlar", "en": "Linux and distributions"},
        "subtitle": {
            "tr": "CarotOS nedir, neyin üzerine kurulu?",
            "en": "What CarotOS is, and what it is built on",
        },
        "body": [
            ("p", {
                "tr": "Linux, işletim sisteminin çekirdeğidir. Tek başına kullanılmaz; "
                      "üzerine masaüstü, uygulamalar ve araçlar eklenerek bir "
                      "dağıtım (distro) hâline getirilir.",
                "en": "Linux is the core of the operating system. It is not used on "
                      "its own; a desktop, applications and tools are added on top "
                      "of it to form a distribution (distro).",
            }),
            ("p", {
                "tr": "CarotOS, Debian 13 \u201cTrixie\u201d temel alınarak hazırlanmış bir "
                      "dağıtımdır. Ubuntu, Linux Mint ve Kali Linux da aynı temelden "
                      "türeyen dağıtımlardır. Bu, Debian için yazılmış binlerce "
                      "yazılımın CarotOS üzerinde de çalıştığı anlamına gelir.",
                "en": "CarotOS is a distribution based on Debian 13 \u201cTrixie\u201d. "
                      "Ubuntu, Linux Mint and Kali Linux are also derived from the "
                      "same base. This means the thousands of programs written for "
                      "Debian run on CarotOS as well.",
            }),
            ("pairs", [
                ("Debian 13", {"tr": "Temel sistem", "en": "Base system"}),
                ("Xfce", {"tr": "Masaüstü ortamı", "en": "Desktop environment"}),
                ("APT", {"tr": "Yazılım yöneticisi", "en": "Software manager"}),
            ]),
        ],
    },
    {
        "id": "desktop",
        "title": {"tr": "Masaüstü", "en": "The desktop"},
        "subtitle": {
            "tr": "İki panelli düzen",
            "en": "A two-panel layout",
        },
        "image": "desktop.png",
        "body": [
            ("bullets", [
                {"tr": "Üst panel: Uygulamalar menüsü, saat ve durum simgeleri.",
                 "en": "Top panel: the Applications menu, clock and status icons."},
                {"tr": "Alt yuva: sık kullanılan programlar. Terminal, Güvenlik "
                       "Paneli, tarayıcı ve dosya yöneticisi buradadır.",
                 "en": "Bottom dock: frequently used programs. The terminal, Security "
                       "Panel, browser and file manager live here."},
                {"tr": "Masaüstüne sağ tıklayarak menüye hızlıca ulaşabilirsiniz.",
                 "en": "Right-click the desktop for quick access to the menu."},
            ]),
        ],
    },
    {
        "id": "files",
        "title": {"tr": "Dosya sistemi", "en": "The file system"},
        "subtitle": {
            "tr": "Linux'ta sürücü harfi yoktur; her şey tek bir ağaçtadır",
            "en": "Linux has no drive letters; everything lives in one tree",
        },
        "image": "filesystem.png",
        "body": [
            ("p", {
                "tr": "Windows'taki C: ve D: sürücülerinin yerine Linux'ta tek bir "
                      "kök dizin vardır: /  Diğer her şey onun altındadır.",
                "en": "Instead of C: and D: drives, Linux has a single root "
                      "directory: /  Everything else sits underneath it.",
            }),
            ("pairs", [
                ("/home", {"tr": "Kullanıcı dosyaları. Sizin alanınız burasıdır.",
                           "en": "User files. This is your space."}),
                ("/etc", {"tr": "Sistem ayarları. Metin dosyalarından oluşur.",
                          "en": "System settings, stored as plain text files."}),
                ("/usr", {"tr": "Kurulu programlar ve paylaşılan dosyalar.",
                          "en": "Installed programs and shared files."}),
                ("/var", {"tr": "Değişen veriler: günlük kayıtları, önbellek.",
                          "en": "Changing data: logs and caches."}),
                ("/opt", {"tr": "Ek yazılımlar. Güvenlik Paneli buradadır.",
                          "en": "Extra software. The Security Panel lives here."}),
                ("/boot", {"tr": "Açılış dosyaları. Elle değiştirmeyin.",
                           "en": "Boot files. Do not edit these by hand."}),
            ]),
        ],
    },
    {
        "id": "home",
        "title": {"tr": "Ev klasörünüz", "en": "Your home folder"},
        "subtitle": {
            "tr": "Kişisel dosyalarınızın bulunduğu yer",
            "en": "Where your personal files live",
        },
        "image": "home.png",
        "body": [
            ("p", {
                "tr": "Ev klasörünüz /home altında, kullanıcı adınızla açılır. "
                      "İçindeki klasörler Windows'takilerle aynı işi görür.",
                "en": "Your home folder sits under /home, named after your user "
                      "account. The folders inside serve the same purpose as their "
                      "Windows counterparts.",
            }),
            ("note", {
                "tr": "Adı nokta ile başlayan dosyalar gizlidir; ayar dosyalarıdır. "
                      "Dosya yöneticisinde Ctrl+H ile görünür hâle gelirler.",
                "en": "Files whose names start with a dot are hidden; they hold "
                      "settings. Press Ctrl+H in the file manager to reveal them.",
            }),
        ],
    },
    {
        "id": "software",
        "title": {"tr": "Yazılım kurmak", "en": "Installing software"},
        "subtitle": {
            "tr": "Depolar: güvenli ve merkezî kurulum",
            "en": "Repositories: safe, centralised installation",
        },
        "body": [
            ("p", {
                "tr": "Linux'ta yazılım internetten .exe indirilerek kurulmaz. "
                      "Depolar adı verilen, imzalanmış ve denetlenmiş kaynaklardan "
                      "gelir. Bu, kurduğunuz yazılımın değiştirilmediğini garanti eder.",
                "en": "On Linux you do not install software by downloading .exe files. "
                      "It comes from repositories: signed, reviewed sources. This "
                      "guarantees that what you install has not been tampered with.",
            }),
            ("p", {
                "tr": "Terminalden kurmak için:",
                "en": "To install from the terminal:",
            }),
            ("code", "sudo apt update"),
            ("code", "sudo apt install PAKET_ADI"),
            ("note", {
                "tr": "sudo, bir komutu yönetici yetkisiyle çalıştırır ve kendi "
                      "parolanızı sorar. Bu sistemde root hesabı kapalıdır; "
                      "yönetici işlemleri sudo üzerinden yapılır.",
                "en": "sudo runs a command with administrator rights and asks for "
                      "your own password. The root account is disabled on this "
                      "system; administrative work goes through sudo.",
            }),
        ],
    },
    {
        "id": "panel",
        "title": {"tr": "CarotOS Güvenlik Paneli", "en": "CarotOS Security Panel"},
        "subtitle": {
            "tr": "Komut satırı bilmeden güvenlik araçlarını kullanın",
            "en": "Use security tools without knowing the command line",
        },
        "image": "panel.png",
        "body": [
            ("p", {
                "tr": "Güvenlik araçları güçlüdür ama komut satırı sözdizimi yeni "
                      "başlayanlar için zordur. Panel, her aracı bir forma dönüştürür: "
                      "alanları doldurursunuz, komut sizin için oluşturulur.",
                "en": "Security tools are powerful, but their command-line syntax is "
                      "hard for beginners. The panel turns each tool into a form: you "
                      "fill in the fields and the command is built for you.",
            }),
            ("bullets", [
                {"tr": "Her araç için ne işe yaradığı, ne zaman kullanıldığı ve "
                       "örnek bir kullanım açıklanır.",
                 "en": "Each tool explains what it does, when to use it, and shows "
                       "an example."},
                {"tr": "Çıktı canlı olarak akar; uzun taramalarda arayüz donmaz.",
                 "en": "Output streams live; the interface stays responsive during "
                       "long scans."},
                {"tr": "Yetki gerektiren araçlar için \u201cRoot ile çalıştır\u201d seçeneği "
                       "vardır.",
                 "en": "A \u201cRun as root\u201d option is available for tools that need "
                       "elevated rights."},
                {"tr": "Dil, tema ve güvenlik duvarı ayarları Ayarlar sekmesindedir.",
                 "en": "Language, theme and firewall settings are in the Settings tab."},
            ]),
        ],
    },
    {
        "id": "tools",
        "title": {"tr": "Kurulu güvenlik araçları", "en": "Installed security tools"},
        "subtitle": {
            "tr": "On araç, hepsi panel üzerinden kullanılabilir",
            "en": "Ten tools, all usable through the panel",
        },
        "body": [
            ("grid", [
                ("nmap", {"tr": "Ağdaki cihazları ve açık portları keşfeder.",
                          "en": "Discovers devices and open ports on a network."}),
                ("tcpdump", {"tr": "Ağ trafiğini komut satırından yakalar.",
                             "en": "Captures network traffic from the command line."}),
                ("tshark", {"tr": "Yakalanan trafiği çözümler ve okunur hâle getirir.",
                            "en": "Analyses captured traffic and makes it readable."}),
                ("aircrack-ng", {"tr": "Kablosuz ağ güvenliğini sınar.",
                                 "en": "Tests wireless network security."}),
                ("nikto", {"tr": "Web sunucularında bilinen zafiyetleri tarar.",
                           "en": "Scans web servers for known weaknesses."}),
                ("sqlmap", {"tr": "SQL enjeksiyonu açıklarını tespit eder.",
                            "en": "Detects SQL injection vulnerabilities."}),
                ("john", {"tr": "Parola karmalarının gücünü sınar.",
                          "en": "Tests the strength of password hashes."}),
                ("hydra", {"tr": "Oturum açma servislerinin dayanıklılığını ölçer.",
                           "en": "Measures how well login services resist guessing."}),
                ("ufw", {"tr": "Güvenlik duvarını yönetir.",
                         "en": "Manages the firewall."}),
                ("fail2ban", {"tr": "Tekrarlayan başarısız girişleri engeller.",
                              "en": "Blocks repeated failed login attempts."}),
            ]),
            ("note", {
                "tr": "Bu araçlar yalnızca kendi sisteminizde veya izin aldığınız "
                      "sistemlerde kullanılmalıdır. İzinsiz tarama ve test yapmak "
                      "birçok ülkede suçtur.",
                "en": "These tools must only be used on your own systems or on "
                      "systems you have permission to test. Unauthorised scanning "
                      "is a criminal offence in many countries.",
            }),
        ],
    },
    {
        "id": "poligon",
        "title": {"tr": "CarotOS Poligon", "en": "CarotOS Poligon"},
        "subtitle": {
            "tr": "Öğrendiğiniz araçları güvenli bir ortamda pratik edin",
            "en": "Practice what you've learned in a safe environment",
        },
        "image": "poligon.png",
        "body": [
            ("p", {
                "tr": "Poligon, izole bir ortamda gerçek görevlerle pratik yapmanızı "
                      "sağlayan bir öğrenci ve öğretmen uygulaması çiftidir. Hiçbir "
                      "görev internete ya da başka bir sisteme erişim gerektirmez; "
                      "her şey kendi bilgisayarınızda kalır.",
                "en": "Poligon is a student/teacher application pair for practicing "
                      "with real tasks in an isolated environment. No task requires "
                      "access to the internet or another system; everything stays "
                      "on your own machine.",
            }),
            ("bullets", [
                {"tr": "Bireysel pratik: öğretmene gerek yok, rastgele bir görevle "
                       "hemen başlayıp kendi hızınızda ilerlersiniz.",
                 "en": "Individual practice: no teacher needed, start with a "
                       "random task right away and go at your own pace."},
                {"tr": "Sınıf modu: öğretmenin verdiği oda kodu ve şifreyle "
                       "katılırsınız, sınıfla birlikte ilerlersiniz.",
                 "en": "Class mode: join with the room code and password your "
                       "teacher gives you, and progress along with the class."},
                {"tr": "hydra, nmap, john, sqlmap ve tshark ile saldırı; ufw ve "
                       "fail2ban ile savunma görevleri bulunur.",
                 "en": "Offense tasks with hydra, nmap, john, sqlmap and tshark; "
                       "defense tasks with ufw and fail2ban."},
            ]),
        ],
    },
    {
        "id": "terminal",
        "title": {"tr": "Terminale ilk adım", "en": "First steps in the terminal"},
        "subtitle": {
            "tr": "Bilmeniz yeterli olan birkaç komut",
            "en": "A handful of commands is enough to start",
        },
        "body": [
            ("pairs", [
                ("pwd", {"tr": "Hangi klasörde olduğunuzu yazar.",
                         "en": "Prints the folder you are currently in."}),
                ("ls", {"tr": "Bulunduğunuz klasörün içeriğini listeler.",
                        "en": "Lists the contents of the current folder."}),
                ("cd klasor", {"tr": "Başka bir klasöre geçer.",
                               "en": "Moves into another folder."}),
                ("cat dosya", {"tr": "Bir metin dosyasının içeriğini gösterir.",
                               "en": "Shows the contents of a text file."}),
                ("man komut", {"tr": "Bir komutun kılavuz sayfasını açar. Çıkmak için q.",
                               "en": "Opens a command's manual page. Press q to exit."}),
                ("ip a", {"tr": "Ağ arayüzlerinizi ve IP adresinizi gösterir.",
                          "en": "Shows your network interfaces and IP address."}),
            ]),
            ("note", {
                "tr": "Tab tuşu dosya ve komut adlarını tamamlar. Yazım hatalarını "
                      "önlemenin en kolay yolu budur.",
                "en": "The Tab key completes file and command names. It is the "
                      "easiest way to avoid typing mistakes.",
            }),
        ],
    },
    {
        "id": "resources",
        "title": {"tr": "Daha fazlası", "en": "Going further"},
        "subtitle": {
            "tr": "Öğrenmeye devam etmek için kaynaklar",
            "en": "Where to keep learning",
        },
        "body": [
            ("links", [
                ("carotos.org", "https://www.carotos.org/",
                 {"tr": "Belgeler, indirmeler ve sürüm notları.",
                  "en": "Documentation, downloads and release notes."}),
                ("debian.org/doc", "https://www.debian.org/doc/",
                 {"tr": "Debian kullanıcı el kitabı.",
                  "en": "The Debian user handbook."}),
                ("nmap.org/book", "https://nmap.org/book/",
                 {"tr": "Ağ taramanın kaynak kitabı, ücretsiz okunabilir.",
                  "en": "The reference book on network scanning, free to read."}),
            ]),
            ("pairs", [
                ("man komut", {"tr": "Her komutun kendi kılavuzu sistemde kuruludur. "
                                     "Çıkmak için q tuşuna basın.",
                               "en": "Every command ships its own manual on the "
                                     "system. Press q to exit."}),
            ]),
            ("p", {
                "tr": "CarotOS açık kaynaklıdır. Hata bildirebilir, öneride "
                      "bulunabilir veya katkı verebilirsiniz.",
                "en": "CarotOS is open source. You are welcome to report bugs, "
                      "suggest improvements or contribute.",
            }),
            ("note", {
                "tr": "Bu tanıtımı istediğiniz zaman Uygulamalar menüsünden "
                      "yeniden açabilirsiniz.",
                "en": "You can reopen this tour at any time from the Applications "
                      "menu.",
            }),
        ],
    },
]


# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------

DEFAULTS = {"lang": "tr", "theme": "dark", "show_on_startup": True}

# Sihirbaz ust bandindaki secicilerin yaninda gosterilen aciklama
PICK_TEXTS = {
    "lang_heading": {"tr": "Sistem dili", "en": "System language"},
    "theme_light": {"tr": "Açık Tema", "en": "Light Theme"},
    "theme_dark": {"tr": "Koyu Tema", "en": "Dark Theme"},
    "apply_note": {
        "tr": "Seçimleriniz, sihirbazın sonundaki “Bitir” düğmesine "
              "bastığınızda uygulanır. Dil değişikliği için oturumu kapatıp "
              "yeniden açmanız gerekir.",
        "en": "Your choices are applied when you press “Finish” at the end of "
              "this tour. A language change takes effect after you log out and "
              "back in.",
    },
}

SCOPE_NOTE = {
    "tr": "Bu seçimler tüm CarotOS uygulamalarına ve masaüstüne uygulanır. "
          "Sistem dili, oturumu kapatıp yeniden açtığınızda değişir.",
    "en": "These choices apply to all CarotOS applications and the desktop. "
          "The session language changes after you log out and back in.",
}
LANG_CHANGED_NOTE = {
    "tr": "Dil değiştirildi. Masaüstünün tamamı için oturumu kapatıp açın.",
    "en": "Language changed. Log out and back in to change the whole desktop.",
}


UI.update(PICK_TEXTS)


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


# ---------------------------------------------------------------------------
# Sistem geneli tercih uygulama
#
# Sihirbazdaki dil ve tema secimi yalnizca bu uygulamayi degil, masaustunu
# ve diger CarotOS uygulamalarini da etkiler.
# ---------------------------------------------------------------------------

# Diger CarotOS uygulamalarinin ayar dosyalari. Sihirbazda yapilan secim
# bunlara da yazilir; boylece dort uygulama ayni gorunumu paylasir ve
# uygulamalarin kodunda degisiklik gerekmez.
SIBLING_CONFIGS = [
    ("carotos-panel", "settings.json"),
    ("carotos-health", "settings.json"),
    ("carotos-usb", "settings.json"),
]

# Koyu ve acik tema adaylari — sistemde bulunan ilki kullanilir.
DARK_THEMES = ["Adwaita-dark", "Greybird-dark", "Materia-dark",
               "Arc-Dark", "Numix-Dark", "Adwaita"]
LIGHT_THEMES = ["Adwaita", "Greybird", "Arc", "Default"]

LOCALE_FOR_LANG = {"tr": "tr_TR.UTF-8", "en": "en_US.UTF-8"}


def available_theme(candidates):
    """Sistemde kurulu ilk temayi dondurur."""
    roots = ["/usr/share/themes",
             os.path.join(GLib.get_home_dir(), ".themes")]
    for name in candidates:
        for root in roots:
            if os.path.isdir(os.path.join(root, name)):
                return name
    return None


def xfconf(channel, prop, value):
    """Xfce ayarini degistirir. Xfce disinda calisiyorsa sessizce gecer."""
    if not shutil.which("xfconf-query"):
        return False
    try:
        subprocess.run(["xfconf-query", "-c", channel, "-p", prop,
                        "-s", value],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=8)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def has_xfwm_variant(name):
    """Temanin pencere yoneticisi (xfwm4) bileseni var mi?

    Adwaita-dark gibi bazi temalar yalnizca GTK bileseni tasir. Boyle bir
    temayi xfwm4'e yazmak baslik cubuklarinin bozulmasina yol acar; bu
    yuzden yalnizca gercekten var olan pencere temalari uygulanir.
    """
    roots = ["/usr/share/themes",
             os.path.join(GLib.get_home_dir(), ".themes")]
    return any(os.path.isdir(os.path.join(root, name, "xfwm4"))
               for root in roots)


def apply_desktop_theme(theme):
    """Masaustu temasini degistirir (kullanici duzeyinde, root gerekmez)."""
    name = available_theme(DARK_THEMES if theme == "dark" else LIGHT_THEMES)
    if not name:
        return False
    ok = xfconf("xsettings", "/Net/ThemeName", name)

    # Pencere temasi ayri bir bilesendir; yalnizca varsa degistirilir.
    if has_xfwm_variant(name):
        xfconf("xfwm4", "/general/theme", name)
    return ok


def apply_sibling_settings(lang, theme):
    """Diger CarotOS uygulamalarinin tercihlerini gunceller.

    Var olan dosyanin diger alanlari korunur; yalnizca dil ve tema yazilir.
    """
    base = GLib.get_user_config_dir()
    for folder, filename in SIBLING_CONFIGS:
        path = os.path.join(base, folder, filename)
        data = {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, ValueError):
            pass
        data["lang"] = lang
        data["theme"] = theme
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except OSError:
            continue


XSESSION_START = "# >>> CarotOS dil ayari >>>"
XSESSION_END = "# <<< CarotOS dil ayari <<<"


def _write_xsessionrc(locale):
    """~/.xsessionrc icine dil degiskenlerini yazar.

    Debian'da X oturumu /etc/X11/Xsession uzerinden baslar ve bu betik
    ~/.xsessionrc dosyasini okur. LightDM'in ~/.dmrc dosyasini artik
    okumadigi sistemlerde dili degistirmenin en guvenilir kullanici
    duzeyi yoludur.
    """
    path = os.path.join(GLib.get_home_dir(), ".xsessionrc")
    language = locale.split(".")[0]
    block = "\n".join([
        XSESSION_START,
        f"export LANG={locale}",
        f"export LANGUAGE={language}",
        f"export LC_MESSAGES={locale}",
        XSESSION_END,
    ])

    existing = ""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            existing = fh.read()
    except OSError:
        pass

    if XSESSION_START in existing and XSESSION_END in existing:
        before = existing.split(XSESSION_START)[0]
        after = existing.split(XSESSION_END, 1)[1]
        content = before + block + after
    else:
        content = (existing.rstrip("\n") + "\n\n" if existing.strip()
                   else "") + block + "\n"

    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.chmod(path, 0o644)
        return True
    except OSError:
        return False


def _write_dmrc(locale):
    """LightDM'in eski yolu. Zararsiz, okuyan sistemlerde ise yarar."""
    path = os.path.join(GLib.get_home_dir(), ".dmrc")
    session = None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip().lower().startswith("session="):
                    session = line.split("=", 1)[1].strip()
    except OSError:
        pass
    lines = ["[Desktop]"]
    if session:
        lines.append(f"Session={session}")
    lines.append(f"Language={locale}")
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return True
    except OSError:
        return False


def _set_accountsservice_language(locale):
    """AccountsService uzerinden dili bildirir (varsa)."""
    try:
        from gi.repository import Gio
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        manager = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            "org.freedesktop.Accounts", "/org/freedesktop/Accounts",
            "org.freedesktop.Accounts", None)
        result = manager.call_sync(
            "FindUserByName", GLib.Variant("(s)", (GLib.get_user_name(),)),
            Gio.DBusCallFlags.NONE, 5000, None)
        path = result.unpack()[0]
        user = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            "org.freedesktop.Accounts", path,
            "org.freedesktop.Accounts.User", None)
        user.call_sync("SetLanguage", GLib.Variant("(s)", (locale,)),
                       Gio.DBusCallFlags.NONE, 5000, None)
        return True
    except Exception:
        return False


def apply_session_language(lang):
    """Oturum dilini kullanici duzeyinde ayarlar.

    Uc yol birden denenir, cunku hangisinin gecerli oldugu sisteme gore
    degisir: ~/.xsessionrc (Debian X oturumu her zaman okur), ~/.dmrc
    (eski LightDM yolu) ve AccountsService (modern yol).

    Sistem geneli /etc/default/locale DEGISTIRILMEZ: root ister ve
    makinedeki TUM kullanicilari etkiler — okul ortaminda istenmez.
    """
    locale = LOCALE_FOR_LANG.get(lang)
    if not locale:
        return False
    ok = _write_xsessionrc(locale)
    _write_dmrc(locale)
    _set_accountsservice_language(locale)
    return ok


def find_logo():
    for path in LOGO_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


# ---------------------------------------------------------------------------
# Pencere
# ---------------------------------------------------------------------------

class WelcomeWindow(Gtk.Window):

    ACCENT = "#87979B"

    def __init__(self, settings):
        super().__init__(title=UI["window_title"][settings["lang"]])

        self.settings = settings
        self.lang = settings["lang"]
        self.theme = settings["theme"]
        self.index = 0

        self.set_default_size(940, 660)
        self.set_size_request(820, 580)
        self.set_position(Gtk.WindowPosition.CENTER)
        logo = find_logo()
        if logo:
            try:
                self.set_icon_from_file(logo)
            except GLib.Error:
                pass
        self.connect("destroy", self.on_destroy)

        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)

        root.pack_start(self.build_header(), False, False, 0)
        root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                        False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(180)
        root.pack_start(self.stack, True, True, 0)

        root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                        False, False, 0)
        root.pack_start(self.build_footer(), False, False, 0)

        self.build_pages()
        self.apply_theme()
        self.refresh()

    # -- ust bant ----------------------------------------------------------

    def build_header(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.get_style_context().add_class("header")
        box.set_border_width(14)

        # Ust bantta logo yok: pencere kenarindaki simgeyle tekrar oluyordu.
        wordmark = Gtk.Label(label="CarotOS", xalign=0.0)
        wordmark.get_style_context().add_class("wordmark")
        box.pack_start(wordmark, False, False, 0)

        version = Gtk.Label(label=f"{APP_VERSION} \u00b7 {APP_CODENAME}", xalign=0.0)
        version.get_style_context().add_class("version-tag")
        version.set_valign(Gtk.Align.CENTER)
        box.pack_start(version, False, False, 0)

        # Sag taraf: dil ve tema secicileri
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append("tr", "Türkçe")
        self.lang_combo.append("en", "English")
        self.lang_combo.set_active_id(self.lang)
        self.lang_combo.connect("changed", self.on_lang_changed)
        box.pack_end(self.lang_combo, False, False, 0)

        self.theme_btn = Gtk.Button()
        self.theme_btn.connect("clicked", self.on_theme_toggled)
        box.pack_end(self.theme_btn, False, False, 0)

        return box

    # -- alt bant ----------------------------------------------------------

    def build_footer(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_border_width(14)

        self.check = Gtk.CheckButton()
        self.check.set_active(not self.settings["show_on_startup"])
        self.check.connect("toggled", self.on_check_toggled)
        box.pack_start(self.check, False, False, 0)


        self.dots = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.dots.set_halign(Gtk.Align.CENTER)
        self.dots.set_valign(Gtk.Align.CENTER)
        for i in range(len(PAGES)):
            dot = Gtk.Label(label="")
            dot.get_style_context().add_class("dot")
            self.dots.pack_start(dot, False, False, 0)
        box.set_center_widget(self.dots)

        self.next_btn = Gtk.Button()
        self.next_btn.get_style_context().add_class("suggested-action")
        self.next_btn.connect("clicked", self.on_next)
        box.pack_end(self.next_btn, False, False, 0)

        self.back_btn = Gtk.Button()
        self.back_btn.connect("clicked", self.on_back)
        box.pack_end(self.back_btn, False, False, 0)

        return box

    # -- sayfalar ----------------------------------------------------------

    def build_pages(self):
        for page in PAGES:
            self.stack.add_named(self.build_page(page), page["id"])

    def build_page(self, page):
        if page.get("custom") == "appearance":
            return self.build_appearance_page(page)
        return self.build_standard_page(page)

    # -- gorunum ve dil sayfasi --------------------------------------------

    def build_appearance_page(self, page):
        """Tema ve dil secimi. Secimler ANINDA sisteme uygulanmaz;
        sihirbazin sonundaki 'Bitir' dugmesine basildiginda uygulanir."""
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_shadow_type(Gtk.ShadowType.NONE)

        centerer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        centerer.set_halign(Gtk.Align.CENTER)
        scroller.add(centerer)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_border_width(32)
        outer.set_size_request(718, -1)
        centerer.pack_start(outer, False, False, 0)

        title = Gtk.Label(label=page["title"][self.lang])
        title.get_style_context().add_class("page-title")
        title.set_justify(Gtk.Justification.CENTER)
        title.set_line_wrap(True)
        outer.pack_start(title, False, False, 0)

        rule = Gtk.Box()
        rule.get_style_context().add_class("title-rule")
        rule.set_size_request(54, 3)
        rule.set_halign(Gtk.Align.CENTER)
        rule.set_margin_top(11)
        outer.pack_start(rule, False, False, 0)

        subtitle = Gtk.Label(label=page["subtitle"][self.lang])
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.set_line_wrap(True)
        subtitle.set_margin_top(13)
        outer.pack_start(subtitle, False, False, 0)

        # --- tema kartlari ---
        theme_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        theme_row.set_homogeneous(True)
        theme_row.set_margin_top(30)
        outer.pack_start(theme_row, False, False, 0)

        self.theme_cards = {}
        for key in ("light", "dark"):
            card = self._theme_card(key)
            self.theme_cards[key] = card
            theme_row.pack_start(card["event"], True, True, 0)

        # --- dil secimi ---
        lang_title = Gtk.Label(label=UI["lang_heading"][self.lang], xalign=0.0)
        lang_title.get_style_context().add_class("section-title")
        lang_title.set_margin_top(34)
        outer.pack_start(lang_title, False, False, 0)

        lang_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        lang_row.set_homogeneous(True)
        lang_row.set_margin_top(14)
        outer.pack_start(lang_row, False, False, 0)

        self.lang_cards = {}
        for code, name, sub in (("tr", "Türkçe", "Turkish"),
                                ("en", "English", "İngilizce")):
            card = self._lang_card(code, name, sub)
            self.lang_cards[code] = card
            lang_row.pack_start(card["event"], True, True, 0)

        # --- aciklama ---
        note = Gtk.Label(label=UI["apply_note"][self.lang], xalign=0.0)
        note.get_style_context().add_class("body-text")
        note.set_line_wrap(True)
        note.set_justify(Gtk.Justification.CENTER)
        note.set_halign(Gtk.Align.CENTER)
        inner = Gtk.Box()
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        inner.set_margin_start(20); inner.set_margin_end(20)
        inner.pack_start(note, True, True, 0)
        note_box = Gtk.Box()
        note_box.get_style_context().add_class("note")
        note_box.set_margin_top(30)
        note_box.pack_start(inner, True, True, 0)
        outer.pack_start(note_box, False, False, 0)

        self._sync_selection()
        return scroller

    def _theme_card(self, key):
        """Kucuk bir pencere onizlemesi tasiyan secilebilir kart."""
        dark = key == "dark"
        event = Gtk.EventBox()
        event.connect("button-press-event", self._on_theme_pick, key)
        event.set_above_child(False)

        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        frame.get_style_context().add_class("pick-card")
        event.add(frame)

        head = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        head.set_margin_top(14); head.set_margin_bottom(12)
        name = Gtk.Label(label=UI["theme_dark" if dark else "theme_light"][self.lang])
        name.get_style_context().add_class("pick-title")
        head.pack_start(name, False, False, 0)
        sub = Gtk.Label(label="Dark Theme" if dark else "Light Theme")
        sub.get_style_context().add_class("pick-sub")
        head.pack_start(sub, False, False, 0)
        frame.pack_start(head, False, False, 0)

        # Onizleme: sahte bir pencere
        preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        preview.get_style_context().add_class(
            "preview-dark" if dark else "preview-light")
        preview.set_size_request(-1, 132)
        preview.set_margin_start(16); preview.set_margin_end(16)
        preview.set_margin_bottom(16)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        bar.get_style_context().add_class(
            "preview-bar-dark" if dark else "preview-bar-light")
        bar.set_size_request(-1, 22)
        for _ in range(3):
            dot = Gtk.Box()
            dot.get_style_context().add_class("preview-dot")
            dot.set_size_request(7, 7)
            dot.set_valign(Gtk.Align.CENTER)
            bar.pack_start(dot, False, False, 0)
        bar.set_margin_bottom(10)
        preview.pack_start(bar, False, False, 0)

        for width in (150, 110, 132):
            line = Gtk.Box()
            line.get_style_context().add_class(
                "preview-line-dark" if dark else "preview-line-light")
            line.set_size_request(width, 8)
            line.set_margin_start(12)
            line.set_margin_bottom(9)
            preview.pack_start(line, False, False, 0)

        chip = Gtk.Box()
        chip.get_style_context().add_class("preview-chip")
        chip.set_size_request(64, 14)
        chip.set_margin_start(12)
        preview.pack_start(chip, False, False, 0)

        frame.pack_start(preview, False, False, 0)
        return {"event": event, "frame": frame}

    def _lang_card(self, code, name, sub_text):
        event = Gtk.EventBox()
        event.connect("button-press-event", self._on_lang_pick, code)

        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        frame.get_style_context().add_class("pick-card")
        event.add(frame)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        inner.set_margin_top(16); inner.set_margin_bottom(16)
        label = Gtk.Label(label=name)
        label.get_style_context().add_class("pick-title")
        inner.pack_start(label, False, False, 0)
        sub = Gtk.Label(label=sub_text)
        sub.get_style_context().add_class("pick-sub")
        inner.pack_start(sub, False, False, 0)
        frame.pack_start(inner, True, True, 0)
        return {"event": event, "frame": frame}

    def _sync_selection(self):
        """Secili karta cerceve verir."""
        for key, card in getattr(self, "theme_cards", {}).items():
            ctx = card["frame"].get_style_context()
            if key == self.theme:
                ctx.add_class("pick-selected")
            else:
                ctx.remove_class("pick-selected")
        for code, card in getattr(self, "lang_cards", {}).items():
            ctx = card["frame"].get_style_context()
            if code == self.lang:
                ctx.add_class("pick-selected")
            else:
                ctx.remove_class("pick-selected")

    def _on_theme_pick(self, _widget, _event, key):
        if key == self.theme:
            return True
        self.theme = key
        self.settings["theme"] = key
        save_settings(self.settings)
        # Sihirbazin kendi gorunumu hemen degisir; sisteme uygulama
        # "Bitir" dugmesinde yapilir.
        self.apply_theme()
        self.refresh()
        return True

    def _on_lang_pick(self, _widget, _event, code):
        if code == self.lang:
            return True
        self.lang = code
        self.settings["lang"] = code
        save_settings(self.settings)
        self.rebuild()
        return True

    def build_standard_page(self, page):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_shadow_type(Gtk.ShadowType.NONE)

        # Icerik sabit genislikte ortalanir; genis ekranda satirlar
        # okunamayacak kadar uzamaz.
        centerer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        centerer.set_halign(Gtk.Align.CENTER)
        scroller.add(centerer)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_border_width(32)
        outer.set_size_request(718, -1)
        if page.get("hero"):
            outer.set_valign(Gtk.Align.CENTER)
        centerer.pack_start(outer, False, False, 0)

        # --- baslik blogu (her sayfada ortali) ---
        if page.get("hero"):
            logo = find_logo()
            if logo:
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo, 104, 104, True)
                    img = Gtk.Image.new_from_pixbuf(pb)
                    img.set_halign(Gtk.Align.CENTER)
                    outer.pack_start(img, False, False, 10)
                except GLib.Error:
                    pass

        title = Gtk.Label(label=page["title"][self.lang])
        title.get_style_context().add_class("page-title")
        title.set_justify(Gtk.Justification.CENTER)
        title.set_line_wrap(True)
        title.set_halign(Gtk.Align.CENTER)
        outer.pack_start(title, False, False, 0)

        rule = Gtk.Box()
        rule.get_style_context().add_class("title-rule")
        rule.set_size_request(46, 3)
        rule.set_halign(Gtk.Align.CENTER)
        outer.pack_start(rule, False, False, 12)

        subtitle = Gtk.Label(label=page["subtitle"][self.lang])
        subtitle.get_style_context().add_class("page-subtitle")
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.set_line_wrap(True)
        subtitle.set_max_width_chars(64)
        subtitle.set_halign(Gtk.Align.CENTER)
        outer.pack_start(subtitle, False, False, 0)

        # --- govde ---
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        body.set_margin_top(24)
        outer.pack_start(body, False, False, 0)

        if page.get("image"):
            body.pack_start(self.build_image(page["image"]), False, False, 0)

        for kind, payload in page["body"]:
            widget = self.build_block(kind, payload)
            if widget is not None:
                body.pack_start(widget, False, False, 0)

        return scroller

    @staticmethod
    def card(child, style="card"):
        """Icerigi hafif acik zeminli bir kutuya yerlestirir."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class(style)
        box.set_border_width(20)
        box.pack_start(child, True, True, 0)
        return box

    def build_image(self, filename):
        path = os.path.join(IMG_DIR, filename)
        frame = Gtk.Frame()
        frame.get_style_context().add_class("shot-frame")
        frame.set_halign(Gtk.Align.CENTER)
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 678, 440, True)
            frame.add(Gtk.Image.new_from_pixbuf(pb))
        except GLib.Error:
            placeholder = Gtk.Label(label=UI["image_missing"][self.lang])
            placeholder.get_style_context().add_class("page-subtitle")
            placeholder.set_size_request(678, 175)
            frame.add(placeholder)
        return frame

    def build_block(self, kind, payload):
        if kind == "p":
            label = Gtk.Label(label=payload[self.lang], xalign=0.0)
            label.set_line_wrap(True)
            label.set_max_width_chars(70)
            label.get_style_context().add_class("body-text")
            return self.card(label)

        if kind == "note":
            inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            mark = Gtk.Label(label="!", xalign=0.5)
            mark.get_style_context().add_class("note-mark")
            mark.set_valign(Gtk.Align.START)
            inner.pack_start(mark, False, False, 0)
            label = Gtk.Label(label=payload[self.lang], xalign=0.0)
            label.set_line_wrap(True)
            label.set_max_width_chars(66)
            label.get_style_context().add_class("note-text")
            inner.pack_start(label, True, True, 0)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.get_style_context().add_class("note-box")
            box.set_border_width(16)
            box.pack_start(inner, True, True, 0)
            return box

        if kind == "code":
            label = Gtk.Label(label=payload, xalign=0.0)
            label.set_selectable(True)
            label.get_style_context().add_class("code-text")
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.get_style_context().add_class("code-box")
            box.set_border_width(11)
            box.pack_start(label, True, True, 0)
            return box

        if kind == "bullets":
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11)
            for item in payload:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
                marker = Gtk.Label(label="\u25b8", xalign=0.5)
                marker.get_style_context().add_class("bullet-marker")
                marker.set_valign(Gtk.Align.START)
                row.pack_start(marker, False, False, 0)
                text = Gtk.Label(label=item[self.lang], xalign=0.0)
                text.set_line_wrap(True)
                text.set_max_width_chars(66)
                text.get_style_context().add_class("body-text")
                row.pack_start(text, True, True, 0)
                inner.pack_start(row, False, False, 0)
            return self.card(inner)

        if kind == "pairs":
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            for row_index, (key, value) in enumerate(payload):
                if row_index:
                    sep = Gtk.Box()
                    sep.get_style_context().add_class("row-sep")
                    sep.set_size_request(-1, 1)
                    inner.pack_start(sep, False, False, 10)

                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
                key_label = Gtk.Label(label=key, xalign=0.0)
                key_label.get_style_context().add_class("pair-key")
                key_label.set_valign(Gtk.Align.START)
                key_label.set_size_request(132, -1)
                row.pack_start(key_label, False, False, 0)

                value_label = Gtk.Label(label=value[self.lang], xalign=0.0)
                value_label.set_line_wrap(True)
                value_label.set_max_width_chars(54)
                value_label.get_style_context().add_class("body-text")
                row.pack_start(value_label, True, True, 0)
                inner.pack_start(row, False, False, 0)
            return self.card(inner)

        if kind == "links":
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            for row_index, (text, url, value) in enumerate(payload):
                if row_index:
                    sep = Gtk.Box()
                    sep.get_style_context().add_class("row-sep")
                    sep.set_size_request(-1, 1)
                    inner.pack_start(sep, False, False, 10)

                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)

                link = Gtk.Label(xalign=0.0)
                link.set_markup(
                    f'<a href="{GLib.markup_escape_text(url)}">'
                    f'{GLib.markup_escape_text(text)}</a>')
                link.set_track_visited_links(False)
                link.get_style_context().add_class("link-key")
                link.set_valign(Gtk.Align.START)
                link.set_size_request(140, -1)
                row.pack_start(link, False, False, 0)

                value_label = Gtk.Label(label=value[self.lang], xalign=0.0)
                value_label.set_line_wrap(True)
                value_label.set_max_width_chars(54)
                value_label.get_style_context().add_class("body-text")
                row.pack_start(value_label, True, True, 0)
                inner.pack_start(row, False, False, 0)
            return self.card(inner)

        if kind == "grid":
            # Iki sutunlu kart izgarasi (araclar sayfasi)
            grid = Gtk.Grid()
            grid.set_column_spacing(12)
            grid.set_row_spacing(12)
            grid.set_column_homogeneous(True)
            for i, (key, value) in enumerate(payload):
                cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                cell.get_style_context().add_class("tile")
                cell.set_border_width(13)

                name = Gtk.Label(label=key, xalign=0.0)
                name.get_style_context().add_class("tile-title")
                cell.pack_start(name, False, False, 0)

                desc = Gtk.Label(label=value[self.lang], xalign=0.0)
                desc.set_line_wrap(True)
                desc.set_max_width_chars(32)
                desc.set_valign(Gtk.Align.START)
                desc.get_style_context().add_class("tile-text")
                cell.pack_start(desc, True, True, 0)

                grid.attach(cell, i % 2, i // 2, 1, 1)
            return grid

        return None

    # -- durum yenileme ----------------------------------------------------

    def refresh(self):
        page = PAGES[self.index]
        self.stack.set_visible_child_name(page["id"])

        self.back_btn.set_label(UI["back"][self.lang])
        self.back_btn.set_sensitive(self.index > 0)

        last = self.index == len(PAGES) - 1
        self.next_btn.set_label(
            UI["finish"][self.lang] if last else UI["next"][self.lang])

        self.check.set_label(UI["dont_show"][self.lang])
        self.theme_btn.set_label(
            UI["theme_light"][self.lang] if self.theme == "dark"
            else UI["theme_dark"][self.lang])
        self.set_title(UI["window_title"][self.lang])

        self._sync_selection()

        for i, dot in enumerate(self.dots.get_children()):
            ctx = dot.get_style_context()
            if i == self.index:
                ctx.add_class("dot-active")
            else:
                ctx.remove_class("dot-active")

    def rebuild(self):
        """Dil degistiginde sayfalar yeniden olusturulur.

        Yigin gecisi sirasinda kapatilir: sayfalar silinip yeniden
        eklendiginde GTK bunu bir sayfa gecisi sanip kaydirma animasyonu
        oynatiyor, oysa kullanici ayni sayfada duruyor.
        """
        previous = self.stack.get_transition_type()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)

        for child in self.stack.get_children():
            self.stack.remove(child)
        self.build_pages()
        self.stack.show_all()
        self.refresh()

        # Gecis tipini, arayuz yerlestikten sonra geri al; hemen geri
        # alinirsa animasyon yine tetikleniyor.
        def restore():
            self.stack.set_transition_type(previous)
            return False
        GLib.idle_add(restore)

    # -- olaylar -----------------------------------------------------------

    def on_next(self, _button):
        if self.index < len(PAGES) - 1:
            self.stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT)
            self.index += 1
            self.refresh()
        else:
            self.apply_choices()
            self.close()

    def apply_choices(self):
        """Sihirbaz kapanirken secimleri sisteme uygular."""
        apply_desktop_theme(self.theme)
        apply_sibling_settings(self.lang, self.theme)
        apply_session_language(self.lang)

    def on_back(self, _button):
        if self.index > 0:
            self.stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_RIGHT)
            self.index -= 1
            self.refresh()

    def on_lang_changed(self, combo):
        chosen = combo.get_active_id()
        if not chosen or chosen == self.lang:
            return
        self.lang = chosen
        self.settings["lang"] = chosen
        save_settings(self.settings)

        # Sisteme uygulama "Bitir" dugmesinde yapilir.
        self.rebuild()

    def on_theme_toggled(self, _button):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings["theme"] = self.theme
        save_settings(self.settings)

        # Yalnizca sihirbazin gorunumu; sisteme uygulama "Bitir"de.
        self.apply_theme()
        self.refresh()

    def on_check_toggled(self, check):
        self.settings["show_on_startup"] = not check.get_active()
        save_settings(self.settings)

    def on_destroy(self, _widget):
        save_settings(self.settings)
        Gtk.main_quit()

    # -- tema --------------------------------------------------------------

    def apply_theme(self):
        if self.theme == "dark":
            bg = "#1f2325"; header = "#2b2f31"; fg = "#e6e6e6"
            sub = "#9aa4a8"; field = "#2b2f31"
            card = "#282d2f"; card_border = "#363c3e"
            note_bg = "#2c3134"; row_sep = "#363c3e"
            btn_bg = "#343a3c"; btn_hover = "#3f4649"; border = "#454b4e"
            dot = "#4a5154"; code_fg = "#8fd6c4"; tile = "#2c3133"
        else:
            bg = "#f2f4f5"; header = "#e4e7e9"; fg = "#1f2325"
            sub = "#5c666a"; field = "#ffffff"
            card = "#ffffff"; card_border = "#dde2e4"
            note_bg = "#eef1f2"; row_sep = "#e6eaeb"
            btn_bg = "#ffffff"; btn_hover = "#eef0f1"; border = "#c3c8ca"
            dot = "#c3c8ca"; code_fg = "#1f5f52"; tile = "#ffffff"

        Gtk.Settings.get_default().set_property(
            "gtk-application-prefer-dark-theme", self.theme == "dark")

        css = f"""
        window {{ background-color: {bg}; color: {fg}; }}
        label {{ color: {fg}; }}

        .header {{ background-color: {header}; }}
        .wordmark {{ font-size: 132%; font-weight: bold; letter-spacing: 1px; }}
        .version-tag {{ color: {sub}; font-size: 88%; }}

        .page-title {{ font-size: 176%; font-weight: bold; }}
        .title-rule {{ background-color: {self.ACCENT}; border-radius: 2px; }}
        .page-subtitle {{ color: {sub}; font-size: 106%; }}
        .body-text {{ font-size: 100%; }}

        .card {{
            background-color: {card};
            border: 1px solid {card_border};
            border-radius: 8px;
        }}
        .row-sep {{ background-color: {row_sep}; }}
        .pair-key {{ font-weight: bold; color: {self.ACCENT}; }}
        .link-key {{ font-weight: bold; }}
        .link-key a {{ color: {self.ACCENT}; text-decoration: none; }}
        .link-key a:hover {{ text-decoration: underline; }}
        .bullet-marker {{ color: {self.ACCENT}; font-size: 100%; }}

        .tile {{
            background-color: {tile};
            border: 1px solid {card_border};
            border-radius: 8px;
        }}
        .tile-title {{ font-weight: bold; color: {self.ACCENT}; font-size: 103%; }}
        .tile-text {{ color: {sub}; font-size: 92%; }}

        .note-box {{
            background-color: {note_bg};
            border: 1px solid {card_border};
            border-left: 3px solid {self.ACCENT};
            border-radius: 8px;
        }}
        .note-mark {{
            color: #ffffff;
            background-color: {self.ACCENT};
            font-weight: bold;
            font-size: 88%;
            border-radius: 999px;
            min-width: 19px; min-height: 19px;
        }}
        .note-text {{ color: {sub}; font-size: 95%; }}

        .code-box {{
            background-color: {field};
            border: 1px solid {border};
            border-radius: 6px;
        }}
        .code-text {{ font-family: monospace; color: {code_fg}; }}

        .shot-frame {{
            border: 1px solid {card_border};
            border-radius: 8px;
            background-color: {card};
        }}

        .scope-note {{ color: {sub}; font-size: 84%; }}
        .pick-card {{
            background-color: {card}; border: 2px solid {card_border};
            border-radius: 10px;
        }}
        .pick-card:hover {{ border-color: {sub}; }}
        .pick-selected {{ border-color: {self.ACCENT}; }}
        .pick-title {{ font-size: 108%; font-weight: bold; }}
        .pick-sub {{ color: {sub}; font-size: 85%; }}
        .section-title {{ font-size: 106%; font-weight: bold; }}

        .preview-light {{
            background-color: #f4f5f6; border: 1px solid #d4d9db;
            border-radius: 6px;
        }}
        .preview-dark {{
            background-color: #23282a; border: 1px solid #3a4042;
            border-radius: 6px;
        }}
        .preview-bar-light {{ background-color: #e2e6e8; }}
        .preview-bar-dark {{ background-color: #2e3436; }}
        .preview-dot {{ background-color: {self.ACCENT}; border-radius: 999px; }}
        .preview-line-light {{ background-color: #ccd2d4; border-radius: 3px; }}
        .preview-line-dark {{ background-color: #3d4446; border-radius: 3px; }}
        .preview-chip {{ background-color: {self.ACCENT}; border-radius: 4px; }}

        .dot {{
            min-width: 8px; min-height: 8px;
            border-radius: 999px;
            background-color: {dot};
        }}
        .dot-active {{ background-color: {self.ACCENT}; min-width: 22px; }}

        button {{
            background-image: none;
            background-color: {btn_bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 5px 18px;
        }}
        button label {{ color: {fg}; }}
        button:hover {{ background-color: {btn_hover}; }}
        button:disabled {{ color: {sub}; }}
        button:disabled label {{ color: {sub}; }}

        button.suggested-action {{
            background-color: {self.ACCENT};
            border-color: {self.ACCENT};
            color: #ffffff;
        }}
        button.suggested-action label {{ color: #ffffff; }}

        combobox button {{ background-color: {field}; color: {fg}; }}
        combobox button label {{ color: {fg}; }}
        menu, .menu, popover, popover.background {{
            background-color: {field}; color: {fg};
        }}
        menuitem label, popover label {{ color: {fg}; }}
        menuitem:hover {{ background-color: {self.ACCENT}; }}
        menuitem:hover label {{ color: #ffffff; }}

        checkbutton label {{ color: {sub}; font-size: 94%; }}
        separator {{ background-color: {border}; }}
        """
        self.css_provider.load_from_data(css.encode())


# ---------------------------------------------------------------------------

def main():
    settings = load_settings()

    # Oturum acilisinda cagrildiysa ve kullanici kapatmissa sessizce cik
    if "--autostart" in sys.argv and not settings["show_on_startup"]:
        return 0

    window = WelcomeWindow(settings)
    window.show_all()
    window.refresh()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
