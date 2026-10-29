"""
CarotOS Poligon -- ortak gorunum ayari (ogrenci ve ogretmen uygulamalari).

* Koyu/acik gorunum secimi ~/.config/carotos-poligon/ayar.json icinde saklanir.
* Poligon'a ozgu ek CSS (ortak/tema.py'nin ustune, yalnizca bu uygulamalarin
  kullandigi siniflar) burada tek yerde tutulur; renkler her zaman etkin
  paletten (tema.AKTIF) gelir, elle renk yazilmaz.

Bu dosya GTK'yi kendisi yuklemez; tema yalnizca poligon_css() icinde kullanilir.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

VURGU = "poligon"          # ortak/tema.py: VURGULAR anahtari


def _ayar_dosyasi() -> Path:
    taban = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")
    return Path(taban) / "carotos-poligon" / "ayar.json"


def _oku() -> dict:
    try:
        veri = json.loads(_ayar_dosyasi().read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def gorunum_oku() -> str:
    """'dark' (varsayilan) ya da 'light'."""
    return "light" if _oku().get("gorunum") == "light" else "dark"


def gorunum_yaz(gorunum: str) -> None:
    """Sessizce basarisiz olur: ayar yazilamazsa uygulama yine calisir."""
    veri = _oku()
    veri["gorunum"] = "light" if gorunum == "light" else "dark"
    try:
        yol = _ayar_dosyasi()
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def logo_bul(rol: str) -> str | None:
    """rol: 'ogrenci' ya da 'ogretmen'. ISO'da /usr/share/..., depodan
    calistirilirsa includes.chroot/usr/share/... altindaki ikon."""
    ad = f"usr/share/icons/hicolor/256x256/apps/carotos-poligon-{rol}.png"
    adaylar = [Path("/") / ad]
    try:
        adaylar.append(Path(__file__).resolve().parents[3] / ad)
    except IndexError:
        pass
    for yol in adaylar:
        if yol.is_file():
            return str(yol)
    return None


def poligon_css(p: dict) -> str:
    """Ortak temada olmayan, yalnizca Poligon'un kullandigi siniflar."""
    import tema  # ortak/tema.py (cagiran uygulama yolu ekler)

    rgba = tema.rgba_metni
    return f"""
/* vurgu rengi acik bir ton (limon): uzerindeki yazi koyu olmali */
button.ana label, button.suggested-action label, button.secim:checked label {{ color: #15210a; }}
check:checked, radio:checked {{ color: #15210a; }}
.kart.kart-dolgu {{ padding: 16px; }}
.kod-buyuk {{ color: {p['vurgu_yazi']}; font-size: 30px; font-weight: 800; letter-spacing: 3px; }}
.oda-seridi {{ padding: 14px 20px; }}
.durum-tamamlandi, .durum-dogru {{ color: {p['yesil']}; font-weight: 700; }}
.durum-basladi {{ color: {p['soluk']}; }}
.durum-deneme {{ color: {p['sari']}; font-weight: 700; }}
.durum-yanlis {{ color: {p['kirmizi']}; font-weight: 700; }}
.sohbet-ogretmen {{ background-color: {rgba(p['vurgu'], 0.14)}; border: 1px solid {rgba(p['vurgu'], 0.35)}; border-radius: 10px; padding: 6px 12px; }}
.sohbet-ogrenci {{ background-color: {p['vurgu_koyu']}; color: #ffffff; border-radius: 10px; padding: 6px 12px; }}
.poligon-liste {{ background-color: transparent; }}
.poligon-liste row {{ background-color: transparent; border-radius: 8px; padding: 2px; }}
.poligon-liste row:hover {{ background-color: {rgba(p['kart2'], 0.7)}; }}
.poligon-liste row:selected, .poligon-liste row:selected:hover {{ background-color: {p['vurgu_zemin']}; }}
.poligon-liste row:selected label {{ color: {p['yazi']}; }}
.bilgi-dugme {{ min-width: 22px; min-height: 22px; padding: 0; border-radius: 11px; border: 1px solid {p['cizgi']}; background-image: none; background-color: transparent; color: {p['soluk']}; font-weight: 800; font-size: 85%; }}
.bilgi-dugme:hover {{ border-color: {p['vurgu']}; color: {p['vurgu_yazi']}; background-color: {rgba(p['vurgu'], 0.12)}; }}
.mono-yazi {{ font-family: monospace; color: {p['vurgu_yazi']}; }}
.bolum-ayrac {{ color: {p['silik']}; font-size: 85%; }}
"""
