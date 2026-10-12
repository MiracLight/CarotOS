"""
CarotOS Poligon -- "Soru Olustur" alan semalari.

Ogretmen bir araci secip parametrelerini KENDISI belirledigi zaman
kullanilir. Her arac icin hangi alanlarin doldurulacagini, her alan icin
5 hazir oneriyi ve formdan gelen string degerleri servis parametrelerine
nasil cevirecegimizi burada tanimliyoruz.

GTK'dan BAGIMSIZ: butun mantik burada; ogretmen_uygulama.py sadece bu
fonksiyonlari cagirip arayuzu cizer. Boylece GTK'siz test edilebilir.

Uretilen parametre sozlugu, zorluk on-ayarlariyla (gorevlerin 'zorluklar'
blogu) AYNI anahtarlari kullanir; yani ogrenci istemcisi bunlari aynen
servise gecirir, makine cevabi bu parametrelere gore uretilir.
"""

from __future__ import annotations

import random

# Her arac: baslik + alan listesi. Alan turleri:
#   "aralik" -> "lo-hi" metni, [lo, hi] listesine cevrilir
#   "sayi"   -> tam sayi (min/max arasina kistirilir)
#   "secim"  -> sabit secenekler arasindan biri (string)
SABLONLAR: dict = {
    "nmap-01": {
        "baslik": {"tr": "nmap — Gizli Portu Bul", "en": "nmap — Find the Hidden Port"},
        "alanlar": [
            {"anahtar": "gizli_port_araligi",
             "etiket": {"tr": "Port aralığı (alt-üst)", "en": "Port range (low-high)"},
             "tur": "aralik", "varsayilan": "20000-20999"},
            {"anahtar": "gurultu_sayisi",
             "etiket": {"tr": "Gürültü portu sayısı", "en": "Noise port count"},
             "tur": "sayi", "min": 1, "max": 12, "varsayilan": "5",
             "oneriler": ["3", "5", "7", "9", "11"]},
        ],
    },
    "john-01": {
        "baslik": {"tr": "john — Hash'i Kır", "en": "john — Crack the Hash"},
        "alanlar": [
            {"anahtar": "basamak",
             "etiket": {"tr": "Parola hane sayısı", "en": "Password digit count"},
             "tur": "sayi", "min": 1, "max": 6, "varsayilan": "3",
             "oneriler": ["1", "2", "3", "4", "5"]},
        ],
    },
    "sqlmap-01": {
        "baslik": {"tr": "sqlmap — Gizli Tabloyu Çıkar", "en": "sqlmap — Extract the Hidden Table"},
        "alanlar": [
            {"anahtar": "tuzak_tablolar",
             "etiket": {"tr": "Tuzak tablo sayısı", "en": "Decoy table count"},
             "tur": "sayi", "min": 0, "max": 4, "varsayilan": "2",
             "oneriler": ["0", "1", "2", "3", "4"]},
        ],
    },
    "tshark-01": {
        "baslik": {"tr": "tshark — Trafiği Yakala", "en": "tshark — Capture the Traffic"},
        "alanlar": [
            {"anahtar": "gurultu",
             "etiket": {"tr": "Gürültü akışı sayısı", "en": "Noise stream count"},
             "tur": "sayi", "min": 0, "max": 4, "varsayilan": "2",
             "oneriler": ["0", "1", "2", "3", "4"]},
            {"anahtar": "kodlama",
             "etiket": {"tr": "Flag kodlaması", "en": "Flag encoding"},
             "tur": "secim", "secenekler": ["duz", "hex"], "varsayilan": "duz"},
        ],
    },
}


def arac_listesi() -> list[str]:
    """Soru olusturulabilen gorev id'leri (saldiri araclari)."""
    return list(SABLONLAR.keys())


def _alan_bul(gorev_id: str, anahtar: str) -> dict | None:
    for a in SABLONLAR.get(gorev_id, {}).get("alanlar", []):
        if a["anahtar"] == anahtar:
            return a
    return None


