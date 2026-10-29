#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Former testleri: zaman cizelgesi motoru (GTK'siz), 14 konunun icerik
dogrulamasi (iki dilli, sahneyle tutarli), Guvenlik Paneli'nin gercek arac
listesiyle capraz kontrol, simge yolu bulma ve (ekran varsa) arayuzun
butun konularda hatasiz gezilmesi.

Calistirma:  python3 tests/test_former.py
"""
from __future__ import annotations

import importlib
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot")
FORMER = os.path.join(INC, "opt/carotos/former")
ORTAK = os.path.join(INC, "opt/carotos/ortak")
PANEL_DIZIN = os.path.join(INC, "opt/carotos/security-panel")
for _y in (ORTAK, FORMER):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import former_zaman as fz  # noqa: E402
import former_cizim  # noqa: E402  (ice aktarilabildigini dogrular, GTK/cairo gerektirir)
import former_sahneler  # noqa: E402
import konular  # noqa: E402


# ---------------------------------------------------------------------------
class ZamanMotoruTesti(unittest.TestCase):
    """former_zaman.py: GTK'siz, saf mantik testleri."""

    def _sahne(self):
        return {
            "genislik": 400, "yukseklik": 300, "sayfa": "ana", "ogeler": [
                {"id": "dugme1", "tur": "dugme", "sayfa": "ana", "x": 10, "y": 10, "w": 80, "h": 24},
                {"id": "secim1", "tur": "secim", "sayfa": "ana", "x": 10, "y": 50, "w": 120, "h": 24,
                 "secenekler": [fz.T("Bir", "One"), fz.T("Iki", "Two")]},
                {"id": "cikti1", "tur": "cikti", "sayfa": "ana", "x": 10, "y": 90, "w": 200, "h": 100},
            ],
        }

    def test_metin_al_dil_dusmesi(self):
        m = fz.T("merhaba", "hello")
        self.assertEqual(fz.metin_al(m, "en"), "hello")
        self.assertEqual(fz.metin_al(m, "tr"), "merhaba")
        self.assertEqual(fz.metin_al(m, "de"), "merhaba")   # bilinmeyen dil -> tr'ye duser
        self.assertEqual(fz.metin_al(None, "tr"), "")
        self.assertEqual(fz.metin_al("duz metin", "tr"), "duz metin")

    def test_derle_toplam_ve_adim_baslangiclari(self):
        sahne = self._sahne()
        adimlar = [
            fz.balon("dugme1", fz.T("Baslik1", "Title1"), fz.T("Kisa metin.", "Short text.")),
            fz.tikla("dugme1"),
            fz.balon("secim1", fz.T("Baslik2", "Title2"), fz.T("Ikinci metin.", "Second text.")),
            fz.sec("secim1", 1),
            fz.cikti("cikti1", ["satir 1", "satir 2"]),
        ]
        cz = fz.derle(sahne, adimlar, "tr")
        self.assertGreater(cz.toplam, 0)
        self.assertEqual(len(cz.adim_baslangiclari), 2)
        self.assertEqual([b for b, _ms in cz.adim_baslangiclari], ["Baslik1", "Baslik2"])
        # adim zamanlari artan sirada olmali
        zamanlar = [ms for _b, ms in cz.adim_baslangiclari]
        self.assertEqual(zamanlar, sorted(zamanlar))
        # son kareye bakildiginda bitmis olmali ve cikti satirlari tam gorunmeli
        son = cz.durum(cz.toplam)
        self.assertTrue(son["bitti"])
        self.assertEqual(son["cikti"]["cikti1"], ["satir 1", "satir 2"])
        self.assertEqual(son["ogeler"]["secim1"]["secili"], 1)
        self.assertEqual(son["ogeler"]["secim1"]["deger"], "Iki")   # dil="tr" ile derlendi

    def test_durum_t0_baslangic(self):
        cz = fz.derle(self._sahne(), [fz.balon("dugme1", fz.T("B", "B"), fz.T("M", "M"))], "tr")
        d0 = cz.durum(0)
        self.assertIsNone(d0["balon"])       # henuz balon acilmadi (acilis duraklamasi var)
        self.assertFalse(d0["bitti"])

    def test_ayarla_sayfa_ve_bayrak(self):
        cz = fz.derle(self._sahne(), [fz.ayarla(_sayfa="baska", _bayrak={"x": True},
                                                dugme1={"pasif": True})], "tr")
        d = cz.durum(cz.toplam)
        self.assertEqual(d["sayfa"], "baska")
        self.assertTrue(d["bayraklar"]["x"])
        self.assertTrue(d["ogeler"]["dugme1"]["pasif"])

    def test_dogrula_temiz_sahne(self):
        sahne = self._sahne()
        adimlar = [fz.balon("dugme1", fz.T("B", "B"), fz.T("M", "M"))]
        self.assertEqual(fz.dogrula(sahne, adimlar), [])

    def test_dogrula_hatalari_yakalar(self):
        sahne = self._sahne()
        # olmayan hedef
        sorunlar = fz.dogrula(sahne, [fz.balon("yok", fz.T("B", "B"), fz.T("M", "M"))])
        self.assertTrue(any("yok" in s and "hedef" in s for s in sorunlar))
        # tek dilli metin
        sorunlar = fz.dogrula(sahne, [fz.balon("dugme1", {"tr": "B"}, fz.T("M", "M"))])
        self.assertTrue(any("iki dilde degil" in s for s in sorunlar))
        # gecersiz secim indeksi
        sorunlar = fz.dogrula(sahne, [fz.sec("secim1", 9)])
        self.assertTrue(any("gecersiz secenek" in s for s in sorunlar))
        # cikti olmayan bir alana cikti yazma
        sorunlar = fz.dogrula(sahne, [fz.cikti("dugme1", ["x"])])
        self.assertTrue(any("cikti alani degil" in s for s in sorunlar))
        # hic balon yoksa uyarmali
        sorunlar = fz.dogrula(sahne, [fz.tikla("dugme1")])
        self.assertTrue(any("balon" in s for s in sorunlar))
        # sahne disina tasan oge
        tasan = self._sahne()
        tasan["ogeler"][0]["w"] = 10000
        sorunlar = fz.dogrula(tasan, [fz.balon("dugme1", fz.T("B", "B"), fz.T("M", "M"))])
        self.assertTrue(any("sahne disinda" in s for s in sorunlar))
        # yinelenen kimlik
        yinelenen = self._sahne()
        yinelenen["ogeler"].append(dict(yinelenen["ogeler"][0]))
        sorunlar = fz.dogrula(yinelenen, [fz.balon("dugme1", fz.T("B", "B"), fz.T("M", "M"))])
        self.assertTrue(any("yinelenen oge kimligi" in s for s in sorunlar))

    def test_bilinmeyen_adim_turu_reddedilir(self):
        with self.assertRaises(ValueError):
            fz.derle(self._sahne(), [{"tur": "yok_boyle_bir_sey"}], "tr")


