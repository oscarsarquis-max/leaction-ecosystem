const axios = require('axios');
const https = require('https');
const tls = require('tls');

const MP_PREAPPROVAL_URL = 'https://api.mercadopago.com/preapproval';
const MP_PAYMENTS_URL = 'https://api.mercadopago.com/v1/payments';

const MP_OK_STATUSES = new Set(['authorized', 'pending']);
const MP_PAYMENT_OK_STATUSES = new Set(['approved', 'authorized']);

let mpHttpsAgent;

/** Node no Windows pode falhar TLS com a CA embutida; usa o trust store do SO (Node 22+). */
function getMpHttpsAgent() {
  if (mpHttpsAgent !== undefined) {
    return mpHttpsAgent;
  }

  try {
    if (typeof tls.getCACertificates === 'function') {
      const systemCa = tls.getCACertificates('system');
      if (Array.isArray(systemCa) && systemCa.length > 0) {
        mpHttpsAgent = new https.Agent({ ca: systemCa, keepAlive: true });
        return mpHttpsAgent;
      }
    }
  } catch (err) {
    console.warn('⚠️ [Mercado Pago] Não foi possível carregar CAs do sistema:', err.message);
  }

  mpHttpsAgent = null;
  return mpHttpsAgent;
}

function buildMpAxiosConfig(extra = {}) {
  const config = { timeout: 30000, ...extra };
  const agent = getMpHttpsAgent();
  if (agent) {
    config.httpsAgent = agent;
  }
  return config;
}

function getMercadoPagoAccessToken() {
  const token = (process.env.MP_ACCESS_TOKEN || process.env.MERCADOPAGO_ACCESS_TOKEN || '').trim();
  if (!token || token.includes('SEU_ACCESS_TOKEN') || token.includes('SEU_PUBLIC_KEY')) {
    return '';
  }
  return token;
}

function getMercadoPagoPublicKey() {
  const key = (process.env.MP_PUBLIC_KEY || process.env.NEXT_PUBLIC_MP_PUBLIC_KEY || '').trim();
  if (!key || key.includes('SEU_PUBLIC_KEY')) {
    return '';
  }
  return key;
}

function isMercadoPagoConfigured() {
  return getMercadoPagoAccessToken().length > 0;
}

function getSubscriptionConfig() {
  return {
    reason: process.env.MP_SUBSCRIPTION_REASON || 'Assinatura Mensal - Leaction Hub',
    amount: Number(process.env.MP_SUBSCRIPTION_AMOUNT || '99'),
    currency_id: process.env.MP_SUBSCRIPTION_CURRENCY || 'BRL',
    frequency: Number(process.env.MP_SUBSCRIPTION_FREQUENCY || '1'),
    frequency_type: process.env.MP_SUBSCRIPTION_FREQUENCY_TYPE || 'months',
  };
}

/** card = pagamento único (/v1/payments, compatível com Brick sandbox). subscription = preapproval. */
function getCheckoutMode() {
  const mode = String(process.env.MP_CHECKOUT_MODE || 'card').trim().toLowerCase();
  return mode === 'subscription' ? 'subscription' : 'card';
}

function getPanelDxPaymentAmount() {
  const fromEnv = Number(process.env.MP_PANELDX_PAYMENT_AMOUNT || process.env.MP_PAYMENT_AMOUNT || '1');
  return Number.isFinite(fromEnv) && fromEnv > 0 ? fromEnv : 1;
}

/** Valor do pedido: prioriza valor_negociado (assinatura) e cai no sandbox em assessment. */
function resolveOrderPaymentAmount(orderRow) {
  const fallback = getPanelDxPaymentAmount();
  if (!orderRow || orderRow.external_resource_id == null) return fallback;
  const raw = orderRow.external_resource_id;
  if (typeof raw === 'string') {
    const trimmed = raw.trim();
    if (!trimmed.startsWith('{')) return fallback;
    try {
      const parsed = JSON.parse(trimmed);
      const v = Number(parsed?.valor_negociado);
      if (Number.isFinite(v) && v > 0) {
        return Math.round(v * 100) / 100;
      }
    } catch {
      return fallback;
    }
  }
  return fallback;
}

