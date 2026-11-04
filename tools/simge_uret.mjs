// CarotOS uygulama simgeleri: tools/simge/*.svg kaynaklarindan tum cikti dosyalarini uretir.
//
// Kullanim (herhangi bir gecici klasorde bir kez `npm install sharp` yapin, sonra o klasorden):
//   node <depo>/tools/simge_uret.mjs <depo> [<site-deposu>]
// sharp, calisma klasorunun node_modules'inden yuklenir (depoya bagimlilik eklenmez).
//
// Uretilenler (<depo>/config/includes.chroot altinda):
//   usr/share/icons/hicolor/<boyut>x<boyut>/apps/carotene.png, carotpot.png   (16-256)
//   usr/share/icons/hicolor/256x256/apps/carotos-health.png, carotos-magaza.png
//   usr/share/icons/hicolor/scalable/apps/{filenor,carotos-former,carotos-gsd,carotos-health,carotos-magaza}.svg
//   opt/carotos/{filenor,former,gsd}/ikonlar.b64   (ISO derlemesinde hook'lar acar: "<boyut> <base64>")
//   opt/carotos/filenor/filenor_simge.py  (PNG_128), opt/carotos/magaza/carotos-magaza.py (LOGO_B64)
// ve site deposu verilirse public/ikonlar/ikon-*.webp (256 px).
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

const svg = (ad) => fs.readFileSync(path.join(kaynakDizini, ad + ".svg"));

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

// 1) hicolor PNG boyutlari (carotene, carotpot: tum boyutlar)
for (const [ad, hedef] of [["carotene", "carotene"], ["carotpot", "carotpot"]]) {
  for (const b of BOYUTLAR) yaz(path.join(hicolor, `${b}x${b}`, "apps", `${hedef}.png`), await png(ad, b));
}
// 2) yalniz 256 PNG
yaz(path.join(hicolor, "256x256", "apps", "carotos-health.png"), await png("saglik", 256));
yaz(path.join(hicolor, "256x256", "apps", "carotos-magaza.png"), await png("magaza", 256));
// 3) scalable SVG kopyalari
for (const [ad, hedef] of [["filenor", "filenor"], ["former", "carotos-former"], ["gsd", "carotos-gsd"],
                           ["saglik", "carotos-health"], ["magaza", "carotos-magaza"]]) {
  yaz(path.join(hicolor, "scalable", "apps", `${hedef}.svg`), svg(ad));
}
// 4) ISO'da hook'larin actigi gomulu PNG kaynaklari
for (const ad of ["filenor", "former", "gsd"]) {
  yaz(path.join(chroot, "opt", "carotos", ad, "ikonlar.b64"), await b64Satirlari(ad));
}

// 5) koda gomulu PNG'ler (satirlara bolunmus dize ya da tek dize)
function degistirGomulu(dosya, degisken, b64, bol) {
  const yol = path.join(chroot, "opt", "carotos", dosya);
  const metin = fs.readFileSync(yol, "utf-8");
  const desen = new RegExp(`(${degisken} = \\(\\r?\\n)((?:\\s*"[^"\\n]*"\\r?\\n)+)(\\))`);
  if (!desen.test(metin)) throw new Error(`${degisken} bulunamadi: ${dosya}`);
  const satirlar = bol ? b64.match(/.{1,100}/g) : [b64];
  const nl = metin.includes("\r\n") ? "\r\n" : "\n";
  const yeni = metin.replace(desen, (_, bas, __, son) =>
    bas + satirlar.map((s) => `    "${s}"`).join(nl) + nl + son);
  yaz(yol, yeni);
}
degistirGomulu("filenor/filenor_simge.py", "PNG_128", (await png("filenor", 128)).toString("base64"), true);
degistirGomulu("magaza/carotos-magaza.py", "LOGO_B64", (await png("magaza", 128)).toString("base64"), false);

// 6) site deposu: public/ikonlar/ikon-*.webp (256 px)
if (site) {
  const dizin = path.join(site, "public", "ikonlar");
  for (const [ad, hedef] of [["carotene", "carotene"], ["carotpot", "carotpot"], ["filenor", "filenor"],
                             ["former", "former"], ["gsd", "gsd"], ["magaza", "magaza"],
                             ["saglik", "sistem-sagligi"]]) {
    const buyuk = await sharp(svg(ad), { density: 144 }).resize(512, 512).png().toBuffer();
    const webp = await sharp(buyuk).resize(256, 256, { kernel: "lanczos3" }).webp({ quality: 92, effort: 6 }).toBuffer();
    yaz(path.join(dizin, `ikon-${hedef}.webp`), webp);
  }
}
console.log("tamam");
