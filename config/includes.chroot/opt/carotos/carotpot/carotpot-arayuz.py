#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CarotPot 2 arayuzu (giris noktasi).

Moduller:
  arayuz/veri.py       veri katmani (GTK'siz)
  arayuz/metinler.py   Turkce/Ingilizce metinler
  arayuz/pencere.py    ana pencere (ortak/tema.py kabugu)
  arayuz/sayfalar/     Pano, Saldirganlar, Tuzaklar, Kanarya, Engelleme,
                       Raporlar, Ag haritasi, Ayarlar

Yetki gereken her islem carotpot-yonet yardimcisina pkexec ile, sabit
komutlarla yapilir (karar D8: engelleme onaylidir).
"""

import os
import sys

sys.dont_write_bytecode = True

BURASI = os.path.dirname(os.path.abspath(__file__))
ORTAK = os.path.join(os.path.dirname(BURASI), "ortak")
for yol in (ORTAK, BURASI):
    if yol not in sys.path:
        sys.path.insert(0, yol)

import carotpot as CP  # noqa: E402,F401
from arayuz.metinler import M as METIN  # noqa: E402,F401
from arayuz.veri import (engelli_ipler, kaynak_ozeti, olaylari_oku,  # noqa: E402,F401
                         otomatik_acik_mi, yardimci_cagir)
import arayuz.veri as _veri  # noqa: E402

subprocess = _veri.subprocess   # testler sahte subprocess.run koyabilsin


def logo_bul():
    kok = os.path.abspath(os.path.join(BURASI, "..", "..", ".."))
    for yol in (os.path.join(kok, "usr/share/icons/hicolor/256x256/apps/carotpot.png"),
                "/usr/share/icons/hicolor/256x256/apps/carotpot.png"):
        if os.path.isfile(yol):
            return yol
    return None


def arayuz_calistir(dongu=True):
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    from arayuz.pencere import Pencere
    pencere = Pencere(logo_bul())
    if dongu:
        Gtk.main()
    return pencere


if __name__ == "__main__":
    arayuz_calistir()
