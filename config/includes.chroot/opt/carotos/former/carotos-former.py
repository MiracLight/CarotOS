#!/usr/bin/env python3
"""
CarotOS Former
Guvenlik araclarini ve CarotOS guvenlik denetim masasini canli, oynatilan
animasyonlarla anlatan iki dilli rehber uygulamasi.
"""
import argparse
import json
import os
import subprocess
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib  # noqa: E402

sys.path.insert(0, "/opt/carotos/ortak")
sys.path.insert(0, "/opt/carotos/former")

import tema  # noqa: E402
import former_zaman as fz  # noqa: E402
from former_zaman import metin_al, T  # noqa: E402
import former_cizim as fc  # noqa: E402
import konular  # noqa: E402

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "carotos-former")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")
BURASI = os.path.dirname(os.path.abspath(__file__))


def logo_bul():
    kok = os.path.abspath(os.path.join(BURASI, "..", "..", ".."))
    for yol in ("/usr/share/icons/hicolor/256x256/apps/carotos-former.png",
                "/usr/share/icons/hicolor/scalable/apps/carotos-former.svg",
                os.path.join(kok, "usr/share/icons/hicolor/256x256/apps/carotos-former.png"),
                os.path.join(kok, "usr/share/icons/hicolor/scalable/apps/carotos-former.svg")):
        if os.path.isfile(yol):
            return yol
    return None


LOGO = logo_bul()


def _varsayilan_dil():
    """Ilk acilis dili: sistem dili Turkce ise 'tr', baska herhangi bir
    dilse 'en'. Kayitli bir ayar varsa o oncelik tasir."""
    for degisken in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        deger = os.environ.get(degisken, "").strip()
        if deger and deger not in ("C", "POSIX"):
            return "tr" if deger.lower().startswith("tr") else "en"
    return "en"


DEFAULT_SETTINGS = {"dil": _varsayilan_dil(), "tema": "dark"}


def ayar_oku():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return {**DEFAULT_SETTINGS, **data}
    except Exception:
        return dict(DEFAULT_SETTINGS)


def ayar_yaz(ayar):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(ayar, fh, indent=2)
    except Exception:
        pass


STRINGS = {
    "app_title": T("CarotOS Former", "CarotOS Former"),
    "marka_alt": T("Güvenlik rehberi", "Security guide"),
    "grup_baslarken": T("Başlarken", "Getting started"),
    "grup_araclar": T("Güvenlik Paneli Araçları", "Security Panel Tools"),
    "grup_uygulamalar": T("Uygulamalar", "Apps"),
    "bos_baslik": T("Detaylı anlatım için konu seçin", "Pick a topic for a detailed walkthrough"),
    "bos_alt": T("Solda CarotOS'un güvenlik araçları ve uygulamaları sıralanır. Her birinde canlı bir "
                 "animasyon, adım adım bir anlatım ve bir \"kendin dene\" bölümü var. Amaç basit: siber "
                 "güvenliği, yeni başlayan biri için anlaşılır kılmak.",
                 "On the left are CarotOS's security tools and apps. Each one has a live animation, a "
                 "step-by-step walkthrough, and a \"try it yourself\" section. The goal is simple: make "
                 "cybersecurity understandable for someone just starting out."),
    "oynat": T("Oynat", "Play"),
    "duraklat": T("Duraklat", "Pause"),
    "bastan": T("Baştan", "Restart"),
    "acik_uygulama": T("{ad}'ı aç", "Open {ad}"),
    "uygulama_yok": T("{ad} bu bilgisayarda kurulu değil.", "{ad} is not installed on this computer."),
    "animasyon_basligi": T("Canlı anlatım", "Live walkthrough"),
    "adimlar_basligi": T("Adımlar", "Steps"),
    "ozet_rozeti": T("Özet", "Summary"),
    "kok_notu": T("Bu araç yönetici (root) yetkisi ister.", "This tool needs administrator (root) rights."),
}

BLOK_BASLIKLARI = {
    "kod": T("Komut", "Command"),
    "tablo": None,
}

GRUP_SIRASI = ["baslarken", "araclar", "uygulamalar"]
HIZLAR = [("0.75", "0.75×"), ("1", "1×"), ("1.5", "1.5×")]


def ac(komut):
    try:
        subprocess.Popen(komut)
        return True
    except Exception:
        return False


