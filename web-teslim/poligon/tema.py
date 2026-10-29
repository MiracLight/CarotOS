# -*- coding: utf-8 -*-
"""
CarotOS ortak gorsel dil (GTK 3): "grafit" temasi.

Butun CarotOS uygulamalari ayni zemin, kart ve yazi tonlarini kullanir; her
uygulamanin kendi vurgu rengi vardir (CarotPot mor, Carotene turuncu...).
Koyu ve acik olmak uzere iki gorunum vardir; vurgu rengi ikisinde de aynidir.

Bu modul sunlari verir:
  * palet / css uretimi:      palet(), css(), uygula()
  * uygulama kabugu:          Kabuk (kenar menusu, sayfa basligi, bildirim seridi)
  * kucuk parcalar:           etiket(), kart(), kart_basligi(), rozet(), dugme(),
                              KpiKutusu, DurumHapi, not_kutusu(), bos_durum(),
                              AcilirSecim (uzun listeler icin kaydirmali acilir secim)
  * cizim yardimcilari:       rgb(), yuvarlak(), yazi(), CizimAlani, Ikon
  * hazir grafikler:          cubuk_grafik(), yatay_cubuklar(), halka()
  * pencereler:               onay_sor()

Karar (1.3): lacivert tek palet yerine grafit zemin + uygulamaya ozel vurgu.
Ayrintisi docs/CarotOS_Uygulama_Gelistirme_Standartlari.md bolum 3'te.
"""

import math

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, GdkPixbuf, GLib, GObject, Gtk, Pango, PangoCairo  # noqa: E402

# ---------------------------------------------------------------------------
# Renkler
# ---------------------------------------------------------------------------

ZEMINLER = {
    "dark": {
        "zemin": "#14161d", "yan": "#1a1d26", "kart": "#1f2330", "kart2": "#262b3a",
        "cizgi": "#2e3446", "yazi": "#e8e9f0", "soluk": "#8d93a8", "silik": "#5b6278",
        "golge": "rgba(0,0,0,0.0)",
    },
    "light": {
        "zemin": "#f2f3f7", "yan": "#e8eaf1", "kart": "#ffffff", "kart2": "#eef0f6",
        "cizgi": "#d8dbe5", "yazi": "#1b1e29", "soluk": "#5b6177", "silik": "#9298ad",
        "golge": "rgba(20,22,29,0.05)",
    },
}

# Durum renkleri: anlam tasir, uygulamadan bagimsizdir.
DURUM = {
    "dark": {"kirmizi": "#e5534b", "sari": "#e3b341", "yesil": "#3fb950",
             "turuncu": "#ff8a3d", "camgobegi": "#3ec7c0", "mavi": "#5aa9e6",
             "pembe": "#d16ba5", "limon": "#9ccc65", "gri": "#5b6278"},
    "light": {"kirmizi": "#d1453e", "sari": "#b8862b", "yesil": "#2f8a3e",
              "turuncu": "#e8711f", "camgobegi": "#1f9e98", "mavi": "#2f86cc",
              "pembe": "#b9508b", "limon": "#6d9b36", "gri": "#8a90a3"},
}

# Uygulama vurgulari (ana ton). Yeni uygulama icin buraya bir satir eklenir.
VURGULAR = {
    "carotpot": "#8b7fd6",     # mor
    "health": "#4fb38a",       # nane yesili
    "carotene": "#ff8a3d",     # havuc turuncusu
    "usb": "#3ec7c0",          # camgobegi
    "guvenlik": "#e3a33b",     # kehribar
    "karsilama": "#378ada",    # marka mavisi (web sitesiyle ortak)
    "magaza": "#d16ba5",       # pembe
    "poligon": "#b4de4f",      # elektrik limon yesili (egitim poligonu)
    "filenor": "#3f9be6",      # gok mavisi (dosya donusturucu)
    "former": "#f0747a",       # mercan (rehber / egitim)
    "gsd": "#6366f1",          # indigo (sozluk / bilgi)
}


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _karistir(a, b, oran):
    """a rengini b'ye dogru 'oran' kadar yaklastirir (0..1)."""
    ra, rb = _hex(a), _hex(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * oran) for x, y in zip(ra, rb))


def rgba_metni(h, alfa):
    r, g, b = _hex(h)
    return f"rgba({r},{g},{b},{alfa})"


def palet(gorunum="dark", vurgu="carotpot"):
    """Butun renkleri tek sozlukte dondurur. vurgu: VURGULAR anahtari ya da
    '#rrggbb'."""
    gorunum = gorunum if gorunum in ZEMINLER else "dark"
    v = VURGULAR.get(vurgu, vurgu if str(vurgu).startswith("#") else VURGULAR["carotpot"])
    p = dict(ZEMINLER[gorunum])
    p.update(DURUM[gorunum])
    p["gorunum"] = gorunum
    p["vurgu"] = v
    if gorunum == "dark":
        p["vurgu_yazi"] = _karistir(v, "#ffffff", 0.42)    # koyu zeminde okunur ton
        p["vurgu_koyu"] = _karistir(v, "#000000", 0.30)
    else:
        p["vurgu_yazi"] = _karistir(v, "#000000", 0.28)
        p["vurgu_koyu"] = _karistir(v, "#000000", 0.18)
    p["vurgu_zemin"] = rgba_metni(v, 0.16)
    p["ana_yazi"] = "#ffffff"
    return p


# Etkin palet: cizim fonksiyonlari renkleri buradan okur (uygula() gunceller).
AKTIF = palet()


