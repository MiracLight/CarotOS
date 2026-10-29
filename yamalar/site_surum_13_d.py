#!/usr/bin/env python3
# CarotOS yamasi -- carotos-yama skill'i tarafindan OTOMATIK uretildi.
# Elle duzenleme; yeni yama uret.
#
# Davranis (hepsi-ya-da-hicbiri):
#   1. Tum hedef dosyalari bul, okunabilir/yazilabilir oldugunu dogrula
#   2. Tum degisiklikleri BELLEKTE uygula, her birinin TAM OLARAK BIR
#      yerde eslestigini dogrula (0 ya da 2+ ise dur)
#   3. Sonucu sozdizimi kontrolunden gecir (.py / .json / .css / shell)
#   4. Ancak hepsi gectiyse: yedek al, dosyalari atomik olarak yaz,
#      izinleri koru, yazilani tekrar okuyup dogrula
#   Herhangi bir adim basarisiz olursa DISKTE HICBIR SEY DEGISMEZ.
#   Ayni yama ikinci kez calistirilirsa "zaten uygulanmis" der, dokunmaz.

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zlib

YUK = "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"
YAMA_ID = "5b60c793"


def yaz(m=""):
    print(m, flush=True)


def dur(m, kod=1):
    yaz("")
    yaz("[YAMA DURDU] " + m)
    yaz("Diskte hicbir sey degismedi.")
    sys.exit(kod)


def satir_goster(s):
    """Bosluklari gorunur kilar: sondaki bosluk '·', tab '→', CR '\\r'."""
    s = s.replace("\r", "\\r").replace("\t", "→")
    govde = s.rstrip(" ")
    return govde + "·" * (len(s) - len(govde)) + "$"


def teshis(icerik, eski, dosya):
    """Eslesme bulunamadiginda NEDENINI bulmaya calisir."""
    yaz("  Teshis:")
    norm = lambda t: re.sub(r"\s+", " ", t).strip()
    if norm(eski) and norm(eski) in norm(icerik):
        yaz("  -> Metin dosyada VAR ama bosluk/bos satir/girinti farkli.")
    else:
        yaz("  -> Metin dosyada hic yok (yanlis dosya, dosya degismis, ya da")
        yaz("     yama daha once kismen uygulanmis olabilir).")

    eski_satirlar = eski.split("\n")
    ilk = next((l for l in eski_satirlar if l.strip()), None)
    if ilk is None:
        return
    dosya_satirlar = icerik.split("\n")
    adaylar = [i for i, l in enumerate(dosya_satirlar) if l.strip() == ilk.strip()]
    if not adaylar:
        yaz("  -> Yamanin ilk dolu satiri bile dosyada bulunamadi:")
        yaz("     " + satir_goster(ilk))
        return
    ofset = eski_satirlar.index(ilk)
    for aday in adaylar[:3]:
        bas = aday - ofset
        yaz("  -> Olasi konum: %s satir %d" % (dosya, bas + 1))
        for k, beklenen in enumerate(eski_satirlar):
            gercek_i = bas + k
            gercek = dosya_satirlar[gercek_i] if 0 <= gercek_i < len(dosya_satirlar) else None
            if gercek == beklenen:
                continue
            yaz("     Ilk fark satir %d:" % (gercek_i + 1))
            yaz("       yamanin bekledigi: " + satir_goster(beklenen))
            yaz("       dosyada olan     : " + (satir_goster(gercek) if gercek is not None else "<dosya sonu>"))
            if gercek is not None:
                if gercek.strip() == "" and beklenen.strip() != "":
                    yaz("       (dosyada FAZLADAN bos satir var)")
                elif beklenen.strip() == "" and gercek.strip() != "":
                    yaz("       (yamada fazladan bos satir var)")
                elif gercek.strip() == beklenen.strip():
                    yaz("       (girinti ya da satir sonu boslugu farkli)")
            break
    yaz("  Cozum: ilgili araligi 'sed -n ... | base64 -w0' ile tekrar al,")
    yaz("         yamayi yeniden uret. Elle tahmin ederek duzeltme.")


