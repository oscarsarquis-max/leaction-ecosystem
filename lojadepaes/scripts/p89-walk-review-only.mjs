import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import http from "node:http";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = "C:\\Projetos\\lojadepaes\\readme\\evidence\\prompt-89\\prod";
const port = 9347;
mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function get(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => resolve(data));
    }).on("error", reject);
  });
}

const chrome = spawn(
  CHROME,
  [
    `--remote-debugging-port=${port}`,
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--user-data-dir=C:\\Temp\\chrome-p89g",
    "--window-size=1440,1400",
    "https://lojadepaes.com.br/#criacao",
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
  const socket = new WebSocket((pages.find((item) => item.type === "page") || pages[0]).webSocketDebuggerUrl || wsUrl);
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
    const res = await send("Runtime.evaluate", { expression, returnByValue: true });
    return res.result?.result?.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1400, deviceScaleFactor: 1, mobile: false });
  for (let i = 0; i < 40; i += 1) {
    if ((await ev('document.querySelectorAll("button.option").length')) >= 6) break;
    await sleep(300);
  }
  const clickOption = async (needle) =>
    ev(
      `(() => { const n = ${JSON.stringify(needle)}.toLowerCase(); const btn = Array.from(document.querySelectorAll("button.option")).find(b => (b.innerText||"").toLowerCase().includes(n)); if (btn) btn.click(); return Boolean(btn); })()`,
    );
  await clickOption("branca");
  await sleep(150);
  await clickOption("natural curta");
  await sleep(200);
  await ev('document.getElementById("next").click()');
  await sleep(300);
  await clickOption("nozes");
  await sleep(150);
  await ev('document.getElementById("next").click()');
  await sleep(400);
  await clickOption("pão de forma");
  await sleep(600);
  await ev('document.getElementById("next").click()');
  await sleep(800);
  const picked = await ev(
    '(() => { const b = Array.from(document.querySelectorAll(".bake-calendar button, button.day")).find(x => /produção aberto/i.test(x.getAttribute("aria-label")||"")); if (!b) return {ok:false}; b.click(); return {ok:true, label:b.getAttribute("aria-label")}; })()',
  );
  await sleep(800);
  const nextState = await ev(
    '({text:document.getElementById("next")&&document.getElementById("next").innerText, disabled:document.getElementById("next")&&document.getElementById("next").disabled})',
  );
  await ev('document.getElementById("next").click()');
  await sleep(1000);
  const review = await ev(
    '({send:document.getElementById("send-order")&&document.getElementById("send-order").innerText, receipt:(document.querySelector(".receipt")||{}).innerText||"", preview:(document.querySelector(".preview-caption")||{}).innerText||"", qty:document.querySelector(".builder-quantity input")&&document.querySelector(".builder-quantity input").value})',
  );
  await ev('document.getElementById("criacao") && document.getElementById("criacao").scrollIntoView()');
  const shot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
  if (shot.result?.data) writeFileSync(join(OUT, "09-revisao-1440.png"), Buffer.from(shot.result.data, "base64"));
  writeFileSync(join(OUT, "09-revisao.json"), JSON.stringify({ picked, nextState, review }, null, 2), "utf8");
  console.log(JSON.stringify({ picked, nextState, send: review?.send, receipt: (review?.receipt || "").slice(0, 400), preview: (review?.preview || "").slice(0, 220) }, null, 2));
  socket.close();
} finally {
  chrome.kill();
}
