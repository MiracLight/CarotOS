"""
CarotOS Poligon -- "gizli sayfa" gorevi icin yerel sahte web sitesi.

Yalniz loopback'te dinler (ag_guvenlik kurali). Uc kesif seviyesi:

  robots : /robots.txt gizli dizini kendisi soyler.
  sozluk : robots.txt yalniz yem dizinler gosterir; gizli dizin, ogrenciye
           verilen sozluk dosyasiyla dizin taramasi yaparak bulunur.
  cerez  : sozluk gibi, ama gizli sayfa ana sayfanin verdigi cerez olmadan
           403 doner ve bayragi govdede degil 'X-Carot-Bayrak' basliginda verir.
"""

from __future__ import annotations

import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ag_guvenlik import loopback_adres_mi


class SahteSite:
    def __init__(self, bind_adres: str, port: int, gizli_dizin: str, bayrak: str,
                 kesif: str = "robots", yem_dizinler=("yedek", "eski", "test")):
        if not loopback_adres_mi(bind_adres):
            raise ValueError(f"SahteSite yalniz loopback'te calisir: {bind_adres!r}")
        if kesif not in ("robots", "sozluk", "cerez"):
            raise ValueError(f"gecersiz kesif: {kesif!r}")
        self.bind_adres = bind_adres
        self.port = port
        self.gizli_dizin = gizli_dizin
        self.bayrak = bayrak
        self.kesif = kesif
        self.yem_dizinler = tuple(yem_dizinler)
        self.cerez = secrets.token_hex(6)
        self._sunucu: ThreadingHTTPServer | None = None
        self._is_parcacigi: threading.Thread | None = None

    def _isleyici(self):
        site = self

        class Isleyici(BaseHTTPRequestHandler):
            server_version = "CarotSite/1.0"

            def log_message(self, *_a):  # sessiz
                pass

            def _yanit(self, kod, govde, tur="text/html; charset=utf-8", basliklar=()):
                veri = govde.encode("utf-8")
                self.send_response(kod)
                self.send_header("Content-Type", tur)
                self.send_header("Content-Length", str(len(veri)))
                for k, v in basliklar:
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(veri)

            def do_GET(self):  # noqa: N802
                yol = self.path.split("?", 1)[0]
                if yol == "/":
                    ek = []
                    if site.kesif == "cerez":
                        ek.append(("Set-Cookie", f"oturum={site.cerez}; Path=/"))
                    return self._yanit(
                        200, "<h1>CarotOS Demo Sitesi</h1><p>Hos geldiniz.</p>", basliklar=ek)
                if yol == "/robots.txt":
                    if site.kesif == "robots":
                        satirlar = [f"Disallow: /{d}/" for d in site.yem_dizinler]
                        satirlar.insert(len(satirlar) // 2, f"Disallow: /{site.gizli_dizin}/")
                    else:
                        satirlar = [f"Disallow: /{d}/" for d in site.yem_dizinler]
                    return self._yanit(200, "User-agent: *\n" + "\n".join(satirlar) + "\n",
                                       "text/plain; charset=utf-8")
                dizin = yol.strip("/")
                if dizin == site.gizli_dizin:
                    if site.kesif == "cerez":
                        if f"oturum={site.cerez}" not in (self.headers.get("Cookie") or ""):
                            return self._yanit(403, "<h1>403</h1><p>Oturum cerezi gerekli.</p>")
                        return self._yanit(
                            200, "<h1>Gizli Alan</h1><p>Bayrak bu yanitin basliginda.</p>",
                            basliklar=[("X-Carot-Bayrak", site.bayrak)])
                    return self._yanit(200, f"<h1>Gizli Alan</h1><p>Bayrak: {site.bayrak}</p>")
                if dizin in site.yem_dizinler:
                    return self._yanit(403, "<h1>403</h1>")
                return self._yanit(404, "<h1>404</h1>")

        return Isleyici

    def baslat(self) -> None:
        self._sunucu = ThreadingHTTPServer((self.bind_adres, self.port), self._isleyici())
        self._sunucu.daemon_threads = True
        self._is_parcacigi = threading.Thread(target=self._sunucu.serve_forever, daemon=True)
        self._is_parcacigi.start()

    def durdur(self) -> None:
        if self._sunucu is not None:
            self._sunucu.shutdown()
            self._sunucu.server_close()
            self._sunucu = None
