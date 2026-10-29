"""
CarotOS Poligon -- klasik şifreler (Sezar ailesi) ve kodlama zinciri
görevleri için soru varyantları.

Her varyant farklı bir soru sorar: sabit/bilinmeyen kaydırma, Atbash, ROT13,
ROT47, Vigenère (anahtar verilmiş / bilinmeyen / adaylardan biri), afin,
çit (rail fence), mors, A1Z26, yerine koyma, ters çevirme, şifreleme yönü...
Kodlama tarafında: katman çözme, KODLAMA, katman sayma, dıştaki katmanı
adlandırma, JSON/URL parametresi okuma, çok satırlı dosyada doğru satırı
bulma, satır sarılmış base64.

kur_sezar / kur_kodlama bir varyantın dosyalarını, doğru cevabını ve metin
yer tutucularını üretir; dosyaya yazma işi üretecidedir.

Yalnız standart kütüphane (+ flag_uretici) kullanır.
"""

from __future__ import annotations

import base64
import codecs
import gzip
import json
import random
import urllib.parse

from flag_uretici import flag_uret, parola_uret

_RNG = random.SystemRandom()
_ALFABE = "abcdefghijklmnopqrstuvwxyz"


# ----------------------------------------------------------------------------
# Şifre ilkelleri
# ----------------------------------------------------------------------------

def kaydir(metin: str, k: int) -> str:
    c = []
    for h in metin:
        if "a" <= h <= "z":
            c.append(chr((ord(h) - 97 + k) % 26 + 97))
        elif "A" <= h <= "Z":
            c.append(chr((ord(h) - 65 + k) % 26 + 65))
        else:
            c.append(h)
    return "".join(c)


def atbash(metin: str) -> str:
    c = []
    for h in metin:
        if "a" <= h <= "z":
            c.append(chr(122 - (ord(h) - 97)))
        elif "A" <= h <= "Z":
            c.append(chr(90 - (ord(h) - 65)))
        else:
            c.append(h)
    return "".join(c)


def vigenere(metin: str, anahtar: str) -> str:
    c, i = [], 0
    for h in metin:
        if "a" <= h <= "z":
            c.append(chr((ord(h) - 97 + ord(anahtar[i % len(anahtar)]) - 97) % 26 + 97))
            i += 1
        else:
            c.append(h)
    return "".join(c)


def afin(metin: str, a: int, b: int) -> str:
    c = []
    for h in metin:
        if "a" <= h <= "z":
            c.append(chr((a * (ord(h) - 97) + b) % 26 + 97))
        else:
            c.append(h)
    return "".join(c)


def rot47(metin: str) -> str:
    return "".join(chr(33 + (ord(h) - 33 + 47) % 94) if 33 <= ord(h) <= 126 else h for h in metin)


def cit_sifrele(metin: str, raylar: int) -> str:
    satirlar = [[] for _ in range(raylar)]
    r, yon = 0, 1
    for h in metin:
        satirlar[r].append(h)
        if r == 0:
            yon = 1
        elif r == raylar - 1:
            yon = -1
        r += yon
    return "".join("".join(s) for s in satirlar)


_MORS = {"a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.", "g": "--.",
         "h": "....", "i": "..", "j": ".---", "k": "-.-", "l": ".-..", "m": "--", "n": "-.",
         "o": "---", "p": ".--.", "q": "--.-", "r": ".-.", "s": "...", "t": "-", "u": "..-",
         "v": "...-", "w": ".--", "x": "-..-", "y": "-.--", "z": "--..",
         "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
         "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----."}


def mors(metin: str) -> str:
    return " ".join(_MORS[h] for h in metin)


def mors_tablosu() -> str:
    return "\n".join(f"{h} {k}" for h, k in _MORS.items()) + "\n"


# ----------------------------------------------------------------------------
# Sezar ailesi: 20 varyant
# ----------------------------------------------------------------------------

_CUMLELER = (
    "toplanti notu: sifre {k} olarak belirlendi",
    "gizli kasa kodu {k} simdi degisti",
    "bugunku giris parolasi {k} unutma",
    "yedekleme anahtari {k} dikkatle sakla",
    "sunucu odasi kapi kodu {k} yarin yenilenecek",
    "acil durum erisim sifresi {k} yalniz yoneticiye",
)
_SOZLER = ("kalkan", "poligon", "carotpot", "zafiyet", "tuzak", "yama", "kayit", "aglar",
           "sunucu", "erisim", "korsan", "sifre")
_VIG_ANAHTARLARI = ("carot", "kasa", "anahtar", "poligon", "siber", "kale", "yama", "tuzak",
                    "ag", "log", "kod", "port")
_AFIN_A = (3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25)

