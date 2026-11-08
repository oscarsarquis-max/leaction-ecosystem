'use strict';

/**
 * Créditos do Hub: concessão por ciclo e reserva/confirm/release idempotente.
 * Saldo vive em entitlement_snapshots.payload_json.credits — satélite não é ledger.
 */

const TABLE_SQL = `
CREATE TABLE IF NOT EXISTS credit_operations (
  operation_id TEXT PRIMARY KEY,
  app_id TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
)`;

const INDEX_SQL = `
CREATE INDEX IF NOT EXISTS ix_credit_operations_subject
  ON credit_operations (app_id, subject_id)`;

const ALLOC_SQL = `
ALTER TABLE credit_operations
  ADD COLUMN IF NOT EXISTS allocation_json JSONB`;

function normalizeMeta(value) {
  if (value == null) return {};
  if (typeof value === 'object' && !Array.isArray(value)) return value;
  return {};
}

const AI_PACK_SKU = 'LOJADEPAES_BIBLIOTECA_CREDITOS';

function isOneShotAiPack(item, hubPayload) {
  const sku = String(item?.sku || hubPayload?.sku || '').toUpperCase();
  const type = String(item?.item_type || item?.type || '').toLowerCase();
  if (sku === AI_PACK_SKU) return true;
  return type === 'credit_pack' && sku.includes('BIBLIOTECA');
}

function isComplementaryItem(item, hubPayload) {
  if (isOneShotAiPack(item, hubPayload)) return false;
  const sku = String(item?.sku || hubPayload?.sku || '').toUpperCase();
  const meta = normalizeMeta(item?.meta_json);
  const hub = hubPayload || {};
  const direitos =
    hub.direitos ||
    hub.entitlements ||
    meta.direitos ||
    meta.entitlements ||
    {};
  const papel = String(
    direitos.papel || meta.papel || hub.papel || direitos.role || ''
  ).toLowerCase();
  return (
    papel === 'complementar' ||
    papel === 'complementary' ||
    sku.includes('COMPLEMENTAR')
  );
}

/**
 * Pacote avulso só quando o catálogo declara credit_pack (ou legado Inove).
 * Plano mensal com creditos=20 NÃO vira pack — senão a renovação acumula.
 */
function classifyCatalogItemType(declaredType, sku, credits) {
  const declared = String(declaredType || '').toLowerCase();
  if (declared === 'credit_pack') return 'credit_pack';
  if (declared === 'plan' || declared === 'addon' || declared === 'seat') return declared;
  if (credits > 0 || /credit/i.test(String(sku || ''))) return 'credit_pack';
  return declared || 'plan';
}

function resolveFranchise(item, hubPayload) {
  const hub = hubPayload || {};
  const meta = normalizeMeta(item?.meta_json);
  const direitos = hub.direitos || hub.entitlements || meta.direitos || {};
  const n = Number(
    hub.credits ??
      direitos.creditos ??
      direitos.credits ??
      meta.creditos ??
      meta.credits ??
      item?.quantity ??
      0
  );
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0;
}

function readBuckets(prev) {
  const complementary = prev.complementary && typeof prev.complementary === 'object' ? prev.complementary : null;
  let principalCredits = Number(prev.principal_credits);
  let complementaryCredits = Number(prev.complementary_credits);
  let packCredits = Number(prev.pack_credits);
  if (!Number.isFinite(packCredits)) packCredits = 0;
  if (!Number.isFinite(principalCredits)) {
    const total = Number(prev.credits || 0) || 0;
    if (complementary) {
      const granted = Number(complementary.remaining ?? complementary.credits_granted ?? 0) || 0;
      complementaryCredits = Number.isFinite(complementaryCredits) ? complementaryCredits : granted;
      principalCredits = Math.max(0, total - complementaryCredits - packCredits);
    } else {
      principalCredits = Math.max(0, total - packCredits);
      complementaryCredits = 0;
    }
  }
  if (!Number.isFinite(complementaryCredits)) complementaryCredits = 0;
  return { principalCredits, complementaryCredits, complementary, packCredits };
}

function isSnapshotValid(validUntil, now = Date.now()) {
  if (validUntil == null) return true;
  const t = new Date(validUntil).getTime();
  if (Number.isNaN(t)) return false;
  return t > now;
}

