#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CarotOS Kurtarma: motor testleri (GTK'siz, subprocess sahte).

Calistirma (depo kokunden):  python3 tests/test_kurtarma_motor.py
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos", "kurtarma", "kurtarma_motor.py")

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("kurtarma_motor", MOD)
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)


class SahteCalistir:
    """Her cagriyi kaydeder; komut[0]'a gore sabit (kod, cikti) dondurur."""

    def __init__(self, varsayilan=(0, "")):
        self.cagrilar = []
        self.varsayilan = varsayilan
        self.yanitlar = {}   # komut[0] -> (kod, cikti) ya da fonksiyon(komut)->(kod,cikti)

    def __call__(self, komut, zaman=120):
        self.cagrilar.append(list(komut))
        yanit = self.yanitlar.get(komut[0], self.varsayilan)
        if callable(yanit):
            return yanit(komut)
        return yanit


class GeciciDizin(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="kurtarma-test-")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.noktalar = os.path.join(self.kok, "noktalar")

    def meta_yaz(self, nokta_id, **ek):
        d = os.path.join(self.noktalar, nokta_id)
        os.makedirs(d, exist_ok=True)
        meta = {"id": nokta_id, "olusturma": "2026-01-01T00:00:00", "etiket": "", "tetikleyici": "elle",
               "parcalar": [], "boyut_mb": 1, "surum": "1.4"}
        meta.update(ek)
        with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh)
        return meta


