# -*- coding: utf-8 -*-
from former_zaman import T, balon, git, yaz
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "aircrack-ng",
    "tagline": T("Kablosuz ağ güvenlik testi", "Wireless security testing"),
    "ne": T("Yakalanmış bir Wi-Fi kayıt dosyasını inceler; ağın adını, şifreleme türünü ve "
            "dosyada kullanılabilir bir kayıt olup olmadığını gösterir.",
            "Inspects a captured Wi-Fi recording file; shows the network's name, its "
            "encryption type, and whether the file contains a usable record."),
    "ne_zaman": T("Kendi Wi-Fi ağının ayarlarını ve genel güvenlik seviyesini kontrol etmek istediğinde.",
                  "When you want to check your own Wi-Fi network's settings and overall security level."),
    "ornek": T("Bir .cap dosyası seç ve incele", "Pick a .cap file and inspect it"),
    "root": False,
    "alanlar": [
        {"id": "capfile", "ad": T("Yakalama dosyası (.cap)", "Capture file (.cap)"), "tur": "dosya"},
    ],
}

CIKTI = [
    "Opening /home/kullanici/ev-agi.cap",
    "Read 4210 packets.",
    "",
    "   #  BSSID              ESSID      Encryption",
    "   1  AA:BB:CC:11:22:33  EvAgi      WPA",
    "",
    "[Bitti — çıkış kodu 0]",
]


def konu():
    adimlar = arac_sec("aircrack-ng") + [
        git("alan:capfile"),
        balon("alan:capfile", T("Yakalama dosyası", "Capture file"),
              T("Burada bir .cap dosyası seçersin. Bu dosya, havadan kaydedilmiş Wi-Fi "
                "trafiğini içerir; başka bir araçla önceden kaydedilmiş olur, panel "
                "kendisi kayıt yapmaz.",
                "Here you pick a .cap file. It holds Wi-Fi traffic recorded from the air; "
                "it is recorded beforehand with another tool, the panel does not record "
                "itself.")),
        yaz("alan:capfile", "~/ev-agi.cap"),
    ] + calistir("aircrack-ng /home/kullanici/ev-agi.cap", CIKTI) + [
        balon("cikti", T("Çıktıyı oku", "Read the output"),
              T("Araç dosyadaki ağları listeler: adı (ESSID) ve şifreleme türü (WPA/WPA2/"
                "açık). Bu, kendi yönlendiricinin ayarlarını terminalden teyit etmenin bir "
                "yoludur.",
                "The tool lists the networks in the file: name (ESSID) and encryption type "
                "(WPA/WPA2/open). This is one way to confirm your own router's settings "
                "from a terminal."), "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("aircrack-ng ailesi, kablosuz ağ güvenliğini incelemek için kullanılan "
                    "araçlardan biridir. Panelde sadece bir .cap dosyasını açıp içindeki "
                    "ağların adını ve şifreleme türünü gösteren basit kısmı sunulur.",
                    "The aircrack-ng family is one of the tools used to examine wireless "
                    "network security. The panel offers only the simple part: opening a "
                    ".cap file and showing the networks' name and encryption type inside it.")),
            ("p", T("Neden önemli: hâlâ WEP ya da şifresiz (açık) bir ağ çalıştırıyorsan bunu "
                    "fark etmenin en kolay yolu budur; WEP yıllardır güvensiz kabul edilir, "
                    "modern yönlendiriciler WPA2 veya WPA3 kullanmalı.",
                    "Why it matters: this is the easiest way to notice if you still run a WEP "
                    "or unencrypted (open) network; WEP has been considered insecure for "
                    "years, modern routers should use WPA2 or WPA3.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan aircrack-ng'yi seç.", "Pick aircrack-ng on the left."),
                T("Yakalama dosyası alanından bir .cap dosyası seç.",
                  "Pick a .cap file in the Capture file field."),
                T("Çalıştır'a bas; araç dosyadaki ağları listeler.",
                  "Press Run; the tool lists the networks in the file."),
            ]),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[3:5])),
            ("tablo", [
                (T("BSSID", "BSSID"), T("Yönlendiricinin donanım adresi (MAC).",
                                        "The router's hardware address (MAC).")),
                (T("ESSID", "ESSID"), T("Ağın adı; telefonunda Wi-Fi listesinde gördüğün isim.",
                                        "The network's name; what you see in your phone's "
                                        "Wi-Fi list.")),
                (T("Encryption", "Encryption"), T("Açık, WEP, WPA ya da WPA2/3. Açık ve WEP "
                                                  "zayıf kabul edilir.",
                                                  "Open, WEP, WPA, or WPA2/3. Open and WEP are "
                                                  "considered weak.")),
            ]),
            ("not", T_DENEME_UYARISI),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("Yönlendiricinin yönetim sayfasından hangi şifreleme türünü kullandığına "
                  "bak; WPA2 ya da WPA3 olmalı.",
                  "Check your router's admin page for which encryption type it uses; it "
                  "should be WPA2 or WPA3."),
                T("Açık ya da WEP bir ağ görürsen, o senin ağınsa yönlendirici ayarlarından "
                  "WPA2/WPA3'e geçir.",
                  "If you see an open or WEP network and it is yours, switch it to WPA2/WPA3 "
                  "from the router settings."),
                T("Wi-Fi parolanı uzun ve rastgele tut; bu, bu tür araçların işini en çok "
                  "zorlaştıran tek şeydir.",
                  "Keep your Wi-Fi password long and random; that is the single thing that "
                  "makes this kind of tool's job hardest."),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Kablosuz ağ araçlarını yalnızca kendi ağın ve kendi cihazların "
                        "üzerinde kullan. Başkasının Wi-Fi'ına izinsiz müdahale etmek, "
                        "trafiğini kaydetmek ya da parolasını denemek birçok ülkede suçtur ve "
                        "bu uygulamanın kapsamı dışındadır.",
                        "Use wireless tools only on your own network and your own devices. "
                        "Interfering with someone else's Wi-Fi without permission, recording "
                        "its traffic, or trying its password is a crime in many countries and "
                        "is outside the scope of this app.")),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "aircrack-ng ev-agi.cap"),
            ("p", T("aircrack-ng paketinde ayrıca airodump-ng (dinleme) ve aireplay-ng (test "
                    "paketleri) gibi başka araçlar da vardır; bunlar sadece kendi ağında, "
                    "bilerek ve izinli kullanılmalıdır.",
                    "The aircrack-ng suite also has other tools such as airodump-ng "
                    "(listening) and aireplay-ng (test packets); these must be used only on "
                    "your own network, knowingly and with permission.")),
        ]),
    ]
    return _konu("aircrack_ng", ARAC, adimlar, bolumler, ikon="wifi")
