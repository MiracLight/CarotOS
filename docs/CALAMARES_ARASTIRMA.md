# CarotOS'a Calamares ekleme araştırması (16 Kasım 2026)

Amaç: canlı masaüstünden "CarotOS'u Kur" simgesiyle Calamares kurulumu; önyükleme
menüsünde debian-installer (d-i) yedek olarak kalır. Bu belge yalnızca araştırmadır,
depoda kod değişikliği yapılmadı.

İşaretler: **[D]** = kaynaktan doğrulandı (URL verildi), **[V]** = varsayım /
bilgi, VM'de doğrulanmalı.

Kaynak notu: `salsa.debian.org/live-team/calamares-settings-debian` **master** dalı
artık Debian 14 (forky) içeriğidir (branding 14, `partition.conf` var). Trixie
içeriği için `sources.debian.org/.../calamares-settings-debian/13.0.13-1/`
kullanıldı. Aşağıda "trixie" denen her şey 13.0.13-1 içindir.

## 1. Debian trixie canlı imajı ne gönderiyor

- Debian'ın Xfce canlı imajı da bizimle **aynı kipte** üretiliyor: `lb config noauto
  --mode debian --debian-installer live --linux-packages "linux-image linux-headers"`
  [D] (live-images `images/xfce-desktop/auto/config`, salsa `live-team/live-images`,
  dal `debian`). Yani d-i menü girişi + Calamares birlikte çalışır; 13 duyurusu da
  "canlı imaj hem Calamares hem d-i içerir" der [D]
  (https://www.debian.org/News/2025/20250809).
- Calamares paketleri Xfce imajına `live-task-xfce` üzerinden gelir:
  `Recommends: calamares-settings-debian` (+ `live-task-localisation`, `plymouth`)
  [D] (https://packages.debian.org/trixie/live-task-xfce). `installer.list.chroot`
  yalnızca `debian-installer-launcher` içerir [D].
- `calamares` trixie: **3.3.14-1**, Qt6 + KF6 (`libkpmcore12`, `libkf6*`,
  `libqt6*`, `libpwquality1`, `os-prober`); Recommends `btrfs-progs`,
  `squashfs-tools` [D] (https://packages.debian.org/trixie/calamares).
- `calamares-settings-debian` trixie: **13.0.13-1**, `Depends: calamares, cryptsetup,
  keyutils, libglib2.0-bin, pkexec, qml-module-qtquick2,
  qml-module-qtquick-window2, rsync, dconf-gsettings-backend`; Recommends yok [D]
  (https://packages.debian.org/trixie/calamares-settings-debian).
- Dosya listesi (37 dosya) [D]
  (https://packages.debian.org/trixie/all/calamares-settings-debian/filelist):
  - `/etc/calamares/settings.conf`
  - modül ayarları: `bootloader, displaymanager, finished, fstab,
    luksopenswaphookcfg, machineid, mount, packages, unpackfs, users, welcome`
    (**`partition.conf`, `locale.conf`, `keyboard.conf` YOK**; yani Calamares
    varsayılanları geçerli. `partition.conf` sadece forky'de var)
  - `/etc/calamares/branding/debian/` (`branding.desc`, `show.qml`, `slide1.png`,
    `welcome.png`, `debian-logo.png`)
  - `/etc/xdg/autostart/calamares-desktop-icon.desktop`,
    `/usr/bin/add-calamares-desktop-icon`, `/usr/bin/calamares-install-debian`,
    `/usr/share/applications/calamares-install-debian.desktop`,
    `/usr/share/pixmaps/install-debian.png`, gschema override (içeriği
    okunamadı [V])
  - özel işler `/usr/lib/calamares/modules/*/module.desc`: `bootloader-config,
    dpkg-unsafe-io, dpkg-unsafe-io-undo, sources-final, sources-media,
    sources-media-unmount`; betikler `/usr/share/calamares/helpers/`.
- trixie `settings.conf` dizisi [D] (sources.debian.org 13.0.13-1):
  - show: `welcome, locale, keyboard, partition, users, summary`
  - exec: `partition, mount, unpackfs, luksbootkeyfile, dpkg-unsafe-io,
    sources-media, machineid, fstab, locale, keyboard, localecfg, users,
    displaymanager, networkcfg, hwclock, services-systemd, bootloader-config,
    grubcfg, bootloader, packages, plymouthcfg, initramfscfg, initramfs,
    dpkg-unsafe-io-undo, sources-media-unmount, sources-final, umount`
  - show (son): `finished`; `branding: debian`; `instances` yok.
- Modül içerikleri [D] (13.0.13-1 ve master aynı):
  - `unpackfs`: kaynak `/run/live/medium/live/filesystem.squashfs`, `sourcefs:
    squashfs`, hedef `""`.
  - `users`: `userGroup users`, `defaultGroups` = cdrom floppy sudo audio dip
    video plugdev netdev lpadmin scanner bluetooth; `autologinGroup autologin`;
    `sudoersGroup sudo`; `setRootPassword false`; parola kuralı: boş olmasın.
    **hostname bloğu yok.**
  - `packages`: backend apt, `remove`: live-boot, live-boot-doc, live-config,
    live-config-doc, live-config-systemd, live-tools, live-task-localisation,
    live-task-recommended, calamares-settings-debian.
  - `bootloader.conf`: `efiBootLoader grub`, `installEFIFallback true`,
    **`efiBootloaderId` ayarlı değil** (varsayılan = branding
    `bootloaderEntryName`, branding'de "Debian").
  - `displaymanager.conf`: `basicSetup false`; `mount.conf`: proc/sys/dev/run/
    udev/efivarfs (yalnız EFI)/devpts bağları; `finished`: yeniden başlat
    seçili, `systemctl -i reboot`; `welcome` gereksinimleri (master): 15 GB
    disk, 1 GB RAM, root zorunlu, güç denetlenir ama zorunlu değil.
- Başlatıcı `calamares-install-debian` [D]: `sudo mv /etc/fstab
  /etc/fstab.orig.calamares` (live-build'in bıraktığı fstab bölümlemeyi
  bozuyor), `QT_AUTO_SCREEN_SCALE_FACTOR=1`, `xhost +si:localuser:root`,
  `pkexec calamares`, sonra xhost geri alınır ve fstab geri konur.
  `add-calamares-desktop-icon` [D]: `xdg-user-dir DESKTOP` altına `.desktop`
  kopyalar, Xfce için `gio` ile güvenilir işaretler, Calamares ikililerini
  `ionice … cat` ile önbelleğe alır. Yardımcı betikte `for file in $(ldd …):`
  satırında şüpheli iki nokta üst üste var (kaynak özeti); kendi betiğimizi
  yazarken kopyalamayalım [V].

## 2. EFI + Secure Boot ve BIOS: Debian'ın yöntemi

- `bootloader-config` (module.desc: process, zaman aşımı 600 sn) [D]
  (13.0.13-1 `helpers/calamares-bootloader-config`):
  - EFI/BIOS ayrımı: **canlı sistemde** `[ -d /sys/firmware/efi/efivars ]`.
  - UEFI: `DEBIAN_FRONTEND=noninteractive chroot $CHROOT apt-get -y install
    grub-efi`; BIOS: `... apt-get -y install grub-pc`.
  - `shim-signed` / `grub-efi-amd64-signed` adı betikte **geçmez**; bunlar
    `grub-efi-amd64`'in bağımlılık/öneri zincirinden gelir [V] (apt Recommends
    açık varsayımı; `Recommends` kapalı olursa imzalı paket gelmez, bkz. risk 3).
  - `/etc/default/grub` içinde `GRUB_DISABLE_OS_PROBER=false` açılır,
    `update-grub` çalışır. LUKS ise `cryptsetup-initramfs cryptsetup keyutils`
    kurulur ve `UMASK=0077` yazılır.
- Paketler **ağdan ya da ISO'dan** gelir. ISO yolu: `sources-media`
  (`calamares-sources-media`) [D]:
  - `/run/live/medium` (ya da dracut için `/run/initramfs/live`) hedefe bind
    mount edilir,
  - `base.list` silinir, `debian-live-media.list` =
    `deb [trusted=yes] file:/run/live/medium trixie main`,
  - hedefte `apt-get update`; sonra `sources-media-unmount` bağı ve listeyi
    kaldırır.
  - Betikte `set -e` yok; medium bulunamazsa sessizce yanlış yere yazabilir.
  - `sources-final` ise hedefte `/etc/apt/sources.list` dosyasını **deb.debian.org,
    -updates, security, -backports** ile üzerine yazar [D].
- ISO'da havuz (pool) kim koyuyor? **live-build.** `--debian-installer live`
  için `installer_debian-installer` betiği `binary/pool` ve
  `dists/<dağıtım>/<alan>/binary-<mimari>/Packages` üretir; amd64 için havuza
  `grub-pc grub-common grub-efi-amd64 efibootmgr shim-signed mokutil
  shim-unsigned cryptsetup keyutils`, varsa `grub-efi-amd64-signed` ve
  `grub-efi-amd64-unsigned`, çekirdek, firmware ve libefi/libfuse bağımlılıklarını
  koyar; `live` kipinde havuz yine oluşur (netboot hariç) [D]
  (salsa `live-team/live-build`, `scripts/build/installer_debian-installer`,
  dal master; **master**, trixie sürümü değil).
  - live-build changelog [D] (https://launchpad.net/debian/+source/live-build/+changelog):
    `1:20230131` "add grub packages for d-i and Calamares", `1:20240810`
    "installer: offline installation with calamares", `1:20250225` "Calamares also
    needs the unsigned GRUB packages for offline installation" ve "Cached apt
    indices for local pool". CarotOS yapılandırması `LB_CONFIGURATION_VERSION=
    "20250505+deb13u1"` (config/common) olduğundan bu üç özellik **bizde var**
    [D, sürüm karşılaştırması].
  - live-build MR 352: calamares-settings-debian `grub-pc`/`grub-efi-amd64` yerine
    `grub-efi` kurmaya başlayınca havuzda `grub-efi` de gerekti [D]
    (https://salsa.debian.org/live-team/live-build/-/merge_requests/352). Trixie
    live-build'inde (20250505+deb13u1) `grub-efi` paketinin havuzda olup olmadığı
    **doğrulanamadı** [V]; derlemeden sonra ISO'da `find pool -name 'grub-efi_*'`
    ile bakılmalı. Yoksa Debian de aynı sorunu yaşardı; muhtemelen vardır.
  - Ek lb seçeneği gerekmez; mevcut `--debian-installer live` yeterli [D/V].
- **BIOS + shim çakışması (BUILD.md'deki d-i hatası) Calamares'te yaşanmaz** [V,
  mantıksal]: hedef sistemde (squashfs) `shim-signed`/`grub-efi*` zaten yok (kural
  korunur: bu paketler `carotos.list.chroot`'a EKLENMEZ). BIOS'ta yalnız `grub-pc`
  kurulur; UEFI'de `grub-efi` imzalı zincirle gelir. d-i'nin yaptığı "EFI
  paketlerini kaldır" adımı Calamares'te yoktur.
- **Kritik: `efiBootloaderId: "debian"` ZORUNLU.** Debian'ın `grubx64.efi` dosyasında
  "debian" sabit gömülü; başka bir dizine kurulursa GRUB istemine düşer [D]
  (https://calamares.codeberg.page/docs/deploy-issues ve bootloader.conf açıklaması).
  Varsayılan branding `bootloaderEntryName` olduğundan, branding'imizde
  "CarotOS" yazarsak Secure Boot kurulumları **bozulur**. Çözüm: bootloader.conf'ta
  `efiBootloaderId: "debian"` (d-i de zaten `EFI/debian` kullanıyor, davranış
  aynı kalır). NVRAM menüsünde "debian" görünür; CLAUDE.md kural 5 ile çelişir ama
  imzalı GRUB için kaçınılmaz [D].
- **Yedek yükleyici:** `installEFIFallback: true` iken Calamares `EFI/BOOT/BOOTX64.EFI`
  olarak GRUB'u kopyalar; Secure Boot'ta bu dosya reddedilebilir (shim değil
  GRUB). Birçok türev `false` yapıyor; Debian için doğru zincir shimx64.efi'yi
  `BOOTX64.EFI` olarak (fbx64/mmx64 ile) kopyalamak [D, forum/PR özeti:
  https://forums.kicksecure.com/t/secure-boot-invalid-signature/771,
  https://github.com/patina-os/patina/pull/55]. Kesin sonuç kaynaklarda yok [V]:
  VM'de iki değer de denenmeli (aşağıda test planı).

## 3. Canlıya özgü şeyler kurulu sistemden nasıl çıkar

- **live-boot / live-config:** `packages` modülünün `remove` işlemi (yukarıda) [D]. Üç
  sonuç doğurur: initramfs yeniden üretilir (`initramfs` modülü `-k all`) [D];
  canlı kullanıcı squashfs'te **yoktur** (live-config çalışma anında, bellekte
  oluşturur) [V, live-boot tasarımı]; `/etc/live/config.conf.d/carotos.conf`
  (bizim dosya) paket sahipli olmadığı için kalır [V], shellprocess ile silinmeli.
- **Kritik tuzak: apt `remove` bilinmeyen paket adında hata verir** [V]. Debian
  listesindeki `live-boot-doc`, `live-config-doc`, `live-task-*` bizim imajda
  kurulu değil, ve çevrimdışı kurulumda ISO havuzunda (yalnız d-i paketleri)
  indeksi de yok. Kendi `packages.conf`'umuzda yalnız kurulu olanlar
  (`live-boot, live-config, live-config-systemd, calamares,
  calamares-settings-debian`) olmalı, ya da `try_remove` işlemi kullanılmalı
  [V: Calamares packages.conf'ta `try_remove` var, VM'de dene].
- **Parola/sudo:** `users.conf` 3.3.14 anahtarları [D]
  (https://raw.githubusercontent.com/calamares/calamares/v3.3.14/src/modules/users/users.conf):
  `setRootPassword: false` kökü devre dışı bırakır ve "yönetici ile aynı parola"
  kutusunu gizler; `sudoersGroup: sudo` `/etc/sudoers.d/10-installer` yazar (`sudo`
  `defaultGroups`'ta olmalı); `doAutologin` yalnızca onay kutusunun başlangıç
  durumu. `passwd -S root` ile "L" çıktığı VM'de doğrulanmalı [V].
- **Bilgisayar adı:** `hostname.location: EtcFile`, `hostname.writeHostsFile: true`,
  `hostname.template: "carotos"` (sabit metin sorunsuz kullanılır; Debian
  `users.conf`'ta bu blok yok, bu yüzden varsayılan `${first}-${product}`
  önerilir) [D]. Alan kullanıcıya gösterilir (preseed'deki "sorulur, öneri carotos"
  davranışının aynısı).
- **Yerel ayar:** `locale.conf` yalnızca **başlangıç saat dilimini** belirler
  (`region: "Europe"`, `zone: "Istanbul"`, `geoip` için `style: "none"` ya da
  bölümü sil), varsayılan dil anahtarı yoktur [D]. Dil seçimi karşılama
  sayfasından gelir. `localecfg` /etc/default/locale + /etc/locale.conf yazar,
  `locale.gen`'de yorumlu satırları **sona ekleyerek** açar, `locale-gen` çalıştırır;
  satır yoksa sessizce "# Missing" yazar, hata vermez [D]
  (calamares `localecfg/main.py`). Bizim `etc/locale.gen` tr_TR, en_US, ja_JP
  içerir (doğrulandı), dolayısıyla sorun beklenmez; diğer 5-6 dilin
  (`carotos-dil-hazirla` ile üretilenler) Calamares'te seçilirse üretilmeyeceği not
  edilmeli [V].
- **Klavye:** `keyboard.conf` anahtarları `xOrgConfFileName`, `writeEtcDefaultKeyboard`,
  `useLocale1`, `guessLayout` (varsayılan true: yerel ayardan tahmin; tr_TR için
  `tr`), ayrıca özel bir "layout: tr" ön ayarı yok [D]. Çözüm: tr_TR seçilince
  `guessLayout` zaten `tr` verir; `guessLayout: false` canlı oturumun mevcut
  düzenini korur. VM'de iki yol denenmeli [V]. Önizleme için `ckbcomp` gerekir (yok
  sayılabilir) [D].
- **Pkexec ortam değişkenleri:** `pkexec` ortamı temizler; Calamares arayüz dilini
  `LANG`'den alır [V]. Türkçe açılış için sarmalayıcıda `pkexec env LANG="$LANG"
  calamares` gibi bir geçiş ve VM testi gerekir [V].

## 4. Kendi marka ve ayarlarımızı ekleme

- Calamares ayar arama yolu `/etc/calamares` (settings.conf, modules/*.conf, branding/)
  [D, Debian dosya düzeninden]. **Önerilen yol:**
  1. `calamares-settings-debian`'ı paket listesine ekle (modüller, yardımcı betikler,
     bağımlılıklar buradan gelir).
  2. **Kendi branding dizinimiz** `config/includes.chroot/etc/calamares/branding/carotos/`
     (paket dosyası değil, dpkg çakışması yok), `settings.conf` içinde
     `branding: carotos`.
  3. `settings.conf` ve `modules/*.conf` dosyalarını `includes.chroot/etc/calamares/`
     altında **aynı adla** koyup paket dosyalarının üstüne yaz. dpkg conffile uyarısı
     [V]: live-build `includes.chroot`'u paketlerden önce de sonra da kopyalar
     (`chroot_includes_before_packages` ve `chroot_includes_after_packages` betikleri
     live-build'de var [D, betik listesi]); sonra kopyalama bizim dosyayı kesin
     bırakır, yalnız derleme günlüğünde conffile sorusu/uyarısı çıkarsa
     `--force-confold` davranışına bakılmalı. Not: `/etc/default/grub` ISO'ya
     konmaz kuralının gerekçesi (kurucu "yerel değişiklik var" diye sorar) burada da
     geçerli olabilir; ancak Calamares `settings.conf` adını sabit okuduğu için o
     dosyayı ezmek kaçınılmazdır, modül `.conf`'ları ise yalnız değiştirilenler
     konur.
  4. Daha temiz alternatif: kendi `.deb`'imiz `carotos-calamares-settings` (ertelenmiş
     .deb işiyle birlikte düşünülür); `apt.carotos.org` deposuna zaten bağlanacak.
     Şimdilik includes.chroot yeterli.
- `branding.desc` anahtarları (master/forky ve 13 aynı) [D]: `componentName`,
  `welcomeStyleCalamares`, `welcomeExpandingLogo`, `windowExpanding`, `windowSize`
  ("800px,580px"), `windowPlacement`, `strings` (productName, shortProductName,
  version, versionedName, bootloaderEntryName, productUrl, supportUrl,
  knownIssuesUrl, releaseNotesUrl, donateUrl), `images` (productLogo, productIcon,
  productWelcome), `slideshow: "show.qml"`, `slideshowAPI: 2`, `sidebar`/`navigation`,
  `style` (4 renk). CarotOS için: `productName: "CarotOS"`, `version: "1.4"` (kural
  2), `bootloaderEntryName: "CarotOS"` (efiBootloaderId ayrıca "debian" olduğu için
  güvenli), `productUrl: https://carotos.org`. Slayt `show.qml` Debian'ınkinin
  yapısıyla (QtQuick Slideshow API 2) yazılır; 3-4 slayt: on araç, Karşılama, Kurtarma,
  gizlilik.
- Debian logosu/yazısı kalmasın (kural 5): yukarıdaki branding + `calamares-install-debian`,
  `add-calamares-desktop-icon` ve `calamares-desktop-icon.desktop` kullanılmaz
  (bkz. §6 hook'u: sil).

## 5. Bilinen tuzaklar

1. **`sources-final` bizim için yanlış** [D]: `/etc/apt/sources.list` yazar (backports
   dahil). CarotOS `etc/apt/sources.list.d/debian.sources` (deb822) kullanıyor
   (+ `carotos.sources`), sonuç çift tanımlı kaynak uyarısı ve istenmeyen
   backports. Çözüm: dizi'den `sources-final` çıkar.
2. **`sources-media` yalnız `base.list`'i siler**, bizim `debian.sources`/
   `carotos.sources` kalır [D]. Çevrimdışı kurulumda `apt-get update` ağa gitmeyi
   dener (DNS yoksa hızlı hata, ama "ağ var ama kapalı" durumda dakikalarca
   bekleyebilir) [V]. Çözüm: `sources-media` öncesi shellprocess ile bu iki dosyayı
   geçici kenara al, `sources-media-unmount`'tan sonra geri koy.
3. **Recommends:** imzalı GRUB/shim'in hedefe gelmesi `apt-get install grub-efi`
   komutunun Recommends'i kurmasına bağlı [V]. Hedefte `APT::Install-Recommends`
   kapatılmadığından emin ol (`etc/apt/apt.conf.d` altında kapatma yok: kontrol
   edildi; yalnız `50carotos-kurtarma` var).
4. **CarotOS Kurtarma apt kancası** (`etc/apt/apt.conf.d/50carotos-kurtarma`,
   `DPkg::Pre-Invoke`) [D, dosya okundu]: ayar varsayılan açık
   (`kurtarma_motor.py:41`), kurulum sırasında hedefte `apt-get`/`dpkg` her çalıştığında
   rsync tabanlı kurtarma noktası açmaya çalışır (kurulum yavaşlar, hedefi doldurur).
   d-i yolunda da var olan bir risk, ama burada kesin önlem lazım: shellprocess ile
   dosyayı kurulum boyunca kenara al, sonda geri koy.
5. **Hedef paketleri kaldırma:** bkz. §3 (bilinmeyen paket adı).
6. **Canlı kalıntıları:** `/etc/live/config.conf.d/carotos.conf` (canlı
   ana bilgisayar adı ve saat dilimi) kurulu sistemde kalmasın (shellprocess ile sil).
7. **`partition.conf` trixie'de yok** [D]: varsayılanlar geçerli. Debian-live
   listesinde bildirilen bilgi: trixie'de LUKS1 + takas dosyası (RAM'e göre) öntanımlı
   iken forky'nin yeni `partition.conf`'u LUKS2 ve `initialSwapChoice: none` getiriyor
   ve **şifreli kurulumlar GRUB isteminde kalıyor** (GRUB'un LUKS2 desteği eksik)
   [D] (https://lists.debian.org/debian-live/2025/09/msg00007.html). Bize: kendi
   `partition.conf`'umuzu yazarsak `luksGeneration: luks1` ve
   `initialSwapChoice: suspend` (ya da `small`) seçilmeli; EFI bölümü `/boot/efi`,
   `defaultFileSystemType: ext4`, `lvm.enable: false` Debian'ınkini izleyebilir.
   LUKS testi ayrıca yapılmalı.
8. **Qt6 / HiDPI:** Debian başlatıcısı `QT_AUTO_SCREEN_SCALE_FACTOR=1` veriyor
   (3.3.0 öncesi geçici çözüm) [D]; 3.3.14'te gerekmeyebilir, zararsız.
9. **Canlı fstab:** başlatıcının fstab'ı kenara alma adımı gerekli (live-build
   bıraktığı fstab bölümlemeyi bozuyor) [D]. `pkexec` + `sudo` kullanıldığı için
   imajda `sudo` ve `x11-xserver-utils` (`xhost`) olduğundan emin ol [V]; listeye
   açıkça ekle.
10. **NVIDIA:** imajda NVIDIA sürücü paketi yok (yalnız firmware) [V, paket listesi
    okundu]; kurulu sistem için ek iş yok.
11. **Çevrimdışı kurulumda `sources-media` boş/yanlış medium** olasılığı
    (betik `set -e` kullanmıyor, medium yoksa `$CHROOT/`'ye bind mount yapmaya
    kalkar) [D]. Calamares'i yalnızca `/run/live/medium` bağlıyken başlat
    (sarmalayıcıda denetim; Ventoy gibi kimlik kullanımlarında yolun adı farklı
    olabilir [V]).
12. **Ventoy:** `partition.conf` `essentialMounts: live-*, control, ventoy` (forky) [D];
    trixie'de bu dosya yok, Ventoy ile açılışta kendi USB'sini silmeye kalkabilir
    [V]; kendi `partition.conf`'umuza `essentialMounts` eklenmeli.
13. **Daha önce d-i'nin yaptığı ama Calamares'te farklı davranan** her şey §6 tablosunda.
14. **`DEBIAN_FRONTEND` bilgisi:** LUKS yolundaki `apt-get install` komutu
    `DEBIAN_FRONTEND` ayarlamıyor [D]; etkileşimsiz oturumda debconf'ta
    takılma olasılığı var, yalnız şifreli kurulumda [V].

## 6. d-i / hook / firstboot'un yaptığı, Calamares'te yeniden sağlanması gerekenler

| # | Ne | Şu an nerede | Calamares'te |
|---|----|--------------|--------------|
| 1 | Root kilitli, kullanıcı sudo'da | `includes.installer/preseed.cfg:13` (`passwd/root-login false`), yedek: `usr/local/sbin/carotos-firstboot.sh:39-53` | `users.conf`: `setRootPassword: false`, `sudoersGroup: sudo`, `defaultGroups`'ta `sudo`. Firstboot yedeği olduğu gibi çalışır (squashfs'teki servis bağı kopyalanır) |
| 2 | wireshark grubu | `carotos-firstboot.sh:55-64` | Aynı betik ilk açılışta yapar; istersen `defaultGroups`'a `wireshark` ekle (grup imajda var) |
| 3 | Bilgisayar adı `carotos`, kurulumda sorulur | `preseed.cfg:25-26` | `users.conf` `hostname.template: "carotos"` |
| 4 | Açılış sessizliği, `quiet splash loglevel=3...` | `preseed.cfg:19` (kurucu GRUB'a yazmıyor) + `etc/default/grub.d/carotos.cfg` | `carotos.cfg` squashfs ile gelir ve `update-grub`'da grubcfg'nin değerini ezer; VM'de `grep -r CMDLINE /boot/grub/grub.cfg` ile doğrula |
| 5 | GRUB menü süresi, os-prober, adlandırma | `etc/grub.d/99_carotos_sure`, `carotos.cfg`, hook `9996-carotos-onyukleme:10` | Aynı dosyalar squashfs'te; `grub-common` hedefe yüklenirken dosyalara dokunmaz (d-i'de de böyle) [V] |
| 6 | Plymouth teması + initramfs | hook `9996-carotos-onyukleme.hook.chroot:17-21` | squashfs'teki `plymouthd.conf` gelir; `plymouthcfg` tema değiştirmez (yapılandırma yoksa dokunmaz) [D]; `initramfs` modülü (`-k all`) initrd'yi live-boot'suz yeniden üretir. Doğrula: `lsinitramfs /boot/initrd.img-* \| grep -i carotos` |
| 7 | Dil: tr_TR varsayılan, `locale-gen` | `etc/default/locale`, `etc/locale.gen`, hook `9999:91-96` | `localecfg` seçilen dili yazar; `welcome`'da Türkçe seçili gelmesi için sarmalayıcıda `LANG` aktarılır [V] |
| 8 | Saat dilimi | `etc/live/config.conf.d/carotos.conf` (yalnız canlı), kurulu: kurucu sorusu | `locale.conf` `Europe/Istanbul` başlangıç; geoip kapalı |
| 9 | Panel saat eşleştirme | `etc/skel/.config/autostart/carotos-saat-eslestir.desktop` | skel ile gelir, değişiklik yok |
| 10 | apt kaynakları, CD satırı temizliği | `etc/apt/sources.list.d/debian.sources`, `carotos-firstboot.sh:66-69` (`deb cdrom:`) | `sources-final` çıkarılır; cdrom satırı oluşmaz (zararsız) |
| 11 | Kurtarma apt kancası | `etc/apt/apt.conf.d/50carotos-kurtarma`, hook `9980-carotos-kurtarma` | Kurulum boyunca devre dışı (shellprocess) |
| 12 | Dosya sahipliği/izin denetimi | hook `9999:117-132` (`/etc/systemd/system`, `/opt/carotos`, ...) | Aynı döngüye `/etc/calamares`, `/usr/share/calamares` ve yeni `usr/bin/carotos-kur` eklenmeli (shellprocess komutları root çalıştırır) |
| 13 | `os-release` dpkg-divert | hook `9999:41-47` | Divert kaydı `/var/lib/dpkg/diversions` ile squashfs'ten gelir; hedefte `cat /usr/lib/os-release` ile doğrula |
| 14 | ModemManager kapalı, fail2ban açık, ufw, servisler | hook `9999:20-33`, `systemctl enable` bağları | Squashfs içindeki bağlar kopyalanır; `services-systemd` modülü hiçbir şey eklemez (yapılandırma yok) |
| 15 | Kurulum ekranı markası | `includes.installer/usr/share/graphics/logo_debian*.png` | d-i'de kalır; Calamares için `branding/carotos/` |
| 16 | `.disk/info` yeniden yazımı | `hooks/live/9998-carotos-disk-info.hook.binary` | ISO düzeyi, Calamares'ten bağımsız |
| 17 | Karşılama sihirbazı / skel panel | `etc/skel/.config/autostart/carotos-welcome-autostart.desktop`, panel `launcher-NN` | Kullanıcı `useradd -m` ile skel'den alır; canlı ev dizini kopyalanmaz |
| 18 | Çok kullanıcı / sudo yedeği | `carotos-firstboot.sh:43-52` | Calamares tek kullanıcı oluşturur; değişiklik yok |

## 7. Uygulama planı (kod değişikliği YAPILMADI)

### Eklenecek / ezilecek dosyalar
- `config/package-lists/calamares.list.chroot` (yeni): `calamares-settings-debian`
  (calamares + bağımlılıkları getirir), `sudo`, `x11-xserver-utils`, `dosfstools`,
  `e2fsprogs`, `ntfs-3g`, `btrfs-progs`, `squashfs-tools`, `xdg-user-dirs`
  (son altısı varsayım, `apt-get -s install` ile kontrol et [V]). `shim-signed` ve
  `grub-efi-amd64-signed` **eklenmez**. Boyut artışı Qt6/KF6 nedeniyle yüzlerce MB
  olabilir [V]: derlemeden sonra ISO boyutunu ve RAM'i (canlı) ölç.
- `config/includes.chroot/etc/calamares/settings.conf` (trixie dizisi; farklar:
  `branding: carotos`, `sources-final` çıkar, `shellprocess@carotos_once` ve
  `shellprocess@carotos_sonra` ekle, `instances:` bloğu).
- `.../etc/calamares/modules/`: `users.conf`, `packages.conf`, `bootloader.conf`
  (`efiBootloaderId: "debian"`; `installEFIFallback` test sonucuna göre),
  `locale.conf`, `partition.conf`, `welcome.conf` (kendi gereksinimleri, `Ventoy`
  vb.), `finished.conf`, `shellprocess_carotos_once.conf`,
  `shellprocess_carotos_sonra.conf`; `unpackfs.conf`, `mount.conf`, `fstab.conf`,
  `machineid.conf`, `luksopenswaphookcfg.conf`, `displaymanager.conf` paketten gelen
  hâliyle kalır (ezmeye gerek yok).
- `.../etc/calamares/branding/carotos/` (branding.desc, show.qml, logo, welcome.png,
  slaytlar).
- `.../usr/bin/carotos-kur` (kendi sarmalayıcımız: medium denetimi, fstab kenara
  alma, xhost, `pkexec env LANG=... calamares`, çıkışta geri alma), 
  `.../usr/share/applications/carotos-kur.desktop` ("CarotOS'u Kur", `Icon=carotos-kur`
  tema simgesi adıyla, BUILD.md "Uygulama simgeleri" kuralı), simge
  `usr/share/icons/hicolor/256x256/apps/carotos-kur.png`.
- `.../etc/xdg/autostart/carotos-kur-simge.desktop` + `usr/bin/carotos-kur-simge`
  (yalnızca `/run/live/medium` varsa masaüstüne simgeyi kopyalar; Debian'ın
  `add-calamares-desktop-icon` yöntemine benzer, **skel'e koyma** yoksa kurulu
  sistemde de çıkar).
- `config/hooks/live/9979-carotos-calamares.hook.chroot` (yeni, mevcut stile uygun
  `set -e` + doğrulama): `chmod`, dosyaların varlığı, Debian başlatıcılarını sil
  (`/etc/xdg/autostart/calamares-desktop-icon.desktop`,
  `/usr/share/applications/calamares-install-debian.desktop`,
  `/usr/bin/add-calamares-desktop-icon`, `/usr/bin/calamares-install-debian`),
  `grep` ile `settings.conf`'ta `branding: carotos` ve `sources-final` yokluğunu
  doğrula, `command -v calamares`.
- `config/hooks/live/9999-carotos-setup.hook.chroot`: sahiplik döngüsüne
  `/etc/calamares /usr/share/calamares` ve `KOTU` aramasına aynı yolları ekle.
- `docs/` ve `BUILD.md`: "Calamares" bölümü (d-i yedeği, `efiBootloaderId` kuralı,
  `sources-final` kuralı).
- Karşılama sayfası/Former animasyonu ve 7 dil çevirisi (eğitim ve çeviri kuralları):
  "kurulum" sahnesi; çeviri yeni "CarotOS'u Kur" dizgisini kapsamalı.

### shellprocess adımları (öneri; `dontChroot: false`, hedefte çalışır)
`carotos_once` (unpackfs'ten sonra, sources-media'dan önce):
1. `mv /etc/apt/apt.conf.d/50carotos-kurtarma /var/lib/carotos-kurulum-50kurtarma`
   (Kurtarma kancası kurulumda çalışmasın)
2. `mkdir -p /var/lib/carotos-kurulum && mv /etc/apt/sources.list.d/debian.sources
   /etc/apt/sources.list.d/carotos.sources /var/lib/carotos-kurulum/` (çevrimdışı
   güvenilirlik; hata olursa kurulum dursun, `-` öneki yok)

`carotos_sonra` (`sources-media-unmount`'tan sonra, `umount`'tan önce):
1. aynı iki dosyayı yerine koy, `50carotos-kurtarma`'yı geri koy;
2. `rm -rf /etc/live` (yalnız bizim `config.conf.d`; live-config kaldırıldı);
3. `rm -rf /var/lib/carotos-kurulum`;
4. `rm -f /etc/apt/sources.list` varsa ve `debian.sources` geri geldiyse (çift tanım
   olmasın);
5. isteğe bağlı: `-rm -rf /etc/calamares` (calamares kaldırıldıktan sonra) ve
   `-test -L /etc/fstab.orig.calamares`.
Not: `shellprocess` `ROOT`/`USER` değişkenleri destekler [D].

### Dizi (önerilen exec sırası)
`partition, mount, unpackfs, luksbootkeyfile, dpkg-unsafe-io, shellprocess@carotos_once,
sources-media, machineid, fstab, locale, keyboard, localecfg, users, displaymanager,
networkcfg, hwclock, services-systemd, bootloader-config, grubcfg, bootloader,
packages, plymouthcfg, initramfscfg, initramfs, dpkg-unsafe-io-undo,
sources-media-unmount, shellprocess@carotos_sonra, umount`.

### Test planı (VM; ben VM'de çalıştıramam, komutları hazır verilecek)
Her deneme: temiz disk (en az 25 GB), 4 GB RAM.
1. **ISO doğrulama:** `grep -aE "^(shim-signed|grub-efi-amd64-signed)" *.packages`
   boş; `find ~/iso-mount/pool -name 'grub-efi_*' -o -name 'grub-pc_*' -o -name
   'shim-signed_*' -o -name 'grub-efi-amd64-signed_*'`; `ls ~/iso-mount/dists/trixie/main/binary-amd64/Packages*`.
   Hook doğrulamaları (`grep -a` ile).
2. **BIOS (eski BIOS kipi, VirtualBox "Enable EFI" kapalı), çevrimiçi**: tüm disk;
   kurulum sonrası: `sudo whoami`, `passwd -S root` (L), `hostnamectl`, `locale`,
   `localectl` (X11 Layout tr), `grep CMDLINE /boot/grub/grub.cfg`, Plymouth, GRUB
   menü adı, `dpkg -l | grep -E "live-boot|live-config|calamares"` (boş),
   `systemctl status carotos-firstboot`, `cat /etc/apt/sources.list.d/*`.
3. **UEFI (VirtualBox EFI açık, Secure Boot kapalı)**: `ls /boot/efi/EFI/*`,
   `efibootmgr -v`, `dpkg -l shim-signed grub-efi-amd64-signed`; yeniden başlat.
4. **UEFI + Secure Boot** (VirtualBox 7 "Secure Boot" etkin, ya da gerçek donanım
   [V]): `mokutil --sb-state`; açılıştan sonra GRUB istemi gelmemeli;
   NVRAM girdisini sil (`efibootmgr -B`) ve yedek yükleyiciyi dene
   (`installEFIFallback` true/false iki ayrı kurulum).
5. **Tamamen çevrimdışı (NIC kapalı)**: BIOS ve UEFI; `apt-get update` takılması,
   `grub-efi` kurulumunun ISO havuzundan gelmesi (`/var/log/syslog` ya da Calamares
   günlüğü `/root/.cache/calamares/session.log`).
6. **Şifreli disk (LUKS1)** + takas; kurulu sistem açılıyor mu.
7. **Mevcut Windows/Linux ile çift açılış**: `os-prober` menü girdisi.
8. **d-i yedek yolu**: önyükleme menüsündeki d-i hâlâ BIOS ve UEFI'de kuruyor
   (regresyon).
9. Canlı: `Calamares` açılışı süresi, RAM kullanımı (`free -m`), simgenin yalnız
   canlıda çıkması, kurulu sistemde Debian ibaresi aramak (`grep -ri debian`
   görünen metinlerde, EFI "debian" kimliği hariç).

## 8. Açık riskler (öncelik sırasıyla)

1. **Secure Boot zinciri**: gerçek donanımda hiç doğrulanmadı (BUILD.md "Bilinen
   sorunlar" zaten bunu söylüyor). `efiBootloaderId: "debian"` ve yedek yükleyici
   davranışı yalnızca kaynak/forum bilgisine dayanıyor [V].
2. **Havuzda `grub-efi` ve türevleri**: trixie live-build 20250505+deb13u1'in havuzu
   master'daki betiğe göre varsayıldı; çevrimdışı UEFI kurulumu bu yüzden başarısız
   olabilir. (İlk ISO derlemesinde `find pool` ile kontrol.)
3. **apt remove bilinmeyen paket** hatası ve **sources-final**: Debian
   ayarlarını olduğu gibi kullanamayız; ayarlar kopyalanıp düzeltilmeli.
4. **Kurtarma apt kancası** kurulumu yavaşlatabilir/doldurabilir.
5. **ISO boyutu / canlı RAM**: Qt6+KF6 yığını eklenir; boyut CLAUDE.md'deki mevcut
   2,6 GB ve 4 GB RAM kuralını etkileyebilir [V].
6. **Dil/klavye ön ayarı**: `pkexec` ortam sıfırlama nedeniyle varsayılan arayüz
   dili İngilizce çıkabilir [V].
7. **`/etc/calamares` dpkg conffile davranışı** derleme günlüğünde doğrulanmalı [V].
8. Bakım: `calamares-settings-debian` forky'de değişiyor (partition.conf, LUKS2);
   trixie güncellemeleri (13.0.x) ayarlarımızı etkilemez çünkü paket dosyalarını
   yalnızca ezeriz, ama paket güncellenirse conffile sorusu çıkabilir (kurulu
   sistemde paket zaten kaldırıldığı için sorun yok).
9. Güvenlik: `/etc/calamares` altındaki her dosya root olarak çalışır; sahiplik/izin
   denetimi (`9999` hook'u) ve `carotos-kur` betiğinde sabit yol/ortam temizliği şart.

## Kaynak listesi
- https://packages.debian.org/trixie/calamares-settings-debian
- https://packages.debian.org/trixie/all/calamares-settings-debian/filelist
- https://packages.debian.org/trixie/calamares
- https://packages.debian.org/trixie/live-task-xfce
- https://sources.debian.org/src/calamares-settings-debian/13.0.13-1/
- https://salsa.debian.org/live-team/calamares-settings-debian (master = forky)
- https://salsa.debian.org/live-team/live-images (dal `debian`, `images/xfce-desktop`)
- https://salsa.debian.org/live-team/live-build (`scripts/build/installer_debian-installer`)
- https://salsa.debian.org/live-team/live-build/-/merge_requests/352
- https://launchpad.net/debian/+source/live-build/+changelog
- https://calamares.codeberg.page/docs/deploy-issues
- https://raw.githubusercontent.com/calamares/calamares/v3.3.14/src/modules/{users,locale,keyboard,bootloader,shellprocess,initramfs,plymouthcfg,localecfg}
- https://lists.debian.org/debian-live/2025/09/msg00007.html
- https://www.debian.org/News/2025/20250809