function viewCredits(payload, now, snapshotValidUntil) {
  const at = now == null ? Date.now() : now;
  const prev = payload && typeof payload === 'object' ? payload : {};
  const buckets = readBuckets(prev);
  const packCredits = Number(buckets.packCredits) || 0;
  const usedBiblioteca =
    Boolean(prev.plan) ||
    Boolean(buckets.complementary) ||
    packCredits > 0 ||
    Number.isFinite(Number(prev.principal_credits));
  if (!usedBiblioteca) {
    const generic = Number(prev.credits || 0) || 0;
    const genericActive = isSnapshotValid(snapshotValidUntil, at);
    return {
      principalActive: genericActive,
      complementaryActive: false,
      principalCredits: genericActive ? generic : 0,
      complementaryCredits: 0,
      packCredits: 0,
      available: genericActive ? generic : 0,
      spendOrder: ['principal', 'complementary'],
      principalUntil: snapshotValidUntil || null,
      complementaryUntil: null,
    };
  }
  const principalUntil = prev.plan?.cycle_ends_at || snapshotValidUntil || null;
  const complementaryUntil =
    buckets.complementary?.cycle_ends_at || buckets.complementary?.valid_until || null;
  const principalActive = Boolean(prev.plan) && isSnapshotValid(principalUntil, at);
  const complementaryActive = Boolean(buckets.complementary) && isSnapshotValid(complementaryUntil, at);
  const principalCredits = principalActive ? buckets.principalCredits : 0;
  const complementaryCredits = complementaryActive && principalActive ? buckets.complementaryCredits : 0;
  const available = principalCredits + complementaryCredits + packCredits;
  const principalEnd = principalUntil ? new Date(principalUntil).getTime() : Infinity;
  const complementaryEnd = complementaryUntil ? new Date(complementaryUntil).getTime() : Infinity;
  const spendOrder =
    complementaryActive && complementaryEnd <= principalEnd
      ? ['complementary', 'principal']
      : ['principal', 'complementary'];
  return {
    principalActive,
    complementaryActive,
    principalCredits,
    complementaryCredits,
    packCredits,
    available,
    spendOrder,
    principalUntil,
    complementaryUntil,
  };
}

function mergeEntitlement(prevObj, items, hubPayload, endsAt) {
  const prev = prevObj && typeof prevObj === 'object' ? { ...prevObj } : {};
  const buckets = readBuckets(prev);
  let principalCredits = buckets.principalCredits;
  let complementaryCredits = buckets.complementaryCredits;
  let premium = Boolean(prev.premium);
  let plan = prev.plan || null;
  let complementary = buckets.complementary;
  let replaceValidUntil = true;
  let seats = Number(prev.seats || 0) || 0;
  const addons = Array.isArray(prev.addons) ? [...prev.addons] : [];
  let genericCredits = Number(prev.credits || 0) || 0;
  let packCredits = buckets.packCredits;
  let usedBibliotecaBuckets = Boolean(plan || complementary || packCredits > 0);

  for (const item of items || []) {
    if (isOneShotAiPack(item, hubPayload)) {
      const qty = Number(item.quantity) || resolveFranchise(item, hubPayload) || 0;
      packCredits += qty;
      usedBibliotecaBuckets = true;
      replaceValidUntil = false;
      continue;
    }
    const complementaryItem = isComplementaryItem(item, hubPayload);
    if (item.item_type === 'credit_pack' && !complementaryItem) {
      genericCredits += Number(item.quantity) || 0;
      continue;
    }
    if (item.item_type === 'credit_pack' || (item.item_type === 'plan' && complementaryItem)) {
      const qty =
        item.item_type === 'credit_pack'
          ? Number(item.quantity) || 0
          : resolveFranchise(item, hubPayload) || Number(item.quantity) || 0;
      complementaryCredits = qty;
      complementary = {
        sku: item.sku,
        credits_granted: qty,
        remaining: qty,
        at: new Date().toISOString(),
        cycle_ends_at: endsAt || complementary?.cycle_ends_at || null,
      };
      replaceValidUntil = false;
      usedBibliotecaBuckets = true;
      continue;
    }
    if (item.item_type === 'plan') {
      const franchise = resolveFranchise(item, hubPayload);
      premium = true;
      plan = {
        sku: item.sku,
        name: item.meta_json?.plano_nome || item.sku,
        periodicidade: item.meta_json?.periodicidade || null,
        id_plano: item.meta_json?.id_plano || hubPayload?.id_plano || null,
        franchise: franchise || null,
        cycle_ends_at: endsAt || plan?.cycle_ends_at || null,
      };
      if (franchise > 0) {
        principalCredits = franchise;
        usedBibliotecaBuckets = true;
      }
      replaceValidUntil = true;
    }
    if (item.item_type === 'addon' || item.item_type === 'seat') {
      seats += Number(item.quantity) || 0;
      addons.push({ sku: item.sku, quantity: item.quantity });
    }
  }

  const credits = usedBibliotecaBuckets
    ? principalCredits + complementaryCredits + packCredits
    : genericCredits;
  const payload = {
    ...prev,
    credits,
    principal_credits: usedBibliotecaBuckets ? principalCredits : undefined,
    complementary_credits: usedBibliotecaBuckets ? complementaryCredits : undefined,
    pack_credits: usedBibliotecaBuckets ? packCredits : undefined,
    premium,
    plan,
    complementary,
    seats,
    addons,
    updated_from: 'contract_service',
    updated_at: new Date().toISOString(),
  };
  return { payload, replaceValidUntil };
}

