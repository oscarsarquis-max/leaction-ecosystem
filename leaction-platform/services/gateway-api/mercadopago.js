const axios = require('axios');
const https = require('https');
const tls = require('tls');

const MP_PREAPPROVAL_URL = 'https://api.mercadopago.com/preapproval';
const MP_PAYMENTS_URL = 'https://api.mercadopago.com/v1/payments';
const MP_PREFERENCES_URL = 'https://api.mercadopago.com/checkout/preferences';

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

function isSandboxAccessToken() {
  return getMercadoPagoAccessToken().startsWith('TEST-');
}

/** E-mail do comprador de teste (Contas de teste no painel MP). */
function getSandboxPayerEmail() {
  const fromEnv = (process.env.MP_SANDBOX_PAYER_EMAIL || '').trim();
  if (!fromEnv.includes('@')) return '';
  return fromEnv;
}

/** No sandbox, o MP exige e-mail de conta de teste comprador — não o e-mail real do cliente. */
function resolveSandboxPayerEmail(payerEmail) {
  const sandbox = getSandboxPayerEmail();
  if (sandbox && isSandboxAccessToken()) return sandbox;
  return String(payerEmail || '').trim();
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
  // Somente informativo / legado assessment. Checkout de plano/addon NÃO usa este valor.
  const fromEnv = Number(process.env.MP_PANELDX_PAYMENT_AMOUNT || process.env.MP_PAYMENT_AMOUNT || '0');
  return Number.isFinite(fromEnv) && fromEnv > 0 ? fromEnv : 0;
}

/**
 * Valor cobrado no checkout.
 * Planos/add-ons: estritamente valor_negociado do pedido (vitrine/DB) — sem fallback .env.
 * Assessment legado: permite MP_PANELDX_PAYMENT_AMOUNT apenas se não houver valor no pedido.
 */
function resolveOrderPaymentAmount(orderRow) {
  if (!orderRow || orderRow.external_resource_id == null) {
    const err = new Error('Pedido sem valor de cobrança (external_resource_id ausente).');
    err.statusCode = 422;
    throw err;
  }
  const raw = orderRow.external_resource_id;
  const trimmed = typeof raw === 'string' ? raw.trim() : String(raw).trim();
  const productType = String(orderRow.product_type || '').trim().toUpperCase();

  if (trimmed.startsWith('{')) {
    try {
      const parsed = JSON.parse(trimmed);
      const v = Number(parsed?.valor_negociado);
      if (Number.isFinite(v) && v > 0) {
        return Math.round(v * 100) / 100;
      }
    } catch {
      /* fall through */
    }
  }

  if (productType === 'PANELDX_ASSESSMENT') {
    const fallback = getPanelDxPaymentAmount();
    if (fallback > 0) return fallback;
  }

  const err = new Error(
    'valor_negociado inválido ou ausente no pedido. Use o preço do plano/add-on da vitrine (não o .env).'
  );
  err.statusCode = 422;
  throw err;
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
    pending_contingency:
      'O Mercado Pago está processando o pagamento (contingência). Aguarde alguns segundos ou tente de novo.',
    pending_review_manual:
      'Pagamento em análise manual no Mercado Pago. A aprovação pode chegar via webhook.',
  };
  return hints[code] || null;
}

