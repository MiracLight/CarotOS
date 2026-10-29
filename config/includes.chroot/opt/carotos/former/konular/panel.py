# -*- coding: utf-8 -*-
"""Guvenlik Paneli'nin genel tanitimi: gezinme, arac sayfasi yapisi, root akisi, ayarlar."""
from former_zaman import T, balon, git, sec, tikla
from konular._panel import PANEL_KOMUT, konu as _konu
from konular.nmap import ARAC as NMAP_ARAC


def konu():
    adimlar = [
        balon("yan", T("Araç listesi", "The tool list"),
              T("Solda Güvenlik Paneli'nin 10 aracı sırayla durur. Her biri ayrı bir işe yarar; birine "
                "tıklayınca sağda o aracın sayfası açılır. Bu sayfalar hep aynı düzeni kullanır, o yüzden "
                "bir tanesini öğrenince hepsini bilirsin.",
                "On the left stand the Security Panel's 10 tools in order. Each does a different job; click "
                "one and its page opens on the right. These pages all share the same layout, so learning one "
                "means you know them all."), "sag"),
        tikla("arac:nmap", sayfa="arac"),
        balon("a_bilgi", T("Üstteki bilgi kartı", "The info card on top"),
              T("Her araç sayfasının tepesinde üç satır var: ne yaptığı, ne zaman kullanılacağı ve bir "
                "örnek. Bir aracı ilk kez açtığında önce bunu oku; ne yapacağını bilmeden çalıştırma.",
                "Every tool page starts with three lines: what it does, when to use it, and an example. The "
                "first time you open a tool, read this before anything else; do not run it without knowing "
                "what it will do.")),
        balon("alan:target", T("Alanlar", "The fields"),
              T("Altında aracın istediği bilgileri doldurduğun alanlar var: bir metin, bir dosya seçimi ya "
                "da bir açılır liste olabilir. Her alanın solunda ne istediğini söyleyen bir etiket vardır.",
                "Below that are the fields where you fill in what the tool needs: a text box, a file picker, "
                "or a dropdown. Each field has a label on its left saying what it wants.")),
        balon("btn:calistir", T("Çalıştır ve Root ile çalıştır", "Run and Run as root"),
              T("Çalıştır, aracı senin normal kullanıcı yetkinle başlatır. Bazı araçlar (ağ dinleme, "
                "güvenlik duvarı gibi) daha yüksek yetki ister; böyle bir araçta sarı bir not görürsün ve "
                "“Root ile çalıştır”ı kullanman gerekir. O zaman küçük bir parola penceresi açılır; "
                "parolanı sadece o pencereye, bir kez girersin.",
                "Run starts the tool with your normal user rights. Some tools (listening on the network, the "
                "firewall) need higher rights; on those you see a yellow note and must use “Run as root”. "
                "That opens a small password dialog; you type your password there, once.")),
        git("cikti"),
        balon("cikti", T("Canlı çıktı", "The live output"),
              T("Araç çalışırken ürettiği satırlar alttaki kutuda canlı akar; gerçek bir terminal gibi. Uzun "
                "sürecek bir işi “Durdur”la her an kesebilirsin. “Çıktıyı temizle” kutuyu boşaltır, aracı "
                "etkilemez.",
                "While the tool runs, its output streams live in the box below, like a real terminal. You "
                "can stop a long job any time with “Stop”. “Clear output” empties the box without affecting "
                "the tool.")),
        tikla("menu:ayar", sayfa="ayar"),
        balon("s_dil", T("Dil ve tema", "Language and theme"),
              T("Ayarlar sayfasında panelin dilini ve koyu/açık temasını değiştirebilirsin. Bu seçim yalnızca "
                "Güvenlik Paneli'ni etkiler, diğer CarotOS uygulamalarını değil.",
                "On the Settings page you can change the panel's language and its dark/light theme. This "
                "choice affects only the Security Panel, not the other CarotOS apps.")),
        tikla("s_fw_ani", ayarla={"s_fw_durum": {"metin": T("Açık", "Enabled")}}),
        balon("s_fw_ani", T("Güvenlik duvarı anahtarı", "The firewall switch"),
              T("Bu anahtar, sistemdeki güvenlik duvarını (ufw) tek tıkla açıp kapatır — ufw konusunda "
                "gördüğün “Etkinleştir” işleminin kısayolu gibi düşün. Açarken SSH ile uzaktan bağlıysan "
                "önce 22 portuna izin verdiğinden emin ol.",
                "This switch turns the system firewall (ufw) on or off with one click — think of it as a "
                "shortcut for the “Enable” action you saw in the ufw topic. If you are connected remotely "
                "over SSH, make sure port 22 is allowed before you turn it on.")),
    ]
    bolumler = [
        (T("Güvenlik Paneli nedir", "What the Security Panel is"), [
            ("p", T("Güvenlik Paneli, CarotOS'un terminale yazılan güvenlik araçlarını tek bir pencerede "
                    "toplayan arayüzüdür. Her araç için ne yazman gerektiğini ezberlemek yerine, formu "
                    "doldurur ve Çalıştır'a basarsın; panel komutu senin için kurar ve ekranda gösterir.",
                    "The Security Panel is CarotOS's interface that gathers terminal-based security tools "
                    "into a single window. Instead of memorising what to type for each tool, you fill in a "
                    "form and press Run; the panel builds the command for you and shows it on screen.")),
            ("p", T("Bu, iki şeyi bir arada sağlar: araçları terminal bilmeden kullanabilirsin, ve her "
                    "seferinde üstte gösterilen komutu okuyarak terminali de öğrenirsin.",
                    "This gives you two things at once: you can use the tools without knowing the terminal, "
                    "and by reading the command shown each time you also learn the terminal.")),
        ]),
        (T("10 araç, tek bakışta", "The 10 tools, at a glance"), [
            ("tablo", [
                (T("nmap", "nmap"), T("Ağ ve port keşfi.", "Network & port discovery.")),
                (T("tcpdump", "tcpdump"), T("Ağ paketi yakalama.", "Network packet capture.")),
                (T("tshark", "tshark"), T("Paketleri protokolle çözümler.", "Dissects packets by protocol.")),
                (T("aircrack-ng", "aircrack-ng"), T("Kablosuz ağ bilgisi.", "Wireless network info.")),
                (T("nikto", "nikto"), T("Web sunucu tarayıcı.", "Web server scanner.")),
                (T("sqlmap", "sqlmap"), T("SQL injection testi.", "SQL injection testing.")),
                (T("john", "john"), T("Parola kırma.", "Password cracking.")),
                (T("hydra", "hydra"), T("Giriş kaba kuvvet testi.", "Login brute-force testing.")),
                (T("ufw", "ufw"), T("Güvenlik duvarı.", "Firewall.")),
                (T("fail2ban", "fail2ban"), T("Kaba kuvvet koruması.", "Brute-force protection.")),
            ]),
            ("p", T("Her birinin kendi konusunda ayrıntılı anlatımı, canlı animasyonu ve denenecek görevleri "
                    "var; soldaki listeden tek tek açabilirsin.",
                    "Each one has its own detailed topic with a live animation and tasks to try; open them "
                    "one by one from the list on the left.")),
        ]),
        (T("Root ile çalıştır ne zaman gerekir", "When you need Run as root"), [
            ("p", T("Bazı işler (bir ağ kartını dinlemek, güvenlik duvarı kurallarını değiştirmek) sıradan "
                    "bir kullanıcıya açık değildir; bilgisayarın yönetici onayı ister. Panel bunu senin "
                    "yerine pkexec ile sorar: parolanı bir kez girersin, araç o yetkiyle çalışır.",
                    "Some jobs (listening on a network card, changing firewall rules) are not open to an "
                    "ordinary user; the computer asks for administrator approval. The panel asks this for "
                    "you via pkexec: you type your password once, and the tool runs with that right.")),
            ("not", T("Parolanı yalnızca bu resmi pencereye gir. Panel dışında, beklenmedik bir yerde parola "
                      "isteyen bir pencere görürsen şüphelen.",
                      "Only type your password into this official dialog. If a window asks for your password "
                      "somewhere unexpected outside the panel, be suspicious.")),
        ]),
        (T("Araçlar kurulu değilse", "If the tools are not installed"), [
            ("p", T("Bu araçların hepsi ayrı paketlerdir; sisteminde kurulu değilse panel sayfada bunu "
                    "söyler. Mağaza uygulamasından tek tıkla kurabilirsin.",
                    "Each of these tools is a separate package; if one is not installed, the panel page says "
                    "so. You can install it with one click from the Store app.")),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Bu sayfadaki araçların tamamı güçlüdür ve yanlış ellerde zarar verebilir. Genel "
                        "kural hep aynı: yalnızca kendi cihazlarında, kendi ağında ya da açıkça izin "
                        "aldığın sistemlerde kullan. Her aracın kendi konusunda ayrı bir “Dikkat” bölümü "
                        "var; oraları da oku.",
                        "All the tools on this page are powerful and can cause harm in the wrong hands. The "
                        "general rule is always the same: use them only on your own devices, your own "
                        "network, or systems you have clear permission for. Each tool's own topic has its "
                        "own “Be careful” section too; read those as well.")),
        ]),
    ]
    k = _konu("panel", NMAP_ARAC, adimlar, bolumler, ikon="panel",
              ozet=T("Güvenlik Paneli'nin genel yapısı: gezinme, araç sayfası, root ve ayarlar.",
                     "The Security Panel's general layout: navigation, a tool page, root and settings."))
    k["ad"] = T("Güvenlik Paneli", "Security Panel")
    k["alt"] = T("Genel tanıtım", "General overview")
    k["uygulama"] = {"ad": T("Güvenlik Paneli", "Security Panel"), "komut": PANEL_KOMUT}
    return k
