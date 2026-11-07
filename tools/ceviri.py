#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS ceviri araci: kodda yazili {"tr","en"} metinlerini tarar, dil
dosyalarindaki (config/includes.chroot/opt/carotos/ortak/diller/<kod>.json)
cevirilerin durumunu raporlar, eksikleri parti parti verir, gelenleri dogrulayip ekler.

Kullanim (depo kokunden):
  python3 tools/ceviri.py durum                     # dil dil kapsam yuzdesi
  python3 tools/ceviri.py eksik es --limit 50       # es icin ceviri bekleyen 50 metin (JSON)
  python3 tools/ceviri.py eksik es --uygulama gsd   # yalniz bir uygulamanin metinleri
  python3 tools/ceviri.py ekle es parti.json        # {"<en metin>": "<ceviri>", ...} dosyasini ekler
  python3 tools/ceviri.py kontrol                   # yer tutucu/bos/yetim denetimi (hata varsa cikis 1)

Metnin kimligi INGILIZCE metindir; ayni Ingilizce metin tum uygulamalarda tek
ceviri paylasir. Tarama yalnizca degeri duz metin olan {"tr": "...", "en": "..."}
sozluklerini ve T("...", "...") cagrilarini bulur; calisma aninda uretilen
(f-string, birlestirme) metinler "dinamik" diye sayilir ve ayrica raporlanir.
Bu betik ISO'ya girmez: live-build yalnizca config/ klasorunu kullanir.
"""
import argparse
import ast
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UYG = "config/includes.chroot/opt/carotos"
DIZIN = os.path.join(KOK, UYG, "ortak", "diller")
KODLAR = ("tr", "en", "de", "ru", "es", "pt", "ja", "zh", "fr")
CEVRILEN = tuple(k for k in KODLAR if k not in ("tr", "en"))
ATLA = {os.path.join(UYG, "ortak", "dil.py")}      # dil katmaninin kendi ornekleri sayilmaz


def _yer_tutucular(s):
    return set(re.findall(r"\{(\w*)\}", s or ""))


def _sabit(dugum):
    return isinstance(dugum, ast.Constant) and isinstance(dugum.value, str)


def dosyalari_tara():
    """Uygulama kaynaklari: [(goreli_yol, tam_yol), ...]"""
    sonuc = []
    for yol, _, dosyalar in os.walk(os.path.join(KOK, UYG)):
        if os.sep + "diller" in yol or "__pycache__" in yol:
            continue
        for ad in sorted(dosyalar):
            if ad.endswith(".py") or ad in ("carotpot-yonet",):
                tam = os.path.join(yol, ad)
                rel = os.path.relpath(tam, KOK).replace(os.sep, "/")
                if rel not in {a.replace(os.sep, "/") for a in ATLA}:
                    sonuc.append((rel, tam))
    return sorted(sonuc)


def _dil_once_ciftleri(tr_sozluk, en_sozluk):
    """Iki ast.Dict'te ortak anahtarlarin (tr_metin, en_metin) ciftleri; yalniz duz metin degerler."""
    def duz(d):
        return {k.value: v.value for k, v in zip(d.keys, d.values)
                if isinstance(k, ast.Constant) and isinstance(k.value, str) and _sabit(v)}
    tr_d, en_d = duz(tr_sozluk), duz(en_sozluk)
    return [(tr_d[k], en_d[k]) for k in tr_d if k in en_d and en_d[k].strip()]


