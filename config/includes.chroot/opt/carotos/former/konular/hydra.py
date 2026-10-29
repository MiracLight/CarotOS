# -*- coding: utf-8 -*-
from former_zaman import T, balon, git, yaz
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "hydra",
    "tagline": T("Oturum açma kaba kuvvet testi", "Login brute-force testing"),
    "ne": T("SSH, FTP gibi servislere kullanıcı ve parola listeleriyle giriş denemeleri yapar.",
            "Tries logins against services like SSH and FTP using username and password lists."),
    "ne_zaman": T("Kendi servislerinin zayıf parolalara karşı ne kadar dayanıklı olduğunu sınarken.",
                  "When testing how well your own services resist weak passwords."),
    "ornek": T("Hedef IP + servis + kullanıcı/parola listeleri", "Target IP + service + user/pass lists"),
    "root": False,
    "alanlar": [
        {"id": "target", "ad": T("Hedef IP", "Target IP"), "tur": "alan",
         "yer": T("örn. 192.168.1.10", "e.g. 192.168.1.10")},
        {"id": "service", "ad": T("Servis", "Service"), "tur": "alan", "varsayilan": "ssh",
         "yer": T("örn. ssh, ftp", "e.g. ssh, ftp")},
        {"id": "userlist", "ad": T("Kullanıcı listesi", "Username list"), "tur": "dosya"},
        {"id": "passlist", "ad": T("Parola listesi", "Password list"), "tur": "dosya"},
    ],
}

CIKTI = [
    "[DATA] max 16 tasks per 1 server, overall 16 tasks, 12 login tries",
    "[DATA] attacking ssh://192.168.1.10:22/",
    "[ATTEMPT] target 192.168.1.10 - login \"ogrenci\" - pass \"123456\" - 1 of 12",
    "[ATTEMPT] target 192.168.1.10 - login \"ogrenci\" - pass \"parola1\" - 2 of 12",
    "[22][ssh] host: 192.168.1.10   login: ogrenci   password: 123456",
    "1 of 1 target successfully completed, 1 valid password found",
]


