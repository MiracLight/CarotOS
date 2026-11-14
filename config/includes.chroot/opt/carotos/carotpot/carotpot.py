#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CarotPot - CarotOS yerel ag tuzagi (bal kupu).

Bu bilgisayarda sahte SSH, Telnet, web yonetim paneli, FTP, VNC, RDP, MySQL
ve Redis tuzaklari acilir. Gercek bir kullanicinin bunlara dokunmasi icin
neden yoktur; bu yuzden her baglanti bir uyaridir. Her tuzak tuzaklar/
dizininde ayri bir moduldur ve kendini farkli bir cihaz olarak tanitabilir
(persona).

Guvenlik ilkeleri:
  * Gercek kabuk ya da gercek hizmet yoktur; her giris denemesi reddedilir.
  * Varsayilan olarak yalnizca ozel ag adreslerinden gelen baglantilar
    kaydedilir; "internet_kabul" ayari acilirsa her adresten kabul edilir.
  * Yuksek portlar kullanilir; hizmet yetkisiz "carotpot" kullanicisiyla ve
    kisitli bir systemd biriminde calisir (karar D5).
  * Okuma boyutu, baglanti basina toplam sure, eszamanli baglanti (toplam ve
    kaynak basina; fazlasi beklemeden kapatilir, SSH dahil), kaynak basina ve
    genel olay hizi ile veritabani satir sayisi sinirlidir.
  * Olay gunlugunde parolalar maskelidir; tam parola yalnizca hizmetin kendi
    veritabaninda (0700 dizin) tutulur.

Kullanim:
  carotpot.py run   --ayar /etc/carotpot/ayarlar.json   tuzaklari baslatir (hizmet)
  carotpot.py bildir                                     oturumda bildirim gosterir,
                                                         kanarya dosyalari izler
  carotpot.py report                                     son 24 saatin ozeti
