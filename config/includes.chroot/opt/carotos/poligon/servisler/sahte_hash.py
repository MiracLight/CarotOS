"""
CarotOS Poligon -- john gorevi icin sahte hash dosyasi.

Aginizli bir servis DEGIL -- sadece yerel bir dosya. Ogrenci bu dosyayi
john ile kirip parolayi buluyor, sonra uygulamaya yaziyor.

FORMAT SECIMI: CarotOS'ta kurulu 'john' paketi "core" surumdur (jumbo
degil), bu yuzden raw-md5/raw-sha256 gibi jumbo-ozel formatlari
DESTEKLEMEZ. Core john'un desteklediginin --format=md5crypt --
klasik /etc/shadow $1$tuz$hash bicimi. Bu ayrica ogretici acidan da
dogru: gercek Linux sistemleri boyle hash tutar (moduern sistemlerde
SHA-512 kullanilir ama MD5crypt hala en cok bilinen/ogretilen bicim).

Hash uretimi Python'un crypt() modulu DEGIL, 'openssl passwd -1' ile
yapiliyor -- crypt modulu Python 3.13'te kaldirildi (PEP 594).
"""

from __future__ import annotations

import os
import secrets
import string
import subprocess
import tempfile


def _tuz_uret(uzunluk: int = 8) -> str:
    alfabe = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabe) for _ in range(uzunluk))


class SahteHashDosyasi:
    """Yerel bir hash dosyasi yazar/siler. Ag baglantisi yok, guvenlik
    kurali (127.0.0.1) bu servis icin gecerli degil -- dosya sistemi
    islemi, soket degil."""

    def __init__(self, kullanici: str, parola: str, dosya_yolu: str | None = None):
        self.kullanici = kullanici
        self.parola = parola
        self.dosya_yolu = dosya_yolu or os.path.join(
            tempfile.gettempdir(), f"carotos-poligon-john-{os.getpid()}.txt"
        )

    def baslat(self) -> None:
        tuz = _tuz_uret()
        sonuc = subprocess.run(
            ["openssl", "passwd", "-1", "-salt", tuz, self.parola],
            capture_output=True, text=True, check=True,
        )
        hash_deger = sonuc.stdout.strip()
        with open(self.dosya_yolu, "w", encoding="utf-8") as f:
            f.write(f"{self.kullanici}:{hash_deger}\n")

    def durdur(self) -> None:
        try:
            os.remove(self.dosya_yolu)
        except FileNotFoundError:
            pass
