#!/bin/bash
# Imzasiz depo agacini uretir:  tools/apt/depo-uret.sh <cikti-dizini> <paket.deb>...
# Imza BURADA atilmaz (anahtar bu makinede yok). Sonraki adim: tools/apt/imzala-yukle.sh (canli oturumda, sen).
set -euo pipefail
[ $# -ge 2 ] || { echo "Kullanim: $0 <cikti-dizini> <paket.deb>..." >&2; exit 2; }
AD="$(cd "$(dirname "$0")" && pwd)"
CIKTI="$1"; shift
REPREPRO="${REPREPRO:-reprepro}"
mkdir -p "$CIKTI/conf"
cp "$AD/conf/distributions" "$AD/conf/options" "$CIKTI/conf/"
grep -q '^SignWith' "$CIKTI/conf/distributions" && { echo "HATA: distributions icinde SignWith olmamali" >&2; exit 1; }
for deb in "$@"; do "$REPREPRO" -b "$CIKTI" includedeb stable "$deb"; done
"$REPREPRO" -b "$CIKTI" export
echo "Imzasiz depo hazir: $CIKTI/dists/stable/Release (imza yok)"
