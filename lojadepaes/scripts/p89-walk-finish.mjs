import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import http from "node:http";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = "C:\\Projetos\\lojadepaes\\readme\\evidence\\prompt-89\\prod";
const port = 9346;
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
    "--user-data-dir=C:\\Temp\\chrome-p89f",
    "--window-size=1440,1400",
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
    return res.result?.exceptionDetails
      ? { __err: res.result.exceptionDetails.exception?.description || res.result.exceptionDetails.text }
      : res.result?.result?.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1400, deviceScaleFactor: 1, mobile: false });
  const shot = async (name) => {
    const res = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    if (res.result?.data) writeFileSync(join(OUT, name), Buffer.from(res.result.data, "base64"));
  };
  const clickOption = async (needle) =>
    ev(
      `(() => { const n = ${JSON.stringify(needle)}.toLowerCase(); const btn = Array.from(document.querySelectorAll("button.option")).find(b => (b.innerText||"").toLowerCase().includes(n)); if (btn) btn.click(); return Boolean(btn); })()`,
    );

  for (let i = 0; i < 40; i += 1) {
    if ((await ev('document.querySelectorAll("button.option").length')) >= 6) break;
    await sleep(400);
  }
  await ev('document.querySelector("a[href=\\"#criacao\\"]") && document.querySelector("a[href=\\"#criacao\\"]").click()');
  await sleep(500);
  await clickOption("branca");
  await sleep(200);
  await clickOption("natural curta");
  await sleep(250);
  await ev('document.getElementById("next").click()');
  await sleep(400);
  await clickOption("nozes");
  await sleep(200);
  await ev('document.getElementById("next").click()');
  await sleep(500);
  await clickOption("pão de forma");
  await sleep(800);
  await ev('document.getElementById("next").click()');
  await sleep(900);

  const days = await ev(
    'Array.from(document.querySelectorAll(".bake-calendar button, button.day")).map(x => x.getAttribute("aria-label")||x.textContent).filter(Boolean)',
  );
  writeFileSync(join(OUT, "08-calendar-labels.json"), JSON.stringify(days, null, 2), "utf8");
  const picked = await ev(
    '(() => { const b = Array.from(document.querySelectorAll(".bake-calendar button, button.day")).find(x => /fornada disponível/i.test(x.getAttribute("aria-label")||"")); if (!b) return {ok:false}; b.click(); return {ok:true, label:b.getAttribute("aria-label")}; })()',
  );
  await sleep(400);
  const meet = await ev(
    '({next:document.getElementById("next")&&document.getElementById("next").innerText, disabled:document.getElementById("next")&&document.getElementById("next").disabled, qty:document.querySelector(".builder-quantity input")&&document.querySelector(".builder-quantity input").value, preview:(document.querySelector(".preview-caption")||{}).innerText||""})',
  );
  if (meet && meet.disabled === false) {
    await ev('document.getElementById("next").click()');
    await sleep(900);
  }
  const review = await ev(
    '({send:document.getElementById("send-order")&&document.getElementById("send-order").innerText, receipt:(document.querySelector(".receipt")||{}).innerText||"", preview:(document.querySelector(".preview-caption")||{}).innerText||"", heading:(document.querySelector(".step-heading, .studio-title")||{}).innerText||""})',
  );
  await ev('document.getElementById("criacao") && document.getElementById("criacao").scrollIntoView()');
  await shot("09-revisao-1440.png");
  writeFileSync(join(OUT, "09-revisao.json"), JSON.stringify({ picked, meet, review }, null, 2), "utf8");

  await ev('document.querySelector("[aria-label=\\"Conversar com Gigio\\"]") && document.querySelector("[aria-label=\\"Conversar com Gigio\\"]").click()');
  await sleep(500);
  await ev(
    '(() => { const input = document.querySelector("[aria-label=\\"Mensagem para o Gigio\\"]"); if (!input) return false; Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set.call(input, "Quero um pão de forma com farinha branca, fermentação natural curta e nozes."); input.dispatchEvent(new Event("input", {bubbles:true})); const sendBtn = Array.from(document.querySelectorAll(".gigio-panel button")).find(x => /Enviar/i.test(x.textContent||"")); if (sendBtn) sendBtn.click(); return true; })()',
  );
  for (let i = 0; i < 40; i += 1) {
    const ready = await ev('Boolean(document.querySelector("a[href*=\\"proposta\\"]"))');
    if (ready === true) break;
    await sleep(700);
  }
  const overwrite = await ev(
    '(() => { const a = document.querySelector("a[href*=\\"proposta\\"]"); if (!a) return {clicked:false}; a.click(); return {clicked:true, href:a.getAttribute("href")}; })()',
  );
  await sleep(1200);
  const dialog = await ev(
    '({text: (document.querySelector(".gigio-loaf-confirm")||{}).innerText || "", bodyHas: /já está montando/i.test(document.body.innerText)})',
  );
  await ev('document.getElementById("criacao") && document.getElementById("criacao").scrollIntoView()');
  await shot("12-nao-sobrescreve-1440.png");
  writeFileSync(join(OUT, "12-overwrite.json"), JSON.stringify({ overwrite, dialog }, null, 2), "utf8");

  if (dialog && dialog.bodyHas) {
    await ev(
      '(() => { const b = Array.from(document.querySelectorAll("button")).find(x => /Manter o atual/i.test(x.textContent||"")); if (b) b.click(); return Boolean(b); })()',
    );
    await sleep(400);
  }

  await ev('document.getElementById("next").click()');
  await sleep(400);
  await ev('document.getElementById("next").click()');
  await sleep(800);
  let tip = {};
  for (let i = 0; i < 30; i += 1) {
    tip = await ev('({text:(document.querySelector(".gigio-loaf-tip")||{}).innerText||""})');
    if (tip && tip.text && tip.text.length > 80 && !/olhando/i.test(tip.text)) break;
    await sleep(600);
  }
  await ev('document.querySelector(".gigio-loaf-tip") && document.querySelector(".gigio-loaf-tip").scrollIntoView()');
  await shot("13-dica-apos-montar-1440.png");
  writeFileSync(join(OUT, "13-dica-montar.json"), JSON.stringify(tip, null, 2), "utf8");

  console.log(
    JSON.stringify(
      {
        picked,
        meet,
        send: review?.send,
        receipt: (review?.receipt || "").slice(0, 350),
        preview: (review?.preview || meet?.preview || "").slice(0, 220),
        overwriteDialog: dialog,
        tipPreview: (tip?.text || "").slice(0, 220),
      },
      null,
      2,
    ),
  );
  socket.close();
} finally {
  chrome.kill();
}
