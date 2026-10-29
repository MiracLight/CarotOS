# -*- coding: utf-8 -*-
"""GSD -- Linux ve Sistem terimleri."""

TERIMLER = [
    {
        "id": "kernel",
        "baslik": {"tr": "Çekirdek (Kernel)", "en": "Kernel"},
        "kisa": {"tr": "Donanımla doğrudan konuşan, işletim sisteminin kalbi olan yazılım katmanı.",
                 "en": "The software layer that talks directly to hardware; the heart of the operating system."},
        "aciklama": {
            "tr": "Çekirdek, işlemci zamanını, belleği, disk erişimini ve çevre birimlerini yöneten ve "
                  "üzerindeki tüm programların donanımla güvenli biçimde konuşmasını sağlayan katmandır. "
                  "Linux çekirdeği 1991'de Linus Torvalds tarafından başlatıldı ve bugün binlerce "
                  "geliştiricinin katkısıyla gelişmeye devam ediyor.\n\n"
                  "CarotOS da dahil olmak üzere her Linux dağıtımı aynı çekirdek ailesini kullanır; "
                  "dağıtımları birbirinden ayıran şey çekirdeğin üzerine eklenen masaüstü, araçlar ve "
                  "paket yönetimidir.",
            "en": "The kernel manages CPU time, memory, disk access and peripherals, letting every "
                  "program above it talk to hardware safely. The Linux kernel was started by Linus "
                  "Torvalds in 1991 and is still developed by thousands of contributors today.\n\n"
                  "Every Linux distribution, CarotOS included, shares the same kernel family; what "
                  "sets distributions apart is the desktop, tools and package management built on top "
                  "of it.",
        },
        "ilgili": ["dagitim", "surec", "kabuk"],
    },
    {
        "id": "dagitim",
        "baslik": {"tr": "Dağıtım (Distro)", "en": "Distribution (Distro)"},
        "kisa": {"tr": "Linux çekirdeği etrafında paketlenmiş, kurulabilir eksiksiz bir işletim sistemi.",
                 "en": "A complete, installable operating system packaged around the Linux kernel."},
        "aciklama": {
            "tr": "Bir dağıtım; çekirdeği, bir paket yöneticisini, sistem araçlarını ve genellikle bir "
                  "masaüstü ortamını bir araya getirip kurulabilir tek bir bütün hâline getirir. Debian, "
                  "Ubuntu, Fedora ve Arch birer dağıtım ailesidir; CarotOS da Debian 13 \"Trixie\" "
                  "tabanlıdır ve bu sayede Debian için yazılmış binlerce paketi doğrudan kullanabilir.\n\n"
                  "Aynı çekirdeği paylaşsalar da dağıtımlar; varsayılan yazılımları, güncelleme "
                  "politikaları ve hedef kitleleri bakımından büyük farklar taşıyabilir.",
            "en": "A distribution bundles the kernel, a package manager, system tools and usually a "
                  "desktop environment into one installable whole. Debian, Ubuntu, Fedora and Arch are "
                  "distribution families; CarotOS itself is based on Debian 13 \"Trixie\", which lets it "
                  "use the thousands of packages written for Debian directly.\n\n"
                  "Even though they share a kernel, distributions can differ a lot in default software, "
                  "update policy and target audience.",
        },
        "ilgili": ["kernel", "paket_yoneticisi", "apt"],
    },
    {
        "id": "dosya_sistemi",
        "baslik": {"tr": "Dosya Sistemi", "en": "File System"},
        "kisa": {"tr": "Verilerin diskte nasıl saklanıp adlandırılacağını belirleyen yapı.",
                 "en": "The structure that decides how data is stored and named on disk."},
        "aciklama": {
            "tr": "Dosya sistemi; dosyaları, dizinleri, izinleri ve meta verileri diskte düzenli biçimde "
                  "tutan katmandır. Linux'ta en yaygın dosya sistemi ext4'tür; btrfs ve xfs gibi daha "
                  "gelişmiş alternatifler de kullanılır. Windows'un aksine Linux'ta tek bir sürücü harfi "
                  "yerine her şey tek bir kök dizinin (/) altında birleşir.",
            "en": "The file system is the layer that keeps files, directories, permissions and metadata "
                  "organized on disk. ext4 is the most common Linux file system, with more advanced "
                  "options like btrfs and xfs also in use. Unlike Windows drive letters, Linux merges "
                  "everything under a single root directory (/).",
        },
        "ilgili": ["kok_dizin", "fhs", "mount"],
    },
    {
        "id": "kok_dizin",
        "baslik": {"tr": "Kök Dizin (/)", "en": "Root Directory (/)"},
        "kisa": {"tr": "Linux dosya ağacının en tepesi; her şey buradan dallanır.",
                 "en": "The very top of the Linux file tree; everything branches from here."},
        "aciklama": {
            "tr": "\"/\" işareti kök dizini temsil eder ve dosya ağacının başlangıç noktasıdır. /home, "
                  "/etc, /usr gibi tüm diğer dizinler bunun altında yer alır. Kök kullanıcısının ev "
                  "dizini olan /root ile karıştırılmamalıdır -- ikisi tamamen farklı şeylerdir.",
            "en": "The \"/\" character represents the root directory, the starting point of the file "
                  "tree. Every other directory -- /home, /etc, /usr and the rest -- lives beneath it. "
                  "It should not be confused with /root, the home directory of the root user; the two "
                  "are entirely different things.",
        },
        "ornek": "ls /",
        "ilgili": ["dosya_sistemi", "fhs", "root_kullanici"],
    },
    {
        "id": "fhs",
        "baslik": {"tr": "FHS (Dosya Sistemi Hiyerarşisi Standardı)", "en": "FHS (Filesystem Hierarchy Standard)"},
        "kisa": {"tr": "Linux dizinlerinin ne işe yaradığını tanımlayan ortak kural kümesi.",
                 "en": "The shared convention that defines what each Linux directory is for."},
        "aciklama": {
            "tr": "FHS, /etc'nin yapılandırma dosyalarını, /var'ın değişken verileri (günlükler, "
                  "önbellekler), /usr'ın kurulu uygulamaları, /home'un kullanıcı dosyalarını "
                  "barındırması gibi kuralları tanımlar. Bu standart sayesinde farklı dağıtımlar "
                  "arasında bile bir dosyayı nerede arayacağınızı tahmin edebilirsiniz.",
            "en": "FHS defines conventions such as /etc holding configuration files, /var holding "
                  "variable data like logs and caches, /usr holding installed applications, and /home "
                  "holding user files. Because of this standard you can predict where to look for a "
                  "file even across different distributions.",
        },
        "ilgili": ["kok_dizin", "log_dosyasi", "dosya_sistemi"],
    },
    {
        "id": "dosya_izinleri",
        "baslik": {"tr": "Dosya İzinleri", "en": "File Permissions"},
        "kisa": {"tr": "Bir dosyayı kimin okuyabileceğini, yazabileceğini ve çalıştırabileceğini belirleyen kurallar.",
                 "en": "The rules that decide who may read, write or execute a given file."},
        "aciklama": {
            "tr": "Linux'ta her dosyanın bir sahibi, bir grubu ve üç izin kümesi vardır: sahip, grup ve "
                  "diğerleri için okuma (r), yazma (w) ve çalıştırma (x). `ls -l` çıktısındaki "
                  "\"rwxr-xr--\" gibi dizgiler bu üç kümeyi art arda gösterir. Sayısal gösterimde her "
                  "harf 4, 2 ve 1 değerlerine karşılık gelir; örneğin 755, sahibe tam yetki, diğerlerine "
                  "yalnızca okuma ve çalıştırma anlamına gelir.",
            "en": "Every Linux file has an owner, a group and three permission sets: read (r), write (w) "
                  "and execute (x) for the owner, the group and everyone else. Strings like "
                  "\"rwxr-xr--\" in `ls -l` output show these three sets in order. In numeric notation "
                  "each letter maps to 4, 2 and 1; 755, for example, means full rights for the owner and "
                  "read-plus-execute for everyone else.",
        },
        "ornek": "ls -l dosya.txt",
        "ilgili": ["chmod", "chown", "root_kullanici"],
    },
    {
        "id": "chmod",
        "baslik": {"tr": "chmod", "en": "chmod"},
        "kisa": {"tr": "Bir dosya ya da dizinin izinlerini değiştiren komut.",
                 "en": "The command that changes a file or directory's permissions."},
        "aciklama": {
            "tr": "chmod (change mode), dosya izinlerini sayısal (755, 644...) ya da sembolik (u+x, "
                  "g-w...) gösterimle değiştirmeye yarar. -R seçeneğiyle bir dizinin tüm içeriğine özyinelemeli "
                  "olarak uygulanabilir. Yanlış kullanıldığında -- örneğin sistem dosyalarına herkese yazma "
                  "izni vererek -- ciddi güvenlik açıkları doğurabilir.",
            "en": "chmod (change mode) changes file permissions either numerically (755, 644...) or "
                  "symbolically (u+x, g-w...). With -R it applies recursively to a directory's whole "
                  "contents. Misused -- say, by granting world write access to system files -- it can "
                  "open serious security holes.",
        },
        "ornek": "chmod 755 betik.sh",
        "ilgili": ["dosya_izinleri", "chown", "sudo"],
    },
    {
        "id": "chown",
        "baslik": {"tr": "chown", "en": "chown"},
        "kisa": {"tr": "Bir dosyanın sahibini ve/veya grubunu değiştiren komut.",
                 "en": "The command that changes a file's owner and/or group."},
        "aciklama": {
            "tr": "chown (change owner), genellikle yönetici yetkisiyle çalıştırılır ve bir dosyanın hangi "
                  "kullanıcıya ve hangi gruba ait olduğunu değiştirir. \"kullanici:grup\" biçiminde her "
                  "ikisi birden, ya da yalnızca biri belirtilebilir.",
            "en": "chown (change owner), usually run with administrator rights, changes which user and "
                  "group a file belongs to. It takes a \"user:group\" form where either part -- or "
                  "both -- can be specified.",
        },
        "ornek": "sudo chown carot:carot dosya.txt",
        "ilgili": ["chmod", "dosya_izinleri", "sudo"],
    },
    {
        "id": "sudo",
        "baslik": {"tr": "sudo", "en": "sudo"},
        "kisa": {"tr": "Yetkili (root) kullanıcı adına tek bir komutu çalıştırmayı sağlayan araç.",
                 "en": "The tool that runs a single command on behalf of the privileged (root) user."},
        "aciklama": {
            "tr": "sudo (\"superuser do\"), yetkili kullanıcılara kendi şifreleriyle geçici olarak kök "
                  "yetkisi kullanma imkânı verir; doğrudan root olarak oturum açmak yerine tercih edilen, "
                  "daha izlenebilir ve daha güvenli bir yöntemdir. Hangi kullanıcının hangi komutları sudo "
                  "ile çalıştırabileceği /etc/sudoers dosyasında tanımlanır.",
            "en": "sudo (\"superuser do\") lets authorized users temporarily run commands with root "
                  "privileges using their own password -- a more auditable and safer alternative to "
                  "logging in as root directly. Which users may run which commands with sudo is defined "
                  "in /etc/sudoers.",
        },
        "ornek": "sudo apt update",
        "ilgili": ["root_kullanici", "chmod", "paket_yoneticisi"],
    },
    {
        "id": "root_kullanici",
        "baslik": {"tr": "Root Kullanıcısı", "en": "Root User"},
        "kisa": {"tr": "Sistemdeki her şeye erişim yetkisi olan yönetici hesabı.",
                 "en": "The administrator account with unrestricted access to the whole system."},
        "aciklama": {
            "tr": "Root, Linux'ta izin denetimlerinin dışında kalan, her dosyayı okuyabilen, her süreci "
                  "sonlandırabilen ve sistemi her yönden değiştirebilen hesaptır. Bu nedenle günlük "
                  "işler için root olarak oturum açmak yerine sudo ile geçici yetki almak önerilir -- tek "
                  "bir yanlış komut tüm sistemi bozabilir.",
            "en": "Root is the account that bypasses permission checks entirely: it can read any file, "
                  "kill any process and change the system in any way. For everyday work it's recommended "
                  "to use sudo for temporary privilege rather than logging in as root -- a single wrong "
                  "command can break the whole system.",
        },
        "ilgili": ["sudo", "dosya_izinleri", "surec"],
    },
    {
        "id": "paket_yoneticisi",
        "baslik": {"tr": "Paket Yöneticisi", "en": "Package Manager"},
        "kisa": {"tr": "Yazılımları kurma, güncelleme ve kaldırma işini bağımlılıklarıyla birlikte yöneten araç.",
                 "en": "The tool that installs, updates and removes software along with its dependencies."},
        "aciklama": {
            "tr": "Paket yöneticisi, bir programı kurarken ihtiyaç duyduğu diğer kütüphaneleri (bağımlılıkları) "
                  "otomatik olarak bulup kurar, sürüm çakışmalarını yönetir ve güvenli güncellemeyi "
                  "kolaylaştırır. Debian ailesinde bu iş APT ve onun alt katmanı dpkg ile yapılır; "
                  "CarotOS da bunu doğrudan kullanır.",
            "en": "A package manager automatically finds and installs the other libraries (dependencies) "
                  "a program needs, manages version conflicts and makes safe updates easier. In the "
                  "Debian family this job is done by APT and its lower layer dpkg; CarotOS uses them "
                  "directly.",
        },
        "ilgili": ["apt", "dpkg", "dagitim"],
    },
    {
        "id": "apt",
        "baslik": {"tr": "APT", "en": "APT"},
        "kisa": {"tr": "Debian tabanlı sistemlerde paket kurmak, güncellemek ve kaldırmak için kullanılan komut satırı aracı.",
                 "en": "The command-line tool for installing, updating and removing packages on Debian-based systems."},
        "aciklama": {
            "tr": "APT (Advanced Package Tool), paket depolarından (repository) yazılım indirip kurar, "
                  "bağımlılıkları otomatik çözer. `apt update` depo listelerini tazeler, `apt upgrade` "
                  "kurulu paketleri günceller, `apt install` ise yeni bir paket kurar. CarotOS Panel'deki "
                  "güncelleme bildirimleri de perde arkasında APT'yi kullanır.",
            "en": "APT (Advanced Package Tool) downloads and installs software from repositories, "
                  "resolving dependencies automatically. `apt update` refreshes the repository lists, "
                  "`apt upgrade` updates installed packages, and `apt install` installs a new one. The "
                  "update notifications in CarotOS Panel use APT behind the scenes too.",
        },
        "ornek": "sudo apt install nmap",
        "ilgili": ["paket_yoneticisi", "dpkg", "paket"],
    },
    {
        "id": "dpkg",
        "baslik": {"tr": "dpkg", "en": "dpkg"},
        "kisa": {"tr": "Debian paketlerini (.deb) doğrudan kurup yöneten alt seviye araç.",
                 "en": "The low-level tool that installs and manages Debian (.deb) packages directly."},
        "aciklama": {
            "tr": "dpkg, .deb uzantılı tek bir paket dosyasıyla doğrudan çalışır ama APT'nin aksine "
                  "bağımlılıkları kendiliğinden indirip çözmez. Genellikle elle indirilmiş bir .deb "
                  "dosyasını kurarken ya da hangi paketlerin kurulu olduğunu listelerken kullanılır.",
            "en": "dpkg works directly with a single .deb package file but, unlike APT, does not fetch "
                  "and resolve dependencies on its own. It's typically used to install a manually "
                  "downloaded .deb file or to list which packages are currently installed.",
        },
        "ornek": "sudo dpkg -i paket.deb",
        "ilgili": ["apt", "paket_yoneticisi", "paket"],
    },
    {
        "id": "paket",
        "baslik": {"tr": "Paket (Package)", "en": "Package"},
        "kisa": {"tr": "Bir programı ve kurulum için gereken dosyalarını bir araya toplayan arşiv.",
                 "en": "An archive bundling a program and the files it needs to be installed."},
        "aciklama": {
            "tr": "Bir paket; çalıştırılabilir dosyaları, yapılandırma şablonlarını ve hangi diğer "
                  "paketlere ihtiyaç duyduğunu (bağımlılıklarını) açıklayan meta verileri içerir. Debian "
                  "ailesinde bu .deb biçimindedir; Fedora/RHEL ailesinde ise .rpm kullanılır.",
            "en": "A package contains executable files, configuration templates and metadata describing "
                  "which other packages it depends on. In the Debian family this is the .deb format; the "
                  "Fedora/RHEL family uses .rpm instead.",
        },
        "ilgili": ["paket_yoneticisi", "apt", "dpkg"],
    },
    {
        "id": "surec",
        "baslik": {"tr": "Süreç (Process)", "en": "Process"},
        "kisa": {"tr": "Çalışmakta olan bir programın işletim sistemindeki örneği.",
                 "en": "A running instance of a program within the operating system."},
        "aciklama": {
            "tr": "Bir program çalıştırıldığında işletim sistemi onun için bellek, bir kimlik numarası "
                  "(PID) ve işlemci zamanı ayırır; bu çalışan örneğe süreç denir. Aynı programın birden "
                  "fazla süreci aynı anda çalışabilir. `ps` ve `top` komutları çalışan süreçleri listeler.",
            "en": "When a program runs, the operating system allocates it memory, an identifier (PID) "
                  "and CPU time; this running instance is called a process. The same program can have "
                  "several processes running at once. The `ps` and `top` commands list running "
                  "processes.",
        },
        "ornek": "ps aux | grep firefox",
        "ilgili": ["pid", "kernel", "systemd"],
    },
    {
        "id": "pid",
        "baslik": {"tr": "PID (Süreç Kimliği)", "en": "PID (Process ID)"},
        "kisa": {"tr": "Çalışan her sürece çekirdek tarafından atanan benzersiz sayı.",
                 "en": "The unique number the kernel assigns to every running process."},
        "aciklama": {
            "tr": "Her süreç başladığında çekirdek ona bir PID atar; bu sayı süreci durdurmak "
                  "(`kill <pid>`), izlemek ya da başka bir süreçle ilişkilendirmek için kullanılır. "
                  "Sistemin ilk süreci olan init/systemd her zaman PID 1'i taşır.",
            "en": "The kernel assigns a PID to every process as it starts; this number is used to stop "
                  "it (`kill <pid>`), monitor it, or relate it to another process. The system's very "
                  "first process, init/systemd, always carries PID 1.",
        },
        "ornek": "kill 4821",
        "ilgili": ["surec", "systemd"],
    },
    {
        "id": "systemd",
        "baslik": {"tr": "systemd", "en": "systemd"},
        "kisa": {"tr": "Modern Linux dağıtımlarında sistem başlatmayı ve servisleri yöneten init sistemi.",
                 "en": "The init system that manages boot and services on modern Linux distributions."},
        "aciklama": {
            "tr": "systemd, açılışta hangi servislerin hangi sırayla başlatılacağını belirler, servisleri "
                  "çöktüğünde yeniden başlatabilir ve günlükleri journald ile toplar. `systemctl status`, "
                  "`systemctl start/stop/restart` ve `systemctl enable` en sık kullanılan komutlarıdır. "
                  "Debian 13 ve dolayısıyla CarotOS da systemd kullanır.",
            "en": "systemd decides which services start in what order at boot, can restart a crashed "
                  "service, and collects logs through journald. `systemctl status`, "
                  "`systemctl start/stop/restart` and `systemctl enable` are its most common commands. "
                  "Debian 13, and therefore CarotOS, uses systemd.",
        },
        "ornek": "sudo systemctl status ufw",
        "ilgili": ["surec", "pid", "log_dosyasi"],
    },
    {
        "id": "kabuk",
        "baslik": {"tr": "Kabuk (Shell)", "en": "Shell"},
        "kisa": {"tr": "Kullanıcının komutlar yazarak işletim sistemiyle konuştuğu program.",
                 "en": "The program through which a user talks to the operating system by typing commands."},
        "aciklama": {
            "tr": "Kabuk, yazılan komutları yorumlayıp çekirdeğe ileten ve sonucu gösteren arayüzdür. "
                  "Linux'ta en yaygın kabuk bash'tir; zsh ve fish gibi alternatifler de vardır. Grafik "
                  "arayüzün aksine kabuk, komutları betikler hâlinde birleştirip otomasyon kurmayı "
                  "kolaylaştırır.",
            "en": "A shell interprets typed commands, passes them to the kernel, and shows the result. "
                  "bash is the most common Linux shell, with alternatives like zsh and fish also in use. "
                  "Unlike a graphical interface, a shell makes it easy to chain commands into scripts and "
                  "build automation.",
        },
        "ilgili": ["bash", "terminal", "ortam_degiskeni"],
    },
    {
        "id": "bash",
        "baslik": {"tr": "Bash", "en": "Bash"},
        "kisa": {"tr": "Linux dağıtımlarında varsayılan olarak gelen, en yaygın kullanılan kabuk.",
                 "en": "The most widely used shell, the default on most Linux distributions."},
        "aciklama": {
            "tr": "Bash (\"Bourne Again Shell\"), tek satırlık komutlardan karmaşık otomasyon "
                  "betiklerine kadar her şeyi çalıştırabilen bir kabuk ve betik dilidir. Değişkenler, "
                  "döngüler, koşullar ve boru hattı (pipe, `|`) ile komutları zincirleme imkânı sunar.",
            "en": "Bash (\"Bourne Again Shell\") is both a shell and a scripting language, capable of "
                  "running everything from one-line commands to complex automation scripts. It supports "
                  "variables, loops, conditionals and chaining commands with pipes (`|`).",
        },
        "ornek": "for f in *.log; do echo \"$f\"; done",
        "ilgili": ["kabuk", "ortam_degiskeni", "grep"],
    },
    {
        "id": "ortam_degiskeni",
        "baslik": {"tr": "Ortam Değişkeni", "en": "Environment Variable"},
        "kisa": {"tr": "Süreçlere ayar bilgisi taşıyan, kabuk oturumuna bağlı isim-değer çifti.",
                 "en": "A name-value pair tied to a shell session that carries settings to processes."},
        "aciklama": {
            "tr": "PATH, HOME ve LANG gibi ortam değişkenleri; programların nerede çalıştırılabilir "
                  "dosya arayacağını, kullanıcının ev dizinini ya da arayüz dilini belirler. `export` "
                  "komutuyla tanımlanır ve o değişkeni tanımlayan kabuktan başlatılan tüm alt süreçlere "
                  "aktarılır.",
            "en": "Environment variables like PATH, HOME and LANG tell programs where to look for "
                  "executables, what the user's home directory is, or what language the interface "
                  "should use. They're set with `export` and passed down to every child process started "
                  "from that shell.",
        },
        "ornek": "export PATH=\"$HOME/bin:$PATH\"",
        "ilgili": ["kabuk", "bash"],
    },
    {
        "id": "symlink",
        "baslik": {"tr": "Sembolik Bağ (Symlink)", "en": "Symbolic Link (Symlink)"},
        "kisa": {"tr": "Başka bir dosyayı ya da dizini işaret eden, kendisi içerik taşımayan kısayol.",
                 "en": "A shortcut that points to another file or directory without holding content itself."},
        "aciklama": {
            "tr": "Sembolik bağ, hedefinin yolunu tutan küçük bir dosyadır; `ln -s` ile oluşturulur. "
                  "Hedef taşınır ya da silinirse bağ \"kırık\" (broken) hâle gelir. Sabit bağdan (hard "
                  "link) farkı, farklı dosya sistemleri arasında çalışabilmesi ve dizinleri de işaret "
                  "edebilmesidir.",
            "en": "A symlink is a small file that holds its target's path; it's created with `ln -s`. If "
                  "the target is moved or deleted, the link becomes \"broken\". Unlike a hard link, a "
                  "symlink can cross file systems and can point to directories too.",
        },
        "ornek": "ln -s /opt/carotos/gsd/carotos-gsd.py /usr/local/bin/carotos-gsd",
        "ilgili": ["dosya_sistemi", "mount"],
    },
    {
        "id": "mount",
        "baslik": {"tr": "Bağlama (Mount)", "en": "Mount"},
        "kisa": {"tr": "Bir diski ya da bölümü dosya ağacının bir noktasına ekleme işlemi.",
                 "en": "Attaching a disk or partition to a point in the file tree."},
        "aciklama": {
            "tr": "Linux'ta ayrı bir disk ya da USB bellek, Windows'taki gibi yeni bir sürücü harfi "
                  "almaz; bunun yerine var olan dosya ağacının bir dizinine \"bağlanır\" (mount edilir). "
                  "Örneğin bir USB bellek genelde /media/kullanici/... altına bağlanır. `umount` ile de "
                  "bağlantı güvenle kesilir.",
            "en": "In Linux a separate disk or USB drive doesn't get a new drive letter like in Windows; "
                  "instead it's \"mounted\" onto a directory within the existing file tree. A USB drive, "
                  "for example, typically mounts under /media/user/.... `umount` safely detaches it "
                  "again.",
        },
        "ornek": "mount | grep sda1",
        "ilgili": ["dosya_sistemi", "symlink"],
    },
    {
        "id": "grep",
        "baslik": {"tr": "grep", "en": "grep"},
        "kisa": {"tr": "Metin içinde kalıp (pattern) arayan komut satırı aracı.",
                 "en": "The command-line tool that searches text for a pattern."},
        "aciklama": {
            "tr": "grep, bir dosyada ya da başka bir komutun çıktısında (boru hattıyla) belirli bir "
                  "metni ya da düzenli ifadeyi (regex) arar ve eşleşen satırları gösterir. Günlük "
                  "dosyalarında hata ararken ya da büyük çıktıları süzerken en sık kullanılan araçlardan "
                  "biridir.",
            "en": "grep searches a file -- or another command's output via a pipe -- for a specific "
                  "string or regular expression, printing the matching lines. It's one of the most "
                  "common tools for hunting errors in logs or filtering large output.",
        },
        "ornek": "grep -i \"error\" /var/log/syslog",
        "ilgili": ["log_dosyasi", "bash"],
    },
    {
        "id": "cron",
        "baslik": {"tr": "Cron", "en": "Cron"},
        "kisa": {"tr": "Komutları belirli zamanlarda otomatik çalıştıran Linux zamanlayıcısı.",
                 "en": "The Linux scheduler that runs commands automatically at set times."},
        "aciklama": {
            "tr": "Cron, \"crontab\" adı verilen bir yapılandırma dosyasında tanımlanan görevleri -- "
                  "örneğin her gece bir yedekleme betiği -- belirtilen zaman diliminde otomatik çalıştırır. "
                  "Zamanlama dakika, saat, ayın günü, ay ve haftanın günü olmak üzere beş alanla ifade "
                  "edilir.",
            "en": "Cron automatically runs tasks defined in a \"crontab\" configuration file -- a nightly "
                  "backup script, say -- at a given schedule. The schedule is expressed with five "
                  "fields: minute, hour, day of month, month and day of week.",
        },
        "ornek": "0 3 * * * /opt/carotos/yedekle.sh",
        "ilgili": ["systemd", "surec"],
    },
    {
        "id": "log_dosyasi",
        "baslik": {"tr": "Günlük Dosyası (Log)", "en": "Log File"},
        "kisa": {"tr": "Bir programın ya da sistemin olaylarını zaman sırasıyla kaydettiği dosya.",
                 "en": "A file that records a program's or the system's events in time order."},
        "aciklama": {
            "tr": "Günlük dosyaları; hataları, uyarıları ve önemli olayları zaman damgasıyla kaydeder ve "
                  "bir sorunu sonradan araştırmanın temel yoludur. Çoğu sistem günlüğü /var/log altında "
                  "tutulur; systemd kullanan dağıtımlarda `journalctl` komutuyla da görüntülenebilir.",
            "en": "Log files record errors, warnings and important events with timestamps, and are the "
                  "main way to investigate a problem after the fact. Most system logs live under "
                  "/var/log; on systemd-based distributions they can also be viewed with `journalctl`.",
        },
        "ornek": "journalctl -u ssh -n 50",
        "ilgili": ["systemd", "grep", "fhs"],
    },
    {
        "id": "swap",
        "baslik": {"tr": "Takas Alanı (Swap)", "en": "Swap"},
        "kisa": {"tr": "Fiziksel bellek dolduğunda kullanılan, diskte ayrılmış yedek bellek alanı.",
                 "en": "Reserved disk space used as overflow memory once physical RAM fills up."},
        "aciklama": {
            "tr": "RAM dolduğunda çekirdek az kullanılan bellek sayfalarını diskteki takas alanına "
                  "taşıyarak sistemin çökmesini engeller; bu alan bir bölüm ya da bir dosya olabilir. "
                  "Disk, RAM'den çok daha yavaş olduğu için yoğun takas kullanımı sistemi fark edilir "
                  "şekilde yavaşlatır.",
            "en": "When RAM fills up, the kernel moves rarely used memory pages to swap space on disk to "
                  "keep the system from crashing; this space can be a partition or a file. Because disk "
                  "is far slower than RAM, heavy swap use noticeably slows the system down.",
        },
        "ornek": "free -h",
        "ilgili": ["kernel", "dosya_sistemi"],
    },
    {
        "id": "terminal",
        "baslik": {"tr": "Uçbirim (Terminal)", "en": "Terminal"},
        "kisa": {"tr": "Kullanıcının bir kabuğa komut yazdığı pencere uygulaması.",
                 "en": "The window application through which a user types commands to a shell."},
        "aciklama": {
            "tr": "Uçbirim (terminal emülatörü), klavyeden girilen metni bir kabuğa iletir ve kabuğun "
                  "çıktısını ekranda gösterir. Eskiden fiziksel bir donanım olan terminal, günümüzde "
                  "masaüstündeki bir pencere uygulamasıdır -- CarotOS'ta da Xfce Terminal bu işi görür.",
            "en": "A terminal (terminal emulator) sends keyboard input to a shell and displays the "
                  "shell's output on screen. Once a physical piece of hardware, a terminal today is a "
                  "window application on the desktop -- in CarotOS, Xfce Terminal does this job.",
        },
        "ilgili": ["kabuk", "bash"],
    },
]
