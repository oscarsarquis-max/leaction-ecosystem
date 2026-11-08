'use strict';

const { createRequireAdminAuth } = require('../admin/auth');

const DESTINOS = new Set([
  'hub-publico',
  'actionhub',
  'inove4us',
  'paneldx',
  'todos',
  'lepain',
]);
const STATUSES = new Set(['rascunho', 'publicado']);
const SECOES = new Set(['insights', 'right_now']);
const IDIOMAS = new Set(['pt', 'en']);
const SENTIDOS = new Set(['olhar', 'toque', 'aroma', 'sabor', 'som', 'memoria']);
const RIGHT_NOW_TIPOS = new Set(['promocao', 'evento', 'noticia']);
const LEPAIN_KEYS = [
  'secao',
  'idioma',
  'grupo_id',
  'sentidos',
  'resumo_instagram',
  'right_now_tipo',
  'data_evento',
  'valido_ate',
];

const POST_COLUMNS = `id, slug, titulo, resumo, conteudo_html, imagem_capa,
                sistema_destino, status, publicado_em, criado_em,
                secao, idioma, grupo_id, sentidos, resumo_instagram,
                right_now_tipo, data_evento, valido_ate, atualizado_em`;

const PUBLIC_CACHE = 'public, max-age=60';

function slugify(input) {
  return String(input || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 240);
}

function dateOnly(value) {
  if (value == null || value === '') return null;
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const y = value.getFullYear();
    const m = String(value.getMonth() + 1).padStart(2, '0');
    const d = String(value.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(String(value).trim());
  return match ? match[1] : null;
}

function serializePost(row) {
  if (!row) return null;
  return {
    id: row.id,
    slug: row.slug,
    titulo: row.titulo,
    resumo: row.resumo,
    conteudo_html: row.conteudo_html,
    imagem_capa: row.imagem_capa,
    sistema_destino: row.sistema_destino,
    status: row.status,
    publicado_em: row.publicado_em,
    criado_em: row.criado_em,
    secao: row.secao ?? null,
    idioma: row.idioma ?? null,
    grupo_id: row.grupo_id ?? null,
    sentidos: Array.isArray(row.sentidos) ? row.sentidos : row.sentidos ?? null,
    resumo_instagram: row.resumo_instagram ?? null,
    right_now_tipo: row.right_now_tipo ?? null,
    data_evento: dateOnly(row.data_evento),
    valido_ate: dateOnly(row.valido_ate),
    atualizado_em: row.atualizado_em ?? null,
  };
}

function blankToNull(value) {
  if (value == null) return null;
  const text = String(value).trim();
  return text ? text.toLowerCase() : null;
}

function parseDate(value) {
  if (value == null || value === '') return null;
  if (value instanceof Date && !Number.isNaN(value.getTime())) return dateOnly(value);
  const text = String(value).trim();
  if (!text) return null;
  const match = /^(\d{4}-\d{2}-\d{2})$/.exec(text);
  return match ? match[1] : text;
}

function parseSentidos(value) {
  if (value == null || value === '') return null;
  if (!Array.isArray(value)) return value;
  const out = [];
  for (const item of value) {
    const key = String(item || '').trim().toLowerCase();
    if (!key || out.includes(key)) continue;
    out.push(key);
  }
  return out;
}

function parseGrupoId(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'number') return Number.isInteger(value) ? value : value;
  const text = String(value).trim();
  if (!/^\d+$/.test(text)) return text;
  return Number(text);
}

