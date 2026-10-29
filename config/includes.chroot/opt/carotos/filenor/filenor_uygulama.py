#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CarotOS Filenor -- dosya biçimi dönüştürücü ve araç kutusu (GTK 3).

Özgün Filenor (MiracLight, MIT) CarotOS tasarım diline taşındı ve genişletildi:
  * Dönüştür:  görsel, ses, video, PDF, ofis belgeleri, tablolar, sunumlar,
               yazı tipleri; sürükle-bırak, toplu işlem, ilerleme, iptal
  * Araçlar:   PDF birleştir / böl / sayfa seç / döndür / küçült / kilitle,
               OCR, görsel küçült-temizle, ses-video kırp
  * Ayarlar:   dil, görünüm, çıktı klasörü, kurulu araçların durumu

Arayüz yalnızca gösterimdir; bütün iş filenor_motor / filenor_araclar'dadır
(GTK'siz, test edilir). Uzun işler iş parçacığında çalışır; arayüze
GLib.idle_add ile dönülür.

Kullanım:
    filenor [DOSYA ...]        arayüzü açar (dosyalar listeye eklenir)
"""

from __future__ import annotations

import os
import sys
import threading

sys.dont_write_bytecode = True

BURASI = os.path.dirname(os.path.abspath(__file__))
ORTAK = os.path.join(os.path.dirname(BURASI), "ortak")
for _yol in (ORTAK, BURASI):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

import tema  # noqa: E402
import filenor_araclar as A  # noqa: E402
import filenor_motor as M  # noqa: E402
import filenor_kurulum as K  # noqa: E402
import filenor_sistem as S  # noqa: E402
from filenor_dil import FilenorHata, hata_metni  # noqa: E402
from filenor_metin import METIN  # noqa: E402

APP_VERSION = "2.0"

BOLUMLER = [
    ("calisma", [("donustur", "yenile"), ("araclar", "arac")]),
    ("sistem", [("ayar", "ayar")]),
]

ROZET_RENK = {"gorsel": "mavi", "ham": "mavi", "svg": "mavi", "video": "vurgu", "ses": "sari", "pdf": "kirmizi",
              "yazidoc": "kirmizi", "txt": "gri", "html": "gri", "tablo": "yesil", "sunum": "sari",
              "yazitipi": "gri", "": "gri"}

# Seçeneklerin hangi bileşenle gösterileceği: (anahtar, tür, parametreler)
SECENEK_TANIM = {
    "kalite": ("secim", [("yuksek", "kal_yuksek"), ("dengeli", "kal_dengeli"), ("kucuk", "kal_kucuk")]),
    "max_kenar": ("sayi", (0, 16000, 10)),
    "meta_temizle": ("anahtar", None),
    "dpi": ("sayi", (36, 600, 10)),
    "sayfa_araligi": ("giris", False),
    "parola": ("giris", True),
    "yeni_parola": ("giris", True),
    "ocr_dil": ("giris", False),
    "ocr_cikti": ("secim", [("txt", "ocr_txt"), ("pdf", "ocr_pdf")]),
    "gif_fps": ("sayi", (1, 30, 1)),
    "gif_genislik": ("sayi", (32, 1920, 20)),
    "derece": ("secim", [("90", "der_90"), ("180", "der_180"), ("270", "der_270")]),
    "parca": ("sayi", (1, 999, 1)),
    "baslangic": ("sayi", (0, 86400, 1)),
    "bitis": ("sayi", (0, 86400, 1)),
    "zip_yap": ("anahtar", None),
}


def dil_varsayilan() -> str:
    return S.sistem_dili()


def _yuklenebilir(yol: str) -> bool:
    """Simge dosyası gerçekten açılıyor mu? (SVG için gdk-pixbuf svg yükleyicisi gerekir)"""
    try:
        from gi.repository import GdkPixbuf
        GdkPixbuf.Pixbuf.new_from_file_at_size(yol, 32, 32)
        return True
    except Exception:
        return False


def logo_bul():
    kok = os.path.abspath(os.path.join(BURASI, "..", "..", ".."))
    for yol in (os.path.join(kok, "usr/share/icons/hicolor/256x256/apps/filenor.png"),
                "/usr/share/icons/hicolor/256x256/apps/filenor.png",
                # PNG'ler ISO derlenirken açılır; depodan çalışırken vektör simge kullanılır
                os.path.join(kok, "usr/share/icons/hicolor/scalable/apps/filenor.svg"),
                "/usr/share/icons/hicolor/scalable/apps/filenor.svg",
                # bağımsız (GitHub) sürüm: simgeler uygulamanın yanındaki simge/ klasöründe
                os.path.join(BURASI, "simge", "filenor.png"),
                os.path.join(BURASI, "simge", "filenor.svg")):
        if os.path.isfile(yol) and _yuklenebilir(yol):
            return yol
    # son çare: gömülü PNG (hiçbir simge kurulu değilken de pencere simgesi görünsün)
    import filenor_simge
    return filenor_simge.cikar()


def ac(yol: str) -> None:
    """Dosya ya da klasörü varsayılan uygulamayla açar; arayüzü bekletmez."""
    S.ac(yol)


def klasor_dosyalari(klasor: str, sinir: int = 1000) -> list[str]:
    uzantilar = set(M.kaynak_uzantilari())
    sonuc: list[str] = []
    for kok, dizinler, dosyalar in os.walk(klasor):
        dizinler[:] = sorted(d for d in dizinler if not d.startswith("."))
        for d in sorted(dosyalar):
            if d.startswith("."):
                continue
            if M.uzanti(d) in uzantilar:
                sonuc.append(os.path.join(kok, d))
                if len(sonuc) >= sinir:
                    return sonuc
    return sonuc


class Oge:
    """Listedeki tek dosya."""

    def __init__(self, yol: str):
        self.yol = yol
        self.ad = os.path.basename(yol)
        self.ext = M.uzanti(yol)
        self.tur = M.tur(self.ext)
        try:
            self.boyut = os.path.getsize(yol)
        except OSError:
            self.boyut = 0
        self.is_: M.Is | None = None
        self.hata: FilenorHata | None = None   # uyumsuzluk ya da çalışma hatası
        self.durum = "bekliyor"                # bekliyor | calisiyor | tamam | hata | iptal
        self.sonuc: list[str] = []
        self.satir = None


class Panel:
    """Dönüştür ve Araçlar sayfalarının ortak gövdesi. mod: 'donustur' | 'arac'."""

    def __init__(self, uyg: "Uygulama", mod: str):
        self.uyg = uyg
        self.mod = mod
        self.ogeler: list[Oge] = []
        self.hedef: str | None = None          # dönüştür: hedef uzantı; araç: araç kimliği
        self.secenek = M.Secenek.sozlukten(uyg.ayar.get("secenek", {}))
        self.kosucu: M.Kosucu | None = None
        self.calisiyor = False
        self._calisan: list[Oge] = []
        self._isler: list[M.Is] = []
        self._son_klasor: str | None = None
        self._sec_w: dict[str, tuple] = {}
        self._chipler: dict[str, Gtk.ToggleButton] = {}
        self._kilit = False

        self.kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self._kur_dosya_karti()
        self._kur_liste_karti()
        self._kur_hedef_karti()
        self._kur_secenek_karti()
        self._kur_cikti_karti()
        self._kur_eylem_karti()
        self.yenile()

    # -- metin ----------------------------------------------------------------
    def t(self, anahtar, **kw):
        return self.uyg.t(anahtar, **kw)

    @staticmethod
    def _hazirla(w, gorunur=False):
        """Cocuklari gorunur isaretler; ustteki kapsayici show()/hide() ile yonetilsin diye
        show_all'dan korunur (no_show_all)."""
        w.show_all()
        w.set_no_show_all(True)
        if not gorunur:
            w.hide()

    # -- kartlar --------------------------------------------------------------
    def _kur_dosya_karti(self):
        self.dosya_kart, ic = tema.kart(16, 10)
        self.kutu.pack_start(self.dosya_kart, False, False, 0)
        self.dosya_ic = ic
        # boş durum (büyük sürükle-bırak alanı)
        self.bos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.bos.set_margin_top(14)
        self.bos.set_margin_bottom(14)
        ik = tema.Ikon("indir", 40, "vurgu")
        ik.set_halign(Gtk.Align.CENTER)
        self.bos.pack_start(ik, False, False, 0)
        self.bos_baslik = tema.etiket("", "buyuk-baslik", x=0.5)
        self.bos_alt = tema.etiket("", "kart-alt", sar=True, x=0.5)
        self.bos_alt.set_justify(Gtk.Justification.CENTER)
        self.bos.pack_start(self.bos_baslik, False, False, 0)
        self.bos.pack_start(self.bos_alt, False, False, 0)
        d = Gtk.Box(spacing=8)
        d.set_halign(Gtk.Align.CENTER)
        d.set_margin_top(6)
        self.b_ekle_bos = tema.dugme("", "ana", self.dosya_sec)
        self.b_klasor_bos = tema.dugme("", None, self.klasor_sec)
        d.pack_start(self.b_ekle_bos, False, False, 0)
        d.pack_start(self.b_klasor_bos, False, False, 0)
        self.bos.pack_start(d, False, False, 0)
        ic.pack_start(self.bos, False, False, 0)
        # dolu durum (ince çubuk)
        self.dolu = Gtk.Box(spacing=8)
        self.dolu_ozet = tema.etiket("", "kart-baslik")
        self.dolu.pack_start(self.dolu_ozet, True, True, 0)
        self.b_ekle = tema.dugme("", "kucuk", self.dosya_sec)
        self.b_klasor = tema.dugme("", "kucuk", self.klasor_sec)
        self.b_bitenleri = tema.dugme("", "kucuk", self.bitenleri_kaldir)
        self.b_temizle = tema.dugme("", "kucuk", self.temizle)
        for b in (self.b_ekle, self.b_klasor, self.b_bitenleri, self.b_temizle):
            self.dolu.pack_start(b, False, False, 0)
        ic.pack_start(self.dolu, False, False, 0)
        self._hazirla(self.bos, True)
        self._hazirla(self.dolu)
        self._hazirla(self.b_bitenleri)

    def _kur_liste_karti(self):
        self.liste_kart, ic = tema.kart(8, 4)
        self.liste = Gtk.ListBox()
        tema.sinif(self.liste, "duz-liste")
        self.liste.set_selection_mode(Gtk.SelectionMode.NONE)
        ic.pack_start(self.liste, False, False, 0)
        self.kutu.pack_start(self.liste_kart, False, False, 0)
        self._hazirla(self.liste_kart)

    def _kur_hedef_karti(self):
        self.hedef_kart, ic = tema.kart(16, 10)
        self.hedef_baslik, self.hedef_alt = tema.kart_basligi(ic, "", "")
        # eksik araç bandı: soluk biçimlerin nedeni + tek tık kurulum
        self._eksik_anahtarlar: list[str] = []
        self._bant_anahtarlar: list[str] = []
        self.kur_bant = Gtk.Box(spacing=12)
        tema.sinif(self.kur_bant, "not not-uyari")
        self.kur_bant_metin = tema.etiket("", None, sar=True, genislik=80)
        self.kur_bant_metin.set_margin_top(10)
        self.kur_bant_metin.set_margin_bottom(10)
        self.kur_bant_metin.set_margin_start(14)
        self.kur_bant.pack_start(self.kur_bant_metin, True, True, 0)
        self.kur_bant_dugme = tema.dugme("", "ana", self.kur_bant_tikla)
        self.kur_bant_dugme.set_margin_end(12)
        self.kur_bant.pack_end(self.kur_bant_dugme, False, False, 0)
        ic.pack_start(self.kur_bant, False, False, 0)
        self.hedef_ic = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        ic.pack_start(self.hedef_ic, False, False, 0)
        self.kutu.pack_start(self.hedef_kart, False, False, 0)
        self._hazirla(self.hedef_kart)
        self.kur_bant.set_no_show_all(True)
        self.kur_bant.hide()

    def _kur_secenek_karti(self):
        self.sec_kart, ic = tema.kart(16, 10)
        self.sec_baslik, _ = tema.kart_basligi(ic, "", None)
        self.sec_izgara = Gtk.Grid(column_spacing=16, row_spacing=10)
        ic.pack_start(self.sec_izgara, False, False, 0)
        self.kutu.pack_start(self.sec_kart, False, False, 0)
        satir = 0
        for anahtar, (tur, par) in SECENEK_TANIM.items():
            etk = tema.etiket("", None, x=0.0)
            etk.set_valign(Gtk.Align.CENTER)
            if tur == "secim":
                w, dugmeler = tema.secim_grubu(
                    [(k, "") for k, _m in par], str(getattr(self.secenek, anahtar)),
                    lambda k, a=anahtar: self._sec_degisti(a, k))
                w._dugmeler = dugmeler
                w._metinler = dict(par)
            elif tur == "sayi":
                alt, ust, adim = par
                ayar = Gtk.Adjustment(value=float(getattr(self.secenek, anahtar)), lower=alt, upper=ust,
                                      step_increment=adim, page_increment=adim * 10)
                w = Gtk.SpinButton(adjustment=ayar, digits=0)
                w.set_numeric(True)
                w.connect("value-changed", lambda s, a=anahtar: self._sec_degisti(a, s.get_value()))
            elif tur == "anahtar":
                w = Gtk.Switch()
                w.set_halign(Gtk.Align.START)
                w.set_active(bool(getattr(self.secenek, anahtar)))
                w.connect("notify::active", lambda s, _p, a=anahtar: self._sec_degisti(a, s.get_active()))
            else:
                w = Gtk.Entry()
                w.set_width_chars(26)
                w.set_visibility(not par)
                if par:
                    w.set_input_purpose(Gtk.InputPurpose.PASSWORD)
                w.set_text(str(getattr(self.secenek, anahtar)) if anahtar == "ocr_dil" else "")
                w.connect("changed", lambda s, a=anahtar: self._sec_degisti(a, s.get_text()))
            w.set_valign(Gtk.Align.CENTER)
            ipucu = tema.etiket("", "kart-alt", sar=True, genislik=60)
            self.sec_izgara.attach(etk, 0, satir, 1, 1)
            self.sec_izgara.attach(w, 1, satir, 1, 1)
            self.sec_izgara.attach(ipucu, 2, satir, 1, 1)
            for x in (etk, w, ipucu):
                self._hazirla(x)
            self._sec_w[anahtar] = (etk, w, ipucu)
            satir += 1
        self.sec_izgara.show()
        self._hazirla(self.sec_kart)

    def _kur_cikti_karti(self):
        self.cikti_kart, ic = tema.kart(16, 10)
        self.cikti_baslik, _ = tema.kart_basligi(ic, "", None)
        self.r_yanina = Gtk.RadioButton.new_with_label(None, "")
        self.r_klasor = Gtk.RadioButton.new_with_label_from_widget(self.r_yanina, "")
        ic.pack_start(self.r_yanina, False, False, 0)
        k = Gtk.Box(spacing=8)
        k.pack_start(self.r_klasor, False, False, 0)
        self.klasor_yol = tema.etiket("", "mono")
        self.klasor_yol.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        k.pack_start(self.klasor_yol, True, True, 0)
        self.b_klasor_sec = tema.dugme("", "kucuk", self.cikti_klasoru_sec)
        k.pack_end(self.b_klasor_sec, False, False, 0)
        ic.pack_start(k, False, False, 0)
        if self.uyg.ayar.get("cikti_modu") == "klasor":
            self.r_klasor.set_active(True)
        else:
            self.r_yanina.set_active(True)
        self.r_yanina.connect("toggled", self._cikti_modu_degisti)
        self.r_klasor.connect("toggled", self._cikti_modu_degisti)
        self.kutu.pack_start(self.cikti_kart, False, False, 0)
        self._hazirla(self.cikti_kart)

    def _kur_eylem_karti(self):
        self.eylem_kart, ic = tema.kart(16, 10)
        self.ilerleme = Gtk.ProgressBar()
        self.durum_metin = tema.etiket("", "kart-alt", sar=True, genislik=90)
        ic.pack_start(self.durum_metin, False, False, 0)
        ic.pack_start(self.ilerleme, False, False, 0)
        satir = Gtk.Box(spacing=10)
        self.b_ana = tema.dugme("", "ana", self.baslat_iptal)
        self.b_klasoru_ac = tema.dugme("", None, self.klasoru_ac)
        satir.pack_end(self.b_ana, False, False, 0)
        satir.pack_end(self.b_klasoru_ac, False, False, 0)
        ic.pack_start(satir, False, False, 0)
        self.kutu.pack_start(self.eylem_kart, False, False, 0)
        self._hazirla(self.b_klasoru_ac)
        self._hazirla(self.ilerleme)
        self._hazirla(self.eylem_kart)

    # -- metinleri uygula ----------------------------------------------------------
    def metinleri_uygula(self):
        t = self.t
        self.bos_baslik.set_text(t("surukle_baslik"))
        self.bos_alt.set_text(t("surukle_alt_donustur") if self.mod == "donustur" else t("surukle_alt_arac"))
        for b in (self.b_ekle_bos, self.b_ekle):
            b.set_label(t("dosya_ekle"))
        for b in (self.b_klasor_bos, self.b_klasor):
            b.set_label(t("klasor_ekle"))
        self.b_bitenleri.set_label(t("bitenleri_kaldir"))
        self.b_temizle.set_label(t("temizle"))
        self.hedef_baslik.set_text(t("hedef_baslik") if self.mod == "donustur" else t("arac_baslik"))
        self.sec_baslik.set_text(t("secenek_baslik"))
        for anahtar, (etk, w, ipucu) in self._sec_w.items():
            etk.set_text(t("sec_" + anahtar))
            ip = METIN.get("sech_" + anahtar)
            ipucu.set_text(ip[self.uyg.lang] if ip else "")
            if hasattr(w, "_dugmeler"):
                for k, d in w._dugmeler.items():
                    d.set_label(t(w._metinler[k]))
        self.cikti_baslik.set_text(t("cikti_baslik"))
        self.r_yanina.set_label(t("cikti_yanina"))
        self.r_klasor.set_label(t("cikti_klasor"))
        self.b_klasor_sec.set_label(t("sec"))
        self.b_klasoru_ac.set_label(t("klasoru_ac"))
        self.klasor_yol.set_text(self.uyg.ayar.get("cikti_klasor") or t("klasor_secilmedi"))
        self.yenile()

    # -- dosya ekleme / çıkarma ---------------------------------------------------------
    def ekle(self, yollar: list[str]) -> int:
        if self.calisiyor:
            return 0
        var = {o.yol for o in self.ogeler}
        eklenen = 0
        for y in yollar:
            y = os.path.abspath(y)
            if y in var:
                continue
            if os.path.isdir(y):
                for f in klasor_dosyalari(y):
                    if f not in var:
                        self.ogeler.append(Oge(f))
                        var.add(f)
                        eklenen += 1
            elif os.path.isfile(y):
                self.ogeler.append(Oge(y))
                var.add(y)
                eklenen += 1
        if eklenen:
            self._sifirla_durum()
            self.yenile()
        return eklenen

    def dosya_sec(self, *_):
        d = Gtk.FileChooserDialog(title=self.t("dosya_ekle"), transient_for=self.uyg, action=Gtk.FileChooserAction.OPEN)
        d.add_buttons(self.t("iptal"), Gtk.ResponseType.CANCEL, self.t("ekle"), Gtk.ResponseType.OK)
        d.set_select_multiple(True)
        if self.uyg.ayar.get("son_klasor") and os.path.isdir(self.uyg.ayar["son_klasor"]):
            d.set_current_folder(self.uyg.ayar["son_klasor"])
        if d.run() == Gtk.ResponseType.OK:
            yollar = d.get_filenames()
            if yollar:
                self.uyg.ayar["son_klasor"] = os.path.dirname(yollar[0])
                self.uyg.ayar_kaydet()
            d.destroy()
            self.ekle(yollar)
        else:
            d.destroy()

    def klasor_sec(self, *_):
        d = Gtk.FileChooserDialog(title=self.t("klasor_ekle"), transient_for=self.uyg,
                                  action=Gtk.FileChooserAction.SELECT_FOLDER)
        d.add_buttons(self.t("iptal"), Gtk.ResponseType.CANCEL, self.t("ekle"), Gtk.ResponseType.OK)
        if d.run() == Gtk.ResponseType.OK:
            yol = d.get_filename()
            d.destroy()
            if yol:
                n = self.ekle([yol])
                if not n:
                    self.uyg.kabuk.bildir(self.t("klasor_bos"), "bilgi")
        else:
            d.destroy()

    def kaldir(self, oge: Oge):
        if self.calisiyor:
            return
        if oge in self.ogeler:
            self.ogeler.remove(oge)
            self.yenile()

    def temizle(self, *_):
        if self.calisiyor:
            return
        self.ogeler.clear()
        self.durum_metin.set_text("")
        self.yenile()

    def bitenleri_kaldir(self, *_):
        if self.calisiyor:
            return
        self.ogeler = [o for o in self.ogeler if o.durum != "tamam"]
        self.yenile()

    def _sifirla_durum(self):
        for o in self.ogeler:
            o.durum, o.hata, o.sonuc, o.is_ = "bekliyor", None, [], None

    # -- hedef / araç seçimi ---------------------------------------------------------------
    def _hedef_sec(self, anahtar: str | None):
        self.hedef = anahtar
        self._sifirla_durum()
        self.yenile(hedefleri_yeniden_kur=False)

    def _kur_hedefler(self):
        for c in self.hedef_ic.get_children():
            self.hedef_ic.remove(c)
        self._chipler = {}
        self._eksik_anahtarlar = []
        if self.mod == "arac":
            akis = Gtk.FlowBox()
            akis.set_selection_mode(Gtk.SelectionMode.NONE)
            akis.set_max_children_per_line(10)
            akis.set_column_spacing(8)
            akis.set_row_spacing(8)
            for kimlik, tanim in A.ARACLAR.items():
                d = Gtk.ToggleButton(label=tanim["ad"][self.uyg.lang])
                tema.sinif(d, "secim")
                ek = A.arac_kullanilabilir(kimlik)
                if ek:
                    d.set_sensitive(False)
                    self._eksik_anahtarlar += ek
                    d.set_tooltip_text(M.mesaj("arac_eksik", self.uyg.lang, arac=ek[0]))
                else:
                    d.set_tooltip_text(tanim["ac"][self.uyg.lang])
                d.set_active(kimlik == self.hedef)
                d.connect("toggled", self._chip_degisti, kimlik)
                akis.add(d)
                self._chipler[kimlik] = d
            self.hedef_ic.pack_start(akis, False, False, 0)
            self.arac_aciklama = tema.etiket("", "kart-alt", sar=True, genislik=100)
            self.hedef_ic.pack_start(self.arac_aciklama, False, False, 0)
            self.hedef_alt.set_text(self.t("arac_alt"))
            self.hedef_ic.show_all()
            self._kur_bant_guncelle()
            return
        # dönüştür: kaynakların hedef birleşimi, kategoriye göre
        sayac: dict[str, int] = {}
        kategori_hedefleri: dict[str, list[str]] = {k: [] for k in M.KATEGORILER}
        for o in self.ogeler:
            for h in M.hedefler(o.ext):
                sayac[h] = sayac.get(h, 0) + 1
                lst = kategori_hedefleri[M.hedef_kategorisi(h)]
                if h not in lst:
                    lst.append(h)
        toplam = len(self.ogeler)
        for kat in M.KATEGORILER:
            hl = sorted(kategori_hedefleri[kat], key=lambda h: M.HEDEF_SIRASI.index(h) if h in M.HEDEF_SIRASI else 99)
            if not hl:
                continue
            satir = Gtk.Box(spacing=12)
            ad = tema.etiket(self.t("kat_" + kat), "kart-alt")
            ad.set_size_request(86, -1)
            ad.set_valign(Gtk.Align.CENTER)
            satir.pack_start(ad, False, False, 0)
            akis = Gtk.FlowBox()
            akis.set_selection_mode(Gtk.SelectionMode.NONE)
            akis.set_max_children_per_line(14)
            akis.set_column_spacing(6)
            akis.set_row_spacing(6)
            for h in hl:
                d = Gtk.ToggleButton(label=h.upper())
                tema.sinif(d, "secim kucuk")
                ornek = next(o for o in self.ogeler if h in M.hedefler(o.ext))
                ek = M.eksikler(ornek.ext, h)
                ipucu = self.t("hedef_sayi", n=sayac[h], toplam=toplam)
                if ek and all(M.eksikler(o.ext, h) for o in self.ogeler if h in M.hedefler(o.ext)):
                    d.set_sensitive(False)
                    self._eksik_anahtarlar += ek
                    ipucu = M.mesaj("arac_eksik", self.uyg.lang, arac=ek[0])
                d.set_tooltip_text(ipucu)
                d.set_active(h == self.hedef)
                d.connect("toggled", self._chip_degisti, h)
                akis.add(d)
                self._chipler[h] = d
            satir.pack_start(akis, True, True, 0)
            self.hedef_ic.pack_start(satir, False, False, 0)
        self.hedef_alt.set_text(self.t("hedef_alt"))
        self.hedef_ic.show_all()
        self._kur_bant_guncelle()

    def _kur_bant_guncelle(self):
        """Soluk kalan biçimlerin eksik araçlarını gösterir; kurulabiliyorsa tek tık kurulum sunar."""
        anahtarlar = list(dict.fromkeys(self._eksik_anahtarlar))
        pl = K.plan(anahtarlar, M.araclar_durumu())
        if pl.bos:
            self._bant_anahtarlar = []
            self.kur_bant.hide()
            return
        self._bant_anahtarlar = [k for k in pl.anahtarlar if k not in pl.elle]
        self.kur_bant_metin.set_text(self.t("kur_banner", liste=", ".join(self._bant_anahtarlar)))
        self.kur_bant_dugme.set_label(self.t("kur_bant_dugme"))
        self.kur_bant_dugme.set_sensitive(not self.uyg._kuruluyor)
        self.kur_bant.show()

    def kur_bant_tikla(self, *_):
        self.uyg.araclari_kur(list(self._bant_anahtarlar))

    def _chip_degisti(self, dugme, anahtar):
        if self._kilit:
            return
        if dugme.get_active():
            self._kilit = True
            for k, d in self._chipler.items():
                if k != anahtar:
                    d.set_active(False)
            self._kilit = False
            self._hedef_sec(anahtar)
        elif self.hedef == anahtar:
            self._hedef_sec(None)

    # -- seçenekler -------------------------------------------------------------------------
    def gorunen_secenekler(self) -> list[str]:
        if self.mod == "arac":
            return list(A.ARACLAR[self.hedef]["sec"]) if self.hedef in A.ARACLAR else []
        h = self.hedef
        if not h:
            return []
        uygun = [o for o in self.ogeler if M.kontrol(o.ext, h) is None]
        kaynaklar = {o.tur for o in uygun}
        ext_set = {o.ext for o in uygun}
        g: list[str] = []
        gorsel_hedef = h in M.GORSEL_YAZ
        if h in ("jpg", "webp", "avif") or h in M.VIDEO_YAZ or h in M.SES_YAZ:
            g.append("kalite")
        if h in ("mp4", "webm") and "gif" in ext_set:
            g.append("kalite")
        if gorsel_hedef or (h == "pdf" and kaynaklar & {"gorsel", "ham", "svg"}):
            g.append("max_kenar")
        if h in M.VIDEO_YAZ and "video" in kaynaklar:
            g.append("max_kenar")
        if kaynaklar & {"gorsel", "ham"} and (gorsel_hedef or h == "pdf"):
            g.append("meta_temizle")
        if kaynaklar & {"video", "ses"}:
            g.append("meta_temizle")
        if h == "gif" and "video" in kaynaklar:
            g += ["gif_fps", "gif_genislik"]
        if "pdf" in kaynaklar:
            g.append("parola")
            if h in ("png", "jpg", "webp", "txt"):
                g.append("sayfa_araligi")
        if (kaynaklar & {"pdf", "sunum"}) and h in ("png", "jpg", "webp"):
            g.append("dpi")
            if "sayfa_araligi" not in g:
                g.append("sayfa_araligi")
        if len(self.ogeler) > 1:
            g.append("zip_yap")
        out = []
        for k in g:
            if k not in out:
                out.append(k)
        return [k for k in SECENEK_TANIM if k in out]   # sabit sıra

    def _sec_degisti(self, anahtar, deger):
        if self._kilit:
            return
        tur = SECENEK_TANIM[anahtar][0]
        if tur == "secim" and anahtar == "derece":
            deger = int(deger)
        elif tur == "sayi":
            deger = float(deger) if anahtar in ("baslangic", "bitis") else int(deger)
        try:
            setattr(self.secenek, anahtar, deger)
        except Exception:
            return
        if anahtar in ("kalite", "ocr_dil", "dpi"):
            self.uyg.ayar.setdefault("secenek", {})[anahtar] = deger
            self.uyg.ayar_kaydet()
        if self.mod == "arac":
            self.yenile_eylem()

    def _secenekleri_goster(self):
        gorunen = self.gorunen_secenekler()
        self._kilit = True
        for anahtar, (etk, w, ipucu) in self._sec_w.items():
            if anahtar in gorunen:
                etk.show()
                w.show()
                ipucu.show() if ipucu.get_text() else ipucu.hide()
                if hasattr(w, "_dugmeler"):
                    for k, d in w._dugmeler.items():
                        d.set_active(k == str(getattr(self.secenek, anahtar)))
            else:
                for x in (etk, w, ipucu):
                    x.hide()
        if "max_kenar" in gorunen:
            video = self.mod == "donustur" and self.hedef in M.VIDEO_YAZ
            self._sec_w["max_kenar"][0].set_text(self.t("sec_max_yukseklik" if video else "sec_max_kenar"))
        self._kilit = False
        self.sec_kart.show() if gorunen else self.sec_kart.hide()

    # -- çıktı ------------------------------------------------------------------------------------
    def _cikti_modu_degisti(self, *_):
        if self._kilit:
            return
        klasor = self.r_klasor.get_active()
        self.uyg.ayar["cikti_modu"] = "klasor" if klasor else "yanina"
        self.uyg.ayar_kaydet()
        self.b_klasor_sec.set_sensitive(klasor)
        self.uyg.cikti_esitle(self)

    def cikti_klasoru_sec(self, *_):
        d = Gtk.FileChooserDialog(title=self.t("cikti_klasor"), transient_for=self.uyg,
                                  action=Gtk.FileChooserAction.SELECT_FOLDER)
        d.add_buttons(self.t("iptal"), Gtk.ResponseType.CANCEL, self.t("sec"), Gtk.ResponseType.OK)
        if d.run() == Gtk.ResponseType.OK:
            yol = d.get_filename()
            d.destroy()
            if yol:
                self.uyg.ayar["cikti_klasor"] = yol
                self.uyg.ayar["cikti_modu"] = "klasor"
                self.uyg.ayar_kaydet()
                self.uyg.cikti_esitle(None)
        else:
            d.destroy()

    def cikti_goster(self):
        self._kilit = True
        klasor = self.uyg.ayar.get("cikti_modu") == "klasor"
        (self.r_klasor if klasor else self.r_yanina).set_active(True)
        self.klasor_yol.set_text(self.uyg.ayar.get("cikti_klasor") or self.t("klasor_secilmedi"))
        self.b_klasor_sec.set_sensitive(klasor)
        self._kilit = False

    # -- liste -------------------------------------------------------------------------------------
    def _uyumsuzluk(self, o: Oge) -> FilenorHata | None:
        if not self.hedef:
            return None
        if self.mod == "donustur":
            return M.kontrol(o.ext, self.hedef)
        if self.hedef in A.ARACLAR and not A.arac_girdi_uygun(self.hedef, o.yol):
            return FilenorHata("desteklenmiyor", kaynak=o.ext or "?", hedef=A.ARACLAR[self.hedef]["ad"][self.uyg.lang])
        return None

    def _satir_kur(self, o: Oge):
        satir = Gtk.ListBoxRow()
        satir.set_activatable(False)
        satir.set_selectable(False)
        kutu = Gtk.Box(spacing=12)
        kutu.set_margin_top(8)
        kutu.set_margin_bottom(8)
        kutu.set_margin_start(8)
        kutu.set_margin_end(8)
        tema.sinif(kutu, "satir-ayrac")
        rz = tema.rozet((o.ext or "?").upper()[:5], ROZET_RENK.get(o.tur, "gri"))
        rz.set_size_request(54, -1)
        rz.set_xalign(0.5)
        kutu.pack_start(rz, False, False, 0)
        orta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ad = tema.etiket(o.ad, "kart-baslik")
        ad.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        ad.set_tooltip_text(o.yol)
        alt = tema.etiket("", "kart-alt")
        alt.set_ellipsize(Pango.EllipsizeMode.END)
        pb = Gtk.ProgressBar()
        pb.set_no_show_all(True)
        orta.pack_start(ad, False, False, 0)
        orta.pack_start(alt, False, False, 0)
        orta.pack_start(pb, False, False, 2)
        kutu.pack_start(orta, True, True, 0)
        sag = Gtk.Box(spacing=6)
        sag.set_valign(Gtk.Align.CENTER)
        b_ac = tema.dugme(self.t("ac"), "kucuk", lambda: self._sonucu_ac(o))
        b_ac.set_no_show_all(True)
        b_kl = tema.dugme(self.t("klasor"), "kucuk", lambda: self._sonuc_klasoru(o))
        b_kl.set_no_show_all(True)
        b_x = tema.dugme("✕", "duz kucuk", self.kaldir, o)
        b_x.set_tooltip_text(self.t("kaldir"))
        for b in (b_ac, b_kl, b_x):
            sag.pack_start(b, False, False, 0)
        kutu.pack_start(sag, False, False, 0)
        satir.add(kutu)
        satir.show_all()
        pb.hide()
        b_ac.hide()
        b_kl.hide()
        o.satir = {"rozet": rz, "ad": ad, "alt": alt, "pb": pb, "ac": b_ac, "klasor": b_kl, "x": b_x, "kutu": kutu}
        return satir

    def _satir_guncelle(self, o: Oge):
        s = o.satir
        if not s:
            return
        alt, pb = s["alt"], s["pb"]
        ctx = alt.get_style_context()
        for c in ("hata-yazi", "basari-yazi", "uyari-yazi"):
            ctx.remove_class(c)
        ozet = M.insan_boyut(o.boyut)
        uyum = self._uyumsuzluk(o) if o.durum in ("bekliyor",) else None
        pb.hide()
        s["ac"].hide()
        s["klasor"].hide()
        s["x"].set_visible(not self.calisiyor)
        if o.durum == "calisiyor":
            alt.set_text(self.t("durum_calisiyor"))
            pb.show()
            pb.set_fraction((o.is_.yuzde if o.is_ else 0) / 100.0)
        elif o.durum == "tamam" and o.is_:
            ctx.add_class("basari-yazi")
            if len(o.sonuc) == 1:
                son = os.path.basename(o.sonuc[0])
                boy = M.insan_boyut(o.is_.boyut_sonra)
                fark = ""
                if o.is_.boyut_once and o.is_.boyut_sonra:
                    yuzde = round(100 * (o.is_.boyut_sonra - o.is_.boyut_once) / o.is_.boyut_once)
                    fark = f" ({yuzde:+d}%)"
                alt.set_text(f"→ {son} · {ozet} → {boy}{fark}")
            else:
                alt.set_text(self.t("sonuc_cok", n=len(o.sonuc), klasor=os.path.basename(os.path.dirname(o.sonuc[0]))))
            s["ac"].show()
            s["klasor"].show()
        elif o.durum == "hata" and o.hata:
            ctx.add_class("hata-yazi")
            alt.set_text("✖ " + hata_metni(o.hata, self.uyg.lang))
            alt.set_tooltip_text(hata_metni(o.hata, self.uyg.lang))
        elif o.durum == "iptal":
            ctx.add_class("uyari-yazi")
            alt.set_text(self.t("durum_iptal"))
        elif uyum is not None:
            ctx.add_class("hata-yazi")
            alt.set_text("⚠ " + hata_metni(uyum, self.uyg.lang))
            alt.set_tooltip_text(hata_metni(uyum, self.uyg.lang))
        else:
            alt.set_text(ozet)
            alt.set_tooltip_text(None)

    def _sonucu_ac(self, o: Oge):
        if o.sonuc:
            ac(o.sonuc[0] if len(o.sonuc) == 1 else os.path.dirname(o.sonuc[0]))

    def _sonuc_klasoru(self, o: Oge):
        if o.sonuc:
            ac(os.path.dirname(o.sonuc[0]))

    # -- ana yenileme --------------------------------------------------------------------------------
    def yenile(self, hedefleri_yeniden_kur: bool = True):
        var = bool(self.ogeler)
        # hedef geçerli mi?
        if self.mod == "donustur" and self.hedef:
            if not any(self.hedef in M.hedefler(o.ext) for o in self.ogeler):
                self.hedef = None
        # dosya kartı
        if var:
            self.bos.hide()
            self.dolu.show()
            if not any(o.durum == "tamam" for o in self.ogeler):
                self.b_bitenleri.hide()
        else:
            self.dolu.hide()
            self.bos.show()
        toplam = sum(o.boyut for o in self.ogeler)
        self.dolu_ozet.set_text(self.t("ozet_dosyalar", n=len(self.ogeler), boyut=M.insan_boyut(toplam)))
        self.b_ekle.set_sensitive(not self.calisiyor)
        self.b_klasor.set_sensitive(not self.calisiyor)
        self.b_temizle.set_sensitive(not self.calisiyor)
        self.b_bitenleri.set_sensitive(not self.calisiyor)
        # liste
        for c in self.liste.get_children():
            self.liste.remove(c)
        for o in self.ogeler:
            self.liste.add(self._satir_kur(o))
            self._satir_guncelle(o)
        self.liste.show()
        if var:
            self.liste_kart.show()
        else:
            self.liste_kart.hide()
        # hedef / araç
        if hedefleri_yeniden_kur:
            if self.mod == "arac" or var:
                self._kur_hedefler()
        if self.mod == "arac" or var:
            self.hedef_kart.show()
        else:
            self.hedef_kart.hide()
        if self.mod == "arac":
            tanim = A.ARACLAR.get(self.hedef)
            self.arac_aciklama.set_text(tanim["ac"][self.uyg.lang] if tanim else "")
        # seçenekler
        self._secenekleri_goster()
        # çıktı + eylem
        hazir_kart = var and self.hedef is not None
        if hazir_kart:
            self.cikti_kart.show()
            self.eylem_kart.show()
        else:
            self.cikti_kart.hide()
            self.eylem_kart.hide()
        self.cikti_goster()
        self.yenile_eylem()

    def uygun_ogeler(self) -> list[Oge]:
        if not self.hedef:
            return []
        return [o for o in self.ogeler if self._uyumsuzluk(o) is None]

    def yenile_eylem(self):
        uygun = self.uygun_ogeler()
        if self.calisiyor:
            self.b_ana.set_label(self.t("iptal_et"))
            self.b_ana.set_sensitive(True)
            tema.sinif(self.b_ana, "tehlike")
            self.b_ana.get_style_context().remove_class("ana")
        else:
            ctx = self.b_ana.get_style_context()
            ctx.remove_class("tehlike")
            ctx.add_class("ana")
            etiket = self.t("donustur_et") if self.mod == "donustur" else self.t("calistir")
            if self.mod == "arac" and self.hedef in A.ARACLAR:
                etiket = A.ARACLAR[self.hedef]["ad"][self.uyg.lang]
            self.b_ana.set_label(etiket)
            minimum = A.ARACLAR[self.hedef]["min"] if (self.mod == "arac" and self.hedef in A.ARACLAR) else 1
            self.b_ana.set_sensitive(len(uygun) >= minimum)
            bitti_var = any(o.durum in ("tamam", "hata", "iptal") for o in self.ogeler)
            if not bitti_var:
                self.ilerleme.hide()
                self.b_klasoru_ac.hide()
                if uygun and len(uygun) < minimum:
                    self.durum_metin.set_text(self.t("en_az_dosya", n=minimum))
                elif uygun:
                    self.durum_metin.set_text(self.t("hazir_n", n=len(uygun)))
                elif self.ogeler and self.hedef:
                    self.durum_metin.set_text(self.t("hic_uygun"))
                else:
                    self.durum_metin.set_text("")

    # -- çalıştırma ----------------------------------------------------------------------------------
    def cikti_dizini(self) -> str | None:
        """None = dosyanın yanına."""
        if self.uyg.ayar.get("cikti_modu") == "klasor" and self.uyg.ayar.get("cikti_klasor"):
            return self.uyg.ayar["cikti_klasor"]
        return None

    def baslat_iptal(self, *_):
        if self.calisiyor:
            if self.kosucu:
                self.kosucu.iptal_et()
                self.b_ana.set_sensitive(False)
                self.durum_metin.set_text(self.t("iptal_ediliyor"))
            return
        uygun = self.uygun_ogeler()
        if not uygun:
            return
        # özel durum: araç için en az dosya
        isler: list[M.Is] = []
        if self.mod == "arac" and self.hedef == "pdf_birlestir":
            i = M.Is(uygun[0].yol, self.hedef)
            i.dosyalar = [o.yol for o in uygun]
            isler.append(i)
            for o in uygun:
                o.is_ = i
        else:
            for o in uygun:
                o.is_ = M.Is(o.yol, self.hedef)
                isler.append(o.is_)
        for o in self.ogeler:
            o.durum, o.hata, o.sonuc = "bekliyor", None, []
        self._calisan = uygun
        self._isler = isler
        sec = M.Secenek.sozlukten(self.secenek.sozluk())
        sinif = A.AracKosucu if self.mod == "arac" else M.Kosucu
        yanina = self.cikti_dizini() is None
        self.kosucu = sinif(isler, self.cikti_dizini(), sec, is_cb=self._is_cb_thread, bitti_cb=self._bitti_cb_thread,
                            yanina=yanina)
        self.calisiyor = True
        self.ilerleme.set_fraction(0)
        self.ilerleme.show()
        self.b_klasoru_ac.hide()
        self.durum_metin.set_text(self.t("calisiyor_n", i=1, n=len(isler)))
        for o in self.ogeler:
            self._satir_guncelle(o)
        self.yenile_eylem()
        self.kosucu.start()

    def _is_cb_thread(self, i: int, is_: M.Is):
        GLib.idle_add(self._is_guncellendi, i)

    def _bitti_cb_thread(self, isler):
        GLib.idle_add(self._bitti)

    def _is_guncellendi(self, i: int):
        if not self.kosucu or i >= len(self._isler):
            return False
        is_ = self._isler[i]
        for o in self._calisan:
            if o.is_ is is_:
                o.durum = is_.durum
                o.hata = is_.hata
                o.sonuc = list(is_.sonuc)
                self._satir_guncelle(o)
        toplam = len(self._isler)
        ort = sum((100.0 if x.durum in ("tamam", "hata", "iptal") else x.yuzde) for x in self._isler) / max(1, toplam)
        self.ilerleme.set_fraction(ort / 100.0)
        bitenler = sum(1 for x in self._isler if x.durum in ("tamam", "hata", "iptal"))
        if self.calisiyor and bitenler < toplam:
            self.durum_metin.set_text(self.t("calisiyor_n", i=bitenler + 1, n=toplam))
        return False

    def _bitti(self):
        k = self.kosucu
        self.calisiyor = False
        isler = self._isler
        ok = sum(1 for x in isler if x.durum == "tamam")
        hata = sum(1 for x in isler if x.durum == "hata")
        iptal = sum(1 for x in isler if x.durum == "iptal")
        for o in self._calisan:
            if o.is_:
                o.durum, o.hata, o.sonuc = o.is_.durum, o.is_.hata, list(o.is_.sonuc)
        self.ilerleme.set_fraction(1.0 if not iptal else self.ilerleme.get_fraction())
        parcalar = [self.t("bitti_ok", n=ok)]
        if hata:
            parcalar.append(self.t("bitti_hata", n=hata))
        if iptal:
            parcalar.append(self.t("bitti_iptal", n=iptal))
        self.durum_metin.set_text(" · ".join(parcalar))
        tum = [s for x in isler if x.durum == "tamam" for s in x.sonuc]
        if k and getattr(k, "zip_yolu", None):
            tum.append(k.zip_yolu)
        self._son_klasor = os.path.dirname(tum[0]) if tum else None
        if self._son_klasor:
            self.b_klasoru_ac.show()
        for o in self.ogeler:
            self._satir_guncelle(o)
        if any(o.durum == "tamam" for o in self.ogeler):
            self.b_bitenleri.show()
        self.yenile_eylem()
        self.uyg.bitis_bildir(ok, hata, iptal, self._son_klasor)
        return False

    def klasoru_ac(self, *_):
        if getattr(self, "_son_klasor", None):
            ac(self._son_klasor)


# ---------------------------------------------------------------------------------------------------
class Uygulama(Gtk.Window):
    def __init__(self, dosyalar: list[str] | None = None, logo: str | None = None):
        super().__init__(title="Filenor")
        self.ayar = M.ayar_oku()
        if self.ayar.get("dil") not in ("tr", "en"):
            self.ayar["dil"] = dil_varsayilan()
        if self.ayar.get("tema") not in ("dark", "light"):
            self.ayar["tema"] = "dark"
        self.lang = self.ayar["dil"]
        tema.uygula(self.ayar["tema"], "filenor")
        self.set_default_size(1180, 820)
        self.set_size_request(980, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        try:
            if logo:
                self.set_icon_from_file(logo)
            else:
                self.set_icon_name("filenor")
        except GLib.Error:
            pass
        self.connect("destroy", self._kapaniyor)
        self._kuruluyor = False
        self._kur_belirsiz = False
        self._temel_eksik: list[str] = []

        self.kabuk = tema.Kabuk(logo, BOLUMLER, self.sayfa_secildi)
        self.add(self.kabuk)
        self.paneller = {"donustur": Panel(self, "donustur"), "araclar": Panel(self, "arac")}
        self.sayfalar = {"donustur": self.paneller["donustur"].kutu, "araclar": self.paneller["araclar"].kutu}
        self._kur_ayar_sayfasi()
        self.sayfalar["ayar"] = self.ayar_kutu

        # sol alt: dil + görünüm (diğer uygulamalarla aynı yer)
        alt = Gtk.Box(spacing=8)
        self.dil_kutu = Gtk.ComboBoxText()
        self.dil_kutu.append("tr", "Türkçe")
        self.dil_kutu.append("en", "English")
        self.dil_kutu.set_active_id(self.lang)
        self.dil_kutu.connect("changed", self.dil_degisti)
        alt.pack_start(self.dil_kutu, True, True, 0)
        self.tema_dugme = tema.dugme("", None, self.tema_degistir)
        alt.pack_start(self.tema_dugme, False, False, 0)
        self.kabuk.yan_alt.pack_start(alt, False, False, 0)
        self.alt_bilgi = tema.etiket("", "marka-alt")
        self.kabuk.yan_alt.pack_start(self.alt_bilgi, False, False, 0)

        # sürükle-bırak: tüm pencere
        self.drag_dest_set(Gtk.DestDefaults.ALL, [Gtk.TargetEntry.new("text/uri-list", 0, 0)], Gdk.DragAction.COPY)
        self.connect("drag-data-received", self._suruklendi)
        self.connect("drag-motion", self._surukle_uzerinde)
        self.connect("drag-leave", self._surukle_cikti)
        # Ctrl+O
        hiz = Gtk.AccelGroup()
        hiz.connect(Gdk.keyval_from_name("o"), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE,
                    lambda *_: self.aktif_panel() and self.aktif_panel().dosya_sec() or True)
        self.add_accel_group(hiz)

        self.aktif = None
        self.metinleri_uygula()
        self.kabuk.sec("donustur")     # icerik, pencere gosterilmeden once yerlessin
        self.show_all()
        if dosyalar:
            self.paneller["donustur"].ekle(dosyalar)

    # -- genel -------------------------------------------------------------------
    def t(self, anahtar, **kw):
        m = METIN[anahtar][self.lang]
        return m.format(**kw) if kw else m

    def ayar_kaydet(self):
        M.ayar_yaz(self.ayar)

    def aktif_panel(self) -> Panel | None:
        return {"donustur": self.paneller["donustur"], "araclar": self.paneller["araclar"]}.get(self.aktif)

    def _kapaniyor(self, *_):
        for p in self.paneller.values():
            if p.kosucu and p.calisiyor:
                p.kosucu.iptal_et()
        if Gtk.main_level() > 0:
            Gtk.main_quit()

    def sayfa_secildi(self, anahtar):
        self.aktif = anahtar
        self.kabuk.icerik(self.sayfalar[anahtar])
        self.kabuk.baslik_ayarla(self.t("baslik_" + anahtar), self.t("alt_" + anahtar))
        p = self.aktif_panel()
        if p:
            p.yenile()

    def cikti_esitle(self, _kaynak=None):
        """Cikti konumu iki sayfada ortaktir; birinde degisince digeri de guncellenir."""
        for p in self.paneller.values():
            p.cikti_goster()

    def bitis_bildir(self, ok, hata, iptal, klasor):
        if iptal and not ok:
            self.kabuk.bildir(self.t("bitti_iptal", n=iptal), "bilgi")
        elif hata and not ok:
            self.kabuk.bildir(self.t("bitti_hata", n=hata), "hata", sure=8)
        else:
            self.kabuk.bildir(self.t("bitti_ok", n=ok) + (" · " + self.t("bitti_hata", n=hata) if hata else ""),
                              "basari" if not hata else "bilgi")
        if ok and klasor and self.ayar.get("bitince_ac"):
            ac(klasor)

    # -- sürükle bırak ---------------------------------------------------------------
    def _surukle_uzerinde(self, w, ctx, x, y, zaman):
        p = self.aktif_panel()
        if p:
            tema.sinif(p.dosya_kart, "vurgulu")
        return False

    def _surukle_cikti(self, w, ctx, zaman):
        for p in self.paneller.values():
            p.dosya_kart.get_style_context().remove_class("vurgulu")

    def _suruklendi(self, w, ctx, x, y, veri, bilgi, zaman):
        self._surukle_cikti(w, ctx, zaman)
        yollar = []
        for u in veri.get_uris() or []:
            try:
                yol = Gio.File.new_for_uri(u).get_path()
            except GLib.Error:
                yol = None
            if yol:
                yollar.append(yol)
        p = self.aktif_panel()
        if p and yollar:
            n = p.ekle(yollar)
            if not n:
                self.kabuk.bildir(self.t("surukle_bos"), "bilgi")
        ctx.finish(True, False, zaman)

    # -- ayar sayfası -----------------------------------------------------------------
    def _kur_ayar_sayfasi(self):
        self.ayar_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        # görünüm ve davranış
        k1, ic1 = tema.kart(16, 12)
        self.a_baslik1, _ = tema.kart_basligi(ic1, "", None)
        satir = Gtk.Box(spacing=12)
        self.a_bitince = tema.etiket("", None)
        self.s_bitince = Gtk.Switch()
        self.s_bitince.set_active(bool(self.ayar.get("bitince_ac")))
        self.s_bitince.connect("notify::active", self._bitince_degisti)
        satir.pack_start(self.a_bitince, True, True, 0)
        satir.pack_end(self.s_bitince, False, False, 0)
        ic1.pack_start(satir, False, False, 0)
        self.ayar_kutu.pack_start(k1, False, False, 0)
        # araç durumu
        k2, ic2 = tema.kart(16, 8)
        self.a_baslik2, self.a_alt2 = tema.kart_basligi(ic2, "", "")
        self.arac_listesi = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ic2.pack_start(self.arac_listesi, False, False, 0)
        dugmeler = Gtk.Box(spacing=8)
        dugmeler.set_halign(Gtk.Align.START)
        self.b_kur_hepsi = tema.dugme("", "ana", self.eksikleri_kur)
        self.b_kur_hepsi.set_no_show_all(True)
        self.b_yenile = tema.dugme("", "kucuk", self.araclari_yenile)
        dugmeler.pack_start(self.b_kur_hepsi, False, False, 0)
        dugmeler.pack_start(self.b_yenile, False, False, 0)
        ic2.pack_start(dugmeler, False, False, 0)
        self.a_kur_ek = tema.etiket("", "kart-alt", sar=True, genislik=100)
        self.a_kur_ek.set_no_show_all(True)
        ic2.pack_start(self.a_kur_ek, False, False, 0)
        self.kur_ilerleme = Gtk.ProgressBar()
        self.kur_ilerleme.set_no_show_all(True)
        ic2.pack_start(self.kur_ilerleme, False, False, 0)
        self.a_kur_durum = tema.etiket("", "kart-alt", sar=True, genislik=100)
        self.a_kur_durum.set_no_show_all(True)
        ic2.pack_start(self.a_kur_durum, False, False, 0)
        self.ayar_kutu.pack_start(k2, False, False, 0)
        # hakkında
        k3, ic3 = tema.kart(16, 6)
        self.a_baslik3, _ = tema.kart_basligi(ic3, "", None)
        self.a_hakkinda = tema.etiket("", "kart-alt", sar=True, genislik=100)
        ic3.pack_start(self.a_hakkinda, False, False, 0)
        self.ayar_kutu.pack_start(k3, False, False, 0)

    def _arac_listesini_kur(self):
        for c in self.arac_listesi.get_children():
            self.arac_listesi.remove(c)
        d = M.araclar_durumu()
        eksik = 0
        for anahtar in ("ffmpeg", "libreoffice", "pdftoppm", "qpdf", "tesseract", "pillow", "reportlab",
                        "fonttools", "brotli", "svg", "avif", "rawpy", "heif", "gs"):
            var = bool(d.get(anahtar))
            satir = Gtk.Box(spacing=10)
            satir.set_margin_top(3)
            satir.set_margin_bottom(3)
            satir.pack_start(tema.Ikon("onay" if var else "yasak", 16, "yesil" if var else "silik"), False, False, 0)
            ad = tema.etiket(anahtar, "ip")
            ad.set_size_request(110, -1)
            satir.pack_start(ad, False, False, 0)
            satir.pack_start(tema.etiket(self.t("ar_" + anahtar), "kart-alt", sar=True, genislik=70), True, True, 0)
            if not var:
                from filenor_dil import ipucu_al
                if anahtar != "gs":
                    eksik += 1
                pl = K.plan([anahtar], d)
                if pl.bos:
                    satir.pack_end(tema.etiket(ipucu_al(anahtar, self.lang), "mono"), False, False, 0)
                else:
                    b = tema.dugme(self.t("kur_dugme"), "kucuk", self.araclari_kur, [anahtar])
                    b.set_sensitive(not self._kuruluyor)
                    b.set_tooltip_text(self.t("kur_yok_ipucu", liste=", ".join(pl.paketler)))
                    satir.pack_end(b, False, False, 0)
            self.arac_listesi.pack_start(satir, False, False, 0)
        self.a_alt2.set_text(self.t("ayar_arac_ok") if not eksik else self.t("ayar_arac_eksik", n=eksik))
        self.arac_listesi.show_all()
        # "Eksikleri kur": kurulabilen, büyük olmayan eksikler
        tpl = K.plan(K.temel_eksikler(d), d)
        self._temel_eksik = [k for k in tpl.anahtarlar if k not in tpl.elle]
        if self._temel_eksik:
            self.b_kur_hepsi.set_label(self.t("kur_hepsi_n", n=len(self._temel_eksik)))
            self.b_kur_hepsi.set_sensitive(not self._kuruluyor)
            self.b_kur_hepsi.show()
        else:
            self.b_kur_hepsi.hide()
        self.b_yenile.set_sensitive(not self._kuruluyor)
        if any(not d.get(k) for k in K.ISTEGE_BAGLI):
            self.a_kur_ek.set_text(self.t("kur_isteye_bagli"))
            self.a_kur_ek.show()
        else:
            self.a_kur_ek.hide()

    # -- araç kurulumu -----------------------------------------------------------------
    def eksikleri_kur(self, *_):
        self.araclari_kur(list(self._temel_eksik))

    def araclari_kur(self, anahtarlar):
        """Eksik araçları kurar (arka planda). Yönetici parolası sistemden istenir."""
        if self._kuruluyor:
            return
        pl = K.plan(anahtarlar, M.araclar_durumu())
        if pl.bos:
            self.kabuk.bildir(self.t("kur_elle", liste=", ".join(pl.elle) or "-"), "hata")
            return
        if "libreoffice" in pl.anahtarlar and not tema.onay_sor(
                self, self.t("kur_onay_baslik", ad="LibreOffice"),
                self.t("kur_onay_metin", boyut="500 MB"),
                self.t("kur_onay_evet"), self.t("kur_onay_hayir")):
            return
        self._kuruluyor = True
        self._kur_gorunum(True, pl)
        threading.Thread(target=self._kur_is, args=(pl,), daemon=True).start()

    def _kur_is(self, pl):
        hata = None
        try:
            K.kur(pl, lambda satir: GLib.idle_add(self._kur_satir, satir),
                  ilerleme_cb=lambda o, a, d: GLib.idle_add(self._kur_ilerle, o, a, d))
        except FilenorHata as h:
            hata = h
        except Exception as e:          # beklenmeyen: arayüz asılı kalmasın
            hata = FilenorHata("bilinmeyen", ayrinti=str(e))
        GLib.idle_add(self._kur_bitti, pl, hata)

    def _kur_satir(self, satir):
        self.a_kur_durum.set_tooltip_text(satir[:300])      # ham çıktı: üzerine gelince
        return False

    def _kur_ilerle(self, oran, asama, ayrinti):
        """Gerçek ilerleme: apt indirme/kurulum yüzdeleri ve pip indirme boyutu."""
        if not self._kuruluyor:
            return False
        self._kur_belirsiz = oran is None
        if oran is not None:
            self.kur_ilerleme.set_fraction(oran)
        if asama == "guncelle":
            metin = self.t("kur_asama_guncelle")
        elif asama == "indir":
            metin = self.t("kur_asama_indir")
        elif asama == "pip":
            metin = self.t("kur_asama_pip", ad=ayrinti)
        else:
            metin = self.t("kur_asama_kur", ad=ayrinti) if ayrinti else self.t("kur_asama_kur_bos")
        if oran is not None:
            metin = self.t("kur_yuzde", n=round(oran * 100)) + " · " + metin
        self.a_kur_durum.set_text(metin)
        return False

    def _nabiz(self):
        """Yalnız boyutu bilinmeyen adımlarda (pip yedeği) çubuk gidip gelir."""
        if not self._kuruluyor:
            return False
        if self._kur_belirsiz:
            self.kur_ilerleme.pulse()
        return True

    def _kur_gorunum(self, acik, pl=None):
        self._arac_listesini_kur()          # düğmelerin etkin/pasif durumunu yeniler
        for p in self.paneller.values():
            p._kur_bant_guncelle()
        if acik:
            self._kur_belirsiz = False
            self.kur_ilerleme.set_fraction(0.0)
            self.a_kur_durum.set_tooltip_text(None)
            self.a_kur_durum.set_text(self.t("kur_basliyor"))
            self.kur_ilerleme.show()
            self.a_kur_durum.show()
            self.a_kur_ek.set_text(self.t("kur_paketler", liste=", ".join(pl.paketler)))
            self.a_kur_ek.show()
            GLib.timeout_add(120, self._nabiz)
            self.kabuk.bildir(self.t("kur_suruyor"), "bilgi", 6)
        else:
            self.kur_ilerleme.hide()
            self.a_kur_durum.hide()

    def _kur_bitti(self, pl, hata):
        self._kuruluyor = False
        K.ortami_yenile()
        A.ocr_dilleri.cache_clear()
        self._kur_gorunum(False)
        for p in self.paneller.values():
            p.yenile()
        if hata is not None:
            self.kabuk.bildir(hata_metni(hata, self.lang), "hata", 10)
            return False
        d = M.araclar_durumu()
        kalan = [k for k in pl.anahtarlar if k not in pl.elle and not d.get(k)]
        if kalan:
            self.kabuk.bildir(self.t("kur_eksik", liste=", ".join(kalan)), "hata", 10)
        else:
            self.kabuk.bildir(self.t("kur_ok"), "basari")
        return False

    def araclari_yenile(self, *_):
        M.araclari_yenile()
        self._arac_listesini_kur()
        for p in self.paneller.values():
            p.yenile()

    def _bitince_degisti(self, sw, _p):
        self.ayar["bitince_ac"] = sw.get_active()
        self.ayar_kaydet()

    # -- dil ve görünüm ----------------------------------------------------------------
    def dil_degisti(self, kutu):
        yeni = kutu.get_active_id()
        if yeni and yeni != self.lang:
            self.lang = yeni
            self.ayar["dil"] = yeni
            self.ayar_kaydet()
            self.metinleri_uygula()
            if self.aktif:
                self.kabuk.baslik_ayarla(self.t("baslik_" + self.aktif), self.t("alt_" + self.aktif))

    def tema_degistir(self, *_):
        yeni = "light" if self.ayar["tema"] == "dark" else "dark"
        self.ayar["tema"] = yeni
        self.ayar_kaydet()
        tema.uygula(yeni, "filenor")
        self.metinleri_uygula()
        self.queue_draw()

    def metinleri_uygula(self):
        t = self.t
        self.kabuk.marka_ayarla("Filenor", t("marka_alt", surum=APP_VERSION))
        self.kabuk.bolum_metni("calisma", t("bolum_calisma"))
        self.kabuk.bolum_metni("sistem", t("bolum_sistem"))
        self.kabuk.menu_metni("donustur", t("menu_donustur"))
        self.kabuk.menu_metni("araclar", t("menu_araclar"))
        self.kabuk.menu_metni("ayar", t("menu_ayar"))
        self.tema_dugme.set_label(t("gorunum_acik") if self.ayar["tema"] == "dark" else t("gorunum_koyu"))
        self.alt_bilgi.set_text(t("alt_bilgi", surum=APP_VERSION))
        self.a_baslik1.set_text(t("ayar_davranis"))
        self.a_bitince.set_text(t("ayar_bitince_ac"))
        self.a_baslik2.set_text(t("ayar_araclar"))
        self.b_yenile.set_label(t("ayar_yeniden_tara"))
        self.a_baslik3.set_text(t("ayar_hakkinda"))
        self.a_hakkinda.set_text(t("hakkinda_metin", surum=APP_VERSION))
        self._arac_listesini_kur()
        for p in self.paneller.values():
            p.metinleri_uygula()
            p._kur_hedefler() if (p.mod == "arac" or p.ogeler) else None
        if self.aktif:
            self.kabuk.baslik_ayarla(t("baslik_" + self.aktif), t("alt_" + self.aktif))


def kendini_sina() -> int:
    """Paketlenmiş uygulamanın gerçekten çalıştığını doğrular (CI için): pencere açılır, gerçek bir
    görsel dönüşümü yapılır. Sonuç FILENOR_SINAMA_CIKTI dosyasına da yazılır (pencereli .exe'de konsol yoktur)."""
    import tempfile
    ozet: list[str] = []
    ok = False
    try:
        with tempfile.TemporaryDirectory(prefix="filenor-sina-") as d:
            w = Uygulama([], logo_bul())
            w.show_all()
            for _ in range(30):
                while Gtk.events_pending():
                    Gtk.main_iteration()
            durum = M.araclar_durumu()
            ozet.append("pillow=%s" % durum.get("pillow"))
            if durum.get("pillow"):
                from PIL import Image
                gir = os.path.join(d, "sina.png")
                Image.new("RGB", (40, 30), (10, 120, 200)).save(gir)
                sonuc = M.donustur(gir, "webp", d)
                ok = bool(sonuc) and os.path.getsize(sonuc[0]) > 0
                ozet.append("webp=%s" % ok)
            w.destroy()
    except Exception as e:                       # noqa: BLE001 - sinama her hatayi raporlamali
        ozet.append("HATA: %r" % (e,))
    metin = ("TAMAM " if ok else "BASARISIZ ") + " ".join(ozet)
    yol = os.environ.get("FILENOR_SINAMA_CIKTI")
    if yol:
        try:
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin + "\n")
        except OSError:
            pass
    try:
        print(metin)
    except (OSError, AttributeError, ValueError):
        pass
    return 0 if ok else 1


def ana(argv: list[str]) -> int:
    if "--surum" in argv:
        try:
            print("Filenor " + APP_VERSION)
        except (OSError, AttributeError, ValueError):
            pass
        return 0
    GLib.set_prgname("filenor")           # .desktop StartupWMClass ile eslesir
    GLib.set_application_name("Filenor")
    if "--kendini-sina" in argv:
        return kendini_sina()
    dosyalar = [a for a in argv[1:] if not a.startswith("-")]
    Uygulama(dosyalar, logo_bul())
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(ana(sys.argv))
