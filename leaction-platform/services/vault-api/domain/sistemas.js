'use strict';

function serializeSistema(row) {
  if (!row) return null;
  return {
    sistema: row.sistema,
    rotation_webhook_url: row.rotation_webhook_url,
    has_rotation_secret: Boolean(row.rotation_secret),
    suporta_rotacao_automatica: Boolean(row.suporta_rotacao_automatica),
  };
}

function registerSistemasRoutes(app, pool, { requireAuth }) {
  app.get('/api/sistemas', requireAuth, async (_req, res) => {
    try {
      const result = await pool.query(
        `SELECT sistema, rotation_webhook_url, rotation_secret, suporta_rotacao_automatica
         FROM sistemas_rotacao
         ORDER BY sistema ASC`
      );
      return res.status(200).json({
        sistemas: result.rows.map(serializeSistema),
      });
    } catch (err) {
      console.error('[vault] GET /api/sistemas', err.message);
      return res.status(500).json({ error: 'Falha ao listar sistemas' });
    }
  });

  app.post('/api/sistemas', requireAuth, async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const sistema = String(body.sistema || '').trim().toLowerCase();
      if (!sistema) {
        return res.status(400).json({ error: 'sistema é obrigatório' });
      }
      const rotation_webhook_url =
        body.rotation_webhook_url != null
          ? String(body.rotation_webhook_url).trim() || null
          : null;
      const rotation_secret =
        body.rotation_secret != null
          ? String(body.rotation_secret).trim() || null
          : null;
      const suporta = Boolean(body.suporta_rotacao_automatica);

      const result = await pool.query(
        `INSERT INTO sistemas_rotacao
           (sistema, rotation_webhook_url, rotation_secret, suporta_rotacao_automatica)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (sistema) DO UPDATE SET
           rotation_webhook_url = EXCLUDED.rotation_webhook_url,
           rotation_secret = COALESCE(EXCLUDED.rotation_secret, sistemas_rotacao.rotation_secret),
           suporta_rotacao_automatica = EXCLUDED.suporta_rotacao_automatica
         RETURNING sistema, rotation_webhook_url, rotation_secret, suporta_rotacao_automatica`,
        [sistema, rotation_webhook_url, rotation_secret, suporta]
      );

      return res.status(200).json({ sistema: serializeSistema(result.rows[0]) });
    } catch (err) {
      console.error('[vault] POST /api/sistemas', err.message);
      return res.status(500).json({ error: 'Falha ao gravar sistema' });
    }
  });
}

module.exports = { registerSistemasRoutes, serializeSistema };
