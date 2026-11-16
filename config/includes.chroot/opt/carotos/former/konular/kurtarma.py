# -*- coding: utf-8 -*-
"""Kurtarma genel tanitimi: sistemi son kararli noktaya dondurme araci."""
from former_sahneler import PH, PW, UST, _yan
from former_zaman import T, balon, git, tikla

KOMUT = ["python3", "/opt/carotos/kurtarma/carotos-kurtarma.py"]


def _sahne():
    menu = [("k:noktalar", T("Kurtarma noktaları", "Recovery points"), "kalkan"),
            ("k:ayarlar", T("Ayarlar", "Settings"), "ayar")]
    o = _yan(T("CarotOS", "CarotOS"), T("Kurtarma", "Recovery"), menu, adim=25, y0=64,
             baslangic_aktif="k:noktalar")
    o += [
        # --- noktalar sayfasi
        {"id": "k_baslik", "tur": "metin", "x": 172, "y": 34, "w": 300, "h": 20, "sayfa": "noktalar",
         "metin": T("Kurtarma noktaları", "Recovery points"), "boyut": 14, "kalin": True},
        {"id": "k_alt", "tur": "metin", "x": 172, "y": 58, "w": 400, "h": 14, "sayfa": "noktalar",
         "boyut": 8.4, "renk": "soluk", "metin": T("Sistemi bu noktaya alabilirsin", "You can bring the system back to one of these")},
        {"id": "k_olustur", "tur": "dugme", "x": 604, "y": 30, "w": 148, "h": 28, "sayfa": "noktalar",
         "birincil": True, "metin": T("Şimdi nokta oluştur", "Create a point now")},
        {"id": "k_bilgi", "tur": "metin", "x": 172, "y": 82, "w": 566, "h": 28, "sayfa": "noktalar", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("/etc, /root ve kurulu paket listesinin yedeği. Kişisel dosyalarına (Belgeler, "
                    "Masaüstü, tarayıcı…) dokunulmaz.",
                    "A copy of /etc, /root and the installed package list. Your personal files "
                    "(Documents, Desktop, browser…) are left untouched.")},
        {"id": "k_bos", "tur": "metin", "x": 172, "y": 150, "w": 566, "h": 40, "sayfa": "noktalar",
         "bayrak": "!nokta_var", "sar": True, "hiza": "orta", "boyut": 10, "renk": "silik",
         "metin": T("Henüz kurtarma noktası yok", "No recovery points yet")},
        {"id": "k_ozet", "tur": "metin", "x": 172, "y": 124, "w": 400, "h": 14, "sayfa": "noktalar",
         "bayrak": "nokta_var", "boyut": 8.4, "renk": "soluk",
         "metin": T("1 nokta · toplam 8 MB", "1 point · 8 MB total")},
        {"id": "k_kart", "tur": "kart", "x": 170, "y": 142, "w": 580, "h": 68, "sayfa": "noktalar",
         "bayrak": "nokta_var"},
        {"id": "k_tarih", "tur": "metin", "x": 182, "y": 152, "w": 300, "h": 16, "sayfa": "noktalar",
         "bayrak": "nokta_var", "boyut": 9.6, "kalin": True, "metin": "15.11.2026 21:03"},
        {"id": "k_detay", "tur": "metin", "x": 182, "y": 172, "w": 340, "h": 14, "sayfa": "noktalar",
         "bayrak": "nokta_var", "boyut": 8.2, "renk": "soluk",
         "metin": T("güncelleme öncesi  ·  8 MB", "before an update  ·  8 MB")},
        {"id": "k_geri", "tur": "dugme", "x": 548, "y": 150, "w": 94, "h": 26, "sayfa": "noktalar",
         "bayrak": "nokta_var", "metin": T("Geri yükle", "Restore")},
        {"id": "k_sil", "tur": "dugme", "x": 648, "y": 150, "w": 64, "h": 26, "sayfa": "noktalar",
         "bayrak": "nokta_var", "metin": T("Sil", "Delete")},
        {"id": "k_not", "tur": "metin", "x": 172, "y": 340, "w": 566, "h": 30, "sayfa": "noktalar", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("apt ile paket kurup güncellerken, değişiklikten hemen önce kendiliğinden bir "
                    "kurtarma noktası açılır.",
                    "When you install or update packages with apt, a recovery point is opened "
                    "automatically right before the change.")},
        # --- ayarlar sayfasi
        {"id": "a_baslik", "tur": "metin", "x": 172, "y": 34, "w": 300, "h": 20, "sayfa": "ayarlar",
         "metin": T("Ayarlar", "Settings"), "boyut": 14, "kalin": True},
        {"id": "a_oto_et", "tur": "metin", "x": 174, "y": 76, "w": 430, "h": 14, "sayfa": "ayarlar",
         "boyut": 9, "kalin": True, "metin": T("Güncellemeden önce otomatik nokta", "Automatic point before an update")},
        {"id": "a_oto_alt", "tur": "metin", "x": 174, "y": 94, "w": 500, "h": 28, "sayfa": "ayarlar", "sar": True,
         "boyut": 8.2, "renk": "soluk",
         "metin": T("apt ile paket kurup güncellerken, değişiklikten hemen önce kendiliğinden bir "
                    "kurtarma noktası açılır.",
                    "When you install or update packages with apt, a recovery point is opened "
                    "automatically right before the change.")},
        {"id": "a_oto_ani", "tur": "anahtar", "x": 700, "y": 80, "w": 40, "h": 22, "sayfa": "ayarlar", "aktif": True},
        {"id": "a_cizgi", "tur": "cizgi", "x": 172, "y": 142, "w": 576, "h": 1, "sayfa": "ayarlar"},
        {"id": "a_sakla_et", "tur": "metin", "x": 174, "y": 156, "w": 400, "h": 14, "sayfa": "ayarlar",
         "boyut": 8.6, "renk": "soluk", "metin": T("Kaç nokta saklansın", "How many points to keep")},
        {"id": "a_sakla_deger", "tur": "metin", "x": 700, "y": 152, "w": 40, "h": 20, "sayfa": "ayarlar",
         "boyut": 10, "kalin": True, "metin": "5"},
        {"id": "a_aralik_et", "tur": "metin", "x": 174, "y": 188, "w": 420, "h": 14, "sayfa": "ayarlar",
         "boyut": 8.6, "renk": "soluk",
         "metin": T("Otomatik noktalar arası en az süre", "Minimum time between automatic points")},
        {"id": "a_aralik_deger", "tur": "metin", "x": 684, "y": 184, "w": 56, "h": 20, "sayfa": "ayarlar",
         "boyut": 10, "kalin": True, "metin": T("10 dk", "10 min")},
        {"id": "a_disk_et", "tur": "metin", "x": 174, "y": 220, "w": 420, "h": 14, "sayfa": "ayarlar",
         "boyut": 8.6, "renk": "soluk",
         "metin": T("Nokta için gereken en az boş alan", "Minimum free space required for a point")},
        {"id": "a_disk_deger", "tur": "metin", "x": 684, "y": 216, "w": 56, "h": 20, "sayfa": "ayarlar",
         "boyut": 10, "kalin": True, "metin": "512 MB"},
        {"id": "a_kaydet", "tur": "dugme", "x": 172, "y": 260, "w": 100, "h": 26, "sayfa": "ayarlar",
         "birincil": True, "metin": T("Kaydet", "Save")},
    ]
    return {"genislik": PW, "yukseklik": PH, "vurgu": "kurtarma", "sayfa": "noktalar",
            "baslik": T("CarotOS Kurtarma", "CarotOS Recovery"), "ogeler": o}


