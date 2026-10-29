# -*- coding: utf-8 -*-
"""Former konulari. Her modul konu() ile bir konu sozlugu dondurur."""

import importlib

# Gosterim sirasi. grup: giris / araclar / uygulamalar
SIRA = ["giris", "panel", "nmap", "tcpdump", "tshark", "aircrack_ng", "nikto", "sqlmap", "john", "hydra", "ufw",
        "fail2ban", "carotpot", "carotene"]


def tumu():
    sonuc = []
    for ad in SIRA:
        m = importlib.import_module("konular." + ad)
        sonuc.append(m.konu())
    return sonuc
