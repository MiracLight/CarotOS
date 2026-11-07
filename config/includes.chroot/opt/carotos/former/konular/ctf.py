# -*- coding: utf-8 -*-
"""CTF yarismasi: Poligon ogrenci uygulamasindaki "CTF yarismasi" penceresi (gorev, dosya, ipucu, bayrak, skor)."""
from former_sahneler import PH, PW
from former_zaman import T, ayarla, balon, bekle, git, tikla, yaz

KOMUT = ["python3", "/opt/carotos/poligon/ogrenci_uygulama.py"]

BAYRAK = "CAROT{...}"


def _sahne():
    o = [
        {"id": "c_baslik", "tur": "metin", "x": 24, "y": 38, "w": 300, "h": 20, "boyut": 14, "kalin": True,
         "metin": T("CTF yarışması", "CTF contest")},
        {"id": "c_sure", "tur": "metin", "x": 330, "y": 42, "w": 200, "h": 14, "boyut": 8.6, "renk": "vurgu_yazi",
         "metin": T("Kalan: 44:10", "Remaining: 44:10")},
        {"id": "c_puan", "tur": "metin", "x": 528, "y": 42, "w": 210, "h": 14, "boyut": 8.6, "hiza": "sag",
         "metin": T("Puanın: 0 · Sıran: 4", "Your score: 0 · Rank: 4")},
        {"id": "c_liste_kart", "tur": "kart", "x": 22, "y": 74, "w": 250, "h": 150},
        {"id": "c_g1", "tur": "satir", "x": 30, "y": 82, "w": 234, "h": 26, "renk": "soluk",
         "metin": T("Tek katman · 100 puan", "One layer · 100 points")},
        {"id": "c_g2", "tur": "satir", "x": 30, "y": 112, "w": 234, "h": 26, "renk": "soluk",
         "metin": T("Sezar'ın şifresi · 150 puan", "Caesar's cipher · 150 points")},
        {"id": "c_g3", "tur": "satir", "x": 30, "y": 142, "w": 234, "h": 26, "renk": "soluk",
         "metin": T("Saldırgan kim? · 200 puan", "Who is the attacker? · 200 points")},
        {"id": "c_detay_kart", "tur": "kart", "x": 284, "y": 74, "w": 454, "h": 150},
        {"id": "c_detay", "tur": "metin", "x": 298, "y": 86, "w": 428, "h": 40, "sar": True, "boyut": 8.6,
         "metin": T("Bir görev seç.", "Pick a challenge.")},
        {"id": "c_dosya", "tur": "dugme", "x": 298, "y": 134, "w": 130, "h": 26,
         "metin": T("Dosyayı kaydet", "Save file")},
        {"id": "c_ipucu", "tur": "dugme", "x": 436, "y": 134, "w": 170, "h": 26,
         "metin": T("İpucu aç (−10 puan)", "Open a hint (−10 points)")},
        {"id": "c_ipucu_metin", "tur": "metin", "x": 298, "y": 170, "w": 428, "h": 30, "sar": True, "boyut": 8.2,
         "renk": "soluk", "metin": ""},
        {"id": "c_bayrak", "tur": "alan", "x": 22, "y": 240, "w": 560, "h": 28, "yer": T(BAYRAK, BAYRAK)},
        {"id": "c_gonder", "tur": "dugme", "x": 592, "y": 240, "w": 146, "h": 28, "birincil": True,
         "metin": T("Gönder", "Submit")},
        {"id": "c_sonuc", "tur": "metin", "x": 24, "y": 282, "w": 700, "h": 16, "boyut": 8.8, "kalin": True,
         "renk": "yesil", "metin": ""},
        {"id": "c_skor_kart", "tur": "kart", "x": 22, "y": 312, "w": 716, "h": 54},
        {"id": "c_skor", "tur": "metin", "x": 36, "y": 322, "w": 690, "h": 34, "sar": True, "boyut": 8.2,
         "renk": "soluk",
         "metin": T("Skor tablosu: 1. Ayşe 350 · 2. Can 250 · 3. Deniz 100 · 4. Sen 0",
                    "Scoreboard: 1. Alex 350 · 2. Sam 250 · 3. Robin 100 · 4. You 0")},
    ]
    return {"genislik": PW, "yukseklik": PH, "vurgu": "guvenlik", "sayfa": None,
            "baslik": T("CarotOS Poligon · CTF", "CarotOS Poligon · CTF"), "ogeler": o}


