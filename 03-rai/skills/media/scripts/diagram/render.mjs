#!/usr/bin/env node
// Render Excalidraw scene skeletons to .excalidraw.svg, the scene embedded.
//   node render.mjs <out-dir> <scene.json> ...
// Writes <out-dir>/<stem>.excalidraw.svg for each scene, and a preview PNG beside
// the scene, <stem>.png, for checking by eye.
// Runs Excalidraw itself (esm.sh) in headless Chromium: no window opens.
// First run installs puppeteer-core into ~/.cache/rai-diagram/node.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";

const CACHE = path.join(os.homedir(), ".cache", "rai-diagram");
const NODE = path.join(CACHE, "node");
const EXCALIDRAW = "https://esm.sh/@excalidraw/excalidraw@0.18.1";
const BROWSERS = [process.env.CHROME, "/usr/bin/chromium", "/usr/bin/google-chrome-stable",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"].filter(Boolean);

const [outDir, ...scenes] = process.argv.slice(2);
if (!scenes.length) {
  console.error("usage: node render.mjs <out-dir> <scene.json> ...");
  process.exit(2);
}
if (!fs.existsSync(path.join(NODE, "node_modules", "puppeteer-core"))) {
  fs.mkdirSync(NODE, { recursive: true });
  execFileSync("npm", ["install", "--prefix", NODE, "puppeteer-core@24"], { stdio: "inherit" });
}
const puppeteer = createRequire(path.join(NODE, "package.json"))("puppeteer-core");
const executablePath = BROWSERS.find((p) => fs.existsSync(p));
if (!executablePath) throw new Error("no Chromium found: set CHROME=/path/to/chrome");

const browser = await puppeteer.launch({ executablePath, headless: true, });
const page = await browser.newPage();
page.on("pageerror", (e) => console.error("pageerror:", e.message));
await page.setContent(`<!doctype html><html><head><meta charset="utf-8">
<script>window.EXCALIDRAW_ASSET_PATH="${EXCALIDRAW}/dist/prod/";</script>
<script type="module">import * as EX from "${EXCALIDRAW}"; window.EX = EX; window.ready = true;</script>
</head><body></body></html>`);
await page.waitForFunction("window.ready === true", { timeout: 120000 });
await page.evaluate(async () => {
  for (const f of ["Excalifont", "Nunito", "Cascadia"]) {
    try { await document.fonts.load(`20px "${f}"`); } catch {}
  }
});
const view = await browser.newPage();
await view.setViewport({ width: 800, height: 600, deviceScaleFactor: 1 });

for (const file of scenes) {
  const scene = JSON.parse(fs.readFileSync(file, "utf8"));
  const svg = await page.evaluate(async (scene) => {
    const elements = window.EX.convertToExcalidrawElements(scene.skeleton, { regenerateIds: false });
    const appState = { exportBackground: true, viewBackgroundColor: scene.background,
      exportEmbedScene: true };
    return (await window.EX.exportToSvg({ elements, appState, files: scene.files })).outerHTML;
  }, scene);
  const stem = path.basename(file, ".json");
  const out = path.join(outDir, `${stem}.excalidraw.svg`);
  fs.writeFileSync(out, svg);
  await view.setContent(`<html><body style="margin:0">${svg}</body></html>`);
  await new Promise((r) => setTimeout(r, 800));
  const box = await (await view.$("svg")).boundingBox();
  const preview = path.join(path.dirname(file), `${stem}.png`);
  await view.screenshot({ path: preview, clip: box });
  console.log(`${out}  (preview: ${preview})`);
}
await browser.close();