class KucukYardimcilar(GeciciDizin):
    def test_id_bicimi_siralanabilir(self):
        a = K.simdi_id(datetime.datetime(2026, 1, 2, 3, 4, 5))
        b = K.simdi_id(datetime.datetime(2026, 1, 2, 3, 5, 0))
        self.assertTrue(K.id_gecerli_mi(a))
        self.assertLess(a, b)

    def test_id_gecersiz_degerler(self):
        for kotu in ("", "abc", "2026-01-02", "../../etc", "20260102-030405x"):
            self.assertFalse(K.id_gecerli_mi(kotu), kotu)

    def test_etiket_gecerli_ve_gecersiz(self):
        for iyi in ("Güncelleme öncesi", "a", "A-Z_0.9 ğüşıöç", "x" * 60):
            self.assertTrue(K.etiket_gecerli_mi(iyi), iyi)
        for kotu in ("", "x" * 61, "../x", "a;b", "a\nb", "a/b"):
            self.assertFalse(K.etiket_gecerli_mi(kotu), kotu)

    def test_ayarlar_varsayilan_ve_yaz_oku_dongusu(self):
        yol = os.path.join(self.kok, "ayarlar.json")
        self.assertEqual(K.ayarlari_oku(yol), K.VARSAYILAN_AYAR)
        yeni = K.ayarlari_yaz({"sakla": 3, "oto_guncelleme_oncesi": False, "fazladan": "yoksayilir"}, yol)
        self.assertEqual(yeni["sakla"], 3)
        self.assertFalse(yeni["oto_guncelleme_oncesi"])
        self.assertNotIn("fazladan", yeni)
        geri = K.ayarlari_oku(yol)
        self.assertEqual(geri["sakla"], 3)
        self.assertEqual(geri["min_bos_mb"], K.VARSAYILAN_AYAR["min_bos_mb"])  # dokunulmayan deger korunur

    def test_ayarlar_dosyasi_dunya_okunabilir(self):
        yol = os.path.join(self.kok, "ayarlar.json")
        K.ayarlari_yaz({"sakla": 2}, yol)
        self.assertEqual(os.stat(yol).st_mode & 0o777, 0o644)

    def test_ayarlar_bozuk_dosyada_varsayilana_duser(self):
        yol = os.path.join(self.kok, "bozuk.json")
        with open(yol, "w") as fh:
            fh.write("{bozuk")
        self.assertEqual(K.ayarlari_oku(yol), K.VARSAYILAN_AYAR)

    def test_ayarlar_yanlis_tur_yoksayilir(self):
        yol = os.path.join(self.kok, "ayarlar.json")
        with open(yol, "w") as fh:
            json.dump({"sakla": "bes"}, fh)   # int beklenirken metin
        self.assertEqual(K.ayarlari_oku(yol)["sakla"], K.VARSAYILAN_AYAR["sakla"])

    def test_canli_sistem_tespiti(self):
        canli = os.path.join(self.kok, "cmdline-canli")
        with open(canli, "w") as fh:
            fh.write("BOOT_IMAGE=/vmlinuz boot=live quiet splash")
        kurulu = os.path.join(self.kok, "cmdline-kurulu")
        with open(kurulu, "w") as fh:
            fh.write("BOOT_IMAGE=/vmlinuz root=UUID=xyz ro quiet")
        self.assertTrue(K.canli_sistem_mi(canli))
        self.assertFalse(K.canli_sistem_mi(kurulu))
        self.assertFalse(K.canli_sistem_mi(os.path.join(self.kok, "yok")))

    def test_surum_oku(self):
        yol = os.path.join(self.kok, "os-release")
        with open(yol, "w") as fh:
            fh.write('PRETTY_NAME="CarotOS 1.4"\nVERSION="1.4 (Eggshell)"\n')
        self.assertEqual(K.surum_oku(yol), "1.4 (Eggshell)")
        self.assertEqual(K.surum_oku(os.path.join(self.kok, "yok")), "?")

    def test_bos_alan_yeterli_mi_esik(self):
        import collections
        Kullanim = collections.namedtuple("Kullanim", "total used free")
        az = lambda _d: Kullanim(0, 0, 100 * 1024 * 1024)
        cok = lambda _d: Kullanim(0, 0, 10 * 1024 * 1024 * 1024)
        self.assertFalse(K.bos_alan_yeterli_mi(self.kok, 512, az))
        self.assertTrue(K.bos_alan_yeterli_mi(self.kok, 512, cok))

    def test_bos_alan_olculemezse_engel_olmaz(self):
        def patlar(_d):
            raise OSError("olcum yok")
        self.assertTrue(K.bos_alan_yeterli_mi(self.kok, 999999, patlar))

    def test_bos_alan_var_olmayan_dizin_ustune_cikar(self):
        kaydedilen = []

        def kaydet(d):
            kaydedilen.append(d)
            import collections
            return collections.namedtuple("U", "total used free")(0, 0, 10**12)

        derin = os.path.join(self.kok, "a", "b", "c")
        self.assertTrue(K.bos_alan_yeterli_mi(derin, 1, kaydet))
        self.assertEqual(kaydedilen[-1], self.kok)   # var olan ilk ustadan olculur


