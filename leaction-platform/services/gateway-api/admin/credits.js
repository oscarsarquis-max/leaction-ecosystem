'use strict';

/**
 * POST /admin/credits/inject — cortesia / bounty (créditos manuais).
 */

const { createContractService } = require('../domain/contract-service');
const { kickOutboxNow } = require('../domain/outbox-worker');

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ requireAdmin: import('express').RequestHandler }} deps
 */
function registerAdminCreditsRoutes(app, pool, { requireAdmin }) {
  const contractService = createContractService(pool);

  app.post('/admin/credits/inject', requireAdmin, async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const appId = body.app_id;
      const subjectId = body.subject_id;
      const amount = body.amount;
      const reason = body.reason;

      const result = await contractService.inject_manual_credits(
        appId,
        subjectId,
        amount,
        reason
      );
      kickOutboxNow(pool);

      return res.status(200).json({
        success: true,
        message: 'Créditos injetados com sucesso. Evento CREDITS_GRANTED enfileirado.',
        ...result,
      });
    } catch (err) {
      const status = Number(err.statusCode) || 500;
      if (status >= 500) {
        console.error('❌ [admin/credits inject]', err.message);
      }
      return res.status(status).json({
        error: err.message || 'Erro ao injetar créditos',
      });
    }
  });
}

module.exports = {
  registerAdminCreditsRoutes,
};
