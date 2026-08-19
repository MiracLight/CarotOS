#!/bin/sh
# CarotOS — ilk acilis ayarlari
#
# Kurulum sirasinda olusturulan normal kullaniciyi sudo grubuna ekler.
# Bu betik chroot hook'unun yapamadigi seyi yapar: chroot hook'lari
# build sirasinda calisir, o an kurulum kullanicisi HENUZ YOKTUR.
# Bu servis ise kurulmus sistemin ilk acilisinda calisir.

STAMP=/var/lib/carotos/firstboot.done

# Zaten calistiysa cik
[ -f "$STAMP" ] && exit 0

if getent group sudo >/dev/null 2>&1; then
    for u in $(awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' /etc/passwd); do
        usermod -aG sudo "$u" || true
        logger -t carotos-firstboot "sudo grubuna eklendi: $u"
    done
fi

mkdir -p /var/lib/carotos
date > "$STAMP"

# Kurulum CD'sini APT kaynak listesinden cikar
if [ -f /etc/apt/sources.list ]; then
    sed -i "s|^deb cdrom:|#deb cdrom:|" /etc/apt/sources.list
fi

exit 0