def konu():
    adimlar = arac_sec("hydra") + [
        git("alan:target"),
        balon("alan:target", T("Hedef", "Target"),
              T("Giriş denemesi yapılacak makinenin adresi. Bu, kendi kurduğun ve kendi hesaplarınla "
                "yönettiğin bir test sunucusu olmalı — örneğin aynı ağda ayrı bir sanal makine.",
                "The address of the machine to try logins against. This should be a test server you set up "
                "and manage with your own accounts — for example a separate virtual machine on the same "
                "network.")),
        git("alan:service"),
        balon("alan:service", T("Servis", "Service"),
              T("Hangi giriş servisi deneniyor: ssh uzaktan bağlantı, ftp dosya sunucusu gibi. Panel sana "
                "uygun olanı seçtirir, hydra arkada o servisin giriş protokolünü konuşur.",
                "Which login service is being tried: ssh is remote login, ftp is a file server, and so on. "
                "The panel lets you pick the right one; hydra speaks that service's login protocol behind the "
                "scenes.")),
        git("alan:userlist"),
        balon("alan:userlist", T("Kullanıcı listesi", "Username list"),
              T("Denenecek kullanıcı adlarının olduğu dosya. Gerçek bir ortamda çoğu zaman “admin”, “root” "
                "gibi birkaç tahmin edilebilir isim yeterli olur; bu yüzden tahmin edilebilir kullanıcı "
                "adları da bir risktir.",
                "The file with the usernames to try. In a real setting, a handful of guessable names like "
                "“admin” or “root” is often enough; that is why guessable usernames are a risk too.")),
        yaz("alan:userlist", "~/kullanicilar.txt"),
        git("alan:passlist"),
        balon("alan:passlist", T("Parola listesi", "Password list"),
              T("Denenecek parolaların olduğu dosya. Panel her kullanıcı/parola çiftini sırayla dener ve "
                "sunucunun cevabına bakar.",
                "The file with the passwords to try. The panel tries each username/password pair in turn and "
                "watches the server's answer.")),
        yaz("alan:passlist", "~/parolalar.txt"),
    ] + calistir("hydra -L kullanicilar.txt -P parolalar.txt 192.168.1.10 ssh", CIKTI) + [
        balon("cikti", T("Sonucu oku", "Read the result"),
              T("[ATTEMPT] satırları tek tek denemeleri gösterir. Bir çift tutarsa parantezsiz bir satırda "
                "“login: … password: …” yazar — bu, o hesabın zayıf bir parolayla korunduğu anlamına gelir.",
                "[ATTEMPT] lines show each try. When a pair works, a line without brackets reads “login: … "
                "password: …” — this means that account is protected by a weak password."), "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("hydra, bir giriş ekranına art arda kullanıcı adı/parola çiftleri dener ve hangisinin "
                    "kabul edildiğine bakar. Bunu bir kapıdaki kilidi, elindeki bir anahtar demetindeki her "
                    "anahtarı sırayla deneyerek açmaya çalışmaya benzetebilirsin.",
                    "hydra tries username/password pairs against a login screen one after another and sees "
                    "which is accepted. You can compare it to trying every key on a keyring on a door lock, "
                    "one after the other.")),
            ("p", T("Bunun gösterdiği şey basit: zayıf ya da tahmin edilebilir bir parola, bu tür bir "
                    "aracın işini saniyeler içine indirir. Amaç kendi servislerinin buna karşı ne kadar "
                    "dayanıklı olduğunu önceden görmektir.",
                    "What this shows is simple: a weak or guessable password turns this kind of tool's job "
                    "into seconds. The goal is to see in advance how resistant your own services are to "
                    "this.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan hydra'yı seç.", "Pick hydra on the left."),
                T("Hedef IP'ye kendi test sunucunun adresini yaz.",
                  "Type your own test server's address in Target IP."),
                T("Servisi seç (varsayılan ssh).", "Pick the service (default ssh)."),
                T("Kullanıcı ve parola listesi dosyalarını seç.", "Pick the username and password list files."),
                T("Çalıştır'a bas. Deneme sayısı arttıkça süre uzar.",
                  "Press Run. The more attempts, the longer it takes."),
            ]),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[2:5])),
            ("not", T("Bu araç gürültülüdür: her başarısız deneme sunucunun kayıtlarında (log) iz bırakır ve "
                      "CarotPot ya da fail2ban gibi araçlar tarafından kolayca fark edilir. " +
                      T_DENEME_UYARISI["tr"],
                      "This tool is noisy: every failed attempt leaves a trace in the server's logs and is "
                      "easily noticed by tools like CarotPot or fail2ban. " + T_DENEME_UYARISI["en"])),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("İkinci bir test makinende zayıf bir parolalı hesap aç, hydra ile bulduğunu gör.",
                  "Open an account with a weak password on a second test machine, and see hydra find it."),
                T("Aynı hesaba uzun ve rastgele bir parola ver, denemenin artık başarısız olduğunu gör.",
                  "Give the same account a long, random password, and see the attempt now fail."),
                T("fail2ban konusunu da oku; bu iki araç birbirinin tam karşılığıdır — biri saldırıyı "
                  "dener, öteki onu engeller.",
                  "Also read the fail2ban topic; these two tools are each other's counterpart — one tries "
                  "the attack, the other blocks it."),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Bu aracı yalnızca kendi kurduğun, kendi hesaplarınla yönettiğin bir laboratuvar "
                        "makinesinde kullan. Başka birinin hesabına veya sunucusuna izinsiz giriş denemek "
                        "ciddi bir suçtur; hesap kilitlenmelerine ve servis kesintilerine de yol açabilir.",
                        "Use this tool only on a lab machine you set up and manage with your own accounts. "
                        "Trying to log into someone else's account or server without permission is a serious "
                        "crime; it can also cause account lockouts and service outages.")),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "hydra -L kullanicilar.txt -P parolalar.txt 192.168.1.10 ssh"),
            ("p", T("-L kullanıcı listesi, -P parola listesi anlamına gelir; tek bir kullanıcı için -l "
                    "kullanıcı_adı kullanılır.",
                    "-L means the username list, -P the password list; for a single user, -l username is "
                    "used.")),
        ]),
    ]
    return _konu("hydra", ARAC, adimlar, bolumler, ikon="anahtar")
