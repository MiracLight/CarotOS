# -*- coding: utf-8 -*-
"""Disk sifreleme ve swap: Sistem Sagligi'ndaki "Swap sifreleme" denetimi ve "Disk swap'ini kapat" eylemi."""
from former_sahneler import PH, PW
from former_zaman import T, ayarla, balon, bekle, git, tikla

KOMUT = ["python3", "/opt/carotos/health/carotos-health.py"]

SIFRESIZ = T("Diskte şifresiz swap var (/dev/sda5): bellek içeriği (parolalar, anahtarlar) diske yazılmış olabilir.",
             "Unencrypted swap on disk (/dev/sda5): memory contents (passwords, keys) may be written to disk.")
TEMIZ = T("Diskte swap yok; yalnızca RAM içinde sıkıştırılmış zram kullanılıyor.",
          "There is no swap on disk; only RAM-compressed zram is used.")


def _sahne():
    o = [
        {"id": "h_baslik", "tur": "metin", "x": 24, "y": 40, "w": 500, "h": 20, "boyut": 14, "kalin": True,
         "metin": T("Sistem Sağlığı", "System Health")},
        {"id": "h_alt", "tur": "metin", "x": 24, "y": 64, "w": 700, "h": 14, "boyut": 8.4, "renk": "soluk",
         "metin": T("Sistemin güvenlik ve sağlık denetimleri.", "Your system's security and health checks.")},
        {"id": "h_kart", "tur": "kart", "x": 22, "y": 92, "w": 716, "h": 118},
        {"id": "h_disk", "tur": "satir", "x": 32, "y": 102, "w": 696, "h": 26, "renk": "yesil",
         "metin": T("Disk alanı: yeterli", "Disk space: enough")},
        {"id": "h_swap", "tur": "satir", "x": 32, "y": 132, "w": 696, "h": 26, "renk": "sari",
         "metin": T("Swap şifreleme: dikkat", "Swap encryption: attention")},
        {"id": "h_guv", "tur": "satir", "x": 32, "y": 162, "w": 696, "h": 26, "renk": "yesil",
         "metin": T("Güvenlik duvarı: açık", "Firewall: on")},
        {"id": "h_detay_kart", "tur": "kart", "x": 22, "y": 222, "w": 716, "h": 96},
        {"id": "h_detay", "tur": "metin", "x": 36, "y": 234, "w": 688, "h": 40, "sar": True, "boyut": 8.4,
         "metin": T("Bir satırı seç, ayrıntısı burada görünür.", "Pick a row and its details appear here.")},
        {"id": "h_buton", "tur": "dugme", "x": 36, "y": 282, "w": 200, "h": 28,
         "metin": T("Disk swap'ını kapat", "Disable disk swap")},
        {"id": "h_not", "tur": "metin", "x": 24, "y": 332, "w": 712, "h": 30, "sar": True, "boyut": 8.2,
         "renk": "soluk",
         "metin": T("zram RAM içinde çalışır ve diske hiçbir şey yazmaz; düğme ona dokunmaz.",
                    "zram works inside RAM and writes nothing to disk; the button leaves it alone.")},
    ]
    return {"genislik": PW, "yukseklik": PH, "vurgu": "guvenlik", "sayfa": None,
            "baslik": T("CarotOS Sistem Sağlığı", "CarotOS System Health"), "ogeler": o}


