# -*- coding: utf-8 -*-
"""RDP tuzagi: baglanti istegini (ve varsa istemcinin bildirdigi kullanici
adini) kaydeder."""

import asyncio
import re

from . import kes

AD = "rdp"
BASLIK = "RDP"
VARSAYILAN_PORT = 3390
ACIKLAMA = {"tr": "Uzak masaüstü bağlantı denemeleri ve istemci kullanıcı adı",
            "en": "Remote desktop connection attempts and client username"}
PERSONALAR = {
    "sunucu": {"tr": "Windows sunucu", "en": "Windows server"},
    "masaustu": {"tr": "Windows masaüstü", "en": "Windows desktop"},
}

_CEREZ = re.compile(rb"Cookie: mstshash=([^\r\n]{1,64})")


async def isle(kayit, r, w, persona, zaman_asimi):
    try:
        ham = await asyncio.wait_for(r.read(512), 3.0)
    except asyncio.TimeoutError:
        ham = b""
    bulunan = _CEREZ.search(ham)
    if bulunan:
        kul = kes(bulunan.group(1).decode("latin-1"), 100)
        await kayit("baglanti", f"RDP baglanti istegi, kullanici '{kes(kul, 40)}'",
                    kullanici=kul)
    elif ham[:1] == b"\x03":
        await kayit("baglanti", "RDP baglanti istegi")
    else:
        await kayit("tarama", "RDP tuzak portuna baglanti",
                    ayrinti=(f"ilk bayt: {kes(ham[:48].decode('latin-1'), 60)!r}" if ham
                             else "veri gondermedi"))
