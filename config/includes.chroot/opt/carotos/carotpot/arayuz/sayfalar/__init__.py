# -*- coding: utf-8 -*-
"""CarotPot sayfalari. Her menu ogesi ayri bir modulde bir Sayfa alt sinifidir.

Sayfa yasam dongusu:
  kur()           parcalari olusturur (ilk gosterimde ve dil/tema degisince)
  guncelle()      durumu p (Pencere) uzerinden okuyup ekrani tazeler
  hazirla(**kw)   baska bir sayfadan gelinirken secim aktarir (or. ip)
  mesgul_degisti()  yetkili bir islem basladiginda/bittiginde
"""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from arayuz.metinler import M  # noqa: E402


# Tuzaklarin grafik ve simge renkleri (tema paletindeki adlar)
RENK = {"ssh": "vurgu", "http": "turuncu", "telnet": "camgobegi", "ftp": "sari",
        "vnc": "pembe", "rdp": "mavi", "mysql": "limon", "redis": "kirmizi"}


def tiklanir(icerik, tik):
    """Bir parcayi tiklanabilir satir yapar (uzerine gelince vurgulanir)."""
    from gi.repository import Gdk
    kutu = Gtk.EventBox()
    kutu.get_style_context().add_class("tiklanir")
    kutu.add(icerik)
    kutu.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
    kutu.connect("button-press-event", lambda *_: tik())
    kutu.connect("realize", lambda w: w.get_window().set_cursor(
        Gdk.Cursor.new_from_name(w.get_display(), "pointer")))
    return kutu


class Sayfa:
    ANAHTAR = ""

    def __init__(self, p):
        self.p = p
        self.kok = None

    def t(self, _anahtar, **kw):
        return self.p.t(_anahtar, **kw)

    def baslik(self):
        a = self.ANAHTAR
        baslik = f"{a}_baslik" if f"{a}_baslik" in M else a
        return self.t(baslik), self.t(f"{a}_alt")

    def kur(self):
        return Gtk.Box()

    def guncelle(self):
        pass

    def hazirla(self, **kw):
        pass

    def mesgul_degisti(self):
        pass

    @staticmethod
    def bosken_gizle(kutu):
        """Icerigi yoksa kutuyu gizler (bos kutu aralik birakmasin).
        Kutu set_no_show_all(True) ile olusturulmus olmalidir."""
        cocuklar = kutu.get_children()
        for c in cocuklar:
            c.show_all()
        kutu.set_visible(bool(cocuklar))

    @staticmethod
    def temizle(kutu):
        for c in kutu.get_children():
            kutu.remove(c)
            c.destroy()


from arayuz.sayfalar.pano import PanoSayfasi  # noqa: E402
from arayuz.sayfalar.saldirgan import SaldirganSayfasi  # noqa: E402
from arayuz.sayfalar.tuzak import TuzakSayfasi  # noqa: E402
from arayuz.sayfalar.kanarya_dosya import KanaryaSayfasi  # noqa: E402
from arayuz.sayfalar.engel import EngelSayfasi  # noqa: E402
from arayuz.sayfalar.rapor import RaporSayfasi  # noqa: E402
from arayuz.sayfalar.harita import HaritaSayfasi  # noqa: E402
from arayuz.sayfalar.ayar import AyarSayfasi  # noqa: E402

SAYFALAR = [PanoSayfasi, SaldirganSayfasi, TuzakSayfasi, KanaryaSayfasi, EngelSayfasi,
            RaporSayfasi, HaritaSayfasi, AyarSayfasi]