function spendFromBuckets(payload, qty, snapshotValidUntil) {
  const prev = payload && typeof payload === 'object' ? payload : {};
  const buckets = readBuckets(prev);
  if (
    !prev.plan &&
    !prev.complementary &&
    !Number.isFinite(Number(prev.principal_credits)) &&
    buckets.packCredits <= 0
  ) {
    const credits = (Number(prev.credits || 0) || 0) - qty;
    return {
      payload: {
        ...prev,
        credits,
        updated_from: 'credits_reserve',
        updated_at: new Date().toISOString(),
      },
      allocation: { principal: qty, complementary: 0, pack: 0, generic: true },
    };
  }
  const view = viewCredits(prev, Date.now(), snapshotValidUntil);
  let remaining = qty;
  let fromPrincipal = 0;
  let fromComplementary = 0;
  let fromPack = 0;
  let principalCredits = buckets.principalCredits;
  let complementaryCredits = buckets.complementaryCredits;
  let packCredits = buckets.packCredits;
  for (const bucket of view.spendOrder) {
    if (remaining <= 0) break;
    if (bucket === 'complementary' && view.complementaryActive && view.principalActive) {
      const take = Math.min(complementaryCredits, remaining);
      complementaryCredits -= take;
      fromComplementary += take;
      remaining -= take;
    } else if (bucket === 'principal' && view.principalActive) {
      const take = Math.min(principalCredits, remaining);
      principalCredits -= take;
      fromPrincipal += take;
      remaining -= take;
    }
  }
  if (remaining > 0 && packCredits > 0) {
    const take = Math.min(packCredits, remaining);
    packCredits -= take;
    fromPack += take;
    remaining -= take;
  }
  const complementary = buckets.complementary
    ? { ...buckets.complementary, remaining: complementaryCredits }
    : null;
  return {
    payload: {
      ...prev,
      credits: principalCredits + complementaryCredits + packCredits,
      principal_credits: principalCredits,
      complementary_credits: complementaryCredits,
      pack_credits: packCredits,
      complementary,
      updated_from: 'credits_reserve',
      updated_at: new Date().toISOString(),
    },
    allocation: { principal: fromPrincipal, complementary: fromComplementary, pack: fromPack },
  };
}

function restoreFromAllocation(payload, allocation, amount) {
  const prev = payload && typeof payload === 'object' ? payload : {};
  if (allocation && allocation.generic) {
    return {
      ...prev,
      credits: (Number(prev.credits || 0) || 0) + (Number(amount) || 0),
      updated_from: 'credits_release',
      updated_at: new Date().toISOString(),
    };
  }
  const buckets = readBuckets(prev);
  let principalCredits = buckets.principalCredits;
  let complementaryCredits = buckets.complementaryCredits;
  let packCredits = buckets.packCredits;
  const fromP = Number(allocation?.principal);
  const fromC = Number(allocation?.complementary);
  const fromPack = Number(allocation?.pack);
  if (Number.isFinite(fromP) || Number.isFinite(fromC) || Number.isFinite(fromPack)) {
    principalCredits += Number.isFinite(fromP) ? fromP : 0;
    complementaryCredits += Number.isFinite(fromC) ? fromC : 0;
    packCredits += Number.isFinite(fromPack) ? fromPack : 0;
  } else {
    principalCredits += Number(amount) || 0;
  }
  const complementary = buckets.complementary
    ? { ...buckets.complementary, remaining: complementaryCredits }
    : null;
  return {
    ...prev,
    credits: principalCredits + complementaryCredits + packCredits,
    principal_credits: principalCredits,
    complementary_credits: complementaryCredits,
    pack_credits: packCredits,
    complementary,
    updated_from: 'credits_release',
    updated_at: new Date().toISOString(),
  };
}

