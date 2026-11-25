#!/bin/bash
# .deb uretir (WSL/Debian'da, kok yetkisiz):  tools/apt/paket-yap.sh <paket> <cikti-dizini>
# Paketler: ortak keyring gsd former health usb security-panel magaza paket kurtarma carotene filenor carotpot poligon welcome acikla sleek yardimci
# Kaynak tek yerde: config/includes.chroot. Dosyalar root:root, hook'taki izinlerle ayni.
# Surum: SURUM ortam degiskeni (varsayilan 1.4.0).
set -euo pipefail
TUMU="ortak keyring gsd former health usb security-panel magaza paket kurtarma carotene filenor carotpot poligon welcome acikla sleek yardimci"
[ $# -eq 2 ] || { echo "Kullanim: $0 <paket> <cikti-dizini>  (paket: $TUMU)" >&2; exit 2; }
PAKET="$1"; CIKTI="$2"
AD="$(cd "$(dirname "$0")" && pwd)"
KAYNAK="$(cd "$AD/../.." && pwd)/config/includes.chroot"
# Surumler paket basina: tools/apt/surumler ("ad surum ortak-en-az"). SURUM ortam degiskeni tabloyu ezer (yalniz test).
# Kural: depoya bir kez giren surumun icerigi bir daha degismez; icerik degisirse tabloda surum artirilir
# (tools/apt/surum-denetle.sh bunu yayin ozetleriyle denetler).
SURUM="${SURUM:-}"; ORTAK_MIN=""
if [ "$PAKET" != keyring ] && grep -qE "^$PAKET[[:space:]]" "$AD/surumler"; then
    [ -n "$SURUM" ] || SURUM="$(awk -v p="$PAKET" '$1==p {print $2}' "$AD/surumler")"
    ORTAK_MIN="$(awk -v p="$PAKET" '$1==p {print $3}' "$AD/surumler")"
fi

# ---- paket tablosu ---------------------------------------------------------------------------------------
# OPT: /opt/carotos/<OPT>   MASAUSTU: usr/share/applications/<ad>.desktop   EK: ek dosyalar (KAYNAK'a gore)
# EXEC: OPT icindeki calistirilabilir dosyalar   EXEC_ABS: paket kokune gore calistirilabilir dosyalar (usr/local/...)   BIN: "komut=OPT-icindeki-dosya" (/usr/bin baglari)
# ESKI: ISO 1.4'te /usr/local altinda dpkg sahipsiz duran eski yollar (ilk kurulumda kaldirilir)   COMPAT: "eski:yeni" uyumluluk
# baglari (kullanicilarin otomatik baslatma girdileri eski yolu gosterir; yalniz eski dosya varsa postinst olusturur)
# PNG_AD: ikonlar.b64'ten acilacak PNG adi   BAGIMLI/ONERILEN: ek paketler   ACIKLAMA: kisa + uzun aciklama
OPT=""; MASAUSTU=""; EK=""; EXEC=""; EXEC_ABS=""; ESKI=""; COMPAT=""; BIN=""; PNG_AD=""; BAGIMLI=""; ONERILEN=""; ONERI=""; ACIKLAMA=""
# ONERILEN -> Recommends (apt varsayilan kurar), ONERI -> Suggests (kurmaz). rkhunter Recommends'i exim4/ruby ceker:
# guvenlik dagitiminda istenmez, bu yuzden Suggests (ISO'da hook'lar zaten kurar).
HICOLOR="usr/share/icons/hicolor"
UYG_BAGIMLI="python3, python3-gi, gir1.2-gtk-3.0, python3-gi-cairo, carotos-ortak (>= $ORTAK_MIN)"
case "$PAKET" in
ortak) ;;
keyring) ;;
gsd)
    OPT=gsd; MASAUSTU=carotos-gsd; EK="$HICOLOR/scalable/apps/carotos-gsd.svg"; EXEC=carotos-gsd.py
    BIN="carotos-gsd=carotos-gsd.py"; PNG_AD=carotos-gsd; BAGIMLI="$UYG_BAGIMLI"
    ACIKLAMA="CarotOS GSD: Genel Sistem Sozlugu
 Linux, ag, siber guvenlik, kriptografi ve algoritma terimleri icin aranabilir, iki dilli sozluk." ;;
