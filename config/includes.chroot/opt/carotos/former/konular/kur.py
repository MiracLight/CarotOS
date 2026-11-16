# -*- coding: utf-8 -*-
"""CarotOS'u kurmak: canli masaustunden Calamares kurucusuyla kurulum (dil, konum, klavye, bolumler, kullanici, ozet)."""
from former_sahneler import PH, PW, _yan
from former_zaman import T, balon, bekle, git, ilerle, sec, tikla, yaz

X0 = 196            # sag taraftaki sayfa alaninin sol kenari
GEN = 552           # sag sayfa alani genisligi


def _ileri(onceki, sonraki, **ek):
    """Ileri dugmesine basip bir sonraki sayfaya gecis (sol listede secili adim da degisir)."""
    ayar = {"k:" + onceki: {"aktif": False}, "k:" + sonraki: {"aktif": True}}
    ayar.update(ek.pop("ayarla", {}))
    return tikla("k_ileri", sayfa=sonraki, ayarla=ayar, **ek)


def _baslik(onek, sayfa, baslik, alt):
    return [
        {"id": onek + "_baslik", "tur": "metin", "x": X0, "y": 34, "w": GEN, "h": 20, "sayfa": sayfa,
         "metin": baslik, "boyut": 14, "kalin": True},
        {"id": onek + "_alt", "tur": "metin", "x": X0, "y": 58, "w": GEN, "h": 14, "sayfa": sayfa,
         "boyut": 8.4, "renk": "soluk", "metin": alt},
    ]


def _etiket(kimlik, sayfa, x, y, w, metin):
    return {"id": kimlik, "tur": "metin", "x": x, "y": y, "w": w, "h": 14, "sayfa": sayfa, "boyut": 8,
            "renk": "soluk", "metin": metin}


