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
YAMA_ID = "e9bf6427"


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
