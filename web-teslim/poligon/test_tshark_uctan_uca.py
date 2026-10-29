"""
tshark-01 GOREVINI PoligonIstemci UZERINDEN UCTAN UCA TEST EDER.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_istemci import PoligonIstemci  # noqa: E402
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402


def tshark_ile_yakala(port: int) -> str | None:
    komut = ["tshark", "-i", "lo", "-f", f"tcp port {port}",
             "-a", "duration:4", "-T", "fields", "-e", "tcp.payload"]
    sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=15)
    for satir in sonuc.stdout.splitlines():
        satir = satir.strip()
        if not satir:
            continue
        try:
            metin = bytes.fromhex(satir.replace(":", "")).decode("utf-8", errors="ignore")
        except ValueError:
            continue
        if "flag=" in metin:
            return metin.split("flag=", 1)[1].split(" ", 1)[0]
    return None


def main():
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac("tshark-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", 8647)

    try:
        istemci = PoligonIstemci("http://127.0.0.1:8647", kod, sifre, "tshark_ogrencisi")
        gorev = istemci.gorevi_yukle("tshark-01")
        print(f"[ÖĞRENCİ] Görev: {gorev['baslik']['tr']}")

        istemci.gorevi_baslat()
        port = istemci.gercek_port
        print(f"[ÖĞRENCİ] Trafik üretici port {port}'da. Gerçek flag (test için biliniyor): {istemci._dogru_cevap}")

        print("\n[ÖĞRENCİ] Gerçek tshark ile yakalanıyor...")
        bulunan = tshark_ile_yakala(port)
        print(f"[ÖĞRENCİ] Yakalanan flag: {bulunan}")

        assert bulunan == istemci._dogru_cevap
        dogru = istemci.cevabi_kontrol_et(bulunan)
        assert dogru
        print(f"\n[MOTOR] Sonuç: ✓ GÖREV TAMAMLANDI, {gorev['puan']} puan kazanıldı")

        istemci.gorevi_durdur()

        gorunum = oda.anlik_goruntu()
        assert gorunum["ogrenciler"]["tshark_ogrencisi"]["durum"] == "tamamlandi"
        print("✓ Öğretmen paneli tshark görevinin tamamlandığını doğru gördü")

        print("\n" + "=" * 70)
        print("✓ TSHARK GÖREVİ UÇTAN UCA TESTİ BAŞARILI")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
