import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import http from "node:http";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = "C:\\Projetos\\lojadepaes\\readme\\evidence\\prompt-91c";
const port = 9343;

mkdirSync(OUT, { recursive: true });

function get(url) {
  return new Promise((resolve, reject) => {
    http
      .get(url, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => resolve(data));
      })
      .on("error", reject);
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function captureViewport(label, width, height) {
  const chrome = spawn(
    CHROME,
    [
      `--remote-debugging-port=${port}`,
      "--headless=new",
      "--disable-gpu",
      "--no-first-run",
      `--user-data-dir=C:\\Temp\\chrome-p91c-${label}`,
      `--window-size=${width},${height}`,
      "https://lojadepaes.com.br/",
    ],
    { stdio: "ignore" },
  );
  try {
    let wsUrl;
    for (let i = 0; i < 40; i += 1) {
      try {
        wsUrl = JSON.parse(await get(`http://127.0.0.1:${port}/json/version`)).webSocketDebuggerUrl;
        break;
      } catch {
        await sleep(250);
      }
    }
    const pages = JSON.parse(await get(`http://127.0.0.1:${port}/json/list`));
    const page = pages.find((item) => item.type === "page") || pages[0];
    const socket = new WebSocket(page.webSocketDebuggerUrl || wsUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve);
      socket.addEventListener("error", reject);
    });
    let id = 0;
    const pending = new Map();
    socket.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && pending.has(msg.id)) pending.get(msg.id)(msg);
    });
    const send = (method, params = {}) => {
      id += 1;
      return new Promise((resolve) => {
        pending.set(id, resolve);
        socket.send(JSON.stringify({ id, method, params }));
      });
    };
    const ev = async (expression) => {
      const res = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
      return res.result?.result?.value;
    };
    await send("Runtime.enable");
    await send("Page.enable");
    await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 800 });
    for (let i = 0; i < 20; i += 1) {
      const ready = await ev("document.body && document.body.innerText && document.body.innerText.length > 40");
      if (ready) break;
      await sleep(250);
    }
    const homeText = (await ev("document.body && document.body.innerText")) || "";
    const homeShot = await send("Page.captureScreenshot", { format: "png" });
    if (homeShot.result?.data) {
      writeFileSync(join(OUT, `${label}-home.png`), Buffer.from(homeShot.result.data, "base64"));
    }
    await ev("window.location.href = 'https://lojadepaes.com.br/biblioteca/o-comeco'");
    let articleText = "";
    for (let i = 0; i < 80; i += 1) {
      articleText = (await ev("document.body && document.body.innerText")) || "";
      const prices = /R\$\s*19/.test(articleText) && /R\$\s*10/.test(articleText);
      const loaded = /Plano principal: R\$ 19/i.test(articleText);
      if (prices && loaded) break;
      await sleep(250);
    }
    const identify = await ev(
      "!!document.querySelector('input[type=email], input[autocomplete=email]')"
    );
    const assinar = await ev(
      "!!Array.from(document.querySelectorAll('button,a')).some((el) => /Assinar/i.test(el.textContent || ''))"
    );
    const unpublished = /ainda não estão publicados/i.test(articleText);
    await ev(
      "const el = document.querySelector('input[type=email], input[autocomplete=email]'); if (el) el.scrollIntoView({block:'center'});"
    );
    await sleep(400);
    const articleShot = await send("Page.captureScreenshot", { format: "png" });
    if (articleShot.result?.data) {
      writeFileSync(join(OUT, `${label}-biblioteca.png`), Buffer.from(articleShot.result.data, "base64"));
    }
    await ev("window.location.href = 'https://lojadepaes.com.br/biblioteca/calculadora'");
    let calcText = "";
    for (let i = 0; i < 40; i += 1) {
      calcText = (await ev("document.body && document.body.innerText")) || "";
      if (/Calcular|porcentagem/i.test(calcText)) break;
      await sleep(250);
    }
    const calcShot = await send("Page.captureScreenshot", { format: "png" });
    if (calcShot.result?.data) {
      writeFileSync(join(OUT, `${label}-calculadora.png`), Buffer.from(calcShot.result.data, "base64"));
    }
    socket.close();
    return {
      viewport: `${width}x${height}`,
      home_has_biblioteca: /biblioteca/i.test(homeText),
      article_has_19: /R\$\s*19/.test(articleText),
      article_has_20: /20/.test(articleText) && /cr[eé]dito/i.test(articleText),
      article_has_10: /R\$\s*10/.test(articleText),
      monthly: /m[eê]s/i.test(articleText),
      optional: /opcional/i.test(articleText),
      identify_form: Boolean(identify),
      unpublished_message: unpublished,
      waiting_for_hub_editor: /botão de pagamento só aparece/i.test(articleText),
      live_catalog_copy: /20 créditos por ciclo mensal/i.test(articleText),
      assinar_before_identify: Boolean(assinar),
      calc_open: /Calcular|porcentagem/i.test(calcText),
    };
  } finally {
    chrome.kill();
  }
}

const desktop = await captureViewport("desktop", 1280, 1600);
const mobile = await captureViewport("mobile", 390, 844);
const report = { charged: false, checkout_opened: false, desktop, mobile };
writeFileSync(join(OUT, "browser.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
const ok =
  desktop.article_has_19 &&
  desktop.article_has_10 &&
  desktop.identify_form &&
  !desktop.unpublished_message &&
  !desktop.waiting_for_hub_editor &&
  desktop.calc_open &&
  mobile.article_has_19 &&
  mobile.article_has_10 &&
  mobile.identify_form &&
  !mobile.unpublished_message &&
  !mobile.waiting_for_hub_editor &&
  mobile.calc_open;
if (!ok) process.exitCode = 1;
