#!/bin/bash
# Tum paketleri sahte bir kok dizinde kurar / yukseltir / kaldirir (kok yetkisiz, dpkg --instdir).
# Bagimliliklar (python3, gtk, clamav...) sahte kokte yok: --force-depends. Bakilan seyler:
#  - tekrarlanabilir derleme (ayni kaynak, ayni bayt)
#  - hepsi tek seferde kurulunca dosya cakismasi yok (dpkg iki paketin ayni dosyayi sahiplenmesini reddeder)
#  - her uygulamada calistirilabilir dosya, masaustu girdisi, /usr/bin baglari gecerli hedefe gidiyor
#  - yukseltmede eski dosya kalmiyor, kaldirmada hicbir sey kalmiyor
set -euo pipefail
AD="$(cd "$(dirname "$0")" && pwd)"
UYGULAMALAR="gsd former health usb security-panel magaza paket kurtarma carotene filenor carotpot poligon welcome"
EKLER="acikla sleek yardimci"   # masaustu girdisi olmayan paketler
TUMU="ortak keyring $UYGULAMALAR $EKLER"
KAYNAK="$(cd "$AD/../.." && pwd)/config/includes.chroot"
opt_adi() { case "$1" in sleek) echo yanpanel;; yardimci) echo "";; *) echo "$1";; esac; }
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
for p in $EKLER; do
    "${DP[@]}" -s "carotos-$p" | grep -q '^Status: install ok installed' || hata "carotos-$p kurulu degil"
done
for x in usr/bin/carotos-acikla usr/bin/carotos-modernlestir usr/sbin/carotos-tema-kur usr/bin/carotos-saat-eslestir \
         usr/sbin/carotos-dil-hazirla usr/sbin/carotos-mac-ayar usr/sbin/carotos-magaza-apt usr/sbin/carotos-ufw-ayar \
         opt/carotos/yanpanel/carotos-yanpanel.py opt/carotos/sleek-ayar/carotos-sleek-ayar.py opt/carotos/poligon/ogrenci_uygulama.py opt/carotos/welcome/carotos-welcome.py; do
    [ -x "$R/$x" ] || hata "calistirilabilir olmali: $x"
done
[ -f "$R/etc/systemd/system/carotpot.service" ] && [ -f "$R/etc/carotpot/ayarlar.json" ] || hata "carotpot servis/ayar dosyalari"
[ -f "$R/usr/share/carotos/acikla.bash" ] && [ -f "$R/usr/share/carotos/welcome/logo.png" ] || hata "acikla.bash ya da karsilama gorselleri"
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
SURUM=1.4.3 bash "$AD/paket-yap.sh" gsd "$T/b" >/dev/null
mkdir -p "$T/x" && dpkg-deb -R "$T/b/carotos-gsd_1.4.3_all.deb" "$T/x" && rm "$T/x/opt/carotos/gsd/terimler/ag.py" \
  && (cd "$T/x" && find . -path ./DEBIAN -prune -o -type f -printf '%P\0' | sort -z | xargs -0 md5sum > DEBIAN/md5sums) \
  && dpkg-deb --root-owner-group -b "$T/x" "$T/b/yeni.deb" >/dev/null
"${DP[@]}" -i "$T/b/yeni.deb" >/dev/null 2>&1 || hata "yukseltme"
[ ! -e "$R/opt/carotos/gsd/terimler/ag.py" ] || hata "yukseltmede eski dosya kaldi"
"${DP[@]}" -s carotos-gsd | grep -q '^Version: 1.4.3' || hata "surum yukselmedi"
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
for p in $EKLER; do
    "${DP[@]}" -P "carotos-$p" >/dev/null 2>&1 || hata "purge $p"
    o="$(opt_adi "$p")"; [ -z "$o" ] || [ ! -e "$R/opt/carotos/$o" ] || hata "$p kalintisi"
done
"${DP[@]}" -P carotos-ortak carotos-archive-keyring >/dev/null 2>&1 || hata "purge ortak/keyring"
[ ! -e "$R/opt/carotos" ] || hata "/opt/carotos dizini kaldi"
KALAN=$(cd "$R" && find . -path ./var -prune -o \( -type f -o -type l \) -print)
[ -z "$KALAN" ] || { echo "$KALAN"; hata "kalinti dosya var"; }
echo "kaldirma: tamam, kalinti yok"

# ---- eski kurulumdan (ISO 1.4: dosyalar dpkg sahipsiz) gecis -------------------------------------------------
# ISO'nun koydugu dosyalarin aynisi sahte kokte durur; paketler hata vermeden uzerine kurulmali, eski/artik
# dosyalar kalmamali, kullanicinin degistirdigi CarotPot ayari korunmali.
G="$T/gecis"; mkdir -p "$G/var/lib/dpkg/"{info,updates,triggers} "$G/etc"
: > "$G/var/lib/dpkg/status"; : > "$G/var/lib/dpkg/available"
GP=(dpkg --force-not-root --force-depends --force-script-chrootless --instdir="$G" --admindir="$G/var/lib/dpkg" --log="$T/gecis.log")
for d in opt usr/share/applications usr/share/icons usr/share/carotos usr/local etc/carotpot etc/systemd etc/fail2ban etc/xdg; do
    mkdir -p "$G/$(dirname "$d")"; cp -r "$KAYNAK/$d" "$G/$d"
