'use strict';

/**
 * Reserva / confirmação / liberação de créditos para satélites.
 * POST /v1/credits/reserve|confirm|release
 * Auth: a mesma de GET /v1/entitlements.
 */

const { authenticateApp, extractCallerSecret } = require('./entitlements-api');
const {
  ensureCreditOperationsTable,
  reserveCredits,
  confirmCredits,
  releaseCredits,
} = require('./credits-ops');

function readBody(req) {
  const body = req.body && typeof req.body === 'object' ? req.body : {};
  return {
    appId: String(body.app_id || '').trim().toLowerCase(),
    subjectId: String(body.subject_id || '').trim(),
    operationId: String(body.operation_id || '').trim(),
    amount: body.amount == null ? 1 : body.amount,
  };
}

async function withAuth(pool, req, res) {
  const { appId, subjectId, operationId, amount } = readBody(req);
  if (!appId || !subjectId || !operationId) {
    res.status(400).json({
      error: 'Campos obrigatórios: app_id, subject_id, operation_id',
    });
    return null;
  }
  if (operationId.length > 80) {
    res.status(400).json({ error: 'operation_id inválido' });
    return null;
  }
  const secret = extractCallerSecret(req);
  if (!secret) {
    res.status(401).json({
      error: 'Credencial ausente. Envie Authorization: Bearer <secret> ou header X-App-Secret.',
    });
    return null;
  }
  const auth = await authenticateApp(pool, appId, secret);
  if (!auth.ok) {
    res.status(auth.status).json({ error: auth.error });
    return null;
  }
  return { appId, subjectId, operationId, amount };
}

function registerCreditsRoutes(app, pool) {
  const run = (handler) => async (req, res) => {
    try {
      await ensureCreditOperationsTable(pool);
      const parsed = await withAuth(pool, req, res);
      if (!parsed) return;
      const client = await pool.connect();
      try {
        await client.query('BEGIN');
        const result = await handler(client, parsed);
        if (!result.ok) {
          await client.query('ROLLBACK');
          return res.status(result.statusCode || 409).json({
            error: result.error,
            status: result.status || null,
            credits: result.credits,
            valid_until: result.valid_until || null,
          });
        }
        await client.query('COMMIT');
        return res.status(200).json({
          ok: true,
          status: result.status,
          idempotent: Boolean(result.idempotent),
          credits: result.credits,
          valid_until: result.valid_until || null,
          app_id: parsed.appId,
          subject_id: parsed.subjectId,
          operation_id: parsed.operationId,
        });
      } catch (err) {
        try {
          await client.query('ROLLBACK');
        } catch {
          /* ignore */
        }
        throw err;
      } finally {
        client.release();
      }
    } catch (err) {
      console.error('❌ Erro em /v1/credits:', err.message);
      return res.status(500).json({ error: 'Erro interno no servidor' });
    }
  };

  app.post(
    '/v1/credits/reserve',
    run((client, parsed) => reserveCredits(client, parsed))
  );
  app.post(
    '/v1/credits/confirm',
    run((client, parsed) => confirmCredits(client, parsed))
  );
  app.post(
    '/v1/credits/release',
    run((client, parsed) => releaseCredits(client, parsed))
  );
}

module.exports = {
  registerCreditsRoutes,
};
