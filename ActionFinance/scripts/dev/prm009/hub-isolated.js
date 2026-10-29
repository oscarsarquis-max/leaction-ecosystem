/**
 * Processo isolado do endpoint real de listagem Pay.
 * Monta registerSpiderPayLookupRoutes do gateway-api.
 * Não lê DATABASE_URL do Hub compartilhado (:5433).
 */
const path = require("path");
const http = require("http");

const gatewayRoot = path.resolve(__dirname, "..", "..", "..", "..", "leaction-platform", "services", "gateway-api");
const express = require(path.join(gatewayRoot, "node_modules", "express"));
const { Pool } = require(path.join(gatewayRoot, "node_modules", "pg"));
const { registerSpiderPayLookupRoutes } = require(path.join(gatewayRoot, "domain", "spider-pay-lookup"));

const DATABASE_URL = process.env.PRM009_HUB_DATABASE_URL || "";
if (!DATABASE_URL || !/127\.0\.0\.1|localhost/i.test(DATABASE_URL)) {
  throw new Error("PRM009_HUB_DATABASE_URL deve apontar para Postgres local descartável");
}
if (/5433/.test(DATABASE_URL)) {
  throw new Error("PRM009 recusa a porta 5433 (Hub compartilhado / não descartável)");
}

const PORT = Number(process.env.PRM009_HUB_PORT || 4101);
const counts = { list: 0, lookup: 0 };
const app = express();
app.use(express.json());
app.use((req, _res, next) => {
  if (req.method === "GET" && req.path === "/v1/integration/payments") {
    counts.list += 1;
  } else if (req.method === "GET" && req.path.startsWith("/v1/integration/payments/")) {
    counts.lookup += 1;
  }
  next();
});
app.get("/health", (_req, res) => {
  res.status(200).json({
    status: "UP",
    service: "prm009-hub-isolated",
    code: "spider-pay-lookup.js",
    testLabeled: true,
    counts,
  });
});
app.get("/__test/counts", (req, res) => {
  const host = String((req.socket && req.socket.remoteAddress) || "");
  if (host !== "127.0.0.1" && host !== "::1" && host !== ":ffff:127.0.0.1") {
    return res.status(404).json({ error: "not found" });
  }
  res.status(200).json({ counts });
});

const pool = new Pool({ connectionString: DATABASE_URL });
registerSpiderPayLookupRoutes(app, pool);

const server = http.createServer(app);
server.listen(PORT, "127.0.0.1", () => {
  process.stdout.write(`prm009-hub-isolated 127.0.0.1:${PORT} disposable-postgres\n`);
});
