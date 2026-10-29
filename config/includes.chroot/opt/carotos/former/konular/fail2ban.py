# -*- coding: utf-8 -*-
from former_zaman import T, balon, git
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "fail2ban",
    "tagline": T("Kaba kuvvet koruması", "Brute-force protection"),
    "ne": T("Tekrarlayan başarısız giriş denemelerini tespit edip saldıran adresleri engeller.",
            "Detects repeated failed login attempts and blocks the attacking addresses."),
    "ne_zaman": T("Koruma servisinin çalışıp çalışmadığını ve hangi kuralların aktif olduğunu görmek için.",
                  "To see whether the protection service is running and which rules are active."),
    "ornek": T("\"Genel durum\" ile özeti gör", "See the overview with \"Overall status\""),
    "root": True,
    "alanlar": [
        {"id": "action", "ad": T("İşlem", "Action"), "tur": "secim",
         "secenekler": [T("Genel durum", "Overall status")]},
    ],
}

CIKTI = [
    "Status",
    "|- Number of jail:      2",
    "`- Jail list:   sshd, recidive",
    "",
    "Status for the jail: sshd",
    "|- Currently failed:   1",
    "|- Total failed:       9",
    "`- Currently banned:   1",
    "   `- Banned IP list:  192.168.1.23",
]


def konu():
    adimlar = arac_sec("fail2ban") + [
        balon("root_ipucu", T("Root gerekir", "Needs root"),
              T("fail2ban'ın durumunu sorgulamak ve kurallarını görmek sistem servisine erişim ister.",
                "Querying fail2ban's status and seeing its rules needs access to a system service."), "alt"),
        git("alan:action"),
        balon("alan:action", T("İşlem", "Action"),
              T("Şimdilik panelde tek seçenek var: genel durumu görmek. Bu, fail2ban'ın hangi servisleri "
                "koruduğunu (“jail” denir) ve şu an kaç adresin engellendiğini gösterir.",
                "The panel currently has one option: see the overall status. This shows which services "
                "fail2ban protects (called a “jail”) and how many addresses are blocked right now.")),
    ] + calistir("fail2ban-client status", CIKTI, kok=True) + [
        balon("cikti", T("Durumu oku", "Read the status"),
              T("Jail list, hangi servislerin korunduğunu sayar — sshd, SSH girişini korur. Altındaki "
                "bölüm o servise özeldir: kaç başarısız deneme oldu, şu an kaç adres engelli.",
                "Jail list counts which services are protected — sshd protects SSH login. The section below "
                "is specific to that service: how many failed attempts there were, how many addresses are "
                "banned right now."), "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("fail2ban, sistem kayıtlarını (log) sürekli izler. Bir adresten kısa sürede çok fazla "
                    "başarısız giriş denemesi gelirse, o adresi bir süreliğine güvenlik duvarından otomatik "
                    "olarak engeller. Bunu bir kapıdaki güvenlik görevlisine benzetebilirsin: birisi şifreyi "
                    "üst üste yanlış denerse, o kişiyi bir süre kapıdan uzaklaştırır.",
                    "fail2ban continuously watches the system logs. If too many failed login attempts come "
                    "from one address in a short time, it automatically blocks that address at the firewall "
                    "for a while. You can compare it to a security guard at a door: if someone keeps getting "
                    "the code wrong, the guard turns that person away for a while.")),
            ("p", T("hydra konusundaki gibi bir kaba kuvvet denemesi, fail2ban çalışan bir makinede birkaç "
                    "yanlış denemeden sonra otomatik olarak durdurulur.",
                    "A brute-force attempt like the one in the hydra topic is automatically stopped after a "
                    "few wrong tries on a machine where fail2ban is running.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan fail2ban'ı seç.", "Pick fail2ban on the left."),
                T("İşlem “Genel durum” olarak kalsın.", "Leave Action as “Overall status”."),
                T("“Root ile çalıştır”a bas ve parolanı gir.", "Press “Run as root” and enter your password."),
            ]),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[4:9])),
            ("tablo", [
                (T("Currently failed", "Currently failed"), T("Son pencerede sayılan başarısız deneme sayısı.",
                                                              "Failed attempts counted in the recent window.")),
                (T("Total failed", "Total failed"), T("Servis başladığından beri toplam başarısız deneme.",
                                                       "Total failed attempts since the service started.")),
                (T("Currently banned", "Currently banned"), T("Şu an engelli olan adres sayısı.",
                                                              "How many addresses are banned right now.")),
                (T("Banned IP list", "Banned IP list"), T("Engelli adreslerin kendisi.",
                                                          "The banned addresses themselves.")),
            ]),
            ("not", T_DENEME_UYARISI),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("fail2ban'ı kur ve çalıştır, sonra genel durumu panelden kontrol et.",
                  "Install and run fail2ban, then check the overall status from the panel."),
                T("CarotPot konusunu da oku; CarotPot de benzer şekilde şüpheli davranışı fark eder, ama "
                  "gerçek servisleri değil sahte tuzakları korur.",
                  "Also read the CarotPot topic; CarotPot notices suspicious behaviour similarly, but it "
                  "protects fake traps rather than real services."),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("p", T("fail2ban varsayılan ayarlarla genelde 10 dakika içinde 5 başarısız denemeden sonra bir "
                    "adresi 10 dakikalığına engeller. Kendi IP'ni yanlışlıkla kilitlemene karşı, test "
                    "yaparken bunu aklında tut.",
                    "With default settings fail2ban typically bans an address for 10 minutes after 5 failed "
                    "attempts within 10 minutes. Keep this in mind while testing, so you do not accidentally "
                    "lock out your own IP.")),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "sudo fail2ban-client status\nsudo fail2ban-client status sshd"),
            ("p", T("Bir adresi elle engellemek için: sudo fail2ban-client set sshd banip 192.168.1.23",
                    "To ban an address manually: sudo fail2ban-client set sshd banip 192.168.1.23")),
        ]),
    ]
    return _konu("fail2ban", ARAC, adimlar, bolumler, ikon="kalkan")
