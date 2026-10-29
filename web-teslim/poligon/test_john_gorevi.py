"""
sahte_hash.py'yi GERCEK john ile test eder.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from servisler.sahte_hash import SahteHashDosyasi  # noqa: E402

DOGRU_PAROLA = "sifreleme1234"


def main():
    ortam = SahteHashDosyasi("ogrenci", DOGRU_PAROLA)
    ortam.baslat()
    print(f"Hash dosyası: {ortam.dosya_yolu}")
    print(f"İçerik: {Path(ortam.dosya_yolu).read_text().strip()}")

    import os as _os
    import shutil as _sh
    john_home = tempfile.mkdtemp(prefix="john-home-")
    john_ortam = dict(_os.environ, HOME=john_home)
    sozluk_yolu = None

    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("123456\npassword\nqwerty\n" + DOGRU_PAROLA + "\nadmin\n")
            sozluk_yolu = f.name

        print("\nGerçek john çalıştırılıyor...")
        sonuc = subprocess.run(
            ["john", "--format=md5crypt", f"--wordlist={sozluk_yolu}", ortam.dosya_yolu],
            capture_output=True, text=True, timeout=30, env=john_ortam,
        )
        print("--- john stdout ---")
        print(sonuc.stdout)
        if sonuc.stderr.strip():
            print("--- john stderr ---")
            print(sonuc.stderr)

        goster = subprocess.run(
            ["john", "--show", "--format=md5crypt", ortam.dosya_yolu],
            capture_output=True, text=True, timeout=15, env=john_ortam,
        )
        print("--- john --show çıktısı ---")
        print(goster.stdout)

        assert f"ogrenci:{DOGRU_PAROLA}" in goster.stdout, "john doğru parolayı bulamadı"
        print(f"✓ TEST GEÇTİ: john gerçekten parolayı buldu: {DOGRU_PAROLA}")

    finally:
        ortam.durdur()
        Path(sozluk_yolu).unlink(missing_ok=True)
        _sh.rmtree(john_home, ignore_errors=True)
        print(f"\nDosya silindi mi: {not Path(ortam.dosya_yolu).exists()}")


if __name__ == "__main__":
    main()
