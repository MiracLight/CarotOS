"""
CarotOS Poligon -- ogretmen skor sunucusu.

KRITIK AYRIM -- bu, sahte_giris.py'deki kuralin TAM TERSI:
  - Saldiri hedefleri (SahteGirisServisi vb.) SADECE 127.0.0.1'e baglanir.
  - Bu sunucu ise SINIF AGINDA ERISILEBILIR OLMAK ZORUNDADIR, cunku
    ogrenciler kendi makinelerinden buraya baglanacak.
Bu iki kural birbirine KARISTIRILMAMALI. Buradan saldiri trafigi
GECMEZ -- sadece ilerleme/skor/ipucu JSON mesajlari.

Protokol (hepsi JSON):
  POST /katil         {ogrenci, sifre}  -> {tamam, anahtar, ad}  (anahtar: ogrenciye ozel; ad: kaydedilen ad)
  POST /ilerleme      {ogrenci, sifre, anahtar, gorev_id, durum, sure_sn[, cevap, soru_no, puan]}
  POST /mesaj         {ogrenci, sifre, anahtar, metin}   (ogrenci -> ogretmen sohbeti)
  GET  /sohbet?ogrenci=AD&sifre=...&anahtar=...&son_no=N (ogrenci kendi sohbetini ceker)
  GET  /aktif_mi?ogrenci=AD&sifre=...&anahtar=...        (ogrenci: hala sinifta miyim?)
  GET  /gorevler                                          (sifresiz: acik gorev ve ayarlari; ogrenci adi icermez)

Sifresiz yanit veren TEK yol /gorevler'dir. Ogrenci adlari ve ilerlemeleri ag uzerinden hicbir yolda
toplu olarak verilmez: ogretmen paneli oda durumunu surec icinden (OdaDurumu) okur. Ogretmenin
ogrencilere yazdigi notlar da surec icinden eklenir (mesaj_ekle / tum_sinifa_yaz); agda bunun yolu yoktur.

Sinirlar: govde 64 KB, yanlis sifre adres basina 60 sn'de 10, oda 200 ogrenci, adres basina 40 katilim,
256 (adres basina 32) eszamanli baglanti, baglanti omru 20 sn.

CTF (hakem sunucudur; hepsi oda sifresi + katilmis ogrenci ister; bkz. ctf_cekirdek.py):
  (CTF isteklerinin hepsi ayrica katilimda verilen 'anahtar' ister)
  GET  /ctf/durum?ogrenci=AD&sifre=...&anahtar=...  gorev listesi (bayrak YOK), kalan sure
  GET  /ctf/dosya?ogrenci=AD&sifre=...&gorev=ID   ogrenciye ozel gorev dosyasi
  GET  /ctf/skor?ogrenci=AD&sifre=...             skor tablosu (donukse donuk hali)
  POST /ctf/gonder    {ogrenci, sifre, gorev, bayrak}   sunucu dogrular ve puanlar
  POST /ctf/ipucu     {ogrenci, sifre, gorev, no}       siradaki ipucu (ceza cozumde dusulur)
"""

from __future__ import annotations

import json
import os
import re
import secrets
import socket
import threading
import time
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# Sinif agindaki herhangi bir cihaz bu sunucuya baglanabilir; istek boyutu ve
# yanlis sifre denemesi sinirlanir (6 haneli onaltilik sifre = 24 bit).
MAKS_GOVDE = 64 * 1024          # bayt
MAKS_AD = 64                    # ogrenci adi / gorev kimligi / durum uzunlugu
MAKS_MESAJ = 1000               # sohbet mesaji ve cevap metni uzunlugu
ISTEK_ZAMAN_ASIMI = 10.0        # sn: yarim kalan istek (govdesi gelmeyen) baglantiyi sonsuza dek tutamaz
# Yukaridaki zaman asimi her okuma icin AYRI sayilir: birkac saniyede bir tek bayt gonderen baglanti onu
# hic asmaz. Bu yuzden istegin tamami icin ayrica bir ust sinir ve eszamanli baglanti sinirlari vardir;
# sunucu ogretmen uygulamasiyla ayni surecte calistigindan is parcacigi/dosya tanitici tukenmesi
# uygulamanin kendisini de durdururdu.
ISTEK_TOPLAM_SURE = 20.0        # sn: bir baglantinin (baslik + govde + yanit) toplam omru
MAKS_BAGLANTI = 256             # ayni anda islenen toplam baglanti
ADRES_BASINA_BAGLANTI = 32      # tek bir IP adresinden ayni anda (NAT arkasindaki sinif sigar)
DENEME_PENCERESI = 60.0         # sn
DENEME_LIMITI = 10              # pencerede yanlis sifre sayisi

# Ogrenci adi olarak kullanilamayan adlar: sunucunun ic anlam yukledigi ya da ogretmenle
# karistirilabilecek adlar. Karsilastirma ad_anahtari() uzerinden yapilir (buyuk/kucuk harf gozetmez).
AYRILMIS_ADLAR = frozenset({"tum_sinif", "tum sinif", "ogretmen", "teacher", "sistem", "system",
                            "sunucu", "server", "admin", "root"})
