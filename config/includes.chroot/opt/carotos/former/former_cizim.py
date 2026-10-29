# -*- coding: utf-8 -*-
"""
Former -- sahne cizimi (Cairo).

former_zaman.Cizelge.durum(t) ciktisini ekrana cizer: uygulamanin sade bir
kopyasi, sahte fare imleci, tiklama dalgasi, balon.  Renkler tema.palet()
sozlugunden gelir; sahne kendi vurgusunu (guvenlik / carotpot / carotene ...)
kullanir.
"""

from __future__ import annotations

import math

import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402

import tema  # noqa: E402
from former_zaman import metin_al, tik_noktasi  # noqa: E402

PENCERE_BASLIK_Y = 26


def _renk(cr, p, ad, alfa=1.0):
    """ad: palet anahtari ya da '#rrggbb'."""
    h = p.get(ad, ad) if not str(ad).startswith("#") else ad
    if isinstance(h, str) and h.startswith("rgba"):
        sayilar = [float(x) for x in h[5:-1].split(",")]
        cr.set_source_rgba(sayilar[0] / 255, sayilar[1] / 255, sayilar[2] / 255, sayilar[3] * alfa)
        return
    r, g, b = tema._hex(h)
    cr.set_source_rgba(r / 255, g / 255, b / 255, alfa)


def _duzen(cr, metin, boyut, kalin=False, mono=False, genislik=None, hiza="sol"):
    d = PangoCairo.create_layout(cr)
    ad = "Monospace" if mono else "Sans"
    d.set_font_description(Pango.FontDescription.from_string(f"{ad} {'Bold ' if kalin else ''}{boyut}"))
    d.set_text(str(metin), -1)
    if genislik:
        d.set_width(int(genislik * Pango.SCALE))
        d.set_wrap(Pango.WrapMode.WORD_CHAR)
    if hiza == "orta":
        d.set_alignment(Pango.Alignment.CENTER)
    elif hiza == "sag":
        d.set_alignment(Pango.Alignment.RIGHT)
    return d


def _yaz(cr, p, x, y, metin, boyut=9, renk="yazi", kalin=False, mono=False, genislik=None, hiza="sol",
         alfa=1.0, dikey="ust"):
    """(x, y) sol-ust kose. hiza='orta' icin x, kutunun sol kenari ve genislik verilmelidir.
    Yuksekligi dondurur."""
    d = _duzen(cr, metin, boyut, kalin, mono, genislik, hiza)
    _m, mant = d.get_pixel_extents()
    if dikey == "orta":
        y = y - mant.height / 2.0
    cr.move_to(x, y)
    _renk(cr, p, renk, alfa)
    PangoCairo.show_layout(cr, d)
    return mant.height


def _olc(cr, metin, boyut, kalin=False, mono=False, genislik=None):
    d = _duzen(cr, metin, boyut, kalin, mono, genislik)
    _m, mant = d.get_pixel_extents()
    return mant.width, mant.height


def _kutu(cr, x, y, w, h, r, dolgu=None, cerceve=None, p=None, cerceve_kalinlik=1.0, alfa=1.0):
    tema.yuvarlak(cr, x, y, w, h, r)
    if dolgu:
        _renk(cr, p, dolgu, alfa)
        if cerceve:
            cr.fill_preserve()
        else:
            cr.fill()
    if cerceve:
        _renk(cr, p, cerceve, alfa)
        cr.set_line_width(cerceve_kalinlik)
        cr.stroke()
    if not dolgu and not cerceve:
        # yuvarlak() ile acilan yol fill/stroke ile tuketilmedi; sonraki
        # cizimlere (orn. bir sonraki fill()) sizmasin diye temizle.
        cr.new_path()


# ---------------------------------------------------------------------------
# Oge cizicileri
# ---------------------------------------------------------------------------
def _gorunur(o, durum):
    if o.get("sayfa") is not None:
        izin = o["sayfa"] if isinstance(o["sayfa"], (list, tuple)) else [o["sayfa"]]
        if durum["sayfa"] not in izin:
            return False
    bayrak = o.get("bayrak")
    if bayrak is not None:
        if bayrak.startswith("!"):
            if durum["bayraklar"].get(bayrak[1:]):
                return False
        elif not durum["bayraklar"].get(bayrak):
            return False
    return True


