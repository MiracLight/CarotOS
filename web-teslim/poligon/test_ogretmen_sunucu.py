"""
ogretmen_sunucu.py'yi GERCEK HTTP istekleriyle test eder (urllib ile,
tıpkı öğrenci uygulamasının yapacağı gibi).
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402

PORT = 8642
TABAN = f"http://127.0.0.1:{PORT}"


def istek(yol, gövde=None, yontem="GET"):
    veri = json.dumps(gövde).encode() if gövde is not None else None
    r = urllib.request.Request(TABAN + yol, data=veri, method=yontem,
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main():
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    print(f"Oda kodu: {kod}  ·  Oda şifresi: {sifre}")
    assert kod.isdigit() and len(kod) == 4, "oda kodu 4 haneli olmalı"

    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac("hydra-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", PORT)
    time.sleep(0.3)

    try:
        print("\n--- TEST 1: yanlış şifreyle ilerleme göndermek reddedilmeli ---")
        durum, cevap = istek("/ilerleme", {
            "ogrenci": "ayse", "sifre": "yanlis-sifre",
            "gorev_id": "hydra-01", "durum": "basladi",
        }, "POST")
        print(f"  durum kodu: {durum}  cevap: {cevap}")
        assert durum == 403, "yanlış şifre kabul edildi -- güvenlik hatası"
        print("  ✓ reddedildi")

        print("\n--- TEST 2: doğru şifreyle ilerleme kabul edilmeli ---")
        durum, cevap = istek("/ilerleme", {
            "ogrenci": "ayse", "sifre": sifre,
            "gorev_id": "hydra-01", "durum": "basladi", "sure_sn": 12,
        }, "POST")
        print(f"  durum kodu: {durum}  cevap: {cevap}")
        assert durum == 200 and cevap.get("tamam")
        print("  ✓ kabul edildi")

        print("\n--- TEST 3: öğretmen /durum ile öğrenciyi görmeli ---")
        durum, cevap = istek("/durum")
        print(f"  {json.dumps(cevap, ensure_ascii=False, indent=2)}")
        assert "ayse" in cevap["ogrenciler"]
        assert cevap["ogrenciler"]["ayse"]["durum"] == "basladi"
        print("  ✓ öğrenci listede, durumu doğru")

        print("\n--- TEST 4: öğrenci görevi tamamlayınca durum güncellenmeli ---")
        istek("/ilerleme", {
            "ogrenci": "ayse", "sifre": sifre,
            "gorev_id": "hydra-01", "durum": "tamamlandi", "sure_sn": 187,
        }, "POST")
        durum, cevap = istek("/durum")
        assert cevap["ogrenciler"]["ayse"]["durum"] == "tamamlandi"
        assert cevap["ogrenciler"]["ayse"]["sure_sn"] == 187
        print("  ✓ tamamlandı durumu ve süre doğru yansıdı")

        print("\n--- TEST 5: sohbet mesajı gönderme ve son_no ile çekme ---")
        istek("/mesaj", {"ogrenci": "ayse", "kimden": "ogretmen",
                          "metin": "Kullanıcı adını unutma"}, "POST")
        durum, cevap = istek("/sohbet?ogrenci=ayse&son_no=0")
        print(f"  ilk çekme: {cevap}")
        assert any(x["metin"] == "Kullanıcı adını unutma" for x in cevap["mesajlar"])
        en_son = max(x["no"] for x in cevap["mesajlar"])
        durum, cevap = istek(f"/sohbet?ogrenci=ayse&son_no={en_son}")
        print(f"  ikinci çekme (son_no={en_son}): {cevap}")
        assert cevap["mesajlar"] == [], "son_no sonrası mesaj olmamalı"
        print("  ✓ mesaj çekildi, son_no ile tekrar çekilmiyor (geçmiş korunuyor)")

        print("\n--- TEST 6: iki farklı öğrenci aynı anda ---")
        istek("/ilerleme", {"ogrenci": "mehmet", "sifre": sifre,
                             "gorev_id": "hydra-01", "durum": "basladi"}, "POST")
        durum, cevap = istek("/durum")
        assert set(cevap["ogrenciler"].keys()) == {"ayse", "mehmet"}
        print(f"  ✓ iki öğrenci de listede: {list(cevap['ogrenciler'].keys())}")

        print("\n" + "=" * 70)
        print("✓ TÜM SUNUCU TESTLERİ GEÇTİ")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
