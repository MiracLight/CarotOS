# -*- coding: utf-8 -*-
from former_zaman import T, balon, git, yaz
from konular._panel import T_DENEME_UYARISI, arac_sec, calistir, konu as _konu

ARAC = {
    "ad": "sqlmap",
    "tagline": T("SQL injection testi", "SQL injection testing"),
    "ne": T("Web adreslerindeki parametreleri SQL injection açıkları için otomatik dener.",
            "Automatically probes parameters in web addresses for SQL injection flaws."),
    "ne_zaman": T("Kendi web uygulamanın veritabanı girdilerini yeterince koruyup korumadığını test ederken.",
                  "When testing whether your own web app protects its database inputs well enough."),
    "ornek": T("URL = http://localhost/sayfa?id=1", "URL = http://localhost/page?id=1"),
    "root": False,
    "alanlar": [
        {"id": "url", "ad": T("Hedef URL", "Target URL"), "tur": "alan",
         "yer": T("örn. http://host/p?id=1", "e.g. http://host/p?id=1")},
        {"id": "extra", "ad": T("Ek parametreler", "Extra parameters"), "tur": "alan", "varsayilan": "--batch"},
    ],
}

CIKTI = [
    "[14:20:11] [INFO] testing connection to the target URL",
    "[14:20:12] [INFO] testing if the target URL content is stable",
    "[14:20:13] [INFO] testing 'AND boolean-based blind - WHERE or HAVING clause'",
    "[14:20:15] [WARNING] parameter 'id' does not seem to be injectable",
    "[14:20:15] [INFO] testing 'MySQL >= 5.0 boolean-based blind'",
    "[14:20:21] all tested parameters do not appear to be injectable",
]


