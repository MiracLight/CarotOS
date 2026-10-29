"""
CarotOS Poligon -- günlük analizi görevleri için soru varyantları.

SSH (auth.log), web erişim günlüğü ve CarotPot kayıtları için her biri
farklı bir soru soran varyantlar tanımlar ve her sorunun cevabını,
üretilen GÜNLÜK METNİNİ yeniden ayrıştırarak hesaplar (öğrencinin yaptığı
işin aynısı). Belirsizlik (eşitlik) çıkarsa Belirsiz fırlatılır; üreteç
günlüğü yeniden üretir.

Yalnız standart kütüphane kullanır.
"""

from __future__ import annotations

import json
import re


class Belirsiz(AssertionError):
    """Cevap tek değil (eşitlik vb.): günlük yeniden üretilmeli."""


# ----------------------------------------------------------------------------
# Ortak yardımcılar
# ----------------------------------------------------------------------------

def _sayim(degerler) -> dict:
    d: dict = {}
    for v in degerler:
        d[v] = d.get(v, 0) + 1
    return d


def _sirali(sayim: dict) -> list:
    return sorted(sayim.items(), key=lambda kv: (-kv[1], str(kv[0])))


def _en_cok(sayim: dict):
    s = _sirali(sayim)
    if not s:
        raise Belirsiz("bos")
    if len(s) > 1 and s[0][1] == s[1][1]:
        raise Belirsiz("esitlik")
    return s[0][0]


def _ikinci(sayim: dict):
    s = _sirali(sayim)
    if len(s) < 3:
        raise Belirsiz("yetersiz")
    if s[0][1] == s[1][1] or s[1][1] == s[2][1]:
        raise Belirsiz("esitlik")
    return s[1][0]


# Öğretmenin açılır listede gördüğü kısa adlar: tur -> (tr, en)
KISA = {
    # ssh
    "ip_en_cok": ("En çok deneyen IP", "Top attacking IP"),
    "sayi_en_cok": ("En çok deneyenin deneme sayısı", "Attempts of the top IP"),
    "farkli_ip": ("Farklı IP sayısı", "Distinct IP count"),
    "toplam_basarisiz": ("Toplam başarısız giriş", "Total failed logins"),
    "gecersiz_kullanici": ("Var olmayan hesap denemeleri", "Non-existent account attempts"),
    "kullanici_en_cok": ("En sık denenen kullanıcı adı", "Most tried username"),
    "kullanici_cesidi": ("Saldırganın denediği hesap sayısı", "Accounts tried by the attacker"),
    "ikinci_ip": ("İkinci sıradaki IP", "Second-ranked IP"),
    "ilk_zaman": ("İlk deneme saati", "First attempt time"),
    "saat_en_cok": ("En yoğun saat", "Busiest hour"),
    "hesap": ("Ele geçirilen hesap", "Compromised account"),
    "basarili_toplam": ("Başarılı giriş sayısı", "Successful login count"),
    "parola_girisi": ("Parolayla girişler", "Password logins"),
    "anahtar_girisi": ("Anahtarla girişler", "Key logins"),
    "giris_zamani": ("Başarılı giriş saati", "Successful login time"),
    "giris_port": ("Giriş kaynak portu", "Login source port"),
    "giris_oncesi": ("Girişten önceki başarısızlıklar", "Failures before the login"),
    "hesap_ve_ip": ("IP ve hesap birlikte", "IP and account together"),
    "oturum_sayisi": ("Açılan oturum sayısı", "Opened session count"),
    # web (ip)
    "ip_en_cok_404": ("En çok 404 alan IP", "IP with most 404s"),
    "sayi_404_top": ("En çok 404 alanın sayısı", "404 count of the top IP"),
    "toplam_404": ("Toplam 404 sayısı", "Total 404 count"),
    "farkli_yol_top": ("Tarayıcının denediği farklı yol", "Distinct paths tried"),
    "arac_adi": ("Tarama aracının adı", "Scanning tool name"),
    "ilk_zaman_top": ("Tarayıcının ilk isteği", "Scanner's first request"),
    "yol_en_cok_404": ("En çok 404 alan yol", "Path with most 404s"),
    "yol_en_cok_200": ("En çok istenen yol", "Most requested path"),
    "saat_en_cok_404": ("404'lerin en yoğun saati", "Busiest hour for 404s"),
    # web (yol)
    "gizli_yol": ("Bulunan gizli yol", "Hidden path found"),
    "gizli_200_sayisi": ("Gizli yola başarılı erişim sayısı", "Successful hits on the hidden path"),
    "gizli_boyut": ("İlk 200 yanıtının boyutu", "Size of the first 200 response"),
    "gizli_dizin": ("Gizli yolun dizin adı", "Hidden path's directory"),
    "gizli_son_bolum": ("Gizli yolun son bölümü", "Hidden path's last segment"),
    "gizli_zaman": ("Gizli yola ilk erişim saati", "First hidden-path hit time"),
    "oncesi_404": ("Bulana kadar alınan 404", "404s before the find"),
    "son_oktet": ("Tarayıcı IP'sinin son sekizlisi", "Scanner IP's last octet"),
    "toplam_boyut": ("Gizli yol yanıtlarının toplam boyutu", "Total size of hidden-path responses"),
    # carotpot (kullanici)
    "en_cok_sayi": ("En çok denenenin sayısı", "Count of the most-tried"),
    "farkli_kullanici": ("Farklı kullanıcı adı sayısı", "Distinct username count"),
    "toplam_giris": ("Toplam giriş denemesi", "Total login attempts"),
    "hizmet_en_cok": ("En çok denenen hizmet", "Most attacked service"),
    "kaynak_en_cok": ("En çok deneyen kaynak", "Most active source"),
    "http_giris": ("http giriş denemeleri", "http login attempts"),
    "ikinci_kullanici": ("İkinci en sık kullanıcı adı", "Second most tried username"),
    "parola_en_cok": ("En sık denenen parola", "Most tried password"),
    "son_zaman": ("Son giriş denemesi saati", "Last login attempt time"),
    # carotpot (tarayici)
    "tarayici_ip": ("En çok hizmete dokunan IP", "IP touching the most services"),
    "hizmet_sayisi": ("Dokunulan hizmet sayısı", "Number of services touched"),
    "hizmet_listesi": ("Dokunulan hizmetlerin listesi", "List of services touched"),
    "tarama_olay_sayisi": ("Tarama olayı sayısı", "Scan event count"),
    "en_cok_olay_ip": ("En çok olay üreten IP", "IP with the most events"),
    "farkli_kaynak": ("Farklı kaynak sayısı", "Distinct source count"),
    "tarama_suresi": ("Taramanın süresi (sn)", "Scan duration (s)"),
    "ilk_tarama_hizmeti": ("İlk taranan hizmet", "First scanned service"),
    "son_tarama_zaman": ("Son tarama saati", "Last scan time"),
    "hizmet_kaynak_http": ("http'ye dokunan kaynak sayısı", "Sources touching http"),
    "hizmet_kaynak_ssh": ("ssh'a dokunan kaynak sayısı", "Sources touching ssh"),
    "hizmet_kaynak_ftp": ("ftp'ye dokunan kaynak sayısı", "Sources touching ftp"),
    "hizmet_kaynak_telnet": ("telnet'e dokunan kaynak sayısı", "Sources touching telnet"),
}
_BICIM_KISA = {"syslog": "syslog", "iso": "ISO", "combined": "combined", "json": "JSON",
               "carotpot": "CarotPot", "jsonl": "JSON"}


