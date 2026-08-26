'use strict';

/**
 * Smoke HTTP — Gestão de Identidade (gateway :4001)
 *
 * Uso (gateway no ar):
 *   node services/gateway-api/scripts/smoke-identidade-http.js
 *
 * Cobre S2S (app_registry.webhook_secret) e rotas admin (JWT Hub).
 * Sistema isolado: smoke-test — limpa ao final.
 *
 * --- Verificação manual Phanton (não automatizada) ---
 * 1) Hub no ar. No Phanton: POST /api/auth/register com código válido.
 *    Conferir GET {HUB}/api/identidade/usuarios/{email}?sistema=phanton (S2S)
 *    e sync_pendente=false no Phanton.
 * 2) Derrubar o gateway do Hub e cadastrar de novo: usuário local ok,
 *    sync_pendente=true.
 * 3) Usuário já sincronizado (cache 8 min) + Hub fora: ação autorizada
 *    por nível continua (cache); sem cache, bloqueia.
 */

const path = require('path');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');

require('dotenv').config({
  path: path.join(__dirname, '../../../.env'),
  override: true,
});

const HUB_BASE = (
  process.env.HUB_BASE ||
  process.env.ACTION_HUB_API_URL ||
  process.env.HUB_API_URL ||
  'http://127.0.0.1:4001'
).replace(/\/$/, '');

const JWT_SECRET = process.env.JWT_SECRET || 'super-secret-hub-key-2026';
const ADMIN_EMAIL =
  (process.env.HUB_ADMIN_EMAILS || '')
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean)[0] ||
  process.env.HUB_SYSADMIN_EMAIL ||
  'admin@actionhub.com.br';

const SISTEMA = 'smoke-test';
const S2S_SECRET = 'dev-identidade-http-smoke-secret';
const EMAIL = 'smoke.identidade@test.local';
const EMAIL_MISSING = 'smoke.ausente@test.local';

function parseDatabaseUrl(url) {
  if (!url) return null;
  try {
    const u = new URL(url);
    return {
      host: u.hostname,
      port: Number(u.port || 5432),
      database: decodeURIComponent(u.pathname.replace(/^\//, '')),
      user: decodeURIComponent(u.username),
      password: decodeURIComponent(u.password),
    };
  } catch {
    return null;
  }
}

const db = parseDatabaseUrl(process.env.DATABASE_URL) || {
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || 5434),
  database: process.env.DB_NAME || 'leaction_hub',
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASS || 'password123',
};

const pool = new Pool(db);

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
  fail(name, `HTTP ${status} (esperado ${allowed.join('/')})${detail ? ` — ${detail}` : ''}`);
  return false;
}

