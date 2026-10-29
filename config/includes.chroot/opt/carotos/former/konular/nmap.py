# -*- coding: utf-8 -*-
from former_zaman import T, balon, git, sec, yaz
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "nmap",
    "tagline": T("Ağ ve port keşfi", "Network & port discovery"),
    "ne": T("Bir ağdaki cihazları, açık portları ve çalışan servisleri haritalar.",
            "Maps devices on a network, their open ports, and running services."),
    "ne_zaman": T("Bir sunucunun hangi kapıları açık, arkasında ne çalışıyor bilmek istediğinde.",
                  "When you want to know which doors a host has open and what runs behind them."),
    "ornek": T("Kendi makineni tara: hedef = 127.0.0.1", "Scan your own machine: target = 127.0.0.1"),
    "root": False,
    "alanlar": [
        {"id": "target", "ad": T("Hedef (IP veya alan adı)", "Target (IP or hostname)"), "tur": "alan",
         "yer": T("örn. 192.168.1.1", "e.g. 192.168.1.1")},
        {"id": "scan", "ad": T("Tarama türü", "Scan type"), "tur": "secim",
         "secenekler": [T("Hızlı", "Quick"), T("Tüm portlar", "All ports"), T("Servis / sürüm", "Service / version"),
                        T("Gizli SYN (root)", "Stealth SYN (root)")]},
    ],
}

CIKTI = [
    "Starting Nmap 7.93 ( https://nmap.org ) at 2026-10-28 14:02 +03",
    "Nmap scan report for localhost (127.0.0.1)",
    "Host is up (0.00011s latency).",
    "Not shown: 98 closed tcp ports (conn-refused)",
    "PORT    STATE SERVICE",
    "22/tcp  open  ssh",
    "631/tcp open  ipp",
    "",
    "Nmap done: 1 IP address (1 host up) scanned in 0.09 seconds",
]


