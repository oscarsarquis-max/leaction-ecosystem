import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { execSync } from "node:child_process";

const evidence = "c:/Projetos/ActionFinance/documents/reviews/evidence/prm-009-continuidade-001";
mkdirSync(evidence, { recursive: true });
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
const af = "http://127.0.0.1:8091";

async function afCall(method, path, token = op) {
  const url = `${af}${path}${path.includes("?") ? "&" : "?"}companyId=${company}`;
  const res = await fetch(url, { method, headers: { Authorization: `Bearer ${token}`, Accept: "application/json" } });
  const text = await res.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    body = { raw: text };
  }
  return { status: res.status, body };
}

execSync(
  `docker exec prm009-hub-postgres psql -U prm009 -d hub_prm009 -c "insert into orders (id,user_id,product_id,gateway_reference,gateway_ref,external_resource_id,status,created_at,updated_at) select ('20000000-0000-4000-8000-00000003'||lpad(n::text,4,'0'))::uuid,'10000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000002','proc-n3-'||n,'hub:homolog-padaria:n3'||n,json_build_object('app_id','homolog-padaria','sandbox',true,'test_order',true,'amount_cents',4000,'currency','BRL')::text,'PENDING',now(),now() from generate_series(1,30) n on conflict do nothing;"`,
  { stdio: "inherit" }
);
await fetch("http://127.0.0.1:8098/__test/reset-counts", { method: "POST" });
await fetch("http://127.0.0.1:8098/__test/list-fail-after", {
  method: "PUT",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ after: 1 }),
});
const hubBefore = await (await fetch("http://127.0.0.1:4101/__test/counts")).json();
const partial = await afCall("POST", "/api/v1/pay-receipts/sync");
const edgeAfterPartial = await (await fetch("http://127.0.0.1:8098/__test/counts")).json();
await fetch("http://127.0.0.1:8098/__test/list-fail-after", {
  method: "PUT",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ after: null }),
});
const resume = await afCall("POST", "/api/v1/pay-receipts/sync");

execSync(
  `docker exec prm009-hub-postgres psql -U prm009 -d hub_prm009 -c "insert into orders (id,user_id,product_id,gateway_reference,gateway_ref,external_resource_id,status,created_at,updated_at) select ('20000000-0000-4000-8000-00000004'||lpad(n::text,4,'0'))::uuid,'10000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000002','proc-n4-'||n,'hub:homolog-padaria:n4'||n,json_build_object('app_id','homolog-padaria','sandbox',true,'test_order',true,'amount_cents',4100,'currency','BRL')::text,'PAID',now(),now() from generate_series(1,20) n on conflict do nothing;"`,
  { stdio: "inherit" }
);
const [a, b] = await Promise.all([
  afCall("POST", "/api/v1/pay-receipts/sync"),
  afCall("POST", "/api/v1/pay-receipts/sync"),
]);

const viewerTok = tokens.ACTIONFINANCE_DEMO_TOKEN_VIEWER_A;
const viewer = await afCall("POST", "/api/v1/pay-receipts/sync", viewerTok);

const report = {
  hubBefore,
  partial: { http: partial.status, run: partial.body.run },
  edgeAfterPartial,
  resume: { http: resume.status, run: resume.body.run, resumed: resume.body.resumed },
  concurrent: [a.status, b.status],
  viewer: viewer.status,
};
writeFileSync(`${evidence}/live-node.json`, JSON.stringify(report, null, 2));
console.log(
  `PARTIAL ${partial.status} ${partial.body.run?.status} imported=${partial.body.run?.importedCount} pages=${partial.body.run?.pageCount} err=${partial.body.run?.lastError}`
);
console.log(`RESUME ${resume.status} ${resume.body.run?.status} imported=${resume.body.run?.importedCount} resumed=${resume.body.resumed}`);
console.log(`CONCURRENT ${a.status} ${b.status}`);
console.log(`VIEWER ${viewer.status}`);
