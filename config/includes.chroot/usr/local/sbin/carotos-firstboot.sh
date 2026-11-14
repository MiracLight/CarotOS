#!/bin/sh
# CarotOS — ilk acilis ayarlari
#
# Kurulum sirasinda olusturulan normal kullaniciyi sudo ve wireshark
# gruplarina ekler. Bu betik chroot hook'unun yapamadigi seyi yapar:
# chroot hook'lari build sirasinda calisir, o an kurulum kullanicisi
# HENUZ YOKTUR.  Bu servis ise kurulmus sistemin ilk acilisinda calisir.
#
# wireshark grubu ve dumpcap'in yetkileri (cap_net_admin, cap_net_raw)
# zaten build sirasinda, wireshark-common paketinin kurulumuyla
# olusuyor -- eksik olan tek sey, gercek kullanicinin bu HAZIR gruba
# eklenmesi. Eklenmezse tshark "Couldn't run dumpcap in child process:
# Erisim engellendi" hatasi verir ve Guvenlik Paneli'ndeki tshark girisi
# de calismaz.

#
# sudo: kurucu (preseed, passwd/root-login false) ilk kullaniciyi zaten sudo'ya
# koyar. Bu betik yalnizca yedektir: sistemde TEK normal kullanici varsa ve sudo
# grubunda hic kimse yoksa o kullaniciyi ekler. Ilk acilistan once acilmis ikinci
# bir hesap (klonlanan sinif makinesi gibi) sessizce yonetici yapilmaz.
# Damga yalnizca butun adimlar basariliysa yazilir; hata olursa sonraki
# acilista yeniden denenir.
#
# CAROTOS_PASSWD / CAROTOS_DAMGA_DIZINI / CAROTOS_SOURCES yalnizca testler
# icindir (systemd birimi temiz ortamla calistirir).

PASSWD="${CAROTOS_PASSWD:-/etc/passwd}"
DAMGA_DIZINI="${CAROTOS_DAMGA_DIZINI:-/var/lib/carotos}"
SOURCES="${CAROTOS_SOURCES:-/etc/apt/sources.list}"
STAMP="$DAMGA_DIZINI/firstboot.done"
HATA=0

# Zaten calistiysa cik
[ -f "$STAMP" ] && exit 0

KULLANICILAR=$(awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' "$PASSWD")
SAYI=$(printf '%s\n' "$KULLANICILAR" | grep -c .)

if SUDO_SATIRI=$(getent group sudo 2>/dev/null); then
    SUDO_UYELER=$(printf '%s\n' "$SUDO_SATIRI" | cut -d: -f4)
    if [ -n "$SUDO_UYELER" ]; then
        logger -t carotos-firstboot "sudo grubunda zaten uye var ($SUDO_UYELER); dokunulmadi"
    elif [ "$SAYI" -eq 1 ]; then
        if usermod -aG sudo "$KULLANICILAR"; then
            logger -t carotos-firstboot "sudo grubuna eklendi: $KULLANICILAR"
        else
            logger -t carotos-firstboot -p user.err "sudo grubuna EKLENEMEDI: $KULLANICILAR"
            HATA=1
        fi
    elif [ "$SAYI" -gt 1 ]; then
        logger -t carotos-firstboot -p user.warning "sudo grubu bos ve $SAYI normal kullanici var; kimse yonetici yapilmadi"
    fi
fi

if getent group wireshark >/dev/null 2>&1; then
    for u in $KULLANICILAR; do
        if usermod -aG wireshark "$u"; then
            logger -t carotos-firstboot "wireshark grubuna eklendi: $u"
        else
            logger -t carotos-firstboot -p user.err "wireshark grubuna EKLENEMEDI: $u"
            HATA=1
        fi
    done
fi

# Kurulum CD'sini APT kaynak listesinden cikar
if [ -f "$SOURCES" ]; then
    sed -i "s|^deb cdrom:|#deb cdrom:|" "$SOURCES" || HATA=1
fi

if [ "$HATA" -ne 0 ]; then
    logger -t carotos-firstboot -p user.err "ilk acilis adimlari tamamlanamadi; sonraki acilista yeniden denenecek"
    exit 1
fi

mkdir -p "$DAMGA_DIZINI"
date > "$STAMP"
exit 0