def css_kontrol(metin):
    """(ic_ice_kural_sayisi, denge_bozuk) dondurur."""
    t = re.sub(r"/\*.*?\*/", "", metin, flags=re.S)
    t = re.sub(r'"(?:\\.|[^"\\])*"' + r"|'(?:\\.|[^'\\])*'", '""', t)
    yigin, ic_ice, bozuk = [], 0, False
    for i, ch in enumerate(t):
        if ch == "{":
            j = max(t.rfind(";", 0, i), t.rfind("{", 0, i), t.rfind("}", 0, i))
            secici = t[j + 1:i].strip()
            if yigin and not yigin[-1].startswith("@"):
                ic_ice += 1
            yigin.append(secici)
        elif ch == "}":
            if not yigin:
                bozuk = True
            else:
                yigin.pop()
    if yigin:
        bozuk = True
    return ic_ice, bozuk


def sozdizimi_kontrol(yol, eski_metin, yeni_metin, zorunlu=False):
    """Hata metni ya da None dondurur. CAROTOS_YAMA_SOZDIZIMI_ATLA yalnizca
    uretecin kendi testinde, dosyanin bir PARCASI uzerinde calisirken
    kullanilir; yeni olusturulan (tam) dosyalarda hic atlanmaz."""
    if not zorunlu and os.environ.get("CAROTOS_YAMA_SOZDIZIMI_ATLA") == "1":
        return None
    ad = os.path.basename(yol)
    if ad.endswith(".py"):
        try:
            compile(yeni_metin, yol, "exec")
        except SyntaxError as e:
            return "Python sozdizimi hatasi: %s (satir %s)" % (e.msg, e.lineno)
    elif ad.endswith(".json"):
        try:
            json.loads(yeni_metin)
        except ValueError as e:
            return "JSON hatasi: %s" % e
    elif ad.endswith(".xml"):
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(yeni_metin.encode("utf-8"))
        except ET.ParseError as e:
            return "XML bozuldu: %s (bozuk XML ile xfce4-panel acilmaz)" % e
    elif ad.endswith(".css"):
        e_ic, e_bozuk = css_kontrol(eski_metin)
        y_ic, y_bozuk = css_kontrol(yeni_metin)
        if y_bozuk and not e_bozuk:
            return "CSS suslu parantez dengesi bozuldu ({ ve } sayisi tutmuyor)"
        if y_ic > e_ic:
            return ("CSS'te YENI ic ice kural olustu (%d -> %d). Buyuk ihtimalle "
                    "bir kuralin kapanis '}' parantezi eksik ve yeni kurallar "
                    "onun icine gomuldu." % (e_ic, y_ic))
    elif yeni_metin.startswith("#!/bin/sh") or yeni_metin.startswith("#!/bin/bash"):
        kabuk = "bash" if yeni_metin.startswith("#!/bin/bash") else "sh"
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8") as f:
            f.write(yeni_metin)
            gecici = f.name
        try:
            r = subprocess.run([kabuk, "-n", gecici], capture_output=True, text=True)
            if r.returncode != 0:
                return "Kabuk betigi sozdizimi hatasi: %s" % r.stderr.strip()
        finally:
            os.unlink(gecici)
    return None


def atomik_yaz(yol, metin):
    dizin = os.path.dirname(os.path.abspath(yol)) or "."
    gecici = os.path.join(dizin, "." + os.path.basename(yol) + ".yama-tmp")
    try:
        with open(gecici, "w", encoding="utf-8", newline="") as f:
            f.write(metin)
        if os.path.exists(yol):
            shutil.copymode(yol, gecici)
        os.replace(gecici, yol)
    finally:
        if os.path.exists(gecici):
            os.unlink(gecici)


