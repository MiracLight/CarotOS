# Former + GSD denetimi (ad: former-gsd; önekler R ve D)

Tarih: 13 Kasım 2026. Dal: 1.4 (temiz, depoya dokunulmadı). Kanıt türleri: **Denendi** = WSL Debian (Python 3.13, xvfb, GTK3) üzerinde çalıştırılıp görüldü; **Okundu** = koddan çıkarıldı.

Özet: Yüksek 0, Orta 3 (R-01, R-02, D-01), Düşük 9 (R-03 … R-09, D-02, D-03). Güvenlik açısından kritik bir bulgu yok; ağ dinleyen kod, kabuk enjeksiyonu, regex, işaretleme kaçışı sorunu yok. Asıl hatalar: iki "uygulamayı aç" düğmesi ölü, GSD aramasında Türkçe "I/ı" katlama hatası, birkaç içerik hatası.

---

## 1. Kapsam

**Satır satır okunanlar (motor ve arayüz):** `former/carotos-former.py`, `former_zaman.py`, `former_cizim.py`, `former_sahneler.py`, `konular/__init__.py`, `konular/_panel.py`; `gsd/carotos-gsd.py`, `gsd/terimler/__init__.py`; `config/hooks/live/9994-carotos-former.hook.chroot`, `9995-carotos-gsd.hook.chroot`.

**Satır satır okunan içerik:** Former'in 20 konusunun tamamı (giris, panel, nmap, tcpdump, tshark, aircrack_ng, nikto, sqlmap, john, hydra, ufw, fail2ban, carotpot, carotene, acikla, etik, disk, dogrula, ctf, savunma); GSD'nin 197 teriminin tamamının Türkçe metni (guvenlik 48, kriptografi 24, ag 32, linux 34, algoritma 25, genel 34) ve guvenlik + kriptografi kategorilerinin (72 terim) İngilizce metni.

**Betikle taranan:** Former 20 konu ve GSD 197 terim için kimlik/grup/anahtar/ikon/tr-en/yer tutucu/sayı/sayfa-bayrak/balon hedefi görünürlüğü denetimleri; 6 dilde (tr, en, de, ja, zh, ru) her konunun zaman çizelgesi 41 ms adımla baştan sona (`durum(t)` istisnası yok); 9 dilde sahne metni ölçümü (Pango); 7 çeviri dosyasında (de, es, fr, ja, pt, ru, zh) 1338 benzersiz İngilizce metnin varlığı ve yer tutucu uyumu; `tests/test_former.py` (29 test) ve `tests/test_gsd.py` (19 test) çalıştırıldı, ikisi de geçti (testlerin kendisi okunmadı, yalnız çalıştırıldı).

**Çalışan arayüz denemeleri (xvfb):** Former penceresi: 300 hızlı konu geçişi, hız düğmesi, dil/tema değişimi, `ac()` davranışı, pencere kapanışı, 4 sahne PNG'ye çizilip görsel incelendi. GSD penceresi: 25 arama sorgusu, bozuk/uzun sorgular, ilgili terime git, dil değişimi.

**Okunmayanlar:** `ikonlar.b64` içerikleri (yalnız biçim/satır sonu denetlendi), `ortak/tema.py` ve `ortak/dil.py` (bu uygulamaların kullandığı kısımlar dışında; başka denetimin kapsamı), `tests/test_former.py` ve `tests/test_gsd.py` kaynakları, GSD'nin algoritma/genel/ag/linux kategorilerinin İngilizce metni (Türkçesi okundu; sayısal ve yer tutucu denetimi betikle tüm terimlerde yapıldı), WSL'de kurulu olmayan araçların (nmap, nikto, sqlmap, john, hydra, ufw, fail2ban, aircrack-ng, tshark, tcpdump) gerçek çıktısı.

---

## 2. Tehdit modeli

Bu iki uygulama ağ dinlemez, root olarak çalışmaz, kimlik doğrulaması yoktur. Yüzey:
- **Kullanıcı girdisi:** yalnızca GSD arama kutusu (düz alt-dize eşleşmesi; regex yok) ve komut satırı bayrakları `--konu`, `--terim` (sözlükte aranır, başka yere gitmez).
- **Başlatılan komutlar:** Former'de 7 "uygulamayı aç" düğmesi; komutlar kod içinde sabit listeler (`["python3", "/opt/carotos/.../x.py"]`), kabuk yok, kullanıcı girdisi karışmaz, root istemez (yetki yükseltmeyi açılan uygulama kendisi pkexec ile yapar).
- **İçerik:** konu/terim metinleri depodan gelir (tedarik zinciri dışında saldırgan kontrolünde değil). Asıl risk, yanlış ya da tehlikeli bilgi öğretmesi ve ölü/yanıltıcı düğmeler.
- **Yerel durum:** `~/.config/carotos-former/settings.json`, `~/.config/carotos-gsd/settings.json` (dil, tema); bozuk dosya `except Exception` ile varsayılana düşer.
- Aynı makinedeki başka kullanıcı ya da ağdaki yabancı için bu uygulamalarda saldırı yüzeyi bulunmadı.

