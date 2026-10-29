"""
sahte_ag.py'yi GERCEK nmap ile tarar. Tahmin degil, olcum.
"""

import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from servisler.sahte_ag import GURULTU_PORTLARI, SahteAgOrtami  # noqa: E402


def test_nmap_gizli_portu_buluyor_mu():
    ortam = SahteAgOrtami()
    ortam.baslat()
    time.sleep(0.3)

    try:
        print(f"Gizli port (gerçekte, test için biliniyor): {ortam.gizli_port}")
        print(f"Gürültü portları: {GURULTU_PORTLARI}")

        # Öğrencinin taracağı aralık: gürültü + gizli aralığın tamamı
        port_araligi = "20-25,25,110,143,3306,20000-20999"
        komut = ["nmap", "-p", port_araligi, "-T4", "127.0.0.1"]
        print(f"\nÇalıştırılan komut: {' '.join(komut)}")
        sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=60)

        print("\n--- nmap çıktısı ---")
        print(sonuc.stdout)

        acik_portlar = [
            int(m.group(1))
            for m in re.finditer(r"(\d+)/tcp\s+open", sonuc.stdout)
        ]
        print(f"\nnmap'in açık bulduğu portlar: {sorted(acik_portlar)}")

        assert ortam.gizli_port in acik_portlar, "nmap gizli portu BULAMADI"
        print(f"✓ Gizli port ({ortam.gizli_port}) nmap tarafından bulundu")

        for gp in GURULTU_PORTLARI:
            if gp in acik_portlar:
                print(f"✓ Gürültü portu {gp} da açık görünüyor (beklenen)")

        # Öğrencinin cevabı: en yüksek/standart-olmayan portu seçmesi gerekiyor
        # (gürültü portları hepsi 1024 altı ya da bilinen servisler)
        standart_disi = [p for p in acik_portlar if p not in GURULTU_PORTLARI]
        print(f"\nStandart dışı (öğrencinin bulması gereken) portlar: {standart_disi}")
        assert standart_disi == [ortam.gizli_port], (
            "gürültü ayrımı net değil -- öğrenci gizli portu ayırt edemeyebilir"
        )
        print("✓ Gizli port, gürültüden net şekilde ayrılabiliyor")

    finally:
        ortam.durdur()


def test_guvenlik_kurali():
    try:
        SahteAgOrtami(bind_adres="0.0.0.0")
        assert False, "0.0.0.0 ile ortam oluşturulabildi!"
    except ValueError as e:
        print(f"✓ Beklenen güvenlik hatası: {e}")


if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: nmap gerçekten gizli portu buluyor mu")
    print("=" * 70)
    test_nmap_gizli_portu_buluyor_mu()

    print()
    print("=" * 70)
    print("TEST 2: güvenlik kuralı")
    print("=" * 70)
    test_guvenlik_kurali()

    print("\nTÜM TESTLER GEÇTİ")