def _v(tur, bicim, soru, ipucu, aciklama, **ek) -> dict:
    kisa = KISA.get(tur, (tur, tur))
    return {"tur": tur, "bicim": bicim, "soru": {"tr": soru[0], "en": soru[1]},
            "ipucu": {"tr": ipucu[0], "en": ipucu[1]},
            "bicim_aciklama": {"tr": aciklama[0], "en": aciklama[1]},
            "ozet": {"tr": f"{kisa[0]} · {_BICIM_KISA.get(bicim, bicim)}",
                     "en": f"{kisa[1]} · {_BICIM_KISA.get(bicim, bicim)}"}, **ek}


_SAAT_RE = re.compile(r"(\d\d):(\d\d):(\d\d)")


def _saat(satir: str) -> str:
    m = _SAAT_RE.search(satir)
    if not m:
        raise Belirsiz("zaman yok")
    return m.group(0)


# ----------------------------------------------------------------------------
# 1) SSH günlüğü
# ----------------------------------------------------------------------------

_FAIL = re.compile(r"Failed password for (?:invalid user )?(\S+) from (\S+) port (\d+)")
_ACC = re.compile(r"Accepted (password|publickey) for (\S+) from (\S+) port (\d+)")

SSH_BICIMLERI = {
    "syslog": ("klasik syslog zaman damgaları", "classic syslog timestamps"),
    "iso": ("ISO 8601 zaman damgaları", "ISO 8601 timestamps"),
}

_SSH_TABLO = "grep 'Failed password' {dosya} | grep -oE 'from [0-9.]+' | sort | uniq -c | sort -rn | head"
_SSH_ILK_IP = "grep 'Failed password' {dosya} | grep -oE 'from [0-9.]+' | sort | uniq -c | sort -rn | head -1"

# (tur, (soru_tr, soru_en), (ipucu_tr, ipucu_en))
_SSH_SALDIRGAN = [
    ("ip_en_cok",
     ("En çok 'Failed password' kaydı bırakan IP adresini bul ve yaz.",
      "Find and write the IP address that left the most 'Failed password' records."),
     (f"Sıklık tablosu: {_SSH_TABLO}", f"Frequency table: {_SSH_TABLO}")),
    ("sayi_en_cok",
     ("En çok 'Failed password' kaydı bırakan IP adresinin kaç kaydı var? Yalnızca sayıyı yaz.",
      "How many 'Failed password' records does the IP with the most records have? Write only the number."),
     (f"Tablonun ilk satırındaki sayı: {_SSH_TABLO}", f"The number on the table's first row: {_SSH_TABLO}")),
    ("farkli_ip",
     ("'Failed password' kaydı bulunan kaç farklı IP adresi var? Yalnızca sayıyı yaz.",
      "How many different IP addresses appear in 'Failed password' records? Write only the number."),
     ("grep 'Failed password' {dosya} | grep -oE 'from [0-9.]+' | sort -u | wc -l",
      "grep 'Failed password' {dosya} | grep -oE 'from [0-9.]+' | sort -u | wc -l")),
    ("toplam_basarisiz",
     ("Günlükte kaç satırda 'Failed password' geçiyor? Yalnızca sayıyı yaz.",
      "On how many lines does 'Failed password' appear? Write only the number."),
     ("grep -c 'Failed password' {dosya}", "grep -c 'Failed password' {dosya}")),
    ("gecersiz_kullanici",
     ("Sistemde olmayan hesaplar için ('invalid user') kaç başarısız parola kaydı var? Yalnızca sayıyı yaz.",
      "How many failed password records are for accounts that do not exist ('invalid user')? Write only the number."),
     ("grep -c 'Failed password for invalid user' {dosya}",
      "grep -c 'Failed password for invalid user' {dosya}")),
    ("kullanici_en_cok",
     ("Başarısız girişlerde en sık denenen kullanıcı adını yaz.",
      "Write the username tried most often in the failed logins."),
     ("grep 'Failed password' {dosya} | sed -E 's/.*Failed password for (invalid user )?([^ ]+) from.*/\\2/' | sort | uniq -c | sort -rn | head",
      "grep 'Failed password' {dosya} | sed -E 's/.*Failed password for (invalid user )?([^ ]+) from.*/\\2/' | sort | uniq -c | sort -rn | head")),
    ("kullanici_cesidi",
     ("En çok başarısız deneme yapan IP adresi kaç farklı kullanıcı adını denedi? Yalnızca sayıyı yaz.",
      "How many different usernames did the IP with the most failed attempts try? Write only the number."),
     (f"Önce IP'yi bul ({_SSH_ILK_IP}); sonra: grep 'Failed password' {{dosya}} | grep 'from <IP> ' | sed -E 's/.*for (invalid user )?([^ ]+) from.*/\\2/' | sort -u | wc -l",
      f"First find the IP ({_SSH_ILK_IP}); then: grep 'Failed password' {{dosya}} | grep 'from <IP> ' | sed -E 's/.*for (invalid user )?([^ ]+) from.*/\\2/' | sort -u | wc -l")),
    ("ikinci_ip",
     ("Başarısız deneme sayısına göre İKİNCİ sıradaki IP adresini yaz.",
      "Write the IP address in SECOND place by number of failed attempts."),
     (f"Sıklık tablosunun ikinci satırı: {_SSH_TABLO}", f"The second row of the frequency table: {_SSH_TABLO}")),
    ("ilk_zaman",
     ("En çok başarısız deneme yapan IP adresinin İLK başarısız denemesi saat kaçta? SS:DD:SN biçiminde yaz (örn. 14:03:09).",
      "At what time was the first failed attempt of the IP with the most failures? Write it as HH:MM:SS (e.g. 14:03:09)."),
     (f"IP'yi bul ({_SSH_ILK_IP}); sonra: grep 'Failed password' {{dosya}} | grep 'from <IP> ' | head -1",
      f"Find the IP ({_SSH_ILK_IP}); then: grep 'Failed password' {{dosya}} | grep 'from <IP> ' | head -1")),
    ("saat_en_cok",
     ("Başarısız parola denemelerinin EN ÇOK yapıldığı saati (iki haneli, 00-23) yaz. Örn. 07.",
      "Write the hour (two digits, 00-23) in which the MOST failed password attempts happened. E.g. 07."),
     ("grep 'Failed password' {dosya} | grep -oE '[0-9]{2}:[0-9]{2}:[0-9]{2}' | cut -d: -f1 | sort | uniq -c | sort -rn | head",
      "grep 'Failed password' {dosya} | grep -oE '[0-9]{2}:[0-9]{2}:[0-9]{2}' | cut -d: -f1 | sort | uniq -c | sort -rn | head")),
]

