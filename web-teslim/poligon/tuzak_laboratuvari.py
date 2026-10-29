"""
CarotOS Poligon -- Tuzak Laboratuvari.

Ogrencinin KENDI makinesinde, sistemdeki gercek CarotPot'tan tamamen ayri
bir CarotPot ornegi calistirir:

  * Yalniz loopback (127.0.0.0/8) adresinde dinler -- ag_guvenlik.py
    kurali; baska adres verilirse ValueError. Ag disina hicbir sey acilmaz.
  * Kendi gecici durum dizini vardir (olay veritabani, ayar, durum dosyasi);
    sistemin /var/lib/carotpot kayitlarina dokunmaz ve onlari okumaz.
  * Yalniz standart kutuphaneyle calisan tuzaklar (ftp, telnet, http) acilir.
  * Gorev bitince durdur() sureci kapatir ve gecici dizini siler.

Gorev dogrulamasi bu orneginin olay veritabanini SALT OKUNUR acarak yapilir
(olaylar() -- bkz. ogrenci_istemci.tuzak_kaydini_dogrula).
"""

from __future__ import annotations

import json
import random
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ag_guvenlik import loopback_adres_mi

# Laboratuvarda acilabilecek tuzaklar (yalniz standart kutuphane gerektirenler)
DESTEKLENEN_HIZMETLER = ("ftp", "telnet", "http")

VARSAYILAN_PORT_ARALIGI = (21000, 21999)

# opt/carotos/poligon/ -> opt/carotos/carotpot/carotpot.py
CAROTPOT_YOLU = Path(__file__).resolve().parent.parent / "carotpot" / "carotpot.py"

HAZIR_BEKLEME_SN = 10.0


class TuzakLabHatasi(RuntimeError):
    pass


