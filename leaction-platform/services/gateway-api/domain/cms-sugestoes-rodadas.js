'use strict';

/**
 * BLOG-024c/d — rodadas assíncronas de sugestões.
 * Uma "rodada" é uma execução de gerarSugestoes (manual ou automática das 07:00),
 * registrada em cms_sugestoes_rodadas para a tela acompanhar por polling.
 *
 * Garantias (também no banco, via índices únicos do patch):
 *  - no máximo 1 rodada `running` por vez (POST repetido devolve a mesma rodada);
 *  - no máximo 1 rodada automática por dia (America/Sao_Paulo).
 */

const { MIN_ROUND_INTERVAL_MS, todaySaoPaulo } = require('./cms-sugestoes-lib');
const sugestoesJob = require('./cms-sugestoes-job');

const RODADAS_DDL = `
CREATE TABLE IF NOT EXISTS cms_sugestoes_rodadas (
  id          SERIAL PRIMARY KEY,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status      TEXT NOT NULL DEFAULT 'running',
  progress    JSONB NOT NULL DEFAULT '{}'::jsonb,
  result      JSONB,
  trigger     TEXT NOT NULL DEFAULT 'manual',
  CONSTRAINT chk_cms_sugestoes_rodadas_status CHECK (status IN ('running', 'done', 'error')),
  CONSTRAINT chk_cms_sugestoes_rodadas_trigger CHECK (trigger IN ('auto', 'manual'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cms_sugestoes_rodadas_running
  ON cms_sugestoes_rodadas ((true)) WHERE status = 'running';
CREATE UNIQUE INDEX IF NOT EXISTS uq_cms_sugestoes_rodadas_auto_dia
  ON cms_sugestoes_rodadas (((started_at AT TIME ZONE 'America/Sao_Paulo')::date))
  WHERE trigger = 'auto';
`;

