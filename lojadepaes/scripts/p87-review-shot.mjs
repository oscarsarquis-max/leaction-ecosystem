import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { join } from "node:path";
import http from "node:http";

const TOKEN =
  "eyJmbG91ciI6ImZhcmluaGEtYnJhbmNhLXN0cm9uZy13aGl0ZSIsInByZXBhcmF0aW9uIjoiZmVybWVudGFjYW8tbmF0dXJhbC1jdXJ0YSIsImluY2x1c2lvbnMiOltdLCJzaGFwZSI6InBhby1kZS1mb3JtYSIsIm5vdGUiOiJQYXJhIHNhbmR1XHUwMGVkY2hlcyBjb20gYW1pZ29zIC0gcFx1MDBlM28gZGUgZm9ybWEgY29tIGZlcm1lbnRhXHUwMGU3XHUwMGUzbyBuYXR1cmFsIGUgZmFyaW5oYSBicmFuY2EifQ.52c68bdc1f125e669e67e717b5b129b7";
const URL = `https://lojadepaes.com.br/?proposta=${encodeURIComponent(TOKEN)}#criacao`;
const OUT = "C:\\Projetos\\lojadepaes\\readme\\evidence\\prompt-87\\prod";
const port = 9336;

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
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  [`--remote-debugging-port=${port}`, "--headless=new", "--disable-gpu", "--user-data-dir=C:\\Temp\\chrome-p87h", "--window-size=1440,1400", URL],
  { stdio: "ignore" },
);

try {
  let wsUrl;
  for (let i = 0; i < 40; i += 1) {
    try {
      wsUrl = JSON.parse(await get(`http://127.0.0.1:${port}/json/version`)).webSocketDebuggerUrl;
      break;
    } catch {
      await new Promise((r) => setTimeout(r, 250));
    }
  }
  const pages = JSON.parse(await get(`http://127.0.0.1:${port}/json/list`));
  const socket = new WebSocket((pages.find((p) => p.type === "page") || pages[0]).webSocketDebuggerUrl || wsUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve);
    socket.addEventListener("error", reject);
  });
  let id = 0;
  const pending = new Map();
  socket.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) pending.get(msg.id)(msg);
  });
  const send = (method, params = {}) => {
    id += 1;
    return new Promise((resolve) => {
      pending.set(id, resolve);
      socket.send(JSON.stringify({ id, method, params }));
    });
  };
  const ev = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true })).result?.result?.value;
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1400, deviceScaleFactor: 1, mobile: false });
  await new Promise((r) => setTimeout(r, 5000));
  await ev(`document.getElementById("next").click()`);
  await new Promise((r) => setTimeout(r, 600));
  await ev(`document.getElementById("next").click()`);
  await new Promise((r) => setTimeout(r, 600));
  await ev(`document.getElementById("next").click()`);
  await new Promise((r) => setTimeout(r, 1000));
  await ev(`document.getElementById("criacao")?.scrollIntoView({block:"start"})`);
  await new Promise((r) => setTimeout(r, 400));
  const info = await ev(`({
    next: document.getElementById("next")?.innerText,
    heading: document.getElementById("step-content")?.innerText?.slice(0, 800),
    send: document.getElementById("send-order")?.innerText || null
  })`);
  const png = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
  writeFileSync(join(OUT, "builder-encontro-1440.png"), Buffer.from(png.result.data, "base64"));
  writeFileSync(join(OUT, "browser-encontro.json"), JSON.stringify(info, null, 2), "utf8");
  console.log(JSON.stringify(info, null, 2));
  socket.close();
} finally {
  chrome.kill();
}
