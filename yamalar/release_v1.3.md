## CarotOS 1.3 "Eggshell"

Carotene, CarotPot, Filenor, CarotOS Former ve CarotOS GSD bu sürümle geliyor. Sistem Sağlığı ve USB Denetimi genişletildi, Mağaza kataloğu 153 uygulamaya çıktı.

### İndirme

- **Dosya:** `carotos-1.3-amd64.iso`
- **Boyut:** 2.528.411.648 bayt (2,53 GB)
- **İndirme bağlantısı:** https://download.carotos.org/carotos-1.3-amd64.iso
- **sha256:** `b25b128bb901aec00343fcf79230e9b5f18b49d14cfafade25542d7d8dc3236e`
- **sha256 dosyası:** https://download.carotos.org/carotos-1.3-amd64.iso.sha256

Doğrulama:

```bash
sha256sum -c carotos-1.3-amd64.iso.sha256
```

ISO, GitHub'ın dosya boyutu sınırını aştığı için bu sayfaya eklenmedi; yukarıdaki bağlantıdan indirilir.

### Eklenenler

- **Carotene:** ClamAV ile hızlı, ana klasör ve özel tarama; karantina, virüs tanımı güncelleme ve tarama geçmişi. Arka planda hizmet çalıştırmaz.
- **CarotPot:** yerel ağ için sahte SSH, Telnet, web paneli, FTP, VNC, RDP, MySQL ve Redis tuzakları; saldırgan profili, kanarya dosyaları ve onaylı engelleme. Sistem açılışında kendiliğinden başlamaz.
- **Filenor:** görsel, ses, video, belge, tablo, sunum ve yazı tipi dönüştürme; PDF birleştirme, bölme, döndürme, küçültme, kilitleme ve OCR.
- **CarotOS Former:** güvenlik araçlarını, CarotPot ve Carotene'i animasyonlarla anlatan iki dilli rehber.
- **CarotOS GSD:** Linux, ağ, siber güvenlik, kriptografi ve bilgisayar bilimi alanlarında 161 terimlik, aranabilir ve iki dilli sözlük.
- **Sistem Sağlığı:** Koruma katmanları kategorisi (AppArmor ve profilleri, virüs tanımlarının güncelliği), `debsums` ve `rkhunter` ile ayrıntılı taramalar. Denetim sayısı 20'den 23'e çıktı.
- **USB Denetimi:** yalnızca kullanıcı başlattığında çalışan ayrıntılı ClamAV taraması. Bulunan dosyalara dokunulmaz, yalnızca raporlanır.
- **Karşılama Sihirbazı** 21 sayfaya çıktı.

### Değişenler

- CarotOS Mağaza kataloğu 51 uygulamadan 153 uygulamaya, yedi kategoriden on kategoriye çıktı.

Tüm değişiklikler: [CHANGELOG.md](https://github.com/MiracLight/CarotOS/blob/main/CHANGELOG.md)
