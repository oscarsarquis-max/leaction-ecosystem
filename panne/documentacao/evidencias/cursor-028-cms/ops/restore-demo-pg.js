const fs = require("fs");
const path = require("path");
const { Client } = require("pg");
require("dotenv").config({ path: path.join(__dirname, "..", "..", ".env"), override: false });

async function main() {
  const defaults = JSON.parse(
    fs.readFileSync("C:/Projetos/panne/documentacao/evidencias/cursor-028-cms/hub-panne-demo-defaults.json", "utf8")
  );
  const landing = defaults.landing_page_data;
  const instructions = defaults.instructions_data || null;
  const databaseUrl =
    process.env.DATABASE_URL ||
    "postgresql://admin:password123@127.0.0.1:5433/leaction_hub";
  const client = new Client({
    connectionString: databaseUrl.replace(/([?&])sslmode=[^&]*/gi, "$1").replace(/[?&]$/, "").replace(/\?&/, "?"),
    ssl: false,
  });
  await client.connect();
  const before = await client.query(
    `SELECT landing_page_data->'columns'->0->>'title' AS t FROM cms_site_config WHERE config_key=$1`,
    ["panne-demo"]
  );
  console.log("BEFORE", before.rows[0]?.t);
  await client.query(
    `INSERT INTO cms_site_config (config_key, landing_page_data, instructions_data, updated_at)
     VALUES ($1, $2::jsonb, $3, CURRENT_TIMESTAMP)
     ON CONFLICT (config_key) DO UPDATE
       SET landing_page_data = EXCLUDED.landing_page_data,
           instructions_data = EXCLUDED.instructions_data,
           updated_at = CURRENT_TIMESTAMP`,
    ["panne-demo", JSON.stringify(landing), instructions]
  );
  const after = await client.query(
    `SELECT landing_page_data->'columns'->0->>'title' AS t FROM cms_site_config WHERE config_key=$1`,
    ["panne-demo"]
  );
  const panne = await client.query(
    `SELECT landing_page_data->'columns'->0->>'title' AS t FROM cms_site_config WHERE config_key=$1`,
    ["panne"]
  );
  console.log("AFTER", after.rows[0]?.t);
  console.log("PANNE", panne.rows[0]?.t);
  await client.end();
  if (String(after.rows[0]?.t || "").includes("SYNTH")) {
    console.error("RESTORE_FAIL");
    process.exit(2);
  }
  console.log("RESTORE_OK");
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
