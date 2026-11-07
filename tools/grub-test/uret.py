#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS GRUB temasi gorsellerini uretir (Pillow gerekir; yalnizca gelistirici makinesinde, VM'de gerekmez).

Cikti: tools/grub-test/tema/{background,select_c,select_w,select_e}.png
Minimal tema: logo yok, notr mavi tonlar (kullanici karari, 7 Kasim). Zemin neredeyse duz, cok hafif gradyan.
Kullanim:  python tools/grub-test/uret.py
"""
import os

from PIL import Image, ImageDraw

BURASI = os.path.dirname(os.path.abspath(__file__))
TEMA = os.path.join(BURASI, "tema")

UST, ALT = (16, 26, 38), (26, 42, 62)          # zemin: koyu notr mavi-gri gradyani
VURGU = (58, 95, 143, 255)                      # secili satir: sakin mavi


def arka_plan(w=1920, h=1080):
    im = Image.new("RGB", (w, h))
    px = ImageDraw.Draw(im)
    for y in range(h):
        t = y / (h - 1)
        px.line([(0, y), (w, y)], fill=tuple(int(UST[i] + (ALT[i] - UST[i]) * t) for i in range(3)))
    im.save(os.path.join(TEMA, "background.png"), optimize=True)


def secim(h=36, r=8, kenar=10):
    """9 dilimli secili-satir cercevesi: select_c (orta), select_w (sol uc), select_e (sag uc)."""
    tam = Image.new("RGBA", (kenar * 2 + 8, h), (0, 0, 0, 0))
    ImageDraw.Draw(tam).rounded_rectangle([0, 0, tam.width - 1, h - 1], radius=r, fill=VURGU)
    tam.crop((0, 0, kenar, h)).save(os.path.join(TEMA, "select_w.png"))
    tam.crop((tam.width - kenar, 0, tam.width, h)).save(os.path.join(TEMA, "select_e.png"))
    Image.new("RGBA", (4, h), VURGU).save(os.path.join(TEMA, "select_c.png"))


if __name__ == "__main__":
    os.makedirs(TEMA, exist_ok=True)
    arka_plan()
    secim()
    for ad in ("background.png", "select_c.png", "select_w.png", "select_e.png"):
        print(ad, os.path.getsize(os.path.join(TEMA, ad)), "bayt")
