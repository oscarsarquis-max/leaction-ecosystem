'use strict';

/**
 * BLOG-025 — receitas dos leitores (Hub). Tudo com mocks: sem Bedrock, S3, Loja nem Postgres.
 *
 * node --test domain/cms-receitas.test.js
 */
const { describe, it, after, afterEach, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const express = require('express');
const {
  registerCmsReceitasRoutes,
  purgeTelefonesDecididos,
  resetReceitasRateLimit,
  validateIntake,
  normalizeTelefone,
  maskTelefone,
  buildWhatsappUrl,
  stripJpegMetadata,
  INTAKE_DAILY_LIMIT,
} = require('./cms-receitas');

process.env.LEPAIN_CMS_KEY = 'blog-025-test-key';
const KEY = process.env.LEPAIN_CMS_KEY;
const TEL_INPUT = '(11) 98765-4321';
const TEL = '5511987654321';

const REVISAO_BEDROCK = {
  correcoes_pt: ['"farinha" estava sem acento'],
  alerta_dado_pessoal: false,
  en: {
    titulo: 'Grandma loaf',
    historia: 'A story long enough to be published on the blog.',
    ingredientes: 'flour, water, salt',
    preparo: 'mix, rest and bake',
    dica: 'Use a hot oven',
    tempo: '3h',
    rendimento: '2 loaves',
    nivel: 'easy',
  },
};

function jpegComExif() {
  const app0 = Buffer.concat([
    Buffer.from([0xff, 0xe0, 0x00, 0x10]),
    Buffer.from('JFIF\0', 'ascii'),
    Buffer.from([0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00]),
  ]);
  const exifBody = Buffer.from('Exif\0\0GPS-SECRETO-1234', 'ascii');
  const app1 = Buffer.concat([
    Buffer.from([0xff, 0xe1, 0x00, exifBody.length + 2]),
    exifBody,
  ]);
  const dqt = Buffer.from([0xff, 0xdb, 0x00, 0x04, 0x00, 0x01]);
  const sos = Buffer.from([0xff, 0xda, 0x00, 0x02]);
  return Buffer.concat([Buffer.from([0xff, 0xd8]), app0, app1, dqt, sos, Buffer.from('PIXELS'), Buffer.from([0xff, 0xd9])]);
}

/** Banco em memória que entende só as queries usadas por cms-receitas. */
function createFakePool() {
  const db = { receitas: [], posts: [], nextReceita: 1, nextPost: 100, log: [] };
  const norm = (s) => s.replace(/\s+/g, ' ').trim();
  const findReceita = (id) => db.receitas.find((r) => r.id === Number(id));

  const pool = {
    db,
    async query(sql, params = []) {
      const q = norm(sql);
      db.log.push({ q, params });
      if (q.startsWith('INSERT INTO cms_receitas')) {
        const [nome, cidade, instagram, telefone, titulo, historia, ingredientes, preparo, foto_url, idioma, cliente_loja, revisao] = params;
        db.receitas.push({
          id: db.nextReceita++, nome, cidade, instagram, telefone, titulo, historia, ingredientes, preparo,
          foto_url, idioma, consentimento: true, status: 'recebida', cliente_loja,
          ponto_creditado_em: null, revisao: JSON.parse(revisao), post_grupo_id: null,
          criado_em: new Date(Date.now() + db.receitas.length), decidido_em: null,
        });
        return { rows: [] };
      }
      if (q.startsWith('SELECT * FROM cms_receitas ORDER BY')) {
        const rows = [...db.receitas].sort(
          (a, b) => (b.status === 'recebida') - (a.status === 'recebida') || b.criado_em - a.criado_em
        );
        return { rows };
      }
      if (q.startsWith('SELECT * FROM cms_receitas WHERE id = $1')) {
        const r = findReceita(params[0]);
        return { rows: r ? [r] : [] };
      }
      if (q.startsWith('SELECT id FROM cms_receitas WHERE id = $1')) {
        const r = findReceita(params[0]);
        return { rows: r ? [{ id: r.id }] : [] };
      }
      if (q.startsWith('INSERT INTO cms_posts')) {
        const cols = /\(([^)]*)\) VALUES/.exec(q)[1].split(',').map((c) => c.trim());
        const row = { id: db.nextPost++ };
        cols.forEach((c, i) => { row[c] = params[i]; });
        db.posts.push(row);
        return { rows: [{ id: row.id }] };
      }
      if (q.startsWith('UPDATE cms_posts SET grupo_id = id WHERE id = $1')) {
        const p = db.posts.find((x) => x.id === params[0]);
        p.grupo_id = p.id;
        return { rows: [] };
      }
      if (q.startsWith("UPDATE cms_receitas SET status = 'publicada'")) {
        const r = findReceita(params[0]);
        r.status = 'publicada';
        r.decidido_em = new Date();
        r.post_grupo_id = params[1];
        return { rows: [] };
      }
      if (q.startsWith('UPDATE cms_receitas SET ponto_creditado_em')) {
        const r = findReceita(params[0]);
        if (!r.ponto_creditado_em) r.ponto_creditado_em = new Date();
        return { rows: [] };
      }
      if (q.startsWith("UPDATE cms_receitas SET status = 'recusada'")) {
        const r = findReceita(params[0]);
        if (!r || r.status !== 'recebida') return { rows: [] };
        r.status = 'recusada';
        r.decidido_em = new Date();
        return { rows: [{ id: r.id }] };
      }
      if (q.startsWith('SELECT r.id, r.nome')) {
        const r = findReceita(params[0]);
        if (!r) return { rows: [] };
        const post = db.posts.find((p) => p.id === r.post_grupo_id);
        return { rows: [{ ...r, post_slug: post ? post.slug : null }] };
      }
      if (q.startsWith('UPDATE cms_receitas SET telefone = NULL')) {
        const cutoff = new Date(params[0]);
        const hit = db.receitas.filter(
          (r) => r.telefone && ['publicada', 'recusada'].includes(r.status) && r.decidido_em && r.decidido_em <= cutoff
        );
        hit.forEach((r) => { r.telefone = null; });
        return { rows: hit.map((r) => ({ id: r.id })) };
      }
      throw new Error(`query não prevista no mock: ${q.slice(0, 80)}`);
    },
  };
  return pool;
}

