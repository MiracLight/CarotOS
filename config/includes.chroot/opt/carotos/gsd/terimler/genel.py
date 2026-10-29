# -*- coding: utf-8 -*-
"""GSD -- Genel Bilgisayar Bilimi terimleri."""

TERIMLER = [
    {
        "id": "degisken",
        "baslik": {"tr": "Değişken (Variable)", "en": "Variable"},
        "kisa": {"tr": "Programın çalışması sırasında bir değeri saklamak için kullanılan isimlendirilmiş bellek alanı.",
                 "en": "A named piece of memory used to store a value while a program runs."},
        "aciklama": {
            "tr": "Bir değişken, bir kutuya isim vermeye benzer: `yas = 25` dendiğinde \"yas\" adlı "
                  "kutuya 25 değeri konur ve program boyunca bu isimle okunup değiştirilebilir. "
                  "Programlama dilinin \"statik tipli\" (C, Java) ya da \"dinamik tipli\" (Python, "
                  "JavaScript) olmasına göre bir değişkenin türü sabit ya da esnek olabilir.",
            "en": "A variable is like naming a box: writing `age = 25` puts the value 25 into a box "
                  "called \"age\", which can then be read and changed by that name throughout the "
                  "program. Depending on whether a language is \"statically typed\" (C, Java) or "
                  "\"dynamically typed\" (Python, JavaScript), a variable's type can be fixed or "
                  "flexible.",
        },
        "ilgili": ["veri_tipi", "fonksiyon"],
    },
    {
        "id": "veri_tipi",
        "baslik": {"tr": "Veri Tipi (Data Type)", "en": "Data Type"},
        "kisa": {"tr": "Bir değerin ne tür bilgi taşıdığını ve üzerinde hangi işlemlerin yapılabileceğini belirleyen sınıflandırma.",
                 "en": "A classification that defines what kind of information a value holds and what operations can be done on it."},
        "aciklama": {
            "tr": "Tam sayı (integer), ondalıklı sayı (float), metin (string), mantıksal değer (boolean) "
                  "ve liste gibi temel veri tipleri, bir değerin bellekte nasıl saklanacağını ve "
                  "hangi işlemleri (toplama, karşılaştırma, birleştirme) desteklediğini belirler. Yanlış "
                  "tipte bir işlem yapmaya çalışmak -- bir metni bir sayıyla toplamak gibi -- çoğu dilde "
                  "hataya yol açar.",
            "en": "Basic data types -- integer, float, string, boolean, list -- determine how a value is "
                  "stored in memory and which operations it supports, like addition, comparison or "
                  "concatenation. Trying an operation on the wrong type, like adding text to a number, "
                  "triggers an error in most languages.",
        },
        "ilgili": ["degisken", "bit_byte"],
    },
    {
        "id": "fonksiyon",
        "baslik": {"tr": "Fonksiyon (Function)", "en": "Function"},
        "kisa": {"tr": "Belirli bir işi yapmak üzere adlandırılmış, tekrar tekrar çağrılabilen kod bloğu.",
                 "en": "A named, reusable block of code written to carry out a specific task."},
        "aciklama": {
            "tr": "Bir fonksiyon, aynı kodu defalarca yazmak yerine bir kez tanımlanıp istenildiği kadar "
                  "\"çağrılmasını\" sağlar; genellikle girdi olarak parametre alır ve bir sonuç "
                  "döndürür. Büyük programları küçük, test edilebilir ve anlaşılır parçalara bölmenin "
                  "temel yoludur.",
            "en": "Instead of writing the same code over and over, a function is defined once and can be "
                  "\"called\" as many times as needed; it typically takes parameters as input and returns "
                  "a result. It's the basic way to break a large program into small, testable, "
                  "understandable pieces.",
        },
        "ornek": "def alan_hesapla(en, boy):\n    return en * boy",
        "ilgili": ["degisken", "nesne_yonelimli_programlama"],
    },
    {
        "id": "nesne_yonelimli_programlama",
        "baslik": {"tr": "Nesne Yönelimli Programlama (OOP)", "en": "Object-Oriented Programming (OOP)"},
        "kisa": {"tr": "Kodu, veri ve o veri üzerinde çalışan davranışları bir arada tutan \"nesneler\" etrafında düzenleyen yaklaşım.",
                 "en": "A programming style that organizes code around \"objects\" bundling data with the behavior that acts on it."},
        "aciklama": {
            "tr": "OOP'de bir \"sınıf\" (class), bir nesnenin sahip olacağı özellikleri ve davranışları "
                  "tanımlayan bir şablondur; o şablondan üretilen her somut örneğe \"nesne\" (object) "
                  "denir. Kalıtım (inheritance), kapsülleme (encapsulation) ve çok biçimlilik "
                  "(polymorphism) OOP'nin temel kavramlarıdır. Python, Java ve C++ bu yaklaşımı güçlü "
                  "biçimde destekler.",
            "en": "In OOP, a \"class\" is a blueprint defining the properties and behavior an object will "
                  "have; each concrete instance made from that blueprint is called an \"object\". "
                  "Inheritance, encapsulation and polymorphism are OOP's core concepts. Python, Java and "
                  "C++ all support this style heavily.",
        },
        "ilgili": ["fonksiyon", "veri_tipi"],
    },
    {
        "id": "api",
        "baslik": {"tr": "API", "en": "API"},
        "kisa": {"tr": "İki yazılımın birbiriyle önceden tanımlı kurallarla konuşmasını sağlayan arayüz.",
                 "en": "The interface that lets two pieces of software talk to each other through predefined rules."},
        "aciklama": {
            "tr": "API (Application Programming Interface), bir programın hangi işlevleri dışarıya "
                  "sunduğunu ve bunlara nasıl erişileceğini tanımlar -- bir restoran menüsü gibi: "
                  "mutfağın nasıl çalıştığını bilmenize gerek yok, yalnızca menüdeki seçenekleri "
                  "isteyebilirsiniz. Hava durumu uygulamaları, ödeme sistemleri ve neredeyse her modern "
                  "servis API'ler üzerinden konuşur.",
            "en": "An API (Application Programming Interface) defines what functions a program exposes "
                  "and how to access them -- like a restaurant menu: you don't need to know how the "
                  "kitchen works, you just order from the listed options. Weather apps, payment systems "
                  "and nearly every modern service talk to each other through APIs.",
        },
        "ilgili": ["rest_api", "json"],
    },
    {
        "id": "rest_api",
        "baslik": {"tr": "REST API", "en": "REST API"},
        "kisa": {"tr": "Web üzerinden HTTP istekleriyle çalışan, en yaygın kullanılan API tasarım biçimi.",
                 "en": "The most common API design style, working over the web through HTTP requests."},
        "aciklama": {
            "tr": "REST (Representational State Transfer), kaynaklara (kullanıcılar, ürünler gibi) HTTP "
                  "yöntemleriyle (GET okuma, POST oluşturma, PUT güncelleme, DELETE silme) erişmeyi "
                  "standartlaştırır. Yanıtlar genellikle JSON biçiminde döner; bu basitlik, onu web "
                  "servisleri arasında en yaygın API tarzı hâline getirmiştir.",
            "en": "REST (Representational State Transfer) standardizes accessing resources -- users, "
                  "products -- through HTTP methods: GET to read, POST to create, PUT to update, DELETE "
                  "to remove. Responses usually come back as JSON; that simplicity has made it the most "
                  "common API style for web services.",
        },
        "ornek": "GET /api/kullanicilar/42",
        "ilgili": ["api", "http", "json"],
    },
    {
        "id": "json",
        "baslik": {"tr": "JSON", "en": "JSON"},
        "kisa": {"tr": "Hem insan hem de makine tarafından kolayca okunabilen, hafif bir veri değişim biçimi.",
                 "en": "A lightweight data-interchange format that's easy for both humans and machines to read."},
        "aciklama": {
            "tr": "JSON (JavaScript Object Notation), verileri anahtar-değer çiftleri ve listeler hâlinde "
                  "`{\"ad\": \"Carot\", \"yas\": 2}` gibi gösterir. API yanıtlarından yapılandırma "
                  "dosyalarına (CarotOS uygulamalarının settings.json dosyaları gibi) kadar hemen her "
                  "yerde karşınıza çıkar.",
            "en": "JSON (JavaScript Object Notation) represents data as key-value pairs and lists, like "
                  "`{\"name\": \"Carot\", \"age\": 2}`. It shows up everywhere from API responses to "
                  "configuration files -- including the settings.json files CarotOS apps use.",
        },
        "ilgili": ["api", "rest_api", "xml"],
    },
    {
        "id": "xml",
        "baslik": {"tr": "XML", "en": "XML"},
        "kisa": {"tr": "Verileri iç içe geçmiş etiketlerle tanımlayan, JSON'dan daha eski bir biçimlendirme dili.",
                 "en": "An older markup language that describes data using nested tags."},
        "aciklama": {
            "tr": "XML (Extensible Markup Language), `<kullanici><ad>Carot</ad></kullanici>` gibi açılış "
                  "ve kapanış etiketleriyle hiyerarşik veri tanımlar. JSON'a göre daha ayrıntılı "
                  "(verbose) olsa da, doğrulama şemaları (XSD) ve geniş araç desteğiyle hâlâ kurumsal "
                  "sistemlerde ve yapılandırma dosyalarında yaygın kullanılır.",
            "en": "XML (Extensible Markup Language) defines hierarchical data with opening and closing "
                  "tags, like `<user><name>Carot</name></user>`. It's more verbose than JSON, but its "
                  "validation schemas (XSD) and broad tooling keep it widely used in enterprise systems "
                  "and configuration files.",
        },
        "ilgili": ["json"],
    },
    {
        "id": "veritabani",
        "baslik": {"tr": "Veritabanı (Database)", "en": "Database"},
        "kisa": {"tr": "Verileri düzenli, aranabilir ve güncellenebilir biçimde saklayan sistem.",
                 "en": "A system that stores data in an organized, searchable and updatable form."},
        "aciklama": {
            "tr": "Bir veritabanı, veriyi düz bir dosyadan çok daha hızlı aranabilir, birden fazla "
                  "kullanıcı tarafından aynı anda güvenle değiştirilebilir ve tutarlı kalacak biçimde "
                  "saklar. İlişkisel (SQL) ve ilişkisel olmayan (NoSQL) olmak üzere iki ana ailesi "
                  "vardır.",
            "en": "A database stores data in a way that's far faster to search than a plain file, can be "
                  "safely modified by multiple users at once, and stays consistent. It comes in two main "
                  "families: relational (SQL) and non-relational (NoSQL).",
        },
        "ilgili": ["sql", "nosql"],
    },
    {
        "id": "sql",
        "baslik": {"tr": "SQL", "en": "SQL"},
        "kisa": {"tr": "İlişkisel veritabanlarıyla konuşmak için kullanılan standart sorgu dili.",
                 "en": "The standard query language used to talk to relational databases."},
        "aciklama": {
            "tr": "SQL (Structured Query Language), verileri tablolar hâlinde tutan ilişkisel "
                  "veritabanlarından veri okumayı (`SELECT`), eklemeyi (`INSERT`), güncellemeyi "
                  "(`UPDATE`) ve silmeyi (`DELETE`) sağlar. MySQL, PostgreSQL ve SQLite gibi birçok "
                  "popüler veritabanı sistemi SQL'in kendi lehçesini kullanır. sqlmap gibi araçların "
                  "test ettiği \"SQL enjeksiyonu\" zafiyeti de adını buradan alır.",
            "en": "SQL (Structured Query Language) lets you read (`SELECT`), add (`INSERT`), update "
                  "(`UPDATE`) and delete (`DELETE`) data in relational databases that store data as "
                  "tables. Popular systems like MySQL, PostgreSQL and SQLite each use their own dialect "
                  "of SQL. The \"SQL injection\" flaw that tools like sqlmap test for takes its name "
                  "from here.",
        },
        "ornek": "SELECT ad FROM kullanicilar WHERE id = 42;",
        "ilgili": ["veritabani", "sqlmap"],
    },
    {
        "id": "nosql",
        "baslik": {"tr": "NoSQL", "en": "NoSQL"},
        "kisa": {"tr": "Veriyi katı tablo yapısı yerine belge, anahtar-değer ya da graf biçiminde saklayan veritabanı türü.",
                 "en": "A database style that stores data as documents, key-value pairs or graphs instead of rigid tables."},
        "aciklama": {
            "tr": "NoSQL veritabanları, ilişkisel modelin sabit şemasına bağlı kalmadan daha esnek veri "
                  "yapılarına izin verir; bu da hızlı değişen ya da düzensiz verilerle çalışırken ve "
                  "çok büyük ölçekte yatay olarak genişlerken avantaj sağlar. MongoDB (belge tabanlı) ve "
                  "Redis (anahtar-değer) bilinen örneklerdir.",
            "en": "NoSQL databases allow more flexible data structures without being locked into the "
                  "relational model's fixed schema, which helps when data changes quickly, is irregular, "
                  "or needs to scale horizontally at very large size. MongoDB (document-based) and Redis "
                  "(key-value) are well-known examples.",
        },
        "ilgili": ["sql", "veritabani"],
    },
    {
        "id": "derleyici",
        "baslik": {"tr": "Derleyici (Compiler)", "en": "Compiler"},
        "kisa": {"tr": "İnsan tarafından yazılan kaynak kodu, çalıştırmadan önce makine koduna çeviren program.",
                 "en": "A program that translates human-written source code into machine code before it runs."},
        "aciklama": {
            "tr": "Bir derleyici, C ya da Rust gibi dillerde yazılmış kodu, çalıştırılmadan önce tek "
                  "seferde işlemciye özel bir ikili (binary) dosyaya çevirir. Bu, programın çok hızlı "
                  "çalışmasını sağlar ama her platform için ayrı bir derleme gerektirir.",
            "en": "A compiler translates code written in languages like C or Rust into a "
                  "processor-specific binary file all at once, before the program ever runs. This makes "
                  "the program run very fast, but requires a separate compile step for each target "
                  "platform.",
        },
        "ilgili": ["yorumlayici", "bit_byte"],
    },
    {
        "id": "yorumlayici",
        "baslik": {"tr": "Yorumlayıcı (Interpreter)", "en": "Interpreter"},
        "kisa": {"tr": "Kaynak kodu önceden derlemeden, satır satır okuyup doğrudan çalıştıran program.",
                 "en": "A program that reads and runs source code directly, line by line, without a separate compile step."},
        "aciklama": {
            "tr": "Python ve JavaScript gibi dillerde yorumlayıcı, kodu çalıştırılacağı anda okuyup "
                  "işler; bu da geliştirmeyi hızlandırır (derleme beklemeye gerek yoktur) ama genellikle "
                  "derlenmiş koddan daha yavaş çalışır. Bazı modern diller (Java gibi) ikisinin "
                  "karmasını kullanır: önce ara bir forma derler, sonra o formu bir sanal makinede "
                  "yorumlar.",
            "en": "In languages like Python and JavaScript, an interpreter reads and processes code at "
                  "the moment it runs, which speeds up development -- no waiting for a compile step -- "
                  "but usually runs slower than compiled code. Some modern languages, like Java, use a "
                  "hybrid: compile to an intermediate form first, then interpret that on a virtual "
                  "machine.",
        },
        "ilgili": ["derleyici", "bash"],
    },
    {
        "id": "bit_byte",
        "baslik": {"tr": "Bit ve Bayt (Byte)", "en": "Bit and Byte"},
        "kisa": {"tr": "Bilgisayarın en küçük bilgi birimi olan bit ve sekiz bitlik grubu olan bayt.",
                 "en": "The bit, the smallest unit of information a computer uses, and the byte, a group of eight bits."},
        "aciklama": {
            "tr": "Bir bit yalnızca 0 ya da 1 değerini taşıyabilir; sekiz bit bir araya geldiğinde bir "
                  "bayt oluşur ve 0-255 arası 256 farklı değeri temsil edebilir. Kilobayt, megabayt, "
                  "gigabayt gibi birimler baytın katları olarak büyür; bir metin karakteri genellikle "
                  "bir bayt yer kaplar.",
            "en": "A bit can hold only 0 or 1; eight bits together form a byte, which can represent 256 "
                  "different values from 0 to 255. Units like kilobyte, megabyte and gigabyte grow as "
                  "multiples of the byte; a single text character typically takes up one byte.",
        },
        "ilgili": ["ikili_sistem", "veri_tipi"],
    },
    {
        "id": "ikili_sistem",
        "baslik": {"tr": "İkili Sayı Sistemi (Binary)", "en": "Binary Number System"},
        "kisa": {"tr": "Yalnızca 0 ve 1 rakamlarını kullanan, bilgisayarların temel çalışma dili olan sayı sistemi.",
                 "en": "The number system using only the digits 0 and 1, the fundamental language computers run on."},
        "aciklama": {
            "tr": "Günlük hayatta kullandığımız onluk (decimal) sistemin aksine, ikili sistemde her "
                  "basamak 2'nin bir kuvvetini temsil eder; örneğin \"1011\" onlukta 11'e eşittir "
                  "(8+0+2+1). Bilgisayarlar temelde transistörlerin \"açık\" ya da \"kapalı\" iki "
                  "durumuyla çalıştığı için her şeyi -- metni, resmi, sesi -- sonunda ikili sayılara "
                  "indirger.",
            "en": "Unlike the decimal system used in everyday life, every digit in binary represents a "
                  "power of 2; \"1011\", for example, equals 11 in decimal (8+0+2+1). Because computers "
                  "fundamentally run on transistors being either \"on\" or \"off\", everything -- text, "
                  "images, sound -- ultimately reduces to binary numbers.",
        },
        "ilgili": ["bit_byte"],
    },
    {
        "id": "versiyon_kontrolu",
        "baslik": {"tr": "Sürüm Kontrolü (Version Control)", "en": "Version Control"},
        "kisa": {"tr": "Bir projenin zaman içindeki tüm değişikliklerini kaydeden ve geri alınabilir kılan sistem.",
                 "en": "A system that records every change to a project over time and makes them reversible."},
        "aciklama": {
            "tr": "Sürüm kontrolü, kimin neyi ne zaman değiştirdiğini kaydeder, birden fazla kişinin aynı "
                  "projede çakışmadan çalışmasını sağlar ve gerektiğinde eski bir sürüme dönmeyi "
                  "mümkün kılar. Günümüzde en yaygın kullanılan sürüm kontrol sistemi Git'tir.",
            "en": "Version control records who changed what and when, lets multiple people work on the "
                  "same project without stepping on each other, and makes it possible to roll back to an "
                  "earlier version when needed. Git is by far the most widely used version control "
                  "system today.",
        },
        "ilgili": ["git", "acik_kaynak"],
    },
    {
        "id": "git",
        "baslik": {"tr": "Git", "en": "Git"},
        "kisa": {"tr": "Linus Torvalds tarafından yazılan, dağıtık sürüm kontrol sistemi.",
                 "en": "The distributed version control system written by Linus Torvalds."},
        "aciklama": {
            "tr": "Git, her geliştiricinin projenin tüm geçmişinin tam bir kopyasını kendi bilgisayarında "
                  "tutmasını sağlar (dağıtık yapı); bu da çevrimdışı çalışmayı ve hızlı dallanmayı "
                  "(branch) mümkün kılar. GitHub ve GitLab gibi platformlar, Git depolarını barındırıp "
                  "iş birliğini kolaylaştıran servislerdir -- Git'in kendisi değildir.",
            "en": "Git lets every developer keep a full copy of the project's entire history on their "
                  "own machine (a distributed design), which enables offline work and fast branching. "
                  "Platforms like GitHub and GitLab host Git repositories and make collaboration easier "
                  "-- they aren't Git itself.",
        },
        "ornek": "git clone https://github.com/kullanici/proje.git",
        "ilgili": ["versiyon_kontrolu", "acik_kaynak"],
    },
    {
        "id": "acik_kaynak",
        "baslik": {"tr": "Açık Kaynak (Open Source)", "en": "Open Source"},
        "kisa": {"tr": "Kaynak kodu herkese açık, incelenebilir ve değiştirilebilir yazılım.",
                 "en": "Software whose source code is openly available for anyone to inspect and modify."},
        "aciklama": {
            "tr": "Açık kaynak yazılım, kodun herkes tarafından okunabilmesini sağlayarak güveni ve "
                  "topluluk katkısını artırır -- bir hata ya da kötü niyetli bir kod parçası, kapalı "
                  "kaynaklı yazılıma göre çok daha kolay fark edilebilir. Linux çekirdeği, Debian ve "
                  "dolayısıyla CarotOS açık kaynaklıdır.",
            "en": "Open source software makes its code readable by anyone, which builds trust and "
                  "encourages community contribution -- a bug or a malicious piece of code is far easier "
                  "to spot than in closed-source software. The Linux kernel, Debian and, by extension, "
                  "CarotOS are all open source.",
        },
        "ilgili": ["git", "yazilim_lisansi", "dagitim"],
    },
    {
        "id": "yazilim_lisansi",
        "baslik": {"tr": "Yazılım Lisansı", "en": "Software License"},
        "kisa": {"tr": "Bir yazılımın nasıl kullanılabileceğini, değiştirilebileceğini ve paylaşılabileceğini belirleyen hukuki kurallar.",
                 "en": "The legal rules that define how software may be used, modified and shared."},
        "aciklama": {
            "tr": "GPL gibi \"copyleft\" lisanslar, yazılımdan türetilen her çalışmanın da aynı özgür "
                  "koşullarla paylaşılmasını zorunlu kılarken; MIT ya da Apache gibi daha izin verici "
                  "lisanslar, kodun neredeyse hiç kısıtlama olmadan ticari projelerde bile kullanılmasına "
                  "izin verir.",
            "en": "\"Copyleft\" licenses like the GPL require that any work derived from the software "
                  "also be shared under the same free terms, while more permissive licenses like MIT or "
                  "Apache let the code be used with almost no restrictions, even in commercial projects.",
        },
        "ilgili": ["acik_kaynak"],
    },
    {
        "id": "bulut_bilisim",
        "baslik": {"tr": "Bulut Bilişim (Cloud Computing)", "en": "Cloud Computing"},
        "kisa": {"tr": "Bilgisayar gücü, depolama ve servislerin kendi donanımınız yerine internet üzerinden kiralanması.",
                 "en": "Renting computing power, storage and services over the internet instead of owning the hardware."},
        "aciklama": {
            "tr": "Bulut bilişim sayesinde bir şirket, kendi sunucu odasını kurup bakımını yapmak yerine "
                  "Amazon Web Services, Google Cloud ya da Microsoft Azure gibi sağlayıcılardan ihtiyacı "
                  "kadar kaynağı dakikalar içinde kiralayıp talebe göre ölçeklendirebilir.",
            "en": "With cloud computing, a company can rent exactly the resources it needs in minutes "
                  "from providers like Amazon Web Services, Google Cloud or Microsoft Azure, and scale "
                  "them up or down on demand, rather than building and maintaining its own server room.",
        },
        "ilgili": ["sanallastirma", "konteyner"],
    },
    {
        "id": "sanallastirma",
        "baslik": {"tr": "Sanallaştırma (Virtualization)", "en": "Virtualization"},
        "kisa": {"tr": "Tek bir fiziksel bilgisayarda birden fazla bağımsız sanal makine çalıştırma tekniği.",
                 "en": "The technique of running multiple independent virtual machines on a single physical computer."},
        "aciklama": {
            "tr": "Bir \"hipervizör\", fiziksel donanımın işlemci, bellek ve disk kaynaklarını bölüştürerek "
                  "her biri kendi işletim sistemine sahip birden fazla sanal makinenin aynı anda ve "
                  "birbirinden izole çalışmasını sağlar. CarotOS'u bir VM üzerinde test etmek de bu "
                  "teknolojiyi kullanır.",
            "en": "A \"hypervisor\" divides a physical machine's CPU, memory and disk resources so that "
                  "several virtual machines, each with its own operating system, can run at the same "
                  "time, isolated from one another. Testing CarotOS inside a VM relies on exactly this "
                  "technology.",
        },
        "ilgili": ["bulut_bilisim", "konteyner"],
    },
    {
        "id": "konteyner",
        "baslik": {"tr": "Konteyner (Container)", "en": "Container"},
        "kisa": {"tr": "Bir uygulamayı, tüm bağımlılıklarıyla birlikte hafif, taşınabilir bir pakette çalıştıran teknoloji.",
                 "en": "A technology that packages an application with all its dependencies into a lightweight, portable unit."},
        "aciklama": {
            "tr": "Bir sanal makinenin aksine konteyner, kendi işletim sistemi çekirdeğini taşımaz; "
                  "sunucunun çekirdeğini diğer konteynerlerle paylaşır, bu da onu çok daha hafif ve hızlı "
                  "başlatılabilir kılar. Docker, konteyner teknolojisinin en yaygın bilinen aracıdır.",
            "en": "Unlike a virtual machine, a container doesn't carry its own kernel; it shares the "
                  "host's kernel with other containers, which makes it far lighter and faster to start. "
                  "Docker is the best-known tool for container technology.",
        },
        "ilgili": ["sanallastirma", "mikroservis"],
    },
    {
        "id": "mikroservis",
        "baslik": {"tr": "Mikroservis (Microservice)", "en": "Microservice"},
        "kisa": {"tr": "Büyük bir uygulamayı, her biri bağımsız çalışan küçük, odaklı servislere bölme mimarisi.",
                 "en": "An architecture that splits a large application into small, focused, independently run services."},
        "aciklama": {
            "tr": "Mikroservis mimarisinde her servis (ödeme, bildirim, kullanıcı yönetimi gibi) ayrı "
                  "geliştirilir, ayrı dağıtılır ve genellikle API'ler üzerinden birbiriyle konuşur; bu da "
                  "tek bir büyük (monolitik) uygulamaya kıyasla esneklik sağlar ama ağ üzerinden "
                  "koordinasyon karmaşıklığı ekler.",
            "en": "In a microservice architecture, each service -- payments, notifications, user "
                  "management -- is developed and deployed separately, usually talking to the others "
                  "through APIs; this offers more flexibility than one large (monolithic) application, "
                  "but adds the complexity of coordinating over a network.",
        },
        "ilgili": ["konteyner", "api"],
    },
    {
        "id": "yapay_zeka",
        "baslik": {"tr": "Yapay Zeka (AI)", "en": "Artificial Intelligence (AI)"},
        "kisa": {"tr": "Normalde insan zekâsı gerektiren görevleri (öğrenme, karar verme) yerine getirebilen sistemlerin genel adı.",
                 "en": "The broad field of systems that can perform tasks normally requiring human intelligence, like learning and decision-making."},
        "aciklama": {
            "tr": "Yapay zeka; basit kural tabanlı sistemlerden, veriden örüntü öğrenen makine öğrenmesi "
                  "modellerine ve büyük dil modellerine kadar geniş bir alanı kapsayan şemsiye bir "
                  "terimdir. Günümüzde en çok ilgi gören alt alanı makine öğrenmesidir.",
            "en": "AI is an umbrella term spanning everything from simple rule-based systems to machine "
                  "learning models that learn patterns from data, to today's large language models. "
                  "Machine learning is the subfield that gets the most attention today.",
        },
        "ilgili": ["makine_ogrenmesi", "sinir_agi"],
    },
    {
        "id": "makine_ogrenmesi",
        "baslik": {"tr": "Makine Öğrenmesi (Machine Learning)", "en": "Machine Learning"},
        "kisa": {"tr": "Kuralları elle yazmak yerine sistemin örnek verilerden örüntü çıkarmasını sağlayan yapay zeka dalı.",
                 "en": "The branch of AI where a system extracts patterns from example data instead of being given hand-written rules."},
        "aciklama": {
            "tr": "Klasik programlamada geliştirici kuralları yazar; makine öğrenmesinde ise bir model, "
                  "binlerce örnekten (etiketli spam/spam-değil e-postalar gibi) kendi başına örüntüleri "
                  "çıkarır ve daha önce görmediği verilerde tahmin yapar. Önerilen videolar, spam "
                  "filtreleri ve yüz tanıma bu yöntemle çalışır.",
            "en": "In classical programming, a developer writes the rules; in machine learning, a model "
                  "extracts patterns on its own from thousands of examples -- labeled spam and not-spam "
                  "emails, say -- and then makes predictions on data it has never seen. Video "
                  "recommendations, spam filters and face recognition all work this way.",
        },
        "ilgili": ["yapay_zeka", "sinir_agi"],
    },
    {
        "id": "sinir_agi",
        "baslik": {"tr": "Yapay Sinir Ağı (Neural Network)", "en": "Neural Network"},
        "kisa": {"tr": "Beyindeki nöronlardan esinlenen, birbirine bağlı katmanlar hâlinde veri işleyen makine öğrenmesi modeli.",
                 "en": "A machine learning model loosely inspired by neurons in the brain, processing data through connected layers."},
        "aciklama": {
            "tr": "Bir yapay sinir ağı, girdi verisini birbirine bağlı \"katmanlar\" hâlinde işler; her "
                  "bağlantının bir \"ağırlığı\" vardır ve eğitim sırasında bu ağırlıklar, modelin doğru "
                  "tahmin yapmasını sağlayacak şekilde kademeli olarak ayarlanır. \"Derin öğrenme\" (deep "
                  "learning), çok sayıda katmana sahip sinir ağlarını ifade eder.",
            "en": "A neural network processes input data through connected \"layers\"; every connection "
                  "has a \"weight\", and during training those weights are gradually adjusted so the "
                  "model learns to make accurate predictions. \"Deep learning\" refers to neural networks "
                  "with many layers.",
        },
        "ilgili": ["makine_ogrenmesi", "yapay_zeka"],
    },
    {
        "id": "hata_ayiklama",
        "baslik": {"tr": "Hata Ayıklama (Debugging)", "en": "Debugging"},
        "kisa": {"tr": "Bir programdaki hatanın kaynağını bulup düzeltme süreci.",
                 "en": "The process of finding and fixing the source of a bug in a program."},
        "aciklama": {
            "tr": "Hata ayıklama; günlük (log) mesajlarını okumak, kodu adım adım bir \"debugger\" "
                  "aracıyla izlemek ya da bölüp test ederek sorunu daraltmak gibi yöntemlerle yapılır. "
                  "\"Bug\" (böcek) teriminin kökeni, 1947'de gerçek bir güve kelebeğinin bir bilgisayar "
                  "rölesine sıkışıp arızaya yol açmasına dayanır.",
            "en": "Debugging involves reading log messages, stepping through code with a debugger tool, "
                  "or narrowing down the problem by splitting and testing pieces of the program. The "
                  "term \"bug\" itself traces back to 1947, when an actual moth got stuck in a computer "
                  "relay and caused a malfunction.",
        },
        "ilgili": ["log_dosyasi"],
    },
    {
        "id": "cevik_gelistirme",
        "baslik": {"tr": "Çevik Geliştirme (Agile)", "en": "Agile Development"},
        "kisa": {"tr": "Yazılımı büyük tek seferlik planlar yerine kısa, tekrarlanan döngülerle geliştirme yaklaşımı.",
                 "en": "A software development approach that works in short, repeated cycles instead of one big upfront plan."},
        "aciklama": {
            "tr": "Çevik yaklaşım, bir projeyi genellikle \"sprint\" adı verilen kısa (1-4 haftalık) "
                  "döngülere böler; her döngü sonunda çalışan bir ürün parçası teslim edilir ve geri "
                  "bildirime göre yön değiştirilebilir. Scrum ve Kanban, en yaygın kullanılan çevik "
                  "çerçevelerdir.",
            "en": "Agile breaks a project into short cycles, usually called \"sprints\" (1-4 weeks); each "
                  "cycle delivers a working piece of the product and lets the team change direction based "
                  "on feedback. Scrum and Kanban are the most widely used agile frameworks.",
        },
        "ilgili": ["git"],
    },
]
