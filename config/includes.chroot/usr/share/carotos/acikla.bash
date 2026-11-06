# CarotOS Komut Açıklayıcı: yazdığın komut satırını Alt+E ile, ÇALIŞTIRMADAN açıklar.
# /etc/bash.bashrc içinden okunur; yalnızca etkileşimli bash'te çalışır.
case $- in
    *i*) ;;
    *) return 0 2>/dev/null ;;
esac
[ -n "$BASH_VERSION" ] || return 0 2>/dev/null
command -v carotos-acikla >/dev/null 2>&1 || return 0 2>/dev/null

carotos_acikla_satir() {
    printf '\n'
    carotos-acikla --satir "$READLINE_LINE"
}
bind -x '"\ee": carotos_acikla_satir' 2>/dev/null
