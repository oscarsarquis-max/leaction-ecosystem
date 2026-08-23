import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { createConnection } from "node:net";
import { createHash, randomBytes } from "node:crypto";
import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

function openWs(url) {
  return new Promise((resolveOpen, reject) => {
    const target = new URL(url);
    const key = randomBytes(16).toString("base64");
    const socket = createConnection({ host: target.hostname, port: Number(target.port) }, () => {
      socket.write(
        `GET ${target.pathname}${target.search} HTTP/1.1\r\n` +
          `Host: ${target.host}\r\n` +
          "Upgrade: websocket\r\nConnection: Upgrade\r\n" +
          `Sec-WebSocket-Key: ${key}\r\nSec-WebSocket-Version: 13\r\n\r\n`,
      );
    });
    let buffer = Buffer.alloc(0);
    let opened = false;
    const pending = new Map();
    let seq = 0;
    function send(method, params = {}) {
      seq += 1;
      const id = seq;
      const payload = Buffer.from(JSON.stringify({ id, method, params }));
      let header;
      if (payload.length < 126) {
        header = Buffer.alloc(6);
        header[0] = 0x81;
        header[1] = 0x80 | payload.length;
        header.writeUInt32BE(0, 2);
      } else {
        header = Buffer.alloc(8);
        header[0] = 0x81;
        header[1] = 0x80 | 126;
        header.writeUInt16BE(payload.length, 2);
        header.writeUInt32BE(0, 4);
      }
      socket.write(Buffer.concat([header, payload]));
      return new Promise((resolveSend) => pending.set(id, resolveSend));
    }
    socket.on("data", (chunk) => {
      buffer = Buffer.concat([buffer, chunk]);
      if (!opened) {
        const split = buffer.indexOf("\r\n\r\n");
        if (split < 0) return;
        const expect = createHash("sha1").update(`${key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11`).digest("base64");
        if (!buffer.subarray(0, split).toString().includes(expect)) {
          reject(new Error("handshake CDP recusado"));
          return;
        }
        buffer = buffer.subarray(split + 4);
        opened = true;
        resolveOpen({ send, close: () => socket.end() });
      }
      while (buffer.length >= 2) {
        const fin = buffer[0] & 0x80;
        const opcode = buffer[0] & 0x0f;
        let len = buffer[1] & 0x7f;
        let offset = 2;
        if (len === 126) {
          if (buffer.length < 4) return;
          len = buffer.readUInt16BE(2);
          offset = 4;
        } else if (len === 127) {
          if (buffer.length < 10) return;
          len = Number(buffer.readBigUInt64BE(2));
          offset = 10;
        }
        if (buffer.length < offset + len) return;
        const body = buffer.subarray(offset, offset + len);
        buffer = buffer.subarray(offset + len);
        if (opcode === 1 && fin) {
          const payload = JSON.parse(body.toString());
          const wait = pending.get(payload.id);
          if (wait) {
            pending.delete(payload.id);
            wait(payload.result);
          }
        }
      }
    });
    socket.on("error", reject);
  });
}

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-017");
mkdirSync(out, { recursive: true });

const browser = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].find((path) => existsSync(path));
if (!browser) process.exit(0);

const port = 9333;
const profile = resolve(here, "../../.tmp-chrome-017");
mkdirSync(profile, { recursive: true });
const chrome = spawn(
  browser,
  [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    "--window-size=1440,900",
    "about:blank",
  ],
  { stdio: "ignore" },
);

function sleep(ms) {
  return new Promise((resolveSleep) => setTimeout(resolveSleep, ms));
}

async function waitJson(url, tries = 30) {
  for (let i = 0; i < tries; i += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return response.json();
    } catch {
      /* chrome still opening */
    }
    await sleep(200);
  }
  throw new Error(`CDP indisponível: ${url}`);
}

async function main() {
  await waitJson(`http://127.0.0.1:${port}/json/version`);
  const pages = await waitJson(`http://127.0.0.1:${port}/json/list`);
  const target = pages.find((item) => item.type === "page") ?? pages[0];
  if (!target?.webSocketDebuggerUrl) throw new Error("aba CDP não encontrada");
  const cdp = await openWs(target.webSocketDebuggerUrl);
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");

  async function shot(name) {
    await sleep(900);
    const image = await cdp.send("Page.captureScreenshot", { format: "png" });
    writeFileSync(resolve(out, `${name}.png`), Buffer.from(image.data, "base64"));
    console.log(resolve(out, `${name}.png`));
  }

  async function go(path) {
    await cdp.send("Runtime.evaluate", {
      expression: `window.history.pushState({}, "", ${JSON.stringify(path)}); window.dispatchEvent(new PopStateEvent("popstate"));`,
    });
    await sleep(1400);
  }

  await cdp.send("Page.navigate", { url: "http://127.0.0.1:5180/entrar" });
  await sleep(1200);
  await cdp.send("Runtime.evaluate", {
    expression: `document.querySelector("button.primary")?.click()`,
  });
  await sleep(2200);
  await go("/inicio");
  await shot("inicio-desktop");
  await go("/componentes/ingredientes");
  await shot("componentes-lista-desktop");
  await go("/componentes/ingredientes/novo");
  await shot("ingrediente-novo-desktop");
  await go("/componentes/ingredientes/03cf10c2-6412-4d55-912d-32a1af3aaf8f");
  await shot("ingrediente-rascunho-desktop");
  await shot("ingrediente-publicado-desktop");
  await go("/componentes/fornecedores");
  await shot("fornecedores-desktop");
  await go("/componentes/catalogos");
  await shot("catalogos-desktop");
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 1366,
    height: 768,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await go("/inicio");
  await shot("inicio-notebook");
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 1024,
    height: 768,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await go("/componentes/ingredientes");
  await shot("componentes-tablet-h");
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: 768,
    height: 1024,
    deviceScaleFactor: 1,
    mobile: true,
  });
  await go("/componentes/ingredientes");
  await shot("componentes-tablet-v");

  cdp.close();
  chrome.kill();
}

main().catch((error) => {
  console.error(error);
  chrome.kill();
  process.exit(1);
});
