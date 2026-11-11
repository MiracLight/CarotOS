# -*- coding: utf-8 -*-
"""Indirdigini dogrula: ISO'nun imzasini (gpgv) ve ozetini (sha256sum) terminalde denetlemek."""
from former_sahneler import dogrula_sahnesi
from former_zaman import T, ayarla, balon, bekle, cikti, tikla, yaz

ANAHTAR = "/usr/share/keyrings/carotos-archive-keyring.gpg"
KOMUT_1 = "gpgv --keyring " + ANAHTAR + " SHA256SUMS.sign SHA256SUMS"
KOMUT_2 = "sha256sum -c SHA256SUMS --ignore-missing"
PARMAK_IZI = "30E6 D4B0 C05E F002 1309 A1A0 9F93 5CD4 D5D0 A1F5"

# gpgv ve sha256sum'un gercek ciktisi (Turkce metinler sistemin kendi cevirileri: gnupg2 / coreutils)
CIKTI_1 = [
    "carot@carotos:~/İndirilenler$ " + KOMUT_1,
    T("gpgv: İmza EDDSA kullanılarak 05F7D6A57B27FF88339EC9DCD71E9B987D57C088 anahtarı ile yapılmış",
      "gpgv:                using EDDSA key 05F7D6A57B27FF88339EC9DCD71E9B987D57C088"),
    T('gpgv: "CarotOS Archive <archive@carotos.org>" konumundaki imza iyi',
      'gpgv: Good signature from "CarotOS Archive <archive@carotos.org>"'),
]
CIKTI_2 = [
    "carot@carotos:~/İndirilenler$ " + KOMUT_2,
    T("carotos-1.4-amd64.iso: Tamam", "carotos-1.4-amd64.iso: OK"),
]


def konu():
    adimlar = [
        balon("d1_pencere", T("Üç dosya, bir klasör", "Three files, one folder"),
              T("ISO'nun yanına aynı yerden iki küçük dosya indir: SHA256SUMS (özetler) ve SHA256SUMS.sign (imza). "
                "Üçü aynı klasörde olsun, terminali o klasörde aç.",
                "Next to the ISO, download two small files from the same place: SHA256SUMS (the checksums) and "
                "SHA256SUMS.sign (the signature). Keep all three in the same folder and open the terminal there."),
              "alt"),
        yaz("d1_komut", KOMUT_1),
        balon("d1_komut", T("Önce imza", "Signature first"),
              T("gpgv, SHA256SUMS dosyasını gerçekten CarotOS'un imzaladığını denetler. Anahtar CarotOS'ta zaten "
                "kurulu; başka bir sistemde önce anahtarı carotos.org'dan alırsın.",
                "gpgv checks that CarotOS really signed the SHA256SUMS file. The key is already installed on "
                "CarotOS; on another system you first get the key from carotos.org."), "ust"),
        tikla("d1_tus", ayarla={"d1_tus": {"renk": "yesil"}}),
        cikti("d1_pencere", CIKTI_1),
        balon("d1_pencere", T("İmza iyi", "Good signature"),
              T("\"CarotOS Archive\" ve \"imza iyi\" (Good signature) görmelisin. \"imza KÖTÜ\" (BAD signature) "
                "çıkarsa dosyalar değiştirilmiş demektir: kullanma.",
                "You should see \"CarotOS Archive\" and \"Good signature\". If it says \"BAD signature\", the files "
                "have been tampered with: do not use them."), "alt"),
        bekle(400),
        ayarla(_sayfa="iki"),
        yaz("d2_komut", KOMUT_2),
        balon("d2_komut", T("Sonra özet", "Then the checksum"),
              T("İmza, özet listesinin doğru olduğunu gösterdi. Şimdi ISO'nun özetini bu listeyle karşılaştır.",
                "The signature showed that the checksum list is genuine. Now compare the ISO's checksum with it."),
              "ust"),
        tikla("d2_tus", ayarla={"d2_tus": {"renk": "yesil"}}),
        cikti("d2_pencere", CIKTI_2),
        balon("d2_pencere", T("Tamam", "OK"),
              T("ISO'nun satırında \"Tamam\" (İngilizce sistemde \"OK\") yazıyorsa dosya bozulmamış ve CarotOS'un "
                "imzaladığı dosyanın aynısı. \"BAŞARISIZ\" (FAILED) görürsen yeniden indir.",
                "If the ISO's line says \"OK\" (\"Tamam\" on a Turkish system), the file is intact and identical to "
                "the one CarotOS signed. If you see \"FAILED\", download it again."), "alt"),
    ]
    bolumler = [
        (T("Neden doğrulamalı", "Why verify"), [
            ("p", T("Değiştirilmiş bir ISO, kurduğun anda bilgisayarına zararlı yazılım sokabilir. Özet, dosyanın "
                    "bozulmadığını; imza, dosyayı gerçekten CarotOS'un hazırladığını gösterir. İkisi birlikte "
                    "güven verir.",
                    "A tampered ISO can put malware on your computer the moment you install it. The checksum shows "
                    "the file is not damaged; the signature shows that CarotOS really made it. Together they give "
                    "you confidence.")),
        ]),
        (T("Adımlar", "Steps"), [
            ("liste", [
                T("ISO, SHA256SUMS ve SHA256SUMS.sign dosyalarını aynı klasöre indir.",
                  "Download the ISO, SHA256SUMS and SHA256SUMS.sign into the same folder."),
                T("İmzayı doğrula:", "Verify the signature:"),
            ]),
            ("kod", KOMUT_1),
            ("liste", [T("Özeti denetle:", "Check the checksum:")]),
            ("kod", KOMUT_2),
        ]),
        (T("Anahtar", "The key"), [
            ("tablo", [
                (T("Ad", "Name"), T("CarotOS Archive <archive@carotos.org>", "CarotOS Archive <archive@carotos.org>")),
                (T("Parmak izi", "Fingerprint"), T(PARMAK_IZI, PARMAK_IZI)),
            ]),
            ("p", T("Başka bir sistemde anahtarı carotos.org'dan indirdikten sonra parmak izini bu satırla "
                    "karşılaştır. Windows'ta Gpg4win (Kleopatra) aynı işi yapar.",
                    "On another system, after downloading the key from carotos.org, compare its fingerprint with "
                    "this line. On Windows, Gpg4win (Kleopatra) does the same job.")),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Özeti ve imzayı ISO'yu indirdiğin sayfadan değil, ayrı ve güvendiğin bir kaynaktan "
                        "aldığın anahtarla doğrula. Aynı sitedeki bir saldırgan hem ISO'yu hem özeti değiştirebilir; "
                        "imza bunu yakalar.",
                        "Verify with a key you got from a separate source you trust, not just the page you "
                        "downloaded the ISO from. An attacker on the same site could change both the ISO and the "
                        "checksum; the signature catches that.")),
        ]),
    ]
    return {
        "id": "dogrula", "grup": "uygulamalar", "ikon": "kalkan", "ad": T("İndirdiğini doğrula", "Verify downloads"),
        "alt": T("ISO'nun imzası ve özeti", "The ISO's signature and checksum"),
        "ozet": T("İndirdiğin ISO'nun bozulmadığını ve gerçekten CarotOS'tan geldiğini kontrol et.",
                  "Check that the ISO you downloaded is intact and really comes from CarotOS."),
        "vurgu": "guvenlik", "sahne": dogrula_sahnesi(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": None, "root": False,
    }
