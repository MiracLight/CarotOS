# -*- coding: utf-8 -*-
"""CarotOS Komut Açıklayıcı: bir komut satırını ÇALIŞTIRMADAN ayrıştırıp ne yaptığını açıklar.

Yapay zekâ yok: veri tabanı (veri_*.py) araç başına özet, bayrak açıklamaları, gürültü ve yetki
bilgisi taşır; tehlikeli kalıplar (veri_tehlike.py) kurallarla yakalanır. Hiçbir zaman komutu çalıştırmaz,
yalnızca ayrıştırır. Bilinmeyen komut/bayrakta dürüstçe "tanımıyorum" der.

Sınırlar (bilerek): değişkenlerin ($X) değeri, takma adlar (alias) ve `$(...)` çıktısı bilinmez; `$(...)`,
ters tırnak, `<(...)`, `sh -c`, `eval`, `find -exec` gibi yerlerdeki iç komutlar ayrı parça olarak açıklanır.
Çözemediği bir yapıda bunu açıkça söyler ("çözümleyemedim"); eksik açıklamayı tam gibi sunmaz.
Yalnızca bash söz dizimi; yerel çalışır, hiçbir şey gönderilmez.

GTK'siz, yalnızca standart kütüphane (+ ortak/dil.py).
"""
from __future__ import annotations

import os
import re
import shlex
import sys

_ORTAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ortak")
if os.path.isdir(_ORTAK) and _ORTAK not in sys.path:
    sys.path.insert(0, _ORTAK)
_BURASI = os.path.dirname(os.path.abspath(__file__))
if _BURASI not in sys.path:
    sys.path.insert(0, _BURASI)

import dil  # noqa: E402
import veri_guvenlik  # noqa: E402
import veri_saldiri  # noqa: E402
import veri_temel  # noqa: E402
import veri_tehlike  # noqa: E402

KOMUTLAR = {**veri_saldiri.KOMUTLAR, **veri_guvenlik.KOMUTLAR, **veri_temel.KOMUTLAR}
TAKMA_ADLAR = {**veri_saldiri.TAKMA_ADLAR, **veri_guvenlik.TAKMA_ADLAR, **veri_temel.TAKMA_ADLAR}   # örn. mkfs.ext4 -> mkfs

SEVIYE_SIRASI = {"dusuk": 0, "orta": 1, "yuksek": 2}
KONTROL_ISLEMLERI = {"|", "||", "&&", ";", "&", "|&"}
_ORTAM_ATAMASI = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def T(tr, en):
    return {"tr": tr, "en": en}


ETIKETLER = {
    "baslik": T("Komut açıklaması (komut ÇALIŞTIRILMADI)", "Command explanation (the command was NOT run)"),
    "parca": T("Parça", "Part"),
    "bayraklar": T("Bayraklar", "Flags"),
    "gurultu": T("Gürültü", "Noise"),
    "yetki": T("Yetki", "Privileges"),
    "uyari": T("Uyarı", "Warning"),
    "tehlike": T("Tehlikeli kalıp", "Dangerous pattern"),
    "tanimiyorum": T("Bu komutu tanımıyorum (veri tabanında yok).", "I don't know this command (it is not in the database)."),
    "bilinmeyen_bayrak": T("Tanımadığım bayraklar", "Flags I don't recognise"),
    "baglanti_boru": T("çıktısı bir sonraki komuta aktarılır (|)", "its output is piped into the next command (|)"),
    "baglanti_ve": T("öncekinin başarılı olması durumunda çalışır (&&)", "runs only if the previous one succeeded (&&)"),
    "baglanti_veya": T("öncekinin başarısız olması durumunda çalışır (||)", "runs only if the previous one failed (||)"),
    "baglanti_sonra": T("öncekinden sonra çalışır (;)", "runs after the previous one (;)"),
    "baglanti_arka": T("öncekiyle aynı anda, arka planda çalışır (&)", "runs at the same time in the background (&)"),
    "yonlendirme_yaz": T("çıktıyı şu dosyaya yazar (varsa üzerine yazar)", "writes the output to this file (overwriting it)"),
    "yonlendirme_ekle": T("çıktıyı şu dosyanın sonuna ekler", "appends the output to this file"),
    "yonlendirme_oku": T("girdiyi şu dosyadan okur", "reads its input from this file"),
    "komut_yerine": T("Satırda $(...) ya da ters tırnak var: içindeki komut ayrı parça olarak açıklandı, ama çıktısını çözmem (ne yazacağı bilinmez).",
                      "The line contains $(...) or backticks: the command inside is explained as a separate part, but I don't resolve its output (what it prints is unknown)."),
    "baglanti_satir": T("ayrı bir satırda: öncekinden sonra çalışır (yeni satır)", "on a separate line: runs after the previous one (new line)"),
    "baglanti_ic": T("Parça {n} bu komutu çalıştırır (sh -c, eval, su -c, find -exec, watch, here-document…)",
                     "Part {n} runs this command (sh -c, eval, su -c, find -exec, watch, here-document…)"),
    "baglanti_ikame": T("Parça {n} içindeki $(…), ters tırnak ya da <(…): bu komut ÖNCE çalışır, çıktısı oraya konur",
                        "Inside part {n} ($(…), backticks or <(…)): this command runs FIRST and its output is put there"),
    "baglanti_uzak": T("Parça {n} bu komutu UZAK makinede çalıştırır (ssh)", "Part {n} runs this command on the REMOTE machine (ssh)"),
    "yonlendirme_kopya": T("bir çıktı akışını diğerine bağlar (ör. 2>&1: hata çıktısı normal çıktıyla aynı yere gider)",
                           "joins one output stream to another (e.g. 2>&1: error output goes where normal output goes)"),
    "yonlendirme_hepsi": T("hem çıktıyı hem hata çıktısını şu dosyaya yazar", "writes both the output and the error output to this file"),
    "yonlendirme_metin": T("girdi olarak bu metni verir (here-string)", "gives this text as input (here-string)"),
    "yonlendirme_belge": T("girdi olarak sonraki satırları verir, bu sözcüğe kadar (here-document)",
                           "gives the following lines as input, up to this word (here-document)"),
    "sarmalayici": T("Önündeki sarmalayıcılar (asıl komutu onlar çalıştırır)", "Wrappers in front (they run the actual command)"),
    "atama": T("Değişken ataması: değeri bu kabukta saklar, kendisi bir program çalıştırmaz (içindeki $(…) yine çalışır).",
               "Variable assignment: stores the value in this shell and runs no program itself (any $(…) inside still runs)."),
    "sudo_kabuk": T("root olarak yeni bir kabuk açar: bundan sonra yazdığın her komut root olarak çalışır.",
                    "opens a new shell as root: every command you type after this runs as root."),
    "yerel_yol": T("{yol} bir dosya yolu: aynı adlı sistem komutu ({ad}) olmayabilir. Aşağıdaki açıklama sistem komutuna göredir; "
                   "bu dosyanın gerçekte ne yaptığını bilmiyorum.",
                   "{yol} is a file path: it may not be the system command of the same name ({ad}). The explanation below is for "
                   "the system command; I don't know what this file really does."),
    "anahtar_for": T("Kabuk döngüsü: do … done arasındaki komutlar listedeki her değer için tekrar çalışır.",
                     "Shell loop: the commands between do … done run again for each value in the list."),
    "anahtar_case": T("Kabuk seçimi (case): değere uyan daldaki komutlar çalışır.",
                      "Shell choice (case): the commands in the branch that matches the value run."),
    "anahtar_fonk": T("İşlev tanımı: { … } içindeki komutlar şimdi değil, işlev adı çağrıldığında çalışır.",
                      "Function definition: the commands inside { … } run when the function's name is called, not now."),
    "supheli_karakter": T("Satırda görünmeyen ya da denetim karakteri var (ör. \\x1b, <U+202E>): ekranda göründüğünden farklı bir "
                          "komut olabilir. Bu karakterler aşağıda görünür biçimde yazıldı.",
                          "The line contains invisible or control characters (e.g. \\x1b, <U+202E>): the command may differ from "
                          "what the screen shows. They are written out visibly below."),
    "cok_satir": T("Satır {n} ayrı satırdan oluşuyor: Enter'a basınca hepsi sırayla çalışır.",
                   "The line is made of {n} separate lines: pressing Enter runs all of them in turn."),
    "yorum": T("# işaretinden satır sonuna kadar olan kısım yorumdur, çalışmaz.",
               "The part from # to the end of the line is a comment and does not run."),
    "cozemedim": T("Bu satırın bir kısmını çözümleyemedim; açıklama eksik olabilir ve tehlikeli bir parça gözden kaçmış olabilir:",
                   "I could not analyse part of this line; the explanation may be incomplete and a dangerous part may have been missed:"),
    "neden_komut_degisken": T("Komut adı bir değişkenden ya da komut çıktısından geliyor ($…); hangi programın çalışacağını bilemem.",
                              "The command name comes from a variable or command output ($…); I can't know which program will run."),
    "neden_metin_calisma_aninda": T("Çalıştırılacak metin çalışma anında üretiliyor (değişken ya da $(…) çıktısı: sh -c, eval, su -c, ssh); "
                                    "içeriğini bilemem.",
                                    "The text to be run is produced at run time (a variable or $(…) output: sh -c, eval, su -c, ssh); "
                                    "I can't know its content."),
    "neden_baska_dil": T("Satırda başka bir programlama dilinde kod var (python -c, perl -e, here-document…); onu çözümlemem.",
                         "The line contains code in another programming language (python -c, perl -e, here-document…); I don't analyse it."),
    "neden_yapi": T("Satırda tam çözemediğim bir kabuk yapısı var (aritmetik, eksik sonlandırıcı, beklenmeyen ayraç…).",
                    "The line contains shell syntax I can't fully resolve (arithmetic, a missing terminator, an unexpected bracket…)."),
    "neden_cok_derin": T("İç içe yapı çok derin; en içteki kısımlar açıklanmadı.",
                         "The nesting is too deep; the innermost parts are not explained."),
    "neden_cok_parca": T("Satırda çok fazla parça var; yalnızca ilk {n} parça açıklandı.",
                         "The line has too many parts; only the first {n} parts are explained."),
    "neden_cok_uzun": T("Satır çok uzun; yalnızca ilk {n} karakter açıklandı.",
                        "The line is too long; only the first {n} characters are explained."),
    "degisken": T("Değişkenler ($ADI) çözülmez: değerleri bilinmediği için olduğu gibi gösterilir.",
                  "Variables ($NAME) are not resolved: they are shown as written because their values are unknown."),
    "bos": T("Açıklanacak bir komut yok.", "There is no command to explain."),
    "tamamlanmamis": T("Satır tamamlanmamış (kapanmayan tırnak).", "The line is incomplete (unclosed quote)."),
    "sudo_ile": T("sudo ile root olarak çalışır", "runs as root via sudo"),
    "root_gerekli": T("root yetkisi gerekir (sudo ile çalıştır)", "needs root privileges (run with sudo)"),
    "root_gerekebilir": T("bazı seçenekler root yetkisi ister", "some options need root privileges"),
    "root_yok": T("normal kullanıcı yeterli", "a normal user is enough"),
    "gsd": T("Sözlükte (GSD) bak", "See the glossary (GSD)"),
    "seviye_dusuk": T("düşük", "low"),
    "seviye_orta": T("orta", "medium"),
    "seviye_yuksek": T("yüksek", "high"),
    "arguman": T("Argümanlar", "Arguments"),
    "nasil": T("Nasıl çalışır", "How it works"),
    "savunma": T("Savunma tarafı", "The defender's side"),
    "etik": T("Yalnızca sana ait ya da yazılı izin aldığın sistemlerde kullan.",
              "Use it only on systems you own or have written permission to test."),
}