_YASAK_KATEGORILER = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})


MAKS_OGRENCI = 200              # bir odadaki en fazla ogrenci
ADRES_BASINA_OGRENCI = 40       # tek bir IP adresinden en fazla katilim (NAT arkasindaki bir sinif sigar,
                                # tek bir cihaz sinifi sahte adlarla dolduramaz)
MAKS_CEVAP_KAYDI = 500          # ogrenci basina saklanan cevap denemesi (eskiler dusurulur)
MAKS_SURE_SN = 24 * 3600        # bildirilen sure bu araliga kirpilir
GENEL_PUAN_SINIRI = 1000        # gorev dosyasi okunamazsa tek soru icin ust sinir
GECERLI_DURUMLAR = frozenset({"basladi", "tamamlandi", "yanlis_denedi", "atlandi"})
_GOREV_KIMLIGI = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
_GOREVLER_DIZINI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gorevler")
_puan_onbellegi: dict[str, int] = {}


class GecersizAd(ValueError):
    """Ad bos, cok uzun, denetim/yon karakteri iceriyor ya da ayrilmis bir ad."""


class SinifDolu(Exception):
    """Oda MAKS_OGRENCI ogrenciye ulasti."""


class AdresSiniri(Exception):
    """Ayni IP adresinden ADRES_BASINA_OGRENCI katilim var."""


def gorev_en_yuksek_puan(gorev_id) -> int:
    """Gorev dosyasindaki en yuksek puan (zorluklarin en buyugu). Ogrencinin bildirdigi puan bununla
    sinirlanir. Kimlik gecersizse 0; dosya yoksa ya da okunamazsa GENEL_PUAN_SINIRI."""
    if not isinstance(gorev_id, str) or not _GOREV_KIMLIGI.match(gorev_id):
        return 0
    if gorev_id in _puan_onbellegi:
        return _puan_onbellegi[gorev_id]
    sinir = GENEL_PUAN_SINIRI
    # Istemciyle ayni kural: gorevin kendi dosyasi yoksa sablon dosyasi kullanilir (orn. hydra-01)
    for dosya in (gorev_id + ".json", "sablon-ve-ornek.json"):
        try:
            with open(os.path.join(_GOREVLER_DIZINI, dosya), encoding="utf-8") as f:
                puan = json.load(f).get("puan")
        except (OSError, ValueError, AttributeError):
            continue
        degerler = list(puan.values()) if isinstance(puan, dict) else [puan]
        degerler = [p for p in degerler if isinstance(p, int) and not isinstance(p, bool) and p >= 0]
        if degerler:
            sinir = min(max(degerler), GENEL_PUAN_SINIRI)
        break
    _puan_onbellegi[gorev_id] = sinir
    return sinir


def json_coz(ham: bytes):
    """Istek govdesini cozer. NaN/Infinity (ve 1e999 gibi sonsuza tasan sayilar) ile asiri derin
    ic ice yapilar ValueError verir: bunlar gecerli JSON degildir ve ileride int()/siralama gibi
    islemleri cokertir (ogretmen paneli zamanlayicisini durdurabiliyordu)."""
    def sabit(ad):
        raise ValueError("sonlu olmayan sayi: " + ad)

    def kayan(metin):
        deger = float(metin)
        if deger != deger or deger in (float("inf"), float("-inf")):
            raise ValueError("sonlu olmayan sayi")
        return deger

    try:
        return json.loads(ham.decode("utf-8"), parse_constant=sabit, parse_float=kayan)
    except RecursionError:
        raise ValueError("cok derin JSON") from None


def _tam_sayi_alani(veri: dict, anahtar: str, ust: int) -> int:
    """Istege bagli tam sayi alani: yoksa/None ise 0; int (ya da tam degerli float) degilse ValueError.
    Sonuc 0..ust araligina kirpilir."""
    deger = veri.get(anahtar)
    if deger is None:
        return 0
    if isinstance(deger, bool) or not isinstance(deger, (int, float)):
        raise ValueError(anahtar)
    if isinstance(deger, float):
        if not deger.is_integer():
            raise ValueError(anahtar)
        deger = int(deger)
    return max(0, min(deger, ust))


def ilerleme_alanlari(veri: dict) -> dict:
    """/ilerleme govdesini dogrular ve OdaDurumu.ilerleme_bildir icin hazirlar.
    Eksik zorunlu alan KeyError, gecersiz deger ValueError verir."""
    gorev_id, durum = veri["gorev_id"], veri["durum"]
    sure_sn = veri.get("sure_sn", 0) or 0
    cevap = veri.get("cevap")
    if not (isinstance(gorev_id, str) and len(gorev_id) <= MAKS_AD):
        raise ValueError("gorev_id")
    if not (isinstance(durum, str) and durum in GECERLI_DURUMLAR):
        raise ValueError("durum")
    if isinstance(sure_sn, bool) or not isinstance(sure_sn, (int, float)):
        raise ValueError("sure_sn")
    if not (cevap is None or (isinstance(cevap, str) and len(cevap) <= MAKS_MESAJ)):
        raise ValueError("cevap")
    return {
        "gorev_id": gorev_id, "durum": durum,
        "sure_sn": max(0, min(sure_sn, MAKS_SURE_SN)),      # int icin de tasmadan calisir
        "cevap": cevap,
        "soru_no": _tam_sayi_alani(veri, "soru_no", 10 ** 6),
        "puan": _tam_sayi_alani(veri, "puan", GENEL_PUAN_SINIRI),
    }


