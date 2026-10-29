"""
CarotOS Poligon -- ogrenci istemci mantigi.

GTK'den BAGIMSIZ: butun ag/dogrulama/servis mantigi burada, GTK katmani
sadece bu sinifi cagirir. Bu ayrim sayesinde mantik GTK kurulu olmayan
bir ortamda bile test edilebiliyor (asagidaki test dosyasinda oldugu gibi).

Mimari:
  - Her ogrencinin makinesinde KENDI hedef parolasi rastgele uretilir
    ve KENDI sahte servisi bu parolayla baslar.
  - Ogrenci cevabi yazinca karsilastirma YEREL yapilir -- ag uzerinden
    parola tasinmaz.
  - Sadece SONUC (basladi/tamamlandi/yanlis_denedi) ogretmen sunucusuna
    bildirilir.
"""

from __future__ import annotations

import json
import secrets
import sys
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flag_uretici import parola_uret  # noqa: E402
from ag_guvenlik import loopback_adres_mi  # noqa: E402

# Ipucu kullanilan soruda puanin NE KADARI kesilir (0.5 = yari puan).
IPUCU_CEZASI_ORANI = 0.5
from servisler.sahte_giris import SahteGirisServisi  # noqa: E402
from servisler.sahte_ag import SahteAgOrtami
from servisler.sahte_hash import SahteHashDosyasi
from servisler.sahte_web import SahteWebServisi
from servisler.sahte_trafik import SahteTrafik  # noqa: E402
from servisler.sahte_savunma_hedefi import BasitDinleyici  # noqa: E402
import gecmis_defteri  # noqa: E402
from tuzak_laboratuvari import TuzakLab  # noqa: E402
import uretilen_gorevler  # noqa: E402

GOREVLER_DIZINI = Path(__file__).resolve().parent / "gorevler"


def _bos_port_bul(tercih_edilen: int, deneme: int = 50) -> int:
    """tercih_edilen portu dener; kullanımdaysa bir sonrakini dener.
    Aynı makinede birden fazla öğrenci (ya da test) çalışırsa port
    çakışmasını önler. Gerçek sınıfta her öğrenci kendi makinesinde
    olduğu için genelde tercih_edilen port zaten boştur."""
    import socket as _s
    for offset in range(deneme):
        aday = tercih_edilen + offset
        test = _s.socket(_s.AF_INET, _s.SOCK_STREAM)
        try:
            test.bind(("127.0.0.1", aday))
            test.close()
            return aday
        except OSError:
            test.close()
            continue
    raise RuntimeError(f"{tercih_edilen} civarında boş port bulunamadı")


class BaglantiHatasi(Exception):
    pass


class OdaKapaliHatasi(BaglantiHatasi):
    """Öğretmen sunucusuna bağlantı KESİN OLARAK reddedildi (connection
    refused) -- işletim sistemi o portta artık kimsenin dinlemediğini
    söylüyor. Bu neredeyse her zaman öğretmenin uygulamayı tamamen
    kapattığı anlamına gelir (bkz. ogretmen_uygulama.py::kapanirken,
    orada shutdown()'dan sonra BİLEREK server_close() de çağrılıyor ki
    bu ayrım güvenilir olsun). Genel BaglantiHatasi (zaman aşımı, DNS
    sorunu vb.) ile KARIŞTIRILMAMALI -- tepki biçimi farklı olmalı:
    geçici sorun -> sessizce sabret, oda kapandı -> öğrenciyi hemen
    ana menüye döndür."""
    pass


def sudo_ile_calistir(komut: list[str], parola: str, zaman_asimi: float = 10) -> tuple[bool, str, str]:
    """Verilen komutu 'sudo -S -k' ile çalıştırır -- ogretmen_uygulama.py
    içindeki `_root_parolasi_dogrula` ile AYNI teknik (parola stdin'den
    verilir, sudo'nun tty/timestamp önbelleğine güvenilmez). Bu proje
    GTK içinden başka hiçbir şekilde kök yetkisi almaz -- sadece bu tek
    nokta üzerinden, ve sadece öğrencinin görev dosyasında sabit olarak
    tanımlı, önceden bilinen komutlar için (örn. 'ufw status',
    'fail2ban-client status <jail>'). Rastgele/serbest metin komutu
    ÇALIŞTIRILMAZ -- çağıran taraf komut listesini kendisi sabit yazar.

    (basarili, stdout, stderr) döner. Yanlış parola veya sudo hatasında
    basarili=False, stderr sudo'nun kendi hata mesajını taşır."""
    try:
        sonuc = subprocess.run(
            ["sudo", "-S", "-k", *komut],
            input=parola + "\n",
            capture_output=True,
            text=True,
            timeout=zaman_asimi,
        )
        return sonuc.returncode == 0, sonuc.stdout, sonuc.stderr
    except FileNotFoundError:
        return False, "", "'sudo' bulunamadı"
    except subprocess.TimeoutExpired:
        return False, "", "komut zaman aşımına uğradı"


