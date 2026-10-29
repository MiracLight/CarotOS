"""
Ogretmen soru atayinca / degistirince, ZATEN GTK penceresi acik olan
ogrencinin ekraninin GERCEKTEN otomatik guncellendigini test eder.
(nmap-01 -> sqlmap-01; her iki servis de saf python, harici ikili gerekmez.)
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


def bekle(n=1):
    for _ in range(n):
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()


def main():
    ogretmen = OgretmenPenceresi()
    ogretmen.show_all()
    bekle()

    # 1. soru: nmap-01 ata
    ogretmen._gorev_anahtarlari["nmap-01"].set_active(True)
    ogretmen.siradaki_dugmesi.clicked()
    bekle()
    assert ogretmen.oda.aktif_soru_no == 1

    ogrenci_pencere = PoligonPenceresi()
    ogrenci_pencere.show_all()
    bekle()

    ogrenci_pencere.sinif_mod_dugmesi.clicked()
    bekle()
    ogrenci_pencere.kod_girisi.set_text(ogretmen.oda.oda_kodu)
    ogrenci_pencere.sifre_girisi.set_text(ogretmen.oda.sifre)
    ogrenci_pencere.ad_girisi.set_text("test_ogr")
    ogrenci_pencere.katil_dugmesi.clicked()

    # Bekleme ekrani + otomatik yukleme (poll 3 sn) icin bekle
    for _ in range(60):
        bekle(1)
        if ogrenci_pencere.gorev_verisi:
            break
    print("[OGRENCI] Katildi, gorev:", (ogrenci_pencere.gorev_verisi or {}).get("id"))
    assert ogrenci_pencere.gorev_verisi and ogrenci_pencere.gorev_verisi["id"] == "nmap-01"
    assert ogrenci_pencere.istemci.aktif_soru_no == 1
    print("\u2713 Ogrenci 1. soruyu (nmap-01) otomatik yukledi")

    # 2. soru: sqlmap-01 ata
    print("[OGRETMEN] sqlmap-01 atiyor (ogrenci penceresi acik)...")
    ogretmen._gorev_anahtarlari["sqlmap-01"].set_active(True)
    ogretmen.siradaki_dugmesi.clicked()
    bekle()
    assert ogretmen.oda.aktif_soru_no == 2

    # Ogrenci izleme dongusu (3 sn) yeni soruyu alsin
    for _ in range(70):
        bekle(1)
        if ogrenci_pencere.gorev_verisi and ogrenci_pencere.gorev_verisi["id"] == "sqlmap-01":
            break
    print("[OGRENCI] Guncel gorev:", ogrenci_pencere.gorev_verisi["id"],
          "| soru_no:", ogrenci_pencere.istemci.aktif_soru_no)
    assert ogrenci_pencere.gorev_verisi["id"] == "sqlmap-01"
    assert ogrenci_pencere.istemci.aktif_soru_no == 2
    print("\u2713 Ogrenci 2. soruya (sqlmap-01) otomatik gecti")

    ogretmen.sunucu.shutdown()
    print("\n\u2713 OTOMATIK SORU GECISI (SIRA NUMARALI) TESTI BASARILI")


if __name__ == "__main__":
    main()