def konu():
    adimlar = [
        balon("k_baslik", T("Kurtarma ne işe yarar", "What Recovery does"),
              T("Bir güncelleme ya da yanlış bir ayar sistemi bozduğunda, Kurtarma seni /etc, /root ve "
                "kurulu paket listesinin önceki bir kopyasına geri götürür. Windows'un Sistem Geri "
                "Yükleme'siyle aynı fikir: kişisel dosyalarına (Belgeler, Masaüstü, tarayıcı…) dokunulmaz.",
                "When an update or a wrong setting breaks the system, Recovery takes you back to an "
                "earlier copy of /etc, /root and the installed package list. Same idea as Windows's "
                "System Restore: your personal files (Documents, Desktop, browser…) are left "
                "untouched."), "alt"),
        git("k_olustur"),
        balon("k_olustur", T("Elle bir nokta aç", "Open a point by hand"),
              T("Büyük bir değişiklikten (güncelleme, ayar değişikliği) önce buna basıp elle bir nokta "
                "alabilirsin. Otomatik olanlar zaten apt her paket kurup güncellediğinde kendiliğinden "
                "açılır.",
                "Press this before a big change (an update, a config change) to take a point by hand. "
                "Automatic ones already open by themselves whenever apt installs or updates a "
                "package."), "ust"),
        tikla("k_olustur", bayrak={"nokta_var": True}),
        git("k_kart"),
        balon("k_detay", T("Nokta ne içerir", "What a point holds"),
              T("Her nokta /etc, /root ve o anki paket listesinin bir kopyasıdır; sabit bağ (hard link) "
                "sayesinde yalnızca değişen dosyalar yer kaplar, bu yüzden ilk nokta hariç genelde "
                "küçüktür.",
                "Each point is a copy of /etc, /root and the package list at that moment; thanks to "
                "hard links, only changed files take up space, so apart from the first point they are "
                "usually small."), "alt"),
        git("k_geri"),
        balon("k_geri", T("Geri yükle", "Restore"),
              T("Bu, /etc ve /root içeriğini o noktadaki haline döndürür; bu noktadan sonra yaptığın "
                "sistem ayarı değişiklikleri kaybolur. O zaman kurulu olup şimdi eksik olan paketleri "
                "de kurmasını isteyebilirsin.",
                "This returns /etc and /root to their state at that point; any system setting changes "
                "made since then are lost. You can also ask it to install packages that were present "
                "then but are missing now."), "ust"),
        tikla("k:ayarlar", sayfa="ayarlar"),
        git("a_oto_ani"),
        balon("a_oto_ani", T("Otomatik nokta", "Automatic point"),
              T("Açıkken, apt ile paket kurup güncellerken değişiklikten hemen önce kendiliğinden bir "
                "nokta açılır; apt işlemini hiçbir zaman durdurmaz (disk doluysa ya da bir hata olursa "
                "sessizce atlar).",
                "When on, installing or updating a package with apt opens a point by itself right "
                "before the change; it never stops the apt operation (it silently skips if the disk "
                "is full or something goes wrong)."), "alt"),
        git("a_sakla_et"),
        balon("a_sakla_et", T("Saklama sınırı", "The keep limit"),
              T("Bu sayıyı aşan en eski noktalar otomatik silinir, böylece disk dolup taşmaz.",
                "The oldest points beyond this number are deleted automatically, so the disk doesn't "
                "fill up."), "sag"),
    ]
    bolumler = [
        (T("Kurtarma nedir", "What Recovery is"), [
            ("p", T("Kurtarma, sistemi son bilinen iyi durumuna döndüren bir araçtır — bir yedekleme "
                    "aracı değildir. Kapsamı bilerek dar tutulur: yalnızca /etc, /root ve kurulu paket "
                    "listesi. Bunlar “sistem neden bozuldu” sorularının çoğunu (kötü bir güncelleme, "
                    "yanlış bir ayar dosyası) kapsar; kişisel dosyalarına (Belgeler, Masaüstü, "
                    "tarayıcı ayarları) hiç dokunulmaz.",
                    "Recovery is a tool that returns the system to its last known-good state — it is "
                    "not a backup tool. Its scope is deliberately narrow: only /etc, /root and the "
                    "installed package list. These cover most “why did the system break” questions "
                    "(a bad update, a wrong config file); your personal files (Documents, Desktop, "
                    "browser settings) are never touched.")),
            ("p", T("Noktalar rsync ve sabit bağ (hard link) ile artımlı tutulur, aynı CarotOS'un dosya "
                    "sistemini sabitlemediği için (çoğu kurulum ext4) Btrfs/LVM anlık görüntüsü yerine "
                    "bu yöntem seçildi. Noktalar aynı diskte saklanır; harici bir diske taşımak sana "
                    "kalmıştır.",
                    "Points are kept incrementally with rsync and hard links; since CarotOS does not "
                    "lock in a filesystem (most installs use ext4), this method was chosen instead of "
                    "a Btrfs/LVM snapshot. Points are stored on the same disk; moving them to an "
                    "external disk is up to you.")),
        ]),
        (T("Nasıl kullanılır", "How to use it"), [
            ("liste", [
                T("Büyük bir değişiklikten (güncelleme, ayar değişikliği) önce “Şimdi nokta oluştur”a "
                  "bas.", "Before a big change (an update, a config change), press “Create a point "
                  "now”."),
                T("apt ile paket kurup güncellerken bir nokta zaten kendiliğinden açılır (ayardan "
                  "kapatılabilir).", "A point already opens by itself when you install or update "
                  "packages with apt (you can turn this off in settings)."),
                T("Sistem bozulursa, ilgili noktada “Geri yükle”ye bas; istersen o zaman kurulu "
                  "paketleri de geri kurdur.", "If the system breaks, press “Restore” on the right "
                  "point; you can also have it reinstall the packages that were there then."),
                T("Ayarlardaki sayıyı aşan en eski noktalar otomatik silinir.", "The oldest points "
                  "beyond the number in settings are deleted automatically."),
            ]),
        ]),
        (T("Ne zaman işe yaramaz", "When it won't help"), [
            ("uyari", T("Bu bir yedekleme aracı değildir: kişisel dosyalarını (Belgeler, Masaüstü, "
                        "fotoğraflar) korumaz. Disk tamamen bozulursa ya da değişirse noktalar da "
                        "onunla gider, çünkü aynı diskte dururlar. Canlı (USB) oturumunda alınan bir "
                        "nokta yalnızca o oturum kapanana kadar kalıcıdır.",
                        "This is not a backup tool: it does not protect your personal files "
                        "(Documents, Desktop, photos). If the disk itself fails or is replaced, the "
                        "points go with it, since they live on the same disk. A point taken in a "
                        "live (USB) session only lasts until that session ends.")),
        ]),
        (T("Ayarlar", "Settings"), [
            ("p", T("Dört ayar vardır: güncelleme öncesi otomatik nokta açık/kapalı, kaç nokta "
                    "saklanacağı, otomatik noktalar arası en az süre (aynı anda art arda güncelleme "
                    "yapınca gereksiz nokta birikmesin diye) ve bir nokta için gereken en az boş disk "
                    "alanı.",
                    "There are four settings: automatic point before an update on/off, how many "
                    "points to keep, the minimum time between automatic points (so installing several "
                    "updates in a row doesn't pile up needless points), and the minimum free disk "
                    "space required for a point.")),
        ]),
    ]
    return {
        "id": "kurtarma", "grup": "uygulamalar", "ikon": "yenile", "ad": T("Kurtarma", "Recovery"),
        "alt": T("Son kararlı duruma dön", "Back to the last stable state"),
        "ozet": T("Sistemi son kararlı duruma geri döndürür.", "Returns the system to its last stable state."),
        "vurgu": "kurtarma", "sahne": _sahne(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": {"ad": T("Kurtarma", "Recovery"), "komut": KOMUT}, "root": False,
    }
