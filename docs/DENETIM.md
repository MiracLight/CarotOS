# CarotOS uygulama denetimi

Uygulama uygulama güvenlik ve sağlamlık denetiminin kayıt defteri. Sıra: Poligon → CarotPot → Güvenlik Paneli + ortak → Carotene / Mağaza / USB / Sistem Sağlığı → Filenor / Karşılama / Former / GSD / Açıklayıcı.

Her bulgunun bir kimliği, önemi, dosya:satır konumu, kanıtı ve önerilen düzeltmesi vardır. "Durum" sütunu düzeltme ilerledikçe güncellenir; denetime başka bir oturumda devam eden kişi buradan sürdürür.

Kanıt türleri:
- **Denendi:** WSL Debian (Python 3.13) üzerinde, yalnızca 127.0.0.1'de açılan gerçek soketlerle doğrulandı.
- **Okundu:** kod okunarak çıkarıldı, çalıştırılarak doğrulanmadı.

---

## 1. Poligon (12 Kasım 2026)

### 1.1 Kapsam

Satır satır okunanlar: `ogretmen_sunucu.py`, `ogrenci_istemci.py`, `ag_guvenlik.py`, `ctf_cekirdek.py`, `ctf_istemci.py`, `servisler/*` (8 dosya), `tuzak_laboratuvari.py`, `flag_uretici.py`, `kullanici_defteri.py`, `gecmis_defteri.py`, `soru_defteri.py`, `olay_gunlugu.py`.

Hedefli taranıp ilgili bölümleri okunanlar (ağ çağrısı, alt süreç, dosya yazma, işaretleme, zamanlayıcı): `ogrenci_uygulama.py`, `ogretmen_uygulama.py`, `ctf_pencere.py`, `ctf_ogretmen.py`, `savunma_pencere.py`, `savunma_analiz.py`, `ctf_uretici.py`, `uretilen_gorevler.py`, `gorev_dogrulayici.py`.

Okunmayanlar (ağ ya da yetki sınırına dokunmayan içerik üreticileri): `varyant_gunluk.py`, `varyant_sifre.py`, `varyantlar.py`, `soru_sablonlari.py`, `gorev_bilgi.py`, `terim_sozlugu.py`, `dil_koprusu.py`, `gorunum_ayari.py`, görev JSON dosyaları.

Yapılmayanlar: VM'de gerçek iki makineli sınıf denemesi; GTK arayüzü çalıştırılarak yapılan doğrulama (zamanlayıcı davranışları kod okumasına dayanıyor).

### 1.2 Tehdit modeli

**Açık yüzey.** Öğretmen uygulaması `0.0.0.0:8642` üzerinde düz HTTP sunucusu açar (`ogretmen_uygulama.py:467`). Makinenin bağlı olduğu her ağdan erişilir. Diğer bütün servisler (sahte giriş, ağ, web, trafik, banner, site, tuzak laboratuvarı) yalnızca `127.0.0.0/8` üzerinde dinler ve bu kural kod düzeyinde iki kez denetlenir.

**Aktörler.**

| Aktör | Elinde ne var | Ne yapmak isteyebilir |
|---|---|---|
| Ağdaki yabancı | Yalnızca ağ erişimi | Dersi durdurmak, öğrenci adlarını öğrenmek, oda şifresini bulmak |
| Sınıftaki öğrenci | Oda şifresi, kendi anahtarı | Skoru şişirmek, başkası adına işlem yapmak, öğretmen gibi görünmek, öğretmen panelini bozmak |
| Sahte ya da araya giren sunucu | Öğrencinin bağlandığı adres (düz HTTP) | Öğrencinin makinesinde dosya okutmak, servis açtırmak, uygulamayı kilitlemek |
| Aynı makinedeki başka kullanıcı | Yerel hesap | Geçici dosyalara müdahale, loopback servislerine bağlanmak |

**Güven sınırları.** (1) Ağ → öğretmen sunucusu. (2) Öğretmen sunucusunun yanıtı → öğrenci istemcisi. İkincisi şu an neredeyse hiç denetlenmiyor; istemci sunucuyu güvenilir sayıyor.

