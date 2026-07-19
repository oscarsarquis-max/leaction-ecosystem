/**
 * ContractService — Fase 1B
 * Orquestra ativação de contrato após pagamento e alimenta o outbox de webhooks.
 *
 * Tudo-ou-nada em transação própria (orders.PAID já deve ter sido marcado pelo fulfill).
 */

const crypto = require('crypto');

const LOG = '[ContractService]';

/**
 * @param {import('pg').Pool} pool
 */
function createContractService(pool) {
  /**
   * Ativa contrato a partir de uma order PAID.
   * @param {string} orderId UUID da order
   * @returns {Promise<object>} resumo da ativação
   */
  async function activateFromOrder(orderId) {
    if (!orderId) {
      const err = new Error('order_id é obrigatório');
      err.statusCode = 400;
      throw err;
    }

    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      const orderRow = await loadOrderContext(client, orderId);
      if (!orderRow) {
        const err = new Error(`Order não encontrada: ${orderId}`);
        err.statusCode = 404;
        throw err;
      }

      if (String(orderRow.status || '').toUpperCase() !== 'PAID') {
        const err = new Error(
          `Order ${orderId} não está PAID (status=${orderRow.status}). Ativação abortada.`
        );
        err.statusCode = 409;
        throw err;
      }

      // Idempotência: já ativada para este pedido
      const existingByOrder = await client.query(
        `SELECT id, app_id, subject_id, status FROM contracts WHERE order_id = $1 LIMIT 1`,
        [orderId]
      );
      if (existingByOrder.rows.length > 0) {
        const c = existingByOrder.rows[0];
        console.log(
          `${LOG} info: contrato já existe para order=${orderId} contract=${c.id} — noop idempotente`
        );
        await client.query('COMMIT');
        return {
          idempotent: true,
          contract_id: c.id,
          app_id: c.app_id,
          subject_id: c.subject_id,
          status: c.status,
        };
      }

      const hubPayload = parseHubPayload(orderRow.external_resource_id);
      const appId = resolveAppId(orderRow, hubPayload);
      const { subjectType, subjectId } = resolveSubject(orderRow, hubPayload);
      const items = buildContractItems(orderRow, hubPayload);
      const endsAt = resolveEndsAt(hubPayload, orderRow.product_type);
      const subscriptionId = orderRow.subscription_id || null;

      await ensureAppRegistry(client, appId);

      console.log(
        `${LOG} info: ativando order=${orderId} app=${appId} subject=${subjectType}:${subjectId} items=${items.length}`
      );

      // --- contracts ---
      const contractResult = await client.query(
        `INSERT INTO contracts (
           app_id, subject_type, subject_id, status,
           started_at, ends_at, order_id, subscription_id,
           external_ref, meta_json, created_at, updated_at
         ) VALUES (
           $1, $2, $3, 'active',
           CURRENT_TIMESTAMP, $4, $5, $6,
           $7, $8::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
         )
         RETURNING id, status, started_at, ends_at`,
        [
          appId,
          subjectType,
          subjectId,
          endsAt,
          orderId,
          subscriptionId,
          orderRow.gateway_ref || null,
          JSON.stringify({
            product_type: orderRow.product_type,
            product_sku: orderRow.product_sku,
            product_name: orderRow.product_name,
            customer_email: orderRow.customer_email,
            hub_payload: hubPayload,
          }),
        ]
      );
      const contract = contractResult.rows[0];

      // --- contract_items ---
      for (const item of items) {
        await client.query(
          `INSERT INTO contract_items (
             contract_id, item_type, sku, quantity, unit_label, meta_json
           ) VALUES ($1, $2, $3, $4, $5, $6::jsonb)`,
          [
            contract.id,
            item.item_type,
            item.sku,
            item.quantity,
            item.unit_label,
            JSON.stringify(item.meta_json || {}),
          ]
        );
      }

      // --- entitlement_snapshots (upsert + merge créditos) ---
      const snap = await computeEntitlementUpsert(client, appId, subjectId, items, endsAt, hubPayload);

      // --- webhook_outbox ---
      const hasCredits = items.some((i) => i.item_type === 'credit_pack');
      const eventType = hasCredits ? 'CREDITS_GRANTED' : 'CONTRACT_ACTIVATED';
      const idempotencyKey = `order_${orderId}_activation`;
      // Delta desta compra (não o saldo acumulado do snapshot — satélites fazem += )
      const creditsAdded = items
        .filter((i) => i.item_type === 'credit_pack')
        .reduce((sum, i) => sum + (Number(i.quantity) || 0), 0);
      const outboxPayload = {
        subject_type: subjectType,
        subject_id: subjectId,
        contract_id: contract.id,
        order_id: orderId,
        event_type: eventType,
        credits: creditsAdded,
        credits_added: creditsAdded,
        credits_balance: snap.payload.credits ?? 0,
        plan: snap.payload.plan || null,
        premium: Boolean(snap.payload.premium),
        items: items.map((i) => ({
          item_type: i.item_type,
          sku: i.sku,
          quantity: i.quantity,
        })),
        valid_until: endsAt,
      };

      await client.query(
        `INSERT INTO webhook_outbox (
           app_id, event_type, payload_json, idempotency_key,
           status, attempts, next_retry_at, created_at
         ) VALUES (
           $1, $2, $3::jsonb, $4,
           'pending', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
         )
         ON CONFLICT (idempotency_key) DO NOTHING`,
        [appId, eventType, JSON.stringify(outboxPayload), idempotencyKey]
      );

      await client.query('COMMIT');
      console.log(
        `${LOG} info: OK order=${orderId} contract=${contract.id} event=${eventType} credits=${outboxPayload.credits}`
      );

      return {
        idempotent: false,
        contract_id: contract.id,
        app_id: appId,
        subject_type: subjectType,
        subject_id: subjectId,
        status: 'active',
        event_type: eventType,
        entitlement: snap.payload,
        idempotency_key: idempotencyKey,
      };
    } catch (err) {
      try {
        await client.query('ROLLBACK');
      } catch (rbErr) {
        console.error(`${LOG} error: rollback falhou:`, rbErr.message);
      }
      console.error(
        `${LOG} error: activate_from_order falhou order=${orderId}:`,
        err.message
      );
      throw err;
    } finally {
      client.release();
    }
  }

  /**
   * Injeta créditos manuais (cortesia / bounty) no snapshot e enfileira CREDITS_GRANTED.
   * @param {string} appId
   * @param {string} subjectId e-mail (ou outro subject_id da app)
   * @param {number} amount inteiro > 0
   * @param {string} reason
   */
  async function injectManualCredits(appId, subjectId, amount, reason) {
    const normalizedAppId = String(appId || '').trim().toLowerCase();
    const normalizedSubject = String(subjectId || '').trim().toLowerCase();
    const creditsAdded = Number.parseInt(String(amount), 10);
    const reasonText = String(reason || '').trim();

    if (!normalizedAppId) {
      throw Object.assign(new Error('app_id é obrigatório'), { statusCode: 400 });
    }
    if (!normalizedSubject) {
      throw Object.assign(new Error('subject_id é obrigatório'), { statusCode: 400 });
    }
    if (!Number.isFinite(creditsAdded) || creditsAdded <= 0) {
      throw Object.assign(new Error('amount deve ser um inteiro positivo'), { statusCode: 400 });
    }
    if (!reasonText) {
      throw Object.assign(new Error('reason é obrigatório'), { statusCode: 400 });
    }

    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      const appRow = await client.query(
        `SELECT app_id FROM app_registry WHERE app_id = $1 AND active = TRUE LIMIT 1`,
        [normalizedAppId]
      );
      if (appRow.rows.length === 0) {
        throw Object.assign(new Error(`Aplicação não encontrada ou inativa: ${normalizedAppId}`), {
          statusCode: 404,
        });
      }

      const prevRes = await client.query(
        `SELECT payload_json
         FROM entitlement_snapshots
         WHERE app_id = $1 AND subject_id = $2
         FOR UPDATE`,
        [normalizedAppId, normalizedSubject]
      );

      const prevRaw = prevRes.rows[0]?.payload_json || {};
      const prevObj = typeof prevRaw === 'string' ? JSON.parse(prevRaw) : { ...prevRaw };
      const previousCredits = Number(prevObj.credits || 0) || 0;
      const newCredits = previousCredits + creditsAdded;

      const payload = {
        ...prevObj,
        credits: newCredits,
        updated_from: 'manual_inject',
        last_manual_inject: {
          credits_added: creditsAdded,
          reason: reasonText,
          at: new Date().toISOString(),
        },
        updated_at: new Date().toISOString(),
      };

      await client.query(
        `INSERT INTO entitlement_snapshots (app_id, subject_id, payload_json, valid_until, updated_at)
         VALUES ($1, $2, $3::jsonb, NULL, CURRENT_TIMESTAMP)
         ON CONFLICT (app_id, subject_id) DO UPDATE SET
           payload_json = EXCLUDED.payload_json,
           updated_at = CURRENT_TIMESTAMP`,
        [normalizedAppId, normalizedSubject, JSON.stringify(payload)]
      );

      const idempotencyKey = `bounty_${crypto.randomUUID()}`;
      const outboxPayload = {
        subject_id: normalizedSubject,
        credits_added: creditsAdded,
        // alias para satélites que leem `credits` (ex.: inove4us webhook)
        credits: creditsAdded,
        reason: reasonText,
        event_type: 'CREDITS_GRANTED',
        source: 'manual_inject',
      };

      await client.query(
        `INSERT INTO webhook_outbox (
           app_id, event_type, payload_json, idempotency_key,
           status, attempts, next_retry_at, created_at
         ) VALUES (
           $1, 'CREDITS_GRANTED', $2::jsonb, $3,
           'pending', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
         )`,
        [normalizedAppId, JSON.stringify(outboxPayload), idempotencyKey]
      );

      await client.query('COMMIT');
      console.log(
        `${LOG} info: inject_manual_credits app=${normalizedAppId} subject=${normalizedSubject} +${creditsAdded} → ${newCredits} key=${idempotencyKey}`
      );

      return {
        app_id: normalizedAppId,
        subject_id: normalizedSubject,
        credits_added: creditsAdded,
        credits_balance: newCredits,
        reason: reasonText,
        idempotency_key: idempotencyKey,
        event_type: 'CREDITS_GRANTED',
      };
    } catch (err) {
      try {
        await client.query('ROLLBACK');
      } catch (rbErr) {
        console.error(`${LOG} error: rollback falhou:`, rbErr.message);
      }
      console.error(
        `${LOG} error: inject_manual_credits falhou app=${normalizedAppId} subject=${normalizedSubject}:`,
        err.message
      );
      throw err;
    } finally {
      client.release();
    }
  }

  return {
    activateFromOrder,
    /** alias snake_case pedido no prompt */
    activate_from_order: activateFromOrder,
    injectManualCredits,
    inject_manual_credits: injectManualCredits,
  };
}