# (tur, zorluk etiketleri, soru tr/en, ipucu tr/en, ozet tr/en)
_S = [
    ("c3", ("kolay",),
     "{dosya} dosyasında Sezar şifresiyle (kaydırma = 3) şifrelenmiş bir mesaj var. Mesajı çöz; içinde geçen kodu (bir kelime ve 4 rakam, örn. kaplumbaga1234) yaz.",
     "The file {dosya} holds a message encrypted with the Caesar cipher (shift = 3). Decrypt it and write the code inside (a word and 4 digits, e.g. kaplumbaga1234).",
     "tr 'd-za-cD-ZA-C' 'a-zA-Z' < {dosya}   (3 harf geri)", "tr 'd-za-cD-ZA-C' 'a-zA-Z' < {dosya}   (shift back by 3)",
     "Sezar şifresi, kaydırma 3", "Caesar cipher, shift 3"),
    ("ck", ("kolay",),
     "{dosya} dosyasında Sezar şifresiyle (kaydırma = {k}) şifrelenmiş bir mesaj var. Mesajı çöz; içinde geçen kodu (bir kelime ve 4 rakam) yaz.",
     "The file {dosya} holds a message encrypted with the Caesar cipher (shift = {k}). Decrypt it and write the code inside (a word and 4 digits).",
     "Her harfi {k} geri kaydır. Örnek: tr 'a-z' 'x-za-w' (kaydırmaya göre ayarla)", "Shift every letter back by {k}. For example: tr 'a-z' 'x-za-w' (adjust to the shift)",
     "Sezar şifresi, kaydırma verilmiş", "Caesar cipher, shift given"),
    ("rot13", ("kolay",),
     "{dosya} dosyasındaki mesaj ROT13 ile şifrelenmiş. Çöz ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is encrypted with ROT13. Decrypt it and write the code inside (a word and 4 digits).",
     "tr 'A-Za-z' 'N-ZA-Mn-za-m' < {dosya}", "tr 'A-Za-z' 'N-ZA-Mn-za-m' < {dosya}",
     "ROT13", "ROT13"),
    ("atbash", ("kolay",),
     "{dosya} dosyasındaki mesaj Atbash (alfabe tersine çevrilmiş: a↔z, b↔y ...) ile şifrelenmiş. Çöz ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is encrypted with Atbash (reversed alphabet: a↔z, b↔y ...). Decrypt it and write the code inside (a word and 4 digits).",
     "tr 'a-z' 'z-a' < {dosya}", "tr 'a-z' 'z-a' < {dosya}",
     "Atbash şifresi", "Atbash cipher"),
    ("sifrele_c", ("kolay",),
     "Bu sefer SEN şifreleyeceksin: '{sozcuk}' sözcüğünü Sezar şifresiyle (kaydırma = {k}) şifrele ve şifreli sözcüğü yaz.",
     "This time YOU encrypt: encrypt the word '{sozcuk}' with the Caesar cipher (shift = {k}) and write the encrypted word.",
     "echo {sozcuk} | tr 'a-z' '<kaydırılmış alfabe>'  — her harfi {k} ileri kaydır.", "echo {sozcuk} | tr 'a-z' '<shifted alphabet>'  — shift every letter forward by {k}.",
     "Sezar ile ŞİFRELEME (yön tersine)", "Caesar ENCRYPTION (reverse direction)"),
    ("ters", ("kolay",),
     "{dosya} dosyasındaki mesaj tersten yazılmış (son harf başta). Düzelt ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is written backwards (last character first). Fix it and write the code inside (a word and 4 digits).",
     "rev {dosya}", "rev {dosya}",
     "Ters yazılmış metin", "Reversed text"),
    ("a1z26", ("orta",),
     "{dosya} dosyasında kelime A1Z26 ile (a=1, b=2 ... z=26, tire ile ayrılmış) yazılmış; '|' işaretinden sonraki 4 rakam şifresizdir. Kodu (kelime + 4 rakam, örn. kaplumbaga1234) yaz.",
     "In {dosya} the word is written with A1Z26 (a=1, b=2 ... z=26, separated by dashes); the 4 digits after '|' are plain. Write the code (word + 4 digits, e.g. kaplumbaga1234).",
     "Her sayıyı harfe çevir: 1=a ... 26=z. Örn. for n in $(cut -d'|' -f1 {dosya} | tr '-' ' '); do printf \"\\\\x$(printf %x $((n+96)))\"; done",
     "Turn every number into a letter: 1=a ... 26=z. E.g. for n in $(cut -d'|' -f1 {dosya} | tr '-' ' '); do printf \"\\\\x$(printf %x $((n+96)))\"; done",
     "A1Z26 sayı-harf", "A1Z26 number-letter"),
    ("c_bil", ("orta",),
     "{dosya} dosyasında Sezar şifresiyle şifrelenmiş bir mesaj var; kaydırma miktarı BİLİNMİYOR (1-25). Mesajı çöz; içinde geçen kodu (bir kelime ve 4 rakam) yaz.",
     "The file {dosya} holds a message encrypted with the Caesar cipher; the shift is UNKNOWN (1-25). Decrypt it and write the code inside (a word and 4 digits).",
     "25 olasılığı da dene: for k in $(seq 1 25); do ...; done  (anlamlı Türkçe çıkan satır doğrudur)", "Try all 25 possibilities: for k in $(seq 1 25); do ...; done  (the line that reads as sensible text is right)",
     "Sezar, kaydırma bilinmiyor", "Caesar, unknown shift"),
    ("c_buyuk", ("orta",),
     "{dosya} dosyasında BÜYÜK HARFLİ bir mesaj Sezar şifresiyle şifrelenmiş; kaydırma BİLİNMİYOR. Mesajı çöz; içindeki kodu (bir kelime ve 4 rakam) KÜÇÜK harflerle yaz.",
     "The file {dosya} holds an UPPERCASE message encrypted with the Caesar cipher; the shift is UNKNOWN. Decrypt it and write the code inside (a word and 4 digits) in LOWERCASE.",
     "tr kullanırken büyük harf aralığını kullan: tr 'A-Z' '<kaydırılmış A-Z>'; sonucu küçültmek için | tr 'A-Z' 'a-z'",
     "Use the uppercase range with tr: tr 'A-Z' '<shifted A-Z>'; lowercase the result with | tr 'A-Z' 'a-z'",
     "Sezar, büyük harfli, bilinmeyen kaydırma", "Caesar, uppercase, unknown shift"),
    ("c_satir", ("orta",),
     "{dosya} dosyasının SATIRLARININ hepsi aynı Sezar kaydırmasıyla (bilinmiyor, 1-25) şifrelenmiş. 'kod' ile başlayan satırı bul, çöz ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "ALL LINES of {dosya} are encrypted with the same unknown Caesar shift (1-25). Find the line that starts with 'kod', decrypt it and write the code inside (a word and 4 digits).",
     "Önce kaydırmayı ilk satırlardan bul; sonra: grep -n '' {dosya}  ve çözülmüş satırlarda 'kod' ile başlayanı ara.", "First find the shift from the first lines; then: grep -n '' {dosya}  and look for the decrypted line starting with 'kod'.",
     "Çok satırlı Sezar, doğru satırı bul", "Multi-line Caesar, find the right line"),
    ("vig_anahtar", ("orta",),
     "{dosya} dosyasındaki mesaj Vigenère şifresiyle şifrelenmiş; anahtar = {anahtar}. Çöz ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is encrypted with the Vigenère cipher; key = {anahtar}. Decrypt it and write the code inside (a word and 4 digits).",
     "Her harf için anahtarın sıradaki harfi kadar geri kaydır (a=0, b=1 ...). Bir betikle yapmak kolaydır.", "For each letter shift back by the next key letter (a=0, b=1 ...). Easiest with a short script.",
     "Vigenère, anahtar verilmiş", "Vigenère, key given"),
    ("afin", ("orta",),
     "{dosya} dosyasındaki mesaj afin şifresiyle şifrelenmiş: şifreli = (a·harf + b) mod 26 (a=0 ... z=25), a = {a}, b = {b}. Çöz ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is encrypted with an affine cipher: cipher = (a·letter + b) mod 26 (a=0 ... z=25), a = {a}, b = {b}. Decrypt it and write the code inside (a word and 4 digits).",
     "Çözme: harf = a⁻¹·(şifreli − b) mod 26. a⁻¹: a·a⁻¹ ≡ 1 (mod 26) olan sayıdır; 1-25 arasını deneyerek bulabilirsin.", "Decryption: letter = a⁻¹·(cipher − b) mod 26, where a·a⁻¹ ≡ 1 (mod 26); find it by trying 1-25.",
     "Afin şifre, a ve b verilmiş", "Affine cipher, a and b given"),
    ("rot47", ("orta", "zor"),
     "{dosya} dosyasındaki mesaj ROT47 ile (yazdırılabilir ASCII, ! ... ~) şifrelenmiş; rakamlar ve noktalama da değişir. Çöz ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is encrypted with ROT47 (printable ASCII, ! ... ~); digits and punctuation change too. Decrypt it and write the code inside (a word and 4 digits).",
     "tr '!-~' 'P-~!-O' < {dosya}", "tr '!-~' 'P-~!-O' < {dosya}",
     "ROT47", "ROT47"),
    ("mors", ("orta", "zor"),
     "{dosya} dosyasında kod Mors alfabesiyle yazılmış (harfler boşlukla ayrılmış). Mors tablosu {tablo} dosyasında. Kodu (bir kelime ve 4 rakam) yaz.",
     "In {dosya} the code is written in Morse code (letters separated by spaces). The Morse table is in {tablo}. Write the code (a word and 4 digits).",
     "Tabloyu kullanarak her işareti harfe/rakama çevir: cat {tablo}", "Use the table to turn every symbol into a letter/digit: cat {tablo}",
     "Mors alfabesi (tabloyla)", "Morse code (with a table)"),
    ("yerine", ("orta", "zor"),
     "{dosya} dosyasındaki mesaj bir yerine koyma şifresiyle şifrelenmiş (her harf başka bir harfle değişmiş). Eşleme {tablo} dosyasında. Çöz ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is encrypted with a substitution cipher (every letter replaced by another). The mapping is in {tablo}. Decrypt it and write the code inside (a word and 4 digits).",
     "cat {tablo}  → iki satırı karşılaştır; sonra: tr '<şifreli alfabe>' 'a-z' < {dosya}", "cat {tablo}  → compare the two lines; then: tr '<cipher alphabet>' 'a-z' < {dosya}",
     "Yerine koyma şifresi (tabloyla)", "Substitution cipher (with a table)"),
    ("vig_bilinmeyen", ("zor",),
     "{dosya} dosyasındaki mesaj Vigenère şifresiyle şifrelenmiş; anahtar BİLİNMİYOR (3 harf). Mesajın başı bilinir: 'toplanti notu: sifre'. Anahtarı bulup mesajı çöz; içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is encrypted with the Vigenère cipher; the key is UNKNOWN (3 letters). The start of the message is known: 'toplanti notu: sifre'. Recover the key, decrypt the message and write the code inside (a word and 4 digits).",
     "Şifreli ilk harflerden bilinen düz metni çıkar: anahtar harfi = şifreli − düz (mod 26); 3 harf bulunca tekrar eder.", "Subtract the known plaintext from the first cipher letters: key letter = cipher − plain (mod 26); it repeats after 3 letters.",
     "Vigenère, bilinen düz metinle anahtar bulma", "Vigenère, key recovery with known plaintext"),
    ("vig_liste", ("zor",),
     "{dosya} dosyasındaki mesaj Vigenère şifresiyle şifrelenmiş. Anahtar {tablo} dosyasındaki 12 aday kelimeden biri. Doğrusunu bulup mesajı çöz; içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is encrypted with the Vigenère cipher. The key is one of the 12 candidate words in {tablo}. Find the right one, decrypt the message and write the code inside (a word and 4 digits).",
     "Her aday anahtarı sırayla dene; anlamlı Türkçe çıkan doğrudur: while read k; do ...; done < {tablo}", "Try every candidate key in turn; the one giving sensible text is right: while read k; do ...; done < {tablo}",
     "Vigenère, anahtar listeden", "Vigenère, key from a list"),
    ("c_base64", ("zor",),
     "{dosya} dosyasındaki mesaj ÖNCE Sezar şifresiyle (kaydırma = {k}), SONRA base64 ile kodlanmış. Önce base64'ü aç, sonra Sezar'ı çöz; içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} was encrypted FIRST with the Caesar cipher (shift = {k}) and THEN encoded with base64. Undo base64 first, then the Caesar cipher; write the code inside (a word and 4 digits).",
     "base64 -d {dosya}  → sonra çıkan metni {k} harf geri kaydır.", "base64 -d {dosya}  → then shift the resulting text back by {k}.",
     "Sezar + base64 zinciri", "Caesar + base64 chain"),
    ("cit", ("zor",),
     "{dosya} dosyasındaki mesaj 3 raylı çit (rail fence) şifresiyle şifrelenmiş: düz metin ray 1, 2, 3, 2, 1, 2, 3... sırasıyla dağıtılmış, raylar sırayla okunmuş. Çöz ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} is encrypted with a 3-rail fence cipher: plaintext is placed on rails 1, 2, 3, 2, 1, 2, 3... and the rails read one after the other. Decrypt it and write the code inside (a word and 4 digits).",
     "Metin uzunluğundan her rayın uzunluğunu hesapla, rayları ayır, sonra zikzak sırasıyla yeniden birleştir (kısa bir betik).", "From the text length work out each rail's length, split the rails, then rebuild in zigzag order (a short script).",
     "Çit (rail fence) şifresi", "Rail fence cipher"),
    ("ters_c", ("zor",),
     "{dosya} dosyasındaki mesaj ÖNCE ters çevrilmiş, SONRA Sezar şifresiyle (kaydırma = {k}) şifrelenmiş. İşlemleri tersten uygula ve içindeki kodu (bir kelime ve 4 rakam) yaz.",
     "The message in {dosya} was reversed FIRST and then encrypted with the Caesar cipher (shift = {k}). Undo the steps in reverse order and write the code inside (a word and 4 digits).",
     "Önce Sezar'ı çöz, sonra ters çevir: ... | rev", "Undo the Caesar cipher first, then reverse: ... | rev",
     "Ters çevirme + Sezar zinciri", "Reverse + Caesar chain"),
]

