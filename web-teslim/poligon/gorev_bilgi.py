"""
CarotOS Poligon -- görev bilgi metinleri.

Öğretmen uygulamasındaki görev listesinde her görevin başındaki bilgi
düğmesi bu metinleri gösterir. Her görev için üç alan vardır:

  amac     : görevin ne olduğu ve neden önemli olduğu
  kazanim  : öğrencinin görevde ne öğrendiği (araç ve kavramlar)
  kullanim : gerçek çalışmada nerede karşılaşıldığı

Yeni bir görev eklendiğinde buraya da girilmelidir; tests/test_poligon_gorev_bilgi.py
gorevler/ klasöründeki her görevin burada iki dilde tanımlı olduğunu denetler.
"""

from __future__ import annotations

BILGI: dict = {
    "nmap-01": {
        "tr": {
            "amac": "Bir makinede dışarıya açık hangi hizmetlerin çalıştığını bulmak, saldırı yüzeyini belirlemenin ilk adımıdır. Öğrenci, yerel makinedeki port aralığını tarayarak standart dışı bir portta çalışan hizmeti bulur.",
            "kazanim": "nmap ile port aralığı taraması; açık, kapalı ve filtreli port ayrımı; olağan dışı hizmetin fark edilmesi.",
            "kullanim": "Sızma testlerinin keşif aşaması; kendi sunucularında gereksiz açık kalmış hizmetlerin denetimi.",
        },
        "en": {
            "amac": "Finding which services a machine exposes is the first step in mapping its attack surface. The student scans a port range on the local machine and finds the service running on a non-standard port.",
            "kazanim": "Port range scanning with nmap; telling open, closed and filtered ports apart; spotting an unusual service.",
            "kullanim": "The reconnaissance phase of penetration tests; auditing one's own servers for services left open without need.",
        },
    },
    "banner-01": {
        "tr": {
            "amac": "Bir servisin sürüm bilgisi, o sürümdeki bilinen güvenlik açıklarının araştırılabilmesi için gereklidir. Birden fazla portta çalışan servisler arasından belirli bir yazılımın sürümü bulunur.",
            "kazanim": "Servis başlığı (banner) okuma; nmap -sV ile sürüm tespiti; nc ile elle bağlanma.",
            "kullanim": "Yama durumu denetimi; envanterde eski sürüm yazılımların bulunması.",
        },
        "en": {
            "amac": "A service's version is needed to look up the vulnerabilities known for that version. The student identifies the version of one specific piece of software among several services on different ports.",
            "kazanim": "Reading service banners; version detection with nmap -sV; connecting manually with nc.",
            "kullanim": "Patch-level audits; finding outdated software in an inventory.",
        },
    },
    "hydra-01": {
        "tr": {
            "amac": "Zayıf parola, kimlik doğrulama saldırılarında en sık istismar edilen zafiyettir. Öğrenci, bir giriş servisine karşı yaygın parola listesini deneyerek doğru parolayı bulur.",
            "kazanim": "Sözlük saldırısının mantığı; hydra kullanımı; uzun ve benzersiz parolanın neden gerektiği.",
            "kullanim": "Parola politikasının sınanması; SSH ve FTP gibi servislere yönelik parola denemelerinin tanınması.",
        },
        "en": {
            "amac": "Weak passwords are the most commonly exploited flaw in authentication attacks. The student tries a common password list against a login service until the right one is found.",
            "kazanim": "How a dictionary attack works; using hydra; why passwords must be long and unique.",
            "kullanim": "Testing a password policy; recognising password guessing against services such as SSH and FTP.",
        },
    },
    "john-01": {
        "tr": {
            "amac": "Sistemler parolayı düz metin olarak değil özet (hash) olarak saklar; ancak zayıf bir parolanın özeti kısa sürede çözülebilir. Öğrenci, verilen özetten parolayı sözlük saldırısıyla bulur.",
            "kazanim": "Hash kavramı; john ile sözlük saldırısı; hash türüne göre çözme hızının değişmesi.",
            "kullanim": "Sızan parola veritabanlarının etkisini anlamak; parola saklama yönteminin seçimi (bcrypt, argon2 gibi yavaş algoritmalar).",
        },
        "en": {
            "amac": "Systems store passwords as hashes rather than plain text, but the hash of a weak password can be recovered quickly. The student recovers the password from a given hash with a dictionary attack.",
            "kazanim": "The concept of a hash; dictionary attacks with john; how cracking speed depends on the hash type.",
            "kullanim": "Understanding the impact of leaked password databases; choosing a password storage method (slow algorithms such as bcrypt or argon2).",
        },
    },
    "hash-02": {
        "tr": {
            "amac": "Bir özetin hangi algoritmayla üretildiği bilinmeden doğru kırma aracı ve modu seçilemez. Öğrenci, dosyadaki parola özetinin türünü uzunluğuna ve biçimine bakarak belirler.",
            "kazanim": "MD5, SHA-1, SHA-256, bcrypt gibi özetlerin uzunluk ve önek özellikleri; hashid ve benzeri araçlar.",
            "kullanim": "Olay incelemesinde ele geçen özetlerin sınıflandırılması; kırma aracına doğru modun verilmesi.",
        },
        "en": {
            "amac": "Without knowing which algorithm produced a hash, the right cracking tool and mode cannot be chosen. The student determines the type of a password hash from its length and format.",
            "kazanim": "Length and prefix characteristics of MD5, SHA-1, SHA-256 and bcrypt hashes; tools such as hashid.",
            "kullanim": "Classifying hashes recovered during an incident investigation; selecting the right mode in a cracking tool.",
        },
    },
    "sqlmap-01": {
        "tr": {
            "amac": "Kullanıcı girdisi sorguya doğrudan eklendiğinde veritabanı yetkisiz biçimde okunabilir. Öğrenci, zafiyetli bir ürün sayfası üzerinden sayfada görünmeyen bir tabloyu çıkarır.",
            "kazanim": "SQL enjeksiyonunun mantığı; sqlmap ile tablo ve sütun listeleme, veri çıkarma.",
            "kullanim": "Web uygulaması güvenlik testleri; parametreli sorgu kullanımının neden zorunlu olduğu.",
        },
        "en": {
            "amac": "When user input is placed directly into a query, the database can be read without authorisation. The student extracts a table that the page never displays, through a vulnerable product page.",
            "kazanim": "How SQL injection works; listing tables and columns and extracting data with sqlmap.",
            "kullanim": "Web application security testing; why parameterised queries are mandatory.",
        },
    },
    "tshark-01": {
        "tr": {
            "amac": "Şifrelenmemiş protokollerde bilgi ağda düz metin olarak geçer. Öğrenci, yerel arayüzde geçen trafiği yakalayıp içindeki mesajı okur.",
            "kazanim": "tshark ile arayüz dinleme, port filtresi uygulama, paket içeriği okuma; düz metin protokollerin riski.",
            "kullanim": "Ağ sorunlarının teşhisi; şüpheli trafiğin incelenmesi; trafiğin neden TLS ile korunması gerektiği.",
        },
        "en": {
            "amac": "On unencrypted protocols the data crosses the network as plain text. The student captures traffic on the local interface and reads the message inside it.",
            "kazanim": "Listening on an interface with tshark, applying a port filter, reading packet contents; the risk of plain-text protocols.",
            "kullanim": "Diagnosing network problems; examining suspicious traffic; why traffic should be protected with TLS.",
        },
    },
    "web-01": {
        "tr": {
            "amac": "Web sitelerinde bağlantısı verilmemiş ama erişilebilir dizinler bulunabilir. Öğrenci, sitedeki gizli bölümü robots.txt, dizin taraması veya çerez ve başlık incelemesiyle bulur.",
            "kazanim": "curl ile istek gönderme ve yanıt başlıklarını okuma; robots.txt'in ifşa ettikleri; HTTP durum kodlarını (200, 403, 404) yorumlama.",
            "kullanim": "Web sızma testlerinde içerik keşfi; yöneticinin gizli sandığı yolların aslında erişilebilir olması.",
        },
        "en": {
            "amac": "Websites may contain directories that are not linked anywhere but are still reachable. The student finds the hidden section through robots.txt, directory brute-forcing, or by inspecting cookies and headers.",
            "kazanim": "Sending requests and reading response headers with curl; what robots.txt reveals; interpreting HTTP status codes (200, 403, 404).",
            "kullanim": "Content discovery in web penetration tests; paths an administrator believes are hidden but are in fact reachable.",
        },
    },
    "adli-01": {
        "tr": {
            "amac": "Dosya uzantısı, dosyanın gerçek türünü kanıtlamaz. Öğrenci, resim gibi görünen bir dosyanın gerçek türünü içeriğinden belirleyip içindeki veriye ulaşır.",
            "kazanim": "file komutu ve dosya imzaları (magic bytes); arşivleri açma; uzantıya güvenmemek.",
            "kullanim": "Adli bilişim; e-posta eki ve indirilen dosyaların zararlı yazılım açısından incelenmesi.",
        },
        "en": {
            "amac": "A file extension does not prove what a file really is. The student determines the true type of a file that looks like an image and reaches the data inside it.",
            "kazanim": "The file command and file signatures (magic bytes); unpacking archives; not trusting extensions.",
            "kullanim": "Digital forensics; inspecting e-mail attachments and downloaded files for malware.",
        },
    },
    "kodlama-01": {
        "tr": {
            "amac": "Veri çoğu zaman base64, hex, rot13 gibi kodlamalarla art arda sarılarak gizlenir. Bunlar şifreleme değildir, geri alınabilir. Öğrenci katmanları sırayla açar.",
            "kazanim": "Kodlama ile şifreleme arasındaki fark; base64, hex, base32, rot13, gzip gibi biçimlerin tanınması ve komut satırında çözülmesi.",
            "kullanim": "Zararlı betiklerdeki gizlemenin çözülmesi; günlüklerde kodlanmış şüpheli verinin okunması.",
        },
        "en": {
            "amac": "Data is often hidden by wrapping it in several encodings such as base64, hex or rot13. These are not encryption and can be reversed. The student unwraps the layers in order.",
            "kazanim": "The difference between encoding and encryption; recognising and decoding base64, hex, base32, rot13 and gzip on the command line.",
            "kullanim": "Deobfuscating malicious scripts; reading suspicious encoded data found in logs.",
        },
    },
    "kodlama-02": {
        "tr": {
            "amac": "Sezar şifresi, harfleri alfabede sabit sayıda kaydıran en eski yer değiştirme şifrelerinden biridir. Anahtar uzayı çok küçük olduğu için kolayca kırılır. Öğrenci şifreli mesajı çözer.",
            "kazanim": "tr komutuyla harf eşleme; deneme yoluyla anahtar bulma; klasik şifrelerin neden güvensiz olduğu.",
            "kullanim": "Kriptografiye giriş; modern şifrelemenin neden geniş bir anahtar uzayı gerektirdiği.",
        },
        "en": {
            "amac": "The Caesar cipher is one of the oldest substitution ciphers; it shifts each letter by a fixed number of places. Its key space is tiny, so it is easily broken. The student decrypts the message.",
            "kazanim": "Mapping letters with the tr command; finding the key by trial; why classical ciphers are insecure.",
            "kullanim": "Introduction to cryptography; why modern encryption needs a large key space.",
        },
    },
    "loganaliz-01": {
        "tr": {
            "amac": "SSH günlüklerinde çok sayıda başarısız giriş kaydı, o adresin parola denediğini gösterir. Öğrenci, günlükten saldırının kaynağı olan IP adresini bulur.",
            "kazanim": "grep ile satır süzme; cut, sort ve uniq -c ile sayma ve sıralama; günlük satırının yapısını okuma.",
            "kullanim": "Sunucu günlüklerinin düzenli denetimi; engellenecek adres listesinin çıkarılması.",
        },
        "en": {
            "amac": "Many failed-login entries in an SSH log show that an address is guessing passwords. The student finds the IP address that is the source of the attack.",
            "kazanim": "Filtering lines with grep; counting and sorting with cut, sort and uniq -c; reading the structure of a log line.",
            "kullanim": "Routine review of server logs; building a list of addresses to block.",
        },
    },
    "loganaliz-02": {
        "tr": {
            "amac": "Bir saldırının asıl önemi başarılı olup olmadığındadır. Öğrenci, saldırgan IP'nin hangi hesaba girdiğini bulur ve olayın boyutunu belirler.",
            "kazanim": "Başarısız ve başarılı girişleri ayırma; iki kaydı aynı IP üzerinden ilişkilendirme.",
            "kullanim": "Olay müdahalesi; hangi hesabın parolasının değiştirilmesi gerektiğine karar verme.",
        },
        "en": {
            "amac": "What matters most about an attack is whether it succeeded. The student finds which account the attacking IP logged in to and determines the scope of the incident.",
            "kazanim": "Separating failed and successful logins; correlating two kinds of records by IP address.",
            "kullanim": "Incident response; deciding which account's password must be changed.",
        },
    },
    "loganaliz-03": {
        "tr": {
            "amac": "Tek bir kaynaktan gelen çok sayıda 404 yanıtı, sitede olmayan sayfaların tek tek denendiğini gösterir. Öğrenci, erişim günlüğünden taramayı yapan adresi bulur.",
            "kazanim": "awk ile sütun ayıklama ve koşullu süzme (HTTP durum kodu); erişim günlüğü biçimi.",
            "kullanim": "Web sunucusu izleme; tarama yapan adreslerin engellenmesi.",
        },
        "en": {
            "amac": "Many 404 responses to a single source show that pages which do not exist are being tried one by one. The student finds the address performing the scan from the access log.",
            "kazanim": "Extracting columns and filtering on a condition (HTTP status code) with awk; the access log format.",
            "kullanim": "Web server monitoring; blocking addresses that scan the site.",
        },
    },
    "loganaliz-04": {
        "tr": {
            "amac": "Taramanın sonunda 200 yanıtı alan istek, saldırganın gerçekten bir şey bulduğunu gösterir. Öğrenci, taramayı yapan adresin eriştiği hassas yolu bulur.",
            "kazanim": "İki aşamalı analiz: önce kaynağı bulma, sonra o kaynağın başarılı isteklerini inceleme; awk ile birleşik koşul.",
            "kullanim": "Yedek dosyası ve yönetim paneli gibi açıkta kalmış kaynakların tespiti.",
        },
        "en": {
            "amac": "A request that receives a 200 response at the end of a scan shows the attacker actually found something. The student finds the sensitive path that the scanning address reached.",
            "kazanim": "Two-stage analysis: first identify the source, then examine that source's successful requests; combined conditions in awk.",
            "kullanim": "Detecting exposed resources such as backup files and admin panels.",
        },
    },
    "loganaliz-05": {
        "tr": {
            "amac": "Honeypot kayıtları, saldırganların hangi kullanıcı adlarını denediğini gösterir. Öğrenci, kayıt dosyasında en sık denenen kullanıcı adını bulur.",
            "kazanim": "CarotPot kayıt biçimini okuma; grep ve awk ile alan çıkarma ve sayma.",
            "kullanim": "Gerçek sistemlerde bu kullanıcı adlarının kapatılması; saldırgan davranışının profillenmesi.",
        },
        "en": {
            "amac": "Honeypot records show which usernames attackers try. The student finds the most frequently attempted username in the log file.",
            "kazanim": "Reading the CarotPot log format; extracting fields and counting with grep and awk.",
            "kullanim": "Disabling those usernames on real systems; profiling attacker behaviour.",
        },
    },
    "loganaliz-06": {
        "tr": {
            "amac": "Çok sayıda olay üretmek ile çok sayıda farklı hizmete dokunmak aynı şey değildir. Farklı hizmetleri yoklayan kaynak keşif yapıyordur. Öğrenci bu kaynağı ayırt eder.",
            "kazanim": "Her kaynak için benzersiz değerleri sayma (sort -u, awk dizisi); olay sayısı ile çeşitlilik ölçütünü ayırma.",
            "kullanim": "Port taraması ve keşif davranışının tespiti.",
        },
        "en": {
            "amac": "Producing many events is not the same as touching many different services. A source probing different services is doing reconnaissance. The student tells this source apart.",
            "kazanim": "Counting unique values per source (sort -u, awk arrays); distinguishing event count from variety.",
            "kullanim": "Detecting port scans and reconnaissance behaviour.",
        },
    },
    "carotpot-01": {
        "tr": {
            "amac": "Honeypot, saldırganı çekmek ve kayıt tutmak için kurulmuş sahte bir servistir. Öğrenci, kendi makinesinde ayrı çalışan bir tuzağı bulur, ona giriş denemeleri yapar ve kaydın oluştuğunu doğrular. Tuzak yalnızca bu bilgisayarın içinde çalışır, ağa açılmaz.",
            "kazanim": "nmap ile tuzak portlarını bulma; ftp, telnet ve http hizmetlerine bağlanma; CarotPot kaydını okuma.",
            "kullanim": "Ağda saldırı girişimlerinin erken tespiti; saldırgan davranışının güvenli bir ortamda gözlenmesi.",
        },
        "en": {
            "amac": "A honeypot is a decoy service set up to attract attackers and record what they do. The student finds a separate trap running on their own machine, attempts logins against it, and confirms that the attempts were recorded. The trap runs only inside this computer and is not exposed to the network.",
            "kazanim": "Finding the trap ports with nmap; connecting to ftp, telnet and http services; reading CarotPot records.",
            "kullanim": "Early detection of attack attempts on a network; observing attacker behaviour in a safe environment.",
        },
    },
    "carotpot-02": {
        "tr": {
            "amac": "Honeypot'un değeri, topladığı kayıtların okunabilmesinde yatar. Öğrenci, tuzağın raporunu açıp en çok olay üreten kaynağı belirler.",
            "kazanim": "carotpot report çıktısını yorumlama; kaynak bazında olay sayımı.",
            "kullanim": "Günlük tehdit raporlaması; öncelikle engellenecek adreslerin belirlenmesi.",
        },
        "en": {
            "amac": "A honeypot is only useful if its records can be read. The student opens the trap's report and identifies the source that generated the most events.",
            "kazanim": "Interpreting the carotpot report output; counting events per source.",
            "kullanim": "Daily threat reporting; deciding which addresses to block first.",
        },
    },
    "ufw-01": {
        "tr": {
            "amac": "Saldırı görevlerinde bulunan açıklar savunma tarafında kapatılır. Öğrenci, korumasız bir portu güvenlik duvarı kuralıyla erişime kapatır. Bu görev yönetici (sudo) yetkisi gerektirir.",
            "kazanim": "ufw ile kural ekleme ve listeleme; izin verme ve engelleme arasındaki fark; kuralın gerçekten uygulandığının doğrulanması.",
            "kullanim": "Sunucu sıkılaştırma; yalnızca gerekli portların açık bırakılması.",
        },
        "en": {
            "amac": "Weaknesses found in the attack exercises are closed on the defence side. The student closes an unprotected port with a firewall rule. This task requires administrator (sudo) rights.",
            "kazanim": "Adding and listing rules with ufw; the difference between allow and deny; verifying that the rule is actually in effect.",
            "kullanim": "Server hardening; leaving only the necessary ports open.",
        },
    },
    "fail2ban-01": {
        "tr": {
            "amac": "fail2ban, tekrarlanan başarısız girişleri günlükten izleyip kaynağı geçici olarak engeller. Öğrenci kural yazmaz; servisin durumunu okuyarak çalıştığını doğrular. Bu görev yönetici (sudo) yetkisi gerektirir.",
            "kazanim": "fail2ban-client status ile jail durumunu okuma; engellenen adresleri ve başarısız deneme sayılarını yorumlama.",
            "kullanim": "SSH parola denemelerine karşı otomatik savunma.",
        },
        "en": {
            "amac": "fail2ban watches the logs for repeated failed logins and temporarily bans the source. The student writes no rules; the student reads the service status and confirms that it is working. This task requires administrator (sudo) rights.",
            "kazanim": "Reading jail status with fail2ban-client status; interpreting banned addresses and failed-attempt counts.",
            "kullanim": "Automatic defence against SSH password guessing.",
        },
    },
}