def konu():
    adimlar = [
        balon("h_baslik", T("Swap neden önemli", "Why swap matters"),
              T("Bellek dolunca sistem bellek içeriğini diske yazar; buna swap denir. Şifresiz bir swap, "
                "parolalarını ve anahtarlarını diskte bırakabilir. CarotOS varsayılan olarak RAM içinde "
                "sıkıştırılmış bir swap (zram) kullanır; bu diske hiçbir şey yazmaz.",
                "When memory fills up, the system writes memory contents to disk; that is called swap. "
                "Unencrypted swap can leave your passwords and keys on the disk. By default CarotOS uses a swap "
                "compressed inside RAM (zram), which writes nothing to the disk."), "alt"),
        git("h_swap"),
        tikla("h_swap", ayarla={"h_detay": {"metin": SIFRESIZ}}),
        balon("h_detay", T("Swap şifreleme denetimi", "The Swap encryption check"),
              T("Sistem Sağlığı'ndaki bu denetim, diskte şifresiz swap olup olmadığına bakar. Burada örnek olarak "
                "bir uyarı görüyorsun; senin bilgisayarında büyük ihtimalle yeşil olur.",
                "This System Health check looks for unencrypted swap on the disk. Here you see a warning as an "
                "example; on your computer it will most likely be green."), "alt"),
        git("h_buton"),
        balon("h_buton", T("Disk swap'ını kapat", "Disable disk swap"),
              T("Düğme önce onay ister, sonra diskteki swap'ı kapatır ve ayar dosyasının (fstab) yedeğini alır. "
                "Yani geri dönüş yolu var. zram'a dokunmaz.",
                "The button first asks for confirmation, then turns off the swap on disk and backs up the "
                "settings file (fstab), so there is a way back. It leaves zram alone."), "ust"),
        tikla("h_buton", ayarla={"h_swap": {"renk": "yesil", "metin": T("Swap şifreleme: tamam", "Swap encryption: OK")},
                                 "h_detay": {"metin": TEMIZ}}),
        bekle(300),
        balon("h_detay", T("Sonuç", "The result"),
              T("Artık diske hiçbir şey yazılmıyor. Disk şifreleme ayrı bir konudur: onu kurulumda seçersin.",
                "Nothing is written to the disk now. Disk encryption is a separate matter: you choose it during "
                "installation."), "alt"),
    ]
    bolumler = [
        (T("Disk şifreleme", "Disk encryption"), [
            ("p", T("Bilgisayarın kaybolur ya da çalınırsa, diski başka bir bilgisayara takan kişi şifresiz "
                    "dosyaları okuyabilir. Tam disk şifreleme (LUKS) bunu önler: disk, parola girilmeden açılmaz.",
                    "If your computer is lost or stolen, whoever puts its disk in another computer can read the "
                    "files that aren't encrypted. Full-disk encryption (LUKS) prevents that: the disk won't open "
                    "without the password.")),
            ("not", T("Disk şifrelemeyi kurulum sırasında, diski bölümlendirirken “şifreli LVM” seçeneğiyle "
                      "açarsın. Sonradan eklemek zordur. Parolayı unutursan verilerin kurtarılamaz.",
                      "You turn on disk encryption during installation, by choosing the “encrypted LVM” option "
                      "when partitioning the disk. Adding it later is hard. If you forget the password, your data "
                      "cannot be recovered.")),
        ]),
        (T("Swap", "Swap"), [
            ("p", T("Swap, bellek dolunca belleğin diske taşındığı alandır. CarotOS varsayılan olarak zram "
                    "kullanır: sıkıştırılmış, yalnızca RAM'de duran bir swap.",
                    "Swap is the area where memory is moved to disk when it fills up. By default CarotOS uses "
                    "zram: a compressed swap that lives only in RAM.")),
            ("liste", [
                T("Sistem Sağlığı'ndaki “Swap şifreleme” denetimini çalıştır.",
                  "Run the “Swap encryption” check in System Health."),
                T("Diskte şifresiz swap görürsen “Disk swap'ını kapat”a bas ve onayla.",
                  "If you see unencrypted swap on disk, press “Disable disk swap” and confirm."),
            ]),
        ]),
        (T("Sınır", "The limit"), [
            ("uyari", T("Disk şifreleme bilgisayar kapalıyken korur; açıkken ve oturum açıkken değil. "
                        "Uzaklaşırken ekranı kilitle.",
                        "Disk encryption protects while the computer is off, not while it is on and you are "
                        "logged in. Lock the screen when you walk away.")),
        ]),
    ]
    return {
        "id": "disk", "grup": "uygulamalar", "ikon": "kilit", "ad": T("Disk şifreleme ve swap", "Disk encryption and swap"),
        "alt": T("Verilerin diskte güvende", "Your data safe on the disk"),
        "ozet": T("Disk şifreleme, zram ve Sistem Sağlığı'ndaki swap denetimi.",
                  "Disk encryption, zram and the swap check in System Health."),
        "vurgu": "guvenlik", "sahne": _sahne(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": {"ad": T("Sistem Sağlığı", "System Health"), "komut": KOMUT}, "root": False,
    }
