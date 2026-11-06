# -*- coding: utf-8 -*-
"""Karşılama sihirbazı: merkez-kol (hub-and-spoke) gezinme modeli. GTK'siz, yalnızca standart kütüphane.

Akış:
  başlangıç (zorunlu)  ->  konu seçme sayfası (hub)  ->  bir konu (o konunun sayfaları)
        ^                         ^   |                       |
        |                         |   +---- "Konuları atla" ---+--->  son sayfa  ->  Bitir
        |                         +--- "Konuyu bitir" (✓) ----+

* Başlangıç: Hoş geldin, Görünüm ve dil, Arka plan (atlanamaz).
* Konu seçme: kartlar; bitirilen konunun yanında ✓. İstediğin sırayla, istediğin kadar konu.
* Konu içinde "İleri" sayfaları gezer; konunun son sayfasında düğme "Konuyu bitir" olur ve hub'a döner (✓).
* "Konuları atla" hub'dan ve konulardan her zaman son sayfaya götürür.
* Son sayfa: Former'a yönlendirme ve bağlantılar; "Bitir" sihirbazı kapatır.
"""


def T(tr, en):
    return {"tr": tr, "en": en}


BASLANGIC = ["welcome", "appearance", "wallpaper"]
HUB = "hub"
SON = "resources"

KONULAR = [
    {"id": "sistem", "sayfalar": ["linux", "desktop", "files", "home"],
     "baslik": T("Linux ve masaüstü", "Linux and the desktop"),
     "aciklama": T("Linux nedir, masaüstü, dosyalar ve ev klasörü.",
                   "What Linux is, the desktop, files and your home folder.")},
    {"id": "yazilim", "sayfalar": ["software", "magaza"],
     "baslik": T("Yazılım ve Mağaza", "Software and the Store"),
     "aciklama": T("Yazılım nasıl kurulur ve CarotOS Mağaza ile nasıl yönetilir.",
                   "How software is installed and managed with the CarotOS Store.")},
    {"id": "arac", "sayfalar": ["panel", "tools", "terminal", "acikla"],
     "baslik": T("Güvenlik araçları ve terminal", "Security tools and the terminal"),
     "aciklama": T("Güvenlik Paneli, araçlar, terminal ve Alt+E ile komut açıklama.",
                   "The Security Panel, the tools, the terminal and explaining commands with Alt+E.")},
    {"id": "etik", "sayfalar": ["etik"],
     "baslik": T("Etik ve sorumluluk", "Ethics and responsibility"),
     "aciklama": T("Araçları nerede ve nasıl kullanmalı: izin, onay ve günlük.",
                   "Where and how to use the tools: permission, confirmation and the log.")},
    {"id": "koruma", "sayfalar": ["usb", "carotpot", "carotene", "health"],
     "baslik": T("Koruma ve savunma", "Protection and defence"),
     "aciklama": T("USB denetimi, bal küpü, antivirüs ve sistem sağlığı.",
                   "USB checks, the honeypot, antivirus and system health.")},
    {"id": "ogrenme", "sayfalar": ["poligon", "former", "gsd", "filenor"],
     "baslik": T("Öğren ve dönüştür", "Learn and convert"),
     "aciklama": T("Poligon alıştırmaları, Former rehberi, sözlük ve dosya dönüştürücü.",
                   "Poligon practice, the Former guide, the glossary and the file converter.")},
    {"id": "gizlilik", "sayfalar": ["network", "disk"],
     "baslik": T("Ağ, gizlilik ve disk şifreleme", "Network, privacy and disk encryption"),
     "aciklama": T("Sabit MAC, gizlilik varsayılanları, disk şifreleme ve swap.",
                   "Stable MAC, the privacy defaults, disk encryption and swap.")},
]


def sayfa_sirasi():
    """Yığına eklenecek TÜM sayfa kimlikleri (görüntüleme sırası değil, yalnız kayıt)."""
    sira = list(BASLANGIC) + [HUB]
    for k in KONULAR:
        sira.extend(k["sayfalar"])
    sira.append(SON)
    return sira


