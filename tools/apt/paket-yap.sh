#!/bin/bash
# .deb uretir (WSL/Debian'da, kok yetkisiz):  tools/apt/paket-yap.sh <paket> <cikti-dizini>
# Paketler: ortak keyring gsd former health usb security-panel magaza carotene filenor
# Kaynak tek yerde: config/includes.chroot. Dosyalar root:root, hook'taki izinlerle ayni.
# Surum: SURUM ortam degiskeni (varsayilan 1.4.0).
set -euo pipefail
TUMU="ortak keyring gsd former health usb security-panel magaza carotene filenor"
[ $# -eq 2 ] || { echo "Kullanim: $0 <paket> <cikti-dizini>  (paket: $TUMU)" >&2; exit 2; }
PAKET="$1"; CIKTI="$2"
AD="$(cd "$(dirname "$0")" && pwd)"
KAYNAK="$(cd "$AD/../.." && pwd)/config/includes.chroot"
SURUM="${SURUM:-1.4.1}"

# ---- paket tablosu ---------------------------------------------------------------------------------------
# OPT: /opt/carotos/<OPT>   MASAUSTU: usr/share/applications/<ad>.desktop   EK: ek dosyalar (KAYNAK'a gore)
# EXEC: OPT icindeki calistirilabilir dosyalar   BIN: "komut=OPT-icindeki-dosya" (/usr/bin baglari)
# PNG_AD: ikonlar.b64'ten acilacak PNG adi   BAGIMLI/ONERILEN: ek paketler   ACIKLAMA: kisa + uzun aciklama
OPT=""; MASAUSTU=""; EK=""; EXEC=""; BIN=""; PNG_AD=""; BAGIMLI=""; ONERILEN=""; ONERI=""; ACIKLAMA=""
# ONERILEN -> Recommends (apt varsayilan kurar), ONERI -> Suggests (kurmaz). rkhunter Recommends'i exim4/ruby ceker:
# guvenlik dagitiminda istenmez, bu yuzden Suggests (ISO'da hook'lar zaten kurar).
HICOLOR="usr/share/icons/hicolor"
UYG_BAGIMLI="python3, python3-gi, gir1.2-gtk-3.0, python3-gi-cairo, carotos-ortak (>= $SURUM)"
case "$PAKET" in
ortak) ;;
keyring) ;;
gsd)
    OPT=gsd; MASAUSTU=carotos-gsd; EK="$HICOLOR/scalable/apps/carotos-gsd.svg"; EXEC=carotos-gsd.py
    BIN="carotos-gsd=carotos-gsd.py"; PNG_AD=carotos-gsd; BAGIMLI="$UYG_BAGIMLI"
    ACIKLAMA="CarotOS GSD: Genel Sistem Sozlugu
 Linux, ag, siber guvenlik, kriptografi ve algoritma terimleri icin aranabilir, iki dilli sozluk." ;;
former)
    OPT=former; MASAUSTU=carotos-former; EK="$HICOLOR/scalable/apps/carotos-former.svg"; EXEC=carotos-former.py
    BIN="carotos-former=carotos-former.py"; PNG_AD=carotos-former; BAGIMLI="$UYG_BAGIMLI"
    ACIKLAMA="CarotOS Former: guvenlik uygulamalari rehberi
 CarotOS guvenlik araclari icin adim adim, canlandirmali baslangic rehberi." ;;
health)
    OPT=health; MASAUSTU=carotos-health; EXEC=carotos-health.py; BAGIMLI="$UYG_BAGIMLI"; ONERI="rkhunter, debsums"
    EK="$HICOLOR/256x256/apps/carotos-health.png $HICOLOR/scalable/apps/carotos-health.svg"
    ACIKLAMA="CarotOS Sistem Sagligi: guvenlik ve sistem denetimi
 Sistemin guvenlik ayarlarini ve sagligini denetleyen, her bulguyu aciklayan arac." ;;
usb)
    OPT=usb; MASAUSTU=carotos-usb-check; EXEC=carotos-usb-check.py; BAGIMLI="$UYG_BAGIMLI"
    EK="$HICOLOR/256x256/apps/carotos-usb-check.png $HICOLOR/scalable/apps/carotos-usb-check.svg etc/xdg/autostart/carotos-usb-check.desktop"
    ACIKLAMA="CarotOS USB Denetimi: takilan bellekleri denetler
 Takilan USB bellekleri tehlikeli dosyalar ve ayarlar icin tarar, bulgulari aciklar." ;;