**Bilinçli tasarım kararları (bulgu değil).** Ders modunda cevap öğrencinin makinesinde doğrulanır ve puanı öğrenci bildirir; yani kararlı bir öğrenci "tamamlandı" bildirimini elle gönderebilir. Hakemin sunucu olduğu tek mod CTF'tir. Bu, ders modunun doğası gereği kabul edilmiş bir sınırdır; yine de bildirilen değerlerin sınırlanması gerekir (P-06).

### 1.3 Bulgular

#### Yüksek

| No | Bulgu | Konum | Kanıt | Durum |
|---|---|---|---|---|
| P-01 | **`tum_sinif` adıyla katılan öğrenci bütün sınıfa öğretmen notu gibi görünen mesaj yazar.** `mesaj_ekle` içinde `tum_sinif` özel bir addır (herkese yayın); `/katil` bu adı yasaklamıyor. Öğrenci arayüzü gelen mesajın `kimden` alanına bakmadan hepsini öğretmen notu biçiminde gösteriyor. | `ogretmen_sunucu.py:317`, `:543-552`, `:617`; `ogrenci_uygulama.py:1592-1598` | Denendi: `tum_sinif` adıyla katılım kabul edildi, gönderilen mesaj başka öğrencinin `/sohbet` yanıtında çıktı. | Düzeltildi (`a9a498a`) |
| P-02 | **Tek bir istek öğretmenin öğrenci listesini kalıcı olarak dondurur.** `/ilerleme` `sure_sn` alanında `NaN` ve `Infinity` kabul ediyor (Python `json` bunları varsayılan olarak okur). Öğretmen paneli her 800 ms'de `int(sure_sn)` çağırıyor; `NaN` için `ValueError` fırlar, GLib zamanlayıcısı istisnada kaldırılır ve liste bir daha güncellenmez. Ayrıca `/durum` geçersiz JSON üretir. | `ogretmen_sunucu.py:573-588`; `ogretmen_uygulama.py:1624` | Denendi: `NaN` 200 ile kabul edildi, `int()` `ValueError` verdi. Zamanlayıcının kaldırılması: Okundu. | Düzeltildi (`d075dda`) |
| P-03 | **Kimlik doğrulamasız bağlantı tüketme.** Her bağlantı için sınırsız iş parçacığı açılıyor. 10 sn'lik zaman aşımı her `recv` için ayrı sayıldığından, birkaç saniyede bir tek bayt gönderen bağlantı süresiz açık kalıyor. Sunucu öğretmen uygulamasıyla aynı süreçte çalıştığı için dosya tanıtıcıları tükenince uygulamanın kendisi de etkilenir. | `ogretmen_sunucu.py:373`, `:627-633` | Denendi: 200 yarım istekle iş parçacığı 2'den 202'ye çıktı; 18 sn sonra 117'si hâlâ açıktı. Tanıtıcı tükenmesinin arayüze etkisi: Okundu. | Düzeltildi (`65aae9b`) |
| P-04 | **Öğrenci istemcisi ilk ağ aksamasında öğretmenle eşitlemeyi kalıcı olarak bırakır.** `_istek` yalnızca `URLError` yakalıyor. Yanıt beklerken zaman aşımı (`TimeoutError`), bağlantının kopması (`ConnectionResetError`, `RemoteDisconnected`) ve JSON olmayan yanıt (`JSONDecodeError`) ham olarak çıkıyor. Çağıranlar yalnızca `BaglantiHatasi` yakaladığı için istisna 3 sn'lik zamanlayıcı geri çağrısından taşar ve zamanlayıcı kaldırılır: yeni soru, mesaj ve atılma bildirimi bir daha gelmez. Ek olarak bu çağrılar GTK ana iş parçacığında yapılıyor; sunucu yavaşsa arayüz her turda 15 sn'ye kadar donar. | `ogrenci_istemci.py:529-545`, `:615-618`, `:715`; `ogrenci_uygulama.py:1114`, `:1575-1601`, `:1659` | Denendi: yanıt vermeyen sunucuda `TimeoutError`, HTML hata sayfasında `JSONDecodeError`, kopan bağlantıda `ConnectionResetError`, bozuk `varyantlar` değerinde `ValueError`. Zamanlayıcının kaldırılması: Okundu. | Düzeltildi (`7eb5e72`) |

#### Orta

