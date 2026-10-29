# -*- coding: utf-8 -*-
"""Redis tuzagi: parola isteyen bir Redis gibi davranir. AUTH denemelerini
ve gonderilen komutlari kaydeder; hicbir komut calistirilmaz."""

import asyncio

from . import kes

AD = "redis"
BASLIK = "Redis"
VARSAYILAN_PORT = 6380
ACIKLAMA = {"tr": "Parolalı önbellek sunucusu gibi davranır; komut ve parola denemeleri kaydedilir",
            "en": "Acts as a password-protected cache server; commands and passwords are recorded"}
PERSONALAR = {
    "onbellek": {"tr": "Önbellek sunucusu", "en": "Cache server"},
    "kuyruk": {"tr": "İş kuyruğu sunucusu", "en": "Job queue server"},
}

# Bir saldirinin parcasi olabilecek komutlar (ayrintida isaretlenir)
TEHLIKELI = {"CONFIG", "SLAVEOF", "REPLICAOF", "MODULE", "EVAL", "EVALSHA", "FLUSHALL",
             "FLUSHDB", "SAVE", "BGSAVE", "SCRIPT", "DEBUG", "SET", "CRON"}


async def komut_oku(r, zaman_asimi):
    """RESP dizisi ya da satir ici komut okur; argumanlar listesi ya da None."""
    satir = await asyncio.wait_for(r.readline(), zaman_asimi)
    if not satir:
        return None
    if satir[:1] != b"*":
        return [a.decode("utf-8", "replace") for a in satir.split()][:16]
    try:
        n = min(int(satir[1:].strip()), 16)
    except ValueError:
        return []
    arglar = []
    for _ in range(n):
        uz_satir = await asyncio.wait_for(r.readline(), zaman_asimi)
        if uz_satir[:1] != b"$":
            return arglar
        try:
            uz = min(int(uz_satir[1:].strip()), 512)
        except ValueError:
            return arglar
        veri = await asyncio.wait_for(r.readexactly(uz + 2), zaman_asimi)
        arglar.append(veri[:-2].decode("utf-8", "replace"))
    return arglar


async def isle(kayit, r, w, persona, zaman_asimi):
    ilk = True
    for _ in range(12):
        try:
            arglar = await komut_oku(r, 10 if ilk else zaman_asimi)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError):
            arglar = None
        if arglar is None:
            if ilk:
                await kayit("tarama", "Redis tuzak portuna baglanti", ayrinti="veri gondermedi")
            return
        ilk = False
        if not arglar:
            continue
        komut = arglar[0].upper()
        if komut == "AUTH":
            kul, par = (arglar[1], arglar[2]) if len(arglar) > 2 else ("default", (arglar + [""])[1])
            await kayit("giris", f"Redis AUTH denemesi, kullanici '{kes(kul, 40)}'",
                        kullanici=kes(kul, 100), parola=kes(par, 100))
            w.write(b"-WRONGPASS invalid username-password pair or user is disabled.\r\n")
        else:
            isaret = " (tehlikeli)" if komut in TEHLIKELI else ""
            await kayit("komut", f"Redis komutu: {kes(komut, 20)}{isaret}",
                        ayrinti=kes(" ".join(arglar), 160))
            if komut == "QUIT":
                w.write(b"+OK\r\n")
                await w.drain()
                return
            w.write(b"-NOAUTH Authentication required.\r\n")
        await w.drain()