class PoligonIstemci:
    def __init__(self, ogretmen_adres: str, oda_kodu: str, oda_sifre: str, ogrenci_adi: str):
        self.ogretmen_adres = ogretmen_adres.rstrip("/")
        self.oda_kodu = oda_kodu
        self.oda_sifre = oda_sifre
        self.ogrenci_adi = ogrenci_adi
        self.gorev: dict | None = None
        self.hedef_parola: str | None = None  # sadece 'parola_uret' yönteminde dolar (geriye uyumluluk)
        self._dogru_cevap: str | None = None   # HER görev türünde dolar, doğrulama bunu kullanır
        self._servis = None
        self._baslangic_zamani: float | None = None
        self.dosya_yolu: str | None = None  # 'statik_dosya' görevlerinde dolar (örn. john)
        self.gercek_port: int | None = None  # port çakışması olursa değişebilir, arayüz bunu gösterir
        # 'tuzak_kaydi' görevleri (CarotPot laboratuvarı): öğrenciye özgü kullanıcı
        # adı ve tuzak başına gereken giriş denemesi sayısı.
        self.tuzak_kullanici: str | None = None
        self.tuzak_gerekli = 1
        # 'uretec' görevleri: senaryo/ipucu yer tutucuları ({dosya}, {port}...)
        self.uretim_degiskenleri: dict[str, str] = {}
        self._son_mesaj_no = 0  # sohbette en son görülen mesaj numarası
        # Bireysel mod: öğretmen adresi boşsa hiçbir ağ isteği YAPILMAZ.
        # Bireysel pratik hiçbir zaman öğretmen sunucusuna bağımlı olmamalı.
        self.bireysel_mod = not self.ogretmen_adres
        # Secili zorluk (kolay/orta/zor). Gorev 'zorluklar' icermiyorsa
        # etkisizdir -- servis kendi varsayilanlarini kullanir.
        self.zorluk = "orta"
        # Sinif modunda ogretmenin her acik goreve atadigi zorluk;
        # acik_gorevleri_getir() her cagrildiginda tazelenir.
        self._acik_zorluklar: dict[str, str] = {}
        # "Soru Olustur" ozel parametreleri: gorev_id -> param sozlugu (onbellek).
        self._acik_ozel: dict[str, dict] = {}
        # Ogretmenin her goreve atadigi SORU VARYANTI (gorev_id -> numara); sinifta
        # herkes ayni varyanti cozer. Aktif gorevin varyanti: bos/None ise
        # (bireysel calisma) uretec zorluga uygun rastgele bir varyant secer.
        self._acik_varyantlar: dict[str, int] = {}
        self.varyant: int | None = None
        # Aktif gorevin ozel parametreleri (None ise isimli zorluk kullanilir).
        self.ozel_parametreler = None
        # "IP ve Adres": ogretmenin sinifa uyguladigi hedef loopback adresi
        # (yoksa None -> gorevin kendi 127.0.0.1'i kullanilir).
        self.sinif_hedef_adres = None
        self.gercek_bind_adres = "127.0.0.1"
        # Ayar surumu (hedef adres vb.). Degisince mevcut soru yeniden yuklenir.
        self.ayar_surumu = 0
        self._yuklu_ayar_surumu = 0
        # Ogretmenin atadigi guncel soru sira numarasi (0 = henuz yok).
        self.aktif_soru_no = 0
        # Su an YUKLU olan sorunun numarasi -- yeni soru algilamasinda kullanilir.
        self._yuklu_soru_no = 0

    # ------------------------------------------------------------------
    # Görev yükleme ve yerel servis başlatma
    # ------------------------------------------------------------------
    def _zorluk_parametreleri(self) -> dict:
        """Secili zorluk icin parametre on-ayarini doner. Gorevde
        'zorluklar' yoksa (henuz parametrik yapilmamis arac) bos sozluk
        doner -> servis kendi varsayilanlarini kullanir (eski davranis)."""
        # Ogretmen "Soru Olustur" ile ozel parametre atadiysa dogrudan onu
        # kullan (isimli zorluk on-ayarini atla). '_' ile baslayan ic
        # anahtarlar (orn. _etiket) servise gecmez.
        if self.ozel_parametreler:
            return {k: v for k, v in self.ozel_parametreler.items()
                    if not str(k).startswith("_")}
        if not self.gorev:
            return {}
        zorluklar = self.gorev.get("zorluklar")
        if not isinstance(zorluklar, dict) or not zorluklar:
            return {}
        return zorluklar.get(self.zorluk) or zorluklar.get("orta") or {}

    def aktif_puan(self) -> int:
        """Gorevin puani; zorluga gore degisebilir. puan int ise dogrudan,
        sozluk ise secili zorlugun puani doner."""
        if not self.gorev:
            return 0
        puan = self.gorev.get("puan", 0)
        if isinstance(puan, dict):
            return int(puan.get(self.zorluk) or puan.get("orta") or 0)
        return int(puan or 0)

    def aralik_metni(self) -> str:
        """Senaryo/ipucu metnindeki {aralik} yer tutucusu icin secili
        zorlugun port araligini 'lo-hi' olarak doner (nmap gibi gorevler).
        Uygun degilse bos string."""
        p = self._zorluk_parametreleri()
        ar = (p.get("gizli_port_araligi") or p.get("tuzak_port_araligi")
              or p.get("port_araligi"))
        if ar and len(ar) == 2:
            return f"{ar[0]}-{ar[1]}"
        return ""

    def metin_degiskenleri(self) -> dict[str, str]:
        """Senaryo/ipucu metinlerindeki ek yer tutucular. Şu an yalnızca
        CarotPot laboratuvarı görevleri doldurur ({kullanici}, {tuzaklar},
        {sayi}); diğer görevlerde boş sözlük döner."""
        d: dict[str, str] = {}
        if self.tuzak_kullanici:
            hizmetler = self._zorluk_parametreleri().get("hizmetler") or []
            d.update({
                "{kullanici}": self.tuzak_kullanici,
                "{tuzaklar}": ", ".join(str(h).upper() for h in hizmetler),
                "{sayi}": str(self.tuzak_gerekli),
            })
        if self.dosya_yolu:
            # john-01 ipucundaki <dosya_yolu> ve üreteç görevlerinin {dosya}'sı
            d["<dosya_yolu>"] = self.dosya_yolu
            d["<file_path>"] = self.dosya_yolu
        d.update(self.uretim_degiskenleri)
        return d

    def metni_doldur(self, metin: str) -> str:
        """Senaryo/ipucu metnindeki tüm yer tutucuları ({aralik}, {dosya},
        {port}...) doldurur. Arayüz aynı adımları kendi içinde uygular; bu
        yöntem GTK'siz testler ve ileride tek kaynağa geçiş içindir."""
        aralik = self.aralik_metni()
        if aralik:
            metin = metin.replace("{aralik}", aralik)
        for anahtar, deger in self.metin_degiskenleri().items():
            metin = metin.replace(anahtar, deger)
        return metin

    def aktif_ipucu(self, dil: str) -> str | None:
        """Zorluğa özgü ipucu metni (varsa). sqlmap gibi görevlerde zorluk
        arttıkça ipucu daha az şey ele verir. Görevde/zorlukta tanımlı
        değilse None döner -> arayüz görevin temel ipucunu kullanır."""
        ip = self._zorluk_parametreleri().get("ipucu")
        if isinstance(ip, dict):
            return ip.get(dil) or ip.get("tr")
        return None

    def gorevi_yukle(self, gorev_id: str) -> dict:
        yol = GOREVLER_DIZINI / f"{gorev_id}.json"
        if not yol.exists():
            # test/demo amaçlı: şablon dosyayı da kabul et
            yol = GOREVLER_DIZINI / "sablon-ve-ornek.json"
        self.gorev = json.loads(yol.read_text(encoding="utf-8"))
        return self.gorev

    def gorevi_baslat(self) -> None:
        """Görev türüne göre yerel hedefi üretir ve başlatır.

        flag_uretimi.yontem alanı hangi görev kalıbının kullanılacağını
        belirler:
          - 'parola_uret' : tek portlu sahte giriş servisi (hydra vb.)
          - 'gizli_port'  : çok portlu sahte ağ ortamı (nmap vb.)
        Yeni bir görev türü eklerken buraya yeni bir dal eklenir.
        """
        if self.gorev is None:
            raise RuntimeError("önce gorevi_yukle() çağrılmalı")
        # önceki görevden kalan metin değişkenlerini temizle
        self.tuzak_kullanici = None
        self.uretim_degiskenleri = {}
        self.dosya_yolu = None

        hedef = dict(self.gorev["hedef"])  # kopya -- orijinal gorev bozulmasin
        yontem = self.gorev["flag_uretimi"]["yontem"]
        # Ogretmen "IP ve Adres" ile sinif hedef adresi belirlediyse (loopback
        # 127.x.x.x), butun servisler bu adrese baglanir; degilse gorevin kendi
        # bind_adres'i (127.0.0.1). Her halukarda loopback -- makineyi terk etmez.
        _sinif_adres = getattr(self, "sinif_hedef_adres", None)
        self.gercek_bind_adres = (
            _sinif_adres if (_sinif_adres and loopback_adres_mi(_sinif_adres))
            else hedef.get("bind_adres", "127.0.0.1")
        )
        hedef["bind_adres"] = self.gercek_bind_adres

        if yontem == "parola_uret":
            self.hedef_parola = parola_uret()
            self.gercek_port = _bos_port_bul(hedef["port"])
            self._servis = SahteGirisServisi(
                kullanici=hedef["sabit_kullanici"],
                parola=self.hedef_parola,
                port=self.gercek_port,
                bind_adres=hedef["bind_adres"],
            )
            self._servis.baslat()
            self._dogru_cevap = self.hedef_parola

        elif yontem == "gizli_port":
            p = self._zorluk_parametreleri()
            kw = {}
            if p.get("gizli_port_araligi"):
                kw["gizli_port_araligi"] = tuple(p["gizli_port_araligi"])
            if p.get("gurultu_sayisi") is not None:
                kw["gurultu_sayisi"] = p["gurultu_sayisi"]
            self._servis = SahteAgOrtami(bind_adres=hedef["bind_adres"], **kw)
            self._servis.baslat()
            self._servis.bekle_hazir()  # tüm portlar bağlanana kadar bekle
            self._dogru_cevap = str(self._servis.gizli_port)

        elif yontem == "hash_uret":
            p = self._zorluk_parametreleri()
            basamak = p.get("basamak", 4)  # zorluk tanimli degilse eski davranis
            self.hedef_parola = parola_uret(basamak=basamak)
            self._servis = SahteHashDosyasi(
                kullanici=hedef.get("sabit_kullanici", "ogrenci"),
                parola=self.hedef_parola,
            )
            self._servis.baslat()
            self._dogru_cevap = self.hedef_parola
            self.dosya_yolu = self._servis.dosya_yolu  # öğrenciye gösterilecek gerçek yol

        elif yontem == "sql_flag":
            p = self._zorluk_parametreleri()
            self._dogru_cevap = parola_uret()
            self.gercek_port = _bos_port_bul(hedef["port"])
            kw = {}
            if p.get("tuzak_tablolar") is not None:
                kw["tuzak_tablolar"] = p["tuzak_tablolar"]
            self._servis = SahteWebServisi(
                gizli_deger=self._dogru_cevap,
                port=self.gercek_port,
                bind_adres=hedef["bind_adres"],
                **kw,
            )
            self._servis.baslat()

        elif yontem == "trafik_flag":
            p = self._zorluk_parametreleri()
            self._dogru_cevap = parola_uret()
            self.gercek_port = _bos_port_bul(hedef["port"])
            kw = {}
            if p.get("gurultu") is not None:
                kw["gurultu"] = p["gurultu"]
            if p.get("kodlama"):
                kw["kodlama"] = p["kodlama"]
            self._servis = SahteTrafik(
                flag=self._dogru_cevap,
                port=self.gercek_port,
                bind_adres=hedef["bind_adres"],
                **kw,
            )
            self._servis.baslat()
            self._servis.bekle_hazir()

        elif yontem == "savunma_hedefi":
            # ufw-01: yerel bir dinleyici başlatılır, öğrenci bunu ufw
            # ile bloke etmeyi dener. 'doğru cevap' YOK -- doğrulama
            # ufw_kuralini_dogrula() ile ayrı yapılır, cevabi_kontrol_et()
            # bu görev türünde KULLANILMAZ.
            self.gercek_port = _bos_port_bul(hedef["port"])
            self._servis = BasitDinleyici(
                port=self.gercek_port, bind_adres=hedef["bind_adres"],
            )
            self._servis.baslat()

        elif yontem == "uretec":
            # Üreteç görevleri (günlük analizi, kodlama, adli analiz, web/banner
            # keşfi...): içerik her açılışta rastgele üretilir, doğru cevap
            # üretimle birlikte hesaplanır (bkz. uretilen_gorevler.py).
            fu = self.gorev["flag_uretimi"]
            parametreler = dict(self._zorluk_parametreleri())
            parametreler["_zorluk"] = self.zorluk
            if self.varyant and "varyant" not in parametreler:
                parametreler["varyant"] = self.varyant
            uretim = uretilen_gorevler.uret(
                fu["uretec"], parametreler,
                fu.get("sabit_parametreler"), hedef["bind_adres"])
            self._servis = uretim
            self._dogru_cevap = uretim.dogru_cevap
            self.dosya_yolu = uretim.dosya_yolu
            self.uretim_degiskenleri = dict(uretim.degiskenler)

        elif yontem == "tuzak_kaydi":
            # carotpot-01: öğrencinin makinesinde AYRI bir CarotPot örneği
            # yalnızca loopback'te açılır. Doğrulama onun olay kayıtlarından
            # yapılır (tuzak_kaydini_dogrula); doğru cevap kutusu YOKTUR.
            p = self._zorluk_parametreleri()
            self.tuzak_kullanici = "ziyaretci-" + secrets.token_hex(2)
            self.tuzak_gerekli = int(p.get("gerekli_giris", 1))
            self._servis = TuzakLab(
                bind_adres=hedef["bind_adres"],
                hizmetler=p.get("hizmetler") or ["ftp"],
                port_araligi=tuple(p.get("tuzak_port_araligi") or (21000, 21999)),
            )
            self._servis.baslat()

        elif yontem == "sistem_kontrolu":
            # fail2ban-01: hiç yerel servis YOK, gerçek sistem aracının
            # (fail2ban) durumu okunur. Doğrulama fail2ban_durumunu_dogrula()
            # ile ayrı yapılır.
            self._servis = None

        else:
            raise ValueError(f"bilinmeyen flag_uretimi yöntemi: '{yontem}'")

        self._baslangic_zamani = time.time()
        self._bildir("basladi")

    def gorevi_durdur(self) -> None:
        if self._servis:
            self._servis.durdur()
            self._servis = None

    # ------------------------------------------------------------------
    # Cevap doğrulama — YEREL, ağa doğru cevap gitmez
    # ------------------------------------------------------------------
    def cevabi_kontrol_et(self, girilen_cevap: str, ipucu_kullanildi: bool = False) -> bool:
        dogru = girilen_cevap.strip() == str(self._dogru_cevap).strip()
        gecen_sure = int(time.time() - (self._baslangic_zamani or time.time()))
        kazanilan = 0
        if dogru:
            kazanilan = self.aktif_puan()
            if ipucu_kullanildi:  # ipucu aciksa yari puan
                kazanilan = int(round(kazanilan * (1 - IPUCU_CEZASI_ORANI)))
        self._bildir("tamamlandi" if dogru else "yanlis_denedi", gecen_sure,
                     cevap=girilen_cevap.strip(), puan=kazanilan)
        return dogru

    # ------------------------------------------------------------------
    # Savunma görevleri (ufw-01, fail2ban-01) doğrulaması -- root
    # gerektirir, "kullanici_girdisi" yöntemine göre AYRI ele alınır.
    # ------------------------------------------------------------------
    def _otomatik_tamamla(self, gecen_sure: int, ozet: str) -> None:
        """Cevap kutusu olmayan görevler (ufw, fail2ban, CarotPot laboratuvarı)
        için 'tamamlandi' bildirimi. Puan ve soru numarası öğretmen skoruna
        yansısın diye cevap alanı kısa bir özetle gönderilir."""
        self._bildir("tamamlandi", gecen_sure, cevap=ozet, puan=self.aktif_puan())

    def ufw_kuralini_dogrula(self, sudo_parolasi: str) -> tuple[bool, str]:
        """ufw-01: `sudo ufw status` çıktısını okur, hedef port için bir
        DENY/REJECT kuralı var mı diye bakar. Bilinçli tasarım: gerçek
        bağlantı denemesi yerine KURALIN VARLIĞINI kontrol ediyoruz --
        loopback trafiğinin ufw tarafından gerçekten kesilip kesilmediği
        sisteme göre değişiyor (bkz. devir belgesi), ama kuralın eklenmiş
        olması her sistemde aynı şekilde doğrulanabilir. (basarili, mesaj)
        döner; basarisizsa mesaj öğrenciye gösterilecek açıklamadır."""
        basarili, cikti, hata = sudo_ile_calistir(["ufw", "status"], sudo_parolasi)
        if not basarili:
            self._bildir("yanlis_denedi")
            return False, hata or "ufw status okunamadı (yanlış parola olabilir)"

        port_str = str(self.gercek_port)
        kural_var = any(
            satir.split()[0].split("/")[0] == port_str and
            ("DENY" in satir.upper() or "REJECT" in satir.upper())
            for satir in cikti.splitlines() if satir.strip()
        )
        if kural_var:
            gecen_sure = int(time.time() - (self._baslangic_zamani or time.time()))
            self._otomatik_tamamla(gecen_sure, f"ufw: {port_str} engellendi")
            return True, "Kural bulundu: port engellenmiş."
        self._bildir("yanlis_denedi")
        return False, (
            f"'{port_str}' portu için bir DENY/REJECT kuralı bulunamadı. "
            f"Terminalde 'sudo ufw deny {port_str}' çalıştırdın mı?"
        )

    def fail2ban_durumunu_dogrula(self, sudo_parolasi: str) -> tuple[bool, str]:
        """fail2ban-01: `sudo fail2ban-client status <jail>` çalıştırır.
        Özel bir jail/filtre YAZMAZ -- sadece görev dosyasında belirtilen
        (genelde önceden var olan) jail'in durumunu okur. Komutun
        başarıyla dönmesi ve beklenen başlığı içermesi yeterli sayılır."""
        jail = self.gorev["hedef"]["jail"] if self.gorev else ""
        basarili, cikti, hata = sudo_ile_calistir(
            ["fail2ban-client", "status", jail], sudo_parolasi,
        )
        if basarili and "status for the jail" in cikti.lower():
            gecen_sure = int(time.time() - (self._baslangic_zamani or time.time()))
            self._otomatik_tamamla(gecen_sure, f"fail2ban: {jail}")
            return True, cikti.strip()
        self._bildir("yanlis_denedi")
        return False, hata or (
            f"'{jail}' jail'inin durumu okunamadı. fail2ban kurulu ve "
            f"'{jail}' jail'i etkin mi?"
        )

    def tuzak_kaydini_dogrula(self, dil: str = "tr") -> tuple[bool, str]:
        """carotpot-01: laboratuvar CarotPot'unun olay kayıtlarında, öğrencinin
        kullanıcı adıyla her tuzak için yeterli sayıda giriş denemesi var mı?
        (basarili, mesaj) döner. Cevap ağa gitmez, kayıtlar yerel okunur."""
        lab = self._servis
        if not isinstance(lab, TuzakLab) or not self.tuzak_kullanici:
            return False, ("Laboratuvar çalışmıyor." if dil == "tr"
                           else "The lab is not running.")
        if not lab.calisiyor_mu():
            return False, ("Laboratuvar durmuş; görevi yeniden başlat." if dil == "tr"
                           else "The lab has stopped; restart the task.")
        sayim = {ad: 0 for ad in lab.hizmetler}
        for o in lab.olaylar(tur="giris", kullanici=self.tuzak_kullanici):
            if o["hizmet"] in sayim:
                sayim[o["hizmet"]] += 1
        ozet = ", ".join(f"{ad.upper()} {min(n, self.tuzak_gerekli)}/{self.tuzak_gerekli}"
                         for ad, n in sayim.items())
        if all(n >= self.tuzak_gerekli for n in sayim.values()):
            gecen_sure = int(time.time() - (self._baslangic_zamani or time.time()))
            self._otomatik_tamamla(gecen_sure, ozet)
            return True, (f"CarotPot kayıtlarında bulundu: {ozet}" if dil == "tr"
                          else f"Found in the CarotPot records: {ozet}")
        self._bildir("yanlis_denedi", cevap=ozet)
        return False, (f"Henüz yeterli kayıt yok ({ozet}). Tuzaklara "
                       f"'{self.tuzak_kullanici}' kullanıcı adıyla giriş dene."
                       if dil == "tr" else
                       f"Not enough records yet ({ozet}). Try logging in to the "
                       f"traps as '{self.tuzak_kullanici}'.")

    # ------------------------------------------------------------------
    # Öğretmen sunucusuyla iletişim
    # ------------------------------------------------------------------
    def _istek(self, yol: str, gövde: dict, yontem: str = "POST") -> tuple[int, dict]:
        veri = json.dumps(gövde).encode("utf-8")
        r = urllib.request.Request(
            self.ogretmen_adres + yol, data=veri, method=yontem,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(r, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
        except urllib.error.URLError as e:
            if isinstance(e.reason, ConnectionRefusedError):
                raise OdaKapaliHatasi(
                    f"öğretmen sunucusuna bağlantı reddedildi (oda kapanmış olabilir): {e}"
                ) from e
            raise BaglantiHatasi(f"öğretmen sunucusuna ulaşılamıyor: {e}") from e

    def _bildir(self, durum: str, sure_sn: float = 0, cevap: str | None = None,
                puan: int | None = None) -> None:
        if self.bireysel_mod:
            # Bireysel modda öğretmen sunucusu yok, ama ilerleme
            # kaybolmasın diye kalıcı yerel deftere yazılır (bkz.
            # gecmis_defteri.py). Sadece 'tamamlandi' olaylarında puan
            # kaydedilir -- diğer durumlarda görevin puanı henüz
            # kazanılmamış demektir.
            if self.gorev is not None:
                gecmis_defteri.kaydet(
                    gorev_id=self.gorev.get("id", "?"),
                    arac=self.gorev.get("arac", "?"),
                    durum=durum,
                    sure_sn=sure_sn,
                    puan=(puan if puan is not None
                          else (self.aktif_puan() if durum == "tamamlandi" else 0)),
                )
            return
        try:
            yuk = {
                "ogrenci": self.ogrenci_adi,
                "sifre": self.oda_sifre,
                "gorev_id": self.gorev["id"] if self.gorev else "?",
                "durum": durum,
                "sure_sn": sure_sn,
            }
            # Gerçek bir cevap denemesiyse öğretmenin "Verdiği Cevaplar"
            # penceresi için cevabı ve yüklü sorunun numarasını da gönder.
            if cevap is not None:
                yuk["cevap"] = cevap
                yuk["soru_no"] = self._yuklu_soru_no
            if puan is not None:
                yuk["puan"] = puan
            self._istek("/ilerleme", yuk)
        except BaglantiHatasi:
            pass  # ağ sorunu görevi engellemez, sadece skor gecikir

    def katil(self) -> tuple[bool, str]:
        """Odaya katılmayı dener -- şifre ve isim çakışması kontrolü
        burada yapılır. (basarili, hata_mesaji) döner; başarılıysa
        hata_mesaji boş string olur."""
        try:
            durum, cevap = self._istek("/katil", {
                "ogrenci": self.ogrenci_adi,
                "sifre": self.oda_sifre,
            })
        except BaglantiHatasi:
            # Sabit Türkçe metin yerine bir isaret kodu donduruyoruz --
            # arayuz katmani (ogrenci_uygulama.py) bunu kendi dilinde
            # gosterir. Bu istemci sinifi GTK'dan bagimsiz, hangi dilde
            # calisildigini bilmiyor.
            return False, "__BAGLANTI_HATASI__"

        if durum == 200:
            return True, ""
        return False, cevap.get("mesaj") or cevap.get("hata", "Bilinmeyen hata")

    def acik_gorevleri_getir(self) -> list[str]:
        """Öğretmen sunucusuna hangi görev(ler)in açık olduğunu sorar.

        Oda koduna/şifresine bakılmaksızın herkese açık bir bilgi --
        öğrenci katılmadan önce bunu bilmesi gerekiyor.
        """
        _, cevap = self._istek("/gorevler", {}, "GET")
        self._acik_zorluklar = cevap.get("zorluklar", {}) or {}
        self._acik_ozel = cevap.get("parametreler", {}) or {}
        self._acik_varyantlar = {k: int(v) for k, v in (cevap.get("varyantlar", {}) or {}).items()}
        self.sinif_hedef_adres = cevap.get("hedef_adres") or None
        self.ayar_surumu = int(cevap.get("ayar_surumu", 0) or 0)
        self.aktif_soru_no = int(cevap.get("aktif_soru_no", 0) or 0)
        return cevap.get("acik_gorevler", [])

    def atanan_zorluk(self, gorev_id: str) -> str:
        """Ogretmenin bu goreve atadigi zorlugu doner. acik_gorevleri_getir()
        en son cagrildiginda alinan bilgiye dayanir; bilinmiyorsa 'orta'."""
        z = self._acik_zorluklar.get(gorev_id, "orta")
        return z if z in ("kolay", "orta", "zor") else "orta"

    def atanan_varyant(self, gorev_id: str) -> int | None:
        """Ogretmenin bu goreve atadigi soru varyanti (yoksa None).
        acik_gorevleri_getir() en son cagrildiginda alinan bilgiye dayanir."""
        v = self._acik_varyantlar.get(gorev_id)
        return v if v else None

    def atanan_parametreler(self, gorev_id: str):
        """Ogretmenin bu goreve 'Soru Olustur' ile atadigi OZEL parametreler.
        Yoksa None -> isimli zorluk on-ayari kullanilir. acik_gorevleri_getir()
        en son cagrildiginda alinan bilgiye dayanir."""
        p = self._acik_ozel.get(gorev_id)
        return dict(p) if isinstance(p, dict) and p else None

    def sinif_baglanti_durumu(self) -> str:
        """Öğretmenle bağlantının durumunu tek bir sözcükle döner --
        periyodik döngüde her turda çağrılır:

          'aktif'       -- hâlâ sınıftayım, her şey normal.
          'atildi'      -- sunucu YAŞIYOR ama öğretmen '✕' ile beni
                           sınıf listesinden çıkardı.
          'oda_kapandi' -- sunucuya KESİN OLARAK ulaşılamıyor (connection
                           refused) -- öğretmen uygulamayı kapattı.
          'belirsiz'    -- geçici bir ağ sorunu (zaman aşımı vb.).
                           Hiçbir şey yapma, bir sonraki turda tekrar dene.

        Bireysel modda hep 'aktif' döner -- öğretmen kavramı yok."""
        if self.bireysel_mod:
            return "aktif"
        try:
            _, cevap = self._istek(
                f"/aktif_mi?ogrenci={self.ogrenci_adi}", {}, "GET",
            )
            return "aktif" if cevap.get("aktif", True) else "atildi"
        except OdaKapaliHatasi:
            return "oda_kapandi"
        except BaglantiHatasi:
            return "belirsiz"

    def gorev_degisti_mi(self) -> str | None:
        """Öğretmen 'Sıradaki Göreve Geç' dediğinde, ZATEN BAĞLI olan
        öğrencinin bunu fark etmesi için periyodik olarak çağrılır.

        Mevcut görev artık açık görevler arasında değilse ve yerine
        BAŞKA bir görev açıksa, o yeni görevin id'sini döner (öğrenci
        arayüzü bunu görünce otomatik geçiş yapar). Değişiklik yoksa
        None döner. Bireysel modda hiç çağrılmamalı."""
        if self.bireysel_mod or self.gorev is None:
            return None
        try:
            acik = self.acik_gorevleri_getir()  # self.aktif_soru_no'yu tazeler
        except BaglantiHatasi:
            return None
        # Yeni bir soru atandi mi? Sira numarasi yukledigim sorudan farkliysa
        # ogretmen yeni soru atamistir: baska gorev, ayni gorev farkli zorluk,
        # ya da "Soru Olustur" ozel parametresi -- hepsi numarayi artirir.
        # Yeni soru (numara) YA DA mevcut sorunun ayarlari (hedef adres
        # vb.) degistiyse yeniden yukle. Ikincisinde soru numarasi ayni kalir
        # ama ayar_surumu artmistir.
        if acik and (self.aktif_soru_no != self._yuklu_soru_no
                     or self.ayar_surumu != self._yuklu_ayar_surumu):
            return acik[0]
        return None

    def gorevi_degistir(self, yeni_gorev_id: str) -> dict:
        """Mevcut yerel servisi durdurur, yeni görevi yükleyip başlatır.
        Öğretmen sınıfı başka bir göreve geçirdiğinde çağrılır."""
        self.gorevi_durdur()
        gorev = self.gorevi_yukle(yeni_gorev_id)
        self.gorevi_baslat()
        self._yuklu_soru_no = self.aktif_soru_no  # bu soruyu yukledim
        self._yuklu_ayar_surumu = self.ayar_surumu
        return gorev

    def yeni_mesajlari_getir(self) -> list:
        """Öğretmenden (ve tüm sınıftan) gelen YENİ mesajları çeker.
        Kendi gönderdiklerini de içerir ama arayüz onları zaten gösterdi;
        son_no takibi sayesinde her mesaj bir kez döner."""
        if self.bireysel_mod:
            return []  # bireysel modda öğretmen yok, mesaj gelmez
        try:
            _, cevap = self._istek(
                f"/sohbet?ogrenci={self.ogrenci_adi}&son_no={self._son_mesaj_no}",
                {}, "GET",
            )
            mesajlar = cevap.get("mesajlar", [])
            if mesajlar:
                self._son_mesaj_no = max(m["no"] for m in mesajlar)
            return mesajlar
        except BaglantiHatasi:
            return []

    def mesaj_gonder(self, metin: str) -> bool:
        """Öğrenci öğretmene mesaj yazar (çift yönlü sohbet)."""
        try:
            self._istek("/mesaj", {
                "ogrenci": self.ogrenci_adi,
                "kimden": "ogrenci",
                "metin": metin,
            })
            return True
        except BaglantiHatasi:
            return False