former)
    OPT=former; MASAUSTU=carotos-former; EK="$HICOLOR/scalable/apps/carotos-former.svg"; EXEC=carotos-former.py
    BIN="carotos-former=carotos-former.py"; PNG_AD=carotos-former; BAGIMLI="$UYG_BAGIMLI"
    ACIKLAMA="CarotOS Former: guvenlik uygulamalari rehberi
 CarotOS guvenlik araclari icin adim adim, canlandirmali baslangic rehberi." ;;
health)
    OPT=health; MASAUSTU=carotos-health; EXEC=carotos-health.py; BAGIMLI="$UYG_BAGIMLI"; ONERI="rkhunter, debsums"
    EK="$HICOLOR/256x256/apps/carotos-health.png $HICOLOR/scalable/apps/carotos-health.svg"
    ACIKLAMA="CarotOS Sistem Sagligi: guvenlik ve sistem denetimi
 Sistemin guvenlik ayarlarini ve sagligini denetleyen, her bulguyu aciklayan arac." ;;
usb)
    OPT=usb; MASAUSTU=carotos-usb-check; EXEC=carotos-usb-check.py; BAGIMLI="$UYG_BAGIMLI"
    EK="$HICOLOR/256x256/apps/carotos-usb-check.png $HICOLOR/scalable/apps/carotos-usb-check.svg etc/xdg/autostart/carotos-usb-check.desktop"
    ACIKLAMA="CarotOS USB Denetimi: takilan bellekleri denetler
 Takilan USB bellekleri tehlikeli dosyalar ve ayarlar icin tarar, bulgulari aciklar." ;;
security-panel)
    OPT=security-panel; MASAUSTU=carotos-security-panel; EXEC=carotos-security-panel.py; BAGIMLI="$UYG_BAGIMLI"
    ONERILEN="ufw, nmap"
    EK="usr/share/icons/carotos/security-panel-icon.png $HICOLOR/256x256/apps/carotos-security-panel.png"
    ACIKLAMA="CarotOS Guvenlik Paneli: guvenlik duvari, ag ve tarama
 Guvenlik duvari, ag durumu ve Nmap taramalari icin tek pencere." ;;
magaza)
    OPT=magaza; MASAUSTU=carotos-magaza; EXEC=carotos-magaza.py; BAGIMLI="$UYG_BAGIMLI, carotos-yardimci"
    EK="$HICOLOR/256x256/apps/carotos-magaza.png $HICOLOR/scalable/apps/carotos-magaza.svg usr/share/pixmaps/carotos-magaza.png"
    ACIKLAMA="CarotOS Magaza: secilmis uygulama katalogu
 Aciklamali, secilmis uygulamalari kurmak ve guncellemek icin arac." ;;
paket)
    OPT=paket; MASAUSTU=carotos-paket; EXEC=carotos-paket.py; BAGIMLI="$UYG_BAGIMLI, carotos-magaza, carotos-yardimci (>= 1.4.3)"
    EK="$HICOLOR/scalable/apps/carotos-paket.svg"
    ACIKLAMA="CarotOS Paket Kurucu: yerel .deb dosyasi kurar
 Bir .deb dosyasinin icerigini, ek paketlerini ve ozetini gosterir; onaydan sonra kurar." ;;
kurtarma)
    OPT=kurtarma; MASAUSTU=carotos-kurtarma; EXEC="carotos-kurtarma.py carotos-kurtarma-yonet"; BAGIMLI="$UYG_BAGIMLI, rsync"; ONERILEN="pkexec"
    EK="etc/apt/apt.conf.d/50carotos-kurtarma"; for b in 16x16 22x22 24x24 32x32 48x48 64x64 128x128 256x256; do EK="$EK $HICOLOR/$b/apps/carotos-kurtarma.png"; done
    ACIKLAMA="CarotOS Kurtarma: sistemi kayitli noktaya dondurur
 rsync ve sabit bag ile artimli kurtarma noktasi alir, gerektiginde sistemi o noktaya dondurur." ;;
carotene)
    OPT=carotene; MASAUSTU=carotos-carotene; EXEC=carotene.py; BAGIMLI="$UYG_BAGIMLI, clamav"; ONERILEN="clamav-freshclam"
    EK=""; for b in 16x16 22x22 24x24 32x32 48x48 64x64 128x128 256x256; do EK="$EK $HICOLOR/$b/apps/carotene.png"; done
    ACIKLAMA="Carotene: ClamAV ile virus taramasi
 ClamAV tabanli, sade arayuzlu virus tarayici." ;;
