#!/usr/bin/env python3
"""Carotene ve ortak tarama motoru testleri (GTK gerektirmez; ISO'ya girmez).

Kullanim (depo kokunden):  python3 tests/test_carotene.py

clamscan kuruluysa gercek tarama testleri de calisir: EICAR test dizgisi
icin gecici bir imza dosyasi uretilir, sistemin tanimlarina dokunulmaz.
"""
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOTOR_YOLU = os.environ.get("MOTOR_YOLU") or os.path.join(
    KOK, "config/includes.chroot/opt/carotos/ortak/tarama_motoru.py")

_spec = importlib.util.spec_from_file_location("tarama_motoru", MOTOR_YOLU)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

EICAR = ("X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-"
         "TEST-FILE!$H+H*\n")


class GeciciEv(unittest.TestCase):
    """Her test kendi gecici XDG_DATA_HOME'u ile calisir."""

    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="carotene-test-")
        self.eski = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = os.path.join(self.kok, "veri")

    def tearDown(self):
        if self.eski is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = self.eski
        for kok, dizinler, dosyalar in os.walk(self.kok):
            for ad in dizinler + dosyalar:
                try:
                    os.chmod(os.path.join(kok, ad), 0o700)
                except OSError:
                    pass
        shutil.rmtree(self.kok, ignore_errors=True)

    def dosya(self, ad, icerik="x", mod=0o644):
        yol = os.path.join(self.kok, ad)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as fh:
            fh.write(icerik)
        os.chmod(yol, mod)
        return yol


class SatirCozmeTesti(unittest.TestCase):
    def test_turler(self):
        self.assertEqual(M.satir_coz("/a/b.txt: OK\n"), ("temiz", "/a/b.txt"))
        self.assertEqual(M.satir_coz("/a/x: b.com: Eicar-Signature FOUND\n"),
                         ("bulgu", ("/a/x: b.com", "Eicar-Signature")))
        self.assertEqual(M.satir_coz("/a/bos: Empty file"), ("atlandi", "/a/bos"))
        self.assertEqual(M.satir_coz("/a/k: Excluded"), ("atlandi", "/a/k"))
        self.assertEqual(M.satir_coz("WARNING: /x: Can't access file")[0], "uyari")
        self.assertEqual(M.satir_coz("   \n"), (None, None))

    def test_komut_kabuksuz_ve_ayiracli(self):
        komut = M.tarama_komutu(["/home/u/-rf", "/home/u/a b"], ["/home/u/.k"])
        i = komut.index("--")
        self.assertEqual(komut[i + 1:], ["/home/u/-rf", "/home/u/a b"])
        self.assertTrue(all(not a.startswith("/home/u/-") for a in komut[:i]))
        self.assertIn("--exclude-dir=^/home/u/\\.k$", komut)


