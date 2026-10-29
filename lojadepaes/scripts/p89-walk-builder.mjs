import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import http from "node:http";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUT = "C:\\Projetos\\lojadepaes\\readme\\evidence\\prompt-89\\prod";
const port = 9344;
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
    "--user-data-dir=C:\\Temp\\chrome-p89d",
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
      const ex = res.result.exceptionDetails;
      return { __err: ex.exception?.description || ex.text, raw: ex };
    }
    return res.result?.result?.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1400, deviceScaleFactor: 1, mobile: false });
  await sleep(2500);
  await ev("document.fonts && document.fonts.ready");
  for (let i = 0; i < 40; i += 1) {
    const ready = await ev(
      'Boolean(document.getElementById("criacao") && document.querySelectorAll("button.option").length >= 6 && /Crie seu p/.test(document.body.innerText))',
    );
    if (ready === true) break;
    await sleep(400);
  }

  const dump = async (name) => {
    const state = await ev(
      '({url:location.href,next:document.getElementById("next")&&document.getElementById("next").innerText,nextDisabled:document.getElementById("next")&&document.getElementById("next").disabled,options:Array.from(document.querySelectorAll("button.option")).map(b=>(b.innerText||"").split("\\n")[0]).slice(0,20),optionCount:document.querySelectorAll("button.option").length,tip:(document.querySelector(".gigio-loaf-tip")||{}).innerText||"",pressed:Array.from(document.querySelectorAll("[aria-pressed=true]")).map(e=>(e.innerText||"").split("\\n")[0]),heading:(document.querySelector(".step-heading")||{}).innerText||""})',
    );
    writeFileSync(join(OUT, name), JSON.stringify(state, null, 2), "utf8");
    return state;
  };
  const shot = async (name) => {
    const res = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    if (res.result?.data) {
      writeFileSync(join(OUT, name), Buffer.from(res.result.data, "base64"));
      return { ok: true, name };
    }
    return { ok: false, name, keys: Object.keys(res.result || {}), err: res.error || res.result?.message };
  };
  const clickOption = async (needle) =>
    ev(
      `(() => { const n = ${JSON.stringify(needle)}.toLowerCase(); const btn = Array.from(document.querySelectorAll("button.option")).find(b => (b.innerText||"").toLowerCase().includes(n)); if (!btn) return {ok:false,n}; btn.click(); return {ok:true,text:(btn.innerText||"").slice(0,80),pressed:btn.getAttribute("aria-pressed")}; })()`,
    );

  const homeShot = await shot("00-home-1440.png");
  const navClick = await ev(
    '(() => { const a = document.querySelector("a[href=\\"#criacao\\"]") || Array.from(document.querySelectorAll("a")).find(x => /Crie seu p|criacao/i.test((x.textContent||"") + (x.getAttribute("href")||""))); if (!a) return {ok:false, hrefs: Array.from(document.querySelectorAll("a")).map(x=>x.getAttribute("href")).slice(0,12)}; a.click(); return {ok:true,href:a.getAttribute("href"),text:a.textContent}; })()',
  );
  await sleep(1200);
  await ev('document.getElementById("criacao") && document.getElementById("criacao").scrollIntoView()');
  await sleep(400);
  await dump("01-criacao.json");
  const essenciaShot = await shot("01-essencia-1440.png");

  const flour = await clickOption("branca");
  await sleep(300);
  const dough = await clickOption("natural curta");
  await sleep(400);
  const afterPick = await dump("01-picks.json");
  await shot("01-essencia-escolhida-1440.png");

  const next1 = await ev('document.getElementById("next").click() || document.getElementById("next").innerText');
  await sleep(700);
  const nozes = await clickOption("nozes");
  await sleep(300);
  await dump("02-toque.json");
  await shot("02-toque-1440.png");
  await ev('document.getElementById("next").click()');
  await sleep(900);
  const beforeShape = await dump("03-formato-antes.json");
  await ev('document.querySelector(".gigio-loaf-tip") && document.querySelector(".gigio-loaf-tip").scrollIntoView()');
  await shot("03-formato-sem-escolha-1440.png");

  const shape = await clickOption("pão de forma");
  let tip = {};
  for (let i = 0; i < 45; i += 1) {
    tip = await ev(
      '({text:(document.querySelector(".gigio-loaf-tip")||{}).innerText||"",loading:/olhando a sua massa/i.test(document.body.innerText)})',
    );
    if (tip && tip.text && tip.text.length > 90 && !tip.loading) break;
    await sleep(700);
  }
  writeFileSync(join(OUT, "04-dica.json"), JSON.stringify(tip, null, 2), "utf8");
  await ev('document.querySelector(".gigio-loaf-tip") && document.querySelector(".gigio-loaf-tip").scrollIntoView()');
  const tipShot = await shot("04-dica-1440.png");

  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await sleep(300);
  await ev('document.querySelector(".gigio-loaf-tip") && document.querySelector(".gigio-loaf-tip").scrollIntoView()');
  await shot("04-dica-390.png");
  await send("Emulation.setDeviceMetricsOverride", { width: 320, height: 720, deviceScaleFactor: 2, mobile: true });
  await sleep(300);
  await ev('document.querySelector(".gigio-loaf-tip") && document.querySelector(".gigio-loaf-tip").scrollIntoView()');
  await shot("04-dica-320.png");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1400, deviceScaleFactor: 1, mobile: false });

  await ev(
    '(() => { const b = Array.from(document.querySelectorAll("button")).find(x => /Conversar com o Gigio/i.test(x.textContent||"")); if (b) b.click(); return Boolean(b); })()',
  );
  await sleep(900);
  await ev(
    '(() => { const input = document.querySelector("[aria-label=\\"Mensagem para o Gigio\\"]"); if (!input) return false; const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set; setter.call(input, "Por que essa combinação funciona?"); input.dispatchEvent(new Event("input", {bubbles:true})); const sendBtn = Array.from(document.querySelectorAll(".gigio-panel button")).find(x => /Enviar/i.test(x.textContent||"")); if (sendBtn) sendBtn.click(); return true; })()',
  );
  let chat = {};
  for (let i = 0; i < 40; i += 1) {
    chat = await ev('({t:(document.querySelector(".gigio-panel")||{}).innerText||""})');
    if (chat && /branca|nozes|forma|ferment/i.test(chat.t || "") && (chat.t || "").length > 160) break;
    await sleep(800);
  }
  writeFileSync(join(OUT, "06-chat.json"), JSON.stringify({ preview: (chat?.t || "").slice(0, 1200) }, null, 2), "utf8");
  await shot("06-chat-combinacao-1440.png");
  await ev('document.querySelector(".gigio-close") && document.querySelector(".gigio-close").click()');
  await sleep(400);

  const shape2 = await clickOption("rústico de cesto");
  let tip2 = {};
  for (let i = 0; i < 35; i += 1) {
    tip2 = await ev('({text:(document.querySelector(".gigio-loaf-tip")||{}).innerText||""})');
    if (tip2 && tip2.text && tip2.text !== tip.text && tip2.text.length > 80) break;
    await sleep(700);
  }
  writeFileSync(
    join(OUT, "07-dica-troca.json"),
    JSON.stringify({ a: (tip?.text || "").slice(0, 280), b: (tip2?.text || "").slice(0, 280) }, null, 2),
    "utf8",
  );
  await ev('document.querySelector(".gigio-loaf-tip") && document.querySelector(".gigio-loaf-tip").scrollIntoView()');
  await shot("07-dica-apos-troca-1440.png");

  await ev(
    '(() => { const b = Array.from(document.querySelectorAll("button")).find(x => /Pedir nova dica/i.test(x.textContent||"")); if (b) b.click(); return Boolean(b); })()',
  );
  await sleep(7000);
  const refresh = await ev(
    '({text:(document.querySelector(".gigio-loaf-tip")||{}).innerText||"",n:document.querySelectorAll(".gigio-loaf-tip").length})',
  );
  writeFileSync(join(OUT, "07-dica-refresh.json"), JSON.stringify(refresh, null, 2), "utf8");

  await ev('document.getElementById("next").click()');
  await sleep(800);
  const meet = await dump("08-encontro.json");
  await shot("08-encontro-1440.png");

  const summary = {
    homeShot,
    essenciaShot,
    tipShot,
    navClick,
    flour,
    dough,
    nozes,
    shape,
    shape2,
    next1,
    pressed: afterPick?.pressed,
    placeholder: /formato acima/i.test(beforeShape?.tip || ""),
    beforeTip: (beforeShape?.tip || "").slice(0, 180),
    tipLen: (tip?.text || "").length,
    tipPreview: (tip?.text || "").slice(0, 220),
    changed: Boolean(tip2?.text && tip2.text !== tip?.text),
    chatHasLoaf: /branca|nozes|forma|ferment/i.test(chat?.t || ""),
    meetNext: meet?.next,
    refreshN: refresh?.n,
  };
  writeFileSync(join(OUT, "walk-summary.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify(summary, null, 2));
  socket.close();
} finally {
  chrome.kill();
}
