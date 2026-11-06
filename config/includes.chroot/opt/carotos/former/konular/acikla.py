# -*- coding: utf-8 -*-
"""Komut Aciklayici: terminalde bir komutu yazip Alt+E ile ne yaptigini ogrenmek. Komut calistirilmaz."""
from former_sahneler import acikla_sahnesi
from former_zaman import T, ayarla, balon, bekle, cikti, git, tikla, yaz

KOMUT_1 = "tar xzf arsiv.tar.gz"
KOMUT_2 = "curl https://ornek.org/kur.sh | sh"

# Gercek carotos-acikla ciktisinin ekrana sigacak sekilde bolunmus hali
CIKTI_1 = [
    T("Komut açıklaması (komut ÇALIŞTIRILMADI)", "Command explanation (the command was NOT run)"),
    "",
    KOMUT_1,
    T("  Dosyaları tek bir arşivde toplar ya da arşivden açar.",
      "  Bundles files into one archive or extracts an archive."),
    T("  Bayraklar:", "  Flags:"),
    T("    -x  —  Arşivden dosyaları çıkarır.", "    -x  —  Extracts files from the archive."),
    T("    -z  —  gzip ile sıkıştırır/açar (.tar.gz).", "    -z  —  Compresses/decompresses with gzip (.tar.gz)."),
    T("    -f arsiv.tar.gz  —  Arşiv dosyasının adını verir.", "    -f arsiv.tar.gz  —  Gives the archive file's name."),
    T("  Gürültü: düşük", "  Noise: low"),
    T("  Yetki: normal kullanıcı yeterli", "  Privileges: a normal user is enough"),
    T("  Uyarı: Kaynağı güvenilmeyen arşivi açmadan önce -t ile içine bak.",
      "  Warning: Before extracting an untrusted archive, look inside with -t."),
]

CIKTI_2 = [
    T("Komut açıklaması (komut ÇALIŞTIRILMADI)", "Command explanation (the command was NOT run)"),
    "",
    T("[Parça 1] curl https://ornek.org/kur.sh", "[Part 1] curl https://ornek.org/kur.sh"),
    T("  Bir adrese istek gönderip yanıtı alır (HTTP, HTTPS, FTP…).",
      "  Sends a request to an address and fetches the reply (HTTP, HTTPS, FTP…)."),
    T("  ↳ çıktısı bir sonraki komuta aktarılır (|)", "  ↳ its output is piped into the next command (|)"),
    T("[Parça 2] sh", "[Part 2] sh"),
    T("  Komut yorumlayıcı (kabuk): verilen komutu ya da betiği çalıştırır.",
      "  Command interpreter (shell): runs the given command or script."),
    "",
    T("⚠ Tehlikeli kalıp (yüksek): İnternetten indirilen içerik, ne olduğuna bakılmadan",
      "⚠ Dangerous pattern (high): Content downloaded from the internet is run directly"),
    T("  doğrudan çalıştırılıyor (curl | sh). Önce indirip oku, sonra çalıştır.",
      "  without looking at it (curl | sh). Download it, read it, then run it."),
]


