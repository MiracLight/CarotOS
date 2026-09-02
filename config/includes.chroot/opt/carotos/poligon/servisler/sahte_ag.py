"""
CarotOS Poligon -- nmap gorevi icin sahte ag ortami.

Fikir: birkac "gurultu" portu (yaygin, taramada normal gorunen) ve
BIR "gizli" port acilir. Ogrenci nmap ile 127.0.0.1'i tarar, hangi
portlarin acik oldugunu gorur, GIZLI portu (rastgele secilen, standart
olmayan bir port) bulup cevap olarak yazar.

Butun portlar sadece dinler, gercek bir servis sunmaz -- amac sadece
nmap'in TCP connect/SYN taramasinda "acik" olarak gorunmeleri.
"""

from __future__ import annotations

import secrets
import socket
import threading

# Gercekci gurultu: yaygin bilinen portlar, ogrenci bunlari "normal"
# sayip gecmeli, asil odaklanmasi gereken RASTGELE gizli port.
GURULTU_PORTLARI = [21, 25, 110, 143, 3306]


class SahteAgOrtami:
    """127.0.0.1 disina ASLA baglanmayan cok portlu dinleyici seti."""

    def __init__(self, bind_adres: str = "127.0.0.1", gizli_port_araligi=(20000, 20999)):
        if bind_adres != "127.0.0.1":
            raise ValueError(
                f"GUVENLIK IHLALI: bind_adres '{bind_adres}' -- sadece "
                "127.0.0.1 kabul edilir."
            )
        self.bind_adres = bind_adres
        self.gizli_port = secrets.randbelow(
            gizli_port_araligi[1] - gizli_port_araligi[0]
        ) + gizli_port_araligi[0]
        self._soketler: list[socket.socket] = []
        self._threadler: list[threading.Thread] = []
        self._calisiyor = False
        self.hazir = threading.Event()  # tüm soketler bağlanınca set edilir

    def baslat(self) -> None:
        self._calisiyor = True
        for port in GURULTU_PORTLARI + [self.gizli_port]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.bind_adres, port))
                s.listen(4)
                self._soketler.append(s)
                t = threading.Thread(target=self._dinle, args=(s,), daemon=True)
                t.start()
                self._threadler.append(t)
            except OSError:
                # port zaten kullanımda olabilir (nadiren) -- o portu atla,
                # gürültü listesinde birkaç port eksik olması görevi bozmaz
                continue
        # Gizli port dahil tüm soketler bağlandıktan SONRA hazır say.
        # Bu olmadan, çağıran taraf nmap'i servis tam ayağa kalkmadan
        # çalıştırabilir -- bu tam olarak yaşadığımız yarış durumuydu.
        self.hazir.set()

    def bekle_hazir(self, zaman_asimi: float = 3.0) -> bool:
        """Servis tam olarak ayağa kalkana kadar bekler. Testlerde ve
        gerçek istemcide nmap/tarayıcıyı çalıştırmadan önce çağrılmalı."""
        return self.hazir.wait(timeout=zaman_asimi)

    def durdur(self) -> None:
        self._calisiyor = False
        for s in self._soketler:
            try:
                s.close()
            except OSError:
                pass

    def _dinle(self, soket: socket.socket) -> None:
        while self._calisiyor:
            try:
                conn, _ = soket.accept()
                conn.close()  # bağlantıyı kabul et, hiçbir şey yapma, kapat
            except OSError:
                break