class TanimTesti(unittest.TestCase):
    BASLIK = ("ClamAV-VDB:25 Oct 2026 07:20 -0400:28164:355788:90:"
              "0123456789abcdef:sig:svc.clamav-publisher:1792927200")

    def test_baslik(self):
        b = M.cvd_basligi_coz(self.BASLIK.encode() + b"\0" * 100)
        self.assertEqual((b["surum"], b["imza"], b["zaman"]),
                         (28164, 355788, 1792927200))
        self.assertIsNone(M.cvd_basligi_coz(b"bozuk"))

    def test_dizin(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(M.tanim_bilgisi(d)["durum"], M.TANIM_YOK)
            with open(os.path.join(d, "daily.cvd"), "wb") as fh:
                fh.write(self.BASLIK.encode().ljust(512, b" "))
            with open(os.path.join(d, "main.cvd"), "wb") as fh:
                fh.write(self.BASLIK.replace(":355788:", ":3287027:")
                         .replace(":1792927200", ":1700000000").encode())
            b = M.tanim_bilgisi(d, simdi=1792927200 + 2 * 86400)
            self.assertEqual(b["durum"], M.TANIM_GUNCEL)
            self.assertEqual(b["yas_gun"], 2)
            self.assertEqual(b["imza"], 355788 + 3287027)
            eski = M.tanim_bilgisi(d, simdi=1792927200 + 30 * 86400)
            self.assertEqual(eski["durum"], M.TANIM_ESKI)


class GuncellemeSonucuTesti(unittest.TestCase):
    CEVRIMDISI = """Trying to retrieve CVD header from https://database.clamav.net/daily.cvd
WARNING: remote_cvdhead: Download failed (56) WARNING:  Message: Failure when receiving data from the peer
ERROR: Database update process failed: HTTP GET failed
ERROR: Update failed."""
    GUNCEL = ("daily.cvd database is up-to-date (version: 28164, sigs: 355788)\n"
              "main.cvd database is up-to-date (version: 63)")

    def test_durumlar(self):
        self.assertEqual(M.guncelleme_sonucu(11, self.CEVRIMDISI), M.CEVRIMDISI)
        self.assertEqual(M.guncelleme_sonucu(0, self.GUNCEL), M.ZATEN_GUNCEL)
        self.assertEqual(M.guncelleme_sonucu(0, "daily.cld updated (version: 28165)"),
                         M.GUNCELLENDI)
        self.assertEqual(M.guncelleme_sonucu(
            1, "You are on cool-down until after: 2026-10-26"), M.BEKLEME)
        self.assertEqual(M.guncelleme_sonucu(
            2, "ERROR: Failed to lock the log file"), M.KILITLI)
        self.assertEqual(M.guncelleme_sonucu(126, ""), M.IPTAL)
        self.assertEqual(M.guncelleme_sonucu(5, "tuhaf"), M.GUNCELLEME_HATASI)

    def test_komut_sabit(self):
        komut = M.guncelleme_komutu()
        self.assertEqual(komut[:3], ["pkexec", "/bin/sh", "-c"])
        self.assertEqual(len(komut), 4)
        self.assertIn("LC_ALL=C", komut[3])
        self.assertTrue(komut[3].rstrip().endswith("freshclam"))


class BellekTesti(unittest.TestCase):
    def test_esik(self):
        self.assertEqual(M.bellek_yeterli("MemAvailable:  4000000 kB\n"),
                         (True, 3906))
        self.assertEqual(M.bellek_yeterli("MemAvailable:   500000 kB\n"),
                         (False, 488))
        self.assertEqual(M.bellek_yeterli("bos"), (True, None))


class HizliTaramaTesti(GeciciEv):
    def test_yollar(self):
        ev = os.path.join(self.kok, "ev")
        os.makedirs(os.path.join(ev, "İndirilenler"))
        os.makedirs(os.path.join(ev, "Masaüstü"))
        os.makedirs(os.path.join(ev, "Belgeler"))
        open(os.path.join(ev, "kurulum.sh"), "w").close()
        os.symlink("/etc/passwd", os.path.join(ev, "bag"))
        eski = os.environ.pop("XDG_CONFIG_HOME", None)
        try:
            yollar = M.hizli_tarama_yollari(ev)
        finally:
            if eski is not None:
                os.environ["XDG_CONFIG_HOME"] = eski
        self.assertEqual(yollar, [os.path.join(ev, "İndirilenler"),
                                  os.path.join(ev, "Masaüstü"),
                                  os.path.join(ev, "kurulum.sh")])

    def test_xdg_dosyasi(self):
        ev = os.path.join(self.kok, "ev2")
        os.makedirs(os.path.join(ev, ".config"))
        os.makedirs(os.path.join(ev, "Indir"))
        with open(os.path.join(ev, ".config", "user-dirs.dirs"), "w") as fh:
            fh.write('XDG_DOWNLOAD_DIR="$HOME/Indir"\nXDG_DESKTOP_DIR="$HOME/"\n')
        os.environ["XDG_CONFIG_HOME"] = os.path.join(ev, ".config")
        try:
            self.assertEqual(M.xdg_dizini("DOWNLOAD", ev), os.path.join(ev, "Indir"))
            self.assertIsNone(M.xdg_dizini("DESKTOP", ev))
        finally:
            os.environ.pop("XDG_CONFIG_HOME", None)


class KarantinaTesti(GeciciEv):
    def test_al_geri_yukle(self):
        yol = self.dosya("ev/kurulum.sh", "zararli", 0o755)
        kod, kayit = M.karantinaya_al(yol, "Test.Imza")
        self.assertEqual(kod, M.TAMAM)
        self.assertFalse(os.path.exists(yol))
        hedef = os.path.join(M.karantina_dizini(), kayit["id"] + ".karantina")
        self.assertEqual(stat.S_IMODE(os.stat(hedef).st_mode), 0o400)
        self.assertEqual(stat.S_IMODE(os.stat(M.karantina_dizini()).st_mode), 0o700)
        self.assertEqual(len(M.karantina_listesi()), 1)

        # Ayni adda yeni bir dosya olusmussa uzerine yazilmaz
        self.dosya("ev/kurulum.sh", "yeni")
        kod, geri = M.geri_yukle(kayit["id"])
        self.assertEqual(kod, M.TAMAM)
        self.assertNotEqual(geri, yol)
        with open(yol) as fh:
            self.assertEqual(fh.read(), "yeni")
        with open(geri) as fh:
            self.assertEqual(fh.read(), "zararli")
        self.assertEqual(stat.S_IMODE(os.stat(geri).st_mode), 0o755)
        self.assertEqual(M.karantina_listesi(), [])

    def test_sil(self):
        yol = self.dosya("ev/a.exe", "z")
        _, kayit = M.karantinaya_al(yol, "X")
        self.assertEqual(M.karantinadan_sil(kayit["id"]), M.TAMAM)
        self.assertEqual(os.listdir(M.karantina_dizini()), ["kayitlar.json"])
        self.assertEqual(M.karantinadan_sil("yok"), M.DOSYA_YOK)

    def test_reddedilenler(self):
        self.assertEqual(M.karantinaya_al(os.path.join(self.kok, "yok"), "X")[0],
                         M.DOSYA_YOK)
        hedef = self.dosya("ev/gercek.txt")
        bag = os.path.join(self.kok, "ev", "bag")
        os.symlink(hedef, bag)
        self.assertEqual(M.karantinaya_al(bag, "X")[0], M.DUZ_DOSYA_DEGIL)
        self.assertTrue(os.path.exists(hedef))
        self.assertEqual(M.karantinaya_al(os.path.join(self.kok, "ev"), "X")[0],
                         M.DUZ_DOSYA_DEGIL)

    def test_klasor_silinmisse(self):
        yol = self.dosya("ev/alt/a.exe", "z")
        _, kayit = M.karantinaya_al(yol, "X")
        os.rmdir(os.path.join(self.kok, "ev", "alt"))
        self.assertEqual(M.geri_yukle(kayit["id"])[0], M.KLASOR_YOK)
        self.assertEqual(len(M.karantina_listesi()), 1)

    def test_dosyayi_sil(self):
        yol = self.dosya("ev/a.exe")
        self.assertEqual(M.dosyayi_sil(yol), M.TAMAM)
        self.assertFalse(os.path.exists(yol))


class GecmisTesti(GeciciEv):
    def test_sinir_ve_sira(self):
        for i in range(M.GECMIS_SINIRI + 5):
            M.gecmise_ekle("hizli", {"taranan": i, "bulgular": [],
                                     "durum": M.TEMIZ}, simdi=1000 + i)
        kayitlar = M.gecmis()
        self.assertEqual(len(kayitlar), M.GECMIS_SINIRI)
        self.assertEqual(kayitlar[0]["taranan"], M.GECMIS_SINIRI + 4)


@unittest.skipUnless(shutil.which("clamscan") and shutil.which("sigtool"),
                     "clamscan/sigtool kurulu degil")
class GercekTaramaTesti(GeciciEv):
    """clamscan'i gecici bir EICAR imzasiyla calistirir."""

    def imzali_motor(self):
        imza_dosyasi = os.path.join(self.kok, "eicar.hdb")
        ornek = self.dosya("imza/eicar.txt", EICAR)
        cikti = subprocess.run(["sigtool", "--md5", ornek], capture_output=True,
                               text=True, check=True).stdout
        with open(imza_dosyasi, "w") as fh:
            fh.write(cikti.replace("eicar.txt", "Eicar-Test-Signature"))
        os.unlink(ornek)
        asil = M.tarama_komutu

        def komut(yollar, haric=()):
            k = asil(yollar, haric)
            return k[:1] + ["-d", imza_dosyasi] + k[1:]
        self.addCleanup(setattr, M, "tarama_komutu", asil)
        M.tarama_komutu = komut

    def test_eicar_bulunur_ve_karantina(self):
        self.imzali_motor()
        self.dosya("hedef/temiz.txt", "merhaba")
        bulasik = self.dosya("hedef/alt klasör/fatura: ocak.pdf.exe", EICAR)
        self.dosya("hedef/-rf", "merhaba")
        satirlar = []
        sonuc = M.Tarama([os.path.join(self.kok, "hedef")],
                         olay=lambda t, v: satirlar.append(t)).calistir()
        self.assertEqual(sonuc["durum"], M.BULGU, sonuc)
        self.assertEqual(sonuc["taranan"], 3)
        self.assertEqual(sonuc["bulgular"], [{"yol": bulasik,
                                              "imza": "Eicar-Test-Signature.UNOFFICIAL"}])
        self.assertIn("bulgu", satirlar)

        kod, kayit = M.karantinaya_al(bulasik, sonuc["bulgular"][0]["imza"])
        self.assertEqual(kod, M.TAMAM)
        # Karantina klasoru taramada atlanir; tekrar tarama temiz cikar
        tekrar = M.Tarama([os.path.join(self.kok, "hedef"), M.veri_dizini()],
                          haric_dizinler=[M.karantina_dizini()]).calistir()
        self.assertEqual(tekrar["durum"], M.TEMIZ, tekrar)
        self.assertEqual(M.geri_yukle(kayit["id"])[0], M.TAMAM)
        self.assertTrue(os.path.exists(bulasik))

    def test_izin_listesi_taramada_uygulanir(self):
        self.imzali_motor()
        bulasik = self.dosya("hedef2/arac.exe", EICAR)
        hedef = os.path.join(self.kok, "hedef2")
        self.assertEqual(M.Tarama([hedef]).calistir()["durum"], M.BULGU)
        self.assertEqual(M.izin_listesine_ekle(bulasik, "X"), M.TAMAM)
        sonuc = M.Tarama([hedef]).calistir()
        self.assertEqual(sonuc["durum"], M.TEMIZ, sonuc)
        self.assertEqual(len(sonuc["izinli"]), 1)
        # Icerik degisirse (yine zararli olsa da parmak izi farkli) bildirilir
        with open(bulasik, "a") as fh:
            fh.write("ek")
        self.dosya("hedef2/kopya.exe", EICAR + "x")
        sonuc = M.Tarama([hedef]).calistir()
        self.assertEqual(sonuc["izinli"], [])

    def test_iptal(self):
        # Ilk satir geldiginde iptal edilir: zamanlamaya bagli degildir
        self.imzali_motor()
        for i in range(400):
            self.dosya(f"cok/{i // 50}/d{i}.txt", "x" * 2000)
        tarama = M.Tarama([os.path.join(self.kok, "cok")],
                          olay=lambda tur, veri: tarama.iptal())
        sonuc = tarama.calistir()
        self.assertEqual(sonuc["durum"], M.IPTAL)

    def test_baslamadan_iptal(self):
        self.imzali_motor()
        self.dosya("tek/a.txt")
        tarama = M.Tarama([os.path.join(self.kok, "tek")])
        tarama.iptal()
        sonuc = tarama.calistir()
        self.assertEqual((sonuc["durum"], sonuc["taranan"]), (M.IPTAL, 0))

    def test_olmayan_yol(self):
        self.imzali_motor()
        sonuc = M.Tarama([os.path.join(self.kok, "yok")]).calistir()
        self.assertEqual(sonuc["durum"], M.TARAMA_HATASI)
        self.assertTrue(sonuc["uyarilar"])


def _uygulamayi_yukle():
    """carotene.py'yi sahte bir gi ile ice alir (GTK gerekmez)."""
    import types
    class _Sinif:
        pass
    gtk = types.SimpleNamespace(Window=_Sinif, Image=_Sinif)
    glib = types.SimpleNamespace(get_user_config_dir=lambda: "/tmp")
    repo = types.SimpleNamespace(Gtk=gtk, Gdk=types.SimpleNamespace(),
                                 GdkPixbuf=types.SimpleNamespace(), GLib=glib,
                                 Pango=types.SimpleNamespace())
    gi = types.ModuleType("gi")
    gi.require_version = lambda *a, **k: None
    gi.repository = repo
    eski = {k: sys.modules.get(k) for k in ("gi", "gi.repository", "tema")}
    sys.modules["gi"], sys.modules["gi.repository"] = gi, repo
    sys.modules["tema"] = types.ModuleType("tema")      # ortak tema GTK ister
    try:
        yol = os.path.join(KOK, "config/includes.chroot/opt/carotos/carotene/carotene.py")
        spec = importlib.util.spec_from_file_location("carotene_test", yol)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul
    finally:
        for k, v in eski.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class UygulamaYapiTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.U = _uygulamayi_yukle()

    def test_metinler_iki_dilli_ve_tutarli(self):
        import re
        for anahtar, sozluk in self.U.METIN.items():
            self.assertEqual(set(sozluk), {"tr", "en"}, anahtar)
            for dil in ("tr", "en"):
                self.assertTrue(sozluk[dil].strip(), anahtar)
            self.assertEqual(set(re.findall(r"\{(\w+)\}", sozluk["tr"])),
                             set(re.findall(r"\{(\w+)\}", sozluk["en"])), anahtar)

    def test_her_kod_icin_metin_var(self):
        for kod in (M.GUNCELLENDI, M.ZATEN_GUNCEL, M.CEVRIMDISI, M.BEKLEME,
                    M.KILITLI, M.IPTAL, M.GUNCELLEME_HATASI):
            self.assertIn("u_" + kod, self.U.METIN)
        for kod in (M.DOSYA_YOK, M.YETKI_YOK, M.DUZ_DOSYA_DEGIL,
                    M.SAHIBI_DEGIL, M.KLASOR_YOK):
            self.assertIn("e_" + kod, self.U.METIN)


class PaketlemeTesti(unittest.TestCase):
    HOOK = os.path.join(KOK, "config/hooks/live/9991-carotos-carotene.hook.chroot")
    DESKTOP = os.path.join(KOK, "config/includes.chroot/usr/share/applications/"
                                "carotos-carotene.desktop")

    def test_hook(self):
        with open(self.HOOK, encoding="utf-8") as fh:
            satirlar = [s.strip() for s in fh if s.strip() and not s.lstrip().startswith("#")]
        kurulum = [s for s in satirlar if "apt-get install" in s]
        self.assertEqual(len(kurulum), 1)
        self.assertTrue(kurulum[0].startswith("LC_ALL=C "))
        self.assertIn("--no-install-recommends", kurulum[0])
        self.assertNotIn("clamav-daemon", kurulum[0])
        self.assertIn("systemctl disable clamav-freshclam.service 2>/dev/null || true",
                      satirlar)
        self.assertTrue(os.access(self.HOOK, os.X_OK))

    def test_desktop(self):
        with open(self.DESKTOP, encoding="utf-8") as fh:
            icerik = fh.read()
        exec_satiri = [s for s in icerik.splitlines() if s.startswith("Exec=")][0]
        hedef = exec_satiri.split("=", 1)[1]
        self.assertEqual(hedef, "/opt/carotos/carotene/carotene.py")
        self.assertTrue(os.path.isfile(os.path.join(KOK, "config/includes.chroot",
                                                    hedef.lstrip("/"))))


class PanelVeSimgeTesti(unittest.TestCase):
    PANEL = os.path.join(KOK, "config/includes.chroot/etc/skel/.config/xfce4/"
                              "xfconf/xfce-perchannel-xml/xfce4-panel.xml")
    BASLATICI = os.path.join(KOK, "config/includes.chroot/etc/skel/.config/xfce4/"
                                  "panel/launcher-27/17870033396.desktop")
    SIMGE_KOK = os.path.join(KOK, "config/includes.chroot/usr/share/icons/hicolor")
    BOYUTLAR = (16, 22, 24, 32, 48, 64, 128, 256)

    def test_ust_panelde(self):
        import xml.etree.ElementTree as ET
        kok = ET.parse(self.PANEL).getroot()
        panel1 = kok.find("./property[@name='panels']/property[@name='panel-1']")
        kimlikler = [v.get("value") for v in
                     panel1.find("./property[@name='plugin-ids']")]
        self.assertIn("27", kimlikler)
        self.assertEqual(kimlikler.count("27"), 1)
        self.assertEqual(kimlikler.index("27"), kimlikler.index("22") + 1)
        eklenti = kok.find("./property[@name='plugins']/property[@name='plugin-27']")
        self.assertEqual(eklenti.get("value"), "launcher")
        self.assertEqual([v.get("value") for v in eklenti.find("./property[@name='items']")],
                         ["17870033396.desktop"])

    def test_baslatici_ve_simge(self):
        with open(self.BASLATICI, encoding="utf-8") as fh:
            icerik = fh.read()
        self.assertIn("Exec=/opt/carotos/carotene/carotene.py\n", icerik)
        self.assertIn("Icon=carotene\n", icerik)
        import struct
        for boyut in self.BOYUTLAR:
            yol = os.path.join(self.SIMGE_KOK, f"{boyut}x{boyut}", "apps", "carotene.png")
            with open(yol, "rb") as fh:
                bas = fh.read(24)
            self.assertEqual(bas[:8], b"\x89PNG\r\n\x1a\n", yol)
            self.assertEqual(struct.unpack(">II", bas[16:24]), (boyut, boyut), yol)
        # SVG yukleyicisi olmayan sistemde panel simgesiz kalmasin
        self.assertFalse(os.path.exists(os.path.join(
            self.SIMGE_KOK, "scalable", "apps", "carotene.svg")))
        with open(PaketlemeTesti.DESKTOP, encoding="utf-8") as fh:
            self.assertIn("Icon=carotene\n", fh.read())


class IzinListesiTesti(GeciciEv):
    def test_ekle_cikar(self):
        yol = self.dosya("ev/arac.exe", "icerik")
        self.assertEqual(M.izin_listesine_ekle(yol, "PUA.Test"), M.TAMAM)
        self.assertEqual(M.izin_listesine_ekle(yol, "PUA.Test"), M.TAMAM)
        self.assertEqual(len(M.izin_listesi()), 1)
        ozet = M.izin_listesi()[0]["sha256"]
        self.assertIn(ozet, M.izin_listesi_ozetleri())
        self.assertEqual(M.izin_listesinden_cikar(ozet), M.TAMAM)
        self.assertEqual(M.izin_listesi(), [])
        self.assertEqual(M.izin_listesinden_cikar(ozet), M.DOSYA_YOK)
        self.assertEqual(M.izin_listesine_ekle(os.path.join(self.kok, "yok"), "X"),
                         M.DOSYA_YOK)


class KomutSatiriTesti(GeciciEv):
    def test_yollar(self):
        a = self.dosya("ev/a b.txt")
        os.makedirs(os.path.join(self.kok, "ev", "klasor"))
        k = os.path.join(self.kok, "ev", "klasor")
        self.assertIsNone(M.komut_satiri_yollari([]))
        self.assertEqual(M.komut_satiri_yollari(["--tara"]), [])
        self.assertEqual(M.komut_satiri_yollari(
            ["--tara", a, "goreli.txt", "/yok/yok", k, a,
             "file://" + k.replace(" ", "%20")]), [a, k])

    def test_thunar_eylemi(self):
        import xml.etree.ElementTree as ET
        yol = os.path.join(KOK, "config/includes.chroot/etc/skel/.config/Thunar/uca.xml")
        kok = ET.parse(yol).getroot()
        komutlar = [a.findtext("command") for a in kok.findall("action")]
        self.assertIn("/opt/carotos/carotene/carotene.py --tara %F", komutlar)
        kimlikler = [a.findtext("unique-id") for a in kok.findall("action")]
        self.assertEqual(len(kimlikler), len(set(kimlikler)))


if __name__ == "__main__":
    unittest.main(verbosity=1)
