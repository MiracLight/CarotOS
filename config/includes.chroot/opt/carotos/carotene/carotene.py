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
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango  # noqa: E402

from bekleme_cubugu import SweepBar  # noqa: E402


# ---------------------------------------------------------------------------
# Metinler
# ---------------------------------------------------------------------------

METIN = {
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

STATUS_CLASS = {"ok": "badge-ok", "warn": "badge-warn", "fail": "badge-fail",
                "info": "badge-info"}


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

    ACCENT = "#87979B"
    C_OK = "#4c9a6a"
    C_WARN = "#c8952a"
    C_FAIL = "#c2554f"
    C_INFO = "#6d7a7e"

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

        self.bars = []
        self.sweep_id = 0
        self.sweep_step = 0

        self.set_default_size(980, 680)
        self.set_size_request(820, 560)
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

        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        root.pack_start(self.build_header(), False, False, 0)
        root.pack_start(Gtk.Separator(), False, False, 0)
        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(split, True, True, 0)
        split.pack_start(self.build_sidebar(), False, False, 0)
        split.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL),
                         False, False, 0)
        self.content = Gtk.ScrolledWindow()
        self.content.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        split.pack_start(self.content, True, True, 0)
        root.pack_start(Gtk.Separator(), False, False, 0)
        root.pack_start(self.build_statusbar(), False, False, 0)

        self.apply_theme()
        self.retranslate()

    def t(self, anahtar, **kw):
        metin = METIN[anahtar][self.lang]
        return metin.format(**kw) if kw else metin

    # -- iskelet -------------------------------------------------------------

    def build_header(self):
        # Ust bant: kenarlari yuvarlatilmis tek parca. Uygulama adi pencere
        # basliginda yazdigi icin burada tekrar edilmez; simge ve tur yazilir.
        dis = Gtk.Box()
        dis.set_margin_top(10)
        dis.set_margin_bottom(10)
        dis.set_margin_start(12)
        dis.set_margin_end(12)
        bant = Gtk.Box()
        bant.get_style_context().add_class("header")
        dis.pack_start(bant, True, True, 0)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(7)
        box.set_margin_bottom(7)
        box.set_margin_start(12)
        box.set_margin_end(8)
        bant.pack_start(box, True, True, 0)

        logo = find_logo()
        if logo:
            try:
                simge = Gtk.Image.new_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_size(logo, 28, 28))
                box.pack_start(simge, False, False, 0)
            except GLib.Error:
                pass
        self.title_label = Gtk.Label(xalign=0.0)
        self.title_label.get_style_context().add_class("header-sub")
        box.pack_start(self.title_label, False, False, 0)

        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append("tr", "Türkçe")
        self.lang_combo.append("en", "English")
        self.lang_combo.set_active_id(self.lang)
        self.lang_combo.connect("changed", self.on_lang_changed)
        box.pack_end(self.lang_combo, False, False, 0)

        self.theme_btn = Gtk.Button()
        self.theme_btn.connect("clicked", self.on_theme_toggled)
        box.pack_end(self.theme_btn, False, False, 0)
        return dis

    def build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("sidebar")
        box.set_size_request(210, -1)
        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("nav-list")
        self.listbox.connect("row-selected", self.on_nav)
        box.pack_start(self.listbox, True, True, 0)
        self.nav_rows = []
        for key in ("scan", "quarantine", "defs", "history"):
            row = Gtk.ListBoxRow()
            row.key = key
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            inner.set_border_width(12)
            row.name_label = Gtk.Label(xalign=0.0)
            row.name_label.get_style_context().add_class("nav-title")
            row.sub_label = Gtk.Label(xalign=0.0)
            row.sub_label.get_style_context().add_class("nav-sub")
            inner.pack_start(row.name_label, False, False, 0)
            inner.pack_start(row.sub_label, False, False, 0)
            row.add(inner)
            self.listbox.add(row)
            self.nav_rows.append(row)
        return box

    def build_statusbar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_border_width(9)
        self.status = Gtk.Label(xalign=0.0)
        self.status.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.status.get_style_context().add_class("status-label")
        box.pack_start(self.status, True, True, 0)
        self.spinner = Gtk.Spinner()
        box.pack_end(self.spinner, False, False, 0)
        return box

    # -- ortak parcalar ---------------------------------------------------------

    def label(self, text, cls=None, wrap=True, select=False):
        lab = Gtk.Label(label=text, xalign=0.0)
        if wrap:
            lab.set_line_wrap(True)
            lab.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            lab.set_max_width_chars(90)
        if select:
            lab.set_selectable(True)
        if cls:
            lab.get_style_context().add_class(cls)
        return lab

    def card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.get_style_context().add_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        inner.set_margin_top(18)
        inner.set_margin_bottom(18)
        inner.set_margin_start(22)
        inner.set_margin_end(22)
        card.pack_start(inner, True, True, 0)
        return card, inner

    def badge(self, text, kind):
        lab = Gtk.Label(label=text)
        lab.get_style_context().add_class("badge")
        lab.get_style_context().add_class(STATUS_CLASS[kind])
        lab.set_valign(Gtk.Align.CENTER)
        return lab

    def button(self, text, callback, *args, style=None):
        btn = Gtk.Button(label=text)
        btn.set_valign(Gtk.Align.CENTER)
        if style:
            btn.get_style_context().add_class(style)
        btn.connect("clicked", lambda _b: callback(*args))
        return btn

    def new_bar(self):
        bar = SweepBar(self.ACCENT)
        self.bars.append(bar)
        bar.show()
        return bar

    def page_header(self, holder, title, intro):
        holder.pack_start(self.label(title, "page-title", wrap=False), False, False, 0)
        holder.pack_start(self.label(intro, "page-subtitle"), False, False, 0)

    # -- sayfa gecisi ------------------------------------------------------------

    def show_page(self, key=None):
        self.page = key or self.page
        self.bars = []
        child = self.content.get_child()
        if child:
            self.content.remove(child)
        holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        holder.set_border_width(26)
        {"scan": self.build_scan_page, "quarantine": self.build_quarantine_page,
         "defs": self.build_defs_page, "history": self.build_history_page
         }[self.page](holder)
        self.content.add(holder)
        holder.show_all()
        self.update_nav()
        self.update_sweep()

    def update_nav(self):
        bilgi = M.tanim_bilgisi()
        alt = {
            "scan": (self.t("scanning") if self.tarama else ""),
            "quarantine": str(len(M.karantina_listesi())),
            "defs": {M.TANIM_GUNCEL: self.t("d_badge_ok"),
                     M.TANIM_ESKI: self.t("d_badge_old"),
                     M.TANIM_YOK: self.t("d_badge_none")}[bilgi["durum"]],
            "history": str(len(M.gecmis())),
        }
        if self.guncelleniyor:
            alt["defs"] = self.t("d_updating")
        for row in self.nav_rows:
            row.name_label.set_text(self.t("nav_" + row.key))
            row.sub_label.set_text(alt[row.key] or "—")

    def update_sweep(self):
        if (self.tarama or self.guncelleniyor) and not self.sweep_id:
            self.sweep_id = GLib.timeout_add(45, self._sweep)
            self.spinner.start()
        elif not (self.tarama or self.guncelleniyor):
            if self.sweep_id:
                GLib.source_remove(self.sweep_id)
                self.sweep_id = 0
            self.spinner.stop()

    def _sweep(self):
        if not (self.tarama or self.guncelleniyor):
            self.sweep_id = 0
            return False
        self.sweep_step += 1
        for bar in self.bars:
            bar.adim(self.sweep_step)
        return True

    # -- tarama sayfasi ------------------------------------------------------------

    def yas_metni(self, gun):
        return self.t("age_today") if gun == 0 else self.t("age_days", gun=gun)

    def build_scan_page(self, holder):
        self.page_header(holder, self.t("scan_title"), self.t("scan_intro"))
        bilgi = M.tanim_bilgisi()
        clamav_var = bool(M.clamscan_yolu())

        # tanim durumu notu
        if not clamav_var:
            holder.pack_start(self.note(self.t("no_clamav"), "fail"), False, False, 0)
        elif bilgi["durum"] == M.TANIM_YOK:
            holder.pack_start(self.note(self.t("no_defs_block"), "fail"), False, False, 0)
        elif bilgi["durum"] == M.TANIM_ESKI:
            holder.pack_start(self.note(self.t("defs_note_old", gun=bilgi["yas_gun"]),
                                        "warn"), False, False, 0)
        else:
            holder.pack_start(self.note(self.t(
                "defs_note_ok", tarih=tarih_metni(bilgi["zaman"]),
                yas=self.yas_metni(bilgi["yas_gun"])), "ok"), False, False, 0)

        if self.tarama:
            holder.pack_start(self.build_running_card(), False, False, 0)
        elif self.son_sonuc:
            holder.pack_start(self.build_result_card(), False, False, 0)

        etkin = clamav_var and bilgi["durum"] != M.TANIM_YOK and not self.tarama
        for kind, title, desc in (("hizli", "quick_title", "quick_desc"),
                                  ("ev", "home_title", "home_desc"),
                                  ("ozel", "custom_title", "custom_desc")):
            card, inner = self.card()
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
            top.pack_start(self.label(self.t(title), "card-title"), True, True, 0)
            if kind == "ozel":
                btns = [self.button(self.t("pick_file"), self.pick, False),
                        self.button(self.t("pick_folder"), self.pick, True,
                                    style="suggested-action")]
            else:
                btns = [self.button(self.t("scan_btn"), self.start_scan, kind, None,
                                    style="suggested-action")]
            for btn in btns:
                btn.set_sensitive(etkin)
                top.pack_end(btn, False, False, 0)
            inner.pack_start(top, False, False, 0)
            inner.pack_start(self.label(self.t(desc), "why-text"), False, False, 0)
            holder.pack_start(card, False, False, 0)

    def note(self, text, kind):
        box = Gtk.Box()
        box.get_style_context().add_class("note-box")
        box.get_style_context().add_class("note-" + kind)
        lab = self.label(text, "note-text")
        lab.set_margin_top(10)
        lab.set_margin_bottom(10)
        lab.set_margin_start(14)
        lab.set_margin_end(14)
        box.pack_start(lab, True, True, 0)
        return box

    def build_running_card(self):
        card, inner = self.card()
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
        top.pack_start(self.label(self.t("running_title"), "card-title"), True, True, 0)
        top.pack_end(self.button(self.t("stop_btn"), self.stop_scan,
                                 style="destructive-action"), False, False, 0)
        top.pack_end(self.new_bar(), False, False, 0)
        inner.pack_start(top, False, False, 0)
        self.count_label = self.label("", None)
        self.path_label = self.label("", "caption-text", wrap=False)
        self.path_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        inner.pack_start(self.count_label, False, False, 0)
        inner.pack_start(self.path_label, False, False, 0)
        self.refresh_counts()
        return card

    def refresh_counts(self):
        self.ui_bekliyor = False
        if not self.tarama or not hasattr(self, "count_label"):
            return False
        try:
            self.count_label.set_text(self.t("running_counts",
                                             n=self.sayac["taranan"],
                                             b=self.sayac["bulgu"]))
            self.path_label.set_text(self.sayac["son"] or self.t("loading_defs"))
        except Exception:
            pass
        return False

    def build_result_card(self):
        s = self.son_sonuc
        card, inner = self.card()
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
        durum = s["durum"]
        if durum == M.BULGU:
            badge, title = self.badge("!", "fail"), self.t("res_found_title",
                                                         b=len(s["bulgular"]))
        elif durum == M.TEMIZ:
            badge, title = self.badge("✓", "ok"), self.t("res_clean_title")
        elif durum == M.IPTAL:
            badge, title = self.badge("–", "info"), self.t("res_cancel_title")
        else:
            badge, title = self.badge("!", "warn"), self.t("res_error_title")
        top.pack_start(badge, False, False, 0)
        top.pack_start(self.label(title, "card-title"), True, True, 0)
        inner.pack_start(top, False, False, 0)
        if durum == M.CLAMAV_YOK:
            inner.pack_start(self.label(self.t("no_clamav")), False, False, 0)
        else:
            inner.pack_start(self.label(self.t("res_summary", n=s["taranan"],
                                               s=s["sure"])), False, False, 0)
        if s.get("atlanan"):
            inner.pack_start(self.label(self.t("res_skipped", k=s["atlanan"]),
                                        "why-text"), False, False, 0)
        if s.get("izinli"):
            inner.pack_start(self.label(self.t("res_allowed", k=len(s["izinli"])),
                                        "why-text"), False, False, 0)
        if durum == M.TARAMA_HATASI:
            for uyari in s.get("uyarilar", [])[:5]:
                inner.pack_start(self.label(uyari, "code-text", select=True),
                                 False, False, 0)
        if s["bulgular"]:
            inner.pack_start(self.label(self.t("res_found_hint"), "why-text"),
                             False, False, 0)
            for bulgu in s["bulgular"]:
                inner.pack_start(Gtk.Separator(), False, False, 4)
                inner.pack_start(self.build_finding(bulgu), False, False, 0)
        return card

    def build_finding(self, bulgu):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        metin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        metin.pack_start(self.label(bulgu["imza"], "card-title", select=True),
                         False, False, 0)
        metin.pack_start(self.label(bulgu["yol"], "code-text", select=True),
                         False, False, 0)
        row.pack_start(metin, True, True, 0)
        sonuc = self.islenen.get(bulgu["yol"])
        if sonuc:
            row.pack_end(self.label(sonuc, "why-text", wrap=False), False, False, 0)
        else:
            row.pack_end(self.button(self.t("act_ignore"), self.on_ignore, bulgu),
                         False, False, 0)
            row.pack_end(self.button(self.t("act_delete"), self.on_delete, bulgu,
                                     style="destructive-action"), False, False, 0)
            row.pack_end(self.button(self.t("act_quarantine"), self.on_quarantine,
                                     bulgu, style="suggested-action"), False, False, 0)
        box.pack_start(row, False, False, 0)
        return box

    # -- tarama akisi ---------------------------------------------------------------

    def pick(self, klasor):
        dialog = Gtk.FileChooserDialog(
            title=self.t("pick_folder" if klasor else "pick_file"),
            transient_for=self,
            action=(Gtk.FileChooserAction.SELECT_FOLDER if klasor
                    else Gtk.FileChooserAction.OPEN))
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser("~"))
        yol = dialog.get_filename() if dialog.run() == Gtk.ResponseType.OK else None
        dialog.destroy()
        if yol and os.path.isabs(yol) and os.path.exists(yol):
            self.start_scan("ozel", [os.path.realpath(yol)])

    def confirm(self, title, body, ok_label=None, destructive=False):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True,
                                   message_type=Gtk.MessageType.QUESTION,
                                   buttons=Gtk.ButtonsType.NONE, text=title)
        dialog.format_secondary_text(body)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        ok = dialog.add_button(ok_label or Gtk.STOCK_OK, Gtk.ResponseType.OK)
        if destructive:
            ok.get_style_context().add_class("destructive-action")
        yanit = dialog.run()
        dialog.destroy()
        return yanit == Gtk.ResponseType.OK

    def start_scan(self, tur, yollar=None):
        if self.tarama:
            return
        if not M.clamscan_yolu():
            self.status.set_text(self.t("no_clamav"))
            return
        if M.tanim_bilgisi()["durum"] == M.TANIM_YOK:
            self.status.set_text(self.t("no_defs_block"))
            return
        if tur == "hizli":
            yollar = M.hizli_tarama_yollari()
        elif tur == "ev":
            yollar = [os.path.expanduser("~")]
        if not yollar:
            self.status.set_text(self.t("nothing_to_scan"))
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
        self.status.set_text(self.t("scanning"))
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
        anahtar = {M.TEMIZ: "res_clean_title", M.IPTAL: "res_cancel_title",
                   M.BULGU: "res_found_title"}.get(sonuc["durum"], "res_error_title")
        self.status.set_text(self.t(anahtar, b=len(sonuc["bulgular"])))
        if self.page == "scan":
            self.show_page("scan")
        else:
            self.update_nav()
            self.update_sweep()
        if sonuc["bulgular"]:
            self.present()
        return False

    # -- bulgu islemleri --------------------------------------------------------------

    def _islendi(self, bulgu, mesaj):
        self.islenen[bulgu["yol"]] = mesaj
        self.status.set_text(mesaj)
        self.show_page("scan")

    def on_quarantine(self, bulgu):
        kod, _kayit = M.karantinaya_al(bulgu["yol"], bulgu["imza"])
        self._islendi(bulgu, self.t("done_quarantined") if kod == M.TAMAM
                      else self.t("e_" + kod))

    def on_delete(self, bulgu):
        if not self.confirm(self.t("act_delete"),
                            self.t("confirm_delete", yol=bulgu["yol"]),
                            self.t("act_delete"), destructive=True):
            return
        kod = M.dosyayi_sil(bulgu["yol"])
        self._islendi(bulgu, self.t("done_deleted") if kod == M.TAMAM
                      else self.t("e_" + kod))

    def on_ignore(self, bulgu):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True,
                                   message_type=Gtk.MessageType.QUESTION,
                                   buttons=Gtk.ButtonsType.NONE,
                                   text=self.t("ignore_title"))
        dialog.format_secondary_text(self.t("ignore_body", yol=bulgu["yol"]))
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(self.t("ignore_always"), 2)
        dialog.add_button(self.t("ignore_once"), 1)
        yanit = dialog.run()
        dialog.destroy()
        if yanit == 1:
            self._islendi(bulgu, self.t("done_ignored"))
        elif yanit == 2:
            kod = M.izin_listesine_ekle(bulgu["yol"], bulgu["imza"])
            self._islendi(bulgu, self.t("done_allowed") if kod == M.TAMAM
                          else self.t("e_" + kod))

    # -- karantina sayfasi ----------------------------------------------------------------

    def build_quarantine_page(self, holder):
        self.page_header(holder, self.t("q_title"), self.t("q_intro"))
        kayitlar = sorted(M.karantina_listesi(), key=lambda k: -k.get("tarih", 0))
        if not kayitlar:
            holder.pack_start(self.label(self.t("q_empty"), "why-text"), False, False, 0)
        for kayit in kayitlar:
            card, inner = self.card()
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            metin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            metin.pack_start(self.label(os.path.basename(kayit["asil_yol"]),
                                        "card-title"), False, False, 0)
            metin.pack_start(self.label(kayit["asil_yol"], "code-text", select=True),
                             False, False, 0)
            metin.pack_start(self.label(self.t("q_meta", imza=kayit.get("imza", "?"),
                                               tarih=tarih_metni(kayit["tarih"])),
                                        "why-text"), False, False, 0)
            row.pack_start(metin, True, True, 0)
            row.pack_end(self.button(self.t("q_delete"), self.on_q_delete, kayit,
                                     style="destructive-action"), False, False, 0)
            row.pack_end(self.button(self.t("q_restore"), self.on_q_restore, kayit),
                         False, False, 0)
            inner.pack_start(row, False, False, 0)
            holder.pack_start(card, False, False, 0)

        izinler = sorted(M.izin_listesi(), key=lambda k: -k.get("tarih", 0))
        if not izinler:
            return
        baslik = self.label(self.t("a_title"), "page-title", wrap=False)
        baslik.set_margin_top(14)
        holder.pack_start(baslik, False, False, 0)
        holder.pack_start(self.label(self.t("a_intro"), "page-subtitle"), False, False, 0)
        for kayit in izinler:
            card, inner = self.card()
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            metin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            metin.pack_start(self.label(os.path.basename(kayit.get("yol", "?")),
                                        "card-title"), False, False, 0)
            metin.pack_start(self.label(kayit.get("yol", ""), "code-text", select=True),
                             False, False, 0)
            metin.pack_start(self.label(self.t("q_meta", imza=kayit.get("imza", "?"),
                                               tarih=tarih_metni(kayit.get("tarih", 0))),
                                        "why-text"), False, False, 0)
            row.pack_start(metin, True, True, 0)
            row.pack_end(self.button(self.t("a_remove"), self.on_a_remove, kayit),
                         False, False, 0)
            inner.pack_start(row, False, False, 0)
            holder.pack_start(card, False, False, 0)

    def on_a_remove(self, kayit):
        kod = M.izin_listesinden_cikar(kayit.get("sha256"))
        self.status.set_text(self.t("a_removed") if kod == M.TAMAM
                             else self.t("e_" + kod))
        self.show_page("quarantine")

    def on_q_restore(self, kayit):
        if not self.confirm(self.t("q_restore"),
                            self.t("confirm_restore", yol=kayit["asil_yol"]),
                            self.t("q_restore")):
            return
        kod, yol = M.geri_yukle(kayit["id"])
        self.status.set_text(self.t("restored_to", yol=yol) if kod == M.TAMAM
                             else self.t("e_" + kod))
        self.show_page("quarantine")

    def on_q_delete(self, kayit):
        if not self.confirm(self.t("q_delete"),
                            self.t("confirm_delete", yol=kayit["asil_yol"]),
                            self.t("q_delete"), destructive=True):
            return
        kod = M.karantinadan_sil(kayit["id"])
        self.status.set_text(self.t("done_deleted") if kod == M.TAMAM
                             else self.t("e_" + kod))
        self.show_page("quarantine")

    # -- tanimlar sayfasi -------------------------------------------------------------------

    def build_defs_page(self, holder):
        self.page_header(holder, self.t("d_title"), self.t("d_intro"))
        bilgi = M.tanim_bilgisi()
        card, inner = self.card()
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
        kind, key = {M.TANIM_GUNCEL: ("ok", "d_badge_ok"),
                     M.TANIM_ESKI: ("warn", "d_badge_old"),
                     M.TANIM_YOK: ("fail", "d_badge_none")}[bilgi["durum"]]
        top.pack_start(self.badge(self.t(key), kind), False, False, 0)
        top.pack_start(self.label(self.t("d_card"), "card-title"), True, True, 0)
        btn = self.button(self.t("d_update"), self.start_update, style="suggested-action")
        btn.set_sensitive(not self.guncelleniyor and bool(M.freshclam_yolu()))
        top.pack_end(btn, False, False, 0)
        if self.guncelleniyor:
            top.pack_end(self.new_bar(), False, False, 0)
        inner.pack_start(top, False, False, 0)

        if bilgi["durum"] == M.TANIM_YOK:
            inner.pack_start(self.label(self.t("d_none")), False, False, 0)
        else:
            inner.pack_start(self.label(self.t(
                "d_date", tarih=tarih_metni(bilgi["zaman"]),
                yas=self.yas_metni(bilgi["yas_gun"]))), False, False, 0)
            dosyalar = ", ".join(f"{d['ad']} {d['surum']}" for d in bilgi["dosyalar"])
            imza = f"{bilgi['imza']:,}".replace(",", "." if self.lang == "tr" else ",")
            inner.pack_start(self.label(self.t("d_sigs", imza=imza, dosyalar=dosyalar),
                                        "why-text"), False, False, 0)
        if bilgi["durum"] == M.TANIM_ESKI:
            inner.pack_start(self.label(self.t("defs_note_old", gun=bilgi["yas_gun"]),
                                        "why-text"), False, False, 0)
        inner.pack_start(self.label(self.t("d_update_note"), "caption-text"),
                         False, False, 0)
        if is_live():
            inner.pack_start(self.label(self.t("d_live_note"), "caption-text"),
                             False, False, 0)
        if self.guncelleme_mesaji:
            sonuc = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            sonuc.pack_start(self.label(self.guncelleme_mesaji), True, True, 0)
            if self.guncelleme_ciktisi:
                sonuc.pack_end(self.button(self.t("show_output"), self.show_output),
                               False, False, 0)
            inner.pack_start(sonuc, False, False, 0)
        holder.pack_start(card, False, False, 0)

    def start_update(self):
        if self.guncelleniyor:
            return
        self.guncelleniyor = True
        self.guncelleme_mesaji = None
        self.status.set_text(self.t("d_updating"))

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
        self.status.set_text(self.guncelleme_mesaji)
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
        self.page_header(holder, self.t("h_title"),
                         self.t("h_intro", n=M.GECMIS_SINIRI))
        if not kayitlar:
            holder.pack_start(self.label(self.t("h_empty"), "why-text"), False, False, 0)
            return
        card, inner = self.card()
        for i, kayit in enumerate(kayitlar):
            if i:
                inner.pack_start(Gtk.Separator(), False, False, 2)
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            durum = kayit.get("durum")
            kind = {M.TEMIZ: "ok", M.BULGU: "fail", M.IPTAL: "info"}.get(durum, "warn")
            isaret = {"ok": "✓", "fail": "!", "info": "–"}.get(kind, "!")
            row.pack_start(self.badge(isaret, kind), False, False, 0)
            metin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            tur = METIN.get("kind_" + str(kayit.get("tur")), METIN["kind_ozel"])[self.lang]
            metin.pack_start(self.label(f"{tur} · {tarih_metni(kayit['tarih'])}",
                                        "card-title"), False, False, 0)
            metin.pack_start(self.label(self.t("h_row", n=kayit.get("taranan", 0),
                                               b=kayit.get("bulgu", 0),
                                               s=kayit.get("sure", 0)),
                                        "why-text"), False, False, 0)
            row.pack_start(metin, True, True, 0)
            inner.pack_start(row, False, False, 0)
        holder.pack_start(card, False, False, 0)

    # -- olaylar --------------------------------------------------------------------------------

    def on_nav(self, _listbox, row):
        if row is not None and row.key != self.page:
            self.show_page(row.key)

    def on_lang_changed(self, combo):
        secilen = combo.get_active_id()
        if secilen and secilen != self.lang:
            self.lang = self.settings["lang"] = secilen
            save_settings(self.settings)
            self.retranslate()

    def on_theme_toggled(self, _button):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings["theme"] = self.theme
        save_settings(self.settings)
        self.apply_theme()
        self.retranslate()

    def retranslate(self):
        self.set_title(self.t("app_title"))
        self.title_label.set_text(self.t("header_sub"))
        self.theme_btn.set_label(self.t("theme_light") if self.theme == "dark"
                                 else self.t("theme_dark"))
        if not self.tarama and not self.guncelleniyor:
            self.status.set_text(self.t("ready"))
        self.show_page()

    def on_destroy(self, _widget):
        if self.tarama:
            self.tarama.iptal()
        if self.sweep_id:
            GLib.source_remove(self.sweep_id)
        Gtk.main_quit()

    # -- tema ------------------------------------------------------------------------------------

    def apply_theme(self):
        if self.theme == "dark":
            bg = "#1f2325"; side = "#2b2f31"; header = "#2b2f31"; fg = "#e6e6e6"
            sub = "#9aa4a8"; field = "#2b2f31"
            card = "#282d2f"; card_border = "#363c3e"; note_bg = "#2c3134"
            btn_bg = "#343a3c"; btn_hover = "#3f4649"; border = "#454b4e"
            code_fg = "#8fd6c4"
        else:
            bg = "#f2f4f5"; side = "#e4e7e9"; header = "#e4e7e9"; fg = "#1f2325"
            sub = "#5c666a"; field = "#ffffff"
            card = "#ffffff"; card_border = "#dde2e4"; note_bg = "#eef1f2"
            btn_bg = "#ffffff"; btn_hover = "#eef0f1"; border = "#c3c8ca"
            code_fg = "#1f5f52"
        Gtk.Settings.get_default().set_property(
            "gtk-application-prefer-dark-theme", self.theme == "dark")
        css = f"""
        window {{ background-color: {bg}; color: {fg}; }}
        label {{ color: {fg}; }}
        .header {{ background-color: {header}; border-radius: 10px; }}
        .header-sub {{ color: {sub}; font-size: 104%; font-weight: bold; }}
        .sidebar {{ background-color: {side}; }}
        .nav-title {{ font-weight: bold; }}
        .nav-sub {{ color: {sub}; font-size: 88%; }}
        .nav-list row:selected {{ background-color: {self.ACCENT}; }}
        .nav-list row:selected label {{ color: #ffffff; }}
        .status-label {{ color: {sub}; font-size: 91%; }}
        .page-title {{ font-size: 152%; font-weight: bold; }}
        .page-subtitle {{ color: {sub}; font-size: 104%; }}
        .card {{ background-color: {card}; border: 1px solid {card_border};
                 border-radius: 8px; }}
        .card-title {{ font-weight: bold; font-size: 106%; }}
        .why-text {{ color: {sub}; font-size: 92%; }}
        .caption-text {{ color: {sub}; font-size: 84%; }}
        .code-text {{ font-family: monospace; color: {code_fg}; }}
        .badge {{ color: #ffffff; font-size: 78%; font-weight: bold;
                  border-radius: 4px; padding: 3px 8px; }}
        .badge-ok {{ background-color: {self.C_OK}; }}
        .badge-warn {{ background-color: {self.C_WARN}; }}
        .badge-fail {{ background-color: {self.C_FAIL}; }}
        .badge-info {{ background-color: {self.C_INFO}; }}
        .note-box {{ background-color: {note_bg}; border: 1px solid {card_border};
                     border-left: 3px solid {self.ACCENT}; border-radius: 8px; }}
        .note-ok {{ border-left-color: {self.C_OK}; }}
        .note-warn {{ border-left-color: {self.C_WARN}; }}
        .note-fail {{ border-left-color: {self.C_FAIL}; }}
        .note-text {{ color: {fg}; font-size: 94%; }}
        button {{ background-image: none; background-color: {btn_bg}; color: {fg};
                  border: 1px solid {border}; border-radius: 6px; padding: 4px 14px; }}
        button label {{ color: {fg}; }}
        button:hover {{ background-color: {btn_hover}; }}
        button:disabled {{ color: {sub}; }}
        button:disabled label {{ color: {sub}; }}
        button.suggested-action {{ background-color: {self.ACCENT};
                                   border-color: {self.ACCENT}; color: #ffffff; }}
        button.suggested-action label {{ color: #ffffff; }}
        button.suggested-action:disabled {{ opacity: 0.55; }}
        button.destructive-action {{ background-color: {self.C_FAIL};
                                     border-color: {self.C_FAIL}; color: #ffffff; }}
        button.destructive-action label {{ color: #ffffff; }}
        combobox button {{ background-color: {field}; color: {fg}; }}
        combobox button label {{ color: {fg}; }}
        menu, .menu, popover, popover.background {{ background-color: {field};
                                                    color: {fg}; }}
        menuitem label, popover label {{ color: {fg}; }}
        menuitem:hover {{ background-color: {self.ACCENT}; }}
        menuitem:hover label {{ color: #ffffff; }}
        separator {{ background-color: {border}; }}
        """
        self.css_provider.load_from_data(css.encode())


def main():
    yollar = M.komut_satiri_yollari(sys.argv[1:])
    window = CaroteneWindow(load_settings())
    window.show_all()
    window.listbox.select_row(window.nav_rows[0])
    if yollar:
        GLib.idle_add(lambda: window.start_scan("ozel", yollar) and False)
    elif yollar is not None:
        window.status.set_text(window.t("args_none"))
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
