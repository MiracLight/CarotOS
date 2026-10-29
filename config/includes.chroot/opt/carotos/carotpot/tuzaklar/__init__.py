# -*- coding: utf-8 -*-
"""
CarotPot tuzak modulleri.

Her tuzak ayri bir moduldur ve su adlari tanimlar:

  AD               ayar dosyasindaki anahtar ("ssh", "mysql"...)
  BASLIK           arayuzde gorunen ad
  VARSAYILAN_PORT  yeni kurulumda kullanilan port (0 = kapali gelir)
  ACIKLAMA         {"tr": ..., "en": ...} kisa aciklama
  PERSONALAR       {anahtar: {"tr": ad, "en": ad, ...tuzaga ozel ayarlar}}
                   ilk anahtar varsayilandir. Persona, tuzagin kendini ne
                   olarak tanittigini belirler (karsilama metni, surum...).
  async isle(kayit, okuyucu, yazici, persona, zaman_asimi)
                   bir baglantiyi isler. kayit(tur, ozet, kullanici=None,
                   parola=None, ayrinti=None) olayi yazar. Kabul denetimi,
                   eszamanlilik siniri ve baglantinin kapatilmasi cekirdekte
                   yapilir; modul yalnizca protokolu konusur.

SSH ozeldir: isle() yerine baslat(kupu, port, veri_dizini, persona) tanimlar.

Yeni bir tuzak eklemek icin: bu dizine modul yazilir ve SIRA'ya eklenir.
Moduller yalnizca standart kutuphaneyi kullanir (SSH: asyncssh, istege bagli).
"""

import importlib

def kes(metin, uzunluk=200):
    """Yazdirilamayan karakterleri temizler ve kisaltir (gunluk icin)."""
    metin = "".join(c if c.isprintable() else "?" for c in str(metin))
    return metin if len(metin) <= uzunluk else metin[:uzunluk] + "…"


SIRA = ("ssh", "http", "telnet", "ftp", "vnc", "rdp", "mysql", "redis")

MODULLER = {ad: importlib.import_module(f"{__name__}.{ad}") for ad in SIRA}


def persona_anahtarlari(ad):
    return tuple(MODULLER[ad].PERSONALAR)


def varsayilan_persona(ad):
    return persona_anahtarlari(ad)[0]