_SSH_GIREN = [
    ("hesap",
     ("En çok başarısız deneme yapan IP adresi sonunda hangi hesaba parolayla girdi? Kullanıcı adını yaz.",
      "Which account did the IP with the most failed attempts finally log in to with a password? Write the username."),
     (f"IP'yi bul ({_SSH_ILK_IP}); sonra: grep 'Accepted password' {{dosya}} | grep 'from <IP> '",
      f"Find the IP ({_SSH_ILK_IP}); then: grep 'Accepted password' {{dosya}} | grep 'from <IP> '")),
    ("basarili_toplam",
     ("Günlükte toplam kaç başarılı giriş ('Accepted') var? Yalnızca sayıyı yaz.",
      "How many successful logins ('Accepted') are there in total? Write only the number."),
     ("grep -c 'Accepted' {dosya}", "grep -c 'Accepted' {dosya}")),
    ("parola_girisi",
     ("Kaç giriş PAROLAYLA yapılmış ('Accepted password')? Yalnızca sayıyı yaz.",
      "How many logins were made with a PASSWORD ('Accepted password')? Write only the number."),
     ("grep -c 'Accepted password' {dosya}", "grep -c 'Accepted password' {dosya}")),
    ("anahtar_girisi",
     ("Kaç giriş ANAHTARLA yapılmış ('Accepted publickey')? Yalnızca sayıyı yaz.",
      "How many logins were made with a KEY ('Accepted publickey')? Write only the number."),
     ("grep -c 'Accepted publickey' {dosya}", "grep -c 'Accepted publickey' {dosya}")),
    ("giris_zamani",
     ("En çok başarısız deneme yapan IP adresinin parolayla BAŞARILI girişi saat kaçta? SS:DD:SN biçiminde yaz (örn. 14:03:09).",
      "At what time did the IP with the most failures log in SUCCESSFULLY with a password? Write it as HH:MM:SS (e.g. 14:03:09)."),
     (f"IP'yi bul ({_SSH_ILK_IP}); sonra: grep 'Accepted password' {{dosya}} | grep 'from <IP> '",
      f"Find the IP ({_SSH_ILK_IP}); then: grep 'Accepted password' {{dosya}} | grep 'from <IP> '")),
    ("giris_port",
     ("En çok başarısız deneme yapan IP adresinin başarılı girişindeki kaynak port numarasını yaz.",
      "Write the source port number of the successful login by the IP with the most failures."),
     (f"IP'yi bul ({_SSH_ILK_IP}); sonra: grep 'Accepted password' {{dosya}} | grep 'from <IP> '  ('port' sözcüğünden sonraki sayı)",
      f"Find the IP ({_SSH_ILK_IP}); then: grep 'Accepted password' {{dosya}} | grep 'from <IP> '  (the number after 'port')")),
    ("giris_oncesi",
     ("Parolayla giren IP adresi, girmeden önce kaç kez başarısız oldu? Yalnızca sayıyı yaz.",
      "How many times did the IP that logged in with a password fail before getting in? Write only the number."),
     (f"IP'yi bul ({_SSH_ILK_IP}); sayı tablonun ilk sütunudur.",
      f"Find the IP ({_SSH_ILK_IP}); the count is the table's first column.")),
    ("kullanici_cesidi",
     ("Saldırgan IP adresi (en çok başarısız deneme yapan) kaç farklı kullanıcı adını denedi? Yalnızca sayıyı yaz.",
      "How many different usernames did the attacking IP (the one with the most failures) try? Write only the number."),
     (f"IP'yi bul ({_SSH_ILK_IP}); sonra: grep 'Failed password' {{dosya}} | grep 'from <IP> ' | sed -E 's/.*for (invalid user )?([^ ]+) from.*/\\2/' | sort -u | wc -l",
      f"Find the IP ({_SSH_ILK_IP}); then: grep 'Failed password' {{dosya}} | grep 'from <IP> ' | sed -E 's/.*for (invalid user )?([^ ]+) from.*/\\2/' | sort -u | wc -l")),
    ("hesap_ve_ip",
     ("Saldırgan IP adresini (en çok başarısız deneme yapan) ve girdiği hesabı 'ip:hesap' biçiminde yaz (örn. 203.0.113.5:ayse).",
      "Write the attacking IP (the one with the most failures) and the account it got into as 'ip:account' (e.g. 203.0.113.5:ayse)."),
     (f"IP'yi bul ({_SSH_ILK_IP}); sonra: grep 'Accepted password' {{dosya}} | grep 'from <IP> '",
      f"Find the IP ({_SSH_ILK_IP}); then: grep 'Accepted password' {{dosya}} | grep 'from <IP> '")),
    ("oturum_sayisi",
     ("Günlükte kaç parola girişi için oturum açılışı kaydı ('session opened') var? Yalnızca sayıyı yaz.",
      "How many 'session opened' records are in the log? Write only the number."),
     ("grep -c 'session opened' {dosya}", "grep -c 'session opened' {dosya}")),
]


