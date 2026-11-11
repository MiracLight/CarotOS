#!/bin/bash
# Depoyu kok yetkisi olmadan uretir (imzasiz -> by-hash -> gecici anahtarla imza), anahtarlik paketini icine koyar ve
# ayri apt dizinleriyle HTTP uzerinden `apt update` dener; by-hash adresinin gercekten istendigini dogrular.
# Gercek anahtara dokunulmaz.
set -euo pipefail
AD="$(cd "$(dirname "$0")" && pwd)"
REPREPRO="${REPREPRO:-reprepro}"
T="$(mktemp -d)"; SUNUCU=""; trap '[ -n "$SUNUCU" ] && kill $SUNUCU 2>/dev/null; rm -rf "$T"' EXIT
export GNUPGHOME="$T/gnupg"; mkdir -m 700 "$GNUPGHOME"
gpg --batch --pinentry-mode loopback --passphrase "" --quick-generate-key "Test <test@example.invalid>" ed25519 cert,sign 1d >/dev/null 2>&1
FPR=$(gpg --list-keys --with-colons | awk -F: '/^fpr/ {print $10; exit}')
cp -r "$AD/keyring-paketi" "$T/k"; find "$T/k" -type d -exec chmod 755 {} +; find "$T/k" -type f -exec chmod 644 {} +
dpkg-deb --root-owner-group --build "$T/k" "$T/k.deb" >/dev/null
REPREPRO="$REPREPRO" bash "$AD/depo-uret.sh" "$T/depo" "$T/k.deb" >/dev/null
R="$T/depo/dists/stable"
gpg --default-key "$FPR" --armor --detach-sign -o "$R/Release.gpg" "$R/Release"
gpg --default-key "$FPR" --clearsign -o "$R/InRelease" "$R/Release"
gpg --export "$FPR" > "$T/test-anahtar.gpg"
grep -E '^(Origin|Codename|Valid-Until|Acquire-By-Hash)' "$R/Release"
# by-hash dosyalari gercekten ozetle ayni mi
H=$(sha256sum "$R/main/binary-amd64/Packages" | cut -d' ' -f1)
cmp "$R/main/binary-amd64/Packages" "$R/main/binary-amd64/by-hash/SHA256/$H" && echo "by-hash-ozet-dogru"
# HTTP sunucusu
PORT=$((20000 + RANDOM % 20000))
(cd "$T/depo" && python3 -m http.server "$PORT" --bind 127.0.0.1 >"$T/http.log" 2>&1) & SUNUCU=$!
sleep 1
mkdir -p "$T/apt/"{state/lists/partial,cache/archives/partial,etc/sources.list.d,etc/trusted.gpg.d}
cat > "$T/apt/etc/sources.list.d/test.sources" <<S
Types: deb
URIs: http://127.0.0.1:$PORT
Suites: stable
Components: main
Signed-By: $T/test-anahtar.gpg
S
touch "$T/apt/etc/sources.list" "$T/apt/status"
APT=(apt-get -o Dir::State="$T/apt/state" -o Dir::State::status="$T/apt/status" -o Dir::Cache="$T/apt/cache"
  -o Dir::Etc::sourcelist="$T/apt/etc/sources.list" -o Dir::Etc::sourceparts="$T/apt/etc/sources.list.d"
  -o Dir::Etc::trusted=/dev/null -o Dir::Etc::trustedparts="$T/apt/etc/trusted.gpg.d" -o APT::Sandbox::User="")
"${APT[@]}" update 2>&1 | tail -4
grep -c "by-hash/SHA256" "$T/http.log" | sed 's/^/by-hash-istek-sayisi: /'
grep -q "by-hash/SHA256" "$T/http.log" || { echo "HATA: apt by-hash istemedi"; exit 1; }
apt-cache -o Dir::State="$T/apt/state" -o Dir::State::status="$T/apt/status" -o Dir::Cache="$T/apt/cache" \
  -o Dir::Etc::sourcelist="$T/apt/etc/sources.list" -o Dir::Etc::sourceparts="$T/apt/etc/sources.list.d" \
  -o Dir::Etc::trustedparts="$T/apt/etc/trusted.gpg.d" policy carotos-archive-keyring | sed -n 1,3p
echo "DEPO-TAMAM"