def main():
    try:
        yuk = json.loads(zlib.decompress(base64.b64decode(YUK)).decode("utf-8"))
    except Exception:
        dur("Yama icerigi bozuk (komut kopyalanirken kesilmis olabilir). "
            "Komutu bastan sona tekrar kopyala.")
    yaz("CarotOS yamasi %s -- %s" % (YAMA_ID, yuk.get("aciklama", "")))
    yaz("Calisma dizini: %s" % os.getcwd())

    root_izin = yuk.get("root_gerekli") or os.environ.get("CAROTOS_YAMA_ROOT_IZIN") == "1"
    if os.geteuid() == 0 and not root_izin:
        dur("Bu yama sudo/root ile calistirilmamali (dosya sahipligi root'a "
            "gecer). 'sudo' olmadan tekrar calistir.")

    planlar = []  # (yol, eski_icerik, yeni_icerik, uygulanan, atlanan, yeni_mi, mod)

    # ---------- 1-2. Dogrula ve bellekte uygula ----------
    for hedef in yuk["dosyalar"]:
        yol = hedef["yol"]

        if hedef.get("tur") == "olustur":
            if os.path.exists(yol):
                with open(yol, encoding="utf-8", newline="") as f:
                    mevcut = f.read()
                if mevcut == hedef["icerik"]:
                    yaz("  %s: zaten ayni icerikle mevcut, atlandi." % yol)
                    continue
                if not hedef.get("uzerine_yaz"):
                    dur("%s zaten var ve icerigi farkli. Uzerine yazilmasi "
                        "istenmemis (uzerine_yaz=false)." % yol)
            ust = os.path.dirname(os.path.abspath(yol))
            if not os.path.isdir(ust):
                dur("%s icin klasor yok: %s" % (yol, ust))
            if not os.access(ust, os.W_OK):
                dur("Klasore yazma izni yok: %s" % ust)
            hata = sozdizimi_kontrol(yol, "", hedef["icerik"], zorunlu=True)
            if hata:
                dur("%s: %s" % (yol, hata))
            planlar.append((yol, None, hedef["icerik"], 1, 0, True, hedef.get("mod")))
            continue

        if not os.path.isfile(yol):
            dur("Dosya bulunamadi: %s\n  (Su an '%s' dizinindesin. Yama dogru "
                "dizinden mi calistiriliyor?)" % (yol, os.getcwd()))
        if not os.access(yol, os.R_OK) or not os.access(yol, os.W_OK):
            dur("Okuma/yazma izni yok: %s (ls -la ile kontrol et)" % yol)
        if not os.access(os.path.dirname(os.path.abspath(yol)), os.W_OK):
            dur("Dosyanin klasorune yazma izni yok: %s" % yol)
        if os.stat(yol).st_uid != os.geteuid() and not root_izin:
            dur("%s baska bir kullaniciya ait (uid %d). Yazarsak sahiplik "
                "degisir. Once 'ls -la' ile kontrol et." % (yol, os.stat(yol).st_uid))

        try:
            with open(yol, encoding="utf-8", newline="") as f:
                orijinal = f.read()
        except UnicodeDecodeError:
            dur("%s UTF-8 degil, yama uygulanamaz." % yol)

        crlf = "\r\n" in orijinal
        metin = orijinal
        uygulanan = atlanan = 0
        for n, d in enumerate(hedef["degisiklikler"], 1):
            eski, yeni = d["eski"], d["yeni"]
            if crlf:
                eski = eski.replace("\r\n", "\n").replace("\n", "\r\n")
                yeni = yeni.replace("\r\n", "\n").replace("\n", "\r\n")
            etiket = "%s / degisiklik %d%s" % (yol, n, (" (" + d["not"] + ")") if d.get("not") else "")

            if yeni and yeni in metin:
                if eski in metin and eski not in yeni:
                    dur("%s: hem eski hem yeni metin dosyada var -- belirsiz durum, "
                        "elle kontrol gerekli." % etiket)
                yaz("  %s: zaten uygulanmis, atlandi." % etiket)
                atlanan += 1
                continue

            adet = metin.count(eski)
            if adet == 1:
                metin = metin.replace(eski, yeni, 1)
                uygulanan += 1
            elif adet == 0:
                yaz("")
                yaz("[ESLESME YOK] " + etiket)
                teshis(metin, eski, yol)
                dur("Eslesme bulunamadi.")
            else:
                dur("%s: eslesecek metin dosyada %d kez geciyor -- hangisi oldugu "
                    "belirsiz. Daha fazla baglam (cevre satir) ile yeniden uret." % (etiket, adet))

        if uygulanan:
            hata = sozdizimi_kontrol(yol, orijinal, metin)
            if hata:
                dur("%s: degisiklik sonrasi %s" % (yol, hata))
        planlar.append((yol, orijinal, metin, uygulanan, atlanan, False, None))

    yazilacak = [p for p in planlar if p[3] > 0]
    if not yazilacak:
        yaz("")
        yaz("[TAMAM] Butun degisiklikler zaten uygulanmis. Hicbir sey yazilmadi.")
        return

    # ---------- 4. Yedek + yaz ----------
    # Yedekler kullaniciya ozel ve kalici: ~/.cache/carotos-yama/yedek/.
    # (/tmp ortak ve yeniden baslatmada silinir; bir kez sudo ile
    # calisirsa root'a ait kalip sonraki calismalari kilitleyebilir.)
    yedek_kok = os.path.join(os.path.expanduser("~"), ".cache", "carotos-yama", "yedek",
                             "%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), YAMA_ID))
    try:
        for yol, orijinal, _, _, _, yeni_mi, _ in yazilacak:
            if orijinal is None:
                continue
            hedef_yedek = os.path.join(yedek_kok, os.path.abspath(yol).lstrip("/"))
            os.makedirs(os.path.dirname(hedef_yedek), exist_ok=True)
            with open(hedef_yedek, "w", encoding="utf-8", newline="") as f:
                f.write(orijinal)
    except OSError as e:
        dur("Yedek alinamadi (%s). Yedeksiz yazmayacagim." % e)

    yazilanlar = []
    try:
        for yol, orijinal, metin, _, _, yeni_mi, mod in yazilacak:
            atomik_yaz(yol, metin)
            if yeni_mi:
                os.chmod(yol, int(mod or "644", 8))
            yazilanlar.append((yol, orijinal))
            with open(yol, encoding="utf-8", newline="") as f:
                if f.read() != metin:
                    raise IOError("yazilan icerik dogrulanamadi: %s" % yol)
    except Exception as e:
        yaz("")
        yaz("[HATA] Yazma sirasinda: %s -- geri aliniyor..." % e)
        for yol, orijinal in yazilanlar:
            if orijinal is None:
                os.unlink(yol)
            else:
                atomik_yaz(yol, orijinal)
        dur("Yazma hatasi, tum dosyalar eski haline dondu.")

    yaz("")
    for yol, _, _, uyg, atl, yeni_mi, _ in planlar:
        if yeni_mi:
            yaz("  [OLUSTURULDU] %s" % yol)
        else:
            yaz("  [GUNCELLENDI] %s -- %d degisiklik uygulandi%s" % (
                yol, uyg, (", %d zaten vardi" % atl) if atl else ""))
    if os.path.isdir(yedek_kok):
        yaz("  Yedek: %s" % yedek_kok)
    yaz("")
    yaz("[TAMAM] Yama basariyla uygulandi.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # Yazma asamasindaki hatalar main() icinde yakalanip geri alinir;
        # buraya dusen her sey yazma ONCESINDE olmustur.
        yaz("")
        yaz("[YAMA DURDU] Beklenmeyen hata: %s: %s" % (type(e).__name__, e))
        yaz("Diskte hicbir sey degismedi. Bu ciktiyi Claude'a gonder.")
        sys.exit(1)