# ---------------------------------------------------------------------------
class IcerikTesti(unittest.TestCase):
    """konular/ altindaki 14 konunun yapisal dogrulugu."""

    @classmethod
    def setUpClass(cls):
        cls.konular = konular.tumu()

    def test_on_dort_konu_ve_benzersiz_kimlik(self):
        self.assertEqual(len(self.konular), 14)
        kimlikler = [k["id"] for k in self.konular]
        self.assertEqual(len(kimlikler), len(set(kimlikler)), kimlikler)
        self.assertEqual(set(kimlikler), set(konular.SIRA))

    def test_her_konu_zorunlu_alanlari_tasir(self):
        for k in self.konular:
            for alan in ("id", "grup", "ikon", "ad", "alt", "ozet", "vurgu", "sahne", "adimlar",
                         "bolumler", "uygulama", "root"):
                self.assertIn(alan, k, k.get("id"))
            self.assertIn(k["grup"], ("baslarken", "araclar", "uygulamalar"), k["id"])
            self.assertIsInstance(k["root"], bool, k["id"])
            for alan in ("alt", "ozet"):
                self.assertEqual(set(k[alan]), {"tr", "en"}, (k["id"], alan))
                self.assertTrue(k[alan]["tr"].strip() and k[alan]["en"].strip(), (k["id"], alan))
            # "ad": arac konularinda duz bir komut adi (orn. "nmap") olabilir;
            # metin_al() hem sozlugu hem duz metni kaldirir, burada da ayni kurali uygularlar.
            ad_tr, ad_en = fz.metin_al(k["ad"], "tr"), fz.metin_al(k["ad"], "en")
            self.assertTrue(ad_tr.strip() and ad_en.strip(), k["id"])
            if isinstance(k["ad"], dict):
                self.assertEqual(set(k["ad"]), {"tr", "en"}, k["id"])

    def test_sahneler_temiz_dogrulanir(self):
        for k in self.konular:
            sorunlar = fz.dogrula(k["sahne"], k["adimlar"])
            self.assertEqual(sorunlar, [], k["id"])

    def test_cizelge_her_dilde_derlenir(self):
        for k in self.konular:
            for dil in ("tr", "en"):
                cz = fz.derle(k["sahne"], k["adimlar"], dil)
                self.assertGreater(cz.toplam, 0, (k["id"], dil))
                # son kareye kadar istisnasiz gidebilmeli
                cz.durum(cz.toplam)
                cz.durum(0)
                cz.durum(cz.toplam / 2)

    def test_bolumler_iki_dilli_ve_bos_degil(self):
        gecerli_bloklar = {"p", "liste", "kod", "not", "uyari", "tablo"}

        def t_kontrol(m, yer):
            self.assertIsInstance(m, dict, yer)
            self.assertEqual(set(m), {"tr", "en"}, yer)
            self.assertTrue(m["tr"].strip(), yer)
            self.assertTrue(m["en"].strip(), yer)

        for k in self.konular:
            self.assertTrue(k["bolumler"], k["id"])
            for baslik, bloklar in k["bolumler"]:
                t_kontrol(baslik, (k["id"], "bolum basligi"))
                self.assertTrue(bloklar, (k["id"], baslik["tr"]))
                for tur, icerik in bloklar:
                    self.assertIn(tur, gecerli_bloklar, (k["id"], baslik["tr"], tur))
                    if tur in ("p", "not", "uyari"):
                        t_kontrol(icerik, (k["id"], baslik["tr"], tur))
                    elif tur == "liste":
                        self.assertTrue(icerik, (k["id"], baslik["tr"]))
                        for ogem in icerik:
                            t_kontrol(ogem, (k["id"], baslik["tr"], "liste ogesi"))
                    elif tur == "kod":
                        self.assertIsInstance(icerik, str, (k["id"], baslik["tr"]))
                        self.assertTrue(icerik.strip(), (k["id"], baslik["tr"]))
                    elif tur == "tablo":
                        self.assertTrue(icerik, (k["id"], baslik["tr"]))
                        for sol, sag in icerik:
                            t_kontrol(sol, (k["id"], baslik["tr"], "tablo sol"))
                            t_kontrol(sag, (k["id"], baslik["tr"], "tablo sag"))

    def test_uygulama_komutlari_listedir(self):
        for k in self.konular:
            uyg = k["uygulama"]
            if uyg is None:
                continue
            self.assertIn("ad", uyg, k["id"])
            self.assertIn("komut", uyg, k["id"])
            self.assertIsInstance(uyg["komut"], list, k["id"])
            self.assertTrue(all(isinstance(p, str) for p in uyg["komut"]), k["id"])

    def test_giris_karolari_tum_uygulamalara_isaret_eder(self):
        kimlikler = {k for k, _s, _a, _al in former_sahneler.KAROLAR}
        # giris sahnesindeki her karo, sahnede "karo:<id>" kimlikli bir ogeye karsilik gelmeli
        sahne = former_sahneler.giris_sahnesi()
        sahne_id = {o["id"] for o in sahne["ogeler"]}
        for kimlik in kimlikler:
            self.assertIn("karo:" + kimlik, sahne_id, kimlik)


