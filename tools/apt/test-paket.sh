#!/bin/bash
# GSD ve ortak paketleri sahte bir kok dizinde kurar / yukseltir / kaldirir (kok yetkisiz, dpkg --instdir).
# Bagimliliklar (python3, gtk) sahte kokte yok: --force-depends. Bakilan sey: dosya yerlesimi, izinler,
# yukseltmede eski dosyanin kalmamasi, kaldirmada her seyin silinmesi.
set -euo pipefail
AD="$(cd "$(dirname "$0")" && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
R="$T/kok"; mkdir -p "$R/var/lib/dpkg/"{info,updates,triggers} "$R/etc"
: > "$R/var/lib/dpkg/status"; : > "$R/var/lib/dpkg/available"
DP=(dpkg --force-not-root --force-depends --force-script-chrootless --instdir="$R" --admindir="$R/var/lib/dpkg" --log="$T/dpkg.log")
hata() { echo "HATA: $*" >&2; exit 1; }

# tekrarlanabilirlik: ayni kaynak iki kez derlenince ayni bayt (depodaki ozet degismesin)
for p in ortak gsd former keyring; do
    bash "$AD/paket-yap.sh" $p "$T/r1" >/dev/null; bash "$AD/paket-yap.sh" $p "$T/r2" >/dev/null
    [ "$(cat "$T"/r1/*"$p"*.deb | sha256sum)" = "$(cat "$T"/r2/*"$p"*.deb | sha256sum)" ] || hata "$p derlemesi tekrarlanabilir degil"
done
echo "tekrarlanabilir: tamam"
SURUM=1.4.0 bash "$AD/paket-yap.sh" ortak "$T/a" >/dev/null
SURUM=1.4.0 bash "$AD/paket-yap.sh" gsd   "$T/a" >/dev/null
SURUM=1.4.0 bash "$AD/paket-yap.sh" former "$T/a" >/dev/null
"${DP[@]}" -i "$T/a/carotos-ortak_1.4.0_all.deb" "$T/a/carotos-gsd_1.4.0_all.deb" "$T/a/carotos-former_1.4.0_all.deb" >/dev/null 2>"$T/hata.txt" || { cat "$T/hata.txt"; hata "kurulum"; }
[ -x "$R/opt/carotos/gsd/carotos-gsd.py" ] || hata "gsd calistirilabilir degil"
[ -L "$R/usr/bin/carotos-gsd" ] && [ "$(readlink "$R/usr/bin/carotos-gsd")" = /opt/carotos/gsd/carotos-gsd.py ] || hata "symlink"
[ -f "$R/opt/carotos/ortak/dil.py" ] && [ -f "$R/usr/share/applications/carotos-gsd.desktop" ] || hata "dosyalar eksik"
[ -f "$R/usr/share/icons/hicolor/48x48/apps/carotos-gsd.png" ] || hata "png simge"
[ ! -e "$R/opt/carotos/gsd/ikonlar.b64" ] || hata "ikonlar.b64 paketten cikmaliydi"
[ -x "$R/opt/carotos/former/carotos-former.py" ] && [ -f "$R/opt/carotos/former/konular/__init__.py" ] || hata "former eksik"
[ "$(readlink "$R/usr/bin/carotos-former")" = /opt/carotos/former/carotos-former.py ] || hata "former symlink"
[ -f "$R/usr/share/icons/hicolor/48x48/apps/carotos-former.png" ] && [ ! -e "$R/opt/carotos/former/ikonlar.b64" ] || hata "former simge"
"${DP[@]}" -s carotos-gsd | grep -q '^Status: install ok installed' || hata "durum"
"${DP[@]}" -L carotos-gsd | grep -c . | sed 's/^/gsd-dosya-sayisi: /'
"${DP[@]}" -V carotos-gsd carotos-former carotos-ortak && echo "dpkg-V: temiz"

# yukseltme: yeni surumde bir terim dosyasi yok olsun, eski dosya kalmamali
SURUM=1.4.1 bash "$AD/paket-yap.sh" gsd "$T/b" >/dev/null
mkdir -p "$T/x" && dpkg-deb -R "$T/b/carotos-gsd_1.4.1_all.deb" "$T/x" && rm "$T/x/opt/carotos/gsd/terimler/ag.py" \
  && (cd "$T/x" && find . -path ./DEBIAN -prune -o -type f -printf '%P\0' | sort -z | xargs -0 md5sum > DEBIAN/md5sums) \
  && dpkg-deb --root-owner-group -b "$T/x" "$T/b/yeni.deb" >/dev/null
"${DP[@]}" -i "$T/b/yeni.deb" >/dev/null 2>&1 || hata "yukseltme"
[ ! -e "$R/opt/carotos/gsd/terimler/ag.py" ] || hata "yukseltmede eski dosya kaldi"
"${DP[@]}" -s carotos-gsd | grep -q '^Version: 1.4.1' || hata "surum yukselmedi"
echo "yukseltme: tamam"

# kaldirma: gsd tamamen gitmeli, ortak kalmali; sonra ortak da
"${DP[@]}" -P carotos-gsd >/dev/null 2>&1 || hata "purge gsd"
[ ! -e "$R/opt/carotos/gsd" ] && [ ! -e "$R/usr/bin/carotos-gsd" ] && [ ! -e "$R/usr/share/applications/carotos-gsd.desktop" ] || hata "gsd kalintisi"
[ -f "$R/opt/carotos/ortak/dil.py" ] && [ -x "$R/opt/carotos/former/carotos-former.py" ] || hata "ortak ya da former yanlislikla silindi"
"${DP[@]}" -P carotos-former >/dev/null 2>&1 || hata "purge former"
[ ! -e "$R/opt/carotos/former" ] && [ ! -e "$R/usr/bin/carotos-former" ] && [ ! -e "$R/usr/share/applications/carotos-former.desktop" ] || hata "former kalintisi"
"${DP[@]}" -P carotos-ortak >/dev/null 2>&1 || hata "purge ortak"
KALAN=$(cd "$R" && find . -path ./var -prune -o \( -type f -o -type l \) -print | wc -l)
[ "$KALAN" = 0 ] || { (cd "$R" && find . -path ./var -prune -o \( -type f -o -type l \) -print); hata "kalinti dosya var"; }
echo "kaldirma: tamam, kalinti yok"
echo "PAKET-TAMAM"
