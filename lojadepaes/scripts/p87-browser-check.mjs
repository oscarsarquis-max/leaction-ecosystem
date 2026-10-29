import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import http from "node:http";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = "C:\\Projetos\\lojadepaes\\readme\\evidence\\prompt-87\\prod";
const TOKEN =
  "eyJmbG91ciI6ImZhcmluaGEtYnJhbmNhLXN0cm9uZy13aGl0ZSIsInByZXBhcmF0aW9uIjoiZmVybWVudGFjYW8tbmF0dXJhbC1jdXJ0YSIsImluY2x1c2lvbnMiOltdLCJzaGFwZSI6InBhby1kZS1mb3JtYSIsIm5vdGUiOiJQYXJhIHNhbmR1XHUwMGVkY2hlcyBjb20gYW1pZ29zIC0gcFx1MDBlM28gZGUgZm9ybWEgY29tIGZlcm1lbnRhXHUwMGU3XHUwMGUzbyBuYXR1cmFsIGUgZmFyaW5oYSBicmFuY2EifQ.52c68bdc1f125e669e67e717b5b129b7";
const URL = `https://lojadepaes.com.br/?proposta=${encodeURIComponent(TOKEN)}#criacao`;
const port = 9335;

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
    "--user-data-dir=C:\\Temp\\chrome-p87g",
    "--window-size=1440,1400",
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
  await send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 1400,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await sleep(5000);
  await ev(`document.getElementById("next").click()`);
  await sleep(700);
  await ev(`document.getElementById("next").click()`);
  await sleep(1000);
  await ev(`document.querySelector(".gigio-loaf-tip")?.scrollIntoView({block:"center"})`);

  let tip = false;
  let tipText = "";
  for (let i = 0; i < 40; i += 1) {
    tip = await ev(`document.body.innerText.includes("Uma dica do Gigio")`);
    tipText = await ev(`(document.body.innerText.match(/Uma dica do Gigio[\\s\\S]{0,500}/)||[""])[0]`);
    if (tip && /sandu|fatia|forma|parmes|serv/i.test(tipText || "")) break;
    await sleep(700);
  }

  const shot = async (name) => {
    const res = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    if (res.result?.data) writeFileSync(join(OUT, name), Buffer.from(res.result.data, "base64"));
  };

  await ev(`document.querySelector(".gigio-loaf-tip")?.scrollIntoView({block:"center"})`);
  await shot("builder-dica-1440.png");

  await send("Emulation.setDeviceMetricsOverride", {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    mobile: true,
  });
  await sleep(400);
  await ev(`document.querySelector(".gigio-loaf-tip")?.scrollIntoView({block:"center"})`);
  await shot("builder-dica-390.png");

  await send("Emulation.setDeviceMetricsOverride", {
    width: 320,
    height: 720,
    deviceScaleFactor: 2,
    mobile: true,
  });
  await sleep(400);
  await ev(`document.querySelector(".gigio-loaf-tip")?.scrollIntoView({block:"center"})`);
  await shot("builder-dica-320.png");

  await send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 1400,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await ev(`document.getElementById("next").click()`);
  await sleep(800);
  await ev(`document.getElementById("next").click()`);
  await sleep(1000);
  const review = await ev(`({
    next: document.getElementById("next") && document.getElementById("next").innerText,
    send: document.getElementById("send-order") && document.getElementById("send-order").innerText,
    body: document.body.innerText.slice(0, 2500),
    hasBranca: /Branca/.test(document.body.innerText),
    hasForma: /P[\\u00e3a]o de forma/.test(document.body.innerText),
    hasNatural: /Fermenta/.test(document.body.innerText),
    hasSubmitOrder: /enviar pedido/i.test(document.body.innerText)
  })`);
  await shot("builder-revisao-1440.png");
  const summary = {
    tip,
    tipText: (tipText || "").slice(0, 400),
    reviewNext: review?.next,
    sendLabel: review?.send,
    hasBranca: review?.hasBranca,
    hasForma: review?.hasForma,
    hasNatural: review?.hasNatural,
    hasSubmitOrder: review?.hasSubmitOrder,
  };
  writeFileSync(join(OUT, "browser-summary.json"), JSON.stringify(summary, null, 2), "utf8");
  writeFileSync(join(OUT, "browser-review.json"), JSON.stringify(review, null, 2), "utf8");
  console.log(JSON.stringify(summary, null, 2));
  socket.close();
} finally {
  chrome.kill();
}
