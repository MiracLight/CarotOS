# CarotOS Derleme

Debian 13 (trixie) tabanlı CarotOS ISO görüntüsünün `live-build` ile üretilmesi.

## Gereksinimler

- Debian 13 (trixie). Derleme makinesi hedef dağıtımla aynı sürüm olmalıdır.
- `live-build`
- **En az 8 GB boş disk alanı.** Bu yapılandırma derleme başına yaklaşık 6 GB
  geçici veri üretir (`chroot/` ~3.6 GB, `binary/` ~2.1 GB) ve buna ~2.1 GB'lık
  ISO çıktısı eklenir. Alan yetmezse derleme ISO paketleme aşamasında
  "Image size exceeds free space" ile kesilir.

## Derleme

```
cd ~/carotos-iso
sudo lb clean --purge
lb config \
  --distribution trixie \
  --architectures amd64 \
  --debian-installer live \
  --archive-areas "main contrib non-free non-free-firmware" \
  --image-name "carotos-1.0" \
  --uefi-secure-boot enable \
  --firmware-chroot true
sudo lb build 2>&1 | tee build.log
```

Üç komut da bu sırayla çalıştırılmalıdır; gerekçesi için "lb clean davranışı"
bölümüne bakın.

### Derleme öncesi paket kontrolü

Bulunamayan tek bir paket derlemeyi yarıda keser ve chroot'u yarım bırakır.
Paket listesi her değiştiğinde önce şunu çalıştırın:

```
apt-cache policy $(cat config/package-lists/carotos.list.chroot) 2>&1 \
  | grep -B1 "Aday: (yok)"
```

Çıktı boşsa tüm paketler mevcuttur.

### Bellek gereksinimi

`mksquashfs` adımı belleğe duyarlıdır. 2 GB RAM'li bir sanal makinede bu
aşamada çekirdek çökmesi gözlendi — ekran kilitlenir ve klavye ışıkları yanıp
söner. En az **4 GB RAM** ayırın; derleme sırasında sanal makinede başka
uygulama çalıştırmayın.

## Doğrulama

```
grep -ai "ISO image produced" build.log
grep -ai "CarotOS: kaynak bulundu" build.log
grep -ai "firstboot servisi etkinlestirildi" build.log
grep -ai "karsilama sihirbazi yerlestirildi" build.log
grep -ai "sistem sagligi yerlestirildi" build.log
grep -ai "shim" build.log | head -3
```

Sırasıyla ISO'nun tamamlandığını, önyükleme görselinin değiştirildiğini, ilk
açılış servisinin etkinleştirildiğini, iki uygulamanın yerleştirildiğini ve
Secure Boot desteğinin devreye girdiğini gösterir. Hepsi sonuç vermelidir.
Derlemenin hatasız bitmesi, hook'ların çalıştığı anlamına gelmez — hook'lar
sessizce başarısız olabilir, bu yüzden ayrı ayrı aranır.

`grep`'e `-a` verilmesi zorunludur: derleme günlüğüne ikili veri karışır ve
`grep` dosyayı metin saymayı bırakır ("İkili dosya eşleşiyor" der, eşleşmeleri
göstermez).

Ayrıca şu **boş dönmelidir**:

```
grep -E "^(shim-signed|grub-efi-amd64-signed)" carotos-1.0-amd64.packages
```

Gerekçesi için "Secure Boot" bölümüne bakın.

ISO'nun yazıldığı dizin yapılandırmaya göre değişir:

```
sudo find / -iname "carotos-1.0*" 2>/dev/null
```

## Dizin yapısı

```
config/
├── package-lists/carotos.list.chroot   Kurulacak paketler
├── includes.chroot/                    Sisteme kopyalanacak dosyalar
│   ├── etc/os-release
│   ├── etc/apt/sources.list.d/debian.sources
│   ├── etc/systemd/system/carotos-firstboot.service
│   ├── etc/skel/.config/xfce4/            Panel düzeni ve başlatıcılar
│   ├── etc/skel/.config/autostart/        Karşılama sihirbazı
│   ├── opt/carotos/security-panel/
│   ├── opt/carotos/welcome/
│   ├── opt/carotos/health/
│   ├── usr/local/sbin/carotos-firstboot.sh
│   ├── usr/share/applications/            .desktop menü girdileri
│   ├── usr/share/backgrounds/carotos/
│   ├── usr/share/carotos/welcome/         Sihirbaz ekran görüntüleri
│   └── usr/share/carotos/carotos_ascii.txt
├── includes.installer/preseed.cfg      debian-installer ön-yapılandırması
├── hooks/live/
│   ├── 9998-carotos-splash.hook.binary
│   └── 9999-carotos-setup.hook.chroot
└── carotos-splash.png                  640x480 önyükleme görseli
```

