// CarotOS uygulama simgeleri: tools/simge/*.svg kaynaklarindan tum cikti dosyalarini uretir.
//
// Kullanim (herhangi bir gecici klasorde bir kez `npm install sharp` yapin, sonra o klasorden):
//   node <depo>/tools/simge_uret.mjs <depo> [<site-deposu>]
// sharp, calisma klasorunun node_modules'inden yuklenir (depoya bagimlilik eklenmez).
//
// Yeni bir simge eklemek: tools/simge/<ad>.svg dosyasini koyup asagidaki TABLO'ya bir satir ekleyin.
// Kaynagi olmayan satirlar atlanir. Uretilenler (<depo>/config/includes.chroot altinda):
//   png      -> usr/share/icons/hicolor/<boyut>x<boyut>/apps/<png>.png (boyutlar: tum | 256); ekPng: ek konumlar
//   svg      -> usr/share/icons/hicolor/scalable/apps/<svg>.svg (kaynagin kopyasi)
//   b64      -> opt/carotos/<b64>/ikonlar.b64  (ISO derlemesinde hook'lar acar: "<boyut> <base64>")
//   kodPng   -> koda gomulu PNG (degisken adi ve dosya); site -> <site>/public/ikonlar/ikon-<site>.webp (256 px)
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(path.join(process.cwd(), "_"));
const sharp = require("sharp");

const depo = path.resolve(process.argv[2] || ".");
const site = process.argv[3] ? path.resolve(process.argv[3]) : null;
const kaynakDizini = path.join(depo, "tools", "simge");
const chroot = path.join(depo, "config", "includes.chroot");
const hicolor = path.join(chroot, "usr", "share", "icons", "hicolor");
const BOYUTLAR = [16, 22, 24, 32, 48, 64, 128, 256];

const TABLO = [
  { ad: "carotene", png: "carotene", boyutlar: "tum", site: "carotene" },
  { ad: "carotpot", png: "carotpot", boyutlar: "tum", site: "carotpot" },
  { ad: "saglik", png: "carotos-health", svg: "carotos-health", site: "sistem-sagligi" },
  { ad: "magaza", png: "carotos-magaza", svg: "carotos-magaza", site: "magaza",
    kodPng: { dosya: "magaza/carotos-magaza.py", degisken: "LOGO_B64", bol: false } },
  { ad: "filenor", svg: "filenor", b64: "filenor", site: "filenor",
    kodPng: { dosya: "filenor/filenor_simge.py", degisken: "PNG_128", bol: true } },
  { ad: "former", svg: "carotos-former", b64: "former", site: "former" },
  { ad: "gsd", svg: "carotos-gsd", b64: "gsd", site: "gsd" },
  { ad: "usb", png: "carotos-usb-check", svg: "carotos-usb-check", site: "usb-denetimi" },
  { ad: "poligon-ogrenci", png: "carotos-poligon-ogrenci", site: "poligon-ogrenci" },
  { ad: "poligon-ogretmen", png: "carotos-poligon-ogretmen", site: "poligon-ogretmen" },
  // Guvenlik Paneli: simge iki yerde tutulur (hicolor + uygulamanin kendi yedegi), ayni 256 px
  { ad: "panel", png: "carotos-security-panel", site: "guvenlik-paneli",
    ekPng: [{ yol: "usr/share/icons/carotos/security-panel-icon.png", boyut: 256 }] },
];

const kaynakYolu = (ad) => path.join(kaynakDizini, ad + ".svg");
const svg = (ad) => fs.readFileSync(kaynakYolu(ad));

// Once 512 px'e cizilir, sonra Lanczos ile kucultulur: kucuk boyutlarda daha net.
async function png(ad, boyut) {
  const buyuk = await sharp(svg(ad), { density: 144 }).resize(512, 512).png().toBuffer();
  return sharp(buyuk).resize(boyut, boyut, { kernel: "lanczos3" }).png({ compressionLevel: 9 }).toBuffer();
}

function yaz(yol, veri) {
  fs.mkdirSync(path.dirname(yol), { recursive: true });
  fs.writeFileSync(yol, veri);
  console.log("yazildi", path.relative(depo, yol));
}

const b64Satirlari = async (ad) =>
  (await Promise.all(BOYUTLAR.map(async (b) => `${b} ${(await png(ad, b)).toString("base64")}`))).join("\n") + "\n";

// Koda gomulu PNG (satirlara bolunmus dize ya da tek dize); satir sonu bicimini korur.
function degistirGomulu(dosya, degisken, b64, bol) {
  const yol = path.join(chroot, "opt", "carotos", dosya);
  const metin = fs.readFileSync(yol, "utf-8");
  const desen = new RegExp(`(${degisken} = \\(\\r?\\n)((?:\\s*"[^"\\n]*"\\r?\\n)+)(\\))`);
  if (!desen.test(metin)) throw new Error(`${degisken} bulunamadi: ${dosya}`);
  const satirlar = bol ? b64.match(/.{1,100}/g) : [b64];
  const nl = metin.includes("\r\n") ? "\r\n" : "\n";
  yaz(yol, metin.replace(desen, (_, bas, __, son) => bas + satirlar.map((s) => `    "${s}"`).join(nl) + nl + son));
}

for (const s of TABLO) {
  if (!fs.existsSync(kaynakYolu(s.ad))) { console.log("atlandi (kaynak yok):", s.ad); continue; }
  if (s.png) {
    for (const b of s.boyutlar === "tum" ? BOYUTLAR : [256]) {
      yaz(path.join(hicolor, `${b}x${b}`, "apps", `${s.png}.png`), await png(s.ad, b));
    }
  }
  for (const e of s.ekPng || []) yaz(path.join(chroot, e.yol), await png(s.ad, e.boyut));
  if (s.svg) yaz(path.join(hicolor, "scalable", "apps", `${s.svg}.svg`), svg(s.ad));
  if (s.b64) yaz(path.join(chroot, "opt", "carotos", s.b64, "ikonlar.b64"), await b64Satirlari(s.ad));
  if (s.kodPng) degistirGomulu(s.kodPng.dosya, s.kodPng.degisken, (await png(s.ad, 128)).toString("base64"), s.kodPng.bol);
  if (site && s.site) {
    const buyuk = await sharp(svg(s.ad), { density: 144 }).resize(512, 512).png().toBuffer();
    const webp = await sharp(buyuk).resize(256, 256, { kernel: "lanczos3" }).webp({ quality: 92, effort: 6 }).toBuffer();
    yaz(path.join(site, "public", "ikonlar", `ikon-${s.site}.webp`), webp);
  }
}
console.log("tamam");
