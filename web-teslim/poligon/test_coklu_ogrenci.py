"""
DÜZELTME TESTİ: aynı makinede iki öğrenci + port çakışması + ipucu.

1. İki öğrenci aynı hydra görevine katılır -> ikincisi port çakışması
   YAŞAMAMALI (otomatik farklı porta geçmeli)
2. Her ikisi de kendi gerçek portunu bilmeli
3. Öğretmen ipucu gönderince her iki öğrenci de KENDİ ipucusunu almalı
"""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_istemci import PoligonIstemci  # noqa: E402
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402


def hydra_dene(port, parola):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("123456\n" + parola + "\nqwerty\n")
        yol = f.name
    try:
        r = subprocess.run(["hydra", "-l", "ogrenci", "-P", yol, "-s", str(port),
                            "-t", "4", "127.0.0.1", "ftp"],
                           capture_output=True, text=True, timeout=30)
        import re
        m = re.search(r"password:\s*(\S+)", r.stdout)
        return m.group(1) if m else None
    finally:
        Path(yol).unlink(missing_ok=True)


def main():
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac("hydra-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", 8648)

    try:
        print("=== İki öğrenci aynı makinede, aynı göreve katılıyor ===")
        ayse = PoligonIstemci("http://127.0.0.1:8648", kod, sifre, "ayse")
        ayse.gorevi_yukle("hydra-01")
        ayse.gorevi_baslat()
        print(f"[AYŞE] gerçek port: {ayse.gercek_port}")

        mehmet = PoligonIstemci("http://127.0.0.1:8648", kod, sifre, "mehmet")
        mehmet.gorevi_yukle("hydra-01")
        mehmet.gorevi_baslat()
        print(f"[MEHMET] gerçek port: {mehmet.gercek_port}")

        assert ayse.gercek_port != mehmet.gercek_port, \
            "PORT ÇAKIŞMASI: iki öğrenci aynı portu kullanıyor!"
        print(f"✓ İki öğrenci farklı portlarda ({ayse.gercek_port} ve {mehmet.gercek_port})")

        # Her ikisi de kendi görevini gerçekten çözebiliyor mu
        a_bul = hydra_dene(ayse.gercek_port, ayse._dogru_cevap)
        m_bul = hydra_dene(mehmet.gercek_port, mehmet._dogru_cevap)
        assert ayse.cevabi_kontrol_et(a_bul), "Ayşe görevini çözemedi"
        assert mehmet.cevabi_kontrol_et(m_bul), "Mehmet görevini çözemedi"
        print("✓ Her iki öğrenci de kendi servisini bağımsız çözdü")

        print("\n=== Sohbet: her öğrenci kendi mesajını almalı ===")
        oda.mesaj_ekle("ayse", "ogretmen", "Ayşe için: portu kontrol et")
        oda.mesaj_ekle("mehmet", "ogretmen", "Mehmet için: sözlüğü genişlet")

        a_mesajlar = [x["metin"] for x in ayse.yeni_mesajlari_getir()]
        m_mesajlar = [x["metin"] for x in mehmet.yeni_mesajlari_getir()]
        print(f"[AYŞE] aldığı: {a_mesajlar}")
        print(f"[MEHMET] aldığı: {m_mesajlar}")
        assert a_mesajlar == ["Ayşe için: portu kontrol et"]
        assert m_mesajlar == ["Mehmet için: sözlüğü genişlet"]
        print("✓ Her öğrenci doğru mesajını aldı (karışma yok)")

        # son_no takibi: ikinci çekimde yeni mesaj olmamalı
        assert ayse.yeni_mesajlari_getir() == []
        print("✓ Aynı mesaj iki kez çekilmiyor (son_no takibi)")

        ayse.gorevi_durdur()
        mehmet.gorevi_durdur()

        print("\n" + "=" * 70)
        print("✓ PORT ÇAKIŞMASI + SOHBET DÜZELTMELERİ DOĞRULANDI")
        print("=" * 70)

    finally:
        sunucu.shutdown()


if __name__ == "__main__":
    main()
