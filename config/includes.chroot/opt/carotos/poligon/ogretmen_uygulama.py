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
import soru_sablonlari as _sablon  # noqa: E402
import soru_defteri as _defter  # noqa: E402


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


def _css_olcekle(css, s):
    """CSS'teki piksel degerlerini s (0.65-1.0) ile carpar ve temel yazi
    boyutunu ayni oranda kucultur. s >= 1 ise HICBIR sey degismez; yani
    normal ekranlarda gorunum eskisiyle birebir ayni kalir. 1px cizgiler
    ile 100px ustu degerler (tam yuvarlak kose) oldugu gibi birakilir."""
    if s >= 0.999:
        return css
    import re

    def _px(eslesme):
        deger = float(eslesme.group(1))
        if deger <= 1 or deger >= 100:
            return eslesme.group(0)
        return "%dpx" % max(1, round(deger * s))

    css = re.sub(r"(\d+(?:\.\d+)?)px", _px, css)
    boyut = 10.0
    try:
        ayar = Gtk.Settings.get_default().get_property("gtk-font-name") or ""
        boyut = float(ayar.rsplit(" ", 1)[-1])
    except (ValueError, TypeError, AttributeError):
        pass
    return css + "\n window { font-size: %.1fpt; }\n" % (boyut * s)


def _ic_kaydirmalari_olcekle(pencere, s):
    """Ic kaydirma alanlarinin KODDA sabit yazilmis en-kucuk yuksekliklerini
    (set_min_content_height) ayni oranla kucultur. Bu degerler CSS'te
    olmadigi icin yazi olcegiyle birlikte kuculmuyor ve kucuk ekranda
    pencere yuksekligini tek baslarina sisiriyorlardi. Taban deger bir kez
    saklanir; boylece her turda ustune ustune kucultulmez."""
    def gez(w):
        if isinstance(w, Gtk.ScrolledWindow):
            taban = getattr(w, "_taban_min_yukseklik", None)
            if taban is None:
                taban = w.get_min_content_height()
                w._taban_min_yukseklik = taban
            if taban > 0:
                w.set_min_content_height(max(80, int(round(taban * s))))
        if isinstance(w, Gtk.Container):
            for c in w.get_children():
                gez(c)
    gez(pencere)


def _olcek_uygula(pencere, icerik, taban_g, taban_y):
    """Pencereyi ekrana sigdirir: yazi, bosluk ve liste yukseklikleri
    birlikte, ayni oranda kuculur -- oranlar bozulmaz.

    Olcek =  min(1, ekran_sinirlari / icerigin gercek en kucuk boyutu),
    alt sinir 0.85. Ekran yetiyorsa olcek 1.00'dir ve GORUNUM DEGISMEZ;
    yani yazi boyutu en fazla mevcut boyut kadardir. Kodda sabit yazilmis
    bosluklar CSS ile kuculmedigi icin tek bir carpan yetmiyor, bu yuzden
    olcup yineliyoruz. 0.85'in altina inilmez (yazi okunmaz olurdu); artan
    fark dikey kaydirma cubuguyla karsilanir.

    ONEMLI: pencere ekrana ciktiktan SONRA cagrilmali. __init__ icinde
    olcmek yanlis sonuc veriyor, cunku Notebook/Stack sayfalari henuz
    gerceklenmedigi icin icerik oldugundan kucuk olculuyor."""
    try:
        from gi.repository import Gdk
        ekran = Gdk.Display.get_default()
        monitor = ekran.get_primary_monitor() or ekran.get_monitor(0)
        alan = monitor.get_workarea()
        sinir_g, sinir_y = alan.width - 40, alan.height - 80

        for _tur in range(6):
            en_kucuk = icerik.get_preferred_size()[0]
            istek_g = max(taban_g, en_kucuk.width)
            istek_y = max(taban_y, en_kucuk.height)
            if istek_g <= sinir_g and istek_y <= sinir_y:
                break
            oran = min(sinir_g / istek_g, sinir_y / istek_y) * 0.98
            s = max(0.85, min(1.0, pencere._olcek * oran))
            if abs(s - pencere._olcek) < 0.005:
                break
            pencere._olcek = s
            pencere._css_uygula()
            _ic_kaydirmalari_olcekle(pencere, s)

        en_kucuk = icerik.get_preferred_size()[0]
        g = min(max(taban_g, en_kucuk.width), sinir_g)
        y = min(max(taban_y, en_kucuk.height), sinir_y)
        if pencere.get_realized():
            pencere.resize(g, y)
        else:
            pencere.set_default_size(g, y)
    except Exception:  # noqa: BLE001 -- olcum basarisizsa taban boyut kalsin
        pencere.set_default_size(taban_g, taban_y)
    return False


