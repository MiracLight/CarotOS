"""
CarotOS Poligon — sahte giris servisi.

Neden FTP el sikismasi: gercek SSH protokolu (anahtar degisimi, sifreleme)
taklit etmek karmasik ve kirilgan olurdu. FTP'nin kimlik dogrulama kismi
duz metin ve uc satirlik: sunucu banner yollar, istemci USER yollar,
sunucu 331 doner, istemci PASS yollar, sunucu 230 (basarili) ya da 530
(basarisiz) doner. Hydra'nin 'ftp' modulu bunu native destekliyor.

Ogrenciye gosterilen senaryo metninde protokol adi gecmiyor, sadece
"giris servisi" deniyor -- gercek FTP dosya transferi yok, sadece
kimlik dogrulama el sikismasi taklit ediliyor.

DOGRULAMA MODELI: Bu servis kendi basari durumunu hicbir yere yazmiyor.
Motor odayi acarken parolayi zaten kendisi uretti ve bu servise verdi;
ogrenci hydra ile parolayi bulup uygulamaya yazinca, motor sadece
kendi urettigi parolayla karsilastiriyor. Servis ile motor arasinda
ekstra bir IPC kanali gerekmiyor.
"""

from __future__ import annotations

import socket
import threading


class SahteGirisServisi:
    """127.0.0.1 disina ASLA baglanmayan, tek kullanicili sahte giris servisi."""

    def __init__(self, kullanici: str, parola: str, port: int, bind_adres: str = "127.0.0.1"):
        if bind_adres != "127.0.0.1":
            # Modul seviyesinde de zorunlu kilinir -- gorev JSON'undaki
            # kural burada ikinci kez, kod seviyesinde uygulanir.
            raise ValueError(
                f"GUVENLIK IHLALI: bind_adres '{bind_adres}' -- sadece "
                "127.0.0.1 kabul edilir."
            )
        self.kullanici = kullanici
        self.parola = parola
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
                # kendine sahte bir baglanti acip accept() cagrisini uyandir
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
            conn.settimeout(10)
            conn.sendall(b"220 CarotOS Egitim Servisi\r\n")
            girilen_kullanici = None
            arabellek = b""
            while True:
                veri = conn.recv(256)
                if not veri:
                    break
                arabellek += veri
                if b"\r\n" not in arabellek and b"\n" not in arabellek:
                    continue
                satir = arabellek.decode("utf-8", errors="ignore").strip()
                arabellek = b""

                ust = satir.upper()
                if ust.startswith("USER"):
                    girilen_kullanici = satir[4:].strip()
                    conn.sendall(b"331 Parola gerekli\r\n")
                elif ust.startswith("PASS"):
                    girilen_parola = satir[4:].strip()
                    if (
                        girilen_kullanici == self.kullanici
                        and girilen_parola == self.parola
                    ):
                        conn.sendall(b"230 Giris basarili\r\n")
                    else:
                        conn.sendall(b"530 Giris basarisiz\r\n")
                elif ust.startswith("QUIT"):
                    conn.sendall(b"221 Bye\r\n")
                    break
                else:
                    conn.sendall(b"502 Desteklenmiyor\r\n")
        except (OSError, socket.timeout):
            pass
        finally:
            conn.close()
