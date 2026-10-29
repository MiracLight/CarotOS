# -*- coding: utf-8 -*-
"""Carotene genel tanitimi: virus taramasi."""
from former_zaman import T, ayarla, balon, bekle, git, ilerle, say, tikla
from former_sahneler import carotene_sahnesi

KOMUT = ["python3", "/opt/carotos/carotene/carotos-carotene.py"]


def konu():
    adimlar = [
        balon("t_giris", T("Carotene ne yapar", "What Carotene does"),
              T("Carotene, dosyalarını bilinen zararlı yazılım imzalarına karşı tarayan bir virüs "
                "tarayıcısıdır (ClamAV kullanır). Taramayı sen başlatmazsan hiçbir şey yapmaz; arka planda "
                "sürekli çalışan bir şey değildir.",
                "Carotene is a virus scanner that checks your files against known malware signatures (it "
                "uses ClamAV). It does nothing unless you start a scan; it is not something that keeps "
                "running in the background."), "sag"),
        git("k_hizli"),
        balon("k_hizli_ad", T("Üç tarama türü", "Three kinds of scan"),
              T("Hızlı tarama yalnızca İndirilenler, Masaüstü ve ana klasördeki dosyalara bakar — yeni "
                "indirdiğin bir şeyi kontrol etmek için idealdir. Ana klasörün tamamı her şeyi tarar ama "
                "uzun sürer. Özel tarama, seçtiğin tek bir klasör ya da dosyaya bakar.",
                "Quick scan looks only at Downloads, Desktop and the files in your home folder — ideal for "
                "checking something you just downloaded. Entire home folder scans everything but takes a "
                "long time. Custom scan looks at one folder or file you choose.")),
        tikla("k_hizli_tara", sayfa="calisiyor"),
        ilerle("r_ilerleme", 0.2, 900),
        say("r_sayac", 0, 310, 900, T("Taranan dosya: {n} · Bulgu: 0", "Files scanned: {n} · Findings: 0")),
        bekle(200),
        balon("r_ilerleme", T("Tarama sürerken", "While it scans"),
              T("İlerleme çubuğu ve taranan dosya sayısı canlı güncellenir. Büyük bir klasörü tararken "
                "bilgisayarın biraz yavaşlayabilir; istersen Durdur'a basıp sonra tekrar başlatabilirsin.",
                "The progress bar and the scanned-file count update live. Your computer may slow down a "
                "little while scanning a large folder; you can press Stop and start again later if you "
                "need to.")),
        ilerle("r_ilerleme", 1.0, 1000),
        say("r_sayac", 310, 1482, 1000, T("Taranan dosya: {n} · Bulgu: 1", "Files scanned: {n} · Findings: 1")),
        bekle(300),
        ayarla(_sayfa="sonuc"),
        git("s_baslik"),
        balon("s_baslik", T("Bir bulgu", "A finding"),
              T("Tarama bir eşleşme buldu: dosya yolu, hangi imzayla eşleştiği ve önerilen işlem. Burada "
                "görünen “eicar.com.txt”, gerçek bir virüs değil; tarayıcıları test etmek için kullanılan, "
                "zararsız standart bir test dosyasıdır.",
                "The scan found a match: the file path, which signature it matched, and the suggested "
                "action. The “eicar.com.txt” shown here is not a real virus; it is a harmless standard test "
                "file used to test scanners.")),
        git("s_ipucu"),
        balon("s_karantina", T("Karantina, Sil, Yok say", "Quarantine, Delete, Ignore"),
              T("Karantinaya al dosyayı çalıştırılamaz hâle getirir ama saklar — geri alman gerekirse "
                "oradan geri yüklersin. Sil geri dönüşü olmadan kaldırır. Yok say hiçbir şey yapmaz; "
                "dosyanın zararsız olduğundan eminsen kullanılır.",
                "Quarantine makes the file non-executable but keeps it — you can restore it later if you "
                "need to. Delete removes it with no way back. Ignore does nothing; use it only when you are "
                "sure the file is harmless.")),
        tikla("s_karantina", bayrak={"karantinada": True}),
        git("t_tanim"),
        balon("t_tanim", T("Tanımlar güncel mi", "Are the definitions up to date"),
              T("Sağ üstteki rozet, virüs tanımlarının ne zaman güncellendiğini gösterir. Eski tanımlarla "
                "yeni bir tehdit yakalanamaz; Ayarlar sayfasındaki “Tanımları güncelle”yi ara sıra "
                "kullanmak önemlidir.",
                "The badge top-right shows when the virus definitions were last updated. Old definitions "
                "cannot catch a new threat; using “Update definitions” on the Settings page now and then "
                "matters.")),
    ]
    bolumler = [
        (T("Carotene nedir", "What Carotene is"), [
            ("p", T("Carotene, dosyalarının içeriğini bilinen zararlı yazılım “imzalarıyla” karşılaştırır. "
                    "Bir imza, bir zararlı programın tanınmasını sağlayan küçük bir parçadır — parmak izi "
                    "gibi düşünebilirsin. Bu imzalar düzenli güncellenir çünkü her gün yeni zararlı "
                    "yazılımlar ortaya çıkar.",
                    "Carotene compares the contents of your files against known malware “signatures”. A "
                    "signature is a small piece that lets a piece of malware be recognised — think of it "
                    "like a fingerprint. These signatures are updated regularly because new malware appears "
                    "every day.")),
            ("p", T("Önemli bir sınırı var: imza tabanlı tarama yalnızca daha önce görülmüş ve "
                    "tanımlanmış tehditleri yakalar. Hiç görülmemiş, yepyeni bir zararlı yazılımı "
                    "yakalamayabilir. Bu yüzden “temiz” sonucu bir garanti değil, bir kontrol sonucudur.",
                    "It has an important limit: signature-based scanning only catches threats that have "
                    "already been seen and defined. It may miss a brand-new piece of malware nobody has "
                    "seen before. That is why a “clean” result is a check result, not a guarantee.")),
        ]),
        (T("Nasıl kullanılır", "How to use it"), [
            ("liste", [
                T("Yeni indirdiğin bir dosya için Hızlı tarama yeterlidir.",
                  "Quick scan is enough for something you just downloaded."),
                T("Şüphelendiğin tek bir dosya ya da klasör için Özel tarama kullan.",
                  "Use Custom scan for one file or folder you are suspicious of."),
                T("Ara sıra, mesela ayda bir, Ana klasörün tamamını tara.",
                  "Now and then, say once a month, scan the entire home folder."),
                T("Bir bulgu çıkarsa dosya yolunu oku, tanımıyorsan Karantinaya al'ı seç.",
                  "If there is a finding, read the file path; if you do not recognise it, choose "
                  "Quarantine."),
            ]),
        ]),
        (T("Bir bulgu çıkarsa", "If you get a finding"), [
            ("p", T("Panikleme. Dosya yolunu oku: tanıdığın, kendi indirdiğin bir dosyaysa ve imza adı "
                    "“Test” ya da “EICAR” gibi bir şey içeriyorsa, bu muhtemelen bir test dosyasıdır. "
                    "Tanımadığın bir dosyaysa ya da bir e-posta ekinden geldiyse, Karantinaya al'ı seç ve "
                    "o dosyayı nereden aldığını hatırlamaya çalış.",
                    "Do not panic. Read the file path: if it is one you recognise, one you downloaded "
                    "yourself, and the signature name contains something like “Test” or “EICAR”, it is "
                    "probably a test file. If it is a file you do not recognise, or it came from an email "
                    "attachment, choose Quarantine and try to remember where that file came from.")),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Carotene yalnızca sen taramayı başlattığında çalışır; indirdiğin her dosyayı "
                        "otomatik olarak kontrol etmez. Yeni indirdiğin ya da bir e-postadan gelen "
                        "dosyaları açmadan önce taramayı alışkanlık hâline getir.",
                        "Carotene runs only when you start a scan yourself; it does not automatically check "
                        "every file you download. Make scanning a habit for files you just downloaded or "
                        "received by email, before you open them.")),
        ]),
    ]
    return {
        "id": "carotene", "grup": "uygulamalar", "ikon": "arama", "ad": T("Carotene", "Carotene"),
        "alt": T("Virüs taraması", "Virus scanner"),
        "ozet": T("Dosyalarını bilinen zararlı yazılım imzalarına karşı tarar.",
                  "Scans your files against known malware signatures."),
        "vurgu": "carotene", "sahne": carotene_sahnesi(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": {"ad": T("Carotene", "Carotene"), "komut": KOMUT}, "root": False,
    }
