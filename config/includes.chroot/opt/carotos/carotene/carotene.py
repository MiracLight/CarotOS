#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carotene - CarotOS antivirus uygulamasi.

ClamAV ile istendiginde tarama yapar. Arka planda surekli calisan bir hizmet
kurmaz: ClamAV tanimlari yuklerken yaklasik 1 GB bellek kullanir, bu da
CarotOS'un hedefledigi dusuk donanimla celisir.

Kullanim:
    carotene                 Arayuzu acar
    carotene --tara YOL...   Verilen dosya ya da klasorleri hemen tarar
                             (dosya yoneticisindeki "Carotene ile tara")
"""

import json
import os
import subprocess
import sys
import threading
import time

APP_VERSION = "1.0"

# Ortak klasore __pycache__ yazilmasin: depodan calistirildiginda ISO'ya
# girerdi, kurulu sistemde zaten yazilamaz.
sys.dont_write_bytecode = True

# Ortak modüller: kurulu sistemde /opt/carotos/ortak, depoda kardes klasor
ORTAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "ortak")
if ORTAK not in sys.path:
    sys.path.insert(0, ORTAK)

import tarama_motoru as M  # noqa: E402

import gi  # noqa: E402
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

import tema  # noqa: E402  (CarotOS ortak grafit temasi)
from bekleme_cubugu import SweepBar  # noqa: E402

VURGU = "carotene"        # ortak/tema.py: havuc turuncusu


# ---------------------------------------------------------------------------
# Metinler
# ---------------------------------------------------------------------------

METIN = {
    "sec_protect": {"tr": "Koruma", "en": "Protection"},
    "k_last": {"tr": "Son tarama", "en": "Last scan"},
    "k_quar": {"tr": "Karantinada", "en": "In quarantine"},
    "k_defs": {"tr": "Tanım yaşı", "en": "Definitions age"},
    "sec_maint": {"tr": "Bakım", "en": "Maintenance"},
    "k_scanned": {"tr": "Taranan dosya", "en": "Files scanned"},
    "k_found": {"tr": "Bulgu", "en": "Findings"},
    "cancel": {"tr": "Vazgeç", "en": "Cancel"},
    "ok_btn": {"tr": "Tamam", "en": "OK"},
    "pick_ok": {"tr": "Seç", "en": "Select"},
    "app_title": {"tr": "Carotene", "en": "Carotene"},
    "header_sub": {"tr": "Antivirüs", "en": "Antivirus"},
    "nav_scan": {"tr": "Tarama", "en": "Scan"},
    "nav_quarantine": {"tr": "Karantina", "en": "Quarantine"},
    "nav_defs": {"tr": "Virüs tanımları", "en": "Virus definitions"},
    "nav_history": {"tr": "Tarama geçmişi", "en": "Scan history"},
    "theme_light": {"tr": "Açık tema", "en": "Light theme"},
    "theme_dark": {"tr": "Koyu tema", "en": "Dark theme"},
    "ready": {"tr": "Hazır", "en": "Ready"},

    "scan_title": {"tr": "Tarama", "en": "Scan"},
    "scan_intro": {
        "tr": "Dosyalar ClamAV ile bilinen zararlı yazılım imzalarına karşı "
              "taranır. Tarama yalnızca siz başlattığınızda çalışır. Temiz "
              "sonucu, dosyaların güvenli olduğunu garanti etmez; yalnızca "
              "bilinen bir imzaya rastlanmadığını gösterir.",
        "en": "Files are scanned with ClamAV against known malware "
              "signatures. A scan runs only when you start it. A clean result "
              "does not guarantee that the files are safe; it only shows that "
              "no known signature was found."},
    "quick_title": {"tr": "Hızlı tarama", "en": "Quick scan"},
    "quick_desc": {
        "tr": "İndirilenler ve Masaüstü klasörleri ile ana klasördeki "
              "dosyalar taranır. Dışarıdan gelen dosyalar çoğunlukla bu "
              "konumlardadır.",
        "en": "Scans the Downloads and Desktop folders and the files in the "
              "home folder. Files from outside usually arrive in these "
              "locations."},
    "home_title": {"tr": "Ana klasörün tamamı", "en": "Entire home folder"},
    "home_desc": {
        "tr": "Ana klasör tüm alt klasörleriyle taranır. Dosya sayısına göre "
              "uzun sürebilir.",
        "en": "Scans the home folder with all subfolders. It may take a long "
              "time depending on the number of files."},
    "custom_title": {"tr": "Özel tarama", "en": "Custom scan"},
    "custom_desc": {
        "tr": "Seçilen bir klasör ya da dosya taranır.",
        "en": "Scans a selected folder or file."},
    "scan_btn": {"tr": "Tara", "en": "Scan"},
    "pick_folder": {"tr": "Klasör seç", "en": "Choose folder"},
    "pick_file": {"tr": "Dosya seç", "en": "Choose file"},
    "stop_btn": {"tr": "Durdur", "en": "Stop"},
    "running_title": {"tr": "Tarama sürüyor", "en": "Scan in progress"},
    "running_counts": {"tr": "Taranan dosya: {n} · Bulgu: {b}",
                       "en": "Files scanned: {n} · Findings: {b}"},
    "loading_defs": {
        "tr": "Virüs tanımları belleğe yükleniyor. Bu adım yaklaşık 10 saniye "
              "sürer.",
        "en": "Loading virus definitions into memory. This step takes about "
              "10 seconds."},
    "scanning": {"tr": "Tarama sürüyor…", "en": "Scanning…"},

    "res_clean_title": {"tr": "Bilinen bir tehdide rastlanmadı",
                        "en": "No known threat was found"},
    "res_found_title": {"tr": "{b} tehdit bulundu", "en": "{b} threats found"},
    "res_cancel_title": {"tr": "Tarama durduruldu", "en": "Scan stopped"},
    "res_error_title": {"tr": "Tarama tamamlanamadı",
                        "en": "The scan could not be completed"},
    "res_summary": {"tr": "{n} dosya tarandı, {s} sn sürdü.",
                    "en": "{n} files scanned in {s} s."},
    "res_skipped": {"tr": "{k} öge atlandı (boş dosya, bağlantı ya da "
                          "okunamayan dosya).",
                    "en": "{k} items were skipped (empty files, links or "
                          "unreadable files)."},
    "res_found_hint": {
        "tr": "Önerilen işlem karantinadır: dosya çalıştırılamaz hâle getirilir "
              "ve gerekirse geri yüklenebilir.",
        "en": "Quarantine is the recommended action: the file is made "
              "non-executable and can be restored if needed."},
    "act_quarantine": {"tr": "Karantinaya al", "en": "Quarantine"},
    "act_delete": {"tr": "Sil", "en": "Delete"},
    "act_ignore": {"tr": "Yok say", "en": "Ignore"},
    "done_quarantined": {"tr": "Karantinaya alındı.",
                         "en": "Moved to quarantine."},
    "done_deleted": {"tr": "Silindi.", "en": "Deleted."},
    "done_ignored": {"tr": "Yok sayıldı; dosya yerinde bırakıldı.",
                     "en": "Ignored; the file was left in place."},
    "done_allowed": {"tr": "İzin listesine eklendi; değişmediği sürece "
                           "bildirilmeyecek.",
                     "en": "Added to the allow list; it will not be reported "
                           "while it stays unchanged."},
    "ignore_title": {"tr": "Bulgu yok sayılsın mı?", "en": "Ignore this finding?"},
    "ignore_body": {
        "tr": "Dosya yerinde bırakılır.\n\n\u201cHer zaman\u201d seçilirse "
              "dosyanın parmak izi izin listesine eklenir ve sonraki "
              "taramalarda bildirilmez. Dosyanın içeriği değişirse yeniden "
              "bildirilir. Bunu yalnızca dosyanın güvenilir olduğundan "
              "eminseniz (yanlış pozitif) seçin.\n\n{yol}",
        "en": "The file is left in place.\n\nIf \u201cAlways\u201d is "
              "chosen, the file's fingerprint is added to the allow list and "
              "it is not reported in later scans. If the file's content "
              "changes, it is reported again. Choose this only if you are "
              "sure the file is trustworthy (a false positive).\n\n{yol}"},
    "ignore_once": {"tr": "Yalnızca bu sefer", "en": "This time only"},
    "ignore_always": {"tr": "Her zaman", "en": "Always"},
    "res_allowed": {"tr": "{k} dosya izin listesinde olduğu için bildirilmedi.",
                    "en": "{k} files were not reported because they are on "
                          "the allow list."},
    "a_title": {"tr": "İzin listesi", "en": "Allow list"},
    "a_intro": {
        "tr": "Bu dosyalar \u201cHer zaman yok say\u201d ile eklendi. "
              "İçerikleri değişmediği sürece taramalarda bildirilmezler.",
        "en": "These files were added with \u201cAlways ignore\u201d. They "
              "are not reported in scans while their content stays unchanged."},
    "a_remove": {"tr": "Listeden çıkar", "en": "Remove from list"},
    "a_removed": {"tr": "İzin listesinden çıkarıldı.",
                  "en": "Removed from the allow list."},
    "args_none": {"tr": "Taranacak geçerli bir dosya ya da klasör verilmedi.",
                  "en": "No valid file or folder was given to scan."},
    "confirm_delete": {
        "tr": "Dosya kalıcı olarak silinecektir ve geri alınamaz:\n\n{yol}",
        "en": "The file will be deleted permanently and cannot be "
              "restored:\n\n{yol}"},

    "mem_title": {"tr": "Bellek az", "en": "Low memory"},
    "mem_body": {
        "tr": "Kullanılabilir bellek {mb} MB. Tarama sırasında virüs tanımları "
              "yaklaşık 1 GB bellek kullanır; sistem yavaşlayabilir. Açık "
              "uygulamaları kapatmanız önerilir. Tarama başlatılsın mı?",
        "en": "Available memory is {mb} MB. Virus definitions use about 1 GB "
              "of memory during a scan; the system may slow down. Closing "
              "open applications is recommended. Start the scan?"},
    "no_defs_block": {
        "tr": "Virüs tanımları bulunamadı. Tarama yapabilmek için önce "
              "“Virüs tanımları” bölümünden tanımları güncelleyin.",
        "en": "No virus definitions were found. Update the definitions in the "
              "“Virus definitions” section before scanning."},
    "no_clamav": {
        "tr": "ClamAV kurulu değildir. Carotene bu sistemde tarama yapamaz.",
        "en": "ClamAV is not installed. Carotene cannot scan on this system."},
    "install_clamav": {"tr": "Mağaza'da ClamAV'ı kur",
                       "en": "Install ClamAV in the Store"},
    "defs_note_ok": {"tr": "Virüs tanımları: {tarih} ({yas})",
                     "en": "Virus definitions: {tarih} ({yas})"},
    "defs_note_old": {
        "tr": "Virüs tanımları {gun} günlüktür. Eski tanımlarla yapılan "
              "taramada yeni tehditler bulunamaz; tanımları güncellemeniz "
              "önerilir.",
        "en": "Virus definitions are {gun} days old. A scan with old "
              "definitions cannot find new threats; updating them is "
              "recommended."},
    "age_today": {"tr": "bugün", "en": "today"},
    "age_days": {"tr": "{gun} gün önce", "en": "{gun} days ago"},
    "nothing_to_scan": {"tr": "Taranacak dosya bulunamadı.",
                        "en": "No files were found to scan."},

    "q_title": {"tr": "Karantina", "en": "Quarantine"},
    "q_intro": {
        "tr": "Karantinadaki dosyalar yalnızca sizin erişebildiğiniz bir "
              "klasörde, çalıştırılamaz biçimde saklanır. Geri yüklenen dosya "
              "yeniden tehlikeli olabilir.",
        "en": "Quarantined files are kept in a folder only you can access and "
              "cannot be executed. A restored file may be dangerous again."},
    "q_empty": {"tr": "Karantinada dosya yok.", "en": "The quarantine is empty."},
    "q_restore": {"tr": "Geri yükle", "en": "Restore"},
    "q_delete": {"tr": "Kalıcı olarak sil", "en": "Delete permanently"},
    "q_meta": {"tr": "Tehdit: {imza} · {tarih}", "en": "Threat: {imza} · {tarih}"},
    "confirm_restore": {
        "tr": "Dosya özgün konumuna geri yüklenecektir. Bulunan tehdit "
              "yanlış pozitif değilse dosya sisteme zarar verebilir.\n\n{yol}",
        "en": "The file will be restored to its original location. If the "
              "threat is not a false positive, the file may harm the "
              "system.\n\n{yol}"},
    "restored_to": {"tr": "Geri yüklendi: {yol}", "en": "Restored: {yol}"},

    "d_title": {"tr": "Virüs tanımları", "en": "Virus definitions"},
    "d_intro": {
        "tr": "Tanımlar, ClamAV'ın tanıdığı zararlı yazılım imzalarıdır. Yeni "
              "tehditler her gün eklenir; tanımlar güncel tutulmadıkça yeni "
              "tehditler bulunamaz.",
        "en": "Definitions are the malware signatures ClamAV recognises. New "
              "threats are added every day; new threats cannot be found "
              "unless the definitions are kept up to date."},
    "d_badge_ok": {"tr": "GÜNCEL", "en": "CURRENT"},
    "d_badge_old": {"tr": "ESKİ", "en": "OUTDATED"},
    "d_badge_none": {"tr": "YOK", "en": "MISSING"},
    "d_card": {"tr": "ClamAV tanım veritabanı", "en": "ClamAV definition database"},
    "d_date": {"tr": "Son güncelleme: {tarih} ({yas})",
               "en": "Last update: {tarih} ({yas})"},
    "d_sigs": {"tr": "{imza} imza · {dosyalar}", "en": "{imza} signatures · {dosyalar}"},
    "d_none": {"tr": "Tanım dosyası bulunamadı.",
               "en": "No definition files were found."},
    "d_update": {"tr": "Tanımları güncelle", "en": "Update definitions"},
    "d_update_note": {
        "tr": "Güncelleme yönetici yetkisi ister ve internet bağlantısı "
              "gerektirir. Arka planda otomatik güncelleme yapılmaz.",
        "en": "Updating requires administrator privileges and an internet "
              "connection. No automatic update runs in the background."},
    "d_live_note": {
        "tr": "Canlı oturumda indirilen tanımlar bellekte tutulur ve yeniden "
              "başlatmada silinir.",
        "en": "In a live session, downloaded definitions are kept in memory "
              "and are removed at restart."},
    "d_updating": {"tr": "Tanımlar güncelleniyor…", "en": "Updating definitions…"},
    "u_" + M.GUNCELLENDI: {"tr": "Tanımlar güncellendi.",
                           "en": "Definitions were updated."},
    "u_" + M.ZATEN_GUNCEL: {"tr": "Tanımlar zaten günceldir.",
                            "en": "Definitions are already up to date."},
    "u_" + M.CEVRIMDISI: {
        "tr": "Güncelleme sunucusuna ulaşılamadı. İnternet bağlantısını "
              "denetleyip yeniden deneyin.",
        "en": "The update server could not be reached. Check the internet "
              "connection and try again."},
    "u_" + M.BEKLEME: {
        "tr": "Güncelleme sunucusu çok sık istek nedeniyle geçici olarak "
              "yanıt vermiyor. Bir süre sonra yeniden deneyin.",
        "en": "The update server is temporarily refusing requests because of "
              "too many requests. Try again later."},
    "u_" + M.KILITLI: {
        "tr": "Başka bir tanım güncellemesi sürüyor. Birkaç dakika sonra "
              "yeniden deneyin.",
        "en": "Another definition update is running. Try again in a few "
              "minutes."},
    "u_" + M.IPTAL: {"tr": "İşlem iptal edildi.", "en": "The operation was cancelled."},
    "u_" + M.GUNCELLEME_HATASI: {"tr": "Güncelleme başarısız oldu.",
                                 "en": "The update failed."},
    "show_output": {"tr": "Çıktıyı göster", "en": "Show output"},
    "close": {"tr": "Kapat", "en": "Close"},

    "h_title": {"tr": "Tarama geçmişi", "en": "Scan history"},
    "h_intro": {"tr": "Son {n} tarama listelenir.",
                "en": "The last {n} scans are listed."},
    "h_empty": {"tr": "Henüz tarama yapılmadı.", "en": "No scans yet."},
    "h_row": {"tr": "{n} dosya · {b} bulgu · {s} sn",
              "en": "{n} files · {b} findings · {s} s"},
    "kind_hizli": {"tr": "Hızlı tarama", "en": "Quick scan"},
    "kind_ev": {"tr": "Ana klasör", "en": "Home folder"},
    "kind_ozel": {"tr": "Özel tarama", "en": "Custom scan"},

    "e_" + M.DOSYA_YOK: {"tr": "Dosya artık yerinde değil.",
                         "en": "The file is no longer there."},
    "e_" + M.YETKI_YOK: {"tr": "Bu işlem için yetki yok.",
                         "en": "Permission denied for this operation."},
    "e_" + M.DUZ_DOSYA_DEGIL: {"tr": "Yalnızca normal dosyalar işlenebilir.",
                               "en": "Only regular files can be handled."},
    "e_" + M.SAHIBI_DEGIL: {"tr": "Dosya başka bir kullanıcıya ait; işlem "
                                  "yapılmadı.",
                            "en": "The file belongs to another user; nothing "
                                  "was changed."},
    "e_" + M.KLASOR_YOK: {"tr": "Özgün klasör artık yok; dosya karantinada "
                                "bırakıldı.",
                          "en": "The original folder no longer exists; the "
                                "file was kept in quarantine."},
}

def _varsayilan_dil():
    for degisken in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        deger = os.environ.get(degisken, "").strip()
        if deger and deger not in ("C", "POSIX"):
            return "tr" if deger.lower().startswith("tr") else "en"
    return "en"


CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "carotene")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
DEFAULTS = {"lang": _varsayilan_dil(), "theme": "dark"}
# Simge (PNG: SVG yukleyicisi her sistemde bulunmuyor), uygulamaya gore ../../../usr/share/... konumundadir: kurulu sistemde
# /usr/share/..., depodan calistirildiginda config/includes.chroot/usr/share/...
_KOK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", ".."))
LOGO_CANDIDATES = [
    os.path.join(_KOK, "usr/share/icons/hicolor/256x256/apps/carotene.png"),
    "/usr/share/icons/hicolor/256x256/apps/carotene.png",
]


def find_logo():
    for yol in LOGO_CANDIDATES:
        if os.path.isfile(yol):
            return yol
    return None


def load_settings():
    data = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            stored = json.load(fh)
        if isinstance(stored, dict):
            for key in DEFAULTS:
                if stored.get(key) in (("tr", "en") if key == "lang"
                                       else ("dark", "light")):
                    data[key] = stored[key]
    except (OSError, ValueError):
        pass
    return data


def save_settings(data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def is_live():
    try:
        with open("/proc/cmdline", encoding="ascii", errors="replace") as fh:
            return "boot=live" in fh.read()
    except OSError:
        return False


def tarih_metni(zaman):
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(zaman))


# ---------------------------------------------------------------------------
# Pencere
# ---------------------------------------------------------------------------

class CaroteneWindow(Gtk.Window):

    def __init__(self, settings):
        super().__init__(title=METIN["app_title"][settings["lang"]])
        self.settings = settings
        self.lang = settings["lang"]
        self.theme = settings["theme"]
        self.page = "scan"

        # tarama durumu
        self.tarama = None          # M.Tarama
        self.tarama_turu = None
        self.sayac = {"taranan": 0, "bulgu": 0, "son": ""}
        self.son_sonuc = None
        self.islenen = {}           # bulgu yolu -> sonuc anahtari
        self.ui_bekliyor = False

        # tanim guncelleme durumu
        self.guncelleniyor = False
        self.guncelleme_mesaji = None
        self.guncelleme_ciktisi = ""

        self.sweep_id = 0
        self.sweep_step = 0
        self.hap_durum = ("ready", {}, "kapali")
        self.kpi_taranan = self.kpi_bulgu = self.yol_etiketi = None

        tema.uygula(self.theme, VURGU)
        self.set_default_size(1040, 700)
        self.set_size_request(860, 580)
        self.set_position(Gtk.WindowPosition.CENTER)
        logo = find_logo()
        try:
            if logo:
                self.set_icon_from_file(logo)
            else:
                self.set_icon_name("carotene")
        except GLib.Error:
            pass
        self.connect("destroy", self.on_destroy)

        bolumler = [
            ("koruma", [("scan", "arama"), ("quarantine", "kilit")]),
            ("bakim", [("defs", "yenile"), ("history", "saat")]),
        ]
        self.kabuk = tema.Kabuk(logo, bolumler, self.on_nav)
        self.add(self.kabuk)

        self.bar = SweepBar(tema.AKTIF["vurgu"])
        self.hap = tema.DurumHapi()
        self.kabuk.ust_sag.pack_start(self.bar, False, False, 0)
        self.kabuk.ust_sag.pack_start(self.hap, False, False, 0)

        alt = Gtk.Box(spacing=8)
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append("tr", "Türkçe")
        self.lang_combo.append("en", "English")
        self.lang_combo.set_active_id(self.lang)
        self.lang_combo.connect("changed", self.on_lang_changed)
        alt.pack_start(self.lang_combo, True, True, 0)
        self.theme_btn = tema.dugme("", None, self.on_theme_toggled)
        alt.pack_start(self.theme_btn, False, False, 0)
        self.kabuk.yan_alt.pack_start(alt, False, False, 0)

        self.retranslate()

    def t(self, anahtar, **kw):
        metin = METIN[anahtar][self.lang]
        return metin.format(**kw) if kw else metin

    # -- durum ve bildirimler ---------------------------------------------------

    def set_hap(self, anahtar=None, tur="kapali", **kw):
        """Ust sagdaki durum hapi. Dil degisince yeniden yazilabilsin diye
        anahtar saklanir."""
        if anahtar:
            self.hap_durum = (anahtar, kw, tur)
        a, kw, tur = self.hap_durum
        self.hap.ayarla(self.t(a, **kw), tur)

    def magazada_clamav_kur(self, *_):
        """CarotOS Mağaza'yı doğrudan ClamAV sayfasında açar."""
        try:
            subprocess.Popen(["/opt/carotos/magaza/carotos-magaza.py",
                              "--paket", "clamav"])
        except OSError:
            self.bildir("no_clamav", "hata")

    def bildir(self, anahtar_ya_da_metin, tur="bilgi", **kw):
        metin = (self.t(anahtar_ya_da_metin, **kw)
                 if anahtar_ya_da_metin in METIN else anahtar_ya_da_metin)
        self.kabuk.bildir(metin, tur)

    # -- ortak parcalar ---------------------------------------------------------

    def giris(self, holder, baslik_anahtari, giris_anahtari, **kw):
        """Sayfa basligini kabuga yazar, aciklamayi sayfanin basina koyar."""
        self.kabuk.baslik_ayarla(self.t(baslik_anahtari), "")
        holder.pack_start(tema.etiket(self.t(giris_anahtari, **kw), "soluk",
                                      sar=True, genislik=110), False, False, 0)

    def satir_karti(self, ikon, renk, baslik, alt=None, sag=()):
        """Soldan simge, ortada metin, sagda dugmeler olan kart."""
        dis, ic = tema.kart(14, 6)
        satir = Gtk.Box(spacing=14)
        satir.pack_start(tema.ikon_kutusu(ikon, renk, 40), False, False, 0)
        orta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        orta.set_valign(Gtk.Align.CENTER)
        orta.pack_start(tema.etiket(baslik, "kart-baslik", sar=True), False, False, 0)
        if alt:
            orta.pack_start(tema.etiket(alt, "kart-alt", sar=True, genislik=80),
                            False, False, 0)
        satir.pack_start(orta, True, True, 0)
        for d in sag:
            satir.pack_end(d, False, False, 0)
        ic.pack_start(satir, False, False, 0)
        return dis, ic

    # -- sayfa gecisi ------------------------------------------------------------

    def show_page(self, key=None):
        self.page = key or self.page
        self.kpi_taranan = self.kpi_bulgu = self.yol_etiketi = None
        holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        {"scan": self.build_scan_page, "quarantine": self.build_quarantine_page,
         "defs": self.build_defs_page, "history": self.build_history_page
         }[self.page](holder)
        self.kabuk.icerik(holder)
        self.update_nav()
        self.update_sweep()

    def update_nav(self):
        bilgi = M.tanim_bilgisi()
        for key in ("scan", "quarantine", "defs", "history"):
            self.kabuk.menu_metni(key, self.t("nav_" + key))
        self.kabuk.rozet("scan", "…" if self.tarama else None, sakin=True)
        n = len(M.karantina_listesi())
        self.kabuk.rozet("quarantine", str(n) if n else None, sakin=True)
        if self.guncelleniyor:
            self.kabuk.rozet("defs", "…", sakin=True)
        elif bilgi["durum"] == M.TANIM_GUNCEL:
            self.kabuk.rozet("defs", None)
        else:
            self.kabuk.rozet("defs", "!")
        g = len(M.gecmis())
        self.kabuk.rozet("history", str(g) if g else None, sakin=True)

    def update_sweep(self):
        if self.tarama or self.guncelleniyor:
            self.bar.show()
            if not self.sweep_id:
                self.sweep_id = GLib.timeout_add(45, self._sweep)
        else:
            if self.sweep_id:
                GLib.source_remove(self.sweep_id)
                self.sweep_id = 0
            self.bar.hide()

    def _sweep(self):
        if not (self.tarama or self.guncelleniyor):
            self.sweep_id = 0
            return False
        self.sweep_step += 1
        self.bar.adim(self.sweep_step)
        return True

    # -- tarama sayfasi ------------------------------------------------------------

    def yas_metni(self, gun):
        return self.t("age_today") if gun == 0 else self.t("age_days", gun=gun)

    def build_scan_page(self, holder):
        self.giris(holder, "scan_title", "scan_intro")
        bilgi = M.tanim_bilgisi()
        clamav_var = bool(M.clamscan_yolu())

        # tanim durumu notu
        if not clamav_var:
            kutu, _ = tema.not_kutusu(self.t("no_clamav"), "hata")
            dugme = tema.dugme(self.t("install_clamav"), "ana",
                               self.magazada_clamav_kur)
            dugme.set_margin_end(14)
            kutu.pack_start(dugme, False, False, 0)
        elif bilgi["durum"] == M.TANIM_YOK:
            kutu, _ = tema.not_kutusu(self.t("no_defs_block"), "hata")
        elif bilgi["durum"] == M.TANIM_ESKI:
            kutu, _ = tema.not_kutusu(self.t("defs_note_old", gun=bilgi["yas_gun"]),
                                      "uyari")
        else:
            kutu, _ = tema.not_kutusu(self.t(
                "defs_note_ok", tarih=tarih_metni(bilgi["zaman"]),
                yas=self.yas_metni(bilgi["yas_gun"])), "basari")
        holder.pack_start(kutu, False, False, 0)

        if not self.tarama:
            son = max((k.get("tarih", 0) for k in M.gecmis()), default=0)
            ozet = Gtk.Box(spacing=12)
            ozet.set_homogeneous(True)
            for ad, deger in (
                    ("k_last", tarih_metni(son) if son else "—"),
                    ("k_quar", str(len(M.karantina_listesi()))),
                    ("k_defs", "—" if bilgi["durum"] == M.TANIM_YOK
                     else self.yas_metni(bilgi["yas_gun"]))):
                kpi = tema.KpiKutusu(self.t(ad))
                kpi.ayarla(deger, orta=(ad != "k_quar"))
                ozet.pack_start(kpi, True, True, 0)
            holder.pack_start(ozet, False, False, 0)

        if self.tarama:
            holder.pack_start(self.build_running_card(), False, False, 0)
        elif self.son_sonuc:
            holder.pack_start(self.build_result_card(), False, False, 0)

        etkin = clamav_var and bilgi["durum"] != M.TANIM_YOK and not self.tarama
        for kind, title, desc, ikon in (("hizli", "quick_title", "quick_desc", "arama"),
                                        ("ev", "home_title", "home_desc", "ev"),
                                        ("ozel", "custom_title", "custom_desc", "dosya")):
            if kind == "ozel":
                btns = [tema.dugme(self.t("pick_folder"), "ana", self.pick, True),
                        tema.dugme(self.t("pick_file"), None, self.pick, False)]
            else:
                btns = [tema.dugme(self.t("scan_btn"), "ana", self.start_scan, kind)]
            for btn in btns:
                btn.set_sensitive(etkin)
            dis, _ic = self.satir_karti(ikon, "vurgu", self.t(title), self.t(desc), btns)
            holder.pack_start(dis, False, False, 0)

    def build_running_card(self):
        dis, ic = tema.kart(18, 12, "vurgulu")
        tema.kart_basligi(ic, self.t("running_title"), None,
                          tema.dugme(self.t("stop_btn"), "tehlike", self.stop_scan))
        sayilar = Gtk.Box(spacing=48)
        for ad_anahtari, nitelik in (("k_scanned", "kpi_taranan"), ("k_found", "kpi_bulgu")):
            kolon = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            deger = tema.etiket("0", "kpi-deger")
            setattr(self, nitelik, deger)
            kolon.pack_start(deger, False, False, 0)
            kolon.pack_start(tema.etiket(self.t(ad_anahtari), "kpi-ad"), False, False, 0)
            sayilar.pack_start(kolon, False, False, 0)
        ic.pack_start(sayilar, False, False, 0)
        self.yol_etiketi = tema.etiket("", "mono")
        self.yol_etiketi.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        ic.pack_start(self.yol_etiketi, False, False, 0)
        self.refresh_counts()
        return dis

    def refresh_counts(self):
        self.ui_bekliyor = False
        if not self.tarama or self.kpi_taranan is None:
            return False
        try:
            self.kpi_taranan.set_text(f"{self.sayac['taranan']:,}".replace(
                ",", "." if self.lang == "tr" else ","))
            self.kpi_bulgu.set_text(str(self.sayac["bulgu"]))
            self.yol_etiketi.set_text(self.sayac["son"] or self.t("loading_defs"))
        except Exception:
            pass
        return False

    def build_result_card(self):
        s = self.son_sonuc
        durum = s["durum"]
        if durum == M.BULGU:
            renk, isaret, title = "kirmizi", "!", self.t("res_found_title",
                                                        b=len(s["bulgular"]))
        elif durum == M.TEMIZ:
            renk, isaret, title = "yesil", "✓", self.t("res_clean_title")
        elif durum == M.IPTAL:
            renk, isaret, title = "gri", "–", self.t("res_cancel_title")
        else:
            renk, isaret, title = "sari", "!", self.t("res_error_title")
        dis, ic = tema.kart(18, 9, "tehlikeli" if durum == M.BULGU else "")
        ust = Gtk.Box(spacing=11)
        ust.pack_start(tema.rozet(isaret, renk), False, False, 0)
        ust.pack_start(tema.etiket(title, "kart-baslik", sar=True), True, True, 0)
        ic.pack_start(ust, False, False, 0)
        if durum == M.CLAMAV_YOK:
            ic.pack_start(tema.etiket(self.t("no_clamav"), None, sar=True),
                          False, False, 0)
        else:
            ic.pack_start(tema.etiket(self.t("res_summary", n=s["taranan"], s=s["sure"]),
                                      None, sar=True), False, False, 0)
        if s.get("atlanan"):
            ic.pack_start(tema.etiket(self.t("res_skipped", k=s["atlanan"]), "soluk",
                                      sar=True), False, False, 0)
        if s.get("izinli"):
            ic.pack_start(tema.etiket(self.t("res_allowed", k=len(s["izinli"])), "soluk",
                                      sar=True), False, False, 0)
        if durum == M.TARAMA_HATASI:
            for uyari in s.get("uyarilar", [])[:5]:
                ic.pack_start(tema.etiket(uyari, "mono", sar=True, sec=True),
                              False, False, 0)
        if s["bulgular"]:
            ic.pack_start(tema.etiket(self.t("res_found_hint"), "soluk", sar=True),
                          False, False, 0)
            for bulgu in s["bulgular"]:
                ic.pack_start(Gtk.Separator(), False, False, 4)
                ic.pack_start(self.build_finding(bulgu), False, False, 0)
        return dis

    def build_finding(self, bulgu):
        row = Gtk.Box(spacing=10)
        metin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        metin.pack_start(tema.etiket(bulgu["imza"], "kart-baslik", sar=True, sec=True),
                         False, False, 0)
        yol = tema.etiket(bulgu["yol"], "mono", sar=True, sec=True)
        metin.pack_start(yol, False, False, 0)
        row.pack_start(metin, True, True, 0)
        sonuc = self.islenen.get(bulgu["yol"])
        if sonuc:
            row.pack_end(tema.etiket(sonuc, "basari-yazi"), False, False, 0)
        else:
            row.pack_end(tema.dugme(self.t("act_ignore"), "kucuk",
                                    self.on_ignore, bulgu), False, False, 0)
            row.pack_end(tema.dugme(self.t("act_delete"), "tehlike kucuk",
                                    self.on_delete, bulgu), False, False, 0)
            row.pack_end(tema.dugme(self.t("act_quarantine"), "ana kucuk",
                                    self.on_quarantine, bulgu), False, False, 0)
        return row

    # -- tarama akisi ---------------------------------------------------------------

    def pick(self, klasor):
        dialog = Gtk.FileChooserDialog(
            title=self.t("pick_folder" if klasor else "pick_file"),
            transient_for=self,
            action=(Gtk.FileChooserAction.SELECT_FOLDER if klasor
                    else Gtk.FileChooserAction.OPEN))
        dialog.add_buttons(self.t("cancel"), Gtk.ResponseType.CANCEL,
                           self.t("pick_ok"), Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser("~"))
        yol = dialog.get_filename() if dialog.run() == Gtk.ResponseType.OK else None
        dialog.destroy()
        if yol and os.path.isabs(yol) and os.path.exists(yol):
            self.start_scan("ozel", [os.path.realpath(yol)])

    def confirm(self, title, body, ok_label=None, destructive=False):
        return tema.onay_sor(self, title, body, ok_label or self.t("ok_btn"),
                             self.t("cancel"), tehlike=destructive)

    def start_scan(self, tur, yollar=None):
        if self.tarama:
            return
        if not M.clamscan_yolu():
            self.bildir("no_clamav", "hata")
            return
        if M.tanim_bilgisi()["durum"] == M.TANIM_YOK:
            self.bildir("no_defs_block", "hata")
            return
        if tur == "hizli":
            yollar = M.hizli_tarama_yollari()
        elif tur == "ev":
            yollar = [os.path.expanduser("~")]
        if not yollar:
            self.bildir("nothing_to_scan", "hata")
            return
        yeterli, mb = M.bellek_yeterli()
        if not yeterli and not self.confirm(self.t("mem_title"),
                                            self.t("mem_body", mb=mb),
                                            self.t("scan_btn")):
            return
        self.sayac = {"taranan": 0, "bulgu": 0, "son": ""}
        self.islenen = {}
        self.son_sonuc = None
        self.tarama_turu = tur
        self.tarama = M.Tarama(yollar, haric_dizinler=[M.karantina_dizini()],
                               olay=self._tarama_olayi)
        self.set_hap("scanning", "acik")
        threading.Thread(target=self._tarama_isi, args=(self.tarama,),
                         daemon=True).start()
        self.show_page("scan")

    def _tarama_olayi(self, tur, veri):
        # is parcaciginda calisir: yalnizca sayaci gunceller, arayuzu
        # en fazla 150 ms'de bir yeniler
        if tur == "temiz":
            self.sayac["taranan"] += 1
            self.sayac["son"] = veri
        elif tur == "bulgu":
            self.sayac["taranan"] += 1
            self.sayac["bulgu"] += 1
            self.sayac["son"] = veri[0]
        if not self.ui_bekliyor:
            self.ui_bekliyor = True
            GLib.timeout_add(150, self.refresh_counts)

    def _tarama_isi(self, tarama):
        sonuc = tarama.calistir()
        GLib.idle_add(self.scan_done, tarama, sonuc)

    def stop_scan(self):
        if self.tarama:
            self.tarama.iptal()

    def scan_done(self, tarama, sonuc):
        if tarama is not self.tarama:
            return False
        self.tarama = None
        self.son_sonuc = sonuc
        M.gecmise_ekle(self.tarama_turu, sonuc)
        anahtar, tur = {M.TEMIZ: ("res_clean_title", "acik"),
                        M.IPTAL: ("res_cancel_title", "kapali"),
                        M.BULGU: ("res_found_title", "hata")
                        }.get(sonuc["durum"], ("res_error_title", "uyari"))
        self.set_hap(anahtar, tur, b=len(sonuc["bulgular"]))
        if self.page == "scan":
            self.show_page("scan")
        else:
            self.update_nav()
            self.update_sweep()
        if sonuc["bulgular"]:
            self.present()
        return False

    # -- bulgu islemleri --------------------------------------------------------------

    def _islendi(self, bulgu, mesaj, tur="basari"):
        self.islenen[bulgu["yol"]] = mesaj
        self.bildir(mesaj, tur)
        self.show_page("scan")

    def on_quarantine(self, bulgu):
        kod, _kayit = M.karantinaya_al(bulgu["yol"], bulgu["imza"])
        self._islendi(bulgu, self.t("done_quarantined") if kod == M.TAMAM
                      else self.t("e_" + kod), "basari" if kod == M.TAMAM else "hata")

    def on_delete(self, bulgu):
        if not self.confirm(self.t("act_delete"),
                            self.t("confirm_delete", yol=bulgu["yol"]),
                            self.t("act_delete"), destructive=True):
            return
        kod = M.dosyayi_sil(bulgu["yol"])
        self._islendi(bulgu, self.t("done_deleted") if kod == M.TAMAM
                      else self.t("e_" + kod), "basari" if kod == M.TAMAM else "hata")

    def on_ignore(self, bulgu):
        # uc secenek: vazgec / her zaman / bir kez
        dis = {"yanit": 0}
        d = Gtk.Dialog(transient_for=self, modal=True)
        d.set_title(self.t("ignore_title"))
        d.set_resizable(False)
        alan = d.get_content_area()
        alan.set_spacing(10)
        for k in ("top", "bottom", "start", "end"):
            getattr(alan, f"set_margin_{k}")(18)
        alan.pack_start(tema.etiket(self.t("ignore_title"), "buyuk-baslik", sar=True,
                                    genislik=50), False, False, 0)
        alan.pack_start(tema.etiket(self.t("ignore_body", yol=bulgu["yol"]), "soluk",
                                    sar=True, genislik=56), False, False, 0)
        satir = Gtk.Box(spacing=8)
        satir.set_margin_top(8)

        def sec(kod):
            dis["yanit"] = kod
            d.response(Gtk.ResponseType.OK)

        satir.pack_end(tema.dugme(self.t("ignore_once"), "ana", sec, 1), False, False, 0)
        satir.pack_end(tema.dugme(self.t("ignore_always"), None, sec, 2), False, False, 0)
        satir.pack_end(tema.dugme(self.t("cancel"), None, sec, 0), False, False, 0)
        alan.pack_start(satir, False, False, 0)
        d.show_all()
        d.run()
        d.destroy()
        yanit = dis["yanit"]
        if yanit == 1:
            self._islendi(bulgu, self.t("done_ignored"), "bilgi")
        elif yanit == 2:
            kod = M.izin_listesine_ekle(bulgu["yol"], bulgu["imza"])
            self._islendi(bulgu, self.t("done_allowed") if kod == M.TAMAM
                          else self.t("e_" + kod), "basari" if kod == M.TAMAM else "hata")

    # -- karantina sayfasi ----------------------------------------------------------------

    def build_quarantine_page(self, holder):
        self.giris(holder, "q_title", "q_intro")
        kayitlar = sorted(M.karantina_listesi(), key=lambda k: -k.get("tarih", 0))
        if not kayitlar:
            dis, ic = tema.kart(10, 0)
            ic.pack_start(tema.bos_durum("kilit", self.t("q_empty")), False, False, 0)
            holder.pack_start(dis, False, False, 0)
        for kayit in kayitlar:
            alt = (kayit["asil_yol"] + "\n" +
                   self.t("q_meta", imza=kayit.get("imza", "?"),
                          tarih=tarih_metni(kayit["tarih"])))
            dis, _ic = self.satir_karti(
                "kilit", "sari", os.path.basename(kayit["asil_yol"]), alt,
                [tema.dugme(self.t("q_delete"), "tehlike kucuk", self.on_q_delete, kayit),
                 tema.dugme(self.t("q_restore"), "kucuk", self.on_q_restore, kayit)])
            holder.pack_start(dis, False, False, 0)

        izinler = sorted(M.izin_listesi(), key=lambda k: -k.get("tarih", 0))
        if not izinler:
            return
        baslik = tema.etiket(self.t("a_title"), "buyuk-baslik")
        baslik.set_margin_top(12)
        holder.pack_start(baslik, False, False, 0)
        holder.pack_start(tema.etiket(self.t("a_intro"), "soluk", sar=True, genislik=110),
                          False, False, 0)
        for kayit in izinler:
            alt = (kayit.get("yol", "") + "\n" +
                   self.t("q_meta", imza=kayit.get("imza", "?"),
                          tarih=tarih_metni(kayit.get("tarih", 0))))
            dis, _ic = self.satir_karti(
                "onay", "yesil", os.path.basename(kayit.get("yol", "?")), alt,
                [tema.dugme(self.t("a_remove"), "kucuk", self.on_a_remove, kayit)])
            holder.pack_start(dis, False, False, 0)

    def on_a_remove(self, kayit):
        kod = M.izin_listesinden_cikar(kayit.get("sha256"))
        self.bildir("a_removed" if kod == M.TAMAM else "e_" + kod,
                    "basari" if kod == M.TAMAM else "hata")
        self.show_page("quarantine")

    def on_q_restore(self, kayit):
        if not self.confirm(self.t("q_restore"),
                            self.t("confirm_restore", yol=kayit["asil_yol"]),
                            self.t("q_restore")):
            return
        kod, yol = M.geri_yukle(kayit["id"])
        if kod == M.TAMAM:
            self.bildir(self.t("restored_to", yol=yol), "basari")
        else:
            self.bildir("e_" + kod, "hata")
        self.show_page("quarantine")

    def on_q_delete(self, kayit):
        if not self.confirm(self.t("q_delete"),
                            self.t("confirm_delete", yol=kayit["asil_yol"]),
                            self.t("q_delete"), destructive=True):
            return
        kod = M.karantinadan_sil(kayit["id"])
        self.bildir("done_deleted" if kod == M.TAMAM else "e_" + kod,
                    "basari" if kod == M.TAMAM else "hata")
        self.show_page("quarantine")

    # -- tanimlar sayfasi -------------------------------------------------------------------

    def build_defs_page(self, holder):
        self.giris(holder, "d_title", "d_intro")
        bilgi = M.tanim_bilgisi()
        dis, ic = tema.kart(18, 9)
        top = Gtk.Box(spacing=11)
        renk, anahtar, ikon = {
            M.TANIM_GUNCEL: ("yesil", "d_badge_ok", "onay"),
            M.TANIM_ESKI: ("sari", "d_badge_old", "uyari"),
            M.TANIM_YOK: ("kirmizi", "d_badge_none", "uyari")}[bilgi["durum"]]
        top.pack_start(tema.ikon_kutusu(ikon, renk, 40), False, False, 0)
        baslik = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        baslik.set_valign(Gtk.Align.CENTER)
        baslik.pack_start(tema.etiket(self.t("d_card"), "kart-baslik"), False, False, 0)
        r = tema.rozet(self.t(anahtar), renk)
        r.set_halign(Gtk.Align.START)
        baslik.pack_start(r, False, False, 0)
        top.pack_start(baslik, True, True, 0)
        btn = tema.dugme(self.t("d_update"), "ana", self.start_update)
        btn.set_sensitive(not self.guncelleniyor and bool(M.freshclam_yolu()))
        top.pack_end(btn, False, False, 0)
        ic.pack_start(top, False, False, 0)
        ic.pack_start(Gtk.Separator(), False, False, 4)

        if bilgi["durum"] == M.TANIM_YOK:
            ic.pack_start(tema.etiket(self.t("d_none"), None, sar=True), False, False, 0)
        else:
            ic.pack_start(tema.etiket(self.t(
                "d_date", tarih=tarih_metni(bilgi["zaman"]),
                yas=self.yas_metni(bilgi["yas_gun"])), None, sar=True), False, False, 0)
            dosyalar = ", ".join(f"{d['ad']} {d['surum']}" for d in bilgi["dosyalar"])
            imza = f"{bilgi['imza']:,}".replace(",", "." if self.lang == "tr" else ",")
            ic.pack_start(tema.etiket(self.t("d_sigs", imza=imza, dosyalar=dosyalar),
                                      "soluk", sar=True), False, False, 0)
        if bilgi["durum"] == M.TANIM_ESKI:
            ic.pack_start(tema.etiket(self.t("defs_note_old", gun=bilgi["yas_gun"]),
                                      "soluk", sar=True), False, False, 0)
        ic.pack_start(tema.etiket(self.t("d_update_note"), "silik", sar=True),
                      False, False, 0)
        if is_live():
            ic.pack_start(tema.etiket(self.t("d_live_note"), "silik", sar=True),
                          False, False, 0)
        if self.guncelleme_mesaji:
            sonuc = Gtk.Box(spacing=10)
            sonuc.pack_start(tema.etiket(self.guncelleme_mesaji, "vurgu-yazi", sar=True),
                             True, True, 0)
            if self.guncelleme_ciktisi:
                sonuc.pack_end(tema.dugme(self.t("show_output"), "kucuk", self.show_output),
                               False, False, 0)
            ic.pack_start(sonuc, False, False, 0)
        holder.pack_start(dis, False, False, 0)

    def start_update(self):
        if self.guncelleniyor:
            return
        self.guncelleniyor = True
        self.guncelleme_mesaji = None
        self.set_hap("d_updating", "acik")

        def isci():
            try:
                proc = subprocess.run(M.guncelleme_komutu(), stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True,
                                      errors="replace", timeout=1800)
                kod, cikti = proc.returncode, proc.stdout
            except subprocess.TimeoutExpired:
                kod, cikti = 124, "timed out"
            except OSError:
                kod, cikti = 127, ""
            GLib.idle_add(self.update_done, kod, cikti)

        threading.Thread(target=isci, daemon=True).start()
        self.show_page()

    def update_done(self, kod, cikti):
        self.guncelleniyor = False
        sonuc = M.guncelleme_sonucu(kod, cikti)
        self.guncelleme_mesaji = self.t("u_" + sonuc)
        self.guncelleme_ciktisi = (cikti or "") if sonuc not in (
            M.GUNCELLENDI, M.ZATEN_GUNCEL, M.IPTAL) else ""
        self.set_hap("ready", "kapali")
        self.bildir(self.guncelleme_mesaji,
                    "basari" if sonuc in (M.GUNCELLENDI, M.ZATEN_GUNCEL) else "hata")
        self.show_page()
        return False

    def show_output(self):
        dialog = Gtk.Dialog(title=self.t("d_card"), transient_for=self, modal=True)
        dialog.add_button(self.t("close"), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(680, 380)
        view = Gtk.TextView()
        view.set_editable(False)
        view.set_monospace(True)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_left_margin(10)
        view.set_right_margin(10)
        view.set_top_margin(8)
        view.get_buffer().set_text(self.guncelleme_ciktisi[-8000:])
        scroller = Gtk.ScrolledWindow()
        scroller.add(view)
        scroller.set_border_width(10)
        dialog.get_content_area().pack_start(scroller, True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    # -- gecmis sayfasi ----------------------------------------------------------------------

    def build_history_page(self, holder):
        kayitlar = M.gecmis()
        self.giris(holder, "h_title", "h_intro", n=M.GECMIS_SINIRI)
        if not kayitlar:
            dis, ic = tema.kart(10, 0)
            ic.pack_start(tema.bos_durum("saat", self.t("h_empty")), False, False, 0)
            holder.pack_start(dis, False, False, 0)
            return
        dis, ic = tema.kart(14, 8)
        for i, kayit in enumerate(kayitlar):
            if i:
                ic.pack_start(Gtk.Separator(), False, False, 2)
            row = Gtk.Box(spacing=12)
            durum = kayit.get("durum")
            renk = {M.TEMIZ: "yesil", M.BULGU: "kirmizi", M.IPTAL: "gri"}.get(durum, "sari")
            isaret = {"yesil": "✓", "kirmizi": "!", "gri": "–"}.get(renk, "!")
            row.pack_start(tema.rozet(isaret, renk), False, False, 0)
            metin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            tur = METIN.get("kind_" + str(kayit.get("tur")), METIN["kind_ozel"])[self.lang]
            metin.pack_start(tema.etiket(f"{tur} · {tarih_metni(kayit['tarih'])}",
                                         "kart-baslik"), False, False, 0)
            metin.pack_start(tema.etiket(self.t("h_row", n=kayit.get("taranan", 0),
                                                b=kayit.get("bulgu", 0),
                                                s=kayit.get("sure", 0)), "soluk"),
                             False, False, 0)
            row.pack_start(metin, True, True, 0)
            ic.pack_start(row, False, False, 0)
        holder.pack_start(dis, False, False, 0)

    # -- olaylar --------------------------------------------------------------------------------

    def on_nav(self, key):
        self.show_page(key)

    def on_lang_changed(self, combo):
        secilen = combo.get_active_id()
        if secilen and secilen != self.lang:
            self.lang = self.settings["lang"] = secilen
            save_settings(self.settings)
            self.retranslate()

    def on_theme_toggled(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings["theme"] = self.theme
        save_settings(self.settings)
        tema.uygula(self.theme, VURGU)
        self.retranslate()
        self.queue_draw()

    def retranslate(self):
        self.set_title(self.t("app_title"))
        self.kabuk.marka_ayarla(self.t("app_title"), self.t("header_sub"))
        self.kabuk.bolum_metni("koruma", self.t("sec_protect"))
        self.kabuk.bolum_metni("bakim", self.t("sec_maint"))
        self.theme_btn.set_label("☀" if self.theme == "dark" else "☾")
        self.theme_btn.set_tooltip_text(self.t("theme_light") if self.theme == "dark"
                                        else self.t("theme_dark"))
        self.set_hap()
        self.show_page()

    def on_destroy(self, _widget):
        if self.tarama:
            self.tarama.iptal()
        if self.sweep_id:
            GLib.source_remove(self.sweep_id)
        Gtk.main_quit()


def main():
    yollar = M.komut_satiri_yollari(sys.argv[1:])
    window = CaroteneWindow(load_settings())
    window.show_all()
    window.kabuk.sec("scan")
    if yollar:
        GLib.idle_add(lambda: window.start_scan("ozel", yollar) and False)
    elif yollar is not None:
        window.bildir("args_none", "hata")
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