filenor)
    OPT=filenor; MASAUSTU=carotos-filenor; EXEC="filenor_uygulama.py filenor-cli"
    BIN="filenor=filenor_uygulama.py filenor-cli=filenor-cli"; PNG_AD=filenor
    EK="$HICOLOR/scalable/apps/filenor.svg"
    BAGIMLI="$UYG_BAGIMLI, ffmpeg, poppler-utils, qpdf, python3-pil, python3-reportlab, python3-fonttools, python3-brotli, python3-cairosvg"
    ONERILEN="tesseract-ocr, tesseract-ocr-tur, tesseract-ocr-eng, python3-pillow-heif"
    ACIKLAMA="Filenor: dosya donusturucu
 Goruntu, belge, ses ve video dosyalarini cihazdan cikmadan donusturur." ;;
carotpot)
    OPT=carotpot; MASAUSTU=carotos-carotpot; EXEC="carotpot.py carotpot-yonet carotpot-arayuz.py"
    BAGIMLI="$UYG_BAGIMLI, python3-asyncssh"; ONERILEN="ufw, fail2ban"
    EK=""; for b in 16x16 22x22 24x24 32x32 48x48 64x64 128x128 256x256; do EK="$EK $HICOLOR/$b/apps/carotpot.png"; done
    EK="$EK etc/carotpot/ayarlar.json etc/systemd/system/carotpot.service etc/systemd/system/carotpot-engel-temizle.service"
    EK="$EK etc/fail2ban/filter.d/carotos-carotpot.conf etc/fail2ban/jail.d/carotos-carotpot.local etc/xdg/autostart/carotpot-bildirim.desktop"
    AYAR="etc/carotpot/ayarlar.json"
    ACIKLAMA="CarotPot: yerel ag tuzagi (bal kupu)
 Yerel agda bu bilgisayari tarayan ya da saldiran cihazlari sahte hizmetlerle yakalayan arac. Hizmet acilista kendiliginden baslamaz."
    POSTINST='if [ -z "${DPKG_ROOT:-}" ]; then
    getent passwd carotpot >/dev/null || adduser --system --group --no-create-home --home /var/lib/carotpot --shell /usr/sbin/nologin carotpot
    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl enable carotpot-engel-temizle.service >/dev/null 2>&1 || true
fi'
    PRERM='if [ "$1" = remove ] && [ -z "${DPKG_ROOT:-}" ]; then
    systemctl stop carotpot.service >/dev/null 2>&1 || true
    systemctl disable carotpot-engel-temizle.service >/dev/null 2>&1 || true
fi'
    POSTRM='if [ "$1" = purge ]; then rm -rf "${DPKG_ROOT:-}/var/lib/carotpot" "${DPKG_ROOT:-}/var/log/carotpot"; fi
if [ -z "${DPKG_ROOT:-}" ]; then systemctl daemon-reload >/dev/null 2>&1 || true; fi' ;;
poligon)
    OPT=poligon; MASAUSTU=carotos-poligon-ogrenci; EXEC="ogrenci_uygulama.py ogretmen_uygulama.py"
    BAGIMLI="$UYG_BAGIMLI"; ONERILEN="nmap, hydra, john, sqlmap, tshark, ufw, fail2ban"
    EK="usr/share/applications/carotos-poligon-ogretmen.desktop $HICOLOR/256x256/apps/carotos-poligon-ogrenci.png $HICOLOR/256x256/apps/carotos-poligon-ogretmen.png"
    ACIKLAMA="CarotOS Poligon: guvenli sizma testi laboratuvari
 Ogrenci ve ogretmen uygulamalariyla yerel agda gorev, CTF yarismasi ve savunmaci gorunumu." ;;
welcome)
    OPT=welcome; MASAUSTU=carotos-welcome; EXEC=carotos-welcome.py
    BAGIMLI="$UYG_BAGIMLI, carotos-yardimci"; ONERILEN="carotos-acikla, carotos-sleek"
    EK="usr/share/carotos/welcome"
    ACIKLAMA="CarotOS Karsilama Sihirbazi
 Ilk oturumda acilan, Linux ve CarotOS uygulamalarini konu konu anlatan tanitim rehberi." ;;
