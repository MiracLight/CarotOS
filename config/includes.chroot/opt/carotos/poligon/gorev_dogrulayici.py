"""
CarotOS Poligon — görev dosyası doğrulayıcı.

Her .json görev dosyasının zorunlu alanları taşıdığını, bind_adres'in
her koşulda 127.0.0.1 olduğunu ve iç tutarlılığı sağladığını kontrol
eder. Poligon motoru bir görevi yüklemeden önce bunu çalıştırır.
"""

import json
import sys
from pathlib import Path

ZORUNLU_ALANLAR = ["id", "arac", "seviye", "baslik", "senaryo", "hedef",
                    "flag_uretimi", "dogrulama", "puan"]

GECERLI_SEVIYELER = {"baslangic", "orta", "ileri"}
GECERLI_HEDEF_TURLERI = {"canli_servis", "statik_dosya", "sistem_araci"}
GECERLI_DOGRULAMA_TURLERI = {"kullanici_girdisi", "ufw_engeli", "fail2ban_durumu"}


def dogrula(dosya_yolu: Path) -> list[str]:
    """Hata mesajlarının listesini döner. Boşsa dosya geçerlidir."""
    hatalar = []

    try:
        veri = json.loads(dosya_yolu.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"JSON çözümlenemedi: {e}"]

    for alan in ZORUNLU_ALANLAR:
        if alan not in veri:
            hatalar.append(f"zorunlu alan eksik: '{alan}'")

    if hatalar:
        return hatalar  # temel alanlar yoksa devamını kontrol etmenin anlamı yok

    # id: dosya adıyla tutarlı olmalı (görev dosyaları elle karışmasın diye)
    beklenen_on_ek = veri["id"]
    if not dosya_yolu.stem.startswith(beklenen_on_ek) and dosya_yolu.stem != "sablon-ve-ornek":
        hatalar.append(
            f"id ('{beklenen_on_ek}') dosya adıyla ('{dosya_yolu.stem}') uyuşmuyor"
        )

    if veri["seviye"] not in GECERLI_SEVIYELER:
        hatalar.append(f"geçersiz seviye: '{veri['seviye']}' (beklenen: {GECERLI_SEVIYELER})")

    for dil in ("tr", "en"):
        if dil not in veri.get("baslik", {}):
            hatalar.append(f"başlık '{dil}' dilinde eksik")
        if dil not in veri.get("senaryo", {}):
            hatalar.append(f"senaryo '{dil}' dilinde eksik")

    hedef = veri.get("hedef", {})
    tur = hedef.get("tur")
    if tur not in GECERLI_HEDEF_TURLERI:
        hatalar.append(f"geçersiz hedef türü: '{tur}'")

    if tur == "canli_servis":
        # KRİTİK GÜVENLİK KURALI — burada asla ödün verilmez.
        bind = hedef.get("bind_adres")
        if bind != "127.0.0.1":
            hatalar.append(
                f"GÜVENLİK İHLALİ: bind_adres '{bind}' — sadece 127.0.0.1 kabul edilir. "
                "Bu görev motora YÜKLENEMEZ."
            )
        if "port" not in hedef and not hedef.get("coklu_port"):
            hatalar.append(
                "canli_servis için 'port' zorunlu (çok portlu servislerse "
                "'coklu_port: true' ekleyin)"
            )
        if "servis_modulu" not in hedef:
            hatalar.append("canli_servis için 'servis_modulu' zorunlu")

    if tur == "sistem_araci":
        # ufw-01 / fail2ban-01 gibi görevler: yerel sahte bir servis
        # YOKTUR, doğrulama gerçek sistem aracının (ufw/fail2ban) durumunu
        # okuyarak yapılır -- bu araçlar root gerektirdiği için istemci
        # tarafında sudo parolası istenir (bkz. ogrenci_istemci.py).
        if "arac_komutu" not in hedef:
            hatalar.append("sistem_araci için 'arac_komutu' zorunlu (örn. ['fail2ban-client'])")

    dogrulama = veri.get("dogrulama", {})
    dogrulama_turu = dogrulama.get("tur")
    if dogrulama_turu not in GECERLI_DOGRULAMA_TURLERI:
        hatalar.append(f"geçersiz doğrulama türü: '{dogrulama_turu}'")

    if dogrulama_turu == "ufw_engeli" and "port" not in hedef:
        hatalar.append("dogrulama.tur == 'ufw_engeli' için hedef.port zorunlu")

    if dogrulama_turu == "fail2ban_durumu" and not hedef.get("jail"):
        hatalar.append("dogrulama.tur == 'fail2ban_durumu' için hedef.jail zorunlu (örn. 'sshd')")

    if not isinstance(veri.get("puan"), int) or veri["puan"] <= 0:
        hatalar.append("'puan' pozitif bir tam sayı olmalı")

    savunma_id = veri.get("savunma_gorevi_id")
    if savunma_id is not None and not isinstance(savunma_id, str):
        hatalar.append("'savunma_gorevi_id' metin ya da null olmalı")

    return hatalar


def main():
    klasor = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    dosyalar = sorted(klasor.glob("*.json"))

    if not dosyalar:
        print(f"'{klasor}' içinde .json dosyası bulunamadı")
        return 1

    toplam_hata = 0
    for dosya in dosyalar:
        hatalar = dogrula(dosya)
        if hatalar:
            print(f"✗ {dosya.name}")
            for h in hatalar:
                print(f"    - {h}")
            toplam_hata += len(hatalar)
        else:
            print(f"✓ {dosya.name}  (geçerli)")

    print()
    if toplam_hata:
        print(f"TOPLAM {toplam_hata} hata bulundu.")
        return 1
    print("Tüm görev dosyaları geçerli.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