function parseBody(body = {}) {
  const titulo = String(body.titulo || '').trim();
  let slug = String(body.slug || '').trim();
  if (!slug && titulo) slug = slugify(titulo);
  const resumo = body.resumo != null ? String(body.resumo) : null;
  const conteudo_html = body.conteudo_html != null ? String(body.conteudo_html) : null;
  const imagem_capa = body.imagem_capa != null ? String(body.imagem_capa).trim() || null : null;
  const sistema_destino = String(body.sistema_destino || 'todos').trim().toLowerCase();
  const status = String(body.status || 'rascunho').trim().toLowerCase();
  const secao = blankToNull(body.secao);
  const idioma = blankToNull(body.idioma);
  const grupo_id = parseGrupoId(body.grupo_id);
  const sentidos = parseSentidos(body.sentidos);
  const resumo_instagram =
    body.resumo_instagram != null ? String(body.resumo_instagram) : null;
  const right_now_tipo = blankToNull(body.right_now_tipo);
  const data_evento = parseDate(body.data_evento);
  const valido_ate = parseDate(body.valido_ate);
  return {
    titulo,
    slug,
    resumo,
    conteudo_html,
    imagem_capa,
    sistema_destino,
    status,
    secao,
    idioma,
    grupo_id,
    sentidos,
    resumo_instagram: resumo_instagram != null && resumo_instagram.trim() ? resumo_instagram : null,
    right_now_tipo,
    data_evento,
    valido_ate,
  };
}

function lepainValuePresent(value) {
  if (value == null || value === '') return false;
  if (Array.isArray(value) && value.length === 0) return false;
  return true;
}

function foreignLepainError(raw) {
  if (!raw || typeof raw !== 'object') return null;
  for (const key of LEPAIN_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(raw, key)) continue;
    if (lepainValuePresent(raw[key])) {
      return 'campos do LePain não se aplicam a este destino';
    }
  }
  return null;
}

function validateLepain(payload) {
  if (!SECOES.has(payload.secao)) {
    return 'secao é obrigatória (insights ou right_now)';
  }
  if (!IDIOMAS.has(payload.idioma)) {
    return 'idioma é obrigatório (pt ou en)';
  }
  if (!Array.isArray(payload.sentidos) || payload.sentidos.length < 1) {
    return 'sentidos é obrigatório (ao menos um)';
  }
  for (const sentido of payload.sentidos) {
    if (!SENTIDOS.has(sentido)) {
      return `sentido inválido (use: ${[...SENTIDOS].join(', ')})`;
    }
  }
  if (payload.secao === 'right_now' && !RIGHT_NOW_TIPOS.has(payload.right_now_tipo)) {
    return 'right_now_tipo é obrigatório (promocao, evento ou noticia)';
  }
  for (const key of ['data_evento', 'valido_ate']) {
    const value = payload[key];
    if (value != null && !/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
      return `${key} inválida (use AAAA-MM-DD)`;
    }
  }
  if (payload.idioma === 'en') {
    if (!Number.isInteger(payload.grupo_id) || payload.grupo_id < 1) {
      return 'grupo_id é obrigatório na versão EN (post LePain em PT)';
    }
  }
  return null;
}

function validatePayload(payload, { raw = null } = {}) {
  if (!payload.titulo) return 'titulo é obrigatório';
  if (!payload.slug) return 'slug é obrigatório';
  if (payload.sistema_destino && !DESTINOS.has(payload.sistema_destino)) {
    return `sistema_destino inválido (use: ${[...DESTINOS].join(', ')})`;
  }
  if (payload.status && !STATUSES.has(payload.status)) {
    return `status inválido (use: ${[...STATUSES].join(', ')})`;
  }
  if (payload.sistema_destino !== 'lepain') {
    return foreignLepainError(raw);
  }
  return validateLepain(payload);
}

function lepainColumns(payload, selfId) {
  if (payload.sistema_destino !== 'lepain') {
    return {
      secao: null,
      idioma: null,
      grupo_id: null,
      sentidos: null,
      resumo_instagram: null,
      right_now_tipo: null,
      data_evento: null,
      valido_ate: null,
    };
  }
  const rightNow = payload.secao === 'right_now';
  return {
    secao: payload.secao,
    idioma: payload.idioma,
    grupo_id: payload.idioma === 'pt' ? selfId || null : payload.grupo_id,
    sentidos: payload.sentidos,
    resumo_instagram: payload.resumo_instagram,
    right_now_tipo: rightNow ? payload.right_now_tipo : null,
    data_evento: rightNow ? payload.data_evento : null,
    valido_ate: rightNow ? payload.valido_ate : null,
  };
}