# ---------------------------------------------------------------------------
class PanelCaprazKontrolTesti(unittest.TestCase):
    """Former'daki 10 arac konusunun, gercek Guvenlik Paneli'nin TOOLS
    listesiyle (arac adi, alan kimlikleri, kok yetkisi) tutarli oldugunu
    dogrular -- panel degisirse Former'in eskidigini burada yakalariz."""

    @classmethod
    def setUpClass(cls):
        panel_dosya = os.path.join(PANEL_DIZIN, "carotos-security-panel.py")
        if not os.path.isfile(panel_dosya):
            raise unittest.SkipTest("carotos-security-panel.py bulunamadi")
        spec = importlib.util.spec_from_file_location("carotos_security_panel", panel_dosya)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as h:    # GTK gerektiren ust duzey kod olabilir
            raise unittest.SkipTest(f"panel modulu yuklenemedi: {h}")
        cls.TOOLS = {t["name"]: t for t in mod.TOOLS}
        cls.konular = {k["id"]: k for k in konular.tumu()}

    # Former konu kimligi (dosya adi, alt cizgi) -> panel arac adi (tire)
    ESLESME = {
        "nmap": "nmap", "tcpdump": "tcpdump", "tshark": "tshark",
        "aircrack_ng": "aircrack-ng", "nikto": "nikto", "sqlmap": "sqlmap",
        "john": "john", "hydra": "hydra", "ufw": "ufw", "fail2ban": "fail2ban",
    }

    def test_on_arac_panelde_de_var(self):
        self.assertEqual(set(self.ESLESME.values()), set(self.TOOLS))

    def test_arac_sirasi_sahneyle_ayni(self):
        self.assertEqual(list(self.ESLESME.values()), former_sahneler.ARAC_SIRASI)

    def test_kok_yetkisi_tutarli(self):
        for former_id, panel_adi in self.ESLESME.items():
            k = self.konular[former_id]
            t = self.TOOLS[panel_adi]
            self.assertEqual(k["root"], bool(t.get("needs_root")), former_id)

    def test_alan_kimlikleri_panelle_eslesir(self):
        for former_id, panel_adi in self.ESLESME.items():
            modul = importlib.import_module("konular." + former_id)
            self.assertTrue(hasattr(modul, "ARAC"), former_id)
            former_alanlar = [a["id"] for a in modul.ARAC.get("alanlar", [])]
            panel_alanlar = [f[0] for f in self.TOOLS[panel_adi]["fields"]]
            self.assertEqual(former_alanlar, panel_alanlar, former_id)


