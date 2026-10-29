# -*- coding: utf-8 -*-
"""
Former -- sahne kurucular (GTK'siz).

Her uygulama ekraninin sade bir kopyasini veri olarak uretir:
  * panel_sahnesi()    Guvenlik Paneli: kenar menusu + arac sayfasi + ayarlar
  * carotpot_sahnesi() CarotPot: pano, saldirganlar, onay penceresi
  * carotene_sahnesi() Carotene: tarama, sonuc, karantina
  * giris_sahnesi()    CarotOS guvenlik uygulamalari haritasi

Konu dosyalari (konular/) bu sahnelere adim listesi ekler.
"""

from __future__ import annotations

from former_zaman import T

PW, PH = 760, 420
UST = 26                    # pencere baslik cubugu

ARAC_SIRASI = ["nmap", "tcpdump", "tshark", "aircrack-ng", "nikto", "sqlmap", "john", "hydra", "ufw",
               "fail2ban"]

# ortak metinler
T_NE_ZAMAN = T("Ne zaman kullanılır", "When to use it")
T_ORNEK = T("Örnek", "Example")
T_CALISTIR = T("Çalıştır", "Run")
T_ROOT = T("Root ile çalıştır", "Run as root")
T_DURDUR = T("Durdur", "Stop")
T_TEMIZLE = T("Çıktıyı temizle", "Clear output")
T_BITTI = T("[Bitti — çıkış kodu 0]", "[Finished — exit code 0]")
T_ARAC_SEC = T("Soldan bir araç seçin", "Pick a tool on the left")
T_ROOT_IPUCU = T("Bu araç yönetici yetkisi ister. “Root ile çalıştır”ı kullanın; parola penceresi açılır.",
                 "This tool needs administrator rights. Use “Run as root”; a password dialog will appear.")


def _yan(marka, marka_alt, ogeler, adim=25, y0=64, grup="menu", genislik=150, sayfa=None, baslangic_aktif=None):
    """Kenar menusu ogeleri. ogeler: [(id, metin, simge_ya_da_None)]"""
    e = [{"id": "yan", "tur": "yan", "x": 0, "y": UST, "w": genislik, "h": PH - UST},
         {"id": "marka", "tur": "metin", "x": 14, "y": UST + 10, "w": genislik - 20, "h": 14, "metin": marka,
          "boyut": 10.5, "kalin": True},
         {"id": "marka_alt", "tur": "metin", "x": 14, "y": UST + 27, "w": genislik - 20, "h": 12,
          "metin": marka_alt, "boyut": 7.4, "renk": "soluk"}]
    y = y0
    for kimlik, metin, simge in ogeler:
        e.append({"id": kimlik, "tur": "menu", "x": 8, "y": y, "w": genislik - 16, "h": 22, "metin": metin,
                  "simge": simge, "grup": grup, "aktif": kimlik == baslangic_aktif})
        y += adim
    return e


# ---------------------------------------------------------------------------
# Guvenlik Paneli
# ---------------------------------------------------------------------------
def _pkexec_ogeleri():
    """Root icin parola penceresi (pkexec). Bayrak: 'pkexec'."""
    return [
        {"id": "pk_perde", "tur": "perde", "x": 0, "y": UST, "w": PW, "h": PH - UST, "bayrak": "pkexec"},
        {"id": "pk_kutu", "tur": "diyalog", "x": 230, "y": 120, "w": 300, "h": 170, "bayrak": "pkexec",
         "baslik": T("Kimlik doğrulaması gerekli", "Authentication required")},
        {"id": "pk_metin", "tur": "metin", "x": 246, "y": 148, "w": 268, "h": 34, "bayrak": "pkexec", "sar": True,
         "boyut": 8, "renk": "soluk",
         "metin": T("Bu işlem için yönetici yetkisi gerekiyor. Kendi parolanı yaz.",
                    "This action needs administrator rights. Type your own password.")},
        {"id": "pk_parola", "tur": "alan", "x": 246, "y": 192, "w": 268, "h": 26, "bayrak": "pkexec",
         "yer": T("Parola", "Password")},
        {"id": "pk_iptal", "tur": "dugme", "x": 330, "y": 244, "w": 80, "h": 26, "bayrak": "pkexec",
         "metin": T("İptal", "Cancel")},
        {"id": "pk_tamam", "tur": "dugme", "x": 418, "y": 244, "w": 96, "h": 26, "bayrak": "pkexec",
         "birincil": True, "metin": T("Doğrula", "Authenticate")},
    ]