def renk(ad):
    """Etkin paletten renk; '#..' verilirse aynen dondurur."""
    return ad if str(ad).startswith("#") else AKTIF.get(ad, AKTIF["yazi"])


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def css(p):
    return f"""
window, dialog, .arka {{ background-color: {p['zemin']}; color: {p['yazi']}; }}
label {{ color: {p['yazi']}; }}
label:disabled {{ color: {p['silik']}; }}
*:focus {{ outline-color: {rgba_metni(p['vurgu'], 0.55)}; }}
tooltip, tooltip.background {{ background-color: {p['kart2']}; border: 1px solid {p['cizgi']}; border-radius: 6px; }}
tooltip label {{ color: {p['yazi']}; }}
separator {{ background-color: {p['cizgi']}; min-height: 1px; min-width: 1px; }}
scrolledwindow, viewport {{ background-color: transparent; border: none; }}
scrollbar {{ background-color: transparent; border: none; }}
scrollbar slider {{ background-color: {rgba_metni(p['soluk'], 0.35)}; border-radius: 6px; min-width: 6px; min-height: 6px; border: none; }}
scrollbar slider:hover {{ background-color: {rgba_metni(p['soluk'], 0.6)}; }}
selection, *:selected {{ background-color: {rgba_metni(p['vurgu'], 0.35)}; color: {p['yazi']}; }}

/* kenar menusu */
.yan {{ background-color: {p['yan']}; border-right: 1px solid {rgba_metni(p['cizgi'], 0.6)}; }}
.marka {{ font-weight: 800; font-size: 120%; }}
.marka-alt {{ color: {p['soluk']}; font-size: 85%; }}
list.menu, .menu {{ background-color: transparent; border: none; box-shadow: none; }}
.menu row {{ border-radius: 8px; margin: 1px 10px; padding: 0; outline: none; background-color: transparent; }}
.menu row:hover {{ background-color: {rgba_metni(p['kart2'], 0.6)}; }}
.menu row:selected {{ background-color: {p['kart2']}; }}
.menu row:selected .menu-yazi {{ color: {p['yazi']}; font-weight: bold; }}
.menu-yazi {{ color: {p['soluk']}; }}
.menu-sayi {{ background-color: {p['kirmizi']}; color: #ffffff; border-radius: 9px; padding: 0 7px; font-size: 80%; font-weight: bold; }}
.menu-sayi.sakin {{ background-color: {p['kart2']}; color: {p['soluk']}; }}
.menu-baslik {{ color: {p['silik']}; font-size: 75%; font-weight: bold; letter-spacing: 1px; }}

/* sayfa basligi */
.sayfa-baslik {{ font-size: 165%; font-weight: 800; }}
.sayfa-alt {{ color: {p['soluk']}; }}
.durum-hap {{ border-radius: 999px; padding: 4px 14px; border: 1px solid; }}
.durum-hap label {{ font-weight: bold; }}
.hap-acik {{ background-color: {rgba_metni(p['yesil'], 0.14)}; border-color: {rgba_metni(p['yesil'], 0.5)}; }}
.hap-acik label {{ color: {p['yesil']}; }}
.hap-kapali {{ background-color: {rgba_metni(p['soluk'], 0.12)}; border-color: {rgba_metni(p['soluk'], 0.4)}; }}
.hap-kapali label {{ color: {p['soluk']}; }}
.hap-uyari {{ background-color: {rgba_metni(p['sari'], 0.14)}; border-color: {rgba_metni(p['sari'], 0.5)}; }}
.hap-uyari label {{ color: {p['sari']}; }}
.hap-hata {{ background-color: {rgba_metni(p['kirmizi'], 0.14)}; border-color: {rgba_metni(p['kirmizi'], 0.5)}; }}
.hap-hata label {{ color: {p['kirmizi']}; }}

/* kartlar */
.kart {{ background-color: {p['kart']}; border: 1px solid {p['cizgi']}; border-radius: 12px; box-shadow: 0 1px 2px {p['golge']}; }}
.kart.vurgulu {{ border-color: {rgba_metni(p['vurgu'], 0.6)}; }}
.kart.tehlikeli {{ border-color: {rgba_metni(p['kirmizi'], 0.6)}; }}
.kart-baslik {{ font-weight: bold; font-size: 103%; }}
.kart-alt, .soluk {{ color: {p['soluk']}; font-size: 92%; }}
.silik {{ color: {p['silik']}; }}
.kpi-deger {{ font-size: 230%; font-weight: 800; }}
.kpi-deger.orta {{ font-size: 175%; }}
.kpi-ad {{ color: {p['soluk']}; font-size: 88%; }}
.fark-kotu {{ color: {p['kirmizi']}; font-size: 85%; font-weight: bold; }}
.fark-iyi {{ color: {p['yesil']}; font-size: 85%; font-weight: bold; }}
.fark-notr {{ color: {p['soluk']}; font-size: 85%; font-weight: bold; }}
.satir-ayrac {{ border-bottom: 1px solid {rgba_metni(p['cizgi'], 0.7)}; }}
.secili-satir {{ background-color: {p['kart2']}; border-radius: 10px; }}
.tiklanir:hover {{ background-color: {rgba_metni(p['kart2'], 0.7)}; border-radius: 10px; }}
.vurgu-yazi {{ color: {p['vurgu_yazi']}; }}
.basari-yazi {{ color: {p['yesil']}; }}
.hata-yazi {{ color: {p['kirmizi']}; }}
.uyari-yazi {{ color: {p['sari']}; }}
.ip {{ font-family: monospace; font-weight: bold; }}
.mono {{ font-family: monospace; color: {p['soluk']}; font-size: 92%; }}
.buyuk-baslik {{ font-size: 140%; font-weight: 800; }}

/* rozet ve etiket */
.rozet {{ border-radius: 5px; padding: 2px 8px; font-size: 78%; font-weight: bold; color: #ffffff; }}
.r-kirmizi {{ background-color: {p['kirmizi']}; }}
.r-sari {{ background-color: {_karistir(p['sari'], '#000000', 0.18)}; }}
.r-yesil {{ background-color: {_karistir(p['yesil'], '#000000', 0.15)}; }}
.r-vurgu {{ background-color: {p['vurgu_koyu']}; }}
.r-mavi {{ background-color: {_karistir(p['mavi'], '#000000', 0.2)}; }}
.r-gri {{ background-color: {p['kart2']}; color: {p['soluk']}; }}
.etiket {{ border-radius: 5px; padding: 1px 7px; font-size: 78%; background-color: {p['kart2']}; color: {p['vurgu_yazi']}; }}

/* not kutulari */
.not {{ border-radius: 10px; border: 1px solid; }}
.not label {{ color: {p['yazi']}; }}
.not-bilgi {{ background-color: {rgba_metni(p['vurgu'], 0.10)}; border-color: {rgba_metni(p['vurgu'], 0.35)}; }}
.not-uyari {{ background-color: {rgba_metni(p['sari'], 0.10)}; border-color: {rgba_metni(p['sari'], 0.4)}; }}
.not-hata {{ background-color: {rgba_metni(p['kirmizi'], 0.10)}; border-color: {rgba_metni(p['kirmizi'], 0.4)}; }}
.not-basari {{ background-color: {rgba_metni(p['yesil'], 0.10)}; border-color: {rgba_metni(p['yesil'], 0.4)}; }}

/* bildirim seridi */
.serit {{ background-color: {p['kart2']}; border: 1px solid {p['cizgi']}; border-radius: 10px; }}
.serit.serit-hata {{ border-color: {rgba_metni(p['kirmizi'], 0.6)}; }}
.serit.serit-basari {{ border-color: {rgba_metni(p['yesil'], 0.6)}; }}

/* dugmeler */
button {{ background-image: none; background-color: {p['kart2']}; border: 1px solid {p['cizgi']}; border-radius: 8px; padding: 5px 14px; box-shadow: none; text-shadow: none; -gtk-icon-shadow: none; color: {p['yazi']}; }}
button:hover {{ background-color: {_karistir(p['kart2'], p['yazi'], 0.06)}; }}
button:active, button:checked {{ background-color: {_karistir(p['kart2'], p['yazi'], 0.12)}; }}
button:disabled {{ opacity: 0.5; }}
button label {{ color: {p['yazi']}; }}
button.ana, button.suggested-action {{ background-color: {p['vurgu']}; border-color: {p['vurgu']}; }}
button.ana:hover, button.suggested-action:hover {{ background-color: {_karistir(p['vurgu'], '#ffffff', 0.12)}; }}
button.ana label, button.suggested-action label {{ color: #ffffff; font-weight: bold; }}
button.tehlike, button.destructive-action {{ background-color: {p['kirmizi']}; border-color: {p['kirmizi']}; }}
button.tehlike:hover, button.destructive-action:hover {{ background-color: {_karistir(p['kirmizi'], '#ffffff', 0.12)}; }}
button.tehlike label, button.destructive-action label {{ color: #ffffff; font-weight: bold; }}
button.duz {{ background-color: transparent; border-color: transparent; }}
button.duz:hover {{ background-color: {p['kart2']}; }}
button.secim {{ border-radius: 999px; padding: 4px 14px; }}
button.secim:checked {{ background-color: {p['vurgu']}; border-color: {p['vurgu']}; }}
button.secim:checked label {{ color: #ffffff; font-weight: bold; }}
button.kucuk {{ padding: 2px 10px; font-size: 90%; }}
switch {{ background-color: {p['kart2']}; border: 1px solid {p['cizgi']}; border-radius: 999px; }}
switch:checked {{ background-color: {p['vurgu']}; border-color: {p['vurgu']}; }}
switch slider {{ background-color: #ffffff; border-radius: 999px; border: none; box-shadow: 0 1px 2px rgba(0,0,0,0.25); }}
entry, spinbutton, textview, textview text {{ background-color: {p['kart2']}; color: {p['yazi']}; border-color: {p['cizgi']}; caret-color: {p['yazi']}; }}
entry, spinbutton {{ border: 1px solid {p['cizgi']}; border-radius: 8px; box-shadow: none; background-image: none; }}
entry:focus, spinbutton:focus {{ border-color: {p['vurgu']}; }}
spinbutton entry {{ border: none; background-color: transparent; }}
spinbutton button {{ border: none; background-color: transparent; border-radius: 0; padding: 0 6px; }}
combobox button, combobox button.combo {{ padding: 4px 10px; }}
combobox button label, combobox cellview {{ color: {p['yazi']}; }}
button.acilir-secim {{ padding: 6px 10px; }}
button.acilir-secim label {{ color: {p['yazi']}; }}
.acilir-ok {{ color: {p['soluk']}; }}
list.acilir-liste, list.acilir-liste row {{ background-color: transparent; }}
list.acilir-liste row {{ border-radius: 6px; padding: 6px 10px; color: {p['yazi']}; }}
list.acilir-liste row label {{ color: {p['yazi']}; }}
list.acilir-liste row:hover {{ background-color: {p['kart2']}; }}
list.acilir-liste row:selected {{ background-color: {rgba_metni(p['vurgu'], 0.22)}; }}
list.duz-liste, list.duz-liste row {{ background-color: transparent; border: none; outline: none; }}
menu, .menu-acilir, popover, popover.background {{ background-color: {p['kart']}; border: 1px solid {p['cizgi']}; border-radius: 8px; }}
menu menuitem, popover modelbutton {{ color: {p['yazi']}; padding: 6px 12px; }}
menu menuitem:hover, popover modelbutton:hover {{ background-color: {p['kart2']}; }}
menu menuitem label {{ color: {p['yazi']}; }}
calendar {{ background-color: {p['kart']}; color: {p['yazi']}; border: 1px solid {p['cizgi']}; }}
calendar:selected {{ background-color: {p['vurgu']}; color: #ffffff; }}
progressbar trough {{ background-color: {p['kart2']}; border: none; border-radius: 4px; min-height: 6px; }}
progressbar progress {{ background-color: {p['vurgu']}; border: none; border-radius: 4px; min-height: 6px; }}
check, radio {{ background-color: {p['kart2']}; background-image: none; border: 1px solid {p['cizgi']}; box-shadow: none; padding: 0; margin: 0 2px; min-width: 14px; min-height: 14px; color: #ffffff; }}
check {{ border-radius: 4px; }}
radio {{ border-radius: 999px; -gtk-icon-source: none; }}
check:checked {{ background-color: {p['vurgu']}; border-color: {p['vurgu']}; }}
radio:checked {{ background-color: #15210a; border: 4px solid {p['vurgu']}; min-width: 8px; min-height: 8px; }}
messagedialog .dialog-action-box button {{ margin: 4px; }}
"""


