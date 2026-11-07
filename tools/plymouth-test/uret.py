#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Plymouth temasi resimlerini uretir (Pillow gerekir; yalniz gelistirici makinesinde, VM'de gerekmez).

Debian 13 temasi (ceratopsian) betigini aynen kullaniriz (parola penceresi ve animasyon orada); yalniz resimler bizim:
  frill.png  1437x1441  sag altta kaplumbaga kabugundan esinli altigen deseni (Debian'in dalga sekli yerine)
  glow.png   1437x1441  desenin ustunde nabiz gibi yanip sonen isik (betik opakligini 0.3-0.9 arasinda degistirir)
  logo.png   459x95     sol altta mutevazi "CarotOS" yazisi (yazi tipi resme gomulu: initramfs'ta yazi tipi gerekmez)
  onizleme.png          betigin yerlesim formulleriyle 16:9 ve 4:3 ekranda yaklasik gorunum
Cikti: tools/plymouth-test/tema/carotos/  Kullanim:  python tools/plymouth-test/uret.py
"""
import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BURASI = os.path.dirname(os.path.abspath(__file__))
TEMA = os.path.join(BURASI, "tema", "carotos")
FRILL_BOY = (1437, 1441)
LOGO_BOY = (459, 95)
ZEMIN_UST, ZEMIN_ALT = (16, 26, 38), (26, 43, 62)            # betikteki arka plan renkleriyle ayni (0.063,0.102,0.149)/(0.102,0.169,0.243)
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


def desen(ss=2):
    """(frill RGBA, maske L): altigen kumesi; sag alt kose sabit, uzaklastikca saydamlasir."""
    W, H = FRILL_BOY[0] * ss, FRILL_BOY[1] * ss
    kat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    k = ImageDraw.Draw(kat)
    maske = Image.new("L", (W, H), 0)
    m = ImageDraw.Draw(maske)
    r = 100 * ss
    adim_x, adim_y = 1.5 * r, math.sqrt(3) * r
    merkez = (W * 0.93, H * 0.91)
    for col in range(-12, 3):
        for row in range(-12, 4):
            cx = merkez[0] + col * adim_x
            cy = merkez[1] + row * adim_y + (adim_y / 2 if col % 2 else 0)
            uzak = math.hypot((cx - merkez[0]) * 0.92, (cy - merkez[1]) * 1.0) / (1120 * ss)
            if uzak > 1.0:
                continue
            guc = (1 - uzak) ** 1.2
            dolgu = (46, 102, 168, int(60 + 150 * guc))
            if col == 0 and row == 0:
                dolgu = (60, 124, 200, 230)                # kabugun orta altigeni belirgin
            poli = altigen(cx, cy, r - 5 * ss)
            k.polygon(poli, fill=dolgu, outline=(120, 165, 215, int(70 + 120 * guc)))
            m.polygon(poli, fill=int(255 * min(1.0, 0.35 + guc)))
    return kat.resize(FRILL_BOY, Image.LANCZOS), maske.resize(FRILL_BOY, Image.LANCZOS)


def isik(maske):
    """Altigenlerin ustunde yumusak bir isik: desen maskesiyle sinirli, kose civarinda daha parlak."""
    W, H = FRILL_BOY
    g = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(g)
    d.ellipse([W * 0.45, H * 0.40, W * 1.15, H * 1.10], fill=190)
    g = g.filter(ImageFilter.GaussianBlur(120))
    alfa = ImageChops.multiply(g, maske)
    out = Image.new("RGBA", (W, H), (150, 195, 245, 0))
    out.putalpha(alfa)
    return out


def yazi_logo():
    """459x95: 'CarotOS' sola yasli, genisligi dolduracak boyda (betik %10 ekran genisligine olcekler)."""
    W, H = LOGO_BOY
    boy = 120
    while boy > 20:
        f = font(boy)
        kutu = f.getbbox("CarotOS")
        if kutu[2] - kutu[0] <= W - 6 and kutu[3] - kutu[1] <= H - 6:
            break
        boy -= 2
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((3 - kutu[0], (H - (kutu[3] - kutu[1])) // 2 - kutu[1]), "CarotOS", font=f, fill=YAZI_RENGI)
    return im


def onizleme(frill, glow, logo):
    """ceratopsian.script'teki calcfmt formulleriyle (coef=0.6, logo en cok %10 genislik) yerlestirme."""
    ceviri = []
    for (sw, sh) in ((1920, 1080), (1024, 768)):
        ekran = Image.new("RGB", (sw, sh))
        d = ImageDraw.Draw(ekran)
        for y in range(sh):
            t = y / (sh - 1)
            d.line([(0, y), (sw, y)], fill=tuple(int(ZEMIN_UST[i] + (ZEMIN_ALT[i] - ZEMIN_UST[i]) * t) for i in range(3)))
        coef = 0.6
        if sw >= sh:
            fy = int(coef * sh)
            fx = int(coef * sh * FRILL_BOY[0] / FRILL_BOY[1])
            px, py = sw - fx, sh - fy
        else:
            fx = int(coef * sw)
            fy = int(coef * sw * FRILL_BOY[1] / FRILL_BOY[0])
            px, py = sw - fx, sh - fy
        f2 = frill.resize((fx, fy), Image.LANCZOS)
        g2 = glow.resize((fx, fy), Image.LANCZOS)
        g2.putalpha(g2.getchannel("A").point(lambda a: int(a * 0.6)))              # betik 0.3-0.9 arasi nabiz atar
        ekran.paste(f2, (px, py), f2)
        ekran.paste(g2, (px, py), g2)
        lw = LOGO_BOY[0] if LOGO_BOY[0] < 0.1 * sw else int(0.1 * sw)
        lh = int(lw / LOGO_BOY[0] * LOGO_BOY[1])
        l2 = logo.resize((lw, lh), Image.LANCZOS)
        ekran.paste(l2, (int(0.01 * sw), int(0.99 * sh) - lh), l2)
        ceviri.append(ekran)
    cikti = Image.new("RGB", (1920 + 40 + 1024, 1080), (40, 40, 40))
    cikti.paste(ceviri[0], (0, 0))
    cikti.paste(ceviri[1], (1960, 0))
    cikti.save(os.path.join(BURASI, "tema", "onizleme.png"))


if __name__ == "__main__":
    os.makedirs(TEMA, exist_ok=True)
    frill, maske = desen()
    glow = isik(maske)
    logo = yazi_logo()
    frill.save(os.path.join(TEMA, "frill.png"), optimize=True)
    glow.save(os.path.join(TEMA, "glow.png"), optimize=True)
    logo.save(os.path.join(TEMA, "logo.png"), optimize=True)
    onizleme(frill, glow, logo)
    for ad in ("carotos/frill.png", "carotos/glow.png", "carotos/logo.png", "onizleme.png"):
        print(ad, os.path.getsize(os.path.join(BURASI, "tema", ad)), "bayt")
