"""
GTK OGRENCI UYGULAMASINI GERCEKTEN CALISTIRIP TEST EDER.

- Gercek ogretmen sunucusu ayaga kalkar
- GTK penceresi acilir (Xvfb uzerinde)
- "Katil" dugmesine PROGRAMATIK olarak basilir
- Gorev gercekten yuklenir, yerel servis gercekten baslar
- Gercek hydra calistirilir
- Bulunan cevap metin kutusuna yazilir, "Gonder"e basilir
- Sonuc etiketinin GERCEKTEN "dogru" gosterdigi dogrulanir
- Dil degistirme dugmesi de test edilir
- Ekran goruntusu alinir
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
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402
from ogrenci_uygulama import PoligonPenceresi  # noqa: E402

PORT = 8642  # ogrenci_uygulama.py bu portu sabit kullanıyor


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
    kod = oda_kodu_uret()
    sifre = oda_sifresi_uret()
    oda = OdaDurumu(kod, sifre)
    oda.gorev_ac("hydra-01")
    sunucu = sunucu_baslat(oda, "127.0.0.1", PORT)
    time.sleep(0.3)
    print(f"[TEST] Sunucu ayakta. Oda: {kod} / {sifre}")

    pencere = PoligonPenceresi()
    pencere.show_all()

    sonuclar = {}

    def adim_1_alanlari_doldur_ve_katil():
        pencere.kod_girisi.set_text(kod)
        pencere.sifre_girisi.set_text(sifre)
        pencere.ad_girisi.set_text("test_ogrenci")
        print("[TEST] Alanlar dolduruldu, 'Katıl' düğmesine basılıyor...")
        pencere.katil_dugmesi.clicked()
        GLib.timeout_add(1200, adim_2_gorevi_kontrol_et)
        return False

    def adim_2_gorevi_kontrol_et():
        gorunen = pencere.yigin.get_visible_child_name()
        print(f"[TEST] Katılım sonrası görünen sayfa: '{gorunen}'")
        sonuclar["katilim_basarili"] = (gorunen == "gorev")
        sonuclar["gorev_basligi"] = pencere.gorev_baslik_etiketi.get_text()
        sonuclar["senaryo_metni"] = pencere.senaryo_etiketi.get_text()
        print(f"[TEST] Görev başlığı: '{sonuclar['gorev_basligi']}'")
        print(f"[TEST] Senaryo (ilk 60 karakter): '{sonuclar['senaryo_metni'][:60]}...'")
        assert sonuclar["katilim_basarili"], "katılım sonrası görev sayfasına geçilmedi"
        assert sonuclar["gorev_basligi"], "görev başlığı boş geldi"

        # Ekran görüntüsü — görev sayfası
        GLib.timeout_add(200, lambda: (adim_3_hydra_calistir(), False)[1])
        return False

    def adim_3_hydra_calistir():
        istemci = pencere.istemci
        port = istemci.gorev["hedef"]["port"]
        parola = istemci.hedef_parola
        print(f"[TEST] Öğrencinin yerel servisi port {port}'da, gerçek parola (test için biliniyor): {parola}")
        print("[TEST] Gerçek hydra çalıştırılıyor...")
        bulunan = hydra_ile_bul(port, "ogrenci", parola)
        print(f"[TEST] hydra'nın bulduğu: {bulunan}")
        sonuclar["hydra_buldu_mu"] = (bulunan == parola)
        assert sonuclar["hydra_buldu_mu"], "hydra doğru parolayı bulamadı"

        pencere.cevap_girisi.set_text(bulunan)
        print("[TEST] Cevap kutusuna yazıldı, 'Gönder' düğmesine basılıyor...")
        pencere.gonder_dugmesi.clicked()

        sonuc_metni = pencere.sonuc_etiketi.get_text()
        print(f"[TEST] Sonuç etiketi: '{sonuc_metni}'")
        sonuclar["sonuc_dogru_gosterildi"] = "✓" in sonuc_metni or "Doğru" in sonuc_metni or "Correct" in sonuc_metni
        assert sonuclar["sonuc_dogru_gosterildi"], f"sonuç etiketi doğruyu göstermiyor: {sonuc_metni}"

        # Ekran görüntüsü — gerçek pencere yüzeyinden (manuel draw() değil)
        while Gtk.events_pending():
            Gtk.main_iteration()
        win = pencere.get_window()
        pix = Gdk.pixbuf_get_from_window(win, 0, 0, *pencere.get_size())
        pix.savev("arena-gorev-basarili.png", "png", [], [])
        print("[TEST] Ekran görüntüsü kaydedildi.")

        GLib.timeout_add(300, adim_4_dil_degistir)
        return False

    def adim_4_dil_degistir():
        print("\n[TEST] Dil değiştirme test ediliyor (TR -> EN)...")
        # NOT: başlık kasıtlı olarak her iki dilde de "CarotOS Poligon" --
        # isim marka kimliği, çeviri gerekmiyor. Dil değişimini başka
        # gerçekten çeviri gerektiren alanlardan (dil düğmesi etiketi,
        # senaryo metni) doğruluyoruz.
        onceki_dil_dugmesi = pencere.dil_dugmesi.get_label()
        pencere.dil_dugmesi.clicked()
        yeni_dil_dugmesi = pencere.dil_dugmesi.get_label()
        print(f"[TEST] Dil düğmesi önce: '{onceki_dil_dugmesi}'  sonra: '{yeni_dil_dugmesi}'")
        sonuclar["dil_degisti"] = (onceki_dil_dugmesi != yeni_dil_dugmesi)
        sonuclar["en_senaryo"] = pencere.senaryo_etiketi.get_text()
        print(f"[TEST] İngilizce senaryo metni: '{sonuclar['en_senaryo'][:60]}...'")
        assert sonuclar["dil_degisti"], "dil düğmesi etiketi değişmedi"
        assert sonuclar["en_senaryo"] != sonuclar["senaryo_metni"], "İngilizce metin Türkçe ile aynı geldi"
        # Başlığın HER İKİ dilde de "CarotOS Poligon" kaldığını doğrula --
        # bu artık beklenen davranış, hata değil.
        baslik_sabit_mi = pencere.baslik_etiketi.get_text() == "CarotOS Poligon"
        print(f"[TEST] Başlık her iki dilde de 'CarotOS Poligon' mu: {baslik_sabit_mi}")
        assert baslik_sabit_mi, "başlık artık 'CarotOS Poligon' değil"

        while Gtk.events_pending():
            Gtk.main_iteration()
        win = pencere.get_window()
        pix = Gdk.pixbuf_get_from_window(win, 0, 0, *pencere.get_size())
        pix.savev("arena-ingilizce.png", "png", [], [])

        GLib.timeout_add(300, bitir)
        return False

    def bitir():
        Gtk.main_quit()
        return False

    GLib.timeout_add(500, adim_1_alanlari_doldur_ve_katil)
    Gtk.main()

    sunucu.shutdown()
    pencere.istemci and pencere.istemci  # servis zaten cevap sonrası kapanmadı, elle durduralım
    try:
        if pencere.istemci and pencere.istemci._servis:
            pencere.istemci._servis.durdur()
    except Exception:
        pass

    print("\n" + "=" * 70)
    if all([
        sonuclar.get("katilim_basarili"),
        sonuclar.get("hydra_buldu_mu"),
        sonuclar.get("sonuc_dogru_gosterildi"),
        sonuclar.get("dil_degisti"),
    ]):
        print("✓ GTK UYGULAMASI UÇTAN UCA TESTİ BAŞARILI")
    else:
        print("✗ BAZI TESTLER BAŞARISIZ:", sonuclar)
        sys.exit(1)
    print("=" * 70)


if __name__ == "__main__":
    main()