| No | Bulgu | Konum | Kanıt | Durum |
|---|---|---|---|---|
| P-05 | **Sunucudan gelen görev kimliği öğrencinin makinesinde dizin dışı dosya yükletir.** `gorevi_yukle` kimliği doğrulamadan yola ekliyor; `../` ya da mutlak yol kabul ediliyor. Yüklenen dosya görev tanımı sayılır: içindeki `hedef.jail` değeri `sudo fail2ban-client status <jail>` komutuna argüman olur, `hedef.port` ve `sabit_kullanici` servis başlatır. Saldırganın içeriğini belirlediği dosya, CTF "kaydet" düğmesiyle `~/Poligon-CTF/` altına `.json` uzantısıyla yazdırılabilir. Sahte ya da araya giren sunucu gerektirir. | `ogrenci_istemci.py:256-262`, `:478-486`; `ctf_pencere.py:129-133`, `:515` | Denendi: hem `../` zinciri hem mutlak yol ile görev dizini dışındaki dosya yüklendi. Zincirin tamamı: Okundu. | Düzeltildi (`d9f1c9a`) |
| P-06 | **Katılım ve ilerleme kayıtlarında üst sınır yok.** Oda şifresini bilen biri saniyeler içinde yüzlerce sahte öğrenci ekleyebiliyor. `puan` ve `soru_no` sınırsız; her farklı `soru_no` yeni kayıt açıyor, `cevaplar` listesi süresiz büyüyor. Sonuç: skor tablosu istenen değere çekilir, öğretmen paneli ve belleği şişirilir. | `ogretmen_sunucu.py:225-242`, `:257-285`, `:587-588` | Denendi: 0,2 sn'de 300 sahte öğrenci; `puan=10**9` kabul edildi ve skor özetine yansıdı; 2000 farklı `soru_no` 2000 kayıt açtı. | Düzeltildi (`d075dda`) |
| P-07 | **Sunucudan gelen görev parametreleri istemcide sınırlanmıyor.** `gurultu` doğrudan iş parçacığı sayısı oluyor (üst sınır yok). `gizli_port_araligi` hatalıysa `ValueError`, `TypeError` ya da `OverflowError` fırlıyor; ayrıcalıklı port verilirse gizli port sessizce açılamıyor ve soru çözülemez hale geliyor. `basamak`, `tuzak_tablolar`, `gerekli_giris` tür denetimi olmadan `int()` ya da üs almaya gidiyor. Üreteçler (`uretilen_gorevler.py`) ise `_tam_sayi` ile doğru biçimde sınırlıyor; eksik olan eski görev türleri. | `ogrenci_istemci.py:309-403`; `servisler/sahte_trafik.py:41`; `servisler/sahte_ag.py:39-41`; `flag_uretici.py:37-39` | Denendi: `gurultu=100000` kabul edildi; port aralığı örneklerinde üç ayrı istisna; `basamak=300000` `ValueError`. | Düzeltildi (`d9f1c9a`) |
| P-08 | **Şifresiz `/durum` bütün öğrenci adlarını ve ilerlemelerini verir.** Bu yolu hiçbir istemci kullanmıyor (öğretmen paneli durumu süreç içinden okuyor). `/aktif_mi` de şifresiz olarak "bu ad sınıfta mı" sorusunu yanıtlıyor. Öğrenciler çoğunlukla reşit olmadığı için ad sızıntısı önemsenmeli. | `ogretmen_sunucu.py:425-426`, `:439-446` | Denendi: şifresiz istekle 302 ad döndü. | Düzeltildi (`507afaa`) |
| P-09 | **Atılan öğrenci yarış durumunda hayalet olarak geri gelir.** Anahtar denetimi ile `ilerleme_guncelle` ayrı kilit bölümlerinde. Araya atma girerse öğrenci anahtarsız olarak listeye yeniden yazılır: adı kilitlenir, kimse o adla katılamaz, öğretmen yeniden atmak zorunda kalır. | `ogretmen_sunucu.py:263-269`, `:569-589` | Denendi (doğrudan çağrı sırasıyla): öğrenci listede, anahtarı yok, yeniden katılım 409. | Düzeltildi (`d075dda`) |
| P-10 | **Sınıf ağı trafiği düz HTTP.** Oda şifresi, öğrenci anahtarı ve CTF bayrakları ağı dinleyen herkesçe okunabilir; araya giren biri P-05 ve P-07'yi tetikleyebilir. Sunucu ayrıca bütün arayüzlerde dinliyor. | `ogretmen_uygulama.py:467`; `ogrenci_uygulama.py:1050-1052` | Okundu. | Karar bekliyor |
| P-11 | **`/tmp` altında öngörülebilir dosya adı.** John görevi `/tmp/carotos-poligon-john-<pid>.txt` yoluna `open(..., "w")` ile yazıyor. Aynı makinedeki başka bir kullanıcı bu yolu önceden oluşturarak görevi bozabilir (Debian'ın `protected_symlinks` ve `protected_regular` ayarları başka dosyanın ezilmesini engeller, görevin açılmasını değil). Parola ayrıca `openssl` komut satırında görünüyor. | `servisler/sahte_hash.py:40-42`, `:47`, `:51` | Denendi: yol `/tmp/carotos-poligon-john-252.txt`. Etki: Okundu. | Düzeltildi (`8fe4420`) |

#### Düşük

| No | Bulgu | Konum | Kanıt | Durum |
|---|---|---|---|---|
| P-12 | İstek işleyicide yakalanmayan istisnalar: çok derin iç içe JSON `RecursionError`, `puan` ya da `soru_no` için `Infinity` `OverflowError` verir. Sunucu çökmez ama yanıt vermeden bağlantıyı keser ve stderr'e iz döker. | `ogretmen_sunucu.py:386-397`, `:587-596` | Denendi: iki durumda da istemci `RemoteDisconnected` aldı. | Düzeltildi (`d075dda`) |
| P-13 | Cevap kutusu olmayan görevlerde (ufw, fail2ban, tuzak) `_dogru_cevap` sıfırlanmıyor. İlk görevde `None` yazmak, sonrakilerde önceki görevin cevabını yazmak "doğru" sayılıyor. | `ogrenci_istemci.py:427-428` | Denendi: `cevabi_kontrol_et("None")` `True` döndü. | Düzeltildi (`d9f1c9a`) |
| P-14 | Öğrenci adında yalnızca uzunluk denetimi var. Denetim karakterleri, yön değiştiren Unicode işaretleri ve görsel olarak aynı adlar (sondaki boşluk, benzer harfler) kabul ediliyor; skor tablosunda başkası gibi görünmek mümkün. | `ogretmen_sunucu.py:399-405` | Okundu. | Düzeltildi (`a9a498a`) |
| P-15 | CTF skor tablosu dondurulmuşken `/ctf/durum` görev başına güncel çözen sayısını ve güncel puanı vermeye devam ediyor; dondurmanın gizlediği bilgi buradan okunur. | `ctf_cekirdek.py:268-269` | Okundu. | Düzeltildi (`2b7e71e`) |
| P-16 | `/ctf/dosya` her istekte dosyayı yeniden üretiyor, bunu genel kilit altında yapıyor ve istek sınırı yok. Katılmış bir öğrenci CTF'i herkes için yavaşlatabilir. | `ctf_cekirdek.py:158-164`; `ogretmen_sunucu.py:503-509` | Okundu. | Düzeltildi (`2b7e71e`) |
| P-17 | Öğrenci adres alanına `192.168.1.5:8642` gibi portlu ya da bozuk bir değer yazarsa `InvalidURL` yakalanmıyor; ekran "Bağlanıyor…" yazısında ve düğme kapalı halde kalıyor. | `ogrenci_uygulama.py:1036-1065` | Okundu. | Düzeltildi (`7eb5e72`) |
| P-18 | İstemci `urllib` varsayılanlarını kullanıyor: ortamdaki `http_proxy` ayarına uyuyor (okul ağlarında öğretmenin yerel adresi vekil sunucuya gider ve bağlantı kurulamaz) ve yönlendirmeleri izliyor. | `ogrenci_istemci.py:531-537` | Okundu. | Düzeltildi (`7eb5e72`) |
| P-19 | İstemci sunucu yanıtını boyut sınırı olmadan belleğe okuyor. | `ogrenci_istemci.py:537`, `:539` | Okundu. | Düzeltildi (`7eb5e72`) |
| P-20 | `gecmis.json` yerinde yeniden yazılıyor; yazma yarıda kesilirse dosya bozulur ve sonraki kayıt bütün geçmişin üzerine tek satır yazar. `kullanicilar/*.json` (ad + okul numarası) varsayılan izinle, makinedeki herkesin okuyabileceği biçimde oluşuyor. | `gecmis_defteri.py`; `kullanici_defteri.py` | Okundu. | Düzeltildi (`8fe4420`) |
| P-21 | 8642 portu doluysa (ikinci öğretmen penceresi) pencere açılırken yakalanmayan `OSError` oluşuyor; kullanıcıya açıklama gösterilmiyor. | `ogretmen_uygulama.py:467` | Okundu. | Düzeltildi (`2b7e71e`) |
| P-22 | CTF süresi duvar saatine (`time.time`) bağlı. Yarışma sırasında sistem saati düzeltilirse süre uzar ya da kısalır. | `ctf_cekirdek.py:89`, `:119-123` | Okundu. | Düzeltildi (`2b7e71e`) |
| P-23 | Sahte servislerde küçük kaynak sızıntıları: `sahte_giris` satır sonu gelmeyen veriyi sınırsız biriktiriyor; `sahte_web.durdur` `server_close` çağırmıyor; durdurma sırasında açılan uyandırma soketleri kapatılmıyor. Hepsi yalnızca loopback'te. | `servisler/sahte_giris.py:84-91`, `:63`; `servisler/sahte_web.py` (`durdur`) | Okundu. | Düzeltildi (`8fe4420`) |
| P-24 | Belge kayması: modül başlığında anlatılan `/ipucu_gonder` ve `/ipucu` yolları kodda yok; `ogrenciyi_at` açıklaması öğrencinin ilerleme bildirince geri döneceğini söylüyor, anahtar denetimi eklendiğinden beri bu doğru değil. | `ogretmen_sunucu.py:17-18`, `:192-197` | Okundu. | Düzeltildi (`507afaa`) |

### 1.4 Sağlam bulunanlar

- Bütün sahte servisler ve üreteçler bağlanma adresini `ag_guvenlik.loopback_adres_mi` ile denetliyor; istemci sunucudan gelen hedef adresi ayrıca denetliyor (`ogrenci_istemci.py:289-293`). Saldırı trafiğinin makineden çıkabildiği bir yol bulunmadı.
- Oda şifresi ve öğrenci anahtarı sabit süreli karşılaştırılıyor; ASCII dışı ve `str` olmayan değerler güvenle reddediliyor.
- Öğrenciye özel anahtar (128 bit) `/ilerleme`, `/mesaj`, `/sohbet` ve bütün CTF yollarında aranıyor.
- Yanlış şifre denemeleri adres başına sınırlı (60 sn'de 10); istek gövdesi 64 KB ile sınırlı; HTTP/1.0, kalıcı bağlantı yok.
- CTF'te hakem sunucu: bayraklar öğrenci başına HMAC ile türetiliyor, saklanmıyor, sabit süreli karşılaştırılıyor; yanlış deneme beklemesi var; ipuçları sırayla açılıyor; CSV dışa aktarımı formül enjeksiyonuna karşı korunuyor.
- Hiçbir yerde kabuk üzerinden komut çalıştırılmıyor; `sudo -S -k` sabit argüman listesiyle çağrılıyor.
- Öğrenci ve öğretmen arayüzünde öğrenciden ya da sunucudan gelen metin Pango işaretlemesine girmeden önce kaçışlanıyor.
- CTF dosya kaydında sunucudan gelen ad `guvenli_dosya_adi` ile temizleniyor (yol parçası kalmıyor).
- Üreteçler ve tuzak laboratuvarı `mkdtemp` kullanıyor; tuzak laboratuvarı hizmet listesini ve port aralığını doğruluyor.

### 1.5 Düzeltme planı

Her adım ayrı commit, her biri testle birlikte. Sıra önem ve bağımlılığa göre.

| Adım | Kapsar | Ne yapılır | Kullanıcıya görünen değişiklik |
|---|---|---|---|
| 1 | P-01, P-14 | `/katil` içinde ad doğrulama: baştaki ve sondaki boşluk kırpılır, NFKC'ye çevrilir, denetim ve yön karakterleri reddedilir, `tum_sinif` ve benzeri ayrılmış adlar reddedilir, büyük-küçük harf farkı gözetmeden tekillik. Yayın için ad yerine ayrı bir çağrı (`tum_sinifa_yaz`). Öğrenci arayüzü `kimden` alanına bakar. | Bazı adlar reddedilir (hata iletisi gerekir, 7 dil). |
| 2 | P-02, P-06, P-09, P-12 | `/ilerleme` doğrulaması: sayılar sonlu ve aralıkta, `puan` görevin en yüksek puanıyla sınırlı, `soru_no` 0 ile etkin soru numarası arasında, `gorev_id` açık görevlerden biri. Öğrenci başına cevap kaydı ve toplam öğrenci sayısı sınırı. Anahtar denetimi ve güncelleme tek kilit altında. `json.loads` `parse_constant` ile `NaN` reddeder; `RecursionError` ve `OverflowError` 400 döner. Öğretmen paneli zamanlayıcısı istisnaya dayanıklı hale gelir. | Sınıf en fazla 200 öğrenci, adres başına en fazla 40 katılım. |
| 3 | P-03 | Eşzamanlı bağlantı sınırı (toplam ve adres başına), istek için toplam süre sınırı; fazlası hemen kapatılır. | Yok. |
| 4 | P-04, P-17, P-18, P-19 | `_istek` bütün ağ ve ayrıştırma hatalarını `BaglantiHatasi`'na çevirir; yanıt boyutu sınırlanır; vekil sunucu ve yönlendirme kapatılır; adres alanı doğrulanır. Periyodik denetimler arka plan iş parçacığına taşınır; zamanlayıcı geri çağrıları istisnada ölmez. | Adres alanında bozuk değer için hata iletisi (7 dil). |
| 5 | P-05, P-07, P-13 | Görev kimliği `[a-z0-9-]` ile sınırlanır ve yerel görev listesinde aranır. Sunucudan gelen bütün parametreler tür ve aralık denetiminden geçer; servisler kendi sınırlarını da uygular. `jail` adı doğrulanır. `_dogru_cevap` her görev başında sıfırlanır. | Yok. |
| 6 | P-08, P-24 | `/durum` kaldırılır (kullanan yok); `/aktif_mi` oda şifresi ve anahtar ister. Başlık belgesi güncellenir. | Yok. |
| 7 | P-11, P-20, P-23 | John dosyası `mkdtemp` altında 0600 izinle; parola `openssl`'e stdin'den. Defterler atomik yazılır, kullanıcı dizini 0700. Servislerde sınır ve kapatma düzeltmeleri. | Yok. |
| 8 | P-15, P-16, P-21, P-22 | Dondurulmuşken `/ctf/durum` kesim anındaki sayıları verir; dosya öğrenci ve görev başına önbelleğe alınır; port doluyken anlaşılır ileti; süre `time.monotonic` ile ölçülür. | Port doluyken hata iletisi (7 dil). |
| Karar | P-10 | Aşağıdaki seçeneklerden biri. | Seçeneğe bağlı. |

**P-10 için seçenekler.**
1. *Olduğu gibi bırak, belgele.* Karşılama ve Former metnine "Poligon sınıf ağı şifrelenmez, güvenilen ağda kullanın" notu. En az iş; 4. ve 5. adımlar araya girenin yapabileceklerini zaten sınırlar.
2. *Sunucuyu yalnızca seçilen arayüze bağla.* `0.0.0.0` yerine öğretmenin gösterilen yerel adresi. Küçük değişiklik; birden çok ağa bağlı makinelerde yanlış arayüz seçilme riski var.
3. *TLS.* Açılışta kendinden imzalı sertifika üretilir (`openssl` ile), parmak izi oda koduyla birlikte gösterilir. En güçlüsü; arayüz ve katılım akışı değişir, 1.4 kapsamını aşar.

Öneri: şimdi 1 + adım 4/5, TLS 1.5 için ayrı iş.

### 1.6 Kalıcı testler

Her bulgunun kalıcı karşılığı `tests/test_poligon_kotuye_kullanim.py` dosyasındadır (80 test; sınıf adları bulgu numarasını taşır, örneğin `P03BaglantiSinirlari`). Testler 127.0.0.1'de geçici portlarda gerçek sunucu ve gerçek soketlerle çalışır, GTK gerektirmez.

### 1.7 Düzeltme kaydı (12 Kasım 2026)

P-10 dışındaki 23 bulgu düzeltildi; her adım ayrı commit, dal `1.4`.

| Commit | Kapsar | Özet |
|---|---|---|
| `a9a498a` | P-01, P-14 | Ad doğrulama (NFKC, denetim ve yön karakterleri, ayrılmış adlar, büyük-küçük harf gözetmeyen tekillik); sınıfa yayın yalnızca öğretmenden; öğrenci arayüzü gönderene bakar. |
| `d075dda` | P-02, P-06, P-09, P-12 | `/ilerleme` doğrulaması; puan yalnızca atanmış soru için ve görevin en yüksek puanıyla sınırlı; sınıf ve kayıt sınırları; anahtar denetimi ile yazma tek kilitte; beklenmeyen hata 500 döner; öğretmen paneli zamanlayıcısı istisnaya dayanıklı. |
| `65aae9b` | P-03 | `SinirliSunucu`: 256 toplam, adres başına 32 eşzamanlı bağlantı; bağlantı ömrü 20 sn. |
| `507afaa` | P-08, P-24 | `/durum` kaldırıldı; `/aktif_mi` şifre ve anahtar ister; protokol belgesi kodla eşlendi. |
| `7eb5e72` | P-04, P-17, P-18, P-19 | İstemci her ağ hatasını `BaglantiHatasi`'na çevirir; vekil sunucu ve yönlendirme kapalı; yanıt alanları tür denetiminden geçer; adres doğrulanır; periyodik denetimler arka planda. |
| `d9f1c9a` | P-05, P-07, P-13 | Görev kimliği biçim denetimi; parametreler biçim ve aralık olarak sınırlı; jail adı doğrulanır; `sudo ... --`; cevap kutusu olmayan görevde eski cevap geçmez. |
| `8fe4420` | P-11, P-20, P-23 | John dosyası 0700 dizinde 0600 izinle, parola stdin'den; defterler atomik ve yalnızca sahibine açık; servislerde sınır ve kapatma. |
| `2b7e71e` | P-15, P-16, P-21, P-22 | Donukken `/ctf/durum` kesim anındaki değerleri verir; CTF dosyaları önbellekte; port doluyken anlaşılır ileti; tekdüze saat. |
| `022a5b4` | | 10 yeni arayüz metni 7 dilde. |

**Plandan sapmalar.**
- Adres başına katılım sınırı 5 yerine 40 yapıldı. Öğrenciler ayrı bir kablosuz yönlendiricinin arkasındaysa öğretmen hepsini tek adresten görür; 5 sınırı böyle bir sınıfı içeri almazdı. 40, bir sınıfı içeri alır ve tek cihazın sınıfı sahte adlarla doldurmasını yine engeller.
- Öğrenci artık `basladi` bildiriminde yüklü soru numarasını istemci tarafında sabitliyor (eskiden yalnızca arayüz yapıyordu); sunucu puanı yalnızca atanmış soru numarasıyla kabul ettiği için gerekliydi.
- Denetim sırasında kendi eklediğim `SinirliSunucu`'da bir hata bulundu ve aynı gün düzeltildi (port doluyken soket kapatılamıyordu; `2b7e71e`).
- Önceden var olan kararsız bir test düzeltildi (`test_poligon_uretecler`: gizli dizin `log`, yem dizin `blog` olunca yanlış kırmızı veriyordu).

**Doğrulanmayanlar (VM gerekir).**
- Öğrenci ve öğretmen arayüzündeki zamanlayıcı değişiklikleri gerçek ekranda denenmedi; testler kaynak düzeyinde ve GTK'siz mantık üzerinde.
- İki makineli gerçek sınıf: katılım, soru atama, soru geçişi, atma, öğretmen uygulamasını kapatma.
- Ağ kesintisi: öğrenci bağlıyken öğretmen makinesinin ağını 20-30 sn kesip geri açınca öğrencinin kendiliğinden toparlanması.
- `ufw status` çıktısının Türkçe yerelde `DENY` sözcüğünü aynen yazıp yazmadığı (bu denetimin kapsamı dışında kaldı, ufw-01 doğrulaması buna bağlı).

**Açık kalan.** P-10 (düz HTTP, bütün arayüzlerde dinleme) karar bekliyor; seçenekler 1.5'te.

**Ayrı depo.** `CarotOS-Poligon` deposu bu değişikliklerle henüz eşitlenmedi.
