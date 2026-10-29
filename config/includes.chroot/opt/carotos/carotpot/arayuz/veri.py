# -*- coding: utf-8 -*-
"""
CarotPot arayuzunun veri katmani. GTK kullanmaz; testler dogrudan cagirir.

Olaylar /var/log/carotpot/olaylar.log'dan okunur (herkes okuyabilir; parolalar
maskelidir). Tam parolalar yalnizca hizmetin veritabanindadir ve "Goster"
dugmesiyle, yonetici onayi alinarak okunur.
"""

import collections
import csv
import html
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

import carotpot as CP
import tuzaklar

BURASI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YARDIMCI = os.path.join(BURASI, "carotpot-yonet")
ENGELLILER = "/var/log/carotpot/engelliler.json"
JAIL = "/etc/fail2ban/jail.d/carotos-carotpot.local"

HIZMET_ADI = CP.HIZMET_ADI


# ---------------------------------------------------------------------------
# Gunluk
# ---------------------------------------------------------------------------

class OlayAkisi:
    """Olay gunlugunu artimli okur. Ilk okumada (ve gunluk dondurulunce)
    eski dosyalar (.3 .2 .1) dahil hepsini, sonra yalnizca yeni satirlari
    okur. tazele() degisiklik olduysa True dondurur."""

    def __init__(self, gunluk=CP.GUNLUK_DOSYASI, sinir=60000):
        self.gunluk = gunluk
        self.sinir = sinir
        self.olaylar = []
        self.konum = None
        self.inode = None
        self.artik = b""
        self.surum = 0

    @staticmethod
    def _coz(metin):
        return [o for o in (CP.olay_satiri_coz(s) for s in metin.splitlines()) if o]

    def tazele(self):
        try:
            st = os.stat(self.gunluk)
        except OSError:
            if self.olaylar or self.konum is not None:
                self.olaylar, self.konum, self.inode = [], None, None
                self.surum += 1
                return True
            return False
        degisti = False
        if self.konum is None or st.st_ino != self.inode or st.st_size < self.konum:
            olaylar = []
            for ek in (".3", ".2", ".1"):
                try:
                    with open(self.gunluk + ek, "rb") as fh:
                        olaylar.extend(self._coz(fh.read().decode("utf-8", "replace")))
                except OSError:
                    continue
            with open(self.gunluk, "rb") as fh:
                ham = fh.read()
            son = ham.rfind(b"\n") + 1
            olaylar.extend(self._coz(ham[:son].decode("utf-8", "replace")))
            self.artik = ham[son:]
            self.olaylar = olaylar
            self.konum, self.inode = len(ham), st.st_ino
            degisti = True
        elif st.st_size > self.konum:
            with open(self.gunluk, "rb") as fh:
                fh.seek(self.konum)
                ham = self.artik + fh.read(4_000_000)
                self.konum = fh.tell()
            son = ham.rfind(b"\n") + 1
            yeni = self._coz(ham[:son].decode("utf-8", "replace"))
            self.artik = ham[son:]
            if yeni:
                self.olaylar.extend(yeni)
                degisti = True
        if len(self.olaylar) > self.sinir:
            del self.olaylar[:len(self.olaylar) - self.sinir]
        if degisti:
            self.surum += 1
        return degisti


def olaylari_oku(gunluk=CP.GUNLUK_DOSYASI, limit=5000):
    """Tek seferlik okuma (eski arayuzle uyumlu)."""
    a = OlayAkisi(gunluk)
    a.tazele()
    return a.olaylar[-limit:]


# ---------------------------------------------------------------------------
# Kaynak profilleri ve risk
# ---------------------------------------------------------------------------

# Mirai ve benzeri IoT botlarinin sozlugundeki tipik kullanici adlari
IOT_KULLANICILARI = {"root", "admin", "support", "guest", "user", "default", "ubnt",
                     "service", "supervisor", "administrator", "888888", "666666",
                     "tech", "mother", "daemon", "telnet"}
WEB_TARAMA_YOLLARI = ("/.env", "/wp-login", "/wp-admin", "/phpmyadmin", "/.git", "/admin",
                      "/cgi-bin", "/boaform", "/hnap1", "/shell", "/actuator", "/vendor/phpunit",
                      "/config", "/backup", "/server-status", "/manager/html", "/login.cgi")


