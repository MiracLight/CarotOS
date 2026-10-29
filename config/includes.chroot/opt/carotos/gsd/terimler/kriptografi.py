# -*- coding: utf-8 -*-
"""GSD -- Kriptografi terimleri."""

TERIMLER = [
    {
        "id": "sifreleme",
        "baslik": {"tr": "Şifreleme (Encryption)", "en": "Encryption"},
        "kisa": {"tr": "Veriyi, yalnızca doğru anahtara sahip olanın okuyabileceği hâle dönüştürme işlemi.",
                 "en": "Transforming data so that only someone with the right key can read it."},
        "aciklama": {
            "tr": "Şifreleme, düz metni (plaintext) bir matematiksel algoritma ve bir anahtar kullanarak "
                  "anlaşılmaz bir biçime (ciphertext) çevirir; doğru anahtar olmadan bu veriyi geri "
                  "çözmek pratikte imkânsızdır. Hem aktarım hâlindeki veriyi (HTTPS gibi) hem de diskte "
                  "duran veriyi korumak için kullanılır.",
            "en": "Encryption turns plaintext into an unreadable form (ciphertext) using a mathematical "
                  "algorithm and a key; without the right key, reversing it is practically impossible. "
                  "It protects both data in transit (like HTTPS) and data at rest on disk.",
        },
        "ilgili": ["simetrik_sifreleme", "asimetrik_sifreleme"],
    },
    {
        "id": "simetrik_sifreleme",
        "baslik": {"tr": "Simetrik Şifreleme", "en": "Symmetric Encryption"},
        "kisa": {"tr": "Şifreleme ve çözme için aynı tek anahtarın kullanıldığı yöntem.",
                 "en": "Encryption where the same single key is used to both lock and unlock the data."},
        "aciklama": {
            "tr": "Simetrik şifrelemede gönderen ve alan aynı gizli anahtarı paylaşır; AES bunun en "
                  "yaygın örneğidir. Hızlıdır ve büyük veri hacimleri için uygundur, ama anahtarı "
                  "karşı tarafa güvenle nasıl ulaştıracağınız ayrı bir problemdir.",
            "en": "In symmetric encryption, sender and receiver share the same secret key; AES is the "
                  "most common example. It's fast and well suited to large volumes of data, but safely "
                  "getting that key to the other party in the first place is a separate problem.",
        },
        "ilgili": ["aes", "asimetrik_sifreleme", "sifreleme"],
    },
    {
        "id": "asimetrik_sifreleme",
        "baslik": {"tr": "Asimetrik Şifreleme (Açık Anahtarlı)", "en": "Asymmetric (Public-Key) Encryption"},
        "kisa": {"tr": "Biri herkese açık, diğeri gizli olan iki farklı anahtar kullanan şifreleme yöntemi.",
                 "en": "Encryption that uses two different keys: one public, one kept secret."},
        "aciklama": {
            "tr": "Asimetrik şifrelemede açık anahtarla şifrelenen veri yalnızca eşleşen özel anahtarla "
                  "çözülebilir; bu sayede iki taraf önceden hiç gizli bilgi paylaşmadan güvenle "
                  "haberleşebilir. RSA en bilinen örneğidir; SSH ve HTTPS'in anahtar değişiminde "
                  "temelini oluşturur. Simetrik şifrelemeye göre çok daha yavaştır, bu yüzden genellikle "
                  "yalnızca bir simetrik anahtarı güvenle iletmek için kullanılır.",
            "en": "In asymmetric encryption, data locked with the public key can only be opened with the "
                  "matching private key, letting two parties communicate securely without ever having "
                  "shared a secret beforehand. RSA is the best-known example and underlies key exchange "
                  "in SSH and HTTPS. It's much slower than symmetric encryption, so it's usually used "
                  "just to safely deliver a symmetric key.",
        },
        "ilgili": ["acik_anahtar", "ozel_anahtar", "rsa"],
    },
    {
        "id": "acik_anahtar",
        "baslik": {"tr": "Açık Anahtar (Public Key)", "en": "Public Key"},
        "kisa": {"tr": "Asimetrik şifrelemede herkesle güvenle paylaşılabilen anahtar.",
                 "en": "The key in asymmetric encryption that can safely be shared with anyone."},
        "aciklama": {
            "tr": "Açık anahtar, eşleştiği özel anahtar olmadan tek başına veriyi çözmeye yaramaz; bu "
                  "yüzden herkese açık paylaşılabilir -- örneğin bir SSH sunucusuna bağlanırken ya da "
                  "e-posta imzalarken. Anahtar çifti matematiksel olarak birbirine bağlıdır ama birinden "
                  "diğerini pratikte çıkarmak imkânsızdır.",
            "en": "A public key is useless for decrypting data on its own without its matching private "
                  "key, which is why it can be shared openly -- when connecting to an SSH server, say, "
                  "or signing an email. The key pair is mathematically linked, but deriving one from the "
                  "other is practically impossible.",
        },
        "ilgili": ["ozel_anahtar", "asimetrik_sifreleme", "ssh"],
    },
    {
        "id": "ozel_anahtar",
        "baslik": {"tr": "Özel Anahtar (Private Key)", "en": "Private Key"},
        "kisa": {"tr": "Asimetrik şifrelemede yalnızca sahibinde kalması gereken gizli anahtar.",
                 "en": "The secret half of an asymmetric key pair that must never leave its owner."},
        "aciklama": {
            "tr": "Özel anahtar sızarsa onunla eşleşen açık anahtarla kurulan tüm güvenin ortadan kalktığı "
                  "anlamına gelir -- bu yüzden genellikle bir şifreyle korunur ve diskte açık metin "
                  "olarak tutulmaz. SSH ile sunucuya bağlanırken ya da bir sayısal imza oluştururken "
                  "kullanılan anahtar budur.",
            "en": "If a private key leaks, all the trust built on its matching public key collapses -- "
                  "which is why it's usually protected with a passphrase and never stored in plaintext "
                  "on disk. It's the key used when connecting to a server over SSH or creating a digital "
                  "signature.",
        },
        "ilgili": ["acik_anahtar", "sayisal_imza", "ssh"],
    },
    {
        "id": "hash_fonksiyonu",
        "baslik": {"tr": "Özet Fonksiyonu (Hash)", "en": "Hash Function"},
        "kisa": {"tr": "Herhangi bir veriyi sabit uzunlukta, geri döndürülemez bir parmak izine dönüştüren işlev.",
                 "en": "A function that turns any data into a fixed-length, irreversible fingerprint."},
        "aciklama": {
            "tr": "Bir özet (hash) fonksiyonu aynı girdi için her zaman aynı çıktıyı üretir, ama çıktıdan "
                  "girdiyi geri hesaplamak (tersine çevirmek) pratikte imkânsızdır. Şifreler veritabanda "
                  "düz metin yerine özetleri saklanarak korunur; bir dosyanın değişip değişmediğini "
                  "kontrol etmek için de kullanılır.",
            "en": "A hash function always produces the same output for the same input, but computing the "
                  "input back from the output is practically impossible. Passwords are protected by "
                  "storing their hash instead of plaintext in a database, and hashes are also used to "
                  "verify whether a file has changed.",
        },
        "ilgili": ["sha256", "md5", "tuzlama"],
    },
    {
        "id": "tuzlama",
        "baslik": {"tr": "Tuzlama (Salting)", "en": "Salting"},
        "kisa": {"tr": "Şifreyi özetlemeden önce rastgele veri ekleyerek aynı şifrelerin aynı özeti üretmesini önleme tekniği.",
                 "en": "Adding random data before hashing a password so identical passwords don't produce identical hashes."},
        "aciklama": {
            "tr": "Tuzlama olmadan, aynı şifreyi kullanan iki kullanıcının özeti de aynı olur; bu da "
                  "saldırganın önceden hazırlanmış özet tablolarıyla (rainbow table) şifreyi hızla "
                  "bulmasını kolaylaştırır. Her kullanıcıya özgü rastgele bir tuz eklemek, bu önceden "
                  "hesaplanmış tabloları işe yaramaz hâle getirir.",
            "en": "Without salting, two users with the same password end up with the same hash, making "
                  "it easy for an attacker to crack it quickly with precomputed hash tables (rainbow "
                  "tables). Adding a random salt unique to each user renders those precomputed tables "
                  "useless.",
        },
        "ilgili": ["hash_fonksiyonu", "sozluk_saldirisi"],
    },
    {
        "id": "sayisal_imza",
        "baslik": {"tr": "Sayısal İmza (Digital Signature)", "en": "Digital Signature"},
        "kisa": {"tr": "Bir verinin kimden geldiğini ve değiştirilmediğini kanıtlayan kriptografik yöntem.",
                 "en": "A cryptographic method that proves who sent a piece of data and that it hasn't been altered."},
        "aciklama": {
            "tr": "Bir sayısal imza, gönderenin özel anahtarıyla oluşturulur ve alıcı bunu gönderenin açık "
                  "anahtarıyla doğrular; bu da hem kimliği (yalnızca özel anahtarın sahibi imzalayabilir) "
                  "hem de bütünlüğü (veri değiştirilirse imza geçersiz olur) garanti eder. Yazılım "
                  "paketlerinin ve sertifikaların doğrulanmasında temel bir yapı taşıdır.",
            "en": "A digital signature is created with the sender's private key and verified by the "
                  "recipient using the sender's public key, guaranteeing both identity (only the private "
                  "key's owner could have signed it) and integrity (altering the data invalidates the "
                  "signature). It's a core building block for verifying software packages and "
                  "certificates.",
        },
        "ilgili": ["ozel_anahtar", "sertifika"],
    },
    {
        "id": "sertifika",
        "baslik": {"tr": "Sayısal Sertifika", "en": "Digital Certificate"},
        "kisa": {"tr": "Bir açık anahtarı belirli bir kimliğe (örneğin bir web sitesine) bağlayan, güvenilir bir otorite tarafından imzalanan belge.",
                 "en": "A document that binds a public key to an identity, such as a website, signed by a trusted authority."},
        "aciklama": {
            "tr": "Bir web sitesine HTTPS ile bağlandığınızda, tarayıcınız sitenin sunduğu sertifikayı "
                  "kontrol ederek sitenin gerçekten iddia ettiği taraf olduğunu doğrular. Sertifika, "
                  "güvenilen bir Sertifika Otoritesi (CA) tarafından imzalanmamışsa tarayıcı bir uyarı "
                  "gösterir.",
            "en": "When you connect to a website over HTTPS, your browser checks the certificate it "
                  "presents to verify the site really is who it claims to be. If the certificate isn't "
                  "signed by a trusted Certificate Authority (CA), the browser shows a warning.",
        },
        "ilgili": ["sertifika_otoritesi", "ssl_tls", "sayisal_imza"],
    },
    {
        "id": "sertifika_otoritesi",
        "baslik": {"tr": "Sertifika Otoritesi (CA)", "en": "Certificate Authority (CA)"},
        "kisa": {"tr": "Sayısal sertifikaları doğrulayıp imzalayan, tarayıcıların önceden güvendiği kuruluş.",
                 "en": "The trusted organization that verifies and signs digital certificates, pre-trusted by browsers."},
        "aciklama": {
            "tr": "Bir CA, bir web sitesinin gerçekten o alan adının sahibi olduğunu doğruladıktan sonra "
                  "sertifikasını kendi imzasıyla onaylar. Tarayıcılar ve işletim sistemleri, dünya "
                  "genelinde güvenilen bir CA listesiyle gelir; Let's Encrypt gibi kuruluşlar ücretsiz "
                  "sertifika sağlayarak HTTPS'in yaygınlaşmasını kolaylaştırmıştır.",
            "en": "A CA verifies that a website genuinely owns the domain it claims before signing its "
                  "certificate with its own signature. Browsers and operating systems ship with a list "
                  "of globally trusted CAs; organizations like Let's Encrypt have made HTTPS far more "
                  "widespread by offering certificates for free.",
        },
        "ilgili": ["sertifika", "ssl_tls"],
    },
    {
        "id": "aes",
        "baslik": {"tr": "AES", "en": "AES"},
        "kisa": {"tr": "Günümüzde en yaygın kullanılan, hızlı ve güvenli simetrik şifreleme standardı.",
                 "en": "The fast, secure symmetric encryption standard in widest use today."},
        "aciklama": {
            "tr": "AES (Advanced Encryption Standard), 2001'de ABD hükûmeti tarafından standart olarak "
                  "kabul edildi ve o günden beri hem hükûmetler hem de şirketler tarafından yaygın "
                  "kullanılıyor. 128, 192 ya da 256 bit anahtar uzunluklarıyla çalışabilir; VPN "
                  "bağlantılarından disk şifrelemesine kadar birçok yerde karşınıza çıkar.",
            "en": "AES (Advanced Encryption Standard) was adopted as a US government standard in 2001 "
                  "and has been in widespread use by governments and companies alike ever since. It "
                  "works with 128, 192 or 256-bit key lengths and shows up everywhere from VPN "
                  "connections to disk encryption.",
        },
        "ilgili": ["simetrik_sifreleme"],
    },
    {
        "id": "rsa",
        "baslik": {"tr": "RSA", "en": "RSA"},
        "kisa": {"tr": "Büyük asal sayıların çarpanlarına ayrılmasının zorluğuna dayanan, en bilinen asimetrik şifreleme algoritması.",
                 "en": "The best-known asymmetric algorithm, relying on the difficulty of factoring large prime numbers."},
        "aciklama": {
            "tr": "RSA, adını 1977'de onu tanımlayan Rivest, Shamir ve Adleman'dan alır; güvenliği, iki "
                  "büyük asal sayının çarpımını asıl asal çarpanlarına geri ayırmanın klasik "
                  "bilgisayarlar için neredeyse imkânsız olmasına dayanır. SSH anahtarlarında ve "
                  "sertifikalarda yaygın kullanılır.",
            "en": "RSA is named after Rivest, Shamir and Adleman, who described it in 1977; its security "
                  "rests on the fact that factoring the product of two large prime numbers back into its "
                  "primes is nearly impossible for classical computers. It's widely used in SSH keys and "
                  "certificates.",
        },
        "ilgili": ["asimetrik_sifreleme", "ozel_anahtar"],
    },
    {
        "id": "sha256",
        "baslik": {"tr": "SHA-256", "en": "SHA-256"},
        "kisa": {"tr": "256 bitlik bir özet üreten, günümüzde yaygın kullanılan güvenli özet algoritması.",
                 "en": "A secure hash algorithm, widely used today, that produces a 256-bit digest."},
        "aciklama": {
            "tr": "SHA-256, SHA-2 ailesinin bir üyesidir ve dosya bütünlüğünü doğrulamaktan şifre "
                  "saklamaya, Bitcoin gibi kripto paraların madenciliğine kadar birçok alanda kullanılır. "
                  "MD5 ve SHA-1'in aksine, bugüne kadar pratik bir çarpışma (iki farklı girdinin aynı "
                  "özeti üretmesi) saldırısı bulunamamıştır.",
            "en": "SHA-256 belongs to the SHA-2 family and is used everywhere from verifying file "
                  "integrity to storing passwords to mining cryptocurrencies like Bitcoin. Unlike MD5 "
                  "and SHA-1, no practical collision attack (two different inputs producing the same "
                  "hash) has been found against it to date.",
        },
        "ornek": "sha256sum carotos-1.3.iso",
        "ilgili": ["hash_fonksiyonu", "md5"],
    },
    {
        "id": "md5",
        "baslik": {"tr": "MD5", "en": "MD5"},
        "kisa": {"tr": "Eskiden yaygın kullanılan, günümüzde güvenlik amaçlı önerilmeyen bir özet algoritması.",
                 "en": "A once-common hash algorithm no longer recommended for security purposes."},
        "aciklama": {
            "tr": "MD5, 1990'larda tasarlandı ve uzun süre dosya bütünlüğü kontrolünde kullanıldı, ama "
                  "2000'lerin ortasından itibaren pratikte çarpışma üretmenin mümkün olduğu gösterildi. "
                  "Bu yüzden şifre saklama ya da sayısal imza gibi güvenlik açısından kritik işlerde "
                  "artık kullanılmamalı, yerine SHA-256 gibi modern algoritmalar tercih edilmelidir.",
            "en": "MD5 was designed in the 1990s and used widely for file integrity checks, but by the "
                  "mid-2000s it was shown that producing collisions was practically feasible. It should "
                  "no longer be used for security-critical work like password storage or digital "
                  "signatures; modern algorithms like SHA-256 should be used instead.",
        },
        "ilgili": ["hash_fonksiyonu", "sha256"],
    },
    {
        "id": "pgp_gpg",
        "baslik": {"tr": "PGP/GPG", "en": "PGP/GPG"},
        "kisa": {"tr": "E-posta ve dosyaları açık anahtarlı kriptografiyle şifrelemek ve imzalamak için kullanılan standart.",
                 "en": "A standard for encrypting and signing email and files using public-key cryptography."},
        "aciklama": {
            "tr": "PGP (Pretty Good Privacy) 1991'de tanıtıldı; GPG (GNU Privacy Guard) onun özgür "
                  "yazılım uygulamasıdır. İkisi de kullanıcıların bir anahtar çifti oluşturup açık "
                  "anahtarlarını paylaşarak, yalnızca alıcının çözebileceği şifreli e-postalar göndermesini "
                  "ya da gönderdiği bir mesajı imzalayarak kimliğini kanıtlamasını sağlar.",
            "en": "PGP (Pretty Good Privacy) was introduced in 1991; GPG (GNU Privacy Guard) is its free "
                  "software implementation. Both let users generate a key pair and share their public "
                  "key so they can send encrypted email only the recipient can decrypt, or sign a "
                  "message to prove their identity.",
        },
        "ilgili": ["asimetrik_sifreleme", "sayisal_imza", "acik_anahtar"],
    },
    {
        "id": "steganografi",
        "baslik": {"tr": "Steganografi", "en": "Steganography"},
        "kisa": {"tr": "Bir mesajı şifrelemek yerine varlığını tamamen gizleme sanatı.",
                 "en": "The art of hiding a message's very existence, rather than just encrypting it."},
        "aciklama": {
            "tr": "Şifreleme bir mesajın okunamaz olmasını sağlarken, steganografi onun var olduğunu "
                  "bile fark ettirmemeyi hedefler -- örneğin bir metni bir resmin piksel verisinin en "
                  "önemsiz bitlerine gizleyerek. İkisi birlikte de kullanılabilir: önce şifrelenen bir "
                  "mesaj, sonra bir resme gizlenebilir.",
            "en": "Where encryption makes a message unreadable, steganography aims to hide the fact that "
                  "a message exists at all -- hiding text in the least significant bits of an image's "
                  "pixel data, for example. The two can be combined: a message can be encrypted first, "
                  "then hidden inside an image.",
        },
        "ilgili": ["sifreleme"],
    },
    {
        "id": "oturum_anahtari",
        "baslik": {"tr": "Oturum Anahtarı (Session Key)", "en": "Session Key"},
        "kisa": {"tr": "Yalnızca tek bir bağlantı süresince kullanılan, geçici simetrik şifreleme anahtarı.",
                 "en": "A temporary symmetric encryption key used only for the duration of a single connection."},
        "aciklama": {
            "tr": "Bir HTTPS bağlantısı kurulduğunda, taraflar yavaş asimetrik şifrelemeyi yalnızca hızlı "
                  "ve tek seferlik bir oturum anahtarını güvenle değiş tokuş etmek için kullanır; "
                  "bağlantının geri kalanı bu simetrik anahtarla, çok daha hızlı biçimde şifrelenir. Her "
                  "yeni oturumda yeni bir anahtar üretilmesi, bir anahtarın ele geçirilmesinin etkisini "
                  "sınırlar.",
            "en": "When an HTTPS connection is established, the two sides use slow asymmetric encryption "
                  "only to safely exchange a fast, one-time session key; the rest of the connection is "
                  "encrypted with that symmetric key, much faster. Generating a fresh key for every new "
                  "session limits the damage if one key is ever compromised.",
        },
        "ilgili": ["simetrik_sifreleme", "asimetrik_sifreleme", "ssl_tls"],
    },
    {
        "id": "uctan_uca_sifreleme",
        "baslik": {"tr": "Uçtan Uca Şifreleme", "en": "End-to-End Encryption"},
        "kisa": {"tr": "Bir mesajın yalnızca gönderen ve alıcı tarafından okunabildiği, aradaki hiçbir sunucunun çözemediği şifreleme biçimi.",
                 "en": "Encryption where only sender and recipient can read a message, with no server in between able to decrypt it."},
        "aciklama": {
            "tr": "Uçtan uca şifrelemede mesaj, göndericinin cihazında şifrelenir ve ancak alıcının "
                  "cihazında çözülür; aradaki mesajlaşma sunucusu bile içeriği okuyamaz. Bu, sunucunun ele "
                  "geçirilmesi ya da verileri paylaşmaya zorlanması durumunda bile mesajların gizli "
                  "kalmasını sağlar.",
            "en": "With end-to-end encryption, a message is encrypted on the sender's device and only "
                  "decrypted on the recipient's device; even the messaging server in between can't read "
                  "the content. That keeps messages private even if the server itself is compromised or "
                  "compelled to hand over data.",
        },
        "ilgili": ["asimetrik_sifreleme", "sifreleme"],
    },
    {
        "id": "blok_zinciri",
        "baslik": {"tr": "Blok Zinciri (Blockchain)", "en": "Blockchain"},
        "kisa": {"tr": "Her bloğun bir öncekine kriptografik olarak bağlandığı, geriye dönük değiştirilmesi çok zor dağıtık kayıt defteri.",
                 "en": "A distributed ledger where each block is cryptographically chained to the last, making retroactive changes extremely difficult."},
        "aciklama": {
            "tr": "Bir blok zincirinde her blok, bir önceki bloğun özetini (hash) içerir; bu da geçmişteki "
                  "bir bloğu değiştirmenin, ondan sonraki tüm blokların da yeniden hesaplanmasını "
                  "gerektirmesi anlamına gelir -- ki bu, binlerce katılımcıya dağıtılmış bir ağda "
                  "pratikte imkânsızdır. Bitcoin gibi kripto paraların temelini oluşturur, ama kavram "
                  "kripto paralarla sınırlı değildir.",
            "en": "In a blockchain, each block contains the hash of the one before it, meaning altering "
                  "a past block would require recomputing every block after it -- practically impossible "
                  "on a network distributed across thousands of participants. It underlies "
                  "cryptocurrencies like Bitcoin, though the concept isn't limited to them.",
        },
        "ilgili": ["hash_fonksiyonu"],
    },
]
