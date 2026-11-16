'use strict';

const crypto = require('crypto');

const WINDOW_MS = 60 * 1000;
const LIMIT = 30;
const hits = new Map();

function resetRateLimit() {
  hits.clear();
}

function keyOf() {
  return String(process.env.LEPAIN_CMS_KEY || '');
}

function keyMatches(req) {
  const expected = keyOf();
  const got = String(req.get('x-lepain-key') || '');
  if (!expected || !got) return false;
  const a = Buffer.from(expected);
  const b = Buffer.from(got);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

function socketIp(req) {
  return String(req.ip || req.socket?.remoteAddress || 'unknown');
}

function allow(ip) {
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((at) => now - at < WINDOW_MS);
  if (recent.length >= LIMIT) {
    hits.set(ip, recent);
    return false;
  }
  recent.push(now);
  hits.set(ip, recent);
  return true;
}

function guard(req, res) {
  const trusted = keyMatches(req);
  const forwarded = String(req.get('x-forwarded-for') || '')
    .split(',')[0]
    .trim();
  const ip = trusted && forwarded ? forwarded : socketIp(req);
  if (!allow(ip)) {
    res.status(429).json({ error: 'muitas requisições' });
    return false;
  }
  if (!trusted) {
    res.status(401).json({ error: 'não autorizado' });
    return false;
  }
  return true;
}

function visitanteOf(value) {
  const text = String(value || '').trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(text)) return null;
  return text;
}