def konu():
    adimlar = [
        balon("c_baslik", T("CTF nedir", "What CTF is"),
              T("CTF (Capture The Flag), bayrak yakalama yarışmasıdır. Her görevde bir dosya incelersin ve içinde "
                "saklı bir bayrak bulursun: CAROT{...} biçiminde bir metin. Öğretmen yarışmayı başlatınca süre "
                "işler ve herkes aynı görevleri çözmeye çalışır.",
                "CTF (Capture The Flag) is a flag-capturing contest. In each challenge you examine a file and "
                "find a hidden flag: a text in the form CAROT{...}. When your teacher starts the contest the "
                "clock runs and everyone tries to solve the same challenges."), "alt"),
        git("c_g1"),
        tikla("c_g1", ayarla={
            "c_g1": {"vurgulu": True, "renk": "vurgu"},
            "c_detay": {"metin": T("Dosyadaki mesaj bir kodlamayla gizlenmiş. Kodlamayı çöz ve bayrağı bul.",
                                   "The message in the file is hidden with an encoding. Decode it and find the flag.")}}),
        balon("c_detay", T("Görev ve dosya", "Challenge and file"),
              T("Görevi seçince açıklaması görünür. “Dosyayı kaydet” görevin dosyasını ana klasöründeki "
                "Poligon-CTF klasörüne kaydeder. Dosya sana özeldir: bayrağın başkasınınkiyle aynı değildir, "
                "o yüzden birinin bayrağını kopyalamak işe yaramaz.",
                "Picking a challenge shows its description. “Save file” saves the challenge's file to the "
                "Poligon-CTF folder in your home folder. The file is yours alone: your flag differs from "
                "everyone else's, so copying someone's flag does not work."), "alt"),
        tikla("c_dosya"),
        git("c_ipucu"),
        balon("c_ipucu", T("İpucu", "Hints"),
              T("Takılırsan ipucu açabilirsin. İpuçları sırayla açılır ve her biri puan keser; kesinti, görevi "
                "çözdüğünde düşülür. Hiç ipucu açmadan çözmek en çok puanı verir.",
                "If you get stuck you can open a hint. Hints open in order and each one costs points; the "
                "cost is deducted when you solve the challenge. Solving without any hint gives the most "
                "points."), "alt"),
        tikla("c_ipucu", ayarla={"c_ipucu_metin": {"metin": T(
            "İpucu: Harf ve rakamlardan oluşan, sonu bazen = ile biten metinler çoğunlukla Base64'tür.",
            "Hint: Text made of letters and digits, sometimes ending in =, is very often Base64.")}}),
        bekle(500),
        yaz("c_bayrak", T("CAROT{kod_cozuldu}", "CAROT{kod_cozuldu}")),
        git("c_gonder"),
        tikla("c_gonder", ayarla={
            "c_sonuc": {"metin": T("Doğru! +100 puan.", "Correct! +100 points.")},
            "c_puan": {"metin": T("Puanın: 90 · Sıran: 3", "Your score: 90 · Rank: 3")},
            "c_g1": {"renk": "yesil"},
            "c_skor": {"metin": T("Skor tablosu: 1. Ayşe 350 · 2. Can 250 · 3. Sen 90 · 4. Deniz 100",
                                  "Scoreboard: 1. Alex 350 · 2. Sam 250 · 3. You 90 · 4. Robin 100")}}),
        bekle(300),
        balon("c_sonuc", T("Bayrak gönderme", "Submitting a flag"),
              T("Bayrağı kutuya yaz ve Gönder'e bas. Sunucu bayrağı senin için doğrular. Art arda çok yanlış "
                "bayrak denersen kısa bir bekleme süresi girer; bayrak tahmin etmek yerine dosyayı incelemek "
                "daha hızlıdır.",
                "Type the flag in the box and press Submit. The server checks the flag for you. If you try "
                "too many wrong flags in a row there is a short wait; examining the file is faster than "
                "guessing."), "alt"),
        balon("c_skor", T("Skor tablosu", "The scoreboard"),
              T("Bir görevi ne kadar çok kişi çözerse değeri o kadar düşer; ilk çözen küçük bir bonus alır. "
                "Yarışmanın son dakikalarında öğretmen tabloyu dondurabilir. O zaman sıralamayı bitişte görürsün.",
                "The more people solve a challenge, the less it is worth; the first solver gets a small "
                "bonus. In the last minutes the teacher can freeze the board. Then you see the final ranking "
                "only at the end."), "ust"),
    ]
    bolumler = [
        (T("Nasıl katılırım", "How do I join"), [
            ("p", T("CTF yalnızca sınıf modunda vardır. Öğrenci uygulamasında sınıf moduyla öğretmenin odasına "
                    "bağlan; üst çubukta “CTF yarışması” düğmesi belirir.",
                    "CTF is only available in class mode. In the student app, connect to your teacher's room in "
                    "class mode; a “CTF contest” button appears in the top bar.")),
            ("liste", [
                T("Öğretmen CTF sayfasında görevleri seçip yarışmayı başlatır.",
                  "The teacher picks the challenges on the CTF page and starts the contest."),
                T("Sen “CTF yarışması” düğmesine basıp pencereyi açarsın.",
                  "You press “CTF contest” to open the window."),
                T("Görevi seç, dosyayı kaydet, incele ve bayrağı gönder.",
                  "Pick a challenge, save the file, examine it and submit the flag."),
            ]),
        ]),
        (T("Görev türleri", "Challenge types"), [
            ("p", T("Görevler beş gruba ayrılır: kodlama, kriptografi, hash, günlük analizi ve adli bilişim. "
                    "Her görevin kolay, orta ya da zor etiketi vardır.",
                    "Challenges fall into five groups: encoding, cryptography, hash, log analysis and forensics. "
                    "Each challenge is labelled easy, medium or hard.")),
        ]),
        (T("Adil oyun", "Fair play"), [
            ("not", T("Dosyalar herkese farklı üretilir ve doğrulama sunucuda yapılır. Bu yüzden bayrak "
                      "paylaşmanın anlamı yok; yarışma, öğrenmen için.",
                      "Files are generated differently for everyone and checking happens on the server. So "
                      "sharing flags is pointless; the contest is for your learning.")),
            ("uyari", T("Yarışma süresi bitince bayrak gönderemezsin. Dosyaları ve notlarını yine de "
                        "saklayabilirsin.",
                        "When the time is up you can no longer submit flags. You can still keep the files and "
                        "your notes.")),
        ]),
    ]
    return {
        "id": "ctf", "grup": "uygulamalar", "ikon": "oyun", "ad": T("CTF yarışması", "CTF contest"),
        "alt": T("Bayrağı bul, puanı kap", "Find the flag, win the points"),
        "ozet": T("Poligon'da bayrak yakalama yarışması: görev, dosya, ipucu, skor.",
                  "A capture-the-flag contest in Poligon: challenges, files, hints, scoreboard."),
        "vurgu": "guvenlik", "sahne": _sahne(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": {"ad": T("Poligon (Öğrenci)", "Poligon (Student)"), "komut": KOMUT}, "root": False,
    }
