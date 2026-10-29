"""
Bireysel mod arayüz değişikliklerini test eder:
1. Sohbet paneli ("Öğretmenden Notlar") bireysel modda GİZLİ olmalı
2. "Atla" butonu bireysel modda GÖRÜNÜR olmalı
3. Atla butonuna basınca GERÇEKTEN farklı bir göreve geçmeli
"""

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_uygulama import PoligonPenceresi  # noqa: E402


def main():
    pencere = PoligonPenceresi()
    pencere.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    print("[TEST] Bireysel Pratik seçiliyor...")
    pencere.bireysel_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    pencere.teste_basla_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()

    ilk_gorev = pencere.gorev_verisi["id"]
    print(f"[TEST] İlk görev: {ilk_gorev}")

    print(f"[TEST] Sohbet paneli görünür mü: {pencere.sohbet_kart.get_visible()}")
    assert not pencere.sohbet_kart.get_visible(), "bireysel modda sohbet paneli görünüyor"
    print("✓ Bireysel modda 'Öğretmenden Notlar' paneli gizli")

    print(f"[TEST] Atla butonu görünür mü: {pencere.atla_dugmesi.get_visible()}")
    assert pencere.atla_dugmesi.get_visible(), "bireysel modda atla butonu görünmüyor"
    print("✓ Bireysel modda 'Atla' butonu görünür")

    eski_servis = pencere.istemci._servis
    print("\n[TEST] Atla butonuna basılıyor...")
    pencere.atla_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()

    yeni_gorev = pencere.gorev_verisi["id"]
    print(f"[TEST] Yeni görev: {yeni_gorev}")
    assert yeni_gorev != ilk_gorev, "atla butonu aynı görevi tekrar getirdi"
    print("✓ Atla butonu gerçekten farklı bir görev getirdi")
    assert pencere.istemci._servis is not eski_servis
    print("✓ Eski yerel servis durdurulup yenisi başlatıldı")

    dogru_cevap = pencere.istemci._dogru_cevap
    pencere.cevap_girisi.set_text(str(dogru_cevap))
    pencere.gonder_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    sonuc = pencere.sonuc_etiketi.get_text()
    print(f"[TEST] Atlanan görevin sonucu: {sonuc}")
    assert "✓" in sonuc or "Doğru" in sonuc
    print("✓ Atlanan yeni görev de gerçekten çözülebiliyor")

    pencere.istemci.gorevi_durdur()

    print("\n" + "=" * 70)
    print("✓ BİREYSEL MOD ARAYÜZ DEĞİŞİKLİKLERİ (SOHBET GİZLEME + ATLA) ÇALIŞIYOR")
    print("=" * 70)


if __name__ == "__main__":
    main()
