# -*- coding: utf-8 -*-
from former_zaman import T, balon, git, yaz
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "tcpdump",
    "tagline": T("Ağ paketi yakalama", "Network packet capture"),
    "ne": T("Ağ arayüzünden geçen ham paketleri yakalar ve ekrana döker.",
            "Captures raw packets passing through a network interface and prints them."),
    "ne_zaman": T("Bir bağlantının gerçekten ne trafiği ürettiğini kendi gözünle görmek istediğinde.",
                  "When you want to see with your own eyes what traffic a connection produces."),
    "ornek": T("eth0 üzerinde 50 paket yakala", "Capture 50 packets on eth0"),
    "root": True,
    "alanlar": [
        {"id": "iface", "ad": T("Arayüz", "Interface"), "tur": "alan", "varsayilan": "eth0",
         "yer": T("örn. eth0, wlan0", "e.g. eth0, wlan0")},
        {"id": "count", "ad": T("Paket sayısı", "Packet count"), "tur": "alan", "varsayilan": "50"},
        {"id": "filter", "ad": T("Filtre (opsiyonel)", "Filter (optional)"), "tur": "alan",
         "yer": T("örn. port 80", "e.g. port 80")},
    ],
}

CIKTI = [
    "listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes",
    "14:05:01.120 IP 10.0.2.15.51234 > 93.184.216.34.443: Flags [S], seq 1043, length 0",
    "14:05:01.142 IP 93.184.216.34.443 > 10.0.2.15.51234: Flags [S.], seq 77, ack 1044, length 0",
    "14:05:01.142 IP 10.0.2.15.51234 > 93.184.216.34.443: Flags [.], ack 1, length 0",
    "14:05:01.150 IP 10.0.2.15.51234 > 93.184.216.34.443: Flags [P.], length 517",
    "4 packets captured",
]