def panel_sahnesi(arac: dict) -> dict:
    """arac: {ad, tagline, ne, ne_zaman, ornek, root, alanlar:[{id, ad, tur, varsayilan, yer, secenekler}]}"""
    ogeler = _yan(T("CarotOS", "CarotOS"), T("Güvenlik Paneli", "Security Panel"),
                  [("arac:" + a, a, None) for a in ARAC_SIRASI], adim=25, y0=64)
    ogeler += [
        {"id": "yan_cizgi", "tur": "cizgi", "x": 14, "y": 322, "w": 122, "h": 1},
        {"id": "menu:ayar", "tur": "menu", "x": 8, "y": 332, "w": 134, "h": 22, "metin": T("Ayarlar", "Settings"),
         "simge": "ayar", "grup": "menu", "aktif": False},
    ]
    # --- bos sayfa
    ogeler.append({"id": "bos", "tur": "metin", "x": 160, "y": 200, "w": PW - 160, "h": 20, "sayfa": "bos",
                   "metin": T_ARAC_SEC, "boyut": 10, "renk": "silik", "hiza": "orta", "sar": True})
    # --- arac sayfasi
    ogeler += [
        {"id": "a_ad", "tur": "metin", "x": 172, "y": 34, "w": 400, "h": 20, "sayfa": "arac", "metin": arac["ad"],
         "boyut": 14, "kalin": True},
        {"id": "a_alt", "tur": "metin", "x": 172, "y": 58, "w": 560, "h": 14, "sayfa": "arac",
         "metin": arac["tagline"], "boyut": 8.6, "renk": "vurgu_yazi"},
        {"id": "a_bilgi", "tur": "kart", "x": 170, "y": 78, "w": 578, "h": 72, "sayfa": "arac"},
        {"id": "a_ne", "tur": "metin", "x": 182, "y": 86, "w": 554, "h": 14, "sayfa": "arac", "metin": arac["ne"],
         "boyut": 8.2, "sar": True},
        {"id": "a_zaman", "tur": "metin", "x": 182, "y": 104, "w": 554, "h": 14, "sayfa": "arac", "sar": True,
         "metin": T("{}: {}".format(T_NE_ZAMAN["tr"], arac["ne_zaman"]["tr"]),
                    "{}: {}".format(T_NE_ZAMAN["en"], arac["ne_zaman"]["en"])), "boyut": 8.2, "renk": "soluk"},
        {"id": "a_ornek", "tur": "metin", "x": 182, "y": 124, "w": 554, "h": 14, "sayfa": "arac", "sar": True,
         "metin": T("{}: {}".format(T_ORNEK["tr"], arac["ornek"]["tr"]),
                    "{}: {}".format(T_ORNEK["en"], arac["ornek"]["en"])), "boyut": 8.2, "renk": "soluk"},
    ]
    y = 160
    for f in arac["alanlar"]:
        ogeler.append({"id": "et:" + f["id"], "tur": "metin", "x": 174, "y": y + 5, "w": 150, "h": 14,
                       "sayfa": "arac", "metin": f["ad"], "boyut": 8.6, "renk": "soluk"})
        o = {"id": "alan:" + f["id"], "tur": f["tur"], "x": 330, "y": y, "w": 310, "h": 24, "sayfa": "arac",
             "deger": f.get("varsayilan", "")}
        if f.get("yer"):
            o["yer"] = f["yer"]
        if f.get("secenekler"):
            o["secenekler"] = f["secenekler"]
        ogeler.append(o)
        y += 30
    if arac.get("root"):
        ogeler.append({"id": "root_ipucu", "tur": "metin", "x": 172, "y": y + 2, "w": 570, "h": 14,
                       "sayfa": "arac", "metin": T_ROOT_IPUCU, "boyut": 7.8, "renk": "sari", "sar": True})
        y += 22
    by = y + 4
    ogeler += [
        {"id": "btn:calistir", "tur": "dugme", "x": 170, "y": by, "w": 96, "h": 26, "sayfa": "arac",
         "birincil": True, "metin": T_CALISTIR},
        {"id": "btn:root", "tur": "dugme", "x": 274, "y": by, "w": 128, "h": 26, "sayfa": "arac", "metin": T_ROOT},
        {"id": "btn:durdur", "tur": "dugme", "x": 410, "y": by, "w": 78, "h": 26, "sayfa": "arac",
         "metin": T_DURDUR, "pasif": True},
        {"id": "btn:temizle", "tur": "dugme", "x": 632, "y": by, "w": 116, "h": 26, "sayfa": "arac",
         "metin": T_TEMIZLE},
        {"id": "onizleme", "tur": "metin", "x": 172, "y": by + 34, "w": 570, "h": 14, "sayfa": "arac",
         "metin": "", "boyut": 8, "mono": True, "renk": "vurgu_yazi"},
        {"id": "cikti", "tur": "cikti", "x": 170, "y": by + 54, "w": 578, "h": PH - 10 - (by + 54),
         "sayfa": "arac", "satirlar": []},
    ]
    # --- ayarlar sayfasi
    ogeler += [
        {"id": "s_ad", "tur": "metin", "x": 172, "y": 34, "w": 400, "h": 20, "sayfa": "ayar", "metin": T("Ayarlar", "Settings"),
         "boyut": 14, "kalin": True},
        {"id": "s_dil_et", "tur": "metin", "x": 174, "y": 84, "w": 100, "h": 14, "sayfa": "ayar",
         "metin": T("Dil", "Language"), "boyut": 8.6, "renk": "soluk"},
        {"id": "s_dil", "tur": "secim", "x": 290, "y": 79, "w": 200, "h": 24, "sayfa": "ayar",
         "secenekler": [T("Türkçe", "Türkçe"), T("English", "English")], "deger": "Türkçe"},
        {"id": "s_tema_et", "tur": "metin", "x": 174, "y": 118, "w": 100, "h": 14, "sayfa": "ayar",
         "metin": T("Tema", "Theme"), "boyut": 8.6, "renk": "soluk"},
        {"id": "s_tema", "tur": "secim", "x": 290, "y": 113, "w": 200, "h": 24, "sayfa": "ayar",
         "secenekler": [T("Koyu", "Dark"), T("Açık", "Light")], "deger": ""},
        {"id": "s_cizgi", "tur": "cizgi", "x": 172, "y": 160, "w": 576, "h": 1, "sayfa": "ayar"},
        {"id": "s_fw", "tur": "metin", "x": 172, "y": 174, "w": 400, "h": 16, "sayfa": "ayar",
         "metin": T("Güvenlik Duvarı", "Firewall"), "boyut": 10.5, "kalin": True},
        {"id": "s_fw_alt", "tur": "metin", "x": 172, "y": 196, "w": 560, "h": 14, "sayfa": "ayar", "sar": True,
         "metin": T("Sisteme gelen bağlantıları engelleyip engellemeyeceğini buradan aç/kapat.",
                    "Turn incoming connection blocking on or off here."), "boyut": 8.2, "renk": "soluk"},
        {"id": "s_fw_ani", "tur": "anahtar", "x": 174, "y": 228, "w": 40, "h": 22, "sayfa": "ayar", "aktif": False},
        {"id": "s_fw_durum", "tur": "metin", "x": 226, "y": 232, "w": 160, "h": 14, "sayfa": "ayar",
         "metin": T("Kapalı", "Disabled"), "boyut": 8.8, "kalin": True},
        {"id": "s_fw_yenile", "tur": "dugme", "x": 390, "y": 227, "w": 76, "h": 24, "sayfa": "ayar",
         "metin": T("Yenile", "Refresh")},
    ]
    ogeler += _pkexec_ogeleri()
    return {"genislik": PW, "yukseklik": PH, "vurgu": "guvenlik", "sayfa": "bos",
            "baslik": T("CarotOS Güvenlik Paneli", "CarotOS Security Panel"), "ogeler": ogeler}


