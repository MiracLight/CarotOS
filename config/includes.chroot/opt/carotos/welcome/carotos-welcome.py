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
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango

import json
import shutil
import subprocess
import os
import sys
import tempfile
import threading

# Ortak grafit tema: kurulu sistemde /opt/carotos/ortak, depoda kardes klasor
sys.dont_write_bytecode = True      # ortak klasore __pycache__ yazilmasin
ORTAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "ortak")
if ORTAK not in sys.path:
    sys.path.insert(0, ORTAK)
import dil  # noqa: E402  (ortak dil katmani: ortak/dil.py)
import sistem_dili as sd  # noqa: E402  (dil paketi/locale hazirligi)
_BURASI = os.path.dirname(os.path.abspath(__file__))
if _BURASI not in sys.path:
    sys.path.insert(0, _BURASI)
import gezinme  # noqa: E402  (merkez-kol gezinme modeli: gezinme.py)
import tema  # noqa: E402
import yetkili  # noqa: E402  (pkexec yalnizca sistem dizinlerinde aranir)

VURGU = "karsilama"                 # ortak/tema.py: marka mavisi

APP_VERSION = "1.4"
APP_CODENAME = "Eggshell"

CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "carotos-welcome")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

IMG_DIR = os.environ.get("CAROTOS_IMG_DIR") or "/usr/share/carotos/welcome"

# Logo icin sirayla denenecek yollar (ilk bulunan kullanilir).
# NOT: Guvenlik Paneli ikonu yedek olarak KULLANILMAZ; aksi halde logo.png
# yoksa karsilama ekraninda yanlis marka (kalkan) gozukuyordu. Her zaman
# CarotOS logosu (logo.png) kullanilir.
LOGO_CANDIDATES = [
    os.path.join(IMG_DIR, "logo.png"),
    "/usr/share/carotos/welcome/logo.png",
    "/usr/share/carotos/logo.png",
]