SEZAR_TURLERI = [s[0] for s in _S]


def _sezar_kayitlari() -> list[dict]:
    out = []
    for tur, zorluk, st, se, it, ie, ot, oe in _S:
        out.append({"tur": tur, "zorluk": zorluk, "soru": {"tr": st, "en": se},
                    "ipucu": {"tr": it, "en": ie}, "ozet": {"tr": ot, "en": oe}})
    return out


def _uyar(metin: str, d: dict) -> str:
    for a, b in d.items():
        metin = metin.replace(a, str(b))
    return metin


def kur_sezar(v: dict) -> dict:
    """Varyanta göre dosyaları/cevabı hazırlar.
    Döner: {cevap, dosyalar: {ad: metin}, dosya: ana dosya adı, yer: {yer tutucu: değer}, gizli}"""
    tur = v["tur"]
    parola = parola_uret()
    kelime, rakam = parola[:-4], parola[-4:]
    mesaj = _RNG.choice(_CUMLELER).format(k=parola)
    yer: dict[str, str] = {}
    dosyalar: dict[str, str] = {}
    gizli: dict = {}
    cevap = parola
    ana = "mesaj.txt"
    if tur == "c3":
        icerik = kaydir(mesaj, 3)
    elif tur == "ck":
        k = _RNG.randint(4, 25)
        yer["{k}"] = str(k)
        gizli["k"] = k
        icerik = kaydir(mesaj, k)
    elif tur == "rot13":
        icerik = codecs.encode(mesaj, "rot13")
    elif tur == "atbash":
        icerik = atbash(mesaj)
    elif tur == "sifrele_c":
        k = _RNG.randint(2, 25)
        sozcuk = _RNG.choice(_SOZLER)
        yer.update({"{k}": str(k), "{sozcuk}": sozcuk})
        gizli.update({"k": k, "sozcuk": sozcuk})
        cevap = kaydir(sozcuk, k)
        icerik = "(bu görevde dosya yok / no file in this task)"
        ana = None
    elif tur == "ters":
        icerik = mesaj[::-1]
    elif tur == "a1z26":
        icerik = "-".join(str(ord(h) - 96) for h in kelime) + " | " + rakam
    elif tur == "c_bil":
        k = _RNG.randint(1, 25)
        gizli["k"] = k
        icerik = kaydir(mesaj, k)
    elif tur == "c_buyuk":
        k = _RNG.randint(1, 25)
        gizli["k"] = k
        icerik = kaydir(mesaj.upper(), k)
    elif tur == "c_satir":
        k = _RNG.randint(1, 25)
        gizli["k"] = k
        satirlar = [f"{_RNG.choice(_SOZLER)} {_RNG.choice(_SOZLER)} {_RNG.choice(_SOZLER)} "
                    f"{_RNG.randint(100, 999)}" for _ in range(8)]
        satirlar.insert(_RNG.randint(0, len(satirlar)), f"kod {parola}")
        icerik = "\n".join(kaydir(s, k) for s in satirlar)
    elif tur == "vig_anahtar":
        anahtar = _RNG.choice(_VIG_ANAHTARLARI)
        yer["{anahtar}"] = anahtar
        gizli["anahtar"] = anahtar
        icerik = vigenere(mesaj, anahtar)
    elif tur == "afin":
        a, b = _RNG.choice(_AFIN_A), _RNG.randint(1, 25)
        yer.update({"{a}": str(a), "{b}": str(b)})
        gizli.update({"a": a, "b": b})
        icerik = afin(mesaj, a, b)
    elif tur == "rot47":
        icerik = rot47(mesaj)
    elif tur == "mors":
        dosyalar["mors_tablosu.txt"] = mors_tablosu()
        yer["{tablo}"] = "mors_tablosu.txt"
        icerik = mors(parola)
    elif tur == "yerine":
        perm = list(_ALFABE)
        while True:
            _RNG.shuffle(perm)
            if all(p != a for p, a in zip(perm, _ALFABE)):
                break
        sifreli_alfabe = "".join(perm)
        gizli["alfabe"] = sifreli_alfabe
        dosyalar["eslesme.txt"] = f"duz:     {_ALFABE}\nsifreli: {sifreli_alfabe}\n"
        yer["{tablo}"] = "eslesme.txt"
        icerik = "".join(sifreli_alfabe[_ALFABE.index(h)] if h in _ALFABE else h for h in mesaj)
    elif tur == "vig_bilinmeyen":
        anahtar = "".join(_RNG.choice(_ALFABE) for _ in range(3))
        gizli["anahtar"] = anahtar
        mesaj = f"toplanti notu: sifre {parola} olarak belirlendi"
        icerik = vigenere(mesaj, anahtar)
    elif tur == "vig_liste":
        adaylar = _RNG.sample(_VIG_ANAHTARLARI, 12)
        anahtar = _RNG.choice(adaylar)
        gizli["anahtar"] = anahtar
        dosyalar["anahtarlar.txt"] = "\n".join(adaylar) + "\n"
        yer["{tablo}"] = "anahtarlar.txt"
        icerik = vigenere(mesaj, anahtar)
    elif tur == "c_base64":
        k = _RNG.randint(2, 25)
        yer["{k}"] = str(k)
        gizli["k"] = k
        icerik = base64.b64encode(kaydir(mesaj, k).encode()).decode()
    elif tur == "cit":
        gizli["raylar"] = 3
        icerik = cit_sifrele(mesaj, 3)
    elif tur == "ters_c":
        k = _RNG.randint(2, 25)
        yer["{k}"] = str(k)
        gizli["k"] = k
        icerik = kaydir(mesaj[::-1], k)
    else:
        raise ValueError(f"bilinmeyen sezar turu: {tur}")
    if ana:
        dosyalar[ana] = icerik + "\n"
    return {"cevap": cevap, "dosyalar": dosyalar, "dosya": ana, "yer": yer, "gizli": gizli,
            "parola": parola}