def konu():
    adimlar = arac_sec("sqlmap") + [
        git("alan:url"),
        balon("alan:url", T("Hedef URL", "Target URL"),
              T("sqlmap bir URL'deki parametreyi (?id=1 gibi) dener. URL'de bir soru işareti ve en az bir "
                "parametre olmalı; aksi hâlde denenecek bir şey yoktur.",
                "sqlmap probes a parameter in a URL (like ?id=1). The URL needs a question mark and at least "
                "one parameter; otherwise there is nothing to test.")),
        yaz("alan:url", "http://localhost/sayfa?id=1"),
        git("alan:extra"),
        balon("alan:extra", T("Ek parametreler", "Extra parameters"),
              T("--batch sqlmap'in her soruya kendi kendine “varsayılanı kullan” cevabını vermesini sağlar; "
                "böylece araç durmadan ilerler. Boş bırakırsan sorular sorulduğunda ilerlemez.",
                "--batch makes sqlmap answer every question with “use default” on its own, so the tool keeps "
                "going without stopping. Leaving it empty means it will not progress when it asks "
                "questions.")),
    ] + calistir("sqlmap -u http://localhost/sayfa?id=1 --batch", CIKTI) + [
        balon("cikti", T("Sonucu oku", "Read the result"),
              T("sqlmap önce bağlantıyı dener, sonra tek tek teknikleri sırayla test eder. “does not seem to "
                "be injectable” ya da “all tested parameters do not appear to be injectable” iyi haberdir: "
                "bulduğu bir açık yok demektir.",
                "sqlmap first tries the connection, then tests techniques one by one. “does not seem to be "
                "injectable” or “all tested parameters do not appear to be injectable” is good news: it "
                "means it found no flaw."), "ust"),
    ]
    bolumler = [
        (T("Ne işe yarar", "What it is for"), [
            ("p", T("Birçok web sayfası, adresteki bir değeri (?id=1 gibi) alıp arka planda veritabanına "
                    "sorar. Sayfa bu değeri yeterince kontrol etmezse, biri bu alana normal bir sayı yerine "
                    "özel bir metin yazarak veritabanını kandırabilir; buna SQL injection denir. sqlmap bu "
                    "zayıflığı otomatik olarak dener ve var mı yok mu söyler.",
                    "Many web pages take a value from the address (like ?id=1) and ask the database with it "
                    "behind the scenes. If the page does not check this value well enough, someone can write "
                    "special text instead of a plain number to trick the database; this is called SQL "
                    "injection. sqlmap automatically tests for this weakness and reports whether it exists.")),
            ("p", T("Kendi web uygulamanı yayına almadan önce bu kontrolü yapmak, kullanıcı verilerini "
                    "korumanın temel adımlarından biridir.",
                    "Running this check before you put your own web app live is one of the basic steps in "
                    "protecting user data.")),
        ]),
        (T("Panelde adım adım", "Step by step in the panel"), [
            ("liste", [
                T("Soldan sqlmap'i seç.", "Pick sqlmap on the left."),
                T("Hedef URL'ye, içinde bir parametre geçen bir adres yaz.",
                  "Type an address that contains a parameter in Target URL."),
                T("Ek parametreleri --batch olarak bırak.", "Leave the extra parameters as --batch."),
                T("Çalıştır'a bas; test birkaç dakika sürebilir.", "Press Run; the test can take a few minutes."),
            ]),
        ]),
        (T("Çıktıyı nasıl okurum", "How to read the output"), [
            ("kod", "\n".join(CIKTI[:4])),
            ("tablo", [
                (T("[INFO]", "[INFO]"), T("Bilgilendirme; araç şu an ne denediğini söylüyor.",
                                         "Information; the tool reports what it is trying now.")),
                (T("[WARNING]", "[WARNING]"), T("Bir teknik işe yaramadı, sıradaki deneniyor.",
                                                "One technique did not work, the next is being tried.")),
                (T("injectable", "injectable"), T("Bu kelime çıkarsa parametre savunmasız demektir; çıkmazsa "
                                                  "iyi bir işarettir.",
                                                  "If this word appears, the parameter is vulnerable; if not, "
                                                  "that is a good sign.")),
            ]),
            ("not", T_DENEME_UYARISI),
        ]),
        (T("Kendin dene", "Try it yourself"), [
            ("liste", [
                T("Basit bir sayfa kur (örn. bir eğitim projesi), kasıtlı olarak güvensiz bir sorgu yaz, "
                  "sqlmap ile bulduğunu gör.",
                  "Set up a simple page (e.g. a learning project), write a query that is deliberately "
                  "insecure on purpose, and see sqlmap find it."),
                T("Aynı sayfayı parametreli sorguyla (prepared statement) düzelt, taramayı tekrarla ve farkı "
                  "gör.",
                  "Fix the same page with a parameterised query, run the scan again, and see the difference."),
            ]),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Yalnızca kendi web uygulamalarını ya da test için açıkça izin aldığın uygulamaları "
                        "tara. Başka bir sitede izinsiz çalıştırmak, veritabanına izinsiz erişmeye teşebbüs "
                        "sayılır ve ciddi hukuki sonuçları olabilir.",
                        "Scan only your own web apps, or apps you have clear permission to test. Running it "
                        "against someone else's site without permission counts as attempting unauthorised "
                        "database access and can have serious legal consequences.")),
        ]),
        (T("Terminalde karşılığı", "The terminal equivalent"), [
            ("kod", "sqlmap -u \"http://localhost/sayfa?id=1\" --batch"),
            ("p", T("Veritabanı adlarını listelemek gibi daha ileri adımlar --dbs, --tables gibi ek "
                    "bayraklarla yapılır; bunlar yalnızca kendi test ortamında, bilerek kullanılmalıdır.",
                    "Further steps such as listing database names use extra flags like --dbs, --tables; use "
                    "these only in your own test environment, knowingly.")),
        ]),
    ]
    return _konu("sqlmap", ARAC, adimlar, bolumler, ikon="veritabani")
