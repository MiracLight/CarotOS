"""
CarotOS Poligon -- tshark gorevi icin loopback trafik ureticisi.

Fikir: bir "gonderici" thread'i, periyodik olarak kendi makinesindeki
bir "alici" soketine baglanip flag'i duz metin olarak gonderiyor, sonra
baglantiyi kapatiyor. Bu, gercekten yakalanabilir TCP paketleri uretiyor.

Ogrenci tshark ile loopback arayuzunu (lo) dinleyip bu paketleri
yakalar, govdedeki (payload) flag'i okur. Dogrulama diger gorevlerle
ayni: ogrenci okudugu flag'i uygulamaya yazar.

ONEMLI (gercek CarotOS kurulumunda): paket yakalamak normalde root
veya 'wireshark' grubu + dumpcap yetkisi gerektirir. Bu servis SADECE
trafigi uretiyor -- yakalama izni CarotOS'un kendi paket kurulumuna
(mevcut Guvenlik Paneli'nin tshark girisiyle ayni sekilde) birakilmistir.
"""

from __future__ import annotations

from ag_guvenlik import loopback_adres_mi  # noqa: E402

import socket
import threading
import time


class SahteTrafik:
    def __init__(self, flag: str, port: int, bind_adres: str = "127.0.0.1", araik_sn: float = 0.3,
                 gurultu: int = 0, kodlama: str = "duz"):
        if not loopback_adres_mi(bind_adres):
            raise ValueError(
                f"GUVENLIK IHLALI: bind_adres '{bind_adres}' -- sadece loopback "
                "(127.0.0.0/8) kabul edilir."
            )
        self.flag = flag
        self.port = port
        self.bind_adres = bind_adres
        self.araik_sn = araik_sn
        # Zorluk: kac tane flag TASIMAYAN sahte baglanti (gurultu) uretilsin
        # ve flag payload icinde duz mu yoksa hex kodlu mu gonderilsin.
        self.gurultu = max(0, int(gurultu))
        self.kodlama = kodlama if kodlama in ("duz", "hex") else "duz"
        self._dinleyici: socket.socket | None = None
        self._calisiyor = False
        self._threadler: list[threading.Thread] = []
        self.hazir = threading.Event()

    def _flag_payload(self) -> bytes:
        """Gercek flag'i tasiyan payload. 'hex' kodlamada flag degeri
        hex'e cevrilir (ogrenci taniyip cozer); cevap yine duz metindir."""
        import time as _t
        deger = self.flag.encode("utf-8").hex() if self.kodlama == "hex" else self.flag
        return f"CAROTOS-MESAJ flag={deger} zaman={int(_t.time())}\n".encode("utf-8")

    def _gurultu_payload(self, sira: int) -> bytes:
        """flag TASIMAYAN sahte trafik -- yakalamayi kalabaliklastirir."""
        import time as _t
        return f"CAROTOS-MESAJ olay=kalp-atisi sira={sira} zaman={int(_t.time())}\n".encode("utf-8")

    def baslat(self) -> None:
        self._dinleyici = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._dinleyici.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._dinleyici.bind((self.bind_adres, self.port))
        self._dinleyici.listen(8)
        self._calisiyor = True

        t_alici = threading.Thread(target=self._alici_dongusu, daemon=True)
        t_alici.start()
        self._threadler.append(t_alici)

        t_gonderici = threading.Thread(target=self._gonderici_dongusu, daemon=True)
        t_gonderici.start()
        self._threadler.append(t_gonderici)

        # Zorluga gore gurultu gondericileri (flag tasimaz).
        for i in range(self.gurultu):
            tg = threading.Thread(target=self._gurultu_dongusu, args=(i + 1,), daemon=True)
            tg.start()
            self._threadler.append(tg)

        self.hazir.set()

    def bekle_hazir(self, zaman_asimi: float = 3.0) -> bool:
        return self.hazir.wait(timeout=zaman_asimi)

    def durdur(self) -> None:
        self._calisiyor = False
        if self._dinleyici:
            try:
                self._dinleyici.close()
            except OSError:
                pass

    def _alici_dongusu(self) -> None:
        while self._calisiyor:
            try:
                conn, _ = self._dinleyici.accept()
                conn.recv(1024)
                conn.close()
            except OSError:
                break

    def _gonderici_dongusu(self) -> None:
        # Gercek flag'i tasiyan baglanti (duz ya da hex kodlu payload).
        while self._calisiyor:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect((self.bind_adres, self.port))
                s.sendall(self._flag_payload())
                s.close()
            except OSError:
                pass
            time.sleep(self.araik_sn)

    def _gurultu_dongusu(self, sira: int) -> None:
        # flag TASIMAYAN sahte trafik -- yakalamayi kalabaliklastirir,
        # ogrenci flag= satirini ayirt etmek zorunda kalir.
        while self._calisiyor:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect((self.bind_adres, self.port))
                s.sendall(self._gurultu_payload(sira))
                s.close()
            except OSError:
                pass
            time.sleep(self.araik_sn)
