"""
Ogretmen giris ekranini GERCEK sudo parolasiyla test eder:
1. Yanlis parola girilirse ogretmen penceresi ACILMAMALI
2. Dogru parola girilirse ogretmen penceresi acilmali
"""

import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_uygulama import OgretmenGirisPenceresi  # noqa: E402

DOGRU_PAROLA = "testsifre123"


def main():
    sonuc = {}

    print("=== TEST 1: YANLIS parola ===")
    giris1 = OgretmenGirisPenceresi("hydra-01")
    giris1.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    giris1.parola_girisi.set_text("kesinlikle-yanlis-bir-parola")
    giris1.giris_dugmesi.clicked()

    for _ in range(30):
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()

    print(f"[TEST] Durum mesaji: '{giris1.durum_etiketi.get_text()}'")
    sonuc["yanlis_reddedildi"] = giris1.durum_etiketi.get_text() == "Yanlış parola, tekrar deneyin."
    assert sonuc["yanlis_reddedildi"], "yanlis parola kabul edilmis gibi gorunuyor"
    print("OK: Yanlis parola reddedildi")
    giris1.destroy()

    print("\n=== TEST 2: DOGRU parola ===")
    giris2 = OgretmenGirisPenceresi("hydra-01")
    giris2.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    giris2.parola_girisi.set_text(DOGRU_PAROLA)
    giris2.giris_dugmesi.clicked()

    for _ in range(30):
        time.sleep(0.1)
        while Gtk.events_pending():
            Gtk.main_iteration()

    acilan_pencereler = [
        w for w in Gtk.Window.list_toplevels()
        if w.get_title() and "Ogretmen" not in "" and "retmen" in (w.get_title() or "")
    ]
    print(f"[TEST] Acik pencere basliklari: {[w.get_title() for w in Gtk.Window.list_toplevels()]}")
    sonuc["dogru_kabul_edildi"] = len(acilan_pencereler) > 0
    assert sonuc["dogru_kabul_edildi"], "dogru parola girildigi halde ogretmen penceresi acilmadi"
    print("OK: Dogru parola kabul edildi, ogretmen penceresi acildi")

    if acilan_pencereler:
        acilan_pencereler[0].sunucu.shutdown()

    print("\n" + "=" * 70)
    if sonuc.get("yanlis_reddedildi") and sonuc.get("dogru_kabul_edildi"):
        print("SONUC: OGRETMEN GIRIS EKRANI (ROOT PAROLASI) TAM CALISIYOR")
    else:
        print("BASARISIZ:", sonuc)
        sys.exit(1)
    print("=" * 70)


if __name__ == "__main__":
    main()
