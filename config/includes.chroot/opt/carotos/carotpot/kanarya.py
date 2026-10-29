# -*- coding: utf-8 -*-
"""
CarotPot kanarya dosyalari.

Kanarya, gercek gorunen ama sahte icerikli bir yem dosyadir (parola tablosu,
banka belgesi, SSH anahtari...). Kullanicinin kendisinin acmasi icin neden
yoktur; biri acarsa, degistirirse ya da silerse bu, bilgisayarda yetkisiz
bir erisimin (USB'den bulasan zararli yazilim, baskasinin oturumu...)
isaretidir. Boylece CarotPot ag disindan gelen tehditleri de yakalar.

Izleme kullanicinin oturumunda, "carotpot.py bildir" surecinde inotify ile
yapilir (root gerekmez). Dosyayi acan sureci bulmak en iyi cabadir: ayni
kullanicinin surecleri /proc uzerinden aranir.

Kayitlar:
  ~/.config/carotpot/kanaryalar.json        kanarya listesi
  ~/.local/share/carotpot/kanarya.log       tetiklenmeler (satir basina JSON)

Dosya yoneticisinin onizleme/kucuk resim surecleri (tumblerd...) tetikleme
sayilmaz; dosyayi gercekten acan uygulama (belge goruntuleyici, kopyalama
komutu, zararli yazilim) sayilir.
"""

import ctypes
import ctypes.util
import json
import os
import random
import secrets
import select
import string
import struct
import time
import zipfile
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Yollar
# ---------------------------------------------------------------------------


def ayar_dizini():
    return os.path.join(os.environ.get("XDG_CONFIG_HOME") or
                        os.path.join(os.path.expanduser("~"), ".config"), "carotpot")


def veri_dizini():
    return os.path.join(os.environ.get("XDG_DATA_HOME") or
                        os.path.join(os.path.expanduser("~"), ".local", "share"), "carotpot")


def liste_yolu():
    return os.path.join(ayar_dizini(), "kanaryalar.json")


def olay_yolu():
    return os.path.join(veri_dizini(), "kanarya.log")


def liste_oku():
    try:
        with open(liste_yolu(), encoding="utf-8") as fh:
            veri = json.load(fh)
        return [k for k in veri if isinstance(k, dict) and isinstance(k.get("yol"), str)]
    except (OSError, ValueError, TypeError):
        return []


def liste_yaz(liste):
    os.makedirs(ayar_dizini(), exist_ok=True)
    gecici = liste_yolu() + ".yeni"
    with open(gecici, "w", encoding="utf-8") as fh:
        json.dump(liste, fh, ensure_ascii=False, indent=1)
    os.replace(gecici, liste_yolu())


def olaylari_oku(limit=500):
    try:
        with open(olay_yolu(), encoding="utf-8", errors="replace") as fh:
            satirlar = fh.readlines()[-limit:]
    except OSError:
        return []
    sonuc = []
    for s in satirlar:
        try:
            o = json.loads(s)
        except ValueError:
            continue
        if isinstance(o, dict) and "yol" in o:
            sonuc.append(o)
    return sonuc


