#!/usr/bin/env python3
"""
CarotOS Poligon -- ogretmen uygulamasi (GTK3).

Uygulama acilinca ODA HEMEN ACILIR: oda kodu + sifre uretilir, ogretmen
sunucusu baslar. Ogretmen bu kodu ve sifreyi sinifa sesli okur/yansitir.
Ogrenciler kendi uygulamalarindan bu bilgilerle katilir.

Sunucu mantigi (OdaDurumu, sunucu_baslat) zaten ayri test edildi --
bu dosya sadece GORSEL katman. Ogretmen uygulamasi kendi sunucusunun
AYNI SURECINDE calistigi icin HTTP istegi atmadan, dogrudan oda
nesnesinin durumunu okuyor (oda.anlik_goruntu()).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402


def _yerel_ip_adresini_bul() -> str:
    """Bu makinenin yerel agdaki gercek IP adresini bulur. UDP soketiyle
    sahte bir baglanti kurulur; gercekten paket gonderilmez, sadece
    isletim sisteminin hangi ag arayuzunu sececegi ogrenilir -- bu
    yuzden internet baglantisi olmasa bile calisir. Belirlenemezse
    127.0.0.1 doner."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _sistem_dilini_belirle() -> str:
    """ogrenci_uygulama.py::_sistem_dilini_belirle ile AYNI mantık --
    sistem dili Türkçe ise 'tr', değilse 'en'. Bkz. oradaki docstring."""
    for degisken in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        if os.environ.get(degisken, "").lower().startswith("tr"):
            return "tr"
    return "en"


METIN = {
    "tr": {
        "baslik": "CarotOS Poligon — Öğretmen",
        "oda_kodu": "Oda Kodu",
        "oda_sifre": "Oda Şifresi",
        "ip_adresi": "IP Adresi",
        "ogrenciler_basligi": "Öğrenciler",
        "hic_ogrenci_yok": "Henüz kimse katılmadı",
        "durum_basladi": "Başladı",
        "durum_tamamlandi": "Tamamlandı",
        "durum_yanlis": "Yanlış denedi",
        "ipucu_yer_tut": "Seçili öğrenciye ipucu yaz…",
        "tum_sinif_aciklama": "Tüm sınıfta uygula",
        "ipucu_gonder": "İpucu Gönder",
        "secim_yok": "Önce listeden bir öğrenci seç",
        "gonderildi": "İpucu gönderildi",
        "gonderildi_tum": "Tüm sınıfa gönderildi",
        "sekme_ogrenciler": "Öğrenciler",
        "sekme_sinif": "Sınıf",
        "sinif_basligi": "Sınıf Ayarları",
        "sinif_aciklama": "Açtığın görevi tüm sınıf görür.",
        "siradaki_gorev": "Seçili Göreve Geç (Tüm Sınıf)",
        "siradaki_gecildi": "Sınıf şu göreve geçirildi:",
        "sure_sn": "sn",
        "ogrenciyi_at": "Öğrenciyi listeden çıkar",
        "savunma_ayirici": "— Savunma görevleri (öğrencinin sudo yetkisi olmalı) —",
        "sudo_gerektirir_notu": "(Bireysel sudo yetkisi ister)",
    },
    "en": {
        "baslik": "CarotOS Poligon — Teacher",
        "oda_kodu": "Room Code",
        "oda_sifre": "Room Password",
        "ip_adresi": "IP Address",
        "ogrenciler_basligi": "Students",
        "hic_ogrenci_yok": "No one has joined yet",
        "durum_basladi": "Started",
        "durum_tamamlandi": "Completed",
        "durum_yanlis": "Wrong attempt",
        "ipucu_yer_tut": "Type a hint for the selected student…",
        "tum_sinif_aciklama": "Apply to whole class",
        "ipucu_gonder": "Send Hint",
        "secim_yok": "Select a student from the list first",
        "gonderildi": "Hint sent",
        "gonderildi_tum": "Sent to the whole class",
        "sekme_ogrenciler": "Students",
        "sekme_sinif": "Class",
        "sinif_basligi": "Class Settings",
        "sinif_aciklama": "Whatever task you open, the whole class sees it.",
        "siradaki_gorev": "Go to Selected Task (Whole Class)",
        "siradaki_gecildi": "Class advanced to:",
        "sure_sn": "s",
        "ogrenciyi_at": "Remove student from list",
        "savunma_ayirici": "— Defense tasks (student needs sudo access) —",
        "sudo_gerektirir_notu": "(Requires individual sudo access)",
    },
}

KOYU_ZEMIN = "#0b2e52"
KART_ZEMIN = "#123a63"
VURGU = "#378ADA"
YESIL = "#4a9c78"
SARI = "#c9a13b"

DURUM_ANAHTARI = {
    "basladi": "durum_basladi",
    "tamamlandi": "durum_tamamlandi",
    "yanlis_denedi": "durum_yanlis",
}


