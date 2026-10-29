# -*- coding: utf-8 -*-
"""
Filenor komut satiri -- arayuzle ayni motoru kullanir.

  filenor-cli durum                         kurulu araclar
  filenor-cli kur [ARAC...]                 eksik araclari kur (yonetici parolasi ister; --deneme yalniz plani gosterir)
  filenor-cli formatlar [uzanti]            hangi bicimden hangisine
  filenor-cli araclar                       PDF/OCR/gorsel araclari
  filenor-cli donustur -t HEDEF DOSYA...    bicim donustur
  filenor-cli arac ARAC DOSYA...            arac calistir (ornek: pdf_birlestir)

Cikti her zaman yeni dosyadir (var olan ezilmez). Varsayilan: kaynagin yanina.
Parola komut satirinda ps ile gorunur; bunun yerine FILENOR_PAROLA ortam
degiskenini kullanin. Cikis kodu: 0 hepsi tamam, 1 en az biri hatali, 2 kullanim, 130 iptal.
"""
import argparse
import json
import os
import signal
import sys
import threading

sys.dont_write_bytecode = True
BURASI = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, BURASI)

import filenor_araclar as A  # noqa: E402
import filenor_motor as M  # noqa: E402
import filenor_kurulum as K  # noqa: E402
from filenor_dil import FilenorHata, Iptal, hata_metni  # noqa: E402


import filenor_sistem as S  # noqa: E402

DIL = S.sistem_dili()


def yaz(*a, **k):
    print(*a, **k)


def secenek_olustur(args) -> M.Secenek:
    s = M.Secenek()
    for ad, alan in (("kalite", "kalite"), ("max_kenar", "max_kenar"), ("dpi", "dpi"), ("sayfalar", "sayfa_araligi"),
                     ("ocr_dil", "ocr_dil"), ("ocr_cikti", "ocr_cikti"), ("fps", "gif_fps"),
                     ("genislik", "gif_genislik"), ("derece", "derece"), ("parca", "parca"),
                     ("baslangic", "baslangic"), ("bitis", "bitis")):
        v = getattr(args, ad, None)
        if v is not None:
            setattr(s, alan, v)
    s.meta_temizle = bool(getattr(args, "meta_temizle", False))
    s.zip_yap = bool(getattr(args, "zip", False))
    s.parola = os.environ.get("FILENOR_PAROLA", "") or (getattr(args, "parola", None) or "")
    s.yeni_parola = os.environ.get("FILENOR_YENI_PAROLA", "") or (getattr(args, "yeni_parola", None) or "")
    return s


def ortak_secenekler(p):
    p.add_argument("-o", "--cikti", help="cikti klasoru (varsayilan: her dosyanin yani)")
    p.add_argument("--kalite", choices=M.KALITELER)
    p.add_argument("--max-kenar", dest="max_kenar", type=int, help="gorsel: en uzun kenar px; video: en buyuk yukseklik")
    p.add_argument("--meta-temizle", dest="meta_temizle", action="store_true", help="EXIF/GPS/ustveri sil")
    p.add_argument("--dpi", type=int)
    p.add_argument("--sayfalar", help="ornek: 1-3,5,8-")
    p.add_argument("--parola", help="PDF parolasi (tercihen FILENOR_PAROLA)")
    p.add_argument("--yeni-parola", dest="yeni_parola")
    p.add_argument("--ocr-dil", dest="ocr_dil")
    p.add_argument("--ocr-cikti", dest="ocr_cikti", choices=("txt", "pdf"))
    p.add_argument("--fps", type=int)
    p.add_argument("--genislik", type=int)
    p.add_argument("--derece", type=int, choices=(90, 180, 270))
    p.add_argument("--parca", type=int)
    p.add_argument("--baslangic", type=float)
    p.add_argument("--bitis", type=float)
    p.add_argument("--zip", action="store_true", help="sonuclari ZIP'le")
    p.add_argument("--json", action="store_true", help="makine okunur cikti")


def calistir_isler(isler, args, arac=False):
    sec = secenek_olustur(args)
    iptal = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: iptal.set())
    signal.signal(signal.SIGTERM, lambda *_: iptal.set())
    sinif = A.AracKosucu if arac else M.Kosucu
    bitti = threading.Event()
    tty = sys.stderr.isatty() and not args.json

    def is_cb(i, is_):
        if tty and is_.durum == "calisiyor":
            sys.stderr.write(f"\r[{i + 1}/{len(isler)}] {os.path.basename(is_.kaynak)}  %{is_.yuzde:3.0f}   ")
            sys.stderr.flush()

    k = sinif(isler, args.cikti, sec, is_cb=is_cb, bitti_cb=lambda _: bitti.set(), yanina=not args.cikti)
    k.iptal = iptal       # ayni olayi paylasir
    k.start()
    while not bitti.wait(0.2):
        pass
    if tty:
        sys.stderr.write("\r" + " " * 70 + "\r")
    sonuc = []
    kod = 0
    for i in isler:
        d = {"kaynak": i.kaynak, "durum": i.durum, "sonuc": i.sonuc}
        if i.hata:
            d["hata"] = {"kod": i.hata.kod, "metin": hata_metni(i.hata, DIL)}
            kod = max(kod, 1)
        if i.durum == "iptal":
            kod = 130
        sonuc.append(d)
    if k.zip_yolu:
        sonuc.append({"zip": k.zip_yolu})
    if args.json:
        yaz(json.dumps(sonuc, ensure_ascii=False, indent=2))
    else:
        for d in sonuc:
            if "zip" in d:
                yaz("ZIP:", d["zip"])
            elif d["durum"] == "tamam":
                for s in d["sonuc"]:
                    yaz("OK  ", s)
            elif d["durum"] == "iptal":
                yaz("IPTAL", d["kaynak"])
            else:
                yaz("HATA", d["kaynak"], "-", d.get("hata", {}).get("metin", "?"), file=sys.stderr)
    return kod


