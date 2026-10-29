# -*- coding: utf-8 -*-
"""
Former -- animasyon zaman cizelgesi (GTK'siz).

Bir "sahne" (ekranin sade bir kopyasi) ve bir "adim listesi" alir; adimlari
zamana dizer. durum(t), t milisaniyesinde ekranda ne gorundugunu verir:
imlecin yeri, yazilmis metinler, acik balon, cikti satirlari...

Cizim bu modulde degildir (former_cizim.py); boylece ayni cizelge testlerde
GTK olmadan sinanabilir ve her an herhangi bir yere atlanabilir.

Sahne:
    {"genislik": 760, "yukseklik": 420, "vurgu": "guvenlik", "sayfa": "ana",
     "baslik": T, "ogeler": [oge, ...]}
Oge (ortak alanlar): id, tur, x, y, w, h; istege bagli: sayfa (yalniz o sayfada
gorunur), bayrak (yalniz bayrak acikken gorunur), metin, deger, aktif ...
Adimlar: git, tikla, yaz, sec, balon, balon_kapat, cikti, say, ilerle,
ayarla, bekle (asagidaki yardimcilarla uretilir).
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Sureler (milisaniye)
# ---------------------------------------------------------------------------
OKUMA_HARF_MS = 42        # balonun okunmasi icin harf basina
OKUMA_EN_AZ_MS = 2400
OKUMA_EN_COK_MS = 11000
YAZ_HARF_MS = 75
TIK_MS = 380
SEC_MS = 1300
CIKTI_SATIR_MS = 170
BITIS_BEKLEME_MS = 2200


def T(tr: str, en: str) -> dict:
    """Iki dilli metin."""
    return {"tr": tr, "en": en}


def metin_al(m, dil: str) -> str:
    if isinstance(m, dict):
        return m.get(dil) or m.get("tr") or ""
    return "" if m is None else str(m)


# ---------------------------------------------------------------------------
# Adim ureticileri
# ---------------------------------------------------------------------------
def git(hedef, dx=0, dy=0, sure=None):
    return {"tur": "git", "hedef": hedef, "dx": dx, "dy": dy, "sure": sure}


def tikla(hedef, **etki):
    """etki: sayfa=..., bayrak={ad: bool}, ayarla={id: {ozellik: deger}}"""
    return {"tur": "tikla", "hedef": hedef, "etki": etki}


def yaz(hedef, metin):
    return {"tur": "yaz", "hedef": hedef, "metin": metin}


def sec(hedef, indeks):
    return {"tur": "sec", "hedef": hedef, "indeks": indeks}


def balon(hedef, baslik, metin, yon="auto"):
    return {"tur": "balon", "hedef": hedef, "baslik": baslik, "metin": metin, "yon": yon}


def balon_kapat():
    return {"tur": "balon_kapat"}


def cikti(hedef, satirlar, aralik=CIKTI_SATIR_MS):
    return {"tur": "cikti", "hedef": hedef, "satirlar": list(satirlar), "aralik": aralik}


def say(hedef, bas, son, sure, bicim):
    return {"tur": "say", "hedef": hedef, "bas": bas, "son": son, "sure": sure, "bicim": bicim}


def ilerle(hedef, son, sure):
    return {"tur": "ilerle", "hedef": hedef, "son": son, "sure": sure}


def ayarla(**degisiklik):
    """ayarla(id={"metin": ..., "aktif": True}, ...) ve ozel anahtarlar: _sayfa, _bayrak"""
    return {"tur": "ayarla", "degisiklik": degisiklik}


def bekle(ms):
    return {"tur": "bekle", "ms": ms}


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------
def yumusat(p: float) -> float:
    p = 0.0 if p < 0 else 1.0 if p > 1 else p
    return p * p * (3 - 2 * p)


def oge_bul(sahne: dict, kimlik: str) -> dict:
    for o in sahne["ogeler"]:
        if o["id"] == kimlik:
            return o
    raise KeyError(f"sahnede '{kimlik}' yok")


def merkez(o: dict) -> tuple:
    return (o["x"] + o["w"] / 2.0, o["y"] + o["h"] / 2.0)


def tik_noktasi(o: dict) -> tuple:
    """Imlecin goruntude durdugu nokta: dugme/oge ortasi; alan icin sol-orta."""
    if o["tur"] in ("alan", "dosya", "secim"):
        return (o["x"] + min(o["w"] * 0.35, 70), o["y"] + o["h"] / 2.0)
    return merkez(o)


# ---------------------------------------------------------------------------
# Derleme
# ---------------------------------------------------------------------------
class Olay:
    __slots__ = ("basla", "bitir", "tur", "veri")

    def __init__(self, basla, bitir, tur, veri):
        self.basla = basla
        self.bitir = bitir
        self.tur = tur
        self.veri = veri

    def __repr__(self):
        return f"Olay({self.tur} {self.basla}-{self.bitir})"


def okuma_suresi(metin: str) -> int:
    return int(max(OKUMA_EN_AZ_MS, min(OKUMA_EN_COK_MS, len(metin) * OKUMA_HARF_MS)))


class Cizelge:
    """Derlenmis animasyon."""

    def __init__(self, sahne: dict, adimlar: list, dil: str = "tr"):
        self.sahne = sahne
        self.dil = dil
        self.olaylar: list[Olay] = []
        self.adim_baslangiclari: list[tuple] = []     # (baslik, ms) -- balonlar
        self.toplam = 0
        self._derle(adimlar)

    # -- derleme ---------------------------------------------------------
    def _derle(self, adimlar):
        s, dil = self.sahne, self.dil
        t = 400                                   # kisa bir acilis duraklamasi
        im = self.baslangic_imleci()
        ilerleme: dict = {}
        for a in adimlar:
            tur = a["tur"]
            if tur == "git":
                o = oge_bul(s, a["hedef"])
                px, py = tik_noktasi(o)
                hedef = (px + a.get("dx", 0), py + a.get("dy", 0))
                uzak = math.hypot(hedef[0] - im[0], hedef[1] - im[1])
                sure = a.get("sure") or int(380 + min(uzak, 700) * 1.0)
                self.olaylar.append(Olay(t, t + sure, "git", {"bas": im, "son": hedef}))
                im = hedef
                t += sure
            elif tur == "tikla":
                o = oge_bul(s, a["hedef"])
                px, py = tik_noktasi(o)
                if math.hypot(px - im[0], py - im[1]) > 6:       # once oraya git
                    uzak = math.hypot(px - im[0], py - im[1])
                    sure = int(380 + min(uzak, 700))
                    self.olaylar.append(Olay(t, t + sure, "git", {"bas": im, "son": (px, py)}))
                    im = (px, py)
                    t += sure
                self.olaylar.append(Olay(t, t + TIK_MS, "tikla",
                                         {"hedef": a["hedef"], "konum": im, "etki": a.get("etki", {})}))
                t += TIK_MS
            elif tur == "yaz":
                o = oge_bul(s, a["hedef"])
                px, py = tik_noktasi(o)
                if math.hypot(px - im[0], py - im[1]) > 6:
                    uzak = math.hypot(px - im[0], py - im[1])
                    sure = int(380 + min(uzak, 700))
                    self.olaylar.append(Olay(t, t + sure, "git", {"bas": im, "son": (px, py)}))
                    im = (px, py)
                    t += sure
                    self.olaylar.append(Olay(t, t + TIK_MS, "tikla",
                                             {"hedef": a["hedef"], "konum": im, "etki": {}}))
                    t += TIK_MS
                metin = metin_al(a["metin"], dil)
                sure = max(1, len(metin)) * YAZ_HARF_MS
                self.olaylar.append(Olay(t, t + sure, "yaz", {"hedef": a["hedef"], "metin": metin}))
                t += sure + 200
            elif tur == "sec":
                o = oge_bul(s, a["hedef"])
                px, py = tik_noktasi(o)
                if math.hypot(px - im[0], py - im[1]) > 6:
                    uzak = math.hypot(px - im[0], py - im[1])
                    sure = int(380 + min(uzak, 700))
                    self.olaylar.append(Olay(t, t + sure, "git", {"bas": im, "son": (px, py)}))
                    im = (px, py)
                    t += sure
                self.olaylar.append(Olay(t, t + SEC_MS, "sec", {"hedef": a["hedef"], "indeks": a["indeks"]}))
                t += SEC_MS
            elif tur == "balon":
                metin = metin_al(a["metin"], dil)
                sure = okuma_suresi(metin)
                baslik = metin_al(a.get("baslik"), dil)
                self.adim_baslangiclari.append((baslik, t))
                self.olaylar.append(Olay(t, t + sure, "balon", {
                    "hedef": a["hedef"], "metin": metin, "baslik": baslik, "yon": a.get("yon", "auto"),
                    "no": len(self.adim_baslangiclari)}))
                t += sure
            elif tur == "balon_kapat":
                self.olaylar.append(Olay(t, t, "balon_kapat", {}))
                t += 250
            elif tur == "cikti":
                n = len(a["satirlar"])
                sure = max(1, n) * a.get("aralik", CIKTI_SATIR_MS)
                self.olaylar.append(Olay(t, t + sure, "cikti", {
                    "hedef": a["hedef"], "satirlar": a["satirlar"], "aralik": a.get("aralik", CIKTI_SATIR_MS)}))
                t += sure + 300
            elif tur == "say":
                self.olaylar.append(Olay(t, t + a["sure"], "say", {
                    "hedef": a["hedef"], "bas": a["bas"], "son": a["son"],
                    "bicim": metin_al(a["bicim"], dil)}))
                t += a["sure"]
            elif tur == "ilerle":
                bas = ilerleme.get(a["hedef"], oge_bul(s, a["hedef"]).get("ilerleme", 0.0))
                self.olaylar.append(Olay(t, t + a["sure"], "ilerle",
                                         {"hedef": a["hedef"], "bas": bas, "son": a["son"]}))
                ilerleme[a["hedef"]] = a["son"]
                t += a["sure"]
            elif tur == "ayarla":
                self.olaylar.append(Olay(t, t, "ayarla", {"degisiklik": a["degisiklik"]}))
            elif tur == "bekle":
                t += int(a["ms"])
            else:
                raise ValueError("bilinmeyen adim turu: " + str(tur))
        self.toplam = t + BITIS_BEKLEME_MS

    def baslangic_imleci(self):
        return tuple(self.sahne.get("imlec_bas") or (self.sahne["genislik"] - 40, self.sahne["yukseklik"] - 26))

    # -- anlik durum -------------------------------------------------------
    def durum(self, t: float) -> dict:
        s = self.sahne
        d = {
            "t": t,
            "imlec": self.baslangic_imleci(),
            "tik": None,
            "sayfa": s.get("sayfa"),
            "bayraklar": dict(s.get("bayraklar", {})),
            "ogeler": {},               # id -> {"deger","aktif","metin","ilerleme","basili","liste","secili"}
            "odak": None,
            "balon": None,
            "cikti": {},                # id -> satir listesi
            "adim_no": 0,
            "bitti": t >= self.toplam - BITIS_BEKLEME_MS,
        }
        og = d["ogeler"]

        def ov(kimlik):
            return og.setdefault(kimlik, {})

        for o in self.olaylar:
            if o.basla > t:
                break
            p = 1.0 if o.bitir <= o.basla else (t - o.basla) / float(o.bitir - o.basla)
            bitti = t >= o.bitir
            v = o.veri
            if o.tur == "git":
                if bitti:
                    d["imlec"] = v["son"]
                else:
                    k = yumusat(p)
                    d["imlec"] = (v["bas"][0] + (v["son"][0] - v["bas"][0]) * k,
                                  v["bas"][1] + (v["son"][1] - v["bas"][1]) * k)
            elif o.tur == "tikla":
                d["imlec"] = v["konum"]
                if p < 1.0:
                    d["tik"] = (v["konum"][0], v["konum"][1], p)
                    ov(v["hedef"])["basili"] = 0.15 < p < 0.6
                else:
                    ov(v["hedef"])["basili"] = False
                if p >= 0.4:                       # tiklama ani
                    self._etki(d, v["hedef"], v["etki"])
            elif o.tur == "yaz":
                n = len(v["metin"]) if bitti else int(p * len(v["metin"]))
                ov(v["hedef"])["deger"] = v["metin"][:n]
                d["odak"] = v["hedef"]
            elif o.tur == "sec":
                self._sec(d, o, v, p, bitti)
            elif o.tur == "balon":
                d["balon"] = {"hedef": v["hedef"], "metin": v["metin"], "baslik": v["baslik"],
                              "yon": v["yon"], "no": v["no"], "alfa": min(1.0, (t - o.basla) / 220.0)}
                d["adim_no"] = v["no"]
            elif o.tur == "balon_kapat":
                d["balon"] = None
            elif o.tur == "cikti":
                k = len(v["satirlar"]) if bitti else min(len(v["satirlar"]), int((t - o.basla) / v["aralik"]) + 1)
                d["cikti"].setdefault(v["hedef"], [])
                d["cikti"][v["hedef"]] = d["cikti"][v["hedef"]] + list(v["satirlar"][:k])
            elif o.tur == "say":
                n = v["son"] if bitti else int(v["bas"] + (v["son"] - v["bas"]) * yumusat(p))
                ov(v["hedef"])["metin"] = v["bicim"].replace("{n}", str(n))
            elif o.tur == "ilerle":
                ov(v["hedef"])["ilerleme"] = v["son"] if bitti else v["bas"] + (v["son"] - v["bas"]) * p
            elif o.tur == "ayarla":
                for kimlik, ch in v["degisiklik"].items():
                    self._ayar_uygula(d, kimlik, ch)
        return d

    # -- yardimcilar ---------------------------------------------------------
    @staticmethod
    def _ayar_uygula(d, kimlik, ch):
        if kimlik == "_sayfa":
            d["sayfa"] = ch
        elif kimlik == "_bayrak":
            d["bayraklar"].update(ch)
        else:
            d["ogeler"].setdefault(kimlik, {}).update(ch)

    def _etki(self, d, hedef, etki):
        if not etki:
            return
        if "sayfa" in etki:
            d["sayfa"] = etki["sayfa"]
        if "bayrak" in etki:
            d["bayraklar"].update(etki["bayrak"])
        for kimlik, ch in (etki.get("ayarla") or {}).items():
            d["ogeler"].setdefault(kimlik, {}).update(ch)
        # kenar menusu: ayni gruptaki ogeler arasinda tek secili
        o = oge_bul(self.sahne, hedef)
        if o["tur"] == "menu" and etki.get("sec", True):
            grup = o.get("grup", "menu")
            for k in self.sahne["ogeler"]:
                if k["tur"] == "menu" and k.get("grup", "menu") == grup:
                    d["ogeler"].setdefault(k["id"], {})["aktif"] = (k["id"] == hedef)
        if o["tur"] == "anahtar" and etki.get("cevir", True):
            mevcut = d["ogeler"].get(hedef, {}).get("aktif", o.get("aktif", False))
            d["ogeler"].setdefault(hedef, {})["aktif"] = not mevcut
        d["odak"] = hedef if o["tur"] in ("alan", "dosya", "secim") else None

    def _sec(self, d, o, v, p, bitti):
        o_sahne = oge_bul(self.sahne, v["hedef"])
        secenekler = o_sahne.get("secenekler") or []
        st = d["ogeler"].setdefault(v["hedef"], {})
        if bitti:
            st["liste"] = False
            st["secili"] = v["indeks"]
            if secenekler:
                st["deger"] = metin_al(secenekler[v["indeks"]], self.dil)
        else:
            st["liste"] = p > 0.18
            st["secili"] = v["indeks"] if p > 0.62 else None
            st["gezen"] = (v["indeks"] if p > 0.5 else max(0, v["indeks"] - 1)) if p > 0.3 else None
        d["odak"] = v["hedef"]


def derle(sahne: dict, adimlar: list, dil: str = "tr") -> Cizelge:
    return Cizelge(sahne, adimlar, dil)


# ---------------------------------------------------------------------------
# Dogrulama (icerik testleri ve gelistirici icin)
# ---------------------------------------------------------------------------
def dogrula(sahne: dict, adimlar: list) -> list:
    """Sorunlarin metin listesini dondurur (bos = temiz)."""
    sorun = []
    kimlikler = [o["id"] for o in sahne["ogeler"]]
    for k in set(kimlikler):
        if kimlikler.count(k) > 1:
            sorun.append(f"yinelenen oge kimligi: {k}")
    sozluk = {o["id"]: o for o in sahne["ogeler"]}
    for o in sahne["ogeler"]:
        for a in ("x", "y", "w", "h"):
            if a not in o:
                sorun.append(f"{o['id']}: '{a}' yok")
        if o.get("x", 0) < 0 or o.get("y", 0) < 0 or o.get("x", 0) + o.get("w", 0) > sahne["genislik"] + 0.5 \
                or o.get("y", 0) + o.get("h", 0) > sahne["yukseklik"] + 0.5:
            sorun.append(f"{o['id']}: sahne disinda")
    for i, a in enumerate(adimlar):
        h = a.get("hedef")
        if h is not None and h not in sozluk:
            sorun.append(f"adim {i + 1} ({a['tur']}): hedef '{h}' sahnede yok")
        if a["tur"] == "tikla":
            for kimlik in (a.get("etki", {}).get("ayarla") or {}):
                if kimlik not in sozluk:
                    sorun.append(f"adim {i + 1}: etki hedefi '{kimlik}' yok")
        if a["tur"] == "sec" and h in sozluk:
            if not sozluk[h].get("secenekler") or a["indeks"] >= len(sozluk[h]["secenekler"]):
                sorun.append(f"adim {i + 1}: '{h}' icin gecersiz secenek")
        if a["tur"] == "cikti" and h in sozluk and sozluk[h]["tur"] != "cikti":
            sorun.append(f"adim {i + 1}: '{h}' bir cikti alani degil")
        if a["tur"] == "ayarla":
            for kimlik in a["degisiklik"]:
                if not kimlik.startswith("_") and kimlik not in sozluk:
                    sorun.append(f"adim {i + 1}: ayarla hedefi '{kimlik}' yok")
        for alan in ("metin", "baslik"):
            m = a.get(alan)
            if isinstance(m, dict) and (not m.get("tr") or not m.get("en")):
                sorun.append(f"adim {i + 1}: '{alan}' iki dilde degil")
    if not any(a["tur"] == "balon" for a in adimlar):
        sorun.append("hic balon (aciklama) yok")
    return sorun