function iso(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function normalizeRow(row) {
  if (!row) return null;
  return {
    id: Number(row.id),
    started_at: iso(row.started_at),
    finished_at: iso(row.finished_at),
    status: row.status,
    progress: row.progress && typeof row.progress === 'object' ? row.progress : {},
    result: row.result && typeof row.result === 'object' ? row.result : null,
    trigger: row.trigger,
  };
}

function blankProgress() {
  return { phase: 'iniciando', materias: 0, com_texto: 0, aprovadas: 0, message: 'Iniciando…' };
}

/** Forma pública devolvida por GET /api/cms/sugestoes/rodadas/:id. */
function shapeRodada(row) {
  const r = normalizeRow(row);
  if (!r) return null;
  const result = r.result;
  return {
    id: r.id,
    status: r.status,
    trigger: r.trigger,
    started_at: r.started_at,
    finished_at: r.finished_at,
    progress: { ...blankProgress(), ...r.progress },
    result:
      r.status === 'done' && result
        ? {
            created: Number(result.created) || 0,
            discarded_summary: Array.isArray(result.discarded_summary) ? result.discarded_summary : [],
            shortfall_message: result.shortfall_message ?? null,
            skipped: result.skipped ?? null,
            items: Array.isArray(result.items) ? result.items : [],
            stats: result.stats ?? null,
          }
        : null,
    error: r.status === 'error' ? result?.error || { code: 'falha', message: sugestoesJob.humanError('falha') } : null,
  };
}

function createMemoryRodadasStore() {
  const rows = [];
  let seq = 0;
  const find = (id) => rows.find((r) => r.id === Number(id));
  return {
    rows,
    async ensureSchema() {},
    async create({ trigger = 'manual', startedAt = new Date() } = {}) {
      const running = rows.find((r) => r.status === 'running');
      if (running) return { conflict: 'running', row: normalizeRow(running) };
      if (trigger === 'auto') {
        const day = todaySaoPaulo(startedAt);
        const hasAuto = rows.some(
          (r) => r.trigger === 'auto' && todaySaoPaulo(new Date(r.started_at)) === day
        );
        if (hasAuto) return { conflict: 'auto_dia' };
      }
      seq += 1;
      const row = {
        id: seq,
        started_at: startedAt.toISOString(),
        finished_at: null,
        status: 'running',
        progress: blankProgress(),
        result: null,
        trigger,
      };
      rows.push(row);
      return { row: normalizeRow(row) };
    },
    async get(id) {
      return normalizeRow(find(id));
    },
    async latestRunning() {
      return normalizeRow([...rows].reverse().find((r) => r.status === 'running'));
    },
    async latestFinished() {
      const done = rows.filter((r) => r.finished_at);
      done.sort((a, b) => new Date(b.finished_at) - new Date(a.finished_at));
      return normalizeRow(done[0]);
    },
    async update(id, patch = {}) {
      const row = find(id);
      if (!row) return;
      if (patch.status) row.status = patch.status;
      if (patch.progress) row.progress = patch.progress;
      if (patch.result) row.result = patch.result;
      if (patch.finished_at) row.finished_at = iso(patch.finished_at);
    },
    async failOrphans(now = new Date()) {
      let n = 0;
      for (const row of rows) {
        if (row.status !== 'running') continue;
        row.status = 'error';
        row.finished_at = now.toISOString();
        row.result = {
          created: 0,
          error: { code: 'interrompida', message: sugestoesJob.humanError('interrompida') },
        };
        n += 1;
      }
      return n;
    },
  };
}

function createPgRodadasStore(pool) {
  return {
    async ensureSchema() {
      await pool.query(RODADAS_DDL);
    },
    async create({ trigger = 'manual', startedAt = new Date() } = {}) {
      try {
        const res = await pool.query(
          `INSERT INTO cms_sugestoes_rodadas (started_at, status, progress, trigger)
           VALUES ($1, 'running', $2::jsonb, $3)
           RETURNING *`,
          [startedAt.toISOString(), JSON.stringify(blankProgress()), trigger]
        );
        return { row: normalizeRow(res.rows[0]) };
      } catch (err) {
        if (err && err.code === '23505') {
          const running = await this.latestRunning();
          if (running) return { conflict: 'running', row: running };
          return { conflict: 'auto_dia' };
        }
        throw err;
      }
    },
    async get(id) {
      const res = await pool.query(`SELECT * FROM cms_sugestoes_rodadas WHERE id = $1`, [id]);
      return normalizeRow(res.rows[0]);
    },
    async latestRunning() {
      const res = await pool.query(
        `SELECT * FROM cms_sugestoes_rodadas WHERE status = 'running' ORDER BY id DESC LIMIT 1`
      );
      return normalizeRow(res.rows[0]);
    },
    async latestFinished() {
      const res = await pool.query(
        `SELECT * FROM cms_sugestoes_rodadas
          WHERE finished_at IS NOT NULL
          ORDER BY finished_at DESC LIMIT 1`
      );
      return normalizeRow(res.rows[0]);
    },
    async update(id, patch = {}) {
      await pool.query(
        `UPDATE cms_sugestoes_rodadas
            SET status = COALESCE($2, status),
                progress = COALESCE($3::jsonb, progress),
                result = COALESCE($4::jsonb, result),
                finished_at = COALESCE($5::timestamptz, finished_at)
          WHERE id = $1`,
        [
          id,
          patch.status || null,
          patch.progress ? JSON.stringify(patch.progress) : null,
          patch.result ? JSON.stringify(patch.result) : null,
          patch.finished_at ? iso(patch.finished_at) : null,
        ]
      );
    },
    async failOrphans(now = new Date()) {
      const res = await pool.query(
        `UPDATE cms_sugestoes_rodadas
            SET status = 'error', finished_at = $1::timestamptz, result = $2::jsonb
          WHERE status = 'running'
          RETURNING id`,
        [
          now.toISOString(),
          JSON.stringify({
            created: 0,
            error: { code: 'interrompida', message: sugestoesJob.humanError('interrompida') },
          }),
        ]
      );
      return res.rows.length;
    },
  };
}

/**
 * @param {import('pg').Pool} pool
 * @param {{ store?, now?: () => Date, minIntervalMs?: number, generate?: Function, generateDeps?: object }} [opts]
 */
function createRodadaRunner(pool, opts = {}) {
  const store = opts.store || createPgRodadasStore(pool);
  const now = opts.now || (() => new Date());
  const minIntervalMs = opts.minIntervalMs ?? MIN_ROUND_INTERVAL_MS;
  // Resolve em tempo de chamada para que testes possam trocar sugestoesJob.gerarSugestoes.
  const generate = opts.generate || ((p, deps) => sugestoesJob.gerarSugestoes(p, deps));
  const active = new Map();

  async function execute(id) {
    let queue = Promise.resolve();
    const enqueue = (patch) => {
      queue = queue
        .then(() => store.update(id, patch))
        .catch((err) => console.warn(`[cms-sugestoes] rodada ${id} update: ${err.message}`));
      return queue;
    };
    let lastProgress = blankProgress();
    try {
      const result = await generate(pool, {
        ...(opts.generateDeps || {}),
        onProgress: (progress) => {
          lastProgress = progress;
          enqueue({ progress });
        },
      });
      await queue;
      await store.update(id, {
        status: 'done',
        finished_at: now(),
        progress: { ...lastProgress, phase: 'concluido' },
        result: {
          created: result.created || 0,
          discarded_summary: result.discarded_summary || [],
          shortfall_message: result.shortfall_message ?? null,
          skipped: result.skipped ?? null,
          already: result.already ?? null,
          slots: result.slots ?? null,
          items: result.items || [],
          ids: result.ids || [],
          stats: result.stats || null,
        },
      });
    } catch (err) {
      console.error(`[cms-sugestoes] rodada ${id}: ${err.message}`);
      await queue;
      const known = err instanceof sugestoesJob.SugestoesError;
      const code = known ? err.code : 'falha';
      const message = known ? err.message : sugestoesJob.humanError('falha');
      try {
        await store.update(id, {
          status: 'error',
          finished_at: now(),
          progress: { ...lastProgress, phase: 'erro', message },
          result: { created: 0, error: { code, message } },
        });
      } catch (writeErr) {
        console.error(`[cms-sugestoes] rodada ${id} erro ao gravar: ${writeErr.message}`);
      }
    }
  }

  /**
   * Inicia (ou reaproveita) uma rodada.
   * @returns {Promise<{ok:boolean, rodada_id?:number, reused?:boolean, status?:number, code?:string, message?:string, skipped?:boolean}>}
   */
  async function start({ trigger = 'manual', at = null } = {}) {
    const running = await store.latestRunning();
    if (running) return { ok: true, reused: true, rodada_id: running.id };

    const startedAt = at || now();
    if (trigger !== 'auto') {
      // Só rodada concluída segura o clique seguinte; se a anterior deu erro, pode tentar de novo.
      const last = await store.latestFinished();
      if (
        last &&
        last.status === 'done' &&
        startedAt.getTime() - new Date(last.finished_at).getTime() < minIntervalMs
      ) {
        return {
          ok: false,
          status: 429,
          code: 'rodada_recente',
          message: sugestoesJob.humanError('rodada_recente'),
          rodada_id: last.id,
        };
      }
    }

    const made = await store.create({ trigger, startedAt });
    if (made.conflict === 'running') return { ok: true, reused: true, rodada_id: made.row.id };
    if (made.conflict === 'auto_dia') return { ok: false, skipped: true, code: 'auto_ja_rodou' };

    const id = made.row.id;
    const task = execute(id).finally(() => active.delete(id));
    active.set(id, task);
    return { ok: true, reused: false, rodada_id: id };
  }

  return {
    store,
    start,
    get: (id) => store.get(id),
    whenIdle: () => Promise.all([...active.values()]),
  };
}

module.exports = {
  RODADAS_DDL,
  shapeRodada,
  blankProgress,
  createMemoryRodadasStore,
  createPgRodadasStore,
  createRodadaRunner,
};
