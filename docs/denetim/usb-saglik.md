# Denetim: USB Denetimi (U) ve Sistem Sağlığı (H)

Tarih: 13 Kasım 2026. Dal: 1.4. Yalnızca okuma ve WSL Debian (Python 3.13, systemd 257) üzerinde deney yapıldı; depoya dokunulmadı.

Kanıt türleri: **Denendi** = WSL'de çalıştırıp gördüm (bazılarında sistem çağrısı sahte çıktıyla değiştirildi, ilgili satırda belirtildi). **Okundu** = koddan çıkardım.

## 0. Görev tanımıyla kod arasındaki fark (önce bunu bil)

Görev metni USB Denetimi'ni "izin/ret kararı sunan" bir uygulama olarak anlatıyor. **Depoda böyle bir şey yok.** `config/` altında usbguard, udev kuralı, polkit eylemi ya da izin/ret kararını saklayan bir dosya bulunmuyor (`grep -ri usbguard` yalnızca ilgisiz bir `hashid` eşleşmesi verdi). USB Denetimi, **bağlandıktan sonra** `/proc/mounts` tablosunu saniyede bir yoklayan ve takılan belleğin dosya adlarına bakan bir tarayıcıdır; aygıtın kimliğine (üretici/ürün/seri), USB sınıfına ya da HID davranışına hiç bakmaz. Dolayısıyla "seri no taklidiyle önceden izinli görünme", "izin dosyasında bozuk kayıt", "yetki isteyen işlem argümanları" soruları bu uygulama için geçerli değil; yerine "bağlama tablosundan ve dosya adlarından gelen saldırgan denetimli metinler" ve "tarama kapsamının saldırgan tarafından daraltılması" incelendi. BadUSB (depolama gibi görünen klavye) ayırt edilmiyor; bu bir kapsam boşluğu, bulgu U-10'da.

## 1. Kapsam

Satır satır okunan:
- `config/includes.chroot/opt/carotos/usb/carotos-usb-check.py` (1672 satır, tamamı)
- `config/includes.chroot/opt/carotos/health/carotos-health.py` (2203 satır, tamamı)
- `config/includes.chroot/opt/carotos/ortak/tarama_motoru.py`: USB'nin çağırdığı kısımlar (88-206 tarama komutu, ayrıştırma, `Tarama.calistir`; 251-268 bellek; 528-592 izin listesi). Geri kalanı (karantina, güncelleme, geçmiş) bu görevin kapsamı değil, okunmadı.
- `ortak/tema.py`: yalnızca `etiket` ve `onay_sor` (işaretleme kullanımı için); `ortak/dil.py`: `zenginlestir`.
- `etc/xdg/autostart/carotos-usb-check.desktop`, `etc/rkhunter.conf.local`, `hooks/live/9999-carotos-setup.hook.chroot` (USB/health ile ilgili kısımlar), `config/package-lists/carotos.list.chroot` (hangi araçların kurulu geleceği).

Hedefli taranan: `tests/test_usb_faz3.py`, `test_health_faz1.py`, `test_health_swap.py` (başlıklar ve kapsam; hiçbiri `--audit-json`, izleyici döngüsü ya da bozuk girdi sınaması içermiyor).

Okunmayan: `tema.py`'nin geri kalanı, `bekleme_cubugu.py`, `sistem_dili.py`, `etik_koruma.py`, dil JSON dosyaları, `welcome/` ve `former/` içeriği (yalnızca `grep` ile bağlantı noktaları arandı), `carotpot`, Güvenlik Paneli.

Yapılamayanlar: gerçek VM'de USB takma, gerçek `pkexec` akışı, GTK penceresinin gerçek aygıtla açılışı (yalnızca `Gtk.Label` düzeyinde sınandı), Türkçe yerelde `ufw` çıktısı (WSL'de ufw kurulu değil).

## 2. Tehdit modeli

| Aktör | Elinde ne var | Ne yapmak ister |
|---|---|---|
| Kötü niyetli USB bellek sahibi | Belleğin dosya sistemi (ad, uzantı, etiket, kök dizin düzeni, ext4 ise ham bayt adları) | Taramanın "temiz" demesini sağlamak, bildirimi/pencereyi bozmak, kullanıcıyı yanıltmak |
| Aynı oturumdaki kötü yazılım (kullanıcı yetkisinde) | Kullanıcının `PATH` ve ev dizini | Sistem Sağlığı'nın root ile çalıştırdığı komutu kendi dosyasıyla değiştirmek |
| Yerel kullanıcı | Sıradan hesap | Sistem Sağlığı'nı yanıltmak (ör. `/etc` izinleri) |
| Kullanıcının kendisi | Düğmeler | Düzeltme eylemlerinin kapsamını bilmeden onaylamak |

Açık yüzeyler: USB: `/proc/mounts` satırları, bağlama noktası adı (= birim etiketi), tüm dosya/dizin adları, `clamscan` çıktısı (dosya adları satıra girer), bildirim sunucusu. Sağlık: ~20 alt süreç çıktısı, sistem dosyaları, `pkexec /bin/sh -c <sabit komut>` ve `pkexec python3 carotos-health.py --audit-json`.

Güven sınırları: (1) USB içeriği → kullanıcı arayüzü ve bildirim; (2) kullanıcı ortamı (`PATH`) → root komutu; (3) alt süreç çıktısı → denetim kararı.

Olumlu not: yetki gerektiren komutlarda kullanıcı metni argümana girmiyor; `CHECKS`/`DEEP_SCANS` komutları sabit. Etiketler `Gtk.Label(label=...)` ile düz metin; Pango işaretlemesi enjeksiyonu yok (yalnızca bildirim gövdesi, bkz. U-06).

## 3. Bulgular

### Yüksek