function intakeForm(overrides = {}, { foto } = {}) {
  const fields = {
    nome: 'Ana Silva',
    cidade: 'São Paulo',
    telefone: TEL_INPUT,
    instagram: '@ana.padeira',
    titulo: 'Pão da vovó',
    historia: 'Aprendi com minha avó numa cozinha pequena e cheirosa.',
    ingredientes: 'farinha, água, sal, fermento',
    preparo: 'Misture tudo, deixe descansar e asse bem quente.',
    consentimento: 'true',
    idioma: 'pt',
    site: '',
    ...overrides,
  };
  const form = new FormData();
  for (const [k, v] of Object.entries(fields)) if (v !== undefined) form.append(k, v);
  if (foto) form.append('foto', new Blob([foto.buffer], { type: foto.type }), foto.name || 'foto.jpg');
  return form;
}

describe('BLOG-025 — receitas (Hub)', () => {
  let pool;
  let server;
  let base;
  let calls;
  let consoleLines;
  const realConsole = { log: console.log, warn: console.warn, error: console.error };

  function startServer(opts = {}) {
    const app = express();
    app.use(express.json());
    const requireAdmin = (req, res, next) =>
      req.get('x-test-admin') === '1' ? next() : res.status(401).json({ error: 'admin' });
    registerCmsReceitasRoutes(app, pool, requireAdmin, {
      getCliente: async (tel) => {
        calls.getCliente.push(tel);
        return { cliente: opts.cliente !== false, pontos: 3, total: 7 };
      },
      postCredito: async (tel, ref) => {
        calls.postCredito.push({ tel, ref });
        return { creditado: opts.creditar !== false, pontos: 1, total: 8 };
      },
      uploadCmsImage: async (buffer, mimetype, name) => {
        calls.upload.push({ buffer, mimetype, name });
        return { publicUrl: 'https://cdn.exemplo.test/cms/receita-1.jpg' };
      },
      converseJson: async (prompt) => {
        calls.bedrock.push(prompt);
        if (opts.bedrockFalha) throw new Error('bedrock fora do ar');
        return REVISAO_BEDROCK;
      },
      notifyPurge: async () => { calls.purge += 1; },
    });
    return new Promise((resolve) => {
      server = http.createServer(app).listen(0, '127.0.0.1', () => {
        base = `http://127.0.0.1:${server.address().port}`;
        resolve();
      });
    });
  }

  const stopServer = () => new Promise((resolve) => (server ? server.close(resolve) : resolve()));

  const intake = (form, headers = { 'x-lepain-key': KEY, 'x-forwarded-for': '203.0.113.9' }) =>
    fetch(`${base}/api/cms/receitas/intake`, { method: 'POST', headers, body: form });
  const admin = (path, init = {}) =>
    fetch(`${base}${path}`, { ...init, headers: { 'x-test-admin': '1', 'content-type': 'application/json', ...(init.headers || {}) } });

  beforeEach(async () => {
    await stopServer();
    pool = createFakePool();
    calls = { getCliente: [], postCredito: [], upload: [], bedrock: [], purge: 0 };
    consoleLines = [];
    resetReceitasRateLimit();
    for (const k of ['log', 'warn', 'error']) {
      console[k] = (...args) => consoleLines.push(args.map(String).join(' '));
    }
    await startServer();
  });

  // restaura console para o runner imprimir normalmente (mesmo se um assert falhar antes)
  const restoreConsole = () => Object.assign(console, realConsole);
  afterEach(restoreConsole);

  after(async () => {
    restoreConsole();
    await stopServer();
  });

  describe('validação', () => {
    it('normaliza telefone e rejeita lixo', () => {
      assert.equal(normalizeTelefone(TEL_INPUT), TEL);
      assert.equal(normalizeTelefone('5511987654321'), TEL);
      assert.equal(normalizeTelefone('123'), null);
      assert.equal(maskTelefone(TEL), '***4321');
    });

    it('aponta campos inválidos e exige consentimento', () => {
      const ruim = validateIntake({ nome: 'A', consentimento: 'false' });
      assert.match(ruim.error, /campos inválidos/);
      for (const c of ['nome', 'cidade', 'telefone', 'titulo', 'historia', 'ingredientes', 'preparo', 'consentimento']) {
        assert.ok(ruim.campos.includes(c), `faltou ${c}`);
      }
      const ok = validateIntake(Object.fromEntries(intakeForm().entries()));
      assert.equal(ok.error, undefined);
      assert.equal(ok.value.telefone, TEL);
      assert.equal(ok.value.instagram, 'ana.padeira');
      assert.equal(ok.value.idioma, 'pt');
      assert.ok(validateIntake({ ...ok.value, consentimento: 'true', instagram: 'com espaço' }).campos.includes('instagram'));
    });

    it('wa.me: só dígitos e texto codificado', () => {
      const url = buildWhatsappUrl('+55 (11) 98765-4321', 'Oi, tudo bem? & mais');
      assert.equal(url, 'https://wa.me/5511987654321?text=Oi%2C%20tudo%20bem%3F%20%26%20mais');
    });

    it('strip de EXIF em JPEG mantém imagem', () => {
      const original = jpegComExif();
      assert.ok(original.includes('GPS-SECRETO'));
      const limpo = stripJpegMetadata(original);
      assert.ok(!limpo.includes('GPS-SECRETO'));
      assert.ok(limpo.includes('PIXELS'));
      assert.equal(limpo[0], 0xff);
      assert.equal(limpo[1], 0xd8);
    });
  });

  describe('intake', () => {
    it('exige X-LePain-Key', async () => {
      const res = await intake(intakeForm(), {});
      restoreConsole();
      assert.equal(res.status, 401);
      assert.equal(pool.db.receitas.length, 0);
    });

    it('honeypot preenchido: responde ok mas não grava, não chama Bedrock/Loja', async () => {
      const res = await intake(intakeForm({ site: 'http://spam.test' }));
      restoreConsole();
      assert.equal(res.status, 201);
      assert.deepEqual(await res.json(), { ok: true, cliente_loja: false });
      assert.equal(pool.db.receitas.length, 0);
      assert.equal(calls.bedrock.length, 0);
      assert.equal(calls.getCliente.length, 0);
    });

    it('campos inválidos viram 400 com a lista', async () => {
      const res = await intake(intakeForm({ titulo: '', consentimento: 'false' }));
      restoreConsole();
      assert.equal(res.status, 400);
      const body = await res.json();
      assert.deepEqual(body.campos.sort(), ['consentimento', 'titulo']);
      assert.equal(pool.db.receitas.length, 0);
    });

    it('grava recebida, consulta cliente, revisa com Bedrock e nunca loga o telefone', async () => {
      const res = await intake(intakeForm());
      const lines = [...consoleLines];
      restoreConsole();
      assert.equal(res.status, 201);
      assert.deepEqual(await res.json(), { ok: true, cliente_loja: true });
      assert.equal(pool.db.receitas.length, 1);
      const r = pool.db.receitas[0];
      assert.equal(r.status, 'recebida');
      assert.equal(r.telefone, TEL);
      assert.equal(r.cliente_loja, true);
      assert.equal(r.instagram, 'ana.padeira');
      assert.equal(r.revisao.en.titulo, 'Grandma loaf');
      assert.deepEqual(r.revisao.correcoes_pt, ['"farinha" estava sem acento']);
      assert.deepEqual(calls.getCliente, [TEL]);
      assert.equal(calls.bedrock.length, 1);
      assert.ok(!calls.bedrock[0].includes(TEL), 'telefone não vai para o prompt');
      assert.ok(!lines.join('\n').includes('987654321'), 'telefone no log');
    });

    it('cliente_loja=false quando a Loja não conhece o telefone', async () => {
      await stopServer();
      await startServer({ cliente: false });
      const res = await intake(intakeForm());
      restoreConsole();
      assert.deepEqual(await res.json(), { ok: true, cliente_loja: false });
    });

    it('foto jpeg: sobe sem EXIF e guarda a URL', async () => {
      const res = await intake(intakeForm({}, { foto: { buffer: jpegComExif(), type: 'image/jpeg' } }));
      restoreConsole();
      assert.equal(res.status, 201);
      assert.equal(calls.upload.length, 1);
      assert.equal(calls.upload[0].mimetype, 'image/jpeg');
      assert.ok(!calls.upload[0].buffer.includes('GPS-SECRETO'));
      assert.equal(pool.db.receitas[0].foto_url, 'https://cdn.exemplo.test/cms/receita-1.jpg');
    });

    it('foto com tipo inválido (gif/texto disfarçado) é recusada', async () => {
      const res = await intake(
        intakeForm({}, { foto: { buffer: Buffer.from('GIF89a-nao-eh-jpeg-nem-png'), type: 'image/jpeg', name: 'x.jpg' } })
      );
      restoreConsole();
      assert.equal(res.status, 400);
      assert.deepEqual((await res.json()).campos, ['foto']);
      assert.equal(calls.upload.length, 0);
      assert.equal(pool.db.receitas.length, 0);
    });

    it('foto acima de 5 MB é recusada', async () => {
      const grande = Buffer.concat([jpegComExif(), Buffer.alloc(5 * 1024 * 1024 + 10)]);
      const res = await intake(intakeForm({}, { foto: { buffer: grande, type: 'image/jpeg' } }));
      restoreConsole();
      assert.equal(res.status, 400);
      assert.match((await res.json()).error, /5 MB/);
      assert.equal(calls.upload.length, 0);
    });

    it('Bedrock fora do ar: receita entra mesmo assim, marcada como sem revisão', async () => {
      await stopServer();
      await startServer({ bedrockFalha: true });
      const res = await intake(intakeForm());
      restoreConsole();
      assert.equal(res.status, 201);
      assert.equal(pool.db.receitas[0].revisao.indisponivel, true);
    });

    it(`rate limit: ${INTAKE_DAILY_LIMIT} por dia por visitante (hash do IP)`, async () => {
      for (let i = 0; i < INTAKE_DAILY_LIMIT; i += 1) {
        assert.equal((await intake(intakeForm())).status, 201);
      }
      const bloqueada = await intake(intakeForm());
      assert.equal(bloqueada.status, 429);
      // outro visitante segue livre
      const outro = await intake(intakeForm(), { 'x-lepain-key': KEY, 'x-forwarded-for': '198.51.100.7' });
      restoreConsole();
      assert.equal(outro.status, 201);
      assert.equal(pool.db.receitas.length, INTAKE_DAILY_LIMIT + 1);
    });
  });

  describe('admin', () => {
    async function semear(overrides = {}) {
      const res = await intake(intakeForm(overrides, { foto: { buffer: jpegComExif(), type: 'image/jpeg' } }));
      assert.equal(res.status, 201);
      return pool.db.receitas[pool.db.receitas.length - 1].id;
    }

    it('rotas admin exigem autenticação', async () => {
      const semAuth = await fetch(`${base}/api/cms/receitas`);
      const semAuth2 = await fetch(`${base}/api/cms/receitas/1/publicar`, { method: 'POST' });
      restoreConsole();
      assert.equal(semAuth.status, 401);
      assert.equal(semAuth2.status, 401);
    });

    it('lista recebida primeiro e nunca devolve o telefone cru', async () => {
      const a = await semear({ titulo: 'Primeira receita' });
      const b = await semear({ titulo: 'Segunda receita' });
      pool.db.receitas.find((r) => r.id === a).status = 'recusada';
      const res = await admin('/api/cms/receitas');
      restoreConsole();
      const { receitas } = await res.json();
      assert.deepEqual(receitas.map((r) => r.id), [b, a]);
      assert.equal(receitas[0].telefone_mascarado, '***4321');
      assert.ok(!JSON.stringify(receitas).includes('987654321'));
      const one = await (await admin(`/api/cms/receitas/${b}`)).json();
      assert.equal(one.titulo, 'Segunda receita');
      assert.equal((await admin('/api/cms/receitas/999')).status, 404);
    });

    it('publicar cria o par PT/EN secao=receita e o par Right Now, credita e avisa o blog', async () => {
      const id = await semear();
      const res = await admin(`/api/cms/receitas/${id}/publicar`, { method: 'POST', body: '{}' });
      restoreConsole();
      assert.equal(res.status, 200);
      const body = await res.json();
      assert.equal(body.ok, true);
      assert.equal(body.credito.creditado, true);

      const posts = pool.db.posts;
      assert.equal(posts.length, 4);
      const [pt, en, rnPt, rnEn] = posts;
      assert.equal(pt.secao, 'receita');
      assert.equal(pt.idioma, 'pt');
      assert.equal(pt.status, 'publicado');
      assert.equal(pt.sistema_destino, 'lepain');
      assert.equal(pt.titulo, 'Pão da vovó');
      assert.equal(pt.autor_nome, 'Ana Silva');
      assert.equal(pt.autor_cidade, 'São Paulo');
      assert.equal(pt.autor_instagram, 'ana.padeira');
      assert.equal(pt.ingredientes, 'farinha, água, sal, fermento');
      assert.equal(pt.preparo, 'Misture tudo, deixe descansar e asse bem quente.');
      assert.equal(pt.imagem_capa, 'https://cdn.exemplo.test/cms/receita-1.jpg');
      assert.equal(pt.grupo_id, pt.id);
      assert.equal(en.idioma, 'en');
      assert.equal(en.grupo_id, pt.id);
      assert.equal(en.titulo, 'Grandma loaf');
      assert.equal(en.dica, 'Use a hot oven');
      assert.equal(en.tempo, '3h');
      assert.equal(en.rendimento, '2 loaves');
      assert.equal(en.nivel, 'easy');
      assert.equal(en.slug, `${pt.slug}-en`);

      assert.equal(rnPt.secao, 'right_now');
      assert.equal(rnPt.right_now_tipo, 'receita');
      assert.equal(rnPt.link_url, `https://lepain.lojadepaes.com.br/pt/receitas/${pt.slug}`);
      assert.equal(rnEn.right_now_tipo, 'receita');
      assert.equal(rnEn.grupo_id, rnPt.id);
      assert.equal(rnEn.link_url, `https://lepain.lojadepaes.com.br/en/receitas/${en.slug}`);
      assert.ok([...rnPt.titulo].length <= 70 && [...rnEn.titulo].length <= 70);

      const r = pool.db.receitas[0];
      assert.equal(r.status, 'publicada');
      assert.ok(r.decidido_em);
      assert.ok(r.ponto_creditado_em);
      assert.equal(r.post_grupo_id, pt.id);
      assert.deepEqual(calls.postCredito, [{ tel: TEL, ref: `lepain-receita-${id}` }]);
      assert.equal(calls.purge, 1);
    });

    it('publicar duas vezes não duplica posts nem crédito', async () => {
      const id = await semear();
      const first = await admin(`/api/cms/receitas/${id}/publicar`, { method: 'POST', body: '{}' });
      const second = await admin(`/api/cms/receitas/${id}/publicar`, { method: 'POST', body: '{}' });
      restoreConsole();
      assert.equal(first.status, 200);
      assert.equal(second.status, 200);
      assert.equal((await second.json()).ja_publicada, true);
      assert.equal(pool.db.posts.length, 4);
      assert.equal(calls.postCredito.length, 1);
      assert.equal(calls.purge, 1);
    });

    it('crédito que falhou é retentado na repetição, sem recriar posts', async () => {
      await stopServer();
      await startServer({ creditar: false });
      const id = await semear();
      await admin(`/api/cms/receitas/${id}/publicar`, { method: 'POST', body: '{}' });
      assert.equal(pool.db.receitas[0].ponto_creditado_em, null);
      await admin(`/api/cms/receitas/${id}/publicar`, { method: 'POST', body: '{}' });
      restoreConsole();
      assert.equal(calls.postCredito.length, 2);
      assert.equal(calls.postCredito[0].ref, calls.postCredito[1].ref);
      assert.equal(pool.db.posts.length, 4);
    });

    it('não credita quem não é cliente da Loja', async () => {
      await stopServer();
      await startServer({ cliente: false });
      const id = await semear();
      const res = await admin(`/api/cms/receitas/${id}/publicar`, { method: 'POST', body: '{}' });
      restoreConsole();
      assert.equal(res.status, 200);
      assert.equal(calls.postCredito.length, 0);
      assert.equal(pool.db.receitas[0].ponto_creditado_em, null);
    });

    it('admin pode ajustar PT/EN no corpo; EN ausente bloqueia a publicação', async () => {
      await stopServer();
      await startServer({ bedrockFalha: true });
      const id = await semear();
      const incompleto = await admin(`/api/cms/receitas/${id}/publicar`, { method: 'POST', body: '{}' });
      assert.equal(incompleto.status, 400);
      assert.match((await incompleto.json()).error, /en\.titulo/);
      assert.equal(pool.db.posts.length, 0);
      assert.equal(pool.db.receitas[0].status, 'recebida');

      const ok = await admin(`/api/cms/receitas/${id}/publicar`, {
        method: 'POST',
        body: JSON.stringify({
          pt: { titulo: 'Pão da Vovó (revisado)' },
          en: { titulo: 'Grandma bread', historia: 'Story in English, long enough.', ingredientes: 'flour', preparo: 'bake it' },
        }),
      });
      restoreConsole();
      assert.equal(ok.status, 200);
      assert.equal(pool.db.posts[0].titulo, 'Pão da Vovó (revisado)');
      assert.equal(pool.db.posts[1].titulo, 'Grandma bread');
    });

    it('recusar marca recusada com decidido_em e não permite decidir de novo', async () => {
      const id = await semear();
      const res = await admin(`/api/cms/receitas/${id}/recusar`, { method: 'POST', body: '{}' });
      assert.equal(res.status, 200);
      const r = pool.db.receitas[0];
      assert.equal(r.status, 'recusada');
      assert.ok(r.decidido_em);
      assert.equal((await admin(`/api/cms/receitas/${id}/recusar`, { method: 'POST', body: '{}' })).status, 409);
      assert.equal((await admin(`/api/cms/receitas/${id}/publicar`, { method: 'POST', body: '{}' })).status, 409);
      assert.equal((await admin('/api/cms/receitas/999/recusar', { method: 'POST', body: '{}' })).status, 404);
      restoreConsole();
      assert.equal(pool.db.posts.length, 0);
      assert.equal(calls.postCredito.length, 0);
    });

    it('whatsapp: devolve wa.me com texto e não loga o telefone', async () => {
      const id = await semear();
      const ajuste = await admin(`/api/cms/receitas/${id}/whatsapp?tipo=ajuste`);
      const { url } = await ajuste.json();
      assert.match(url, /^https:\/\/wa\.me\/5511987654321\?text=.+/);
      const texto = decodeURIComponent(url.split('?text=')[1]);
      assert.match(texto, /Ana/);
      assert.match(texto, /Pão da vovó/);
      assert.match(texto, /farinha/); // correção sugerida pelo Bedrock

      await admin(`/api/cms/receitas/${id}/publicar`, { method: 'POST', body: '{}' });
      const pub = await (await admin(`/api/cms/receitas/${id}/whatsapp?tipo=publicou`)).json();
      const txt = decodeURIComponent(pub.url.split('?text=')[1]);
      assert.match(txt, /https:\/\/lepain\.lojadepaes\.com\.br\/pt\/receitas\/pao-da-vovo-\d+/);

      assert.equal((await admin(`/api/cms/receitas/${id}/whatsapp?tipo=outro`)).status, 400);
      assert.equal((await admin('/api/cms/receitas/999/whatsapp?tipo=ajuste')).status, 404);
      const lines = [...consoleLines];
      restoreConsole();
      assert.ok(!lines.join('\n').includes('987654321'));
    });

    it('whatsapp depois do purge responde 410', async () => {
      const id = await semear();
      pool.db.receitas[0].telefone = null;
      const res = await admin(`/api/cms/receitas/${id}/whatsapp?tipo=ajuste`);
      restoreConsole();
      assert.equal(res.status, 410);
    });
  });

  describe('purgeTelefonesDecididos', () => {
    it('apaga o telefone 30 dias depois da decisão e só de decididas', async () => {
      restoreConsole();
      const now = new Date('2026-08-31T12:00:00Z');
      const dia = 24 * 60 * 60 * 1000;
      const base0 = { telefone: TEL, instagram: null };
      pool.db.receitas.push(
        { id: 1, ...base0, status: 'publicada', decidido_em: new Date(now - 31 * dia) },
        { id: 2, ...base0, status: 'recusada', decidido_em: new Date(now - 30 * dia) },
        { id: 3, ...base0, status: 'publicada', decidido_em: new Date(now - 10 * dia) },
        { id: 4, ...base0, status: 'recebida', decidido_em: null }
      );
      const n = await purgeTelefonesDecididos(pool, now);
      assert.equal(n, 2);
      assert.deepEqual(pool.db.receitas.map((r) => r.telefone), [null, null, TEL, TEL]);
      const sql = pool.db.log[pool.db.log.length - 1];
      assert.equal(sql.params[0], new Date(now - 30 * dia).toISOString());
    });
  });
});