# ---------------------------------------------------------------------------
# CarotPot
# ---------------------------------------------------------------------------
def carotpot_sahnesi() -> dict:
    menu = [("cp:pano", T("Pano", "Dashboard"), "pano"), ("cp:saldirgan", T("Saldırganlar", "Attackers"), "kisi"),
            ("cp:tuzak", T("Tuzaklar", "Traps"), "altigen"), ("cp:kanarya", T("Kanarya dosyalar", "Canary files"), "dosya"),
            ("cp:engel", T("Engelleme", "Blocking"), "kalkan"), ("cp:rapor", T("Raporlar", "Reports"), "rapor"),
            ("cp:ag", T("Ağ haritası", "Network map"), "ag"), ("cp:ayar", T("Ayarlar", "Settings"), "ayar")]
    o = _yan(T("CarotPot", "CarotPot"), T("Yerel ağ tuzağı", "Local network trap"), menu, adim=26, y0=62,
             baslangic_aktif="cp:pano")
    o += [
        # --- pano
        {"id": "p_baslik", "tur": "metin", "x": 172, "y": 34, "w": 300, "h": 20, "sayfa": "pano",
         "metin": T("Pano", "Dashboard"), "boyut": 14, "kalin": True},
        {"id": "p_alt", "tur": "metin", "x": 172, "y": 58, "w": 330, "h": 14, "sayfa": "pano", "boyut": 8.4,
         "renk": "soluk", "metin": T("Ağdaki tuzak etkinliğinin canlı özeti", "Live summary of trap activity")},
        {"id": "p_hap", "tur": "rozet", "x": 484, "y": 36, "w": 150, "h": 22, "sayfa": "pano", "renk": "gri",
         "metin": T("Tuzak kapalı", "Trap off")},
        {"id": "p_baslat", "tur": "dugme", "x": 644, "y": 34, "w": 104, "h": 26, "sayfa": "pano", "birincil": True,
         "metin": T("Başlat", "Start")},
        {"id": "kpi1", "tur": "kpi", "x": 170, "y": 82, "w": 136, "h": 66, "sayfa": "pano",
         "ad": T("Olay · son 24 saat", "Events · 24 h"), "metin": "0"},
        {"id": "kpi2", "tur": "kpi", "x": 314, "y": 82, "w": 136, "h": 66, "sayfa": "pano",
         "ad": T("Benzersiz kaynak", "Unique sources"), "metin": "0"},
        {"id": "kpi3", "tur": "kpi", "x": 458, "y": 82, "w": 136, "h": 66, "sayfa": "pano",
         "ad": T("Giriş denemesi", "Login attempts"), "metin": "0"},
        {"id": "kpi4", "tur": "kpi", "x": 602, "y": 82, "w": 146, "h": 66, "sayfa": "pano",
         "ad": T("Engellenen adres", "Blocked addresses"), "metin": "0"},
        {"id": "p_kapali", "tur": "metin", "x": 176, "y": 170, "w": 566, "h": 40, "sayfa": "pano", "bayrak": "!acik",
         "sar": True,
         "boyut": 8.6, "renk": "soluk",
         "metin": T("Tuzak kapalı. Açtığınızda yerel ağda bu bilgisayarı tarayan ya da giriş deneyen cihazlar "
                    "burada görünür. Sistem açılışında kendiliğinden başlamaz.",
                    "The trap is off. When you turn it on, devices on the local network that scan this computer "
                    "or try to log in appear here. It does not start automatically at boot.")},
        {"id": "p_akis_kart", "tur": "kart", "x": 170, "y": 164, "w": 578, "h": 246, "sayfa": "pano",
         "bayrak": "acik", "baslik": T("Canlı akış", "Live feed")},
        {"id": "olay1", "tur": "satir", "x": 180, "y": 194, "w": 558, "h": 28, "sayfa": "pano", "bayrak": "o1",
         "renk": "sari", "metin": T("192.168.1.23 · Port taraması · 8 tuzağa bakıldı",
                                    "192.168.1.23 · Port scan · 8 traps probed")},
        {"id": "olay2", "tur": "satir", "x": 180, "y": 226, "w": 558, "h": 28, "sayfa": "pano", "bayrak": "o2",
         "renk": "kirmizi", "metin": T("192.168.1.23 · SSH giriş denemesi · root / ●●●●●●",
                                       "192.168.1.23 · SSH login attempt · root / ●●●●●●")},
        {"id": "olay3", "tur": "satir", "x": 180, "y": 258, "w": 558, "h": 28, "sayfa": "pano", "bayrak": "o3",
         "renk": "kirmizi", "metin": T("192.168.1.23 · SSH giriş denemesi · admin / ●●●●●●●●",
                                       "192.168.1.23 · SSH login attempt · admin / ●●●●●●●●")},
        {"id": "olay4", "tur": "satir", "x": 180, "y": 290, "w": 558, "h": 28, "sayfa": "pano", "bayrak": "o4",
         "renk": "mavi", "metin": T("192.168.1.40 · Web isteği · /admin/login.php",
                                    "192.168.1.40 · Web request · /admin/login.php")},
        # --- saldirganlar
        {"id": "s_baslik", "tur": "metin", "x": 172, "y": 34, "w": 300, "h": 20, "sayfa": "saldirgan",
         "metin": T("Saldırgan profili", "Attacker profile"), "boyut": 14, "kalin": True},
        {"id": "s_alt", "tur": "metin", "x": 172, "y": 58, "w": 460, "h": 14, "sayfa": "saldirgan", "boyut": 8.4,
         "renk": "soluk", "metin": T("Kaynak başına davranış, kimlik bilgileri ve risk",
                                     "Behaviour, credentials and risk per source")},
        {"id": "s_liste", "tur": "kart", "x": 170, "y": 82, "w": 190, "h": 328, "sayfa": "saldirgan",
         "baslik": T("Kaynaklar · 2", "Sources · 2")},
        {"id": "s_kaynak1", "tur": "satir", "x": 178, "y": 112, "w": 174, "h": 32, "sayfa": "saldirgan",
         "renk": "kirmizi", "vurgulu": True, "metin": "192.168.1.23"},
        {"id": "s_kaynak2", "tur": "satir", "x": 178, "y": 148, "w": 174, "h": 32, "sayfa": "saldirgan",
         "renk": "mavi", "metin": "192.168.1.40"},
        {"id": "s_profil", "tur": "kart", "x": 368, "y": 82, "w": 380, "h": 328, "sayfa": "saldirgan"},
        {"id": "s_ip", "tur": "metin", "x": 382, "y": 94, "w": 200, "h": 20, "sayfa": "saldirgan",
         "metin": "192.168.1.23", "boyut": 12, "kalin": True},
        {"id": "s_risk", "tur": "rozet", "x": 600, "y": 96, "w": 132, "h": 20, "sayfa": "saldirgan",
         "renk": "kirmizi", "metin": T("YÜKSEK RİSK", "HIGH RISK")},
        {"id": "s_cihaz", "tur": "metin", "x": 382, "y": 124, "w": 350, "h": 14, "sayfa": "saldirgan",
         "boyut": 8.2, "renk": "soluk", "sar": True,
         "metin": T("Cihaz: Raspberry Pi Trading (MAC b8:27:eb:…)", "Device: Raspberry Pi Trading (MAC b8:27:eb:…)")},
        {"id": "s_zaman", "tur": "metin", "x": 382, "y": 142, "w": 350, "h": 28, "sayfa": "saldirgan",
         "boyut": 8.2, "renk": "soluk", "sar": True,
         "metin": T("İlk görülme 14:02 · son görülme 14:09 · 38 olay, 31 giriş denemesi",
                    "First seen 14:02 · last seen 14:09 · 38 events, 31 login attempts")},
        {"id": "s_davranis", "tur": "metin", "x": 382, "y": 176, "w": 350, "h": 28, "sayfa": "saldirgan",
         "boyut": 8.4, "sar": True,
         "metin": T("Davranış: port taraması, kaba kuvvet (sözlük saldırısı)",
                    "Behaviour: port scan, brute force (dictionary attack)")},
        {"id": "s_kul", "tur": "metin", "x": 382, "y": 214, "w": 350, "h": 28, "sayfa": "saldirgan",
         "boyut": 8.2, "renk": "soluk", "sar": True,
         "metin": T("Denenen kullanıcı adları: root, admin, pi, ubuntu",
                    "Attempted usernames: root, admin, pi, ubuntu")},
        {"id": "s_engelle", "tur": "dugme", "x": 382, "y": 370, "w": 100, "h": 26, "sayfa": "saldirgan",
         "birincil": True, "metin": T("Engelle", "Block")},
        {"id": "s_yoksay", "tur": "dugme", "x": 490, "y": 370, "w": 100, "h": 26, "sayfa": "saldirgan",
         "metin": T("Yok say", "Ignore")},
        {"id": "s_engelli", "tur": "rozet", "x": 600, "y": 372, "w": 100, "h": 22, "sayfa": "saldirgan",
         "bayrak": "engelli", "renk": "kirmizi", "metin": T("ENGELLİ", "BLOCKED")},
        # --- baslatma onayi
        {"id": "b_perde", "tur": "perde", "x": 0, "y": UST, "w": PW, "h": PH - UST, "bayrak": "baslat_diyalog"},
        {"id": "b_kutu", "tur": "diyalog", "x": 200, "y": 96, "w": 360, "h": 206, "bayrak": "baslat_diyalog",
         "baslik": T("Tuzak açılsın mı?", "Turn the trap on?")},
        {"id": "b_metin", "tur": "metin", "x": 216, "y": 126, "w": 328, "h": 100, "bayrak": "baslat_diyalog",
         "sar": True, "boyut": 8.2, "renk": "soluk",
         "metin": T("Bu bilgisayarda sahte hizmetler açılacak ve güvenlik duvarında bu portlara izin verilecek. "
                    "Yalnızca güvendiğiniz ağlarda (ev, okul laboratuvarı) açın; kafe, otel gibi ortak ağlarda "
                    "açmayın. Gerçek bir kabuk ya da hizmet yoktur; her giriş denemesi reddedilir.",
                    "Fake services will be opened on this computer and the firewall will allow these ports. Turn "
                    "it on only on networks you trust (home, school lab); not on shared networks such as cafés "
                    "or hotels. There is no real shell or service; every login attempt is rejected.")},
        {"id": "b_iptal", "tur": "dugme", "x": 360, "y": 256, "w": 90, "h": 28, "bayrak": "baslat_diyalog",
         "metin": T("İptal", "Cancel")},
        {"id": "b_tamam", "tur": "dugme", "x": 458, "y": 256, "w": 90, "h": 28, "bayrak": "baslat_diyalog",
         "birincil": True, "metin": T("Aç", "Turn on")},
        # --- engelleme onayi
        {"id": "e_perde", "tur": "perde", "x": 0, "y": UST, "w": PW, "h": PH - UST, "bayrak": "engel_diyalog"},
        {"id": "e_kutu", "tur": "diyalog", "x": 200, "y": 96, "w": 360, "h": 196, "bayrak": "engel_diyalog",
         "baslik": T("192.168.1.23 engellensin mi?", "Block 192.168.1.23?")},
        {"id": "e_metin", "tur": "metin", "x": 216, "y": 126, "w": 328, "h": 80, "bayrak": "engel_diyalog",
         "sar": True, "boyut": 8.2, "renk": "soluk",
         "metin": T("Bu adresten gelen tüm bağlantılar güvenlik duvarında reddedilecek. Adres tanıdığınız bir "
                    "cihaza aitse (öğretmen bilgisayarı, yazıcı) engellemeyin; “Yok say” seçeneğini kullanın.",
                    "All connections from this address will be rejected by the firewall. If the address belongs "
                    "to a device you know (teacher computer, printer), do not block it; use “Ignore” instead.")},
        {"id": "e_sure_et", "tur": "metin", "x": 216, "y": 214, "w": 60, "h": 14, "bayrak": "engel_diyalog",
         "metin": T("Süre", "Duration"), "boyut": 8.4, "renk": "soluk"},
        {"id": "e_sure", "tur": "secim", "x": 280, "y": 209, "w": 150, "h": 24, "bayrak": "engel_diyalog",
         "secenekler": [T("15 dakika", "15 minutes"), T("1 saat", "1 hour"), T("24 saat", "24 hours"),
                        T("Süresiz", "Indefinite")], "deger": ""},
        {"id": "e_iptal", "tur": "dugme", "x": 360, "y": 250, "w": 90, "h": 28, "bayrak": "engel_diyalog",
         "metin": T("İptal", "Cancel")},
        {"id": "e_tamam", "tur": "dugme", "x": 458, "y": 250, "w": 90, "h": 28, "bayrak": "engel_diyalog",
         "birincil": True, "metin": T("Engelle", "Block")},
    ]
    return {"genislik": PW, "yukseklik": PH, "vurgu": "carotpot", "sayfa": "pano",
            "baslik": T("CarotPot", "CarotPot"), "ogeler": o}