def _oge_durumu(o, durum):
    e = dict(o)
    e.update(durum["ogeler"].get(o["id"], {}))
    return e


def _simge(cr, p, ad, x, y, boyut, renk):
    cr.save()
    tema.AKTIF = p                # ikon_ciz renkleri tema.renk() ile okur
    tema.ikon_ciz(cr, ad, x, y, boyut, renk if str(renk).startswith("#") else renk)
    cr.restore()


def _ciz_oge(cr, p, o, e, durum, dil, t):
    tur = o["tur"]
    x, y, w, h = o["x"], o["y"], o["w"], o["h"]
    odakta = durum["odak"] == o["id"]
    if tur == "yan":
        cr.rectangle(x, y, w, h)
        _renk(cr, p, "yan")
        cr.fill()
        cr.move_to(x + w - 0.5, y)
        cr.line_to(x + w - 0.5, y + h)
        _renk(cr, p, "cizgi")
        cr.set_line_width(1)
        cr.stroke()
    elif tur == "menu":
        aktif = bool(e.get("aktif"))
        if aktif:
            _kutu(cr, x, y, w, h, 6, "vurgu_zemin", None, p)
        if o.get("simge"):
            _simge(cr, p, o["simge"], x + 8, y + (h - 12) / 2.0, 12, "vurgu_yazi" if aktif else "soluk")
        _yaz(cr, p, x + (26 if o.get("simge") else 10), y + h / 2.0, metin_al(e.get("metin"), dil),
             o.get("boyut", 8.5), "vurgu_yazi" if aktif else "soluk", kalin=aktif, dikey="orta",
             genislik=w - 34 if o.get("simge") else w - 14)
    elif tur == "metin":
        genislik = o["w"] if o.get("sar") else None
        _yaz(cr, p, x, y, metin_al(e.get("metin"), dil), o.get("boyut", 9), o.get("renk", "yazi"),
             kalin=o.get("kalin", False), mono=o.get("mono", False), genislik=genislik,
             hiza=o.get("hiza", "sol"), dikey="orta" if o.get("dikey") == "orta" else "ust")
    elif tur == "kart":
        _kutu(cr, x, y, w, h, 8, "kart", "cizgi", p)
        if o.get("baslik"):
            _yaz(cr, p, x + 12, y + 9, metin_al(o["baslik"], dil), 8.5, "soluk", kalin=True)
    elif tur in ("alan", "dosya", "secim"):
        cerceve = "vurgu" if (odakta or e.get("liste")) else "cizgi"
        _kutu(cr, x, y, w, h, 6, "kart2", cerceve, p, 1.6 if cerceve == "vurgu" else 1.0)
        deger = e.get("deger", "")
        if tur == "secim" and not deger and o.get("secenekler"):
            deger = metin_al(o["secenekler"][0], dil)
        if tur == "dosya" and not deger:
            _simge(cr, p, "dosya", x + 8, y + (h - 12) / 2.0, 12, "soluk")
            _yaz(cr, p, x + 26, y + h / 2.0, metin_al(o.get("yer") or T_DOSYA, dil), 8.5, "silik", dikey="orta")
        elif tur == "dosya":
            _simge(cr, p, "dosya", x + 8, y + (h - 12) / 2.0, 12, "vurgu_yazi")
            _yaz(cr, p, x + 26, y + h / 2.0, deger, 8.5, "yazi", mono=True, dikey="orta", genislik=w - 34)
        elif deger:
            _yaz(cr, p, x + 9, y + h / 2.0, deger, 8.5, "yazi", mono=(tur != "secim"), dikey="orta",
                 genislik=w - 30)
            if odakta and tur == "alan" and int(t / 450) % 2 == 0:
                gw, _gh = _olc(cr, deger, 8.5, mono=True)
                cr.rectangle(x + 9 + gw + 1, y + 5, 1.2, h - 10)
                _renk(cr, p, "vurgu_yazi")
                cr.fill()
        else:
            if o.get("yer"):
                _yaz(cr, p, x + 9, y + h / 2.0, metin_al(o["yer"], dil), 8.5, "silik", dikey="orta")
            if odakta and tur == "alan" and int(t / 450) % 2 == 0:
                cr.rectangle(x + 9, y + 5, 1.2, h - 10)
                _renk(cr, p, "vurgu_yazi")
                cr.fill()
        if tur == "secim":
            cx, cy = x + w - 14, y + h / 2.0
            cr.move_to(cx - 4, cy - 2)
            cr.line_to(cx, cy + 2)
            cr.line_to(cx + 4, cy - 2)
            _renk(cr, p, "soluk")
            cr.set_line_width(1.5)
            cr.stroke()
    elif tur == "dugme":
        birincil = o.get("birincil", False)
        basili = e.get("basili")
        pasif = e.get("pasif")
        dolgu = "vurgu" if birincil else "kart2"
        _kutu(cr, x, y + (1 if basili else 0), w, h, 6, dolgu, None if birincil else "cizgi", p,
              alfa=0.45 if pasif else 1.0)
        if basili:
            _kutu(cr, x, y + 1, w, h, 6, "#000000", None, p, alfa=0.16)
        _yaz(cr, p, x, y + h / 2.0 + (1 if basili else 0), metin_al(e.get("metin"), dil), o.get("boyut", 8.5),
             "ana_yazi" if birincil else "yazi", kalin=birincil, hiza="orta", genislik=w, dikey="orta",
             alfa=0.55 if pasif else 1.0)
    elif tur == "anahtar":
        acik = bool(e.get("aktif"))
        _kutu(cr, x, y, w, h, h / 2.0, "vurgu" if acik else "kart2", "cizgi", p)
        r = h / 2.0 - 3
        cx = x + w - h / 2.0 if acik else x + h / 2.0
        cr.arc(cx, y + h / 2.0, r, 0, 2 * math.pi)
        _renk(cr, p, "ana_yazi" if acik else "soluk")
        cr.fill()
    elif tur == "rozet":
        renk = e.get("renk", o.get("renk", "gri"))
        r, g, b = tema._hex(p.get(renk, renk))
        cr.save()
        _kutu(cr, x, y, w, h, h / 2.0, None, None, p)
        cr.set_source_rgba(r / 255, g / 255, b / 255, 0.18)
        cr.fill()
        cr.restore()
        cr.arc(x + 9, y + h / 2.0, 3, 0, 2 * math.pi)
        _renk(cr, p, renk)
        cr.fill()
        _yaz(cr, p, x + 17, y + h / 2.0, metin_al(e.get("metin"), dil), 8, renk, kalin=True, dikey="orta")
    elif tur == "kpi":
        _kutu(cr, x, y, w, h, 8, "kart", "cizgi", p)
        _yaz(cr, p, x + 12, y + 8, metin_al(o.get("ad"), dil), 7.5, "soluk", genislik=w - 20)
        _yaz(cr, p, x + 12, y + h - 30, metin_al(e.get("metin"), dil), 17, o.get("renk", "yazi"), kalin=True)
    elif tur == "satir":
        _kutu(cr, x, y, w, h, 6, "kart2" if e.get("vurgulu") else None, None, p)
        ren = e.get("renk", o.get("renk", "soluk"))
        cr.arc(x + 10, y + h / 2.0, 3.2, 0, 2 * math.pi)
        _renk(cr, p, ren)
        cr.fill()
        _yaz(cr, p, x + 22, y + h / 2.0, metin_al(e.get("metin"), dil), 8.2, "yazi", dikey="orta", genislik=w - 30)
    elif tur == "cikti":
        _kutu(cr, x, y, w, h, 6, "#0d0f14" if p["gorunum"] == "dark" else "#1c2030", "cizgi", p)
        satirlar = [metin_al(s, dil) for s in
                    list(o.get("satirlar", [])) + list(durum["cikti"].get(o["id"], []))]
        sigar = max(1, int((h - 12) / 13.0))
        gorunen = satirlar[-sigar:]
        for i, s in enumerate(gorunen):
            ren = "#d7dae6"
            if s.startswith("[!]") or "ERROR" in s:
                ren = "#ff8a80"
            elif s.startswith("$"):
                ren = "#ffd37a"
            elif s.startswith("[") and s.endswith("]"):
                ren = "#8d93a8"
            elif "open" in s or "AÇIK" in s or "FOUND" in s or "found" in s or "valid" in s:
                ren = "#8fe39a"
            _yaz(cr, p, x + 8, y + 6 + i * 13, s, 7.6, ren, mono=True)
    elif tur == "ilerleme":
        _kutu(cr, x, y, w, h, h / 2.0, "kart2", "cizgi", p)
        oran = max(0.0, min(1.0, e.get("ilerleme", 0.0)))
        if oran > 0:
            _kutu(cr, x, y, max(h, w * oran), h, h / 2.0, "vurgu", None, p)
    elif tur == "karo":
        aktif = bool(e.get("aktif"))
        _kutu(cr, x, y, w, h, 10, "kart", "vurgu" if aktif else "cizgi", p, 1.8 if aktif else 1.0)
        if aktif:
            _kutu(cr, x, y, w, h, 10, "vurgu_zemin", None, p)
        _simge(cr, p, o.get("simge", "kalkan"), x + w / 2.0 - 11, y + 12, 22, "vurgu_yazi" if aktif else "soluk")
        _yaz(cr, p, x, y + 42, metin_al(o.get("metin"), dil), 8.5, "yazi", kalin=True, hiza="orta", genislik=w)
        _yaz(cr, p, x + 4, y + 57, metin_al(o.get("alt"), dil), 7.2, "soluk", hiza="orta", genislik=w - 8)
    elif tur == "cizgi":
        cr.move_to(x, y + 0.5)
        cr.line_to(x + w, y + 0.5)
        _renk(cr, p, "cizgi")
        cr.set_line_width(1)
        cr.stroke()
    elif tur == "perde":
        cr.rectangle(o["x"], o["y"], o["w"], o["h"])
        cr.set_source_rgba(0, 0, 0, 0.5)
        cr.fill()
    elif tur == "diyalog":
        _kutu(cr, x + 2, y + 4, w, h, 10, "#000000", None, p, alfa=0.3)
        _kutu(cr, x, y, w, h, 10, "kart", "cizgi", p)
        _yaz(cr, p, x + 16, y + 14, metin_al(o.get("baslik"), dil), 10, "yazi", kalin=True, genislik=w - 32)


