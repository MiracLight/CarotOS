"""
CarotOS Poligon -- savunma görevi (ufw-01) hedefi.

Diğer sahte_*.py dosyalarından FARKI: burada "kırılacak" bir protokol
yok. Bu servisin TEK işi, öğrencinin `sudo ufw deny <port>` komutunu
denemesi için ortada bir şey dinliyor olmak. Bağlanan istemciye kısa
bir banner yollar ve kapatır -- kimlik doğrulama, flag, parola YOK.

DOĞRULAMA MODELİ (ufw-01): Bu servisin çalışıp çalışmaması doğrulamaya
karışmaz. Asıl doğrulama `ogrenci_istemci.py::ufw_kuralini_dogrula()`
içinde, `sudo ufw status` çıktısı okunarak yapılır -- bkz. oradaki not.
"""

from __future__ import annotations

import socket
import threading


class BasitDinleyici:
    """127.0.0.1 dışına ASLA bağlanmayan, tamamen pasif bir TCP dinleyici."""

    def __init__(self, port: int, bind_adres: str = "127.0.0.1"):
        if bind_adres != "127.0.0.1":
            raise ValueError(
                f"GUVENLIK IHLALI: bind_adres '{bind_adres}' -- sadece "
                "127.0.0.1 kabul edilir."
            )
        self.port = port
        self.bind_adres = bind_adres
        self._soket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._calisiyor = False

    def baslat(self) -> None:
        self._soket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._soket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._soket.bind((self.bind_adres, self.port))
        self._soket.listen(8)
        self._calisiyor = True
        self._thread = threading.Thread(target=self._dinle, daemon=True)
        self._thread.start()

    def durdur(self) -> None:
        self._calisiyor = False
        if self._soket:
            try:
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(
                    (self.bind_adres, self.port)
                )
            except OSError:
                pass
            self._soket.close()

    def _dinle(self) -> None:
        while self._calisiyor:
            try:
                conn, _ = self._soket.accept()
            except OSError:
                break
            threading.Thread(target=self._istemciyi_isle, args=(conn,), daemon=True).start()

    def _istemciyi_isle(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(5)
            conn.sendall(b"CarotOS Poligon -- savunma hedefi\r\n")
        except (OSError, socket.timeout):
            pass
        finally:
            conn.close()

    def baglanti_denemesi_basarili_mi(self, zaman_asimi: float = 1.5) -> bool:
        """Kendi portuna hızlı bir bağlantı denemesi yapar. Bilgi
        amaçlıdır -- ufw-01 doğrulamasının ZORUNLU parçası DEĞİLDİR,
        çünkü loopback trafiğinin ufw tarafından engellenip
        engellenmeyeceği sisteme göre değişir (bkz. modül docstring'i
        ve devir belgesi). Sadece öğrenciye ek bir ipucu göstermek için
        kullanılır."""
        test = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test.settimeout(zaman_asimi)
        try:
            test.connect((self.bind_adres, self.port))
            return True
        except OSError:
            return False
        finally:
            test.close()
