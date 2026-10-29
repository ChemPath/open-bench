// Drive web/chemical-space.html in headless Chromium and report what rendered.
//
// Usage: node tests/web/explorer_check.js <page.html> <out.json> [screenshot_dir]
"use strict";
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const [pagePath, outPath, shotDir] = process.argv.slice(2);
  const browser = await chromium.launch();
  const out = { errors: [] };
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    page.on("pageerror", (e) => out.errors.push(String(e)));
    page.on("console", (m) => { if (m.type() === "error") out.errors.push(m.text()); });
    await page.goto("file://" + pagePath);
    await page.waitForSelector("#chart circle.hit");

    out.hits = await page.locator("#chart circle.hit").count();
    out.highlighted = await page.locator("#chart circle.pt.hi").count();
    out.hollow = await page.locator("#chart circle.pt.hollow").count();
    out.multiples = await page.locator("#multiples .mini").count();
    out.rows = await page.locator("#table tbody tr").count();
    out.detail_name = (await page.textContent("#detail h3")).trim();
    out.region_on_pca = await page.locator("#chart rect.region").count();

    await page.click('[data-view="logp,tpsa"]');
    out.region_on_logp_tpsa = await page.locator("#chart rect.region").count();
    out.region_label = (await page.textContent("#chart .region-label")).trim();

    await page.fill("#find", "Quercetin");
    await page.dispatchEvent("#find", "change");
    out.after_find = {
      detail: (await page.textContent("#detail h3")).trim(),
      family: await page.evaluate(() => window.OpenBenchExplorer.state.family),
      url: await page.evaluate(() => location.search),
    };

    await page.click("#detail [data-go]");
    out.after_neighbor = (await page.textContent("#detail h3")).trim();

    await page.click('#table th button[data-sort="mw"]');
    out.first_by_mw = (await page.textContent("#table tbody tr:first-child td:first-child")).trim();

    await page.click('#multiples .mini:nth-child(6)');
    out.family_after_mini = await page.evaluate(() => window.OpenBenchExplorer.state.family);

    if (shotDir) {
      await page.evaluate(() => { window.OpenBenchExplorer.state.x = "pc1"; window.OpenBenchExplorer.state.y = "pc2"; window.OpenBenchExplorer.select("CBD", true); window.scrollTo(0, 0); });
      await page.screenshot({ path: path.join(shotDir, "explorer-light.png"), fullPage: true });
    }
    await page.close();

    const restored = await browser.newPage({ viewport: { width: 1280, height: 900 }, colorScheme: "dark" });
    restored.on("pageerror", (e) => out.errors.push(String(e)));
    await restored.goto("file://" + pagePath + "?x=mw&y=logp&family=Flavonoid&c=Apigenin");
    await restored.waitForSelector("#chart circle.hit");
    out.url_restore = await restored.evaluate(() => ({ ...window.OpenBenchExplorer.state }));
    if (shotDir) await restored.screenshot({ path: path.join(shotDir, "explorer-dark.png"), fullPage: false });
    await restored.close();

    const mobile = await browser.newPage({ viewport: { width: 375, height: 800 } });
    await mobile.goto("file://" + pagePath);
    await mobile.waitForSelector("#chart circle.hit");
    out.mobile_overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    if (shotDir) await mobile.screenshot({ path: path.join(shotDir, "explorer-mobile.png"), fullPage: true });
    await mobile.close();
  } finally {
    await browser.close();
  }
  fs.writeFileSync(outPath, JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
