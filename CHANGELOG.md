# CarotOS Sürüm Geçmişi (Changelog)

CarotOS ISO sürümlerinin kaydı.
Her satır, bir `lb build` çıktısıyla üretilmiş ve sanal makinede kurularak
doğrulanmış bir alt sürümü temsil eder.

Not: Toplam 9 alt sürüm üretilmiştir. Bir ara sürüm (7) ayrıca UEFI/EFI
modunda yeniden kurulmuş, ancak bu yeni bir derleme olmadığından ayrı sürüm
sayılmamıştır.

---

## Sürüm 12 — 1.2.1 "Eggshell": bellek, açılış ve Poligon güncellemesi
**Durum:** Yayınlandı (ISO adı 1.2 olarak kaldı; `carotos-1.2-amd64.iso`
dosyası güncellendi, carotos.org ve GitHub Release metni yeni sha256 ile
düzeltildi).
- **Bellek kullanımı düşürüldü:** Papirus simge temalarının önbelleği
  (`icon-theme.cache`) ISO'da üretilmiyordu; her GTK süreci (panel, `nm-applet`,
  `xfdesktop`, `xfwm4`) simgeleri tek tek tarayıp yüzlerce MB fazla bellek
  tutuyordu. Önbellek artık derleme sırasında üretiliyor
  (`config/hooks/live/9998-carotos-ikon-onbellek.hook.chroot`). Boşta bellek
  kullanımı yaklaşık 980 MB'tan yaklaşık 600 MB'a indi.
- **Masaüstü arka planları** 2560 piksel genişliğe küçültüldü (`wallpaper1`
  46 MB'tan 5,7 MB'a). ISO yaklaşık 44 MB küçüldü ve masaüstü daha hızlı
  çiziliyor.
- **USB izleyici** iki kez başlıyordu (`/etc/xdg/autostart` ve `/etc/skel`
  girdileri); yinelenen başlangıç girdisi kaldırıldı.
- **Oturum açılış perdesi** yeniden yazıldı: yeni CarotOS logosu, pencere
  yöneticisinden bağımsız tam ekran, saniyede onlarca süreç başlatan hazırlık
  denetiminin yerine `/proc` okuması, zaman aşımı koruması
  (`05carotos-acilis` içinde `timeout`).
- **Üst panel:** CarotOS Mağaza başlatıcısı kendi logosuyla eklendi.
- **CarotOS Poligon:** ISO'ya yanlışlıkla Eylül başındaki eski sürüm
  girmişti. Güncel sürümle değiştirildi; misafir, kullanıcı oluşturma ve
  kullanıcı girişi seçenekleri ile yeni görev ve soru dosyaları artık gerçekten
  ISO'da.

## Sürüm 11 — 1.2 "Eggshell": CarotOS Mağaza ve yeni masaüstü
**Durum:** Yayınlandı (GitHub Release v1.2, carotos.org).
- **CarotOS Mağaza** eklendi: yedi kategoride 51 uygulama sunan grafik
  mağaza. Kurulum ve kaldırma `apt` üzerinden yürütülür, yetki `pkexec` ile
  istenir. Açık ve koyu tema, Türkçe ve İngilizce arayüz.
- **Karşılama Sihirbazı** 15 sayfaya çıkarıldı: üç seçenekli masaüstü arka
  planı sayfası, USB Denetimi ve CarotOS Mağaza tanıtım sayfaları eklendi.
  Seçilen arka plan sihirbazdan çıkışta masaüstüne uygulanır.
- **USB Denetimi** oturum açılışında arka planda başlar.
- **CarotOS Poligon:** misafir, kullanıcı oluşturma ve kullanıcı girişi
  seçenekleri eklendi.
- **Masaüstü teması** yenilendi: Arc GTK teması, Papirus simge teması ve
  Breeze imleç teması. Açık veya koyu seçimi karşılama sihirbazında yapılır;
  sihirbaz tema, simge ve imleci seçime göre birlikte değiştirir. Varsayılan
  koyudur.
- Yeni CarotOS arka planları: oturum açma ekranı (LightDM) için bir görsel,
  masaüstü için üç görsel. Yeni kurulumda varsayılan masaüstü arka planı
  `carotosbackgroundwallpaper1`'dir.
- **Oturum açılış perdesi:** LightDM girişinden sonra masaüstü hazır olana
  kadar siyah ekran yerine animasyonlu bir perde gösterilir
  (`/usr/local/bin/carotos-oturum-acilis`, `/etc/X11/Xsession.d/05carotos-acilis`).
