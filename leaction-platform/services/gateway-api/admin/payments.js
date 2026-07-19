'use strict';

/**
 * Ops de pagamentos (admin):
 *   GET  /admin/payments              — pedidos recentes (filtro status/app)
 *   GET  /admin/payments/stats        — evolução por plano
 *   POST /admin/payments/:orderId/notice — mensagem para a app satélite
 */

const { kickOutboxNow } = require('../domain/outbox-worker');

async function ensureNoticesTable(pool) {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS admin_order_notices (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
      app_id TEXT,
      subject_id TEXT NOT NULL,
      message TEXT NOT NULL,
      status_label TEXT,
      created_by TEXT,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
  `);
  await pool.query(`
    CREATE INDEX IF NOT EXISTS idx_admin_order_notices_order
      ON admin_order_notices (order_id)
  `);
}

function parseHubPayload(raw) {
  if (raw == null) return {};
  if (typeof raw === 'object' && !Array.isArray(raw)) return raw;
  const text = String(raw || '').trim();
  if (!text.startsWith('{')) return {};
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function serializePaymentRow(row) {
  const hub = parseHubPayload(row.external_resource_id);
  const amount = Number(hub.valor_negociado);
  return {
    id: row.id,
    status: row.status,
    payment_status: row.payment_status,
    created_at: row.created_at,
    paid_at: row.paid_at,
    updated_at: row.updated_at,
    gateway_reference: row.gateway_reference,
    payer_email: row.payer_email,
    product_name: row.product_name,
    product_sku: row.product_sku,
    product_type: row.product_type,
    app_id: row.app_id || hub.app_id || null,
    subject_id: row.subject_id || hub.subject_id || row.payer_email || null,
    plan_name: hub.plano_nome || row.product_name || null,
    plan_sku: hub.sku || row.product_sku || null,
    amount: Number.isFinite(amount) && amount > 0 ? amount : null,
    currency: hub.currency || 'BRL',
    contract_id: row.contract_id || null,
    contract_status: row.contract_status || null,
    latest_notice: row.latest_notice || null,
  };
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ requireAdmin: import('express').RequestHandler }} deps
 */
function registerAdminPaymentsRoutes(app, pool, { requireAdmin }) {
  app.get('/admin/payments', requireAdmin, async (req, res) => {
    try {
      await ensureNoticesTable(pool);

      const status = String(req.query.status || '').trim().toUpperCase();
      const appId = String(req.query.app_id || '').trim().toLowerCase();
      const limit = Math.min(200, Math.max(1, Number(req.query.limit) || 80));

      const params = [];
      const where = [];
      if (status) {
        params.push(status);
        where.push(`UPPER(o.status) = $${params.length}`);
      }
      if (appId) {
        params.push(appId);
        where.push(
          `(c.app_id = $${params.length} OR LOWER(COALESCE(
            CASE WHEN o.external_resource_id LIKE '{%'
              THEN o.external_resource_id::jsonb->>'app_id'
              ELSE NULL
            END, ''
          )) = $${params.length})`
        );
      }
      params.push(limit);

      const sql = `
        SELECT
          o.id,
          o.status,
          o.payment_status,
          o.created_at,
          o.paid_at,
          o.updated_at,
          o.gateway_reference,
          o.external_resource_id,
          u.email AS payer_email,
          p.name AS product_name,
          p.sku AS product_sku,
          p.type AS product_type,
          c.id AS contract_id,
          c.app_id,
          c.subject_id,
          c.status AS contract_status,
          (
            SELECT n.message
            FROM admin_order_notices n
            WHERE n.order_id = o.id
            ORDER BY n.created_at DESC
            LIMIT 1
          ) AS latest_notice
        FROM orders o
        LEFT JOIN users u ON u.id = o.user_id
        LEFT JOIN products p ON p.id = o.product_id
        LEFT JOIN contracts c ON c.order_id = o.id
        ${where.length ? `WHERE ${where.join(' AND ')}` : ''}
        ORDER BY o.created_at DESC
        LIMIT $${params.length}
      `;

      const result = await pool.query(sql, params);
      const payments = result.rows.map(serializePaymentRow);

      const counts = await pool.query(`
        SELECT
          COUNT(*)::int AS total,
          COUNT(*) FILTER (WHERE UPPER(status) = 'PENDING')::int AS pending,
          COUNT(*) FILTER (WHERE UPPER(status) = 'PAID')::int AS paid,
          COUNT(*) FILTER (WHERE UPPER(status) NOT IN ('PENDING', 'PAID'))::int AS other
        FROM orders
      `);

      return res.status(200).json({
        payments,
        counts: counts.rows[0] || { total: 0, pending: 0, paid: 0, other: 0 },
      });
    } catch (err) {
      console.error('❌ [admin/payments GET]', err.message);
      return res.status(500).json({ error: 'Erro ao listar pagamentos' });
    }
  });

  app.get('/admin/payments/stats', requireAdmin, async (req, res) => {
    try {
      const days = Math.min(90, Math.max(7, Number(req.query.days) || 30));
      const appId = String(req.query.app_id || '').trim().toLowerCase();
      const params = [days];
      let appFilter = '';
      if (appId) {
        params.push(appId);
        appFilter = `AND (
          c.app_id = $2
          OR LOWER(COALESCE(
            CASE WHEN o.external_resource_id LIKE '{%' THEN o.external_resource_id::jsonb->>'app_id' ELSE NULL END,
            ''
          )) = $2
        )`;
      }

      const result = await pool.query(
        `
        SELECT
          DATE(o.created_at) AS day,
          COALESCE(
            CASE
              WHEN o.external_resource_id LIKE '{%'
              THEN NULLIF(TRIM(o.external_resource_id::jsonb->>'plano_nome'), '')
              ELSE NULL
            END,
            p.name,
            'Sem plano'
          ) AS plan_name,
          COALESCE(
            c.app_id,
            CASE
              WHEN o.external_resource_id LIKE '{%'
              THEN NULLIF(TRIM(o.external_resource_id::jsonb->>'app_id'), '')
              ELSE NULL
            END,
            'hub'
          ) AS app_id,
          COUNT(*)::int AS orders_total,
          COUNT(*) FILTER (WHERE UPPER(o.status) = 'PAID')::int AS orders_paid,
          COUNT(*) FILTER (WHERE UPPER(o.status) = 'PENDING')::int AS orders_pending,
          COALESCE(
            SUM(
              CASE
                WHEN UPPER(o.status) = 'PAID'
                 AND o.external_resource_id LIKE '{%'
                 AND (o.external_resource_id::jsonb->>'valor_negociado') ~ '^[0-9]+(\\.[0-9]+)?$'
                THEN (o.external_resource_id::jsonb->>'valor_negociado')::numeric
                ELSE 0
              END
            ),
            0
          ) AS revenue
        FROM orders o
        LEFT JOIN products p ON p.id = o.product_id
        LEFT JOIN contracts c ON c.order_id = o.id
        WHERE o.created_at >= CURRENT_DATE - ($1::int * INTERVAL '1 day')
          ${appFilter}
        GROUP BY 1, 2, 3
        ORDER BY 1 ASC, 2 ASC
        `,
        params
      );

      return res.status(200).json({
        days,
        series: result.rows.map((r) => ({
          day: r.day,
          plan_name: r.plan_name,
          app_id: r.app_id,
          orders_total: Number(r.orders_total) || 0,
          orders_paid: Number(r.orders_paid) || 0,
          orders_pending: Number(r.orders_pending) || 0,
          revenue: Number(r.revenue) || 0,
        })),
      });
    } catch (err) {
      console.error('❌ [admin/payments/stats]', err.message);
      return res.status(500).json({ error: 'Erro ao carregar estatísticas' });
    }
  });

  app.post('/admin/payments/:orderId/notice', requireAdmin, async (req, res) => {
    try {
      await ensureNoticesTable(pool);

      const orderId = String(req.params.orderId || '').trim();
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const message = String(body.message || '').trim();
      const statusLabel = String(body.status_label || body.status || '').trim() || null;

      if (!orderId) {
        return res.status(400).json({ error: 'orderId obrigatório' });
      }
      if (!message || message.length < 3) {
        return res.status(400).json({ error: 'message obrigatória (mín. 3 caracteres)' });
      }

      const orderRes = await pool.query(
        `
        SELECT
          o.id,
          o.status,
          o.external_resource_id,
          u.email AS payer_email,
          c.app_id,
          c.subject_id
        FROM orders o
        LEFT JOIN users u ON u.id = o.user_id
        LEFT JOIN contracts c ON c.order_id = o.id
        WHERE o.id = $1
        LIMIT 1
        `,
        [orderId]
      );

      if (!orderRes.rows[0]) {
        return res.status(404).json({ error: 'Pedido não encontrado' });
      }

      const order = orderRes.rows[0];
      const hub = parseHubPayload(order.external_resource_id);
      const appId = String(order.app_id || hub.app_id || 'inove4us').trim().toLowerCase();
      const subjectId = String(
        order.subject_id || hub.subject_id || order.payer_email || ''
      )
        .trim()
        .toLowerCase()
        .replace(/^email:/, '');

      if (!subjectId) {
        return res.status(400).json({ error: 'Pedido sem subject_id/e-mail para notificar' });
      }

      const createdBy = req.admin?.email || 'admin';
      const noticeIns = await pool.query(
        `
        INSERT INTO admin_order_notices (order_id, app_id, subject_id, message, status_label, created_by)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, created_at
        `,
        [orderId, appId, subjectId, message, statusLabel, createdBy]
      );

      const outboxPayload = {
        subject_id: subjectId,
        order_id: orderId,
        message,
        status_label: statusLabel,
        order_status: order.status,
        source: 'admin_notice',
        notice_id: noticeIns.rows[0].id,
      };

      const idempotencyKey = `admin_notice_${noticeIns.rows[0].id}`;
      await pool.query(
        `
        INSERT INTO webhook_outbox (
          app_id, event_type, payload_json, idempotency_key,
          status, attempts, next_retry_at, created_at
        ) VALUES (
          $1, 'PAYMENT_NOTICE', $2::jsonb, $3,
          'pending', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        `,
        [appId, JSON.stringify(outboxPayload), idempotencyKey]
      );

      kickOutboxNow(pool);

      return res.status(200).json({
        success: true,
        notice: {
          id: noticeIns.rows[0].id,
          order_id: orderId,
          app_id: appId,
          subject_id: subjectId,
          message,
          status_label: statusLabel,
          created_at: noticeIns.rows[0].created_at,
          created_by: createdBy,
        },
      });
    } catch (err) {
      console.error('❌ [admin/payments notice]', err.message);
      return res.status(500).json({ error: 'Erro ao enviar aviso' });
    }
  });
}

module.exports = {
  registerAdminPaymentsRoutes,
};
