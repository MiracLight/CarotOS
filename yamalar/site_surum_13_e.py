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
YAMA_ID = "f3e2ada3"


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
