#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rehber (Former + GSD) denetim duzeltmeleri: R-01..R-09, D-01..D-03 ve icerik hatalari.

Calistirma:  python3 tests/test_rehber_denetim.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config/includes.chroot")
OPT = os.path.join(INC, "opt/carotos")
FORMER = os.path.join(OPT, "former")
GSD = os.path.join(OPT, "gsd")
ORTAK = os.path.join(OPT, "ortak")
for _y in (ORTAK, FORMER, GSD):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import former_zaman as fz  # noqa: E402
import former_sahneler  # noqa: E402
import konular  # noqa: E402

EKRAN = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def oku(*yol):
    with open(os.path.join(OPT, *yol), encoding="utf-8") as f:
        return f.read()


def metinler(konu):
    """Bir konunun tum tr+en metni."""
    parca = [a.get("metin") for a in konu["adimlar"] if isinstance(a.get("metin"), dict)]
    for _b, bloklar in konu["bolumler"]:
        for tur, icerik in bloklar:
            if tur in ("p", "not", "uyari"):
                parca.append(icerik)
            elif tur == "liste":
                parca.extend(icerik)
            elif tur == "kod":
                parca.append({"tr": icerik, "en": icerik})
    return "\n".join(p["tr"] + "\n" + p["en"] for p in parca)


class FormerKonuTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.konular = {k["id"]: k for k in konular.tumu()}

    def test_r01_uygulama_yollari_depoda_var(self):
        for kid, k in self.konular.items():
            for parca in (k.get("uygulama") or {"komut": []})["komut"][1:]:
                if parca.startswith("/opt/carotos/"):
                    self.assertTrue(os.path.isfile(os.path.join(INC, parca.lstrip("/"))), (kid, parca))

    def test_r01_ac_olmayan_betikte_false(self):
        if not EKRAN:
            self.skipTest("ekran yok")
        mod = self._former_modulu()
        self.assertFalse(mod["ac"](["python3", "/opt/carotos/olmayan/yok.py"]))

    @staticmethod
    def _former_modulu():
        yol = os.path.join(FORMER, "carotos-former.py")
        mod = {"__file__": yol, "__name__": "carotos_former_rd"}
        with open(yol, encoding="utf-8") as fh:
            kaynak = fh.read().replace('if __name__ == "__main__":\n    main()', "")
        exec(compile(kaynak, yol, "exec"), mod)
        return mod

    def test_r02_balon_hedefleri_gorunur(self):
        for kid, k in self.konular.items():
            self.assertEqual(fz.balon_hedefi_sorunlari(k["sahne"], k["adimlar"]), [], kid)
        c = self.konular["carotene"]
        self.assertTrue(any(a.get("hedef") == "d_guncelle" for a in c["adimlar"]))
        self.assertIn("Virüs tanımları bölümü", metinler(c))
        self.assertNotIn("Ayarlar sayfasındaki", metinler(c))

    def test_r02_gorunmeyen_hedef_yakalanir(self):
        sahne = {"genislik": 400, "yukseklik": 300, "sayfa": "a", "ogeler": [
            {"id": "x", "tur": "dugme", "sayfa": "b", "x": 1, "y": 1, "w": 10, "h": 10}]}
        sorun = fz.balon_hedefi_sorunlari(sahne, [fz.balon("x", fz.T("B", "B"), fz.T("M", "M"))])
        self.assertEqual(len(sorun), 1)

    def test_r06_panel_ikonu_tanimli(self):
        self.assertEqual(self.konular["panel"]["ikon"], "kalkan")

    def test_r07_birlesik_cumleler_parcali_cevrilir(self):
        m = fz.birlestir(fz.T("Ne zaman", "When"), ": ", fz.T("şimdi", "now"))
        self.assertEqual(m["tr"], "Ne zaman: şimdi")
        self.assertEqual(m["en"], "When: now")
        self.assertEqual(set(m), {"tr", "en"})
        self.assertEqual(fz.metin_al(m, "de"), "When: now")      # cevirisi olmayan dil -> en
        sahne = former_sahneler.panel_sahnesi(
            {"ad": "x", "tagline": fz.T("a", "a"), "ne": fz.T("b", "b"), "ne_zaman": fz.T("c", "c"),
             "ornek": fz.T("d", "d"), "root": False, "alanlar": []})
        zaman = next(o for o in sahne["ogeler"] if o["id"] == "a_zaman")
        self.assertEqual(zaman["metin"]["en"], "When to use it: c")

    def test_r09_bozuk_konu_uygulamayi_dusurmez(self):
        import importlib
        gercek = importlib.import_module
        def bozuk(ad, *a, **k):
            if ad == "konular.nmap":
                raise KeyError("bozuk")
            return gercek(ad, *a, **k)
        importlib.import_module = bozuk
        try:
            sonuc = konular.tumu()
        finally:
            importlib.import_module = gercek
        self.assertEqual(len(sonuc), len(konular.SIRA) - 1)

    def test_savunma_rozetleri_sigar(self):
        for k in ("savunma",):
            for o in self.konular[k]["sahne"]["ogeler"]:
                if o["id"] in ("s_ufw", "s_f2b"):
                    self.assertGreaterEqual(o["w"], 130)

    # --- icerik
    def test_nikto_sunucu_yalniz_yerel(self):
        m = metinler(self.konular["nikto"])
        self.assertIn("--bind 127.0.0.1", m)
        self.assertIn("http://127.0.0.1:8000", m)

    def test_sqlmap_bulunamadi_guvence_degildir(self):
        m = metinler(self.konular["sqlmap"])
        self.assertNotIn("iyi haberdir", m)
        self.assertNotIn("is good news", m)
        self.assertIn("kanıtı değildir", m)

    def test_fail2ban_panel_ciktisi_yalniz_genel_durum(self):
        import konular.fail2ban as f
        self.assertNotIn("Status for the jail", "\n".join(f.CIKTI))
        self.assertIn("Status for the jail: sshd", "\n".join(f.SSHD_CIKTI))
        self.assertIn("sudo fail2ban-client status sshd", metinler(self.konular["fail2ban"]))

    def test_ctf_puan_ve_sira_tutarli(self):
        ad = next(a for a in self.konular["ctf"]["adimlar"]
                  if a["tur"] == "tikla" and "c_skor" in (a["etki"].get("ayarla") or {}))
        ay = ad["etki"]["ayarla"]
        self.assertIn("Sıran: 4", ay["c_puan"]["metin"]["tr"])
        self.assertIn("3. Deniz 100 · 4. Sen 90", ay["c_skor"]["metin"]["tr"])

    def test_hydra_servis_serbest_metin(self):
        m = metinler(self.konular["hydra"])
        self.assertNotIn("Panel sana uygun olanı seçtirir", m)
        self.assertIn("sen yazarsın", m)

    def test_dogrula_parmak_izi_ayri_kaynak(self):
        self.assertIn("ayrı bir kaynaktan", metinler(self.konular["dogrula"]))

    def test_ufw_varsayilan_kapali_anlatilir(self):
        m = metinler(self.konular["ufw"])
        self.assertIn("varsayılan olarak kapalı", m)
        self.assertIn("by default", m)
        self.assertIn("Güvenlik Paneli > ufw > Etkinleştir", m)
        self.assertIn("sudo ufw enable", m)
        self.assertIn("ufw açıkken varsayılan kural", m)

    def test_carotpot_baglanti_kapsami(self):
        k = self.konular["carotpot"]
        m = metinler(k)
        for parca in ("yalnızca yerel ağdan", "silinir", "Bağlantı kapsamı", "İnternetten gelen bağlantıları da kabul et",
                      "varsayılan olarak kapalı", "bilerek"):
            self.assertIn(parca, m, parca)
        # etiketler CarotPot arayuzuyle ayni
        met = oku("carotpot", "arayuz", "metinler.py")
        self.assertIn("Bağlantı kapsamı", met)
        self.assertIn("İnternetten gelen bağlantıları da kabul et", met)
        # sahnede anahtar var, kapali ve olay satirlari gosteriliyor (icerik #9)
        o = {x["id"]: x for x in k["sahne"]["ogeler"]}
        self.assertFalse(o["ay_internet"]["aktif"])
        bayraklar = {}
        for a in k["adimlar"]:
            if a["tur"] == "ayarla":
                bayraklar.update(a["degisiklik"].get("_bayrak", {}))
        for b in ("o1", "o2", "o3", "o4"):
            self.assertTrue(bayraklar.get(b), b)

    def test_poligon_notu_uc_konuda(self):
        for kid in ("giris", "ctf", "savunma"):
            m = metinler(self.konular[kid])
            self.assertIn("sınıf içi kullanım için tasarlandı; güvendiğin bir ağda kullan", m, kid)
            self.assertIn("designed for use inside a classroom", m, kid)


class GsdTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kaynak = oku("gsd", "carotos-gsd.py")
        cls.ns = {}
        # GTK'siz saf yardimcilari al: _ara_katla ve _tr_anahtar
        bas = cls.kaynak.index("_TR_KUCUK = ")
        son = cls.kaynak.index("KATEGORI_IKON")
        exec(cls.kaynak[bas:son], cls.ns)

    def test_d01_arama_katlamasi(self):
        k = self.ns["_ara_katla"]
        self.assertEqual(k("IP Adresi"), k("ip adresi"))
        self.assertIn(k("ip adresi"), k("IP Adresi"))
        self.assertEqual(k("INFO"), k("info"))
        self.assertEqual(k("ISTISMAR"), k("İstismar"))
        self.assertEqual(k("IKILI"), k("ikili"))
        self.assertEqual(k("İki Faktörlü"), k("iki faktorlu"))

    def test_d01_siralama_ingilizcede_i_ile(self):
        a = self.ns["_tr_anahtar"]
        self.assertLess(a("ICMP", tr=False), a("iptables", tr=False))
        self.assertGreater(a("ICMP", tr=True), a("hash", tr=True))

    def test_d01_gercek_terimlerde_sorgular_bulunur(self):
        import terimler
        k = self.ns["_ara_katla"]
        tumu = terimler.tumu() if hasattr(terimler, "tumu") else terimler.TERIMLER
        metin = {}
        for t in tumu:
            parca = [t["id"]]
            for alan in ("baslik", "kisa", "aciklama"):
                parca += [fz.metin_al(t.get(alan), "tr"), fz.metin_al(t.get(alan), "en")]
            parca.append(t.get("ornek") or "")
            metin[t["id"]] = k(" ".join(parca))
        for sorgu in ("ip adresi", "INFO", "ISTISMAR", "ikili", "İki Faktörlü"):
            self.assertTrue(any(k(sorgu) in m for m in metin.values()), sorgu)

    def test_d02_d03_kaynak(self):
        self.assertIn("self._listeyi_yenile()\n            if self._aktif_id:", self.kaynak)
        self.assertIn("get_vadjustment().set_value(0)", self.kaynak)
        self.assertIn('"mono", sar=True, genislik=90, sec=True', self.kaynak)

    def test_icerik_duzeltmeleri(self):
        linux = oku("gsd", "terimler", "linux.py")
        genel = oku("gsd", "terimler", "genel.py")
        krip = oku("gsd", "terimler", "kriptografi.py")
        algo = oku("gsd", "terimler", "algoritma.py")
        guv = oku("gsd", "terimler", "guvenlik.py")
        self.assertNotIn("/var/log/syslog", linux)
        self.assertIn('journalctl -b | grep -i', linux)
        self.assertNotIn("/var/log/auth.log", genel)
        self.assertIn("journalctl -u ssh | grep -E", genel)
        self.assertIn("SHA256:", krip)
        self.assertIn("sha256sum carotos-1.4-amd64.iso", krip)
        self.assertNotIn("1947'de gerçek bir güve kelebeğinin bir bilgisayar \"\n", "")  # yer tutucu
        self.assertIn("popülerleşti", genel)
        self.assertIn("popularised in 1947", genel)
        self.assertIn("P≠NP", algo)
        self.assertNotIn("şifirelerden", guv)
        self.assertNotIn("veritabanda", krip)
        self.assertNotIn("150'den fazla", self.kaynak)


@unittest.skipUnless(EKRAN, "ekran yok (xvfb-run ile calistirin)")
class FormerArayuzTesti(unittest.TestCase):
    def test_hiz_durumu_ve_zamanlayici(self):
        import tempfile
        ev = tempfile.mkdtemp(prefix="rehber-ev-")
        eski = os.environ.get("HOME")
        os.environ["HOME"] = ev
        self.addCleanup(lambda: os.environ.__setitem__("HOME", eski) if eski else None)
        mod = FormerKonuTesti._former_modulu()
        app = mod["Uygulama"]()
        app.kabuk.sec("nmap")
        self.assertIsNotNone(app._zamanlayici_id)
        app._hiz_degisti("1.5")
        app.kabuk.sec("ufw")                     # baska konu: hiz korunur, dugme grubu da 1.5 gosterir
        self.assertEqual(app._hiz, 1.5)
        # bitince zamanlayici birakilir
        app._t = float(app._cz.toplam) - 1.0
        self.assertFalse(app._adim() is True and app._oynuyor)
        self.assertIsNone(app._zamanlayici_id)
        # tekrar oynat -> zamanlayici yeniden kurulur
        app._oynat_duraklat()
        self.assertTrue(app._oynuyor)
        self.assertIsNotNone(app._zamanlayici_id)
        # tema degisince anlatim yeri korunur
        app._t = 3000.0
        app._oynuyor = False
        app._tema_degistir()
        self.assertGreaterEqual(app._t, 3000.0)
        self.assertFalse(app._oynuyor)
        app.destroy()


if __name__ == "__main__":
    unittest.main()
