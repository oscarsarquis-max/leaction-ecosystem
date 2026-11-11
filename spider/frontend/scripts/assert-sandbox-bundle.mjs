import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const assets = join(dirname(fileURLToPath(import.meta.url)), "..", "dist", "assets");
const forbidden = ["api.spider.actionhub.com.br", "127.0.0.1:8080", "localhost:8080"];
let checked = 0;
for (const name of readdirSync(assets)) {
  if (!name.endsWith(".js")) continue;
  const text = readFileSync(join(assets, name), "utf8");
  checked += 1;
  for (const host of forbidden) {
    if (text.includes(host)) {
      throw new Error(`${name} bakes ${host}; Monitor console must stay same-origin`);
    }
  }
  if (!text.includes("/v1/console/monitor/events") || !text.includes("/v1/console/executions")) {
    throw new Error(`${name} is missing same-origin console paths`);
  }
}
if (!checked) {
  throw new Error("no JavaScript assets found in dist/assets");
}
console.log(`sandbox-bundle-ok assets=${checked}`);
