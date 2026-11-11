#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Panel saatinin zaman dilimi eslestirmesi (carotos-saat-eslestir). xfconf-query ve timedatectl taklit edilir.

Calistirma (Linux/WSL):  python3 tests/test_saat_eslestir.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INC = os.path.join(KOK, "config", "includes.chroot")
BETIK = os.path.join(INC, "usr", "local", "bin", "carotos-saat-eslestir")
SH = shutil.which("sh")

XFCONF_TAKLIT = r"""#!/bin/sh
# basit anahtar=deger deposu: $DEPO ("anahtar\tdeger" satirlari)
anahtar=""; deger=""; liste=0; yeni=0
while [ $# -gt 0 ]; do
  case "$1" in
    -c) shift;;
    -l) liste=1;;
    -p) anahtar="$2"; shift;;
    -n) yeni=1;;
    -t) shift;;
    -s) deger="$2"; shift; atama=1;;
  esac
  shift
done
if [ "$liste" = 1 ]; then cut -f1 "$DEPO"; exit 0; fi
if [ "${atama:-0}" = 1 ]; then
  grep -v -P "^\Q$anahtar\E\t" "$DEPO" > "$DEPO.yeni" 2>/dev/null; mv "$DEPO.yeni" "$DEPO"
  printf '%s\t%s\n' "$anahtar" "$deger" >> "$DEPO"; exit 0
fi
satir=$(grep -P "^\Q$anahtar\E\t" "$DEPO" | head -1)
[ -n "$satir" ] || exit 1
printf '%s\n' "${satir#*	}"
"""


@unittest.skipUnless(SH and os.path.isdir("/usr/share/zoneinfo/Europe") and os.name == "posix",
                     "Linux ve zoneinfo gerekir")
