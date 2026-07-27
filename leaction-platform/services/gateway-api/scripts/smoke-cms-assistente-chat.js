'use strict';

/**
 * Smoke — CMS Assistente Chat (Nina / inove4us)
 *
 * Uso (gateway no ar em :4001, seed aplicado):
 *   node services/gateway-api/scripts/smoke-cms-assistente-chat.js
 *
 * Env:
 *   HUB_BASE / ACTION_HUB_API_URL  (default http://127.0.0.1:4001)
 *   JWT_SECRET, HUB_ADMIN_EMAILS / HUB_SYSADMIN_EMAIL
 *   INOVE4US_API_URL (opcional, default http://127.0.0.1:5010) — checagem manual documentada
 */

const path = require('path');
const jwt = require('jsonwebtoken');

try {
  require('dotenv').config({
    path: path.join(__dirname, '../../../.env'),
    override: false,
  });
} catch {
  /* dotenv opcional */
}

const HUB_BASE = (
  process.env.HUB_BASE ||
  process.env.ACTION_HUB_API_URL ||
  process.env.HUB_API_URL ||
  'http://127.0.0.1:4001'
).replace(/\/$/, '');

const INOVE_BASE = (
  process.env.INOVE4US_API_URL ||
  'http://127.0.0.1:5010'
).replace(/\/$/, '');

const JWT_SECRET = process.env.JWT_SECRET || 'super-secret-hub-key-2026';
const ADMIN_EMAIL =
  (process.env.HUB_ADMIN_EMAILS || '')
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean)[0] ||
  process.env.HUB_SYSADMIN_EMAIL ||
  'sysadmin@inove4us.com.br';

const ACTIONS_OK = new Set(['open_upgrade']);

let failed = 0;
let passed = 0;

function ok(name, detail) {
  passed += 1;
  console.log(`PASS  ${name}${detail ? ` — ${detail}` : ''}`);
}

function fail(name, detail) {
  failed += 1;
  console.error(`FAIL  ${name}${detail ? ` — ${detail}` : ''}`);
}

