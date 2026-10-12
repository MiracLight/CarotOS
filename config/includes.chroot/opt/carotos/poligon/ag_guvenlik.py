"""
CarotOS Poligon -- ag guvenligi: loopback (127.0.0.0/8) dogrulamasi.

TEK GUVENLIK KAYNAGI. Sahte saldiri hedefleri (servisler) ve gorev
dogrulayici, bind adresinin SADECE loopback oldugunu buradan kontrol
eder. 127.0.0.0/8 araligindaki hicbir adres yonlendirilemez; trafik
makineyi ASLA terk etmez. Bu yuzden "IP ve Adres" ile uretilen sahte
adresler (orn. 127.45.0.1) guvenlidir -- gercek bir aga cikmazlar.

Ogretmen skor sunucusu (ogretmen_sunucu.sunucu_baslat) bu kuraldan
MUAFTIR: o, sinif agina erisilebilir olmak zorunda (0.0.0.0), cunku
koordinasyon icindir, bir saldiri HEDEFI degildir.
"""

from __future__ import annotations

import ipaddress

LOOPBACK_AGI = ipaddress.ip_network("127.0.0.0/8")


def loopback_adres_mi(adres) -> bool:
    """adres 127.0.0.0/8 icindeyse True. 0.0.0.0, LAN ya da genel IP'ler
    icin False. Gecersiz metin icin de False."""
    try:
        return ipaddress.ip_address(str(adres).strip()) in LOOPBACK_AGI
    except ValueError:
        return False