def _ssh_kayitlari(liste) -> list[dict]:
    out = []
    for tur, soru, ipucu in liste:
        for bicim, aciklama in SSH_BICIMLERI.items():
            out.append(_v(tur, bicim, soru, ipucu, aciklama))
    return out


def ssh_cevap(tur: str, satirlar: list[str]) -> str:
    fails, accs = [], []
    for s in satirlar:
        m = _FAIL.search(s)
        if m:
            fails.append((m.group(1), m.group(2), m.group(3), s))
        m = _ACC.search(s)
        if m:
            accs.append((m.group(1), m.group(2), m.group(3), m.group(4), s))
    ip_sayim = _sayim(f[1] for f in fails)

    def ust_ip() -> str:
        return _en_cok(ip_sayim)

    def girisi() -> tuple:
        ip = ust_ip()
        liste = [a for a in accs if a[0] == "password" and a[2] == ip]
        if len(liste) != 1:
            raise Belirsiz("giris belirsiz")
        return liste[0]

    if tur == "ip_en_cok":
        return ust_ip()
    if tur == "sayi_en_cok":
        return str(ip_sayim[ust_ip()])
    if tur == "farkli_ip":
        return str(len(ip_sayim))
    if tur == "toplam_basarisiz":
        return str(len(fails))
    if tur == "gecersiz_kullanici":
        return str(sum(1 for s in satirlar if "Failed password for invalid user" in s))
    if tur == "kullanici_en_cok":
        return _en_cok(_sayim(f[0] for f in fails))
    if tur == "kullanici_cesidi":
        ip = ust_ip()
        return str(len({f[0] for f in fails if f[1] == ip}))
    if tur == "ikinci_ip":
        return _ikinci(ip_sayim)
    if tur == "ilk_zaman":
        ip = ust_ip()
        return _saat(next(f[3] for f in fails if f[1] == ip))
    if tur == "saat_en_cok":
        return _en_cok(_sayim(_saat(f[3])[:2] for f in fails))
    # --- ssh_giren
    if tur == "hesap":
        return girisi()[1]
    if tur == "basarili_toplam":
        return str(len(accs))
    if tur == "parola_girisi":
        return str(sum(1 for a in accs if a[0] == "password"))
    if tur == "anahtar_girisi":
        return str(sum(1 for a in accs if a[0] == "publickey"))
    if tur == "giris_zamani":
        return _saat(girisi()[4])
    if tur == "giris_port":
        return girisi()[3]
    if tur == "giris_oncesi":
        return str(ip_sayim[girisi()[2]])
    if tur == "hesap_ve_ip":
        g = girisi()
        return f"{g[2]}:{g[1]}"
    if tur == "oturum_sayisi":
        return str(sum(1 for s in satirlar if "session opened for user" in s))
    raise ValueError(f"bilinmeyen ssh turu: {tur}")


# ----------------------------------------------------------------------------
# 2) Web erişim günlüğü
# ----------------------------------------------------------------------------

_WEB_RE = re.compile(r'^(\S+) \S+ \S+ \[[^\]]*?:(\d\d:\d\d:\d\d) [^\]]*\] "(\S+) (\S+) [^"]*" (\d{3}) (\d+) "[^"]*" "([^"]*)"$')

ARAC_UA = (
    ("Nikto/2.1.6", "Nikto"),
    ("sqlmap/1.7.2#stable (https://sqlmap.org)", "sqlmap"),
    ("gobuster/3.5", "gobuster"),
    ("DirBuster-1.0-RC1", "DirBuster"),
    ("Wfuzz/3.1.0", "Wfuzz"),
    ("python-requests/2.31.0", "python-requests"),
)

WEB_BICIMLERI = {
    "combined": ("Apache 'combined' biçimi", "Apache 'combined' format"),
    "json": ("satır başına bir JSON nesnesi, jq ile okunur", "one JSON object per line, read with jq"),
}


def arac_adi_bul(ua: str) -> str | None:
    for u, ad in ARAC_UA:
        if ua == u:
            return ad
    return None


def web_ayikla(satirlar: list[str], bicim: str) -> list[dict]:
    out = []
    for s in satirlar:
        if bicim == "json":
            o = json.loads(s)
            out.append({"ip": o["ip"], "zaman": o["ts"][11:19], "yol": o["path"],
                        "kod": int(o["status"]), "boyut": int(o["bytes"]), "ua": o["ua"]})
        else:
            m = _WEB_RE.match(s)
            if not m:
                raise Belirsiz("satir ayristirilamadi")
            out.append({"ip": m.group(1), "zaman": m.group(2), "yol": m.group(4),
                        "kod": int(m.group(5)), "boyut": int(m.group(6)), "ua": m.group(7)})
    return out


def _web_komut(bicim: str, combined: str, jq: str) -> str:
    return combined if bicim == "combined" else jq


def _web_hint_ip_tablosu(bicim):
    return _web_komut(
        bicim,
        "awk '$9==404 {print $1}' {dosya} | sort | uniq -c | sort -rn | head",
        "jq -r 'select(.status==404) | .ip' {dosya} | sort | uniq -c | sort -rn | head")


