# -*- coding: utf-8 -*-
"""Savunmaci gorunumu: Poligon ogrenci uygulamasindaki "Savunmaci gorunumu" penceresi (olay gunlugu, bulgular, ufw/fail2ban)."""
from former_sahneler import PH, PW
from former_zaman import T, ayarla, balon, bekle, cikti, git, tikla

KOMUT = ["python3", "/opt/carotos/poligon/ogrenci_uygulama.py"]


def _sahne():
    o = [
        {"id": "s_baslik", "tur": "metin", "x": 24, "y": 38, "w": 300, "h": 20, "boyut": 14, "kalin": True,
         "metin": T("Savunmacı görünümü", "Defender view")},
        {"id": "s_ufw", "tur": "rozet", "x": 560, "y": 40, "w": 84, "h": 20, "renk": "gri",
         "metin": T("ufw: kapalı", "ufw: off")},
        {"id": "s_f2b", "tur": "rozet", "x": 650, "y": 40, "w": 96, "h": 20, "renk": "yesil",
         "metin": T("fail2ban: açık", "fail2ban: on")},
        {"id": "s_alt", "tur": "metin", "x": 24, "y": 66, "w": 712, "h": 14, "boyut": 8.4, "renk": "soluk",
         "metin": T("Saldırının sahte servislerde bıraktığı izleri gör.",
                    "See the traces your attack left on the fake services.")},
        {"id": "s_bulgu_et", "tur": "metin", "x": 24, "y": 96, "w": 300, "h": 14, "boyut": 9, "kalin": True,
         "metin": T("Bulgular", "Findings")},
        {"id": "s_bos", "tur": "metin", "x": 24, "y": 120, "w": 712, "h": 14, "boyut": 8.4, "renk": "soluk",
         "bayrak": "!bulgu", "metin": T("Şimdilik şüpheli bir iz yok.", "No suspicious traces yet.")},
        {"id": "s_bulgu_kart", "tur": "kart", "x": 22, "y": 116, "w": 716, "h": 88, "bayrak": "bulgu"},
        {"id": "s_bulgu_ad", "tur": "metin", "x": 36, "y": 126, "w": 360, "h": 16, "boyut": 9, "kalin": True,
         "bayrak": "bulgu", "metin": T("Parola deneme saldırısı", "Password guessing attack")},
        {"id": "s_bulgu_onem", "tur": "rozet", "x": 220, "y": 125, "w": 100, "h": 18, "renk": "kirmizi",
         "bayrak": "bulgu", "metin": T("Önem: yüksek", "Severity: high")},
        {"id": "s_bulgu_ne", "tur": "metin", "x": 36, "y": 148, "w": 688, "h": 14, "boyut": 8.2, "sar": True,
         "bayrak": "bulgu", "metin": T("Kısa sürede çok sayıda başarısız giriş görüldü.",
                                       "Many failed logins were seen in a short time.")},
        {"id": "s_bulgu_sav", "tur": "metin", "x": 36, "y": 168, "w": 688, "h": 28, "boyut": 8.2, "sar": True,
         "renk": "soluk", "bayrak": "bulgu",
         "metin": T("Savunma: fail2ban birkaç başarısız denemeden sonra o adresi geçici olarak engeller.",
                    "Defense: fail2ban temporarily blocks that address after a few failed attempts.")},
        {"id": "s_gunluk_et", "tur": "metin", "x": 24, "y": 222, "w": 300, "h": 14, "boyut": 9, "kalin": True,
         "metin": T("Olay günlüğü", "Event log")},
        {"id": "s_temizle", "tur": "dugme", "x": 600, "y": 216, "w": 138, "h": 26,
         "metin": T("Günlüğü temizle", "Clear the log")},
        {"id": "s_gunluk", "tur": "cikti", "x": 22, "y": 250, "w": 716, "h": 112, "satirlar": []},
    ]
    return {"genislik": PW, "yukseklik": PH, "vurgu": "guvenlik", "sayfa": None,
            "baslik": T("CarotOS Poligon · Savunmacı görünümü", "CarotOS Poligon · Defender view"), "ogeler": o}


