"""
SORULAR SEKMESI TESTI (yeni davranis):
- Oda BOS baslar (acilista otomatik gorev YOK).
- Radyo isaretlemek gorevi ACMAZ; "Soruyu Ata" ile acilir.
- Her atama soru sira numarasini (aktif_soru_no) bir artirir.
"""

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_uygulama import OgretmenPenceresi  # noqa: E402


def bekle():
    while Gtk.events_pending():
        Gtk.main_iteration()


def main():
    pencere = OgretmenPenceresi()  # ARTIK bos baslar
    pencere.show_all()
    bekle()

    print("[TEST] Baslangicta acik gorevler:", pencere.oda.acik_gorevler)
    assert pencere.oda.acik_gorevler == set(), "oda bos baslamali"
    assert pencere.oda.aktif_soru_no == 0, "baslangicta soru numarasi 0 olmali"
    print("\u2713 Oda bos basladi, soru numarasi 0")

    # nmap radyosunu isaretle -- bu TEK BASINA gorev acmamali
    pencere._gorev_anahtarlari["nmap-01"].set_active(True)
    bekle()
    assert pencere.oda.acik_gorevler == set(), \
        "isaretlemek gorevi acmamali, sadece secimi belirler"
    print("\u2713 Isaretlemek tek basina gorevi ACMADI")

    # "Soruyu Ata" -> 1. soru
    pencere.siradaki_dugmesi.clicked()
    bekle()
    print("Acik gorevler:", pencere.oda.acik_gorevler, "| soru_no:", pencere.oda.aktif_soru_no)
    print("Durum:", pencere.sinif_durum_etiketi.get_text())
    assert pencere.oda.acik_gorevler == {"nmap-01"}
    assert pencere.oda.aktif_soru_no == 1
    assert "1" in pencere.sinif_durum_etiketi.get_text()
    print("\u2713 'Soruyu Ata' -> nmap-01 acildi, 1. soru")

    # Ogrenci /gorevler ile soru numarasini da gorur
    import urllib.request, json
    with urllib.request.urlopen("http://127.0.0.1:8642/gorevler") as r:
        cevap = json.loads(r.read())
    print("[OGRENCI] /gorevler:", cevap)
    assert cevap["acik_gorevler"] == ["nmap-01"]
    assert cevap["aktif_soru_no"] == 1

    # tshark sec + ata -> 2. soru
    pencere._gorev_anahtarlari["tshark-01"].set_active(True)
    pencere.siradaki_dugmesi.clicked()
    bekle()
    assert pencere.oda.acik_gorevler == {"tshark-01"}
    assert pencere.oda.aktif_soru_no == 2
    print("\u2713 Ikinci atama -> tshark-01, 2. soru")

    pencere.sunucu.shutdown()
    print("\n" + "=" * 70)
    print("\u2713 SORULAR SEKMESI (BOS BASLAMA + SIRA NUMARASI) TAM CALISIYOR")
    print("=" * 70)


if __name__ == "__main__":
    main()