async function loadOrderContext(client, orderId) {
  const result = await client.query(
    `SELECT
       o.id,
       o.status,
       o.gateway_ref,
       o.external_resource_id,
       o.paid_at,
       p.sku AS product_sku,
       p.name AS product_name,
       p.type AS product_type,
       u.email AS customer_email,
       u.full_name AS customer_name,
       (
         SELECT s.id FROM subscriptions s
         WHERE s.order_id = o.id
         ORDER BY s.created_at DESC
         LIMIT 1
       ) AS subscription_id
     FROM orders o
     JOIN products p ON p.id = o.product_id
     LEFT JOIN users u ON u.id = o.user_id
     WHERE o.id = $1
     FOR UPDATE OF o`,
    [orderId]
  );
  return result.rows[0] || null;
}

function parseHubPayload(externalResourceId) {
  if (externalResourceId == null) return null;
  const raw = String(externalResourceId).trim();
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object') return parsed;
  } catch {
    /* id_matu numérico legado */
  }
  if (/^\d+$/.test(raw)) {
    return { id_matu: Number(raw) };
  }
  return null;
}

function resolveAppId(order, hubPayload) {
  if (hubPayload?.app_id) return String(hubPayload.app_id).trim().toLowerCase();
  const ref = String(order.gateway_ref || '');
  // hub:{client_id}:{orderId}
  const m = ref.match(/^hub:([^:]+):/i);
  if (m && m[1]) return m[1].trim().toLowerCase();

  const t = String(order.product_type || '');
  if (t.startsWith('PANELDX')) return 'paneldx';
  if (t.startsWith('INOVE') || /inove4us/i.test(String(order.product_sku || ''))) {
    return 'inove4us';
  }
  return 'paneldx';
}