def konu():
    adimlar = [
        balon("s_baslik", T("Saldıran ve savunan", "Attacker and defender"),
              T("Bir saldırıyı anlamanın en iyi yolu, karşı tarafın ne gördüğüne bakmaktır. Savunmacı görünümü, "
                "Poligon'daki sahte servislerin tuttuğu olay günlüğünü gösterir: kim bağlandı, hangi port, kaç kez.",
                "The best way to understand an attack is to look at what the other side sees. The defender view "
                "shows the event log kept by Poligon's fake services: who connected, which port, how many times."),
              "alt"),
        git("s_gunluk"),
        cikti("s_gunluk", [T("15:58:51  Giriş servisi   Bağlantı           :2121",
                             "15:58:51  Login service   Connection         :2121"),
                           T("15:58:52  Giriş servisi   Başarısız giriş    admin",
                             "15:58:52  Login service   Failed login       admin"),
                           T("15:58:52  Giriş servisi   Başarısız giriş    admin",
                             "15:58:52  Login service   Failed login       admin"),
                           T("15:58:53  Giriş servisi   Başarısız giriş    admin",
                             "15:58:53  Login service   Failed login       admin")]),
        balon("s_gunluk", T("Olay günlüğü", "The event log"),
              T("Her satır bir olaydır. Günlüğe yalnızca meta veri yazılır: servis, olay türü, port ve kısa bir "
                "ayrıntı. Denenen parolalar günlüğe girmez. Günlük yalnızca bellekte durur, diske yazılmaz.",
                "Each line is an event. Only metadata is logged: the service, the kind of event, the port and a "
                "short detail. The passwords that were tried are not logged. The log lives only in memory and is "
                "never written to disk."), "ust"),
        cikti("s_gunluk", [T("15:58:53  Giriş servisi   Başarısız giriş    admin",
                             "15:58:53  Login service   Failed login       admin"),
                           T("15:58:54  Giriş servisi   Başarısız giriş    admin",
                             "15:58:54  Login service   Failed login       admin"),
                           T("15:58:54  Giriş servisi   Başarısız giriş    admin",
                             "15:58:54  Login service   Failed login       admin")]),
        ayarla(_bayrak={"bulgu": True}),
        balon("s_bulgu_ad", T("Bulgular", "Findings"),
              T("Uygulama günlükteki örüntüleri okur. Kısa sürede çok başarısız giriş, birçok farklı porta bağlantı ya "
                "da çok sayıda “bulunamadı” isteği görürse bunu bir bulgu olarak gösterir ve ilgili savunmayı anlatır.",
                "The app reads patterns in the log. If it sees many failed logins, connections to many different "
                "ports or many “not found” requests in a short time, it shows a finding and explains the matching "
                "defense."), "alt"),
        git("s_f2b"),
        balon("s_f2b", T("ufw ve fail2ban", "ufw and fail2ban"),
              T("Sağ üstteki rozetler güvenlik duvarının (ufw) ve fail2ban'ın bu bilgisayarda açık olup olmadığını "
                "gösterir. Yalnızca durumu okur; hiçbir şeyi açıp kapatmaz.",
                "The badges at the top right show whether the firewall (ufw) and fail2ban are on for this computer. "
                "They only read the status; they do not switch anything on or off."), "alt"),
        git("s_temizle"),
        balon("s_temizle", T("Günlüğü temizle", "Clear the log"),
              T("Yeni bir deneme öncesi günlüğü temizlersen yalnızca o denemenin izlerini görürsün.",
                "If you clear the log before a new attempt, you see only the traces of that attempt."), "ust"),
        bekle(300),
    ]
    bolumler = [
        (T("Neden savunmacı gözüyle bakmalı", "Why look through a defender's eyes"), [
            ("p", T("Saldırgan hedefin içeri girmesini görür; savunmacı ise arkada kalan izi görür. İkisini de "
                    "bilirsen hem saldırıyı daha iyi anlar hem de kendi sistemini nasıl koruyacağını öğrenirsin.",
                    "An attacker sees getting in; a defender sees the trail left behind. If you know both you "
                    "understand the attack better and learn how to protect your own system.")),
        ]),
        (T("Nasıl kullanırım", "How do I use it"), [
            ("liste", [
                T("Poligon öğrenci uygulamasında bir görev açıkken üst çubuktaki “Savunmacı görünümü”ne bas.",
                  "While a task is open in the Poligon student app, press “Defender view” in the top bar."),
                T("Görevde bir araç çalıştır (örneğin port taraması ya da parola denemesi).",
                  "Run a tool in the task (for example a port scan or password guessing)."),
                T("Pencerede olayların ve bulguların belirmesini izle, savunma açıklamasını oku.",
                  "Watch the events and findings appear in the window and read the defense explanation."),
            ]),
        ]),
        (T("Sınır", "The limit"), [
            ("not", T("Bu görünüm yalnızca Poligon'un kendi sahte servislerini gösterir. Gerçek bir sistemin "
                      "günlüklerinin yerini tutmaz; amaç, izlerin nasıl göründüğünü öğretmektir.",
                      "This view shows only Poligon's own fake services. It does not replace the logs of a real "
                      "system; the goal is to teach what traces look like.")),
        ]),
    ]
    return {
        "id": "savunma", "grup": "uygulamalar", "ikon": "kalkan",
        "ad": T("Savunmacı görünümü", "Defender view"),
        "alt": T("Saldırının bıraktığı izler", "The traces an attack leaves"),
        "ozet": T("Poligon'da olay günlüğü, bulgular ve ufw/fail2ban durumu.",
                  "In Poligon: the event log, findings and the ufw/fail2ban status."),
        "vurgu": "guvenlik", "sahne": _sahne(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": {"ad": T("Poligon (Öğrenci)", "Poligon (Student)"), "komut": KOMUT}, "root": False,
    }
