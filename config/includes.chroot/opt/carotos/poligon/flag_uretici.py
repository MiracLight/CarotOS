"""
CarotOS Poligon -- oda basina rastgele flag/parola uretici.

Oda acilirken BIR KEZ calisir, o odanin omru boyunca sabit kalir.
Farkli oda = farkli parola, bu yuzden bir sinifin cevabi baska sinifa
kopyalanamaz.

secrets modulu kullaniliyor (random degil) -- kriptografik olarak
guvenli rastgelelik, tahmin edilebilirlik riski yok.
"""

from __future__ import annotations

import secrets
from pathlib import Path

VARSAYILAN_KELIME_LISTESI = [
    "kaplumbaga", "guvenlik", "firewall", "sifreleme", "protokol",
    "yonlendirici", "anahtar", "erisim", "denetim", "izleme",
    "yetki", "dogrulama", "tarama", "kesif", "savunma",
]


def parola_uret(kelime_listesi: list[str] | None = None) -> str:
    """Rastgele bir kelime + 4 haneli sayı. Örnek: 'firewall7392'."""
    kelimeler = kelime_listesi or VARSAYILAN_KELIME_LISTESI
    kelime = secrets.choice(kelimeler)
    sayi = secrets.randbelow(9000) + 1000  # 1000-9999
    return f"{kelime}{sayi}"


def flag_uret(on_ek: str = "CAROT{", son_ek: str = "}") -> str:
    """Görev doğrulaması için CAROT{...} biçiminde flag üretir."""
    parca1 = secrets.token_hex(4)  # 8 hex karakter
    return f"{on_ek}{parca1}{son_ek}"


def kelime_listesini_dosyadan_yukle(yol: str | Path) -> list[str]:
    p = Path(yol)
    if not p.exists():
        return VARSAYILAN_KELIME_LISTESI
    satirlar = [s.strip() for s in p.read_text(encoding="utf-8").splitlines()]
    return [s for s in satirlar if s] or VARSAYILAN_KELIME_LISTESI


if __name__ == "__main__":
    # Hizli goz kontrolu: birkac ornek uret, hepsi farkli mi bak
    print("Ornek parolalar:")
    ornekler = {parola_uret() for _ in range(10)}
    for o in sorted(ornekler):
        print(" ", o)
    print(f"\n10 uretimden {len(ornekler)} tanesi benzersiz (hepsi farkli olmali)")
    assert len(ornekler) == 10, "CARPISMA: iki uretim ayni parolayi verdi"
    print("✓ carpisma yok")

    print("\nOrnek flag'ler:")
    flagler = {flag_uret() for _ in range(5)}
    for f in sorted(flagler):
        print(" ", f)
    assert len(flagler) == 5
    print("✓ carpisma yok")
