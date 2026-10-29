# -*- coding: utf-8 -*-
"""Tuzak modulleri: her tuzak icin ac/kapat, port ve kimlik (persona).
Degisiklikler taslakta toplanir ve "Uygula" ile tek seferde kaydedilir."""

import copy
import time

from gi.repository import Gtk, Pango

import tema
import tuzaklar
from arayuz import veri as V
from arayuz.sayfalar import RENK, Sayfa

IKON = {"ssh": "kilit", "http": "ev", "telnet": "altigen", "ftp": "dosya", "vnc": "pano",
        "rdp": "pano", "mysql": "liste", "redis": "elmas"}


class TuzakSayfasi(Sayfa):
    ANAHTAR = "tuzak"

    def __init__(self, p):
        super().__init__(p)
        self.taslak = None
        self.son_port = {}
        self._kilit = False

    def _taslagi_sifirla(self):
        a = self.p.ayar
        self.taslak = {"portlar": dict(a["portlar"]), "personalar": dict(a["personalar"])}
        for ad in tuzaklar.SIRA:
            if a["portlar"][ad]:
                self.son_port[ad] = a["portlar"][ad]
            else:
                self.son_port.setdefault(ad, tuzaklar.MODULLER[ad].VARSAYILAN_PORT)

    def kirli(self):
        a = self.p.ayar
        return (self.taslak["portlar"] != a["portlar"] or
                self.taslak["personalar"] != a["personalar"])

    def kur(self):
        self._taslagi_sifirla()
        kok = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.degisiklik = Gtk.Box()
        self.degisiklik.set_no_show_all(True)
        dis, ic = tema.kart(14, 8, "vurgulu")
        satir = Gtk.Box(spacing=12)
        satir.pack_start(tema.Ikon("bilgi", 18, "vurgu"), False, False, 0)
        self.degisiklik_metni = tema.etiket("", None, sar=True, genislik=90)
        satir.pack_start(self.degisiklik_metni, True, True, 0)
        self.geri_al = tema.dugme(self.t("geri_al"), None, self.geri_al_tik)
        self.uygula = tema.dugme(self.t("uygula"), "ana", self.uygula_tik)
        satir.pack_end(self.uygula, False, False, 0)
        satir.pack_end(self.geri_al, False, False, 0)
        ic.pack_start(satir, False, False, 0)
        dis.show_all()
        self.degisiklik.pack_start(dis, True, True, 0)
        kok.pack_start(self.degisiklik, False, False, 0)

        izgara = Gtk.Grid(column_spacing=16, row_spacing=16, column_homogeneous=True)
        self.kartlar = {}
        for i, ad in enumerate(tuzaklar.SIRA):
            izgara.attach(self.tuzak_karti(ad), i % 3, i // 3, 1, 1)
        kok.pack_start(izgara, False, False, 0)
        kutu, _ = tema.not_kutusu(self.t("tuzak_not"), "bilgi")
        kok.pack_start(kutu, False, False, 0)
        return kok

    def tuzak_karti(self, ad):
        m = tuzaklar.MODULLER[ad]
        dis, ic = tema.kart(16, 10)
        u = Gtk.Box(spacing=10)
        u.pack_start(tema.ikon_kutusu(IKON.get(ad, "altigen"), RENK.get(ad, "vurgu")), False, False, 0)
        bv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        bv.set_valign(Gtk.Align.CENTER)
        bv.pack_start(tema.etiket(m.BASLIK, "kart-baslik"), False, False, 0)
        durum = tema.etiket("", "kart-alt")
        bv.pack_start(durum, False, False, 0)
        u.pack_start(bv, True, True, 0)
        anahtar = Gtk.Switch()
        anahtar.set_valign(Gtk.Align.CENTER)
        anahtar.connect("notify::active", self.anahtar_degisti, ad)
        u.pack_end(anahtar, False, False, 0)
        ic.pack_start(u, False, False, 0)
        ic.pack_start(tema.etiket(m.ACIKLAMA[self.p.lang], "kart-alt", sar=True, genislik=40),
                      False, False, 0)
        satir = Gtk.Box(spacing=8)
        satir.pack_start(tema.etiket(self.t("port"), "soluk"), False, False, 0)
        port = Gtk.SpinButton.new_with_range(1024, 65535, 1)
        port.set_width_chars(6)
        port.connect("value-changed", self.port_degisti, ad)
        satir.pack_start(port, False, False, 0)
        sayi = tema.etiket("", "etiket")
        sayi.set_valign(Gtk.Align.CENTER)
        satir.pack_end(sayi, False, False, 0)
        ic.pack_start(satir, False, False, 0)
        persona = Gtk.ComboBoxText()
        persona.set_size_request(120, -1)
        for hucre in persona.get_cells():
            hucre.set_property("ellipsize", Pango.EllipsizeMode.END)
        for anahtar_, bilgi in m.PERSONALAR.items():
            persona.append(anahtar_, f"{self.t('kimlik')}: {bilgi[self.p.lang]}")
        persona.connect("changed", self.persona_degisti, ad)
        ic.pack_start(persona, False, False, 0)
        self.kartlar[ad] = {"anahtar": anahtar, "port": port, "sayi": sayi, "durum": durum,
                            "persona": persona, "kart": dis}
        return dis

    # -- olaylar ------------------------------------------------------------------
    def anahtar_degisti(self, sw, _pspec, ad):
        if self._kilit:
            return
        if sw.get_active():
            self.taslak["portlar"][ad] = self.son_port.get(ad) or tuzaklar.MODULLER[ad].VARSAYILAN_PORT
        else:
            if self.taslak["portlar"][ad]:
                self.son_port[ad] = self.taslak["portlar"][ad]
            self.taslak["portlar"][ad] = 0
        self.yansit()

    def port_degisti(self, sb, ad):
        if self._kilit:
            return
        deger = int(sb.get_value())
        self.son_port[ad] = deger
        if self.taslak["portlar"][ad]:
            self.taslak["portlar"][ad] = deger
        self.yansit()

    def persona_degisti(self, kutu, ad):
        if self._kilit or not kutu.get_active_id():
            return
        self.taslak["personalar"][ad] = kutu.get_active_id()
        self.yansit()

    def geri_al_tik(self):
        self._taslagi_sifirla()
        self.guncelle()

    def hata(self):
        portlar = [p for p in self.taslak["portlar"].values() if p]
        if not portlar:
            return self.t("en_az_bir")
        for p in portlar:
            if portlar.count(p) > 1:
                return self.t("port_cakisma", port=p)
        return None

    def uygula_tik(self):
        if self.hata():
            return
        yeni = copy.deepcopy(self.p.ayar)
        yeni["portlar"] = dict(self.taslak["portlar"])
        yeni["personalar"] = dict(self.taslak["personalar"])

        def sonra(kod, _veri):
            if kod == "__TAMAM__":
                self._taslagi_sifirla()
        self.p.ayar_kaydet(yeni, sonra=sonra)

    def mesgul_degisti(self):
        if hasattr(self, "uygula"):
            self.uygula.set_sensitive(self.p.mesgul is None and not self.hata())

    # -- gorunum --------------------------------------------------------------------
    def yansit(self):
        """Taslagi parcalara yansitir (sinyalleri tetiklemeden)."""
        self._kilit = True
        try:
            for ad, k in self.kartlar.items():
                port = self.taslak["portlar"][ad]
                k["anahtar"].set_active(bool(port))
                k["port"].set_value(port or self.son_port.get(ad, 1024))
                k["port"].set_sensitive(bool(port))
                k["persona"].set_active_id(self.taslak["personalar"][ad])
                k["persona"].set_sensitive(bool(port))
        finally:
            self._kilit = False
        if self.kirli():
            hata = self.hata()
            self.degisiklik_metni.set_text(hata or self.t("degisiklik_var"))
            self.degisiklik_metni.get_style_context().remove_class("hata-yazi")
            if hata:
                self.degisiklik_metni.get_style_context().add_class("hata-yazi")
            self.degisiklik.show()
        else:
            self.degisiklik.hide()
        self.mesgul_degisti()

    def guncelle(self):
        p = self.p
        if self.taslak is None or not self.kirli():
            self._taslagi_sifirla()
        sayilar = dict(V.hizmet_sayilari(p.akis.olaylar, time.time(), 86400))
        acik = p.hdurum.get("acik", {}) if p.hizmet else {}
        hatalar = p.hdurum.get("hatalar", {}) if p.hizmet else {}
        for ad, k in self.kartlar.items():
            k["sayi"].set_text(self.t("olay_n", n=sayilar.get(ad, 0)))
            ctx = k["durum"].get_style_context()
            for c in ("basari-yazi", "hata-yazi", "uyari-yazi"):
                ctx.remove_class(c)
            if not p.ayar["portlar"][ad]:
                k["durum"].set_text("○ " + self.t("t_kapali"))
            elif not p.hizmet:
                k["durum"].set_text("○ " + self.t("t_bekliyor"))
            elif ad in hatalar:
                k["durum"].set_text("● " + self.t("t_mesgul"))
                ctx.add_class("hata-yazi")
            elif f"{ad}_tam" in hatalar:
                k["durum"].set_text("● " + self.t("t_basliksiz"))
                ctx.add_class("uyari-yazi")
            elif ad in acik:
                k["durum"].set_text("● " + self.t("t_calisiyor"))
                ctx.add_class("basari-yazi")
            ctxk = k["kart"].get_style_context()
            (ctxk.add_class if ad in hatalar else ctxk.remove_class)("tehlikeli")
        self.yansit()
