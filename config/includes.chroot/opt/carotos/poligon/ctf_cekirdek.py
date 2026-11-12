# -*- coding: utf-8 -*-
"""CarotOS Poligon CTF -- sunucu tarafi cekirdek (GTK'siz, yalnizca standart kutuphane).

Ilke: HAKEM SUNUCUDUR. Istemci yalnizca bayrak metnini gonderir; dogrulamayi ve puani sunucu yapar.
  * Bayrak her ogrenci icin oturum sirrindan HMAC ile turetilir: bir ogrencinin bayragi digerine yaramaz.
  * Sunucu bayragi diske yazmaz; dosyayi oturum sirrindan yeniden uretip karsilastirir (sabit sureli
    karsilastirma). Uretilen dosyalar bellekte sinirli bir onbellekte tutulur (her istekte yeniden uretim
    sunucuyu yavaslatmasin diye).
  * Puan zamanla azalir (cozen sayisina gore), ilk cozum bonusu ve ipucu cezasi vardir.
  * Yanlis denemede bekleme (kaba kuvveti yavaslatir), sure ve skor dondurma vardir.
  * Skor, degistirilemez bir olay listesinden (cozumler + ipuclari) HER SEFERINDE yeniden hesaplanir.

Saat enjekte edilebilir (testler gercek zaman beklemez). Varsayilan saat TEKDUZEDIR (time.monotonic):
yarisma sirasinda sistem saati duzeltilirse (NTP, elle ayar) kalan sure uzamaz ya da kisalmaz.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import hmac
import io
import json
import os
import random
import secrets
import threading
import time

import ctf_uretici as U

KATEGORILER = ("kodlama", "kriptografi", "hash", "log", "adli")
ZORLUKLAR = ("kolay", "orta", "zor")
MAKS_BAYRAK = 200                  # gonderilen bayrak metni sinirlari
YANLIS_PENCERE = 60.0              # sn: bu surede
YANLIS_LIMIT = 5                   # bu kadar yanlis denemeden sonra
YANLIS_BEKLEME = 30.0              # sn: son yanlis denemeden itibaren beklenir
ILK_COZUM_ORANI = 0.10             # ilk cozene taban puanin %10'u bonus
MIN_ORAN = 0.30                    # puan, tabanin en fazla %30'una kadar duser
AZALMA_VARSAYILAN = 10             # bu kadar cozumde en dusuk puana inilir
URETIM_ONBELLEGI = 256             # bellekte tutulan (ogrenci, gorev) dosyasi sayisi (en eski kullanilan atilir)

DURUMLAR = ("hazir", "surec", "bitti")


class CtfHata(Exception):
    """Kullaniciya gosterilebilir, kisa kodlu hata."""

    def __init__(self, kod: str):
        super().__init__(kod)
        self.kod = kod


def gorevleri_yukle(yol: str | None = None) -> dict:
    """ctf/gorevler.json dosyasini okur ve DOGRULAR. Kimlik -> gorev sozlugu. Bozuk tanim hemen hata verir."""
    if yol is None:
        yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ctf", "gorevler.json")
    with open(yol, encoding="utf-8") as f:
        ham = json.load(f)
    gorevler = {}
    for g in ham["gorevler"]:
        _gorev_dogrula(g)
        if g["id"] in gorevler:
            raise ValueError("yinelenen CTF gorevi: " + g["id"])
        gorevler[g["id"]] = g
    return gorevler


def _gorev_dogrula(g: dict) -> None:
    for alan in ("id", "kategori", "zorluk", "baslik", "aciklama", "uretici", "puan"):
        if alan not in g:
            raise ValueError("CTF gorevinde '%s' yok: %s" % (alan, g.get("id")))
    if g["kategori"] not in KATEGORILER or g["zorluk"] not in ZORLUKLAR:
        raise ValueError("gecersiz kategori/zorluk: " + g["id"])
    if g["uretici"] not in U.URETICILER:
        raise ValueError("bilinmeyen uretici: " + g["uretici"])
    if not isinstance(g["puan"], int) or g["puan"] <= 0:
        raise ValueError("gecersiz puan: " + g["id"])
    for dil in ("tr", "en"):
        if not str(g["baslik"].get(dil, "")).strip() or not str(g["aciklama"].get(dil, "")).strip():
            raise ValueError("CTF gorevinde %s metni bos: %s" % (dil, g["id"]))
    for ip in g.get("ipuclari", []):
        if not (str(ip["tr"]).strip() and str(ip["en"]).strip()) or int(ip["ceza"]) < 0:
            raise ValueError("gecersiz ipucu: " + g["id"])


def _hmac(sir: bytes, *parcalar: str) -> bytes:
    return hmac.new(sir, "|".join(parcalar).encode("utf-8"), hashlib.sha256).digest()


class CtfOturumu:
    """Bir CTF yarismasinin tum durumu (bellek ici; oda kapaninca biter)."""

    def __init__(self, gorevler: dict | None = None, saat=time.monotonic, sir: bytes | None = None,
                 azalma: int = AZALMA_VARSAYILAN):
        self.gorevler = dict(gorevler if gorevler is not None else gorevleri_yukle())
        self.saat = saat
        self._sir = sir or secrets.token_bytes(32)
        self.azalma = max(2, int(azalma))
        self._kilit = threading.RLock()
        self.baslangic: float | None = None
        self.bitis: float | None = None
        self.dondurma: float | None = None         # bu andan sonraki olaylar skor tablosunda gorunmez
        self.manuel_bitti = False
        self.acik_idler: list[str] = []
        self.cozumler: list[dict] = []             # {ogrenci, gorev, zaman}
        self.ipuclari: list[dict] = []             # {ogrenci, gorev, no, ceza, zaman}
        self._yanlislar: dict[str, list[float]] = {}
        self.deneme_sayisi: dict[tuple, int] = {}  # (ogrenci, gorev) -> toplam deneme
        self._uretimler: collections.OrderedDict = collections.OrderedDict()   # (ogrenci, gorev) -> (ad, icerik, bayrak)

    # -- yonetim (ogretmen) -----------------------------------------------------------------------------
    def baslat(self, sure_dk: float, gorev_idleri: list[str] | None = None, dondurma_dk: float = 0) -> None:
        with self._kilit:
            if self.durum() == "surec":
                raise CtfHata("zaten_suruyor")
            idler = list(gorev_idleri) if gorev_idleri else sorted(self.gorevler)
            bilinmeyen = [i for i in idler if i not in self.gorevler]
            if bilinmeyen:
                raise CtfHata("bilinmeyen_gorev")
            if not idler:
                raise CtfHata("gorev_yok")
            if not (1 <= float(sure_dk) <= 24 * 60) or not (0 <= float(dondurma_dk) < float(sure_dk)):
                raise CtfHata("gecersiz_sure")
            su = self.saat()
            self.acik_idler = idler
            self.baslangic = su
            self.bitis = su + float(sure_dk) * 60
            self.dondurma = self.bitis - float(dondurma_dk) * 60 if dondurma_dk else None
            self.manuel_bitti = False
            self.cozumler, self.ipuclari = [], []
            self._yanlislar, self.deneme_sayisi = {}, {}
            self._sir = secrets.token_bytes(32)    # her yarisma yeni bayraklar uretir
            self._uretimler.clear()                # eski sirla uretilmis dosyalar gecersiz

    def bitir(self) -> None:
        with self._kilit:
            self.manuel_bitti = True

    def durum(self) -> str:
        with self._kilit:
            if self.baslangic is None:
                return "hazir"
            if self.manuel_bitti or self.saat() >= (self.bitis or 0):
                return "bitti"
            return "surec"

    def kalan_sn(self) -> int:
        with self._kilit:
            if self.durum() != "surec":
                return 0
            return max(0, int(self.bitis - self.saat()))

    def donuk_mu(self) -> bool:
        with self._kilit:
            return self.durum() == "surec" and self.dondurma is not None and self.saat() >= self.dondurma

    # -- gorev dosyasi ve bayrak -----------------------------------------------------------------------------
    def _uret(self, ogrenci: str, gorev_id: str):
        """(dosya_adi, icerik, bayrak). Kilit ALINMIS olarak cagrilir. Sonuc belirlenimci oldugu icin
        onbellege alinir: bir ogrenci /ctf/dosya'yi art arda isteyerek sunucuyu mesgul edemez."""
        anahtar = (ogrenci, gorev_id)
        kayit = self._uretimler.get(anahtar)
        if kayit is not None:
            self._uretimler.move_to_end(anahtar)
            return kayit
        g = self.gorevler[gorev_id]
        rng = random.Random(int.from_bytes(_hmac(self._sir, "rng", gorev_id, ogrenci)[:16], "big"))
        ctx = U.Baglam(rng, _hmac(self._sir, "bayrak", gorev_id, ogrenci).hex())
        kayit = U.URETICILER[g["uretici"]](ctx, g.get("parametreler") or {})
        self._uretimler[anahtar] = kayit
        while len(self._uretimler) > URETIM_ONBELLEGI:
            self._uretimler.popitem(last=False)
        return kayit

    def dosya(self, ogrenci: str, gorev_id: str) -> tuple[str, str]:
        with self._kilit:
            self._gorev_acik_mi(gorev_id)
            if self.durum() == "hazir":
                raise CtfHata("baslamadi")
            ad, icerik, _bayrak = self._uret(ogrenci, gorev_id)
            return ad, icerik

    def _gorev_acik_mi(self, gorev_id: str) -> None:
        if gorev_id not in self.gorevler or gorev_id not in self.acik_idler:
            raise CtfHata("bilinmeyen_gorev")

    # -- puanlama -------------------------------------------------------------------------------------------------
    def _deger(self, gorev_id: str, cozen_sayisi: int) -> int:
        taban = self.gorevler[gorev_id]["puan"]
        en_az = max(1, int(round(taban * MIN_ORAN)))
        if cozen_sayisi >= self.azalma:
            return en_az
        oran = (max(0, cozen_sayisi - 1) / float(self.azalma - 1)) ** 2 if cozen_sayisi > 1 else 0.0
        return max(en_az, int(round(taban - (taban - en_az) * oran)))

    def puan_simdi(self, gorev_id: str) -> int:
        with self._kilit:
            return self._deger(gorev_id, self._cozen_sayisi(gorev_id) + 1)

    def _cozen_sayisi(self, gorev_id: str, kesim: float | None = None) -> int:
        return sum(1 for c in self.cozumler if c["gorev"] == gorev_id and (kesim is None or c["zaman"] <= kesim))

    def _ilk_cozen(self, gorev_id: str, kesim: float | None = None):
        for c in self.cozumler:                       # liste zaman sirasiyla eklenir
            if c["gorev"] == gorev_id and (kesim is None or c["zaman"] <= kesim):
                return c["ogrenci"]
        return None

    def _ipucu_cezasi(self, ogrenci: str, gorev_id: str, kesim: float | None = None) -> int:
        return sum(i["ceza"] for i in self.ipuclari if i["ogrenci"] == ogrenci and i["gorev"] == gorev_id
                   and (kesim is None or i["zaman"] <= kesim))

    def _kazanilan(self, c: dict, kesim: float | None) -> dict:
        g = c["gorev"]
        deger = self._deger(g, self._cozen_sayisi(g, kesim))
        ceza = self._ipucu_cezasi(c["ogrenci"], g, kesim)
        bonus = int(round(self.gorevler[g]["puan"] * ILK_COZUM_ORANI)) if self._ilk_cozen(g, kesim) == c["ogrenci"] else 0
        return {"gorev": g, "puan": max(0, deger - ceza) + bonus, "bonus": bonus, "ceza": ceza,
                "zaman": c["zaman"]}

    # -- ogrenci eylemleri ----------------------------------------------------------------------------------------
    def gonder(self, ogrenci: str, gorev_id: str, bayrak: str) -> dict:
        """Dondurur: {"sonuc": "dogru"|"yanlis"|"bekle"|"zaten"|"baslamadi"|"bitti", ...}. Yanlis girdi hata atmaz."""
        with self._kilit:
            durum = self.durum()
            if durum == "hazir":
                return {"sonuc": "baslamadi"}
            if durum == "bitti":
                return {"sonuc": "bitti"}
            self._gorev_acik_mi(gorev_id)
            if not isinstance(bayrak, str) or not bayrak.strip() or len(bayrak) > MAKS_BAYRAK:
                return {"sonuc": "yanlis"}
            if self._cozdu_mu(ogrenci, gorev_id):
                return {"sonuc": "zaten"}
            simdi = self.saat()
            gecmis = [t for t in self._yanlislar.get(ogrenci, []) if simdi - t < YANLIS_PENCERE]
            self._yanlislar[ogrenci] = gecmis
            if len(gecmis) >= YANLIS_LIMIT and simdi - gecmis[-1] < YANLIS_BEKLEME:
                return {"sonuc": "bekle", "bekleme_sn": int(YANLIS_BEKLEME - (simdi - gecmis[-1])) + 1}
            self.deneme_sayisi[(ogrenci, gorev_id)] = self.deneme_sayisi.get((ogrenci, gorev_id), 0) + 1
            beklenen = self._uret(ogrenci, gorev_id)[2]
            if hmac.compare_digest(beklenen.encode("utf-8"), bayrak.strip().encode("utf-8")):
                self.cozumler.append({"ogrenci": ogrenci, "gorev": gorev_id, "zaman": simdi})
                k = self._kazanilan(self.cozumler[-1], None)
                return {"sonuc": "dogru", "puan": k["puan"], "bonus": k["bonus"], "ceza": k["ceza"]}
            gecmis.append(simdi)
            return {"sonuc": "yanlis"}

    def _cozdu_mu(self, ogrenci: str, gorev_id: str) -> bool:
        return any(c["ogrenci"] == ogrenci and c["gorev"] == gorev_id for c in self.cozumler)

    def ipucu_al(self, ogrenci: str, gorev_id: str, no: int) -> dict:
        """no: 0'dan baslayan ipucu sirasi. Ipuclari SIRAYLA acilir; ceza cozumde puandan dusulur."""
        with self._kilit:
            if self.durum() != "surec":
                raise CtfHata("surec_degil")
            self._gorev_acik_mi(gorev_id)
            ipuclari = self.gorevler[gorev_id].get("ipuclari", [])
            if not isinstance(no, int) or isinstance(no, bool) or not (0 <= no < len(ipuclari)):
                raise CtfHata("gecersiz_ipucu")
            acilan = {i["no"] for i in self.ipuclari if i["ogrenci"] == ogrenci and i["gorev"] == gorev_id}
            if no not in acilan:
                if any(k not in acilan for k in range(no)):
                    raise CtfHata("once_oncekini_ac")
                if self._cozdu_mu(ogrenci, gorev_id):
                    raise CtfHata("zaten_cozuldu")
                self.ipuclari.append({"ogrenci": ogrenci, "gorev": gorev_id, "no": no,
                                      "ceza": int(ipuclari[no]["ceza"]), "zaman": self.saat()})
            ip = ipuclari[no]
            return {"tr": ip["tr"], "en": ip["en"], "ceza": int(ip["ceza"])}

    # -- gorunumler ------------------------------------------------------------------------------------------------------
    def ogrenci_gorevleri(self, ogrenci: str) -> list[dict]:
        """Ogrenciye gosterilen liste. BAYRAK/COZUM BILGISI ICERMEZ."""
        with self._kilit:
            if self.durum() == "hazir":
                return []
            acilan = {(i["ogrenci"], i["gorev"], i["no"]) for i in self.ipuclari}
            # Skor tablosu donukken gorev basina cozen sayisi ve guncel puan da donma anindaki haliyle
            # verilir; yoksa dondurmanin gizledigi bilgi (kim hala cozuyor) bu listeden okunurdu.
            kesim = self.dondurma if (self.dondurma is not None and
                                      (self.donuk_mu() or self.durum() == "bitti")) else None
            sonuc = []
            for gid in self.acik_idler:
                g = self.gorevler[gid]
                ipuclari = g.get("ipuclari", [])
                sonuc.append({
                    "id": gid, "kategori": g["kategori"], "zorluk": g["zorluk"], "baslik": g["baslik"],
                    "aciklama": g["aciklama"], "puan": self._deger(gid, self._cozen_sayisi(gid, kesim) + 1),
                    "cozen": self._cozen_sayisi(gid, kesim), "cozuldu": self._cozdu_mu(ogrenci, gid),
                    "ipucu_sayisi": len(ipuclari),
                    "ipucu_acilan": sum(1 for k in range(len(ipuclari)) if (ogrenci, gid, k) in acilan),
                    "ipucu_cezalari": [int(i["ceza"]) for i in ipuclari],
                    "deneme": self.deneme_sayisi.get((ogrenci, gid), 0),
                })
            return sonuc

    def acilan_ipuclari(self, ogrenci: str, gorev_id: str) -> list[dict]:
        with self._kilit:
            self._gorev_acik_mi(gorev_id)
            ipuclari = self.gorevler[gorev_id].get("ipuclari", [])
            nolar = sorted(i["no"] for i in self.ipuclari if i["ogrenci"] == ogrenci and i["gorev"] == gorev_id)
            return [{"no": k, "tr": ipuclari[k]["tr"], "en": ipuclari[k]["en"], "ceza": int(ipuclari[k]["ceza"])}
                    for k in nolar]

    def skor_tablosu(self, ogretmen: bool = False) -> dict:
        """Siralama. Ogrenci gorunumu donuk andaki durumu gosterir; ogretmen (ogretmen=True) gercek durumu."""
        with self._kilit:
            kesim = self.dondurma if (self.dondurma is not None and not ogretmen and
                                      (self.donuk_mu() or self.durum() == "bitti")) else None
            satirlar: dict[str, dict] = {}
            for c in self.cozumler:
                if kesim is not None and c["zaman"] > kesim:
                    continue
                k = self._kazanilan(c, kesim)
                s = satirlar.setdefault(c["ogrenci"], {"ad": c["ogrenci"], "puan": 0, "cozulen": 0,
                                                       "son": 0.0, "bonus": 0})
                s["puan"] += k["puan"]
                s["bonus"] += k["bonus"]
                s["cozulen"] += 1
                s["son"] = max(s["son"], c["zaman"])
            liste = sorted(satirlar.values(), key=lambda s: (-s["puan"], s["son"], s["ad"].lower()))
            for sira, s in enumerate(liste, 1):
                s["sira"] = sira
                s["son_sn"] = int(s.pop("son") - (self.baslangic or 0))
            return {"donuk": kesim is not None, "durum": self.durum(), "kalan_sn": self.kalan_sn(),
                    "satirlar": liste}

    def csv_metni(self) -> str:
        """Ogretmen icin sonuc tablosu (gercek, donmamis durum)."""
        with self._kilit:
            tablo = self.skor_tablosu(ogretmen=True)
            cikti = io.StringIO()
            yaz = csv.writer(cikti)
            yaz.writerow(["sira", "ogrenci", "puan", "cozulen", "ilk_cozum_bonusu", "son_cozum_sn"])
            for s in tablo["satirlar"]:
                yaz.writerow([s["sira"], _csv_guvenli(s["ad"]), s["puan"], s["cozulen"], s["bonus"], s["son_sn"]])
            return cikti.getvalue()

    def gorev_istatistigi(self) -> list[dict]:
        """Ogretmen: her gorev icin cozen sayisi ve toplam deneme."""
        with self._kilit:
            return [{"id": gid, "kategori": self.gorevler[gid]["kategori"], "cozen": self._cozen_sayisi(gid),
                     "deneme": sum(v for (o, g), v in self.deneme_sayisi.items() if g == gid)}
                    for gid in self.acik_idler]


def _csv_guvenli(metin: str) -> str:
    """Tablo programlarinda formul olarak calismasin (CSV enjeksiyonu)."""
    return "'" + metin if metin[:1] in ("=", "+", "-", "@", "\t", "\r") else metin
