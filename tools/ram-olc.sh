#!/bin/sh
# CarotOS boşta RAM ölçümü (yalnızca okur, hiçbir şeyi değiştirmez; root gerekmez).
#
# Nasıl ölçülür (her seferinde aynı): yeniden başlat, giriş yap, HİÇBİR ŞEY AÇMA (tarayıcı, terminal hariç bu betik),
# 2 dakika bekle, sonra:   sh ram-olc.sh
# Sonuç ekrana yazılır ve ~/ram-olcum-<tarih>.txt dosyasına kaydedilir (sürümler arası karşılaştırma için).
# Rakamlar RSS'tir: paylaşılan kütüphane sayfalarını da sayar, süreç RSS'lerinin toplamı "used" değerini vermez.
set -eu

tarih=$(date +%Y%m%d-%H%M%S)
cikti="$HOME/ram-olcum-$tarih.txt"

{
    echo "# CarotOS RAM ölçümü: $tarih"
    echo "# sürüm: $( ( . /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" ) || echo bilinmiyor )  çekirdek: $(uname -r)"
    echo "# oturum süresi: $(uptime -p 2>/dev/null || echo ?)"
    echo
    echo "## free -m"
    free -m
    echo
    echo "## en çok bellek kullanan 15 süreç (RSS KB)"
    ps -eo rss,comm --sort=-rss | head -n 16
    echo
    echo "## tarayıcı açık mı? (açıksa 'used' 300-500 MB şişer; iddia için KAPALI ölçün)"
    if pgrep -x firefox-esr >/dev/null 2>&1 || pgrep -x firefox >/dev/null 2>&1; then echo "EVET (ölçüm temiz değil)"; else echo "hayır"; fi
    echo
    echo "## CarotOS (Python/GTK) süreçleri (RSS KB)"
    ps -eo rss,args | grep -E "/opt/carotos/" | grep -v grep | head -n 20 || echo "yok"
    echo
    echo "## Xfce panel eklenti sarmalayıcıları (wrapper-2.0): hangi eklenti ne kadar?"
    ps -eo rss,args | grep -E "xfce4/panel/wrapper" | grep -v grep | head -n 10 || echo "yok"
    echo
    echo "## swap"
    swapon --show 2>/dev/null || echo "yok"
} | tee "$cikti"

echo
echo "Kaydedildi: $cikti"
