"""
sahte_giris servisini GERCEKTEN calistirip GERCEK hydra ile saldirtir.
Tahmin degil, olcum.
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from servisler.sahte_giris import SahteGirisServisi  # noqa: E402

PORT = 2222
KULLANICI = "ogrenci"
DOGRU_PAROLA = "carot2026"


def test_hydra_dogru_parolayi_buluyor_mu():
    servis = SahteGirisServisi(KULLANICI, DOGRU_PAROLA, PORT)
    servis.baslat()
    time.sleep(0.3)

    try:
        # Dogru parola listenin ortasina gizlenmis, tesadufen ilk denemede
        # bulunmadigindan emin olmak icin -- gercekci bir sozluk saldirisi.
        parolalar = ["123456", "password", "qwerty", DOGRU_PAROLA, "admin", "letmein"]
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("\n".join(parolalar) + "\n")
            wordlist_yolu = f.name

        komut = [
            "hydra", "-l", KULLANICI, "-P", wordlist_yolu,
            "-s", str(PORT), "-t", "4", "127.0.0.1", "ftp",
        ]
        print("Calistirilan komut:", " ".join(komut))
        sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=30)

        print("\n--- hydra stdout ---")
        print(sonuc.stdout)
        if sonuc.stderr.strip():
            print("--- hydra stderr ---")
            print(sonuc.stderr)

        basarili_satir = [
            s for s in sonuc.stdout.splitlines() if "login:" in s and "password:" in s
        ]
        bulundu = any(DOGRU_PAROLA in s for s in basarili_satir)

        print("\nSONUC:")
        print("  hydra bir kimlik bilgisi buldu mu:", bool(basarili_satir))
        print("  bulunan dogru parola mi:", bulundu)
        if basarili_satir:
            print("  bulunan satir:", basarili_satir[0])

        assert bulundu, "hydra dogru parolayi BULAMADI -- servis hatali calisiyor"
        print("\n✓ TEST GECTI: hydra gercekten dogru parolayi buldu")

    finally:
        servis.durdur()
        Path(wordlist_yolu).unlink(missing_ok=True)


def test_yanlis_parola_reddediliyor_mu():
    """Sadece dogru parolanin kabul edildigini, baskalarinin edilmedigini dogrular."""
    servis = SahteGirisServisi(KULLANICI, DOGRU_PAROLA, PORT + 1)
    servis.baslat()
    time.sleep(0.3)
    try:
        import socket
        s = socket.socket()
        s.connect(("127.0.0.1", PORT + 1))
        s.recv(100)  # banner
        s.sendall(f"USER {KULLANICI}\r\n".encode())
        s.recv(100)
        s.sendall(b"PASS yanlisparola\r\n")
        cevap = s.recv(100).decode()
        s.close()
        print("Yanlis parola cevabi:", cevap.strip())
        assert "530" in cevap, "yanlis parola KABUL EDILDI -- guvenlik hatasi"
        print("✓ TEST GECTI: yanlis parola dogru sekilde reddedildi")
    finally:
        servis.durdur()


def test_guvenlik_kurali_kod_seviyesinde_zorunlu_mu():
    """bind_adres 127.0.0.1 disinda bir sey olursa servis olusturulamamali."""
    try:
        SahteGirisServisi(KULLANICI, DOGRU_PAROLA, PORT + 2, bind_adres="0.0.0.0")
        print("✗ TEST BASARISIZ: 0.0.0.0 ile servis olusturulabildi!")
        assert False, "guvenlik kurali kod seviyesinde uygulanmiyor"
    except ValueError as e:
        print("Beklenen hata dogru sekilde firlatildi:", e)
        print("✓ TEST GECTI: kod seviyesinde de bind_adres kisitlamasi zorunlu")


if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: hydra gercekten dogru parolayi buluyor mu")
    print("=" * 70)
    test_hydra_dogru_parolayi_buluyor_mu()

    print()
    print("=" * 70)
    print("TEST 2: yanlis parola reddediliyor mu")
    print("=" * 70)
    test_yanlis_parola_reddediliyor_mu()

    print()
    print("=" * 70)
    print("TEST 3: guvenlik kurali kod seviyesinde zorunlu mu")
    print("=" * 70)
    test_guvenlik_kurali_kod_seviyesinde_zorunlu_mu()

    print()
    print("TUM TESTLER GECTI")
