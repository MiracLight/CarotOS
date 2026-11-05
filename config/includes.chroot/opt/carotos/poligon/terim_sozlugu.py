# -*- coding: utf-8 -*-
"""Poligon -- üretilen kayıt dosyalarındaki alan adları ve olay türleri, arayüz diline göre.

CarotPot kayıt biçiminde (``kaynak=… hizmet=… tur=giris | {"kullanici": …}``) alan adları Türkçe sabit
yazılıydı; İngilizce arayüzde bile ``kullanici`` / ``hedef_port`` çıkıyordu. Burada her dil için küçük
bir sözlük tutulur. Üreteç ve doğru-cevap hesabı Türkçe (kanonik) adlarla çalışmaya devam eder; sözlük
yalnızca öğrencinin gördüğü dosyaya ve ipucu komutlarına uygulanır.

Kurallar:
  * Dil, GÖREV BAŞLARKEN sabitlenir (dosya o dilde üretilir, ipucu komutları aynı adları kullanır).
    Görev sürerken arayüz dili değişirse dosya ve komutlar aynı kalır; sonraki görev yeni dille üretilir.
  * Latin harfli diller (de, es, fr, pt) kendi sözcüklerini kullanır (aksansız, kabukta yazılabilir).
    ru, ja, zh İngilizce adları kullanır: kabukta Kiril/CJK alan adı yazmak pratik değil.
  * ``tr`` kanonik adlardır: dönüşüm hiçbir şeyi değiştirmez.
GTK'siz, yalnız standart kütüphane.
"""
from __future__ import annotations

import json
import re

ANAHTARLAR = ("kaynak", "hizmet", "tur", "kullanici", "parola", "kaynak_port", "hedef_port", "ozet", "ayrinti")
DEGERLER = ("baglanti", "giris", "tarama", "istek")      # "tur" alanının değerleri (olay türleri)
SIRA = ANAHTARLAR + DEGERLER

_EN = ("source", "service", "type", "username", "password", "source_port", "target_port", "summary", "detail",
       "connection", "login", "scan", "request")

SOZLUK: dict[str, tuple[str, ...]] = {
    "tr": SIRA,
    "en": _EN,
    "de": ("quelle", "dienst", "typ", "benutzername", "passwort", "quellport", "zielport", "zusammenfassung",
           "detail", "verbindung", "anmeldung", "scan", "anfrage"),
    "es": ("origen", "servicio", "tipo", "usuario", "contrasena", "puerto_origen", "puerto_destino", "resumen",
           "detalle", "conexion", "acceso", "escaneo", "solicitud"),
    "fr": ("source", "service", "type", "utilisateur", "mot_de_passe", "port_source", "port_cible", "resume",
           "detail", "connexion", "authentification", "scan", "requete"),
    "pt": ("origem", "servico", "tipo", "usuario", "senha", "porta_origem", "porta_destino", "resumo",
           "detalhe", "conexao", "acesso", "varredura", "requisicao"),
    "ru": _EN,
    "ja": _EN,
    "zh": _EN,
}

# kanonik ad -> dildeki ad
def _harita(kod: str) -> dict[str, str]:
    return dict(zip(SIRA, SOZLUK.get(kod, _EN)))


def sozluk_kodu(kod: str | None) -> str:
    """Bilinmeyen dil İngilizce adlarını kullanır (tr kanonik)."""
    return kod if kod in SOZLUK else "en"


_ANAHTAR_RE = "|".join(sorted(ANAHTARLAR, key=len, reverse=True))     # kaynak_port, kaynak'tan önce
_DEGER_RE = "|".join(DEGERLER)


def komut_yerellestir(metin: str, kod: str | None) -> str:
    """İpucu/soru metnindeki KOMUT parçalarını dile çevirir: ``anahtar=``, ``.anahtar`` (jq),
    ``"anahtar"``, ``=değer``, ``=="değer"`` ve tek tırnaklı ``'değer'``. Düz Türkçe cümledeki
    sözcüklere (ör. "hizmet adını") dokunmaz."""
    kod = sozluk_kodu(kod)
    if kod == "tr" or not metin:
        return metin
    h = _harita(kod)
    metin = re.sub(rf"\b({_ANAHTAR_RE})=", lambda m: h[m.group(1)] + "=", metin)
    metin = re.sub(rf"\.({_ANAHTAR_RE})\b", lambda m: "." + h[m.group(1)], metin)
    metin = re.sub(rf'"({_ANAHTAR_RE})"', lambda m: '"' + h[m.group(1)] + '"', metin)
    metin = re.sub(rf'=="({_DEGER_RE})"', lambda m: '=="' + h[m.group(1)] + '"', metin)
    metin = re.sub(rf"=({_DEGER_RE})\b", lambda m: "=" + h[m.group(1)], metin)
    metin = re.sub(rf"'({_DEGER_RE})'", lambda m: "'" + h[m.group(1)] + "'", metin)
    return metin


_CP_BASLIK = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) CAROTPOT kaynak=(\S+) hizmet=(\S+) tur=(\S+) \| (.*)$")


def cp_satiri_yerellestir(satir: str, bicim: str, kod: str | None) -> str:
    """Kanonik (Türkçe adlı) bir CarotPot kayıt satırını dile çevirir; ``bicim``: "carotpot" | "jsonl"."""
    kod = sozluk_kodu(kod)
    if kod == "tr":
        return satir
    h = _harita(kod)
    if bicim == "jsonl":
        govde = json.loads(satir)
        zaman = None
    else:
        m = _CP_BASLIK.match(satir)
        if not m:
            raise ValueError(f"tanınmayan CarotPot satırı: {satir[:60]!r}")
        zaman, govde = m.group(1), json.loads(m.group(5))

    yeni = {}
    for k, v in govde.items():
        if k == "tur" and isinstance(v, str):
            v = h.get(v, v)
        elif k == "ozet" and isinstance(v, str):
            v = " ".join(h.get(parca, parca) for parca in v.split(" "))
        yeni[h.get(k, k)] = v
    js = json.dumps(yeni, ensure_ascii=False)
    if bicim == "jsonl":
        return js
    return (f"{zaman} CAROTPOT {h['kaynak']}={govde['kaynak']} {h['hizmet']}={govde['hizmet']} "
            f"{h['tur']}={h.get(govde['tur'], govde['tur'])} | {js}")


def cp_yerellestir(satirlar: list[str], bicim: str, kod: str | None) -> list[str]:
    return [cp_satiri_yerellestir(s, bicim, kod) for s in satirlar]