acikla)
    OPT=acikla; ESKI="usr/local/bin/carotos-acikla"; EXEC_ABS="usr/bin/carotos-acikla"; BAGIMLI="python3, carotos-ortak (>= $ORTAK_MIN)"
    EK="usr/bin/carotos-acikla usr/share/carotos/acikla.bash"
    ACIKLAMA="CarotOS Komut Aciklayici (Alt+E)
 Bir komutu calistirmadan once ne yapacagini aciklar; terminalde Alt+E ile acilir."
    POSTINST='B="${DPKG_ROOT:-}/etc/bash.bashrc"
if [ -f "$B" ] && ! grep -q "carotos/acikla.bash" "$B"; then
    printf "\n# CarotOS Komut Aciklayici (Alt+E)\n[ -r /usr/share/carotos/acikla.bash ] && . /usr/share/carotos/acikla.bash\n" >> "$B"
fi'
    POSTRM='B="${DPKG_ROOT:-}/etc/bash.bashrc"
if { [ "$1" = remove ] || [ "$1" = purge ]; } && [ -f "$B" ]; then
    sed -i "/CarotOS Komut Aciklayici (Alt+E)/d;/carotos\/acikla.bash/d" "$B"
fi' ;;
sleek)
    OPT=yanpanel; MASAUSTU=carotos-sleek-ayar; EXEC=carotos-yanpanel.py
    ESKI="usr/local/sbin/carotos-tema-kur"; COMPAT="usr/local/bin/carotos-modernlestir:/usr/bin/carotos-modernlestir"
    EXEC_ABS="usr/bin/carotos-modernlestir usr/sbin/carotos-tema-kur opt/carotos/sleek-ayar/carotos-sleek-ayar.py"
    BAGIMLI="python3, python3-gi, gir1.2-gtk-3.0, python3-gi-cairo, carotos-ortak (>= $ORTAK_MIN)"
    EK="usr/bin/carotos-modernlestir usr/sbin/carotos-tema-kur opt/carotos/sleek-ayar"
    ACIKLAMA="CarotOS Carot Sleek: modern masaustu temasi ve yan panel
 Isteze bagli koyu tema, yuvarlak koseler, dock ve kenardan kayan CarotOS yan paneli; geri alinabilir." ;;
yardimci)
    ESKI="usr/local/sbin/carotos-dil-hazirla usr/local/sbin/carotos-mac-ayar usr/local/sbin/carotos-magaza-apt usr/local/sbin/carotos-ufw-ayar"
    COMPAT="usr/local/bin/carotos-saat-eslestir:/usr/bin/carotos-saat-eslestir"
    EXEC_ABS="usr/sbin/carotos-dil-hazirla usr/sbin/carotos-mac-ayar usr/sbin/carotos-magaza-apt usr/sbin/carotos-deb-kur usr/sbin/carotos-ufw-ayar usr/bin/carotos-saat-eslestir usr/bin/carotos-panel-eslestir usr/sbin/carotos-ceviri-ek"
    BAGIMLI="python3"; ONERILEN="pkexec"
    POSTINST='[ -n "${DPKG_ROOT:-}" ] || ! [ -e /usr/share/doc/xfdesktop4-data ] || /usr/sbin/carotos-ceviri-ek || true'
    EK="usr/sbin/carotos-dil-hazirla usr/sbin/carotos-mac-ayar usr/sbin/carotos-magaza-apt usr/sbin/carotos-deb-kur usr/sbin/carotos-ufw-ayar usr/bin/carotos-saat-eslestir usr/bin/carotos-panel-eslestir usr/sbin/carotos-ceviri-ek usr/share/carotos/ceviri-ek/xfdesktop.json etc/xdg/autostart/carotos-panel-eslestir.desktop"
    ACIKLAMA="CarotOS yardimci betikleri
 Uygulamalarin pkexec ile cagirdigi yetkili yardimcilar (dil hazirlama, MAC, guvenlik duvari, Magaza kurulumu, saat)." ;;
*) echo "Bilinmeyen paket: $PAKET (paket: $TUMU)" >&2; exit 2 ;;
esac