function buildPublicPostsQuery({ sistema, secao, idioma, limit, offset }) {
  const params = [];
  let where = `status = 'publicado'`;
  if (sistema) {
    params.push(sistema);
    where += ` AND (sistema_destino = $${params.length} OR sistema_destino = 'todos')`;
  }
  if (secao) {
    params.push(secao);
    where += ` AND secao = $${params.length}`;
  }
  if (idioma) {
    params.push(idioma);
    where += ` AND idioma = $${params.length}`;
  }
  params.push(limit);
  const limitIdx = params.length;
  params.push(offset);
  const offsetIdx = params.length;
  const sql = `SELECT ${POST_COLUMNS}
         FROM cms_posts
         WHERE ${where}
         ORDER BY publicado_em DESC NULLS LAST, criado_em DESC
         LIMIT $${limitIdx} OFFSET $${offsetIdx}`;
  return { sql, params };
}

function parseOffset(raw) {
  if (raw == null || raw === '') return { offset: 0 };
  const text = String(raw).trim();
  if (!/^\d+$/.test(text)) return { error: 'offset inválido' };
  return { offset: Number(text) };
}

function parsePublicFilter(raw, allowed, name) {
  const value = String(raw || '').trim().toLowerCase();
  if (!value) return { value: null };
  if (!allowed.has(value)) return { error: `${name} inválido` };
  return { value };
}

function conflictMessage(err) {
  if (!err || err.code !== '23505') return null;
  if (err.constraint === 'uq_cms_posts_grupo_idioma') {
    return 'já existe uma versão EN deste grupo';
  }
  return 'slug já existe';
}

async function assertEnGroup(pool, grupoId, selfId) {
  const parent = await pool.query(
    `SELECT id FROM cms_posts
      WHERE id = $1 AND sistema_destino = 'lepain' AND idioma = 'pt'`,
    [grupoId]
  );
  if (!parent.rows[0]) {
    return 'grupo_id precisa ser um post LePain em PT';
  }
  const sibling = await pool.query(
    `SELECT id FROM cms_posts
      WHERE grupo_id = $1 AND idioma = 'en' AND id <> $2
      LIMIT 1`,
    [grupoId, selfId || 0]
  );
  if (sibling.rows[0]) return 'já existe uma versão EN deste grupo';
  return null;
}

/**
 * Headless CMS — Action Hub como provedor.
 * Admin: GET /api/cms/posts/admin/:id, POST/PUT/DELETE /api/cms/posts
 * Público: GET /api/cms/posts?sistema_destino=&limit=&offset=&secao=&idioma=
 *          GET /api/cms/posts/:slug
 *
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ jwtSecret?: string }} [options]
 */
