# -*- coding: utf-8 -*-
from former_zaman import T, balon, git, yaz
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "nikto",
    "tagline": T("Web sunucu tarayıcı", "Web server scanner"),
    "ne": T("Bir web sunucusunu bilinen açıklar, eski yazılımlar ve riskli dosyalar için tarar.",
            "Scans a web server for known vulnerabilities, outdated software, and risky files."),
    "ne_zaman": T("Kendi web sunucunun bariz güvenlik açıkları taşıyıp taşımadığını görmek istediğinde.",
                  "When you want to see whether your own web server carries obvious security holes."),
    "ornek": T("Hedef = http://localhost", "Target = http://localhost"),
    "root": False,
    "alanlar": [
        {"id": "target", "ad": T("Hedef URL / IP", "Target URL / IP"), "tur": "alan",
         "yer": T("örn. http://localhost", "e.g. http://localhost")},
    ],
}

CIKTI = [
    "- Nikto v2.5.0",
    "+ Target IP:          127.0.0.1",
    "+ Target Hostname:    localhost",
    "+ Start Time:         2026-10-28 14:12:03",
    "+ Server: Apache/2.4.58 (Debian)",
    "+ The anti-clickjacking X-Frame-Options header is not present.",
    "+ /admin/: Directory indexing found.",
    "+ 7102 requests: 0 error(s) and 2 item(s) reported on remote host",
    "+ End Time: 2026-10-28 14:12:49 (46 seconds)",
]


def konu():
    adimlar = arac_sec("nikto") + [
        git("alan:target"),
        balon("alan:target", T("Hedef", "Target"),
              T("Tarayacağın web sunucusunun adresi. localhost, bu bilgisayarda çalışan bir sunucu demek; "
                "kendi makinende bir web sunucusu kurup denemek en güvenli başlangıçtır.",
                "The address of the web server to scan. localhost means a server running on this computer; "
                "setting up a web server on your own machine and testing it is the safest start.")),
        yaz("alan:target", "http://localhost"),
    ] + calistir("nikto -h http://localhost", CIKTI) + [
        balon("cikti", T("Bulguları oku", "Read the findings"),
              T("Her “+” satırı bir gözlem: eksik bir güvenlik başlığı, açık bir dizin listesi, eski bir sürüm "
                "gibi. Bunların çoğu “kesin açık” değil, “bakmaya değer” demektir.",
                "Each “+” line is an observation: a missing security header, an exposed directory listing, an "
                "old version. Most of these mean “worth a look”, not “definite hole”."), "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("nikto, bir web sitesine binlerce standart istek gönderip cevaplara bakar: eski bir "
                    "sunucu sürümü mü çalışıyor, yönetim paneli herkese açık mı, güvenlik başlıkları eksik "
                    "mi. Bir binanın dış kapılarını, pencerelerini, tabelalarını kontrol eden bir denetçi "
                    "gibi düşün; içeri girmez, sadece dışarıdan görüneni listeler.",
                    "nikto sends thousands of standard requests to a website and looks at the answers: is an "
                    "old server version running, is the admin panel open to everyone, are security headers "
                    "missing. Think of an inspector who checks a building's outer doors, windows and signs; "
                    "it does not go inside, it only lists what is visible from outside.")),
            ("p", T("Kendi web sitenin ya da uygulamanın yayına çıkmadan önce bariz hataları yakalamasında "
                    "işine yarar.",
                    "It is useful for catching obvious mistakes in your own website or app before it goes "
                    "live.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan nikto'yu seç.", "Pick nikto on the left."),
                T("Hedef alanına taranacak adresi yaz.", "Type the address to scan in the Target field."),
                T("Çalıştır'a bas. Tarama yavaştır; bitene kadar birkaç dakika sürebilir.",
                  "Press Run. The scan is slow; it can take a few minutes to finish."),
            ]),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[4:7])),
            ("p", T("Server satırı hangi web sunucusunun ve sürümünün çalıştığını söyler. Altındaki satırlar "
                    "bulunan noktalar: başlık eksikliği zararsız bir ipucu, dizin listesi ise dosyaların "
                    "doğrudan görünmesi anlamına gelir ve genelde kapatılmalıdır.",
                    "The Server line says which web server and version is running. The lines below are "
                    "findings: a missing header is a harmless hint, a directory listing means files are "
                    "directly visible and should usually be turned off.")),
            ("not", T("nikto “burada bir şey var” der ama kesin karar vermez; bazı bulgular yanlış alarm "
                      "(false positive) olabilir. " + T_DENEME_UYARISI["tr"],
                      "nikto says “there might be something here” but does not decide for certain; some "
                      "findings can be false positives. " + T_DENEME_UYARISI["en"])),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("Kendi makinende basit bir web sunucusu başlat (örn. python3 -m http.server) ve onu tara.",
                  "Start a simple web server on your own machine (e.g. python3 -m http.server) and scan it."),
                T("Çıktıdaki bir bulguyu seç, ne anlama geldiğini web'de ara.",
                  "Pick one finding from the output and search the web for what it means."),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Yalnızca kendi sunucularını ya da taramak için açıkça izin aldığın sunucuları tara. "
                        "Binlerce istek göndermek bir siteyi yavaşlatabilir; başkasının sitesinde izinsiz "
                        "çalıştırmak hem etik dışıdır hem de hukuki sorun doğurabilir.",
                        "Scan only your own servers or servers you have clear permission to scan. Sending "
                        "thousands of requests can slow a site down; running it on someone else's site "
                        "without permission is both unethical and can cause legal trouble.")),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "nikto -h http://localhost"),
            ("p", T("Sonucu dosyaya kaydetmek için -o rapor.html -Format htm ekleyebilirsin.",
                    "To save the result to a file you can add -o report.html -Format htm.")),
        ]),
    ]
    return _konu("nikto", ARAC, adimlar, bolumler, ikon="web")
