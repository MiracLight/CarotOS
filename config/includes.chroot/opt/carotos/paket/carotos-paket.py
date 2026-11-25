#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Paket Kurucu: yerel bir .deb dosyasını inceler ve onaydan sonra kurar.

Kurulumu root yardımcısı /usr/sbin/carotos-deb-kur yapar; ona kullanıcının gördüğü dosyanın özeti
verilir. Paket bilgileri güvenilmezdir: biçimi denetlenir, kırpılır ve düz metin olarak gösterilir."""
import hashlib
import os
import re
import subprocess
import sys
import threading
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from urllib.parse import unquote, urlsplit

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(BASE_DIR), "ortak"))
import dil  # noqa: E402
import tema  # noqa: E402
from yetkili import sistem_yolu, temiz_ortam  # noqa: E402

YARDIMCI = "/usr/sbin/carotos-deb-kur"
ALANLAR = ("Package", "Version", "Architecture", "Maintainer", "Installed-Size", "Depends",
           "Description", "Homepage")
DIL = "en"
METIN = dil.zenginlestir({
    "baslik": {"tr": "Paket Kurucu", "en": "Package Installer"},
    "bos": {"tr": "Kurulacak .deb dosyasını seç", "en": "Choose a .deb file to install"},
    "bos_alt": {"tr": "Dosyayı bu pencereye de sürükleyebilirsin.",
                "en": "You can also drag the file onto this window."},
    "sec": {"tr": "Dosya seç", "en": "Choose file"},
    "inceleniyor": {"tr": "Paket inceleniyor…", "en": "Inspecting the package…"},
    "gecersiz": {"tr": "Bu dosya açılamadı. Bilgisayardaki geçerli bir .deb dosyası seç.",
                 "en": "This file could not be opened. Choose a valid .deb file on this computer."},
    "uyari": {"tr": "Bu paket CarotOS ya da Debian deposundan gelmiyor; kurulum sırasında yönetici "
                    "yetkisiyle kod çalıştırabilir. Yalnız güvendiğin kaynaktan kur.",
              "en": "This package does not come from the CarotOS or Debian repository; it can run code "
                    "with administrator rights during installation. Install only from a source you trust."},
    "surum": {"tr": "Sürüm", "en": "Version"},
    "kurulu": {"tr": "Kurulu sürüm", "en": "Installed version"},
    "gelistirici": {"tr": "Geliştirici", "en": "Developer"},
    "site": {"tr": "Web sitesi", "en": "Website"},
    "boyut": {"tr": "Kurulu boyut", "en": "Installed size"},
    "ekler": {"tr": "Ek kurulacak paketler", "en": "Additional packages to install"},
    "yok": {"tr": "Yok", "en": "None"},
    "kur": {"tr": "Kur", "en": "Install"},
    "ac": {"tr": "Aç", "en": "Open"},
    "vazgec": {"tr": "Vazgeç", "en": "Cancel"},
    "goster": {"tr": "İşlemi göster", "en": "Show operation"},
    "guven": {"tr": "Kaynağa güveniyorum", "en": "I trust the source"},
    "kuruluyor": {"tr": "Kuruluyor: {ad}", "en": "Installing: {ad}"},
    "yardimci_yok": {"tr": "pkexec ya da kurulum yardımcısı bulunamadı.",
                     "en": "pkexec or the installation helper was not found."},
    "d_yeni": {"tr": "Yeni kurulum", "en": "New installation"},
    "d_guncelleme": {"tr": "Güncelleme", "en": "Update"},
    "d_ayni": {"tr": "Aynı sürüm", "en": "Same version"},
    "d_eski": {"tr": "Eski sürüm", "en": "Older version"},
    "d_mimari": {"tr": "Uyumsuz mimari", "en": "Incompatible architecture"},
    "n_ayni": {"tr": "Bu sürüm zaten kurulu.", "en": "This version is already installed."},
    "n_eski": {"tr": "Daha yeni bir sürüm kurulu; eski sürüm kurulamaz.",
               "en": "A newer version is installed; an older version cannot be installed."},
    "n_mimari": {"tr": "Bu paket bu bilgisayarın mimarisi için değil.",
                 "en": "This package is not for this computer's architecture."},
    "n_hata": {"tr": "Paket kurulamıyor (bağımlılıklar karşılanamıyor olabilir):",
               "en": "The package cannot be installed (dependencies may be unmet):"},
})


def M(anahtar, **b):
    return dil.T(METIN.get(anahtar), DIL, anahtar, **b)


# --- Saf mantık -------------------------------------------------------------
def kirp(metin, sinir=200):
    """Denetim ve çift yönlü yazı karakterlerini atar, uzunluğu kırpar."""
    metin = "".join(c for c in (metin or "")[:sinir * 2] if c == "\n" or c.isprintable()).strip()
    return metin if len(metin) <= sinir else metin[:sinir - 1] + "…"


def yol_coz(arg, cwd=None):
    """Komut satırı yolu ya da file:// URI -> var olan mutlak .deb yolu; değilse None."""
    if not arg or "\0" in arg:
        return None
    if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", arg):
        try:
            p = urlsplit(arg)
        except ValueError:
            return None
        if p.scheme != "file" or p.netloc not in ("", "localhost") or not p.path.startswith("/"):
            return None
        arg = unquote(p.path, errors="surrogateescape")
        if "\0" in arg:
            return None
    yol = os.path.realpath(os.path.join(cwd or os.getcwd(), arg))   # yardımcı sembolik bağ açmaz
    return yol if yol.endswith(".deb") and os.path.isfile(yol) else None