# ---------------------------------------------------------------------------
# Carotene
# ---------------------------------------------------------------------------
def carotene_sahnesi() -> dict:
    menu = [("ct:tarama", T("Tarama", "Scan"), "arama"), ("ct:karantina", T("Karantina", "Quarantine"), "kilit"),
            ("ct:tanim", T("Virüs tanımları", "Virus definitions"), "indir"),
            ("ct:gecmis", T("Tarama geçmişi", "Scan history"), "saat")]
    o = _yan(T("Carotene", "Carotene"), T("Virüs taraması", "Virus scanner"), menu, adim=26, y0=62,
             baslangic_aktif="ct:tarama")
    o += [
        # --- tarama
        {"id": "t_baslik", "tur": "metin", "x": 172, "y": 34, "w": 300, "h": 20, "sayfa": "tarama",
         "metin": T("Tarama", "Scan"), "boyut": 14, "kalin": True},
        {"id": "t_tanim", "tur": "rozet", "x": 560, "y": 36, "w": 188, "h": 22, "sayfa": "tarama", "renk": "yesil",
         "metin": T("Tanımlar: bugün", "Definitions: today")},
        {"id": "t_giris", "tur": "metin", "x": 172, "y": 64, "w": 576, "h": 30, "sayfa": "tarama", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("Dosyalar ClamAV ile bilinen zararlı yazılım imzalarına karşı taranır. Tarama yalnızca siz "
                    "başlattığınızda çalışır. Temiz sonuç, dosyaların güvenli olduğunu garanti etmez.",
                    "Files are scanned with ClamAV against known malware signatures. A scan runs only when you "
                    "start it. A clean result does not guarantee the files are safe.")},
        {"id": "k_hizli", "tur": "kart", "x": 170, "y": 112, "w": 578, "h": 80, "sayfa": "tarama"},
        {"id": "k_hizli_ad", "tur": "metin", "x": 184, "y": 124, "w": 360, "h": 16, "sayfa": "tarama",
         "metin": T("Hızlı tarama", "Quick scan"), "boyut": 10, "kalin": True},
        {"id": "k_hizli_acik", "tur": "metin", "x": 184, "y": 146, "w": 420, "h": 32, "sayfa": "tarama", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("İndirilenler ve Masaüstü klasörleri ile ana klasördeki dosyalar taranır.",
                    "Scans the Downloads and Desktop folders and the files in the home folder.")},
        {"id": "k_hizli_tara", "tur": "dugme", "x": 648, "y": 138, "w": 88, "h": 28, "sayfa": "tarama",
         "birincil": True, "metin": T("Tara", "Scan")},
        {"id": "k_ev", "tur": "kart", "x": 170, "y": 200, "w": 578, "h": 80, "sayfa": "tarama"},
        {"id": "k_ev_ad", "tur": "metin", "x": 184, "y": 212, "w": 360, "h": 16, "sayfa": "tarama",
         "metin": T("Ana klasörün tamamı", "Entire home folder"), "boyut": 10, "kalin": True},
        {"id": "k_ev_acik", "tur": "metin", "x": 184, "y": 234, "w": 420, "h": 32, "sayfa": "tarama", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("Ana klasör tüm alt klasörleriyle taranır. Dosya sayısına göre uzun sürebilir.",
                    "Scans the home folder with all subfolders. It may take a long time.")},
        {"id": "k_ev_tara", "tur": "dugme", "x": 648, "y": 226, "w": 88, "h": 28, "sayfa": "tarama",
         "metin": T("Tara", "Scan")},
        {"id": "k_ozel", "tur": "kart", "x": 170, "y": 288, "w": 578, "h": 80, "sayfa": "tarama"},
        {"id": "k_ozel_ad", "tur": "metin", "x": 184, "y": 300, "w": 360, "h": 16, "sayfa": "tarama",
         "metin": T("Özel tarama", "Custom scan"), "boyut": 10, "kalin": True},
        {"id": "k_ozel_acik", "tur": "metin", "x": 184, "y": 322, "w": 360, "h": 32, "sayfa": "tarama", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("Seçilen bir klasör ya da dosya taranır.", "Scans a selected folder or file.")},
        {"id": "k_klasor", "tur": "dugme", "x": 540, "y": 314, "w": 100, "h": 28, "sayfa": "tarama",
         "metin": T("Klasör seç", "Choose folder")},
        {"id": "k_dosya", "tur": "dugme", "x": 648, "y": 314, "w": 88, "h": 28, "sayfa": "tarama",
         "metin": T("Dosya seç", "Choose file")},
        # --- tarama suruyor
        {"id": "r_baslik", "tur": "metin", "x": 172, "y": 34, "w": 400, "h": 20, "sayfa": "calisiyor",
         "metin": T("Tarama sürüyor", "Scan in progress"), "boyut": 14, "kalin": True},
        {"id": "r_kart", "tur": "kart", "x": 170, "y": 82, "w": 578, "h": 130, "sayfa": "calisiyor"},
        {"id": "r_ilerleme", "tur": "ilerleme", "x": 190, "y": 108, "w": 538, "h": 10, "sayfa": "calisiyor",
         "ilerleme": 0.0},
        {"id": "r_sayac", "tur": "metin", "x": 190, "y": 134, "w": 538, "h": 16, "sayfa": "calisiyor",
         "metin": T("Taranan dosya: 0 · Bulgu: 0", "Files scanned: 0 · Findings: 0"), "boyut": 9.5, "kalin": True},
        {"id": "r_not", "tur": "metin", "x": 190, "y": 160, "w": 538, "h": 30, "sayfa": "calisiyor", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("Virüs tanımları belleğe yükleniyor. Bu adım yaklaşık 10 saniye sürer.",
                    "Loading virus definitions into memory. This step takes about 10 seconds.")},
        {"id": "r_durdur", "tur": "dugme", "x": 640, "y": 224, "w": 108, "h": 28, "sayfa": "calisiyor",
         "metin": T("Durdur", "Stop")},
        # --- sonuc
        {"id": "s_baslik", "tur": "metin", "x": 172, "y": 34, "w": 500, "h": 20, "sayfa": "sonuc",
         "metin": T("1 tehdit bulundu", "1 threat found"), "boyut": 14, "kalin": True, "renk": "kirmizi"},
        {"id": "s_ozet", "tur": "metin", "x": 172, "y": 58, "w": 500, "h": 14, "sayfa": "sonuc", "boyut": 8.4,
         "renk": "soluk", "metin": T("1.482 dosya tarandı, 38 sn sürdü.", "1,482 files scanned in 38 s.")},
        {"id": "s_kart", "tur": "kart", "x": 170, "y": 86, "w": 578, "h": 112, "sayfa": "sonuc"},
        {"id": "s_yol", "tur": "metin", "x": 184, "y": 98, "w": 550, "h": 16, "sayfa": "sonuc", "mono": True,
         "boyut": 8.4, "metin": "~/İndirilenler/eicar.com.txt"},
        {"id": "s_imza", "tur": "rozet", "x": 184, "y": 122, "w": 220, "h": 20, "sayfa": "sonuc", "renk": "kirmizi",
         "metin": "Win.Test.EICAR_HDB-1"},
        {"id": "s_ipucu", "tur": "metin", "x": 184, "y": 150, "w": 550, "h": 28, "sayfa": "sonuc", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("Önerilen işlem karantinadır: dosya çalıştırılamaz hâle getirilir ve gerekirse geri yüklenebilir.",
                    "Quarantine is the recommended action: the file is made non-executable and can be restored.")},
        {"id": "s_karantina", "tur": "dugme", "x": 170, "y": 208, "w": 130, "h": 28, "sayfa": "sonuc",
         "birincil": True, "metin": T("Karantinaya al", "Quarantine")},
        {"id": "s_sil", "tur": "dugme", "x": 308, "y": 208, "w": 80, "h": 28, "sayfa": "sonuc",
         "metin": T("Sil", "Delete")},
        {"id": "s_yoksay", "tur": "dugme", "x": 396, "y": 208, "w": 90, "h": 28, "sayfa": "sonuc",
         "metin": T("Yok say", "Ignore")},
        {"id": "s_bitti", "tur": "rozet", "x": 170, "y": 252, "w": 230, "h": 22, "sayfa": "sonuc", "bayrak": "karantinada",
         "renk": "yesil", "metin": T("Karantinaya alındı.", "Moved to quarantine.")},
        # --- karantina
        {"id": "q_baslik", "tur": "metin", "x": 172, "y": 34, "w": 400, "h": 20, "sayfa": "karantina",
         "metin": T("Karantina", "Quarantine"), "boyut": 14, "kalin": True},
        {"id": "q_giris", "tur": "metin", "x": 172, "y": 60, "w": 576, "h": 30, "sayfa": "karantina", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("Karantinadaki dosyalar yalnızca sizin erişebildiğiniz bir klasörde, çalıştırılamaz biçimde "
                    "saklanır. Geri yüklenen dosya yeniden tehlikeli olabilir.",
                    "Files in quarantine are kept in a folder only you can access, in a non-executable form. A "
                    "restored file may be dangerous again.")},
        {"id": "q_kart", "tur": "kart", "x": 170, "y": 100, "w": 578, "h": 64, "sayfa": "karantina"},
        {"id": "q_yol", "tur": "metin", "x": 184, "y": 110, "w": 380, "h": 16, "sayfa": "karantina", "mono": True,
         "boyut": 8.4, "metin": "~/İndirilenler/eicar.com.txt"},
        {"id": "q_imza", "tur": "metin", "x": 184, "y": 132, "w": 380, "h": 16, "sayfa": "karantina",
         "boyut": 8.2, "renk": "soluk", "metin": T("Win.Test.EICAR_HDB-1 · bugün", "Win.Test.EICAR_HDB-1 · today")},
        {"id": "q_geri", "tur": "dugme", "x": 560, "y": 114, "w": 90, "h": 28, "sayfa": "karantina",
         "metin": T("Geri yükle", "Restore")},
        {"id": "q_sil", "tur": "dugme", "x": 658, "y": 114, "w": 80, "h": 28, "sayfa": "karantina",
         "metin": T("Sil", "Delete")},
        # --- tanimlar
        {"id": "d_baslik", "tur": "metin", "x": 172, "y": 34, "w": 400, "h": 20, "sayfa": "tanim",
         "metin": T("Virüs tanımları", "Virus definitions"), "boyut": 14, "kalin": True},
        {"id": "d_kart", "tur": "kart", "x": 170, "y": 82, "w": 578, "h": 110, "sayfa": "tanim"},
        {"id": "d_not", "tur": "metin", "x": 184, "y": 96, "w": 540, "h": 30, "sayfa": "tanim", "sar": True,
         "boyut": 9, "metin": T("Virüs tanımları: bugün (0 gün önce)", "Virus definitions: today (0 days ago)")},
        {"id": "d_acik", "tur": "metin", "x": 184, "y": 122, "w": 540, "h": 30, "sayfa": "tanim", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("Eski tanımlarla yapılan taramada yeni tehditler bulunamaz; tanımları ara sıra güncelleyin.",
                    "A scan with old definitions cannot find new threats; update them now and then.")},
        {"id": "d_guncelle", "tur": "dugme", "x": 184, "y": 154, "w": 140, "h": 28, "sayfa": "tanim",
         "birincil": True, "metin": T("Tanımları güncelle", "Update definitions")},
    ]
    return {"genislik": PW, "yukseklik": PH, "vurgu": "carotene", "sayfa": "tarama",
            "baslik": T("Carotene", "Carotene"), "ogeler": o}