_saglayici = None


def uygula(gorunum="dark", vurgu="carotpot"):
    """Temayi ekrana uygular ve AKTIF paleti gunceller. Tekrar
    cagrilabilir (gorunum degisince)."""
    global _saglayici, AKTIF
    AKTIF = palet(gorunum, vurgu)
    ekran = Gdk.Screen.get_default()
    if _saglayici is None:
        _saglayici = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            ekran, _saglayici, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    _saglayici.load_from_data(css(AKTIF).encode())
    ayar = Gtk.Settings.get_default()
    if ayar is not None:
        ayar.set_property("gtk-application-prefer-dark-theme", AKTIF["gorunum"] == "dark")
    return AKTIF


# ---------------------------------------------------------------------------
# Kucuk parcalar
# ---------------------------------------------------------------------------

def sinif(w, siniflar):
    ctx = w.get_style_context()
    for c in (siniflar or "").split():
        ctx.add_class(c)
    return w


def etiket(metin="", siniflar=None, sar=False, sec=False, x=0.0, genislik=70):
    e = Gtk.Label(label=metin, xalign=x)
    if sar:
        e.set_line_wrap(True)
        e.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        e.set_max_width_chars(genislik)
    e.set_selectable(sec)
    return sinif(e, siniflar)


def kart(dolgu=18, aralik=10, siniflar=None):
    """(dis, ic) dondurur; icerik 'ic'e eklenir."""
    dis = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    sinif(dis, "kart " + (siniflar or ""))
    ic = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=aralik)
    ic.set_margin_top(dolgu)
    ic.set_margin_bottom(dolgu)
    ic.set_margin_start(dolgu + 2)
    ic.set_margin_end(dolgu + 2)
    dis.pack_start(ic, True, True, 0)
    return dis, ic


def kart_basligi(ic, baslik, alt=None, sag=None):
    """Kartin ust satiri. (baslik_etiketi, alt_etiketi) dondurur."""
    satir = Gtk.Box(spacing=10)
    sol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    b = etiket(baslik, "kart-baslik", sar=True)
    sol.pack_start(b, False, False, 0)
    a = None
    if alt is not None:
        a = etiket(alt, "kart-alt", sar=True, genislik=90)
        sol.pack_start(a, False, False, 0)
    satir.pack_start(sol, True, True, 0)
    if sag is not None:
        sag.set_valign(Gtk.Align.START)
        satir.pack_end(sag, False, False, 0)
    ic.pack_start(satir, False, False, 0)
    return b, a


def rozet(metin, renk_adi="gri"):
    r = etiket(metin, f"rozet r-{renk_adi}")
    r.set_valign(Gtk.Align.CENTER)
    return r


def rozet_ayarla(r, metin, renk_adi):
    ctx = r.get_style_context()
    for c in ("r-kirmizi", "r-sari", "r-yesil", "r-vurgu", "r-mavi", "r-gri"):
        ctx.remove_class(c)
    ctx.add_class(f"r-{renk_adi}")
    r.set_text(metin)


def dugme(metin, siniflar=None, tik=None, *arg):
    d = Gtk.Button(label=metin)
    d.set_valign(Gtk.Align.CENTER)
    sinif(d, siniflar)
    if tik is not None:
        d.connect("clicked", lambda _d: tik(*arg))
    return d


