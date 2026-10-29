"""
'Tüm sınıfa gönder' kutucuğu işaretliyken mesaj göndermeyi test eder.
Bu senaryo daha önce HİÇ test edilmemişti ve gerçek bir KeyError
çökmesine yol açıyordu (m["gonderildi_tum"] tanımsızdı).
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
    pencere = OgretmenPenceresi()
    pencere.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    # İki öğrenci katılsın ki "tüm sınıf" gerçekten anlamlı olsun
    ayse = PoligonIstemci("http://127.0.0.1:8642", pencere.oda.oda_kodu, pencere.oda.sifre, "ayse")
    ayse.acik_gorevleri_getir()
    ayse._bildir("basladi")
    mehmet = PoligonIstemci("http://127.0.0.1:8642", pencere.oda.oda_kodu, pencere.oda.sifre, "mehmet")
    mehmet._bildir("basladi")

    for _ in range(10):
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()

    print("[TEST] 'Tüm sınıfa gönder' kutucuğu işaretleniyor...")
    pencere.tum_sinif_kutusu.set_active(True)
    pencere.ipucu_girisi.set_text("Herkese: 5 dakikanız kaldı!")

    print("[TEST] Gönder düğmesine basılıyor (bu daha önce ÇÖKÜYORDU)...")
    pencere.ipucu_gonder_dugmesi.clicked()  # KeyError burada patlardı
    while Gtk.events_pending():
        Gtk.main_iteration()

    durum_metni = pencere.ipucu_durum_etiketi.get_text()
    print(f"[TEST] Durum etiketi: '{durum_metni}'")
    assert durum_metni, "durum etiketi boş kaldı"
    assert "sınıf" in durum_metni.lower() or "class" in durum_metni.lower()
    print("✓ Çökmeden 'tüm sınıfa gönderildi' mesajı gösterildi")

    # Her iki öğrenci de mesajı aldı mı?
    a_mesajlar = [x["metin"] for x in ayse.yeni_mesajlari_getir()]
    m_mesajlar = [x["metin"] for x in mehmet.yeni_mesajlari_getir()]
    print(f"[AYŞE] aldığı: {a_mesajlar}")
    print(f"[MEHMET] aldığı: {m_mesajlar}")
    assert "Herkese: 5 dakikanız kaldı!" in a_mesajlar
    assert "Herkese: 5 dakikanız kaldı!" in m_mesajlar
    print("✓ Her iki öğrenci de tüm sınıf mesajını aldı")

    pencere.sunucu.shutdown()
    print("\n" + "=" * 70)
    print("✓ TÜM SINIFA GÖNDER SENARYOSU ARTIK ÇALIŞIYOR (önceden çöküyordu)")
    print("=" * 70)


if __name__ == "__main__":
    main()
