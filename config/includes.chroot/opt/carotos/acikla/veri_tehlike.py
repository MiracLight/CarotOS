# -*- coding: utf-8 -*-
"""Komut Açıklayıcı: kullanıcıyı yanlışlıkla zarar vermekten koruyan uyarı kuralları.

SATIR_KURALLARI : ham satırda regex (şu an boş: regex kurallar tırnak içini de görüyor, yaygın biçimleri
                  kaçırıyor ve uzun satırda ikinci dereceden yavaşlıyordu; denetim A-04, A-09)
PARCA_KURALLARI : her çözümlenmiş komut parçasında koşul işlevi
YAPI_KURALLARI  : bütün parça listesine bakan kurallar (boru hattı, $(…)/<(…) iç komutları, işlev gövdesi)
Açıklayıcı hiçbir zaman komutu çalıştırmaz; yalnızca "dur, şuna dikkat et" der.
"""
import os
import posixpath
import re


def T(tr, en):
    return {"tr": tr, "en": en}


SATIR_KURALLARI = []


def _ozyinelemeli(p):
    return any(a in ("-r", "-R", "--recursive") or (a.startswith("-") and not a.startswith("--") and ("r" in a or "R" in a))
               for a in p["argumanlar"])


def _hedefler(p):
    out, bitti = [], False
    for a in p["argumanlar"]:
        if bitti or not a.startswith("-"):
            out.append(a)
        elif a == "--":
            bitti = True
    return out


# ---- yol değerlendirme -----------------------------------------------------
_EV = "/home/__ev__"
_SISTEM = {"/bin", "/boot", "/dev", "/etc", "/lib", "/lib32", "/lib64", "/libx32", "/opt", "/proc", "/root", "/run",
           "/sbin", "/srv", "/sys", "/usr", "/var", "/home", "/media", "/mnt", "/snap", "/efi"}
_ALTI_DA = {"/usr", "/etc", "/var", "/home", "/boot"}       # bunların doğrudan altı da (ör. /usr/bin, /etc/ssh)


def _sus_ac(h):
    """Tek düzeyli süslü ayraç açılımı: /{usr,etc} → /usr, /etc (en çok 32)."""
    m = re.search(r"\{([^{}]*,[^{}]*)\}", h)
    if not m:
        return [h]
    return [h[:m.start()] + x + h[m.end():] for x in m.group(1).split(",")[:32]]


def _tek_yol_tehlikeli(h):
    if not h:
        return False
    for onek in ("${HOME}", "$HOME", "~"):
        if h == onek or h.startswith(onek + "/"):
            h = _EV + h[len(onek):]
            break
    mutlak = h.startswith("/")
    parcalar = [x for x in h.split("/") if x not in ("", ".")] if mutlak else h.split("/")
    # sondaki "", "." ve yalnızca joker bileşenler (*, .*, .[!.]*, ?*) "dizinin içi" demektir: dizinin kendisi sayılır
    while parcalar and (parcalar[-1] in ("", ".") or (re.fullmatch(r"[.*?\[\]!^]+", parcalar[-1])
                                                    and re.search(r"[*?]", parcalar[-1]))):
        parcalar.pop()
    if mutlak:
        n = posixpath.normpath("/" + "/".join(parcalar))
        return n == "/" or n in _SISTEM or n == _EV or posixpath.dirname(n) in _ALTI_DA
    n = posixpath.normpath("/".join(parcalar) or ".")
    return n == "." or all(x == ".." for x in n.split("/"))


def tehlikeli_yol(h):
    """Kök, ev dizini, sistem dizini (ya da doğrudan altı) veya bulunulan dizinin tamamı mı?"""
    return any(_tek_yol_tehlikeli(x) for x in _sus_ac(h or ""))


def _rm_tehlikeli(p):
    if p["komut"] != "rm":
        return False
    if "--no-preserve-root" in p["argumanlar"]:
        return True
    return _ozyinelemeli(p) and any(tehlikeli_yol(h) for h in _hedefler(p))