GOREVLER_DIZINI = Path(__file__).resolve().parent / "gorevler"


def _gorev_sudo_gerektirir_mi(gorev: dict) -> bool:
    """ufw-01/fail2ban-01 gibi görevler öğrencinin KENDİ makinesinde
    sudo yetkisi olmasını gerektirir -- normal 5 görevden farklı bir
    kategori. Sınıf sekmesinde bunlar ayrı gösterilir ve normal
    döngüde (bireysel modun rastgele seçiminde) hiç çıkmazlar; sadece
    öğretmen bilerek seçip 'Uygula' derse sınıfa açılırlar."""
    return gorev.get("dogrulama", {}).get("tur") in ("ufw_engeli", "fail2ban_durumu")


def _tum_gorevleri_yukle() -> list[dict]:
    """gorevler/ klasöründeki tüm geçerli görevleri döner. Sıralama:
    önce normal görevler (seviyeye göre), EN SONDA sudo gerektiren
    savunma görevleri -- sınıf sekmesindeki listede bunlar hep altta,
    bir çizgiyle ayrılmış şekilde görünsün diye. 'Sıradaki göreve geç'
    butonu da bu sırayı kullanır."""
    SEVIYE_SIRASI = {"baslangic": 0, "orta": 1, "ileri": 2}
    gorevler = []
    for dosya in sorted(GOREVLER_DIZINI.glob("*.json")):
        try:
            veri = json.loads(dosya.read_text(encoding="utf-8"))
            if "id" in veri and "arac" in veri:
                gorevler.append(veri)
        except (json.JSONDecodeError, OSError):
            continue
    gorevler.sort(key=lambda g: (
        _gorev_sudo_gerektirir_mi(g),
        SEVIYE_SIRASI.get(g.get("seviye"), 9),
        g["id"],
    ))
    return gorevler


def _ip_gorunurlugu_degistir_metodu(self, _dugme):
    """IP adresini goster/gizle. Varsayilan gizli secildi cunku sinifta
    projeksiyon veya ekran paylasimi acikken bu bilginin yanlislikla
    herkese gorunmesi istenmez; ogretmen bilerek acar."""
    self._ip_gorunur = not self._ip_gorunur
    if self._ip_gorunur:
        self.ip_deger_etiketi.set_text(self._gercek_ip)
        ikon_adi = "view-conceal-symbolic"
    else:
        self.ip_deger_etiketi.set_text("\u2022" * 10)
        ikon_adi = "view-reveal-symbolic"
    self.ip_goz_dugmesi.get_child().destroy()
    self.ip_goz_dugmesi.add(Gtk.Image.new_from_icon_name(ikon_adi, Gtk.IconSize.BUTTON))
    self.ip_goz_dugmesi.show_all()


