import express from "express";

const app = express();
app.use(express.json({ limit: "1mb" }));
const port = Number(process.env.PORT || 8081);
const spiderUrl = process.env.SPIDER_URL || "http://localhost:8080";

const callbacks = [];

app.get("/health", (_req, res) => res.json({ status: "ok", system: "originador" }));

app.get("/api/callbacks", (_req, res) => res.json(callbacks.slice(-20)));

app.post("/api/callback", (req, res) => {
  const entry = {
    at: new Date().toISOString(),
    traceparent: req.header("traceparent"),
    body: req.body,
  };
  callbacks.push(entry);
  console.log("[callback]", JSON.stringify(entry));
  res.status(202).json({ accepted: true });
});

/** Dispara orquestração no Spider (utilitário local de teste). */
app.post("/api/iniciar", async (req, res) => {
  const payload = {
    productId: req.body?.productId || "CONTA_DIGITAL_ONBOARDING",
    transactionId: req.body?.transactionId || `tx-${Date.now()}`,
    payload: req.body?.payload || { canal: "originador-mock" },
  };
  try {
    const r = await fetch(`${spiderUrl}/v1/products/orchestrate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/problem+json",
        traceparent: req.header("traceparent") || "",
      },
      body: JSON.stringify(payload),
    });
    const body = await r.json();
    res.status(r.status).json(body);
  } catch (e) {
    res.status(502).json({ title: "Spider unreachable", detail: String(e) });
  }
});

app.listen(port, () => console.log(`service-originador on :${port}`));