function iso(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function parseStamp(value) {
  if (value == null || value === '') return { value: null, error: 'data obrigatória' };
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return { value: null, error: 'data inválida' };
  return { value: date.toISOString(), error: null };
}

function parseOpcoes(value) {
  if (!Array.isArray(value) || value.length < 2 || value.length > 4) {
    return { error: 'a enquete precisa de 2 a 4 opções' };
  }
  const opcoes = [];
  for (const item of value) {
    const pt = String(item?.pt || '').trim();
    const en = String(item?.en || '').trim();
    if (!pt || !en) return { error: 'cada opção precisa de texto em PT e EN' };
    const id = String(item?.id || '').trim() || `o${opcoes.length + 1}`;
    if (!/^[A-Za-z0-9_-]{1,32}$/.test(id)) return { error: 'id de opção inválido' };
    opcoes.push({ id, pt, en });
  }
  if (new Set(opcoes.map((item) => item.id)).size !== opcoes.length) {
    return { error: 'opções com id repetido' };
  }
  return { opcoes };
}

function resultadoDe(opcoes, rows) {
  const counts = new Map(rows.map((row) => [String(row.opcao_id), Number(row.n) || 0]));
  const total = [...counts.values()].reduce((sum, n) => sum + n, 0);
  const resultado = opcoes.map((opcao) => {
    const n = counts.get(opcao.id) || 0;
    return { id: opcao.id, pct: total ? Math.round((n * 100) / total) : 0 };
  });
  return { resultado, total };
}

async function contagem(pool, enqueteId) {
  const result = await pool.query(
    `SELECT opcao_id, count(*)::int AS n
       FROM cms_votos
      WHERE enquete_id = $1
      GROUP BY opcao_id`,
    [enqueteId]
  );
  return result.rows;
}

function shapeEnquete(row, vote, counts) {
  const opcoes = Array.isArray(row.opcoes) ? row.opcoes : [];
  const fecha = new Date(row.fecha_em);
  const closed = !Number.isNaN(fecha.getTime()) && fecha.getTime() <= Date.now();
  const voted = Boolean(vote);
  const body = {
    id: row.id,
    pergunta_pt: row.pergunta_pt,
    pergunta_en: row.pergunta_en,
    opcoes,
    fecha_em: iso(row.fecha_em),
    votou: voted,
  };
  if (voted || closed) {
    const tally = resultadoDe(opcoes, counts);
    body.resultado = tally.resultado;
    body.total = tally.total;
  }
  return body;
}

async function outraAberta(pool, selfId, abre, fecha) {
  const result = await pool.query(
    `SELECT id FROM cms_enquetes
      WHERE status = 'publicada'
        AND id <> $1
        AND abre_em < $3
        AND fecha_em > $2
      LIMIT 1`,
    [selfId || 0, abre, fecha]
  );
  return Boolean(result.rows[0]);
}

function parseEnquete(body) {
  const pergunta_pt = String(body.pergunta_pt || '').trim();
  const pergunta_en = String(body.pergunta_en || '').trim();
  if (!pergunta_pt || !pergunta_en) return { error: 'pergunta em PT e EN é obrigatória' };
  const parsed = parseOpcoes(body.opcoes);
  if (parsed.error) return parsed;
  const abre = parseStamp(body.abre_em);
  if (abre.error) return { error: `abre_em: ${abre.error}` };
  const fecha = parseStamp(body.fecha_em);
  if (fecha.error) return { error: `fecha_em: ${fecha.error}` };
  if (new Date(fecha.value) <= new Date(abre.value)) {
    return { error: 'fecha_em precisa ser depois de abre_em' };
  }
  const status = String(body.status || 'rascunho').trim().toLowerCase();
  if (status !== 'rascunho' && status !== 'publicada') {
    return { error: 'status inválido (rascunho ou publicada)' };
  }
  return {
    pergunta_pt,
    pergunta_en,
    opcoes: parsed.opcoes,
    abre_em: abre.value,
    fecha_em: fecha.value,
    status,
  };
}

/**
 * Rotas privadas do Right Now e o cadastro de enquetes.
 * A chave fica em LEPAIN_CMS_KEY. O blog manda o IP do visitante em X-Forwarded-For.
 *
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {(req: import('express').Request, res: import('express').Response, next: Function) => void} requireAdmin
 */
function registerCmsRightNowRoutes(app, pool, requireAdmin) {
  app.post('/api/cms/posts/:id/quero', async (req, res) => {
    if (!guard(req, res)) return;
    try {
      const id = parseInt(String(req.params.id), 10);
      const visitante = visitanteOf(req.body?.visitante);
      if (!Number.isFinite(id) || !visitante) {
        return res.status(400).json({ error: 'post e visitante são obrigatórios' });
      }
      const post = await pool.query(`SELECT id, status FROM cms_posts WHERE id = $1`, [id]);
      if (!post.rows[0] || post.rows[0].status !== 'publicado') {
        return res.status(404).json({ error: 'Post não encontrado' });
      }
      const inserted = await pool.query(
        `INSERT INTO cms_reacoes (post_id, visitante)
         VALUES ($1, $2)
         ON CONFLICT (post_id, visitante) DO NOTHING
         RETURNING id`,
        [id, visitante]
      );
      const count = await pool.query(
        `SELECT count(*)::int AS n FROM cms_reacoes WHERE post_id = $1`,
        [id]
      );
      return res.status(200).json({
        count: count.rows[0].n,
        novo: inserted.rows.length > 0,
      });
    } catch (err) {
      console.error('[cms] POST /api/cms/posts/:id/quero', err.message);
      return res.status(500).json({ error: 'Falha ao registrar reação' });
    }
  });

  app.get('/api/cms/enquetes/atual', async (req, res) => {
    if (!guard(req, res)) return;
    try {
      const visitante = visitanteOf(req.query.visitante);
      const open = await pool.query(
        `SELECT id, pergunta_pt, pergunta_en, opcoes, abre_em, fecha_em, status
           FROM cms_enquetes
          WHERE status = 'publicada'
            AND abre_em <= now()
            AND fecha_em > now()
          ORDER BY abre_em DESC
          LIMIT 1`
      );
      const row = open.rows[0];
      if (!row) return res.status(200).json(null);
      let vote = null;
      if (visitante) {
        const found = await pool.query(
          `SELECT id FROM cms_votos WHERE enquete_id = $1 AND visitante = $2`,
          [row.id, visitante]
        );
        vote = found.rows[0] || null;
      }
      const counts = vote || new Date(row.fecha_em).getTime() <= Date.now()
        ? await contagem(pool, row.id)
        : [];
      return res.status(200).json(shapeEnquete(row, vote, counts));
    } catch (err) {
      console.error('[cms] GET /api/cms/enquetes/atual', err.message);
      return res.status(500).json({ error: 'Falha ao ler a enquete' });
    }
  });

  app.post('/api/cms/enquetes/:id/votos', async (req, res) => {
    if (!guard(req, res)) return;
    try {
      const id = parseInt(String(req.params.id), 10);
      const visitante = visitanteOf(req.body?.visitante);
      const opcaoId = String(req.body?.opcao_id || '').trim();
      if (!Number.isFinite(id) || !visitante || !opcaoId) {
        return res.status(400).json({ error: 'enquete, opção e visitante são obrigatórios' });
      }
      const found = await pool.query(`SELECT * FROM cms_enquetes WHERE id = $1`, [id]);
      const row = found.rows[0];
      if (!row || row.status !== 'publicada') {
        return res.status(404).json({ error: 'Enquete não encontrada' });
      }
      const now = Date.now();
      if (new Date(row.fecha_em).getTime() <= now) {
        return res.status(410).json({ error: 'enquete fechada' });
      }
      if (new Date(row.abre_em).getTime() > now) {
        return res.status(404).json({ error: 'Enquete não encontrada' });
      }
      const opcoes = Array.isArray(row.opcoes) ? row.opcoes : [];
      if (!opcoes.some((item) => item.id === opcaoId)) {
        return res.status(400).json({ error: 'opção inválida' });
      }
      const inserted = await pool.query(
        `INSERT INTO cms_votos (enquete_id, opcao_id, visitante)
         VALUES ($1, $2, $3)
         ON CONFLICT (enquete_id, visitante) DO NOTHING
         RETURNING id`,
        [id, opcaoId, visitante]
      );
      if (!inserted.rows[0]) {
        return res.status(409).json({ error: 'voto já registrado' });
      }
      const tally = resultadoDe(opcoes, await contagem(pool, id));
      return res.status(200).json(tally);
    } catch (err) {
      console.error('[cms] POST /api/cms/enquetes/:id/votos', err.message);
      return res.status(500).json({ error: 'Falha ao registrar voto' });
    }
  });

  app.get('/api/cms/enquetes/admin', requireAdmin, async (_req, res) => {
    try {
      const result = await pool.query(
        `SELECT id, pergunta_pt, pergunta_en, opcoes, abre_em, fecha_em, status
           FROM cms_enquetes
          ORDER BY abre_em DESC, id DESC
          LIMIT 100`
      );
      const enquetes = [];
      for (const row of result.rows) {
        const tally = resultadoDe(
          Array.isArray(row.opcoes) ? row.opcoes : [],
          await contagem(pool, row.id)
        );
        enquetes.push({
          id: row.id,
          pergunta_pt: row.pergunta_pt,
          pergunta_en: row.pergunta_en,
          opcoes: row.opcoes,
          abre_em: iso(row.abre_em),
          fecha_em: iso(row.fecha_em),
          status: row.status,
          resultado: tally.resultado,
          total: tally.total,
        });
      }
      return res.status(200).json({ enquetes });
    } catch (err) {
      console.error('[cms] GET /api/cms/enquetes/admin', err.message);
      return res.status(500).json({ error: 'Falha ao listar enquetes' });
    }
  });

  app.post('/api/cms/enquetes', requireAdmin, async (req, res) => {
    try {
      const parsed = parseEnquete(req.body || {});
      if (parsed.error) return res.status(400).json({ error: parsed.error });
      if (
        parsed.status === 'publicada' &&
        (await outraAberta(pool, 0, parsed.abre_em, parsed.fecha_em))
      ) {
        return res.status(409).json({ error: 'já existe uma enquete aberta nesse período' });
      }
      const result = await pool.query(
        `INSERT INTO cms_enquetes
           (pergunta_pt, pergunta_en, opcoes, abre_em, fecha_em, status)
         VALUES ($1, $2, $3::jsonb, $4, $5, $6)
         RETURNING id`,
        [
          parsed.pergunta_pt,
          parsed.pergunta_en,
          JSON.stringify(parsed.opcoes),
          parsed.abre_em,
          parsed.fecha_em,
          parsed.status,
        ]
      );
      return res.status(201).json({ id: result.rows[0].id });
    } catch (err) {
      console.error('[cms] POST /api/cms/enquetes', err.message);
      return res.status(500).json({ error: 'Falha ao criar enquete' });
    }
  });

  app.put('/api/cms/enquetes/:id', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) return res.status(400).json({ error: 'id inválido' });
      const existing = await pool.query(`SELECT id FROM cms_enquetes WHERE id = $1`, [id]);
      if (!existing.rows[0]) return res.status(404).json({ error: 'Enquete não encontrada' });
      const parsed = parseEnquete(req.body || {});
      if (parsed.error) return res.status(400).json({ error: parsed.error });
      if (
        parsed.status === 'publicada' &&
        (await outraAberta(pool, id, parsed.abre_em, parsed.fecha_em))
      ) {
        return res.status(409).json({ error: 'já existe uma enquete aberta nesse período' });
      }
      await pool.query(
        `UPDATE cms_enquetes SET
            pergunta_pt = $1,
            pergunta_en = $2,
            opcoes = $3::jsonb,
            abre_em = $4,
            fecha_em = $5,
            status = $6
         WHERE id = $7`,
        [
          parsed.pergunta_pt,
          parsed.pergunta_en,
          JSON.stringify(parsed.opcoes),
          parsed.abre_em,
          parsed.fecha_em,
          parsed.status,
          id,
        ]
      );
      return res.status(200).json({ id });
    } catch (err) {
      console.error('[cms] PUT /api/cms/enquetes/:id', err.message);
      return res.status(500).json({ error: 'Falha ao atualizar enquete' });
    }
  });
}

module.exports = {
  registerCmsRightNowRoutes,
  resetRateLimit,
  resultadoDe,
};