def konu():
    adimlar = [
        balon("a1_pencere", T("Terminalde açıklayıcı", "The explainer in the terminal"),
              T("Komut Açıklayıcı, terminale yazdığın bir komutun ne yaptığını sen çalıştırmadan anlatır. "
                "Tanımadığın bir komutu internetten kopyaladığında, önce ne yapacağını öğrenmenin güvenli yoludur.",
                "The Command Explainer tells you what a command you typed in the terminal does, before you run "
                "it. When you copy a command you do not know from the internet, it is the safe way to find out "
                "what it will do first."), "alt"),
        yaz("a1_komut", KOMUT_1),
        balon("a1_komut", T("Yaz ama Enter'a basma", "Type it but do not press Enter"),
              T("Komutu terminale her zamanki gibi yaz. Enter'a basma: basarsan komut çalışır. Satır yazılı "
                "kalsın.",
                "Type the command in the terminal as usual. Do not press Enter: if you do, the command runs. "
                "Leave the line typed."), "ust"),
        git("a1_tus"),
        balon("a1_tus", T("Alt+E'ye bas", "Press Alt+E"),
              T("Alt ve E tuşlarına birlikte bas. Yazdığın satır aynen yerinde kalır, altında açıklama çıkar.",
                "Press Alt and E together. The line you typed stays exactly where it is, and the explanation "
                "appears below it."), "ust"),
        tikla("a1_tus", ayarla={"a1_tus": {"renk": "yesil"}}),
        cikti("a1_pencere", CIKTI_1),
        balon("a1_pencere", T("Açıklamayı oku", "Read the explanation"),
              T("Önce komutun ne işe yaradığı yazar, sonra her bayrağın tek tek anlamı. Gürültü, ağda ne kadar "
                "iz bıraktığını; Yetki, root gerekip gerekmediğini söyler. Uyarı satırı dikkat edilecek yeri "
                "gösterir.",
                "First it says what the command is for, then what each flag means. Noise says how much trace it "
                "leaves on the network; Privileges says whether root is needed. The Warning line points out "
                "what to watch for."), "alt"),
        balon("a1_komut", T("Komut çalışmadı", "The command did not run"),
              T("Satır hâlâ yazılı. Açıklama bittikten sonra çalıştırmak istersen Enter'a basarsın; "
                "istemiyorsan satırı silersin. Karar senin.",
                "The line is still typed. After the explanation, press Enter if you want to run it, or delete "
                "the line if you do not. The decision is yours."), "ust"),
        bekle(400),
        ayarla(_sayfa="iki"),
        yaz("a2_komut", KOMUT_2),
        balon("a2_komut", T("Tehlikeli bir örnek", "A dangerous example"),
              T("Bu satır internetten bir betik indirir ve doğrudan çalıştırır. Yeni başlayanlara sık gösterilen, "
                "ama riskli bir kalıptır.",
                "This line downloads a script from the internet and runs it straight away. It is a pattern often "
                "shown to beginners, but a risky one."), "ust"),
        tikla("a2_tus", ayarla={"a2_tus": {"renk": "yesil"}}),
        cikti("a2_pencere", CIKTI_2),
        balon("a2_pencere", T("Tehlike uyarısı", "Danger warning"),
              T("Komut iki parçaya bölünür ve ⚠ ile başlayan satır riski adıyla söyler: betik sen okumadan "
                "çalışır, değişmiş olabilir. Önce indirip oku, sonra çalıştır.",
                "The command is split into two parts and the line starting with ⚠ names the risk: the script "
                "runs before you have read it, and it may have been tampered with. Download it, read it, then "
                "run it."), "alt"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("Komut Açıklayıcı, terminaldeki bir komutu parçalara ayırıp her parçanın ne yaptığını "
                    "sade bir dille anlatır. Bayrakları tek tek açıklar, gerekiyorsa uyarır.",
                    "The Command Explainer breaks a terminal command into parts and says in plain words what "
                    "each part does. It explains the flags one by one and warns you when needed.")),
            ("p", T("Önemli: komutu hiçbir zaman çalıştırmaz. Yalnızca yazdığın metni okur.",
                    "Important: it never runs the command. It only reads the text you typed.")),
        ]),
        (T("Nasıl kullanılır", "How to use it"), [
            ("liste", [
                T("Terminali aç ve komutu yaz, ama Enter'a basma.",
                  "Open the terminal and type the command, but do not press Enter."),
                T("Alt+E'ye bas; açıklama komutun altında çıkar.",
                  "Press Alt+E; the explanation appears below the command."),
                T("Açıklamayı oku. Çalıştırmak istiyorsan Enter'a bas, istemiyorsan satırı sil.",
                  "Read the explanation. Press Enter to run it, or delete the line if you do not want to."),
            ]),
        ]),
        (T("Açıklamada neler var", "What is in the explanation"), [
            ("tablo", [
                (T("Bayraklar", "Flags"), T("Her seçeneğin tek tek anlamı.", "What each option means.")),
                (T("Gürültü", "Noise"), T("Komutun ağda ne kadar iz bıraktığı.",
                                          "How much trace the command leaves on the network.")),
                (T("Yetki", "Privileges"), T("Normal kullanıcı yeter mi, root gerekir mi.",
                                              "Whether a normal user is enough or root is needed.")),
                (T("Uyarı", "Warning"), T("Dikkat edilecek nokta ya da riskli kalıp.",
                                          "Something to watch for, or a risky pattern.")),
            ]),
            ("kod", "carotos-acikla tar xzf arsiv.tar.gz"),
            ("p", T("Aynı açıklamayı terminalde Alt+E olmadan da alabilirsin: yukarıdaki komut, açıklamasını "
                    "istediğin komutun önüne yazarsın.",
                    "You can also get the same explanation without Alt+E: the command above takes the command "
                    "you want explained after it.")),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Açıklama bir yol göstericidir, güvenlik kontrolü değildir. Bilmediğin bir komutun "
                        "açıklaması rahatlatıcı görünse bile, kaynağına güvenmiyorsan çalıştırma. "
                        "Saldırı araçlarının bayrakları şimdilik kapsam dışındadır.",
                        "The explanation is a guide, not a security check. Even if the explanation of an "
                        "unfamiliar command looks reassuring, do not run it if you do not trust where it came "
                        "from. The flags of attack tools are out of scope for now.")),
        ]),
    ]
    return {
        "id": "acikla", "grup": "uygulamalar", "ikon": "arama", "ad": T("Komut Açıklayıcı", "Command Explainer"),
        "alt": T("Alt+E ile komutu anla", "Understand a command with Alt+E"),
        "ozet": T("Terminaldeki bir komutun ne yaptığını, sen çalıştırmadan anlatır.",
                  "Tells you what a terminal command does, before you run it."),
        "vurgu": "guvenlik", "sahne": acikla_sahnesi(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": None, "root": False,
    }
