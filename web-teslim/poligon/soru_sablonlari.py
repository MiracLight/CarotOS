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
        "baslik": {"tr": "nmap — Açık Port Keşfi", "en": "nmap — Open Port Discovery"},
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
        "baslik": {"tr": "john — Parola Özeti Kırma", "en": "john — Password Hash Cracking"},
        "alanlar": [
            {"anahtar": "basamak",
             "etiket": {"tr": "Parola hane sayısı", "en": "Password digit count"},
             "tur": "sayi", "min": 1, "max": 6, "varsayilan": "3",
             "oneriler": ["1", "2", "3", "4", "5"]},
        ],
    },
    "sqlmap-01": {
        "baslik": {"tr": "sqlmap — SQL Enjeksiyonu", "en": "sqlmap — SQL Injection"},
        "alanlar": [
            {"anahtar": "tuzak_tablolar",
             "etiket": {"tr": "Tuzak tablo sayısı", "en": "Decoy table count"},
             "tur": "sayi", "min": 0, "max": 4, "varsayilan": "2",
             "oneriler": ["0", "1", "2", "3", "4"]},
        ],
    },
    "tshark-01": {
        "baslik": {"tr": "tshark — Ağ Trafiği Yakalama", "en": "tshark — Network Traffic Capture"},
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
    "loganaliz-01": {
        "baslik": {"tr": "grep — SSH Kaba Kuvvet Kaynağı", "en": "grep — SSH Brute-Force Source"},
        "alanlar": [
            {"anahtar": "satir_sayisi",
             "etiket": {"tr": "Günlük satır sayısı", "en": "Log line count"},
             "tur": "sayi", "min": 60, "max": 5000, "varsayilan": "300",
             "oneriler": ["150", "300", "600", "1000", "2000"]},
            {"anahtar": "saldirgan_sayisi",
             "etiket": {"tr": "Saldırgan sayısı", "en": "Attacker count"},
             "tur": "sayi", "min": 1, "max": 6, "varsayilan": "2",
             "oneriler": ["1", "2", "3", "4", "5"]},
            {"anahtar": "yakin_rakip",
             "etiket": {"tr": "Rakip saldırgan çok yakın mı? (0=hayır, 1=evet)", "en": "Close runner-up? (0=no, 1=yes)"},
             "tur": "secim", "secenekler": ["0", "1"], "varsayilan": "0"},
        ],
    },
    "loganaliz-02": {
        "baslik": {"tr": "grep — Ele Geçirilen Hesap Tespiti", "en": "grep — Compromised Account Identification"},
        "alanlar": [
            {"anahtar": "satir_sayisi",
             "etiket": {"tr": "Günlük satır sayısı", "en": "Log line count"},
             "tur": "sayi", "min": 60, "max": 5000, "varsayilan": "300",
             "oneriler": ["150", "300", "600", "1000", "2000"]},
            {"anahtar": "saldirgan_sayisi",
             "etiket": {"tr": "Saldırgan sayısı", "en": "Attacker count"},
             "tur": "sayi", "min": 1, "max": 6, "varsayilan": "2",
             "oneriler": ["1", "2", "3", "4", "5"]},
            {"anahtar": "yakin_rakip",
             "etiket": {"tr": "Rakip saldırgan çok yakın mı? (0=hayır, 1=evet)", "en": "Close runner-up? (0=no, 1=yes)"},
             "tur": "secim", "secenekler": ["0", "1"], "varsayilan": "0"},
            {"anahtar": "sahte_basari",
             "etiket": {"tr": "İkinci saldırgan da girsin mi? (0/1)", "en": "Second attacker also gets in? (0/1)"},
             "tur": "secim", "secenekler": ["0", "1"], "varsayilan": "0"},
        ],
    },
    "loganaliz-03": {
        "baslik": {"tr": "awk — Web Taraması Tespiti", "en": "awk — Web Scan Detection"},
        "alanlar": [
            {"anahtar": "satir_sayisi",
             "etiket": {"tr": "Günlük satır sayısı", "en": "Log line count"},
             "tur": "sayi", "min": 80, "max": 6000, "varsayilan": "500",
             "oneriler": ["300", "500", "800", "1500", "3000"]},
            {"anahtar": "tarayici_sayisi",
             "etiket": {"tr": "Tarayıcı sayısı", "en": "Scanner count"},
             "tur": "sayi", "min": 1, "max": 4, "varsayilan": "2",
             "oneriler": ["1", "2", "3", "4"]},
            {"anahtar": "arac_ua",
             "etiket": {"tr": "Tarayıcı araç imzası taşısın mı? (1=evet, 0=gizli)", "en": "Scanner shows tool signature? (1=yes, 0=hidden)"},
             "tur": "secim", "secenekler": ["1", "0"], "varsayilan": "1"},
            {"anahtar": "yakin_rakip",
             "etiket": {"tr": "Rakip saldırgan çok yakın mı? (0=hayır, 1=evet)", "en": "Close runner-up? (0=no, 1=yes)"},
             "tur": "secim", "secenekler": ["0", "1"], "varsayilan": "0"},
        ],
    },
    "loganaliz-04": {
        "baslik": {"tr": "awk — Taramayla Ulaşılan Yol", "en": "awk — Path Reached by a Scan"},
        "alanlar": [
            {"anahtar": "satir_sayisi",
             "etiket": {"tr": "Günlük satır sayısı", "en": "Log line count"},
             "tur": "sayi", "min": 80, "max": 6000, "varsayilan": "500",
             "oneriler": ["300", "500", "800", "1500", "3000"]},
            {"anahtar": "tarayici_sayisi",
             "etiket": {"tr": "Tarayıcı sayısı", "en": "Scanner count"},
             "tur": "sayi", "min": 1, "max": 4, "varsayilan": "2",
             "oneriler": ["1", "2", "3", "4"]},
            {"anahtar": "arac_ua",
             "etiket": {"tr": "Tarayıcı araç imzası taşısın mı? (1=evet, 0=gizli)", "en": "Scanner shows tool signature? (1=yes, 0=hidden)"},
             "tur": "secim", "secenekler": ["1", "0"], "varsayilan": "1"},
            {"anahtar": "yakin_rakip",
             "etiket": {"tr": "Rakip saldırgan çok yakın mı? (0=hayır, 1=evet)", "en": "Close runner-up? (0=no, 1=yes)"},
             "tur": "secim", "secenekler": ["0", "1"], "varsayilan": "0"},
        ],
    },
    "loganaliz-05": {
        "baslik": {"tr": "CarotPot — Tuzak Kaydında Kullanıcı Adı Analizi", "en": "CarotPot — Username Analysis in Honeypot Logs"},
        "alanlar": [
            {"anahtar": "saldirgan_sayisi",
             "etiket": {"tr": "Saldırgan sayısı", "en": "Attacker count"},
             "tur": "sayi", "min": 2, "max": 8, "varsayilan": "4",
             "oneriler": ["2", "3", "4", "6", "8"]},
            {"anahtar": "satir_sayisi",
             "etiket": {"tr": "Kayıt satır sayısı", "en": "Log line count"},
             "tur": "sayi", "min": 40, "max": 3000, "varsayilan": "300",
             "oneriler": ["100", "300", "600", "1000", "2000"]},
            {"anahtar": "yakin_rakip",
             "etiket": {"tr": "Rakip saldırgan çok yakın mı? (0=hayır, 1=evet)", "en": "Close runner-up? (0=no, 1=yes)"},
             "tur": "secim", "secenekler": ["0", "1"], "varsayilan": "0"},
        ],
    },
    "loganaliz-06": {
        "baslik": {"tr": "CarotPot — Çok Hizmetli Tarama Tespiti", "en": "CarotPot — Multi-Service Scan Detection"},
        "alanlar": [
            {"anahtar": "saldirgan_sayisi",
             "etiket": {"tr": "Kaynak sayısı", "en": "Source count"},
             "tur": "sayi", "min": 2, "max": 8, "varsayilan": "5",
             "oneriler": ["3", "4", "5", "6", "7"]},
            {"anahtar": "taranan_hizmet",
             "etiket": {"tr": "Tarayıcının dokunduğu hizmet sayısı", "en": "Services touched by the scanner"},
             "tur": "sayi", "min": 3, "max": 8, "varsayilan": "4",
             "oneriler": ["3", "4", "5", "6", "7"]},
            {"anahtar": "satir_sayisi",
             "etiket": {"tr": "Kayıt satır sayısı", "en": "Log line count"},
             "tur": "sayi", "min": 40, "max": 3000, "varsayilan": "300",
             "oneriler": ["100", "300", "600", "1000", "2000"]},
            {"anahtar": "cok_olayli_rakip",
             "etiket": {"tr": "Olay sayısıyla yanıltan rakip olsun mu? (0/1)", "en": "Decoy with many events? (0/1)"},
             "tur": "secim", "secenekler": ["0", "1"], "varsayilan": "1"},
        ],
    },
    "kodlama-01": {
        "baslik": {"tr": "base64 — Çok Katmanlı Kodlama Çözme", "en": "base64 — Multi-Layer Decoding"},
        # Kodlama zinciri artık varyanttan gelir (aşağıdaki "varyant" alanı).
        "alanlar": [],
    },
    "kodlama-02": {
        "baslik": {"tr": "tr — Sezar Şifresi", "en": "tr — Caesar Cipher"},
        # Şifre türü artık varyanttan gelir (aşağıdaki "varyant" alanı).
        "alanlar": [],
    },
    "adli-01": {
        "baslik": {"tr": "file — Dosya Türü Doğrulama", "en": "file — File Type Verification"},
        "alanlar": [
            {"anahtar": "gizleme",
             "etiket": {"tr": "Gizleme yöntemi", "en": "Hiding method"},
             "tur": "secim", "secenekler": ["strings", "gzip", "tar"], "varsayilan": "gzip"},
        ],
    },
    "hash-02": {
        "baslik": {"tr": "hash — Hash Türü Tanıma", "en": "hash — Hash Type Identification"},
        "alanlar": [
            {"anahtar": "cesit",
             "etiket": {"tr": "Hash çeşitleri", "en": "Hash families"},
             "tur": "secim", "secenekler": ["temel", "unix", "karma"], "varsayilan": "temel"},
            {"anahtar": "kullanici_sayisi",
             "etiket": {"tr": "Satır (kullanıcı) sayısı", "en": "Row (user) count"},
             "tur": "sayi", "min": 1, "max": 10, "varsayilan": "4",
             "oneriler": ["1", "2", "4", "6", "10"]},
        ],
    },
    "web-01": {
        "baslik": {"tr": "curl — Gizli Dizin Keşfi", "en": "curl — Hidden Directory Discovery"},
        "alanlar": [
            {"anahtar": "kesif",
             "etiket": {"tr": "Keşif türü", "en": "Discovery type"},
             "tur": "secim", "secenekler": ["robots", "sozluk", "cerez"], "varsayilan": "sozluk"},
        ],
    },
    "banner-01": {
        "baslik": {"tr": "nmap — Servis Sürümü Tespiti", "en": "nmap — Service Version Detection"},
        "alanlar": [
            {"anahtar": "port_sayisi",
             "etiket": {"tr": "Servis sayısı", "en": "Service count"},
             "tur": "sayi", "min": 3, "max": 15, "varsayilan": "8",
             "oneriler": ["4", "6", "8", "10", "12"]},
            {"anahtar": "port_araligi",
             "etiket": {"tr": "Port aralığı (alt-üst)", "en": "Port range (low-high)"},
             "tur": "aralik", "varsayilan": "24000-24299"},
            {"anahtar": "mod",
             "etiket": {"tr": "Başlık ne zaman gelsin?", "en": "When does the banner arrive?"},
             "tur": "secim", "secenekler": ["hemen", "istek"], "varsayilan": "hemen"},
        ],
    },
    "carotpot-01": {
        "baslik": {"tr": "CarotPot — Honeypot Tetikleme", "en": "CarotPot — Triggering a Honeypot"},
        "alanlar": [
            {"anahtar": "hizmetler",
             "etiket": {"tr": "Açılacak tuzaklar", "en": "Traps to open"},
             "tur": "secim", "secenekler": ["ftp", "ftp,telnet", "ftp,telnet,http"], "varsayilan": "ftp,telnet", "liste": True},
            {"anahtar": "tuzak_port_araligi",
             "etiket": {"tr": "Tuzak port aralığı (alt-üst)", "en": "Trap port range (low-high)"},
             "tur": "aralik", "varsayilan": "21000-21999"},
            {"anahtar": "gerekli_giris",
             "etiket": {"tr": "Tuzak başına giriş denemesi", "en": "Login attempts per trap"},
             "tur": "sayi", "min": 1, "max": 20, "varsayilan": "2",
             "oneriler": ["1", "2", "3", "5", "10"]},
        ],
    },
    "carotpot-02": {
        "baslik": {"tr": "CarotPot — Honeypot Raporu Okuma", "en": "CarotPot — Reading a Honeypot Report"},
        "alanlar": [
            {"anahtar": "saldirgan_sayisi",
             "etiket": {"tr": "Saldırgan sayısı", "en": "Attacker count"},
             "tur": "sayi", "min": 2, "max": 6, "varsayilan": "4",
             "oneriler": ["2", "3", "4", "5", "6"]},
            {"anahtar": "hizmetler",
             "etiket": {"tr": "Açılacak tuzaklar", "en": "Traps to open"},
             "tur": "secim", "secenekler": ["ftp", "ftp,telnet", "ftp,telnet,http"], "varsayilan": "ftp,telnet", "liste": True},
            {"anahtar": "en_cok_deneme",
             "etiket": {"tr": "En çok deneme yapanın sayısı", "en": "Attempts by the top source"},
             "tur": "sayi", "min": 5, "max": 30, "varsayilan": "10",
             "oneriler": ["6", "8", "10", "14", "20"]},
        ],
    },
}


