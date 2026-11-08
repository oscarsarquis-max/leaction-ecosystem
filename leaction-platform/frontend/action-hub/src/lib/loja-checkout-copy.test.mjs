import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const src = fs.readFileSync(new URL('./loja-checkout-copy.ts', import.meta.url), 'utf8');

test('copy da Loja: títulos da Biblioteca e sem ActionHub', () => {
  assert.match(src, /Sua assinatura da Biblioteca/);
  assert.match(src, /Suas consultas de IA/);
  assert.match(src, /Preencha o cartão para autorizar a cobrança mensal/);
  assert.match(src, /Assinatura autorizada\. Aguardando confirmação do primeiro pagamento/);
  assert.match(src, /gerenciamento da sua assinatura/);
  assert.doesNotMatch(src, /ActionHub/);
  assert.doesNotMatch(src, /Renovação automática mensal autorizada neste cartão/);
  assert.doesNotMatch(src, /Cancele no ActionHub/);
});
