import express from "express";

const app = express();
app.use(express.json());
const port = Number(process.env.PORT || 8092);

app.get("/health", (_req, res) => res.json({ status: "ok", system: "credito" }));

app.post("/api/credito/analise", (req, res) => {
  const customerExternalId = req.body?.customerExternalId ?? "unknown";
  res.json({
    status: "OK",
    system: "credito",
    customerExternalId,
    score: 720,
    decisao: "APROVADO_MOCK",
    limiteSugerido: 5000,
  });
});

app.listen(port, () => {
  console.log(`mock-sistema-credito on :${port}`);
});
