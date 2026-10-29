"""
Öğretmenin, öğrenci satırındaki '✕' butonuna basarak öğrenciyi listeden
atabildiğini test eder.
"""

import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_uygulama import OgretmenPenceresi  # noqa: E402
from ogrenci_istemci import PoligonIstemci  # noqa: E402


def main():
    pencere = OgretmenPenceresi(gorev_id="hydra-01")
    pencere.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    ayse = PoligonIstemci("http://127.0.0.1:8642", pencere.oda.oda_kodu, pencere.oda.sifre, "ayse")
    ayse._bildir("basladi")
    mehmet = PoligonIstemci("http://127.0.0.1:8642", pencere.oda.oda_kodu, pencere.oda.sifre, "mehmet")
    mehmet._bildir("basladi")

    for _ in range(10):
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()

    print(f"[TEST] Başlangıçta liste: {sorted(pencere.oda.anlik_goruntu()['ogrenciler'].keys())}")
    assert set(pencere._satirlar.keys()) == {"ayse", "mehmet"}
    print("✓ İki öğrenci de GTK listesinde görünüyor")

    # Ayşe'nin satırındaki "✕" butonunu bul ve tıkla
    ayse_satiri = pencere._satirlar["ayse"]["satir"]
    icerik = ayse_satiri.get_child()
    at_dugmesi = None
    for cocuk in icerik.get_children():
        if isinstance(cocuk, Gtk.Button):
            at_dugmesi = cocuk
    assert at_dugmesi is not None, "✕ butonu bulunamadı"
    print("[TEST] Ayşe'nin '✕' butonuna basılıyor...")
    at_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()

    print(f"[TEST] Atma sonrası sunucu durumu: {sorted(pencere.oda.anlik_goruntu()['ogrenciler'].keys())}")
    assert "ayse" not in pencere.oda.anlik_goruntu()["ogrenciler"]
    print("✓ Ayşe sunucu tarafında da listeden çıkarıldı")

    print(f"[TEST] GTK listesindeki satırlar: {sorted(pencere._satirlar.keys())}")
    assert "ayse" not in pencere._satirlar
    assert "mehmet" in pencere._satirlar
    print("✓ Ayşe'nin satırı GTK listesinden kaldırıldı, Mehmet'inki duruyor")

    # Ayşe tekrar ilerleme bildirirse listeye geri dönebilmeli (kalıcı yasak değil)
    ayse._bildir("basladi")
    for _ in range(10):
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()
    assert "ayse" in pencere.oda.anlik_goruntu()["ogrenciler"]
    print("✓ Ayşe tekrar ilerleme bildirince listeye normal şekilde döndü (kalıcı yasak yok)")

    pencere.sunucu.shutdown()
    print("\n" + "=" * 70)
    print("✓ ÖĞRENCİYİ ATMA ÖZELLİĞİ ÇALIŞIYOR")
    print("=" * 70)


if __name__ == "__main__":
    main()