ALAN_ETIKETLERI = {
    "tr": {"amac": "Amaç", "kazanim": "Kazanım", "kullanim": "Kullanım alanı"},
    "en": {"amac": "Purpose", "kazanim": "What it teaches", "kullanim": "Where it is used"},
}


CESITLILIK_ETIKETI = {"tr": "Soru çeşitliliği", "en": "Question variety"}


def cesitlilik_getir(gorev_id: str, dil: str) -> str:
    """Görevde kaç farklı soru olduğunu ve bunların sınıfa nasıl dağıtıldığını anlatır."""
    import varyantlar
    n = varyantlar.gorev_varyant_sayisi(gorev_id)
    if n > 1:
        if dil == "en":
            return (f"{n} different questions. Each time you assign the task the computer picks "
                    f"one that has not come up yet; the whole class gets the same question, "
                    f"while each student's data (IPs, files, flags) is generated separately.")
        return (f"{n} farklı soru. Görevi her atadığınızda bilgisayar henüz çıkmamış birini seçer; "
                f"sınıfın tamamı aynı soruyu çözer, her öğrencinin verisi (IP, dosya, bayrak) "
                f"ayrı üretilir.")
    if dil == "en":
        return ("A single question type, the same for the whole class; each student's data "
                "(IPs, files, flags) is generated separately.")
    return ("Tek soru türü, sınıfta herkes için aynı; her öğrencinin verisi (IP, dosya, bayrak) "
            "ayrı üretilir.")


def bilgi_getir(gorev_id: str, dil: str) -> dict | None:
    """Görevin bilgi metnini döner; tanımsızsa None."""
    kayit = BILGI.get(gorev_id)
    if not kayit:
        return None
    return kayit.get(dil) or kayit.get("tr")
