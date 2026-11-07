#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS GRUB temasi gorsellerini uretir (Pillow gerekir; yalnizca gelistirici makinesinde, VM'de gerekmez).

Cikti: tools/grub-test/tema/{background,logo,select_c,select_w,select_e}.png
Kullanim:  python tools/grub-test/uret.py
Renkler mavi-beyaz palet (kullanici karari, 3 Kasim): lacivert zemin, acik mavi vurgu, beyaz yazi.
"""
import os

from PIL import Image, ImageDraw, ImageFilter

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(BURASI))
TEMA = os.path.join(BURASI, "tema")
LOGO = os.path.join(KOK, "config", "includes.chroot", "usr", "share", "carotos", "welcome", "logo.png")

UST, ALT = (8, 20, 40), (16, 52, 98)         # zemin gradyani (lacivert)
VURGU = (47, 127, 214, 255)                   # secili satir (acik mavi)


def arka_plan(w=1920, h=1080):
    im = Image.new("RGB", (w, h))
    px = ImageDraw.Draw(im)
    for y in range(h):
        t = y / (h - 1)
        px.line([(0, y), (w, y)], fill=tuple(int(UST[i] + (ALT[i] - UST[i]) * t) for i in range(3)))
    isik = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(isik)
    d.ellipse([w * 0.5 - 420, h * 0.22 - 260, w * 0.5 + 420, h * 0.22 + 260], fill=(60, 140, 230, 70))
    isik = isik.filter(ImageFilter.GaussianBlur(120))
    im = Image.alpha_composite(im.convert("RGBA"), isik).convert("RGB")
    im.save(os.path.join(TEMA, "background.png"), optimize=True)


def logo(boy=180):
    im = Image.open(LOGO).convert("RGBA")
    im = im.resize((boy, boy), Image.LANCZOS)
    im.save(os.path.join(TEMA, "logo.png"), optimize=True)


def secim(h=40, r=10, kenar=12):
    """9 dilimli secili-satir cercevesi: select_c (orta), select_w (sol uc), select_e (sag uc)."""
    tam = Image.new("RGBA", (kenar * 2 + 8, h), (0, 0, 0, 0))
    ImageDraw.Draw(tam).rounded_rectangle([0, 0, tam.width - 1, h - 1], radius=r, fill=VURGU)
    tam.crop((0, 0, kenar, h)).save(os.path.join(TEMA, "select_w.png"))
    tam.crop((tam.width - kenar, 0, tam.width, h)).save(os.path.join(TEMA, "select_e.png"))
    Image.new("RGBA", (4, h), VURGU).save(os.path.join(TEMA, "select_c.png"))


if __name__ == "__main__":
    os.makedirs(TEMA, exist_ok=True)
    arka_plan()
    logo()
    secim()
    for ad in sorted(os.listdir(TEMA)):
        if ad.endswith(".png"):
            print(ad, os.path.getsize(os.path.join(TEMA, ad)), "bayt")
