#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poligon: üretilen kayıt dosyalarının alan adları arayüz diline göre (GTK'siz).

* her dilde dosya o dilin alan adlarıyla yazılır, Türkçe (kanonik) ad kalmaz
* ipucu komutlarındaki her alan adı/değer gerçekten dosyada vardır (komut dosyayla uyuşur)
* görev sürerken dil değişirse AÇIK görev bozulmaz; sonraki görev yeni dille üretilir
* cevap dilden bağımsızdır

Calistirma:  python3 tests/test_poligon_terim.py
"""
import json
import os
import re
import sys
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPT = os.path.join(KOK, "config", "includes.chroot", "opt", "carotos")
for _y in (os.path.join(OPT, "ortak"), os.path.join(OPT, "poligon")):
    sys.path.insert(0, _y)

import terim_sozlugu as T  # noqa: E402
import uretilen_gorevler as U  # noqa: E402
import varyantlar as VY  # noqa: E402

DILLER = ("tr", "en", "de", "es", "fr", "pt", "ru", "ja", "zh")
KANONIK_ANAHTAR = ("kaynak", "hizmet", "kullanici", "parola", "hedef_port", "kaynak_port", "ozet", "ayrinti")


def uret(soru, no, kod, zorluk="kolay"):
    return U.uret("carotpot_kayit", {"_zorluk": zorluk, "varyant": no}, {"soru": soru}, "127.0.0.1", dil=kod)


class SozlukTesti(unittest.TestCase):
    def test_dokuz_dil_ve_ayni_uzunluk(self):
        self.assertEqual(set(T.SOZLUK), set(DILLER))
        for kod, terimler in T.SOZLUK.items():
            self.assertEqual(len(terimler), len(T.SIRA), kod)

    def test_terimler_tekil_ve_kabukta_yazilabilir(self):
        for kod, terimler in T.SOZLUK.items():
            with self.subTest(kod=kod):
                self.assertEqual(len(set(terimler)), len(terimler), "ayni terim iki alana verilmis")
                for t in terimler:
                    self.assertRegex(t, r"^[a-z_]+$", "ASCII, kucuk harf, alt cizgi")

    def test_tr_kanonik_ve_degismez(self):
        self.assertEqual(T.SOZLUK["tr"], T.SIRA)
        metin = "grep 'tur=giris' x | grep -oE '\"kullanici\": \"[^\"]+\"'"
        self.assertEqual(T.komut_yerellestir(metin, "tr"), metin)

    def test_bilinmeyen_dil_ingilizce(self):
        self.assertEqual(T.sozluk_kodu("xx"), "en")
        self.assertEqual(T.sozluk_kodu(None), "en")


class KomutDonusumuTesti(unittest.TestCase):
    def test_komut_kaliplari(self):
        s = ("grep 'tur=giris' F | grep -oE '\"kullanici\": \"[^\"]+\"'; "
             "jq -r 'select(.tur==\"giris\" and .hizmet==\"http\") | .kaynak' F; grep -oE 'kaynak=[0-9.]+' F")
        self.assertEqual(
            T.komut_yerellestir(s, "en"),
            "grep 'type=login' F | grep -oE '\"username\": \"[^\"]+\"'; "
            "jq -r 'select(.type==\"login\" and .service==\"http\") | .source' F; grep -oE 'source=[0-9.]+' F")

    def test_duz_cumledeki_sozcuklere_dokunmaz(self):
        # "hizmet" Türkçe bir sözcük: komut kalıbı değilse değişmemeli
        c = "En çok giriş denemesi hangi hizmete yapıldı? Hizmet adını yaz."
        self.assertEqual(T.komut_yerellestir(c, "en"), c)

    def test_tirnakli_olay_turu(self):
        self.assertEqual(T.komut_yerellestir("Kayıtta kaç 'giris' olayı var?", "de"), "Kayıtta kaç 'anmeldung' olayı var?")
        self.assertEqual(T.komut_yerellestir("How many 'tarama' events?", "es"), "How many 'escaneo' events?")

    def test_port_alanlari_once(self):
        # kaynak_port, kaynak'tan önce eşleşmeli
        self.assertEqual(T.komut_yerellestir(".kaynak_port .hedef_port", "en"), ".source_port .target_port")


class SatirDonusumuTesti(unittest.TestCase):
    def test_satir_ve_jsonl(self):
        js = json.dumps({"ts": 1.0, "hizmet": "ssh", "kaynak": "10.0.0.1", "kaynak_port": 1, "hedef_port": 2222,
                         "tur": "giris", "ozet": "ssh giris", "kullanici": "root", "ayrinti": None, "parola": "p***"})
        satir = f"2026-01-02 03:04:05 CAROTPOT kaynak=10.0.0.1 hizmet=ssh tur=giris | {js}"
        yeni = T.cp_satiri_yerellestir(satir, "carotpot", "de")
        self.assertTrue(yeni.startswith("2026-01-02 03:04:05 CAROTPOT quelle=10.0.0.1 dienst=ssh typ=anmeldung | "))
        o = json.loads(yeni.split(" | ", 1)[1])
        self.assertEqual(o["benutzername"], "root")
        self.assertEqual(o["zielport"], 2222)
        self.assertEqual(o["zusammenfassung"], "ssh anmeldung")
        self.assertEqual(o["typ"], "anmeldung")
        j = json.loads(T.cp_satiri_yerellestir(js, "jsonl", "en"))
        self.assertEqual(j["username"], "root")
        self.assertEqual(j["type"], "login")
        self.assertEqual(j["ts"], 1.0)

    def test_tanimsiz_satir_hata(self):
        with self.assertRaises(ValueError):
            T.cp_satiri_yerellestir("bozuk satir", "carotpot", "en")


class UretimTesti(unittest.TestCase):
    def _her_varyant(self):
        for soru in ("kullanici", "tarayici"):
            anahtar = VY.anahtar_bul("carotpot_kayit", soru)
            for no in range(1, VY.sayi(anahtar) + 1):
                yield soru, no

    def test_dosya_ve_ipucu_her_dilde_uyusur(self):
        for soru, no in self._her_varyant():
            for kod in DILLER:
                with self.subTest(soru=soru, varyant=no, dil=kod):
                    u = uret(soru, no, kod)
                    try:
                        icerik = open(u.dosya_yolu, encoding="utf-8").read()
                        for dil in ("tr", "en"):
                            ipucu = u.degiskenler[f"{{ipucu_{dil}}}"].replace(u.dosya_yolu, "")
                            for tok in re.findall(r"\b([a-z_]+)=", ipucu):
                                self.assertIn(tok, icerik, f"{tok!r} dosyada yok: {ipucu[:120]}")
                            for tok in re.findall(r"\.([a-z_]{2,})\b", ipucu):
                                self.assertIn(tok, icerik, f".{tok} dosyada yok: {ipucu[:120]}")
                            for tok in re.findall(r'"([a-z_]+)"', ipucu):
                                self.assertIn(f'"{tok}"', icerik, f'"{tok}" dosyada yok: {ipucu[:120]}')
                            for tok in re.findall(r"=([a-z_]{3,})\b", ipucu):
                                self.assertIn(tok, icerik, f"=​{tok} dosyada yok")
                            if kod != "tr":
                                for yasak in ("tur=", "kaynak=", "hizmet=", '"kullanici"', '"parola"', ".kullanici"):
                                    self.assertNotIn(yasak, ipucu)
                        if kod != "tr":
                            for ad in KANONIK_ANAHTAR:
                                self.assertNotIn(f'"{ad}"', icerik)
                            self.assertNotIn("CAROTPOT kaynak=", icerik)
                    finally:
                        u.durdur()

    def test_cevap_dilden_bagimsiz(self):
        # Ayni varyant: cevap TÜRÜ aynı (IP / kullanıcı adı / sayı); dil yalnız alan adlarını değiştirir
        for kod in DILLER:
            u = uret("kullanici", 1, kod)
            try:
                self.assertTrue(u.dogru_cevap)
            finally:
                u.durdur()

    def test_tr_dosyasi_eski_bicimle_ayni_anahtarlar(self):
        u = uret("kullanici", 1, "tr")
        try:
            satir = open(u.dosya_yolu, encoding="utf-8").read().splitlines()[0]
            self.assertIn("CAROTPOT kaynak=", satir)
            self.assertIn('"kullanici"', satir)
        finally:
            u.durdur()


class GorevSirasindaDilTesti(unittest.TestCase):
    """Açık görev bozulmaz; yeni dil sonraki görevde etkili olur."""

    def test_dil_degisimi_acik_gorevi_bozmaz(self):
        import ogrenci_istemci as OI
        ist = OI.PoligonIstemci("", "", "", "bireysel")
        ist.zorluk = "kolay"
        try:
            ist.gorevi_yukle("loganaliz-05")
            ist.arayuz_dili = "de"
            ist.gorevi_baslat()
            self.assertEqual(ist.gorev_dili, "de")
            yol = ist.dosya_yolu
            once = open(yol, encoding="utf-8").read()
            ipucu_once = dict(ist.uretim_degiskenleri)
            self.assertIn("benutzername", once)

            # görev sürerken arayüz dili değişti: dosya ve komutlar aynı kalır
            ist.arayuz_dili = "en"
            self.assertEqual(open(yol, encoding="utf-8").read(), once)
            self.assertEqual(ist.uretim_degiskenleri, ipucu_once)
            self.assertEqual(ist.gorev_dili, "de")
            self.assertIn("typ=anmeldung", ist.uretim_degiskenleri["{ipucu_en}"])

            # sonraki görev yeni dille üretilir
            ist.gorevi_degistir("loganaliz-05")
            self.assertEqual(ist.gorev_dili, "en")
            yeni = open(ist.dosya_yolu, encoding="utf-8").read()
            self.assertIn("username", yeni)
            self.assertNotIn("benutzername", yeni)
        finally:
            ist.gorevi_durdur()


if __name__ == "__main__":
    unittest.main()
