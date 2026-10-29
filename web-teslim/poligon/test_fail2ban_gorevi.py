"""
fail2ban-01 gorevini GERCEK fail2ban ile test eder.

GEREKLI:
- fail2ban kurulu ve calisiyor olmali, 'sshd' jail'i etkin olmali.
- Gercek bir sudo-yetkili kullanici (`roottest` / `testsifre123`) OLARAK
  calistirilmali (bkz. test_ufw_gorevi.py'deki ayni aciklama).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ogrenci_istemci import PoligonIstemci  # noqa: E402

DOGRU_PAROLA = "testsifre123"


def main():
    istemci = PoligonIstemci("", "", "", "test_ogrencisi")
    gorev = istemci.gorevi_yukle("fail2ban-01")
    istemci.gorevi_baslat()  # bu gorevde yerel servis yok, sadece durum sifirlanir

    print("=== TEST 1: dogru parola ile durum okuma ===")
    basarili, mesaj = istemci.fail2ban_durumunu_dogrula(DOGRU_PAROLA)
    print(f"[TEST] Sonuc: {basarili}")
    print(mesaj)
    assert basarili is True, (
        "fail2ban durumu okunamadi -- 'sshd' jail'i etkin mi, "
        "fail2ban servisi calisiyor mu kontrol et"
    )
    assert "status for the jail" in mesaj.lower()
    print("OK: fail2ban durumu basariyla okundu")

    print("\n=== TEST 2: yanlis parola ===")
    basarili2, mesaj2 = istemci.fail2ban_durumunu_dogrula("kesinlikle-yanlis")
    assert basarili2 is False, "yanlis parola kabul edilmis gibi gorunuyor"
    print("OK: yanlis parola reddedildi")

    print("\n" + "=" * 70)
    print("SONUC: fail2ban-01 GOREVI TAM CALISIYOR")
    print("=" * 70)


if __name__ == "__main__":
    main()