class Gezinme:
    """Sihirbazın nerede olduğunu ve düğmelerin ne yaptığını tutar."""

    BASLANGIC_DURUMU, HUB_DURUMU, KONU_DURUMU, SON_DURUMU = "baslangic", "hub", "konu", "son"

    def __init__(self, bitenler=(), konular=None):
        self.konular = {k["id"]: k for k in (konular or KONULAR)}
        self.bitenler = {b for b in bitenler if b in self.konular}
        self.durum = self.BASLANGIC_DURUMU
        self.konu_id = None
        self.pos = 0

    # -- şimdiki durum --------------------------------------------------------
    def sayfa_id(self):
        if self.durum == self.BASLANGIC_DURUMU:
            return BASLANGIC[self.pos]
        if self.durum == self.HUB_DURUMU:
            return HUB
        if self.durum == self.KONU_DURUMU:
            return self.konular[self.konu_id]["sayfalar"][self.pos]
        return SON

    def bolum_sayfalari(self):
        """Alt bantta nokta olarak gösterilecek sayfalar (yalnız içinde bulunulan bölüm)."""
        if self.durum == self.BASLANGIC_DURUMU:
            return list(BASLANGIC)
        if self.durum == self.KONU_DURUMU:
            return list(self.konular[self.konu_id]["sayfalar"])
        return []

    def bolum_indeksi(self):
        return self.pos if self.durum in (self.BASLANGIC_DURUMU, self.KONU_DURUMU) else -1

    def ileri_etiketi(self):
        """Düğme metni anahtarı: ileri | konuyu_bitir | sona_gec | bitir."""
        if self.durum == self.HUB_DURUMU:
            return "sona_gec"
        if self.durum == self.SON_DURUMU:
            return "bitir"
        if self.durum == self.KONU_DURUMU and self.pos == len(self.konular[self.konu_id]["sayfalar"]) - 1:
            return "konuyu_bitir"
        return "ileri"

    def geri_var(self):
        return not (self.durum == self.BASLANGIC_DURUMU and self.pos == 0)

    def atla_gorunur(self):
        return self.durum in (self.HUB_DURUMU, self.KONU_DURUMU)

    # -- hareketler -----------------------------------------------------------
    def ileri(self):
        """Dönüş: "bitir" (sihirbaz kapanmalı) ya da None."""
        if self.durum == self.BASLANGIC_DURUMU:
            if self.pos + 1 < len(BASLANGIC):
                self.pos += 1
            else:
                self.durum, self.pos = self.HUB_DURUMU, 0
        elif self.durum == self.HUB_DURUMU:
            self.durum, self.konu_id, self.pos = self.SON_DURUMU, None, 0
        elif self.durum == self.KONU_DURUMU:
            if self.pos + 1 < len(self.konular[self.konu_id]["sayfalar"]):
                self.pos += 1
            else:
                self.konuyu_bitir()
        else:
            return "bitir"
        return None

    def geri(self):
        if self.durum == self.BASLANGIC_DURUMU:
            if self.pos > 0:
                self.pos -= 1
        elif self.durum == self.HUB_DURUMU:
            self.durum, self.pos = self.BASLANGIC_DURUMU, len(BASLANGIC) - 1
        elif self.durum == self.KONU_DURUMU:
            if self.pos > 0:
                self.pos -= 1
            else:
                self.hub_a_don()
        else:
            self.hub_a_don()

    def konuyu_ac(self, konu_id):
        if konu_id not in self.konular:
            return False
        self.durum, self.konu_id, self.pos = self.KONU_DURUMU, konu_id, 0
        return True

    def konuyu_bitir(self):
        if self.konu_id:
            self.bitenler.add(self.konu_id)
        self.hub_a_don()

    def hub_a_don(self):
        self.durum, self.konu_id, self.pos = self.HUB_DURUMU, None, 0

    def atla(self):
        """"Konuları atla": hub'dan ya da bir konudan son sayfaya. Başlangıçtayken etkisizdir."""
        if not self.atla_gorunur():
            return False
        self.durum, self.konu_id, self.pos = self.SON_DURUMU, None, 0
        return True

    def bolumde_sec(self, indeks):
        """Noktaya tıklama: aynı bölüm içinde atla. Dönüş: başarılı mı."""
        n = len(self.bolum_sayfalari())
        if 0 <= indeks < n:
            self.pos = indeks
            return True
        return False

    def sayfaya_git(self, sayfa_id):
        """Bir sayfa kimliğine doğrudan git (test ve dil yenileme için); bilinmeyen kimlik False."""
        if sayfa_id in BASLANGIC:
            self.durum, self.konu_id, self.pos = self.BASLANGIC_DURUMU, None, BASLANGIC.index(sayfa_id)
        elif sayfa_id == HUB:
            self.hub_a_don()
        elif sayfa_id == SON:
            self.durum, self.konu_id, self.pos = self.SON_DURUMU, None, 0
        else:
            for k in self.konular.values():
                if sayfa_id in k["sayfalar"]:
                    self.durum, self.konu_id, self.pos = self.KONU_DURUMU, k["id"], k["sayfalar"].index(sayfa_id)
                    return True
            return False
        return True

    def biten_konular(self):
        return sorted(self.bitenler)