_FIND_DAR = {"-name", "-iname", "-path", "-ipath", "-wholename", "-iwholename", "-regex", "-iregex", "-newer", "-mtime",
             "-mmin", "-atime", "-amin", "-ctime", "-cmin", "-size", "-user", "-group", "-perm", "-empty", "-inum",
             "-samefile", "-links", "-uid", "-gid", "-nouser", "-nogroup"}
_YIKICI = {"rm", "shred", "dd", "unlink", "wipefs", "truncate", "chmod", "chown", "mv"}


def _find_parca(p):
    """find parcasi icin (baslangic yollari, yikici eylem var mi); find degilse None."""
    if p["komut"] != "find":
        return None
    a = p["argumanlar"]
    baslar = []
    for x in a:
        if x.startswith("-") or x in ("(", "!", ")"):
            break
        baslar.append(x)
    sil = "-delete" in a
    for i, x in enumerate(a):
        if x in ("-exec", "-execdir", "-ok", "-okdir") and i + 1 < len(a):
            ad = os.path.basename(a[i + 1])
            if ad in _YIKICI or ad.startswith("mkfs"):
                sil = True
    return baslar or ["."], sil


def _find_sil(p):
    f = _find_parca(p)
    if not f or any(x in _FIND_DAR for x in p["argumanlar"]):
        return False
    baslar, sil = f
    return sil and any(tehlikeli_yol(b) for b in baslar)


def _sistem_kapsamli(h):
    """Kok ya da bir sistem dizini (/, /etc, /usr, /home…): ev dizini ve bulunulan dizin degil."""
    if not h or not h.startswith("/"):
        return False
    n = posixpath.normpath(h)
    return n == "/" or n in _SISTEM


def _find_sistem_sil(p):
    # Ad suzgeci (-name '*.conf') varken find_sil susar, cunku ev dizininde ya da bulunulan dizinde
    # (find . -name '*.pyc' -delete) yaygin ve zararsizdir. Kokten ya da bir sistem dizininden baslayan
    # silmede ise suzgec sistemi korumaz: find / -name '*.conf' -exec rm {} \; yine her yerdeki ayarlari siler.
    f = _find_parca(p)
    if not f or not any(x in _FIND_DAR for x in p["argumanlar"]):
        return False
    baslar, sil = f
    return sil and any(_sistem_kapsamli(b) for b in baslar)


# ---- aygıtlar ve yönlendirme ------------------------------------------------
_GUVENLI_AYGIT = re.compile(r"^/dev/(null|zero|full|random|urandom|stdin|stdout|stderr|tty|ptmx|console|fd/.*|pts/.*|shm/.*|tty\w*)$")


def _disk_hedefi(deger):
    """/dev altında null/zero/tty gibi zararsızlar dışındaki her aygıt (disk, by-id, mapper, md, loop, mem…)."""
    h = re.sub(r"/+", "/", deger or "")
    return h.startswith("/dev/") and len(h) > 5 and not _GUVENLI_AYGIT.match(h)


def _dd_diske(p):
    return p["komut"] == "dd" and any(a.startswith("of=") and (_disk_hedefi(a[3:]) or a[3:].startswith("$"))
                                      for a in p["argumanlar"])


def _yazma_hedefleri(p):
    out = []
    for op, h in p.get("yonlendirme", []):
        temel = op.lstrip("0123456789")
        if temel in (">", ">>", ">|", "&>", "&>>", "<>"):
            out.append((temel, h))
        elif temel == ">&" and not re.fullmatch(r"[0-9]+-?|-", h or ""):
            out.append((temel, h))
    return out


def _diske_yaz(p):
    if any(_disk_hedefi(h) for _, h in _yazma_hedefleri(p)):
        return True
    hedefler = _hedefler(p)
    if p["program"] == "tee":
        return any(_disk_hedefi(h) for h in hedefler)
    if p["program"] in ("cp", "cat", "pv") and len(hedefler) >= 2:
        return _disk_hedefi(hedefler[-1])
    return False


_HASSAS_DOSYA = re.compile(r"^(/etc/(passwd|shadow|group|gshadow|sudoers|fstab|hosts|resolv\.conf|crontab|profile|"
                           r"bash\.bashrc|environment|sudoers\.d/.*|pam\.d/.*|ssh/.*)|/boot/.*|"
                           r"(~|\$HOME|\$\{HOME\})/\.(bashrc|profile|bash_profile|zshrc|ssh/.*))$")


