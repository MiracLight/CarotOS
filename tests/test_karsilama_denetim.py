#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Karsilama denetim duzeltmeleri (K-01..K-07, O-03) ve yeni icerik (ekran yoksa atlanir).

Calistirma:  xvfb-run -a python3 tests/test_karsilama_denetim.py
"""
import json
import os
import shutil
import tempfile
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_dil_uygulamalar import EKRAN, UygulamaDilTabani, INC  # noqa: E402

sys.path.insert(0, os.path.join(INC, "welcome"))


def _metin(sayfa):
    out = []
    for tur, yuk in sayfa.get("body", []):
        if tur in ("p", "note"):
            out.append(yuk)
        elif tur == "bullets":
            out.extend(yuk)
    return out


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class KarsilamaDenetimTesti(UygulamaDilTabani):
    def setUp(self):
        super().setUp()
        self.m = self.modul("welcome")
        os.makedirs(self.m.CONFIG_DIR, exist_ok=True)

    # -- K-05 ------------------------------------------------------------------------
    def test_k05_yanlis_turlu_ayarlar_cokmez(self):
        kotuler = [{"biten_konular": [[1]]}, {"biten_konular": [{"a": 1}]}, {"theme": [1]},
                   {"wallpaper": ["a"]}, {"wallpaper": 5}, {"show_on_startup": "false"}, [1, 2], 5]
        for k in kotuler:
            with open(self.m.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(k, f)
            s = self.m.load_settings()
            self.assertIn(s["theme"], ("dark", "light"))
            self.assertIsInstance(s["wallpaper"], str)
            self.assertTrue(all(isinstance(b, str) for b in s["biten_konular"]))
            self.assertIsInstance(s["show_on_startup"], bool)
            self.m.gezinme.Gezinme(s["biten_konular"])           # unhashable hatasi vermemeli

    def test_k05_gezinme_hashlenemeyen_ogeleri_yok_sayar(self):
        g = self.m.gezinme.Gezinme([[1], {"a": 1}, "sistem", 3, None])
        self.assertEqual(g.biten_konular(), ["sistem"])

    def test_k05_atomik_yaz_ve_save_settings(self):
        self.m.save_settings({"lang": "tr", "theme": "light"})
        with open(self.m.CONFIG_FILE, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["theme"], "light")
        self.assertEqual([a for a in os.listdir(self.m.CONFIG_DIR) if a.startswith(".carotos-tmp")], [])

    def test_k05_bozuk_kardes_ayar_kenara_alinir(self):
        base = os.environ["XDG_CONFIG_HOME"]
        yol = os.path.join(base, "carotos-panel", "settings.json")
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            f.write("{bozuk json")
        self.m.apply_sibling_settings("tr", "dark")
        self.assertTrue(os.path.isfile(yol + ".bozuk"))
        with open(yol + ".bozuk", encoding="utf-8") as f:
            self.assertEqual(f.read(), "{bozuk json")
        with open(yol, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["language"], "tr")

    # -- K-04 ------------------------------------------------------------------------
    def test_k04_xsessionrc_utf8_degilse_ve_ters_isaretcide(self):
        ev = os.environ["HOME"]
        yol = os.path.join(ev, ".xsessionrc")
        with open(yol, "wb") as f:
            f.write(b"export A=\xe9\xff\n")
        self.assertTrue(self.m._write_xsessionrc("ja_JP.UTF-8"))
        with open(yol, "rb") as f:
            self.assertIn(b"export A=", f.read())
        # ters siralanmis isaretciler dosyayi cogaltmaz
        with open(yol, "w", encoding="utf-8") as f:
            f.write(self.m.XSESSION_END + "\nx\n" + self.m.XSESSION_START + "\n")
        self.assertTrue(self.m._write_xsessionrc("tr_TR.UTF-8"))
        with open(yol, encoding="utf-8") as f:
            icerik = f.read()
        self.assertEqual(icerik.count(self.m.XSESSION_START), 2)  # ters isaretci: yeni blok eklenir, eskisi bozulmaz
        self.assertIn("export LANG=tr_TR.UTF-8", icerik)

    def test_k04_dmrc_utf8_degilse_cokmez(self):
        yol = os.path.join(os.environ["HOME"], ".dmrc")
        with open(yol, "wb") as f:
            f.write(b"[Desktop]\nSession=xfce\n\xe9\xff\n")
        self.assertTrue(self.m._write_dmrc("tr_TR.UTF-8"))
        with open(yol, encoding="utf-8") as f:
            self.assertIn("Language=tr_TR.UTF-8", f.read())

    def _sahte_pencere(self, hazir):
        m = self.m
        cagrilar = []

        class Sahte:
            lang, theme, wallpaper = "ja", "dark", ""

            def set_sensitive(self, _):
                pass

            def prepare_language(self):
                return hazir

            _sistemi_uygula = m.WelcomeWindow._sistemi_uygula

        return Sahte(), cagrilar

    def _kancala(self, cagrilar, hata=None):
        m = self.m
        eski = (m.apply_desktop_theme, m.apply_sibling_settings, m.apply_session_language,
                m.apply_wallpaper, m.sd.hazirlik_gerekli_mi)

        def kaydet(ad, exc=None):
            def f(*a):
                cagrilar.append(ad)
                if exc:
                    raise exc
            return f
        m.apply_desktop_theme = kaydet("tema", hata)
        m.apply_sibling_settings = kaydet("kardes")
        m.apply_session_language = kaydet("oturum")
        m.apply_wallpaper = kaydet("duvar")
        m.sd.hazirlik_gerekli_mi = lambda kod: False
        self.addCleanup(lambda: (setattr(m, "apply_desktop_theme", eski[0]),
                                 setattr(m, "apply_sibling_settings", eski[1]),
                                 setattr(m, "apply_session_language", eski[2]),
                                 setattr(m, "apply_wallpaper", eski[3]),
                                 setattr(m.sd, "hazirlik_gerekli_mi", eski[4])))

    # -- K-02 ------------------------------------------------------------------------
    def test_k02_hazirlik_basarisizsa_oturum_dili_yazilmaz(self):
        for hazir, beklenen in ((False, False), (True, True)):
            pencere, cagrilar = self._sahte_pencere(hazir)
            self._kancala(cagrilar)
            self.m.WelcomeWindow.apply_choices(pencere)
            self.assertEqual("oturum" in cagrilar, beklenen)
            self.assertIn("duvar", cagrilar)

    # -- K-04: adim hatasi digerlerini durdurmaz -----------------------------------
    def test_k04_bir_adim_hata_verse_digerleri_calisir(self):
        pencere, cagrilar = self._sahte_pencere(True)
        self._kancala(cagrilar, hata=RuntimeError("deneme"))
        self.m.WelcomeWindow.apply_choices(pencere)
        self.assertEqual(cagrilar, ["tema", "kardes", "oturum", "duvar"])

    def test_k04_apply_choices_hatasinda_pencere_kapanir(self):
        p = self.m.WelcomeWindow(self.m.load_settings())
        self.addCleanup(p.destroy)
        kapandi = []
        p.close = lambda: kapandi.append(1)

        def patla():
            raise ValueError("x")
        p.apply_choices = patla
        p.gezinme.sayfaya_git("resources")
        p.next_btn.emit("clicked")
        self.assertEqual(kapandi, [1])

    # -- K-03 ------------------------------------------------------------------------
    def test_k03_xfconf_donus_kodunu_denetler(self):
        m = self.m
        eski_run, eski_which = m.subprocess.run, m.shutil.which
        m.shutil.which = lambda a: "/bin/x"

        class R:
            returncode = 1
        m.subprocess.run = lambda *a, **k: R()
        try:
            self.assertFalse(m.xfconf("c", "/p", "v"))
            R.returncode = 0
            self.assertTrue(m.xfconf("c", "/p", "v"))
        finally:
            m.subprocess.run, m.shutil.which = eski_run, eski_which

    # -- K-01 / O-03 -----------------------------------------------------------------
    def test_k01_iptal_izin_hatasi_pencereyi_acik_birakmaz(self):
        kaynak = open(os.path.join(INC, "welcome", "carotos-welcome.py"), encoding="utf-8").read()
        govde = kaynak[kaynak.index("def _run_language_setup"):kaynak.index("def on_back")]
        self.assertIn("except OSError", govde)
        self.assertIn("finally:", govde)
        self.assertIn("dlg.destroy()", govde.split("finally:")[1].split("\n")[1])
        self.assertIn("dh_iptal_edilemedi", self.m.UI)
        for dl in ("tr", "en"):
            self.assertTrue(self.m.UI["dh_iptal_edilemedi"][dl])

    # -- K-06 ------------------------------------------------------------------------
    def test_k06_bitir_bir_daha_kendiliginden_acilmaz_yaridan_kapatinca_acilir(self):
        p = self.m.WelcomeWindow(self.m.load_settings())
        self.addCleanup(p.destroy)
        self.assertTrue(self.m.load_settings()["show_on_startup"])
        p.close = lambda: None
        p.apply_choices = lambda: None
        # yarida kapatma: Bitir'e basilmadi -> ayar degismez, sonraki acilista yine gelir
        self.assertTrue(self.m.load_settings()["show_on_startup"])
        p.gezinme.sayfaya_git("resources")
        p.next_btn.emit("clicked")                  # son sayfadan Bitir
        self.assertFalse(self.m.load_settings()["show_on_startup"])
        # --autostart artik sessizce cikar; menuden (bayraksiz) acilis etkilenmez
        eski = sys.argv
        sys.argv = ["carotos-welcome", "--autostart"]
        try:
            self.assertEqual(self.m.main(), 0)      # pencere acilmadan doner
        finally:
            sys.argv = eski

    def test_k06_autostart_aciklamasi_gercek_davranisi_soyler(self):
        yol = os.path.join(INC, "..", "..", "etc", "skel", ".config", "autostart", "carotos-welcome-autostart.desktop")
        with open(yol, encoding="utf-8") as f:
            icerik = f.read()
        self.assertNotIn("once after installation", icerik)
        self.assertNotIn("bir kez gösterilir", icerik)
        for anahtar in ("Comment=", "Comment[tr]="):
            self.assertIn(anahtar, icerik)

    # -- K-07 ------------------------------------------------------------------------
    def test_k07_kartla_dil_secince_ust_secici_eslesir(self):
        self.dil_dosyasi("de", {"Next": "Weiter"})
        p = self.m.WelcomeWindow(self.m.load_settings())
        self.addCleanup(p.destroy)
        p.show_all()
        p.refresh()
        self.pompala()
        p._on_lang_pick(None, None, "de")
        self.pompala()
        self.assertEqual(p.lang_combo.get_active_id(), "de")

    # -- "Sistem temasini modernlestir" anahtari ------------------------------------------
    def test_modern_anahtar_komutlari(self):
        import types
        W = self.m.WelcomeWindow
        ns = types.SimpleNamespace(TEMA_KUR=W.TEMA_KUR, MODERNLESTIR=W.MODERNLESTIR)
        ac = W.modern_komutlari(ns, True)
        self.assertEqual(len(ac), 2)
        self.assertTrue(ac[0][0].endswith("pkexec"))
        self.assertEqual(ac[0][1:], ["/usr/sbin/carotos-tema-kur", "kur"])        # sabit, kullanici girdisi yok
        self.assertEqual(ac[1], ["/usr/bin/python3", "-I", "/usr/bin/carotos-modernlestir", "uygula"])
        self.assertEqual(W.modern_komutlari(ns, False),
                         [["/usr/bin/python3", "-I", "/usr/bin/carotos-modernlestir", "geri-al"]])

    def test_modern_calistir_ilk_hatada_durur(self):
        import types
        W = self.m.WelcomeWindow
        ns = types.SimpleNamespace()
        self.assertEqual(W.modern_calistir(ns, [["/bin/true"], ["/bin/true"]]), 0)
        self.assertEqual(W.modern_calistir(ns, [["/bin/false"], ["/bin/true"]]), 1)
        self.assertEqual(W.modern_calistir(ns, [["/yok/boyle/komut"]]), 1)

    def test_modern_gorunum_aciksa_bitir_temayi_ezmez(self):
        ev = tempfile.mkdtemp(prefix="karsilama-ev-")
        self.addCleanup(shutil.rmtree, ev, True)
        eski = os.environ.get("HOME")
        os.environ["HOME"] = ev
        self.addCleanup(lambda: os.environ.__setitem__("HOME", eski) if eski is not None
                        else os.environ.pop("HOME", None))
        cagrilar = []
        eski_xfconf = self.m.xfconf
        self.m.xfconf = lambda *a, **k: cagrilar.append(a) or True
        self.addCleanup(setattr, self.m, "xfconf", eski_xfconf)
        for ad, deger in (("available_theme", lambda liste: "Arc-Dark"),            # kurulu tema varmis gibi
                          ("available_icon_theme", lambda liste: None),
                          ("available_cursor_theme", lambda liste: None),
                          ("has_xfwm_variant", lambda ad: False)):
            self.addCleanup(setattr, self.m, ad, getattr(self.m, ad))
            setattr(self.m, ad, deger)
        self.assertFalse(self.m.sleek_uygulanmis_mi())
        self.m.apply_desktop_theme("dark")
        ilk = len(cagrilar)
        self.assertGreater(ilk, 0)                              # modern gorunum yokken tema uygulanir
        yedek = os.path.join(ev, ".local", "state", "carotos", "sleek-yedek.json")
        os.makedirs(os.path.dirname(yedek))
        with open(yedek, "w") as f:
            f.write("{}")
        self.assertTrue(self.m.sleek_uygulanmis_mi())
        self.assertTrue(self.m.apply_desktop_theme("dark"))
        self.assertEqual(len(cagrilar), ilk)                    # Orchis/Papirus/imlec ezilmedi

    # -- yeni icerik ------------------------------------------------------------------
    def _sayfa(self, kimlik):
        return next(s for s in self.m.PAGES if s["id"] == kimlik)

    def _tum_en(self, sayfa):
        return " ".join(d["en"] for d in _metin(sayfa))

    def test_guvenlik_duvari_sayfasi(self):
        s = self._sayfa("guvenlik_duvari")
        konular = {k["id"]: k["sayfalar"] for k in self.m.gezinme.KONULAR}
        self.assertEqual(konular["guvenlik_duvari"], ["guvenlik_duvari"])   # artik kendi konusu
        self.assertNotIn("guvenlik_duvari", konular["koruma"])
        tr = " ".join(d["tr"] for d in _metin(s))
        en = self._tum_en(s)
        for parca in ("Güvenlik Paneli", "Etkinleştir", "sudo ufw enable", "kapalı"):
            self.assertIn(parca, tr + " ".join(c for t, c in s["body"] if t == "code"))
        self.assertIn("Security Panel", en)
        self.assertIn("off on purpose", en)
        self.assertIn(("code", "sudo ufw enable"), s["body"])

    def test_poligon_ve_carotpot_notlari(self):
        p = " ".join(d["tr"] for d in _metin(self._sayfa("poligon")))
        self.assertIn("sınıf içi kullanım için tasarlandı; güvendiğin bir ağda kullan", p)
        self.assertIn("1.5", p)
        c = " ".join(d["tr"] for d in _metin(self._sayfa("carotpot")))
        for parca in ("yalnızca yerel ağdan", "kendiliğinden silinir", "Ayarlar", "bilerek aç"):
            self.assertIn(parca, c)
        ce = self._tum_en(self._sayfa("carotpot"))
        self.assertIn("removed automatically", ce)
        self.assertIn("only on purpose", ce)

    def test_acikla_sayfasi_sarmalayicilari_anlatir(self):
        s = self._sayfa("acikla")
        tr = " ".join(d["tr"] for d in _metin(s))
        self.assertIn("ayrı parça olarak açıklanır", tr)
        self.assertNotIn("içi açıklanmaz", tr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