def kaynak_ozeti(olaylar, simdi=None, pencere=86400):
    """Kaynak basina ozet; en etkin once. Her kayit: kaynak, sayi, giris,
    hizmetler (set), ilk, son, kullanicilar/parolalar/turler/hizmet_sayi
    (Counter), yollar, komutlar, zaman [(ts, hizmet)]."""
    simdi = simdi or time.time()
    ozet = {}
    for o in olaylar:
        ts = o.get("ts", 0)
        if pencere and simdi - ts > pencere:
            continue
        k = ozet.get(o["kaynak"])
        if k is None:
            k = ozet[o["kaynak"]] = {
                "kaynak": o["kaynak"], "sayi": 0, "giris": 0, "hizmetler": set(),
                "ilk": ts, "son": ts, "kullanicilar": collections.Counter(),
                "parolalar": collections.Counter(), "turler": collections.Counter(),
                "hizmet_sayi": collections.Counter(), "yollar": collections.Counter(),
                "komutlar": collections.Counter(), "zaman": [], "anahtar": 0,
                "telnet_kullanicilar": set()}
        hz = o.get("hizmet", "?")
        tur = o.get("tur", "?")
        k["sayi"] += 1
        k["hizmetler"].add(hz)
        k["hizmet_sayi"][hz] += 1
        k["turler"][tur] += 1
        k["ilk"] = min(k["ilk"], ts)
        k["son"] = max(k["son"], ts)
        if len(k["zaman"]) < 2000:
            k["zaman"].append((ts, hz))
        if tur == "giris":
            k["giris"] += 1
            if o.get("kullanici"):
                k["kullanicilar"][o["kullanici"]] += 1
                if hz == "telnet":
                    k["telnet_kullanicilar"].add(o["kullanici"])
            if o.get("parola"):
                k["parolalar"][o["parola"]] += 1
            if "anahtar" in str(o.get("ayrinti") or ""):
                k["anahtar"] += 1
        if hz == "http" and tur == "istek":
            yol = str(o.get("ayrinti") or "").split(" UA=")[0].split("?")[0]
            if yol:
                k["yollar"][yol[:80]] += 1
        if tur == "komut":
            k["komutlar"][str(o.get("ayrinti") or "").split(" ")[0].upper()[:20]] += 1
    for k in ozet.values():
        k["davranis"] = davranislar(k)
        k["risk"] = risk_puani(k)
    return sorted(ozet.values(), key=lambda k: (-k["risk"], -k["sayi"], -k["son"]))


def davranislar(k):
    """Kaynagin davranis etiketleri (anahtarlar; metinler arayuzde)."""
    d = []
    if k["giris"] >= 10 or (k["giris"] >= 5 and len(k["kullanicilar"]) >= 3):
        d.append("kaba_kuvvet")
    elif k["giris"] >= 1:
        d.append("giris_denemesi")
    if k["anahtar"]:
        d.append("anahtar_denemesi")
    if len(k["hizmetler"]) >= 3 or k["turler"]["tarama"] >= 3:
        d.append("port_tarama")
    if len(k["telnet_kullanicilar"] & IOT_KULLANICILARI) >= 2:
        d.append("iot_botu")
    if any(y.lower().startswith(WEB_TARAMA_YOLLARI) for y in k["yollar"]):
        d.append("web_tarama")
    if k["komutlar"] and set(k["komutlar"]) & {"CONFIG", "SLAVEOF", "REPLICAOF", "MODULE",
                                                "EVAL", "FLUSHALL", "SET", "SAVE"}:
        d.append("redis_istismar")
    if k["hizmet_sayi"]["mysql"] and k["giris"]:
        d.append("veritabani")
    return d


