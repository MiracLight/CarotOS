# -*- coding: utf-8 -*-
"""Ayarlar: bildirim ve kayit ayarlari (yonetici onayiyla), dil ve gorunum
(hemen), hakkinda."""

import copy
import urllib.parse

from gi.repository import Gtk

import carotpot as CP
import tema
from arayuz.sayfalar import Sayfa


class AyarSayfasi(Sayfa):
    ANAHTAR = "ayar"

    def kur(self):
        p = self.p
        kok = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        ust = Gtk.Box(spacing=16, homogeneous=True)

        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("bildirimler"))
        self.bekleme = self.sayi(ic, self.t("bekleme"), 1, 1440)
        ic.pack_start(tema.etiket(self.t("webhook"), "soluk"), False, False, 4)
        self.webhook = Gtk.Entry()
        self.webhook.set_placeholder_text("https://")
        self.webhook.connect("changed", lambda *_: self.denetle())
        ic.pack_start(self.webhook, False, False, 0)
        ic.pack_start(tema.etiket(self.t("webhook_not"), "kart-alt", sar=True, genislik=56),
                      False, False, 0)
        ust.pack_start(dis, True, True, 0)

        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("kayitlar"))
        self.sakla = self.sayi(ic, self.t("sakla_gun"), 1, 365)
        self.dakika = self.sayi(ic, self.t("dakikada_olay"), 10, 6000)
        ust.pack_start(dis, True, True, 0)
        kok.pack_start(ust, False, False, 0)

        satir = Gtk.Box(spacing=12)
        self.hata = tema.etiket("", "hata-yazi")
        satir.pack_start(tema.etiket(self.t("kaydedilecek"), "kart-alt", sar=True, genislik=90),
                         True, True, 0)
        satir.pack_end(self.hata, False, False, 0)
        self.kaydet_dugme = tema.dugme(self.t("kaydet"), "ana", self.kaydet)
        satir.pack_end(self.kaydet_dugme, False, False, 0)
        kok.pack_start(satir, False, False, 0)

        alt = Gtk.Box(spacing=16, homogeneous=True)
        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("gorunum"))
        izgara = Gtk.Grid(column_spacing=14, row_spacing=12)
        dil = Gtk.ComboBoxText()
        dil.append("tr", "Türkçe")
        dil.append("en", "English")
        dil.set_active_id(p.lang)
        dil.connect("changed", lambda k: p.dil_kutu.set_active_id(k.get_active_id()))
        izgara.attach(tema.etiket(self.t("dil"), "soluk"), 0, 0, 1, 1)
        izgara.attach(dil, 1, 0, 1, 1)
        secim, _ = tema.secim_grubu([("dark", self.t("gorunum_koyu")),
                                     ("light", self.t("gorunum_acik"))], p.ui["theme"],
                                    lambda g: g != p.ui["theme"] and p.tema_degistir(g))
        izgara.attach(tema.etiket(self.t("tema"), "soluk"), 0, 1, 1, 1)
        izgara.attach(secim, 1, 1, 1, 1)
        ic.pack_start(izgara, False, False, 0)
        alt.pack_start(dis, True, True, 0)

        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("hakkinda"), f"CarotPot {CP.SURUM}")
        ic.pack_start(tema.etiket(self.t("hakkinda_metin"), "kart-alt", sar=True, genislik=60),
                      False, False, 0)
        alt.pack_start(dis, True, True, 0)
        kok.pack_start(alt, False, False, 0)
        self.doldur()
        return kok

    def sayi(self, ic, metin, alt, ust):
        satir = Gtk.Box(spacing=10)
        satir.pack_start(tema.etiket(metin, "soluk", sar=True, genislik=40), True, True, 0)
        sb = Gtk.SpinButton.new_with_range(alt, ust, 1)
        sb.connect("value-changed", lambda *_: self.denetle())
        satir.pack_end(sb, False, False, 0)
        ic.pack_start(satir, False, False, 2)
        return sb

    def doldur(self):
        a = self.p.ayar
        self.bekleme.set_value(max(1, a["bekleme"] // 60))
        self.sakla.set_value(a["sakla_gun"])
        self.dakika.set_value(a["dakikada_olay"])
        self.webhook.set_text(a["webhook"])
        self.denetle()

    def taslak(self):
        yeni = copy.deepcopy(self.p.ayar)
        yeni["bekleme"] = int(self.bekleme.get_value()) * 60
        yeni["sakla_gun"] = int(self.sakla.get_value())
        yeni["dakikada_olay"] = int(self.dakika.get_value())
        yeni["webhook"] = self.webhook.get_text().strip()
        return yeni

    def denetle(self):
        yeni = self.taslak()
        hata = ""
        if yeni["webhook"]:
            parca = urllib.parse.urlparse(yeni["webhook"])
            if parca.scheme != "https" or not parca.netloc:
                hata = "https://…"
        self.hata.set_text(hata)
        self.kaydet_dugme.set_sensitive(not hata and yeni != self.p.ayar and self.p.mesgul is None)

    def guncelle(self):
        if self.taslak() == self.p.ayar or not self.kaydet_dugme.get_sensitive():
            self.doldur()

    def mesgul_degisti(self):
        if hasattr(self, "kaydet_dugme"):
            self.denetle()

    def kaydet(self):
        self.p.ayar_kaydet(self.taslak())