function canReserveCredits(view, qty) {
  if (!view) {
    return { ok: false, error: 'insufficient_credits', credits: 0 };
  }
  const pack = Number(view.packCredits || 0);
  if (!view.principalActive && pack <= 0) {
    if (view.principalUntil && !isSnapshotValid(view.principalUntil)) {
      return {
        ok: false,
        error: 'expired',
        credits: Number(view.available) || 0,
        valid_until: view.principalUntil,
      };
    }
  }
  if (view.available < qty) {
    return { ok: false, error: 'insufficient_credits', credits: Number(view.available) || 0 };
  }
  if (!view.principalActive && pack <= 0) {
    return { ok: false, error: 'expired', valid_until: view.principalUntil || null };
  }
  return { ok: true };
}

function nextOperationStatus(existingStatus, action) {
  const current = existingStatus || null;
  if (action === 'reserve') {
    if (!current) return { ok: true, status: 'reserved', apply: true };
    if (current === 'reserved' || current === 'confirmed') {
      return { ok: true, status: current, apply: false, idempotent: true };
    }
    return { ok: false, error: 'operation_closed', status: current };
  }
  if (action === 'confirm') {
    if (current === 'reserved') return { ok: true, status: 'confirmed', apply: true };
    if (current === 'confirmed') return { ok: true, status: 'confirmed', apply: false, idempotent: true };
    if (!current) return { ok: false, error: 'operation_not_found' };
    return { ok: false, error: 'operation_not_reserved', status: current };
  }
  if (action === 'release') {
    if (current === 'reserved') return { ok: true, status: 'released', apply: true };
    if (current === 'released') return { ok: true, status: 'released', apply: false, idempotent: true };
    if (current === 'confirmed') return { ok: false, error: 'already_confirmed', status: current };
    if (!current) return { ok: false, error: 'operation_not_found' };
    return { ok: false, error: 'operation_not_reserved', status: current };
  }
  return { ok: false, error: 'unknown_action' };
}

async function ensureCreditOperationsTable(pool) {
  await pool.query(TABLE_SQL);
  await pool.query(INDEX_SQL);
  await pool.query(ALLOC_SQL);
}

function parsePayload(raw) {
  if (!raw) return {};
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  }
  return { ...raw };
}

async function reserveCredits(client, { appId, subjectId, amount, operationId }) {
  const qty = Number.parseInt(String(amount), 10);
  if (!Number.isFinite(qty) || qty <= 0) {
    return { ok: false, statusCode: 400, error: 'amount deve ser um inteiro positivo' };
  }
  const existing = await client.query(
    `SELECT status, amount FROM credit_operations
     WHERE operation_id = $1 FOR UPDATE`,
    [operationId]
  );
  if (existing.rows[0]) {
    const decision = nextOperationStatus(existing.rows[0].status, 'reserve');
    if (!decision.ok) {
      return { ok: false, statusCode: 409, error: decision.error, status: existing.rows[0].status };
    }
    const snap = await client.query(
      `SELECT payload_json, valid_until FROM entitlement_snapshots
       WHERE app_id = $1 AND subject_id = $2`,
      [appId, subjectId]
    );
    const payload = parsePayload(snap.rows[0]?.payload_json);
    return {
      ok: true,
      idempotent: true,
      status: existing.rows[0].status,
      credits: Number(payload.credits || 0) || 0,
      valid_until: snap.rows[0]?.valid_until || null,
    };
  }

  const snap = await client.query(
    `SELECT payload_json, valid_until FROM entitlement_snapshots
     WHERE app_id = $1 AND subject_id = $2
     FOR UPDATE`,
    [appId, subjectId]
  );
  if (!snap.rows[0]) {
    return { ok: false, statusCode: 409, error: 'no_entitlement' };
  }
  const payload = parsePayload(snap.rows[0].payload_json);
  const view = viewCredits(payload, Date.now(), snap.rows[0].valid_until);
  const allowed = canReserveCredits(view, qty);
  if (!allowed.ok) {
    return {
      ok: false,
      statusCode: 409,
      error: allowed.error,
      credits: allowed.credits,
      valid_until: allowed.valid_until || view.principalUntil || snap.rows[0].valid_until,
    };
  }
  const spent = spendFromBuckets(payload, qty, snap.rows[0].valid_until);
  await client.query(
    `UPDATE entitlement_snapshots
     SET payload_json = $3::jsonb, updated_at = CURRENT_TIMESTAMP
     WHERE app_id = $1 AND subject_id = $2`,
    [appId, subjectId, JSON.stringify(spent.payload)]
  );
  await client.query(
    `INSERT INTO credit_operations (operation_id, app_id, subject_id, amount, status, allocation_json)
     VALUES ($1, $2, $3, $4, 'reserved', $5::jsonb)`,
    [operationId, appId, subjectId, qty, JSON.stringify(spent.allocation)]
  );
  return {
    ok: true,
    status: 'reserved',
    credits: spent.payload.credits,
    valid_until: snap.rows[0].valid_until,
  };
}