/** Dica amigável para rejeições comuns no sandbox Mercado Pago. */
function mapMpStatusDetailHint(statusDetail) {
  const code = String(statusDetail || '').toLowerCase();
  const hints = {
    cc_rejected_other_reason:
      'No sandbox, use cartão 5031 4332 1540 6351, CVV 123, validade futura e titular APRO.',
    cc_rejected_bad_filled_card_number: 'Número do cartão inválido. Confira os dígitos.',
    cc_rejected_bad_filled_date: 'Data de validade inválida.',
    cc_rejected_bad_filled_security_code: 'CVV inválido.',
    cc_rejected_call_for_authorize: 'Cartão exige autorização do banco (use titular APRO no sandbox).',
    cc_rejected_insufficient_amount: 'Saldo insuficiente no cartão de teste.',
    cc_rejected_high_risk: 'Pagamento bloqueado por risco. Use o cartão de teste oficial do Mercado Pago.',
  };
  return hints[code] || null;
}

function extractMpErrorMessage(err) {
  const raw = err?.message || '';
  if (
    err?.code === 'UNABLE_TO_VERIFY_LEAF_SIGNATURE' ||
    raw.toLowerCase().includes('unable to verify the first certificate')
  ) {
    return (
      'Falha TLS ao contactar Mercado Pago. Reinicie o gateway com ' +
      'NODE_OPTIONS=--use-system-ca ou atualize o Node para 22+.'
    );
  }

  const data = err?.response?.data;
  if (!data) return raw || 'Erro ao comunicar com Mercado Pago';

  if (typeof data.message === 'string' && data.message.trim()) {
    const msg = data.message.trim();
    if (msg.toLowerCase().includes('card token service not found')) {
      return (
        'Token de cartão não aceito para assinatura no sandbox MP. ' +
        'Use MP_CHECKOUT_MODE=card no .env (pagamento único) ou contas de teste vendedor/comprador do MP.'
      );
    }
    return msg;
  }

  if (Array.isArray(data.cause) && data.cause.length > 0) {
    const first = data.cause[0];
    if (typeof first === 'string') return first;
    if (first?.description) return String(first.description);
    if (first?.code) return String(first.code);
  }

  return 'Erro ao processar assinatura no Mercado Pago';
}

/**
 * Cria assinatura recorrente via POST /preapproval (Checkout Transparente).
 * @see https://www.mercadopago.com.br/developers/pt/reference/subscriptions/_preapproval/post
 */
async function createPreapprovalSubscription({ payerEmail, cardTokenId, externalReference }) {
  const accessToken = getMercadoPagoAccessToken();
  if (!accessToken) {
    const err = new Error('MP_ACCESS_TOKEN não configurado no .env do gateway');
    err.statusCode = 503;
    throw err;
  }

  const email = String(payerEmail || '').trim();
  const token = String(cardTokenId || '').trim();

  if (!email.includes('@')) {
    const err = new Error('payer_email inválido');
    err.statusCode = 400;
    throw err;
  }

  if (!token) {
    const err = new Error('card_token_id obrigatório');
    err.statusCode = 400;
    throw err;
  }

  const cfg = getSubscriptionConfig();

  const payload = {
    reason: cfg.reason,
    payer_email: email,
    card_token_id: token,
    auto_recurring: {
      frequency: cfg.frequency,
      frequency_type: cfg.frequency_type,
      transaction_amount: cfg.amount,
      currency_id: cfg.currency_id,
    },
    status: 'authorized',
  };

  if (externalReference) {
    payload.external_reference = String(externalReference);
  }

  console.log(`💳 [Mercado Pago] Criando preapproval para ${email} (R$ ${cfg.amount}/mês)`);

  try {
    const { data } = await axios.post(
      MP_PREAPPROVAL_URL,
      payload,
      buildMpAxiosConfig({
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      })
    );

    return data;
  } catch (err) {
    const wrapped = new Error(extractMpErrorMessage(err));
    wrapped.statusCode = err.response?.status || 502;
    wrapped.mpResponse = err.response?.data;
    throw wrapped;
  }
}