security-panel)
    OPT=security-panel; MASAUSTU=carotos-security-panel; EXEC=carotos-security-panel.py; BAGIMLI="$UYG_BAGIMLI"
    ONERILEN="ufw, nmap"
    EK="usr/share/icons/carotos/security-panel-icon.png $HICOLOR/256x256/apps/carotos-security-panel.png"
    ACIKLAMA="CarotOS Guvenlik Paneli: guvenlik duvari, ag ve tarama
 Guvenlik duvari, ag durumu ve Nmap taramalari icin tek pencere." ;;
magaza)
    OPT=magaza; MASAUSTU=carotos-magaza; EXEC=carotos-magaza.py; BAGIMLI="$UYG_BAGIMLI"
    EK="$HICOLOR/256x256/apps/carotos-magaza.png $HICOLOR/scalable/apps/carotos-magaza.svg usr/share/pixmaps/carotos-magaza.png"
    ACIKLAMA="CarotOS Magaza: secilmis uygulama katalogu
 Aciklamali, secilmis uygulamalari kurmak ve guncellemek icin arac." ;;
carotene)
    OPT=carotene; MASAUSTU=carotos-carotene; EXEC=carotene.py; BAGIMLI="$UYG_BAGIMLI, clamav"; ONERILEN="clamav-freshclam"
    EK=""; for b in 16x16 22x22 24x24 32x32 48x48 64x64 128x128 256x256; do EK="$EK $HICOLOR/$b/apps/carotene.png"; done
    ACIKLAMA="Carotene: ClamAV ile virus taramasi
 ClamAV tabanli, sade arayuzlu virus tarayici." ;;
filenor)
    OPT=filenor; MASAUSTU=carotos-filenor; EXEC="filenor_uygulama.py filenor-cli"
    BIN="filenor=filenor_uygulama.py filenor-cli=filenor-cli"; PNG_AD=filenor
    EK="$HICOLOR/scalable/apps/filenor.svg"
    BAGIMLI="$UYG_BAGIMLI, ffmpeg, poppler-utils, qpdf, python3-pil, python3-reportlab, python3-fonttools, python3-brotli, python3-cairosvg"
    ONERILEN="tesseract-ocr, tesseract-ocr-tur, tesseract-ocr-eng, python3-pillow-heif"
    ACIKLAMA="Filenor: dosya donusturucu
 Goruntu, belge, ses ve video dosyalarini cihazdan cikmadan donusturur." ;;
*) echo "Bilinmeyen paket: $PAKET (paket: $TUMU)" >&2; exit 2 ;;
esac

# ---- tekrarlanabilir derleme -----------------------------------------------------------------------------
# Ayni kaynak -> ayni .deb (ayni surumun ozeti depoda degismesin). Zaman damgasi = kaynaklara dokunan son commit.
if [ -z "${SOURCE_DATE_EPOCH:-}" ]; then
    case "$PAKET" in
        ortak) YOL="config/includes.chroot/opt/carotos/ortak" ;;
        keyring) YOL="tools/apt/keyring-paketi" ;;
        *) YOL="config/includes.chroot/opt/carotos/$OPT config/includes.chroot/usr/share/applications/$MASAUSTU.desktop"
           for e in $EK; do YOL="$YOL config/includes.chroot/$e"; done ;;
    esac
    # shellcheck disable=SC2086
    SOURCE_DATE_EPOCH="$(cd "$AD/../.." && git log -1 --format=%ct -- $YOL 2>/dev/null || true)"
    [ -n "$SOURCE_DATE_EPOCH" ] || SOURCE_DATE_EPOCH=1762819200
fi
export SOURCE_DATE_EPOCH

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
S="$T/p"; mkdir -p "$S/DEBIAN" "$S/opt/carotos"

ekle() {   # KAYNAK'a gore dosya ya da dizin kopyala
    [ -e "$KAYNAK/$1" ] || { echo "HATA: kaynak yok: $1" >&2; exit 1; }
    mkdir -p "$S/$(dirname "$1")"; cp -r "$KAYNAK/$1" "$S/$1"
}
temizle() { find "$S" -name '__pycache__' -type d -prune -exec rm -rf {} +; }