_WEB_IP = [
    ("ip_en_cok_404",
     ("En çok 404 (bulunamadı) yanıtı alan IP adresini yaz.",
      "Write the IP address that received the most 404 (not found) responses."),
     lambda b: (f"Sıklık tablosu: {_web_hint_ip_tablosu(b)}", f"Frequency table: {_web_hint_ip_tablosu(b)}")),
    ("sayi_404_top",
     ("En çok 404 alan IP adresi kaç tane 404 aldı? Yalnızca sayıyı yaz.",
      "How many 404 responses did the IP with the most 404s receive? Write only the number."),
     lambda b: (f"Tablonun ilk satırındaki sayı: {_web_hint_ip_tablosu(b)}",
                f"The number on the first row: {_web_hint_ip_tablosu(b)}")),
    ("toplam_404",
     ("Günlükte toplam kaç istek 404 yanıtı almış? Yalnızca sayıyı yaz.",
      "How many requests in total received a 404 response? Write only the number."),
     lambda b: (_web_komut(b, "awk '$9==404' {dosya} | wc -l", "jq -r 'select(.status==404) | .ip' {dosya} | wc -l"),) * 2),
    ("farkli_yol_top",
     ("En çok 404 alan IP adresi kaç FARKLI yolu denedi? Yalnızca sayıyı yaz.",
      "How many DIFFERENT paths did the IP with the most 404s try? Write only the number."),
     lambda b: (f"IP'yi bul ({_web_hint_ip_tablosu(b)}); sonra: " + _web_komut(
         b, "awk '$9==404 && $1==\"<IP>\" {print $7}' {dosya} | sort -u | wc -l",
         "jq -r 'select(.status==404 and .ip==\"<IP>\") | .path' {dosya} | sort -u | wc -l"),) * 2),
    ("arac_adi",
     ("En çok 404 alan IP adresi hangi aracı kullanıyor? User-Agent'taki araç adını yaz (örn. Nikto).",
      "Which tool does the IP with the most 404s use? Write the tool name from its User-Agent (e.g. Nikto)."),
     lambda b: (f"IP'yi bul ({_web_hint_ip_tablosu(b)}); sonra o IP'nin satırlarında User-Agent alanına bak: grep '<IP>' {{dosya}} | head -3",) * 2),
    ("ilk_zaman_top",
     ("En çok 404 alan IP adresinin İLK isteği saat kaçta? SS:DD:SN biçiminde yaz (örn. 14:03:09).",
      "At what time was the FIRST request of the IP with the most 404s? Write it as HH:MM:SS (e.g. 14:03:09)."),
     lambda b: (f"IP'yi bul ({_web_hint_ip_tablosu(b)}); sonra: grep '<IP>' {{dosya}} | head -1",) * 2),
    ("yol_en_cok_404",
     ("Tüm günlükte en çok 404 alan YOLU (örn. /admin) yaz.",
      "Write the PATH that received the most 404 responses in the whole log (e.g. /admin)."),
     lambda b: (_web_komut(b, "awk '$9==404 {print $7}' {dosya} | sort | uniq -c | sort -rn | head",
                           "jq -r 'select(.status==404) | .path' {dosya} | sort | uniq -c | sort -rn | head"),) * 2),
    ("farkli_ip",
     ("Günlükte kaç FARKLI IP adresi var? Yalnızca sayıyı yaz.",
      "How many DIFFERENT IP addresses are in the log? Write only the number."),
     lambda b: (_web_komut(b, "awk '{print $1}' {dosya} | sort -u | wc -l",
                           "jq -r '.ip' {dosya} | sort -u | wc -l"),) * 2),
    ("yol_en_cok_200",
     ("Başarılı (200) yanıt verilen en çok istenen YOLU yaz.",
      "Write the PATH requested most often among successful (200) responses."),
     lambda b: (_web_komut(b, "awk '$9==200 {print $7}' {dosya} | sort | uniq -c | sort -rn | head",
                           "jq -r 'select(.status==200) | .path' {dosya} | sort | uniq -c | sort -rn | head"),) * 2),
    ("saat_en_cok_404",
     ("404 yanıtlarının EN ÇOK verildiği saati (iki haneli, 00-23) yaz. Örn. 07.",
      "Write the hour (two digits, 00-23) with the MOST 404 responses. E.g. 07."),
     lambda b: (_web_komut(b, "awk '$9==404' {dosya} | grep -oE '[0-9]{2}:[0-9]{2}:[0-9]{2}' | cut -d: -f1 | sort | uniq -c | sort -rn | head",
                           "jq -r 'select(.status==404) | .ts[11:13]' {dosya} | sort | uniq -c | sort -rn | head"),) * 2),
]

_WEB_YOL = [
    ("gizli_yol",
     ("Önce tarayıcıyı (en çok 404 alan IP) bul; sonra onun 200 (başarılı) yanıt aldığı gizli yolu yaz (örn. /yedek-ab3d/veritabani.sql).",
      "First find the scanner (the IP with the most 404s); then write the hidden path for which it received a 200 (success) (e.g. /yedek-ab3d/veritabani.sql)."),
     None),
    ("gizli_200_sayisi",
     ("Tarayıcı IP adresi (en çok 404 alan) gizli yola kaç kez başarıyla (200) eriştı? Yalnızca sayıyı yaz.",
      "How many times did the scanner IP (the one with the most 404s) reach the hidden path successfully (200)? Write only the number."),
     None),
    ("gizli_boyut",
     ("Tarayıcının gizli yola aldığı İLK 200 yanıtının boyutu (bayt) kaç? Yalnızca sayıyı yaz.",
      "What is the size in bytes of the scanner's FIRST 200 response for the hidden path? Write only the number."),
     None),
    ("gizli_dizin",
     ("Tarayıcının bulduğu gizli yolun İLK dizin adını yaz (örn. yedek-ab3d).",
      "Write the FIRST directory name of the hidden path the scanner found (e.g. yedek-ab3d)."),
     None),
    ("gizli_son_bolum",
     ("Tarayıcının bulduğu gizli yolun SON bölümünü (dosya adı ya da son dizin) yaz (örn. veritabani.sql).",
      "Write the LAST segment (file or last directory name) of the hidden path the scanner found (e.g. veritabani.sql)."),
     None),
    ("gizli_zaman",
     ("Tarayıcı gizli yola ilk kez saat kaçta başarıyla (200) eriştı? SS:DD:SN biçiminde yaz (örn. 14:03:09).",
      "At what time did the scanner first reach the hidden path successfully (200)? Write it as HH:MM:SS (e.g. 14:03:09)."),
     None),
    ("oncesi_404",
     ("Tarayıcı IP adresi toplam kaç 404 aldı (gizli yolu bulana kadar)? Yalnızca sayıyı yaz.",
      "How many 404s did the scanner IP receive in total before finding the hidden path? Write only the number."),
     None),
    ("arac_adi",
     ("Gizli yolu bulan tarayıcı hangi aracı kullanıyor? User-Agent'taki araç adını yaz (örn. Nikto).",
      "Which tool does the scanner that found the hidden path use? Write the tool name from its User-Agent (e.g. Nikto)."),
     None),
    ("son_oktet",
     ("Gizli yolu bulan tarayıcının IP adresinin SON sekizlisini (son sayı) yaz.",
      "Write the LAST octet (last number) of the IP address of the scanner that found the hidden path."),
     None),
    ("toplam_boyut",
     ("Tarayıcının gizli yoldan aldığı TÜM 200 yanıtlarının boyutlarının toplamı (bayt) kaç? Yalnızca sayıyı yaz.",
      "What is the total size in bytes of ALL the scanner's 200 responses for the hidden path? Write only the number."),
     None),
]