function resolveSubject(order, hubPayload) {
  if (hubPayload?.id_clie != null && String(hubPayload.id_clie).trim() !== '') {
    return { subjectType: 'tenant', subjectId: String(hubPayload.id_clie).trim() };
  }
  if (hubPayload?.subject_id) {
    return {
      subjectType: String(hubPayload.subject_type || 'email').trim(),
      subjectId: String(hubPayload.subject_id).trim(),
    };
  }
  const email = String(order.customer_email || '').trim().toLowerCase();
  if (email) {
    return { subjectType: 'email', subjectId: email };
  }
  throw Object.assign(new Error('Não foi possível determinar subject_id da order'), {
    statusCode: 400,
  });
}

function mapProductTypeToItemType(productType) {
  switch (String(productType || '')) {
    case 'PANELDX_ADDON':
      return 'addon';
    case 'PANELDX_SUBSCRIPTION':
      return 'plan';
    case 'MOODLE_COURSE':
      return 'plan';
    case 'PANELDX_ASSESSMENT':
      return 'plan';
    default:
      return 'plan';
  }
}

function buildContractItems(order, hubPayload) {
  // Checkout de catálogo grava o SKU real em hubPayload.sku (product pode ser HUB_CATALOG bridge)
  const sku = String(hubPayload?.sku || order.product_sku || 'UNKNOWN').trim();
  const productType = String(order.product_type || '');
  const declaredType = String(
    hubPayload?.item_type || hubPayload?.catalog_type || ''
  ).toLowerCase();

  // Pacote de créditos (inove4us / genérico / catalog_plans)
  const credits =
    Number(
      hubPayload?.credits ??
        hubPayload?.credit_quantity ??
        hubPayload?.quantidade_creditos ??
        0
    ) || 0;
  const isCreditPack =
    declaredType === 'credit_pack' ||
    credits > 0 ||
    /credit/i.test(sku);

  if (isCreditPack && credits > 0) {
    return [
      {
        item_type: 'credit_pack',
        sku,
        quantity: credits,
        unit_label: 'créditos',
        meta_json: { hub_payload: hubPayload, product_type: productType },
      },
    ];
  }

  if (productType === 'PANELDX_ADDON') {
    const qty = Number(hubPayload?.quantidade || 1) || 1;
    return [
      {
        item_type: 'addon',
        sku,
        quantity: qty,
        unit_label: 'seats',
        meta_json: {
          id_plano_addon: hubPayload?.id_plano_addon,
          plano_nome: hubPayload?.plano_nome,
          product_type: productType,
        },
      },
    ];
  }

  // Assento explícito
  if (declaredType === 'seat') {
    return [
      {
        item_type: 'seat',
        sku,
        quantity: Number(hubPayload?.quantidade || hubPayload?.seats || 1) || 1,
        unit_label: 'seats',
        meta_json: { hub_payload: hubPayload },
      },
    ];
  }

  // Catálogo Hub (product bridge HUB_CATALOG) — respeita type do catalog_plans
  if (
    (productType === 'HUB_CATALOG' || hubPayload?.source === 'catalog_checkout') &&
    (declaredType === 'plan' || declaredType === 'addon')
  ) {
    return [
      {
        item_type: declaredType,
        sku,
        quantity: Number(hubPayload?.quantidade || hubPayload?.seats || 1) || 1,
        unit_label: declaredType === 'addon' ? 'seats' : hubPayload?.periodicidade || 'plano',
        meta_json: {
          id_plano: hubPayload?.id_plano || hubPayload?.catalog_plan_id,
          plano_nome: hubPayload?.plano_nome,
          periodicidade: hubPayload?.periodicidade,
          product_type: productType,
          hub_payload: hubPayload,
        },
      },
    ];
  }

  return [
    {
      item_type: mapProductTypeToItemType(productType),
      sku,
      quantity: 1,
      unit_label: hubPayload?.periodicidade || 'plano',
      meta_json: {
        id_plano: hubPayload?.id_plano,
        plano_nome: hubPayload?.plano_nome,
        periodicidade: hubPayload?.periodicidade,
        product_type: productType,
      },
    },
  ];
}

