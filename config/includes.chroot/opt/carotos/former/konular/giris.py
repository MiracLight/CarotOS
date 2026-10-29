# -*- coding: utf-8 -*-
"""Giris/harita konusu: CarotOS guvenlik uygulamalarina genel bakis."""
from former_zaman import T, ayarla, balon, bekle, git
from former_sahneler import giris_sahnesi, KAROLAR


def konu():
    adimlar = [
        balon("g_baslik", T("Hoş geldin", "Welcome"),
              T("Bu, CarotOS'un güvenlik uygulamalarına genel bir bakış. Her kutu farklı bir soruya cevap "
                "verir: bir şeye mi bakıyorum, bir şeyi mi tarıyorum, yoksa güvenli bir ortamda pratik mi "
                "yapıyorum? Hangisine tıklarsan tıkla, o konunun kendi anlatımı bu uygulamada seni "
                "bekliyor.",
                "This is an overview of CarotOS's security apps. Each tile answers a different question: "
                "am I looking at something, scanning something, or practising safely? Whichever you click, "
                "that topic's own walkthrough is waiting for you in this app."), "alt"),
    ]
    for kimlik, simge, ad, alt in KAROLAR:
        adimlar += [
            git("karo:" + kimlik),
            ayarla(**{"karo:" + kimlik: {"aktif": True}}),
            bekle(650),
            ayarla(**{"karo:" + kimlik: {"aktif": False}}),
        ]
    bolumler = [
        (T("Bu uygulamalar ne işe yarar", "What these apps are for"), [
            ("tablo", [
                (ad, alt) for (_k, _s, ad, alt) in KAROLAR
            ]),
            ("p", T("Hepsi aynı makinede, kendi yetkinle çalışır; hiçbiri sistem açılışında kendiliğinden "
                    "başlamaz. Ne zaman kullanacağını sen seçersin.",
                    "All of them run on this same machine with your own rights; none of them starts "
                    "itself at boot. You decide when to use each one.")),
        ]),
        (T("Nereden başlamalı", "Where to start"), [
            ("liste", [
                T("Hiç fikrin yoksa, Güvenlik Paneli konusuyla başla; orada 10 aracın hepsinin kısa bir "
                  "turu var.",
                  "If you have no idea, start with the Security Panel topic; it has a short tour of all 10 "
                  "tools."),
                T("Bir terimi (port, hash, güvenlik duvarı gibi) hiç duymadıysan, o terimin geçtiği aracın "
                  "konusunu aç; her konu kendi terimlerini açıklar.",
                  "If you have never heard a term (port, hash, firewall), open the topic of the tool that "
                  "uses it; every topic explains its own terms."),
                T("Bir şeyi gerçekten denemek istiyorsan Poligon'a bak; orada güvenli, izole bir ortamda "
                  "pratik yaparsın.",
                  "If you really want to try something, look at Poligon; there you practise in a safe, "
                  "isolated environment."),
            ]),
        ]),
        (T("Ortak kural", "The common rule"), [
            ("uyari", T("Bu uygulamalardaki hiçbir araç, kendi cihazların ve açıkça izin aldığın sistemler "
                        "dışında kullanılmak için yapılmamıştır. Her konunun sonunda bunu hatırlatan ayrı "
                        "bir “Dikkat” bölümü var; onları atlamadan oku.",
                        "None of the tools in these apps are meant to be used on anything other than your "
                        "own devices and systems you have clear permission for. Every topic ends with its "
                        "own “Be careful” section reminding you of this; read it, do not skip it.")),
        ]),
    ]
    return {
        "id": "giris", "grup": "baslarken", "ikon": "ev", "ad": T("Genel bakış", "Overview"),
        "alt": T("CarotOS güvenlik uygulamaları", "CarotOS security applications"),
        "ozet": T("Hangi uygulama ne işe yarar, nereden başlamalı.",
                  "What each app is for, and where to start."),
        "vurgu": "karsilama", "sahne": giris_sahnesi(), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": None, "root": False,
    }