def bilgi_coz(metin):
    """`dpkg-deb -f` çıktısı -> {alan: metin}; ad/sürüm/mimari geçersizse None."""
    ham, son = {}, None
    for satir in (metin or "").splitlines():
        if satir[:1] in (" ", "\t"):
            if son:
                ham[son].append("" if satir.strip() == "." else satir.strip())
        elif ":" in satir:
            son, deger = satir.split(":", 1)
            ham[son] = [deger.strip()]
    b = {a: kirp("\n".join(ham.get(a, [])), 1500 if a == "Description" else 200) for a in ALANLAR}
    if not (re.fullmatch(r"[a-z0-9][a-z0-9+.-]{0,127}", b["Package"])
            and re.fullmatch(r"[0-9][0-9A-Za-z.+:~-]{0,127}", b["Version"])
            and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", b["Architecture"])):
        return None
    b["Installed-Size"] = int(b["Installed-Size"]) if re.fullmatch(r"[0-9]{1,12}", b["Installed-Size"]) else 0
    return b


def simulasyon_coz(kod, cikti):
    """`apt-get -s install` -> (kurulacak paket adları, hata metni ya da None)."""
    satirlar = (cikti or "").splitlines()
    adlar = re.findall(r"(?m)^Inst ([a-z0-9][a-z0-9+.-]*)", cikti or "")
    if kod == 0:
        return list(dict.fromkeys(adlar)), None
    ayrinti = [s for s in satirlar if s.startswith("E:") or "Depends:" in s or "Conflicts:" in s]
    return [], kirp("\n".join(ayrinti or satirlar[-3:]), 600) or "apt-get: %s" % kod


def durum_belirle(kurulu, yeni, mimari, sistem_mimarisi, karsilastir):
    """yeni | guncelleme | ayni | eski | mimari. karsilastir(a, işlem, b) -> bool."""
    if mimari not in ("all", sistem_mimarisi):
        return "mimari"
    if not kurulu:
        return "yeni"
    if karsilastir(yeni, "eq", kurulu):
        return "ayni"
    return "guncelleme" if karsilastir(yeni, "gt", kurulu) else "eski"


# --- Paket inceleme (arka planda) -------------------------------------------
def calistir(ad, *arg, sure=60):
    return subprocess.run([sistem_yolu(ad) or "/usr/bin/" + ad, *arg], capture_output=True, text=True,
                          errors="replace", timeout=sure, stdin=subprocess.DEVNULL, env=temiz_ortam())


def ozet_al(yol):
    with open(yol, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def incele(yol):
    """Ekranda gösterilecek her şey; dosya geçersizse None."""
    try:
        ozet = ozet_al(yol)
        r = calistir("dpkg-deb", "-f", yol, *ALANLAR)
        b = bilgi_coz(r.stdout) if r.returncode == 0 else None
        if b is None:
            return None
        s = calistir("apt-get", "-s", "--no-remove", "install", yol, sure=120)
        inst, hata = simulasyon_coz(s.returncode, s.stdout + "\n" + s.stderr)
        q = calistir("dpkg-query", "-W", "-f=${db:Status-Status} ${Version}\n", b["Package"])
        kurulu = next((x.split()[1] for x in q.stdout.splitlines() if x.startswith("installed ")), None)
        durum = durum_belirle(kurulu, b["Version"], b["Architecture"],
                              calistir("dpkg", "--print-architecture").stdout.strip(),
                              lambda a, i, c: calistir("dpkg", "--compare-versions", a, i, c).returncode == 0)
        if ozet_al(yol) != ozet:             # inceleme sırasında değişti: bilgiler bu özete ait olmayabilir
            return None
    except (OSError, subprocess.SubprocessError):
        return None
    neden = None
    if durum in ("mimari", "eski") or (durum == "ayni" and b["Package"] not in inst and not hata):
        neden = "n_" + durum
    elif hata:
        neden = "n_hata"
    return dict(b, yol=yol, sha256=ozet, kurulu=kurulu, durum=durum, hata=hata, neden=neden,
                ekler=[a for a in inst if a != b["Package"]])


def magaza_yukle():
    yukleyici = SourceFileLoader("carotos_magaza", os.path.join(BASE_DIR, "..", "magaza", "carotos-magaza.py"))
    modul = module_from_spec(spec_from_loader("carotos_magaza", yukleyici))
    yukleyici.exec_module(modul)
    return modul


# --- Pencere ----------------------------------------------------------------
class PaketPenceresi(Gtk.Window):
    def __init__(self, magaza):
        super().__init__()
        global DIL
        self.magaza, self.bilgi, self.islem, self._sira = magaza, None, None, 0
        ayar = magaza.ayarlari_oku()
        DIL = magaza.DIL = ayar["lang"]
        tema.uygula(ayar["theme"], "#5196d6")
        self.set_title("CarotOS " + M("baslik"))
        self.set_icon_name("carotos-paket")
        self.set_default_size(680, 640)
        self.connect("delete-event", lambda *_: self._islem_goster())
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect("drag-data-received", lambda _w, _c, _x, _y, veri, *_: self.ac((veri.get_uris() or [""])[0]))
        dis = tema.sinif(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "arka")
        self.add(dis)
        self.kaydir = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        dis.pack_start(self.kaydir, True, True, 0)
        alt = Gtk.Box(spacing=8, margin=14)
        dis.pack_start(alt, False, False, 0)
        self.sec_dugme = tema.dugme(M("sec"), None, self._sec)
        self.kur_dugme = tema.dugme(M("kur"), "ana", self._kur)
        alt.pack_start(self.sec_dugme, False, False, 0)
        alt.pack_end(self.kur_dugme, False, False, 0)
        self.ac_dugme = tema.dugme(M("ac"), None, self._uygulama_ac)
        self.ac_dugme.set_no_show_all(True)
        alt.pack_end(self.ac_dugme, False, False, 0)
        self._bos("bos", "bos_alt")

    def _icerik(self, parcalar):
        eski = self.kaydir.get_child()
        if eski:
            eski.destroy()
        kutu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=18)
        for p in parcalar:
            kutu.pack_start(p, False, False, 0)
        self.kaydir.add(kutu)
        self.kaydir.show_all()
        self.kur_dugme.set_sensitive(bool(self.bilgi and not self.bilgi["neden"]))
        self.ac_dugme.set_visible(self._acilacak() is not None)

    def _acilacak(self):
        return self.magaza.uygulama_bul(self.bilgi["desktop"]) if self.bilgi else None

    def _uygulama_ac(self):
        bilgi = self._acilacak()
        if bilgi is not None:
            self.magaza.uygulama_ac(bilgi, self)

    def _incele(self, yol):
        b = incele(yol)
        if b:
            b["desktop"] = self.magaza.desktop_haritasi().get(b["Package"], []) if b["kurulu"] else []
        return b

    def _bos(self, baslik, alt=None):
        self.bilgi = None
        self._icerik([tema.bos_durum("paket", M(baslik), M(alt) if alt else None)])

    def _islem_goster(self):
        """İşlem sürüyorsa onu öne getirir ve True döner (pencere kapanmaz)."""
        if self.islem and self.islem.calisiyor():
            self.islem.present()
            return True
        return False

    def _sec(self):
        d = Gtk.FileChooserNative.new(M("sec"), self, Gtk.FileChooserAction.OPEN, None, None)
        suzgec = Gtk.FileFilter()
        suzgec.set_name("*.deb")
        suzgec.add_pattern("*.deb")
        d.add_filter(suzgec)
        if d.run() == Gtk.ResponseType.ACCEPT:
            self.ac(d.get_uri() or "")
        d.destroy()

    def ac(self, arg, cwd=None):
        if self._islem_goster():
            return
        self._sira += 1
        sira, yol = self._sira, yol_coz(arg, cwd)
        if yol is None:
            self._bos("gecersiz")
            return
        self._bos("inceleniyor")
        threading.Thread(target=lambda: GLib.idle_add(self._goster, sira, self._incele(yol)), daemon=True).start()

    def _goster(self, sira, b):
        if sira != self._sira:               # bu arada başka dosya seçildi
            return False
        if b is None:
            self._bos("gecersiz")
            return False
        self.bilgi = b
        dis, ic = tema.kart()
        bas = Gtk.Box(spacing=10)
        ad = tema.etiket(b["Package"], "buyuk-baslik")
        ad.set_ellipsize(Pango.EllipsizeMode.END)
        bas.pack_start(ad, True, True, 0)
        bas.pack_end(tema.rozet(M("d_" + b["durum"]), "kirmizi" if b["neden"] else "mavi"), False, False, 0)
        ic.pack_start(bas, False, False, 0)
        ic.pack_start(tema.etiket(b["Description"], None, sar=True), False, False, 0)
        ekler = ", ".join(b["ekler"])
        for anahtar, deger in (("surum", b["Version"]), ("kurulu", b["kurulu"]), ("gelistirici", b["Maintainer"]),
                               ("site", b["Homepage"]),
                               ("boyut", b["Installed-Size"] and GLib.format_size(b["Installed-Size"] * 1024)),
                               ("ekler", "" if b["hata"] else kirp(ekler, 1000) or M("yok")),
                               ("SHA-256", b["sha256"])):
            if deger:
                satir = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                satir.pack_start(tema.etiket(M(anahtar), "kart-alt"), False, False, 0)
                satir.pack_start(tema.etiket(deger, None, sar=True, sec=True), False, False, 0)
                ic.pack_start(satir, False, False, 0)
        parcalar = [tema.not_kutusu(M("uyari"), "uyari")[0], dis]
        if b["neden"]:
            metin = M(b["neden"]) + ("\n" + b["hata"] if b["neden"] == "n_hata" else "")
            parcalar.insert(0, tema.not_kutusu(metin, "hata")[0])
        self._icerik(parcalar)
        return False

    def _onay(self, b):
        kutu = Gtk.CheckButton(label=M("guven"))

        def bagla(_k):                       # onay_sor'un "ana" düğmesi kutuya bağlı
            alan = kutu.get_parent().get_children()
            for d in alan[alan.index(kutu) + 1].get_children():
                if d.get_style_context().has_class("ana"):
                    d.set_sensitive(kutu.get_active())
        for sinyal in ("map", "toggled"):
            kutu.connect(sinyal, bagla)
        return (tema.onay_sor(self, "%s %s" % (b["Package"], b["Version"]), M("uyari"), M("kur"), M("vazgec"),
                              ek=kutu) and kutu.get_active())

    def _kur(self):
        b, pkexec = self.bilgi, sistem_yolu("pkexec")
        if self._islem_goster() or not b or b["neden"]:
            return
        if not pkexec or not os.access(YARDIMCI, os.X_OK):
            self._icerik([tema.not_kutusu(M("yardimci_yok"), "hata")[0]])
            return
        if not self._onay(b):
            return
        self.sec_dugme.set_sensitive(False)
        self.kur_dugme.set_label(M("goster"))
        self.islem = self.magaza.IslemPenceresi(self, M("kuruluyor", ad=b["Package"]),
                                                [pkexec, YARDIMCI, b["yol"], b["sha256"]],
                                                lambda _basarili: self._bitti(b["yol"]))
        self.islem.baslat()

    def _bitti(self, yol):
        self.islem = None
        self.sec_dugme.set_sensitive(True)
        self.kur_dugme.set_label(M("kur"))
        self.ac(yol)                         # durum dpkg'den yeniden okunur


class PaketUygulamasi(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.carotos.Paket", flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.pencere = None

    def do_command_line(self, komut):
        if self.pencere is None:
            self.pencere = PaketPenceresi(magaza_yukle())
            self.add_window(self.pencere)
            self.pencere.show_all()
        if len(komut.get_arguments()) > 1:
            self.pencere.ac(komut.get_arguments()[1], komut.get_cwd())
        self.pencere.present()
        return 0


if __name__ == "__main__":
    sys.exit(PaketUygulamasi().run(sys.argv))
