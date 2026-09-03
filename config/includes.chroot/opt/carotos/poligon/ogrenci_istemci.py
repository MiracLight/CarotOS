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
import sys
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flag_uretici import parola_uret  # noqa: E402
from servisler.sahte_giris import SahteGirisServisi  # noqa: E402
from servisler.sahte_ag import SahteAgOrtami
from servisler.sahte_hash import SahteHashDosyasi
from servisler.sahte_web import SahteWebServisi
from servisler.sahte_trafik import SahteTrafik  # noqa: E402
from servisler.sahte_savunma_hedefi import BasitDinleyici  # noqa: E402
import gecmis_defteri  # noqa: E402

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
        self._son_mesaj_no = 0  # sohbette en son görülen mesaj numarası
        # Bireysel mod: öğretmen adresi boşsa hiçbir ağ isteği YAPILMAZ.
        # Bireysel pratik hiçbir zaman öğretmen sunucusuna bağımlı olmamalı.
        self.bireysel_mod = not self.ogretmen_adres

    # ------------------------------------------------------------------
    # Görev yükleme ve yerel servis başlatma
    # ------------------------------------------------------------------
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

        hedef = self.gorev["hedef"]
        yontem = self.gorev["flag_uretimi"]["yontem"]

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
            self._servis = SahteAgOrtami(bind_adres=hedef["bind_adres"])
            self._servis.baslat()
            self._servis.bekle_hazir()  # tüm portlar bağlanana kadar bekle
            self._dogru_cevap = str(self._servis.gizli_port)

        elif yontem == "hash_uret":
            self.hedef_parola = parola_uret()
            self._servis = SahteHashDosyasi(
                kullanici=hedef.get("sabit_kullanici", "ogrenci"),
                parola=self.hedef_parola,
            )
            self._servis.baslat()
            self._dogru_cevap = self.hedef_parola
            self.dosya_yolu = self._servis.dosya_yolu  # öğrenciye gösterilecek gerçek yol

        elif yontem == "sql_flag":
            self._dogru_cevap = parola_uret()
            self.gercek_port = _bos_port_bul(hedef["port"])
            self._servis = SahteWebServisi(
                gizli_deger=self._dogru_cevap,
                port=self.gercek_port,
                bind_adres=hedef["bind_adres"],
            )
            self._servis.baslat()

        elif yontem == "trafik_flag":
            self._dogru_cevap = parola_uret()
            self.gercek_port = _bos_port_bul(hedef["port"])
            self._servis = SahteTrafik(
                flag=self._dogru_cevap,
                port=self.gercek_port,
                bind_adres=hedef["bind_adres"],
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
    def cevabi_kontrol_et(self, girilen_cevap: str) -> bool:
        dogru = girilen_cevap.strip() == str(self._dogru_cevap).strip()
        gecen_sure = int(time.time() - (self._baslangic_zamani or time.time()))
        self._bildir("tamamlandi" if dogru else "yanlis_denedi", gecen_sure)
        return dogru

    # ------------------------------------------------------------------
    # Savunma görevleri (ufw-01, fail2ban-01) doğrulaması -- root
    # gerektirir, "kullanici_girdisi" yöntemine göre AYRI ele alınır.
    # ------------------------------------------------------------------
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
            self._bildir("tamamlandi", gecen_sure)
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
            self._bildir("tamamlandi", gecen_sure)
            return True, cikti.strip()
        self._bildir("yanlis_denedi")
        return False, hata or (
            f"'{jail}' jail'inin durumu okunamadı. fail2ban kurulu ve "
            f"'{jail}' jail'i etkin mi?"
        )

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

    def _bildir(self, durum: str, sure_sn: float = 0) -> None:
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
                    puan=self.gorev.get("puan", 0) if durum == "tamamlandi" else 0,
                )
            return
        try:
            self._istek("/ilerleme", {
                "ogrenci": self.ogrenci_adi,
                "sifre": self.oda_sifre,
                "gorev_id": self.gorev["id"] if self.gorev else "?",
                "durum": durum,
                "sure_sn": sure_sn,
            })
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
        return cevap.get("acik_gorevler", [])

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
            acik = self.acik_gorevleri_getir()
        except BaglantiHatasi:
            return None
        mevcut = self.gorev["id"]
        if mevcut in acik:
            return None  # hâlâ aynı görev açık, değişiklik yok
        if acik:
            return acik[0]  # öğretmen başka bir göreve geçti
        return None  # öğretmen her şeyi kapattı, mevcut görevde kalınır

    def gorevi_degistir(self, yeni_gorev_id: str) -> dict:
        """Mevcut yerel servisi durdurur, yeni görevi yükleyip başlatır.
        Öğretmen sınıfı başka bir göreve geçirdiğinde çağrılır."""
        self.gorevi_durdur()
        gorev = self.gorevi_yukle(yeni_gorev_id)
        self.gorevi_baslat()
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
