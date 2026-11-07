# -*- coding: utf-8 -*-
"""Etik ve sorumluluk: Guvenlik Paneli'nin hedef kontrolu (ozel ag sorusu, elle yazma onayi, gunluk).

Sahne, panel sahnesinin ustune iki onay penceresi ekler. Metinler panelin gercek akisini ozetler;
hicbir yasadan madde/ceza atfi yoktur ve hukuki tavsiye degildir.
"""
from former_sahneler import PH, PW, UST, panel_sahnesi
from former_zaman import T, ayarla, balon, bekle, git, tikla, yaz
from konular._panel import PANEL_KOMUT, arac_sec
from konular.nmap import ARAC as NMAP

HEDEF_OZEL = "192.168.1.20"
HEDEF_ACIK = "93.184.216.34"


def _sahne():
    s = panel_sahnesi(NMAP)
    s["ogeler"] += [
        # --- 1) "Bu ag sana mi ait?"
        {"id": "e1_perde", "tur": "perde", "x": 0, "y": UST, "w": PW, "h": PH - UST, "bayrak": "etik_ozel"},
        {"id": "e1_kutu", "tur": "diyalog", "x": 190, "y": 96, "w": 380, "h": 210, "bayrak": "etik_ozel",
         "baslik": T("Bu ağ sana mı ait?", "Is this your network?")},
        {"id": "e1_metin", "tur": "metin", "x": 206, "y": 128, "w": 348, "h": 100, "bayrak": "etik_ozel",
         "sar": True, "boyut": 8, "renk": "soluk",
         "metin": T("Hedef özel bir ağda (192.168.1.0/24). Okul, iş yeri ya da kafe gibi başkasına ait bir ağ "
                    "olabilir. Evet dersen bu ağ hatırlanır ve bir daha sorulmaz.",
                    "The target is on a private network (192.168.1.0/24). It may belong to someone else, like a "
                    "school, workplace or café. If you say yes, this network is remembered and you won't be "
                    "asked again.")},
        {"id": "e1_iptal", "tur": "dugme", "x": 206, "y": 262, "w": 80, "h": 28, "bayrak": "etik_ozel",
         "metin": T("Vazgeç", "Cancel")},
        {"id": "e1_evet", "tur": "dugme", "x": 330, "y": 262, "w": 226, "h": 28, "bayrak": "etik_ozel",
         "birincil": True, "metin": T("Evet, bu benim ağım / iznim var", "Yes, it's my network / I have permission")},
        # --- 2) acik adres: hedefi elle yaz
        {"id": "e2_perde", "tur": "perde", "x": 0, "y": UST, "w": PW, "h": PH - UST, "bayrak": "etik_acik"},
        {"id": "e2_kutu", "tur": "diyalog", "x": 190, "y": 80, "w": 380, "h": 250, "bayrak": "etik_acik",
         "baslik": T("Bu hedef sana ait görünmüyor", "This target doesn't look like yours")},
        {"id": "e2_metin", "tur": "metin", "x": 206, "y": 112, "w": 348, "h": 100, "bayrak": "etik_acik",
         "sar": True, "boyut": 8, "renk": "soluk",
         "metin": T("Yalnızca sahibi olduğun ya da yazılı izin aldığın sistemleri test et. Güvenle deneyebileceğin "
                    "yerler: kendi makinen (127.0.0.1) ve CarotOS Poligon.",
                    "Only test systems you own or have written permission to test. Safe places to practise: your "
                    "own machine (127.0.0.1) and CarotOS Poligon.")},
        {"id": "e2_yaz", "tur": "metin", "x": 206, "y": 214, "w": 348, "h": 14, "bayrak": "etik_acik",
         "boyut": 8, "renk": "soluk",
         "metin": T("Devam etmek için hedefi aynen yaz:", "To continue, type the target exactly:")},
        {"id": "e2_alan", "tur": "alan", "x": 206, "y": 236, "w": 348, "h": 26, "bayrak": "etik_acik",
         "yer": HEDEF_ACIK},
        {"id": "e2_iptal", "tur": "dugme", "x": 206, "y": 282, "w": 80, "h": 28, "bayrak": "etik_acik",
         "metin": T("Vazgeç", "Cancel")},
        {"id": "e2_devam", "tur": "dugme", "x": 458, "y": 282, "w": 96, "h": 28, "bayrak": "etik_acik",
         "birincil": True, "pasif": True, "metin": T("Devam et", "Continue")},
    ]
    return s