class NoktaListesi(GeciciDizin):
    def test_bos_dizinde_bos_liste(self):
        self.assertEqual(K.noktalari_listele(self.noktalar), [])
        self.assertEqual(K.noktalari_listele(os.path.join(self.kok, "hic-yok")), [])

    def test_en_yeni_once(self):
        self.meta_yaz("20260101-000000")
        self.meta_yaz("20260103-000000")
        self.meta_yaz("20260102-000000")
        ids = [m["id"] for m in K.noktalari_listele(self.noktalar)]
        self.assertEqual(ids, ["20260103-000000", "20260102-000000", "20260101-000000"])

    def test_bozuk_veya_eslesmeyen_meta_atlanir(self):
        self.meta_yaz("20260101-000000")
        # id klasor adiyla uyusmuyor -> atlanir
        self.meta_yaz("20260102-000000", id="baska-id")
        # gecersiz klasor adi (nokta_olustur disinda biri birakmis olabilir) -> atlanir
        kotu = os.path.join(self.noktalar, "gecersiz-ad")
        os.makedirs(kotu)
        with open(os.path.join(kotu, "meta.json"), "w") as fh:
            fh.write("{bozuk json")
        sonuc = K.noktalari_listele(self.noktalar)
        self.assertEqual([m["id"] for m in sonuc], ["20260101-000000"])

    def test_nokta_oku(self):
        self.meta_yaz("20260101-000000", etiket="deneme")
        self.assertEqual(K.nokta_oku("20260101-000000", self.noktalar)["etiket"], "deneme")
        self.assertIsNone(K.nokta_oku("20260102-000000", self.noktalar))
        self.assertIsNone(K.nokta_oku("../../etc", self.noktalar))

    def test_son_nokta_zamani_tetikleyiciye_gore(self):
        self.meta_yaz("20260101-000000", tetikleyici="elle", olusturma="2026-01-01T00:00:00")
        self.meta_yaz("20260102-000000", tetikleyici="oto", olusturma="2026-01-02T00:00:00")
        self.assertEqual(K.son_nokta_zamani(None, self.noktalar), "2026-01-02T00:00:00")
        self.assertEqual(K.son_nokta_zamani("elle", self.noktalar), "2026-01-01T00:00:00")
        self.assertIsNone(K.son_nokta_zamani("elle", os.path.join(self.kok, "bos")))

    def test_aralik_doldu_mu(self):
        simdi = datetime.datetime(2026, 1, 1, 12, 0, 0)
        self.meta_yaz("20260101-115500", tetikleyici="oto", olusturma="2026-01-01T11:55:00")
        self.assertFalse(K.aralik_doldu_mu("oto", 10, self.noktalar, simdi))   # 5 dk once
        self.assertTrue(K.aralik_doldu_mu("oto", 3, self.noktalar, simdi))     # 5 dk >= 3 dk
        self.assertTrue(K.aralik_doldu_mu("oto", 10, os.path.join(self.kok, "bos"), simdi))  # hic yok


class RsyncKomutlari(unittest.TestCase):
    def test_olustur_link_dest_yoksa_eklenmez(self):
        komut = K.rsync_olustur_komutu("/etc", "/hedef")
        self.assertNotIn("--link-dest", komut)
        self.assertNotIn("--delete", komut)
        self.assertEqual(komut[-2:], ["/etc/", "/hedef"])

    def test_olustur_link_dest_var_olan_dizinde_eklenir(self):
        with tempfile.TemporaryDirectory() as d:
            komut = K.rsync_olustur_komutu("/etc", "/hedef", onceki_dizin=d)
            self.assertIn("--link-dest", komut)
            self.assertEqual(komut[komut.index("--link-dest") + 1], d)

    def test_olustur_link_dest_olmayan_dizin_eklenmez(self):
        komut = K.rsync_olustur_komutu("/etc", "/hedef", onceki_dizin="/boyle/bir/yer/yok")
        self.assertNotIn("--link-dest", komut)

    def test_geri_yukle_delete_icerir(self):
        komut = K.rsync_geri_yukle_komutu("/nokta/etc", "/etc")
        self.assertIn("--delete", komut)
        self.assertNotIn("--link-dest", komut)
        self.assertEqual(komut[-2:], ["/nokta/etc/", "/etc"])

    def test_haric_desenleri_komutta(self):
        komut = K.rsync_olustur_komutu("/root", "/hedef", haric=("Cache", "*.sock"))
        self.assertEqual(komut.count("--exclude"), 2)
        self.assertIn("Cache", komut)
        self.assertIn("*.sock", komut)

    def test_kaynak_sondaki_egik_cizgi_tekillesir(self):
        komut = K.rsync_olustur_komutu("/etc/", "/hedef")
        self.assertEqual(komut[-2], "/etc/")