# ----------------------------------------------------------------------------
# Kodlama zinciri: 20 varyant
# ----------------------------------------------------------------------------

def _rot13(b: bytes) -> bytes:
    return codecs.encode(b.decode("ascii"), "rot13").encode("ascii")


KATMANLAR = {
    "base64": lambda b: base64.b64encode(b),
    "base32": lambda b: base64.b32encode(b),
    "hex": lambda b: b.hex().encode(),
    "rot13": _rot13,
    "url": lambda b: "".join(f"%{c:02x}" for c in b).encode(),
    "gzip": lambda b: gzip.compress(b, mtime=0),
}
_METIN_KATMANLARI = ("base64", "hex", "base32", "rot13")
_KOMUT = {"base64": "base64 -d", "hex": "xxd -r -p", "base32": "base32 -d", "rot13": "tr 'A-Za-z' 'N-ZA-Mn-za-m'",
          "url": "python3 -c \"import sys,urllib.parse as u;sys.stdout.buffer.write(u.unquote_to_bytes(sys.stdin.read()))\"",
          "gzip": "zcat"}
_KOMUT_KODLA = {"base64": "base64 -w0", "hex": "xxd -p | tr -d '\\n'", "base32": "base32 -w0",
                "rot13": "tr 'A-Za-z' 'N-ZA-Mn-za-m'"}

