#!/bin/bash
# Yayinlanmis bir surumun icerigi degisti mi? (WSL/Debian'da, kok yetkisiz)
#   tools/apt/surum-denetle.sh            tum paketleri derler, tools/apt/yayin-ozetleri ile karsilastirir
#   tools/apt/surum-denetle.sh --kaydet   kayitli olmayan (paket, surum) ciftlerinin ozetini dosyaya ekler
# Hata verir:  (1) ayni surum, farkli icerik   (2) tablodaki surum kayitli en yuksek surumden dusuk
# Derlemeler tekrarlanabilir oldugu icin ozet karsilastirmasi anlamlidir.
set -euo pipefail
AD="$(cd "$(dirname "$0")" && pwd)"
KAYIT="$AD/yayin-ozetleri"
KAYDET=0; [ "${1:-}" = "--kaydet" ] && KAYDET=1
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
touch "$KAYIT"
HATA=0; YENI=()
for p in keyring $(awk '!/^#/ && NF {print $1}' "$AD/surumler"); do
    bash "$AD/paket-yap.sh" "$p" "$T" >/dev/null
done
for deb in "$T"/*.deb; do
    ad="$(dpkg-deb -f "$deb" Package)"; sur="$(dpkg-deb -f "$deb" Version)"; oz="$(sha256sum "$deb" | cut -d' ' -f1)"
    kayitli="$(awk -v a="$ad" -v s="$sur" '$1==a && $2==s {print $3}' "$KAYIT")"
    if [ -n "$kayitli" ]; then
        if [ "$kayitli" = "$oz" ]; then echo "tamam   $ad $sur"
        else echo "HATA    $ad $sur: icerik degisti ama surum ayni; surumler dosyasinda surumu artirin" >&2; HATA=1; fi
    else
        echo "yeni    $ad $sur (kayitli degil)"; YENI+=("$ad $sur $oz")
    fi
    while read -r s; do
        [ -n "$s" ] && dpkg --compare-versions "$sur" lt "$s" && { echo "HATA    $ad: surum $sur, kayitli en yuksek $s'den dusuk" >&2; HATA=1; }
    done < <(awk -v a="$ad" '$1==a {print $2}' "$KAYIT")
done
[ "$HATA" = 0 ] || exit 1
if [ "$KAYDET" = 1 ]; then
    for y in "${YENI[@]:-}"; do [ -n "$y" ] && echo "$y" >> "$KAYIT"; done
    echo "kaydedildi: ${#YENI[@]} yeni cift"
fi
echo "SURUM-DENETIMI-TAMAM"