class SaatEslestirTesti(unittest.TestCase):
    def kur(self, depo_satirlari, dilim="Europe/Istanbul", isaret=None):
        self.kok = tempfile.mkdtemp(prefix="saat-")
        self.addCleanup(shutil.rmtree, self.kok, True)
        bin_ = os.path.join(self.kok, "bin")
        os.makedirs(bin_)
        with open(os.path.join(bin_, "xfconf-query"), "w") as f:
            f.write(XFCONF_TAKLIT)
        with open(os.path.join(bin_, "timedatectl"), "w") as f:
            f.write(f"#!/bin/sh\necho '{dilim}'\n")
        for ad in ("xfconf-query", "timedatectl"):
            os.chmod(os.path.join(bin_, ad), 0o755)
        self.depo = os.path.join(self.kok, "depo")
        with open(self.depo, "w") as f:
            f.write("".join(f"{k}\t{v}\n" for k, v in depo_satirlari))
        self.cfg = os.path.join(self.kok, "cfg")
        if isaret is not None:
            os.makedirs(os.path.join(self.cfg, "carotos"))
            with open(os.path.join(self.cfg, "carotos", "saat-dilimi"), "w") as f:
                f.write(isaret + "\n")

    def calistir(self):
        env = dict(os.environ, PATH=os.path.join(self.kok, "bin") + ":" + os.environ["PATH"],
                   DEPO=self.depo, XDG_CONFIG_HOME=self.cfg, HOME=self.kok)
        s = subprocess.run([SH, BETIK], env=env, capture_output=True, timeout=60)
        self.assertEqual(s.returncode, 0, s.stderr.decode())
        veri = {}
        for satir in open(self.depo).read().splitlines():
            k, _, v = satir.partition("\t")
            veri[k] = v
        return veri

    def isaret(self):
        yol = os.path.join(self.cfg, "carotos", "saat-dilimi")
        return open(yol).read().strip() if os.path.exists(yol) else None

    def test_bos_dilim_sistem_dilimine_ayarlanir(self):
        self.kur([("/plugins/plugin-8", "clock"), ("/plugins/plugin-8/mode", "2"), ("/plugins/plugin-2", "tasklist")])
        v = self.calistir()
        self.assertEqual(v["/plugins/plugin-8/timezone"], "Europe/Istanbul")
        self.assertNotIn("/plugins/plugin-2/timezone", v)          # saat olmayan eklentiye dokunulmaz
        self.assertEqual(self.isaret(), "Europe/Istanbul")

    def test_betigin_yazdigi_eski_deger_guncellenir(self):
        self.kur([("/plugins/plugin-8", "clock"), ("/plugins/plugin-8/timezone", "UTC")], dilim="Europe/Istanbul", isaret="UTC")
        self.assertEqual(self.calistir()["/plugins/plugin-8/timezone"], "Europe/Istanbul")

    def test_kullanicinin_sectigi_baska_sehir_ezilmez(self):
        self.kur([("/plugins/plugin-8", "clock"), ("/plugins/plugin-8/timezone", "America/New_York")], isaret="Europe/Istanbul")
        self.assertEqual(self.calistir()["/plugins/plugin-8/timezone"], "America/New_York")

    def test_birden_cok_saat(self):
        self.kur([("/plugins/plugin-8", "clock"), ("/plugins/plugin-9", "clock")])
        v = self.calistir()
        self.assertEqual(v["/plugins/plugin-8/timezone"], "Europe/Istanbul")
        self.assertEqual(v["/plugins/plugin-9/timezone"], "Europe/Istanbul")

    def test_gecersiz_dilim_adlari_yazilmaz(self):
        for kotu in ("../etc/passwd", "Europe/Yok Boyle", "/etc/passwd", "Yok/Boyle", "a;rm -rf x"):
            with self.subTest(dilim=kotu):
                self.kur([("/plugins/plugin-8", "clock")], dilim=kotu)
                self.assertNotIn("/plugins/plugin-8/timezone", self.calistir())

    def test_izle_kipi_dilim_degisince_paneli_gunceller(self):
        """Oturum sirasinda dilim degisirse eklentiyi kaldirip eklemeye gerek kalmadan panel guncellenir."""
        import time
        self.kur([("/plugins/plugin-8", "clock")])
        dilim_dosyasi = os.path.join(self.kok, "dilim")
        with open(dilim_dosyasi, "w") as f:
            f.write("Europe/Istanbul\n")
        with open(os.path.join(self.kok, "bin", "timedatectl"), "w") as f:
            f.write(f"#!/bin/sh\ncat '{dilim_dosyasi}'\n")
        izlenen = os.path.join(self.kok, "localtime")
        os.symlink("/usr/share/zoneinfo/Europe/Istanbul", izlenen)
        env = dict(os.environ, PATH=os.path.join(self.kok, "bin") + ":" + os.environ["PATH"],
                   DEPO=self.depo, XDG_CONFIG_HOME=self.cfg, HOME=self.kok,
                   CAROTOS_SAAT_IZLENEN=izlenen, CAROTOS_SAAT_ARALIK="1")
        surec = subprocess.Popen([SH, BETIK, "--izle"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: (surec.kill(), surec.wait()))

        def deger():
            for satir in open(self.depo).read().splitlines():
                k, _, v = satir.partition("\t")
                if k == "/plugins/plugin-8/timezone":
                    return v
            return None

        def bekle(beklenen):
            son = time.time() + 10
            while time.time() < son:
                if deger() == beklenen:
                    return True
                time.sleep(0.2)
            return False

        self.assertTrue(bekle("Europe/Istanbul"), deger())
        self.assertIsNone(surec.poll(), "izleme kipi hemen cikmamali")
        with open(dilim_dosyasi, "w") as f:
            f.write("Europe/Berlin\n")
        os.remove(izlenen)
        os.symlink("/usr/share/zoneinfo/Europe/Berlin", izlenen)       # timedatectl set-timezone boyle yapar
        self.assertTrue(bekle("Europe/Berlin"), deger())
        self.assertEqual(self.isaret(), "Europe/Berlin")

    def test_zaten_dogruysa_degismez(self):
        self.kur([("/plugins/plugin-8", "clock"), ("/plugins/plugin-8/timezone", "Europe/Istanbul")], isaret=None)
        self.assertEqual(self.calistir()["/plugins/plugin-8/timezone"], "Europe/Istanbul")


class DosyaTesti(unittest.TestCase):
    def test_betik_sozdizimi_ve_shebang(self):
        veri = open(BETIK, "rb").read()
        self.assertTrue(veri.startswith(b"#!/bin/sh\n"))
        self.assertNotIn(b"\r\n", veri)
        if SH:
            self.assertEqual(subprocess.run([SH, "-n", BETIK], capture_output=True).returncode, 0)

    def test_autostart_ve_hook_ve_paket(self):
        desk = open(os.path.join(INC, "etc", "skel", ".config", "autostart", "carotos-saat-eslestir.desktop"),
                    encoding="utf-8").read()
        self.assertIn("Exec=/usr/local/bin/carotos-saat-eslestir --izle", desk)
        hook = open(os.path.join(KOK, "config", "hooks", "live", "9999-carotos-setup.hook.chroot"), encoding="utf-8").read()
        self.assertIn("chmod 755 /usr/local/bin/carotos-saat-eslestir", hook)
        paketler = open(os.path.join(KOK, "config", "package-lists", "carotos.list.chroot"), encoding="utf-8").read().split()
        self.assertIn("systemd-timesyncd", paketler)


if __name__ == "__main__":
    unittest.main()
