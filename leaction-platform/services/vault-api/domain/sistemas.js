'use strict';

function serializeSistema(row) {
  if (!row) return null;
  return {
    sistema: row.sistema,
    rotation_webhook_url: row.rotation_webhook_url,
    has_rotation_secret: Boolean(row.rotation_secret),
    suporta_rotacao_automatica: Boolean(row.suporta_rotacao_automatica),
    conta_webhook_url: row.conta_webhook_url || null,
    has_conta_secret: Boolean(row.conta_secret),
  };
}

function registerSistemasRoutes(app, pool, { requireAuth }) {
  app.get('/api/sistemas', requireAuth, async (_req, res) => {
    try {
      const result = await pool.query(
        `SELECT sistema, rotation_webhook_url, rotation_secret, suporta_rotacao_automatica,
                conta_webhook_url, conta_secret
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
      const hasContaUrl = Object.prototype.hasOwnProperty.call(body, 'conta_webhook_url');
      const hasContaSecret = Object.prototype.hasOwnProperty.call(body, 'conta_secret');
      const conta_webhook_url = hasContaUrl
        ? String(body.conta_webhook_url || '').trim() || null
        : null;
      const conta_secret = hasContaSecret
        ? String(body.conta_secret || '').trim() || null
        : null;

      const result = await pool.query(
        `INSERT INTO sistemas_rotacao
           (sistema, rotation_webhook_url, rotation_secret, suporta_rotacao_automatica,
            conta_webhook_url, conta_secret)
         VALUES ($1, $2, $3, $4, $5, $6)
         ON CONFLICT (sistema) DO UPDATE SET
           rotation_webhook_url = EXCLUDED.rotation_webhook_url,
           rotation_secret = COALESCE(EXCLUDED.rotation_secret, sistemas_rotacao.rotation_secret),
           suporta_rotacao_automatica = EXCLUDED.suporta_rotacao_automatica,
           conta_webhook_url = CASE
             WHEN $7 THEN EXCLUDED.conta_webhook_url
             ELSE sistemas_rotacao.conta_webhook_url
           END,
           conta_secret = CASE
             WHEN $8 THEN COALESCE(EXCLUDED.conta_secret, sistemas_rotacao.conta_secret)
             ELSE sistemas_rotacao.conta_secret
           END
         RETURNING sistema, rotation_webhook_url, rotation_secret, suporta_rotacao_automatica,
                   conta_webhook_url, conta_secret`,
        [
          sistema,
          rotation_webhook_url,
          rotation_secret,
          suporta,
          conta_webhook_url,
          conta_secret,
          hasContaUrl,
          hasContaSecret,
        ]
      );

      return res.status(200).json({ sistema: serializeSistema(result.rows[0]) });
    } catch (err) {
      console.error('[vault] POST /api/sistemas', err.message);
      return res.status(500).json({ error: 'Falha ao gravar sistema' });
    }
  });
}

module.exports = { registerSistemasRoutes, serializeSistema };
