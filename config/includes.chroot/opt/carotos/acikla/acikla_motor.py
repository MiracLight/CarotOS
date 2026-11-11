# -*- coding: utf-8 -*-
"""CarotOS Komut Açıklayıcı: bir komut satırını ÇALIŞTIRMADAN ayrıştırıp ne yaptığını açıklar.

Yapay zekâ yok: veri tabanı (veri_*.py) araç başına özet, bayrak açıklamaları, gürültü ve yetki
bilgisi taşır; tehlikeli kalıplar (veri_tehlike.py) kurallarla yakalanır. Hiçbir zaman komutu çalıştırmaz,
yalnızca ayrıştırır. Bilinmeyen komut/bayrakta dürüstçe "tanımıyorum" der.

Sınırlar (bilerek): değişkenler ($X), takma adlar (alias) ve `$(...)` / ters tırnak içindekiler çözülmez;
yalnızca bash söz dizimi; yerel çalışır, hiçbir şey gönderilmez.

GTK'siz, yalnızca standart kütüphane (+ ortak/dil.py).
"""
from __future__ import annotations

import os
import re
import shlex
import sys

_ORTAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ortak")
if os.path.isdir(_ORTAK) and _ORTAK not in sys.path:
    sys.path.insert(0, _ORTAK)
_BURASI = os.path.dirname(os.path.abspath(__file__))
if _BURASI not in sys.path:
    sys.path.insert(0, _BURASI)

import dil  # noqa: E402
import veri_guvenlik  # noqa: E402
import veri_saldiri  # noqa: E402
import veri_temel  # noqa: E402
import veri_tehlike  # noqa: E402

KOMUTLAR = {**veri_saldiri.KOMUTLAR, **veri_guvenlik.KOMUTLAR, **veri_temel.KOMUTLAR}
TAKMA_ADLAR = {**veri_saldiri.TAKMA_ADLAR, **veri_guvenlik.TAKMA_ADLAR, **veri_temel.TAKMA_ADLAR}   # örn. mkfs.ext4 -> mkfs

SEVIYE_SIRASI = {"dusuk": 0, "orta": 1, "yuksek": 2}
KONTROL_ISLEMLERI = {"|", "||", "&&", ";", "&", "|&"}
_ORTAM_ATAMASI = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def T(tr, en):
    return {"tr": tr, "en": en}


ETIKETLER = {
    "baslik": T("Komut açıklaması (komut ÇALIŞTIRILMADI)", "Command explanation (the command was NOT run)"),
    "parca": T("Parça", "Part"),
    "bayraklar": T("Bayraklar", "Flags"),
    "gurultu": T("Gürültü", "Noise"),
    "yetki": T("Yetki", "Privileges"),
    "uyari": T("Uyarı", "Warning"),
    "tehlike": T("Tehlikeli kalıp", "Dangerous pattern"),
    "tanimiyorum": T("Bu komutu tanımıyorum (veri tabanında yok).", "I don't know this command (it is not in the database)."),
    "bilinmeyen_bayrak": T("Tanımadığım bayraklar", "Flags I don't recognise"),
    "baglanti_boru": T("çıktısı bir sonraki komuta aktarılır (|)", "its output is piped into the next command (|)"),
    "baglanti_ve": T("öncekinin başarılı olması durumunda çalışır (&&)", "runs only if the previous one succeeded (&&)"),
    "baglanti_veya": T("öncekinin başarısız olması durumunda çalışır (||)", "runs only if the previous one failed (||)"),
    "baglanti_sonra": T("öncekinden sonra çalışır (;)", "runs after the previous one (;)"),
    "baglanti_arka": T("öncekiyle aynı anda, arka planda çalışır (&)", "runs at the same time in the background (&)"),
    "yonlendirme_yaz": T("çıktıyı şu dosyaya yazar (varsa üzerine yazar)", "writes the output to this file (overwriting it)"),
    "yonlendirme_ekle": T("çıktıyı şu dosyanın sonuna ekler", "appends the output to this file"),
    "yonlendirme_oku": T("girdiyi şu dosyadan okur", "reads its input from this file"),
    "komut_yerine": T("Satırda $(...) ya da ters tırnak var: içindeki komutu çözümlemem, o kısım açıklanmadı.",
                      "The line contains $(...) or backticks: I don't resolve the command inside, so that part isn't explained."),
    "degisken": T("Değişkenler ($ADI) çözülmez: değerleri bilinmediği için olduğu gibi gösterilir.",
                  "Variables ($NAME) are not resolved: they are shown as written because their values are unknown."),
    "bos": T("Açıklanacak bir komut yok.", "There is no command to explain."),
    "tamamlanmamis": T("Satır tamamlanmamış (kapanmayan tırnak).", "The line is incomplete (unclosed quote)."),
    "sudo_ile": T("sudo ile root olarak çalışır", "runs as root via sudo"),
    "root_gerekli": T("root yetkisi gerekir (sudo ile çalıştır)", "needs root privileges (run with sudo)"),
    "root_gerekebilir": T("bazı seçenekler root yetkisi ister", "some options need root privileges"),
    "root_yok": T("normal kullanıcı yeterli", "a normal user is enough"),
    "gsd": T("Sözlükte (GSD) bak", "See the glossary (GSD)"),
    "seviye_dusuk": T("düşük", "low"),
    "seviye_orta": T("orta", "medium"),
    "seviye_yuksek": T("yüksek", "high"),
    "arguman": T("Argümanlar", "Arguments"),
    "nasil": T("Nasıl çalışır", "How it works"),
    "savunma": T("Savunma tarafı", "The defender's side"),
    "etik": T("Yalnızca sana ait ya da yazılı izin aldığın sistemlerde kullan.",
              "Use it only on systems you own or have written permission to test."),
}