# ---------------------------------------------------------------------------
# Genel bakis (uygulama haritasi)
# ---------------------------------------------------------------------------
KAROLAR = [
    ("panel", "kalkan", T("Güvenlik Paneli", "Security Panel"), T("10 araç, form ile", "10 tools, as forms")),
    ("saglik", "kalp", T("Sistem Sağlığı", "System Health"), T("Güvenlik denetimi", "Security check-up")),
    ("usb", "usb", T("USB Denetimi", "USB Check"), T("Takılan aygıtı tara", "Check plugged-in drives")),
    ("carotpot", "altigen", T("CarotPot", "CarotPot"), T("Ağ tuzağı", "Network trap")),
    ("carotene", "arama", T("Carotene", "Carotene"), T("Virüs taraması", "Virus scanner")),
    ("magaza", "canta", T("Mağaza", "Store"), T("Araç kur", "Install tools")),
    ("poligon", "oyun", T("Poligon", "Poligon"), T("Güvenli pratik", "Safe practice")),
]


def giris_sahnesi() -> dict:
    o = [{"id": "g_baslik", "tur": "metin", "x": 24, "y": 40, "w": 700, "h": 20, "metin":
          T("CarotOS güvenlik uygulamaları", "CarotOS security applications"), "boyut": 14, "kalin": True},
         {"id": "g_alt", "tur": "metin", "x": 24, "y": 64, "w": 700, "h": 14, "boyut": 8.6, "renk": "soluk",
          "metin": T("Her biri farklı bir soruya cevap verir: bir şeye bakıyor, bir şeyi tarıyor, ya da pratik yaptırıyor.",
                     "Each one answers a different question: it looks at something, scans something, or lets you practise.")}]
    kw, kh, bosluk = 160, 118, 14
    for i, (kimlik, simge, ad, alt) in enumerate(KAROLAR):
        sira, sutun = divmod(i, 4)
        o.append({"id": "karo:" + kimlik, "tur": "karo", "x": 24 + sutun * (kw + bosluk), "y": 100 + sira * (kh + 18),
                  "w": kw, "h": kh, "simge": simge, "metin": ad, "alt": alt, "aktif": False})
    return {"genislik": PW, "yukseklik": PH, "vurgu": "karsilama", "sayfa": None,
            "baslik": T("CarotOS", "CarotOS"), "ogeler": o}