def risk_puani(k):
    """0-100 arasi risk. Giris denemesi, cesitlilik, saldiri davranislari ve
    yakinlik etkiler."""
    p = min(k["giris"] * 2, 36)
    p += min(k["sayi"] // 3, 14)
    p += min((len(k["hizmetler"]) - 1) * 6, 18)
    agir = {"kaba_kuvvet": 30, "iot_botu": 24, "redis_istismar": 26, "web_tarama": 10,
            "anahtar_denemesi": 6, "port_tarama": 6, "veritabani": 6}
    p += sum(agir.get(d, 0) for d in k.get("davranis", ()))
    if time.time() - k["son"] < 3600:
        p += 6
    return max(1, min(int(p), 100))


def seviye(puan):
    """(anahtar, renk) -- yuksek/orta/dusuk"""
    if puan >= 60:
        return "yuksek", "kirmizi"
    if puan >= 30:
        return "orta", "sari"
    return "dusuk", "vurgu"


# ---------------------------------------------------------------------------
# Seriler
# ---------------------------------------------------------------------------

def saatlik(olaylar, simdi=None, saat=24):
    """Son 'saat' saatin saat basina olay sayilari ve saat etiketleri."""
    simdi = simdi or time.time()
    bas_saat = datetime.fromtimestamp(simdi).replace(minute=0, second=0, microsecond=0)
    baslangic = (bas_saat - timedelta(hours=saat - 1)).timestamp()
    sayilar = [0] * saat
    for o in olaylar:
        ts = o.get("ts", 0)
        if ts >= baslangic:
            i = int((ts - baslangic) // 3600)
            if 0 <= i < saat:
                sayilar[i] += 1
    etiketler = [(bas_saat - timedelta(hours=saat - 1 - i)).strftime("%H") for i in range(saat)]
    return sayilar, etiketler


def gunluk_seri(olaylar, bas, bit):
    """[bas, bit) araligindaki gun basina sayilar ve 'gg.aa' etiketleri."""
    gun0 = datetime.fromtimestamp(bas).replace(hour=0, minute=0, second=0, microsecond=0)
    gunler = max(1, int((bit - gun0.timestamp() + 86399) // 86400))
    sayilar = [0] * gunler
    for o in olaylar:
        ts = o.get("ts", 0)
        if bas <= ts < bit:
            i = (datetime.fromtimestamp(ts).date() - gun0.date()).days
            if 0 <= i < gunler:
                sayilar[i] += 1
    etiketler = [(gun0 + timedelta(days=i)).strftime("%d.%m") for i in range(gunler)]
    return sayilar, etiketler


def hizmet_sayilari(olaylar, simdi=None, pencere=86400):
    simdi = simdi or time.time()
    c = collections.Counter(o.get("hizmet") for o in olaylar
                            if not pencere or simdi - o.get("ts", 0) <= pencere)
    return [(ad, c.get(ad, 0)) for ad in tuzaklar.SIRA]


def aralikta(olaylar, bas, bit):
    return [o for o in olaylar if bas <= o.get("ts", 0) < bit]


# ---------------------------------------------------------------------------
# Durum dosyalari
# ---------------------------------------------------------------------------

def json_oku(yol, varsayilan):
    try:
        with open(yol, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return varsayilan


def engeller(yol=ENGELLILER):
    """[{ip, tarih, bitis?}] -- suresi gecmis olanlar da dahil (henuz
    kaldirilmamis olabilir)."""
    return [e for e in json_oku(yol, []) if isinstance(e, dict) and e.get("ip")]


def engelli_ipler(yol=ENGELLILER):
    return {e.get("ip") for e in engeller(yol)}


def otomatik_acik_mi(yol=JAIL):
    try:
        with open(yol, encoding="utf-8") as fh:
            return any(s.replace(" ", "").lower() == "enabled=true"
                       for s in fh.read().splitlines())
    except OSError:
        return False


def hizmet_acik_mi():
    return CP.hizmet_calisiyor_mu()


def hizmet_durumu(yol=CP.DURUM_DOSYASI):
    """Calisan hizmetin yazdigi durum (acik portlar, hatalar, baslangic)."""
    return json_oku(yol, {})


def ufw_durumu():
    """ufw durumu root olmadan okunabilir (ufw.conf). True/False/None."""
    try:
        with open("/etc/ufw/ufw.conf", encoding="utf-8") as fh:
            for s in fh:
                if s.strip().upper().startswith("ENABLED="):
                    return s.split("=", 1)[1].strip().lower() in ("yes", "true")
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------
# Kullanici notlari (kaynak basina)
# ---------------------------------------------------------------------------

def _not_yolu():
    import kanarya
    return os.path.join(kanarya.ayar_dizini(), "notlar.json")


def notlar():
    v = json_oku(_not_yolu(), {})
    return v if isinstance(v, dict) else {}


def not_yaz(ip, metin):
    v = notlar()
    if metin.strip():
        v[ip] = metin.strip()[:500]
    else:
        v.pop(ip, None)
    yol = _not_yolu()
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol + ".yeni", "w", encoding="utf-8") as fh:
        json.dump(v, fh, ensure_ascii=False, indent=1)
    os.replace(yol + ".yeni", yol)


# ---------------------------------------------------------------------------
# Yetkili yardimci ve bildirici
# ---------------------------------------------------------------------------

def yardimci_cagir(komut, *arglar, girdi=None):
    """carotpot-yonet'i pkexec ile cagirir; (kod, veri) dondurur."""
    cmd = ["pkexec", YARDIMCI, komut] + [str(a) for a in arglar if a is not None]
    try:
        p = subprocess.run(cmd, input=girdi, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired):
        return "__CALISTIRILAMADI__", {}
    if p.returncode in (126, 127) and not p.stdout.strip():
        return "__IPTAL__", {}
    for satir in reversed(p.stdout.strip().splitlines()):
        try:
            veri = json.loads(satir)
            return veri.get("kod", "__BILINMEYEN__"), veri
        except ValueError:
            continue
    return "__BILINMEYEN__", {"cikti": (p.stdout + p.stderr)[-1500:]}


def bildirici_baslat():
    """Oturum bildiricisi (tuzak uyarilari + kanarya izleme) calismiyorsa
    baslatir."""
    try:
        cikti = subprocess.run(["pgrep", "-u", str(os.getuid()), "-f", "carotpot.py bildir"],
                               capture_output=True, timeout=5).stdout
        if cikti.strip():
            return
        subprocess.Popen([sys.executable, "-I", os.path.join(BURASI, "carotpot.py"), "bildir"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.TimeoutExpired):
        pass


# ---------------------------------------------------------------------------
# Raporlar
# ---------------------------------------------------------------------------

def donem_ozeti(olaylar, bas, bit):
    """Rapor icin donem ozeti; ayni uzunluktaki onceki donemle karsilastirir."""
    simdi = min(bit, time.time())
    secili = aralikta(olaylar, bas, bit)
    onceki = aralikta(olaylar, bas - (bit - bas), bas)
    kaynaklar = kaynak_ozeti(secili, simdi, pencere=0)
    onceki_kaynak = {o["kaynak"] for o in onceki}
    kullanicilar = collections.Counter()
    for k in kaynaklar:
        kullanicilar.update(k["kullanicilar"])
    return {
        "bas": bas, "bit": bit, "toplam": len(secili), "onceki_toplam": len(onceki),
        "kaynak": len(kaynaklar), "onceki_kaynak": len(onceki_kaynak),
        "yeni_kaynak": len({k["kaynak"] for k in kaynaklar} - onceki_kaynak),
        "giris": sum(k["giris"] for k in kaynaklar),
        "hizmetler": [(ad, n) for ad, n in hizmet_sayilari(secili, simdi, 0) if n],
        "kaynaklar": kaynaklar,
        "kullanicilar": kullanicilar.most_common(10),
        "seri": (gunluk_seri(secili, bas, bit) if bit - bas > 2 * 86400
                 else saatlik(secili, simdi, max(1, int((bit - bas) // 3600)))),
    }


def degisim(simdi_, once):
    if not once:
        return None if not simdi_ else "+"
    return round((simdi_ - once) * 100 / once)


def rapor_csv(olaylar, bas, bit):
    cikti = io.StringIO()
    y = csv.writer(cikti)
    y.writerow(["zaman", "kaynak", "hizmet", "tur", "hedef_port", "kullanici",
                "parola_maskeli", "ayrinti"])
    for o in aralikta(olaylar, bas, bit):
        y.writerow([datetime.fromtimestamp(o.get("ts", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                    o.get("kaynak", ""), o.get("hizmet", ""), o.get("tur", ""),
                    o.get("hedef_port") or "", o.get("kullanici") or "",
                    o.get("parola") or "", o.get("ayrinti") or ""])
    return cikti.getvalue()


def _svg_cubuk(degerler, etiketler, renk="#8b7fd6", w=760, h=170):
    en = max(degerler + [1])
    bw = (w - 40) / max(len(degerler), 1)
    parca = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
             f'width="100%" role="img">']
    for i in range(5):
        yy = 10 + (h - 40) * i / 4
        parca.append(f'<line x1="34" x2="{w}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#e3e5ec"/>'
                     f'<text x="28" y="{yy + 4:.1f}" font-size="10" fill="#8a90a3" '
                     f'text-anchor="end">{round(en * (4 - i) / 4)}</text>')
    adim = max(1, len(degerler) // 12)
    for i, v in enumerate(degerler):
        bh = (h - 40) * v / en
        x = 38 + i * bw
        parca.append(f'<rect x="{x:.1f}" y="{h - 30 - bh:.1f}" width="{bw * 0.7:.1f}" '
                     f'height="{max(bh, 1):.1f}" rx="2" fill="{renk}"/>')
        if i % adim == 0:
            parca.append(f'<text x="{x + bw * 0.35:.1f}" y="{h - 12}" font-size="10" '
                         f'fill="#8a90a3" text-anchor="middle">{html.escape(etiketler[i])}</text>')
    parca.append("</svg>")
    return "".join(parca)


def rapor_html(oz, t, lang, kaynak_adi=lambda ip: "", one_cikanlar=()):
    """Tek dosyalik, yazdirilabilir HTML rapor. t(anahtar, **kw) metin
    fonksiyonudur."""
    e = html.escape
    bas = datetime.fromtimestamp(oz["bas"]).strftime("%d.%m.%Y %H:%M")
    bit = datetime.fromtimestamp(min(oz["bit"], time.time())).strftime("%d.%m.%Y %H:%M")
    kpi = [(t("r_toplam"), oz["toplam"]), (t("r_kaynak"), oz["kaynak"]),
           (t("r_giris"), oz["giris"]), (t("r_yeni_kaynak"), oz["yeni_kaynak"])]
    satirlar = "".join(
        f"<tr><td class=m>{e(k['kaynak'])}</td><td>{e(kaynak_adi(k['kaynak']))}</td>"
        f"<td>{k['sayi']}</td><td>{k['giris']}</td>"
        f"<td>{e(', '.join(HIZMET_ADI.get(h, h) for h in sorted(k['hizmetler'])))}</td>"
        f"<td>{k['risk']}</td><td>{e(', '.join(t('d_' + d) for d in k['davranis']))}</td></tr>"
        for k in oz["kaynaklar"][:30])
    hizmet = "".join(f"<tr><td>{e(HIZMET_ADI.get(a, a))}</td><td>{n}</td></tr>"
                     for a, n in oz["hizmetler"])
    kul = "".join(f"<tr><td class=m>{e(k)}</td><td>{n}</td></tr>" for k, n in oz["kullanicilar"])
    onemli = "".join(f"<li>{e(m)}</li>" for m in one_cikanlar) or f"<li>{e(t('r_sakin'))}</li>"
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>{e(t('r_baslik'))} · {bas} – {bit}</title>
<style>
body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#1b1e29;background:#f2f3f7;margin:0}}
main{{max-width:900px;margin:32px auto;background:#fff;border:1px solid #d8dbe5;border-radius:14px;padding:32px 36px}}
h1{{margin:0;font-size:24px}} .alt{{color:#5b6177;margin:4px 0 24px}}
.kpi{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}}
.kpi div{{border:1px solid #d8dbe5;border-radius:10px;padding:12px 14px}}
.kpi b{{display:block;font-size:28px}} .kpi span{{color:#5b6177;font-size:13px}}
h2{{font-size:16px;margin:26px 0 8px}} table{{border-collapse:collapse;width:100%;font-size:13px}}
td,th{{text-align:left;padding:6px 8px;border-bottom:1px solid #eceef3}} th{{color:#5b6177;font-weight:600}}
.m{{font-family:ui-monospace,monospace}} li{{margin:4px 0}}
footer{{color:#8a90a3;font-size:12px;margin-top:28px}}
@media print{{body{{background:#fff}} main{{border:none;margin:0}}}}
</style></head><body><main>
<h1>{e(t('r_baslik'))}</h1>
<p class="alt">{bas} – {bit} · CarotOS CarotPot {CP.SURUM}</p>
<div class="kpi">{''.join(f'<div><b>{v}</b><span>{e(a)}</span></div>' for a, v in kpi)}</div>
<h2>{e(t('r_one_cikanlar'))}</h2><ul>{onemli}</ul>
<h2>{e(t('r_etkinlik'))}</h2>{_svg_cubuk(*oz['seri'])}
<h2>{e(t('r_kaynaklar'))}</h2>
<table><tr><th>{e(t('r_adres'))}</th><th>{e(t('r_cihaz'))}</th><th>{e(t('r_olay'))}</th>
<th>{e(t('r_giris'))}</th><th>{e(t('r_tuzaklar'))}</th><th>{e(t('r_risk'))}</th>
<th>{e(t('r_davranis'))}</th></tr>{satirlar}</table>
<h2>{e(t('r_tuzak_basina'))}</h2><table>{hizmet}</table>
<h2>{e(t('r_kullanicilar'))}</h2><table>{kul}</table>
<footer>{e(t('r_dipnot'))}</footer>
</main></body></html>
"""
