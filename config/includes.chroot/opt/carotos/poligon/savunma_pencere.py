# -*- coding: utf-8 -*-
"""CarotOS Poligon -- savunmaci gorunumu penceresi (GTK3).

Ogrencinin saldirisinin sahte servislerde biraktigi izleri gosterir: olay gunlugu (yalniz meta veri), bunlardan
cikarilan bulgular ve ilgili savunma dersi, ufw/fail2ban durumu. Hicbir sey calistirmaz; yalniz okur.
Mantik savunma_analiz.py ve olay_gunlugu.py'dedir (GTK'siz).
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ortak"))
import dil_koprusu as _dil  # noqa: E402
import olay_gunlugu  # noqa: E402
import savunma_analiz as _a  # noqa: E402
from ctf_pencere import POLIGON_VURGU, ctf_css, pencere_ikonu_ata  # noqa: E402  (ortak gorunum, ikon)

T = _a.T
YENILEME_MS = 1000
DURUM_SN = 10
EN_COK_SATIR = 200

BASLIK = T("Savunmacı görünümü", "Defender view")
ACIKLAMA = T("Saldırının sahte servislerde bıraktığı izleri gör. Saldıran da savunan da bu izlerden öğrenir.",
             "See the traces your attack left on the fake services. Both attackers and defenders learn from these traces.")
BOS_BULGU = T("Şimdilik şüpheli bir iz yok. Poligon görevinde bir araç çalıştırınca burada izler görünür.",
              "No suspicious traces yet. When you run a tool in a Poligon task, traces show up here.")
BULGULAR_BASLIK = T("Bulgular", "Findings")
GUNLUK_BASLIK = T("Olay günlüğü", "Event log")
TEMIZLE = T("Günlüğü temizle", "Clear the log")
DURUM_AD = {"aktif": T("açık", "on"), "pasif": T("kapalı", "off"), "bilinmiyor": T("bilinmiyor", "unknown")}
DURUM_RENK = {"aktif": "yesil", "pasif": "gri", "bilinmiyor": "sari"}
SUTUNLAR = (T("Zaman", "Time"), T("Servis", "Service"), T("Olay", "Event"), T("Ayrıntı", "Detail"))
ONEM_ETIKET = T("Önem", "Severity")
SIDDET_AD = {"yuksek": T("yüksek", "high"), "orta": T("orta", "medium")}
SAAT_BICIMI = "%H:%M:%S"


def satir_metni(olay: dict, dil: str):
    """Tablo satiri: (zaman, servis, olay, ayrinti). GTK'siz; test edilir."""
    servis = _dil.sec(_a.SERVIS_AD.get(olay["servis"], T(olay["servis"], olay["servis"])), dil)
    tur = _dil.sec(_a.TUR_AD.get(olay["tur"], T(olay["tur"], olay["tur"])), dil)
    ayrinti = olay.get("ayrinti", "")
    if olay.get("port"):
        ayrinti = ("%s  :%d" % (ayrinti, olay["port"])).strip()
    return (time.strftime(SAAT_BICIMI, time.localtime(olay["zaman"])), servis, tur, ayrinti)


