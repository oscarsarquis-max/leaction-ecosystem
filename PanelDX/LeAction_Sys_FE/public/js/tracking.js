/**
 * PanelDX PLG Tracking — sensor anônimo → POST /api/tracking/enviar (proxy Hub).
 *
 * Equivalente ao hook React `useTracking` (FE do PanelDX é EJS/vanilla).
 * session_id UUID em localStorage com expiração de 30 dias.
 */
(function (global) {
  'use strict';

  var STORAGE_KEY = 'paneldx_crm_session';
  var TTL_MS = 30 * 24 * 60 * 60 * 1000;
  var ENDPOINT = '/api/tracking/enviar';

  function uuidv4() {
    if (global.crypto && typeof global.crypto.randomUUID === 'function') {
      return global.crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function readStore() {
    try {
      var raw = global.localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || !parsed.id || !parsed.expiresAt) return null;
      if (Date.now() > Number(parsed.expiresAt)) {
        global.localStorage.removeItem(STORAGE_KEY);
        return null;
      }
      return parsed;
    } catch (e) {
      return null;
    }
  }

  function writeStore(id) {
    var payload = { id: id, expiresAt: Date.now() + TTL_MS };
    try {
      global.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch (e) { /* private mode */ }
    return payload;
  }

  function getSessionId() {
    var existing = readStore();
    if (existing) {
      // Renova TTL a cada visita (janela deslizante de 30 dias)
      writeStore(existing.id);
      return existing.id;
    }
    return writeStore(uuidv4()).id;
  }

  function resolveUserId() {
    try {
      if (global._leadData && global._leadData.id_clie != null) {
        return Number(global._leadData.id_clie) || null;
      }
    } catch (e) { /* ignore */ }
    return null;
  }

  function track(tipoEvento, options) {
    options = options || {};
    var body = {
      id_sessao: getSessionId(),
      tipo_evento: String(tipoEvento || 'pageview'),
      url_pagina: options.url || (global.location && (global.location.pathname + global.location.search)) || '/',
      id_usuario: options.idUsuario != null ? options.idUsuario : resolveUserId(),
      tempo_gasto_segundos: options.tempoGastoSegundos || 0
    };

    // fire-and-forget — nunca bloqueia UX
    try {
      if (global.navigator && typeof global.navigator.sendBeacon === 'function' && options.useBeacon) {
        var blob = new Blob([JSON.stringify(body)], { type: 'application/json' });
        global.navigator.sendBeacon(ENDPOINT, blob);
        return Promise.resolve({ ok: true, beacon: true });
      }
      return fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        keepalive: true,
        credentials: 'same-origin'
      }).then(function (res) {
        return res.json().catch(function () { return { ok: true }; });
      }).catch(function () {
        return { ok: false };
      });
    } catch (e) {
      return Promise.resolve({ ok: false });
    }
  }

  function pageview(url) {
    return track('pageview', { url: url });
  }

  function bindCtaClicks(root) {
    var scope = root || global.document;
    if (!scope || !scope.querySelectorAll) return;
    scope.querySelectorAll('[data-crm-event]').forEach(function (el) {
      if (el.__crmBound) return;
      el.__crmBound = true;
      el.addEventListener('click', function () {
        var evt = el.getAttribute('data-crm-event');
        if (!evt) return;
        track(evt, { url: el.getAttribute('href') || (global.location && global.location.pathname) });
      }, { capture: true });
    });
  }

  function inferPageviewFromPath() {
    var path = (global.location && global.location.pathname) || '/';
    pageview(path);
  }

  function isEngagementPath(path) {
    return (
      path.indexOf('/mesa-do-inovador') === 0 ||
      path.indexOf('/solucionador-de-problemas') === 0 ||
      path.indexOf('/consultor-leaction') === 0
    );
  }

  /** Envia tempo_gasto_segundos no unload das ferramentas freemium (BI engajamento). */
  function bindDwellTime() {
    var path = (global.location && global.location.pathname) || '/';
    if (!isEngagementPath(path)) return;
    var startedAt = Date.now();
    var flushed = false;

    function flush() {
      if (flushed) return;
      var secs = Math.round((Date.now() - startedAt) / 1000);
      if (secs < 1) return;
      flushed = true;
      track('pageview', {
        url: path,
        tempoGastoSegundos: secs,
        useBeacon: true
      });
    }

    global.addEventListener('pagehide', flush);
    global.addEventListener('visibilitychange', function () {
      if (global.document && global.document.visibilityState === 'hidden') flush();
    });
  }

  /**
   * API estilo hook: const { track, pageview, sessionId } = useTracking()
   */
  function useTracking() {
    return {
      sessionId: getSessionId(),
      track: track,
      pageview: pageview,
      bindCtaClicks: bindCtaClicks
    };
  }

  function init() {
    getSessionId();
    inferPageviewFromPath();
    bindCtaClicks(global.document);
    bindDwellTime();
  }

  var api = {
    useTracking: useTracking,
    track: track,
    pageview: pageview,
    getSessionId: getSessionId,
    bindCtaClicks: bindCtaClicks,
    init: init
  };

  global.PanelDXTracking = api;
  global.useTracking = useTracking;

  if (global.document && global.document.readyState === 'loading') {
    global.document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : globalThis);