async function req(method, urlPath, { token, secret, body } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  if (secret) {
    headers.Authorization = `Bearer ${secret}`;
    headers['X-App-Secret'] = secret;
  }
  const res = await fetch(`${HUB_BASE}${urlPath}`, {
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
  return { status: res.status, json };
}

function adminToken() {
  return jwt.sign({ email: ADMIN_EMAIL, sub: 'identidade-http-smoke' }, JWT_SECRET, {
    expiresIn: '20m',
  });
}

async function cleanup() {
  await pool.query(`DELETE FROM identidade_usuarios WHERE sistema = $1`, [SISTEMA]);
  await pool.query(`DELETE FROM identidade_funcoes WHERE sistema = $1`, [SISTEMA]);
  await pool.query(`DELETE FROM identidade_permissoes WHERE sistema = $1`, [SISTEMA]);
}

(async () => {
  const health = await req('GET', '/health');
  if (health.status !== 200) {
    throw new Error(`Gateway indisponível em ${HUB_BASE} (HTTP ${health.status})`);
  }

  await pool.query(
    `INSERT INTO app_registry (app_id, name, webhook_secret, return_origins, active)
     VALUES ($1, 'Identidade HTTP smoke', $2, ARRAY[]::TEXT[], TRUE)
     ON CONFLICT (app_id) DO UPDATE
       SET webhook_secret = EXCLUDED.webhook_secret,
           active = TRUE`,
    [SISTEMA, S2S_SECRET]
  );
  await cleanup();

  const admin = adminToken();

  // 1) POST S2S cria usuário executor
  const created = await req('POST', '/api/identidade/usuarios', {
    secret: S2S_SECRET,
    body: {
      sistema: SISTEMA,
      email: EMAIL,
      nome: 'Smoke Executor',
      nivel: 'usuario_executor',
    },
  });
  expectStatus('1 POST S2S cria usuario_executor', created.status, [200, 201]);
  const userId = created.json?.usuario?.id;
  if (created.json?.usuario?.nivel !== 'usuario_executor') {
    fail('1 corpo POST', `nivel=${created.json?.usuario?.nivel}`);
  } else {
    ok('1 corpo POST', `id=${userId}`);
  }

  // 2) GET S2S perfil coerente
  const perfil = await req(
    'GET',
    `/api/identidade/usuarios/${encodeURIComponent(EMAIL)}?sistema=${SISTEMA}`,
    { secret: S2S_SECRET }
  );
  if (
    expectStatus('2 GET S2S perfil existente', perfil.status, [200]) &&
    perfil.json?.nivel === 'usuario_executor' &&
    perfil.json?.status === 'ativo' &&
    Array.isArray(perfil.json?.permissoes)
  ) {
    ok(
      '2 corpo GET',
      `nivel=${perfil.json.nivel} funcao=${perfil.json.funcao} permissoes=[${perfil.json.permissoes}] status=${perfil.json.status}`
    );
  } else if (perfil.status === 200) {
    fail('2 corpo GET', JSON.stringify(perfil.json));
  }

  // 3) GET email inexistente → 404
  const missing = await req(
    'GET',
    `/api/identidade/usuarios/${encodeURIComponent(EMAIL_MISSING)}?sistema=${SISTEMA}`,
    { secret: S2S_SECRET }
  );
  expectStatus('3 GET email inexistente', missing.status, [404], missing.json?.error);

  // 4) POST funcao inexistente → 400 específico
  const badFn = await req('POST', '/api/identidade/usuarios', {
    secret: S2S_SECRET,
    body: {
      sistema: SISTEMA,
      email: 'smoke.badfn@test.local',
      nome: 'Smoke Bad Fn',
      nivel: 'usuario_executor',
      funcao: 'nao_existe_xyz',
    },
  });
  const badMsg = String(badFn.json?.error || '');
  if (expectStatus('4 POST funcao inexistente', badFn.status, [400], badMsg)) {
    if (badMsg.includes('não existe') && !/500/.test(String(badFn.status))) {
      ok('4 erro específico', badMsg);
    } else {
      fail('4 erro específico', badMsg || JSON.stringify(badFn.json));
    }
  }

  // 5) Rotas admin sem JWT → 401/403
  const noAdminPut = await req('PUT', `/api/identidade/usuarios/${userId || 1}`, {
    body: { nivel: 'admin', status: 'ativo' },
  });
  expectStatus('5 PUT usuario sem admin', noAdminPut.status, [401, 403]);

  const noAdminFn = await req('POST', '/api/identidade/funcoes', {
    body: {
      sistema: SISTEMA,
      nome: 'ghost',
      nivel_associado: 'admin',
      permissoes: [],
    },
  });
  expectStatus('5 POST funcoes sem admin', noAdminFn.status, [401, 403]);

  const noAdminPerm = await req('POST', '/api/identidade/permissoes', {
    body: { sistema: SISTEMA, chave: 'ghost', descricao: 'x' },
  });
  expectStatus('5 POST permissoes sem admin', noAdminPerm.status, [401, 403]);

  // 6) S2S ausente / errado → 401/403
  const noSecret = await req('POST', '/api/identidade/usuarios', {
    body: {
      sistema: SISTEMA,
      email: EMAIL,
      nome: 'Smoke',
      nivel: 'usuario_executor',
    },
  });
  expectStatus('6 POST sem S2S', noSecret.status, [401, 403]);

  const badSecret = await req(
    'GET',
    `/api/identidade/usuarios/${encodeURIComponent(EMAIL)}?sistema=${SISTEMA}`,
    { secret: 'secret-errado-nao-e-o-do-registry' }
  );
  expectStatus('6 GET S2S secret errado', badSecret.status, [401, 403]);

  // 7) Função admin (X,Y) + catálogo extra Z; GET inclui X,Y e herança do nível
  const permX = await req('POST', '/api/identidade/permissoes', {
    token: admin,
    body: { sistema: SISTEMA, chave: 'perm_x', descricao: 'Permissão X' },
  });
  const permY = await req('POST', '/api/identidade/permissoes', {
    token: admin,
    body: { sistema: SISTEMA, chave: 'perm_y', descricao: 'Permissão Y' },
  });
  const permZ = await req('POST', '/api/identidade/permissoes', {
    token: admin,
    body: { sistema: SISTEMA, chave: 'perm_z', descricao: 'Permissão Z (só catálogo)' },
  });
  if ([permX, permY, permZ].every((r) => r.status === 201 || r.status === 200)) {
    ok('7 catálogo X,Y,Z', 'perm_x perm_y perm_z');
  } else {
    fail(
      '7 catálogo X,Y,Z',
      `HTTP ${permX.status}/${permY.status}/${permZ.status}`
    );
  }

  const fnAdmin = await req('POST', '/api/identidade/funcoes', {
    token: admin,
    body: {
      sistema: SISTEMA,
      nome: 'coordenador',
      nivel_associado: 'admin',
      permissoes: ['perm_x', 'perm_y'],
    },
  });
  expectStatus('7 POST funcao coordenador', fnAdmin.status, [200, 201]);

  const upsertAdmin = await req('POST', '/api/identidade/usuarios', {
    secret: S2S_SECRET,
    body: {
      sistema: SISTEMA,
      email: EMAIL,
      nome: 'Smoke Admin Fn',
      nivel: 'admin',
      funcao: 'coordenador',
    },
  });
  expectStatus('7 POST usuario admin+coordenador', upsertAdmin.status, [200, 201]);

  const adminPerfil = await req(
    'GET',
    `/api/identidade/usuarios/${encodeURIComponent(EMAIL)}?sistema=${SISTEMA}`,
    { secret: S2S_SECRET }
  );
  const perms = Array.isArray(adminPerfil.json?.permissoes)
    ? adminPerfil.json.permissoes
    : [];
  const hasXY = perms.includes('perm_x') && perms.includes('perm_y');
  const hasZ = perms.includes('perm_z');
  if (adminPerfil.status === 200 && hasXY && hasZ) {
    ok(
      '7 GET permissoes admin+funcao',
      `inclui X,Y da função e Z da herança do nível: [${perms.join(', ')}]`
    );
  } else {
    fail(
      '7 GET permissoes admin+funcao',
      `HTTP ${adminPerfil.status} perms=${JSON.stringify(perms)}`
    );
  }

  await cleanup();
  await pool.query(`DELETE FROM app_registry WHERE app_id = $1`, [SISTEMA]);
  await pool.end();

  console.log('');
  console.log(`RESULTADO  ${passed} pass / ${failed} fail`);
  if (failed > 0) process.exit(1);
  console.log('SMOKE_OK');
})().catch(async (err) => {
  console.error(err);
  try {
    await cleanup();
    await pool.query(`DELETE FROM app_registry WHERE app_id = $1`, [SISTEMA]);
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
