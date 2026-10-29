"""
Sohbet sistemini GERCEK HTTP istekleriyle test eder.

- Ogretmen bir ogrenciye mesaj yollar -> ogrenci gorur
- Ogrenci geri yazar -> ogretmen gorur
- Mesajlar BIRIKIR (tek seferlik degil) -- son_no ile artan cekme
- 'tum_sinif' mesaji butun ogrencilere gider
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402

PORT = 8655
TABAN = f"http://127.0.0.1:{PORT}"


def istek(yol, govde=None, yontem="GET"):
    veri = json.dumps(govde).encode() if govde is not None else None
    r = urllib.request.Request(TABAN + yol, data=veri, method=yontem,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=5) as resp:
        return json.loads(resp.read())


def main():
    oda = OdaDurumu(oda_kodu_uret(), oda_sifresi_uret())
    oda.gorev_ac("hydra-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", PORT)
    time.sleep(0.3)
    s = oda.sifre

    try:
        # İki öğrenci katılıyor (ilerleme göndererek kayıt oluşuyor)
        istek("/ilerleme", {"ogrenci": "ayse", "sifre": s, "gorev_id": "hydra-01",
                            "durum": "basladi", "sure_sn": 0}, "POST")
        istek("/ilerleme", {"ogrenci": "mehmet", "sifre": s, "gorev_id": "hydra-01",
                            "durum": "basladi", "sure_sn": 0}, "POST")

        print("=== TEST 1: öğretmen -> ayşe (birebir) ===")
        istek("/mesaj", {"ogrenci": "ayse", "kimden": "ogretmen",
                         "metin": "Kullanıcı adını unutma"}, "POST")
        ayse_msg = istek("/sohbet?ogrenci=ayse&son_no=0")["mesajlar"]
        mehmet_msg = istek("/sohbet?ogrenci=mehmet&son_no=0")["mesajlar"]
        print(f"  ayşe: {[m['metin'] for m in ayse_msg]}")
        print(f"  mehmet: {[m['metin'] for m in mehmet_msg]}")
        assert len(ayse_msg) == 1 and ayse_msg[0]["metin"] == "Kullanıcı adını unutma"
        assert len(mehmet_msg) == 0, "birebir mesaj yanlış öğrenciye gitti!"
        print("  ✓ sadece ayşe aldı")

        print("\n=== TEST 2: ayşe geri yazıyor (çift yön) ===")
        istek("/mesaj", {"ogrenci": "ayse", "kimden": "ogrenci",
                         "metin": "Takıldım, port neydi?"}, "POST")
        ayse_msg = istek("/sohbet?ogrenci=ayse&son_no=0")["mesajlar"]
        print(f"  ayşe sohbeti: {[(m['kimden'], m['metin']) for m in ayse_msg]}")
        assert len(ayse_msg) == 2
        assert ayse_msg[1]["kimden"] == "ogrenci"
        print("  ✓ öğrenci mesajı geçmişe eklendi, kimden='ogrenci'")

        print("\n=== TEST 3: mesajlar BİRİKİYOR (tek seferlik değil) ===")
        # Aynı sohbeti tekrar çek -- mesajlar hâlâ orada olmalı
        ayse_msg_tekrar = istek("/sohbet?ogrenci=ayse&son_no=0")["mesajlar"]
        assert len(ayse_msg_tekrar) == 2, "mesajlar kayboldu (tek seferlik davranış)!"
        print("  ✓ ikinci okumada mesajlar hâlâ duruyor")

        print("\n=== TEST 4: son_no ile sadece YENİ mesajları çekme ===")
        en_son = ayse_msg[-1]["no"]
        istek("/mesaj", {"ogrenci": "ayse", "kimden": "ogretmen",
                         "metin": "Port 2222"}, "POST")
        yeniler = istek(f"/sohbet?ogrenci=ayse&son_no={en_son}")["mesajlar"]
        print(f"  son_no={en_son} sonrası yeni: {[m['metin'] for m in yeniler]}")
        assert len(yeniler) == 1 and yeniler[0]["metin"] == "Port 2222"
        print("  ✓ sadece yeni mesaj döndü (öğrenci sürekli tümünü çekmez)")

        print("\n=== TEST 5: tüm sınıfa mesaj ===")
        istek("/mesaj", {"ogrenci": "tum_sinif", "kimden": "ogretmen",
                         "metin": "10 dakikanız kaldı"}, "POST")
        a = istek("/sohbet?ogrenci=ayse&son_no=0")["mesajlar"]
        m = istek("/sohbet?ogrenci=mehmet&son_no=0")["mesajlar"]
        assert any(x["metin"] == "10 dakikanız kaldı" for x in a)
        assert any(x["metin"] == "10 dakikanız kaldı" for x in m)
        print("  ✓ tüm sınıf mesajı hem ayşe'ye hem mehmet'e ulaştı")

        print("\n" + "=" * 70)
        print("✓ SOHBET SİSTEMİ (SUNUCU) TÜM TESTLERİ GEÇTİ")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
