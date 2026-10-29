# -*- coding: utf-8 -*-
"""
GSD (Genel Sistem Sozlugu) terim modullerini birlestirir.

Her kategori kendi dosyasinda bir TERIMLER listesi tutar (bkz. linux.py,
ag.py, guvenlik.py, kriptografi.py, algoritma.py, genel.py). Terim sozlugu
sunlari icerir:
    id        : benzersiz anahtar (kategoriler arasinda da benzersiz)
    baslik    : {"tr": ..., "en": ...}
    kisa      : {"tr": ..., "en": ...}   -- tek cumlelik tanim
    aciklama  : {"tr": ..., "en": ...}   -- ayrintili aciklama (bir ya da
                birden fazla paragraf, "\n\n" ile ayrilir)
    ornek     : (istege bagli) komut/kod ornegi, duz metin
    ilgili    : (istege bagli) iliskili terim id'lerinin listesi

Kategori kendisi burada (__init__.py) eklenir; tek tek terimlerde tekrar
edilmez.
"""

from . import algoritma as _algoritma
from . import ag as _ag
from . import genel as _genel
from . import guvenlik as _guvenlik
from . import kriptografi as _kriptografi
from . import linux as _linux

KATEGORILER = {
    "linux": {"ad": {"tr": "Linux ve Sistem", "en": "Linux & Systems"}, "renk": "gri"},
    "ag": {"ad": {"tr": "Ağ ve Protokoller", "en": "Networking & Protocols"}, "renk": "mavi"},
    "guvenlik": {"ad": {"tr": "Siber Güvenlik", "en": "Cybersecurity"}, "renk": "kirmizi"},
    "kriptografi": {"ad": {"tr": "Kriptografi", "en": "Cryptography"}, "renk": "vurgu"},
    "algoritma": {"ad": {"tr": "Algoritma ve Veri Yapıları", "en": "Algorithms & Data Structures"}, "renk": "sari"},
    "genel": {"ad": {"tr": "Genel Bilgisayar Bilimi", "en": "General Computer Science"}, "renk": "yesil"},
}

# Sol paneldeki kategori sirasi.
SIRA = ["linux", "ag", "guvenlik", "kriptografi", "algoritma", "genel"]

_MODULLER = {
    "linux": _linux,
    "ag": _ag,
    "guvenlik": _guvenlik,
    "kriptografi": _kriptografi,
    "algoritma": _algoritma,
    "genel": _genel,
}


def tumu():
    """Butun terimleri (kategori damgasi vurulmus) tek listede dondurur.

    Id tekrarini dogrular; CarotOS testleri bu fonksiyon uzerinden calisir."""
    sonuc = []
    gorulen = set()
    for kat in SIRA:
        for t in _MODULLER[kat].TERIMLER:
            if t["id"] in gorulen:
                raise ValueError("Yinelenen terim id: %s" % t["id"])
            gorulen.add(t["id"])
            t2 = dict(t)
            t2["kategori"] = kat
            sonuc.append(t2)
    return sonuc