def _sahne():
    menu = [("k:dil", T("Hoş geldin", "Welcome"), "ev"),
            ("k:konum", T("Konum", "Location"), "ag"),
            ("k:klavye", T("Klavye", "Keyboard"), "ayar"),
            ("k:bolumler", T("Bölümler", "Partitions"), "dosya"),
            ("k:kullanici", T("Kullanıcı", "Users"), "kisi"),
            ("k:ozet", T("Özet", "Summary"), "liste"),
            ("k:kurulum", T("Kurulum", "Install"), "indir"),
            ("k:bitti", T("Bitiş", "Finish"), "onay")]
    o = _yan(T("CarotOS", "CarotOS"), T("Kurulum", "Installer"), menu, adim=26, y0=72,
             genislik=176, baslangic_aktif="k:dil")
    for e in o:
        if e["tur"] == "menu":
            e["boyut"] = 8
    # --- hos geldin / dil
    o += _baslik("d", "dil", T("Hoş geldin", "Welcome"), T("Kurulum bu dilde yapılır.", "The installation runs in this language."))
    o += [
        _etiket("d_et", "dil", X0, 92, 300, T("Dil", "Language")),
        {"id": "k_dil", "tur": "secim", "x": X0, "y": 108, "w": 300, "h": 28, "sayfa": "dil",
         "secenekler": ["English", "Türkçe", "Deutsch", "Español", "Français"]},
        {"id": "d_not", "tur": "metin", "x": X0, "y": 250, "w": GEN, "h": 46, "sayfa": "dil", "sar": True,
         "boyut": 8.4, "renk": "soluk",
         "metin": T("Canlı oturum İngilizce olsa bile dili burada seçersin. Kurulum internet olmadan da çalışır.",
                    "Even if the live session is in English, you pick the language here. The installation also "
                    "works without internet.")},
    ]
    # --- konum
    o += _baslik("n", "konum", T("Neredesin?", "Where are you?"),
                 T("Saat dilimini seç.", "Pick your time zone."))
    o += [
        _etiket("n_et1", "konum", X0, 92, 200, T("Bölge", "Region")),
        _etiket("n_et2", "konum", X0 + 212, 92, 200, T("Saat dilimi", "Time zone")),
        {"id": "n_bolge", "tur": "alan", "x": X0, "y": 108, "w": 200, "h": 28, "sayfa": "konum",
         "deger": "Europe"},
        {"id": "n_dilim", "tur": "alan", "x": X0 + 212, "y": 108, "w": 200, "h": 28, "sayfa": "konum",
         "deger": "Istanbul"},
        {"id": "n_not", "tur": "metin", "x": X0, "y": 156, "w": GEN, "h": 34, "sayfa": "konum", "sar": True,
         "boyut": 8.4, "renk": "soluk",
         "metin": T("Varsayılan İstanbul'dur; başka bir yerdeysen değiştir.",
                    "Istanbul is the default; change it if you are somewhere else.")},
    ]
    # --- klavye
    o += _baslik("y", "klavye", T("Klavye düzeni", "Keyboard layout"),
                 T("Klavyene uyan düzeni seç.", "Pick the layout that matches your keyboard."))
    o += [
        _etiket("y_et1", "klavye", X0, 92, 300, T("Düzen", "Layout")),
        {"id": "y_duzen", "tur": "secim", "x": X0, "y": 108, "w": 300, "h": 28, "sayfa": "klavye",
         "secenekler": ["English (US)", "Turkish (Q)", "Turkish (F)", "German"]},
        _etiket("y_et2", "klavye", X0, 210, 400, T("Denemek için buraya yaz", "Type here to test it")),
        {"id": "y_test", "tur": "alan", "x": X0, "y": 226, "w": 300, "h": 28, "sayfa": "klavye", "deger": ""},
    ]
    # --- bolumler
    o += _baslik("b", "bolumler", T("Diski nasıl kullanalım?", "How should we use the disk?"),
                 T("Bir seçenek seç.", "Pick an option."))
    o += [
        {"id": "b_kart", "tur": "kart", "x": X0 - 2, "y": 90, "w": GEN + 4, "h": 124, "sayfa": "bolumler"},
        {"id": "b_sil", "tur": "satir", "x": X0 + 6, "y": 98, "w": GEN - 12, "h": 34, "sayfa": "bolumler",
         "renk": "silik",
         "metin": T("Diski sil ve CarotOS'u kur", "Erase disk and install CarotOS")},
        {"id": "b_yan", "tur": "satir", "x": X0 + 6, "y": 136, "w": GEN - 12, "h": 34, "sayfa": "bolumler",
         "renk": "silik",
         "metin": T("Mevcut sistemin yanına kur (örn. Windows)", "Install alongside another system (e.g. Windows)")},
        {"id": "b_elle", "tur": "satir", "x": X0 + 6, "y": 174, "w": GEN - 12, "h": 34, "sayfa": "bolumler",
         "renk": "silik", "metin": T("Elle bölümle", "Manual partitioning")},
        {"id": "b_not", "tur": "metin", "x": X0, "y": 222, "w": GEN, "h": 42, "sayfa": "bolumler", "sar": True,
         "boyut": 8.4, "renk": "soluk",
         "metin": T("Önce önemli dosyalarının yedeğini al.", "Back up your important files first.")},
        {"id": "b_sifre", "tur": "anahtar", "x": X0, "y": 268, "w": 40, "h": 22, "sayfa": "bolumler",
         "aktif": False},
        {"id": "b_sifre_et", "tur": "metin", "x": X0 + 52, "y": 272, "w": GEN - 56, "h": 14, "sayfa": "bolumler",
         "boyut": 8.6,
         "metin": T("Diski şifrele (açılışta parola sorulur)", "Encrypt the disk (a password is asked at boot)")},
        {"id": "b_sifre_not", "tur": "metin", "x": X0, "y": 304, "w": GEN, "h": 30, "sayfa": "bolumler",
         "bayrak": "sifre", "sar": True, "boyut": 8.4, "renk": "sari",
         "metin": T("Şifre parolasını unutursan verilerin kurtarılamaz.",
                    "If you forget the encryption password, your data cannot be recovered.")},
    ]
    # --- kullanici
    o += _baslik("u", "kullanici", T("Sen kimsin?", "Who are you?"),
                 T("Giriş için bir kullanıcı adı ve parola belirle.", "Choose a user name and password to log in."))
    o += [
        _etiket("u_et1", "kullanici", X0, 90, 330, T("Adın", "Your name")),
        {"id": "u_ad", "tur": "alan", "x": X0, "y": 106, "w": 330, "h": 28, "sayfa": "kullanici", "deger": ""},
        _etiket("u_et2", "kullanici", X0, 142, 330, T("Bilgisayarın adı", "Computer name")),
        {"id": "u_bilgisayar", "tur": "alan", "x": X0, "y": 158, "w": 330, "h": 28, "sayfa": "kullanici",
         "deger": "carotos"},
        _etiket("u_et3", "kullanici", X0, 194, 330, T("Parola (en az 8 karakter)", "Password (at least 8 characters)")),
        {"id": "u_parola", "tur": "alan", "x": X0, "y": 210, "w": 330, "h": 28, "sayfa": "kullanici", "deger": ""},
        _etiket("u_et4", "kullanici", X0, 246, 330, T("Parolayı tekrar yaz", "Repeat the password")),
        {"id": "u_parola2", "tur": "alan", "x": X0, "y": 262, "w": 330, "h": 28, "sayfa": "kullanici",
         "deger": ""},
        {"id": "u_kart", "tur": "kart", "x": X0 + 346, "y": 106, "w": 206, "h": 184, "sayfa": "kullanici"},
        {"id": "u_kart_metin", "tur": "metin", "x": X0 + 358, "y": 118, "w": 182, "h": 160, "sayfa": "kullanici",
         "sar": True, "boyut": 8.2,
         "metin": T("Bu kullanıcı sudo ile yönetici işlerini yapabilir. Root girişi kilitli kalır. "
                    "Bilgisayar adı varsayılan olarak carotos'tur.",
                    "This user can do administrator tasks with sudo. Root login stays locked. The computer "
                    "name is carotos by default.")},
    ]
    # --- ozet
    o += _baslik("o", "ozet", T("Özet", "Summary"), T("Yapılacakları gözden geçir.", "Review what is about to happen."))
    ozet_satirlar = [
        T("Dil: Türkçe", "Language: Turkish"),
        T("Saat dilimi: Europe/Istanbul", "Time zone: Europe/Istanbul"),
        T("Klavye: Turkish (Q)", "Keyboard: Turkish (Q)"),
        T("Disk: Windows'un yanına kur, şifreleme açık", "Disk: install alongside Windows, encryption on"),
        T("Kullanıcı: ayse (sudo), bilgisayar adı: carotos", "User: ayse (sudo), computer name: carotos"),
    ]
    o.append({"id": "o_kart", "tur": "kart", "x": X0 - 2, "y": 90, "w": GEN + 4, "h": 156, "sayfa": "ozet"})
    for i, m in enumerate(ozet_satirlar):
        o.append({"id": "o_s%d" % i, "tur": "metin", "x": X0 + 12, "y": 104 + i * 28, "w": GEN - 24, "h": 16,
                  "sayfa": "ozet", "boyut": 8.8, "metin": m})
    o.append({"id": "o_not", "tur": "metin", "x": X0, "y": 262, "w": GEN, "h": 30, "sayfa": "ozet", "sar": True,
              "boyut": 8.4, "renk": "soluk",
              "metin": T("“Kur”a bastığında diske yazma başlar.", "Writing to the disk starts when you press “Install”.")})
    # --- kurulum
    o += _baslik("i", "kurulum", T("Kuruluyor…", "Installing…"),
                 T("Bu sırada slaytlar gösterilir.", "Slides are shown meanwhile."))
    o += [
        {"id": "i_bar", "tur": "ilerleme", "x": X0, "y": 92, "w": GEN, "h": 14, "sayfa": "kurulum"},
        {"id": "i_durum", "tur": "metin", "x": X0, "y": 114, "w": GEN, "h": 14, "sayfa": "kurulum", "boyut": 8.2,
         "renk": "soluk", "metin": T("Dosyalar kopyalanıyor…", "Copying files…")},
        {"id": "i_kart", "tur": "kart", "x": X0 - 2, "y": 142, "w": GEN + 4, "h": 120, "sayfa": "kurulum"},
        {"id": "i_slayt_baslik", "tur": "metin", "x": X0 + 12, "y": 156, "w": GEN - 24, "h": 20, "sayfa": "kurulum",
         "boyut": 12, "kalin": True, "renk": "vurgu_yazi", "metin": T("On seçilmiş araç", "Ten chosen tools")},
        {"id": "i_slayt_metin", "tur": "metin", "x": X0 + 12, "y": 184, "w": GEN - 24, "h": 80, "sayfa": "kurulum",
         "sar": True, "boyut": 8.8,
         "metin": T("Ağ tarama, paket analizi, parola denetimi, web güvenliği ve savunma: her aracın ne işe "
                    "yaradığı ve nasıl kullanıldığı Karşılama uygulamasında adım adım anlatılır.",
                    "Network scanning, packet analysis, password auditing, web security and defence: what every "
                    "tool does and how to use it is explained step by step in the Welcome app.")},
        {"id": "i_not", "tur": "metin", "x": X0, "y": 276, "w": GEN, "h": 30, "sayfa": "kurulum", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("Canlı oturum çalışmaya devam eder; beklerken tarayıcıda gezebilirsin.",
                    "The live session keeps working; you can browse the web while you wait.")},
    ]
    # --- bitti
    o += _baslik("f", "bitti", T("Her şey tamam", "All done"),
                 T("CarotOS bilgisayarına kuruldu.", "CarotOS has been installed on your computer."))
    o += [
        {"id": "f_anahtar", "tur": "anahtar", "x": X0, "y": 100, "w": 40, "h": 22, "sayfa": "bitti", "aktif": True},
        {"id": "f_et", "tur": "metin", "x": X0 + 52, "y": 104, "w": GEN - 56, "h": 14, "sayfa": "bitti",
         "boyut": 8.8, "metin": T("Şimdi yeniden başlat", "Restart now")},
        {"id": "f_not", "tur": "metin", "x": X0, "y": 144, "w": GEN, "h": 44, "sayfa": "bitti", "sar": True,
         "boyut": 8.4, "renk": "soluk",
         "metin": T("USB belleği çıkar. Yeniden başlayınca sistem diskten açılır ve ilk girişte Karşılama sihirbazı açılır.",
                    "Remove the USB stick. After the restart the system boots from the disk and the Welcome "
                    "wizard opens on first login.")},
    ]
    # --- alt dugmeler (her sayfada)
    o += [
        {"id": "k_iptal", "tur": "dugme", "x": X0, "y": 382, "w": 96, "h": 28, "metin": T("İptal", "Cancel")},
        {"id": "k_geri", "tur": "dugme", "x": 520, "y": 382, "w": 100, "h": 28, "metin": T("Geri", "Back")},
        {"id": "k_ileri", "tur": "dugme", "x": 632, "y": 382, "w": 116, "h": 28, "birincil": True,
         "metin": T("İleri", "Next")},
    ]
    return {"genislik": PW, "yukseklik": PH, "vurgu": "karsilama", "sayfa": "dil",
            "baslik": T("CarotOS'u Kur", "Install CarotOS"), "ogeler": o}


