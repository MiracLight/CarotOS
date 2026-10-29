# -*- coding: utf-8 -*-
from former_zaman import T, balon, git, yaz
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "john",
    "tagline": T("Parola kırma (John the Ripper)", "Password cracking (John the Ripper)"),
    "ne": T("Parola özet (hash) dosyalarını sözlük ve kaba kuvvetle çözmeye çalışır.",
            "Attempts to crack password hash files with dictionaries and brute force."),
    "ne_zaman": T("Bir sistemden alınmış parola özetlerinin ne kadar zayıf olduğunu ölçerken.",
                  "When measuring how weak password hashes taken from a system are."),
    "ornek": T("Hash dosyası seç, istersen kelime listesi ekle",
               "Pick a hash file, optionally add a wordlist"),
    "root": False,
    "alanlar": [
        {"id": "hashfile", "ad": T("Hash dosyası", "Hash file"), "tur": "dosya"},
        {"id": "wordlist", "ad": T("Kelime listesi (opsiyonel)", "Wordlist (optional)"), "tur": "dosya"},
    ],
}

CIKTI = [
    "Using default input encoding: UTF-8",
    "Loaded 3 password hashes with 3 different salts (sha512crypt, crypt(3) $6$ [SHA512 128/128])",
    "Press 'q' or Ctrl-C to abort, almost any other key for status",
    "123456           (ogrenci3)",
    "parola1          (ogrenci7)",
    "2g 0:00:00:04 DONE (2026-10-28 14:30) 0.4651g/s 11200p/s 11200c/s 11200C/s",
    "Use the \"--show\" option to display all of the cracked passwords reliably",
]


def konu():
    adimlar = arac_sec("john") + [
        git("alan:hashfile"),
        balon("alan:hashfile", T("Hash dosyası", "Hash file"),
              T("Parolaların kendisi değil, “özet”leri (hash) saklanır; bu, geri çevrilemeyen bir karışım "
                "gibidir. john bu dosyadaki özetleri dener, doğru parolayı bulursan özetin eşleştiğini "
                "görürsün.",
                "What is stored is not the passwords themselves but their “hashes”; this is like a mix that "
                "cannot be reversed. john tries values against the hashes in this file; if you find the "
                "right password, you see the hash match.")),
        yaz("alan:hashfile", "~/hashlar.txt"),
        git("alan:wordlist"),
        balon("alan:wordlist", T("Kelime listesi", "Wordlist"),
              T("Boş bırakırsan john kendi küçük yerleşik listesiyle dener. Bir dosya seçersen, o dosyadaki "
                "her kelimeyi sırayla parola olarak dener.",
                "Leave it empty and john tries with its own small built-in list. Pick a file and it tries "
                "every word in that file as a password, one by one.")),
    ] + calistir("john --wordlist=liste.txt hashlar.txt", CIKTI) + [
        balon("cikti", T("Sonucu oku", "Read the result"),
              T("Bulunan her parola bir satırda, karşısında hangi hesaba ait olduğu parantez içinde yazar. "
                "Son satır, güvenilir tam listeyi görmek için “--show” kullanmanı söylüyor.",
                "Each cracked password appears on a line, with the account it belongs to in parentheses. The "
                "last line says to use “--show” to see the full, reliable list."), "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("Bir sistemde parolalar asla açık metin olarak saklanmaz; bunun yerine bir “özet” "
                    "(hash) fonksiyonundan geçirilip öyle saklanır. john, elindeki bir sözlükteki her "
                    "kelimeyi aynı fonksiyondan geçirip sonucu dosyadaki özetlerle karşılaştırır; eşleşirse "
                    "parolayı bulmuş olur.",
                    "On a system, passwords are never stored as plain text; instead they are run through a "
                    "“hash” function and stored that way. john runs every word in a dictionary it has through "
                    "the same function and compares the result with the hashes in the file; a match means it "
                    "found the password.")),
            ("p", T("Bunu kendi sistemlerinde yapmak, kullanıcıların ne kadar zayıf parola seçtiğini ve bir "
                    "parola politikasına ihtiyaç olup olmadığını gösterir.",
                    "Doing this on your own systems shows how weak the passwords users pick are, and whether "
                    "you need a password policy.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan john'u seç.", "Pick john on the left."),
                T("Hash dosyasını seç (kendi test ortamından aldığın bir dosya).",
                  "Pick the hash file (one from your own test environment)."),
                T("İstersen bir kelime listesi dosyası ekle.", "Add a wordlist file if you like."),
                T("Çalıştır'a bas.", "Press Run."),
            ]),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[3:6])),
            ("p", T("“123456 (ogrenci3)” satırı, ogrenci3 hesabının parolasının 123456 olduğunu bulduğu "
                    "anlamına gelir — yani çok zayıf bir paroladır. Son satırdaki hız bilgisi (p/s, c/s), "
                    "aracın saniyede kaç deneme yaptığını gösterir.",
                    "The line “123456 (ogrenci3)” means it found that account ogrenci3's password is 123456 "
                    "— in other words, a very weak password. The speed figures on the last line (p/s, c/s) "
                    "show how many tries per second the tool makes.")),
            ("not", T_DENEME_UYARISI),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("Kendi test kullanıcınla “123456” gibi zayıf bir parola belirle, özetini al, john'un ne "
                  "kadar hızlı bulduğunu gör.",
                  "Set a weak password like “123456” for your own test user, take its hash, and see how fast "
                  "john finds it."),
                T("Aynı denemeyi uzun, rastgele bir parolayla yap; aradaki süre farkını karşılaştır.",
                  "Do the same test with a long, random password; compare the difference in time."),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Yalnızca kendi hesaplarından aldığın ya da size açıkça verilmiş hash dosyalarını "
                        "dene. Başkasına ait parola özetlerini izinsiz elde etmek ya da kırmaya çalışmak "
                        "suçtur.",
                        "Only test hash files from your own accounts or ones you were explicitly given. "
                        "Obtaining or trying to crack other people's password hashes without permission is a "
                        "crime.")),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "john --wordlist=liste.txt hashlar.txt"),
            ("p", T("Bulunan parolaları sonradan tekrar görmek için: john --show hashlar.txt",
                    "To see the cracked passwords again later: john --show hashlar.txt")),
        ]),
    ]
    return _konu("john", ARAC, adimlar, bolumler, ikon="anahtar")