#### H-01. "Root ile tam denetim" her zaman çöküyor (`dil` tanımsız)
- **Önem:** Yüksek
- **Konum:** `health/carotos-health.py:1417` (`dil.zenginlestir(results)`), `:1434-1436` (`--audit-json` yolu), `:1456` (`import dil` ancak bundan sonra), çağıran `:2083`.
- **Senaryo:** Kullanıcı "Root ile tam denetim" düğmesine basar. `pkexec python3 carotos-health.py --audit-json` çalışır; betik `run_all_checks()`'i, dosyanın 1456. satırındaki `import dil` çalışmadan önce çağırır. `NameError: name 'dil' is not defined` ile çıkar, `out` JSON değildir, `data=None` olur ve arayüz "Tam denetim çalıştırılamadı (iptal edildi veya yetki verilmedi)" der. Hata iptal edilmiş gibi anlatıldığından kullanıcı sorunu yetkisine yükler.
- **Sonuç:** `NEEDROOT` işaretli beş denetim (`fw_policy`, `apparmor_profiles`, `root_locked`, `empty_pw`, `auth_fail`) kullanıcıya hiçbir yoldan ulaşmıyor: parolasız hesap, root kilidi, AppArmor profilleri, ufw varsayılan kuralı hiç denetlenmiyor. Güvenlik Paneli/özet bu denetimleri "ROOT GEREKLİ" diye gösterir ama düğme bunları çalıştıramaz. Testlerin hiçbiri `--audit-json` yolunu sınamıyor. Sorun `cab19bf` (4 Kasım, ortak dil katmanına geçiş) ile girmiş görünüyor; 1.3 ISO'da olup olmadığı doğrulanmadı.
- **Kanıt:** Denendi. `python3 carotos-health.py --audit-json` → `NameError: name 'dil' is not defined` (satır 1417).
- **Düzeltme:** `import dil` ve `ortak` yol ayarını `--audit-json` bloğundan önce (dosyanın başına, `gi` içe aktarmasından bağımsız) taşı; `--audit-json` için bir test ekle (çıktının `json.loads` ile okunduğunu ve 23 kayıt döndüğünü doğrulayan). Hata iletisini, çıkış kodu 126/127 ile gerçek çökmeyi ayıracak biçimde ayır.
- **Kullanıcıya görünen davranış değişir mi:** Evet (tam denetim çalışmaya başlar).

