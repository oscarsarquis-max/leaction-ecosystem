import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import http from "node:http";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = "C:\\Projetos\\lojadepaes\\readme\\evidence\\prompt-91b";
const URL = "https://lojadepaes.com.br/biblioteca/o-comeco";
const port = 9341;

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

const chrome = spawn(
  CHROME,
  [
    `--remote-debugging-port=${port}`,
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--user-data-dir=C:\\Temp\\chrome-p91b",
    "--window-size=1280,1600",
    URL,
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
  let text = "";
  for (let i = 0; i < 60; i += 1) {
    text = (await ev("document.body && document.body.innerText")) || "";
    if (/R\$\s*19/.test(text) && /R\$\s*10/.test(text)) break;
    await sleep(250);
  }
  const checkout = await ev(
    "!!Array.from(document.querySelectorAll('button,a')).some((el) => /Assinar/i.test(el.textContent || ''))"
  );
  const shot = await send("Page.captureScreenshot", { format: "png" });
  if (shot.result?.data) {
    writeFileSync(join(OUT, "biblioteca-o-comeco.png"), Buffer.from(shot.result.data, "base64"));
  }
  const calcNav = await ev(`window.location.href = 'https://lojadepaes.com.br/biblioteca/calculadora'; 'ok'`);
  await sleep(1200);
  const calcText = await ev("document.body.innerText");
  const calcShot = await send("Page.captureScreenshot", { format: "png" });
  if (calcShot.result?.data) {
    writeFileSync(join(OUT, "biblioteca-calculadora.png"), Buffer.from(calcShot.result.data, "base64"));
  }
  const report = {
    article_has_19: /R\$\s*19/.test(text || ""),
    article_has_20: /20/.test(text || "") && /cr[eé]dito/i.test(text || ""),
    article_has_10: /R\$\s*10/.test(text || ""),
    monthly: /m[eê]s/i.test(text || ""),
    no_auto_buy: /n[aã]o entra sozinho|opcional/i.test(text || ""),
    checkout_button: checkout,
    calc_open: /porcentagem de padeiro/i.test(calcText || ""),
    calc_nav: calcNav,
  };
  writeFileSync(join(OUT, "browser.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (!report.article_has_19 || !report.article_has_10 || !report.monthly || !report.calc_open) {
    process.exitCode = 1;
  }
  socket.close();
} finally {
  chrome.kill();
}
