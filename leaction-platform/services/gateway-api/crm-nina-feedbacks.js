'use strict';

const axios = require('axios');

const STATUSES = new Set(['pendente', 'lido', 'recompensado', 'arquivado']);

function inoveBase() {
  return (process.env.INOVE4US_API_URL || 'https://inove4us.com.br').replace(/\/$/, '');
}

function inoveSecret() {
  return (process.env.CRM_TRACKING_SECRET || '').trim();
}

async function inoveRequest(path, { method = 'GET', body } = {}) {
  const secret = inoveSecret();
  if (!secret) {
    const err = new Error('CRM_TRACKING_SECRET não configurado');
    err.status = 503;
    throw err;
  }
  const url = `${inoveBase()}${path}`;
  try {
    const res = await axios({
      method,
      url,
      data: body,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'x-crm-secret': secret,
      },
      timeout: 15000,
      validateStatus: () => true,
    });
    return { status: res.status, data: res.data };
  } catch (err) {
    const e = new Error(err.message || 'inove_unavailable');
    e.status = 502;
    throw e;
  }
}

function registerCrmNinaFeedbacksRoutes(app, auth) {
  const crmSecretAuthorized = auth && auth.crmSecretAuthorized;
  if (typeof crmSecretAuthorized !== 'function') {
    throw new Error('crm-nina-feedbacks: crmSecretAuthorized é obrigatório');
  }

  app.get('/api/crm/feedbacks', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }
    const status = String(req.query.status || '').trim().toLowerCase();
    if (status && !STATUSES.has(status)) {
      return res.status(400).json({ ok: false, error: 'status inválido' });
    }
    try {
      const suffix = status ? `?status=${encodeURIComponent(status)}` : '';
      const upstream = await inoveRequest(`/internal/feedbacks${suffix}`);
      return res.status(upstream.status).json(upstream.data);
    } catch (err) {
      console.error('❌ [crm/feedbacks GET]', err.message);
      return res.status(err.status || 502).json({
        ok: false,
        error: err.status === 503 ? err.message : 'Falha ao listar feedbacks do Inove',
      });
    }
  });

  app.patch('/api/crm/feedbacks/:id', async (req, res) => {
    if (!crmSecretAuthorized(req)) {
      return res.status(401).json({ ok: false, error: 'x-crm-secret inválido ou ausente' });
    }
    const id = Number.parseInt(String(req.params.id || ''), 10);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ ok: false, error: 'id inválido' });
    }
    const body = req.body && typeof req.body === 'object' ? req.body : {};
    const status = body.status != null ? String(body.status).trim().toLowerCase() : undefined;
    const retorno = body.retorno_texto != null ? String(body.retorno_texto) : undefined;
    if (status && !STATUSES.has(status)) {
      return res.status(400).json({ ok: false, error: 'status inválido' });
    }
    const payload = {};
    if (status) payload.status = status;
    if (retorno != null && String(retorno).trim()) payload.retorno_texto = String(retorno).trim();
    if (!payload.status && !payload.retorno_texto) {
      return res.status(400).json({ ok: false, error: 'informe status e/ou retorno_texto' });
    }
    try {
      const upstream = await inoveRequest(`/internal/feedbacks/${id}`, {
        method: 'PATCH',
        body: payload,
      });
      return res.status(upstream.status).json(upstream.data);
    } catch (err) {
      console.error('❌ [crm/feedbacks PATCH]', err.message);
      return res.status(err.status || 502).json({
        ok: false,
        error: err.status === 503 ? err.message : 'Falha ao atualizar feedback no Inove',
      });
    }
  });
}

module.exports = {
  registerCrmNinaFeedbacksRoutes,
  STATUSES,
};