---

## Önyükleme görseli

Özel bir önyükleme görselini `config/bootloaders/` altına koyarak veya
`splash.svg` sağlayarak değiştirmek bu yapılandırmada sonuç vermez. Nedeni
`live-build`'in `binary_bootloader_splash` betiğinin davranışıdır:

- Betik, hedefte kullanılabilir bir `splash.png` **zaten varsa** SVG→PNG
  dönüşümünü hiç yapmaz. Dolayısıyla sağlanan SVG göz ardı edilir.
- SVG içine base64 olarak gömülmüş PNG'ler işlenmez. chroot içindeki
  `rsvg-convert` bu biçimi çözemez ve hata vermeden varsayılan görsele döner.
  Derleme başarılı görünür, görsel değişmez.
- `binary_hooks` adımı, splash hazırlandıktan **sonra** ancak ISO
  paketlenmeden **önce** çalışır.

Uygulanan çözüm bu son maddeye dayanır: hazır bir 640x480 PNG, bir binary hook
ile ISO paketlenmeden hemen önce yerine yazılır. Hook `binary/` dizininden
çalışır ve kaynağa `../config/carotos-splash.png` yolundan erişir. Değiştirilen
dosyalar:

```
isolinux/splash.png
boot/grub/splash.png
```

Hook dosyasının izni `755` olmalıdır. Yalnızca çalıştırma izni yetmez; okuma
izni de gerekir. İzin eksikse hook çalışmaz ve derleme günlüğünde bununla ilgili
bir hata görünmez.

```
chmod 755 config/hooks/live/9998-carotos-splash.hook.binary
```

## Sudo yetkisi

Debian kurulumunda root parolası ayrıca belirlendiğinde normal kullanıcı `sudo`
grubuna eklenmez. Bunun chroot hook'u içinde `/etc/passwd` üzerinde dönen bir
döngüyle çözülmesi **mümkün değildir**: chroot hook'ları derleme sırasında
çalışır, kurulum kullanıcısı ise çok sonra, hedef sistem kurulurken oluşturulur.
Döngü boş listeyle çalışır, sıfır kodla çıkar ve günlüğe hiçbir iz bırakmaz.

Çözüm iki katmanlıdır:

**1. Kurulum aşaması.** `config/includes.installer/preseed.cfg`:

```
d-i passwd/root-login boolean false
```

`user-setup` bileşeni bu değeri gördüğünde normal kullanıcı oluşturmayı zorunlu
kılar ve kullanıcıyı `sudo` grubuna ekler. Dosyanın bu dizinde bulunması
yeterlidir; `lb config`'e ek parametre gerekmez, önyükleyici menüsüne
dokunulmaz. Sonuç olarak kurulumda root parolası sorulmaz ve root hesabı
kilitli kalır; yönetici işlemleri `sudo` ile yapılır.

**2. İlk açılış.** `carotos-firstboot.service`, kurulmuş sistemin ilk açılışında
UID ≥ 1000 olan kullanıcıları `sudo` grubuna ekler ve
`/var/lib/carotos/firstboot.done` damgasını bırakır. Birinci katman devreye
girmezse yedek görevi görür.

### Doğrulama durumu

Temiz kurulumda (2026-08-16, `carotos-1.0-amd64.iso`) doğrulandı:

```
$ sudo whoami
root
$ sudo passwd -S root
root L ...
$ systemctl status carotos-firstboot.service
Active: active (exited)   Main PID: 743 (code=exited, status=0/SUCCESS)
```

