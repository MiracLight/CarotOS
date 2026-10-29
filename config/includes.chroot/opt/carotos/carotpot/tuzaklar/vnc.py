# -*- coding: utf-8 -*-
"""VNC tuzagi: RFB el sikismasinin ilk satirini gosterir ve baglantiyi
kaydeder."""

import asyncio

from . import kes

AD = "vnc"
BASLIK = "VNC"
VARSAYILAN_PORT = 5900
ACIKLAMA = {"tr": "Uzak masaüstü el sıkışması; bağlanan istemci kaydedilir",
            "en": "Remote desktop handshake; the connecting client is recorded"}
PERSONALAR = {
    "masaustu": {"tr": "Uzak masaüstü", "en": "Remote desktop", "karsilama": b"RFB 003.008\n"},
    "eski": {"tr": "Eski VNC sunucusu", "en": "Legacy VNC server", "karsilama": b"RFB 003.003\n"},
}


async def isle(kayit, r, w, persona, zaman_asimi):
    p = PERSONALAR.get(persona) or PERSONALAR["masaustu"]
    w.write(p["karsilama"])
    await w.drain()
    try:
        ham = await asyncio.wait_for(r.read(64), 3.0)
    except asyncio.TimeoutError:
        ham = b""
    if ham.startswith(b"RFB "):
        await kayit("baglanti", "VNC baglantisi",
                    ayrinti=f"istemci {kes(ham[:12].decode('latin-1').strip(), 20)}")
    else:
        await kayit("tarama", "VNC tuzak portuna baglanti",
                    ayrinti=(f"ilk bayt: {kes(ham[:48].decode('latin-1'), 60)!r}" if ham
                             else "veri gondermedi"))
