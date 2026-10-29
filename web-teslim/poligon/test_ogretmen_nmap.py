"""
Ogretmen nmap-01 actiginda, ogrenci uygulamasinin (istemci mantigi
uzerinden, GTK'siz) dogru gorevi alip GERCEK nmap ile cozdugunu test eder.
"""

import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_uygulama import OgretmenPenceresi  # noqa: E402
from ogrenci_istemci import PoligonIstemci  # noqa: E402


def nmap_ile_bul():
    sonuc = subprocess.run(
        ["nmap", "-p", "20-25,25,110,143,3306,20000-20999", "-T4", "127.0.0.1"],
        capture_output=True, text=True, timeout=60,
    )
    for satir in sonuc.stdout.splitlines():
        m = re.match(r"(\d+)/tcp\s+open\s+unknown", satir)
        if m:
            return m.group(1)
    return None


def main():
    pencere = OgretmenPenceresi(gorev_id="nmap-01")
    pencere.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()
    # Oda artik bos basladigi icin nmap-01'i acikca ata (radyo on-secili gelir).
    pencere.siradaki_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()

    kod, sifre = pencere.oda.oda_kodu, pencere.oda.sifre
    print(f"[TEST] Öğretmen nmap-01 açtı. Oda: {kod}/{sifre}")

    istemci = PoligonIstemci("http://127.0.0.1:8642", kod, sifre, "nmap_test")

    hata_kutusu = []

    def akis():
        try:
            acik = istemci.acik_gorevleri_getir()
            assert acik == ["nmap-01"], f"beklenmeyen açık görev listesi: {acik}"
            gorev = istemci.gorevi_yukle(acik[0])
            assert gorev["arac"] == "nmap"
            istemci.gorevi_baslat()
        except Exception as e:  # arka plan thread'i sessizce yutmasın
            hata_kutusu.append(e)

    t = threading.Thread(target=akis, daemon=True)
    t.start()
    t.join(timeout=5)
    if hata_kutusu:
        raise hata_kutusu[0]

    for _ in range(15):
        time.sleep(0.15)
        while Gtk.events_pending():
            Gtk.main_iteration()

    gorunum = pencere.oda.anlik_goruntu()
    print(f"[TEST] Öğretmen panelinde: {gorunum['ogrenciler']}")
    assert "nmap_test" in gorunum["ogrenciler"]
    print("✓ Öğrenci öğretmen panelinde göründü (nmap görevinde)")

    print("\n[ÖĞRENCİ] Gerçek nmap çalıştırılıyor...")
    bulunan = nmap_ile_bul()
    print(f"[ÖĞRENCİ] Bulunan port: {bulunan}")
    dogru = istemci.cevabi_kontrol_et(bulunan)
    assert dogru
    istemci.gorevi_durdur()

    for _ in range(10):
        time.sleep(0.15)
        while Gtk.events_pending():
            Gtk.main_iteration()

    gorunum = pencere.oda.anlik_goruntu()
    assert gorunum["ogrenciler"]["nmap_test"]["durum"] == "tamamlandi"
    print(f"[TEST] Tamamlanma sonrası öğretmen panelinde: {gorunum['ogrenciler']['nmap_test']}")
    print("✓ Öğretmen paneli nmap görevinin tamamlandığını doğru gösterdi")

    pencere.sunucu.shutdown()
    print("\n✓ ÖĞRETMEN + NMAP UÇTAN UCA TESTİ BAŞARILI")


if __name__ == "__main__":
    main()
