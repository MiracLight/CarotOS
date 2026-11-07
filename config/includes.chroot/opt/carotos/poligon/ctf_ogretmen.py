# -*- coding: utf-8 -*-
"""CarotOS Poligon CTF -- ogretmen paneli (GTK3 parcasi).

Ogretmen uygulamasinin bir sayfasi olarak gomulur: yarismayi baslatir/bitirir, canli (donmamis) skoru ve gorev
istatistigini gosterir, sonuclari CSV olarak kaydeder. Veri ayni surecte (oda.ctf_oturumu()) tutulur.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ortak"))
import dil_koprusu as _dil  # noqa: E402
from ctf_pencere import DURUM_AD, DURUM_RENK, KATEGORI_AD, T, gorevleri_grupla, sure_metni  # noqa: E402

VARSAYILAN_SURE_DK = 45
YENILEME_MS = 2000


def csv_dosya_adi(an: float | None = None) -> str:
    return "poligon-ctf-%s.csv" % time.strftime("%Y%m%d-%H%M", time.localtime(an if an is not None else time.time()))


def csv_kaydet(yol: str, metin: str) -> None:
    """Excel Turkce karakterleri dogru acsin diye BOM'lu UTF-8."""
    with open(yol, "w", encoding="utf-8-sig", newline="") as f:
        f.write(metin)


