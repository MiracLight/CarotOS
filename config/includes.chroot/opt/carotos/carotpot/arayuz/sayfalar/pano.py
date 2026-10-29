# -*- coding: utf-8 -*-
"""Pano: canli gosterge (KPI'lar, saatlik grafik, tuzak basina olay,
en etkin saldirganlar, canli akis)."""

import time

from gi.repository import Gtk, Pango

import tema
from arayuz import veri as V
from arayuz.sayfalar import RENK, Sayfa, tiklanir


def saatlik_renk(v, en):
    if en < 6:
        return "vurgu"
    if v > en * 0.66:
        return "kirmizi"
    if v > en * 0.33:
        return "turuncu"
    return "vurgu"


class PanoSayfasi(Sayfa):
    ANAHTAR = "pano"

    def kur(self):
        kok = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.not_alani = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.not_alani.set_no_show_all(True)
        kok.pack_start(self.not_alani, False, False, 0)

        sira = Gtk.Box(spacing=16, homogeneous=True)
        self.k_olay = tema.KpiKutusu(self.t("kpi_olay"))
        self.k_kaynak = tema.KpiKutusu(self.t("kpi_kaynak"))
        self.k_giris = tema.KpiKutusu(self.t("kpi_giris"))
        self.k_engel = tema.KpiKutusu(self.t("kpi_engel"))
        for k in (self.k_olay, self.k_kaynak, self.k_giris, self.k_engel):
            sira.pack_start(k, True, True, 0)
        kok.pack_start(sira, False, False, 0)

        orta = Gtk.Box(spacing=16)
        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("saatlik"), self.t("saatlik_alt"))
        self.grafik = tema.CizimAlani(self.ciz_saatlik, -1, 210)
        ic.pack_start(self.grafik, True, True, 0)
        orta.pack_start(dis, True, True, 0)
        dis, ic = tema.kart()
        dis.set_size_request(330, -1)
        tema.kart_basligi(ic, self.t("tuzak_basina"))
        self.cubuklar = tema.CizimAlani(self.ciz_cubuklar, -1, 214)
        ic.pack_start(self.cubuklar, True, True, 0)
        orta.pack_start(dis, False, False, 0)
        kok.pack_start(orta, False, False, 0)

        alt = Gtk.Box(spacing=16, homogeneous=True)
        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("etkin_saldirganlar"),
                          sag=tema.dugme(self.t("tumu"), None, self.p.gezin, "saldirgan"))
        self.sl_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ic.pack_start(self.sl_kutu, False, False, 0)
        alt.pack_start(dis, True, True, 0)
        dis, ic = tema.kart()
        self.canli = tema.rozet(self.t("canli"), "kirmizi")
        self.canli.set_no_show_all(True)
        tema.kart_basligi(ic, self.t("canli_akis"), sag=self.canli)
        self.akis_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ic.pack_start(self.akis_kutu, False, False, 0)
        alt.pack_start(dis, True, True, 0)
        kok.pack_start(alt, False, False, 0)
        return kok

    # -- cizimler -------------------------------------------------------------
    def ciz_saatlik(self, cr, w, h, veri):
        if not veri:
            return
        sayilar, etiketler = veri
        tema.cubuk_grafik(cr, w, h, sayilar, etiketler, saatlik_renk, 3,
                          bos_metin=self.t("saatlik_bos"))

    def ciz_cubuklar(self, cr, w, h, veri):
        if veri:
            tema.yatay_cubuklar(cr, w, h, veri, ad_genislik=66)

    # -- guncelleme -----------------------------------------------------------
    def guncelle(self):
        p = self.p
        simdi = time.time()
        olaylar = p.akis.olaylar
        son24 = [o for o in olaylar if simdi - o.get("ts", 0) <= 86400]
        once24 = [o for o in olaylar if 86400 < simdi - o.get("ts", 0) <= 172800]

        self.temizle(self.not_alani)
        if not p.hizmet:
            kutu, _ = tema.not_kutusu(self.t("pano_kapali"), "bilgi")
            self.not_alani.pack_start(kutu, False, False, 0)
        else:
            hatalar = [k for k in p.hdurum.get("hatalar", {}) if not k.endswith("_tam")]
            if hatalar:
                kutu, _ = tema.not_kutusu(self.t("pano_hata", liste=", ".join(
                    V.HIZMET_ADI.get(h, h) for h in hatalar)), "uyari")
                self.not_alani.pack_start(kutu, False, False, 0)
        self.bosken_gizle(self.not_alani)

        def yuzde(a, b):
            if not b:
                return ("", "notr")
            d = round((a - b) * 100 / b)
            if d == 0:
                return ("", "notr")
            return (self.t("fark_yuzde", y="▲ " if d > 0 else "▼ ", n=abs(d)),
                    "kotu" if d > 0 else "iyi")

        f, tur = yuzde(len(son24), len(once24))
        self.k_olay.ayarla(len(son24), fark=f, tur=tur)
        onceki_kaynak = {o["kaynak"] for o in once24}
        yeni = len({k["kaynak"] for k in p.ozet24} - onceki_kaynak)
        self.k_kaynak.ayarla(len(p.ozet24), fark=self.t("fark_yeni", n=yeni) if yeni else "",
                             tur="kotu")
        giris = sum(1 for o in son24 if o.get("tur") == "giris")
        f, tur = yuzde(giris, sum(1 for o in once24 if o.get("tur") == "giris"))
        self.k_giris.ayarla(giris, fark=f, tur=tur)
        self.k_engel.ayarla(len(p.engeller),
                            fark=self.t("f2b_acik") if p.otomatik else self.t("f2b_kapali"),
                            tur="iyi" if p.otomatik else "notr")

        self.grafik.veri_ayarla(V.saatlik(son24, simdi))
        acik = {ad for ad, port in p.ayar["portlar"].items() if port}
        sayilar = V.hizmet_sayilari(son24, simdi)
        self.cubuklar.veri_ayarla([(V.HIZMET_ADI[ad], n, RENK[ad]) for ad, n in sayilar
                                   if ad in acik or n][:8])

        # en etkin saldirganlar
        self.temizle(self.sl_kutu)
        if not p.ozet24:
            self.sl_kutu.pack_start(tema.etiket(self.t("saldirgan_bos"), "soluk"), False, False, 6)
        for k in p.ozet24[:4]:
            seviye, renk = p.seviye_metni(k["risk"])
            satir = Gtk.Box(spacing=12)
            for kenar in ("top", "bottom", "start", "end"):
                getattr(satir, f"set_margin_{kenar}")(6)
            r = tema.rozet(seviye, renk)
            r.set_size_request(58, -1)
            satir.pack_start(r, False, False, 0)
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            v.pack_start(tema.etiket(k["kaynak"], "ip"), False, False, 0)
            alt_ = p.cihaz_adi(k["kaynak"]) or ", ".join(
                V.HIZMET_ADI.get(h, h) for h in sorted(k["hizmetler"]))
            a = tema.etiket(alt_, "kart-alt")
            a.set_ellipsize(Pango.EllipsizeMode.END)
            v.pack_start(a, False, False, 0)
            satir.pack_start(v, True, True, 0)
            satir.pack_end(tema.etiket(f"{self.t('olay_n', n=k['sayi'])} · {p.saat(k['son'])}",
                                       "kart-alt"), False, False, 0)
            self.sl_kutu.pack_start(tiklanir(satir, lambda ip=k["kaynak"]: p.gezin(
                "saldirgan", ip=ip)), False, False, 0)
        self.sl_kutu.show_all()

        # canli akis
        self.temizle(self.akis_kutu)
        if p.hizmet:
            self.canli.show()
        else:
            self.canli.hide()
        if not olaylar:
            self.akis_kutu.pack_start(tema.etiket(self.t("akis_bos"), "soluk", sar=True),
                                      False, False, 6)
        for o in reversed(olaylar[-8:]):
            satir = Gtk.Box(spacing=10)
            satir.set_margin_top(4)
            satir.set_margin_bottom(4)
            satir.pack_start(tema.etiket(p.saat_sn(o.get("ts", 0)), "mono"), False, False, 0)
            e = tema.etiket(V.HIZMET_ADI.get(o.get("hizmet"), "?"), "etiket")
            e.set_size_request(48, -1)
            e.set_xalign(0.5)
            satir.pack_start(e, False, False, 0)
            satir.pack_start(tema.etiket(o.get("kaynak", ""), "ip"), False, False, 0)
            d = tema.etiket(p.akis_metni(o), "kart-alt")
            d.set_ellipsize(Pango.EllipsizeMode.END)
            satir.pack_start(d, True, True, 0)
            self.akis_kutu.pack_start(satir, False, False, 0)
        self.akis_kutu.show_all()

