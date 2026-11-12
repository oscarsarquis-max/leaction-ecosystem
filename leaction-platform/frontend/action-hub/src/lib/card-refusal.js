const React = require('react');

/** Frases ao cliente. O código técnico não entra aqui. */

const EXACT = {
  cc_rejected_high_risk:
    'O pagamento com este cartão não foi aprovado pela análise de segurança do Mercado Pago. Tente outro cartão ou pague com Pix.',
  cc_rejected_insufficient_amount:
    'Este cartão não tem limite disponível para este valor. Tente outro cartão ou pague com Pix.',
  cc_rejected_call_for_authorize:
    'O banco pediu autorização para este cartão. Fale com o banco ou pague com Pix.',
  cc_rejected_card_disabled:
    'Este cartão está desativado para compras. Use outro cartão ou pague com Pix.',
  cc_rejected_duplicated_payment:
    'Este pagamento foi recusado por parecer repetido. Aguarde um instante e tente de novo, ou pague com Pix.',
  cc_rejected_bad_filled_card_number:
    'O número do cartão não confere. Confira os dígitos ou pague com Pix.',
  cc_rejected_bad_filled_date:
    'A validade do cartão não confere. Confira a data ou pague com Pix.',
  cc_rejected_bad_filled_security_code:
    'O código de segurança não confere. Confira o CVV ou pague com Pix.',
  cc_rejected_bad_filled_other:
    'Algum dado do cartão não confere. Revise o formulário ou pague com Pix.',
};

const GENERIC =
  'O pagamento com este cartão não foi aprovado. Tente outro cartão ou pague com Pix.';

function customerCardMessage(statusDetail) {
  const code = String(statusDetail || '').toLowerCase();
  if (EXACT[code]) return EXACT[code];
  if (code.startsWith('cc_rejected_bad_filled_')) return EXACT.cc_rejected_bad_filled_other;
  return GENERIC;
}

function messageLeaksTechnical(text) {
  const value = String(text || '');
  return /cc_rejected|status_detail|\bteste\b|\bAPRO\b|5031\s*4332/i.test(value);
}

function checkoutSafetyLine(sandbox) {
  if (sandbox) {
    return 'Ambiente de teste: use o cartão indicado pelo suporte para simular o pagamento.';
  }
  return 'Pagamento seguro pelo Mercado Pago. Use o cartão do titular da compra.';
}

function CardRefusalNotice({ message, pixHref }) {
  return React.createElement(
    'div',
    { className: 'mb-4' },
    React.createElement('p', { className: 'text-sm text-red-600', role: 'alert' }, message),
    pixHref
      ? React.createElement(
          'a',
          {
            href: pixHref,
            className:
              'mt-3 inline-flex rounded-xl bg-slate-900 px-4 py-3 text-sm font-bold text-white',
          },
          'Pagar com Pix',
        )
      : null,
  );
}

module.exports = {
  EXACT,
  GENERIC,
  customerCardMessage,
  messageLeaksTechnical,
  checkoutSafetyLine,
  CardRefusalNotice,
};