T_DOSYA = {"tr": "Dosya seç", "en": "Choose file"}


# ---------------------------------------------------------------------------
# Imlec, balon
# ---------------------------------------------------------------------------
def _imlec(cr, x, y):
    cr.save()
    cr.translate(x, y)
    cr.move_to(0, 0)
    cr.line_to(0, 17)
    cr.line_to(4.6, 13.2)
    cr.line_to(7.6, 20)
    cr.line_to(10.2, 18.9)
    cr.line_to(7.3, 12.2)
    cr.line_to(13, 12)
    cr.close_path()
    cr.set_source_rgba(0, 0, 0, 0.28)
    cr.save()
    cr.translate(1.3, 1.8)
    cr.append_path(cr.copy_path())
    cr.fill()
    cr.restore()
    cr.set_source_rgba(1, 1, 1, 1)
    cr.fill_preserve()
    cr.set_source_rgba(0.08, 0.09, 0.12, 1)
    cr.set_line_width(1.2)
    cr.stroke()
    cr.restore()


def _balon(cr, p, W, H, sahne, durum, dil, t):
    b = durum["balon"]
    if not b:
        return
    hedef = next((o for o in sahne["ogeler"] if o["id"] == b["hedef"]), None)
    if hedef is None:
        return
    alfa = b["alfa"]
    # hedefi cevreleyen nabiz halkasi
    nabiz = 0.5 + 0.5 * math.sin(t / 220.0)
    _kutu(cr, hedef["x"] - 4, hedef["y"] - 4, hedef["w"] + 8, hedef["h"] + 8, 8, None, "vurgu", p,
          1.6 + nabiz * 1.2, alfa * (0.55 + 0.45 * nabiz))

    gen = 236
    bw, bh = _olc(cr, b["metin"], 8.6, genislik=gen - 28)
    bt_w, bt_h = _olc(cr, b["baslik"], 9, kalin=True, genislik=gen - 52)
    kutu_h = 14 + max(bt_h, 20) + 6 + bh + 14
    kutu_w = gen
    cx, cy = hedef["x"] + hedef["w"] / 2.0, hedef["y"] + hedef["h"] / 2.0
    secenekler = {
        "sag": (hedef["x"] + hedef["w"] + 14, cy - kutu_h / 2.0),
        "sol": (hedef["x"] - kutu_w - 14, cy - kutu_h / 2.0),
        "alt": (cx - kutu_w / 2.0, hedef["y"] + hedef["h"] + 14),
        "ust": (cx - kutu_w / 2.0, hedef["y"] - kutu_h - 14),
    }
    sira = [b["yon"]] if b["yon"] in secenekler else []
    sira += [y for y in ("sag", "sol", "alt", "ust") if y not in sira]
    secilen = None
    for yon in sira:
        bx, by = secenekler[yon]
        if bx >= 6 and by >= PENCERE_BASLIK_Y + 4 and bx + kutu_w <= W - 6 and by + kutu_h <= H - 6:
            secilen = yon
            break
    if secilen is None:
        secilen = sira[0]
    bx, by = secenekler[secilen]
    bx = max(6, min(W - kutu_w - 6, bx))
    by = max(PENCERE_BASLIK_Y + 4, min(H - kutu_h - 6, by))

    cr.push_group()
    # golge
    _kutu(cr, bx + 2, by + 4, kutu_w, kutu_h, 10, "#000000", None, p, alfa=0.28)
    _kutu(cr, bx, by, kutu_w, kutu_h, 10, "kart2", "vurgu", p, 1.6)
    # ok
    cr.save()
    if secilen == "sag":
        ax, ay = bx, min(max(cy, by + 18), by + kutu_h - 18)
        pts = [(ax + 0.8, ay - 8), (ax - 8, ay), (ax + 0.8, ay + 8)]
    elif secilen == "sol":
        ax, ay = bx + kutu_w, min(max(cy, by + 18), by + kutu_h - 18)
        pts = [(ax - 0.8, ay - 8), (ax + 8, ay), (ax - 0.8, ay + 8)]
    elif secilen == "alt":
        ax, ay = min(max(cx, bx + 22), bx + kutu_w - 22), by
        pts = [(ax - 8, ay + 0.8), (ax, ay - 8), (ax + 8, ay + 0.8)]
    else:
        ax, ay = min(max(cx, bx + 22), bx + kutu_w - 22), by + kutu_h
        pts = [(ax - 8, ay - 0.8), (ax, ay + 8), (ax + 8, ay - 0.8)]
    cr.move_to(*pts[0])
    cr.line_to(*pts[1])
    cr.line_to(*pts[2])
    cr.close_path()
    _renk(cr, p, "kart2")
    cr.fill_preserve()
    _renk(cr, p, "vurgu")
    cr.set_line_width(1.6)
    cr.stroke()
    # ok tabaninin cercevesini ortada sil
    cr.restore()
    _kutu(cr, bx + 1, by + 1, kutu_w - 2, kutu_h - 2, 9, "kart2", None, p)
    # numara rozeti
    cr.arc(bx + 20, by + 14 + 10, 10, 0, 2 * math.pi)
    _renk(cr, p, "vurgu")
    cr.fill()
    _yaz(cr, p, bx + 10, by + 14 + 10, str(b["no"]), 9, "ana_yazi", kalin=True, hiza="orta", genislik=20,
         dikey="orta")
    _yaz(cr, p, bx + 38, by + 14 + max(0, (20 - bt_h) / 2.0), b["baslik"], 9, "vurgu_yazi", kalin=True,
         genislik=gen - 52)
    _yaz(cr, p, bx + 14, by + 14 + max(bt_h, 20) + 6, b["metin"], 8.6, "yazi", genislik=gen - 28)
    cr.pop_group_to_source()
    cr.paint_with_alpha(alfa)


