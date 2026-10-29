"""
GTK "Katıl" akışının artık isim çakışmasını GERÇEKTEN engellediğini
test eder -- öğrenci uygulaması üzerinden, gerçek pencereyle.
"""

import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_uygulama import OgretmenPenceresi  # noqa: E402
from ogrenci_uygulama import PoligonPenceresi  # noqa: E402


def main():
    ogretmen = OgretmenPenceresi(gorev_id="hydra-01")
    ogretmen.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    ogrenci1 = PoligonPenceresi()
    ogrenci1.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()
    ogrenci1.sinif_mod_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    ogrenci1.kod_girisi.set_text(ogretmen.oda.oda_kodu)
    ogrenci1.sifre_girisi.set_text(ogretmen.oda.sifre)
    ogrenci1.ad_girisi.set_text("ayse")
    ogrenci1.katil_dugmesi.clicked()

    for _ in range(20):
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()

    print(f"[ÖĞRENCİ 1] Görev sayfasına geçti mi: {ogrenci1.yigin.get_visible_child_name()}")
    assert ogrenci1.yigin.get_visible_child_name() == "gorev"
    print("✓ İlk 'ayse' katılımı başarılı, görev sayfasına geçti")

    ogrenci2 = PoligonPenceresi()
    ogrenci2.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()
    ogrenci2.sinif_mod_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    ogrenci2.kod_girisi.set_text(ogretmen.oda.oda_kodu)
    ogrenci2.sifre_girisi.set_text(ogretmen.oda.sifre)
    ogrenci2.ad_girisi.set_text("ayse")
    ogrenci2.katil_dugmesi.clicked()

    for _ in range(20):
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()

    print(f"[ÖĞRENCİ 2] Görev sayfasına geçti mi: {ogrenci2.yigin.get_visible_child_name()}")
    print(f"[ÖĞRENCİ 2] Durum mesajı: '{ogrenci2.baglanti_durum_etiketi.get_text()}'")
    assert ogrenci2.yigin.get_visible_child_name() != "gorev", \
        "AYNI İSİMLE İKİNCİ ÖĞRENCİ KATILABİLDİ -- bu bir hata"
    assert ogrenci2.baglanti_durum_etiketi.get_text() == "Bu isim mevcut sınıf için alındı"
    print("✓ İkinci 'ayse' katılımı GTK arayüzünde doğru şekilde reddedildi")

    ogrenci3 = PoligonPenceresi()
    ogrenci3.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()
    ogrenci3.sinif_mod_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    ogrenci3.kod_girisi.set_text(ogretmen.oda.oda_kodu)
    ogrenci3.sifre_girisi.set_text(ogretmen.oda.sifre)
    ogrenci3.ad_girisi.set_text("mehmet")
    ogrenci3.katil_dugmesi.clicked()

    for _ in range(20):
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()

    print(f"[ÖĞRENCİ 3] Görev sayfasına geçti mi: {ogrenci3.yigin.get_visible_child_name()}")
    assert ogrenci3.yigin.get_visible_child_name() == "gorev"
    print("✓ Farklı isimle üçüncü öğrenci sorunsuz katıldı")

    ogrenci1.istemci.gorevi_durdur()
    ogrenci3.istemci.gorevi_durdur()
    ogretmen.sunucu.shutdown()

    print("\n" + "=" * 70)
    print("✓ GTK KATIL AKIŞINDA İSİM ÇAKIŞMASI KONTROLÜ TAM ÇALIŞIYOR")
    print("=" * 70)


if __name__ == "__main__":
    main()
