# -*- coding: utf-8 -*-
"""Komut Açıklayıcı veri tabanı: Güvenlik Paneli'ndeki SIZMA TESTİ / ANALİZ araçları (eğitim amaçlı).

CarotOS siber güvenliğe yeni başlayanlara öğretir: bu araçlar sistemde zaten kurulu ve Güvenlik
Paneli'nden çalıştırılıyor. Burada her birinin ne yaptığı, nasıl çalıştığı, bayraklarının anlamı,
ne kadar iz bıraktığı ve savunma tarafının onu nasıl gördüğü anlatılır. Başka bir sisteme dokunan
araçlarda "etik" işareti vardır: açıklamanın sonunda etik kullanım hatırlatması çıkar (Güvenlik
Paneli yerel olmayan hedeflerde ayrıca onay ister, bkz. ortak/etik_koruma.py).

Alanlar veri_guvenlik.py ile aynıdır; ek olarak:
  nasil   : aracın arka planda ne yaptığı (adım adım, kısa)
  savunma : savunmacının bu etkinliği nasıl gördüğü / nasıl önlediği
"""


def T(tr, en):
    return {"tr": tr, "en": en}


def A(tr, en, **kw):
    return {"a": T(tr, en), **kw}


TAKMA_ADLAR = {"netcat": "nc", "ncat": "nc", "nc.openbsd": "nc", "nc.traditional": "nc"}

