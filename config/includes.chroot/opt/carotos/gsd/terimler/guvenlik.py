# -*- coding: utf-8 -*-
"""GSD -- Siber Güvenlik terimleri."""

TERIMLER = [
    {
        "id": "zafiyet",
        "baslik": {"tr": "Zafiyet (Vulnerability)", "en": "Vulnerability"},
        "kisa": {"tr": "Bir sistemde saldırganın kötüye kullanabileceği zayıflık ya da hata.",
                 "en": "A weakness or flaw in a system that an attacker can abuse."},
        "aciklama": {
            "tr": "Zafiyet; eski bir yazılım sürümü, yanlış yapılandırma ya da kod hatası gibi "
                  "nedenlerle ortaya çıkabilir ve kendi başına zarar vermez -- bir saldırgan onu "
                  "\"istismar\" (exploit) ettiğinde zarara dönüşür. Düzenli güncellemeler ve tarama "
                  "araçları (nikto, nmap gibi) zafiyetleri bulmanın temel yoludur.",
            "en": "A vulnerability can come from an outdated software version, a misconfiguration or a "
                  "coding mistake, and causes no harm on its own -- it only becomes damaging once an "
                  "attacker \"exploits\" it. Regular updates and scanning tools like nikto and nmap are "
                  "the main way to find them.",
        },
        "ilgili": ["exploit", "cve", "zafiyet_taramasi"],
    },
    {
        "id": "exploit",
        "baslik": {"tr": "İstismar (Exploit)", "en": "Exploit"},
        "kisa": {"tr": "Bir zafiyetten faydalanmak için yazılmış kod ya da yöntem.",
                 "en": "Code or a technique written to take advantage of a vulnerability."},
        "aciklama": {
            "tr": "Bir istismar, bir zafiyeti kullanarak sistemde yetkisiz bir eylem gerçekleştirir -- "
                  "örneğin yetki yükseltme, veri sızdırma ya da uzaktan kod çalıştırma. Güvenlik "
                  "araştırmacıları, zafiyeti sorumlu biçimde bildirmeden önce etkisini kanıtlamak için "
                  "\"kanıt amaçlı istismar\" (proof-of-concept) de yazabilir.",
            "en": "An exploit uses a vulnerability to carry out an unauthorized action on a system -- "
                  "privilege escalation, data exfiltration, or remote code execution, for example. "
                  "Security researchers may also write a \"proof-of-concept\" exploit to demonstrate "
                  "impact before responsibly disclosing the flaw.",
        },
        "ilgili": ["zafiyet", "sifirinci_gun", "yetki_yukseltme"],
    },
    {
        "id": "zararli_yazilim",
        "baslik": {"tr": "Zararlı Yazılım (Malware)", "en": "Malware"},
        "kisa": {"tr": "Zarar vermek ya da yetkisiz erişim sağlamak için tasarlanmış her türlü yazılımın genel adı.",
                 "en": "The umbrella term for any software designed to cause harm or gain unauthorized access."},
        "aciklama": {
            "tr": "Zararlı yazılım; virüs, solucan, truva atı, fidye yazılımı, casus yazılım ve rootkit "
                  "gibi birçok alt türü kapsayan şemsiye bir terimdir. Her biri farklı bir yöntemle "
                  "yayılır ya da zarar verir, ama ortak noktaları kullanıcının gerçek izni ya da bilgisi "
                  "olmadan çalışmalarıdır.",
            "en": "Malware is an umbrella term covering many subtypes -- viruses, worms, trojans, "
                  "ransomware, spyware, rootkits. Each spreads or does harm differently, but they share "
                  "the trait of running without the user's genuine knowledge or consent.",
        },
        "ilgili": ["fidye_yazilimi", "truva_ati", "rootkit"],
    },
    {
        "id": "fidye_yazilimi",
        "baslik": {"tr": "Fidye Yazılımı (Ransomware)", "en": "Ransomware"},
        "kisa": {"tr": "Dosyaları şifreleyip açmak için fidye talep eden zararlı yazılım türü.",
                 "en": "Malware that encrypts files and demands a ransom to unlock them."},
        "aciklama": {
            "tr": "Fidye yazılımı, bulaştığı sistemdeki dosyaları güçlü şifreleme ile kilitler ve "
                  "genellikle kripto para karşılığında bir \"çözme anahtarı\" vaat eder. Ödeme yapmak "
                  "dosyaların geri geleceğini garanti etmez; en iyi savunma düzenli ve çevrimdışı "
                  "yedeklerdir.",
            "en": "Ransomware locks files on an infected system with strong encryption and typically "
                  "promises a \"decryption key\" in exchange for payment, often in cryptocurrency. Paying "
                  "does not guarantee the files come back; regular, offline backups are the best "
                  "defense.",
        },
        "ilgili": ["zararli_yazilim", "kimlik_avi"],
    },
    {
        "id": "kimlik_avi",
        "baslik": {"tr": "Kimlik Avı (Phishing)", "en": "Phishing"},
        "kisa": {"tr": "Güvenilir biri gibi davranıp kullanıcıyı şifre ya da hassas bilgi vermeye ikna etme saldırısı.",
                 "en": "An attack that impersonates a trusted party to trick a user into giving up passwords or sensitive data."},
        "aciklama": {
            "tr": "Kimlik avı genellikle sahte bir e-posta ya da web sitesiyle, bankanız ya da tanıdığınız "
                  "bir şirketmiş gibi davranarak sizi bir bağlantıya tıklatıp bilgilerinizi girdirmeye "
                  "çalışır. \"Spear phishing\", belirli bir kişiyi hedef alan, araştırılarak kişiselleştirilmiş "
                  "bir türüdür.",
            "en": "Phishing typically uses a fake email or website posing as your bank or a company you "
                  "know, trying to get you to click a link and enter your information. \"Spear phishing\" "
                  "is a more targeted, researched variant aimed at a specific person.",
        },
        "ilgili": ["sosyal_muhendislik", "fidye_yazilimi"],
    },
    {
        "id": "sosyal_muhendislik",
        "baslik": {"tr": "Sosyal Mühendislik", "en": "Social Engineering"},
        "kisa": {"tr": "Teknik açık yerine insan psikolojisini hedef alan manipülasyon tekniği.",
                 "en": "A manipulation technique that targets human psychology rather than a technical flaw."},
        "aciklama": {
            "tr": "Sosyal mühendislik; aciliyet, otorite ya da merak hissi uyandırarak insanları normalde "
                  "yapmayacakları bir şeyi yapmaya (bir bağlantıya tıklamak, bir şifreyi paylaşmak) ikna "
                  "eder. Kimlik avı, telefonla kimliğe bürünme (vishing) ve tailgating en yaygın "
                  "biçimleridir. En güçlü güvenlik duvarının bile insan zaafına karşı yetersiz "
                  "kalabileceğini gösterir.",
            "en": "Social engineering exploits urgency, authority or curiosity to get people to do "
                  "something they otherwise wouldn't -- click a link, share a password. Phishing, voice "
                  "impersonation (vishing) and tailgating are its most common forms, and it shows how "
                  "even the strongest firewall can be undone by human nature.",
        },
        "ilgili": ["kimlik_avi"],
    },
    {
        "id": "sifirinci_gun",
        "baslik": {"tr": "Sıfırıncı Gün (Zero-Day)", "en": "Zero-Day"},
        "kisa": {"tr": "Yazılım üreticisi henüz farkında değilken keşfedilen ve istismar edilebilen zafiyet.",
                 "en": "A vulnerability discovered and exploitable before the software maker even knows about it."},
        "aciklama": {
            "tr": "\"Sıfırıncı gün\" adı, üreticinin sorunu düzeltmek için \"sıfır günü\" kalmış "
                  "olmasından gelir -- henüz bir yama yokken saldırganlar zafiyeti kullanabilir. Bu "
                  "zafiyetler yüksek değerli oldukları için bazen kara borsada alınıp satılır.",
            "en": "The name \"zero-day\" comes from the maker having \"zero days\" left to fix the "
                  "issue -- attackers can use the flaw before any patch exists. Because they're so "
                  "valuable, these vulnerabilities are sometimes bought and sold on black markets.",
        },
        "ilgili": ["zafiyet", "exploit", "cve"],
    },
    {
        "id": "ddos",
        "baslik": {"tr": "DDoS", "en": "DDoS"},
        "kisa": {"tr": "Bir hedefi binlerce cihazdan gelen trafikle boğup erişilmez kılma saldırısı.",
                 "en": "An attack that floods a target with traffic from thousands of devices to make it unreachable."},
        "aciklama": {
            "tr": "DDoS (Dağıtık Hizmet Reddi), genellikle ele geçirilmiş cihazlardan oluşan bir botnet "
                  "kullanılarak bir sunucuya aynı anda devasa miktarda istek göndermeyi ve sunucuyu "
                  "normal kullanıcılara hizmet veremez hâle getirmeyi amaçlar. Veri çalmaz; amacı "
                  "yalnızca hizmeti durdurmaktır.",
            "en": "DDoS (Distributed Denial of Service) typically uses a botnet of compromised devices "
                  "to send a server a massive volume of requests at once, overwhelming it so it can't "
                  "serve legitimate users. It doesn't steal data -- its only goal is to take the service "
                  "down.",
        },
        "ilgili": ["botnet"],
    },
    {
        "id": "botnet",
        "baslik": {"tr": "Botnet", "en": "Botnet"},
        "kisa": {"tr": "Zararlı yazılımla ele geçirilip uzaktan birlikte yönetilen cihazlar ağı.",
                 "en": "A network of devices infected and remotely controlled together as one."},
        "aciklama": {
            "tr": "Bir botnet'teki her cihaz (\"bot\" ya da \"zombi\"), genellikle sahibinin haberi "
                  "olmadan bir komuta-kontrol sunucusundan talimat alır; DDoS saldırılarında, spam "
                  "göndermede ya da kripto para madenciliğinde toplu olarak kullanılabilir.",
            "en": "Every device in a botnet (a \"bot\" or \"zombie\"), usually without its owner's "
                  "knowledge, takes instructions from a command-and-control server, and can be used "
                  "collectively for DDoS attacks, sending spam, or cryptocurrency mining.",
        },
        "ilgili": ["ddos", "zararli_yazilim", "arka_kapi"],
    },
    {
        "id": "arka_kapi",
        "baslik": {"tr": "Arka Kapı (Backdoor)", "en": "Backdoor"},
        "kisa": {"tr": "Normal kimlik doğrulamayı atlayarak bir sisteme gizli erişim sağlayan yol.",
                 "en": "A hidden way into a system that bypasses normal authentication."},
        "aciklama": {
            "tr": "Bir arka kapı, bir saldırgan tarafından sisteme kötü amaçla yerleştirilebileceği gibi, "
                  "geliştiriciler tarafından hata ayıklama için bilerek bırakılıp sonra unutulmuş da "
                  "olabilir. Her iki durumda da fark edilmeden sisteme tekrar tekrar erişim sağladığı "
                  "için ciddi bir risktir.",
            "en": "A backdoor can be planted maliciously by an attacker, or it can be something "
                  "developers deliberately left in for debugging and then forgot about. Either way it's "
                  "a serious risk because it grants repeated, unnoticed access to the system.",
        },
        "ilgili": ["rootkit", "truva_ati", "botnet"],
    },
    {
        "id": "yetki_yukseltme",
        "baslik": {"tr": "Yetki Yükseltme (Privilege Escalation)", "en": "Privilege Escalation"},
        "kisa": {"tr": "Sınırlı bir hesaptan daha yüksek (genellikle root) yetkiye geçme tekniği.",
                 "en": "The technique of moving from a limited account to higher, often root, privileges."},
        "aciklama": {
            "tr": "Bir saldırgan sisteme düşük yetkili bir hesapla girdikten sonra, bir zafiyeti ya da "
                  "yanlış yapılandırmayı kullanarak root yetkisine ulaşmaya çalışabilir. \"Dikey\" yükselme "
                  "(daha yüksek yetkiye geçiş) ile \"yatay\" yükselme (aynı yetki seviyesinde başka bir "
                  "hesaba geçiş) ayrımı yapılır.",
            "en": "Once an attacker gets into a system with a low-privilege account, they may try to "
                  "reach root privileges by exploiting a vulnerability or a misconfiguration. A "
                  "distinction is made between \"vertical\" escalation (moving to higher privilege) and "
                  "\"horizontal\" escalation (moving to another account at the same level).",
        },
        "ilgili": ["exploit", "root_kullanici"],
    },
    {
        "id": "pentest",
        "baslik": {"tr": "Sızma Testi (Pentest)", "en": "Penetration Testing"},
        "kisa": {"tr": "Bir sistemin güvenliğini, izinle gerçek bir saldırıyı simüle ederek sınama süreci.",
                 "en": "The process of testing a system's security by simulating a real attack, with permission."},
        "aciklama": {
            "tr": "Sızma testi, yetkili güvenlik uzmanlarının (pentester) kuruluşun izniyle sistemlere "
                  "sızmaya çalışıp bulduğu zafiyetleri raporladığı yapılandırılmış bir süreçtir. CarotOS "
                  "Güvenlik Paneli'ndeki nmap, nikto, sqlmap gibi araçlar tam da bu tür çalışmalarda "
                  "kullanılır -- Poligon uygulaması da bunu güvenli bir ortamda pratik etme imkânı sunar.",
            "en": "Penetration testing is a structured process where authorized security professionals "
                  "(pentesters) try to break into systems with the organization's permission and report "
                  "the vulnerabilities they find. Tools in the CarotOS Security Panel -- nmap, nikto, "
                  "sqlmap -- are exactly what this kind of work uses, and the Poligon app lets you "
                  "practice it in a safe environment.",
        },
        "ilgili": ["kirmizi_mavi_takim", "zafiyet_taramasi"],
    },
    {
        "id": "kirmizi_mavi_takim",
        "baslik": {"tr": "Kırmızı Takım / Mavi Takım", "en": "Red Team / Blue Team"},
        "kisa": {"tr": "Saldırıyı simüle eden (kırmızı) ve savunmayı üstlenen (mavi) iki rakip güvenlik ekibi.",
                 "en": "Two opposing security teams: red simulates attacks, blue handles defense."},
        "aciklama": {
            "tr": "Kırmızı takım gerçek bir saldırganın bakış açısıyla sistemlere sızmaya çalışırken, "
                  "mavi takım bu girişimleri tespit edip engellemeye çalışır. İkisinin birlikte çalıştığı "
                  "tatbikatlara \"mor takım\" (purple team) egzersizi denir ve her iki tarafın "
                  "öğrendiklerini paylaşmasını sağlar.",
            "en": "The red team tries to break into systems from a real attacker's perspective while the "
                  "blue team tries to detect and stop those attempts. Exercises where the two work "
                  "together are called \"purple team\" exercises, letting both sides share what they "
                  "learned.",
        },
        "ilgili": ["pentest"],
    },
    {
        "id": "cve",
        "baslik": {"tr": "CVE", "en": "CVE"},
        "kisa": {"tr": "Bilinen bir güvenlik zafiyetine verilen benzersiz, herkese açık kimlik numarası.",
                 "en": "The unique, public identifier assigned to a known security vulnerability."},
        "aciklama": {
            "tr": "CVE (Common Vulnerabilities and Exposures), \"CVE-2024-12345\" biçiminde bir kimlik "
                  "numarasıdır ve aynı zafiyetten farklı kaynaklarda bahsedilirken ortak bir referans "
                  "sağlar. nikto ve nmap gibi tarama araçları bulduğu zafiyetleri genellikle CVE "
                  "numarasıyla raporlar.",
            "en": "A CVE (Common Vulnerabilities and Exposures) identifier looks like "
                  "\"CVE-2024-12345\" and gives a shared reference point when the same vulnerability is "
                  "discussed across different sources. Scanning tools like nikto and nmap typically "
                  "report what they find using its CVE number.",
        },
        "ilgili": ["zafiyet", "sifirinci_gun", "nikto"],
    },
    {
        "id": "ids_ips",
        "baslik": {"tr": "IDS/IPS", "en": "IDS/IPS"},
        "kisa": {"tr": "Ağ trafiğinde şüpheli etkinliği tespit eden (IDS) ya da engelleyen (IPS) sistemler.",
                 "en": "Systems that detect (IDS) or actively block (IPS) suspicious network activity."},
        "aciklama": {
            "tr": "IDS (Intrusion Detection System) şüpheli trafiği izleyip uyarı üretirken, IPS "
                  "(Intrusion Prevention System) bir adım daha ileri giderek bu trafiği otomatik olarak "
                  "engeller. CarotOS Panel'deki fail2ban, başarısız giriş denemelerini izleyip ilgili IP "
                  "adresini engelleyerek basit bir IPS gibi çalışır.",
            "en": "An IDS (Intrusion Detection System) watches suspicious traffic and raises alerts, "
                  "while an IPS (Intrusion Prevention System) goes a step further and blocks that traffic "
                  "automatically. fail2ban in CarotOS Panel works like a simple IPS, watching failed "
                  "login attempts and blocking the offending IP address.",
        },
        "ilgili": ["fail2ban", "guvenlik_duvari"],
    },
    {
        "id": "honeypot",
        "baslik": {"tr": "Bal Küpü (Honeypot)", "en": "Honeypot"},
        "kisa": {"tr": "Saldırganları çekmek ve davranışlarını incelemek için kurulan sahte hedef sistem.",
                 "en": "A decoy system set up to attract attackers and study their behavior."},
        "aciklama": {
            "tr": "Bal küpü, gerçek bir sunucu gibi görünen ama değerli hiçbir veri barındırmayan bir "
                  "tuzaktır; amacı saldırganları gerçek sistemlerden uzaklaştırmak ve kullandıkları "
                  "yöntemleri güvenli biçimde gözlemlemektir. CarotOS'taki CarotPot uygulaması tam "
                  "olarak bu amaçla, gelen bağlantı denemelerini kaydedip görselleştirir.",
            "en": "A honeypot is a trap that looks like a real server but holds nothing of value; its "
                  "purpose is to draw attackers away from real systems and safely observe the methods "
                  "they use. CarotOS's CarotPot app does exactly this, logging and visualizing incoming "
                  "connection attempts.",
        },
        "ilgili": ["pentest", "ids_ips"],
    },
    {
        "id": "sandbox",
        "baslik": {"tr": "Kum Havuzu (Sandbox)", "en": "Sandbox"},
        "kisa": {"tr": "Şüpheli bir yazılımı izole bir ortamda, gerçek sisteme zarar vermeden çalıştırma yöntemi.",
                 "en": "Running a suspicious program in an isolated environment where it can't harm the real system."},
        "aciklama": {
            "tr": "Bir kum havuzu, çalışan yazılımın dosya sistemine, ağa ya da diğer süreçlere erişimini "
                  "sınırlayarak onu geri kalan sistemden izole eder. Zararlı yazılım analizinde yaygın "
                  "kullanılır; CarotOS'taki Poligon uygulaması da öğrencilerin saldırı tekniklerini "
                  "güvenli, izole bir ortamda denemesini sağlar.",
            "en": "A sandbox isolates a running program from the rest of the system by limiting its "
                  "access to the file system, the network or other processes. It's widely used in "
                  "malware analysis; CarotOS's Poligon app similarly lets students try attack techniques "
                  "in a safe, isolated environment.",
        },
        "ilgili": ["zararli_yazilim", "honeypot"],
    },
    {
        "id": "iki_faktorlu_dogrulama",
        "baslik": {"tr": "İki Faktörlü Doğrulama (2FA)", "en": "Two-Factor Authentication (2FA)"},
        "kisa": {"tr": "Şifreye ek olarak ikinci bir kanıt isteyerek hesap güvenliğini artıran yöntem.",
                 "en": "A method that strengthens account security by requiring a second proof alongside the password."},
        "aciklama": {
            "tr": "2FA, \"bildiğin bir şey\" (şifre) ile \"sahip olduğun bir şey\" (telefon, güvenlik "
                  "anahtarı) ya da \"olduğun bir şey\" (parmak izi) kanıtlarından ikisini birleştirir. "
                  "Şifre çalınsa bile saldırganın ikinci faktöre erişmesi gerektiğinden hesabın ele "
                  "geçirilme olasılığını büyük ölçüde azaltır.",
            "en": "2FA combines two of \"something you know\" (a password), \"something you have\" (a "
                  "phone, a security key) or \"something you are\" (a fingerprint). Even if the password "
                  "is stolen, an attacker would still need the second factor, which greatly reduces the "
                  "chance of account takeover.",
        },
        "ilgili": ["kaba_kuvvet", "sozluk_saldirisi"],
    },
    {
        "id": "kaba_kuvvet",
        "baslik": {"tr": "Kaba Kuvvet Saldırısı (Brute Force)", "en": "Brute-Force Attack"},
        "kisa": {"tr": "Doğru şifreyi bulana kadar tüm olası kombinasyonları sırayla deneme yöntemi.",
                 "en": "Systematically trying every possible combination until the correct password is found."},
        "aciklama": {
            "tr": "Kaba kuvvet saldırısı hiçbir akıllı tahmin yapmaz; yalnızca mümkün olan her "
                  "kombinasyonu dener. Uzun ve karmaşık şifreler bu saldırıyı pratikte imkânsız hâle "
                  "getirirken, hydra gibi araçlar bu yöntemi giriş formlarına karşı otomatikleştirir. "
                  "fail2ban gibi araçlar, art arda başarısız denemeleri tespit ederek bu saldırıyı "
                  "yavaşlatır.",
            "en": "A brute-force attack makes no clever guesses; it simply tries every possible "
                  "combination. Long, complex passwords make this attack impractical, while tools like "
                  "hydra automate it against login forms. Tools like fail2ban slow it down by detecting "
                  "repeated failed attempts.",
        },
        "ornek": "hydra -l admin -P sifreler.txt ssh://192.168.1.20",
        "ilgili": ["sozluk_saldirisi", "hydra", "fail2ban"],
    },
    {
        "id": "sozluk_saldirisi",
        "baslik": {"tr": "Sözlük Saldırısı (Dictionary Attack)", "en": "Dictionary Attack"},
        "kisa": {"tr": "Rastgele deneme yerine sık kullanılan şifrelerden oluşan bir liste kullanan saldırı türü.",
                 "en": "An attack that tries a list of commonly used passwords instead of every random combination."},
        "aciklama": {
            "tr": "Sözlük saldırısı, saf kaba kuvvetin aksine önceden hazırlanmış, gerçek kullanıcıların "
                  "sıkça seçtiği şifirelerden (\"123456\", \"sifre123\" gibi) oluşan bir liste kullanır; "
                  "bu da onu çok daha hızlı ve pratik kılar. john gibi araçlar, çalınmış şifre özetlerini "
                  "(hash) kırmak için bu listeleri kullanır.",
            "en": "Unlike pure brute force, a dictionary attack uses a prepared list of passwords real "
                  "users commonly choose -- \"123456\", \"password123\" -- making it far faster and more "
                  "practical. Tools like john use these lists to crack stolen password hashes.",
        },
        "ilgili": ["kaba_kuvvet", "john"],
    },
    {
        "id": "paket_koklama",
        "baslik": {"tr": "Paket Koklama (Packet Sniffing)", "en": "Packet Sniffing"},
        "kisa": {"tr": "Bir ağ üzerinden geçen veri paketlerini yakalayıp inceleme işlemi.",
                 "en": "Capturing and inspecting data packets as they travel over a network."},
        "aciklama": {
            "tr": "Paket koklama; ağ yöneticilerinin sorun gidermesine yardımcı olabileceği gibi, "
                  "şifrelenmemiş trafikteki şifreleri ya da hassas verileri açığa çıkarmak için kötüye de "
                  "kullanılabilir. CarotOS Panel'deki tcpdump ve tshark (Wireshark'ın komut satırı "
                  "sürümü) bu işi görür.",
            "en": "Packet sniffing can help network administrators troubleshoot, but it can also be "
                  "abused to expose passwords or sensitive data in unencrypted traffic. tcpdump and "
                  "tshark (Wireshark's command-line form) in CarotOS Panel do this job.",
        },
        "ilgili": ["tcpdump", "wireshark_tshark", "mitm"],
    },
    {
        "id": "mitm",
        "baslik": {"tr": "Ortadaki Adam Saldırısı (MITM)", "en": "Man-in-the-Middle (MITM)"},
        "kisa": {"tr": "Saldırganın iki taraf arasındaki iletişimi gizlice dinlediği ya da değiştirdiği saldırı.",
                 "en": "An attack where someone secretly intercepts or alters communication between two parties."},
        "aciklama": {
            "tr": "Bir MITM saldırısında saldırgan, iki tarafın da haberi olmadan aralarına girer ve "
                  "trafiği okuyabilir hatta değiştirebilir -- örneğin açık bir Wi-Fi ağında. HTTPS/TLS "
                  "şifrelemesi, trafiği okunamaz hâle getirerek bu saldırıyı büyük ölçüde etkisiz "
                  "kılar.",
            "en": "In a MITM attack, an attacker inserts themselves between two parties without either "
                  "noticing, able to read or even alter the traffic -- on an open Wi-Fi network, for "
                  "example. HTTPS/TLS encryption largely neutralizes this attack by making the traffic "
                  "unreadable.",
        },
        "ilgili": ["paket_koklama", "ssl_tls", "sahtecilik"],
    },
    {
        "id": "sahtecilik",
        "baslik": {"tr": "Sahtecilik (Spoofing)", "en": "Spoofing"},
        "kisa": {"tr": "Bir kaynağı olduğundan farklı göstererek güven kazanma tekniği.",
                 "en": "Disguising a source as something it's not, in order to gain trust."},
        "aciklama": {
            "tr": "Sahtecilik; bir e-postanın gönderen adresini (e-posta sahteciliği), bir cihazın IP "
                  "adresini (IP sahteciliği) ya da MAC adresini taklit ederek karşı tarafı kandırmayı "
                  "amaçlar. Kimlik avı saldırılarının çoğu, bir çeşit sahtecilikle başlar.",
            "en": "Spoofing aims to deceive the other party by faking an email's sender address (email "
                  "spoofing), a device's IP address (IP spoofing), or its MAC address. Most phishing "
                  "attacks start with some form of spoofing.",
        },
        "ilgili": ["mitm", "kimlik_avi"],
    },
    {
        "id": "rootkit",
        "baslik": {"tr": "Rootkit", "en": "Rootkit"},
        "kisa": {"tr": "Kendini ve varlığını sistemden gizleyerek kalıcı, yetkili erişim sağlayan zararlı yazılım türü.",
                 "en": "A type of malware that hides itself and its activity while keeping persistent, privileged access."},
        "aciklama": {
            "tr": "Rootkit, genellikle çekirdek seviyesinde çalışarak kendi süreçlerini, dosyalarını ve ağ "
                  "bağlantılarını normal sistem araçlarından (hatta bazı antivirüs yazılımlarından) "
                  "gizler. Bu derin gizlenme becerisi onu tespit etmeyi ve temizlemeyi özellikle zor "
                  "kılar; çoğu zaman sistemi sıfırdan kurmak en güvenli çözümdür.",
            "en": "A rootkit typically operates at the kernel level, hiding its own processes, files and "
                  "network connections from normal system tools -- sometimes even from antivirus "
                  "software. This deep concealment makes it especially hard to detect and clean; "
                  "reinstalling the system from scratch is often the safest fix.",
        },
        "ilgili": ["arka_kapi", "zararli_yazilim", "yetki_yukseltme"],
    },
    {
        "id": "truva_ati",
        "baslik": {"tr": "Truva Atı (Trojan)", "en": "Trojan"},
        "kisa": {"tr": "Yararlı bir program gibi görünüp gizlice zararlı işler yapan yazılım.",
                 "en": "Software that looks like a useful program while secretly doing something harmful."},
        "aciklama": {
            "tr": "Adını Truva Savaşı'ndaki tahta attan alan bu zararlı yazılım türü, kendini bir oyun, "
                  "araç ya da güncelleme gibi tanıtarak kullanıcıyı kendi isteğiyle çalıştırmaya ikna "
                  "eder. Solucanların aksine kendi kendine yayılmaz; yayılması kullanıcının onu "
                  "paylaşmasına ya da indirmesine bağlıdır.",
            "en": "Named after the wooden horse of the Trojan War, this type of malware disguises itself "
                  "as a game, tool or update to trick the user into running it voluntarily. Unlike a "
                  "worm, it doesn't spread on its own -- its spread depends on people sharing or "
                  "downloading it.",
        },
        "ilgili": ["zararli_yazilim", "arka_kapi"],
    },
    {
        "id": "keylogger",
        "baslik": {"tr": "Tuş Kaydedici (Keylogger)", "en": "Keylogger"},
        "kisa": {"tr": "Kullanıcının bastığı her tuşu sessizce kaydeden casus yazılım türü.",
                 "en": "Spyware that silently records every key a user presses."},
        "aciklama": {
            "tr": "Bir tuş kaydedici, yazılan şifreleri, kart numaralarını ve mesajları yakalayıp genellikle "
                  "uzaktaki bir saldırgana gönderir. Yazılım tabanlı olabileceği gibi, fiziksel bir "
                  "donanım olarak klavye ile bilgisayar arasına da takılabilir.",
            "en": "A keylogger captures typed passwords, card numbers and messages, usually sending them "
                  "off to a remote attacker. It can be software-based, or it can be a physical hardware "
                  "device plugged in between the keyboard and the computer.",
        },
        "ilgili": ["zararli_yazilim", "kimlik_avi"],
    },
    {
        "id": "zafiyet_taramasi",
        "baslik": {"tr": "Zafiyet Taraması", "en": "Vulnerability Scanning"},
        "kisa": {"tr": "Bir sistemdeki bilinen zafiyetleri otomatik araçlarla sistematik biçimde arama süreci.",
                 "en": "Systematically searching a system for known vulnerabilities using automated tools."},
        "aciklama": {
            "tr": "Zafiyet taraması, nikto'nun bir web sunucusunu taraması ya da nmap'in bir ağdaki açık "
                  "portları ve servisleri listelemesi gibi, elle bir saldırı denemeden önce sistemin genel "
                  "resmini çıkarır. Düzenli yapıldığında, saldırganlar fark etmeden zayıf noktaları "
                  "kapatma fırsatı verir.",
            "en": "Vulnerability scanning -- nikto scanning a web server, or nmap listing the open ports "
                  "and services on a network -- builds a picture of a system before any manual attack is "
                  "attempted. Done regularly, it gives defenders the chance to close weak points before "
                  "attackers find them.",
        },
        "ilgili": ["nmap", "nikto", "cve"],
    },
    {
        "id": "nmap",
        "baslik": {"tr": "nmap", "en": "nmap"},
        "kisa": {"tr": "Bir ağdaki cihazları, açık portları ve çalışan servisleri keşfeden tarama aracı.",
                 "en": "The scanning tool that discovers devices, open ports and running services on a network."},
        "aciklama": {
            "tr": "nmap (Network Mapper), bir ağ aralığına ya da tek bir hedefe çeşitli tarama teknikleri "
                  "uygulayarak hangi cihazların ayakta olduğunu, hangi portların açık olduğunu ve hatta "
                  "hangi işletim sistemi/servis sürümünün çalıştığını tahmin eder. CarotOS Güvenlik "
                  "Paneli'ndeki en temel keşif aracıdır; CarotOS Former'da adım adım anlatımı bulunur.",
            "en": "nmap (Network Mapper) runs various scanning techniques against a network range or a "
                  "single target to figure out which devices are up, which ports are open, and even "
                  "guess the operating system or service version running. It's the most fundamental "
                  "discovery tool in CarotOS Security Panel, with a step-by-step walkthrough in CarotOS "
                  "Former.",
        },
        "ornek": "sudo nmap -sV 192.168.1.0/24",
        "ilgili": ["port", "zafiyet_taramasi", "pentest"],
    },
    {
        "id": "tcpdump",
        "baslik": {"tr": "tcpdump", "en": "tcpdump"},
        "kisa": {"tr": "Ağ trafiğini komut satırından yakalayıp gösteren klasik paket analiz aracı.",
                 "en": "The classic command-line tool that captures and displays network traffic."},
        "aciklama": {
            "tr": "tcpdump, bir ağ arayüzünden geçen paketleri gerçek zamanlı yakalar ve filtrelerle "
                  "(belirli bir port, IP ya da protokol) inceler; sonuçlar daha ayrıntılı analiz için bir "
                  "dosyaya (.pcap) kaydedilip Wireshark gibi araçlarda da açılabilir.",
            "en": "tcpdump captures packets passing through a network interface in real time and lets "
                  "you filter them -- by a specific port, IP or protocol. Results can be saved to a "
                  "file (.pcap) for deeper analysis, or opened later in a tool like Wireshark.",
        },
        "ornek": "sudo tcpdump -i eth0 port 80",
        "ilgili": ["paket_koklama", "wireshark_tshark"],
    },
    {
        "id": "wireshark_tshark",
        "baslik": {"tr": "Wireshark / tshark", "en": "Wireshark / tshark"},
        "kisa": {"tr": "Yakalanan ağ trafiğini katman katman, ayrıntılı biçimde inceleyen analiz aracı.",
                 "en": "The analysis tool that inspects captured network traffic layer by layer, in detail."},
        "aciklama": {
            "tr": "Wireshark, yakalanan paketleri protokol katmanlarına ayırarak gösteren grafik arayüzlü "
                  "bir analiz aracıdır; tshark ise aynı motorun komut satırı sürümüdür ve CarotOS "
                  "Güvenlik Paneli'nde bu şekilde yer alır. İkisi de bir ağ sorununu ya da şüpheli "
                  "trafiği paket düzeyinde incelemek için kullanılır.",
            "en": "Wireshark is a graphical analysis tool that breaks captured packets down by protocol "
                  "layer; tshark is the command-line version of the same engine, and that's the form "
                  "included in CarotOS Security Panel. Both are used to examine a network problem or "
                  "suspicious traffic at the packet level.",
        },
        "ilgili": ["tcpdump", "paket_koklama"],
    },
    {
        "id": "aircrack_ng",
        "baslik": {"tr": "aircrack-ng", "en": "aircrack-ng"},
        "kisa": {"tr": "Kablosuz ağların güvenliğini denetlemek için kullanılan araç paketi.",
                 "en": "A suite of tools used to audit the security of wireless networks."},
        "aciklama": {
            "tr": "aircrack-ng; Wi-Fi trafiğini yakalama, erişim noktalarını izleme ve WEP/WPA/WPA2 "
                  "şifrelerini -- özellikle zayıf şifreler karşısında -- kırma gibi işlevleri bir araya "
                  "getiren bir araç takımıdır. Kablosuz ağ güvenliği eğitiminde ve yetkili denetimlerde "
                  "kullanılır; izinsiz bir ağda kullanmak yasa dışıdır.",
            "en": "aircrack-ng bundles tools for capturing Wi-Fi traffic, monitoring access points, and "
                  "cracking WEP/WPA/WPA2 passwords -- especially weak ones. It's used in wireless "
                  "security training and authorized audits; using it against a network without "
                  "permission is illegal.",
        },
        "ilgili": ["kaba_kuvvet", "pentest"],
    },
    {
        "id": "nikto",
        "baslik": {"tr": "nikto", "en": "nikto"},
        "kisa": {"tr": "Web sunucularını bilinen zafiyetlere ve yanlış yapılandırmalara karşı tarayan araç.",
                 "en": "A tool that scans web servers for known vulnerabilities and misconfigurations."},
        "aciklama": {
            "tr": "nikto, bir web sunucusuna binlerce bilinen tehlikeli dosyayı, eski yazılım sürümünü ve "
                  "yanlış yapılandırmayı kontrol eden istekler gönderir ve bulduklarını genellikle CVE "
                  "numaralarıyla raporlar. Hızlı bir ilk güvenlik taraması için yaygın kullanılır.",
            "en": "nikto sends a web server thousands of requests checking for known dangerous files, "
                  "outdated software versions and misconfigurations, usually reporting what it finds "
                  "with CVE numbers. It's commonly used for a quick first security pass.",
        },
        "ornek": "nikto -h http://192.168.1.20",
        "ilgili": ["zafiyet_taramasi", "cve", "sqlmap"],
    },
    {
        "id": "sqlmap",
        "baslik": {"tr": "sqlmap", "en": "sqlmap"},
        "kisa": {"tr": "Web uygulamalarındaki SQL enjeksiyonu zafiyetlerini otomatik tespit eden ve test eden araç.",
                 "en": "The tool that automatically detects and tests SQL injection vulnerabilities in web applications."},
        "aciklama": {
            "tr": "sqlmap, bir web uygulamasının veritabanıyla konuştuğu noktalara özel olarak "
                  "hazırlanmış girdiler göndererek SQL enjeksiyonuna açık olup olmadığını test eder; "
                  "açık bulursa veritabanı yapısını, tablolarını ve hatta verilerini çıkarabilir. Yetkisiz "
                  "sistemlerde kullanmak yasa dışıdır.",
            "en": "sqlmap sends specially crafted input to the points where a web application talks to "
                  "its database, testing whether it's open to SQL injection; if it finds a hole, it can "
                  "extract the database structure, tables and even the data itself. Using it against "
                  "unauthorized systems is illegal.",
        },
        "ilgili": ["nikto", "pentest"],
    },
    {
        "id": "john",
        "baslik": {"tr": "John the Ripper", "en": "John the Ripper"},
        "kisa": {"tr": "Şifre özetlerini (hash) kırmak için kullanılan klasik şifre kırma aracı.",
                 "en": "The classic password-cracking tool used to break password hashes."},
        "aciklama": {
            "tr": "John the Ripper (kısaca \"john\"), elde edilmiş şifre özetlerine hem sözlük saldırısı "
                  "hem de kaba kuvvet yöntemlerini uygulayarak orijinal şifreyi bulmaya çalışır. Sistem "
                  "yöneticileri, kendi kullanıcılarının ne kadar zayıf şifre kullandığını denetlemek için "
                  "de kullanabilir.",
            "en": "John the Ripper (\"john\" for short) applies both dictionary and brute-force methods "
                  "against captured password hashes to recover the original password. System "
                  "administrators can also use it to audit how weak their own users' passwords are.",
        },
        "ilgili": ["sozluk_saldirisi", "kaba_kuvvet"],
    },
    {
        "id": "hydra",
        "baslik": {"tr": "Hydra", "en": "Hydra"},
        "kisa": {"tr": "SSH, FTP gibi giriş formlarına karşı hızlı, çok iş parçacıklı kaba kuvvet saldırısı yapan araç.",
                 "en": "A fast, multi-threaded tool for brute-forcing login forms such as SSH or FTP."},
        "aciklama": {
            "tr": "Hydra, bir kullanıcı adı (ya da liste) ile bir şifre listesini SSH, FTP, bir web giriş "
                  "formu gibi birçok farklı protokole karşı hızla dener; aynı anda birçok denemeyi paralel "
                  "yürüterek süreci hızlandırır. Zayıf şifrelerin ne kadar çabuk kırılabileceğini "
                  "göstermesi açısından farkındalık oluşturan bir araçtır.",
            "en": "Hydra rapidly tries a username (or list) against a password list across many "
                  "protocols -- SSH, FTP, a web login form -- running many attempts in parallel to speed "
                  "things up. It's a useful awareness tool for showing just how quickly a weak password "
                  "can fall.",
        },
        "ilgili": ["kaba_kuvvet", "ssh"],
    },
    {
        "id": "fail2ban",
        "baslik": {"tr": "fail2ban", "en": "fail2ban"},
        "kisa": {"tr": "Başarısız giriş denemelerini izleyip tekrarlayan IP adreslerini otomatik engelleyen koruma aracı.",
                 "en": "A protection tool that watches failed login attempts and automatically bans repeat-offending IP addresses."},
        "aciklama": {
            "tr": "fail2ban, sistem günlüklerini (örneğin SSH giriş denemelerini) izler ve belirlenen "
                  "sürede çok sayıda başarısız deneme yapan bir IP adresini, güvenlik duvarı kuralı "
                  "ekleyerek geçici olarak engeller. Bu, kaba kuvvet saldırılarına karşı basit ama etkili "
                  "bir savunmadır.",
            "en": "fail2ban watches system logs -- SSH login attempts, say -- and temporarily bans an IP "
                  "address that makes too many failed attempts in a given window, by adding a firewall "
                  "rule. It's a simple but effective defense against brute-force attacks.",
        },
        "ilgili": ["ids_ips", "kaba_kuvvet", "guvenlik_duvari"],
    },
    {
        "id": "ufw",
        "baslik": {"tr": "UFW", "en": "UFW"},
        "kisa": {"tr": "Linux'un karmaşık güvenlik duvarı kurallarını basit komutlarla yönetilebilir kılan araç.",
                 "en": "The tool that makes Linux's complex firewall rules manageable with simple commands."},
        "aciklama": {
            "tr": "UFW (Uncomplicated Firewall), çekirdeğin netfilter/iptables sistemine basit bir ön yüz "
                  "sunar; \"ufw allow 22\" gibi tek bir komutla port açıp kapatmak mümkündür. CarotOS "
                  "Güvenlik Paneli, UFW kurallarını görsel bir arayüzle sunarak komut satırına gerek "
                  "bırakmaz.",
            "en": "UFW (Uncomplicated Firewall) provides a simple front end to the kernel's "
                  "netfilter/iptables system; a single command like \"ufw allow 22\" opens or closes a "
                  "port. CarotOS Security Panel presents UFW rules through a visual interface so no "
                  "command line is needed.",
        },
        "ornek": "sudo ufw allow 22/tcp",
        "ilgili": ["guvenlik_duvari", "port"],
    },
]