class PaketKumeleri(unittest.TestCase):
    ESKI = "paket-a\tinstall\npaket-b\tinstall\npaket-sil\tdeinstall\n"
    YENI = "paket-a\tinstall\npaket-c\tinstall\n"

    def test_kume_yalniz_install_satirlari(self):
        self.assertEqual(K.paket_kumesi(self.ESKI), {"paket-a", "paket-b"})
        self.assertEqual(K.paket_kumesi(""), set())
        self.assertEqual(K.paket_kumesi("tek-kelime\n"), set())

    def test_eksik_paketler_siralı_ve_farkla_sinirlı(self):
        self.assertEqual(K.eksik_paketler(self.ESKI, self.YENI), ["paket-b"])
        self.assertEqual(K.eksik_paketler(self.ESKI, self.ESKI), [])
        self.assertEqual(K.eksik_paketler("", self.YENI), [])


class NoktaOlustur(GeciciDizin):
    def ayar(self, **ek):
        a = dict(K.VARSAYILAN_AYAR)
        a.update(ek)
        return a

    def test_basarili_olusturma_meta_ve_dosyalar(self):
        sc = SahteCalistir()
        sc.yanitlar["dpkg"] = (0, "paket-a\tinstall\n")
        sc.yanitlar["du"] = (0, "12\t/hedef\n")
        # /etc, /root gercek sistemde var olabilir ama test onlari kullanmasin
        # diye PARCALAR'i gecici olarak degistiriyoruz.
        etc_kaynak = os.path.join(self.kok, "sahte-etc")
        os.makedirs(etc_kaynak)
        with open(os.path.join(etc_kaynak, "ornek.conf"), "w") as fh:
            fh.write("x")
        eski_parcalar = K.PARCALAR
        K.PARCALAR = (("etc", etc_kaynak),)
        try:
            sonuc = K.nokta_olustur(sc, etiket="İlk nokta", tetikleyici="elle",
                                    kok=self.noktalar, ayarlar=self.ayar())
        finally:
            K.PARCALAR = eski_parcalar
        meta = sonuc["nokta"]
        self.assertTrue(K.id_gecerli_mi(meta["id"]))
        self.assertEqual(meta["etiket"], "İlk nokta")
        self.assertEqual(meta["tetikleyici"], "elle")
        self.assertEqual(meta["parcalar"], ["etc"])
        self.assertEqual(meta["boyut_mb"], 12)
        self.assertEqual(sonuc["silinen"], [])
        nokta_dizini = K.nokta_yolu(meta["id"], self.noktalar)
        self.assertTrue(os.path.isfile(os.path.join(nokta_dizini, "meta.json")))
        self.assertTrue(os.path.isfile(os.path.join(nokta_dizini, "paketler.txt")))
        # ilk cagri: onceki nokta olmadigi icin --link-dest YOK
        ilk_rsync = sc.cagrilar[0]
        self.assertNotIn("--link-dest", ilk_rsync)

    def test_ikinci_nokta_oncekine_link_dest_verir(self):
        # Iki cagri ayni saniyede yapilabilir (simdi_id saniye hassasiyetinde);
        # id uretimi sabitlenerek cakisma onlenir.
        sc = SahteCalistir()
        sc.yanitlar["dpkg"] = (0, "")
        sc.yanitlar["du"] = (0, "1\t/x\n")
        kaynak = os.path.join(self.kok, "sahte-etc")
        os.makedirs(kaynak)
        eski_parcalar, eski_id_fn = K.PARCALAR, K.simdi_id
        K.PARCALAR = (("etc", kaynak),)
        K.simdi_id = lambda: "20260101-000001"
        try:
            ilk = K.nokta_olustur(sc, tetikleyici="elle", kok=self.noktalar, ayarlar=self.ayar())
            sc2 = SahteCalistir()
            sc2.yanitlar["dpkg"] = (0, "")
            sc2.yanitlar["du"] = (0, "1\t/x\n")
            K.simdi_id = lambda: "20260101-000002"
            K.nokta_olustur(sc2, tetikleyici="elle", kok=self.noktalar, ayarlar=self.ayar())
        finally:
            K.PARCALAR = eski_parcalar
            K.simdi_id = eski_id_fn
        ikinci_rsync = sc2.cagrilar[0]
        self.assertIn("--link-dest", ikinci_rsync)
        beklenen = os.path.join(K.nokta_yolu(ilk["nokta"]["id"], self.noktalar), "etc")
        self.assertEqual(ikinci_rsync[ikinci_rsync.index("--link-dest") + 1], beklenen)

    def test_disk_dolu_reddedilir_ve_dizin_birakilmaz(self):
        sc = SahteCalistir()
        import collections
        az = lambda _d: collections.namedtuple("U", "total used free")(0, 0, 1)
        with self.assertRaises(K.KurtarmaHatasi) as ctx:
            K.nokta_olustur(sc, kok=self.noktalar,
                            ayarlar=self.ayar(min_bos_mb=99999999))
        self.assertEqual(ctx.exception.kod, "disk_dolu")
        self.assertEqual(sc.cagrilar, [])   # hic rsync denenmedi
        self.assertFalse(os.path.isdir(self.noktalar) and os.listdir(self.noktalar))

    def test_gecersiz_etiket_reddedilir(self):
        sc = SahteCalistir()
        with self.assertRaises(K.KurtarmaHatasi) as ctx:
            K.nokta_olustur(sc, etiket="kotu;etiket", kok=self.noktalar, ayarlar=self.ayar())
        self.assertEqual(ctx.exception.kod, "gecersiz_etiket")

    def test_gecersiz_tetikleyici_reddedilir(self):
        sc = SahteCalistir()
        with self.assertRaises(K.KurtarmaHatasi) as ctx:
            K.nokta_olustur(sc, tetikleyici="baska", kok=self.noktalar, ayarlar=self.ayar())
        self.assertEqual(ctx.exception.kod, "gecersiz_tetikleyici")

    def test_rsync_hatasinda_dizin_temizlenir(self):
        sc = SahteCalistir(varsayilan=(1, "rsync hata ciktisi"))
        kaynak = os.path.join(self.kok, "sahte-etc")
        os.makedirs(kaynak)
        eski_parcalar = K.PARCALAR
        K.PARCALAR = (("etc", kaynak),)
        onceki_icerik = set(os.listdir(self.noktalar)) if os.path.isdir(self.noktalar) else set()
        try:
            with self.assertRaises(K.KurtarmaHatasi) as ctx:
                K.nokta_olustur(sc, kok=self.noktalar, ayarlar=self.ayar())
        finally:
            K.PARCALAR = eski_parcalar
        self.assertEqual(ctx.exception.kod, "rsync_hata")
        self.assertEqual(ctx.exception.ek["parca"], "etc")
        sonraki_icerik = set(os.listdir(self.noktalar)) if os.path.isdir(self.noktalar) else set()
        self.assertEqual(onceki_icerik, sonraki_icerik)   # yarim kalan nokta dizini silindi

    def test_eskiler_saklama_sinirini_asinca_silinir(self):
        # Dort cagri ayni saniyeye denk gelebilir; id uretimi sayacla sabitlenir.
        sc_fn = lambda: SahteCalistir(varsayilan=(0, "0\t/x\n"))
        kaynak = os.path.join(self.kok, "sahte-etc")
        os.makedirs(kaynak)
        eski_parcalar, eski_id_fn = K.PARCALAR, K.simdi_id
        K.PARCALAR = (("etc", kaynak),)
        idler = []
        try:
            for i in range(4):
                K.simdi_id = (lambda n: lambda: "2026010%d-000000" % n)(i + 1)
                sonuc = K.nokta_olustur(sc_fn(), tetikleyici="elle", kok=self.noktalar,
                                        ayarlar=self.ayar(sakla=2))
                idler.append(sonuc["nokta"]["id"])
        finally:
            K.PARCALAR = eski_parcalar
            K.simdi_id = eski_id_fn
        kalanlar = {m["id"] for m in K.noktalari_listele(self.noktalar)}
        self.assertEqual(len(kalanlar), 2)
        self.assertEqual(kalanlar, set(idler[-2:]))

    def test_cakisan_id_reddedilir(self):
        sc = SahteCalistir()
        kaynak = os.path.join(self.kok, "sahte-etc")
        os.makedirs(kaynak)
        eski_parcalar, eski_id_fn = K.PARCALAR, K.simdi_id
        K.PARCALAR = (("etc", kaynak),)
        K.simdi_id = lambda: "20260101-000000"
        try:
            os.makedirs(K.nokta_yolu("20260101-000000", self.noktalar))
            with self.assertRaises(K.KurtarmaHatasi) as ctx:
                K.nokta_olustur(sc, kok=self.noktalar, ayarlar=self.ayar())
            self.assertEqual(ctx.exception.kod, "cakisma")
            self.assertEqual(sc.cagrilar, [])
        finally:
            K.PARCALAR = eski_parcalar
            K.simdi_id = eski_id_fn