`L`, root hesabının kilitli olduğunu gösterir; yani birinci katman devreye
girmiştir. İkinci katman çalışmış ancak yapacak iş bulamamıştır — `usermod -aG`
kullanıcı zaten gruptayken de başarıyla döndüğü için, servisin tek başına
yeterli olup olmadığı bu testle **kanıtlanmamıştır**. Preseed kaldırılacaksa
ayrıca test edilmelidir.

### Root hesabı

Kurulumda root parolası sorulmaz ve hesap kilitli gelir. Bu, eğitim ortamları
göz önünde bulundurularak seçilmiş bir varsayılandır: kullanıcı sudo yetkisiz
kalamaz, root ile doğrudan oturum açılamaz ve yetkili işlemler sudo üzerinden
günlüğe kaydedilir.

Root hesabını etkinleştirmek için:

```
sudo passwd root
```

Yeniden kilitlemek için:

```
sudo passwd -l root
```

## lb clean davranışı

`live-build` tamamlanan adımları `.build/` altında işaretler ve tekrar
çalıştırmaz. `chroot/` veya `binary/` dizinleri elle silinse bile bu işaretler
kalır; sistem adımları "zaten yapıldı" sayarak atlar. Sonuç, eksik bir ISO veya
uygulanmamış bir hook olur ve hata mesajı alınmaz.

- `lb clean --binary` yetersizdir. chroot yeniden kurulmadığı için derleme
  "vmlinuz bulunamadı" hatası verir.
- `sudo lb clean --purge` tam temizlik yapar.
- `lb clean` yapılandırma ağacını da sıfırlar; ardından `lb config` **yeniden**
  çalıştırılmalıdır, aksi halde derleme config aşamasının eksik olduğunu
  bildirir.

## Secure Boot ve UEFI

`--uefi-secure-boot enable` parametresi, derleme sırasında imzalı `shim` ve
`grub-efi` paketlerini kurar ve imzalı `.efi` dosyalarını ISO'ya kopyalar.
Önyükleme zinciri: UEFI → shim → grub. Değer `enabled` değil **`enable`**
olmalıdır; geçerli değerler `auto|enable|disable`. `auto` paketleri bulamazsa
sessizce imzasız grub'a döner, `enable` ise derlemeyi durdurur — bu yüzden
`enable` tercih edilir.

Doğrulama, ISO bağlanarak yapılır:

```
sudo mount -o loop carotos-1.0-amd64.iso ~/iso-mount
ls -l ~/iso-mount/EFI/boot/
sudo umount ~/iso-mount
```

`bootx64.efi` yaklaşık 1 MB olmalıdır (imzalı shim). Çok daha küçükse imzasız
sürüm kullanılmış demektir.

### İmzalı paketler paket listesine EKLENMEZ

`shim-signed` ve `grub-efi-amd64-signed` paketlerini
`config/package-lists/carotos.list.chroot` içine eklemeyin. Eklendiğinde BIOS
(msdos) modundaki kurulum **başarısız olur**:

```
grub-installer: shim-signed:amd64 depends on grub-efi-amd64-bin; however:
grub-installer:   Package grub-efi-amd64-bin is to be removed.
grub-installer: error processing package grub-efi-amd64-signed (--purge):
grub-installer:   this is a protected package; it should not be removed
main-menu: Menu item 'grub-installer' failed.
```

Sebep: `grub-installer`, BIOS modunda kurulum yaparken EFI paketlerini kaldırıp
`grub-pc` kurmak ister. Kurulu sistemde bulunan `shim-signed` bunu bağımlılıkla
engeller ve kurulum önyükleyicisiz kalır.

`--uefi-secure-boot enable` parametresi tek başına yeterlidir: live-build o
paketleri derleme sırasında geçici olarak kullanır, kurulan sisteme geçirmez.
Bu yüzden doğrulamada `carotos-1.0-amd64.packages` içinde bu iki paket
**bulunmamalıdır**.

## Uygulama simgeleri

Panel ve menü başlatıcıları, `.desktop` dosyasında **tam yol** yerine **tema
simgesi adı** kullanmalıdır. Xfce panel başlatıcısı, tam yollu (`Icon=/usr/...`)
simgeleri güvenilir biçimde çözemez ve genel bir simgeye düşer.