def _metin(sozluk, kod):
    return dil.metin(sozluk, kod)


# ---------------------------------------------------------------------------
# Ayrıştırma
# ---------------------------------------------------------------------------

def parcala(satir: str):
    """Satırı kontrol işlemlerine (| && || ; &) göre parçalara böler.
    Dönüş: [(bagla, parca_dict)]; ilk parçanın bağlacı None. Kapanmayan tırnakta ValueError."""
    lex = shlex.shlex(satir, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = "#"
    belirtecler = list(lex)
    parcalar, simdiki, bagla = [], None, None

    def yeni():
        return {"belirtec": [], "yonlendirme": [], "komut_yerine": False}

    simdiki = yeni()
    i = 0
    while i < len(belirtecler):
        b = belirtecler[i]
        if b in KONTROL_ISLEMLERI:
            if simdiki["belirtec"] or simdiki["yonlendirme"]:
                parcalar.append((bagla, simdiki))
            bagla, simdiki = b, yeni()
        elif b and set(b) <= set("<>&|();") and ("<" in b or ">" in b):
            hedef = belirtecler[i + 1] if i + 1 < len(belirtecler) else ""
            simdiki["yonlendirme"].append((b, hedef))
            i += 1
        elif b and set(b) <= set("();"):
            pass
        else:
            if "$(" in b or "`" in b:
                simdiki["komut_yerine"] = True
            simdiki["belirtec"].append(b)
        i += 1
    if simdiki["belirtec"] or simdiki["yonlendirme"]:
        parcalar.append((bagla, simdiki))
    # shlex tırnak içindeki $( ) i tek belirteç yapar; ham satırda da ara
    return parcalar


_SUDO_DEGER_ALAN = {"-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-U", "-r", "-t"}


def onek_ayikla(belirtecler):
    """sudo/env/time/nohup/nice/command/exec/timeout öneklerini ve VAR=deger atamalarını ayıklar.
    Dönüş: (program, argümanlar, sudo_mu, atamalar)."""
    b = list(belirtecler)
    sudo, atamalar = False, []
    while b:
        ilk = b[0]
        if _ORTAM_ATAMASI.match(ilk):
            atamalar.append(b.pop(0))
            continue
        ad = os.path.basename(ilk)
        if ad in ("sudo", "doas"):
            sudo = True
            b.pop(0)
            while b and b[0].startswith("-") and b[0] != "--":
                bayrak = b.pop(0)
                if bayrak in _SUDO_DEGER_ALAN and b:
                    b.pop(0)
            if b and b[0] == "--":
                b.pop(0)
            continue
        if ad == "env":
            b.pop(0)
            while b and (b[0].startswith("-") or _ORTAM_ATAMASI.match(b[0])):
                b.pop(0)
            continue
        if ad in ("time", "nohup", "command", "exec", "stdbuf"):
            b.pop(0)
            continue
        if ad == "nice":
            b.pop(0)
            if b and b[0] == "-n" and len(b) > 1:
                del b[0:2]
            elif b and re.match(r"^-\d+$", b[0]):
                b.pop(0)
            continue
        if ad == "timeout":
            b.pop(0)
            while b and b[0].startswith("-"):
                b.pop(0)
            if b:
                b.pop(0)          # süre
            continue
        break
    if not b:
        return "", [], sudo, atamalar
    return os.path.basename(b[0]), b[1:], sudo, atamalar


def _tanim_bul(program):
    program = TAKMA_ADLAR.get(program, program)
    if program in KOMUTLAR:
        return program, KOMUTLAR[program]
    # mkfs.ext4, python3.11 gibi: nokta öncesi ad
    kok = program.split(".")[0]
    if kok in KOMUTLAR:
        return kok, KOMUTLAR[kok]
    return program, None


def bayraklari_coz(tanim, argumanlar):
    """Dönüş: (bulunan[(ad, girdi, deger)], bilinmeyen[str], konumsal[str])."""
    bayraklar = tanim.get("bayraklar", {})
    desenler = tanim.get("desenler", [])
    kume = tanim.get("kume", False)
    bulunan, bilinmeyen, konumsal = [], [], []
    argumanlar = list(argumanlar)
    # tar xzf dosya.tar.gz gibi tire içermeyen eski biçim
    if tanim.get("eski_kume") and argumanlar and re.fullmatch(r"[A-Za-z]+", argumanlar[0]) \
            and all(("-" + h) in bayraklar for h in argumanlar[0]):
        argumanlar[0] = "-" + argumanlar[0]
    i = 0
    while i < len(argumanlar):
        a = argumanlar[i]
        if a == "--":
            konumsal.extend(argumanlar[i + 1:])
            break
        if a.startswith("-") and len(a) > 1:
            ad, deger = a, None
            if a.startswith("--") and "=" in a:
                ad, deger = a.split("=", 1)
            girdi = bayraklar.get(ad)
            if girdi is None:
                for desen, g in desenler:
                    if re.match(desen, a):
                        girdi, ad = g, a
                        break
            if girdi is None and re.match(r"^-\d+(\.\d+)?$", a):
                konumsal.append(a)      # sayı (ör. -1 gibi bir değer): bayrak değil
                i += 1
                continue
            if girdi is None and kume and not a.startswith("--") and len(a) > 2:
                parcalar = [(("-" + h), bayraklar.get("-" + h)) for h in a[1:]]
                if all(g is not None for _, g in parcalar):
                    for ad2, g in parcalar:
                        bulunan.append((ad2, g, None))
                    # kümenin son harfi değer alıyorsa sıradaki argüman onun değeri
                    son = parcalar[-1][1]
                    if son.get("deger") and i + 1 < len(argumanlar):
                        bulunan[-1] = (bulunan[-1][0], son, argumanlar[i + 1])
                        i += 1
                    i += 1
                    continue
            if girdi is None:
                bilinmeyen.append(a)
                i += 1
                continue
            if girdi.get("deger") and deger is None and i + 1 < len(argumanlar):
                deger = argumanlar[i + 1]
                i += 1
            bulunan.append((ad, girdi, deger))
        else:
            konumsal.append(a)
        i += 1
    return bulunan, bilinmeyen, konumsal


def _en_yuksek(*seviyeler):
    en = "dusuk"
    for s in seviyeler:
        if s and SEVIYE_SIRASI.get(s, 0) > SEVIYE_SIRASI[en]:
            en = s
    return en


def parca_coz(parca):
    program, argumanlar, sudo, atamalar = onek_ayikla(parca["belirtec"])
    ad, tanim = _tanim_bul(program)
    sonuc = {
        "program": program, "komut": ad, "argumanlar": argumanlar, "sudo": sudo, "atamalar": atamalar,
        "bilinen": tanim is not None, "ozet": None, "bayraklar": [], "bilinmeyen": [], "konumsal": [],
        "gurultu": None, "root": None, "uyari": None, "gsd": None, "etik": False,
        "nasil": None, "savunma": None,
        "altkomut": None, "parametreler": [],
        "yonlendirme": parca["yonlendirme"], "komut_yerine": parca["komut_yerine"],
    }
    if tanim is None:
        return sonuc
    bulunan, bilinmeyen, konumsal = bayraklari_coz(tanim, argumanlar)
    sonuc["ozet"] = tanim["ozet"]
    sonuc["bayraklar"] = [{"ad": a, "aciklama": g["a"], "deger": d} for a, g, d in bulunan]
    sonuc["bilinmeyen"], sonuc["konumsal"] = bilinmeyen, konumsal
    alt = tanim.get("altkomut")
    if alt and konumsal and konumsal[0] in alt:
        sonuc["altkomut"] = (konumsal[0], alt[konumsal[0]])
    prm = tanim.get("parametreler")
    if prm:
        kalan = []
        for k in sonuc["konumsal"]:
            ad_, _, deger_ = k.partition("=")
            if _ and ad_ in prm:
                sonuc["parametreler"].append((ad_, deger_, prm[ad_]))
            else:
                kalan.append(k)
        sonuc["konumsal"] = kalan
    sonuc["gurultu"] = _en_yuksek(tanim.get("gurultu"), *[g.get("g") for _, g, _ in bulunan])
    root_bayrak = any(g.get("root") for _, g, _ in bulunan)
    if tanim.get("yetki") == "root" or root_bayrak:
        sonuc["root"] = "gerekli"
    elif tanim.get("yetki") == "kismen":
        sonuc["root"] = "gerekebilir"
    else:
        sonuc["root"] = "yok"
    sonuc["uyari"] = tanim.get("uyari")
    sonuc["gsd"] = tanim.get("gsd")
    sonuc["etik"] = bool(tanim.get("etik"))
    sonuc["nasil"] = tanim.get("nasil")
    sonuc["savunma"] = tanim.get("savunma")
    return sonuc


def tehlikeleri_bul(satir, cozulmus_parcalar):
    """Satır geneli ve parça bazlı kurallar. Dönüş: [{"id","siddet","neden"}] (yinelenmez)."""
    bulunan, goruldu = [], set()

    def ekle(kural):
        if kural["id"] not in goruldu:
            goruldu.add(kural["id"])
            bulunan.append({"id": kural["id"], "siddet": kural["siddet"], "neden": kural["neden"]})

    for kural in veri_tehlike.SATIR_KURALLARI:
        if re.search(kural["desen"], satir):
            ekle(kural)
    for p in cozulmus_parcalar:
        for kural in veri_tehlike.PARCA_KURALLARI:
            try:
                if kural["kosul"](p):
                    ekle(kural)
            except Exception:  # noqa: BLE001  (kural hatası açıklamayı durdurmasın)
                continue
    bulunan.sort(key=lambda k: -SEVIYE_SIRASI.get(k["siddet"], 0))
    return bulunan


def ayristir(satir: str) -> dict:
    """Ana giriş. Dönüş: {"satir", "tamam", "hata", "parcalar":[{"bagla", **parca}], "tehlikeler":[...],
    "komut_yerine": bool, "degisken": bool}"""
    sonuc = {"satir": satir, "tamam": True, "hata": None, "parcalar": [], "tehlikeler": [],
             "komut_yerine": False, "degisken": False}
    if not satir or not satir.strip():
        sonuc["tamam"], sonuc["hata"] = False, "bos"
        return sonuc
    try:
        parcalar = parcala(satir)
    except ValueError:
        sonuc["tamam"], sonuc["hata"] = False, "tamamlanmamis"
        return sonuc
    if not parcalar:
        sonuc["tamam"], sonuc["hata"] = False, "bos"
        return sonuc
    cozulmus = []
    for bagla, p in parcalar:
        c = parca_coz(p)
        c["bagla"] = bagla
        cozulmus.append(c)
    sonuc["parcalar"] = cozulmus
    sonuc["tehlikeler"] = tehlikeleri_bul(satir, cozulmus)
    sonuc["komut_yerine"] = any(p["komut_yerine"] for p in cozulmus) or "$(" in satir or "`" in satir
    sonuc["degisken"] = bool(re.search(r"\$[A-Za-z_{]", satir))
    return sonuc


# ---------------------------------------------------------------------------
# Metin çıktısı (CLI ve kutu)
# ---------------------------------------------------------------------------

def _bagla_etiketi(bagla):
    return {"|": "baglanti_boru", "|&": "baglanti_boru", "&&": "baglanti_ve", "||": "baglanti_veya",
            ";": "baglanti_sonra", "&": "baglanti_arka"}.get(bagla)


def metin_olustur(sonuc: dict, kod: str = "tr") -> str:
    """Okunabilir düz metin. `kod` dil kodu (tr/en/de/…); çeviri yoksa İngilizce."""
    def E(anahtar):
        return _metin(ETIKETLER[anahtar], kod)

    satirlar = [E("baslik"), ""]
    if not sonuc["tamam"]:
        satirlar.append(E(sonuc["hata"] or "bos"))
        return "\n".join(satirlar)
    coklu = len(sonuc["parcalar"]) > 1
    for n, p in enumerate(sonuc["parcalar"], 1):
        if p["bagla"] and _bagla_etiketi(p["bagla"]):
            satirlar.append("  ↳ " + E(_bagla_etiketi(p["bagla"])))
        ad = (("sudo " if p["sudo"] else "") + (p["program"] or "?"))
        satirlar.append((f"[{E('parca')} {n}] " if coklu else "") + ad + (" " + " ".join(p["argumanlar"]) if p["argumanlar"] else ""))
        if not p["bilinen"]:
            satirlar.append("  " + E("tanimiyorum"))
            satirlar.append("")
            continue
        satirlar.append("  " + _metin(p["ozet"], kod))
        if p["altkomut"]:
            satirlar.append(f"  {p['altkomut'][0]}: {_metin(p['altkomut'][1], kod)}")
        for ad_, deger_, aciklama_ in p["parametreler"]:
            satirlar.append(f"  {ad_}={deger_}  —  {_metin(aciklama_, kod)}")
        if p["bayraklar"]:
            satirlar.append("  " + E("bayraklar") + ":")
            for b in p["bayraklar"]:
                deger = f" {b['deger']}" if b["deger"] else ""
                satirlar.append(f"    {b['ad']}{deger}  —  {_metin(b['aciklama'], kod)}")
        if p["konumsal"]:
            satirlar.append("  " + E("arguman") + ": " + " ".join(p["konumsal"]))
        if p["bilinmeyen"]:
            satirlar.append("  " + E("bilinmeyen_bayrak") + ": " + " ".join(p["bilinmeyen"]))
        satirlar.append("  " + E("gurultu") + ": " + E("seviye_" + p["gurultu"]))
        if p["sudo"]:
            yetki = E("sudo_ile")
        else:
            yetki = {"gerekli": E("root_gerekli"), "gerekebilir": E("root_gerekebilir"), "yok": E("root_yok")}[p["root"]]
        satirlar.append("  " + E("yetki") + ": " + yetki)
        for op, hedef in p["yonlendirme"]:
            anahtar = "yonlendirme_oku" if "<" in op else ("yonlendirme_ekle" if ">>" in op else "yonlendirme_yaz")
            satirlar.append(f"  {op} {hedef}: {E(anahtar)}")
        if p["nasil"]:
            satirlar.append("  " + E("nasil") + ": " + _metin(p["nasil"], kod))
        if p["savunma"]:
            satirlar.append("  " + E("savunma") + ": " + _metin(p["savunma"], kod))
        if p["uyari"]:
            satirlar.append("  " + E("uyari") + ": " + _metin(p["uyari"], kod))
        if p["etik"]:
            satirlar.append("  " + E("etik"))
        if p["gsd"]:
            satirlar.append("  " + E("gsd") + ": " + p["gsd"])
        satirlar.append("")
    for t in sonuc["tehlikeler"]:
        satirlar.append(f"⚠ {E('tehlike')} ({E('seviye_' + t['siddet'])}): {_metin(t['neden'], kod)}")
    if sonuc["komut_yerine"]:
        satirlar.append("• " + E("komut_yerine"))
    if sonuc["degisken"]:
        satirlar.append("• " + E("degisken"))
    return "\n".join(satirlar).rstrip() + "\n"


def acikla(satir: str, kod: str | None = None) -> str:
    """Kolay giriş: satır → açıklama metni."""
    return metin_olustur(ayristir(satir), kod or dil.varsayilan_dil())