def secim_grubu(secenekler, secili, degisti):
    """Hap bicimli tek secimli dugme grubu. secenekler: [(anahtar, metin)].
    (kutu, {anahtar: dugme}) dondurur."""
    kutu = Gtk.Box(spacing=8)
    dugmeler = {}
    durum = {"kilit": False}

    def tiklandi(d, anahtar):
        if durum["kilit"]:
            return
        durum["kilit"] = True
        for k, dd in dugmeler.items():
            dd.set_active(k == anahtar)
        durum["kilit"] = False
        degisti(anahtar)

    for anahtar, metin in secenekler:
        d = Gtk.ToggleButton(label=metin)
        sinif(d, "secim")
        d.set_active(anahtar == secili)
        d.connect("toggled", tiklandi, anahtar)
        kutu.pack_start(d, False, False, 0)
        dugmeler[anahtar] = d
    return kutu, dugmeler


def not_kutusu(metin, tur="bilgi"):
    """tur: bilgi / uyari / hata / basari. (kutu, etiket) dondurur."""
    kutu = Gtk.Box()
    sinif(kutu, f"not not-{tur}")
    e = etiket(metin, None, sar=True, genislik=100)
    e.set_margin_top(10)
    e.set_margin_bottom(10)
    e.set_margin_start(14)
    e.set_margin_end(14)
    kutu.pack_start(e, True, True, 0)
    return kutu, e


def bos_durum(ikon, baslik, alt=None):
    kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    kutu.set_margin_top(28)
    kutu.set_margin_bottom(28)
    i = Ikon(ikon, 40, "silik")
    i.set_halign(Gtk.Align.CENTER)
    kutu.pack_start(i, False, False, 0)
    b = etiket(baslik, "kart-baslik", x=0.5)
    kutu.pack_start(b, False, False, 0)
    a = None
    if alt:
        a = etiket(alt, "kart-alt", sar=True, x=0.5)
        a.set_justify(Gtk.Justification.CENTER)
        kutu.pack_start(a, False, False, 0)
    kutu.baslik, kutu.alt = b, a
    return kutu


class AcilirSecim(Gtk.Box):
    """Uzun listeler icin ComboBoxText yerine: dugmeye basinca dugmenin altinda
    kaydirmali bir liste acilir. (GTK'nin klasik combo menusu cok ogeli
    listelerde konumu sasirip ustte buyuk bir bosluk birakabiliyordu.)

    ComboBoxText ile ayni cekirdek arayuz: append(), remove_all(), set_active(),
    set_active_id(), get_active(), get_active_id(), get_active_text(),
    metni_degistir() ve "changed" sinyali. Kimlikler metindir."""

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    EN_COK_YUKSEKLIK = 300

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._ogeler: list[list[str]] = []     # [kimlik, metin]
        self._aktif = -1
        self._dugme = Gtk.Button()
        sinif(self._dugme, "acilir-secim")
        ic = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._yazi = Gtk.Label(xalign=0)
        self._yazi.set_ellipsize(Pango.EllipsizeMode.END)
        ic.pack_start(self._yazi, True, True, 0)
        ok = Gtk.Label(label="\u25be")
        sinif(ok, "acilir-ok")
        ic.pack_end(ok, False, False, 0)
        self._dugme.add(ic)
        self._dugme.connect("clicked", self._ac)
        self.pack_start(self._dugme, True, True, 0)

        self._liste = Gtk.ListBox()
        self._liste.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._liste.set_activate_on_single_click(True)
        sinif(self._liste, "acilir-liste")
        self._liste.connect("row-activated", self._satir_secildi)
        self._kaydirma = Gtk.ScrolledWindow()
        self._kaydirma.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._kaydirma.set_propagate_natural_height(True)
        self._kaydirma.set_max_content_height(self.EN_COK_YUKSEKLIK)
        self._kaydirma.add(self._liste)
        self._kaydirma.set_margin_top(6)
        self._kaydirma.set_margin_bottom(6)
        self._kaydirma.set_margin_start(6)
        self._kaydirma.set_margin_end(6)
        self._kaydirma.show_all()
        self._acilir = Gtk.Popover.new(self._dugme)
        self._acilir.set_position(Gtk.PositionType.BOTTOM)
        self._acilir.add(self._kaydirma)
        self._yazi_guncelle()
        self.show_all()      # set_no_show_all kullanan ust pencereler icin cocuklar hazir olsun

    # --- ComboBoxText uyumlu arayuz ---------------------------------------
    def append(self, kimlik, metin):
        self._ogeler.append([str(kimlik), metin])
        satir = Gtk.ListBoxRow()
        etiket_ = Gtk.Label(label=metin, xalign=0)
        etiket_.set_ellipsize(Pango.EllipsizeMode.END)
        satir.add(etiket_)
        satir.show_all()
        self._liste.add(satir)

    def remove_all(self):
        self._ogeler = []
        self._aktif = -1
        for satir in self._liste.get_children():
            self._liste.remove(satir)
        self._yazi_guncelle()

    def set_active(self, indeks):
        if not (0 <= indeks < len(self._ogeler)):
            indeks = -1
        degisti = indeks != self._aktif
        self._aktif = indeks
        if indeks >= 0:
            self._liste.select_row(self._liste.get_row_at_index(indeks))
        self._yazi_guncelle()
        if degisti:
            self.emit("changed")

    def set_active_id(self, kimlik):
        for i, (k, _m) in enumerate(self._ogeler):
            if k == str(kimlik):
                self.set_active(i)
                return True
        return False

    def get_active(self):
        return self._aktif

    def get_active_id(self):
        return self._ogeler[self._aktif][0] if self._aktif >= 0 else None

    def get_active_text(self):
        return self._ogeler[self._aktif][1] if self._aktif >= 0 else None

    def metni_degistir(self, kimlik, metin):
        """Sinyal tetiklemeden bir ogenin gorunen metnini degistirir (dil degisimi)."""
        for i, oge in enumerate(self._ogeler):
            if oge[0] == str(kimlik):
                oge[1] = metin
                self._liste.get_row_at_index(i).get_child().set_text(metin)
        self._yazi_guncelle()

    def popdown(self):
        self._acilir.popdown()

    # --- ic isler ---------------------------------------------------------
    def _yazi_guncelle(self):
        self._yazi.set_text(self.get_active_text() or "")

    def _ac(self, _dugme):
        genislik = self._dugme.get_allocated_width()
        self._kaydirma.set_size_request(max(genislik - 12, 200), -1)
        if self._aktif >= 0:
            self._liste.select_row(self._liste.get_row_at_index(self._aktif))
        self._acilir.popup()
        if self._aktif >= 0:
            satir = self._liste.get_row_at_index(self._aktif)
            GLib.idle_add(self._satira_kaydir, satir)

    def _satira_kaydir(self, satir):
        alan = satir.get_allocation()
        ayar = self._kaydirma.get_vadjustment()
        ayar.set_value(max(0, alan.y - 40))
        return False

    def _satir_secildi(self, _liste, satir):
        self._acilir.popdown()
        self.set_active(satir.get_index())