# ---------------------------------------------------------------------------
# Ana islev
# ---------------------------------------------------------------------------
def sahne_ciz(cr, w, h, sahne, durum, dil, p, t=None):
    """Sahneyi w x h alana, oran korunarak ortalayip cizer."""
    W, H = sahne["genislik"], sahne["yukseklik"]
    t = durum["t"] if t is None else t
    olcek = min(w / float(W), h / float(H))
    cr.save()
    cr.translate((w - W * olcek) / 2.0, (h - H * olcek) / 2.0)
    cr.scale(olcek, olcek)

    # pencere govdesi
    _kutu(cr, 0, 0, W, H, 10, "zemin", "cizgi", p)
    cr.save()
    tema.yuvarlak(cr, 0, 0, W, H, 10)
    cr.clip()
    # baslik cubugu
    cr.rectangle(0, 0, W, PENCERE_BASLIK_Y)
    _renk(cr, p, "yan")
    cr.fill()
    for i, ren in enumerate(("kirmizi", "sari", "yesil")):
        cr.arc(14 + i * 15, PENCERE_BASLIK_Y / 2.0, 4.2, 0, 2 * math.pi)
        _renk(cr, p, ren, 0.85)
        cr.fill()
    _yaz(cr, p, 0, PENCERE_BASLIK_Y / 2.0, metin_al(sahne.get("baslik"), dil), 8.3, "soluk", hiza="orta",
         genislik=W, dikey="orta")
    cr.move_to(0, PENCERE_BASLIK_Y - 0.5)
    cr.line_to(W, PENCERE_BASLIK_Y - 0.5)
    _renk(cr, p, "cizgi")
    cr.set_line_width(1)
    cr.stroke()

    ustte = []                      # secim listeleri en ustte cizilir
    for o in sahne["ogeler"]:
        if not _gorunur(o, durum):
            continue
        e = _oge_durumu(o, durum)
        _ciz_oge(cr, p, o, e, durum, dil, t)
        if o["tur"] == "secim" and e.get("liste"):
            ustte.append((o, e))
    for o, e in ustte:
        sec = o.get("secenekler") or []
        satir_h = 22
        lh = satir_h * len(sec) + 8
        _kutu(cr, o["x"] + 1, o["y"] + o["h"] + 3, o["w"] - 2, lh + 3, 6, "#000000", None, p, alfa=0.22)
        _kutu(cr, o["x"], o["y"] + o["h"] + 1, o["w"], lh, 6, "kart", "vurgu", p, 1.2)
        for i, s in enumerate(sec):
            ry = o["y"] + o["h"] + 5 + i * satir_h
            gez = e.get("gezen")
            if gez == i or e.get("secili") == i:
                _kutu(cr, o["x"] + 4, ry, o["w"] - 8, satir_h - 2, 5, "vurgu_zemin", None, p)
            _yaz(cr, p, o["x"] + 12, ry + (satir_h - 2) / 2.0, metin_al(s, dil), 8.4,
                 "vurgu_yazi" if (gez == i or e.get("secili") == i) else "yazi", dikey="orta")

    _balon(cr, p, W, H, sahne, durum, dil, t)
    if durum["tik"]:
        tx, ty, tp = durum["tik"]
        cr.arc(tx, ty, 4 + 22 * tp, 0, 2 * math.pi)
        _renk(cr, p, "vurgu", 0.55 * (1 - tp))
        cr.set_line_width(2.2)
        cr.stroke()
    _imlec(cr, *durum["imlec"])
    cr.restore()
    cr.restore()
