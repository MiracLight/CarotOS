#!/usr/bin/env python3
"""Tarama ekibi denetim bulgularinin kalici testleri (T-01..T-05, U-01..U-05,
O-01, O-04; ayrinti: docs/denetim/carotene-magaza.md, usb-saglik.md,
panel-ortak.md).

Kullanim (depo kokunden):  python3 tests/test_tarama_denetim.py
Arayuz testleri icin:      xvfb-run -a python3 tests/test_tarama_denetim.py

Root, ag ve gercek ClamAV gerekmez: clamscan yerine ayni cikti bicimini
ureten sahte bir betik kullanilir. Sinif adlari bulgu numarasini tasir.
"""
import errno
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORTAK = os.path.join(KOK, "config/includes.chroot/opt/carotos/ortak")
MOTOR_YOLU = os.path.join(ORTAK, "tarama_motoru.py")
USB_YOLU = os.path.join(KOK, "config/includes.chroot/opt/carotos/usb/carotos-usb-check.py")
CAROTENE_YOLU = os.path.join(KOK, "config/includes.chroot/opt/carotos/carotene/carotene.py")
EKRAN = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


def _yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M = _yukle("tarama_motoru_denetim", MOTOR_YOLU)


def _usb_sahte_gi():
    glib = types.SimpleNamespace(get_user_config_dir=lambda: "/tmp",
                                 get_home_dir=lambda: "/tmp")
    repo = types.SimpleNamespace(GLib=glib)
    gi = types.ModuleType("gi")
    gi.require_version = lambda *a, **k: None
    gi.repository = repo
    eski = {k: sys.modules.get(k) for k in ("gi", "gi.repository")}
    sys.modules["gi"], sys.modules["gi.repository"] = gi, repo
    try:
        return _yukle("usb_denetim", USB_YOLU)
    finally:
        for k, v in eski.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


U = _usb_sahte_gi()


