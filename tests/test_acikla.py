#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Komut Açıklayıcı: ayrıştırma, uyarı kuralları, veri bütünlüğü, CLI, Alt+E bağlantısı (GTK'siz).

Calistirma:  python3 tests/test_acikla.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
ACIKLA = os.path.join(INC, "opt", "carotos", "acikla")
sys.path.insert(0, os.path.join(INC, "opt", "carotos", "ortak"))
sys.path.insert(0, ACIKLA)

import acikla_motor as M  # noqa: E402
import dil  # noqa: E402
import veri_guvenlik  # noqa: E402
import veri_saldiri  # noqa: E402
import veri_tehlike  # noqa: E402
import veri_temel  # noqa: E402


def program_adlari(sonuc):
    return [p["komut"] for p in sonuc["parcalar"]]


def tehlike_idleri(satir):
    return {t["id"] for t in M.ayristir(satir)["tehlikeler"]}


class AyristirmaTesti(unittest.TestCase):
    def test_basit_komut_ve_bayraklar(self):
        s = M.ayristir("ls -lah /etc")
        p = s["parcalar"][0]
        self.assertEqual(p["komut"], "ls")
        self.assertEqual([b["ad"] for b in p["bayraklar"]], ["-l", "-a", "-h"])   # -lah kümesi çözüldü
        self.assertEqual(p["konumsal"], ["/etc"])
        self.assertEqual(p["bilinmeyen"], [])

    def test_sudo_oneki_ayiklanir_ve_yetki(self):
        s = M.ayristir("sudo -u root ufw status verbose")
        p = s["parcalar"][0]
        self.assertEqual(p["komut"], "ufw")
        self.assertTrue(p["sudo"])
        self.assertEqual(p["altkomut"][0], "status")

    def test_ortam_atamasi_ve_env(self):
        p = M.ayristir("LANG=C env TZ=UTC nice -n 5 grep -i abc dosya")["parcalar"][0]
        self.assertEqual(p["komut"], "grep")
        self.assertEqual(p["atamalar"], ["LANG=C"])

    def test_boru_ve_mantiksal_baglaclar(self):
        s = M.ayristir("cat a.txt | grep x && echo ok; ls || pwd")
        self.assertEqual(program_adlari(s), ["cat", "grep", "echo", "ls", "pwd"])
        self.assertEqual([p["bagla"] for p in s["parcalar"]], [None, "|", "&&", ";", "||"])

    def test_tirnak_icindeki_ozel_karakterler_bolmez(self):
        s = M.ayristir("grep 'a|b && c' dosya")
        self.assertEqual(len(s["parcalar"]), 1)
        self.assertEqual(s["parcalar"][0]["konumsal"], ["a|b && c", "dosya"])

    def test_yonlendirme(self):
        p = M.ayristir("echo hi > a.txt")["parcalar"][0]
        self.assertEqual(p["yonlendirme"], [(">", "a.txt")])
        self.assertEqual(p["konumsal"], ["hi"])

    def test_deger_alan_bayrak(self):
        p = M.ayristir("head -n 5 dosya")["parcalar"][0]
        self.assertEqual(p["bayraklar"][0]["deger"], "5")
        self.assertEqual(p["konumsal"], ["dosya"])

    def test_uzun_bayrak_esittir_degeri(self):
        p = M.ayristir("journalctl --since=today -u ssh")["parcalar"][0]
        self.assertEqual([b["ad"] for b in p["bayraklar"]], ["--since", "-u"])
        self.assertEqual(p["bayraklar"][0]["deger"], "today")

    def test_tar_eski_bicim(self):
        p = M.ayristir("tar xzf a.tar.gz")["parcalar"][0]
        self.assertEqual([b["ad"] for b in p["bayraklar"]], ["-x", "-z", "-f"])
        self.assertEqual(p["bayraklar"][-1]["deger"], "a.tar.gz")

    def test_sayisal_sinyal_bayragi(self):
        p = M.ayristir("kill -9 1234")["parcalar"][0]
        self.assertEqual(p["bayraklar"][0]["ad"], "-9")
        self.assertEqual(p["konumsal"], ["1234"])

    def test_dd_parametreleri(self):
        p = M.ayristir("dd if=a.iso of=/dev/null bs=4M")["parcalar"][0]
        self.assertEqual([x[0] for x in p["parametreler"]], ["if", "of", "bs"])
        self.assertEqual(p["konumsal"], [])

    def test_bilinmeyen_komut_durustce(self):
        p = M.ayristir("foobar --x")["parcalar"][0]
        self.assertFalse(p["bilinen"])
        metin = M.acikla("foobar --x", "en")
        self.assertIn("I don't know", metin)

    def test_bilinmeyen_bayrak_listelenir(self):
        p = M.ayristir("ls --yok-boyle")["parcalar"][0]
        self.assertEqual(p["bilinmeyen"], ["--yok-boyle"])

    def test_bos_ve_tamamlanmamis_satir(self):
        self.assertEqual(M.ayristir("   ")["hata"], "bos")
        self.assertEqual(M.ayristir("echo 'acik")["hata"], "tamamlanmamis")
        self.assertIn("incomplete", M.acikla("echo 'acik", "en"))

    def test_komut_yerine_koyma_ve_degisken_notu(self):
        s = M.ayristir("echo $(whoami) $HOME")
        self.assertTrue(s["komut_yerine"])
        self.assertTrue(s["degisken"])
        self.assertIn("don't resolve", M.metin_olustur(s, "en"))

    def test_gurultu_ve_root(self):
        self.assertEqual(M.ayristir("ls")["parcalar"][0]["root"], "yok")
        self.assertEqual(M.ayristir("chown a b")["parcalar"][0]["root"], "gerekli")
        self.assertEqual(M.ayristir("apt install x")["parcalar"][0]["root"], "gerekebilir")
        self.assertEqual(M.ayristir("ping -c1 x")["parcalar"][0]["gurultu"], "orta")


