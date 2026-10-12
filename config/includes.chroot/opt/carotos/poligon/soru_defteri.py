"""
CarotOS Poligon -- kaydedilmis "Soru Olustur" sorulari defteri.

Ogretmen "Soru Olustur" ekraninda bir soruyu kaydettiginde burada,
KENDI makinesinde saklanir:

    ~/.local/share/carotos-poligon/sorular/<id>.json
    = {"id","gorev_id","parametreler","ad","olusturma"}

'parametreler' alani, ogrenciye aynen gonderilen servis parametreleridir
(orn. {"gizli_port_araligi":[20000,20999],"gurultu_sayisi":5}); yani
kaydedilmis bir soru tekrar gonderildiginde makine cevabi yine bu
parametrelere gore uretilir.

GTK'dan BAGIMSIZ: butun mantik burada; arayuz (ogretmen_uygulama.py)
yalnizca bu fonksiyonlari cagirir, boylece GTK'siz test edilebilir.
"""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path

DIZIN = Path.home() / ".local" / "share" / "carotos-poligon" / "sorular"


def _dizini_hazirla() -> None:
    DIZIN.mkdir(parents=True, exist_ok=True)


def _id_uret() -> str:
    _dizini_hazirla()
    while True:
        yeni = secrets.token_hex(4)  # 8 hex karakter
        if not (DIZIN / f"{yeni}.json").exists():
            return yeni


def kaydet(gorev_id: str, parametreler: dict, ad: str = "") -> dict:
    """Yeni bir kaydedilmis soru olusturup diske yazar. Donen sozluk kaydin
    kendisidir."""
    _dizini_hazirla()
    kayit = {
        "id": _id_uret(),
        "gorev_id": gorev_id,
        "parametreler": dict(parametreler),
        "ad": (ad or "").strip(),
        "olusturma": time.time(),
    }
    yol = DIZIN / f"{kayit['id']}.json"
    yol.write_text(
        json.dumps(kayit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return kayit


def listele() -> list[dict]:
    """Kayitli tum sorulari EN YENI en ustte olacak sekilde doner. Bozuk
    dosyalar sessizce atlanir."""
    if not DIZIN.exists():
        return []
    kayitlar = []
    for yol in DIZIN.glob("*.json"):
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(veri, dict) and veri.get("gorev_id") and veri.get("id"):
            kayitlar.append(veri)
    kayitlar.sort(key=lambda k: k.get("olusturma", 0), reverse=True)
    return kayitlar


def oku(soru_id: str) -> dict | None:
    yol = DIZIN / f"{soru_id}.json"
    if not yol.exists():
        return None
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def sil(soru_id: str) -> bool:
    """Kaydi siler. Silindiyse True, dosya yoksa False."""
    yol = DIZIN / f"{soru_id}.json"
    try:
        yol.unlink()
        return True
    except FileNotFoundError:
        return False
