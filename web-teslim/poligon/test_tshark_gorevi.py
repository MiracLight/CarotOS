"""
sahte_trafik.py'yi GERCEK tshark ile test eder.
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from servisler.sahte_trafik import SahteTrafik  # noqa: E402

PORT = 15900
FLAG = "carotflag2288"


def main():
    trafik = SahteTrafik(FLAG, PORT, araik_sn=0.2)
    trafik.baslat()
    trafik.bekle_hazir()
    print(f"Trafik üretici port {PORT}'da çalışıyor, flag: {FLAG}")

    try:
        print("\nGerçek tshark ile 3 saniye yakalama yapılıyor...")
        komut = [
            "tshark", "-i", "lo", "-f", f"tcp port {PORT}",
            "-a", "duration:3", "-T", "fields", "-e", "tcp.payload",
        ]
        print("Komut:", " ".join(komut))
        sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=15)

        if sonuc.stderr.strip():
            print("--- tshark stderr ---")
            print(sonuc.stderr[:300])

        bulundu = False
        for satir in sonuc.stdout.splitlines():
            satir = satir.strip()
            if not satir:
                continue
            try:
                ham = bytes.fromhex(satir.replace(":", ""))
                metin = ham.decode("utf-8", errors="ignore")
                if FLAG in metin:
                    bulundu = True
                    print(f"Çözülen payload içinde flag bulundu: {metin.strip()!r}")
                    break
            except ValueError:
                continue

        print(f"\nFlag ({FLAG}) yakalanan trafikte bulundu mu: {bulundu}")

        assert bulundu, "tshark flag'i yakalayamadı"
        print("\n✓ TEST GEÇTİ: tshark gerçekten paketi yakaladı ve flag okunabildi")

    finally:
        trafik.durdur()


if __name__ == "__main__":
    main()