KOMUTLAR = {
    "nmap": {
        "ozet": T("Ağ keşif ve port tarama aracı: hangi cihazların açık olduğunu, hangi portların dinlediğini ve "
                  "arkasında hangi servisin (ve sürümünün) çalıştığını bulur.",
                  "Network discovery and port scanner: finds which hosts are up, which ports are listening and "
                  "which service (and version) runs behind them."),
        "nasil": T("Önce hedefin ayakta olup olmadığını yoklar (ping/ARP), sonra her porta bir paket gönderip "
                   "cevaba bakar: SYN-ACK = açık, RST = kapalı, cevap yok = filtreli (güvenlik duvarı). "
                   "-sV ile açık porta bağlanıp servisin kendini tanıttığı ilk satırı (banner) okur.",
                   "It first checks whether the target is up (ping/ARP), then sends a packet to each port and "
                   "reads the reply: SYN-ACK = open, RST = closed, no reply = filtered (firewall). With -sV it "
                   "connects to open ports and reads the first line the service sends about itself (banner)."),
        "savunma": T("Kısa sürede çok sayıda porta gelen bağlantı, saldırı tespit sistemlerinde (IDS) ve güvenlik "
                     "duvarı günlüklerinde 'port taraması' olarak görünür. Kapatılmış gereksiz servisler ve "
                     "varsayılan 'gelen: deny' politikası (ufw) taramanın bulacağı şeyi azaltır.",
                     "Many connections to many ports in a short time show up as a 'port scan' in intrusion "
                     "detection systems (IDS) and firewall logs. Disabling unneeded services and a default "
                     "'incoming: deny' policy (ufw) reduce what a scan can find."),
        "gurultu": "orta", "yetki": "kismen", "etik": True, "gsd": "Port",
        "bayraklar": {
            "-sS": A("SYN taraması: bağlantıyı tamamlamaz (SYN gönderir, SYN-ACK gelince RST ile keser). Hızlıdır, "
                     "uygulama günlüklerine daha az düşer; ham paket gerektirdiği için root ister.",
                     "SYN scan: never completes the connection (sends SYN, answers SYN-ACK with RST). Fast and "
                     "shows up less in application logs; needs root because it crafts raw packets.", root=True),
            "-sT": A("TCP bağlantı taraması: her porta tam bağlantı kurar. Root gerekmez ama hedefin günlüklerinde "
                     "her bağlantı görünür.",
                     "TCP connect scan: makes a full connection to each port. No root needed, but every "
                     "connection appears in the target's logs.", g="orta"),
            "-sU": A("UDP taraması (DNS, SNMP, DHCP gibi servisler). Yavaştır: UDP'de cevap gelmemesi 'açık' da "
                     "'filtreli' de olabilir.",
                     "UDP scan (services like DNS, SNMP, DHCP). Slow: no reply over UDP can mean 'open' or "
                     "'filtered'.", root=True),
            "-sn": A("Port taraması yapmaz, yalnızca hangi cihazların ayakta olduğunu bulur (ping taraması).",
                     "No port scan; only finds which hosts are up (ping sweep).", g="dusuk"),
            "-Pn": A("Ayakta mı yoklamasını atlar, her hedefi açık sayar. Ping'e cevap vermeyen (güvenlik duvarlı) "
                     "makinelerde işe yarar ama tarama uzar.",
                     "Skips host discovery and treats every target as up. Useful for hosts that block ping "
                     "(firewalled), but the scan takes longer."),
            "-sV": A("Açık portlardaki servisin adını ve sürümünü bulmaya çalışır. Sürüm bilgisi, bilinen açıkları "
                     "(CVE) aramanın ilk adımıdır; servise gerçek istekler gönderdiği için daha gürültülüdür.",
                     "Tries to find the name and version of the service on open ports. The version is the first "
                     "step to looking up known flaws (CVE); it sends real requests, so it is noisier.", g="orta"),
            "-O": A("İşletim sistemini tahmin eder (TCP/IP yığınının cevaplarındaki küçük farklardan).",
                    "Guesses the operating system (from small differences in how the TCP/IP stack replies).",
                    root=True, g="orta"),
            "-A": A("Saldırgan mod: -O, -sV, -sC ve traceroute birlikte. Çok bilgi verir, çok iz bırakır.",
                    "Aggressive mode: -O, -sV, -sC and traceroute together. Lots of information, lots of noise.",
                    root=True, g="yuksek"),
            "-sC": A("Varsayılan NSE betiklerini çalıştırır (servisten ek bilgi toplayan küçük Lua betikleri).",
                     "Runs the default NSE scripts (small Lua scripts that gather extra details from services).",
                     g="orta"),
            "--script": A("Belirtilen NSE betiklerini çalıştırır. Bazı betik kategorileri (vuln, brute, exploit) "
                          "yalnızca keşif yapmaz, hedefe gerçekten saldırır.",
                          "Runs the named NSE scripts. Some script categories (vuln, brute, exploit) don't just "
                          "discover; they really attack the target.", deger=True, g="yuksek"),
            "-p": A("Taranacak portlar (ör. 22,80,443 ya da 1-1024).", "Ports to scan (e.g. 22,80,443 or 1-1024).",
                    deger=True),
            "-p-": A("Tüm 65535 TCP portunu tarar (varsayılan: en yaygın 1000 port). Uzun sürer.",
                     "Scans all 65535 TCP ports (default: the 1000 most common). Takes a while.", g="orta"),
            "-F": A("Hızlı tarama: yalnızca en yaygın 100 port.", "Fast scan: only the 100 most common ports."),
            "--top-ports": A("En yaygın N portu tarar.", "Scans the N most common ports.", deger=True),
            "--open": A("Yalnızca açık portları listeler.", "Lists only open ports."),
            "-n": A("Adres adlarını çözmez (DNS sorgusu yapmaz): daha hızlı ve daha sessiz.",
                    "Doesn't resolve names (no DNS lookups): faster and quieter."),
            "-v": A("Ayrıntılı çıktı: bulunan portları tarama sürerken gösterir.",
                    "Verbose output: shows ports as they are found."),
            "-6": A("IPv6 adreslerini tarar.", "Scans IPv6 addresses."),
            "-iL": A("Hedefleri bir dosyadan okur (satır başına bir hedef).", "Reads targets from a file (one per line).",
                     deger=True),
            "-oN": A("Sonucu normal metin olarak dosyaya yazar.", "Writes the result as normal text to a file.",
                     deger=True),
            "-oX": A("Sonucu XML olarak dosyaya yazar (başka araçlara aktarmak için).",
                     "Writes the result as XML to a file (to feed other tools).", deger=True),
            "-oG": A("Sonucu grep'lenebilir tek satırlık biçimde yazar.", "Writes the result in a greppable one-line format.",
                     deger=True),
            "-oA": A("Sonucu üç biçimde birden yazar (.nmap, .xml, .gnmap).", "Writes the result in all three formats (.nmap, .xml, .gnmap).",
                     deger=True),
            "--reason": A("Her portun neden açık/kapalı sayıldığını (hangi cevap geldiğini) yazar.",
                          "Prints why each port was judged open/closed (which reply came back)."),
        },
        "desenler": [
            (r"^-T[0-5]$", A("Zamanlama şablonu: T0-T1 çok yavaş ve sessiz (IDS'den kaçınmak için), T3 varsayılan, "
                             "T4 hızlı, T5 çok hızlı ama paket kaybı ve yanlış sonuç riski var.",
                             "Timing template: T0-T1 very slow and quiet (to avoid IDS), T3 default, T4 fast, "
                             "T5 very fast but risks dropped packets and wrong results.")),
        ],
        "uyari": T("Tarama başkasının ağında izinsiz yapılırsa saldırı girişimi sayılabilir; yerel ağda bile ağ "
                   "yöneticisini rahatsız eder. Alıştırma için 127.0.0.1 ya da Poligon'u kullan.",
                   "Scanning someone else's network without permission can be treated as an attack attempt; even "
                   "on a local network it bothers the network admin. Practise on 127.0.0.1 or Poligon."),
    },
    "tcpdump": {
        "ozet": T("Ağ arayüzünden geçen paketleri yakalar ve tek satırlık özetlerle gösterir; isterseniz .pcap "
                  "dosyasına kaydeder.",
                  "Captures the packets passing through a network interface and prints one-line summaries; "
                  "it can save them to a .pcap file."),
        "nasil": T("Arayüzü dinleme moduna alır ve çekirdeğin gördüğü her paketin bir kopyasını okur. Sonuna "
                   "yazılan filtre (ör. 'port 80', 'host 10.0.0.5') BPF olarak çekirdekte uygulanır: yalnızca "
                   "eşleşen paketler kopyalanır.",
                   "It puts the interface into capture mode and reads a copy of every packet the kernel sees. "
                   "The filter at the end (e.g. 'port 80', 'host 10.0.0.5') runs in the kernel as BPF: only "
                   "matching packets are copied."),
        "savunma": T("Pasiftir: paket göndermez, ağda iz bırakmaz. Savunma tarafında da kullanılır (şüpheli trafiği "
                     "görmek için). Şifreli (HTTPS, SSH) trafiğin içeriği okunamaz, yalnızca kimin kiminle "
                     "konuştuğu görünür.",
                     "It is passive: sends no packets and leaves no trace on the network. Defenders use it too "
                     "(to look at suspicious traffic). Encrypted traffic (HTTPS, SSH) can't be read, only who "
                     "talks to whom."),
        "gurultu": "dusuk", "yetki": "root", "kume": True, "gsd": "Packet",
        "bayraklar": {
            "-i": A("Dinlenecek arayüz (eth0, wlan0; 'any' = hepsi).", "Interface to listen on (eth0, wlan0; 'any' = all).",
                    deger=True),
            "-c": A("Bu kadar paket yakalayınca durur.", "Stops after capturing this many packets.", deger=True),
            "-n": A("Adresleri ada çevirmez (DNS sorgusu yapmaz).", "Doesn't turn addresses into names (no DNS lookups)."),
            "-nn": A("Ne adresleri ne port numaralarını ada çevirir.", "Turns neither addresses nor port numbers into names."),
            "-w": A("Paketleri ekrana değil .pcap dosyasına yazar (Wireshark ile sonra açılabilir).",
                    "Writes packets to a .pcap file instead of the screen (open it later in Wireshark).", deger=True),
            "-r": A("Canlı yakalamak yerine bir .pcap dosyasını okur (root gerekmez).",
                    "Reads a .pcap file instead of capturing live (no root needed).", deger=True),
            "-v": A("Daha ayrıntılı çözümleme (TTL, uzunluk, seçenekler).", "More detailed decoding (TTL, length, options)."),
            "-X": A("Paket içeriğini onaltılık ve ASCII olarak gösterir.", "Shows packet contents as hex and ASCII."),
            "-A": A("Paket içeriğini ASCII olarak gösterir (şifresiz HTTP'yi okumak için).",
                    "Shows packet contents as ASCII (to read unencrypted HTTP)."),
            "-D": A("Yakalama yapılabilecek arayüzleri listeler.", "Lists the interfaces you can capture on."),
            "-s": A("Paket başına kaç bayt yakalanacağı (0 = tamamı).", "How many bytes to capture per packet (0 = all).",
                    deger=True),
            "-e": A("Ethernet başlığını (MAC adreslerini) da gösterir.", "Also shows the Ethernet header (MAC addresses)."),
            "-q": A("Kısa çıktı.", "Short output."),
        },
        "uyari": T("Başkalarının trafiğini dinlemek, ağ senin olsa bile kişisel veri içerebilir. Yakalama dosyalarını "
                   "paylaşmadan önce içinde parola/çerez olmadığından emin ol.",
                   "Listening to other people's traffic can include personal data even on your own network. "
                   "Before sharing a capture file, make sure it contains no passwords/cookies."),
    },
    "tshark": {
        "ozet": T("Wireshark'ın terminal sürümü: paketleri yakalar ve protokol protokol çözümler (HTTP başlıkları, "
                  "DNS soruları, TLS el sıkışması…).",
                  "The terminal version of Wireshark: captures packets and dissects them protocol by protocol "
                  "(HTTP headers, DNS queries, TLS handshakes…)."),
        "nasil": T("tcpdump ile aynı yakalama altyapısını (libpcap) kullanır, ama her paketi Wireshark'ın yüzlerce "
                   "protokol çözücüsünden geçirir. -f yakalama filtresi (çekirdekte, BPF), -Y görüntü filtresidir "
                   "(yakalandıktan sonra, Wireshark söz dizimiyle: http.request, dns.qry.name…).",
                   "It uses the same capture layer as tcpdump (libpcap) but runs each packet through Wireshark's "
                   "hundreds of protocol dissectors. -f is a capture filter (in the kernel, BPF), -Y is a display "
                   "filter (after capture, Wireshark syntax: http.request, dns.qry.name…)."),
        "savunma": T("Pasiftir, iz bırakmaz. Olay incelemede (adli bilişim) .pcap dosyalarını okumak için de kullanılır.",
                     "Passive, leaves no trace. Also used in incident response (forensics) to read .pcap files."),
        "gurultu": "dusuk", "yetki": "kismen", "gsd": "Packet",
        "bayraklar": {
            "-i": A("Dinlenecek arayüz.", "Interface to listen on.", deger=True),
            "-c": A("Bu kadar paketten sonra durur.", "Stops after this many packets.", deger=True),
            "-D": A("Arayüzleri listeler.", "Lists interfaces."),
            "-f": A("Yakalama filtresi (BPF, tcpdump söz dizimi): ör. \"port 53\".", "Capture filter (BPF, tcpdump syntax): e.g. \"port 53\".",
                    deger=True),
            "-Y": A("Görüntü filtresi (Wireshark söz dizimi): ör. \"http.request\" ya da \"dns\".",
                    "Display filter (Wireshark syntax): e.g. \"http.request\" or \"dns\".", deger=True),
            "-w": A("Paketleri .pcapng dosyasına yazar.", "Writes packets to a .pcapng file.", deger=True),
            "-r": A("Kaydedilmiş bir yakalama dosyasını okur.", "Reads a saved capture file.", deger=True),
            "-V": A("Her paketin tüm protokol katmanlarını ağaç olarak gösterir.", "Shows every protocol layer of each packet as a tree."),
            "-T": A("Çıktı biçimi (fields, json, pdml…).", "Output format (fields, json, pdml…).", deger=True),
            "-e": A("-T fields ile hangi alanın yazılacağı (ör. ip.src).", "With -T fields, which field to print (e.g. ip.src).",
                    deger=True),
            "-z": A("İstatistik üretir (ör. io,phs = protokol dağılımı, conv,tcp = konuşmalar).",
                    "Produces statistics (e.g. io,phs = protocol hierarchy, conv,tcp = conversations).", deger=True),
            "-q": A("Paketleri tek tek yazmaz (istatistikle birlikte kullanılır).", "Doesn't print packets one by one (used with statistics)."),
            "-n": A("Ad çözümlemesi yapmaz.", "No name resolution."),
        },
        "uyari": T("Canlı yakalama için root ya da 'wireshark' grubu üyeliği gerekir; dosya okumak için gerekmez.",
                   "Live capture needs root or membership in the 'wireshark' group; reading a file doesn't."),
    },
    "aircrack-ng": {
        "ozet": T("Yakalanmış kablosuz trafikten (.cap) WEP anahtarını ya da WPA/WPA2 parolasını bulmaya çalışır.",
                  "Tries to recover a WEP key or a WPA/WPA2 passphrase from captured wireless traffic (.cap)."),
        "nasil": T("WPA/WPA2'de ağa bağlanan bir cihazın 4 yönlü el sıkışması (handshake) yakalanmış olmalıdır. "
                   "aircrack-ng kelime listesindeki her parolayı ağ adıyla birlikte PBKDF2'den geçirip el sıkışmadaki "
                   "değerle karşılaştırır: eşleşirse parola bulunmuştur. Yani bu bir sözlük saldırısıdır; listede "
                   "olmayan güçlü bir parola bulunamaz. WEP ise algoritma hatası yüzünden yeterli paketle kırılır.",
                   "For WPA/WPA2 you need a captured 4-way handshake of a device joining the network. aircrack-ng "
                   "runs every password in the wordlist through PBKDF2 together with the network name and compares "
                   "it with the handshake: a match means the password is found. So this is a dictionary attack; a "
                   "strong password that isn't in the list won't be found. WEP breaks with enough packets because "
                   "of a flaw in the algorithm."),
        "savunma": T("Kırma işlemi çevrimdışıdır (dosya üzerinde), ağda iz bırakmaz; iz yakalama aşamasında oluşur. "
                     "En iyi savunma: WPA3 ya da en az 12-15 karakterli, sözlükte olmayan bir WPA2 parolası ve WPS'i "
                     "kapatmak.",
                     "Cracking is offline (on a file) and leaves no trace on the network; traces come from the "
                     "capture step. Best defence: WPA3, or a WPA2 password of 12-15+ characters that isn't in any "
                     "dictionary, and WPS turned off."),
        "gurultu": "dusuk", "yetki": "yok", "kume": True, "etik": True, "gsd": "WPA",
        "bayraklar": {
            "-w": A("Kelime listesi dosyası (her satırda bir aday parola).", "Wordlist file (one candidate password per line).",
                    deger=True),
            "-b": A("Hedef erişim noktasının MAC adresi (BSSID): dosyada birden çok ağ varsa seçer.",
                    "MAC address (BSSID) of the target access point: picks one when the file has several networks.",
                    deger=True),
            "-e": A("Hedef ağın adı (ESSID).", "Name (ESSID) of the target network.", deger=True),
            "-a": A("Saldırı türü: 1 = WEP, 2 = WPA/WPA2-PSK.", "Attack mode: 1 = WEP, 2 = WPA/WPA2-PSK.", deger=True),
            "-q": A("Sessiz mod: ilerleme ekranını göstermez.", "Quiet mode: no progress screen."),
            "-p": A("Kullanılacak işlemci çekirdeği sayısı.", "Number of CPU cores to use.", deger=True),
            "-l": A("Bulunan anahtarı dosyaya yazar.", "Writes the found key to a file.", deger=True),
        },
        "uyari": T("Yalnızca kendi ağından yakaladığın dosyalarla dene. Başkasının ağının parolasını kırmak, "
                   "kullanmasan bile izinsiz erişim girişimidir.",
                   "Only try it with captures from your own network. Cracking someone else's network password is "
                   "an unauthorised access attempt even if you never use it."),
    },
    "nikto": {
        "ozet": T("Web sunucusu tarayıcısı: binlerce bilinen riskli dosya, eski yazılım sürümü ve yanlış ayarı tek tek "
                  "dener (ör. açık bırakılmış yönetim sayfaları, yedek dosyalar, eksik güvenlik başlıkları).",
                  "Web server scanner: tries thousands of known risky files, outdated software versions and "
                  "misconfigurations one by one (e.g. exposed admin pages, backup files, missing security headers)."),
        "nasil": T("Kendi veri tabanındaki her kontrol için sunucuya bir HTTP isteği gönderir ve cevabı (durum kodu, "
                   "içerik, başlıklar) bilinen imzalarla karşılaştırır. Açığı sömürmez, yalnızca 'burada şu sorun "
                   "olabilir' der; yanlış alarmlar olabilir, bulgular elle doğrulanmalıdır.",
                   "For every check in its database it sends an HTTP request and compares the reply (status code, "
                   "content, headers) with known signatures. It doesn't exploit anything, it only says 'this may be "
                   "a problem'; false alarms happen, so findings must be checked by hand."),
        "savunma": T("Çok gürültülüdür: sunucu erişim günlüğünde dakikada yüzlerce 404 ve tuhaf adres görünür, "
                     "User-Agent'ında bile 'Nikto' yazar. Web uygulama güvenlik duvarları (WAF) ve fail2ban kuralları "
                     "onu kolayca yakalar.",
                     "Very noisy: the server's access log fills with hundreds of 404s and odd paths per minute, and "
                     "even its User-Agent says 'Nikto'. Web application firewalls (WAF) and fail2ban rules catch it "
                     "easily."),
        "gurultu": "yuksek", "yetki": "yok", "etik": True, "gsd": "Web server",
        "bayraklar": {
            "-h": A("Hedef sunucu (adres, alan adı ya da tam URL).", "Target host (address, domain or full URL).", deger=True),
            "-host": A("Hedef sunucu (adres, alan adı ya da tam URL).", "Target host (address, domain or full URL).", deger=True),
            "-p": A("Port (varsayılan 80).", "Port (default 80).", deger=True),
            "-port": A("Port (varsayılan 80).", "Port (default 80).", deger=True),
            "-ssl": A("HTTPS kullanmaya zorlar.", "Forces HTTPS."),
            "-nossl": A("HTTPS kullanmaz.", "Doesn't use HTTPS."),
            "-Tuning": A("Hangi kontrol türlerinin yapılacağı (ör. 1 ilginç dosyalar, 2 yanlış ayar, 4 enjeksiyon, "
                         "9 SQL enjeksiyonu; x ile hariç tutulur).",
                         "Which kinds of checks to run (e.g. 1 interesting files, 2 misconfiguration, 4 injection, "
                         "9 SQL injection; x excludes).", deger=True),
            "-C": A("CGI dizinlerini kontrol et (all = hepsini dene).", "CGI directories to check (all = try them all).",
                    deger=True),
            "-o": A("Raporu dosyaya yazar.", "Writes the report to a file.", deger=True),
            "-output": A("Raporu dosyaya yazar.", "Writes the report to a file.", deger=True),
            "-Format": A("Rapor biçimi (txt, htm, csv, xml).", "Report format (txt, htm, csv, xml).", deger=True),
            "-maxtime": A("Taramayı en fazla bu süre çalıştırır (ör. 10m).", "Runs the scan for at most this long (e.g. 10m).",
                          deger=True),
            "-useragent": A("İsteklerde başka bir tarayıcı kimliği gösterir.", "Uses a different browser identity in requests.",
                            deger=True),
            "-Display": A("Ekranda neyin gösterileceği (V = ayrıntılı).", "What to show on screen (V = verbose).", deger=True),
            "-Plugins": A("Çalıştırılacak eklentiler.", "Plugins to run.", deger=True),
        },
        "uyari": T("Yüzlerce istek gönderdiği için yalnızca kendi sunucunda ya da izinli test ortamında kullan.",
                   "It sends hundreds of requests, so use it only on your own server or an authorised test environment."),
    },
    "sqlmap": {
        "ozet": T("SQL enjeksiyonu test aracı: bir web adresindeki parametrenin, kullanıcı girdisini veritabanı "
                  "sorgusuna güvensiz biçimde ekleyip eklemediğini otomatik dener; açık varsa veritabanını okuyabilir.",
                  "SQL injection testing tool: automatically checks whether a parameter in a web address puts user "
                  "input into a database query unsafely; if so, it can read the database."),
        "nasil": T("Parametreye (ör. ?id=1) özel hazırlanmış değerler koyar ve sayfanın cevabındaki farka bakar: "
                   "hata mesajı (error-based), sayfanın değişip değişmemesi (boolean-based), cevabın gecikmesi "
                   "(time-based, ör. SLEEP) ya da UNION ile başka tablodan veri çekme. Açık doğrulanınca veritabanı "
                   "adlarını, tabloları ve satırları adım adım çıkarabilir.",
                   "It puts specially crafted values into the parameter (e.g. ?id=1) and watches how the reply "
                   "changes: an error message (error-based), whether the page changes (boolean-based), a delayed "
                   "reply (time-based, e.g. SLEEP) or pulling data from another table with UNION. Once confirmed, "
                   "it can extract database names, tables and rows step by step."),
        "savunma": T("Sunucu günlüklerinde aynı parametreye gelen yüzlerce tuhaf istek (tırnak, UNION, SLEEP) görünür. "
                     "Kalıcı çözüm koddadır: parametreli sorgular (hazır ifadeler) kullanmak; WAF yalnızca ek katmandır.",
                     "Server logs show hundreds of odd requests (quotes, UNION, SLEEP) to the same parameter. The real "
                     "fix is in the code: parameterised queries (prepared statements); a WAF is only an extra layer."),
        "gurultu": "yuksek", "yetki": "yok", "etik": True, "gsd": "SQL injection",
        "bayraklar": {
            "-u": A("Hedef URL (test edilecek parametreyle birlikte, ör. http://localhost/urun?id=1).",
                    "Target URL (with the parameter to test, e.g. http://localhost/item?id=1).", deger=True),
            "--url": A("Hedef URL.", "Target URL.", deger=True),
            "-r": A("İsteği bir dosyadan okur (tarayıcıdan/proxy'den kaydedilmiş ham HTTP isteği).",
                    "Reads the request from a file (a raw HTTP request saved from a browser/proxy).", deger=True),
            "--data": A("POST gövdesi (form alanları): ör. \"kullanici=a&parola=b\".", "POST body (form fields): e.g. \"user=a&pass=b\".",
                        deger=True),
            "--cookie": A("İsteklere eklenecek çerez (oturum açılmış sayfaları test etmek için).",
                          "Cookie to send with requests (to test pages behind a login).", deger=True),
            "-p": A("Yalnızca bu parametreyi test eder.", "Tests only this parameter.", deger=True),
            "--level": A("Test kapsamı 1-5: yüksek seviye çerez ve başlıkları da dener, çok daha fazla istek atar.",
                         "Test depth 1-5: higher levels also try cookies and headers and send many more requests.",
                         deger=True, g="yuksek"),
            "--risk": A("Risk 1-3: yüksek risk, veriyi değiştirebilecek (UPDATE gibi) ya da ağır sorgular da dener.",
                        "Risk 1-3: higher risk also tries payloads that may change data (like UPDATE) or heavy queries.",
                        deger=True, g="yuksek"),
            "--batch": A("Hiç soru sormaz, her soruya varsayılan cevabı verir.", "Never asks; answers every question with the default."),
            "--technique": A("Kullanılacak teknikler: B boolean, E error, U union, S stacked, T time, Q inline.",
                             "Techniques to use: B boolean, E error, U union, S stacked, T time, Q inline.", deger=True),
            "--dbs": A("Açık doğrulanınca veritabanı adlarını listeler.", "Lists database names once the flaw is confirmed."),
            "--tables": A("Tabloları listeler.", "Lists tables."),
            "--columns": A("Sütunları listeler.", "Lists columns."),
            "-D": A("Çalışılacak veritabanı.", "Database to work on.", deger=True),
            "-T": A("Çalışılacak tablo.", "Table to work on.", deger=True),
            "--dump": A("Tablonun içeriğini çeker ve diske kaydeder (gerçek veriler: kişisel bilgi olabilir).",
                        "Pulls the table's contents and saves them to disk (real data: may be personal information).",
                        g="yuksek"),
            "--current-user": A("Uygulamanın veritabanına hangi kullanıcıyla bağlandığını gösterir.",
                                "Shows which user the application connects to the database as."),
            "--os-shell": A("Veritabanı üzerinden sunucuda komut çalıştırmayı dener: test değil, ele geçirme adımıdır.",
                            "Tries to run commands on the server through the database: not a test, a takeover step.",
                            g="yuksek"),
            "--forms": A("Sayfadaki formları bulup onları test eder.", "Finds the forms on the page and tests them."),
            "--crawl": A("Siteyi verilen derinlikte gezip bulduğu adresleri test eder.", "Crawls the site to the given depth and tests the URLs it finds.",
                         deger=True, g="yuksek"),
            "--random-agent": A("Her çalıştırmada rastgele bir tarayıcı kimliği kullanır.", "Uses a random browser identity."),
            "--threads": A("Aynı anda gönderilecek istek sayısı.", "Number of concurrent requests.", deger=True),
            "--flush-session": A("Bu hedef için kaydedilmiş önceki sonuçları siler, baştan başlar.",
                                 "Deletes saved results for this target and starts over."),
        },
        "uyari": T("Açık bulunan bir sitede --dump gerçek kişisel verileri bilgisayarına kopyalar. Yalnızca kendi "
                   "uygulamanda ya da Poligon/izinli laboratuvarda kullan.",
                   "On a vulnerable site --dump copies real personal data to your computer. Use it only on your own "
                   "application or Poligon/an authorised lab."),
    },
    "john": {
        "ozet": T("John the Ripper: parola özetlerini (hash) kırmaya çalışır; bir parola politikasının ne kadar zayıf "
                  "olduğunu ölçmek için kullanılır.",
                  "John the Ripper: tries to crack password hashes; used to measure how weak a password policy is."),
        "nasil": T("Özet tek yönlüdür, geri çevrilemez. John aday parolaları (kelime listesi, kurallarla türetilmiş "
                   "varyasyonlar: Parola1!, p4rola…, ya da tüm kombinasyonlar) aynı algoritmayla özetleyip dosyadaki "
                   "özetle karşılaştırır. Eşleşen aday parolanın kendisidir. Hız algoritmaya bağlıdır: MD5 saniyede "
                   "milyonlarca, bcrypt/yescrypt yalnızca birkaç yüz dener.",
                   "A hash is one-way and can't be reversed. John hashes candidate passwords (a wordlist, variations "
                   "made by rules: Password1!, p4ssword…, or every combination) with the same algorithm and compares "
                   "them with the hashes in the file. A match is the password itself. Speed depends on the algorithm: "
                   "millions per second for MD5, only a few hundred for bcrypt/yescrypt."),
        "savunma": T("Çevrimdışı çalışır, hedefte iz bırakmaz; asıl olay özet dosyasının ele geçirilmesidir. "
                     "Savunma: yavaş ve tuzlu algoritmalar (yescrypt, bcrypt, Argon2), uzun parolalar, /etc/shadow "
                     "gibi dosyaların korunması.",
                     "Runs offline, leaves no trace on the target; the real incident is the hash file being stolen. "
                     "Defence: slow salted algorithms (yescrypt, bcrypt, Argon2), long passwords, protecting files "
                     "like /etc/shadow."),
        "gurultu": "dusuk", "yetki": "yok", "gsd": "Hash",
        "bayraklar": {
            "--wordlist": A("Kelime listesi (sözlük) modu: verilen dosyadaki her satırı dener.",
                            "Wordlist (dictionary) mode: tries every line in the given file.", deger=True),
            "--rules": A("Kelime listesindeki her kelimeden kurallarla yeni adaylar türetir (büyük harf, sona rakam…).",
                         "Derives new candidates from each wordlist entry with rules (capitals, trailing digits…)."),
            "--single": A("Tek mod: kullanıcı adı ve ad-soyad gibi bilgilerden aday üretir (en hızlı ilk deneme).",
                          "Single mode: makes candidates from the username and full name (fastest first try)."),
            "--incremental": A("Artımlı mod: tüm karakter kombinasyonlarını dener (kaba kuvvet; uzun parolalarda yıllar sürebilir).",
                               "Incremental mode: tries every character combination (brute force; can take years for long passwords)."),
            "--format": A("Özet türünü elle belirtir (ör. raw-md5, sha512crypt, bcrypt).", "Sets the hash type by hand (e.g. raw-md5, sha512crypt, bcrypt).",
                          deger=True),
            "--show": A("Daha önce kırılmış parolaları gösterir (john.pot dosyasından).", "Shows passwords cracked earlier (from the john.pot file)."),
            "--fork": A("Bu kadar işlemle paralel çalışır.", "Runs this many processes in parallel.", deger=True),
            "--session": A("Oturuma ad verir (sonra --restore ile devam etmek için).", "Names the session (to continue later with --restore).",
                           deger=True),
            "--restore": A("Yarıda kalan oturuma devam eder.", "Continues an interrupted session."),
            "--list": A("Bilgi listeler (ör. --list=formats desteklenen özet türleri).", "Lists information (e.g. --list=formats supported hash types).",
                        deger=True),
            "--pot": A("Kırılan parolaların yazılacağı dosya.", "File where cracked passwords are stored.", deger=True),
        },
        "uyari": T("Yalnızca sana ait ya da test için izin verilmiş özet dosyalarıyla çalış. Kırılan parolalar "
                   "~/.john/john.pot dosyasında açık metin durur; işin bitince sil.",
                   "Only use hash files that are yours or that you're allowed to test. Cracked passwords stay in "
                   "plain text in ~/.john/john.pot; delete it when you're done."),
    },
    "hydra": {
        "ozet": T("Çevrimiçi parola deneme (kaba kuvvet) aracı: SSH, FTP, HTTP formu gibi bir servise kullanıcı adı "
                  "ve parola listelerindeki her çifti gerçekten deneyerek giriş yapmaya çalışır.",
                  "Online password guessing (brute force) tool: tries to log in to a service such as SSH, FTP or an "
                  "HTTP form by really trying every pair from username and password lists."),
        "nasil": T("Servisin kendi giriş protokolünü konuşur ve her denemede gerçek bir oturum açma isteği gönderir; "
                   "birden çok bağlantıyı paralel açar (-t). John'dan farkı: çevrimiçidir, yani her deneme hedef "
                   "sunucuya gider ve orada kayda geçer.",
                   "It speaks the service's own login protocol and sends a real login request for every try, opening "
                   "several connections in parallel (-t). Unlike John it is online: every attempt reaches the target "
                   "server and gets logged there."),
        "savunma": T("Çok gürültülüdür: /var/log/auth.log'da art arda 'Failed password' satırları görünür. fail2ban "
                     "adresi birkaç denemede engeller, hesap kilitleme politikaları hesabı kilitler (kendi hesabını "
                     "kilitleyebilirsin!). En iyi savunma: SSH'ta parola yerine anahtarla giriş.",
                     "Very noisy: /var/log/auth.log fills with 'Failed password' lines. fail2ban blocks the address "
                     "after a few tries and account lockout policies lock the account (you can lock yourself out!). "
                     "Best defence: key-based SSH login instead of passwords."),
        "gurultu": "yuksek", "yetki": "yok", "kume": False, "etik": True, "gsd": "Brute force",
        "bayraklar": {
            "-l": A("Tek bir kullanıcı adı dener.", "Tries a single username.", deger=True),
            "-L": A("Kullanıcı adı listesi dosyası.", "Username list file.", deger=True),
            "-p": A("Tek bir parola dener.", "Tries a single password.", deger=True),
            "-P": A("Parola listesi dosyası.", "Password list file.", deger=True),
            "-C": A("'kullanici:parola' çiftlerinden oluşan dosya.", "File of 'user:password' pairs.", deger=True),
            "-e": A("Ek denemeler: n = boş parola, s = kullanıcı adıyla aynı, r = kullanıcı adının tersi.",
                    "Extra tries: n = empty password, s = same as the username, r = the username reversed.", deger=True),
            "-t": A("Aynı anda açılacak bağlantı sayısı (varsayılan 16). Yüksek değer hem daha hızlı hem daha "
                    "gürültülüdür; SSH sunucuları bağlantıları kesebilir.",
                    "Number of parallel connections (default 16). Higher is faster and noisier; SSH servers may drop "
                    "connections.", deger=True, g="yuksek"),
            "-s": A("Servisin standart dışı portu.", "Non-standard port of the service.", deger=True),
            "-f": A("İlk geçerli çifti bulunca durur.", "Stops at the first valid pair."),
            "-V": A("Her denemeyi ekrana yazar.", "Prints every attempt."),
            "-v": A("Ayrıntılı çıktı.", "Verbose output."),
            "-o": A("Bulunan çiftleri dosyaya yazar.", "Writes found pairs to a file.", deger=True),
            "-w": A("Cevap için bekleme süresi (saniye).", "Time to wait for a reply (seconds).", deger=True),
            "-u": A("Sırayı değiştirir: önce her kullanıcıya aynı parolayı dener (hesap kilitlemeyi geciktirir).",
                    "Changes the order: tries the same password on every user first (delays account lockouts)."),
            "-M": A("Hedefleri bir dosyadan okur.", "Reads targets from a file.", deger=True),
        },
        "uyari": T("Her deneme gerçek bir giriş girişimidir. Başkasının servisinde izinsiz denemek suçtur; kendi "
                   "sisteminde bile hesabını kilitleyebilir. Poligon'un sahte giriş servisinde dene.",
                   "Every attempt is a real login attempt. Trying it on someone else's service without permission is "
                   "an offence; even on your own system it can lock your account. Practise on Poligon's fake login "
                   "service."),
    },
    "nc": {
        "ozet": T("netcat: TCP/UDP bağlantısı açan ya da dinleyen çok amaçlı araç ('ağın İsviçre çakısı'). Port "
                  "denemek, servisin banner'ını okumak, iki makine arasında dosya ya da metin aktarmak için kullanılır.",
                  "netcat: an all-purpose tool that opens or listens for TCP/UDP connections ('the network's Swiss "
                  "army knife'). Used to test ports, read a service's banner, or move files or text between two machines."),
        "nasil": T("Klavyeden yazılanı bağlantıya, bağlantıdan geleni ekrana aktarır. -l ile sunucu gibi bir portu "
                   "dinler, olmadan istemci gibi bağlanır.",
                   "It sends what you type into the connection and prints what comes back. With -l it listens on a "
                   "port like a server; without it, it connects like a client."),
        "savunma": T("Dinleyen bir nc, 'ss -tlnp' çıktısında görünür. -e ile kabuk bağlamak saldırganların 'ters "
                     "kabuk' yöntemidir; çıkış trafiğini süzmek (egress filtreleme) bunu zorlaştırır.",
                     "A listening nc shows up in 'ss -tlnp'. Attaching a shell with -e is the attacker's 'reverse "
                     "shell' technique; filtering outgoing traffic (egress filtering) makes it harder."),
        "gurultu": "dusuk", "yetki": "yok", "kume": True, "gsd": "Port",
        "bayraklar": {
            "-l": A("Bağlanmak yerine dinler (sunucu modu).", "Listens instead of connecting (server mode)."),
            "-p": A("Kaynak/dinleme portu.", "Source/listening port.", deger=True),
            "-v": A("Ayrıntılı: bağlantının kurulup kurulmadığını yazar.", "Verbose: prints whether the connection succeeded."),
            "-n": A("DNS sorgusu yapmaz, yalnızca IP adresi kabul eder.", "No DNS lookups; accepts only IP addresses."),
            "-z": A("Veri göndermeden yalnızca portun açık olup olmadığına bakar (basit port taraması).",
                    "Only checks whether the port is open without sending data (simple port scan).", g="orta"),
            "-u": A("TCP yerine UDP kullanır.", "Uses UDP instead of TCP."),
            "-w": A("Bağlantı/boşta bekleme süresi (saniye).", "Connection/idle timeout (seconds).", deger=True),
            "-k": A("Bir bağlantı bitince yenisini dinlemeye devam eder.", "Keeps listening after a connection ends."),
            "-N": A("Girdi bitince bağlantıyı kapatır.", "Closes the connection when the input ends."),
            "-e": A("Bağlantıya bir program bağlar (ör. /bin/sh): uzaktan komut çalıştırma, 'ters kabuk'. "
                    "Debian'ın varsayılan nc'sinde (OpenBSD) bu seçenek yoktur.",
                    "Attaches a program to the connection (e.g. /bin/sh): remote command execution, a 'reverse "
                    "shell'. Debian's default nc (OpenBSD) doesn't have this option.", g="yuksek"),
        },
        "uyari": T("Dinleyen bir port açtığında ağdaki herkes ona bağlanabilir; işin bitince kapat.",
                   "When you open a listening port anyone on the network can connect to it; close it when you're done."),
    },
}