def ad_anahtari(ad: str) -> str:
    """Tekillik karsilastirmasi icin anahtar: 'Ali', 'ALI', 'ALİ' ve 'alı' ayni sayilir
    (Turkce i/ı/İ/I dahil), boylece skor tablosunda birbirinin aynisi gorunen iki ad olusmaz."""
    a = unicodedata.normalize("NFKC", ad).casefold()
    a = unicodedata.normalize("NFKD", a)
    a = "".join(c for c in a if not unicodedata.combining(c))
    return a.replace("ı", "i")


def ad_temizle(ad):
    """Gecerli bir ogrenci adini NORMALLESTIRILMIS halde doner, gecersizse None.

    NFKC'ye cevrilir, bastaki/sondaki bosluk atilir, ic bosluklar teke indirilir. Denetim karakterleri,
    yon degistiren/gorunmez bicim isaretleri ve ayrilmis adlar (tum_sinif, ogretmen...) reddedilir.
    Ayni ad iki kez temizlenince degismez; bu yuzden her istekte guvenle uygulanabilir."""
    if not isinstance(ad, str) or len(ad) > 4 * MAKS_AD:
        return None
    ad = unicodedata.normalize("NFKC", ad)
    # Once karakter denetimi: satir sonu/sekme gibi denetim karakterleri bosluga cevrilip kabul EDILMEZ
    if any(unicodedata.category(c) in _YASAK_KATEGORILER for c in ad):
        return None
    ad = " ".join(ad.split())
    if not (1 <= len(ad) <= MAKS_AD):
        return None
    if ad_anahtari(ad) in AYRILMIS_ADLAR:
        return None
    return ad


