"""
BİREYSEL/SINIF MOD AYRIMI TESTİ.

- Uygulama açılınca giriş ekranı gösterilmeli (Misafir -> mod seçimi)
- 'Bireysel Pratik' -> hiç ağa bağlanmadan rastgele bir görev başlamalı
- 'Sınıfa Katıl' -> mevcut oda kodu/şifre akışına gitmeli
- 'Geri' butonları mod seçimine dönmeli
"""

import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_uygulama import PoligonPenceresi  # noqa: E402


def main():
    pencere = PoligonPenceresi()
    pencere.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    print("[TEST] Açılış sayfası:", pencere.yigin.get_visible_child_name())
    assert pencere.yigin.get_visible_child_name() == "giris"
    print("✓ Uygulama giriş ekranıyla açılıyor")

    # Misafir olarak devam et -> mod seçim ekranı
    pencere.misafir_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    assert pencere.yigin.get_visible_child_name() == "mod_secimi"
    assert pencere.aktif_kullanici is None
    print("✓ Misafir seçimi mod seçim ekranına götürdü (aktif_kullanici=None)")

    # --- Sınıf modu: Geri butonu doğru çalışıyor mu ---
    print("\n[TEST] 'Sınıfa Katıl' -> 'Geri' -> mod seçime dönmeli")
    pencere.sinif_mod_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    assert pencere.yigin.get_visible_child_name() == "baglanti"
    assert pencere.bireysel_mod is False
    print("✓ Sınıfa Katıl doğru sayfaya götürdü, bireysel_mod=False")

    pencere.geri_dugmesi_sinif.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    assert pencere.yigin.get_visible_child_name() == "mod_secimi"
    print("✓ Geri butonu mod seçimine döndürdü")

    # --- Bireysel mod: rastgele görevle, ağ olmadan başlamalı ---
    print("\n[TEST] 'Bireysel Pratik' -> 'Teste Başla' -> rastgele görev")
    pencere.bireysel_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    assert pencere.yigin.get_visible_child_name() == "bireysel_basla"
    assert pencere.bireysel_mod is True
    print("✓ Bireysel Pratik doğru sayfaya götürdü, bireysel_mod=True")

    pencere.teste_basla_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()

    print("[TEST] Görev sayfasına geçildi mi:", pencere.yigin.get_visible_child_name())
    assert pencere.yigin.get_visible_child_name() == "gorev"
    assert pencere.istemci is not None
    assert pencere.istemci.bireysel_mod is True
    print(f"✓ Rastgele görev başladı: {pencere.gorev_verisi['id']} ({pencere.gorev_verisi['arac']})")

    # Servis gerçekten ayakta mı? (istemcinin _servis'i None olmamalı)
    assert pencere.istemci._servis is not None
    print("✓ Yerel hedef servis gerçekten başlatıldı")

    # Görevi çözelim (cevabı doğrudan biliyoruz, testte)
    dogru_cevap = pencere.istemci._dogru_cevap
    pencere.cevap_girisi.set_text(str(dogru_cevap))
    pencere.gonder_dugmesi.clicked()
    while Gtk.events_pending():
        Gtk.main_iteration()
    sonuc_metni = pencere.sonuc_etiketi.get_text()
    print(f"[TEST] Sonuç: {sonuc_metni}")
    assert "✓" in sonuc_metni or "Doğru" in sonuc_metni or "Correct" in sonuc_metni
    print("✓ Bireysel moddaki görev yerel olarak doğrulandı (ağ olmadan)")

    pencere.istemci.gorevi_durdur()

    print("\n" + "=" * 70)
    print("✓ BİREYSEL/SINIF MOD AYRIMI TAM ÇALIŞIYOR")
    print("=" * 70)


if __name__ == "__main__":
    main()
