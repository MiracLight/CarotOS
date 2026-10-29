"""
OGRETMEN GTK UYGULAMASINI GERCEKTEN CALISTIRIP TEST EDER.

- Ogretmen penceresi acilir, oda kodu/sifre GERCEKTEN uretilir ve gosterilir
- Baslangicta liste "kimse katilmadi" gostermeli
- GERCEK bir ogrenci (PoligonIstemci + gercek hydra) odaya katilir
- Liste GUNCELLENMELI (polling ile) -- ogrenci gorunmeli
- Ogrenci gorevi tamamlar (gercek hydra ile) -- durum "Tamamlandi" olmali
- Ogretmen o satiri secip ipucu gonderir -- ogrencinin istemcisi bunu almali
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
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_uygulama import OgretmenPenceresi  # noqa: E402
from ogrenci_istemci import PoligonIstemci  # noqa: E402


def hydra_ile_bul(port, kullanici, dogru_parola):
    sahte_sozluk = ["123456", "password", dogru_parola, "qwerty"]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(sahte_sozluk) + "\n")
        yol = f.name
    try:
        sonuc = subprocess.run(
            ["hydra", "-l", kullanici, "-P", yol, "-s", str(port),
             "-t", "4", "127.0.0.1", "ftp"],
            capture_output=True, text=True, timeout=30,
        )
        eslesme = re.search(r"password:\s*(\S+)", sonuc.stdout)
        return eslesme.group(1) if eslesme else None
    finally:
        Path(yol).unlink(missing_ok=True)


def main():
    pencere = OgretmenPenceresi()
    pencere.show_all()

    sonuclar = {}
    while Gtk.events_pending():
        Gtk.main_iteration()

    # --- ADIM 0: oda kodu/şifre gerçekten üretildi mi ve gösteriliyor mu ---
    kod = pencere.kod_deger_etiketi.get_text()
    sifre = pencere.sifre_deger_etiketi.get_text()
    print(f"[TEST] Öğretmen ekranında gösterilen oda kodu: {kod}  şifre: {sifre}")
    sonuclar["kod_gosteriliyor"] = bool(kod) and kod == pencere.oda.oda_kodu
    sonuclar["sifre_gosteriliyor"] = bool(sifre) and sifre == pencere.oda.sifre
    assert sonuclar["kod_gosteriliyor"] and sonuclar["sifre_gosteriliyor"]
    print("[TEST] ✓ Oda kodu ve şifre doğru üretilip gösterildi")

    # --- ADIM 1: liste başta boş olmalı ---
    ilk_satir = pencere.liste_kutusu.get_row_at_index(0)
    ilk_metin = ilk_satir.get_child().get_text() if ilk_satir else None
    print(f"[TEST] Başlangıç liste durumu: '{ilk_metin}'")
    sonuclar["bastan_bos"] = "katılmadı" in (ilk_metin or "") or "joined yet" in (ilk_metin or "")

    # --- ADIM 2: gerçek öğrenci arka planda katılır ve görevi çözer ---
    print("\n[ÖĞRENCİ] Arka planda odaya katılıyor (gerçek ağ isteğiyle)...")
    istemci = PoligonIstemci(f"http://127.0.0.1:8642", kod, sifre, "test_ogrenci")

    def ogrenci_akisi():
        istemci.gorevi_yukle("hydra-01")
        istemci.gorevi_baslat()
        sonuclar["ogrenci_basladi"] = True

    thread = threading.Thread(target=ogrenci_akisi, daemon=True)
    thread.start()
    thread.join(timeout=5)

    # Öğretmen panelinin polling'i yakalaması için birkaç ana döngü çeviriyoruz
    for _ in range(15):
        time.sleep(0.15)
        while Gtk.events_pending():
            Gtk.main_iteration()

    gorunum = pencere.oda.anlik_goruntu()
    print(f"[TEST] Sunucu durumu (dahili): {gorunum['ogrenciler']}")
    sonuclar["ogrenci_listede"] = "test_ogrenci" in gorunum["ogrenciler"]
    assert sonuclar["ogrenci_listede"], "öğrenci sunucu tarafında görünmüyor"

    # Liste kutusunda gerçekten satır oluştu mu (GTK tarafı)
    bulunan_satir = None
    for i in range(10):
        satir = pencere.liste_kutusu.get_row_at_index(i)
        if satir is None:
            break
        if getattr(satir, "ogrenci_adi", None) == "test_ogrenci":
            bulunan_satir = satir
            break
    sonuclar["gtk_listesinde_gorunuyor"] = bulunan_satir is not None
    assert sonuclar["gtk_listesinde_gorunuyor"], "öğrenci GTK listesinde görünmüyor"
    print("[TEST] ✓ Öğrenci hem sunucuda hem öğretmen GTK listesinde görünüyor")

    # --- ADIM 3: gerçek hydra ile görevi tamamla ---
    port = istemci.gorev["hedef"]["port"]
    parola = istemci.hedef_parola
    print(f"\n[ÖĞRENCİ] Gerçek hydra çalıştırılıyor (port {port})...")
    bulunan = hydra_ile_bul(port, "ogrenci", parola)
    print(f"[ÖĞRENCİ] hydra buldu: {bulunan}")
    dogru = istemci.cevabi_kontrol_et(bulunan)
    assert dogru, "hydra'nın bulduğu cevap yanlış çıktı"
    istemci.gorevi_durdur()

    for _ in range(10):
        time.sleep(0.15)
        while Gtk.events_pending():
            Gtk.main_iteration()

    gorunum = pencere.oda.anlik_goruntu()
    print(f"[TEST] Tamamlama sonrası sunucu durumu: {gorunum['ogrenciler']['test_ogrenci']}")
    sonuclar["tamamlandi_yansidi"] = gorunum["ogrenciler"]["test_ogrenci"]["durum"] == "tamamlandi"
    assert sonuclar["tamamlandi_yansidi"]

    # GTK listesindeki durum metni de güncellendi mi?
    bulunan_satir = None
    for i in range(10):
        satir = pencere.liste_kutusu.get_row_at_index(i)
        if satir and getattr(satir, "ogrenci_adi", None) == "test_ogrenci":
            bulunan_satir = satir
            break
    kutu = bulunan_satir.get_child()
    etiketler = [w for w in kutu.get_children() if isinstance(w, Gtk.Label)]
    durum_metni = etiketler[1].get_text() if len(etiketler) > 1 else "?"
    print(f"[TEST] GTK listesindeki durum metni: '{durum_metni}'")
    sonuclar["gtk_durum_tamamlandi"] = durum_metni in ("Tamamlandı", "Completed")
    assert sonuclar["gtk_durum_tamamlandi"]
    print("[TEST] ✓ Görev tamamlanması hem sunucuda hem öğretmen ekranında yansıdı")

    # Ekran görüntüsü
    win = pencere.get_window()
    pix = Gdk.pixbuf_get_from_window(win, 0, 0, *pencere.get_size())
    pix.savev("ogretmen-ekrani.png", "png", [], [])
    print("[TEST] Ekran görüntüsü kaydedildi: ogretmen-ekrani.png")

    # --- ADIM 4: öğretmen mesaj gönderir, öğrenci alır mı? ---
    print("\n[ÖĞRETMEN] Öğrenciyi seçip mesaj gönderiyor...")
    pencere.liste_kutusu.select_row(bulunan_satir)
    while Gtk.events_pending():
        Gtk.main_iteration()
    pencere.ipucu_girisi.set_text("Bir dahaki sefere şunu dene: kullanıcı adı sabit")
    pencere.ipucu_gonder_dugmesi.clicked()

    yeni = istemci.yeni_mesajlari_getir()
    metinler = [x["metin"] for x in yeni]
    print(f"[ÖĞRENCİ] Aldığı mesajlar: {metinler}")
    sonuclar["ipucu_ulasti"] = "Bir dahaki sefere şunu dene: kullanıcı adı sabit" in metinler
    assert sonuclar["ipucu_ulasti"], "mesaj öğrenciye ulaşmadı"
    print("[TEST] ✓ Öğretmenden gönderilen mesaj öğrenciye gerçekten ulaştı")

    pencere.sunucu.shutdown()

    print("\n" + "=" * 70)
    basarili = all(sonuclar.values())
    print("✓ ÖĞRETMEN GTK UYGULAMASI UÇTAN UCA TESTİ BAŞARILI" if basarili
          else f"✗ BAZI TESTLER BAŞARISIZ: {sonuclar}")
    print("=" * 70)
    if not basarili:
        sys.exit(1)


if __name__ == "__main__":
    main()
