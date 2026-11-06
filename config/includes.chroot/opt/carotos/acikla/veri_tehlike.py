# -*- coding: utf-8 -*-
"""Komut Açıklayıcı: kullanıcıyı yanlışlıkla zarar vermekten koruyan uyarı kuralları.

SATIR_KURALLARI : ham satırda regex (ör. internetten indirip doğrudan çalıştırma)
PARCA_KURALLARI : her çözümlenmiş komut parçasında koşul işlevi
Açıklayıcı hiçbir zaman komutu çalıştırmaz; yalnızca "dur, şuna dikkat et" der.
"""
import re


def T(tr, en):
    return {"tr": tr, "en": en}


SATIR_KURALLARI = [
    {"id": "indir_calistir", "siddet": "yuksek",
     "desen": r"\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(-\S+\s+)*([a-z]*sh)\b",
     "neden": T("İnternetten indirilen içerik, ne olduğuna bakılmadan doğrudan çalıştırılıyor (curl | sh). "
                "Betik değişmiş olabilir; önce indirip oku, sonra çalıştır.",
                "Content downloaded from the internet is run directly without looking at it (curl | sh). "
                "The script may have been tampered with; download it, read it, then run it.")},
    {"id": "komut_indir_calistir", "siddet": "yuksek",
     "desen": r"\b(ba)?sh\s+-c\s+[\"']?\$\(\s*(curl|wget)\b",
     "neden": T("İnternetten indirilen kod doğrudan çalıştırılıyor. Önce indirip oku, sonra çalıştır.",
                "Code downloaded from the internet is run directly. Download it, read it, then run it.")},
]


def _ozyinelemeli(p):
    return any(a in ("-r", "-R", "--recursive") or (a.startswith("-") and not a.startswith("--") and ("r" in a or "R" in a))
               for a in p["argumanlar"])


def _rm_tehlikeli(p):
    if p["komut"] != "rm":
        return False
    if "--no-preserve-root" in p["argumanlar"]:
        return True
    hedefler = [a for a in p["argumanlar"] if not a.startswith("-")]
    tehlikeli = {"/", "/*", "~", "~/", "~/*", "$HOME", "$HOME/", "$HOME/*", "/home", "/home/*", "/etc", "/etc/*",
                 "/usr", "/usr/*", "/var", "/var/*", "/boot", "/boot/*", "/bin", "/lib", "/sbin", "*"}
    return _ozyinelemeli(p) and any(h in tehlikeli for h in hedefler)


def _disk_hedefi(deger):
    return bool(re.match(r"^/dev/(sd[a-z]|hd[a-z]|vd[a-z]|xvd[a-z]|nvme\d+n\d+|mmcblk\d+)", deger or ""))


def _dd_diske(p):
    return p["komut"] == "dd" and any(a.startswith("of=") and _disk_hedefi(a[3:]) for a in p["argumanlar"])


def _mkfs(p):
    return p["komut"] in ("mkfs", "mke2fs") or p["program"].startswith("mkfs")


def _chmod_genis(p):
    if p["komut"] != "chmod":
        return False
    modlar = [a for a in p["argumanlar"] if not a.startswith("-")]
    herkes_yazar = bool(modlar) and modlar[0] in ("777", "666", "a+w", "o+w", "ugo+w", "a=rwx")
    kok = any(m in ("/", "/*", "/etc", "/usr", "/var", "/home", "~") for m in modlar[1:])
    return herkes_yazar and (_ozyinelemeli(p) or kok)


def _chown_kok(p):
    if p["komut"] not in ("chown", "chgrp"):
        return False
    hedefler = [a for a in p["argumanlar"] if not a.startswith("-")][1:]
    return _ozyinelemeli(p) and any(h in ("/", "/*", "/etc", "/usr", "/var", "/home", "/bin", "/lib") for h in hedefler)


def _guvenlik_kapat(p):
    k = p["konumsal"]
    if p["komut"] == "ufw" and k and k[0] in ("disable", "reset"):
        return True
    if p["komut"] == "systemctl" and len(k) >= 2 and k[0] in ("stop", "disable", "mask") \
            and k[1].split(".")[0] in ("ufw", "fail2ban", "apparmor", "clamav-daemon", "carotpot"):
        return True
    return False


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
]
