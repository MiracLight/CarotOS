# -*- coding: utf-8 -*-
"""Raporlar: donem secimi, onizleme, HTML ve CSV disa aktarma."""

import os
import time
from datetime import datetime, timedelta

from gi.repository import GLib, Gtk

import ag
import kanarya
import tema
from arayuz import veri as V
from arayuz.sayfalar import Sayfa
from arayuz.sayfalar.pano import saatlik_renk


class RaporSayfasi(Sayfa):
    ANAHTAR = "rapor"

    def __init__(self, p):
        super().__init__(p)
        self.donem = "7"
        bugun = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.ozel = ((bugun - timedelta(days=6)).timestamp(), (bugun + timedelta(days=1)).timestamp())
        self._onbellek = (None, None)

    def aralik(self):
        simdi = time.time()
        bugun = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if self.donem == "bugun":
            return bugun.timestamp(), simdi + 1
        if self.donem == "7":
            return simdi - 7 * 86400, simdi + 1
        if self.donem == "30":
            return simdi - 30 * 86400, simdi + 1
        return self.ozel

    def ozet(self):
        bas, bit = self.aralik()
        anahtar = (self.p.akis.surum, self.donem, round(bas / 60), round(bit / 60))
        if self._onbellek[0] != anahtar:
            self._onbellek = (anahtar, V.donem_ozeti(self.p.akis.olaylar, bas, bit))
        return self._onbellek[1]

    def kur(self):
        kok = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        dis, ic = tema.kart(14, 8)
        u = Gtk.Box(spacing=10)
        u.pack_start(tema.etiket(self.t("donem"), "kart-baslik"), False, False, 0)
        secim, self.secim_dugmeleri = tema.secim_grubu(
            [("bugun", self.t("d_bugun")), ("7", self.t("d_7")), ("30", self.t("d_30")),
             ("ozel", self.t("d_ozel"))], self.donem, self.donem_degisti)
        u.pack_start(secim, False, False, 0)
        u.pack_end(tema.dugme(self.t("csv_aktar"), None, self.disa_aktar, "csv"), False, False, 0)
        u.pack_end(tema.dugme(self.t("html_rapor"), "ana", self.disa_aktar, "html"), False, False, 0)
        ic.pack_start(u, False, False, 0)
        kok.pack_start(dis, False, False, 0)
        self.onizleme = Gtk.Box()
        kok.pack_start(self.onizleme, False, False, 0)
        return kok

    def donem_degisti(self, anahtar):
        if anahtar == "ozel" and not self.ozel_sec():
            onceki = self.donem          # vazgecildi: onceki secime don
            GLib.idle_add(lambda: self.secim_dugmeleri[onceki].set_active(True) and False)
            return
        self.donem = anahtar
        self.guncelle()

    def ozel_sec(self):
        ek = Gtk.Box(spacing=16)
        takvimler = []
        for ts in (self.ozel[0], self.ozel[1] - 86400):
            d = datetime.fromtimestamp(ts)
            c = Gtk.Calendar()
            c.select_month(d.month - 1, d.year)
            c.select_day(d.day)
            ek.pack_start(c, False, False, 0)
            takvimler.append(c)
        if not tema.onay_sor(self.p, self.t("ozel_aralik_baslik"), self.t("ozel_aralik_metin"),
                             self.t("uygula"), self.t("iptal"), ek=ek):
            return False
        gunler = []
        for c in takvimler:
            y, m, g = c.get_date()
            gunler.append(datetime(y, m + 1, g))
        a, b = sorted(gunler)
        self.ozel = (a.timestamp(), (b + timedelta(days=1)).timestamp())
        return True

    # -- one cikanlar --------------------------------------------------------------
    def one_cikanlar(self, oz):
        p = self.p
        mesajlar = []
        for k in [k for k in oz["kaynaklar"] if k["risk"] >= 30][:3]:
            m = self.t("oc_saldirgan", ip=k["kaynak"], cihaz=p.cihaz_adi(k["kaynak"]) or "?",
                       n=k["sayi"], davranis=", ".join(self.t("d_" + d) for d in k["davranis"])
                       or self.t("tur_baglanti").lower())
            if k["kullanicilar"]:
                m += self.t("oc_kullanicilar", liste=", ".join(
                    u for u, _ in k["kullanicilar"].most_common(3)))
            mesajlar.append(m)
        for k in oz["kaynaklar"]:
            if "iot_botu" in k["davranis"]:
                mesajlar.append(self.t("oc_iot", ip=k["kaynak"]))
                break
        for o in kanarya.olaylari_oku(500):
            if oz["bas"] <= o.get("ts", 0) < oz["bit"]:
                mesajlar.append(self.t("oc_kanarya", ad=os.path.basename(o["yol"]),
                                       zaman=datetime.fromtimestamp(o["ts"]).strftime("%d.%m %H:%M"),
                                       tur=self.t("kt_" + o.get("tur", "acildi"))
                                       if o.get("tur") in ("acildi", "degisti", "silindi", "tasindi")
                                       else o.get("tur", "")))
        if oz["yeni_kaynak"]:
            mesajlar.append(self.t("oc_yeni", n=oz["yeni_kaynak"]))
        d = V.degisim(oz["toplam"], oz["onceki_toplam"])
        if isinstance(d, int) and oz["onceki_toplam"] >= 10 and abs(d) >= 20:
            mesajlar.append(self.t("oc_artis" if d > 0 else "oc_azalis", n=abs(d)))
        return mesajlar[:6]

    # -- guncelleme ------------------------------------------------------------------
    def guncelle(self):
        p = self.p
        oz = self.ozet()
        self.temizle(self.onizleme)
        dis, ic = tema.kart(26, 12)
        bas = datetime.fromtimestamp(oz["bas"]).strftime("%d.%m.%Y")
        bit = datetime.fromtimestamp(min(oz["bit"], time.time()) - 1).strftime("%d.%m.%Y")
        ic.pack_start(tema.etiket(self.t("rapor_on_baslik", aralik=bas if bas == bit else
                                         f"{bas} – {bit}"), "sayfa-baslik"), False, False, 0)
        ag_adi = ag.yerel_ag()
        ic.pack_start(tema.etiket(self.t("rapor_on_alt", ag=f"{self.t('yerel_ag')} {ag_adi}"
                                         if ag_adi else self.t("yerel_ag")), "kart-alt"),
                      False, False, 0)
        s = Gtk.Box(spacing=16, homogeneous=True)

        def fark(a, b):
            d = V.degisim(a, b)
            if not isinstance(d, int) or d == 0:
                return "", "notr"
            return self.t("fark_yuzde", y="▲ " if d > 0 else "▼ ", n=abs(d)), "kotu" if d > 0 else "iyi"
        for deger, ad, (f, tur) in ((oz["toplam"], self.t("r_toplam"),
                                     fark(oz["toplam"], oz["onceki_toplam"])),
                                    (oz["kaynak"], self.t("r_kaynak"),
                                     fark(oz["kaynak"], oz["onceki_kaynak"])),
                                    (oz["giris"], self.t("r_giris"), ("", "notr")),
                                    (oz["yeni_kaynak"], self.t("r_yeni_kaynak"), ("", "notr"))):
            k = tema.KpiKutusu(ad)
            k.ayarla(deger, fark=f, tur=tur)
            s.pack_start(k, True, True, 0)
        ic.pack_start(s, False, False, 4)
        ic.pack_start(tema.etiket(self.t("r_one_cikanlar"), "kart-baslik"), False, False, 6)
        for m in self.one_cikanlar(oz) or [self.t("r_sakin")]:
            ic.pack_start(tema.etiket("•  " + m, None, sar=True, genislik=110), False, False, 0)
        sayilar, etiketler = oz["seri"]
        grafik = tema.CizimAlani(lambda cr, w, h, v: tema.cubuk_grafik(
            cr, w, h, v[0], v[1], saatlik_renk, max(1, len(v[0]) // 10),
            bos_metin=self.t("liste_bos")), -1, 180, (sayilar, etiketler))
        ic.pack_start(grafik, False, False, 8)
        if oz["bas"] < time.time() - p.ayar["sakla_gun"] * 86400:
            ic.pack_start(tema.etiket(self.t("veri_notu", gun=p.ayar["sakla_gun"]), "silik"),
                          False, False, 0)
        self.onizleme.pack_start(dis, True, True, 0)
        self.onizleme.show_all()

    # -- disa aktarma ----------------------------------------------------------------
    def disa_aktar(self, tur):
        p = self.p
        oz = self.ozet()
        d = Gtk.FileChooserDialog(title=self.t("html_rapor" if tur == "html" else "csv_aktar"),
                                  transient_for=p, action=Gtk.FileChooserAction.SAVE)
        d.add_buttons(self.t("iptal"), Gtk.ResponseType.CANCEL,
                      self.t("kaydet"), Gtk.ResponseType.OK)
        d.set_do_overwrite_confirmation(True)
        belgeler = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS) \
            or os.path.expanduser("~")
        d.set_current_folder(belgeler)
        d.set_current_name(f"carotpot-rapor-{datetime.now():%Y%m%d-%H%M}.{tur}")
        f = Gtk.FileFilter()
        f.set_name(self.t("html_filtre" if tur == "html" else "csv_filtre"))
        f.add_pattern(f"*.{tur}")
        d.add_filter(f)
        yol = d.get_filename() if d.run() == Gtk.ResponseType.OK else None
        d.destroy()
        if not yol:
            return
        try:
            if tur == "html":
                icerik = V.rapor_html(oz, self.t, p.lang, p.cihaz_adi, self.one_cikanlar(oz))
            else:
                icerik = V.rapor_csv(p.akis.olaylar, oz["bas"], oz["bit"])
            with open(yol, "w", encoding="utf-8", newline="") as fh:
                fh.write(icerik)
        except OSError as hata:
            p.bildir(self.t("kaydedilemedi", hata=str(hata)), "hata")
            return
        p.bildir(self.t("rapor_kaydedildi", yol=yol), "basari")