def _metin(sozluk, kod):
    return dil.metin(sozluk, kod)


# ---------------------------------------------------------------------------
# Ayrıştırma
# ---------------------------------------------------------------------------

# Neden shlex değil: shlex `#`'i sözcük ortasında da yorum sayıyor, yeni satırı boşluk sayıyor, `$(…)`,
# `<(…)` ve here-document bilmiyor (denetim A-01, A-02, A-03). Aşağıdaki küçük sözcükleyici bash'in
# kurallarına yakın davranır; emin olamadığı yerde "çözümleyemedim" nedeni ekler, asla susmaz.

SINIR_KARAKTER = 65536       # bundan uzun satırın yalnızca başı açıklanır (A-09)
SINIR_PARCA = 200            # en çok bu kadar parça açıklanır
SINIR_DERINLIK = 8           # sh -c / $(…) / eval iç içe en çok bu kadar çözülür
_SOZCUKLEYICI_DERINLIK = 40  # $( iç içe: bundan derini özyinelemesiz atlanır (Python yığını taşmasın)

_ISLEMLER = (";;&", ";;", ";&", "&&", "||", "|&", ";", "&", "|", "(", ")")
_YONLER = ("&>>", "&>", "<<<", "<<-", "<<", "<>", "<&", ">&", ">>", ">|", "<", ">")
_METAKARAKTER = set(" \t\n\r;&|()<>")
_DIZI_ATAMASI = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\[[^\]]*\])?\+?=$")
_DEGISKEN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*|[0-9@*#?$!-])")
_ANSI_SAYI = re.compile(r"x([0-9A-Fa-f]{1,2})|u([0-9A-Fa-f]{1,4})|U([0-9A-Fa-f]{1,8})|([0-7]{1,3})|c(.)")
_ANSI = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "e": "\x1b", "E": "\x1b",
         "\\": "\\", "'": "'", '"': '"', "?": "?"}
_ANAHTAR_ONEK = {"if", "then", "elif", "else", "do", "while", "until", "!", "{"}
_ANAHTAR_SON = {"fi", "done", "esac", "}"}
_SISTEM_DIZINLERI = ("/bin/", "/sbin/", "/usr/bin/", "/usr/sbin/", "/usr/local/bin/", "/usr/local/sbin/")


class _Tamamlanmamis(ValueError):
    """Kapanmayan tırnak, $( ya da ters tırnak: bash satırı çalıştırmaz, devamını bekler."""


def _k(deger):
    """Yapay (tırnaksız, düz) sözcük belirteci."""
    return {"t": "k", "d": deger, "h": deger, "ik": [], "g": False, "tirnak": False}


def _ansi_c(s, i):
    """$'…' içeriğini çözer (\\e, \\x1b, \\u202e…). Dönüş: (metin, kapanıştan sonraki konum)."""
    out, n = [], len(s)
    while i < n:
        c = s[i]
        if c == "'":
            return "".join(out), i + 1
        if c == "\\" and i + 1 < n:
            d = s[i + 1]
            if d in _ANSI:
                out.append(_ANSI[d])
                i += 2
                continue
            m = _ANSI_SAYI.match(s, i + 1)
            if m:
                if m.group(5):
                    out.append(chr(ord(m.group(5)) & 0x1F))
                else:
                    sayi = int(m.group(1) or m.group(2) or m.group(3) or m.group(4), 8 if m.group(4) else 16)
                    out.append(chr(sayi) if sayi <= 0x10FFFF and not 0xD800 <= sayi <= 0xDFFF else "�")
                i = m.end()
                continue
            out.append(c + d)
            i += 2
            continue
        out.append(c)
        i += 1
    raise _Tamamlanmamis()


def _kapanisi_atla(s, j):
    """Çok derin $( için özyinelemesiz, yaklaşık kapanış araması (yalnızca konumu bulur)."""
    derin, n = 1, len(s)
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "'":
            k = s.find("'", j + 1)
            if k < 0:
                raise _Tamamlanmamis()
            j = k + 1
            continue
        if c == "(":
            derin += 1
        elif c == ")":
            derin -= 1
            if derin == 0:
                return j + 1
        j += 1
    raise _Tamamlanmamis()


