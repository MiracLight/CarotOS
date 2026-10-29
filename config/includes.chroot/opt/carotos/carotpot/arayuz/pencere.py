# -*- coding: utf-8 -*-
"""CarotPot ana penceresi: ortak tema kabugu, ortak durum, yetkili islemler.

Sayfalar durumu bu nesneden okur (p.ozet24, p.akis.olaylar, p.engeller...)
ve degisiklikleri p.yetkili(...) ile ister. Durum 3 saniyede bir tazelenir;
bir sey degistiyse yalnizca gorunen sayfa guncellenir."""

import json
import os
import subprocess
import threading
import time
from datetime import datetime

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

import tema  # noqa: E402
from bekleme_cubugu import SweepBar  # noqa: E402

import ag  # noqa: E402
import carotpot as CP  # noqa: E402
import kanarya  # noqa: E402
from arayuz import veri as V  # noqa: E402
from arayuz.metinler import M, TUR  # noqa: E402
from arayuz.sayfalar import SAYFALAR  # noqa: E402

BOLUMLER = [
    ("izleme", [("pano", "pano"), ("saldirgan", "kisi"), ("tuzak", "altigen"),
                ("kanarya", "elmas"), ("engel", "yasak"), ("rapor", "rapor"), ("ag", "ag")]),
    ("sistem", [("ayar", "ayar")]),
]


def ayar_dosyasi():
    return os.path.join(GLib.get_user_config_dir(), "carotpot", "settings.json")


def dil_varsayilan():
    for d in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(d, "").strip()
        if v and v not in ("C", "POSIX"):
            return "tr" if v.lower().startswith("tr") else "en"
    return "en"


def arayuz_ayarlari():
    veri = {"lang": dil_varsayilan(), "theme": "dark"}
    kayitli = V.json_oku(ayar_dosyasi(), {})
    if isinstance(kayitli, dict):
        if kayitli.get("lang") in ("tr", "en"):
            veri["lang"] = kayitli["lang"]
        if kayitli.get("theme") in ("dark", "light"):
            veri["theme"] = kayitli["theme"]
    return veri


def arayuz_ayarlarini_kaydet(veri):
    try:
        os.makedirs(os.path.dirname(ayar_dosyasi()), exist_ok=True)
        with open(ayar_dosyasi(), "w", encoding="utf-8") as fh:
            json.dump(veri, fh)
    except OSError:
        pass


