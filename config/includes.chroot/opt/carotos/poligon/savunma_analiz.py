# -*- coding: utf-8 -*-
"""CarotOS Poligon -- savunmaci gorunumu: olay gunlugunu bulgulara ve savunma derslerine cevirir (GTK'siz).

Saf fonksiyonlar; zaman disaridan verilir (testler gercek zaman beklemez). Hicbir sey calistirmaz, yalnizca
olay listesini okur. Sistem durumu icin tek istisna: `savunma_durumu` sabit argumanli, kabuksuz
`systemctl is-active` cagrisi yapar (root gerekmez).
"""
from __future__ import annotations

import subprocess


def T(tr, en):
    return {"tr": tr, "en": en}


# Esikler (sahte servislerin urettigi trafige gore, ogrenciye "saldiri izi" gostermek icin)
PAROLA_ESIK, PAROLA_PENCERE = 5, 30.0          # ayni servise 30 sn'de 5 basarisiz giris
PORT_ESIK, PORT_PENCERE = 6, 5.0               # 5 sn'de 6 farkli porta baglanti
WEB_ESIK, WEB_PENCERE = 12, 10.0               # 10 sn'de 12 http istegi
WEB_404_ESIK = 5                               # ... ya da 5 "bulunamadi"

TUR_AD = {
    "baglanti": T("Bağlantı", "Connection"),
    "giris_basarisiz": T("Başarısız giriş", "Failed login"),
    "giris_basarili": T("Başarılı giriş", "Successful login"),
    "http_istek": T("Web isteği", "Web request"),
    "http_404": T("Web isteği (bulunamadı)", "Web request (not found)"),
}
SERVIS_AD = {
    "giris": T("Giriş servisi", "Login service"), "ag": T("Ağ ortamı", "Network environment"),
    "banner": T("Banner servisi", "Banner service"), "web": T("Web servisi", "Web service"),
    "savunma": T("Savunma hedefi", "Defense target"),
}

BULGULAR = {
    "parola_deneme": {
        "baslik": T("Parola deneme saldırısı", "Password guessing attack"),
        "ne": T("Kısa sürede çok sayıda başarısız giriş görüldü: biri parolayı tahmin etmeye çalışıyor.",
                "Many failed logins in a short time: someone is trying to guess the password."),
        "savunma": T("Savunma: fail2ban belirli bir sayıda başarısız denemeden sonra o adresi geçici olarak engeller. "
                     "Güçlü ve uzun bir parola da saldırıyı pratikte imkânsız kılar.",
                     "Defense: fail2ban temporarily blocks an address after a number of failed attempts. "
                     "A strong, long password also makes the attack practically impossible."),
        "konu": "fail2ban", "siddet": "yuksek",
    },
    "port_tarama": {
        "baslik": T("Port taraması", "Port scan"),
        "ne": T("Kısa sürede birçok farklı porta bağlantı denendi: biri hangi servislerin açık olduğunu arıyor.",
                "Connections to many different ports in a short time: someone is looking for open services."),
        "savunma": T("Savunma: ihtiyacın olmayan portları kapat ve güvenlik duvarında (ufw) yalnızca gerekenlere izin ver. "
                     "Açık port ne kadar azsa saldırı yüzeyi o kadar küçüktür.",
                     "Defense: close ports you do not need and allow only what is required in the firewall (ufw). "
                     "The fewer open ports, the smaller the attack surface."),
        "konu": "ufw", "siddet": "orta",
    },
    "web_tarama": {
        "baslik": T("Web taraması", "Web scan"),
        "ne": T("Web servisine kısa sürede çok istek geldi ve birçoğu “bulunamadı” döndü: biri sayfaları sırayla deniyor.",
                "The web service received many requests in a short time and many returned “not found”: someone is trying pages one after another."),
        "savunma": T("Savunma: günlükleri izle, sık istek yapan adresleri sınırla ve gereksiz sayfaları kaldır. "
                     "Sunucu sürümünü gizlemek de işi zorlaştırır.",
                     "Defense: watch the logs, limit addresses that make frequent requests and remove unneeded pages. "
                     "Hiding the server version also makes it harder."),
        "konu": "fail2ban", "siddet": "orta",
    },
}


def _pencere(olaylar, simdi, sure):
    return [o for o in olaylar if simdi - o["zaman"] <= sure]


def analiz_et(olaylar: list, simdi: float) -> list:
    """Olay listesinden etkin bulgular. Her bulgu: {"tur", "adet", "servis"} + BULGULAR[tur] alanlari."""
    sonuc = []
    for servis in sorted({o["servis"] for o in olaylar}):
        ol = [o for o in olaylar if o["servis"] == servis]
        basarisiz = [o for o in _pencere(ol, simdi, PAROLA_PENCERE) if o["tur"] == "giris_basarisiz"]
        if len(basarisiz) >= PAROLA_ESIK:
            sonuc.append({"tur": "parola_deneme", "adet": len(basarisiz), "servis": servis})
        portlar = {o["port"] for o in _pencere(ol, simdi, PORT_PENCERE) if o["tur"] == "baglanti" and o["port"]}
        if len(portlar) >= PORT_ESIK:
            sonuc.append({"tur": "port_tarama", "adet": len(portlar), "servis": servis})
        web = [o for o in _pencere(ol, simdi, WEB_PENCERE) if o["tur"] in ("http_istek", "http_404")]
        bulunamadi = sum(1 for o in web if o["tur"] == "http_404")
        if len(web) >= WEB_ESIK or bulunamadi >= WEB_404_ESIK:
            sonuc.append({"tur": "web_tarama", "adet": len(web), "servis": servis})
    for b in sonuc:
        b.update({k: v for k, v in BULGULAR[b["tur"]].items()})
    return sonuc


def _aktif_mi(birim: str) -> str:
    """'aktif' | 'pasif' | 'bilinmiyor'. Sabit argumanli, kabuksuz; root gerekmez."""
    try:
        r = subprocess.run(["systemctl", "is-active", birim], capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return "bilinmiyor"
    cikti = r.stdout.strip()
    if cikti == "active":
        return "aktif"
    if cikti in ("inactive", "failed", "activating", "deactivating", "unknown"):
        return "pasif"
    return "bilinmiyor"


def savunma_durumu() -> dict:
    return {"ufw": _aktif_mi("ufw"), "fail2ban": _aktif_mi("fail2ban")}
