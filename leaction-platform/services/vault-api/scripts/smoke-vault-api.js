'use strict';

/**
 * Smoke in-process do vault-api (não usa JWT nem banco do Action Hub).
 */

const crypto = require('crypto');
const path = require('path');
const { spawnSync } = require('child_process');
const { Client } = require('pg');

process.env.VAULT_MASTER_KEY =
  process.env.VAULT_MASTER_KEY || crypto.randomBytes(32).toString('hex');
process.env.VAULT_JWT_SECRET =
  process.env.VAULT_JWT_SECRET || crypto.randomBytes(32).toString('hex');
process.env.VAULT_DB_PASSWORD =
  process.env.VAULT_DB_PASSWORD || 'vault_local_change_me';
process.env.VAULT_DATABASE_URL =
  process.env.VAULT_DATABASE_URL ||
  `postgresql://vault_api:${process.env.VAULT_DB_PASSWORD}@127.0.0.1:5434/leaction_vault`;
process.env.VAULT_BOOTSTRAP_DATABASE_URL =
  process.env.VAULT_BOOTSTRAP_DATABASE_URL ||
  'postgresql://admin:password123@127.0.0.1:5434/leaction_hub';

require('dotenv').config({
  path: path.join(__dirname, '..', '.env'),
  override: false,
});

const apply = spawnSync(process.execPath, [path.join(__dirname, 'apply-schema.js')], {
  env: process.env,
  stdio: 'inherit',
});
if (apply.status !== 0) {
  process.exit(apply.status || 1);
}

const { createPool } = require('../lib/db');
const { hashPassword } = require('../lib/passwords');
const { createApp } = require('../server');

const EMAIL = 'smoke.vault@cofre.local';
const SENHA = 'smoke-vault-senha-ok';
const SISTEMA = 'smoke-vault';

