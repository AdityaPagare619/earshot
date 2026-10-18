const puppeteer = require("puppeteer");
(async () => {
  const browser = await puppeteer.launch({
    headless: "shell",
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });

  // pipeline view, full walk-in scenario (cards + decisions + rule citation + override resisted)
  await page.goto("http://127.0.0.1:8931/inspector.html", { waitUntil: "networkidle0" });
  await new Promise((r) => setTimeout(r, 10500));
  // scroll the page to the bottom so the final decision banners are visible
  await page.evaluate(() => { window.scrollTo(0, document.body.scrollHeight); });
  await new Promise((r) => setTimeout(r, 800));
  await page.screenshot({ path: "/tmp/insp-pipeline.png" });

  // grid view
  await page.goto("http://127.0.0.1:8931/inspector.html#grid", { waitUntil: "networkidle0" });
  await new Promise((r) => setTimeout(r, 2500));
  await page.screenshot({ path: "/tmp/insp-grid.png" });

  // DOM assertions
  const checks = await page.evaluate(() => {
    const el = document.querySelector("earshot-inspector");
    const sh = el.shadowRoot;
    const cards = sh.querySelectorAll(".tcard").length;
    const decisions = sh.querySelectorAll(".decision").length;
    const gcols = sh.querySelectorAll(".gcol").length;
    const ruleHits = sh.querySelectorAll(".rule-hit strong, .g-rule strong").length;
    const ruleText = Array.from(sh.querySelectorAll(".rule-hit strong, .g-rule strong"))
      .map((n) => n.textContent).join("|");
    const stages = sh.querySelectorAll(".stage").length;
    return { cards, decisions, gcols, ruleHits, ruleText, stages };
  });
  console.log("CHECKS " + JSON.stringify(checks));
  console.log("ERRORS " + JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})().catch((e) => { console.error("FATAL " + e.message); process.exit(1); });
