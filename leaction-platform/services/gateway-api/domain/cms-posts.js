'use strict';

const { createRequireAdminAuth } = require('../admin/auth');

const DESTINOS = new Set([
  'hub-publico',
  'actionhub',
  'inove4us',
  'paneldx',
  'todos',
]);
const STATUSES = new Set(['rascunho', 'publicado']);

function slugify(input) {
  return String(input || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 240);
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
  };
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
  return { titulo, slug, resumo, conteudo_html, imagem_capa, sistema_destino, status };
}

function validatePayload(payload, { partial = false } = {}) {
  if (!partial || payload.titulo !== undefined) {
    if (!payload.titulo) return 'titulo é obrigatório';
  }
  if (!partial || payload.slug !== undefined) {
    if (!payload.slug) return 'slug é obrigatório';
  }
  if (payload.sistema_destino && !DESTINOS.has(payload.sistema_destino)) {
    return `sistema_destino inválido (use: ${[...DESTINOS].join(', ')})`;
  }
  if (payload.status && !STATUSES.has(payload.status)) {
    return `status inválido (use: ${[...STATUSES].join(', ')})`;
  }
  return null;
}

/**
 * Headless CMS — Action Hub como provedor.
 * Admin: POST/PUT /api/cms/posts
 * Público: GET /api/cms/posts?sistema_destino=&limit=
 *
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ jwtSecret?: string }} [options]
 */
function registerCmsPostsRoutes(app, pool, options = {}) {
  const requireAdmin = createRequireAdminAuth(options.jwtSecret || process.env.JWT_SECRET);

  // —— Leitura pública (satélites) ——
  app.get('/api/cms/posts', async (req, res) => {
    try {
      const sistema = String(req.query.sistema_destino || '').trim().toLowerCase();
      let limit = parseInt(String(req.query.limit || '20'), 10);
      if (!Number.isFinite(limit) || limit < 1) limit = 20;
      if (limit > 100) limit = 100;

      const params = [];
      let where = `status = 'publicado'`;
      if (sistema) {
        params.push(sistema);
        where += ` AND (sistema_destino = $${params.length} OR sistema_destino = 'todos')`;
      }
      params.push(limit);

      const result = await pool.query(
        `SELECT id, slug, titulo, resumo, conteudo_html, imagem_capa,
                sistema_destino, status, publicado_em, criado_em
         FROM cms_posts
         WHERE ${where}
         ORDER BY publicado_em DESC NULLS LAST, criado_em DESC
         LIMIT $${params.length}`,
        params
      );

      return res.status(200).json({
        posts: result.rows.map(serializePost),
        count: result.rows.length,
      });
    } catch (err) {
      console.error('[cms] GET /api/cms/posts', err.message);
      return res.status(500).json({ error: 'Falha ao listar posts publicados' });
    }
  });

  // Admin: listagem completa (rascunhos + publicados)
  app.get('/api/cms/posts/admin', requireAdmin, async (_req, res) => {
    try {
      const result = await pool.query(
        `SELECT id, slug, titulo, resumo, conteudo_html, imagem_capa,
                sistema_destino, status, publicado_em, criado_em
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

  app.post('/api/cms/posts', requireAdmin, async (req, res) => {
    try {
      const payload = parseBody(req.body);
      const errMsg = validatePayload(payload);
      if (errMsg) return res.status(400).json({ error: errMsg });

      const publicadoEm =
        payload.status === 'publicado' ? new Date().toISOString() : null;

      const result = await pool.query(
        `INSERT INTO cms_posts
          (slug, titulo, resumo, conteudo_html, imagem_capa, sistema_destino, status, publicado_em)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
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
        ]
      );

      return res.status(201).json({ post: serializePost(result.rows[0]) });
    } catch (err) {
      if (err && err.code === '23505') {
        return res.status(409).json({ error: 'slug já existe' });
      }
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
      const incoming = parseBody({ ...prev, ...req.body });
      // Se slug veio vazio no body, mantém o anterior
      if (!String(req.body?.slug || '').trim()) incoming.slug = prev.slug;
      if (!String(req.body?.titulo || '').trim()) incoming.titulo = prev.titulo;

      const errMsg = validatePayload(incoming);
      if (errMsg) return res.status(400).json({ error: errMsg });

      let publicadoEm = prev.publicado_em;
      if (incoming.status === 'publicado' && prev.status !== 'publicado') {
        publicadoEm = new Date().toISOString();
      } else if (incoming.status === 'rascunho') {
        publicadoEm = prev.publicado_em;
      }

      const result = await pool.query(
        `UPDATE cms_posts SET
            slug = $1,
            titulo = $2,
            resumo = $3,
            conteudo_html = $4,
            imagem_capa = $5,
            sistema_destino = $6,
            status = $7,
            publicado_em = $8
         WHERE id = $9
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
          id,
        ]
      );

      return res.status(200).json({ post: serializePost(result.rows[0]) });
    } catch (err) {
      if (err && err.code === '23505') {
        return res.status(409).json({ error: 'slug já existe' });
      }
      console.error('[cms] PUT /api/cms/posts/:id', err.message);
      return res.status(500).json({ error: 'Falha ao atualizar post' });
    }
  });

  console.log('📰 [cms] rotas /api/cms/posts (GET público + POST/PUT admin) registradas');
}

module.exports = {
  registerCmsPostsRoutes,
  slugify,
};
