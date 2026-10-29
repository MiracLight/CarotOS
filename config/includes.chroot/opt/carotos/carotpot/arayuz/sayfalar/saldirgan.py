# -*- coding: utf-8 -*-
"""Saldirgan profilleri: kaynak listesi, risk, cihaz bilgisi, zaman cizelgesi,
denenen kimlik bilgileri ve eylemler (engelle, sureli engelle, yok say, not)."""

import collections
import math
import time
from datetime import datetime

from gi.repository import Gtk, Pango

import tema
from arayuz import veri as V
from arayuz.sayfalar import RENK, Sayfa, tiklanir

SURELER = (("", "sure_suresiz"), ("15", "sure_15dk"), ("60", "sure_1sa"),
           ("360", "sure_6sa"), ("1440", "sure_24sa"), ("10080", "sure_7gun"))


def engel_iste(sayfa, ip, varsayilan_sure=""):
    """Onay + sure secimi; onaylanirsa yetkili engelleme. Engelleme ve
    saldirgan sayfalari ortak kullanir."""
    p = sayfa.p
    ek = Gtk.Box(spacing=10)
    ek.pack_start(tema.etiket(sayfa.t("engel_sure"), "kart-baslik"), False, False, 0)
    kutu = Gtk.ComboBoxText()
    for kimlik, anahtar in SURELER:
        kutu.append(kimlik, sayfa.t(anahtar))
    kutu.set_active_id(varsayilan_sure)
    ek.pack_start(kutu, False, False, 0)
    if not tema.onay_sor(p, sayfa.t("engel_onay_baslik", ip=ip), sayfa.t("engel_onay"),
                         sayfa.t("engelle"), sayfa.t("iptal"), tehlike=True, ek=ek):
        return
    sure = kutu.get_active_id() or None
    p.yetkili("engelle", ip, sure, basari=sayfa.t("engellendi", ip=ip))


def yoksay_iste(sayfa, ip):
    p = sayfa.p
    if not tema.onay_sor(p, sayfa.t("yoksay_onay_baslik", ip=ip), sayfa.t("yoksay_onay"),
                         sayfa.t("yok_say"), sayfa.t("iptal")):
        return
    yeni = dict(p.ayar)
    yeni["yoksay"] = list(dict.fromkeys(list(p.ayar["yoksay"]) + [ip]))
    p.ayar_kaydet(yeni, basari=sayfa.t("yoksayildi", ip=ip))