def konu():
    adimlar = arac_sec("nmap") + [
        balon("a_bilgi", T("Önce şunu oku", "Read this first"),
              T("Her araçta bu üç satır var: ne yaptığı, ne zaman kullanılacağı, bir örnek. Aracı ilk kez "
                "kullanıyorsan örneği aynen dene.",
                "Every tool has these three lines: what it does, when to use it, an example. If you are new to "
                "the tool, try the example exactly as written."), "alt"),
        git("alan:target"),
        balon("alan:target", T("Hedef", "Target"),
              T("Taramak istediğin bilgisayarın adresi. 127.0.0.1 senin kendi bilgisayarın demektir; ilk "
                "denemeni oradan yap, kimseden izin gerekmez.",
                "The address of the computer you want to scan. 127.0.0.1 means your own computer; make your "
                "first try there, no one's permission is needed.")),
        yaz("alan:target", "127.0.0.1"),
        git("alan:scan"),
        balon("alan:scan", T("Tarama türü", "Scan type"),
              T("Hızlı en sık kullanılan 100 porta bakar ve birkaç saniye sürer. Tüm portlar 65535 kapının "
                "hepsini dener, uzun sürer. Servis/sürüm, açık kapının arkasında hangi program olduğunu sorar. "
                "Gizli SYN root ister.",
                "Quick checks the 100 most common ports and takes seconds. All ports tries all 65535 doors and "
                "takes long. Service/version asks which program is behind an open door. Stealth SYN needs root.")),
        sec("alan:scan", 0),
        balon("btn:calistir", T("Çalıştır", "Run"),
              T("Çalıştır'a basınca panel komutu kurar ve üstte gösterir. Böylece arkada ne çalıştığını hep "
                "görürsün ve terminalde kendin de yazabilirsin.",
                "When you press Run the panel builds the command and shows it on top. That way you always see "
                "what runs behind the scenes, and you can type it yourself in a terminal.")),
    ] + calistir("/usr/bin/nmap -T4 -F 127.0.0.1", CIKTI) + [
        balon("cikti", T("Çıktıyı oku", "Read the output"),
              T("PORT, STATE, SERVICE sütunlarına bak. “open” o kapıda bir programın dinlediği demek. Burada SSH "
                "ve yazıcı servisi açık; ihtiyacın yoksa kapatmak iyi bir fikir.",
                "Look at the PORT, STATE, SERVICE columns. “open” means a program is listening at that door. "
                "SSH and the print service are open here; if you do not need them, closing them is a good idea."),
              "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("Nmap, bir bilgisayarın ağ üzerinde hangi kapılarını açık tuttuğunu gösterir. Bilgisayarı bir "
                    "apartman gibi düşün: her port bir kapı numarasıdır. 22 numaralı kapıda uzaktan bağlantı "
                    "(SSH), 80'de web sitesi, 631'de yazıcı servisi oturur. Nmap bu kapıları tek tek çalar ve "
                    "birinin cevap verip vermediğine bakar.",
                    "Nmap shows which doors a computer keeps open on the network. Think of the computer as an "
                    "apartment block: every port is a door number. Door 22 hosts remote login (SSH), 80 hosts a "
                    "website, 631 hosts the print service. Nmap knocks on the doors one by one and sees whether "
                    "anyone answers.")),
            ("p", T("Neden önemli: açık her kapı, birinin içeri girmeyi deneyebileceği bir yerdir. Kendi "
                    "makinende hiç ihtiyacın olmayan bir servis açıksa, onu kapatmak en ucuz güvenlik "
                    "önlemidir.",
                    "Why it matters: every open door is a place someone can try to get in. If a service you never "
                    "need is open on your own machine, switching it off is the cheapest security measure there is.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan nmap'i seç.", "Pick nmap on the left."),
                T("Hedef alanına bir adres yaz. İlk deneme için 127.0.0.1.",
                  "Type an address in the Target field. For a first try: 127.0.0.1."),
                T("Tarama türünü seç (aşağıdaki tabloya bak).", "Choose a scan type (see the table below)."),
                T("Çalıştır'a bas. Çıktı canlı akar; uzun sürerse Durdur'a basabilirsin.",
                  "Press Run. Output streams live; press Stop if it takes too long."),
            ]),
            ("tablo", [
                (T("Hızlı", "Quick"), T("Panelin çalıştırdığı komut: nmap -T4 -F HEDEF. En sık kullanılan 100 port; "
                                        "saniyeler sürer.",
                                        "Runs: nmap -T4 -F TARGET. The 100 most common ports; takes seconds.")),
                (T("Tüm portlar", "All ports"), T("nmap -p- HEDEF. 65535 portun hepsi; dakikalar sürebilir. Hızlı'nın "
                                                  "görmediği, yüksek numaralı sakin kapıları bulur.",
                                                  "nmap -p- TARGET. All 65535 ports; can take minutes. Finds quiet, "
                                                  "high-numbered doors that Quick misses.")),
                (T("Servis / sürüm", "Service / version"), T("nmap -sV HEDEF. Açık kapının arkasındaki programı ve "
                                                             "sürümünü sorar. Eski sürüm, bilinen bir açığa işaret "
                                                             "edebilir.",
                                                             "nmap -sV TARGET. Asks which program and version is behind "
                                                             "an open door. An old version can point to a known flaw.")),
                (T("Gizli SYN (root)", "Stealth SYN (root)"), T("nmap -sS HEDEF. Bağlantıyı tamamlamadan yoklar; "
                                                                "hem hızlıdır hem daha az iz bırakır. Root ister, "
                                                                "bu yüzden “Root ile çalıştır”ı kullan.",
                                                                "nmap -sS TARGET. Probes without completing the "
                                                                "connection; fast and leaves fewer traces. Needs "
                                                                "root, so use “Run as root”.")),
            ]),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[1:7])),
            ("tablo", [
                (T("open (açık)", "open"), T("Orada bir program dinliyor. Dışarıdan bağlanılabilir.",
                                             "A program is listening there. It can be reached from outside.")),
                (T("closed (kapalı)", "closed"), T("Kapı var ama kimse dinlemiyor. Nmap bunu çoğunlukla "
                                                   "yazmaz, “Not shown” satırında sayar.",
                                                   "The door exists but nobody listens. Nmap usually does not list "
                                                   "these; it counts them in the “Not shown” line.")),
                (T("filtered (süzülmüş)", "filtered"), T("Arada bir güvenlik duvarı var ve cevap vermiyor. Açık mı "
                                                         "kapalı mı bilinmez.",
                                                         "A firewall in between does not answer. Open or closed is "
                                                         "unknown.")),
            ]),
            ("not", T_DENEME_UYARISI),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("127.0.0.1 için Hızlı taramayı çalıştır ve hangi portların açık olduğunu not et.",
                  "Run Quick on 127.0.0.1 and write down which ports are open."),
                T("Aynı hedefte Servis / sürüm'ü dene; hangi programların çalıştığını gör.",
                  "Try Service / version on the same target; see which programs run."),
                T("Açık gördüğün bir servisi tanımıyorsan adını arayıp ne işe yaradığını öğren. Gerekmiyorsa "
                  "kapat, sonra taramayı tekrarla ve kapının kapandığını kontrol et.",
                  "If you do not recognise an open service, look up its name. If you do not need it, switch it "
                  "off, then scan again and check that the door is closed."),
                T("Ağında kendi ikinci bir bilgisayarın varsa ve CarotPot açıksa, o bilgisayardan tara; CarotPot "
                  "Panosu'nda “Port taraması” olarak görünmesi gerekir.",
                  "If you own a second computer on your network and CarotPot is on, scan from it; it should show "
                  "up as “Port scan” on the CarotPot dashboard."),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Yalnızca kendi cihazlarını ve izin aldığın sistemleri tara. Başkasının ağını izinsiz "
                        "taramak saldırı hazırlığı gibi görülür; ağ yöneticisi seni engeller ve hukuki sorun "
                        "çıkabilir. Okul ya da iş ağında önce yetkili kişiden yazılı izin al.",
                        "Scan only your own devices and systems you have permission for. Scanning someone else's "
                        "network without permission looks like preparing an attack; the network admin will block "
                        "you and legal trouble can follow. On a school or work network, get written permission "
                        "first.")),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "nmap -T4 -F 127.0.0.1"),
            ("p", T("-T4 hızı artırır, -F “fast” yani yalnızca yaygın 100 port demektir. Başka seçenekler için "
                    "terminalde man nmap yaz; kitabı da nmap.org/book adresinde ücretsiz okuyabilirsin.",
                    "-T4 raises the speed, -F means “fast”, only the 100 common ports. For other options type man "
                    "nmap in a terminal; the book is free to read at nmap.org/book.")),
        ]),
    ]
    return _konu("nmap", ARAC, adimlar, bolumler, ikon="ag")
