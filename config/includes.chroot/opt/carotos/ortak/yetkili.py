# -*- coding: utf-8 -*-
"""CarotOS ortak -- yetkiyle (pkexec/sudo) calistirilacak programlarin yolunu bulma.

NEDEN: pkexec'e ya da sudo'ya verilen program adi kullanicinin PATH'inden cozulurse, kullanici
hesabinda calisan bir yazilim ~/.local/bin gibi bir dizine ayni adli bir dosya birakip kullanicinin
bir sonraki parola girisini root yetkisine cevirebilir (Debian'in ~/.profile dosyasi ~/.local/bin'i
PATH'in BASINA ekler). Parola penceresi yolu gosterse de yeni baslayan biri bunu fark etmez.

Bu yuzden root olarak calisacak HER program yalnizca asagidaki, yalnizca root'un yazabildigi sistem
dizinlerinde aranir. Uygulamalar `shutil.which(ad)` yerine `sistem_yolu(ad)` kullanir.

GTK gerektirmez; yalnizca standart kutuphane.
"""
from __future__ import annotations

import os
import re

# Yalnizca root'un yazabildigi dizinler. /usr/local BILEREK yok: Debian'da /usr/local 'staff' grubuna
# yazilabilir; CarotOS'un kendi yetkili betikleri (/usr/local/sbin/carotos-*) tam yoluyla cagrilir.
SISTEM_DIZINLERI = ("/usr/sbin", "/usr/bin", "/sbin", "/bin")
# pkexec/sudo ile calisan komutlara verilecek ortam: sabit PATH, ceviriden bagimsiz cikti
SISTEM_PATH = os.pathsep.join(SISTEM_DIZINLERI)
_PROGRAM_ADI = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}\Z")


def sistem_yolu(ad, dizinler=SISTEM_DIZINLERI):
    """Program adinin sistem dizinlerindeki tam yolunu doner; yoksa None.

    `ad` duz bir program adi olmalidir (yol ayirici, bosluk, '-' ile baslayan ad kabul edilmez);
    aksi halde None. PATH ortam degiskenine HIC bakilmaz."""
    if not isinstance(ad, str) or not _PROGRAM_ADI.match(ad):
        return None
    for dizin in dizinler:
        yol = os.path.join(dizin, ad)
        if os.path.isfile(yol) and os.access(yol, os.X_OK):
            return yol
    return None


def temiz_ortam(ek=None):
    """Alt surec icin ortam: PATH yalnizca sistem dizinleri, cikti dili sabit (LC_ALL=C).

    Komut ciktisini ayristiran her cagri bunu kullanmalidir: sistem Turkce yerelde calisir ve
    cevrilmis cikti ('active' yerine 'etkin' gibi) ayristirmayi sessizce bozar."""
    ortam = dict(os.environ)
    ortam.update({"PATH": SISTEM_PATH, "LC_ALL": "C", "LANGUAGE": "C"})
    if ek:
        ortam.update(ek)
    return ortam
