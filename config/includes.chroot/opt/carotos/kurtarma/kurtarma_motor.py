# -*- coding: utf-8 -*-
"""CarotOS Kurtarma: motor (GTK'siz, yalniz standart kutuphane).

Model: rsync + sabit bag (hard link) ile artimli "kurtarma noktasi" (Linux
Mint'in Timeshift'i, Windows'un Sistem Geri Yukleme'si ile ayni fikir).
Btrfs/LVM anlik goruntusu DEGIL: CarotOS kurucusu dosya sistemini sabitlemez
(cogu zaman ext4), bu yuzden her dosya sistemiyle calisan bu yontem secildi.

v1 kapsami BILEREK dar: yalnizca /etc, /root ve kurulu paket listesi (dpkg
--get-selections). Bunlar "sistem neden bozuldu" sorularinin buyuk kismini
(kotu bir guncelleme, yanlis bir ayar dosyasi) kapsar. Kullanicilarin kendi
ev dizini (belgeler, masaustu ayarlari) BILEREK disaridadir: bu bir yedekleme
araci degil, "sistemi son bilinen iyi duruma dondurme" aracidir -- aynen
Windows'un Sistem Geri Yukleme'sinin kisisel dosyalara dokunmamasi gibi.
Ev dizini/nokta ayarlari (.config, .ssh...) icin bkz. docs/KURTARMA.md ("v2").

Depolama: /var/lib/carotos-kurtarma/noktalar/<id>/ (ayni diskte, varsayilan
Timeshift konumuyla ayni karar). Harici diske tasima kullaniciya birakilir.

Butun yetki isteyen islemler (olustur/geri-yukle/sil) carotos-kurtarma-yonet
yardimcisina birakilir (ortak/yetkili.py kurallari orada uygulanir); bu
dosya alt surec CAGIRMAZ -- yalnizca komut listesi URETIR ve metin/JSON
isler, boylece GTK'siz ve kolay test edilir.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shutil

SURUM = "1.0"

TABAN_DIZIN = "/var/lib/carotos-kurtarma"
NOKTALAR_DIZINI = os.path.join(TABAN_DIZIN, "noktalar")
AYAR_DOSYASI = "/etc/carotos-kurtarma/ayarlar.json"

VARSAYILAN_AYAR = {
    "sakla": 5,                   # en fazla kac nokta tutulur (eskisi silinir)
    "oto_guncelleme_oncesi": True,  # apt kurulum/guncellemeden once otomatik nokta
    "min_aralik_dk": 10,          # ayni tetikleyiciden iki nokta arasi en az sure
    "min_bos_mb": 512,            # bundan az bos alan varsa yeni nokta reddedilir
}

# Sabit kapsam: ad -> kaynak yol. ("etc", "root-ev") disk uzerindeki nokta
# alt klasorunun adidir; hedef_sistem geri yuklemede dosyalarin YAZILACAGI yer.
PARCALAR = (("etc", "/etc"), ("root-ev", "/root"))

# Her iki tarafta da (olustur/geri-yukle) uygulanir: buyuk/onemsiz klasorler.
HARIC_DESENLERI = ("Cache", "CacheStorage", "Code Cache", "GPUCache",
                    "Service Worker", ".git", "*.sock")

ETIKET_RE = re.compile(r"^[\w ÇĞİÖŞÜçğıöşü.-]{1,60}\Z", re.UNICODE)
_ID_RE = re.compile(r"\A\d{8}-\d{6}\Z")

TETIKLEYICILER = ("elle", "oto")


class KurtarmaHatasi(Exception):
    """Kullaniciya gosterilecek, beklenen bir hata (disk dolu, nokta yok...)."""

    def __init__(self, kod, **ek):
        super().__init__(kod)
        self.kod = kod
        self.ek = ek


# ---------------------------------------------------------------------------
# Kucuk yardimcilar (saf, yan etkisiz)
# ---------------------------------------------------------------------------

def simdi_id(simdi=None):
    """Nokta klasor adi: siralanabilir, dosya sistemi icin güvenli, yerelden bagimsiz."""
    return (simdi or datetime.datetime.now()).strftime("%Y%m%d-%H%M%S")


def id_gecerli_mi(nokta_id):
    return bool(_ID_RE.match(nokta_id or ""))


def etiket_gecerli_mi(etiket):
    return etiket is not None and bool(ETIKET_RE.match(etiket))


def nokta_yolu(nokta_id, kok=NOKTALAR_DIZINI):
    return os.path.join(kok, nokta_id)


def _oku_json(yol):
    try:
        with open(yol, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def _atomik_json_yaz(yol, veri, izin=0o600):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as fh:
        json.dump(veri, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.chmod(gecici, izin)
    os.replace(gecici, yol)


def ayarlari_oku(yol=AYAR_DOSYASI):
    veri = _oku_json(yol)
    sonuc = dict(VARSAYILAN_AYAR)
    if isinstance(veri, dict):
        for anahtar in VARSAYILAN_AYAR:
            if anahtar in veri and isinstance(veri[anahtar], type(VARSAYILAN_AYAR[anahtar])):
                sonuc[anahtar] = veri[anahtar]
    return sonuc


def ayarlari_yaz(ayar, yol=AYAR_DOSYASI):
    # 0644: hassas veri icermez (sayi/booleanlar), arayuz pkexec olmadan okuyabilsin
    temiz = {k: ayar.get(k, v) for k, v in VARSAYILAN_AYAR.items()}
    _atomik_json_yaz(yol, temiz, izin=0o644)
    return temiz


def canli_sistem_mi(cmdline_yolu="/proc/cmdline"):
    """Canli (USB) oturumda mi calisiyoruz? Degisiklikler kalici olmaz, uyari icin."""
    try:
        with open(cmdline_yolu, encoding="utf-8", errors="replace") as fh:
            icerik = fh.read()
    except OSError:
        return False
    return "boot=live" in icerik or " live-media" in (" " + icerik)


def surum_oku(yol="/etc/os-release"):
    veri = {}
    try:
        with open(yol, encoding="utf-8", errors="replace") as fh:
            for satir in fh:
                if "=" in satir:
                    k, _, v = satir.partition("=")
                    veri[k.strip()] = v.strip().strip('"')
    except OSError:
        pass
    return veri.get("VERSION") or veri.get("PRETTY_NAME") or "?"


def bos_alan_yeterli_mi(dizin, gerekli_mb, disk_kullanimi=None):
    disk_kullanimi = disk_kullanimi or shutil.disk_usage
    olcum_dizini = dizin
    while olcum_dizini and not os.path.isdir(olcum_dizini):
        ust = os.path.dirname(olcum_dizini.rstrip(os.sep))
        if ust == olcum_dizini:
            break
        olcum_dizini = ust
    try:
        kullanim = disk_kullanimi(olcum_dizini or "/")
    except OSError:
        return True  # olcemiyorsak islemi engelleme
    return (kullanim.free // (1024 * 1024)) >= gerekli_mb


# ---------------------------------------------------------------------------
# Nokta listesi
# ---------------------------------------------------------------------------

def noktalari_listele(kok=NOKTALAR_DIZINI):
    """[meta, ...] -- en yeni once. Bozuk/eksik meta.json sessizce atlanir."""
    if not os.path.isdir(kok):
        return []
    sonuc = []
    for ad in os.listdir(kok):
        if not id_gecerli_mi(ad):
            continue
        meta = _oku_json(os.path.join(kok, ad, "meta.json"))
        if isinstance(meta, dict) and meta.get("id") == ad:
            sonuc.append(meta)
    sonuc.sort(key=lambda m: m["id"], reverse=True)
    return sonuc


def nokta_oku(nokta_id, kok=NOKTALAR_DIZINI):
    if not id_gecerli_mi(nokta_id):
        return None
    meta = _oku_json(os.path.join(kok, nokta_id, "meta.json"))
    return meta if isinstance(meta, dict) and meta.get("id") == nokta_id else None


def son_nokta_zamani(tetikleyici=None, kok=NOKTALAR_DIZINI):
    for meta in noktalari_listele(kok):
        if tetikleyici is None or meta.get("tetikleyici") == tetikleyici:
            return meta.get("olusturma")
    return None


def _ayristir_zaman(iso_metin):
    try:
        return datetime.datetime.fromisoformat(iso_metin)
    except (TypeError, ValueError):
        return None


def aralik_doldu_mu(tetikleyici, min_aralik_dk, kok=NOKTALAR_DIZINI, simdi=None):
    """Son <tetikleyici> noktasindan bu yana min_aralik_dk gecti mi? (oto-oncesi
    kancanin her apt islemi icin ayri nokta acmasini onler)."""
    son = _ayristir_zaman(son_nokta_zamani(tetikleyici, kok))
    if son is None:
        return True
    simdi = simdi or datetime.datetime.now()
    return (simdi - son) >= datetime.timedelta(minutes=min_aralik_dk)


# ---------------------------------------------------------------------------
# rsync komut uretimi (saf: hicbir sey calistirmaz)
# ---------------------------------------------------------------------------

def rsync_olustur_komutu(kaynak_dizin, hedef_dizin, onceki_dizin=None, haric=HARIC_DESENLERI):
    """Nokta OLUSTURURKEN kullanilir: --delete YOK (hedef her zaman bos/yeni)."""
    komut = ["rsync", "-a", "--numeric-ids"]
    for desen in haric:
        komut += ["--exclude", desen]
    if onceki_dizin and os.path.isdir(onceki_dizin):
        komut += ["--link-dest", onceki_dizin]
    komut += [kaynak_dizin.rstrip("/") + "/", hedef_dizin]
    return komut


def rsync_geri_yukle_komutu(kaynak_dizin, hedef_sistem_dizin, haric=HARIC_DESENLERI):
    """GERI YUKLERKEN kullanilir: --delete VAR (canli sistemi noktayla birebir
    eslestirir; nokta alinandan sonra eklenen dosyalar silinir)."""
    komut = ["rsync", "-a", "--delete", "--numeric-ids"]
    for desen in haric:
        komut += ["--exclude", desen]
    komut += [kaynak_dizin.rstrip("/") + "/", hedef_sistem_dizin]
    return komut


# ---------------------------------------------------------------------------
# Paket listesi (dpkg --get-selections metni -> kume islemleri)
# ---------------------------------------------------------------------------

def paket_kumesi(metin):
    kume = set()
    for satir in (metin or "").splitlines():
        parca = satir.split()
        if len(parca) == 2 and parca[1] == "install":
            kume.add(parca[0])
    return kume


def eksik_paketler(eski_metin, simdiki_metin):
    """Noktada kurulu olup simdi kurulu olmayan paketler (siralı, yinelenmez)."""
    return sorted(paket_kumesi(eski_metin) - paket_kumesi(simdiki_metin))


# ---------------------------------------------------------------------------
# Yuksek seviye akislar: calistir(komut, zaman=...) -> (kod, cikti) enjekte edilir
# (carotos-kurtarma-yonet gercek calistir() ile cagirir; testler sahtesini verir)
# ---------------------------------------------------------------------------

def nokta_olustur(calistir, etiket=None, tetikleyici="elle", kok=NOKTALAR_DIZINI,
                  ayarlar=None, ev_ayarlari=None):
    if tetikleyici not in TETIKLEYICILER:
        raise KurtarmaHatasi("gecersiz_tetikleyici")
    if etiket is not None and not etiket_gecerli_mi(etiket):
        raise KurtarmaHatasi("gecersiz_etiket")
    ayarlar = ayarlar if ayarlar is not None else ayarlari_oku()
    if not bos_alan_yeterli_mi(kok, ayarlar["min_bos_mb"]):
        raise KurtarmaHatasi("disk_dolu")

    nid = simdi_id()
    hedef_kok = nokta_yolu(nid, kok)
    if os.path.exists(hedef_kok):
        raise KurtarmaHatasi("cakisma")

    onceki = noktalari_listele(kok)
    onceki_id = onceki[0]["id"] if onceki else None

    os.makedirs(hedef_kok)
    parcalar = []
    try:
        for ad, kaynak in PARCALAR:
            if not os.path.isdir(kaynak):
                continue
            hedef = os.path.join(hedef_kok, ad)
            os.makedirs(hedef, exist_ok=True)
            onceki_alt = os.path.join(nokta_yolu(onceki_id, kok), ad) if onceki_id else None
            kod, cikti = calistir(rsync_olustur_komutu(kaynak, hedef, onceki_alt))
            if kod != 0:
                raise KurtarmaHatasi("rsync_hata", parca=ad, cikti=cikti)
            parcalar.append(ad)

        kod, paket_metni = calistir(["dpkg", "--get-selections"])
        with open(os.path.join(hedef_kok, "paketler.txt"), "w", encoding="utf-8") as fh:
            fh.write(paket_metni if kod == 0 else "")

        kod, du_cikti = calistir(["du", "-sm", hedef_kok])
        boyut_mb = None
        ilk = (du_cikti.split() or [""])[0] if kod == 0 else ""
        if ilk.isdigit():
            boyut_mb = int(ilk)

        meta = {
            "id": nid,
            "olusturma": datetime.datetime.now().isoformat(timespec="seconds"),
            "etiket": etiket or "",
            "tetikleyici": tetikleyici,
            "parcalar": parcalar,
            "boyut_mb": boyut_mb,
            "surum": surum_oku(),
            "kurtarma_surumu": SURUM,
        }
        _atomik_json_yaz(os.path.join(hedef_kok, "meta.json"), meta, izin=0o644)
    except Exception:
        shutil.rmtree(hedef_kok, ignore_errors=True)
        raise

    silinen = _eskileri_temizle(kok, ayarlar["sakla"])
    return {"nokta": meta, "silinen": silinen}


def _eskileri_temizle(kok, sakla):
    silinen = []
    for meta in noktalari_listele(kok)[max(sakla, 0):]:
        shutil.rmtree(nokta_yolu(meta["id"], kok), ignore_errors=True)
        silinen.append(meta["id"])
    return silinen


def nokta_sil(nokta_id, kok=NOKTALAR_DIZINI):
    if not id_gecerli_mi(nokta_id):
        raise KurtarmaHatasi("gecersiz_id")
    yol = nokta_yolu(nokta_id, kok)
    if not os.path.isdir(yol):
        raise KurtarmaHatasi("nokta_yok")
    shutil.rmtree(yol)


def nokta_geri_yukle(calistir, nokta_id, kok=NOKTALAR_DIZINI, paketleri_de_kur=False):
    meta = nokta_oku(nokta_id, kok)
    if meta is None:
        raise KurtarmaHatasi("nokta_yok")
    yol = nokta_yolu(nokta_id, kok)
    sonuc = {"parcalar": {}}
    for ad, hedef_sistem in PARCALAR:
        kaynak = os.path.join(yol, ad)
        if not os.path.isdir(kaynak):
            continue
        kod, cikti = calistir(rsync_geri_yukle_komutu(kaynak, hedef_sistem))
        sonuc["parcalar"][ad] = kod == 0
        if kod != 0:
            raise KurtarmaHatasi("rsync_hata", parca=ad, cikti=cikti, kismi=sonuc)
    if paketleri_de_kur:
        sonuc["paketler"] = _paketleri_tamamla(calistir, os.path.join(yol, "paketler.txt"))
    return sonuc


def _paketleri_tamamla(calistir, paket_dosyasi):
    try:
        with open(paket_dosyasi, encoding="utf-8") as fh:
            eski_metin = fh.read()
    except OSError:
        return {"basarili": False, "hata": "paket_listesi_yok"}
    kod, simdiki_metin = calistir(["dpkg", "--get-selections"])
    if kod != 0:
        return {"basarili": False, "hata": "dpkg_okunamadi"}
    eksik = eksik_paketler(eski_metin, simdiki_metin)
    if not eksik:
        return {"basarili": True, "kurulan": []}
    kod, cikti = calistir(["apt-get", "-y", "install", "--"] + eksik, 1800)
    return {"basarili": kod == 0, "denenen": eksik, "cikti": cikti}


def oto_guncelleme_oncesi(calistir, kok=NOKTALAR_DIZINI, ayarlar=None):
    """apt kancasinin (DPkg::Pre-Invoke) cagirdigi islev: ayar kapaliysa ya da
    araya az zaman girdiyse sessizce hicbir sey yapmaz (apt islemini ASLA
    durdurmaz -- cagiran taraf cikis kodunu yok sayar)."""
    ayarlar = ayarlar if ayarlar is not None else ayarlari_oku()
    if not ayarlar["oto_guncelleme_oncesi"]:
        return {"atlandi": "kapali"}
    if not aralik_doldu_mu("oto", ayarlar["min_aralik_dk"], kok):
        return {"atlandi": "cok_yakin"}
    try:
        return nokta_olustur(calistir, etiket=None, tetikleyici="oto", kok=kok, ayarlar=ayarlar)
    except KurtarmaHatasi as exc:
        return {"atlandi": exc.kod}