"""

import argparse
import asyncio
import collections
import html
import ipaddress
import json
import logging
import logging.handlers
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# Hizmet "python3 -I" ile calisir; -I betigin dizinini yola eklemez. Tuzak
# modulleri bu dizindedir (yalniz root yazabilir).
_BURASI = os.path.dirname(os.path.abspath(__file__))
if _BURASI not in sys.path:
    sys.path.insert(0, _BURASI)

import tuzaklar  # noqa: E402
from tuzaklar.ssh import asyncssh  # noqa: E402,F401  (testler ve durum icin)

SURUM = "2.0"
LOG = logging.getLogger("carotpot")

AYAR_DOSYASI = "/etc/carotpot/ayarlar.json"
GUNLUK_DOSYASI = "/var/log/carotpot/olaylar.log"
DURUM_DOSYASI = "/run/carotpot/durum.json"
VERI_DIZINI = "/var/lib/carotpot"

# Ayarlarin varsayilanlari ve gecerli araliklari. Ayar dosyasi ve yonetici
# yardimcisi ayni dogrulamayi kullanir.
VARSAYILAN = {
    "portlar": {ad: tuzaklar.MODULLER[ad].VARSAYILAN_PORT for ad in tuzaklar.SIRA},
    "personalar": {ad: tuzaklar.varsayilan_persona(ad) for ad in tuzaklar.SIRA},
    "yoksay": [],
    "bekleme": 300,
    "sakla_gun": 30,
    "dakikada_olay": 120,
    "webhook": "",
    "dinle": "",       # "" = tum arayuzler; Poligon laboratuvari 127.x verir
    # False = yalnizca yerel ag (tuzak kabulu ve ufw izni ozel adres bloklari);
    # True = internetten gelen baglantilar da kabul edilir, ufw izni her adrese
    "internet_kabul": False,
}
HIZMETLER = tuzaklar.SIRA


# --------------------------------------------------------------------------
# Yardimcilar
# --------------------------------------------------------------------------

# ipaddress.is_private belge/test araliklarini da ozel saydigi icin acik liste
YEREL_AGLAR = [ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    "127.0.0.0/8", "169.254.0.0/16",
    "::1/128", "fe80::/10", "fc00::/7",
)]


def adres_coz(ip):
    """Gecerli IP nesnesi ya da None. IPv4-mapped IPv6 cozulur."""
    try:
        adr = ipaddress.ip_address(str(ip).split("%")[0])
    except ValueError:
        return None
    if isinstance(adr, ipaddress.IPv6Address) and adr.ipv4_mapped:
        adr = adr.ipv4_mapped
    return adr


def ozel_adres_mi(ip):
    adr = adres_coz(ip)
    return adr is not None and any(adr.version == n.version and adr in n
                                   for n in YEREL_AGLAR)


kes = tuzaklar.kes


def maske(s):
    if not s:
        return ""
    return s[0] + "*" * (len(s) - 1) if len(s) > 1 else "*"


def sinir_anahtari(ip):
    """Sinirlarin sayildigi kaynak anahtari. IPv6 /64 onekine indirgenir:
    saldirgan ayni agda sinirsiz IPv6 adresi uretebilir (C-04)."""
    adr = adres_coz(ip)
    if adr is None:
        return str(ip)
    if adr.version == 6:
        return str(ipaddress.ip_network(f"{adr}/64", strict=False))
    return str(adr)


def bildirim_arindir(metin, uzunluk=300):
    """Masaustu bildirim govdesi: denetim karakterleri temizlenir, Pango/HTML
    isaretlemesi kacislanir (saldirganin yazdigi ad bildirimde baglanti
    olamasin, C-05)."""
    return html.escape(kes(metin, uzunluk), quote=False)


# Webhook hedefleri (Discord, Slack...) bu karakterlerle anma, baglanti ve
# bicim uretir; saldirganin metninde etkisizlestirilir.
_WEBHOOK_DEGISTIR = str.maketrans({"<": "‹", ">": "›", "`": "ˋ", "[": "(", "]": ")"})


def webhook_arindir(metin, uzunluk=500):
    metin = kes(metin, uzunluk).translate(_WEBHOOK_DEGISTIR)
    return metin.replace("@", "@​").replace("&", "&​")


def ayar_dogrula(veri):
    """Ayar sozlugunu dogrular ve normallestirir. Hata varsa ValueError."""
    if not isinstance(veri, dict):
        raise ValueError("ayar bir sozluk olmali")
    sonuc = json.loads(json.dumps(VARSAYILAN))
    portlar = veri.get("portlar", sonuc["portlar"])
    if not isinstance(portlar, dict) or set(portlar) - set(HIZMETLER):
        raise ValueError("bilinmeyen hizmet")
    kullanilan = set()
    for ad in HIZMETLER:
        p = portlar.get(ad, 0)
        if p in (None, 0, False):
            sonuc["portlar"][ad] = 0      # 0 = kapali
            continue
        if not isinstance(p, int) or isinstance(p, bool) or not 1024 <= p <= 65535:
            raise ValueError(f"gecersiz port: {ad}")
        if p in kullanilan:
            raise ValueError(f"port iki kez kullaniliyor: {p}")
        kullanilan.add(p)
        sonuc["portlar"][ad] = p
    if not kullanilan:
        raise ValueError("en az bir tuzak acik olmali")
    personalar = veri.get("personalar", {})
    if not isinstance(personalar, dict) or set(personalar) - set(HIZMETLER):
        raise ValueError("gecersiz persona")
    for ad, persona in personalar.items():
        if persona not in tuzaklar.persona_anahtarlari(ad):
            raise ValueError(f"gecersiz persona: {ad}")
        sonuc["personalar"][ad] = persona
    yoksay = veri.get("yoksay", [])
    if not isinstance(yoksay, list) or len(yoksay) > 64:
        raise ValueError("yoksay listesi gecersiz")
    temiz = []
    for ip in yoksay:
        adr = adres_coz(ip)
        if adr is None:
            raise ValueError(f"gecersiz IP: {kes(ip, 40)}")
        if str(adr) not in temiz:
            temiz.append(str(adr))
    sonuc["yoksay"] = temiz
    for anahtar, alt, ust in (("bekleme", 10, 86400), ("sakla_gun", 1, 365),
                              ("dakikada_olay", 10, 6000)):
        deger = veri.get(anahtar, sonuc[anahtar])
        if not isinstance(deger, int) or isinstance(deger, bool) or not alt <= deger <= ust:
            raise ValueError(f"gecersiz deger: {anahtar}")
        sonuc[anahtar] = deger
    webhook = veri.get("webhook", "") or ""
    if webhook:
        parca = urllib.parse.urlparse(webhook)
        if parca.scheme != "https" or not parca.netloc or len(webhook) > 500:
            raise ValueError("webhook https ile baslayan bir adres olmali")
    sonuc["webhook"] = webhook
    dinle = veri.get("dinle", "") or ""
    if dinle:
        adr = adres_coz(dinle) if isinstance(dinle, str) else None
        if adr is None:
            raise ValueError("gecersiz dinleme adresi")
        dinle = str(adr)
    sonuc["dinle"] = dinle
    internet = veri.get("internet_kabul", False)
    if not isinstance(internet, bool):
        raise ValueError("gecersiz deger: internet_kabul")
    sonuc["internet_kabul"] = internet
    return sonuc


def ayar_oku(yol=AYAR_DOSYASI):
    try:
        with open(yol, encoding="utf-8") as fh:
            return ayar_dogrula(json.load(fh))
    except (OSError, ValueError):
        return json.loads(json.dumps(VARSAYILAN))


# --------------------------------------------------------------------------
# Olay gunlugu (fail2ban ve arayuz okur)
# --------------------------------------------------------------------------
# Satir bicimi:
#   2026-10-26 17:30:01 CAROTPOT kaynak=192.168.1.5 hizmet=ssh tur=giris | {json}
# fail2ban filtresi "kaynak=<HOST>" kismini kullanir; arayuz " | " sonrasini.

def olay_satiri(olay):
    zaman = datetime.fromtimestamp(olay["ts"]).strftime("%Y-%m-%d %H:%M:%S")
    govde = {k: olay.get(k) for k in ("ts", "hizmet", "kaynak", "kaynak_port",
                                      "hedef_port", "tur", "ozet", "kullanici",
                                      "ayrinti")}
    if olay.get("parola") is not None:
        govde["parola"] = maske(olay["parola"])
    return (f"{zaman} CAROTPOT kaynak={olay['kaynak']} hizmet={olay['hizmet']} "
            f"tur={olay['tur']} | " + json.dumps(govde, ensure_ascii=False))


def olay_satiri_coz(satir):
    if " CAROTPOT " not in satir or " | " not in satir:
        return None
    try:
        veri = json.loads(satir.split(" | ", 1)[1])
    except ValueError:
        return None
    return veri if isinstance(veri, dict) and "kaynak" in veri else None


# --------------------------------------------------------------------------
# Kayit (SQLite)
# --------------------------------------------------------------------------

class Depo:
    # Satir ust siniri (C-03): asilinca en eskiler silinir. Alanlar kisaltildigi
    # icin satir basina en fazla ~1,5 KB; tipik ~250 bayt.
    EN_COK_SATIR = 100_000
    BUDAMA_ARALIGI = 500        # bu kadar eklemede bir sayi denetlenir

    def __init__(self, yol, en_cok_satir=None):
        self.kilit = threading.Lock()
        self.en_cok_satir = en_cok_satir or self.EN_COK_SATIR
        self.eklenen = 0
        self.db = sqlite3.connect(str(yol), check_same_thread=False)
        # Silinen satirlarin yeri geri verilebilsin; eski dosyada bir kez VACUUM
        if self.db.execute("PRAGMA auto_vacuum").fetchone()[0] != 2:
            self.db.execute("PRAGMA auto_vacuum=INCREMENTAL")
            self.db.execute("VACUUM")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS olaylar (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL,
                 hizmet TEXT NOT NULL, kaynak TEXT NOT NULL, kaynak_port INTEGER,
                 hedef_port INTEGER, tur TEXT NOT NULL, kullanici TEXT,
                 parola TEXT, ayrinti TEXT)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS i_ts ON olaylar(ts)")
        self.db.execute("CREATE INDEX IF NOT EXISTS i_kaynak ON olaylar(kaynak)")
        self.db.commit()
        try:
            os.chmod(yol, 0o600)
        except OSError:
            pass

    def ekle(self, o):
        with self.kilit:
            self.db.execute(
                "INSERT INTO olaylar(ts,hizmet,kaynak,kaynak_port,hedef_port,tur,"
                "kullanici,parola,ayrinti) VALUES(?,?,?,?,?,?,?,?,?)",
                (o["ts"], o["hizmet"], o["kaynak"], o.get("kaynak_port"),
                 o.get("hedef_port"), o["tur"], o.get("kullanici"),
                 o.get("parola"), o.get("ayrinti")))
            self.eklenen += 1
            if self.eklenen >= self.BUDAMA_ARALIGI:
                self.eklenen = 0
                self._buda()
            self.db.commit()

    def _buda(self):
        """Satir sayisi siniri asildiysa en eskileri siler (kilit altinda)."""
        say = self.db.execute("SELECT COUNT(*) FROM olaylar").fetchone()[0]
        if say <= self.en_cok_satir:
            return 0
        # sinirin %90'i kalir; budama her eklemede yapilmasin
        kalan = self.en_cok_satir * 9 // 10
        sinir = self.db.execute("SELECT id FROM olaylar ORDER BY id DESC LIMIT 1 OFFSET ?",
                                (kalan - 1,)).fetchone()
        if not sinir:
            return 0
        c = self.db.execute("DELETE FROM olaylar WHERE id < ?", (sinir[0],))
        self.db.commit()
        self.db.execute("PRAGMA incremental_vacuum")
        LOG.warning("olay veritabani siniri (%d satir) asildi; en eski %d kayit silindi",
                    self.en_cok_satir, c.rowcount)
        return c.rowcount

    def temizle(self, gun):
        with self.kilit:
            c = self.db.execute("DELETE FROM olaylar WHERE ts < ?",
                                (time.time() - gun * 86400,))
            self.db.commit()
            self._buda()
            self.db.execute("PRAGMA incremental_vacuum")
            return c.rowcount

    def sorgu(self, sql, args=()):
        with self.kilit:
            return self.db.execute(sql, args).fetchall()


# --------------------------------------------------------------------------
# Webhook (istege bagli; yalniz kullanici acarsa)
# --------------------------------------------------------------------------

class Webhook:
    DAKIKADA_EN_COK = 10      # kaynak sayisindan bagimsiz genel sinir (C-04)

    def __init__(self, adres, bekleme):
        self.adres = adres
        self.bekleme = bekleme
        self.son = {}
        self.gonderilen = collections.deque()

    async def olay(self, kaynak, ozet):
        if not self.adres:
            return
        simdi = time.time()
        anahtar = sinir_anahtari(kaynak)
        if simdi - self.son.get(anahtar, 0) < self.bekleme:
            return
        while self.gonderilen and simdi - self.gonderilen[0] > 60:
            self.gonderilen.popleft()
        if len(self.gonderilen) >= self.DAKIKADA_EN_COK:
            return
        self.gonderilen.append(simdi)
        self.son[anahtar] = simdi
        if len(self.son) > 5000:
            for k in sorted(self.son, key=self.son.get)[:1000]:
                del self.son[k]
        metin = f"CarotPot: {webhook_arindir(ozet)}"
        # allowed_mentions: Discord hicbir anmayi (@everyone dahil) islemesin
        veri = json.dumps({"text": metin, "content": metin,
                           "allowed_mentions": {"parse": []}}).encode()

        def gonder():
            istek = urllib.request.Request(self.adres, data=veri,
                                           headers={"Content-Type": "application/json"})
            urllib.request.urlopen(istek, timeout=5).read()

        try:
            await asyncio.get_running_loop().run_in_executor(None, gonder)
        except Exception as hata:  # noqa: BLE001
            LOG.error("webhook gonderilemedi: %s", hata)


# --------------------------------------------------------------------------
# Cekirdek
# --------------------------------------------------------------------------

class CarotPot:
    ZAMAN_ASIMI = 15          # tek okuma icin
    TOPLAM_SURE = 60          # bir baglantinin en uzun suresi (C-01)
    EN_COK_BAGLANTI = 64      # butun tuzaklar (SSH dahil) icin eszamanli
    KAYNAK_BASINA_BAGLANTI = 8
    DAKIKADA_GENEL_OLAY = 1200   # kaynak sayisindan bagimsiz yazma siniri (C-03/C-04)

    def __init__(self, ayar, depo, gunluk):
        self.ayar = ayar
        self.depo = depo
        self.gunluk = gunluk
        self.webhook = Webhook(ayar["webhook"], ayar["bekleme"])
        self.yoksay = set(ayar["yoksay"])
        self.internet = bool(ayar.get("internet_kabul"))
        self.dinle = None      # None = tum arayuzler (calistir() belirler)
        self.acik_baglanti = 0
        self.kaynak_baglanti = collections.Counter()
        self.hiz = collections.defaultdict(collections.deque)
        self.genel_hiz = collections.deque()
        self.son_uyari = {}
        self.gorevler = set()     # ensure_future gorevleri cop toplanmasin (S-3)

    def kabul(self, ip):
        adr = adres_coz(ip)
        if adr is None or str(adr) in self.yoksay:
            return False
        if self.internet:
            return not (adr.is_unspecified or adr.is_multicast)
        return ozel_adres_mi(adr)

    def uyar(self, anahtar, metin, *arg):
        """Saldiri altinda gunluk selini onlemek icin dakikada bir uyari."""
        simdi = time.time()
        if simdi - self.son_uyari.get(anahtar, 0) >= 60:
            self.son_uyari[anahtar] = simdi
            LOG.warning(metin, *arg)

    def yer_al(self, ip):
        """Baglanti icin yer ayirir; dolu ise False (baglanti hemen kapatilir,
        kuyrukta beklemez). Basarili her cagri bir yer_birak ile eslenir."""
        anahtar = sinir_anahtari(ip)
        if (self.acik_baglanti >= self.EN_COK_BAGLANTI
                or self.kaynak_baglanti[anahtar] >= self.KAYNAK_BASINA_BAGLANTI):
            self.uyar("kapasite", "baglanti siniri dolu; fazla baglantilar kapatiliyor")
            return False
        self.acik_baglanti += 1
        self.kaynak_baglanti[anahtar] += 1
        return True

    def yer_birak(self, ip):
        anahtar = sinir_anahtari(ip)
        self.acik_baglanti = max(0, self.acik_baglanti - 1)
        self.kaynak_baglanti[anahtar] -= 1
        if self.kaynak_baglanti[anahtar] <= 0:
            del self.kaynak_baglanti[anahtar]

    def arka_plan(self, coro):
        gorev = asyncio.ensure_future(coro)
        self.gorevler.add(gorev)
        gorev.add_done_callback(self.gorevler.discard)
        return gorev

    def hiz_siniri(self, ip):
        simdi = time.time()
        g = self.genel_hiz
        while g and simdi - g[0] > 60:
            g.popleft()
        if len(g) >= self.DAKIKADA_GENEL_OLAY:
            self.uyar("hiz", "genel olay siniri asildi; fazla olaylar kaydedilmiyor")
            return False
        d = self.hiz[sinir_anahtari(ip)]
        while d and simdi - d[0] > 60:
            d.popleft()
        if len(d) >= self.ayar["dakikada_olay"]:
            return False
        d.append(simdi)
        g.append(simdi)
        if len(self.hiz) > 5000:
            for k in list(self.hiz)[:1000]:
                self.hiz.pop(k, None)
        return True

    async def kaydet(self, hizmet, kaynak, kaynak_port, hedef_port, tur, ozet,
                     kullanici=None, parola=None, ayrinti=None):
        kaynak = str(adres_coz(kaynak) or kaynak)
        if not self.hiz_siniri(kaynak):
            return
        olay = {"ts": time.time(), "hizmet": hizmet, "kaynak": kaynak,
                "kaynak_port": kaynak_port, "hedef_port": hedef_port, "tur": tur,
                "ozet": ozet, "kullanici": kullanici, "parola": parola,
                "ayrinti": ayrinti}
        self.depo.ekle(olay)
        self.gunluk.info(olay_satiri(olay))
        await self.webhook.olay(kaynak, f"{kaynak} → {hizmet} ({hedef_port}): {ozet}")

    @staticmethod
    def uclar(w):
        ip, port = w.get_extra_info("peername")[:2]
        return ip, port, w.get_extra_info("sockname")[1]

    def isleyici(self, hizmet, fonk, persona):
        """Bir tuzak modulunun isle() fonksiyonunu asyncio sunucusuna baglar:
        kabul denetimi, eszamanlilik siniri (islemeden once; dolu ise baglanti
        beklemeden kapatilir), toplam sure siniri, hata yakalama ve kapatma."""
        async def isle(r, w):
            try:
                ip, port, hport = self.uclar(w)
            except (TypeError, OSError):
                w.close()
                return
            if not self.kabul(ip) or not self.yer_al(ip):
                w.transport.abort()
                return

            async def kayit(tur, ozet, kullanici=None, parola=None, ayrinti=None):
                await self.kaydet(hizmet, ip, port, hport, tur, ozet,
                                  kullanici=kullanici, parola=parola, ayrinti=ayrinti)

            try:
                await asyncio.wait_for(fonk(kayit, r, w, persona, self.ZAMAN_ASIMI),
                                       self.TOPLAM_SURE)
            except (asyncio.TimeoutError, asyncio.IncompleteReadError,
                    asyncio.LimitOverrunError, ConnectionError, OSError,
                    ValueError, UnicodeError):
                pass
            except Exception as hata:  # noqa: BLE001 -- bir tuzak hatasi digerlerini durdurmasin
                LOG.error("%s tuzaginda beklenmeyen hata: %r", hizmet, hata)
            finally:
                self.yer_birak(ip)
                w.close()
        return isle


def durum_yaz(yol, veri):
    if not yol:
        return
    try:
        gecici = f"{yol}.yeni"
        with open(gecici, "w", encoding="utf-8") as fh:
            json.dump(veri, fh, ensure_ascii=False)
        os.chmod(gecici, 0o644)
        os.replace(gecici, yol)
    except OSError as hata:
        LOG.error("durum dosyasi yazilamadi: %s", hata)


async def calistir(a):
    ayar = ayar_oku(a.ayar)
    veri = Path(a.durum_dizini)
    veri.mkdir(parents=True, exist_ok=True)
    os.chmod(veri, 0o700)
    depo = Depo(veri / "olaylar.db")
    silinen = depo.temizle(ayar["sakla_gun"])
    if silinen:
        LOG.info("%d eski kayit silindi", silinen)

    gunluk = logging.getLogger("carotpot.olaylar")
    gunluk.propagate = False
    gunluk.setLevel(logging.INFO)
    if a.gunluk:
        Path(a.gunluk).parent.mkdir(parents=True, exist_ok=True)
        isleyici = logging.handlers.RotatingFileHandler(
            a.gunluk, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        isleyici.setFormatter(logging.Formatter("%(message)s"))
        gunluk.addHandler(isleyici)
        try:
            os.chmod(a.gunluk, 0o644)
        except OSError:
            pass

    kupu = CarotPot(ayar, depo, gunluk)
    # --dinle ayar dosyasindakini gecersiz kilar (Poligon tuzak laboratuvari)
    dinle = adres_coz(a.dinle) if a.dinle else adres_coz(ayar["dinle"])
    if a.dinle and dinle is None:
        LOG.error("Gecersiz dinleme adresi: %s", kes(a.dinle, 40))
        sys.exit(2)
    kupu.dinle = str(dinle) if dinle else None
    sunucular, acik, hatalar = [], {}, {}
    p, pers = ayar["portlar"], ayar["personalar"]
    for ad in tuzaklar.SIRA:
        if not p[ad]:
            continue
        modul = tuzaklar.MODULLER[ad]
        try:
            if hasattr(modul, "baslat"):
                sunucu, not_ = await modul.baslat(kupu, p[ad], veri, pers[ad])
                if not_:
                    hatalar[f"{ad}_tam"] = not_
            else:
                sunucu = await asyncio.start_server(
                    kupu.isleyici(ad, modul.isle, pers[ad]), kupu.dinle, p[ad], limit=8192)
            sunucular.append(sunucu)
            acik[ad] = p[ad]
        except OSError as hata:
            # Port baska bir program tarafindan kullaniliyorsa digerleri calisir
            hatalar[ad] = str(hata)
    for ad, hata in hatalar.items():
        LOG.warning("%s acilamadi: %s", ad, hata)
    durum_yaz(a.durum_dosyasi, {"baslangic": int(time.time()), "pid": os.getpid(),
                                "acik": acik, "hatalar": hatalar, "surum": SURUM,
                                "dinle": kupu.dinle or "",
                                "personalar": {k: pers[k] for k in acik}})
    if not acik:
        LOG.error("Hicbir tuzak baslatilamadi")
        sys.exit(1)
    LOG.info("CarotPot hazir: %s", ", ".join(f"{k}:{v}" for k, v in acik.items()))

    async def gunluk_temizlik():
        while True:
            await asyncio.sleep(86400)
            depo.temizle(ayar["sakla_gun"])

    gorev = asyncio.create_task(gunluk_temizlik())
    try:
        await asyncio.Event().wait()
    finally:
        gorev.cancel()
        for s in sunucular:
            s.close()


# --------------------------------------------------------------------------
# Oturum bildiricisi (kullanici olarak calisir)
# --------------------------------------------------------------------------

def hizmet_calisiyor_mu():
    try:
        return subprocess.run(["systemctl", "is-active", "--quiet", "carotpot"],
                              timeout=5).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


HIZMET_ADI = {ad: tuzaklar.MODULLER[ad].BASLIK for ad in tuzaklar.SIRA}


def _dilli(sozluk, lang):
    """{"tr","en"} sozlugunden metin; tr/en disindaki bir dilde Ingilizce. (Hizmet
    "python3 -I" ile calistigi icin ortak/dil.py'ye bagimli degil; bildirim
    metinleri henuz dil dosyalarindan cevrilmez.)"""
    return sozluk.get(lang) or sozluk.get("en") or sozluk.get("tr") or ""


def olay_aciklamasi(olay, lang):
    """Olayi arayuz dilinde aciklar (gunlukteki ozet alani Turkce ve
    yalnizca hizmet icindir)."""
    h = HIZMET_ADI.get(olay.get("hizmet"), str(olay.get("hizmet", "?")))
    tur, port = olay.get("tur"), olay.get("hedef_port")
    kul = olay.get("kullanici")
    if tur == "giris":
        metin = _dilli({"tr": f"{h} giriş denemesi", "en": f"{h} login attempt"}, lang)
        if kul:
            metin += _dilli({"tr": f", kullanıcı “{kul}”", "en": f", user “{kul}”"}, lang)
        return metin
    if tur == "baglanti":
        return _dilli({"tr": f"{h} bağlantısı", "en": f"{h} connection"}, lang)
    if tur == "istek":
        return _dilli({"tr": "Web paneli isteği", "en": "Web panel request"}, lang)
    if tur == "komut":
        komut = str(olay.get("ayrinti") or "").split(" ")[0].upper()[:20]
        return _dilli({"tr": f"{h} komutu {komut}".strip(), "en": f"{h} command {komut}".strip()}, lang)
    return _dilli({"tr": f"{h} tuzak portuna bağlantı ({port})",
                   "en": f"Connection to the {h} trap port ({port})"}, lang)


def bildirim_metni(olay, lang):
    baslik = _dilli({"tr": "CarotPot: ağda şüpheli hareket",
                     "en": "CarotPot: suspicious activity on the network"}, lang)
    return baslik, f"{olay['kaynak']}: {olay_aciklamasi(olay, lang)}"


def bildirim_ozeti(n, lang):
    """Bildirim siniri asildiginda gosterilmeyen kaynaklarin ozeti."""
    baslik = _dilli({"tr": "CarotPot: ağda şüpheli hareket",
                     "en": "CarotPot: suspicious activity on the network"}, lang)
    return baslik, _dilli({"tr": f"{n} kaynak daha tuzağa dokundu. Ayrıntılar CarotPot "
                                 f"uygulamasında.",
                           "en": f"{n} more sources touched the trap. See the CarotPot app "
                                 f"for details."}, lang)


class BildirimSiniri:
    """Kaynak sayisindan bagimsiz genel bildirim siniri (C-04): dakikada en
    fazla DAKIKADA_EN_COK bildirim; fazlasi sayilir ve yer acilinca tek bir
    ozet bildirimiyle gosterilir."""
    DAKIKADA_EN_COK = 3

    def __init__(self):
        self.zamanlar = collections.deque()
        self.bekleyen = 0

    def _temizle(self, simdi):
        while self.zamanlar and simdi - self.zamanlar[0] > 60:
            self.zamanlar.popleft()

    def izin(self, simdi):
        self._temizle(simdi)
        if len(self.zamanlar) >= self.DAKIKADA_EN_COK:
            self.bekleyen += 1
            return False
        self.zamanlar.append(simdi)
        return True

    def ozet_al(self, simdi):
        """Gosterilmesi gereken ozet sayisi (0 = yok)."""
        self._temizle(simdi)
        if not self.bekleyen or len(self.zamanlar) >= self.DAKIKADA_EN_COK:
            return 0
        n, self.bekleyen = self.bekleyen, 0
        self.zamanlar.append(simdi)
        return n


def bildirim_goster(baslik, govde):
    # Govde isaretleme kabul eder (xfce4-notifyd body-markup); saldirganin
    # yazdigi metin kacislanir (C-05).
    govde = bildirim_arindir(govde)
    if shutil.which("notify-send"):
        try:
            subprocess.run(["notify-send", "-u", "critical", "-a", "CarotPot",
                            "-i", "carotpot", baslik, govde], timeout=5,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            pass


def bildir(a):
    """Oturumda calisir. Tuzak gunlugunu izler: her kaynak icin ilk olayda
    hemen, sonra en fazla bekleme suresinde bir kez bildirim gosterir.
    Ayrica kanarya dosyalari izler. Hizmet durdugunda ve izlenecek kanarya
    kalmadiginda cikar."""
    import kanarya
    ayar = ayar_oku(a.ayar)
    bekleme = ayar["bekleme"]
    lang = "tr" if os.environ.get("LANG", "").lower().startswith("tr") else "en"
    son = {}
    sinir = BildirimSiniri()
    konum = None
    son_denetim = 0
    izleyici = kanarya.Izleyici()
    try:
        while True:
            simdi = time.time()
            if simdi - son_denetim > 30:
                son_denetim = simdi
                izleyici.yeniden_yukle()
                if not hizmet_calisiyor_mu() and not izleyici.kanarya_var_mi():
                    return 0
            try:
                boyut = os.path.getsize(a.gunluk)
                if konum is None or boyut < konum:   # ilk acilis ya da dondurme
                    konum = boyut if konum is None else 0
                if boyut > konum:
                    with open(a.gunluk, encoding="utf-8", errors="replace") as fh:
                        fh.seek(konum)
                        satirlar = fh.read(256_000).splitlines()
                        konum = fh.tell()
                    for satir in satirlar:
                        olay = olay_satiri_coz(satir)
                        if not olay:
                            continue
                        anahtar = sinir_anahtari(olay["kaynak"])
                        if simdi - son.get(anahtar, 0) < bekleme:
                            continue
                        son[anahtar] = simdi
                        if len(son) > 5000:
                            for k in sorted(son, key=son.get)[:1000]:
                                del son[k]
                        if sinir.izin(simdi):
                            bildirim_goster(*bildirim_metni(olay, lang))
            except OSError:
                pass
            n = sinir.ozet_al(simdi)
            if n:
                bildirim_goster(*bildirim_ozeti(n, lang))
            if izleyici.kanarya_var_mi():
                for olay in izleyici.bekle(2):
                    bildirim_goster(*kanarya.bildirim_metni(olay, lang))
            else:
                time.sleep(2)
    finally:
        izleyici.kapat()


# --------------------------------------------------------------------------
# Rapor
# --------------------------------------------------------------------------

def rapor(a):
    yol = Path(a.durum_dizini) / "olaylar.db"
    if not yol.exists():
        print("Henuz kayit yok.")
        return
    depo = Depo(yol)
    t0 = time.time() - 86400
    toplam, kaynak_say = depo.sorgu(
        "SELECT COUNT(*), COUNT(DISTINCT kaynak) FROM olaylar WHERE ts>=?", (t0,))[0]
    print(f"CarotPot raporu (son 24 saat): {toplam} olay, {kaynak_say} kaynak")
    for ip, n, hz in depo.sorgu(
            "SELECT kaynak, COUNT(*), GROUP_CONCAT(DISTINCT hizmet) FROM olaylar"
            " WHERE ts>=? GROUP BY kaynak ORDER BY 2 DESC LIMIT 10", (t0,)):
        print(f"  {ip:<40} {n:>5}  [{hz}]")


def ayrisici():
    p = argparse.ArgumentParser(prog="carotpot", description="CarotOS yerel ag tuzagi")
    p.add_argument("--ayar", default=AYAR_DOSYASI)
    p.add_argument("--durum-dizini", default=VERI_DIZINI)
    p.add_argument("--gunluk", default=GUNLUK_DOSYASI)
    p.add_argument("--durum-dosyasi", default=DURUM_DOSYASI)
    p.add_argument("--dinle", default="",
                   help="yalniz bu adreste dinle (ornek 127.0.0.1); bos = ayar dosyasi")
    p.add_argument("--surum", action="version", version=f"carotpot {SURUM}")
    p.add_argument("komut", choices=("run", "bildir", "report"))
    return p


def main(argv=None):
    a = ayrisici().parse_args(argv)
    if a.komut == "report":
        return rapor(a)
    if a.komut == "bildir":
        return bildir(a)
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("Uyari: CarotPot root olarak calistirilmamalidir.", file=sys.stderr)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(levelname)s %(message)s")
    # asyncssh her baglantida adres ayrintisi yazar; olaylar zaten gunlukte
    logging.getLogger("asyncssh").setLevel(logging.WARNING)
    try:
        asyncio.run(calistir(a))
    except KeyboardInterrupt:
        LOG.info("Durduruldu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