---

## 3. Bulgular (önem sırasıyla)

### Orta

#### R-01 — Carotene ve CarotPot konularındaki "uygulamayı aç" düğmeleri var olmayan betiğe gidiyor; hata gizleniyor
- **Konum:** `former/konular/carotene.py:6,121`; `former/konular/carotpot.py:6,126`; `former/carotos-former.py:111-116,272-274`.
- **Senaryo:** Carotene konusunda "Carotene'ı aç" düğmesi `python3 /opt/carotos/carotene/carotos-carotene.py` çalıştırır; gerçek dosya `carotene.py` (`.desktop` `Exec=/opt/carotos/carotene/carotene.py`, hook 9991 `chmod 755 .../carotene.py`). CarotPot için `.../carotos-carotpot.py` yazıyor; gerçek dosya `carotpot-arayuz.py` (`.desktop` ve hook 9992). `ac()` yalnızca `Popen` istisnasına bakar; `python3` var olduğu için `Popen` başarılı döner, python "can't open file" yazıp çıkar, kullanıcı hiçbir şey görmez. Yani `uygulama_yok` ("… kurulu değil") iletisi bu kalıpta hiç çıkamaz; iki düğme sessizce ölü.
- **Kanıt:** Okundu (yol uyuşmazlığı, depo ağacı + `.desktop` + hook) ve Denendi (`ac(["python3","/opt/carotos/olmayan/yok.py"])` → `True`, stderr'e "can't open file"; olmayan ikili için `False`).
- **Düzeltme:** (1) Yolları düzelt: `carotene.py`, `carotpot-arayuz.py`. (2) `ac()` içinde betik yolunu `os.path.isfile` ile denetle, yoksa `False` dön (bildirim çıksın); `start_new_session=True` ve `stdin/stdout=DEVNULL` ekle (çocuk Former'e bağlı kalmasın, zombi bırakmasın). (3) Test ekle: her konunun `uygulama.komut[-1]` yolunun depo ağacında (`config/includes.chroot` altında) var olduğunu doğrulayan test. Düğmeler çalışır hale gelir; bu bir hata düzeltmesidir, istenmeyen bir davranış değişikliği değil.

#### R-02 — Carotene konusunun son balonu görünmeyen bir öğeye işaret ediyor ve var olmayan "Ayarlar sayfası"nı anlatıyor
- **Konum:** `former/konular/carotene.py:56-64`; `former/former_sahneler.py:301` (`t_tanim` yalnızca `tarama` sayfasında görünür); `former/former_cizim.py:308-318` (balon çizimi hedefin görünürlüğüne bakmaz).
- **Senaryo:** Animasyon `sonuc` sayfasında biter; sonra `balon("t_tanim", …)` gelir. `t_tanim` rozeti `tarama` sayfasındadır, o anda ekranda yoktur. Balon ve nabız halkası boş bir yere çizilir (PNG ile görüldü: sağ üstte ok boşluğu gösteriyor, altında hiçbir şey yok). Metin "Ayarlar sayfasındaki 'Tanımları güncelle'" der; Carotene'de bu kenar menüsü "Virüs tanımları" bölümüdür (`carotene.py:68,229,246`) ve sahnede de öyle (`ct:tanim`).
- **Kanıt:** Denendi (betik: `BALON HEDEFI GORUNMUYOR carotene t_tanim`; görsel çıktı); tek konu etkileniyor (20 konunun hepsi tarandı).
- **Düzeltme:** Balondan önce `tikla("ct:tanim", sayfa="tanim")`, hedefi `d_guncelle` yap, metni "Virüs tanımları bölümündeki 'Tanımları güncelle'" olarak düzelt (7 dil çevirisiyle). Kalıcı çözüm: `fz.dogrula` içine "balon anında hedef görünür mü" denetimi (benim betiğimdeki `gorunur()` mantığı) ve `_balon`'da görünür olmayan hedef için balonu atla. Kullanıcıya görünen metin/animasyon değişir.

#### D-01 — GSD arama kutusu, "I/ı/İ" katlaması yüzünden çok yaygın sorguları kaçırıyor
- **Konum:** `gsd/carotos-gsd.py:83-87` (`_TR_KUCUK = str.maketrans("İIĞÜŞÖÇ", "iığüşöç")`), `:195-206` (dizin), `:393-395` (sorgu), `:97-100` (sıralama anahtarı de aynı fonksiyonu kullanır).
- **Senaryo:** `I` her zaman `ı` (noktasız) yapılıyor, hem dizinde hem sorguda; ama kullanıcı küçük `i` yazar, metinde büyük `I` vardır (İngilizce kısaltmalar, "IP", "IDS", "INFO", "Injection", "ISO"…). Sonuç: dizindeki "IP Adresi" → "ıp adresı"; "ip adresi" yazınca eşleşmez.
- **Kanıt:** Denendi (gerçek pencerede, arama kutusu). Türkçe başlığı olduğu gibi yazınca 0 kayıp; küçük harfle yazınca başlığın tamamını arayanlarda 31 başlık bulunamıyor.

| Sorgu | Sonuç sayısı |
|---|---|
| `IP Adresi` | 13 |
| `ip adresi` | **0** |
| `IP address` | 13 |
| `ip address` | **0** |
| `INFO` | **0** (`info` → 5) |
| `ISTISMAR` | **0** (`İstismar`/`istismar` → 3) |
| `IKILI` | **0** (`ikili` → 5) |
| `SQL Injection` | 1; `sql injection` → 3 (farklı sonuç kümesi) |
| `osi` | 12 (gürültü), `OSI` → 1 |

  Ayrıca "ip" gibi kısa sorgular gürültülü (ör. "ip" 66 terim: "script", "tip" içinde geçiyor) ve `ids` yalnız kimlik alanı yüzünden bulunuyor. Sıralama anahtarı da aynı katlamayı kullandığı için İngilizce başlıklarda "I" ile başlayanlar `ı` konumunda sıralanır (İngilizce arayüzde "ICMP, IDS" i-harflerinden önce gelir; Türkçe alfabede doğru, İngilizcede şaşırtıcı).
- **Düzeltme:** Hem dizine hem sorguya aynı katlamayı uygula: `s.translate(str.maketrans({"İ":"i","I":"i","ı":"i","Ğ":"g","ğ":"g",…})).lower()` ya da yalnız `İ,I,ı → i` ve isteğe bağlı ASCII katlama (ş→s, ç→c, ö→o, ü→u, ğ→g) ki klavyede Türkçe harf olmayan kullanıcı da bulsun. Sıralama anahtarı için ayrı (Türkçe alfabeli) fonksiyon kalsın, ama dil `en` iken düz `casefold` kullanılsın. Test: "ip adresi", "INFO", "ISTISMAR", "ikili", "İki Faktörlü" (hepsi ≥1 sonuç). Kullanıcıya görünen davranışı değiştirir (daha çok sonuç döner), kural açısından olumlu.

### Düşük

#### R-03 — Hız seçimi ve oynatma durumu sayfa yeniden kurulunca arayüzle uyuşmuyor; tema/dil değişince animasyon baştan başlıyor
- **Konum:** `former/carotos-former.py:147` (`self._hiz`), `:298` (`tema.secim_grubu(HIZLAR, "1", …)`), `:362-366`, `:277-318`, `:203-224`.
- **Senaryo:** 1.5× seçip başka konuya geçince arayüzde "1×" seçili görünür ama animasyon 1.5× oynar (`_hiz` sıfırlanmıyor, düğme grubu her seferinde "1" ile kuruluyor). Kullanıcı hızı sezer ama göstergeyi yanlış okur. Ayrıca tema ya da dil değişimi `_sayfayi_yeniden_kur` çağırdığı için animasyon `t=0`'dan, `_oynuyor=True` ile yeniden başlar (duraklatılmış anlatım kaybolur).
- **Kanıt:** Denendi (1.5× seçildi → konu değişti → `_hiz=1.5`, düğmeler `[0.75×:False, 1×:True, 1.5×:False]`; tema iki kez çevrilince `_t` sıfırlandı).
- **Düzeltme:** `secim_grubu` başlangıç değerini `str(self._hiz)` yap (ya da `_hiz`'ı sayfada 1.0'a sıfırla); dil/tema değişiminde `_t` ve `_oynuyor` korunsun. Küçük kullanıcı-görünür değişiklik.

#### R-04 — Animasyon zamanlayıcısı bitince/duraklayınca da 30 Hz çizdirir; ilerleme duvar saatiyle değil kare sayısıyla ölçülür
- **Konum:** `former/carotos-former.py:325-345`.
- **Senaryo:** `_adim` her 33 ms'de `queue_draw` ve `return True`; animasyon bitince ya da duraklatılınca da sürer (pencere küçültülmüş olsa bile). İlerleme `self._t += 33 * hiz` olduğundan ağır yükte (VM) animasyon gerçek saatten yavaş akar ve "1×" tutarsızlaşır.
- **Kanıt:** Okundu. Zamanlayıcı kaynağı konu değiştirmede tekilleşiyor (Denendi, 300 hızlı geçiş sonrası `_adim` çağrı hızı tek zamanlayıcıya uygun), kapatınca durur; yani kaçak zamanlayıcı yok.
- **Düzeltme:** Bitince/duraklayınca `return False` ile kaynağı bırak, oynat'ta yeniden kur; ilerlemeyi `GLib.get_monotonic_time()` farkıyla ölç. Davranış görünür değişmez (CPU/pil iyileşir).

#### R-05 — Komut blokları ve GSD örnekleri seçilemiyor, kopyalanamıyor
- **Konum:** `former/carotos-former.py:399-408` (`tema.etiket(icerik, "mono", sar=True, genislik=100)`, `sec` varsayılan `False`); `gsd/carotos-gsd.py:517`.
- **Senaryo:** Öğrenci "Terminalde karşılığı" bölümündeki `sudo tcpdump -i eth0 -c 50 port 443` komutunu fareyle seçip terminale yapıştıramaz; elle yazmak zorunda kalır (bir öğrenme aracı için gereksiz sürtünme; yazım hatası yapılırsa öğretici yanlış anlaşılır).
- **Kanıt:** Okundu.
- **Düzeltme:** `tema.etiket(..., sec=True)` (parametre zaten var). Görünür davranış: metin seçilebilir olur.

#### R-06 — "panel" konusu için tanımsız ikon (kenar çubuğunda dolu daire)
- **Konum:** `former/konular/panel.py:120` (`ikon="panel"`); `ortak/tema.py` `ikon_ciz` listesinde `panel` yok (docstring: bilinmeyen ad dolu daire).
- **Kanıt:** Denendi (`IKON YOK panel panel`; diğer 19 konunun ikonu ve sahne ikonları tanımlı).
- **Düzeltme:** `ikon="pano"` ya da `ikon="kalkan"`. Küçük görsel değişiklik.

#### R-07 — 23 Former cümlesi 7 çeviri dilinde İngilizce kalıyor (birleştirilerek üretilen anahtarlar)
- **Konum:** `former/former_sahneler.py:96-100` (`T("{}: {}".format(T_NE_ZAMAN["tr"], …), "{}: {}".format(T_NE_ZAMAN["en"], …))`); `former/konular/tcpdump.py:116-119`, `nikto.py:80-83`, `hydra.py:100-104` (`"…" + T_DENEME_UYARISI["en"]`).
- **Senaryo:** Çeviri dosyaları İngilizce metne göre anahtarlıdır. Parçalar ayrı ayrı çevrilmiş ama birleştirilmiş cümle ("When to use it: When you want …", "Example: …", ve üç "not" kutusu) anahtar olarak yoktur; de/es/fr/ja/pt/ru/zh'de Güvenlik Paneli sahnesindeki "Ne zaman kullanılır / Örnek" satırları ve üç not İngilizce görünür. Ayrıca `dogrula` parmak izi ve `ctf` `CAROT{...}` (çevrilmeyen, doğru) listede çıkıyor.
- **Kanıt:** Denendi (7 dosyada aynı 25 eksik: 23 gerçek cümle + 2 değişmeyen kimlik/sabit, toplam 1338 metin içinden). Yer tutucu (`{n}`, `{ad}`, `{eslesen}`) uyuşmazlığı yok.
- **Düzeltme:** Sahne metnini çalışma zamanında parçalardan kur (her parça `metin_al` ile kendi dilinde), ya da birleşik anahtarları `ceviri.py`/ajanla ekle (CLAUDE hafızasındaki "çeviri hemen" kuralı). Kullanıcıya görünen değişiklik: çeviri dillerinde tam çeviri.

#### R-08 — Sabit genişlikli sahne bileşenleri çevirilerde taşıyor / iki satıra kırılıyor
- **Konum:** `former/konular/savunma.py:13-16,27-28` (`s_ufw` w=84, `s_f2b` w=96, `s_bulgu_onem` w=100); `former/former_sahneler.py:177,246` (`p_hap` w=150, `s_engelli` w=100); kenar menüsü öğeleri (`h=22`, `genislik=150`).
- **Senaryo:** Savunma sahnesinde `ufw: desactivado` (es) 103 px'e karşılık 67 px alan; `fail2ban: activado` rozetle ufw rozetinin üstüne biner; ru `ЗАБЛОКИРОВАНО` 111 px'e karşılık 80 px; Türkçede bile `Önem: yüksek` 85 px / 83 px (2 px). Kenar menüsü öğeleri (Carotene "Virus definitions", CarotPot "Kanarya dosyalar", "Tarama geçmişi") etkin (kalın) halde iki satıra kırılıp `h=22` satırdan taşıyor; ja düğmeleri 38 px, 30 px düğmeye sığmıyor (Carotene `k_klasor`, `k_dosya`; ctf `c_ipucu`; disk `h_buton`; etik `e1_evet`).
- **Kanıt:** Denendi (Pango ölçümü, 9 dil; PNG ile doğrulanan düzen kısıtı, ölçüm kuru).
- **Düzeltme:** Rozet genişliğini metin ölçüsüyle belirle (`_olc`) ya da yeterince geniş ver; kenar menüsü öğesinde `ellipsize`/daha küçük punto. Ölçüm betiğini teste dönüştür. Görünür değişiklik yalnız taşma düzelmesi.

#### R-09 — Bir konu modülündeki hata bütün uygulamayı açılmaz kılıyor
- **Konum:** `former/konular/__init__.py:11-16`, `former/carotos-former.py:142`.
- **Senaryo:** `tumu()` 20 modülü sırayla içe aktarıp `konu()` çağırır; tek bir `KeyError`/söz dizimi hatası pencereyi hiç açmaz ve kullanıcı traceback'siz kaybolur (başlatıcıdan). Testler bunu yakalar; ama çalışma zamanında sağlamlık yok.
- **Kanıt:** Okundu.
- **Düzeltme:** Her konuyu `try/except` içinde yükle, bozuk konuyu atla ve stderr'e yaz. Davranış: normal durumda değişiklik yok.

#### D-02 — GSD'de dil değişince arama sonuçları yenilenmiyor
- **Konum:** `gsd/carotos-gsd.py:333-344` (`_dil_degisti` → `_arama_indeksi_kur`, `_metinleri_uygula`, ama `_listeyi_yenile()` yok); `_metinleri_uygula` yalnızca `invalidate_sort` çağırır.
- **Senaryo:** Dizin çeviri dilinin metnini de içerir (`:203-204`); sorgu aktifken (ör. "ssh") dil Almancaya çevrilince filtre yeniden değerlendirilmez: yeni dilde eşleşmesi olan satırlar görünmez, artık eşleşmeyenler kalır. Sayaç da bayat. (Denememde sayı aynı kaldı; fark ancak çevrilmiş terimde farklı eşleşme olursa görünür, bu yüzden düşük.)
- **Kanıt:** Okundu; Denendi kısmen (sayı değişmedi).
- **Düzeltme:** `_dil_degisti` sonunda `self._listeyi_yenile()`.

#### D-03 — Açıklama/örnek içeriği ve sayfa kaydırma konumu
- **Konum:** `gsd/carotos-gsd.py:448-453` (`_icerik_ayarla` kaydırma konumunu sıfırlamıyor; Former'in `Kabuk.icerik` sıfırlıyor: `tema.py` `self.kaydir.get_vadjustment().set_value(0)`); `:517` (seçilemeyen örnek).
- **Senaryo:** Uzun bir terimi aşağı kaydırıp başka terim seçince yeni sayfa aynı ofsetten başlayabilir (GTK yeni görünüm penceresine kaydırma ayarını aktarır). Test edilmedi; bu yüzden aşağıda "Şüpheli" olarak da var. R-05 ile aynı kök neden (örnek seçilemez) GSD için de geçerli.
- **Kanıt:** Okundu.
- **Düzeltme:** `self.sag_kaydir.get_vadjustment().set_value(0)`, `etiket(..., sec=True)`.

---

## 4. İçerik hataları tablosu

| # | Dosya:satır | Yanlış olan | Doğrusu / öneri | Önem |
|---|---|---|---|---|
| 1 | `former/konular/nikto.py:87` | "Kendi makinende basit bir web sunucusu başlat (örn. `python3 -m http.server`) ve onu tara." Bu sunucu port 8000'de açılır; nikto konusundaki hedef `http://localhost` (port 80) olduğu için "No web server found" çıkar. Ayrıca `http.server` varsayılan olarak 0.0.0.0'a bağlanır, çalışma klasörünü yerel ağa açar (güvenlik açısından tehlikeli öğüt). | `python3 -m http.server --bind 127.0.0.1` ve hedef `http://127.0.0.1:8000`. | Orta |
| 2 | `former/konular/sqlmap.py:49-54`, `:87-90` | "“does not seem to be injectable” … iyi haberdir: bulduğu bir açık yok demektir." / "çıkmazsa iyi bir işarettir". Varsayılan taramada (level 1, risk 1) bulunamamak güvende olmak demek değildir; yanlış güven öğretir. | "Bu aramada bir açık bulunamadı; bu, açık olmadığının kanıtı değildir (varsayılan düzey yalnızca temel teknikleri dener)." | Orta |
| 3 | `former/konular/fail2ban.py:20-30,44,75-85` | Panelin çalıştırdığı `fail2ban-client status` yalnızca ilk üç satırı (jail listesi) verir; "Status for the jail: sshd … Currently banned" bölümü `fail2ban-client status sshd` çıktısıdır. Ayrıca gerçek biçim `|- Filter … \`- Actions` ağacıdır, burada düz liste. Animasyon, panelde olmayan bir çıktıyı gösteriyor. | Çıktıyı iki parçaya böl (önce `status`, sonra `status sshd`) ve panelde yalnız `status` olduğunu söyle; gerçek ağaç biçimini kullan. | Orta |
| 4 | `former/konular/ctf.py:85-90` | Doğru bayraktan sonra "Doğru! +100 puan." ama puan "90" (ipucu cezası -10); sıralama "Sıran: 3" ve tabloda "3. Sen 90 · 4. Deniz 100". 100 > 90 olduğundan Deniz üçüncü, Sen dördüncü olmalı; üstelik tablo azalan puan sırasında değil. | "Doğru! +90 puan." ve "3. Deniz 100 · 4. Sen 90" (sıran 4, ya da puanı 110 yap). | Düşük |
| 5 | `former/konular/carotene.py:59-64` | "Ayarlar sayfasındaki “Tanımları güncelle”". Carotene'de bu bölüm "Virüs tanımları". | "Virüs tanımları bölümündeki “Tanımları güncelle”" (bkz. R-02). | Düşük |
| 6 | `former/konular/hydra.py:44-49` | "Panel sana uygun olanı seçtirir" (servis). Panelde servis serbest metin alanıdır (`carotos-security-panel.py` `("service", …, "text", "ssh", …)`); sahne de `alan`. | "Servis adını (ssh, ftp…) sen yazarsın; varsayılan ssh." | Düşük |
| 7 | `former/konular/dogrula.py:35-38` ve `:91-96` | Balon: "başka bir sistemde önce anahtarı carotos.org'dan alırsın"; uyarı: "ISO'yu indirdiğin sayfadan değil, ayrı ve güvendiğin bir kaynaktan aldığın anahtarla doğrula". İkisi birbiriyle çelişir (carotos.org ISO'yu da sunan site). | Parmak izini ayrı bir kanaldan (GitHub README, ikinci bir kaynak) karşılaştırmayı balonda da söyle. | Düşük |
| 8 | `former/konular/ufw.py:59-65` | "Varsayılan kural “gelen her şeyi reddet” olduğu için … dışarıdan kimse bir porta bağlanamaz." Bu yalnız ufw etkinse (`Status: active`) doğrudur; Debian'da ufw varsayılan olarak devre dışıdır. | "ufw açıkken varsayılan kural …". | Düşük |
| 9 | `former/konular/carotpot.py:28,37` ve `former_sahneler.py:204-209` | Sahnede 4 olay satırı var (`olay3`, `olay4`), animasyon yalnızca `o1`, `o2` bayraklarını açıyor; metin "taramalar, giriş denemeleri, web istekleri" diyor ama web isteği hiç görünmüyor. | `ayarla(_bayrak={"o3": True, "o4": True})` ekle ya da iki satırı sahneden çıkar. | Düşük |
| 10 | `former/carotos-former.py:94` | Düğme etiketi "{ad}'ı aç" Türkçe ek uyumsuz: "Sistem Sağlığı'ı aç", "Güvenlik Paneli'ı aç", "CarotPot'ı aç", "Carotene'ı aç", "Poligon (Öğrenci)'ı aç". | "Aç: {ad}" ya da ad başına ek tablosu. | Düşük |
| 11 | `gsd/terimler/linux.py:405` | Örnek `grep -i "error" /var/log/syslog`. CarotOS'ta (Debian 13) `rsyslog` kurulu değil (`config/package-lists/*` içinde yok), `/var/log/syslog` yok; komut "Böyle bir dosya yok" verir. | `journalctl -p err -b` (ya da `journalctl \| grep -i error`). | Orta |
| 12 | `gsd/terimler/genel.py:531` | Örnek `grep -E 'Failed password .* from [0-9.]+' /var/log/auth.log`; aynı nedenle `/var/log/auth.log` yok. | `journalctl -u ssh \| grep -E 'Failed password .* from [0-9.]+'`. (Aynı dosya adı `ctf_uretici`/`varyant_gunluk` üretilen CTF görevleri için bilinçli olabilir; bu satır gerçek komut gösterdiği için yanıltıcı.) | Orta |
| 13 | `gsd/terimler/kriptografi.py:377` (TR ve EN) | "Bir GPG ya da SSH anahtarının parmak izi 40 karakterlik bir onaltılık dizidir." OpenSSH parmak izi `SHA256:` + base64 (43 karakter) gösterir; 40 onaltılık yalnız GPG için doğru. | "GPG parmak izi 40 onaltılık karakter; SSH parmak izi `SHA256:…` biçiminde bir özettir." | Düşük |
| 14 | `gsd/terimler/kriptografi.py:223` | Örnek `sha256sum carotos-1.3.iso`. CLAUDE.md kural 3: yayın dosya adı `carotos-1.3-amd64.iso`. | `sha256sum carotos-1.3-amd64.iso` | Düşük |
| 15 | `gsd/terimler/genel.py:456-460` | "“Bug” teriminin kökeni, 1947'de … bir güve kelebeği". Terim 1947'den çok eskidir (ör. Edison 1878); 1947 olayı yaygınlaştırdı. Yaygın efsane. | "…terimi 1947'deki güve olayıyla popülerleşti." | Düşük |
| 16 | `gsd/terimler/algoritma.py:405-` (`p_np_problemi`) | "Modern şifrelemenin güvenliği büyük ölçüde bu sorunun yanıtının “hayır” olmasına dayanır." P≠NP gerekli ama yeterli değil; şifreleme belirli zorluk varsayımlarına dayanır. | "…P≠NP'nin doğru olması gerekir, ama tek başına yetmez." | Düşük |
| 17 | `gsd/terimler/guvenlik.py:332` | Yazım hatası "şifirelerden". | "şifrelerden" | Düşük |
| 18 | `gsd/terimler/kriptografi.py:96` | "Şifreler veritabanda" | "veritabanında" | Düşük |
| 19 | `gsd/terimler/guvenlik.py:632,673`, `kriptografi.py:338`, `linux.py:491,513`, `ag.py:432,484`, `genel.py:489` | `ornek` alanı çevrilmez (düz `str`); İngilizce ve diğer arayüzlerde Türkçe yorumlar görünür ("-- güvenli: değer ayrı gönderilir", "# dinleyen taraf …", "# çekirdeğin hangi parametrelerle …"). | Yorumları kod bloğundan çıkar ya da `ornek` yanına çevrilebilir not alanı ekle. | Düşük |
| 20 | `gsd/carotos-gsd.py:119-121` ("150'den fazla terim") | Gerçek terim sayısı 197. Hata değil ama bayat; CLAUDE.md "161" der. | "190'dan fazla" ya da sayıyı koddan hesapla. | Düşük |

Adlandırma/sürüm kuralları açısından: "CarotOS" öneki, Carotene/CarotPot önek kuralı ve "debian" bilgisayar adı tutarlı; konularda "1.3.1" geçmiyor. Tek aykırılık 14 numara (dosya adı); `dogrula` konusunun `carotos-1.4-amd64.iso` adı 1.4 dalı için doğal olabilir (aşağıda Şüpheli).

---

## 5. Şüpheliler (çalıştırarak ya da kaynağa bakarak doğrulayamadıklarım)

1. **`StartupWMClass`**: `carotos-former.desktop` ve `carotos-gsd.desktop` `StartupWMClass=carotos-former` / `carotos-gsd` diyor; pencere `GLib.set_prgname` çağrılmadan python betiğiyle açıldığından WM_CLASS büyük olasılıkla `carotos-former.py` olur ve görev çubuğunda simge gruplaması tutmaz. Gerçek masaüstünde denenmedi.
2. **`dogrula` parmak izi**: `PARMAK_IZI = 30E6 D4B0 …` ile gpgv örnek çıktısındaki imza anahtarı `05F7D6A5…` farklı. İmza alt anahtarla atılmışsa doğaldır; ama öğrenci "parmak izini karşılaştır" derken iki farklı değer görür. Anahtarın gerçek parmak izi ve alt anahtarı VM'de `gpg --show-keys --fingerprint /usr/share/keyrings/carotos-archive-keyring.gpg` ile doğrulanmalı.
3. **`carotos-1.4-amd64.iso`** (`dogrula.py:21`, `former_sahneler.py:460`): CLAUDE.md kural 3 ve kural 2 sürüm "1.3" der; 1.4 dalında bu doğal olabilir. Yayında 1.3 adı kullanılacaksa değiştirilmeli.
4. **aircrack-ng örnek çıktısı** (`aircrack_ng.py:21-29`): gerçek aracın çıktısı `WPA (0 handshake)` sütunu ve "Choosing first network as target / Please specify a dictionary (option -w)" satırlarını içerir ve sıfırdan farklı çıkış kodu verebilir; örnekte "çıkış kodu 0" yazıyor. WSL'de aircrack-ng kurulu olmadığı için doğrulanamadı.
5. **GSD örneklerindeki araçlar**: `traceroute`, `gobuster`, `ffuf`, `arp-scan`, `nc`, `aa-status`, `flatpak` `config/package-lists` içinde yok (bind9-dnsutils, curl dışındaki bazıları standart görev ya da başka paketlerle gelebilir). VM'de `command -v` ile denetlenmeli.
6. **GSD "apt" terimi** (`linux.py`): "CarotOS Panel'deki güncelleme bildirimleri de perde arkasında APT'yi kullanır." Güncelleme denetimi Sistem Sağlığı'nda (`carotos-health.py:158`, `apt-get -s upgrade`); "Panel" adı yanlış olabilir.
7. **GSD kaydırma sıfırlanması** (D-03): yeni terim seçilince eski kaydırma ofsetinin korunup korunmadığı denenmedi.
8. **Çalışma ağacındaki `__pycache__`**: `gsd/terimler/__pycache__` ve `carotpot/tuzaklar/__pycache__` Windows ağacında duruyor (git yok sayıyor, `.gitignore:36`). VM `git clone`'dan derleniyorsa sorun yok; bu ağaçtan derlenirse `.pyc` dosyaları ISO'ya girer.

---

## 6. Sağlam bulunanlar

- **Arama:** düz alt-dize eşleşmesi, kullanıcı metni regex'e girmiyor; `re.error` ve aşırı yavaşlama yok. 100 000 karakterlik sorgu, 50 000 `ı`, `\x00`, `[`, `(`, `\`, `{x}`, `%s`, `<b>&amp;` ile deneme: istisna yok, süre ihmal edilebilir (3 ms). Boş sorgu tüm terimleri döndürür.
- **İşaretleme:** arayüz `Gtk.Label(label=…)` kullanıyor (markup değil); içerikteki `<script>`, `<pid>`, `&` güvenli. Cairo tarafında `set_text`. Pango markup enjeksiyonu yok.
- **Zamanlayıcılar:** konu değiştirmede eski zamanlayıcı durdurulur (300 hızlı geçiş denemesi: tek zamanlayıcı), pencere kapanınca durur ve `_adim` çağrısı kalmaz, `_adim` istisnaya açık bir yol içermiyor, çizim hatası `CizimAlani._on_draw` içinde yakalanıyor (pencere düşmez). `Baştan`/adıma git/hız düğmesi yeni zamanlayıcı yaratmıyor.
- **Dizin sınırları:** `fz.dogrula` 20 konuda sorun bulmadı; `sec` indeksi sınırlı; altı dilde tüm `t` için `durum(t)` istisnasız. Pencere boyutu: `sahne_ciz` oranı koruyarak ölçekler (en az 980×600 istenir).
- **Komut başlatma:** komut listeleri sabit, kabuk kullanılmıyor, argümanlara kullanıcı girdisi karışmıyor; root isteyen komut doğrudan çalıştırılmıyor (panel açılır, pkexec orada).
- **Veri bütünlüğü:** Former 20 konu, GSD 197 terim; yinelenen kimlik yok, başlık yinelenmesi yok, `ilgili` başvurularının hepsi var olan terime gider ve kendine ya da tekrar etmez, tr/en çiftinde boş metin yok, yer tutucu uyuşmazlığı yok (7 dilde `{n}`, `{ad}`, `{eslesen}` dahil), paragraf sayısı tr/en uyumlu, grup/kategori adları geçerli, bayrak/sayfa adları sahnede var. (`anahtar_turetme` sayı farkı "0,5" / "half a second" yazım farkı, anlam farkı değil.)
- **Panel uyumu:** Former'in gösterdiği nmap (`-T4 -F`, `-p-`, `-sV`, `-sS`), hydra (`-L -P`), john (`--wordlist=`) komutları panel kodundaki argümanlarla birebir; Poligon/sağlık/swap/etik günlüğü/fstab yedeği (`sed -i.carotos-yedek`) iddiaları kodla doğrulandı.
- **Gerçek çıktı doğruluğu:** `gpgv` ve `sha256sum` Türkçe iletileri ("imza iyi", "KÖTÜ", "Tamam", "BAŞARISIZ") sistemin `.mo` dosyalarıyla birebir uyuşuyor (Denendi).
- **Hook'lar (9994, 9995):** `set -e`, `--no-install-recommends`, ikon `.b64` dosyaları satır sonu ile bitiyor (`read` son satırı atlamaz), izinler `755/644`, hook dosya modu 100755, `.desktop`/ikon dosyaları depoda var.
- **Testler:** `test_former.py` 29/29, `test_gsd.py` 19/19 geçti; git durumu temiz kaldı.

---

## 7. Düzeltme planı

Her adım küçük ve ayrı commit olabilir; hepsi testle birlikte.

1. **R-01 (Orta):** `konular/carotene.py`, `konular/carotpot.py` yolları düzelt; `carotos-former.py` `ac()` betik varlığı + `start_new_session`; `tests/test_former.py`'a "uygulama.komut yolu depo ağacında var" testi. Kullanıcıya görünür: iki düğme çalışır.
2. **R-02 (Orta):** `konular/carotene.py` son adımlar (`ct:tanim` tıklama, hedef `d_guncelle`, metin "Virüs tanımları"), `former_zaman.dogrula` ve `former_cizim._balon` (görünür olmayan hedef); testte dogrula'ya "balon hedefi görünür" kontrolü; 7 dil çevirisi. Kullanıcıya görünür: metin ve animasyon.
3. **D-01 (Orta) + D-02:** `gsd/carotos-gsd.py` `_kucult`/`_tr_anahtar`, `_dil_degisti` (`_listeyi_yenile`); `tests/test_gsd.py`'a "ip adresi", "INFO", "ISTISMAR", "ikili" sorguları. Kullanıcıya görünür: arama daha çok terim bulur.
4. **İçerik hataları 1-3, 11-12 (Orta):** `nikto.py`, `sqlmap.py`, `fail2ban.py`, `gsd/terimler/linux.py`, `genel.py`. Sonra 4-10 ve 13-20 (Düşük) tek commit. Kullanıcıya görünür: metinler (7 dil çevirisi gerekir).
5. **R-03, R-05, R-06, D-03:** `carotos-former.py` (hız başlangıcı, durumu koru, `sec=True`), `konular/panel.py` (ikon), `carotos-gsd.py` (kaydırma sıfırla, `sec=True`). Kullanıcıya görünür: küçük.
6. **R-07, R-08:** `former_sahneler.py:96-100` ve üç `not` kutusunu parçalı çeviriye çevir; savunma/carotpot rozet genişlikleri ve kenar menüsü kırpma; `ceviri.py` ile eksik anahtarlar; çeviri kapsama testi. Kullanıcıya görünür: çeviri dilleri.
7. **R-04, R-09 (isteğe bağlı sağlamlaştırma):** zamanlayıcı bitince bırak; konu yükleme `try/except`. Görünür değişiklik yok.
8. VM'de doğrulanacaklar: Şüpheli 1, 2, 4, 5 (masaüstü simge gruplaması, anahtar parmak izi, araçlar, aircrack çıktısı).
