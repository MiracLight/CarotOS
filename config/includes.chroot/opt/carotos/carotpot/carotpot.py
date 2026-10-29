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
  * Yalnizca ozel ag adreslerinden gelen baglantilar kaydedilir.
  * Yuksek portlar kullanilir; hizmet yetkisiz "carotpot" kullanicisiyla ve
    kisitli bir systemd biriminde calisir (karar D5).
  * Okuma boyutu, sure, eszamanli baglanti ve kaynak basina olay sayisi
    sinirlidir.
  * Olay gunlugunde parolalar maskelidir; tam parola yalnizca hizmetin kendi
    veritabaninda (0700 dizin) tutulur.

Kullanim:
  carotpot.py run   --ayar /etc/carotpot/ayarlar.json   tuzaklari baslatir (hizmet)
  carotpot.py bildir                                     oturumda bildirim gosterir,
                                                         kanarya dosyalari izler
  carotpot.py report --since 24h                         ozet rapor
"""

import argparse
import asyncio
import collections
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
    def __init__(self, yol):
        self.kilit = threading.Lock()
        self.db = sqlite3.connect(str(yol), check_same_thread=False)
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
            self.db.commit()

    def temizle(self, gun):
        with self.kilit:
            c = self.db.execute("DELETE FROM olaylar WHERE ts < ?",
                                (time.time() - gun * 86400,))
            self.db.commit()
            return c.rowcount

    def sorgu(self, sql, args=()):
        with self.kilit:
            return self.db.execute(sql, args).fetchall()


# --------------------------------------------------------------------------
# Webhook (istege bagli; yalniz kullanici acarsa)
# --------------------------------------------------------------------------

class Webhook:
    def __init__(self, adres, bekleme):
        self.adres = adres
        self.bekleme = bekleme
        self.son = {}

    async def olay(self, kaynak, ozet):
        if not self.adres:
            return
        simdi = time.time()
        if simdi - self.son.get(kaynak, 0) < self.bekleme:
            return
        self.son[kaynak] = simdi
        if len(self.son) > 5000:
            for k in sorted(self.son, key=self.son.get)[:1000]:
                del self.son[k]
        metin = f"CarotPot: {ozet}"
        veri = json.dumps({"text": metin, "content": metin}).encode()

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
    ZAMAN_ASIMI = 15
    EN_COK_BAGLANTI = 64

    def __init__(self, ayar, depo, gunluk):
        self.ayar = ayar
        self.depo = depo
        self.gunluk = gunluk
        self.webhook = Webhook(ayar["webhook"], ayar["bekleme"])
        self.yoksay = set(ayar["yoksay"])
        self.dinle = None      # None = tum arayuzler (calistir() belirler)
        self.kapasite = asyncio.Semaphore(self.EN_COK_BAGLANTI)
        self.hiz = collections.defaultdict(collections.deque)

    def kabul(self, ip):
        adr = adres_coz(ip)
        if adr is None or str(adr) in self.yoksay:
            return False
        return ozel_adres_mi(adr)

    def hiz_siniri(self, ip):
        simdi = time.time()
        d = self.hiz[ip]
        while d and simdi - d[0] > 60:
            d.popleft()
        if len(d) >= self.ayar["dakikada_olay"]:
            return False
        d.append(simdi)
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
        await self.webhook.olay(kaynak, f"{kaynak} -> {hizmet} ({hedef_port}): {ozet}")

    @staticmethod
    def uclar(w):
        ip, port = w.get_extra_info("peername")[:2]
        return ip, port, w.get_extra_info("sockname")[1]

    def isleyici(self, hizmet, fonk, persona):
        """Bir tuzak modulunun isle() fonksiyonunu asyncio sunucusuna baglar:
        kabul denetimi, eszamanlilik siniri, hata yakalama ve kapatma."""
        async def isle(r, w):
            try:
                ip, port, hport = self.uclar(w)
            except (TypeError, OSError):
                w.close()
                return
            if not self.kabul(ip):
                w.close()
                return

            async def kayit(tur, ozet, kullanici=None, parola=None, ayrinti=None):
                await self.kaydet(hizmet, ip, port, hport, tur, ozet,
                                  kullanici=kullanici, parola=parola, ayrinti=ayrinti)

            async with self.kapasite:
                try:
                    await fonk(kayit, r, w, persona, self.ZAMAN_ASIMI)
                except (asyncio.TimeoutError, asyncio.IncompleteReadError,
                        asyncio.LimitOverrunError, ConnectionError, OSError,
                        ValueError, UnicodeError):
                    pass
                except Exception as hata:  # noqa: BLE001 -- bir tuzak hatasi digerlerini durdurmasin
                    LOG.error("%s tuzaginda beklenmeyen hata: %r", hizmet, hata)
                finally:
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


def olay_aciklamasi(olay, lang):
    """Olayi arayuz dilinde aciklar (gunlukteki ozet alani Turkce ve
    yalnizca hizmet icindir)."""
    h = HIZMET_ADI.get(olay.get("hizmet"), str(olay.get("hizmet", "?")))
    tur, port = olay.get("tur"), olay.get("hedef_port")
    kul = olay.get("kullanici")
    if tur == "giris":
        metin = {"tr": f"{h} giriş denemesi", "en": f"{h} login attempt"}[lang]
        if kul:
            metin += {"tr": f", kullanıcı “{kul}”", "en": f", user “{kul}”"}[lang]
        return metin
    if tur == "baglanti":
        return {"tr": f"{h} bağlantısı", "en": f"{h} connection"}[lang]
    if tur == "istek":
        return {"tr": "Web paneli isteği", "en": "Web panel request"}[lang]
    if tur == "komut":
        komut = str(olay.get("ayrinti") or "").split(" ")[0].upper()[:20]
        return {"tr": f"{h} komutu {komut}".strip(), "en": f"{h} command {komut}".strip()}[lang]
    return {"tr": f"{h} tuzak portuna bağlantı ({port})",
            "en": f"Connection to the {h} trap port ({port})"}[lang]


def bildirim_metni(olay, lang):
    baslik = {"tr": "CarotPot: ağda şüpheli hareket",
              "en": "CarotPot: suspicious activity on the network"}[lang]
    return baslik, f"{olay['kaynak']}: {olay_aciklamasi(olay, lang)}"


def bildirim_goster(baslik, govde):
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
                        if not olay or simdi - son.get(olay["kaynak"], 0) < bekleme:
                            continue
                        son[olay["kaynak"]] = simdi
                        bildirim_goster(*bildirim_metni(olay, lang))
            except OSError:
                pass
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
