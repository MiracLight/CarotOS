#!/bin/bash
# .deb uretir (WSL/Debian'da, kok yetkisiz):  tools/apt/paket-yap.sh <ortak|gsd|former|keyring> <cikti-dizini>
# Kaynak tek yerde: config/includes.chroot. Dosyalar root:root, hook'taki izinlerle ayni.
# Surum: SURUM ortam degiskeni (varsayilan 1.4.0).
set -euo pipefail
[ $# -eq 2 ] || { echo "Kullanim: $0 <ortak|gsd|former> <cikti-dizini>" >&2; exit 2; }
PAKET="$1"; CIKTI="$2"
AD="$(cd "$(dirname "$0")" && pwd)"
KAYNAK="$(cd "$AD/../.." && pwd)/config/includes.chroot"
SURUM="${SURUM:-1.4.0}"
# Tekrarlanabilir derleme: ayni kaynak -> ayni .deb (ayni surumun ozeti depoda degismesin).
# Zaman damgasi = paketin kaynaklarina dokunan son commit.
if [ -z "${SOURCE_DATE_EPOCH:-}" ]; then
    case "$PAKET" in
        ortak) YOL="config/includes.chroot/opt/carotos/ortak" ;;
        keyring) YOL="tools/apt/keyring-paketi" ;;
        *) YOL="config/includes.chroot/opt/carotos/$PAKET config/includes.chroot/usr/share/applications/carotos-$PAKET.desktop config/includes.chroot/usr/share/icons/hicolor/scalable/apps/carotos-$PAKET.svg" ;;
    esac
    # shellcheck disable=SC2086
    SOURCE_DATE_EPOCH="$(cd "$AD/../.." && git log -1 --format=%ct -- $YOL 2>/dev/null || true)"
    [ -n "$SOURCE_DATE_EPOCH" ] || SOURCE_DATE_EPOCH=1762819200
fi
export SOURCE_DATE_EPOCH
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
S="$T/p"; mkdir -p "$S/DEBIAN" "$S/opt/carotos"

kopyala_py() {   # dizin kopyala, onbellekleri at
    cp -r "$1" "$2"
    find "$2" -name '__pycache__' -type d -prune -exec rm -rf {} +
}

case "$PAKET" in
ortak)
    kopyala_py "$KAYNAK/opt/carotos/ortak" "$S/opt/carotos/"
    BAGIMLI="python3, python3-gi, gir1.2-gtk-3.0, python3-gi-cairo"
    ACIKLAMA="CarotOS ortak katman (tema, dil, etik koruma)
 CarotOS uygulamalarinin paylastigi Python/GTK3 kutuphaneleri ve 7 dillik ceviri dosyalari."
    ;;
keyring)
    # kendi DEBIAN/control dosyasi var (surum tarih bicimli); aynen kopyalanir
    cp -r "$AD/keyring-paketi/." "$S/"
    SURUM="$(sed -n 's/^Version: //p' "$S/DEBIAN/control")"
    ;;
gsd|former)
    kopyala_py "$KAYNAK/opt/carotos/$PAKET" "$S/opt/carotos/"
    rm -f "$S/opt/carotos/$PAKET/ikonlar.b64"
    install -d "$S/usr/share/applications" "$S/usr/share/icons/hicolor/scalable/apps" "$S/usr/bin"
    cp "$KAYNAK/usr/share/applications/carotos-$PAKET.desktop" "$S/usr/share/applications/"
    cp "$KAYNAK/usr/share/icons/hicolor/scalable/apps/carotos-$PAKET.svg" "$S/usr/share/icons/hicolor/scalable/apps/"
    # PNG simgeler kaynakta "<boyut> <base64>" satirlari olarak durur
    while read -r boyut veri; do
        [ -n "$boyut" ] || continue
        install -d "$S/usr/share/icons/hicolor/${boyut}x${boyut}/apps"
        printf '%s' "$veri" | base64 -d > "$S/usr/share/icons/hicolor/${boyut}x${boyut}/apps/carotos-$PAKET.png"
    done < "$KAYNAK/opt/carotos/$PAKET/ikonlar.b64"
    ln -s "/opt/carotos/$PAKET/carotos-$PAKET.py" "$S/usr/bin/carotos-$PAKET"
    BAGIMLI="python3, python3-gi, gir1.2-gtk-3.0, python3-gi-cairo, carotos-ortak (>= $SURUM)"
    if [ "$PAKET" = gsd ]; then
        ACIKLAMA="CarotOS GSD: Genel Sistem Sozlugu
 Linux, ag, siber guvenlik, kriptografi ve algoritma terimleri icin aranabilir, iki dilli sozluk."
    else
        ACIKLAMA="CarotOS Former: guvenlik uygulamalari rehberi
 CarotOS guvenlik araclari icin adim adim, canlandirmali baslangic rehberi."
    fi
    ;;
*) echo "Bilinmeyen paket: $PAKET" >&2; exit 2 ;;
esac

# izinler: dizin 755, dosya 644, betikler 755
find "$S" -mindepth 1 -type d -exec chmod 755 {} +
find "$S" -type f -not -path "$S/DEBIAN/*" -exec chmod 644 {} +
case "$PAKET" in gsd|former) chmod 755 "$S/opt/carotos/$PAKET/carotos-$PAKET.py" ;; esac
find "$S/opt/carotos/ortak" -name '*.py' -perm -u+x -exec chmod 644 {} + 2>/dev/null || true
find "$S" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +

# md5sums + control
(cd "$S" && find . -path ./DEBIAN -prune -o -type f -printf '%P\0' | sort -z | xargs -0 md5sum) > "$S/DEBIAN/md5sums"
KB=$(du -sk --exclude=DEBIAN "$S" | cut -f1)
AD_PAKET="carotos-$PAKET"
if [ "$PAKET" = keyring ]; then
    AD_PAKET="carotos-archive-keyring"
else
cat > "$S/DEBIAN/control" <<EOF
Package: carotos-$PAKET
Version: $SURUM
Section: misc
Priority: optional
Architecture: all
Maintainer: CarotOS <archive@carotos.org>
Homepage: https://carotos.org
Installed-Size: $KB
Depends: $BAGIMLI
Description: $ACIKLAMA
EOF
fi
chmod 644 "$S/DEBIAN/control" "$S/DEBIAN/md5sums"
mkdir -p "$CIKTI"
dpkg-deb --root-owner-group --build "$S" "$CIKTI/${AD_PAKET}_${SURUM}_all.deb" >/dev/null
echo "$CIKTI/${AD_PAKET}_${SURUM}_all.deb"
