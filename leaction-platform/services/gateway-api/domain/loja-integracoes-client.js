'use strict';

/**
 * Cliente HTTP da Loja para fidelidade/vitrine (BLOG-025).
 * Nunca loga telefone.
 */
const axios = require('axios');

function lojaBase() {
  return String(process.env.LOJA_API_BASE_URL || 'https://lojadepaes.com.br').replace(/\/$/, '');
}

function serviceKey() {
  return String(process.env.LOJA_INTEGRACOES_SERVICE_KEY || '').trim();
}

function headers() {
  const key = serviceKey();
  if (!key) return null;
  return { 'X-Service-Key': key, Accept: 'application/json' };
}

async function getCliente(telefone) {
  const h = headers();
  if (!h) return { cliente: false, pontos: 0, total: 0, skipped: 'no_key' };
  try {
    const { data, status } = await axios.get(`${lojaBase()}/api/v1/integracoes/fidelidade/cliente`, {
      params: { telefone: String(telefone || '') },
      headers: h,
      timeout: 12000,
      validateStatus: () => true,
    });
    if (status >= 200 && status < 300 && data && typeof data === 'object') {
      return {
        cliente: Boolean(data.cliente),
        pontos: Number(data.pontos) || 0,
        total: Number(data.total) || 0,
      };
    }
    console.warn('[loja-integracoes] cliente status=', status);
    return { cliente: false, pontos: 0, total: 0, error: `http_${status}` };
  } catch (err) {
    console.warn('[loja-integracoes] cliente fail:', err.message);
    return { cliente: false, pontos: 0, total: 0, error: 'network' };
  }
}

async function postCredito(telefone, referencia) {
  const h = headers();
  if (!h) return { creditado: false, pontos: 0, total: 0, skipped: 'no_key' };
  try {
    const { data, status } = await axios.post(
      `${lojaBase()}/api/v1/integracoes/fidelidade/credito`,
      { telefone: String(telefone || ''), referencia: String(referencia || '') },
      { headers: { ...h, 'Content-Type': 'application/json' }, timeout: 15000, validateStatus: () => true }
    );
    if (status >= 200 && status < 300 && data && typeof data === 'object') {
      return {
        creditado: Boolean(data.creditado),
        pontos: Number(data.pontos) || 0,
        total: Number(data.total) || 0,
      };
    }
    console.warn('[loja-integracoes] credito status=', status);
    return { creditado: false, pontos: 0, total: 0, error: `http_${status}` };
  } catch (err) {
    console.warn('[loja-integracoes] credito fail:', err.message);
    return { creditado: false, pontos: 0, total: 0, error: 'network' };
  }
}

async function getVitrine() {
  const h = headers();
  if (!h) return [];
  try {
    const { data, status } = await axios.get(`${lojaBase()}/api/v1/integracoes/vitrine`, {
      headers: h,
      timeout: 12000,
      validateStatus: () => true,
    });
    if (status >= 200 && status < 300 && Array.isArray(data)) return data;
    console.warn('[loja-integracoes] vitrine status=', status);
    return [];
  } catch (err) {
    console.warn('[loja-integracoes] vitrine fail:', err.message);
    return [];
  }
}

module.exports = { getCliente, postCredito, getVitrine, lojaBase, serviceKey };
