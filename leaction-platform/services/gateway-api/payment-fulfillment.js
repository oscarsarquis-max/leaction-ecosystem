const axios = require('axios');
const jwt = require('jsonwebtoken');
const { createContractService } = require('./domain/contract-service');
const { kickOutboxNow } = require('./domain/outbox-worker');

/**
 * Marca pedido como PAID, ativa contrato (ContractService + outbox) e
 * dispara webhook JWT ao originador (PanelDX) — legado, até o worker de outbox.
 */
async function fulfillOrderPayment(pool, orderId, jwtSecret, options = {}) {
  const gatewayReference = options.gatewayReference || null;
  const contractService = createContractService(pool);

  const orderResult = await pool.query(
    `SELECT 
       o.id,
       o.status,
       o.payment_url,
       o.gateway_ref,
       o.external_resource_id AS id_matu,
       p.type AS product_type,
       COALESCE(o.external_resource_id, p.external_resource_id) AS external_resource_id,
       u.email AS customer_email,
       u.full_name
     FROM orders o
     JOIN products p ON p.id = o.product_id
     LEFT JOIN users u ON u.id = o.user_id
     WHERE o.id = $1`,
    [orderId]
  );

  if (orderResult.rows.length === 0) {
    const err = new Error('Pedido não encontrado');
    err.statusCode = 404;
    throw err;
  }

  const order = orderResult.rows[0];
  let idMatuForJwt = order.id_matu != null ? String(order.id_matu).trim() : '';

  let hubPayloadParsed = null;
  try {
    const parsed = JSON.parse(String(order.external_resource_id || ''));
    if (typeof parsed === 'object' && parsed) {
      hubPayloadParsed = parsed;
      if (order.product_type === 'PANELDX_SUBSCRIPTION' && parsed.id_matu != null) {
        const matuFromPayload = String(parsed.id_matu).trim();
        if (/^\d+$/.test(matuFromPayload)) {
          idMatuForJwt = matuFromPayload;
        }
      }
    }
  } catch {
    hubPayloadParsed = null;
  }

  // Idempotência: já PAID — ainda garante activateFromOrder (noop se contrato existe)
  if (String(order.status || '').toUpperCase() === 'PAID') {
    let contractActivation = null;
    try {
      contractActivation = await contractService.activateFromOrder(orderId);
      kickOutboxNow(pool);
    } catch (contractErr) {
      console.error(
        `❌ [ContractService] Falha (order já PAID) order=${orderId}:`,
        contractErr.message
      );
    }
    return {
      order: {
        id: order.id,
        status: order.status,
        paid_at: null,
        gateway_reference: gatewayReference,
        updated_at: null,
      },
      alreadyPaid: true,
      webhookDelivered: false,
      customer_email: order.customer_email,
      id_matu: idMatuForJwt,
      product_type: order.product_type,
      contract: contractActivation,
    };
  }

  const updateResult = await pool.query(
    `UPDATE orders
     SET status = 'PAID',
         payment_status = 'paid',
         paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP),
         updated_at = CURRENT_TIMESTAMP,
         gateway_reference = COALESCE($2, gateway_reference)
     WHERE id = $1
     RETURNING id, status, paid_at, gateway_reference, updated_at`,
    [orderId, gatewayReference]
  );
  const updatedOrder = updateResult.rows[0];

  // Fase 1B — ledger de contratos + outbox (transação própria, tudo-ou-nada)
  let contractActivation = null;
  try {
    contractActivation = await contractService.activateFromOrder(orderId);
    console.log(
      `📋 [ContractService] Ativação order=${orderId} contract=${contractActivation.contract_id} event=${contractActivation.event_type || 'idempotent'}`
    );
    kickOutboxNow(pool);
  } catch (contractErr) {
    // Pagamento já está PAID; não reverte cobrança — falha fica rastreável nos logs
    console.error(
      `❌ [ContractService] Falha ao ativar contrato order=${orderId}:`,
      contractErr.message
    );
  }

  const webhook_url = order.payment_url && String(order.payment_url).trim();
  let webhookDelivered = false;

  if (webhook_url) {
    try {
      const tokenPayload = {
        iss: 'leaction-hub',
        status_tecnico: 'PAYMENT_CONFIRMED',
        order_id: updatedOrder.id,
        customer_email: order.customer_email,
        gateway_ref: order.gateway_ref,
        id_matu: idMatuForJwt,
        product_type: order.product_type,
        hub_payload: hubPayloadParsed,
        payment_provider: options.paymentProvider || 'mercadopago',
        mp_preapproval_id: options.mpPreapprovalId || null,
        contract_id: contractActivation?.contract_id || null,
      };
      const tecnicoToken = jwt.sign(tokenPayload, jwtSecret, { expiresIn: '1h' });

      console.log('🚀 [HUB PLATFORMA] Enviando Webhook de confirmação via JWT para o originador...');
      console.log(`   Destino: ${webhook_url} | id_matu: ${idMatuForJwt}`);

      await axios.post(webhook_url, { token: tecnicoToken }, { timeout: 15000 });
      webhookDelivered = true;
    } catch (webhookErr) {
      console.error(
        `❌ [HUB PLATFORMA] Falha ao disparar webhook para ${webhook_url}:`,
        webhookErr.message
      );
    }
  }

  if (order.product_type === 'MOODLE_COURSE') {
    console.log(
      `🚀 [AUTOMAÇÃO] Iniciando matrícula de ${order.full_name || 'LeActioner'} no curso ${order.external_resource_id}`
    );
  } else if (order.product_type === 'PANELDX_ASSESSMENT') {
    console.log(
      `🚀 [AUTOMAÇÃO] Iniciando liberação do assessment PanelDX ${order.external_resource_id} para ${order.full_name || 'LeActioner'}`
    );
  } else if (order.product_type === 'PANELDX_SUBSCRIPTION') {
    console.log(
      `🚀 [AUTOMAÇÃO] Assinatura PanelDX confirmada — recurso ${order.external_resource_id} para ${order.full_name || 'LeActioner'}`
    );
  } else if (order.product_type === 'PANELDX_ADDON') {
    console.log(
      `🚀 [AUTOMAÇÃO] Add-on PanelDX confirmado — recurso ${order.external_resource_id} para ${order.full_name || 'LeActioner'}`
    );
  }

  return {
    order: updatedOrder,
    webhookDelivered,
    customer_email: order.customer_email,
    id_matu: idMatuForJwt,
    product_type: order.product_type,
    contract: contractActivation,
  };
}

function parsePanelDxIdMatu(value) {
  const raw = value === undefined || value === null ? '' : String(value).trim();
  if (!/^\d+$/.test(raw) || Number(raw) <= 0) {
    return null;
  }
  return raw;
}

module.exports = {
  fulfillOrderPayment,
  parsePanelDxIdMatu,
};