function isCardPaymentPending(mpResponse) {
  const status = String(mpResponse?.status || '').toLowerCase();
  return status === 'in_process' || status === 'pending';
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Em sandbox, aguarda pending_contingency virar approved/rejected. */
async function settleCardPaymentIfPending(mpPayment, { attempts = 6, delayMs = 1500 } = {}) {
  let current = mpPayment;
  if (!current?.id || !isCardPaymentPending(current)) return current;

  console.log(
    `⏳ [Mercado Pago] Pagamento ${current.id} ${current.status}/${current.status_detail} — aguardando resolução...`
  );

  for (let i = 0; i < attempts; i++) {
    await sleep(delayMs);
    try {
      current = await fetchMercadoPagoPayment(current.id);
    } catch (err) {
      console.warn(`⚠️ [Mercado Pago] poll payment ${current.id}: ${err.message}`);
      continue;
    }
    if (!isCardPaymentPending(current)) {
      console.log(
        `✅ [Mercado Pago] Pagamento ${current.id} resolveu: ${current.status}/${current.status_detail}`
      );
      return current;
    }
  }
  return current;
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
    const lower = msg.toLowerCase();
    if (lower.includes('card token service not found')) {
      return (
        'Token de cartão não aceito para assinatura no sandbox MP. ' +
        'Use MP_CHECKOUT_MODE=card no .env (pagamento único) ou contas de teste vendedor/comprador do MP.'
      );
    }
    if (lower.includes('card token not found') || String(data?.cause?.[0]?.code) === '2006') {
      return (
        'Card Token not found (MP 2006): a Public Key do Brick e o Access Token do gateway ' +
        'não são do mesmo par de Credenciais de teste. No painel MP → Sua integração → ' +
        'Credenciais de teste, copie PUBLIC_KEY e ACCESS_TOKEN juntos, atualize .env + ' +
        '.env.local (NEXT_PUBLIC_MP_PUBLIC_KEY) e reinicie gateway (:4001) e Next (:4000).'
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
 * Busca pagamento na API MP (fonte da verdade do webhook).
 * @see https://www.mercadopago.com.br/developers/pt/reference/payments/_payments_id/get
 */
async function fetchMercadoPagoPayment(paymentId) {
  const accessToken = getMercadoPagoAccessToken();
  if (!accessToken) {
    const err = new Error('MP_ACCESS_TOKEN não configurado no .env do gateway');
    err.statusCode = 503;
    throw err;
  }
  const id = String(paymentId || '').trim();
  if (!id) {
    const err = new Error('payment_id obrigatório');
    err.statusCode = 400;
    throw err;
  }

  try {
    const { data } = await axios.get(
      `${MP_PAYMENTS_URL}/${encodeURIComponent(id)}`,
      buildMpAxiosConfig({
        headers: { Authorization: `Bearer ${accessToken}` },
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

/**
 * Busca merchant_order (Checkout Pro costuma notificar este tópico).
 * @see https://www.mercadopago.com.br/developers/pt/reference/merchant_orders/_merchant_orders_id/get
 */
async function fetchMercadoPagoMerchantOrder(orderId) {
  const accessToken = getMercadoPagoAccessToken();
  if (!accessToken) {
    const err = new Error('MP_ACCESS_TOKEN não configurado no .env do gateway');
    err.statusCode = 503;
    throw err;
  }
  const id = String(orderId || '').trim();
  if (!id) {
    const err = new Error('merchant_order_id obrigatório');
    err.statusCode = 400;
    throw err;
  }

  try {
    const { data } = await axios.get(
      `https://api.mercadopago.com/merchant_orders/${encodeURIComponent(id)}`,
      buildMpAxiosConfig({
        headers: { Authorization: `Bearer ${accessToken}` },
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

/**
 * Cria Preference (Checkout Pro) e devolve init_point / sandbox_init_point.
 * @see https://www.mercadopago.com.br/developers/pt/reference/preferences/_checkout_preferences/post
 */
async function createCheckoutPreference({
  title,
  amount,
  quantity = 1,
  currencyId = 'BRL',
  externalReference,
  payerEmail,
  notificationUrl,
  backUrls,
  statementDescriptor,
}) {
  const accessToken = getMercadoPagoAccessToken();
  if (!accessToken) {
    const err = new Error('MP_ACCESS_TOKEN não configurado no .env do gateway');
    err.statusCode = 503;
    throw err;
  }

  const unitPrice = Math.round(Number(amount) * 100) / 100;
  if (!Number.isFinite(unitPrice) || unitPrice <= 0) {
    const err = new Error('unit_price inválido para Preference Mercado Pago');
    err.statusCode = 400;
    throw err;
  }

  const itemTitle = String(title || 'Plano Action Hub').trim() || 'Plano Action Hub';
  const qty = Math.max(1, Number(quantity) || 1);

  const payload = {
    items: [
      {
        title: itemTitle,
        quantity: qty,
        unit_price: unitPrice,
        currency_id: String(currencyId || 'BRL').trim() || 'BRL',
      },
    ],
  };

  if (externalReference) {
    payload.external_reference = String(externalReference);
  }

  const email = String(payerEmail || '').trim();
  if (email.includes('@')) {
    payload.payer = { email: resolveSandboxPayerEmail(email) };
  }

  const notif = String(notificationUrl || '').trim();
  // MP rejeita notification_url em localhost/loopback (precisa URL pública / túnel)
  if (notif && isPubliclyReachableUrl(notif)) {
    payload.notification_url = notif;
  } else if (notif) {
    console.warn(
      `⚠️ [Mercado Pago] notification_url ignorada (não pública): ${notif}`
    );
  }

  if (backUrls && typeof backUrls === 'object') {
    const urls = {};
    for (const key of ['success', 'failure', 'pending']) {
      if (backUrls[key] && String(backUrls[key]).trim()) {
        urls[key] = String(backUrls[key]).trim();
      }
    }
    if (urls.success) {
      payload.back_urls = urls;
      // Redireciona o comprador de volta à app demandante após approved
      payload.auto_return = 'approved';
    }
  }

  if (statementDescriptor && String(statementDescriptor).trim()) {
    payload.statement_descriptor = String(statementDescriptor).trim().slice(0, 22);
  }

  console.log(
    `🛒 [Mercado Pago] Preference "${itemTitle}" R$ ${unitPrice} ref=${externalReference || '—'} back_urls=${payload.back_urls?.success || '—'}`
  );

  async function postPreference(body) {
    const { data } = await axios.post(
      MP_PREFERENCES_URL,
      body,
      buildMpAxiosConfig({
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      })
    );
    return data;
  }

  function warnIfBackUrlsStripped(pref, requested) {
    const got = String(pref?.back_urls?.success || '').trim();
    const want = String(requested?.success || '').trim();
    if (want && !got) {
      console.warn(
        '⚠️ [Mercado Pago] back_urls foram esvaziadas pela API (comum com http://localhost). ' +
          'Use HTTPS público (túnel/produção) em INOVE4US_FRONTEND_URL / APP_FRONTEND_URL_* para auto_return funcionar.'
      );
    }
  }

  try {
    const pref = await postPreference(payload);
    warnIfBackUrlsStripped(pref, payload.back_urls);
    return pref;
  } catch (err) {
    const msg = extractMpErrorMessage(err).toLowerCase();
    // Sandbox costuma rejeitar auto_return com http://localhost — retenta sem auto_return
    if (payload.auto_return && payload.back_urls?.success && msg.includes('auto_return')) {
      console.warn(
        '⚠️ [Mercado Pago] auto_return rejeitado; recriando Preference só com back_urls'
      );
      const retryPayload = { ...payload };
      delete retryPayload.auto_return;
      try {
        const pref = await postPreference(retryPayload);
        warnIfBackUrlsStripped(pref, retryPayload.back_urls);
        return pref;
      } catch (retryErr) {
        const wrapped = new Error(extractMpErrorMessage(retryErr));
        wrapped.statusCode = retryErr.response?.status || 502;
        wrapped.mpResponse = retryErr.response?.data;
        throw wrapped;
      }
    }
    const wrapped = new Error(extractMpErrorMessage(err));
    wrapped.statusCode = err.response?.status || 502;
    wrapped.mpResponse = err.response?.data;
    throw wrapped;
  }
}

/** URL alcançável pela internet (webhook MP). Localhost/loopback não serve. */
function isPubliclyReachableUrl(raw) {
  try {
    const u = new URL(String(raw).trim());
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return false;
    const host = u.hostname.toLowerCase();
    if (
      host === 'localhost' ||
      host === '127.0.0.1' ||
      host === '0.0.0.0' ||
      host === '::1' ||
      host.endsWith('.local') ||
      host.startsWith('192.168.') ||
      host.startsWith('10.')
    ) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * URL de checkout pública da Preference (sandbox vs produção).
 * Com token TEST-, NUNCA devolve www.mercadopago.com.br — isso faz o usuário
 * cair na conta real (saldo/carteira) e rejeitar cartão de teste.
 */
function resolvePreferenceCheckoutUrl(preference) {
  if (!preference || typeof preference !== 'object') return '';

  if (isSandboxAccessToken()) {
    let url = String(
      preference.sandbox_init_point || preference.init_point || ''
    ).trim();
    if (!url && preference.id) {
      url = `https://sandbox.mercadopago.com.br/checkout/v1/redirect?pref_id=${preference.id}`;
    }
    // Cinto de segurança: se a API devolver init_point de produção, reescreve
    if (url.includes('www.mercadopago.com')) {
      url = url.replace(/https?:\/\/www\.mercadopago\.[^/]+/i, 'https://sandbox.mercadopago.com.br');
    }
    if (url && !url.includes('sandbox.mercadopago')) {
      console.warn(
        '⚠️ [Mercado Pago] checkout_url sem sandbox — forçando domínio sandbox:',
        url
      );
      const prefId = preference.id || new URL(url).searchParams.get('pref_id');
      if (prefId) {
        url = `https://sandbox.mercadopago.com.br/checkout/v1/redirect?pref_id=${prefId}`;
      }
    }
    return url;
  }

  return String(preference.init_point || preference.sandbox_init_point || '').trim();
}

/**
 * Cria assinatura recorrente via POST /preapproval (Checkout Transparente).
 * @see https://www.mercadopago.com.br/developers/pt/reference/subscriptions/_preapproval/post
 */
async function createPreapprovalSubscription({
  payerEmail,
  cardTokenId,
  externalReference,
  amount,
  reason,
}) {
  const accessToken = getMercadoPagoAccessToken();
  if (!accessToken) {
    const err = new Error('MP_ACCESS_TOKEN não configurado no .env do gateway');
    err.statusCode = 503;
    throw err;
  }

  const email = resolveSandboxPayerEmail(payerEmail);
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
  const transactionAmount = Math.round(Number(amount) * 100) / 100;
  if (!Number.isFinite(transactionAmount) || transactionAmount <= 0) {
    const err = new Error(
      'transaction_amount inválido: informe o valor dinâmico do plano/add-on (não use fallback do .env).'
    );
    err.statusCode = 400;
    throw err;
  }

  const payload = {
    reason: String(reason || cfg.reason || 'Assinatura PanelDX').trim(),
    payer_email: email,
    card_token_id: token,
    auto_recurring: {
      frequency: cfg.frequency,
      frequency_type: cfg.frequency_type,
      transaction_amount: transactionAmount,
      currency_id: cfg.currency_id,
    },
    status: 'authorized',
  };

  if (externalReference) {
    payload.external_reference = String(externalReference);
  }

  console.log(`💳 [Mercado Pago] Criando preapproval para ${email} (R$ ${transactionAmount}/mês)`);

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
  payerIdentification = null,
}) {
  const accessToken = getMercadoPagoAccessToken();
  if (!accessToken) {
    const err = new Error('MP_ACCESS_TOKEN não configurado no .env do gateway');
    err.statusCode = 503;
    throw err;
  }

  const email = resolveSandboxPayerEmail(payerEmail);
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

  // CPF fixo só no sandbox TEST. Em produção: usa identificação do Brick, se houver.
  let identification = normalizePayerIdentification(payerIdentification);
  if (!identification && isSandboxAccessToken()) {
    const sandboxCpf = (process.env.MP_SANDBOX_PAYER_CPF || '12345678909').replace(/\D/g, '');
    identification = { type: 'CPF', number: sandboxCpf || '12345678909' };
  }

  const payload = {
    transaction_amount: transactionAmount,
    token,
    description: description || 'Action Hub — pagamento',
    installments: safeInstallments,
    payment_method_id: methodId,
    // NÃO usar binary_mode no sandbox TEST: o cartão APRO passa a
    // retornar cc_rejected_other_reason em vez de approved/in_process.
    payer: {
      email,
      ...(identification ? { identification } : {}),
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
    return settleCardPaymentIfPending(data);
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

function isMpCardTokenNotFoundError(err) {
  if (!err) return false;
  const msg = String(err.message || '').toLowerCase();
  const code = err.mpResponse?.cause?.[0]?.code;
  return code === 2006 || code === '2006' || msg.includes('card token not found');
}

function isServerTokenizeFallbackEnabled() {
  if (!isSandboxAccessToken()) return false;
  const flag = String(process.env.MP_SERVER_TOKENIZE_FALLBACK || '1').trim().toLowerCase();
  return flag !== '0' && flag !== 'false' && flag !== 'off';
}

/** Sandbox/dev only: após poll, trata pending_contingency como aprovado. Nunca em produção. */
function isSandboxTreatPendingAsApproved() {
  if (process.env.NODE_ENV === 'production') return false;
  if (!isSandboxAccessToken()) return false;
  const flag = String(process.env.MP_SANDBOX_TREAT_PENDING_AS_APPROVED || '1')
    .trim()
    .toLowerCase();
  return flag !== '0' && flag !== 'false' && flag !== 'off';
}

/**
 * Simulação local de pagamento (POST /simular-pagamento).
 * Bloqueada em production salvo ALLOW_PAYMENT_SIMULATION=1 explícito (emergência).
 */
function isPaymentSimulationAllowed() {
  const flag = String(process.env.ALLOW_PAYMENT_SIMULATION || '')
    .trim()
    .toLowerCase();
  if (flag === '1' || flag === 'true' || flag === 'on' || flag === 'yes') return true;
  if (flag === '0' || flag === 'false' || flag === 'off') return false;
  return process.env.NODE_ENV !== 'production';
}

function normalizePayerIdentification(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const type = String(raw.type || raw.identification_type || 'CPF')
    .trim()
    .toUpperCase();
  const number = String(raw.number || raw.identification_number || '').replace(/\D/g, '');
  if (!number || number.length < 11) return null;
  return { type: type || 'CPF', number };
}

function isSandboxRejectedOtherReason(mpPayment) {
  const status = String(mpPayment?.status || '').toLowerCase();
  const detail = String(mpPayment?.status_detail || '').toLowerCase();
  return status === 'rejected' && detail === 'cc_rejected_other_reason';
}

/** Tokenização server-side (sandbox) — compatível com Access Token TEST quando a Public Key do Brick está desatualizada. */
async function createSandboxCardTokenServerSide() {
  const accessToken = getMercadoPagoAccessToken();
  if (!accessToken) {
    const err = new Error('MP_ACCESS_TOKEN não configurado');
    err.statusCode = 503;
    throw err;
  }

  const sandboxCpf = (process.env.MP_SANDBOX_PAYER_CPF || '12345678909').replace(/\D/g, '');

  const { data } = await axios.post(
    'https://api.mercadopago.com/v1/card_tokens',
    {
      card_number: '5031433215406351',
      security_code: '123',
      expiration_month: 11,
      expiration_year: 2030,
      cardholder: {
        name: 'APRO',
        identification: {
          type: 'CPF',
          number: sandboxCpf || '12345678909',
        },
      },
    },
    buildMpAxiosConfig({
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    })
  );

  return data;
}

let brickPairCache = null;
let brickPairCacheAt = 0;

/** Valida se Public Key + Access Token formam par utilizável no Brick (sandbox). */
async function validateBrickCredentialPair() {
  const now = Date.now();
  if (brickPairCache && now - brickPairCacheAt < 60_000) {
    return brickPairCache;
  }

  const publicKey = getMercadoPagoPublicKey();
  const accessToken = getMercadoPagoAccessToken();
  if (!publicKey || !accessToken) {
    brickPairCache = { valid: false, reason: 'missing_credentials' };
    brickPairCacheAt = now;
    return brickPairCache;
  }

  if (!accessToken.startsWith('TEST-')) {
    brickPairCache = { valid: true, reason: 'production_mode' };
    brickPairCacheAt = now;
    return brickPairCache;
  }

  try {
    await axios.get('https://api.mercadopago.com/v1/payment_methods', buildMpAxiosConfig({
      headers: { Authorization: `Bearer ${accessToken}` },
      timeout: 15000,
    }));
  } catch (err) {
    const msg = extractMpErrorMessage(err).toLowerCase();
    brickPairCache = {
      valid: false,
      reason: 'invalid_access_token',
      hint:
        'Access Token inválido ou revogado. Copie Public Key e Access Token juntos em Credenciais de teste e atualize o .env.',
      error: msg,
    };
    brickPairCacheAt = now;
    return brickPairCache;
  }

  try {
    const email = getSandboxPayerEmail() || 'hubaction@testuser.com.br';
    const { data: card } = await axios.post(
      `https://api.mercadopago.com/v1/card_tokens?public_key=${encodeURIComponent(publicKey)}`,
      {
        card_number: '5031433215406351',
        security_code: '123',
        expiration_month: 11,
        expiration_year: 2030,
        cardholder: {
          name: 'APRO',
          email,
          identification: { type: 'CPF', number: '12345678909' },
        },
      },
      buildMpAxiosConfig({ timeout: 20000 })
    );

    if (!card?.id) {
      brickPairCache = { valid: false, reason: 'brick_token_failed', hint: 'Public Key não gerou card_token.' };
      brickPairCacheAt = now;
      return brickPairCache;
    }

    try {
      const { data: payProbe, status: payStatus } = await axios.post(
        MP_PAYMENTS_URL,
        {
          transaction_amount: 1,
          token: card.id,
          description: 'brick-pair-validation',
          installments: 1,
          payment_method_id: 'master',
          payer: { email },
        },
        buildMpAxiosConfig({
          headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
            'X-Idempotency-Key': `brick-pair-check-${Date.now()}`,
          },
          timeout: 20000,
          validateStatus: () => true,
        })
      );

      // Par PK+AT ok se o token foi aceito pela API de payments.
      // Sandbox frequentemente devolve in_process/pending_contingency (não "approved") —
      // isso NÃO é erro 2006; o aviso antigo assustava sem motivo.
      if (payStatus < 400 && payProbe?.id) {
        brickPairCache = {
          valid: true,
          reason: 'ok',
          live_mode: card.live_mode,
          probe_status: payProbe.status || null,
        };
        brickPairCacheAt = now;
        return brickPairCache;
      }

      const causeCode = payProbe?.cause?.[0]?.code;
      if (payStatus === 400 && (causeCode === 2006 || causeCode === '2006')) {
        brickPairCache = {
          valid: false,
          reason: 'brick_token_incompatible',
          live_mode: card.live_mode,
          hint:
            'Access Token válido, mas o token do Brick não é aceito (erro 2006). Confira se Public Key e Access Token são do mesmo app (Credenciais de teste).',
        };
        brickPairCacheAt = now;
        return brickPairCache;
      }

      throw new Error(extractMpErrorMessage({ response: { data: payProbe, status: payStatus } }));
    } catch (payErr) {
      if (isMpCardTokenNotFoundError(payErr)) {
        brickPairCache = {
          valid: false,
          reason: 'brick_token_incompatible',
          live_mode: card.live_mode,
          hint:
            'Access Token válido, mas o token do Brick não é aceito (erro 2006). Use "Pagar sandbox (MP real, sem Brick)".',
        };
        brickPairCacheAt = now;
        return brickPairCache;
      }
      throw payErr;
    }
  } catch (err) {
    brickPairCache = {
      valid: false,
      reason: 'brick_token_failed',
      error: extractMpErrorMessage(err),
      hint: 'Falha ao validar Public Key. Confira Credenciais de teste no painel MP.',
    };
    brickPairCacheAt = now;
    return brickPairCache;
  }
}

async function payWithServerSideAproToken(params) {
  const card = await createSandboxCardTokenServerSide();
  const payment = await createCardPayment({
    ...params,
    cardTokenId: card.id,
    paymentMethodId: card.payment_method_id || params.paymentMethodId || 'master',
  });
  return payment;
}

/**
 * Tenta pagamento com token do Brick; em sandbox, se MP retornar 2006
 * ou rejeitar com cc_rejected_other_reason, retenta com tokenização server-side (APRO).
 */
async function createCardPaymentWithSandboxFallback(params) {
  let payment;
  let usedServerTokenize = false;

  try {
    payment = await createCardPayment(params);
  } catch (err) {
    if (!isMpCardTokenNotFoundError(err) || !isServerTokenizeFallbackEnabled()) {
      throw err;
    }

    console.warn(
      '⚠️ [Mercado Pago] Token do Brick incompatível (2006). Usando tokenização server-side sandbox (cartão APRO).'
    );
    payment = await payWithServerSideAproToken(params);
    usedServerTokenize = true;
  }

  if (
    isServerTokenizeFallbackEnabled() &&
    !usedServerTokenize &&
    isSandboxRejectedOtherReason(payment)
  ) {
    console.warn(
      '⚠️ [Mercado Pago] Brick rejeitado (cc_rejected_other_reason). Retentando com tokenização server-side (APRO).'
    );
    try {
      payment = await payWithServerSideAproToken(params);
      usedServerTokenize = true;
    } catch (retryErr) {
      console.warn(`⚠️ [Mercado Pago] fallback server-side falhou: ${retryErr.message}`);
    }
  }

  // Sandbox costuma ficar em pending_contingency sem resolver a tempo do checkout
  if (
    isSandboxTreatPendingAsApproved() &&
    isCardPaymentPending(payment) &&
    String(payment.status_detail || '').toLowerCase() === 'pending_contingency'
  ) {
    console.warn(
      `⚠️ [Mercado Pago] Sandbox pending_contingency (payment ${payment.id}) — tratando como aprovado (TEST only).`
    );
    payment = {
      ...payment,
      status: 'approved',
      status_detail: 'accredited',
      __sandbox_forced_approved: true,
    };
  }

  return { payment, usedServerTokenize };
}

module.exports = {
  fetchMercadoPagoPayment,
  fetchMercadoPagoMerchantOrder,
  createCheckoutPreference,
  resolvePreferenceCheckoutUrl,
  createPreapprovalSubscription,
  createCardPayment,
  createCardPaymentWithSandboxFallback,
  createSandboxCardTokenServerSide,
  validateBrickCredentialPair,
  getMercadoPagoAccessToken,
  getSubscriptionConfig,
  getCheckoutMode,
  getPanelDxPaymentAmount,
  resolveOrderPaymentAmount,
  getMercadoPagoPublicKey,
  isMercadoPagoConfigured,
  isSandboxAccessToken,
  getSandboxPayerEmail,
  resolveSandboxPayerEmail,
  isPreapprovalSuccess,
  isCardPaymentSuccess,
  isCardPaymentPending,
  isMpCardTokenNotFoundError,
  isServerTokenizeFallbackEnabled,
  isSandboxTreatPendingAsApproved,
  isPaymentSimulationAllowed,
  normalizePayerIdentification,
  mapMpStatusDetailHint,
  MP_OK_STATUSES,
  MP_PAYMENT_OK_STATUSES,
};
