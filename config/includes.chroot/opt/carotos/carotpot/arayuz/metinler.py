# -*- coding: utf-8 -*-
"""CarotPot arayuz metinleri. Her anahtar Turkce ve Ingilizce icerir;
yer tutucular ({ad}) iki dilde aynidir (test denetler)."""

M = {
    # --- genel / kabuk ------------------------------------------------------
    "marka_alt": {"tr": "Yerel ağ tuzağı · {surum}", "en": "Local network trap · {surum}"},
    "bolum_izleme": {"tr": "İzleme", "en": "Monitoring"},
    "bolum_sistem": {"tr": "Sistem", "en": "System"},
    "alt_bilgi": {"tr": "CarotOS · CarotPot {surum}", "en": "CarotOS · CarotPot {surum}"},
    "gorunum_koyu": {"tr": "Koyu", "en": "Dark"},
    "gorunum_acik": {"tr": "Açık", "en": "Light"},
    "hap_acik": {"tr": "Tuzak açık · {n} tuzak · {sure}", "en": "Trap on · {n} traps · {sure}"},
    "hap_kapali": {"tr": "Tuzak kapalı", "en": "Trap off"},
    "hap_hata": {"tr": "Tuzak açık · {n} tuzak açılamadı", "en": "Trap on · traps failed: {n}"},
    "baslat": {"tr": "Başlat", "en": "Start"},
    "durdur": {"tr": "Durdur", "en": "Stop"},
    "sure_dk": {"tr": "{dk} dk", "en": "{dk} min"},
    "sure_sa": {"tr": "{sa} sa {dk} dk", "en": "{sa} h {dk} min"},
    "sure_gun": {"tr": "{gun} gün {sa} sa", "en": "{gun} d {sa} h"},
    "az_once": {"tr": "az önce", "en": "just now"},
    "dk_once": {"tr": "{n} dk önce", "en": "{n} min ago"},
    "sa_once": {"tr": "{n} sa önce", "en": "{n} h ago"},
    "gun_once": {"tr": "{n} gün önce", "en": "{n} days ago"},
    "iptal": {"tr": "İptal", "en": "Cancel"},
    "kaydet": {"tr": "Kaydet", "en": "Save"},
    "kaldir": {"tr": "Kaldır", "en": "Remove"},
    "evet_kaldir": {"tr": "Kaldır", "en": "Remove"},
    "tumu": {"tr": "Tümü", "en": "All"},
    "bilinmiyor": {"tr": "bilinmiyor", "en": "unknown"},
    "rastgele_mac": {"tr": "Rastgele MAC (gizlilik)", "en": "Randomised MAC (privacy)"},
    "olay_n": {"tr": "{n} olay", "en": "{n} events"},
    "seviye_yuksek": {"tr": "Yüksek", "en": "High"},
    "seviye_orta": {"tr": "Orta", "en": "Medium"},
    "seviye_dusuk": {"tr": "Düşük", "en": "Low"},
    "risk": {"tr": "risk", "en": "risk"},
    "engelli": {"tr": "ENGELLİ", "en": "BLOCKED"},
    "baslatiliyor": {"tr": "Tuzak açılıyor…", "en": "Turning the trap on…"},
    "durduruluyor": {"tr": "Tuzak kapatılıyor…", "en": "Turning the trap off…"},
    "baslatildi": {"tr": "Tuzak açıldı.", "en": "The trap is on."},
    "durduruldu": {"tr": "Tuzak kapatıldı.", "en": "The trap is off."},
    "baslat_onay_baslik": {"tr": "Tuzak açılsın mı?", "en": "Turn the trap on?"},
    "baslat_onay": {
        "tr": "Bu bilgisayarda sahte hizmetler açılacak ve güvenlik duvarında bu "
              "portlara izin verilecek. Yalnızca güvendiğiniz ağlarda (ev, okul "
              "laboratuvarı) açın; kafe, otel gibi ortak ağlarda açmayın. Gerçek "
              "bir kabuk ya da hizmet yoktur; her giriş denemesi reddedilir.",
        "en": "Fake services will be opened on this computer and the firewall will "
              "allow these ports. Turn it on only on networks you trust (home, school "
              "lab); not on shared networks such as cafés or hotels. There is no real "
              "shell or service; every login attempt is rejected."},

    # --- islem sonuclari ----------------------------------------------------
    "k___TAMAM__": {"tr": "İşlem tamamlandı.", "en": "Done."},
    "k___IPTAL__": {"tr": "İşlem iptal edildi.", "en": "The operation was cancelled."},
    "k___KORUNAN_ADRES__": {
        "tr": "Bu adres ağ geçidi, bu bilgisayarın kendi adresi ya da hiç "
              "engellenmeyecekler listesinde olduğu için engellenmedi.",
        "en": "This address was not blocked because it is the gateway, this "
              "computer's own address or on the never-block list."},
    "k___GECERSIZ_IP__": {"tr": "Geçersiz adres.", "en": "Invalid address."},
    "k___GECERSIZ_SURE__": {"tr": "Geçersiz süre.", "en": "Invalid duration."},
    "k___UFW_KAPALI__": {
        "tr": "Güvenlik duvarı kapalı olduğu için engelleme yapılamadı. Sistem "
              "Sağlığı'ndan açılabilir.",
        "en": "Blocking was not possible because the firewall is off. It can be "
              "turned on in System Health."},
    "k___AYAR_HATASI__": {"tr": "Ayarlar geçersiz: {ayrinti}", "en": "Invalid settings: {ayrinti}"},
    "k___BASLATILAMADI__": {"tr": "Tuzak başlatılamadı.", "en": "The trap could not be started."},
    "k___FAIL2BAN_HATASI__": {"tr": "fail2ban yeniden yüklenemedi.",
                              "en": "fail2ban could not be reloaded."},
    "k_genel": {"tr": "İşlem başarısız oldu.", "en": "The operation failed."},

    # --- pano ---------------------------------------------------------------
    "pano": {"tr": "Pano", "en": "Dashboard"},
    "pano_alt": {"tr": "Ağdaki tuzak etkinliğinin canlı özeti",
                 "en": "Live summary of trap activity on the network"},
    "pano_kapali": {
        "tr": "Tuzak kapalı. Açtığınızda yerel ağda bu bilgisayarı tarayan ya da "
              "giriş deneyen cihazlar burada görünür. Sistem açılışında "
              "kendiliğinden başlamaz.",
        "en": "The trap is off. When you turn it on, devices on the local network "
              "that scan this computer or try to log in appear here. It does not "
              "start automatically at boot."},
    "pano_hata": {"tr": "Açılamayan tuzaklar: {liste}. Port başka bir program tarafından "
                        "kullanılıyor olabilir; Tuzaklar sayfasından değiştirilebilir.",
                  "en": "Traps that could not be opened: {liste}. The port may be in use "
                        "by another program; it can be changed on the Traps page."},
    "kpi_olay": {"tr": "Olay · son 24 saat", "en": "Events · last 24 hours"},
    "kpi_kaynak": {"tr": "Benzersiz kaynak", "en": "Unique sources"},
    "kpi_giris": {"tr": "Giriş denemesi", "en": "Login attempts"},
    "kpi_engel": {"tr": "Engellenen adres", "en": "Blocked addresses"},
    "fark_yuzde": {"tr": "{y}%{n}", "en": "{y}{n}%"},
    "fark_yeni": {"tr": "▲ {n} yeni", "en": "▲ {n} new"},
    "f2b_acik": {"tr": "otomatik açık", "en": "automatic on"},
    "f2b_kapali": {"tr": "otomatik kapalı", "en": "automatic off"},
    "saatlik": {"tr": "Saatlik etkinlik", "en": "Hourly activity"},
    "saatlik_alt": {"tr": "Son 24 saat · renk yoğunluğu gösterir",
                    "en": "Last 24 hours · colour shows intensity"},
    "saatlik_bos": {"tr": "Son 24 saatte olay yok", "en": "No events in the last 24 hours"},
    "tuzak_basina": {"tr": "Tuzak başına olay", "en": "Events per trap"},
    "etkin_saldirganlar": {"tr": "En etkin saldırganlar", "en": "Most active attackers"},
    "canli_akis": {"tr": "Canlı akış", "en": "Live feed"},
    "canli": {"tr": "CANLI", "en": "LIVE"},
    "akis_bos": {"tr": "Henüz olay yok: ağda tuzaklara dokunan olmadı.",
                 "en": "No events yet: nobody on the network has touched the traps."},
    "saldirgan_bos": {"tr": "Son 24 saatte kaynak yok.", "en": "No sources in the last 24 hours."},

    # --- olay turleri (akis) --------------------------------------------------
    "tur_giris": {"tr": "Giriş denemesi", "en": "Login attempt"},
    "tur_baglanti": {"tr": "Bağlantı", "en": "Connection"},
    "tur_istek": {"tr": "Web isteği", "en": "Web request"},
    "tur_tarama": {"tr": "Port taraması", "en": "Port scan"},
    "tur_komut": {"tr": "Komut", "en": "Command"},

    # --- saldirganlar --------------------------------------------------------
    "saldirgan": {"tr": "Saldırganlar", "en": "Attackers"},
    "saldirgan_baslik": {"tr": "Saldırgan profili", "en": "Attacker profile"},
    "saldirgan_alt": {"tr": "Kaynak başına davranış, kimlik bilgileri ve risk",
                      "en": "Behaviour, credentials and risk per source"},
    "kaynaklar_n": {"tr": "Kaynaklar · {n}", "en": "Sources · {n}"},
    "pencere_24": {"tr": "24 saat", "en": "24 h"},
    "pencere_7": {"tr": "7 gün", "en": "7 days"},
    "pencere_tum": {"tr": "Tümü", "en": "All"},
    "profil_bos_baslik": {"tr": "Henüz saldırgan yok", "en": "No attackers yet"},
    "profil_bos": {"tr": "Tuzaklara dokunan ilk cihaz burada profiliyle görünür.",
                   "en": "The first device that touches the traps appears here with its profile."},
    "risk_rozet": {"tr": "{seviye} RİSK", "en": "{seviye} RISK"},
    "cihaz_satiri": {"tr": "{uretici} (MAC {mac}) · {ad}", "en": "{uretici} (MAC {mac}) · {ad}"},
    "cihaz_yok": {"tr": "Cihaz bilgisi yok (komşu tablosunda değil)",
                  "en": "No device info (not in the neighbour table)"},
    "zaman_satiri": {"tr": "İlk görülme {ilk} · son görülme {son} · {n} olay, {giris} giriş denemesi",
                     "en": "First seen {ilk} · last seen {son} · {n} events, {giris} login attempts"},
    "davranis_satiri": {"tr": "Davranış: {liste}", "en": "Behaviour: {liste}"},
    "not_satiri": {"tr": "Not: {metin}", "en": "Note: {metin}"},
    "engelle": {"tr": "Engelle", "en": "Block"},
    "engeli_kaldir": {"tr": "Engeli kaldır", "en": "Unblock"},
    "sureli_engelle": {"tr": "Süreli engelle", "en": "Block for…"},
    "yok_say": {"tr": "Yok say", "en": "Ignore"},
    "not_ekle": {"tr": "Not ekle", "en": "Add note"},
    "not_duzenle": {"tr": "Notu düzenle", "en": "Edit note"},
    "not_baslik": {"tr": "{ip} için not", "en": "Note for {ip}"},
    "not_aciklama": {"tr": "Yalnızca bu bilgisayarda, sizin hesabınızda saklanır.",
                     "en": "Stored only on this computer, in your account."},
    "zaman_cizelgesi": {"tr": "Zaman çizelgesi", "en": "Timeline"},
    "zaman_alt": {"tr": "Her nokta bir olay; tuzaklara göre", "en": "Each dot is an event; by trap"},
    "denenen_kullanicilar": {"tr": "Denenen kullanıcı adları", "en": "Attempted usernames"},
    "denenen_parolalar": {"tr": "Denenen parolalar · maskeli", "en": "Attempted passwords · masked"},
    "denenen_parolalar_acik": {"tr": "Denenen parolalar", "en": "Attempted passwords"},
    "goster": {"tr": "Göster", "en": "Show"},
    "gizle": {"tr": "Gizle", "en": "Hide"},
    "liste_bos": {"tr": "Kayıt yok", "en": "None recorded"},
    "web_istekleri": {"tr": "İstenen web yolları", "en": "Requested web paths"},
    "komutlar": {"tr": "Gönderilen komutlar", "en": "Commands sent"},
    "engel_onay_baslik": {"tr": "{ip} engellensin mi?", "en": "Block {ip}?"},
    "engel_onay": {
        "tr": "Bu adresten gelen tüm bağlantılar güvenlik duvarında reddedilecek. "
              "Adres tanıdığınız bir cihaza aitse (öğretmen bilgisayarı, yazıcı) "
              "engellemeyin; “Yok say” seçeneğini kullanın.",
        "en": "All connections from this address will be rejected by the firewall. "
              "If the address belongs to a device you know (teacher computer, "
              "printer), do not block it; use “Ignore” instead."},
    "engel_sure": {"tr": "Süre", "en": "Duration"},
    "sure_15dk": {"tr": "15 dakika", "en": "15 minutes"},
    "sure_1sa": {"tr": "1 saat", "en": "1 hour"},
    "sure_6sa": {"tr": "6 saat", "en": "6 hours"},
    "sure_24sa": {"tr": "24 saat", "en": "24 hours"},
    "sure_7gun": {"tr": "7 gün", "en": "7 days"},
    "sure_suresiz": {"tr": "Süresiz", "en": "Indefinite"},
    "engellendi": {"tr": "{ip} engellendi.", "en": "{ip} has been blocked."},
    "engel_kalkti": {"tr": "{ip} engeli kaldırıldı.", "en": "{ip} has been unblocked."},
    "yoksay_onay_baslik": {"tr": "{ip} yok sayılsın mı?", "en": "Ignore {ip}?"},
    "yoksay_onay": {
        "tr": "Bu adresten gelen bağlantılar artık kaydedilmeyecek ve "
              "bildirilmeyecek; adres hiç engellenmeyecekler listesine eklenir. "
              "Engelleme sayfasından geri alınabilir.",
        "en": "Connections from this address will no longer be recorded or "
              "reported; it is added to the never-block list. This can be undone "
              "on the Blocking page."},
    "yoksayildi": {"tr": "{ip} yok sayılıyor.", "en": "{ip} is now ignored."},
    "parola_yok": {"tr": "Bu kaynak için kayıtlı parola yok.",
                   "en": "No passwords recorded for this source."},

    # --- davranislar ----------------------------------------------------------
    "d_kaba_kuvvet": {"tr": "kaba kuvvet (sözlük saldırısı)", "en": "brute force (dictionary attack)"},
    "d_giris_denemesi": {"tr": "giriş denemesi", "en": "login attempt"},
    "d_anahtar_denemesi": {"tr": "SSH anahtarı denemesi", "en": "SSH key attempt"},
    "d_port_tarama": {"tr": "port taraması", "en": "port scan"},
    "d_iot_botu": {"tr": "IoT botu (Mirai benzeri)", "en": "IoT bot (Mirai-like)"},
    "d_web_tarama": {"tr": "web açığı taraması", "en": "web vulnerability scan"},
    "d_redis_istismar": {"tr": "Redis istismar denemesi", "en": "Redis exploitation attempt"},
    "d_veritabani": {"tr": "veritabanı giriş denemesi", "en": "database login attempt"},

    # --- tuzaklar ---------------------------------------------------------------
    "tuzak": {"tr": "Tuzaklar", "en": "Traps"},
    "tuzak_alt": {"tr": "Her tuzak bir modül; kimliğini ve portunu seçin",
                  "en": "Each trap is a module; choose its identity and port"},
    "port": {"tr": "Port", "en": "Port"},
    "kimlik": {"tr": "Kimlik", "en": "Identity"},
    "t_calisiyor": {"tr": "çalışıyor", "en": "running"},
    "t_mesgul": {"tr": "port meşgul", "en": "port in use"},
    "t_kapali": {"tr": "kapalı", "en": "off"},
    "t_bekliyor": {"tr": "tuzak kapalı", "en": "trap off"},
    "t_basliksiz": {"tr": "yalnız karşılama (asyncssh yok)", "en": "banner only (no asyncssh)"},
    "degisiklik_var": {"tr": "Kaydedilmemiş değişiklikler var. Tuzak açıksa uygulanınca "
                             "yeniden başlatılır.",
                       "en": "There are unsaved changes. If the trap is on, it is "
                             "restarted when they are applied."},
    "geri_al": {"tr": "Geri al", "en": "Revert"},
    "uygula": {"tr": "Uygula", "en": "Apply"},
    "ayar_kaydedildi": {"tr": "Ayarlar kaydedildi.", "en": "Settings saved."},
    "port_cakisma": {"tr": "Port {port} birden fazla tuzakta kullanılıyor.",
                     "en": "Port {port} is used by more than one trap."},
    "en_az_bir": {"tr": "En az bir tuzak açık olmalı.", "en": "At least one trap must be on."},
    "tuzak_not": {
        "tr": "Tuzaklar yalnızca yerel ağ adreslerinden gelen bağlantıları kaydeder. "
              "Portlar 1024–65535 arasında olmalıdır; yetki gerektirmeyen yüksek "
              "portlar kullanılır.",
        "en": "Traps record connections only from local network addresses. Ports "
              "must be between 1024 and 65535; high ports that need no privileges "
              "are used."},

    # --- kanarya ------------------------------------------------------------------
    "kanarya": {"tr": "Kanarya dosyalar", "en": "Canary files"},
    "kanarya_alt": {"tr": "Yem dosyalarla yerel erişimi yakalayın",
                    "en": "Catch local access with decoy files"},
    "kanarya_kart_alt": {
        "tr": "Gerçek görünen yem dosyalar. Biri açarsa, değiştirirse ya da silerse "
              "anında uyarı gelir. Ağ dışından gelen tehditleri (USB, zararlı "
              "yazılım, başkasının oturumu) de yakalar.",
        "en": "Real-looking decoy files. If someone opens, changes or deletes one, "
              "you are alerted at once. Also catches threats that do not come over "
              "the network (USB, malware, someone else's session)."},
    "kanarya_ekle": {"tr": "Kanarya ekle", "en": "Add canary"},
    "k_izleniyor": {"tr": "İZLENİYOR", "en": "WATCHING"},
    "k_tetiklendi": {"tr": "TETİKLENDİ", "en": "TRIGGERED"},
    "k_kayip": {"tr": "KAYIP", "en": "MISSING"},
    "k_beklemede": {"tr": "BEKLEMEDE", "en": "PAUSED"},
    "k_hic": {"tr": "Hiç açılmadı", "en": "Never opened"},
    "k_tetik": {"tr": "{zaman} · {tur}", "en": "{zaman} · {tur}"},
    "k_tetik_surec": {"tr": "{zaman} · {tur} · süreç: {surec}",
                      "en": "{zaman} · {tur} · process: {surec}"},
    "kt_acildi": {"tr": "açıldı", "en": "opened"},
    "kt_degisti": {"tr": "değiştirildi", "en": "modified"},
    "kt_silindi": {"tr": "silindi", "en": "deleted"},
    "kt_tasindi": {"tr": "taşındı", "en": "moved"},
    "kanarya_bos_baslik": {"tr": "Henüz kanarya yok", "en": "No canaries yet"},
    "kanarya_bos": {"tr": "Bir şablon seçerek ilk yem dosyanızı oluşturun.",
                    "en": "Choose a template to create your first decoy file."},
    "sablonlar": {"tr": "Şablonlar", "en": "Templates"},
    "sablonlar_alt": {"tr": "İçerik sahte ama inandırıcı üretilir; gerçek bilgi içermez.",
                      "en": "Content is fake but convincing; it contains no real information."},
    "son_tetiklenmeler": {"tr": "Son tetiklenmeler", "en": "Recent triggers"},
    "izleyici_kapali": {
        "tr": "Kanarya izleyicisi çalışmıyor; dosyalar şu an izlenmiyor.",
        "en": "The canary watcher is not running; files are not being watched."},
    "izleyiciyi_baslat": {"tr": "İzlemeyi başlat", "en": "Start watching"},
    "kanarya_not": {
        "tr": "İzleme oturumunuzda çalışır ve oturum açıldığında kendiliğinden "
              "başlar. Dosya yöneticisinin önizleme ve küçük resim işlemleri "
              "tetikleme sayılmaz. Dosyayı açan süreç, aynı kullanıcıya aitse "
              "gösterilir.",
        "en": "Watching runs in your session and starts automatically when you log "
              "in. File manager previews and thumbnails do not count as triggers. "
              "The process that opened the file is shown if it belongs to the same "
              "user."},
    "kanarya_ekle_baslik": {"tr": "Kanarya dosya ekle", "en": "Add a canary file"},
    "sablon": {"tr": "Şablon", "en": "Template"},
    "klasor": {"tr": "Klasör", "en": "Folder"},
    "dosya_adi": {"tr": "Dosya adı", "en": "File name"},
    "olustur": {"tr": "Oluştur", "en": "Create"},
    "kanarya_eklendi": {"tr": "“{ad}” oluşturuldu ve izleniyor.",
                        "en": "“{ad}” was created and is being watched."},
    "dosya_var": {"tr": "Bu klasörde aynı adlı bir dosya zaten var.",
                  "en": "A file with this name already exists in this folder."},
    "kanarya_hata": {"tr": "Kanarya oluşturulamadı: {hata}", "en": "Could not create the canary: {hata}"},
    "kanarya_kaldir_baslik": {"tr": "“{ad}” kaldırılsın mı?", "en": "Remove “{ad}”?"},
    "kanarya_kaldir_onay": {"tr": "Yem dosya silinir ve artık izlenmez.",
                            "en": "The decoy file is deleted and no longer watched."},

    # --- engelleme -------------------------------------------------------------
    "engel": {"tr": "Engelleme", "en": "Blocking"},
    "engel_baslik": {"tr": "Engelleme merkezi", "en": "Blocking centre"},
    "engel_alt": {"tr": "Onaylı engeller, süreler ve koruma listesi",
                  "en": "Approved blocks, durations and the protection list"},
    "kpi_etkin_engel": {"tr": "Etkin engel", "en": "Active blocks"},
    "kpi_yakin_bitis": {"tr": "En yakın bitiş", "en": "Next expiry"},
    "kpi_otomatik": {"tr": "Otomatik engelleme", "en": "Automatic blocking"},
    "acik": {"tr": "Açık", "en": "On"},
    "kapali": {"tr": "Kapalı", "en": "Off"},
    "oner_onay": {"tr": "öner → onay", "en": "suggest → approve"},
    "fail2ban": {"tr": "fail2ban", "en": "fail2ban"},
    "engellenen_adresler": {"tr": "Engellenen adresler", "en": "Blocked addresses"},
    "adres_engelle": {"tr": "Adres engelle", "en": "Block address"},
    "s_adres": {"tr": "Adres", "en": "Address"},
    "s_neden": {"tr": "Neden", "en": "Reason"},
    "s_baslangic": {"tr": "Başlangıç", "en": "Start"},
    "s_bitis": {"tr": "Bitiş", "en": "Ends"},
    "s_yontem": {"tr": "Yöntem", "en": "Method"},
    "elle_ufw": {"tr": "Elle · ufw", "en": "Manual · ufw"},
    "suresiz": {"tr": "Süresiz", "en": "Indefinite"},
    "suresi_doldu": {"tr": "süresi doldu", "en": "expired"},
    "engel_bos": {"tr": "Engellenmiş adres yok.", "en": "No blocked addresses."},
    "neden_yok": {"tr": "—", "en": "—"},
    "hic_engellenmeyecek": {"tr": "Hiç engellenmeyecekler", "en": "Never blocked"},
    "hic_alt": {"tr": "Kendini kilitleme koruması", "en": "Self-lockout protection"},
    "otomatik": {"tr": "OTOMATİK", "en": "AUTOMATIC"},
    "elle": {"tr": "ELLE", "en": "MANUAL"},
    "ag_gecidi": {"tr": "ağ geçidi", "en": "gateway"},
    "bu_bilgisayar": {"tr": "bu bilgisayar", "en": "this computer"},
    "adres_ekle": {"tr": "Ekle", "en": "Add"},
    "adres_ornek": {"tr": "ör. 192.168.1.12", "en": "e.g. 192.168.1.12"},
    "gecersiz_adres": {"tr": "Geçersiz adres: {ip}", "en": "Invalid address: {ip}"},
    "otomatik_baslik": {"tr": "Otomatik engelleme (fail2ban)", "en": "Automatic blocking (fail2ban)"},
    "otomatik_aciklama": {
        "tr": "Açıkken 10 dakikada 3 olay üreten kaynak 1 saat engellenir. Kapalı "
              "gelir: yanlış bir adresin (ağ geçidi, öğretmen bilgisayarı) "
              "engellenmesi ağ bağlantısını kesebilir. Hiç engellenmeyecekler "
              "listesi bu durumda da geçerlidir.",
        "en": "When on, a source that produces 3 events in 10 minutes is blocked "
              "for 1 hour. It comes off: blocking a wrong address (gateway, teacher "
              "computer) may cut the network connection. The never-block list "
              "applies in this case too."},
    "ufw_kapali": {
        "tr": "Güvenlik duvarı (ufw) kapalı. Tuzak çalışır, ancak engelleme "
              "yapılamaz. Sistem Sağlığı'ndan açılabilir.",
        "en": "The firewall (ufw) is off. The trap works, but blocking is not "
              "possible. It can be turned on in System Health."},
    "engel_adres_baslik": {"tr": "Adres engelle", "en": "Block an address"},
    "engel_adres_metin": {"tr": "Engellenecek IP adresini ve süreyi seçin.",
                          "en": "Enter the IP address to block and choose a duration."},

    # --- raporlar -------------------------------------------------------------------
    "rapor": {"tr": "Raporlar", "en": "Reports"},
    "rapor_alt": {"tr": "Dönemsel özet; HTML ve CSV olarak dışa aktarılır",
                  "en": "Periodic summary; exported as HTML and CSV"},
    "donem": {"tr": "Dönem", "en": "Period"},
    "d_bugun": {"tr": "Bugün", "en": "Today"},
    "d_7": {"tr": "Son 7 gün", "en": "Last 7 days"},
    "d_30": {"tr": "Son 30 gün", "en": "Last 30 days"},
    "d_ozel": {"tr": "Özel aralık", "en": "Custom range"},
    "html_rapor": {"tr": "HTML rapor oluştur", "en": "Create HTML report"},
    "csv_aktar": {"tr": "CSV dışa aktar", "en": "Export CSV"},
    "rapor_kaydedildi": {"tr": "Rapor kaydedildi: {yol}", "en": "Report saved: {yol}"},
    "kaydedilemedi": {"tr": "Dosya kaydedilemedi: {hata}", "en": "Could not save the file: {hata}"},
    "ozel_aralik_baslik": {"tr": "Rapor aralığı", "en": "Report range"},
    "ozel_aralik_metin": {"tr": "Başlangıç ve bitiş gününü seçin.",
                          "en": "Choose the first and last day."},
    "rapor_on_baslik": {"tr": "CarotPot raporu · {aralik}", "en": "CarotPot report · {aralik}"},
    "rapor_on_alt": {"tr": "{ag} · CarotOS · rapor önizlemesi", "en": "{ag} · CarotOS · report preview"},
    "yerel_ag": {"tr": "Yerel ağ", "en": "Local network"},
    "veri_notu": {"tr": "Olay günlüğü {gun} günden eski kayıtları tutmaz.",
                  "en": "The event log does not keep records older than {gun} days."},
    "r_baslik": {"tr": "CarotPot raporu", "en": "CarotPot report"},
    "r_toplam": {"tr": "Toplam olay", "en": "Total events"},
    "r_kaynak": {"tr": "Kaynak", "en": "Sources"},
    "r_giris": {"tr": "Giriş denemesi", "en": "Login attempts"},
    "r_yeni_kaynak": {"tr": "Yeni kaynak", "en": "New sources"},
    "r_one_cikanlar": {"tr": "Öne çıkanlar", "en": "Highlights"},
    "r_etkinlik": {"tr": "Etkinlik", "en": "Activity"},
    "r_kaynaklar": {"tr": "Kaynaklar", "en": "Sources"},
    "r_adres": {"tr": "Adres", "en": "Address"},
    "r_cihaz": {"tr": "Cihaz", "en": "Device"},
    "r_olay": {"tr": "Olay", "en": "Events"},
    "r_tuzaklar": {"tr": "Tuzaklar", "en": "Traps"},
    "r_risk": {"tr": "Risk", "en": "Risk"},
    "r_davranis": {"tr": "Davranış", "en": "Behaviour"},
    "r_tuzak_basina": {"tr": "Tuzak başına olay", "en": "Events per trap"},
    "r_kullanicilar": {"tr": "En çok denenen kullanıcı adları", "en": "Most tried usernames"},
    "r_sakin": {"tr": "Bu dönemde dikkat çeken bir hareket yok.",
                "en": "Nothing notable happened in this period."},
    "r_dipnot": {"tr": "Parolalar raporda yer almaz. Bu rapor CarotOS CarotPot ile bu "
                       "bilgisayarda oluşturuldu; hiçbir veri dışarı gönderilmedi.",
                 "en": "Passwords are not included. This report was generated by CarotOS "
                       "CarotPot on this computer; no data was sent anywhere."},
    "oc_saldirgan": {"tr": "{ip} ({cihaz}) {n} olay üretti: {davranis}.",
                     "en": "{ip} ({cihaz}) produced {n} events: {davranis}."},
    "oc_kullanicilar": {"tr": " En çok denenen kullanıcı adları: {liste}.",
                        "en": " Most tried usernames: {liste}."},
    "oc_iot": {"tr": "{ip} Telnet'e IoT botu desenleriyle bağlandı; cihazın parolası "
                     "değiştirilmeli ya da yazılımı güncellenmeli.",
               "en": "{ip} connected to Telnet with IoT-bot patterns; the device's password "
                     "should be changed or its firmware updated."},
    "oc_kanarya": {"tr": "“{ad}” kanaryası {zaman} tarihinde {tur}.",
                   "en": "The “{ad}” canary {tur} on {zaman}."},
    "oc_yeni": {"tr": "Bu dönemde {n} yeni kaynak görüldü.", "en": "{n} new sources were seen in this period."},
    "oc_artis": {"tr": "Olay sayısı önceki döneme göre %{n} arttı.",
                 "en": "Events rose by {n}% compared with the previous period."},
    "oc_azalis": {"tr": "Olay sayısı önceki döneme göre %{n} azaldı.",
                  "en": "Events fell by {n}% compared with the previous period."},
    "html_filtre": {"tr": "HTML belgesi", "en": "HTML document"},
    "csv_filtre": {"tr": "CSV tablosu", "en": "CSV table"},

    # --- ag haritasi -------------------------------------------------------------
    "ag": {"tr": "Ağ haritası", "en": "Network map"},
    "ag_alt": {"tr": "Yerel ağdaki cihazlar ve tuzakla ilişkileri",
               "en": "Devices on the local network and their relation to the trap"},
    "yerel_ag_kart": {"tr": "Yerel ağ", "en": "Local network"},
    "ag_kart_alt": {"tr": "Komşu tablosundan görülen {n} cihaz · tuzağa dokunanlar işaretli",
                    "en": "{n} devices seen in the neighbour table · those that touched the trap are marked"},
    "yenile": {"tr": "Yenile", "en": "Refresh"},
    "agi_yokla": {"tr": "Ağı yokla", "en": "Probe network"},
    "yokla_ipucu": {"tr": "Yerel ağdaki her adrese bir ping gönderir; böylece sessiz "
                          "cihazlar da haritada görünür (yaklaşık 10 saniye).",
                    "en": "Sends one ping to every address on the local network so that "
                          "quiet devices also appear on the map (about 10 seconds)."},
    "yoklaniyor": {"tr": "Ağ yoklanıyor…", "en": "Probing the network…"},
    "yoklandi": {"tr": "{n} cihaz yanıt verdi.", "en": "{n} devices responded."},
    "gosterim": {"tr": "Gösterim", "en": "Legend"},
    "g_saldirgan": {"tr": "Saldırgan (giriş denedi)", "en": "Attacker (tried to log in)"},
    "g_supheli": {"tr": "Şüpheli (tarama)", "en": "Suspicious (scan)"},
    "g_gecit": {"tr": "Ağ geçidi", "en": "Gateway"},
    "g_normal": {"tr": "Normal cihaz", "en": "Normal device"},
    "secili": {"tr": "Seçili: {ad}", "en": "Selected: {ad}"},
    "secim_yok": {"tr": "Ayrıntı için haritada bir cihaza tıklayın.",
                  "en": "Click a device on the map for details."},
    "profili_ac": {"tr": "Profili aç", "en": "Open profile"},
    "bu_pc": {"tr": "Bu PC", "en": "This PC"},
    "tuzaga_dokundu": {"tr": "{n} olay · son {son}", "en": "{n} events · last {son}"},
    "tuzaga_dokunmadi": {"tr": "Tuzağa dokunmadı", "en": "Has not touched the trap"},
    "ag_bos": {"tr": "Komşu tablosu boş. “Ağı yokla” ile cihazları bulabilirsiniz.",
               "en": "The neighbour table is empty. Use “Probe network” to find devices."},
    "ve_fazlasi": {"tr": "+{n} cihaz daha", "en": "+{n} more devices"},

    # --- ayarlar ------------------------------------------------------------------------
    "ayar": {"tr": "Ayarlar", "en": "Settings"},
    "ayar_alt": {"tr": "Bildirimler, kayıtlar ve görünüm", "en": "Notifications, records and appearance"},
    "bildirimler": {"tr": "Bildirimler", "en": "Notifications"},
    "bekleme": {"tr": "Aynı kaynak için bildirimler arası süre (dakika)",
                "en": "Time between alerts for the same source (minutes)"},
    "webhook": {"tr": "Webhook adresi (isteğe bağlı, https)", "en": "Webhook address (optional, https)"},
    "webhook_not": {"tr": "Doldurulursa uyarılar bu adrese gönderilir. Boş bırakılırsa hiçbir "
                          "veri bilgisayardan dışarı gönderilmez.",
                    "en": "If filled in, alerts are sent to this address. If left empty, no data "
                          "leaves the computer."},
    "kayitlar": {"tr": "Kayıtlar", "en": "Records"},
    "sakla_gun": {"tr": "Olayların saklanacağı süre (gün)", "en": "How long events are kept (days)"},
    "dakikada_olay": {"tr": "Kaynak başına dakikada en fazla kayıt",
                      "en": "Maximum records per source per minute"},
    "gorunum": {"tr": "Görünüm", "en": "Appearance"},
    "dil": {"tr": "Dil", "en": "Language"},
    "tema": {"tr": "Tema", "en": "Theme"},
    "hakkinda": {"tr": "Hakkında", "en": "About"},
    "hakkinda_metin": {
        "tr": "CarotPot bu bilgisayarda sahte hizmetler açar. Gerçek bir kullanıcının "
              "bunlara bağlanması için neden yoktur; bu nedenle her bağlantı şüphelidir. "
              "Gerçek bir kabuk ya da hizmet yoktur; her giriş denemesi reddedilir. "
              "Hizmet yetkisiz bir kullanıcıyla, kısıtlı bir sistem biriminde çalışır ve "
              "yalnızca yerel ağ adreslerinden gelen bağlantıları kaydeder. Parolalar "
              "günlükte maskelidir.",
        "en": "CarotPot opens fake services on this computer. A real user has no reason "
              "to connect to them, so every connection is suspicious. There is no real "
              "shell or service; every login attempt is rejected. The service runs as an "
              "unprivileged user in a restricted system unit and records connections only "
              "from local network addresses. Passwords are masked in the log."},
    "kaydedilecek": {"tr": "Bildirim ve kayıt ayarları yönetici onayıyla kaydedilir. Dil ve "
                           "tema hemen uygulanır.",
                     "en": "Notification and record settings are saved with administrator "
                           "approval. Language and theme apply immediately."},
}

# Olay turu -> metin anahtari
TUR = {"giris": "tur_giris", "baglanti": "tur_baglanti", "istek": "tur_istek",
       "tarama": "tur_tarama", "komut": "tur_komut"}
