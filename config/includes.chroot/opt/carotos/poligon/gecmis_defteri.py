"""
CarotOS Poligon -- bireysel mod kalıcı geçmiş defteri.

SADECE bireysel modda kullanılır. Sınıf modunda ilerleme zaten
öğretmen sunucusuna gidiyor (bkz. ogretmen_sunucu.py::OdaDurumu) ve
o oda ders bitince kapanıyor -- bu bilinçli bir tasarım, kalıcı
olması gerekmiyor. Bireysel modda ise öğretmen sunucusu HİÇ yok, bu
yüzden ilerleme aynı oturum içinde bile hiçbir yere kaydedilmiyordu
(devir belgesindeki açık soruydu). Bu modül, öğrencinin KENDİ ev
dizinine basit bir JSON dosyası olarak yazıyor.

Dosya: ~/.local/share/carotos-poligon/gecmis.json -- düz bir liste,
her eleman bir "olay" (görev başladı/tamamlandı/yanlış denendi).
Veritabanı YOK, şifreleme YOK -- tek kullanıcılı yerel bir dosya,
CarotOS'taki diğer kullanıcı-ayarları dosyalarıyla aynı basitlikte.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

GECMIS_DOSYASI = Path.home() / ".local" / "share" / "carotos-poligon" / "gecmis.json"


def _ham_oku() -> list:
    if not GECMIS_DOSYASI.exists():
        return []
    try:
        veri = json.loads(GECMIS_DOSYASI.read_text(encoding="utf-8"))
        return veri if isinstance(veri, list) else []
    except (OSError, json.JSONDecodeError):
        # Bozuk/okunamayan dosya pratiği ENGELLEMEMELİ -- boş geçmişle
        # devam et, bir dahaki yazımda dosya normal şekilde üzerine yazılır.
        return []


def kaydet(gorev_id: str, arac: str, durum: str, sure_sn: float = 0, puan: int = 0) -> None:
    """Bir olayı geçmiş defterine ekler. Dizin yoksa oluşturur.
    Yazma hatası (disk dolu, izin sorunu vb.) SESSİZCE yutulur --
    geçmiş kaydı pratiğe hiçbir zaman engel olmamalı, sadece 'olursa
    iyi olur' bir özellik."""
    try:
        GECMIS_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
        gecmis = _ham_oku()
        gecmis.append({
            "gorev_id": gorev_id,
            "arac": arac,
            "durum": durum,
            "sure_sn": sure_sn,
            "puan": puan,
            "zaman": time.time(),
        })
        GECMIS_DOSYASI.write_text(
            json.dumps(gecmis, ensure_ascii=False, indent=2), encoding="utf-8",
        )
    except OSError:
        pass


def tumunu_oku() -> list:
    """Tüm geçmişi, en eskiden en yeniye, döner."""
    return _ham_oku()


def ozet() -> dict:
    """Bireysel modun 'başla' ekranında gösterilecek basit özet:
    toplam tamamlanan görev sayısı ve toplam puan."""
    gecmis = _ham_oku()
    tamamlanan = [g for g in gecmis if g.get("durum") == "tamamlandi"]
    return {
        "toplam_tamamlanan": len(tamamlanan),
        "toplam_puan": sum(g.get("puan", 0) for g in tamamlanan),
    }
