#!/bin/sh
# CarotOS Plymouth acilis temasi deneme betigi. KURULU test makinesinde, root ile calistirilir (ISO'ya girmez).
#
# Tema Debian 13'un 'ceratopsian' temasinin betigini kullanir (parola penceresi ve animasyon orada); yalniz
# resimler ve arka plan rengi CarotOS'un. Debian'in temasina DOKUNULMAZ: ayri bir 'carotos' klasoru kurulur.
#
# Kullanim:
#   sh plymouth-tema.sh durum            hangi tema secili, carotos kurulu mu (root gerekmez, bir sey degistirmez)
#   sh plymouth-tema.sh kur --kuru       neler yapilacagini yazar, hicbir sey degistirmez
#   sudo sh plymouth-tema.sh kur         temayi kurar, secer ve baslangic imajini (initramfs) yeniler (~30 sn)
#   sudo sh plymouth-tema.sh geri-al     onceki temaya doner, carotos klasorunu kaldirir, initramfs'i yeniler
#
# Not: komut satirinda 'splash' olmali (grub-test/grub-tema.sh ekler); yoksa Plymouth ekrani gorunmez.
# CAROT_KOK=/baska/dizin ortam degiskeni testler icindir (sahte kok dizin; root aranmaz).
set -eu

BURASI=$(cd "$(dirname "$0")" && pwd)
KOK=${CAROT_KOK:-}
KAYNAK="$BURASI/tema/carotos"
TEMALAR="$KOK/usr/share/plymouth/themes"
HEDEF="$TEMALAR/carotos"
ONCEKI="$HEDEF/.onceki-tema"
GEREKLI="carotos.plymouth carotos.script frill.png glow.png logo.png password_dot.png password_field.png password_dot16.png password_field16.png"

KOMUT=${1:-durum}
KURU=0
[ "${2:-}" = "--kuru" ] && KURU=1

soyle() { printf '%s\n' "$*"; }
hata() { printf 'HATA: %s\n' "$*" >&2; exit 1; }
yap() {
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
        command -v "$k" >/dev/null 2>&1 || hata "'$k' bulunamadi. Kurmak icin: sudo apt install plymouth initramfs-tools"
    done
}

durum() {
    var() { [ -e "$1" ] && echo "VAR " || echo "YOK "; }
    soyle "carotos klasoru     : $(var "$HEDEF/carotos.plymouth")$HEDEF"
    if command -v plymouth-set-default-theme >/dev/null 2>&1; then
        soyle "secili tema         : $(plymouth-set-default-theme 2>/dev/null || echo bilinmiyor)"
    else
        soyle "plymouth-set-default-theme bulunamadi (sudo apt install plymouth)"
    fi
    soyle "onceki tema notu    : $(var "$ONCEKI")$ONCEKI"
}

kur() {
    kok_gerekli
    komut_gerekli plymouth-set-default-theme update-initramfs
    for f in $GEREKLI; do
        [ -f "$KAYNAK/$f" ] || hata "tema dosyasi eksik: $f ($KAYNAK)"
    done

    soyle "1/4 Onceki temayi kaydet"
    onceki=$(plymouth-set-default-theme 2>/dev/null || true)
    [ "$onceki" = "carotos" ] && onceki=""
    soyle "  onceki tema: ${onceki:-(yok)}"

    soyle "2/4 Tema dosyalari ($HEDEF)"
    yap mkdir -p "$HEDEF"
    for f in $GEREKLI; do yap cp -f "$KAYNAK/$f" "$HEDEF/$f"; done
    if [ "$KURU" -eq 0 ] && [ -n "$onceki" ]; then printf '%s\n' "$onceki" > "$ONCEKI"; fi

    soyle "3/4 Temayi sec"
    yap plymouth-set-default-theme carotos

    soyle "4/4 Baslangic imajini (initramfs) yenile -- biraz surer"
    yap update-initramfs -u
    soyle ""
    soyle "Tamam. Kontrol:  sh $0 durum"
    soyle "Yeniden baslat. Sorun olursa: sudo sh $0 geri-al"
}

geri_al() {
    kok_gerekli
    komut_gerekli plymouth-set-default-theme update-initramfs
    onceki=""
    [ -f "$ONCEKI" ] && onceki=$(head -n 1 "$ONCEKI")
    [ -n "$onceki" ] || onceki=ceratopsian
    soyle "1/3 Onceki tema seciliyor: $onceki"
    yap plymouth-set-default-theme "$onceki"
    soyle "2/3 carotos klasoru kaldiriliyor"
    yap rm -rf "$HEDEF"
    soyle "3/3 Baslangic imaji yenileniyor"
    yap update-initramfs -u
    soyle "Geri alindi."
}

case "$KOMUT" in
    durum) durum ;;
    kur) kur ;;
    geri-al) geri_al ;;
    *) hata "bilinmeyen komut '$KOMUT' (durum | kur [--kuru] | geri-al)" ;;
esac