def konu():
    adimlar = [
        balon("d_baslik", T("Masaüstündeki kurulum simgesi", "The installer icon on the desktop"),
              T("Canlı masaüstünde “CarotOS'u Kur” simgesine çift tıklayınca bu pencere açılır. Şu an hiçbir şey "
                "diske yazılmıyor; sen ilerlemeden bir şey değişmez.",
                "Double-click the “Install CarotOS” icon on the live desktop and this window opens. Nothing is "
                "written to the disk yet; nothing changes until you go on."), "alt"),
        git("k:ozet"),
        balon("k:ozet", T("Soldaki liste", "The list on the left"),
              T("Sol taraf yolun haritasıdır: dil, konum, klavye, bölümler, kullanıcı, özet, kurulum, bitiş. "
                "Hangi adımda olduğunu buradan görürsün.",
                "The left side is the map of the way: language, location, keyboard, partitions, user, summary, "
                "install, finish. You see which step you are on."), "sag"),
        sec("k_dil", 1),
        balon("k_dil", T("Dili seç", "Pick the language"),
              T("Canlı oturum İngilizce olsa bile kurulum için istediğin dili burada seçersin.",
                "Even if the live session is in English, you choose the installation language here."), "alt"),
        _ileri("dil", "konum"),
        git("n_dilim"),
        balon("n_dilim", T("Saat dilimi", "Time zone"),
              T("Varsayılan İstanbul'dur. Başka bir yerdeysen bölgeyi ve şehri değiştir; saat ona göre ayarlanır.",
                "The default is Istanbul. If you are somewhere else, change the region and the city; the clock is set "
                "accordingly."), "alt"),
        _ileri("konum", "klavye"),
        sec("y_duzen", 1),
        git("y_test"),
        yaz("y_test", "ğüşiöçı"),
        balon("y_test", T("Klavyeyi dene", "Try the keyboard"),
              T("Buraya yazıp özel harflerin doğru çıktığına bak. Çıkmıyorsa düzeni değiştir.",
                "Type here and check that special letters come out right. If they don't, change the layout."),
              "ust"),
        _ileri("klavye", "bolumler"),
        balon("b_kart", T("Disk için üç yol", "Three ways to use the disk"),
              T("“Diski sil” diskteki her şeyi siler. “Yanına kur” boş alan kullanır, mevcut sistemi silmez. "
                "“Elle” ise bölümleri kendin düzenlersin. Dokunmadan önce yedek al.",
                "“Erase disk” deletes everything on the disk. “Install alongside” uses free space and keeps the "
                "existing system. “Manual” lets you arrange the partitions yourself. Back up before you touch "
                "anything."), "sag"),
        git("b_yan"),
        tikla("b_yan", ayarla={"b_yan": {"renk": "vurgu", "vurgulu": True},
                               "b_not": {"metin": T("Boş alanı kullanır; Windows silinmez. Önce Windows'ta bölümü küçültmeni isteyebilir.",
                                                    "Uses free space; Windows is not deleted. You may need to shrink "
                                                    "the Windows partition first.")}}),
        balon("b_not", T("Yanına kurulum", "Installing alongside"),
              T("Windows'un yanına kurulumda diskteki Windows kalır. Ne olacağı bu satırda yazar.",
                "When installing next to Windows, the Windows on the disk stays. What will happen is written on "
                "this line."), "alt"),
        git("b_sifre"),
        tikla("b_sifre", bayrak={"sifre": True}),
        balon("b_sifre_not", T("Disk şifreleme", "Disk encryption"),
              T("Açık olursa disk parolasız okunamaz. Ama parolayı unutursan verilerin geri getirilemez; "
                "bu yüzden parolayı güvenli bir yere yaz.",
                "If on, the disk can't be read without the password. But if you forget it, your data can't be "
                "brought back; write the password down somewhere safe."), "ust"),
        _ileri("bolumler", "kullanici"),
        balon("u_kart_metin", T("sudo ve root", "sudo and root"),
              T("Oluşturduğun kullanıcı sudo ile yönetici işleri yapabilir. Root hesabının girişi kilitli kalır. "
                "Bilgisayarın adı carotos'tur.",
                "The user you create can do administrator tasks with sudo. The root account stays locked for login. "
                "The computer name is carotos."), "sol"),
        _ileri("kullanici", "ozet", ayarla={"k_ileri": {"metin": T("Kur", "Install")}}),
        balon("o_kart", T("Son bakış", "A last look"),
              T("Seçtiklerin burada toplanır. Yanlış bir şey görürsen “Geri” ile döner, düzeltirsin. "
                "“Kur”a basana kadar diske hiçbir şey yazılmaz.",
                "Everything you chose is gathered here. If something is wrong, go “Back” and fix it. Nothing is "
                "written to the disk until you press “Install”."), "alt"),
        git("k_ileri"),
        tikla("k_ileri", sayfa="kurulum",
              ayarla={"k:ozet": {"aktif": False}, "k:kurulum": {"aktif": True},
                      "k_ileri": {"metin": T("İleri", "Next"), "pasif": True}, "k_geri": {"pasif": True}}),
        ilerle("i_bar", 0.55, 1800),
        balon("i_kart", T("Kurulum sürerken", "While it installs"),
              T("Kurulum bir süre sürer; bu arada slaytlar gösterilir. Canlı oturum çalışmaya devam eder, "
                "internet de gerekmez.",
                "The installation takes a while; slides are shown meanwhile. The live session keeps working "
                "and no internet is needed."), "alt"),
        ilerle("i_bar", 1.0, 1500),
        bekle(300),
        tikla("k_ileri", sayfa="bitti",
              ayarla={"k:kurulum": {"aktif": False}, "k:bitti": {"aktif": True},
                      "k_ileri": {"metin": T("Bitir", "Done"), "pasif": False}}),
        balon("f_anahtar", T("Yeniden başlat", "Restart"),
              T("Kurulum bitince bilgisayarı yeniden başlat ve USB belleği çıkar. Sistem artık diskten açılır.",
                "When the installation ends, restart the computer and remove the USB stick. The system now boots "
                "from the disk."), "alt"),
    ]
    bolumler = [
        (T("CarotOS'u kurmak", "Installing CarotOS"), [
            ("p", T("Canlı oturumda CarotOS'u diske yazmadan deneyebilirsin. Beğenirsen masaüstündeki “CarotOS'u Kur” "
                    "simgesiyle bilgisayarına kurarsın; kurulum sırasında canlı oturum çalışmaya devam eder ve "
                    "internet gerekmez. Kurulu sistemde kurucu ve canlı oturum paketleri bulunmaz.",
                    "In the live session you can try CarotOS without writing anything to the disk. If you like it, "
                    "install it with the “Install CarotOS” icon on the desktop; the live session keeps working "
                    "during the installation and no internet is needed. The installed system does not contain the "
                    "installer or the live-session packages.")),
        ]),
        (T("Adımlar", "The steps"), [
            ("liste", [
                T("Dil: kurulumun dilini seç (canlı oturum İngilizce olsa bile).",
                  "Language: pick the installation language (even if the live session is in English)."),
                T("Konum: saat dilimini seç, varsayılan İstanbul'dur.",
                  "Location: pick the time zone; the default is Istanbul."),
                T("Klavye: düzeni seç ve kutuda dene.", "Keyboard: pick the layout and test it in the box."),
                T("Bölümler: diski sil, mevcut sistemin yanına kur ya da elle bölümle; istersen disk şifrelemeyi aç.",
                  "Partitions: erase the disk, install alongside the existing system or partition by hand; turn on "
                  "disk encryption if you like."),
                T("Kullanıcı: kullanıcı adı ve parola belirle. Bu kullanıcı sudo kullanır, root girişi kilitli "
                  "kalır, bilgisayar adı carotos olur.",
                  "User: choose a user name and password. This user gets sudo, root login stays locked, and the "
                  "computer name is carotos."),
                T("Özet: yapılacakları gözden geçir ve “Kur”a bas.", "Summary: review what will happen and press “Install”."),
                T("Kurulum: slaytlar gösterilirken beklersin; bitince bilgisayarı yeniden başlat.",
                  "Install: wait while slides are shown; when it ends, restart the computer."),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Diske dokunmadan önce önemli dosyalarının yedeğini al: “Diski sil” diskteki her şeyi "
                        "siler. Windows'un yanına kuracaksan Karşılama'daki “Windows ile birlikte” sayfasındaki "
                        "hazırlıkları yap. Disk şifreleme parolasını unutursan verilerin kurtarılamaz.",
                        "Back up your important files before touching the disk: “Erase disk” deletes everything on "
                        "it. If you will install next to Windows, follow the preparations on the “Alongside "
                        "Windows” page in Welcome. If you forget the disk encryption password, your data cannot "
                        "be recovered.")),
        ]),
        (T("Kurucu açılmazsa", "If the installer fails"), [
            ("p", T("Kurucu açılmazsa ya da takılırsa bilgisayarı yeniden başlat ve USB açılış menüsünde eski metin "
                    "tabanlı Debian kurucusunu seç; o yedek olarak durur.",
                    "If the installer doesn't open or gets stuck, restart the computer and choose the older "
                    "text-based Debian installer in the USB boot menu; it stays there as a fallback.")),
        ]),
    ]
    return {
        "id": "kur", "grup": "baslarken", "ikon": "indir", "ad": T("CarotOS'u kurmak", "Installing CarotOS"),
        "alt": T("Canlı masaüstünden diske kur", "Install to disk from the live desktop"),
        "ozet": T("Canlı masaüstünden adım adım kurulum: dil, bölümler, kullanıcı.",
                  "Step-by-step installation from the live desktop: language, partitions, user."),
        "vurgu": "karsilama", "sahne": _sahne(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": None, "root": False,
    }
