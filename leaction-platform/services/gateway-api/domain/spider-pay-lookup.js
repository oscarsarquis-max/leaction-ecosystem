const crypto = require('crypto');

const ISOLATED_ORDERS_SCHEMA = 'prm009_public_test';

function timingSafeEqual(expected, provided) {
  if (!expected || !provided) return false;
  const a = Buffer.from(String(expected), 'utf8');
  const b = Buffer.from(String(provided), 'utf8');
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

function lookupEnabled(env = process.env) {
  if (env.ACTIONHUB_PAY_LOOKUP_ENABLED !== 'true') return false;
  return env.ACTIONHUB_PAY_LOOKUP_ISOLATED === 'true' || env.ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST === 'true';
}

function sanitizeStatus(row) {
  const status = String(row.status || '').toUpperCase();
  if (status === 'PAID') return { externalStatus: 'CONFIRMED', deliveryStatus: 'DELIVERED' };
  if (status === 'CANCELLED' || status === 'CANCELED') {
    return { externalStatus: 'REFUSED', deliveryStatus: 'DELIVERED' };
  }
  if (status === 'PENDING') return { externalStatus: 'IN_PROGRESS', deliveryStatus: 'DELIVERED' };
  if (status === 'REFUNDED') return { externalStatus: 'REFUNDED', deliveryStatus: 'DELIVERED' };
  return { externalStatus: 'REVIEW_REQUIRED', deliveryStatus: 'DELIVERED' };
}

function extractAppId(row) {
  const ref = String(row.gateway_ref || '');
  const hub = ref.match(/^hub:([^:]+):/);
  if (hub) return hub[1];
  const amount = ref.match(/^amount:([^:]+):/);
  if (amount) return amount[1];
  try {
    const payload = JSON.parse(row.external_resource_id || '{}');
    if (payload && payload.app_id) return String(payload.app_id);
  } catch {
    return null;
  }
  return null;
}

function parsePayload(row) {
  try {
    const payload = JSON.parse(row.external_resource_id || '{}');
    return payload && typeof payload === 'object' ? payload : {};
  } catch {
    return {};
  }
}

function isIsolatedLookup(env = process.env) {
  return env.ACTIONHUB_PAY_LOOKUP_ISOLATED === 'true';
}

function ordersRelation(env = process.env) {
  return isIsolatedLookup(env) ? `${ISOLATED_ORDERS_SCHEMA}.orders` : 'public.orders';
}

function isProvenSandbox(row, env = process.env) {
  if (isIsolatedLookup(env)) {
    return true;
  }
  const payload = parsePayload(row);
  return payload.sandbox === true || payload.test_order === true;
}

function amountMinorOf(row) {
  const payload = parsePayload(row);
  if (Number.isInteger(payload.amount_cents) && payload.amount_cents > 0) {
    return String(payload.amount_cents);
  }
  return null;
}

const MAX_LIST_LIMIT = 50;
const DEFAULT_LIST_LIMIT = 25;

function currencyOf(row) {
  const payload = parsePayload(row);
  const raw = payload.currency || payload.currency_id;
  if (typeof raw === 'string' && /^[A-Za-z]{3}$/.test(raw.trim())) {
    return raw.trim().toUpperCase();
  }
  return null;
}

function amountMinorForList(row) {
  const payload = parsePayload(row);
  if (Number.isInteger(payload.amount_cents) && payload.amount_cents >= 0) {
    return { amountMinor: String(payload.amount_cents), amountSource: 'amount_cents', reviewRequired: false };
  }
  if (Number.isInteger(payload.paid_amount_cents) && payload.paid_amount_cents >= 0) {
    return {
      amountMinor: String(payload.paid_amount_cents),
      amountSource: 'paid_amount_cents',
      reviewRequired: false,
    };
  }
  if (payload.valor_negociado != null && payload.valor_negociado !== '') {
    const reais = Number(payload.valor_negociado);
    if (!Number.isFinite(reais) || reais < 0) {
      return { amountMinor: null, amountSource: 'valor_negociado_invalid', reviewRequired: true };
    }
    const cents = Math.round(reais * 100);
    if (Math.abs(reais * 100 - cents) > 1e-6) {
      return { amountMinor: null, amountSource: 'valor_negociado_imprecise', reviewRequired: true };
    }
    return { amountMinor: String(cents), amountSource: 'valor_negociado_brl', reviewRequired: false };
  }
  return { amountMinor: null, amountSource: 'absent', reviewRequired: true };
}

function toIso(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function toCursorIso(value) {
  return toIso(value);
}

function listOrderSql() {
  return `ORDER BY date_trunc('milliseconds', updated_at) ASC, id::text ASC`;
}

function publicListItem(row, options = {}) {
  const mapped = sanitizeStatus(row);
  const amount = amountMinorForList(row);
  const updatedAt = toIso(row.updated_at);
  const createdAt = toIso(row.created_at);
  return {
    transactionId: String(row.id),
    orderReference: String(row.id),
    processorReference: row.gateway_reference ? String(row.gateway_reference) : null,
    companyBinding: extractAppId(row),
    origin: 'ACTIONHUB_PAY',
    environment: options.environment || null,
    originalStatus: String(row.status || '').toUpperCase() || null,
    normalizedStatus: mapped.externalStatus,
    amountMinor: amount.amountMinor,
    amountAbsent: amount.amountMinor == null,
    amountSource: amount.amountSource,
    currency: currencyOf(row),
    createdAt,
    updatedAt,
    originRevision: updatedAt,
    testLabeled: options.sandbox === true,
    reviewRequired: amount.reviewRequired || !updatedAt,
  };
}

function encodeListCursor(scope) {
  return Buffer.from(
    JSON.stringify({
      v: 1,
      a: scope.appId,
      e: scope.environment,
      u: scope.updatedAt,
      i: scope.id,
    }),
    'utf8'
  ).toString('base64url');
}

function decodeListCursor(raw, expectedAppId, expectedEnvironment) {
  if (!raw) return { ok: true, cursor: null };
  let parsed;
  try {
    parsed = JSON.parse(Buffer.from(String(raw), 'base64url').toString('utf8'));
  } catch {
    return { ok: false, error: 'cursor inválido' };
  }
  if (!parsed || parsed.v !== 1 || !parsed.a || !parsed.e || !parsed.u || !parsed.i) {
    return { ok: false, error: 'cursor inválido' };
  }
  if (parsed.a !== expectedAppId || parsed.e !== expectedEnvironment) {
    return { ok: false, error: 'cursor de outro escopo' };
  }
  const updatedAt = new Date(parsed.u);
  if (Number.isNaN(updatedAt.getTime())) {
    return { ok: false, error: 'cursor inválido' };
  }
  return { ok: true, cursor: { updatedAt, id: String(parsed.i) } };
}

function normalizeListEnvironment(raw) {
  const value = String(raw || '').trim().toUpperCase();
  if (!value) return 'HOMOLOG';
  if (value === 'HOMOLOG' || value === 'SANDBOX') return value;
  return null;
}

function parseListLimit(raw) {
  if (raw == null || raw === '') return DEFAULT_LIST_LIMIT;
  const n = Number(raw);
  if (!Number.isInteger(n) || n < 1 || n > MAX_LIST_LIMIT) return null;
  return n;
}

function publicLookup(row, options = {}) {
  const mapped = sanitizeStatus(row);
  return {
    providerId: 'actionhub-pay',
    status: 'COMPLETED',
    result: {
      providerReference: String(row.id),
      externalStatus: mapped.externalStatus,
      deliveryStatus: mapped.deliveryStatus,
      amountMinor: amountMinorOf(row),
      currency: 'BRL',
      sandbox: options.sandbox === true,
      origin: 'ACTIONHUB_PAY',
      providerObservedAt: row.updated_at ? new Date(row.updated_at).toISOString() : null,
    },
  };
}

function registerSpiderPayLookupRoutes(app, pool, options = {}) {
  const env = options.env || process.env;
  app.get('/v1/integration/payments', async (req, res) => {
    if (!lookupEnabled(env)) {
      return res.status(404).json({ error: 'not found' });
    }
    const secret = options.providerSecret || env.ACTIONHUB_PAY_PROVIDER_SECRET || '';
    if (!secret) {
      return res.status(503).json({ error: 'borda de integração indisponível' });
    }
    const provided = req.get('X-Spider-Provider-Key') || '';
    if (!timingSafeEqual(secret, provided)) {
      return res.status(401).json({ error: 'credencial de provedor inválida' });
    }
    const payAppId = String(req.get('X-Pay-App-Id') || '');
    if (!payAppId) {
      return res.status(403).json({ error: 'aplicativo Pay não informado pela Spider' });
    }
    const environment = normalizeListEnvironment(req.query.environment);
    if (!environment) {
      return res.status(400).json({ error: 'ambiente incompatível' });
    }
    if (environment === 'SANDBOX' && env.ACTIONHUB_PAY_ENVIRONMENT !== 'sandbox') {
      return res.status(403).json({ error: 'ambiente incompatível' });
    }
    const limit = parseListLimit(req.query.limit);
    if (limit == null) {
      return res.status(400).json({ error: 'limite de página inválido' });
    }
    const decoded = decodeListCursor(req.query.cursor, payAppId, environment);
    if (!decoded.ok) {
      return res.status(403).json({ error: decoded.error });
    }
    try {
      const isolated = isIsolatedLookup(env);
      const params = [payAppId];
      let sql = `SELECT id, status, gateway_ref, gateway_reference, external_resource_id, created_at, updated_at
         FROM ${ordersRelation(env)}
         WHERE (
           gateway_ref LIKE ('hub:' || $1 || ':%')
           OR gateway_ref LIKE ('amount:' || $1 || ':%')
           OR external_resource_id LIKE ('%"app_id":"' || $1 || '"%')
         )`;
      if (!isolated) {
        sql += ` AND (
           external_resource_id LIKE '%"sandbox":true%'
           OR external_resource_id LIKE '%"test_order":true%'
         )`;
      }
      if (decoded.cursor) {
        params.push(toCursorIso(decoded.cursor.updatedAt), decoded.cursor.id);
        sql += ` AND (date_trunc('milliseconds', updated_at), id::text) > ($${params.length - 1}::timestamptz, $${params.length})`;
      }
      sql += ` ${listOrderSql()} LIMIT ${limit + 1}`;
      const result = await pool.query(sql, params);
      const owned = result.rows.filter((row) => extractAppId(row) === payAppId && isProvenSandbox(row, env));
      const pageRows = owned.slice(0, limit);
      const items = pageRows.map((row) => publicListItem(row, { sandbox: true, environment }));
      const last = pageRows[pageRows.length - 1];
      const nextCursor =
        owned.length > limit && last
          ? encodeListCursor({
              appId: payAppId,
              environment,
              updatedAt: toCursorIso(last.updated_at),
              id: String(last.id),
            })
          : null;
      return res.status(200).json({
        providerId: 'actionhub-pay',
        status: 'COMPLETED',
        environment,
        testLabeled: true,
        itemCount: items.length,
        nextCursor,
        items,
      });
    } catch (err) {
      console.error('[spider-pay-lookup] listagem falhou');
      return res.status(500).json({ error: 'Erro interno no servidor' });
    }
  });
  app.get('/v1/integration/payments/:orderId', async (req, res) => {
    if (!lookupEnabled(env)) {
      return res.status(404).json({ error: 'not found' });
    }
    const secret = options.providerSecret || env.ACTIONHUB_PAY_PROVIDER_SECRET || '';
    if (!secret) {
      return res.status(503).json({ error: 'borda de integração indisponível' });
    }
    const provided = req.get('X-Spider-Provider-Key') || '';
    if (!timingSafeEqual(secret, provided)) {
      return res.status(401).json({ error: 'credencial de provedor inválida' });
    }
    const payAppId = String(req.get('X-Pay-App-Id') || '');
    if (!payAppId) {
      return res.status(403).json({ error: 'aplicativo Pay não informado pela Spider' });
    }
    try {
      const result = await pool.query(
        `SELECT id, status, gateway_ref, external_resource_id, updated_at
         FROM ${ordersRelation(env)}
         WHERE id = $1
         LIMIT 1`,
        [req.params.orderId]
      );
      const row = result.rows[0];
      if (!row) {
        return res.status(404).json({ error: 'pagamento de teste não encontrado' });
      }
      const owner = extractAppId(row);
      if (!owner || owner !== payAppId) {
        return res.status(404).json({ error: 'pagamento de teste não encontrado' });
      }
      if (!isProvenSandbox(row, env)) {
        return res.status(403).json({ error: 'consulta bloqueada: ambiente de teste não comprovado' });
      }
      return res.status(200).json(publicLookup(row, { sandbox: true }));
    } catch (err) {
      console.error('[spider-pay-lookup] consulta falhou');
      return res.status(500).json({ error: 'Erro interno no servidor' });
    }
  });
}

module.exports = {
  registerSpiderPayLookupRoutes,
  timingSafeEqual,
  extractAppId,
  sanitizeStatus,
  publicLookup,
  publicListItem,
  amountMinorForList,
  currencyOf,
  encodeListCursor,
  decodeListCursor,
  toCursorIso,
  listOrderSql,
  normalizeListEnvironment,
  parseListLimit,
  lookupEnabled,
  isIsolatedLookup,
  ordersRelation,
  isProvenSandbox,
  ISOLATED_ORDERS_SCHEMA,
  MAX_LIST_LIMIT,
  DEFAULT_LIST_LIMIT,
};
