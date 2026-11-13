# CarotOS sistem denetimi (S): derleme ve açılışta root olarak çalışanlar

Tarih: 13 Kasım 2026. Dal: `1.4` (HEAD `6345b58`). Salt okunur denetim. Depoda hiçbir dosya değiştirilmedi.

Kanıt türleri:
- **Denendi:** WSL Debian'da, root olmadan, `/tmp/denetim-sistem/` altındaki kopyalar üzerinde çalıştırılarak görüldü.
- **Okundu:** koddan ya da yapılandırmadan çıkarıldı, çalıştırılmadı.

---

## 1. Kapsam

**Satır satır okunanlar**
- `config/hooks/live/`: 9989, 9990, 9991, 9992, 9993, 9994, 9995, 9996, 9997, 9998-disk-info (binary), 9998-ikon-onbellek, 9998-ikon-servis, 9998-splash (binary), 9999. 0010 ve 0050 live-build'in kendi kancalarına giden sembolik bağlar (git kipi 120000); içerikleri live-build paketinde, okunmadı.
- `config/includes.installer/preseed.cfg`
- `config/includes.chroot/usr/local/sbin/`: `carotos-firstboot.sh`, `carotos-dil-hazirla`, `carotos-mac-ayar`, `carotos-ikon-onbellek`
- `config/includes.chroot/usr/local/bin/`: `carotos-desktop-init`, `carotos-oturum-acilis`, `carotos-saat-eslestir`, `carotos-acikla`
- `config/includes.chroot/usr/share/carotos/acikla.bash` (`/etc/bash.bashrc`'den okunur, root'un etkileşimli kabuğunda da çalışır)
- `config/includes.chroot/etc/`: dört systemd birimi (`carotos-firstboot`, `carotos-ikon-onbellek`, `carotpot`, `carotpot-engel-temizle`), `system.conf.d/zz-carotos-sessiz.conf`, `zram-generator.conf.d/90-carotos.conf`, `X11/Xsession.d/05carotos-acilis`, `xdg/autostart/*` (2), `skel/.config/autostart/*` (3), `skel/.profile`, `skel/.bashrc`, `skel/.bash_logout`, `skel/.config/Thunar/uca.xml`, `lightdm/lightdm.conf`, `lightdm/lightdm-gtk-greeter.conf`, `live/config.conf.d/carotos.conf`, `NetworkManager/conf.d/90-carotos-gizlilik.conf`, `sysctl.d/90-carotos-gizlilik.conf`, `apt/sources.list.d/debian.sources`, `default/grub.d/carotos.cfg`, `grub.d/99_carotos_sure`, `default/locale`, `fail2ban/filter.d/carotos-carotpot.conf`, `fail2ban/jail.d/carotos-carotpot.local`, `carotpot/ayarlar.json`, `os-release`, `issue`, `rkhunter.conf.local`, `nikto.conf`
- `config/package-lists/*` (4 dosya), `config/common`, `config/binary`, `config/chroot`, `config/bootstrap`, `config/source` (yorum dışı satırlar)
- `config/packages.chroot/carotos-archive-keyring_2026.11.11_all.deb` (içerik listesi ve dosyalar açılarak), `tools/apt/keyring-paketi/*`, `tools/apt/conf/*`
- `tools/iso/imzala-iso.sh`; bağlam için `tools/apt/depo-uret.sh`, `imzala-yukle.sh`, `surum-denetle.sh`, `paket-yap.sh`
- Testler (davranışı anlamak için): `tests/test_hooks.py` tamamı; diğerlerinin (`test_onyukleme`, `test_iso_onyukleme`, `test_iso_imza`, `test_apt_depo`, `test_saat_eslestir`, `test_mac_anahtari`, `test_grub_tema`, `test_plymouth_tema`, `test_masaustu_gorunum`, `test_yerel`) test adları ve ilgili iddiaları