def _web_yol_ipucu(b: str):
    tablo = _web_hint_ip_tablosu(b)
    gizli = _web_komut(b, "awk '$9==200 && $1==\"<IP>\"' {dosya}",
                       "jq -c 'select(.status==200 and .ip==\"<IP>\")' {dosya}")
    return (f"Önce 404 sıklık tablosundan tarayıcı IP'sini bul ({tablo}); sonra onun 200 satırlarına bak: {gizli}",
            f"First find the scanner IP in the 404 frequency table ({tablo}); then look at its 200 lines: {gizli}")


def _web_kayitlari(liste, ip_modu: bool) -> list[dict]:
    out = []
    for tur, soru, ipucu in liste:
        for bicim, aciklama in WEB_BICIMLERI.items():
            ip = ipucu(bicim) if ip_modu else _web_yol_ipucu(bicim)
            ek = {"arac_ua": 1} if tur == "arac_adi" else {}
            out.append(_v(tur, bicim, soru, ip, aciklama, **ek))
    return out


def web_cevap(kip: str, tur: str, satirlar: list[str], bicim: str) -> str:
    k = web_ayikla(satirlar, bicim)
    k404 = [x for x in k if x["kod"] == 404]
    ip_sayim = _sayim(x["ip"] for x in k404)

    def tarayici() -> str:
        return _en_cok(ip_sayim)

    def gizli() -> list[dict]:
        ip = tarayici()
        g = [x for x in k if x["ip"] == ip and x["kod"] == 200]
        if not g or len({x["yol"] for x in g}) != 1:
            raise Belirsiz("gizli yol belirsiz")
        return g

    if tur == "ip_en_cok_404":
        return tarayici()
    if tur == "sayi_404_top":
        return str(ip_sayim[tarayici()])
    if tur == "toplam_404":
        return str(len(k404))
    if tur == "farkli_yol_top":
        ip = tarayici()
        return str(len({x["yol"] for x in k404 if x["ip"] == ip}))
    if tur == "arac_adi":
        ip = tarayici()
        ad = {arac_adi_bul(x["ua"]) for x in k if x["ip"] == ip}
        if len(ad) != 1 or None in ad:
            raise Belirsiz("arac belirsiz")
        return ad.pop()
    if tur == "ilk_zaman_top":
        ip = tarayici()
        return next(x["zaman"] for x in k if x["ip"] == ip)
    if tur == "yol_en_cok_404":
        return _en_cok(_sayim(x["yol"] for x in k404))
    if tur == "farkli_ip":
        return str(len({x["ip"] for x in k}))
    if tur == "yol_en_cok_200":
        return _en_cok(_sayim(x["yol"] for x in k if x["kod"] == 200))
    if tur == "saat_en_cok_404":
        return _en_cok(_sayim(x["zaman"][:2] for x in k404))
    # --- yol kipi
    if tur == "gizli_yol":
        return gizli()[0]["yol"]
    if tur == "gizli_200_sayisi":
        return str(len(gizli()))
    if tur == "gizli_boyut":
        return str(gizli()[0]["boyut"])
    if tur == "gizli_dizin":
        return gizli()[0]["yol"].strip("/").split("/")[0]
    if tur == "gizli_son_bolum":
        return gizli()[0]["yol"].rstrip("/").split("/")[-1]
    if tur == "gizli_zaman":
        return gizli()[0]["zaman"]
    if tur == "oncesi_404":
        return str(ip_sayim[tarayici()])
    if tur == "son_oktet":
        return tarayici().split(".")[-1]
    if tur == "toplam_boyut":
        return str(sum(x["boyut"] for x in gizli()))
    raise ValueError(f"bilinmeyen web turu: {tur}")


# ----------------------------------------------------------------------------
# 3) CarotPot kayıtları
# ----------------------------------------------------------------------------

CP_BICIMLERI = {
    "carotpot": ("CarotPot günlük biçimi: tarih, CAROTPOT, anahtar=değer ve JSON",
                 "CarotPot log format: date, CAROTPOT, key=value and JSON"),
    "jsonl": ("satır başına bir JSON nesnesi, jq ile okunur", "one JSON object per line, read with jq"),
}


def cp_ayikla(satirlar: list[str], bicim: str) -> list[dict]:
    out = []
    for s in satirlar:
        if bicim == "jsonl":
            o = json.loads(s)
            zaman = None
        else:
            onek, _, js = s.partition(" | ")
            o = json.loads(js)
            zaman = onek[11:19]
        out.append({"ip": o["kaynak"], "hizmet": o["hizmet"], "tur": o["tur"],
                    "kullanici": o.get("kullanici"), "parola": o.get("parola"),
                    "ts": float(o["ts"]), "zaman": zaman})
    return out


def _cp_komut(b, grep, jq):
    return grep if b == "carotpot" else jq


_CP_GIRIS_KULLANICI = {
    "carotpot": "grep 'tur=giris' {dosya} | grep -oE '\"kullanici\": \"[^\"]+\"' | sort | uniq -c | sort -rn | head",
    "jsonl": "jq -r 'select(.tur==\"giris\") | .kullanici' {dosya} | sort | uniq -c | sort -rn | head",
}

