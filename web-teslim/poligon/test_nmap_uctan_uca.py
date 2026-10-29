"""
nmap-01 GOREVINI PoligonIstemci UZERINDEN UCTAN UCA TEST EDER.

hydra testinden farkli: burada "cevap" bir parola degil, GERCEK nmap
taramasiyla bulunan gizli port numarasi.
"""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_istemci import PoligonIstemci  # noqa: E402
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402


def nmap_ile_gizli_portu_bul() -> str | None:
    """Gerçek nmap çalıştırır, standart-dışı (unknown) portu döner."""
    sonuc = subprocess.run(
        ["nmap", "-p", "20-25,25,110,143,3306,20000-20999", "-T4", "127.0.0.1"],
        capture_output=True, text=True, timeout=60,
    )
    for satir in sonuc.stdout.splitlines():
        eslesme = re.match(r"(\d+)/tcp\s+open\s+unknown", satir)
        if eslesme:
            return eslesme.group(1)
    return None


def main():
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac("nmap-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", 8644)

    try:
        print("[ÖĞRENCİ] nmap-01 görevini yüklüyor...")
        istemci = PoligonIstemci("http://127.0.0.1:8644", kod, sifre, "nmap_ogrencisi")
        gorev = istemci.gorevi_yukle("nmap-01")
        print(f"[ÖĞRENCİ] Görev: {gorev['baslik']['tr']}")

        istemci.gorevi_baslat()
        print(f"[ÖĞRENCİ] Sahte ağ ortamı başlatıldı. Gerçek gizli port (test için biliniyor): {istemci._dogru_cevap}")

        print("\n[ÖĞRENCİ] Gerçek nmap ile 20000-20999 aralığı taranıyor...")
        bulunan = nmap_ile_gizli_portu_bul()
        print(f"[ÖĞRENCİ] nmap'in bulduğu standart-dışı port: {bulunan}")

        assert bulunan is not None, "nmap hiçbir 'unknown' port bulamadı"
        assert bulunan == istemci._dogru_cevap, (
            f"nmap'in bulduğu port ({bulunan}) motorun beklediğinden "
            f"({istemci._dogru_cevap}) farklı"
        )

        dogru = istemci.cevabi_kontrol_et(bulunan)
        assert dogru, "doğru port girildiği halde cevap yanlış sayıldı"
        print(f"\n[MOTOR] Cevap doğrulandı: {bulunan} == {istemci._dogru_cevap}")
        print(f"[MOTOR] Sonuç: ✓ GÖREV TAMAMLANDI, {gorev['puan']} puan kazanıldı")

        istemci.gorevi_durdur()

        gorunum = oda.anlik_goruntu()
        assert gorunum["ogrenciler"]["nmap_ogrencisi"]["durum"] == "tamamlandi"
        print(f"\n[ÖĞRETMEN] /durum: {gorunum['ogrenciler']}")
        print("✓ Öğretmen paneli nmap görevinin tamamlandığını doğru gördü")

        print("\n" + "=" * 70)
        print("✓ NMAP GÖREVİ UÇTAN UCA TESTİ BAŞARILI")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