**Hedefli taranıp ilgili bölümü okunanlar**
- `opt/carotos/ortak/sistem_dili.py` (dil-hazırla'nın root olarak yüklediği modül: içe aktarmalar, alt süreçler)
- `opt/carotos/carotpot/carotpot-yonet` (yalnızca root'ta çalışan `carotpot-engel-temizle.service`'in tükettiği dosya yolu ve ufw çağrıları)
- `opt/carotos/health/carotos-health.py` (ufw ve unattended-upgrades denetimleri), `opt/carotos/welcome/carotos-welcome.py` (pkexec çağrı yerleri), `opt/carotos/poligon/ogretmen_uygulama.py:473`
- `BUILD.md` (doğrulama grep'leri, sudo bölümü), `docs/DEPO.md` (Valid-Until kararı), `CHANGELOG.md`

**Okunmayanlar / okunamayanlar**
- `config/includes.chroot/usr/local/bin/nikto` ve `config/includes.chroot/opt/nikto/**`: git'te izleniyor ama bu çalışma kopyasında **sparse checkout (skip-worktree)** nedeniyle diskte yok. 9999 kancası `chmod 755 /usr/local/bin/nikto` çağırdığı için VM'deki klonda bulunmalı. Üçüncü taraf kod; içeriği denetlenmedi.
- `etc/skel/.config/xfce4/**` XML'leri, fastfetch, gtk.css, Plymouth betiği, panel başlatıcıları: yetki sınırına dokunmuyor.
- Uygulamaların kendisi (`/opt/carotos/*`): ayrı denetimlerin konusu.

**Yapılmayanlar:** VM'de derleme, canlı ya da kurulu açılış, `ss`, `getcap`, `systemctl` çıktıları. Bunlara bağlı her şey "Şüpheliler" bölümünde.

**Denenenler (WSL, root yok):** bütün kancalar ve kabuk betikleri `sh -n` ve `shellcheck 0.10.0 -S warning` (yalnızca iki zararsız uyarı: 9998-disk-info'da SC1090, bash betiği olan `carotos-ikon-onbellek`'te sh kipinde SC3013); ISO'daki keyring paketinin içeriği kaynakla karşılaştırıldı; `carotos-saat-eslestir --izle` xfconf yokken çalıştırıldı (S-05).

---

## 2. Tehdit modeli

**Aktörler**

| Aktör | Elinde ne var | Ne isteyebilir |
|---|---|---|
| Ağdaki yabancı | Aynı LAN/Wi-Fi (okul, kafe) | Açık porta bağlanmak, Poligon/CarotPot gibi `0.0.0.0` dinleyicilerine ulaşmak, apt trafiğini izlemek ya da araya girmek |
| Yerel yetkisiz kullanıcı | Aynı makinede ikinci hesap (sınıf bilgisayarı) | root'un okuduğu bir dosyayı ya da modülü değiştirmek, root betiğine kendi değerini sokmak, paket yakalama yetkisi |
| Kötü niyetli USB / medya | Takılı bellek ya da disk | Root'un otomatik bağladığı/ayrıştırdığı dosya sistemi (os-prober), GRUB menüsüne giriş sokmak |
| Derleme zincirine sızan içerik | Ayna, paket, derleme makinesi | İmzasız içerik, doğrulanmadan çalıştırılan indirme, sessizce başarısız olan kanca |
| Fiziksel erişim | Makinenin başında | GRUB/live menüsünden çekirdek parametresi; masaüstü dağıtımlarının ortak sınırı, bulgu sayılmadı |

**Açık yüzeyler.** (1) Kancalar: derleme makinesinde root, ağdan apt ve freshclam ile içerik çeker. (2) Açılış: `carotos-firstboot`, `carotos-ikon-onbellek`, `carotpot-engel-temizle` root birimleri; `fail2ban` root servisi. (3) Yetki yükseltme: `carotos-dil-hazirla` ve `carotos-mac-ayar` pkexec ile root. (4) Kurulu sistemin ağ duruşu: güvenlik duvarı, dinleyen uygulamalar. (5) Güncelleme zinciri: Debian aynaları (HTTP + imza), `apt.carotos.org` (HTTPS + ayrı anahtar).

**Güven sınırları.** Kullanıcı → pkexec → root betiği; `/opt/carotos` (root'a ait olduğu varsayılan) → root betiğinin yüklediği Python modülü; ağ → apt (imza ile korunur); takılı medya → `update-grub` sırasında os-prober.

**Bilinçli kararlar (bulgu sayılmadı).** Root hesabı kilitli, ilk kullanıcı sudo'da (preseed). Live oturumunda live-config'in standart davranışı (otomatik oturum, parolasız sudo). Kurucu kullanıcının wireshark grubunda olması (eğitim dağıtımı; dumpcap yetkisi grupla sınırlı). Sahte MAC'in varsayılan kapalı olması. Fiziksel erişime karşı GRUB parolası olmaması.

---

## 3. Bulgular

Yüksek önemde bulgu çıkmadı. Kapsamdaki betiklerde ağdan doğrulanmadan içerik çalıştıran ya da yerel kullanıcının root'a kendi değerini sokabildiği bir yol bulunmadı.

### Orta

#### S-01: Kurulu sistemin varsayılan ağ duruşu dağıtımın kendi Sistem Sağlığı denetiminden geçmiyor: güvenlik duvarı kapalı, otomatik güvenlik güncellemesi yok

- **Konum:** `config/package-lists/carotos.list.chroot:13` (ufw kurulur, hiçbir kanca etkinleştirmez); `config/hooks/live/9999-carotos-setup.hook.chroot:23-24` (aynı kanca fail2ban'ı açılışa bağlıyor ama ufw'ye dokunmuyor); paket listelerinde `unattended-upgrades` yok. Karşılaştırma: `opt/carotos/health/carotos-health.py:263-266` ve `:1150-1206` bu iki durumu uyarı olarak işaretliyor ve tek tıkla düzeltme sunuyor.
- **Senaryo:** Yeni kurulmuş bir CarotOS, okul ya da kafe ağında. Öğretmen Poligon'u açınca `0.0.0.0:8642` (`ogretmen_uygulama.py:473`) bütün arayüzlerde dinler; ufw kapalı olduğu için ağdaki herkes erişir (P-10 ile birleşir). Ubuntu'nun aksine Debian'da ufw kurulunca kapalı gelir (`/etc/ufw/ufw.conf` `ENABLED=no`). Güvenlik güncellemeleri kullanıcı elle `apt upgrade` yapana kadar gelmez. İlk açılışta kullanıcının çalıştırdığı Sistem Sağlığı aynı sistemi "uyarı" ile karşılar: "güvenliğe yeni başlayanlar" için tutarsız bir ilk izlenim.
- **Kanıt:** Okundu (paket listesi, kancalar, `ufw` ve `unattended-upgrades` için hiçbir etkinleştirme satırı yok; Health'in denetim tanımları).
- **Önerilen düzeltme:**
  1. Yeni bir kanca (ya da 9999'a blok): chroot'ta iptables çalıştırılamadığı için `ufw enable` değil, yapılandırma yazılır: `/etc/default/ufw` içinde `DEFAULT_INPUT_POLICY="DROP"`, `DEFAULT_OUTPUT_POLICY="ACCEPT"`, `/etc/ufw/ufw.conf` içinde `ENABLED=yes`, `systemctl enable ufw`; sonra `grep -q '^ENABLED=yes'` ile doğrula, olmazsa `exit 1`.
  2. CarotPot zaten kendi portları için `ufw allow` ekliyor (`carotpot-yonet:142`); Poligon öğretmen penceresi açılırken 8642 için aynı şekilde pkexec ile kural ekleyip kapanınca silmeli (ya da öğretmene "güvenlik duvarında 8642'yi aç" düğmesi). Bu Poligon tarafında ayrı bir iş.
  3. `unattended-upgrades` paket listesine; yalnızca `trixie-security` kaynağı (Debian varsayılanı zaten bu). Alternatif: kurulmaz ama Karşılama'da "otomatik güvenlik güncellemelerini aç" adımı.
- **Kullanıcıya görünen değişiklik:** Evet. Gelen bağlantılar varsayılan engellenir; Poligon sınıf kurulumu ek bir adım ister. Karar kullanıcının (eğitim amaçlı "öğrenci kendisi açsın" tercihi de savunulabilir; o durumda Karşılama'da açıkça söylenmeli).
- **VM'de derleme gerekir mi:** Evet.

#### S-02: Kancaların bir kısmı sessizce başarısız olabiliyor; sonuçlarını doğrulamayan adımlar var ve BUILD.md yalnızca dört iletiyi arıyor

- **Konum:**
  - `9998-carotos-ikon-servis.hook.chroot:1-5`: `set -e` yok, `systemctl enable carotos-ikon-onbellek.service || true`; başarısız olsa da "etkinlestirildi" yazar.
  - `9999-carotos-setup.hook.chroot:65-89`: Karşılama, Sistem Sağlığı ve USB Denetimi dosyalarının `chmod`'ları `|| true` ile; `:88` diskte olmayan `/etc/skel/.config/autostart/carotos-usb-monitor.desktop` dosyasına `chmod` yapıyor (her derlemede hata veriyor, yutuluyor). `:77` `locale-gen || true`: Türkçe yerel üretilmezse ISO sessizce bozuk dil ayarıyla çıkar.
  - `9989-carotos-wireshark.hook.chroot:12-13` yorumu "grup ve yetki doğrulanır" diyor, ama `:21` yalnızca grubu doğruluyor; `:22-23` `ls`/`getcap` yalnızca yazdırıyor (`getcap` yetki yokken de 0 döner). `setcap` başarısız olursa paket dumpcap'i setuid-root yapar ve derleme fark etmez.
  - `9991-carotos-carotene.hook.chroot:14`: `systemctl disable clamav-freshclam.service 2>/dev/null || true`. "Tanımlar yalnızca kullanıcı isteyince güncellenir" kararı sessizce bozulabilir (arka planda ağ trafiği).
  - `9997-carotos-liveuser.hook.chroot:10-11`: `init-config.sh` bulunamazsa yalnızca uyarı.
  - `9998-carotos-splash.hook.binary:30-38`: hiçbir hedef dizin yoksa hiçbir şey kopyalamadan "splash islemi tamam" der; BUILD.md'nin aradığı "kaynak bulundu" iletisi kopyanın yapıldığını kanıtlamaz.
  - `BUILD.md:57-64`: yalnızca firstboot, Karşılama, Sistem Sağlığı ve splash iletileri aranıyor; diğer on kancanın iletisi (wireshark, carotene, carotpot, filenor, former, gsd, önyükleme, live user, disk-info, depo) aranmıyor.
- **Senaryo:** live-build ya da Debian'da bir yol veya davranış değişir (ör. paket bir dosyayı taşır, `init-config.sh` yeri değişir, `setcap` derleme dosya sisteminde çalışmaz). Derleme "başarılı" biter, ISO yayımlanır; hata ancak kullanıcı tshark'ı, Türkçe yerel ayarı ya da bir uygulamayı açınca ortaya çıkar. CLAUDE.md'nin özellikle uyardığı durum.
- **Kanıt:** Okundu. `carotos-usb-monitor.desktop`'ın depoda olmadığı `git ls-files` ile görüldü (Denendi).
- **Önerilen düzeltme:**
  1. Her kancada `set -e`; gerekli adımlarda `|| true` kaldırılır. Gerçekten isteğe bağlı adımlar (ör. `gtk-update-icon-cache`) açıkça "isteğe bağlı" diye yorumlanır.
  2. Etkinin doğrulanması: `systemctl is-enabled carotos-ikon-onbellek.service`, `getcap /usr/bin/dumpcap | grep -q cap_net_raw` (yoksa `exit 1`), `systemctl is-enabled clamav-freshclam.service` "disabled" değilse `exit 1`, `locale -a | grep -qi '^tr_TR\.utf8$'`, uygulama dosyaları için `test -x`. Splash kancasında kopyalanan dizin sayısı en az 1 olmalı.
  3. Ölü satır (`carotos-usb-monitor.desktop`) silinir.
  4. `tests/test_hooks.py`'ye: kancalarda `|| true` yalnızca beyaz listedeki komutlarla (gtk-update-icon-cache, update-desktop-database) kullanılabilir; her kanca `set -e` içerir; her kanca "CarotOS:" ile başlayan bir başarı iletisi yazar.
  5. BUILD.md'deki dört grep yerine tek bir betik (ör. `tools/iso/derleme-denetle.sh build.log`): beklenen bütün "CarotOS:" iletilerini ve hiçbir "CarotOS HATA"/"CarotOS UYARI" olmadığını denetler.
- **Kullanıcıya görünen değişiklik:** Hayır (yalnızca derleme daha erken durur).
- **VM'de derleme gerekir mi:** Evet (kanca değişiklikleri derlemede doğrulanır).

### Düşük

#### S-03: İlk açılış birimi UID ≥ 1000 olan herkesi sudo ve wireshark grubuna ekliyor, oturum açılışıyla yarışıyor; 9999'daki derleme anı sudo döngüsü ölü kod

- **Konum:** `usr/local/sbin/carotos-firstboot.sh:21-42`; `etc/systemd/system/carotos-firstboot.service:3`, `:11-12`; `hooks/live/9999-carotos-setup.hook.chroot:26-31`.
- **Senaryo:**
  - Yetki: preseed (`passwd/root-login false`) ilk kullanıcıyı zaten sudo'ya koyuyor (BUILD.md:163-197 bunu doğruluyor ve firstboot'un yalnız başına yeterliliğinin kanıtlanmadığını yazıyor). Firstboot ise "ilk kullanıcıyı" değil, o an var olan **bütün** normal hesapları sudo'ya ekliyor. İlk açılıştan önce ikinci bir hesap varsa (görüntü klonlanan sınıf makineleri, OEM tarzı hazırlık) o hesap da sessizce yönetici olur.
  - Yarış: birim `After=multi-user.target` ile çalışıyor; LightDM buna göre sıralanmadığından kullanıcı firstboot bitmeden oturum açabilir. Grup üyeliği ancak bir sonraki oturumda geçerli olduğundan ilk oturumda tshark "Couldn't run dumpcap" verir. Live oturumunda (her açılışta firstboot yeniden çalışır, damga kalıcı değil) otomatik oturum genellikle firstboot'tan önce açılır; live kullanıcısının wireshark üyeliği o oturumda belirsiz.
  - Damga (`:41-42`) `usermod` hataları olsa da yazılır; hata günlüğe gider ama birim bir daha denemez.
  - `9999:26-31` derleme sırasında çalışır; o an UID ≥ 1000 kullanıcı yoktur (BUILD.md:155-159 da bunu söylüyor). Yorum "İlk kullanıcıyı otomatik sudo yetkili yap" diyerek yanıltıyor.
- **Kanıt:** Okundu. (Sıralama döngüsü yok: systemd, hedef zaten birimden önce sıralıysa örtük `After=` eklemiyor; BUILD.md'deki "active (exited)" çıktısı bununla uyumlu.)
- **Önerilen düzeltme:**
  1. Wireshark üyeliğini kurulum anına taşı: preseed'e `d-i passwd/user-default-groups string audio cdrom dip floppy video plugdev netdev scanner bluetooth sudo wireshark` (Debian'ın varsayılan listesi + `sudo` + `wireshark`; tam varsayılan liste VM'de `debconf-get-selections --installer` ile alınmalı). Live için `etc/live/config.conf.d/carotos.conf`'a `LIVE_USER_DEFAULT_GROUPS` (live-config'in varsayılanı + `wireshark`).
  2. Firstboot'tan sudo döngüsünü çıkar (ya da yalnızca preseed çalışmadığında, tek kullanıcı varsa ve o kullanıcı hiçbir yönetici grubunda değilse ekle). Kalırsa birime `Before=display-manager.service systemd-user-sessions.service` ve `After=local-fs.target` ver, `After=multi-user.target`'ı kaldır.
  3. Damgayı yalnızca bütün adımlar başarılıysa yaz.
  4. `9999:26-31` silinir.
- **Kullanıcıya görünen değişiklik:** Yok denecek kadar az (tshark ilk oturumda da çalışır). Sudo döngüsünün kaldırılması davranış değişikliğidir; preseed katmanının tek başına yeterliliği VM'de doğrulanmalı.
- **VM'de derleme gerekir mi:** Evet; BIOS ya da UEFI temiz kurulum ve ilk oturumda `id` denetimi.

#### S-04: `carotpot.service` başlatılamazsa sonsuz yeniden başlatma döngüsüne girer

- **Konum:** `etc/systemd/system/carotpot.service:17-18` (`Restart=on-failure`, `RestartSec=5`), `[Unit]`'te `StartLimitIntervalSec`/`StartLimitBurst` yok.
- **Senaryo:** Port 5900 ya da 8080 başka bir uygulamada (ör. kullanıcı VNC ya da bir web sunucusu açtı), ayar dosyası bozuk ya da bağımlılık eksik. CarotPot her başlatmada hata koduyla çıkar. systemd'nin varsayılan sınırı "10 sn içinde 5 başlatma"; 5 sn aralıkla bu sınıra hiç ulaşılmaz, birim kullanıcı durdurana kadar her 5 saniyede Python'u yeniden başlatır ve günlüğü doldurur. Kullanıcı arayüzde "çalışıyor/başlıyor" arasında gidip gelen bir durum görür.
- **Kanıt:** Okundu (systemd'nin varsayılan `DefaultStartLimitIntervalSec=10s`, `DefaultStartLimitBurst=5` değerleri ile).
- **Önerilen düzeltme:** `[Unit]` bölümüne `StartLimitIntervalSec=120` ve `StartLimitBurst=3`; yapılandırma hatası için ayrı bir çıkış kodu tanımlanıp `RestartPreventExitStatus=` ile yeniden başlatma kapatılır. CarotPot arayüzü `failed` durumunu "başlatılamadı: günlüğe bakın" diye gösterir (uygulama tarafı).
- **Kullanıcıya görünen değişiklik:** Yalnızca hata durumunda (sonsuz döngü yerine "başlatılamadı").
- **VM'de derleme gerekir mi:** Hayır; VM'de birim dosyası elle kopyalanıp port dolu bırakılarak denenebilir. ISO'ya girmesi için derleme gerekir.

#### S-05: `carotos-saat-eslestir --izle` oturum kapandıktan sonra da sonsuza kadar çalışır

- **Konum:** `usr/local/bin/carotos-saat-eslestir:84-92` (çıkış koşulu olmayan `while :` döngüsü); autostart `etc/skel/.config/autostart/carotos-saat-eslestir.desktop:7`.
- **Senaryo:** Xfce oturumu kapanır; autostart ile başlatılan süreçler xfce4-session tarafından öldürülmez ve Debian'da logind `KillUserProcesses=no` varsayılandır. Döngü yetim kalır, her 15 sn'de `readlink` ve `stat` çalıştırır. Her oturum aç/kapat yeni bir yetim ekler (paylaşılan sınıf makinesinde gün içinde onlarca). Saat dilimi değişirse yetimlerin `xfconf-query` çağrıları D-Bus etkinleştirmesiyle oturumu olmayan bir xfconfd başlatabilir. Kaynak tüketimi küçük, ama sınırsız.
- **Kanıt:** Denendi: `xfconf-query` her çağrıda hata veren bir taslakla değiştirildi (`CAROTOS_SAAT_ARALIK=1`); betik 20 sn sonunda kendiliğinden çıkmadı, `timeout` ile sonlandırıldı (çıkış 124). Oturum sonunda süreçlerin yaşamaya devam etmesi: Okundu (Debian varsayılanı; VM'de doğrulanacak).
- **Önerilen düzeltme:** Döngü başında oturumun canlı olduğunu denetle ve değilse çık. Örneğin başlangıçta `OTURUM=$(pgrep -u "$(id -u)" -x xfce4-session | head -n1)` al, döngüde `kill -0 "$OTURUM" 2>/dev/null || exit 0`. Alternatif: `xfconf-query -c xfce4-panel -l` art arda 3 kez başarısız olursa çık. Test: `test_saat_eslestir.py`'ye "oturum süreci yoksa döngü çıkar" senaryosu.
- **Kullanıcıya görünen değişiklik:** Hayır.
- **VM'de derleme gerekir mi:** Hayır (betik tek başına WSL'de test edilebilir); ISO'ya girmesi için derleme gerekir.

#### S-06: `os-prober` açık ve her `update-grub`'da iki kez çalışıyor; takılı medyayı root olarak bağlıyor

- **Konum:** `etc/default/grub.d/carotos.cfg:27` (`GRUB_DISABLE_OS_PROBER=false`); `etc/grub.d/99_carotos_sure:14-16` (`timeout 90 os-prober`, `30_os-prober`'dan ayrı ikinci çalıştırma).
- **Senaryo:** Her çekirdek güncellemesinde `update-grub` önce `30_os-prober`, sonra `99_carotos_sure` içinde os-prober'ı yeniden çalıştırır. os-prober bütün blok aygıtları, takılı USB bellekler dahil, root olarak salt okunur bağlayıp tarar. Güncelleme sırasında takılı, bilerek bozulmuş bir dosya sistemi çekirdeğin dosya sistemi sürücüsüne root bağlamında verilmiş olur; o bellekteki bir "işletim sistemi" GRUB menüsüne giriş olarak eklenir. GRUB, os-prober'ı 2.06'dan beri bu tür gerekçelerle varsayılan olarak kapatıyor. İkinci çalıştırma güncellemeyi ayrıca uzatır (en fazla 90 sn).
- **Kanıt:** Okundu. os-prober'ın açık olması bilinçli bir karar (`test_iso_onyukleme.py:69`), bu yüzden önem Düşük.
- **Önerilen düzeltme:** İki seçenek. (a) os-prober açık kalır: `99_carotos_sure` os-prober'ı yeniden çalıştırmaz. `grub-mkconfig` betikleri sırayla çalıştırıp çıktıları birleştirdiği için 99, 30'un çıktısını göremez; bu yüzden sayım `30_os-prober`'dan önce çalışan bir `29_carotos_sure` içinde yapılır ve 30 kendi taramasını yine yapar (çift tarama sürer), ya da 99 bütünüyle kaldırılıp süre sabit 10 sn yapılır. Ek olarak Karşılama/Former'da "güncelleme sırasında tanımadığınız USB bellek takılı olmasın" notu. (b) os-prober yalnızca kurulumda bir kez çalışır (kurucu öbür sistemi menüye koyar), sonra `GRUB_DISABLE_OS_PROBER=true` olur; menü süresi kurulumda belirlenip sabitlenir.
- **Kullanıcıya görünen değişiklik:** Seçeneğe bağlı (çift önyüklemede menü davranışı).
- **VM'de derleme gerekir mi:** Hayır, kurulu VM'de `/etc/grub.d` değiştirilerek denenebilir; ISO için derleme gerekir.

#### S-07: `carotos-dil-hazirla` root olarak yüklediği modülün yalnızca `.py` dosyasını denetliyor; dizini ve bayt kodu önbelleğini denetlemiyor

- **Konum:** `usr/local/sbin/carotos-dil-hazirla:30-38`.
- **Senaryo:** Betik, belge dizesinde (`:13-15`) "modül root'a ait değilse ya da başkalarınca yazılabiliyorsa hiçbir şey yapmadan çıkar" diyor. Denetim yalnızca `/opt/carotos/ortak/sistem_dili.py` dosyasının sahibine ve kipine bakıyor. `import`, geçerli bir `__pycache__/sistem_dili.cpython-313.pyc` bulursa kaynak yerine onu çalıştırır; `/opt/carotos/ortak` ya da `__pycache__` dizini root dışında biri tarafından yazılabiliyorsa (derleme klonunun umask'ı, ileride `.deb` paketlemede bir hata, elle `cp`), `.py`'ye dokunmadan root kodu çalıştırılabilir. Bugün bu dizinlerin root'a ait ve 755 olması bekleniyor; bulgu bir sertleştirme açığıdır, doğrudan sömürü yolu değil.
- **Kanıt:** Okundu.
- **Önerilen düzeltme:** `/opt`, `/opt/carotos`, `/opt/carotos/ortak` ve (varsa) `__pycache__` için de sahip root ve `mode & 0o022 == 0` denetimi. Daha sağlamı: modülü `import` yerine kaynaktan yükle (dosyayı `O_NOFOLLOW` ile aç, `fstat` ile denetle, `compile()` + `exec()` ile yeni bir modül nesnesine yükle). Böylece denetlenen dosya ile çalıştırılan kod aynı olur. Test: `__pycache__` içine farklı bayt kodu konunca betiğin çıktığı senaryo.
- **Kullanıcıya görünen değişiklik:** Hayır.
- **VM'de derleme gerekir mi:** Hayır (WSL'de `kok` önekiyle test edilebilir); ISO için derleme gerekir.

---

## 4. Şüpheliler (VM'de doğrulanmalı)

Koddan kesin çıkarılamayan, Debian ya da live-build varsayılanlarına bağlı noktalar. Her biri için VM komutu verilmiştir; komutlar canlı ya da kurulu CarotOS içinde, normal kullanıcıyla çalıştırılır (sudo gerekenler belirtildi).

1. **dumpcap yetkileri kurulu sistemde kayboluyor olabilir.** 9989 yetkiyi dosya özniteliği (xattr) olarak verir. squashfs öznitelikleri varsayılan olarak korur, ama kurucunun canlı dosya sistemini hedef diske kopyalama biçimi öznitelikleri korumayabilir. Kayıpsa wireshark grubundaki kullanıcı yine yakalama yapamaz. Hem canlıda hem kuruluda: `getcap /usr/bin/dumpcap; ls -l /usr/bin/dumpcap`. Beklenen: `cap_net_admin,cap_net_raw=eip`, `root wireshark`, `-rwxr-x---`.
2. **`includes.chroot` dosyalarının sahibi ve izinleri derleme klonuna bağlı.** Kancalar bazı dosyaların iznini düzeltiyor, hepsini değil (ör. `/usr/local/sbin/carotos-ikon-onbellek`, `/etc/X11/Xsession.d/05carotos-acilis`, `/etc/systemd/system/carotos-ikon-onbellek.service`). VM'deki klon umask 002 ile alındıysa grup-yazılabilir dosyalar ISO'ya girer; bu S-07'nin önkoşuludur. Canlıda: `find /etc/systemd/system /etc/X11/Xsession.d /etc/grub.d /etc/default/grub.d /usr/local /opt/carotos -xdev ! -type l \( -perm /022 -o ! -user root \) -ls | head -20`. Beklenen: boş.
3. **Varsayılan olarak dinleyen servisler.** `LB_APT_RECOMMENDS="true"` olduğundan önerilen paketlerle avahi-daemon, cups ya da benzeri bir dinleyici gelmiş olabilir. Canlıda: `sudo ss -tulpn` ve `systemctl list-unit-files --state=enabled --type=service`. Beklenen: dışa açık dinleyici yok; etkin servisler bilinen listede.
4. **fail2ban'ın korumak için bir şeyi var mı?** `9999:24` fail2ban'ı açılışa bağlıyor; listede SSH sunucusu yok, CarotPot hapsi kapalı. Debian'ın `defaults-debian.conf`'u sshd hapsini açar; trixie'de bunun systemd günlüğüyle sorunsuz başlayıp başlamadığı ve gereksiz yere root bir servisin sürekli çalışıp çalışmadığı doğrulanmalı: `systemctl status fail2ban --no-pager; sudo fail2ban-client status`. Hapis yoksa ya da yalnızca sshd varsa öneri: fail2ban'ı varsayılan kapalı getir, CarotPot otomatik engellemeyi açınca etkinleştirsin.
5. **SSH sunucusu yok mu?** Live oturumu live-config gereği bilinen parolalı (`live`) ve parolasız sudo'lu bir kullanıcıyla açılır. Bu ancak ağdan giriş yolu yoksa kabul edilebilir: `dpkg -l openssh-server 2>/dev/null | grep '^ii' || echo yok`. Beklenen: `yok`.
6. **Yinelenen apt kaynakları.** live-build ve kurucu `/etc/apt/sources.list` yazar, ISO ayrıca `sources.list.d/debian.sources` taşır; `LB_APT_SOURCE_ARCHIVES="true"` `deb-src` satırları da ekler. Uyarılar ve fazladan indirme olabilir: `cat /etc/apt/sources.list; sudo apt-get update 2>&1 | grep -iE "multiple times|birden (çok|fazla)"`.
7. **`apt.carotos.org` ve Valid-Until.** ISO depo tanımını varsayılan olarak taşıyor (`9999:93-97`), depo 60 gün geçerli imzalanıyor (`tools/apt/conf/distributions:8`, karar `docs/DEPO.md:15`). Depo yayında değilse ya da imza 60 gün içinde yenilenmezse bütün kurulu sistemlerde `apt update` hata koduyla biter (Mağaza ve `carotos-dil-hazirla` bundan etkilenir). Doğrulama: `curl -sI https://apt.carotos.org/dists/stable/InRelease | head -1` ve `curl -s https://apt.carotos.org/dists/stable/InRelease | grep Valid-Until`. Öneri: yeniden imzalama için takvim hatırlatıcısı ya da Valid-Until'e 14 gün kala uyaran bir betik.
8. **clamav-freshclam gerçekten kapalı mı?** (S-02 ile ilgili) `systemctl is-enabled clamav-freshclam.service`. Beklenen: `disabled`.
9. **`init-config.sh` yolu.** 9997 trixie live-config'te dosyayı bulamazsa yalnızca uyarı verir: `grep -a "Live User adi guncellendi\|init-config.sh bulunamadi" build.log`.
10. **Firstboot ile oturumun yarışı (S-03).** Kurulu sistemin ilk açılışında, ilk oturumda: `id | tr ',' '\n' | grep -c wireshark` ve `systemd-analyze critical-chain carotos-firstboot.service`.
11. **Arşiv anahtarının ana anahtarında son kullanma tarihi yok.** ISO'daki anahtar (`30E6 D4B0 C05E F002 1309 A1A0 9F93 5CD4 D5D0 A1F5`, ed25519) için `gpg --show-keys` son kullanma alanı boş döndü (Denendi). Anahtar çevrimdışı ve şifreli USB'de tutulduğu için önemi düşük; bir anahtar dönüşüm (rotation) planı ve iptal sertifikası yazılı olmalı.

---

## 5. Sağlam bulunanlar

- **Ağdan çalıştırılan doğrulanmamış içerik yok.** Hiçbir kancada `curl | sh`, `wget` ya da imzasız indirme yok. Derleme içi kurulumlar apt üzerinden (`LB_APT_SECURE="true"`, `debian-archive-keyring`); freshclam imzalı CVD indirir. Debian kaynakları HTTP ama `Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg` ile.
- **CarotOS deposu doğru kurulmuş.** `carotos.sources` HTTPS ve yalnızca kendi anahtarına bağlı (`Signed-By`); anahtar `trusted.gpg.d`'ye konmuyor (test var). ISO'daki keyring paketinin anahtarı kaynaktakiyle bayt bayt aynı (Denendi: her ikisi `168bb128…4495`); dosyalar root:root 644. 9999 paketin kurulduğunu ve iki dosyanın boş olmadığını doğruluyor.
- **Secure Boot zinciri:** `shim-signed` ve `grub-efi-amd64-signed` paket listesinde yok (test var), `LB_UEFI_SECURE_BOOT="enable"`.
- **Yetkili betikler:** `carotos-dil-hazirla` ve `carotos-mac-ayar` `python3 -I`, sabit `PATH`/`LC_ALL` ortamı, beyaz listeli tek argüman, kabuk yok, `euid` denetimi. mac-ayar sabit içerikli dosyayı `O_NOFOLLOW` ile geçici dosyaya yazıp atomik değiştiriyor (test var). dil-hazırla'nın apt'ye verdiği paket adları yalnızca sabit tablodan geliyor; `/etc/locale.gen` atomik yazılıyor.
- **Yetkilendirme:** Depoda `sudoers.d` ya da polkit kuralı yok; iki betik pkexec'in varsayılan `org.freedesktop.policykit.exec` eylemiyle (yönetici parolası) yetkilendiriliyor. Parolasız yükseltme yolu bulunmadı.
- **Kancalar 9989-9997, 9999 ve iki binary kancası `set -e` ile çalışıyor**; 9996 (GRUB süresi, Plymouth), 9997 (hostname), 9998-disk-info, 9999 (os-release divert, bash.bashrc bağlantısı, keyring) kendi sonucunu doğrulayıp başarısızlıkta derlemeyi durduruyor. `shellcheck -S warning` gerçek bir sorun bulmadı (Denendi).
- **preseed:** root hesabı kilitli, bilgisayar adı soruluyor ama zorlanmıyor; kurucu parametreleri GRUB ile aynı (test var).
- **CarotPot birimi:** ayrı yetkisiz kullanıcı, `CapabilityBoundingSet=` boş, `ProtectSystem=strict`, sistem çağrısı filtresi, bellek ve görev sınırı, varsayılan olarak etkin değil. `carotpot-engel-temizle` `python3 -I`, `ConditionPathExists`, kısmi sandbox, hata durumunu artık gizlemiyor.
- **Ağ gizliliği varsayılanları:** DHCP'de makine adı gönderilmiyor, IPv6 geçici adresler (NetworkManager ve sysctl), Wi-Fi taramasında rastgele MAC.
- **Oturum betikleri:** `carotos-desktop-init` ve `carotos-oturum-acilis` sınırlı bekleme süreleriyle çalışıyor (15+20+3 sn; perde `signal.alarm` ve `timeout -k 2 32` ile iki kez sınırlı), kullanıcı bağlamında ve root'a hiçbir değer taşımıyor. `acikla.bash` satırı tek argüman olarak tırnaklı geçiriyor, komutu çalıştırmıyor.
- **firstboot:** kullanıcı adları yalnızca `/etc/passwd`'den, `usermod` hataları günlüğe yazılıyor (test var); `/var/lib/carotos` root'a ait oluşturuluyor.
- **`tools/iso/imzala-iso.sh`:** `set -euo pipefail`, `mktemp`, imzayı yalnızca genel anahtarla `gpgv` ile doğruluyor (testler var).

---

## 6. Düzeltme planı

Her adım ayrı commit ve testiyle. Sıra önem ve bağımlılığa göre. VM komutları derleme sonrası, `~/carotos-iso` içinde ya da canlı/kurulu sistemde çalıştırılır.

| Adım | Kapsar | Dokunulan dosyalar | Ne yapılır | Kullanıcıya görünen | VM doğrulaması |
|---|---|---|---|---|---|
| 1 | S-02 | `config/hooks/live/9989`, `9991`, `9997`, `9998-ikon-servis`, `9998-splash`, `9999`; `tests/test_hooks.py`; yeni `tools/iso/derleme-denetle.sh`; `BUILD.md` | `set -e` her yerde; gerekli adımlarda `|| true` kaldırılır; etki doğrulamaları (`is-enabled`, `getcap`, `locale -a`, `test -x`, splash sayacı); ölü `carotos-usb-monitor.desktop` satırı silinir; test, `|| true`'yu beyaz liste dışında yasaklar; derleme günlüğü betiği bütün "CarotOS:" iletilerini arar. | Yok | `bash tools/iso/derleme-denetle.sh build.log` (çıktı: hepsi tamam); `grep -a "CarotOS HATA\|CarotOS UYARI" build.log` boş |
| 2 | S-03 | `config/includes.installer/preseed.cfg`, `config/includes.chroot/etc/live/config.conf.d/carotos.conf`, `usr/local/sbin/carotos-firstboot.sh`, `etc/systemd/system/carotos-firstboot.service`, `hooks/live/9999` (26-31 silinir), `tests/test_hooks.py`, `tests/test_onyukleme.py` | wireshark üyeliği kurulumda (`passwd/user-default-groups`) ve live'da (`LIVE_USER_DEFAULT_GROUPS`); firstboot sudo döngüsü kaldırılır ya da tek kullanıcı koşuluna bağlanır; birim oturumdan önce sıralanır; damga yalnızca başarıda. | Neredeyse yok (tshark ilk oturumda da çalışır) | Temiz kurulum, ilk oturumda `id` (sudo ve wireshark görünmeli), `sudo -n true 2>&1`, `systemctl status carotos-firstboot --no-pager`; canlıda `id` |
| 3 | S-01 | yeni kanca `config/hooks/live/9988-carotos-guvenlik-duvari.hook.chroot` (ya da 9999'a blok), `config/package-lists/carotos.list.chroot`, Poligon öğretmen uygulaması (ayrı commit), Karşılama metni (7 dil), testler | **Önce karar:** ufw varsayılan açık mı, unattended-upgrades kurulu mu? Açılacaksa `/etc/default/ufw` gelen DROP, `ufw.conf` `ENABLED=yes`, `systemctl enable ufw`, doğrulama; Poligon 8642 için pkexec ile geçici kural. | Evet (gelen bağlantı engeli, Poligon'da ek adım, arka planda güvenlik güncellemesi) | `sudo ufw status verbose` (Durum: etkin, gelen: deny); Sistem Sağlığı'nda ufw ve unattended satırları yeşil; iki VM arasında Poligon katılımı |
| 4 | S-04 | `config/includes.chroot/etc/systemd/system/carotpot.service`, CarotPot arayüzünün durum gösterimi | `StartLimitIntervalSec=120`, `StartLimitBurst=3`; yapılandırma hatasına ayrı çıkış kodu ve `RestartPreventExitStatus`. | Yalnızca hata durumunda | `nc -l 8080 &` ile portu doldur, `sudo systemctl start carotpot`, 1 dk sonra `systemctl status carotpot --no-pager` "failed" ve `journalctl -u carotpot | grep -c Started` en fazla 3 |
| 5 | S-05 | `config/includes.chroot/usr/local/bin/carotos-saat-eslestir`, `tests/test_saat_eslestir.py` | Döngüde oturum süreci yaşıyor mu denetimi; yoksa çık. | Yok | Oturum aç/kapat, sonra başka TTY'den `pgrep -af carotos-saat-eslestir` (yalnızca etkin oturumunki görünmeli) |
| 6 | S-07 | `config/includes.chroot/usr/local/sbin/carotos-dil-hazirla`, yeni test (`tests/test_dil_hazirla.py` ya da mevcut dil testine ek) | Dizin zinciri ve `__pycache__` denetimi; modülün kaynaktan doğrulanmış tanıtıcıyla yüklenmesi. | Yok | Canlıda Karşılama'dan Almanca hazırlığı (`pkexec /usr/local/sbin/carotos-dil-hazirla de` çıktısı "3/3 tamam") |
| 7 | S-06 | `config/includes.chroot/etc/grub.d/99_carotos_sure`, `etc/default/grub.d/carotos.cfg`, `tests/test_grub_tema.py`, `tests/test_iso_onyukleme.py` | **Önce karar:** os-prober açık kalsın mı? Kalırsa çift çalıştırma kaldırılır ve Karşılama/Former'da not; kapanırsa kurulumda bir kez. | Seçeneğe bağlı | Çift önyüklemeli VM'de `time sudo update-grub` ve `grep -c "os-prober\|menuentry" /boot/grub/grub.cfg` |
| Doğrulama | Şüpheliler 1-11 | | Bölüm 4'teki komutlar ilk VM derlemesinde bir kez çalıştırılır; çıkan her sapma yeni bir S-numarasıyla bu deftere eklenir. | | Bölüm 4 |

**Önerilen sıra:** 1 (derlemenin kendisini güvenilir kılar, sonraki adımların doğrulanmasını sağlar) → 2 → 4, 5, 6 (küçük, kullanıcıya görünmez) → 3 ve 7 kullanıcı kararından sonra. 1, 2 ve 3 aynı VM derlemesinde birlikte doğrulanabilir.
