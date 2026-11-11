#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reprepro'nun uretemedigi Acquire-By-Hash'i ekler (imzadan ONCE calistirilir).

Kullanim: by_hash.py <depo-dizini>

- dists/stable/Release icindeki SHA256 listesinde adi gecen her dosyayi
  <dizin>/by-hash/SHA256/<ozet> yoluna kopyalar,
- Release basligina "Acquire-By-Hash: yes" ekler (SHA256 listesinin hesabi degismez; imza sonradan atilir).
Eski by-hash dosyalari SILINMEZ: yukleme sirasinda yarisan istemciler eski ozetle istek atabilir.
"""
import os
import re
import shutil
import sys

SURUM = "stable"


def calistir(depo):
    kok = os.path.join(depo, "dists", SURUM)
    yol = os.path.join(kok, "Release")
    with open(yol, "r", encoding="utf-8", newline="") as f:
        metin = f.read()
    satirlar = metin.split("\n")
    dosyalar, bolum = [], None
    for s in satirlar:
        if re.match(r"^[A-Za-z0-9-]+:", s):
            bolum = s.split(":")[0]
        elif bolum == "SHA256" and s.startswith(" "):
            parca = s.split()
            if len(parca) == 3:
                dosyalar.append((parca[0], parca[2]))
    if not dosyalar:
        raise SystemExit("Release icinde SHA256 listesi yok: " + yol)
    for ozet, goreli in dosyalar:
        kaynak = os.path.join(kok, goreli)
        if not os.path.isfile(kaynak):
            continue
        hedef_dizin = os.path.join(os.path.dirname(kaynak), "by-hash", "SHA256")
        os.makedirs(hedef_dizin, exist_ok=True)
        hedef = os.path.join(hedef_dizin, ozet)
        if not os.path.exists(hedef):
            shutil.copyfile(kaynak, hedef)
    if not any(s.startswith("Acquire-By-Hash:") for s in satirlar):
        ilk = next(i for i, s in enumerate(satirlar) if s.startswith("MD5Sum:") or s.startswith("SHA1:")
                   or s.startswith("SHA256:"))
        satirlar.insert(ilk, "Acquire-By-Hash: yes")
        with open(yol, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(satirlar))
    return len(dosyalar)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Kullanim: by_hash.py <depo-dizini>")
    print("by-hash: %d dosya islendi" % calistir(sys.argv[1]))
