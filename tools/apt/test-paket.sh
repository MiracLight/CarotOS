#!/bin/bash
# Tum paketleri sahte bir kok dizinde kurar / yukseltir / kaldirir (kok yetkisiz, dpkg --instdir).
# Bagimliliklar (python3, gtk, clamav...) sahte kokte yok: --force-depends. Bakilan seyler:
#  - tekrarlanabilir derleme (ayni kaynak, ayni bayt)
#  - hepsi tek seferde kurulunca dosya cakismasi yok (dpkg iki paketin ayni dosyayi sahiplenmesini reddeder)
#  - her uygulamada calistirilabilir dosya, masaustu girdisi, /usr/bin baglari gecerli hedefe gidiyor
#  - yukseltmede eski dosya kalmiyor, kaldirmada hicbir sey kalmiyor
set -euo pipefail
AD="$(cd "$(dirname "$0")" && pwd)"
UYGULAMALAR="gsd former health usb security-panel magaza carotene filenor"
TUMU="ortak keyring $UYGULAMALAR"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
R="$T/kok"; mkdir -p "$R/var/lib/dpkg/"{info,updates,triggers} "$R/etc"
: > "$R/var/lib/dpkg/status"; : > "$R/var/lib/dpkg/available"
DP=(dpkg --force-not-root --force-depends --force-script-chrootless --instdir="$R" --admindir="$R/var/lib/dpkg" --log="$T/dpkg.log")
hata() { echo "HATA: $*" >&2; exit 1; }

# tekrarlanabilirlik
for p in $TUMU; do
    bash "$AD/paket-yap.sh" "$p" "$T/r1" >/dev/null; bash "$AD/paket-yap.sh" "$p" "$T/r2" >/dev/null
    [ "$(cat "$T"/r1/*"$p"*.deb | sha256sum)" = "$(cat "$T"/r2/*"$p"*.deb | sha256sum)" ] || hata "$p derlemesi tekrarlanabilir degil"
done
echo "tekrarlanabilir: tamam ($(echo $TUMU | wc -w) paket)"

# hepsini tek seferde kur
for p in $TUMU; do bash "$AD/paket-yap.sh" "$p" "$T/a" >/dev/null; done
"${DP[@]}" -i "$T"/a/*.deb >/dev/null 2>"$T/hata.txt" || { cat "$T/hata.txt"; hata "toplu kurulum (dosya cakismasi?)"; }
for p in $UYGULAMALAR; do
    "${DP[@]}" -s "carotos-$p" | grep -q '^Status: install ok installed' || hata "carotos-$p kurulu degil"
    [ -n "$(find "$R/opt/carotos/$p" -type f -perm -u+x -name '*.py' -o -type f -perm -u+x -name '*-cli' | head -1)" ] || hata "$p: calistirilabilir dosya yok"
    "${DP[@]}" -L "carotos-$p" | grep -q '/usr/share/applications/.*\.desktop$' || hata "$p: masaustu girdisi yok"
    [ ! -e "$R/opt/carotos/$p/ikonlar.b64" ] || hata "$p: ikonlar.b64 paketten cikmaliydi"
done
for l in "$R"/usr/bin/*; do
    [ -L "$l" ] || continue
    [ -x "$R$(readlink "$l")" ] || hata "$(basename "$l") baglisi gecersiz hedefe gidiyor: $(readlink "$l")"
done
[ -f "$R/opt/carotos/ortak/dil.py" ] && [ -f "$R/usr/share/keyrings/carotos-archive-keyring.gpg" ] || hata "ortak ya da keyring eksik"
[ -f "$R/usr/share/icons/hicolor/48x48/apps/filenor.png" ] && [ -f "$R/usr/share/icons/hicolor/48x48/apps/carotos-gsd.png" ] || hata "png simgeler"
[ -f "$R/etc/xdg/autostart/carotos-usb-check.desktop" ] || hata "usb otomatik baslatma girdisi"
"${DP[@]}" -V $(for p in $TUMU; do [ "$p" = keyring ] && echo carotos-archive-keyring || echo carotos-$p; done) && echo "dpkg-V: temiz"
echo "kurulu dosya sayisi: $(find "$R" -path "$R/var" -prune -o \( -type f -o -type l \) -print | wc -l)"

# yukseltme: yeni surumde bir terim dosyasi yok olsun, eski dosya kalmamali
SURUM=1.4.2 bash "$AD/paket-yap.sh" gsd "$T/b" >/dev/null
mkdir -p "$T/x" && dpkg-deb -R "$T/b/carotos-gsd_1.4.2_all.deb" "$T/x" && rm "$T/x/opt/carotos/gsd/terimler/ag.py" \
  && (cd "$T/x" && find . -path ./DEBIAN -prune -o -type f -printf '%P\0' | sort -z | xargs -0 md5sum > DEBIAN/md5sums) \
  && dpkg-deb --root-owner-group -b "$T/x" "$T/b/yeni.deb" >/dev/null
"${DP[@]}" -i "$T/b/yeni.deb" >/dev/null 2>&1 || hata "yukseltme"
[ ! -e "$R/opt/carotos/gsd/terimler/ag.py" ] || hata "yukseltmede eski dosya kaldi"
"${DP[@]}" -s carotos-gsd | grep -q '^Version: 1.4.2' || hata "surum yukselmedi"
echo "yukseltme: tamam"

# uygulamalar root olarak calisinca __pycache__ birakir (dpkg bilmez): kaldirma bunu da temizlemeli
for p in $UYGULAMALAR; do mkdir -p "$R/opt/carotos/$p/__pycache__" && echo x > "$R/opt/carotos/$p/__pycache__/x.pyc"; done
mkdir -p "$R/opt/carotos/ortak/__pycache__" && echo x > "$R/opt/carotos/ortak/__pycache__/x.pyc"

# kaldirma: once uygulamalar (her biri tamamen gitmeli, ortak kalmali), sonra ortak ve keyring
for p in $UYGULAMALAR; do
    "${DP[@]}" -P "carotos-$p" >/dev/null 2>&1 || hata "purge $p"
    [ ! -e "$R/opt/carotos/$p" ] || hata "$p kalintisi"
    [ -f "$R/opt/carotos/ortak/dil.py" ] || hata "ortak $p kaldirilirken silindi"
done
"${DP[@]}" -P carotos-ortak carotos-archive-keyring >/dev/null 2>&1 || hata "purge ortak/keyring"
[ ! -e "$R/opt/carotos" ] || hata "/opt/carotos dizini kaldi"
KALAN=$(cd "$R" && find . -path ./var -prune -o \( -type f -o -type l \) -print)
[ -z "$KALAN" ] || { echo "$KALAN"; hata "kalinti dosya var"; }
echo "kaldirma: tamam, kalinti yok"
echo "PAKET-TAMAM"