_KODLA_SOZ = ("kalkan", "poligon", "carotpot", "tuzak", "kayit", "zafiyet", "sunucu", "yama")

# (tur, zorluk, parametre sözlüğü, soru tr, soru en, ipucu tr, ipucu en, özet tr, özet en)
_K = [
    ("coz", ("kolay",), {"n": 1, "adlar": "sirali"},
     "{dosya} dosyasının içinde CAROT{...} biçiminde bir bayrak var ama 1 kat kodlanmış (kodlama: {katmanlar}). Aç ve bayrağı yaz.",
     "The file {dosya} holds a flag in the form CAROT{...} but it is encoded in 1 layer (encoding: {katmanlar}). Decode it and write the flag.",
     "Örnek: {komutlar}", "Example: {komutlar}", "1 katman çözme, ad verilmiş", "Decode 1 layer, name given"),
    ("coz", ("kolay",), {"n": 2, "adlar": "sirali"},
     "{dosya} dosyasının içinde CAROT{...} biçiminde bir bayrak var ama 2 kat kodlanmış. Katmanlar (dıştan içe): {katmanlar}. Hepsini aç ve bayrağı yaz.",
     "The file {dosya} holds a flag in the form CAROT{...} but it is encoded in 2 layers. Layers (outside in): {katmanlar}. Decode them all and write the flag.",
     "Boru hattıyla: {komutlar}", "With a pipeline: {komutlar}", "2 katman çözme, sıra verilmiş", "Decode 2 layers, order given"),
    ("coz", ("kolay", "orta"), {"n": 2, "adlar": "karisik"},
     "{dosya} dosyasının içinde CAROT{...} biçiminde bir bayrak var ama 2 kat kodlanmış. Kullanılan kodlamalar (SIRASIZ): {katmanlar}. Sırayı bulup hepsini aç ve bayrağı yaz.",
     "The file {dosya} holds a flag in the form CAROT{...} but it is encoded in 2 layers. The encodings used (UNORDERED): {katmanlar}. Work out the order, decode them all and write the flag.",
     "Dosyaya bakarak dıştaki kodlamayı tanı (base64: A-Z a-z 0-9 + / =; hex: yalnız 0-9 a-f ...).", "Recognise the outer encoding from the file (base64: A-Z a-z 0-9 + / =; hex: only 0-9 a-f ...).",
     "2 katman, sıra bilinmiyor", "2 layers, order unknown"),
    ("coz", ("orta",), {"n": 3, "adlar": "sirali"},
     "{dosya} dosyasının içinde CAROT{...} biçiminde bir bayrak var ama 3 kat kodlanmış. Katmanlar (dıştan içe): {katmanlar}. Hepsini aç ve bayrağı yaz.",
     "The file {dosya} holds a flag in the form CAROT{...} but it is encoded in 3 layers. Layers (outside in): {katmanlar}. Decode them all and write the flag.",
     "Boru hattıyla: {komutlar}", "With a pipeline: {komutlar}", "3 katman çözme, sıra verilmiş", "Decode 3 layers, order given"),
    ("coz", ("orta",), {"n": 3, "adlar": "karisik"},
     "{dosya} dosyasının içinde CAROT{...} biçiminde bir bayrak var ama 3 kat kodlanmış. Kullanılan kodlamalar (SIRASIZ): {katmanlar}. Sırayı bulup hepsini aç ve bayrağı yaz.",
     "The file {dosya} holds a flag in the form CAROT{...} but it is encoded in 3 layers. The encodings used (UNORDERED): {katmanlar}. Work out the order, decode them all and write the flag.",
     "Her adımda dosyanın görünüşüne bak ve hangi kodlama olduğunu tanı; sonra bir üst katmana geç.", "At each step look at the file and recognise the encoding; then move to the next layer.",
     "3 katman, sıra bilinmiyor", "3 layers, order unknown"),
    ("coz", ("orta", "zor"), {"n": 3, "adlar": "yok"},
     "{dosya} dosyasının içinde CAROT{...} biçiminde bir bayrak var ama 3 kat kodlanmış ve hangi kodlamalar olduğu SÖYLENMİYOR. Katmanları kendin tanıyıp aç ve bayrağı yaz.",
     "The file {dosya} holds a flag in the form CAROT{...} but it is encoded in 3 layers and the encodings are NOT stated. Recognise the layers yourself, decode them and write the flag.",
     "file {dosya} ve head -c 100 {dosya} ile içeriğe bak; gzip ise 'gzip compressed data' der.", "Look at the content with file {dosya} and head -c 100 {dosya}; gzip is reported as 'gzip compressed data'.",
     "3 katman, ad verilmemiş", "3 layers, names not given"),
    ("coz", ("zor",), {"n": 4, "adlar": "karisik"},
     "{dosya} dosyasının içinde CAROT{...} biçiminde bir bayrak var ama 4 kat kodlanmış. Kullanılan kodlamalar (SIRASIZ): {katmanlar}. Sırayı bulup hepsini aç ve bayrağı yaz.",
     "The file {dosya} holds a flag in the form CAROT{...} but it is encoded in 4 layers. The encodings used (UNORDERED): {katmanlar}. Work out the order, decode them all and write the flag.",
     "Her katmandan sonra çıktıyı bir dosyaya yaz ve tanı: ... > adim1.bin; file adim1.bin", "After every layer write the output to a file and recognise it: ... > step1.bin; file step1.bin",
     "4 katman, sıra bilinmiyor", "4 layers, order unknown"),
    ("coz", ("zor",), {"n": 5, "adlar": "yok"},
     "{dosya} dosyasının içinde CAROT{...} biçiminde bir bayrak var ama 5 kat kodlanmış ve hangi kodlamalar olduğu SÖYLENMİYOR. Katmanları kendin tanıyıp aç ve bayrağı yaz.",
     "The file {dosya} holds a flag in the form CAROT{...} but it is encoded in 5 layers and the encodings are NOT stated. Recognise the layers yourself, decode them and write the flag.",
     "Her adımda: dosyanın türü (file) ve ilk baytlar (xxd | head) hangi kodlama olduğunu söyler.", "At each step: the file type (file) and the first bytes (xxd | head) tell you which encoding it is.",
     "5 katman, ad verilmemiş", "5 layers, names not given"),
    ("kodla", ("kolay",), {"zincir": ["base64"]},
     "Bu sefer SEN kodlayacaksın: '{sozcuk}' sözcüğünü base64 ile kodla ve sonucu (tek satır, sonda satır sonu olmadan) yaz.",
     "This time YOU encode: encode the word '{sozcuk}' with base64 and write the result (one line, no trailing newline).",
     "printf %s '{sozcuk}' | base64 -w0", "printf %s '{sozcuk}' | base64 -w0", "base64 ile KODLAMA", "ENCODING with base64"),
    ("kodla", ("kolay",), {"zincir": ["hex"]},
     "Bu sefer SEN kodlayacaksın: '{sozcuk}' sözcüğünü onaltılık (hex, küçük harf) kodla ve sonucu (tek satır) yaz.",
     "This time YOU encode: encode the word '{sozcuk}' as hexadecimal (lowercase) and write the result (one line).",
     "printf %s '{sozcuk}' | xxd -p | tr -d '\\n'", "printf %s '{sozcuk}' | xxd -p | tr -d '\\n'", "hex ile KODLAMA", "ENCODING as hex"),
    ("kodla", ("orta",), {"zincir": ["base64", "hex"]},
     "'{sozcuk}' sözcüğünü SIRASIYLA önce base64, sonra hex (küçük harf) ile kodla ve sonucu (tek satır) yaz.",
     "Encode the word '{sozcuk}' IN ORDER: first base64, then hex (lowercase), and write the result (one line).",
     "printf %s '{sozcuk}' | base64 -w0 | xxd -p | tr -d '\\n'", "printf %s '{sozcuk}' | base64 -w0 | xxd -p | tr -d '\\n'", "base64 sonra hex ile KODLAMA", "ENCODING with base64 then hex"),
    ("kodla", ("orta",), {"zincir": ["rot13", "base64"]},
     "'{sozcuk}' sözcüğünü SIRASIYLA önce ROT13, sonra base64 ile kodla ve sonucu (tek satır) yaz.",
     "Encode the word '{sozcuk}' IN ORDER: first ROT13, then base64, and write the result (one line).",
     "printf %s '{sozcuk}' | tr 'A-Za-z' 'N-ZA-Mn-za-m' | base64 -w0", "printf %s '{sozcuk}' | tr 'A-Za-z' 'N-ZA-Mn-za-m' | base64 -w0", "ROT13 sonra base64 ile KODLAMA", "ENCODING with ROT13 then base64"),
    ("kodla", ("orta", "zor"), {"zincir": ["base64", "base32"]},
     "'{sozcuk}' sözcüğünü SIRASIYLA önce base64, sonra base32 ile kodla ve sonucu (tek satır, '=' dolgusu dahil) yaz.",
     "Encode the word '{sozcuk}' IN ORDER: first base64, then base32, and write the result (one line, including '=' padding).",
     "printf %s '{sozcuk}' | base64 -w0 | base32 -w0", "printf %s '{sozcuk}' | base64 -w0 | base32 -w0", "base64 sonra base32 ile KODLAMA", "ENCODING with base64 then base32"),
    ("say", ("orta",), {"n": 3, "adlar": "yok"},
     "{dosya} dosyası birden çok katman kodlanmış (base64, hex, base32, rot13, gzip, url karışık). Bayrağa (CAROT{...}) ulaşana kadar kaç katman açman gerekti? Yalnızca sayıyı yaz.",
     "The file {dosya} is encoded in several layers (a mix of base64, hex, base32, rot13, gzip, url). How many layers did you have to undo to reach the flag (CAROT{...})? Write only the number.",
     "Her katmanı aç, kaç adım olduğunu say; CAROT{ görünce dur.", "Undo each layer and count the steps; stop when you see CAROT{.",
     "Kaç katman olduğunu say", "Count the layers"),
    ("ilk", ("orta",), {"n": 3, "adlar": "yok"},
     "{dosya} dosyası birden çok katman kodlanmış. EN DIŞTAKİ kodlama hangisi? Şunlardan birini yaz: base64, hex, base32, rot13, gzip, url.",
     "The file {dosya} is encoded in several layers. Which is the OUTERMOST encoding? Write one of: base64, hex, base32, rot13, gzip, url.",
     "file {dosya} ve head -c 80 {dosya} ile dosyaya bak; karakter kümesi hangi kodlama olduğunu belli eder.", "Look at the file with file {dosya} and head -c 80 {dosya}; the character set shows which encoding it is.",
     "Dıştaki kodlamayı adlandır", "Name the outermost encoding"),
    ("dis", ("kolay", "orta"), {"n": 2, "adlar": "yok"},
     "{dosya} dosyası 2 kat kodlanmış; dıştaki kodlama {dis}. YALNIZCA bu en dıştaki katmanı aç ve ortaya çıkan metni (henüz bayrak değil) olduğu gibi yaz.",
     "The file {dosya} is encoded in 2 layers; the outer encoding is {dis}. Undo ONLY this outermost layer and write the resulting text (not yet the flag) exactly as it is.",
     "{komutlar}", "{komutlar}", "Yalnız dıştaki katmanı aç", "Undo only the outer layer"),
    ("json", ("orta",), {"n": 2, "adlar": "karisik"},
     "{dosya} dosyası 2 kat kodlanmış (kodlamalar, SIRASIZ: {katmanlar}); içinden çıkan şey bir JSON nesnesi. 'token' alanının değerini (CAROT{...}) yaz.",
     "The file {dosya} is encoded in 2 layers (encodings, UNORDERED: {katmanlar}); the result is a JSON object. Write the value of its 'token' field (CAROT{...}).",
     "Açtıktan sonra: ... | jq -r .token", "After decoding: ... | jq -r .token", "Kodlanmış JSON'dan alan oku", "Read a field from encoded JSON"),
    ("url", ("orta", "zor"), {"n": 1, "adlar": "yok"},
     "{dosya} dosyasında URL kodlamalı bir sorgu dizesi var (a=...&sifre=...&b=...). 'sifre' parametresinin ÇÖZÜLMÜŞ değerini (CAROT{...}) yaz.",
     "The file {dosya} holds a URL-encoded query string (a=...&sifre=...&b=...). Write the DECODED value of the 'sifre' parameter (CAROT{...}).",
     "tr '&' '\\n' < {dosya} | grep '^sifre='  → sonra %xx dizilerini çöz (python3 -c ... urllib.parse.unquote).", "tr '&' '\\n' < {dosya} | grep '^sifre='  → then decode the %xx sequences (python3 -c ... urllib.parse.unquote).",
     "URL parametresi çözme", "Decode a URL parameter"),
    ("satir", ("kolay", "orta"), {"n": 1, "adlar": "yok"},
     "{dosya} dosyasının 6 satırı var; her biri base64, hex, base32 veya rot13 ile kodlanmış. Satırlardan YALNIZ BİRİ CAROT{...} bayrağına çözülür (diğerleri NOTFLAG{...}). Bayrağı yaz.",
     "The file {dosya} has 6 lines, each encoded with base64, hex, base32 or rot13. ONLY ONE line decodes to a CAROT{...} flag (the others decode to NOTFLAG{...}). Write the flag.",
     "Her satırı sırayla tüm kodlamalarla dene; çözülünce 'CAROT{' ya da 'NOTFLAG{' çıkar. while read s; do ...; done < {dosya}", "Try each line with every encoding; a successful decode shows 'CAROT{' or 'NOTFLAG{'. while read s; do ...; done < {dosya}",
     "6 satırdan doğru olanı bul", "Find the right one of 6 lines"),
    ("sarili", ("kolay", "orta"), {"n": 2, "adlar": "sirali"},
     "{dosya} dosyasının içinde CAROT{...} bayrağı 2 kat kodlanmış; satırlar 40 karakterde sarılmış. Katmanlar (dıştan içe): {katmanlar}. Satır sonlarını temizleyip aç ve bayrağı yaz.",
     "The file {dosya} holds a CAROT{...} flag encoded in 2 layers; lines are wrapped at 40 characters. Layers (outside in): {katmanlar}. Remove the line breaks, decode and write the flag.",
     "tr -d '\\n' < {dosya} | ...", "tr -d '\\n' < {dosya} | ...", "Satırları sarılmış kodlama", "Line-wrapped encoding"),
]

