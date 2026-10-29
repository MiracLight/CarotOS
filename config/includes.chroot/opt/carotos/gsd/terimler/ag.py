# -*- coding: utf-8 -*-
"""GSD -- Ağ ve Protokoller terimleri."""

TERIMLER = [
    {
        "id": "ip",
        "baslik": {"tr": "IP Adresi", "en": "IP Address"},
        "kisa": {"tr": "Bir ağ üzerindeki cihazı benzersiz biçimde tanımlayan sayısal adres.",
                 "en": "The numeric address that uniquely identifies a device on a network."},
        "aciklama": {
            "tr": "IP adresi, posta adresine benzer şekilde bir cihazın ağdaki yerini belirtir. IPv4 "
                  "\"192.168.1.10\" gibi dört basamaklı gruplardan oluşurken, çok daha geniş bir adres "
                  "havuzu sunan IPv6 \"2001:db8::1\" gibi onaltılık gruplar kullanır. Özel (yerel) ve "
                  "genel (internet üzerinde görünen) olmak üzere iki türü vardır.",
            "en": "An IP address, much like a postal address, marks a device's place on a network. IPv4 "
                  "uses four decimal groups like \"192.168.1.10\", while IPv6 -- offering a vastly larger "
                  "address pool -- uses hexadecimal groups like \"2001:db8::1\". Addresses come in "
                  "private (local) and public (visible on the internet) forms.",
        },
        "ornek": "ip addr show",
        "ilgili": ["mac_adresi", "subnet", "nat"],
    },
    {
        "id": "mac_adresi",
        "baslik": {"tr": "MAC Adresi", "en": "MAC Address"},
        "kisa": {"tr": "Bir ağ donanımına fabrikada verilen, teorik olarak eşsiz fiziksel adres.",
                 "en": "The theoretically unique physical address burned into a network interface at the factory."},
        "aciklama": {
            "tr": "MAC (Media Access Control) adresi, \"AA:BB:CC:11:22:33\" biçiminde altı baytlık bir "
                  "tanımlayıcıdır ve bir yerel ağ (LAN) içinde cihazları birbirinden ayırt etmek için "
                  "kullanılır. IP adresinin aksine genellikle sabittir, ama yazılımla geçici olarak "
                  "değiştirilebilir (MAC spoofing).",
            "en": "A MAC (Media Access Control) address is a six-byte identifier like "
                  "\"AA:BB:CC:11:22:33\", used to tell devices apart within a local network (LAN). Unlike "
                  "an IP address it's usually fixed in hardware, though it can be temporarily changed in "
                  "software (MAC spoofing).",
        },
        "ornek": "ip link show",
        "ilgili": ["ip", "osi_modeli"],
    },
    {
        "id": "tcp",
        "baslik": {"tr": "TCP", "en": "TCP"},
        "kisa": {"tr": "Verinin sırayla ve eksiksiz ulaşmasını garanti eden bağlantı temelli ağ protokolü.",
                 "en": "The connection-based protocol that guarantees data arrives in order and intact."},
        "aciklama": {
            "tr": "TCP (Transmission Control Protocol), veriyi göndermeden önce bir \"el sıkışma\" "
                  "(three-way handshake) ile bağlantı kurar, kaybolan paketleri yeniden gönderir ve "
                  "sırayı korur. Web sayfası yüklemek, e-posta göndermek ya da dosya indirmek gibi "
                  "doğruluğun hız kadar önemli olduğu işlerde kullanılır.",
            "en": "TCP (Transmission Control Protocol) establishes a connection via a three-way "
                  "handshake before sending data, retransmits lost packets, and preserves order. It's "
                  "used for tasks like loading a web page, sending email or downloading a file, where "
                  "correctness matters as much as speed.",
        },
        "ilgili": ["udp", "port", "osi_modeli"],
    },
    {
        "id": "udp",
        "baslik": {"tr": "UDP", "en": "UDP"},
        "kisa": {"tr": "Bağlantı kurmadan, hız için doğruluk garantisinden ödün veren hafif ağ protokolü.",
                 "en": "A lightweight protocol that skips connection setup, trading guaranteed delivery for speed."},
        "aciklama": {
            "tr": "UDP (User Datagram Protocol), TCP'nin aksine el sıkışma ya da yeniden gönderme "
                  "yapmaz; paketleri \"gönder ve unut\" mantığıyla yollar. Bu da onu canlı video, "
                  "oyunlar ve DNS sorguları gibi hız ve düşük gecikmenin önemli olduğu, birkaç paket "
                  "kaybının sorun yaratmadığı işler için uygun kılar.",
            "en": "UDP (User Datagram Protocol), unlike TCP, skips the handshake and retransmission; it "
                  "fires packets off in a \"send and forget\" manner. That makes it a good fit for live "
                  "video, gaming and DNS lookups, where speed and low latency matter more than losing an "
                  "occasional packet.",
        },
        "ilgili": ["tcp", "dns", "port"],
    },
    {
        "id": "port",
        "baslik": {"tr": "Port (Bağlantı Noktası)", "en": "Port"},
        "kisa": {"tr": "Bir cihaz üzerinde belirli bir servisi tanımlayan 0-65535 arası sayı.",
                 "en": "A number from 0-65535 that identifies a specific service on a device."},
        "aciklama": {
            "tr": "IP adresi bir binayı gösterirse, port o binadaki daire numarasıdır: aynı cihazda "
                  "çalışan web sunucusu (80/443), SSH (22) ya da e-posta gibi birden fazla servisi "
                  "birbirinden ayırır. nmap gibi araçlar, bir sistemde hangi portların açık olduğunu "
                  "tarayarak hangi servislerin çalıştığını ortaya çıkarır.",
            "en": "If an IP address points to a building, a port is the apartment number inside it: it "
                  "separates multiple services on the same device -- a web server (80/443), SSH (22), "
                  "email and so on. Tools like nmap scan which ports are open on a system to reveal "
                  "which services are running.",
        },
        "ornek": "sudo nmap -p 1-1000 192.168.1.1",
        "ilgili": ["tcp", "udp", "ssh"],
    },
    {
        "id": "dns",
        "baslik": {"tr": "DNS", "en": "DNS"},
        "kisa": {"tr": "İnsan dostu alan adlarını IP adreslerine çeviren internetin telefon rehberi.",
                 "en": "The internet's phone book, translating human-friendly domain names into IP addresses."},
        "aciklama": {
            "tr": "DNS (Domain Name System), \"carotos.org\" gibi bir adresi tarayıcının gerçekten "
                  "bağlanacağı IP adresine çevirir; böylece sayıları ezberlemek yerine isimleri hatırlamak "
                  "yeterli olur. DNS sunucuları bu eşleşmeleri hiyerarşik olarak saklar ve sorguları "
                  "önbelleğe alarak hızlandırır.",
            "en": "DNS (Domain Name System) translates an address like \"carotos.org\" into the actual IP "
                  "address the browser connects to, so people only need to remember names instead of "
                  "numbers. DNS servers store these mappings hierarchically and cache lookups to speed "
                  "things up.",
        },
        "ornek": "dig carotos.org",
        "ilgili": ["ip", "udp", "dhcp"],
    },
    {
        "id": "dhcp",
        "baslik": {"tr": "DHCP", "en": "DHCP"},
        "kisa": {"tr": "Ağa bağlanan cihazlara otomatik IP adresi dağıtan protokol.",
                 "en": "The protocol that automatically hands out IP addresses to devices joining a network."},
        "aciklama": {
            "tr": "DHCP (Dynamic Host Configuration Protocol) olmasaydı her cihaza elle bir IP adresi "
                  "girmek gerekirdi. Ev yönlendiricileri de dahil çoğu ağda bir DHCP sunucusu, bağlanan "
                  "her cihaza boşta bir IP adresi, ağ geçidi ve DNS sunucusu bilgisi atar.",
            "en": "Without DHCP (Dynamic Host Configuration Protocol), every device would need a manually "
                  "typed IP address. On most networks -- including home routers -- a DHCP server assigns "
                  "each connecting device a free IP address plus gateway and DNS server information.",
        },
        "ilgili": ["ip", "router", "dns"],
    },
    {
        "id": "http",
        "baslik": {"tr": "HTTP", "en": "HTTP"},
        "kisa": {"tr": "Web tarayıcılarının sunucularla veri alışverişi için kullandığı temel protokol.",
                 "en": "The foundational protocol web browsers use to exchange data with servers."},
        "aciklama": {
            "tr": "HTTP (Hypertext Transfer Protocol), bir tarayıcının bir sayfa \"isteği\" (GET), form "
                  "verisi gönderimi (POST) gibi işlemleri sunucuyla konuşmak için kullandığı metin "
                  "tabanlı protokoldür. Şifrelenmemiş olduğu için ağ üzerinde izlenebilir; bu yüzden "
                  "günümüzde yerini büyük ölçüde HTTPS'e bırakmıştır.",
            "en": "HTTP (Hypertext Transfer Protocol) is the text-based protocol a browser uses to talk "
                  "to a server: requesting a page (GET), submitting form data (POST), and so on. Because "
                  "it's unencrypted it can be observed on the network, which is why it has largely been "
                  "replaced by HTTPS today.",
        },
        "ilgili": ["https", "tcp", "proxy"],
    },
    {
        "id": "https",
        "baslik": {"tr": "HTTPS", "en": "HTTPS"},
        "kisa": {"tr": "TLS şifrelemesiyle korunan, HTTP'nin güvenli sürümü.",
                 "en": "The secure version of HTTP, protected by TLS encryption."},
        "aciklama": {
            "tr": "HTTPS, HTTP trafiğini SSL/TLS ile şifreleyerek araya giren birinin (man-in-the-middle) "
                  "verileri okumasını ya da değiştirmesini zorlaştırır; ayrıca sunucunun gerçekten iddia "
                  "ettiği taraf olduğunu bir sertifikayla doğrular. Tarayıcıdaki kilit simgesi, "
                  "bağlantının HTTPS ile korunduğunu gösterir.",
            "en": "HTTPS wraps HTTP traffic in SSL/TLS encryption, making it far harder for someone "
                  "sitting in the middle to read or tamper with the data, and verifies the server's "
                  "identity with a certificate. The padlock icon in a browser shows the connection is "
                  "protected by HTTPS.",
        },
        "ilgili": ["http", "ssl_tls", "proxy"],
    },
    {
        "id": "ssl_tls",
        "baslik": {"tr": "SSL/TLS", "en": "SSL/TLS"},
        "kisa": {"tr": "Ağ üzerindeki iletişimi şifreleyen ve kimlik doğrulayan protokol ailesi.",
                 "en": "The protocol family that encrypts and authenticates communication over a network."},
        "aciklama": {
            "tr": "SSL (Secure Sockets Layer) ve onun modern, güvenli devamı TLS (Transport Layer "
                  "Security), iki taraf arasındaki trafiği açık anahtarlı şifreleme ile korur ve "
                  "sertifikalarla karşı tarafın kimliğini doğrular. Günümüzde SSL kullanım dışıdır; "
                  "\"SSL sertifikası\" denilen şey aslında genellikle TLS kullanır.",
            "en": "SSL (Secure Sockets Layer) and its modern, secure successor TLS (Transport Layer "
                  "Security) protect traffic between two parties with public-key encryption and verify "
                  "identity through certificates. SSL itself is obsolete today; what people still call an "
                  "\"SSL certificate\" is usually using TLS underneath.",
        },
        "ilgili": ["https", "vpn", "acik_anahtar"],
    },
    {
        "id": "vpn",
        "baslik": {"tr": "VPN", "en": "VPN"},
        "kisa": {"tr": "İnternet üzerinden şifreli bir özel tünel kuran ağ teknolojisi.",
                 "en": "A network technology that builds an encrypted private tunnel over the internet."},
        "aciklama": {
            "tr": "VPN (Virtual Private Network), cihazla bir sunucu arasında şifreli bir tünel kurarak "
                  "trafiğin sanki özel bir ağ üzerinden gidiyormuş gibi görünmesini sağlar. Hem "
                  "kurumların uzaktaki çalışanları şirket ağına güvenle bağlaması hem de genel Wi-Fi "
                  "ağlarında gizlilik sağlamak için kullanılır.",
            "en": "A VPN (Virtual Private Network) builds an encrypted tunnel between a device and a "
                  "server, making traffic appear to travel over a private network. It's used both by "
                  "organizations to safely connect remote employees to the company network and by "
                  "individuals for privacy on public Wi-Fi.",
        },
        "ilgili": ["ssl_tls", "proxy", "guvenlik_duvari"],
    },
    {
        "id": "guvenlik_duvari",
        "baslik": {"tr": "Güvenlik Duvarı (Firewall)", "en": "Firewall"},
        "kisa": {"tr": "Ağ trafiğini kurallara göre süzen, istenmeyen bağlantıları engelleyen koruma katmanı.",
                 "en": "A protective layer that filters network traffic by rule, blocking unwanted connections."},
        "aciklama": {
            "tr": "Güvenlik duvarı, gelen ve giden bağlantıları önceden tanımlı kurallara (port, IP "
                  "adresi, protokol) göre denetleyip izin verir ya da reddeder. Linux'ta çekirdek "
                  "düzeyinde netfilter/iptables bu işi görür; CarotOS Panel'deki UFW aracı bu kuralları "
                  "basit bir arayüzle yönetir.",
            "en": "A firewall inspects incoming and outgoing connections against predefined rules -- "
                  "port, IP address, protocol -- and allows or denies them. On Linux this happens at the "
                  "kernel level via netfilter/iptables; the UFW tool in CarotOS Panel manages those rules "
                  "through a simple interface.",
        },
        "ornek": "sudo ufw status verbose",
        "ilgili": ["port", "vpn", "ip"],
    },
    {
        "id": "router",
        "baslik": {"tr": "Yönlendirici (Router)", "en": "Router"},
        "kisa": {"tr": "Farklı ağlar arasında veri paketlerini doğru yöne ileten cihaz.",
                 "en": "The device that forwards data packets between different networks in the right direction."},
        "aciklama": {
            "tr": "Yönlendirici, örneğin ev ağınızla internet servis sağlayıcınızın ağı arasında köprü "
                  "kurar; gelen paketleri hedef IP adresine bakarak doğru yola yönlendirir. Çoğu ev "
                  "yönlendiricisi aynı zamanda DHCP sunucusu ve basit bir güvenlik duvarı görevi de "
                  "görür.",
            "en": "A router bridges, say, your home network and your internet service provider's "
                  "network, forwarding incoming packets toward their destination based on the IP "
                  "address. Most home routers also double as a DHCP server and a basic firewall.",
        },
        "ilgili": ["switch_ag", "gateway", "dhcp"],
    },
    {
        "id": "switch_ag",
        "baslik": {"tr": "Anahtar (Switch)", "en": "Switch"},
        "kisa": {"tr": "Yerel ağdaki cihazları birbirine bağlayan, trafiği MAC adresine göre yönlendiren donanım.",
                 "en": "The hardware that connects devices on a local network, forwarding traffic by MAC address."},
        "aciklama": {
            "tr": "Bir anahtar, yönlendiriciden farklı olarak genellikle tek bir yerel ağ içinde çalışır "
                  "ve gelen veriyi tüm cihazlara değil, yalnızca doğru MAC adresine sahip cihaza iletir. "
                  "Bu, eski hub cihazlarına kıyasla ağ trafiğini çok daha verimli kılar.",
            "en": "Unlike a router, a switch typically operates within a single local network and "
                  "forwards incoming data only to the device with the matching MAC address, not to "
                  "everyone. This makes network traffic far more efficient than the old hub devices it "
                  "replaced.",
        },
        "ilgili": ["router", "mac_adresi", "osi_modeli"],
    },
    {
        "id": "gateway",
        "baslik": {"tr": "Ağ Geçidi (Gateway)", "en": "Gateway"},
        "kisa": {"tr": "Yerel ağdan dışarıya çıkan trafiğin ilk uğrağı olan adres.",
                 "en": "The first hop for traffic leaving a local network."},
        "aciklama": {
            "tr": "Bir cihaz, kendi yerel ağı dışındaki bir adrese ulaşmak istediğinde paketi önce "
                  "varsayılan ağ geçidine (genellikle yönlendiricinin kendisi) gönderir; oradan internete "
                  "ya da başka bir ağa yönlendirilir. Yanlış yapılandırılmış bir ağ geçidi, cihazın "
                  "yerel ağ dışına hiç çıkamamasına neden olur.",
            "en": "When a device wants to reach an address outside its own local network, it first sends "
                  "the packet to the default gateway -- usually the router itself -- which forwards it "
                  "onward to the internet or another network. A misconfigured gateway means a device "
                  "can't reach anything outside its local network at all.",
        },
        "ilgili": ["router", "ip", "subnet"],
    },
    {
        "id": "subnet",
        "baslik": {"tr": "Alt Ağ (Subnet)", "en": "Subnet"},
        "kisa": {"tr": "Büyük bir ağı daha küçük, yönetilebilir parçalara bölen mantıksal yapı.",
                 "en": "A logical structure that divides a larger network into smaller, manageable pieces."},
        "aciklama": {
            "tr": "Alt ağlama (subnetting), \"192.168.1.0/24\" gibi bir ağı bölümlere ayırarak trafiği "
                  "izole etmeyi, yönetimi kolaylaştırmayı ve güvenliği artırmayı sağlar. \"/24\" kısmı "
                  "alt ağ maskesini belirtir; kaç bitin ağı, kaç bitin cihazı tanımladığını gösterir.",
            "en": "Subnetting splits a network like \"192.168.1.0/24\" into sections to isolate traffic, "
                  "simplify management and improve security. The \"/24\" part is the subnet mask, "
                  "specifying how many bits identify the network versus the individual device.",
        },
        "ilgili": ["ip", "gateway", "nat"],
    },
    {
        "id": "nat",
        "baslik": {"tr": "NAT", "en": "NAT"},
        "kisa": {"tr": "Birden çok cihazın tek bir genel IP adresini paylaşmasını sağlayan teknik.",
                 "en": "The technique that lets many devices share a single public IP address."},
        "aciklama": {
            "tr": "NAT (Network Address Translation), bir ev ağındaki onlarca cihazın özel IP "
                  "adreslerini, internete çıkarken yönlendiricinin tek bir genel IP adresi arkasında "
                  "gizler. Bu hem sınırlı IPv4 adreslerinin daha verimli kullanılmasını sağlar hem de bir "
                  "ölçüde doğal bir koruma katmanı oluşturur.",
            "en": "NAT (Network Address Translation) hides the private IP addresses of dozens of devices "
                  "on a home network behind the router's single public IP address when they go out to "
                  "the internet. This both uses the limited pool of IPv4 addresses more efficiently and "
                  "forms a degree of natural protection.",
        },
        "ilgili": ["ip", "subnet", "router"],
    },
    {
        "id": "proxy",
        "baslik": {"tr": "Vekil Sunucu (Proxy)", "en": "Proxy"},
        "kisa": {"tr": "İstemci ile hedef sunucu arasına girip trafiği onun adına ileten ara sunucu.",
                 "en": "An intermediary server that sits between a client and a target, relaying traffic on its behalf."},
        "aciklama": {
            "tr": "Bir vekil sunucuya yapılan istek, hedef sunucuya proxy'nin kendi kimliğiyle iletilir; "
                  "bu sayede gerçek istemcinin IP adresi gizlenebilir, içerik önbelleğe alınabilir ya da "
                  "kurumsal ağlarda belirli sitelere erişim süzülebilir. VPN'den farkı, genellikle tüm "
                  "trafiği değil belirli bir uygulamanın trafiğini yönlendirmesidir.",
            "en": "A request made through a proxy reaches the target server carrying the proxy's own "
                  "identity, which can hide the real client's IP, cache content, or filter access to "
                  "certain sites on a corporate network. Unlike a VPN, a proxy typically routes a single "
                  "application's traffic rather than everything.",
        },
        "ilgili": ["vpn", "http", "nat"],
    },
    {
        "id": "ssh",
        "baslik": {"tr": "SSH", "en": "SSH"},
        "kisa": {"tr": "Uzaktaki bir sisteme şifreli komut satırı erişimi sağlayan protokol.",
                 "en": "The protocol that provides encrypted command-line access to a remote system."},
        "aciklama": {
            "tr": "SSH (Secure Shell), bir sunucuya uzaktan bağlanıp komut çalıştırmayı -- tüm trafiği "
                  "şifreleyerek -- mümkün kılar; eski, şifrelenmemiş Telnet'in yerini almıştır. Şifre "
                  "yerine genellikle daha güvenli olan ortak/özel anahtar çiftleriyle kimlik doğrulaması "
                  "da yapılabilir.",
            "en": "SSH (Secure Shell) makes it possible to connect to a server remotely and run commands "
                  "-- with all traffic encrypted -- and has replaced the old, unencrypted Telnet. "
                  "Authentication can also use a public/private key pair instead of a password, which is "
                  "generally more secure.",
        },
        "ornek": "ssh carot@192.168.1.20",
        "ilgili": ["port", "acik_anahtar", "guvenlik_duvari"],
    },
    {
        "id": "ftp",
        "baslik": {"tr": "FTP", "en": "FTP"},
        "kisa": {"tr": "Dosyaları bir sunucu ile bir istemci arasında aktarmak için kullanılan eski protokol.",
                 "en": "An older protocol used to transfer files between a server and a client."},
        "aciklama": {
            "tr": "FTP (File Transfer Protocol), dosya yükleme ve indirme için tasarlanmıştır ama klasik "
                  "hâliyle kullanıcı adı ve şifreyi şifrelemeden gönderir; bu yüzden günümüzde yerini "
                  "şifreli SFTP (SSH üzerinden) ya da FTPS'e bırakmıştır.",
            "en": "FTP (File Transfer Protocol) was designed for uploading and downloading files, but in "
                  "its classic form sends usernames and passwords unencrypted, which is why it has "
                  "largely been replaced today by encrypted SFTP (over SSH) or FTPS.",
        },
        "ilgili": ["ssh", "port", "tcp"],
    },
    {
        "id": "osi_modeli",
        "baslik": {"tr": "OSI Modeli", "en": "OSI Model"},
        "kisa": {"tr": "Ağ iletişimini yedi kavramsal katmana ayıran referans çerçevesi.",
                 "en": "The reference framework that splits network communication into seven conceptual layers."},
        "aciklama": {
            "tr": "OSI modeli; fiziksel katmandan (kablolar, sinyaller) uygulama katmanına (HTTP gibi "
                  "protokoller) kadar yedi katman tanımlar ve her katmanın kendinden altındaki katmanın "
                  "hizmetlerini kullandığı bir çerçeve sunar. Günlük hayatta protokolleri konumlandırmak "
                  "ve ağ sorunlarını katman katman izole etmek için kullanılır.",
            "en": "The OSI model defines seven layers, from the physical layer (cables, signals) up to "
                  "the application layer (protocols like HTTP), each building on the services of the one "
                  "below it. In practice it's used to place protocols in context and to isolate network "
                  "problems layer by layer.",
        },
        "ilgili": ["tcp", "mac_adresi", "switch_ag"],
    },
    {
        "id": "mtu",
        "baslik": {"tr": "MTU", "en": "MTU"},
        "kisa": {"tr": "Bir ağ bağlantısında tek seferde gönderilebilecek en büyük paket boyutu.",
                 "en": "The largest packet size that can be sent in one piece over a network link."},
        "aciklama": {
            "tr": "MTU (Maximum Transmission Unit), genellikle Ethernet için 1500 bayt olarak "
                  "ayarlıdır; bundan büyük veri, parçalara bölünerek (fragmentation) gönderilir. VPN "
                  "tünelleri gibi ek başlık ekleyen teknolojilerde MTU'nun doğru ayarlanmaması bağlantı "
                  "sorunlarına yol açabilir.",
            "en": "MTU (Maximum Transmission Unit) is commonly set to 1500 bytes for Ethernet; data "
                  "larger than that gets split into fragments. Technologies that add extra headers, like "
                  "VPN tunnels, can cause connection problems if the MTU isn't set correctly.",
        },
        "ilgili": ["tcp", "vpn"],
    },
    {
        "id": "ping",
        "baslik": {"tr": "ping", "en": "ping"},
        "kisa": {"tr": "Bir ağ cihazına ulaşılıp ulaşılmadığını ve yanıt süresini ölçen temel tanı aracı.",
                 "en": "The basic diagnostic tool that checks whether a network host is reachable and measures response time."},
        "aciklama": {
            "tr": "ping, hedefe ICMP Echo Request paketleri gönderir ve gelen yanıtlardan bağlantının "
                  "açık olup olmadığını, gecikme (latency) süresini ve paket kaybını ölçer. Bir ağ "
                  "sorununu araştırırken atılacak genellikle ilk adımdır.",
            "en": "ping sends ICMP Echo Request packets to a target and measures from the replies "
                  "whether the connection is up, how much latency there is, and whether any packets are "
                  "lost. It's usually the very first step when troubleshooting a network issue.",
        },
        "ornek": "ping -c 4 carotos.org",
        "ilgili": ["traceroute", "ip", "tcp"],
    },
    {
        "id": "traceroute",
        "baslik": {"tr": "traceroute", "en": "traceroute"},
        "kisa": {"tr": "Bir hedefe ulaşana kadar paketin geçtiği her yönlendiriciyi listeleyen araç.",
                 "en": "The tool that lists every router a packet passes through on its way to a target."},
        "aciklama": {
            "tr": "traceroute, hedefe giden yoldaki her \"atlamayı\" (hop) sırayla gösterir ve her "
                  "atlamadaki gecikmeyi ölçer; bu sayede bir yavaşlığın ya da kopukluğun ağın hangi "
                  "noktasında olduğu anlaşılabilir.",
            "en": "traceroute shows every \"hop\" along the path to a target in order and measures the "
                  "delay at each one, which helps pinpoint exactly where in the network a slowdown or "
                  "break is happening.",
        },
        "ornek": "traceroute carotos.org",
        "ilgili": ["ping", "router", "ip"],
    },
    {
        "id": "localhost",
        "baslik": {"tr": "Localhost", "en": "Localhost"},
        "kisa": {"tr": "Bir cihazın kendi kendine işaret eden özel adı: 127.0.0.1.",
                 "en": "The special name a device uses to refer to itself: 127.0.0.1."},
        "aciklama": {
            "tr": "localhost adı her zaman 127.0.0.1 (döngü/loopback) adresine çözülür ve bir cihazın "
                  "ağa hiç çıkmadan kendi üzerindeki bir servise bağlanmasını sağlar. Geliştiriciler, "
                  "henüz yayınlanmamış bir web sunucusunu test ederken sıkça localhost kullanır.",
            "en": "The name localhost always resolves to 127.0.0.1 (the loopback address), letting a "
                  "device connect to a service running on itself without ever touching the network. "
                  "Developers commonly use localhost to test a web server before it's published.",
        },
        "ornek": "curl http://localhost:8080",
        "ilgili": ["ip", "port"],
    },
]