# ---- tekrarlanabilir derleme -----------------------------------------------------------------------------
# Ayni kaynak -> ayni .deb (ayni surumun ozeti depoda degismesin). Zaman damgasi = kaynaklara dokunan son commit.
if [ -z "${SOURCE_DATE_EPOCH:-}" ]; then
    case "$PAKET" in
        ortak) YOL="config/includes.chroot/opt/carotos/ortak" ;;
        keyring) YOL="tools/apt/keyring-paketi" ;;
        *) YOL=""
           [ -z "$OPT" ] || YOL="config/includes.chroot/opt/carotos/$OPT"
           [ -z "$MASAUSTU" ] || YOL="$YOL config/includes.chroot/usr/share/applications/$MASAUSTU.desktop"
           for e in $EK; do YOL="$YOL config/includes.chroot/$e"; done ;;
    esac
    # shellcheck disable=SC2086
    SOURCE_DATE_EPOCH="$(cd "$AD/../.." && git log -1 --format=%ct -- $YOL 2>/dev/null || true)"
    [ -n "$SOURCE_DATE_EPOCH" ] || SOURCE_DATE_EPOCH=1762819200
fi
export SOURCE_DATE_EPOCH

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
S="$T/p"; mkdir -p "$S/DEBIAN" "$S/opt/carotos"

ekle() {   # KAYNAK'a gore dosya ya da dizin kopyala
    [ -e "$KAYNAK/$1" ] || { echo "HATA: kaynak yok: $1" >&2; exit 1; }
    mkdir -p "$S/$(dirname "$1")"; cp -r "$KAYNAK/$1" "$S/$1"
}
temizle() { find "$S" -name '__pycache__' -type d -prune -exec rm -rf {} +; }

# ---- icerik ----------------------------------------------------------------------------------------------
case "$PAKET" in
ortak)
    ekle opt/carotos/ortak; temizle
    BAGIMLI="python3, python3-gi, gir1.2-gtk-3.0, python3-gi-cairo"
    ACIKLAMA="CarotOS ortak katman (tema, dil, etik koruma)
 CarotOS uygulamalarinin paylastigi Python/GTK3 kutuphaneleri ve 7 dillik ceviri dosyalari." ;;
keyring)
    # kendi DEBIAN/control dosyasi var (surum tarih bicimli); aynen kopyalanir
    cp -r "$AD/keyring-paketi/." "$S/"
    SURUM="$(sed -n 's/^Version: //p' "$S/DEBIAN/control")" ;;
*)
    if [ -n "$OPT" ]; then ekle "opt/carotos/$OPT"; rm -f "$S/opt/carotos/$OPT/ikonlar.b64"; fi
    [ -z "$MASAUSTU" ] || ekle "usr/share/applications/$MASAUSTU.desktop"
    for e in $EK; do ekle "$e"; done
    temizle
    if [ -n "$PNG_AD" ]; then   # PNG simgeler kaynakta "<boyut> <base64>" satirlari olarak durur
        while read -r boyut veri; do
            [ -n "$boyut" ] || continue
            install -d "$S/$HICOLOR/${boyut}x${boyut}/apps"
            printf '%s' "$veri" | base64 -d > "$S/$HICOLOR/${boyut}x${boyut}/apps/$PNG_AD.png"
        done < "$KAYNAK/opt/carotos/$OPT/ikonlar.b64"
    fi
    for b in $BIN; do
        install -d "$S/usr/bin"; ln -s "/opt/carotos/$OPT/${b#*=}" "$S/usr/bin/${b%%=*}"
    done ;;
esac

