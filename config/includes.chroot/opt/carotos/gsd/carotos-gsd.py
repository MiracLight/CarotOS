#!/usr/bin/env python3
"""
CarotOS GSD (General System Dictionary)
Linux, ag, siber guvenlik, kriptografi, algoritma ve genel bilgisayar
bilimi hakkinda aranabilir, iki dilli bir sozluk uygulamasi.
"""
import argparse
import json
import os
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango  # noqa: E402

sys.path.insert(0, "/opt/carotos/ortak")
sys.path.insert(0, "/opt/carotos/gsd")

import tema  # noqa: E402
import terimler  # noqa: E402

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "carotos-gsd")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")
BURASI = os.path.dirname(os.path.abspath(__file__))


def logo_bul():
    kok = os.path.abspath(os.path.join(BURASI, "..", "..", ".."))
    for yol in ("/usr/share/icons/hicolor/256x256/apps/carotos-gsd.png",
                "/usr/share/icons/hicolor/scalable/apps/carotos-gsd.svg",
                os.path.join(kok, "usr/share/icons/hicolor/256x256/apps/carotos-gsd.png"),
                os.path.join(kok, "usr/share/icons/hicolor/scalable/apps/carotos-gsd.svg")):
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


def T(tr, en):
    """Iki dilli metin."""
    return {"tr": tr, "en": en}


def metin_al(m, dil):
    if isinstance(m, dict):
        return m.get(dil) or m.get("tr") or ""
    return "" if m is None else str(m)


# Turkce-duyarli kucuk harfe cevirme: arama ve siralamada "İstanbul" ile
# "istanbul", "VPN" ile "vpn" ayni sekilde eslessin.
_TR_KUCUK = str.maketrans("İIĞÜŞÖÇ", "iığüşöç")


def _kucult(s):
    return (s or "").translate(_TR_KUCUK).lower()


# Doğru Türkçe alfabe sırası (q/w/x Türkçe'de yok ama İngilizce terimlerde
# geçebildiği için en yakın konuma eklendi). Bu tablo duz ASCII a-z icin de
# ayni bagil sirayi korur, yani Ingilizce basliklar da doğru sıralanır.
_TR_SIRA_HARF = "abcçdefgğhıijklmnoöpqrsştuüvwxyz"
_TR_SIRA_INDEKS = {ch: i for i, ch in enumerate(_TR_SIRA_HARF)}


def _tr_anahtar(s):
    """Dogru Turkce alfabe sirasina gore karsilastirilabilir anahtar uretir."""
    s = _kucult(s)
    return [_TR_SIRA_INDEKS.get(ch, 1000 + ord(ch)) for ch in s]


KATEGORI_IKON = {
    "linux": "arac",
    "ag": "ag",
    "guvenlik": "kalkan",
    "kriptografi": "kilit",
    "algoritma": "liste",
    "genel": "kitap",
}

STRINGS = {
    "app_title": T("CarotOS GSD", "CarotOS GSD"),
    "marka_alt": T("Genel Sistem Sözlüğü", "General System Dictionary"),
    "arama_ipucu": T("Terim ara…", "Search terms…"),
    "kat_tumu": T("Tümü", "All"),
    "eslesen_sayisi": T("{eslesen} / {toplam} terim", "{eslesen} / {toplam} terms"),
    "bos_baslik": T("Bir terim seçin", "Pick a term"),
    "bos_alt": T("Soldaki listeden bir terim seçin ya da arama kutusuna yazmaya başlayın. "
                 "Linux, ağ, siber güvenlik, kriptografi, algoritma ve genel bilgisayar bilimi "
                 "üzerine 150'den fazla terim burada.",
                 "Pick a term from the list on the left, or start typing in the search box. "
                 "There are over 150 terms here on Linux, networking, cybersecurity, "
                 "cryptography, algorithms and general computer science."),
    "sonuc_yok_baslik": T("Sonuç bulunamadı", "No results found"),
    "sonuc_yok_alt": T("Farklı bir arama terimi deneyin ya da kategori filtresini değiştirin.",
                        "Try a different search term or change the category filter."),
    "ornek_basligi": T("Örnek", "Example"),
    "ilgili_basligi": T("İlgili terimler", "Related terms"),
}


