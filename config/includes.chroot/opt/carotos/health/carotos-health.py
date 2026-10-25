#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CarotOS Sistem Sağlığı
Sistemin güvenlik ve bakım durumunu denetler, bulguları açıklar ve
düzeltme önerir.

Kullanım:
    carotos-health                Arayüzü açar
    carotos-health --audit-json   Denetimi çalıştırır, JSON basar (pkexec için)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time

APP_VERSION = "1.1"

# --- durum kodlari ---------------------------------------------------------
OK = "ok"          # sorun yok
WARN = "warn"      # iyilestirilebilir
FAIL = "fail"      # dikkat gerektiriyor
INFO = "info"      # bilgi, puana girmez
NEEDROOT = "root"  # root olmadan bakilamaz


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------

def run(cmd, timeout=12):
    """Komutu calistirir, (donus_kodu, cikti) dondurur."""
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, text=True, errors="replace")
        return proc.returncode, proc.stdout.strip()
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError:
        return 1, ""


def read_file(path, limit=200000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return None


def is_root():
    return os.geteuid() == 0


def have(binary):
    return shutil.which(binary) is not None or os.path.exists("/usr/sbin/" + binary)


def bin_path(binary):
    """Aracin tam yolunu bulur; /usr/sbin normal PATH'te olmayabilir."""
    found = shutil.which(binary)
    if found:
        return found
    for prefix in ("/usr/sbin/", "/sbin/", "/usr/bin/", "/bin/"):
        candidate = prefix + binary
        if os.path.exists(candidate):
            return candidate
    return binary


# ---------------------------------------------------------------------------
# Denetimler
#
# Her denetim bir sozluk dondurur:
#   status  : OK / WARN / FAIL / INFO / NEEDROOT
#   detail  : {tr, en} kullaniciya gosterilecek bulgu
#   extra   : (istege bagli) coklu satirli ek bilgi
# ---------------------------------------------------------------------------

def check_os_info():
    data = {}
    content = read_file("/etc/os-release") or ""
    for line in content.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            data[key] = value.strip().strip('"')
    name = data.get("PRETTY_NAME", "?")
    _, kernel = run(["uname", "-r"])
    return {
        "status": INFO,
        "detail": {"tr": f"{name} \u00b7 çekirdek {kernel}",
                   "en": f"{name} \u00b7 kernel {kernel}"},
    }


def check_uptime():
    content = read_file("/proc/uptime") or "0"
    try:
        seconds = float(content.split()[0])
    except (ValueError, IndexError):
        seconds = 0
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    return {
        "status": INFO,
        "detail": {"tr": f"{days} gün {hours} saattir açık",
                   "en": f"Up for {days} days, {hours} hours"},
    }


def check_reboot_required():
    if os.path.exists("/var/run/reboot-required") or \
       os.path.exists("/run/reboot-required"):
        return {
            "status": WARN,
            "detail": {"tr": "Yeniden başlatma bekleniyor. Kurulan güncellemeler "
                             "yeniden başlatılana kadar tam olarak etkin olmaz.",
                       "en": "A reboot is pending. Installed updates are not fully "
                             "active until you restart."},
        }
    return {
        "status": OK,
        "detail": {"tr": "Yeniden başlatma gerekmiyor.",
                   "en": "No reboot required."},
    }


def check_failed_units():
    code, out = run(["systemctl", "--failed", "--no-legend", "--plain"])
    if code != 0:
        return {"status": INFO,
                "detail": {"tr": "Servis durumu okunamadı.",
                           "en": "Could not read service status."}}
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return {"status": OK,
                "detail": {"tr": "Başarısız olan servis yok.",
                           "en": "No failed services."}}
    names = ", ".join(l.split()[0] for l in lines[:6])
    return {
        "status": FAIL,
        "detail": {"tr": f"{len(lines)} servis başarısız: {names}",
                   "en": f"{len(lines)} failed service(s): {names}"},
    }


def check_pending_updates():
    if not have("apt-get"):
        return {"status": INFO, "detail": {"tr": "apt bulunamadı.",
                                           "en": "apt not found."}}
    code, out = run(["apt-get", "-s", "-o", "Debug::NoLocking=1", "upgrade"],
                    timeout=40)
    if code != 0:
        return {"status": WARN,
                "detail": {"tr": "Güncelleme listesi alınamadı. Depo "
                                 "yapılandırmasını kontrol edin.",
                           "en": "Could not read the update list. Check the "
                                 "repository configuration."}}
    count = len(re.findall(r"^Inst ", out, re.M))
    security = len(re.findall(r"^Inst .*(?:security|Security)", out, re.M))
    if security:
        return {"status": FAIL,
                "detail": {"tr": f"{count} güncelleme bekliyor, bunların "
                                 f"{security} tanesi güvenlik güncellemesi.",
                           "en": f"{count} updates pending, {security} of them "
                                 f"security updates."}}
    if count:
        return {"status": WARN,
                "detail": {"tr": f"{count} güncelleme bekliyor.",
                           "en": f"{count} updates pending."}}
    return {"status": OK,
            "detail": {"tr": "Sistem güncel.", "en": "System is up to date."}}


def check_last_apt_update():
    paths = ["/var/lib/apt/periodic/update-success-stamp",
             "/var/lib/apt/lists"]
    newest = 0
    for path in paths:
        try:
            newest = max(newest, os.path.getmtime(path))
        except OSError:
            continue
    if not newest:
        return {"status": WARN,
                "detail": {"tr": "Paket listesi hiç güncellenmemiş görünüyor.",
                           "en": "The package list appears to have never been "
                                 "updated."}}
    days = int((time.time() - newest) // 86400)
    if days > 14:
        status = FAIL
    elif days > 7:
        status = WARN
    else:
        status = OK
    return {"status": status,
            "detail": {"tr": f"Paket listesi {days} gün önce güncellendi.",
                       "en": f"Package list last refreshed {days} days ago."}}


def check_repositories():
    """Bugunku hatayi yakalayan denetim: ag deposu tanimli mi?"""
    sources = []
    main = read_file("/etc/apt/sources.list")
    if main:
        sources.append(("/etc/apt/sources.list", main))
    list_dir = "/etc/apt/sources.list.d"
    if os.path.isdir(list_dir):
        for name in sorted(os.listdir(list_dir)):
            if name.endswith((".list", ".sources")):
                body = read_file(os.path.join(list_dir, name))
                if body:
                    sources.append((os.path.join(list_dir, name), body))

    has_network = False
    has_cdrom = False
    has_security = False
    for _, body in sources:
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            lowered = stripped.lower()
            if lowered.startswith("deb cdrom:"):
                has_cdrom = True
            if "http://" in lowered or "https://" in lowered:
                has_network = True
                if "security" in lowered:
                    has_security = True

    if not has_network:
        return {"status": FAIL,
                "detail": {"tr": "Ağ deposu tanımlı değil. Bu sistemde yazılım "
                                 "kurulamaz ve güvenlik güncellemesi alınamaz.",
                           "en": "No network repository is configured. This system "
                                 "cannot install software or receive security "
                                 "updates."}}
    if not has_security:
        return {"status": WARN,
                "detail": {"tr": "Güvenlik deposu tanımlı görünmüyor.",
                           "en": "The security repository does not appear to be "
                                 "configured."}}
    if has_cdrom:
        return {"status": WARN,
                "detail": {"tr": "Ağ depoları tanımlı, ancak kurulum CD'si de "
                                 "kaynak listesinde duruyor ve her güncellemede "
                                 "hata satırı üretiyor.",
                           "en": "Network repositories are configured, but the "
                                 "installation CD is still listed and produces an "
                                 "error line on every update."}}
    return {"status": OK,
            "detail": {"tr": "Ağ ve güvenlik depoları tanımlı.",
                       "en": "Network and security repositories are configured."}}


def check_unattended():
    code, _ = run(["dpkg-query", "-W", "-f=${Status}", "unattended-upgrades"])
    if code != 0:
        return {"status": WARN,
                "detail": {"tr": "Otomatik güvenlik güncellemeleri kurulu değil. "
                                 "Güncellemeler elle yapılmalıdır.",
                           "en": "Automatic security updates are not installed. "
                                 "Updates must be applied manually."}}
    return {"status": OK,
            "detail": {"tr": "Otomatik güvenlik güncellemeleri kurulu.",
                       "en": "Automatic security updates are installed."}}


def check_firewall_enabled():
    # systemctl root gerektirmez
    code, out = run(["systemctl", "is-enabled", "ufw"])
    active_code, active = run(["systemctl", "is-active", "ufw"])
    conf = read_file("/etc/ufw/ufw.conf") or ""
    conf_enabled = "ENABLED=yes" in conf

    if active.strip() == "active" and conf_enabled:
        return {"status": OK,
                "detail": {"tr": "Güvenlik duvarı etkin ve çalışıyor.",
                           "en": "The firewall is enabled and running."}}
    if active.strip() == "active" and not conf_enabled:
        return {"status": WARN,
                "detail": {"tr": "ufw servisi çalışıyor ancak kural uygulaması "
                                 "kapalı görünüyor.",
                           "en": "The ufw service is running but rule enforcement "
                                 "appears to be off."}}
    return {"status": FAIL,
            "detail": {"tr": "Güvenlik duvarı kapalı. Gelen bağlantılar "
                             "filtrelenmiyor.",
                       "en": "The firewall is off. Incoming connections are not "
                             "being filtered."}}


def check_firewall_policy():
    if not is_root():
        return {"status": NEEDROOT,
                "detail": {"tr": "Varsayılan kurallar root yetkisiyle okunabilir.",
                           "en": "Default policies can only be read as root."}}
    code, out = run([bin_path("ufw"), "status", "verbose"])
    if code != 0:
        return {"status": INFO,
                "detail": {"tr": "ufw durumu okunamadı.",
                           "en": "Could not read ufw status."}}
    match = re.search(r"Default:\s*(.+)", out)
    if not match:
        return {"status": INFO,
                "detail": {"tr": "Varsayılan kural bulunamadı.",
                           "en": "Default policy not found."}}
    policy = match.group(1).strip()
    if "deny (incoming)" in policy or "reject (incoming)" in policy:
        return {"status": OK,
                "detail": {"tr": f"Gelen bağlantılar varsayılan olarak "
                                 f"engelleniyor. ({policy})",
                           "en": f"Incoming connections are denied by default. "
                                 f"({policy})"}}
    return {"status": WARN,
            "detail": {"tr": f"Gelen bağlantılar için varsayılan kural "
                             f"kısıtlayıcı değil. ({policy})",
                       "en": f"The default policy for incoming traffic is not "
                             f"restrictive. ({policy})"}}


def check_listening_ports():
    code, out = run(["ss", "-tulnH"])
    if code != 0:
        return {"status": INFO,
                "detail": {"tr": "Dinlenen portlar okunamadı.",
                           "en": "Could not read listening ports."}}
    external = []
    local_only = 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        proto = parts[0]
        local = parts[4]
        addr, _, port = local.rpartition(":")
        addr = addr.strip("[]")
        if addr in ("127.0.0.1", "::1", "localhost"):
            local_only += 1
        else:
            external.append(f"{proto}/{port}")
    if not external:
        return {"status": OK,
                "detail": {"tr": f"Dışarıya açık dinleyen servis yok. "
                                 f"({local_only} servis yalnızca yerelde)",
                           "en": f"No services are listening externally. "
                                 f"({local_only} local-only)"}}
    listed = ", ".join(sorted(set(external))[:10])
    return {"status": WARN,
            "detail": {"tr": f"{len(set(external))} servis tüm arayüzlerde "
                             f"dinliyor: {listed}",
                       "en": f"{len(set(external))} service(s) listening on all "
                             f"interfaces: {listed}"}}


def check_fail2ban():
    _, active = run(["systemctl", "is-active", "fail2ban"])
    if active.strip() == "active":
        return {"status": OK,
                "detail": {"tr": "fail2ban çalışıyor, tekrarlayan başarısız "
                                 "girişler engelleniyor.",
                           "en": "fail2ban is running; repeated failed logins are "
                                 "being blocked."}}
    if not have("fail2ban-client"):
        return {"status": INFO,
                "detail": {"tr": "fail2ban kurulu değil.",
                           "en": "fail2ban is not installed."}}
    return {"status": WARN,
            "detail": {"tr": "fail2ban kurulu ama çalışmıyor.",
                       "en": "fail2ban is installed but not running."}}


# --- AppArmor ----------------------------------------------------------------

def _systemd_durum(birim):
    """(acilista_etkin, su_an_calisiyor) dondurur; root gerektirmez."""
    _, enabled = run(["systemctl", "is-enabled", birim])
    _, active = run(["systemctl", "is-active", birim])
    return (enabled.strip() in ("enabled", "enabled-runtime"),
            active.strip() == "active")


def check_apparmor_enabled():
    if not have("apparmor_parser"):
        return {"status": INFO,
                "detail": {"tr": "AppArmor kurulu değildir.",
                           "en": "AppArmor is not installed."}}
    kernel = (read_file("/sys/module/apparmor/parameters/enabled") or "").strip()
    if kernel != "Y":
        return {"status": WARN,
                "detail": {"tr": "AppArmor çekirdekte etkin değildir. Bu uygulama "
                                 "çekirdek açılış parametrelerini değiştirmez.",
                           "en": "AppArmor is not enabled in the kernel. This "
                                 "application does not change kernel boot "
                                 "parameters."}}
    enabled, running = _systemd_durum("apparmor")
    if enabled and running:
        return {"status": OK,
                "detail": {"tr": "AppArmor etkindir ve sistem açılışında "
                                 "başlatılmaktadır.",
                           "en": "AppArmor is enabled and is started at boot."}}
    if running and not enabled:
        return {"status": FAIL,
                "detail": {"tr": "AppArmor şu anda çalışmaktadır ancak sistem "
                                 "açılışında başlatılmayacaktır.",
                           "en": "AppArmor is currently running but will not be "
                                 "started at boot."}}
    if enabled and not running:
        return {"status": FAIL,
                "detail": {"tr": "AppArmor sistem açılışında başlatılacaktır "
                                 "ancak şu anda çalışmamaktadır.",
                           "en": "AppArmor will be started at boot but is not "
                                 "currently running."}}
    return {"status": FAIL,
            "detail": {"tr": "AppArmor devre dışıdır. Uygulamalar profillerle "
                             "kısıtlanmamaktadır.",
                       "en": "AppArmor is disabled. Applications are not "
                             "restricted by profiles."}}


_AA_SATIR = re.compile(r"^(.*) \((enforce|complain|kill|unconfined|prompt|mixed)\)$")


def parse_aa_profiles(metin):
    """/sys/kernel/security/apparmor/profiles icerigini sayar."""
    sayac = {"enforce": 0, "complain": 0, "diger": 0}
    for satir in (metin or "").splitlines():
        eslesme = _AA_SATIR.match(satir.strip())
        if not eslesme:
            continue
        mod = eslesme.group(2)
        sayac[mod if mod in ("enforce", "complain") else "diger"] += 1
    sayac["toplam"] = sayac["enforce"] + sayac["complain"] + sayac["diger"]
    return sayac


def check_apparmor_profiles():
    if not is_root():
        return {"status": NEEDROOT,
                "detail": {"tr": "Yüklü profillerin listesi yalnızca yönetici "
                                 "yetkisiyle okunabilir.",
                           "en": "The list of loaded profiles can only be read "
                                 "with administrator privileges."}}
    if not have("apparmor_parser"):
        return {"status": INFO,
                "detail": {"tr": "AppArmor kurulu değildir.",
                           "en": "AppArmor is not installed."}}
    metin = read_file("/sys/kernel/security/apparmor/profiles")
    if metin is None:
        return {"status": INFO,
                "detail": {"tr": "Profil listesi okunamadı (AppArmor devre dışı "
                                 "olabilir).",
                           "en": "The profile list could not be read (AppArmor "
                                 "may be disabled)."}}
    sayac = parse_aa_profiles(metin)
    _, running = _systemd_durum("apparmor")
    if sayac["toplam"] == 0:
        if running:
            return {"status": WARN,
                    "detail": {"tr": "AppArmor çalışmaktadır ancak yüklü profil "
                                     "bulunmamaktadır.",
                               "en": "AppArmor is running but no profiles are "
                                     "loaded."}}
        return {"status": INFO,
                "detail": {"tr": "Yüklü profil bulunmamaktadır (AppArmor devre "
                                 "dışı).",
                           "en": "No profiles are loaded (AppArmor is disabled)."}}
    ozet_tr = (f"{sayac['toplam']} profil yüklüdür: {sayac['enforce']} zorlayıcı, "
               f"{sayac['complain']} şikâyet (yalnızca kayıt) modundadır.")
    ozet_en = (f"{sayac['toplam']} profiles are loaded: {sayac['enforce']} "
               f"enforcing, {sayac['complain']} in complain (log-only) mode.")
    if not running:
        return {"status": WARN,
                "detail": {"tr": "AppArmor hizmeti devre dışı görünmektedir "
                                 "ancak profiller hâlâ yüklüdür. " + ozet_tr,
                           "en": "The AppArmor service appears disabled but "
                                 "profiles are still loaded. " + ozet_en}}
    if sayac["enforce"] == 0:
        return {"status": WARN,
                "detail": {"tr": ozet_tr + " Zorlayıcı modda profil "
                                 "bulunmamaktadır; profiller engelleme "
                                 "yapmamakta, yalnızca kayıt tutmaktadır.",
                           "en": ozet_en + " No profile is in enforce mode; "
                                 "profiles only log and do not block."}}
    return {"status": OK, "detail": {"tr": ozet_tr, "en": ozet_en}}


# --- Ayrintili taramalar (istege bagli, yonetici yetkisi ister) --------------

def is_live():
    """Canli oturumda mi calisiyoruz (kalici kayit tutulamaz)."""
    return "boot=live" in (read_file("/proc/cmdline") or "")


# CarotOS'un kendi ozellestirmeleri nedeniyle paket ozetinden farkli olmasi
# beklenen dosyalar.
DEBSUMS_BEKLENEN = ("/usr/lib/os-release",)

_DEBSUMS_YOL = re.compile(r"changed file (\S+)|^(\S+)\s+FAILED", re.I)


def parse_debsums(code, out):
    """debsums -s ciktisini yorumlar. Cikti bicimi tum surumlerde ayni
    olmayabilir; yorumlanamazsa ham satirlar gosterilir."""
    if code in (126, 127) and not out:
        return {"status": INFO,
                "detail": {"tr": "Tarama çalıştırılamadı.",
                           "en": "The scan could not be run."}, "extra": []}
    bulgular = []
    for satir in (out or "").splitlines():
        metin = satir.strip()
        dusuk = metin.lower()
        if metin and ("failed" in dusuk or "changed" in dusuk):
            eslesme = _DEBSUMS_YOL.search(metin)
            yol = (eslesme.group(1) or eslesme.group(2)) if eslesme else None
            bulgular.append((yol, metin))
    beklenen = [b for b in bulgular if b[0] in DEBSUMS_BEKLENEN]
    beklenmeyen = [b for b in bulgular if b[0] not in DEBSUMS_BEKLENEN]
    ekstra = ([{"text": m, "explain": {
                   "tr": "CarotOS özelleştirmesi nedeniyle beklenen farklılıktır.",
                   "en": "An expected difference caused by a CarotOS "
                         "customisation."}} for _, m in beklenen]
              + [{"text": m, "explain": None} for _, m in beklenmeyen])[:40]
    if beklenmeyen:
        n = len(beklenmeyen)
        return {"status": WARN,
                "detail": {"tr": f"{n} dosyanın sağlama toplamı paketle "
                                 f"uyuşmamaktadır. Dosya adları incelenmelidir.",
                           "en": f"The checksum of {n} files does not match the "
                                 f"package. The file names should be reviewed."},
                "extra": ekstra}
    if code == 0 or beklenen:
        k = len(beklenen)
        tr = "Paketlerle dağıtılan dosyalarda değişiklik tespit edilmemiştir."
        en = "No changes were detected in files distributed with packages."
        if k:
            tr = (f"Beklenmeyen değişiklik tespit edilmemiştir; yalnızca "
                  f"CarotOS özelleştirmesi olan {k} dosya farklıdır.")
            en = (f"No unexpected changes were detected; only {k} file(s) "
                  f"differ because of CarotOS customisation.")
        return {"status": OK, "detail": {"tr": tr, "en": en}, "extra": ekstra}
    ham = [s.strip() for s in (out or "").splitlines() if s.strip()][:20]
    return {"status": INFO,
            "detail": {"tr": f"Çıktı yorumlanamadı (çıkış kodu {code}).",
                       "en": f"The output could not be interpreted (exit code {code})."},
            "extra": [{"text": s, "explain": None} for s in ham]}


_RKH_UYARI = re.compile(r"^\s*Warning:\s*(.*)$")

# rkhunter'in kendi ön koşul denetimi: tehdit bulgusu degildir, yalnizca
# bazi alt denetimlerin atlandigini bildirir.
_RKH_ONKOSUL = re.compile(r"prerequisites", re.I)
_RKH_ONKOSUL_ACIKLAMA = {
    "tr": "rkhunter bir ön koşulu sağlayamamıştır ve bazı alt denetimleri "
          "(örneğin betikle değiştirilmiş komutların denetimi) atlamıştır. "
          "Bu bir tehdit bulgusu değildir. Ayrıntı /var/log/rkhunter.log "
          "dosyasındadır.",
    "en": "rkhunter could not satisfy a prerequisite and skipped some "
          "sub-checks (for example the check for commands replaced by "
          "scripts). This is not a threat finding. Details are in "
          "/var/log/rkhunter.log.",
}

_RKH_ACIKLAMALAR = [
    (re.compile(r"replaced by a script", re.I),
     {"tr": "Bir sistem komutu betikle değiştirilmiş görünmektedir. Debian'da "
            "bazı komutlar zaten betik olarak dağıtıldığından bu uyarı "
            "çoğunlukla yanlış pozitiftir.",
      "en": "A system command appears to have been replaced by a script. Some "
            "Debian commands are distributed as scripts, so this warning is "
            "usually a false positive."}),
    (re.compile(r"hidden (file|dir)", re.I),
     {"tr": "Gizli bir dosya veya dizin bulunmuştur. Sistem bileşenleri de "
            "gizli dosya kullanabilir; ad tanınıyorsa uyarı göz ardı "
            "edilebilir.",
      "en": "A hidden file or directory was found. System components may also "
            "use hidden files; the warning can be disregarded if the name is "
            "recognised."}),
    (re.compile(r"shared memory", re.I),
     {"tr": "Bazı masaüstü bileşenleri (ekran, oturum, terminal) büyük "
            "paylaşımlı bellek kullanır; bu normaldir. Listelenen süreçler "
            "tanınan uygulamalara aitse uyarı göz ardı edilebilir; "
            "tanınmayan bir süreç varsa incelenmelidir.",
      "en": "Some desktop components (display, session, terminal) use large "
            "shared memory segments; this is normal. If the listed processes "
            "belong to recognised applications the warning can be "
            "disregarded; an unrecognised process should be investigated."}),
    (re.compile(r"propert", re.I),
     {"tr": "Bir dosyanın özellikleri kayıtlı değerlerden farklıdır. Sistem "
            "güncellemesinden sonra beklenen bir durumdur; güncelleme "
            "yapılmadıysa incelenmelidir.",
      "en": "A file's properties differ from the recorded values. This is "
            "expected after a system update; if no update was made, it should "
            "be investigated."}),
    (re.compile(r"ssh|PermitRootLogin", re.I),
     {"tr": "SSH yapılandırması rkhunter'ın beklediği değerlerden farklıdır. "
            "Bu bir yapılandırma uyuşmazlığıdır ve tek başına tehdit "
            "göstergesi değildir.",
      "en": "The SSH configuration differs from the values rkhunter expects. "
            "This is a configuration mismatch and is not a threat indicator "
            "by itself."}),
    (re.compile(r"no copy of|\.dat|database|propupd", re.I),
     {"tr": "Karşılaştırma kaydı bulunamamış veya güncel değildir. İlk "
            "çalıştırmada beklenen bir durumdur. Sistemin güvenilir olduğu "
            "doğrulandıysa “Kaydı yenile” ile oluşturulabilir.",
      "en": "The comparison record is missing or out of date. If the system is "
            "known to be trustworthy, it can be created with “Refresh "
            "record”."}),
]

_RKH_VARSAYILAN = {
    "tr": "Bu uyarının ayrıntıları incelenmelidir. Sistem güncellemesinden sonra "
          "yanlış pozitif olabilir; emin olunamıyorsa uyarı metni araştırılmalı "
          "veya proje ekibine bildirilmelidir.",
    "en": "The details of this warning should be reviewed. It may be a false "
          "positive after a system update; if unsure, the warning text should "
          "be researched or reported to the project team.",
}


def rkhunter_aciklama(metin):
    for desen, aciklama in _RKH_ACIKLAMALAR:
        if desen.search(metin):
            return aciklama
    return _RKH_VARSAYILAN


_RKH_BELLEK = re.compile(r"shared memory", re.I)


def parse_rkhunter(code, out, own_pid=None):
    if code in (126, 127) and not out:
        return {"status": INFO,
                "detail": {"tr": "Tarama çalıştırılamadı.",
                           "en": "The scan could not be run."}, "extra": []}
    uyarilar, notlar = [], []
    # Bir uyarinin altindaki girintili satirlar (ornegin surec listesi) o
    # uyariya aittir ve birlikte gosterilir.
    gecerli, ilk = None, ""
    for satir in (out or "").splitlines():
        eslesme = _RKH_UYARI.match(satir)
        if eslesme and eslesme.group(1).strip():
            ilk = eslesme.group(1).strip()
            gecerli = [ilk]
            (notlar if _RKH_ONKOSUL.search(ilk) else uyarilar).append(gecerli)
        elif gecerli is not None and satir[:1] in (" ", "\t") and satir.strip():
            gecerli.append(satir.strip())
        else:
            gecerli = None
    # Taramayi baslatan bu uygulamanin kendi paylasimli bellegi (GTK ekran
    # cizimi) rkhunter tarafindan listelenir; yalnizca bu uygulamanin kendi
    # surec numarasi listeden cikarilir, baska hicbir surec cikarilmaz.
    pid = own_pid if own_pid is not None else os.getpid()
    kendi = re.compile(r"\bPID:\s*%d\b" % pid)
    suzulen, elendi = [], False
    for u in uyarilar:
        if _RKH_BELLEK.search(u[0]):
            ayrintilar = [x for x in u[1:] if not kendi.search(x)]
            if len(u) > 1 and not ayrintilar:
                elendi = True
                continue
            u = [u[0]] + ayrintilar
        suzulen.append(u)
    uyarilar = ["\n".join(u) for u in suzulen]
    notlar = ["\n".join(m) for m in notlar]
    not_ekstra = [{"text": m, "explain": _RKH_ONKOSUL_ACIKLAMA} for m in notlar]
    if uyarilar:
        n = len(uyarilar)
        return {"status": WARN,
                "detail": {"tr": f"{n} uyarı tespit edilmiştir. Her uyarının "
                                 f"altında olası anlamı belirtilmiştir.",
                           "en": f"{n} warnings were detected. The possible "
                                 f"meaning is given under each warning."},
                "extra": [{"text": u, "explain": rkhunter_aciklama(u)}
                          for u in uyarilar[:40]] + not_ekstra}
    if notlar:
        return {"status": INFO,
                "detail": {"tr": "Bilinen izlere rastlanmamıştır; ancak bir ön "
                                 "koşul uyarısı nedeniyle bazı alt denetimler "
                                 "atlanmıştır. Bu sonuç sistemin güvenli "
                                 "olduğunu garanti etmez.",
                           "en": "No known traces were found, but some "
                                 "sub-checks were skipped because of a "
                                 "prerequisite warning. This result does not "
                                 "guarantee that the system is secure."},
                "extra": not_ekstra}
    if code == 0 or elendi:
        return {"status": OK,
                "detail": {"tr": "Bilinen izlere rastlanmamıştır. Bu sonuç "
                                 "sistemin güvenli olduğunu garanti etmez.",
                           "en": "No known traces were found. This result does "
                                 "not guarantee that the system is secure."},
                "extra": []}
    ham = [s.strip() for s in (out or "").splitlines() if s.strip()][:20]
    return {"status": INFO,
            "detail": {"tr": f"Çıktı yorumlanamadı (çıkış kodu {code}).",
                       "en": f"The output could not be interpreted (exit code {code})."},
            "extra": [{"text": s, "explain": None} for s in ham]}


def deep_command(binary, args):
    """Ayrintili tarama komutu. Araclar Turkce dil ayariyla bazi desenleri
    yanlis yorumladigindan (ornegin [a-z] araligi) ve ciktilari Ingilizce
    metinlere gore yorumlandigindan LC_ALL=C ile calistirilir."""
    return (["pkexec", bin_path("env"), "LC_ALL=C", bin_path(binary)]
            + list(args))


# Sabit komutlar: kullanici metni argumana hic girmez. rkhunter'a
# "--syslog none" verilir: yapilandirmadaki syslog degeri dogrulanirken
# bazi sistemlerde tarama baslamadan hata veriyordu.
DEEP_SCANS = [
    {
        "id": "debsums", "binary": "debsums", "args": ["-s"], "timeout": 900,
        "parse": parse_debsums,
        "title": {"tr": "Paket bütünlüğü denetimi (debsums)",
                  "en": "Package integrity check (debsums)"},
        "why": {"tr": "Kurulu paketlerin dosyalarını, paketle birlikte "
                      "dağıtılan sağlama toplamlarıyla karşılaştırır. Sağlama "
                      "toplamı uyuşmayan dosya değiştirilmiş ya da bozulmuş "
                      "olabilir.",
                "en": "Compares the files of installed packages with the "
                      "checksums distributed with the package. A file whose "
                      "checksum does not match may have been modified or "
                      "corrupted."},
    },
    {
        "id": "rkhunter", "binary": "rkhunter",
        "args": ["--check", "--skip-keypress", "--report-warnings-only",
                 "--nocolors", "--syslog", "none"],
        "timeout": 1800, "parse": parse_rkhunter, "live_note": True,
        "propupd_args": ["--propupd", "--syslog", "none"],
        "propupd_warning": {
            "tr": "Sistemin mevcut durumu temiz kabul edilerek karşılaştırma "
                  "kaydı olarak saklanacaktır. İşleme yalnızca sistemin "
                  "güvenilir olduğundan emin olunduğunda devam edilmelidir; "
                  "ele geçirilmiş bir sistemde bu kayıt sorunu normal "
                  "gösterir.",
            "en": "The current state of the system will be stored as the "
                  "clean comparison record. Continue only if the system is "
                  "known to be trustworthy; on a compromised system this "
                  "record makes the problem appear normal."},
        "title": {"tr": "Rootkit denetimi (rkhunter)",
                  "en": "Rootkit check (rkhunter)"},
        "why": {"tr": "Bilinen rootkit izlerini, gizli dosyaları ve temel "
                      "sistem programlarındaki değişiklikleri denetler. Sistem "
                      "güncellemelerinden sonra yanlış pozitif uyarı "
                      "üretebilir; her uyarının altındaki açıklama dikkate "
                      "alınmalıdır.",
                "en": "Checks for known rootkit traces, hidden files and "
                      "changes in core system programs. It may produce false "
                      "positive warnings after system updates; the explanation "
                      "under each warning should be taken into account."},
    },
]


def check_root_locked():
    if not is_root():
        return {"status": NEEDROOT,
                "detail": {"tr": "Root hesabının durumu root yetkisiyle "
                                 "görülebilir.",
                           "en": "The root account state requires root to inspect."}}
    code, out = run([bin_path("passwd"), "-S", "root"])
    if code != 0 or not out:
        return {"status": INFO,
                "detail": {"tr": "Root hesabının durumu okunamadı.",
                           "en": "Could not read the root account state."}}
    parts = out.split()
    state = parts[1] if len(parts) > 1 else "?"
    if state == "L":
        return {"status": OK,
                "detail": {"tr": "Root hesabı kilitli. Yönetici işlemleri sudo "
                                 "üzerinden yapılıyor ve günlüğe kaydediliyor.",
                           "en": "The root account is locked. Administrative work "
                                 "goes through sudo and is logged."}}
    if state == "NP":
        return {"status": FAIL,
                "detail": {"tr": "Root hesabının parolası yok. Bu ciddi bir "
                                 "güvenlik açığıdır.",
                           "en": "The root account has no password. This is a "
                                 "serious security hole."}}
    return {"status": WARN,
            "detail": {"tr": "Root hesabı parolalı ve açık. CarotOS'un "
                             "varsayılanı kilitli hesaptır.",
                       "en": "The root account is enabled with a password. The "
                             "CarotOS default is a locked account."}}


def check_empty_passwords():
    if not is_root():
        return {"status": NEEDROOT,
                "detail": {"tr": "Parola alanları root yetkisiyle okunabilir.",
                           "en": "Password fields can only be read as root."}}
    shadow = read_file("/etc/shadow")
    if shadow is None:
        return {"status": INFO,
                "detail": {"tr": "/etc/shadow okunamadı.",
                           "en": "Could not read /etc/shadow."}}
    empty = []
    for line in shadow.splitlines():
        fields = line.split(":")
        if len(fields) > 1 and fields[1] == "":
            empty.append(fields[0])
    if empty:
        return {"status": FAIL,
                "detail": {"tr": f"Parolasız hesap var: {', '.join(empty)}",
                           "en": f"Account(s) without a password: "
                                 f"{', '.join(empty)}"}}
    return {"status": OK,
            "detail": {"tr": "Parolasız hesap yok.",
                       "en": "No accounts without a password."}}


def check_sudo_users():
    code, out = run(["getent", "group", "sudo"])
    members = ""
    if code == 0 and ":" in out:
        members = out.split(":")[-1]
    names = [n for n in members.split(",") if n]
    if not names:
        return {"status": WARN,
                "detail": {"tr": "sudo grubunda kullanıcı yok. Yönetici işlemi "
                                 "yapılamayabilir.",
                           "en": "No users are in the sudo group. Administrative "
                                 "work may be impossible."}}
    if len(names) > 3:
        return {"status": WARN,
                "detail": {"tr": f"{len(names)} kullanıcı yönetici yetkisine "
                                 f"sahip: {', '.join(names)}",
                           "en": f"{len(names)} users have administrator rights: "
                                 f"{', '.join(names)}"}}
    return {"status": OK,
            "detail": {"tr": f"Yönetici yetkisi olan kullanıcılar: "
                             f"{', '.join(names)}",
                       "en": f"Users with administrator rights: "
                             f"{', '.join(names)}"}}


def check_ssh_server():
    _, active = run(["systemctl", "is-active", "ssh"])
    if active.strip() != "active":
        return {"status": OK,
                "detail": {"tr": "SSH sunucusu çalışmıyor. Uzaktan oturum açma "
                                 "kapalı.",
                           "en": "The SSH server is not running. Remote login is "
                                 "closed."}}
    config = read_file("/etc/ssh/sshd_config") or ""
    permit = re.search(r"^\s*PermitRootLogin\s+(\S+)", config, re.M | re.I)
    if permit and permit.group(1).lower() in ("yes", "prohibit-password"):
        return {"status": FAIL,
                "detail": {"tr": f"SSH açık ve root ile oturum açmaya izin "
                                 f"veriyor (PermitRootLogin {permit.group(1)}).",
                           "en": f"SSH is open and permits root login "
                                 f"(PermitRootLogin {permit.group(1)})."}}
    return {"status": WARN,
            "detail": {"tr": "SSH sunucusu çalışıyor. İhtiyacınız yoksa kapatın.",
                       "en": "The SSH server is running. Disable it if you do not "
                             "need it."}}


def check_auth_failures():
    if not is_root():
        return {"status": NEEDROOT,
                "detail": {"tr": "Kimlik doğrulama günlüğü root yetkisiyle "
                                 "okunabilir.",
                           "en": "The authentication log requires root to read."}}
    code, out = run(["journalctl", "-b", "--no-pager", "-g",
                     "authentication failure|Failed password", "-q"], timeout=20)
    if code != 0:
        return {"status": INFO,
                "detail": {"tr": "Günlük okunamadı.",
                           "en": "Could not read the log."}}
    count = len([l for l in out.splitlines() if l.strip()])
    if count > 20:
        return {"status": WARN,
                "detail": {"tr": f"Bu açılışta {count} başarısız kimlik doğrulama "
                                 f"denemesi kaydedilmiş.",
                           "en": f"{count} failed authentication attempts recorded "
                                 f"this boot."}}
    return {"status": OK,
            "detail": {"tr": f"Bu açılışta {count} başarısız giriş denemesi var.",
                       "en": f"{count} failed login attempts this boot."}}


def check_disk_usage():
    code, out = run(["df", "-P", "/"])
    if code != 0:
        return {"status": INFO,
                "detail": {"tr": "Disk kullanımı okunamadı.",
                           "en": "Could not read disk usage."}}
    lines = out.splitlines()
    if len(lines) < 2:
        return {"status": INFO,
                "detail": {"tr": "Disk kullanımı okunamadı.",
                           "en": "Could not read disk usage."}}
    parts = lines[1].split()
    try:
        percent = int(parts[4].rstrip("%"))
    except (IndexError, ValueError):
        return {"status": INFO,
                "detail": {"tr": "Disk kullanımı çözümlenemedi.",
                           "en": "Could not parse disk usage."}}
    free_kb = int(parts[3]) if parts[3].isdigit() else 0
    free_gb = free_kb / 1048576
    if percent >= 95:
        status = FAIL
    elif percent >= 85:
        status = WARN
    else:
        status = OK
    return {"status": status,
            "detail": {"tr": f"Kök bölüm %{percent} dolu, {free_gb:.1f} GB boş.",
                       "en": f"Root partition is {percent}% full, {free_gb:.1f} GB "
                             f"free."}}


def check_memory():
    content = read_file("/proc/meminfo") or ""
    values = {}
    for line in content.splitlines():
        key, _, rest = line.partition(":")
        digits = re.search(r"(\d+)", rest)
        if digits:
            values[key] = int(digits.group(1))
    total = values.get("MemTotal", 0) / 1048576
    available = values.get("MemAvailable", 0) / 1048576
    used = total - available
    return {"status": INFO,
            "detail": {"tr": f"{used:.2f} GB / {total:.2f} GB kullanımda",
                       "en": f"{used:.2f} GB / {total:.2f} GB in use"}}


def check_world_writable():
    """/etc altinda herkesin yazabildigi dosya guvenlik riskidir."""
    code, out = run(["find", "/etc", "-xdev", "-type", "f", "-perm", "-0002",
                     "-not", "-path", "*/shadow*"], timeout=25)
    if code not in (0, 1):
        return {"status": INFO,
                "detail": {"tr": "Dosya izinleri taranamadı.",
                           "en": "Could not scan file permissions."}}
    files = [l for l in out.splitlines() if l.strip() and l.startswith("/etc")]
    if files:
        return {"status": FAIL,
                "detail": {"tr": f"/etc altında herkesin yazabildiği "
                                 f"{len(files)} dosya var: "
                                 f"{', '.join(files[:4])}",
                           "en": f"{len(files)} world-writable file(s) under /etc: "
                                 f"{', '.join(files[:4])}"}}
    return {"status": OK,
            "detail": {"tr": "/etc altında herkesin yazabildiği dosya yok.",
                       "en": "No world-writable files under /etc."}}


# ---------------------------------------------------------------------------
# Denetim kaydi
# ---------------------------------------------------------------------------

CATEGORIES = [
    ("system",   {"tr": "Sistem",              "en": "System"}),
    ("updates",  {"tr": "Güncellemeler",       "en": "Updates"}),
    ("repos",    {"tr": "Depolar",             "en": "Repositories"}),
    ("network",  {"tr": "Ağ ve güvenlik duvarı", "en": "Network & firewall"}),
    ("protect",  {"tr": "Koruma katmanları",   "en": "Protection layers"}),
    ("accounts", {"tr": "Hesaplar ve erişim",  "en": "Accounts & access"}),
    ("storage",  {"tr": "Disk ve bellek",      "en": "Storage & memory"}),
    ("deep",     {"tr": "Ayrıntılı taramalar", "en": "Detailed scans"}),
]

CHECKS = [
    {
        "id": "os_info", "category": "system", "func": check_os_info,
        "title": {"tr": "Sistem bilgisi", "en": "System information"},
        "why": {"tr": "Hangi sürümü ve çekirdeği kullandığınız, destek alırken "
                      "ilk sorulan bilgidir.",
                "en": "The version and kernel you run is the first thing asked "
                      "when you seek support."},
    },
    {
        "id": "uptime", "category": "system", "func": check_uptime,
        "title": {"tr": "Çalışma süresi", "en": "Uptime"},
        "why": {"tr": "Uzun süre yeniden başlatılmayan sistemler, kurulmuş "
                      "çekirdek güncellemelerinden yararlanamaz.",
                "en": "Systems that go a long time without a restart do not "
                      "benefit from installed kernel updates."},
    },
    {
        "id": "reboot", "category": "system", "func": check_reboot_required,
        "title": {"tr": "Yeniden başlatma durumu", "en": "Reboot status"},
        "why": {"tr": "Çekirdek ve kütüphane güncellemeleri ancak yeniden "
                      "başlatmadan sonra tam olarak devreye girer.",
                "en": "Kernel and library updates only take full effect after a "
                      "restart."},
        "fix": "sudo reboot",
        "action": {"cmd": 'systemctl reboot',
                   "label": {'tr': 'Yeniden başlat', 'en': 'Restart'},
                   "confirm": True},
    },
    {
        "id": "failed_units", "category": "system", "func": check_failed_units,
        "title": {"tr": "Başarısız servisler", "en": "Failed services"},
        "why": {"tr": "Başarısız bir servis, sessizce devre dışı kalmış bir "
                      "koruma katmanı anlamına gelebilir.",
                "en": "A failed service can mean a protective layer has quietly "
                      "stopped working."},
        "fix": "systemctl --failed",
    },
    {
        "id": "updates", "category": "updates", "func": check_pending_updates,
        "title": {"tr": "Bekleyen güncellemeler", "en": "Pending updates"},
        "why": {"tr": "Yayımlanmış bir güvenlik yaması kurulmadığı sürece "
                      "sistemi korumaz. Saldırganlar bilinen açıkları hedefler.",
                "en": "A published security patch protects nothing until it is "
                      "installed. Attackers target known holes."},
        "fix": "sudo apt update && sudo apt upgrade",
        "action": {"cmd": 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y upgrade',
                   "label": {'tr': 'Güncelle', 'en': 'Update'},
                   "confirm": True},
    },
    {
        "id": "apt_age", "category": "updates", "func": check_last_apt_update,
        "title": {"tr": "Paket listesinin tazeliği", "en": "Package list freshness"},
        "why": {"tr": "Paket listesi eskiyse sistem yeni yamalardan haberdar "
                      "olmaz; güncelleme yok sanır.",
                "en": "If the package list is stale the system does not learn "
                      "about new patches and believes it is up to date."},
        "fix": "sudo apt update",
        "action": {"cmd": 'apt-get update',
                   "label": {'tr': 'Listeyi yenile', 'en': 'Refresh list'},
                   "confirm": False},
    },
    {
        "id": "unattended", "category": "updates", "func": check_unattended,
        "title": {"tr": "Otomatik güvenlik güncellemeleri",
                  "en": "Automatic security updates"},
        "why": {"tr": "Elle güncelleme unutulur. Otomatik güncelleme, kritik "
                      "yamaların gecikmeden uygulanmasını sağlar.",
                "en": "Manual updates get forgotten. Automatic updates ensure "
                      "critical patches are applied without delay."},
        "fix": "sudo apt install unattended-upgrades",
        "action": {"cmd": 'DEBIAN_FRONTEND=noninteractive apt-get install -y unattended-upgrades',
                   "label": {'tr': 'Kur', 'en': 'Install'},
                   "confirm": False},
    },
    {
        "id": "repos", "category": "repos", "func": check_repositories,
        "title": {"tr": "Yazılım depoları", "en": "Software repositories"},
        "why": {"tr": "Depo tanımlı değilse sistem ne yazılım kurabilir ne de "
                      "güvenlik güncellemesi alabilir. Sessizce kapalı kalır.",
                "en": "Without a repository the system can neither install "
                      "software nor receive security updates. It fails silently."},
        "fix": "cat /etc/apt/sources.list.d/debian.sources",
        "action": {"cmd": "printf '%s\\n' 'Types: deb' 'URIs: http://deb.debian.org/debian' 'Suites: trixie trixie-updates' 'Components: main contrib non-free non-free-firmware' 'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' '' 'Types: deb' 'URIs: http://security.debian.org/debian-security' 'Suites: trixie-security' 'Components: main contrib non-free non-free-firmware' 'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' > /etc/apt/sources.list.d/debian.sources && sed -i 's|^deb cdrom:|#deb cdrom:|' /etc/apt/sources.list; apt-get update",
                   "label": {'tr': 'Depoları yapılandır', 'en': 'Configure repositories'},
                   "confirm": True},
    },
    {
        "id": "fw_enabled", "category": "network", "func": check_firewall_enabled,
        "title": {"tr": "Güvenlik duvarı", "en": "Firewall"},
        "why": {"tr": "Güvenlik duvarı, dışarıdan gelen istenmeyen bağlantıları "
                      "servise ulaşmadan durdurur.",
                "en": "The firewall stops unwanted inbound connections before "
                      "they reach a service."},
        "fix": "sudo ufw enable",
        "action": {"cmd": 'ufw --force enable',
                   "label": {'tr': 'Duvarı aç', 'en': 'Enable firewall'},
                   "confirm": False},
        "off": {"cmd": 'ufw disable',
                "label": {'tr': 'Devre dışı bırak', 'en': 'Disable'},
                "confirm": True,
                "warning": {"tr": "Güvenlik duvarı devre dışı bırakılacaktır ve "
                                  "yeniden başlatmadan sonra da devre dışı "
                                  "kalacaktır. Gelen bağlantılar "
                                  "filtrelenmeyecektir. Bu karttaki düğme ile "
                                  "yeniden etkinleştirilebilir.",
                            "en": "The firewall will be disabled and will "
                                  "remain disabled after a restart. Incoming "
                                  "connections will not be filtered. It can be "
                                  "re-enabled with the button on this card."}},
    },
    {
        "id": "fw_policy", "category": "network", "func": check_firewall_policy,
        "title": {"tr": "Varsayılan kural", "en": "Default policy"},
        "why": {"tr": "Doğru varsayılan, izin verilmeyen her şeyi engellemektir. "
                      "Tersi durumda unutulan her port açık kalır.",
                "en": "The correct default is to block anything not explicitly "
                      "allowed. Otherwise every forgotten port stays open."},
        "fix": "sudo ufw default deny incoming",
        "action": {"cmd": 'ufw default deny incoming',
                   "label": {'tr': 'Varsayılanı düzelt', 'en': 'Fix default'},
                   "confirm": False},
    },
    {
        "id": "ports", "category": "network", "func": check_listening_ports,
        "title": {"tr": "Dinlenen portlar", "en": "Listening ports"},
        "why": {"tr": "Dışarıya açık her port bir giriş noktasıdır. Yalnızca "
                      "ihtiyaç duyulanlar açık olmalıdır.",
                "en": "Every externally exposed port is an entry point. Only the "
                      "ones you need should be open."},
        "fix": "ss -tuln",
    },
    {
        "id": "fail2ban", "category": "network", "func": check_fail2ban,
        "title": {"tr": "Kaba kuvvet koruması", "en": "Brute-force protection"},
        "why": {"tr": "fail2ban, art arda başarısız giriş deneyen adresleri "
                      "geçici olarak engeller.",
                "en": "fail2ban temporarily blocks addresses that repeatedly fail "
                      "to log in."},
        "fix": "sudo systemctl enable --now fail2ban",
        "action": {"cmd": 'systemctl enable --now fail2ban',
                   "label": {'tr': 'Başlat', 'en': 'Start'},
                   "confirm": False},
    },
    {
        "id": "apparmor", "category": "protect", "func": check_apparmor_enabled,
        "title": {"tr": "AppArmor (uygulama kısıtlama)",
                  "en": "AppArmor (application confinement)"},
        "why": {"tr": "AppArmor, programların yalnızca izin verilen dosya ve "
                      "kaynaklara erişmesini sağlar. Ele geçirilen bir "
                      "programın verebileceği zarar bu sayede sınırlandırılır.",
                "en": "AppArmor restricts programs to the files and resources "
                      "they are permitted to access. This limits the damage "
                      "that a compromised program can cause."},
        "fix": "sudo systemctl enable --now apparmor",
        "action": {"cmd": 'systemctl enable --now apparmor',
                   "label": {'tr': 'Etkinleştir', 'en': 'Enable'},
                   "confirm": False},
        # Hizmeti durdurmak yuklu profilleri bellekten kaldirmaz; bu nedenle
        # aa-teardown da calistirilir. Profil listesi zaten bossa basarili sayilir.
        "off": {"cmd": 'systemctl disable --now apparmor && '
                       '{ aa-teardown || [ -z "$(cat /sys/kernel/security/apparmor/profiles)" ]; }',
                "label": {'tr': 'Devre dışı bırak', 'en': 'Disable'},
                "confirm": True,
                "warning": {"tr": "AppArmor devre dışı bırakılacak, yüklü profiller "
                                  "bellekten kaldırılacak ve yeniden başlatmadan "
                                  "sonra da devre dışı kalacaktır. Programlar "
                                  "profillerle kısıtlanmayacaktır. Bu karttaki "
                                  "düğme ile yeniden etkinleştirilebilir; "
                                  "etkinleştirildiğinde çalışmakta olan "
                                  "programlar, kapatılıp yeniden açılana kadar "
                                  "kısıtlanmaz.",
                            "en": "AppArmor will be disabled, the loaded profiles "
                                  "will be removed from memory and it will remain "
                                  "disabled after a restart. Programs will not be "
                                  "restricted by profiles. It can be re-enabled "
                                  "with the button on this card; once enabled, "
                                  "programs that are already running are not "
                                  "restricted until they are closed and opened "
                                  "again."}},
    },
    {
        "id": "apparmor_profiles", "category": "protect",
        "func": check_apparmor_profiles,
        "title": {"tr": "AppArmor profilleri", "en": "AppArmor profiles"},
        "why": {"tr": "Zorlayıcı moddaki profiller ihlalleri engeller; şikâyet "
                      "modundakiler yalnızca kayıt tutar. Debian bazı "
                      "profilleri bilerek şikâyet modunda dağıtır; bu bir hata "
                      "değildir.",
                "en": "Profiles in enforce mode block violations; those in "
                      "complain mode only keep a record. Debian distributes "
                      "some profiles in complain mode on purpose; this is not "
                      "an error."},
        "fix": "sudo aa-status",
    },
    {
        "id": "root_locked", "category": "accounts", "func": check_root_locked,
        "title": {"tr": "Root hesabı", "en": "Root account"},
        "why": {"tr": "Root kilitliyken tüm yönetici işlemleri sudo üzerinden "
                      "geçer ve kim ne yaptı günlüğe yazılır.",
                "en": "With root locked, all administrative work goes through "
                      "sudo and who did what is written to the log."},
        "fix": "sudo passwd -l root",
        "action": {"cmd": 'passwd -l root',
                   "label": {'tr': "Root'u kilitle", 'en': 'Lock root'},
                   "confirm": True},
    },
    {
        "id": "empty_pw", "category": "accounts", "func": check_empty_passwords,
        "title": {"tr": "Parolasız hesaplar", "en": "Accounts without a password"},
        "why": {"tr": "Parolasız bir hesap, makineye fiziksel erişimi olan "
                      "herkese kapıyı açar.",
                "en": "An account with no password opens the door to anyone with "
                      "physical access to the machine."},
        "fix": "sudo passwd KULLANICI",
    },
    {
        "id": "sudo_users", "category": "accounts", "func": check_sudo_users,
        "title": {"tr": "Yönetici yetkisi olanlar", "en": "Users with admin rights"},
        "why": {"tr": "Yönetici yetkisi ne kadar az kişide olursa, hatalı veya "
                      "kötü niyetli değişiklik riski o kadar azalır.",
                "en": "The fewer people hold administrator rights, the lower the "
                      "risk of mistaken or malicious changes."},
        "fix": "getent group sudo",
    },
    {
        "id": "ssh", "category": "accounts", "func": check_ssh_server,
        "title": {"tr": "Uzaktan erişim (SSH)", "en": "Remote access (SSH)"},
        "why": {"tr": "Çalışan bir SSH sunucusu, ağdaki herkesin oturum açmayı "
                      "denemesine izin verir.",
                "en": "A running SSH server lets anyone on the network attempt "
                      "to log in."},
        "fix": "sudo systemctl disable --now ssh",
        "action": {"cmd": 'systemctl disable --now ssh',
                   "label": {'tr': "SSH'ı kapat", 'en': 'Disable SSH'},
                   "confirm": True},
    },
    {
        "id": "auth_fail", "category": "accounts", "func": check_auth_failures,
        "title": {"tr": "Başarısız giriş denemeleri", "en": "Failed login attempts"},
        "why": {"tr": "Olağandışı sayıda başarısız deneme, parola tahmin "
                      "saldırısının işareti olabilir.",
                "en": "An unusual number of failed attempts can signal a password "
                      "guessing attack."},
        "fix": "journalctl -b -g 'Failed password'",
    },
    {
        "id": "world_writable", "category": "accounts", "func": check_world_writable,
        "title": {"tr": "Dosya izinleri", "en": "File permissions"},
        "why": {"tr": "/etc altında herkesin yazabildiği bir ayar dosyası, "
                      "yetkisiz kullanıcının sistemi değiştirmesine izin verir.",
                "en": "A world-writable configuration file under /etc lets an "
                      "unprivileged user change the system."},
        "fix": "find /etc -type f -perm -0002",
        "action": {"cmd": "find /etc -xdev -type f -perm -0002 -not -path '*/shadow*' -exec chmod o-w {} +",
                   "label": {'tr': 'İzinleri düzelt', 'en': 'Fix permissions'},
                   "confirm": False},
    },
    {
        "id": "disk", "category": "storage", "func": check_disk_usage,
        "title": {"tr": "Disk kullanımı", "en": "Disk usage"},
        "why": {"tr": "Disk dolduğunda günlük kaydı durur, güncelleme yapılamaz "
                      "ve bazı servisler açılmaz.",
                "en": "When the disk fills up, logging stops, updates fail and "
                      "some services will not start."},
        "fix": "sudo apt clean && du -sh /var/log/*",
        "action": {"cmd": 'apt-get clean; journalctl --vacuum-size=100M; '
                          'DEBIAN_FRONTEND=noninteractive apt-get -y autoremove --purge',
                   "label": {'tr': 'Yer aç', 'en': 'Free up space'},
                   "confirm": True},
    },
    {
        "id": "memory", "category": "storage", "func": check_memory,
        "title": {"tr": "Bellek kullanımı", "en": "Memory usage"},
        "why": {"tr": "Boştaki bellek kullanımı, sistemin ne kadar hafif "
                      "çalıştığını gösterir.",
                "en": "Idle memory usage shows how lightweight the system is."},
        "fix": "free -h",
    },
]


def run_all_checks():
    """Tum denetimleri calistirir, sonuc listesi dondurur."""
    results = []
    for check in CHECKS:
        try:
            outcome = check["func"]()
        except Exception as exc:  # denetim cokerse uygulama durmasin
            outcome = {"status": INFO,
                       "detail": {"tr": f"Denetim çalıştırılamadı: {exc}",
                                  "en": f"Check could not run: {exc}"}}
        results.append({
            "id": check["id"],
            "category": check["category"],
            "status": outcome["status"],
            "detail": outcome["detail"],
        })
    return results


def score(results):
    """Puana yalnizca OK/WARN/FAIL girer; INFO ve NEEDROOT sayilmaz."""
    weights = {OK: 1.0, WARN: 0.5, FAIL: 0.0}
    counted = [r for r in results if r["status"] in weights]
    if not counted:
        return 0, 0, 0, 0
    total = sum(weights[r["status"]] for r in counted)
    percent = int(round(100 * total / len(counted)))
    ok = sum(1 for r in counted if r["status"] == OK)
    warn = sum(1 for r in counted if r["status"] == WARN)
    fail = sum(1 for r in counted if r["status"] == FAIL)
    return percent, ok, warn, fail


if __name__ == "__main__" and "--audit-json" in sys.argv:
    print(json.dumps(run_all_checks(), ensure_ascii=False))
    sys.exit(0)


# ===========================================================================
# Arayüz
# ===========================================================================

import gi  # noqa: E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib  # noqa: E402

import threading  # noqa: E402

CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "carotos-health")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

LOGO_CANDIDATES = [
    "/usr/share/carotos/welcome/logo.png",
    "/usr/share/icons/carotos/security-panel-icon.png",
]

UI = {
    "app_title": {"tr": "CarotOS Sistem Sağlığı", "en": "CarotOS System Health"},
    "summary": {"tr": "Özet", "en": "Summary"},
    "refresh": {"tr": "Yeniden denetle", "en": "Re-scan"},
    "full_audit": {"tr": "Root ile tam denetim", "en": "Full audit as root"},
    "export": {"tr": "Raporu kaydet", "en": "Save report"},
    "scanning": {"tr": "Denetleniyor…", "en": "Scanning…"},
    "ready": {"tr": "Hazır", "en": "Ready"},
    "score": {"tr": "Sağlık puanı", "en": "Health score"},
    "why": {"tr": "Neden önemli", "en": "Why it matters"},
    "suggested": {"tr": "Önerilen komut", "en": "Suggested command"},
    "language": {"tr": "Dil", "en": "Language"},
    "theme_light": {"tr": "Açık tema", "en": "Light theme"},
    "theme_dark": {"tr": "Koyu tema", "en": "Dark theme"},
    "count_ok": {"tr": "sorunsuz", "en": "passed"},
    "count_warn": {"tr": "iyileştirilebilir", "en": "could improve"},
    "count_fail": {"tr": "dikkat", "en": "needs attention"},
    "root_hint": {
        "tr": "Bazı denetimler root yetkisi ister. Tam sonuç için yukarıdaki "
              "düğmeyi kullanın.",
        "en": "Some checks require root. Use the button above for full results.",
    },
    "saved": {"tr": "Rapor kaydedildi: {path}", "en": "Report saved: {path}"},
    "save_failed": {"tr": "Rapor kaydedilemedi.", "en": "Could not save report."},
    "audit_failed": {
        "tr": "Tam denetim çalıştırılamadı (iptal edildi veya yetki verilmedi).",
        "en": "The full audit could not run (cancelled or not authorised).",
    },
    "as_root": {"tr": "root yetkisiyle denetlendi", "en": "audited as root"},
    "confirm_body": {
        "tr": "\u201c{action}\u201d işlemi uygulanacak. Devam edilsin mi?",
        "en": "The action \u201c{action}\u201d will be applied. Continue?",
    },
    "applying": {"tr": "{action} uygulanıyor…", "en": "Applying {action}…"},
    "fix_ok": {"tr": "{title}: düzeltme uygulandı, yeniden denetleniyor.",
               "en": "{title}: fix applied, re-scanning."},
    "fix_failed": {"tr": "{title}: düzeltme başarısız oldu.",
                   "en": "{title}: the fix failed."},
    "fix_cancelled": {"tr": "İşlem iptal edildi veya yetki verilmedi.",
                      "en": "The action was cancelled or not authorised."},
    "all_clear": {"tr": "Dikkat gerektiren bulgu yok.",
                  "en": "Nothing needs attention."},
    "deep_intro": {
        "tr": "Ayrıntılı taramalar yönetici yetkisi gerektirir ve uzun "
              "sürebilir. Yalnızca kullanıcı başlattığında çalıştırılır. "
              "Sonuçlar yalnızca tespit edilen bulguları listeler; sistemin "
              "güvenli olduğunu garanti etmez.",
        "en": "Detailed scans require administrator privileges and may take a "
              "long time. They are run only when started by the user. Results "
              "list only the findings detected and do not guarantee that the "
              "system is secure.",
    },
    "deep_none": {"tr": "Henüz çalıştırılmamıştır.", "en": "Not run yet."},
    "deep_missing": {"tr": "Bu araç kurulu değildir.",
                     "en": "This tool is not installed."},
    "deep_working": {"tr": "Tarama sürmektedir.", "en": "Scan in progress."},
    "deep_badge_none": {"tr": "ÇALIŞTIRILMADI", "en": "NOT RUN"},
    "deep_badge_run": {"tr": "ÇALIŞIYOR", "en": "RUNNING"},
    "deep_scan": {"tr": "Tara", "en": "Scan"},
    "deep_rescan": {"tr": "Yeniden tara", "en": "Scan again"},
    "deep_propupd": {"tr": "Kaydı yenile", "en": "Refresh record"},
    "deep_running": {"tr": "{title} çalışmaktadır. İşlem birkaç dakika "
                           "sürebilir.",
                     "en": "{title} is running. This may take a few minutes."},
    "deep_finished": {"tr": "{title}: tarama tamamlandı.",
                      "en": "{title}: scan completed."},
    "deep_propupd_ok": {"tr": "{title}: karşılaştırma kaydı yenilendi.",
                        "en": "{title}: comparison record refreshed."},
    "deep_propupd_failed": {"tr": "{title}: karşılaştırma kaydı yenilenemedi.",
                            "en": "{title}: the comparison record could not be "
                                  "refreshed."},
    "deep_live_note": {
        "tr": "Canlı oturumda çalışılmaktadır. Sistem her açılışta "
              "sıfırlandığından karşılaştırma kaydı kalıcı değildir; sonuçlar "
              "yalnızca o anki durumu yansıtır.",
        "en": "A live session is in use. Because the system is reset at every "
              "boot, the comparison record is not permanent; results reflect "
              "only the current state.",
    },
}

STATUS_LABEL = {
    OK: {"tr": "SORUNSUZ", "en": "PASS"},
    WARN: {"tr": "UYARI", "en": "WARNING"},
    FAIL: {"tr": "DİKKAT", "en": "ATTENTION"},
    INFO: {"tr": "BİLGİ", "en": "INFO"},
    NEEDROOT: {"tr": "ROOT GEREKLİ", "en": "ROOT REQUIRED"},
}


def _varsayilan_dil():
    """Ilk acilis dili: sistem dili Turkce ise 'tr', baska HERHANGI bir dilse
    'en'. Sabit 'tr' yazmak, kurulumda baska dil secen kullanicinin
    uygulamalari Turkce gormesine yol aciyordu. C/POSIX dil bilgisi
    tasimaz, o yuzden atlanir. Kayitli bir ayar varsa o yine onceliklidir."""
    import os
    for degisken in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        deger = os.environ.get(degisken, "").strip()
        if deger and deger not in ("C", "POSIX"):
            return "tr" if deger.lower().startswith("tr") else "en"
    return "en"


DEFAULTS = {"lang": _varsayilan_dil(), "theme": "dark"}


def load_settings():
    data = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
        if isinstance(stored, dict):
            for key in DEFAULTS:
                if key in stored:
                    data[key] = stored[key]
    except (OSError, ValueError):
        pass
    return data


def save_settings(data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def find_logo():
    for path in LOGO_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def check_meta(check_id):
    for check in CHECKS:
        if check["id"] == check_id:
            return check
    return None


class SweepBar(Gtk.Image):
    """Süresi belirsiz işlemler için tek yönde ilerleyen ince çubuk.

    Soldan sağa akan bir parça gösterir; sağ uca ulaşınca yeniden soldan
    başlar (ileri geri gitmez). Cairo gerektirmez: kareler GdkPixbuf ile
    önceden üretilir ve her adımda sırayla gösterilir."""

    WIDTH = 132
    HEIGHT = 5
    FRAMES = 44
    TAIL = 52
    _onbellek = {}

    @classmethod
    def kareler(cls, renk):
        if renk in cls._onbellek:
            return cls._onbellek[renk]
        r, g, b = (int(renk[i:i + 2], 16) for i in (1, 3, 5))
        w, h, n, kuyruk = cls.WIDTH, cls.HEIGHT, cls.FRAMES, cls.TAIL
        zemin = 0.22
        kareler = []
        for k in range(n):
            bas = k * (w + kuyruk) // n
            veri = bytearray()
            for y in range(h):
                for x in range(w):
                    mesafe = bas - x
                    if 0 <= mesafe <= kuyruk:
                        parca = (1.0 - mesafe / kuyruk) ** 1.6
                        if mesafe < 3:
                            parca *= (mesafe + 1) / 4.0
                    else:
                        parca = 0.0
                    alfa = max(zemin, parca)
                    if (x in (0, w - 1)) and (y in (0, h - 1)):
                        alfa = 0.0
                    veri += bytes((r, g, b, int(alfa * 255)))
            kareler.append(GdkPixbuf.Pixbuf.new_from_bytes(
                GLib.Bytes.new(bytes(veri)), GdkPixbuf.Colorspace.RGB,
                True, 8, w, h, w * 4))
        cls._onbellek[renk] = kareler
        return kareler

    def __init__(self, renk):
        super().__init__()
        self._kareler = self.kareler(renk)
        self.set_from_pixbuf(self._kareler[0])
        self.set_size_request(self.WIDTH, self.HEIGHT)
        self.set_valign(Gtk.Align.CENTER)
        self.set_no_show_all(True)

    def adim(self, sayac):
        self.set_from_pixbuf(self._kareler[sayac % len(self._kareler)])


class HealthWindow(Gtk.Window):

    ACCENT = "#87979B"
    C_OK = "#4c9a6a"
    C_WARN = "#c8952a"
    C_FAIL = "#c2554f"
    C_INFO = "#6d7a7e"

    def __init__(self, settings):
        super().__init__(title=UI["app_title"][settings["lang"]])
        self.settings = settings
        self.lang = settings["lang"]
        self.theme = settings["theme"]
        self.results = []
        self.audited_as_root = False
        self.jobs = set()
        self.job_ui = {}
        self.sweep_id = 0
        self.sweep_step = 0
        self.rescan_pending = False
        self.current_category = "summary"

        self.set_default_size(1000, 700)
        self.set_size_request(880, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        logo = find_logo()
        if logo:
            try:
                self.set_icon_from_file(logo)
            except GLib.Error:
                pass
        self.connect("destroy", self.on_destroy)

        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        root.pack_start(self.build_header(), False, False, 0)
        root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                        False, False, 0)

        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(split, True, True, 0)
        split.pack_start(self.build_sidebar(), False, False, 0)
        split.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL),
                         False, False, 0)

        self.content = Gtk.ScrolledWindow()
        self.content.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        split.pack_start(self.content, True, True, 0)

        root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                        False, False, 0)
        root.pack_start(self.build_statusbar(), False, False, 0)

        self.apply_theme()
        self.retranslate()

    # -- ust bant ----------------------------------------------------------

    def build_header(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.get_style_context().add_class("header")
        box.set_border_width(13)

        # Ust bantta logo yok: pencere kenarindaki simgeyle tekrar oluyordu.
        self.title_label = Gtk.Label(xalign=0.0)
        self.title_label.get_style_context().add_class("wordmark")
        box.pack_start(self.title_label, False, False, 0)

        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append("tr", "Türkçe")
        self.lang_combo.append("en", "English")
        self.lang_combo.set_active_id(self.lang)
        self.lang_combo.connect("changed", self.on_lang_changed)
        box.pack_end(self.lang_combo, False, False, 0)

        self.theme_btn = Gtk.Button()
        self.theme_btn.connect("clicked", self.on_theme_toggled)
        box.pack_end(self.theme_btn, False, False, 0)

        self.export_btn = Gtk.Button()
        self.export_btn.connect("clicked", self.on_export)
        box.pack_end(self.export_btn, False, False, 0)

        self.root_btn = Gtk.Button()
        self.root_btn.connect("clicked", self.on_full_audit)
        box.pack_end(self.root_btn, False, False, 0)

        self.refresh_btn = Gtk.Button()
        self.refresh_btn.get_style_context().add_class("suggested-action")
        self.refresh_btn.connect("clicked", lambda *_: self.start_scan(False))
        box.pack_end(self.refresh_btn, False, False, 0)

        return box

    # -- yan menu ----------------------------------------------------------

    def build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("sidebar")
        box.set_size_request(210, -1)

        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("nav-list")
        self.listbox.connect("row-selected", self.on_category_selected)
        box.pack_start(self.listbox, True, True, 0)

        self.nav_rows = []
        entries = [("summary", UI["summary"])] + list(CATEGORIES)
        for key, label in entries:
            row = Gtk.ListBoxRow()
            row.category_key = key
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            inner.set_border_width(12)
            name = Gtk.Label(xalign=0.0)
            name.get_style_context().add_class("nav-title")
            inner.pack_start(name, False, False, 0)
            tally = Gtk.Label(xalign=0.0)
            tally.get_style_context().add_class("nav-sub")
            inner.pack_start(tally, False, False, 0)
            row.add(inner)
            row.name_label = name
            row.tally_label = tally
            row.label_source = label
            self.listbox.add(row)
            self.nav_rows.append(row)

        return box

    def build_statusbar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_border_width(9)
        self.status = Gtk.Label(xalign=0.0)
        self.status.get_style_context().add_class("status-label")
        box.pack_start(self.status, True, True, 0)
        self.spinner = Gtk.Spinner()
        box.pack_end(self.spinner, False, False, 0)
        return box

    # -- icerik ------------------------------------------------------------

    def clear_content(self):
        child = self.content.get_child()
        if child:
            self.content.remove(child)

    def show_category(self, key):
        self.current_category = key
        self.job_ui = {}
        self.clear_content()

        holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        holder.set_border_width(26)
        self.content.add(holder)

        if key == "summary":
            holder.pack_start(self.build_summary(), False, False, 0)
        elif key == "deep":
            heading = Gtk.Label(label=dict(CATEGORIES)[key][self.lang], xalign=0.0)
            heading.get_style_context().add_class("page-title")
            holder.pack_start(heading, False, False, 0)
            intro = Gtk.Label(label=UI["deep_intro"][self.lang], xalign=0.0)
            intro.set_line_wrap(True)
            intro.set_max_width_chars(88)
            intro.get_style_context().add_class("page-subtitle")
            holder.pack_start(intro, False, False, 0)
            for scan in DEEP_SCANS:
                holder.pack_start(self.build_deep_card(scan), False, False, 0)
        else:
            title = None
            for cat_key, label in CATEGORIES:
                if cat_key == key:
                    title = label[self.lang]
            heading = Gtk.Label(label=title or "", xalign=0.0)
            heading.get_style_context().add_class("page-title")
            holder.pack_start(heading, False, False, 0)

            order = {FAIL: 0, WARN: 1, NEEDROOT: 2, OK: 3, INFO: 4}
            rows = sorted((r for r in self.results if r["category"] == key),
                          key=lambda r: order.get(r["status"], 9))
            if not rows:
                holder.pack_start(Gtk.Label(label=UI["scanning"][self.lang],
                                            xalign=0.0), False, False, 0)
            for result in rows:
                holder.pack_start(self.build_card(result), False, False, 0)

        holder.show_all()

    def build_summary(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        percent, ok, warn, fail = score(self.results)

        hero_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hero_outer.get_style_context().add_class("card")
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        hero.set_margin_top(24); hero.set_margin_bottom(24)
        hero.set_margin_start(24); hero.set_margin_end(24)
        hero_outer.pack_start(hero, True, True, 0)

        big = Gtk.Label(label=f"{percent}%" if self.results else "\u2014")
        big.get_style_context().add_class("score-big")
        if percent >= 85:
            big.get_style_context().add_class("score-ok")
        elif percent >= 60:
            big.get_style_context().add_class("score-warn")
        else:
            big.get_style_context().add_class("score-fail")
        hero.pack_start(big, False, False, 0)

        caption = Gtk.Label(label=UI["score"][self.lang])
        caption.get_style_context().add_class("page-subtitle")
        hero.pack_start(caption, False, False, 0)

        tally = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        tally.set_halign(Gtk.Align.CENTER)
        tally.set_margin_top(12)
        for count, key, css in ((ok, "count_ok", "pill-ok"),
                                (warn, "count_warn", "pill-warn"),
                                (fail, "count_fail", "pill-fail")):
            pill = Gtk.Label(label=f"{count} {UI[key][self.lang]}")
            pill.get_style_context().add_class("pill")
            pill.get_style_context().add_class(css)
            tally.pack_start(pill, False, False, 0)
        hero.pack_start(tally, False, False, 0)
        box.pack_start(hero_outer, False, False, 0)

        if not is_root() and not self.audited_as_root:
            hint = Gtk.Label(label=UI["root_hint"][self.lang], xalign=0.0)
            hint.set_line_wrap(True)
            hint.get_style_context().add_class("note-text")
            hint_body = Gtk.Box()
            hint_body.set_margin_top(15); hint_body.set_margin_bottom(15)
            hint_body.set_margin_start(20); hint_body.set_margin_end(20)
            hint_body.pack_start(hint, True, True, 0)
            wrap = Gtk.Box()
            wrap.get_style_context().add_class("note-box")
            wrap.pack_start(hint_body, True, True, 0)
            box.pack_start(wrap, False, False, 0)

        # Dikkat gerektiren bulgular one cikarilir
        problems = [r for r in self.results if r["status"] in (FAIL, WARN)]
        problems.sort(key=lambda r: 0 if r["status"] == FAIL else 1)
        if self.results and not problems:
            clear = Gtk.Label(label=UI["all_clear"][self.lang], xalign=0.0)
            clear.get_style_context().add_class("page-subtitle")
            wrap = Gtk.Box()
            wrap.get_style_context().add_class("card")
            body = Gtk.Box()
            body.set_margin_top(18); body.set_margin_bottom(18)
            body.set_margin_start(22); body.set_margin_end(22)
            body.pack_start(clear, True, True, 0)
            wrap.pack_start(body, True, True, 0)
            box.pack_start(wrap, False, False, 0)
        for result in problems:
            box.pack_start(self.build_card(result), False, False, 0)

        return box

    def build_card(self, result):
        meta = check_meta(result["id"])
        status = result["status"]
        colour_class = {
            OK: "badge-ok", WARN: "badge-warn", FAIL: "badge-fail",
            INFO: "badge-info", NEEDROOT: "badge-info",
        }[status]

        # Dis kutu yalnizca zemin ve cerceve tasir; ic bosluklar
        # icerideki kutunun kenar bosluklariyla verilir ki ust/alt esit,
        # sol/sag biraz daha ferah olsun.
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.get_style_context().add_class("card")

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        inner.set_margin_top(18)
        inner.set_margin_bottom(18)
        inner.set_margin_start(22)
        inner.set_margin_end(22)
        card.pack_start(inner, True, True, 0)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
        badge = Gtk.Label(label=STATUS_LABEL[status][self.lang])
        badge.get_style_context().add_class("badge")
        badge.get_style_context().add_class(colour_class)
        badge.set_valign(Gtk.Align.CENTER)
        top.pack_start(badge, False, False, 0)

        title = Gtk.Label(label=meta["title"][self.lang] if meta else result["id"],
                          xalign=0.0)
        title.get_style_context().add_class("card-title")
        title.set_line_wrap(True)
        title.set_valign(Gtk.Align.CENTER)
        top.pack_start(title, True, True, 0)

        # Duzeltme dugmesi: yalnizca eylemi olan ve sorunlu denetimlerde
        action = meta.get("action") if meta else None
        if action and status in (WARN, FAIL):
            fix_btn = Gtk.Button(label=action["label"][self.lang])
            fix_btn.get_style_context().add_class("suggested-action")
            fix_btn.set_valign(Gtk.Align.CENTER)
            fix_btn.connect("clicked", self.on_fix, meta)
            top.pack_end(fix_btn, False, False, 0)

            # Islem suresince dugmenin solunda tek yonlu ilerleme cubugu
            bar = self.new_bar()
            top.pack_end(bar, False, False, 0)
            self.job_attach(("fix", meta["id"]), fix_btn, bar)
        # Kapatma anahtari: koruma aciksa ve denetimin "off" eylemi varsa
        off = meta.get("off") if meta else None
        if off and status == OK:
            off_btn = Gtk.Button(label=off["label"][self.lang])
            off_btn.get_style_context().add_class("destructive-action")
            off_btn.set_valign(Gtk.Align.CENTER)
            off_btn.connect("clicked", self.on_fix, meta, off)
            top.pack_end(off_btn, False, False, 0)

            off_bar = self.new_bar()
            top.pack_end(off_bar, False, False, 0)
            self.job_attach(("fix", meta["id"]), off_btn, off_bar)
        inner.pack_start(top, False, False, 0)

        detail = Gtk.Label(label=result["detail"][self.lang], xalign=0.0)
        detail.set_line_wrap(True)
        detail.set_max_width_chars(88)
        inner.pack_start(detail, False, False, 0)

        if meta and status in (WARN, FAIL, NEEDROOT):
            why = Gtk.Label(label=f"{UI['why'][self.lang]}: {meta['why'][self.lang]}",
                            xalign=0.0)
            why.set_line_wrap(True)
            why.set_max_width_chars(88)
            why.get_style_context().add_class("why-text")
            inner.pack_start(why, False, False, 0)

        if meta and meta.get("fix") and status in (WARN, FAIL):
            caption = Gtk.Label(label=UI["suggested"][self.lang], xalign=0.0)
            caption.get_style_context().add_class("caption-text")
            inner.pack_start(caption, False, False, 0)

            code = Gtk.Label(label=meta["fix"], xalign=0.0)
            code.set_selectable(True)
            code.set_line_wrap(True)
            code.get_style_context().add_class("code-text")
            code_inner = Gtk.Box()
            code_inner.set_margin_top(9)
            code_inner.set_margin_bottom(9)
            code_inner.set_margin_start(13)
            code_inner.set_margin_end(13)
            code_inner.pack_start(code, True, True, 0)
            code_box = Gtk.Box()
            code_box.get_style_context().add_class("code-box")
            code_box.pack_start(code_inner, True, True, 0)
            inner.pack_start(code_box, False, False, 0)

        return card

    # -- duzeltme calistirma -----------------------------------------------

    def on_fix(self, button, meta, action=None):
        action = action or meta["action"]
        key = ("fix", meta["id"])
        if key in self.jobs:
            return
        if action.get("confirm"):
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=meta["title"][self.lang])
            body = UI["confirm_body"][self.lang].format(
                action=action["label"][self.lang])
            if action.get("warning"):
                body += "\n\n" + action["warning"][self.lang]
            dialog.format_secondary_text(body)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return

        self.job_begin(key)
        self.status.set_text(UI["applying"][self.lang].format(
            action=action["label"][self.lang]))

        def worker():
            code, out = run(["pkexec", "/bin/sh", "-c", action["cmd"]],
                            timeout=900)
            GLib.idle_add(self.fix_done, code, out, meta)

        threading.Thread(target=worker, daemon=True).start()

    # -- ayrintili taramalar -----------------------------------------------

    def deep_state(self):
        if not hasattr(self, "deep"):
            self.deep = {}
        return self.deep

    def build_deep_card(self, scan):
        key = ("deep", scan["id"])
        state = self.deep_state().get(scan["id"])
        installed = have(scan["binary"])
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.get_style_context().add_class("card")

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        inner.set_margin_top(18)
        inner.set_margin_bottom(18)
        inner.set_margin_start(22)
        inner.set_margin_end(22)
        card.pack_start(inner, True, True, 0)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
        if key in self.jobs:
            badge_text = UI["deep_badge_run"][self.lang]
            badge_class = "badge-info"
        elif state and "status" in state:
            badge_text = STATUS_LABEL[state["status"]][self.lang]
            badge_class = {OK: "badge-ok", WARN: "badge-warn", FAIL: "badge-fail",
                           INFO: "badge-info"}.get(state["status"], "badge-info")
        else:
            badge_text = UI["deep_badge_none"][self.lang]
            badge_class = "badge-info"
        badge = Gtk.Label(label=badge_text)
        badge.get_style_context().add_class("badge")
        badge.get_style_context().add_class(badge_class)
        badge.set_valign(Gtk.Align.CENTER)
        top.pack_start(badge, False, False, 0)

        title = Gtk.Label(label=scan["title"][self.lang], xalign=0.0)
        title.get_style_context().add_class("card-title")
        title.set_line_wrap(True)
        title.set_valign(Gtk.Align.CENTER)
        top.pack_start(title, True, True, 0)

        if installed:
            scan_btn = Gtk.Button(
                label=UI["deep_rescan" if state and "status" in state
                         else "deep_scan"][self.lang])
            scan_btn.get_style_context().add_class("suggested-action")
            scan_btn.set_valign(Gtk.Align.CENTER)
            scan_btn.connect("clicked", self.start_deep, scan, "scan")
            top.pack_end(scan_btn, False, False, 0)

            if scan.get("propupd_args"):
                prop_btn = Gtk.Button(label=UI["deep_propupd"][self.lang])
                prop_btn.set_valign(Gtk.Align.CENTER)
                prop_btn.connect("clicked", self.start_deep, scan, "propupd")
                top.pack_end(prop_btn, False, False, 0)
                self.job_attach(key, prop_btn)

            bar = self.new_bar()
            top.pack_end(bar, False, False, 0)
            self.job_attach(key, scan_btn, bar)
        inner.pack_start(top, False, False, 0)

        if not installed:
            detail_text = UI["deep_missing"][self.lang]
        elif key in self.jobs:
            detail_text = UI["deep_working"][self.lang]
        elif state and "detail" in state:
            detail_text = state["detail"][self.lang]
        else:
            detail_text = UI["deep_none"][self.lang]
        detail = Gtk.Label(label=detail_text, xalign=0.0)
        detail.set_line_wrap(True)
        detail.set_max_width_chars(88)
        inner.pack_start(detail, False, False, 0)

        why = Gtk.Label(label=f"{UI['why'][self.lang]}: {scan['why'][self.lang]}",
                        xalign=0.0)
        why.set_line_wrap(True)
        why.set_max_width_chars(88)
        why.get_style_context().add_class("why-text")
        inner.pack_start(why, False, False, 0)

        if scan.get("live_note") and is_live():
            note = Gtk.Label(label=UI["deep_live_note"][self.lang], xalign=0.0)
            note.set_line_wrap(True)
            note.set_max_width_chars(88)
            note.get_style_context().add_class("caption-text")
            inner.pack_start(note, False, False, 0)

        for item in (state or {}).get("extra", []):
            line = Gtk.Label(label=item["text"], xalign=0.0)
            line.set_selectable(True)
            line.set_line_wrap(True)
            line.set_max_width_chars(88)
            line.get_style_context().add_class("code-text")
            inner.pack_start(line, False, False, 0)
            if item.get("explain"):
                expl = Gtk.Label(label=item["explain"][self.lang], xalign=0.0)
                expl.set_line_wrap(True)
                expl.set_max_width_chars(88)
                expl.get_style_context().add_class("why-text")
                inner.pack_start(expl, False, False, 0)
        return card

    def start_deep(self, button, scan, mode):
        key = ("deep", scan["id"])
        if key in self.jobs:
            return
        if mode == "propupd":
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=scan["title"][self.lang])
            dialog.format_secondary_text(scan["propupd_warning"][self.lang])
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return
            args = scan["propupd_args"]
        else:
            args = scan["args"]

        self.job_begin(key)
        if self.current_category == "deep":
            self.show_category("deep")
        self.status.set_text(UI["deep_running"][self.lang].format(
            title=scan["title"][self.lang]))

        def worker():
            code, out = run(deep_command(scan["binary"], args),
                            timeout=scan["timeout"])
            GLib.idle_add(self.deep_done, scan, mode, code, out)

        threading.Thread(target=worker, daemon=True).start()

    def deep_done(self, scan, mode, code, out):
        self.job_end(("deep", scan["id"]))
        title = scan["title"][self.lang]
        if code in (126, 127) and not out:
            self.status.set_text(UI["fix_cancelled"][self.lang])
        elif mode == "propupd":
            key = "deep_propupd_ok" if code == 0 else "deep_propupd_failed"
            self.status.set_text(UI[key][self.lang].format(title=title))
            if code != 0:
                self.show_output(title, out or "")
        else:
            result = scan["parse"](code, out)
            result["stamp"] = time.strftime("%H:%M")
            self.deep_state()[scan["id"]] = result
            self.status.set_text(UI["deep_finished"][self.lang].format(title=title))
        if self.current_category == "deep":
            self.show_category("deep")
        return False

    # -- eşzamanlı işler ---------------------------------------------------
    # Her iş bir anahtarla izlenir: ("scan",), ("fix", denetim_kimligi),
    # ("deep", tarama_kimligi). Farklı işler aynı anda çalışabilir; aynı
    # anahtara bağlı düğmeler iş sürerken devre dışı kalır.

    def job_attach(self, key, button, bar=None):
        self.job_ui.setdefault(key, []).append((button, bar))
        running = key in self.jobs
        button.set_sensitive(not running)
        if bar is not None and running:
            bar.show()

    def new_bar(self):
        return SweepBar(self.ACCENT)

    def apply_jobs(self):
        scanning = ("scan",) in self.jobs
        self.refresh_btn.set_sensitive(not scanning)
        self.root_btn.set_sensitive(not scanning)
        for key, items in self.job_ui.items():
            running = key in self.jobs
            for button, bar in items:
                try:
                    button.set_sensitive(not running)
                    if bar is not None:
                        bar.show() if running else bar.hide()
                except Exception:
                    pass

    def job_begin(self, key):
        self.jobs.add(key)
        self.apply_jobs()
        self.spinner.start()
        if not self.sweep_id:
            self.sweep_step = 0
            self.sweep_id = GLib.timeout_add(45, self._sweep)

    def job_end(self, key):
        self.jobs.discard(key)
        self.apply_jobs()
        if not self.jobs:
            self.spinner.stop()
            self.sweep_stop()

    def _sweep(self):
        if not self.jobs:
            self.sweep_id = 0
            return False
        self.sweep_step += 1
        for key in self.jobs:
            for _button, bar in self.job_ui.get(key, []):
                if bar is not None:
                    bar.adim(self.sweep_step)
        return True

    def sweep_stop(self):
        if self.sweep_id:
            GLib.source_remove(self.sweep_id)
            self.sweep_id = 0

    def flush_rescan(self):
        if self.rescan_pending:
            self.rescan_pending = False
            self.start_scan(False)

    def fix_done(self, code, out, meta):
        self.job_end(("fix", meta["id"]))
        if code == 0:
            self.status.set_text(UI["fix_ok"][self.lang].format(
                title=meta["title"][self.lang]))
            # Yeniden tarama normal yetkiyle yapilir; root gerektiren
            # denetimlerin onceki sonuclari korunur, boylece parola
            # ikinci kez sorulmaz.
            self.start_scan(False)
        elif code in (126, 127):
            self.status.set_text(UI["fix_cancelled"][self.lang])
        else:
            self.status.set_text(UI["fix_failed"][self.lang].format(
                title=meta["title"][self.lang]))
            self.show_output(meta["title"][self.lang], out or "")
        return False

    def show_output(self, title, text):
        dialog = Gtk.Dialog(title=title, transient_for=self, modal=True)
        dialog.add_button("Kapat" if self.lang == "tr" else "Close",
                          Gtk.ResponseType.CLOSE)
        dialog.set_default_size(680, 380)
        view = Gtk.TextView()
        view.set_editable(False)
        view.set_monospace(True)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.get_buffer().set_text(text[-8000:] if text else "")
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(view)
        scroller.set_margin_top(10)
        scroller.set_margin_bottom(10)
        scroller.set_margin_start(10)
        scroller.set_margin_end(10)
        dialog.get_content_area().pack_start(scroller, True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    # -- tarama ------------------------------------------------------------

    def start_scan(self, as_root):
        if ("scan",) in self.jobs:
            # Devam eden tarama varken istenen yeniden tarama, bitince yapilir
            if not as_root:
                self.rescan_pending = True
            return
        self.job_begin(("scan",))
        self.status.set_text(UI["scanning"][self.lang])

        def worker():
            if as_root:
                script = os.path.abspath(__file__)
                code, out = run(["pkexec", sys.executable, script,
                                 "--audit-json"], timeout=180)
                try:
                    data = json.loads(out) if code == 0 else None
                except ValueError:
                    data = None
                GLib.idle_add(self.scan_done, data, True)
            else:
                GLib.idle_add(self.scan_done, run_all_checks(), False)

        threading.Thread(target=worker, daemon=True).start()

    def scan_done(self, data, was_root):
        self.job_end(("scan",))

        if data is None:
            self.status.set_text(UI["audit_failed"][self.lang])
            self.flush_rescan()
            return False

        if was_root:
            self.results = data
            self.audited_as_root = True
        else:
            self.results = self.merge_results(data)

        stamp = time.strftime("%H:%M")
        suffix = f" \u00b7 {UI['as_root'][self.lang]}" if self.audited_as_root else ""
        self.status.set_text(f"{UI['ready'][self.lang]} \u00b7 {stamp}{suffix}")

        self.update_tallies()
        self.show_category(self.current_category)
        self.flush_rescan()
        return False

    def merge_results(self, fresh):
        """Normal yetkili taramada NEEDROOT donen denetimler icin, daha once
        root ile elde edilmis sonuc varsa onu korur."""
        if not self.audited_as_root or not self.results:
            return fresh
        previous = {r["id"]: r for r in self.results}
        merged = []
        for result in fresh:
            old = previous.get(result["id"])
            if result["status"] == NEEDROOT and old and old["status"] != NEEDROOT:
                merged.append(old)
            else:
                merged.append(result)
        return merged

    def update_tallies(self):
        for row in self.nav_rows:
            key = row.category_key
            if key == "summary":
                percent, _, _, fail = score(self.results)
                row.tally_label.set_text(
                    f"{percent}%" if self.results else "\u2014")
                continue
            rows = [r for r in self.results if r["category"] == key]
            bad = sum(1 for r in rows if r["status"] in (WARN, FAIL))
            if not rows:
                row.tally_label.set_text("\u2014")
            elif bad:
                row.tally_label.set_text(
                    f"{bad} {UI['count_fail'][self.lang]}")
            else:
                row.tally_label.set_text(
                    f"{len(rows)} {UI['count_ok'][self.lang]}")

    # -- rapor -------------------------------------------------------------

    def build_report(self):
        percent, ok, warn, fail = score(self.results)
        lines = [
            "CarotOS " + UI["app_title"][self.lang],
            "=" * 58,
            time.strftime("%Y-%m-%d %H:%M:%S"),
            f"{UI['score'][self.lang]}: {percent}%   "
            f"({ok} {UI['count_ok'][self.lang]}, "
            f"{warn} {UI['count_warn'][self.lang]}, "
            f"{fail} {UI['count_fail'][self.lang]})",
            "",
        ]
        for cat_key, cat_label in CATEGORIES:
            rows = [r for r in self.results if r["category"] == cat_key]
            if not rows:
                continue
            lines.append(f"[{cat_label[self.lang]}]")
            for result in rows:
                meta = check_meta(result["id"])
                title = meta["title"][self.lang] if meta else result["id"]
                tag = STATUS_LABEL[result["status"]][self.lang]
                lines.append(f"  {tag:<14} {title}")
                lines.append(f"                 {result['detail'][self.lang]}")
            lines.append("")
        for scan in DEEP_SCANS:
            state = getattr(self, "deep", {}).get(scan["id"])
            if not state or "status" not in state:
                continue
            lines.append(f"[{scan['title'][self.lang]}]")
            tag = STATUS_LABEL[state["status"]][self.lang]
            lines.append(f"  {tag:<14} {state['detail'][self.lang]}")
            for item in state.get("extra", [])[:20]:
                lines.append(f"                 {item['text']}")
            lines.append("")
        return "\n".join(lines)

    def on_export(self, _button):
        path = os.path.join(GLib.get_home_dir(),
                            time.strftime("carotos-health-%Y%m%d-%H%M.txt"))
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.build_report())
            self.status.set_text(UI["saved"][self.lang].format(path=path))
        except OSError:
            self.status.set_text(UI["save_failed"][self.lang])

    # -- olaylar -----------------------------------------------------------

    def on_category_selected(self, _listbox, row):
        if row is not None:
            self.show_category(row.category_key)

    def on_full_audit(self, _button):
        self.start_scan(True)

    def on_lang_changed(self, combo):
        chosen = combo.get_active_id()
        if chosen and chosen != self.lang:
            self.lang = chosen
            self.settings["lang"] = chosen
            save_settings(self.settings)
            self.retranslate()

    def on_theme_toggled(self, _button):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings["theme"] = self.theme
        save_settings(self.settings)
        self.apply_theme()
        self.retranslate()

    def retranslate(self):
        self.set_title(UI["app_title"][self.lang])
        self.title_label.set_text(UI["app_title"][self.lang])
        self.refresh_btn.set_label(UI["refresh"][self.lang])
        self.root_btn.set_label(UI["full_audit"][self.lang])
        self.export_btn.set_label(UI["export"][self.lang])
        self.theme_btn.set_label(
            UI["theme_light"][self.lang] if self.theme == "dark"
            else UI["theme_dark"][self.lang])
        for row in self.nav_rows:
            row.name_label.set_text(row.label_source[self.lang])
        self.update_tallies()
        self.show_category(self.current_category)

    def on_destroy(self, _widget):
        self.sweep_stop()
        Gtk.main_quit()

    # -- tema --------------------------------------------------------------

    def apply_theme(self):
        if self.theme == "dark":
            bg = "#1f2325"; side = "#2b2f31"; header = "#2b2f31"; fg = "#e6e6e6"
            sub = "#9aa4a8"; field = "#2b2f31"
            card = "#282d2f"; card_border = "#363c3e"; note_bg = "#2c3134"
            btn_bg = "#343a3c"; btn_hover = "#3f4649"; border = "#454b4e"
            code_fg = "#8fd6c4"
        else:
            bg = "#f2f4f5"; side = "#e4e7e9"; header = "#e4e7e9"; fg = "#1f2325"
            sub = "#5c666a"; field = "#ffffff"
            card = "#ffffff"; card_border = "#dde2e4"; note_bg = "#eef1f2"
            btn_bg = "#ffffff"; btn_hover = "#eef0f1"; border = "#c3c8ca"
            code_fg = "#1f5f52"

        Gtk.Settings.get_default().set_property(
            "gtk-application-prefer-dark-theme", self.theme == "dark")

        css = f"""
        window {{ background-color: {bg}; color: {fg}; }}
        label {{ color: {fg}; }}

        .header {{ background-color: {header}; }}
        .wordmark {{ font-size: 122%; font-weight: bold; }}
        .sidebar {{ background-color: {side}; }}
        .nav-title {{ font-weight: bold; }}
        .nav-sub {{ color: {sub}; font-size: 88%; }}
        .nav-list row:selected {{ background-color: {self.ACCENT}; }}
        .nav-list row:selected label {{ color: #ffffff; }}
        .status-label {{ color: {sub}; font-size: 91%; }}

        .page-title {{ font-size: 152%; font-weight: bold; }}
        .page-subtitle {{ color: {sub}; font-size: 104%; }}
        .card {{
            background-color: {card};
            border: 1px solid {card_border};
            border-radius: 8px;
        }}
        .card-title {{ font-weight: bold; font-size: 106%; }}
        .why-text {{ color: {sub}; font-size: 92%; }}
        .caption-text {{ color: {sub}; font-size: 84%; }}
        progressbar trough {{ background-color: {btn_bg};
            border: 1px solid {border}; border-radius: 999px;
            min-height: 7px; }}
        progressbar progress {{ background-color: {self.ACCENT};
            border-radius: 999px; min-height: 7px; }}

        .badge {{
            color: #ffffff; font-size: 78%; font-weight: bold;
            border-radius: 4px; padding: 3px 8px;
        }}
        .badge-ok {{ background-color: {self.C_OK}; }}
        .badge-warn {{ background-color: {self.C_WARN}; }}
        .badge-fail {{ background-color: {self.C_FAIL}; }}
        .badge-info {{ background-color: {self.C_INFO}; }}

        .score-big {{ font-size: 320%; font-weight: bold; }}
        .score-ok {{ color: {self.C_OK}; }}
        .score-warn {{ color: {self.C_WARN}; }}
        .score-fail {{ color: {self.C_FAIL}; }}
        .pill {{
            border-radius: 999px; padding: 4px 14px;
            font-size: 90%; color: #ffffff;
        }}
        .pill-ok {{ background-color: {self.C_OK}; }}
        .pill-warn {{ background-color: {self.C_WARN}; }}
        .pill-fail {{ background-color: {self.C_FAIL}; }}

        .note-box {{
            background-color: {note_bg};
            border: 1px solid {card_border};
            border-left: 3px solid {self.ACCENT};
            border-radius: 8px;
        }}
        .note-text {{ color: {sub}; font-size: 94%; }}
        .code-box {{
            background-color: {field};
            border: 1px solid {border};
            border-radius: 6px;
        }}
        .code-text {{ font-family: monospace; color: {code_fg}; }}

        button {{
            background-image: none; background-color: {btn_bg}; color: {fg};
            border: 1px solid {border}; border-radius: 6px; padding: 4px 14px;
        }}
        button label {{ color: {fg}; }}
        button:hover {{ background-color: {btn_hover}; }}
        button:disabled {{ color: {sub}; }}
        button:disabled label {{ color: {sub}; }}
        button.suggested-action {{
            background-color: {self.ACCENT}; border-color: {self.ACCENT};
            color: #ffffff;
        }}
        button.suggested-action label {{ color: #ffffff; }}
        button.destructive-action {{
            background-color: {self.C_FAIL}; border-color: {self.C_FAIL};
            color: #ffffff;
        }}
        button.destructive-action label {{ color: #ffffff; }}

        combobox button {{ background-color: {field}; color: {fg}; }}
        combobox button label {{ color: {fg}; }}
        menu, .menu, popover, popover.background {{
            background-color: {field}; color: {fg};
        }}
        menuitem label, popover label {{ color: {fg}; }}
        menuitem:hover {{ background-color: {self.ACCENT}; }}
        menuitem:hover label {{ color: #ffffff; }}
        separator {{ background-color: {border}; }}
        """
        self.css_provider.load_from_data(css.encode())


def main():
    settings = load_settings()
    window = HealthWindow(settings)
    window.show_all()
    window.listbox.select_row(window.nav_rows[0])
    window.start_scan(False)
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