# ---- icerik ----------------------------------------------------------------------------------------------
case "$PAKET" in
ortak)
    ekle opt/carotos/ortak; temizle
    BAGIMLI="python3, python3-gi, gir1.2-gtk-3.0, python3-gi-cairo"
    ACIKLAMA="CarotOS ortak katman (tema, dil, etik koruma)
 CarotOS uygulamalarinin paylastigi Python/GTK3 kutuphaneleri ve 7 dillik ceviri dosyalari." ;;
keyring)
    # kendi DEBIAN/control dosyasi var (surum tarih bicimli); aynen kopyalanir
    cp -r "$AD/keyring-paketi/." "$S/"
    SURUM="$(sed -n 's/^Version: //p' "$S/DEBIAN/control")" ;;
*)
    ekle "opt/carotos/$OPT"; temizle
    rm -f "$S/opt/carotos/$OPT/ikonlar.b64"
    ekle "usr/share/applications/$MASAUSTU.desktop"
    for e in $EK; do ekle "$e"; done
    if [ -n "$PNG_AD" ]; then   # PNG simgeler kaynakta "<boyut> <base64>" satirlari olarak durur
        while read -r boyut veri; do
            [ -n "$boyut" ] || continue
            install -d "$S/$HICOLOR/${boyut}x${boyut}/apps"
            printf '%s' "$veri" | base64 -d > "$S/$HICOLOR/${boyut}x${boyut}/apps/$PNG_AD.png"
        done < "$KAYNAK/opt/carotos/$OPT/ikonlar.b64"
    fi
    for b in $BIN; do
        install -d "$S/usr/bin"; ln -s "/opt/carotos/$OPT/${b#*=}" "$S/usr/bin/${b%%=*}"
    done ;;
esac

# ---- postrm ----------------------------------------------------------------------------------------------
# Uygulama root olarak (pkexec) calisinca olusan __pycache__ dpkg'nin bilmedigi dosyalardir; kaldirmada dizin
# bos kalsin diye uygulama dizini silinir. DPKG_ROOT: test ortaminda (dpkg --root) gercek /opt'a dokunmaz.
if [ "$PAKET" != keyring ]; then
    D="${OPT:-ortak}"
    cat > "$S/DEBIAN/postrm" <<EOS
#!/bin/sh
set -e
case "\$1" in
    remove|purge)
        rm -rf "\${DPKG_ROOT:-}/opt/carotos/$D"
        rmdir "\${DPKG_ROOT:-}/opt/carotos" 2>/dev/null || true
        ;;
esac
exit 0
EOS
    chmod 755 "$S/DEBIAN/postrm"
fi

# ---- izinler: dizin 755, dosya 644, betikler 755 ---------------------------------------------------------
find "$S" -mindepth 1 -type d -exec chmod 755 {} +
find "$S" -type f -not -path "$S/DEBIAN/*" -exec chmod 644 {} +
for x in $EXEC; do chmod 755 "$S/opt/carotos/$OPT/$x"; done
[ -d "$S/opt/carotos/ortak" ] && find "$S/opt/carotos/ortak" -name '*.py' -perm -u+x -exec chmod 644 {} + 2>/dev/null || true
find "$S" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +

# ---- md5sums + control -----------------------------------------------------------------------------------
(cd "$S" && find . -path ./DEBIAN -prune -o -type f -printf '%P\0' | sort -z | xargs -0 md5sum) > "$S/DEBIAN/md5sums"
KB=$(du -sk --exclude=DEBIAN "$S" | cut -f1)
AD_PAKET="carotos-$PAKET"
if [ "$PAKET" = keyring ]; then
    AD_PAKET="carotos-archive-keyring"
else
    {
        echo "Package: carotos-$PAKET"; echo "Version: $SURUM"; echo "Section: misc"; echo "Priority: optional"
        echo "Architecture: all"; echo "Maintainer: CarotOS <archive@carotos.org>"; echo "Homepage: https://carotos.org"
        echo "Installed-Size: $KB"; echo "Depends: $BAGIMLI"
        [ -n "$ONERILEN" ] && echo "Recommends: $ONERILEN"
        [ -n "$ONERI" ] && echo "Suggests: $ONERI"
        echo "Description: $ACIKLAMA"
    } > "$S/DEBIAN/control"
fi
chmod 644 "$S/DEBIAN/control" "$S/DEBIAN/md5sums"
mkdir -p "$CIKTI"
dpkg-deb --root-owner-group --build "$S" "$CIKTI/${AD_PAKET}_${SURUM}_all.deb" >/dev/null
echo "$CIKTI/${AD_PAKET}_${SURUM}_all.deb"
