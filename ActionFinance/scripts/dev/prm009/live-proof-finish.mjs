import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";

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
    headers: { Authorization: `Bearer ${op}`, Accept: "application/json" },
  });
  return { status: res.status, body: await res.json() };
}

execSync(
  `docker exec prm009-hub-postgres psql -U prm009 -d hub_prm009 -c "insert into orders (id,user_id,product_id,gateway_reference,gateway_ref,external_resource_id,status,created_at,updated_at) select ('20000000-0000-4000-8000-00000005'||lpad(n::text,4,'0'))::uuid,'10000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000002','proc-n5-'||n,'hub:homolog-padaria:n5'||n,json_build_object('app_id','homolog-padaria','sandbox',true,'test_order',true,'amount_cents',5000,'currency','BRL')::text,'PAID',now(),now() from generate_series(1,30) n on conflict do nothing;"`,
  { stdio: "inherit" }
);
await fetch("http://127.0.0.1:8098/__test/reset-counts", { method: "POST" });
await fetch("http://127.0.0.1:8098/__test/list-fail-after", {
  method: "PUT",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ after: 1 }),
});
const partial = await sync();
const firstNew = "20000000-0000-4000-8000-000000050001";
execSync(
  `docker exec prm009-hub-postgres psql -U prm009 -d hub_prm009 -c "update orders set status='REFUNDED', updated_at=now() where id='${firstNew}';"`,
  { stdio: "inherit" }
);
await fetch("http://127.0.0.1:8098/__test/list-fail-after", {
  method: "PUT",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ after: null }),
});
const resume = await sync();
const list = await (
  await fetch(`http://127.0.0.1:8091/api/v1/pay-receipts?companyId=${company}`, {
    headers: { Authorization: `Bearer ${op}` },
  })
).json();
const changed = (list.items || []).find((i) => i.transactionId === firstNew);
const hubBefore = await (await fetch("http://127.0.0.1:4101/__test/counts")).json();
const edgeBefore = await (await fetch("http://127.0.0.1:8098/__test/counts")).json();

writeFileSync(
  "c:/Projetos/ActionFinance/documents/reviews/evidence/prm-009-continuidade-001/live-fail-resume.json",
  JSON.stringify(
    {
      partial: { http: partial.status, run: partial.body.run },
      resume: { http: resume.status, run: resume.body.run, resumed: resume.body.resumed },
      updatedDuringWindow: changed && changed.normalizedStatus,
      hubBefore,
      edgeBefore,
    },
    null,
    2
  )
);
console.log(
  `PARTIAL imported=${partial.body.run?.importedCount} pages=${partial.body.run?.pageCount} status=${partial.body.run?.status}`
);
console.log(
  `RESUME imported=${resume.body.run?.importedCount} updated=${resume.body.run?.updatedCount} resumed=${resume.body.resumed} status=${resume.body.run?.status}`
);
console.log(`WINDOW_UPDATE ${changed && changed.normalizedStatus}`);
console.log(`HUB_BEFORE ${hubBefore.counts.list}`);
