#!/usr/bin/env python3
"""
CarotOS Poligon -- ogrenci uygulamasi (GTK3).

Gorsel dil CarotOS Guvenlik Paneli ile tutarli tutulmustur: koyu tema,
sol tarafta durum, sag tarafta islem alani. Iki dilli (TR/EN), sag ustte
dil degistirici -- CarotOS'un genel dil deseniyle ayni yerde.
"""

from __future__ import annotations

import sys
import json
import os
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_istemci import BaglantiHatasi, GOREVLER_DIZINI, PoligonIstemci  # noqa: E402
import gecmis_defteri  # noqa: E402


def _gorev_sudo_gerektirir_mi(gorev_id: str) -> bool:
    """ufw-01/fail2ban-01 gibi görevler öğrencinin kendi makinesinde
    sudo yetkisi gerektirir -- bireysel modun RASTGELE havuzuna hiç
    girmezler. Öğretmen bunları sınıfa bilerek açarsa (Sınıf sekmesinde
    ayrı gösterilirler, bkz. ogretmen_uygulama.py) sınıf modunda normal
    şekilde gelirler; bu filtre SADECE bireysel/atla rastgele seçimi
    içindir."""
    yol = GOREVLER_DIZINI / f"{gorev_id}.json"
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return veri.get("dogrulama", {}).get("tur") in ("ufw_engeli", "fail2ban_durumu")


def _bireysel_havuz() -> list:
    """Bireysel modun rastgele seçim yapacağı görev dosyalarının listesi:
    şablon hariç, sudo gerektiren savunma görevleri hariç."""
    return [
        g for g in sorted(GOREVLER_DIZINI.glob("*.json"))
        if g.stem != "sablon-ve-ornek" and not _gorev_sudo_gerektirir_mi(g.stem)
    ]

def _sistem_dilini_belirle() -> str:
    """Uygulama ilk açıldığında hangi dille başlayacağını belirler:
    sistem dili Türkçe ise 'tr', başka HERHANGİ bir dilse (ya da hiç
    belirlenemiyorsa) 'en'. LC_ALL/LC_MESSAGES/LANG/LANGUAGE ortam
    değişkenlerine bakılıyor -- GTK/gettext'in de kullandığı standart
    öncelik sırası bu. Kullanıcı yine de sağ üstteki dil düğmesiyle
    istediği an değiştirebiliyor, bu sadece AÇILIŞ varsayılanı."""
    for degisken in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        if os.environ.get(degisken, "").lower().startswith("tr"):
            return "tr"
    return "en"


