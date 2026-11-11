#!/bin/bash
# ISO'yu imzalar. CANLI CarotOS oturumunda, sifreli anahtar USB'si bagliyken calistirilir (siz):
#   export GNUPGHOME=/mnt/anahtar/gnupg
#   bash tools/iso/imzala-iso.sh <ISO-dizini>
# Uretir: <ISO-dizini>/SHA256SUMS (dizindeki *.iso dosyalarinin ozetleri) ve SHA256SUMS.sign (ayrik, ASCII imza).
# Sonra imzayi YALNIZ genel anahtarla dogrular (kullanicinin yapacagi gibi). ISO'ya dokunmaz, yukleme yapmaz.
# Yayin: ISO ile birlikte SHA256SUMS ve SHA256SUMS.sign download.carotos.org'a yuklenir.
set -euo pipefail
[ $# -eq 1 ] && [ -d "$1" ] || { echo "Kullanim: $0 <ISO-dizini>" >&2; exit 2; }
D="$(cd "$1" && pwd)"
: "${GNUPGHOME:?GNUPGHOME ayarli degil: sifreli USB deki gnupg klasorunu verin}"
shopt -s nullglob
ISOLAR=("$D"/*.iso)
[ ${#ISOLAR[@]} -gt 0 ] || { echo "HATA: $D icinde .iso yok" >&2; exit 1; }
FPR=$(gpg --list-keys --with-colons | awk -F: '/^fpr/ {print $10; exit}')
echo "Imzalayan anahtar: $FPR"
(cd "$D" && LC_ALL=C sha256sum -- *.iso > SHA256SUMS)
cat "$D/SHA256SUMS"
gpg --default-key "$FPR" --armor --detach-sign --yes -o "$D/SHA256SUMS.sign" "$D/SHA256SUMS"
# Kullanicinin dogrulamasi: yalniz genel anahtarla (gizli anahtar kullanilmaz)
GEN="$(mktemp)"; trap 'rm -f "$GEN"' EXIT
gpg --export "$FPR" > "$GEN"
gpgv --keyring "$GEN" "$D/SHA256SUMS.sign" "$D/SHA256SUMS"
(cd "$D" && LC_ALL=C sha256sum -c SHA256SUMS)
echo "ISO-IMZA-TAMAM: $D/SHA256SUMS ve $D/SHA256SUMS.sign hazir"