def _yonlendirme_tehlikeli(p):
    return any(op in (">", ">|", "&>", ">&") and _HASSAS_DOSYA.match(re.sub(r"/+", "/", h or ""))
               for op, h in _yazma_hedefleri(p))


def _mkfs(p):
    return p["komut"] in ("mkfs", "mke2fs") or p["program"].startswith("mkfs")


def _disk_sil(p):
    k, a = p["program"], p["argumanlar"]
    aygit = any(_disk_hedefi(x) for x in a)
    if k == "wipefs":
        return aygit and any(x in ("-a", "--all") or (x.startswith("-") and not x.startswith("--") and "a" in x) for x in a)
    if k in ("shred", "blkdiscard"):
        return aygit
    if k == "sgdisk":
        return any(x in ("--zap-all", "-Z", "--clear", "-o", "--zap", "-z") for x in a)
    return False


def _bolum_degistir(p):
    k, a = p["program"], p["argumanlar"]
    if k not in ("fdisk", "sfdisk", "gdisk", "cfdisk", "parted"):
        return False
    return any(_disk_hedefi(x) for x in a) and not any(x in ("-l", "--list", "print", "-s", "--show-size", "-d", "--dump")
                                                        for x in a)


# ---- izinler -----------------------------------------------------------------
def mod_coz(m):
    """chmod izin dizgisi → (herkese yazma, setuid). Sekizlik (777, 4755) ve sembolik (a+rwx, u+s) biçim."""
    if re.fullmatch(r"[0-7]{3,4}", m):
        d = m.zfill(4)
        return bool(int(d[3]) & 2), bool(int(d[0]) & 4)
    herkes = suid = False
    for madde in m.split(","):
        mm = re.fullmatch(r"([ugoa]*)([-+=])([rwxXst]*)", madde)
        if not mm:
            continue
        kim, isl, izin = mm.groups()
        if isl == "-":
            continue
        if "w" in izin and ("o" in kim or "a" in kim):
            herkes = True
        if "s" in izin and (not kim or "u" in kim or "a" in kim):
            suid = True
    return herkes, suid


_HASSAS_IZIN = re.compile(r"^(/etc/(shadow|gshadow|passwd|group|sudoers.*)|/(usr/)?(s?bin)/.*|(~|\$HOME|\$\{HOME\})/\.ssh.*)$")


def _chmod_parcala(p):
    modlar = [a for a in p["argumanlar"] if not a.startswith("-")]
    if not modlar:
        return (False, False), []
    return mod_coz(modlar[0]), modlar[1:]


def _chmod_genis(p):
    if p["komut"] != "chmod":
        return False
    (herkes_yazar, _), hedefler = _chmod_parcala(p)
    kok = any(tehlikeli_yol(h) or _HASSAS_IZIN.match(h) for h in hedefler)
    return herkes_yazar and (_ozyinelemeli(p) or kok)


def _chmod_suid(p):
    if p["komut"] != "chmod":
        return False
    (_, suid), hedefler = _chmod_parcala(p)
    return suid and bool(hedefler)


def _chown_kok(p):
    if p["komut"] not in ("chown", "chgrp"):
        return False
    hedefler = [a for a in p["argumanlar"] if not a.startswith("-")][1:]
    return _ozyinelemeli(p) and any(tehlikeli_yol(h) for h in hedefler)


def _guvenlik_kapat(p):
    k, a = p["konumsal"], p["argumanlar"]
    if p["komut"] == "ufw" and k and k[0] in ("disable", "reset"):
        return True
    if p["komut"] == "systemctl" and len(k) >= 2 and k[0] in ("stop", "disable", "mask") \
            and k[1].split(".")[0] in ("ufw", "fail2ban", "apparmor", "clamav-daemon", "carotpot"):
        return True
    if p["program"] in ("iptables", "ip6tables"):
        if any(x in ("-F", "--flush") for x in a):
            return True
        for i, x in enumerate(a):
            if x in ("-P", "--policy") and i + 2 < len(a) and a[i + 2] == "ACCEPT":
                return True
    if p["program"] == "nft" and "flush" in a and "ruleset" in a:
        return True
    if p["program"] == "setenforce" and any(x in ("0", "Permissive", "permissive") for x in a):
        return True
    return False