class NoktaSilVeGeriYukle(GeciciDizin):
    def test_sil_gecerli_nokta(self):
        self.meta_yaz("20260101-000000")
        K.nokta_sil("20260101-000000", self.noktalar)
        self.assertEqual(K.noktalari_listele(self.noktalar), [])

    def test_sil_gecersiz_id(self):
        with self.assertRaises(K.KurtarmaHatasi) as ctx:
            K.nokta_sil("../../etc", self.noktalar)
        self.assertEqual(ctx.exception.kod, "gecersiz_id")

    def test_sil_olmayan_nokta(self):
        with self.assertRaises(K.KurtarmaHatasi) as ctx:
            K.nokta_sil("20260101-000000", self.noktalar)
        self.assertEqual(ctx.exception.kod, "nokta_yok")

    def test_geri_yukle_olmayan_nokta(self):
        sc = SahteCalistir()
        with self.assertRaises(K.KurtarmaHatasi) as ctx:
            K.nokta_geri_yukle(sc, "20260101-000000", self.noktalar)
        self.assertEqual(ctx.exception.kod, "nokta_yok")

    def test_geri_yukle_mevcut_parcalari_rsync_eder(self):
        meta = self.meta_yaz("20260101-000000", parcalar=["etc"])
        os.makedirs(os.path.join(self.noktalar, meta["id"], "etc"))
        sc = SahteCalistir()
        eski_parcalar = K.PARCALAR
        K.PARCALAR = (("etc", "/hedef/etc/yolu"), ("root-ev", "/hedef/root/yolu"))
        try:
            sonuc = K.nokta_geri_yukle(sc, meta["id"], self.noktalar)
        finally:
            K.PARCALAR = eski_parcalar
        self.assertEqual(sonuc["parcalar"], {"etc": True})
        self.assertEqual(len(sc.cagrilar), 1)
        self.assertIn("--delete", sc.cagrilar[0])
        self.assertEqual(sc.cagrilar[0][-1], "/hedef/etc/yolu")

    def test_geri_yukle_rsync_hatasinda_durur(self):
        meta = self.meta_yaz("20260101-000000")
        os.makedirs(os.path.join(self.noktalar, meta["id"], "etc"))
        sc = SahteCalistir(varsayilan=(1, "hata"))
        eski_parcalar = K.PARCALAR
        K.PARCALAR = (("etc", "/hedef/etc"),)
        try:
            with self.assertRaises(K.KurtarmaHatasi) as ctx:
                K.nokta_geri_yukle(sc, meta["id"], self.noktalar)
        finally:
            K.PARCALAR = eski_parcalar
        self.assertEqual(ctx.exception.kod, "rsync_hata")

    def test_geri_yukle_paketleri_de_kur(self):
        meta = self.meta_yaz("20260101-000000")
        nokta_d = os.path.join(self.noktalar, meta["id"])
        with open(os.path.join(nokta_d, "paketler.txt"), "w") as fh:
            fh.write("paket-a\tinstall\npaket-b\tinstall\n")
        sc = SahteCalistir()
        sc.yanitlar["dpkg"] = (0, "paket-a\tinstall\n")
        sc.yanitlar["apt-get"] = (0, "Kuruldu")
        eski_parcalar = K.PARCALAR
        K.PARCALAR = ()
        try:
            sonuc = K.nokta_geri_yukle(sc, meta["id"], self.noktalar, paketleri_de_kur=True)
        finally:
            K.PARCALAR = eski_parcalar
        self.assertTrue(sonuc["paketler"]["basarili"])
        self.assertEqual(sonuc["paketler"]["denenen"], ["paket-b"])
        apt_cagrisi = [c for c in sc.cagrilar if c[0] == "apt-get"][0]
        self.assertIn("paket-b", apt_cagrisi)

    def test_geri_yukle_paket_listesi_yoksa_hata_doner_cokmez(self):
        meta = self.meta_yaz("20260101-000000")
        sc = SahteCalistir()
        eski_parcalar = K.PARCALAR
        K.PARCALAR = ()
        try:
            sonuc = K.nokta_geri_yukle(sc, meta["id"], self.noktalar, paketleri_de_kur=True)
        finally:
            K.PARCALAR = eski_parcalar
        self.assertFalse(sonuc["paketler"]["basarili"])
        self.assertEqual(sonuc["paketler"]["hata"], "paket_listesi_yok")


