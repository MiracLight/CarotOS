# -*- coding: utf-8 -*-
"""SSH tuzagi (asyncssh ile): parola ve anahtar denemelerini kaydeder, hepsini
reddeder. asyncssh yoksa yalnizca SSH karsilama satirini gosteren bir tuzak
calisir (karar D3)."""

import asyncio
import os
from pathlib import Path

from . import kes

try:
    import asyncssh  # type: ignore
except ImportError:
    asyncssh = None

AD = "ssh"
BASLIK = "SSH"
VARSAYILAN_PORT = 2222
ACIKLAMA = {"tr": "Sahte OpenSSH; parola ve anahtar denemeleri kaydedilir",
            "en": "Fake OpenSSH; password and key attempts are recorded"}
PERSONALAR = {
    "ubuntu": {"tr": "Ubuntu 22.04 sunucu", "en": "Ubuntu 22.04 server",
               "surum": "OpenSSH_8.9p1 Ubuntu-3ubuntu0.10"},
    "debian": {"tr": "Debian 12 sunucu", "en": "Debian 12 server",
               "surum": "OpenSSH_9.2p1 Debian-2+deb12u3"},
    "raspi": {"tr": "Raspberry Pi", "en": "Raspberry Pi",
              "surum": "OpenSSH_9.2p1 Raspbian-2+deb12u3"},
    "gomulu": {"tr": "Gömülü cihaz (Dropbear)", "en": "Embedded device (Dropbear)",
               "surum": "dropbear_2022.83"},
}


def surum(persona):
    return (PERSONALAR.get(persona) or PERSONALAR["ubuntu"])["surum"]


def sunucu_sinifi(kupu):
    class Sunucu(asyncssh.SSHServer):  # type: ignore[misc]
        def connection_made(self, conn):
            self.conn = conn
            ad = conn.get_extra_info("peername")
            self.ip, self.port = ad[0], ad[1]
            self.hport = conn.get_extra_info("sockname")[1]
            self.izin = kupu.kabul(self.ip)
            self.bildirildi = False
            if not self.izin:
                conn.close()

        def kayit(self, tur, ozet, **kw):
            asyncio.ensure_future(kupu.kaydet("ssh", self.ip, self.port, self.hport,
                                              tur, ozet, **kw))

        def begin_auth(self, username):
            if self.izin and not self.bildirildi:
                self.bildirildi = True
                istemci = kes(str(self.conn.get_extra_info("client_version") or ""), 80)
                self.kayit("baglanti", f"SSH baglantisi, istemci {istemci or 'bilinmiyor'}",
                           ayrinti=istemci)
            return True

        def password_auth_supported(self):
            return True

        def public_key_auth_supported(self):
            return True

        def validate_password(self, username, password):
            if self.izin:
                self.kayit("giris", f"SSH giris denemesi, kullanici '{kes(username, 40)}'",
                           kullanici=kes(username, 100), parola=kes(password, 100))
            return False   # her zaman reddet

        def validate_public_key(self, username, key):
            if self.izin:
                try:
                    parmak = key.get_fingerprint("sha256")
                except Exception:  # noqa: BLE001
                    parmak = "?"
                self.kayit("giris", f"SSH anahtar denemesi, kullanici '{kes(username, 40)}'",
                           kullanici=kes(username, 100), ayrinti=f"anahtar {parmak}")
            return False

    return Sunucu


async def baslat(kupu, port, veri_dizini, persona):
    """Sunucu nesnesi ve not (str ya da None) dondurur."""
    if asyncssh is None:
        sunucu = await asyncio.start_server(
            kupu.isleyici(AD, basliksiz_isle, persona), kupu.dinle, port, limit=8192)
        return sunucu, "asyncssh yok; yalniz SSH basligi"
    anahtar_yolu = Path(veri_dizini) / "ssh_host_ed25519"
    if anahtar_yolu.exists():
        anahtar = asyncssh.read_private_key(str(anahtar_yolu))
    else:
        anahtar = asyncssh.generate_private_key("ssh-ed25519")
        anahtar.write_private_key(str(anahtar_yolu))
        os.chmod(anahtar_yolu, 0o600)
    sunucu = await asyncssh.listen(
        kupu.dinle or "", port, server_factory=sunucu_sinifi(kupu), server_host_keys=[anahtar],
        server_version=surum(persona), login_timeout=kupu.ZAMAN_ASIMI)
    return sunucu, None


async def basliksiz_isle(kayit, r, w, persona, zaman_asimi):
    """asyncssh olmadan: yalniz SSH karsilama satiri."""
    w.write(f"SSH-2.0-{surum(persona)}\r\n".encode())
    await w.drain()
    try:
        ham = await asyncio.wait_for(r.read(256), 3.0)
    except asyncio.TimeoutError:
        ham = b""
    await kayit("baglanti" if ham.startswith(b"SSH-") else "tarama",
                "SSH tuzak portuna baglanti",
                ayrinti=(kes(ham[:60].decode("latin-1").strip(), 60) if ham else "veri gondermedi"))
