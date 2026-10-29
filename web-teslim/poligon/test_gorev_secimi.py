"""
Ogrenci uygulamasinin ARTIK sabit "hydra-01" degil, ogretmenin actigi
GERCEK gorevi sunucudan sorup dogru yukledigini test eder.

Iki ayri senaryo: ogretmen once hydra-01 acar, sonra nmap-01 acar.
Ikisinde de ogrenci dogru gorevi almali.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402
from ogrenci_istemci import PoligonIstemci  # noqa: E402


def senaryo(gorev_id: str, port: int):
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac(gorev_id)
    sunucu = sunucu_baslat(oda, "127.0.0.1", port)

    try:
        istemci = PoligonIstemci(f"http://127.0.0.1:{port}", kod, sifre, "test")
        acik = istemci.acik_gorevleri_getir()
        print(f"[TEST] Öğretmen '{gorev_id}' açtı. Sunucudan gelen liste: {acik}")
        assert acik == [gorev_id], f"beklenen: [{gorev_id}], gelen: {acik}"

        gorev = istemci.gorevi_yukle(acik[0])
        print(f"[TEST] Öğrenci uygulaması yüklediği görev: {gorev['id']} ({gorev['arac']})")
        assert gorev["id"] == gorev_id
        print(f"✓ Doğru görev otomatik olarak seçildi: {gorev_id}\n")
    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    print("=" * 70)
    print("SENARYO 1: Öğretmen hydra-01 açtı")
    print("=" * 70)
    senaryo("hydra-01", 8650)

    print("=" * 70)
    print("SENARYO 2: Öğretmen nmap-01 açtı")
    print("=" * 70)
    senaryo("nmap-01", 8651)

    print("✓ TÜM SENARYOLAR GEÇTİ — öğrenci uygulaması artık sunucudan öğreniyor")