def _eval(p):
    return p["program"] == "eval"


PARCA_KURALLARI = [
    {"id": "rm_tehlikeli", "siddet": "yuksek", "kosul": _rm_tehlikeli,
     "neden": T("Tüm bir dizini (/, ev dizini, sistem klasörü…) özyinelemeli silmeye çalışıyor; geri alınamaz ve sistemi bozabilir.",
                "It tries to recursively delete a whole directory (/, your home, a system folder…); it can't be undone and can break the system.")},
    {"id": "dd_diske", "siddet": "yuksek", "kosul": _dd_diske,
     "neden": T("`dd` doğrudan bir diske yazıyor (of=/dev/…): diskteki her şey silinir. Hedef diski iki kez kontrol et.",
                "`dd` writes straight to a disk (of=/dev/…): everything on it is erased. Double-check the target disk.")},
    {"id": "mkfs", "siddet": "yuksek", "kosul": _mkfs,
     "neden": T("Bir bölümü ya da diski biçimlendirir: içindeki tüm veri silinir.",
                "It formats a partition or disk: all the data on it is erased.")},
    {"id": "chmod_genis", "siddet": "orta", "kosul": _chmod_genis,
     "neden": T("Herkese yazma izni veriyor (777 gibi), üstelik geniş kapsamda; her kullanıcı dosyaları değiştirebilir.",
                "It gives everyone write permission (like 777) on a broad scope; any user can change the files.")},
    {"id": "chown_kok", "siddet": "yuksek", "kosul": _chown_kok,
     "neden": T("Sistem dizinlerinin sahibini özyinelemeli değiştiriyor; sistem ve sudo çalışmaz hale gelebilir.",
                "It recursively changes the owner of system directories; the system and sudo can stop working.")},
    {"id": "guvenlik_kapat", "siddet": "orta", "kosul": _guvenlik_kapat,
     "neden": T("Bir koruma katmanını (güvenlik duvarı, fail2ban, AppArmor, antivirüs…) kapatıyor ya da sıfırlıyor; sistem savunmasız kalır.",
                "It turns off or resets a protection layer (firewall, fail2ban, AppArmor, antivirus…); the system is left exposed.")},
    {"id": "find_sil", "siddet": "yuksek", "kosul": _find_sil,
     "neden": T("`find` geniş bir dizinde (/, ev dizini, bulunulan dizin…) ad süzgeci olmadan bulduğu her şeyi siliyor ya da değiştiriyor "
                "(-delete, -exec rm…). Önce -delete olmadan çalıştırıp listeye bak.",
                "`find` deletes or changes everything it finds in a broad directory (/, your home, the current folder…) without a "
                "name filter (-delete, -exec rm…). First run it without -delete and check the list.")},
    {"id": "find_sistem_sil", "siddet": "yuksek", "kosul": _find_sistem_sil,
     "neden": T("`find` kökten ya da bir sistem dizininden (/, /etc, /usr…) başlayıp eşleşen her dosyayı siliyor ya da değiştiriyor. "
                "Ad süzgeci sistem dosyalarını korumaz (ör. tüm *.conf dosyaları gider). Önce -delete/-exec olmadan çalıştırıp listeye bak.",
                "`find` starts at the root or a system directory (/, /etc, /usr…) and deletes or changes every matching file. "
                "A name filter does not protect system files (e.g. every *.conf goes). First run it without -delete/-exec and check the list.")},
    {"id": "diske_yaz", "siddet": "yuksek", "kosul": _diske_yaz,
     "neden": T("Bir aygıta (/dev/sda, /dev/nvme0n1, /dev/mapper/…) doğrudan yazıyor; diskteki veri ve bölümler bozulur.",
                "It writes straight to a device (/dev/sda, /dev/nvme0n1, /dev/mapper/…); the data and partitions on it are destroyed.")},
    {"id": "yonlendirme_tehlikeli", "siddet": "orta", "kosul": _yonlendirme_tehlikeli,
     "neden": T("Çıktı önemli bir sistem ya da ayar dosyasının üzerine yazılıyor (> /etc/…, ~/.bashrc, ~/.ssh/…); dosyanın eski içeriği silinir.",
                "The output overwrites an important system or settings file (> /etc/…, ~/.bashrc, ~/.ssh/…); its old content is erased.")},
    {"id": "disk_sil", "siddet": "yuksek", "kosul": _disk_sil,
     "neden": T("Bir diskin içeriğini ya da bölüm tablosunu siliyor (wipefs -a, shred, sgdisk --zap-all, blkdiscard); geri alınamaz.",
                "It erases a disk's contents or partition table (wipefs -a, shred, sgdisk --zap-all, blkdiscard); it can't be undone.")},
    {"id": "bolum_degistir", "siddet": "orta", "kosul": _bolum_degistir,
     "neden": T("Bir diskin bölümlerini değiştirebilir (fdisk, parted…); yanlış diskte veri kaybına yol açar. Aygıt adını lsblk ile kontrol et.",
                "It can change a disk's partitions (fdisk, parted…); on the wrong disk this loses data. Check the device name with lsblk.")},
    {"id": "chmod_suid", "siddet": "yuksek", "kosul": _chmod_suid,
     "neden": T("Dosyaya setuid biti veriyor (u+s, 4755): dosya, sahibinin (çoğu zaman root) yetkisiyle çalışır. Bir kabuğa ya da "
                "yorumlayıcıya verilirse kalıcı bir root kapısı olur.",
                "It sets the setuid bit (u+s, 4755): the file runs with its owner's (often root's) privileges. On a shell or "
                "interpreter this becomes a permanent root backdoor.")},
    {"id": "eval_calistir", "siddet": "orta", "kosul": _eval,
     "neden": T("`eval`, verilen metni yeniden komut olarak yorumlayıp çalıştırır; tırnaklar ve değişkenler ikinci kez açılır, "
                "beklenmedik komutlar çalışabilir.",
                "`eval` interprets the given text again as a command and runs it; quotes and variables are expanded a second "
                "time, so unexpected commands can run.")},
]