KODLAMA_TURLERI = [k[0] for k in _K]


def _kodlama_kayitlari() -> list[dict]:
    out = []
    for tur, zorluk, par, st, se, it, ie, ot, oe in _K:
        out.append({"tur": tur, "zorluk": zorluk, "par": par, "soru": {"tr": st, "en": se},
                    "ipucu": {"tr": it, "en": ie}, "ozet": {"tr": ot, "en": oe}})
    return out


def _zincir_kur(n: int, havuz_adlari, sadece_metin: bool = False, deger: bytes | None = None):
    """İçten dışa kodlar; aynı katman art arda gelmez, rot13 en çok bir kez ve yalnız ASCII
    metne uygulanır. Döner: (veri, içten-dışa katman adları)."""
    havuz = [k for k in havuz_adlari]
    veri = deger
    secilen: list[str] = []
    while len(secilen) < n:
        k = _RNG.choice(havuz)
        if secilen and secilen[-1] == k:
            continue
        if k == "rot13" and ("rot13" in secilen or not veri.isascii()):
            continue
        yeni = KATMANLAR[k](veri)
        if yeni == veri:       # etkisiz katman (orn. yalniz rakam iceren metinde rot13)
            continue           # ogrenci onu goremez; sayim/ad sorulari yanlis olurdu
        veri = yeni
        secilen.append(k)
    return veri, secilen