function resolveEndsAt(hubPayload, productType) {
  if (hubPayload?.ends_at) {
    const d = new Date(hubPayload.ends_at);
    if (!Number.isNaN(d.getTime())) return d.toISOString();
  }
  const months = Number(hubPayload?.period_months || hubPayload?.meses || 0);
  if (months > 0) {
    const d = new Date();
    d.setMonth(d.getMonth() + months);
    return d.toISOString();
  }
  const period = String(hubPayload?.periodicidade || '').toLowerCase();
  const d = new Date();
  if (period.includes('anual') || period === 'year' || period === 'yearly') {
    d.setFullYear(d.getFullYear() + 1);
    return d.toISOString();
  }
  if (
    period.includes('mensal') ||
    period === 'month' ||
    period === 'monthly' ||
    String(productType) === 'PANELDX_SUBSCRIPTION'
  ) {
    d.setMonth(d.getMonth() + 1);
    return d.toISOString();
  }
  return null;
}

async function ensureAppRegistry(client, appId) {
  await client.query(
    `INSERT INTO app_registry (app_id, name, return_origins, active)
     VALUES ($1, $2, '{}', TRUE)
     ON CONFLICT (app_id) DO NOTHING`,
    [appId, appId]
  );
}

async function computeEntitlementUpsert(client, appId, subjectId, items, endsAt, hubPayload) {
  const prevRes = await client.query(
    `SELECT payload_json, valid_until
     FROM entitlement_snapshots
     WHERE app_id = $1 AND subject_id = $2
     FOR UPDATE`,
    [appId, subjectId]
  );
  const prev = prevRes.rows[0]?.payload_json || {};
  const prevObj = typeof prev === 'string' ? JSON.parse(prev) : { ...prev };

  let credits = Number(prevObj.credits || 0) || 0;
  let premium = Boolean(prevObj.premium);
  let plan = prevObj.plan || null;

  for (const item of items) {
    if (item.item_type === 'credit_pack') {
      credits += Number(item.quantity) || 0;
    }
    if (item.item_type === 'plan') {
      premium = true;
      plan = {
        sku: item.sku,
        name: item.meta_json?.plano_nome || item.sku,
        periodicidade: item.meta_json?.periodicidade || null,
        id_plano: item.meta_json?.id_plano || hubPayload?.id_plano || null,
      };
    }
    if (item.item_type === 'addon' || item.item_type === 'seat') {
      const seats = Number(prevObj.seats || 0) + (Number(item.quantity) || 0);
      prevObj.seats = seats;
      prevObj.addons = Array.isArray(prevObj.addons) ? prevObj.addons : [];
      prevObj.addons.push({ sku: item.sku, quantity: item.quantity });
    }
  }

  const payload = {
    ...prevObj,
    credits,
    premium,
    plan,
    updated_from: 'contract_service',
    updated_at: new Date().toISOString(),
  };

  await client.query(
    `INSERT INTO entitlement_snapshots (app_id, subject_id, payload_json, valid_until, updated_at)
     VALUES ($1, $2, $3::jsonb, $4, CURRENT_TIMESTAMP)
     ON CONFLICT (app_id, subject_id) DO UPDATE SET
       payload_json = EXCLUDED.payload_json,
       valid_until = COALESCE(EXCLUDED.valid_until, entitlement_snapshots.valid_until),
       updated_at = CURRENT_TIMESTAMP`,
    [appId, subjectId, JSON.stringify(payload), endsAt]
  );

  return { payload };
}

module.exports = {
  createContractService,
};