# ---------------------------------------------------------------------------
class UygulamaDosyasiTesti(unittest.TestCase):
    """carotos-former.py: logo_bul() ve ayar anahtarlari."""

    @classmethod
    def setUpClass(cls):
        yol = os.path.join(FORMER, "carotos-former.py")
        mod = {"__file__": yol, "__name__": "carotos_former_test_mod"}
        with open(yol, encoding="utf-8") as fh:
            kaynak = fh.read()
        kaynak = kaynak.replace('if __name__ == "__main__":\n    main()', "")
        exec(compile(kaynak, yol, "exec"), mod)
        cls.mod = mod

    def test_logo_bul_gercek_bir_dosyaya_erisir(self):
        logo = self.mod["logo_bul"]()
        self.assertIsNotNone(logo, "logo_bul() None dondu; SVG/PNG bulunamadi")
        self.assertTrue(os.path.isfile(logo), logo)

    def test_varsayilan_ayarlar_dil_tema_anahtarlarini_kullanir(self):
        self.assertEqual(set(self.mod["DEFAULT_SETTINGS"]), {"dil", "tema"})
        self.assertIn(self.mod["DEFAULT_SETTINGS"]["dil"], ("tr", "en"))
        self.assertIn(self.mod["DEFAULT_SETTINGS"]["tema"], ("dark", "light"))


