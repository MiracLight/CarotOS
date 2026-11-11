#!/bin/bash
# Bos depoyu kok yetkisi olmadan uretir, keyring paketini derler ve ayri apt dizinleriyle `apt update` dener.
# Imza yok: depo burada bir "gecici" anahtarla imzalanir (yalniz test). Gercek anahtara dokunulmaz.
set -euo pipefail
AD="$(cd "$(dirname "$0")" && pwd)"
REPREPRO="${REPREPRO:-reprepro}"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export GNUPGHOME="$T/gnupg"; mkdir -m 700 "$GNUPGHOME"
gpg --batch --pinentry-mode loopback --passphrase "" --quick-generate-key "Test <test@example.invalid>" ed25519 cert,sign 1d >/dev/null 2>&1
FPR=$(gpg --list-keys --with-colons | awk -F: '/^fpr/ {print $10; exit}')
mkdir -p "$T/depo/conf"; cp "$AD/conf/distributions" "$AD/conf/options" "$T/depo/conf/"
echo "SignWith: $FPR" >> "$T/depo/conf/distributions"
"$REPREPRO" -b "$T/depo" export >/dev/null
gpg --export "$FPR" > "$T/test-anahtar.gpg"
ls "$T/depo/dists/stable"
grep -E '^(Origin|Codename|Valid-Until|Acquire-By-Hash)' "$T/depo/dists/stable/Release"
# apt: ayri dizinler, file: URI
mkdir -p "$T/apt/"{state/lists/partial,cache/archives/partial,etc/sources.list.d,etc/trusted.gpg.d,etc/preferences.d}
cat > "$T/apt/etc/sources.list.d/test.sources" <<S
Types: deb
URIs: file://$T/depo
Suites: stable
Components: main
Signed-By: $T/test-anahtar.gpg
S
touch "$T/apt/etc/sources.list" "$T/apt/status"
apt-get -o Dir::State="$T/apt/state" -o Dir::State::status="$T/apt/status" -o Dir::Cache="$T/apt/cache" \
  -o Dir::Etc::sourcelist="$T/apt/etc/sources.list" -o Dir::Etc::sourceparts="$T/apt/etc/sources.list.d" \
  -o Dir::Etc::trusted=/dev/null -o Dir::Etc::trustedparts="$T/apt/etc/trusted.gpg.d" \
  -o APT::Sandbox::User="" update 2>&1 | tail -5
echo "BOS-DEPO-TAMAM"
