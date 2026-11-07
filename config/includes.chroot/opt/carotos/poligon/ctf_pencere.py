# -*- coding: utf-8 -*-
"""CarotOS Poligon CTF -- ogrenci penceresi (GTK3).

Sunucu hakemdir: bu pencere yalnizca gosterir ve gonderir. Mantik (metin bicimleme, siralama) GTK'siz
fonksiyonlardir ve ayrica test edilir.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ortak"))
import dil_koprusu as _dil  # noqa: E402

KATEGORI_SIRASI = ("kodlama", "kriptografi", "hash", "log", "adli")
ZORLUK_SIRASI = {"kolay": 0, "orta": 1, "zor": 2}
YENILEME_SN = 3
KAYIT_KLASORU = "Poligon-CTF"


def T(tr, en):
    return {"tr": tr, "en": en}


KATEGORI_AD = {
    "kodlama": T("Kodlama", "Encoding"), "kriptografi": T("Kriptografi", "Cryptography"),
    "hash": T("Hash", "Hash"), "log": T("Günlük analizi", "Log analysis"), "adli": T("Adli bilişim", "Forensics"),
}
ZORLUK_AD = {"kolay": T("Kolay", "Easy"), "orta": T("Orta", "Medium"), "zor": T("Zor", "Hard")}
DURUM_AD = {"hazir": T("Hazır", "Ready"), "surec": T("Sürüyor", "Running"), "bitti": T("Bitti", "Finished")}
DURUM_RENK = {"hazir": "gri", "surec": "yesil", "bitti": "sari"}

HATA_AD = {
    "baglanti": T("Öğretmen sunucusuna ulaşılamıyor.", "Cannot reach the teacher's server."),
    "bireysel": T("CTF yalnızca sınıf modunda vardır.", "CTF is only available in class mode."),
    "bilinmeyen_gorev": T("Bu görev açık değil.", "This challenge is not open."),
    "baslamadi": T("Yarışma henüz başlamadı.", "The contest has not started yet."),
    "surec_degil": T("Yarışma şu anda sürmüyor.", "The contest is not running right now."),
    "once_oncekini_ac": T("İpuçları sırayla açılır: önce öncekini aç.", "Hints open in order: open the previous one first."),
    "zaten_cozuldu": T("Bu görevi zaten çözdün.", "You already solved this challenge."),
    "gecersiz_ipucu": T("Geçersiz ipucu.", "Invalid hint."),
}


def ctf_css(p: dict) -> str:
    """CTF'ye ozel CSS (ortak tema TreeView/Notebook/ListBox'a dokunmaz; yalniz ctf-* siniflari). p: tema paleti."""
    def a(h, alfa):
        h = h.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return "rgba(%d,%d,%d,%s)" % (r, g, b, alfa)
    return f"""
checkbutton.ctf-secim check {{ border-radius: 999px; -gtk-icon-source: none; }}
checkbutton.ctf-secim check:checked {{ background-color: #15210a; border: 4px solid {p['vurgu']};
    min-width: 8px; min-height: 8px; }}
notebook.ctf-sekme {{ background-color: transparent; border: none; }}
notebook.ctf-sekme > header {{ background-color: transparent; border: none; border-bottom: 1px solid {p['cizgi']}; }}
notebook.ctf-sekme > header tab {{ background-color: transparent; border: none; border-bottom: 2px solid transparent;
    padding: 6px 16px; color: {p['soluk']}; }}
notebook.ctf-sekme > header tab:checked {{ color: {p['yazi']}; border-bottom: 2px solid {p['vurgu']}; }}
notebook.ctf-sekme > stack {{ background-color: transparent; }}
list.ctf-liste, list.ctf-liste row {{ background-color: transparent; border: none; outline: none; }}
list.ctf-liste row {{ border-radius: 6px; padding: 4px 8px; }}
list.ctf-liste row:hover {{ background-color: {a(p['kart2'], 0.7)}; }}
list.ctf-liste row:selected {{ background-color: {a(p['vurgu'], 0.22)}; }}
treeview.ctf-agac {{ background-color: {p['kart']}; color: {p['yazi']}; border: none; }}
treeview.ctf-agac:selected {{ background-color: {a(p['vurgu'], 0.22)}; color: {p['yazi']}; }}
treeview.ctf-agac header button {{ background-color: {p['kart2']}; background-image: none; color: {p['soluk']};
    border: none; border-bottom: 1px solid {p['cizgi']}; border-radius: 0; box-shadow: none; font-weight: bold;
    padding: 6px 10px; }}