done
# ISO 1.4'te yardimcilar /usr/local altindaydi (dpkg sahipsiz): ayni dosyalari eski yerlerine de koy
for f in carotos-dil-hazirla carotos-mac-ayar carotos-magaza-apt carotos-ufw-ayar carotos-tema-kur; do
    mkdir -p "$G/usr/local/sbin"; cp "$KAYNAK/usr/sbin/$f" "$G/usr/local/sbin/$f"
done
for f in carotos-acikla carotos-modernlestir carotos-saat-eslestir; do
    mkdir -p "$G/usr/local/bin"; cp "$KAYNAK/usr/bin/$f" "$G/usr/local/bin/$f"
done
find "$G" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
echo "eski-artik" > "$G/opt/carotos/gsd/eski_artik.py"
mkdir -p "$G/opt/carotos/health/__pycache__"; echo x > "$G/opt/carotos/health/__pycache__/x.pyc"
echo '{"kullanici_ayari": true}' > "$G/etc/carotpot/ayarlar.json"
for p in $TUMU; do bash "$AD/paket-yap.sh" "$p" "$T/g" >/dev/null; done
"${GP[@]}" -i "$T"/g/*.deb >"$T/gecis.out" 2>"$T/gecis.err" || { cat "$T/gecis.err"; hata "eski kurulumun uzerine kurulum"; }
grep -qiE 'overwrit|another package|baska paket' "$T/gecis.err" && { cat "$T/gecis.err"; hata "dosya cakismasi uyarisi"; } || true
[ ! -e "$G/opt/carotos/gsd/eski_artik.py" ] || hata "gecis: eski artik dosya kaldi"
[ ! -e "$G/opt/carotos/health/__pycache__" ] || hata "gecis: eski __pycache__ kaldi"
grep -q kullanici_ayari "$G/etc/carotpot/ayarlar.json" || hata "gecis: kullanici CarotPot ayari kayboldu"
[ ! -e "$G/var/lib/carotos-gecis" ] || hata "gecis: yedek klasoru kaldi"
cmp -s "$G/etc/systemd/system/carotpot.service" "$KAYNAK/etc/systemd/system/carotpot.service" || hata "gecis: servis birimi paketin surumu degil"
for p in $TUMU; do
    ad="carotos-$p"; [ "$p" = keyring ] && ad=carotos-archive-keyring
    "${GP[@]}" -s "$ad" | grep -q '^Status: install ok installed' || hata "gecis: $ad kurulu degil"
done
# her paketin dosyasi artik dpkg sahipli (sahipsiz kalan CarotOS dosyasi olmamali); ISO'ya ozgu sistem dosyalari haric
SAHIPSIZ_N=0
for d in opt/carotos usr/share/applications; do
    while IFS= read -r f; do
        "${GP[@]}" -S "/${f#$G/}" >/dev/null 2>&1 || { echo "sahipsiz: ${f#$G}"; SAHIPSIZ_N=$((SAHIPSIZ_N+1)); }
    done < <(find "$G/$d" -type f -not -name carotos-kur.desktop -not -path "*/__pycache__/*")   # kur: yalniz canli ISO
done
[ "$SAHIPSIZ_N" -eq 0 ] || hata "gecis: $SAHIPSIZ_N sahipsiz CarotOS dosyasi kaldi"
for f in carotos-dil-hazirla carotos-mac-ayar carotos-magaza-apt carotos-ufw-ayar carotos-tema-kur; do
    [ ! -e "$G/usr/local/sbin/$f" ] || hata "gecis: eski /usr/local/sbin/$f kaldi"
done
[ ! -e "$G/usr/local/bin/carotos-acikla" ] || hata "gecis: eski /usr/local/bin/carotos-acikla kaldi"
for f in carotos-modernlestir carotos-saat-eslestir; do
    [ -L "$G/usr/local/bin/$f" ] && [ "$(readlink "$G/usr/local/bin/$f")" = "/usr/bin/$f" ] || hata "gecis: /usr/local/bin/$f uyumluluk baglisi yok"
done
echo "gecis: uyumluluk baglari tamam"
echo "gecis: tamam (eski kurulumun uzerine, ayar korundu, sahipsiz dosya yok)"
# temiz kurulumda (eski dosya yok) uyumluluk bagi olusmamali
K="$T/temiz"; mkdir -p "$K/var/lib/dpkg/"{info,updates,triggers} "$K/etc"; : > "$K/var/lib/dpkg/status"; : > "$K/var/lib/dpkg/available"
KP=(dpkg --force-not-root --force-depends --force-script-chrootless --instdir="$K" --admindir="$K/var/lib/dpkg" --log="$T/temiz.log")
"${KP[@]}" -i "$T"/g/carotos-yardimci_*.deb "$T"/g/carotos-sleek_*.deb >/dev/null 2>&1 || hata "temiz kurulum"
[ ! -e "$K/usr/local" ] || hata "temiz kurulumda /usr/local olusmamali"
echo "temiz kurulum: tamam"
echo "PAKET-TAMAM"