def konu():
    adimlar = arac_sec("nmap") + [
        git("alan:target"),
        balon("alan:target", T("Hedefi yazarken", "When you type a target"),
              T("nmap, nikto, sqlmap ve hydra gibi araçlarda hedefe bir adres yazarsın. Panel, çalıştırmadan önce "
                "adrese bakar (sorgulama yapmaz) ve hedefin kime ait olabileceğini tahmin eder.",
                "In tools like nmap, nikto, sqlmap and hydra you type an address as the target. Before running, "
                "the panel looks at the address (it does not look anything up) and guesses who the target could "
                "belong to."), "sag"),
        yaz("alan:target", "127.0.0.1"),
        balon("alan:target", T("Kendi bilgisayarın", "Your own computer"),
              T("127.0.0.1 senin kendi makinendir. Hiçbir şey sorulmaz: kendi sisteminde istediğin gibi "
                "alıştırma yapabilirsin.",
                "127.0.0.1 is your own machine. Nothing is asked: you can practise on your own system as you "
                "like."), "sag"),
        yaz("alan:target", HEDEF_OZEL),
        tikla("btn:calistir", bayrak={"etik_ozel": True}),
        balon("e1_kutu", T("Özel ağ: bir kez sorulur", "Private network: asked once"),
              T("Ev, okul ya da kafe ağı gibi özel bir adres yazdın. Panel, bu ağın sana ait olup olmadığını "
                "sorar. Okul ya da kafe ağı senin değildir; orada izinsiz deneme yapma.",
                "You typed a private address, like a home, school or café network. The panel asks whether this "
                "network belongs to you. A school or café network is not yours; do not try things there without "
                "permission."), "sag"),
        tikla("e1_evet", bayrak={"etik_ozel": False}),
        balon("a_bilgi", T("Ağ hatırlanır", "The network is remembered"),
              T("Evet dersen bu ağ hatırlanır ve bir daha sorulmaz. Yanlış bir ağa evet dersen sorumluluk "
                "sendedir.",
                "If you say yes, this network is remembered and you are not asked again. If you say yes for a "
                "network that is not yours, the responsibility is yours."), "alt"),
        yaz("alan:target", HEDEF_ACIK),
        tikla("btn:calistir", bayrak={"etik_acik": True}),
        balon("e2_kutu", T("Açık internet adresi", "A public internet address"),
              T("Bu bir internet adresi. Panel bu kez evet düğmesi vermez: hedefi aynen elle yazman gerekir. "
                "Bu, düşünmeden basılan bir onayı engeller.",
                "This is a public internet address. This time the panel gives no yes button: you have to type "
                "the target exactly. That stops an approval pressed without thinking."), "sag"),
        yaz("e2_alan", HEDEF_ACIK),
        ayarla(e2_devam={"pasif": False}),
        tikla("e2_devam", bayrak={"etik_acik": False}),
        balon("a_bilgi", T("Her onay günlüğe yazılır", "Every confirmation is logged"),
              T("Verdiğin her onay bilgisayarında bir günlüğe yazılır "
                "(~/.config/carotos-panel/etik-gunlugu.log). Günlük hiçbir yere gönderilmez; yalnızca sana aittir.",
                "Every confirmation you give is written to a log on your computer "
                "(~/.config/carotos-panel/etik-gunlugu.log). The log is not sent anywhere; it belongs only to "
                "you."), "alt"),
        bekle(300),
    ]
    bolumler = [
        (T("Neden var", "Why it exists"), [
            ("p", T("Bu araçlar öğrenmek ve kendi sistemini savunmak içindir. Başkasının ağında ya da sisteminde "
                    "izinsiz tarama veya deneme yapmak birçok ülkede suçtur; geçerli kuralları kendin kontrol et. "
                    "Bu metin hukuki tavsiye değildir.",
                    "These tools are for learning and for defending your own systems. Scanning or trying things "
                    "on someone else's network or system without permission is a criminal offence in many "
                    "countries; check the rules that apply to you. This text is not legal advice.")),
        ]),
        (T("Panel ne yapar", "What the panel does"), [
            ("tablo", [
                (T("127.0.0.1, localhost", "127.0.0.1, localhost"),
                 T("Kendi bilgisayarın: hiçbir şey sorulmaz.", "Your own computer: nothing is asked.")),
                (T("Özel ağ", "Private network"),
                 T("Ev, okul, kafe: “Bu ağ sana mı ait?” bir kez sorulur.",
                   "Home, school, café: “Is this your network?” is asked once.")),
                (T("Başka bir yer", "Anywhere else"),
                 T("Açık internet adresi ya da geniş blok: hedefi aynen yazarsın, yoksa araç çalışmaz.",
                   "A public address or wide block: you type the target exactly, or the tool does not run.")),
            ]),
            ("p", T("Her onay günlüğe yazılır. Günlük yalnızca senin bilgisayarında durur.",
                    "Every confirmation is written to the log. The log stays only on your computer.")),
        ]),
        (T("Güvenle alıştır", "Practise safely"), [
            ("liste", [
                T("Kendi bilgisayarında: hedef 127.0.0.1.", "On your own computer: target 127.0.0.1."),
                T("CarotOS Poligon'da: alıştırma için hazırlanmış bir ortam.",
                  "In CarotOS Poligon: an environment built for practice."),
            ]),
            ("uyari", T("Bir ağın sana ait olduğundan emin değilsen evet deme. Onay verdiğinde sorumluluk sana "
                        "geçer.",
                        "If you are not sure a network is yours, do not say yes. When you confirm, the "
                        "responsibility is yours.")),
        ]),
    ]
    return {
        "id": "etik", "grup": "baslarken", "ikon": "kalkan", "ad": T("Etik ve sorumluluk", "Ethics and responsibility"),
        "alt": T("İzinli yerde kullan", "Use it where you have permission"),
        "ozet": T("Güvenlik araçlarını nerede ve nasıl kullanmalı: izin, onay ve günlük.",
                  "Where and how to use security tools: permission, confirmation and the log."),
        "vurgu": "guvenlik", "sahne": _sahne(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": {"ad": T("Güvenlik Paneli", "Security Panel"), "komut": PANEL_KOMUT}, "root": False,
    }