class OtoGuncellemeOncesi(GeciciDizin):
    def test_kapaliyken_hicbir_sey_yapmaz(self):
        sc = SahteCalistir()
        ayar = dict(K.VARSAYILAN_AYAR, oto_guncelleme_oncesi=False)
        sonuc = K.oto_guncelleme_oncesi(sc, self.noktalar, ayar)
        self.assertEqual(sonuc, {"atlandi": "kapali"})
        self.assertEqual(sc.cagrilar, [])

    def test_cok_yakin_zamandaysa_atlar(self):
        self.meta_yaz("20991231-235959", tetikleyici="oto",
                      olusturma=datetime.datetime.now().isoformat(timespec="seconds"))
        sc = SahteCalistir()
        sonuc = K.oto_guncelleme_oncesi(sc, self.noktalar, dict(K.VARSAYILAN_AYAR))
        self.assertEqual(sonuc, {"atlandi": "cok_yakin"})
        self.assertEqual(sc.cagrilar, [])

    def test_hic_oto_nokta_yoksa_olusturur(self):
        sc = SahteCalistir()
        sc.yanitlar["dpkg"] = (0, "")
        sc.yanitlar["du"] = (0, "1\t/x\n")
        kaynak = os.path.join(self.kok, "sahte-etc")
        os.makedirs(kaynak)
        eski_parcalar = K.PARCALAR
        K.PARCALAR = (("etc", kaynak),)
        try:
            sonuc = K.oto_guncelleme_oncesi(sc, self.noktalar, dict(K.VARSAYILAN_AYAR))
        finally:
            K.PARCALAR = eski_parcalar
        self.assertEqual(sonuc["nokta"]["tetikleyici"], "oto")
        self.assertEqual(sonuc["nokta"]["etiket"], "")

    def test_disk_doluysa_apt_islemini_durdurmaz_sadece_atlar(self):
        sc = SahteCalistir()
        ayar = dict(K.VARSAYILAN_AYAR, min_bos_mb=99999999)
        sonuc = K.oto_guncelleme_oncesi(sc, self.noktalar, ayar)
        self.assertEqual(sonuc, {"atlandi": "disk_dolu"})


if __name__ == "__main__":
    unittest.main(verbosity=1)