- Terminal isteminde `kullanıcı@bilgisayar` kısmı yeşilden cyan renge
  çevrildi.
- Açılış (splash) görselinde sürüm 1.2 olarak güncellendi.
- Sürüm etiketi 1.1'den 1.2'ye yükseltildi (`/etc/os-release`, `/etc/issue`,
  karşılama sihirbazı, README, BUILD.md, `LB_IMAGE_NAME`).

## Sürüm 10 — 1.1 "Eggshell": CarotOS Poligon
**Durum:** Yayınlandı (GitHub Release v1.1, carotos.org).
- **CarotOS Poligon** eklendi: öğrenci ve öğretmen uygulamalarından oluşan,
  izole bir ortamda hydra, nmap, john, sqlmap ve tshark ile sızma testi
  pratiği yapılmasını sağlayan yeni bir modül. ufw ve fail2ban ile savunma
  görevleri de içeriyor. Masaüstü panelinde ayrı kısayollarla erişilebiliyor.
- tshark artık normal kullanıcı hesabında "Erişim engellendi" hatası
  vermeden çalışıyor (ilk açılışta wireshark grubuna otomatik ekleniyor).
- "Dene" (Try Live) modunda oturum açan kullanıcının adı artık
  "Debian Live User" yerine "CarotOS Live User" olarak görünüyor.
- Sürüm etiketi 1.0'dan 1.1'e yükseltildi (`/etc/os-release`, `/etc/issue`,
  README, BUILD.md).

**Yayın sonrası düzeltmeler (aynı "1.1" etiketi altında, ISO indirme
bağlantısındaki dosya üç kez güncellendi — sha256 her seferinde
değişti):**
- **Kritik:** İlk yayınlanan 1.1 ISO'su hiç açılmıyordu —
  `--bootappend-live` parametresi verilirken çekirdeğin kök dosya
  sistemini bulması için zorunlu olan `boot=live components` değeri
  yanlışlıkla silinmişti. Düzeltildi, gerçek donanımda yeniden
  doğrulandı.
- CarotOS Poligon, aynı fiziksel makine dışında (öğretmen ve öğrenci
  farklı bilgisayarlarda) çalışmıyordu — öğrenci uygulaması sabit
  olarak `127.0.0.1`'e bağlanıyordu. Öğrenci uygulamasına "Öğretmen
  Adresi" alanı eklendi, ağ üzerinden farklı makineler arası bağlantı
  doğrulandı.

---

## Sürüm 9 — Kozmetik olarak en sağlam, donanıma portlanmaya hazır
**Durum:** Referans sürüm. Gerçek UEFI veya BIOS donanımında kart hatası
vermeden kurulması hedeflenen aday. Sürüm etiketi 1.09V olarak güncellenecek.

- Kullanıcı avatarı (`.face`) Debian kırmızı logosundan CarotOS kaplumbağasına
  değiştirildi — giriş ekranı ve yetki (polkit) pencerelerinde marka tutarlılığı
- Firefox panel başlatıcısının adı "Web Browser" yerine "Firefox" yapıldı (TR/EN)
- Önceki tüm düzeltmeler doğrulandı: BIOS + UEFI kurulum, Türkçe dil, simgeler,
  nikto, panel araçları

## Sürüm 8 — Panel araç düzeltmeleri ve gerçek kullanım testi
- **nikto çalışır hale getirildi:** `/etc/nikto.conf` ile dizin yolları
  (EXECDIR, PLUGINDIR, DBDIR, TEMPLATEDIR) açıkça tanımlandı. GitHub'dan
  kurulan nikto artık ilk açılıştan itibaren çalışıyor
- **Panel "Durdur" düğmesi düzeltildi:** pkexec ile root olarak başlatılan
  araçlar (tcpdump gibi) artık durdurulabiliyor. Araçlar kendi süreç grubunda
  başlatılıyor, root araçlar için durdurma da root yetkisiyle yapılıyor
- **cdrom satırı temizliği:** kurulum sonrası ilk açılışta `/etc/apt/sources.list`
  içindeki eski CD kaynağı otomatik devre dışı bırakılıyor; `apt update` artık
  hata satırı üretmiyor
- Panel araçları gerçek kurulumda test edildi: nmap, nikto, john, ufw, tcpdump

## Sürüm 7 — Türkçe dil ve simge düzeltmeleri
- **Sistem dili düzeltildi:** kurulan sistem artık Türkçe açılıyor. `locales`
  paketi eklendi, tr_TR ve en_US yerel ayarları üretiliyor, varsayılan Türkçe
  (önceki sürümlerde sistem `C.UTF-8` ile dilsiz açılıyordu)