function registerCmsPostsRoutes(app, pool, options = {}) {
  const requireAdmin = createRequireAdminAuth(options.jwtSecret || process.env.JWT_SECRET);

  app.get('/api/cms/posts', async (req, res) => {
    try {
      const sistema = String(req.query.sistema_destino || '').trim().toLowerCase();
      let limit = parseInt(String(req.query.limit || '20'), 10);
      if (!Number.isFinite(limit) || limit < 1) limit = 20;
      if (limit > 100) limit = 100;

      const offsetParsed = parseOffset(req.query.offset);
      if (offsetParsed.error) return res.status(400).json({ error: offsetParsed.error });
      const secaoParsed = parsePublicFilter(req.query.secao, SECOES, 'secao');
      if (secaoParsed.error) return res.status(400).json({ error: secaoParsed.error });
      const idiomaParsed = parsePublicFilter(req.query.idioma, IDIOMAS, 'idioma');
      if (idiomaParsed.error) return res.status(400).json({ error: idiomaParsed.error });

      const query = buildPublicPostsQuery({
        sistema,
        secao: secaoParsed.value,
        idioma: idiomaParsed.value,
        limit,
        offset: offsetParsed.offset,
      });
      const result = await pool.query(query.sql, query.params);
      res.set('Cache-Control', PUBLIC_CACHE);
      return res.status(200).json({
        posts: result.rows.map(serializePost),
        count: result.rows.length,
      });
    } catch (err) {
      console.error('[cms] GET /api/cms/posts', err.message);
      return res.status(500).json({ error: 'Falha ao listar posts publicados' });
    }
  });

  app.get('/api/cms/posts/admin', requireAdmin, async (_req, res) => {
    try {
      const result = await pool.query(
        `SELECT ${POST_COLUMNS}
         FROM cms_posts
         ORDER BY criado_em DESC
         LIMIT 500`
      );
      return res.status(200).json({ posts: result.rows.map(serializePost) });
    } catch (err) {
      console.error('[cms] GET /api/cms/posts/admin', err.message);
      return res.status(500).json({ error: 'Falha ao listar posts' });
    }
  });

  app.get('/api/cms/posts/admin/:id', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) return res.status(400).json({ error: 'id inválido' });
      const result = await pool.query(
        `SELECT ${POST_COLUMNS}
         FROM cms_posts
         WHERE id = $1`,
        [id]
      );
      if (!result.rows[0]) return res.status(404).json({ error: 'Post não encontrado' });
      return res.status(200).json({ post: serializePost(result.rows[0]) });
    } catch (err) {
      console.error('[cms] GET /api/cms/posts/admin/:id', err.message);
      return res.status(500).json({ error: 'Falha ao ler post' });
    }
  });

  app.get('/api/cms/posts/:slug', async (req, res) => {
    try {
      const slug = String(req.params.slug || '').trim();
      if (!slug) return res.status(404).json({ error: 'Post não encontrado' });
      const result = await pool.query(
        `SELECT ${POST_COLUMNS}
         FROM cms_posts
         WHERE slug = $1 AND status = 'publicado'
         LIMIT 1`,
        [slug]
      );
      if (!result.rows[0]) return res.status(404).json({ error: 'Post não encontrado' });
      res.set('Cache-Control', PUBLIC_CACHE);
      return res.status(200).json({ post: serializePost(result.rows[0]) });
    } catch (err) {
      console.error('[cms] GET /api/cms/posts/:slug', err.message);
      return res.status(500).json({ error: 'Falha ao ler post' });
    }
  });

  app.post('/api/cms/posts', requireAdmin, async (req, res) => {
    try {
      const raw = req.body || {};
      const payload = parseBody(raw);
      const errMsg = validatePayload(payload, { raw });
      if (errMsg) return res.status(400).json({ error: errMsg });

      if (payload.sistema_destino === 'lepain' && payload.idioma === 'en') {
        const groupErr = await assertEnGroup(pool, payload.grupo_id, 0);
        if (groupErr) {
          const status = groupErr.startsWith('já existe') ? 409 : 400;
          return res.status(status).json({ error: groupErr });
        }
      }

      const publicadoEm = payload.status === 'publicado' ? new Date().toISOString() : null;
      const cols = lepainColumns(payload, null);
      const result = await pool.query(
        `INSERT INTO cms_posts
          (slug, titulo, resumo, conteudo_html, imagem_capa, sistema_destino, status, publicado_em,
           secao, idioma, grupo_id, sentidos, resumo_instagram, right_now_tipo, data_evento, valido_ate)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
         RETURNING *`,
        [
          payload.slug,
          payload.titulo,
          payload.resumo,
          payload.conteudo_html,
          payload.imagem_capa,
          payload.sistema_destino,
          payload.status,
          publicadoEm,
          cols.secao,
          cols.idioma,
          cols.grupo_id,
          cols.sentidos,
          cols.resumo_instagram,
          cols.right_now_tipo,
          cols.data_evento,
          cols.valido_ate,
        ]
      );

      let row = result.rows[0];
      if (payload.sistema_destino === 'lepain' && payload.idioma === 'pt') {
        const linked = await pool.query(
          `UPDATE cms_posts SET grupo_id = id WHERE id = $1 RETURNING *`,
          [row.id]
        );
        row = linked.rows[0];
      }

      return res.status(201).json({ post: serializePost(row) });
    } catch (err) {
      const conflict = conflictMessage(err);
      if (conflict) return res.status(409).json({ error: conflict });
      console.error('[cms] POST /api/cms/posts', err.message);
      return res.status(500).json({ error: 'Falha ao criar post' });
    }
  });

  app.put('/api/cms/posts/:id', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) return res.status(400).json({ error: 'id inválido' });

      const existing = await pool.query(`SELECT * FROM cms_posts WHERE id = $1`, [id]);
      if (!existing.rows[0]) return res.status(404).json({ error: 'Post não encontrado' });

      const prev = existing.rows[0];
      const raw = req.body || {};
      const incoming = parseBody({ ...prev, ...raw });
      if (!String(raw.slug || '').trim()) incoming.slug = prev.slug;
      if (!String(raw.titulo || '').trim()) incoming.titulo = prev.titulo;

      const errMsg = validatePayload(incoming, { raw });
      if (errMsg) return res.status(400).json({ error: errMsg });

      if (incoming.sistema_destino === 'lepain' && incoming.idioma === 'en') {
        const groupErr = await assertEnGroup(pool, incoming.grupo_id, id);
        if (groupErr) {
          const status = groupErr.startsWith('já existe') ? 409 : 400;
          return res.status(status).json({ error: groupErr });
        }
      }

      let publicadoEm = prev.publicado_em;
      if (incoming.status === 'publicado' && prev.status !== 'publicado') {
        publicadoEm = new Date().toISOString();
      } else if (incoming.status === 'rascunho') {
        publicadoEm = prev.publicado_em;
      }

      const cols = lepainColumns(incoming, id);
      const result = await pool.query(
        `UPDATE cms_posts SET
            slug = $1,
            titulo = $2,
            resumo = $3,
            conteudo_html = $4,
            imagem_capa = $5,
            sistema_destino = $6,
            status = $7,
            publicado_em = $8,
            secao = $9,
            idioma = $10,
            grupo_id = $11,
            sentidos = $12,
            resumo_instagram = $13,
            right_now_tipo = $14,
            data_evento = $15,
            valido_ate = $16,
            atualizado_em = now()
         WHERE id = $17
         RETURNING *`,
        [
          incoming.slug,
          incoming.titulo,
          incoming.resumo,
          incoming.conteudo_html,
          incoming.imagem_capa,
          incoming.sistema_destino,
          incoming.status,
          publicadoEm,
          cols.secao,
          cols.idioma,
          cols.grupo_id,
          cols.sentidos,
          cols.resumo_instagram,
          cols.right_now_tipo,
          cols.data_evento,
          cols.valido_ate,
          id,
        ]
      );

      return res.status(200).json({ post: serializePost(result.rows[0]) });
    } catch (err) {
      const conflict = conflictMessage(err);
      if (conflict) return res.status(409).json({ error: conflict });
      console.error('[cms] PUT /api/cms/posts/:id', err.message);
      return res.status(500).json({ error: 'Falha ao atualizar post' });
    }
  });

  app.delete('/api/cms/posts/:id', requireAdmin, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) return res.status(400).json({ error: 'id inválido' });

      const existing = await pool.query(`SELECT * FROM cms_posts WHERE id = $1`, [id]);
      if (!existing.rows[0]) return res.status(404).json({ error: 'Post não encontrado' });

      const prev = existing.rows[0];
      const removePair = prev.sistema_destino === 'lepain' && prev.idioma === 'pt';
      const deleted = await pool.query(
        `DELETE FROM cms_posts
          WHERE id = $1
             OR ($2::boolean IS TRUE AND idioma = 'en' AND grupo_id = $1)
          RETURNING id`,
        [id, removePair]
      );
      return res.status(200).json({
        deleted: deleted.rows.map((row) => row.id),
      });
    } catch (err) {
      console.error('[cms] DELETE /api/cms/posts/:id', err.message);
      return res.status(500).json({ error: 'Falha ao excluir post' });
    }
  });

  console.log('📰 [cms] rotas /api/cms/posts (GET público + GET/POST/PUT/DELETE admin) registradas');
}

module.exports = {
  registerCmsPostsRoutes,
  slugify,
  parseBody,
  validatePayload,
  buildPublicPostsQuery,
  serializePost,
};
