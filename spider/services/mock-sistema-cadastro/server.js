import express from "express";

const app = express();
const port = Number(process.env.PORT || 8091);

app.get("/health", (_req, res) => res.json({ status: "ok", system: "cadastro" }));

app.get("/api/cadastro/:id", (req, res) => {
  const id = req.params.id;
  res.json({
    status: "OK",
    system: "cadastro",
    customerExternalId: id,
    nome: `Cliente Mock ${id}`,
    documentoMascarado: "***.***.***-**",
    situacao: "ATIVO",
  });
});

app.listen(port, () => {
  console.log(`mock-sistema-cadastro on :${port}`);
});
