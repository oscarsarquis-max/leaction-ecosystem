import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import http from "node:http";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = "C:\\Projetos\\lojadepaes\\readme\\evidence\\prompt-90\\prod";
const port = 9350;
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
    "--user-data-dir=C:\\Temp\\chrome-p90b",
    "--window-size=1440,1100",
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
    return res.result?.result?.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  for (let i = 0; i < 30; i += 1) {
    if ((await ev('Boolean(document.querySelector("[aria-label=\\"Conversar com Gigio\\"]"))')) === true) break;
    await sleep(400);
  }
  const shot = async (name) => {
    const res = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    if (res.result?.data) writeFileSync(join(OUT, name), Buffer.from(res.result.data, "base64"));
  };
  const typeSend = async (text) =>
    ev(
      `(() => { const input = document.querySelector("[aria-label=\\"Mensagem para o Gigio\\"]"); if (!input) return false; Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set.call(input, ${JSON.stringify(text)}); input.dispatchEvent(new Event("input", {bubbles:true})); const b = Array.from(document.querySelectorAll(".gigio-panel button")).find(x => /Enviar/i.test(x.textContent||"")); if (b) b.click(); return true; })()`,
    );
  const panel = async () =>
    ev(`(() => {
      const msgs = Array.from(document.querySelectorAll(".gigio-thread .gigio-msg"));
      const last = msgs[msgs.length - 1];
      return {
        t: (document.querySelector(".gigio-thread")||{}).innerText || "",
        n: document.querySelectorAll(".gigio-thread a[href*='acompanhar'], .gigio-thread a[href*='proposta']").length,
        labels: Array.from(document.querySelectorAll(".gigio-thread a")).map(a => (a.textContent||"").trim()).filter(Boolean),
        last: (last && last.innerText) || "",
        lastLinks: last ? Array.from(last.querySelectorAll("a")).map(a => (a.textContent||"").trim()) : [],
        count: msgs.length
      };
    })()`);

  await ev('document.querySelector("[aria-label=\\"Conversar com Gigio\\"]").click()');
  await sleep(700);
  await typeSend(
    "queremos fazer um hambúrguer bem legal, com batatas e molho. que sugestão de acompanhamento você poderia me dar?",
  );
  let first = {};
  for (let i = 0; i < 50; i += 1) {
    first = await panel();
    if (first && /acompanhamentos|cerveja|batata/i.test(first.t || "") && first.n > 0) break;
    await sleep(800);
  }
  writeFileSync(join(OUT, "01-hamburguer.json"), JSON.stringify(first, null, 2), "utf8");
  await shot("01-hamburguer-1440.png");
  for (let i = 0; i < 20; i += 1) {
    const ready = await ev(
      '(() => { const b = Array.from(document.querySelectorAll(".gigio-panel button")).find(x => /Enviar/i.test(x.textContent||"")); return Boolean(b && !b.disabled); })()',
    );
    if (ready === true) break;
    await sleep(300);
  }
  const sentFusca = await typeSend("Onde compro um Fusca?");
  writeFileSync(join(OUT, "02-sent.json"), JSON.stringify({ sentFusca }, null, 2), "utf8");
  let second = {};
  for (let i = 0; i < 55; i += 1) {
    second = await panel();
    if (/Onde compro um Fusca/i.test(second?.t || "") && (second?.count || 0) >= 4 && (second?.last || "").length > 40) break;
    await sleep(800);
  }
  writeFileSync(join(OUT, "02-fusca.json"), JSON.stringify(second, null, 2), "utf8");
  await shot("02-fusca-1440.png");

  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await sleep(300);
  await shot("02-fusca-390.png");

  const summary = {
    firstCtas: first?.labels,
    firstCount: first?.n,
    secondCtas: second?.labels,
    secondCount: second?.n,
    sameCtaCount: first?.n === second?.n,
    fuscaText: (second?.t || "").slice(0, 800),
  };
  writeFileSync(join(OUT, "walk-summary.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify(summary, null, 2));
  socket.close();
} finally {
  chrome.kill();
}