Doğru yöntem: simgeyi standart tema dizinine koymak ve adla çağırmak.

```
config/includes.chroot/usr/share/icons/hicolor/256x256/apps/carotos-security-panel.png
```

`.desktop` içinde: `Icon=carotos-security-panel` (uzantısız, yolsuz).

Panel başlatıcısının kopyası da (`/etc/skel/.config/xfce4/panel/launcher-NN/`)
aynı adı kullanmalıdır; menüdeki `.desktop` ile panel başlatıcısı ayrı
dosyalardır, ikisi de düzeltilmelidir.

Hook, tema dizinine dosya konduktan sonra önbelleği tazelemelidir:

```
gtk-update-icon-cache -f /usr/share/icons/hicolor
```

## Kullanıcı avatarı

Kurulan sistemde her kullanıcının profil avatarı, giriş ekranında ve yetki
(polkit) pencerelerinde görünür. Varsayılan olarak Debian'ın kırmızı logosu
gelir. Marka tutarlılığı için bu, `config/includes.chroot/etc/skel/.face`
dosyasıyla değiştirilir:

- Kare bir PNG (358x358 kullanıldı; sistem otomatik ölçekler)
- `/etc/skel/.face` her yeni kullanıcıya kopyalanır

Bu bir kullanıcı avatarıdır, uygulama simgesi değil; polkit penceresindeki
logo `.desktop` dosyasından değil bu dosyadan gelir.

## Panel başlatıcı adları

Xfce'nin genel "web tarayıcısı" başlatıcısı (`xfce4-web-browser.desktop`),
`Exec=exo-open --launch WebBrowser` ile varsayılan tarayıcıyı açar ve adı
"Web Browser" görünür. Firefox varsayılan olsa bile ad genel kalır. Başlatıcı
kopyasında (`/etc/skel/.config/xfce4/panel/launcher-NN/`) yalnızca `Name` ve
`Comment` alanları düzeltilir; `Exec` korunur (kullanıcı ileride başka tarayıcı
seçerse başlatıcı otomatik ona geçsin).

## Yerel ayarlar (dil)

`--debian-installer live` ile üretilen ISO'da kurulan sistem, kurulumda dil
seçilse bile `LANG=C.UTF-8` ile açılabilir — ne Türkçe ne İngilizce, sistem
dilsiz kalır ve uygulamalar İngilizce metne düşer. Sebep: `locales` paketi
yapılandırılmamış ve hiçbir yerel ayar üretilmemiştir.

Çözüm üç parçalıdır:

1. Paket listesine `locales` eklenir.
2. `config/includes.chroot/etc/locale.gen` üretilecek dilleri listeler:

```
tr_TR.UTF-8 UTF-8
en_US.UTF-8 UTF-8
```

3. `config/includes.chroot/etc/default/locale` varsayılanı belirler
   (`LANG=tr_TR.UTF-8`), ve hook `locale-gen` çalıştırır — dosyaları koymak
   yetmez, diller üretilmelidir.

## GitHub'dan kurulan araçların yapılandırması

nikto Debian deposunda yalnızca 2.1.5 (2011) sürümüyle bulunur; güncel sürüm
(2.5+) için GitHub'dan klonlanır. Ancak `/opt/nikto/program/` altına açılan
program, `nikto.conf` içindeki dizin yollarını kendiliğinden bilmez ve
"Could not work out the nikto EXECDIR" ile başlamaz.

Çözüm: `config/includes.chroot/etc/nikto.conf` dosyasına doğru yollar yazılır:

```
EXECDIR=/opt/nikto/program
PLUGINDIR=/opt/nikto/program/plugins
DBDIR=/opt/nikto/program/databases
TEMPLATEDIR=/opt/nikto/program/templates
```

Genel kural: GitHub'dan `/opt` altına kurulan araçların çalıştırılabilir
kopyası `/usr/local/bin`'e konduğunda, aracın veri/eklenti dizinlerini
bulamama ihtimali vardır; bu yollar açıkça yapılandırılmalıdır.

## Firmware

