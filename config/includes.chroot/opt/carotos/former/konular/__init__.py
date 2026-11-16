# -*- coding: utf-8 -*-
"""Former konulari. Her modul konu() ile bir konu sozlugu dondurur."""

import importlib
import sys

# Gosterim sirasi. grup: giris / araclar / uygulamalar
SIRA = ["giris", "kur", "panel", "nmap", "tcpdump", "tshark", "aircrack_ng", "nikto", "sqlmap", "john", "hydra", "ufw",
        "fail2ban", "carotpot", "carotene", "acikla", "etik", "disk", "kurtarma", "dogrula", "ctf", "savunma"]


def tumu():
    sonuc = []
    for ad in SIRA:
        try:
            m = importlib.import_module("konular." + ad)
            sonuc.append(m.konu())
        except Exception as h:      # R-09: tek bozuk konu butun uygulamayi acilmaz kilmaz
            print("Former: '%s' konusu yuklenemedi: %r" % (ad, h), file=sys.stderr)
    return sonuc
