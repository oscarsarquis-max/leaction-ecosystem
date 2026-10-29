'use strict';

const crypto = require('crypto');
const { listPublicCatalog } = require('./catalog-public');
const { getEntitlementForSubject } = require('./entitlements-api');
const {
  findActiveCatalogSubscription,
  parseHubPayload,
  processPreapprovalLifecycle,
} = require('./catalog-subscription');
const {
  ensureCreditOperationsTable,
  reserveCredits,
  confirmCredits,
  releaseCredits,
} = require('./credits-ops');

const PROVIDER_ID = 'actionhub-biblioteca';
const SECRET_HEADER = 'X-ActionHub-Biblioteca-Credential';
const CAPABILITIES = new Set([
  'LIST_HUB_CATALOG',
  'GET_HUB_ENTITLEMENTS',
  'LIST_HUB_SUBSCRIPTIONS',
  'START_HUB_CATALOG_CHECKOUT',
  'CANCEL_HUB_SUBSCRIPTION',
  'RESERVE_HUB_CREDITS',
  'CONFIRM_HUB_CREDITS',
  'RELEASE_HUB_CREDITS',
]);

function timingSafeEqual(expected, provided) {
  if (!expected || !provided) return false;
  const a = Buffer.from(String(expected), 'utf8');
  const b = Buffer.from(String(provided), 'utf8');
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

function providerSecret(env = process.env) {
  return String(env.ACTIONHUB_BIBLIOTECA_PROVIDER_SECRET || '').trim();
}

function authorized(req, env = process.env) {
  const expected = providerSecret(env);
  if (!expected) return false;
  const provided = String(req.headers['x-actionhub-biblioteca-credential'] || '').trim();
  return timingSafeEqual(expected, provided);
}

function envelopeOk(body, capabilityId) {
  return (
    body &&
    body.contractVersion === '1.5' &&
    body.capabilityId === capabilityId &&
    body.requestId &&
    body.correlationId
  );
}

function completed(reqBody, result) {
  return {
    status: 'COMPLETED',
    providerId: PROVIDER_ID,
    requestId: reqBody.requestId,
    correlationId: reqBody.correlationId,
    capabilityId: reqBody.capabilityId,
    result,
  };
}

async function listSubscriptions(pool, appId, subjectId) {
  const rows = await pool.query(
    `SELECT s.id, s.status, s.mp_preapproval_id, s.amount, s.frequency, s.frequency_type,
            s.order_id, o.external_resource_id
     FROM subscriptions s
     JOIN orders o ON o.id = s.order_id
     WHERE o.external_resource_id::text LIKE $1
     ORDER BY s.created_at DESC`,
    [`%"app_id":"${appId}"%`]
  );
  const items = rows.rows
    .map((row) => {
      const payload = parseHubPayload(row.external_resource_id);
      if (String(payload.subject_id || '').toLowerCase() !== subjectId.toLowerCase()) return null;
      return {
        id: row.id,
        sku: payload.sku,
        status: row.status,
        amount: Number(row.amount),
        frequency: row.frequency,
        frequency_type: row.frequency_type,
        cancelable: ['authorized', 'pending', 'paused'].includes(String(row.status || '').toLowerCase()),
      };
    })
    .filter(Boolean);
  return {
    app_id: appId,
    subject_id: subjectId,
    subscriptions: items,
    cancel_policy:
      'O cancelamento interrompe a renovação automática. O período já pago e os créditos daquele ciclo continuam até o vencimento. Sem pró-rata.',
  };
}

async function executeCapability(pool, capabilityId, inputs, helpers) {
  const appId = String(inputs.appId || '').trim().toLowerCase();
  const subjectId = String(inputs.subjectId || '').trim();
  if (appId !== 'lojadepaes') {
    return { status: 403, body: { error: 'appId não autorizado nesta capacidade' } };
  }
  if (capabilityId === 'LIST_HUB_CATALOG') {
    return listPublicCatalog(pool, appId);
  }
  if (capabilityId === 'GET_HUB_ENTITLEMENTS') {
    if (!subjectId) return { status: 400, body: { error: 'subjectId obrigatório' } };
    return { status: 200, body: await getEntitlementForSubject(pool, { appId, subjectId }) };
  }
  if (capabilityId === 'LIST_HUB_SUBSCRIPTIONS') {
    if (!subjectId) return { status: 400, body: { error: 'subjectId obrigatório' } };
    return { status: 200, body: await listSubscriptions(pool, appId, subjectId) };
  }
  if (capabilityId === 'START_HUB_CATALOG_CHECKOUT') {
    if (!helpers.startCatalogCheckout) {
      return { status: 503, body: { error: 'checkout do catálogo indisponível' } };
    }
    return helpers.startCatalogCheckout({
      app_id: appId,
      sku: String(inputs.sku || ''),
      subject_id: subjectId,
      email: subjectId,
      return_origin: inputs.returnOrigin,
      return_to: inputs.returnTo,
    });
  }
  if (capabilityId === 'CANCEL_HUB_SUBSCRIPTION') {
    if (!subjectId) return { status: 400, body: { error: 'subjectId obrigatório' } };
    const sku = String(inputs.sku || 'LOJADEPAES_BIBLIOTECA_MENSAL');
    const active = await findActiveCatalogSubscription(pool, { appId, subjectId, sku });
    if (!active?.mp_preapproval_id) {
      return { status: 404, body: { error: 'assinatura vigente não encontrada' } };
    }
    if (!helpers.cancelPreapproval) {
      return { status: 503, body: { error: 'cancelamento indisponível' } };
    }
    await helpers.cancelPreapproval(active.mp_preapproval_id, 'cancelled');
    const lifecycle = await processPreapprovalLifecycle(
      pool,
      { id: active.mp_preapproval_id, status: 'cancelled' },
      { cancelPreapproval: helpers.cancelPreapproval }
    );
    return {
      status: 200,
      body: {
        ok: true,
        status: 'cancelled',
        sku,
        cancelled_dependents: lifecycle.cancelled_dependents || [],
        message:
          'A renovação automática foi cancelada. O período já pago continua até o vencimento. Não há reembolso proporcional.',
      },
    };
  }
  if (
    capabilityId === 'RESERVE_HUB_CREDITS' ||
    capabilityId === 'CONFIRM_HUB_CREDITS' ||
    capabilityId === 'RELEASE_HUB_CREDITS'
  ) {
    const operationId = String(inputs.operationId || '').trim();
    if (!subjectId || !operationId) {
      return { status: 400, body: { error: 'subjectId e operationId obrigatórios' } };
    }
    await ensureCreditOperationsTable(pool);
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      const handler =
        capabilityId === 'RESERVE_HUB_CREDITS'
          ? reserveCredits
          : capabilityId === 'CONFIRM_HUB_CREDITS'
            ? confirmCredits
            : releaseCredits;
      const result = await handler(client, {
        appId,
        subjectId,
        operationId,
        amount: inputs.amount == null ? 1 : inputs.amount,
      });
      if (!result.ok) {
        await client.query('ROLLBACK');
        return {
          status: result.statusCode || 409,
          body: {
            ok: false,
            error: result.error,
            reason: result.error,
            credits: result.credits,
            valid_until: result.valid_until || null,
          },
        };
      }
      await client.query('COMMIT');
      return {
        status: 200,
        body: {
          ok: true,
          status: result.status,
          idempotent: Boolean(result.idempotent),
          credits: result.credits,
          valid_until: result.valid_until || null,
        },
      };
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }
  return { status: 404, body: { error: 'capacidade não implementada' } };
}

function registerSpiderBibliotecaRoutes(app, pool, options = {}) {
  const env = options.env || process.env;
  const helpers = {
    cancelPreapproval: options.cancelPreapproval,
    startCatalogCheckout: options.startCatalogCheckout,
  };
  for (const capability of CAPABILITIES) {
    app.post(`/v1/provider/capabilities/${capability}/executions`, async (req, res) => {
    const capabilityId = capability;
    if (!authorized(req, env)) {
      return res.status(401).json({ error: 'credencial de provedor ausente ou inválida' });
    }
    const body = req.body && typeof req.body === 'object' ? req.body : {};
    if (!envelopeOk(body, capabilityId)) {
      return res.status(400).json({ error: 'envelope de capacidade inválido' });
    }
    const inputs = body.inputs && typeof body.inputs === 'object' ? body.inputs : {};
    try {
      const executed = await executeCapability(pool, capabilityId, inputs, helpers);
      if (executed.status >= 400) {
        return res.status(executed.status).json({
          status: 'FAILED',
          providerId: PROVIDER_ID,
          requestId: body.requestId,
          correlationId: body.correlationId,
          capabilityId,
          result: executed.body,
        });
      }
      return res.status(200).json(completed(body, executed.body));
    } catch (err) {
      console.error('❌ [spider-biblioteca]', err.message);
      return res.status(500).json({ error: 'erro ao executar capacidade da Biblioteca' });
    }
  });
  }
}

module.exports = {
  PROVIDER_ID,
  SECRET_HEADER,
  CAPABILITIES,
  registerSpiderBibliotecaRoutes,
  executeCapability,
};
