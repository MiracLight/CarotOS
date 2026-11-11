#!/bin/bash
# CANLI CarotOS oturumunda, sifreli anahtar USB'si bagliyken calistirilir (siz):
#   export GNUPGHOME=/mnt/anahtar/gnupg
#   tools/apt/imzala-yukle.sh <depo-dizini> [--sadece-imzala]   (deneme: imzalar, yuklemez)
# Release'i imzalar, once pool/ sonra dists/ yukler (dists en son: istemci eski dosya gormesin).
set -euo pipefail
[ $# -ge 1 ] && [ $# -le 2 ] && [ -d "$1/dists/stable" ] || { echo "Kullanim: $0 <depo-dizini> [--sadece-imzala]" >&2; exit 2; }
SADECE=0; [ "${2:-}" = "--sadece-imzala" ] && SADECE=1
D="$1"; R="$D/dists/stable"
: "${GNUPGHOME:?GNUPGHOME ayarli degil: sifreli USB deki gnupg klasorunu verin}"
FPR=$(gpg --list-keys --with-colons | awk -F: '/^fpr/ {print $10; exit}')
echo "Imzalayan anahtar: $FPR"
gpg --default-key "$FPR" --armor --detach-sign --yes -o "$R/Release.gpg" "$R/Release"
gpg --default-key "$FPR" --clearsign --yes -o "$R/InRelease" "$R/Release"
gpg --verify "$R/InRelease" && gpg --verify "$R/Release.gpg" "$R/Release"
[ "$SADECE" = 1 ] && { echo "Imza tamam, yukleme yapilmadi (--sadece-imzala)."; exit 0; }
echo "Imza tamam. Yuklemeden once emin misiniz? (e/H)"; read -r c; [ "$c" = e ] || exit 1
rclone copy "$D/pool" r2apt:carotos-apt/pool --checksum -v
rclone copy "$D/dists" r2apt:carotos-apt/dists --checksum -v
echo "Yuklendi. Test: temiz bir makinede  sudo apt update"
