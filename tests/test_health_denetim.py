#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sistem Sagligi kotuye kullanim / hata yolu testleri: docs/DENETIM.md'deki H- bulgularinin kalici
karsiliklari. Komut ciktilari sahte calistiriciyla verilir; root ve ag gerektirmez, GTK gerektirmez.
Her sinif bir bulguyu kapatir ve o bulgunun numarasini adinda tasir.

Calistirma:  python3 tests/test_health_denetim.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_health_faz1 as F  # noqa: E402

H = F.modulu_yukle()
YOL = F.YOL


class Taban(unittest.TestCase):
    def kur(self, **degerler):
        eskiler = {}
        for ad, deger in degerler.items():
            eskiler[ad] = getattr(H, ad)
            setattr(H, ad, deger)
        self.addCleanup(lambda: [setattr(H, a, d) for a, d in eskiler.items()])

    def sahte_run(self, kod, cikti):
        self.kur(run=lambda cmd, timeout=12, env=None: (kod, cikti))


class H01RootDenetimiCalisir(unittest.TestCase):
    """--audit-json yolu GTK'siz ortamda gercekten calismali (pkexec ile root olarak calisir)."""

    def test_audit_json_gtksiz_ortamda_gecerli_json_verir(self):
        gecici = tempfile.mkdtemp(prefix="saglik-gtksiz-")
        self.addCleanup(shutil.rmtree, gecici, True)
        os.makedirs(os.path.join(gecici, "gi"))
        with open(os.path.join(gecici, "gi", "__init__.py"), "w") as f:
            f.write("raise ImportError('GTK yok (test)')\n")
        ortam = dict(os.environ, PYTHONPATH=gecici, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run([sys.executable, YOL, "--audit-json"], env=ortam,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        veri = json.loads(proc.stdout)
        self.assertEqual({r["id"] for r in veri}, {c["id"] for c in H.CHECKS})
        for r in veri:
            self.assertEqual(set(r["detail"]), {"tr", "en"}, r["id"])
            self.assertIn(r["status"], {H.OK, H.WARN, H.FAIL, H.INFO, H.NEEDROOT})

    def test_dil_modulu_denetimlerden_once_yuklenir(self):
        with open(YOL, encoding="utf-8") as f:
            kaynak = f.read()
        self.assertLess(kaynak.index("\nimport dil"), kaynak.index("def run_all_checks"))
        self.assertLess(kaynak.index("\nimport dil"), kaynak.index("\nimport gi"))

    def test_audit_json_coz(self):
        liste = [{"id": "a", "status": "ok", "detail": {"tr": "x", "en": "y"}}]
        self.assertEqual(H.audit_json_coz(0, json.dumps(liste))[0]["id"], "a")
        # stderr uyarisi onde olsa da son satir JSON ise okunur
        self.assertIsNotNone(H.audit_json_coz(0, "uyari\n" + json.dumps(liste)))
        for kod, cikti in ((126, json.dumps(liste)), (0, ""), (0, "Traceback ..."),
                           (0, "{}"), (0, "[]"), (0, '[{"id": 1}]')):
            self.assertIsNone(H.audit_json_coz(kod, cikti), (kod, cikti))


class H02KeptBackGuncellemeler(Taban):
    KEPT = ("Reading package lists...\nThe following packages have been kept back:\n"
            "  linux-image-amd64 linux-headers-amd64\n  firefox-esr\n"
            "0 upgraded, 0 newly installed, 0 to remove and 3 not upgraded.\n")

    def test_kept_back_paketler_sayilir(self):
        self.assertEqual(H.kept_back_packages(self.KEPT),
                         ["linux-image-amd64", "linux-headers-amd64", "firefox-esr"])
        self.assertEqual(H.kept_back_packages(""), [])

    def test_yalniz_kept_back_varsa_sistem_guncel_denmez(self):
        self.kur(have=lambda b: True)
        self.sahte_run(0, self.KEPT)
        r = H.check_pending_updates()
        self.assertEqual(r["status"], H.WARN)
        self.assertIn("3", r["detail"]["en"])
        self.assertIn("held back", r["detail"]["en"])

    def test_bos_cikti_guncel(self):
        self.kur(have=lambda b: True)
        self.sahte_run(0, "Reading package lists...\n")
        self.assertEqual(H.check_pending_updates()["status"], H.OK)

    def test_guvenlik_guncellemesi_fail(self):
        self.kur(have=lambda b: True)
        self.sahte_run(0, "Inst libc6 [1] (2 Debian-Security:13/stable-security [amd64])\n")
        self.assertEqual(H.check_pending_updates()["status"], H.FAIL)

    def test_eylem_onay_iletisi_kapsami_soyler(self):
        meta = [c for c in H.CHECKS if c["id"] == "updates"][0]
        a = meta["action"]
        self.assertIn("--no-remove dist-upgrade", a["cmd"])
        self.assertIn("kaldırılmaz", a["note"]["tr"])
        self.assertIn("no package is removed", a["note"]["en"])


class H03YetkiliYolSistemDizinleri(Taban):
    def test_kullanici_PATH_inde_olan_arac_bulunmus_sayilmaz(self):
        gecici = tempfile.mkdtemp(prefix="saglik-path-")
        self.addCleanup(shutil.rmtree, gecici, True)
        yol = os.path.join(gecici, "carotos-sahte-arac")
        with open(yol, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(yol, 0o755)
        eski = os.environ["PATH"]
        os.environ["PATH"] = gecici + os.pathsep + eski
        self.addCleanup(os.environ.__setitem__, "PATH", eski)
        self.assertFalse(H.have("carotos-sahte-arac"))
        self.assertIsNone(H.bin_path("carotos-sahte-arac"))

    def test_deep_komutu_yalniz_sistem_yollariyla_kurulur(self):
        self.kur(sistem_yolu=lambda ad: "/usr/bin/" + ad)
        self.assertEqual(H.deep_command("rkhunter", ["--check"]),
                         ["pkexec", "/usr/bin/env", "LC_ALL=C", "/usr/bin/rkhunter", "--check"])

    def test_arac_sistem_dizininde_yoksa_komut_kurulmaz(self):
        self.kur(sistem_yolu=lambda ad: None if ad == "rkhunter" else "/usr/bin/" + ad)
        self.assertIsNone(H.deep_command("rkhunter", ["--check"]))

    def test_calistirici_temiz_ortamla_calisir(self):
        kod, cikti = H.run(["sh", "-c", 'printf "%s|%s" "$LC_ALL" "$PATH"'])
        self.assertEqual(kod, 0)
        self.assertEqual(cikti, "C|/usr/sbin:/usr/bin:/sbin:/bin")

    def test_ufw_yoksa_bilinmiyor(self):
        self.kur(is_root=lambda: True, bin_path=lambda ad: None)
        r = H.check_firewall_policy()
        self.assertEqual(r["status"], H.INFO)
        self.assertTrue(r.get("unknown"))


class H04KaldirilmisPaketKurulSayilmaz(Taban):
    def test_ayari_kalmis_paket_uyarir(self):
        self.sahte_run(0, "deinstall ok config-files")
        self.assertEqual(H.check_unattended()["status"], H.WARN)

    def test_kurulu_paket_tamam(self):
        self.sahte_run(0, "install ok installed")
        self.assertEqual(H.check_unattended()["status"], H.OK)

    def test_kurulu_degil_uyarir(self):
        self.sahte_run(1, "dpkg-query: no packages found matching unattended-upgrades")
        self.assertEqual(H.check_unattended()["status"], H.WARN)

    def test_komut_yoksa_ya_da_hata_bilinmiyor_ok_degil(self):
        for kod in (127, 124, 2):
            self.sahte_run(kod, "")
            r = H.check_unattended()
            self.assertEqual(r["status"], H.INFO, kod)
            self.assertTrue(r.get("unknown"))


class H05EskiRootSonucuYasiGosterilir(unittest.TestCase):
    def pencere(self, eski, fixed=()):
        return types.SimpleNamespace(audited_as_root=True, results=eski,
                                     fixed_ids=set(fixed), root_stamp="10:15")

    def sonuc(self, kimlik, durum):
        return {"id": kimlik, "category": "accounts", "status": durum,
                "detail": {"tr": "x", "en": "x"}}

    def test_eski_root_sonucu_yas_damgasiyla_tasinir(self):
        p = self.pencere([self.sonuc("root_locked", H.OK)])
        birlesik = H.HealthWindow.merge_results(p, [self.sonuc("root_locked", H.NEEDROOT)])
        self.assertEqual(birlesik[0]["status"], H.OK)
        self.assertEqual(birlesik[0]["stale"], "10:15")

    def test_duzeltilen_denetimin_eski_sonucu_tasinmaz(self):
        p = self.pencere([self.sonuc("root_locked", H.WARN)], fixed=["root_locked"])
        birlesik = H.HealthWindow.merge_results(p, [self.sonuc("root_locked", H.NEEDROOT)])
        self.assertEqual(birlesik[0]["status"], H.NEEDROOT)
        self.assertNotIn("stale", birlesik[0])

    def test_taze_sonuc_oldugu_gibi_kalir(self):
        p = self.pencere([self.sonuc("disk", H.WARN)])
        birlesik = H.HealthWindow.merge_results(p, [self.sonuc("disk", H.OK)])
        self.assertEqual(birlesik[0]["status"], H.OK)


class H06CalismayanDenetimOkSayilmaz(Taban):
    def test_istisna_bilinmiyor_olur(self):
        def patla():
            raise RuntimeError("bozuk")
        self.kur(CHECKS=[{"id": "x", "category": "system", "func": patla}])
        r = H.run_all_checks()[0]
        self.assertEqual(r["status"], H.INFO)
        self.assertTrue(r["unknown"])

    def test_not_run_sayimi(self):
        sonuclar = [
            {"id": "a", "status": H.OK}, {"id": "b", "status": H.INFO},          # dogasi bilgi
            {"id": "c", "status": H.INFO, "unknown": True},
            {"id": "d", "status": H.NEEDROOT},
        ]
        self.assertEqual(H.not_run(sonuclar), 2)
        self.assertEqual(H.not_run([{"id": "a", "status": H.OK}]), 0)

    def test_tum_denetimler_bilinmiyorsa_puan_sifir_ve_eksik_tam(self):
        sonuclar = [{"id": str(i), "status": H.INFO, "unknown": True} for i in range(5)]
        self.assertEqual(H.score(sonuclar), (0, 0, 0, 0))
        self.assertEqual(H.not_run(sonuclar), 5)

    def test_komut_bulunamayan_denetimler_unknown_isaretler(self):
        self.sahte_run(127, "")
        self.kur(is_root=lambda: True, bin_path=lambda ad: None, read_file=lambda p, limit=0: None)
        for fonk in (H.check_failed_units, H.check_listening_ports, H.check_root_locked,
                     H.check_empty_passwords, H.check_auth_failures, H.check_disk_usage):
            r = fonk()
            self.assertNotEqual(r["status"], H.OK, fonk.__name__)
            self.assertTrue(r.get("unknown"), fonk.__name__)

    def test_root_durumu_beklenmeyen_bicim_bilinmiyor(self):
        self.kur(is_root=lambda: True, bin_path=lambda ad: "/usr/bin/passwd")
        self.sahte_run(0, "root ?? 2020-01-01")
        r = H.check_root_locked()
        self.assertEqual(r["status"], H.INFO)
        self.assertTrue(r.get("unknown"))


class H07EylemKapsamiIletiyleUyumlu(unittest.TestCase):
    def kart(self, kimlik):
        return [c for c in H.CHECKS if c["id"] == kimlik][0]

    def test_notlu_eylemler_iki_dilli(self):
        for kimlik in ("updates", "repos", "disk", "swap_crypt"):
            note = self.kart(kimlik)["action"]["note"]
            self.assertEqual(set(note), {"tr", "en"}, kimlik)
            self.assertTrue(note["tr"].strip() and note["en"].strip(), kimlik)

    def test_yer_ac_gunluk_kisaltmaz_ve_purge_yapmaz(self):
        cmd = self.kart("disk")["action"]["cmd"]
        self.assertNotIn("journalctl", cmd)
        self.assertNotIn("--purge", cmd)
        self.assertIn("kaldırılacak", self.kart("disk")["action"]["note"]["tr"])

    def test_depo_eylemi_once_yedek_alir(self):
        cmd = self.kart("repos")["action"]["cmd"]
        self.assertIn("cp -a", cmd)
        self.assertLess(cmd.index("cp -a"), cmd.index("printf"))
        self.assertIn("yedeğe", self.kart("repos")["action"]["note"]["tr"])
        self.assertIn("backup", self.kart("repos")["action"]["note"]["en"])

    def test_swap_eylemi_zaman_damgali_yedek_alir(self):
        a = self.kart("swap_crypt")["action"]
        self.assertIn("fstab.carotos-yedek-$(date", a["cmd"])
        self.assertNotIn("sed -i.carotos-yedek", a["cmd"])
        self.assertIn("encrypted", a["note"]["en"])

    def test_pkexec_iptali_ile_komut_bulunamadi_ayrilir(self):
        self.assertTrue(H.pkexec_iptal_mi(126, "Error executing command: Not authorized"))
        self.assertTrue(H.pkexec_iptal_mi(127, ""))
        self.assertFalse(H.pkexec_iptal_mi(127, "sh: 1: ufw: not found"))
        self.assertFalse(H.pkexec_iptal_mi(1, ""))


class H08EtcTaramasiEksikseYokDenmez(Taban):
    def test_okunamayan_dizin_bilinmiyor(self):
        self.sahte_run(1, "find: '/etc/ssl/private': Permission denied")
        r = H.check_world_writable()
        self.assertEqual(r["status"], H.INFO)
        self.assertTrue(r.get("unknown"))

    def test_temiz_tarama_tamam(self):
        self.sahte_run(0, "")
        self.assertEqual(H.check_world_writable()["status"], H.OK)

    def test_bulunan_dosya_hata_satirina_ragmen_fail(self):
        self.sahte_run(1, "find: '/etc/x': Permission denied\n/etc/cron.d/a")
        self.assertEqual(H.check_world_writable()["status"], H.FAIL)


class H10DinlenenPortlar(Taban):
    SS = ("udp UNCONN 0 0 127.0.0.53%lo:53 0.0.0.0:*\n"
          "udp UNCONN 0 0 127.0.0.54:53 0.0.0.0:*\n"
          "tcp LISTEN 0 128 [::1]:631 [::]:*\n")

    def test_yerel_adresler_dista_sayilmaz(self):
        self.sahte_run(0, self.SS)
        r = H.check_listening_ports()
        self.assertEqual(r["status"], H.OK)
        self.assertIn("3", r["detail"]["en"])

    def test_dis_adres_uyarir(self):
        self.sahte_run(0, self.SS + "tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n")
        r = H.check_listening_ports()
        self.assertEqual(r["status"], H.WARN)
        self.assertIn("tcp/22", r["detail"]["en"])

    def test_bozuk_cikti_sorun_yok_denmez(self):
        self.sahte_run(0, "garbage line\nbaska bir seyler olan satir daha burada ama bozuk\n")
        r = H.check_listening_ports()
        self.assertEqual(r["status"], H.INFO)
        self.assertTrue(r.get("unknown"))

    def test_gercekten_bos_cikti_dinleyen_yok(self):
        self.sahte_run(0, "")
        self.assertEqual(H.check_listening_ports()["status"], H.OK)

    # Toshiba C660 (gercek cikti): avahi mDNS + gecici UDP portlari + DHCPv6 istemcisi
    TOSHIBA = ("udp UNCONN 0 0 0.0.0.0:46127 0.0.0.0:*\n"
               "udp UNCONN 0 0 0.0.0.0:5353 0.0.0.0:*\n"
               "udp UNCONN 0 0 [::]:5353 [::]:*\n"
               "udp UNCONN 0 0 [fe80::b674:9fff:fe9d:acbd]%wlp6s0b1:546 [::]:*\n"
               "udp UNCONN 0 0 [::]:35472 [::]:*\n")

    def _sahte(self, ss, avahi="inactive", ufw="inactive"):
        def run(cmd, timeout=12, env=None):
            if cmd[0] == "ss":
                return 0, ss
            if cmd[:2] == ["systemctl", "is-active"]:
                return 0, avahi if cmd[2] == "avahi-daemon" else ufw
            return 1, ""
        self.kur(run=run)

    def test_avahi_ve_dhcpv6_beklenen_sayilir(self):
        self._sahte(self.TOSHIBA, avahi="active")
        r = H.check_listening_ports()
        self.assertEqual(r["status"], H.OK, r)                  # artik puan kirmaz
        self.assertIn("DHCP/mDNS", r["detail"]["tr"])

    def test_avahi_yokken_gecici_udp_portlari_beklenmez(self):
        self._sahte(self.TOSHIBA, avahi="inactive")
        r = H.check_listening_ports()
        self.assertEqual(r["status"], H.WARN)
        self.assertIn("udp/46127", r["detail"]["en"])
        self.assertNotIn("5353", r["detail"]["en"])

    def test_surec_adi_varsa_ona_gore_karar_verilir(self):
        ss = ('udp UNCONN 0 0 0.0.0.0:40000 0.0.0.0:* users:(("avahi-daemon",pid=612,fd=14))\n'
              'tcp LISTEN 0 128 0.0.0.0:8080 0.0.0.0:* users:(("python3",pid=900,fd=3))\n')
        self._sahte(ss)
        r = H.check_listening_ports()
        self.assertEqual(r["status"], H.WARN)
        self.assertIn("tcp/8080 (python3)", r["detail"]["en"])
        self.assertNotIn("40000", r["detail"]["en"])

    def test_guvenlik_duvari_engelliyorsa_beklenmeyen_dinleyici_puan_kirmaz_ama_bilgi_verir(self):
        ss = "tcp LISTEN 0 128 0.0.0.0:8080 0.0.0.0:*\n"
        self._sahte(ss, ufw="active")
        self.kur(read_file=lambda y, limit=200000: (
            "ENABLED=yes\n" if y.endswith("ufw.conf") else 'DEFAULT_INPUT_POLICY="DROP"\n'),
            is_root=lambda: False)
        r = H.check_listening_ports()
        self.assertEqual(r["status"], H.INFO)           # puana girmez; root olmadan izin kurali okunamaz
        self.assertTrue(r.get("unknown"))
        self.assertIn("8080", r["detail"]["tr"])

    def test_root_ve_izin_kurali_yoksa_tamam_varsa_uyarir(self):
        ss = "tcp LISTEN 0 128 0.0.0.0:8080 0.0.0.0:*\n"
        self._sahte(ss, ufw="active")
        durum = {"ufw": "Status: active\n\nTo   Action  From\n22/tcp   ALLOW   Anywhere\n"}

        def run(cmd, timeout=12, env=None):
            if cmd[0] == "ss":
                return 0, ss
            if cmd[:2] == ["systemctl", "is-active"]:
                return 0, "active" if cmd[2] == "ufw" else "inactive"
            if cmd[-1] == "status":
                return 0, durum["ufw"]
            return 1, ""
        self.kur(run=run, is_root=lambda: True, bin_path=lambda n: "/usr/sbin/" + n,
                 read_file=lambda y, limit=200000: (
                     "ENABLED=yes\n" if y.endswith("ufw.conf") else 'DEFAULT_INPUT_POLICY="DROP"\n'))
        self.assertEqual(H.check_listening_ports()["status"], H.OK)
        durum["ufw"] += "8080/tcp   ALLOW   Anywhere\n"
        self.assertEqual(H.check_listening_ports()["status"], H.WARN)

    def test_oneri_komutu_sureci_gosterir(self):
        meta = [m for m in H.CHECKS if m["id"] == "ports"][0]
        self.assertEqual(meta["fix"], "sudo ss -tulnp")


class H11SwapZram(Taban):
    BASLIK = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n"

    def test_yolunda_zram_gecen_disk_swapi_ram_ici_sayilmaz(self):
        metin = self.BASLIK + "/home/kullanici/zram/swapfile  file\t1000\t0\t-2\n"
        r = H.check_swap_encryption(metin, lambda y, t: False)
        self.assertEqual(r["status"], H.WARN)

    def test_gercek_zram_ram_ici(self):
        metin = self.BASLIK + "/dev/zram0  partition\t1000\t0\t100\n"
        self.assertEqual(H.check_swap_encryption(metin, lambda y, t: self.fail("sorulmamali"))["status"], H.OK)

    def test_proc_swaps_bosluk_kodu_cozulur(self):
        metin = self.BASLIK + "/mnt/a\\040b/swap  file\t1000\t0\t-2\n"
        self.assertEqual(H.swap_cihazlari(metin), [("/mnt/a b/swap", "file")])


class H12KimlikGunluguEslesmeYok(Taban):
    def test_kod_1_ve_bos_cikti_sifir_deneme(self):
        self.kur(is_root=lambda: True)
        self.sahte_run(1, "")
        r = H.check_auth_failures()
        self.assertEqual(r["status"], H.OK)

    def test_kod_1_ve_hata_metni_bilinmiyor(self):
        self.kur(is_root=lambda: True)
        self.sahte_run(1, "No journal files were found.")
        r = H.check_auth_failures()
        self.assertEqual(r["status"], H.INFO)
        self.assertTrue(r.get("unknown"))

    def test_cok_deneme_uyarir(self):
        self.kur(is_root=lambda: True)
        self.sahte_run(0, "\n".join("Failed password %d" % i for i in range(25)))
        self.assertEqual(H.check_auth_failures()["status"], H.WARN)


if __name__ == "__main__":
    unittest.main(verbosity=1)
