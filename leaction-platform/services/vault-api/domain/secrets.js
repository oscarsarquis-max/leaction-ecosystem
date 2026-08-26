'use strict';

const { encryptPlaintext, decryptBuffer } = require('../lib/crypto');
const { clientIp } = require('../lib/auth');
const {
  generateSecretValue,
  notifySatelliteRotation,
} = require('../lib/rotation-s2s');

const STATUSES = new Set(['ativo', 'pendente_aplicacao', 'revogado']);

function serializeSecretMeta(row) {
  if (!row) return null;
  return {
    id: row.id,
    sistema: row.sistema,
    tipo: row.tipo,
    versao: row.versao,
    status: row.status,
    criado_em: row.criado_em,
    atualizado_em: row.atualizado_em,
    atualizado_por: row.atualizado_por,
    expira_em: row.expira_em,
  };
}

async function writeAudit(pool, { secretId, acao, ator, ip, detalhe }) {
  await pool.query(
    `INSERT INTO secrets_audit_log (secret_id, acao, ator, origem_ip, detalhe)
     VALUES ($1, $2, $3, $4, $5::jsonb)`,
    [
      secretId ?? null,
      acao,
      ator,
      ip,
      detalhe != null ? JSON.stringify(detalhe) : null,
    ]
  );
}