class _Sozcukleyici:
    """Bash'e yakın sözcükleyici. Belirteçler:
    {"t":"k"} sözcük (d: tırnakları açılmış değer, h: yazıldığı gibi, ik: [(tür, iç satır)], g: genişleme var mı),
    {"t":"i"} işlem (; && || | |& & ( ) ;; ve yeni satır "\\n"), {"t":"y"} yönlendirme, {"t":"yorum"}."""

    def __init__(self, s, i=0, derinlik=0, kapanis=False, nedenler=None):
        self.s, self.i, self.derinlik, self.kapanis = s, i, derinlik, kapanis
        self.nedenler = nedenler if nedenler is not None else set()
        self.bekleyen_belgeler = []

    def calistir(self):
        s, n = self.s, len(self.s)
        out = []
        parantez = case = 0
        while self.i < n:
            c = s[self.i]
            if c in " \t":
                self.i += 1
                continue
            if c == "\\" and s.startswith("\n", self.i + 1):
                self.i += 2
                continue
            if c in "\n\r":
                # \r de ayırıcı sayılır: yapıştırmada Enter gibi davranabilir; gizli komut ayrı parça görünsün (A-02)
                self.i += 2 if s.startswith("\r\n", self.i) else 1
                out.append({"t": "i", "d": "\n"})
                if self.bekleyen_belgeler:
                    self._belgeleri_oku()
                continue
            if c == "#":            # yalnızca sözcük başında yorum (A-01)
                j = self.i
                while j < n and s[j] not in "\n\r":
                    j += 1
                out.append({"t": "yorum", "d": s[self.i:j]})
                self.i = j
                continue
            if c in "<>" and s.startswith("(", self.i + 1):
                out.append(self._sozcuk())
                continue
            op = next((o for o in _YONLER if s.startswith(o, self.i)), None)
            if op:
                self.i += len(op)
                y = {"t": "y", "d": op, "fd": ""}
                out.append(y)
                if op in ("<<", "<<-"):
                    self._belge_kaydet(y, out)
                continue
            op = next((o for o in _ISLEMLER if s.startswith(o, self.i)), None)
            if op:
                if self.kapanis and op == ")" and parantez == 0 and case == 0:
                    self.i += 1
                    return out
                if op == "(":
                    parantez += 1
                elif op == ")" and parantez:
                    parantez -= 1
                self.i += len(op)
                out.append({"t": "i", "d": op})
                continue
            t = self._sozcuk()
            out.append(t)
            if t["t"] == "y":
                if t["d"] in ("<<", "<<-"):
                    self._belge_kaydet(t, out)
            elif not t["tirnak"]:
                if t["d"] == "case":
                    case += 1
                elif t["d"] == "esac" and case:
                    case -= 1
        if self.kapanis:
            raise _Tamamlanmamis()
        return out

    def _belge_kaydet(self, y, out):
        s, n = self.s, len(self.s)
        while self.i < n and s[self.i] in " \t":
            self.i += 1
        if self.i >= n or s[self.i] in _METAKARAKTER:
            self.nedenler.add("yapi")
            return
        w = self._sozcuk()
        if w["t"] != "k":
            self.nedenler.add("yapi")
            return
        out.append(w)
        self.bekleyen_belgeler.append((y, w["d"], w["tirnak"], y["d"] == "<<-"))

    def _belgeleri_oku(self):
        """Here-document gövdelerini okur: gövde komut değil veridir, ama tırnaksız sınırlayıcıda içindeki $(…) çalışır."""
        s, n = self.s, len(self.s)
        for y, bitis, tirnakli, sekme in self.bekleyen_belgeler:
            satirlar = []
            while self.i < n:
                j = self.i
                while j < n and s[j] not in "\n\r":
                    j += 1
                satir = s[self.i:j]
                self.i = (j + (2 if s.startswith("\r\n", j) else 1)) if j < n else n
                kontrol = satir.lstrip("\t") if sekme else satir
                if kontrol == bitis:
                    break
                satirlar.append(kontrol)
            y["govde"] = "\n".join(satirlar)
            if not tirnakli:
                ik = []
                alt = _Sozcukleyici(y["govde"], 0, self.derinlik + 1, False, self.nedenler)
                alt._belge_tara(ik)
                y["ik"] = ik
        self.bekleyen_belgeler = []

    def _belge_tara(self, ikameler):
        s, n = self.s, len(self.s)
        while self.i < n:
            c = s[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c in "$`":
                self._genisleme(ikameler)
                continue
            self.i += 1

    def _alt(self, j):
        """j'den başlayan $( … ) / <( … ) içini ayrı sözcükleyiciyle okur. Dönüş: (iç metin, belirteçler)."""
        if self.derinlik >= _SOZCUKLEYICI_DERINLIK:
            self.nedenler.add("cok_derin")
            self.i = _kapanisi_atla(self.s, j)
            return "", []
        alt = _Sozcukleyici(self.s, j, self.derinlik + 1, True, self.nedenler)
        belirtecler = alt.calistir()
        self.i = alt.i
        return self.s[j:alt.i - 1], belirtecler

    def _genisleme(self, ikameler):
        """self.i'deki $… ya da ters tırnağı okur. Dönüş: genişleme var mı."""
        s, n = self.s, len(self.s)
        if s[self.i] == "`":
            j, parca = self.i + 1, []
            while j < n and s[j] != "`":
                if s[j] == "\\" and j + 1 < n and s[j + 1] in "`\\$":
                    parca.append(s[j + 1])
                    j += 2
                    continue
                parca.append(s[j])
                j += 1
            if j >= n:
                raise _Tamamlanmamis()
            self.i = j + 1
            ikameler.append(("ikame", "".join(parca)))
            return True
        if s.startswith("$((", self.i):
            self.i += 3
            self._aritmetik(ikameler)
            return True
        if s.startswith("$(", self.i):
            metin, _ = self._alt(self.i + 2)
            ikameler.append(("ikame", metin))
            return True
        if s.startswith("${", self.i):
            j, derin = self.i + 2, 1
            while j < n and derin:
                if s[j] == "\\":
                    j += 2
                    continue
                if s.startswith("$(", j) or s[j] == "`":
                    self.i = j
                    self._genisleme(ikameler)
                    j = self.i
                    continue
                if s[j] == "{":
                    derin += 1
                elif s[j] == "}":
                    derin -= 1
                j += 1
            if derin:
                raise _Tamamlanmamis()
            self.i = j
            return True
        m = _DEGISKEN.match(s, self.i)
        if m:
            self.i = m.end()
            return True
        self.i += 1                     # yalnız $: düz karakter
        return False

    def _aritmetik(self, ikameler):
        s, n, derin = self.s, len(self.s), 2
        while self.i < n:
            c = s[self.i]
            if (c == "$" and s.startswith("$(", self.i)) or c == "`":
                self._genisleme(ikameler)
                continue
            if c == "(":
                derin += 1
            elif c == ")":
                derin -= 1
                if derin == 0:
                    self.i += 1
                    return
            self.i += 1
        raise _Tamamlanmamis()

    def _cift_tirnak(self, deger, ikameler):
        s, n, g = self.s, len(self.s), False
        while self.i < n:
            c = s[self.i]
            if c == '"':
                self.i += 1
                return g
            if c == "\\" and self.i + 1 < n and s[self.i + 1] in '$`"\\\n':
                if s[self.i + 1] != "\n":
                    deger.append(s[self.i + 1])
                self.i += 2
                continue
            if c in "$`":
                bas = self.i
                if self._genisleme(ikameler):
                    g = True
                deger.append(s[bas:self.i])
                continue
            deger.append(c)
            self.i += 1
        raise _Tamamlanmamis()

    def _sozcuk(self):
        s, n = self.s, len(self.s)
        bas = self.i
        deger, ikameler = [], []
        genisleme = tirnak = False
        while self.i < n:
            c = s[self.i]
            if c in "<>" and s.startswith("(", self.i + 1):         # süreç ikamesi <(…) >(…)
                bas2 = self.i
                metin, _ = self._alt(self.i + 2)
                ikameler.append(("ikame", metin))
                deger.append(s[bas2:self.i])
                genisleme = True
                continue
            if c == "(" and deger and not tirnak:
                onceki = "".join(deger)
                if _DIZI_ATAMASI.match(onceki) or onceki[-1] in "?*+@!":     # dizi ataması ya da extglob
                    bas2 = self.i
                    _, alt_belirtec = self._alt(self.i + 1)
                    for t in alt_belirtec:
                        ikameler.extend(t.get("ik", []))
                    deger.append(s[bas2:self.i])
                    continue
            if c in _METAKARAKTER:
                break
            if c == "\\":
                if self.i + 1 < n:
                    if s[self.i + 1] != "\n":
                        deger.append(s[self.i + 1])
                    self.i += 2
                else:
                    self.i += 1
                tirnak = True           # kaçışlı sözcük anahtar sözcük sayılmaz
                continue
            if c == "'":
                j = s.find("'", self.i + 1)
                if j < 0:
                    raise _Tamamlanmamis()
                deger.append(s[self.i + 1:j])
                self.i = j + 1
                tirnak = True
                continue
            if c == "$" and s.startswith("'", self.i + 1):
                metin, self.i = _ansi_c(s, self.i + 2)
                deger.append(metin)
                tirnak = True
                continue
            if c == '"' or (c == "$" and s.startswith('"', self.i + 1)):
                self.i += 1 if c == '"' else 2
                genisleme |= self._cift_tirnak(deger, ikameler)
                tirnak = True
                continue
            if c in "$`":
                bas2 = self.i
                if self._genisleme(ikameler):
                    genisleme = True
                deger.append(s[bas2:self.i])
                continue
            deger.append(c)
            self.i += 1
        if self.i == bas:               # güvenlik: hiçbir şey okunmadıysa ilerle (sonsuz döngü olmasın)
            self.i += 1
            return _k(s[bas])
        d = "".join(deger)
        if (not tirnak and not ikameler and re.fullmatch(r"[0-9]+", d) and self.i < n and s[self.i] in "<>"
                and not s.startswith("(", self.i + 1)):
            op = next(o for o in _YONLER if s.startswith(o, self.i))
            self.i += len(op)
            return {"t": "y", "d": op, "fd": d}
        return {"t": "k", "d": d, "h": s[bas:self.i], "ik": ikameler, "g": genisleme, "tirnak": tirnak}


def _yeni_parca():
    return {"kelime": [], "yonlendirme": [], "anahtar": None, "bagla": None, "fonk": None, "ham_ek": ""}


def _aritmetigi_atla(b, i, nedenler):
    """(( … )) aritmetik komutunu atlar (komut değildir; içi çözümlenmez, bunu söyleriz)."""
    nedenler.add("yapi")
    derin = 0
    while i < len(b):
        t = b[i]
        if t["t"] == "i" and t["d"] == "(":
            derin += 1
        elif t["t"] == "i" and t["d"] == ")":
            derin -= 1
            if derin <= 0:
                return i + 1
        elif t["t"] == "k" and t["ik"]:
            nedenler.add("yapi")
        i += 1
    nedenler.add("yapi")
    return i


def _yapilar(belirtecler, nedenler):
    """Belirteçleri basit komutlara böler; anahtar sözcükleri (if/then/do/{/!…) atlar, for/case/işlev
    başlıklarını ayrı parça yapar. Dönüş: (ham parçalar, bilgi)."""
    parcalar = []
    bilgi = {"yorum": False}
    durum = {"bagla": None, "simdi": _yeni_parca()}
    fonklar, kume, case_derin, blok = [], 0, 0, 0
    mod = None                  # None | "baslik" | "desen"
    bas = True

    def bitir():
        simdi = durum["simdi"]
        if simdi["kelime"] or simdi["yonlendirme"] or simdi["anahtar"]:
            simdi["bagla"] = durum["bagla"]
            simdi["fonk"] = fonklar[-1][0] if fonklar else None
            parcalar.append(simdi)
            durum["bagla"] = None
        durum["simdi"] = _yeni_parca()

    def bos_mu():
        s = durum["simdi"]
        return not (s["kelime"] or s["yonlendirme"] or s["anahtar"])

    def islem_mi(t, d):
        return t["t"] == "i" and t["d"] == d

    i, n = 0, len(belirtecler)
    while i < n:
        t = belirtecler[i]
        tur = t["t"]
        simdi = durum["simdi"]
        if tur == "yorum":
            bilgi["yorum"] = True
            i += 1
            continue
        if mod == "desen":          # case dalı deseni: ")"e kadar komut değil
            if tur == "k" and t["d"] == "esac" and not t["tirnak"]:
                case_derin -= 1
                mod = None
            elif islem_mi(t, ")"):
                mod, bas = None, True
            i += 1
            continue
        if tur == "i":
            op = t["d"]
            if op == "\n":
                if bos_mu():
                    if parcalar and durum["bagla"] is None:
                        durum["bagla"] = "\n"
                else:
                    bitir()
                    durum["bagla"] = "\n"
                if mod == "baslik":
                    mod = None
                bas = True
            elif op in (";;", ";&", ";;&"):
                bitir()
                durum["bagla"] = None
                if case_derin:
                    mod = "desen"
                bas = True
            elif op == "(":
                if bas and bos_mu():
                    if i + 1 < n and islem_mi(belirtecler[i + 1], "("):
                        i = _aritmetigi_atla(belirtecler, i, nedenler)
                        continue
                elif (len(simdi["kelime"]) == 1 and not simdi["yonlendirme"] and not simdi["anahtar"]
                      and i + 1 < n and islem_mi(belirtecler[i + 1], ")")):
                    ad = simdi["kelime"][0]["d"]               # ad() { … } işlev tanımı
                    simdi["anahtar"], simdi["ham_ek"] = "fonk", "()"
                    bitir()
                    fonklar.append((ad, kume))
                    bas = True
                    i += 2
                    continue
                else:
                    nedenler.add("yapi")
            elif op == ")":
                bitir()
                bas = True
            else:
                bitir()
                durum["bagla"] = op
                if mod == "baslik":
                    mod = None
                bas = True
            i += 1
            continue
        if tur == "y":
            hedef = belirtecler[i + 1] if i + 1 < n and belirtecler[i + 1]["t"] == "k" else None
            if hedef is None:
                nedenler.add("yapi")
            simdi["yonlendirme"].append((t["fd"] + t["d"], hedef, t))
            i += 2 if hedef else 1
            continue
        w = t["d"]
        duz = not t["tirnak"] and not t["ik"] and not t["g"]
        if mod == "baslik":
            simdi["kelime"].append(t)
            if simdi["anahtar"] == "case" and duz and w == "in":
                bitir()
                mod = "desen"
                case_derin += 1
            i += 1
            continue
        if bas and bos_mu() and duz:
            if w in _ANAHTAR_ONEK:
                if w == "{":
                    kume += 1
                elif w in ("if", "while", "until"):
                    blok += 1
                i += 1
                continue
            if w in _ANAHTAR_SON:
                if w in ("fi", "done"):
                    blok -= 1
                if w == "}":
                    kume -= 1
                    if fonklar and fonklar[-1][1] == kume:
                        fonklar.pop()
                elif w == "esac" and case_derin:
                    case_derin -= 1
                i += 1
                continue
            if w in ("for", "select", "case"):
                if w != "case" and i + 1 < n and islem_mi(belirtecler[i + 1], "("):
                    blok += 1
                    i = _aritmetigi_atla(belirtecler, i + 1, nedenler)
                    continue
                simdi["anahtar"] = "case" if w == "case" else "for"
                if w != "case":
                    blok += 1
                simdi["kelime"].append(t)
                mod = "baslik"
                i += 1
                continue
            if w == "function":
                simdi["anahtar"] = "fonk"
                simdi["kelime"].append(t)
                if i + 1 < n and belirtecler[i + 1]["t"] == "k":
                    ad = belirtecler[i + 1]["d"]
                    simdi["kelime"].append(belirtecler[i + 1])
                    i += 2
                    if i + 1 < n and islem_mi(belirtecler[i], "(") and islem_mi(belirtecler[i + 1], ")"):
                        i += 2
                    bitir()
                    fonklar.append((ad, kume))
                    bas = True
                    continue
                i += 1
                continue
            if w == "coproc":
                i += 1
                continue
        simdi["kelime"].append(t)
        bas = False
        i += 1
    bitir()
    if mod or case_derin > 0 or kume > 0 or blok > 0:
        nedenler.add("yapi")        # kapanmamış for/case/{ … : bash devamını bekler, yapı tam değil
    return parcalar, bilgi


def parcala(satir: str):
    """Satırı basit komut parçalarına böler (geriye uyumluluk için).
    Dönüş: [(bagla, {"belirtec", "yonlendirme", "komut_yerine"})]. Kapanmayan tırnakta ValueError."""
    hamlar, _ = _yapilar(_Sozcukleyici(satir).calistir(), set())
    return [(h["bagla"], {"belirtec": [t["d"] for t in h["kelime"]],
                          "yonlendirme": [(op, hd["d"] if hd else "") for op, hd, _ in h["yonlendirme"]],
                          "komut_yerine": any(t["ik"] for t in h["kelime"])}) for h in hamlar]


# Başka bir komutu argümanlarıyla çalıştıran önekler: (değer alan kısa seçenekler, değer alan uzun seçenekler)
_SARMALAYICILAR = {
    "sudo": ({"-u", "-g", "-p", "-C", "-D", "-R", "-T", "-U", "-r", "-t", "-c"},
             {"--user", "--group", "--host", "--prompt", "--close-from", "--chdir", "--chroot", "--command-timeout",
              "--other-user", "--role", "--type", "--login-class"}),
    "doas": ({"-u", "-C"}, set()),
    "env": ({"-u", "-C", "-S"}, {"--unset", "--chdir", "--split-string"}),
    "nice": ({"-n"}, {"--adjustment"}),
    "ionice": ({"-c", "-n", "-p", "-P", "-u"}, {"--class", "--classdata"}),
    "timeout": ({"-s", "-k"}, {"--signal", "--kill-after"}),
    "nohup": (set(), set()),
    "setsid": (set(), set()),
    "command": (set(), set()),
    "builtin": (set(), set()),
    "exec": ({"-a"}, set()),
    "time": ({"-f", "-o"}, {"--format", "--output"}),
    "stdbuf": ({"-i", "-o", "-e"}, {"--input", "--output", "--error"}),
    "xargs": ({"-a", "-d", "-E", "-I", "-L", "-n", "-P", "-s"},
              {"--arg-file", "--delimiter", "--eof", "--replace", "--max-lines", "--max-args", "--max-procs",
               "--max-chars", "--process-slot-var"}),
    "chroot": (set(), {"--userspec", "--groups"}),
    "flock": ({"-w", "-E", "-c"}, {"--timeout", "--conflict-exit-code", "--command"}),
    "proxychains": ({"-f"}, set()),
    "proxychains4": ({"-f"}, set()),
    "torsocks": ({"-u", "-p", "-a", "-P"}, set()),
    "busybox": (set(), set()),
}
# Seçeneklerden sonra komuttan önce bir konumsal değer alanlar (süre, yeni kök, kilit dosyası)
_SARMALAYICI_KONUMSAL = {"timeout": 1, "chroot": 1, "flock": 1}


def _sistem_yolu_mu(yol):
    """/usr/bin/rm gibi standart sistem dizinindeki program: aynı adlı komut sayılır."""
    return any(yol.startswith(d) and "/" not in yol[len(d):] for d in _SISTEM_DIZINLERI)


def _program_adi(yol):
    """Önek/sarmalayıcı tanıma için: yalın ad ya da sistem dizinindeki yol → ad; ./sudo gibi yerel yol → None."""
    if "/" not in yol:
        return yol
    return os.path.basename(yol) if _sistem_yolu_mu(yol) else None


def _secenekleri_gec(b, kisa_deger, uzun_deger):
    """b'nin başındaki seçenekleri (ve değer alanların değerlerini) çıkarır. Dönüş: [(ad, değer)]."""
    alinan = []
    while b and b[0]["d"].startswith("-") and b[0]["d"] != "-":
        a = b.pop(0)["d"]
        if a == "--":
            break
        if a.startswith("--"):
            ad, esit, deger = a.partition("=")
            if ad in uzun_deger and not esit and b:
                deger = b.pop(0)["d"]
            alinan.append((ad, deger))
            continue
        for k, h in enumerate(a[1:], 1):        # kısa küme: -Eu root, -uroot
            if "-" + h in kisa_deger:
                deger = a[k + 1:]
                if not deger and b:
                    deger = b.pop(0)["d"]
                alinan.append(("-" + h, deger))
                break
            alinan.append(("-" + h, ""))
    return alinan


def _onek_coz(kelimeler, nedenler):
    """VAR=deger atamalarını ve sudo/env/nice/timeout/xargs… sarmalayıcılarını ayıklar.
    Dönüş: (kalan belirteçler [program, argümanlar…], bilgi)."""
    b = list(kelimeler)
    bilgi = {"sudo": False, "kabuk": False, "atamalar": [], "onekler": [], "flock_c": None}
    while b:
        ilk = b[0]
        if _ORTAM_ATAMASI.match(ilk["h"]):          # A="x y", A=$(…), a=(…) de atamadır
            bilgi["atamalar"].append(b.pop(0)["d"])
            continue
        if ilk["g"] or ilk["ik"]:
            break
        ad = _program_adi(ilk["d"])
        if ad not in _SARMALAYICILAR:
            break
        b.pop(0)
        kisa, uzun = _SARMALAYICILAR[ad]
        secenekler = _secenekleri_gec(b, kisa, uzun)
        if ad in ("sudo", "doas"):
            bilgi["sudo"] = True
            if any(s in ("-i", "-s", "--login", "--shell") for s, _ in secenekler):
                bilgi["kabuk"] = True
        else:
            bilgi["onekler"].append(ad)
        if ad == "env":
            while b and _ORTAM_ATAMASI.match(b[0]["h"]):
                b.pop(0)                        # env'in kendi atamaları: asıl komutun ortamı
            for s, deger in secenekler:
                if s in ("-S", "--split-string") and deger:
                    try:
                        b[0:0] = [_k(x) for x in shlex.split(deger)]
                    except ValueError:
                        nedenler.add("yapi")
        if ad == "flock":                       # flock [seçenek] dosya [seçenek] -c 'komut' | komut…
            if b:
                b.pop(0)
            secenekler += _secenekleri_gec(b, kisa, uzun)
            komut = [d for s, d in secenekler if s in ("-c", "--command")]
            if komut:
                bilgi["flock_c"] = _k(komut[0])
                return [], bilgi
            continue
        for _ in range(_SARMALAYICI_KONUMSAL.get(ad, 0)):
            if b:
                b.pop(0)
        if ad == "busybox" and b and b[0]["d"].startswith("-"):
            break
    return b, bilgi


def onek_ayikla(belirtecler):
    """sudo/env/time/nohup/nice/command/exec/timeout/xargs… öneklerini ve VAR=deger atamalarını ayıklar.
    Dönüş: (program, argümanlar, sudo_mu, atamalar)."""
    kalan, bilgi = _onek_coz([_k(x) for x in belirtecler], set())
    if not kalan:
        return "", [], bilgi["sudo"], bilgi["atamalar"]
    return os.path.basename(kalan[0]["d"]), [t["d"] for t in kalan[1:]], bilgi["sudo"], bilgi["atamalar"]


def _tanim_bul(program):
    program = TAKMA_ADLAR.get(program, program)
    if program in KOMUTLAR:
        return program, KOMUTLAR[program]
    # Yalnızca bilinen nokta biçimleri: mkfs.ext4, fsck.vfat, python3.11. `ls.sh`, `cat.py` gibi
    # adlar başka bir dosyadır; aynı adlı sistem komutu sanılmamalı (A-06).
    if re.fullmatch(r"(mkfs|fsck)\.[A-Za-z0-9]+|[A-Za-z]+[0-9]*\.[0-9]+", program):
        kok = program.split(".")[0]
        if kok in KOMUTLAR:
            return kok, KOMUTLAR[kok]
    return program, None


def bayraklari_coz(tanim, argumanlar):
    """Dönüş: (bulunan[(ad, girdi, deger)], bilinmeyen[str], konumsal[str])."""
    bayraklar = tanim.get("bayraklar", {})
    desenler = tanim.get("desenler", [])
    kume = tanim.get("kume", False)
    bulunan, bilinmeyen, konumsal = [], [], []
    argumanlar = list(argumanlar)
    # tar xzf dosya.tar.gz gibi tire içermeyen eski biçim
    if tanim.get("eski_kume") and argumanlar and re.fullmatch(r"[A-Za-z]+", argumanlar[0]) \
            and all(("-" + h) in bayraklar for h in argumanlar[0]):
        argumanlar[0] = "-" + argumanlar[0]
    i = 0
    while i < len(argumanlar):
        a = argumanlar[i]
        if a == "--":
            konumsal.extend(argumanlar[i + 1:])
            break
        if a.startswith("-") and len(a) > 1:
            ad, deger = a, None
            if a.startswith("--") and "=" in a:
                ad, deger = a.split("=", 1)
            girdi = bayraklar.get(ad)
            if girdi is None:
                for desen, g in desenler:
                    if re.match(desen, a):
                        girdi, ad = g, a
                        break
            if girdi is None and re.match(r"^-\d+(\.\d+)?$", a):
                konumsal.append(a)      # sayı (ör. -1 gibi bir değer): bayrak değil
                i += 1
                continue
            if girdi is None and kume and not a.startswith("--") and len(a) > 2:
                parcalar = [(("-" + h), bayraklar.get("-" + h)) for h in a[1:]]
                if all(g is not None for _, g in parcalar):
                    for ad2, g in parcalar:
                        bulunan.append((ad2, g, None))
                    # kümenin son harfi değer alıyorsa sıradaki argüman onun değeri
                    son = parcalar[-1][1]
                    if son.get("deger") and i + 1 < len(argumanlar):
                        bulunan[-1] = (bulunan[-1][0], son, argumanlar[i + 1])
                        i += 1
                    i += 1
                    continue
            if girdi is None:
                bilinmeyen.append(a)
                i += 1
                continue
            if girdi.get("deger") and deger is None and i + 1 < len(argumanlar):
                deger = argumanlar[i + 1]
                i += 1
            bulunan.append((ad, girdi, deger))
        else:
            konumsal.append(a)
        i += 1
    return bulunan, bilinmeyen, konumsal


def _en_yuksek(*seviyeler):
    en = "dusuk"
    for s in seviyeler:
        if s and SEVIYE_SIRASI.get(s, 0) > SEVIYE_SIRASI[en]:
            en = s
    return en


_KABUKLAR = {"sh", "bash", "dash", "zsh", "ksh", "mksh", "ash", "fish", "rbash"}
_YORUMLAYICI_RE = re.compile(r"^(python[0-9.]*|perl[0-9.]*|ruby[0-9.]*|node|nodejs|php[0-9.]*|lua[0-9.]*|tclsh|pwsh|Rscript)$")


def yorumlayici_mi(program):
    return program in _KABUKLAR or bool(_YORUMLAYICI_RE.match(program or ""))


def _kabuk_c(args):
    """sh/bash … -c 'komut': (c kipi mi, komut metni belirteci)."""
    c_kipi, i = False, 0
    while i < len(args):
        a = args[i]["d"]
        if a in ("--", "-"):
            i += 1
            break
        if a in ("-o", "+o", "-O", "+O", "--rcfile", "--init-file"):
            i += 2
            continue
        if a.startswith("--"):
            i += 1
            continue
        if len(a) > 1 and a[0] in "-+":
            if a[0] == "-" and "c" in a[1:]:
                c_kipi = True
            i += 1
            continue
        break
    return c_kipi, (args[i] if c_kipi and i < len(args) else None)


def _stdin_kod_mu(program, args):
    """Yorumlayıcı kodu standart girdiden mi okuyor (curl … | sh)? Betik dosyası, -c ya da -m varsa hayır."""
    if not yorumlayici_mi(program):
        return False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-":
            return True
        if a == "--":
            return i + 1 >= len(args)
        if a.startswith("--"):
            i += 1
            continue
        if a.startswith("-") and len(a) > 1:
            h = a[1:]
            if program in _KABUKLAR:
                if "c" in h:
                    return False
                if "s" in h:
                    return True
                if a in ("-o", "-O"):
                    i += 1
            elif any(x in h for x in "cmeErp"):
                return False
            i += 1
            continue
        return False
    return True


def _baska_dil_kodu(program, args):
    """python -c, perl -e, node -e, php -r: kod başka bir dilde, çözümlenmez."""
    if program in _KABUKLAR or not yorumlayici_mi(program):
        return False
    for a in args:
        if a.startswith("--"):
            if a in ("--eval", "--print") or a.startswith("--eval=") or a.startswith("--command"):
                return True
            continue
        if a.startswith("-") and len(a) > 1:
            h = a[1:]
            if (program.startswith("python") and "c" in h) or (program.startswith(("perl", "ruby")) and ("e" in h or "E" in h)) \
                    or (program in ("node", "nodejs") and h in ("e", "p")) or (program.startswith("php") and h == "r") \
                    or (program.startswith(("lua", "pwsh")) and h in ("e", "c", "Command")):
                return True
    return False


def _yazi(tokenlar):
    return " ".join(t["d"] if re.fullmatch(r"[\w@%+=:,./{}~-]+", t["d"]) else shlex.quote(t["d"]) for t in tokenlar)


def _ic_isler(c, kalan, hp, bilgi, nedenler):
    """Bu parçanın çalıştıracağı iç komutlar: [(tür, satır)]; tür ikame | ic | uzak."""
    isler = []

    def metin_ekle(tur, tokenlar):
        if not tokenlar:
            return
        if any(t["g"] or t["ik"] for t in tokenlar):
            nedenler.add("metin_calisma_aninda")     # içerik çalışma anında üretiliyor; $(…) kısmı zaten ikame
        else:
            isler.append((tur, " ".join(t["d"] for t in tokenlar)))

    for t in hp["kelime"]:
        isler.extend(("ikame", m) for _, m in t["ik"])
    for op, h, y in hp["yonlendirme"]:
        if h:
            isler.extend(("ikame", m) for _, m in h["ik"])
        isler.extend(("ikame", m) for _, m in y.get("ik", []))
        if "govde" in y and op.lstrip("0123456789") in ("<<", "<<-") and op[:1] in ("<", "0"):
            if c["program"] in _KABUKLAR and not c["c_kipi"]:
                isler.append(("ic", y["govde"]))
            elif yorumlayici_mi(c["program"]):
                nedenler.add("baska_dil")
    if bilgi.get("flock_c"):
        metin_ekle("ic", [bilgi["flock_c"]])
    if not kalan:
        return isler
    prog, args = c["program"], kalan[1:]
    if c.get("yol") or c.get("degisken_komut"):
        return isler
    if prog in _KABUKLAR:
        c_kipi, tok = _kabuk_c(args)
        if c_kipi:
            if tok is None:
                nedenler.add("yapi")
            else:
                metin_ekle("ic", [tok])
    elif _baska_dil_kodu(prog, [t["d"] for t in args]):
        nedenler.add("baska_dil")
    elif prog == "eval":
        metin_ekle("ic", args)
    elif prog == "su":
        for k, t in enumerate(args):
            if t["d"] in ("-c", "--command") and k + 1 < len(args):
                metin_ekle("ic", [args[k + 1]])
            elif t["d"].startswith("--command="):
                metin_ekle("ic", [dict(t, d=t["d"].split("=", 1)[1])])
    elif prog == "ssh":
        b = list(args)
        _secenekleri_gec(b, {"-p", "-i", "-l", "-L", "-R", "-D", "-o", "-J", "-F", "-b", "-c", "-e", "-m", "-O", "-Q",
                             "-S", "-W", "-w", "-E", "-B", "-I"}, set())
        if len(b) > 1:
            metin_ekle("uzak", b[1:])
    elif prog == "watch":
        b = list(args)
        _secenekleri_gec(b, {"-n", "-d", "-q"}, {"--interval", "--differences"})
        metin_ekle("ic", b)
    elif prog == "find":
        k = 0
        while k < len(args):
            if args[k]["d"] in ("-exec", "-execdir", "-ok", "-okdir"):
                j = k + 1
                while j < len(args) and args[j]["d"] not in (";", "+"):
                    j += 1
                if j >= len(args):
                    nedenler.add("yapi")
                if any(t["g"] or t["ik"] for t in args[k + 1:j]):
                    nedenler.add("metin_calisma_aninda")
                elif j > k + 1:
                    isler.append(("ic", _yazi(args[k + 1:j])))
                k = j
            k += 1
    return isler


def parca_coz(parca, nedenler=None):
    """Tek bir basit komutu çözer. `parca`: _yapilar'ın ham parçası ya da eski biçim {"belirtec": [...]}.
    Dönüş: çözülmüş parça sözlüğü (iç komutlar "_isler" anahtarında)."""
    nedenler = set() if nedenler is None else nedenler
    if "kelime" not in parca:           # eski biçim
        parca = dict(_yeni_parca(), kelime=[_k(x) for x in parca.get("belirtec", [])],
                     yonlendirme=[(op, _k(h), {}) for op, h in parca.get("yonlendirme", [])])
    kelime = parca["kelime"]
    sonuc = {
        "program": "", "komut": "", "argumanlar": [], "sudo": False, "atamalar": [],
        "bilinen": False, "ozet": None, "bayraklar": [], "bilinmeyen": [], "konumsal": [],
        "gurultu": None, "root": None, "uyari": None, "gsd": None, "etik": False,
        "nasil": None, "savunma": None,
        "altkomut": None, "parametreler": [],
        "yonlendirme": [(op, h["d"] if h else "") for op, h, _ in parca["yonlendirme"]],
        "komut_yerine": any(t["ik"] for t in kelime) or any(h and h["ik"] for _, h, _ in parca["yonlendirme"]),
        "ham": " ".join(t["h"] for t in kelime) + parca.get("ham_ek", ""),
        "anahtar": parca.get("anahtar"), "fonk": parca.get("fonk"), "onekler": [], "kabuk": False,
        "yol": None, "degisken_komut": False, "c_kipi": False, "stdin_kod": False, "_isler": [],
    }
    if sonuc["anahtar"]:
        sonuc["bilinen"] = True
        sonuc["_isler"] = [("ikame", m) for t in kelime for _, m in t["ik"]]
        return sonuc
    kalan, bilgi = _onek_coz(kelime, nedenler)
    sonuc.update(sudo=bilgi["sudo"], atamalar=bilgi["atamalar"], onekler=bilgi["onekler"], kabuk=bilgi["kabuk"])
    tanim = None
    if kalan:
        pt = kalan[0]
        yol = pt["d"]
        program = os.path.basename(yol) if "/" in yol else yol
        argumanlar = [t["d"] for t in kalan[1:]]
        sonuc.update(program=program, komut=program, argumanlar=argumanlar)
        if pt["g"] or pt["ik"]:
            sonuc["degisken_komut"] = True
            nedenler.add("komut_degisken")
        else:
            if "/" in yol and not _sistem_yolu_mu(yol):
                sonuc["yol"] = yol
            ad, tanim = _tanim_bul(program)
            sonuc["komut"] = ad
        if program in _KABUKLAR:
            sonuc["c_kipi"] = _kabuk_c(kalan[1:])[0]
        sonuc["stdin_kod"] = _stdin_kod_mu(program, argumanlar)
    sonuc["bilinen"] = tanim is not None
    sonuc["_isler"] = _ic_isler(sonuc, kalan, parca, bilgi, nedenler)
    if tanim is None:
        return sonuc
    argumanlar = sonuc["argumanlar"]
    bulunan, bilinmeyen, konumsal = bayraklari_coz(tanim, argumanlar)
    sonuc["ozet"] = tanim["ozet"]
    sonuc["bayraklar"] = [{"ad": a, "aciklama": g["a"], "deger": d} for a, g, d in bulunan]
    sonuc["bilinmeyen"], sonuc["konumsal"] = bilinmeyen, konumsal
    alt = tanim.get("altkomut")
    if alt and konumsal and konumsal[0] in alt:
        sonuc["altkomut"] = (konumsal[0], alt[konumsal[0]])
    prm = tanim.get("parametreler")
    if prm:
        kalan = []
        for k in sonuc["konumsal"]:
            ad_, _, deger_ = k.partition("=")
            if _ and ad_ in prm:
                sonuc["parametreler"].append((ad_, deger_, prm[ad_]))
            else:
                kalan.append(k)
        sonuc["konumsal"] = kalan
    sonuc["gurultu"] = _en_yuksek(tanim.get("gurultu"), *[g.get("g") for _, g, _ in bulunan])
    root_bayrak = any(g.get("root") for _, g, _ in bulunan)
    if tanim.get("yetki") == "root" or root_bayrak:
        sonuc["root"] = "gerekli"
    elif tanim.get("yetki") == "kismen":
        sonuc["root"] = "gerekebilir"
    else:
        sonuc["root"] = "yok"
    sonuc["uyari"] = tanim.get("uyari")
    sonuc["gsd"] = tanim.get("gsd")
    sonuc["etik"] = bool(tanim.get("etik"))
    sonuc["nasil"] = tanim.get("nasil")
    sonuc["savunma"] = tanim.get("savunma")
    return sonuc


_YEDEK_BOL = re.compile(r"[;&|()\n\r`]|\$\(|<\(")
_YEDEK_PROGRAMLAR = {"rm", "dd", "mkfs", "mke2fs", "chmod", "chown", "chgrp", "find", "shred", "wipefs", "sgdisk",
                     "blkdiscard", "ufw", "systemctl", "iptables", "ip6tables", "nft", "setenforce", "eval"}


def _yedek_parcalar(satir):
    """Yapıdan bağımsız ikinci geçiş: satır çözülemediğinde tehlikeli program adlarının ardından gelen
    sözcükleri kaba biçimde parça sayar (tırnaklar yok sayılır). Yalnızca tehlike taraması içindir."""
    out = []
    for kesit in _YEDEK_BOL.split(satir)[:2000]:
        sozcukler = kesit.replace('"', " ").replace("'", " ").split()
        for i, s in enumerate(sozcukler[:500]):
            ad = os.path.basename(s)
            if ad in _YEDEK_PROGRAMLAR or ad.startswith("mkfs"):
                out.append(parca_coz(dict(_yeni_parca(), kelime=[_k(x) for x in sozcukler[i:i + 64]]), set()))
                if len(out) >= 300:
                    return out
    return out


def tehlikeleri_bul(satir, cozulmus_parcalar, nedenler=None):
    """Parça bazlı, yapı (boru hattı / iç komut) ve satır kuralları. Satır çözülemediyse (nedenler dolu)
    yapıdan bağımsız ikinci geçiş de yapılır. Dönüş: [{"id","siddet","neden"}] (yinelenmez)."""
    bulunan, goruldu = [], set()

    def ekle(kural):
        if kural["id"] not in goruldu:
            goruldu.add(kural["id"])
            bulunan.append({"id": kural["id"], "siddet": kural["siddet"], "neden": kural["neden"]})

    def parca_kurallari(parcalar):
        for p in parcalar:
            for kural in veri_tehlike.PARCA_KURALLARI:
                try:
                    if kural["kosul"](p):
                        ekle(kural)
                except Exception:  # noqa: BLE001  (kural hatası açıklamayı durdurmasın)
                    continue

    for kural in veri_tehlike.SATIR_KURALLARI:
        if re.search(kural["desen"], satir):
            ekle(kural)
    for kural in veri_tehlike.YAPI_KURALLARI:
        try:
            if kural["kosul"](cozulmus_parcalar, satir):
                ekle(kural)
        except Exception:  # noqa: BLE001
            continue
    parca_kurallari(cozulmus_parcalar)
    if nedenler:
        parca_kurallari(_yedek_parcalar(satir))
    bulunan.sort(key=lambda k: -SEVIYE_SIRASI.get(k["siddet"], 0))
    return bulunan


def _coz(satir, derinlik, ust, ust_tur, ctx):
    """satir'ı ayrıştırıp çözülmüş parçaları ctx["parcalar"]'a ekler; iç komutları özyinelemeli çözer."""
    if derinlik > SINIR_DERINLIK:
        ctx["nedenler"].add("cok_derin")
        return
    belirtecler = _Sozcukleyici(satir, nedenler=ctx["nedenler"]).calistir()
    hamlar, bilgi = _yapilar(belirtecler, ctx["nedenler"])
    if derinlik == 0:
        ctx["bilgi"] = bilgi
    onceki_boru = None
    for sira, hp in enumerate(hamlar):
        if len(ctx["parcalar"]) >= SINIR_PARCA:
            ctx["nedenler"].add("cok_parca")
            return
        c = parca_coz(hp, ctx["nedenler"])
        isler = c.pop("_isler")
        c["bagla"] = ust_tur if (sira == 0 and ust is not None) else hp["bagla"]
        c["ust"], c["ic_tur"] = ust, ust_tur
        if c["bagla"] in ("|", "|&") and onceki_boru is not None:
            c["boru"] = onceki_boru
        else:
            ctx["boru"] += 1
            c["boru"] = ctx["boru"]
        onceki_boru = c["boru"]
        ctx["parcalar"].append(c)
        no = len(ctx["parcalar"]) - 1
        for tur, metin in isler:
            if not metin.strip():
                continue
            try:
                _coz(metin, derinlik + 1, no, tur, ctx)
            except _Tamamlanmamis:
                ctx["nedenler"].add("yapi")


_NEDEN_SIRASI = ("cok_uzun", "cok_parca", "cok_derin", "komut_degisken", "metin_calisma_aninda", "baska_dil", "yapi")
_SUPHELI = ("\x00-\x08\x0b-\x1f\x7f-\x9f­؜ᅟᅠ᠎​-‏‪-‮  "
            "⁠-⁤⁦-⁯ㅤ﻿￹-￻\udc80-\udcff\U000e0000-\U000e007f")
_SUPHELI_RE = re.compile("[" + _SUPHELI + "]")          # \t ve \n hariç denetim/görünmez/yön karakterleri
_GORUNMEZ_RE = re.compile("[\n" + _SUPHELI + "]")       # çıktı satırının içinde \n de kaçışlanır


def ayristir(satir: str) -> dict:
    """Ana giriş. Dönüş: {"satir", "tamam", "hata", "parcalar":[{"bagla", **parca}], "tehlikeler":[...],
    "komut_yerine": bool, "degisken": bool, "nedenler": [çözümlenemeyen yapı kodları], "supheli_karakter": bool,
    "satir_sayisi": int, "yorum": bool}"""
    sonuc = {"satir": satir, "tamam": True, "hata": None, "parcalar": [], "tehlikeler": [],
             "komut_yerine": False, "degisken": False, "nedenler": [], "supheli_karakter": False,
             "satir_sayisi": 1, "yorum": False}
    if not isinstance(satir, str) or not satir.strip():
        sonuc["tamam"], sonuc["hata"] = False, "bos"
        return sonuc
    nedenler = set()
    if len(satir) > SINIR_KARAKTER:
        satir = satir[:SINIR_KARAKTER]
        nedenler.add("cok_uzun")
    sonuc["supheli_karakter"] = bool(_SUPHELI_RE.search(satir))
    ctx = {"parcalar": [], "nedenler": nedenler, "boru": 0, "bilgi": {"yorum": False}}
    try:
        _coz(satir, 0, None, None, ctx)
    except _Tamamlanmamis:
        # bash bu satırı çalıştırmaz (devamını bekler); yine de görünen tehlikeler gösterilir
        sonuc["tamam"], sonuc["hata"] = False, "tamamlanmamis"
        sonuc["tehlikeler"] = tehlikeleri_bul(satir, [], {"yapi"})
        sonuc["nedenler"] = [k for k in _NEDEN_SIRASI if k in nedenler]
        return sonuc
    cozulmus = ctx["parcalar"]
    sonuc["yorum"] = ctx["bilgi"].get("yorum", False)
    sonuc["nedenler"] = [k for k in _NEDEN_SIRASI if k in nedenler]
    if not cozulmus:
        sonuc["tamam"], sonuc["hata"] = False, "bos"
        return sonuc
    sonuc["parcalar"] = cozulmus
    sonuc["tehlikeler"] = tehlikeleri_bul(satir, cozulmus, nedenler)
    sonuc["komut_yerine"] = any(p["komut_yerine"] for p in cozulmus) or "$(" in satir or "`" in satir
    sonuc["degisken"] = bool(re.search(r"\$[A-Za-z_{]", satir))
    sonuc["satir_sayisi"] = 1 + sum(1 for p in cozulmus if p["ust"] is None and p["bagla"] == "\n")
    sonuc["nedenler"] = [k for k in _NEDEN_SIRASI if k in nedenler]
    return sonuc


# ---------------------------------------------------------------------------
# Metin çıktısı (CLI ve kutu)
# ---------------------------------------------------------------------------

def _bagla_etiketi(bagla):
    return {"|": "baglanti_boru", "|&": "baglanti_boru", "&&": "baglanti_ve", "||": "baglanti_veya",
            ";": "baglanti_sonra", "&": "baglanti_arka"}.get(bagla)


def _kacis(m):
    cp = ord(m.group(0))
    if 0xDC80 <= cp <= 0xDCFF:          # geçersiz UTF-8 baytı (surrogateescape)
        return "\\x%02x" % (cp - 0xDC00)
    if cp < 0x100:
        return "\\x%02x" % cp
    return "<U+%04X>" % cp


_SATIR_SINIRI = 2000        # tek bir çıktı satırı en çok bu kadar karakter (uzun komut çıktıyı şişirmesin)


def _gorunur(metin):
    """Terminale güvenle yazılabilir metin: ESC, OSC, diğer denetim ve yön (bidi) karakterleri görünür kaçışla (A-05)."""
    if len(metin) > _SATIR_SINIRI:
        metin = metin[:_SATIR_SINIRI] + " …"
    return _GORUNMEZ_RE.sub(_kacis, metin) if _GORUNMEZ_RE.search(metin) else metin


def _yon_satiri(op, hedef, E):
    temel = op.lstrip("0123456789")
    if temel in ("<<", "<<-"):
        anahtar = "yonlendirme_belge"
    elif temel == "<<<":
        anahtar = "yonlendirme_metin"
    elif temel in (">&", "<&") and re.fullmatch(r"[0-9]+-?|-", hedef or ""):
        return f"  {op}{hedef}: {E('yonlendirme_kopya')}"
    elif temel in ("&>", "&>>", ">&"):
        anahtar = "yonlendirme_hepsi"
    elif "<" in temel and temel != "<>":
        anahtar = "yonlendirme_oku"
    elif ">>" in temel:
        anahtar = "yonlendirme_ekle"
    else:
        anahtar = "yonlendirme_yaz"
    return f"  {op} {hedef}: {E(anahtar)}"


def _bagla_metni(p, E):
    b = p.get("bagla")
    if b in ("ic", "ikame", "uzak"):
        return E("baglanti_" + b).replace("{n}", str(p["ust"] + 1))
    if b == "\n":
        return E("baglanti_satir")
    k = _bagla_etiketi(b)
    return E(k) if k else None


def metin_olustur(sonuc: dict, kod: str = "tr") -> str:
    """Okunabilir düz metin. `kod` dil kodu (tr/en/de/…); çeviri yoksa İngilizce.
    Kullanıcıdan gelen her şey _gorunur'den geçer: çıktı terminali yönetemez."""
    def E(anahtar):
        return _metin(ETIKETLER[anahtar], kod)

    satirlar = [E("baslik"), ""]
    ust = []
    if sonuc.get("supheli_karakter"):
        ust.append("⚠ " + E("supheli_karakter"))
    if sonuc.get("satir_sayisi", 1) > 1:
        ust.append("⚠ " + E("cok_satir").replace("{n}", str(sonuc["satir_sayisi"])))
    if sonuc.get("nedenler"):
        ust.append("⚠ " + E("cozemedim"))
        sinir = {"cok_parca": SINIR_PARCA, "cok_uzun": SINIR_KARAKTER}
        for k in sonuc["nedenler"]:
            ust.append("  - " + E("neden_" + k).replace("{n}", str(sinir.get(k, ""))))
    if ust:
        satirlar += ust + [""]
    if not sonuc["tamam"]:
        satirlar.append(E(sonuc["hata"] or "bos"))
        for t in sonuc.get("tehlikeler", []):
            satirlar.append(f"⚠ {E('tehlike')} ({E('seviye_' + t['siddet'])}): {_metin(t['neden'], kod)}")
        return "\n".join(_gorunur(x) for x in satirlar)
    coklu = len(sonuc["parcalar"]) > 1
    for n, p in enumerate(sonuc["parcalar"], 1):
        etiket = _bagla_metni(p, E)
        if etiket:
            satirlar.append("  ↳ " + etiket)
        if "ham" in p:
            baslik = p["ham"] or "?"
        else:
            baslik = (("sudo " if p["sudo"] else "") + (p["program"] or "?")
                      + (" " + " ".join(p["argumanlar"]) if p["argumanlar"] else ""))
        satirlar.append((f"[{E('parca')} {n}] " if coklu else "") + baslik)
        if p.get("anahtar"):
            satirlar.append("  " + E("anahtar_" + p["anahtar"]))
            for op, hedef in p["yonlendirme"]:
                satirlar.append(_yon_satiri(op, hedef, E))
            satirlar.append("")
            continue
        if p.get("yol"):
            satirlar.append("  ⚠ " + E("yerel_yol").replace("{yol}", p["yol"]).replace("{ad}", p["program"]))
        if not p["bilinen"]:
            if p.get("kabuk") and not p["program"]:
                satirlar.append("  " + E("sudo_kabuk"))
            elif not p["program"] and p.get("atamalar") and not p.get("sudo") and not p.get("onekler"):
                satirlar.append("  " + E("atama"))
            else:
                satirlar.append("  " + E("tanimiyorum"))
            for op, hedef in p["yonlendirme"]:
                satirlar.append(_yon_satiri(op, hedef, E))
            satirlar.append("")
            continue
        satirlar.append("  " + _metin(p["ozet"], kod))
        if p.get("onekler"):
            satirlar.append("  " + E("sarmalayici") + ": " + ", ".join(p["onekler"]))
        if p["altkomut"]:
            satirlar.append(f"  {p['altkomut'][0]}: {_metin(p['altkomut'][1], kod)}")
        for ad_, deger_, aciklama_ in p["parametreler"]:
            satirlar.append(f"  {ad_}={deger_}  —  {_metin(aciklama_, kod)}")
        if p["bayraklar"]:
            satirlar.append("  " + E("bayraklar") + ":")
            for b in p["bayraklar"]:
                deger = f" {b['deger']}" if b["deger"] else ""
                satirlar.append(f"    {b['ad']}{deger}  —  {_metin(b['aciklama'], kod)}")
        if p["konumsal"]:
            satirlar.append("  " + E("arguman") + ": " + " ".join(p["konumsal"]))
        if p["bilinmeyen"]:
            satirlar.append("  " + E("bilinmeyen_bayrak") + ": " + " ".join(p["bilinmeyen"]))
        satirlar.append("  " + E("gurultu") + ": " + E("seviye_" + p["gurultu"]))
        if p["sudo"]:
            yetki = E("sudo_ile")
        else:
            yetki = {"gerekli": E("root_gerekli"), "gerekebilir": E("root_gerekebilir"), "yok": E("root_yok")}[p["root"]]
        satirlar.append("  " + E("yetki") + ": " + yetki)
        for op, hedef in p["yonlendirme"]:
            satirlar.append(_yon_satiri(op, hedef, E))
        if p["nasil"]:
            satirlar.append("  " + E("nasil") + ": " + _metin(p["nasil"], kod))
        if p["savunma"]:
            satirlar.append("  " + E("savunma") + ": " + _metin(p["savunma"], kod))
        if p["uyari"]:
            satirlar.append("  " + E("uyari") + ": " + _metin(p["uyari"], kod))
        if p["etik"]:
            satirlar.append("  " + E("etik"))
        if p["gsd"]:
            satirlar.append("  " + E("gsd") + ": " + p["gsd"])
        satirlar.append("")
    for t in sonuc["tehlikeler"]:
        satirlar.append(f"⚠ {E('tehlike')} ({E('seviye_' + t['siddet'])}): {_metin(t['neden'], kod)}")
    if sonuc["komut_yerine"]:
        satirlar.append("• " + E("komut_yerine"))
    if sonuc["degisken"]:
        satirlar.append("• " + E("degisken"))
    if sonuc.get("yorum"):
        satirlar.append("• " + E("yorum"))
    return "\n".join(_gorunur(x) for x in satirlar).rstrip() + "\n"


def acikla(satir: str, kod: str | None = None) -> str:
    """Kolay giriş: satır → açıklama metni."""
    return metin_olustur(ayristir(satir), kod or dil.varsayilan_dil())
