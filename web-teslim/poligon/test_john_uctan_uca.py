"""
john-01 GOREVINI PoligonIstemci UZERINDEN UCTAN UCA TEST EDER.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_istemci import PoligonIstemci  # noqa: E402
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402


def john_ile_kir(dosya_yolu: str, dogru_parola: str) -> str | None:
    import os as _os
    import shutil as _sh
    sahte_sozluk = ["123456", "password", dogru_parola, "qwerty", "admin"]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(sahte_sozluk) + "\n")
        sozluk_yolu = f.name
    # Core john --pot desteklemez ve potfile'ı $HOME/.john/john.pot'ta tutar.
    # Her çağrıya İZOLE bir geçici HOME vererek testler arası potfile
    # kirlenmesini tamamen önlüyoruz (art arda/toplu çalıştırmada john'un
    # "zaten kırıldı" diye atlamasının kökten çözümü).
    gecici_home = tempfile.mkdtemp(prefix="john-home-")
    ortam = dict(_os.environ, HOME=gecici_home)
    try:
        subprocess.run(["john", "--format=md5crypt", f"--wordlist={sozluk_yolu}", dosya_yolu],
                        capture_output=True, text=True, timeout=30, env=ortam)
        goster = subprocess.run(["john", "--show", "--format=md5crypt", dosya_yolu],
                                 capture_output=True, text=True, timeout=15, env=ortam)
        for satir in goster.stdout.splitlines():
            if ":" in satir and not satir.startswith("1 password") and not satir.startswith("0 password"):
                return satir.split(":", 1)[1]
        return None
    finally:
        Path(sozluk_yolu).unlink(missing_ok=True)
        _sh.rmtree(gecici_home, ignore_errors=True)


def main():
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac("john-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", 8645)

    try:
        istemci = PoligonIstemci("http://127.0.0.1:8645", kod, sifre, "john_ogrencisi")
        gorev = istemci.gorevi_yukle("john-01")
        print(f"[ÖĞRENCİ] Görev: {gorev['baslik']['tr']}")

        istemci.gorevi_baslat()
        print(f"[ÖĞRENCİ] Hash dosyası: {istemci.dosya_yolu}")
        print(f"[ÖĞRENCİ] Gerçek parola (test için biliniyor): {istemci._dogru_cevap}")

        print("\n[ÖĞRENCİ] Gerçek john çalıştırılıyor...")
        bulunan = john_ile_kir(istemci.dosya_yolu, istemci._dogru_cevap)
        print(f"[ÖĞRENCİ] john'un bulduğu: {bulunan}")

        assert bulunan == istemci._dogru_cevap
        dogru = istemci.cevabi_kontrol_et(bulunan)
        assert dogru
        print(f"\n[MOTOR] Sonuç: ✓ GÖREV TAMAMLANDI, {gorev['puan']} puan kazanıldı")

        istemci.gorevi_durdur()
        print(f"[TEST] Dosya temizlendi mi: {not Path(istemci.dosya_yolu).exists()}")

        gorunum = oda.anlik_goruntu()
        assert gorunum["ogrenciler"]["john_ogrencisi"]["durum"] == "tamamlandi"
        print("✓ Öğretmen paneli john görevinin tamamlandığını doğru gördü")

        print("\n" + "=" * 70)
        print("✓ JOHN GÖREVİ UÇTAN UCA TESTİ BAŞARILI")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
