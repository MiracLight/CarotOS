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
YAMA_ID = "4bdc790d"


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
