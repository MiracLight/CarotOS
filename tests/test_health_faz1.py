#!/usr/bin/env python3
"""Sistem Sagligi Faz 1 mantik testleri (GTK gerektirmez; ISO'ya girmez).

Kullanim (depo kokunden):  python3 tests/test_health_faz1.py
"""
import importlib.util
import os
import sys
import types
import unittest

# Test, ISO agacina __pycache__ birakmasin
sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOL = os.environ.get("HEALTH_YOLU") or os.path.join(
    KOK, "config/includes.chroot/opt/carotos/health/carotos-health.py")


def modulu_yukle():
    """gi'yi sahte bir modulle degistirip dosyayi iceri alir."""
    class _Pencere:
        pass
    gtk = types.SimpleNamespace(Window=_Pencere, Image=_Pencere)
    glib = types.SimpleNamespace(get_user_config_dir=lambda: "/tmp",
                                 get_home_dir=lambda: "/tmp")
    repo = types.SimpleNamespace(Gtk=gtk, Gdk=types.SimpleNamespace(),
                                 GdkPixbuf=types.SimpleNamespace(), GLib=glib)
    gi = types.ModuleType("gi")
    gi.require_version = lambda *a, **k: None
    gi.repository = repo
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = repo
    spec = importlib.util.spec_from_file_location("carotos_health", YOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H = modulu_yukle()

AA_ORNEK = """/usr/bin/man (enforce)
lsb_release (enforce)
tcpdump (enforce)
Xorg (complain)
plasmashell (complain)
plasmashell//QtWebEngineProcess (complain)
garip satir
"""


class Ortak(unittest.TestCase):
    def kur(self, **degerler):
        """H icindeki yardimcilari gecici olarak degistirir."""
        eskiler = {}
        for ad, deger in degerler.items():
            eskiler[ad] = getattr(H, ad)
            setattr(H, ad, deger)
        self.addCleanup(lambda: [setattr(H, a, d) for a, d in eskiler.items()])


class AppArmorProfilTesti(Ortak):
    def test_sayim(self):
        s = H.parse_aa_profiles(AA_ORNEK)
        self.assertEqual((s["enforce"], s["complain"], s["toplam"]), (3, 3, 6))

    def test_bos(self):
        self.assertEqual(H.parse_aa_profiles("")["toplam"], 0)
        self.assertEqual(H.parse_aa_profiles(None)["toplam"], 0)

    def test_ok_durumu(self):
        self.kur(is_root=lambda: True, have=lambda b: True,
                 read_file=lambda p, limit=0: AA_ORNEK,
                 _systemd_durum=lambda b: (True, True))
        self.assertEqual(H.check_apparmor_profiles()["status"], H.OK)

    def test_hepsi_sikayet_uyarir(self):
        self.kur(is_root=lambda: True, have=lambda b: True,
                 read_file=lambda p, limit=0: "Xorg (complain)\n",
                 _systemd_durum=lambda b: (True, True))
        self.assertEqual(H.check_apparmor_profiles()["status"], H.WARN)

    def test_hizmet_kapali_ama_profil_yuklu(self):
        self.kur(is_root=lambda: True, have=lambda b: True,
                 read_file=lambda p, limit=0: AA_ORNEK,
                 _systemd_durum=lambda b: (False, False))
        self.assertEqual(H.check_apparmor_profiles()["status"], H.WARN)

    def test_root_degilse_needroot(self):
        self.kur(is_root=lambda: False)
        self.assertEqual(H.check_apparmor_profiles()["status"], H.NEEDROOT)


class AppArmorDurumTesti(Ortak):
    def _durum(self, cekirdek, enabled, running, kurulu=True):
        self.kur(have=lambda b: kurulu,
                 read_file=lambda p, limit=0: cekirdek,
                 _systemd_durum=lambda b: (enabled, running))
        return H.check_apparmor_enabled()["status"]

    def test_acik(self):
        self.assertEqual(self._durum("Y\n", True, True), H.OK)

    def test_kapali(self):
        self.assertEqual(self._durum("Y\n", False, False), H.FAIL)

    def test_yari_acik(self):
        self.assertEqual(self._durum("Y\n", True, False), H.FAIL)
        self.assertEqual(self._durum("Y\n", False, True), H.FAIL)

    def test_cekirdekte_kapali(self):
        self.assertEqual(self._durum("N\n", True, True), H.WARN)

    def test_kurulu_degil(self):
        self.assertEqual(self._durum("", False, False, kurulu=False), H.INFO)


class DebsumsTesti(unittest.TestCase):
    def test_temiz(self):
        self.assertEqual(H.parse_debsums(0, "")["status"], H.OK)

    def test_degisen_cesitli_bicimler(self):
        out = ("/usr/bin/ornek                                       FAILED\n"
               "debsums: changed file /usr/lib/x (from paket package)\n"
               "debsums: no md5sums for paket2\n")
        r = H.parse_debsums(2, out)
        self.assertEqual(r["status"], H.WARN)
        self.assertEqual(len(r["extra"]), 2)

    def test_yorumlanamayan(self):
        self.assertEqual(H.parse_debsums(3, "tuhaf cikti\n")["status"], H.INFO)

    def test_beklenen_dosya_uyari_uretmez(self):
        out = "debsums: changed file /usr/lib/os-release (from base-files package)\n"
        r = H.parse_debsums(2, out)
        self.assertEqual(r["status"], H.OK)
        self.assertEqual(len(r["extra"]), 1)
        self.assertIn("CarotOS", r["extra"][0]["explain"]["tr"])
        out2 = out + "/usr/bin/ornek                                       FAILED\n"
        r2 = H.parse_debsums(2, out2)
        self.assertEqual(r2["status"], H.WARN)
        self.assertIn("1 dosyanın", r2["detail"]["tr"])

    def test_calistirilamadi(self):
        self.assertEqual(H.parse_debsums(126, "")["status"], H.INFO)


class RkhunterTesti(unittest.TestCase):
    def test_syslog_secenegi_sabit(self):
        rk = [s for s in H.DEEP_SCANS if s["id"] == "rkhunter"][0]
        for liste in (rk["args"], rk["propupd_args"]):
            i = liste.index("--syslog")
            self.assertEqual(liste[i + 1], "none")

    def test_temiz(self):
        r = H.parse_rkhunter(0, "")
        self.assertEqual(r["status"], H.OK)
        # Temiz sonuc "guvenlidir" demez; garanti verilmedigini belirtir
        self.assertIn("garanti etmez", r["detail"]["tr"])
        self.assertIn("does not guarantee", r["detail"]["en"])

    def test_uyarilar_ve_aciklamalar(self):
        out = ("Warning: The command '/usr/bin/lwp-request' has been replaced by a script: x\n"
               "    some detail\n"
               "Warning: Hidden file found: /etc/.updated: ASCII text\n"
               "Warning: The file properties have changed:\n"
               "Warning: Garip yeni bir uyari\n")
        r = H.parse_rkhunter(1, out)
        self.assertEqual(r["status"], H.WARN)
        self.assertEqual(len(r["extra"]), 4)
        self.assertIn("betik", r["extra"][0]["explain"]["tr"])
        self.assertIn("Gizli", r["extra"][1]["explain"]["tr"])
        self.assertEqual(r["extra"][3]["explain"], H._RKH_VARSAYILAN)

    def test_yorumlanamayan_hata(self):
        self.assertEqual(H.parse_rkhunter(2, "Error: bir sey\n")["status"], H.INFO)

    def test_onkosul_uyarisi_tehdit_sayilmaz(self):
        out = "Warning: Checking for prerequisites               [ Warning ]\n"
        r = H.parse_rkhunter(1, out)
        self.assertEqual(r["status"], H.INFO)
        self.assertEqual(len(r["extra"]), 1)
        self.assertIn("tehdit bulgusu değildir", r["extra"][0]["explain"]["tr"])
        self.assertIn("garanti etmez", r["detail"]["tr"])

    def test_onkosul_ve_gercek_uyari(self):
        out = ("Warning: Checking for prerequisites [ Warning ]\n"
               "Warning: Hidden file found: /etc/.x: ASCII text\n")
        r = H.parse_rkhunter(1, out)
        self.assertEqual(r["status"], H.WARN)
        self.assertIn("1 uyarı", r["detail"]["tr"])
        self.assertEqual(len(r["extra"]), 2)

    def test_ilk_calistirma_uyarilari_kayit_aciklamasi_alir(self):
        for metin in ("Unable to check for passwd file differences: no copy of the passwd file exists.",
                      "WARNING! It is the users responsibility to ensure that when the '--propupd' option"):
            self.assertIn("Kaydı yenile", H.rkhunter_aciklama(metin)["tr"], metin)

    def test_uyari_altindaki_ayrintilar_birlikte_gosterilir(self):
        out = ("Warning: The following suspicious (large) shared memory segments have been found:\n"
               "         Process: /usr/bin/xfdesktop    PID: 1654    Owner: u    Size: 32MB\n"
               "         Process: /usr/bin/xfce4-terminal    PID: 1861    Owner: u    Size: 1.0MB\n"
               "\n"
               "Warning: Hidden file found: /etc/.updated: ASCII text\n")
        r = H.parse_rkhunter(1, out)
        self.assertEqual(len(r["extra"]), 2)
        self.assertIn("xfdesktop", r["extra"][0]["text"])
        self.assertIn("xfce4-terminal", r["extra"][0]["text"])
        self.assertNotIn("xfdesktop", r["extra"][1]["text"])
        self.assertIn("paylaşımlı bellek", r["extra"][0]["explain"]["tr"])

    def test_kendi_sureci_bellek_uyarisindan_cikarilir(self):
        out = ("Warning: The following suspicious (large) shared memory segments have been found:\n"
               "         Process: /usr/bin/python3.13    PID: 4242    Owner: u    Size: 4.0MB\n")
        # Yalnizca kendi surecimiz listelenmisse uyari hic gosterilmez
        self.assertEqual(H.parse_rkhunter(1, out, own_pid=4242)["status"], H.OK)
        # Baska bir surec de varsa o kalir, kendi surecimiz cikar
        out2 = out + "         Process: /usr/bin/bilinmeyen    PID: 777    Owner: u    Size: 9MB\n"
        r = H.parse_rkhunter(1, out2, own_pid=4242)
        self.assertEqual(r["status"], H.WARN)
        self.assertIn("bilinmeyen", r["extra"][0]["text"])
        self.assertNotIn("4242", r["extra"][0]["text"])
        # Baska bir surec numarasi (4242'nin on eki) yanlislikla eslesmez
        r3 = H.parse_rkhunter(1, out.replace("4242", "42421"), own_pid=4242)
        self.assertEqual(r3["status"], H.WARN)

    def test_derin_komut_dil_ayari(self):
        komut = H.deep_command("rkhunter", ["--check"])
        self.assertEqual(komut[0], "pkexec")
        self.assertIn("LC_ALL=C", komut)
        self.assertEqual(komut[-1], "--check")


class RkhunterAyarTesti(unittest.TestCase):
    YOL = os.path.join(KOK, "config/includes.chroot/etc/rkhunter.conf.local")

    def test_yerel_ayar_syslogu_kapatir(self):
        # Turkce dil ayarinda rkhunter varsayilan USE_SYSLOG degerini gecersiz
        # sayip --config-check'i (ve paket kurulumunu) bozuyor.
        with open(self.YOL, encoding="utf-8") as f:
            satirlar = [s.strip() for s in f if s.strip() and not s.startswith("#")]
        self.assertIn("USE_SYSLOG=none", satirlar)

    def test_yerel_ayar_yalniz_bilinen_anahtarlar(self):
        izinli = {"SCRIPTWHITELIST", "ALLOWHIDDENFILE", "ALLOWIPCPROC", "USE_SYSLOG"}
        with open(self.YOL, encoding="utf-8") as f:
            for s in f:
                s = s.strip()
                if s and not s.startswith("#"):
                    self.assertIn(s.split("=")[0], izinli, s)


class DenetimHookTesti(unittest.TestCase):
    YOL = os.path.join(KOK, "config/hooks/live/9990-carotos-denetim-araclari.hook.chroot")

    def test_kurulum_dil_ayarindan_bagimsiz(self):
        with open(self.YOL, encoding="utf-8") as f:
            komutlar = [s.strip() for s in f if "apt-get install" in s and not s.lstrip().startswith("#")]
        self.assertEqual(len(komutlar), 1)
        self.assertTrue(komutlar[0].startswith("LC_ALL=C "), komutlar[0])
        self.assertIn("--no-install-recommends", komutlar[0])


class YapiTesti(unittest.TestCase):
    def iki_dilli(self, sozluk, yer):
        self.assertEqual(set(sozluk), {"tr", "en"}, yer)
        for dil in ("tr", "en"):
            self.assertTrue(sozluk[dil].strip(), yer)

    def test_denetim_kimlikleri_benzersiz(self):
        kimlikler = [c["id"] for c in H.CHECKS]
        self.assertEqual(len(kimlikler), len(set(kimlikler)))

    def test_kategoriler_tanimli(self):
        kategoriler = {k for k, _ in H.CATEGORIES}
        for c in H.CHECKS:
            self.assertIn(c["category"], kategoriler, c["id"])
        self.assertIn("deep", kategoriler)

    def test_baslik_ve_neden_iki_dilli(self):
        for c in H.CHECKS:
            self.iki_dilli(c["title"], c["id"])
            self.iki_dilli(c["why"], c["id"])
        for k, etiket in H.CATEGORIES:
            self.iki_dilli(etiket, k)

    def test_off_eylemleri(self):
        bulunan = [c["id"] for c in H.CHECKS if "off" in c]
        self.assertEqual(sorted(bulunan), ["apparmor", "fw_enabled"])
        for c in H.CHECKS:
            off = c.get("off")
            if not off:
                continue
            self.assertTrue(off["confirm"], "kapatma her zaman onay ister")
            self.iki_dilli(off["label"], c["id"])
            self.iki_dilli(off["warning"], c["id"])
            self.assertIsInstance(off["cmd"], str)
            self.assertIn("action", c, "kapatilan korumanin acma eylemi de olmali")

    def test_komutlar_sabit(self):
        # Faz 1'in getirdigi komutlar yalnizca harf, tire ve bosluk icerir:
        # degisken, kabuk ozel karakteri ya da kullanici metni yok.
        import re
        for c in H.CHECKS:
            if c["id"] not in ("apparmor", "fw_enabled"):
                continue
            for anahtar in ("action", "off"):
                if (c["id"], anahtar) == ("apparmor", "off"):
                    continue  # asagida birebir sabit olarak denetlenir
                self.assertRegex(c[anahtar]["cmd"], r"^[a-z\- ]+$", c["id"])

    def test_apparmor_kapatma_profilleri_kaldirir(self):
        apparmor = [c for c in H.CHECKS if c["id"] == "apparmor"][0]
        komut = apparmor["off"]["cmd"]
        self.assertTrue(komut.startswith("systemctl disable --now apparmor && "))
        self.assertIn("aa-teardown", komut)
        # Kullanici metni ya da degisken yok; yalniz bilinen sabit ifade
        self.assertEqual(komut.count("$("), 1)
        self.assertIn("/sys/kernel/security/apparmor/profiles", komut)
        self.assertIn("kaldırılacak", apparmor["off"]["warning"]["tr"])

    def test_derin_taramalar(self):
        kimlikler = [s["id"] for s in H.DEEP_SCANS]
        self.assertEqual(kimlikler, ["debsums", "rkhunter"])
        for s in H.DEEP_SCANS:
            for liste in (s["args"], s.get("propupd_args", [])):
                self.assertTrue(all(isinstance(a, str) for a in liste))
                self.assertTrue(liste == [] or liste[0].startswith("-"))
                # Degeri olan secenekler disinda her oge "-" ile baslar
                for onceki, a in zip([""] + liste, liste):
                    self.assertTrue(a.startswith("-") or onceki == "--syslog", a)
            self.assertTrue(s["timeout"] > 0)
            self.iki_dilli(s["title"], s["id"])
            self.iki_dilli(s["why"], s["id"])
            self.assertTrue(callable(s["parse"]))

    def test_ui_metinleri_iki_dilli(self):
        for anahtar, sozluk in H.UI.items():
            self.iki_dilli(sozluk, anahtar)

    def test_ui_yer_tutuculari_tutarli(self):
        import re
        for anahtar, sozluk in H.UI.items():
            tr = set(re.findall(r"\{(\w+)\}", sozluk["tr"]))
            en = set(re.findall(r"\{(\w+)\}", sozluk["en"]))
            self.assertEqual(tr, en, anahtar)

    def test_tum_denetimler_calisir(self):
        # Sandbox'ta bile cokmemeli; her sonuc gecerli bir durum dondurmeli
        gecerli = {H.OK, H.WARN, H.FAIL, H.INFO, H.NEEDROOT}
        for r in H.run_all_checks():
            self.assertIn(r["status"], gecerli, r["id"])
            self.iki_dilli(r["detail"], r["id"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