class Pencere(Gtk.Window):
    def __init__(self, logo=None):
        super().__init__(title="CarotPot")
        self.ui = arayuz_ayarlari()
        self.lang = self.ui["lang"]
        tema.uygula(self.ui["theme"], "carotpot")
        self.set_default_size(1280, 820)
        self.set_size_request(1040, 640)
        self.set_position(Gtk.WindowPosition.CENTER)
        try:
            if logo:
                self.set_icon_from_file(logo)
            else:
                self.set_icon_name("carotpot")
        except GLib.Error:
            pass
        self.connect("destroy", lambda *_: Gtk.main_quit())

        self.akis = V.OlayAkisi()
        self.cihaz = {}            # ip -> {"mac", "uretici", "ad"}
        self._cihaz_istek = set()
        self.mesgul = None
        self._bar_id = 0
        self._bar_sayac = 0
        self.imza = None
        self.aktif = None
        self.bildirici = True
        self._bildirici_zaman = 0

        self.kabuk = tema.Kabuk(logo, BOLUMLER, self.sayfa_secildi)
        self.add(self.kabuk)
        self.bar = SweepBar(tema.AKTIF["vurgu"])
        self.hap = tema.DurumHapi()
        self.ana_dugme = tema.dugme("", "ana", self.ana_dugme_tik)
        self.kabuk.ust_sag.pack_start(self.bar, False, False, 0)
        self.kabuk.ust_sag.pack_start(self.hap, False, False, 0)
        self.kabuk.ust_sag.pack_start(self.ana_dugme, False, False, 0)

        alt = Gtk.Box(spacing=8)
        self.dil_kutu = Gtk.ComboBoxText()
        self.dil_kutu.append("tr", "Türkçe")
        self.dil_kutu.append("en", "English")
        self.dil_kutu.set_active_id(self.lang)
        self.dil_kutu.connect("changed", self.dil_degisti)
        alt.pack_start(self.dil_kutu, True, True, 0)
        self.tema_dugme = tema.dugme("", None, self.tema_degistir)
        alt.pack_start(self.tema_dugme, False, False, 0)
        self.kabuk.yan_alt.pack_start(alt, False, False, 0)
        self.alt_bilgi = tema.etiket("", "marka-alt")
        self.kabuk.yan_alt.pack_start(self.alt_bilgi, False, False, 0)

        self.sayfalar = {cls.ANAHTAR: cls(self) for cls in SAYFALAR}
        self.durum_tazele(zorla=True)
        self.metinleri_uygula()
        self.show_all()
        self.bar.hide()
        self.kabuk.sec("pano")
        GLib.timeout_add_seconds(3, self.tik)

    # -- metin ve bicim yardimcilari ---------------------------------------------
    def t(self, _anahtar, **kw):
        m = M[_anahtar][self.lang]
        return m.format(**kw) if kw else m

    def saat(self, ts):
        d = datetime.fromtimestamp(ts)
        return d.strftime("%H:%M") if d.date() == datetime.now().date() else d.strftime("%d.%m %H:%M")

    def saat_sn(self, ts):
        d = datetime.fromtimestamp(ts)
        return d.strftime("%H:%M:%S") if d.date() == datetime.now().date() else d.strftime("%d.%m %H:%M")

    def once(self, ts):
        fark = max(0, time.time() - ts)
        if fark < 60:
            return self.t("az_once")
        if fark < 3600:
            return self.t("dk_once", n=int(fark // 60))
        if fark < 86400:
            return self.t("sa_once", n=int(fark // 3600))
        return self.t("gun_once", n=int(fark // 86400))

    def sure(self, saniye):
        saniye = max(0, int(saniye))
        if saniye < 3600:
            return self.t("sure_dk", dk=max(1, saniye // 60))
        if saniye < 86400:
            return self.t("sure_sa", sa=saniye // 3600, dk=(saniye % 3600) // 60)
        return self.t("sure_gun", gun=saniye // 86400, sa=(saniye % 86400) // 3600)

    def seviye_metni(self, puan):
        anahtar, renk = V.seviye(puan)
        return self.t(f"seviye_{anahtar}"), renk

    def olay_metni(self, o):
        return CP.olay_aciklamasi(o, self.lang)

    def akis_metni(self, o):
        """Kisa olay satiri: tur · ayrinti (kullanici/parola, yol, komut)."""
        tur = o.get("tur")
        metin = self.t(TUR.get(tur, "tur_baglanti"))
        if tur == "giris" and (o.get("kullanici") or o.get("parola")):
            metin += f" · {o.get('kullanici') or '?'} / {o.get('parola') or '—'}"
        elif tur in ("istek", "komut") and o.get("ayrinti"):
            metin += " · " + str(o["ayrinti"]).split(" UA=")[0][:60]
        elif tur == "baglanti" and o.get("kullanici"):
            metin += f" · {o['kullanici']}"
        return metin

    def cihaz_adi(self, ip):
        c = self.cihaz.get(ip) or {}
        if c.get("ad"):
            return c["ad"]
        u = c.get("uretici")
        if u == "rastgele":
            return self.t("rastgele_mac")
        return u or ""

    # -- durum --------------------------------------------------------------------
    def durum_tazele(self, zorla=False):
        degisti = self.akis.tazele()
        self.ayar = CP.ayar_oku()
        self.hizmet = V.hizmet_acik_mi()
        self.hdurum = V.hizmet_durumu() if self.hizmet else {}
        self.engeller = V.engeller()
        self.otomatik = V.otomatik_acik_mi()
        self.ufw = V.ufw_durumu()
        self.kanaryalar = kanarya.durumlar()
        if time.time() - self._bildirici_zaman > 15 or zorla:
            self._bildirici_zaman = time.time()
            self.bildirici = self._bildirici_calisiyor()
        imza = (self.akis.surum, self.hizmet, self.hdurum.get("baslangic"),
                json.dumps(self.engeller), self.otomatik, self.ufw,
                json.dumps(self.ayar, sort_keys=True),
                json.dumps(self.kanaryalar, sort_keys=True, default=str), self.bildirici)
        if not degisti and imza == self.imza and not zorla:
            return False
        self.imza = imza
        simdi = time.time()
        self.ozet24 = V.kaynak_ozeti(self.akis.olaylar, simdi, 86400)
        self.engelli = {e["ip"] for e in self.engeller}
        for k in self.ozet24[:40]:
            self.cihaz_bilgisi_iste(k["kaynak"])
        return True

    @staticmethod
    def _bildirici_calisiyor():
        try:
            return bool(subprocess.run(
                ["pgrep", "-u", str(os.getuid()), "-f", "carotpot.py bildir"],
                capture_output=True, timeout=5).stdout.strip())
        except (OSError, subprocess.TimeoutExpired):
            return True

    def tik(self):
        try:
            if self.durum_tazele():
                self.ust_guncelle()
                if self.aktif:
                    self.sayfalar[self.aktif].guncelle()
            else:
                self.ust_guncelle()
        except Exception as hata:  # noqa: BLE001 -- zamanlayici durmasin
            import traceback
            traceback.print_exc()
            print("tazeleme hatasi:", hata)
        return True

    def ust_guncelle(self):
        acik = self.hdurum.get("acik", {}) if self.hizmet else {}
        hatalar = [k for k in self.hdurum.get("hatalar", {}) if not k.endswith("_tam")]
        if self.hizmet and hatalar:
            self.hap.ayarla(self.t("hap_hata", n=len(hatalar)), "uyari")
        elif self.hizmet:
            sure = self.sure(time.time() - self.hdurum.get("baslangic", time.time()))
            self.hap.ayarla(self.t("hap_acik", n=len(acik), sure=sure), "acik")
        else:
            self.hap.ayarla(self.t("hap_kapali"), "kapali")
        self.ana_dugme.set_label(self.t("durdur") if self.hizmet else self.t("baslat"))
        ctx = self.ana_dugme.get_style_context()
        ctx.remove_class("ana" if self.hizmet else "tehlike")
        ctx.add_class("tehlike" if self.hizmet else "ana")
        self.ana_dugme.set_sensitive(self.mesgul is None)
        # menu rozetleri
        n = len(self.ozet24)
        yuksek = any(k["risk"] >= 60 for k in self.ozet24)
        self.kabuk.rozet("saldirgan", n if n else None, sakin=not yuksek)
        tetik = sum(1 for k in self.kanaryalar
                    if k["tetik"] and time.time() - k["tetik"]["ts"] < 86400)
        self.kabuk.rozet("kanarya", tetik or None)
        self.kabuk.rozet("engel", len(self.engeller) or None, sakin=True)

    # -- gezinme ------------------------------------------------------------------
    def sayfa_secildi(self, anahtar):
        self.aktif = anahtar
        s = self.sayfalar[anahtar]
        if s.kok is None:
            s.kok = s.kur()
        self.kabuk.baslik_ayarla(*s.baslik())
        self.kabuk.icerik(s.kok)
        s.guncelle()

    def gezin(self, anahtar, **kw):
        self.sayfalar[anahtar].hazirla(**kw)
        if self.aktif == anahtar:
            self.sayfalar[anahtar].guncelle()
        else:
            self.kabuk.sec(anahtar)

    def metinleri_uygula(self):
        self.kabuk.marka_ayarla("CarotPot", self.t("marka_alt", surum=CP.SURUM))
        for bolum, sayfalar in BOLUMLER:
            self.kabuk.bolum_metni(bolum, self.t(f"bolum_{bolum}"))
            for anahtar, _ in sayfalar:
                self.kabuk.menu_metni(anahtar, self.t(anahtar))
        self.alt_bilgi.set_text(self.t("alt_bilgi", surum=CP.SURUM))
        koyu = self.ui["theme"] == "dark"
        self.tema_dugme.set_label("☀" if koyu else "☾")
        self.tema_dugme.set_tooltip_text(self.t("tema") + ": " + (
            self.t("gorunum_acik") if koyu else self.t("gorunum_koyu")))
        self.ust_guncelle()

    def dil_degisti(self, kutu):
        yeni = kutu.get_active_id()
        if yeni not in ("tr", "en") or yeni == self.lang:
            return
        self.lang = self.ui["lang"] = yeni
        arayuz_ayarlarini_kaydet(self.ui)
        self.yeniden_kur()

    def tema_degistir(self, gorunum=None):
        self.ui["theme"] = gorunum or ("light" if self.ui["theme"] == "dark" else "dark")
        arayuz_ayarlarini_kaydet(self.ui)
        tema.uygula(self.ui["theme"], "carotpot")
        self.yeniden_kur()

    def yeniden_kur(self):
        self.metinleri_uygula()
        for s in self.sayfalar.values():
            s.kok = None
        if self.dil_kutu.get_active_id() != self.lang:
            self.dil_kutu.set_active_id(self.lang)
        if self.aktif:
            self.sayfa_secildi(self.aktif)
        self.queue_draw()

    # -- bildirim ve mesgul --------------------------------------------------------
    def bildir(self, metin, tur="bilgi"):
        self.kabuk.bildir(metin, tur)

    def _mesgul_ayarla(self, ad):
        self.mesgul = ad
        if ad:
            self.bar.show()
            if not self._bar_id:
                self._bar_id = GLib.timeout_add(40, self._bar_adim)
        else:
            self.bar.hide()
            if self._bar_id:
                GLib.source_remove(self._bar_id)
                self._bar_id = 0
        self.ust_guncelle()
        if self.aktif:
            self.sayfalar[self.aktif].mesgul_degisti()

    def _bar_adim(self):
        self._bar_sayac += 1
        self.bar.adim(self._bar_sayac)
        return True

    def arka_plan(self, is_, bitti=None, mesgul=None):
        """is_() ayri is parcaciginda; bitti(sonuc) ana dongude."""
        if mesgul:
            self._mesgul_ayarla(mesgul)

        def calis():
            try:
                sonuc = is_()
            except Exception as hata:  # noqa: BLE001
                sonuc = hata

            def son():
                if mesgul:
                    self._mesgul_ayarla(None)
                if bitti:
                    bitti(sonuc)
                return False
            GLib.idle_add(son)
        threading.Thread(target=calis, daemon=True).start()

    def kod_metni(self, kod, veri):
        anahtar = "k_" + kod
        if anahtar in M:
            try:
                return self.t(anahtar, **{k: v for k, v in veri.items() if k == "ayrinti"})
            except KeyError:
                return self.t(anahtar, ayrinti="")
        return self.t("k_genel")

    def yetkili(self, komut, *arglar, girdi=None, basari=None, sonra=None, mesgul_metni=None):
        """carotpot-yonet'i pkexec ile cagirir (arka planda)."""
        if self.mesgul:
            return
        if mesgul_metni:
            self.bildir(mesgul_metni)

        def bitti(sonuc):
            kod, veri = sonuc if isinstance(sonuc, tuple) else ("__CALISTIRILAMADI__", {})
            if kod == "__TAMAM__":
                if basari:
                    self.bildir(basari, "basari")
            elif kod != "__IPTAL__":
                self.bildir(self.kod_metni(kod, veri), "hata")
            else:
                self.bildir(self.t("k___IPTAL__"))
            self.durum_tazele(zorla=True)
            self.ust_guncelle()
            if sonra:
                sonra(kod, veri)
            if self.aktif:
                self.sayfalar[self.aktif].guncelle()
        self.arka_plan(lambda: V.yardimci_cagir(komut, *arglar, girdi=girdi), bitti, mesgul=komut)

    def ayar_kaydet(self, yeni, basari=None, sonra=None):
        self.yetkili("ayar", girdi=json.dumps(yeni), basari=basari or self.t("ayar_kaydedildi"),
                     sonra=sonra)

    # -- tuzak ac/kapat ------------------------------------------------------------
    def ana_dugme_tik(self):
        if self.hizmet:
            self.yetkili("durdur", basari=self.t("durduruldu"), mesgul_metni=self.t("durduruluyor"))
            return
        if not tema.onay_sor(self, self.t("baslat_onay_baslik"), self.t("baslat_onay"),
                             self.t("baslat"), self.t("iptal")):
            return

        def sonra(kod, _veri):
            if kod == "__TAMAM__":
                V.bildirici_baslat()
                self._bildirici_zaman = 0
        self.yetkili("baslat", basari=self.t("baslatildi"), sonra=sonra,
                     mesgul_metni=self.t("baslatiliyor"))

    # -- cihaz bilgisi (arka planda) ---------------------------------------------
    def cihaz_bilgisi_iste(self, ip, bitti=None):
        if ip in self.cihaz:          # zaten biliniyor: geri cagirma yok
            return
        if ip in self._cihaz_istek:
            return
        self._cihaz_istek.add(ip)

        def is_():
            mac = ag.mac_bul(ip)
            return {"mac": mac, "uretici": ag.uretici(mac) if mac else "", "ad": ag.ad_coz(ip)}

        def son(sonuc):
            self._cihaz_istek.discard(ip)
            if isinstance(sonuc, dict):
                self.cihaz[ip] = sonuc
                if bitti:
                    bitti(sonuc)
        self.arka_plan(is_, son)