class OgretmenPenceresi(Gtk.Window):
    _ip_gorunurlugu_degistir = _ip_gorunurlugu_degistir_metodu

    def __init__(self, gorev_id: str = "hydra-01"):
        super().__init__(title="CarotOS Poligon — Öğretmen")
        try:
            self.set_icon_from_file(
                "/usr/share/icons/hicolor/256x256/apps/carotos-poligon-ogretmen.png"
            )
        except GLib.Error:
            pass  # ISO disinda (bagimsiz depodan) calistirilirsa ikon bulunamayabilir
        self.dil = _sistem_dilini_belirle()
        self._css_saglayici = None
        self._geri_metin_rengi = "#a8c6e0"
        self.secili_ogrenci: str | None = None
        self._satirlar: dict = {}  # ad -> {satir, durum etiketi, sure etiketi}
        self._bos_etiket_gosteriliyor = False

        # --- Oda hemen açılır ---
        kod = oda_kodu_uret()
        sifre = oda_sifresi_uret()
        self.oda = OdaDurumu(kod, sifre)
        self.oda.gorev_ac(gorev_id)
        self._gercek_ip = _yerel_ip_adresini_bul()
        self._ip_gorunur = False
        self.sunucu = sunucu_baslat(self.oda, "0.0.0.0", 8642)

        self.set_default_size(520, 560)
        self._css_uygula()
        self._arayuzu_kur()
        self._metinleri_uygula()

        GLib.timeout_add(800, self._listeyi_guncelle)

    # ------------------------------------------------------------------
    def _css_uygula(self):
        """Sabit koyu tema. Tema değiştirme özelliği kaldırıldı."""
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
        liste_hover = "#1a4a7a"
        durum_basladi = "#a8c6e0"
        self._geri_metin_rengi = "#a8c6e0"

        self._css_saglayici.load_from_data(f"""
            window {{ background-color: {KOYU_ZEMIN}; }}
            label {{ color: {metin_ana}; }}
            .kart {{
                background-color: {kart_zemin}; border-radius: 10px; padding: 16px;
                border: 1px solid {kart_kenar};
            }}
            .baslik {{ color: {metin_ana}; font-size: 18px; font-weight: 800; }}
            .baslik-sabit {{ color: #eaf4fc; font-size: 18px; font-weight: 800; }}
            .kod-buyuk {{ color: {VURGU}; font-size: 34px; font-weight: 800; letter-spacing: 2px; }}
            .etiket {{ color: {metin_soft}; font-size: 12px; }}
            .durum-tamamlandi {{ color: {YESIL}; font-weight: 700; }}
            .durum-basladi {{ color: {durum_basladi}; }}
            .durum-yanlis {{ color: {SARI}; }}
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
            button.duz {{
                background-color: transparent; background-image: none;
                border: none; box-shadow: none;
                color: {metin_soft}; padding: 4px 10px;
            }}
            button.duz label {{ color: {metin_soft}; }}
            button.duz-sabit {{
                background-color: transparent; background-image: none;
                border: none; box-shadow: none;
                color: #a8c6e0; padding: 4px 10px;
            }}
            button.duz-sabit label {{ color: #a8c6e0; }}
            list {{ background-color: {kart_zemin}; color: {metin_ana}; border: none; }}
            scrolledwindow, scrolledwindow > viewport {{ background-color: {kart_zemin}; }}
            row {{ background-color: {kart_zemin}; color: {metin_ana}; padding: 2px; }}
            row:hover {{ background-color: {liste_hover}; }}
            row:selected, row:selected:hover {{ background-color: {VURGU}; }}
            row:selected label {{ color: white; }}
        """.encode())

    def _arayuzu_kur(self):
        disKutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        disKutu.set_margin_top(16); disKutu.set_margin_bottom(16)
        disKutu.set_margin_start(20); disKutu.set_margin_end(20)

        # Üst çubuk: başlık + dil + tema
        ust = Gtk.Box(spacing=8)
        self.baslik_etiketi = Gtk.Label(xalign=0)
        self.baslik_etiketi.get_style_context().add_class("baslik-sabit")
        ust.pack_start(self.baslik_etiketi, True, True, 0)
        self.dil_dugmesi = Gtk.Button(label="EN")
        self.dil_dugmesi.get_style_context().add_class("duz-sabit")
        self.dil_dugmesi.connect("clicked", self._dili_degistir)
        ust.pack_end(self.dil_dugmesi, False, False, 0)
        disKutu.pack_start(ust, False, False, 0)

        # Oda bilgisi kartı — her iki sekmede de görünsün diye üstte, sekmelerin dışında
        oda_kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        oda_kart.get_style_context().add_class("kart")

        kod_satiri = Gtk.Box(spacing=20)
        kod_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.kod_baslik_etiketi = Gtk.Label(xalign=0)
        self.kod_baslik_etiketi.get_style_context().add_class("etiket")
        self.kod_deger_etiketi = Gtk.Label(xalign=0, label=self.oda.oda_kodu)
        self.kod_deger_etiketi.get_style_context().add_class("kod-buyuk")
        kod_kutu.pack_start(self.kod_baslik_etiketi, False, False, 0)
        kod_kutu.pack_start(self.kod_deger_etiketi, False, False, 0)
        kod_satiri.pack_start(kod_kutu, False, False, 0)

        sifre_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sifre_baslik_etiketi = Gtk.Label(xalign=0)
        self.sifre_baslik_etiketi.get_style_context().add_class("etiket")
        self.sifre_deger_etiketi = Gtk.Label(xalign=0, label=self.oda.sifre)
        self.sifre_deger_etiketi.get_style_context().add_class("kod-buyuk")
        sifre_kutu.pack_start(self.sifre_baslik_etiketi, False, False, 0)
        sifre_kutu.pack_start(self.sifre_deger_etiketi, False, False, 0)
        kod_satiri.pack_start(sifre_kutu, False, False, 0)
        ip_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.ip_baslik_etiketi = Gtk.Label(xalign=0)
        self.ip_baslik_etiketi.get_style_context().add_class("etiket")
        ip_deger_satiri = Gtk.Box(spacing=6)
        self.ip_deger_etiketi = Gtk.Label(xalign=0, label="\u2022" * 10)
        self.ip_deger_etiketi.get_style_context().add_class("kod-buyuk")
        self.ip_goz_dugmesi = Gtk.Button()
        self.ip_goz_dugmesi.set_relief(Gtk.ReliefStyle.NONE)
        self.ip_goz_dugmesi.add(Gtk.Image.new_from_icon_name(
            "view-reveal-symbolic", Gtk.IconSize.BUTTON
        ))
        self.ip_goz_dugmesi.connect("clicked", self._ip_gorunurlugu_degistir)
        ip_deger_satiri.pack_start(self.ip_deger_etiketi, False, False, 0)
        ip_deger_satiri.pack_start(self.ip_goz_dugmesi, False, False, 0)
        ip_kutu.pack_start(self.ip_baslik_etiketi, False, False, 0)
        ip_kutu.pack_start(ip_deger_satiri, False, False, 0)
        kod_satiri.pack_start(ip_kutu, False, False, 0)
        oda_kart.pack_start(kod_satiri, False, False, 0)
        disKutu.pack_start(oda_kart, False, False, 0)

        # --- Sekmeler: Öğrenciler / Sınıf ---
        self.sekmeler = Gtk.Notebook()
        disKutu.pack_start(self.sekmeler, True, True, 0)

        self.sekmeler.append_page(self._ogrenciler_sekmesi_olustur(), Gtk.Label(label=""))
        self.sekmeler.append_page(self._sinif_sekmesi_olustur(), Gtk.Label(label=""))

        self.add(disKutu)

    def _ogrenciler_sekmesi_olustur(self) -> Gtk.Widget:
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        icerik.set_margin_top(10)

        # Öğrenci listesi kartı
        liste_kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        liste_kart.get_style_context().add_class("kart")

        self.ogrenciler_baslik_etiketi = Gtk.Label(xalign=0)
        self.ogrenciler_baslik_etiketi.get_style_context().add_class("baslik")
        liste_kart.pack_start(self.ogrenciler_baslik_etiketi, False, False, 0)

        self.ilerleme_etiketi = Gtk.Label(xalign=0)
        self.ilerleme_etiketi.get_style_context().add_class("etiket")
        liste_kart.pack_start(self.ilerleme_etiketi, False, False, 0)

        self.liste_kutusu = Gtk.ListBox()
        self.liste_kutusu.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.liste_kutusu.connect("row-selected", self._ogrenci_secildi)
        kaydirma = Gtk.ScrolledWindow()
        kaydirma.set_min_content_height(180)
        kaydirma.add(self.liste_kutusu)
        liste_kart.pack_start(kaydirma, True, True, 0)

        icerik.pack_start(liste_kart, True, True, 0)

        # Sohbet kartı: seçili öğrenciye not gönderme
        sohbet_kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sohbet_kart.get_style_context().add_class("kart")

        self.sohbet_baslik_etiketi = Gtk.Label(xalign=0)
        self.sohbet_baslik_etiketi.get_style_context().add_class("baslik")
        sohbet_kart.pack_start(self.sohbet_baslik_etiketi, False, False, 0)

        self.sohbet_gecmis_kutusu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sohbet_kaydirma = Gtk.ScrolledWindow()
        sohbet_kaydirma.set_min_content_height(110)
        sohbet_kaydirma.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sohbet_kaydirma.add(self.sohbet_gecmis_kutusu)
        sohbet_kart.pack_start(sohbet_kaydirma, True, True, 0)

        tum_sinif_satiri = Gtk.Box(spacing=8)
        self.tum_sinif_kutusu = Gtk.CheckButton()
        tum_sinif_satiri.pack_start(self.tum_sinif_kutusu, False, False, 0)
        self.tum_sinif_aciklama_etiketi = Gtk.Label(xalign=0)
        self.tum_sinif_aciklama_etiketi.get_style_context().add_class("etiket")
        tum_sinif_satiri.pack_start(self.tum_sinif_aciklama_etiketi, False, False, 0)
        sohbet_kart.pack_start(tum_sinif_satiri, False, False, 0)

        giris_satiri = Gtk.Box(spacing=6)
        self.ipucu_girisi = Gtk.Entry()
        self.ipucu_girisi.connect("activate", self._mesaj_gonder)
        giris_satiri.pack_start(self.ipucu_girisi, True, True, 0)
        self.ipucu_gonder_dugmesi = Gtk.Button()
        self.ipucu_gonder_dugmesi.get_style_context().add_class("vurgu")
        self.ipucu_gonder_dugmesi.connect("clicked", self._mesaj_gonder)
        giris_satiri.pack_start(self.ipucu_gonder_dugmesi, False, False, 0)
        sohbet_kart.pack_start(giris_satiri, False, False, 0)

        self.ipucu_durum_etiketi = Gtk.Label(xalign=0)
        self.ipucu_durum_etiketi.get_style_context().add_class("etiket")
        sohbet_kart.pack_start(self.ipucu_durum_etiketi, False, False, 0)

        icerik.pack_start(sohbet_kart, False, False, 0)
        return icerik

    def _sinif_sekmesi_olustur(self) -> Gtk.Widget:
        """Sınıf genelinde ayarlar: hangi görev(ler) açık, sıradaki
        göreve geçme. Öğretmenin tek tek öğrenciyle değil, tüm sınıfla
        ilgilendiği kontroller burada."""
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        icerik.set_margin_top(10)

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        kart.get_style_context().add_class("kart")

        self.sinif_baslik_etiketi = Gtk.Label(xalign=0)
        self.sinif_baslik_etiketi.get_style_context().add_class("baslik")
        kart.pack_start(self.sinif_baslik_etiketi, False, False, 0)

        self.sinif_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.sinif_aciklama_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.sinif_aciklama_etiketi, False, False, 4)

        # Görev listesi: her satırda görev adı + seçim düğmesi.
        # RadioButton grubu -- aynı anda sadece BİR görev seçilebilir.
        # İşaretlemek hemen görevi açmaz, sadece seçimi belirler;
        # gerçek geçiş "Uygula" butonuna basınca olur.
        self._tum_gorevler = _tum_gorevleri_yukle()
        self._gorev_anahtarlari: dict[str, Gtk.RadioButton] = {}

        gorev_listesi_kutusu = Gtk.ListBox()
        gorev_listesi_kutusu.set_selection_mode(Gtk.SelectionMode.NONE)
        ilk_radio = None
        savunma_ayirici_eklendi = False
        for g in self._tum_gorevler:
            sudo_gerekli = _gorev_sudo_gerektirir_mi(g)

            # Normal görevlerden savunma görevlerine geçerken -- bir kez --
            # tıklanamayan bir ayırıcı satır ekle (Uygula'yı etkilemez,
            # sadece görsel gruplama).
            if sudo_gerekli and not savunma_ayirici_eklendi:
                ayirici_satir = Gtk.ListBoxRow(selectable=False, activatable=False)
                ayirici_etiketi = Gtk.Label(xalign=0.5)
                ayirici_etiketi.set_markup(
                    f"<span size='small' color='#7fa8cc'>{METIN[self.dil]['savunma_ayirici']}</span>"
                )
                ayirici_etiketi.set_margin_top(8); ayirici_etiketi.set_margin_bottom(4)
                ayirici_satir.add(ayirici_etiketi)
                gorev_listesi_kutusu.add(ayirici_satir)
                savunma_ayirici_eklendi = True

            satir = Gtk.ListBoxRow()
            satir_dis_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            satir_kutu = Gtk.Box(spacing=10)
            satir_kutu.set_margin_top(4)
            satir_kutu.set_margin_start(6); satir_kutu.set_margin_end(6)

            ad_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            ad_etiketi = Gtk.Label(xalign=0)
            ad_etiketi.set_markup(f"<b>{g['baslik']['tr']}</b>  ·  {g['arac']}")
            ad_kutu.pack_start(ad_etiketi, False, False, 0)
            if sudo_gerekli:
                not_etiketi = Gtk.Label(xalign=0)
                not_etiketi.set_markup(
                    f"<span size='small' color='#a8c6e0'>{METIN[self.dil]['sudo_gerektirir_notu']}</span>"
                )
                ad_kutu.pack_start(not_etiketi, False, False, 0)
            satir_kutu.pack_start(ad_kutu, True, True, 0)

            if ilk_radio is None:
                anahtar = Gtk.RadioButton()
                ilk_radio = anahtar
            else:
                anahtar = Gtk.RadioButton.new_from_widget(ilk_radio)
            anahtar.set_active(g["id"] in self.oda.acik_gorevler)
            satir_kutu.pack_start(anahtar, False, False, 0)
            self._gorev_anahtarlari[g["id"]] = anahtar

            satir_dis_kutu.pack_start(satir_kutu, False, False, 0)
            satir_dis_kutu.set_margin_bottom(4)
            satir.add(satir_dis_kutu)
            gorev_listesi_kutusu.add(satir)

        # Hiçbir görev açık değilse (oda yeni açıldıysa vb.) ilk satır
        # varsayılan seçili olsun -- radio grubunda hep biri işaretli olmalı.
        if not any(a.get_active() for a in self._gorev_anahtarlari.values()) and ilk_radio:
            ilk_radio.set_active(True)

        gorev_kaydirma = Gtk.ScrolledWindow()
        gorev_kaydirma.set_min_content_height(180)
        gorev_kaydirma.add(gorev_listesi_kutusu)
        kart.pack_start(gorev_kaydirma, True, True, 0)

        # Seçili göreve geç ("Uygula")
        self.siradaki_dugmesi = Gtk.Button()
        self.siradaki_dugmesi.get_style_context().add_class("vurgu")
        self.siradaki_dugmesi.connect("clicked", self._secili_goreve_gec)
        kart.pack_start(self.siradaki_dugmesi, False, False, 8)

        self.sinif_durum_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.sinif_durum_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.sinif_durum_etiketi, False, False, 0)

        icerik.pack_start(kart, True, True, 0)
        return icerik

    # ------------------------------------------------------------------
    def _dili_degistir(self, _düğme):
        self.dil = "en" if self.dil == "tr" else "tr"
        self._metinleri_uygula()

    def _metinleri_uygula(self):
        m = METIN[self.dil]
        self.set_title(m["baslik"])
        self.baslik_etiketi.set_text(m["baslik"])
        self.dil_dugmesi.set_label("TR" if self.dil == "en" else "EN")
        self.kod_baslik_etiketi.set_text(m["oda_kodu"])
        self.sifre_baslik_etiketi.set_text(m["oda_sifre"])
        self.ip_baslik_etiketi.set_text(m["ip_adresi"])
        self.ogrenciler_baslik_etiketi.set_text(m["ogrenciler_basligi"])
        self.ipucu_girisi.set_placeholder_text(m["ipucu_yer_tut"])
        self.tum_sinif_aciklama_etiketi.set_label(m["tum_sinif_aciklama"])
        self.ipucu_gonder_dugmesi.set_label(m["ipucu_gonder"])
        self.sekmeler.set_tab_label_text(self.sekmeler.get_nth_page(0), m["sekme_ogrenciler"])
        self.sekmeler.set_tab_label_text(self.sekmeler.get_nth_page(1), m["sekme_sinif"])
        self.sinif_baslik_etiketi.set_text(m["sinif_basligi"])
        self.sinif_aciklama_etiketi.set_text(m["sinif_aciklama"])
        self.siradaki_dugmesi.set_label(m["siradaki_gorev"])
        self._listeyi_guncelle()

    # ------------------------------------------------------------------
    def _ogrenci_secildi(self, _kutu, satir):
        # Yer tutucu ("kimse yok") satırının ogrenci_adi'si None'dır;
        # onu seçmek gerçek bir seçim değildir, görmezden gel.
        if satir is not None and getattr(satir, "ogrenci_adi", None):
            self.secili_ogrenci = satir.ogrenci_adi
            self._sohbeti_goster()

    def _mesaj_gonder(self, _widget):
        m = METIN[self.dil]
        metin = self.ipucu_girisi.get_text().strip()
        if not metin:
            return
        tum_sinifa = self.tum_sinif_kutusu.get_active()
        if tum_sinifa:
            self.oda.mesaj_ekle("tum_sinif", "ogretmen", metin)
            self.ipucu_durum_etiketi.set_text(m["gonderildi_tum"])
        else:
            if not self.secili_ogrenci:
                self.ipucu_durum_etiketi.set_text(m["secim_yok"])
                return
            self.oda.mesaj_ekle(self.secili_ogrenci, "ogretmen", metin)
            self.ipucu_durum_etiketi.set_text(f"{m['gonderildi']}: {self.secili_ogrenci}")
        self.ipucu_girisi.set_text("")
        self._sohbeti_goster()

    def _sohbeti_goster(self):
        """Seçili öğrenciye şimdiye kadar gönderilen notların günlüğü.
        Tek yönlü: sadece öğretmenden gelen mesajlar olur."""
        for cocuk in list(self.sohbet_gecmis_kutusu.get_children()):
            self.sohbet_gecmis_kutusu.remove(cocuk)

        if not self.secili_ogrenci:
            return

        mesajlar = self.oda.sohbet_getir(self.secili_ogrenci, 0)
        for msg in mesajlar:
            tum = " (tüm sınıf)" if msg.get("tum_sinif") else ""
            etk = Gtk.Label(xalign=0, wrap=True)
            etk.set_text(f"{msg['metin']}{tum}")
            etk.get_style_context().add_class("sohbet-ogretmen")
            self.sohbet_gecmis_kutusu.pack_start(etk, False, False, 0)
        self.sohbet_gecmis_kutusu.show_all()

    # ------------------------------------------------------------------
    # Sınıf sekmesi: hangi görevlerin açık olduğu, sıradaki göreve geçiş
    # ------------------------------------------------------------------
    def _secili_goreve_gec(self, _widget):
        """Radio grubunda işaretli olan görevi açar, diğer tüm görevleri
        kapatır. 'Sıradaki' otomatik hesaplaması yerine öğretmenin
        SEÇTİĞİ göreve gider."""
        m = METIN[self.dil]
        secili_id = None
        for gid, anahtar in self._gorev_anahtarlari.items():
            if anahtar.get_active():
                secili_id = gid
                break

        if secili_id is None:
            return  # radio grubunda teorik olarak hep biri seçili olur

        for gid in list(self.oda.acik_gorevler):
            self.oda.gorev_kapat(gid)
        self.oda.gorev_ac(secili_id)

        secili_gorev = next(g for g in self._tum_gorevler if g["id"] == secili_id)
        self.sinif_durum_etiketi.set_text(
            f"{m['siradaki_gecildi']} {secili_gorev['baslik']['tr']}"
        )

    def _listeyi_guncelle(self):
        m = METIN[self.dil]
        gorunum = self.oda.anlik_goruntu()
        ogrenciler = gorunum["ogrenciler"]

        ozet = self.oda.ilerleme_ozeti()
        if ozet["toplam"] > 0:
            self.ilerleme_etiketi.set_text(f"{ozet['tamamlayan']}/{ozet['toplam']} bitirdi")
        else:
            self.ilerleme_etiketi.set_text("")

        # "Kimse yok" durumu: özel bir yer tutucu satır göster
        if not ogrenciler:
            if not self._bos_etiket_gosteriliyor:
                for satir in list(self.liste_kutusu.get_children()):
                    self.liste_kutusu.remove(satir)
                self._satirlar.clear()
                bos = Gtk.ListBoxRow()
                bos.ogrenci_adi = None
                etk = Gtk.Label(label=m["hic_ogrenci_yok"], xalign=0)
                etk.get_style_context().add_class("etiket")
                etk.set_margin_top(6); etk.set_margin_bottom(6)
                etk.set_margin_start(6)
                bos.add(etk)
                self.liste_kutusu.add(bos)
                self.liste_kutusu.show_all()
                self._bos_etiket_gosteriliyor = True
            return True

        # En az bir öğrenci var: yer tutucuyu temizle
        if self._bos_etiket_gosteriliyor:
            for satir in list(self.liste_kutusu.get_children()):
                self.liste_kutusu.remove(satir)
            self._bos_etiket_gosteriliyor = False

        for ad, bilgi in sorted(ogrenciler.items()):
            durum = bilgi["durum"]
            sure = int(bilgi.get("sure_sn", 0))
            durum_metni = m[DURUM_ANAHTARI.get(durum, "durum_basladi")]
            durum_sinifi = {
                "tamamlandi": "durum-tamamlandi",
                "basladi": "durum-basladi",
            }.get(durum, "durum-yanlis")

            if ad in self._satirlar:
                # VAR OLAN satırı güncelle -- silme yok, yani seçim korunur,
                # yanıp sönme olmaz
                kayit = self._satirlar[ad]
                kayit["durum"].set_text(durum_metni)
                kayit["durum"].set_name(durum_sinifi)  # css için
                bag = kayit["durum"].get_style_context()
                for s in ("durum-tamamlandi", "durum-basladi", "durum-yanlis"):
                    bag.remove_class(s)
                bag.add_class(durum_sinifi)
                kayit["sure"].set_text(f"{sure} {m['sure_sn']}")
            else:
                # YENİ öğrenci -- yeni satır ekle
                satir = Gtk.ListBoxRow()
                satir.ogrenci_adi = ad
                icerik = Gtk.Box(spacing=10)
                icerik.set_margin_top(4); icerik.set_margin_bottom(4)
                icerik.set_margin_start(6); icerik.set_margin_end(6)

                ad_etiketi = Gtk.Label(label=ad, xalign=0)
                icerik.pack_start(ad_etiketi, True, True, 0)

                durum_etiketi = Gtk.Label(label=durum_metni, xalign=1)
                durum_etiketi.get_style_context().add_class(durum_sinifi)
                icerik.pack_start(durum_etiketi, False, False, 0)

                sure_etiketi = Gtk.Label(label=f"{sure} {m['sure_sn']}", xalign=1)
                sure_etiketi.get_style_context().add_class("etiket")
                icerik.pack_start(sure_etiketi, False, False, 0)

                at_dugmesi = Gtk.Button(label="✕")
                at_dugmesi.get_style_context().add_class("duz")
                at_dugmesi.set_tooltip_text(m["ogrenciyi_at"])
                at_dugmesi.connect("clicked", self._ogrenciyi_at, ad)
                icerik.pack_start(at_dugmesi, False, False, 0)

                satir.add(icerik)
                self.liste_kutusu.add(satir)
                satir.show_all()
                self._satirlar[ad] = {"satir": satir, "durum": durum_etiketi, "sure": sure_etiketi}

        return True  # zamanlayıcı tekrarlamaya devam etsin

    def _ogrenciyi_at(self, _düğme, ad: str):
        self.oda.ogrenciyi_at(ad)
        if ad in self._satirlar:
            self.liste_kutusu.remove(self._satirlar[ad]["satir"])
            del self._satirlar[ad]
        if self.secili_ogrenci == ad:
            self.secili_ogrenci = None