class TehlikeKurallariTesti(unittest.TestCase):
    def test_tehlikeli_olanlar(self):
        vaka = {
            "rm -rf /": "rm_tehlikeli", "sudo rm -rf ~": "rm_tehlikeli", "rm -r /etc": "rm_tehlikeli",
            "rm --no-preserve-root -rf x": "rm_tehlikeli", "dd if=a of=/dev/sda": "dd_diske",
            "mkfs.ext4 /dev/sdb1": "mkfs", "chmod -R 777 /var": "chmod_genis", "chown -R a:a /etc": "chown_kok",
            "curl -s http://x/i.sh | sh": "indir_calistir", "wget -qO- http://x | sudo bash": "indir_calistir",
            "sh -c \"$(curl -fsSL http://x)\"": "komut_indir_calistir", "sudo ufw disable": "guvenlik_kapat",
            "systemctl stop fail2ban": "guvenlik_kapat",
        }
        for satir, beklenen in vaka.items():
            with self.subTest(satir=satir):
                self.assertIn(beklenen, tehlike_idleri(satir))

    def test_zararsiz_olanlar_uyari_vermez(self):
        for satir in ("rm dosya.txt", "rm -rf build/", "rm -r ./gecici", "dd if=a.iso of=/tmp/b.img", "chmod 644 a", "chmod -R 755 ./site",
                      "curl -O http://x/a.tar.gz", "curl -s http://x | grep abc", "ufw status", "ls -l /etc", "chown me file"):
            with self.subTest(satir=satir):
                self.assertEqual(tehlike_idleri(satir), set(), satir)

    def test_tehlike_metinde_gorunur(self):
        self.assertIn("Dangerous pattern", M.acikla("rm -rf /", "en"))
        self.assertIn("Tehlikeli kalıp", M.acikla("rm -rf /", "tr"))


