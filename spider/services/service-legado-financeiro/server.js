import express from "express";

const app = express();
app.use(express.json({ limit: "1mb" }));
const port = Number(process.env.PORT || 8082);

app.get("/health", (_req, res) => res.json({ status: "ok", system: "legado-financeiro" }));

app.post("/api/legado/processar", (req, res) => {
  const traceparent = req.header("traceparent");
  console.log("[legado] processar", { traceparent, body: req.body });
  res.json({
    status: "PAYMENT_CONFIRMED",
    system: "legado-financeiro",
    productId: req.body?.productId,
    transactionId: req.body?.transactionId,
    processedAt: new Date().toISOString(),
  });
});

app.listen(port, () => console.log(`service-legado-financeiro on :${port}`));