def pencere_olustur(dil: str, gorunum: str = "dark", gunluk=None, durum_fn=None, saat=time.time):
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk
    import tema

    gunluk = gunluk or olay_gunlugu.GUNLUK
    durum_fn = durum_fn or _a.savunma_durumu

    class SavunmaPencere(Gtk.Window):
        def __init__(self):
            super().__init__(title="CarotOS Poligon · " + _dil.sec(BASLIK, dil))
            pencere_ikonu_ata(self)
            self.dil = dil
            self._kapali = False
            self._son_no = 0
            self._durum_bekliyor = False
            self._bulgu_anahtari = None
            self._son_durum = 0.0
            self.set_default_size(860, 700)
            palet = tema.uygula(gorunum, POLIGON_VURGU)        # ekran geneli: Poligon vurgusu korunur
            css = Gtk.CssProvider()
            css.load_from_data(ctf_css(palet).encode())
            Gtk.StyleContext.add_provider_for_screen(self.get_screen(), css,
                                                     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2)
            kok = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            for kenar in ("top", "bottom"):
                getattr(kok, "set_margin_" + kenar)(12)
            kok.set_margin_start(14)
            kok.set_margin_end(14)
            self.add(kok)

            ust = Gtk.Box(spacing=12)
            self.baslik = Gtk.Label(xalign=0)
            tema.sinif(self.baslik, "marka")
            ust.pack_start(self.baslik, False, False, 0)
            self.ufw_rozet = tema.rozet("", "gri")
            self.f2b_rozet = tema.rozet("", "gri")
            ust.pack_end(self.f2b_rozet, False, False, 0)
            ust.pack_end(self.ufw_rozet, False, False, 0)
            kok.pack_start(ust, False, False, 0)

            self.aciklama = Gtk.Label(xalign=0, wrap=True)
            tema.sinif(self.aciklama, "soluk")
            kok.pack_start(self.aciklama, False, False, 0)

            self.bulgu_baslik = Gtk.Label(xalign=0)
            tema.sinif(self.bulgu_baslik, "kart-baslik")
            kok.pack_start(self.bulgu_baslik, False, False, 4)
            self.bulgu_kutusu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            kok.pack_start(self.bulgu_kutusu, False, False, 0)

            gust = Gtk.Box(spacing=8)
            self.gunluk_baslik = Gtk.Label(xalign=0)
            tema.sinif(self.gunluk_baslik, "kart-baslik")
            gust.pack_start(self.gunluk_baslik, True, True, 0)
            self.temizle_dugmesi = tema.dugme("", None, self._temizle)
            gust.pack_end(self.temizle_dugmesi, False, False, 0)
            kok.pack_start(gust, False, False, 4)

            self.model = Gtk.ListStore(str, str, str, str)
            self.agac = Gtk.TreeView(model=self.model)
            tema.sinif(self.agac, "ctf-agac")
            self.sutunlar = []
            for i in range(4):
                s = Gtk.TreeViewColumn("", Gtk.CellRendererText(xpad=10, ypad=4), text=i)
                s.set_min_width((90, 150, 190, 200)[i])
                s.set_expand(i == 3)
                self.agac.append_column(s)
                self.sutunlar.append(s)
            kay = Gtk.ScrolledWindow()
            kay.add(self.agac)
            kok.pack_start(kay, True, True, 0)

            self._metinleri_uygula()
            self.connect("destroy", lambda *_: setattr(self, "_kapali", True))
            self.yenile()
            self._son_durum = saat()
            self._durum_yenile()                      # ufw/fail2ban durumu hemen sorulur
            GLib.timeout_add(YENILEME_MS, self._zamanlayici)

        def t(self, m, **kw):
            return _dil.T(m, self.dil, **kw) if kw else _dil.sec(m, self.dil)

        def _metinleri_uygula(self):
            self.baslik.set_text(self.t(BASLIK))
            self.aciklama.set_text(self.t(ACIKLAMA))
            self.bulgu_baslik.set_text(self.t(BULGULAR_BASLIK))
            self.gunluk_baslik.set_text(self.t(GUNLUK_BASLIK))
            self.temizle_dugmesi.set_label(self.t(TEMIZLE))
            for s, m in zip(self.sutunlar, SUTUNLAR):
                s.set_title(self.t(m))
            self._durum_goster({"ufw": "bilinmiyor", "fail2ban": "bilinmiyor"})

        def dil_ayarla(self, yeni):
            self.dil = yeni
            self._metinleri_uygula()
            self._son_no = 0
            self.model.clear()
            self.yenile()

        def _durum_goster(self, d):
            for rozet, ad, anahtar in ((self.ufw_rozet, "ufw", "ufw"), (self.f2b_rozet, "fail2ban", "fail2ban")):
                v = d.get(anahtar, "bilinmiyor")
                tema.rozet_ayarla(rozet, "%s: %s" % (ad, self.t(DURUM_AD[v])), DURUM_RENK[v])

        def _durum_yenile(self):
            if self._durum_bekliyor:
                return
            self._durum_bekliyor = True

            def is_():
                d = durum_fn()
                GLib.idle_add(self._durum_geldi, d)
            threading.Thread(target=is_, daemon=True).start()

        def _durum_geldi(self, d):
            self._durum_bekliyor = False
            if not self._kapali:
                self._durum_goster(d)
            return False

        def _temizle(self, *_):
            gunluk.temizle()
            self._son_no = 0
            self.model.clear()
            self.yenile()

        def _bulgulari_goster(self, olaylar):
            bulgular = _a.analiz_et(olaylar, saat())
            anahtar = (self.dil, tuple((b["tur"], b["servis"], b["adet"]) for b in bulgular))
            if anahtar == self._bulgu_anahtari:               # degismediyse yeniden cizme (titremesin)
                return
            self._bulgu_anahtari = anahtar
            for c in self.bulgu_kutusu.get_children():
                self.bulgu_kutusu.remove(c)
            if not bulgular:
                et = Gtk.Label(xalign=0, wrap=True)
                tema.sinif(et, "soluk")
                et.set_text(self.t(BOS_BULGU))
                self.bulgu_kutusu.pack_start(et, False, False, 0)
            for b in bulgular:
                kart, ic = tema.kart()
                ust = Gtk.Box(spacing=8)
                bas = Gtk.Label(xalign=0)
                bas.set_markup("<b>%s</b>" % GLib.markup_escape_text(self.t(b["baslik"])))
                ust.pack_start(bas, False, False, 0)
                r = tema.rozet("", "gri")
                tema.rozet_ayarla(r, "%s: %s" % (self.t(ONEM_ETIKET), self.t(SIDDET_AD[b["siddet"]])),
                                  "kirmizi" if b["siddet"] == "yuksek" else "sari")
                ust.pack_start(r, False, False, 0)
                ic.pack_start(ust, False, False, 0)
                for m in (b["ne"], b["savunma"]):
                    et = Gtk.Label(xalign=0, wrap=True)
                    et.set_text(self.t(m))
                    ic.pack_start(et, False, False, 0)
                self.bulgu_kutusu.pack_start(kart, False, False, 0)
            self.bulgu_kutusu.show_all()

        def yenile(self):
            yeni = gunluk.son(self._son_no, EN_COK_SATIR)
            for o in yeni:
                self.model.insert(0, list(satir_metni(o, self.dil)))
                self._son_no = max(self._son_no, o["no"])
            while len(self.model) > EN_COK_SATIR:
                self.model.remove(self.model.get_iter(len(self.model) - 1))
            self._bulgulari_goster(gunluk.son(0, olay_gunlugu.MAKS_OLAY))

        def _zamanlayici(self):
            if self._kapali:
                return False
            self.yenile()
            if saat() - self._son_durum >= DURUM_SN:
                self._son_durum = saat()
                self._durum_yenile()
            return True

    return SavunmaPencere()
