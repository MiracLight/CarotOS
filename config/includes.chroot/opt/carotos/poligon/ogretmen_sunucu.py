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
        # Her acik gorevin zorlugu: gorev_id -> 'kolay'|'orta'|'zor'.
        # Ogretmen gorevi atarken secer; ogrenci /gorevler'den okur.
        self.gorev_zorluklari: dict[str, str] = {}
        # "Soru Olustur" ile atanan OZEL parametreler: gorev_id -> param sozlugu.
        # Isimli zorluk yerine dogrudan bu parametreler ogrenciye tasinir.
        self.gorev_parametreleri: dict[str, dict] = {}
        # Atanan soru varyanti (gorev_id -> numara) ve gorev basina kullanilmis
        # varyantlar (otomatik secim ayni soruyu arka arkaya vermesin).
        self.gorev_varyantlari: dict[str, int] = {}
        self._varyant_gecmisi: dict[str, list[int]] = {}
        # Siniftaki "N. soru" sayaci. 0 = henuz soru atanmadi. Ogretmen her
        # "Soruyu Ata" dediginde (gorev_ata / ozel_soru_ata) 1 artar.
        self.aktif_soru_no = 0
        self.ogrenciler: dict[str, dict] = {}
        # Her öğrenci için BİRİKEN sohbet geçmişi (tek seferlik kuyruk değil):
        # ad -> [{"kimden","metin","zaman","no"}]. Mesajlar silinmez.
        self.sohbetler: dict[str, list] = {}
        # Her öğrenci için BİRİKEN cevap günlüğü (öğretmenin "Verdiği
        # Cevaplar" penceresi okur): ad -> [{soru_no,gorev_id,cevap,dogru,zaman}].
        self.cevaplar: dict[str, list] = {}
        # "IP ve Adres": ogretmenin sinifa uyguladigi hedef loopback adresi.
        # Varsayilan 127.0.0.1. Atanan gorevler bu adrese baglanir (hepsi
        # 127.0.0.0/8 -- makineyi terk etmez).
        self.hedef_adres = "127.0.0.1"
        # Ayar surumu: hedef adres gibi "mevcut soruyu etkileyen" ayarlar
        # degisince artar. Ogrenci bunu gorunce soruyu (numara degismeden)
        # yeniden yukler ve uyari gosterir.
        self.ayar_surumu = 0
        # Skor: her ogrencinin COZDUGU sorular -> {soru_no: {"puan","gorev_id"}}.
        # soru_no benzersiz oldugu icin tekrar cozmek puani sismiyor; en iyi
        # deneme saklaniyor. "Sinif" skor sekmesinin kaynagi budur.
        self.cozulen_sorular: dict[str, dict] = {}
        self._mesaj_sayaci = 0
        self._kilit = threading.Lock()

    def gorev_ac(self, gorev_id: str, zorluk: str = "orta") -> None:
        if zorluk not in ("kolay", "orta", "zor"):
            zorluk = "orta"
        with self._kilit:
            self.acik_gorevler.add(gorev_id)
            self.gorev_zorluklari[gorev_id] = zorluk

    def gorev_kapat(self, gorev_id: str) -> None:
        with self._kilit:
            self.acik_gorevler.discard(gorev_id)
            self.gorev_zorluklari.pop(gorev_id, None)
            self.gorev_varyantlari.pop(gorev_id, None)

    def varyant_oner(self, gorev_id: str, zorluk: str = "orta") -> int:
        """Gorev icin SIRADAKI soru varyantini secer: ayni gorevde daha once
        kullanilmamis olanlardan, zorluga uygun rastgele biri; hepsi
        kullanildiysa dongu yeniden baslar. Varyanti olmayan gorevde 0."""
        import varyantlar as _vy
        with self._kilit:
            kullanilan = self._varyant_gecmisi.setdefault(gorev_id, [])
            no = _vy.gorev_varyant_sec(gorev_id, zorluk, kullanilan)
            if no and no in kullanilan:
                # tum varyantlar bitti: yeni tur; son verilen yine de elenir ki
                # tur sinirinda ayni soru art arda gelmesin
                kullanilan[:] = kullanilan[-1:]
                no = _vy.gorev_varyant_sec(gorev_id, zorluk, kullanilan)
            if no:
                kullanilan.append(no)
            return no

    def gorev_ata(self, gorev_id: str, zorluk: str = "orta", varyant: int | None = None) -> int:
        """Ogretmen 'Soruyu Ata' dediginde cagrilir: acik gorevi (ve
        zorlugunu) bununla DEGISTIRIR ve sira numarasini bir artirir.
        Siniftaki 'N. soru' kavraminin kaynagi budur. Atanan soru
        numarasini doner."""
        if zorluk not in ("kolay", "orta", "zor"):
            zorluk = "orta"
        if varyant is None:                      # otomatik: bilgisayar secer
            varyant = self.varyant_oner(gorev_id, zorluk)
        with self._kilit:
            self.acik_gorevler = {gorev_id}
            self.gorev_zorluklari = {gorev_id: zorluk}
            self.gorev_parametreleri = {}  # hazir soru -> ozel parametre yok
            self.gorev_varyantlari = {gorev_id: int(varyant)} if varyant else {}
            self.aktif_soru_no += 1
            return self.aktif_soru_no

    def ozel_soru_ata(self, gorev_id: str, parametreler: dict, etiket: str = "") -> int:
        """'Soru Olustur': ogretmenin KENDI belirledigi parametrelerle bir
        soru atar. Isimli zorluk yerine parametreler dogrudan ogrenciye
        tasinir; makine cevabi bunlara gore uretilir. Soru numarasini doner."""
        parametreler = dict(parametreler)
        try:
            varyant = int(parametreler.pop("varyant", 0) or 0)
        except (TypeError, ValueError):
            varyant = 0
        if varyant < 1:                          # 0 / bos: bilgisayar secer
            varyant = self.varyant_oner(gorev_id, "orta")
        with self._kilit:
            self.acik_gorevler = {gorev_id}
            self.gorev_zorluklari = {}          # ozel soruda isimli zorluk yok
            self.gorev_parametreleri = {gorev_id: parametreler}
            self.gorev_varyantlari = {gorev_id: varyant} if varyant else {}
            self.aktif_soru_no += 1
            return self.aktif_soru_no

    def set_hedef_adres(self, adres: str) -> str:
        """'IP ve Adres': sinif hedef adresini belirler. SADECE loopback
        (127.0.0.0/8) kabul edilir -- hepsi makinede kalir. Gecersizse
        ValueError. Ayarlanan adresi doner."""
        from ag_guvenlik import loopback_adres_mi
        adres = str(adres).strip()
        if not loopback_adres_mi(adres):
            raise ValueError("adres loopback (127.0.0.0/8) olmali")
        with self._kilit:
            if adres != self.hedef_adres:
                self.hedef_adres = adres
                self.ayar_surumu += 1  # mevcut soruyu etkiler -> ogrenci yeniden yukler
            return adres

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
                           durum: str, sure_sn: float,
                           cevap: str | None = None, soru_no: int = 0,
                           puan: int = 0) -> None:
        if not secrets.compare_digest(sifre, self.sifre):
            raise PermissionError("yanlış oda şifresi")
        with self._kilit:
            self.ogrenciler[ad] = {
                "gorev_id": gorev_id,
                "durum": durum,
                "sure_sn": sure_sn,
                "son_gorulme": time.time(),
            }
            # Gerçek bir cevap denemesi ise cevap günlüğüne ekle (başladı/
            # atlandı gibi durumlarda cevap metni olmaz).
            if cevap is not None and durum in ("tamamlandi", "yanlis_denedi"):
                self.cevaplar.setdefault(ad, []).append({
                    "soru_no": int(soru_no or 0),
                    "gorev_id": gorev_id,
                    "cevap": cevap,
                    "dogru": durum == "tamamlandi",
                    "zaman": time.time(),
                })
            # Dogru cevapta puani kaydet (soru basina en iyi deneme).
            if durum == "tamamlandi":
                d = self.cozulen_sorular.setdefault(ad, {})
                no = int(soru_no or 0)
                if int(puan or 0) >= d.get(no, {}).get("puan", -1):
                    d[no] = {"puan": int(puan or 0), "gorev_id": gorev_id}

    def sinif_ozeti(self) -> list:
        """Her ogrenci icin ozet: cozulen soru sayisi, toplam puan, deneme
        sayisi, durum. Puana (sonra cozulene) gore sirali -- skor tablosu."""
        with self._kilit:
            satirlar = []
            for ad, bilgi in self.ogrenciler.items():
                cozulen = self.cozulen_sorular.get(ad, {})
                satirlar.append({
                    "ad": ad,
                    "cozulen": len(cozulen),
                    "puan": sum(v.get("puan", 0) for v in cozulen.values()),
                    "deneme": len(self.cevaplar.get(ad, [])),
                    "durum": bilgi.get("durum", ""),
                })
            satirlar.sort(key=lambda s: (-s["puan"], -s["cozulen"], s["ad"].lower()))
            return satirlar

    def ogrenci_cevaplari(self, ad: str) -> list:
        """Bir öğrencinin verdiği tüm cevapların (zaman sırasıyla) kopyası."""
        with self._kilit:
            return [dict(k) for k in self.cevaplar.get(ad, [])]

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
                "zorluklar": dict(self.gorev_zorluklari),
                "parametreler": dict(self.gorev_parametreleri),
                "varyantlar": dict(self.gorev_varyantlari),
                "hedef_adres": self.hedef_adres,
                "ayar_surumu": self.ayar_surumu,
                "aktif_soru_no": self.aktif_soru_no,
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
                self._json_gonder({
                    "acik_gorevler": sorted(oda.acik_gorevler),
                    "zorluklar": dict(oda.gorev_zorluklari),
                    "parametreler": dict(oda.gorev_parametreleri),
                    "varyantlar": dict(oda.gorev_varyantlari),
                    "hedef_adres": oda.hedef_adres,
                    "ayar_surumu": oda.ayar_surumu,
                    "aktif_soru_no": oda.aktif_soru_no,
                })
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
                        cevap=veri.get("cevap"),
                        soru_no=int(veri.get("soru_no", 0) or 0),
                        puan=int(veri.get("puan", 0) or 0),
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