def _varyant_alanlarini_ekle() -> None:
    """Birden çok soru varyantı olan her şablona "varyant" alanı ekler
    (0 = bilgisayar seçsin). Alan, parametre olarak değil atama seçeneği olarak
    kullanılır: öğretmen sunucusu onu ayıklayıp tüm sınıfa duyurur."""
    import varyantlar
    for gorev_id, sablon in SABLONLAR.items():
        n = varyantlar.gorev_varyant_sayisi(gorev_id)
        if n < 2 or any(a["anahtar"] == "varyant" for a in sablon["alanlar"]):
            continue
        sablon["alanlar"].append({
            "anahtar": "varyant",
            "etiket": {"tr": f"Soru varyantı (0=bilgisayar seçsin, 1-{n})",
                       "en": f"Question variant (0=computer picks, 1-{n})"},
            "tur": "sayi", "min": 0, "max": n, "varsayilan": "0",
            "oneriler": ["0", "1", "2", "3", "4"],
        })


_varyant_alanlarini_ekle()


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
            # "liste": secenek "ftp,telnet" gibi virgullu degerse listeye cevrilir
            sonuc[anahtar] = ham.split(",") if alan.get("liste") else ham
    return sonuc


def etiket_uret(gorev_id: str, parametreler: dict) -> str:
    """Atanan ozel soruyu ozetleyen kisa etiket (ogretmen panelinde ve
    ogrenci basliginda degil, sadece durum metninde kullanilir)."""
    parcalar = []
    for alan in SABLONLAR.get(gorev_id, {}).get("alanlar", []):
        a = alan["anahtar"]
        if a == "varyant":
            continue
        if a in parametreler:
            d = parametreler[a]
            if isinstance(d, list):
                d = ",".join(map(str, d)) if d and isinstance(d[0], str) else f"{d[0]}-{d[1]}"
            parcalar.append(f"{alan['etiket']['tr']}={d}")
    return ", ".join(parcalar)
