# -*- coding: utf-8 -*-
"""Ag haritasi: komsu tablosundaki cihazlar, ag gecidi ve tuzaga dokunanlar
(radyal yerlesim; tiklanan cihazin ayrintisi sagda)."""

import math
import time
from concurrent.futures import ThreadPoolExecutor

from gi.repository import Gtk

import ag
import tema
from arayuz import veri as V
from arayuz.sayfalar import Sayfa

KATEGORI_RENK = {"saldirgan": "kirmizi", "supheli": "sari", "gecit": "camgobegi",
                 "normal": "gri"}
EN_FAZLA_DIS = 24


class HaritaSayfasi(Sayfa):
    ANAHTAR = "ag"

    def __init__(self, p):
        super().__init__(p)
        self.cihazlar = None
        self.zaman = 0
        self.yukleniyor = False
        self.secili = None
        self.dugumler = []
        self._profil = (None, {})

    def profiller(self):
        if self._profil[0] != self.p.akis.surum:
            oz = V.kaynak_ozeti(self.p.akis.olaylar, time.time(), 7 * 86400)
            self._profil = (self.p.akis.surum, {k["kaynak"]: k for k in oz})
        return self._profil[1]

    def kur(self):
        kok = Gtk.Box(spacing=16)
        dis, ic = tema.kart()
        sag = Gtk.Box(spacing=8)
        self.yokla_dugme = tema.dugme(self.t("agi_yokla"), None, self.yokla)
        self.yokla_dugme.set_tooltip_text(self.t("yokla_ipucu"))
        sag.pack_start(self.yokla_dugme, False, False, 0)
        sag.pack_start(tema.dugme(self.t("yenile"), None, self.tara), False, False, 0)
        _, self.alt_baslik = tema.kart_basligi(ic, self.t("yerel_ag_kart"), "", sag=sag)
        self.harita = tema.CizimAlani(self.ciz, -1, 540, tikla=self.tiklandi)
        ic.pack_start(self.harita, True, True, 0)
        kok.pack_start(dis, True, True, 0)
        dis, ic = tema.kart()
        dis.set_size_request(280, -1)
        tema.kart_basligi(ic, self.t("gosterim"))
        for kat, anahtar in (("saldirgan", "g_saldirgan"), ("supheli", "g_supheli"),
                             ("gecit", "g_gecit"), ("normal", "g_normal")):
            b = Gtk.Box(spacing=10)
            b.pack_start(tema.CizimAlani(lambda cr, w, h, r: (
                cr.set_source_rgba(*tema.rgb(r)), cr.arc(w / 2, h / 2, 6, 0, 2 * math.pi),
                cr.fill()), 14, 14, KATEGORI_RENK[kat]), False, False, 0)
            b.pack_start(tema.etiket(self.t(anahtar), "kart-alt"), False, False, 0)
            ic.pack_start(b, False, False, 2)
        self.ayrinti = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.ayrinti.set_margin_top(12)
        ic.pack_start(self.ayrinti, False, False, 0)
        kok.pack_start(dis, False, False, 0)
        return kok

    # -- veri -------------------------------------------------------------------------
    def tara(self):
        if self.yukleniyor:
            return
        self.yukleniyor = True
        tuzak = self.profiller()

        def is_():
            liste = ag.cihazlar(tuzak)
            with ThreadPoolExecutor(16) as havuz:
                adlar = list(havuz.map(lambda c: ag.ad_coz(c["ip"], 1.0), liste))
            for c, ad in zip(liste, adlar):
                c["ad"] = ad
            return liste

        def bitti(sonuc):
            self.yukleniyor = False
            if isinstance(sonuc, list):
                self.cihazlar = sonuc
                self.zaman = time.time()
                for c in sonuc:
                    if c.get("mac") or c.get("ad"):
                        self.p.cihaz[c["ip"]] = {"mac": c.get("mac", ""),
                                                 "uretici": c.get("uretici", ""), "ad": c.get("ad", "")}
            if self.p.aktif == self.ANAHTAR:
                self.guncelle()
        self.p.arka_plan(is_, bitti)

    def yokla(self):
        self.p.bildir(self.t("yoklaniyor"))
        self.yokla_dugme.set_sensitive(False)

        def bitti(sonuc):
            if self.kok is not None:
                self.yokla_dugme.set_sensitive(True)
            self.p.bildir(self.t("yoklandi", n=sonuc if isinstance(sonuc, int) else 0), "basari")
            self.tara()
        self.p.arka_plan(ag.yokla, bitti, mesgul="yokla")

    def kategori(self, c, prof):
        k = prof.get(c["ip"])
        if k is not None:
            return "saldirgan" if (k["giris"] or k["risk"] >= 60) else "supheli"
        if c.get("gecit"):
            return "gecit"
        return "normal"

    def guncelle(self):
        if self.cihazlar is None or time.time() - self.zaman > 60:
            self.tara()
        prof = self.profiller()
        liste = self.cihazlar or []
        self.alt_baslik.set_text(self.t("ag_kart_alt", n=len(liste)))
        dugumler = []
        for c in liste:
            dugumler.append(dict(c, kat=self.kategori(c, prof)))
        self.harita.veri_ayarla(dugumler)
        self.ayrinti_guncelle(dugumler, prof)

    def ayrinti_guncelle(self, dugumler, prof):
        p = self.p
        self.temizle(self.ayrinti)
        c = next((d for d in dugumler if d["ip"] == self.secili), None)
        if c is None:
            self.ayrinti.pack_start(tema.etiket(
                self.t("secim_yok") if dugumler else self.t("ag_bos"), "kart-alt", sar=True,
                genislik=34), False, False, 0)
        else:
            self.ayrinti.pack_start(tema.etiket(self.t("secili", ad=self.ad(c)), "kart-baslik",
                                                sar=True, genislik=30), False, False, 0)
            u = c.get("uretici")
            u = self.t("rastgele_mac") if u == "rastgele" else u
            for s in (" · ".join(x for x in (c["ip"], u) if x), c.get("mac") or ""):
                if s:
                    self.ayrinti.pack_start(tema.etiket(s, "kart-alt", sec=True), False, False, 0)
            k = prof.get(c["ip"])
            if k:
                self.ayrinti.pack_start(tema.etiket(
                    self.t("tuzaga_dokundu", n=k["sayi"], son=p.once(k["son"])), "kart-alt"),
                    False, False, 0)
                if k["davranis"]:
                    self.ayrinti.pack_start(tema.etiket(", ".join(
                        self.t("d_" + d) for d in k["davranis"]), "kart-alt", sar=True,
                        genislik=34), False, False, 0)
                ac = tema.dugme(self.t("profili_ac"), "ana",
                                lambda ip=c["ip"]: p.gezin("saldirgan", ip=ip))
                self.ayrinti.pack_start(ac, False, False, 8)
            else:
                self.ayrinti.pack_start(tema.etiket(self.t("tuzaga_dokunmadi"), "kart-alt"),
                                        False, False, 0)
        self.ayrinti.show_all()

    def ad(self, c):
        u = c.get("uretici")
        return c.get("ad") or (u if u and u != "rastgele" else "") or c["ip"]

    # -- cizim --------------------------------------------------------------------------
    def ciz(self, cr, w, h, dugumler):
        cx, cy = w / 2, h / 2
        olcek = min(w, h)
        r1, r2 = olcek * 0.24, olcek * 0.42
        for r in (r1, r2):
            cr.set_source_rgba(*tema.rgb("cizgi"))
            cr.set_line_width(1)
            cr.set_dash([4, 6])
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.stroke()
        cr.set_dash([])
        dugumler = dugumler or []
        ic = [d for d in dugumler if d["kat"] != "normal"]
        dis = [d for d in dugumler if d["kat"] == "normal"]
        fazla = max(0, len(dis) - EN_FAZLA_DIS)
        dis = dis[:EN_FAZLA_DIS]
        yer = []
        for halka, r, kayma in ((ic, r1, -math.pi / 2), (dis, r2, -math.pi / 2 + 0.35)):
            for i, d in enumerate(halka):
                a = kayma + 2 * math.pi * i / max(len(halka), 1)
                yer.append((cx + r * math.cos(a), cy + r * math.sin(a), d))
        self.dugumler = [(x, y, d["ip"]) for x, y, d in yer]
        for x, y, d in yer:
            renk = KATEGORI_RENK[d["kat"]]
            cr.set_source_rgba(*tema.rgb(renk, 0.85 if d["kat"] != "normal" else 0.45))
            cr.set_line_width(2.4 if d["kat"] == "saldirgan" else 1.4)
            if d["kat"] in ("saldirgan", "supheli"):
                cr.set_dash([6, 4])
            cr.move_to(x, y)
            cr.line_to(cx, cy)
            cr.stroke()
            cr.set_dash([])
        cr.set_source_rgba(*tema.rgb("turuncu", 0.18))
        cr.arc(cx, cy, 44, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(*tema.rgb("turuncu"))
        cr.arc(cx, cy, 26, 0, 2 * math.pi)
        cr.fill()
        tema.yazi(cr, cx, cy, self.t("bu_pc"), 9, "#1a1d26", True, "orta", "orta")
        for x, y, d in yer:
            renk = KATEGORI_RENK[d["kat"]]
            if d["kat"] == "saldirgan":
                cr.set_source_rgba(*tema.rgb("kirmizi", 0.2))
                cr.arc(x, y, 25, 0, 2 * math.pi)
                cr.fill()
            if d["ip"] == self.secili:
                cr.set_source_rgba(*tema.rgb("vurgu", 0.35))
                cr.arc(x, y, 22, 0, 2 * math.pi)
                cr.fill()
            cr.set_source_rgba(*tema.rgb("kart2"))
            cr.arc(x, y, 14, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgba(*tema.rgb(renk))
            cr.set_line_width(3.2)
            cr.arc(x, y, 14, 0, 2 * math.pi)
            cr.stroke()
            ad = self.ad(d)
            tema.yazi(cr, x, y + 31, ad if d["kat"] != "gecit" else self.t("g_gecit"), 9, "yazi",
                      d["kat"] == "saldirgan", "orta", en_fazla=130)
            alt = d["ip"] if ad != d["ip"] or d["kat"] == "gecit" else (
                d.get("uretici") if d.get("uretici") not in (None, "", "rastgele") else "")
            if alt:
                tema.yazi(cr, x, y + 45, alt, 8, "soluk", hiza="orta", en_fazla=130)
        if fazla:
            tema.yazi(cr, w - 8, h - 8, self.t("ve_fazlasi", n=fazla), 8.5, "soluk", hiza="sag")
        if not dugumler:
            tema.yazi(cr, cx, cy + 70, self.t("ag_bos"), 9.5, "soluk", hiza="orta", en_fazla=w - 40)

    def tiklandi(self, x, y, _w, _h):
        en_yakin = None
        for dx, dy, ip in self.dugumler:
            m = math.hypot(dx - x, dy - y)
            if m < 24 and (en_yakin is None or m < en_yakin[0]):
                en_yakin = (m, ip)
        if en_yakin:
            self.secili = en_yakin[1]
            self.guncelle()