# ---- bakim betikleri ---------------------------------------------------------------------------------------
# DPKG_ROOT: test ortaminda (dpkg --instdir) gercek sisteme dokunmaz. ISO 1.4 bu dosyalari dpkg sahipsiz koydu:
# preinst ilk kurulumda sahipsiz eski kopyalari kaldirir (yoksa dpkg "baska yerden geliyor" diye reddeder);
# Kullanici ayari dosyalari (AYAR) silinmez: yedeklenip postinst'te (paketin varsayilanindan farkliysa) geri konur;
# diger sahipsiz /etc dosyalari (servis birimleri vb.) paketin surumuyle degisir.
# Uygulama root olarak (pkexec) calisinca olusan __pycache__ dpkg'nin bilmedigi dosyalardir; kaldirmada dizin
# bos kalsin diye uygulama dizini silinir.
POSTINST="${POSTINST:-}"; PRERM="${PRERM:-}"; POSTRM="${POSTRM:-}"; AYAR="${AYAR:-}"
if [ "$PAKET" != keyring ]; then
    D="$OPT"; [ "$PAKET" = ortak ] && D=ortak
    LISTE="$T/liste"
    (cd "$S" && find . -path ./DEBIAN -prune -o \( -type f -o -type l \) -print | sed 's|^\./|/|' | sort) > "$LISTE"
    ETC="$(grep '^/etc/' "$LISTE" || true)"        # hepsi conffile
    AYAR_L=""; for a in $AYAR; do AYAR_L="$AYAR_L /$a"; done   # AYAR: kullanicinin degistirdigi dosyalar (yedeklenir, geri konur)
    if [ -n "$D" ]; then
        DIGER="$(grep -v "^/opt/carotos/$D/" "$LISTE" || true)"
        PROBE="$(grep "^/opt/carotos/$D/" "$LISTE" | head -1 || true)"
    else
        DIGER="$(cat "$LISTE")"; PROBE=""
    fi
    for a in $AYAR_L; do DIGER="$(printf '%s
' "$DIGER" | grep -vxF "$a" || true)"; done
    {
        echo '#!/bin/sh'
        echo 'set -e'
        echo '[ "$1" = install ] || exit 0'
        echo 'R="${DPKG_ROOT:-}"'
        echo 'SAHIPSIZ() { ! dpkg -S "$1" >/dev/null 2>&1; }'
        echo "YEDEK=\"\$R/var/lib/carotos-gecis/$PAKET\""
        if [ -n "$PROBE" ]; then
            echo "if [ -e \"\$R$PROBE\" ] && SAHIPSIZ \"$PROBE\"; then rm -rf \"\$R/opt/carotos/$D\"; fi"
        fi
        for f in $DIGER; do
            echo "if { [ -e \"\$R$f\" ] || [ -L \"\$R$f\" ]; } && SAHIPSIZ \"$f\"; then rm -f \"\$R$f\"; fi"
        done
        for f in $ESKI; do
            echo "if { [ -e \"\$R/$f\" ] || [ -L \"\$R/$f\" ]; } && SAHIPSIZ \"/$f\"; then rm -f \"\$R/$f\"; fi"
        done
        echo "UYUM=\"\$R/var/lib/carotos-gecis/$PAKET.uyum\""
        for c in $COMPAT; do
            e="${c%%:*}"; k="$(echo "$e" | tr / _)"
            echo "if { [ -e \"\$R/$e\" ] || [ -L \"\$R/$e\" ]; } && SAHIPSIZ \"/$e\"; then mkdir -p \"\$UYUM\"; : > \"\$UYUM/$k\"; rm -f \"\$R/$e\"; fi"
        done
        for f in $AYAR_L; do
            echo "if [ -f \"\$R$f\" ] && SAHIPSIZ \"$f\"; then mkdir -p \"\$YEDEK$(dirname "$f")\"; mv \"\$R$f\" \"\$YEDEK$f\"; fi"
        done
        echo 'exit 0'
    } > "$S/DEBIAN/preinst"
    {
        echo '#!/bin/sh'
        echo 'set -e'
        echo '[ "$1" = configure ] || exit 0'
        echo 'R="${DPKG_ROOT:-}"'
        echo "YEDEK=\"\$R/var/lib/carotos-gecis/$PAKET\""
        echo 'if [ -d "$YEDEK" ]; then'
        echo '    (cd "$YEDEK" && find . -type f) | while read -r f; do'
        echo '        f="${f#.}"'
        echo '        if [ -f "$R$f" ] && ! cmp -s "$YEDEK$f" "$R$f"; then cp -p "$YEDEK$f" "$R$f"; fi'
        echo '    done'
        echo '    rm -rf "$YEDEK"; rmdir "$R/var/lib/carotos-gecis" 2>/dev/null || true'
        echo 'fi'
        echo "UYUM=\"\$R/var/lib/carotos-gecis/$PAKET.uyum\""
        for c in $COMPAT; do
            e="${c%%:*}"; y="${c#*:}"; k="$(echo "$e" | tr / _)"
            echo "if [ -e \"\$UYUM/$k\" ]; then ln -sf \"$y\" \"\$R/$e\"; fi"
        done
        echo 'rm -rf "$UYUM"; rmdir "$R/var/lib/carotos-gecis" 2>/dev/null || true'
        [ -z "$POSTINST" ] || echo "$POSTINST"
        if grep -q '^/usr/share/icons/' "$LISTE"; then
            echo '[ -n "${DPKG_ROOT:-}" ] || gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true'
        fi
        echo 'exit 0'
    } > "$S/DEBIAN/postinst"
    if [ -n "$PRERM" ]; then { echo '#!/bin/sh'; echo 'set -e'; echo "$PRERM"; echo 'exit 0'; } > "$S/DEBIAN/prerm"; fi
    {
        echo '#!/bin/sh'
        echo 'set -e'
        if [ -n "$D" ]; then
            echo 'case "$1" in'
            echo '    remove|purge)'
            echo "        rm -rf \"\${DPKG_ROOT:-}/opt/carotos/$D\""
            echo '        rmdir "${DPKG_ROOT:-}/opt/carotos" 2>/dev/null || true'
            echo '        ;;'
            echo 'esac'
        fi
        for c in $COMPAT; do
            e="${c%%:*}"; y="${c#*:}"
            echo "if [ \"\$1\" = remove ] || [ \"\$1\" = purge ]; then if [ -L \"\${DPKG_ROOT:-}/$e\" ] && [ \"\$(readlink \"\${DPKG_ROOT:-}/$e\")\" = \"$y\" ]; then rm -f \"\${DPKG_ROOT:-}/$e\"; fi; fi"
        done
        [ -z "$POSTRM" ] || echo "$POSTRM"
        echo 'exit 0'
    } > "$S/DEBIAN/postrm"
    for b in preinst postinst prerm postrm; do [ -f "$S/DEBIAN/$b" ] && chmod 755 "$S/DEBIAN/$b"; done
    # /etc altindaki dosyalar conffile (kullanici degistirebilir; dpkg sormadan ezmez)
    [ -z "$ETC" ] || echo "$ETC" > "$S/DEBIAN/conffiles"
