# -*- coding: utf-8 -*-
"""CarotOS Poligon -- sahte servislerin olay gunlugu (savunmaci gorunumunun veri kaynagi).

Servisler (sahte_giris, sahte_ag, sahte_banner, sahte_web, sahte_savunma_hedefi) burada yalniz META VERI
yazar: hangi servis, ne tur olay, hangi port, kisa ayrinti (kullanici adi ya da URL yolu). Parola, govde ya da
baska icerik ASLA yazilmaz. Bellek icidir (halka tampon), diske hicbir sey yazilmaz, root gerekmez.

Olay turleri: baglanti, giris_basarisiz, giris_basarili, http_istek, http_404.
"""
from __future__ import annotations

import collections
import threading
import time

TURLER = ("baglanti", "giris_basarisiz", "giris_basarili", "http_istek", "http_404")
MAKS_OLAY = 500
MAKS_AYRINTI = 60


class OlayGunlugu:
    def __init__(self, kapasite: int = MAKS_OLAY, saat=time.time):
        self._olaylar: collections.deque = collections.deque(maxlen=kapasite)
        self._kilit = threading.Lock()
        self._no = 0
        self.saat = saat

    def kaydet(self, servis: str, tur: str, ayrinti: str = "", port: int = 0) -> None:
        if tur not in TURLER:
            return
        ayrinti = "".join(c for c in str(ayrinti)[:MAKS_AYRINTI] if c.isprintable())
        with self._kilit:
            self._no += 1
            self._olaylar.append({"no": self._no, "zaman": self.saat(), "servis": str(servis)[:16], "tur": tur,
                                  "ayrinti": ayrinti, "port": int(port or 0)})

    def son(self, sonra_no: int = 0, en_cok: int = 200) -> list:
        """sonra_no'dan yeni olaylar (eskiden yeniye), en fazla en_cok tane (en yeniler)."""
        with self._kilit:
            liste = [dict(o) for o in self._olaylar if o["no"] > sonra_no]
        return liste[-en_cok:]

    def temizle(self) -> None:
        with self._kilit:
            self._olaylar.clear()


GUNLUK = OlayGunlugu()