def komut_durum(args):
    d = M.araclar_durumu()
    if args.json:
        yaz(json.dumps(d, indent=2))
        return 0
    from filenor_dil import ipucu_al
    for k, v in d.items():
        ip = "" if v else "   " + ipucu_al(k, DIL)
        yaz(f"{'var ' if v else 'YOK '} {k}{ip}")
    return 0


def komut_kur(args):
    d = M.araclar_durumu()
    istek = args.araclar or K.temel_eksikler(d)
    bilinmeyen = [a for a in istek if a not in K.APT and a not in K.PIP and a not in K.KURULAMAZ]
    if bilinmeyen:
        yaz(("bilinmeyen arac: " if DIL == "tr" else "unknown tool: ") + ", ".join(bilinmeyen), file=sys.stderr)
        return 2
    pl = K.plan(istek, d)
    if pl.elle:
        yaz(("otomatik kurulamaz: " if DIL == "tr" else "cannot be installed automatically: ") + ", ".join(pl.elle))
    if pl.bos:
        yaz("kurulacak bir sey yok" if DIL == "tr" else "nothing to install")
        return 0 if not pl.elle else 1
    yaz(("kurulacak: " if DIL == "tr" else "to install: ") + " ".join(pl.paketler))
    if args.deneme:
        return 0
    yok = K.kur(pl, lambda s: yaz(s))
    K.ortami_yenile()
    kalan = [k for k in pl.anahtarlar if k not in pl.elle and not M.araclar_durumu().get(k)]
    if yok or kalan:
        yaz(("hala eksik: " if DIL == "tr" else "still missing: ") + ", ".join(kalan or yok), file=sys.stderr)
        return 1
    yaz("tamam" if DIL == "tr" else "done")
    return 0


def komut_formatlar(args):
    if args.uzanti:
        e = M.norm(args.uzanti)
        h = M.hedefler(e)
        if not h:
            yaz("desteklenmiyor" if DIL == "tr" else "unsupported", file=sys.stderr)
            return 2
        yaz(" ".join(h))
        return 0
    for e in M.kaynak_uzantilari():
        yaz(f"{e:6} -> {' '.join(M.hedefler(e))}")
    return 0


def komut_araclar(args):
    for k, t in A.ARACLAR.items():
        ek = A.arac_kullanilabilir(k)
        yaz(f"{k:15} {t['ad'][DIL]}{'  [eksik: ' + ', '.join(ek) + ']' if ek else ''}")
        yaz(f"{'':15} {t['ac'][DIL]}")
    return 0


def komut_donustur(args):
    isler = [M.Is(os.path.abspath(f), M.norm(args.hedef)) for f in args.dosyalar]
    return calistir_isler(isler, args)


def komut_arac(args):
    if args.arac not in A.ARACLAR:
        yaz(("bilinmeyen arac: " if DIL == "tr" else "unknown tool: ") + args.arac, file=sys.stderr)
        return 2
    t = A.ARACLAR[args.arac]
    dosyalar = [os.path.abspath(f) for f in args.dosyalar]
    if args.arac == "pdf_birlestir":
        i = M.Is(dosyalar[0], args.arac)
        i.dosyalar = dosyalar
        isler = [i]
    else:
        isler = [M.Is(f, args.arac) for f in dosyalar]
    if len(dosyalar) < t["min"]:
        yaz(hata_metni(FilenorHata("en_az_bir", n=t["min"]), DIL), file=sys.stderr)
        return 2
    return calistir_isler(isler, args, arac=True)


def main(argv=None):
    for akis in (sys.stdout, sys.stderr):        # Windows konsolu: Turkce karakter hata vermesin
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    ap = argparse.ArgumentParser(prog="filenor-cli", description="Filenor: dosya donusturucu / arac kutusu")
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("durum", help="kurulu araclari goster")
    p.add_argument("--json", action="store_true")
    p.set_defaults(f=komut_durum)
    p = alt.add_parser("kur", help="eksik araclari kur")
    p.add_argument("araclar", nargs="*", help="arac anahtari (bos: LibreOffice/Ghostscript disindaki eksikler)")
    p.add_argument("--deneme", action="store_true", help="yalniz ne kurulacagini goster")
    p.set_defaults(f=komut_kur)
    p = alt.add_parser("formatlar", help="bicim donusum tablosu")
    p.add_argument("uzanti", nargs="?")
    p.set_defaults(f=komut_formatlar)
    p = alt.add_parser("araclar", help="arac listesi")
    p.set_defaults(f=komut_araclar)
    p = alt.add_parser("donustur", help="bicim donustur")
    p.add_argument("-t", "--hedef", required=True, help="hedef bicim (png, pdf, mp3 ...)")
    p.add_argument("dosyalar", nargs="+")
    ortak_secenekler(p)
    p.set_defaults(f=komut_donustur)
    p = alt.add_parser("arac", help="arac calistir")
    p.add_argument("arac", help="arac kimligi (filenor-cli araclar)")
    p.add_argument("dosyalar", nargs="+")
    ortak_secenekler(p)
    p.set_defaults(f=komut_arac)
    args = ap.parse_args(argv)
    try:
        return args.f(args)
    except (FilenorHata, Iptal) as h:
        yaz(hata_metni(h, DIL) if isinstance(h, FilenorHata) else "iptal", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