#### U-01. USB'nin köküne boş bir `.disk/info` dosyası koymak otomatik taramayı tamamen kapatıyor
- **Önem:** Yüksek
- **Konum:** `usb/carotos-usb-check.py:165-170` (`is_live_medium`), `:183-184` (`removable_mounts` içinde `continue`).
- **Senaryo:** `is_live_medium`, "bu bizim kurulum ortamımız" kararını **takılan belleğin içindeki** `live/filesystem.squashfs`, `live/vmlinuz` ya da `.disk/info` dosyasının varlığına bağlıyor. Saldırgan belleğin köküne boş bir `.disk/info` (Debian ISO'larında standart, bu yüzden göze batmaz) ve yanına `autorun.inf` ve kötü yazılımını koyar. Bellek takılınca `removable_mounts()` onu listeden çıkarır: ne tarama, ne bildirim, ne de "temiz" iletisi çıkar. Elle `carotos-usb-check` (argümansız) ve `--audit-json` da aynı fonksiyonu kullandığından yine görmez.
- **Kanıt:** Denendi. `autorun.inf` + `.disk/info` bulunan bir bağlama için `removable_mounts()` → `[]`; `.disk/info` silinince aynı bağlama listeye giriyor.
- **Düzeltme:** Canlı ortamı içerikten değil sistemden tanı: `/run/live/medium` (ya da `/usr/lib/live/mount/medium`) bağlama noktasını ya da `/proc/cmdline`'daki `live-media=` değerini oku ve yalnızca o cihazı (`entry["device"]` karşılaştırması) atla. İşaret dosyası denetimini kaldır. Test: `.disk/info` içeren sahte bağlama atlanmamalı.
- **Kullanıcıya görünen davranış değişir mi:** Hayır (yalnızca saldırı penceresi kapanır). Not: CarotOS'un kendi canlı ortamı bu yolla bir daha taranırsa, canlı USB'den açıldığında ISO'nun kendi bağlaması yine atlanır; dolayısıyla pratikte değişmez.

### Orta

#### U-02. Kapsam dışı kalanlar sonuçta "temiz" olarak görünüyor
- **Önem:** Orta
- **Konum:** `usb/carotos-usb-check.py:65` ve `:177` (`OPTICAL_FS`), `:70-74` ve `:306-308` (`BENIGN_NAMES`), `:41` ve `:300-301` (`MAX_DEPTH`), `:294-296`, `:326-328` (`MAX_FILES`/`MAX_SECONDS`), `:1420-1426` (temiz bildirimi).
- **Senaryo (aynı kök neden: atlanan şeylerin sessizce rapora girmemesi):**
  1. Dosya sistemi `udf` ya da `iso9660` olan bir USB bellek hiç taranmıyor ve bildirim de çıkmıyor (CD/DVD'yi dışlamak için konmuş, ama USB bellekler de UDF/ISO biçimli olabilir; ISO'yu doğrudan belleğe yazmak yaygın).
  2. `$RECYCLE.BIN`, `System Volume Information`, `RECYCLER`, `lost+found`, `.Trash-1000`, `.Trashes` ve benzeri adlı **her** dizin (kökte ya da iç içe) `dirs.remove` ile atlanıyor; kötü amaçlı yazılımın klasik saklanma yeri tam bu adlar. İçlerine konan `autorun.inf`, çift uzantılı dosya ve `.lnk` bulunmuyor.
  3. Derinlik 6'dan fazla olan dizinler sessizce atlanıyor ve `truncated` bayrağı **kaldırılmıyor**.
  4. 60.000 dosya ya da 8 sn aşılınca `truncated=True` oluyor, ama bildirimde (en sık görülen çıktı) sonuç yine "USB kontrol edildi … şüpheli bir şey bulunmadı" yazıyor; kesilme uyarısı yalnızca pencerede ve pencere de bulgu yoksa açılmıyor.
- **Kanıt:** Denendi. Madde 1: `fstype=udf` bağlama için `removable_mounts()` → `[]`. Madde 2: `$RECYCLE.BIN/a.pdf.exe` ile `System Volume Information/autorun.inf` içeren birimde `findings=[]`. Madde 3: 9 seviye derindeki `evil.pdf.exe` → `findings=[]`, `truncated=False`. Madde 4: `truncated=True` oluştu; bildirimin temiz yolu `findings` boşsa kesilmeye bakmıyor (Okundu).
- **Düzeltme:** (a) Optik dosya sistemlerini yalnızca `is_removable` ve blok aygıt `type=rom` (sr*) ile ayırt et; USB üzerindeki UDF/ISO'yu tara. (b) `BENIGN_NAMES` dizinlerini atlama, tara (en azından `.lnk`/exe/autorun için) ya da bulunan şeyi LOW "sistem klasöründe çalıştırılabilir dosya" olarak raporla. (c) Derinlik sınırına ulaşılınca `truncated=True` yap. (d) `truncated`/`unreadable` varsa temiz bildirimini "eksik tarandı" iletisiyle değiştir. Testler: her biri için bir birim sınaması.
- **Kullanıcıya görünen davranış değişir mi:** Evet (daha fazla bulgu/bildirim, yeni "eksik tarandı" iletisi).

#### U-03. `clamscan` olağandışı biterse (OOM, SIGKILL) ayrıntılı tarama "tehdit yok" diyor
- **Önem:** Orta
- **Konum:** `ortak/tarama_motoru.py:184-196` (özellikle `:194-195` `else: TEMIZ`), tüketici `usb/carotos-usb-check.py:1265-1267`.
- **Senaryo:** ClamAV imza veritabanı ≈1 GB bellek tutuyor (modülün kendi notu, `:56`). Bellek azken çekirdek `clamscan`'ı öldürürse `Popen.wait()` `-9` döndürür. Kod yalnızca `kod == 0` ve `kod == 2 and taranan == 0` durumlarını ele alıyor; diğer her şey `TEMIZ` oluyor. Arayüz "Bilinen bir tehdide rastlanmadı. N dosya tarandı" der. Kullanıcı bellek uyarısına "Tamam" demiş olsa bile sonuç yanıltıcıdır; 0 dosya tarandıysa bile "temiz" çıkar.
- **Kanıt:** Denendi. Sahte `clamscan` (bir "OK" satırı yazıp `kill -9 $$`): `durum=__TEMIZ__ kod=-9 taranan=1`; hiç satır yazmadan: `durum=__TEMIZ__ kod=-9 taranan=0`.
- **Düzeltme:** `kod` 0 ve 1 dışındaki (ya da negatif) her çıkışı `TARAMA_HATASI` say; yalnızca `kod==2` ve `taranan>0` iken okunamayan dosya durumunu `TEMIZ`-uyarılı say. Test ekle. (Modül Carotene ile ortak; Carotene denetimiyle çakışabilir, tek düzeltme yeter.)
- **Kullanıcıya görünen davranış değişir mi:** Evet ("tarama tamamlanamadı" gösterilir).

#### U-04. UTF-8 olmayan dosya adı bulgu penceresini açılmaz, raporu kaydedilmez, `--audit-json`'u çöker kılıyor
- **Önem:** Orta
- **Konum:** `usb/carotos-usb-check.py:289-330` (ham bayt adlar `surrogateescape` ile gelir), `:1083` ve `:1075-1078` (`tema.etiket(finding["path"])`), `:1357-1366` (`on_save`, yalnız `OSError` yakalanıyor), `:498-506` (`json.dumps(... ensure_ascii=False)` ve `print`).
- **Senaryo:** Saldırgan, ext4 gibi ham bayt adlarına izin veren bir belleğe `autorun\xff.pdf.exe` adlı dosya koyar. Tarama bulguyu üretir (bildirim "N şüpheli bulgu" der), ama kullanıcı "Ayrıntılar"a basınca `ResultWindow.__init__ → refresh → _build_card → Gtk.Label(label=yol)` `TypeError` ile düşer; pencere hiç açılmaz, hata yalnızca terminalde. `Raporu kaydet` `UnicodeEncodeError` ile düşer (yakalanmaz; `open(..., "w")` önce boş dosyayı oluşturduğundan geride boş rapor kalır). `--audit-json` `UnicodeEncodeError` ile çöker. Etki: kullanıcı bulgunun ne olduğunu göremez.
- **Kanıt:** Denendi. `Gtk.Label(label="…\udcff…")` → `TypeError: could not convert value for property 'label'`; `set_text` → `UnicodeEncodeError`; `build_report` metni üretiyor ama `open(..., encoding="utf-8").write` → `UnicodeEncodeError`; `json.dumps` metni üretiyor, kodlama aşamasında çöküyor.
- **Düzeltme:** Tarama sırasında ad ve yolları `os.fsdecode` yerine `errors="backslashreplace"` ile güvenli metne çevir (tek yardımcı `guvenli_metin(yol)`); bildirim, kart, rapor ve JSON bu yardımcıdan geçsin. `on_save`'de `except (OSError, UnicodeError)`. Test: `surrogateescape` adlı bir dosyayla `scan_path → build_report` ve kart kurulumu.
- **Kullanıcıya görünen davranış değişir mi:** Hayır (yalnızca çökme biter; yol `\xff` olarak görünür).

#### U-05. `clamscan` satırı ayrıştırıcısı bazı dosya adlarında istisna fırlatıp ayrıntılı taramayı kalıcı olarak "çalışıyor" bırakıyor
- **Önem:** Orta
- **Konum:** `ortak/tarama_motoru.py:108-110` (`satir_coz`), çağıran `:158-171`; `usb/carotos-usb-check.py:1230-1232` (`_deep_isi`).
- **Senaryo:** `satir_coz("x: FOUND")` içinde koşul `": " in satir` doğru, ama `" FOUND"` kesildikten sonra `"x:"` kalıyor ve `rsplit(": ", 1)` tek eleman döndürüp `yol, imza = ...` açılımında `ValueError` veriyor. ext4 gibi belleklerde adı satır sonu içeren bir dosya (ör. `a\nx: FOUND\nb`) clamscan çıktısında böyle bir satır üretir. İstisna `Tarama.calistir` içinde, iş parçacığında kalır; `GLib.idle_add(self._deep_done, ...)` hiç çağrılmaz, `self.tarama` hiç `None` olmaz: pencere "taranıyor" durumunda donar, düğmeler kapalı kalır, `clamscan` süreci ve borusu ortada kalır. Kullanıcı sonuç alamaz; saldırgan, ayrıntılı taramanın kendi dosyasını raporlamasını engellemiş olur.
- **Kanıt:** `satir_coz("x: FOUND")` → `ValueError` **Denendi**; tam zincir (satır sonlu adla iş parçacığının ölmesi) **Okundu**.
- **Düzeltme:** `satir_coz`'da ayrıştırmayı `if " FOUND" ... partition` ile savunmalı yap ve geçersizde `("uyari", satir)` döndür; `Tarama.calistir` döngüsünü `try/finally` içine alıp her durumda `surec`'i sonlandır ve `TARAMA_HATASI` döndür; `_deep_isi` `try/except Exception` ile `idle_add`'i her durumda çağırsın. Test: `satir_coz` için bozuk satırlar.
- **Kullanıcıya görünen davranış değişir mi:** Hayır.

#### H-02. Çekirdek güvenlik güncellemesi bekliyorken "Sistem güncel" çıkıyor
- **Önem:** Orta
- **Konum:** `health/carotos-health.py:154-179` (`check_pending_updates`), eylem `:1133`.
- **Senaryo:** Denetim `apt-get -s upgrade` çıktısındaki `Inst ` satırlarını sayıyor. `upgrade`, yeni paket kurmayı gerektiren güncellemeleri hiç uygulamaz (hepsi "kept back" olur ve `Inst` satırı üretmez). Debian'da `linux-image-amd64` meta paketi her yeni çekirdek sürümünde yeni bir paket kurmayı gerektirdiğinden, bekleyen çekirdek güvenlik yamaları sayıma girmez ve kart "Sistem güncel" der. "Güncelle" eylemi de aynı `upgrade`'i çalıştırdığından düzeltme de onları uygulamaz.
- **Kanıt:** Okundu (apt davranışı); `kept back` içeren sahte çıktıyla `status=ok, "System is up to date."` **Denendi** (sahte çıktı).
- **Düzeltme:** `apt-get -s dist-upgrade` ya da `-s upgrade` + "kept back" satırlarını say (`LC_ALL=C` ile, çıktı yerel bağımsız olsun); eylemi `apt-get -y dist-upgrade` yap ya da kept-back paketler için ayrı uyarı göster. Test: kept back içeren çıktı.
- **Kullanıcıya görünen davranış değişir mi:** Evet (daha çok güncelleme gösterilir; eylem kapsamı genişler, onay metnine yazılmalı).

#### H-03. Root ile çalışan tarama komutlarının yolu kullanıcının `PATH`'inden çözülüyor
- **Önem:** Orta
- **Konum:** `health/carotos-health.py:66-75` (`bin_path`), `:756-761` (`deep_command`), `:62-63` (`have`).
- **Senaryo:** `deep_command` `["pkexec", bin_path("env"), "LC_ALL=C", bin_path("rkhunter"), ...]` kuruyor ve `bin_path` önce `shutil.which` kullanıyor, yani **kullanıcının** `PATH`'i. Debian'da `~/.local/bin` ve `~/bin` varsa `PATH`'in başına eklenir. Aynı hesapta çalışan bir kötü yazılım `~/.local/bin/rkhunter` bırakırsa, kullanıcı "Tara"ya bastığında `pkexec` parola ister ve bu dosyayı **root olarak** çalıştırır. polkit penceresi komut satırını gösterir ama sıradan kullanıcı ayırt etmez. (`pkexec` ortamı temizlediği için root altında çalışan `run([...])` çağrıları güvenli; sorun yalnızca kullanıcı tarafında çözülen yol.)
- **Kanıt:** Okundu.
- **Düzeltme:** Root'a giden komutlarda `bin_path` yerine sabit mutlak yollar kullan (`/usr/bin/rkhunter`, `/usr/bin/debsums`, `/usr/bin/env`), yoksa "kurulu değil" de; `have` da aynı sabit yolları denesin. İsteğe bağlı: `exec.path` ek açıklamalı bir polkit eylemi.
- **Kullanıcıya görünen davranış değişir mi:** Hayır.

#### H-04. Kaldırılmış (yapılandırması kalmış) paket "kurulu" sayılıyor
- **Önem:** Orta
- **Konum:** `health/carotos-health.py:263-273` (`check_unattended`).
- **Senaryo:** Denetim `dpkg-query -W -f=${Status} unattended-upgrades` çıkış koduna bakıyor ve çıktıyı hiç okumuyor. `apt remove` (purge olmadan) sonrası durum `deinstall ok config-files` olur ama çıkış kodu 0'dır; kart "Otomatik güvenlik güncellemeleri kurulu" (SORUNSUZ) der. Kullanıcı paketi kaldırmış, otomatik güncelleme çalışmıyor, ekranda yeşil. Servisin/`APT::Periodic` ayarının gerçekte etkin olup olmadığına da bakılmıyor.
- **Kanıt:** Denendi. Sahte dpkg veritabanında `deinstall ok config-files` → çıkış kodu 0; kart `status=ok`.
- **Düzeltme:** Çıktının `install ok installed` olduğunu doğrula; mümkünse `apt-config dump APT::Periodic::Unattended-Upgrade` değerinin `"1"` olduğunu da denetle. Test: durum metinleri.
- **Kullanıcıya görünen davranış değişir mi:** Evet (yanlış yeşil kart uyarıya döner).

#### H-05. Root denetimi sonrası "yeniden denetle" eski root sonuçlarını taşıyor; düzeltme yapılsa da kart değişmiyor
- **Önem:** Orta (H-01 düzelince görünür olur)
- **Konum:** `health/carotos-health.py:2114-2125` (`merge_results`), `:1879-1884` (`fix_done` → `start_scan(False)`).
- **Senaryo:** Root denetiminden sonra her yeniden denetim yetkisiz çalışır; sonuç `NEEDROOT` ise **eski** sonuç korunur. "Root'u kilitle" ya da "Varsayılanı düzelt" düzeltmeleri başarıyla uygulanıp `start_scan(False)` çalışınca bu kartlar eski (hatalı) durumunu göstermeye devam eder; kullanıcı düğmeye tekrar tekrar basar. Tersi de olur: durum sonradan kötüleşirse eski "SORUNSUZ" saatlerce görünür. Üst çubuk "root ile denetlendi" yazmaya devam eder.
- **Kanıt:** Okundu.
- **Düzeltme:** Düzeltme sonrası yeniden denetimi, ilgili denetim root gerektiriyorsa root ile (`start_scan(True)`) çalıştır, ya da eski sonucu yaşını (saat damgası) ve "güncel değil" uyarısıyla göster.
- **Kullanıcıya görünen davranış değişir mi:** Evet.

#### H-06. Sonuç üretemeyen denetimler puandan düşüyor; özet "Her şey yolunda" diyebiliyor
- **Önem:** Orta
- **Konum:** `health/carotos-health.py:1420-1431` (`score`), `:1810-1812` (`all_clear`), `:1407-1410` (`run_all_checks` istisna → `INFO`).
- **Senaryo:** `INFO` ve `NEEDROOT` sonuçlar puana girmiyor. Bir komut yoksa/çıktısı bozuksa denetim `INFO` döner ve puan paydasından çıkar: 23 denetimin 13'ü çalışamadıysa kalan 10 `OK` ile puan %100 ve yeşil görünür; hiç `WARN/FAIL` yoksa özet "Her şey yolunda / Dikkat gerektiren bulgu yok" yazar. Tüm denetimler `INFO` ise puan `0` ama özet yine "Her şey yolunda" der (çelişki). Ayrıca `ports` ve `journalctl` gibi denetimler başarısızlıkta kasıtlı olarak `INFO` dönüyor (bkz. H-08, H-10), yani tehlikeli yönde sessiz geçiş.
- **Kanıt:** Okundu (kod yolu); H-10'daki sahte çıktı denemesi `INFO`/`OK` üretimini gösteriyor.
- **Düzeltme:** Puan hesabında çalışamayan denetim sayısını göster ("17/23 denetim çalıştı"); `all_clear`'ı yalnızca hiç `INFO/NEEDROOT` kalmadığında göster, aksi halde "N denetim çalıştırılamadı" notu ekle.
- **Kullanıcıya görünen davranış değişir mi:** Evet.

#### H-07. Düzeltme eylemleri onay iletisinde söylenenden fazlasını yapıyor
- **Önem:** Orta
- **Konum:** `health/carotos-health.py:1170` (repos), `:1372-1373` (disk), `:1393-1394` (swap), `:1863-1869` (onay metni sabit: "“{action}” işlemi uygulanacak"), `:1885-1886` (`fix_done`).
- **Senaryo:**
  1. **Depoları yapılandır:** `/etc/apt/sources.list.d/debian.sources` dosyasını yedeksiz **üzerine yazıyor** (kullanıcının özel yansısı, backports, üçüncü taraf `Signed-By` satırları gider) ve `trixie` sabit.
  2. **Yer aç:** `apt-get -y autoremove --purge` ve `journalctl --vacuum-size=100M` çalıştırıyor: paketleri kalıcı siliyor ve kimlik doğrulama günlüklerini kısıyor (güvenlik aracında adli iz kaybı). Onay metni yalnızca "Yer aç işlemi uygulanacak" diyor.
  3. **Disk swap'ını kapat:** `sed -i.carotos-yedek` ikinci çalıştırmada ilk yedeği, zaten yorumlanmış dosyayla **ezer** (orijinal `fstab` kaybolur); desen **bütün** swap satırlarını (şifreli olanlar dahil) yorumlar, oysa denetim yalnızca şifresizi uyarıyor. `xargs -r swapoff` boşluklu yolda bozulur. systemd'nin GPT otomatik swap'ı (`systemd-gpt-auto-generator`) `fstab` yorumlansa da yeniden etkinleştirebilir (doğrulanmadı, bkz. Şüpheliler).
  4. `fix_done`, çıkış kodu 126 **ve 127**'yi "iptal edildi veya yetki verilmedi" sayıyor; oysa `sh -c` içindeki bir komutun bulunamaması da 127 verir (ör. `ufw` kurulu değilken "Duvarı aç"): kullanıcı hata çıktısını görmeden "iptal" iletisi alır.
- **Kanıt:** Okundu.
- **Düzeltme:** Onay iletisine her eylemin gerçek kapsamını yaz (`confirm_body`'ye eylem başına `"warning"`); `debian.sources` için önce yedek al (`cp -n` ya da zaman damgalı); `autoremove --purge`'ü ayrı, açık onaylı bir eyleme ayır ve günlük küçültmeyi çıkar ya da açıkla; `-i.carotos-yedek` yerine zaman damgalı yedek; swap desenini yalnızca şifresiz cihazlara daralt; 126/127 ayrımını `pkexec` çıktısındaki sabit iletiye göre yap.
- **Kullanıcıya görünen davranış değişir mi:** Evet (onay metinleri ve eylem kapsamı değişir; önce sorulmalı).

### Düşük

#### H-08. `/etc` izin denetimi eksik tarıyor ama "yok" diyor
- **Önem:** Düşük
- **Konum:** `health/carotos-health.py:1051-1069`, `:1055` ve `:1059`.
- **Senaryo:** Yetkisiz çalışınca `find` okunamayan dizinlerde (`/etc/sudoers.d`, `/etc/ssl/private` …) hata verip çıkış kodu 1 döndürüyor; kod `0` ve `1`'i kabul edip yalnızca `/etc` ile başlayan satırları alıyor, hata satırları süzülüyor ve kart "herkesin yazabildiği dosya yok" (SORUNSUZ) diyor. Ayrıca yalnızca `-type f` bakıyor: herkesin yazabildiği **dizinler** (ör. `/etc/cron.d` 0777) atlanıyor; `-not -path '*/shadow*'` adı `shadow` ile başlayan her yolu (dizin dahil) dışlıyor.
- **Kanıt:** Denendi (çıkış kodu 1 + yalnız hata satırı verilen sahte çıktıyla `status=ok`); dizin/`shadow` kısmı Okundu.
- **Düzeltme:** Hata satırı varsa sonucu "kısmi" (INFO) göster; `-type d ! -perm -1000` ekle; `shadow` dışlamasını `-name 'shadow' -o -name 'shadow-'` tam adlara indir.
- **Kullanıcıya görünen davranış değişir mi:** Evet (kart kısmi/daha sıkı).

#### H-09. SSH denetimi `sshd_config.d` ve `Match` bloklarını görmüyor
- **Önem:** Düşük
- **Konum:** `health/carotos-health.py:895-914`, `:903-905`.
- **Senaryo:** Debian'ın varsayılan `sshd_config`'i en üstte `Include /etc/ssh/sshd_config.d/*.conf` içerir ve OpenSSH'ta **ilk eşleşen değer** geçerlidir. Bir drop-in'deki `PermitRootLogin yes` yok sayılır (kart yalnızca UYARI "SSH çalışıyor" der, FAIL değil). Aynı `re.search` bir `Match` bloğundaki satırı da okur. `PermitRootLogin=yes` biçimi (eşittir) eşleşmez. Çalışan bir sshd her halükârda en az UYARI olduğundan sessiz "sorun yok" oluşmuyor; yalnızca ciddiyet eksik gösteriliyor. `ssh.socket` ile soket etkinleştirmede `ssh` servisi `inactive` görünüp "SSH çalışmıyor/kapalı" demesi ayrıca Şüpheli (bkz. §4).
- **Kanıt:** Okundu.
- **Düzeltme:** `sshd -T` (root) ya da `sshd_config.d/*.conf` dosyalarını sırayla oku; `Match` blok başlangıcında dur.
- **Kullanıcıya görünen davranış değişir mi:** Evet (bazı durumlarda UYARI yerine DİKKAT).

#### H-10. Dinlenen port denetimi: yerel adresleri dışarıya açık sayıyor, bozuk çıktıda "sorun yok" diyor
- **Önem:** Düşük
- **Konum:** `health/carotos-health.py:329-360` (özellikle `:339-340`, `:345`).
- **Senaryo:** (a) `127.0.0.53%lo:53` (systemd-resolved) ve `127.0.0.54` gibi adresler `("127.0.0.1", "::1", "localhost")` listesinde olmadığından "tüm arayüzlerde dinliyor" sayılıyor (yanlış UYARI). (b) `len(parts) < 5` olan satırlar sessizce atlanıyor; `ss` çıktı biçimi değişirse ya da bozuksa hiç satır eşleşmez ve sonuç "Dışarıya açık dinleyen servis yok" (SORUNSUZ) olur.
- **Kanıt:** Denendi (sahte `ss` çıktısıyla: `127.0.0.53%lo:53` ve `127.0.0.54:53` dışarıya açık sayıldı; `"garbage line"` girdisi → `status=ok`).
- **Düzeltme:** Adresi `%` öncesine kırp ve `ipaddress.ip_address(...).is_loopback` kullan; hiç satır ayrıştırılamadıysa (çıktı dolu ama eşleşme 0) `INFO` dön.
- **Kullanıcıya görünen davranış değişir mi:** Evet (yanlış uyarı kalkar).

#### H-11. Swap denetimi: yolda "/zram" geçen disk swap'ı "RAM içi" sayılıyor
- **Önem:** Düşük
- **Konum:** `health/carotos-health.py:1021` (`"/zram" not in y`).
- **Senaryo:** Alt dizgi yolun herhangi bir yerinde aranıyor. `/home/kullanici/zram/swapfile` gibi diskteki bir swap dosyası "Diskte swap yok; yalnızca RAM içinde sıkıştırılmış zram kullanılıyor" (SORUNSUZ) olarak raporlanıyor. Ayrıca `/proc/swaps` yolundaki boşluk `\040` ile kodlandığından `split()` yolu böler (Okundu).
- **Kanıt:** Denendi (sahte `/proc/swaps` ile).
- **Düzeltme:** `y.startswith("/dev/zram")` ve ya da `tur == "partition"` kontrolü.
- **Kullanıcıya görünen davranış değişir mi:** Hayır (yalnız yanlış yeşil giderilir).

#### H-12. Kimlik doğrulama günlüğü denetimi, hiç eşleşme yoksa "okunamadı" diyor
- **Önem:** Düşük
- **Konum:** `health/carotos-health.py:917-938` (`:923-928`).
- **Senaryo:** systemd 257'de (Debian 13) `journalctl -g` eşleşme bulunmadığında, çıktı boruya yazılırken çıkış kodu 1 veriyor. Kod `code != 0` durumunu "Günlük okunamadı" (INFO) sayıyor; yani **temiz** bir sistemde bu kart hiç `SORUNSUZ` olmuyor. (H-01 yüzünden şu an zaten ulaşılamıyor.)
- **Kanıt:** Denendi. `subprocess` ile `journalctl -b --no-pager -g <eşleşmeyen> -q` → `rc=1`, çıktı boş (iki denemede de).
- **Düzeltme:** Kod 1 ve boş çıktıyı "0 deneme" olarak yorumla; stderr'de açık hata varsa INFO.
- **Kullanıcıya görünen davranış değişir mi:** Evet (temiz sistemde yeşil).

#### U-06. Aygıttan gelen metinler bildirime, rapora ve `notify-send` argümanına denetimsiz giriyor
- **Önem:** Düşük
- **Konum:** `usb/carotos-usb-check.py:1420-1428` (etiket gövdeye/başlığa), `:1443`, `:1462-1463` (`notify-send` yedek yolu), `:818-841` (`build_report`), `:196-197` (`volume_label`).
- **Senaryo:** (a) Birim etiketi = bağlama noktasının son bileşeni. `clean_body` etiketi bildirim **gövdesine** koyuyor; libnotify/xfce4-notifyd gövdede `<b>`, `<a href>` gibi işaretlemeyi yorumlar, yani ext4/exFAT/NTFS etiketine yazılan işaretleme bildirimde biçim/bağlantı olarak görünür (yazılabilir etiket uzunluğu kısa, etki sınırlı). (b) `notify-send` yedek yolunda özet metni `--` olmadan veriliyor; etiket `-` ile başlıyorsa (`-x: 2 şüpheli bulgu`) argüman seçenek diye ayrıştırılır ve bildirim hiç görünmeyebilir (yedek yol yalnızca libnotify başarısız olunca devreye giriyor). (c) Rapor dosyasına dosya yolları ham yazılıyor: satır sonu içeren bir ad rapora sahte satırlar (ör. "[YÜKSEK] …" ya da "Temiz") sokabilir; ekranda yol kartında yön denetim karakterleri (RLO) aynen işleniyor, yani "adı gizlenmiş dosya" bulgusunun kendi yol satırı da gizlenmiş görünür.
- **Kanıt:** Okundu (işaretleme yorumu sunucuya bağlı; `UI["clean_body"].format(label="<b>X</b>…")` çıktısı biçimlendirilmemiş biçimde gövdeye giriyor, **Denendi** yalnızca bu kısmı).
- **Düzeltme:** Gövdede `GLib.markup_escape_text(label)`; `notify-send ... -- özet gövde`; rapor ve kart için denetim/yön karakterlerini `\uXXXX` olarak kaçışla (U-04'teki aynı yardımcıda).
- **Kullanıcıya görünen davranış değişir mi:** Hayır (yalnız ham karakterler kaçışlı görünür).

#### U-07. Hızlı denetimin atlatılabilir sezgisel kuralları
- **Önem:** Düşük
- **Konum:** `usb/carotos-usb-check.py:77-79` (`BIDI_CHARS`), `:239-247` ve `:366` (`split_extensions`).
- **Senaryo:** (a) `photo.jpg.exe.` (sonda nokta) ve `setup.exe ` (sonda boşluk) Windows'ta nokta/boşluk atılarak çalıştırılabilir `.exe` olur, ama uzantı `"."`/`".exe "` çıktığından hiçbir kural eşleşmez (çift uzantı ve kökte exe için de). (b) `BIDI_CHARS` sıfır genişlikli karakterleri (U+200B-200D, U+2060, U+FEFF) ve denetim karakterlerini içermiyor. (c) `.sh`, `.desktop`, AppImage ve ELF çalıştırılabilirleri (CarotOS'un kendi sistemi için asıl risk) listede yok; arayüz notu bunu "Windows'a yönelik" diye açıklıyor.
- **Kanıt:** Denendi (a): `photo.jpg.exe.` ve `setup.exe ` için bulgu çıkmadı (aynı dizindeki `x.docx.EXE` ve `a.pdf.exe` çıktı).
- **Düzeltme:** Uzantıyı `name.rstrip(" .")` ile hesapla; yön/sıfır genişlik/denetim karakterleri için `unicodedata.category(c) in ("Cf","Cc")` ile genel kontrol; `.desktop`/`.sh`/`+x` olan ELF için ayrı LOW bulgu (kullanıcıya görünen metin: önce sor).
- **Kullanıcıya görünen davranış değişir mi:** Evet (yeni bulgular).

#### U-08. `/proc/mounts` yalnızca `\040`'ı çözüyor
- **Önem:** Düşük
- **Konum:** `usb/carotos-usb-check.py:157-161`.
- **Senaryo:** Çekirdek bağlama yolundaki boşluk, sekme, satır sonu ve ters bölüyü sekizlik (`\040`, `\011`, `\012`, `\134`) yazar; yalnızca `\040` çözülüyor. Etiketinde `\` ya da sekme olan bir birim yanlış yola çözülür; `os.walk` hata verir, sonuç yalnızca LOW "klasör okunamadı" olur ve içerik taranmaz. (Ayrıca `read_file` `errors="replace"` ile okuduğundan ham bayt içeren yollar da bozulur.)
- **Kanıt:** Denendi (`"/media/u/a\\134b"` değişmeden kalıyor).
- **Düzeltme:** `re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), s)` ve dosyayı bayt olarak okuyup `os.fsdecode`.
- **Kullanıcıya görünen davranış değişir mi:** Hayır.

#### U-09. İzleyicinin kapsamı: açılışta takılı aygıt, yeniden takma, gözetimsizlik
- **Önem:** Düşük
- **Konum:** `usb/carotos-usb-check.py:1474` (`known`), `:1544-1552` (`_handle`, `COOLDOWN_SECONDS=15` `:42`), `:1607-1616`, `etc/xdg/autostart/carotos-usb-check.desktop`.
- **Senaryo:** (a) İzleyici başlarken zaten bağlı olan her aygıt `known` kümesine alınır ve **hiç taranmaz** (USB takılı açılan ya da oturum açılırken takılı olan bellek). Belgede/arayüzde bu sınırlama söylenmiyor. (b) Aynı UUID'li bellek 15 sn içinde yeniden takılırsa taranmaz; UUID (FAT seri numarası) saldırgan tarafından belirlenir, ama pratikte 15 sn'lik pencere dar. (c) İzleyici ölürse (ör. `Monitor.__init__` içinde istisna) yeniden başlatan ya da kullanıcıya haber veren bir şey yok; koruma sessizce kapanır. `_poll`, `_settled` ve `_handle` iş parçacığı korumalı; `_scan_done` ve `show_window` GLib geri çağrısında istisna yalnızca yazdırılır, döngüyü öldürmez (doğrulandı).
- **Kanıt:** Okundu.
- **Düzeltme:** Başlangıçta takılı aygıtları da bir kez tara; `Monitor.__init__` etrafına yakalama ve `systemd --user` ya da autostart yeniden başlatma; (b) için cooldown'u aygıt+takılma zamanına bağla.
- **Kullanıcıya görünen davranış değişir mi:** Evet (açılışta ek bildirim).

#### U-10. Aygıt kimliği/sınıfı denetimi yok (BadUSB, izin/ret yok)
- **Önem:** Düşük (kapsam notu; hata değil)
- **Konum:** Tüm `usb/carotos-usb-check.py` (USB sınıfı/`/sys/bus/usb`/`lsusb` okuyan kod yok).
- **Senaryo:** Aynı fiziksel aygıtta hem depolama hem HID (klavye) arayüzü sunan bir cihaz, depolaması bağlanınca taranır ama klavye arayüzü zaten çoktan etkindir; uygulama bunu fark etmez ve "temiz" bildirebilir. Karşılama sayfası ("USB solucanı belirtileri") bu sınırı belirtmiyor.
- **Kanıt:** Okundu.
- **Düzeltme:** Gerekirse sonraki sürümde `usbguard` ya da `udev` kuralıyla (yeni HID arayüzü için onay) çözülür; şimdilik Karşılama/Former metnine "klavye gibi davranan aygıtları denetlemez" notu eklenebilir.
- **Kullanıcıya görünen davranış değişir mi:** Yalnız metin.

## 4. Şüpheliler (kodda gösterilemedi)

1. **`ufw status verbose` yerel bağımlı:** `check_firewall_policy` (`:305-326`) `Default:` ve `deny (incoming)` metinlerini arıyor ve komutu `LC_ALL=C` olmadan çalıştırıyor (derin taramalar C ile çalışıyor, bu çalışmıyor). `pkexec` `LANG`'ı koruduğundan Türkçe yerelde ufw çevrilmiş çıktı verirse sonuç `INFO` ("Varsayılan kural bulunamadı") olur, puana girmez. ufw'nin Türkçe çevirisi olup olmadığı WSL'de doğrulanamadı (ufw kurulu değil). H-01 düzelince ortaya çıkar.
2. **`ssh.socket` etkinleştirmesi:** `check_ssh_server` yalnızca `ssh` servisine bakıyor (`:896`). Soket etkinleştirmeyle çalışan sshd'de servis `inactive` olabilir ve kart "SSH kapalı" der. Debian 13 varsayılanının hangisi olduğu doğrulanmadı.
3. **`check_reboot_required`** (`:118-132`) yalnızca `/var/run/reboot-required` dosyasına bakıyor; bu dosyayı Debian'da `update-notifier-common` paketi üretir ve paket listesinde (`carotos.list.chroot`) yok. Dosya hiç oluşmuyorsa kart her zaman "gerekmiyor" der. Doğrulanmadı.
4. **`df -P /` sütun kayması** (`:952-954`): dosya sistemi adı boşluk içerirse sütunlar kayar ve yüzde yanlış okunur. Sahte girdide gösterildi (`over lay` → %10), gerçek bir canlı/kurulu sistemde böyle bir ad görülmedi.
5. **`pkexec` iptali ve derin taramalar:** `pkexec` "Request dismissed" iletisini stderr'e yazıp 126 ile çıktığından `out` boş değil; `deep_done` (`:1974`) "iptal" yolunu atlayıp `parse(…)`'a düşer ve kart önceki sonucun yerine "Çıktı yorumlanamadı (çıkış kodu 126)" (BİLGİ) olur. Tam davranış gerçek `pkexec` ile görülmedi.
6. **Zaman aşımında `pkexec`:** `subprocess.run` zaman aşımında yalnızca `pkexec` sürecine `kill` gönderir; root'a geçmiş çocuk (ör. 900 sn'lik `apt-get upgrade`) arkada çalışmayı sürdürebilir ve kullanıcı eylemi yeniden başlatırsa dpkg kilidine çarpar. Gerçek `pkexec` ile doğrulanmadı.
7. **GPT otomatik swap:** H-07 madde 3'te belirtilen, `fstab` yorumlansa da swap'ın yeniden etkinleşmesi doğrulanmadı.
8. **Carotene izin listesi USB penceresini de etkiliyor:** `Tarama.calistir` (`tarama_motoru.py:177-183`) SHA-256'sı izin listesinde olan bulguları siliyor ve USB penceresi `sonuc["izinli"]` sayısını göstermiyor. Tasarım gereği olabilir; USB'de "N dosya izin listesi nedeniyle gizlendi" notu yok.
9. **Kurulum betiği:** `9999-carotos-setup.hook.chroot` `etc/skel/.config/autostart/carotos-usb-monitor.desktop` dosyasına `chmod` uyguluyor (`|| true`), ama dosya depoda yok (gerçek otomatik başlatma `etc/xdg/autostart` altında). Zararsız ama hook sessizce başarısız oluyor; hook'ların sessiz başarısızlığı CLAUDE.md'de zaten bilinen risk.

## 5. Sağlam bulunanlar

- **Etiketler düz metin:** `tema.etiket` `Gtk.Label(label=...)` kullanıyor, `use_markup` yok; aygıttan ve sistemden gelen metinler Pango işaretlemesi olarak yorumlanmıyor (yalnızca bildirim gövdesi, U-06).
- **Root'a giden komutlar sabit:** `pkexec /bin/sh -c action["cmd"]` ve `deep_command` argümanları yalnızca sabit tablolardan geliyor; kullanıcı/aygıt metni argümana girmiyor (test de `test_komutlar_sabit` ile kilitliyor). `clamscan` komutu liste argümanı ve `--` ile kuruluyor, kabuk yok; USB'den seçilen klasör `realpath` ile kök altında doğrulanıyor.
- **Tarama güvenli:** `os.walk(followlinks=False)`, dosya içeriği hızlı taramada okunmuyor, `getsize` yalnızca `stat`; FIFO/aygıt dosyası açılmıyor.
- **İzleyici döngüsü sağlam:** `_poll`, `_settled` ve her tarama iş parçacığı geniş `except` ile korunuyor; geri çağrının `True` döndürmesi sayesinde zamanlayıcı hata sonrası ölmüyor. Tarama ayrı iş parçacığında, ana döngü donmuyor. `recent` sözlüğü sınırlı büyüyor; bildirim listesi 12 ile sınırlı.
- **Ayarlar:** `load_settings` bozuk/eksik dosyada varsayılana dönüyor, dil doğrulanıyor.
- **Sağlık denetimleri:** `run()` komut yok/zaman aşımı/OSError durumlarını ayrı kodlarla döndürüyor; tek denetimin istisnası `run_all_checks`'te yakalanıp listeyi durdurmuyor (`:1405-1410`); denetimler ayrı iş parçacığında çalışıyor, GTK donmuyor.
- **Derin tarama çözümleyicileri güvenli yönde:** `parse_debsums` ve `parse_rkhunter` yorumlanamayan çıktıyı ve zaman aşımı/öldürülmeyi (`code 124`, negatif kodlar) `INFO` yapıyor, "temiz" demiyor; rkhunter'ın kendi PID'ini ayıklaması yalnızca o PID'e bakıyor.
- **Yerel bağımsızlık:** `systemctl is-active/is-enabled`, `dpkg-query`, `passwd -S`, `df -P`, `lsblk -s` ve `apt-get -s` çıktıları çevrilmiyor; derin taramalar `LC_ALL=C` ile çalışıyor; tarih biçimi `strftime` ile sabit; ondalık virgül ayrıştırması yok.
- **Root yetkisiz çalışınca:** root gerektiren denetimler yanlış sonuç değil `NEEDROOT` dönüyor (kontrol `is_root()` ile yapılıyor).

## 6. Düzeltme planı (küçük, ayrı commit'ler; her biri test ile)

| Adım | Kapsadığı bulgular | Dokunulacak dosyalar | Kullanıcıya görünen değişiklik |
|---|---|---|---|
| 1 | H-01 | `health/carotos-health.py` (içe aktarma sırası), `tests/test_health_faz1.py` (`--audit-json` testi) | Evet: tam denetim çalışır. **İlk yapılacak.** |
| 2 | U-01 | `usb/carotos-usb-check.py` (`is_live_medium`), `tests/test_usb_faz3.py` | Hayır |
| 3 | U-04, U-06 (c), U-08 | `usb/carotos-usb-check.py` (tek `guvenli_metin` yardımcısı, `on_save`, mount ayrıştırma, bildirim kaçışı), testler | Hayır |
| 4 | U-05, U-03 | `ortak/tarama_motoru.py` (`satir_coz`, `calistir` durum kodları), `usb/carotos-usb-check.py` (`_deep_isi`), `tests/test_carotene.py` + `test_usb_faz3.py` (Carotene ile koordine edilmeli) | Evet: bozuk taramada "tamamlanamadı" |
| 5 | U-02 | `usb/carotos-usb-check.py` (kapsam sınırları, optik FS, benign adlar, temiz bildirimi) | Evet: "eksik tarandı" ve yeni bulgular; **önce sor** |
| 6 | H-03 | `health/carotos-health.py` (`bin_path`, `deep_command`, `have`) | Hayır |
| 7 | H-04, H-11, H-10, H-12, H-08 | `health/carotos-health.py` (ilgili denetimler), `tests/test_health_faz1.py`, `test_health_swap.py` | Evet (bazı kartlar durum değiştirir) |
| 8 | H-02 | `health/carotos-health.py` (`check_pending_updates`, eylem) | Evet: kapsam genişler; **önce sor** |
| 9 | H-05, H-06 | `health/carotos-health.py` (`merge_results`, `score`, `build_summary`) | Evet |
| 10 | H-07 | `health/carotos-health.py` (eylem tablosu, onay metinleri, `fix_done`), 7 dil çevirisi (CLAUDE.md/memory: yeni metin aynı oturumda çevrilir) | Evet; **önce sor** |
| 11 | U-07, U-09, H-09 | `usb/carotos-usb-check.py`, `health/carotos-health.py` | Evet (ek bulgu/bildirim); **önce sor** |
| 12 | U-10, Şüpheli 9 | Karşılama/Former metni; hook'taki ölü `chmod` | Yalnız metin |

Not: Adım 4, `tarama_motoru.py`'yi Carotene denetimiyle paylaşıyor; aynı kök neden orada da bulunursa tek düzeltme yeterli. Adım 10'daki yeni/değişen metinler 7 dile çevrilmeli. VM'de doğrulanacaklar: gerçek `pkexec` akışı (Şüpheli 5, 6), gerçek USB ile U-01/U-02 senaryoları, Türkçe yerelde `ufw` çıktısı (Şüpheli 1).
