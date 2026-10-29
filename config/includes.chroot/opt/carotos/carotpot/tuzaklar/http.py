# -*- coding: utf-8 -*-
"""Sahte web yonetim paneli: istekleri ve giris formlarini kaydeder; her
giris "hatali parola" ile reddedilir."""

import asyncio
import html
import urllib.parse

from . import kes

AD = "http"
BASLIK = "Web"
VARSAYILAN_PORT = 8080
ACIKLAMA = {"tr": "Sahte yönetim sayfası; istekler ve giriş formları kaydedilir",
            "en": "Fake admin page; requests and login forms are recorded"}
PERSONALAR = {
    "modem": {"tr": "Ev modemi arayüzü", "en": "Home router interface",
              "baslik": "Ağ Geçidi Yönetimi", "sunucu": "micro_httpd", "renk": "#1d5fa8"},
    "kamera": {"tr": "IP kamera arayüzü", "en": "IP camera interface",
               "baslik": "IP Camera Web Viewer", "sunucu": "Boa/0.94.14rc21", "renk": "#333333"},
    "nas": {"tr": "NAS yönetim paneli", "en": "NAS admin panel",
            "baslik": "NAS Storage Manager", "sunucu": "nginx", "renk": "#0f7a6c"},
    "yazici": {"tr": "Ağ yazıcısı", "en": "Network printer",
               "baslik": "Printer Embedded Web Server", "sunucu": "HTTP Server", "renk": "#5b3e96"},
}

SAYFA = (
    "<!doctype html><html><meta charset=utf-8><title>{baslik}</title>"
    "<body style='font-family:sans-serif;background:#f3f3f3;margin:0'>"
    "<div style='background:{renk};color:#fff;padding:14px 24px;font-size:18px'>{baslik}</div>"
    "<div style='max-width:320px;margin:10vh auto;background:#fff;padding:24px;"
    "border:1px solid #ddd'>{mesaj}"
    "<form method=post action=/login><p><input name=username placeholder='Username' style='width:100%'>"
    "<p><input name=password type=password placeholder='Password' style='width:100%'>"
    "<p><button>Login</button></form></div></body></html>"
)


async def isle(kayit, r, w, persona, zaman_asimi):
    p = PERSONALAR.get(persona) or PERSONALAR["modem"]
    baslik = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), zaman_asimi)
    satirlar = baslik.decode("latin-1").split("\r\n")
    yontem, yol = (satirlar[0].split(" ") + ["", ""])[:2]
    basliklar = {}
    for s in satirlar[1:]:
        if ":" in s:
            k, v = s.split(":", 1)
            basliklar[k.strip().lower()] = v.strip()
    ua = kes(basliklar.get("user-agent", ""), 120)
    mesaj = ""
    if yontem == "POST":
        try:
            uz = min(int(basliklar.get("content-length", "0") or 0), 4096)
        except ValueError:
            uz = 0
        govde = await asyncio.wait_for(r.readexactly(uz), zaman_asimi) if uz > 0 else b""
        alanlar = urllib.parse.parse_qs(govde.decode("utf-8", "replace"))
        kul = (alanlar.get("username") or alanlar.get("user") or [""])[0]
        par = (alanlar.get("password") or alanlar.get("pass") or [""])[0]
        await kayit("giris", f"Web paneline giris denemesi, kullanici '{kes(kul, 40)}'",
                    kullanici=kes(kul, 100), parola=kes(par, 100),
                    ayrinti=f"{kes(yol, 80)} UA={ua}")
        mesaj = "<p style='color:#b00'>Invalid username or password.</p>"
    else:
        await kayit("istek", f"Web paneli istegi: {kes(yontem, 10)} {kes(yol, 80)}",
                    ayrinti=f"{kes(yol, 120)} UA={ua}")
    govde = SAYFA.format(baslik=html.escape(p["baslik"]), renk=p["renk"], mesaj=mesaj).encode()
    w.write(b"HTTP/1.1 200 OK\r\nServer: " + p["sunucu"].encode() +
            b"\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: " +
            str(len(govde)).encode() + b"\r\nConnection: close\r\n\r\n" + govde)
    await w.drain()