_CP_KULLANICI = [
    ("kullanici_en_cok", ("Saldırganların en çok denediği kullanıcı adını yaz.",
                          "Write the username the attackers tried most."),
     lambda b: _CP_GIRIS_KULLANICI[b], True),
    ("en_cok_sayi", ("En çok denenen kullanıcı adı kaç kez denendi? Yalnızca sayıyı yaz.",
                     "How many times was the most-tried username tried? Write only the number."),
     lambda b: "Tablonun ilk satırındaki sayı: " + _CP_GIRIS_KULLANICI[b], True),
    ("farkli_kullanici", ("Giriş denemelerinde kaç FARKLI kullanıcı adı denendi? Yalnızca sayıyı yaz.",
                          "How many DIFFERENT usernames were tried in login attempts? Write only the number."),
     lambda b: _CP_GIRIS_KULLANICI[b].split(" | sort | uniq")[0] + " | sort -u | wc -l", True),
    ("toplam_giris", ("Kayıtta kaç 'giris' olayı (giriş denemesi) var? Yalnızca sayıyı yaz.",
                      "How many 'giris' (login attempt) events are in the log? Write only the number."),
     lambda b: _cp_komut(b, "grep -c 'tur=giris' {dosya}", "jq -r 'select(.tur==\"giris\") | .tur' {dosya} | wc -l"), True),
    ("hizmet_en_cok", ("En çok giriş denemesi hangi hizmete yapıldı? Hizmet adını yaz (örn. ftp).",
                       "Which service received the most login attempts? Write the service name (e.g. ftp)."),
     lambda b: _cp_komut(b, "grep 'tur=giris' {dosya} | grep -oE 'hizmet=[a-z]+' | sort | uniq -c | sort -rn | head",
                         "jq -r 'select(.tur==\"giris\") | .hizmet' {dosya} | sort | uniq -c | sort -rn | head"), True),
    ("kaynak_en_cok", ("En çok giriş denemesi yapan kaynak IP adresini yaz.",
                       "Write the source IP address that made the most login attempts."),
     lambda b: _cp_komut(b, "grep 'tur=giris' {dosya} | grep -oE 'kaynak=[0-9.]+' | sort | uniq -c | sort -rn | head",
                         "jq -r 'select(.tur==\"giris\") | .kaynak' {dosya} | sort | uniq -c | sort -rn | head"), True),
    ("http_giris", ("'http' hizmetine kaç giriş denemesi yapılmış? Yalnızca sayıyı yaz.",
                    "How many login attempts were made on the 'http' service? Write only the number."),
     lambda b: _cp_komut(b, "grep 'tur=giris' {dosya} | grep -c 'hizmet=http'",
                         "jq -r 'select(.tur==\"giris\" and .hizmet==\"http\") | .tur' {dosya} | wc -l"), True),
    ("ikinci_kullanici", ("En çok denenen İKİNCİ kullanıcı adını yaz.",
                          "Write the SECOND most-tried username."),
     lambda b: "Tablonun ikinci satırı: " + _CP_GIRIS_KULLANICI[b], True),
    ("parola_en_cok", ("En çok denenen (maskeli) parolayı kayıttaki haliyle yaz (örn. p*******).",
                       "Write the most-tried (masked) password exactly as shown in the log (e.g. p*******)."),
     lambda b: _cp_komut(b, "grep 'tur=giris' {dosya} | grep -oE '\"parola\": \"[^\"]+\"' | sort | uniq -c | sort -rn | head",
                         "jq -r 'select(.tur==\"giris\") | .parola' {dosya} | sort | uniq -c | sort -rn | head"), True),
    ("ilk_zaman", ("İlk giriş denemesi saat kaçta yapıldı? SS:DD:SN biçiminde yaz (örn. 14:03:09).",
                   "At what time was the first login attempt made? Write it as HH:MM:SS (e.g. 14:03:09)."),
     lambda b: "grep 'tur=giris' {dosya} | head -1", False),
    ("son_zaman", ("SON giriş denemesi saat kaçta yapıldı? SS:DD:SN biçiminde yaz (örn. 14:03:09).",
                   "At what time was the LAST login attempt made? Write it as HH:MM:SS (e.g. 14:03:09)."),
     lambda b: "grep 'tur=giris' {dosya} | tail -1", False),
]

_CP_TARAYICI = [
    ("tarayici_ip", ("Hangi kaynak IP adresi EN ÇOK FARKLI hizmete dokundu? IP adresini yaz. (En çok olay üreten değil, en çok çeşitli hizmete dokunan.)",
                     "Which source IP touched the MOST DIFFERENT services? Write the IP address. (Not the one with the most events: the one touching the most varied services.)"),
     lambda b: _cp_komut(b, "grep -oE 'kaynak=[0-9.]+ hizmet=[a-z]+' {dosya} | sort -u | cut -d' ' -f1 | sort | uniq -c | sort -rn | head",
                         "jq -r '[.kaynak,.hizmet] | @tsv' {dosya} | sort -u | cut -f1 | sort | uniq -c | sort -rn | head"), True),
    ("hizmet_sayisi", ("En çok farklı hizmete dokunan kaynak kaç FARKLI hizmete dokundu? Yalnızca sayıyı yaz.",
                       "How many DIFFERENT services did the source touching the most services touch? Write only the number."),
     lambda b: "Tablonun ilk satırındaki sayı: " + _cp_komut(
         b, "grep -oE 'kaynak=[0-9.]+ hizmet=[a-z]+' {dosya} | sort -u | cut -d' ' -f1 | sort | uniq -c | sort -rn | head",
         "jq -r '[.kaynak,.hizmet] | @tsv' {dosya} | sort -u | cut -f1 | sort | uniq -c | sort -rn | head"), True),
    ("hizmet_listesi", ("En çok farklı hizmete dokunan kaynağın dokunduğu hizmetleri alfabetik sırayla, virgülle ayırarak yaz (örn. ftp,http,ssh).",
                        "Write the services touched by the source touching the most services, alphabetically, comma-separated (e.g. ftp,http,ssh)."),
     lambda b: "IP'yi bul; sonra: " + _cp_komut(
         b, "grep 'kaynak=<IP> ' {dosya} | grep -oE 'hizmet=[a-z]+' | sort -u",
         "jq -r 'select(.kaynak==\"<IP>\") | .hizmet' {dosya} | sort -u"), True),
    ("tarama_olay_sayisi", ("Kayıtta kaç 'tarama' olayı var? Yalnızca sayıyı yaz.",
                            "How many 'tarama' (scan) events are in the log? Write only the number."),
     lambda b: _cp_komut(b, "grep -c 'tur=tarama' {dosya}", "jq -r 'select(.tur==\"tarama\") | .tur' {dosya} | wc -l"), True),
    ("en_cok_olay_ip", ("Toplam olay sayısına göre en çok olay üreten kaynak IP adresini yaz.",
                        "Write the source IP that produced the most events overall."),
     lambda b: _cp_komut(b, "grep -oE 'kaynak=[0-9.]+' {dosya} | sort | uniq -c | sort -rn | head",
                         "jq -r '.kaynak' {dosya} | sort | uniq -c | sort -rn | head"), True),
    ("farkli_kaynak", ("Kayıtta kaç FARKLI kaynak IP adresi var? Yalnızca sayıyı yaz.",
                       "How many DIFFERENT source IP addresses are in the log? Write only the number."),
     lambda b: _cp_komut(b, "grep -oE 'kaynak=[0-9.]+' {dosya} | sort -u | wc -l", "jq -r '.kaynak' {dosya} | sort -u | wc -l"), True),
    ("tarama_suresi", ("İlk 'tarama' olayı ile son 'tarama' olayı arasında kaç saniye var? Yalnızca sayıyı yaz.",
                       "How many seconds are there between the first and the last 'tarama' (scan) event? Write only the number."),
     lambda b: _cp_komut(b, "grep 'tur=tarama' {dosya} | sed -n '1p;$p'  (iki satırın saatlerini çıkar)",
                         "jq -r 'select(.tur==\"tarama\") | .ts' {dosya} | sort -n | sed -n '1p;$p'  (iki değeri çıkar)"), True),
    ("ilk_tarama_hizmeti", ("İlk 'tarama' olayı hangi hizmete yapıldı? Hizmet adını yaz.",
                            "Which service did the first 'tarama' (scan) event target? Write the service name."),
     lambda b: _cp_komut(b, "grep 'tur=tarama' {dosya} | head -1",
                         "jq -r 'select(.tur==\"tarama\") | [.ts,.hizmet] | @tsv' {dosya} | sort -n | head -1"), True),
    ("son_tarama_zaman", ("SON 'tarama' olayı saat kaçta? SS:DD:SN biçiminde yaz (örn. 14:03:09).",
                          "At what time was the LAST 'tarama' (scan) event? Write it as HH:MM:SS (e.g. 14:03:09)."),
     lambda b: "grep 'tur=tarama' {dosya} | tail -1", False),
]
for _h, _tr in (("http", "http"), ("ssh", "ssh"), ("ftp", "ftp"), ("telnet", "telnet")):
    _CP_TARAYICI.append(
        (f"hizmet_kaynak_{_h}",
         (f"'{_h}' hizmetine dokunan kaç FARKLI kaynak IP adresi var? Yalnızca sayıyı yaz.",
          f"How many DIFFERENT source IP addresses touched the '{_h}' service? Write only the number."),
         (lambda h: lambda b: _cp_komut(
             b, f"grep 'hizmet={h} ' {{dosya}} | grep -oE 'kaynak=[0-9.]+' | sort -u | wc -l",
             f"jq -r 'select(.hizmet==\"{h}\") | .kaynak' {{dosya}} | sort -u | wc -l"))(_h), True))