function isPreapprovalSuccess(mpResponse) {
  const status = String(mpResponse?.status || '').toLowerCase();
  return MP_OK_STATUSES.has(status);
}

/**
 * Pagamento único com token do Card Payment Brick (sandbox TEST).
 * @see https://www.mercadopago.com.br/developers/pt/reference/payments/_payments/post
 */
async function createCardPayment({
  payerEmail,
  cardTokenId,
  paymentMethodId,
  amount,
  externalReference,
  description,
  installments = 1,
}) {
  const accessToken = getMercadoPagoAccessToken();
  if (!accessToken) {
    const err = new Error('MP_ACCESS_TOKEN não configurado no .env do gateway');
    err.statusCode = 503;
    throw err;
  }

  const email = String(payerEmail || '').trim();
  const token = String(cardTokenId || '').trim();
  const methodId = String(paymentMethodId || '').trim();

  if (!email.includes('@')) {
    const err = new Error('payer_email inválido');
    err.statusCode = 400;
    throw err;
  }
  if (!token) {
    const err = new Error('card_token_id obrigatório');
    err.statusCode = 400;
    throw err;
  }
  if (!methodId) {
    const err = new Error('payment_method_id obrigatório');
    err.statusCode = 400;
    throw err;
  }

  const transactionAmount = Math.round(Number(amount) * 100) / 100;
  if (!Number.isFinite(transactionAmount) || transactionAmount <= 0) {
    const err = new Error('transaction_amount inválido');
    err.statusCode = 400;
    throw err;
  }

  const safeInstallments =
    transactionAmount < 10 ? 1 : Math.max(1, Math.min(12, Number(installments) || 1));

  const sandboxCpf = (process.env.MP_SANDBOX_PAYER_CPF || '12345678909').replace(/\D/g, '');

  const payload = {
    transaction_amount: transactionAmount,
    token,
    description: description || 'PanelDX — Diagnóstico de Maturidade',
    installments: safeInstallments,
    payment_method_id: methodId,
    payer: {
      email,
      identification: {
        type: 'CPF',
        number: sandboxCpf || '12345678909',
      },
    },
  };

  if (externalReference) {
    payload.external_reference = String(externalReference);
  }

  const idempotencyKey = `hub-card-${externalReference || 'na'}-${Date.now()}`;

  console.log(
    `💳 [Mercado Pago] Pagamento único R$ ${transactionAmount} para ${email} (pedido ${externalReference || '—'})`
  );

  try {
    const { data } = await axios.post(
      MP_PAYMENTS_URL,
      payload,
      buildMpAxiosConfig({
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
          'X-Idempotency-Key': idempotencyKey,
        },
      })
    );
    return data;
  } catch (err) {
    const wrapped = new Error(extractMpErrorMessage(err));
    wrapped.statusCode = err.response?.status || 502;
    wrapped.mpResponse = err.response?.data;
    throw wrapped;
  }
}

function isCardPaymentSuccess(mpResponse) {
  const status = String(mpResponse?.status || '').toLowerCase();
  return MP_PAYMENT_OK_STATUSES.has(status);
}

module.exports = {
  createPreapprovalSubscription,
  createCardPayment,
  getMercadoPagoAccessToken,
  getSubscriptionConfig,
  getCheckoutMode,
  getPanelDxPaymentAmount,
  resolveOrderPaymentAmount,
  getMercadoPagoPublicKey,
  isMercadoPagoConfigured,
  isPreapprovalSuccess,
  isCardPaymentSuccess,
  mapMpStatusDetailHint,
  MP_OK_STATUSES,
  MP_PAYMENT_OK_STATUSES,
};
