"""
İsim çakışması kontrolünü test eder: aynı isimle iki öğrenci katılmaya
çalışırsa, ikincisi reddedilmeli.
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
    sunucu = sunucu_baslat(oda, "127.0.0.1", 8651)
    time.sleep(0.3)

    try:
        print("--- TEST 1: ilk 'ayse' katılımı başarılı olmalı ---")
        ayse1 = PoligonIstemci("http://127.0.0.1:8651", kod, sifre, "ayse")
        basarili, hata = ayse1.katil()
        print(f"Sonuç: basarili={basarili}, hata='{hata}'")
        assert basarili and hata == ""
        print("✓ İlk katılım başarılı")

        print("\n--- TEST 2: aynı isimle ikinci katılım REDDEDİLMELİ ---")
        ayse2 = PoligonIstemci("http://127.0.0.1:8651", kod, sifre, "ayse")
        basarili2, hata2 = ayse2.katil()
        print(f"Sonuç: basarili={basarili2}, hata='{hata2}'")
        assert not basarili2, "aynı isim kabul edildi -- bu bir hata"
        assert hata2 == "Bu isim mevcut sınıf için alındı", f"beklenmeyen hata mesajı: {hata2}"
        print("✓ İkinci katılım doğru mesajla reddedildi")

        print("\n--- TEST 3: farklı isim sorunsuz katılabilmeli ---")
        mehmet = PoligonIstemci("http://127.0.0.1:8651", kod, sifre, "mehmet")
        basarili3, hata3 = mehmet.katil()
        print(f"Sonuç: basarili={basarili3}, hata='{hata3}'")
        assert basarili3
        print("✓ Farklı isim sorunsuz katıldı")

        print("\n--- TEST 4: yanlış şifreyle katılma denemesi ---")
        yanlis = PoligonIstemci("http://127.0.0.1:8651", kod, "yanlis-sifre", "zeynep")
        basarili4, hata4 = yanlis.katil()
        print(f"Sonuç: basarili={basarili4}, hata='{hata4}'")
        assert not basarili4
        print("✓ Yanlış şifre reddedildi")

        print("\n--- TEST 5: öğretmen 'ayse'yi atınca isim tekrar müsait olmalı ---")
        oda.ogrenciyi_at("ayse")
        ayse_tekrar = PoligonIstemci("http://127.0.0.1:8651", kod, sifre, "ayse")
        basarili5, hata5 = ayse_tekrar.katil()
        print(f"Sonuç: basarili={basarili5}, hata='{hata5}'")
        assert basarili5, "atılan öğrencinin ismi tekrar kullanılamadı"
        print("✓ Atılan öğrencinin ismi tekrar kullanılabildi")

        print("\n" + "=" * 70)
        print("✓ İSİM ÇAKIŞMASI KONTROLÜ TAM ÇALIŞIYOR")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
