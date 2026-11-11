# CarotOS kendi apt deposu: plan ve anahtar süreci

Amaç: `carotos-*` uygulamaları ve ileride Caroise, ISO'yu yeniden indirmeden **imzalı** bir apt deposundan güncellensin.
Adres: **`apt.carotos.org`** (Cloudflare R2, ayrı kova `carotos-apt`). Araç: `reprepro`. İlk sürümde yalnızca `stable` kanalı.
Kaynak paketleri de yayınlanır (GPL).

## 1. Güvenlik modeli (neden bu kadar titiz)

apt root olarak çalışır: **depo ele geçerse bütün kullanıcılarda root kodu çalışır.** Bu yüzden:

- İmza anahtarı **çevrimdışı** tutulur; günlük kullandığın Windows bilgisayarına **hiç girmez**.
- Anahtar **canlı CarotOS oturumunda** (RAM'de, kapanınca silinir) üretilir ve imzalama orada yapılır.
- Claude özel anahtarı **görmez ve üretmez**. Bana yalnızca **genel anahtar ve parmak izi** gelir.
- Otomatik sistem (CI) imza yapmaz: ben imzasız depo ağacını üretirim, **imzayı sen yaparsın**, yüklemeyi sen yaparsın.
- `Valid-Until` (60 gün) ve düzenli yeniden imzalama (dondurma saldırısına karşı). Not: Debian trixie `reprepro` 5.3 `Acquire-By-Hash` üretmez; `tools/apt/by_hash.py` imzadan önce `by-hash/SHA256` dizinlerini ve Release alanını ekler (apt ile doğrulandı). Ek olarak `dists/*` önbellek atlama ve `dists`i en son yükleme.
- Ana (sertifika) anahtar ile **imzalama alt anahtarı** ayrıdır; alt anahtarın 2 yıllık son kullanma tarihi olur.
- Depo için **ayrı ve yalnızca o kovaya yetkili** R2 token'ı kullanılır (mevcut `downloads` token'ı bu iş için kullanılmaz).
- Gizlilik notu (dürüstçe yazılır): `apt update` istekleri Cloudflare günlüğüne düşer; CarotOS telemetri toplamaz.

## 2. Senin yapacakların

### 2.1 Cloudflare (yaklaşık 20 dakika)

