import { spawn } from "node:child_process";
import http from "node:http";

const TOKEN =
  "eyJmbG91ciI6ImZhcmluaGEtYnJhbmNhLXN0cm9uZy13aGl0ZSIsInByZXBhcmF0aW9uIjoiZmVybWVudGFjYW8tbmF0dXJhbC1jdXJ0YSIsImluY2x1c2lvbnMiOltdLCJzaGFwZSI6InBhby1kZS1mb3JtYSIsIm5vdGUiOiJQYXJhIHNhbmR1XHUwMGVkY2hlcyBjb20gYW1pZ29zIC0gcFx1MDBlM28gZGUgZm9ybWEgY29tIGZlcm1lbnRhXHUwMGU3XHUwMGUzbyBuYXR1cmFsIGUgZmFyaW5oYSBicmFuY2EifQ.52c68bdc1f125e669e67e717b5b129b7";
const URL = `https://lojadepaes.com.br/?proposta=${encodeURIComponent(TOKEN)}#criacao`;
const port = 9334;

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
  [
    `--remote-debugging-port=${port}`,
    "--headless=new",
    "--disable-gpu",
    "--user-data-dir=C:\\Temp\\chrome-p87f",
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
      await new Promise((r) => setTimeout(r, 250));
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
    return res.result?.result?.value;
  };
  await send("Runtime.enable");
  await new Promise((r) => setTimeout(r, 5000));
  const steps = [];
  steps.push(await ev(`document.getElementById("next") && document.getElementById("next").innerText`));
  await ev(`document.getElementById("next").click()`);
  await new Promise((r) => setTimeout(r, 800));
  steps.push(await ev(`document.getElementById("next") && document.getElementById("next").innerText`));
  await ev(`document.getElementById("next").click()`);
  await new Promise((r) => setTimeout(r, 800));
  steps.push(await ev(`document.getElementById("next") && document.getElementById("next").innerText`));
  const tip = await ev(`document.body.innerText.includes("Uma dica do Gigio")`);
  const pressed = await ev(`Array.from(document.querySelectorAll('[aria-pressed="true"]')).map(e=>e.innerText.slice(0,40))`);
  console.log(JSON.stringify({ steps, tip, pressed }, null, 2));
  socket.close();
} finally {
  chrome.kill();
}
