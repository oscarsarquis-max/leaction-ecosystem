const express = require("express");
const { processarIngestaoJson } = require("../services/ingestao_json_service");

function createIngestaoRouter(pool) {
  const router = express.Router();

  /**
   * POST /api/ingestao/json
   * Recebe o JSON completo (WorkItems_History / Snapshot por pessoa)
   * e aplica o pipeline ETL para a tabela medicoes.
   */
  router.post("/json", async (req, res, next) => {
    try {
      if (!req.body || typeof req.body !== "object" || Array.isArray(req.body)) {
        return res.status(400).json({
          erro: "Corpo da requisição deve ser um objeto JSON",
        });
      }

      const nomeArquivo =
        (req.query.nome_arquivo && String(req.query.nome_arquivo).trim()) ||
        (req.headers["x-nome-arquivo"] &&
          String(req.headers["x-nome-arquivo"]).trim()) ||
        null;

      const verbose =
        req.query.verbose === "1" ||
        req.query.verbose === "true" ||
        req.query.verbose === "sim";

      const resultado = await processarIngestaoJson(pool, req.body, {
        nomeArquivo,
        verbose,
      });

      res.status(201).json(resultado);
    } catch (error) {
      next(error);
    }
  });

  return router;
}

module.exports = createIngestaoRouter;