function request(app, method, url, { token, body } = {}) {
  return new Promise((resolve, reject) => {
    const server = app.listen(0, '127.0.0.1', async () => {
      const { port } = server.address();
      try {
        const headers = { Accept: 'application/json' };
        if (body !== undefined) headers['Content-Type'] = 'application/json';
        if (token) headers.Authorization = `Bearer ${token}`;
        const res = await fetch(`http://127.0.0.1:${port}${url}`, {
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
        resolve({ status: res.status, json, headers: res.headers });
      } catch (err) {
        reject(err);
      } finally {
        server.close();
      }
    });
  });
}

(async () => {
  const pool = createPool();
  await pool.query(`DELETE FROM secrets_audit_log WHERE ator = $1`, [EMAIL]);
  await pool.query(`DELETE FROM secrets WHERE sistema = $1`, [SISTEMA]);
  await pool.query(`DELETE FROM sistemas_rotacao WHERE sistema = $1`, [SISTEMA]);
  await pool.query(`DELETE FROM vault_admins WHERE email = $1`, [EMAIL]);
  await pool.query(
    `INSERT INTO vault_admins (email, senha_hash, ativo) VALUES ($1, $2, TRUE)`,
    [EMAIL, hashPassword(SENHA)]
  );

  const app = createApp(pool);

  const health = await request(app, 'GET', '/health');
  if (health.status !== 200 || health.json.service !== 'vault-api') {
    throw new Error(`health falhou: ${health.status}`);
  }

  const noAuth = await request(app, 'GET', `/api/secrets?sistema=${SISTEMA}`);
  if (![401, 403].includes(noAuth.status)) {
    throw new Error(`sem JWT deveria 401/403, veio ${noAuth.status}`);
  }

  const badLogin = await request(app, 'POST', '/api/auth/login', {
    body: { email: EMAIL, senha: 'errada' },
  });
  if (badLogin.status !== 401) {
    throw new Error(`login errado deveria 401, veio ${badLogin.status}`);
  }

  const login = await request(app, 'POST', '/api/auth/login', {
    body: { email: EMAIL, senha: SENHA },
  });
  if (login.status !== 200 || !login.json.access_token) {
    throw new Error(`login falhou: ${login.status} ${JSON.stringify(login.json)}`);
  }
  const token = login.json.access_token;

  const upSys = await request(app, 'POST', '/api/sistemas', {
    token,
    body: {
      sistema: SISTEMA,
      rotation_webhook_url: 'http://127.0.0.1:9/rotacao',
      rotation_secret: 'canal-s2s-vault-only',
      suporta_rotacao_automatica: false,
    },
  });
  if (upSys.status !== 200 || upSys.json.sistema?.has_rotation_secret !== true) {
    throw new Error(`POST sistemas falhou: ${JSON.stringify(upSys.json)}`);
  }

  const listSys = await request(app, 'GET', '/api/sistemas', { token });
  if (listSys.status !== 200) throw new Error('GET sistemas falhou');
  if (!listSys.json.sistemas.some((s) => s.sistema === SISTEMA)) {
    throw new Error('sistema smoke não listado');
  }

  const created = await request(app, 'POST', '/api/secrets', {
    token,
    body: { sistema: SISTEMA, tipo: 'api_key', valor: 'super-secreto-xyz' },
  });
  if (created.status !== 201) {
    throw new Error(`POST secret ${created.status} ${JSON.stringify(created.json)}`);
  }
  const dumped = JSON.stringify(created.json);
  if (dumped.includes('super-secreto-xyz') || created.json.secret?.valor_cifrado) {
    throw new Error('POST ecoou valor em texto plano');
  }
  const secretId = created.json.secret.id;

  const listed = await request(app, 'GET', `/api/secrets?sistema=${SISTEMA}`, { token });
  if (listed.status !== 200 || listed.json.count !== 1) {
    throw new Error(`GET secrets falhou: ${JSON.stringify(listed.json)}`);
  }
  if (JSON.stringify(listed.json).includes('super-secreto-xyz')) {
    throw new Error('GET lista vazou valor');
  }

  const revelar = await request(app, 'GET', `/api/secrets/${secretId}/revelar`, { token });
  if (revelar.status !== 200 || revelar.json.valor !== 'super-secreto-xyz') {
    throw new Error(`revelar falhou: ${JSON.stringify(revelar.json)}`);
  }
  const cache = String(revelar.headers.get('cache-control') || '');
  if (!cache.includes('no-store')) {
    throw new Error(`revelar sem no-store: ${cache}`);
  }

  const rotated = await request(app, 'POST', `/api/secrets/${secretId}/rotacionar`, {
    token,
    body: { novo_valor: 'valor-rotacionado-manual' },
  });
  if (rotated.status !== 200 || rotated.json.modo !== 'manual') {
    throw new Error(`rotação manual falhou: ${rotated.status} ${JSON.stringify(rotated.json)}`);
  }
  if (rotated.json.valor !== 'valor-rotacionado-manual') {
    throw new Error('rotação manual deveria devolver o valor uma vez');
  }
  if (!String(rotated.headers.get('cache-control') || '').includes('no-store')) {
    throw new Error('rotação manual sem no-store');
  }
  const pendingId = rotated.json.secret.id;
  if (rotated.json.secret.status !== 'pendente_aplicacao') {
    throw new Error('nova versão deveria ficar pendente_aplicacao');
  }

  const stillActive = await pool.query(`SELECT status FROM secrets WHERE id = $1`, [secretId]);
  if (stillActive.rows[0].status !== 'ativo') {
    throw new Error('versão anterior deveria continuar ativa na rotação manual');
  }

  const confirmed = await request(
    app,
    'POST',
    `/api/secrets/${pendingId}/confirmar-aplicacao`,
    { token }
  );
  if (confirmed.status !== 200 || confirmed.json.secret.status !== 'ativo') {
    throw new Error(`confirmar falhou: ${JSON.stringify(confirmed.json)}`);
  }
  const oldAfter = await pool.query(`SELECT status FROM secrets WHERE id = $1`, [secretId]);
  if (oldAfter.rows[0].status !== 'revogado') {
    throw new Error('versão anterior deveria ficar revogada após confirmar');
  }

  const hist = await request(app, 'GET', `/api/secrets/${secretId}/historico`, { token });
  if (hist.status !== 200 || hist.json.versoes.length < 2) {
    throw new Error(`histórico falhou: ${JSON.stringify(hist.json)}`);
  }
  if (JSON.stringify(hist.json).includes('valor-rotacionado-manual')) {
    throw new Error('histórico vazou valor');
  }

  const http = require('http');
  const received = { headers: null, body: null };
  const webhook = await new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const chunks = [];
      req.on('data', (c) => chunks.push(c));
      req.on('end', () => {
        received.headers = req.headers;
        received.body = Buffer.concat(chunks).toString('utf8');
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end('{"ok":true}');
      });
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
  const whPort = webhook.address().port;

  await pool.query(
    `UPDATE sistemas_rotacao
     SET rotation_webhook_url = $1, suporta_rotacao_automatica = TRUE
     WHERE sistema = $2`,
    [`http://127.0.0.1:${whPort}/rotacao`, SISTEMA]
  );

  const autoOk = await request(app, 'POST', `/api/secrets/${pendingId}/rotacionar`, {
    token,
    body: {},
  });
  if (autoOk.status !== 200 || autoOk.json.modo !== 'automatico') {
    webhook.close();
    throw new Error(`rotação auto falhou: ${autoOk.status} ${JSON.stringify(autoOk.json)}`);
  }
  if (autoOk.json.valor) {
    webhook.close();
    throw new Error('rotação automática não deve devolver valor');
  }
  if (!String(received.headers?.authorization || '').includes('canal-s2s-vault-only')) {
    webhook.close();
    throw new Error('S2S Bearer ausente no webhook');
  }
  const payload = JSON.parse(received.body || '{}');
  if (!payload.tipo || !payload.novo_valor) {
    webhook.close();
    throw new Error(`webhook sem tipo/novo_valor: ${received.body}`);
  }
  webhook.close();

  const autoNewId = autoOk.json.secret.id;
  const prevAfterAuto = await pool.query(`SELECT status FROM secrets WHERE id = $1`, [
    pendingId,
  ]);
  if (prevAfterAuto.rows[0].status !== 'revogado' || autoOk.json.secret.status !== 'ativo') {
    throw new Error('auto sucesso deveria ativar nova e revogar anterior');
  }

  await pool.query(
    `UPDATE sistemas_rotacao
     SET rotation_webhook_url = $1, suporta_rotacao_automatica = TRUE
     WHERE sistema = $2`,
    ['http://127.0.0.1:1/rotacao', SISTEMA]
  );
  const autoFail = await request(app, 'POST', `/api/secrets/${autoNewId}/rotacionar`, {
    token,
    body: { novo_valor: 'nao-deve-aplicar' },
  });
  if (autoFail.status !== 502) {
    throw new Error(`auto falha deveria 502, veio ${autoFail.status}`);
  }
  if (JSON.stringify(autoFail.json).includes('nao-deve-aplicar')) {
    throw new Error('falha de rotação vazou o novo valor');
  }
  const still = await pool.query(`SELECT status FROM secrets WHERE id = $1`, [autoNewId]);
  if (still.rows[0].status !== 'ativo') {
    throw new Error('versão anterior deve permanecer ativa após falha_rotacao');
  }
  const pendingFail = await pool.query(
    `SELECT status FROM secrets WHERE sistema = $1 AND tipo = 'api_key' AND versao = (
       SELECT MAX(versao) FROM secrets WHERE sistema = $1 AND tipo = 'api_key'
     )`,
    [SISTEMA]
  );
  if (pendingFail.rows[0].status !== 'pendente_aplicacao') {
    throw new Error('nova versão da falha deveria ficar pendente_aplicacao');
  }

  const badNivel = await request(app, 'POST', '/api/contas', {
    token,
    body: { sistema: SISTEMA, email: 'adm@cofre.test', nivel: 'root' },
  });
  if (badNivel.status !== 400) {
    throw new Error(`nivel inválido deveria 400, veio ${badNivel.status}`);
  }

  const contaManual = await request(app, 'POST', '/api/contas', {
    token,
    body: {
      sistema: SISTEMA,
      email: 'adm.manual@cofre.test',
      nivel: 'admin',
      funcao: 'cofre_admin',
    },
  });
  if (contaManual.status !== 201 || contaManual.json.modo !== 'manual') {
    throw new Error(`POST contas manual falhou: ${JSON.stringify(contaManual.json)}`);
  }
  if (!contaManual.json.valor || contaManual.json.secret?.usuario_email !== 'adm.manual@cofre.test') {
    throw new Error('criação manual deveria devolver a senha uma vez');
  }
  if (contaManual.json.secret.status !== 'pendente_aplicacao') {
    throw new Error('conta manual deveria ficar pendente_aplicacao');
  }
  if (!String(contaManual.headers.get('cache-control') || '').includes('no-store')) {
    throw new Error('POST contas manual sem no-store');
  }
  const contaManualId = contaManual.json.secret.id;
  const senhaManual = contaManual.json.valor;

  const listedInfra = await request(app, 'GET', `/api/secrets?sistema=${SISTEMA}`, { token });
  if (JSON.stringify(listedInfra.json).includes('adm.manual@cofre.test')) {
    throw new Error('GET /api/secrets não deve listar senha_conta');
  }

  const listedContas = await request(app, 'GET', `/api/contas?sistema=${SISTEMA}`, { token });
  if (listedContas.status !== 200 || !listedContas.json.identidade?.nivel_funcao) {
    throw new Error(`GET contas falhou: ${JSON.stringify(listedContas.json)}`);
  }
  if (JSON.stringify(listedContas.json).includes(senhaManual)) {
    throw new Error('GET /api/contas vazou a senha');
  }
  if (!listedContas.json.contas.some((c) => c.usuario_email === 'adm.manual@cofre.test')) {
    throw new Error('GET /api/contas não listou a conta criada');
  }

  const revelarConta = await request(app, 'GET', `/api/secrets/${contaManualId}/revelar`, {
    token,
  });
  if (revelarConta.status !== 200 || revelarConta.json.valor !== senhaManual) {
    throw new Error(`revelar conta falhou: ${JSON.stringify(revelarConta.json)}`);
  }
  const auditRevelar = await pool.query(
    `SELECT detalhe FROM secrets_audit_log
     WHERE secret_id = $1 AND acao = 'lido' AND detalhe->>'rota' = 'GET /api/secrets/:id/revelar'
     ORDER BY id DESC LIMIT 1`,
    [contaManualId]
  );
  if (auditRevelar.rows[0]?.detalhe?.usuario_email !== 'adm.manual@cofre.test') {
    throw new Error(`audit revelar sem usuario_email: ${JSON.stringify(auditRevelar.rows[0])}`);
  }

  const confConta = await request(
    app,
    'POST',
    `/api/secrets/${contaManualId}/confirmar-aplicacao`,
    { token }
  );
  if (confConta.status !== 200 || confConta.json.secret.status !== 'ativo') {
    throw new Error(`confirmar conta falhou: ${JSON.stringify(confConta.json)}`);
  }

  const rotContaManual = await request(app, 'POST', `/api/secrets/${contaManualId}/rotacionar`, {
    token,
    body: { novo_valor: 'senha-conta-rotacionada' },
  });
  if (rotContaManual.status !== 200 || rotContaManual.json.modo !== 'manual') {
    throw new Error(`rotação manual de conta falhou: ${JSON.stringify(rotContaManual.json)}`);
  }
  if (rotContaManual.json.valor !== 'senha-conta-rotacionada') {
    throw new Error('rotação manual de conta deveria devolver o valor uma vez');
  }
  const contaPendingId = rotContaManual.json.secret.id;
  const confRotConta = await request(
    app,
    'POST',
    `/api/secrets/${contaPendingId}/confirmar-aplicacao`,
    { token }
  );
  if (confRotConta.status !== 200) {
    throw new Error(`confirmar rotação conta falhou: ${JSON.stringify(confRotConta.json)}`);
  }
  const oldConta = await pool.query(`SELECT status FROM secrets WHERE id = $1`, [contaManualId]);
  if (oldConta.rows[0].status !== 'revogado') {
    throw new Error('versão anterior da conta deveria ficar revogada');
  }

  const receivedConta = { headers: null, body: null };
  const webhookConta = await new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const chunks = [];
      req.on('data', (c) => chunks.push(c));
      req.on('end', () => {
        receivedConta.headers = req.headers;
        receivedConta.body = Buffer.concat(chunks).toString('utf8');
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end('{"ok":true}');
      });
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
  const contaWhPort = webhookConta.address().port;

  await request(app, 'POST', '/api/sistemas', {
    token,
    body: {
      sistema: SISTEMA,
      rotation_webhook_url: 'http://127.0.0.1:9/rotacao',
      rotation_secret: 'canal-s2s-vault-only',
      suporta_rotacao_automatica: false,
      conta_webhook_url: `http://127.0.0.1:${contaWhPort}/contas`,
      conta_secret: 'canal-s2s-contas-only',
    },
  });

  const contaAuto = await request(app, 'POST', '/api/contas', {
    token,
    body: {
      sistema: SISTEMA,
      email: 'gestor.auto@cofre.test',
      nivel: 'gestor_produtivo',
      senha: 'senha-gestor-auto-ok',
    },
  });
  if (contaAuto.status !== 201 || contaAuto.json.modo !== 'automatico') {
    webhookConta.close();
    throw new Error(`POST contas auto falhou: ${JSON.stringify(contaAuto.json)}`);
  }
  if (contaAuto.json.valor) {
    webhookConta.close();
    throw new Error('criação automática de conta não deve devolver senha');
  }
  const criaPayload = JSON.parse(receivedConta.body || '{}');
  if (
    criaPayload.acao !== 'criar' ||
    criaPayload.email !== 'gestor.auto@cofre.test' ||
    criaPayload.senha !== 'senha-gestor-auto-ok' ||
    criaPayload.nivel !== 'gestor_produtivo'
  ) {
    webhookConta.close();
    throw new Error(`S2S criar conta payload errado: ${receivedConta.body}`);
  }
  if (!String(receivedConta.headers?.authorization || '').includes('canal-s2s-contas-only')) {
    webhookConta.close();
    throw new Error('S2S de contas usou o canal errado');
  }
  const contaAutoId = contaAuto.json.secret.id;
  if (contaAuto.json.secret.status !== 'ativo') {
    webhookConta.close();
    throw new Error('criação automática deveria ativar o secret');
  }

  receivedConta.body = null;
  const rotContaAuto = await request(app, 'POST', `/api/secrets/${contaAutoId}/rotacionar`, {
    token,
    body: { novo_valor: 'senha-gestor-rotacionada' },
  });
  if (rotContaAuto.status !== 200 || rotContaAuto.json.modo !== 'automatico') {
    webhookConta.close();
    throw new Error(`rotação auto de conta falhou: ${JSON.stringify(rotContaAuto.json)}`);
  }
  const rotPayload = JSON.parse(receivedConta.body || '{}');
  if (
    rotPayload.acao !== 'rotacionar_senha' ||
    rotPayload.email !== 'gestor.auto@cofre.test' ||
    rotPayload.novo_valor !== 'senha-gestor-rotacionada' ||
    rotPayload.tipo
  ) {
    webhookConta.close();
    throw new Error(`S2S rotacionar conta payload errado: ${receivedConta.body}`);
  }
  webhookConta.close();

  await request(app, 'POST', '/api/sistemas', {
    token,
    body: {
      sistema: SISTEMA,
      rotation_webhook_url: 'http://127.0.0.1:9/rotacao',
      rotation_secret: 'canal-s2s-vault-only',
      suporta_rotacao_automatica: false,
      conta_webhook_url: 'http://127.0.0.1:1/contas',
      conta_secret: 'canal-s2s-contas-only',
    },
  });
  const contaFail = await request(app, 'POST', '/api/contas', {
    token,
    body: {
      sistema: SISTEMA,
      email: 'fail@cofre.test',
      nivel: 'usuario_executor',
    },
  });
  if (contaFail.status !== 502) {
    throw new Error(`criação auto falha deveria 502, veio ${contaFail.status}`);
  }
  if (contaFail.json.secret?.status !== 'pendente_aplicacao') {
    throw new Error('falha_criacao deveria deixar pendente_aplicacao');
  }
  const auditFail = await pool.query(
    `SELECT acao FROM secrets_audit_log
     WHERE secret_id = $1 AND acao = 'falha_criacao' LIMIT 1`,
    [contaFail.json.secret.id]
  );
  if (!auditFail.rows[0]) {
    throw new Error('audit deveria registrar falha_criacao');
  }

  const audit = await pool.query(
    `SELECT acao, COUNT(*)::int AS n FROM secrets_audit_log
     WHERE ator = $1 GROUP BY acao ORDER BY acao`,
    [EMAIL]
  );
  const byAcao = Object.fromEntries(audit.rows.map((r) => [r.acao, r.n]));
  if (!byAcao.criado || !byAcao.lido) {
    throw new Error(`audit incompleto: ${JSON.stringify(byAcao)}`);
  }

  await pool.query(`DELETE FROM secrets_audit_log WHERE ator = $1`, [EMAIL]);
  await pool.query(`DELETE FROM secrets WHERE sistema = $1`, [SISTEMA]);
  await pool.query(`DELETE FROM sistemas_rotacao WHERE sistema = $1`, [SISTEMA]);
  await pool.query(`DELETE FROM vault_admins WHERE email = $1`, [EMAIL]);
  await pool.end();

  console.log('audit', byAcao);
  console.log('SMOKE_OK');
})().catch(async (err) => {
  console.error(err);
  try {
    const c = new Client({ connectionString: process.env.VAULT_DATABASE_URL });
    await c.connect();
    await c.query(`DELETE FROM secrets_audit_log WHERE ator = $1`, [EMAIL]);
    await c.query(`DELETE FROM secrets WHERE sistema = $1`, [SISTEMA]);
    await c.query(`DELETE FROM sistemas_rotacao WHERE sistema = $1`, [SISTEMA]);
    await c.query(`DELETE FROM vault_admins WHERE email = $1`, [EMAIL]);
    await c.end();
  } catch {
    /* ignore */
  }
  process.exit(1);
});
