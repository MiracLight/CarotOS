# -*- coding: utf-8 -*-
"""CarotOS Poligon CTF -- ogrenci tarafi istemci (GTK'siz).

Yalnizca ogretmen sunucusuyla konusur; dogrulama ve puan SUNUCUDA. Bu sinif hicbir yerde bayrak uretmez ya da
saklamaz. Ag hatasinda istisna firlatmaz, {"hata": "baglanti"} doner (arayuz kendi dilinde gosterir).
"""
from __future__ import annotations

import urllib.parse

from ogrenci_istemci import BaglantiHatasi, PoligonIstemci

HATA_BAGLANTI = "baglanti"
HATA_BIREYSEL = "bireysel"          # CTF yalnizca sinif modunda vardir


class CtfIstemci:
    def __init__(self, istemci: PoligonIstemci):
        self._i = istemci

    @property
    def kullanilabilir(self) -> bool:
        return not self._i.bireysel_mod

    def _sorgu(self, yol: str, **ek) -> dict:
        if not self.kullanilabilir:
            return {"hata": HATA_BIREYSEL}
        q = urllib.parse.urlencode({"ogrenci": self._i.ogrenci_adi, "sifre": self._i.oda_sifre, **ek})
        try:
            kod, govde = self._i._istek("%s?%s" % (yol, q), {}, "GET")
        except BaglantiHatasi:
            return {"hata": HATA_BAGLANTI}
        return govde if isinstance(govde, dict) else {"hata": "gecersiz_yanit"}

    def _gonder(self, yol: str, **ek) -> dict:
        if not self.kullanilabilir:
            return {"hata": HATA_BIREYSEL}
        try:
            kod, govde = self._i._istek(yol, {"ogrenci": self._i.ogrenci_adi, "sifre": self._i.oda_sifre, **ek})
        except BaglantiHatasi:
            return {"hata": HATA_BAGLANTI}
        return govde if isinstance(govde, dict) else {"hata": "gecersiz_yanit"}

    def durum(self) -> dict:
        return self._sorgu("/ctf/durum")

    def dosya(self, gorev_id: str) -> dict:
        return self._sorgu("/ctf/dosya", gorev=gorev_id)

    def skor(self) -> dict:
        return self._sorgu("/ctf/skor")

    def bayrak_gonder(self, gorev_id: str, bayrak: str) -> dict:
        return self._gonder("/ctf/gonder", gorev=gorev_id, bayrak=bayrak)

    def ipucu_al(self, gorev_id: str, no: int) -> dict:
        return self._gonder("/ctf/ipucu", gorev=gorev_id, no=no)