def panel_olustur(oda, dil: str, ust=None):
    """Dondurur: Panel nesnesi (.widget, .dil_ayarla(kod), .yenile())."""
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk
    import tema

    class Panel:
        def __init__(self):
            self.oda, self.dil, self.ust = oda, dil, ust
            self.secili: dict[str, Gtk.CheckButton] = {}
            self._kapali = False
            self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            self.widget.connect("destroy", lambda *_: setattr(self, "_kapali", True))
            self._kontrol_karti()
            self._skor_karti()
            self.dil_ayarla(dil)
            GLib.timeout_add(YENILEME_MS, self._zamanlayici)

        def t(self, m, **kw):
            return _dil.T(m, self.dil, **kw) if kw else _dil.sec(m, self.dil)

        @property
        def ctf(self):
            return self.oda.ctf_oturumu()

        # -- kurulum ---------------------------------------------------------------------------------------
        def _kontrol_karti(self):
            kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            tema.sinif(kart, "kart kart-dolgu")
            ust_satir = Gtk.Box(spacing=12)
            self.durum_rozeti = tema.rozet("", "gri")
            self.sure_etiketi = Gtk.Label(xalign=0)
            ust_satir.pack_start(self.durum_rozeti, False, False, 0)
            ust_satir.pack_start(self.sure_etiketi, False, False, 0)
            kart.pack_start(ust_satir, False, False, 0)

            ayar = Gtk.Box(spacing=12)
            self.sure_girisi = Gtk.SpinButton.new_with_range(5, 240, 5)
            self.sure_girisi.set_value(VARSAYILAN_SURE_DK)
            self.dondurma_girisi = Gtk.SpinButton.new_with_range(0, 60, 5)
            self.sure_et, self.dondurma_et = Gtk.Label(xalign=0), Gtk.Label(xalign=0)
            for e, w in ((self.sure_et, self.sure_girisi), (self.dondurma_et, self.dondurma_girisi)):
                ayar.pack_start(e, False, False, 0)
                ayar.pack_start(w, False, False, 0)
            kart.pack_start(ayar, False, False, 0)

            self.gorev_et = Gtk.Label(xalign=0)
            tema.sinif(self.gorev_et, "soluk")
            kart.pack_start(self.gorev_et, False, False, 0)
            izgara = Gtk.FlowBox()
            izgara.set_selection_mode(Gtk.SelectionMode.NONE)
            izgara.set_max_children_per_line(3)
            izgara.set_homogeneous(False)
            for kategori, grup in gorevleri_grupla([{"id": g["id"], "kategori": g["kategori"], "zorluk": g["zorluk"],
                                                      "baslik": g["baslik"]} for g in self.ctf.gorevler.values()]):
                for g in grup:
                    cb = Gtk.CheckButton()
                    cb.set_active(True)
                    cb._baslik = g["baslik"]
                    cb._kategori = kategori
                    self.secili[g["id"]] = cb
                    izgara.add(cb)
            kart.pack_start(izgara, False, False, 0)

            dugmeler = Gtk.Box(spacing=8)
            self.baslat_dugmesi = Gtk.Button()
            tema.sinif(self.baslat_dugmesi, "ana")
            self.baslat_dugmesi.connect("clicked", self._baslat)
            self.bitir_dugmesi = Gtk.Button()
            self.bitir_dugmesi.connect("clicked", self._bitir)
            self.csv_dugmesi = Gtk.Button()
            self.csv_dugmesi.connect("clicked", self._csv)
            for d in (self.baslat_dugmesi, self.bitir_dugmesi, self.csv_dugmesi):
                dugmeler.pack_start(d, False, False, 0)
            kart.pack_start(dugmeler, False, False, 0)
            self.not_etiketi = Gtk.Label(xalign=0, wrap=True)
            tema.sinif(self.not_etiketi, "soluk")
            kart.pack_start(self.not_etiketi, False, False, 0)
            self.widget.pack_start(kart, False, False, 0)

        def _agac(self, tur, n):
            model = Gtk.ListStore(*tur)
            agac = Gtk.TreeView(model=model)
            sutunlar = []
            for i in range(n):
                s = Gtk.TreeViewColumn("", Gtk.CellRendererText(), text=i)
                agac.append_column(s)
                sutunlar.append(s)
            kay = Gtk.ScrolledWindow()
            kay.set_min_content_height(120)
            kay.add(agac)
            return model, sutunlar, kay

        def _skor_karti(self):
            kart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            tema.sinif(kart, "kart kart-dolgu")
            self.skor_baslik = Gtk.Label(xalign=0)
            tema.sinif(self.skor_baslik, "kart-baslik")
            kart.pack_start(self.skor_baslik, False, False, 0)
            self.skor_modeli, self.skor_sutunlari, kay = self._agac((int, str, int, int, int), 5)
            kart.pack_start(kay, True, True, 0)
            self.ist_baslik = Gtk.Label(xalign=0)
            tema.sinif(self.ist_baslik, "kart-baslik")
            kart.pack_start(self.ist_baslik, False, False, 0)
            self.ist_modeli, self.ist_sutunlari, kay2 = self._agac((str, str, int, int), 4)
            kart.pack_start(kay2, True, True, 0)
            self.widget.pack_start(kart, True, True, 0)

        # -- metinler -------------------------------------------------------------------------------------------
        def dil_ayarla(self, dil):
            self.dil = dil
            self.sure_et.set_text(self.t(T("Süre (dk)", "Duration (min)")))
            self.dondurma_et.set_text(self.t(T("Son dakikalarda skoru dondur (dk, 0 = kapalı)",
                                               "Freeze the score in the last minutes (0 = off)")))
            self.gorev_et.set_text(self.t(T("Yarışmaya girecek görevler", "Challenges in the contest")))
            for gid, cb in self.secili.items():
                cb.set_label("%s · %s" % (self.t(KATEGORI_AD.get(cb._kategori, T(cb._kategori, cb._kategori))),
                                           self.t(cb._baslik)))
            self.baslat_dugmesi.set_label(self.t(T("Yarışmayı başlat", "Start the contest")))
            self.bitir_dugmesi.set_label(self.t(T("Bitir", "End")))
            self.csv_dugmesi.set_label(self.t(T("Sonuçları CSV kaydet", "Save results as CSV")))
            self.skor_baslik.set_text(self.t(T("Canlı skor tablosu", "Live scoreboard")))
            self.ist_baslik.set_text(self.t(T("Görev istatistikleri", "Challenge statistics")))
            for s, m in zip(self.skor_sutunlari, (T("Sıra", "Rank"), T("Öğrenci", "Student"), T("Puan", "Points"),
                                                    T("Çözülen", "Solved"), T("Bonus", "Bonus"))):
                s.set_title(self.t(m))
            for s, m in zip(self.ist_sutunlari, (T("Görev", "Challenge"), T("Kategori", "Category"),
                                                   T("Çözen", "Solved by"), T("Deneme", "Attempts"))):
                s.set_title(self.t(m))
            self.yenile()

        # -- eylemler ---------------------------------------------------------------------------------------------------
        def _secili_idler(self):
            return [gid for gid, cb in self.secili.items() if cb.get_active()]

        def _baslat(self, _d):
            import ctf_cekirdek
            idler = self._secili_idler()
            if not idler:
                self._not(self.t(T("En az bir görev seç.", "Pick at least one challenge.")))
                return
            if self.ctf.cozumler and not tema.onay_sor(
                    self.ust, self.t(T("Yeni yarışma başlasın mı?", "Start a new contest?")),
                    self.t(T("Önceki yarışmanın sonuçları silinir. Sonuçları kaydetmediysen önce CSV olarak kaydet.",
                             "The previous contest's results are erased. Save them as CSV first if you have not.")),
                    self.t(T("Başlat", "Start")), self.t(T("Vazgeç", "Cancel")), tehlike=True):
                return
            try:
                if self.ctf.durum() == "surec":
                    self._not(self.t(T("Yarışma zaten sürüyor.", "The contest is already running.")))
                    return
                self.ctf.baslat(self.sure_girisi.get_value(), idler, self.dondurma_girisi.get_value())
            except ctf_cekirdek.CtfHata as h:
                self._not(self.t(T("Yarışma başlatılamadı ({k}).", "Could not start the contest ({k})."), k=h.kod))
                return
            self._not("")
            self.yenile()

        def _bitir(self, _d):
            if self.ctf.durum() != "surec":
                return
            if tema.onay_sor(self.ust, self.t(T("Yarışma bitirilsin mi?", "End the contest?")),
                             self.t(T("Öğrenciler artık bayrak gönderemez.", "Students will no longer be able to submit flags.")),
                             self.t(T("Bitir", "End")), self.t(T("Vazgeç", "Cancel")), tehlike=True):
                self.ctf.bitir()
                self.yenile()

        def _csv(self, _d):
            if not self.ctf.cozumler and self.ctf.durum() == "hazir":
                self._not(self.t(T("Kaydedilecek sonuç yok.", "There are no results to save.")))
                return
            dlg = Gtk.FileChooserDialog(title=self.t(T("Sonuçları kaydet", "Save results")), transient_for=self.ust,
                                        action=Gtk.FileChooserAction.SAVE)
            dlg.add_buttons(self.t(T("Vazgeç", "Cancel")), Gtk.ResponseType.CANCEL,
                            self.t(T("Kaydet", "Save")), Gtk.ResponseType.OK)
            dlg.set_current_name(csv_dosya_adi())
            dlg.set_do_overwrite_confirmation(True)
            try:
                if dlg.run() == Gtk.ResponseType.OK:
                    yol = dlg.get_filename()
                    try:
                        csv_kaydet(yol, self.ctf.csv_metni())
                        self._not(self.t(T("Kaydedildi: {y}", "Saved: {y}"), y=yol))
                    except OSError:
                        self._not(self.t(T("Dosya kaydedilemedi.", "Could not save the file.")))
            finally:
                dlg.destroy()

        def _not(self, metin):
            self.not_etiketi.set_text(metin)

        # -- yenileme -----------------------------------------------------------------------------------------------------------
        def _zamanlayici(self):
            if self._kapali:
                return False
            self.yenile()
            return True

        def yenile(self):
            ctf = self.ctf
            kod = ctf.durum()
            tema.rozet_ayarla(self.durum_rozeti, self.t(DURUM_AD[kod]), DURUM_RENK[kod])
            ozel = ""
            if kod == "surec":
                ozel = self.t(T("Kalan: {s}", "Remaining: {s}"), s=sure_metni(ctf.kalan_sn()))
                if ctf.donuk_mu():
                    ozel += " · " + self.t(T("skor öğrencilere donuk gösteriliyor",
                                             "scoreboard is frozen for students"))
            self.sure_etiketi.set_text(ozel)
            calisiyor = kod == "surec"
            for w in (self.sure_girisi, self.dondurma_girisi, self.baslat_dugmesi):
                w.set_sensitive(not calisiyor)
            for cb in self.secili.values():
                cb.set_sensitive(not calisiyor)
            self.bitir_dugmesi.set_sensitive(calisiyor)
            self.csv_dugmesi.set_sensitive(kod != "hazir")
            self.skor_modeli.clear()
            for r in ctf.skor_tablosu(ogretmen=True)["satirlar"]:
                self.skor_modeli.append([r["sira"], r["ad"], r["puan"], r["cozulen"], r["bonus"]])
            self.ist_modeli.clear()
            for r in ctf.gorev_istatistigi():
                g = ctf.gorevler[r["id"]]
                self.ist_modeli.append([_dil.sec(g["baslik"], self.dil),
                                        _dil.sec(KATEGORI_AD.get(r["kategori"], T(r["kategori"], r["kategori"])), self.dil),
                                        r["cozen"], r["deneme"]])

    return Panel()