def ufw_durumu(yol):
    """ufw acik mi: /etc/ufw/ufw.conf'taki ENABLED satirindan, parola istemeden (Guvenlik Paneli ile ayni desen).
    True/False; dosya okunamaz ya da deger tanimsizsa None."""
    try:
        with open(yol, encoding="utf-8", errors="replace") as fh:
            satirlar = fh.read(65536).splitlines()
    except OSError:
        return None
    durum = None
    for satir in satirlar:                     # kabuk dosyasi gibi okunur: son atama gecerli
        satir = satir.strip()
        if satir.startswith("ENABLED="):
            deger = satir.split("=", 1)[1].strip().strip("'\"").lower()
            durum = True if deger == "yes" else False if deger == "no" else None
    return durum


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
#   ("links",   [ (metin, url, {tr, en}), ... ]) tiklanabilir web baglantilari
#   ("grid",    [ (baslik, {tr, en}), ... ])   iki sutunlu kutu izgarasi
#   ("mac_anahtar", {baslik, alt, acik, kapali, hata: {tr, en}})
#                                               sahte MAC anahtari (pkexec carotos-mac-ayar)
#   ("ufw_anahtar", {baslik, alt, acik, kapali, bilinmiyor, hata: {tr, en}})
#                                               guvenlik duvari anahtari (pkexec carotos-ufw-ayar)
#   ("action",  ({tr, en} baslik, {tr, en} alt, [komut, ...]))
#                                               tiklandiginda bir uygulama acan buyuk kutu

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
        "id": "wallpaper",
        "custom": "wallpaper",
        "title": {"tr": "Masaüstü arka planı", "en": "Desktop wallpaper"},
        "subtitle": {
            "tr": "Masaüstünüz için bir arka plan seçin",
            "en": "Choose a background for your desktop",
        },
    },
    {
        "id": "hub",
        "title": {"tr": "Ne öğrenmek istersin?", "en": "What would you like to learn?"},
        "subtitle": {
            "tr": "İstediğin konuyu seç, bitirdiğin konunun yanında ✓ görünür. Hepsini görmek zorunda değilsin; "
                  "dilediğin zaman “Konuları atla” ile sona geçebilirsin.",
            "en": "Pick any topic; a ✓ appears next to the ones you finish. You don't have to see them all; "
                  "you can jump to the end any time with “Skip topics”.",
        },
        "body": [("hub", None)],
    },
    {
        "id": "network",
        "title": {"tr": "Ağ ve gizlilik", "en": "Network and privacy"},
        "subtitle": {
            "tr": "Ortak ağlarda adresin ve adın korunur",
            "en": "Your address and name are protected on shared networks",
        },
        "body": [
            ("p", {
                "tr": "Kafe, okul ya da yurt gibi ortak ağlarda bilgisayarının donanım "
                      "adresi (MAC) ve adı ağdaki herkese görünebilir. CarotOS bunu "
                      "azaltacak şekilde ayarlıdır:",
                "en": "On shared networks such as cafés, schools or dorms, your "
                      "computer's hardware address (MAC) and name can be visible to "
                      "everyone on the network. CarotOS is set up to reduce this:",
            }),
            ("bullets", [
                {"tr": "Bir ağa katılırken bilgisayarının adı yayınlanmaz.",
                 "en": "Your computer's name is not announced when joining a network."},
                {"tr": "IPv6'da giden bağlantılar için geçici adresler tercih edilir.",
                 "en": "Temporary addresses are preferred for outgoing IPv6 connections."},
                {"tr": "Takas önce RAM'de sıkıştırılmış (zram) tutulur. Kurulumda disk "
                       "takası da oluştuysa, zram dolunca o yedek olarak kullanılır.",
                 "en": "Swap goes to compressed RAM (zram) first. If the installer "
                       "also created a disk swap, it is used as overflow once zram "
                       "is full."},
                {"tr": "Güncellemeleri denetlerken apt, Debian'ın yanında CarotOS deposuna "
                       "(apt.carotos.org) da bağlanır. Bu istekler sunucu günlüğüne düşer; "
                       "CarotOS kullanım verisi toplamaz.",
                 "en": "When checking for updates, apt also connects to the CarotOS repository "
                       "(apt.carotos.org) besides Debian. These requests appear in the server log; "
                       "CarotOS does not collect usage data."},
                {"tr": "Ağ keşfi (mDNS/avahi) varsayılan olarak açıktır, böylece ağdaki yazıcılar bulunur. "
                       "Bilgisayarının adını ağda duyurmasını istemezsen Sistem Sağlığı'nda “Dinlenen "
                       "portlar” kartındaki düğmeyle kapatabilir, istediğin an tekrar açabilirsin.",
                 "en": "Network discovery (mDNS/avahi) is on by default so that printers on the network "
                       "are found. If you do not want your computer's name announced on the network, you can "
                       "turn it off with the button on the “Listening ports” card in System Health, and turn "
                       "it back on at any time."},
            ]),
            ("mac_anahtar", {
                "baslik": {"tr": "Her ağ için farklı sahte donanım adresi (MAC)",
                           "en": "A different fake hardware address (MAC) for each network"},
                "alt": {"tr": "Kafe, otel ya da havalimanı gibi tanımadığın ağlarda aç. Aynı ağda adres "
                              "hep aynı kalır, giriş sayfaları bozulmaz. Okul ya da ofis ağı donanım "
                              "adresine göre izin veriyorsa kapalı bırak: aksi halde bağlanamazsın.",
                        "en": "Turn this on for networks you do not know, such as cafés, hotels or "
                              "airports. The address stays the same on the same network, so login pages "
                              "keep working. Leave it off if your school or office network only allows "
                              "registered hardware addresses: otherwise you cannot connect."},
                "acik": {"tr": "Açık: yeni bağlantılarda sahte adres kullanılır. Ağdan çıkıp yeniden bağlan.",
                         "en": "On: a fake address is used for new connections. Disconnect and reconnect."},
                "kapali": {"tr": "Kapalı: donanımın gerçek adresi kullanılır.",
                           "en": "Off: the real hardware address is used."},
                "hata": {"tr": "Ayar değiştirilemedi (yetki verilmedi ya da bir hata oldu).",
                         "en": "The setting could not be changed (permission was not granted or an "
                               "error occurred)."},
            }),
            ("p", {
                "tr": "Bazı ağlar (bazı yurt, otel ve ev modemleri) yalnızca kayıtlı "
                      "donanım adreslerine izin verir. Böyle bir ağa bağlanamıyorsan o "
                      "bağlantı için gerçek adresi seç. Kablosuz ağ için:",
                "en": "Some networks (certain dorms, hotels and home routers) only "
                      "allow registered hardware addresses. If you cannot connect to "
                      "such a network, choose the real address for that connection. "
                      "For a wireless network:",
            }),
            ("code", 'nmcli connection modify "AĞ ADI" wifi.cloned-mac-address permanent'),
            ("p", {
                "tr": "Kablolu bağlantı için:",
                "en": "For a wired connection:",
            }),
            ("code", 'nmcli connection modify "AĞ ADI" ethernet.cloned-mac-address permanent'),
            ("p", {
                "tr": "Ardından ağdan çıkıp yeniden bağlan. Dilersen aynı ayarı ağ "
                      "simgesine sağ tıklayıp Bağlantıları Düzenle (Edit Connections) "
                      "penceresinde, ağını seçip “Cloned MAC address” alanında "
                      "Permanent seçerek de yapabilirsin.",
                "en": "Then disconnect and reconnect. You can also make the same "
                      "change by right-clicking the network icon, choosing Edit "
                      "Connections, selecting your network and setting “Cloned MAC "
                      "address” to Permanent.",
            }),
            ("note", {
                "tr": "Bu ayar yalnızca o bağlantıyı etkiler; diğer ağlarda koruma "
                      "açık kalır. Bu önlemler bir gizlilik azaltıcıdır, tam "
                      "gizlilik garantisi vermez.",
                "en": "This setting only affects that one connection; protection "
                      "stays on for other networks. These measures reduce exposure; "
                      "they do not guarantee full privacy.",
            }),
        ],
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
        "id": "magaza",
        "title": {"tr": "CarotOS Mağaza", "en": "CarotOS Store"},
        "subtitle": {
            "tr": "Uygulamaları tek tıkla, terminale gerek kalmadan kurun",
            "en": "Install applications with a single click, without the terminal",
        },
        "image": "magaza.png",
        "body": [
            ("p", {
                "tr": "CarotOS Mağaza, seçilmiş uygulamaları apt üzerinden kuran "
                      "grafik bir mağazadır. Kategorilere ayrılmış uygulamaları "
                      "gezebilir, arama yapabilir ve her birini tek bir düğmeyle "
                      "kurabilir ya da kaldırabilirsiniz.",
                "en": "CarotOS Store is a graphical store that installs curated "
                      "applications through apt. You can browse apps by category, "
                      "search, and install or remove each one with a single button.",
            }),
            ("bullets", [
                {"tr": "Grafik, Ofis, İnternet, Medya, Geliştirme, Sistem ve "
                       "Güvenlik kategorileri bulunur.",
                 "en": "Categories for Graphics, Office, Internet, Media, "
                       "Development, System and Security."},
                {"tr": "Kurulum ve kaldırma, yönetici parolası sorularak güvenli "
                       "biçimde yapılır.",
                 "en": "Installing and removing is done securely, prompting for "
                       "the administrator password."},
                {"tr": "Kurulu uygulamalar bir rozetle işaretlenir; depo listesi "
                       "tek düğmeyle yenilenir.",
                 "en": "Installed apps are marked with a badge; the repository "
                       "list refreshes with a single button."},
                {"tr": "Arayüz, sistemin diline ve temasına uyum sağlar.",
                 "en": "The interface follows the system language and theme."},
            ]),
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
        "id": "usb",
        "title": {"tr": "CarotOS USB Denetimi", "en": "CarotOS USB Check"},
        "subtitle": {
            "tr": "Takılan USB belleklerini otomatik güvenlik taraması",
            "en": "Automatic security scan of inserted USB drives",
        },
        "image": "usb.png",
        "body": [
            ("p", {
                "tr": "CarotOS USB Denetimi, bir USB bellek takıldığında arka "
                      "planda çalışır ve belleği şüpheli dosyalara karşı tarar. "
                      "Dosyaların içeriğini okumaz; yalnızca ad, uzantı ve biçim "
                      "gibi ipuçlarına bakarak USB solucanı belirtilerini tespit "
                      "eder.",
                "en": "CarotOS USB Check runs in the background when a USB drive "
                      "is inserted and scans it for suspicious files. It does not "
                      "read file contents; it detects signs of USB worms using "
                      "only clues such as names, extensions and format.",
            }),
            ("bullets", [
                {"tr": "Otomatik çalıştırma dosyaları, çift uzantılar ve sahte "
                       "kısayollar gibi bilinen bulaşma yöntemlerini yakalar.",
                 "en": "Catches known infection methods such as autorun files, "
                       "double extensions and fake shortcuts."},
                {"tr": "Bulgular düşük, orta ve yüksek olarak derecelendirilir; "
                       "her biri sade bir dille açıklanır.",
                 "en": "Findings are rated low, medium and high, each explained "
                       "in plain language."},
                {"tr": "Tarama tamamen yereldir; hiçbir veri dışarı gönderilmez.",
                 "en": "The scan is entirely local; no data is sent anywhere."},
            ]),
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
                {"tr": "CTF yarışması: öğretmen yarışmayı başlatır, herkes aynı görevleri kendi dosyasıyla "
                       "çözer ve CAROT{...} biçimindeki bayrağı gönderir. Bayrağı doğrulayan ve puanı "
                       "hesaplayan öğretmenin bilgisayarıdır; bayrağın başkasına yaramaz.",
                 "en": "CTF contest: the teacher starts the contest, everyone solves the same challenges with "
                       "their own file and submits the flag in the CAROT{...} format. The teacher's computer "
                       "checks the flag and works out the score; your flag is no use to anyone else."},
                {"tr": "Savunmacı görünümü: saldırının sahte servislerde bıraktığı izleri (olay günlüğü) görürsün; "
                       "uygulama kalıpları bulgu olarak gösterir ve ufw ile fail2ban'ın nasıl koruduğunu anlatır. "
                       "Günlüğe yalnızca meta veri yazılır, parolalar yazılmaz.",
                 "en": "Defender view: you see the traces your attack left on the fake services (the event log); "
                       "the app shows patterns as findings and explains how ufw and fail2ban protect. Only "
                       "metadata is logged, never passwords."},
            ]),
            ("note", {
                "tr": "Poligon sınıf içi kullanım için tasarlandı; güvendiğin bir ağda kullan. "
                      "Sınıf modundaki bağlantı henüz şifreli değil; şifreleme CarotOS 1.5'te gelecek.",
                "en": "Poligon is designed for use inside a classroom; use it on a network you trust. "
                      "The class-mode connection is not encrypted yet; encryption is planned for CarotOS 1.5.",
            }),
        ],
    },
    {
        "id": "carotpot",
        "title": {"tr": "CarotPot", "en": "CarotPot"},
        "subtitle": {
            "tr": "Ağınızı tarayan ya da saldıran cihazları yakalayın",
            "en": "Catch devices that scan or attack your network",
        },
        "image": "carotpot.png",
        "body": [
            ("p", {
                "tr": "CarotPot, yerel ağınızda sahte bir hedef gibi davranan bir "
                      "bal küpü (honeypot) uygulamasıdır. Gerçek sistemlerinize "
                      "dokunmadan, ağınızı tarayan ya da ona saldırmaya çalışan "
                      "cihazları tespit eder.",
                "en": "CarotPot is a honeypot that behaves like a fake target on "
                      "your local network. Without touching your real systems, it "
                      "detects devices that scan or try to attack your network.",
            }),
            ("bullets", [
                {"tr": "Port tarama, kaba kuvvet denemesi gibi şüpheli davranışları "
                       "canlı olarak yakalar.",
                 "en": "Catches suspicious behaviour such as port scans and "
                       "brute-force attempts live."},
                {"tr": "Saldıran cihazın IP adresini, zamanını ve ne yaptığını "
                       "kaydeder.",
                 "en": "Logs the attacking device's IP address, time and what it "
                       "did."},
                {"tr": "Tamamen yereldir; hiçbir veri dışarı gönderilmez.",
                 "en": "Entirely local; no data is sent anywhere."},
            ]),
            ("note", {
                "tr": "CarotPot varsayılan olarak yalnızca yerel ağdan bağlantı kabul eder; güvenlik "
                      "duvarında yalnızca gerçekten açılan tuzak portlarına, yalnızca yerel ağa izin verir "
                      "ve bu izinler tuzak kapanınca kendiliğinden silinir. İstersen Ayarlar'dan "
                      "internetten gelen bağlantıları da açabilirsin; makinen internete açıksa gerçek "
                      "saldırı denemelerini kaydedersin, bu yüzden yalnızca bilerek aç.",
                "en": "By default CarotPot accepts connections from the local network only; in the "
                      "firewall it allows only the trap ports that are really opened, only for the local "
                      "network, and these permissions are removed automatically when the trap closes. If "
                      "you like, you can also allow connections from the internet in Settings; if your "
                      "machine is exposed to the internet you will record real attack attempts, so turn it "
                      "on only on purpose.",
            }),
        ],
    },
    {
        "id": "carotene",
        "title": {"tr": "Carotene", "en": "Carotene"},
        "subtitle": {
            "tr": "ClamAV ile dosyalarınızı bilinen zararlı yazılımlara karşı tarayın",
            "en": "Scan your files for known malware with ClamAV",
        },
        "image": "carotene.png",
        "body": [
            ("p", {
                "tr": "Carotene, ClamAV motorunu kullanan basit bir antivirüs "
                      "uygulamasıdır. Seçtiğiniz dosya ya da klasörleri bilinen "
                      "zararlı yazılım imzalarına karşı tarar.",
                "en": "Carotene is a simple antivirus application built on the "
                      "ClamAV engine. It scans the files or folders you choose "
                      "against known malware signatures.",
            }),
            ("bullets", [
                {"tr": "Tek dosya, bir klasör ya da tüm ev dizininizi "
                       "tarayabilirsiniz.",
                 "en": "Scan a single file, a folder, or your entire home "
                       "directory."},
                {"tr": "Bulunan tehditler karantinaya alınabilir ya da silinebilir.",
                 "en": "Detected threats can be quarantined or deleted."},
                {"tr": "İmza veritabanı tek düğmeyle güncellenir.",
                 "en": "The signature database updates with a single button."},
            ]),
        ],
    },
    {
        "id": "guvenlik_duvari",
        "title": {"tr": "Güvenlik duvarı", "en": "Firewall"},
        "subtitle": {
            "tr": "Ağdan gelen bağlantıları süzen koruma; ne zaman açmalı?",
            "en": "The shield that filters incoming connections; when to turn it on",
        },
        "body": [
            ("p", {
                "tr": "Güvenlik duvarı, bilgisayarına ağdan gelmek isteyen bağlantıları kurallara "
                      "göre kabul eden ya da geri çeviren bir kapıcı gibidir. CarotOS'ta bu iş ufw ile "
                      "yapılır.",
                "en": "A firewall works like a doorkeeper: it accepts or turns away connections that "
                      "try to reach your computer from the network, following rules. In CarotOS this is "
                      "done with ufw.",
            }),
            ("p", {
                "tr": "CarotOS'ta güvenlik duvarı bilerek kapalı gelir; böylece nmap, CarotPot ve "
                      "Poligon gibi ağ araçlarını ilk günden rahatça deneyebilirsin. Evde ve kendi "
                      "ağında bu sakin bir başlangıçtır.",
                "en": "In CarotOS the firewall comes turned off on purpose, so you can try network tools "
                      "such as nmap, CarotPot and Poligon comfortably from day one. At home and on your "
                      "own network this is a calm starting point.",
            }),
            ("ufw_anahtar", {
                "baslik": {"tr": "Güvenlik duvarı (ufw)", "en": "Firewall (ufw)"},
                "alt": {"tr": "Açıkken dışarıdan gelen bağlantılar engellenir. CarotPot başlarken kendi portlarına "
                              "izin verir; Poligon sınıf modu için izin vermen gerekebilir.",
                        "en": "While it is on, incoming connections from outside are blocked. CarotPot allows its "
                              "own ports when it starts; Poligon class mode may need to be allowed."},
                "acik": {"tr": "Açık: dışarıdan gelen bağlantılar engelleniyor.",
                         "en": "On: incoming connections from outside are blocked."},
                "kapali": {"tr": "Kapalı: gelen bağlantılar süzülmüyor.",
                           "en": "Off: incoming connections are not filtered."},
                "bilinmiyor": {"tr": "Durum bilinmiyor (ufw ayarı okunamadı).",
                               "en": "State unknown (the ufw setting could not be read)."},
                "hata": {"tr": "Ayar değiştirilemedi (yetki verilmedi, ufw kurulu değil ya da bir hata oldu).",
                         "en": "The setting could not be changed (permission was not granted, ufw is not "
                               "installed or an error occurred)."},
            }),
            ("bullets", [
                {"tr": "Ne zaman açmalı: kafe, okul, yurt ya da herhangi bir ortak ağdayken; "
                       "tanımadığın kişilerle aynı ağı paylaştığında.",
                 "en": "When to turn it on: in a café, school, dorm or any shared network; whenever you "
                       "share the network with people you do not know."},
                {"tr": "CarotOS Güvenlik Paneli'nde: ufw aracını seç, eylem olarak “Etkinleştir”i seçip "
                       "çalıştır.",
                 "en": "In the CarotOS Security Panel: pick the ufw tool, choose “Enable” as the action "
                       "and run it."},
                {"tr": "Terminalde aşağıdaki komutu kullanabilirsin. Kapatmak için "
                       "sudo ufw disable yazman yeter.",
                 "en": "In the terminal you can use the command below. To turn it off again, "
                       "just type sudo ufw disable."},
            ]),
            ("code", "sudo ufw enable"),
            ("note", {
                "tr": "Durumu istediğin zaman sudo ufw status ile ya da CarotOS Sistem Sağlığı'ndan "
                      "görebilirsin. Güvenlik duvarını açınca, ağdan bağlanmasını beklediğin bir "
                      "hizmet varsa (örneğin Poligon sınıf modu) önce ona izin vermen gerekebilir.",
                "en": "You can check the state any time with sudo ufw status or in CarotOS System Health. "
                      "Once the firewall is on, a service you expect to be reachable from the network "
                      "(for example Poligon class mode) may need to be allowed first.",
            }),
        ],
    },
    {
        "id": "health",
        "title": {"tr": "CarotOS Sistem Sağlığı", "en": "CarotOS System Health"},
        "subtitle": {
            "tr": "Sisteminizin güvenlik ve bakım durumunu tek bakışta görün",
            "en": "See your system's security and maintenance status at a glance",
        },
        "image": "health.png",
        "body": [
            ("p", {
                "tr": "CarotOS Sistem Sağlığı, sisteminizi düzenli olarak "
                      "denetleyerek güvenlik duvarı, güncellemeler, parola "
                      "politikası gibi önemli ayarların durumunu kontrol eder ve "
                      "basit bir dille özetler.",
                "en": "CarotOS System Health audits your system regularly, "
                      "checking important settings such as the firewall, updates "
                      "and password policy, and summarises the results in plain "
                      "language.",
            }),
            ("bullets", [
                {"tr": "Her bulgu, ne anlama geldiği ve nasıl düzeltileceğiyle "
                       "birlikte açıklanır.",
                 "en": "Every finding is explained, along with what it means and "
                       "how to fix it."},
                {"tr": "Denetimler düşük, orta ve yüksek önem derecesine göre "
                       "sıralanır.",
                 "en": "Checks are ranked by low, medium and high severity."},
                {"tr": "Tek düğmeyle yeniden tarama yapılabilir.",
                 "en": "A single button re-runs the scan."},
            ]),
        ],
    },
    {
        "id": "kurtarma",
        "title": {"tr": "CarotOS Kurtarma", "en": "CarotOS Recovery"},
        "subtitle": {
            "tr": "Bir güncelleme ya da yanlış ayar sistemi bozarsa son kararlı duruma dönün",
            "en": "Go back to the last stable state when an update or a wrong setting breaks the system",
        },
        "image": "kurtarma.png",
        "body": [
            ("p", {
                "tr": "CarotOS Kurtarma, sisteminizin belirli anlardaki kopyalarını "
                      "(kurtarma noktalarını) saklar. Bir güncelleme ya da yanlış bir ayar "
                      "sistemi bozduğunda, ilgili noktayı seçip o ana geri dönebilirsiniz. "
                      "Windows'un Sistem Geri Yükleme'siyle aynı fikirdir.",
                "en": "CarotOS Recovery keeps copies of your system at chosen moments "
                      "(recovery points). When an update or a wrong setting breaks the system, "
                      "you can pick a point and go back to that moment. It is the same idea as "
                      "Windows System Restore.",
            }),
            ("bullets", [
                {"tr": "“Şimdi nokta oluştur” ile büyük bir değişiklikten önce elle nokta alabilirsiniz.",
                 "en": "Use “Create a point now” to take a point by hand before a big change."},
                {"tr": "apt ile paket kurup güncellerken, değişiklikten hemen önce kendiliğinden bir "
                       "nokta açılır (ayarlardan kapatılabilir).",
                 "en": "When you install or update packages with apt, a point is opened "
                       "automatically right before the change (you can turn this off in settings)."},
                {"tr": "Her nokta /etc, /root ve kurulu paket listesini içerir. Sabit bağlar "
                       "sayesinde yalnızca değişen dosyalar yer kaplar.",
                 "en": "Each point holds /etc, /root and the installed package list. Thanks to "
                       "hard links, only changed files take up space."},
                {"tr": "Noktaları geri yükleyebilir ya da silebilirsiniz.",
                 "en": "You can restore or delete any point."},
                {"tr": "Ayarlar: otomatik nokta açık/kapalı, kaç nokta saklanacağı (varsayılan 5), "
                       "otomatik noktalar arası en az süre (10 dakika) ve gereken en az boş alan "
                       "(512 MB).",
                 "en": "Settings: automatic point on/off, how many points to keep (default 5), "
                       "the minimum time between automatic points (10 minutes) and the minimum "
                       "free space required (512 MB)."},
            ]),
            ("note", {
                "tr": "Bu bir yedekleme aracı değildir: kişisel dosyalarınıza (Belgeler, "
                      "Masaüstü, fotoğraflar, /home) dokunmaz ve onları korumaz; onlar için ayrıca "
                      "yedek alın. Noktalar aynı diskte durur, disk bozulursa onlar da gider.",
                "en": "This is not a backup tool: it does not touch or protect your personal "
                      "files (Documents, Desktop, photos, /home), so back those up separately. "
                      "Points live on the same disk, so if the disk fails they go with it.",
            }),
        ],
    },
    {
        "id": "filenor",
        "title": {"tr": "Filenor", "en": "Filenor"},
        "subtitle": {
            "tr": "Görsel, ses, video ve belgeleri terminale gerek kalmadan "
                  "dönüştürün",
            "en": "Convert images, audio, video and documents without the "
                  "terminal",
        },
        "image": "filenor.png",
        "body": [
            ("p", {
                "tr": "Filenor, günlük dosya işlerini tek bir pencerede toplayan "
                      "bir dönüştürücüdür. Görsel, ses, video, belge ve yazı tipi "
                      "biçimleri arasında dönüştürme yapar.",
                "en": "Filenor brings everyday file tasks into a single window. "
                      "It converts between image, audio, video, document and "
                      "font formats.",
            }),
            ("bullets", [
                {"tr": "PDF'leri birleştirir, böler ve parola ile kilitler.",
                 "en": "Merges, splits and password-locks PDFs."},
                {"tr": "Taranmış belgelerden OCR ile metin çıkarır.",
                 "en": "Extracts text from scanned documents with OCR."},
                {"tr": "Birden fazla dosyayı aynı anda, toplu olarak dönüştürür.",
                 "en": "Converts many files at once, in batch."},
            ]),
        ],
    },
    {
        "id": "former",
        "title": {"tr": "CarotOS Former", "en": "CarotOS Former"},
        "subtitle": {
            "tr": "Güvenlik araçlarını canlandırmalı, adım adım bir rehberle "
                  "öğrenin",
            "en": "Learn the security tools with an animated, step-by-step "
                  "guide",
        },
        "image": "former.png",
        "body": [
            ("p", {
                "tr": "Former, Güvenlik Paneli'ndeki her aracı, CarotPot'u ve "
                      "Carotene'i canlandırmalı ekranlarla adım adım anlatan bir "
                      "rehberdir. Kendi hızınızda, dokunmadan önce ne olacağını "
                      "görerek ilerlersiniz.",
                "en": "Former is a guide that walks through every Security Panel "
                      "tool, plus CarotPot and Carotene, with animated, "
                      "step-by-step screens. You move at your own pace, seeing "
                      "what happens before you try it yourself.",
            }),
            ("bullets", [
                {"tr": "Her araç için ne işe yaradığı, ne zaman kullanılacağı ve "
                       "örnek bir çalıştırma gösterilir.",
                 "en": "For each tool it shows what it does, when to use it, and "
                       "an example run."},
                {"tr": "Adımlar arasında istediğiniz zaman ileri geri "
                       "gidebilirsiniz.",
                 "en": "You can move back and forth between steps at any time."},
                {"tr": "Yeni başlayanlar için gerçek araçları çalıştırmadan "
                       "önceki en güvenli durak.",
                 "en": "The safest stop for beginners before running the real "
                       "tools."},
            ]),
        ],
    },
    {
        "id": "gsd",
        "title": {"tr": "CarotOS GSD", "en": "CarotOS GSD"},
        "subtitle": {
            "tr": "Linux, ağ, güvenlik ve kriptografi terimleri için aranabilir "
                  "bir sözlük",
            "en": "A searchable dictionary of Linux, networking, security and "
                  "cryptography terms",
        },
        "image": "gsd.png",
        "body": [
            ("p", {
                "tr": "GSD (Genel Sistem Sözlüğü), bu turda ve Güvenlik "
                      "Paneli'nde karşınıza çıkan terimleri açıklayan, iki dilli "
                      "bir başvuru kaynağıdır. 150'den fazla terim; kategoriye "
                      "göre süzebilir ya da arayabilirsiniz.",
                "en": "GSD (General System Dictionary) is a bilingual reference "
                      "that explains the terms you encounter in this tour and in "
                      "the Security Panel. Over 150 terms, filterable by "
                      "category or searchable directly.",
            }),
            ("bullets", [
                {"tr": "Linux, ağ, güvenlik, kriptografi ve algoritma "
                       "kategorilerine ayrılmıştır.",
                 "en": "Organised into Linux, networking, security, "
                       "cryptography and algorithms categories."},
                {"tr": "Her terim kısa bir tanım, ayrıntılı açıklama ve çoğu "
                       "zaman bir örnekle anlatılır.",
                 "en": "Each term comes with a short definition, a detailed "
                       "explanation and often an example."},
                {"tr": "İlgili terimler birbirine bağlıdır; biri okurken "
                       "diğerine tek tıkla geçebilirsiniz.",
                 "en": "Related terms are cross-linked; jump from one to another "
                       "with a single click."},
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
        "id": "acikla",
        "title": {"tr": "Komut Açıklayıcı", "en": "Command Explainer"},
        "subtitle": {
            "tr": "Bir komutu çalıştırmadan önce ne yapacağını öğren",
            "en": "Find out what a command does before you run it",
        },
        "body": [
            ("p", {
                "tr": "Terminalde bir komut yazarken ne yapacağından emin değil misin? Satırı yazıp "
                      "Alt+E tuşlarına bas: CarotOS komutu ÇALIŞTIRMADAN açıklar. Hiçbir şey çalışmaz, "
                      "hiçbir şey ağa gönderilmez; her şey bilgisayarında kalır.",
                "en": "Not sure what a command will do while you type it in the terminal? Write the line "
                      "and press Alt+E: CarotOS explains it WITHOUT running it. Nothing is executed and "
                      "nothing is sent over the network; it all stays on your computer.",
            }),
            ("bullets", [
                {"tr": "Komutun her parçasının (boru, &&, ;) kısa bir özetini verir.",
                 "en": "It gives a short summary of every part of the command (pipe, &&, ;)."},
                {"tr": "Bayrakların ne işe yaradığını tek tek anlatır (ör. -l, -r, --no-install-recommends).",
                 "en": "It explains what each flag does (e.g. -l, -r, --no-install-recommends)."},
                {"tr": "Ağda ne kadar dikkat çekeceğini (gürültü) ve root yetkisi gerekip gerekmediğini söyler.",
                 "en": "It tells you how much attention it draws on a network (noise) and whether root privileges are needed."},
                {"tr": "Tehlikeli kalıpları uyarır: bir klasörü topluca silmek, internetten indirip doğrudan "
                       "çalıştırmak (curl … | sh), bir disk aygıtına yazmak gibi.",
                 "en": "It warns about dangerous patterns: deleting a whole folder, running something downloaded "
                       "from the internet directly (curl … | sh), writing to a disk device, and so on."},
                {"tr": "Veri tabanında olmayan bir komutu ya da bayrağı bilmiyormuş gibi yapmaz: açıkça \"tanımıyorum\" der.",
                 "en": "It doesn't pretend to know a command or flag it doesn't have: it plainly says \"I don't know this\"."},
            ]),
            ("code", "sudo ufw status verbose"),
            ("p", {
                "tr": "Yukarıdaki satırı terminale yaz ama Enter'a basma; onun yerine Alt+E'ye bas. "
                      "Komut satırından da kullanabilirsin:",
                "en": "Type the line above in the terminal but don't press Enter; press Alt+E instead. "
                      "You can also use it from the command line:",
            }),
            ("code", "carotos-acikla tar xzf arsiv.tar.gz"),
            ("note", {
                "tr": "Yapay zekâ değildir: hazır bir veri tabanıyla çalışır; temel Linux komutlarını, savunma "
                      "araçlarını ve Güvenlik Paneli'ndeki test araçlarını (nmap, hydra, sqlmap…) tanır. Panel'deki "
                      "\"Açıkla\" düğmesi de aynı açıklamayı gösterir. Değişkenleri ($ADI) ve takma adları çözmez, "
                      "yalnızca bash'te çalışır. $(...), ters tırnak, sudo, sh -c gibi sarmalayıcıların "
                      "içindeki komut ayrı parça olarak açıklanır; ama komutun çıktısı çözülmez (hiçbir şey "
                      "çalıştırılmadığı için). Bir komutu anlamadan çalıştırma.",
                "en": "It is not an AI: it works from a ready-made database and knows the basic Linux commands, "
                      "defensive tools and the testing tools in the Security Panel (nmap, hydra, sqlmap…). The "
                      "Panel's \"Explain\" button shows the same explanation. It doesn't resolve variables ($NAME) or "
                      "aliases and works only in bash. A command inside $(...), backticks, "
                      "sudo or sh -c is explained as a separate part; its output is not resolved (nothing "
                      "is run, so there is no output). Never run a command you don't understand.",
            }),
        ],
    },
    {
        "id": "etik",
        "title": {"tr": "Etik ve sorumluluk", "en": "Ethics and responsibility"},
        "subtitle": {
            "tr": "Güvenlik araçlarını yalnızca izinli yerlerde kullan",
            "en": "Use security tools only where you have permission",
        },
        "body": [
            ("p", {
                "tr": "Bu araçlar öğrenmek ve kendi sistemini savunmak içindir. Başkasının ağında ya da "
                      "sisteminde izinsiz tarama veya deneme yapmak birçok ülkede suçtur; geçerli kuralları kendin "
                      "kontrol et. Bu metin hukuki tavsiye değildir.",
                "en": "These tools are for learning and for defending your own systems. Scanning or trying things "
                      "on someone else's network or system without permission is a criminal offence in many "
                      "countries; check the rules that apply to you. This text is not legal advice.",
            }),
            ("p", {
                "tr": "Bu yüzden Güvenlik Paneli, nmap, nikto, sqlmap ve hydra gibi araçlarda hedef olarak bir adres "
                      "yazdığında önce hedefin kime ait olabileceğine bakar (adres sorgulaması yapmadan, yalnızca "
                      "adrese bakarak):",
                "en": "That is why, when you type a target address into tools like nmap, nikto, sqlmap and hydra, "
                      "the Security Panel first checks who the target could belong to (just by looking at the "
                      "address, without any lookup):",
            }),
            ("bullets", [
                {"tr": "Kendi bilgisayarın (127.0.0.1, localhost): hiçbir şey sorulmaz.",
                 "en": "Your own computer (127.0.0.1, localhost): nothing is asked."},
                {"tr": "Özel ağ (ev, okul, kafe gibi): \"Bu ağ sana mı ait?\" bir kez sorulur; evet dersen o ağ hatırlanır.",
                 "en": "A private network (home, school, café…): you are asked \"Is this your network?\" once; if you say yes, "
                       "that network is remembered."},
                {"tr": "Başka bir yer (açık internet adresi ya da geniş adres bloğu): hedefi aynen elle yazman "
                       "istenir; yazmazsan araç çalışmaz.",
                 "en": "Anywhere else (a public internet address or a wide address block): you must type the target "
                       "exactly; if you don't, the tool does not run."},
                {"tr": "Verdiğin her onay bilgisayarında bir günlüğe yazılır (~/.config/carotos-panel/etik-gunlugu.log); "
                       "hiçbir yere gönderilmez.",
                 "en": "Every confirmation you give is written to a log on your computer "
                       "(~/.config/carotos-panel/etik-gunlugu.log); nothing is sent anywhere."},
            ]),
            ("note", {
                "tr": "Güvenle alıştırma yapabileceğin yerler: kendi bilgisayarın (127.0.0.1) ve CarotOS Poligon.",
                "en": "Safe places to practise: your own computer (127.0.0.1) and CarotOS Poligon.",
            }),
        ],
    },
    {
        "id": "disk",
        "title": {"tr": "Disk şifreleme ve swap", "en": "Disk encryption and swap"},
        "subtitle": {
            "tr": "Bilgisayarın çalınırsa verilerin güvende kalsın",
            "en": "Keep your data safe if your computer is stolen",
        },
        "body": [
            ("p", {
                "tr": "Bilgisayarın kaybolur ya da çalınırsa, diski başka bir bilgisayara takan kişi şifresiz dosyaları "
                      "okuyabilir. Tam disk şifreleme (LUKS) bunu önler: disk, parola girilmeden açılmaz.",
                "en": "If your computer is lost or stolen, whoever puts its disk in another computer can read the "
                      "files that aren't encrypted. Full-disk encryption (LUKS) prevents that: the disk won't open "
                      "without the password.",
            }),
            ("note", {
                "tr": "Disk şifrelemeyi kurulum sırasında, diski bölümlendirirken \"şifreli LVM\" seçeneğiyle açarsın. "
                      "Sonradan eklemek zordur (diski yeniden kurmak gerekir). Şifreli diskin parolasını unutursan "
                      "verilerin kurtarılamaz.",
                "en": "You turn on disk encryption during installation, by choosing the \"encrypted LVM\" option when "
                      "partitioning the disk. Adding it later is hard (you would need to reinstall). If you forget an "
                      "encrypted disk's password, your data cannot be recovered.",
            }),
            ("p", {
                "tr": "Swap da önemlidir: bellek dolunca sistem bellek içeriğini diske yazar. Şifresiz bir swap, "
                      "parolalarını ve anahtarlarını diskte bırakabilir. CarotOS varsayılan olarak RAM içinde "
                      "sıkıştırılmış bir swap (zram) kullanır; bu diske hiçbir şey yazmaz.",
                "en": "Swap matters too: when memory fills up the system writes memory contents to disk. Unencrypted "
                      "swap can leave your passwords and keys on the disk. By default CarotOS uses a swap compressed "
                      "inside RAM (zram), which writes nothing to the disk.",
            }),
            ("bullets", [
                {"tr": "Sistem Sağlığı'ndaki \"Swap şifreleme\" denetimi, diskte şifresiz swap olup olmadığına bakar.",
                 "en": "The \"Swap encryption\" check in System Health looks for unencrypted swap on the disk."},
                {"tr": "Varsa \"Disk swap'ını kapat\" düğmesi sunar: onay ister, ayar dosyasının yedeğini alır, zram'a dokunmaz.",
                 "en": "If there is some, it offers a \"Disable disk swap\" button: it asks for confirmation, backs up the "
                       "settings file and leaves zram alone."},
                {"tr": "Disk şifreleme bilgisayar kapalıyken korur; açıkken ve oturum açıkken değil. Uzaklaşırken ekranı kilitle.",
                 "en": "Disk encryption protects while the computer is off, not while it is on and you are logged in. "
                       "Lock the screen when you walk away."},
            ]),
        ],
    },
    {
        "id": "kur",
        "title": {"tr": "CarotOS'u kurmak", "en": "Installing CarotOS"},
        "subtitle": {
            "tr": "Canlı masaüstünden, birkaç adımda bilgisayarına kur",
            "en": "Install it on your computer from the live desktop, in a few steps",
        },
        "body": [
            ("p", {
                "tr": "Şu an CarotOS'u canlı oturumda deniyorsun: hiçbir şey diske yazılmaz. Beğendiysen masaüstündeki "
                      "\"CarotOS'u Kur\" simgesine çift tıkla; kurulum penceresi açılır. Kurulum sırasında canlı "
                      "oturum çalışmaya devam eder, internete ihtiyaç yoktur.",
                "en": "You are trying CarotOS in the live session right now: nothing is written to the disk. If you "
                      "like it, double-click the \"Install CarotOS\" icon on the desktop and the installer window "
                      "opens. The live session keeps working during the installation, and no internet connection "
                      "is needed.",
            }),
            ("bullets", [
                {"tr": "Dil: canlı oturum İngilizce olsa bile kurucunun ilk ekranında dili seçersin.",
                 "en": "Language: even if the live session is in English, you choose the language on the "
                       "installer's first screen."},
                {"tr": "Konum: saat dilimini seç (varsayılan İstanbul). Sonra klavye düzenini seç.",
                 "en": "Location: pick your time zone (Istanbul by default). Then pick the keyboard layout."},
                {"tr": "Bölümler: tüm diski sil, mevcut sistemin (örneğin Windows) yanına kur ya da elle bölümle. "
                       "İstersen disk şifrelemeyi de buradan açarsın.",
                 "en": "Partitions: erase the whole disk, install alongside an existing system (for example "
                       "Windows), or partition by hand. You can also turn on disk encryption here."},
                {"tr": "Kullanıcı: bir kullanıcı adı ve parola belirle. Bu kullanıcı sudo kullanabilir; root girişi "
                       "kilitli kalır. Bilgisayar adı carotos olur.",
                 "en": "User: choose a user name and password. This user can use sudo; root login stays locked. "
                       "The computer name is carotos."},
                {"tr": "Özet: yapılacakları son kez gör, \"Kur\"a bas. Kurulum sürerken slaytlar gösterilir; "
                       "bitince bilgisayarı yeniden başlat.",
                 "en": "Summary: review what will happen one last time and press \"Install\". Slides are shown "
                       "during the installation; when it ends, restart the computer."},
            ]),
            ("note", {
                "tr": "Diske dokunmadan önce önemli dosyalarının yedeğini al. \"Tüm diski sil\" diskteki her şeyi "
                      "siler. Windows yanına kuracaksan \"Windows ile birlikte\" sayfasındaki hazırlıkları yap. "
                      "Şifreli diskin parolasını unutursan verilerin kurtarılamaz.",
                "en": "Back up your important files before touching the disk. \"Erase disk\" deletes everything "
                      "on it. If you will install next to Windows, follow the preparations on the \"Alongside "
                      "Windows\" page. If you forget an encrypted disk's password, your data cannot be recovered.",
            }),
            ("p", {
                "tr": "Kurulu sistemde kurucu ve canlı oturum paketleri bulunmaz. Kurucu açılmazsa ya da takılırsa, "
                      "bilgisayarı yeniden başlatıp USB açılış menüsünde eski metin tabanlı Debian kurucusunu seçebilirsin; "
                      "o yedek olarak durur.",
                "en": "The installed system does not contain the installer or the live-session packages. If the "
                      "installer does not open or gets stuck, restart the computer and choose the older text-based "
                      "Debian installer in the USB boot menu; it stays there as a fallback.",
            }),
        ],
    },
    {
        "id": "windows",
        "title": {"tr": "Windows ile birlikte", "en": "Alongside Windows"},
        "subtitle": {
            "tr": "Aynı bilgisayarda iki sistem: kurmadan önce ve sonra",
            "en": "Two systems on one computer: before and after installing",
        },
        "body": [
            ("p", {
                "tr": "CarotOS'u Windows'u silmeden aynı diske kurabilirsin. Bilgisayar açılınca bir menüden hangi "
                      "sistemi başlatacağını seçersin. Kurmadan önce Windows'ta birkaç hazırlık yapmak verilerini korur:",
                "en": "You can install CarotOS on the same disk without removing Windows. When the computer starts, "
                      "you choose which system to boot from a menu. A few preparations in Windows before installing "
                      "keep your data safe:",
            }),
            ("bullets", [
                {"tr": "Önemli dosyalarının yedeğini al. Disk bölümlendirme yanlış seçimle veri siler.",
                 "en": "Back up your important files. Partitioning the disk deletes data if you pick the wrong option."},
                {"tr": "BitLocker açıksa kurtarma anahtarını bir yere yaz ya da kurulumdan önce askıya al; "
                       "yoksa Windows açılışta bu anahtarı isteyebilir.",
                 "en": "If BitLocker is on, write down the recovery key or suspend it before installing; otherwise "
                       "Windows may ask for that key at startup."},
                {"tr": "Windows'ta Hızlı Başlatma'yı kapat. Açıkken Windows diski tam kapatmaz ve iki sistemden "
                       "aynı dosyalara erişmek veri bozabilir.",
                 "en": "Turn off Fast Startup in Windows. While it is on, Windows does not fully release the disk, "
                       "and using the same files from both systems can corrupt data."},
                {"tr": "Windows'un Disk Yönetimi'nde Windows bölümünü küçülterek CarotOS'a boş alan aç.",
                 "en": "Make free space for CarotOS by shrinking the Windows partition in Windows Disk Management."},
                {"tr": "Kurucuda boş alanı kullanan seçeneği seç; \"tüm diski kullan\" Windows'u siler.",
                 "en": "In the installer, choose the option that uses the free space; \"use the entire disk\" erases "
                       "Windows."},
            ]),
            ("p", {
                "tr": "Kurulumdan sonra açılış menüsünde Windows da listelenir. Başka bir sistem bulunduğunda menü "
                      "30 saniye bekler, yalnızca CarotOS varsa 5 saniye. Secure Boot'u kapatman gerekmez.",
                "en": "After installation, Windows is also listed in the boot menu. When another system is found the "
                      "menu waits 30 seconds, or 5 seconds if only CarotOS is installed. You do not need to turn off "
                      "Secure Boot.",
            }),
        ],
    },
    {
        "id": "dogrula",
        "title": {"tr": "İndirdiğini doğrula", "en": "Verify what you download"},
        "subtitle": {
            "tr": "ISO dosyasının gerçekten CarotOS'tan geldiğini kontrol et",
            "en": "Check that the ISO file really comes from CarotOS",
        },
        "body": [
            ("p", {
                "tr": "Değiştirilmiş bir ISO dosyası, kurduğun anda bilgisayarına zararlı yazılım sokabilir. İki "
                      "kontrol bunu önler: özet (SHA-256) dosyanın indirirken bozulmadığını, imza ise dosyayı "
                      "gerçekten CarotOS'un hazırladığını gösterir.",
                "en": "A tampered ISO file can put malware on your computer the moment you install it. Two checks "
                      "prevent this: the checksum (SHA-256) shows the file was not damaged while downloading, and "
                      "the signature shows that CarotOS really made it.",
            }),
            ("p", {
                "tr": "ISO ile aynı yerden iki küçük dosya daha indir: SHA256SUMS (özetler) ve SHA256SUMS.sign "
                      "(imza). Üçünü aynı klasöre koy ve o klasörde terminali aç. CarotOS'ta imza anahtarı zaten "
                      "kurulu, önce imzayı doğrula:",
                "en": "Download two small files from the same place as the ISO: SHA256SUMS (the checksums) and "
                      "SHA256SUMS.sign (the signature). Put all three in the same folder and open the terminal "
                      "there. The signing key is already installed on CarotOS, so first verify the signature:",
            }),
            ("code", "gpgv --keyring /usr/share/keyrings/carotos-archive-keyring.gpg SHA256SUMS.sign SHA256SUMS"),
            ("p", {
                "tr": "\"CarotOS Archive\" ve \"imza iyi\" (İngilizce sistemde \"Good signature\") yazmalı. Sonra "
                      "ISO'nun özetini denetle:",
                "en": "It should say \"Good signature\" and \"CarotOS Archive\". Then check the ISO's checksum:",
            }),
            ("code", "sha256sum -c SHA256SUMS --ignore-missing"),
            ("bullets", [
                {"tr": "ISO'nun satırında \"Tamam\" (İngilizce sistemde \"OK\") yazmalı.",
                 "en": "The ISO's line should say \"OK\" (\"Tamam\" on a Turkish system)."},
                {"tr": "\"imza KÖTÜ\" (BAD signature) ya da \"BAŞARISIZ\" (FAILED) görürsen o dosyayı kullanma, "
                       "yeniden indir.",
                 "en": "If you see \"BAD signature\" or \"FAILED\", do not use that file; download it again."},
                {"tr": "Başka bir sistemde önce CarotOS anahtarını carotos.org'dan al ve parmak izini karşılaştır: "
                       "30E6 D4B0 C05E F002 1309 A1A0 9F93 5CD4 D5D0 A1F5",
                 "en": "On another system, first get the CarotOS key from carotos.org and compare its fingerprint: "
                       "30E6 D4B0 C05E F002 1309 A1A0 9F93 5CD4 D5D0 A1F5"},
                {"tr": "Windows'ta aynı imzayı Gpg4win (Kleopatra) ile doğrulayabilirsin.",
                 "en": "On Windows you can verify the same signature with Gpg4win (Kleopatra)."},
            ]),
            ("note", {
                "tr": "Aynı anahtar CarotOS uygulama güncellemelerini (apt.carotos.org) de imzalar; apt bu imzayı "
                      "her güncellemede kendiliğinden denetler.",
                "en": "The same key also signs the CarotOS app updates (apt.carotos.org); apt checks that signature "
                      "automatically on every update.",
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
            ("action", (
                {"tr": "CarotOS Former'ı aç", "en": "Open CarotOS Former"},
                {"tr": "Güvenlik Paneli'ndeki her araç, CarotPot ve Carotene için "
                       "canlandırmalı, adım adım bir rehber. Burada gördüklerinizi "
                       "biraz daha ayrıntılı, kendi hızınızda öğrenmek isterseniz "
                       "başlamak için en iyi yer.",
                 "en": "A live, step-by-step walkthrough for every Security Panel "
                       "tool, CarotPot and Carotene. The best place to start if you "
                       "want to go a little deeper, at your own pace."},
                ["python3", "/opt/carotos/former/carotos-former.py"],
            )),
            ("action", (
                {"tr": "Sözlüğü (GSD) aç", "en": "Open the Glossary (GSD)"},
                {"tr": "Linux, ağ, siber güvenlik ve kriptografi terimlerinin kısa "
                       "açıklamaları. Duyduğunuz bir kelimeyi hızlıca aramak için.",
                 "en": "Short explanations of Linux, networking, cybersecurity and "
                       "cryptography terms. For looking up a word you just heard."},
                ["python3", "/opt/carotos/gsd/carotos-gsd.py"],
            )),
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

def _varsayilan_dil():
    """Ilk acilis dili: sistem dili etkin (cevirisi hazir) bir dilse o, degilse
    'en'. Kayitli bir ayar varsa o yine onceliklidir (bkz. ortak/dil.py)."""
    return dil.varsayilan_dil()


DEFAULTS = {"lang": _varsayilan_dil(), "theme": "dark", "show_on_startup": True,
            "wallpaper": "", "biten_konular": []}

# CarotOS Sleek anahtari (Masaustu arka plani sayfasi): yetkili anahtar karti metinleri
MODERN_ANAHTAR = {
    "baslik": {"tr": "CarotOS Sleek", "en": "CarotOS Sleek"},
    "alt": {
        "tr": "Koyu modern görünüm: yuvarlak köşeler, alt dock ve yan panel. Paketler internetten "
              "indirilir; istediğin an kapatabilirsin.",
        "en": "A modern dark look: rounded corners, a bottom dock and a side panel. Packages are "
              "downloaded from the internet; you can turn it off at any time.",
    },
    "acik": {"tr": "Açık: modern görünüm uygulandı.", "en": "On: the modern look is applied."},
    "kapali": {"tr": "Kapalı: varsayılan CarotOS görünümü.", "en": "Off: the default CarotOS look."},
    "hata": {
        "tr": "Değiştirilemedi (internet yok, yetki verilmedi ya da bir hata oldu). Eski görünüm korunur.",
        "en": "Could not be changed (no internet, permission was not granted or an error occurred). The old "
              "look is kept.",
    },
}

# Sihirbaz ust bandindaki secicilerin yaninda gosterilen aciklama
PICK_TEXTS = {
    "lang_heading": {"tr": "Sistem dili", "en": "System language"},
    "theme_light": {"tr": "Açık Tema", "en": "Light Theme"},
    "theme_dark": {"tr": "Koyu Tema", "en": "Dark Theme"},
    "apply_note": {
        "tr": "Tema hemen değişir. Dil, bu pencere kapanırken kaydedilir ve "
              "oturumu kapatıp yeniden açtığınızda geçerli olur.",
        "en": "The theme changes right away. The language is saved when this window "
              "closes and takes effect after you log out and back in.",
    },
    "wp_heading": {"tr": "Arka planlar", "en": "Wallpapers"},
    "wp_none": {
        "tr": "Henüz arka plan bulunamadı. Arka plan dosyaları sisteme "
              "eklendiğinde burada görünür.",
        "en": "No wallpapers found yet. They appear here once wallpaper files "
              "are added to the system.",
    },
    "wp_note": {
        "tr": "Seçtiğiniz arka plan, “Bitir” düğmesine bastığınızda masaüstüne "
              "uygulanır.",
        "en": "The wallpaper you pick is applied to the desktop when you press "
              "“Finish”.",
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


DIL_HAZIRLIK = {
    "dh_baslik": {"tr": "Sistem dili hazırlığı", "en": "System language setup"},
    "dh_soru": {
        "tr": "“{ad}” sistem dili olarak kullanılabilmesi için dil dosyaları ve gerekirse yazı "
              "tipleri indirilecek (internet ve yönetici parolası gerekir). Şimdi hazırlansın mı?",
        "en": "To use “{ad}” as the system language, language files and, if needed, fonts will be "
              "downloaded (internet and your administrator password are required). Prepare now?"},
    "dh_soru_alt": {
        "tr": "Hayır derseniz CarotOS uygulamaları yine bu dilde açılır; masaüstü şimdiki dilde kalır. "
              "Daha sonra Karşılama'dan tekrar deneyebilirsiniz.",
        "en": "If you choose no, CarotOS apps still open in this language and the desktop stays in the "
              "current language. You can try again later from Welcome."},
    "dh_evet": {"tr": "Hazırla", "en": "Prepare"},
    "dh_kismi": {
        "tr": "Dil etkinleştirildi; ancak ek dil paketleri indirilemedi. İnternete bağlanınca Karşılama'dan "
              "yeniden deneyebilirsiniz.",
        "en": "The language is enabled, but the extra language packages could not be downloaded. Once online, "
              "you can try again from Welcome."},
    "oturum_baslik": {"tr": "Dil kaydedildi", "en": "Language saved"},
    "oturum_soru": {
        "tr": "Masaüstünün yeni dilde açılması için oturumun kapatılıp açılması gerekir. Önce açık "
              "çalışmalarınızı kaydedin. Yeniden başlatmanız gerekmez.",
        "en": "The desktop switches to the new language after you log out and back in. Save your open work "
              "first. You do not need to restart the computer."},
    "oturum_kapat": {"tr": "Oturumu kapat", "en": "Log out"},
    "oturum_sonra": {"tr": "Daha sonra", "en": "Later"},
    "dh_hayir": {"tr": "Şimdi değil", "en": "Not now"},
    "dh_iptal": {"tr": "İptal", "en": "Cancel"},
    "dh_calisiyor": {"tr": "Hazırlanıyor… pencereyi kapatmayın.", "en": "Preparing… please keep this window open."},
    "dh_iptal_edilemedi": {
        "tr": "Hazırlık yönetici yetkisiyle çalıştığı için durdurulamadı; arka planda bitecek. "
              "Bitene kadar yazılım kurmayı ya da güncellemeyi denemeyin. Masaüstü dili değiştirilmedi.",
        "en": "Setup runs with administrator rights, so it could not be stopped; it will finish in the "
              "background. Please do not install or update software until it ends. The desktop language "
              "was not changed."},
    "dh_hata": {
        "tr": "Hazırlık tamamlanamadı. İnternet bağlantısını kontrol edin. CarotOS uygulamaları yine "
              "seçtiğiniz dilde açılır.",
        "en": "Setup could not be completed. Check your internet connection. CarotOS apps still open in "
              "your chosen language."},
}
HUB_TEXTS = {
    "finish_topic": {"tr": "Konuyu bitir", "en": "Finish topic"},
    "skip_topics": {"tr": "Konuları atla", "en": "Skip topics"},
    "to_end": {"tr": "Sona geç", "en": "Go to the end"},
    "topic_pages": {"tr": "{n} sayfa", "en": "{n} pages"},
}
UI.update(HUB_TEXTS)
UI.update(DIL_HAZIRLIK)
UI.update(PICK_TEXTS)

# tr/en sozlukleri her dil icin yedekli olur (eksik ceviri Ingilizceye duser)
UI = dil.zenginlestir(UI)
KONULAR = dil.zenginlestir(gezinme.KONULAR)
PAGES = dil.zenginlestir(PAGES)
SCOPE_NOTE = dil.zenginlestir(SCOPE_NOTE)
MODERN_ANAHTAR = dil.zenginlestir(MODERN_ANAHTAR)
LANG_CHANGED_NOTE = dil.zenginlestir(LANG_CHANGED_NOTE)

# Dil kartlarinin alt yazisi (kartin dilinin Ingilizce adi; tr/en eskisi gibi)
DIL_ALT_ADI = {"tr": "Turkish", "en": "İngilizce", "de": "German", "ru": "Russian",
               "es": "Spanish", "pt": "Portuguese", "ja": "Japanese", "zh": "Chinese",
               "fr": "French", "ar": "Arabic", "hi": "Hindi"}


def atomik_yaz(path, metin, izin=0o600):
    """Dosyayi gecici dosya + os.replace ile yazar (yarida kesilirse eski dosya bozulmaz).

    Basarisizsa OSError firlatir; cagiran karar verir."""
    klasor = os.path.dirname(path) or "."
    fd, gecici = tempfile.mkstemp(prefix=".carotos-tmp-", dir=klasor)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(metin)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(gecici, izin)
        os.replace(gecici, path)
    except BaseException:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def _bozugu_kenara_al(path):
    """Bozuk/beklenmedik biciminde bir dosyayi silmeden '.bozuk' adiyla kenara alir (K-05)."""
    try:
        os.replace(path, path + ".bozuk")
    except OSError:
        pass


def ayarlari_dogrula(stored):
    """Ayar dosyasindan okunan degerleri tur ve deger kumesiyle dogrular (K-05).
    Sorunlu anahtar varsayilana doner; uygulama acilista cokmez."""
    data = dict(DEFAULTS)
    if not isinstance(stored, dict):
        return data
    if stored.get("theme") in ("dark", "light"):
        data["theme"] = stored["theme"]
    if isinstance(stored.get("lang"), str):
        data["lang"] = stored["lang"]
    if isinstance(stored.get("show_on_startup"), bool):
        data["show_on_startup"] = stored["show_on_startup"]
    wp = stored.get("wallpaper")
    if isinstance(wp, str) and "\x00" not in wp:
        data["wallpaper"] = wp
    bk = stored.get("biten_konular")
    if isinstance(bk, list):
        data["biten_konular"] = [b for b in bk if isinstance(b, str)]
    return data


def load_settings():
    stored = None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
    except (OSError, ValueError):
        pass
    data = ayarlari_dogrula(stored)
    data["lang"] = dil.gecerli(data.get("lang"))     # bozuk/bilinmeyen kayitli dil -> en
    return data


def save_settings(data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        atomik_yaz(CONFIG_FILE, json.dumps(data, indent=2))
    except (OSError, ValueError, TypeError):
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
    ("carotos-former", "settings.json"),
    ("carotos-gsd", "settings.json"),
    ("carotene", "settings.json"),
    ("carotos-kurtarma", "arayuz.json"),  # Kurtarma: anahtarlar "lang" ve "theme"
    ("carotos-magaza", "ayarlar.json"),
    ("carotpot", "settings.json"),
    ("carotos-poligon", "ayar.json"),     # Poligon: anahtarlar "dil" ve "gorunum"
    ("filenor", "filenor.json"),          # Filenor: anahtarlar "dil" ve "tema"
]

# Koyu ve acik tema adaylari — sistemde bulunan ilki kullanilir.
DARK_THEMES = ["Arc-Dark", "Materia-dark", "Greybird-dark",
               "Adwaita-dark", "Numix-Dark", "Adwaita"]
LIGHT_THEMES = ["Arc", "Materia", "Greybird", "Adwaita", "Default"]

# Simge temasi adaylari (CarotOS 1.3: Papirus). Sistemde bulunan ilki kullanilir.
DARK_ICON_THEMES = ["Papirus-Dark", "Papirus", "gnome"]
LIGHT_ICON_THEMES = ["Papirus-Light", "Papirus", "gnome"]   # acik temada panel de acik: koyu tepsi simgeleri

# Fare imleci: koyu temada acik (Breeze_Snow), acik temada koyu imlec.
DARK_CURSOR_THEMES = ["Breeze_Light", "Breeze_Snow", "DMZ-White", "Adwaita"]
LIGHT_CURSOR_THEMES = ["breeze_cursors", "DMZ-Black", "Adwaita"]

LOCALE_FOR_LANG = {kod: v["locale"] for kod, v in sd.HAZIRLIK.items()}

# Duvar kagitlarinin arandigi dizinler (ilk dolu olan kullanilir).
# CAROTOS_WP_DIR ile test/ozel dizin one alinabilir.
WALLPAPER_DIRS = [
    os.environ.get("CAROTOS_WP_DIR", ""),
    "/usr/share/backgrounds/carotos",
]
# Varsayilan olarak secili gelecek dosyanin adi (uzantisiz on ek olarak eslenir).
DEFAULT_WALLPAPER = "carotosbackgroundwallpaper1"
WALLPAPER_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
# Masaustu listesine YALNIZCA bu on ekle baslayan dosyalar girer. Boylece
# klasorde baska gorseller (lightdm, splash, ekran goruntuleri) olsa bile
# listede sadece masaustu duvar kagitlari gorunur.
WALLPAPER_PREFIX = "carotosbackgroundwallpaper"


def list_wallpapers():
    """(ad, tam_yol) listesi dondurur. Yalnizca 'carotosbackgroundwallpaper*'
    adli masaustu duvar kagitlari; varsayilan olan basa alinir."""
    bulunan = {}
    for d in WALLPAPER_DIRS:
        if d and os.path.isdir(d):
            for ad in os.listdir(d):
                low = ad.lower()
                if low.startswith(WALLPAPER_PREFIX) and low.endswith(WALLPAPER_EXTS):
                    bulunan.setdefault(ad, os.path.join(d, ad))
            if bulunan:
                break
    ogeler = list(bulunan.items())
    ogeler.sort(key=lambda kv: (
        not kv[0].lower().startswith(DEFAULT_WALLPAPER), kv[0].lower()))
    return ogeler


def apply_wallpaper(path):
    """Secili arka plani tum monitor/workspace'lere uygular (Xfce).

    Kullanici duzeyinde calisir, root gerektirmez. Xfce disinda ya da
    xfconf yoksa sessizce gecer."""
    if not path or not os.path.isfile(path) or not shutil.which("xfconf-query"):
        return False
    props = []
    try:
        r = subprocess.run(["xfconf-query", "-c", "xfce4-desktop", "-l"],
                           capture_output=True, text=True, timeout=5)
        props =[ln.strip() for ln in r.stdout.splitlines()
                 if ln.strip().endswith("/last-image")]
    except (OSError, subprocess.SubprocessError):
        props = []
    if not props:
        props = ["/backdrop/screen0/monitor0/workspace0/last-image"]
    ok = False
    for p in props:
        if xfconf("xfce4-desktop", p, path):
            ok = True
        # Goruntu stili: 5 = ekrana yayilmis (zoomed). Varsa guncellenir.
        xfconf("xfce4-desktop", p.rsplit("/", 1)[0] + "/image-style", "5")
    try:
        subprocess.run(["xfdesktop", "--reload"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass
    return ok


def available_theme(candidates):
    """Sistemde kurulu ilk temayi dondurur."""
    roots = ["/usr/share/themes",
             os.path.join(GLib.get_home_dir(), ".themes")]
    for name in candidates:
        for root in roots:
            if os.path.isdir(os.path.join(root, name)):
                return name
    return None


def available_icon_theme(candidates):
    """Sistemde kurulu ilk simge temasini dondurur."""
    roots = ["/usr/share/icons",
             os.path.join(GLib.get_home_dir(), ".icons"),
             os.path.join(GLib.get_user_data_dir(), "icons")]
    for name in candidates:
        for root in roots:
            if os.path.isfile(os.path.join(root, name, "index.theme")):
                return name
    return None


def available_cursor_theme(candidates):
    """Sistemde kurulu ilk imlec temasini dondurur (cursors/ klasoru olan)."""
    roots = ["/usr/share/icons",
             os.path.join(GLib.get_home_dir(), ".icons"),
             os.path.join(GLib.get_user_data_dir(), "icons")]
    for name in candidates:
        for root in roots:
            if os.path.isdir(os.path.join(root, name, "cursors")):
                return name
    return None


def xfconf(channel, prop, value):
    """Xfce ayarini degistirir. Xfce disinda calisiyorsa sessizce gecer."""
    if not shutil.which("xfconf-query"):
        return False
    try:
        komut = ["xfconf-query", "-c", channel, "-p", prop]
        for ek in (["-s", value], ["-n", "-t", "string", "-s", value]):   # ozellik yoksa olusturulur
            r = subprocess.run(komut + ek, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            if r.returncode == 0:
                return True
        return False                    # K-03: basarisiz komut basarili sayilmaz
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


def sleek_uygulanmis_mi():
    """CarotOS Sleek uygulanmis mi? (carotos-modernlestir yedegi var mi)"""
    return os.path.isfile(os.path.join(os.path.expanduser("~"), ".local", "state", "carotos",
                                       "sleek-yedek.json"))


def _sleek_yedegine_yaz(kanal, ozellik, deger):
    """Sleek acikken secilen tema masaustune degil yedege yazilir: Sleek kapaninca o tema gelir."""
    yol = os.path.join(os.path.expanduser("~"), ".local", "state", "carotos", "sleek-yedek.json")
    try:
        with open(yol, encoding="utf-8") as fh:
            yedek = json.load(fh)
        for x in yedek["xfconf"]:
            if x["kanal"] == kanal and x["ozellik"] == ozellik:
                x.update(var=True, tur="string", deger=deger)
                atomik_yaz(yol, json.dumps(yedek, ensure_ascii=False, indent=1))
                break
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return True                       # yedek bu ayari tutmuyorsa Sleek onu degistirmemistir


def apply_desktop_theme(theme):
    """Masaustu temasini degistirir (kullanici duzeyinde, root gerekmez). Sleek kendi koyu temasini yonetir:
    acikken secim yedege yazilir."""
    xfconf = _sleek_yedegine_yaz if sleek_uygulanmis_mi() else globals()["xfconf"]
    name = available_theme(DARK_THEMES if theme == "dark" else LIGHT_THEMES)
    if not name:
        return False
    ok = xfconf("xsettings", "/Net/ThemeName", name)

    # Simge temasi: kosea gore Papirus-Dark / Papirus (varsa).
    icons = available_icon_theme(
        DARK_ICON_THEMES if theme == "dark" else LIGHT_ICON_THEMES)
    if icons:
        xfconf("xsettings", "/Net/IconThemeName", icons)

    # Imlec temasi: tema ile uyumlu acik/koyu imlec (varsa).
    cursor = available_cursor_theme(
        DARK_CURSOR_THEMES if theme == "dark" else LIGHT_CURSOR_THEMES)
    if cursor:
        xfconf("xsettings", "/Gtk/CursorThemeName", cursor)

    # Pencere temasi ayri bir bilesendir; yalnizca varsa degistirilir.
    if has_xfwm_variant(name):
        xfconf("xfwm4", "/general/theme", name)
    # Paneller, panel menuleri ve GTK4 uygulamalari (Sleek acikken betik kendisi dokunmaz)
    try:
        subprocess.run(["/usr/bin/carotos-panel-eslestir", "--tema", "dark" if theme == "dark" else "light"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    except (OSError, subprocess.SubprocessError):
        pass
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
            else:
                _bozugu_kenara_al(path)         # K-05: liste vb. kokluyse silmeden kenara al
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            _bozugu_kenara_al(path)             # bozuk JSON/UTF-8: sessizce ezme, .bozuk olarak sakla
        data["lang"] = lang
        data["theme"] = theme
        if folder == "carotos-panel":
            # Guvenlik Paneli dil anahtarini "language" diye okur; "lang"
            # yazmak onu hic etkilemiyordu.
            data["language"] = lang
        elif folder == "carotos-former":
            # Former dil/tema anahtarlarini "dil"/"tema" diye okur.
            data["dil"] = lang
            data["tema"] = theme
        elif folder == "carotos-gsd":
            # GSD de Former ile ayni "dil"/"tema" anahtarlarini kullanir.
            data["dil"] = lang
            data["tema"] = theme
        elif folder == "carotos-poligon":
            # Poligon "dil" ve "gorunum" (dark/light) anahtarlarini okur
            data.pop("lang", None)
            data.pop("theme", None)
            data["dil"] = lang
            data["gorunum"] = theme
        elif folder == "filenor":
            # Filenor "dil" ve "tema" (dark/light) anahtarlarini okur
            data.pop("lang", None)
            data.pop("theme", None)
            data["dil"] = lang
            data["tema"] = theme
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            atomik_yaz(path, json.dumps(data, indent=2))
        except (OSError, ValueError, TypeError):
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
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
            existing = fh.read()
    except OSError:
        pass

    # Isaretciler yalnizca tam birer kez ve dogru sirada ise yerinde degistirilir (K-04)
    if (existing.count(XSESSION_START) == 1 and existing.count(XSESSION_END) == 1
            and existing.index(XSESSION_START) < existing.index(XSESSION_END)):
        before = existing.split(XSESSION_START)[0]
        after = existing.split(XSESSION_END, 1)[1]
        content = before + block + after
    else:
        content = (existing.rstrip("\n") + "\n\n" if existing.strip()
                   else "") + block + "\n"

    try:
        atomik_yaz(path, content, 0o644)
        return True
    except (OSError, ValueError):
        return False


def _write_dmrc(locale):
    """LightDM'in eski yolu. Zararsiz, okuyan sistemlerde ise yarar."""
    path = os.path.join(GLib.get_home_dir(), ".dmrc")
    session = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
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
        atomik_yaz(path, "\n".join(lines) + "\n", 0o644)
        return True
    except (OSError, ValueError):
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
            Gio.DBusCallFlags.NONE, 3000, None)
        path = result.unpack()[0]
        user = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            "org.freedesktop.Accounts", path,
            "org.freedesktop.Accounts.User", None)
        user.call_sync("SetLanguage", GLib.Variant("(s)", (locale,)),
                       Gio.DBusCallFlags.NONE, 3000, None)
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
    # Uretilmemis bir locale'i oturuma yazmak terminali/yazi tiplerini bozar (sessizce C'ye duser):
    # tr/en ISO'dadir; digerleri once hazirlanmali (bkz. sistem_dili, carotos-dil-hazirla)
    if not sd.locale_var_mi(lang, sd.locale_a()):
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

    def __init__(self, settings):
        super().__init__(title=UI["window_title"][settings["lang"]])

        self.settings = settings
        self.lang = settings["lang"]
        self.theme = settings["theme"]
        self.wallpaper = settings.get("wallpaper", "") or ""
        self.wp_cards = {}
        self.gezinme = gezinme.Gezinme(settings.get("biten_konular", []))
        self.hub_kartlari = {}

        self.set_default_size(940, 660)
        self.set_size_request(820, 580)
        self.set_position(Gtk.WindowPosition.CENTER)
        logo = find_logo()
        if logo:
            try:
                self.set_icon_from_file(logo)
            except GLib.Error:
                pass
        self._uygulanan = (self.lang, self.theme, self.wallpaper)
        self._oturum_dili = dil.varsayilan_dil()
        self._dil_yazildi = False
        self.connect("delete-event", self.on_delete)
        self.connect("destroy", self.on_destroy)

        # Ortak grafit tema (tema.uygula); asagidaki saglayici yalnizca
        # sihirbaza ozgu siniflari boyar ve ortak temanin ustunde durur.
        tema.uygula(self.theme, VURGU)
        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
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
        box.get_style_context().add_class("pad-header")

        # Ust bantta logo yok: pencere kenarindaki simgeyle tekrar oluyordu.
        wordmark = Gtk.Label(label="CarotOS", xalign=0.0)
        wordmark.get_style_context().add_class("wordmark")
        box.pack_start(wordmark, False, False, 0)

        version = Gtk.Label(label=f"{APP_VERSION} \u00b7 {APP_CODENAME}", xalign=0.0)
        version.get_style_context().add_class("version-tag")
        version.set_valign(Gtk.Align.CENTER)
        box.pack_start(version, False, False, 0)

        # Sag taraf: dil ve tema secicileri
        self.lang_combo = tema.AcilirSecim()
        for kod, ad, taslak in dil.etkin_diller():       # yalniz cevirisi hazir diller
            self.lang_combo.append(kod, dil.secici_adi(kod, ad, taslak))
        self.lang_combo.set_active_id(self.lang)
        self._lang_combo_id = self.lang_combo.connect("changed", self.on_lang_changed)
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
        box.set_center_widget(self.dots)          # noktalar bolume gore _noktalari_kur() ile dolar

        self.next_btn = Gtk.Button()
        self.next_btn.get_style_context().add_class("suggested-action")
        self.next_btn.connect("clicked", self.on_next)
        box.pack_end(self.next_btn, False, False, 0)

        self.back_btn = Gtk.Button()
        self.back_btn.connect("clicked", self.on_back)
        box.pack_end(self.back_btn, False, False, 0)

        # Hub'da ve konularda her zaman gorunur; baslangicta (zorunlu bolum) gizli
        self.skip_btn = Gtk.Button()
        self.skip_btn.set_no_show_all(True)
        self.skip_btn.connect("clicked", self.on_skip)
        box.pack_end(self.skip_btn, False, False, 0)

        return box

    # -- sayfalar ----------------------------------------------------------

    def build_pages(self):
        for page in PAGES:
            self.stack.add_named(self.build_page(page), page["id"])

    def build_page(self, page):
        if page.get("custom") == "appearance":
            return self.build_appearance_page(page)
        if page.get("custom") == "wallpaper":
            return self.build_wallpaper_page(page)
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

        # Cevirisi hazir her dil icin bir kart; uc sutunlu izgara (2 dilde eskisi gibi
        # iki kart, daha cok dilde alt satirlara iner).
        lang_row = Gtk.Grid(column_spacing=14, row_spacing=14)
        lang_row.set_column_homogeneous(True)
        lang_row.set_margin_top(14)
        outer.pack_start(lang_row, False, False, 0)

        self.lang_cards = {}
        etkin = dil.etkin_diller()
        sutun = 2 if len(etkin) <= 2 else 3             # iki dilde eski gorunum
        for sira, (code, name, taslak) in enumerate(etkin):
            card = self._lang_card(code, dil.gorunen_ad(code, name), DIL_ALT_ADI.get(code, ""))
            self.lang_cards[code] = card
            lang_row.attach(card["event"], sira % sutun, sira // sutun, 1, 1)

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
            self._masaustu_temasi()     # masaustu baska yoldan degismis olabilir (or. Sleek kapatildi)
            return True
        self.theme = key
        self.settings["theme"] = key
        save_settings(self.settings)
        self.apply_theme()
        self._masaustu_temasi()
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

    # -- masaustu arka plani sayfasi ---------------------------------------

    def build_wallpaper_page(self, page):
        """Kurulu duvar kagitlarini kucuk onizlemelerle listeler. Secim
        ANINDA uygulanmaz; sihirbazin sonundaki 'Bitir' dugmesinde uygulanir."""
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

        wallpapers = list_wallpapers()

        # Varsayilan secim: kayitli secim yoksa DEFAULT_WALLPAPER, o da yoksa
        # listedeki ilk arka plan.
        if not self.wallpaper or not os.path.isfile(self.wallpaper):
            if wallpapers:
                varsayilan = next(
                    (p for ad, p in wallpapers
                     if ad.lower().startswith(DEFAULT_WALLPAPER)),
                    wallpapers[0][1])
                self.wallpaper = varsayilan

        self.wp_cards = {}

        if not wallpapers:
            bos = Gtk.Label(label=UI["wp_none"][self.lang])
            bos.get_style_context().add_class("page-subtitle")
            bos.set_line_wrap(True)
            bos.set_justify(Gtk.Justification.CENTER)
            bos.set_margin_top(40)
            outer.pack_start(bos, False, False, 0)
            self._sleek_karti_ekle(outer)
            return scroller

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(16)
        grid.set_column_homogeneous(True)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_margin_top(26)
        outer.pack_start(grid, False, False, 0)

        for i, (ad, path) in enumerate(wallpapers):
            card = self._wallpaper_card(ad, path)
            self.wp_cards[path] = card
            grid.attach(card["event"], i % 3, i // 3, 1, 1)

        self._sleek_karti_ekle(outer)

        note = Gtk.Label(label=UI["wp_note"][self.lang], xalign=0.0)
        note.get_style_context().add_class("body-text")
        note.set_line_wrap(True)
        note.set_justify(Gtk.Justification.CENTER)
        note.set_halign(Gtk.Align.CENTER)
        inner = Gtk.Box()
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        inner.set_margin_start(20); inner.set_margin_end(20)
        inner.pack_start(note, True, True, 0)
        note_box = Gtk.Box()
        note_box.get_style_context().add_class("note-box")
        note_box.set_margin_top(28)
        note_box.set_halign(Gtk.Align.CENTER)
        note_box.set_size_request(self.CARD_WIDTH, -1)
        note_box.pack_start(inner, True, True, 0)
        outer.pack_start(note_box, False, False, 0)

        self._sync_wallpaper_selection()
        return scroller

    def _sleek_karti_ekle(self, outer):
        """CarotOS Sleek ac/kapa karti (internetten paket indirir; geri alinabilir).
        Gorunum arka planla birlikte secildigi icin arka plan sayfasindadir."""
        modern_kart, self.modern_anahtar = self._yetkili_anahtar(
            MODERN_ANAHTAR, sleek_uygulanmis_mi(),
            lambda istenen: self.modern_calistir(self.modern_komutlari(istenen)))
        modern_kart.set_margin_top(28)
        modern_kart.set_halign(Gtk.Align.CENTER)
        modern_kart.set_size_request(self.CARD_WIDTH, -1)
        outer.pack_start(modern_kart, False, False, 0)

    def _wallpaper_card(self, name, path):
        event = Gtk.EventBox()
        event.connect("button-press-event", self._on_wallpaper_pick, path)

        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        frame.get_style_context().add_class("pick-card")
        # Ic bosluk: onizleme gorseli kartin yuvarlak kenarina yapismasin,
        # kosesinden tasmasin.
        frame.get_style_context().add_class("pad-xs")
        event.add(frame)

        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 188, 106, False)
            img = Gtk.Image.new_from_pixbuf(pb)
        except GLib.Error:
            img = Gtk.Image.new_from_icon_name("image-x-generic",
                                               Gtk.IconSize.DIALOG)
            img.set_pixel_size(88)
        img.get_style_context().add_class("wp-thumb")
        img.set_halign(Gtk.Align.CENTER)
        img.set_valign(Gtk.Align.CENTER)
        frame.pack_start(img, False, False, 0)

        return {"event": event, "frame": frame}

    def _sync_wallpaper_selection(self):
        for path, card in getattr(self, "wp_cards", {}).items():
            ctx = card["frame"].get_style_context()
            if path == self.wallpaper:
                ctx.add_class("pick-selected")
            else:
                ctx.remove_class("pick-selected")

    def _on_wallpaper_pick(self, _widget, _event, path):
        if path == self.wallpaper:
            return True
        self.wallpaper = path
        self.settings["wallpaper"] = path
        save_settings(self.settings)
        self._sync_wallpaper_selection()
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
        # Metin kartlari, baslik hizasindan biraz iceride dursun diye govdeye
        # yan bosluk verilir (adalarin sag/sol gap'i).
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

    # Metin kartlarinin sabit genisligi. Sutundan dar olmasi, kartlarin iki
    # yaninda belirgin bir bosluk (ada gap'i) birakir.
    CARD_WIDTH = 600

    @classmethod
    def card(cls, child, style="card"):
        """Icerigi hafif acik zeminli, sabit genislikte ortalanmis bir kutuya
        yerlestirir (iki yaninda bosluk kalir)."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class(style)
        box.get_style_context().add_class("pad")
        box.set_halign(Gtk.Align.CENTER)
        box.set_size_request(cls.CARD_WIDTH, -1)
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

    def build_hub_block(self):
        """Konu kartlari (iki sutun). Karta tiklayinca konu acilir; bitirilen konunun karti ✓ alir."""
        self.hub_kartlari = {}
        izgara = Gtk.Grid()
        izgara.set_column_spacing(14)
        izgara.set_row_spacing(14)
        izgara.set_halign(Gtk.Align.CENTER)
        for n, konu in enumerate(KONULAR):
            kart = Gtk.EventBox()
            kart.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            kart.connect("button-press-event", self._on_konu_tikla, konu["id"])
            kart.connect("realize", self._el_isaretci_yap)
            ic = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            ic.get_style_context().add_class("konu-kart")
            ic.get_style_context().add_class("pad")
            ic.set_size_request(292, 124)
            baslik = Gtk.Label(xalign=0.0)
            baslik.set_markup("<b>%s</b>" % GLib.markup_escape_text(dil.metin(konu["baslik"], self.lang)))
            baslik.set_line_wrap(True)
            ic.pack_start(baslik, False, False, 0)
            aciklama = Gtk.Label(label=dil.metin(konu["aciklama"], self.lang), xalign=0.0)
            aciklama.set_line_wrap(True)
            aciklama.set_max_width_chars(36)
            aciklama.get_style_context().add_class("body-text")
            ic.pack_start(aciklama, True, True, 0)
            alt = Gtk.Label(xalign=0.0)
            alt.get_style_context().add_class("page-subtitle")
            ic.pack_end(alt, False, False, 0)
            kart.add(ic)
            izgara.attach(kart, n % 2, n // 2, 1, 1)
            self.hub_kartlari[konu["id"]] = (alt, len(konu["sayfalar"]))
        self._hub_guncelle()
        return izgara

    def _hub_guncelle(self):
        for kimlik, (alt, sayfa_sayisi) in self.hub_kartlari.items():
            metin = dil.T(UI["topic_pages"], self.lang, n=sayfa_sayisi)
            ctx = alt.get_style_context()
            if kimlik in self.gezinme.bitenler:
                alt.set_text("\u2713 " + metin)
                ctx.add_class("konu-bitti")
            else:
                alt.set_text(metin)
                ctx.remove_class("konu-bitti")

    def _on_konu_tikla(self, _widget, _event, kimlik):
        if self.gezinme.konuyu_ac(kimlik):
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
            self.refresh()
        return True

    def build_block(self, kind, payload):
        if kind == "hub":
            return self.build_hub_block()
        if kind == "p":
            label = Gtk.Label(label=payload[self.lang], xalign=0.0)
            label.set_line_wrap(True)
            label.set_max_width_chars(58)
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
            label.set_max_width_chars(54)
            label.get_style_context().add_class("note-text")
            inner.pack_start(label, True, True, 0)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.get_style_context().add_class("note-box")
            box.get_style_context().add_class("pad-sm")
            box.set_halign(Gtk.Align.CENTER)
            box.set_size_request(self.CARD_WIDTH, -1)
            box.pack_start(inner, True, True, 0)
            return box

        if kind == "code":
            label = Gtk.Label(label=payload, xalign=0.0)
            label.set_selectable(True)
            label.set_line_wrap(True)                 # uzun komutlar kutudan tasmasin
            label.set_line_wrap_mode(Pango.WrapMode.CHAR)
            label.set_max_width_chars(64)             # yoksa dogal genislik tum satir olur, kaydirma calismaz
            label.get_style_context().add_class("code-text")
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.get_style_context().add_class("code-box")
            box.get_style_context().add_class("pad-sm")
            box.set_halign(Gtk.Align.CENTER)
            box.set_size_request(self.CARD_WIDTH, -1)
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
                text.set_max_width_chars(54)
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
                value_label.set_max_width_chars(46)
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
                value_label.set_max_width_chars(46)
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
            grid.set_halign(Gtk.Align.CENTER)
            grid.set_size_request(self.CARD_WIDTH, -1)
            for i, (key, value) in enumerate(payload):
                cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                cell.get_style_context().add_class("tile")
                cell.get_style_context().add_class("pad-sm")

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

        if kind == "mac_anahtar":
            return self.build_mac_anahtar(payload)

        if kind == "ufw_anahtar":
            return self.build_ufw_anahtar(payload)

        if kind == "action":
            baslik, alt_metin, komut = payload
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            title = Gtk.Label(label=baslik[self.lang], xalign=0.0)
            title.get_style_context().add_class("action-title")
            inner.pack_start(title, False, False, 0)
            sub = Gtk.Label(label=alt_metin[self.lang], xalign=0.0)
            sub.set_line_wrap(True)
            sub.set_max_width_chars(58)
            sub.get_style_context().add_class("action-sub")
            inner.pack_start(sub, False, False, 0)

            btn = Gtk.Button()
            btn.get_style_context().add_class("action-card")
            btn.add(inner)
            btn.set_halign(Gtk.Align.CENTER)
            btn.set_size_request(self.CARD_WIDTH, -1)
            btn.connect("clicked", self.on_action_clicked, komut)
            return btn

        return None

    MAC_AYAR = "/usr/sbin/carotos-mac-ayar"
    MAC_DOSYASI = "/etc/NetworkManager/conf.d/91-carotos-mac.conf"

    def mac_acik_mi(self):
        return os.path.isfile(self.MAC_DOSYASI)

    def mac_komutu(self, acik):
        """Yetkili betigin komutu (pkexec ile); testte yerine kopya konur."""
        return ["pkexec", self.MAC_AYAR, "ac" if acik else "kapat"]

    def mac_yetkili_calistir(self, komut):
        try:
            return subprocess.run(komut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120).returncode
        except (OSError, subprocess.SubprocessError):
            return 1

    TEMA_KUR = "/usr/sbin/carotos-tema-kur"
    MODERNLESTIR = "/usr/bin/carotos-modernlestir"

    def modern_komutlari(self, acik):
        """Sirayla calisacak komutlar: ac = paketleri kur (pkexec) + gorunumu uygula; kapat = geri al."""
        python = "/usr/bin/python3"
        if acik:
            pkexec = yetkili.sistem_yolu("pkexec") or "pkexec"
            return [[pkexec, self.TEMA_KUR, "kur"], [python, "-I", self.MODERNLESTIR, "uygula"]]
        return [[python, "-I", self.MODERNLESTIR, "geri-al"]]

    def modern_calistir(self, komutlar):
        """0: hepsi basarili; aksi halde 1. Paket indirme uzun surebilir (30 dk sinir).

        Her komut basarisizsa BIR KEZ yeniden denenir (gecici ag/kilit/ilk acilis hatasi tek
        tikta kurulumu dusurmesin; komutlar tekrar calistirilabilir). Cikti
        ~/.local/state/carotos/sleek-kurulum.log dosyasina yazilir (sorun giderme)."""
        gunluk = None
        try:
            klasor = os.path.join(os.path.expanduser("~"), ".local", "state", "carotos")
            os.makedirs(klasor, mode=0o700, exist_ok=True)
            gunluk = open(os.path.join(klasor, "sleek-kurulum.log"), "ab")
        except OSError:
            gunluk = None
        hedef = gunluk if gunluk is not None else subprocess.DEVNULL
        try:
            for komut in komutlar:
                kod = 1
                for deneme in range(2):
                    try:
                        kod = subprocess.run(komut, stdin=subprocess.DEVNULL, stdout=hedef,
                                             stderr=subprocess.STDOUT, timeout=1800).returncode
                    except (OSError, subprocess.SubprocessError):
                        kod = 1
                    if kod == 0 or kod in (126, 127):     # 126/127: yetki verilmedi ya da yok
                        break
                if kod != 0:
                    return 1
            return 0
        finally:
            if gunluk is not None:
                gunluk.close()

    UFW_AYAR = "/usr/sbin/carotos-ufw-ayar"
    UFW_CONF = "/etc/ufw/ufw.conf"

    def ufw_acik_mi(self):
        """True/False; okunamazsa None ("durum bilinmiyor"). Root gerekmez."""
        return ufw_durumu(self.UFW_CONF)

    def ufw_komutu(self, acik):
        """Yetkili betigin komutu (pkexec ile); testte yerine kopya konur."""
        return ["pkexec", self.UFW_AYAR, "ac" if acik else "kapat"]

    def ufw_yetkili_calistir(self, komut):
        try:
            return subprocess.run(komut, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, timeout=120).returncode
        except (OSError, subprocess.SubprocessError):
            return 1

    def build_mac_anahtar(self, p):
        """Sahte MAC anahtari: yetkili betigi pkexec ile calistirir; pencere donmaz, basarisizsa anahtar eski haline doner."""
        kart, anahtar = self._yetkili_anahtar(
            p, self.mac_acik_mi(),
            lambda istenen: self.mac_yetkili_calistir(self.mac_komutu(istenen)))
        self.mac_anahtari = anahtar                        # testler icin
        return kart

    def build_ufw_anahtar(self, p):
        """Guvenlik duvari anahtari: MAC anahtariyla ayni mantik (pkexec carotos-ufw-ayar)."""
        kart, anahtar = self._yetkili_anahtar(
            p, self.ufw_acik_mi(),
            lambda istenen: self.ufw_yetkili_calistir(self.ufw_komutu(istenen)))
        self.ufw_anahtari = anahtar                        # testler icin
        return kart

    def _yetkili_anahtar(self, p, baslangic, calistir):
        """Ortak anahtar karti. baslangic True/False/None (None: durum bilinmiyor, anahtar kapali gorunur).
        calistir(istenen) arka planda cagrilir ve cikis kodunu dondurur; basarisizsa anahtar eski haline doner."""
        import threading
        satir = Gtk.Box(spacing=14)
        metin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        baslik = Gtk.Label(label=p["baslik"][self.lang], xalign=0.0)
        baslik.set_line_wrap(True)
        baslik.set_max_width_chars(42)
        baslik.get_style_context().add_class("action-title")
        metin.pack_start(baslik, False, False, 0)
        alt = Gtk.Label(label=p["alt"][self.lang], xalign=0.0)
        alt.set_line_wrap(True)
        alt.set_max_width_chars(42)
        alt.get_style_context().add_class("body-text")
        metin.pack_start(alt, False, False, 0)
        durum = Gtk.Label(xalign=0.0)
        durum.set_line_wrap(True)
        durum.set_max_width_chars(42)
        durum.get_style_context().add_class("action-sub")
        metin.pack_start(durum, False, False, 0)
        satir.pack_start(metin, True, True, 0)
        anahtar = Gtk.Switch()
        anahtar.set_valign(Gtk.Align.CENTER)
        satir.pack_end(anahtar, False, False, 0)

        def yaz(acik):
            durum.set_text((p["acik"] if acik else p["kapali"])[self.lang])

        anahtar.set_active(bool(baslangic))
        if baslangic is None and "bilinmiyor" in p:
            durum.set_text(p["bilinmiyor"][self.lang])
        else:
            yaz(bool(baslangic))

        def degisti(sw, istenen):
            sw.set_sensitive(False)

            def calis():
                tamam = calistir(istenen) == 0
                GLib.idle_add(bitti, tamam, istenen)
            threading.Thread(target=calis, daemon=True).start()
            return True                                    # durumu biz ayarliyoruz (basarisizsa eski haline doner)

        def bitti(tamam, istenen):
            anahtar.set_sensitive(True)
            if tamam:
                anahtar.set_state(istenen)
                yaz(istenen)
            else:
                # set_active "state-set" sinyalini yeniden tetikler (betik tekrar calisirdi): sinyal gecici bloklanir
                anahtar.handler_block(kimlik)
                anahtar.set_active(not istenen)
                anahtar.handler_unblock(kimlik)
                anahtar.set_state(not istenen)
                durum.set_text(p["hata"][self.lang])
            return False

        kimlik = anahtar.connect("state-set", degisti)
        return self.card(satir), anahtar                   # diger bloklarla ayni kutu

    def on_action_clicked(self, _button, komut):
        """'action' turundeki bir kutuya tiklandiginda ilgili uygulamayi acar."""
        try:
            subprocess.Popen(komut)
        except OSError:
            pass

    # -- durum yenileme ----------------------------------------------------

    def refresh(self):
        g = self.gezinme
        self.stack.set_visible_child_name(g.sayfa_id())

        self.back_btn.set_label(UI["back"][self.lang])
        self.back_btn.set_sensitive(g.geri_var())

        etiket = {"ileri": "next", "konuyu_bitir": "finish_topic",
                  "sona_gec": "to_end", "bitir": "finish"}[g.ileri_etiketi()]
        self.next_btn.set_label(UI[etiket][self.lang])
        self.skip_btn.set_label(UI["skip_topics"][self.lang])
        if g.atla_gorunur():
            self.skip_btn.show()
        else:
            self.skip_btn.hide()

        if self.lang_combo.get_active_id() != self.lang:     # K-07: kartla secilen dil ust bantta da gorunsun
            self.lang_combo.handler_block(self._lang_combo_id)
            self.lang_combo.set_active_id(self.lang)
            self.lang_combo.handler_unblock(self._lang_combo_id)

        self.check.set_label(UI["dont_show"][self.lang])
        self.theme_btn.set_label(
            UI["theme_light"][self.lang] if self.theme == "dark"
            else UI["theme_dark"][self.lang])
        self.set_title(UI["window_title"][self.lang])

        self._sync_selection()
        self._noktalari_kur()
        self._hub_guncelle()

    def _noktalari_kur(self):
        """Alt banttaki noktalar yalnizca icinde bulunulan bolumu (baslangic ya da konu) gosterir."""
        for cocuk in self.dots.get_children():
            self.dots.remove(cocuk)
        aktif = self.gezinme.bolum_indeksi()
        for i in range(len(self.gezinme.bolum_sayfalari())):
            dot = Gtk.Label(label="")
            dot.get_style_context().add_class("dot")
            if i == aktif:
                dot.get_style_context().add_class("dot-active")
            dot_box = Gtk.EventBox()
            dot_box.add(dot)
            dot_box.connect("button-press-event", self.on_dot_clicked, i)
            dot_box.connect("realize", self._el_isaretci_yap)
            self.dots.pack_start(dot_box, False, False, 0)
        self.dots.show_all()

    def sayfaya_git(self, sayfa_id):
        """Bir sayfa kimligine dogrudan git (arayuzu yeniler)."""
        if self.gezinme.sayfaya_git(sayfa_id):
            self.refresh()

    def _konulari_kaydet(self):
        self.settings["biten_konular"] = self.gezinme.biten_konular()
        save_settings(self.settings)

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
        if self.gezinme.ileri() == "bitir":
            self._konulari_kaydet()
            try:
                self.apply_choices()
            except Exception as exc:                  # K-04: tek hata sihirbazi acik birakmasin
                print("carotos-welcome: secimler uygulanirken hata:", exc, file=sys.stderr)
            finally:
                # K-06: sihirbaz sonuna kadar gezilip Bitir'e basildi -> bir daha kendiliginden
                # acilmaz (yaridan kapatilirsa ayar degismez, sonraki oturumda yine gelir;
                # menuden her zaman acilabilir).
                try:
                    self.settings["show_on_startup"] = False
                    save_settings(self.settings)
                except Exception as exc:
                    print("carotos-welcome: ayar yazilamadi:", exc, file=sys.stderr)
                self.close()
            return
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self._konulari_kaydet()
        self.refresh()

    def on_skip(self, _button):
        """'Konulari atla': hub'dan ya da bir konudan son sayfaya."""
        if self.gezinme.atla():
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
            self.refresh()

    def apply_choices(self):
        """Sihirbaz kapanirken secimleri sisteme uygular.

        Iletisim kutulari (dil hazirligi) ana is parcacigindadir; xfconf/D-Bus gibi
        bloklayabilen adimlar ayri is parcacigindadir ve bu sirada GTK dongusu
        donmadan islenir (K-03). Her adim ayri korunur (K-04)."""
        try:
            hazir = self.prepare_language()
        except Exception as exc:
            print("carotos-welcome: dil hazirligi hatasi:", exc, file=sys.stderr)
            hazir = False
        self.set_sensitive(False)
        t = threading.Thread(target=self._sistemi_uygula, args=(hazir,), daemon=True)
        t.start()
        while t.is_alive():
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            t.join(0.03)
        self.set_sensitive(True)
        self._uygulanan = (self.lang, self.theme, self.wallpaper)
        if self._dil_yazildi and self.lang != self._oturum_dili:
            self._oturum_kapat_sor()

    def _oturum_kapat_sor(self):
        soru = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                 buttons=Gtk.ButtonsType.NONE, text=UI["oturum_baslik"][self.lang])
        soru.format_secondary_text(UI["oturum_soru"][self.lang])
        soru.add_button(UI["oturum_sonra"][self.lang], Gtk.ResponseType.CANCEL)
        soru.add_button(UI["oturum_kapat"][self.lang], Gtk.ResponseType.OK)
        yanit = soru.run()
        soru.destroy()
        if yanit == Gtk.ResponseType.OK and shutil.which("xfce4-session-logout"):
            subprocess.Popen(["xfce4-session-logout", "--logout"])

    def _sistemi_uygula(self, hazir):
        adimlar = [lambda: apply_desktop_theme(self.theme),
                   lambda: apply_sibling_settings(self.lang, self.theme)]
        # K-02: oturum dili yalnizca hazirlik tamamsa (ya da gerekmiyorsa) yazilir
        # (locale uretildiyse ek paketlerin eksikligi dili engellemez)
        if hazir:
            adimlar.append(self._oturum_dilini_yaz)
        adimlar.append(lambda: apply_wallpaper(self.wallpaper))
        for adim in adimlar:
            try:
                adim()
            except Exception as exc:
                print("carotos-welcome: adim hatasi:", exc, file=sys.stderr)

    def _oturum_dilini_yaz(self):
        self._dil_yazildi = apply_session_language(self.lang)

    def prepare_language(self):
        """Secilen dilin locale'i/paketleri eksikse sorar ve hazirlar (ISO kucuk kalsin diye
        dil paketleri istenince kurulur). Reddedilirse/basarisiz olursa oturum dili degismez;
        CarotOS uygulamalari yine secilen dilde acilir (kendi cevirileri ISO'dadir)."""
        if not sd.hazirlik_gerekli_mi(self.lang):
            return True
        ad = dict(dil.DILLER).get(self.lang, self.lang)
        soru = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                 buttons=Gtk.ButtonsType.NONE, text=UI["dh_baslik"][self.lang])
        soru.format_secondary_text(dil.T(UI["dh_soru"], self.lang, ad=ad) + "\n\n" + UI["dh_soru_alt"][self.lang])
        soru.add_button(UI["dh_hayir"][self.lang], Gtk.ResponseType.CANCEL)
        soru.add_button(UI["dh_evet"][self.lang], Gtk.ResponseType.OK)
        yanit = soru.run()
        soru.destroy()
        if yanit != Gtk.ResponseType.OK:
            return False
        return self._run_language_setup(self.lang)

    def _run_language_setup(self, kod):
        """pkexec ile carotos-dil-hazirla'yi arka planda calistirir; pencere donmaz."""
        dlg = Gtk.Dialog(title=UI["dh_baslik"][self.lang], transient_for=self, modal=True)
        kutu = dlg.get_content_area()
        kutu.set_spacing(10)
        kutu.set_border_width(16)
        satir = Gtk.Box(spacing=10)
        spinner = Gtk.Spinner()
        spinner.start()
        satir.pack_start(spinner, False, False, 0)
        durum = Gtk.Label(label=UI["dh_calisiyor"][self.lang], xalign=0)
        durum.set_line_wrap(True)
        satir.pack_start(durum, True, True, 0)
        kutu.pack_start(satir, False, False, 0)
        dlg.add_button(UI["dh_iptal"][self.lang], Gtk.ResponseType.CANCEL)
        dlg.show_all()
        kayit = {"surec": None, "kod": 1}

        def calis():
            try:
                surec = subprocess.Popen(sd.hazirla_komutu(kod), stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True, bufsize=1)
                kayit["surec"] = surec
                for ln in surec.stdout:
                    if ln.startswith("[carotos-dil]"):
                        GLib.idle_add(durum.set_text, ln.rstrip()[len("[carotos-dil] "):])
                kayit["kod"] = surec.wait()
            except OSError:
                kayit["kod"] = 1
            GLib.idle_add(dlg.response, Gtk.ResponseType.OK)

        threading.Thread(target=calis, daemon=True).start()
        yanit = dlg.run()
        surec = kayit["surec"]
        durduruldu = True
        try:
            if yanit == Gtk.ResponseType.CANCEL and surec is not None and surec.poll() is None:
                try:
                    surec.terminate()
                except OSError:
                    durduruldu = False      # pkexec ile root olmus surece sinyal gonderilemez (K-01/O-03)
        finally:
            dlg.destroy()
        if yanit != Gtk.ResponseType.OK:
            if not durduruldu:
                bilgi = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.INFO,
                                          buttons=Gtk.ButtonsType.CLOSE, text=UI["dh_baslik"][self.lang])
                bilgi.format_secondary_text(UI["dh_iptal_edilemedi"][self.lang])
                bilgi.run()
                bilgi.destroy()
            return False
        kismi = kayit["kod"] == 4        # locale hazir, ek paketler inmedi
        if kayit["kod"] != 0:
            hata = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
                                     buttons=Gtk.ButtonsType.CLOSE, text=UI["dh_baslik"][self.lang])
            hata.format_secondary_text(UI["dh_kismi" if kismi else "dh_hata"][self.lang])
            hata.run()
            hata.destroy()
            return kismi
        return True

    def on_back(self, _button):
        if self.gezinme.geri_var():
            self.gezinme.geri()
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)
            self.refresh()

    def _el_isaretci_yap(self, widget):
        pencere = widget.get_window()
        if pencere:
            pencere.set_cursor(
                Gdk.Cursor.new_from_name(widget.get_display(), "pointer"))

    def on_dot_clicked(self, _widget, _event, index):
        onceki = self.gezinme.bolum_indeksi()
        if index == onceki:
            return
        self.stack.set_transition_type(
            Gtk.StackTransitionType.SLIDE_LEFT if index > onceki else Gtk.StackTransitionType.SLIDE_RIGHT)
        if self.gezinme.bolumde_sec(index):
            self.refresh()

    def on_lang_changed(self, combo):
        chosen = combo.get_active_id()
        if not chosen or chosen == self.lang:
            return
        self.lang = chosen
        self.settings["lang"] = chosen
        save_settings(self.settings)

        # Sisteme uygulama "Bitir"de ya da pencere kapanirken yapilir.
        self.rebuild()

    def _masaustu_temasi(self):
        """Masaustu temasi secilir secilmez degisir (xfconf bloklayabilir: ayri is parcacigi)."""
        threading.Thread(target=apply_desktop_theme, args=(self.theme,), daemon=True).start()

    def on_theme_toggled(self, _button):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings["theme"] = self.theme
        save_settings(self.settings)

        self.apply_theme()
        self._masaustu_temasi()
        self.refresh()

    def on_check_toggled(self, check):
        self.settings["show_on_startup"] = not check.get_active()
        save_settings(self.settings)

    def on_delete(self, *_a):
        """Bitir'e basilmadan kapatilirsa da secimler kaybolmaz."""
        if not self.get_sensitive():
            return True                 # uygulama suruyor
        if (self.lang, self.theme, self.wallpaper) != self._uygulanan:
            try:
                self.apply_choices()
            except Exception as exc:
                print("carotos-welcome: secimler uygulanirken hata:", exc, file=sys.stderr)
        return False

    def on_destroy(self, _widget):
        save_settings(self.settings)
        Gtk.main_quit()

    # -- tema --------------------------------------------------------------

    def apply_theme(self):
        p = tema.uygula(self.theme, VURGU)
        vz = tema.rgba_metni(p["vurgu"], 0.14)

        css = f"""
        .header {{ background-color: {p['yan']}; }}
        .pad {{ padding: 18px 22px; }}
        .pad-sm {{ padding: 14px 16px; }}
        .pad-xs {{ padding: 10px; }}
        .pad-header {{ padding: 12px 16px; }}
        .wordmark {{ font-size: 132%; font-weight: 800; letter-spacing: 1px; }}
        .version-tag {{ color: {p['soluk']}; font-size: 85%;
                        background-color: {p['kart2']}; border-radius: 999px;
                        padding: 2px 10px; }}

        .page-title {{ font-size: 182%; font-weight: 800; }}
        .title-rule {{ background-color: {p['vurgu']}; border-radius: 2px; }}
        .page-subtitle {{ color: {p['soluk']}; font-size: 106%; }}
        .body-text {{ font-size: 100%; }}

        .card {{ background-color: {p['kart']}; border: 1px solid {p['cizgi']};
                 border-radius: 12px; }}
        .row-sep {{ background-color: {tema.rgba_metni(p['cizgi'], 0.7)}; }}
        .pair-key {{ font-weight: bold; color: {p['vurgu_yazi']}; }}
        .link-key {{ font-weight: bold; }}
        .link-key a {{ color: {p['vurgu_yazi']}; text-decoration: none; }}
        .link-key a:hover {{ text-decoration: underline; }}
        .bullet-marker {{ color: {p['vurgu_yazi']}; font-size: 100%; }}

        .tile {{ background-color: {p['kart']}; border: 1px solid {p['cizgi']};
                 border-radius: 12px; }}
        .tile-title {{ font-weight: bold; color: {p['vurgu_yazi']}; font-size: 103%; }}
        .tile-text {{ color: {p['soluk']}; font-size: 92%; }}

        .note-box {{ background-color: {tema.rgba_metni(p['vurgu'], 0.10)};
                     border: 1px solid {tema.rgba_metni(p['vurgu'], 0.35)};
                     border-radius: 10px; }}
        .note-mark {{ color: {p['ana_yazi']}; background-color: {p['vurgu']};
                      font-weight: bold; font-size: 88%; border-radius: 999px;
                      min-width: 19px; min-height: 19px; }}
        .note-text {{ color: {p['yazi']}; font-size: 95%; }}

        .code-box {{ background-color: {p['kart2']}; border: 1px solid {p['cizgi']};
                     border-radius: 8px; }}
        .code-text {{ font-family: monospace; color: {p['vurgu_yazi']}; }}

        .shot-frame {{ border: 1px solid {p['cizgi']}; border-radius: 12px;
                       background-color: {p['kart']}; }}

        .scope-note {{ color: {p['soluk']}; font-size: 84%; }}
        .pick-card {{ background-color: {p['kart']};
                      border: 2px solid {p['cizgi']}; border-radius: 12px; }}
        .pick-card:hover {{ border-color: {p['silik']}; }}
        .konu-kart {{ background-color: {p['kart']}; border: 1px solid {p['cizgi']}; border-radius: 12px; }}
        .konu-kart:hover {{ border-color: {p['vurgu']}; }}
        .konu-bitti {{ color: {p['yesil']}; font-weight: 700; }}
        .pick-selected, .pick-selected:hover {{ border-color: {p['vurgu']};
                                                background-color: {vz}; }}
        .pick-title {{ font-size: 108%; font-weight: bold; }}
        .pick-sub {{ color: {p['soluk']}; font-size: 85%; }}
        .section-title {{ font-size: 106%; font-weight: bold; }}
        .wp-thumb {{ border-radius: 6px; }}

        .preview-light {{ background-color: #f4f5f6; border: 1px solid #d4d9db;
                          border-radius: 6px; }}
        .preview-dark {{ background-color: #23282a; border: 1px solid #3a4042;
                         border-radius: 6px; }}
        .preview-bar-light {{ background-color: #e2e6e8; }}
        .preview-bar-dark {{ background-color: #2e3436; }}
        .preview-dot {{ background-color: {p['vurgu']}; border-radius: 999px; }}
        .preview-line-light {{ background-color: #ccd2d4; border-radius: 3px; }}
        .preview-line-dark {{ background-color: #3d4446; border-radius: 3px; }}
        .preview-chip {{ background-color: {p['vurgu']}; border-radius: 4px; }}

        .dot {{ min-width: 8px; min-height: 8px; border-radius: 999px;
                background-color: {p['cizgi']}; }}
        .dot-active {{ background-color: {p['vurgu']}; min-width: 22px; }}

        .action-card {{ background-color: {vz}; border: 2px solid {p['vurgu']};
                        border-radius: 12px; padding: 16px 20px; }}
        .action-card:hover {{ background-color: {tema.rgba_metni(p['vurgu'], 0.22)}; }}
        .action-title {{ font-size: 110%; font-weight: 800; color: {p['vurgu_yazi']}; }}
        .action-sub {{ color: {p['yazi']}; font-size: 94%; }}

        button {{ padding: 6px 20px; }}
        checkbutton label {{ color: {p['soluk']}; font-size: 94%; }}
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