async function confirmCredits(client, { appId, subjectId, operationId }) {
  const existing = await client.query(
    `SELECT status, app_id, subject_id FROM credit_operations
     WHERE operation_id = $1 FOR UPDATE`,
    [operationId]
  );
  if (!existing.rows[0]) {
    return { ok: false, statusCode: 409, error: 'operation_not_found' };
  }
  const row = existing.rows[0];
  if (row.app_id !== appId || row.subject_id !== subjectId) {
    return { ok: false, statusCode: 403, error: 'operation_mismatch' };
  }
  const decision = nextOperationStatus(row.status, 'confirm');
  if (!decision.ok) {
    return { ok: false, statusCode: 409, error: decision.error, status: row.status };
  }
  if (decision.apply) {
    await client.query(
      `UPDATE credit_operations
       SET status = 'confirmed', updated_at = CURRENT_TIMESTAMP
       WHERE operation_id = $1`,
      [operationId]
    );
  }
  const snap = await client.query(
    `SELECT payload_json, valid_until FROM entitlement_snapshots
     WHERE app_id = $1 AND subject_id = $2`,
    [appId, subjectId]
  );
  const payload = parsePayload(snap.rows[0]?.payload_json);
  return {
    ok: true,
    idempotent: Boolean(decision.idempotent),
    status: 'confirmed',
    credits: Number(payload.credits || 0) || 0,
    valid_until: snap.rows[0]?.valid_until || null,
  };
}

async function releaseCredits(client, { appId, subjectId, operationId }) {
  const existing = await client.query(
    `SELECT status, amount, app_id, subject_id, allocation_json FROM credit_operations
     WHERE operation_id = $1 FOR UPDATE`,
    [operationId]
  );
  if (!existing.rows[0]) {
    return { ok: false, statusCode: 409, error: 'operation_not_found' };
  }
  const row = existing.rows[0];
  if (row.app_id !== appId || row.subject_id !== subjectId) {
    return { ok: false, statusCode: 403, error: 'operation_mismatch' };
  }
  const decision = nextOperationStatus(row.status, 'release');
  if (!decision.ok) {
    return { ok: false, statusCode: 409, error: decision.error, status: row.status };
  }
  if (decision.apply) {
    const snap = await client.query(
      `SELECT payload_json FROM entitlement_snapshots
       WHERE app_id = $1 AND subject_id = $2
       FOR UPDATE`,
      [appId, subjectId]
    );
    if (snap.rows[0]) {
      const payload = parsePayload(snap.rows[0].payload_json);
      const allocation =
        row.allocation_json && typeof row.allocation_json === 'object'
          ? row.allocation_json
          : parsePayload(row.allocation_json);
      const restored = restoreFromAllocation(payload, allocation, row.amount);
      await client.query(
        `UPDATE entitlement_snapshots
         SET payload_json = $3::jsonb, updated_at = CURRENT_TIMESTAMP
         WHERE app_id = $1 AND subject_id = $2`,
        [appId, subjectId, JSON.stringify(restored)]
      );
    }
    await client.query(
      `UPDATE credit_operations
       SET status = 'released', updated_at = CURRENT_TIMESTAMP
       WHERE operation_id = $1`,
      [operationId]
    );
    const after = await client.query(
      `SELECT payload_json, valid_until FROM entitlement_snapshots
       WHERE app_id = $1 AND subject_id = $2`,
      [appId, subjectId]
    );
    const payload = parsePayload(after.rows[0]?.payload_json);
    return {
      ok: true,
      status: 'released',
      credits: Number(payload.credits || 0) || 0,
      valid_until: after.rows[0]?.valid_until || null,
    };
  }
  const snap = await client.query(
    `SELECT payload_json, valid_until FROM entitlement_snapshots
     WHERE app_id = $1 AND subject_id = $2`,
    [appId, subjectId]
  );
  const payload = parsePayload(snap.rows[0]?.payload_json);
  return {
    ok: true,
    idempotent: true,
    status: 'released',
    credits: Number(payload.credits || 0) || 0,
    valid_until: snap.rows[0]?.valid_until || null,
  };
}

module.exports = {
  AI_PACK_SKU,
  classifyCatalogItemType,
  isOneShotAiPack,
  isComplementaryItem,
  mergeEntitlement,
  viewCredits,
  spendFromBuckets,
  restoreFromAllocation,
  nextOperationStatus,
  isSnapshotValid,
  ensureCreditOperationsTable,
  reserveCredits,
  confirmCredits,
  releaseCredits,
  canReserveCredits,
};