class Uygulama(Gtk.Window):
    def __init__(self, konu_id=None):
        super().__init__(title=metin_al(STRINGS["app_title"], "tr"))
        self.ayar = ayar_oku()
        if self.ayar.get("dil") not in ("tr", "en"):
            self.ayar["dil"] = _varsayilan_dil()
        if self.ayar.get("tema") not in ("dark", "light"):
            self.ayar["tema"] = "dark"
        self.lang = self.ayar["dil"]
        tema.uygula(self.ayar["tema"], "former")

        self.set_default_size(1180, 820)
        self.set_size_request(980, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        try:
            if LOGO:
                self.set_icon_from_file(LOGO)
            else:
                self.set_icon_name("carotos-former")
        except GLib.Error:
            pass
        self.connect("destroy", self._kapaniyor)

        self.konular = {k["id"]: k for k in konular.tumu()}
        self._zamanlayici_id = None
        self._cz = None
        self._t = 0.0
        self._oynuyor = False
        self._hiz = 1.0
        self._canvas = None
        self._aktif_id = None

        bolumler = []
        for g in GRUP_SIRASI:
            satirlar = [(k["id"], k["ikon"]) for k in self.konular.values() if k["grup"] == g]
            bolumler.append((g, satirlar))
        self.kabuk = tema.Kabuk(LOGO, bolumler, self.sayfa_secildi)
        self.add(self.kabuk)
        # GtkListBox (SINGLE secim) ilk satiri kendiliginden secebiliyor;
        # bunu etkisiz kilip baslangic durumunu biz belirleriz.
        for liste in self.kabuk.listeler:
            liste.unselect_all()

        # sol alt: dil + gorunum (diger CarotOS uygulamalariyla ayni yer)
        alt = Gtk.Box(spacing=8)
        self.dil_kutu = Gtk.ComboBoxText()
        self.dil_kutu.append("tr", "Türkçe")
        self.dil_kutu.append("en", "English")
        self.dil_kutu.set_active_id(self.lang)
        self.dil_kutu.connect("changed", self._dil_degisti)
        alt.pack_start(self.dil_kutu, True, True, 0)
        self.tema_dugme = tema.dugme("☀" if self.ayar["tema"] == "dark" else "☾", None, self._tema_degistir)
        alt.pack_start(self.tema_dugme, False, False, 0)
        self.kabuk.yan_alt.pack_start(alt, False, False, 0)

        self._metinleri_uygula()
        # icerik, pencere gosterilmeden once yerlessin (filenor ile ayni desen)
        if konu_id and konu_id in self.konular:
            self.kabuk.sec(konu_id)
        else:
            self._bos_goster()
        self.show_all()
        # GtkListBox (SINGLE secim), show_all()/realize sirasinda ilk satiri
        # kendiliginden secip sayfa_secildi'yi tekrar tetikleyebiliyor;
        # pencere gorunur olduktan sonra dogru baslangic durumunu bir kez
        # daha zorla geri getiririz.
        if konu_id and konu_id in self.konular:
            self.kabuk.sec(konu_id)
        else:
            for liste in self.kabuk.listeler:
                liste.unselect_all()
            self._bos_goster()

    # -- genel ---------------------------------------------------------------
    def t(self, anahtar, **kw):
        m = metin_al(STRINGS[anahtar], self.lang)
        return m.format(**kw) if kw else m

    def _metinleri_uygula(self):
        self.kabuk.marka_ayarla(self.t("app_title"), self.t("marka_alt"))
        for g in GRUP_SIRASI:
            self.kabuk.bolum_metni(g, self.t("grup_" + g))
        for kid, k in self.konular.items():
            self.kabuk.menu_metni(kid, metin_al(k["ad"], self.lang))

    def _dil_degisti(self, combo):
        kid = combo.get_active_id()
        if kid and kid != self.lang:
            self.lang = kid
            self.ayar["dil"] = kid
            ayar_yaz(self.ayar)
            self._metinleri_uygula()
            if self._aktif_id:
                self._sayfayi_yeniden_kur(self._aktif_id)
            else:
                self._bos_goster()

    def _tema_degistir(self, *_):
        yeni = "light" if self.ayar["tema"] == "dark" else "dark"
        self.ayar["tema"] = yeni
        ayar_yaz(self.ayar)
        tema.uygula(yeni, "former")
        self.tema_dugme.set_label("☀" if yeni == "dark" else "☾")
        if self._aktif_id:
            self._sayfayi_yeniden_kur(self._aktif_id)
        else:
            self._bos_goster()

    def _kapaniyor(self, *_):
        self._zamanlayiciyi_durdur()
        if Gtk.main_level() > 0:
            Gtk.main_quit()

    # -- gezinme ---------------------------------------------------------------
    def sayfa_secildi(self, anahtar):
        self._sayfayi_yeniden_kur(anahtar)

    def _sayfayi_yeniden_kur(self, anahtar):
        self._zamanlayiciyi_durdur()
        self._aktif_id = anahtar
        k = self.konular[anahtar]
        self.kabuk.baslik_ayarla(metin_al(k["ad"], self.lang), metin_al(k["alt"], self.lang))
        self.kabuk.icerik(self._konu_govdesi(k))

    def _bos_goster(self):
        self._zamanlayiciyi_durdur()
        self._aktif_id = None
        self.kabuk.baslik_ayarla(self.t("bos_baslik"), "")
        w = tema.bos_durum("kitap", self.t("bos_baslik"), self.t("bos_alt"))
        self.kabuk.icerik(w)

    # -- konu govdesi -----------------------------------------------------------
    def _konu_govdesi(self, k):
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        kutu.pack_start(self._ozet_satiri(k), False, False, 0)
        kutu.pack_start(self._animasyon_karti(k), False, False, 0)
        for baslik, bloklar in k["bolumler"]:
            kutu.pack_start(self._bolum_karti(baslik, bloklar), False, False, 0)
        if k.get("uygulama"):
            b = tema.dugme(self.t("acik_uygulama", ad=metin_al(k["uygulama"]["ad"], self.lang)), "ana",
                            self._uygulamayi_ac, k)
            b.set_halign(Gtk.Align.START)
            kutu.pack_start(b, False, False, 0)
        return kutu

    def _ozet_satiri(self, k):
        satir = Gtk.Box(spacing=10)
        e = tema.etiket(metin_al(k.get("ozet"), self.lang), "kart-alt", sar=True, genislik=100)
        satir.pack_start(e, True, True, 0)
        if k.get("root"):
            r = tema.rozet(self.t("kok_notu"), "sari")
            satir.pack_end(r, False, False, 0)
        return satir

    def _uygulamayi_ac(self, k):
        if not ac(k["uygulama"]["komut"]):
            self.kabuk.bildir(self.t("uygulama_yok", ad=metin_al(k["uygulama"]["ad"], self.lang)), "hata")

    # -- animasyon --------------------------------------------------------------
    def _animasyon_karti(self, k):
        dis, ic = tema.kart(dolgu=16, aralik=10)
        cz = fz.derle(k["sahne"], k["adimlar"], self.lang)
        self._cz = cz
        self._t = 0.0
        self._palet = tema.palet(self.ayar["tema"], k.get("vurgu", "guvenlik"))
        self._sahne = k["sahne"]

        oran = k["sahne"]["yukseklik"] / float(k["sahne"]["genislik"])
        yukseklik = max(260, min(460, int(640 * oran)))
        canvas = tema.CizimAlani(self._ciz, -1, yukseklik)
        self._canvas = canvas
        cerceve = Gtk.Frame()
        tema.sinif(cerceve, "mono")
        cerceve.add(canvas)
        ic.pack_start(cerceve, False, False, 0)

        denetim = Gtk.Box(spacing=8)
        self._oynat_dugme = tema.dugme(self.t("duraklat"), "kucuk", self._oynat_duraklat)
        denetim.pack_start(self._oynat_dugme, False, False, 0)
        denetim.pack_start(tema.dugme(self.t("bastan"), "kucuk duz", self._bastan), False, False, 0)
        hiz_kutu, _ = tema.secim_grubu(HIZLAR, "1", self._hiz_degisti)
        denetim.pack_end(hiz_kutu, False, False, 0)
        ic.pack_start(denetim, False, False, 0)

        if cz.adim_baslangiclari:
            cips_baslik = tema.etiket(self.t("adimlar_basligi"), "kart-alt")
            ic.pack_start(cips_baslik, False, False, 0)
            cips = Gtk.FlowBox()
            cips.set_selection_mode(Gtk.SelectionMode.NONE)
            cips.set_max_children_per_line(6)
            cips.set_row_spacing(6)
            cips.set_column_spacing(6)
            for i, (baslik, ms) in enumerate(cz.adim_baslangiclari):
                etiket_metni = f"{i + 1}. {baslik}" if baslik else str(i + 1)
                b = tema.dugme(etiket_metni, "kucuk duz", self._adima_git, ms)
                cips.add(b)
            ic.pack_start(cips, False, False, 0)

        self._oynuyor = True
        self._zamanlayiciyi_baslat()
        return dis

    def _ciz(self, cr, w, h, _veri):
        if self._cz is None:
            return
        fc.sahne_ciz(cr, w, h, self._sahne, self._cz.durum(self._t), self.lang, self._palet, self._t)

    def _zamanlayiciyi_baslat(self):
        self._zamanlayiciyi_durdur()
        self._zamanlayici_id = GLib.timeout_add(33, self._adim)

    def _zamanlayiciyi_durdur(self):
        if self._zamanlayici_id is not None:
            GLib.source_remove(self._zamanlayici_id)
            self._zamanlayici_id = None

    def _adim(self):
        if self._cz is None:
            return False
        if self._oynuyor:
            self._t += 33 * self._hiz
            if self._t >= self._cz.toplam:
                self._t = float(self._cz.toplam)
                self._oynuyor = False
                self._oynat_dugme.set_label(self.t("oynat"))
        if self._canvas is not None:
            self._canvas.queue_draw()
        return True

    def _oynat_duraklat(self, *_):
        if self._cz is None:
            return
        if not self._oynuyor and self._t >= self._cz.toplam:
            self._t = 0.0
        self._oynuyor = not self._oynuyor
        self._oynat_dugme.set_label(self.t("duraklat") if self._oynuyor else self.t("oynat"))

    def _bastan(self, *_):
        self._t = 0.0
        self._oynuyor = True
        self._oynat_dugme.set_label(self.t("duraklat"))
        if self._canvas is not None:
            self._canvas.queue_draw()

    def _hiz_degisti(self, anahtar):
        try:
            self._hiz = float(anahtar)
        except (TypeError, ValueError):
            self._hiz = 1.0

    def _adima_git(self, ms):
        self._t = float(ms)
        self._oynuyor = True
        self._oynat_dugme.set_label(self.t("duraklat"))
        if self._canvas is not None:
            self._canvas.queue_draw()

    # -- detay kartlari -----------------------------------------------------------
    def _bolum_karti(self, baslik, bloklar):
        dis, ic = tema.kart(dolgu=16, aralik=10)
        tema.kart_basligi(ic, metin_al(baslik, self.lang))
        for blok in bloklar:
            tur = blok[0]
            icerik = blok[1]
            ic.pack_start(self._blok_widget(tur, icerik), False, False, 0)
        return dis

    def _blok_widget(self, tur, icerik):
        if tur == "p":
            return tema.etiket(metin_al(icerik, self.lang), None, sar=True, genislik=100)
        if tur == "liste":
            kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            for madde in icerik:
                satir = Gtk.Box(spacing=8)
                nokta = tema.etiket("•", "soluk")
                nokta.set_valign(Gtk.Align.START)
                satir.pack_start(nokta, False, False, 0)
                satir.pack_start(tema.etiket(metin_al(madde, self.lang), None, sar=True, genislik=100),
                                  True, True, 0)
                kutu.pack_start(satir, False, False, 0)
            return kutu
        if tur == "kod":
            kutu = Gtk.Box()
            tema.sinif(kutu, "secili-satir")
            e = tema.etiket(icerik, "mono", sar=True, genislik=100)
            e.set_margin_top(10)
            e.set_margin_bottom(10)
            e.set_margin_start(14)
            e.set_margin_end(14)
            kutu.pack_start(e, True, True, 0)
            return kutu
        if tur == "not":
            kutu, _ = tema.not_kutusu(metin_al(icerik, self.lang), "bilgi")
            return kutu
        if tur == "uyari":
            kutu, _ = tema.not_kutusu(metin_al(icerik, self.lang), "uyari")
            return kutu
        if tur == "tablo":
            izgara = Gtk.Grid()
            izgara.set_row_spacing(6)
            izgara.set_column_spacing(16)
            for i, (sol, sag) in enumerate(icerik):
                es = tema.etiket(metin_al(sol, self.lang), "kart-baslik", sar=True, genislik=36)
                ed = tema.etiket(metin_al(sag, self.lang), None, sar=True, genislik=64)
                izgara.attach(es, 0, i, 1, 1)
                izgara.attach(ed, 1, i, 1, 1)
            return izgara
        return tema.etiket(metin_al(icerik, self.lang) if isinstance(icerik, (dict, str)) else "", None, sar=True)


def main():
    ayrıstırıcı = argparse.ArgumentParser(description="CarotOS Former")
    ayrıstırıcı.add_argument("--konu", dest="konu", default=None, help="Dogrudan acilacak konu kimligi")
    args = ayrıstırıcı.parse_args()
    pencere = Uygulama(konu_id=args.konu)
    pencere.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