def _root_parolasi_dogrula(parola: str) -> bool:
    """Sistemin (sudo) parolasını doğrular. Öğretmen uygulaması bu
    doğrulama geçilmeden açılmaz -- öğrencilerin panele erişememesi
    için. Gerçek 'root' hesabı kilitli olabileceğinden (Ubuntu/Debian
    live sistemlerde yaygın), 'su' yerine kullanıcının kendi sudo
    yetkili parolasını doğrulayan 'sudo' tercih edildi."""
    try:
        sonuc = subprocess.run(
            ["sudo", "-S", "-k", "true"],
            input=parola + "\n",
            capture_output=True, text=True, timeout=10,
        )
        return sonuc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


class OgretmenGirisPenceresi(Gtk.Window):
    """Öğretmen uygulaması açılmadan önce gösterilen kimlik doğrulama
    ekranı. Öğrencilerin öğretmen paneline erişip görevleri değiştirmesini
    veya sınıfı yönetmesini engellemek için sistem parolası istenir."""

    def __init__(self, gorev_id: str):
        super().__init__(title="CarotOS Poligon — Öğretmen Girişi")
        try:
            self.set_icon_from_file(
                "/usr/share/icons/hicolor/256x256/apps/carotos-poligon-ogretmen.png"
            )
        except GLib.Error:
            pass  # ISO disinda (bagimsiz depodan) calistirilirsa ikon bulunamayabilir
        self.gorev_id = gorev_id
        self.set_default_size(380, 240)

        css = Gtk.CssProvider()
        css.load_from_data(f"""
            window {{ background-color: {KOYU_ZEMIN}; }}
            label {{ color: #eaf4fc; }}
            entry {{
                background-color: #0e3a68; color: #eaf4fc; border-radius: 6px;
                border: 1px solid rgba(169, 198, 224, 0.25);
            }}
            button.vurgu {{
                background-color: {VURGU}; background-image: none;
                border: none; box-shadow: none;
                color: white; border-radius: 999px; padding: 6px 16px;
            }}
            button.vurgu label {{ color: white; }}
        """.encode())
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        kutu.set_margin_top(36); kutu.set_margin_start(30); kutu.set_margin_end(30)

        baslik = Gtk.Label(xalign=0.5)
        baslik.set_markup("<span size='large' weight='bold'>Öğretmen Girişi</span>")
        kutu.pack_start(baslik, False, False, 0)

        aciklama = Gtk.Label(
            label="Bu panel yalnızca öğretmen içindir.\nDevam etmek için sistem parolanızı girin.",
            xalign=0.5, justify=Gtk.Justification.CENTER,
        )
        kutu.pack_start(aciklama, False, False, 4)

        self.parola_girisi = Gtk.Entry()
        self.parola_girisi.set_visibility(False)  # parola gizlenir
        self.parola_girisi.set_placeholder_text("Parola")
        self.parola_girisi.connect("activate", self._dogrula)
        kutu.pack_start(self.parola_girisi, False, False, 6)

        self.giris_dugmesi = Gtk.Button(label="Giriş Yap")
        self.giris_dugmesi.get_style_context().add_class("vurgu")
        self.giris_dugmesi.connect("clicked", self._dogrula)
        kutu.pack_start(self.giris_dugmesi, False, False, 4)

        self.durum_etiketi = Gtk.Label(label="", xalign=0.5)
        kutu.pack_start(self.durum_etiketi, False, False, 0)

        self.add(kutu)

    def _dogrula(self, _widget):
        parola = self.parola_girisi.get_text()
        if not parola:
            return
        self.giris_dugmesi.set_sensitive(False)
        self.parola_girisi.set_sensitive(False)
        self.durum_etiketi.set_text("Doğrulanıyor…")

        def kontrol_et():
            basarili = _root_parolasi_dogrula(parola)
            GLib.idle_add(self._sonuc, basarili)

        threading.Thread(target=kontrol_et, daemon=True).start()

    def _sonuc(self, basarili: bool):
        if basarili:
            self.destroy()
            _ogretmen_penceresini_ac(self.gorev_id)
        else:
            self.durum_etiketi.set_text("Yanlış parola, tekrar deneyin.")
            self.parola_girisi.set_text("")
            self.parola_girisi.set_sensitive(True)
            self.giris_dugmesi.set_sensitive(True)
            self.parola_girisi.grab_focus()
        return False


def _ogretmen_penceresini_ac(gorev_id: str):
    pencere = OgretmenPenceresi(gorev_id=gorev_id)

    def kapanirken(_pencere):
        pencere.sunucu.shutdown()
        # KRİTİK: sadece shutdown() portu SERBEST BIRAKMAZ -- soket açık
        # kalır, öğrencinin isteği bağlanır ama cevap gelmediği için
        # zaman aşımına uğrar (bu da 'geçici ağ sorunu' ile 'oda
        # gerçekten kapandı' ayrımını imkansız kılar). server_close()
        # soketi gerçekten kapatır, öğrenci tarafında net bir
        # 'connection refused' oluşur -- bkz. ogrenci_istemci.py
        # OdaKapaliHatasi / sinif_baglanti_durumu().
        pencere.sunucu.server_close()
        Gtk.main_quit()

    pencere.connect("destroy", kapanirken)
    pencere.show_all()


def main():
    gorev_id = sys.argv[1] if len(sys.argv) > 1 else "hydra-01"
    giris = OgretmenGirisPenceresi(gorev_id)
    giris.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
