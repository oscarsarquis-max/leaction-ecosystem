'use strict';

/**
 * Smoke HTTP — vault-api em :4020 (processo real, não in-process).
 *
 * Pré-requisito: vault-api no ar (`npm start` neste serviço) com admin
 * seedado (`node scripts/seed-admin.js`). Credenciais vêm de
 * VAULT_BOOTSTRAP_EMAIL / VAULT_BOOTSTRAP_PASSWORD no .env do vault-api.
 *
 *   node scripts/smoke-vault-http.js
 *
 * Sistema isolado: smoke-test — limpa ao final (secrets + audit + sistemas).
 * Não remove o admin do seed.
 *
 * --- Verificação manual da casca do Hub (não automatizada) ---
 * 1) vault-api no ar em :4020 e Action Hub FE em :4000.
 * 2) Entrar no Hub como admin e abrir /dashboard/vault.
 * 3) Fazer o segundo login do cofre (e-mail/senha do seed — não o JWT do Hub).
 * 4) Conferir que a lista de sistemas/secrets carrega (valor sempre ••••••••).
 * 5) Clicar em Revelar: modal temporário com o valor e aviso de auditoria.
 * 6) Clicar em Rotacionar: fluxo manual (confirmar aplicação) ou automático,
 *    conforme o sistema de teste.
 */

const path = require('path');
const { Pool } = require('pg');

require('dotenv').config({
  path: path.join(__dirname, '..', '.env'),
  override: false,
});

const VAULT_BASE = (process.env.VAULT_BASE || 'http://127.0.0.1:4020').replace(
  /\/$/,
  ''
);
const EMAIL = String(process.env.VAULT_BOOTSTRAP_EMAIL || '')
  .trim()
  .toLowerCase();
const SENHA = String(process.env.VAULT_BOOTSTRAP_PASSWORD || '');
const SISTEMA = 'smoke-test';
const PLAIN = 'smoke-valor-plano-xyz';

if (!EMAIL.includes('@') || SENHA.length < 8) {
  console.error(
    'Defina VAULT_BOOTSTRAP_EMAIL e VAULT_BOOTSTRAP_PASSWORD (>= 8) no .env do vault-api'
  );
  process.exit(1);
}

const pool = new Pool({
  connectionString:
    process.env.VAULT_DATABASE_URL ||
    'postgresql://vault_api:vault_local_change_me@127.0.0.1:5434/leaction_vault',
});

let passed = 0;
let failed = 0;

function ok(name, detail) {
  passed += 1;
  console.log(`PASS  ${name}${detail ? ` — ${detail}` : ''}`);
}

function fail(name, detail) {
  failed += 1;
  console.error(`FAIL  ${name}${detail ? ` — ${detail}` : ''}`);
}

function expectStatus(name, status, allowed, detail) {
  if (allowed.includes(status)) {
    ok(name, detail || `HTTP ${status}`);
    return true;
  }
  fail(
    name,
    `HTTP ${status} (esperado ${allowed.join('/')})${detail ? ` — ${detail}` : ''}`
  );
  return false;
}

function containsPlain(payload, needle) {
  return JSON.stringify(payload).includes(needle);
}

async function req(method, urlPath, { token, body } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${VAULT_BASE}${urlPath}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    json = { raw: text };
  }
  return { status: res.status, json, headers: res.headers };
}

async function cleanup() {
  await pool.query(
    `DELETE FROM secrets_audit_log
     WHERE secret_id IN (SELECT id FROM secrets WHERE sistema = $1)
        OR detalhe->>'sistema' = $1`,
    [SISTEMA]
  );
  await pool.query(`DELETE FROM secrets WHERE sistema = $1`, [SISTEMA]);
  await pool.query(`DELETE FROM sistemas_rotacao WHERE sistema = $1`, [SISTEMA]);
}

