"""
CarotOS Poligon -- sqlmap gorevi icin SQL enjeksiyonuna acik web servisi.

Kasitli zafiyet: /urun?id=<DEGER> parametresi dogrudan SQL sorgusuna
string olarak ekleniyor (parametrize sorgu KULLANILMIYOR -- bu tam
olarak ogretilmek istenen hata). Boolean-based blind enjeksiyona acik:
gecerli id -> urun bilgisi doner, gecersiz id -> "bulunamadi" doner.
Bu iki farkli yanit, sqlmap'in True/False ayrimini yapmasini saglar.

'gizli' adinda ayri bir tablo var, normal /urun sayfasindan hic
erisilmiyor -- ogrenci sqlmap ile bu tabloyu (UNION ya da blind ile)
disari cikarmayi ogreniyor. Bu, gercek dunyada saldirganlarin "gorunen"
tablonun disindaki verileri de cekebildigini gosteren klasik senaryo.

SADECE 127.0.0.1: guvenlik kurali burada da kod seviyesinde zorunlu.
"""

from __future__ import annotations

import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


class SahteWebServisi:
    def __init__(self, gizli_deger: str, port: int, bind_adres: str = "127.0.0.1"):
        if bind_adres != "127.0.0.1":
            raise ValueError(
                f"GUVENLIK IHLALI: bind_adres '{bind_adres}' -- sadece "
                "127.0.0.1 kabul edilir."
            )
        self.bind_adres = bind_adres
        self.port = port
        self.gizli_deger = gizli_deger
        self._sunucu: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._db_kilit = threading.Lock()
        self._db_yolu = f"file:carotos_poligon_sqlmap_{id(self)}?mode=memory&cache=shared"
        self._baglanti_tutucu = None  # in-memory + cache=shared için en az bir açık bağlantı gerekir

    def _db_kur(self):
        # cache=shared + uri=True: aynı isimli bellek-içi DB'yi farklı
        # thread'ler paylaşabilsin diye. Bağlantıyı kapatmıyoruz,
        # kapanırsa bellek-içi DB de silinir.
        self._baglanti_tutucu = sqlite3.connect(self._db_yolu, uri=True, check_same_thread=False)
        c = self._baglanti_tutucu.cursor()
        c.execute("CREATE TABLE urunler (id INTEGER PRIMARY KEY, ad TEXT, aciklama TEXT)")
        c.executemany("INSERT INTO urunler VALUES (?,?,?)", [
            (1, "Klavye", "Mekanik klavye"),
            (2, "Fare", "Kablosuz fare"),
            (3, "Monitor", "27 inc monitor"),
        ])
        c.execute("CREATE TABLE gizli (deger TEXT)")
        c.execute("INSERT INTO gizli VALUES (?)", (self.gizli_deger,))
        self._baglanti_tutucu.commit()

    def baslat(self) -> None:
        self._db_kur()
        gizli_deger = self.gizli_deger
        db_yolu = self._db_yolu
        db_kilit = self._db_kilit

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                ayristirilan = urlparse(self.path)
                if ayristirilan.path != "/urun":
                    self.send_response(404); self.end_headers(); return

                sorgu = parse_qs(ayristirilan.query)
                kullanici_id = sorgu.get("id", ["1"])[0]

                with db_kilit:
                    conn = sqlite3.connect(db_yolu, uri=True, check_same_thread=False)
                    try:
                        # KASITLI ZAFIYET: parametrize sorgu yerine string birlestirme
                        c = conn.cursor()
                        c.execute(f"SELECT ad, aciklama FROM urunler WHERE id = {kullanici_id}")
                        satir = c.fetchone()
                    except sqlite3.Error:
                        satir = None
                    finally:
                        conn.close()

                govde = (
                    f"<h1>{satir[0]}</h1><p>{satir[1]}</p>".encode("utf-8")
                    if satir else b"<p>Urun bulunamadi</p>"
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(govde)))
                self.end_headers()
                self.wfile.write(govde)

        self._sunucu = ThreadingHTTPServer((self.bind_adres, self.port), Handler)
        self._thread = threading.Thread(target=self._sunucu.serve_forever, daemon=True)
        self._thread.start()

    def durdur(self) -> None:
        if self._sunucu:
            self._sunucu.shutdown()
            self._sunucu = None
        if self._baglanti_tutucu:
            self._baglanti_tutucu.close()
            self._baglanti_tutucu = None
