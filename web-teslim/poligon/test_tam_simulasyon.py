"""
TAM SINIF SIMULASYONU -- gercek sunucu, gercek hydra, iki "ogrenci".

Ayse dogru cevabi bulup gonderir, Mehmet once yanlis dener sonra dogruyu
bulur. Ogretmen /durum'da ikisinin de son durumunu gormeli.
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402
from ogrenci_istemci import PoligonIstemci  # noqa: E402

PORT = 8643


def hydra_ile_bul(port: int, kullanici: str, dogru_parola: str) -> str | None:
    """Gerçek hydra çalıştırır, bulduğu parolayı döner (öğrencinin okuyup
    yapıştıracağı adımın simülasyonu)."""
    sahte_sozluk = ["123456", "password", dogru_parola, "qwerty", "admin"]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(sahte_sozluk) + "\n")
        sozluk_yolu = f.name
    try:
        sonuc = subprocess.run(
            ["hydra", "-l", kullanici, "-P", sozluk_yolu, "-s", str(port),
             "-t", "4", "127.0.0.1", "ftp"],
            capture_output=True, text=True, timeout=30,
        )
        import re
        eslesme = re.search(r"password:\s*(\S+)", sonuc.stdout)
        return eslesme.group(1) if eslesme else None
    finally:
        Path(sozluk_yolu).unlink(missing_ok=True)


def main():
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac("hydra-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", PORT)
    time.sleep(0.3)
    print(f"[ÖĞRETMEN] Oda açıldı. Kod: {kod}  Şifre: {sifre}")

    try:
        # --- AYŞE: doğru yolu izler ---
        print("\n[AYŞE] Odaya katılıyor, görevi başlatıyor...")
        ayse = PoligonIstemci(f"http://127.0.0.1:{PORT}", kod, sifre, "ayse")
        ayse.gorevi_yukle("hydra-01")
        ayse.gorevi_baslat()  # kendi 2222 portunda kendi servisini başlatır
        print(f"[AYŞE] Kendi hedef parolası (görünmez, sadece testte biliyoruz): {ayse.hedef_parola}")

        # hedef portu görevden al (2222, ama ikinci öğrenci çakışmasın diye ayrı porta ihtiyaç var)
        bulunan = hydra_ile_bul(ayse.gorev["hedef"]["port"], "ogrenci", ayse.hedef_parola)
        print(f"[AYŞE] hydra'nın bulduğu parola: {bulunan}")

        dogru_mu = ayse.cevabi_kontrol_et(bulunan)
        print(f"[AYŞE] Cevabı gönderdi, sonuç: {'DOĞRU' if dogru_mu else 'YANLIŞ'}")
        assert dogru_mu
        ayse.gorevi_durdur()

        # --- Öğretmen kontrolü ---
        import json, urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/durum") as r:
            durum = json.loads(r.read())
        print(f"\n[ÖĞRETMEN] /durum: {json.dumps(durum['ogrenciler'], ensure_ascii=False)}")
        assert durum["ogrenciler"]["ayse"]["durum"] == "tamamlandi"
        print("✓ Öğretmen panelinde Ayşe'nin durumu doğru: tamamlandı")

        # --- MEHMET: önce yanlış dener ---
        print("\n[MEHMET] Odaya katılıyor (Ayşe'nin servisi kapandığı için aynı portu kullanabilir)...")
        mehmet = PoligonIstemci(f"http://127.0.0.1:{PORT}", kod, sifre, "mehmet")
        mehmet.gorevi_yukle("hydra-01")
        mehmet.gorevi_baslat()

        print("[MEHMET] Önce yanlış bir cevap deniyor...")
        yanlis_sonuc = mehmet.cevabi_kontrol_et("tamamen-yanlis-bir-sey")
        assert not yanlis_sonuc
        print("[MEHMET] Yanlış olduğu doğrulandı, şimdi hydra çalıştırıyor...")

        bulunan2 = hydra_ile_bul(mehmet.gorev["hedef"]["port"], "ogrenci", mehmet.hedef_parola)
        dogru_mu2 = mehmet.cevabi_kontrol_et(bulunan2)
        print(f"[MEHMET] İkinci deneme sonucu: {'DOĞRU' if dogru_mu2 else 'YANLIŞ'}")
        assert dogru_mu2
        mehmet.gorevi_durdur()

        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/durum") as r:
            durum = json.loads(r.read())
        print(f"\n[ÖĞRETMEN] Son durum: {json.dumps(durum['ogrenciler'], ensure_ascii=False, indent=2)}")
        assert durum["ogrenciler"]["mehmet"]["durum"] == "tamamlandi"
        assert durum["ogrenciler"]["ayse"]["durum"] == "tamamlandi"

        print("\n" + "=" * 70)
        print("✓ TAM SINIF SİMÜLASYONU BAŞARILI")
        print("  İki öğrenci, iki bağımsız yerel servis, gerçek hydra saldırısı,")
        print("  yanlış deneme + doğru deneme, öğretmen paneli her ikisini de")
        print("  doğru şekilde izledi.")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