class CalistirmazTesti(unittest.TestCase):
    def test_kaynakta_komut_calistirma_yok(self):
        # Açıklayıcı hiçbir zaman komut çalıştırmamalı: süreç/exec/eval çağrıları kaynakta bulunmamalı.
        for ad in ("acikla_motor.py", "veri_guvenlik.py", "veri_saldiri.py", "veri_temel.py", "veri_tehlike.py"):
            kod = open(os.path.join(ACIKLA, ad), encoding="utf-8").read()
            kod = re.sub(r'"""[\s\S]*?"""', "", kod)                       # açıklama metinleri sayılmaz
            for yasak in (r"\bsubprocess\b", r"\bos\.system\b", r"\bos\.popen\b", r"\bos\.exec", r"\bexec\(", r"\beval\(",
                          r"\bPopen\b", r"\bos\.spawn", r"\b__import__\b", r"\bpty\b"):
                with self.subTest(dosya=ad, yasak=yasak):
                    self.assertIsNone(re.search(yasak, kod), f"{ad}: {yasak}")

    def test_tehlikeli_satir_calistirilmaz(self):
        iz = os.path.join(tempfile.mkdtemp(prefix="acikla-"), "izi")
        M.acikla(f"touch {iz}; echo x > {iz}", "en")
        self.assertFalse(os.path.exists(iz), "açıklama komutu çalıştırdı!")


class VeriButunluguTesti(unittest.TestCase):
    def kontrol_T(self, t, yer):
        self.assertEqual(set(t), {"tr", "en"}, yer)
        self.assertTrue(t["tr"].strip() and t["en"].strip(), yer)

    def test_butun_komutlar(self):
        tum = {**veri_saldiri.KOMUTLAR, **veri_guvenlik.KOMUTLAR, **veri_temel.KOMUTLAR}
        self.assertEqual(len(tum), len(veri_saldiri.KOMUTLAR) + len(veri_guvenlik.KOMUTLAR) + len(veri_temel.KOMUTLAR),
                         "ayni komut iki veri dosyasinda")
        self.assertGreaterEqual(len(tum), 40)
        for ad, k in tum.items():
            self.kontrol_T(k["ozet"], ad)
            self.assertIn(k["gurultu"], M.SEVIYE_SIRASI, ad)
            self.assertIn(k["yetki"], ("yok", "kismen", "root"), ad)
            for bayrak, g in k.get("bayraklar", {}).items():
                self.assertTrue(bayrak.startswith("-"), (ad, bayrak))
                self.kontrol_T(g["a"], (ad, bayrak))
            for desen, g in k.get("desenler", []):
                re.compile(desen)
                self.kontrol_T(g["a"], (ad, desen))
            for alt, t in k.get("altkomut", {}).items():
                self.kontrol_T(t, (ad, alt))
            for prm, t in k.get("parametreler", {}).items():
                self.kontrol_T(t, (ad, prm))
            for alan in ("uyari", "nasil", "savunma"):
                if alan in k:
                    self.kontrol_T(k[alan], (ad, alan))

    def test_tehlike_kurallari(self):
        for k in veri_tehlike.SATIR_KURALLARI + veri_tehlike.PARCA_KURALLARI:
            self.kontrol_T(k["neden"], k["id"])
            self.assertIn(k["siddet"], ("orta", "yuksek"), k["id"])
        for k in veri_tehlike.SATIR_KURALLARI:
            re.compile(k["desen"])

    def test_kurallar_benzersiz(self):
        idler = [k["id"] for k in veri_tehlike.SATIR_KURALLARI + veri_tehlike.PARCA_KURALLARI]
        self.assertEqual(len(idler), len(set(idler)))

    def test_etiketler_iki_dilli(self):
        for ad, t in M.ETIKETLER.items():
            self.kontrol_T(t, ad)

    def test_takma_adlar_gecerli_komuta_gider(self):
        for takma, hedef in M.TAKMA_ADLARI.items() if hasattr(M, "TAKMA_ADLARI") else M.TAKMA_ADLAR.items():
            self.assertIn(hedef, M.KOMUTLAR, takma)


