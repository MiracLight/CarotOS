#!/bin/sh
# CarotOS GRUB temasi deneme betigi. KURULU test makinesinde, root ile calistirilir (ISO'ya girmez).
#
# Kullanim:
#   sh grub-tema.sh durum            ne kurulu, ne degil (root gerekmez, hicbir sey degistirmez)
#   sh grub-tema.sh kur --kuru       neler yapilacagini yazar, hicbir sey degistirmez
#   sudo sh grub-tema.sh kur         temayi, 5/30 sn sure betigini ve os-prober'i etkinlestirir
#   sudo sh grub-tema.sh geri-al     hepsini kaldirir, GRUB'i eski haline getirir
#
# Guvenlik: shim/grub ikililerine ve /etc/default/grub dosyasina DOKUNMAZ. Ayarlar yalnizca
# /etc/default/grub.d/90-carotos-tema.cfg icinde. grub.cfg once gecici dosyaya uretilir, grub-script-check
# gecerse yerine konur; ilk calistirmada eski grub.cfg grub.cfg.carotos-yedek olarak saklanir.
# Tema bozuksa GRUB duz metin menuye duser.
#
# CAROT_KOK=/baska/dizin ortam degiskeni testler icindir (sahte kok dizin; root aranmaz).
set -eu

BURASI=$(cd "$(dirname "$0")" && pwd)
KOK=${CAROT_KOK:-}
TEMA_KAYNAK="$BURASI/tema"
SURE_KAYNAK="$BURASI/grub.d/99_carotos_sure"
TEMA_HEDEF="$KOK/boot/grub/themes/carotos"
CFG="$KOK/etc/default/grub.d/90-carotos-tema.cfg"
SURE_HEDEF="$KOK/etc/grub.d/99_carotos_sure"
GRUBCFG="$KOK/boot/grub/grub.cfg"
YEDEK="$GRUBCFG.carotos-yedek"
YAZI_DIZINI=${CAROT_YAZI_DIZINI:-/usr/share/fonts/truetype/dejavu}

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
    soyle "Tema klasoru      : $(var "$TEMA_HEDEF/theme.txt")$TEMA_HEDEF"
    soyle "Ayar parcasi      : $(var "$CFG")$CFG"
    soyle "Sure betigi       : $(var "$SURE_HEDEF")$SURE_HEDEF"
    soyle "Yedek grub.cfg    : $(var "$YEDEK")$YEDEK"
    if command -v os-prober >/dev/null 2>&1; then soyle "os-prober        : kurulu"; else soyle "os-prober        : KURULU DEGIL (sudo apt install os-prober)"; fi
    if [ -r "$GRUBCFG" ]; then
        soyle "grub.cfg timeout  : $(grep -E '^ *set timeout=' "$GRUBCFG" | tr '\n' ' ')"
        soyle "grub.cfg tema     : $(grep -c 'theme' "$GRUBCFG" || true) satir 'theme' geciyor"
    else
        soyle "grub.cfg okunamadi (root gerekebilir)."
    fi
}

