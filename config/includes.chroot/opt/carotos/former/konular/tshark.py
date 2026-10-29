# -*- coding: utf-8 -*-
from former_zaman import T, balon, git, yaz
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "tshark",
    "tagline": T("Wireshark — terminal sürümü", "Wireshark — terminal edition"),
    "ne": T("Wireshark'ın komut satırı hâli; paketleri yakalar ve protokol ayrıntısıyla çözümler.",
            "The command-line side of Wireshark; captures packets and dissects them with protocol detail."),
    "ne_zaman": T("tcpdump'tan daha okunur, protokol bazında ayrıştırılmış çıktı istediğinde.",
                  "When you want output that's more readable and dissected per protocol than tcpdump."),
    "ornek": T("eth0 üzerinde 5 paket çözümle", "Dissect 5 packets on eth0"),
    "root": True,
    "alanlar": [
        {"id": "iface", "ad": T("Arayüz", "Interface"), "tur": "alan", "varsayilan": "eth0",
         "yer": T("örn. eth0, wlan0", "e.g. eth0, wlan0")},
        {"id": "count", "ad": T("Paket sayısı", "Packet count"), "tur": "alan", "varsayilan": "50"},
    ],
}

CIKTI = [
    "Capturing on 'eth0'",
    "    1 0.000000 10.0.2.15 → 10.0.2.3 DNS 74 Standard query A example.com",
    "    2 0.011200 10.0.2.3 → 10.0.2.15 DNS 90 Standard query response A 93.184.216.34",
    "    3 0.012000 10.0.2.15 → 93.184.216.34 TCP 74 51234 → 443 [SYN]",
    "    4 0.034100 93.184.216.34 → 10.0.2.15 TCP 74 443 → 51234 [SYN, ACK]",
    "    5 0.034300 10.0.2.15 → 93.184.216.34 TLSv1.3 571 Client Hello",
    "5 packets captured",
]


def konu():
    adimlar = arac_sec("tshark") + [
        git("alan:iface"),
        balon("alan:iface", T("Arayüz", "Interface"),
              T("Dinlenecek ağ kartı; tcpdump ile aynı mantık. Kablolu için eth0 ya da enp0s3, kablosuz için "
                "wlan0.",
                "The network card to listen on, same idea as tcpdump. eth0 or enp0s3 for wired, wlan0 for "
                "wireless.")),
        git("alan:count"),
        balon("alan:count", T("Paket sayısı", "Packet count"),
              T("Yakalanacak paket sayısı. tshark her paketi ayrıştırdığı için çıktı uzundur; küçük sayıyla "
                "başla.",
                "How many packets to capture. tshark dissects every packet so output is long; start small.")),
        yaz("alan:count", "5"),
    ] + calistir("tshark -i eth0 -c 5", CIKTI, kok=True) + [
        balon("cikti", T("Protokolleri oku", "Read the protocols"),
              T("tcpdump'ta “IP … Flags” gördüğün yerde burada protokol adı yazıyor: DNS, TCP, TLSv1.3. "
                "Önce DNS ile “example.com kim?” diye sorulmuş, sonra bağlantı kurulmuş.",
                "Where tcpdump shows “IP … Flags”, here the protocol name is written: DNS, TCP, TLSv1.3. First "
                "DNS asks “who is example.com?”, then a connection is made."), "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("tshark, Wireshark programının terminalde çalışan hâlidir. tcpdump paketi “ham” gösterir; "
                    "tshark ise her paketin hangi protokole ait olduğunu bilir ve çıktıya yazar. İsim "
                    "çözümlemesi (DNS), web (HTTP), şifreli web (TLS) gibi katmanları ayrı ayrı tanır.",
                    "tshark is the terminal version of the Wireshark program. tcpdump shows packets “raw”; "
                    "tshark knows which protocol each packet belongs to and prints it. It recognises layers "
                    "such as name lookup (DNS), web (HTTP) and encrypted web (TLS) separately.")),
            ("p", T("Öğrenmek için güzel bir araçtır: bir siteyi açtığında arkada önce DNS sorgusu, sonra TCP "
                    "el sıkışması, sonra TLS başlangıcı olduğunu kendi gözünle görürsün.",
                    "It is a good tool for learning: you see with your own eyes that opening a site starts "
                    "with a DNS query, then a TCP handshake, then the TLS start.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan tshark'ı seç.", "Pick tshark on the left."),
                T("Arayüz adını kontrol et.", "Check the interface name."),
                T("Paket sayısını küçük tut (5–20).", "Keep the packet count small (5–20)."),
                T("“Root ile çalıştır”a bas ve parolanı gir. tshark da ağ kartını dinlediği için root ister.",
                  "Press “Run as root” and enter your password. tshark also listens on the network card so it "
                  "needs root."),
            ]),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[1:6])),
            ("tablo", [
                (T("Birinci sütun", "First column"), T("Paket numarası.", "Packet number.")),
                (T("İkinci sütun", "Second column"), T("Yakalamanın başından beri geçen saniye.",
                                                       "Seconds since the capture started.")),
                (T("Kaynak → Hedef", "Source → Destination"), T("Paketi kim kime yolladı.",
                                                                  "Who sent the packet to whom.")),
                (T("Protokol", "Protocol"), T("DNS, TCP, TLSv1.3, HTTP gibi; paketin hangi dili konuştuğu.",
                                              "DNS, TCP, TLSv1.3, HTTP and so on; which language the packet "
                                              "speaks.")),
                (T("Son sütun", "Last column"), T("Paketin kısa özeti: ne sorulmuş, ne cevaplanmış.",
                                                  "A short summary: what was asked, what was answered.")),
            ]),
            ("not", T_DENEME_UYARISI),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("5 paket yakala ve aynı anda tarayıcıda bir site aç. DNS satırını bul.",
                  "Capture 5 packets and open a website at the same time. Find the DNS line."),
                T("Aynı yakalamayı tcpdump ile yap ve ikisini karşılaştır; hangisi daha okunaklı?",
                  "Do the same capture with tcpdump and compare the two; which is easier to read?"),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Sadece kendi trafiğini ve kendi ağını yakala. Paket dosyalarında parola ya da kişisel "
                        "bilgi olabilir; kaydettiysen kimseyle paylaşma.",
                        "Capture only your own traffic and network. Packet files can contain passwords or "
                        "personal data; if you saved one, do not share it.")),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "sudo tshark -i eth0 -c 5"),
            ("p", T("Belirli bir protokole bakmak için -Y ekle: sudo tshark -i eth0 -Y dns.",
                    "To look at one protocol add -Y: sudo tshark -i eth0 -Y dns.")),
        ]),
    ]
    return _konu("tshark", ARAC, adimlar, bolumler, ikon="paket")
