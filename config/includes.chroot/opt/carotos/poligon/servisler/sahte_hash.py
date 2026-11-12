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
import shutil
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
        self._dizin: str | None = None
        if dosya_yolu is None:
            # Yalnizca bu kullanicinin erisebildigi (0700), adi tahmin edilemeyen bir gecici dizin.
            # Eskiden /tmp/carotos-poligon-john-<pid>.txt kullaniliyordu: ayni makinedeki baska bir
            # kullanici o yolu onceden olusturup gorevin acilmasini engelleyebiliyordu.
            self._dizin = tempfile.mkdtemp(prefix="carotos-poligon-john-")
            dosya_yolu = os.path.join(self._dizin, "hash.txt")
        self.dosya_yolu = dosya_yolu

    def baslat(self) -> None:
        tuz = _tuz_uret()
        # Parola komut satirinda DEGIL stdin'den verilir (komut satiri diger kullanicilara gorunur)
        sonuc = subprocess.run(
            ["openssl", "passwd", "-1", "-salt", tuz, "-stdin"],
            input=self.parola + "\n", capture_output=True, text=True, check=True,
        )
        hash_deger = sonuc.stdout.strip()
        if not hash_deger.startswith("$1$"):
            raise RuntimeError("openssl beklenen md5crypt ozetini uretmedi")
        # Sembolik bag izlenmez, dosya yalnizca sahibine acik olusur
        fd = os.open(self.dosya_yolu, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"{self.kullanici}:{hash_deger}\n")

    def durdur(self) -> None:
        try:
            os.remove(self.dosya_yolu)
        except OSError:
            pass
        if self._dizin is not None:
            shutil.rmtree(self._dizin, ignore_errors=True)
            self._dizin = None