def _port_bos_mu(adres: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((adres, port))
        except OSError:
            return False
    return True


class TuzakLab:
    """Ayri bir CarotPot ornegi. Baslat/durdur ve olay sorgusu saglar."""

    def __init__(self, bind_adres: str = "127.0.0.1", hizmetler=("ftp",),
                 port_araligi=VARSAYILAN_PORT_ARALIGI, carotpot_yolu=None):
        if not loopback_adres_mi(bind_adres):
            raise ValueError(
                f"Tuzak laboratuvari yalniz loopback (127.0.0.0/8) adresinde "
                f"calisir: '{bind_adres}'")
        hizmetler = tuple(hizmetler)
        if not hizmetler or set(hizmetler) - set(DESTEKLENEN_HIZMETLER):
            raise ValueError(f"gecersiz hizmet listesi: {hizmetler}")
        if len(set(hizmetler)) != len(hizmetler):
            raise ValueError("hizmet listesinde tekrar var")
        alt, ust = int(port_araligi[0]), int(port_araligi[1])
        if not (1024 <= alt <= ust <= 65535) or (ust - alt + 1) < len(hizmetler):
            raise ValueError(f"gecersiz port araligi: {port_araligi}")
        self.bind_adres = bind_adres
        self.hizmetler = hizmetler
        self.port_araligi = (alt, ust)
        self.portlar: dict[str, int] = {}
        self._yol = Path(carotpot_yolu) if carotpot_yolu else CAROTPOT_YOLU
        self._surec: subprocess.Popen | None = None
        self._dizin: Path | None = None

    # ------------------------------------------------------------------
    def _port_sec(self) -> dict[str, int]:
        alt, ust = self.port_araligi
        adaylar = list(range(alt, ust + 1))
        random.SystemRandom().shuffle(adaylar)
        secilen: dict[str, int] = {}
        for ad in self.hizmetler:
            for p in adaylar:
                if p not in secilen.values() and _port_bos_mu(self.bind_adres, p):
                    secilen[ad] = p
                    break
            else:
                raise TuzakLabHatasi("aralikta bos port kalmadi")
        return secilen

    @property
    def veritabani(self) -> Path | None:
        return self._dizin / "veri" / "olaylar.db" if self._dizin else None

    def calisiyor_mu(self) -> bool:
        return self._surec is not None and self._surec.poll() is None

    def baslat(self) -> None:
        if self.calisiyor_mu():
            return
        if not self._yol.is_file():
            raise TuzakLabHatasi(f"CarotPot bulunamadi: {self._yol}")
        self._dizin = Path(tempfile.mkdtemp(prefix="poligon-tuzak-"))
        try:
            self.portlar = self._port_sec()
            ayar = {
                "portlar": dict(self.portlar),
                "dinle": self.bind_adres,
                "sakla_gun": 1,
                "dakikada_olay": 6000,   # lab: sinir ogrenciyi engellemesin
            }
            ayar_yolu = self._dizin / "ayarlar.json"
            ayar_yolu.write_text(json.dumps(ayar), encoding="utf-8")
            durum_yolu = self._dizin / "durum.json"
            self._surec = subprocess.Popen(
                [sys.executable, str(self._yol), "run",
                 "--ayar", str(ayar_yolu),
                 "--durum-dizini", str(self._dizin / "veri"),
                 "--durum-dosyasi", str(durum_yolu),
                 "--gunluk", "",
                 "--dinle", self.bind_adres],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            self._hazir_bekle(durum_yolu)
        except BaseException:
            self.durdur()
            raise

    def _hazir_bekle(self, durum_yolu: Path) -> None:
        # Hazirlik durum dosyasindan okunur; tuzak portlarina baglanmak
        # laboratuvara bos "tarama" kaydi dusurur, bunu yapmayiz.
        bitis = time.time() + HAZIR_BEKLEME_SN
        while time.time() < bitis:
            if self._surec.poll() is not None:
                raise TuzakLabHatasi("CarotPot laboratuvari baslatilamadi")
            try:
                durum = json.loads(durum_yolu.read_text(encoding="utf-8"))
                if set(self.hizmetler) <= set(durum.get("acik", {})):
                    return
            except (OSError, ValueError):
                pass
            time.sleep(0.1)
        raise TuzakLabHatasi("CarotPot laboratuvari zamaninda hazir olmadi")

    def durdur(self) -> None:
        if self._surec is not None:
            if self._surec.poll() is None:
                self._surec.terminate()
                try:
                    self._surec.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._surec.kill()
                    self._surec.wait(timeout=3)
            self._surec = None
        if self._dizin is not None:
            shutil.rmtree(self._dizin, ignore_errors=True)
            self._dizin = None

    def __enter__(self):
        self.baslat()
        return self

    def __exit__(self, *_):
        self.durdur()

    # ------------------------------------------------------------------
    def olaylar(self, tur: str | None = "giris", kullanici: str | None = None) -> list[dict]:
        """Laboratuvar orneginin kayitlari. Veritabani SALT OKUNUR acilir."""
        yol = self.veritabani
        if yol is None or not yol.is_file():
            return []
        sorgu = ("SELECT hizmet, tur, kullanici, parola, kaynak_port, hedef_port, ts, kaynak "
                 "FROM olaylar WHERE 1=1")
        arg: list = []
        if tur is not None:
            sorgu += " AND tur = ?"
            arg.append(tur)
        if kullanici is not None:
            sorgu += " AND kullanici = ?"
            arg.append(kullanici)
        sorgu += " ORDER BY id"
        try:
            db = sqlite3.connect(f"file:{yol}?mode=ro", uri=True, timeout=2)
            try:
                satirlar = db.execute(sorgu, arg).fetchall()
            finally:
                db.close()
        except sqlite3.Error:
            return []
        anahtarlar = ("hizmet", "tur", "kullanici", "parola", "kaynak_port",
                      "hedef_port", "ts", "kaynak")
        return [dict(zip(anahtarlar, s)) for s in satirlar]
