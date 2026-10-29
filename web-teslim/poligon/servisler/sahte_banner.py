"""
CarotOS Poligon -- "baslik avi" gorevi icin cok portlu sahte servisler.

Her port baglanana bir servis basligi (banner) yollar. Portlardan biri
'CarotBox/x.y.z' basligini verir; ogrenci nmap -sV ya da nc ile onu bulup
surum numarasini yazar. Yalniz loopback'te dinler (ag_guvenlik kurali).

  mod = "hemen" : baglanir baglanmaz baslik gelir.
  mod = "istek" : istemci bir satir gonderene kadar sessiz kalir.
"""

from __future__ import annotations

import socket
import threading

from ag_guvenlik import loopback_adres_mi

YEM_BASLIKLAR = (
    "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.4",
    "220 ProFTPD 1.3.7a Server (Debian) ready.",
    "220 mail.example.test ESMTP Postfix",
    "+OK Dovecot ready.",
    "* OK [CAPABILITY IMAP4rev1] Courier-IMAP ready.",
    "5.7.42-0ubuntu0.18.04.1 MySQL Community Server",
    "RFB 003.008",
    "220 (vsFTPd 3.0.5)",
    "SSH-2.0-dropbear_2022.83",
    "+PONG redis_version:7.0.11",
)


class SahteBannerOrtami:
    def __init__(self, bind_adres: str, portlar, hedef_port: int, surum: str,
                 mod: str = "hemen"):
        if not loopback_adres_mi(bind_adres):
            raise ValueError(f"SahteBannerOrtami yalniz loopback'te calisir: {bind_adres!r}")
        if mod not in ("hemen", "istek"):
            raise ValueError(f"gecersiz mod: {mod!r}")
        self.bind_adres = bind_adres
        self.portlar = list(portlar)
        self.hedef_port = hedef_port
        self.surum = surum
        self.mod = mod
        self.basliklar: dict[int, str] = {}
        self._soketler: list[socket.socket] = []
        self._parcaciklar: list[threading.Thread] = []
        self._calisiyor = False

    def _baslik_ata(self) -> None:
        yemler = list(YEM_BASLIKLAR)
        i = 0
        for p in self.portlar:
            if p == self.hedef_port:
                self.basliklar[p] = f"CarotBox/{self.surum} ready"
            else:
                self.basliklar[p] = yemler[i % len(yemler)]
                i += 1

    def _sunucu_dongusu(self, s: socket.socket, port: int) -> None:
        baslik = (self.basliklar[port] + "\r\n").encode()
        # accept() zaman asimli: durdur() cagrilinca dongu kendiliginden biter
        # ve soket gercekten kapanir (bloke accept portu acik tutardi).
        s.settimeout(0.3)
        while self._calisiyor:
            try:
                bag, _ = s.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                bag.settimeout(3)
                if self.mod == "istek":
                    try:
                        bag.recv(256)
                    except OSError:
                        continue
                bag.sendall(baslik)
            except OSError:
                pass
            finally:
                try:
                    bag.close()
                except OSError:
                    pass

    def baslat(self) -> None:
        self._baslik_ata()
        self._calisiyor = True
        try:
            for p in self.portlar:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.bind_adres, p))
                s.listen(8)
                self._soketler.append(s)
                t = threading.Thread(target=self._sunucu_dongusu, args=(s, p), daemon=True)
                t.start()
                self._parcaciklar.append(t)
        except BaseException:
            self.durdur()
            raise

    def durdur(self) -> None:
        self._calisiyor = False
        for t in self._parcaciklar:
            t.join(timeout=2)
        for s in self._soketler:
            try:
                s.close()
            except OSError:
                pass
        self._soketler = []
        self._parcaciklar = []
