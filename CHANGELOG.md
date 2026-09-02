# CarotOS Sürüm Geçmişi (Changelog)

CarotOS ISO sürümlerinin kaydı.
Her satır, bir `lb build` çıktısıyla üretilmiş ve sanal makinede kurularak
doğrulanmış bir alt sürümü temsil eder.

Not: Toplam 9 alt sürüm üretilmiştir. Bir ara sürüm (7) ayrıca UEFI/EFI
modunda yeniden kurulmuş, ancak bu yeni bir derleme olmadığından ayrı sürüm
sayılmamıştır.

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
