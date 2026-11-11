#!/bin/bash
# .deb uretir (WSL/Debian'da, kok yetkisiz):  tools/apt/paket-yap.sh <ortak|gsd> <cikti-dizini>
# Kaynak tek yerde: config/includes.chroot. Dosyalar root:root, hook'taki izinlerle ayni.
# Surum: SURUM ortam degiskeni (varsayilan 1.4.0).
set -euo pipefail
[ $# -eq 2 ] || { echo "Kullanim: $0 <ortak|gsd> <cikti-dizini>" >&2; exit 2; }
PAKET="$1"; CIKTI="$2"
AD="$(cd "$(dirname "$0")" && pwd)"
KAYNAK="$(cd "$AD/../.." && pwd)/config/includes.chroot"
SURUM="${SURUM:-1.4.0}"
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
gsd)
    kopyala_py "$KAYNAK/opt/carotos/gsd" "$S/opt/carotos/"
    rm -f "$S/opt/carotos/gsd/ikonlar.b64"
    install -d "$S/usr/share/applications" "$S/usr/share/icons/hicolor/scalable/apps" "$S/usr/bin"
    cp "$KAYNAK/usr/share/applications/carotos-gsd.desktop" "$S/usr/share/applications/"
    cp "$KAYNAK/usr/share/icons/hicolor/scalable/apps/carotos-gsd.svg" "$S/usr/share/icons/hicolor/scalable/apps/"
    # PNG simgeler kaynakta "<boyut> <base64>" satirlari olarak durur
    while read -r boyut veri; do
        [ -n "$boyut" ] || continue
        install -d "$S/usr/share/icons/hicolor/${boyut}x${boyut}/apps"
        printf '%s' "$veri" | base64 -d > "$S/usr/share/icons/hicolor/${boyut}x${boyut}/apps/carotos-gsd.png"
    done < "$KAYNAK/opt/carotos/gsd/ikonlar.b64"
    ln -s /opt/carotos/gsd/carotos-gsd.py "$S/usr/bin/carotos-gsd"
    BAGIMLI="python3, python3-gi, gir1.2-gtk-3.0, python3-gi-cairo, carotos-ortak (>= $SURUM)"
    ACIKLAMA="CarotOS GSD: Genel Sistem Sozlugu
 Linux, ag, siber guvenlik, kriptografi ve algoritma terimleri icin aranabilir, iki dilli sozluk."
    ;;
*) echo "Bilinmeyen paket: $PAKET" >&2; exit 2 ;;
esac

# izinler: dizin 755, dosya 644, betikler 755
find "$S" -mindepth 1 -type d -exec chmod 755 {} +
find "$S" -type f -not -path "$S/DEBIAN/*" -exec chmod 644 {} +
[ "$PAKET" = gsd ] && chmod 755 "$S/opt/carotos/gsd/carotos-gsd.py"
find "$S/opt/carotos/ortak" -name '*.py' -perm -u+x -exec chmod 644 {} + 2>/dev/null || true

# md5sums + control
(cd "$S" && find . -path ./DEBIAN -prune -o -type f -printf '%P\0' | sort -z | xargs -0 md5sum) > "$S/DEBIAN/md5sums"
KB=$(du -sk --exclude=DEBIAN "$S" | cut -f1)
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
chmod 644 "$S/DEBIAN/control" "$S/DEBIAN/md5sums"
mkdir -p "$CIKTI"
dpkg-deb --root-owner-group --build "$S" "$CIKTI/carotos-${PAKET}_${SURUM}_all.deb" >/dev/null
echo "$CIKTI/carotos-${PAKET}_${SURUM}_all.deb"
