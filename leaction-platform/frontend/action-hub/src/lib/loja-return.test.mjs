import assert from 'node:assert/strict';
import test from 'node:test';

const ALLOWED = new Set([
  'https://lojadepaes.com.br',
  'http://127.0.0.1:5175',
  'http://localhost:5175',
]);

function parseReturnOrigin(raw) {
  const value = String(raw || '').trim();
  if (!value) return '';
  try {
    const parsed = new URL(value.includes('://') ? value : `https://${value}`);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return '';
    return parsed.origin;
  } catch {
    return '';
  }
}

function parseReturnTo(raw) {
  const value = String(raw || '').trim();
  if (!value || !value.startsWith('/') || value.startsWith('//')) return '/';
  return value;
}

function safeLojaReturnOrigin(raw) {
  const origin = parseReturnOrigin(raw);
  if (origin && ALLOWED.has(origin)) return origin;
  return 'https://lojadepaes.com.br';
}

function safeLojaReturnTo(raw) {
  const path = parseReturnTo(raw);
  if (path === '/') return '/#biblioteca';
  return path;
}

test('aceita origem da Loja e rejeita terceiro', () => {
  assert.equal(safeLojaReturnOrigin('https://lojadepaes.com.br'), 'https://lojadepaes.com.br');
  assert.equal(
    safeLojaReturnOrigin('https://lojadepaes.com.br/loja'),
    'https://lojadepaes.com.br'
  );
  assert.equal(safeLojaReturnOrigin('https://evil.example'), 'https://lojadepaes.com.br');
  assert.equal(safeLojaReturnOrigin('javascript:alert(1)'), 'https://lojadepaes.com.br');
});

test('preserva retorno à biblioteca e recusa caminho aberto', () => {
  assert.equal(safeLojaReturnTo('/#biblioteca'), '/#biblioteca');
  assert.equal(safeLojaReturnTo('//evil.example'), '/#biblioteca');
  assert.equal(safeLojaReturnTo('https://evil.example'), '/#biblioteca');
});