"""


def sure_metni(sn) -> str:
    """Kalan sure: 1:05:09 ya da 04:30."""
    sn = max(0, int(sn or 0))
    s, d, k = sn // 3600, (sn % 3600) // 60, sn % 60
    return "%d:%02d:%02d" % (s, d, k) if s else "%02d:%02d" % (d, k)


def sonuc_metni(sonuc: dict, dil: str) -> tuple[str, str]:
    """Sunucu yanitindan (kisa mesaj, renk) -- renk: yesil | kirmizi | sari | gri."""
    if "hata" in sonuc:
        return _dil.sec(HATA_AD.get(sonuc["hata"], T("Bir sorun oluştu.", "Something went wrong.")), dil), "kirmizi"
    s = sonuc.get("sonuc")
    if s == "dogru":
        ek = ""
        if sonuc.get("bonus"):
            ek = " " + _dil.T(T("(+{b} ilk çözüm bonusu)", "(+{b} first-solve bonus)"), dil, b=sonuc["bonus"])
        return _dil.T(T("Doğru! +{p} puan.", "Correct! +{p} points."), dil, p=sonuc.get("puan", 0)) + ek, "yesil"
    if s == "yanlis":
        return _dil.sec(T("Yanlış bayrak. Bir daha dene.", "Wrong flag. Try again."), dil), "kirmizi"
    if s == "bekle":
        return _dil.T(T("Çok fazla yanlış deneme. {n} saniye bekle.", "Too many wrong tries. Wait {n} seconds."),
                      dil, n=sonuc.get("bekleme_sn", 30)), "sari"
    if s == "zaten":
        return _dil.sec(T("Bu görevi zaten çözdün.", "You already solved this challenge."), dil), "gri"
    if s == "baslamadi":
        return _dil.sec(HATA_AD["baslamadi"], dil), "sari"
    if s == "bitti":
        return _dil.sec(T("Yarışma bitti.", "The contest is over."), dil), "sari"
    return _dil.sec(T("Bir sorun oluştu.", "Something went wrong."), dil), "kirmizi"


def gorevleri_grupla(gorevler: list[dict]) -> list[tuple[str, list[dict]]]:
    """Kategoriye gore gruplar; grup ici zorluk, sonra kimlik sirasinda."""
    gruplar: dict[str, list] = {}
    for g in gorevler:
        gruplar.setdefault(g.get("kategori", ""), []).append(g)
    sira = list(KATEGORI_SIRASI) + sorted(k for k in gruplar if k not in KATEGORI_SIRASI)
    return [(k, sorted(gruplar[k], key=lambda g: (ZORLUK_SIRASI.get(g.get("zorluk"), 9), g.get("id", ""))))
            for k in sira if k in gruplar]


def kendi_satirim(skor: dict, ad: str):
    for s in skor.get("satirlar", []):
        if s.get("ad") == ad:
            return s
    return None


def guvenli_dosya_adi(ad: str) -> str:
    """Sunucudan gelen dosya adini kayit klasorunde guvenle kullan (yol parcasi yok)."""
    temiz = os.path.basename(str(ad).replace("\\", "/"))
    temiz = "".join(c for c in temiz if c.isalnum() or c in "._-")
    return temiz.lstrip(".") or "gorev.txt"


def kayit_yolu(ad: str, taban: str | None = None) -> str:
    taban = taban or os.path.join(os.path.expanduser("~"), KAYIT_KLASORU)
    return os.path.join(taban, guvenli_dosya_adi(ad))


# ===========================================================================================================
# GTK katmani (ekran gerektirir)
# ===========================================================================================================
def pencere_olustur(ctf, dil: str, ogrenci: str, gorunum: str = "dark", kayit_taban: str | None = None):
    """GTK iceri aktarilir (bu islev cagrilmadikca mantik fonksiyonlari GTK'siz kullanilabilir)."""
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk, Pango
    import tema

    class CtfPencere(Gtk.Window):
        def __init__(self):
            super().__init__(title="CarotOS Poligon · CTF")
            self.ctf, self.dil, self.ogrenci, self.kayit_taban = ctf, dil, ogrenci, kayit_taban
            self.gorevler: list[dict] = []
            self.secili: str | None = None
            self.durum = {}
            self._yenileniyor = False
            self._yeniden_ciziliyor = False
            self._kapali = False
            self.set_default_size(920, 620)
            self._palet = tema.uygula(gorunum, "guvenlik")
            self._css = Gtk.CssProvider()
            self._css.load_from_data(ctf_css(self._palet).encode())
            Gtk.StyleContext.add_provider_for_screen(self.get_screen(), self._css,
                                                     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2)

            kok = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            kok.set_margin_top(12); kok.set_margin_bottom(12); kok.set_margin_start(14); kok.set_margin_end(14)
            self.add(kok)

            ust = Gtk.Box(spacing=12)
            self.baslik = Gtk.Label(xalign=0)
            tema.sinif(self.baslik, "marka")
            ust.pack_start(self.baslik, False, False, 0)
            self.durum_rozeti = tema.rozet("", "gri")
            ust.pack_start(self.durum_rozeti, False, False, 0)
            self.sure_etiketi = Gtk.Label(xalign=0)
            ust.pack_start(self.sure_etiketi, False, False, 0)
            self.puan_etiketi = Gtk.Label(xalign=1)
            ust.pack_end(self.puan_etiketi, False, False, 0)
            kok.pack_start(ust, False, False, 0)

            self.not_etiketi = Gtk.Label(xalign=0, wrap=True)
            tema.sinif(self.not_etiketi, "soluk")
            kok.pack_start(self.not_etiketi, False, False, 0)

            self.sekmeler = Gtk.Notebook()
            tema.sinif(self.sekmeler, "ctf-sekme")
            kok.pack_start(self.sekmeler, True, True, 0)
            self._gorev_sekmesi()
            self._skor_sekmesi()
            self._metinleri_uygula()
            self.connect("destroy", self._kapat)
            GLib.timeout_add_seconds(YENILEME_SN, self._zamanlayici)
            self._yenile_baslat()

        # -- yardimcilar --------------------------------------------------------------------------------
        def t(self, m, **kw):
            return _dil.T(m, self.dil, **kw) if kw else _dil.sec(m, self.dil)

        def _kapat(self, *_):
            self._kapali = True

        # -- sekmeler -------------------------------------------------------------------------------------
        def _gorev_sekmesi(self):
            kutu = Gtk.Box(spacing=12)
            self.liste = Gtk.ListBox()
            tema.sinif(self.liste, "ctf-liste")
            self.liste.set_selection_mode(Gtk.SelectionMode.SINGLE)
            self.liste.connect("row-selected", self._satir_secildi)
            kay = Gtk.ScrolledWindow()
            kay.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            kay.set_size_request(280, -1)
            kay.add(self.liste)
            kutu.pack_start(kay, False, False, 0)

            sag = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            self.g_baslik = Gtk.Label(xalign=0, wrap=True)
            tema.sinif(self.g_baslik, "marka")
            self.g_alt = Gtk.Label(xalign=0)
            tema.sinif(self.g_alt, "soluk")
            self.g_aciklama = Gtk.Label(xalign=0, wrap=True, selectable=True)
            sag.pack_start(self.g_baslik, False, False, 0)
            sag.pack_start(self.g_alt, False, False, 0)
            sag.pack_start(self.g_aciklama, False, False, 0)

            self.dosya_gorunumu = Gtk.TextView()
            self.dosya_gorunumu.set_editable(False)
            self.dosya_gorunumu.set_monospace(True)
            self.dosya_gorunumu.set_wrap_mode(Gtk.WrapMode.CHAR)
            kay2 = Gtk.ScrolledWindow()
            kay2.set_shadow_type(Gtk.ShadowType.IN)
            kay2.add(self.dosya_gorunumu)
            sag.pack_start(kay2, True, True, 0)

            dosya_satiri = Gtk.Box(spacing=8)
            self.kaydet_dugmesi = Gtk.Button()
            self.kaydet_dugmesi.connect("clicked", self._dosyayi_kaydet)
            self.kayit_etiketi = Gtk.Label(xalign=0, wrap=True, selectable=True)
            tema.sinif(self.kayit_etiketi, "soluk")
            dosya_satiri.pack_start(self.kaydet_dugmesi, False, False, 0)
            dosya_satiri.pack_start(self.kayit_etiketi, True, True, 0)
            sag.pack_start(dosya_satiri, False, False, 0)

            self.ipucu_kutusu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            sag.pack_start(self.ipucu_kutusu, False, False, 0)
            self.ipucu_dugmesi = Gtk.Button()
            self.ipucu_dugmesi.connect("clicked", self._ipucu_ac)
            sag.pack_start(self.ipucu_dugmesi, False, False, 0)

            gonder = Gtk.Box(spacing=8)
            self.bayrak_girisi = Gtk.Entry()
            self.bayrak_girisi.set_max_length(200)
            self.bayrak_girisi.connect("activate", self._bayrak_gonder)
            self.gonder_dugmesi = Gtk.Button()
            tema.sinif(self.gonder_dugmesi, "ana")
            self.gonder_dugmesi.connect("clicked", self._bayrak_gonder)
            gonder.pack_start(self.bayrak_girisi, True, True, 0)
            gonder.pack_start(self.gonder_dugmesi, False, False, 0)
            sag.pack_start(gonder, False, False, 0)
            self.sonuc_etiketi = Gtk.Label(xalign=0, wrap=True)
            sag.pack_start(self.sonuc_etiketi, False, False, 0)

            kutu.pack_start(sag, True, True, 0)
            self.gorev_sekme_etiketi = Gtk.Label()
            self.sekmeler.append_page(kutu, self.gorev_sekme_etiketi)

        def _skor_sekmesi(self):
            self.skor_modeli = Gtk.ListStore(int, str, int, int, int)      # son sutun: yazi agirligi (kendi satirim kalin)
            self.skor_agaci = Gtk.TreeView(model=self.skor_modeli)
            tema.sinif(self.skor_agaci, "ctf-agac")
            self.skor_sutunlari = []
            for i in range(4):
                sutun = Gtk.TreeViewColumn("", Gtk.CellRendererText(), text=i, weight=4)
                self.skor_agaci.append_column(sutun)
                self.skor_sutunlari.append(sutun)
            kay = Gtk.ScrolledWindow()
            kay.add(self.skor_agaci)
            kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            self.skor_not = Gtk.Label(xalign=0, wrap=True)
            tema.sinif(self.skor_not, "soluk")
            kutu.pack_start(self.skor_not, False, False, 0)
            kutu.pack_start(kay, True, True, 0)
            self.skor_sekme_etiketi = Gtk.Label()
            self.sekmeler.append_page(kutu, self.skor_sekme_etiketi)

        # -- metinler -------------------------------------------------------------------------------------------
        def _metinleri_uygula(self):
            self.baslik.set_text("CTF")
            self.gorev_sekme_etiketi.set_text(self.t(T("Görevler", "Challenges")))
            self.skor_sekme_etiketi.set_text(self.t(T("Skor tablosu", "Scoreboard")))
            for sutun, m in zip(self.skor_sutunlari, (T("Sıra", "Rank"), T("Öğrenci", "Student"), T("Puan", "Points"),
                                                       T("Çözülen", "Solved"))):
                sutun.set_title(self.t(m))
            self.kaydet_dugmesi.set_label(self.t(T("Dosyayı kaydet", "Save file")))
            self.gonder_dugmesi.set_label(self.t(T("Gönder", "Submit")))
            self.bayrak_girisi.set_placeholder_text("CAROT{...}")
            self._ayrinti_yaz()

        # -- yenileme (agi arka planda cagir, arayuzu ana is parcaciginda guncelle) ------------------------------
        def _zamanlayici(self):
            if self._kapali:
                return False
            self._yenile_baslat()
            return True

        def _yenile_baslat(self):
            if self._yenileniyor:
                return
            self._yenileniyor = True

            def is_():
                d, s = self.ctf.durum(), self.ctf.skor()
                GLib.idle_add(self._yenile_bitti, d, s)
            threading.Thread(target=is_, daemon=True).start()

        def _yenile_bitti(self, d, s):
            self._yenileniyor = False
            if self._kapali:
                return False
            self.uygula_durum(d, s)
            return False

        def uygula_durum(self, d: dict, s: dict):
            """Sunucu yanitlarini arayuze yazar (testlerde dogrudan cagrilir)."""
            if "hata" in d:
                self.not_etiketi.set_text(sonuc_metni(d, self.dil)[0])
                return
            self.not_etiketi.set_text("")
            self.durum = d
            kod = d.get("durum", "hazir")
            tema.rozet_ayarla(self.durum_rozeti, self.t(DURUM_AD.get(kod, DURUM_AD["hazir"])), DURUM_RENK.get(kod, "gri"))
            self.sure_etiketi.set_text(self.t(T("Kalan: {s}", "Remaining: {s}"), s=sure_metni(d.get("kalan_sn", 0)))
                                       if kod == "surec" else "")
            benim = kendi_satirim(s, self.ogrenci) if "hata" not in s else None
            self.puan_etiketi.set_text(self.t(T("Puanın: {p} · Sıran: {r}", "Your score: {p} · Rank: {r}"),
                                              p=benim["puan"], r=benim["sira"]) if benim else
                                       self.t(T("Puanın: 0", "Your score: 0")))
            self._gorevleri_yaz(d.get("gorevler", []))
            self._skoru_yaz(s)

        def _gorevleri_yaz(self, gorevler):
            if gorevler == self.gorevler:
                return
            self.gorevler = gorevler
            onceki = self.secili
            self._yeniden_ciziliyor = True
            for c in self.liste.get_children():
                self.liste.remove(c)
            self._satirlar = {}
            if not gorevler:
                satir = Gtk.ListBoxRow()
                satir.set_selectable(False)
                satir.add(Gtk.Label(label=self.t(T("Yarışma başlayınca görevler burada görünür.",
                                                    "Challenges appear here once the contest starts.")),
                                    xalign=0, wrap=True))
                self.liste.add(satir)
            for kategori, grup in gorevleri_grupla(gorevler):
                baslik = Gtk.ListBoxRow()
                baslik.set_selectable(False)
                et = Gtk.Label(xalign=0)
                et.set_markup("<b>%s</b>" % GLib.markup_escape_text(self.t(KATEGORI_AD.get(kategori, T(kategori, kategori)))))
                baslik.add(et)
                self.liste.add(baslik)
                for g in grup:
                    satir = Gtk.ListBoxRow()
                    satir.gorev_id = g["id"]
                    kutu = Gtk.Box(spacing=8)
                    isaret = "✓" if g["cozuldu"] else "○"
                    kutu.pack_start(Gtk.Label(label=isaret), False, False, 0)
                    kutu.pack_start(Gtk.Label(label=self.t(g["baslik"]), xalign=0, ellipsize=Pango.EllipsizeMode.END),
                                    True, True, 0)
                    kutu.pack_end(Gtk.Label(label=str(g["puan"])), False, False, 0)
                    satir.add(kutu)
                    self.liste.add(satir)
                    self._satirlar[g["id"]] = satir
            self.liste.show_all()
            if onceki in self._satirlar:
                self.liste.select_row(self._satirlar[onceki])
            else:
                self.secili = None
            self._yeniden_ciziliyor = False
            self._ayrinti_yaz()

        def _skoru_yaz(self, s):
            self.skor_modeli.clear()
            if "hata" in s:
                return
            for r in s.get("satirlar", []):
                self.skor_modeli.append([r["sira"], r["ad"], r["puan"], r["cozulen"],
                                         700 if r["ad"] == self.ogrenci else 400])
            self.skor_not.set_text(self.t(T("Skor tablosu donduruldu: son dakikalardaki gelişmeler gizli.",
                                            "The scoreboard is frozen: the latest changes are hidden."))
                                   if s.get("donuk") else "")

        # -- gorev ayrintisi ----------------------------------------------------------------------------------------
        def _gorev(self):
            return next((g for g in self.gorevler if g["id"] == self.secili), None)

        def _satir_secildi(self, _liste, satir):
            if self._yeniden_ciziliyor:                  # liste tazelenirken secim olayi gurultusu
                return
            yeni = getattr(satir, "gorev_id", None) if satir is not None else None
            degisti = yeni != self.secili
            self.secili = yeni
            if degisti:                                   # ayni goreve donus mesaji/dosyayi sifirlamaz
                self.sonuc_etiketi.set_text("")
                self.kayit_etiketi.set_text("")
                self._dosya_yukle()
            self._ayrinti_yaz()

        def _ayrinti_yaz(self):
            g = self._gorev()
            var = g is not None
            for w in (self.kaydet_dugmesi, self.ipucu_dugmesi, self.bayrak_girisi, self.gonder_dugmesi):
                w.set_sensitive(var)
            if not var:
                self.g_baslik.set_text(self.t(T("Bir görev seç", "Pick a challenge")))
                self.g_alt.set_text("")
                self.g_aciklama.set_text("")
                self.dosya_gorunumu.get_buffer().set_text("")
                for c in self.ipucu_kutusu.get_children():
                    self.ipucu_kutusu.remove(c)
                self.ipucu_dugmesi.set_label("")
                return
            self.g_baslik.set_text(self.t(g["baslik"]))
            self.g_alt.set_text("%s · %s · %s" % (
                self.t(KATEGORI_AD.get(g["kategori"], T(g["kategori"], g["kategori"]))),
                self.t(ZORLUK_AD.get(g["zorluk"], T(g["zorluk"], g["zorluk"]))),
                self.t(T("{p} puan · {n} çözen", "{p} points · {n} solved"), p=g["puan"], n=g["cozen"])))
            self.g_aciklama.set_text(self.t(g["aciklama"]))
            cozuldu = g["cozuldu"]
            self.bayrak_girisi.set_sensitive(not cozuldu)
            self.gonder_dugmesi.set_sensitive(not cozuldu)
            kalan = g["ipucu_sayisi"] - g["ipucu_acilan"]
            if cozuldu or kalan <= 0:
                self.ipucu_dugmesi.set_visible(False)
            else:
                ceza = g["ipucu_cezalari"][g["ipucu_acilan"]]
                self.ipucu_dugmesi.set_visible(True)
                self.ipucu_dugmesi.set_label(self.t(T("İpucu aç (−{c} puan)", "Open a hint (−{c} points)"), c=ceza))

        def _dosya_yukle(self):
            g = self._gorev()
            tampon = self.dosya_gorunumu.get_buffer()
            for c in self.ipucu_kutusu.get_children():
                self.ipucu_kutusu.remove(c)
            if g is None:
                tampon.set_text("")
                return
            gid = g["id"]
            tampon.set_text(self.t(T("Yükleniyor…", "Loading…")))

            def is_():
                GLib.idle_add(self._dosya_geldi, gid, self.ctf.dosya(gid))
            threading.Thread(target=is_, daemon=True).start()

        def _dosya_geldi(self, gid, yanit):
            if self._kapali or gid != self.secili:
                return False
            tampon = self.dosya_gorunumu.get_buffer()
            if "hata" in yanit:
                tampon.set_text(sonuc_metni(yanit, self.dil)[0])
                return False
            self._dosya_adi = yanit["ad"]
            tampon.set_text(yanit["icerik"])
            for ip in yanit.get("ipuclari", []):
                self._ipucu_ekle(ip)
            return False

        def _ipucu_ekle(self, ip):
            et = Gtk.Label(xalign=0, wrap=True, selectable=True)
            et.set_markup("<b>%s</b> %s" % (GLib.markup_escape_text(self.t(T("İpucu:", "Hint:"))),
                                           GLib.markup_escape_text(_dil.sec(ip, self.dil))))
            et.show()
            self.ipucu_kutusu.pack_start(et, False, False, 0)

        def _dosyayi_kaydet(self, _d):
            g = self._gorev()
            if g is None or not getattr(self, "_dosya_adi", None):
                return
            tampon = self.dosya_gorunumu.get_buffer()
            icerik = tampon.get_text(tampon.get_start_iter(), tampon.get_end_iter(), False)
            yol = kayit_yolu("%s-%s" % (g["id"], self._dosya_adi), self.kayit_taban)
            try:
                os.makedirs(os.path.dirname(yol), exist_ok=True)
                with open(yol, "w", encoding="utf-8", newline="\n") as f:
                    f.write(icerik)
            except OSError:
                self.kayit_etiketi.set_text(self.t(T("Dosya kaydedilemedi.", "Could not save the file.")))
                return
            self.kayit_etiketi.set_text(self.t(T("Kaydedildi: {y}", "Saved: {y}"), y=yol))

        def _ipucu_ac(self, _d):
            g = self._gorev()
            if g is None:
                return
            no, ceza = g["ipucu_acilan"], g["ipucu_cezalari"][g["ipucu_acilan"]]
            if ceza > 0 and not self._onayla(self.t(T("Bu ipucu çözümde puanından {c} düşer. Açılsın mı?",
                                                        "This hint costs {c} points when you solve it. Open it?"), c=ceza)):
                return
            gid = g["id"]

            def is_():
                GLib.idle_add(self._ipucu_geldi, gid, self.ctf.ipucu_al(gid, no))
            threading.Thread(target=is_, daemon=True).start()

        def _ipucu_geldi(self, gid, yanit):
            if self._kapali:
                return False
            if "hata" in yanit:
                self.sonuc_etiketi.set_text(sonuc_metni(yanit, self.dil)[0])
            elif gid == self.secili:
                self._ipucu_ekle(yanit)
                self._yenile_baslat()
            return False

        def _onayla(self, metin) -> bool:
            d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                  buttons=Gtk.ButtonsType.YES_NO, text=metin)
            try:
                return d.run() == Gtk.ResponseType.YES
            finally:
                d.destroy()

        def _bayrak_gonder(self, _w):
            g = self._gorev()
            bayrak = self.bayrak_girisi.get_text().strip()
            if g is None or not bayrak:
                return
            gid = g["id"]
            self.gonder_dugmesi.set_sensitive(False)

            def is_():
                GLib.idle_add(self._sonuc_geldi, gid, self.ctf.bayrak_gonder(gid, bayrak))
            threading.Thread(target=is_, daemon=True).start()

        def _sonuc_geldi(self, gid, yanit):
            if self._kapali:
                return False
            metin, renk = sonuc_metni(yanit, self.dil)
            self.sonuc_etiketi.set_text(metin)
            ctx = self.sonuc_etiketi.get_style_context()
            for eski in ("basari", "hata", "uyari", "soluk"):
                ctx.remove_class(eski)
            tema.sinif(self.sonuc_etiketi, {"yesil": "basari", "kirmizi": "hata", "sari": "uyari"}.get(renk, "soluk"))
            if yanit.get("sonuc") == "dogru":
                self.bayrak_girisi.set_text("")
                self._yenile_baslat()
            self.gonder_dugmesi.set_sensitive(True)
            return False

    return CtfPencere()