class KpiKutusu(Gtk.Box):
    """Buyuk sayi + ad + degisim notu."""

    def __init__(self, ad="", deger="—"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        dis, ic = kart(16, 4)
        self.pack_start(dis, True, True, 0)
        self.ad = etiket(ad, "kpi-ad")
        ic.pack_start(self.ad, False, False, 0)
        s = Gtk.Box(spacing=10)
        self.deger = etiket(deger, "kpi-deger")
        s.pack_start(self.deger, False, False, 0)
        self.fark = etiket("", "fark-notr")
        self.fark.set_valign(Gtk.Align.END)
        self.fark.set_margin_bottom(8)
        s.pack_start(self.fark, False, False, 0)
        ic.pack_start(s, False, False, 0)

    def ayarla(self, deger=None, ad=None, fark=None, tur="notr", orta=False):
        if deger is not None:
            self.deger.set_text(str(deger))
            ctx = self.deger.get_style_context()
            (ctx.add_class if orta else ctx.remove_class)("orta")
        if ad is not None:
            self.ad.set_text(ad)
        if fark is not None:
            ctx = self.fark.get_style_context()
            for c in ("fark-kotu", "fark-iyi", "fark-notr"):
                ctx.remove_class(c)
            ctx.add_class(f"fark-{tur}")
            self.fark.set_text(fark)


class DurumHapi(Gtk.Box):
    """Ust sagdaki yuvarlak durum gostergesi."""

    def __init__(self):
        super().__init__()
        sinif(self, "durum-hap hap-kapali")
        self.set_valign(Gtk.Align.CENTER)
        self.e = etiket("")
        self.pack_start(self.e, False, False, 0)

    def ayarla(self, metin, tur="kapali"):
        ctx = self.get_style_context()
        for c in ("hap-acik", "hap-kapali", "hap-uyari", "hap-hata"):
            ctx.remove_class(c)
        ctx.add_class(f"hap-{tur}")
        self.e.set_text(("●  " if tur in ("acik", "hata", "uyari") else "○  ") + metin)


# ---------------------------------------------------------------------------
# Cairo yardimcilari
# ---------------------------------------------------------------------------

def rgb(ad, alfa=1.0):
    r, g, b = _hex(renk(ad))
    return (r / 255, g / 255, b / 255, alfa)


def yuvarlak(cr, x, y, w, h, r):
    r = max(0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def yazi(cr, x, y, metin, boyut=9.5, renk_adi="soluk", kalin=False, hiza="sol",
         dikey="taban", en_fazla=None):
    """Pango ile metin yazar. y: taban cizgisi (dikey='taban') ya da orta
    ('orta'). Yazilan genisligi dondurur."""
    duzen = PangoCairo.create_layout(cr)
    yazitipi = Pango.FontDescription.from_string(
        f"Sans {'Bold' if kalin else ''} {boyut}")
    duzen.set_font_description(yazitipi)
    duzen.set_text(str(metin), -1)
    if en_fazla:
        duzen.set_width(int(en_fazla * Pango.SCALE))
        duzen.set_ellipsize(Pango.EllipsizeMode.END)
    _m, mant = duzen.get_pixel_extents()
    w, h = mant.width, mant.height
    taban = duzen.get_baseline() / Pango.SCALE
    if hiza == "orta":
        x -= w / 2
    elif hiza == "sag":
        x -= w
    if dikey == "orta":
        y -= h / 2
    else:
        y -= taban
    cr.set_source_rgba(*rgb(renk_adi))
    cr.move_to(x, y)
    PangoCairo.show_layout(cr, duzen)
    return w


class CizimAlani(Gtk.DrawingArea):
    """ciz(cr, w, h, veri) fonksiyonuyla cizilen alan. veri_ayarla() ile
    yenilenir. tikla(x, y, w, h) verilirse fare tiklamasi iletilir."""

    def __init__(self, ciz, genislik=-1, yukseklik=-1, veri=None, tikla=None):
        super().__init__()
        self._ciz = ciz
        self.veri = veri
        self.set_size_request(genislik, yukseklik)
        self.connect("draw", self._on_draw)
        if tikla is not None:
            self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
            self.connect("button-press-event", lambda w, e: tikla(
                e.x, e.y, w.get_allocated_width(), w.get_allocated_height()))

    def _on_draw(self, w, cr):
        try:
            self._ciz(cr, w.get_allocated_width(), w.get_allocated_height(), self.veri)
        except Exception as hata:  # noqa: BLE001 -- cizim hatasi pencereyi dusurmesin
            import sys
            print("cizim hatasi:", hata, file=sys.stderr)
        return False

    def veri_ayarla(self, veri):
        self.veri = veri
        self.queue_draw()


# ---------------------------------------------------------------------------
# Simgeler (vektor; tema rengini alir)
# ---------------------------------------------------------------------------

def ikon_ciz(cr, ad, x, y, s, renk_adi="soluk"):
    """s x s karede cizgisel simge. Bilinmeyen ad: dolu daire."""
    cr.save()
    cr.translate(x, y)
    cr.scale(s / 20.0, s / 20.0)
    cr.set_source_rgba(*rgb(renk_adi))
    cr.set_line_width(1.7)
    cr.set_line_cap(1)
    cr.set_line_join(1)
    pi = math.pi

    def daire(cx, cy, r, dolu=False):
        cr.new_sub_path()
        cr.arc(cx, cy, r, 0, 2 * pi)
        cr.fill() if dolu else cr.stroke()

    def cizgi(*noktalar):
        cr.move_to(*noktalar[0])
        for n in noktalar[1:]:
            cr.line_to(*n)
        cr.stroke()

    if ad == "pano":
        for (a, b) in ((3, 3), (11, 3), (3, 11), (11, 11)):
            yuvarlak(cr, a, b, 6, 6, 1.5)
            cr.stroke()
    elif ad == "kisi":
        daire(10, 7, 3.4)
        cr.arc(10, 19, 7, pi * 1.12, pi * 1.88)
        cr.stroke()
    elif ad == "hedef":
        daire(10, 10, 7.5)
        daire(10, 10, 4)
        daire(10, 10, 1.3, True)
    elif ad == "altigen":
        for i in range(7):
            a = pi / 6 + i * pi / 3
            (cr.move_to if i == 0 else cr.line_to)(10 + 7.5 * math.cos(a), 10 + 7.5 * math.sin(a))
        cr.stroke()
        daire(10, 10, 2.2, True)
    elif ad == "elmas":
        cizgi((10, 2.5), (17.5, 10), (10, 17.5), (2.5, 10), (10, 2.5))
        daire(10, 10, 1.8, True)
    elif ad == "yasak":
        daire(10, 10, 7.5)
        cizgi((4.8, 15.2), (15.2, 4.8))
    elif ad == "liste":
        for yy in (5, 10, 15):
            cizgi((7, yy), (17, yy))
            daire(3.6, yy, 1.1, True)
    elif ad == "rapor":
        yuvarlak(cr, 4, 2.5, 12, 15, 2)
        cr.stroke()
        cizgi((7, 13), (7, 10))
        cizgi((10, 13), (10, 7))
        cizgi((13, 13), (13, 9))
    elif ad == "ag":
        daire(10, 10, 2.4, True)
        for (a, b) in ((3.5, 4), (16.5, 4), (3.5, 16), (16.5, 16)):
            daire(a, b, 1.9)
            cizgi((10, 10), (a + (1.5 if a < 10 else -1.5), b + (1.4 if b < 10 else -1.4)))
    elif ad == "ayar":
        daire(10, 10, 2.8)
        for i in range(8):
            a = i * pi / 4
            cizgi((10 + 5.6 * math.cos(a), 10 + 5.6 * math.sin(a)),
                  (10 + 8 * math.cos(a), 10 + 8 * math.sin(a)))
        daire(10, 10, 5.6)
    elif ad == "kalkan":
        cr.move_to(10, 2.5)
        cr.line_to(16.5, 5)
        cr.curve_to(16.5, 11, 14, 15.5, 10, 17.5)
        cr.curve_to(6, 15.5, 3.5, 11, 3.5, 5)
        cr.close_path()
        cr.stroke()
    elif ad == "onay":
        cizgi((4, 10.5), (8.2, 14.5), (16, 5.5))
    elif ad == "uyari":
        cizgi((10, 3), (18, 17), (2, 17), (10, 3))
        cizgi((10, 8), (10, 12))
        daire(10, 14.6, 0.9, True)
    elif ad == "bilgi":
        daire(10, 10, 7.5)
        cizgi((10, 9), (10, 14))
        daire(10, 6.2, 0.9, True)
    elif ad == "arti":
        cizgi((10, 4), (10, 16))
        cizgi((4, 10), (16, 10))
    elif ad == "yenile":
        cr.arc(10, 10, 6.5, -pi * 0.35, pi * 1.45)
        cr.stroke()
        cizgi((13.5, 1.8), (15.6, 4.6), (12.4, 6))
    elif ad == "dosya":
        cizgi((5, 2.5), (12, 2.5), (16, 6.5), (16, 17.5), (5, 17.5), (5, 2.5))
        cizgi((12, 2.5), (12, 6.5), (16, 6.5))
    elif ad == "usb":
        yuvarlak(cr, 6, 8, 8, 10, 1.5)
        cr.stroke()
        yuvarlak(cr, 7.5, 2.5, 5, 5.5, 1)
        cr.stroke()
    elif ad == "arama":
        daire(8.5, 8.5, 5.5)
        cizgi((12.6, 12.6), (17, 17))
    elif ad == "kalp":
        cizgi((2, 10.5), (6, 10.5), (8, 6), (11, 15), (13, 9), (14.5, 10.5), (18, 10.5))
    elif ad == "canta":
        yuvarlak(cr, 3, 6.5, 14, 11, 2)
        cr.stroke()
        cr.arc(10, 6.5, 3.2, pi, 2 * pi)
        cr.stroke()
    elif ad == "ev":
        cizgi((2.5, 9.5), (10, 3), (17.5, 9.5))
        cizgi((5, 8), (5, 17), (15, 17), (15, 8))
    elif ad == "saat":
        daire(10, 10, 7.5)
        cizgi((10, 5.5), (10, 10), (13.2, 12))
    elif ad == "kilit":
        yuvarlak(cr, 4, 9, 12, 8.5, 2)
        cr.stroke()
        cr.arc(10, 9, 3.6, pi, 2 * pi)
        cr.stroke()
    elif ad == "oyna":
        cizgi((7, 4), (16, 10), (7, 16), (7, 4))
    elif ad == "nota":
        daire(7, 15, 2.2, True)
        daire(15, 13, 2.2, True)
        cizgi((9.2, 15), (9.2, 5), (17, 3.5), (17, 13))
    elif ad == "kitap":
        cizgi((10, 5), (10, 16.5))
        cr.move_to(10, 5)
        cr.curve_to(7, 3.2, 4.5, 3.4, 3, 4)
        cr.line_to(3, 15)
        cr.curve_to(4.5, 14.4, 7, 14.2, 10, 16)
        cr.curve_to(13, 14.2, 15.5, 14.4, 17, 15)
        cr.line_to(17, 4)
        cr.curve_to(15.5, 3.4, 13, 3.2, 10, 5)
        cr.stroke()
    elif ad == "oyun":
        yuvarlak(cr, 2.5, 6.5, 15, 8.5, 4)
        cr.stroke()
        cizgi((5, 10.7), (8, 10.7))
        cizgi((6.5, 9.2), (6.5, 12.2))
        daire(13, 9.6, 1.0, True)
        daire(14.6, 11.6, 1.0, True)
    elif ad == "arac":
        cr.move_to(13.5, 3.2)
        cr.curve_to(11.2, 3.6, 9.8, 6, 10.8, 8.1)
        cr.line_to(3.5, 15.4)
        cr.line_to(5.6, 17.5)
        cr.line_to(12.9, 10.2)
        cr.curve_to(15, 11.2, 17.4, 9.8, 17.8, 7.5)
        cr.line_to(15, 8.8)
        cr.line_to(13.2, 7)
        cr.close_path()
        cr.stroke()
    elif ad == "yildiz":
        import math as _m
        for i in range(10):
            a = -_m.pi / 2 + i * _m.pi / 5
            r = 7.5 if i % 2 == 0 else 3.2
            (cr.move_to if i == 0 else cr.line_to)(10 + r * _m.cos(a), 10 + r * _m.sin(a))
        cr.close_path()
        cr.stroke()
    elif ad == "indir":
        cizgi((10, 3), (10, 13))
        cizgi((6, 9.5), (10, 13.5), (14, 9.5))
        cizgi((4, 17), (16, 17))
    elif ad == "paket":
        cizgi((10, 3), (17, 7), (17, 14), (10, 18), (3, 14), (3, 7), (10, 3))
        cizgi((3, 7), (10, 11), (17, 7))
        cizgi((10, 11), (10, 18))
    elif ad == "anahtar":
        daire(7, 8, 4)
        cizgi((10, 11), (17, 18))
        cizgi((14, 15), (16, 13))
        cizgi((15.5, 16.5), (17.5, 14.5))
    elif ad == "web":
        daire(10, 10, 7.5)
        cizgi((2.5, 10), (17.5, 10))
        cr.save()
        cr.translate(10, 10)
        cr.scale(0.42, 1.0)
        cr.new_sub_path()
        cr.arc(0, 0, 7.5, 0, 2 * pi)
        cr.restore()
        cr.stroke()
    elif ad == "veritabani":
        for cy in (5, 10, 15):
            cr.new_sub_path()
            cr.save()
            cr.translate(10, cy)
            cr.scale(1.0, 0.34)
            cr.arc(0, 0, 7, 0, 2 * pi)
            cr.restore()
            cr.stroke()
        cizgi((3, 5), (3, 15))
        cizgi((17, 5), (17, 15))
    elif ad == "wifi":
        for i, r in enumerate((4, 8.5, 13)):
            cr.new_sub_path()
            cr.arc(10, 19, r, pi * 1.18, pi * 1.82)
            cr.stroke()
        daire(10, 16.3, 1.1, True)
    else:
        daire(10, 10, 4, True)
    cr.restore()


class Ikon(Gtk.DrawingArea):
    def __init__(self, ad, boyut=18, renk_adi="soluk"):
        super().__init__()
        self.ad, self.boyut, self.renk_adi = ad, boyut, renk_adi
        self.set_size_request(boyut, boyut)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", lambda w, cr: ikon_ciz(
            cr, self.ad, (w.get_allocated_width() - self.boyut) / 2,
            (w.get_allocated_height() - self.boyut) / 2, self.boyut, self.renk_adi))

    def renk_ayarla(self, renk_adi):
        if renk_adi != self.renk_adi:
            self.renk_adi = renk_adi
            self.queue_draw()


