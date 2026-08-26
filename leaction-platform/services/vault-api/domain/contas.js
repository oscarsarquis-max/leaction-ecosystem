'use strict';

const { encryptPlaintext } = require('../lib/crypto');
const { clientIp } = require('../lib/auth');
const {
  generateSecretValue,
  notifySatelliteConta,
} = require('../lib/rotation-s2s');
const { serializeSecretMeta, writeAudit } = require('./secrets');

const NIVEIS = new Set(['admin', 'gestor_produtivo', 'usuario_executor']);
const TIPO_CONTA = 'senha_conta';

const CONTA_META_COLS = `id, sistema, tipo, versao, status, criado_em, atualizado_em,
                atualizado_por, expira_em, usuario_email`;

function registerContasRoutes(app, pool, { requireAuth }) {
  app.get('/api/contas', requireAuth, async (req, res) => {
    try {
      const sistema = String(req.query.sistema || '').trim().toLowerCase();
      if (!sistema) {
        return res.status(400).json({ error: 'sistema é obrigatório' });
      }

      const result = await pool.query(
        `SELECT ${CONTA_META_COLS}
         FROM secrets
         WHERE sistema = $1 AND usuario_email IS NOT NULL
         ORDER BY usuario_email ASC, versao DESC, id DESC`,
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
          detalhe: { rota: 'GET /api/contas', sistema, count: 0, mascarado: true },
        });
      } else {
        for (const row of result.rows) {
          await writeAudit(pool, {
            secretId: row.id,
            acao: 'lido',
            ator,
            ip,
            detalhe: {
              rota: 'GET /api/contas',
              mascarado: true,
              usuario_email: row.usuario_email,
            },
          });
        }
      }

      return res.status(200).json({
        contas: result.rows.map(serializeSecretMeta),
        count: result.rows.length,
        identidade: {
          nivel_funcao:
            'Nivel e função desta conta ficam na Gestão de Identidade do Hub. O cofre não duplica esses campos — só guarda a senha.',
        },
      });
    } catch (err) {
      console.error('[vault] GET /api/contas', err.message);
      return res.status(500).json({ error: 'Falha ao listar contas privilegiadas' });
    }
  });

  app.post('/api/contas', requireAuth, async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const sistema = String(body.sistema || '').trim().toLowerCase();
      const email = String(body.email || '').trim().toLowerCase();
      const nivel = String(body.nivel || '').trim();
      const funcao = body.funcao != null ? String(body.funcao).trim() : '';
      const senhaInformada =
        body.senha != null && String(body.senha) !== '' ? String(body.senha) : '';

      if (!sistema || !email || !nivel) {
        return res.status(400).json({
          error: 'Campos obrigatórios: sistema, email, nivel',
        });
      }
      if (!email.includes('@')) {
        return res.status(400).json({ error: 'E-mail inválido' });
      }
      if (!NIVEIS.has(nivel)) {
        return res.status(400).json({
          error: `nivel inválido (use: ${[...NIVEIS].join(', ')})`,
        });
      }

      const existing = await pool.query(
        `SELECT id, status FROM secrets
         WHERE sistema = $1 AND usuario_email = $2
           AND status IN ('ativo', 'pendente_aplicacao')
         LIMIT 1`,
        [sistema, email]
      );
      if (existing.rows[0]) {
        return res.status(409).json({
          error: 'Já existe uma senha ativa ou pendente para esta conta neste sistema',
        });
      }

      const senha = senhaInformada || generateSecretValue();
      const ator = req.vaultAdmin.email;
      const ip = clientIp(req);
      const cifrado = encryptPlaintext(senha);

      const inserted = await pool.query(
        `INSERT INTO secrets
           (sistema, tipo, valor_cifrado, versao, status, atualizado_por, usuario_email)
         VALUES ($1, $2, $3, 1, 'pendente_aplicacao', $4, $5)
         RETURNING ${CONTA_META_COLS}`,
        [sistema, TIPO_CONTA, cifrado, ator, email]
      );
      const secret = inserted.rows[0];

      const sistemaRow = await pool.query(
        `SELECT conta_webhook_url, conta_secret
         FROM sistemas_rotacao
         WHERE sistema = $1
         LIMIT 1`,
        [sistema]
      );
      const cfg = sistemaRow.rows[0] || null;
      const webhook = String(cfg?.conta_webhook_url || '').trim();

      if (webhook) {
        try {
          const payload = { acao: 'criar', email, senha, nivel };
          if (funcao) payload.funcao = funcao;
          const notify = await notifySatelliteConta({
            url: webhook,
            contaSecret: cfg.conta_secret,
            payload,
          });
          const activated = await pool.query(
            `UPDATE secrets
             SET status = 'ativo', atualizado_em = CURRENT_TIMESTAMP, atualizado_por = $2
             WHERE id = $1
             RETURNING ${CONTA_META_COLS}`,
            [secret.id, ator]
          );
          await writeAudit(pool, {
            secretId: secret.id,
            acao: 'criado',
            ator,
            ip,
            detalhe: {
              rota: 'POST /api/contas',
              modo: 'automatico',
              usuario_email: email,
              nivel,
              satelite_http: notify.status,
            },
          });
          return res.status(201).json({
            secret: serializeSecretMeta(activated.rows[0]),
            modo: 'automatico',
          });
        } catch (err) {
          await writeAudit(pool, {
            secretId: secret.id,
            acao: 'falha_criacao',
            ator,
            ip,
            detalhe: {
              rota: 'POST /api/contas',
              modo: 'automatico',
              usuario_email: email,
              nivel,
              erro: String(err.message || err).slice(0, 400),
            },
          });
          return res.status(502).json({
            error:
              'Falha ao criar a conta no satélite. A senha ficou pendente de aplicação.',
            detalhe: String(err.message || err).slice(0, 240),
            secret: serializeSecretMeta(secret),
            modo: 'automatico',
          });
        }
      }

      await writeAudit(pool, {
        secretId: secret.id,
        acao: 'criado',
        ator,
        ip,
        detalhe: {
          rota: 'POST /api/contas',
          modo: 'manual',
          usuario_email: email,
          nivel,
        },
      });
      await writeAudit(pool, {
        secretId: secret.id,
        acao: 'lido',
        ator,
        ip,
        detalhe: {
          rota: 'POST /api/contas',
          revelado: true,
          modo: 'manual',
          usuario_email: email,
        },
      });

      res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
      res.set('Pragma', 'no-cache');
      return res.status(201).json({
        secret: serializeSecretMeta(secret),
        modo: 'manual',
        valor: senha,
      });
    } catch (err) {
      const status = err.status || 500;
      if (status === 503) {
        return res.status(503).json({ error: err.message });
      }
      console.error('[vault] POST /api/contas', err.message);
      return res.status(500).json({ error: 'Falha ao criar conta privilegiada' });
    }
  });
}

module.exports = { registerContasRoutes, NIVEIS };
