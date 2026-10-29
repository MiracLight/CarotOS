# -*- coding: utf-8 -*-
"""Engelleme merkezi: onayli (ve sureli) engeller, hic engellenmeyecekler
listesi ve otomatik engelleme (fail2ban)."""

import copy
import time

from gi.repository import Gtk

import ag
import carotpot as CP
import tema
from arayuz import veri as V
from arayuz.sayfalar import Sayfa
from arayuz.sayfalar.saldirgan import SURELER


class EngelSayfasi(Sayfa):
    ANAHTAR = "engel"

    def __init__(self, p):
        super().__init__(p)
        self._ag = (0, None, [])
        self._kilit = False
        self._davranis = (None, {})

    def ag_bilgisi(self):
        if time.time() - self._ag[0] > 30:
            self._ag = (time.time(), ag.ag_gecidi(), [ip for ip, _ in ag.kendi_adresler()])
        return self._ag[1], self._ag[2]

    def davranis(self, ip):
        if self._davranis[0] != self.p.akis.surum:
            oz = V.kaynak_ozeti(self.p.akis.olaylar, time.time(), 0)
            self._davranis = (self.p.akis.surum, {k["kaynak"]: k for k in oz})
        return self._davranis[1].get(ip)

    def kur(self):
        kok = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.uyari = Gtk.Box()
        self.uyari.set_no_show_all(True)
        kok.pack_start(self.uyari, False, False, 0)
        ust = Gtk.Box(spacing=16, homogeneous=True)
        self.k_etkin = tema.KpiKutusu(self.t("kpi_etkin_engel"))
        self.k_bitis = tema.KpiKutusu(self.t("kpi_yakin_bitis"))
        self.k_oto = tema.KpiKutusu(self.t("kpi_otomatik"))
        for k in (self.k_etkin, self.k_bitis, self.k_oto):
            ust.pack_start(k, True, True, 0)
        kok.pack_start(ust, False, False, 0)

        dis, ic = tema.kart()
        self.engelle_dugme = tema.dugme(self.t("adres_engelle"), "ana", self.adres_engelle)
        tema.kart_basligi(ic, self.t("engellenen_adresler"), sag=self.engelle_dugme)
        self.tablo_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ic.pack_start(self.tablo_kutu, False, False, 0)
        kok.pack_start(dis, False, False, 0)

        alt = Gtk.Box(spacing=16, homogeneous=True)
        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("hic_engellenmeyecek"), self.t("hic_alt"))
        self.korunan = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ic.pack_start(self.korunan, False, False, 0)
        ekle = Gtk.Box(spacing=8)
        self.yeni_ip = Gtk.Entry()
        self.yeni_ip.set_placeholder_text(self.t("adres_ornek"))
        self.yeni_ip.connect("activate", lambda *_: self.yoksay_ekle())
        ekle.pack_start(self.yeni_ip, True, True, 0)
        ekle.pack_start(tema.dugme(self.t("adres_ekle"), None, self.yoksay_ekle), False, False, 0)
        ic.pack_start(ekle, False, False, 6)
        alt.pack_start(dis, True, True, 0)
        dis, ic = tema.kart()
        u = Gtk.Box(spacing=10)
        u.pack_start(tema.etiket(self.t("otomatik_baslik"), "kart-baslik"), True, True, 0)
        self.oto = Gtk.Switch()
        self.oto.set_valign(Gtk.Align.CENTER)
        self.oto.connect("notify::active", self.oto_degisti)
        u.pack_end(self.oto, False, False, 0)
        ic.pack_start(u, False, False, 0)
        ic.pack_start(tema.etiket(self.t("otomatik_aciklama"), "kart-alt", sar=True, genislik=60),
                      False, False, 0)
        alt.pack_start(dis, True, True, 0)
        kok.pack_start(alt, False, False, 0)
        return kok

    def guncelle(self):
        p = self.p
        simdi = time.time()
        self.temizle(self.uyari)
        if p.ufw is False:
            kutu, _ = tema.not_kutusu(self.t("ufw_kapali"), "hata")
            self.uyari.pack_start(kutu, True, True, 0)
        self.bosken_gizle(self.uyari)

        etkin = [e for e in p.engeller if not e.get("bitis") or e["bitis"] > simdi]
        self.k_etkin.ayarla(len(etkin))
        bitisler = [e["bitis"] for e in etkin if e.get("bitis")]
        self.k_bitis.ayarla(p.sure(min(bitisler) - simdi) if bitisler else "—", orta=True)
        self.k_oto.ayarla(self.t("acik") if p.otomatik else self.t("kapali"),
                          fark=self.t("fail2ban") if p.otomatik else self.t("oner_onay"),
                          tur="iyi", orta=True)

        self.temizle(self.tablo_kutu)
        if not p.engeller:
            self.tablo_kutu.pack_start(tema.etiket(self.t("engel_bos"), "soluk"), False, False, 6)
        else:
            izgara = Gtk.Grid(column_spacing=24, row_spacing=10)
            for j, b in enumerate(("s_adres", "s_neden", "s_baslangic", "s_bitis", "s_yontem")):
                izgara.attach(tema.etiket(self.t(b), "kart-alt"), j, 0, 1, 1)
            for i, e in enumerate(sorted(p.engeller, key=lambda e: -e.get("tarih", 0)), 1):
                k = self.davranis(e["ip"])
                neden = ", ".join(self.t("d_" + d) for d in k["davranis"][:2]) if k else ""
                if k and k["giris"]:
                    neden += f" ({k['giris']})"
                if e.get("bitis"):
                    bitis = self.t("suresi_doldu") if e["bitis"] <= simdi else p.saat(e["bitis"])
                else:
                    bitis = self.t("suresiz")
                hucreler = (tema.etiket(e["ip"], "ip", sec=True),
                            tema.etiket(neden or self.t("neden_yok"), None, sar=True, genislik=36),
                            tema.etiket(p.saat(e.get("tarih", simdi))), tema.etiket(bitis),
                            tema.etiket(self.t("elle_ufw"), "soluk"))
                for j, h in enumerate(hucreler):
                    h.set_valign(Gtk.Align.CENTER)
                    izgara.attach(h, j, i, 1, 1)
                d = tema.dugme(self.t("kaldir"), "kucuk", p.yetkili, "kaldir", e["ip"])
                d.set_sensitive(p.mesgul is None)
                izgara.attach(d, 5, i, 1, 1)
            self.tablo_kutu.pack_start(izgara, False, False, 4)
        self.tablo_kutu.show_all()

        self.temizle(self.korunan)
        gecit, kendi = self.ag_bilgisi()
        satirlar = []
        if gecit:
            satirlar.append((f"{gecit} · {self.t('ag_gecidi')}", self.t("otomatik"), None))
        for ip in kendi:
            if not ip.startswith("fe80:"):
                satirlar.append((f"{ip} · {self.t('bu_bilgisayar')}", self.t("otomatik"), None))
        for ip in p.ayar["yoksay"]:
            ad = p.cihaz_adi(ip)
            satirlar.append((f"{ip}" + (f" · {ad}" if ad else ""), self.t("elle"), ip))
        for metin, tur, ip in satirlar:
            b = Gtk.Box(spacing=10)
            b.pack_start(tema.etiket(metin, "mono"), True, True, 0)
            if ip:
                b.pack_end(tema.dugme(self.t("kaldir"), "kucuk duz", self.yoksay_kaldir, ip),
                           False, False, 0)
            b.pack_end(tema.rozet(tur, "gri"), False, False, 0)
            self.korunan.pack_start(b, False, False, 2)
        self.korunan.show_all()

        self._kilit = True
        self.oto.set_active(p.otomatik)
        self._kilit = False
        self.mesgul_degisti()

    def mesgul_degisti(self):
        if hasattr(self, "engelle_dugme"):
            serbest = self.p.mesgul is None
            self.engelle_dugme.set_sensitive(serbest and self.p.ufw is not False)
            self.oto.set_sensitive(serbest)

    # -- eylemler ------------------------------------------------------------------
    def oto_degisti(self, sw, _pspec):
        if self._kilit:
            return
        istenen = sw.get_active()
        self._kilit = True
        sw.set_active(self.p.otomatik)      # sonuca gore guncelle() ayarlar
        self._kilit = False
        self.p.yetkili("otomatik", "ac" if istenen else "kapat")

    def adres_engelle(self):
        ek = Gtk.Grid(column_spacing=12, row_spacing=10)
        giris = Gtk.Entry()
        giris.set_placeholder_text(self.t("adres_ornek"))
        sure = Gtk.ComboBoxText()
        for kimlik, anahtar in SURELER:
            sure.append(kimlik, self.t(anahtar))
        sure.set_active_id("60")
        ek.attach(tema.etiket(self.t("s_adres"), "soluk"), 0, 0, 1, 1)
        ek.attach(giris, 1, 0, 1, 1)
        ek.attach(tema.etiket(self.t("engel_sure"), "soluk"), 0, 1, 1, 1)
        ek.attach(sure, 1, 1, 1, 1)
        if not tema.onay_sor(self.p, self.t("engel_adres_baslik"), self.t("engel_adres_metin"),
                             self.t("engelle"), self.t("iptal"), tehlike=True, ek=ek):
            return
        ip = giris.get_text().strip()
        adr = CP.adres_coz(ip)
        if adr is None:
            self.p.bildir(self.t("gecersiz_adres", ip=ip[:40]), "hata")
            return
        self.p.yetkili("engelle", str(adr), sure.get_active_id() or None,
                       basari=self.t("engellendi", ip=str(adr)))

    def yoksay_ekle(self):
        ip = self.yeni_ip.get_text().strip()
        adr = CP.adres_coz(ip)
        if adr is None:
            self.p.bildir(self.t("gecersiz_adres", ip=ip[:40]), "hata")
            return
        yeni = copy.deepcopy(self.p.ayar)
        yeni["yoksay"] = list(dict.fromkeys(yeni["yoksay"] + [str(adr)]))
        self.yeni_ip.set_text("")
        self.p.ayar_kaydet(yeni)

    def yoksay_kaldir(self, ip):
        yeni = copy.deepcopy(self.p.ayar)
        yeni["yoksay"] = [x for x in yeni["yoksay"] if x != ip]
        self.p.ayar_kaydet(yeni)
