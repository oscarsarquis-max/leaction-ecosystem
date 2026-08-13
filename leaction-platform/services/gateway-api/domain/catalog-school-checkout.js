'use strict';

/**
 * Regras aditivas do checkout de catálogo para inove4us-school.
 * Não se aplica a outros app_id (inove4us B2C permanece no fluxo original).
 */

const { validatePayerDocument } = require('./br-documents');

const SCHOOL_APP_ID = 'inove4us-school';
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isSchoolCatalogApp(appId) {
  return String(appId || '').trim().toLowerCase() === SCHOOL_APP_ID;
}

/**
 * @returns {{ ok: true, fields: object } | { ok: false, status: number, error: string }}
 */
function parseSchoolCatalogCheckout(body) {
  const payload = body && typeof body === 'object' ? body : {};
  const subjectId = String(payload.subject_id || '').trim();
  const subjectType = String(payload.subject_type || '').trim().toLowerCase();
  const payerEmail = String(payload.payer_email || payload.email || '')
    .trim()
    .toLowerCase();
  const razaoSocial = String(payload.razao_social || '').trim();

  if (!UUID_RE.test(subjectId)) {
    return {
      ok: false,
      status: 400,
      error: 'subject_id deve ser um UUID de instituição.',
    };
  }
  if (subjectType !== 'instituicao') {
    return {
      ok: false,
      status: 400,
      error: 'subject_type deve ser instituicao.',
    };
  }
  if (!payerEmail || !payerEmail.includes('@') || payerEmail.length > 255) {
    return {
      ok: false,
      status: 400,
      error: 'payer_email obrigatório e válido.',
    };
  }
  if (razaoSocial.length < 2 || razaoSocial.length > 255) {
    return {
      ok: false,
      status: 400,
      error: 'Informe o nome da escola (razao_social).',
    };
  }

  const doc = validatePayerDocument(
    payload.payer_document_type,
    payload.payer_document
  );
  if (!doc.ok) {
    return { ok: false, status: 400, error: doc.error };
  }

  return {
    ok: true,
    fields: {
      subject_id: subjectId.toLowerCase(),
      subject_type: 'instituicao',
      instituicao_id: subjectId.toLowerCase(),
      payer_email: payerEmail,
      razao_social: razaoSocial,
      payer_document: doc.digits,
      payer_document_type: doc.type,
    },
  };
}

function licensesFromPlanMeta(meta) {
  const direitos =
    (meta && typeof meta.direitos === 'object' && meta.direitos) ||
    (meta && typeof meta.entitlements === 'object' && meta.entitlements) ||
    {};
  const raw =
    meta?.licenses_granted ??
    meta?.seats ??
    direitos.licenses_granted ??
    direitos.seats;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

module.exports = {
  SCHOOL_APP_ID,
  isSchoolCatalogApp,
  parseSchoolCatalogCheckout,
  licensesFromPlanMeta,
};