def onerileri_uret(gorev_id: str, anahtar: str) -> list[str]:
    """Bir alan icin 5 hazir oneri doner. 'aralik' alaninda bir kismi
    rastgele uretilir (ogretmene cesitlilik sunmak icin); digerleri sabit
    listeden gelir. 'secim' alaninda tum secenekler donulur."""
    alan = _alan_bul(gorev_id, anahtar)
    if not alan:
        return []
    if alan["tur"] == "secim":
        return list(alan.get("secenekler", []))
    if alan["tur"] == "aralik":
        sabit = ["20000-20099", "20000-20999", "20000-29999"]
        rastgele = []
        for _ in range(2):
            bas = random.choice([20000, 25000, 30000, 40000])
            genislik = random.choice([99, 199, 499, 999, 4999])
            rastgele.append(f"{bas}-{bas + genislik}")
        return sabit + rastgele
    # sayi
    return list(alan.get("oneriler", []))


def varsayilan(gorev_id: str, anahtar: str) -> str:
    alan = _alan_bul(gorev_id, anahtar)
    return str(alan.get("varsayilan", "")) if alan else ""


class GecersizDeger(ValueError):
    """Formdaki bir alan gecersiz (ogretmene gosterilecek)."""


def _aralik_ayristir(metin: str) -> list[int]:
    parcalar = metin.replace(" ", "").split("-")
    if len(parcalar) != 2 or not all(p.isdigit() for p in parcalar):
        raise GecersizDeger(f"Aralık 'alt-üst' biçiminde olmalı (örn. 20000-20999): {metin!r}")
    lo, hi = int(parcalar[0]), int(parcalar[1])
    if lo >= hi:
        raise GecersizDeger(f"Alt sınır üst sınırdan küçük olmalı: {metin!r}")
    if lo < 1024 or hi > 65535:
        raise GecersizDeger("Port aralığı 1024-65535 arasında olmalı")
    return [lo, hi]


def parametreleri_ayristir(gorev_id: str, ham_degerler: dict) -> dict:
    """Formdan gelen {anahtar: metin} sozlugunu servis parametrelerine
    cevirir. Gecersiz deger GecersizDeger firlatir (arayuz yakalayip
    ogretmene gosterir)."""
    sonuc: dict = {}
    for alan in SABLONLAR.get(gorev_id, {}).get("alanlar", []):
        anahtar = alan["anahtar"]
        ham = str(ham_degerler.get(anahtar, alan.get("varsayilan", ""))).strip()
        if alan["tur"] == "aralik":
            sonuc[anahtar] = _aralik_ayristir(ham)
        elif alan["tur"] == "sayi":
            if not ham.lstrip("-").isdigit():
                raise GecersizDeger(f"{alan['etiket']['tr']}: tam sayı olmalı ({ham!r})")
            deger = int(ham)
            alt, ust = alan.get("min"), alan.get("max")
            if alt is not None and deger < alt:
                raise GecersizDeger(f"{alan['etiket']['tr']}: en az {alt} olmalı")
            if ust is not None and deger > ust:
                raise GecersizDeger(f"{alan['etiket']['tr']}: en çok {ust} olmalı")
            sonuc[anahtar] = deger
        elif alan["tur"] == "secim":
            if ham not in alan.get("secenekler", []):
                raise GecersizDeger(f"{alan['etiket']['tr']}: {alan['secenekler']} içinden biri olmalı")
            sonuc[anahtar] = ham
    return sonuc


def etiket_uret(gorev_id: str, parametreler: dict) -> str:
    """Atanan ozel soruyu ozetleyen kisa etiket (ogretmen panelinde ve
    ogrenci basliginda degil, sadece durum metninde kullanilir)."""
    parcalar = []
    for alan in SABLONLAR.get(gorev_id, {}).get("alanlar", []):
        a = alan["anahtar"]
        if a in parametreler:
            d = parametreler[a]
            d = f"{d[0]}-{d[1]}" if isinstance(d, list) else d
            parcalar.append(f"{alan['etiket']['tr']}={d}")
    return ", ".join(parcalar)