def olay_yaz(olay):
    os.makedirs(veri_dizini(), exist_ok=True)
    with open(olay_yolu(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(olay, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Sablonlar: inandirici ama tamamen uydurma icerik
# ---------------------------------------------------------------------------

_ADLAR = ["Ayşe", "Mehmet", "Zeynep", "Can", "Elif", "Burak", "Deniz", "Ece", "Emre", "Selin"]
_SOYADLAR = ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Arslan", "Koç", "Aydın"]
_SITELER = ["e-posta", "okul portalı", "banka", "bulut depolama", "modem arayüzü",
            "muhasebe", "sosyal medya", "kargo takibi", "sunucu (ssh)", "wifi"]


def _parola(uz=12):
    harfler = string.ascii_letters + string.digits + "!.*_"
    return "".join(secrets.choice(harfler) for _ in range(uz))


def _xml_kacir(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def uret_parola_tablosu(yol):
    """En kucuk gecerli .xlsx (tek sayfa, satir ici metinler)."""
    satirlar = [["Hizmet", "Kullanıcı adı", "Parola", "Not"]]
    for site in random.sample(_SITELER, 7):
        ad = random.choice(_ADLAR).lower().replace("ş", "s").replace("ç", "c").replace("ğ", "g")
        satirlar.append([site, f"{ad}{random.randint(10, 99)}", _parola(), ""])
    hucreler = []
    for i, satir in enumerate(satirlar, 1):
        h = "".join(f'<c r="{chr(65 + j)}{i}" t="inlineStr"><is><t>{_xml_kacir(v)}</t></is></c>'
                    for j, v in enumerate(satir))
        hucreler.append(f'<row r="{i}">{h}</row>')
    sayfa = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             f'<sheetData>{"".join(hucreler)}</sheetData></worksheet>')
    with zipfile.ZipFile(yol, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   '<sheets><sheet name="Parolalar" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                   '</Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", sayfa)


def _pdf_metin(s):
    # Tek baytli standart yazitipi: Turkce harfler ASCII karsiligina indirilir
    tablo = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return s.translate(tablo).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def uret_banka_belgesi(yol):
    """Tek sayfalik, en kucuk gecerli PDF (uydurma hesap ozeti)."""
    bugun = datetime.now()
    ad = f"{random.choice(_ADLAR)} {random.choice(_SOYADLAR)}"
    satirlar = [("Hesap Ozeti", 16), ("", 11),
                (f"Musteri: {ad}", 11),
                (f"IBAN: TR{random.randint(10, 99)} 0000 {random.randint(1000, 9999)} "
                 f"{random.randint(1000, 9999)} {random.randint(1000, 9999)} "
                 f"{random.randint(1000, 9999)} {random.randint(10, 99)}", 11),
                (f"Donem: {(bugun - timedelta(days=30)):%d.%m.%Y} - {bugun:%d.%m.%Y}", 11),
                ("", 11)]
    bakiye = random.randint(20_000, 90_000)
    for _ in range(9):
        tutar = random.randint(-4000, 6000)
        bakiye += tutar
        gun = bugun - timedelta(days=random.randint(1, 30))
        satirlar.append((f"{gun:%d.%m.%Y}   {random.choice(['EFT', 'Kart', 'Havale', 'Fatura'])}"
                         f"   {tutar:>8} TL   Bakiye {bakiye} TL", 10))
    akis = ["BT", "/F1 16 Tf", "56 780 Td"]
    for metin, boyut in satirlar:
        akis.append(f"/F1 {boyut} Tf ({_pdf_metin(metin)}) Tj 0 -{boyut + 8} Td")
    akis.append("ET")
    icerik = "\n".join(akis).encode("latin-1")
    nesneler = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(icerik)).encode() + b" >>\nstream\n" + icerik + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    cikti = bytearray(b"%PDF-1.4\n")
    konumlar = []
    for i, n in enumerate(nesneler, 1):
        konumlar.append(len(cikti))
        cikti += f"{i} 0 obj\n".encode() + n + b"\nendobj\n"
    xref = len(cikti)
    cikti += f"xref\n0 {len(nesneler) + 1}\n0000000000 65535 f \n".encode()
    for k in konumlar:
        cikti += f"{k:010d} 00000 n \n".encode()
    cikti += (f"trailer\n<< /Size {len(nesneler) + 1} /Root 1 0 R >>\n"
              f"startxref\n{xref}\n%%EOF\n").encode()
    with open(yol, "wb") as fh:
        fh.write(cikti)


def uret_ssh_anahtari(yol):
    """OpenSSH ozel anahtari gibi gorunen, gecersiz (rastgele) icerik."""
    import base64
    govde = base64.b64encode(b"openssh-key-v1\0" + secrets.token_bytes(380)).decode()
    satirlar = [govde[i:i + 70] for i in range(0, len(govde), 70)]
    with open(yol, "w", encoding="ascii") as fh:
        fh.write("-----BEGIN OPENSSH PRIVATE KEY-----\n" + "\n".join(satirlar) +
                 "\n-----END OPENSSH PRIVATE KEY-----\n")
    os.chmod(yol, 0o600)


def uret_env(yol):
    with open(yol, "w", encoding="utf-8") as fh:
        fh.write(
            "APP_ENV=production\n"
            f"APP_KEY=base64:{secrets.token_urlsafe(32)}\n"
            "DB_HOST=10.0.12.5\nDB_PORT=3306\nDB_DATABASE=uygulama\n"
            f"DB_USERNAME=uygulama_yonetici\nDB_PASSWORD={_parola(18)}\n"
            f"MAIL_PASSWORD={_parola(14)}\n"
            f"API_TOKEN=tk_{secrets.token_hex(20)}\n")


def uret_yer_imleri(yol):
    baglantilar = "".join(
        f'<DT><A HREF="http://10.0.{random.randint(0, 20)}.{random.randint(2, 250)}/'
        f'{yol_}">{ad}</A>\n'
        for ad, yol_ in (("Sunucu yönetim paneli", "admin"), ("Yedekleme", "backup"),
                         ("Kamera kayıtları", "nvr"), ("Muhasebe", "erp/login"),
                         ("Modem", "")))
    with open(yol, "w", encoding="utf-8") as fh:
        fh.write("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n"
                 '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n'
                 "<TITLE>Bookmarks</TITLE>\n<H1>Bookmarks</H1>\n<DL><p>\n"
                 + baglantilar + "</DL><p>\n")


SABLONLAR = {
    "parola": {"tr": "Parola tablosu", "en": "Password sheet",
               "dosya": "sifreler.xlsx", "uret": uret_parola_tablosu},
    "banka": {"tr": "Banka belgesi", "en": "Bank statement",
              "dosya": "hesap-ozeti.pdf", "uret": uret_banka_belgesi},
    "ssh": {"tr": "SSH anahtarı", "en": "SSH key",
            "dosya": "id_rsa_yedek", "uret": uret_ssh_anahtari},
    "env": {"tr": "Yapılandırma (.env)", "en": "Configuration (.env)",
            "dosya": ".env", "uret": uret_env},
    "yerimi": {"tr": "Tarayıcı yer imleri", "en": "Browser bookmarks",
               "dosya": "yer-imleri.html", "uret": uret_yer_imleri},
}


def kanarya_olustur(sablon, dizin, ad=None):
    """Kanaryayi olusturur ve listeye ekler. Kayit sozlugunu dondurur.
    Dosya varsa FileExistsError."""
    if sablon not in SABLONLAR:
        raise ValueError("bilinmeyen sablon")
    ad = os.path.basename(ad or SABLONLAR[sablon]["dosya"])
    if not ad or ad in (".", ".."):
        raise ValueError("gecersiz dosya adi")
    yol = os.path.join(os.path.realpath(dizin), ad)
    if os.path.lexists(yol):
        raise FileExistsError(yol)
    SABLONLAR[sablon]["uret"](yol)
    # Dosya yeni olusturulmus gibi gorunmesin
    eski = time.time() - random.randint(20, 120) * 86400
    os.utime(yol, (eski, eski))
    kayit = {"yol": yol, "sablon": sablon, "olusturma": int(time.time())}
    liste = [k for k in liste_oku() if k["yol"] != yol]
    liste.append(kayit)
    liste_yaz(liste)
    return kayit


def kanarya_kaldir(yol, dosyayi_sil=True):
    """Once listeden cikarir, sonra dosyayi siler: izleyici silmeyi
    tetikleme saymaz (listede olmayan dosyalarin olaylari yok sayilir)."""
    liste = liste_oku()
    vardi = any(k["yol"] == yol for k in liste)
    liste_yaz([k for k in liste if k["yol"] != yol])
    if dosyayi_sil and vardi:
        try:
            os.unlink(yol)
        except OSError:
            pass


def durumlar():
    """Her kanarya icin son tetiklenme ve dosyanin varligi."""
    olaylar = olaylari_oku()
    sonuc = []
    for k in liste_oku():
        son = [o for o in olaylar if o.get("yol") == k["yol"]]
        sonuc.append(dict(k, var=os.path.exists(k["yol"]),
                          tetik=son[-1] if son else None, tetik_sayi=len(son)))
    return sonuc


# ---------------------------------------------------------------------------
# inotify ile izleme
# ---------------------------------------------------------------------------

IN_ACCESS, IN_MODIFY, IN_ATTRIB, IN_CLOSE_WRITE = 0x1, 0x2, 0x4, 0x8
IN_OPEN, IN_MOVE_SELF, IN_DELETE_SELF, IN_IGNORED = 0x20, 0x800, 0x400, 0x8000
IN_NONBLOCK, IN_CLOEXEC = 0o4000, 0o2000000
IZLENEN = IN_OPEN | IN_ACCESS | IN_MODIFY | IN_CLOSE_WRITE | IN_MOVE_SELF | IN_DELETE_SELF

# Dosyanin icini okumadan onizleme/dizin yapan surecler: tetikleme sayilmaz
YOKSAYILAN_SURECLER = {"tumblerd", "tracker-miner-f", "tracker-extract", "baloo_file",
                       "baloo_file_extr", "gvfsd-metadata", "thunar", "xfdesktop", "nautilus",
                       "pcmanfm", "nemo", "caja", "updatedb", "mlocate", "plocate",
                       "clamscan", "clamdscan", "freshclam", "rkhunter"}


def surec_bul(yol):
    """Dosyayi su an acik tutan (ayni kullaniciya ait) sureci bulur.
    [(ad, pid), ...] dondurur; bulamazsa bos liste."""
    bulunan = []
    benim = os.getpid()
    try:
        pidler = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return bulunan
    for pid in pidler:
        if int(pid) == benim:
            continue
        fd_dizini = f"/proc/{pid}/fd"
        try:
            for fd in os.listdir(fd_dizini):
                try:
                    if os.readlink(f"{fd_dizini}/{fd}") == yol:
                        with open(f"/proc/{pid}/comm", encoding="utf-8") as fh:
                            bulunan.append((fh.read().strip(), int(pid)))
                        break
                except OSError:
                    continue
        except OSError:
            continue
    return bulunan


class Izleyici:
    """Kanarya dosyalarini inotify ile izler. bekle(sure) olaylari toplar ve
    yeni tetiklenmeleri dondurur."""

    TEKRAR_SURESI = 30        # ayni dosya icin bu surede tek tetiklenme

    def __init__(self):
        self.libc = None
        self.fd = -1
        yol = ctypes.util.find_library("c")
        if yol:
            try:
                self.libc = ctypes.CDLL(yol, use_errno=True)
                self.fd = self.libc.inotify_init1(IN_NONBLOCK | IN_CLOEXEC)
            except (OSError, AttributeError):
                self.fd = -1
        self.izler = {}        # wd -> yol
        self.son = {}          # yol -> son tetiklenme zamani
        self.liste_imza = None
        self.yeniden_yukle()

    @property
    def calisiyor(self):
        return self.fd >= 0

    def kapat(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def _imza(self):
        try:
            st = os.stat(liste_yolu())
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def yeniden_yukle(self):
        """Kanarya listesi degistiyse izleri gunceller."""
        imza = self._imza()
        if imza == self.liste_imza or not self.calisiyor:
            return
        self.liste_imza = imza
        for wd in list(self.izler):
            self.libc.inotify_rm_watch(self.fd, wd)
        self.izler.clear()
        for k in liste_oku():
            if os.path.exists(k["yol"]):
                wd = self.libc.inotify_add_watch(self.fd, k["yol"].encode(), IZLENEN)
                if wd >= 0:
                    self.izler[wd] = k["yol"]

    def kanarya_var_mi(self):
        return bool(self.izler)

    def bekle(self, sure):
        """En fazla 'sure' saniye olay bekler; yeni tetiklenmeleri dondurur."""
        if not self.calisiyor:
            time.sleep(sure)
            return []
        hazir, _, _ = select.select([self.fd], [], [], sure)
        if not hazir:
            return []
        try:
            veri = os.read(self.fd, 64 * 1024)
        except BlockingIOError:
            return []
        olaylar = {}
        i = 0
        while i + 16 <= len(veri):
            wd, maske, _cerez, uz = struct.unpack_from("iIII", veri, i)
            i += 16 + uz
            yol = self.izler.get(wd)
            if yol is None:
                continue
            if maske & (IN_DELETE_SELF | IN_MOVE_SELF):
                tur = "silindi" if maske & IN_DELETE_SELF else "tasindi"
            elif maske & (IN_MODIFY | IN_CLOSE_WRITE):
                tur = "degisti"
            elif maske & (IN_OPEN | IN_ACCESS):
                tur = "acildi"
            else:
                continue
            # en onemli tur kalsin
            onem = {"acildi": 1, "degisti": 2, "tasindi": 3, "silindi": 4}
            if onem[tur] > onem.get(olaylar.get(yol), 0):
                olaylar[yol] = tur
            if maske & (IN_DELETE_SELF | IN_MOVE_SELF | IN_IGNORED):
                self.izler.pop(wd, None)
        yeni = []
        simdi = time.time()
        gecerli = {k["yol"] for k in liste_oku()}
        for yol, tur in olaylar.items():
            if yol not in gecerli:          # kullanici kanaryayi kaldirdi
                continue
            surecler = surec_bul(yol) if tur in ("acildi", "degisti") else []
            if surecler and all(ad.lower() in YOKSAYILAN_SURECLER for ad, _ in surecler):
                continue
            if tur == "acildi" and simdi - self.son.get(yol, 0) < self.TEKRAR_SURESI:
                continue
            self.son[yol] = simdi
            olay = {"ts": simdi, "yol": yol, "tur": tur,
                    "surec": ", ".join(f"{ad} ({pid})" for ad, pid in surecler[:3])}
            olay_yaz(olay)
            yeni.append(olay)
        return yeni


def bildirim_metni(olay, lang):
    ad = os.path.basename(olay["yol"])
    tur = {"acildi": {"tr": "açıldı", "en": "was opened"},
           "degisti": {"tr": "değiştirildi", "en": "was modified"},
           "silindi": {"tr": "silindi", "en": "was deleted"},
           "tasindi": {"tr": "taşındı", "en": "was moved"}}[olay["tur"]][lang]
    baslik = {"tr": "CarotPot: kanarya dosya tetiklendi",
              "en": "CarotPot: canary file triggered"}[lang]
    govde = {"tr": f"“{ad}” {tur}.", "en": f"“{ad}” {tur}."}[lang]
    if olay.get("surec"):
        govde += {"tr": f" Süreç: {olay['surec']}", "en": f" Process: {olay['surec']}"}[lang]
    return baslik, govde
