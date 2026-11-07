# Caroise 0.1: cloud Claude için görev brifingi

Bu belge, **Caroise** tarayıcısını ayrı bir depoda (`MiracLight/Caroise`) yazacak Claude oturumu içindir. Okuyan Claude CarotOS'u
bilmiyor varsay; bilmesi gerekenler burada. CarotOS tarafındaki entegrasyonu (Karşılama sayfası, Former sahnesi, 7 dil çevirisi,
ISO hook'u) CarotOS deposundaki başka bir Claude oturumu yapar; sen yalnızca bu depoyu yazarsın.

## 1. Proje

CarotOS, siber güvenliğe yeni başlayanlar için Debian 13 "trixie" tabanlı, Xfce masaüstlü bir Linux dağıtımıdır
(GPL-3.0, https://carotos.org). Felsefe: yüzlerce araç yerine on seçilmiş araç, her biri iyi anlatılmış. Uygulamalar
Python 3 + PyGObject (GTK3), **harici Python bağımlılığı eklenmez**. Hedef kitle: yeni başlayanlar ve öğrenciler; dil Türkçe
ve İngilizce (diğer 7 dil çeviri katmanından gelir).

**Caroise nedir:** CarotOS'un gizlilik odaklı gezinme ortamı. **Fork DEĞİL, yapılandırma:** Debian'ın `firefox-esr` paketinin
üstüne sıkılaştırılmış bir profil, kurumsal politika dosyası, eklentiler ve bir başlatıcı. Firefox'u derlemek ya da
çatallamak kapsam dışı (Debian güvenlik yamaları otomatik gelsin).

## 2. Kesin kurallar (bozma)

1. **Commit kimliği:** `MiracLight <209255494+MiracLight@users.noreply.github.com>`. Commit mesajına ve PR açıklamasına
   **Claude imzası, `Co-Authored-By: Claude`, oturum bağlantısı ya da "Generated with Claude Code" ekleme.** Bir araç ya da hook
   ekletmek isterse yapma.
2. **Push yok.** Yalnızca yerelde commit at; push'u kullanıcı yapar. `sudo`, silme, dışarıya yükleme için önce söyle.
3. **Sürüm:** "Caroise 0.1". CarotOS'un kullanıcıya görünen sürümü 1.3'tür; CarotOS sürümünü bu depoda gösterme.
4. **Dürüstlük ("iddia = test"):** arayüzde, belgede ve README'de **yalnızca bir testin kanıtladığı şey iddia edilir.**
   Şunlar **yazılmayacak**: "iz bırakmaz", "RAM ezilir", "adli temizlik", "tam anonim", "izlenemez". Sansürlü ortamlarda yanlış
   güven zarar verir. Sınırlamalar bir özellik gibi açıkça yazılır (ör. "tmpfs silme güvenli silme değildir; swap
   şifreli değilse RAM içeriği diske yazılabilir").
5. **Kullanıcıya dönük metinler** Türkçe ve İngilizce birlikte tutulur: Python'da `T("türkçe", "english")` biçimi (sözlük
   `{"tr": ..., "en": ...}`). Kabuk betiklerinde mesajlar `case "$LANG"` ile iki dilli. Başka dillere sen çevirme.
6. **Yeni başlayanlara öğretir, engellemez.** Her sıkılaştırma kararının yanında "neden" kısa yazılsın.
7. **Etik/yasal:** özel proxy/tünel dağıtımı ve sansür aşma "ürünü" YOK. DoH + ECH (Firefox'un kendi özellikleri) yeterli;
   proxy yalnızca kullanıcının kendi verdiği yapılandırmayla (BYO); Tor için Tor Browser'a (`torbrowser-launcher`) yönlendir.
8. **Telemetri yok, dışarıya kendiliğinden bağlantı yok.** Betikler kurulumda/çalışırken ağa çıkmaz (Firefox hariç).
   Parola, anahtar, kimlik bilgisi dosyaya yazılmaz.

## 3. Kapsam: Caroise 0.1

Teslim edilecekler (hepsi bu depoda, yeni başlayan okuyabilsin diye yorumlu):

- `firefox/policies.json` — kurumsal politika: telemetri/araştırma/Pocket/öneriler kapalı, otomatik güncelleme **Debian'a
  bırakılır** (kapatılır), DoH + ECH, `DisableFirefoxStudies`, parola yöneticisi tercihi kullanıcıya bırakılır.
  **DoH sağlayıcısı kullanıcı kararıdır:** varsayılanı seçme; `SEÇENEKLER.md` içinde Quad9 / Cloudflare / "sistem çözümleyicisi"
  için artı-eksi yaz, politikada tek satırla değiştirilebilir bırak.
- `firefox/user.js` ya da `autoconfig` — `privacy.resistFingerprinting` (ek bir **"Parmak izi koruması" seçeneği** olarak:
  bazı sitelerde bozulur, bunu arayüz metninde söyle), WebRTC IP sızıntısını azaltan ayarlar, üçüncü taraf çerez kısıtı.
- `firefox/chrome/userChrome.css` — CarotOS teması: nötr koyu mavi (`#101a26` → `#1a2b3e`), vurgu `#5b86b8`. Okunabilirliği bozma.
- **Eklentiler:** uBlock Origin (Debian paketi `webext-ublock-origin-firefox` varsa onu kullan; **adayı `apt-cache policy`
  ile doğrula**, yoksa nedenini yaz), Firefox Multi-Account Containers (OSINT/pentest konteynerleri için; sıfırdan yazma).
- `bin/caroise` — başlatıcı (POSIX sh ya da Python 3): iki profil: **kalıcı** ve **geçici oturum**. Geçici oturum profili
  `$XDG_RUNTIME_DIR` ya da `/dev/shm` altında oluşur, çıkışta silinir; başlarken swap durumunu kontrol edip **uyarır**
  (`swapon --show`: diskte şifresiz swap varsa "RAM içeriği diske yazılabilir" de). CarotOS'ta varsayılan swap zram'dır
  (RAM'de), ama bunu da test etmeden iddia etme.
- `bin/caroise-panik` — iki ayrı eylem, **ayrı komutlar**: `gizle` (tüm Caroise pencerelerini anında gizle / küçült) ve
  `temizle` (tarayıcıyı kapat, geçici profili sil, panoyu temizle, isteğe bağlı ekran kilidi). `temizle` bittiğinde
  **dürüst bir "Temizlik Raporu"** yazdırır: neyin silindiği ve **neyin kalabileceği** (DNS önbelleği, `journald`, küçük
  resimler, GPU belleği, swap).
- `qa/sizinti-testi.sh` — yerel ölçümler: DNS şifreli mi, WebRTC yerel IP sızdırıyor mu, canvas/audio parmak izi.
  Yalnızca **ölçebildiğini** raporlar; ölçemediğini "ölçülemedi" yazar. Ağ gerektiren kısmı atlanabilir olsun.
- `tests/` — `python3 tests/test_<ad>.py` biçiminde `unittest` (ekran yoksa arayüz testleri atlanır) ve kabuk betikleri için
  `shellcheck` (varsa). JSON dosyalarının geçerliliği, politika anahtarlarının varlığı, başlatıcının geçici profili gerçekten
  sildiği, panik betiğinin yalnızca kendi profilini silmesi (yol doğrulaması!) testle kanıtlanır.
- `debian/` — **iskelet** (kaynak paketi `caroise`, bağımlılık `firefox-esr`); henüz yayınlanmayacak. Dosya sahipliği
  `root:root`, kullanıcı verisi (`~/.config`) pakete girmez, `postinst` yerine trigger.
- `README.md` — ne yaptığı, **ne yapmadığı**, sınırlamalar. `SEÇENEKLER.md` — kullanıcının karar vereceği noktalar.

**Kapsam dışı (0.1'de yok):** tünel/proxy hub'ı, donanım anahtarı kilidi, özel arayüz çatalı, apt deposu, otomatik
güncelleme mekanizması, Windows/macOS sürümü.

## 4. Güvenlik gereksinimleri

- Silme işlemleri (panik, geçici profil) **yalnızca Caroise'in kendi oluşturduğu dizinde** çalışır: yol `realpath` ile
  çözülür, beklenen kök dizinin altında olduğu doğrulanır, sembolik bağlantı izlenmez. Doğrulanamazsa **silme**, hata ver.
- Kabuk betiklerinde değişkenler tırnaklı, `set -eu`, tahmin edilebilir geçici dosya adı yok (`mktemp -d`).
- `rm -rf` ile boş/`/` olabilecek bir değişken kullanma; testle kanıtla.
- `policies.json` içine kimlik bilgisi, kişisel URL, sabit proxy yazma.

## 5. Test ve doğrulama

Bulutta yapabileceklerin: birim testler, `shellcheck`, JSON doğrulama, **`firefox-esr` kurulabiliyorsa** başsız modda
(`firefox-esr -headless`) politikaların yüklendiğinin doğrulanması (ör. `about:policies` çıktısı ya da profilde beklenen
tercihler). Yapamadığın (masaüstü kısayolu, ekran kilidi, Xfce davranışı, gerçek ağ sızıntı ölçümü) şeyleri **"doğrulanmadı:
CarotOS VM'inde denenmeli"** diye README'de listele. **Çalıştırmadığın testi çalıştı sayma.**

## 6. Entegrasyon sözleşmesi (CarotOS tarafı bunu bekler)

Depoyu aşağıdaki düzende teslim et; CarotOS ISO'sunda bu klasörler aynen şuraya kopyalanacak:

| Depoda | ISO'da |
|---|---|
| `bin/caroise`, `bin/caroise-panik` | `/opt/carotos/caroise/bin/` (başlatıcılar `/usr/local/bin/` altına bağlanır) |
| `firefox/policies.json` | `/usr/lib/firefox-esr/distribution/policies.json` |
| `firefox/user.js`, `firefox/chrome/` | `/opt/carotos/caroise/firefox/` (profil şablonu) |
| `qa/sizinti-testi.sh` | `/opt/carotos/caroise/qa/` |
| `desktop/caroise.desktop` | `/usr/share/applications/` (Name/Name[tr], Keywords; simge adı `carotos-caroise`) |

Simgeyi sen çizme (`desktop/` içinde yer tutucu adı yeterli); logo kararı kullanıcıya ait. Kullanıcı arayüzü yazan her şey
`T(tr, en)` biçiminde olmalı ki CarotOS'un çeviri aracı (`tools/ceviri.py`) taraması yapabilsin.

## 7. Çalışma şekli ve rapor

- Küçük, ayrı commit'ler; her commit'te ilgili test. Önce `README.md` ve `SEÇENEKLER.md` taslağı, sonra politika, sonra
  başlatıcı + geçici oturum, sonra panik, sonra sızıntı testi, en son `debian/` iskeleti.
- Bitince kısa rapor: ne yapıldı, ne **doğrulanmadı**, kullanıcının karar vermesi gerekenler (`SEÇENEKLER.md`), CarotOS tarafının
  yapacakları.
- Emin olmadığın bir Firefox ilkesi/tercih adı varsa **tahmin etme**: Mozilla'nın politika şablonu belgelerinden
  (`policy-templates`) doğrula, bulamazsan açıkça "doğrulanamadı" yaz.