METIN = {
    "tr": {
        "baslik": "CarotOS Poligon",
        "baglan_sekme": "Odaya Katıl",
        "ogretmen_adres": "Öğretmen Adresi (IP)",
        "oda_kodu": "Oda Kodu",
        "oda_sifre": "Oda Şifresi",
        "ad": "Adın",
        "baglan": "Katıl",
        "baglaniyor": "Bağlanıyor…",
        "hata_alan": "Tüm alanları doldur",
        "hata_baglanti": "Öğretmen sunucusuna ulaşılamıyor",
        "gorev_yuklendi": "Görev yüklendi, hedef hazırlanıyor…",
        "senaryo_basligi": "Senaryo",
        "ipucu_goster": "İpucunu Göster",
        "cevap_yer_tut": "Bulduğun parolayı buraya yaz",
        "gonder": "Gönder",
        "dogru": "✓ Doğru! Görev tamamlandı.",
        "yanlis": "✗ Yanlış, tekrar dene.",
        "puan": "puan",
        "yeni_ipucu": "Öğretmenden yeni ipucu geldi:",
        "sohbet_basligi": "Öğretmenden Notlar",
        "sohbet_yer_tut": "Öğretmene bir soru yaz…",
        "sohbet_gonder": "Yolla",
        "sohbet_bos": "Henüz not yok. Öğretmenin gönderdiği ipuçları burada birikir.",
        "yeni_gorev_bildirimi": "Öğretmen yeni bir göreve geçti:",
        "atildin_basligi": "Sınıftan çıkarıldın",
        "atildin_mesaji": "Öğretmen seni sınıf listesinden çıkardı. Tekrar katılmak istersen oda kodunu ve şifresini tekrar gir.",
        "oda_kapandi_basligi": "Sınıf sona erdi",
        "oda_kapandi_mesaji": "Öğretmen paneli kapanmıştır. Tekrar katılmak istersen öğretmenin yeni oda kodu/şifresiyle tekrar dene.",
        "tamam": "Tamam",
        "kimden_ogretmen": "Öğretmen",
        "kimden_ben": "Sen",
        "mod_secim_basligi": "Nasıl pratik yapmak istersin?",
        "bireysel_dugme": "Bireysel Pratik",
        "bireysel_aciklama": "Rastgele bir görevle hemen başla. Öğretmen gerekmez, kendi hızında ilerlersin.",
        "sinif_mod_dugme": "Sınıfa Katıl",
        "sinif_mod_aciklama": "Öğretmenin verdiği oda kodu ve şifreyle sınıfa katıl.",
        "geri": "← Geri",
        "bireysel_bilgi": "Rastgele bir görev seçilecek. Hazır olduğunda başla.",
        "teste_basla": "Teste Başla",
        "gecmis_ozet": "Bugüne kadar {sayi} görev tamamladın · toplam {puan} puan.",
        "gecmis_yok": "Henüz tamamlanmış bir görevin yok — ilk görevin seni bekliyor.",
        "atla_dugmesi": "↻ Bu görevi atla, farklı bir tane getir",
        "kontrol_et": "Kontrol Et",
        "kontrol_ediliyor": "Kontrol ediliyor…",
        "sudo_parola_basligi": "Sudo Parolası",
        "sudo_parola_aciklama": "Bu görev, savunma önlemini gerçekten uyguladığını doğrulamak için kendi sudo parolanı ister (ör. ufw/fail2ban durumunu okumak için).",
        "sudo_parola_yer_tut": "Sudo parolan",
        "giris_yap": "Doğrula",
        "iptal": "İptal",
    },
    "en": {
        "baslik": "CarotOS Poligon",
        "baglan_sekme": "Join Room",
        "ogretmen_adres": "Teacher Address (IP)",
        "oda_kodu": "Room Code",
        "oda_sifre": "Room Password",
        "ad": "Your Name",
        "baglan": "Join",
        "baglaniyor": "Connecting…",
        "hata_alan": "Fill in all fields",
        "hata_baglanti": "Cannot reach the teacher's server",
        "gorev_yuklendi": "Task loaded, preparing target…",
        "senaryo_basligi": "Scenario",
        "ipucu_goster": "Show Hint",
        "cevap_yer_tut": "Type the password you found here",
        "gonder": "Submit",
        "dogru": "✓ Correct! Task completed.",
        "yanlis": "✗ Incorrect, try again.",
        "puan": "points",
        "yeni_ipucu": "New hint from the teacher:",
        "sohbet_basligi": "Notes from Teacher",
        "sohbet_yer_tut": "Ask the teacher a question…",
        "sohbet_gonder": "Send",
        "sohbet_bos": "No notes yet. Hints from the teacher will collect here.",
        "yeni_gorev_bildirimi": "The teacher moved the class to a new task:",
        "atildin_basligi": "Removed from class",
        "atildin_mesaji": "The teacher removed you from the class list. Enter the room code and password again if you'd like to rejoin.",
        "oda_kapandi_basligi": "Class has ended",
        "oda_kapandi_mesaji": "The teacher's panel has closed. If you'd like to rejoin, ask the teacher for a new room code/password.",
        "tamam": "OK",
        "kimden_ogretmen": "Teacher",
        "kimden_ben": "You",
        "mod_secim_basligi": "How would you like to practice?",
        "bireysel_dugme": "Individual Practice",
        "bireysel_aciklama": "Start immediately with a random task. No teacher needed, go at your own pace.",
        "sinif_mod_dugme": "Join a Class",
        "sinif_mod_aciklama": "Join the class using the room code and password from your teacher.",
        "geri": "← Back",
        "bireysel_bilgi": "A random task will be chosen. Start when you're ready.",
        "teste_basla": "Start Task",
        "gecmis_ozet": "You've completed {sayi} tasks so far · {puan} points total.",
        "gecmis_yok": "You haven't completed any tasks yet — your first one is waiting.",
        "atla_dugmesi": "↻ Skip this task, give me another",
        "kontrol_et": "Check",
        "kontrol_ediliyor": "Checking…",
        "sudo_parola_basligi": "Sudo Password",
        "sudo_parola_aciklama": "This task asks for your own sudo password to actually verify you applied the defense (e.g. to read ufw/fail2ban status).",
        "sudo_parola_yer_tut": "Your sudo password",
        "giris_yap": "Verify",
        "iptal": "Cancel",
    },
}

KOYU_ZEMIN = "#0b2e52"
KART_ZEMIN = "#123a63"
VURGU = "#378ADA"
YESIL = "#4a9c78"
KIRMIZI = "#c0546a"


