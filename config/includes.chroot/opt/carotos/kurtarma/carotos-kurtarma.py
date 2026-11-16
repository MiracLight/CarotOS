#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CarotOS Kurtarma: "sistemi son kaydedilen kararlı noktaya döndür" uygulaması.

Model Linux Mint'in Timeshift'i ve Windows'un Sistem Geri Yükleme'siyle
aynıdır (rsync + sabit bağ ile artımlı nokta); CarotOS kurucusu dosya
sistemini sabitlemediği için (çoğu zaman ext4) btrfs/LVM anlık görüntüsü
kullanılmaz. Kapsam bilerek dar: /etc, /root ve kurulu paket listesi.
Kişisel dosyalara DOKUNULMAZ -- bu bir yedekleme aracı değildir.

Listeleme ve ayar OKUMA pkexec GEREKTİRMEZ (kurtarma_motor dosyaları dünya
okunabilir izinlerle yazar); yalnızca nokta oluşturma, geri yükleme, silme
ve ayar YAZMA carotos-kurtarma-yonet'e pkexec ile gider.
"""
import json
import os
import subprocess
import sys
import threading

sys.dont_write_bytecode = True

BURASI = os.path.dirname(os.path.abspath(__file__))
ORTAK = os.path.join(os.path.dirname(BURASI), "ortak")
for yol in (ORTAK, BURASI):
    if yol not in sys.path:
        sys.path.insert(0, yol)

import kurtarma_motor as K  # noqa: E402

import gi  # noqa: E402
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

import dil  # noqa: E402
import tema  # noqa: E402

APP_VERSION = "1.0"
VURGU = "kurtarma"
YONET = os.path.join(BURASI, "carotos-kurtarma-yonet")

METIN = {
    "baslik": {"tr": "CarotOS Kurtarma", "en": "CarotOS Recovery"},
    "bolum": {"tr": "Kurtarma", "en": "Recovery"},
    "men_noktalar": {"tr": "Kurtarma noktaları", "en": "Recovery points"},
    "men_ayarlar": {"tr": "Ayarlar", "en": "Settings"},
    "ust_noktalar": {"tr": "Sistemi bu noktaya alabilirsin",
                     "en": "You can bring the system back to one of these"},
    "aciklama": {"tr": "/etc, /root ve kurulu paket listesinin yedeği. Kişisel dosyalarına "
                       "(Belgeler, Masaüstü, tarayıcı…) dokunulmaz.",
                 "en": "A copy of /etc, /root and the installed package list. Your personal "
                       "files (Documents, Desktop, browser…) are left untouched."},
    "olustur": {"tr": "Şimdi nokta oluştur", "en": "Create a point now"},
    "olustur_basligi": {"tr": "Kurtarma noktası oluştur", "en": "Create a recovery point"},
    "etiket_sor": {"tr": "Bu noktaya kısa bir ad vermek ister misin? (boş bırakabilirsin)",
                  "en": "Want to give this point a short name? (you can leave it blank)"},
    "olustur_dugme": {"tr": "Oluştur", "en": "Create"},
    "iptal": {"tr": "Vazgeç", "en": "Cancel"},
    "olusturuluyor": {"tr": "Kurtarma noktası oluşturuluyor…", "en": "Creating a recovery point…"},
    "olusturuldu": {"tr": "Kurtarma noktası oluşturuldu.", "en": "Recovery point created."},
    "bos_baslik": {"tr": "Henüz kurtarma noktası yok", "en": "No recovery points yet"},
    "bos_alt": {"tr": "“Şimdi nokta oluştur” ile ilkini aç; büyük bir değişiklikten "
                      "(güncelleme, ayar değişikliği) önce almak iyi fikirdir.",
               "en": "Create your first one with “Create a point now”; it's a good idea "
                     "before a big change (an update, a config change)."},
    "elle": {"tr": "elle", "en": "manual"},
    "oto": {"tr": "güncelleme öncesi", "en": "before an update"},
    "boyut_bilinmiyor": {"tr": "boyut bilinmiyor", "en": "size unknown"},
    "geri_yukle": {"tr": "Geri yükle", "en": "Restore"},
    "sil": {"tr": "Sil", "en": "Delete"},
    "geri_yukle_baslik": {"tr": "Bu noktaya geri dön", "en": "Return to this point"},
    "geri_yukle_metin": {"tr": "{tarih} tarihli kurtarma noktasındaki /etc ve /root içeriği "
                               "şimdiki sistemin ÜZERİNE YAZILACAK. Bu noktadan sonra "
                               "yaptığın sistem ayarı değişiklikleri kaybolur.",
                        "en": "The /etc and /root contents from the {tarih} recovery point "
                              "will be WRITTEN OVER the current system. Any system setting "
                              "changes made since then will be lost."},
    "paketleri_de_kur": {"tr": "O zaman kurulu olup şimdi eksik olan paketleri de kur",
                        "en": "Also install packages that were present then but are missing now"},
    "geri_yukle_dugme": {"tr": "Geri yükle", "en": "Restore"},
    "geri_yukluyor": {"tr": "Geri yükleniyor, kapatma…", "en": "Restoring, don't close…"},
    "geri_yuklendi": {"tr": "Geri yüklendi. Değişikliklerin tamamı için yeniden başlatman "
                            "önerilir.",
                      "en": "Restored. A reboot is recommended for all the changes to take "
                            "effect."},
    "sil_baslik": {"tr": "Kurtarma noktasını sil", "en": "Delete the recovery point"},
    "sil_metin": {"tr": "{tarih} tarihli nokta kalıcı olarak silinecek.",
                 "en": "The point from {tarih} will be permanently deleted."},
    "silindi": {"tr": "Kurtarma noktası silindi.", "en": "Recovery point deleted."},
    "hata_disk_dolu": {"tr": "Disk yeterince boş değil, nokta oluşturulamadı.",
                       "en": "Not enough free disk space; the point wasn't created."},
    "hata_etiket": {"tr": "Ad çok uzun ya da izin verilmeyen bir karakter içeriyor.",
                   "en": "The name is too long or has a character that isn't allowed."},
    "hata_rsync": {"tr": "Kopyalama sırasında bir hata oldu, hiçbir şey değişmedi.",
                  "en": "Something went wrong while copying; nothing was changed."},
    "hata_yetki": {"tr": "İşlem iptal edildi ya da yetki alınamadı.",
                  "en": "The action was cancelled or authorization failed."},
    "hata_genel": {"tr": "Bir şeyler ters gitti.", "en": "Something went wrong."},
    "ayar_oto_baslik": {"tr": "Güncellemeden önce otomatik nokta",
                        "en": "Automatic point before an update"},
    "ayar_oto_alt": {"tr": "apt ile paket kurup güncellerken, değişiklikten hemen önce "
                          "kendiliğinden bir kurtarma noktası açılır.",
                    "en": "When you install or update packages with apt, a recovery point "
                          "is opened automatically right before the change."},
    "ayar_sakla_baslik": {"tr": "Kaç nokta saklansın", "en": "How many points to keep"},
    "ayar_sakla_alt": {"tr": "Bu sayıyı aşan en eski noktalar otomatik silinir.",
                       "en": "The oldest points beyond this number are deleted automatically."},
    "ayar_aralik_baslik": {"tr": "Otomatik noktalar arası en az süre (dakika)",
                          "en": "Minimum time between automatic points (minutes)"},
    "ayar_aralik_alt": {"tr": "Güncelleme öncesi otomatik nokta, öncekinden bu kadar dakika "
                             "geçmeden tekrar açılmaz.",
                       "en": "An automatic point before an update won't open again until "
                             "this many minutes have passed since the last one."},
    "ayar_disk_baslik": {"tr": "Nokta için gereken en az boş alan (MB)",
                        "en": "Minimum free space required for a point (MB)"},
    "ayar_disk_alt": {"tr": "Bundan az boş disk alanı varsa yeni nokta oluşturulmaz.",
                     "en": "If there's less free disk space than this, a new point won't "
                           "be created."},
    "ayar_kaydet": {"tr": "Kaydet", "en": "Save"},
    "ayar_kaydedildi": {"tr": "Ayarlar kaydedildi.", "en": "Settings saved."},
    "canli_uyari": {"tr": "Canlı (USB) oturumundasın: oluşturulacak nokta yalnızca bu "
                         "oturum kapanana kadar kalıcı olur. Kurulu bir sistemde kullan.",
                   "en": "You're in a live (USB) session: a point created now only lasts "
                         "until this session ends. Use this on an installed system."},
}
METIN = dil.zenginlestir(METIN)
HATA_ANAHTARLARI = {
    "disk_dolu": "hata_disk_dolu", "gecersiz_etiket": "hata_etiket",
    "rsync_hata": "hata_rsync", "__YETKI_YOK__": "hata_yetki",
    "__BOS_CIKTI__": "hata_yetki",
}


def logo_bul():
    kok = os.path.abspath(os.path.join(BURASI, "..", "..", ".."))
    for yol in (os.path.join(kok, "usr/share/icons/hicolor/256x256/apps/carotos-kurtarma.png"),
                "/usr/share/icons/hicolor/256x256/apps/carotos-kurtarma.png"):
        if os.path.isfile(yol):
            return yol
    return None


CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "carotos-kurtarma")
CONFIG_FILE = os.path.join(CONFIG_DIR, "arayuz.json")


def arayuz_ayarlarini_oku():
    ayar = {"lang": dil.varsayilan_dil(), "theme": "dark"}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            veri = json.load(fh)
        if isinstance(veri, dict):
            ayar["lang"] = dil.gecerli(veri.get("lang"))
            if veri.get("theme") in ("dark", "light"):
                ayar["theme"] = veri["theme"]
    except (OSError, ValueError):
        pass
    return ayar


def arayuz_ayarlarini_yaz(ayar):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(ayar, fh)
    except OSError:
        pass


def yonet_cagir(argv, girdi=None, zaman=600):
    """pkexec ile carotos-kurtarma-yonet'i cagirir; ({"kod": ...}) dondurur.
    pkexec dogrudan kullanicinin iptal etmesinde/yetki alamamasinda hedef hic
    calismadan cikar (stdout bos kalir) -- bu, "__BOS_CIKTI__" ile yakalanir."""
    try:
        p = subprocess.run(["pkexec", YONET] + list(argv), input=girdi,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, errors="replace", timeout=zaman)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"kod": "__SURECHATASI__", "ayrinti": str(exc)}
    satirlar = [s for s in p.stdout.splitlines() if s.strip()]
    if not satirlar:
        return {"kod": "__BOS_CIKTI__"}
    try:
        return json.loads(satirlar[-1])
    except ValueError:
        return {"kod": "__GECERSIZ_CIKTI__", "ayrinti": p.stdout[-400:]}


class KurtarmaPenceresi(Gtk.Window):
    def __init__(self):
        self.ayar = arayuz_ayarlarini_oku()
        self.lang = self.ayar["lang"]
        self.theme = self.ayar["theme"]
        self.mesgul = False

        super().__init__(title=METIN["baslik"][self.lang])
        self.set_default_size(760, 620)
        self.set_size_request(640, 480)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", lambda *_: Gtk.main_quit())

        tema.uygula(self.theme, VURGU)
        logo = logo_bul()
        if logo:
            try:
                self.set_icon_from_file(logo)
            except GLib.Error:
                pass

        bolumler = [("kurtarma", [("noktalar", "kalkan"), ("ayarlar", "ayar")])]
        self.kabuk = tema.Kabuk(logo, bolumler, self._sayfa_secildi)
        self.add(self.kabuk)
        self.kabuk.marka_ayarla(METIN["baslik"][self.lang], "v" + APP_VERSION)

        olustur_btn = tema.dugme(METIN["olustur"][self.lang], "ana", self._olustur_dialogu)
        self.kabuk.ust_sag.pack_start(olustur_btn, False, False, 0)

        alt = Gtk.Box(spacing=8)
        self.lang_combo = tema.AcilirSecim()
        for kod, ad, taslak in dil.etkin_diller():
            self.lang_combo.append(kod, dil.secici_adi(kod, ad, taslak))
        self.lang_combo.set_active_id(self.lang)
        self.lang_combo.connect("changed", self._dil_degisti)
        alt.pack_start(self.lang_combo, True, True, 0)
        self.theme_btn = tema.dugme("", None, self._tema_degistir)
        alt.pack_start(self.theme_btn, False, False, 0)
        self.kabuk.yan_alt.pack_start(alt, False, False, 0)

        self._noktalar_sayfasi_kur()
        self._ayarlar_sayfasi_kur()
        self.kabuk.sec("noktalar")
        self._yenile()

    # -- yardimcilar ---------------------------------------------------------

    def _dil_degisti(self, combo):
        kod = combo.get_active_id()
        if not kod or kod == self.lang:
            return
        self.lang = kod
        self.ayar["lang"] = kod
        arayuz_ayarlarini_yaz(self.ayar)
        self.set_title(METIN["baslik"][self.lang])
        self.kabuk.marka_ayarla(METIN["baslik"][self.lang], "v" + APP_VERSION)
        for anahtar in ("noktalar", "ayarlar"):
            self.kabuk.menu_metni(anahtar, METIN["men_" + anahtar][self.lang])
        self._yenile()
        self._ayarlar_sayfasi_doldur()

    def _tema_degistir(self, *_a):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.ayar["theme"] = self.theme
        arayuz_ayarlarini_yaz(self.ayar)
        tema.uygula(self.theme, VURGU)
        self._yenile()
        self._ayarlar_sayfasi_doldur()

    def _sayfa_secildi(self, anahtar):
        if anahtar == "noktalar":
            self.kabuk.baslik_ayarla(METIN["men_noktalar"][self.lang], METIN["ust_noktalar"][self.lang])
            self.kabuk.icerik(self.noktalar_kutu)
        else:
            self.kabuk.baslik_ayarla(METIN["men_ayarlar"][self.lang])
            self.kabuk.icerik(self.ayarlar_kutu)

    def _kilitli_mi(self):
        if self.mesgul:
            return True
        return False

    # -- kurtarma noktalari sayfasi ------------------------------------------

    def _noktalar_sayfasi_kur(self):
        self.noktalar_kutu = Gtk.ScrolledWindow()
        self.noktalar_kutu.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.noktalar_ic = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.noktalar_ic.set_margin_top(4)
        self.noktalar_ic.set_margin_bottom(16)
        self.noktalar_kutu.add(self.noktalar_ic)

    def _yenile(self):
        for w in list(self.noktalar_ic.get_children()):
            self.noktalar_ic.remove(w)
        if K.canli_sistem_mi():
            kutu, _ = tema.not_kutusu(METIN["canli_uyari"][self.lang], "uyari")
            self.noktalar_ic.pack_start(kutu, False, False, 0)
        kutu, _ = tema.not_kutusu(METIN["aciklama"][self.lang], "bilgi")
        self.noktalar_ic.pack_start(kutu, False, False, 0)
        noktalar = K.noktalari_listele()
        if not noktalar:
            self.noktalar_ic.pack_start(
                tema.bos_durum("kalkan", METIN["bos_baslik"][self.lang], METIN["bos_alt"][self.lang]),
                False, False, 10)
        for meta in noktalar:
            self.noktalar_ic.pack_start(self._nokta_karti(meta), False, False, 0)
        self.noktalar_ic.show_all()

    def _tarihi_bicimle(self, iso_metin):
        try:
            import datetime
            dt = datetime.datetime.fromisoformat(iso_metin)
            return dt.strftime("%d.%m.%Y %H:%M")
        except (TypeError, ValueError):
            return iso_metin or "?"

    def _nokta_karti(self, meta):
        dis, ic = tema.kart()
        tarih = self._tarihi_bicimle(meta.get("olusturma"))
        baslik = meta.get("etiket") or tarih
        alt_satirlar = [tarih if meta.get("etiket") else None,
                        METIN["oto" if meta.get("tetikleyici") == "oto" else "elle"][self.lang]]
        boyut = meta.get("boyut_mb")
        alt_satirlar.append(f"{boyut} MB" if boyut else METIN["boyut_bilinmiyor"][self.lang])
        alt = "  ·  ".join(s for s in alt_satirlar if s)

        dugmeler = Gtk.Box(spacing=8)
        geri_btn = tema.dugme(METIN["geri_yukle"][self.lang], "tehlike", self._geri_yukle_sor, meta)
        sil_btn = tema.dugme(METIN["sil"][self.lang], None, self._sil_sor, meta)
        dugmeler.pack_start(geri_btn, False, False, 0)
        dugmeler.pack_start(sil_btn, False, False, 0)
        tema.kart_basligi(ic, baslik, alt, dugmeler)
        return dis

    def _olustur_dialogu(self, *_a):
        if self._kilitli_mi():
            return
        dlg = Gtk.Dialog(title=METIN["olustur_basligi"][self.lang], transient_for=self,
                         flags=Gtk.DialogFlags.MODAL)
        dlg.add_button(METIN["iptal"][self.lang], Gtk.ResponseType.CANCEL)
        dlg.add_button(METIN["olustur_dugme"][self.lang], Gtk.ResponseType.OK)
        kutu = dlg.get_content_area()
        kutu.set_margin_top(14)
        kutu.set_margin_bottom(14)
        kutu.set_margin_start(16)
        kutu.set_margin_end(16)
        kutu.set_spacing(8)
        kutu.add(tema.etiket(METIN["etiket_sor"][self.lang], sar=True, genislik=50))
        giris = Gtk.Entry()
        giris.set_activates_default(True)
        kutu.add(giris)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.show_all()
        yanit = dlg.run()
        etiket = giris.get_text().strip() or None
        dlg.destroy()
        if yanit != Gtk.ResponseType.OK:
            return
        if etiket is not None and not K.etiket_gecerli_mi(etiket):
            self.kabuk.bildir(METIN["hata_etiket"][self.lang], "hata")
            return
        self._olustur_calistir(etiket)

    def _olustur_calistir(self, etiket):
        self.mesgul = True
        self.kabuk.bildir(METIN["olusturuluyor"][self.lang])
        argv = ["olustur"] + (["--etiket", etiket] if etiket else [])

        def isci():
            sonuc = yonet_cagir(argv)
            GLib.idle_add(self._olustur_bitti, sonuc)

        threading.Thread(target=isci, daemon=True).start()

    def _olustur_bitti(self, sonuc):
        self.mesgul = False
        if sonuc.get("kod") == "__TAMAM__":
            self.kabuk.bildir(METIN["olusturuldu"][self.lang], "basari")
        else:
            self._hata_goster(sonuc)
        self._yenile()
        return False

    def _geri_yukle_sor(self, meta):
        if self._kilitli_mi():
            return
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        onay = Gtk.CheckButton(label=METIN["paketleri_de_kur"][self.lang])
        kutu.add(onay)
        metin = METIN["geri_yukle_metin"][self.lang].format(tarih=self._tarihi_bicimle(meta.get("olusturma")))
        if not tema.onay_sor(self, METIN["geri_yukle_baslik"][self.lang], metin,
                             METIN["geri_yukle_dugme"][self.lang], METIN["iptal"][self.lang],
                             tehlike=True, ek=kutu):
            return
        self._geri_yukle_calistir(meta["id"], onay.get_active())

    def _geri_yukle_calistir(self, nokta_id, paketler):
        self.mesgul = True
        self.kabuk.bildir(METIN["geri_yukluyor"][self.lang])
        argv = ["geri-yukle", nokta_id] + (["--paketler"] if paketler else [])

        def isci():
            sonuc = yonet_cagir(argv, zaman=1800)
            GLib.idle_add(self._geri_yukle_bitti, sonuc)

        threading.Thread(target=isci, daemon=True).start()

    def _geri_yukle_bitti(self, sonuc):
        self.mesgul = False
        if sonuc.get("kod") == "__TAMAM__":
            self.kabuk.bildir(METIN["geri_yuklendi"][self.lang], "basari")
        else:
            self._hata_goster(sonuc)
        self._yenile()
        return False

    def _sil_sor(self, meta):
        if self._kilitli_mi():
            return
        metin = METIN["sil_metin"][self.lang].format(tarih=self._tarihi_bicimle(meta.get("olusturma")))
        if not tema.onay_sor(self, METIN["sil_baslik"][self.lang], metin,
                             METIN["sil"][self.lang], METIN["iptal"][self.lang], tehlike=True):
            return
        self._sil_calistir(meta["id"])

    def _sil_calistir(self, nokta_id):
        self.mesgul = True

        def isci():
            sonuc = yonet_cagir(["sil", nokta_id])
            GLib.idle_add(self._sil_bitti, sonuc)

        threading.Thread(target=isci, daemon=True).start()

    def _sil_bitti(self, sonuc):
        self.mesgul = False
        if sonuc.get("kod") == "__TAMAM__":
            self.kabuk.bildir(METIN["silindi"][self.lang], "basari")
        else:
            self._hata_goster(sonuc)
        self._yenile()
        return False

    def _hata_goster(self, sonuc):
        anahtar = HATA_ANAHTARLARI.get(sonuc.get("kod"), "hata_genel")
        self.kabuk.bildir(METIN[anahtar][self.lang], "hata")

    # -- ayarlar sayfasi ------------------------------------------------------

    def _ayarlar_sayfasi_kur(self):
        self.ayarlar_kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.ayarlar_kutu.set_margin_top(4)
        self._ayarlar_sayfasi_doldur()

    def _ayarlar_sayfasi_doldur(self):
        for w in list(self.ayarlar_kutu.get_children()):
            self.ayarlar_kutu.remove(w)
        ayar = K.ayarlari_oku()

        dis, ic = tema.kart()
        self.oto_anahtari = Gtk.Switch()
        self.oto_anahtari.set_active(bool(ayar["oto_guncelleme_oncesi"]))
        self.oto_anahtari.set_valign(Gtk.Align.CENTER)
        tema.kart_basligi(ic, METIN["ayar_oto_baslik"][self.lang], METIN["ayar_oto_alt"][self.lang],
                          self.oto_anahtari)
        self.ayarlar_kutu.pack_start(dis, False, False, 0)

        dis2, ic2 = tema.kart()
        self.sakla_spin = Gtk.SpinButton.new_with_range(1, 30, 1)
        self.sakla_spin.set_value(ayar["sakla"])
        self.sakla_spin.set_valign(Gtk.Align.CENTER)
        tema.kart_basligi(ic2, METIN["ayar_sakla_baslik"][self.lang], METIN["ayar_sakla_alt"][self.lang],
                          self.sakla_spin)
        self.ayarlar_kutu.pack_start(dis2, False, False, 0)

        dis3, ic3 = tema.kart()
        self.aralik_spin = Gtk.SpinButton.new_with_range(1, 1440, 1)
        self.aralik_spin.set_value(ayar["min_aralik_dk"])
        self.aralik_spin.set_valign(Gtk.Align.CENTER)
        tema.kart_basligi(ic3, METIN["ayar_aralik_baslik"][self.lang], METIN["ayar_aralik_alt"][self.lang],
                          self.aralik_spin)
        self.ayarlar_kutu.pack_start(dis3, False, False, 0)

        dis4, ic4 = tema.kart()
        self.disk_spin = Gtk.SpinButton.new_with_range(64, 20480, 64)
        self.disk_spin.set_value(ayar["min_bos_mb"])
        self.disk_spin.set_valign(Gtk.Align.CENTER)
        tema.kart_basligi(ic4, METIN["ayar_disk_baslik"][self.lang], METIN["ayar_disk_alt"][self.lang],
                          self.disk_spin)
        self.ayarlar_kutu.pack_start(dis4, False, False, 0)

        kaydet_btn = tema.dugme(METIN["ayar_kaydet"][self.lang], "ana", self._ayarlari_kaydet)
        kaydet_btn.set_halign(Gtk.Align.START)
        self.ayarlar_kutu.pack_start(kaydet_btn, False, False, 4)
        self.ayarlar_kutu.show_all()

    def _ayarlari_kaydet(self, *_a):
        if self._kilitli_mi():
            return
        yeni = {"oto_guncelleme_oncesi": self.oto_anahtari.get_active(),
               "sakla": int(self.sakla_spin.get_value()),
               "min_aralik_dk": int(self.aralik_spin.get_value()),
               "min_bos_mb": int(self.disk_spin.get_value())}
        self.mesgul = True

        def isci():
            sonuc = yonet_cagir(["ayar-yaz"], girdi=json.dumps(yeni))
            GLib.idle_add(self._ayar_yazildi, sonuc)

        threading.Thread(target=isci, daemon=True).start()

    def _ayar_yazildi(self, sonuc):
        self.mesgul = False
        if sonuc.get("kod") == "__TAMAM__":
            self.kabuk.bildir(METIN["ayar_kaydedildi"][self.lang], "basari")
        else:
            self._hata_goster(sonuc)
        return False


def main():
    pencere = KurtarmaPenceresi()
    pencere.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
