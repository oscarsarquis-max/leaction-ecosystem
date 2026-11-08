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
  return (
    env.ACTIONHUB_PAY_LOOKUP_ISOLATED === 'true' ||
    env.ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST === 'true' ||
    env.ACTIONHUB_PAY_LOOKUP_OPERATIONAL === 'true'
  );
}

function operationalAppIds(env = process.env) {
  return String(env.ACTIONHUB_PAY_OPERATIONAL_APP_IDS || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
}

function isOperationalApp(env, appId) {
  return env.ACTIONHUB_PAY_LOOKUP_OPERATIONAL === 'true' && operationalAppIds(env).includes(String(appId || ''));
}

function classifyOrderDetail(row) {
  const payload = parsePayload(row);
  if (payload.sandbox === true) {
    return { classification: 'TEST', reason: 'payload.sandbox=true' };
  }
  if (payload.test_order === true) {
    return { classification: 'TEST', reason: 'payload.test_order=true' };
  }
  if (payload.live_mode === false || payload.mp_live_mode === false) {
    return { classification: 'TEST', reason: 'live_mode=false' };
  }
  if (payload.live_mode === true || payload.mp_live_mode === true) {
    return { classification: 'REAL', reason: 'live_mode=true' };
  }
  return {
    classification: 'INDETERMINATE',
    reason: 'sem live_mode nem flag de teste; mp_payment_id, payment_request_id e prefixo amount: não comprovam ambiente',
  };
}

function classifyOrder(row) {
  return classifyOrderDetail(row).classification;
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

function ordersRelation(env = process.env, appId) {
  if (isOperationalApp(env, appId)) {
    return 'public.orders';
  }
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

function confirmedPaid(row) {
  const paid = paidAmountMinorOf(row);
  if (paid == null) {
    return {};
  }
  return { paidAmountMinor: paid, paidAmountAbsent: false };
}

function paidAmountMinorOf(row) {
  const payload = parsePayload(row);
  if (payload.paid_amount_confirmed !== true) {
    return null;
  }
  if (Number.isInteger(payload.paid_amount_cents) && payload.paid_amount_cents >= 0) {
    return String(payload.paid_amount_cents);
  }
  return null;
}

function paymentMethodOf(row) {
  const payload = parsePayload(row);
  const raw = payload.method || payload.payment_method;
  return typeof raw === 'string' && raw.trim() ? raw.trim() : null;
}

function firstNonEmpty(...values) {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

function payerOf(row) {
  const payload = parsePayload(row);
  const email = firstNonEmpty(row.payer_email, payload.payer_email, payload.customer_email);
  const subject = firstNonEmpty(payload.subject_id, row.subject_id);
  if (email) {
    return { payerKind: 'EMAIL', payerLabel: email, payerProvenance: 'ACTIONHUB_PAY' };
  }
  if (subject) {
    return { payerKind: 'SUBJECT', payerLabel: subject, payerProvenance: 'ACTIONHUB_PAY' };
  }
  return { payerKind: 'ABSENT', payerLabel: null, payerProvenance: null };
}

function commercialOf(row) {
  const payload = parsePayload(row);
  return {
    commercialApplication: firstNonEmpty(payload.app_id, extractAppId(row)),
    commercialDescription: firstNonEmpty(payload.plano_nome, row.product_name, payload.sku, row.product_sku),
  };
}

function providerStatusOf(row) {
  const payload = parsePayload(row);
  const pixStatus = payload.pix && typeof payload.pix === 'object' ? payload.pix.status : null;
  return firstNonEmpty(payload.provider_status, pixStatus);
}

function processorNameOf(row) {
  const payload = parsePayload(row);
  const named = firstNonEmpty(payload.processor, payload.processor_name);
  if (named) {
    return named;
  }
  if (payload.mp_payment_id || payload.mp_live_mode != null || payload.pix) {
    return 'Mercado Pago';
  }
  return null;
}

function channelOf(row) {
  const payload = parsePayload(row);
  const raw = payload.source || payload.channel;
  return typeof raw === 'string' && raw.trim() ? raw.trim() : null;
}

function currencyOf(row) {
  const payload = parsePayload(row);
  const raw = payload.currency || payload.currency_id;
  if (typeof raw === 'string' && /^[A-Za-z]{3}$/.test(raw.trim())) {
    return raw.trim().toUpperCase();
  }
  return null;
}

function chargedAmountForList(row) {
  const payload = parsePayload(row);
  if (Number.isInteger(payload.amount_cents) && payload.amount_cents >= 0) {
    return { amountMinor: String(payload.amount_cents), amountSource: 'amount_cents', reviewRequired: false };
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

function amountMinorForList(row) {
  return chargedAmountForList(row);
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

function listOrderSql(alias) {
  const prefix = alias ? `${alias}.` : '';
  return `ORDER BY date_trunc('milliseconds', ${prefix}updated_at) ASC, ${prefix}id::text ASC`;
}

function publicListItem(row, options = {}) {
  const mapped = sanitizeStatus(row);
  const amount = amountMinorForList(row);
  const updatedAt = toIso(row.updated_at);
  const createdAt = toIso(row.created_at);
  const classified = classifyOrderDetail(row);
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
    chargedAmountMinor: amount.amountMinor,
    ...confirmedPaid(row),
    paymentMethod: paymentMethodOf(row),
    ...payerOf(row),
    ...commercialOf(row),
    providerStatus: providerStatusOf(row),
    processorName: processorNameOf(row),
    channel: channelOf(row),
    currency: currencyOf(row),
    classification: classified.classification,
    classificationReason: classified.reason,
    createdAt,
    updatedAt,
    originRevision: updatedAt,
    testLabeled: options.sandbox === true,
    reviewRequired: amount.reviewRequired || !updatedAt,
  };
}

function publicReviewItem(row, options = {}) {
  const item = publicListItem(row, options);
  const detail = classifyOrderDetail(row);
  return {
    ...item,
    classification: detail.classification,
    classificationReason: options.reasonOverride || detail.reason,
    reviewRequired: true,
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
  if (value === 'HOMOLOG' || value === 'SANDBOX' || value === 'PRODUCTION') return value;
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

function providedProviderSecret(req) {
  return (
    req.get('X-ActionHub-Pay-Credential') ||
    req.get('X-Spider-Provider-Key') ||
    ''
  );
}

function validateProviderListEnvelope(body) {
  if (!body || typeof body !== 'object') {
    return 'payload inválido';
  }
  const inputs = body.inputs || {};
  if (body.capabilityId !== 'LIST_PAYMENT_TRANSACTIONS') {
    return 'capacidade não autorizada';
  }
  if (body.contractVersion !== '1.4') {
    return 'contrato 1.4 obrigatório';
  }
  if (!inputs.payAppId || !inputs.companyId || !inputs.environment) {
    return 'empresa, aplicativo ou ambiente não autorizados pela Spider';
  }
  if (!body.requestId || !body.correlationId) {
    return 'requestId e correlationId obrigatórios';
  }
  if (inputs.environment !== 'HOMOLOG' && inputs.environment !== 'SANDBOX' && inputs.environment !== 'PRODUCTION') {
    return 'ambiente incompatível';
  }
  return null;
}

function completedProviderList(body, result) {
  return {
    status: 'COMPLETED',
    providerId: 'actionhub-pay',
    requestId: body.requestId,
    correlationId: body.correlationId,
    capabilityId: 'LIST_PAYMENT_TRANSACTIONS',
    result: {
      companyId: String(body.inputs.companyId),
      payAppId: String(body.inputs.payAppId),
      environment: String(body.inputs.environment),
      origin: result.origin || 'ACTIONHUB_PAY',
      testLabeled: result.testLabeled === true,
      itemCount: Array.isArray(result.items) ? result.items.length : 0,
      reviewCount: Array.isArray(result.reviews) ? result.reviews.length : 0,
      nextCursor: result.nextCursor || null,
      items: Array.isArray(result.items) ? result.items : [],
      reviews: Array.isArray(result.reviews) ? result.reviews : [],
    },
  };
}

const MAX_SCAN_ROWS = 500;

async function fetchOrderPage(pool, env, payAppId, limitPlus, cursor) {
  const operational = isOperationalApp(env, payAppId);
  const isolated = isIsolatedLookup(env);
  const params = [payAppId];
  const useJoin = operational || !isolated;
  const relation = ordersRelation(env, payAppId);
  let sql;
  if (useJoin) {
    sql = `SELECT o.id, o.status, o.gateway_ref, o.gateway_reference, o.external_resource_id, o.created_at, o.updated_at,
         u.email AS payer_email, p.name AS product_name, p.sku AS product_sku
         FROM ${relation} o
         LEFT JOIN users u ON u.id = o.user_id
         LEFT JOIN products p ON p.id = o.product_id
         WHERE (
           o.gateway_ref LIKE ('hub:' || $1 || ':%')
           OR o.gateway_ref LIKE ('amount:' || $1 || ':%')
           OR o.external_resource_id LIKE ('%"app_id":"' || $1 || '"%')
         )`;
  } else {
    sql = `SELECT id, status, gateway_ref, gateway_reference, external_resource_id, created_at, updated_at,
         NULL::text AS payer_email, NULL::text AS product_name, NULL::text AS product_sku
         FROM ${relation}
         WHERE (
           gateway_ref LIKE ('hub:' || $1 || ':%')
           OR gateway_ref LIKE ('amount:' || $1 || ':%')
           OR external_resource_id LIKE ('%"app_id":"' || $1 || '"%')
         )`;
  }
  if (!operational && !isolated) {
    const extCol = useJoin ? 'o.external_resource_id' : 'external_resource_id';
    sql += ` AND (
           ${extCol} LIKE '%"sandbox":true%'
           OR ${extCol} LIKE '%"test_order":true%'
         )`;
  }
  if (cursor) {
    params.push(toCursorIso(cursor.updatedAt), cursor.id);
    const updatedCol = useJoin ? 'o.updated_at' : 'updated_at';
    const idCol = useJoin ? 'o.id::text' : 'id::text';
    sql += ` AND (date_trunc('milliseconds', ${updatedCol}), ${idCol}) > ($${params.length - 1}::timestamptz, $${params.length})`;
  }
  sql += ` ${listOrderSql(useJoin ? 'o' : '')} LIMIT ${limitPlus}`;
  const result = await pool.query(sql, params);
  return result.rows;
}

async function queryPaymentList(pool, env, payAppId, environment, limit, cursor) {
  if (environment === 'SANDBOX' && env.ACTIONHUB_PAY_ENVIRONMENT !== 'sandbox') {
    return { httpStatus: 403, error: 'ambiente incompatível' };
  }
  const operational = isOperationalApp(env, payAppId);
  if (operational && environment !== 'PRODUCTION') {
    return { httpStatus: 403, error: 'ambiente incompatível' };
  }
  if (!operational && environment === 'PRODUCTION') {
    return { httpStatus: 403, error: 'ambiente incompatível' };
  }
  const decoded = decodeListCursor(cursor, payAppId, environment);
  if (!decoded.ok) {
    return { httpStatus: 403, error: decoded.error };
  }
  const items = [];
  const reviews = [];
  let lastConsumed = null;
  let moreAfterConsumed = false;
  let scanCursor = decoded.cursor;
  let scanned = 0;
  const batchSize = Math.max(limit + 1, 25);

  while (items.length < limit && scanned < MAX_SCAN_ROWS) {
    const take = Math.min(batchSize, MAX_SCAN_ROWS - scanned);
    const rows = await fetchOrderPage(pool, env, payAppId, take + 1, scanCursor);
    const hasMoreSql = rows.length > take;
    const page = rows.slice(0, take);
    if (page.length === 0) {
      moreAfterConsumed = false;
      break;
    }
    let filled = false;
    for (let i = 0; i < page.length; i += 1) {
      const row = page[i];
      scanned += 1;
      lastConsumed = row;
      if (extractAppId(row) !== payAppId) {
        reviews.push(
          publicReviewItem(row, {
            environment,
            sandbox: false,
            reasonOverride: 'app_id divergente do recorte',
          })
        );
        continue;
      }
      if (operational) {
        const detail = classifyOrderDetail(row);
        if (detail.classification === 'REAL') {
          items.push(publicListItem(row, { sandbox: false, environment }));
          if (items.length >= limit) {
            moreAfterConsumed = i < page.length - 1 || hasMoreSql;
            filled = true;
            break;
          }
        } else {
          reviews.push(publicReviewItem(row, { environment, sandbox: detail.classification === 'TEST' }));
        }
      } else if (!isProvenSandbox(row, env)) {
        reviews.push(
          publicReviewItem(row, {
            environment,
            sandbox: false,
            reasonOverride: 'sandbox não comprovado',
          })
        );
      } else {
        items.push(publicListItem(row, { sandbox: true, environment }));
        if (items.length >= limit) {
          moreAfterConsumed = i < page.length - 1 || hasMoreSql;
          filled = true;
          break;
        }
      }
    }
    if (filled) {
      break;
    }
    if (!hasMoreSql) {
      moreAfterConsumed = false;
      break;
    }
    scanCursor = { updatedAt: lastConsumed.updated_at, id: String(lastConsumed.id) };
  }

  const nextCursor =
    moreAfterConsumed && lastConsumed
      ? encodeListCursor({
          appId: payAppId,
          environment,
          updatedAt: toCursorIso(lastConsumed.updated_at),
          id: String(lastConsumed.id),
        })
      : null;
  return { httpStatus: 200, environment, items, reviews, nextCursor };
}

function registerSpiderPayLookupRoutes(app, pool, options = {}) {
  const env = options.env || process.env;
  const requireLookup = (req, res) => {
    if (!lookupEnabled(env)) {
      res.status(404).json({ error: 'not found' });
      return false;
    }
    const secret = options.providerSecret || env.ACTIONHUB_PAY_PROVIDER_SECRET || '';
    if (!secret) {
      res.status(503).json({ error: 'borda de integração indisponível' });
      return false;
    }
    if (!timingSafeEqual(secret, providedProviderSecret(req))) {
      res.status(401).json({ error: 'credencial de provedor inválida' });
      return false;
    }
    return true;
  };
  app.get('/v1/integration/payments', async (req, res) => {
    if (!requireLookup(req, res)) return;
    const payAppId = String(req.get('X-Pay-App-Id') || '');
    if (!payAppId) {
      return res.status(403).json({ error: 'aplicativo Pay não informado pela Spider' });
    }
    const environment = normalizeListEnvironment(req.query.environment);
    if (!environment) {
      return res.status(400).json({ error: 'ambiente incompatível' });
    }
    const limit = parseListLimit(req.query.limit);
    if (limit == null) {
      return res.status(400).json({ error: 'limite de página inválido' });
    }
    try {
      const listed = await queryPaymentList(pool, env, payAppId, environment, limit, req.query.cursor);
      if (listed.httpStatus !== 200) {
        return res.status(listed.httpStatus).json({ error: listed.error });
      }
      return res.status(200).json({
        providerId: 'actionhub-pay',
        status: 'COMPLETED',
        environment: listed.environment,
        testLabeled: true,
        itemCount: listed.items.length,
        reviewCount: Array.isArray(listed.reviews) ? listed.reviews.length : 0,
        nextCursor: listed.nextCursor,
        items: listed.items,
        reviews: listed.reviews || [],
      });
    } catch (err) {
      console.error('[spider-pay-lookup] listagem falhou');
      return res.status(500).json({ error: 'Erro interno no servidor' });
    }
  });
  app.post('/v1/provider/capabilities/LIST_PAYMENT_TRANSACTIONS/executions', async (req, res) => {
    if (!requireLookup(req, res)) return;
    const body = req.body || {};
    const invalid = validateProviderListEnvelope(body);
    if (invalid) {
      return res.status(invalid.includes('autorizad') || invalid.includes('ambiente') ? 403 : 400).json({
        error: invalid,
      });
    }
    const inputs = body.inputs;
    const limit = parseListLimit(inputs.limit);
    if (limit == null) {
      return res.status(400).json({ error: 'limite de página inválido' });
    }
    try {
      const listed = await queryPaymentList(
        pool,
        env,
        String(inputs.payAppId),
        String(inputs.environment),
        limit,
        inputs.cursor
      );
      if (listed.httpStatus !== 200) {
        return res.status(listed.httpStatus).json({
          status: 'FAILED',
          providerId: 'actionhub-pay',
          error: listed.error,
        });
      }
      return res.status(200).json(
        completedProviderList(body, {
          origin: 'ACTIONHUB_PAY',
          testLabeled: true,
          items: listed.items,
          reviews: listed.reviews || [],
          nextCursor: listed.nextCursor,
        })
      );
    } catch (err) {
      console.error('[spider-pay-lookup] execução de listagem falhou');
      return res.status(500).json({ error: 'Erro interno no servidor' });
    }
  });
  app.get('/v1/integration/payments/:orderId', async (req, res) => {
    if (!requireLookup(req, res)) return;
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
  providedProviderSecret,
  validateProviderListEnvelope,
  completedProviderList,
  timingSafeEqual,
  extractAppId,
  sanitizeStatus,
  publicLookup,
  publicListItem,
  amountMinorForList,
  chargedAmountForList,
  currencyOf,
  encodeListCursor,
  decodeListCursor,
  toCursorIso,
  listOrderSql,
  normalizeListEnvironment,
  parseListLimit,
  lookupEnabled,
  isIsolatedLookup,
  isOperationalApp,
  operationalAppIds,
  classifyOrder,
  classifyOrderDetail,
  queryPaymentList,
  ordersRelation,
  isProvenSandbox,
  ISOLATED_ORDERS_SCHEMA,
  MAX_LIST_LIMIT,
  DEFAULT_LIST_LIMIT,
};
