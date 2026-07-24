'use strict';

/**
 * Fonte do Micro-CMS no PanelDX.
 *
 * CMS_SOURCE=hub   (default) — lê Action Hub GET /api/public/cms
 * CMS_SOURCE=local — legado Flask PanelDX (ctdi_cms_config)
 *
 * CMS_FALLBACK_LOCAL=1 — se Hub falhar, tenta Flask (opcional)
 */

function getCmsSource() {
  return String(process.env.CMS_SOURCE || 'hub')
    .trim()
    .toLowerCase();
}

function isCmsFromHub() {
  const mode = getCmsSource();
  return mode !== 'local' && mode !== 'paneldx' && mode !== 'flask';
}

function hubGatewayBase() {
  return (
    process.env.HUB_GATEWAY_INTERNAL_URL ||
    process.env.HUB_API_INTERNAL_URL ||
    'http://127.0.0.1:4001'
  ).replace(/\/$/, '');
}

function hubPublicCmsAdminUrl() {
  const base = (
    process.env.HUB_PUBLIC_URL ||
    process.env.ACTION_HUB_PUBLIC_URL ||
    'http://localhost:4000'
  ).replace(/\/$/, '');
  return `${base}/dashboard/cms/site`;
}

/**
 * @param {import('axios').AxiosStatic} axios
 * @param {{ flaskPublicUrl: string }} opts flaskPublicUrl = `${API_BASE_URL}/public/cms`
 */
async function fetchCmsPublicPayload(axios, opts) {
  const flaskUrl = opts.flaskPublicUrl;
  const hubUrl = `${hubGatewayBase()}/api/public/cms`;

  if (isCmsFromHub()) {
    try {
      const response = await axios.get(hubUrl, {
        timeout: 8000,
        headers: { Accept: 'application/json' },
        validateStatus: (s) => s < 500,
      });
      if (response.status === 200 && response.data && typeof response.data === 'object') {
        return {
          ...response.data,
          success: response.data.success !== false,
          _cms_source: 'hub',
        };
      }
      console.warn(`[CMS] Hub respondeu HTTP ${response.status}`);
    } catch (err) {
      console.warn('[CMS] Hub indisponível:', err.message);
    }

    if (String(process.env.CMS_FALLBACK_LOCAL || '').trim() === '1') {
      try {
        const response = await axios.get(flaskUrl, { timeout: 8000 });
        return {
          ...response.data,
          _cms_source: 'local_fallback',
        };
      } catch (err) {
        console.warn('[CMS] Fallback local também falhou:', err.message);
      }
    }
    return null;
  }

  try {
    const response = await axios.get(flaskUrl, { timeout: 8000 });
    return {
      ...response.data,
      _cms_source: 'local',
    };
  } catch (err) {
    console.warn('[CMS] Flask CMS indisponível:', err.message);
    return null;
  }
}

module.exports = {
  getCmsSource,
  isCmsFromHub,
  hubGatewayBase,
  hubPublicCmsAdminUrl,
  fetchCmsPublicPayload,
};
