# -*- coding: utf-8 -*-
from former_zaman import T, balon, git, sec, yaz
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "ufw",
    "tagline": T("Güvenlik duvarı", "Firewall"),
    "ne": T("Sisteme gelen ve giden bağlantıları basit kurallarla yönetir.",
            "Manages incoming and outgoing connections with simple rules."),
    "ne_zaman": T("Hangi portların açık olduğunu görmek ya da bir portu açıp kapatmak istediğinde.",
                  "When you want to see which ports are open, or open and close one."),
    "ornek": T("\"Durum\" ile mevcut kuralları listele", "List current rules with \"Status\""),
    "root": True,
    "alanlar": [
        {"id": "action", "ad": T("İşlem", "Action"), "tur": "secim",
         "secenekler": [T("Durum", "Status"), T("Etkinleştir", "Enable"),
                        T("Devre dışı bırak", "Disable"), T("Port izni ver", "Allow port")]},
        {"id": "port", "ad": T("Port (izin için)", "Port (for allow)"), "tur": "alan",
         "yer": T("örn. 22", "e.g. 22")},
    ],
}

CIKTI = [
    "Status: active",
    "Logging: on (low)",
    "Default: deny (incoming), allow (outgoing), disabled (routed)",
    "",
    "To                         Action      From",
    "--                         ------      ----",
    "22/tcp                     ALLOW       Anywhere",
]


def konu():
    adimlar = arac_sec("ufw") + [
        balon("root_ipucu", T("Root gerekir", "Needs root"),
              T("Güvenlik duvarı kurallarını değiştirmek sistem genelini etkiler; bu yüzden root ister.",
                "Changing firewall rules affects the whole system; that is why it needs root."), "alt"),
        git("alan:action"),
        balon("alan:action", T("İşlem", "Action"),
              T("Durum mevcut kuralları gösterir, hiçbir şeyi değiştirmez — ilk kez kullanıyorsan buradan "
                "başla. Etkinleştir/Devre dışı bırak güvenlik duvarını açıp kapatır. Port izni ver, "
                "belirttiğin porta gelen bağlantılara izin verir.",
                "Status shows the current rules without changing anything — start here if this is your first "
                "time. Enable/Disable turns the firewall on or off. Allow port lets connections through to "
                "the port you name.")),
        sec("alan:action", 0),
    ] + calistir("ufw status verbose", CIKTI, kok=True) + [
        balon("cikti", T("Durumu oku", "Read the status"),
              T("Status: active, güvenlik duvarının çalıştığını gösterir. Default satırı kuralı özetler: "
                "gelen bağlantılar varsayılan olarak reddedilir (deny), giden bağlantılara izin verilir. "
                "Alttaki tablo hangi portlara özel izin verildiğini listeler.",
                "Status: active means the firewall is running. The Default line summarises the policy: "
                "incoming connections are denied by default, outgoing ones are allowed. The table below lists "
                "which ports have a specific allow rule."), "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("ufw (Uncomplicated Firewall), bilgisayarına hangi bağlantıların girebileceğini "
                    "belirleyen basit bir güvenlik duvarı arayüzüdür. Varsayılan kural “gelen her şeyi "
                    "reddet” olduğu için, sen açıkça izin vermediğin sürece dışarıdan kimse bir porta "
                    "bağlanamaz.",
                    "ufw (Uncomplicated Firewall) is a simple firewall interface that decides which "
                    "connections can reach your computer. Because the default rule is “deny everything "
                    "incoming”, nobody from outside can connect to a port unless you explicitly allow it.")),
            ("p", T("Bir binanın kapıcısı gibi düşün: sen listeye yazmadığın hiç kimseyi içeri almaz.",
                    "Think of it like a building's doorkeeper: it lets in nobody you have not written on the "
                    "list.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan ufw'yi seç.", "Pick ufw on the left."),
                T("Önce “Durum” ile mevcut kuralları gör.", "First see the current rules with “Status”."),
                T("Bir port açmak istiyorsan “Port izni ver”i seç ve port numarasını yaz.",
                  "To open a port, pick “Allow port” and type the port number."),
                T("“Root ile çalıştır”a bas ve parolanı gir.", "Press “Run as root” and enter your password."),
            ]),
            ("uyari", T("SSH ile uzaktan bağlandığın bir makinede güvenlik duvarını etkinleştirmeden önce "
                        "22 (ssh) portuna izin verdiğinden emin ol; aksi hâlde kendi bağlantını keser, "
                        "makineye bir daha uzaktan giremezsin.",
                        "Before enabling the firewall on a machine you are connected to remotely over SSH, "
                        "make sure port 22 (ssh) is allowed; otherwise you cut off your own connection and "
                        "cannot get back in remotely.")),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[:3])),
            ("tablo", [
                (T("Status: active", "Status: active"), T("Güvenlik duvarı çalışıyor.", "The firewall is running.")),
                (T("Status: inactive", "Status: inactive"), T("Güvenlik duvarı kapalı; hiçbir şey "
                                                              "engellenmiyor.",
                                                              "The firewall is off; nothing is being "
                                                              "blocked.")),
                (T("ALLOW", "ALLOW"), T("O porta/kurala gelen bağlantılara izin var.",
                                        "Connections to that port/rule are allowed.")),
                (T("DENY", "DENY"), T("O porta/kurala gelen bağlantılar reddediliyor.",
                                      "Connections to that port/rule are rejected.")),
            ]),
            ("not", T_DENEME_UYARISI),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("Önce “Durum” ile hangi portların açık olduğuna bak.",
                  "First check which ports are open with “Status”."),
                T("İhtiyacın olmayan bir servisin portunu kapat (önce o servisi durdurarak ya da kuralı "
                  "kaldırarak).",
                  "Close the port of a service you do not need (by stopping that service or removing the "
                  "rule)."),
                T("nmap konusuna dön ve aynı makineyi tekrar tara; kapattığın portun artık görünmediğini "
                  "doğrula.",
                  "Go back to the nmap topic and scan the same machine again; confirm the port you closed no "
                  "longer appears."),
            ]),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "sudo ufw status verbose\nsudo ufw allow 22\nsudo ufw enable"),
            ("p", T("Bir kuralı kaldırmak için: sudo ufw delete allow 22",
                    "To remove a rule: sudo ufw delete allow 22")),
        ]),
    ]
    return _konu("ufw", ARAC, adimlar, bolumler, ikon="kalkan")
