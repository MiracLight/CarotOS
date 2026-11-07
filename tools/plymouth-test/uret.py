#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Plymouth acilis resmini uretir (Pillow gerekir; yalniz gelistirici makinesinde).

Cikti (tools/plymouth-test/tema/):
  background.png  1920x1080 notr koyu mavi zemin, sag altta kaplumbaga kabugundan esinli altigen deseni (logo yok)
  yazi.png        seffaf zeminli kucuk "CarotOS" yazisi (sol alta konur; yazi tipi resme gomulu: initramfs'ta yazi tipi gerekmez)
  onizleme.png    ikisinin 16:9 ve 4:3 ekranda nasil gorunecegi (yaklasik)
Kullanim:  python tools/plymouth-test/uret.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

BURASI = os.path.dirname(os.path.abspath(__file__))
TEMA = os.path.join(BURASI, "tema")
UST, ALT = (16, 26, 38), (26, 43, 62)
YAZI_RENGI = (143, 163, 186, 255)
FONT_ADAYLARI = (r"C:\Windows\Fonts\segoeuisl.ttf", r"C:\Windows\Fonts\segoeui.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def font(boy):
    for yol in FONT_ADAYLARI:
        if os.path.isfile(yol):
            return ImageFont.truetype(yol, boy)
    raise SystemExit("yazi tipi bulunamadi")


def altigen(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * i)), cy + r * math.sin(math.radians(60 * i))) for i in range(6)]


def arka_plan(w=1920, h=1080, ss=2):
    W, H = w * ss, h * ss
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(UST[i] + (ALT[i] - UST[i]) * t) for i in range(3)))
    kat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    k = ImageDraw.Draw(kat)
    r = 118 * ss                                   # altigen yaricapi (yassi uclu dizilim)
    adim_x, adim_y = 1.5 * r, math.sqrt(3) * r
    merkez = (W * 0.90, H * 0.88)
    for col in range(-9, 3):
        for row in range(-8, 4):
            cx = merkez[0] + col * adim_x
            cy = merkez[1] + row * adim_y + (adim_y / 2 if col % 2 else 0)
            uzak = math.hypot(cx - merkez[0], cy - merkez[1]) / (620 * ss)
            if uzak > 1.0:
                continue
            guc = (1 - uzak) ** 1.4
            dolgu = (47, 100, 160, int(20 + 85 * guc))
            if col == 0 and row == 0:
                dolgu = (52, 112, 182, 150)          # kabugun orta altigeni biraz belirgin
            k.polygon(altigen(cx, cy, r - 5 * ss), fill=dolgu, outline=(110, 150, 200, int(30 + 70 * guc)))
    im = Image.alpha_composite(im.convert("RGBA"), kat).convert("RGB")
    im = im.resize((w, h), Image.LANCZOS)
    im.save(os.path.join(TEMA, "background.png"), optimize=True)
    return im


def yazi():
    f = font(34)
    kutu = f.getbbox("CarotOS")
    w, h = kutu[2] - kutu[0] + 8, kutu[3] - kutu[1] + 16
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, 4 - kutu[1] + 4), "CarotOS", font=f, fill=YAZI_RENGI)
    im.save(os.path.join(TEMA, "yazi.png"), optimize=True)
    return im


def onizleme(bg, yz):
    """Betik mantigi: arka plan ekrani kaplayacak sekilde olceklenir (kirpilir), yazi sol alta konur."""
    cikti = Image.new("RGB", (1920 + 40 + 1024, 1080), (40, 40, 40))
    for (sw, sh, x0) in ((1920, 1080, 0), (1024, 768, 1960)):
        oran = max(sw / bg.width, sh / bg.height)
        yw, yh = int(bg.width * oran + 1), int(bg.height * oran + 1)
        b = bg.resize((yw, yh), Image.LANCZOS)
        ekran = Image.new("RGB", (sw, sh))
        ekran.paste(b, ((sw - yw) // 2, (sh - yh) // 2))
        ekran.paste(yz, (int(sw * 0.03), sh - yz.height - int(sh * 0.04)), yz)
        cikti.paste(ekran, (x0, 0))
    cikti.save(os.path.join(BURASI, "tema", "onizleme.png"))


if __name__ == "__main__":
    os.makedirs(TEMA, exist_ok=True)
    onizleme(arka_plan(), yazi())
    for ad in ("background.png", "yazi.png", "onizleme.png"):
        print(ad, os.path.getsize(os.path.join(TEMA, ad)), "bayt")
