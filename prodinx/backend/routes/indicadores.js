const express = require("express");
const {
  listarIndicadoresConfig,
  atualizarIndicadorConfig,
} = require("../services/indicadores_config_api");

function createIndicadoresRouter(pool) {
  const router = express.Router();

  router.get("/config", async (_req, res, next) => {
    try {
      const indicadores = await listarIndicadoresConfig(pool);
      res.json({
        total: indicadores.length,
        indicadores,
      });
    } catch (error) {
      next(error);
    }
  });

  router.put("/config/:cod_indicador", async (req, res, next) => {
    try {
      const codIndicador = String(req.params.cod_indicador || "").trim();
      const nomeGrupo = req.query.nome_grupo
        ? String(req.query.nome_grupo).trim()
        : null;

      if (!codIndicador) {
        return res.status(400).json({
          erro: "cod_indicador é obrigatório na rota",
        });
      }

      const resultado = await atualizarIndicadorConfig(
        pool,
        codIndicador,
        req.body,
        nomeGrupo
      );

      res.json({
        mensagem: "Configuração do indicador atualizada com sucesso",
        ...resultado,
      });
    } catch (error) {
      next(error);
    }
  });

  return router;
}

module.exports = createIndicadoresRouter;