# ---- yapı kuralları (bütün parça listesi) -------------------------------------
_INDIRICI = {"curl", "wget", "fetch", "aria2c", "nc", "ncat", "netcat", "socat", "tftp", "ftp", "lwp-download", "http",
             "https", "xh"}
_KAYNAK = {"source", "."}


def _yorumlayici(program):
    return bool(re.match(r"^(sh|bash|dash|zsh|ksh|mksh|ash|fish|rbash|python[0-9.]*|perl[0-9.]*|ruby[0-9.]*|node|nodejs|"
                         r"php[0-9.]*|lua[0-9.]*|tclsh|pwsh|Rscript)$", program or ""))


def _indirici(p):
    return p.get("komut") in _INDIRICI or p.get("program") in _INDIRICI


def _cozucu(p):
    a, k = p["argumanlar"], p["program"]
    if k in ("base64", "base32", "basenc"):
        return any(x in ("-d", "--decode") or (x.startswith("-") and not x.startswith("--") and "d" in x) for x in a)
    if k == "xxd":
        return any(x.startswith("-") and "r" in x for x in a)
    if k == "openssl":
        return "-d" in a
    return False


def _ikame_altlari(parcalar, i):
    """i parçasının $(…), ters tırnak ve <(…) içindeki komutları (ve onların tüm altları)."""
    kume, out = {i}, []
    for j in range(i + 1, len(parcalar)):
        q = parcalar[j]
        u = q.get("ust")
        if (u == i and q.get("ic_tur") == "ikame") or (u in kume and u != i):
            kume.add(j)
            out.append(q)
    return out


def _boru_oncesi(parcalar, i):
    p = parcalar[i]
    return [q for q in parcalar[:i] if q.get("boru") is not None and q.get("boru") == p.get("boru")]


