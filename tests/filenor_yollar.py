# -*- coding: utf-8 -*-
"""Test yardimcisi: Filenor kodunun yerini bulur ve sys.path'e ekler.

Iki duzeni de bilir:
  * CarotOS agaci:  config/includes.chroot/opt/carotos/{filenor,ortak}
  * Bagimsiz depo:  filenor/   (tema.py de burada)
"""
import os
import sys

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CAROT = os.path.join(KOK, "config/includes.chroot/opt/carotos")
if os.path.isdir(os.path.join(_CAROT, "filenor")):
    FN = os.path.join(_CAROT, "filenor")
    ORTAK = os.path.join(_CAROT, "ortak")
    DESKTOP = os.path.join(KOK, "config/includes.chroot/usr/share/applications/carotos-filenor.desktop")
else:
    FN = os.path.join(KOK, "filenor")
    ORTAK = FN
    DESKTOP = os.path.join(KOK, "packaging/linux/filenor.desktop")
for _y in (ORTAK, FN):
    if _y not in sys.path:
        sys.path.insert(0, _y)