def _havuz(n: int) -> tuple:
    if n == 1:
        return ("base64", "hex", "base32", "rot13")
    if n <= 3:
        return ("base64", "hex", "base32", "rot13", "gzip")
    return ("base64", "hex", "base32", "rot13", "gzip", "url")


def _katman_metni(dis_sira: list[str], mod: str) -> str:
    if mod == "sirali":
        return " → ".join(dis_sira)
    if mod == "karisik":
        k = sorted(set(dis_sira))
        _RNG.shuffle(k)
        return ", ".join(k)
    return "?"


def _komutlar(dis_sira: list[str], dosya_yer: str = "{dosya}") -> str:
    parca = [f"cat {dosya_yer}"] + [_KOMUT[a] for a in dis_sira]
    return " | ".join(parca)


def kur_kodlama(v: dict) -> dict:
    """Kodlama varyantı: {cevap, dosyalar, dosya, yer, gizli}."""
    tur, par = v["tur"], v.get("par", {})
    yer: dict[str, str] = {}
    gizli: dict = {}
    dosyalar: dict[str, bytes | str] = {}
    ana = "gizli.dat"
    if tur in ("coz", "say", "ilk", "dis", "sarili"):
        n = _RNG.randint(2, 5) if tur == "say" else par["n"]
        bayrak = flag_uret()
        if tur in ("dis", "sarili"):       # satir sarma ikili (gzip) veriyi bozar
            havuz = _METIN_KATMANLARI
            veri, secilen = _zincir_kur(n, havuz, True, bayrak.encode())
        else:
            veri, secilen = _zincir_kur(n, _havuz(n), False, bayrak.encode())
        dis_sira = list(reversed(secilen))
        gizli = {"katmanlar": dis_sira}
        yer["{katmanlar}"] = _katman_metni(dis_sira, par["adlar"])
        yer["{katman_sayisi}"] = str(n)
        yer["{komutlar}"] = _komutlar(dis_sira)
        cevap = bayrak
        if tur == "say":
            cevap = str(len(dis_sira))
        elif tur == "ilk":
            cevap = dis_sira[0]
        elif tur == "dis":
            yer["{dis}"] = dis_sira[0]
            yer["{komutlar}"] = f"cat {{dosya}} | {_KOMUT[dis_sira[0]]}"
            # dıştaki katmanı açınca çıkan metin içteki katmanın çıktısıdır
            cevap = _dis_ac(veri, dis_sira[0]).decode("ascii")
        elif tur == "sarili":
            veri = b"\n".join(veri[i:i + 40] for i in range(0, len(veri), 40))
        dosyalar[ana] = veri
    elif tur == "kodla":
        sozcuk = _RNG.choice(_KODLA_SOZ) + str(_RNG.randint(10, 99))
        yer["{sozcuk}"] = sozcuk
        veri = sozcuk.encode()
        for k in par["zincir"]:
            veri = KATMANLAR[k](veri)
        cevap = veri.decode("ascii")
        ana = None
        gizli = {"zincir": par["zincir"], "sozcuk": sozcuk}
    elif tur == "json":
        bayrak = flag_uret()
        obj = {"kullanici": _RNG.choice(("ayse", "mehmet", "zeynep", "can")), "rol": "okuyucu",
               "token": bayrak, "gecerlilik": _RNG.randint(1, 30)}
        veri = json.dumps(obj, ensure_ascii=False).encode()
        veri, secilen = _zincir_kur(2, _METIN_KATMANLARI, True, veri)
        dis_sira = list(reversed(secilen))
        gizli = {"katmanlar": dis_sira}
        yer["{katmanlar}"] = _katman_metni(dis_sira, "karisik")
        cevap = bayrak
        dosyalar[ana] = veri
    elif tur == "url":
        bayrak = flag_uret()
        kuyruk = [f"a={_RNG.randint(1, 99)}", f"b={_RNG.choice(('x', 'y', 'z'))}{_RNG.randint(1, 99)}"]
        sorgu = "&".join([kuyruk[0], "sifre=" + urllib.parse.quote(bayrak, safe=""), kuyruk[1]])
        cevap = bayrak
        dosyalar[ana] = sorgu.encode()
    elif tur == "satir":
        bayrak = flag_uret()
        hedef = _RNG.randrange(6)
        satirlar = []
        for i in range(6):
            metin = bayrak if i == hedef else f"NOTFLAG{{{_RNG.randbytes(4).hex()}}}"
            k = _RNG.choice(_METIN_KATMANLARI)
            satirlar.append(KATMANLAR[k](metin.encode()))
        cevap = bayrak
        dosyalar[ana] = b"\n".join(satirlar)
    else:
        raise ValueError(f"bilinmeyen kodlama turu: {tur}")
    return {"cevap": cevap, "dosyalar": dosyalar, "dosya": ana, "yer": yer, "gizli": gizli}


def _dis_ac(veri: bytes, ad: str) -> bytes:
    if ad == "base64":
        return base64.b64decode(veri)
    if ad == "base32":
        return base64.b32decode(veri)
    if ad == "hex":
        return bytes.fromhex(veri.decode("ascii"))
    if ad == "rot13":
        return _rot13(veri)
    raise ValueError(ad)


def metni_uyar(metin: str, yer: dict) -> str:
    return _uyar(metin, yer)


KAYITLAR: dict[str, list[dict]] = {
    "sezar": _sezar_kayitlari(),
    "kodlama_zinciri": _kodlama_kayitlari(),
}