class OdaDurumu:
    """Bellek ici oda durumu. Veritabani gerekmez -- ders bitince oda kapanir."""

    def __init__(self, oda_kodu: str, sifre: str):
        self.oda_kodu = oda_kodu
        self.sifre = sifre
        self._basarisiz: dict[str, list[float]] = {}   # adres -> yanlis deneme zamanlari
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
        # Katilimda her ogrenciye verilen gizli anahtar: oda sifresi tum sinifta ortak oldugu icin
        # CTF islemleri (bayrak, ipucu, dosya) baska bir ogrencinin adina yapilamasin diye bu da aranir.
        self._anahtarlar: dict[str, str] = {}
        # Tekillik anahtari -> kayitli ad ('ALI' varken 'ali' katilamaz; bkz. ad_anahtari)
        self._ad_anahtarlari: dict[str, str] = {}
        # Katilim sinirlari (testler ve ozel kurulumlar ornek uzerinden degistirebilir)
        self.maks_ogrenci = MAKS_OGRENCI
        self.adres_basina = ADRES_BASINA_OGRENCI
        self._adresler: dict[str, str] = {}            # ad -> katildigi IP adresi
        # Atanan her sorunun gorevi: soru_no -> gorev_id. Ag uzerinden bildirilen puan yalnizca
        # gercekten atanmis bir soru icin ve o gorevin en yuksek puaniyla sinirli olarak yazilir.
        self._soru_gorevleri: dict[int, str] = {}
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
        # CTF yarismasi (ders modundan bagimsiz): ogretmen baslatinca olusur. Hakem sunucudur.
        self.ctf = None

    def ctf_oturumu(self):
        """CTF oturumunu (yoksa) olusturur ve dondurur; yarisma ogretmen 'baslat' diyene kadar 'hazir' kalir."""
        with self._kilit:
            if self.ctf is None:
                import ctf_cekirdek
                self.ctf = ctf_cekirdek.CtfOturumu()
            return self.ctf

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
            self._soru_gorevleri[self.aktif_soru_no] = gorev_id
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
            self._soru_gorevleri[self.aktif_soru_no] = gorev_id
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
        """Öğrenciyi listeden kaldırır ve anahtarını geçersiz kılar: eski
        anahtarla gelen ilerleme/mesaj/CTF istekleri reddedilir. Kalıcı
        bir yasaklama değil -- öğrenci oda şifresiyle YENİDEN KATILIRSA
        (yeni anahtar alarak) listeye geri döner. Öğretmenin ekranını
        (yanlışlıkla iki kez katılma, test amaçlı isim gibi durumlar
        için) temizlemesine yarar."""
        with self._kilit:
            self.ogrenciler.pop(ad, None)
            self._anahtarlar.pop(ad, None)
            self._adresler.pop(ad, None)
            for k in [k for k, v in self._ad_anahtarlari.items() if v == ad]:
                del self._ad_anahtarlari[k]

    def sifre_dogru(self, sifre) -> bool:
        """Sabit sureli karsilastirma. ASCII disi ya da str olmayan degerde
        compare_digest TypeError verirdi (istek isleyicisi cokerdi); bayta cevrilir."""
        if not isinstance(sifre, str):
            return False
        return secrets.compare_digest(sifre.encode("utf-8"), self.sifre.encode("utf-8"))

    def cok_deneme_mi(self, adres: str) -> bool:
        """Son DENEME_PENCERESI sn'de DENEME_LIMITI yanlis sifre denemesi yapan
        adres gecici olarak reddedilir."""
        simdi = time.monotonic()
        with self._kilit:
            kayit = [t for t in self._basarisiz.get(adres, []) if simdi - t < DENEME_PENCERESI]
            if kayit:
                self._basarisiz[adres] = kayit
            else:
                self._basarisiz.pop(adres, None)
            return len(kayit) >= DENEME_LIMITI

    def basarisiz_kaydet(self, adres: str) -> None:
        with self._kilit:
            self._basarisiz.setdefault(adres, []).append(time.monotonic())

    def katil(self, ad: str, sifre: str, adres: str | None = None) -> str:
        """Öğrenci odaya katılırken çağrılır. Şifre yanlışsa
        PermissionError, isim geçersizse GecersizAd, isim zaten kullanımdaysa
        ValueError, oda doluysa SinifDolu, aynı adresten çok katılım varsa
        AdresSiniri fırlatır. Kaydedilen (normalleştirilmiş) adı döner.
        Aynı isim, önceki sahibi öğretmen tarafından atılana kadar (veya
        oda kapanana kadar) tekrar kullanılamaz -- kalıcı bir yasak
        değil, sadece aynı anda iki öğrencinin aynı adı taşımasını önler.
        Büyük/küçük harf farkı ayrı ad saymaz ('Ali' varken 'ALI' katılamaz)."""
        if not self.sifre_dogru(sifre):
            raise PermissionError("yanlış oda şifresi")
        temiz = ad_temizle(ad)
        if temiz is None:
            raise GecersizAd("gecersiz isim")
        ad = temiz
        anahtar = ad_anahtari(ad)
        with self._kilit:
            if ad in self.ogrenciler or anahtar in self._ad_anahtarlari:
                raise ValueError(f"'{ad}' ismi zaten kullanılıyor")
            if len(self.ogrenciler) >= self.maks_ogrenci:
                raise SinifDolu()
            if adres is not None and sum(1 for a in self._adresler.values() if a == adres) >= self.adres_basina:
                raise AdresSiniri()
            if adres is not None:
                self._adresler[ad] = adres
            self._ad_anahtarlari[anahtar] = ad
            self.ogrenciler[ad] = {
                "gorev_id": None,
                "durum": "basladi",
                "sure_sn": 0,
                "son_gorulme": time.time(),
            }
            self._anahtarlar[ad] = secrets.token_hex(16)
        return ad

    def anahtar_ver(self, ad: str) -> str:
        """Katilmis ogrencinin gizli anahtari (yalnizca /katil yanitinda ogrencinin kendisine doner)."""
        with self._kilit:
            return self._anahtarlar.get(ad, "")

    def anahtar_dogru(self, ad: str, anahtar) -> bool:
        """Sabit sureli karsilastirma; str olmayan ya da bos anahtar her zaman reddedilir."""
        with self._kilit:
            gercek = self._anahtarlar.get(ad)
        if not gercek or not isinstance(anahtar, str):
            return False
        return secrets.compare_digest(anahtar.encode("utf-8"), gercek.encode("utf-8"))

    def ilerleme_bildir(self, ad: str, anahtar, gorev_id: str, durum: str, sure_sn: float,
                        cevap: str | None = None, soru_no: int = 0, puan: int = 0) -> bool:
        """AG UZERINDEN gelen ilerleme (istek isleyicisi bunu cagirir). Alanlar ilerleme_alanlari()
        ile dogrulanmis olmalidir. Ogrencinin anahtari yanlissa ya da ogrenci artik sinifta degilse
        False doner ve HICBIR SEY yazilmaz.

        Anahtar denetimi ile yazma TEK kilit altindadir: araya 'ogrenciyi at' girip atilan ogrencinin
        anahtarsiz olarak listeye geri yazilmasi (adin kilitlenmesi) mumkun degildir.

        Puan yalnizca gercekten atanmis bir soru icin (soru_no o goreve aitse) ve gorevin en yuksek
        puaniyla sinirli olarak yazilir; boylece elle gonderilen bir istek skoru sisiremez ve
        'cozulen_sorular' atanan soru sayisindan fazla kayit tutamaz."""
        with self._kilit:
            gercek = self._anahtarlar.get(ad)
            if (not gercek or ad not in self.ogrenciler or not isinstance(anahtar, str)
                    or not secrets.compare_digest(anahtar.encode("utf-8"), gercek.encode("utf-8"))):
                return False
            soru_no = soru_no if 0 <= soru_no <= self.aktif_soru_no else 0
            puanlanir = (self._soru_gorevleri.get(soru_no) == gorev_id if soru_no
                         else (self.aktif_soru_no == 0 and gorev_id in self.acik_gorevler))
            puan = max(0, min(puan, gorev_en_yuksek_puan(gorev_id)))
            self._ilerleme_yaz(ad, gorev_id, durum, sure_sn, cevap, soru_no, puan, puanlanir)
            return True

    def ilerleme_guncelle(self, ad: str, sifre: str, gorev_id: str,
                           durum: str, sure_sn: float,
                           cevap: str | None = None, soru_no: int = 0,
                           puan: int = 0) -> None:
        """SUREC ICI kullanim (ogretmen tarafi, testler): degerler oldugu gibi yazilir ve ogrenci
        listede yoksa eklenir. Ag isteklerinde KULLANILMAZ -- bkz. ilerleme_bildir."""
        if not self.sifre_dogru(sifre):
            raise PermissionError("yanlış oda şifresi")
        with self._kilit:
            self._ilerleme_yaz(ad, gorev_id, durum, sure_sn, cevap, int(soru_no or 0), int(puan or 0), True)

    def _ilerleme_yaz(self, ad, gorev_id, durum, sure_sn, cevap, soru_no, puan, puanlanir) -> None:
        """Kilit ALINMIS olarak cagrilir."""
        self.ogrenciler[ad] = {
            "gorev_id": gorev_id,
            "durum": durum,
            "sure_sn": sure_sn,
            "son_gorulme": time.time(),
        }
        # Gerçek bir cevap denemesi ise cevap günlüğüne ekle (başladı/
        # atlandı gibi durumlarda cevap metni olmaz).
        if cevap is not None and durum in ("tamamlandi", "yanlis_denedi"):
            kayitlar = self.cevaplar.setdefault(ad, [])
            kayitlar.append({
                "soru_no": soru_no,
                "gorev_id": gorev_id,
                "cevap": cevap,
                "dogru": durum == "tamamlandi",
                "zaman": time.time(),
            })
            if len(kayitlar) > MAKS_CEVAP_KAYDI:
                del kayitlar[:len(kayitlar) - MAKS_CEVAP_KAYDI]
        # Dogru cevapta puani kaydet (soru basina en iyi deneme).
        if durum == "tamamlandi" and puanlanir:
            d = self.cozulen_sorular.setdefault(ad, {})
            if puan >= d.get(soru_no, {}).get("puan", -1):
                d[soru_no] = {"puan": puan, "gorev_id": gorev_id}

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
        ogrenci='tum_sinif' VE kimden='ogretmen' ise o anki tum ogrencilere yazar (bkz. tum_sinifa_yaz).
        Yayin yalnizca ogretmene aciktir: 'tum_sinif' ogrenci adi olarak alinamaz (AYRILMIS_ADLAR) ve
        bir ogrenci mesaji hicbir kosulda baska ogrencilerin sohbetine dusmez."""
        if kimden not in ("ogretmen", "ogrenci"):
            raise ValueError("gecersiz gonderen")
        with self._kilit:
            self._mesaj_sayaci += 1
            no = self._mesaj_sayaci
            temel = {"kimden": kimden, "metin": metin, "zaman": time.time(), "no": no}
            if ogrenci == "tum_sinif" and kimden == "ogretmen":
                temel["tum_sinif"] = True
                for ad in self.ogrenciler:
                    self.sohbetler.setdefault(ad, []).append(dict(temel))
            else:
                self.sohbetler.setdefault(ogrenci, []).append(temel)
            return temel

    def tum_sinifa_yaz(self, metin: str) -> dict:
        """Ogretmenin tum sinifa yazdigi not. Yalnizca surec icinden (ogretmen arayuzu) cagrilir;
        ag uzerinden bu islemi tetikleyen bir yol YOKTUR."""
        return self.mesaj_ekle("tum_sinif", "ogretmen", metin)

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
        timeout = ISTEK_ZAMAN_ASIMI     # govdesi gelmeyen baglanti is parcacigini sonsuza dek tutmasin

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
            """OverflowError: govde cok buyuk; ValueError: gecersiz uzunluk/JSON."""
            uzunluk = int(self.headers.get("Content-Length", 0))
            if uzunluk < 0:
                raise ValueError("gecersiz Content-Length")
            if uzunluk > MAKS_GOVDE:
                raise OverflowError("govde cok buyuk")
            ham = self.rfile.read(uzunluk) if uzunluk else b"{}"
            veri = json_coz(ham)
            if not isinstance(veri, dict):
                raise ValueError("JSON nesnesi bekleniyordu")
            return veri

        @staticmethod
        def _ad(veri: dict):
            """Gecerli ogrenci adi (normallestirilmis; bkz. ad_temizle) ya da None."""
            return ad_temizle(veri.get("ogrenci"))

        @staticmethod
        def _sorgu_adi(sorgu: dict):
            """GET sorgusundaki ogrenci adi: govdedekiyle AYNI kuraldan gecer (yoksa/gecersizse None)."""
            return ad_temizle(sorgu.get("ogrenci", [""])[0])

        def _yetkili_mi(self, sifre) -> bool:
            """Oda sifresi dogruysa True. Yanlis denemeler adres basina sayilir;
            cok sayida yanlis denemeden sonra 429 doner. Yanit zaten gonderilmistir."""
            adres = self.client_address[0]
            if oda.cok_deneme_mi(adres):
                self._json_gonder({"hata": "cok_fazla_deneme",
                                   "mesaj": "Çok fazla yanlış deneme; bir dakika bekleyin"}, 429)
                return False
            if oda.sifre_dogru(sifre):
                return True
            oda.basarisiz_kaydet(adres)
            self._json_gonder({"hata": "yanlış şifre"}, 403)
            return False

        def _guvenli(self, islev) -> None:
            """Isleyicide beklenmeyen bir hata istemciyi yanitsiz birakmasin ve stderr'e iz dokmesin:
            500 doner. Soket hatalarinda (istemci gitti, zaman asimi) baglanti sessizce kapatilir."""
            try:
                islev()
            except OSError:
                self.close_connection = True
            except Exception:  # noqa: BLE001
                try:
                    self._json_gonder({"hata": "sunucu_hatasi"}, 500)
                except OSError:
                    self.close_connection = True

        def do_GET(self) -> None:  # noqa: N802
            self._guvenli(self._get)

        def do_POST(self) -> None:  # noqa: N802
            self._guvenli(self._post)

        def _get(self) -> None:
            ayristirilan = urlparse(self.path)
            sorgu = parse_qs(ayristirilan.query)

            if ayristirilan.path == "/gorevler":
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
                # diye periyodik olarak bunu sorar. Oda şifresi ve öğrencinin
                # KENDİ anahtarı gerekir: şifresiz olsaydı ağdaki herkes
                # "bu ad sınıfta mı" diye ad ad yoklayabilirdi. Atılan
                # öğrencinin anahtarı silindiği için yanıt 'aktif: false' olur;
                # bilinmeyen ad ile yanlış anahtar ayırt edilemez.
                if not self._yetkili_mi(sorgu.get("sifre", [""])[0]):
                    return
                ad = self._sorgu_adi(sorgu)
                anahtar = sorgu.get("anahtar", [""])[0]
                self._json_gonder({"aktif": ad is not None and oda.anahtar_dogru(ad, anahtar)})
            elif ayristirilan.path == "/sohbet":
                # Öğrenci kendi sohbetindeki yeni mesajları çeker.
                # son_no: en son gördüğü mesaj numarası (0 = tümü).
                # Sohbet ogretmenle ogrenci arasindadir; oda sifresi olmayan
                # sinif agi cihazlari okuyamaz.
                if not self._yetkili_mi(sorgu.get("sifre", [""])[0]):
                    return
                ad = self._sorgu_adi(sorgu)
                if not self._anahtar_tamam(ad, sorgu.get("anahtar", [""])[0]):
                    return
                try:
                    son_no = int(sorgu.get("son_no", ["0"])[0])
                except ValueError:
                    son_no = 0
                self._json_gonder({"mesajlar": oda.sohbet_getir(ad, son_no)})
            elif ayristirilan.path in ("/ctf/durum", "/ctf/dosya", "/ctf/skor"):
                self._ctf_oku(ayristirilan.path, sorgu)
            else:
                self._json_gonder({"hata": "bilinmeyen yol"}, 404)

        def _anahtar_tamam(self, ad, anahtar) -> bool:
            """Ogrencinin KENDI anahtarini gostermesi: oda sifresi tum sinifta ortak oldugu icin tek basina
            baska bir ogrenci adina ilerleme/mesaj/CTF islemi yapilmasini engellemez. Yanit hatada gonderilmistir."""
            if isinstance(ad, str) and oda.anahtar_dogru(ad, anahtar):
                return True
            self._json_gonder({"hata": "gecersiz_anahtar"}, 403)
            return False

        def _ctf_ogrenci(self, sifre, ad, anahtar) -> bool:
            """CTF istekleri: oda sifresi dogru, ogrenci odaya katilmis ve KENDI anahtarini gostermis olmali
            (aksi halde sinifta oda sifresini bilen biri baska ogrenci adina ipucu acip puan kirabilirdi).
            Yanit hatada gonderilmistir."""
            if not self._yetkili_mi(sifre):
                return False
            if not isinstance(ad, str) or not (1 <= len(ad) <= MAKS_AD) or not oda.ogrenci_aktif_mi(ad):
                self._json_gonder({"hata": "bilinmeyen öğrenci"}, 404)
                return False
            return self._anahtar_tamam(ad, anahtar)

        def _ctf_hata(self, h) -> None:
            kod = {"bilinmeyen_gorev": 404, "baslamadi": 409, "surec_degil": 409}.get(h.kod, 400)
            self._json_gonder({"hata": h.kod}, kod)

        def _ctf_oku(self, yol, sorgu) -> None:
            import ctf_cekirdek
            ad = self._sorgu_adi(sorgu)
            if not self._ctf_ogrenci(sorgu.get("sifre", [""])[0], ad, sorgu.get("anahtar", [""])[0]):
                return
            ctf = oda.ctf_oturumu()
            try:
                if yol == "/ctf/durum":
                    self._json_gonder({
                        "durum": ctf.durum(), "kalan_sn": ctf.kalan_sn(), "donuk": ctf.donuk_mu(),
                        "gorevler": ctf.ogrenci_gorevleri(ad)})
                elif yol == "/ctf/skor":
                    self._json_gonder(ctf.skor_tablosu())
                else:
                    gorev = sorgu.get("gorev", [""])[0]
                    if len(gorev) > MAKS_AD:
                        raise ctf_cekirdek.CtfHata("bilinmeyen_gorev")
                    dosya_adi, icerik = ctf.dosya(ad, gorev)
                    self._json_gonder({"ad": dosya_adi, "icerik": icerik,
                                       "ipuclari": ctf.acilan_ipuclari(ad, gorev)})
            except ctf_cekirdek.CtfHata as h:
                self._ctf_hata(h)

        def _ctf_yaz(self, yol, veri) -> None:
            import ctf_cekirdek
            ad = self._ad(veri)
            if not self._ctf_ogrenci(veri.get("sifre"), ad, veri.get("anahtar")):
                return
            gorev = veri.get("gorev")
            if not isinstance(gorev, str) or len(gorev) > MAKS_AD:
                self._json_gonder({"hata": "bilinmeyen_gorev"}, 404)
                return
            ctf = oda.ctf_oturumu()
            try:
                if yol == "/ctf/gonder":
                    self._json_gonder(ctf.gonder(ad, gorev, veri.get("bayrak")))
                else:
                    self._json_gonder(ctf.ipucu_al(ad, gorev, veri.get("no")))
            except ctf_cekirdek.CtfHata as h:
                self._ctf_hata(h)

        def _post(self) -> None:
            try:
                veri = self._json_oku()
            except OverflowError:
                self._json_gonder({"hata": "gövde çok büyük"}, 413)
                return
            except ValueError:   # JSONDecodeError ve UnicodeDecodeError dahil
                self._json_gonder({"hata": "geçersiz JSON"}, 400)
                return

            ayristirilan = urlparse(self.path)

            if ayristirilan.path == "/katil":
                ad = self._ad(veri)
                if ad is None:
                    self._json_gonder({"hata": "geçersiz isim"}, 400)
                    return
                if not self._yetkili_mi(veri.get("sifre")):
                    return
                try:
                    ad = oda.katil(ad=ad, sifre=veri["sifre"], adres=self.client_address[0])
                    # 'ad': sunucunun kaydettigi (normallestirilmis) ad; istemci sonraki isteklerde bunu kullanir
                    self._json_gonder({"tamam": True, "anahtar": oda.anahtar_ver(ad), "ad": ad})
                except PermissionError:
                    self._json_gonder({"hata": "yanlış şifre"}, 403)
                except GecersizAd:
                    self._json_gonder({"hata": "geçersiz isim"}, 400)
                except SinifDolu:
                    self._json_gonder({"hata": "sinif_dolu"}, 409)
                except AdresSiniri:
                    self._json_gonder({"hata": "adres_siniri"}, 429)
                except ValueError:
                    self._json_gonder({
                        "hata": "isim_alinmis",
                        "mesaj": "Bu isim mevcut sınıf için alındı",
                    }, 409)
                except KeyError as e:
                    self._json_gonder({"hata": f"eksik alan: {e}"}, 400)
            elif ayristirilan.path == "/ilerleme":
                ad = self._ad(veri)
                if ad is None:
                    self._json_gonder({"hata": "geçersiz isim"}, 400)
                    return
                if not self._yetkili_mi(veri.get("sifre")):
                    return
                try:
                    alanlar = ilerleme_alanlari(veri)
                except KeyError as e:
                    self._json_gonder({"hata": f"eksik alan: {e}"}, 400)
                    return
                except (TypeError, ValueError):
                    self._json_gonder({"hata": "geçersiz alan"}, 400)
                    return
                # Anahtar denetimi ve yazma tek adimda (bkz. OdaDurumu.ilerleme_bildir)
                if oda.ilerleme_bildir(ad, veri.get("anahtar"), **alanlar):
                    self._json_gonder({"tamam": True})
                else:
                    self._json_gonder({"hata": "gecersiz_anahtar"}, 403)
            elif ayristirilan.path == "/mesaj":
                # Bu yolu yalnizca ogrenci istemcisi kullanir; ogretmen mesajlarini
                # surec icinden oda.mesaj_ekle ile gonderir. Bu yuzden oda sifresi
                # zorunludur ve gonderen sunucuda 'ogrenci' olarak sabitlenir;
                # aksi halde sinif agindaki herkes ogretmen adina ogrencilere
                # mesaj yazabilirdi.
                if not self._yetkili_mi(veri.get("sifre")):
                    return
                ad = self._ad(veri)
                metin = veri.get("metin")
                if (ad is None or not isinstance(metin, str)
                        or not metin.strip() or len(metin) > MAKS_MESAJ):
                    self._json_gonder({"hata": "geçersiz mesaj"}, 400)
                    return
                if not oda.ogrenci_aktif_mi(ad):
                    # katilmamis adlara yazilamaz: sohbet sozlugu sisirilemez
                    self._json_gonder({"hata": "bilinmeyen öğrenci"}, 404)
                    return
                if not self._anahtar_tamam(ad, veri.get("anahtar")):
                    return
                kayit = oda.mesaj_ekle(ogrenci=ad, kimden="ogrenci", metin=metin)
                self._json_gonder({"tamam": True, "no": kayit["no"]})
            elif ayristirilan.path in ("/ctf/gonder", "/ctf/ipucu"):
                self._ctf_yaz(ayristirilan.path, veri)
            else:
                self._json_gonder({"hata": "bilinmeyen yol"}, 404)

    return Handler


class SinirliSunucu(ThreadingHTTPServer):
    """Baglanti sayisini ve baglanti omrunu sinirlayan HTTP sunucusu.

    * Toplamda maks_baglanti, tek adresten adres_basina_baglanti eszamanli baglanti islenir; fazlasi
      is parcacigi ACILMADAN hemen kapatilir (istemci 'baglanti kesildi' gorur ve yeniden dener).
    * istek_toplam_sure'yi asan baglanti bir gozcu tarafindan kapatilir: yavas yavas bayt gonderip
      is parcacigini suresiz tutmak (slowloris) mumkun degildir.
    """

    daemon_threads = True

    def __init__(self, *a, **k):
        # Alanlar ust sinif kurulmadan ONCE atanir: port doluysa ust sinif kurucusu server_close()
        # cagirir ve o da _kapandi'ya bakar (yoksa soket kapatilamadan AttributeError olusurdu).
        self.maks_baglanti = MAKS_BAGLANTI
        self.adres_basina_baglanti = ADRES_BASINA_BAGLANTI
        self.istek_toplam_sure = ISTEK_TOPLAM_SURE
        self.reddedilen = 0                                  # sinir yuzunden kapatilan baglanti sayisi
        self._bag_kilit = threading.Lock()
        self._adres_sayisi: dict[str, int] = {}
        self._aktif: dict[socket.socket, float] = {}         # baglanti -> baslangic (monotonic)
        self._kapandi = threading.Event()
        super().__init__(*a, **k)                            # port doluysa OSError (gozcu baslamaz)
        threading.Thread(target=self._gozcu, daemon=True).start()

    def aktif_baglanti(self) -> int:
        with self._bag_kilit:
            return len(self._aktif)

    def process_request(self, request, client_address):
        adres = client_address[0]
        with self._bag_kilit:
            dolu = (len(self._aktif) >= self.maks_baglanti
                    or self._adres_sayisi.get(adres, 0) >= self.adres_basina_baglanti)
            if dolu:
                self.reddedilen += 1
            else:
                self._aktif[request] = time.monotonic()
                self._adres_sayisi[adres] = self._adres_sayisi.get(adres, 0) + 1
        if dolu:
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._birak(request, adres)                      # is parcacigi acilamadi
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._birak(request, client_address[0])

    def _birak(self, request, adres) -> None:
        with self._bag_kilit:
            if self._aktif.pop(request, None) is None:
                return
            kalan = self._adres_sayisi.get(adres, 0) - 1
            if kalan > 0:
                self._adres_sayisi[adres] = kalan
            else:
                self._adres_sayisi.pop(adres, None)

    def _gozcu(self) -> None:
        """Toplam suresini asan baglantilari kapatir (okumada bekleyen is parcacigi boylece uyanir)."""
        while not self._kapandi.wait(min(1.0, max(0.05, self.istek_toplam_sure / 4))):
            simdi = time.monotonic()
            with self._bag_kilit:
                eski = [b for b, t in self._aktif.items() if simdi - t > self.istek_toplam_sure]
            for b in eski:
                try:
                    b.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def handle_error(self, request, client_address):
        """Istemci kaynakli soket hatalari (kesilen baglanti, zaman asimi) stderr'i doldurmasin."""
        import sys as _sys
        if isinstance(_sys.exc_info()[1], OSError):
            return
        super().handle_error(request, client_address)

    def server_close(self):
        self._kapandi.set()
        super().server_close()


def sunucu_baslat(oda: OdaDurumu, bind_adres: str, port: int) -> SinirliSunucu:
    """bind_adres burada BİLEREK '0.0.0.0' veya sınıfın LAN adresi olabilir.
    sahte_giris.py'deki 127.0.0.1 kısıtlaması bu fonksiyona UYGULANMAZ."""
    sunucu = SinirliSunucu((bind_adres, port), _sunucu_sinifi_olustur(oda))
    thread = threading.Thread(target=sunucu.serve_forever, daemon=True)
    thread.start()
    return sunucu
