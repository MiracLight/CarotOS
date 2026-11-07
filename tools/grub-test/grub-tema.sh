#!/bin/sh
# CarotOS GRUB ayar denemesi. KURULU test makinesinde, root ile calistirilir (ISO'ya girmez).
#
# Karar (7 Kasim): GRUB gorunumu DEBIAN'IN KENDI TEMASI (desktop-base) olarak kalir; ozel tema yoktur.
# Bu betik yalnizca sunlari yapar:
#   * yalniz CarotOS varsa menu 5 sn, baska isletim sistemi bulunursa 30 sn bekler (99_carotos_sure)
#   * os-prober'i acar (Windows / baska Linux menude gorunsun; Debian 12'den beri varsayilan kapali)
#   * sessiz acilis parametreleri (cekirdek / systemd durum satirlari ekrana dokulmesin)
#   * onceki denemeden kalan ozel temayi ve ayar dosyasini temizler
#
# Kullanim:
#   sh grub-tema.sh durum            ne kurulu, ne degil (root gerekmez, hicbir sey degistirmez)
#   sh grub-tema.sh kur --kuru       neler yapilacagini yazar, hicbir sey degistirmez
#   sudo sh grub-tema.sh kur         ayarlari uygular
#   sudo sh grub-tema.sh geri-al     bu betigin koydugu her seyi kaldirir, GRUB'i eski haline getirir
#
# Guvenlik: shim/grub ikililerine ve /etc/default/grub dosyasina DOKUNMAZ. Ayarlar yalnizca
# /etc/default/grub.d/zz-carotos-grub.cfg icinde ("zz": dosyalar sirayla okunur, bu EN SON okunur, baska bir
# parca ayni degiskeni ezemez). grub.cfg once gecici dosyaya uretilir, grub-script-check gecerse yerine konur;
# ilk calistirmada eski grub.cfg grub.cfg.carotos-yedek olarak saklanir.
#
# CAROT_KOK=/baska/dizin ortam degiskeni testler icindir (sahte kok dizin; root aranmaz).
set -eu

BURASI=$(cd "$(dirname "$0")" && pwd)
KOK=${CAROT_KOK:-}
SURE_KAYNAK="$BURASI/grub.d/99_carotos_sure"
CFG="$KOK/etc/default/grub.d/zz-carotos-grub.cfg"
ESKI_CFG="$KOK/etc/default/grub.d/90-carotos-tema.cfg"          # onceki denemenin ayar parcasi
ESKI_TEMA="$KOK/boot/grub/themes/carotos"                         # onceki denemenin ozel temasi
SURE_HEDEF="$KOK/etc/grub.d/99_carotos_sure"
SYSTEMD_CFG="$KOK/etc/systemd/system.conf.d/zz-carotos-sessiz.conf"
GRUBCFG="$KOK/boot/grub/grub.cfg"
YEDEK="$GRUBCFG.carotos-yedek"

KOMUT=${1:-durum}
KURU=0
[ "${2:-}" = "--kuru" ] && KURU=1

soyle() { printf '%s\n' "$*"; }
hata() { printf 'HATA: %s\n' "$*" >&2; exit 1; }
yap() {
    # Komutu yazar; kuru modda calistirmaz.
    soyle "  + $*"
    if [ "$KURU" -eq 0 ]; then "$@"; fi
}

kok_gerekli() {
    [ "$KURU" -eq 1 ] && return 0
    [ -n "$KOK" ] && return 0
    [ "$(id -u)" -eq 0 ] || hata "root gerekli: sudo sh $0 $KOMUT"
}

komut_gerekli() {
    for k in "$@"; do
        command -v "$k" >/dev/null 2>&1 || hata "'$k' bulunamadi. Kurmak icin: sudo apt install $PAKET_IPUCU"
    done
}

grub_uret() {
    # grub.cfg'yi gecici dosyaya uretir, dogrular, yerine koyar.
    yeni="$GRUBCFG.yeni"
    yap grub-mkconfig -o "$yeni"
    if [ "$KURU" -eq 1 ]; then
        soyle "  + grub-script-check $yeni && mv $yeni $GRUBCFG"
        return 0
    fi
    if ! grub-script-check "$yeni"; then
        rm -f "$yeni"
        hata "uretilen grub.cfg gecersiz; eski grub.cfg yerinde duruyor, degisiklik uygulanmadi."
    fi
    mv "$yeni" "$GRUBCFG"
}

durum() {
    var() { [ -e "$1" ] && echo "VAR " || echo "YOK "; }
    soyle "Ayar parcasi        : $(var "$CFG")$CFG"
    soyle "Sure betigi         : $(var "$SURE_HEDEF")$SURE_HEDEF"
    soyle "systemd sessiz ayari: $(var "$SYSTEMD_CFG")$SYSTEMD_CFG"
    soyle "Yedek grub.cfg      : $(var "$YEDEK")$YEDEK"
    soyle "Eski ozel tema      : $(var "$ESKI_TEMA")$ESKI_TEMA (VAR ise 'kur' kaldirir)"
    soyle "Eski ayar parcasi   : $(var "$ESKI_CFG")$ESKI_CFG (VAR ise 'kur' kaldirir)"
    if command -v os-prober >/dev/null 2>&1; then soyle "os-prober          : kurulu"; else soyle "os-prober          : KURULU DEGIL (sudo apt install os-prober)"; fi
    if [ -r "$GRUBCFG" ]; then
        soyle "grub.cfg timeout    : $(grep -E '^ *set timeout=' "$GRUBCFG" | tr '\n' ' ')"
    else
        soyle "grub.cfg okunamadi (root gerekebilir)."
    fi
}