class PoligonPenceresi(Gtk.Window):
    def __init__(self):
        super().__init__(title="CarotOS Poligon")
        try:
            self.set_icon_from_file(
                "/usr/share/icons/hicolor/256x256/apps/carotos-poligon-ogrenci.png"
            )
        except GLib.Error:
            pass  # ISO disinda (bagimsiz depodan) calistirilirsa ikon bulunamayabilir
        self.dil = _sistem_dilini_belirle()
        self._css_saglayici = None
        self._ikincil_metin_rengi = "#eaf4fc"
        self._geri_metin_rengi = "#a8c6e0"
        self.istemci: PoligonIstemci | None = None
        self._ipucu_izleyici_id = None
        self.bireysel_mod = False  # True ise öğretmen sunucusuna hiç bağlanılmaz

        self.set_default_size(560, 480)
        self._css_uygula()

        self.yigin = Gtk.Stack()
        self.yigin.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        self._mod_secim_sayfasi_olustur()
        self._baglanti_sayfasi_olustur()
        self._gorev_sayfasi_olustur()

        ana = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ana.pack_start(self._ust_cubuk_olustur(), False, False, 0)
        ana.pack_start(self.yigin, True, True, 0)
        self.add(ana)

        self._metinleri_uygula()
        self.yigin.set_visible_child_name("mod_secimi")

    # ------------------------------------------------------------------
    def _css_uygula(self):
        """Sabit koyu tema. Pencere ve kartlar hep aynı marka lacivert
        paletini kullanır -- tema değiştirme özelliği kaldırıldı."""
        if self._css_saglayici is None:
            self._css_saglayici = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(
                self.get_screen(), self._css_saglayici,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

        kart_zemin = KART_ZEMIN
        kart_kenar = "rgba(169, 198, 224, 0.30)"
        metin_ana = "#eaf4fc"
        metin_soft = "#a8c6e0"
        giris_zemin = "#0e3a68"
        giris_kenar = "rgba(169, 198, 224, 0.25)"
        ikincil_zemin = "#1a4a7a"
        ikincil_metin = "#eaf4fc"
        sohbet_zemin = "#17406e"
        sohbet_metin = "#eaf4fc"
        self._ikincil_metin_rengi = "#eaf4fc"
        self._geri_metin_rengi = "#a8c6e0"

        self._css_saglayici.load_from_data(f"""
            window {{ background-color: {KOYU_ZEMIN}; }}
            label {{ color: {metin_ana}; }}
            .kart {{
                background-color: {kart_zemin}; border-radius: 10px; padding: 18px;
                border: 1px solid {kart_kenar};
            }}
            .baslik {{ color: {metin_ana}; font-size: 20px; font-weight: 800; }}
            .baslik-sabit {{ color: #eaf4fc; font-size: 20px; font-weight: 800; }}
            .etiket {{ color: {metin_soft}; font-size: 13px; }}
            .durum-dogru {{ color: {YESIL}; font-weight: 700; }}
            .durum-yanlis {{ color: {KIRMIZI}; font-weight: 700; }}
            entry {{
                background-color: {giris_zemin}; color: {metin_ana};
                border: 1px solid {giris_kenar}; border-radius: 6px;
            }}
            button {{ color: {metin_ana}; }}
            button label {{ color: {metin_ana}; }}
            button.vurgu {{
                background-color: {VURGU}; background-image: none;
                border: none; box-shadow: none;
                color: white; border-radius: 999px; padding: 6px 16px;
            }}
            button.vurgu label {{ color: white; }}
            button.ikincil {{
                background-color: {ikincil_zemin}; background-image: none;
                border: none; box-shadow: none;
                color: {ikincil_metin}; border-radius: 10px; padding: 10px 16px;
            }}
            button.ikincil label {{ color: {ikincil_metin}; }}
            button.duz {{
                background-color: transparent; background-image: none;
                border: none; box-shadow: none;
                color: {metin_soft}; padding: 4px 10px;
            }}
            button.duz label {{ color: {metin_soft}; }}
            .sohbet-ogretmen {{ background-color: {sohbet_zemin}; color: {sohbet_metin}; border-radius: 8px; padding: 6px 10px; }}
            .sohbet-ogrenci {{ background-color: {VURGU}; color: white; border-radius: 8px; padding: 6px 10px; }}
        """.encode())

    def _ust_cubuk_olustur(self):
        cubuk = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cubuk.set_margin_top(10); cubuk.set_margin_bottom(6)
        cubuk.set_margin_start(16); cubuk.set_margin_end(16)

        self.baslik_etiketi = Gtk.Label(xalign=0)
        self.baslik_etiketi.get_style_context().add_class("baslik-sabit")
        cubuk.pack_start(self.baslik_etiketi, True, True, 0)

        self.dil_dugmesi = Gtk.Button(label="EN")
        self.dil_dugmesi.get_style_context().add_class("ikincil")
        self.dil_dugmesi.connect("clicked", self._dili_degistir)
        cubuk.pack_end(self.dil_dugmesi, False, False, 0)
        return cubuk

    def _dugme_metni_ayarla(self, dugme: Gtk.Button, metin: str, renk: str = "#eaf4fc"):
        """Buton metnini Pango markup ile renklendirir. CSS sınıf
        mirasına güvenmek yerine bunu kullanıyoruz -- GTK3'te bazı
        temalarda buton içi label'a class miras kalmayabiliyor,
        markup her koşulda garantili çalışıyor."""
        etiket = dugme.get_child()
        if etiket is None:
            etiket = Gtk.Label()
            dugme.add(etiket)
            etiket.show()
        etiket.set_markup(f"<span color='{renk}'>{GLib.markup_escape_text(metin)}</span>")

    def _dili_degistir(self, _düğme):
        self.dil = "en" if self.dil == "tr" else "tr"
        self._metinleri_uygula()

    def _metinleri_uygula(self):
        m = METIN[self.dil]
        self.baslik_etiketi.set_text(m["baslik"])
        self.dil_dugmesi.set_label("TR" if self.dil == "en" else "EN")
        self.mod_baslik_etiketi.set_text(m["mod_secim_basligi"])
        self._dugme_metni_ayarla(self.bireysel_dugmesi, m["bireysel_dugme"], "white")
        self.bireysel_aciklama_etiketi.set_text(m["bireysel_aciklama"])
        self._dugme_metni_ayarla(self.sinif_mod_dugmesi, m["sinif_mod_dugme"], "white")
        self.sinif_mod_aciklama_etiketi.set_text(m["sinif_mod_aciklama"])
        self._dugme_metni_ayarla(self.geri_dugmesi_sinif, m["geri"], self._geri_metin_rengi)
        self._dugme_metni_ayarla(self.geri_dugmesi_bireysel, m["geri"], self._geri_metin_rengi)
        self.bireysel_bilgi_etiketi.set_text(m["bireysel_bilgi"])
        self._gecmis_ozetini_yenile()
        self._dugme_metni_ayarla(self.teste_basla_dugmesi, m["teste_basla"], "white")
        self.adres_girisi.set_placeholder_text(m["ogretmen_adres"])
        self.kod_girisi.set_placeholder_text(m["oda_kodu"])
        self.sifre_girisi.set_placeholder_text(m["oda_sifre"])
        self.ad_girisi.set_placeholder_text(m["ad"])
        self.katil_dugmesi.set_label(m["baglan"])
        self.senaryo_baslik_etiketi.set_text(m["senaryo_basligi"])
        self.ipucu_dugmesi.set_label(m["ipucu_goster"])
        self.cevap_girisi.set_placeholder_text(m["cevap_yer_tut"])
        self.gonder_dugmesi.set_label(m["gonder"])
        self.kontrol_dugmesi.set_label(m["kontrol_et"])
        self.atla_dugmesi.set_label(m["atla_dugmesi"])
        # Sohbet widget'ları görev sayfasıyla birlikte oluşuyor; bağlantı
        # sayfasındayken henüz yoklar, o yüzden hasattr ile koru.
        if hasattr(self, "sohbet_baslik_etiketi"):
            self.sohbet_baslik_etiketi.set_label(m["sohbet_basligi"])
        if self.gorev_verisi:
            senaryo = self.gorev_verisi["senaryo"][self.dil]
            ipucu = self.gorev_verisi["ipucu"][self.dil]
            # Port çakışması yüzünden gerçek port değiştiyse, öğrenciye
            # gösterilen metindeki port numarasını da güncelle -- yoksa
            # öğrenci yanlış porta saldırır.
            hedef = self.gorev_verisi.get("hedef", {})
            tanimli_port = hedef.get("port")
            gercek_port = getattr(self.istemci, "gercek_port", None) if self.istemci else None
            if tanimli_port and gercek_port and tanimli_port != gercek_port:
                senaryo = senaryo.replace(str(tanimli_port), str(gercek_port))
                ipucu = ipucu.replace(str(tanimli_port), str(gercek_port))
            self.senaryo_etiketi.set_text(senaryo)
            self.gorev_baslik_etiketi.set_text(self.gorev_verisi["baslik"][self.dil])
            self._ipucu_metni = ipucu
        self._sonuc_etiketini_guncelle()

    def _gecmis_ozetini_yenile(self):
        """Bireysel mod başlangıç ekranındaki kalıcı geçmiş özetini
        (~/.local/share/carotos-poligon/gecmis.json'dan) yeniden okuyup
        çizer. Hem dil değişince (_metinleri_uygula) hem de öğrenci
        'Bireysel Pratik'e her girdiğinde (_bireysel_secildi) çağrılır
        ki bir önceki görevin sonucu sayaca hemen yansısın."""
        m = METIN[self.dil]
        ozet = gecmis_defteri.ozet()
        if ozet["toplam_tamamlanan"] > 0:
            self.gecmis_ozet_etiketi.set_text(
                m["gecmis_ozet"].format(sayi=ozet["toplam_tamamlanan"], puan=ozet["toplam_puan"])
            )
        else:
            self.gecmis_ozet_etiketi.set_text(m["gecmis_yok"])

    # ------------------------------------------------------------------
    def _mod_secim_sayfasi_olustur(self):
        """Açılışta gösterilen ilk sayfa: Bireysel mi Sınıf mı."""
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        kutu.set_margin_top(50); kutu.set_margin_start(40); kutu.set_margin_end(40)

        self.mod_baslik_etiketi = Gtk.Label(xalign=0.5)
        self.mod_baslik_etiketi.get_style_context().add_class("baslik-sabit")
        kutu.pack_start(self.mod_baslik_etiketi, False, False, 10)

        self.bireysel_dugmesi = Gtk.Button()
        self.bireysel_dugmesi.get_style_context().add_class("vurgu")
        self.bireysel_dugmesi.set_size_request(-1, 56)
        self.bireysel_dugmesi.connect("clicked", self._bireysel_secildi)
        kutu.pack_start(self.bireysel_dugmesi, False, False, 0)

        self.bireysel_aciklama_etiketi = Gtk.Label(xalign=0.5, wrap=True)
        self.bireysel_aciklama_etiketi.get_style_context().add_class("etiket")
        kutu.pack_start(self.bireysel_aciklama_etiketi, False, False, 0)

        self.sinif_mod_dugmesi = Gtk.Button()
        self.sinif_mod_dugmesi.get_style_context().add_class("vurgu")
        self.sinif_mod_dugmesi.set_size_request(-1, 56)
        self.sinif_mod_dugmesi.connect("clicked", self._sinif_modu_secildi)
        kutu.pack_start(self.sinif_mod_dugmesi, False, False, 14)

        self.sinif_mod_aciklama_etiketi = Gtk.Label(xalign=0.5, wrap=True)
        self.sinif_mod_aciklama_etiketi.get_style_context().add_class("etiket")
        kutu.pack_start(self.sinif_mod_aciklama_etiketi, False, False, 0)

        self.yigin.add_named(kutu, "mod_secimi")

    def _bireysel_secildi(self, _düğme):
        self.bireysel_mod = True
        self._gecmis_ozetini_yenile()  # her girişte güncel sayıyı göster
        self.yigin.set_visible_child_name("bireysel_basla")

    def _sinif_modu_secildi(self, _düğme):
        self.bireysel_mod = False
        self.yigin.set_visible_child_name("baglanti")

    def _baglanti_sayfasi_olustur(self):
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        kutu.set_margin_top(30); kutu.set_margin_start(40); kutu.set_margin_end(40)

        self.geri_dugmesi_sinif = Gtk.Button()
        self.geri_dugmesi_sinif.get_style_context().add_class("duz")
        self.geri_dugmesi_sinif.connect("clicked", lambda _b: self.yigin.set_visible_child_name("mod_secimi"))
        kutu.pack_start(self.geri_dugmesi_sinif, False, False, 0)

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        kart.get_style_context().add_class("kart")

        self.adres_girisi = Gtk.Entry()
        self.adres_girisi.set_text("127.0.0.1")
        self.kod_girisi = Gtk.Entry()
        self.sifre_girisi = Gtk.Entry()
        self.ad_girisi = Gtk.Entry()
        for e in (self.adres_girisi, self.kod_girisi, self.sifre_girisi, self.ad_girisi):
            kart.pack_start(e, False, False, 0)

        self.katil_dugmesi = Gtk.Button()
        self.katil_dugmesi.get_style_context().add_class("vurgu")
        self.katil_dugmesi.connect("clicked", self._odaya_katil)
        kart.pack_start(self.katil_dugmesi, False, False, 6)

        self.baglanti_durum_etiketi = Gtk.Label(xalign=0)
        self.baglanti_durum_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.baglanti_durum_etiketi, False, False, 0)

        kutu.pack_start(kart, False, False, 0)
        self.yigin.add_named(kutu, "baglanti")

        # --- Bireysel mod: sadece "başla" butonu, öğretmen bağlantısı yok ---
        bireysel_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        bireysel_kutu.set_margin_top(40); bireysel_kutu.set_margin_start(40); bireysel_kutu.set_margin_end(40)

        self.geri_dugmesi_bireysel = Gtk.Button()
        self.geri_dugmesi_bireysel.get_style_context().add_class("duz")
        self.geri_dugmesi_bireysel.connect("clicked", lambda _b: self.yigin.set_visible_child_name("mod_secimi"))
        bireysel_kutu.pack_start(self.geri_dugmesi_bireysel, False, False, 0)

        bireysel_kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        bireysel_kart.get_style_context().add_class("kart")

        self.bireysel_bilgi_etiketi = Gtk.Label(xalign=0.5, wrap=True)
        bireysel_kart.pack_start(self.bireysel_bilgi_etiketi, False, False, 10)

        # Kalıcı geçmiş özeti -- ~/.local/share/carotos-poligon/gecmis.json
        # üzerinden okunur, dile göre yeniden çizilir (bkz. _metinleri_uygula).
        self.gecmis_ozet_etiketi = Gtk.Label(xalign=0.5, wrap=True)
        self.gecmis_ozet_etiketi.get_style_context().add_class("etiket")
        bireysel_kart.pack_start(self.gecmis_ozet_etiketi, False, False, 0)

        self.teste_basla_dugmesi = Gtk.Button()
        self.teste_basla_dugmesi.get_style_context().add_class("vurgu")
        self.teste_basla_dugmesi.set_size_request(-1, 50)
        self.teste_basla_dugmesi.connect("clicked", self._bireysel_baslat)
        bireysel_kart.pack_start(self.teste_basla_dugmesi, False, False, 0)

        bireysel_kutu.pack_start(bireysel_kart, False, False, 0)
        self.yigin.add_named(bireysel_kutu, "bireysel_basla")

    def _bireysel_baslat(self, _düğme):
        """Bireysel modda: öğretmen sunucusuna HİÇ bağlanmadan, yerel
        görev havuzundan rastgele bir görev seçip direkt başlatır."""
        import random
        gorev_dosyalari = _bireysel_havuz()
        if not gorev_dosyalari:
            return
        secilen = random.choice(gorev_dosyalari).stem

        istemci = PoligonIstemci("", "", "", "bireysel")  # oda bilgisi kullanılmaz
        gorev = istemci.gorevi_yukle(secilen)
        istemci.gorevi_baslat()
        self._katildi(istemci, gorev)

    def _odaya_katil(self, _düğme):
        m = METIN[self.dil]
        adres = self.adres_girisi.get_text().strip()
        adres = adres.replace("http://", "").replace("https://", "").rstrip("/")
        kod = self.kod_girisi.get_text().strip()
        sifre = self.sifre_girisi.get_text().strip()
        ad = self.ad_girisi.get_text().strip()
        if not (adres and kod and sifre and ad):
            self.baglanti_durum_etiketi.set_text(m["hata_alan"])
            return

        self.baglanti_durum_etiketi.set_text(m["baglaniyor"])
        self.katil_dugmesi.set_sensitive(False)

        def arka_planda():
            try:
                istemci = PoligonIstemci(
                    f"http://{adres}:8642", kod, sifre, ad
                )
                basarili, hata_mesaji = istemci.katil()
                if not basarili:
                    GLib.idle_add(self._katilma_reddedildi, hata_mesaji)
                    return
                acik_gorevler = istemci.acik_gorevleri_getir()
                if not acik_gorevler:
                    GLib.idle_add(self._gorev_yok_hatasi)
                    return
                # Şimdilik ilk açık görev otomatik seçiliyor. Öğretmenin
                # birden fazla görev arasından seçim yaptığı arayüz,
                # Bireysel/Sınıf mod tasarımıyla birlikte eklenecek.
                gorev = istemci.gorevi_yukle(acik_gorevler[0])
                istemci.gorevi_baslat()
                GLib.idle_add(self._katildi, istemci, gorev)
            except BaglantiHatasi:
                GLib.idle_add(self._katilma_hatasi)

        threading.Thread(target=arka_planda, daemon=True).start()

    def _katilma_reddedildi(self, hata_mesaji: str):
        """Sunucu katılmayı reddetti -- yanlış şifre veya isim çakışması --
        YA DA sunucuya hiç ulaşılamadı (bkz. ogrenci_istemci.py::katil()
        içindeki "__BAGLANTI_HATASI__" işaret kodu). İşaret kodu görülürse
        arayüz kendi dilinde gösterir; sunucudan gelen gerçek bir reddetme
        mesajı ise (yanlış şifre vb.) olduğu gibi gösterilir -- o mesaj
        öğretmenin kendi sunucusundan geliyor, ayrı bir konu."""
        if hata_mesaji == "__BAGLANTI_HATASI__":
            hata_mesaji = METIN[self.dil]["hata_baglanti"]
        self.baglanti_durum_etiketi.set_text(hata_mesaji)
        self.katil_dugmesi.set_sensitive(True)

    def _gorev_yok_hatasi(self):
        self.baglanti_durum_etiketi.set_text(
            "Öğretmen henüz bir görev açmadı" if self.dil == "tr"
            else "The teacher hasn't opened a task yet"
        )
        self.katil_dugmesi.set_sensitive(True)

    def _katilma_hatasi(self):
        self.baglanti_durum_etiketi.set_text(METIN[self.dil]["hata_baglanti"])
        self.katil_dugmesi.set_sensitive(True)

    def _gorev_dugmelerini_guncelle(self, gorev: dict):
        """cevap kutusu+Gönder mi, yoksa Kontrol Et düğmesi mi
        gösterilecek -- görevin dogrulama.tur'una bakarak karar verir.
        Hem ilk katılımda (_katildi) hem görev değişince/atlanınca
        (_otomatik_gorev_gecisi, _gorevi_atla) çağrılır."""
        dogrulama_turu = (gorev or {}).get("dogrulama", {}).get("tur", "kullanici_girdisi")
        if dogrulama_turu in ("ufw_engeli", "fail2ban_durumu"):
            self.cevap_girisi.hide()
            self.gonder_dugmesi.hide()
            self.kontrol_dugmesi.show()
            self.kontrol_dugmesi.set_sensitive(True)
        else:
            self.cevap_girisi.show()
            self.gonder_dugmesi.show()
            self.kontrol_dugmesi.hide()

    def _katildi(self, istemci, gorev):
        self.istemci = istemci
        self.gorev_verisi = gorev
        self._metinleri_uygula()
        self.yigin.set_visible_child_name("gorev")
        self._gorev_dugmelerini_guncelle(gorev)

        if self.bireysel_mod:
            self.sohbet_kart.hide()  # bireysel modda öğretmen yok, not paneli anlamsız
            self.atla_dugmesi.show()
        else:
            self.sohbet_kart.show()
            self.atla_dugmesi.hide()
            self._sohbeti_ciz()  # boş not günlüğünü göster
            self._ipucu_izlemeyi_baslat()

    def _gorevi_atla(self, _düğme):
        """Bireysel modda: mevcut görevi bırakıp rastgele başka bir
        göreve geçer. Çözemeyen öğrenci için çıkış yolu."""
        import random
        if self.istemci:
            self.istemci._bildir("atlandi")  # kalıcı geçmişe düşsün
            self.istemci.gorevi_durdur()
        gorev_dosyalari = [
            g for g in _bireysel_havuz()
            if g.stem != (self.gorev_verisi or {}).get("id")
        ]
        if not gorev_dosyalari:
            gorev_dosyalari = _bireysel_havuz()
        secilen = random.choice(gorev_dosyalari).stem

        istemci = PoligonIstemci("", "", "", "bireysel")
        gorev = istemci.gorevi_yukle(secilen)
        istemci.gorevi_baslat()
        self._son_sonuc = None
        self.cevap_girisi.set_text("")
        self.gonder_dugmesi.set_sensitive(True)
        self.ipucu_etiketi.set_text("")
        self._katildi(istemci, gorev)

    # ------------------------------------------------------------------
    def _gorev_sayfasi_olustur(self):
        self.gorev_verisi = None
        self._ipucu_metni = ""
        self._son_sonuc = None  # None | True | False -- dil değişiminde yeniden çizmek için

        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        kutu.set_margin_top(20); kutu.set_margin_start(30); kutu.set_margin_end(30)

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        kart.get_style_context().add_class("kart")

        self.gorev_baslik_etiketi = Gtk.Label(xalign=0)
        self.gorev_baslik_etiketi.get_style_context().add_class("baslik")
        kart.pack_start(self.gorev_baslik_etiketi, False, False, 0)

        self.senaryo_baslik_etiketi = Gtk.Label(xalign=0)
        self.senaryo_baslik_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.senaryo_baslik_etiketi, False, False, 4)

        self.senaryo_etiketi = Gtk.Label(xalign=0, wrap=True)
        kart.pack_start(self.senaryo_etiketi, False, False, 0)

        self.ipucu_dugmesi = Gtk.Button()
        self.ipucu_dugmesi.get_style_context().add_class("ikincil")
        self.ipucu_dugmesi.connect("clicked", self._ipucunu_goster)
        kart.pack_start(self.ipucu_dugmesi, False, False, 4)

        self.ipucu_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ipucu_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.ipucu_etiketi, False, False, 0)

        self.cevap_girisi = Gtk.Entry()
        kart.pack_start(self.cevap_girisi, False, False, 8)

        self.gonder_dugmesi = Gtk.Button()
        self.gonder_dugmesi.get_style_context().add_class("vurgu")
        self.gonder_dugmesi.connect("clicked", self._cevabi_gonder)
        kart.pack_start(self.gonder_dugmesi, False, False, 0)

        # Sadece savunma görevlerinde (ufw_engeli / fail2ban_durumu)
        # görünür: metin girişi yerine tek düğmeyle root-gerekli kontrol.
        # cevap_girisi + gonder_dugmesi bu görev türünde gizlenir.
        self.kontrol_dugmesi = Gtk.Button()
        self.kontrol_dugmesi.get_style_context().add_class("vurgu")
        self.kontrol_dugmesi.connect("clicked", self._kontrol_et_tiklandi)
        self.kontrol_dugmesi.set_no_show_all(True)
        kart.pack_start(self.kontrol_dugmesi, False, False, 0)

        self.sonuc_etiketi = Gtk.Label(xalign=0)
        kart.pack_start(self.sonuc_etiketi, False, False, 4)

        # Sadece Bireysel modda görünür: çözemeyen öğrenci için çıkış yolu
        self.atla_dugmesi = Gtk.Button()
        self.atla_dugmesi.get_style_context().add_class("duz")
        self.atla_dugmesi.connect("clicked", self._gorevi_atla)
        self.atla_dugmesi.set_no_show_all(True)  # show_all() ile istemsiz görünmesin
        kart.pack_start(self.atla_dugmesi, False, False, 4)

        kutu.pack_start(kart, False, False, 0)

        # --- Öğretmenden gelen notlar: TEK YÖNLÜ günlük (öğrenci yazamaz) ---
        # Bireysel modda hiç öğretmen olmadığı için bu panel gizlenir.
        self.sohbet_kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.sohbet_kart.get_style_context().add_class("kart")

        self.sohbet_baslik_etiketi = Gtk.Label(xalign=0)
        self.sohbet_baslik_etiketi.get_style_context().add_class("baslik")
        self.sohbet_kart.pack_start(self.sohbet_baslik_etiketi, False, False, 0)

        self.sohbet_gecmis_kutusu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sohbet_kaydirma = Gtk.ScrolledWindow()
        sohbet_kaydirma.set_min_content_height(120)
        sohbet_kaydirma.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sohbet_kaydirma.add(self.sohbet_gecmis_kutusu)
        self.sohbet_kart.pack_start(sohbet_kaydirma, True, True, 0)

        kutu.pack_start(self.sohbet_kart, True, True, 8)

        self._sohbet_mesajlari = []  # öğretmenden gelen tüm notlar, birikir
        self.yigin.add_named(kutu, "gorev")

    def _ipucunu_goster(self, _düğme):
        self.ipucu_etiketi.set_text(self._ipucu_metni)

    def _sohbeti_ciz(self):
        """Öğretmenden gelen notların günlüğünü çizer. Tek yönlü --
        öğrenci buradan yazamaz, sadece okur."""
        m = METIN[self.dil]
        for cocuk in list(self.sohbet_gecmis_kutusu.get_children()):
            self.sohbet_gecmis_kutusu.remove(cocuk)
        if not self._sohbet_mesajlari:
            bos = Gtk.Label(label=m["sohbet_bos"], xalign=0, wrap=True)
            bos.get_style_context().add_class("etiket")
            self.sohbet_gecmis_kutusu.pack_start(bos, False, False, 0)
        else:
            for msj in self._sohbet_mesajlari:
                satir = Gtk.Label(xalign=0, wrap=True)
                zaman = msj.get("saat", "")
                satir.set_markup(
                    f"<span size='small' color='#7fa8cc'>{zaman}</span>  "
                    f"{GLib.markup_escape_text(msj['metin'])}"
                )
                satir.get_style_context().add_class("sohbet-ogretmen")
                self.sohbet_gecmis_kutusu.pack_start(satir, False, False, 0)
        self.sohbet_gecmis_kutusu.show_all()

    def _kontrol_et_tiklandi(self, _düğme):
        """Savunma görevleri (ufw_engeli/fail2ban_durumu) için: metin
        cevabı yerine sudo parolası isteyen küçük bir pencere açar,
        sonra doğrulamayı ARKA PLANDA (thread) çalıştırır -- root
        gerektiren subprocess çağrısı UI'yi dondurmasın diye. Aynı
        teknik ogretmen_uygulama.py::OgretmenGirisPenceresi'nde de
        kullanılıyor."""
        m = METIN[self.dil]
        kutu = Gtk.Dialog(title=m["sudo_parola_basligi"], transient_for=self, modal=True)
        kutu.add_buttons(
            m["iptal"], Gtk.ResponseType.CANCEL,
            m["giris_yap"], Gtk.ResponseType.OK,
        )
        alan = kutu.get_content_area()
        alan.set_spacing(8)
        alan.set_margin_top(12); alan.set_margin_bottom(12)
        alan.set_margin_start(16); alan.set_margin_end(16)

        aciklama = Gtk.Label(label=m["sudo_parola_aciklama"], wrap=True, xalign=0)
        alan.pack_start(aciklama, False, False, 0)

        parola_girisi = Gtk.Entry()
        parola_girisi.set_visibility(False)
        parola_girisi.set_placeholder_text(m["sudo_parola_yer_tut"])
        parola_girisi.set_activates_default(True)
        alan.pack_start(parola_girisi, False, False, 4)

        kutu.set_default_response(Gtk.ResponseType.OK)
        kutu.show_all()
        yanit = kutu.run()
        parola = parola_girisi.get_text()
        kutu.destroy()

        if yanit != Gtk.ResponseType.OK or not parola:
            return

        self.kontrol_dugmesi.set_sensitive(False)
        self.sonuc_etiketi.set_text(m["kontrol_ediliyor"])

        dogrulama_turu = self.gorev_verisi["dogrulama"]["tur"]

        def arka_planda():
            if dogrulama_turu == "ufw_engeli":
                basarili, mesaj = self.istemci.ufw_kuralini_dogrula(parola)
            else:  # "fail2ban_durumu"
                basarili, mesaj = self.istemci.fail2ban_durumunu_dogrula(parola)
            GLib.idle_add(self._kontrol_sonucu, basarili, mesaj)

        threading.Thread(target=arka_planda, daemon=True).start()

    def _kontrol_sonucu(self, basarili: bool, mesaj: str):
        m = METIN[self.dil]
        self._son_sonuc = basarili
        baglam = self.sonuc_etiketi.get_style_context()
        baglam.remove_class("durum-dogru")
        baglam.remove_class("durum-yanlis")
        if basarili:
            puan = (self.gorev_verisi or {}).get("puan", 0)
            self.sonuc_etiketi.set_text(f"{m['dogru']} (+{puan} {m['puan']})")
            baglam.add_class("durum-dogru")
            self.kontrol_dugmesi.set_sensitive(False)
        else:
            self.sonuc_etiketi.set_text(f"{m['yanlis']} {mesaj}")
            baglam.add_class("durum-yanlis")
            self.kontrol_dugmesi.set_sensitive(True)
        return False

    def _cevabi_gonder(self, _düğme):
        cevap = self.cevap_girisi.get_text()
        dogru = self.istemci.cevabi_kontrol_et(cevap)
        self._son_sonuc = dogru
        self._sonuc_etiketini_guncelle()
        if dogru:
            self.gonder_dugmesi.set_sensitive(False)

    def _sonuc_etiketini_guncelle(self):
        if self._son_sonuc is None:
            self.sonuc_etiketi.set_text("")
            return
        m = METIN[self.dil]
        baglam = self.sonuc_etiketi.get_style_context()
        baglam.remove_class("durum-dogru")
        baglam.remove_class("durum-yanlis")
        if self._son_sonuc:
            self.sonuc_etiketi.set_text(f"{m['dogru']} (+{self.gorev_verisi['puan']} {m['puan']})")
            baglam.add_class("durum-dogru")
        else:
            self.sonuc_etiketi.set_text(m["yanlis"])
            baglam.add_class("durum-yanlis")

    # ------------------------------------------------------------------
    def _ipucu_izlemeyi_baslat(self):
        def kontrol_et():
            if self.istemci is None:
                return False

            # 1) Öğretmenle bağlantının durumu ne? Bu, görev
            # değişikliği kontrolünden ÖNCE gelmeli -- atılmış ya da
            # odası kapanmış bir öğrenci için görev senkronizasyonuyla
            # uğraşmanın anlamı yok.
            durum = self.istemci.sinif_baglanti_durumu()
            if durum == "atildi":
                self._oturumu_sonlandir(m_anahtar="atildin")
                return False  # döngüyü durdur, artık bu istemci geçersiz
            if durum == "oda_kapandi":
                self._oturumu_sonlandir(m_anahtar="oda_kapandi")
                return False
            if durum == "belirsiz":
                return True  # geçici ağ sorunu, bir sonraki turda tekrar dene

            # 2) Öğretmen sınıfı başka bir göreve geçirdi mi?
            yeni_gorev_id = self.istemci.gorev_degisti_mi()
            if yeni_gorev_id:
                self._otomatik_gorev_gecisi(yeni_gorev_id)
                return True  # görev değiştiyse mesaj kontrolünü bu turda atla

            # 3) Öğretmenden (veya tüm sınıfa) gelen YENİ notları çek.
            yeni = self.istemci.yeni_mesajlari_getir()
            if yeni:
                import time as _time
                for msj in yeni:
                    saat = _time.strftime("%H:%M", _time.localtime(msj.get("zaman", _time.time())))
                    self._sohbet_mesajlari.append({"metin": msj["metin"], "saat": saat})
                self._sohbeti_ciz()
            return True  # tekrarlamaya devam et

        GLib.timeout_add_seconds(3, kontrol_et)

    def _oturumu_sonlandir(self, m_anahtar: str):
        """Öğrenciyi sınıf oturumundan çıkarıp bağlantı ekranına
        döndüren ORTAK akış. İki farklı sebepten çağrılır:
          - 'atildin'      -- öğretmen '✕' ile beni sınıftan attı
                              (sunucu hâlâ yaşıyor, sadece ben listede
                              yokum).
          - 'oda_kapandi'  -- öğretmen uygulamayı tamamen kapattı
                              (sunucuya kesin olarak ulaşılamıyor).
        m_anahtar, METIN sözlüğündeki '{m_anahtar}_basligi' ve
        '{m_anahtar}_mesaji' anahtarlarının ön eki olarak kullanılır."""
        m = METIN[self.dil]
        if self.istemci is not None:
            self.istemci.gorevi_durdur()
        self.istemci = None
        self.gorev_verisi = None
        self._son_sonuc = None
        self._sohbet_mesajlari = []
        self._son_mesaj_no = 0

        iletisim_kutusu = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=m[f"{m_anahtar}_basligi"],
        )
        iletisim_kutusu.format_secondary_text(m[f"{m_anahtar}_mesaji"])
        iletisim_kutusu.add_button(m["tamam"], Gtk.ResponseType.OK)
        iletisim_kutusu.run()
        iletisim_kutusu.destroy()

        # Giriş alanlarını temizle ki aynı isimle tekrar denerken eski
        # değerler kafa karıştırmasın (şifre hariç -- oda şifresi genelde
        # aynı kalır, tekrar yazmak gereksiz sürtünme yaratır).
        self.ad_girisi.set_text("")
        self.katil_dugmesi.set_sensitive(True)
        self.baglanti_durum_etiketi.set_text("")
        self.yigin.set_visible_child_name("baglanti")

    def _otomatik_gorev_gecisi(self, yeni_gorev_id: str):
        """Öğretmen sınıfı başka bir göreve geçirdiğinde çağrılır --
        eski yerel servisi durdurur, yeni görevi yükleyip başlatır,
        ekranı günceller."""
        m = METIN[self.dil]
        yeni_gorev = self.istemci.gorevi_degistir(yeni_gorev_id)
        self.gorev_verisi = yeni_gorev
        self._son_sonuc = None
        self.cevap_girisi.set_text("")
        self.gonder_dugmesi.set_sensitive(True)
        self._gorev_dugmelerini_guncelle(yeni_gorev)
        self._metinleri_uygula()
        # Sohbet günlüğüne sistem notu düş, öğrenci neden ekranın
        # değiştiğini anlasın
        import time as _time
        saat = _time.strftime("%H:%M")
        self._sohbet_mesajlari.append({
            "metin": f"{m['yeni_gorev_bildirimi']} {yeni_gorev['baslik'][self.dil]}",
            "saat": saat,
        })
        self._sohbeti_ciz()


def main():
    pencere = PoligonPenceresi()
    pencere.connect("destroy", Gtk.main_quit)
    pencere.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
