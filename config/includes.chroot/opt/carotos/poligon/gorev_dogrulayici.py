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
GECERLI_DOGRULAMA_TURLERI = {"kullanici_girdisi", "ufw_engeli", "fail2ban_durumu",
                             "carotpot_kaydi"}


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
        from ag_guvenlik import loopback_adres_mi
        if not loopback_adres_mi(bind):
            hatalar.append(
                f"GÜVENLİK İHLALİ: bind_adres '{bind}' — sadece loopback (127.0.0.0/8) "
                "kabul edilir. Bu görev motora YÜKLENEMEZ."
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

    fu = veri.get("flag_uretimi", {})
    if fu.get("yontem") == "uretec":
        import uretilen_gorevler as _ug
        ad = fu.get("uretec")
        if ad not in _ug.URETECLER:
            hatalar.append(f"bilinmeyen üreteç: '{ad}' (izinli: {sorted(_ug.URETECLER)})")
        elif (ad in _ug.AG_URETECLERI) != (tur == "canli_servis"):
            hatalar.append(f"üreteç '{ad}' için hedef.tur "
                           f"{'canli_servis' if ad in _ug.AG_URETECLERI else 'statik_dosya'} olmalı")
        if dogrulama_turu != "kullanici_girdisi":
            hatalar.append("uretec görevleri dogrulama.tur = 'kullanici_girdisi' kullanır")
        sp = fu.get("sabit_parametreler")
        if sp is not None and not isinstance(sp, dict):
            hatalar.append("flag_uretimi.sabit_parametreler bir sözlük olmalı")

    if dogrulama_turu == "carotpot_kaydi":
        # CarotPot laboratuvari: her zorlukta hangi tuzaklarin acilacagi ve
        # kac giris denemesi gerektigi bellidir; hizmetler ve port araligi
        # tuzak_laboratuvari.py'nin destekledigiyle uyumlu olmalidir.
        from tuzak_laboratuvari import DESTEKLENEN_HIZMETLER
        zl = veri.get("zorluklar")
        if not isinstance(zl, dict) or not zl:
            hatalar.append("carotpot_kaydi için 'zorluklar' zorunlu")
        else:
            for seviye, p in zl.items():
                if not isinstance(p, dict):
                    continue
                hz = p.get("hizmetler")
                if (not isinstance(hz, list) or not hz
                        or set(hz) - set(DESTEKLENEN_HIZMETLER)):
                    hatalar.append(f"zorluklar['{seviye}'].hizmetler geçersiz "
                                   f"(izinli: {sorted(DESTEKLENEN_HIZMETLER)})")
                ar = p.get("tuzak_port_araligi")
                if (not isinstance(ar, list) or len(ar) != 2
                        or not all(isinstance(x, int) for x in ar)
                        or not 1024 <= ar[0] <= ar[1] <= 65535):
                    hatalar.append(f"zorluklar['{seviye}'].tuzak_port_araligi geçersiz")
                g = p.get("gerekli_giris", 1)
                if not isinstance(g, int) or isinstance(g, bool) or not 1 <= g <= 20:
                    hatalar.append(f"zorluklar['{seviye}'].gerekli_giris 1-20 arası olmalı")

    puan = veri.get("puan")
    if isinstance(puan, dict):
        gecersiz_anahtar = set(puan) - {"kolay", "orta", "zor"}
        if not puan or any(not isinstance(v, int) or v <= 0 for v in puan.values()):
            hatalar.append("'puan' sözlüğündeki her değer pozitif tam sayı olmalı")
        if gecersiz_anahtar:
            hatalar.append(f"'puan' sözlüğünde geçersiz zorluk anahtarı: {gecersiz_anahtar}")
    elif not isinstance(puan, int) or puan <= 0:
        hatalar.append("'puan' pozitif bir tam sayı ya da zorluk sözlüğü olmalı")

    zorluklar = veri.get("zorluklar")
    if zorluklar is not None:
        if not isinstance(zorluklar, dict) or not zorluklar:
            hatalar.append("'zorluklar' boş olmayan bir sözlük olmalı")
        else:
            gecersiz = set(zorluklar) - {"kolay", "orta", "zor"}
            if gecersiz:
                hatalar.append(f"'zorluklar' içinde geçersiz anahtar: {gecersiz}")
            for seviye, p in zorluklar.items():
                if not isinstance(p, dict):
                    hatalar.append(f"zorluklar['{seviye}'] bir sözlük olmalı")

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
