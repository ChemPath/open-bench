// Load web/index.html in headless Chromium with RDKit.js replaced by a stub,
// run analyzeFormulation() on each payload, and write the results as JSON.
//
// Usage: node tests/web/browser_check.js <job.json> <out.json> [screenshot_dir]
// job.json: { "page": "<abs path>", "stub": "<stub js source>", "payloads": [...] }
"use strict";
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const [jobPath, outPath, shotDir] = process.argv.slice(2);
  const job = JSON.parse(fs.readFileSync(jobPath, "utf8"));
  const browser = await chromium.launch();
  const out = { results: [], console_errors: [] };
  try {
    for (const scheme of ["light", "dark"]) {
      const page = await browser.newPage({ viewport: { width: 1200, height: 900 }, colorScheme: scheme });
      page.on("pageerror", (e) => out.console_errors.push(String(e)));
      page.on("console", (m) => { if (m.type() === "error") out.console_errors.push(m.text()); });
      await page.route(/RDKit_minimal\.js$/, (r) => r.fulfill({ contentType: "text/javascript", body: job.stub }));
      await page.goto("file://" + job.page);
      await page.waitForFunction(() => !document.getElementById("analyze").disabled, null, { timeout: 15000 });
      await page.waitForSelector("#results .card");
      if (scheme === "light") {
        out.boot_status = await page.textContent("#results .status");
        for (const p of job.payloads) {
          out.results.push(await page.evaluate((payload) => {
            try {
              const r = window.ChemPathDemo.analyzeFormulation(payload);
              for (const e of r.entries) delete e._svg;
              return { ok: r };
            } catch (err) {
              return { error: err.message, http_status: err.httpStatus };
            }
          }, p));
        }
        await page.click('[data-preset="partial"]');
        await page.click("#analyze");
        out.partial_cards = await page.locator("#results .card").count();
        out.partial_missing = await page.locator("#results .card.missing").count();
      }
      if (shotDir) {
        await page.click('[data-preset="full"]');
        await page.click("#analyze");
        await page.screenshot({ path: path.join(shotDir, `page-${scheme}.png`), fullPage: true });
      }
      await page.close();
    }
    const mobile = await browser.newPage({ viewport: { width: 375, height: 800 } });
    await mobile.route(/RDKit_minimal\.js$/, (r) => r.fulfill({ contentType: "text/javascript", body: job.stub }));
    await mobile.goto("file://" + job.page);
    await mobile.waitForSelector("#results .card");
    out.mobile_overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    if (shotDir) await mobile.screenshot({ path: path.join(shotDir, "page-mobile.png"), fullPage: true });
  } finally {
    await browser.close();
  }
  fs.writeFileSync(outPath, JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
