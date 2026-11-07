#!/bin/sh
# CarotOS RAM deneyi: bir ölçüm + geri alınan bir deney (root gerekmez, kalıcı hiçbir şeyi değiştirmez).
#
# Neden RSS değil PSS: RSS paylaşılan kütüphane sayfalarını (GTK, glib...) her süreçte tam sayar; bir süreci kaldırınca gerçekte
# geri gelen bellek PSS (paylaşılan sayfaların süreçlere bölünmüş payı) kadardır. Bu betik ikisini de yazar.
#
# Kullanım (Firefox kapalıyken, giriş yaptıktan ve 2 dakika bekledikten sonra):   sh ram-deney.sh
#   1) bellekteki sürecin RSS ve PSS değerleri
#   2) masaüstü duvar kağıdı dosyası (xfdesktop'un bellek payı büyük resimle şişer)
#   3) DENEY: xfwm4 saydamlığı (compositor) KAPATILIR, bellek ölçülür, ESKİ HALİNE GETİRİLİR (hata olsa da, Ctrl+C olsa da)
# Sonuç ~/ram-deney-<tarih>.txt dosyasına da yazılır.
set -u

tarih=$(date +%Y%m%d-%H%M%S)
cikti="$HOME/ram-deney-$tarih.txt"

kullanilan() { free -m | awk '/^Mem:/ {print $3}'; }

# PID için "RSS_MB PSS_MB"; PSS okunamazsa (başkasının süreci) "n/a"
bellek() {
    pid=$1
    rss=$(awk '/^VmRSS/ {printf "%.1f", $2/1024}' "/proc/$pid/status" 2>/dev/null)
    pss=$(awk '/^Pss:/ {printf "%.1f", $2/1024}' "/proc/$pid/smaps_rollup" 2>/dev/null)
    printf '%s %s\n' "${rss:-?}" "${pss:-n/a}"
}

satir() {  # etiket pid
    set -- "$1" "$2" "$(bellek "$2")"
    printf '%-34s pid %-6s RSS %-7s PSS %s\n' "$1" "$2" "${3% *}" "${3#* }"
}

xfwm4_pss() {
    pid=$(pgrep -x xfwm4 | head -n 1)
    [ -n "$pid" ] && bellek "$pid" | awk '{print $2}'
}

{
    echo "# CarotOS RAM deneyi: $tarih  ($(uname -r))"
    echo
    echo "## 1) Süreçler (MB): RSS = paylaşılanlar dahil, PSS = gerçek payı"
    for ad in xfwm4 Xorg xfdesktop nm-applet xfce4-panel pulseaudio xfsettingsd xfce4-session; do
        for pid in $(pgrep -x "$ad"); do satir "$ad" "$pid"; done
    done
    # panel eklenti sarmalayıcıları: hangi eklenti?
    for pid in $(pgrep -f "xfce4/panel/wrapper"); do
        eklenti=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | sed 's|.*plugins/lib\([a-z0-9_-]*\)\.so.*|\1|')
        satir "panel eklentisi: $eklenti" "$pid"
    done
    for ad in unattended-upgr fail2ban-server; do
        for pid in $(pgrep -f "$ad" | head -n 2); do satir "$ad (root)" "$pid"; done
    done
    echo
    echo "## 1b) TÜM süreçler, gerçek pay (PSS, MB), en büyük 25 (root süreçleri için 'sudo sh ram-deney.sh' çalıştırın)"
    for d in /proc/[0-9]*; do
        p=${d#/proc/}
        v=$(awk '/^Pss:/ {printf "%.1f", $2/1024}' "$d/smaps_rollup" 2>/dev/null) || continue
        [ -n "$v" ] || continue
        printf '%s %s %s\n' "$v" "$p" "$(cut -c1-40 "$d/comm" 2>/dev/null)"
    done | sort -rn | head -n 25 | awk '{printf "  %7s MB  pid %-6s %s\n", $1, $2, $3}'
    echo
    echo "## 1c) Süreçlerin toplam PSS'i ve çekirdek/diğer payı (MB)"
    toplam=$(for d in /proc/[0-9]*; do awk '/^Pss:/ {print $2}' "$d/smaps_rollup" 2>/dev/null; done | awk '{t+=$1} END {printf "%.0f", t/1024}')
    echo "  okunabilen süreçlerin toplam PSS'i : ${toplam:-?} MB (root olmadan başkalarının süreçleri eksik)"
    awk '/^(MemTotal|MemFree|Buffers|Cached|AnonPages|Shmem|Slab|SReclaimable|SUnreclaim|KernelStack|PageTables|Percpu|Mapped):/ {printf "  %-14s %7.0f MB\n", $1, $2/1024}' /proc/meminfo
    echo
    echo "## 2) Masaüstü duvar kağıdı"
    if command -v xfconf-query >/dev/null 2>&1; then
        xfconf-query -c xfce4-desktop -lv 2>/dev/null | grep -E "last-image" | head -n 3 || true
        for yol in $(xfconf-query -c xfce4-desktop -lv 2>/dev/null | awk '/last-image/ {print $2}' | sort -u); do
            [ -f "$yol" ] && ls -l "$yol" | awk '{printf "  dosya boyutu: %.1f MB  %s\n", $5/1048576, $9}'
        done
    else
        echo "  xfconf-query yok (Xfce oturumunda çalıştırın)"
    fi
    echo
    echo "## 3) DENEY: xfwm4 saydamlığı (compositing) kapalı"
} | tee "$cikti"

if ! command -v xfconf-query >/dev/null 2>&1 || [ -z "$(pgrep -x xfwm4 | head -n 1)" ]; then
    echo "  Xfce oturumu bulunamadı: deney atlandı." | tee -a "$cikti"
    exit 0
fi

onceki=$(xfconf-query -c xfwm4 -p /general/use_compositing 2>/dev/null || echo "")
if [ -z "$onceki" ]; then
    echo "  use_compositing okunamadı: deney atlandı." | tee -a "$cikti"
    exit 0
fi

geri_al() {
    xfconf-query -c xfwm4 -p /general/use_compositing -s "$onceki" >/dev/null 2>&1 || true
    echo "  (saydamlık eski haline getirildi: $onceki)"
}
trap 'geri_al' EXIT INT TERM HUP

oncekiusd=$(kullanilan)
oncekipss=$(xfwm4_pss)
{
    echo "  önce  (saydamlık $onceki): kullanılan ${oncekiusd} MB, xfwm4 PSS ${oncekipss:-?} MB"
    xfconf-query -c xfwm4 -p /general/use_compositing -s false
    sleep 6
    sonrausd=$(kullanilan)
    sonrapss=$(xfwm4_pss)
    echo "  sonra (saydamlık false):  kullanılan ${sonrausd} MB, xfwm4 PSS ${sonrapss:-?} MB"
    echo "  fark: kullanılan $((sonrausd - oncekiusd)) MB  (±10 MB gürültü olabilir; iki kez çalıştırıp karşılaştır)"
} | tee -a "$cikti"
echo
echo "Kaydedildi: $cikti"
