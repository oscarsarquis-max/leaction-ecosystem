'use strict';

/**
 * Watcher desatendido: sonda os 5 serviços e alerta via SES em transição DOWN/UP.
 *
 * Env:
 *   STATUS_ALERT_ENABLED=1          (ou NODE_ENV=production + FROM configurado)
 *   STATUS_ALERT_INTERVAL_MS=60000
 *   STATUS_ALERT_COOLDOWN_MS=1800000
 *   STATUS_ALERT_STATE_PATH=...
 *   STATUS_ALERT_PROBE_JWT=...
 *   STATUS_ALERT_FROM / STATUS_ALERT_TO
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { runAllStatusProbes } = require('./status-probes');
const { isSesMailConfigured, sendStatusAlertEmail, alertTo, alertFrom } = require('./ses-mailer');

const DEFAULT_INTERVAL_MS = 60_000;
const DEFAULT_COOLDOWN_MS = 1_800_000;

function log(...args) {
  console.log('[status-watcher]', ...args);
}

function warn(...args) {
  console.warn('[status-watcher]', ...args);
}

function isWatcherEnabled() {
  const flag = String(process.env.STATUS_ALERT_ENABLED || '').trim().toLowerCase();
  if (flag === '0' || flag === 'false' || flag === 'off') return false;
  if (flag === '1' || flag === 'true' || flag === 'on') return true;
  // Produção: liga só se e-mail SES estiver configurado
  return process.env.NODE_ENV === 'production' && isSesMailConfigured();
}

function intervalMs() {
  const n = Number(process.env.STATUS_ALERT_INTERVAL_MS);
  return Number.isFinite(n) && n >= 15_000 ? n : DEFAULT_INTERVAL_MS;
}

function cooldownMs() {
  const n = Number(process.env.STATUS_ALERT_COOLDOWN_MS);
  return Number.isFinite(n) && n >= 0 ? n : DEFAULT_COOLDOWN_MS;
}

function statePath() {
  const explicit = String(process.env.STATUS_ALERT_STATE_PATH || '').trim();
  if (explicit) return explicit;
  if (process.env.NODE_ENV === 'production') {
    return '/var/tmp/actionhub-status-state.json';
  }
  return path.join(__dirname, '..', '..', '..', '.dev-logs', 'status-watcher-state.json');
}

function readState() {
  const file = statePath();
  try {
    if (!fs.existsSync(file)) return { services: {}, history: [] };
    const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
    return {
      services: raw.services && typeof raw.services === 'object' ? raw.services : {},
      history: Array.isArray(raw.history) ? raw.history : [],
    };
  } catch {
    return { services: {}, history: [] };
  }
}

function writeState(state) {
  const file = statePath();
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(state, null, 2), 'utf8');
  } catch (err) {
    warn('falha ao gravar estado:', err.message);
  }
}

function formatBrTime(iso) {
  try {
    return new Intl.DateTimeFormat('pt-BR', {
      timeZone: 'America/Sao_Paulo',
      dateStyle: 'short',
      timeStyle: 'medium',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function envLabel() {
  return (
    process.env.ACTION_HUB_PUBLIC_URL ||
    process.env.HOSTNAME ||
    os.hostname() ||
    'action-hub'
  );
}

function buildEmail(service, prevStatus, nextStatus, allServices) {
  const down = nextStatus === 'DOWN' || nextStatus === 'TIMEOUT';
  const subject = down
    ? `[Action Hub] Serviço FORA: ${service.name}`
    : `[Action Hub] Serviço recuperado: ${service.name}`;

  const checked = service.lastChecked || new Date().toISOString();
  const lines = [
    down ? 'ALERTA: serviço do Action Hub fora do ar.' : 'RECUPERAÇÃO: serviço do Action Hub voltou.',
    '',
    `Serviço: ${service.name}`,
    `Status: ${prevStatus || '—'} → ${nextStatus}`,
    `Latência: ${typeof service.latency === 'number' ? `${service.latency} ms` : '—'}`,
    `Detalhe: ${service.detail || '—'}`,
    `Probe: ${service.probeUrl || '—'}`,
    `Ambiente: ${envLabel()}`,
    `Horário (BRT): ${formatBrTime(checked)}`,
    `Horário (UTC): ${checked}`,
    '',
    'Snapshot dos serviços neste ciclo:',
  ];

  for (const s of allServices) {
    const mark = s.status === 'UP' ? 'OK' : s.status;
    lines.push(
      `  - [${mark}] ${s.name}` +
        (typeof s.latency === 'number' ? ` (${s.latency} ms)` : '') +
        (s.detail ? ` — ${s.detail}` : '')
    );
  }

  lines.push('', `Destinatários: ${alertTo().join(', ')}`, `Remetente: ${alertFrom()}`);

  const text = lines.join('\n');
  const html = `<pre style="font-family:ui-monospace,monospace;font-size:13px;line-height:1.45">${text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')}</pre>`;

  return { subject, text, html };
}

function shouldNotify(prev, next, lastAlertAt, now, cooldown) {
  if (!prev) {
    // Primeiro ciclo: só alerta se já estiver DOWN (não spammar UP inicial)
    return next === 'DOWN' || next === 'TIMEOUT';
  }
  if (prev === next) return false;
  const becameDown =
    (prev === 'UP' || prev === 'TIMEOUT') && (next === 'DOWN' || next === 'TIMEOUT');
  const recovered = (prev === 'DOWN' || prev === 'TIMEOUT') && next === 'UP';
  if (!becameDown && !recovered) return false;
  if (becameDown && lastAlertAt && now - lastAlertAt < cooldown) {
    return false;
  }
  return true;
}

/**
 * @param {import('pg').Pool} pool
 */
