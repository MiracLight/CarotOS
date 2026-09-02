"""
CarotOS Poligon -- ogretmen skor sunucusu.

KRITIK AYRIM -- bu, sahte_giris.py'deki kuralin TAM TERSI:
  - Saldiri hedefleri (SahteGirisServisi vb.) SADECE 127.0.0.1'e baglanir.
  - Bu sunucu ise SINIF AGINDA ERISILEBILIR OLMAK ZORUNDADIR, cunku
    ogrenciler kendi makinelerinden buraya baglanacak.
Bu iki kural birbirine KARISTIRILMAMALI. Buradan saldiri trafigi
GECMEZ -- sadece ilerleme/skor/ipucu JSON mesajlari.

Protokol (hepsi JSON):
  POST /ilerleme      {ogrenci, sifre, gorev_id, durum, sure_sn}
  POST /ipucu_gonder  {ogrenci, mesaj}                    (ogretmen kullanir)
  GET  /ipucu?ogrenci=AD                                   (ogrenci sorar, bir kez okunur)
  GET  /durum                                              (ogretmen paneli izler)
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


class OdaDurumu:
    """Bellek ici oda durumu. Veritabani gerekmez -- ders bitince oda kapanir."""

    def __init__(self, oda_kodu: str, sifre: str):
        self.oda_kodu = oda_kodu
        self.sifre = sifre
        self.acik_gorevler: set[str] = set()
        self.ogrenciler: dict[str, dict] = {}
        # Her öğrenci için BİRİKEN sohbet geçmişi (tek seferlik kuyruk değil):
        # ad -> [{"kimden","metin","zaman","no"}]. Mesajlar silinmez.
        self.sohbetler: dict[str, list] = {}
        self._mesaj_sayaci = 0
        self._kilit = threading.Lock()

    def gorev_ac(self, gorev_id: str) -> None:
        with self._kilit:
            self.acik_gorevler.add(gorev_id)

    def gorev_kapat(self, gorev_id: str) -> None:
        with self._kilit:
            self.acik_gorevler.discard(gorev_id)

    def ogrenci_aktif_mi(self, ad: str) -> bool:
        """Öğrencinin KENDİ istemcisinin periyodik olarak sorması içindir:
        öğretmen '✕' ile onu attıysa buradan False döner, istemci bunu
        görünce kendini oturumdan çıkarır (giriş ekranına döner)."""
        with self._kilit:
            return ad in self.ogrenciler

    def ogrenciyi_at(self, ad: str) -> None:
        """Öğrenciyi listeden kaldırır. Kalıcı bir yasaklama değil --
        öğrenci tekrar ilerleme bildirirse (veya yeniden katılırsa)
        listeye normal şekilde geri döner. Sadece öğretmenin ekranını
        (yanlışlıkla iki kez katılma, test amaçlı isim gibi durumlar
        için) temizlemesine yarar."""
        with self._kilit:
            self.ogrenciler.pop(ad, None)

    def katil(self, ad: str, sifre: str) -> None:
        """Öğrenci odaya katılırken çağrılır. Şifre yanlışsa
        PermissionError, isim zaten kullanımdaysa ValueError fırlatır.
        Aynı isim, önceki sahibi öğretmen tarafından atılana kadar (veya
        oda kapanana kadar) tekrar kullanılamaz -- kalıcı bir yasak
        değil, sadece aynı anda iki öğrencinin aynı adı taşımasını önler."""
        if not secrets.compare_digest(sifre, self.sifre):
            raise PermissionError("yanlış oda şifresi")
        with self._kilit:
            if ad in self.ogrenciler:
                raise ValueError(f"'{ad}' ismi zaten kullanılıyor")
            self.ogrenciler[ad] = {
                "gorev_id": None,
                "durum": "basladi",
                "sure_sn": 0,
                "son_gorulme": time.time(),
            }

    def ilerleme_guncelle(self, ad: str, sifre: str, gorev_id: str,
                           durum: str, sure_sn: float) -> None:
        if not secrets.compare_digest(sifre, self.sifre):
            raise PermissionError("yanlış oda şifresi")
        with self._kilit:
            self.ogrenciler[ad] = {
                "gorev_id": gorev_id,
                "durum": durum,
                "sure_sn": sure_sn,
                "son_gorulme": time.time(),
            }

    def mesaj_ekle(self, ogrenci: str, kimden: str, metin: str) -> dict:
        """Bir ogrencinin sohbetine mesaj ekler.
        kimden: 'ogretmen' | 'ogrenci'
        ogrenci='tum_sinif' ise o anki tum ogrencilere yazar."""
        with self._kilit:
            self._mesaj_sayaci += 1
            no = self._mesaj_sayaci
            temel = {"kimden": kimden, "metin": metin, "zaman": time.time(), "no": no}
            if ogrenci == "tum_sinif":
                temel["tum_sinif"] = True
                for ad in self.ogrenciler:
                    self.sohbetler.setdefault(ad, []).append(dict(temel))
            else:
                self.sohbetler.setdefault(ogrenci, []).append(temel)
            return temel

    def sohbet_getir(self, ogrenci: str, son_no: int = 0) -> list:
        """son_no'dan buyuk numarali mesajlari doner.
        Ogrenci sadece yeni mesajlari icin son_no verir; ogretmen tum
        gecmis icin son_no=0 kullanir."""
        with self._kilit:
            return [m for m in self.sohbetler.get(ogrenci, []) if m["no"] > son_no]

    def anlik_goruntu(self) -> dict:
        with self._kilit:
            return {
                "oda_kodu": self.oda_kodu,
                "acik_gorevler": sorted(self.acik_gorevler),
                "ogrenciler": dict(self.ogrenciler),
            }

    def ilerleme_ozeti(self, gorev_id: str | None = None) -> dict:
        """Bir görev için 'kaç öğrenci var / kaç tamamladı' sayısını verir.

        gorev_id verilmezse tüm öğrenciler sayılır (hangi görevde
        olursa olsun). '5/10 bitirdi' göstergesinin veri kaynağı budur.
        """
        with self._kilit:
            ilgili = [
                b for b in self.ogrenciler.values()
                if gorev_id is None or b.get("gorev_id") == gorev_id
            ]
            toplam = len(ilgili)
            tamamlayan = sum(1 for b in ilgili if b.get("durum") == "tamamlandi")
            return {"toplam": toplam, "tamamlayan": tamamlayan}


def oda_kodu_uret() -> str:
    """4 haneli, öğretmenin sesli okuyup öğrencilerin kolayca yazabileceği kod."""
    return str(secrets.randbelow(9000) + 1000)


def oda_sifresi_uret() -> str:
    return secrets.token_hex(3)  # 6 hex karakter, örn. 'a1b2c3'


def _sunucu_sinifi_olustur(oda: OdaDurumu):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002
            pass  # sınıfta konsolu kirletmesin

        def _json_gonder(self, veri: dict, kod: int = 200) -> None:
            govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
            self.send_response(kod)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(govde)))
            self.end_headers()
            self.wfile.write(govde)

        def _json_oku(self) -> dict:
            uzunluk = int(self.headers.get("Content-Length", 0))
            ham = self.rfile.read(uzunluk) if uzunluk else b"{}"
            return json.loads(ham.decode("utf-8"))

        def do_GET(self) -> None:  # noqa: N802
            ayristirilan = urlparse(self.path)
            sorgu = parse_qs(ayristirilan.query)

            if ayristirilan.path == "/durum":
                self._json_gonder(oda.anlik_goruntu())
            elif ayristirilan.path == "/gorevler":
                # Kimlik doğrulama gerekmez: hangi görevin açık olduğu
                # gizli bir bilgi değil, öğrenci katılmadan önce bunu bilmeli.
                self._json_gonder({"acik_gorevler": sorted(oda.acik_gorevler)})
            elif ayristirilan.path == "/aktif_mi":
                # Öğrenci istemcisi, öğretmen '✕' ile kendisini attı mı
                # diye periyodik olarak bunu sorar. Kimlik doğrulama
                # gerekmez -- /sohbet ve /gorevler ile aynı gerekçe:
                # sadece kendi adının listede olup olmadığını öğreniyor,
                # başka bir öğrenciye ait gizli bir bilgi sızmıyor.
                ad = sorgu.get("ogrenci", [""])[0]
                self._json_gonder({"aktif": oda.ogrenci_aktif_mi(ad)})
            elif ayristirilan.path == "/sohbet":
                # Öğrenci kendi sohbetindeki yeni mesajları çeker.
                # son_no: en son gördüğü mesaj numarası (0 = tümü).
                ad = sorgu.get("ogrenci", [""])[0]
                son_no = int(sorgu.get("son_no", ["0"])[0])
                self._json_gonder({"mesajlar": oda.sohbet_getir(ad, son_no)})
            else:
                self._json_gonder({"hata": "bilinmeyen yol"}, 404)

        def do_POST(self) -> None:  # noqa: N802
            try:
                veri = self._json_oku()
            except json.JSONDecodeError:
                self._json_gonder({"hata": "geçersiz JSON"}, 400)
                return

            ayristirilan = urlparse(self.path)

            if ayristirilan.path == "/katil":
                try:
                    oda.katil(ad=veri["ogrenci"], sifre=veri["sifre"])
                    self._json_gonder({"tamam": True})
                except PermissionError:
                    self._json_gonder({"hata": "yanlış şifre"}, 403)
                except ValueError:
                    self._json_gonder({
                        "hata": "isim_alinmis",
                        "mesaj": "Bu isim mevcut sınıf için alındı",
                    }, 409)
                except KeyError as e:
                    self._json_gonder({"hata": f"eksik alan: {e}"}, 400)
            elif ayristirilan.path == "/ilerleme":
                try:
                    oda.ilerleme_guncelle(
                        ad=veri["ogrenci"], sifre=veri["sifre"],
                        gorev_id=veri["gorev_id"], durum=veri["durum"],
                        sure_sn=veri.get("sure_sn", 0),
                    )
                    self._json_gonder({"tamam": True})
                except PermissionError:
                    self._json_gonder({"hata": "yanlış şifre"}, 403)
                except KeyError as e:
                    self._json_gonder({"hata": f"eksik alan: {e}"}, 400)
            elif ayristirilan.path == "/mesaj":
                # Hem öğretmen hem öğrenci mesaj gönderir.
                # kimden: 'ogretmen' | 'ogrenci'
                # ogrenci: hedef öğrenci adı (öğrenci kendi adını yazar),
                #          öğretmen 'tum_sinif' da yazabilir.
                kayit = oda.mesaj_ekle(
                    ogrenci=veri["ogrenci"],
                    kimden=veri.get("kimden", "ogretmen"),
                    metin=veri["metin"],
                )
                self._json_gonder({"tamam": True, "no": kayit["no"]})
            else:
                self._json_gonder({"hata": "bilinmeyen yol"}, 404)

    return Handler


def sunucu_baslat(oda: OdaDurumu, bind_adres: str, port: int) -> ThreadingHTTPServer:
    """bind_adres burada BİLEREK '0.0.0.0' veya sınıfın LAN adresi olabilir.
    sahte_giris.py'deki 127.0.0.1 kısıtlaması bu fonksiyona UYGULANMAZ."""
    sunucu = ThreadingHTTPServer((bind_adres, port), _sunucu_sinifi_olustur(oda))
    thread = threading.Thread(target=sunucu.serve_forever, daemon=True)
    thread.start()
    return sunucu
