# CarotOS — Uygulama Geliştirme Standartları

**Amaç:** Yeni bir CarotOS uygulaması yazarken (ya da mevcut birini
değiştirirken) altı uygulamanın hepsinin paylaştığı desenleri korumak.
Bu belge **mevcut koddan türetildi**, tasarım önerisi değil — "böyle olsun"
değil, "zaten böyle" anlatır.

**Kapsadığı uygulamalar:** Güvenlik Paneli, Karşılama Sihirbazı, Sistem
Sağlığı, USB Denetimi, CarotOS Poligon (öğrenci), CarotOS Poligon Öğretmen.

---

## 1. TEMEL YAPI

### 1.1 Teknoloji

- **Python 3 + PyGObject (GTK 3)** — istisnasız. Qt, Tkinter, web tabanlı
  arayüz kullanılmaz.
- Harici Python bağımlılığı **eklenmez**; Debian deposunda olmayan bir
  kütüphaneye ihtiyaç duyuluyorsa önce alternatif aranır (ISO boyutu ve
  bağımlılık yönetimi için).
- Dosyanın başında shebang + modül docstring:

```python
#!/usr/bin/env python3
"""
CarotOS <Uygulama Adi> -- kisa aciklama.

Neyi neden yaptigini anlatan birkac satir. Tasarim kararlari varsa
(ornegin "X yerine Y secildi cunku...") burada belirtilir.
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa: E402
```

### 1.2 Dosya konumu

```
config/includes.chroot/opt/carotos/<uygulama-adi>/<uygulama-adi>.py
config/includes.chroot/usr/share/applications/carotos-<ad>.desktop
config/includes.chroot/usr/share/icons/hicolor/256x256/apps/carotos-<ad>.png
```

Panel kısayolu da isteniyorsa ek olarak `/etc/skel/.config/xfce4/panel/
launcher-N/` + `xfce4-panel.xml` düzenlemesi (bkz. İşletim Rehberi 4.4).

### 1.3 Sürüm sabiti

```python
APP_VERSION = "1.1"
APP_CODENAME = "Eggshell"   # gerekiyorsa
```

Sürüm yükseltmelerinde bu sabit **elle** güncellenir (şu an merkezi bir
sürüm kaynağı yok — bilinen teknik borç).

---

## 2. İKİ DİLLİLİK — ZORUNLU

Her uygulama **Türkçe ve İngilizce** çalışır. Desen:

### 2.1 METIN sözlüğü

```python
METIN = {
    "tr": {
        "baslik": "CarotOS Uygulama Adi",
        "kaydet": "Kaydet",
        "hata_alan": "Tüm alanları doldur",
    },
    "en": {
        "baslik": "CarotOS Application Name",
        "kaydet": "Save",
        "hata_alan": "Fill in all fields",
    },
}
```

**Kurallar:**
- Anahtar adları **Türkçe ve açıklayıcı** (`hata_baglanti`, `oda_kodu`),
  İngilizce değil.
- İki sözlükte de **aynı anahtar seti** bulunur. Birine ekleyip diğerine
  eklememek sessiz bir hataya yol açar (`KeyError` ya da eksik metin).
- Uzun metinler satır bölerek yazılır, string birleştirme ile:
  ```python
  "aciklama": "Uzun bir metin burada başlar ve "
              "ikinci satırda devam eder.",
  ```

### 2.2 Açılış dili

```python
def _sistem_dilini_belirle() -> str:
    """Sistem dili Türkçe ise 'tr', başka bir dilse (ya da hiç
    belirlenemiyorsa) 'en'. GTK/gettext'in kullandığı standart öncelik
    sırası. Kullanıcı arayüzden değiştirebilir; bu sadece açılış
    varsayılanı."""
    for degisken in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        if os.environ.get(degisken, "").lower().startswith("tr"):
            return "tr"
    return "en"
```

Pencere `__init__` içinde: `self.dil = _sistem_dilini_belirle()`

### 2.3 Dil değiştirme düğmesi

Sağ üst köşede, mevcut dilin **karşıtını** gösteren bir düğme:

```python
self.dil_dugmesi = Gtk.Button(label="EN")
self.dil_dugmesi.get_style_context().add_class("duz-sabit")
self.dil_dugmesi.connect("clicked", self._dili_degistir)
# _metinleri_uygula() içinde:
self.dil_dugmesi.set_label("TR" if self.dil == "en" else "EN")
```

### 2.4 `_metinleri_uygula()` deseni — kritik

**Tüm görünen metinler tek bir metotta atanır**, widget oluşturulurken
değil. Bu sayede dil değişince tek çağrıyla her şey güncellenir.

