import { readFileSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";

const tokens = Object.fromEntries(
  readFileSync("c:/Projetos/ActionFinance/.local/demo-tokens.env", "utf8")
    .split(/\r?\n/)
    .filter((l) => l.includes("="))
    .map((l) => {
      const i = l.indexOf("=");
      return [l.slice(0, i).trim(), l.slice(i + 1)];
    })
);
const op = tokens.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A;
const company = "11111111-1111-4111-a111-111111111111";

async function sync() {
  const res = await fetch(`http://127.0.0.1:8091/api/v1/pay-receipts/sync?companyId=${company}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${op}` },
  });
  const body = await res.json();
  return { status: res.status, body };
}

const listBefore = await (
  await fetch(`http://127.0.0.1:8091/api/v1/pay-receipts?companyId=${company}`, {
    headers: { Authorization: `Bearer ${op}` },
  })
).json();
const hubBefore = await (await fetch("http://127.0.0.1:4101/__test/counts")).json();
execSync("powershell -NoProfile -File c:\\Projetos\\ActionFinance\\scripts\\dev\\prm009\\stop-spider-engine.ps1", {
  stdio: "inherit",
});
await new Promise((r) => setTimeout(r, 1500));
const down = await sync();
const hubDuring = await (await fetch("http://127.0.0.1:4101/__test/counts")).json();
const listDuring = await (
  await fetch(`http://127.0.0.1:8091/api/v1/pay-receipts?companyId=${company}`, {
    headers: { Authorization: `Bearer ${op}` },
  })
).json();
execSync("powershell -NoProfile -File c:\\Projetos\\ActionFinance\\scripts\\dev\\prm009\\start-spider-forward.ps1", {
  stdio: "inherit",
});
const up = await sync();
writeFileSync(
  "c:/Projetos/ActionFinance/documents/reviews/evidence/prm-009-continuidade-001/live-spider-down.json",
  JSON.stringify(
    {
      itemsBefore: (listBefore.items || []).length,
      itemsDuring: (listDuring.items || []).length,
      hubBefore: hubBefore.counts.list,
      hubDuring: hubDuring.counts.list,
      down: { http: down.status, error: down.body.lastError || down.body.run?.lastError || down.body.message },
      up: { http: up.status, status: up.body.run?.status, imported: up.body.run?.importedCount },
      hubUnchanged: hubBefore.counts.list === hubDuring.counts.list,
    },
    null,
    2
  )
);
console.log(
  `DOWN http=${down.status} hub ${hubBefore.counts.list}->${hubDuring.counts.list} items ${listBefore.items.length}->${listDuring.items.length}`
);
console.log(`UP ${up.status} ${up.body.run?.status} imported=${up.body.run?.importedCount}`);