`--firmware-chroot true`, firmware paketlerini canlı oturumun kök dosya
sistemine dahil eder. `--archive-areas` içinde `non-free-firmware` bulunduğu
sürece Wi-Fi, ses ve grafik firmware'lerinin tamamı (AMD, NVIDIA, Intel grafik,
`firmware-sof-signed`, tüm kablosuz yongalar) paket listesine ayrıca eklenmeden
gelir. Doğrulamak için:

```
grep -c "^firmware" carotos-1.0-amd64.packages
```

## Installer markalaması

Kurulum arayüzünün üst bandı `config/includes.installer/usr/share/graphics/`
altındaki dosyalarla değiştirilir. Dosya adları korunmalıdır.

| Dosya | Ölçü | Biçim |
|---|---|---|
| `logo_debian.png` | 800x75 | 8-bit RGB PNG, non-interlaced |
| `logo_debian_dark.png` | 800x75 | 8-bit RGB PNG, non-interlaced |

`logo_installer.png` ve `logo_installer_dark.png`, `logo_debian.*` dosyalarına
işaret eden sembolik bağlantılardır; ayrıca sağlanmalarına gerek yoktur.

Bant tek parçadır — arka plan ve logo aynı görselin içindedir, dolayısıyla
saydam arka plan kullanılmaz. 75 piksel yükseklikte ince yazı ve ayrıntılı
çizim okunmaz.

Orijinal dosyaları incelemek için (ölçü değişirse doğrulamak amacıyla):

```
mkdir -p ~/iso-mount ~/logo-test
sudo mount -o loop carotos-1.0-amd64.iso ~/iso-mount
cd ~/logo-test
zcat ~/iso-mount/install/gtk/initrd.gz | cpio -idmv "usr/share/graphics/*"
file usr/share/graphics/*
cd ~ && sudo umount ~/iso-mount
```

Yolun `install/gtk/` olduğuna dikkat edin. Debian belgelerinin çoğunda geçen
`install.amd/gtk/` yolu, `live-build` ile üretilen ISO'da bulunmaz.

## Debian 13 paket notları

- `policykit-1` kaldırıldı; yerine `polkitd`.
- `update-grub` chroot içinde çalışmaz (GRUB kurulu değildir). GRUB
  yapılandırması `includes.chroot` üzerinden yapılır.
- `xorriso` ve `isolinux` derleme sırasında kaldırılıp yeniden kurulur. Bu
  beklenen davranıştır ve `apt-mark manual` ile engellenemez.
- `wordlists` paketi Debian'da **yoktur**; Kali'ye özgüdür ve derlemeyi keser.
  Kelime listeleri zaten `john`, `nmap` ve `sqlmap` paketleriyle birlikte
  gelir (`/usr/share/john/password.lst`,
  `/usr/share/nmap/nselib/data/passwords.lst`,
  `/usr/share/sqlmap/data/txt/wordlist.txt`). Genel olarak Kali paket adları
  Debian'a doğrudan taşınmaz.
- Masaüstü ortamı `xfce4` üzerinden kurulduğunda `network-manager` ve
  `network-manager-gnome` gelmez. İkisi olmadan kablosuz ağa grafik arayüzden
  bağlanılamaz; paket listesine açıkça eklenmelidir. Aynı şekilde `gvfs`
  olmadan USB bellekler dosya yöneticisinde görünmez.

---

## Bilinen sorunlar

- Secure Boot'un gerçek donanımda çalıştığı henüz doğrulanmadı. İmzalı shim
  ISO'da mevcut (`EFI/boot/bootx64.efi` ~1 MB) ama VirtualBox'ta Secure Boot
  olmadığı için imzanın gerçek UEFI tarafından kabul edildiği görülmedi.
- `apt upgrade` sonrası bütünlük, depoda yeni paket çıkana kadar anlamlı
  test edilemedi (şu ana dek boş döndü, komut çalışıyor).
- `mksquashfs` aşamasına gelmeden, paket indirme sırasında da nadiren çekirdek
  çökmesi (kernel panic) gözlendi. Bellekle ilgili değil (6 GB'da da oldu);
  ana makine/VirtualBox kaynaklı rastgele bir olay. Aynı build yeniden
  başlatıldığında sorunsuz tamamlandı — yapılandırma sorunu değildir.