```python
def _metinleri_uygula(self):
    m = METIN[self.dil]
    self.set_title(m["baslik"])
    self.baslik_etiketi.set_text(m["baslik"])
    self.kaydet_dugmesi.set_label(m["kaydet"])
    self.ad_girisi.set_placeholder_text(m["ad"])
    # ... her metin burada

def _dili_degistir(self, _dugme):
    self.dil = "en" if self.dil == "tr" else "tr"
    self._metinleri_uygula()
```

**Yeni bir widget eklerken metnini `_metinleri_uygula()` içine eklemeyi
unutma** — yoksa dil değişince o widget eski dilde kalır. (Bu, Poligon'da
bir kez yaşandı.)

---

## 3. GÖRSEL KİMLİK — ORTAK GRAFİT TEMA

CarotOS sistem uygulamaları (Karşılama, Mağaza, Sistem Sağlığı, Carotene, USB
Denetimi, Güvenlik Paneli, CarotPot) **tek bir ortak tema modülünü** kullanır:
`opt/carotos/ortak/tema.py`. Renk, CSS ve ortak parçalar orada tanımlıdır;
uygulama kendi CSS'ini **yazmaz**, yalnızca kendi **vurgu rengini** seçer.

- **Koyu/açık görünüm vardır** ve kullanıcı değiştirebilir (eski "sabit
  lacivert" kararı kalktı). Koyu varsayılandır.
- Zemin/kart/yazı tonları **tüm uygulamalarda ortak**; uygulamayı ayıran tek
  şey vurgu rengidir.
- Durum renkleri (kırmızı, sarı, yeşil…) **anlam taşır**, uygulamadan
  bağımsızdır; vurgu olarak kullanılmaz.
- Gerekli paket: `python3-gi-cairo` (tema cairo/PangoCairo ile çizim yapar;
  `carotos.list.chroot` içinde).

### 3.1 Vurgu renkleri

`tema.VURGULAR` sözlüğünde tutulur; yeni uygulama için oraya **bir satır**
eklenir.

| Uygulama | Anahtar | Renk |
|---|---|---|
| CarotPot | `carotpot` | mor `#8b7fd6` |
| Sistem Sağlığı | `health` | nane yeşili `#4fb38a` |
| Carotene | `carotene` | havuç turuncusu `#ff8a3d` |
| USB Denetimi | `usb` | camgöbeği `#3ec7c0` |
| Güvenlik Paneli | `guvenlik` | kehribar `#e3a33b` |
| Karşılama | `karsilama` | marka mavisi `#378ada` (web sitesiyle ortak) |
| Mağaza | `magaza` | pembe `#d16ba5` |

### 3.2 Uygulama iskeleti

```python
ORTAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ortak")
sys.path.insert(0, ORTAK)
import tema

tema.uygula(gorunum, "carotene")          # "dark" | "light", vurgu anahtarı
self.kabuk = tema.Kabuk(logo_yolu, bolumler, sayfa_secildi)
# bolumler: [("koruma", [("scan", "arama"), ("quarantine", "kilit")]), ...]
self.add(self.kabuk)
self.kabuk.marka_ayarla(ad, alt_ad)       # sol üst marka
self.kabuk.ust_sag.pack_start(...)        # sağ üst: durum hapı, düğmeler
self.kabuk.yan_alt.pack_start(...)        # sol alt: dil ve görünüm düğmeleri
self.kabuk.baslik_ayarla(baslik, alt)     # sayfa başlığı
self.kabuk.icerik(govde)                  # kaydırılabilir içerik
self.kabuk.bildir(metin, "basari")        # alt bildirim şeridi: bilgi/basari/hata
self.kabuk.rozet("sayfa", "3")            # menü sayacı
```

Hazır parçalar: `kart`, `kart_basligi`, `etiket`, `rozet`, `dugme`,
`secim_grubu`, `not_kutusu`, `bos_durum`, `KpiKutusu`, `DurumHapi`,
`CizimAlani`, `Ikon`, `ikon_kutusu`, `cubuk_grafik`, `yatay_cubuklar`,
`halka`, `onay_sor`. Yeni bir parça gerekiyorsa uygulamaya değil **ortak
modüle** eklenir.

**Dil/görünüm değişince:** `tema.uygula(yeni_gorunum, vurgu)` yeniden
çağrılır, sayfa yeniden kurulur. Çizim fonksiyonları renkleri
`tema.AKTIF` paletinden okur; elle renk yazma.

### 3.3 CSS sınıfları

Sınıf adları **Türkçe ve açıklayıcıdır**. Sık kullanılanlar:

| Sınıf | Kullanım |
|---|---|
| `.kart` (+ `.vurgulu`, `.tehlikeli`) | İçerik kutusu: zemin, 12px köşe, ince kenar |
| `.kart-baslik` / `.kart-alt` | Kart başlığı / soluk açıklama |
| `.soluk`, `.silik` | İkincil / çok soluk metin |
| `.mono` | Monospace, soluk (yol, komut) |
| `.buyuk-baslik` | Büyük başlık |
| `.kpi-deger`, `.kpi-ad` | Büyük sayı ve adı |
| `.rozet` + `.r-kirmizi/-sari/-yesil/-vurgu/-mavi/-gri` | Küçük durum etiketi |
| `.not` + `.not-bilgi/-uyari/-hata/-basari` | Renkli bilgi kutusu |
| `.durum-hap` + `.hap-acik/-kapali/-uyari/-hata` | Üst sağ durum göstergesi |
| `button.ana`, `button.tehlike`, `button.duz`, `button.kucuk`, `button.secim` | Düğme türleri |
| `.basari-yazi`, `.hata-yazi`, `.uyari-yazi`, `.vurgu-yazi` | Renkli yazı |

Uygulamaya özgü sınıf gerekirse **ek bir `Gtk.CssProvider`** eklenir
(`Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1` ile, ortak temanın üstünde) ve
renkler `tema.AKTIF`/`tema.palet` üzerinden yazılır. Kart dolgusunu
`set_border_width` ile **verme**: GTK bunu kartın dışına boşluk olarak
uygular; iç boşluk için CSS `padding` ya da iç kutuya `margin` kullan.

**İzleme/arka plan modu olan uygulamalarda** (ör. USB Denetimi `--monitor`)
`tema` ve Gtk **ilk pencere açılırken** içe aktarılır; arka plan süreci Gtk'yi
hiç yüklemez.

### 3.4 Pencere ikonu

```python
try:
    self.set_icon_from_file(
        "/usr/share/icons/hicolor/256x256/apps/carotos-<ad>.png"
    )
except GLib.Error:
    pass  # ISO disinda calistirilirsa ikon bulunamayabilir -- cokme yok
```

`try/except` **zorunlu** — uygulama ISO dışında (depodan doğrudan)
çalıştırıldığında ikon yoktur, bu yüzden çökmemeli.

### 3.5 Çok sayfalı arayüz

Birden fazla ekran varsa `Gtk.Stack` kullanılır:

```python
self.yigin = Gtk.Stack()
self.yigin.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
# ...
self.yigin.set_visible_child_name("sayfa_adi")
```

Kenar menülü uygulamalarda sayfa geçişini `tema.Kabuk` yapar (`yigin`
gerekmez); sihirbaz gibi adım adım akışlarda (Karşılama) `Gtk.Stack` kalır.

### 3.6 İstisna: Poligon

Poligon (eğitim oyunu) **şimdilik** eski lacivert paletini kullanır
(`#0b2e52` zemin, `#123a63` kart, `#378ada` vurgu; web sitesiyle ortak).
Poligon'un temasının ortak grafit temaya mı taşınacağı, yoksa kendi kimliğini
mi koruyacağı **ayrıca kararlaştırılır** (CarotPot entegrasyonuyla birlikte).
O zamana kadar Poligon'a ortak tema uygulanmaz.

---

## 4. YETKİ YÜKSELTME — KIRMIZI ÇİZGİ

**Uygulama asla kendiliğinden root olmaz.** İki kabul edilen yöntem:

### 4.1 `pkexec` (Güvenlik Paneli deseni)
Grafik bir yetki istemi açar, tek seferlik komut çalıştırır.

### 4.2 `sudo -S -k` + parola penceresi (Poligon deseni)

```python
def sudo_ile_calistir(komut: list[str], parola: str, zaman_asimi: float = 10):
    """Parolayi stdin'den verir; sudo'nun tty/timestamp onbellegine
    guvenilmez. SADECE sabit tanimli komutlar icin -- cagiran taraf
    komut listesini kendisi yazar, kullanicidan gelen serbest metin
    ASLA calistirilmaz."""
    sonuc = subprocess.run(
        ["sudo", "-S", "-k", *komut],
        input=parola + "\n", capture_output=True, text=True,
        timeout=zaman_asimi,
    )
    return sonuc.returncode == 0, sonuc.stdout, sonuc.stderr
```

**Kurallar:**
- Komut listesi **kodda sabit** yazılır. Kullanıcı girdisi komuta
  dönüştürülmez.
- Parola istemi **açık** olur (kullanıcı ne için istendiğini görür).
- Komut **arka planda** (thread) çalışır, arayüz donmaz:
  ```python
  threading.Thread(target=arka_planda, daemon=True).start()
  # sonucu GLib.idle_add(...) ile arayüze döndür
  ```

---

## 5. HATA YÖNETİMİ

### 5.1 Mantık katmanı ile arayüz katmanı ayrı

Ağ/dosya/komut işlemleri yapan sınıflar **GTK'dan bağımsız** olmalı
(Poligon'daki `ogrenci_istemci.py` gibi). Bu sayede GTK olmadan test
edilebilirler.

### 5.2 Dil bağımsız hata kodları

Mantık katmanı **sabit Türkçe metin döndürmez** — hangi dilde çalışıldığını
bilmez. İşaret kodu döndürür, arayüz çevirir:

```python
# mantik katmani
return False, "__BAGLANTI_HATASI__"

# arayuz katmani
if hata == "__BAGLANTI_HATASI__":
    hata = METIN[self.dil]["hata_baglanti"]
```

### 5.3 Sessiz başarısızlık nerede kabul edilir

Yan özellikler (ikon yükleme, ilerleme kaydı, istatistik gönderimi) asıl işi
**engellememeli** — `try/except` ile yutulur ama yorumla gerekçesi yazılır:

```python
except OSError:
    pass  # gecmis kaydi pratigi engellemez, sadece istatistik kaybolur
```

Asıl işlevde (kullanıcının gördüğü sonuç) sessiz başarısızlık **kabul
edilmez** — kullanıcıya anlaşılır bir mesaj gösterilir.

---

## 6. YORUM VE BELGELEME TARZI

- Yorumlar **Türkçe**.
- **Neden**'i anlat, **ne**'yi değil. Kod ne yaptığını zaten söylüyor.
  ```python
  # KOTU:  # dili tr yap
  # IYI:   # Sistem dili Turkce ise 'tr' -- kullanici arayuzden
  #        # degistirebilir, bu sadece acilis varsayilani.
  ```
- Bir tasarım kararı alışılmadıksa gerekçesini yaz:
  ```python
  # Varsayilan GIZLI secildi cunku sinifta projeksiyon acikken bu
  # bilginin yanlislikla herkese gorunmesi istenmiyor.
  ```
- Kaldırılmış/denenmiş ama vazgeçilmiş yaklaşımları not et — gelecekte
  aynı şeyin tekrar denenmesini önler.

---

## 7. YENİ UYGULAMA EKLEME — KONTROL LİSTESİ

1. [ ] `opt/carotos/<ad>/<ad>.py` yazıldı, shebang + docstring var
2. [ ] `APP_VERSION` sabiti var
3. [ ] `METIN` sözlüğü tr+en, aynı anahtar seti
4. [ ] `_sistem_dilini_belirle()` ile açılış dili
5. [ ] `_metinleri_uygula()` tüm metinleri kapsıyor, dil düğmesi çalışıyor
6. [ ] Ortak tema (`tema.py`) + uygulamanın vurgu rengi kullanıldı (kendi CSS'in yok)
7. [ ] 256×256 ikon hazırlandı, `set_icon_from_file` + `try/except`
8. [ ] `.desktop` dosyası (`Name`, `Name[tr]`, `Comment`, `Comment[tr]`,
       `Exec`, `Icon`, `Categories`, `Keywords`, `Keywords[tr]`)
9. [ ] Yetki gerekiyorsa pkexec ya da sabit-komut sudo deseni
10. [ ] Uzun işlemler thread'de, `GLib.idle_add` ile arayüze dönüş
11. [ ] Panel kısayolu gerekiyorsa launcher-N + `xfce4-panel.xml` (iki yer!)
12. [ ] Dosya izinleri: ikon/görsel `644`, betik `755`
13. [ ] `python3 -m py_compile` ve mümkünse `pyflakes` temiz
14. [ ] **Gerçek sistemde çalıştırılıp görsel olarak test edildi**
15. [ ] README.md ve web sitesi "Uygulamalar" bölümü güncellendi
16. [ ] Uygulama sayısı güncellendi (hero metni, istatistik kutusu, lede)

**15 ve 16 sık atlanıyor** — Poligon eklenirken "dört uygulama" ifadesi beş
ayrı yerde elle düzeltilmek zorunda kaldı.

---

## 8. TEST ALIŞKANLIĞI

- **Mantık katmanı GTK'sız test edilir** (`test_*.py`, konsol).
- **GTK katmanı gerçek ortamda gözle test edilir** — "derleniyor" yeterli
  değil.
- Sudo gerektiren testler **gerçek sudo yetkili kullanıcı olarak**
  çalıştırılır, root olarak değil (root'ta sudo hep başarılı döner,
  anlamsız sonuç verir).
- Test dosyaları **ISO'ya girmez** (`rm .../test_*.py` senkronizasyon
  adımında).