def konu():
    adimlar = arac_sec("tcpdump") + [
        balon("root_ipucu", T("Root gerekir", "Needs root"),
              T("Sarı not, bu aracın root ile çalışması gerektiğini söylüyor. Ağ kartını dinlemek ayrıcalıklı "
                "bir iştir; sıradan kullanıcı bunu yapamaz.",
                "The yellow note says this tool must run as root. Listening on a network card is a privileged "
                "job; a normal user cannot do it."), "alt"),
        git("alan:iface"),
        balon("alan:iface", T("Arayüz", "Interface"),
              T("Hangi ağ kartını dinleyeceğin. Kablolu bağlantı genelde eth0 ya da enp0s3, Wi-Fi wlan0 gibi "
                "görünür. Emin değilsen terminalde ip link yaz.",
                "Which network card to listen on. Wired is usually eth0 or enp0s3, Wi-Fi looks like wlan0. If "
                "you are not sure, type ip link in a terminal.")),
        git("alan:count"),
        balon("alan:count", T("Paket sayısı", "Packet count"),
              T("Bu kadar paket yakalayınca araç kendiliğinden durur. Küçük başla; 50 paket birkaç saniyede "
                "dolar ve ekran taşmaz.",
                "The tool stops by itself after this many packets. Start small; 50 packets fill up in seconds "
                "and the screen does not flood.")),
        git("alan:filter"),
        balon("alan:filter", T("Filtre", "Filter"),
              T("Boş bırakırsan her şeyi görürsün. “port 443” yazarsan yalnızca şifreli web trafiğini, “host "
                "10.0.2.2” yazarsan yalnızca o adresle olan konuşmayı görürsün.",
                "Leave it empty and you see everything. Type “port 443” to see only encrypted web traffic, or "
                "“host 10.0.2.2” to see only conversation with that address.")),
        yaz("alan:filter", "port 443"),
    ] + calistir("tcpdump -i eth0 -c 50 port 443", CIKTI, kok=True) + [
        balon("cikti", T("Paketleri oku", "Read the packets"),
              T("Her satır bir paket: saat, kimden kime, bayraklar. [S] bağlantı isteği, [S.] cevap, [.] onay, "
                "[P.] veri demek. İlk üç satır “üçlü el sıkışma”dır.",
                "Each line is a packet: time, from whom to whom, flags. [S] is a connection request, [S.] the "
                "reply, [.] an acknowledgement, [P.] data. The first three lines are the “three-way "
                "handshake”."), "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("Ağdaki her konuşma küçük paketlere bölünerek gider. tcpdump bu paketleri ağ kartından "
                    "geçerken yakalar ve her birini tek satıra yazar. Bir posta şubesinde zarfları sayıp "
                    "üzerindeki adreslere bakmak gibi düşün; içini açmazsın ama kimin kime yazdığını görürsün.",
                    "Every conversation on a network is split into small packets. tcpdump catches them as they "
                    "pass the network card and writes each on one line. Think of counting envelopes at a post "
                    "office and reading the addresses; you do not open them, but you see who writes to whom.")),
            ("p", T("Ne zaman işe yarar: bilgisayarın “internete bağlanıyor ama bilmediğim bir yere de "
                    "gidiyor” gibi bir şüphe uyandırdığında, ya da bir güvenlik aracı alarm verip nedenini "
                    "görmek istediğinde.",
                    "When it helps: when your computer makes you suspect it “talks to somewhere I do not "
                    "know”, or when a security tool raises an alarm and you want to see why.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan tcpdump'ı seç.", "Pick tcpdump on the left."),
                T("Arayüz alanına ağ kartının adını yaz (varsayılan eth0).",
                  "Type the network card name in the Interface field (default eth0)."),
                T("Paket sayısını küçük tut.", "Keep the packet count small."),
                T("İstersen filtre yaz, istemezsen boş bırak.", "Type a filter if you like, or leave it empty."),
                T("“Root ile çalıştır”a bas, parolanı gir. Normal Çalıştır root olmadığı için izin hatası verir.",
                  "Press “Run as root” and enter your password. Plain Run fails with a permission error because "
                  "it is not root."),
            ]),
            ("tablo", [
                (T("-i arayüz", "-i interface"), T("Hangi ağ kartı dinlenecek.", "Which network card to listen on.")),
                (T("-c sayı", "-c count"), T("Bu kadar paketten sonra dur.", "Stop after this many packets.")),
                (T("filtre", "filter"), T("port 80, host 1.2.3.4, tcp, udp gibi; boşsa hepsi.",
                                          "port 80, host 1.2.3.4, tcp, udp and so on; all traffic if empty.")),
            ]),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[1:5])),
            ("p", T("Satırı soldan sağa oku: saat, IP, kaynak adres ve port, “>” işareti, hedef adres ve port, "
                    "bayraklar. Burada 10.0.2.15 senin bilgisayarın, 93.184.216.34 uzaktaki bir web sunucusu, "
                    "443 şifreli web portu.",
                    "Read a line left to right: time, IP, source address and port, the “>” sign, destination "
                    "address and port, flags. Here 10.0.2.15 is your computer, 93.184.216.34 a remote web "
                    "server, 443 the encrypted web port.")),
            ("tablo", [
                (T("[S]", "[S]"), T("SYN: “bağlanmak istiyorum.”", "SYN: “I want to connect.”")),
                (T("[S.]", "[S.]"), T("SYN-ACK: “tamam, ben de hazırım.”", "SYN-ACK: “OK, I am ready too.”")),
                (T("[.]", "[.]"), T("ACK: “aldım.” Üçüncü adımla el sıkışma biter.",
                                    "ACK: “received.” The third step ends the handshake.")),
                (T("[P.]", "[P.]"), T("PSH-ACK: veri taşıyan paket.", "PSH-ACK: a packet carrying data.")),
                (T("[F.] / [R.]", "[F.] / [R.]"), T("Bağlantıyı kapatma / zorla koparma.",
                                                    "Closing / forcibly resetting the connection.")),
            ]),
            ("not", T("Port 443 trafiği şifrelidir; tcpdump içeriği değil, yalnızca kimin kiminle konuştuğunu "
                      "gösterir. " + T_DENEME_UYARISI["tr"],
                      "Port 443 traffic is encrypted; tcpdump shows only who talks to whom, not the content. "
                      + T_DENEME_UYARISI["en"])),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("Filtre boşken 20 paket yakala, hangi adreslerin göründüğüne bak.",
                  "Capture 20 packets with an empty filter and look at which addresses appear."),
                T("Bir tarayıcıda bir site aç, aynı anda “port 443” filtresiyle yakala; kendi trafiğini tanı.",
                  "Open a website in a browser and capture with “port 443” at the same time; recognise your "
                  "own traffic."),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Yalnızca kendi ağında ve kendi trafiğinde kullan. Başkalarının trafiğini izinsiz "
                        "dinlemek birçok ülkede suçtur. Okul ya da iş ağında bu aracı çalıştırmadan önce "
                        "izin al.",
                        "Use it only on your own network and your own traffic. Listening to other people's "
                        "traffic without permission is a crime in many countries. On a school or work network, "
                        "get permission first.")),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "sudo tcpdump -i eth0 -c 50 port 443"),
            ("p", T("Dosyaya kaydetmek istersen -w yakalama.pcap ekle; sonra Wireshark ya da tshark ile "
                    "açabilirsin.",
                    "To save to a file add -w capture.pcap; you can open it later with Wireshark or tshark.")),
        ]),
    ]
    return _konu("tcpdump", ARAC, adimlar, bolumler, ikon="paket")