def ikon_kutusu(ad, renk_adi="vurgu", boyut=30):
    """Renkli zeminde simge (kart basliklarinda)."""
    def ciz(cr, w, h, _v):
        cr.set_source_rgba(*rgb(renk_adi, 0.18))
        yuvarlak(cr, 0, 0, w, h, 8)
        cr.fill()
        ikon_ciz(cr, ad, (w - boyut * 0.6) / 2, (h - boyut * 0.6) / 2, boyut * 0.6, renk_adi)
    a = CizimAlani(ciz, boyut, boyut)
    a.set_valign(Gtk.Align.CENTER)
    return a


# ---------------------------------------------------------------------------
# Hazir grafikler
# ---------------------------------------------------------------------------

def cubuk_grafik(cr, w, h, degerler, etiketler=None, renk_fn=None, etiket_adim=3,
                 bos_metin=""):
    """Dikey cubuk grafigi. renk_fn(deger, en_buyuk) -> renk adi."""
    sol, alt, ust = 34, 24, 10
    if not degerler:
        return
    en = max(degerler) or 0
    olcek = en if en > 0 else 4
    for i in range(5):
        yy = ust + (h - alt - ust) * i / 4
        cr.set_source_rgba(*rgb("cizgi"))
        cr.set_line_width(1)
        cr.move_to(sol, round(yy) + 0.5)
        cr.line_to(w - 4, round(yy) + 0.5)
        cr.stroke()
        yazi(cr, sol - 8, yy, str(round(olcek * (4 - i) / 4)), 8, "silik", hiza="sag", dikey="orta")
    n = len(degerler)
    bw = (w - sol - 6) / n
    for i, v in enumerate(degerler):
        bh = (h - alt - ust) * v / olcek
        x = sol + i * bw + bw * 0.18
        r = renk_fn(v, en) if renk_fn else "vurgu"
        cr.set_source_rgba(*rgb(r, 0.92 if v else 0.35))
        yuvarlak(cr, x, h - alt - max(bh, 2), bw * 0.64, max(bh, 2), min(3, bw * 0.3))
        cr.fill()
        if etiketler and i % etiket_adim == 0:
            yazi(cr, x + bw * 0.32, h - 5, etiketler[i], 8, "silik", hiza="orta")
    if en == 0 and bos_metin:
        yazi(cr, (w + sol) / 2, (h - alt) / 2, bos_metin, 10, "soluk", hiza="orta", dikey="orta")