kur() {
    kok_gerekli
    PAKET_IPUCU=grub-common
    komut_gerekli grub-mkfont grub-mkconfig grub-script-check
    PAKET_IPUCU=os-prober
    komut_gerekli os-prober
    [ -f "$TEMA_KAYNAK/theme.txt" ] || hata "tema bulunamadi: $TEMA_KAYNAK"
    for f in background.png select_c.png select_w.png select_e.png; do
        [ -f "$TEMA_KAYNAK/$f" ] || hata "tema dosyasi eksik: $f (python tools/grub-test/uret.py ile uretin)"
    done
    [ -f "$SURE_KAYNAK" ] || hata "sure betigi bulunamadi: $SURE_KAYNAK"
    [ -f "$YAZI_DIZINI/DejaVuSans.ttf" ] && [ -f "$YAZI_DIZINI/DejaVuSans-Bold.ttf" ] ||
        hata "DejaVu yazi tipi bulunamadi ($YAZI_DIZINI). Kurmak icin: sudo apt install fonts-dejavu-core"

    soyle "1/5 Eski grub.cfg yedegi"
    if [ -f "$GRUBCFG" ] && [ ! -f "$YEDEK" ]; then yap cp -a "$GRUBCFG" "$YEDEK"; else soyle "  (yedek zaten var ya da grub.cfg yok)"; fi

    soyle "2/5 Tema dosyalari"
    yap mkdir -p "$TEMA_HEDEF"
    yap rm -f "$TEMA_HEDEF/logo.png"                  # onceki denemeden kalan logo (artik kullanilmiyor)
    yap cp -f "$TEMA_KAYNAK/theme.txt" "$TEMA_KAYNAK/background.png" \
        "$TEMA_KAYNAK/select_c.png" "$TEMA_KAYNAK/select_w.png" "$TEMA_KAYNAK/select_e.png" "$TEMA_HEDEF/"
    yap grub-mkfont -s 14 -o "$TEMA_HEDEF/dejavu-regular-14.pf2" "$YAZI_DIZINI/DejaVuSans.ttf"
    yap grub-mkfont -s 18 -o "$TEMA_HEDEF/dejavu-regular-18.pf2" "$YAZI_DIZINI/DejaVuSans.ttf"
    yap grub-mkfont -s 18 -o "$TEMA_HEDEF/dejavu-bold-18.pf2" "$YAZI_DIZINI/DejaVuSans-Bold.ttf"

    soyle "3/5 Ayar parcasi ($CFG)"
    yap mkdir -p "$(dirname "$CFG")"
    if [ "$KURU" -eq 0 ]; then
        cat > "$CFG" <<'EOF'
# CarotOS GRUB temasi (deneme). /etc/default/grub'a dokunulmaz; update-grub bu parcayi ondan sonra okur.
GRUB_THEME="/boot/grub/themes/carotos/theme.txt"
GRUB_GFXMODE="1920x1080,1366x768,1280x720,1024x768,800x600,auto"
GRUB_TERMINAL_OUTPUT="gfxterm"
# Sessiz acilis (ISO'daki carotos.cfg ile ayni deger; eski kurulu test makinesinde o dosya yoktur): GRUB'dan sonra
# cekirdegin hata/uyari satirlari (vmwgfx, ata, acpi vb.) ekrana dokulmesin. loglevel=3, quiet'ten SONRA gelmeli.
GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=3 systemd.show_status=auto vt.global_cursor_default=0"
GRUB_TIMEOUT_STYLE="menu"
GRUB_TIMEOUT="5"
# Debian 12'den beri varsayilan kapali: Windows ve baska Linux'lar menude gorunsun.
GRUB_DISABLE_OS_PROBER=false
EOF
        chmod 644 "$CFG"
    else
        soyle "  + (GRUB_THEME, GFXMODE, sessiz acilis parametreleri, TIMEOUT_STYLE, GRUB_DISABLE_OS_PROBER=false yazilir)"
    fi

    soyle "4/5 Sure betigi (yalniz CarotOS varsa 5 sn, baska sistem bulunursa 30 sn)"
    yap mkdir -p "$(dirname "$SURE_HEDEF")"
    yap cp -f "$SURE_KAYNAK" "$SURE_HEDEF"
    yap chmod 755 "$SURE_HEDEF"

    soyle "5/5 grub.cfg uretimi"
    grub_uret
    soyle ""
    soyle "Tamam. Kontrol:  sh $0 durum"
    soyle "Sonra yeniden baslat ve menuyu gor. Sorun olursa: sudo sh $0 geri-al"
}

geri_al() {
    kok_gerekli
    PAKET_IPUCU=grub-common
    komut_gerekli grub-mkconfig grub-script-check
    soyle "1/2 Dosyalar kaldiriliyor"
    yap rm -rf "$TEMA_HEDEF"
    yap rm -f "$CFG" "$SURE_HEDEF"
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