# ---------------------------------------------------------------------------
class SiblingAyarSenkronTesti(unittest.TestCase):
    """welcome/carotos-welcome.py: carotos-former SIBLING_CONFIGS'te ve
    kendi dil/tema anahtarlariyla (dil/tema) yaziliyor mu."""

    @classmethod
    def setUpClass(cls):
        yol = os.path.join(INC, "opt/carotos/welcome/carotos-welcome.py")
        if not os.path.isfile(yol):
            raise unittest.SkipTest("carotos-welcome.py bulunamadi")
        with open(yol, encoding="utf-8") as fh:
            cls.kaynak = fh.read()

    def test_former_sibling_configs_icinde(self):
        m = re.search(r"SIBLING_CONFIGS\s*=\s*\[(.*?)\]", self.kaynak, re.S)
        self.assertIsNotNone(m)
        self.assertIn('"carotos-former"', m.group(1))

    def test_former_icin_dil_tema_anahtar_eslemesi_var(self):
        self.assertIn('folder == "carotos-former"', self.kaynak)
        blok = self.kaynak[self.kaynak.index('folder == "carotos-former"'):]
        blok = blok[:blok.index("\n\n")] if "\n\n" in blok else blok[:400]
        self.assertIn('data["dil"]', blok)
        self.assertIn('data["tema"]', blok)

    def test_resources_sayfasinda_former_eylemi_var(self):
        self.assertIn('"action"', self.kaynak)
        self.assertIn("/opt/carotos/former/carotos-former.py", self.kaynak)


# ---------------------------------------------------------------------------
@unittest.skipUnless(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"),
                     "ekran yok (xvfb-run ile calistirin)")
class ArayuzDumanTesti(unittest.TestCase):
    """Pencereyi acar, 14 konunun hepsini gezer, dil/tema degistirir.
    Yakalanmayan istisna olmamali."""

    def test_butun_konular_hatasiz_gezilir(self):
        import tempfile
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, GLib

        ev = tempfile.mkdtemp(prefix="former-ev-")
        eski_home = os.environ.get("HOME")
        os.environ["HOME"] = ev
        self.addCleanup(lambda: os.environ.__setitem__("HOME", eski_home) if eski_home else None)

        yol = os.path.join(FORMER, "carotos-former.py")
        mod = {"__file__": yol, "__name__": "carotos_former_smoke_mod"}
        with open(yol, encoding="utf-8") as fh:
            kaynak = fh.read()
        kaynak = kaynak.replace('if __name__ == "__main__":\n    main()', "")
        exec(compile(kaynak, yol, "exec"), mod)
        Uygulama = mod["Uygulama"]

        app = Uygulama()
        self.assertIsNone(app._aktif_id)   # bos karsilama ekraniyla acilir
        hatalar = []

        def gez(kimlikler, i=0):
            if i >= len(kimlikler):
                app.dil_kutu.set_active_id("en")
                app._tema_degistir()
                GLib.timeout_add(200, lambda: Gtk.main_quit())
                return False
            try:
                app.kabuk.sec(kimlikler[i])
                app._adim()
            except Exception as h:    # noqa: BLE001
                hatalar.append((kimlikler[i], repr(h)))
            GLib.timeout_add(40, lambda: gez(kimlikler, i + 1))
            return False

        kimlikler = list(app.konular.keys())
        GLib.timeout_add(100, lambda: gez(kimlikler))
        GLib.timeout_add(8000, Gtk.main_quit)
        Gtk.main()
        app.destroy()
        self.assertEqual(hatalar, [])


if __name__ == "__main__":
    unittest.main()
