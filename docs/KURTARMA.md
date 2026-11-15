# CarotOS Kurtarma — tasarım kararları

"Sistemi son kaydedilen kararlı noktaya döndüren" uygulama. Bu dosya 15 Kasım
2026'da, diğer dağıtımların kurtarma/anlık görüntü yaklaşımları araştırılıp
CarotOS'un kendi kısıtlarına (kurulum dosya sistemi sabitlenmemiş, "az ve öz"
felsefesi, tek geliştirici) göre bir model seçildikten sonra yazıldı.

## 1. Araştırılan modeller ve neden seçilmedi/seçildi

| Dağıtım / araç | Yöntem | CarotOS için sonuç |
|---|---|---|
| **Kali Unkaputtbar**, **Parrot (Snapper + Btrfs Assistant)** | Btrfs anlık görüntüsü, GRUB'dan önyükleme | Kurulumda **btrfs zorunlu**. CarotOS kurucusu (debian-installer, standart) dosya sistemini sabitlemiyor — çoğu kullanıcı ext4 kurar. Bunu değiştirmek partisyonlama akışını kökten değiştirir, riskli ve kullanıcıya görünen davranışı değiştirir (CLAUDE.md kural: önce sor). |
| **openSUSE/Fedora Snapper**, **Garuda Snapshot Assistant** | Aynı (btrfs + GRUB entegrasyonu) | Aynı engel. Ayrıca GRUB'dan anlık görüntüye önyükleme forum raporlarına göre kırılgan (Garuda, EndeavourOS kullanıcı raporları). |
| **Linux Mint Timeshift (rsync kipi)** | rsync + sabit bağ (hard link) ile artımlı tam kopya; herhangi bir dosya sisteminde çalışır | **Seçildi.** CarotOS'un varsayılan ext4 kurulumunda değişiklik gerektirmez, kanıtlanmış (Mint'in varsayılanı), anlaşılması basit. |
| **Windows Sistem Geri Yükleme** | Kişisel dosyalara dokunmadan sistem durumunu (kayıt defteri, sürücüler, programlar) geri alır | Kapsam fikri buradan alındı: **kişisel dosyalara dokunma**, yalnızca "sistem neden bozuldu" sorusuna cevap ver. Windows'tan gelen kullanıcılar için tanıdık bir zihin modeli (Karşılama'daki "Windows'un yanına kurulum" sayfasıyla aynı kitle). |
| **apt/dpkg pre-invoke kancası (Timeshift-autosnap, Snapper'ın apt entegrasyonu)** | Güncellemeden hemen önce otomatik nokta | Aynen uygulandı: `DPkg::Pre-Invoke`. |

Kaynaklar (15 Kasım 2026 araştırması): Linux Mint Timeshift README/wiki;
openSUSE/SUSE Snapper belgeleri; Parrot OS Btrfs Assistant + Snapper kurulum
kılavuzu; Kali "Unkaputtbar" duyurusu (helpnetsecurity, TechRepublic); Garuda
ve EndeavourOS forumlarında GRUB'dan anlık görüntüye önyükleme sorunları;
Ubuntu/Proxmox apt hook örnekleri (`DPkg::Pre-Invoke`).

## 2. v1 kapsamı (bilerek dar)

- **Kapsanan:** `/etc`, `/root`, kurulu paket listesi (`dpkg --get-selections`).
- **Kapsanmayan (kişisel dosyalar):** `/home` içeriği, tarayıcı/masaüstü
  ayarları. Bu bir yedekleme aracı DEĞİLDİR; "sistemi son iyi duruma döndür"
  aracıdır. Çoğu "sistemi bozdum" durumu (kötü bir güncelleme, yanlış bir
  `/etc` dosyası) bu ikisiyle çözülür.
- **Depolama:** `/var/lib/carotos-kurtarma/noktalar/<ISO-zaman-id>/`, aynı
  diskte (Timeshift'in kendi varsayılanıyla aynı karar). Harici diske taşıma
  kullanıcıya bırakılır (v2 adayı).
- **Saklama:** sayı tabanlı (varsayılan 5, ayarlanabilir); Timeshift'in
  günlük/haftalık/aylık katmanlı sistemi yerine basit "en yeni N" — az ve öz.
- **Yetki modeli:** listeleme/ayar okuma pkexec GEREKTİRMEZ (dosyalar dünya
  okunabilir izinle yazılır); oluşturma/geri yükleme/silme/ayar yazma
  `carotos-kurtarma-yonet` yardımcısına pkexec ile gider (CarotPot'un
  `carotpot-yonet` deseniyle birebir aynı: sabit komutlar, `ortak/yetkili.py`
  ile yol çözümü, kabuk yok).
- **Otomatik nokta:** `/etc/apt/apt.conf.d/50carotos-kurtarma`, her
  `apt install/upgrade`'den önce. Varsayılan AÇIK (Kurtarma > Ayarlar'dan
  kapatılabilir), apt işlemini asla durdurmaz (`|| true`), art arda
  tetiklenmeyi önlemek için en az 10 dakika aralık ister.
- **Geri yükleme çalışırken yapılır** (Timeshift'in dokümante ettiği gibi):
  canlı USB gerekmez; `/etc` ve `/root` dosyaları sistem çalışırken rsync ile
  üzerine yazılır. Yeniden başlatma önerilir, zorunlu değildir.

## 3. v2 adayları (bu oturumda YAPILMADI)

- Kullanıcı ev dizini alt kümesi (`.config`, `.ssh`, `.gnupg`, kabuk
  ayarları) — izin/sahiplik ve "hangi dosyalar güvenle dahil edilir"
  sorusu daha dikkat ister, ayrı bir onay gerektirir.
- Harici diske/USB'ye nokta yazma.
- Sistem Sağlığı'na "son kurtarma noktası ne zaman alındı" denetimi —
  **bilerek eklenmedi**: 1.4 duyuruları zaten "24 denetim" sayısını
  kullanıcıya açıkladı, bu sayıyı onaysız artırmamak için.
- `tools/apt/paket-yap.sh`'a Kurtarma'yı eklemek (1.4 yaması planındaki
  "apt köklü çözüm" işiyle birlikte ele alınmalı).
- Gerçek bir uygulama simgesi (bu oturumda **YOK**: mevcut CarotOS ikonları
  el yapımı/ayrı bir araçla üretiliyor (bkz. BUILD.md ekran görüntüsü
  notları); burada taklit etmek tutarsız/düşük kaliteli bir simge
  demek olurdu. `Icon=carotos-kurtarma` şimdilik genel simgeye düşer.
- Canlı USB'den (sistem açılmıyorken) kurtarma: motor fonksiyonları buna
  hazır (`PARCALAR`'daki hedef yollar parametrik hale getirilebilir) ama
  arayüz/akış bu oturumda eklenmedi. Bkz. aşağıdaki "Canlı ortam" notu.

## 4. Test kapsamı

- `tests/test_kurtarma_motor.py` — 46 test, GTK'siz, `subprocess` sahte
  (saf mantık: id/etiket doğrulama, rsync komut üretimi, `--link-dest`
  zinciri, saklama sınırı, disk doluluğu reddi, paket kümesi farkı, yarım
  kalan noktanın temizlenmesi).
- `tests/test_kurtarma_yonet.py` — 18 test, kök yardımcının komut
  dağıtımını ve doğrulamasını sınar (gerçek ayrıcalıklı komut ÇALIŞTIRMAZ).
- Yapılmadı (VM gerektirir): gerçek rsync ile uçtan uca oluştur/geri yükle,
  ISO derleme + hook doğrulaması, apt kancasının gerçek bir `apt install`
  sırasında tetiklenmesi.

## 5. Canlı ortam notu (ayrı araştırma, reddit geri bildirimine karşılık)

Topluluktan gelen "canlı ortamda kurulum öncesi test/kurulum seçeneği daha
görünür olsun" isteğine bakıldı (15 Kasım 2026). Bulgular:

- CarotOS ISO'su `--debian-installer live` ile üretiliyor (BUILD.md). Bu,
  Debian Live'ın resmi "canlı + kurucu birlikte" modudur; **Calamares
  DEĞİLDİR**. "Kur" seçeneği önyükleme menüsünde **ayrı bir giriş** olarak
  durur, canlı masaüstünden tek tıkla açılan bir simge değildir.
- Debian'ın kendi Calamares tabanlı canlı imajlarında (GNOME/KDE/Xfce
  varyantları) `calamares-settings-debian` paketi masaüstüne bir "Install"
  simgesi koyuyor (`add-calamares-desktop-icon` betiği,
  `/etc/xdg/autostart/calamares-desktop-icon.desktop` ile tetikleniyor).
  CarotOS Calamares KULLANMIYOR, bu yüzden bu paket/yöntem doğrudan
  uygulanamaz.
- debian-installer'ı canlı oturumdan (yeniden başlatmadan) açmanın güvenilir
  bir yolu şu an doğrulanmadı: GRUB'un varsayılan girişini değiştirip
  (`grub-reboot` + `GRUB_DEFAULT=saved`) yeniden başlatmak teorik olarak
  mümkün, ama giriş adı/ID'si yalnızca **gerçek bir ISO derlemesinde**
  üretilen `grub.cfg`'den okunup doğrulanabilir; bu oturumda ISO
  derlenmediği için denenmedi.
- **Önerilen sıradaki adım (yapılmadı):** VM'de bir ISO derleyip
  `boot/grub/grub.cfg`'deki kurulum girişinin tam `menuentry` adını/ID'sini
  bulmak, sonra masaüstüne "CarotOS'u Kur" adlı, `pkexec grub-reboot
  <id> && systemctl reboot` çalıştıran bir başlatıcı eklemek — bu adı kodda
  SABİT YAZMAK yerine `grub.cfg`'den `grep` ile dinamik okumak (yerel ad
  değişirse kırılmasın diye). Bu, bir ISO/önyükleme davranışı değişikliği
  olduğu için CLAUDE.md kuralına göre uygulamadan önce onay istenecek.
