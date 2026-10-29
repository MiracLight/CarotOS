# -*- coding: utf-8 -*-
"""Guvenlik Paneli araclarinin konulari icin ortak yardimcilar."""

from __future__ import annotations

from former_sahneler import panel_sahnesi
from former_zaman import T, ayarla, balon, bekle, cikti, git, tikla, yaz

PANEL_KOMUT = ["python3", "/opt/carotos/security-panel/carotos-security-panel.py"]
BITTI = T("[Bitti — çıkış kodu 0]", "[Finished — exit code 0]")
T_DENEME_UYARISI = T(
    "Bu bölümdeki örnek çıktılar temsilidir; senin bilgisayarında sayılar, adresler ve sürümler farklı çıkar.",
    "Sample outputs in this section are illustrative; numbers, addresses and versions will differ on your computer.")


def arac_sec(arac_adi, baslik=None, metin=None):
    """Aracı kenar menüsünden seçme adımları."""
    k = "arac:" + arac_adi
    return [
        git(k),
        balon(k, baslik or T("Aracı seç", "Pick the tool"),
              metin or T("Soldaki listeden aracı seçersin. Sayfanın üstünde aracın ne yaptığı, ne zaman "
                         "kullanıldığı ve bir örnek yazar. Önce onu oku.",
                         "Pick the tool in the list on the left. The top of the page says what it does, when "
                         "to use it, and gives an example. Read that first."), "sag"),
        tikla(k, sayfa="arac"),
        bekle(300),
    ]


def calistir(komut_satiri, satirlar, kok=False, kok_bayragi="btn:calistir"):
    """Çalıştır'a bas, komut önizlemesi çıksın, satırlar aksın, bitiş satırı eklensin."""
    adimlar = []
    if kok:
        adimlar += [
            tikla("btn:root", bayrak={"pkexec": True}),
            yaz("pk_parola", "••••••••"),
            tikla("pk_tamam", bayrak={"pkexec": False}),
        ]
        onizleme = "$ pkexec " + komut_satiri
    else:
        adimlar += [tikla(kok_bayragi)]
        onizleme = "$ " + komut_satiri
    adimlar += [
        ayarla(onizleme={"metin": onizleme}, **{"btn:calistir": {"pasif": True}, "btn:root": {"pasif": True},
                                                  "btn:durdur": {"pasif": False}}),
        cikti("cikti", satirlar),
        ayarla(**{"btn:calistir": {"pasif": False}, "btn:root": {"pasif": False}, "btn:durdur": {"pasif": True}}),
        cikti("cikti", ["", BITTI]),
    ]
    return adimlar


def konu(kimlik, arac, adimlar, bolumler, ikon="arac", ozet=None):
    return {
        "id": kimlik, "grup": "araclar", "ikon": ikon, "ad": arac["ad"],
        "alt": arac["tagline"], "ozet": ozet or arac["ne"], "vurgu": "guvenlik",
        "sahne": panel_sahnesi(arac), "adimlar": adimlar, "bolumler": bolumler,
        "uygulama": {"ad": T("Güvenlik Paneli", "Security Panel"), "komut": PANEL_KOMUT},
        "root": bool(arac.get("root")),
    }