class GeciciKok(unittest.TestCase):
    """Her test kendi gecici XDG_DATA_HOME'u ile calisir."""

    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="tarama-denetim-")
        eski = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = os.path.join(self.kok, "veri")
        self.addCleanup(self._temizle, eski)

    def _temizle(self, eski):
        if eski is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = eski
        for kok, dizinler, dosyalar in os.walk(self.kok):
            for ad in dizinler + dosyalar:
                try:
                    os.chmod(os.path.join(kok, ad), 0o700, follow_symlinks=False)
                except (OSError, NotImplementedError):
                    pass
        shutil.rmtree(self.kok, ignore_errors=True)

    def dosya(self, ad, icerik="x", mod=0o644):
        yol = os.path.join(self.kok, ad)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as fh:
            fh.write(icerik)
        os.chmod(yol, mod)
        return yol

    def sahte_clamscan(self, cikti, kod=0, oldur=False):
        """clamscan yerine 'cikti'yi yazip 'kod' ile (ya da SIGKILL ile) biten
        betik kurar."""
        veri = os.path.join(self.kok, "sahte-cikti.txt")
        with open(veri, "w", encoding="utf-8", newline="") as fh:
            fh.write(cikti)
        betik = os.path.join(self.kok, "sahte-clamscan")
        with open(betik, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\ncat '%s'\n" % veri)
            fh.write("kill -9 $$\n" if oldur else "exit %d\n" % kod)
        os.chmod(betik, 0o755)
        asil = M.clamscan_yolu
        self.addCleanup(setattr, M, "clamscan_yolu", asil)
        M.clamscan_yolu = lambda: betik
        return betik

    def karantina_kayit_sayisi(self):
        return len(M.karantina_listesi())


# --- T-02 / U-03: basarisiz ya da yarida kalan tarama temiz gorunmez ----------

class T02BasarisizTaramaTemizDegil(GeciciKok):
    def tara(self, *yollar):
        return M.Tarama(list(yollar) or [self.kok]).calistir()

    def test_ciktisiz_olduruldu_yarida(self):
        self.sahte_clamscan("", oldur=True)
        s = self.tara()
        self.assertEqual(s["durum"], M.YARIDA, s)
        self.assertNotEqual(s["durum"], M.TEMIZ)

    def test_bir_dosyadan_sonra_olduruldu_yarida(self):
        a = self.dosya("h/a.txt")
        self.sahte_clamscan(a + ": OK\n", oldur=True)
        s = self.tara()
        self.assertEqual((s["durum"], s["taranan"]), (M.YARIDA, 1))
        self.assertTrue(s["eksik"])

    def test_kod2_ve_taranan_var_kismi(self):
        a = self.dosya("h/a.txt")
        self.sahte_clamscan("LibClamAV Error: Malformed database\n" + a + ": OK\n", kod=2)
        s = self.tara()
        self.assertEqual(s["durum"], M.KISMI, s)
        self.assertTrue(s["uyarilar"])

    def test_kod2_hic_taranmadi_hata(self):
        self.sahte_clamscan("ERROR: Can't open file or directory\n", kod=2)
        self.assertEqual(self.tara()["durum"], M.TARAMA_HATASI)

    def test_kod1_ayristirilamayan_hata(self):
        self.sahte_clamscan("tuhaf satir\n", kod=1)
        self.assertEqual(self.tara()["durum"], M.TARAMA_HATASI)

    def test_beklenmeyen_kod_hata(self):
        a = self.dosya("h/a.txt")
        self.sahte_clamscan(a + ": OK\n", kod=50)
        self.assertEqual(self.tara()["durum"], M.TARAMA_HATASI)

    def test_basarili_temiz(self):
        a = self.dosya("h/a.txt")
        self.sahte_clamscan(a + ": OK\n", kod=0)
        self.assertEqual(self.tara()["durum"], M.TEMIZ)

    def test_kod1_hepsi_izinli_temiz(self):
        a = self.dosya("h/arac.exe", "icerik")
        self.assertEqual(M.izin_listesine_ekle(a, "PUA.X"), M.TAMAM)
        self.sahte_clamscan(a + ": PUA.X FOUND\n", kod=1)
        s = self.tara()
        self.assertEqual((s["durum"], len(s["izinli"])), (M.TEMIZ, 1))

    def test_gecmis_yeni_durumu_saklar(self):
        M.gecmise_ekle("hizli", {"taranan": 3, "bulgular": [], "durum": M.KISMI})
        self.assertEqual(M.gecmis()[0]["durum"], M.KISMI)


class U03UsbYeniDurumlariTanir(unittest.TestCase):
    def test_metinler_var(self):
        for anahtar in ("deep_partial", "deep_aborted", "status_partial", "partial_body"):
            self.assertIn(anahtar, U.UI)
            self.assertTrue(U.UI[anahtar]["en"].strip())

    def test_deep_done_kodu_yeni_durumlari_ayiriyor(self):
        with open(USB_YOLU, encoding="utf-8") as fh:
            kaynak = fh.read()
        self.assertIn("durum == motor.KISMI", kaynak)
        self.assertIn("durum == motor.YARIDA", kaynak)


# --- U-05: bozuk satir taramayi dondurmez -----------------------------------

class U05BozukSatirTakilmaz(GeciciKok):
    def test_satir_coz_bicimsiz(self):
        for satir in ("x: FOUND", ": FOUND", "a:  FOUND"):
            tur, _veri = M.satir_coz(satir)
            self.assertEqual(tur, "uyari", satir)
        self.assertEqual(M.satir_coz("/a/x: Sig FOUND")[0], "bulgu")

    def test_satir_sonlu_ad_ciktisi_istisna_atmaz(self):
        self.sahte_clamscan("/m/a\nx: FOUND\nb: OK\n", kod=1)
        s = M.Tarama([self.kok]).calistir()
        self.assertNotEqual(s["durum"], M.TEMIZ)
        self.assertIsNotNone(s["kod"])

    def test_olay_istisnasi_taramayi_bitirir(self):
        a = self.dosya("h/a.txt")
        self.sahte_clamscan((a + ": OK\n") * 5, kod=0)

        def olay(_tur, _veri):
            raise RuntimeError("arayuz hatasi")
        tarama = M.Tarama([self.kok], olay=olay)
        s = tarama.calistir()
        self.assertEqual(s["durum"], M.TARAMA_HATASI)
        self.assertIsNotNone(tarama.surec.poll())


# --- T-01: bulgu tarama anindaki dosya kimligini tasir ------------------------

class T01DosyaKimligi(GeciciKok):
    def test_satir_sonlu_klasor_temiz_dosyayi_sildirmez(self):
        hedef = os.path.join(self.kok, "Indirilenler")
        os.makedirs(os.path.join(hedef, "x\n"))
        tez = self.dosya("Belgeler/tez.odt", "tez")
        self.sahte_clamscan(hedef + "/x\n" + tez + ": Eicar-Signature FOUND\n", kod=1)
        s = M.Tarama([hedef]).calistir()
        self.assertEqual(s["durum"], M.BULGU)
        bulgu = s["bulgular"][0]
        self.assertEqual(bulgu["yol"], tez)
        self.assertTrue(s["satir_sonlu_ad"])
        self.assertIsNone(bulgu["kimlik"])
        self.assertEqual(M.dosyayi_sil(bulgu["yol"], bulgu["kimlik"]), M.DOGRULANAMADI)
        self.assertEqual(M.karantinaya_al(bulgu["yol"], bulgu["imza"], bulgu["kimlik"])[0],
                         M.DOGRULANAMADI)
        self.assertEqual(M.izin_listesine_ekle(bulgu["yol"], "X", bulgu["kimlik"]),
                         M.DOGRULANAMADI)
        self.assertTrue(os.path.exists(tez))

    def test_kok_disindaki_yol_dogrulanamaz(self):
        hedef = os.path.join(self.kok, "A")
        os.makedirs(hedef)
        baska = self.dosya("B/onemli.txt")
        self.sahte_clamscan(baska + ": Sig FOUND\n", kod=1)
        s = M.Tarama([hedef]).calistir()
        self.assertIsNone(s["bulgular"][0]["kimlik"])

    def test_degisen_dosyaya_islem_yapilmaz(self):
        zararli = self.dosya("h/zararli.exe", "z")
        self.sahte_clamscan(zararli + ": Sig FOUND\n", kod=1)
        bulgu = M.Tarama([os.path.join(self.kok, "h")]).calistir()["bulgular"][0]
        self.assertIsNotNone(bulgu["kimlik"])
        os.unlink(zararli)
        self.dosya("h/zararli.exe", "baska ve temiz bir dosya")
        self.assertEqual(M.dosyayi_sil(zararli, bulgu["kimlik"]), M.DOSYA_DEGISTI)
        self.assertEqual(M.karantinaya_al(zararli, "Sig", bulgu["kimlik"])[0],
                         M.DOSYA_DEGISTI)
        self.assertEqual(M.izin_listesine_ekle(zararli, "Sig", bulgu["kimlik"]),
                         M.DOSYA_DEGISTI)
        self.assertTrue(os.path.exists(zararli))
        self.assertEqual(self.karantina_kayit_sayisi(), 0)

    def test_degismeyen_dosya_islenir(self):
        a = self.dosya("h/a.exe", "z")
        b = self.dosya("h/b.exe", "y")
        self.sahte_clamscan(a + ": S FOUND\n" + b + ": S FOUND\n", kod=1)
        bulgular = M.Tarama([os.path.join(self.kok, "h")]).calistir()["bulgular"]
        self.assertEqual(M.karantinaya_al(a, "S", bulgular[0]["kimlik"])[0], M.TAMAM)
        self.assertEqual(M.dosyayi_sil(b, bulgular[1]["kimlik"]), M.TAMAM)
        self.assertFalse(os.path.exists(a) or os.path.exists(b))

    def test_sembolik_bag_reddedilir(self):
        hedef = self.dosya("h/gercek.txt")
        bag = os.path.join(self.kok, "h", "bag")
        os.symlink(hedef, bag)
        self.assertEqual(M.dosyayi_sil(bag), M.DUZ_DOSYA_DEGIL)
        self.assertTrue(os.path.exists(hedef))

    def test_karantinada_degistirilen_dosya_geri_yuklenmez(self):
        yol = self.dosya("h/k.exe", "zararli")
        kod, kayit = M.karantinaya_al(yol, "S")
        self.assertEqual(kod, M.TAMAM)
        karantina = os.path.join(M.karantina_dizini(), kayit["id"] + ".karantina")
        os.chmod(karantina, 0o600)
        with open(karantina, "a") as fh:
            fh.write("degisti")
        self.assertEqual(M.geri_yukle(kayit["id"])[0], M.DOSYA_DEGISTI)
        self.assertFalse(os.path.exists(yol))
        self.assertEqual(self.karantina_kayit_sayisi(), 1)


# --- T-03 / O-01: root komutu kullanicinin PATH'inden bulunmaz --------------

class T03GuncellemeKomutuPathBagimsiz(GeciciKok):
    def test_path_basindaki_sahte_programlar_kullanilmaz(self):
        sahte = os.path.join(self.kok, "a;touch ENJEKTE;b")
        os.makedirs(sahte)
        for ad in ("freshclam", "pkexec", "env", "sh"):
            yol = os.path.join(sahte, ad)
            with open(yol, "w") as fh:
                fh.write("#!/bin/sh\n")
            os.chmod(yol, 0o755)
        with mock.patch.dict(os.environ, {"PATH": sahte + os.pathsep + os.environ.get("PATH", "")}):
            komut = M.guncelleme_komutu()
            freshclam = M.freshclam_yolu()
        self.assertFalse(freshclam and freshclam.startswith(self.kok))
        if komut is None:
            return          # bu makinede pkexec/freshclam yok: komut hic kurulmaz
        self.assertNotIn("/bin/sh", komut)
        self.assertNotIn("-c", komut)
        for parca in komut:
            self.assertNotIn(self.kok, parca)
        for program in (komut[0], komut[1], komut[-1]):
            self.assertTrue(program.startswith(("/usr/sbin/", "/usr/bin/", "/sbin/", "/bin/")),
                            program)

    def test_program_yoksa_komut_yok(self):
        asil = M.sistem_yolu
        self.addCleanup(setattr, M, "sistem_yolu", asil)
        M.sistem_yolu = lambda ad: None if ad == "freshclam" else "/usr/bin/" + ad
        self.assertIsNone(M.guncelleme_komutu())


# --- T-04 / O-04: kayit defteri kirilgan degil ------------------------------

class T04KayitDefteri(GeciciKok):
    def test_bozuk_defter_kenara_alinir_ezilmez(self):
        yol = self.dosya("ev/a.exe", "z")
        os.makedirs(M.karantina_dizini(), mode=0o700)
        with open(os.path.join(M.karantina_dizini(), "kayitlar.json"), "w") as fh:
            fh.write('[{"id": "bozuk"')
        self.assertEqual(M.karantina_listesi(), [])
        kod, _kayit = M.karantinaya_al(yol, "X")
        self.assertEqual(kod, M.TAMAM)
        yedekler = [a for a in os.listdir(M.karantina_dizini()) if ".bozuk-" in a]
        self.assertEqual(len(yedekler), 1)
        with open(os.path.join(M.karantina_dizini(), yedekler[0])) as fh:
            self.assertEqual(fh.read(), '[{"id": "bozuk"')
        self.assertEqual(self.karantina_kayit_sayisi(), 1)

    def test_gecersiz_ogeler_listeyi_bozmaz(self):
        os.makedirs(M.karantina_dizini(), mode=0o700)
        gecerli = {"id": "a" * 32, "asil_yol": "/home/u/x.exe", "tarih": 5,
                   "imza": "S", "sha256": "", "mod": 420}
        with open(os.path.join(M.karantina_dizini(), "kayitlar.json"), "w") as fh:
            json.dump([5, "metin", {"id": "b" * 32}, {"asil_yol": "/x", "tarih": 1},
                       {"id": "../../x", "asil_yol": "/x", "tarih": 1}, gecerli], fh)
        self.assertEqual(M.karantina_listesi(), [gecerli])
        self.assertEqual(M.geri_yukle("b" * 32)[0], M.DOSYA_YOK)
        self.assertEqual(M.karantinadan_sil("../../x"), M.DOSYA_YOK)

    def test_izin_ve_gecmis_bozuk_ogede_cokmez(self):
        os.makedirs(M.veri_dizini(), mode=0o700)
        with open(os.path.join(M.veri_dizini(), "izin_listesi.json"), "w") as fh:
            json.dump([1, None, {"sha256": 3}], fh)
        with open(os.path.join(M.veri_dizini(), "gecmis.json"), "w") as fh:
            fh.write("{bozuk")
        self.assertEqual(M.izin_listesi_ozetleri(), set())
        self.assertEqual(M.gecmis(), [])
        M.gecmise_ekle("hizli", {"taranan": 1, "bulgular": [], "durum": M.TEMIZ})
        self.assertEqual(len(M.gecmis()), 1)
        self.assertTrue(any(".bozuk-" in a for a in os.listdir(M.veri_dizini())))

    def test_kayitsiz_dosya_listelenir_ve_silinir(self):
        dizin = M._gizli_dizin(M.karantina_dizini())
        kimlik = "c" * 32
        yetim = os.path.join(dizin, kimlik + ".karantina")
        with open(yetim, "w") as fh:
            fh.write("z")
        os.chmod(yetim, 0o400)
        self.assertEqual(M.kayitsiz_karantina_dosyalari(), [kimlik])
        self.assertEqual(M.karantinadan_sil(kimlik), M.TAMAM)
        self.assertFalse(os.path.exists(yetim))
        self.assertEqual(M.kayitsiz_karantina_dosyalari(), [])

    def test_kayit_yazilamazsa_dosya_yerinde_kalir(self):
        yol = self.dosya("ev/a.exe", "z")

        def yazilamaz(_kayitlar):
            raise OSError(errno.ENOSPC, "No space left on device")
        with mock.patch.object(M, "_kayitlari_yaz", yazilamaz):
            kod, kayit = M.karantinaya_al(yol, "X")
        self.assertEqual((kod, kayit), (M.KAYIT_HATASI, None))
        self.assertTrue(os.path.exists(yol))
        self.assertEqual(M.kayitsiz_karantina_dosyalari(), [])

    @unittest.skipIf(ROOT, "root izin denetimlerini asar")
    def test_tasima_basarisizsa_kayit_geri_alinir(self):
        yol = self.dosya("salt/a.sh", "z", 0o755)
        os.chmod(os.path.dirname(yol), 0o555)
        kod, _ = M.karantinaya_al(yol, "X")
        self.assertNotEqual(kod, M.TAMAM)
        self.assertEqual(self.karantina_kayit_sayisi(), 0)
        self.assertEqual([a for a in os.listdir(M.karantina_dizini())
                          if a.endswith(".karantina")], [])
        self.assertTrue(os.path.exists(yol))

    def test_yazma_atomik_ve_gizli(self):
        yol = self.dosya("ev/a.exe", "z")
        M.karantinaya_al(yol, "X")
        defter = os.path.join(M.karantina_dizini(), "kayitlar.json")
        self.assertEqual(stat.S_IMODE(os.stat(defter).st_mode), 0o600)
        self.assertEqual([a for a in os.listdir(M.karantina_dizini()) if a.endswith(".yeni")], [])


# --- T-05: basarisiz karantina calistirilabilir kopya birakmaz ---------------

class T05BasarisizKarantinaKopyaBirakmaz(GeciciKok):
    def exdev(self, *_a, **_k):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    @unittest.skipIf(ROOT, "root izin denetimlerini asar")
    def test_kaynak_silinemezse_kopya_temizlenir(self):
        yol = self.dosya("usb/kur.sh", "zararli", 0o755)
        os.chmod(os.path.dirname(yol), 0o555)
        with mock.patch.object(M.os, "rename", self.exdev):
            kod, kayit = M.karantinaya_al(yol, "X")
        self.assertEqual((kod, kayit), (M.KAYNAK_SILINEMEDI, None))
        self.assertTrue(os.path.exists(yol))
        self.assertEqual([a for a in os.listdir(M.karantina_dizini())
                          if a.endswith(".karantina")], [])
        self.assertEqual(self.karantina_kayit_sayisi(), 0)

    def test_baska_bolumden_kopya_calistirilamaz(self):
        yol = self.dosya("usb/kur.sh", "zararli", 0o755)
        with mock.patch.object(M.os, "rename", self.exdev):
            kod, kayit = M.karantinaya_al(yol, "X")
        self.assertEqual(kod, M.TAMAM)
        hedef = os.path.join(M.karantina_dizini(), kayit["id"] + ".karantina")
        self.assertEqual(stat.S_IMODE(os.stat(hedef).st_mode), 0o400)
        self.assertFalse(os.path.exists(yol))
        self.assertEqual(kayit["mod"], 0o755)

    def test_yer_yoksa_kopya_temizlenir(self):
        yol = self.dosya("usb/kur.sh", "zararli", 0o755)
        asil_write = os.write

        def dolu(fd, veri):
            if veri:
                raise OSError(errno.ENOSPC, "No space left on device")
            return asil_write(fd, veri)
        with mock.patch.object(M.os, "rename", self.exdev), \
                mock.patch.object(M.os, "write", dolu):
            kod, _ = M.karantinaya_al(yol, "X")
        self.assertEqual(kod, M.YER_YOK)
        self.assertTrue(os.path.exists(yol))
        self.assertEqual([a for a in os.listdir(M.karantina_dizini())
                          if a.endswith(".karantina")], [])

    def test_geri_yukleme_var_olan_dosyayi_ezmez(self):
        yol = self.dosya("ev/a.txt", "zararli")
        _, kayit = M.karantinaya_al(yol, "X")
        self.dosya("ev/a.txt", "yeni")
        kod, geri = M.geri_yukle(kayit["id"])
        self.assertEqual(kod, M.TAMAM)
        with open(yol) as fh:
            self.assertEqual(fh.read(), "yeni")
        with open(geri) as fh:
            self.assertEqual(fh.read(), "zararli")


# --- U-01: canli ortam taninmasi bellek icerigiyle atlatilamaz ---------------

class U01CanliOrtamAtlatilamaz(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="usb-u01-")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.bellek = os.path.join(self.kok, "BELLEK")
        os.makedirs(os.path.join(self.bellek, ".disk"))
        os.makedirs(os.path.join(self.bellek, "live"))
        for ad in (".disk/info", "live/vmlinuz", "live/filesystem.squashfs", "autorun.inf"):
            open(os.path.join(self.bellek, ad), "w").close()

    def bagla(self, girdiler, cmdline):
        yamalar = [mock.patch.object(U, "mount_entries", lambda: girdiler),
                   mock.patch.object(U, "is_removable", lambda _d: True),
                   mock.patch.object(U, "kernel_cmdline", lambda: cmdline),
                   mock.patch.object(U, "MOUNT_PREFIXES", (self.kok + "/",))]
        for y in yamalar:
            y.start()
            self.addCleanup(y.stop)
        return U.removable_mounts()

    def test_isaret_dosyalari_taramayi_atlatmaz(self):
        girdi = {"device": "/dev/sdz1", "mount": self.bellek, "fstype": "vfat"}
        self.assertEqual(self.bagla([girdi], "boot=live quiet"), [girdi])
        self.assertEqual(self.bagla([girdi], "quiet"), [girdi])

    def test_gercek_acilis_ortami_atlanir(self):
        ortam = {"device": "/dev/sdz1", "mount": "/run/live/medium", "fstype": "iso9660"}
        ayni = {"device": "/dev/sdz1", "mount": self.bellek, "fstype": "vfat"}
        baska = {"device": "/dev/sdy1", "mount": self.kok + "/BASKA", "fstype": "vfat"}
        self.assertEqual(self.bagla([ortam, ayni, baska], "boot=live"), [baska])

    def test_live_media_parametresi(self):
        self.assertEqual(U.live_medium_devices([], "boot=live live-media=/dev/sdq2"),
                         {os.path.realpath("/dev/sdq2")})
        self.assertEqual(U.live_medium_devices([], "live-media=/dev/sdq2"), set())


# --- U-02: kapsam disi kalanlar "temiz" gorunmez ----------------------------

class U02KapsamDisiTemizDegil(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="usb-u02-")
        self.addCleanup(shutil.rmtree, self.kok, True)

    def dosya(self, ad):
        yol = os.path.join(self.kok, ad)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        open(yol, "w").close()
        return yol

    def test_usb_uzerindeki_iso_udf_taranir(self):
        with mock.patch.object(U, "read_file", lambda _p, limit=0: ""):
            self.assertFalse(U.is_optical_drive("/dev/sdz1"))
            self.assertTrue(U.is_optical_drive("/dev/sr0"))
        girdiler = [{"device": "/dev/sdz1", "mount": self.kok + "/ISO", "fstype": "udf"},
                    {"device": "/dev/sr0", "mount": self.kok + "/CD", "fstype": "iso9660"}]
        with mock.patch.object(U, "mount_entries", lambda: girdiler), \
                mock.patch.object(U, "is_removable", lambda _d: True), \
                mock.patch.object(U, "kernel_cmdline", lambda: ""), \
                mock.patch.object(U, "MOUNT_PREFIXES", (self.kok + "/",)):
            self.assertEqual([e["device"] for e in U.removable_mounts()], ["/dev/sdz1"])

    def test_sistem_klasorleri_taranir(self):
        self.dosya("$RECYCLE.BIN/a.pdf.exe")
        self.dosya("System Volume Information/autorun.inf")
        self.dosya(".Trash-1000/files/kur.exe")
        sonuc = U.scan_path(self.kok)
        turler = {b["kind"] for b in sonuc["findings"]}
        self.assertIn("double_ext", turler)
        self.assertIn("system_exec", turler)
        self.assertNotIn("hidden_dirs", turler)

    def test_derinlik_siniri_eksik_sayilir(self):
        self.dosya("/".join("d%d" % i for i in range(9)) + "/evil.pdf.exe")
        self.assertTrue(U.scan_path(self.kok)["stats"]["truncated"])

    def test_sinirli_denetim_temiz_bildirilmez(self):
        sonuc = {"findings": [], "label": "<b>X</b>", "stats": {"truncated": True}}
        with mock.patch.object(U, "_notify_araclari", lambda: False), \
                mock.patch.object(U.subprocess, "Popen") as popen:
            U.send_notification(sonuc, {"lang": "en"})
        argv = popen.call_args[0][0]
        self.assertIn("--", argv)
        govde = argv[-1]
        self.assertIn("could not be checked", govde)
        self.assertNotIn("<b>", govde)
        self.assertIn("&lt;b&gt;", govde)


# --- U-04: UTF-8 olmayan ve denetim karakterli adlar ------------------------

class U04GecersizAdlar(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="usb-u04-")
        self.addCleanup(shutil.rmtree, self.kok, True)
        try:
            open(os.path.join(os.fsencode(self.kok), b"autorun\xff.pdf.exe"), "w").close()
            open(os.path.join(self.kok, "a\n[HIGH] Temiz.pdf.exe"), "w").close()
        except (OSError, UnicodeError):
            self.skipTest("dosya sistemi ham bayt/satir sonu adlarina izin vermiyor")

    def test_rapor_ve_json_uretilir(self):
        sonuc = U.enrich(U.scan_path(self.kok), self.kok)
        self.assertEqual(len([b for b in sonuc["findings"] if b["kind"] == "double_ext"]), 2)
        rapor = U.build_report(sonuc, "en")
        rapor.encode("utf-8")
        self.assertIn("autorun\\xff.pdf.exe", rapor)
        self.assertNotIn("\n[HIGH] Temiz", rapor)
        self.assertIn("a\\x0a[HIGH] Temiz", rapor)
        json.dumps(U.guvenli_veri(sonuc), ensure_ascii=False).encode("utf-8")
        # bulgudaki gercek yol degismez (Konumu ac icin)
        self.assertTrue(any(os.path.exists(b["path"]) for b in sonuc["findings"]))

    def test_guvenli_metin(self):
        self.assertEqual(U.guvenli_metin("a‮b"), "a\\u202eb")
        self.assertEqual(U.guvenli_metin("düz metin"), "düz metin")
        self.assertEqual(U.guvenli_metin(os.fsdecode(b"x\xffy")), "x\\xffy")


# --- Arayuz: Carotene ve USB Denetimi yeni durumlari gosterir ----------------

@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class T02ArayuzEksikTaramaTemizDegil(GeciciKok):
    @classmethod
    def setUpClass(cls):
        cls.ayar = tempfile.mkdtemp(prefix="tarama-denetim-ayar-")
        os.environ["XDG_CONFIG_HOME"] = cls.ayar
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            raise unittest.SkipTest("GTK yok")
        cls.Gtk = Gtk
        cls.C = _yukle("carotene_denetim", CAROTENE_YOLU)
        cls.Uu = _yukle("usb_denetim_gtk", USB_YOLU)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ayar, ignore_errors=True)

    def sonuc(self, durum, **ek):
        s = {"taranan": 2, "atlanan": 1, "bulgular": [], "uyarilar": ["LibClamAV Error: x"],
             "izinli": [], "kod": 2, "durum": durum, "sure": 0.1, "yollar": [self.kok]}
        s.update(ek)
        return s

    def test_carotene_kismi_ve_yarida(self):
        C = self.C
        pencere = C.CaroteneWindow({"lang": "en", "theme": "dark"})
        for durum, anahtar in ((C.M.KISMI, "res_partial_title"),
                               (C.M.YARIDA, "res_aborted_title")):
            tarama = object()
            pencere.tarama = tarama
            pencere.tarama_turu = "hizli"
            pencere.scan_done(tarama, self.sonuc(durum))
            self.assertEqual(pencere.hap_durum[0], anahtar)
            self.assertEqual(C.M.gecmis()[0]["durum"], durum)
        pencere.show_page("history")
        pencere.show_page("quarantine")

    def test_carotene_kayitsiz_dosya_sayfasi(self):
        C = self.C
        dizin = C.M._gizli_dizin(C.M.karantina_dizini())
        with open(os.path.join(dizin, "d" * 32 + ".karantina"), "w") as fh:
            fh.write("z")
        pencere = C.CaroteneWindow({"lang": "en", "theme": "dark"})
        pencere.show_page("quarantine")
        self.assertEqual(C.M.kayitsiz_karantina_dosyalari(), ["d" * 32])

    def test_usb_kismi_temiz_degil(self):
        RW = self.Uu._gtk_araclari()
        sonuc = {"findings": [], "stats": {"files": 1, "dirs": 0, "size": 0, "seconds": 0,
                                           "truncated": False, "empty": False},
                 "root": self.kok, "label": "X", "device": None, "fstype": None}
        pencere = RW(sonuc, {"lang": "en", "theme": "dark"})
        self.addCleanup(pencere.destroy)
        motor = self.Uu.tarama_motoru()
        for durum, beklenen in ((motor.KISMI, "kismi"), (motor.YARIDA, "yarida")):
            tarama = object()
            pencere.tarama = tarama
            pencere._deep_done(tarama, self.sonuc(durum))
            self.assertEqual(pencere.deep["durum"], beklenen)
        pencere.result["stats"]["truncated"] = True
        pencere._hap_guncelle()

    def test_usb_gecersiz_adli_kart(self):
        RW = self.Uu._gtk_araclari()
        yol = os.fsdecode(b"/media/u/autorun\xff.pdf.exe")
        sonuc = {"findings": [{"level": "high", "kind": "double_ext", "path": yol,
                               "title": {"tr": "t", "en": "t"},
                               "detail": {"tr": yol, "en": yol}}],
                 "stats": {"files": 1, "dirs": 0, "size": 0, "seconds": 0,
                           "truncated": False, "empty": False},
                 "root": self.kok, "label": "X", "device": None, "fstype": None}
        pencere = RW(sonuc, {"lang": "en", "theme": "dark"})
        self.addCleanup(pencere.destroy)


if __name__ == "__main__":
    unittest.main(verbosity=1)
