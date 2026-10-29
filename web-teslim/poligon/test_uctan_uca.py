"""
UCTAN UCA ENTEGRASYON TESTI.

Gercek gorev JSON dosyasini okur, orada tanimli parametrelerle servisi
baslatir, flag_uretici ile parola uretir (motor bunu boyle yapacak),
GERCEK hydra ile saldirtir, ogrencinin hydra ciktisindan okuyup
yapistiracagi parolayi motorun urettigi degerle karsilastirir.

Bu, sinifta olacak tam akisin simulasyonu:
  1. Ogretmen odayi acar -> motor flag/parola uretir, servisi baslatir
  2. Ogrenci hydra calistirir -> parolayi bulur
  3. Ogrenci bulunan parolayi uygulamaya yazar
  4. Motor karsilastirir -> dogru/yanlis
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flag_uretici import parola_uret  # noqa: E402
from servisler.sahte_giris import SahteGirisServisi  # noqa: E402


def main():
    # --- 1. ADIM: gorev tanimini oku (motorun yapacagi gibi) ---
    gorev = json.loads(Path("gorevler/sablon-ve-ornek.json").read_text(encoding="utf-8"))
    hedef = gorev["hedef"]

    assert hedef["bind_adres"] == "127.0.0.1", "gorev dosyasi guvenlik kuralini ihlal ediyor"

    print(f"Görev yüklendi: {gorev['baslik']['tr']}")
    print(f"  Araç: {gorev['arac']}  ·  Port: {hedef['port']}  ·  Bind: {hedef['bind_adres']}")

    # --- 2. ADIM: oda acilirken motor parolayi ureti ---
    dogru_parola = parola_uret()
    print(f"\nOda açıldı. Motor tarafından üretilen parola: {dogru_parola}")
    print("(Bu değer öğrenciye HİÇBİR ZAMAN gösterilmez, sadece log'da görünüyor)")

    # --- 3. ADIM: motor servisi baslatir ---
    servis = SahteGirisServisi(
        kullanici=hedef["sabit_kullanici"],
        parola=dogru_parola,
        port=hedef["port"],
        bind_adres=hedef["bind_adres"],
    )
    servis.baslat()
    time.sleep(0.3)
    print(f"\nSahte servis 127.0.0.1:{hedef['port']} üzerinde çalışıyor.")

    try:
        # --- 4. ADIM: OGRENCI ROLU -- gercek hydra ile saldiri ---
        # Ogrenci gorevin onerdigi ipucu komutunu (kucuk degisiklikle) calistirir.
        # Gercek sinifta rockyou benzeri gercek bir sozluk kullanilir; testte
        # kucuk bir liste kullaniyoruz ama mekanizma birebir ayni.
        sahte_sozluk = [
            "123456", "password", "qwerty", "admin", dogru_parola, "letmein", "111111",
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("\n".join(sahte_sozluk) + "\n")
            sozluk_yolu = f.name

        print(f"\n[ÖĞRENCİ] hydra çalıştırıyor (ipucu: {gorev['ipucu']['tr'][:50]}...)")
        komut = [
            "hydra", "-l", hedef["sabit_kullanici"], "-P", sozluk_yolu,
            "-s", str(hedef["port"]), "-t", "4", hedef["bind_adres"], "ftp",
        ]
        sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=30)

        # Ogrenci hydra ciktisindan parolayi okur (regex ile ayikliyoruz,
        # gercek ogrenci goz ile okuyup yapistirir)
        import re
        eslesme = re.search(r"password:\s*(\S+)", sonuc.stdout)
        ogrencinin_buldugu = eslesme.group(1) if eslesme else None

        print(f"[ÖĞRENCİ] hydra çıktısından okunan parola: {ogrencinin_buldugu}")

        # --- 5. ADIM: ogrenci bulunan parolayi uygulamaya yazar, motor dogrular ---
        print(f"\n[ÖĞRENCİ] Uygulamadaki kutuya '{ogrencinin_buldugu}' yazıp gönderiyor...")
        dogru_mu = (ogrencinin_buldugu == dogru_parola)

        print(f"\n[MOTOR] Karşılaştırma: '{ogrencinin_buldugu}' == '{dogru_parola}' ?")
        print(f"[MOTOR] Sonuç: {'✓ GÖREV TAMAMLANDI, ' + str(gorev['puan']) + ' puan kazanıldı' if dogru_mu else '✗ YANLIŞ'}")

        assert dogru_mu, "UCTAN UCA TEST BASARISIZ: ogrencinin buldugu parola motorunkiyle eslesmiyor"
        print("\n" + "=" * 70)
        print("✓ UÇTAN UCA TEST GEÇTİ")
        print("  Oda açılışından öğrenci doğrulamasına kadar tüm zincir çalıştı.")
        print("=" * 70)

    finally:
        servis.durdur()
        Path(sozluk_yolu).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
