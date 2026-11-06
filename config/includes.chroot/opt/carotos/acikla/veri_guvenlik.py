# -*- coding: utf-8 -*-
"""Komut Açıklayıcı veri tabanı: sistem yönetimi ve SAVUNMA araçları.

Her komut: ozet {tr,en}, gurultu (dusuk|orta|yuksek), yetki (yok|kismen|root), kume (kısa bayraklar birleşir mi),
bayraklar {bayrak: A(tr, en, g=gürültü, root=True, deger=True)}, desenler [(regex, A(...))],
altkomut {ad: T}, uyari T, gsd (sözlük terimi).
"""


def T(tr, en):
    return {"tr": tr, "en": en}


def A(tr, en, **kw):
    return {"a": T(tr, en), **kw}


TAKMA_ADLAR = {}

KOMUTLAR = {
    "ufw": {
        "ozet": T("Güvenlik duvarı yönetimi (Uncomplicated Firewall): hangi bağlantıların izinli olduğunu ayarlar.",
                  "Firewall management (Uncomplicated Firewall): sets which connections are allowed."),
        "gurultu": "dusuk", "yetki": "root", "gsd": "Firewall",
        "bayraklar": {
            "--force": A("Onay sormadan uygular.", "Applies without asking for confirmation."),
            "--dry-run": A("Uygulamadan ne yapacağını gösterir.", "Shows what it would do without applying it."),
        },
        "altkomut": {
            "status": T("Güvenlik duvarının durumunu ve kuralları gösterir (verbose ayrıntı, numbered numaralı liste).",
                        "Shows the firewall status and rules (verbose for detail, numbered for a numbered list)."),
            "enable": T("Güvenlik duvarını açar ve açılışta başlatır.", "Turns the firewall on and starts it at boot."),
            "disable": T("Güvenlik duvarını kapatır: gelen bağlantılar süzülmez.", "Turns the firewall off: incoming connections are not filtered."),
            "reset": T("Tüm kuralları siler ve güvenlik duvarını kapatır.", "Deletes all rules and turns the firewall off."),
            "allow": T("Bir bağlantıya izin veren kural ekler (ör. 22/tcp).", "Adds a rule allowing a connection (e.g. 22/tcp)."),
            "deny": T("Bir bağlantıyı sessizce engelleyen kural ekler.", "Adds a rule that silently blocks a connection."),
            "reject": T("Bir bağlantıyı reddeder ve karşı tarafa bildirir.", "Rejects a connection and tells the other side."),
            "limit": T("Bir bağlantıya izin verir ama kısa sürede çok deneme yapanı sınırlar (kaba kuvveti zorlaştırır).",
                       "Allows a connection but limits sources that try too often (makes brute force harder)."),
            "delete": T("Bir kuralı siler (kural metniyle ya da numarasıyla).", "Deletes a rule (by its text or its number)."),
            "default": T("Varsayılan politikayı ayarlar (ör. gelen: deny).", "Sets the default policy (e.g. incoming: deny)."),
            "logging": T("Güvenlik duvarı günlüğünü açar/kapatır ya da düzeyini ayarlar.", "Turns firewall logging on/off or sets its level."),
            "reload": T("Kuralları yeniden yükler.", "Reloads the rules."),
        },
    },
    "fail2ban-client": {
        "ozet": T("fail2ban hizmetini yönetir: tekrar tekrar başarısız giriş yapan adresleri geçici olarak engeller.",
                  "Manages the fail2ban service: it temporarily blocks addresses that repeatedly fail to log in."),
        "gurultu": "dusuk", "yetki": "root",
        "bayraklar": {
            "-x": A("Çalışan hizmetin yerine yeniden başlatır.", "Replaces the running service by restarting it."),
            "-v": A("Daha ayrıntılı çıktı verir.", "Gives more detailed output."),
        },
        "altkomut": {
            "status": T("Etkin 'jail' listesini ya da belirtilen jail'in durumunu gösterir.", "Shows the active jail list or the status of a given jail."),
            "ping": T("Hizmetin çalışıp çalışmadığını sınar.", "Checks whether the service is running."),
            "reload": T("Yapılandırmayı yeniden yükler.", "Reloads the configuration."),
            "start": T("Hizmeti başlatır.", "Starts the service."),
            "stop": T("Hizmeti durdurur: koruma kapanır.", "Stops the service: the protection goes off."),
            "set": T("Bir jail ayarını değiştirir (ör. bir adresi engelden çıkarma).", "Changes a jail setting (e.g. unbanning an address)."),
            "get": T("Bir jail ayarını okur.", "Reads a jail setting."),
        },
    },
    "clamscan": {
        "ozet": T("ClamAV ile dosyaları virüs imzalarına karşı tarar (Carotene'in arka planındaki araç).",
                  "Scans files against virus signatures with ClamAV (the tool behind Carotene)."),
        "gurultu": "dusuk", "yetki": "yok", "kume": True, "gsd": "Antivirus",
        "bayraklar": {
            "-r": A("Alt klasörleri de tarar.", "Scans subfolders too."),
            "-i": A("Yalnızca bulaşık dosyaları listeler.", "Lists only infected files."),
            "-v": A("Her dosyayı ayrıntılı gösterir.", "Shows every file in detail."),
            "-l": A("Sonuçları bir günlük dosyasına yazar.", "Writes the results to a log file.", deger=True),
            "--infected": A("Yalnızca bulaşık dosyaları listeler.", "Lists only infected files."),
            "--remove": A("Bulaşık dosyaları SİLER (geri alınamaz; önce karantinayı düşün).",
                          "DELETES infected files (can't be undone; consider quarantine first)."),
            "--move": A("Bulaşık dosyaları verilen klasöre taşır (karantina).", "Moves infected files to the given folder (quarantine).", deger=True),
            "--bell": A("Virüs bulununca sesli uyarı verir.", "Beeps when a virus is found."),
        },
        "uyari": T("Tarama için güncel virüs imzaları gerekir (freshclam ya da Carotene).",
                   "Scanning needs up-to-date virus signatures (freshclam or Carotene)."),
    },
    "rkhunter": {
        "ozet": T("Rootkit ve şüpheli sistem değişikliklerini arar.", "Looks for rootkits and suspicious system changes."),
        "gurultu": "dusuk", "yetki": "root",
        "bayraklar": {
            "--check": A("Tam denetimi başlatır.", "Starts the full check."),
            "-c": A("Tam denetimi başlatır (--check).", "Starts the full check (--check)."),
            "--update": A("Veri dosyalarını günceller.", "Updates its data files."),
            "--propupd": A("Şu anki dosya özelliklerini 'temiz' karşılaştırma kaydı olarak saklar. Yalnızca sistem güvenilirse!",
                           "Stores the current file properties as the 'clean' comparison record. Only if the system is trustworthy!"),
            "--sk": A("Adımlar arasında tuşa basmayı beklemez.", "Doesn't wait for a key press between steps."),
            "--skip-keypress": A("Adımlar arasında tuşa basmayı beklemez.", "Doesn't wait for a key press between steps."),
            "--rwo": A("Yalnızca uyarıları raporlar.", "Reports warnings only."),
            "--report-warnings-only": A("Yalnızca uyarıları raporlar.", "Reports warnings only."),
            "--list": A("Yapılan denetimleri listeler.", "Lists the checks it performs."),
        },
        "uyari": T("Güncelleme sonrası yanlış alarm (false positive) verebilir; her uyarıyı ayrıca değerlendir.",
                   "It can raise false positives after updates; judge each warning separately."),
    },
    "debsums": {
        "ozet": T("Kurulu paketlerin dosyalarını paketle gelen sağlama toplamlarıyla karşılaştırır: değişmiş ya da bozulmuş dosyaları bulur.",
                  "Compares the files of installed packages with the package's checksums: finds modified or corrupted files."),
        "gurultu": "dusuk", "yetki": "kismen", "kume": True,
        "bayraklar": {
            "-s": A("Sessiz: yalnızca hataları gösterir.", "Silent: shows errors only."),
            "-c": A("Yalnızca DEĞİŞMİŞ dosyaları listeler.", "Lists only CHANGED files."),
            "-a": A("Yapılandırma dosyalarını da denetler.", "Checks configuration files too."),
            "-e": A("Yalnızca yapılandırma dosyalarını denetler.", "Checks only configuration files."),
        },
    },
    "ss": {
        "ozet": T("Ağ bağlantılarını ve dinlenen portları listeler (netstat'ın yenisi).", "Lists network connections and listening ports (the modern netstat)."),
        "gurultu": "dusuk", "yetki": "kismen", "kume": True, "gsd": "Port",
        "bayraklar": {
            "-t": A("TCP bağlantılarını gösterir.", "Shows TCP connections."),
            "-u": A("UDP bağlantılarını gösterir.", "Shows UDP connections."),
            "-l": A("Yalnızca dinleyen (bağlantı bekleyen) soketleri gösterir.", "Shows only listening sockets (waiting for connections)."),
            "-n": A("Adları çözmez; port ve IP'yi sayı olarak gösterir.", "Doesn't resolve names; shows ports and IPs as numbers."),
            "-p": A("Soketi kullanan süreci gösterir (başkasının süreci için root gerekir).", "Shows the process using the socket (root needed for other users' processes).", root=True),
            "-a": A("Dinleyen ve bağlı tüm soketleri gösterir.", "Shows all listening and connected sockets."),
            "-4": A("Yalnızca IPv4.", "IPv4 only."),
            "-6": A("Yalnızca IPv6.", "IPv6 only."),
            "-s": A("Özet istatistik verir.", "Gives summary statistics."),
        },
    },
    "systemctl": {
        "ozet": T("systemd hizmetlerini yönetir: başlatır, durdurur, durumunu gösterir.", "Manages systemd services: starts, stops and shows their status."),
        "gurultu": "dusuk", "yetki": "kismen",
        "bayraklar": {
            "--now": A("enable/disable ile birlikte hizmeti hemen başlatır/durdurur.", "With enable/disable, also starts/stops the service right now."),
            "--user": A("Sistem yerine kendi kullanıcı hizmetlerini yönetir.", "Manages your own user services instead of system ones."),
            "-l": A("Satırları kısaltmadan tam gösterir.", "Shows lines in full, without truncating."),
            "--no-pager": A("Çıktıyı sayfalamaz, doğrudan yazar.", "Doesn't page the output; prints it directly."),
        },
        "altkomut": {
            "status": T("Hizmetin durumunu ve son günlük satırlarını gösterir.", "Shows a service's status and latest log lines."),
            "start": T("Hizmeti başlatır (root gerekir).", "Starts the service (needs root)."),
            "stop": T("Hizmeti durdurur (root gerekir).", "Stops the service (needs root)."),
            "restart": T("Hizmeti yeniden başlatır (root gerekir).", "Restarts the service (needs root)."),
            "enable": T("Hizmeti açılışta başlayacak şekilde ayarlar.", "Sets the service to start at boot."),
            "disable": T("Hizmetin açılışta başlamasını kapatır.", "Stops the service from starting at boot."),
            "mask": T("Hizmetin hiçbir şekilde başlatılmasını engeller.", "Prevents the service from being started at all."),
            "is-active": T("Hizmet çalışıyor mu diye yazar (active/inactive).", "Prints whether the service is running (active/inactive)."),
            "list-units": T("Yüklü birimleri listeler.", "Lists loaded units."),
            "daemon-reload": T("Birim dosyalarını yeniden okur.", "Re-reads the unit files."),
        },
    },
    "journalctl": {
        "ozet": T("Sistem günlüklerini (systemd journal) okur.", "Reads the system logs (systemd journal)."),
        "gurultu": "dusuk", "yetki": "kismen", "kume": True,
        "bayraklar": {
            "-u": A("Yalnızca belirtilen hizmetin kayıtlarını gösterir.", "Shows only the given service's entries.", deger=True),
            "-f": A("Yeni kayıtları canlı izler (çıkmak için Ctrl+C).", "Follows new entries live (Ctrl+C to quit)."),
            "-n": A("Son N satırı gösterir.", "Shows the last N lines.", deger=True),
            "-b": A("Yalnızca bu açılıştan beri olanları gösterir.", "Shows only entries since this boot."),
            "-p": A("Öncelik düzeyine göre süzer (ör. err).", "Filters by priority level (e.g. err).", deger=True),
            "-k": A("Yalnızca çekirdek (kernel) iletilerini gösterir.", "Shows only kernel messages."),
            "-r": A("En yeni kayıt başta olacak şekilde ters sıralar.", "Reverses the order: newest first."),
            "--since": A("Verilen zamandan sonrasını gösterir.", "Shows entries after the given time.", deger=True),
            "--no-pager": A("Çıktıyı sayfalamaz.", "Doesn't page the output."),
        },
        "uyari": T("Başkalarının/sistemin kayıtlarını tam görmek için sudo gerekebilir.", "You may need sudo to see other users'/system entries in full."),
    },
}
