"""
BUG DOĞRULAMA: öğretmen sıradaki göreve geçince, ZATEN BAĞLI öğrencinin
ekranı bunu fark ediyor mu?
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

    ogrenci = PoligonIstemci("http://127.0.0.1:8642", pencere.oda.oda_kodu, pencere.oda.sifre, "test")
    acik = ogrenci.acik_gorevleri_getir()
    print(f"[ÖĞRENCİ] Katıldığında açık görev: {acik}")
    gorev = ogrenci.gorevi_yukle(acik[0])
    print(f"[ÖĞRENCİ] Yüklenen görev: {gorev['id']}")
    assert gorev["id"] == "hydra-01"

    print("\n[ÖĞRETMEN] Sıradaki göreve geçiyor...")
    pencere.siradaki_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    print(f"[ÖĞRETMEN] Sunucu tarafında açık görev şimdi: {pencere.oda.acik_gorevler}")

    print("\n[ÖĞRENCİ] Tekrar /gorevler soruyor (eğer soruyorsa)...")
    yeni_acik = ogrenci.acik_gorevleri_getir()
    print(f"[ÖĞRENCİ] Sorgu sonucu: {yeni_acik}")

    # Asıl soru: öğrencinin GTK uygulaması bu değişikliği KENDİLİĞİNDEN
    # fark ediyor mu, yoksa sadece elle sorunca mı görüyor?
    print(f"\nSONUÇ: sunucu değişti mi: {pencere.oda.acik_gorevler != {'hydra-01'}}")
    print(f"SONUÇ: öğrenci elle sorunca doğru cevabı alıyor mu: {yeni_acik == list(pencere.oda.acik_gorevler)}")

    pencere.sunucu.shutdown()


if __name__ == "__main__":
    main()