function registerSecretsRoutes(app, pool, { requireAuth }) {
  app.get('/api/secrets', requireAuth, async (req, res) => {
    try {
      const sistema = String(req.query.sistema || '').trim().toLowerCase();
      if (!sistema) {
        return res.status(400).json({ error: 'sistema é obrigatório' });
      }

      const result = await pool.query(
        `SELECT id, sistema, tipo, versao, status, criado_em, atualizado_em,
                atualizado_por, expira_em
         FROM secrets
         WHERE sistema = $1
         ORDER BY tipo ASC, id ASC`,
        [sistema]
      );

      const ator = req.vaultAdmin.email;
      const ip = clientIp(req);
      if (result.rows.length === 0) {
        await writeAudit(pool, {
          secretId: null,
          acao: 'lido',
          ator,
          ip,
          detalhe: { rota: 'GET /api/secrets', sistema, count: 0, mascarado: true },
        });
      } else {
        for (const row of result.rows) {
          await writeAudit(pool, {
            secretId: row.id,
            acao: 'lido',
            ator,
            ip,
            detalhe: { rota: 'GET /api/secrets', mascarado: true },
          });
        }
      }

      return res.status(200).json({
        secrets: result.rows.map(serializeSecretMeta),
        count: result.rows.length,
      });
    } catch (err) {
      console.error('[vault] GET /api/secrets', err.message);
      return res.status(500).json({ error: 'Falha ao listar secrets' });
    }
  });

  app.post('/api/secrets', requireAuth, async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const sistema = String(body.sistema || '').trim().toLowerCase();
      const tipo = String(body.tipo || '').trim();
      const valor = body.valor != null ? String(body.valor) : '';
      if (!sistema || !tipo || !valor) {
        return res.status(400).json({ error: 'Campos obrigatórios: sistema, tipo, valor' });
      }

      const cifrado = encryptPlaintext(valor);
      const ator = req.vaultAdmin.email;
      const result = await pool.query(
        `INSERT INTO secrets
           (sistema, tipo, valor_cifrado, versao, status, atualizado_por)
         VALUES ($1, $2, $3, 1, 'ativo', $4)
         RETURNING id, sistema, tipo, versao, status, criado_em, atualizado_em,
                   atualizado_por, expira_em`,
        [sistema, tipo, cifrado, ator]
      );

      await writeAudit(pool, {
        secretId: result.rows[0].id,
        acao: 'criado',
        ator,
        ip: clientIp(req),
        detalhe: { tipo, sistema },
      });

      return res.status(201).json({ secret: serializeSecretMeta(result.rows[0]) });
    } catch (err) {
      const status = err.status || 500;
      if (status === 503) {
        return res.status(503).json({ error: err.message });
      }
      console.error('[vault] POST /api/secrets', err.message);
      return res.status(500).json({ error: 'Falha ao criar secret' });
    }
  });

  app.get('/api/secrets/:id/revelar', requireAuth, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) {
        return res.status(400).json({ error: 'id inválido' });
      }

      const result = await pool.query(
        `SELECT id, sistema, tipo, valor_cifrado, versao, status, criado_em,
                atualizado_em, atualizado_por, expira_em
         FROM secrets
         WHERE id = $1
         LIMIT 1`,
        [id]
      );
      if (!result.rows[0]) {
        return res.status(404).json({ error: 'Secret não encontrado' });
      }

      const row = result.rows[0];
      if (!STATUSES.has(row.status) || row.status === 'revogado') {
        return res.status(403).json({ error: 'Secret revogado — revelação bloqueada' });
      }

      const valor = decryptBuffer(row.valor_cifrado);
      const ator = req.vaultAdmin.email;
      const ip = clientIp(req);

      await writeAudit(pool, {
        secretId: row.id,
        acao: 'lido',
        ator,
        ip,
        detalhe: {
          rota: 'GET /api/secrets/:id/revelar',
          revelado: true,
          sistema: row.sistema,
          tipo: row.tipo,
          versao: row.versao,
        },
      });

      res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
      res.set('Pragma', 'no-cache');
      return res.status(200).json({
        secret: serializeSecretMeta(row),
        valor,
      });
    } catch (err) {
      const status = err.status || 500;
      if (status === 503) {
        return res.status(503).json({ error: err.message });
      }
      console.error('[vault] GET /api/secrets/:id/revelar', err.message);
      return res.status(500).json({ error: 'Falha ao revelar secret' });
    }
  });

  app.post('/api/secrets/:id/rotacionar', requireAuth, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) {
        return res.status(400).json({ error: 'id inválido' });
      }

      const current = await pool.query(`SELECT * FROM secrets WHERE id = $1 LIMIT 1`, [id]);
      if (!current.rows[0]) {
        return res.status(404).json({ error: 'Secret não encontrado' });
      }
      const anterior = current.rows[0];
      if (anterior.status !== 'ativo') {
        return res.status(400).json({
          error: 'Só é possível rotacionar um secret com status ativo',
        });
      }

      const pending = await pool.query(
        `SELECT id FROM secrets
         WHERE sistema = $1 AND tipo = $2 AND status = 'pendente_aplicacao'
         LIMIT 1`,
        [anterior.sistema, anterior.tipo]
      );
      if (pending.rows[0]) {
        return res.status(409).json({
          error: 'Já existe uma versão pendente de aplicação para este secret',
        });
      }

      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const novoValor =
        body.novo_valor != null && String(body.novo_valor) !== ''
          ? String(body.novo_valor)
          : generateSecretValue();

      const maxV = await pool.query(
        `SELECT COALESCE(MAX(versao), 0)::int AS v
         FROM secrets WHERE sistema = $1 AND tipo = $2`,
        [anterior.sistema, anterior.tipo]
      );
      const nextVersao = Number(maxV.rows[0].v) + 1;
      const ator = req.vaultAdmin.email;
      const ip = clientIp(req);
      const cifrado = encryptPlaintext(novoValor);

      const inserted = await pool.query(
        `INSERT INTO secrets
           (sistema, tipo, valor_cifrado, versao, status, atualizado_por)
         VALUES ($1, $2, $3, $4, 'pendente_aplicacao', $5)
         RETURNING id, sistema, tipo, versao, status, criado_em, atualizado_em,
                   atualizado_por, expira_em`,
        [anterior.sistema, anterior.tipo, cifrado, nextVersao, ator]
      );
      const nova = inserted.rows[0];

      const sistemaRow = await pool.query(
        `SELECT sistema, rotation_webhook_url, rotation_secret, suporta_rotacao_automatica
         FROM sistemas_rotacao
         WHERE sistema = $1
         LIMIT 1`,
        [anterior.sistema]
      );
      const cfg = sistemaRow.rows[0] || null;
      const auto =
        Boolean(cfg?.suporta_rotacao_automatica) &&
        Boolean(String(cfg?.rotation_webhook_url || '').trim());

      if (auto) {
        try {
          const notify = await notifySatelliteRotation({
            url: cfg.rotation_webhook_url,
            rotationSecret: cfg.rotation_secret,
            tipo: anterior.tipo,
            novo_valor: novoValor,
          });
          await pool.query(
            `UPDATE secrets
             SET status = 'revogado', atualizado_em = CURRENT_TIMESTAMP, atualizado_por = $2
             WHERE id = $1`,
            [anterior.id, ator]
          );
          const activated = await pool.query(
            `UPDATE secrets
             SET status = 'ativo', atualizado_em = CURRENT_TIMESTAMP, atualizado_por = $2
             WHERE id = $1
             RETURNING id, sistema, tipo, versao, status, criado_em, atualizado_em,
                       atualizado_por, expira_em`,
            [nova.id, ator]
          );
          await writeAudit(pool, {
            secretId: nova.id,
            acao: 'rotacionado',
            ator,
            ip,
            detalhe: {
              rota: 'POST /api/secrets/:id/rotacionar',
              modo: 'automatico',
              versao_anterior: anterior.versao,
              versao_nova: nextVersao,
              secret_anterior_id: anterior.id,
              satelite_http: notify.status,
            },
          });
          return res.status(200).json({
            secret: serializeSecretMeta(activated.rows[0]),
            anterior: { id: anterior.id, versao: anterior.versao, status: 'revogado' },
            modo: 'automatico',
          });
        } catch (err) {
          await writeAudit(pool, {
            secretId: nova.id,
            acao: 'falha_rotacao',
            ator,
            ip,
            detalhe: {
              rota: 'POST /api/secrets/:id/rotacionar',
              modo: 'automatico',
              erro: String(err.message || err).slice(0, 400),
              versao_anterior: anterior.versao,
              versao_nova: nextVersao,
            },
          });
          return res.status(502).json({
            error: 'Falha ao aplicar rotação no satélite. A versão anterior permanece ativa.',
            detalhe: String(err.message || err).slice(0, 240),
            secret: serializeSecretMeta(nova),
            anterior: {
              id: anterior.id,
              versao: anterior.versao,
              status: 'ativo',
            },
            modo: 'automatico',
          });
        }
      }

      await writeAudit(pool, {
        secretId: nova.id,
        acao: 'criado',
        ator,
        ip,
        detalhe: {
          rota: 'POST /api/secrets/:id/rotacionar',
          modo: 'manual',
          versao: nextVersao,
        },
      });
      await writeAudit(pool, {
        secretId: nova.id,
        acao: 'lido',
        ator,
        ip,
        detalhe: {
          rota: 'POST /api/secrets/:id/rotacionar',
          revelado: true,
          modo: 'manual',
        },
      });

      res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
      res.set('Pragma', 'no-cache');
      return res.status(200).json({
        secret: serializeSecretMeta(nova),
        anterior: { id: anterior.id, versao: anterior.versao, status: anterior.status },
        modo: 'manual',
        valor: novoValor,
      });
    } catch (err) {
      const status = err.status || 500;
      if (status === 503) {
        return res.status(503).json({ error: err.message });
      }
      console.error('[vault] POST /api/secrets/:id/rotacionar', err.message);
      return res.status(500).json({ error: 'Falha ao rotacionar secret' });
    }
  });

  app.post('/api/secrets/:id/confirmar-aplicacao', requireAuth, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) {
        return res.status(400).json({ error: 'id inválido' });
      }

      const current = await pool.query(`SELECT * FROM secrets WHERE id = $1 LIMIT 1`, [id]);
      if (!current.rows[0]) {
        return res.status(404).json({ error: 'Secret não encontrado' });
      }
      const pendente = current.rows[0];
      if (pendente.status !== 'pendente_aplicacao') {
        return res.status(400).json({
          error: 'Só é possível confirmar uma versão pendente de aplicação',
        });
      }

      const ator = req.vaultAdmin.email;
      const anterior = await pool.query(
        `SELECT id, versao, status FROM secrets
         WHERE sistema = $1 AND tipo = $2 AND status = 'ativo' AND id <> $3
         ORDER BY versao DESC
         LIMIT 1`,
        [pendente.sistema, pendente.tipo, pendente.id]
      );

      if (anterior.rows[0]) {
        await pool.query(
          `UPDATE secrets
           SET status = 'revogado', atualizado_em = CURRENT_TIMESTAMP, atualizado_por = $2
           WHERE id = $1`,
          [anterior.rows[0].id, ator]
        );
      }

      const activated = await pool.query(
        `UPDATE secrets
         SET status = 'ativo', atualizado_em = CURRENT_TIMESTAMP, atualizado_por = $2
         WHERE id = $1
         RETURNING id, sistema, tipo, versao, status, criado_em, atualizado_em,
                   atualizado_por, expira_em`,
        [pendente.id, ator]
      );

      await writeAudit(pool, {
        secretId: pendente.id,
        acao: 'rotacionado',
        ator,
        ip: clientIp(req),
        detalhe: {
          rota: 'POST /api/secrets/:id/confirmar-aplicacao',
          modo: 'manual',
          secret_anterior_id: anterior.rows[0]?.id || null,
          versao_anterior: anterior.rows[0]?.versao || null,
          versao_nova: pendente.versao,
        },
      });

      return res.status(200).json({
        secret: serializeSecretMeta(activated.rows[0]),
        anterior: anterior.rows[0]
          ? {
              id: anterior.rows[0].id,
              versao: anterior.rows[0].versao,
              status: 'revogado',
            }
          : null,
      });
    } catch (err) {
      console.error('[vault] POST /api/secrets/:id/confirmar-aplicacao', err.message);
      return res.status(500).json({ error: 'Falha ao confirmar aplicação' });
    }
  });

  app.get('/api/secrets/:id/historico', requireAuth, async (req, res) => {
    try {
      const id = parseInt(String(req.params.id), 10);
      if (!Number.isFinite(id)) {
        return res.status(400).json({ error: 'id inválido' });
      }

      const current = await pool.query(
        `SELECT id, sistema, tipo FROM secrets WHERE id = $1 LIMIT 1`,
        [id]
      );
      if (!current.rows[0]) {
        return res.status(404).json({ error: 'Secret não encontrado' });
      }

      const result = await pool.query(
        `SELECT id, sistema, tipo, versao, status, criado_em, atualizado_em,
                atualizado_por, expira_em
         FROM secrets
         WHERE sistema = $1 AND tipo = $2
         ORDER BY versao DESC, id DESC`,
        [current.rows[0].sistema, current.rows[0].tipo]
      );

      return res.status(200).json({
        sistema: current.rows[0].sistema,
        tipo: current.rows[0].tipo,
        versoes: result.rows.map(serializeSecretMeta),
      });
    } catch (err) {
      console.error('[vault] GET /api/secrets/:id/historico', err.message);
      return res.status(500).json({ error: 'Falha ao listar histórico' });
    }
  });
}

module.exports = { registerSecretsRoutes, serializeSecretMeta };