def yatay_cubuklar(cr, w, h, ogeler, ad_genislik=64, satir=26):
    """ogeler: [(ad, sayi, renk_adi)]"""
    en = max([o[1] for o in ogeler] + [1])
    for i, (ad, n, r) in enumerate(ogeler):
        yy = 4 + i * satir
        yazi(cr, 0, yy + 9, ad, 9.5, "yazi", dikey="orta", en_fazla=ad_genislik - 6)
        uz = w - ad_genislik - 46
        cr.set_source_rgba(*rgb("kart2"))
        yuvarlak(cr, ad_genislik, yy + 3, uz, 12, 6)
        cr.fill()
        if n:
            cr.set_source_rgba(*rgb(r))
            yuvarlak(cr, ad_genislik, yy + 3, max(uz * n / en, 10), 12, 6)
            cr.fill()
        yazi(cr, w, yy + 9, str(n), 9.5, "yazi", hiza="sag", dikey="orta")


def halka(cr, w, h, deger, renk_adi, alt_metin=""):
    """0-100 arasi deger icin halka gosterge."""
    cx, cy, r = w / 2, h / 2, min(w, h) / 2 - 8
    cr.set_line_width(10)
    cr.set_source_rgba(*rgb("kart2"))
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.stroke()
    if deger > 0:
        cr.set_source_rgba(*rgb(renk_adi))
        cr.set_line_cap(1)
        cr.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * min(deger, 100) / 100)
        cr.stroke()
    yazi(cr, cx, cy - 2, str(int(deger)), 20, "yazi", True, "orta", "orta")
    if alt_metin:
        yazi(cr, cx, cy + 20, alt_metin, 8.5, "soluk", hiza="orta", dikey="orta")


# ---------------------------------------------------------------------------
# Pencereler
# ---------------------------------------------------------------------------

def onay_sor(ust, baslik, metin, evet, hayir, tehlike=False, ek=None):
    """Tema ile uyumlu onay penceresi. True/False. ek: iletisim icine
    eklenecek istege bagli parca (or. sure secimi)."""
    d = Gtk.Dialog(transient_for=ust, modal=True)
    d.set_decorated(True)
    d.set_title(baslik)
    d.set_resizable(False)
    alan = d.get_content_area()
    alan.set_spacing(10)
    for k in ("top", "bottom", "start", "end"):
        getattr(alan, f"set_margin_{k}")(18)
    alan.pack_start(etiket(baslik, "buyuk-baslik", sar=True, genislik=50), False, False, 0)
    alan.pack_start(etiket(metin, "soluk", sar=True, genislik=56), False, False, 0)
    if ek is not None:
        alan.pack_start(ek, False, False, 4)
    satir = Gtk.Box(spacing=8)
    satir.set_margin_top(8)
    h = dugme(hayir, None, d.response, Gtk.ResponseType.CANCEL)
    e = dugme(evet, "tehlike" if tehlike else "ana", d.response, Gtk.ResponseType.OK)
    satir.pack_end(e, False, False, 0)
    satir.pack_end(h, False, False, 0)
    alan.pack_start(satir, False, False, 0)
    d.show_all()
    cevap = d.run()
    if ek is not None:
        alan.remove(ek)      # cagiran, pencere kapandiktan sonra degeri okuyabilsin
    d.destroy()
    return cevap == Gtk.ResponseType.OK


# ---------------------------------------------------------------------------
# Uygulama kabugu
# ---------------------------------------------------------------------------