- **Güvenlik Paneli simgesi düzeltildi:** simge tema dizinine
  (`hicolor/256x256/apps`) taşındı, `.desktop` tema adıyla çağırıyor. Menüde ve
  panelde artık kaplumbağa simgesi görünüyor (önce genel simgeye düşüyordu)
- Panel başlatıcısının simgesi de aynı şekilde düzeltildi
- Not: Bu sürüm ayrıca UEFI/EFI modunda yeniden kurularak doğrulandı

## Sürüm 6 — Donanım desteği ve Secure Boot
- **Secure Boot desteği eklendi:** `--uefi-secure-boot enable` ile imzalı shim
  ve grub-efi ISO'ya dahil edildi (UEFI → shim → grub zinciri)
- **Firmware desteği:** `--firmware-chroot true` ile Wi-Fi, ses ve grafik
  firmware'leri canlı sisteme dahil edildi (AMD, NVIDIA, Intel, tüm kablosuz)
- **Ağ ve kullanılabilirlik paketleri eklendi:** network-manager (kablosuz ağ
  arayüzü), gvfs (USB otomatik bağlama), mokutil, efibootmgr, bash-completion,
  htop, alsa-utils
- **Kritik düzeltme:** imzalı önyükleyici paketleri kurulu sisteme dahil
  edilmedi — aksi halde BIOS modundaki kurulum GRUB aşamasında kırılıyordu

## Sürüm 5 — Karşılama sihirbazı ve sistem sağlığı uygulamaları
- **CarotOS Karşılama Sihirbazı eklendi:** ilk açılışta çıkan, 9 sayfalı,
  iki dilli (TR/EN) tanıtım. Linux temelleri, dosya sistemi, yazılım kurulumu,
  güvenlik araçları tanıtımı. "Bir daha gösterme" seçeneğiyle
- **CarotOS Sistem Sağlığı uygulaması eklendi:** 20 denetim, 6 kategori,
  puanlama, tek tıkla düzeltme düğmeleri, rapor kaydetme. Güvenlik duvarı,
  güncellemeler, depolar, açık portlar, hesap güvenliği denetimi
- Her iki uygulama panel başlatıcısı olarak üst panele eklendi
- Güvenlik Paneli açık tema hatası düzeltildi (düğme yazıları okunmuyordu)

## Sürüm 4 — APT depoları ve eksik paketler (kritik işlevsel düzeltme)
- **APT depo sorunu çözüldü:** kurulan sistemde ağ deposu tanımlı değildi,
  hiçbir paket kurulamıyordu. `debian.sources` eklendi (main + security +
  updates). Dış kullanıcı testinde bulunan en kritik hata
- Eksik paketler eklendi: net-tools, dnsutils, lsb-release
- ISO adındaki çift "amd64" düzeltildi

## Sürüm 3 — Kod adı ve installer markalaması
- **"Eggshell" kod adı** os-release'e işlendi (PRETTY_NAME ve VERSION)
- **Kurulum ekranı markalandı:** debian-installer üst bandı CarotOS banner'ı
  ile değiştirildi (800x75, kendi tasarım)
- **fastfetch başlık renkleri** cyan yapıldı (display.color.keys)
- **sudo düzeltmesi doğrulandı:** ilk kullanıcı otomatik yönetici yetkisi
  alıyor (firstboot servisi + preseed ikili katmanı)

## Sürüm 2 — Sudo düzeltmesi (ilk deneme)
- Kurulum sonrası ilk açılışta kullanıcıyı sudo grubuna ekleyen firstboot
  servisi eklendi (chroot hook'unun kurulum kullanıcısını görememesi sorunu)
- Root hesabı kilitli, yönetici işlemleri sudo üzerinden

## Sürüm 1 — İlk tam sürüm "Eggshell"
- Debian 13 (trixie) tabanlı, XFCE masaüstü
- Boot logosu (kaplumbağa), duvar kağıdı, ASCII logo, iki panelli masaüstü
- 10 güvenlik aracı: nmap, tcpdump, tshark, aircrack-ng, nikto, sqlmap, john,
  hydra, ufw, fail2ban
- CarotOS Güvenlik Paneli (araçlar için rehberli grafik arayüz)

---

## Sonraki adımlar (Sürüm 10+)
- Gerçek donanımda test (Secure Boot doğrulaması)
- İkinci kullanıcıya yönetici yetkisi verme akışının belgelenmesi
- README, LICENSE, sürüm etiketi güncellemesi (1.09V)
- Birkaç haftalık mükemmelleştirme sürecinde ek düzeltmeler
