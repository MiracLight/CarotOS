"""
Otomatik görev geçişi mekanizmasını test eder: öğrenci gorev_degisti_mi()
ile öğretmenin görevi değiştirdiğini fark edip gorevi_degistir() ile
otomatik geçiş yapabiliyor mu?
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402
from ogrenci_istemci import PoligonIstemci  # noqa: E402


def main():
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac("hydra-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", 8649)
    time.sleep(0.3)

    try:
        ogrenci = PoligonIstemci("http://127.0.0.1:8649", kod, sifre, "test")
        acik = ogrenci.acik_gorevleri_getir()
        gorev = ogrenci.gorevi_yukle(acik[0])
        ogrenci.gorevi_baslat()
        print(f"[ÖĞRENCİ] hydra-01 ile başladı, port: {ogrenci.gercek_port}")

        degisim_yok = ogrenci.gorev_degisti_mi()
        print(f"[TEST] Değişiklik yokken gorev_degisti_mi(): {degisim_yok}")
        assert degisim_yok is None, "değişiklik olmadan da 'değişti' dedi"
        print("✓ Değişiklik olmadığında None dönüyor")

        print("\n[ÖĞRETMEN] Görevi nmap-01'e değiştiriyor...")
        oda.gorev_kapat("hydra-01")
        oda.gorev_ac("nmap-01")

        yeni_gorev_id = ogrenci.gorev_degisti_mi()
        print(f"[TEST] Şimdi gorev_degisti_mi(): {yeni_gorev_id}")
        assert yeni_gorev_id == "nmap-01"
        print("✓ Değişiklik doğru şekilde algılandı")

        eski_servis = ogrenci._servis
        yeni_gorev = ogrenci.gorevi_degistir(yeni_gorev_id)
        print(f"[ÖĞRENCİ] Yeni göreve geçti: {yeni_gorev['id']} ({yeni_gorev['arac']})")
        assert yeni_gorev["id"] == "nmap-01"
        assert ogrenci._servis is not eski_servis, "eski servis hâlâ kullanılıyor"
        print("✓ Eski servis durduruldu, yeni servis başlatıldı")

        # Yeni görevi gerçekten çözebiliyor mu?
        import subprocess
        r = subprocess.run(
            ["nmap", "-p", "20-25,25,110,143,3306,20000-20999", "-T4", "127.0.0.1"],
            capture_output=True, text=True, timeout=60,
        )
        import re
        bulunan = None
        for satir in r.stdout.splitlines():
            m = re.match(r"(\d+)/tcp\s+open\s+unknown", satir)
            if m:
                bulunan = m.group(1)
        print(f"[ÖĞRENCİ] nmap ile bulunan port: {bulunan}")
        assert ogrenci.cevabi_kontrol_et(bulunan)
        print("✓ Otomatik geçiş sonrası yeni görev gerçekten çözülebiliyor")

        ogrenci.gorevi_durdur()
        print("\n" + "=" * 70)
        print("✓ OTOMATİK GÖREV GEÇİŞİ TAM ÇALIŞIYOR")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