class SaldirganSayfasi(Sayfa):
    ANAHTAR = "saldirgan"

    def __init__(self, p):
        super().__init__(p)
        self.pencere = "24"
        self.secili = None
        self.acik_parolalar = {}
        self._onbellek = (None, None)

    def hazirla(self, ip=None, **_kw):
        if ip:
            self.secili = ip
            if not any(k["kaynak"] == ip for k in self.ozet()):
                self.pencere = "tum"

    def ozet(self):
        anahtar = (self.p.akis.surum, self.pencere, self.p.imza)
        if self._onbellek[0] == anahtar:
            return self._onbellek[1]
        if self.pencere == "24":
            oz = self.p.ozet24
        else:
            oz = V.kaynak_ozeti(self.p.akis.olaylar, time.time(),
                                7 * 86400 if self.pencere == "7" else 0)
        self._onbellek = (anahtar, oz)
        return oz

    def kur(self):
        kok = Gtk.Box(spacing=16)
        dis, ic = tema.kart(14, 8)
        dis.set_size_request(300, -1)
        self.liste_baslik = tema.etiket("", "kart-baslik")
        ic.pack_start(self.liste_baslik, False, False, 2)
        secim, _ = tema.secim_grubu(
            [("24", self.t("pencere_24")), ("7", self.t("pencere_7")),
             ("tum", self.t("pencere_tum"))], self.pencere, self.pencere_degisti)
        ic.pack_start(secim, False, False, 4)
        self.liste = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ic.pack_start(self.liste, False, False, 0)
        kok.pack_start(dis, False, False, 0)
        self.sag = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        kok.pack_start(self.sag, True, True, 0)
        return kok

    def pencere_degisti(self, anahtar):
        self.pencere = anahtar
        self.guncelle()

    def sec(self, ip):
        self.secili = ip
        self.guncelle()

    def mesgul_degisti(self):
        for d in getattr(self, "eylem_dugmeleri", []):
            d.set_sensitive(self.p.mesgul is None)

    # -- guncelleme -----------------------------------------------------------
    def guncelle(self):
        p = self.p
        oz = self.ozet()
        self.liste_baslik.set_text(self.t("kaynaklar_n", n=len(oz)))
        if oz and (self.secili is None or not any(k["kaynak"] == self.secili for k in oz)):
            self.secili = oz[0]["kaynak"]
        self.temizle(self.liste)
        for k in oz[:100]:
            seviye, renk = p.seviye_metni(k["risk"])
            ic = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            for kenar, d in (("top", 8), ("bottom", 8), ("start", 10), ("end", 10)):
                getattr(ic, f"set_margin_{kenar}")(d)
            u = Gtk.Box(spacing=8)
            u.pack_start(tema.etiket(k["kaynak"], "ip"), True, True, 0)
            if k["kaynak"] in p.engelli:
                u.pack_end(tema.rozet(self.t("engelli"), "gri"), False, False, 0)
            u.pack_end(tema.rozet(seviye, renk), False, False, 0)
            ic.pack_start(u, False, False, 0)
            alt = " · ".join(x for x in (p.cihaz_adi(k["kaynak"]), self.t("olay_n", n=k["sayi"])) if x)
            a = tema.etiket(alt, "kart-alt")
            a.set_ellipsize(Pango.EllipsizeMode.END)
            ic.pack_start(a, False, False, 0)
            if k["kaynak"] == self.secili:
                ic.get_style_context().add_class("secili-satir")
                self.liste.pack_start(ic, False, False, 0)
            else:
                self.liste.pack_start(tiklanir(ic, lambda ip=k["kaynak"]: self.sec(ip)),
                                      False, False, 0)
        self.liste.show_all()

        self.temizle(self.sag)
        self.eylem_dugmeleri = []
        k = next((k for k in oz if k["kaynak"] == self.secili), None)
        if k is None:
            dis, ic = tema.kart()
            ic.pack_start(tema.bos_durum("kisi", self.t("profil_bos_baslik"),
                                         self.t("profil_bos")), True, True, 0)
            self.sag.pack_start(dis, False, False, 0)
            self.sag.show_all()
            return
        p.cihaz_bilgisi_iste(k["kaynak"], lambda _b, ip=k["kaynak"]: (
            self.guncelle() if ip == self.secili and p.aktif == self.ANAHTAR else None))
        self.sag.pack_start(self.profil_karti(k), False, False, 0)
        self.sag.pack_start(self.zaman_karti(k), False, False, 0)
        alt = Gtk.Box(spacing=16, homogeneous=True)
        alt.pack_start(self.liste_karti(self.t("denenen_kullanicilar"),
                                        k["kullanicilar"].most_common(8)), True, True, 0)
        alt.pack_start(self.parola_karti(k), True, True, 0)
        self.sag.pack_start(alt, False, False, 0)
        if k["yollar"] or k["komutlar"]:
            alt2 = Gtk.Box(spacing=16, homogeneous=True)
            if k["yollar"]:
                alt2.pack_start(self.liste_karti(self.t("web_istekleri"),
                                                 k["yollar"].most_common(8)), True, True, 0)
            if k["komutlar"]:
                alt2.pack_start(self.liste_karti(self.t("komutlar"),
                                                 k["komutlar"].most_common(8)), True, True, 0)
            self.sag.pack_start(alt2, False, False, 0)
        self.sag.show_all()
        self.mesgul_degisti()

    # -- kartlar ----------------------------------------------------------------
    def profil_karti(self, k):
        p = self.p
        ip = k["kaynak"]
        seviye, renk = p.seviye_metni(k["risk"])
        dis, ic = tema.kart()
        ust = Gtk.Box(spacing=20)
        halka = tema.CizimAlani(lambda cr, w, h, v: tema.halka(cr, w, h, v, renk, self.t("risk")),
                                120, 120, k["risk"])
        halka.set_valign(Gtk.Align.START)
        ust.pack_start(halka, False, False, 0)
        bilgi = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        b1 = Gtk.Box(spacing=10)
        b1.pack_start(tema.etiket(ip, "sayfa-baslik ip", sec=True), False, False, 0)
        b1.pack_start(tema.rozet(self.t("risk_rozet", seviye=seviye.upper()), renk), False, False, 0)
        if ip in p.engelli:
            b1.pack_start(tema.rozet(self.t("engelli"), "gri"), False, False, 0)
        bilgi.pack_start(b1, False, False, 0)
        c = p.cihaz.get(ip) or {}
        if c.get("mac"):
            u = c.get("uretici")
            u = self.t("rastgele_mac") if u == "rastgele" else (u or self.t("bilinmiyor"))
            mac = c["mac"][:8] + ":••:••:••"
            satir = self.t("cihaz_satiri", uretici=u, mac=mac, ad=c.get("ad") or "—")
        else:
            satir = self.t("cihaz_yok") + (f" · {c['ad']}" if c.get("ad") else "")
        for metin in (satir,
                      self.t("zaman_satiri", ilk=p.saat(k["ilk"]), son=p.saat(k["son"]),
                             n=k["sayi"], giris=k["giris"]),
                      self.t("davranis_satiri", liste=", ".join(
                          self.t("d_" + d) for d in k["davranis"]) or "—")):
            bilgi.pack_start(tema.etiket(metin, "kart-alt", sar=True, genislik=80), False, False, 0)
        not_ = V.notlar().get(ip)
        if not_:
            bilgi.pack_start(tema.etiket(self.t("not_satiri", metin=not_), "vurgu-yazi", sar=True,
                                         genislik=80), False, False, 0)
        eylem = Gtk.Box(spacing=8)
        if ip in p.engelli:
            d = tema.dugme(self.t("engeli_kaldir"), None, lambda: p.yetkili(
                "kaldir", ip, basari=self.t("engel_kalkti", ip=ip)))
            eylem.pack_start(d, False, False, 0)
            self.eylem_dugmeleri.append(d)
        else:
            for metin, css, sure in ((self.t("engelle"), "tehlike", ""),
                                     (self.t("sureli_engelle"), None, "60")):
                d = tema.dugme(metin, css, engel_iste, self, ip, sure)
                eylem.pack_start(d, False, False, 0)
                self.eylem_dugmeleri.append(d)
        if ip not in p.ayar["yoksay"]:
            d = tema.dugme(self.t("yok_say"), None, yoksay_iste, self, ip)
            eylem.pack_start(d, False, False, 0)
            self.eylem_dugmeleri.append(d)
        eylem.pack_start(tema.dugme(self.t("not_duzenle") if not_ else self.t("not_ekle"),
                                    None, self.not_duzenle, ip, not_ or ""), False, False, 0)
        bilgi.pack_start(eylem, False, False, 6)
        ust.pack_start(bilgi, True, True, 0)
        ic.pack_start(ust, False, False, 0)
        return dis

    def zaman_karti(self, k):
        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("zaman_cizelgesi"), self.t("zaman_alt"))
        hizmetler = [h for h, _ in k["hizmet_sayi"].most_common(5)]
        yukseklik = 30 + 34 * len(hizmetler)
        ic.pack_start(tema.CizimAlani(self.ciz_zaman, -1, yukseklik,
                                      (k["zaman"], hizmetler)), False, False, 0)
        return dis

    def ciz_zaman(self, cr, w, h, veri):
        olaylar, hizmetler = veri
        if not olaylar:
            return
        ilk = min(t for t, _ in olaylar)
        son = max(t for t, _ in olaylar)
        if son - ilk < 600:
            ilk = son - 600
        pay = (son - ilk) * 0.04
        ilk, son = ilk - pay, son + pay
        sol, sag = 70, 12
        en = w - sol - sag

        def x(ts):
            return sol + en * (ts - ilk) / (son - ilk)
        for j, hz in enumerate(hizmetler):
            y = 16 + j * 34
            tema.yazi(cr, 0, y, V.HIZMET_ADI.get(hz, hz), 9.5, "yazi", dikey="orta")
            cr.set_source_rgba(*tema.rgb("cizgi"))
            cr.set_line_width(1)
            cr.move_to(sol, y)
            cr.line_to(w - sag, y)
            cr.stroke()
            for ts, h_ in olaylar:
                if h_ == hz:
                    cr.set_source_rgba(*tema.rgb(RENK.get(hz, "vurgu"), 0.8))
                    cr.arc(x(ts), y, 4.5, 0, 2 * math.pi)
                    cr.fill()
        bicim = "%H:%M" if son - ilk < 86400 else "%d.%m %H:%M"
        for i in range(4):
            ts = ilk + (son - ilk) * (0.06 + 0.88 * i / 3)
            tema.yazi(cr, x(ts), h - 4, datetime.fromtimestamp(ts).strftime(bicim), 8.5,
                      "silik", hiza="orta")

    def liste_karti(self, baslik, ogeler, sag=None):
        dis, ic = tema.kart()
        tema.kart_basligi(ic, baslik, sag=sag)
        if not ogeler:
            ic.pack_start(tema.etiket(self.t("liste_bos"), "soluk"), False, False, 2)
        for ad, n in ogeler:
            r = Gtk.Box(spacing=10)
            e = tema.etiket(str(ad), "mono", sec=True)
            e.set_ellipsize(Pango.EllipsizeMode.END)
            r.pack_start(e, True, True, 0)
            r.pack_end(tema.etiket(str(n), "kart-alt"), False, False, 0)
            ic.pack_start(r, False, False, 2)
        return dis

    def parola_karti(self, k):
        ip = k["kaynak"]
        acik = self.acik_parolalar.get(ip)
        if acik is not None:
            sayac = collections.Counter()
            for x in acik:
                sayac[x["parola"]] += x["sayi"]
            d = tema.dugme(self.t("gizle"), None, self.parola_gizle, ip)
            return self.liste_karti(self.t("denenen_parolalar_acik"), sayac.most_common(8), d)
        d = tema.dugme(self.t("goster"), None, self.parola_goster, ip)
        d.set_sensitive(bool(k["parolalar"]) and self.p.mesgul is None)
        if k["parolalar"]:
            self.eylem_dugmeleri.append(d)
        return self.liste_karti(self.t("denenen_parolalar"), k["parolalar"].most_common(8), d)

    # -- eylemler -----------------------------------------------------------------
    def parola_goster(self, ip):
        def sonra(kod, veri):
            if kod == "__TAMAM__":
                self.acik_parolalar[ip] = veri.get("parolalar", [])
                if not self.acik_parolalar[ip]:
                    self.p.bildir(self.t("parola_yok"))
        self.p.yetkili("parolalar", ip, sonra=sonra)

    def parola_gizle(self, ip):
        self.acik_parolalar.pop(ip, None)
        self.guncelle()

    def not_duzenle(self, ip, eski):
        giris = Gtk.Entry()
        giris.set_text(eski)
        giris.set_max_length(500)
        giris.set_activates_default(True)
        if tema.onay_sor(self.p, self.t("not_baslik", ip=ip), self.t("not_aciklama"),
                         self.t("kaydet"), self.t("iptal"), ek=giris):
            try:
                V.not_yaz(ip, giris.get_text())
            except OSError:
                pass
            self.guncelle()