def _cp_kayitlari(liste) -> list[dict]:
    out = []
    for tur, soru, ipucu, her_bicim in liste:
        for bicim, aciklama in CP_BICIMLERI.items():
            if bicim == "jsonl" and not her_bicim:
                continue
            ip = ipucu(bicim)
            out.append(_v(tur, bicim, soru, (ip, ip), aciklama))
    return out


def cp_cevap(kip: str, tur: str, satirlar: list[str], bicim: str) -> str:
    k = cp_ayikla(satirlar, bicim)
    giris = [x for x in k if x["tur"] == "giris"]
    tarama = sorted((x for x in k if x["tur"] == "tarama"), key=lambda x: x["ts"])
    hz_ip: dict = {}
    for x in k:
        hz_ip.setdefault(x["ip"], set()).add(x["hizmet"])

    def tarayici() -> str:
        return _en_cok({ip: len(h) for ip, h in hz_ip.items()})

    kul_sayim = _sayim(x["kullanici"] for x in giris)
    if tur == "kullanici_en_cok":
        return _en_cok(kul_sayim)
    if tur == "en_cok_sayi":
        return str(kul_sayim[_en_cok(kul_sayim)])
    if tur == "farkli_kullanici":
        return str(len(kul_sayim))
    if tur == "toplam_giris":
        return str(len(giris))
    if tur == "hizmet_en_cok":
        return _en_cok(_sayim(x["hizmet"] for x in giris))
    if tur == "kaynak_en_cok":
        return _en_cok(_sayim(x["ip"] for x in giris))
    if tur == "http_giris":
        return str(sum(1 for x in giris if x["hizmet"] == "http"))
    if tur == "ikinci_kullanici":
        return _ikinci(kul_sayim)
    if tur == "parola_en_cok":
        return _en_cok(_sayim(x["parola"] for x in giris))
    if tur == "ilk_zaman":
        return min(giris, key=lambda x: x["ts"])["zaman"]
    if tur == "son_zaman":
        return max(giris, key=lambda x: x["ts"])["zaman"]
    if tur == "tarayici_ip":
        return tarayici()
    if tur == "hizmet_sayisi":
        return str(len(hz_ip[tarayici()]))
    if tur == "hizmet_listesi":
        return ",".join(sorted(hz_ip[tarayici()]))
    if tur == "tarama_olay_sayisi":
        return str(len(tarama))
    if tur == "en_cok_olay_ip":
        return _en_cok(_sayim(x["ip"] for x in k))
    if tur == "farkli_kaynak":
        return str(len(hz_ip))
    if tur == "tarama_suresi":
        if len(tarama) < 2:
            raise Belirsiz("tarama az")
        return str(int(round(tarama[-1]["ts"] - tarama[0]["ts"])))
    if tur == "ilk_tarama_hizmeti":
        if len(tarama) > 1 and tarama[0]["ts"] == tarama[1]["ts"]:
            raise Belirsiz("esit zaman")
        return tarama[0]["hizmet"]
    if tur == "son_tarama_zaman":
        if len(tarama) > 1 and tarama[-1]["ts"] == tarama[-2]["ts"]:
            raise Belirsiz("esit zaman")
        return tarama[-1]["zaman"]
    if tur.startswith("hizmet_kaynak_"):
        h = tur.rsplit("_", 1)[1]
        n = len({x["ip"] for x in k if x["hizmet"] == h})
        if n == 0:
            raise Belirsiz("sifir")
        return str(n)
    raise ValueError(f"bilinmeyen carotpot turu: {tur}")


# ----------------------------------------------------------------------------
# Kayıtlar
# ----------------------------------------------------------------------------

KAYITLAR: dict[str, list[dict]] = {
    "ssh_saldirgan": _ssh_kayitlari(_SSH_SALDIRGAN),
    "ssh_giren": _ssh_kayitlari(_SSH_GIREN),
    "web_tarayici:ip": _web_kayitlari(_WEB_IP, True),
    "web_tarayici:yol": _web_kayitlari(_WEB_YOL, False),
    "carotpot_kayit:kullanici": _cp_kayitlari(_CP_KULLANICI),
    "carotpot_kayit:tarayici": _cp_kayitlari(_CP_TARAYICI),
}