class DilTesti(unittest.TestCase):
    def test_her_dilde_calisir_ve_bos_olmaz(self):
        for kod in dil.KODLAR:
            with self.subTest(kod=kod):
                metin = M.acikla("sudo ufw status && rm -rf /", kod)
                self.assertTrue(metin.strip())
                self.assertNotIn("{", metin.split("\n", 1)[0])

    def test_ceviri_dosyasi_kullanilir(self):
        eski = dil.DIZIN
        gecici = tempfile.mkdtemp(prefix="acikla-dil-")
        try:
            import json
            with open(os.path.join(gecici, "de.json"), "w", encoding="utf-8") as f:
                json.dump({"_meta": {"etkin": True}, "metinler": {"Lists the files in a folder.": "Listet die Dateien eines Ordners auf."}}, f)
            dil.DIZIN = gecici
            dil.onbellegi_temizle()
            self.assertIn("Listet die Dateien", M.acikla("ls", "de"))
            self.assertIn("Lists the files", M.acikla("ls", "fr"))      # fr dosyası yok: İngilizce
        finally:
            dil.DIZIN = eski
            dil.onbellegi_temizle()


class CliTesti(unittest.TestCase):
    CLI = os.path.join(INC, "usr", "local", "bin", "carotos-acikla")

    def calistir(self, *argv, girdi=None):
        s = subprocess.run([sys.executable, self.CLI, *argv], input=girdi, capture_output=True, text=True,
                           encoding="utf-8", timeout=60,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(s.returncode, 0, s.stderr)
        return s.stdout

    def test_argumanlardan(self):
        self.assertIn("Lists the files in a folder.", self.calistir("--dil", "en", "ls", "-l"))

    def test_satir_bayragi(self):
        self.assertIn("Firewall management", self.calistir("--dil", "en", "--satir", "sudo ufw status"))

    def test_stdin(self):
        self.assertIn("Prints the given text", self.calistir("--dil", "en", girdi="echo selam\n"))

    def test_yardim(self):
        self.assertIn("ÇALIŞTIRMADAN", self.calistir("--help"))


class BashBaglantisiTesti(unittest.TestCase):
    def test_dosya_ve_hook(self):
        bash = open(os.path.join(INC, "usr", "share", "carotos", "acikla.bash"), encoding="utf-8").read()
        self.assertIn('bind -x \'"\\ee": carotos_acikla_satir\'', bash)      # Alt+E
        self.assertIn("READLINE_LINE", bash)
        hook = open(os.path.join(KOK, "config", "hooks", "live", "9999-carotos-setup.hook.chroot"), encoding="utf-8").read()
        self.assertIn("chmod 755 /usr/local/bin/carotos-acikla", hook)
        self.assertIn("/usr/share/carotos/acikla.bash", hook)

    @unittest.skipUnless(shutil.which("bash") and os.name == "posix", "bash gerekir")
    def test_interaktif_bash_dosyayi_okur_ve_baglar(self):
        kok = tempfile.mkdtemp(prefix="acikla-bash-")
        bin_ = os.path.join(kok, "bin")
        os.makedirs(bin_)
        with open(os.path.join(bin_, "carotos-acikla"), "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(os.path.join(bin_, "carotos-acikla"), 0o755)
        dosya = os.path.join(INC, "usr", "share", "carotos", "acikla.bash")
        s = subprocess.run(["bash", "--norc", "-i", "-c", f"source '{dosya}'; bind -X | grep -c carotos_acikla_satir"],
                           capture_output=True, text=True, timeout=30,
                           env=dict(os.environ, PATH=bin_ + ":" + os.environ["PATH"]))
        self.assertEqual(s.stdout.strip().splitlines()[-1], "1", s.stdout + s.stderr)


class SaldiriAraclariTesti(unittest.TestCase):
    """Güvenlik Paneli'ndeki eğitim araçları ayrıntılı açıklanır (Panel'in 'Açıkla' düğmesi)."""

    PANEL = os.path.join(INC, "opt", "carotos", "security-panel", "carotos-security-panel.py")

    def panel_araclari(self):
        kod = open(self.PANEL, encoding="utf-8").read()
        return set(re.findall(r'"build": lambda v: \(?\s*\[\s*"([a-z0-9-]+)"', kod))

    def test_paneldeki_her_arac_taninir_ve_ayrintili(self):
        araclar = self.panel_araclari()
        self.assertGreaterEqual(len(araclar), 10, araclar)
        for arac in araclar:
            with self.subTest(arac=arac):
                ad, tanim = M._tanim_bul(arac)
                self.assertIsNotNone(tanim, arac)
        for ad, k in veri_saldiri.KOMUTLAR.items():
            with self.subTest(arac=ad):
                self.assertIn("nasil", k)
                self.assertIn("savunma", k)
                self.assertGreaterEqual(len(k["bayraklar"]), 6, ad)

    def test_hedefe_dokunan_araclarda_etik_hatirlatma(self):
        for arac in ("nmap", "nikto", "sqlmap", "hydra", "aircrack-ng"):
            with self.subTest(arac=arac):
                self.assertTrue(veri_saldiri.KOMUTLAR[arac].get("etik"), arac)
                metin = M.acikla(f"{arac} -h 10.0.0.5", "tr")
                self.assertIn(M.ETIKETLER["etik"]["tr"], metin)

    def test_nmap_ayrintisi(self):
        s = M.ayristir("sudo nmap -sS -sV -T4 -p 22,80 -oN out.txt 192.168.1.10")
        p = s["parcalar"][0]
        self.assertEqual(p["komut"], "nmap")
        self.assertEqual([b["ad"] for b in p["bayraklar"]], ["-sS", "-sV", "-T4", "-p", "-oN"])
        self.assertEqual(p["konumsal"], ["192.168.1.10"])
        self.assertFalse(p["bilinmeyen"])
        metin = M.metin_olustur(s, "tr")
        for parca in ("Nasıl çalışır", "Savunma tarafı", "SYN", "-p 22,80"):
            self.assertIn(parca, metin)

    def test_gurultu_bayrakla_yukselir(self):
        self.assertEqual(M.ayristir("nmap -sn 10.0.0.0/24")["parcalar"][0]["gurultu"], "orta")
        self.assertEqual(M.ayristir("nmap -A 10.0.0.5")["parcalar"][0]["gurultu"], "yuksek")
        self.assertEqual(M.ayristir("tcpdump -i eth0 -c 10")["parcalar"][0]["gurultu"], "dusuk")

    def test_nc_kume_ve_takma_ad(self):
        p = M.ayristir("netcat -lvnp 4444")["parcalar"][0]
        self.assertEqual(p["komut"], "nc")
        self.assertEqual([(b["ad"], b["deger"]) for b in p["bayraklar"]],
                         [("-l", None), ("-v", None), ("-n", None), ("-p", "4444")])

    def test_john_ve_hydra_bicimleri(self):
        p = M.ayristir("john --wordlist=liste.txt --format=raw-md5 hash.txt")["parcalar"][0]
        self.assertEqual([(b["ad"], b["deger"]) for b in p["bayraklar"]],
                         [("--wordlist", "liste.txt"), ("--format", "raw-md5")])
        p = M.ayristir("hydra -L k.txt -P p.txt -t 4 10.0.0.5 ssh")["parcalar"][0]
        self.assertEqual(p["konumsal"], ["10.0.0.5", "ssh"])
        self.assertEqual(p["gurultu"], "yuksek")


class PanelAciklaDugmesiTesti(unittest.TestCase):
    PANEL = SaldiriAraclariTesti.PANEL

    def test_dugme_motoru_kullanir_ve_calistirmaz(self):
        kod = open(self.PANEL, encoding="utf-8").read()
        self.assertIn("import acikla_motor", kod)
        self.assertIn("self.explain_btn", kod)
        govde = kod[kod.index("    def explain_text(self):"):kod.index("    def _etik_onay(self, values):")]
        self.assertIn("acikla_motor.acikla(", govde)
        for yasak in ("subprocess", "Popen", "_worker", "pkexec", "threading"):
            self.assertNotIn(yasak, govde)


if __name__ == "__main__":
    unittest.main()
