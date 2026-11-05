# CarotOS çeviri sistemi

Dokuz dil: Türkçe, İngilizce (kaynak, kodda yazılı) ve Almanca, Rusça, İspanyolca,
Portekizce, Japonca, Çince (yalın), Fransızca (dil dosyalarından). Ortak katman:
`config/includes.chroot/opt/carotos/ortak/dil.py`, araç: `tools/ceviri.py`.

## Nasıl çalışır

Uygulamaların metinleri kodda `{"tr": "...", "en": "..."}` sözlükleri olarak kalır.
Diğer diller kodu değiştirmeden `ortak/diller/<kod>.json` dosyalarından gelir:

```json
{
 "_meta": {"ad": "Español", "etkin": true, "durum": "taslak"},
 "metinler": {"Run": "Ejecutar", "{tool} running…": "{tool} se está ejecutando…"}
}
```

- **Anahtar İngilizce metindir** (gettext'teki msgid gibi). Aynı İngilizce metin
  tüm uygulamalarda tek çeviri paylaşır; kodda anahtar uydurulmaz.
- Çeviri yoksa İngilizceye, o da yoksa Türkçeye düşülür; hiçbir yerde `KeyError` çıkmaz.
- Yer tutucular (`{tool}`, `{dosya}`) çeviride aynen kalmalıdır. Bozuk çeviri
  uygulamayı çökertmez, İngilizce metne düşülür; `tools/ceviri.py` zaten reddeder.
- `_meta.etkin: true` olan ve en az bir çevirisi bulunan dil, uygulamaların dil
  seçicisine girer. `durum: "taslak"` ise seçicide **"(beta)"** yazar
  (ana dilini konuşan biri gözden geçirmediyse taslak kalır). Gözden geçirilince
  `durum` değeri `"gozden-gecirildi"` yapılır.
- Sistem dili etkin bir dilse ilk açılış dili odur, değilse İngilizce
  (`dil.varsayilan_dil()`). Kayıtlı kullanıcı ayarı her zaman önceliklidir.

## Bir uygulamayı bu sisteme bağlama

```python
import dil                                   # ortak/ yolu sys.path'te olmalı
STRINGS = dil.zenginlestir(STRINGS)          # tr/en sözlükleri her dil için yedekli olur
TOOLS = dil.zenginlestir(TOOLS)              # iç içe yapılar da olur
def T(key, lang, **kw): return dil.T(STRINGS.get(key), lang, key, **kw)
# düz sözlükte: dil.metin({"tr": "..", "en": ".."}, lang)   ({...}[lang] KeyError verir!)
# dil seçici:  for kod, ad, taslak in dil.etkin_diller(): combo.append(kod, dil.secici_adi(kod, ad, taslak))
# ayar:        self.lang = dil.gecerli(ayar["language"])
```

Bağlı uygulamalar (`tests/test_dil_guvenlik_paneli.py`, `tests/test_dil_uygulamalar.py`,
`tests/test_filenor_dil.py`, `tests/test_poligon_dil.py`): Güvenlik Paneli, Sistem Sağlığı,
USB Denetimi, Mağaza, Carotene, Karşılama, GSD, Former, CarotPot (arayüz), Poligon (öğrenci +
öğretmen) ve Filenor. Poligon'un `METIN` yapısı dil-önce (`METIN[dil][anahtar]`) olduğundan
`dil.dil_once()` ile sarılır (çağrı yerleri değişmez); görev/şablon verisi `zenginlestir`
ile her dilde okunur. İkisi de ortak katmana kendi köprülerinden bağlanır
(`poligon/dil_koprusu.py`, `filenor/filenor_dil.py`); `ortak/` yoksa (bağımsız depo)
yalnız tr/en çalışır. Poligon'un seçtiği dil `~/.config/carotos-poligon/ayar.json`'a
kaydedilir. `tests/test_dil_etkin_kosulu.py` etkin bir dil varken bağlanmamış uygulama
kalırsa kırmızı olur. **Ayrı depolara (CarotOS-Poligon, filenor) aynalama henüz yapılmadı.**

Bilinen sınırlar: (1) Former'ın birleştirerek ürettiği metinler (`T(a + b, c + d)`)
ve f-string ile çalışma anında kurulan sözlükler `tools/ceviri.py` taramasında
görünmez; çevrilebilmeleri için sabit metne dönüştürülmeli ya da çalışma anı
toplayıcısı eklenmelidir. (2) CarotPot bildirim metinleri (hizmet `python3 -I` ile
çalıştığı için) henüz dil dosyalarından çevrilmez; tr/en dışında İngilizce gelir.
(3) Filenor komut satırı çıktıları yalnız tr/en'dir (CLI). (4) Karşılama'nın "Sistem dili" kartı yalnızca tr/en için oturum dilini (locale)
değiştirir; diğer diller yalnızca CarotOS uygulamalarının dilini ayarlar.

Çalışma anında üretilen metinler (f-string, birleştirme) `tools/ceviri.py` tarafından
çıkarılamaz ("dinamik" sayılır): bunlar `dil.T(...)` ile yer tutuculu sözlüğe
çevrilmelidir.

## Çeviri iş akışı (parti parti)

```bash
python3 tools/ceviri.py durum                      # dil dil kapsam yüzdesi
python3 tools/ceviri.py eksik es --limit 80        # çeviri bekleyen 80 metin (JSON, kısadan uzuna)
python3 tools/ceviri.py eksik es --uygulama gsd    # yalnızca bir uygulamanın metinleri
python3 tools/ceviri.py ekle es parti.json         # {"<en metin>": "<çeviri>"} dosyasını doğrulayıp ekler
python3 tools/ceviri.py kontrol                    # yer tutucu/boş/yetim denetimi (hata varsa çıkış 1)
```

Her partide çevirilerle birlikte **Türkçe geri çeviri** verilir ki onay bir anlam
kontrolü olsun. Yeterli kapsama ulaşan dilde `etkin: true` yapılır (seçiciye girer).
Hiçbir dil, ana dilini konuşan biri gözden geçirmeden "tam destek" diye duyurulmaz.

## Kurallar

- Çeviriler hukuki/etik iddia taşımaz; etik işlem metni her dilde aynı içeriktedir.
- İngilizce kaynak metin değişirse çeviri "yetim" olur (`kontrol` uyarır); yeniden çevrilir.
- Dil dosyaları UTF-8, LF, anahtarlar sıralı yazılır (`ekle` bunu yapar); elle düzenlenebilir.

## İspanyolca stil rehberi ve sözlük (taslak, kullanıcı onaylı parti 1: Güvenlik Paneli)

- **Varyant:** Latin Amerika'ya yakın, tarafsız İspanyolca (İspanya'ya özgü sözcük yok: `Añadir` değil `Agregar`, `Ajustes` değil `Configuración`, `Comprobando` değil `Verificando`).
- **Hitap:** `tú` kipi (`Elige`, `Guarda`, `¿Es esta tu red?`). `usted` ve `vosotros` kullanılmaz.
- **Çevrilmeyenler:** araç/ürün adları (nmap, ClamAV, Wireshark, CarotOS, Poligon), kısaltmalar (SSH, UFW, DNS, SQL…), komut/dosya yolları, yer tutucular (`{tool}`, `{code}`).
- **Sözlük:** target = `objetivo` (saldırı bağlamı); scan = `escanear`/`escaneo`; Firewall = `Firewall`; Enabled/Disabled = `Activado`/`Desactivado`; Status = `Estado`; Settings = `Configuración`; Language = `Idioma`; Refresh = `Actualizar`; Cancel = `Cancelar`; wordlist = `lista de palabras`; brute force = `fuerza bruta`; packet capture = `captura de paquetes`; PASS = `CORRECTO`, ATTENTION = `ATENCIÓN`, WARNING = `ADVERTENCIA` (karşıtı FAIL çıkarsa `FALLO`).
- **Sözlük (parti 3, Sistem Sağlığı):** report = `reporte`; log = `registro`; Start = `Inicio`; Uptime = `Tiempo activo`; eylem düğmeleri emir kipinde (`Bloquear root`, `Desactivar SSH`, `Activar firewall`); `passed` = `correcto`; Restart = `Reiniciar`. Düğmeye sığmayan uzun etiketler kısaltılır (ör. `Corregir predeterminado`).
- **Çift anlamlı kısa anahtarlar** (aynı İngilizce metin farklı yerde): bir çeviri tüm uygulamalarda geçerli olur; menü için isim, düğme için fiil gerekiyorsa fiil biçimi seçilir (`Scan` = `Escanear`).
- **Parti sırası:** değişmeyecek uygulamalardan önce (Güvenlik Paneli → Sistem Sağlığı → Mağaza → USB → Carotene/CarotPot); Karşılama/Former/GSD uzun içerikleri, Karşılama yeni akışı (merkez-kol) yazıldıktan sonra.
- Her partide: tablo (İngilizce, çeviri, Türkçe geri çeviri) kullanıcıya sunulur, onaylanınca `ekle` ile işlenir. `etkin: true` yalnız çekirdek uygulamalar büyük ölçüde bitince.
