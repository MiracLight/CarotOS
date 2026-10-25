#!/usr/bin/env python3
"""CarotOS surum bilgisini tek kaynaktan (surum.json) ilgili dosyalara esitler.

Kullanim (depo kokunden):
  python3 tools/surum_esitle.py kontrol   # yalnizca raporlar; uyusmazlik varsa cikis kodu 1
  python3 tools/surum_esitle.py uygula    # dosyalari surum.json'a gore gunceller

Cikis kodlari: 0 uyumlu, 1 uyusmazlik (kontrol), 2 yapisal hata (dosya yok ya da
satir tam olarak bir kez bulunamadi). Harici bagimlilik yoktur. Bu betik ISO'ya
girmez: live-build yalnizca config/ klasorunu kullanir.
"""
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UYG = "config/includes.chroot/opt/carotos"
OS_RELEASE = "config/includes.chroot/etc/os-release"

# uygulama anahtari -> surum degiskenini iceren dosya
UYGULAMA_DOSYALARI = {
    "health": f"{UYG}/health/carotos-health.py",
    "usb": f"{UYG}/usb/carotos-usb-check.py",
    "welcome": f"{UYG}/welcome/carotos-welcome.py",
    "magaza": f"{UYG}/magaza/carotos-magaza.py",
}


def kurallar(veri):
    """(dosya, aranan satir deseni, olmasi gereken satir, etiket) listesi."""
    s = veri["dagitim"]["surum"]
    k = veri["dagitim"]["kod_adi"]
    liste = [
        (OS_RELEASE, r'^PRETTY_NAME="[^"\n]*"$', f'PRETTY_NAME="CarotOS {s} ({k})"', "os-release PRETTY_NAME"),
        (OS_RELEASE, r'^VERSION_ID="[^"\n]*"$', f'VERSION_ID="{s}"', "os-release VERSION_ID"),
        (OS_RELEASE, r'^VERSION="[^"\n]*"$', f'VERSION="{s} ({k})"', "os-release VERSION"),
        (UYGULAMA_DOSYALARI["welcome"], r'^APP_CODENAME = "[^"\n]*"$', f'APP_CODENAME = "{k}"', "welcome APP_CODENAME"),
    ]
    for ad, dosya in UYGULAMA_DOSYALARI.items():
        if ad not in veri["uygulamalar"]:
            raise SystemExit(f"surum.json: '{ad}' uygulamasi eksik")
        liste.append((dosya, r'^APP_VERSION = "[^"\n]*"$', f'APP_VERSION = "{veri["uygulamalar"][ad]}"', f"{ad} APP_VERSION"))
    return liste


def calistir(uygula):
    with open(os.path.join(KOK, "surum.json"), encoding="utf-8") as f:
        veri = json.load(f)
    icerik = {}      # dosya -> metin
    degisen = set()
    sorun = 0
    yapisal = 0
    for dosya, desen, olmasi_gereken, etiket in kurallar(veri):
        yol = os.path.join(KOK, dosya)
        if dosya not in icerik:
            try:
                with open(yol, encoding="utf-8", newline="") as f:
                    icerik[dosya] = f.read()
            except OSError as e:
                print(f"HATA   {etiket}: dosya okunamadi ({e})")
                yapisal += 1
                continue
        eslesen = re.findall(desen, icerik[dosya], flags=re.MULTILINE)
        if len(eslesen) != 1:
            print(f"HATA   {etiket}: satir {len(eslesen)} kez bulundu (1 olmali) - {dosya}")
            yapisal += 1
            continue
        if eslesen[0] == olmasi_gereken:
            print(f"TAMAM  {etiket}: {olmasi_gereken}")
            continue
        sorun += 1
        print(f"FARKLI {etiket}: {eslesen[0]}  ->  {olmasi_gereken}")
        if uygula:
            icerik[dosya] = re.sub(desen, lambda m: olmasi_gereken, icerik[dosya], count=1, flags=re.MULTILINE)
            degisen.add(dosya)
    if yapisal:
        print(f"\nYapisal hata var ({yapisal}); hicbir dosya yazilmadi.")
        return 2
    if uygula:
        for dosya in sorted(degisen):
            yol = os.path.join(KOK, dosya)
            gecici = yol + ".tmp"
            with open(gecici, "w", encoding="utf-8", newline="") as f:
                f.write(icerik[dosya])
            os.replace(gecici, yol)
            print(f"YAZILDI {dosya}")
        print(f"\n{len(degisen)} dosya guncellendi." if degisen else "\nDegisiklik gerekmedi.")
        return 0
    if sorun:
        print(f"\n{sorun} uyusmazlik var. Duzeltmek icin: python3 tools/surum_esitle.py uygula")
        return 1
    bilgi = veri.get("surumsuz_uygulamalar", [])
    print("\nTum surum bilgileri uyumlu." + (f" (APP_VERSION tasimayan uygulamalar: {', '.join(bilgi)})" if bilgi else ""))
    return 0


if __name__ == "__main__":
    mod = sys.argv[1] if len(sys.argv) > 1 else "kontrol"
    if mod not in ("kontrol", "uygula"):
        print(__doc__)
        sys.exit(2)
    sys.exit(calistir(mod == "uygula"))