function startStatusWatcher(pool) {
  if (!isWatcherEnabled()) {
    log('desligado (STATUS_ALERT_ENABLED / NODE_ENV / SES)');
    return { stop() {} };
  }
  if (!isSesMailConfigured()) {
    warn('habilitado mas STATUS_ALERT_FROM ausente — watcher não inicia');
    return { stop() {} };
  }

  const interval = intervalMs();
  const cooldown = cooldownMs();
  let running = false;
  let timer = null;

  log(
    `iniciado interval=${interval}ms cooldown=${cooldown}ms to=${alertTo().join(',')} state=${statePath()}`
  );

  async function tick() {
    if (running) return;
    running = true;
    try {
      const results = await runAllStatusProbes(pool);
      const state = readState();
      const now = Date.now();

      for (const service of results) {
        const key = service.name;
        const prevEntry = state.services[key] || {};
        const prevStatus = prevEntry.status || null;
        const nextStatus = service.status;
        const lastAlertAt = typeof prevEntry.lastAlertAt === 'number' ? prevEntry.lastAlertAt : 0;

        if (shouldNotify(prevStatus, nextStatus, lastAlertAt, now, cooldown)) {
          const mail = buildEmail(service, prevStatus, nextStatus, results);
          try {
            const sent = await sendStatusAlertEmail(mail);
            log(`e-mail enviado: ${mail.subject} id=${sent.messageId || '?'}`);
            state.services[key] = {
              status: nextStatus,
              lastAlertAt: now,
              lastChecked: service.lastChecked,
              detail: service.detail || null,
            };
            state.history = [
              {
                at: new Date().toISOString(),
                name: key,
                from: prevStatus,
                to: nextStatus,
                messageId: sent.messageId,
              },
              ...state.history,
            ].slice(0, 50);
          } catch (err) {
            warn(`falha SES (${key}):`, err.message);
            state.services[key] = {
              status: nextStatus,
              lastAlertAt: prevEntry.lastAlertAt || 0,
              lastChecked: service.lastChecked,
              detail: service.detail || null,
            };
          }
        } else {
          state.services[key] = {
            status: nextStatus,
            lastAlertAt: prevEntry.lastAlertAt || 0,
            lastChecked: service.lastChecked,
            detail: service.detail || null,
          };
        }
      }

      writeState(state);
    } catch (err) {
      warn('ciclo falhou:', err.message);
    } finally {
      running = false;
    }
  }

  // Primeiro ciclo após boot (atraso curto para deps subirem)
  const bootDelay = Number(process.env.STATUS_ALERT_BOOT_DELAY_MS);
  const delay = Number.isFinite(bootDelay) && bootDelay >= 0 ? bootDelay : 15_000;
  setTimeout(() => {
    void tick();
  }, delay);

  timer = setInterval(() => {
    void tick();
  }, interval);
  if (typeof timer.unref === 'function') timer.unref();

  return {
    stop() {
      if (timer) clearInterval(timer);
      timer = null;
    },
    tick,
  };
}

module.exports = {
  startStatusWatcher,
  isWatcherEnabled,
};