class Kabuk(Gtk.Box):
    """Sol kenar menusu + ust baslik + kaydirilabilir icerik + bildirim
    seridi.

    bolumler: [(bolum_anahtari, [(sayfa_anahtari, ikon_adi), ...]), ...]
    Metinler metin_ayarla() ile verilir (dil degisince yeniden cagrilir).
    sayfa_secildi(anahtar) her menu seciminde cagrilir."""

    def __init__(self, logo=None, bolumler=(), sayfa_secildi=None, genislik=232):
        super().__init__()
        self._secildi = sayfa_secildi
        self._satirlar = {}
        self._bolum_etiketleri = {}
        self._serit_id = 0

        yan = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sinif(yan, "yan")
        yan.set_size_request(genislik, -1)
        marka = Gtk.Box(spacing=10)
        marka.set_margin_top(20)
        marka.set_margin_start(20)
        marka.set_margin_end(12)
        marka.set_margin_bottom(14)
        if logo:
            try:
                marka.pack_start(Gtk.Image.new_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_size(logo, 36, 36)), False, False, 0)
            except GLib.Error:
                pass
        mv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        mv.set_valign(Gtk.Align.CENTER)
        self.marka_ad = etiket("", "marka")
        self.marka_alt = etiket("", "marka-alt")
        self.marka_alt.set_ellipsize(Pango.EllipsizeMode.END)
        mv.pack_start(self.marka_ad, False, False, 0)
        mv.pack_start(self.marka_alt, False, False, 0)
        marka.pack_start(mv, True, True, 0)
        yan.pack_start(marka, False, False, 0)

        self.listeler = []
        for bolum, sayfalar in bolumler:
            be = etiket("", "menu-baslik")
            be.set_margin_start(22)
            be.set_margin_top(8)
            be.set_margin_bottom(2)
            yan.pack_start(be, False, False, 0)
            self._bolum_etiketleri[bolum] = be
            liste = Gtk.ListBox()
            sinif(liste, "menu")
            liste.set_selection_mode(Gtk.SelectionMode.SINGLE)
            liste.set_can_focus(False)
            liste.connect("row-selected", self._satir_secildi)
            for anahtar, ikon in sayfalar:
                row = Gtk.ListBoxRow()
                row.anahtar = anahtar
                row.set_can_focus(False)
                b = Gtk.Box(spacing=12)
                b.set_margin_top(8)
                b.set_margin_bottom(8)
                b.set_margin_start(12)
                b.set_margin_end(10)
                row.ikon = Ikon(ikon, 17, "soluk")
                row.ad = etiket("", "menu-yazi")
                row.ad.set_ellipsize(Pango.EllipsizeMode.END)
                row.sayi = etiket("", "menu-sayi")
                row.sayi.set_no_show_all(True)
                b.pack_start(row.ikon, False, False, 0)
                b.pack_start(row.ad, True, True, 0)
                b.pack_end(row.sayi, False, False, 0)
                row.add(b)
                liste.add(row)
                self._satirlar[anahtar] = row
            yan.pack_start(liste, False, False, 0)
            self.listeler.append(liste)

        # alt kisim: uygulamanin kendi denetimleri (dil, gorunum)
        self.yan_alt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.yan_alt.set_margin_start(18)
        self.yan_alt.set_margin_end(18)
        self.yan_alt.set_margin_bottom(16)
        yan.pack_end(self.yan_alt, False, False, 0)
        self.pack_start(yan, False, False, 0)

        sag = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sinif(sag, "arka")
        ust = Gtk.Box(spacing=12)
        ust.set_margin_top(20)
        ust.set_margin_start(28)
        ust.set_margin_end(28)
        bv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.baslik = etiket("", "sayfa-baslik")
        self.baslik.set_ellipsize(Pango.EllipsizeMode.END)
        self.alt = etiket("", "sayfa-alt")
        self.alt.set_ellipsize(Pango.EllipsizeMode.END)
        bv.pack_start(self.baslik, False, False, 0)
        bv.pack_start(self.alt, False, False, 0)
        ust.pack_start(bv, True, True, 0)
        self.ust_sag = Gtk.Box(spacing=10)
        self.ust_sag.set_valign(Gtk.Align.CENTER)
        ust.pack_end(self.ust_sag, False, False, 0)
        sag.pack_start(ust, False, False, 0)

        katman = Gtk.Overlay()
        self.kaydir = Gtk.ScrolledWindow()
        self.kaydir.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        katman.add(self.kaydir)
        self.serit = Gtk.Revealer()
        self.serit.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.serit.set_halign(Gtk.Align.CENTER)
        self.serit.set_valign(Gtk.Align.END)
        self.serit.set_margin_bottom(18)
        sk = Gtk.Box(spacing=10)
        sinif(sk, "serit")
        self.serit_ikon = Ikon("bilgi", 16, "vurgu")
        self.serit_ikon.set_margin_start(14)
        self.serit_metin = etiket("", None, sar=True, genislik=80)
        self.serit_metin.set_margin_top(10)
        self.serit_metin.set_margin_bottom(10)
        self.serit_metin.set_margin_end(16)
        sk.pack_start(self.serit_ikon, False, False, 0)
        sk.pack_start(self.serit_metin, True, True, 0)
        self.serit.add(sk)
        self._serit_kutu = sk
        katman.add_overlay(self.serit)
        katman.set_overlay_pass_through(self.serit, True)
        sag.pack_start(katman, True, True, 0)
        self.pack_start(sag, True, True, 0)

    # -- metinler -----------------------------------------------------------
    def marka_ayarla(self, ad, alt):
        self.marka_ad.set_text(ad)
        self.marka_alt.set_text(alt)

    def bolum_metni(self, bolum, metin):
        if bolum in self._bolum_etiketleri:
            self._bolum_etiketleri[bolum].set_text(metin.upper())

    def menu_metni(self, anahtar, metin):
        if anahtar in self._satirlar:
            self._satirlar[anahtar].ad.set_text(metin)

    def rozet(self, anahtar, metin=None, sakin=False):
        row = self._satirlar.get(anahtar)
        if row is None:
            return
        if metin:
            row.sayi.set_text(str(metin))
            ctx = row.sayi.get_style_context()
            (ctx.add_class if sakin else ctx.remove_class)("sakin")
            row.sayi.show()
        else:
            row.sayi.hide()

    def baslik_ayarla(self, baslik, alt=""):
        self.baslik.set_text(baslik)
        self.alt.set_text(alt)

    # -- gezinme ------------------------------------------------------------
    def sec(self, anahtar):
        row = self._satirlar.get(anahtar)
        if row is not None:
            row.get_parent().select_row(row)

    def _satir_secildi(self, liste, row):
        if row is None:
            return
        for diger in self.listeler:
            if diger is not liste:
                diger.unselect_all()
        for r in self._satirlar.values():
            r.ikon.renk_ayarla("vurgu" if r is row else "soluk")
        if self._secildi:
            self._secildi(row.anahtar)

    def icerik(self, widget):
        eski = self.kaydir.get_child()
        if eski is not None:
            self.kaydir.remove(eski)
            if isinstance(eski, Gtk.Viewport):
                for c in eski.get_children():
                    eski.remove(c)
        widget.set_margin_top(18)
        widget.set_margin_start(28)
        widget.set_margin_end(28)
        widget.set_margin_bottom(28)
        self.kaydir.add(widget)
        self.kaydir.get_vadjustment().set_value(0)
        widget.show_all()

    # -- bildirim seridi ------------------------------------------------------
    def bildir(self, metin, tur="bilgi", sure=5):
        """tur: bilgi / basari / hata"""
        ctx = self._serit_kutu.get_style_context()
        for c in ("serit-hata", "serit-basari"):
            ctx.remove_class(c)
        if tur in ("hata", "basari"):
            ctx.add_class(f"serit-{tur}")
        self.serit_ikon.ad = {"hata": "uyari", "basari": "onay"}.get(tur, "bilgi")
        self.serit_ikon.renk_ayarla({"hata": "kirmizi", "basari": "yesil"}.get(tur, "vurgu"))
        self.serit_ikon.queue_draw()
        self.serit_metin.set_text(metin)
        self.serit.show_all()
        self.serit.set_reveal_child(True)
        self._serit_id += 1
        kimlik = self._serit_id

        def gizle():
            if kimlik == self._serit_id:
                self.serit.set_reveal_child(False)
            return False
        GLib.timeout_add_seconds(sure, gizle)
