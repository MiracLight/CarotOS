# -*- coding: utf-8 -*-
"""MySQL tuzagi: protokol 10 karsilama paketi gonderir, istemcinin giris
paketinden kullanici adini okur ve "Access denied" ile reddeder. Parola
istemcide ozetlendigi icin kaydedilmez."""

import asyncio
import os
import struct

from . import kes

AD = "mysql"
BASLIK = "MySQL"
VARSAYILAN_PORT = 3307
ACIKLAMA = {"tr": "Sahte veritabanı karşılaması; denenen kullanıcı adları kaydedilir",
            "en": "Fake database greeting; attempted usernames are recorded"}
PERSONALAR = {
    "mysql57": {"tr": "Veritabanı sunucusu (MySQL 5.7)", "en": "Database server (MySQL 5.7)",
                "surum": b"5.7.42-log"},
    "mariadb": {"tr": "MariaDB (Debian)", "en": "MariaDB (Debian)",
                "surum": b"5.5.5-10.11.6-MariaDB-0+deb12u1"},
    "mysql8": {"tr": "MySQL 8", "en": "MySQL 8", "surum": b"8.0.36"},
}

_YETENEK = 0x81FFF7FF     # PROTOCOL_41, SECURE_CONNECTION, PLUGIN_AUTH; SSL yok


def paket(sira, govde):
    return struct.pack("<I", len(govde))[:3] + bytes([sira]) + govde


def karsilama(surum, baglanti_no):
    tuz = os.urandom(20).replace(b"\0", b"\x01")
    govde = (b"\x0a" + surum + b"\0" + struct.pack("<I", baglanti_no) + tuz[:8] + b"\0" +
             struct.pack("<H", _YETENEK & 0xFFFF) + b"\x21" + struct.pack("<H", 2) +
             struct.pack("<H", _YETENEK >> 16) + bytes([21]) + b"\0" * 10 + tuz[8:] + b"\0" +
             b"mysql_native_password\0")
    return paket(0, govde)


def kullanici_coz(govde):
    """HandshakeResponse41 paketinden kullanici adi; cozulemezse None."""
    if len(govde) < 33:
        return None
    son = govde.find(b"\0", 32)
    if son < 0:
        return None
    return govde[32:son].decode("utf-8", "replace")


def red_paketi(kullanici, ip):
    mesaj = f"Access denied for user '{kullanici}'@'{ip}' (using password: YES)".encode()
    return paket(2, b"\xff" + struct.pack("<H", 1045) + b"#28000" + mesaj)


async def isle(kayit, r, w, persona, zaman_asimi):
    p = PERSONALAR.get(persona) or PERSONALAR["mysql57"]
    w.write(karsilama(p["surum"], int.from_bytes(os.urandom(2), "big") + 8))
    await w.drain()
    try:
        bas = await asyncio.wait_for(r.readexactly(4), zaman_asimi)
        uz = min(int.from_bytes(bas[:3], "little"), 4096)
        govde = await asyncio.wait_for(r.readexactly(uz), zaman_asimi)
    except (asyncio.TimeoutError, asyncio.IncompleteReadError):
        await kayit("tarama", "MySQL tuzak portuna baglanti", ayrinti="giris paketi gondermedi")
        return
    kul = kullanici_coz(govde)
    if kul is None:
        await kayit("tarama", "MySQL tuzak portuna baglanti", ayrinti="gecersiz giris paketi")
        return
    await kayit("giris", f"MySQL giris denemesi, kullanici '{kes(kul, 40)}'",
                kullanici=kes(kul, 100))
    ip = (w.get_extra_info("peername") or ("?",))[0]
    w.write(red_paketi(kes(kul, 64), ip))
    await w.drain()