def main():
    ayrıstırıcı = argparse.ArgumentParser(description="CarotOS GSD")
    ayrıstırıcı.add_argument("--terim", dest="terim", default=None,
                              help="Dogrudan acilacak terim kimligi")
    args = ayrıstırıcı.parse_args()
    pencere = Uygulama(terim_id=args.terim)
    pencere.connect("destroy", Gtk.main_quit)
    Gtk.main()


class Uygulama(Gtk.Window):
    def __init__(self, terim_id=None):
        super().__init__()
        self.ayar = ayar_oku()
        if self.ayar.get("dil") not in ("tr", "en"):
            self.ayar["dil"] = _varsayilan_dil()
        if self.ayar.get("tema") not in ("dark", "light"):
            self.ayar["tema"] = "dark"
        self.lang = self.ayar["dil"]
        tema.uygula(self.ayar["tema"], "gsd")

        self.set_title(metin_al(STRINGS["app_title"], "tr"))
        self.set_default_size(1150, 780)
        self.set_size_request(900, 580)
        self.set_position(Gtk.WindowPosition.CENTER)
        try:
            if LOGO:
                self.set_icon_from_file(LOGO)
            else:
                self.set_icon_name("carotos-gsd")
        except GLib.Error:
            pass
        self.connect("destroy", self._kapaniyor)

        # -- veri --------------------------------------------------------
        self.tumu = terimler.tumu()
        self.terimler = {t["id"]: t for t in self.tumu}
        self._arama_metni = {}
        for t in self.tumu:
            parcalar = [
                t["id"],
                metin_al(t.get("baslik"), "tr"), metin_al(t.get("baslik"), "en"),
                metin_al(t.get("kisa"), "tr"), metin_al(t.get("kisa"), "en"),
                metin_al(t.get("aciklama"), "tr"), metin_al(t.get("aciklama"), "en"),
                t.get("ornek") or "",
            ]
            self._arama_metni[t["id"]] = _kucult(" ".join(parcalar))

        self.kategori_filtre = "tumu"
        self._arama_sorgu = ""
        self._aktif_id = None
        self._kat_kilit = False

        # -- arayuz --------------------------------------------------------
        self._arayuz_kur()
        self._metinleri_uygula()
        self._listeyi_yenile()

        if terim_id and terim_id in self.terimler:
            self._terime_git(terim_id)
        else:
            self._bos_goster()

        self.show_all()
        if terim_id and terim_id in self.terimler:
            self._terime_git(terim_id)
        else:
            self.liste.unselect_all()
            self._bos_goster()

    # -- genel ---------------------------------------------------------------
    def t(self, anahtar, **kw):
        m = metin_al(STRINGS[anahtar], self.lang)
        return m.format(**kw) if kw else m

    def _kapaniyor(self, *_):
        if Gtk.main_level() > 0:
            Gtk.main_quit()

    # -- arayuz kurulumu ---------------------------------------------------
    def _arayuz_kur(self):
        kok = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(kok)

        # -- sol: arama + kategori + liste ----------------------------------
        sol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tema.sinif(sol, "yan")
        sol.set_size_request(300, -1)

        ust_marka = Gtk.Box(spacing=10)
        ust_marka.set_margin_top(20)
        ust_marka.set_margin_start(20)
        ust_marka.set_margin_end(14)
        ust_marka.set_margin_bottom(4)
        if LOGO:
            try:
                from gi.repository import GdkPixbuf
                ust_marka.pack_start(Gtk.Image.new_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_size(LOGO, 36, 36)), False, False, 0)
            except Exception:
                pass
        mv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        mv.set_valign(Gtk.Align.CENTER)
        self.marka_ad = tema.etiket("", "marka")
        self.marka_alt = tema.etiket("", "marka-alt")
        self.marka_alt.set_ellipsize(Pango.EllipsizeMode.END)
        mv.pack_start(self.marka_ad, False, False, 0)
        mv.pack_start(self.marka_alt, False, False, 0)
        ust_marka.pack_start(mv, True, True, 0)
        sol.pack_start(ust_marka, False, False, 0)

        arama_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        arama_kutu.set_margin_start(18)
        arama_kutu.set_margin_end(18)
        self.arama = Gtk.SearchEntry()
        self.arama.connect("search-changed", self._arama_degisti)
        arama_kutu.pack_start(self.arama, False, False, 0)
        arama_kutu.pack_start(self._kategori_cipleri_kur(), False, False, 0)
        self.sayac = tema.etiket("", "kart-alt soluk", x=0.0)
        arama_kutu.pack_start(self.sayac, False, False, 0)
        sol.pack_start(arama_kutu, False, False, 0)

        kaydir = Gtk.ScrolledWindow()
        kaydir.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.liste = Gtk.ListBox()
        tema.sinif(self.liste, "menu")
        self.liste.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.liste.set_filter_func(self._satir_filtre)
        self.liste.set_sort_func(self._satir_sirala)
        self.liste.connect("row-selected", self._satir_secildi)
        for t in self.tumu:
            self.liste.add(self._satir_olustur(t["id"]))
        kaydir.add(self.liste)
        sol.pack_start(kaydir, True, True, 0)

        # alt: dil + gorunum (diger CarotOS uygulamalariyla ayni yer)
        alt = Gtk.Box(spacing=8)
        alt.set_margin_start(18)
        alt.set_margin_end(18)
        alt.set_margin_bottom(16)
        alt.set_margin_top(4)
        self.dil_kutu = Gtk.ComboBoxText()
        self.dil_kutu.append("tr", "Türkçe")
        self.dil_kutu.append("en", "English")
        self.dil_kutu.set_active_id(self.lang)
        self.dil_kutu.connect("changed", self._dil_degisti)
        alt.pack_start(self.dil_kutu, True, True, 0)
        self.tema_dugme = tema.dugme("☀" if self.ayar["tema"] == "dark" else "☾", None,
                                      self._tema_degistir)
        alt.pack_start(self.tema_dugme, False, False, 0)
        sol.pack_start(alt, False, False, 0)

        kok.pack_start(sol, False, False, 0)

        # -- sag: detay paneli ------------------------------------------------
        sag = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        tema.sinif(sag, "arka")
        self.sag_kaydir = Gtk.ScrolledWindow()
        self.sag_kaydir.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sag.pack_start(self.sag_kaydir, True, True, 0)
        kok.pack_start(sag, True, True, 0)

    def _kategori_cipleri_kur(self):
        akis = Gtk.FlowBox()
        akis.set_selection_mode(Gtk.SelectionMode.NONE)
        akis.set_max_children_per_line(3)
        akis.set_min_children_per_line(1)
        akis.set_row_spacing(6)
        akis.set_column_spacing(6)
        akis.set_homogeneous(False)
        self.kat_dugmeleri = {}
        for anahtar in ["tumu"] + list(terimler.SIRA):
            d = Gtk.ToggleButton(label="")
            tema.sinif(d, "secim kucuk")
            d.set_active(anahtar == self.kategori_filtre)
            d.connect("toggled", self._kategori_tiklandi, anahtar)
            self.kat_dugmeleri[anahtar] = d
            akis.add(d)
        self.kat_akis = akis
        return akis

    # -- metinler / dil -------------------------------------------------------
    def _metinleri_uygula(self):
        self.set_title(self.t("app_title"))
        self.marka_ad.set_text(self.t("app_title"))
        self.marka_alt.set_text(self.t("marka_alt"))
        self.arama.set_placeholder_text(self.t("arama_ipucu"))
        self.kat_dugmeleri["tumu"].set_label(self.t("kat_tumu"))
        for kat in terimler.SIRA:
            self.kat_dugmeleri[kat].set_label(
                metin_al(terimler.KATEGORILER[kat]["ad"], self.lang))
        for row in self.liste.get_children():
            t = self.terimler[row.terim_id]
            row.ad.set_text(metin_al(t["baslik"], self.lang))
        self.liste.invalidate_sort()
        self._guncelle_sayac()

    def _dil_degisti(self, combo):
        kid = combo.get_active_id()
        if kid and kid != self.lang:
            self.lang = kid
            self.ayar["dil"] = kid
            ayar_yaz(self.ayar)
            self._metinleri_uygula()
            if self._aktif_id:
                self._detay_goster(self._aktif_id)
            else:
                self._bos_goster()

    def _tema_degistir(self, *_):
        yeni = "light" if self.ayar["tema"] == "dark" else "dark"
        self.ayar["tema"] = yeni
        ayar_yaz(self.ayar)
        tema.uygula(yeni, "gsd")
        self.tema_dugme.set_label("☀" if yeni == "dark" else "☾")
        if self._aktif_id:
            self._detay_goster(self._aktif_id)
        else:
            self._bos_goster()

    # -- liste / filtre -------------------------------------------------------
    def _satir_olustur(self, tid):
        t = self.terimler[tid]
        row = Gtk.ListBoxRow()
        row.terim_id = tid
        row.set_can_focus(False)
        b = Gtk.Box(spacing=10)
        b.set_margin_top(7)
        b.set_margin_bottom(7)
        b.set_margin_start(10)
        b.set_margin_end(10)
        row.ikon = tema.Ikon(KATEGORI_IKON.get(t["kategori"], "kitap"), 15, t["kategori"])
        row.ad = tema.etiket(metin_al(t["baslik"], self.lang), "menu-yazi")
        row.ad.set_ellipsize(Pango.EllipsizeMode.END)
        b.pack_start(row.ikon, False, False, 0)
        b.pack_start(row.ad, True, True, 0)
        row.add(b)
        return row

    def _satir_filtre(self, row):
        t = self.terimler[row.terim_id]
        if self.kategori_filtre != "tumu" and t["kategori"] != self.kategori_filtre:
            return False
        if not self._arama_sorgu:
            return True
        return self._arama_sorgu in self._arama_metni[row.terim_id]

    def _satir_sirala(self, row1, row2):
        a = _tr_anahtar(metin_al(self.terimler[row1.terim_id]["baslik"], self.lang))
        b = _tr_anahtar(metin_al(self.terimler[row2.terim_id]["baslik"], self.lang))
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    def _arama_degisti(self, entry):
        self._arama_sorgu = _kucult(entry.get_text().strip())
        self._listeyi_yenile()

    def _kategori_tiklandi(self, _d, anahtar):
        if self._kat_kilit:
            return
        self._kat_kilit = True
        for k, dd in self.kat_dugmeleri.items():
            dd.set_active(k == anahtar)
        self._kat_kilit = False
        if self.kategori_filtre != anahtar:
            self.kategori_filtre = anahtar
            self._listeyi_yenile()

    def _listeyi_yenile(self):
        self.liste.invalidate_filter()
        self._guncelle_sayac()
        gorunur_idler = {r.terim_id for r in self.liste.get_children() if r.get_child_visible()}
        if self._aktif_id is not None and self._aktif_id in gorunur_idler:
            return  # secili terim hala gorunur, detay panelini degistirme
        self.liste.unselect_all()
        if gorunur_idler:
            self._bos_goster()
        else:
            self._sonuc_yok_goster()

    def _guncelle_sayac(self):
        eslesen = len([r for r in self.liste.get_children() if r.get_child_visible()])
        self.sayac.set_text(self.t("eslesen_sayisi", eslesen=eslesen, toplam=len(self.tumu)))

    def _satir_secildi(self, _liste, row):
        if row is None:
            return
        self._detay_goster(row.terim_id)

    def _terime_git(self, tid):
        """Aramayi/kategoriyi sifirlayip verilen terime atlar (ilgili terim
        tiklamalarinda kullanilir)."""
        if self.kategori_filtre != "tumu":
            self.kategori_filtre = "tumu"
            for k, dd in self.kat_dugmeleri.items():
                dd.set_active(k == "tumu")
        if self._arama_sorgu:
            self._arama_sorgu = ""
            self.arama.set_text("")
        self.liste.invalidate_filter()
        self._guncelle_sayac()
        for row in self.liste.get_children():
            if row.terim_id == tid:
                self.liste.select_row(row)
                row.grab_focus()
                break

    # -- detay paneli ---------------------------------------------------------
    def _icerik_ayarla(self, widget):
        eski = self.sag_kaydir.get_child()
        if eski is not None:
            self.sag_kaydir.remove(eski)
        self.sag_kaydir.add(widget)
        widget.show_all()

    def _bos_goster(self):
        self._aktif_id = None
        self._icerik_ayarla(self._durum_sarmalayici(
            tema.bos_durum("kitap", self.t("bos_baslik"), self.t("bos_alt"))))

    def _sonuc_yok_goster(self):
        self._aktif_id = None
        self._icerik_ayarla(self._durum_sarmalayici(
            tema.bos_durum("arama", self.t("sonuc_yok_baslik"), self.t("sonuc_yok_alt"))))

    def _durum_sarmalayici(self, ic):
        dis = Gtk.Box()
        dis.set_valign(Gtk.Align.CENTER)
        dis.set_halign(Gtk.Align.CENTER)
        dis.set_margin_top(60)
        dis.set_margin_start(40)
        dis.set_margin_end(40)
        ic.set_size_request(380, -1)
        dis.pack_start(ic, True, True, 0)
        return dis

    def _detay_goster(self, tid):
        self._aktif_id = tid
        t = self.terimler[tid]
        kat = terimler.KATEGORILER[t["kategori"]]

        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        kutu.set_margin_top(24)
        kutu.set_margin_bottom(32)
        kutu.set_margin_start(32)
        kutu.set_margin_end(32)

        # ust satir: baslik + kategori rozeti
        ust = Gtk.Box(spacing=12)
        basv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        baslik = tema.etiket(metin_al(t["baslik"], self.lang), "sayfa-baslik", sar=True, genislik=60)
        basv.pack_start(baslik, False, False, 0)
        ust.pack_start(basv, True, True, 0)
        r = tema.rozet(metin_al(kat["ad"], self.lang), t["kategori"])
        r.set_valign(Gtk.Align.START)
        ust.pack_end(r, False, False, 0)
        kutu.pack_start(ust, False, False, 0)

        # kisa tanim (vurgulu giris cumlesi)
        kisa = tema.etiket(metin_al(t["kisa"], self.lang), "kart-alt", sar=True, genislik=90)
        kutu.pack_start(kisa, False, False, 0)

        # ayrintili aciklama (bir ya da birden fazla paragraf)
        aciklama = metin_al(t["aciklama"], self.lang)
        for paragraf in aciklama.split("\n\n"):
            paragraf = paragraf.strip()
            if not paragraf:
                continue
            p = tema.etiket(paragraf, None, sar=True, genislik=92)
            kutu.pack_start(p, False, False, 0)

        # ornek (varsa)
        if t.get("ornek"):
            dis, ic = tema.kart(dolgu=14, aralik=8)
            tema.kart_basligi(ic, self.t("ornek_basligi"))
            ornek_kutu = Gtk.Box()
            tema.sinif(ornek_kutu, "secili-satir")
            e = tema.etiket(t["ornek"], "mono", sar=True, genislik=90)
            e.set_margin_top(10)
            e.set_margin_bottom(10)
            e.set_margin_start(14)
            e.set_margin_end(14)
            ornek_kutu.pack_start(e, True, True, 0)
            ic.pack_start(ornek_kutu, False, False, 0)
            kutu.pack_start(dis, False, False, 0)

        # ilgili terimler (varsa)
        ilgili = [i for i in t.get("ilgili", []) if i in self.terimler]
        if ilgili:
            ilgili_baslik = tema.etiket(self.t("ilgili_basligi"), "kart-alt")
            kutu.pack_start(ilgili_baslik, False, False, 0)
            akis = Gtk.FlowBox()
            akis.set_selection_mode(Gtk.SelectionMode.NONE)
            akis.set_max_children_per_line(6)
            akis.set_row_spacing(6)
            akis.set_column_spacing(6)
            akis.set_homogeneous(False)
            for iid in ilgili:
                etiket_metni = metin_al(self.terimler[iid]["baslik"], self.lang)
                b = tema.dugme(etiket_metni, "kucuk duz", self._terime_git, iid)
                akis.add(b)
            kutu.pack_start(akis, False, False, 0)

        self._icerik_ayarla(kutu)


if __name__ == "__main__":
    main()
