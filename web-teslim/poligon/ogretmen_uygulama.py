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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ortak"))  # ortak grafit tema
from ogretmen_sunucu import OdaDurumu, oda_kodu_uret, oda_sifresi_uret, sunucu_baslat  # noqa: E402
import soru_sablonlari as _sablon  # noqa: E402
import soru_defteri as _defter  # noqa: E402
import gorunum_ayari as _gorunum  # noqa: E402
import gorev_bilgi as _bilgi  # noqa: E402
import varyantlar as _varyantlar  # noqa: E402
import tema  # noqa: E402


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
        "varyant_basligi": "Soru varyantı",
        "varyant_otomatik": "Otomatik (her atamada farklı bir soru)",
        "varyant_notu": "Varyant {v}/{t}",
        "varyant_soru": "Sınıfa sorulan: {s}",
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
        "marka_alt": "Öğretmen",
        "bolum_sinif": "Sınıf",
        "bolum_soru": "Soru bankası",
        "bolum_ayar": "Ayarlar",
        "menu_skor": "Skor Tablosu",
        "oda_acik": "Oda açık · {n} öğrenci",
        "kpi_katilan": "Katılan öğrenci",
        "kpi_bitiren": "Bitirenler",
        "kpi_soru": "Aktif soru no",
        "tema_acik": "Açık tema",
        "tema_koyu": "Koyu tema",
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
        "varyant_basligi": "Question variant",
        "varyant_otomatik": "Automatic (a different question each time)",
        "varyant_notu": "Variant {v}/{t}",
        "varyant_soru": "Asked of the class: {s}",
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
        "marka_alt": "Teacher",
        "bolum_sinif": "Class",
        "bolum_soru": "Question bank",
        "bolum_ayar": "Settings",
        "menu_skor": "Scoreboard",
        "oda_acik": "Room open · {n} students",
        "kpi_katilan": "Students joined",
        "kpi_bitiren": "Finished",
        "kpi_soru": "Active question #",
        "tema_acik": "Light theme",
        "tema_koyu": "Dark theme",
    },
}

VURGU = _gorunum.VURGU   # ortak/tema.py vurgu anahtari (renkler tema.AKTIF'ten okunur)