(async () => {
  const health = await req('GET', '/health');
  if (health.status !== 200 || health.json.service !== 'vault-api') {
    throw new Error(
      `vault-api indisponível em ${VAULT_BASE} (HTTP ${health.status})`
    );
  }
  ok('health', `${VAULT_BASE} ${health.json.service}`);

  await cleanup();

  // 1) login inválido → 401; login do seed → 200 + JWT
  const badLogin = await req('POST', '/api/auth/login', {
    body: { email: EMAIL, senha: 'senha-invalida-smoke' },
  });
  expectStatus('1 login inválido', badLogin.status, [401], badLogin.json?.error);

  const login = await req('POST', '/api/auth/login', {
    body: { email: EMAIL, senha: SENHA },
  });
  if (
    expectStatus('1 login seed', login.status, [200]) &&
    login.json?.access_token &&
    login.json?.admin?.email === EMAIL
  ) {
    ok('1 JWT do cofre', `admin=${login.json.admin.email}`);
  } else if (login.status === 200) {
    fail('1 JWT do cofre', JSON.stringify({ ...login.json, access_token: '***' }));
  }
  const token = login.json?.access_token;
  if (!token) {
    throw new Error('sem JWT do cofre — abortando');
  }

  // 2) rota protegida sem JWT → 401
  const noAuth = await req('GET', `/api/secrets?sistema=${SISTEMA}`);
  expectStatus('2 GET secrets sem JWT', noAuth.status, [401], noAuth.json?.error);

  // 3) POST/GET sistemas
  const upSys = await req('POST', '/api/sistemas', {
    token,
    body: {
      sistema: SISTEMA,
      rotation_webhook_url: null,
      suporta_rotacao_automatica: false,
    },
  });
  if (
    expectStatus('3 POST sistemas smoke-test', upSys.status, [200]) &&
    upSys.json?.sistema?.sistema === SISTEMA &&
    upSys.json?.sistema?.suporta_rotacao_automatica === false
  ) {
    ok('3 corpo sistema', 'manual, sem webhook');
  } else if (upSys.status === 200) {
    fail('3 corpo sistema', JSON.stringify(upSys.json));
  }

  const listSys = await req('GET', '/api/sistemas', { token });
  const listedSys = Array.isArray(listSys.json?.sistemas)
    ? listSys.json.sistemas
    : [];
  if (
    expectStatus('3 GET sistemas', listSys.status, [200]) &&
    listedSys.some((s) => s.sistema === SISTEMA)
  ) {
    ok('3 smoke-test na lista', `n=${listedSys.length}`);
  } else if (listSys.status === 200) {
    fail('3 smoke-test na lista', JSON.stringify(listedSys.map((s) => s.sistema)));
  }

  // 4) POST secret — sem texto plano
  const created = await req('POST', '/api/secrets', {
    token,
    body: { sistema: SISTEMA, tipo: 'api_key', valor: PLAIN },
  });
  const createdDump = JSON.stringify(created.json);
  if (expectStatus('4 POST secret', created.status, [201])) {
    if (createdDump.includes(PLAIN) || created.json?.secret?.valor_cifrado) {
      fail('4 POST sem texto plano', 'resposta ecoou valor');
    } else if (created.json?.secret?.id && created.json.secret.status === 'ativo') {
      ok('4 POST só metadados', `id=${created.json.secret.id}`);
    } else {
      fail('4 POST metadados', JSON.stringify(created.json));
    }
  }
  const secretId = created.json?.secret?.id;
  if (!secretId) throw new Error('POST secret não devolveu id');

  // 5) GET lista — nunca o texto real
  const listed = await req('GET', `/api/secrets?sistema=${SISTEMA}`, { token });
  const listedDump = JSON.stringify(listed.json);
  if (expectStatus('5 GET secrets', listed.status, [200])) {
    const rows = Array.isArray(listed.json?.secrets) ? listed.json.secrets : [];
    const leaked = listedDump.includes(PLAIN);
    const hasCipher = rows.some((r) => r.valor_cifrado);
    const realValor = rows.some((r) => r.valor === PLAIN);
    if (leaked || hasCipher || realValor) {
      fail('5 valor mascarado', 'texto plano ou cifrado na lista');
    } else {
      ok('5 valor mascarado', `count=${listed.json.count} sem texto real`);
    }
  }

  // 6) revelar + audit lido
  const beforeRevelar = new Date();
  const revelar = await req('GET', `/api/secrets/${secretId}/revelar`, { token });
  const cache = String(revelar.headers.get('cache-control') || '');
  if (expectStatus('6 revelar', revelar.status, [200])) {
    if (revelar.json?.valor !== PLAIN) {
      fail('6 valor revelado', 'valor diferente do gravado');
    } else if (!cache.includes('no-store')) {
      fail('6 Cache-Control', cache || '(ausente)');
    } else {
      ok('6 valor + no-store', cache);
    }
  }

  const auditLido = await pool.query(
    `SELECT acao, ator, criado_em, detalhe
     FROM secrets_audit_log
     WHERE secret_id = $1 AND acao = 'lido'
       AND detalhe->>'rota' = 'GET /api/secrets/:id/revelar'
     ORDER BY criado_em DESC
     LIMIT 1`,
    [secretId]
  );
  const lido = auditLido.rows[0];
  if (
    lido &&
    lido.ator === EMAIL &&
    lido.criado_em &&
    new Date(lido.criado_em) >= new Date(beforeRevelar.getTime() - 2000)
  ) {
    ok(
      '6 audit lido',
      `ator=${lido.ator} em=${new Date(lido.criado_em).toISOString()}`
    );
  } else {
    fail('6 audit lido', JSON.stringify(lido || auditLido.rows));
  }

  // 7) rotação manual (sem novo_valor, sem webhook)
  const rotated = await req('POST', `/api/secrets/${secretId}/rotacionar`, {
    token,
    body: {},
  });
  const pendingId = rotated.json?.secret?.id;
  if (expectStatus('7 rotacionar manual', rotated.status, [200])) {
    const novo = rotated.json?.valor;
    const okManual =
      rotated.json?.modo === 'manual' &&
      typeof novo === 'string' &&
      novo.length > 0 &&
      rotated.json.secret?.status === 'pendente_aplicacao' &&
      novo !== PLAIN;
    if (!okManual) {
      fail(
        '7 corpo rotação manual',
        JSON.stringify({ ...rotated.json, valor: novo ? '[presente]' : null })
      );
    } else {
      ok('7 nova versão pendente', `id=${pendingId} modo=manual`);
    }
  }
  const oldStatus = await pool.query(`SELECT status FROM secrets WHERE id = $1`, [
    secretId,
  ]);
  if (oldStatus.rows[0]?.status === 'ativo') {
    ok('7 versão anterior ativa', `id=${secretId}`);
  } else {
    fail('7 versão anterior ativa', oldStatus.rows[0]?.status);
  }
  if (!pendingId) throw new Error('rotação manual sem id da nova versão');

  // 8) confirmar aplicação
  const confirmed = await req(
    'POST',
    `/api/secrets/${pendingId}/confirmar-aplicacao`,
    { token }
  );
  if (
    expectStatus('8 confirmar aplicação', confirmed.status, [200]) &&
    confirmed.json?.secret?.status === 'ativo'
  ) {
    ok('8 nova versão ativa', `id=${pendingId}`);
  } else if (confirmed.status === 200) {
    fail('8 nova versão ativa', JSON.stringify(confirmed.json));
  }
  const afterConfirm = await pool.query(
    `SELECT id, status FROM secrets WHERE id = ANY($1::int[])`,
    [[secretId, pendingId]]
  );
  const byId = Object.fromEntries(
    afterConfirm.rows.map((r) => [r.id, r.status])
  );
  if (byId[secretId] === 'revogado' && byId[pendingId] === 'ativo') {
    ok('8 anterior revogada', `id=${secretId}`);
  } else {
    fail('8 anterior revogada', JSON.stringify(byId));
  }

  // 9) histórico sem valor
  const hist = await req('GET', `/api/secrets/${pendingId}/historico`, { token });
  const histDump = JSON.stringify(hist.json);
  const versoes = Array.isArray(hist.json?.versoes) ? hist.json.versoes : [];
  const statuses = versoes.map((v) => v.status).sort();
  if (expectStatus('9 histórico', hist.status, [200])) {
    const hasBoth =
      versoes.length >= 2 &&
      statuses.includes('ativo') &&
      statuses.includes('revogado');
    const leaked =
      histDump.includes(PLAIN) ||
      versoes.some((v) => v.valor || v.valor_cifrado);
    if (!hasBoth) {
      fail('9 duas versões', JSON.stringify(statuses));
    } else if (leaked) {
      fail('9 histórico sem valor', 'texto ou campo valor presente');
    } else {
      ok('9 metadados apenas', statuses.join(','));
    }
  }

  // 10) rotação automática contra porta fechada → 502
  const upAuto = await req('POST', '/api/sistemas', {
    token,
    body: {
      sistema: SISTEMA,
      rotation_webhook_url: 'http://127.0.0.1:1/rotacao',
      rotation_secret: 'smoke-s2s-canal',
      suporta_rotacao_automatica: true,
    },
  });
  if (
    !expectStatus('10 atualiza sistema auto', upAuto.status, [200]) ||
    upAuto.json?.sistema?.suporta_rotacao_automatica !== true
  ) {
    fail('10 sistema auto', JSON.stringify(upAuto.json));
  }

  const beforeFail = new Date();
  const autoFail = await req('POST', `/api/secrets/${pendingId}/rotacionar`, {
    token,
    body: {},
  });
  if (expectStatus('10 rotacionar auto falha', autoFail.status, [502])) {
    if (autoFail.json?.secret?.status === 'pendente_aplicacao') {
      ok('10 nova versão pendente', `id=${autoFail.json.secret.id}`);
    } else {
      fail('10 nova versão pendente', JSON.stringify(autoFail.json?.secret));
    }
  }
  const stillActive = await pool.query(`SELECT status FROM secrets WHERE id = $1`, [
    pendingId,
  ]);
  if (stillActive.rows[0]?.status === 'ativo') {
    ok('10 anterior permanece ativa', `id=${pendingId}`);
  } else {
    fail('10 anterior permanece ativa', stillActive.rows[0]?.status);
  }

  const auditFail = await pool.query(
    `SELECT acao, ator, criado_em, detalhe
     FROM secrets_audit_log
     WHERE acao = 'falha_rotacao'
       AND ator = $1
       AND criado_em >= $2
     ORDER BY criado_em DESC
     LIMIT 1`,
    [EMAIL, new Date(beforeFail.getTime() - 2000)]
  );
  const falha = auditFail.rows[0];
  if (falha && falha.detalhe?.modo === 'automatico') {
    ok(
      '10 audit falha_rotacao',
      `ator=${falha.ator} em=${new Date(falha.criado_em).toISOString()}`
    );
  } else {
    fail('10 audit falha_rotacao', JSON.stringify(falha || auditFail.rows));
  }

  await cleanup();
  await pool.end();

  console.log('');
  console.log(`RESULTADO  ${passed} pass / ${failed} fail`);
  if (failed > 0) process.exit(1);
  console.log('SMOKE_OK');
})().catch(async (err) => {
  console.error(err);
  try {
    await cleanup();
  } catch {
    /* ignore */
  }
  try {
    await pool.end();
  } catch {
    /* ignore */
  }
  process.exit(1);
});
