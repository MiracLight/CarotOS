"""
ufw-01 gorevini GERCEK ufw ile test eder.

GEREKLI: gercek bir sudo-yetkili kullanici (`roottest` / `testsifre123`,
bkz. test_ogretmen_giris.py'deki ayni kullanici) OLARAK calistirilmali:

    su - roottest -c "cd /path/to/carotos-arena-hydra-poc && python3 test_ufw_gorevi.py"

Root olarak calistirirsan sudo zaten hep basarili doner, anlamsiz sonuc verir.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_istemci import PoligonIstemci, sudo_ile_calistir  # noqa: E402

DOGRU_PAROLA = "testsifre123"


def main():
    istemci = PoligonIstemci("", "", "", "test_ogrencisi")
    gorev = istemci.gorevi_yukle("ufw-01")
    istemci.gorevi_baslat()
    port = istemci.gercek_port
    print(f"[TEST] BasitDinleyici port {port}'te calisiyor")

    print("\n=== TEST 1: kural eklenmeden once ===")
    basarili, mesaj = istemci.ufw_kuralini_dogrula(DOGRU_PAROLA)
    print(f"[TEST] Sonuc: {basarili} -- {mesaj}")
    assert basarili is False, "kural henuz yokken 'basarili' donmemeli"
    print("OK: kural yokken dogru sekilde reddedildi")

    print(f"\n=== TEST 2: 'sudo ufw deny {port}' calistiriliyor ===")
    ok, cikti, hata = sudo_ile_calistir(["ufw", "deny", str(port)], DOGRU_PAROLA)
    assert ok, f"ufw deny calisamadi: {hata}"
    print(f"[TEST] ufw deny cikti: {cikti.strip()}")

    print("\n=== TEST 3: kural eklendikten sonra ===")
    basarili2, mesaj2 = istemci.ufw_kuralini_dogrula(DOGRU_PAROLA)
    print(f"[TEST] Sonuc: {basarili2} -- {mesaj2}")
    assert basarili2 is True, "kural eklendigi halde dogrulama basarisiz oldu"
    print("OK: kural eklendikten sonra dogru sekilde onaylandi")

    print("\n=== TEST 4: yanlis parola ===")
    basarili3, mesaj3 = istemci.ufw_kuralini_dogrula("kesinlikle-yanlis")
    assert basarili3 is False, "yanlis parola kabul edilmis gibi gorunuyor"
    print("OK: yanlis parola reddedildi")

    istemci.gorevi_durdur()
    subprocess.run(["sudo", "-S", "-k", "ufw", "delete", "deny", str(port)],
                    input=DOGRU_PAROLA + "\n", capture_output=True, text=True)

    print("\n" + "=" * 70)
    print("SONUC: ufw-01 GOREVI TAM CALISIYOR")
    print("=" * 70)


if __name__ == "__main__":
    main()
