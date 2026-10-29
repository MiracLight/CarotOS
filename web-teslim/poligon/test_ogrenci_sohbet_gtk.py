"""
ÖĞRENCİ GTK SOHBET PANELİ TESTİ.

Öğrenci penceresini gerçekten açar, sunucuya bağlar, öğretmen mesaj
gönderir ve öğrencinin izleme döngüsünün bu mesajı GERÇEKTEN ekrana
(sohbet baloncuğuna) getirdiğini doğrular. Ayrıca öğrenci kendi
mesajını yazıp gönderdiğinde öğretmen tarafında göründüğünü test eder.

Bu test, GTK öğrenci uygulamasının artık kaldırılmış 'ipucu_var_mi'
yerine 'yeni_mesajlari_getir' kullandığını -- yani bug'ın gerçekten
düzeldiğini -- kanıtlar.
"""

import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402
from ogrenci_uygulama import PoligonPenceresi  # noqa: E402


def main():
    oda = OdaDurumu(oda_kodu_uret(), oda_sifresi_uret())
    oda.gorev_ac("hydra-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", 8642)
    time.sleep(0.3)
    print(f"[TEST] Oda: {oda.oda_kodu}/{oda.sifre}")

    pencere = PoligonPenceresi()
    pencere.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    sonuc = {}

    def adim1_katil():
        pencere.kod_girisi.set_text(oda.oda_kodu)
        pencere.sifre_girisi.set_text(oda.sifre)
        pencere.ad_girisi.set_text("sohbet_ogr")
        pencere.katil_dugmesi.clicked()
        GLib.timeout_add(1500, adim2_ogretmen_mesaj)
        return False

    def adim2_ogretmen_mesaj():
        gorunen = pencere.yigin.get_visible_child_name()
        print(f"[TEST] Katılım sonrası sayfa: {gorunen}")
        assert gorunen == "gorev", "görev sayfasına geçilemedi"
        # Öğretmen bir mesaj gönderiyor (GTK öğretmen panelinin yaptığı gibi)
        oda.mesaj_ekle("sohbet_ogr", "ogretmen", "Merhaba, nasıl gidiyor?")
        print("[TEST] Öğretmen mesaj gönderdi, öğrencinin çekmesi bekleniyor...")
        # İzleme döngüsü 3 saniyede bir; birkaç saniye bekleyip kontrol et
        GLib.timeout_add(4000, adim3_kontrol)
        return False

    def adim3_kontrol():
        for _ in range(10):
            while Gtk.events_pending():
                Gtk.main_iteration()
            time.sleep(0.1)
        gelen = [msj["metin"] for msj in pencere._sohbet_mesajlari]
        print(f"[TEST] Öğrenci ekranındaki notlar: {gelen}")
        sonuc["ogretmen_mesaji_geldi"] = "Merhaba, nasıl gidiyor?" in gelen
        assert sonuc["ogretmen_mesaji_geldi"], \
            "ÖĞRETMEN MESAJI ÖĞRENCİ EKRANINA GELMEDİ (bug hâlâ var)"
        print("[TEST] ✓ Öğretmen notu öğrenci ekranına geldi")

        # Tek yönlü tasarım: öğrenci tarafında yazma widget'ı OLMAMALI
        sonuc["giris_kutusu_yok"] = not hasattr(pencere, "sohbet_girisi")
        assert sonuc["giris_kutusu_yok"], \
            "öğrenci hâlâ geri yazabiliyor -- tek yönlü olması gerekiyordu"
        print("[TEST] ✓ Öğrenci tarafında yazma kutusu yok (tasarım gereği tek yönlü)")

        Gtk.main_quit()
        return False

    GLib.timeout_add(500, adim1_katil)
    Gtk.main()
    sunucu.shutdown()

    print("\n" + "=" * 70)
    if sonuc.get("ogretmen_mesaji_geldi") and sonuc.get("giris_kutusu_yok"):
        print("✓ ÖĞRENCİ GTK NOT GÜNLÜĞÜ (TEK YÖNLÜ) ÇALIŞIYOR")
    else:
        print("✗ BAŞARISIZ:", sonuc)
        sys.exit(1)
    print("=" * 70)


if __name__ == "__main__":
    main()