# Kenar menusu sayfasi -> sayfa basligi metin anahtari
SAYFA_BASLIK = {
    "ogrenciler": "ogrenciler_basligi", "skor": "ozet_baslik",
    "soru_ata": "sinif_basligi", "soru_olustur": "so_baslik",
    "kayitli": "ks_baslik", "ag": "ip_baslik",
}

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
        self.gorunum = _gorunum.gorunum_oku()   # "dark" | "light"
        self._css_saglayici = None
        self.secili_ogrenci: str | None = None
        self.sayfa = "ogrenciler"
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
        self.set_default_size(1060, 720)
        self._arayuzu_kur()
        self._metinleri_uygula()
        self.kabuk.sec("ogrenciler")
        _olcek_planla(self, self.kabuk, 980, 660)

        GLib.timeout_add(800, self._listeyi_guncelle)

    # ------------------------------------------------------------------
    def _css_uygula(self):
        """Ortak grafit tema (ortak/tema.py) + Poligon'a ozgu siniflar.
        Ekran kucukse (_olcek < 1) yazi ve bosluklar ayni oranda kucultulur;
        olcek 1 ise ek saglayici yalnizca Poligon siniflarini tasir."""
        p = tema.uygula(self.gorunum, VURGU)
        ek = _gorunum.poligon_css(p)
        olcek = getattr(self, "_olcek", 1.0)
        if olcek < 0.999:
            ek = tema.css(p) + ek
        if self._css_saglayici is None:
            self._css_saglayici = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(
                self.get_screen(), self._css_saglayici,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
            )
        self._css_saglayici.load_from_data(_css_olcekle(ek, olcek).encode())

    def _arayuzu_kur(self):
        bolumler = [
            ("sinif", [("ogrenciler", "kisi"), ("skor", "rapor"), ("soru_ata", "hedef")]),
            ("soru", [("soru_olustur", "arti"), ("kayitli", "liste")]),
            ("ayar", [("ag", "ag")]),
        ]
        self.kabuk = tema.Kabuk(_gorunum.logo_bul("ogretmen"), bolumler, self._sayfa_secildi)
        self.add(self.kabuk)

        # Ust sag: oda durumu
        self.hap = tema.DurumHapi()
        self.kabuk.ust_sag.pack_start(self.hap, False, False, 0)

        # Sol alt: dil ve gorunum
        alt = Gtk.Box(spacing=8)
        self.dil_dugmesi = Gtk.Button(label="EN")
        self.dil_dugmesi.connect("clicked", self._dili_degistir)
        alt.pack_start(self.dil_dugmesi, True, True, 0)
        self.tema_dugmesi = Gtk.Button()
        self.tema_dugmesi.connect("clicked", self._tema_degistir)
        alt.pack_start(self.tema_dugmesi, True, True, 0)
        self.kabuk.yan_alt.pack_start(alt, False, False, 0)

        # Oda kodu / sifre / IP seridi: her sayfanin ustunde gorunur
        self._oda_seridi = self._oda_seridi_olustur()

        # Sayfalar bir kez kurulur; menuden secilince kabuga takilir.
        liste_sayfasi = self._ogrenciler_sekmesi_olustur()
        self._sayfalar = {
            "ogrenciler": liste_sayfasi,
            "skor": self._skor_sayfasi,
            "soru_ata": self._sinif_sekmesi_olustur(),
            "soru_olustur": self._soru_olustur_sekmesi_olustur(),
            "kayitli": self._kayitli_sorular_sekmesi_olustur(),
            "ag": self._ip_adres_sekmesi_olustur(),
        }
        # Sayfa basligi kabukta; kartlarin kendi basliklari gizlenir
        # (metinleri yine guncellenir, kod yollari degismez).
        for ad in ("ogrenciler_baslik_etiketi", "ilerleme_etiketi", "so_baslik_etiketi",
                   "ks_baslik_etiketi", "ip_baslik_etiketi2", "ozet_baslik_etiketi",
                   "sinif_baslik_etiketi"):
            e = getattr(self, ad)
            e.set_no_show_all(True)
            e.hide()

    def _oda_seridi_olustur(self) -> Gtk.Widget:
        kart = Gtk.Box(spacing=44)
        tema.sinif(kart, "kart oda-seridi")

        def blok(baslik_ad, deger_ad, metin):
            kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            b = Gtk.Label(xalign=0)
            tema.sinif(b, "soluk")
            d = Gtk.Label(xalign=0, label=metin)
            tema.sinif(d, "kod-buyuk")
            setattr(self, baslik_ad, b)
            setattr(self, deger_ad, d)
            kutu.pack_start(b, False, False, 0)
            kutu.pack_start(d, False, False, 0)
            return kutu

        kart.pack_start(blok("kod_baslik_etiketi", "kod_deger_etiketi", self.oda.oda_kodu),
                        False, False, 0)
        kart.pack_start(blok("sifre_baslik_etiketi", "sifre_deger_etiketi", self.oda.sifre),
                        False, False, 0)

        # IP: varsayilan gizli (projeksiyonda yanlislikla gorunmesin)
        ip_kutu = blok("ip_baslik_etiketi", "ip_deger_etiketi", "\u2022" * 10)
        ip_satiri = Gtk.Box(spacing=6)
        deger = self.ip_deger_etiketi
        ip_kutu.remove(deger)
        ip_satiri.pack_start(deger, False, False, 0)
        self.ip_goz_dugmesi = Gtk.Button()
        self.ip_goz_dugmesi.set_relief(Gtk.ReliefStyle.NONE)
        tema.sinif(self.ip_goz_dugmesi, "duz")
        self.ip_goz_dugmesi.add(Gtk.Image.new_from_icon_name(
            "view-reveal-symbolic", Gtk.IconSize.BUTTON))
        self.ip_goz_dugmesi.connect("clicked", self._ip_gorunurlugu_degistir)
        ip_satiri.pack_start(self.ip_goz_dugmesi, False, False, 0)
        ip_kutu.pack_start(ip_satiri, False, False, 0)
        kart.pack_start(ip_kutu, False, False, 0)
        return kart

    def _sayfa_secildi(self, anahtar):
        """Kenar menusunden sayfa secildi: oda seridi + sayfa kabuga takilir."""
        self.sayfa = anahtar
        govde = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        # Eski govde kabuktan atilinca icindekileri de yok eder: butun
        # sayfalari ve seridi ONCE ondan ayir (nesneler self'te yasar).
        for w in (self._oda_seridi, *self._sayfalar.values()):
            ata = w.get_parent()
            if ata is not None:
                ata.remove(w)
        govde.pack_start(self._oda_seridi, False, False, 0)
        govde.pack_start(self._sayfalar[anahtar], True, True, 0)
        self.kabuk.icerik(govde)
        govde.show_all()
        self._baslik_guncelle()

    def _baslik_guncelle(self):
        m = METIN[self.dil]
        self.kabuk.baslik_ayarla(m[SAYFA_BASLIK[self.sayfa]], "")

    def _soru_olustur_sekmesi_olustur(self) -> Gtk.Widget:
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tema.sinif(kart, "kart kart-dolgu")

        self.so_baslik_etiketi = Gtk.Label(xalign=0)
        self.so_baslik_etiketi.get_style_context().add_class("kart-baslik")
        kart.pack_start(self.so_baslik_etiketi, False, False, 0)

        self.so_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.so_aciklama_etiketi.get_style_context().add_class("soluk")
        kart.pack_start(self.so_aciklama_etiketi, False, False, 0)

        arac_satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.so_arac_etiketi = Gtk.Label(xalign=0)
        self.so_arac_etiketi.get_style_context().add_class("soluk")
        arac_satir.pack_start(self.so_arac_etiketi, False, False, 0)
        self.so_arac_combo = tema.AcilirSecim()
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
        self.so_ad_etiketi.get_style_context().add_class("soluk")
        ad_satir.pack_start(self.so_ad_etiketi, False, False, 0)
        self.so_ad_girisi = Gtk.Entry()
        ad_satir.pack_start(self.so_ad_girisi, True, True, 0)
        kart.pack_start(ad_satir, False, False, 0)

        dugme_satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.so_onizle_dugmesi = Gtk.Button()
        self.so_onizle_dugmesi.connect("clicked", self._so_onizle)
        dugme_satir.pack_start(self.so_onizle_dugmesi, False, False, 0)
        self.so_gonder_dugmesi = Gtk.Button()
        self.so_gonder_dugmesi.get_style_context().add_class("ana")
        self.so_gonder_dugmesi.connect("clicked", self._so_gonder)
        dugme_satir.pack_start(self.so_gonder_dugmesi, False, False, 0)
        self.so_kaydet_dugmesi = Gtk.Button()
        self.so_kaydet_dugmesi.connect("clicked", self._so_kaydet)
        dugme_satir.pack_start(self.so_kaydet_dugmesi, False, False, 0)
        kart.pack_start(dugme_satir, False, False, 6)

        self.so_onizleme_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.so_onizleme_etiketi.get_style_context().add_class("soluk")
        kart.pack_start(self.so_onizleme_etiketi, False, False, 0)

        self.so_durum_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.so_durum_etiketi.get_style_context().add_class("soluk")
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
            etiket.get_style_context().add_class("soluk")
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
            ornek = ist._dogru_cevap or "(otomatik doğrulama)"
            senaryo = gorev["senaryo"][self.dil]
            aralik = ist.aralik_metni()
            if aralik:
                senaryo = senaryo.replace("{aralik}", aralik)
            for _k, _v in ist.metin_degiskenleri().items():
                senaryo = senaryo.replace(_k, _v)
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
            + self._varyant_metni(gid)
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

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tema.sinif(kart, "kart kart-dolgu")

        ust = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.ks_baslik_etiketi = Gtk.Label(xalign=0)
        self.ks_baslik_etiketi.get_style_context().add_class("kart-baslik")
        ust.pack_start(self.ks_baslik_etiketi, True, True, 0)
        self.ks_yenile_dugmesi = Gtk.Button()
        self.ks_yenile_dugmesi.connect("clicked", self._kayitli_listesini_yenile)
        ust.pack_start(self.ks_yenile_dugmesi, False, False, 0)
        kart.pack_start(ust, False, False, 0)

        self.ks_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ks_aciklama_etiketi.get_style_context().add_class("soluk")
        kart.pack_start(self.ks_aciklama_etiketi, False, False, 0)

        self.ks_liste = Gtk.ListBox()
        tema.sinif(self.ks_liste, "poligon-liste")
        self.ks_liste.set_selection_mode(Gtk.SelectionMode.NONE)
        kaydirma = Gtk.ScrolledWindow()
        kaydirma.set_min_content_height(260)
        kaydirma.add(self.ks_liste)
        kart.pack_start(kaydirma, True, True, 0)

        self.ks_durum_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ks_durum_etiketi.get_style_context().add_class("soluk")
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
            gonder.get_style_context().add_class("ana")
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
            bos_etiket.get_style_context().add_class("soluk")
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
            + self._varyant_metni(gid)
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
        for gid in _sablon.arac_listesi():
            self.so_arac_combo.metni_degistir(gid, _sablon.SABLONLAR[gid]["baslik"][self.dil])
        self.so_onizle_dugmesi.set_label(m["so_onizle_dugme"])
        self.so_gonder_dugmesi.set_label(m["so_gonder_dugme"])
        self.so_kaydet_dugmesi.set_label(m["so_kaydet_dugme"])
        self.so_ad_etiketi.set_text(m["so_ad_etiketi"])
        self.so_ad_girisi.set_placeholder_text(m["so_ad_yer_tut"])

    def _ip_adres_sekmesi_olustur(self) -> Gtk.Widget:
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tema.sinif(kart, "kart kart-dolgu")

        self.ip_baslik_etiketi2 = Gtk.Label(xalign=0)
        self.ip_baslik_etiketi2.get_style_context().add_class("kart-baslik")
        kart.pack_start(self.ip_baslik_etiketi2, False, False, 0)

        self.ip_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ip_aciklama_etiketi.get_style_context().add_class("soluk")
        kart.pack_start(self.ip_aciklama_etiketi, False, False, 0)

        self.ip_mevcut_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ip_mevcut_etiketi.get_style_context().add_class("kart-baslik")
        kart.pack_start(self.ip_mevcut_etiketi, False, False, 6)

        giris_satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.ip_girisi = Gtk.Entry()
        giris_satir.pack_start(self.ip_girisi, True, True, 0)
        self.ip_uret_dugmesi = Gtk.Button()
        self.ip_uret_dugmesi.connect("clicked", self._ip_rastgele)
        giris_satir.pack_start(self.ip_uret_dugmesi, False, False, 0)
        kart.pack_start(giris_satir, False, False, 0)

        dugme_satir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.ip_uygula_dugmesi = Gtk.Button()
        self.ip_uygula_dugmesi.get_style_context().add_class("ana")
        self.ip_uygula_dugmesi.connect("clicked", self._ip_uygula)
        dugme_satir.pack_start(self.ip_uygula_dugmesi, False, False, 0)
        self.ip_varsayilan_dugmesi = Gtk.Button()
        self.ip_varsayilan_dugmesi.connect("clicked", self._ip_varsayilan)
        dugme_satir.pack_start(self.ip_varsayilan_dugmesi, False, False, 0)
        kart.pack_start(dugme_satir, False, False, 6)

        self.ip_durum_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ip_durum_etiketi.get_style_context().add_class("soluk")
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
        # Skor tablosu ayri bir menu sayfasi: ikisi de burada kurulur,
        # skor sayfasi self._skor_sayfasi'nda beklenir.
        self._skor_sayfasi = self._sinif_ozeti_alt_sekmesi()
        return self._ogrenci_listesi_alt_sekmesi()

    def _sinif_ozeti_alt_sekmesi(self) -> Gtk.Widget:
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tema.sinif(kart, "kart kart-dolgu")
        self.ozet_baslik_etiketi = Gtk.Label(xalign=0)
        self.ozet_baslik_etiketi.get_style_context().add_class("kart-baslik")
        kart.pack_start(self.ozet_baslik_etiketi, False, False, 0)
        self.ozet_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.ozet_aciklama_etiketi.get_style_context().add_class("soluk")
        kart.pack_start(self.ozet_aciklama_etiketi, False, False, 0)
        self.ozet_liste = Gtk.ListBox()
        tema.sinif(self.ozet_liste, "poligon-liste")
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
        self.ozet_baslik_etiketi.set_text(m["ozet_baslik"])
        self.ozet_aciklama_etiketi.set_text(m["ozet_aciklama"])
        self._sinif_ozetini_guncelle()

    def _ogrenci_listesi_alt_sekmesi(self) -> Gtk.Widget:
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Ozet kutulari: katilan / bitiren / aktif soru
        kpi_satiri = Gtk.Box(spacing=12)
        kpi_satiri.set_homogeneous(True)
        self.kpi_katilan = tema.KpiKutusu("")
        self.kpi_bitiren = tema.KpiKutusu("")
        self.kpi_soru = tema.KpiKutusu("")
        for k in (self.kpi_katilan, self.kpi_bitiren, self.kpi_soru):
            kpi_satiri.pack_start(k, True, True, 0)
        icerik.pack_start(kpi_satiri, False, False, 0)

        # Öğrenci listesi kartı
        liste_kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tema.sinif(liste_kart, "kart kart-dolgu")

        self.ogrenciler_baslik_etiketi = Gtk.Label(xalign=0)
        self.ogrenciler_baslik_etiketi.get_style_context().add_class("kart-baslik")
        liste_kart.pack_start(self.ogrenciler_baslik_etiketi, False, False, 0)

        self.ilerleme_etiketi = Gtk.Label(xalign=0)
        self.ilerleme_etiketi.get_style_context().add_class("soluk")
        liste_kart.pack_start(self.ilerleme_etiketi, False, False, 0)

        self.liste_kutusu = Gtk.ListBox()
        tema.sinif(self.liste_kutusu, "poligon-liste")
        self.liste_kutusu.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.liste_kutusu.connect("row-selected", self._ogrenci_secildi)
        kaydirma = Gtk.ScrolledWindow()
        kaydirma.set_min_content_height(180)
        kaydirma.add(self.liste_kutusu)
        liste_kart.pack_start(kaydirma, True, True, 0)

        icerik.pack_start(liste_kart, True, True, 0)

        # Sohbet kartı: seçili öğrenciye not gönderme
        sohbet_kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tema.sinif(sohbet_kart, "kart kart-dolgu")

        self.sohbet_baslik_etiketi = Gtk.Label(xalign=0)
        self.sohbet_baslik_etiketi.get_style_context().add_class("kart-baslik")
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
        self.tum_sinif_aciklama_etiketi.get_style_context().add_class("soluk")
        tum_sinif_satiri.pack_start(self.tum_sinif_aciklama_etiketi, False, False, 0)
        sohbet_kart.pack_start(tum_sinif_satiri, False, False, 0)

        giris_satiri = Gtk.Box(spacing=6)
        self.ipucu_girisi = Gtk.Entry()
        self.ipucu_girisi.connect("activate", self._mesaj_gonder)
        giris_satiri.pack_start(self.ipucu_girisi, True, True, 0)
        self.ipucu_gonder_dugmesi = Gtk.Button()
        self.ipucu_gonder_dugmesi.get_style_context().add_class("ana")
        self.ipucu_gonder_dugmesi.connect("clicked", self._mesaj_gonder)
        giris_satiri.pack_start(self.ipucu_gonder_dugmesi, False, False, 0)
        sohbet_kart.pack_start(giris_satiri, False, False, 0)

        self.ipucu_durum_etiketi = Gtk.Label(xalign=0)
        self.ipucu_durum_etiketi.get_style_context().add_class("soluk")
        sohbet_kart.pack_start(self.ipucu_durum_etiketi, False, False, 0)

        icerik.pack_start(sohbet_kart, False, False, 0)
        return icerik

    def _sinif_sekmesi_olustur(self) -> Gtk.Widget:
        """Sınıf genelinde ayarlar: hangi görev(ler) açık, sıradaki
        göreve geçme. Öğretmenin tek tek öğrenciyle değil, tüm sınıfla
        ilgilendiği kontroller burada."""
        icerik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tema.sinif(kart, "kart kart-dolgu")

        self.sinif_baslik_etiketi = Gtk.Label(xalign=0)
        self.sinif_baslik_etiketi.get_style_context().add_class("kart-baslik")
        kart.pack_start(self.sinif_baslik_etiketi, False, False, 0)

        self.sinif_aciklama_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.sinif_aciklama_etiketi.get_style_context().add_class("soluk")
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
        tema.sinif(gorev_listesi_kutusu, "poligon-liste")
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
                    f"<span size='small' color='{tema.AKTIF['silik']}'>{METIN[self.dil]['savunma_ayirici']}</span>"
                )
                ayirici_etiketi.set_margin_top(8); ayirici_etiketi.set_margin_bottom(4)
                ayirici_satir.add(ayirici_etiketi)
                self._gorev_dil_yenileyicileri.append(
                    lambda e=ayirici_etiketi: e.set_markup(
                        f"<span size='small' color='{tema.AKTIF['silik']}'>{METIN[self.dil]['savunma_ayirici']}</span>"
                    )
                )
                gorev_listesi_kutusu.add(ayirici_satir)
                savunma_ayirici_eklendi = True

            satir = Gtk.ListBoxRow()
            satir_dis_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            satir_kutu = Gtk.Box(spacing=10)
            satir_kutu.set_margin_top(4)
            satir_kutu.set_margin_start(6); satir_kutu.set_margin_end(6)

            # Satırın başındaki bilgi düğmesi: görevin ne işe yaradığını anlatır.
            bilgi_dugmesi = Gtk.Button(label="i")
            tema.sinif(bilgi_dugmesi, "bilgi-dugme")
            bilgi_dugmesi.set_relief(Gtk.ReliefStyle.NONE)
            bilgi_dugmesi.set_valign(Gtk.Align.CENTER)
            bilgi_dugmesi.set_can_focus(False)
            bilgi_dugmesi.connect("clicked", self._bilgi_goster, g)
            satir_kutu.pack_start(bilgi_dugmesi, False, False, 0)

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
                    f"<span size='small' color='{tema.AKTIF['soluk']}'>{METIN[self.dil]['sudo_gerektirir_notu']}</span>"
                )
                ad_kutu.pack_start(not_etiketi, False, False, 0)
                self._gorev_dil_yenileyicileri.append(
                    lambda e=not_etiketi: e.set_markup(
                        f"<span size='small' color='{tema.AKTIF['soluk']}'>{METIN[self.dil]['sudo_gerektirir_notu']}</span>"
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
            anahtar.connect("toggled", self._gorev_secimi_degisti)

            satir_dis_kutu.pack_start(satir_kutu, False, False, 0)
            satir_dis_kutu.set_margin_bottom(4)
            satir.add(satir_dis_kutu)
            gorev_listesi_kutusu.add(satir)

        # Hiçbir görev açık değilse (oda yeni açıldıysa vb.) ilk satır
        # varsayılan seçili olsun -- radio grubunda hep biri işaretli olmalı.
        if not any(a.get_active() for a in self._gorev_anahtarlari.values()) and ilk_radio:
            ilk_radio.set_active(True)

        gorev_kaydirma = Gtk.ScrolledWindow()
        gorev_kaydirma.set_min_content_height(280)
        gorev_kaydirma.add(gorev_listesi_kutusu)
        kart.pack_start(gorev_kaydirma, True, True, 0)

        # Zorluk seçimi: seçili görev BU zorlukla sınıfa açılır. Makine,
        # doğru cevabı seçilen zorluğun parametrelerine göre üretir.
        # (Zorluk parametresi tanımsız görevlerde etkisizdir; görev yine
        #  servisin kendi varsayılanıyla açılır.)
        self.zorluk_baslik_etiketi = Gtk.Label(xalign=0)
        self.zorluk_baslik_etiketi.get_style_context().add_class("soluk")
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

        # Soru varyantı: aynı görevin farklı soruları. 'Otomatik' bilgisayarın
        # her atamada daha önce verilmemiş bir varyant seçmesidir; sınıftaki
        # herkes AYNI varyantı çözer.
        self.varyant_baslik_etiketi = Gtk.Label(xalign=0)
        self.varyant_baslik_etiketi.get_style_context().add_class("soluk")
        self.varyant_baslik_etiketi.set_margin_top(6)
        kart.pack_start(self.varyant_baslik_etiketi, False, False, 0)
        self.varyant_combo = tema.AcilirSecim()
        kart.pack_start(self.varyant_combo, False, False, 4)
        # Varyantı olmayan görevde bu bölümün tamamı gizlenir (show_all açmasın).
        for _w in (self.varyant_baslik_etiketi, self.varyant_combo):
            _w.set_no_show_all(True)
            _w.set_visible(False)

        # Seçili göreve geç ("Uygula")
        self.siradaki_dugmesi = Gtk.Button()
        self.siradaki_dugmesi.get_style_context().add_class("ana")
        self.siradaki_dugmesi.connect("clicked", self._secili_goreve_gec)
        kart.pack_start(self.siradaki_dugmesi, False, False, 8)

        self.sinif_durum_etiketi = Gtk.Label(xalign=0, wrap=True)
        self.sinif_durum_etiketi.get_style_context().add_class("soluk")
        kart.pack_start(self.sinif_durum_etiketi, False, False, 0)

        icerik.pack_start(kart, True, True, 0)
        return icerik

    # ------------------------------------------------------------------
    def _dili_degistir(self, _düğme):
        self.dil = "en" if self.dil == "tr" else "tr"
        self._metinleri_uygula()

    def _tema_degistir(self, _düğme):
        self.gorunum = "light" if self.gorunum == "dark" else "dark"
        _gorunum.gorunum_yaz(self.gorunum)
        self._css_uygula()
        self._metinleri_uygula()   # sabit renkli markup'lar yeni paletle yenilenir
        self.queue_draw()

    def _metinleri_uygula(self):
        m = METIN[self.dil]
        self.set_title(m["baslik"])
        self.kabuk.marka_ayarla("Poligon", m["marka_alt"])
        self.kabuk.bolum_metni("sinif", m["bolum_sinif"])
        self.kabuk.bolum_metni("soru", m["bolum_soru"])
        self.kabuk.bolum_metni("ayar", m["bolum_ayar"])
        for _anahtar, _metin in (("ogrenciler", "sekme_ogrenciler"), ("skor", "menu_skor"),
                                 ("soru_ata", "sekme_sinif"), ("soru_olustur", "sekme_soru_olustur"),
                                 ("kayitli", "sekme_kayitli"), ("ag", "sekme_ip")):
            self.kabuk.menu_metni(_anahtar, m[_metin])
        self.dil_dugmesi.set_label("TR" if self.dil == "en" else "EN")
        self.tema_dugmesi.set_label(m["tema_acik"] if self.gorunum == "dark" else m["tema_koyu"])
        self.kpi_katilan.ayarla(ad=m["kpi_katilan"])
        self.kpi_bitiren.ayarla(ad=m["kpi_bitiren"])
        self.kpi_soru.ayarla(ad=m["kpi_soru"])
        self.kod_baslik_etiketi.set_text(m["oda_kodu"])
        self.sifre_baslik_etiketi.set_text(m["oda_sifre"])
        self.ip_baslik_etiketi.set_text(m["ip_adresi"])
        self.ogrenciler_baslik_etiketi.set_text(m["ogrenciler_basligi"])
        self.ipucu_girisi.set_placeholder_text(m["ipucu_yer_tut"])
        self.tum_sinif_aciklama_etiketi.set_label(m["tum_sinif_aciklama"])
        self.ipucu_gonder_dugmesi.set_label(m["ipucu_gonder"])
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
        self.varyant_baslik_etiketi.set_text(m["varyant_basligi"])
        self._varyant_listesini_yenile()
        if getattr(self, "oda", None) is not None and self.oda.aktif_soru_no == 0:
            self.sinif_durum_etiketi.set_text(m["henuz_soru_yok"])
        self._baslik_guncelle()
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
        tema.sinif(liste, "poligon-liste")
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
                renk = tema.AKTIF["yesil"] if dogru else tema.AKTIF["kirmizi"]
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
            etk.set_halign(Gtk.Align.START)
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

    def _bilgi_goster(self, dugme, gorev):
        """Görev satırındaki 'i' düğmesi: görevin amacını, kazanımını ve
        gerçek kullanım alanını küçük bir kutuda gösterir. Metin tıklama
        anında geçerli dilde kurulur."""
        kayit = _bilgi.bilgi_getir(gorev["id"], self.dil)
        if kayit is None:
            return
        etiketler = _bilgi.ALAN_ETIKETLERI[self.dil]
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        kutu.set_margin_top(12); kutu.set_margin_bottom(12)
        kutu.set_margin_start(14); kutu.set_margin_end(14)
        baslik = Gtk.Label(xalign=0, wrap=True)
        tema.sinif(baslik, "kart-baslik")
        baslik.set_text(gorev["baslik"][self.dil])
        kutu.pack_start(baslik, False, False, 0)
        for alan in ("amac", "kazanim", "kullanim"):
            ust = Gtk.Label(xalign=0)
            tema.sinif(ust, "soluk")
            ust.set_markup(f"<small><b>{GLib.markup_escape_text(etiketler[alan].upper())}</b></small>")
            ust.set_margin_top(4)
            kutu.pack_start(ust, False, False, 0)
            govde = Gtk.Label(xalign=0, wrap=True)
            govde.set_max_width_chars(48)
            govde.set_width_chars(48)
            govde.set_text(kayit[alan])
            kutu.pack_start(govde, False, False, 0)
        ust = Gtk.Label(xalign=0)
        tema.sinif(ust, "soluk")
        ust.set_markup(f"<small><b>{GLib.markup_escape_text(_bilgi.CESITLILIK_ETIKETI[self.dil].upper())}</b></small>")
        ust.set_margin_top(4)
        kutu.pack_start(ust, False, False, 0)
        govde = Gtk.Label(xalign=0, wrap=True)
        govde.set_max_width_chars(48)
        govde.set_width_chars(48)
        govde.set_text(_bilgi.cesitlilik_getir(gorev["id"], self.dil))
        kutu.pack_start(govde, False, False, 0)
        kutu.show_all()
        acilir = Gtk.Popover.new(dugme)
        acilir.add(kutu)
        acilir.connect("closed", lambda w: GLib.idle_add(w.destroy))
        acilir.popup()
        self._bilgi_acilir = acilir

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
        varyant = self._secili_varyant()
        soru_no = self.oda.gorev_ata(secili_id, zorluk, varyant)

        secili_gorev = next(g for g in self._tum_gorevler if g["id"] == secili_id)
        zorluk_etiketi = m[f"zorluk_{zorluk}"]
        durum = m["soru_atama_durumu"].format(
            n=soru_no, b=secili_gorev["baslik"][self.dil], z=zorluk_etiketi)
        durum += self._varyant_metni(secili_id)
        self.sinif_durum_etiketi.set_text(durum)

    # --- soru varyantı ---------------------------------------------------
    def _secili_gorev_id(self):
        for gid, anahtar in self._gorev_anahtarlari.items():
            if anahtar.get_active():
                return gid
        return None

    def _gorev_secimi_degisti(self, anahtar):
        if anahtar.get_active():
            self._varyant_listesini_yenile()

    def _varyant_listesini_yenile(self):
        """Seçili görevin varyantlarını açılır listeye doldurur."""
        m = METIN[self.dil]
        gid = self._secili_gorev_id()
        n = _varyantlar.gorev_varyant_sayisi(gid) if gid else 0
        onceki = self.varyant_combo.get_active_id()
        if gid != getattr(self, "_varyant_gorevi", None):
            onceki = None                # baska goreve gecildi: yeniden "Otomatik"
        self._varyant_gorevi = gid
        self.varyant_combo.remove_all()
        if n < 2:
            self.varyant_combo.set_visible(False)
            self.varyant_baslik_etiketi.set_visible(False)
            return
        self.varyant_combo.set_visible(True)
        self.varyant_baslik_etiketi.set_visible(True)
        self.varyant_combo.append("0", m["varyant_otomatik"])
        for no in range(1, n + 1):
            kisa = _varyantlar.gorev_varyant_ozeti(gid, no, self.dil)
            self.varyant_combo.append(str(no), f"{no}. {kisa}")
        self.varyant_combo.set_active_id(onceki if onceki and int(onceki) <= n else "0")

    def _secili_varyant(self):
        """Açılır listedeki seçim: sayı (elle) ya da None (otomatik)."""
        if not self.varyant_combo.get_visible():
            return None
        kimlik = self.varyant_combo.get_active_id()
        return int(kimlik) if kimlik and int(kimlik) > 0 else None

    def _varyant_metni(self, gid):
        """Durum metnine eklenen ' · Varyant 7/20' + sınıfa sorulan soru."""
        m = METIN[self.dil]
        no = self.oda.gorev_varyantlari.get(gid)
        if not no:
            return ""
        toplam = _varyantlar.gorev_varyant_sayisi(gid)
        ek = " · " + m["varyant_notu"].format(v=no, t=toplam)
        soru = _varyantlar.gorev_varyant_aciklamasi(gid, no, self.dil)
        if soru:
            ek += "\n" + m["varyant_soru"].format(s=soru)
        return ek

    def _listeyi_guncelle(self):
        m = METIN[self.dil]
        gorunum = self.oda.anlik_goruntu()
        ogrenciler = gorunum["ogrenciler"]

        ozet = self.oda.ilerleme_ozeti()
        if ozet["toplam"] > 0:
            self.ilerleme_etiketi.set_text(f"{ozet['tamamlayan']}/{ozet['toplam']} bitirdi")
        else:
            self.ilerleme_etiketi.set_text("")
        self.kpi_katilan.ayarla(ozet["toplam"])
        self.kpi_bitiren.ayarla(ozet["tamamlayan"])
        self.kpi_soru.ayarla(self.oda.aktif_soru_no or "—")
        self.hap.ayarla(m["oda_acik"].format(n=len(ogrenciler)), "acik")
        self.kabuk.rozet("ogrenciler", len(ogrenciler) or None, sakin=True)

        # "Kimse yok" durumu: özel bir yer tutucu satır göster
        if not ogrenciler:
            if not self._bos_etiket_gosteriliyor:
                for satir in list(self.liste_kutusu.get_children()):
                    self.liste_kutusu.remove(satir)
                self._satirlar.clear()
                bos = Gtk.ListBoxRow()
                bos.ogrenci_adi = None
                etk = Gtk.Label(label=m["hic_ogrenci_yok"], xalign=0)
                etk.get_style_context().add_class("soluk")
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
            }.get(durum, "durum-deneme")

            if ad in self._satirlar:
                # VAR OLAN satırı güncelle -- silme yok, yani seçim korunur,
                # yanıp sönme olmaz
                kayit = self._satirlar[ad]
                kayit["durum"].set_text(durum_metni)
                kayit["durum"].set_name(durum_sinifi)  # css için
                bag = kayit["durum"].get_style_context()
                for s in ("durum-tamamlandi", "durum-basladi", "durum-deneme"):
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
                sure_etiketi.get_style_context().add_class("soluk")
                icerik.pack_start(sure_etiketi, False, False, 0)

                cevap_dugmesi = Gtk.Button(label=m["cevaplar_kisa"])
                cevap_dugmesi.get_style_context().add_class("kucuk")
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
        self.set_default_size(440, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        tema.uygula(_gorunum.gorunum_oku(), VURGU)

        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        kutu.set_margin_top(32); kutu.set_margin_bottom(28)
        kutu.set_margin_start(36); kutu.set_margin_end(36)

        ikon = tema.ikon_kutusu("kilit", "vurgu", 60)
        ikon.set_halign(Gtk.Align.CENTER)
        kutu.pack_start(ikon, False, False, 4)

        baslik = Gtk.Label(xalign=0.5, label="Öğretmen Girişi")
        tema.sinif(baslik, "buyuk-baslik")
        kutu.pack_start(baslik, False, False, 0)

        aciklama = Gtk.Label(
            label="Bu panel yalnızca öğretmen içindir.\nDevam etmek için sistem parolanızı girin.",
            xalign=0.5, justify=Gtk.Justification.CENTER,
        )
        tema.sinif(aciklama, "soluk")
        kutu.pack_start(aciklama, False, False, 4)

        self.parola_girisi = Gtk.Entry()
        self.parola_girisi.set_visibility(False)  # parola gizlenir
        self.parola_girisi.set_placeholder_text("Parola")
        self.parola_girisi.connect("activate", self._dogrula)
        kutu.pack_start(self.parola_girisi, False, False, 6)

        self.giris_dugmesi = Gtk.Button(label="Giriş Yap")
        self.giris_dugmesi.get_style_context().add_class("ana")
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
            tema.sinif(self.durum_etiketi, "hata-yazi")
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
