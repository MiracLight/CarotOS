# -*- coding: utf-8 -*-
"""Telnet tuzagi: giris istemi gosterir, kullanici adi ve parolayi kaydeder,
her denemeyi reddeder. IoT botlarinin (Mirai benzeri) ilk hedefidir."""

import asyncio

from . import kes

AD = "telnet"
BASLIK = "Telnet"
VARSAYILAN_PORT = 2323
ACIKLAMA = {"tr": "IoT botlarının (Mirai vb.) ilk hedefi; giriş denemeleri kaydedilir",
            "en": "First target of IoT bots (Mirai etc.); login attempts are recorded"}
PERSONALAR = {
    "kamera": {"tr": "IP kamera (BusyBox)", "en": "IP camera (BusyBox)",
               "karsilama": b"", "istem": b"IPCamera login: "},
    "modem": {"tr": "Ev modemi", "en": "Home router",
              "karsilama": b"", "istem": b"Router login: "},
    "linux": {"tr": "Linux sunucu", "en": "Linux server",
              "karsilama": b"Ubuntu 22.04.4 LTS\r\n", "istem": b"srv01 login: "},
}


def satir_coz(ham):
    """Telnet satirindan IAC muzakeresini ayiklar. Baglanti kapandiysa None."""
    if not ham:
        return None
    cikti = bytearray()
    i = 0
    while i < len(ham):
        if ham[i] == 0xFF and i + 2 < len(ham):
            i += 3
            continue
        cikti.append(ham[i])
        i += 1
    return cikti.decode("utf-8", "replace").strip("\r\n\x00 ")


async def isle(kayit, r, w, persona, zaman_asimi):
    p = PERSONALAR.get(persona) or PERSONALAR["kamera"]
    await kayit("baglanti", "Telnet baglantisi")
    w.write(b"\r\n" + p["karsilama"])
    for _ in range(3):
        w.write(b"\r\n" + p["istem"])
        await w.drain()
        kul = satir_coz(await asyncio.wait_for(r.readline(), zaman_asimi))
        if kul is None:
            return
        w.write(b"Password: ")
        await w.drain()
        par = satir_coz(await asyncio.wait_for(r.readline(), zaman_asimi))
        if par is None:
            return
        await kayit("giris", f"Telnet giris denemesi, kullanici '{kes(kul, 40)}'",
                    kullanici=kes(kul, 100), parola=kes(par, 100))
        w.write(b"\r\nLogin incorrect\r\n")
        await w.drain()