def cikar():
    """Kaynak taramasi. Dondurur: (metinler, dinamik)
    metinler: {en_metin: {"tr": {tr_metinler}, "yer": {goreli dosyalar}}}
    dinamik : [(dosya, satir), ...]  tr/en'i duz metin olmayan sozlukler."""
    metinler, dinamik = {}, []
    for rel, tam in dosyalari_tara():
        try:
            with open(tam, "rb") as f:
                agac = ast.parse(f.read().decode("utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for dugum in ast.walk(agac):
            tr = en = None
            if isinstance(dugum, ast.Dict):
                anahtar = {k.value: v for k, v in zip(dugum.keys, dugum.values)
                           if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                if "tr" in anahtar and "en" in anahtar and (set(anahtar) & set(KODLAR)) <= {"tr", "en"}:
                    # tr/en disinda dil kodu da tasiyan sozluk (ör. DIL_ALT_ADI) bir dil tablosudur, ceviri cifti degil
                    if _sabit(anahtar["tr"]) and _sabit(anahtar["en"]):
                        tr, en = anahtar["tr"].value, anahtar["en"].value
                    elif isinstance(anahtar["tr"], ast.Dict) and isinstance(anahtar["en"], ast.Dict):
                        # dil-once tablo (Poligon METIN = {"tr": {k: ..}, "en": {k: ..}}): ayni anahtarlar eslenir
                        for tr_k, en_k in _dil_once_ciftleri(anahtar["tr"], anahtar["en"]):
                            kayit = metinler.setdefault(en_k, {"tr": set(), "yer": set()})
                            kayit["tr"].add(tr_k)
                            kayit["yer"].add(rel)
                    else:
                        dinamik.append((rel, dugum.lineno))
            elif (isinstance(dugum, ast.Call) and isinstance(dugum.func, ast.Name) and dugum.func.id in ("T", "A")
                  and len(dugum.args) == 2 and not dugum.keywords
                  and _sabit(dugum.args[0]) and _sabit(dugum.args[1])):
                tr, en = dugum.args[0].value, dugum.args[1].value
            if en is not None and en.strip():
                kayit = metinler.setdefault(en, {"tr": set(), "yer": set()})
                kayit["tr"].add(tr)
                kayit["yer"].add(rel)
    for rel, tam in json_dosyalari():
        try:
            with open(tam, encoding="utf-8") as f:
                veri = json.load(f)
        except (OSError, ValueError):
            continue
        for tr, en in _json_ciftleri(veri):
            if en.strip():
                kayit = metinler.setdefault(en, {"tr": set(), "yer": set()})
                kayit["tr"].add(tr)
                kayit["yer"].add(rel)
    return metinler, dinamik


def _json_ciftleri(obj):
    """JSON agacindaki duz metin {"tr": .., "en": ..} ciftleri (baska dil kodu tasimayanlar)."""
    if isinstance(obj, dict):
        if (isinstance(obj.get("tr"), str) and isinstance(obj.get("en"), str)
                and (set(obj) & set(KODLAR)) <= {"tr", "en"}):
            yield obj["tr"], obj["en"]
        else:
            for v in obj.values():
                yield from _json_ciftleri(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _json_ciftleri(v)


def json_dosyalari():
    """Poligon gorev paketleri (gorevler/*.json, ctf/*.json): metinleri JSON'dadir."""
    sonuc = []
    for alt in ("gorevler", "ctf"):
        yol = os.path.join(KOK, UYG, "poligon", alt)
        if not os.path.isdir(yol):
            continue
        for ad in sorted(os.listdir(yol)):
            if ad.endswith(".json"):
                tam = os.path.join(yol, ad)
                sonuc.append((os.path.relpath(tam, KOK).replace(os.sep, "/"), tam))
    return sonuc


def dil_dosyasi(kod):
    yol = os.path.join(DIZIN, kod + ".json")
    meta, metinler = {"ad": dict(zip(KODLAR, ("Türkçe", "English", "Deutsch", "Русский", "Español",
                                              "Português", "日本語", "中文", "Français")))[kod],
                      "etkin": False, "durum": "taslak"}, {}
    if os.path.exists(yol):
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
        meta.update(veri.get("_meta", {}))
        metinler = dict(veri.get("metinler", {}))
    return yol, meta, metinler


def yaz(kod, meta, metinler):
    os.makedirs(DIZIN, exist_ok=True)
    yol = os.path.join(DIZIN, kod + ".json")
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"_meta": meta, "metinler": metinler}, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    return yol


def komut_durum(_a):
    metinler, dinamik = cikar()
    toplam = len(metinler)
    print(f"Taranan benzersiz metin: {toplam} | dinamik (cikarilamayan) sozluk: {len(dinamik)}")
    print(f"{'dil':<4} {'ceviri':>7} {'toplam':>7} {'kapsam':>7}  {'yetim':>5}  etkin  durum")
    for kod in CEVRILEN:
        _, meta, dosya = dil_dosyasi(kod)
        var = sum(1 for en in metinler if dosya.get(en, "").strip())
        yetim = sum(1 for en in dosya if en not in metinler)
        yuzde = 100 * var / toplam if toplam else 0
        print(f"{kod:<4} {var:>7} {toplam:>7} {yuzde:>6.1f}%  {yetim:>5}  {'evet' if meta.get('etkin') else 'hayir':<5}  {meta.get('durum')}")
    return 0


def komut_eksik(a):
    if a.dil not in CEVRILEN:
        print(f"Dil cevrilen dillerden biri olmali: {', '.join(CEVRILEN)}", file=sys.stderr)
        return 2
    metinler, _ = cikar()
    _, _, dosya = dil_dosyasi(a.dil)
    liste = []
    for en in sorted(metinler, key=lambda s: (len(s), s)):          # kisadan uzuna
        if dosya.get(en, "").strip():
            continue
        if a.uygulama and not any(y.startswith(f"{UYG}/{a.uygulama}/") for y in metinler[en]["yer"]):
            continue
        liste.append({"en": en, "tr": sorted(metinler[en]["tr"])[0]})
        if a.limit and len(liste) >= a.limit:
            break
    json.dump(liste, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


def dogrula(en, ceviri):
    """Bir cevirinin sorunlarini listeler (bos liste = temiz)."""
    sorun = []
    if not isinstance(ceviri, str) or not ceviri.strip():
        return ["bos ceviri"]
    if _yer_tutucular(en) != _yer_tutucular(ceviri):
        sorun.append(f"yer tutucular farkli: {sorted(_yer_tutucular(en))} != {sorted(_yer_tutucular(ceviri))}")
    if en.count("\n") != ceviri.count("\n"):
        sorun.append("satir sayisi farkli")
    return sorun


def komut_ekle(a):
    if a.dil not in CEVRILEN:
        print(f"Dil cevrilen dillerden biri olmali: {', '.join(CEVRILEN)}", file=sys.stderr)
        return 2
    with open(a.dosya, encoding="utf-8") as f:
        gelen = json.load(f)
    if isinstance(gelen, list):                       # [{"en":..., "ceviri":...}] da kabul
        gelen = {x["en"]: x.get("ceviri", "") for x in gelen}
    metinler, _ = cikar()
    yol, meta, dosya = dil_dosyasi(a.dil)
    eklenen, hata = 0, 0
    for en, ceviri in gelen.items():
        if en not in metinler:
            print(f"ATLANDI  kaynakta yok: {en[:60]!r}")
            hata += 1
            continue
        sorun = dogrula(en, ceviri)
        if sorun:
            print(f"REDDEDILDI {en[:60]!r}: {'; '.join(sorun)}")
            hata += 1
            continue
        dosya[en] = ceviri.strip() if "\n" not in ceviri else ceviri
        eklenen += 1
    yaz(a.dil, meta, dosya)
    print(f"{eklenen} ceviri eklendi, {hata} reddedildi/atlandi -> {os.path.relpath(yol, KOK)}")
    return 1 if hata else 0


def komut_kontrol(_a):
    metinler, _ = cikar()
    hatali = 0
    for kod in CEVRILEN:
        yol, meta, dosya = dil_dosyasi(kod)
        if not os.path.exists(yol):
            continue
        for en, ceviri in dosya.items():
            for s in dogrula(en, ceviri):
                print(f"HATA {kod}: {en[:50]!r}: {s}")
                hatali += 1
        yetim = [en for en in dosya if en not in metinler]
        if yetim:
            print(f"UYARI {kod}: {len(yetim)} yetim ceviri (Ingilizce metin degismis ya da silinmis)")
        if meta.get("etkin") and not dosya:
            print(f"HATA {kod}: etkin ama hic ceviri yok")
            hatali += 1
    print("Temiz." if not hatali else f"{hatali} sorun.")
    return 1 if hatali else 0


def main(argv=None):
    p = argparse.ArgumentParser(description="CarotOS ceviri araci")
    alt = p.add_subparsers(dest="komut", required=True)
    alt.add_parser("durum")
    e = alt.add_parser("eksik")
    e.add_argument("dil")
    e.add_argument("--limit", type=int, default=0)
    e.add_argument("--uygulama")
    a = alt.add_parser("ekle")
    a.add_argument("dil")
    a.add_argument("dosya")
    alt.add_parser("kontrol")
    args = p.parse_args(argv)
    return {"durum": komut_durum, "eksik": komut_eksik, "ekle": komut_ekle,
            "kontrol": komut_kontrol}[args.komut](args)


if __name__ == "__main__":
    sys.exit(main())
