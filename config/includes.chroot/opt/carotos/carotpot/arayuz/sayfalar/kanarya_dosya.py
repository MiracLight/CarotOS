# -*- coding: utf-8 -*-
"""Kanarya dosyalar: yem dosya olusturma, izleme durumu ve tetiklenmeler.
Izleme oturumdaki "carotpot.py bildir" surecindedir; yetki gerekmez."""

import os
from datetime import datetime

from gi.repository import GLib, Gtk, Pango

import kanarya
import tema
from arayuz import veri as V
from arayuz.metinler import M
from arayuz.sayfalar import Sayfa


def kisa_yol(yol):
    ev = os.path.expanduser("~")
    return "~" + yol[len(ev):] if yol.startswith(ev + os.sep) else yol


class KanaryaSayfasi(Sayfa):
    ANAHTAR = "kanarya"

    def kur(self):
        kok = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.uyari = Gtk.Box()
        self.uyari.set_no_show_all(True)
        kok.pack_start(self.uyari, False, False, 0)
        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("kanarya"), self.t("kanarya_kart_alt"),
                          sag=tema.dugme(self.t("kanarya_ekle"), "ana", self.ekle))
        self.liste = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ic.pack_start(self.liste, False, False, 4)
        kok.pack_start(dis, False, False, 0)

        alt = Gtk.Box(spacing=16, homogeneous=True)
        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("sablonlar"), self.t("sablonlar_alt"))
        akis = Gtk.FlowBox()
        akis.set_selection_mode(Gtk.SelectionMode.NONE)
        akis.set_max_children_per_line(3)
        akis.set_column_spacing(8)
        akis.set_row_spacing(8)
        for anahtar, s in kanarya.SABLONLAR.items():
            d = tema.dugme(s[self.p.lang], None, self.ekle, anahtar)
            d.set_halign(Gtk.Align.START)
            akis.add(d)
        ic.pack_start(akis, False, False, 0)
        alt.pack_start(dis, True, True, 0)
        dis, ic = tema.kart()
        tema.kart_basligi(ic, self.t("son_tetiklenmeler"))
        self.tetikler = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ic.pack_start(self.tetikler, False, False, 0)
        alt.pack_start(dis, True, True, 0)
        kok.pack_start(alt, False, False, 0)
        kutu, _ = tema.not_kutusu(self.t("kanarya_not"), "bilgi")
        kok.pack_start(kutu, False, False, 0)
        return kok

    def tetik_metni(self, o):
        zaman = datetime.fromtimestamp(o["ts"]).strftime("%d.%m %H:%M")
        tur = o.get("tur", "")
        tur = self.t("kt_" + tur) if "kt_" + tur in M else tur
        if o.get("surec"):
            return self.t("k_tetik_surec", zaman=zaman, tur=tur, surec=o["surec"])
        return self.t("k_tetik", zaman=zaman, tur=tur)

    def guncelle(self):
        p = self.p
        self.temizle(self.uyari)
        if p.kanaryalar and not p.bildirici:
            dis, ic = tema.kart(12, 8, "tehlikeli")
            s = Gtk.Box(spacing=12)
            s.pack_start(tema.Ikon("uyari", 18, "kirmizi"), False, False, 0)
            s.pack_start(tema.etiket(self.t("izleyici_kapali"), None, sar=True), True, True, 0)
            s.pack_end(tema.dugme(self.t("izleyiciyi_baslat"), "ana", self.izleyici_baslat),
                       False, False, 0)
            ic.pack_start(s, False, False, 0)
            self.uyari.pack_start(dis, True, True, 0)
        self.bosken_gizle(self.uyari)

        self.temizle(self.liste)
        if not p.kanaryalar:
            self.liste.pack_start(tema.bos_durum("elmas", self.t("kanarya_bos_baslik"),
                                                 self.t("kanarya_bos")), False, False, 0)
        for k in p.kanaryalar:
            r = Gtk.Box(spacing=12)
            r.set_margin_top(4)
            r.set_margin_bottom(4)
            if not k["var"]:
                rozet = tema.rozet(self.t("k_kayip"), "gri")
            elif k["tetik"]:
                rozet = tema.rozet(self.t("k_tetiklendi"), "kirmizi")
            elif not p.bildirici:
                rozet = tema.rozet(self.t("k_beklemede"), "sari")
            else:
                rozet = tema.rozet(self.t("k_izleniyor"), "yesil")
            rozet.set_size_request(96, -1)
            r.pack_start(rozet, False, False, 0)
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            v.pack_start(tema.etiket(os.path.basename(k["yol"]), "kart-baslik"), False, False, 0)
            durum = self.tetik_metni(k["tetik"]) if k["tetik"] else self.t("k_hic")
            a = tema.etiket(f"{kisa_yol(k['yol'])} · {durum}", "kart-alt")
            a.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            v.pack_start(a, False, False, 0)
            r.pack_start(v, True, True, 0)
            r.pack_end(tema.dugme(self.t("kaldir"), None, self.kaldir, k["yol"]), False, False, 0)
            self.liste.pack_start(r, False, False, 0)
        self.liste.show_all()

        self.temizle(self.tetikler)
        olaylar = kanarya.olaylari_oku(50)[-8:]
        if not olaylar:
            self.tetikler.pack_start(tema.etiket(self.t("liste_bos"), "soluk"), False, False, 2)
        for o in reversed(olaylar):
            s = Gtk.Box(spacing=10)
            s.pack_start(tema.Ikon("uyari", 14, "kirmizi"), False, False, 0)
            e = tema.etiket(f"{os.path.basename(o['yol'])} · {self.tetik_metni(o)}", "kart-alt")
            e.set_ellipsize(Pango.EllipsizeMode.END)
            s.pack_start(e, True, True, 0)
            self.tetikler.pack_start(s, False, False, 2)
        self.tetikler.show_all()

    # -- eylemler -----------------------------------------------------------------
    def izleyici_baslat(self):
        V.bildirici_baslat()
        self.p._bildirici_zaman = 0
        GLib.timeout_add(1200, lambda: (self.p.durum_tazele(zorla=True), self.guncelle(), False)[-1])

    def ekle(self, sablon="parola"):
        p = self.p
        d = Gtk.Dialog(transient_for=p, modal=True, title=self.t("kanarya_ekle_baslik"))
        d.set_resizable(False)
        alan = d.get_content_area()
        alan.set_spacing(10)
        for k in ("top", "bottom", "start", "end"):
            getattr(alan, f"set_margin_{k}")(18)
        alan.pack_start(tema.etiket(self.t("kanarya_ekle_baslik"), "buyuk-baslik"), False, False, 0)
        izgara = Gtk.Grid(column_spacing=12, row_spacing=10)
        sablon_kutu = Gtk.ComboBoxText()
        for anahtar, s in kanarya.SABLONLAR.items():
            sablon_kutu.append(anahtar, s[p.lang])
        klasor = Gtk.FileChooserButton(action=Gtk.FileChooserAction.SELECT_FOLDER)
        belgeler = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS) \
            or os.path.expanduser("~")
        klasor.set_current_folder(belgeler)
        ad = Gtk.Entry()
        ad.set_width_chars(28)

        def sablon_degisti(kutu):
            ad.set_text(kanarya.SABLONLAR[kutu.get_active_id()]["dosya"])
            if kutu.get_active_id() == "ssh":
                ssh = os.path.expanduser("~/.ssh")
                klasor.set_current_folder(ssh if os.path.isdir(ssh) else belgeler)
        sablon_kutu.connect("changed", sablon_degisti)
        sablon_kutu.set_active_id(sablon)
        for i, (etk, w) in enumerate(((self.t("sablon"), sablon_kutu), (self.t("klasor"), klasor),
                                      (self.t("dosya_adi"), ad))):
            izgara.attach(tema.etiket(etk, "soluk"), 0, i, 1, 1)
            izgara.attach(w, 1, i, 1, 1)
        alan.pack_start(izgara, False, False, 0)
        hata = tema.etiket("", "hata-yazi", sar=True)
        alan.pack_start(hata, False, False, 0)
        satir = Gtk.Box(spacing=8)
        satir.pack_end(tema.dugme(self.t("olustur"), "ana", d.response, Gtk.ResponseType.OK),
                       False, False, 0)
        satir.pack_end(tema.dugme(self.t("iptal"), None, d.response, Gtk.ResponseType.CANCEL),
                       False, False, 0)
        alan.pack_start(satir, False, False, 6)
        d.show_all()
        while d.run() == Gtk.ResponseType.OK:
            try:
                kayit = kanarya.kanarya_olustur(sablon_kutu.get_active_id(),
                                                klasor.get_filename() or belgeler, ad.get_text())
            except FileExistsError:
                hata.set_text(self.t("dosya_var"))
                continue
            except (OSError, ValueError) as h:
                hata.set_text(self.t("kanarya_hata", hata=str(h)))
                continue
            p.bildir(self.t("kanarya_eklendi", ad=os.path.basename(kayit["yol"])), "basari")
            V.bildirici_baslat()
            p._bildirici_zaman = 0
            break
        d.destroy()
        p.durum_tazele(zorla=True)
        self.guncelle()
        GLib.timeout_add(1500, lambda: (p.durum_tazele(zorla=True), self.guncelle(), False)[-1])

    def kaldir(self, yol):
        if not tema.onay_sor(self.p, self.t("kanarya_kaldir_baslik", ad=os.path.basename(yol)),
                             self.t("kanarya_kaldir_onay"), self.t("evet_kaldir"),
                             self.t("iptal"), tehlike=True):
            return
        kanarya.kanarya_kaldir(yol)
        self.p.durum_tazele(zorla=True)
        self.p.ust_guncelle()
        self.guncelle()