def _indirilen_dosyalar_calisir(parcalar):
    """curl -o kur.sh URL && bash kur.sh (ya da ./kur.sh)."""
    dosyalar = set()
    for p in parcalar:
        a = p["argumanlar"]
        if p.get("komut") in ("curl", "wget"):
            harf = "o" if p["komut"] == "curl" else "O"
            for k, x in enumerate(a):
                if x.startswith("--output=") or x.startswith("--output-document="):
                    dosyalar.add(x.split("=", 1)[1])
                elif (x in ("--output", "--output-document") or (x.startswith("-") and not x.startswith("--") and x.endswith(harf))) \
                        and k + 1 < len(a):
                    dosyalar.add(a[k + 1])
            dosyalar.discard("-")
            continue
        if not dosyalar:
            continue
        adaylar = []
        if p.get("yol"):
            adaylar.append(p["yol"])
        if _yorumlayici(p["program"]) or p["program"] in _KAYNAK:
            adaylar.extend(x for x in a if not x.startswith("-"))
        if {posixpath.normpath(x) for x in adaylar} & {posixpath.normpath(x) for x in dosyalar}:
            return True
    return False


def _indir_calistir(parcalar, satir):
    for i, p in enumerate(parcalar):
        if p.get("anahtar"):
            continue
        if p.get("stdin_kod") and any(_indirici(q) for q in _boru_oncesi(parcalar, i)):
            return True                                    # curl … | sh, curl … | sudo -u root /bin/bash
        if (_yorumlayici(p["program"]) or p["program"] in _KAYNAK) and not p.get("c_kipi") \
                and any(_indirici(q) for q in _ikame_altlari(parcalar, i)):
            return True                                    # bash <(curl …), source <(curl …), bash <<< "$(curl …)"
    return _indirilen_dosyalar_calisir(parcalar)


def _komut_indir_calistir(parcalar, satir):
    for i, p in enumerate(parcalar):
        calistirir = p["program"] in ("eval", "su") or p.get("c_kipi") or p.get("degisken_komut")
        if calistirir and any(_indirici(q) for q in _ikame_altlari(parcalar, i)):
            return True                                    # sh -c "$(curl …)", eval "$(wget -qO- …)", $(curl …)
    return False


def _gizli_kod_calistir(parcalar, satir):
    for i, p in enumerate(parcalar):
        if p.get("stdin_kod") and any(_cozucu(q) for q in _boru_oncesi(parcalar, i)):
            return True                                    # echo … | base64 -d | sh
    return False


def _catal_bombasi(parcalar, satir):
    if re.search(r":\s*\(\s*\)\s*\{", satir):
        return True
    return any(p.get("fonk") and p["program"] == p["fonk"] and p.get("bagla") in ("|", "|&") for p in parcalar)


YAPI_KURALLARI = [
    {"id": "indir_calistir", "siddet": "yuksek", "kosul": _indir_calistir,
     "neden": T("İnternetten indirilen içerik, ne olduğuna bakılmadan doğrudan çalıştırılıyor (curl | sh). "
                "Betik değişmiş olabilir; önce indirip oku, sonra çalıştır.",
                "Content downloaded from the internet is run directly without looking at it (curl | sh). "
                "The script may have been tampered with; download it, read it, then run it.")},
    {"id": "komut_indir_calistir", "siddet": "yuksek", "kosul": _komut_indir_calistir,
     "neden": T("İnternetten indirilen kod doğrudan çalıştırılıyor. Önce indirip oku, sonra çalıştır.",
                "Code downloaded from the internet is run directly. Download it, read it, then run it.")},
    {"id": "gizli_kod_calistir", "siddet": "yuksek", "kosul": _gizli_kod_calistir,
     "neden": T("Kodlanmış (base64 gibi) bir içerik çözülüp doğrudan çalıştırılıyor; ne yaptığı bilerek gizlenmiş. Önce çözüp oku.",
                "Encoded content (such as base64) is decoded and run directly; what it does is deliberately hidden. Decode it and read it first.")},
    {"id": "catal_bombasi", "siddet": "yuksek", "kosul": _catal_bombasi,
     "neden": T("Çatal bombası: kendini durmadan çoğaltan bir işlev; sistemi dakikalar içinde kilitler.",
                "Fork bomb: a function that keeps copying itself; it locks up the system within minutes.")},
]