fi

# ---- izinler: dizin 755, dosya 644, betikler 755 ---------------------------------------------------------
find "$S" -mindepth 1 -type d -exec chmod 755 {} +
find "$S" -type f -not -path "$S/DEBIAN/*" -exec chmod 644 {} +
for x in $EXEC; do chmod 755 "$S/opt/carotos/$OPT/$x"; done
for x in $EXEC_ABS; do chmod 755 "$S/$x"; done
[ -d "$S/opt/carotos/ortak" ] && find "$S/opt/carotos/ortak" -name '*.py' -perm -u+x -exec chmod 644 {} + 2>/dev/null || true
find "$S" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +

# ---- md5sums + control -----------------------------------------------------------------------------------
(cd "$S" && find . -path ./DEBIAN -prune -o -type f -printf '%P\0' | sort -z | xargs -0 md5sum) > "$S/DEBIAN/md5sums"
KB=$(du -sk --exclude=DEBIAN "$S" | cut -f1)
AD_PAKET="carotos-$PAKET"
if [ "$PAKET" = keyring ]; then
    AD_PAKET="carotos-archive-keyring"
else
    {
        echo "Package: carotos-$PAKET"; echo "Version: $SURUM"; echo "Section: misc"; echo "Priority: optional"
        echo "Architecture: all"; echo "Maintainer: CarotOS <archive@carotos.org>"; echo "Homepage: https://carotos.org"
        echo "Installed-Size: $KB"; echo "Depends: $BAGIMLI"
        [ -n "$ONERILEN" ] && echo "Recommends: $ONERILEN"
        [ -n "$ONERI" ] && echo "Suggests: $ONERI"
        echo "Description: $ACIKLAMA"
    } > "$S/DEBIAN/control"
fi
chmod 644 "$S/DEBIAN/control" "$S/DEBIAN/md5sums"
[ ! -f "$S/DEBIAN/conffiles" ] || chmod 644 "$S/DEBIAN/conffiles"
mkdir -p "$CIKTI"
dpkg-deb --root-owner-group --build "$S" "$CIKTI/${AD_PAKET}_${SURUM}_all.deb" >/dev/null
echo "$CIKTI/${AD_PAKET}_${SURUM}_all.deb"