1. R2'de **yeni kova**: `carotos-apt` (konum otomatik).
2. Kovada **Settings → Custom Domains → Add**: `apt.carotos.org` (carotos.org zaten Cloudflare DNS'te; bağlantı kendiliğinden kurulur).
3. **Cache Rules:** `apt.carotos.org/dists/*` için **önbelleği atla** (ya da kenar TTL'i 60 sn). Aksi halde "Hash Sum mismatch"
   hatası çıkar. `pool/*` normal önbelleğe alınabilir.
4. R2 → **Manage API tokens → Create API token:** izin **Object Read & Write**, kapsam **yalnızca `carotos-apt` kovası**.
   `Access Key ID` ve `Secret`'ı **bana yazma**; yalnızca kendi rclone ayarına koy (aşağıda).
5. `rclone config` ile yeni uzak: ad **`r2apt`** (türü S3 / Cloudflare, uç nokta kendi hesap kimliğinle). `r2:` uzağından ayrı.
   Token'da liste izni olmayabilir (403 normaldir); yükleme çalışır.

### 2.2 İmza anahtarı (yaklaşık 1 saat, bir kez)

**Gerekenler:** CarotOS canlı USB'si (ya da derlenmiş ISO ile açılmış bir sanal makine), **iki** boş USB bellek (şifreli
yedek için), kâğıt ve kalem. Donanım anahtarı (YubiKey 5 serisi, OpenPGP destekli; ucuz "Security Key" serisi OpenPGP'yi
desteklemez) **sonra** alınabilir (aşama 2).

> **DİKKAT:** aşağıdaki `luksFormat` komutu verdiğin aygıttaki **her şeyi siler**. `lsblk` çıktısında USB belleğin adını
> (örn. `sdb`) boyutuyla doğrula; ana diskini (`sda`) yazma.

1. Canlı CarotOS'u aç (kalıcılık yok, her şey RAM'de). Bir terminal aç.
2. Şifreli USB hazırla (USB'yi tak, aygıtı bul):
   ```bash
   lsblk
   ```
   Aygıt `/dev/sdb` ise (kendi aygıtına göre değiştir):
   ```bash
   sudo parted -s /dev/sdb mklabel gpt mkpart anahtar ext4 1MiB 100%
   sudo cryptsetup luksFormat /dev/sdb1
   sudo cryptsetup open /dev/sdb1 anahtar
   sudo mkfs.ext4 -L CAROT-ANAHTAR /dev/mapper/anahtar
   sudo mkdir -p /mnt/anahtar && sudo mount /dev/mapper/anahtar /mnt/anahtar && sudo chown "$USER" /mnt/anahtar
   ```
   `luksFormat` sırasında **uzun, benzersiz bir parola** seç (bir parola yöneticisine değil, aklında/kâğıtta).
3. Anahtarları üret (özel anahtarlar şifreli USB'deki `gnupg` klasöründe kalır):
   ```bash
   export GNUPGHOME=/mnt/anahtar/gnupg
   mkdir -m 700 "$GNUPGHOME"
   gpg --quick-generate-key "CarotOS Archive <archive@carotos.org>" ed25519 cert 0
   FPR=$(gpg --list-keys --with-colons | awk -F: '/^fpr/ {print $10; exit}')
   gpg --quick-add-key "$FPR" ed25519 sign 2y
   gpg --list-keys --with-subkey-fingerprints
   ```
   Parola sorulduğunda **güçlü bir parola** ver (ana anahtar parolası). Ana anahtar süresiz (`0`), imzalama alt anahtarı 2 yıl.
4. **İptal sertifikası** üret (anahtar kaybolursa ya da çalınırsa ilan etmek için tek yol):
   ```bash
   gpg --output /mnt/anahtar/iptal-sertifikasi.asc --gen-revoke "$FPR"
   ```
   Sebep sorarsa `0` (belirtilmedi). Çıktıyı **kâğıda yazdır ya da ayrı bir USB'ye** de kopyala; ana anahtardan ayrı saklanmalı.
5. **Genel anahtarı ve parmak izini dışa aktar** (yalnızca bunlar bana gelecek):
   ```bash
   mkdir -p /tmp/genel
   gpg --armor --export "$FPR" > /tmp/genel/carotos-archive-keyring.asc
   gpg --export "$FPR" > /tmp/genel/carotos-archive-keyring.gpg
   gpg --fingerprint "$FPR" > /tmp/genel/parmak-izi.txt
   cat /tmp/genel/parmak-izi.txt
   ```
   Bu üç dosyayı (**yalnızca bunları**) `/media/sf_Share` ya da başka bir yolla Windows tarafındaki `Share` klasörüne
   kopyala. **`gnupg` klasörünü, `.asc` iptal dosyasını ya da özel anahtarı Share'e KOYMA.**
6. **İkinci yedek:** çalışan şifreli USB'yi kapat, ikinci USB'yi aynı yöntemle hazırla ve `gnupg` klasörünü ona kopyala:
   ```bash
   cp -a /mnt/anahtar/gnupg /mnt/yedek/ && sync
   ```
   İki USB'yi **farklı yerlerde** sakla. Parolayı ayrıca (kâğıtta) sakla.
7. Takvime 2 yıl sonrası için "alt anahtar süresi doluyor" hatırlatıcısı koy.
8. Parmak izini (`parmak-izi.txt`) sonra birden çok bağımsız yerde yayınlarız: site, GitHub, README, DistroWatch.

### 2.3 Bana vereceğin şeyler

- `carotos-archive-keyring.gpg`, `carotos-archive-keyring.asc`, `parmak-izi.txt` (Share'e).
- Cloudflare tarafı bittiğinde "kova ve alan adı hazır" demen yeter. rclone ayarını sen yaparsın.

## 3. Benim yapacaklarım (anahtar gelince)

**Aşama 1 — boş ama doğru depo:**
- `tools/apt/`: `reprepro` yapılandırması (`conf/distributions`: Origin/Label CarotOS, Codename `trixie`, bileşen `main`,
  `Valid-Until` (`ValidFor: 60d`); imza **yok**, imzayı sen yaparsın), depo üretim ve imzalama betikleri.
- `carotos-archive-keyring` paketi: `/usr/share/keyrings/carotos-archive-keyring.gpg` ve
  `/etc/apt/sources.list.d/carotos.sources` (deb822, `Signed-By` ile; genel `trusted.gpg.d` KULLANILMAZ). Boş depo bile
  `apt update`'i bozmamalı; bunu WSL'de kök yetkisiz, ayrı dizinlerle test ederim.
- ISO'ya keyring + sources dosyası girer (final derlemeden önce).

**Aşama 2 — ilk paket:** en küçük ve riski az uygulama (GSD ya da Former) ile hattı kanıtlarım: `lintian`, temiz ortamda
kur / yükselt / kaldır testleri. Paketleme dersleri: `/etc/default/grub` gibi conffile'lara dokunma (`*.d/` kullan);
CarotPot servisi etkinleştirilmeden/başlatılmadan kurulur (`--no-enable --no-start`); `postinst` yerine trigger; dosyalar
`root:root`; kullanıcı verisi pakete girmez.

**Aşama 3 — kalan 11 uygulama** (Poligon, CarotPot en zoru), eski kurulumlar için `carotos-migrate` (eski sahipsiz `/opt/carotos`
dosyalarını yedekleyip kaldırır; dev VM 1.0 ilk geçiş testi olur). **Aşama 4:** Caroise.

## 4. Yayın akışı (her depo güncellemesinde, senin onayınla)

1. Ben `.deb` paketlerini ve imzasız depo ağacını üretirim.
2. Sen canlı oturumda `Release` dosyasını imzalarsın:
   ```bash
   gpg --default-key "$FPR" --armor --detach-sign -o Release.gpg Release
   gpg --default-key "$FPR" --clearsign -o InRelease Release
   ```
3. Sen `rclone sync` ile `r2apt:carotos-apt` kovasına yüklersin (`dists/` önce değil **en son**: önce `pool/`, sonra `dists/`).
4. `apt update` ile test (temiz bir VM'de), sonra duyuru.

## 5. Açık kararlar

- Kanal: şimdilik yalnızca `stable` (öneri). `testing` ileride.
- Donanım anahtarı: ne zaman alınacak (aşama 2, imzalama alt anahtarı karta taşınır; ana anahtar çevrimdışı kalır).
- Tek bakımcı riski: ana anahtarın yedeği ve "ben yokken" talimatı bu belgeye yazılır (anahtar töreni bittikten sonra).

## 6. ISO imzası (her ISO yayınında, senin onayınla)

Aynı anahtar ISO özetlerini de imzalar (apt deposuyla tek anahtar altyapısı).

1. ISO'yu derle, VM'de dene, bir klasöre koy (yalnız yayınlanacak `.iso` dosyaları).
2. Canlı oturumda, şifreli USB bağlıyken:
   ```bash
   export GNUPGHOME=/mnt/anahtar/gnupg
   bash tools/iso/imzala-iso.sh <ISO-klasörü>
   ```
   Betik `SHA256SUMS` ve `SHA256SUMS.sign` üretir, sonra imzayı yalnız genel anahtarla doğrular
   (`ISO-IMZA-TAMAM`). ISO'ya dokunmaz, yükleme yapmaz.
3. ISO ile birlikte `SHA256SUMS` ve `SHA256SUMS.sign` download.carotos.org'a yüklenir; site ve GitHub notunda
   parmak izi (`30E6 D4B0 C05E F002 1309  A1A0 9F93 5CD4 D5D0 A1F5`) ve doğrulama komutları yer alır.
4. Kullanıcı tarafı: Karşılama > Koruma ve savunma > "İndirdiğini doğrula" ve Former "İndirdiğini doğrula".
   Test: `tests/test_iso_imza.py` (parmak izi anahtar dosyasından hesaplanır; imzalama uçtan uca denenir).
