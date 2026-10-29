import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import http from "node:http";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = "C:\\Projetos\\lojadepaes\\readme\\evidence\\prompt-89\\prod";
const port = 9345;
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
    "--user-data-dir=C:\\Temp\\chrome-p89e",
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
    const res = await send("Runtime.evaluate", { expression, returnByValue: true });
    if (res.result?.exceptionDetails) {
      return { __err: res.result.exceptionDetails.exception?.description || res.result.exceptionDetails.text };
    }
    return res.result?.result?.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1400, deviceScaleFactor: 1, mobile: false });
  for (let i = 0; i < 40; i += 1) {
    const ready = await ev('document.querySelectorAll("button.option").length >= 6');
    if (ready === true) break;
    await sleep(400);
  }
  const shot = async (name) => {
    const res = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    if (res.result?.data) writeFileSync(join(OUT, name), Buffer.from(res.result.data, "base64"));
  };
  const clickOption = async (needle) =>
    ev(
      `(() => { const n = ${JSON.stringify(needle)}.toLowerCase(); const btn = Array.from(document.querySelectorAll("button.option")).find(b => (b.innerText||"").toLowerCase().includes(n)); if (!btn) return {ok:false,n}; btn.click(); return {ok:true}; })()`,
    );

  await ev('document.querySelector("a[href=\\"#criacao\\"]") && document.querySelector("a[href=\\"#criacao\\"]").click()');
  await sleep(600);
  await clickOption("branca");
  await sleep(200);
  await clickOption("natural curta");
  await sleep(300);
  await ev('document.getElementById("next").click()');
  await sleep(500);
  await clickOption("nozes");
  await sleep(200);
  await ev('document.getElementById("next").click()');
  await sleep(600);
  await clickOption("pão de forma");
  await sleep(1500);
  await ev('document.getElementById("next").click()');
  await sleep(900);

  const day = await ev(
    '(() => { const b = Array.from(document.querySelectorAll("button.day, .bake-calendar button")).find(x => /fornada disponível/i.test(x.getAttribute("aria-label")||x.textContent||"")); if (!b) return {ok:false, labels: Array.from(document.querySelectorAll(".bake-calendar button, button.day")).map(x => x.getAttribute("aria-label")||x.textContent).slice(0,12)}; b.click(); return {ok:true, label:b.getAttribute("aria-label")||b.textContent}; })()',
  );
  await sleep(500);
  const afterDay = await ev(
    '({next:document.getElementById("next")&&document.getElementById("next").innerText, disabled:document.getElementById("next")&&document.getElementById("next").disabled, qty:document.querySelector(".builder-quantity input")&&document.querySelector(".builder-quantity input").value, preview:(document.querySelector(".preview-caption")||{}).innerText||"", send:document.getElementById("send-order")&&document.getElementById("send-order").innerText})',
  );
  await ev('document.getElementById("criacao") && document.getElementById("criacao").scrollIntoView()');
  await shot("08-encontro-data-1440.png");
  if (afterDay && afterDay.disabled === false) {
    await ev('document.getElementById("next").click()');
    await sleep(900);
  }
  const review = await ev(
    '({send:document.getElementById("send-order")&&document.getElementById("send-order").innerText, heading:(document.querySelector(".step-heading, .success")||{}).innerText||"", receipt:(document.querySelector(".receipt")||{}).innerText||"", preview:(document.querySelector(".preview-caption")||{}).innerText||"", body:document.body.innerText.slice(0,2200)})',
  );
  await ev('document.getElementById("criacao") && document.getElementById("criacao").scrollIntoView()');
  await shot("09-revisao-1440.png");
  writeFileSync(join(OUT, "09-revisao.json"), JSON.stringify({ day, afterDay, review }, null, 2), "utf8");

  await send("Page.navigate", { url: "https://lojadepaes.com.br/" });
  await sleep(3500);
  for (let i = 0; i < 20; i += 1) {
    const fab = await ev('Boolean(document.querySelector("[aria-label=\\"Conversar com Gigio\\"]"))');
    if (fab === true) break;
    await sleep(300);
  }
  await ev('document.querySelector("[aria-label=\\"Conversar com Gigio\\"]") && document.querySelector("[aria-label=\\"Conversar com Gigio\\"]").click()');
  await sleep(700);
  await ev(
    '(() => { const input = document.querySelector("[aria-label=\\"Mensagem para o Gigio\\"]"); if (!input) return false; Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set.call(input, "Quero um pão de forma com farinha branca, fermentação natural curta e nozes."); input.dispatchEvent(new Event("input", {bubbles:true})); const sendBtn = Array.from(document.querySelectorAll(".gigio-panel button")).find(x => /Enviar/i.test(x.textContent||"")); if (sendBtn) sendBtn.click(); return true; })()',
  );
  let chat = {};
  for (let i = 0; i < 50; i += 1) {
    chat = await ev(
      '({t:(document.querySelector(".gigio-panel")||{}).innerText||"", mount: Boolean(document.querySelector("a[href*=\\"proposta\\"]")), label: (document.querySelector("a[href*=\\"proposta\\"]")||{}).innerText||""})',
    );
    if (chat && (chat.mount || /Montar esse pão/i.test(chat.t || ""))) break;
    await sleep(800);
  }
  writeFileSync(join(OUT, "10-chat-proposta.json"), JSON.stringify({ preview: (chat?.t || "").slice(0, 1400), mount: chat?.mount, label: chat?.label }, null, 2), "utf8");
  await shot("10-chat-proposta-1440.png");
  await ev(
    '(() => { const a = document.querySelector("a[href*=\\"proposta\\"]") || Array.from(document.querySelectorAll("a")).find(x => /Montar esse pão/i.test(x.textContent||"")); if (!a) return {ok:false}; a.click(); return {ok:true, href:a.getAttribute("href")}; })()',
  );
  await sleep(2500);
  for (let i = 0; i < 20; i += 1) {
    const n = await ev('document.querySelectorAll("[aria-pressed=true]").length');
    if (n > 1) break;
    await sleep(400);
  }
  const filled = await ev(
    '({url:location.href, heading:(document.querySelector(".step-heading")||{}).innerText||"", pressed:Array.from(document.querySelectorAll("[aria-pressed=true]")).map(e=>(e.innerText||"").split("\\n")[0]), notice:(document.querySelector("[role=status], .tip")||{}).innerText||"", tip:(document.querySelector(".gigio-loaf-tip")||{}).innerText||"", overwrite: /já está montando/i.test(document.body.innerText)})',
  );
  await ev('document.getElementById("criacao") && document.getElementById("criacao").scrollIntoView()');
  await shot("11-montar-preenchido-1440.png");
  writeFileSync(join(OUT, "11-montar.json"), JSON.stringify(filled, null, 2), "utf8");

  const summary = {
    day,
    afterDay,
    send: review?.send,
    receipt: (review?.receipt || "").slice(0, 400),
    chatMount: chat?.mount,
    chatLabel: chat?.label,
    filledPressed: filled?.pressed,
    overwrite: filled?.overwrite,
    filledTip: (filled?.tip || "").slice(0, 200),
  };
  writeFileSync(join(OUT, "walk-review-chat.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify(summary, null, 2));
  socket.close();
} finally {
  chrome.kill();
}
