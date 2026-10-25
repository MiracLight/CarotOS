# -*- coding: utf-8 -*-
"""
CarotOS ortak bekleme cubugu (GTK 3).

Suresi belirsiz isler icin tek yonde ilerleyen ince cubuk. Sistem Sagligi'nda
dogdu; CarotOS uygulamalari bunu ortak klasorden kullanir (karar D2).
Kullanim: cubuk = SweepBar("#87979B"); bir zamanlayicida cubuk.adim(sayac).
"""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, GLib, Gtk  # noqa: E402


class SweepBar(Gtk.Image):
    """Süresi belirsiz işlemler için tek yönde ilerleyen ince çubuk.

    Soldan sağa akan bir parça gösterir; sağ uca ulaşınca yeniden soldan
    başlar (ileri geri gitmez). Cairo gerektirmez: kareler GdkPixbuf ile
    önceden üretilir ve her adımda sırayla gösterilir."""

    WIDTH = 132
    HEIGHT = 5
    FRAMES = 44
    TAIL = 52
    _onbellek = {}

    @classmethod
    def kareler(cls, renk):
        if renk in cls._onbellek:
            return cls._onbellek[renk]
        r, g, b = (int(renk[i:i + 2], 16) for i in (1, 3, 5))
        w, h, n, kuyruk = cls.WIDTH, cls.HEIGHT, cls.FRAMES, cls.TAIL
        zemin = 0.22
        kareler = []
        for k in range(n):
            bas = k * (w + kuyruk) // n
            veri = bytearray()
            for y in range(h):
                for x in range(w):
                    mesafe = bas - x
                    if 0 <= mesafe <= kuyruk:
                        parca = (1.0 - mesafe / kuyruk) ** 1.6
                        if mesafe < 3:
                            parca *= (mesafe + 1) / 4.0
                    else:
                        parca = 0.0
                    alfa = max(zemin, parca)
                    if (x in (0, w - 1)) and (y in (0, h - 1)):
                        alfa = 0.0
                    veri += bytes((r, g, b, int(alfa * 255)))
            kareler.append(GdkPixbuf.Pixbuf.new_from_bytes(
                GLib.Bytes.new(bytes(veri)), GdkPixbuf.Colorspace.RGB,
                True, 8, w, h, w * 4))
        cls._onbellek[renk] = kareler
        return kareler

    def __init__(self, renk):
        super().__init__()
        self._kareler = self.kareler(renk)
        self.set_from_pixbuf(self._kareler[0])
        self.set_size_request(self.WIDTH, self.HEIGHT)
        self.set_valign(Gtk.Align.CENTER)
        self.set_no_show_all(True)

    def adim(self, sayac):
        self.set_from_pixbuf(self._kareler[sayac % len(self._kareler)])