kur() {
    kok_gerekli
    PAKET_IPUCU=grub-common
    komut_gerekli grub-mkconfig grub-script-check
    PAKET_IPUCU=os-prober
    komut_gerekli os-prober
    [ -f "$SURE_KAYNAK" ] || hata "sure betigi bulunamadi: $SURE_KAYNAK"

    soyle "1/5 Eski grub.cfg yedegi"
    if [ -f "$GRUBCFG" ] && [ ! -f "$YEDEK" ]; then yap cp -a "$GRUBCFG" "$YEDEK"; else soyle "  (yedek zaten var ya da grub.cfg yok)"; fi

    soyle "2/5 Onceki denemeden kalan ozel tema ve ayar temizleniyor (Debian temasina donulur)"
    yap rm -rf "$ESKI_TEMA"
    yap rm -f "$ESKI_CFG"

    soyle "3/5 Ayar parcasi ($CFG)"
    yap mkdir -p "$(dirname "$CFG")"
    if [ "$KURU" -eq 0 ]; then
        cat > "$CFG" <<'EOF'
# CarotOS GRUB ayarlari (deneme). /etc/default/grub'a dokunulmaz. Dosya adi "zz": EN SON okunur.
# Gorunum Debian'in kendi temasidir (desktop-base); burada tema ayari yoktur.
#
# Sessiz acilis (ISO'daki carotos.cfg ile ayni amac; eski kurulu test makinesinde o dosya yoktur).
# loglevel=3, quiet'ten SONRA gelmeli. systemd.show_status=error: basarili adimlar ([ OK ] satirlari)
# gizlenir, hata olursa gorunur. noresume: diskte swap yok (zram kullaniliyor), "Gave up waiting for suspend/resume device"
# satiri ve bekleme kalkar (hazirda bekletme bu kurulumda zaten kullanilamaz).
GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=3 systemd.show_status=error vt.global_cursor_default=0 noresume"
GRUB_TIMEOUT_STYLE="menu"
GRUB_TIMEOUT="5"
# Debian 12'den beri varsayilan kapali: Windows ve baska Linux'lar menude gorunsun.
GRUB_DISABLE_OS_PROBER=false
EOF
        chmod 644 "$CFG"
    else
        soyle "  + (sessiz acilis parametreleri, TIMEOUT_STYLE, GRUB_DISABLE_OS_PROBER=false yazilir)"
    fi

    soyle "3b/5 systemd durum satirlari ($SYSTEMD_CFG)"
    yap mkdir -p "$(dirname "$SYSTEMD_CFG")"
    if [ "$KURU" -eq 0 ]; then
        cat > "$SYSTEMD_CFG" <<'EOF'
# CarotOS: acilista basarili adimlarin ([ OK ] Started ...) ekrana dokulmesini engeller; hata olursa gorunur.
# Cekirdek parametresi systemd.show_status=error ile ayni; baska bir yapilandirma dosyasi onu ezerse bu
# parca ("zz": en son okunur) son sozu soyler.
[Manager]
ShowStatus=error
EOF
        chmod 644 "$SYSTEMD_CFG"
    else
        soyle "  + (ShowStatus=error yazilir)"
    fi

    soyle "4/5 Sure betigi (yalniz CarotOS varsa 5 sn, baska sistem bulunursa 30 sn)"
    yap mkdir -p "$(dirname "$SURE_HEDEF")"
    yap cp -f "$SURE_KAYNAK" "$SURE_HEDEF"
    yap chmod 755 "$SURE_HEDEF"

    soyle "5/5 grub.cfg uretimi"
    grub_uret
    soyle ""
    soyle "Tamam. Kontrol:  sh $0 durum"
    soyle "Sonra yeniden baslat. Sorun olursa: sudo sh $0 geri-al"
}

geri_al() {
    kok_gerekli
    PAKET_IPUCU=grub-common
    komut_gerekli grub-mkconfig grub-script-check
    soyle "1/2 Dosyalar kaldiriliyor"
    yap rm -rf "$ESKI_TEMA"
    yap rm -f "$CFG" "$ESKI_CFG" "$SURE_HEDEF" "$SYSTEMD_CFG"
    soyle "2/2 grub.cfg yeniden uretiliyor"
    grub_uret
    soyle "Geri alindi. Ilk yedek (varsa): $YEDEK"
}

case "$KOMUT" in
    durum) durum ;;
    kur) kur ;;
    geri-al) geri_al ;;
    *) hata "bilinmeyen komut '$KOMUT' (durum | kur [--kuru] | geri-al)" ;;
esac