async function req(method, urlPath, { token, body } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
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

function assertTreeShape(tree) {
  if (!tree || typeof tree !== 'object') return 'tree ausente';
  if (!tree.avatar_name) return 'avatar_name ausente';
  if (!tree.avatar_tagline) return 'avatar_tagline ausente';
  if (!tree.root_id) return 'root_id ausente';
  if (!tree.nodes || typeof tree.nodes !== 'object') return 'nodes ausente';
  if (!(tree.root_id in tree.nodes)) {
    return `root_id '${tree.root_id}' não está em nodes`;
  }
  return null;
}

function assertTreeIntegrity(tree) {
  const errors = [];
  const nodes = tree.nodes || {};
  for (const [nid, node] of Object.entries(nodes)) {
    const options = Array.isArray(node?.options) ? node.options : [];
    options.forEach((opt, idx) => {
      const prefix = `${nid}.options[${idx}]`;
      if (opt.next != null && String(opt.next).trim() !== '') {
        const next = String(opt.next).trim();
        if (!(next in nodes)) {
          errors.push(`${prefix}.next '${next}' inexistente`);
        }
      }
      if (opt.href != null && String(opt.href).trim() !== '') {
        const href = String(opt.href).trim();
        if (!href.startsWith('/')) {
          errors.push(`${prefix}.href '${href}' não começa com /`);
        }
      }
      if (opt.action != null && String(opt.action).trim() !== '') {
        const action = String(opt.action).trim();
        if (!ACTIONS_OK.has(action)) {
          errors.push(`${prefix}.action '${action}' fora da whitelist`);
        }
      }
    });
  }
  return errors;
}

(async () => {
  console.log('HUB_BASE=', HUB_BASE);
  console.log('ADMIN_EMAIL=', ADMIN_EMAIL);

  // 1) GET público
  const pub = await req(
    'GET',
    '/api/cms/assistente-chat?sistema_destino=inove4us'
  );
  if (pub.status !== 200) {
    fail('1 GET público 200', `status=${pub.status} body=${JSON.stringify(pub.json)}`);
  } else {
    const shapeErr = assertTreeShape(pub.json?.tree);
    if (shapeErr) fail('1 GET shape', shapeErr);
    else {
      ok(
        '1 GET público',
        `avatar=${pub.json.tree.avatar_name} root=${pub.json.tree.root_id} nodes=${Object.keys(pub.json.tree.nodes).length}`
      );
    }
  }

  // 2–4) Integridade da árvore publicada
  if (pub.status === 200 && pub.json?.tree) {
    const integ = assertTreeIntegrity(pub.json.tree);
    if (integ.length) fail('2-4 integridade', integ.join(' | '));
    else ok('2-4 integridade next/href/action', 'ok');
  } else {
    fail('2-4 integridade', 'pulado (GET público falhou)');
  }

  // 5) Admin sem JWT
  const noAuth = await req(
    'GET',
    '/api/cms/assistente-chat/admin?sistema_destino=inove4us'
  );
  if (noAuth.status === 401 || noAuth.status === 403) {
    ok('5 admin sem JWT', `status=${noAuth.status}`);
  } else {
    fail('5 admin sem JWT', `esperado 401/403, got ${noAuth.status}`);
  }

  // 6) PUT inválido (precisa JWT)
  const token = jwt.sign({ sub: 'smoke-assistente', email: ADMIN_EMAIL }, JWT_SECRET, {
    expiresIn: '1h',
  });

  const baseTree =
    pub.status === 200 && pub.json?.tree
      ? JSON.parse(JSON.stringify(pub.json.tree))
      : {
          avatar_name: 'Nina',
          avatar_tagline: 'Guia do inovador',
          root_id: 'inicio',
          nodes: {
            inicio: {
              message: 'oi',
              options: [{ label: 'x', next: 'ghost_node' }],
            },
          },
        };

  // Garante next quebrado
  const rootId = baseTree.root_id || 'inicio';
  if (!baseTree.nodes[rootId]) {
    baseTree.nodes[rootId] = { message: 'oi', options: [] };
  }
  baseTree.nodes[rootId].options = [
    { label: 'Opção quebrada (smoke)', next: 'node_inexistente_smoke' },
  ];

  const badPut = await req('PUT', '/api/cms/assistente-chat', {
    token,
    body: {
      sistema_destino: 'inove4us',
      status: 'publicado',
      tree: baseTree,
    },
  });

  if (badPut.status !== 400) {
    fail(
      '6 PUT inválido → 400',
      `status=${badPut.status} body=${JSON.stringify(badPut.json)}`
    );
  } else {
    const errors = Array.isArray(badPut.json?.errors) ? badPut.json.errors : [];
    const hasSpecific =
      errors.some((e) => /node_inexistente_smoke|não existe|inexistente/i.test(String(e))) ||
      /inválid|não existe|inexistente/i.test(String(badPut.json?.error || ''));
    if (!hasSpecific) {
      fail(
        '6 PUT erro específico',
        `400 sem detalhe útil: ${JSON.stringify(badPut.json)}`
      );
    } else {
      ok(
        '6 PUT inválido → 400',
        `errors=${errors.length || 1}: ${(errors[0] || badPut.json.error || '').slice(0, 80)}`
      );
    }
  }

  // PUT sem auth também deve negar
  const putNoAuth = await req('PUT', '/api/cms/assistente-chat', {
    body: {
      sistema_destino: 'inove4us',
      status: 'rascunho',
      tree: { avatar_name: 'Nina', root_id: 'inicio', nodes: { inicio: { message: 'x', options: [] } } },
    },
  });
  if (putNoAuth.status === 401 || putNoAuth.status === 403) {
    ok('6b PUT sem JWT', `status=${putNoAuth.status}`);
  } else {
    fail('6b PUT sem JWT', `esperado 401/403, got ${putNoAuth.status}`);
  }

  // Confirma que o publicado íntegro continua intacto após PUT inválido
  const pub2 = await req(
    'GET',
    '/api/cms/assistente-chat?sistema_destino=inove4us'
  );
  if (pub2.status === 200 && assertTreeIntegrity(pub2.json.tree).length === 0) {
    ok('pós-PUT publicado intacto', `root=${pub2.json.tree.root_id}`);
  } else {
    fail('pós-PUT publicado intacto', JSON.stringify(pub2.json)?.slice(0, 200));
  }

  // Passo manual / checagem opcional inove4us
  console.log('\n--- Checagem opcional inove4us (não conta como fail do smoke Hub) ---');
  try {
    const inv = await fetch(`${INOVE_BASE}/api/assistente-chat`, {
      headers: { Accept: 'application/json' },
    });
    const invJson = await inv.json().catch(() => ({}));
    if (inv.ok && invJson.source === 'hub') {
      console.log(`NOTE  inove4us source=hub (OK) — ${INOVE_BASE}/api/assistente-chat`);
    } else if (inv.ok) {
      console.log(
        `NOTE  inove4us respondeu source=${invJson.source || '?'} (esperado "hub" com gateway no ar). ` +
          'Se for "fallback", confira ACTION_HUB_API_URL no backend inove4us.'
      );
    } else {
      console.log(`NOTE  inove4us HTTP ${inv.status} — pule ou suba o serviço.`);
    }
    console.log(
      'MANUAL: derrube o gateway e repita GET inove4us /api/assistente-chat → deve cair em source=fallback.'
    );
  } catch (e) {
    console.log(
      `NOTE  inove4us indisponível (${e.message}). Passo manual: com gateway UP → source=hub; gateway DOWN → source=fallback.`
    );
  }

  console.log(`\nRESULTADO: ${passed} pass, ${failed} fail`);
  if (failed > 0) process.exit(1);
  console.log('SMOKE_OK cms-assistente-chat');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