def _olcek_planla(pencere, icerik, taban_g, taban_y):
    """Olcegi pencere gorundukten sonra, birkac turda hesaplar.

    Tek tur yetmiyor: CSS ve liste yuksekligi degisince GTK yeni boyut
    istegini hemen degil, bir sonraki dongude hesapliyor. Uc kisa tur,
    olculen boyutun oturmasina izin veriyor."""
    pencere._olcek_turu = 0

    def _adim():
        _olcek_uygula(pencere, icerik, taban_g, taban_y)
        pencere._olcek_turu += 1
        return pencere._olcek_turu < 3

    GLib.timeout_add(150, _adim, priority=GLib.PRIORITY_LOW)


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
        "cevaplari_goster": "Verdiği Cevaplar",
        "cevaplar_kisa": "Cevaplar",
        "cevaplar_baslik": "{ad} — Verdiği Cevaplar",
        "cevaplar_bos": "Bu öğrenci henüz cevap göndermedi.",
        "cevaplar_soru_no": "{n}. soru:",
        "cevaplar_kapat": "Kapat",
        "gonderildi": "İpucu gönderildi",
        "gonderildi_tum": "Tüm sınıfa gönderildi",
        "sekme_ogrenciler": "Öğrenciler",
        "sekme_sinif": "Sorular",
        "sinif_basligi": "Soru Ata",
        "sinif_aciklama": "Seçtiğin görevi ve zorluğu tüm sınıfa 'soru' olarak gönderirsin; her atama sıradaki soru numarasını alır.",
        "siradaki_gorev": "Soruyu Ata (Tüm Sınıf)",
        "soru_atama_durumu": "{n}. soru atandı: {b} · {z}",
        "henuz_soru_yok": "Henüz soru atanmadı.",
        "sekme_soru_olustur": "Soru Oluştur",
        "so_baslik": "Soru Oluştur",
        "so_aciklama": "Bir araç seç, parametreleri belirle (hazır öneriden seç ya da kendin yaz). Doğru cevabı makine üretir; her öğrencide farklı olur.",
        "so_arac_etiketi": "Araç",
        "so_onizle_dugme": "Önizle",
        "so_gonder_dugme": "Sınıfa Gönder",
        "so_ornek_cevap": "Örnek cevap (her öğrencide farklı üretilir): {c}",
        "so_gonderildi": "{n}. soru (özel) atandı: {b} — {e}",
        "so_hata": "Geçersiz değer:",
        "so_ad_etiketi": "Soru adı",
        "so_ad_yer_tut": "İsteğe bağlı (kaydederken görünür)",
        "so_kaydet_dugme": "Kaydet",
        "so_kaydedildi": "Soru kaydedildi (Kaydedilmiş Sorular sekmesinde).",
        "sekme_kayitli": "Kaydedilmiş Sorular",
        "ks_baslik": "Kaydedilmiş Sorular",
        "ks_aciklama": "Kaydettiğin soruları buradan sınıfa gönderebilir ya da silebilirsin.",
        "ks_gonder": "Sınıfa Gönder",
        "ks_sil": "Sil",
        "ks_yenile": "Yenile",
        "ks_bos": "Henüz kayıtlı soru yok. 'Soru Oluştur'da Kaydet'e bas.",
        "sekme_ip": "IP ve Adres",
        "ip_baslik": "Sınıf Hedef Adresi",
        "ip_aciklama": "Görevlerin çalışacağı hedef adresi belirle. Sadece loopback (127.x.x.x) kabul edilir; tüm trafik makinede kalır, dışarı çıkmaz. Ayarladığın adres, AÇIK olan mevcut soru dahil tüm sınıfa anında uygulanır (öğrenciler uyarı alıp görevi yeniden yükler).",
        "ip_mevcut": "Şu anki sınıf hedef adresi: {a}",
        "ip_uret_dugme": "Rastgele Üret",
        "ip_uygula_dugme": "Sınıfa Uygula",
        "ip_varsayilan_dugme": "Varsayılana Dön (127.0.0.1)",
        "ip_uygulandi": "Sınıf hedef adresi ayarlandı: {a} (mevcut açık soru dahil tüm sınıfa uygulandı).",
        "ip_hata": "Geçersiz adres — yalnızca loopback (127.x.x.x) olabilir.",
        "ip_girdi_yer_tut": "örn. 127.45.0.1",
        "alt_sekme_ogrenciler": "Öğrenciler",
        "alt_sekme_sinif": "Sınıf",
        "ozet_baslik": "Sınıf Skor Tablosu",
        "ozet_aciklama": "Öğrenciler puana göre sıralı. Puan = çözülen soruların toplamı (ipucu kullanılan soruda yarı puan).",
        "ozet_bos": "Henüz veri yok.",
        "ozet_s_ad": "Öğrenci",
        "ozet_s_cozulen": "Çözülen",
        "ozet_s_puan": "Puan",
        "ozet_s_deneme": "Deneme",
        "siradaki_gecildi": "Sınıf şu göreve geçirildi:",
        "zorluk_basligi": "Zorluk",
        "zorluk_kolay": "Kolay",
        "zorluk_orta": "Orta",
        "zorluk_zor": "Zor",
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
        "cevaplari_goster": "Submitted Answers",
        "cevaplar_kisa": "Answers",
        "cevaplar_baslik": "{ad} — Submitted Answers",
        "cevaplar_bos": "This student hasn't submitted any answers yet.",
        "cevaplar_soru_no": "Q{n}:",
        "cevaplar_kapat": "Close",
        "gonderildi": "Hint sent",
        "gonderildi_tum": "Sent to the whole class",
        "sekme_ogrenciler": "Students",
        "sekme_sinif": "Questions",
        "sinif_basligi": "Assign Question",
        "sinif_aciklama": "You send the chosen task and difficulty to the whole class as a 'question'; each assignment gets the next question number.",
        "siradaki_gorev": "Assign Question (Whole Class)",
        "soru_atama_durumu": "Question {n} assigned: {b} · {z}",
        "henuz_soru_yok": "No question assigned yet.",
        "sekme_soru_olustur": "Create Question",
        "so_baslik": "Create Question",
        "so_aciklama": "Pick a tool and set the parameters (choose a suggestion or type your own). The machine computes the correct answer; it differs for each student.",
        "so_arac_etiketi": "Tool",
        "so_onizle_dugme": "Preview",
        "so_gonder_dugme": "Send to Class",
        "so_ornek_cevap": "Sample answer (generated differently per student): {c}",
        "so_gonderildi": "Question {n} (custom) assigned: {b} — {e}",
        "so_hata": "Invalid value:",
        "so_ad_etiketi": "Question name",
        "so_ad_yer_tut": "Optional (shown when saved)",
        "so_kaydet_dugme": "Save",
        "so_kaydedildi": "Question saved (see the Saved Questions tab).",
        "sekme_kayitli": "Saved Questions",
        "ks_baslik": "Saved Questions",
        "ks_aciklama": "Send a saved question to the class or delete it from here.",
        "ks_gonder": "Send to Class",
        "ks_sil": "Delete",
        "ks_yenile": "Refresh",
        "ks_bos": "No saved questions yet. Press Save in 'Create Question'.",
        "sekme_ip": "IP & Address",
        "ip_baslik": "Class Target Address",
        "ip_aciklama": "Set the address tasks will run on. Only loopback (127.x.x.x) is allowed; all traffic stays on the machine. The address applies to the whole class immediately, including the currently open question (students get a notice and reload the task).",
        "ip_mevcut": "Current class target address: {a}",
        "ip_uret_dugme": "Generate Random",
        "ip_uygula_dugme": "Apply to Class",
        "ip_varsayilan_dugme": "Reset to Default (127.0.0.1)",
        "ip_uygulandi": "Class target address set: {a} (applied to the whole class, including the current question).",
        "ip_hata": "Invalid address — only loopback (127.x.x.x) is allowed.",
        "ip_girdi_yer_tut": "e.g. 127.45.0.1",
        "alt_sekme_ogrenciler": "Students",
        "alt_sekme_sinif": "Class",
        "ozet_baslik": "Class Scoreboard",
        "ozet_aciklama": "Students sorted by score. Score = total of solved questions (half points when the hint was used).",
        "ozet_bos": "No data yet.",
        "ozet_s_ad": "Student",
        "ozet_s_cozulen": "Solved",
        "ozet_s_puan": "Score",
        "ozet_s_deneme": "Attempts",
        "siradaki_gecildi": "Class advanced to:",
        "zorluk_basligi": "Difficulty",
        "zorluk_kolay": "Easy",
        "zorluk_orta": "Medium",
        "zorluk_zor": "Hard",
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
        # Oda BOS baslar: ogretmen "Soruyu Ata" demeden hicbir gorev acik
        # degildir (ogrenci "ogretmenden soru bekleniyor" ekraninda bekler).
        # gorev_id yalnizca baslangicta hangi radyonun secili gelecegini belirler.
        self._on_secili_gorev = gorev_id
        self._gercek_ip = _yerel_ip_adresini_bul()
        self._ip_gorunur = False
        self.sunucu = sunucu_baslat(self.oda, "0.0.0.0", 8642)

        self._olcek = 1.0  # ekran kucukse __init__ sonunda hesaplanip dusurulur
        self._css_uygula()
        self._arayuzu_kur()
        self._metinleri_uygula()
        _olcek_planla(self, self._ana_kutu, 520, 560)

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

        self._css_saglayici.load_from_data(_css_olcekle(f"""
            window {{ background-color: {KOYU_ZEMIN}; }}
            scrolledwindow.pencere-kaydirma, scrolledwindow.pencere-kaydirma > viewport {{ background-color: {KOYU_ZEMIN}; }}
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
            .alt-sekme-secici {{
                background-color: {giris_zemin}; border-radius: 999px; padding: 3px;
                border: 1px solid {giris_kenar};
            }}
            .alt-sekme-secici button {{
                background-color: transparent; background-image: none;
                border: none; box-shadow: none; border-radius: 999px;
                padding: 4px 20px; margin: 0; min-height: 0; color: {metin_soft};
            }}
            .alt-sekme-secici button label {{ color: {metin_soft}; font-weight: 600; }}
            .alt-sekme-secici button:checked {{ background-color: {VURGU}; }}
            .alt-sekme-secici button:checked label {{ color: white; }}
        """, getattr(self, "_olcek", 1.0)).encode())

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
        self.sekmeler.append_page(self._soru_olustur_sekmesi_olustur(), Gtk.Label(label=""))
        self.sekmeler.append_page(self._kayitli_sorular_sekmesi_olustur(), Gtk.Label(label=""))
        self.sekmeler.append_page(self._ip_adres_sekmesi_olustur(), Gtk.Label(label=""))

        # Kucuk ekranda alt kisimlar disarida kalmasin: icerik kaydirilabilir.
        kaydirma = Gtk.ScrolledWindow()
        kaydirma.get_style_context().add_class("pencere-kaydirma")
        kaydirma.set_shadow_type(Gtk.ShadowType.NONE)
        kaydirma.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._ana_kutu = disKutu  # olcek hesabi icin
        kaydirma.add(disKutu)
        self.add(kaydirma)

    def _soru_olustur_sekmesi_olustur(self) -> Gtk.Widget:
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        icerik.set_margin_top(14); icerik.set_margin_start(16)
        icerik.set_margin_end(16); icerik.set_margin_bottom(14)

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        kart.get_style_context().add_class("kart")

        self.so_baslik_etiketi = Gtk.Label(xalign=0)
        self.so_baslik_etiketi.get_style_context().add_class("baslik-sabit")
        kart.pack_start(self.so_baslik_etiketi, False, False, 0)

        self.so_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.so_aciklama_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.so_aciklama_etiketi, False, False, 0)

        arac_satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.so_arac_etiketi = Gtk.Label(xalign=0)
        self.so_arac_etiketi.get_style_context().add_class("etiket")
        arac_satir.pack_start(self.so_arac_etiketi, False, False, 0)
        self.so_arac_combo = Gtk.ComboBoxText()
        for gid in _sablon.arac_listesi():
            self.so_arac_combo.append(gid, _sablon.SABLONLAR[gid]["baslik"][self.dil])
        self.so_arac_combo.set_active(0)
        self.so_arac_combo.connect("changed", self._so_arac_degisti)
        arac_satir.pack_start(self.so_arac_combo, True, True, 0)
        kart.pack_start(arac_satir, False, False, 0)

        # Secili aracin alanlari bu kutuya dinamik cizilir.
        self.so_alan_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        kart.pack_start(self.so_alan_kutu, False, False, 0)
        self._so_alanlar = []  # [(anahtar, combo_with_entry)]

        ad_satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.so_ad_etiketi = Gtk.Label(xalign=0)
        self.so_ad_etiketi.get_style_context().add_class("etiket")
        ad_satir.pack_start(self.so_ad_etiketi, False, False, 0)
        self.so_ad_girisi = Gtk.Entry()
        ad_satir.pack_start(self.so_ad_girisi, True, True, 0)
        kart.pack_start(ad_satir, False, False, 0)

        dugme_satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.so_onizle_dugmesi = Gtk.Button()
        self.so_onizle_dugmesi.get_style_context().add_class("ikincil")
        self.so_onizle_dugmesi.connect("clicked", self._so_onizle)
        dugme_satir.pack_start(self.so_onizle_dugmesi, False, False, 0)
        self.so_gonder_dugmesi = Gtk.Button()
        self.so_gonder_dugmesi.get_style_context().add_class("vurgu")
        self.so_gonder_dugmesi.connect("clicked", self._so_gonder)
        dugme_satir.pack_start(self.so_gonder_dugmesi, False, False, 0)
        self.so_kaydet_dugmesi = Gtk.Button()
        self.so_kaydet_dugmesi.get_style_context().add_class("ikincil")
        self.so_kaydet_dugmesi.connect("clicked", self._so_kaydet)
        dugme_satir.pack_start(self.so_kaydet_dugmesi, False, False, 0)
        kart.pack_start(dugme_satir, False, False, 6)

        self.so_onizleme_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.so_onizleme_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.so_onizleme_etiketi, False, False, 0)

        self.so_durum_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.so_durum_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.so_durum_etiketi, False, False, 0)

        icerik.pack_start(kart, True, True, 0)
        self._so_alanlari_ciz()  # ilk arac icin alanlari ciz
        return icerik

    def _so_secili_arac(self) -> str:
        return self.so_arac_combo.get_active_id() or _sablon.arac_listesi()[0]

    def _so_alanlari_ciz(self):
        """Secili aracin alan satirlarini (etiket + onerili serbest giris)
        yeniden cizer."""
        for c in list(self.so_alan_kutu.get_children()):
            self.so_alan_kutu.remove(c)
        self._so_alanlar = []
        gid = self._so_secili_arac()
        for alan in _sablon.SABLONLAR[gid]["alanlar"]:
            satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            etiket = Gtk.Label(xalign=0, label=alan["etiket"][self.dil])
            etiket.get_style_context().add_class("etiket")
            etiket.set_size_request(190, -1)
            satir.pack_start(etiket, False, False, 0)
            combo = Gtk.ComboBoxText.new_with_entry()
            for o in _sablon.onerileri_uret(gid, alan["anahtar"]):
                combo.append_text(o)
            combo.get_child().set_text(_sablon.varsayilan(gid, alan["anahtar"]))
            satir.pack_start(combo, True, True, 0)
            self.so_alan_kutu.pack_start(satir, False, False, 0)
            self._so_alanlar.append((alan["anahtar"], combo))
        self.so_alan_kutu.show_all()

    def _so_arac_degisti(self, _combo):
        self._so_alanlari_ciz()
        self.so_onizleme_etiketi.set_text("")
        self.so_durum_etiketi.set_text("")

    def _so_degerleri_topla(self) -> dict:
        return {anahtar: combo.get_child().get_text().strip()
                for anahtar, combo in self._so_alanlar}

    def _so_onizle(self, _w):
        """Secili parametrelerle gorevi YERELDE bir kez calistirip ornek
        cevabi ve senaryo metnini gosterir (ornek cevap her ogrencide farkli)."""
        m = METIN[self.dil]
        gid = self._so_secili_arac()
        try:
            params = _sablon.parametreleri_ayristir(gid, self._so_degerleri_topla())
        except _sablon.GecersizDeger as e:
            self.so_onizleme_etiketi.set_text("")
            self.so_durum_etiketi.set_text(f"{m['so_hata']} {e}")
            return
        from ogrenci_istemci import PoligonIstemci  # GTK'siz, yerel engine
        ist = PoligonIstemci("", "", "", "bireysel")
        ist.ozel_parametreler = params
        ist.sinif_hedef_adres = self.oda.hedef_adres
        ornek, senaryo = "", ""
        try:
            gorev = ist.gorevi_yukle(gid)
            ist.gorevi_baslat()
            ornek = ist._dogru_cevap
            senaryo = gorev["senaryo"][self.dil]
            aralik = ist.aralik_metni()
            if aralik:
                senaryo = senaryo.replace("{aralik}", aralik)
        finally:
            ist.gorevi_durdur()
        self.so_durum_etiketi.set_text("")
        self.so_onizleme_etiketi.set_text(
            senaryo + "\n\n" + m["so_ornek_cevap"].format(c=ornek)
        )

    def _so_gonder(self, _w):
        m = METIN[self.dil]
        gid = self._so_secili_arac()
        try:
            params = _sablon.parametreleri_ayristir(gid, self._so_degerleri_topla())
        except _sablon.GecersizDeger as e:
            self.so_durum_etiketi.set_text(f"{m['so_hata']} {e}")
            return
        etiket = _sablon.etiket_uret(gid, params)
        soru_no = self.oda.ozel_soru_ata(gid, params, etiket)
        baslik = _sablon.SABLONLAR[gid]["baslik"][self.dil]
        self.so_onizleme_etiketi.set_text("")
        self.so_durum_etiketi.set_text(
            m["so_gonderildi"].format(n=soru_no, b=baslik, e=etiket)
        )

    def _so_kaydet(self, _w):
        m = METIN[self.dil]
        gid = self._so_secili_arac()
        try:
            params = _sablon.parametreleri_ayristir(gid, self._so_degerleri_topla())
        except _sablon.GecersizDeger as e:
            self.so_durum_etiketi.set_text(f"{m['so_hata']} {e}")
            return
        ad = self.so_ad_girisi.get_text().strip()
        _defter.kaydet(gid, params, ad)
        self.so_onizleme_etiketi.set_text("")
        self.so_durum_etiketi.set_text(m["so_kaydedildi"])
        if hasattr(self, "ks_liste"):
            self._kayitli_listesini_yenile()

    def _kayitli_sorular_sekmesi_olustur(self) -> Gtk.Widget:
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        icerik.set_margin_top(14); icerik.set_margin_start(16)
        icerik.set_margin_end(16); icerik.set_margin_bottom(14)

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        kart.get_style_context().add_class("kart")

        ust = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.ks_baslik_etiketi = Gtk.Label(xalign=0)
        self.ks_baslik_etiketi.get_style_context().add_class("baslik-sabit")
        ust.pack_start(self.ks_baslik_etiketi, True, True, 0)
        self.ks_yenile_dugmesi = Gtk.Button()
        self.ks_yenile_dugmesi.get_style_context().add_class("ikincil")
        self.ks_yenile_dugmesi.connect("clicked", self._kayitli_listesini_yenile)
        ust.pack_start(self.ks_yenile_dugmesi, False, False, 0)
        kart.pack_start(ust, False, False, 0)

        self.ks_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ks_aciklama_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.ks_aciklama_etiketi, False, False, 0)

        self.ks_liste = Gtk.ListBox()
        self.ks_liste.set_selection_mode(Gtk.SelectionMode.NONE)
        kaydirma = Gtk.ScrolledWindow()
        kaydirma.set_min_content_height(260)
        kaydirma.add(self.ks_liste)
        kart.pack_start(kaydirma, True, True, 0)

        self.ks_durum_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ks_durum_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.ks_durum_etiketi, False, False, 0)

        icerik.pack_start(kart, True, True, 0)
        self._kayitli_listesini_yenile()
        return icerik

    def _kayitli_listesini_yenile(self, *_):
        m = METIN[self.dil]
        for c in list(self.ks_liste.get_children()):
            self.ks_liste.remove(c)
        gorunur = 0
        for kayit in _defter.listele():
            gid = kayit.get("gorev_id")
            if gid not in _sablon.SABLONLAR:
                continue  # artik bilinmeyen arac -- atla
            gorunur += 1
            baslik = _sablon.SABLONLAR[gid]["baslik"][self.dil]
            etiket_metni = _sablon.etiket_uret(gid, kayit.get("parametreler", {}))
            ad = kayit.get("ad") or baslik

            satir = Gtk.ListBoxRow()
            kutu = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            kutu.set_margin_top(4); kutu.set_margin_bottom(4)
            kutu.set_margin_start(6); kutu.set_margin_end(6)
            bilgi = Gtk.Label(xalign=0, wrap=True)
            bilgi.set_markup(
                "<b>%s</b>\n<small>%s — %s</small>"
                % (GLib.markup_escape_text(ad),
                   GLib.markup_escape_text(baslik),
                   GLib.markup_escape_text(etiket_metni))
            )
            kutu.pack_start(bilgi, True, True, 0)
            gonder = Gtk.Button(label=m["ks_gonder"])
            gonder.get_style_context().add_class("vurgu")
            gonder.connect("clicked", self._ks_gonder, kayit)
            kutu.pack_start(gonder, False, False, 0)
            sil = Gtk.Button(label=m["ks_sil"])
            sil.connect("clicked", self._ks_sil, kayit)
            kutu.pack_start(sil, False, False, 0)
            satir.add(kutu)
            self.ks_liste.add(satir)

        if gorunur == 0:
            bos_satir = Gtk.ListBoxRow(selectable=False, activatable=False)
            bos_etiket = Gtk.Label(xalign=0.5, label=m["ks_bos"])
            bos_etiket.get_style_context().add_class("etiket")
            bos_etiket.set_margin_top(16); bos_etiket.set_margin_bottom(16)
            bos_satir.add(bos_etiket)
            self.ks_liste.add(bos_satir)
        self.ks_liste.show_all()

    def _ks_gonder(self, _btn, kayit):
        m = METIN[self.dil]
        gid = kayit["gorev_id"]
        params = kayit.get("parametreler", {})
        etiket = _sablon.etiket_uret(gid, params)
        soru_no = self.oda.ozel_soru_ata(gid, params, etiket)
        baslik = _sablon.SABLONLAR[gid]["baslik"][self.dil]
        self.ks_durum_etiketi.set_text(
            m["so_gonderildi"].format(n=soru_no, b=baslik, e=etiket)
        )

    def _ks_sil(self, _btn, kayit):
        _defter.sil(kayit.get("id", ""))
        self._kayitli_listesini_yenile()

    def _ks_metinleri_uygula(self):
        m = METIN[self.dil]
        self.ks_baslik_etiketi.set_text(m["ks_baslik"])
        self.ks_aciklama_etiketi.set_text(m["ks_aciklama"])
        self.ks_yenile_dugmesi.set_label(m["ks_yenile"])
        self._kayitli_listesini_yenile()

    def _so_metinleri_uygula(self):
        m = METIN[self.dil]
        self.so_baslik_etiketi.set_text(m["so_baslik"])
        self.so_aciklama_etiketi.set_text(m["so_aciklama"])
        self.so_arac_etiketi.set_text(m["so_arac_etiketi"])
        # Arac listesindeki adlar da secili dile gore degissin (satir
        # sirasi ve secili oge ayni kalir; sinyal tetiklenmez).
        for _satir in self.so_arac_combo.get_model():
            _satir[0] = _sablon.SABLONLAR[_satir[1]]["baslik"][self.dil]
        self.so_onizle_dugmesi.set_label(m["so_onizle_dugme"])
        self.so_gonder_dugmesi.set_label(m["so_gonder_dugme"])
        self.so_kaydet_dugmesi.set_label(m["so_kaydet_dugme"])
        self.so_ad_etiketi.set_text(m["so_ad_etiketi"])
        self.so_ad_girisi.set_placeholder_text(m["so_ad_yer_tut"])

    def _ip_adres_sekmesi_olustur(self) -> Gtk.Widget:
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        icerik.set_margin_top(14); icerik.set_margin_start(16)
        icerik.set_margin_end(16); icerik.set_margin_bottom(14)

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        kart.get_style_context().add_class("kart")

        self.ip_baslik_etiketi2 = Gtk.Label(xalign=0)
        self.ip_baslik_etiketi2.get_style_context().add_class("baslik-sabit")
        kart.pack_start(self.ip_baslik_etiketi2, False, False, 0)

        self.ip_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ip_aciklama_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.ip_aciklama_etiketi, False, False, 0)

        self.ip_mevcut_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ip_mevcut_etiketi.get_style_context().add_class("baslik-sabit")
        kart.pack_start(self.ip_mevcut_etiketi, False, False, 6)

        giris_satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.ip_girisi = Gtk.Entry()
        giris_satir.pack_start(self.ip_girisi, True, True, 0)
        self.ip_uret_dugmesi = Gtk.Button()
        self.ip_uret_dugmesi.get_style_context().add_class("ikincil")
        self.ip_uret_dugmesi.connect("clicked", self._ip_rastgele)
        giris_satir.pack_start(self.ip_uret_dugmesi, False, False, 0)
        kart.pack_start(giris_satir, False, False, 0)

        dugme_satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.ip_uygula_dugmesi = Gtk.Button()
        self.ip_uygula_dugmesi.get_style_context().add_class("vurgu")
        self.ip_uygula_dugmesi.connect("clicked", self._ip_uygula)
        dugme_satir.pack_start(self.ip_uygula_dugmesi, False, False, 0)
        self.ip_varsayilan_dugmesi = Gtk.Button()
        self.ip_varsayilan_dugmesi.get_style_context().add_class("ikincil")
        self.ip_varsayilan_dugmesi.connect("clicked", self._ip_varsayilan)
        dugme_satir.pack_start(self.ip_varsayilan_dugmesi, False, False, 0)
        kart.pack_start(dugme_satir, False, False, 6)

        self.ip_durum_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ip_durum_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.ip_durum_etiketi, False, False, 0)

        icerik.pack_start(kart, True, True, 0)
        return icerik

    def _ip_rastgele(self, _w):
        import random
        a = random.randint(1, 254); b = random.randint(0, 254); c = random.randint(1, 254)
        self.ip_girisi.set_text(f"127.{a}.{b}.{c}")

    def _ip_uygula(self, _w):
        m = METIN[self.dil]
        try:
            adres = self.oda.set_hedef_adres(self.ip_girisi.get_text())
        except ValueError:
            self.ip_durum_etiketi.set_text(m["ip_hata"])
            return
        self.ip_durum_etiketi.set_text(m["ip_uygulandi"].format(a=adres))
        self._ip_mevcut_guncelle()

    def _ip_varsayilan(self, _w):
        m = METIN[self.dil]
        adres = self.oda.set_hedef_adres("127.0.0.1")
        self.ip_girisi.set_text(adres)
        self.ip_durum_etiketi.set_text(m["ip_uygulandi"].format(a=adres))
        self._ip_mevcut_guncelle()

    def _ip_mevcut_guncelle(self):
        m = METIN[self.dil]
        self.ip_mevcut_etiketi.set_text(m["ip_mevcut"].format(a=self.oda.hedef_adres))

    def _ip_metinleri_uygula(self):
        m = METIN[self.dil]
        self.ip_baslik_etiketi2.set_text(m["ip_baslik"])
        self.ip_aciklama_etiketi.set_text(m["ip_aciklama"])
        self.ip_uret_dugmesi.set_label(m["ip_uret_dugme"])
        self.ip_uygula_dugmesi.set_label(m["ip_uygula_dugme"])
        self.ip_varsayilan_dugmesi.set_label(m["ip_varsayilan_dugme"])
        self.ip_girisi.set_placeholder_text(m["ip_girdi_yer_tut"])
        self._ip_mevcut_guncelle()

    def _ogrenciler_sekmesi_olustur(self) -> Gtk.Widget:
        # Ic geçiş: üst ana sekmelerle KARIŞMASIN diye notebook DEĞİL --
        # segmentli (pill) aç/kapa düğmeleri + Gtk.Stack.
        dis = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.og_ic_yigin = Gtk.Stack()
        self.og_ic_yigin.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.og_ic_yigin.set_transition_duration(120)
        self.og_ic_yigin.add_named(self._ogrenci_listesi_alt_sekmesi(), "liste")
        self.og_ic_yigin.add_named(self._sinif_ozeti_alt_sekmesi(), "sinif")

        secici = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        secici.get_style_context().add_class("linked")
        secici.get_style_context().add_class("alt-sekme-secici")
        self.og_liste_dugmesi = Gtk.RadioButton.new_with_label(None, "")
        self.og_sinif_dugmesi = Gtk.RadioButton.new_with_label(None, "")
        self.og_sinif_dugmesi.join_group(self.og_liste_dugmesi)
        for d in (self.og_liste_dugmesi, self.og_sinif_dugmesi):
            d.set_mode(False)  # radyo yuvarlağı değil, düğme gibi görün
            d.connect("toggled", self._og_ic_sekme_degis)
        self.og_liste_dugmesi.set_active(True)
        secici.pack_start(self.og_liste_dugmesi, False, False, 0)
        secici.pack_start(self.og_sinif_dugmesi, False, False, 0)

        secici_kutu = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        secici_kutu.set_halign(Gtk.Align.CENTER)
        secici_kutu.set_margin_top(8); secici_kutu.set_margin_bottom(2)
        secici_kutu.pack_start(secici, False, False, 0)

        dis.pack_start(secici_kutu, False, False, 0)
        dis.pack_start(self.og_ic_yigin, True, True, 0)
        return dis

    def _og_ic_sekme_degis(self, dugme):
        # toggled hem eskiyen hem yeni düğmede tetiklenir; sadece aktife tepki ver.
        if not dugme.get_active():
            return
        ad = "sinif" if dugme is self.og_sinif_dugmesi else "liste"
        self.og_ic_yigin.set_visible_child_name(ad)
        if ad == "sinif":
            self._sinif_ozetini_guncelle()

    def _sinif_ozeti_alt_sekmesi(self) -> Gtk.Widget:
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        icerik.set_margin_top(12); icerik.set_margin_start(14)
        icerik.set_margin_end(14); icerik.set_margin_bottom(12)
        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        kart.get_style_context().add_class("kart")
        self.ozet_baslik_etiketi = Gtk.Label(xalign=0)
        self.ozet_baslik_etiketi.get_style_context().add_class("baslik-sabit")
        kart.pack_start(self.ozet_baslik_etiketi, False, False, 0)
        self.ozet_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ozet_aciklama_etiketi.get_style_context().add_class("etiket")
        kart.pack_start(self.ozet_aciklama_etiketi, False, False, 0)
        self.ozet_liste = Gtk.ListBox()
        self.ozet_liste.set_selection_mode(Gtk.SelectionMode.NONE)
        kaydirma = Gtk.ScrolledWindow(); kaydirma.set_min_content_height(300)
        kaydirma.add(self.ozet_liste)
        kart.pack_start(kaydirma, True, True, 0)
        icerik.pack_start(kart, True, True, 0)
        self._sinif_ozetini_guncelle()
        return icerik

    def _ozet_satir_kutu(self, ad_metni, coz, puan, den, kalin=False):
        kutu = Gtk.Box(spacing=8)
        kutu.set_margin_start(6); kutu.set_margin_end(6)
        kutu.set_margin_top(3); kutu.set_margin_bottom(3)
        l_ad = Gtk.Label(xalign=0); l_coz = Gtk.Label(xalign=1)
        l_puan = Gtk.Label(xalign=1); l_den = Gtk.Label(xalign=1)
        l_coz.set_size_request(70, -1); l_puan.set_size_request(70, -1); l_den.set_size_request(80, -1)
        esle = [(l_ad, ad_metni), (l_coz, coz), (l_puan, puan), (l_den, den)]
        for et, metin in esle:
            if kalin:
                et.set_markup("<b>%s</b>" % GLib.markup_escape_text(str(metin)))
            else:
                et.set_text(str(metin))
        kutu.pack_start(l_ad, True, True, 0)
        kutu.pack_start(l_coz, False, False, 0)
        kutu.pack_start(l_puan, False, False, 0)
        kutu.pack_start(l_den, False, False, 0)
        return kutu

    def _sinif_ozetini_guncelle(self):
        if not hasattr(self, "ozet_liste"):
            return
        m = METIN[self.dil]
        for c in list(self.ozet_liste.get_children()):
            self.ozet_liste.remove(c)
        satirlar = self.oda.sinif_ozeti()
        if not satirlar:
            satir = Gtk.ListBoxRow(selectable=False, activatable=False)
            et = Gtk.Label(xalign=0.5, label=m["ozet_bos"])
            et.set_margin_top(16); et.set_margin_bottom(16)
            satir.add(et); self.ozet_liste.add(satir)
            self.ozet_liste.show_all(); return
        # baslik satiri
        bas = Gtk.ListBoxRow(selectable=False, activatable=False)
        bas.add(self._ozet_satir_kutu(m["ozet_s_ad"], m["ozet_s_cozulen"],
                                      m["ozet_s_puan"], m["ozet_s_deneme"], kalin=True))
        self.ozet_liste.add(bas)
        for s in satirlar:
            satir = Gtk.ListBoxRow()
            satir.add(self._ozet_satir_kutu(s["ad"], s["cozulen"], s["puan"], s["deneme"]))
            self.ozet_liste.add(satir)
        self.ozet_liste.show_all()

    def _og_ic_metinleri_uygula(self):
        m = METIN[self.dil]
        self.og_liste_dugmesi.set_label(m["alt_sekme_ogrenciler"])
        self.og_sinif_dugmesi.set_label(m["alt_sekme_sinif"])
        self.ozet_baslik_etiketi.set_text(m["ozet_baslik"])
        self.ozet_aciklama_etiketi.set_text(m["ozet_aciklama"])
        self._sinif_ozetini_guncelle()

    def _ogrenci_listesi_alt_sekmesi(self) -> Gtk.Widget:
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
        # Dil degisince gorev listesindeki metinleri tazeleyen islevler
        # (liste bir kez kurulur; etiketler eskiden hep Turkce kaliyordu).
        self._gorev_dil_yenileyicileri = []

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
                self._gorev_dil_yenileyicileri.append(
                    lambda e=ayirici_etiketi: e.set_markup(
                        f"<span size='small' color='#7fa8cc'>{METIN[self.dil]['savunma_ayirici']}</span>"
                    )
                )
                gorev_listesi_kutusu.add(ayirici_satir)
                savunma_ayirici_eklendi = True

            satir = Gtk.ListBoxRow()
            satir_dis_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            satir_kutu = Gtk.Box(spacing=10)
            satir_kutu.set_margin_top(4)
            satir_kutu.set_margin_start(6); satir_kutu.set_margin_end(6)

            ad_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            ad_etiketi = Gtk.Label(xalign=0)
            ad_etiketi.set_markup(f"<b>{g['baslik'][self.dil]}</b>  ·  {g['arac']}")
            self._gorev_dil_yenileyicileri.append(
                lambda e=ad_etiketi, gv=g: e.set_markup(
                    f"<b>{gv['baslik'][self.dil]}</b>  ·  {gv['arac']}")
            )
            ad_kutu.pack_start(ad_etiketi, False, False, 0)
            if sudo_gerekli:
                not_etiketi = Gtk.Label(xalign=0)
                not_etiketi.set_markup(
                    f"<span size='small' color='#a8c6e0'>{METIN[self.dil]['sudo_gerektirir_notu']}</span>"
                )
                ad_kutu.pack_start(not_etiketi, False, False, 0)
                self._gorev_dil_yenileyicileri.append(
                    lambda e=not_etiketi: e.set_markup(
                        f"<span size='small' color='#a8c6e0'>{METIN[self.dil]['sudo_gerektirir_notu']}</span>"
                    )
                )
            satir_kutu.pack_start(ad_kutu, True, True, 0)

            if ilk_radio is None:
                anahtar = Gtk.RadioButton()
                ilk_radio = anahtar
            else:
                anahtar = Gtk.RadioButton.new_from_widget(ilk_radio)
            anahtar.set_active(g["id"] == self._on_secili_gorev)
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

        # Zorluk seçimi: seçili görev BU zorlukla sınıfa açılır. Makine,
        # doğru cevabı seçilen zorluğun parametrelerine göre üretir.
        # (Zorluk parametresi tanımsız görevlerde etkisizdir; görev yine
        #  servisin kendi varsayılanıyla açılır.)
        self.zorluk_baslik_etiketi = Gtk.Label(xalign=0)
        self.zorluk_baslik_etiketi.get_style_context().add_class("etiket")
        self.zorluk_baslik_etiketi.set_margin_top(6)
        kart.pack_start(self.zorluk_baslik_etiketi, False, False, 0)

        zorluk_kutu = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.zorluk_kolay_radio = Gtk.RadioButton.new_with_label(None, "")
        self.zorluk_orta_radio = Gtk.RadioButton.new_with_label(None, "")
        self.zorluk_orta_radio.join_group(self.zorluk_kolay_radio)
        self.zorluk_zor_radio = Gtk.RadioButton.new_with_label(None, "")
        self.zorluk_zor_radio.join_group(self.zorluk_kolay_radio)
        self.zorluk_orta_radio.set_active(True)
        for r in (self.zorluk_kolay_radio, self.zorluk_orta_radio, self.zorluk_zor_radio):
            zorluk_kutu.pack_start(r, False, False, 0)
        kart.pack_start(zorluk_kutu, False, False, 4)

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
        self.sekmeler.set_tab_label_text(self.sekmeler.get_nth_page(2), m["sekme_soru_olustur"])
        self.sekmeler.set_tab_label_text(self.sekmeler.get_nth_page(3), m["sekme_kayitli"])
        self.sekmeler.set_tab_label_text(self.sekmeler.get_nth_page(4), m["sekme_ip"])
        self._so_metinleri_uygula()
        self._ks_metinleri_uygula()
        self._ip_metinleri_uygula()
        self._og_ic_metinleri_uygula()
        self.sinif_baslik_etiketi.set_text(m["sinif_basligi"])
        self.sinif_aciklama_etiketi.set_text(m["sinif_aciklama"])
        self.siradaki_dugmesi.set_label(m["siradaki_gorev"])
        for _yenile in getattr(self, "_gorev_dil_yenileyicileri", []):
            _yenile()
        self.zorluk_baslik_etiketi.set_text(m["zorluk_basligi"])
        self.zorluk_kolay_radio.set_label(m["zorluk_kolay"])
        self.zorluk_orta_radio.set_label(m["zorluk_orta"])
        self.zorluk_zor_radio.set_label(m["zorluk_zor"])
        if getattr(self, "oda", None) is not None and self.oda.aktif_soru_no == 0:
            self.sinif_durum_etiketi.set_text(m["henuz_soru_yok"])
        self._listeyi_guncelle()

    # ------------------------------------------------------------------
    def _ogrenci_secildi(self, _kutu, satir):
        # Yer tutucu ("kimse yok") satırının ogrenci_adi'si None'dır;
        # onu seçmek gerçek bir seçim değildir, görmezden gel.
        if satir is not None and getattr(satir, "ogrenci_adi", None):
            self.secili_ogrenci = satir.ogrenci_adi
            self._sohbeti_goster()

    def _cevaplari_goster(self, _w, ad=None):
        """Bir ogrencinin verdigi tum cevaplari ayri bir pencerede gosterir.
        Ad satir dugmesinden gelebilir; gelmezse secili ogrenci kullanilir.
        Veri ayni surecte (self.oda) tutuldugu icin HTTP'ye gerek yok."""
        m = METIN[self.dil]
        if ad is None:
            ad = self.secili_ogrenci
        if not ad:
            self.ipucu_durum_etiketi.set_text(m["secim_yok"])
            return
        kayitlar = self.oda.ogrenci_cevaplari(ad)

        pencere = Gtk.Window(title=m["cevaplar_baslik"].format(ad=ad))
        pencere.set_default_size(480, 440)
        pencere.set_transient_for(self)
        dis = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        dis.set_margin_top(12); dis.set_margin_start(12)
        dis.set_margin_end(12); dis.set_margin_bottom(12)

        baslik = Gtk.Label(xalign=0)
        baslik.set_markup("<b>%s</b>" % GLib.markup_escape_text(
            m["cevaplar_baslik"].format(ad=ad)))
        dis.pack_start(baslik, False, False, 0)

        liste = Gtk.ListBox()
        liste.set_selection_mode(Gtk.SelectionMode.NONE)
        if not kayitlar:
            satir = Gtk.ListBoxRow(selectable=False, activatable=False)
            bos = Gtk.Label(xalign=0.5, label=m["cevaplar_bos"])
            bos.set_margin_top(16); bos.set_margin_bottom(16)
            satir.add(bos); liste.add(satir)
        else:
            import time as _t
            for k in kayitlar:
                satir = Gtk.ListBoxRow()
                dogru = k.get("dogru")
                isaret = "✓" if dogru else "✗"
                renk = YESIL if dogru else "#c0546a"
                no = k.get("soru_no", 0)
                no_metni = (m["cevaplar_soru_no"].format(n=no) + " ") if no else ""
                saat = _t.strftime("%H:%M:%S", _t.localtime(k.get("zaman", 0)))
                lbl = Gtk.Label(xalign=0, wrap=True)
                lbl.set_margin_top(3); lbl.set_margin_bottom(3)
                lbl.set_margin_start(6); lbl.set_margin_end(6)
                lbl.set_markup(
                    "<span color='%s'><b>%s</b></span> %s<b>%s</b>  "
                    "<small>%s · %s</small>" % (
                        renk, isaret, GLib.markup_escape_text(no_metni),
                        GLib.markup_escape_text(str(k.get("cevap", ""))),
                        GLib.markup_escape_text(str(k.get("gorev_id", ""))), saat)
                )
                satir.add(lbl); liste.add(satir)
        kaydirma = Gtk.ScrolledWindow(); kaydirma.add(liste)
        dis.pack_start(kaydirma, True, True, 0)

        kapat = Gtk.Button(label=m["cevaplar_kapat"])
        kapat.connect("clicked", lambda *_: pencere.destroy())
        dis.pack_start(kapat, False, False, 0)

        pencere.add(dis)
        pencere.show_all()

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
    def _secili_zorluk(self) -> str:
        """Sınıf sekmesindeki zorluk radyolarından seçili olanı döner."""
        if self.zorluk_kolay_radio.get_active():
            return "kolay"
        if self.zorluk_zor_radio.get_active():
            return "zor"
        return "orta"

    def _secili_goreve_gec(self, _widget):
        """Radio grubunda işaretli olan görevi SEÇİLİ ZORLUKLA açar, diğer
        tüm görevleri kapatır. 'Sıradaki' otomatik hesaplaması yerine
        öğretmenin SEÇTİĞİ görev ve zorluğa gider."""
        m = METIN[self.dil]
        secili_id = None
        for gid, anahtar in self._gorev_anahtarlari.items():
            if anahtar.get_active():
                secili_id = gid
                break

        if secili_id is None:
            return  # radio grubunda teorik olarak hep biri seçili olur

        zorluk = self._secili_zorluk()
        soru_no = self.oda.gorev_ata(secili_id, zorluk)

        secili_gorev = next(g for g in self._tum_gorevler if g["id"] == secili_id)
        zorluk_etiketi = m[f"zorluk_{zorluk}"]
        self.sinif_durum_etiketi.set_text(
            m["soru_atama_durumu"].format(
                n=soru_no, b=secili_gorev["baslik"][self.dil], z=zorluk_etiketi
            )
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

                cevap_dugmesi = Gtk.Button(label=m["cevaplar_kisa"])
                cevap_dugmesi.get_style_context().add_class("ikincil")
                cevap_dugmesi.set_tooltip_text(m["cevaplari_goster"])
                cevap_dugmesi.connect("clicked", self._cevaplari_goster, ad)
                icerik.pack_start(cevap_dugmesi, False, False, 0)

                at_dugmesi = Gtk.Button(label="✕")
                at_dugmesi.get_style_context().add_class("duz")
                at_dugmesi.set_tooltip_text(m["ogrenciyi_at"])
                at_dugmesi.connect("clicked", self._ogrenciyi_at, ad)
                icerik.pack_start(at_dugmesi, False, False, 0)

                satir.add(icerik)
                self.liste_kutusu.add(satir)
                satir.show_all()
                self._satirlar[ad] = {"satir": satir, "durum": durum_etiketi, "sure": sure_etiketi}

        self._sinif_ozetini_guncelle()
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
