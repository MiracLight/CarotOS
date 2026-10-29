# -*- coding: utf-8 -*-
"""FTP tuzagi: karsilama metni gosterir, USER/PASS denemelerini kaydeder ve
reddeder. Veri gondermeyen baglantilar tarama sayilir."""

import asyncio

from . import kes

AD = "ftp"
BASLIK = "FTP"
VARSAYILAN_PORT = 2121
ACIKLAMA = {"tr": "Karşılama mesajı; kullanıcı adı ve parola denemeleri kaydedilir",
            "en": "Welcome banner; username and password attempts are recorded"}
PERSONALAR = {
    "nas": {"tr": "NAS dosya sunucusu", "en": "NAS file server",
            "karsilama": b"220 NAS FTP server ready.\r\n"},
    "linux": {"tr": "Linux sunucu (vsFTPd)", "en": "Linux server (vsFTPd)",
              "karsilama": b"220 (vsFTPd 3.0.5)\r\n"},
    "yazici": {"tr": "Ağ yazıcısı", "en": "Network printer",
               "karsilama": b"220 Printer FTP service ready.\r\n"},
}


async def isle(kayit, r, w, persona, zaman_asimi):
    p = PERSONALAR.get(persona) or PERSONALAR["nas"]
    w.write(p["karsilama"])
    await w.drain()
    kullanici = None
    ilk = True
    for _ in range(8):
        try:
            ham = await asyncio.wait_for(r.readline(), 10 if ilk else zaman_asimi)
        except asyncio.TimeoutError:
            ham = b""
        if not ham:
            if ilk:
                await kayit("tarama", "FTP tuzak portuna baglanti", ayrinti="veri gondermedi")
            return
        if ilk:
            await kayit("baglanti", "FTP baglantisi")
            ilk = False
        satir = ham.decode("utf-8", "replace").strip()
        komut, _, arg = satir.partition(" ")
        komut = komut.upper()
        if komut == "USER":
            kullanici = arg
            w.write(b"331 Please specify the password.\r\n")
        elif komut == "PASS":
            await kayit("giris", f"FTP giris denemesi, kullanici '{kes(kullanici or '', 40)}'",
                        kullanici=kes(kullanici or "", 100), parola=kes(arg, 100))
            w.write(b"530 Login incorrect.\r\n")
        elif komut == "QUIT":
            w.write(b"221 Goodbye.\r\n")
            await w.drain()
            return
        else:
            w.write(b"530 Please login with USER and PASS.\r\n")
        await w.drain()
