# -*- coding: utf-8 -*-
"""CarotPot genel tanitimi: yerel ag tuzagi."""
from former_zaman import T, ayarla, balon, git, tikla
from former_sahneler import carotpot_sahnesi

KOMUT = ["python3", "/opt/carotos/carotpot/carotos-carotpot.py"]


def konu():
    adimlar = [
        balon("p_alt", T("CarotPot ne yapar", "What CarotPot does"),
              T("CarotPot, bu bilgisayarda sahte servisler açan bir ağ tuzağıdır. Gerçek bir şey yoktur; "
                "amaç, ağındaki birinin ya da bir kötücül yazılımın bu bilgisayarı taramasını, kullanıcı/"
                "parola denemesini fark edip kaydetmektir.",
                "CarotPot is a network trap that opens fake services on this computer. Nothing real is "
                "there; the goal is to notice and log when someone — or some malware — on your network "
                "scans this computer or tries usernames and passwords."), "sag"),
        tikla("p_baslat", bayrak={"baslat_diyalog": True}),
        balon("b_metin", T("Açmadan önce", "Before you turn it on"),
              T("Tuzağı açmak, güvenlik duvarında bazı portlara izin verir ve orada sahte bir servis "
                "dinlemeye başlar. Bu yalnızca güvendiğin ağlarda (evin, okulun laboratuvarı) güvenlidir; "
                "bir kafede ya da otel Wi-Fi'ında açma.",
                "Turning the trap on opens some ports in the firewall and starts a fake service listening "
                "there. This is safe only on networks you trust (your home, a school lab); do not turn it "
                "on at a café or hotel Wi-Fi.")),
        tikla("b_tamam", bayrak={"baslat_diyalog": False, "acik": True}, ayarla={
            "p_hap": {"metin": T("Tuzak açık", "Trap on"), "renk": "yesil"}}),
        ayarla(_bayrak={"o1": True}),
        git("olay1"),
        balon("olay1", T("İlk olay: port taraması", "First event: a port scan"),
              T("Bir cihaz bu bilgisayarın portlarına bakmış. Satırda kimin (IP adresi), ne yaptığı (port "
                "taraması) ve kaç sahte servise baktığı yazar. Bu sayfa, nmap konusunda gördüğün "
                "taramanın karşı taraftan — hedef olarak — görünüşüdür.",
                "A device looked at this computer's ports. The line shows who (IP address), what they did "
                "(port scan), and how many fake services they probed. This page is the same scan you saw "
                "in the nmap topic, seen from the other side — as the target.")),
        ayarla(_bayrak={"o2": True}),
        git("olay2"),
        balon("olay2", T("İkinci olay: giriş denemesi", "Second event: a login attempt"),
              T("Aynı adres şimdi SSH ile giriş denemiş; kullanıcı adı ve parola (gizlenmiş olarak) "
                "görünür. Bu, CarotPot'un hydra konusunda gördüğün türden bir kaba kuvvet denemesini canlı "
                "yakaladığı andır.",
                "The same address now tried an SSH login; the username and password (hidden) are shown. "
                "This is the moment CarotPot catches, live, the kind of brute-force attempt you saw in the "
                "hydra topic.")),
        tikla("cp:saldirgan", sayfa="saldirgan"),
        balon("s_kaynak1", T("Saldırgan profili", "Attacker profile"),
              T("Saldırganlar sayfası, her kaynağı tek bir profilde toplar: kaç olay ürettiği, hangi "
                "kullanıcı adlarını denediği, ilk ve son görülme zamanı. Soldan bir kaynak seçip sağda "
                "ayrıntıyı görürsün.",
                "The Attackers page gathers each source into one profile: how many events it produced, "
                "which usernames it tried, when it was first and last seen. Pick a source on the left and "
                "see the detail on the right.")),
        git("s_risk"),
        balon("s_risk", T("Risk etiketi", "The risk label"),
              T("31 giriş denemesi ve bir port taraması bir araya gelince CarotPot bu kaynağı “yüksek "
                "risk” sayar. Bu otomatik bir etikettir, kesin bir hüküm değildir; yine de bir göz atmaya "
                "değer.",
                "31 login attempts together with a port scan make CarotPot mark this source “high risk”. "
                "This is an automatic label, not a final verdict; still, it is worth a look.")),
        tikla("s_engelle", bayrak={"engel_diyalog": True}),
        balon("e_metin", T("Engellemeden önce", "Before you block"),
              T("Engelle, bu adresten gelen her şeyi güvenlik duvarında reddeder. Adres tanıdığın bir "
                "cihaza (öğretmen bilgisayarı, yazıcı) aitse engelleme; “Yok say” ile profili sessize al.",
                "Block rejects everything from this address at the firewall. If the address belongs to a "
                "device you know (a teacher's computer, a printer), do not block it; use “Ignore” to "
                "silence the profile instead.")),
        tikla("e_tamam", bayrak={"engel_diyalog": False, "engelli": True}),
        balon("s_engelli", T("Engellendi", "Blocked"),
              T("Artık bu adresten gelen bağlantılar reddediliyor — tıpkı ufw konusunda gördüğün “DENY” "
                "kuralı gibi; CarotPot bu kuralı senin yerine ekledi.",
                "Connections from this address are now rejected — just like the “DENY” rule you saw in the "
                "ufw topic; CarotPot added that rule for you.")),
    ]
    bolumler = [
        (T("CarotPot nedir", "What CarotPot is"), [
            ("p", T("CarotPot bir “bal küpü” (honeypot) uygulamasıdır: gerçek bir servis gibi görünen ama "
                    "aslında hiçbir şey yapmayan sahte servisler açar. Bu bilgisayara normal şartlarda "
                    "hiç kimsenin bağlanmaması gerektiği için, bu sahte servislere gelen her bağlantı "
                    "zaten şüphelidir.",
                    "CarotPot is a “honeypot” app: it opens fake services that look real but do nothing. "
                    "Since nobody should normally connect to this computer at all, every connection to "
                    "these fake services is already suspicious.")),
            ("p", T("Bunu bir dükkânın vitrinine konan sahte bir kasa gibi düşün: içinde para yoktur, ama "
                    "biri ona dokunursa bunu hemen fark edersin.",
                    "Think of it like a fake cash register placed in a shop window: there is no money in "
                    "it, but you notice right away if someone touches it.")),
        ]),
        (T("Nasıl kullanılır", "How to use it"), [
            ("liste", [
                T("Pano'dan Başlat'a bas; açılan uyarıyı oku ve yalnızca güvendiğin ağdaysan onayla.",
                  "Press Start on the Dashboard; read the warning that opens and confirm only if you are on "
                  "a network you trust."),
                T("Pano canlı akışta gelen olayları gösterir: taramalar, giriş denemeleri, web istekleri.",
                  "The Dashboard's live feed shows incoming events: scans, login attempts, web requests."),
                T("Saldırganlar sayfasında bir kaynağı seç, profiline bak, gerekirse Engelle.",
                  "On the Attackers page, pick a source, look at its profile, and Block it if needed."),
            ]),
        ]),
        (T("Bu bir saldırı mı", "Is this an attack"), [
            ("p", T("Çoğu zaman hayır. Ev ağındaki bir telefon ya da yazıcının otomatik taraması, ya da "
                    "internetten rastgele adresleri deneyen bir bot bile olay üretebilir. Önemli olan "
                    "paniklememek; adres tanıdıksa yok say, tanımıyorsan ve davranış ısrarcıysa (çok "
                    "sayıda giriş denemesi gibi) engelle.",
                    "Often not. Even a phone or printer's automatic scan on your home network, or a bot "
                    "trying random addresses on the internet, can create an event. The point is not to "
                    "panic: ignore it if the address is familiar, and block it if it is unfamiliar and "
                    "persistent (many login attempts, for instance).")),
        ]),
        (T("Dikkat", "Be careful"), [
            ("uyari", T("Tuzağı yalnızca kendi güvendiğin ağında aç; paylaşılan bir ağda (kafe, otel, okul "
                        "misafir ağı) açman hem gereksizdir hem de yanlış anlaşılabilir. Sistem açılışında "
                        "kendiliğinden başlamaz, her seferinde elle açman gerekir.",
                        "Turn the trap on only on a network you trust; turning it on on a shared network "
                        "(café, hotel, a school guest network) is both pointless and could be "
                        "misunderstood. It does not start automatically at boot; you must turn it on by "
                        "hand each time.")),
        ]),
    ]
    return {
        "id": "carotpot", "grup": "uygulamalar", "ikon": "altigen", "ad": T("CarotPot", "CarotPot"),
        "alt": T("Yerel ağ tuzağı", "Local network trap"),
        "ozet": T("Sahte servislerle ağındaki şüpheli davranışı yakalar.",
                  "Catches suspicious behaviour on your network with fake services."),
        "vurgu": "carotpot", "sahne": carotpot_sahnesi(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": {"ad": T("CarotPot", "CarotPot"), "komut": KOMUT}, "root": False,
    }
