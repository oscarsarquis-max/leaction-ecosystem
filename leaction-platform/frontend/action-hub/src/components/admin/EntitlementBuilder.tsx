'use client';

import { Plus, Trash2 } from 'lucide-react';

export type EntitlementRow = {
  key: string;
  value: string;
  kind: 'string' | 'number' | 'boolean';
};

/** Chaves EN legadas → PT (exibição e gravação canônica). */
const KEY_ALIASES: Record<string, string> = {
  tier: 'nivel',
  credits: 'creditos',
  subscription: 'assinatura',
  entitlements: 'direitos',
};

function canonicalizeKey(key: string): string {
  const k = key.trim();
  return KEY_ALIASES[k] || k;
}

export function entitlementsFromMeta(
  meta: Record<string, unknown> | null | undefined
): EntitlementRow[] {
  const source =
    meta && typeof meta.direitos === 'object' && meta.direitos
      ? (meta.direitos as Record<string, unknown>)
      : meta && typeof meta.entitlements === 'object' && meta.entitlements
        ? (meta.entitlements as Record<string, unknown>)
        : meta && typeof meta === 'object'
          ? meta
          : {};

  const rows: EntitlementRow[] = [];
  const seen = new Set<string>();
  for (const [rawKey, raw] of Object.entries(source)) {
    if (
      rawKey === 'entitlements' ||
      rawKey === 'direitos' ||
      rawKey === 'features_bullets'
    ) {
      continue;
    }
    const key = canonicalizeKey(rawKey);
    if (seen.has(key)) continue;
    seen.add(key);
    if (typeof raw === 'boolean') {
      rows.push({ key, value: raw ? 'true' : 'false', kind: 'boolean' });
    } else if (typeof raw === 'number') {
      rows.push({ key, value: String(raw), kind: 'number' });
    } else if (raw != null && typeof raw !== 'object') {
      rows.push({ key, value: String(raw), kind: 'string' });
    }
  }
  return rows.length
    ? rows
    : [{ key: 'creditos', value: '10', kind: 'number' }];
}

export function metaFromEntitlements(rows: EntitlementRow[]): Record<string, unknown> {
  const direitos: Record<string, unknown> = {};
  for (const row of rows) {
    const key = canonicalizeKey(row.key);
    if (!key) continue;
    if (row.kind === 'boolean') {
      direitos[key] = ['true', '1', 'yes', 'sim'].includes(
        row.value.trim().toLowerCase()
      );
    } else if (row.kind === 'number') {
      const n = Number(row.value);
      direitos[key] = Number.isFinite(n) ? n : 0;
    } else {
      direitos[key] = row.value;
    }
  }
  // Espelha creditos no topo — checkout/fulfill lê meta_json.creditos
  const out: Record<string, unknown> = { direitos };
  if (direitos.creditos != null) {
    out.creditos = direitos.creditos;
  }
  return out;
}

/** Rótulos amigáveis para cards do construtor. */
export function direitoLabel(key: string): string {
  const k = canonicalizeKey(key);
  const labels: Record<string, string> = {
    nivel: 'nível',
    creditos: 'créditos',
    assinatura: 'assinatura',
    aulas_simples: 'aulas simples',
    desafios_ativos: 'desafios ativos',
    licenses_granted: 'licenças concedidas',
    seats: 'vagas',
    licencas: 'licenças',
    vagas: 'vagas',
  };
  return labels[k] || k.replace(/_/g, ' ');
}

/** Valores amigáveis: -1 = ilimitado. */
export function direitoValueLabel(value: unknown): string {
  if (typeof value === 'boolean') return value ? 'sim' : 'não';
  if (typeof value === 'number' && value === -1) return 'ilimitados';
  if (value === '-1') return 'ilimitados';
  return String(value);
}

type Props = {
  rows: EntitlementRow[];
  onChange: (rows: EntitlementRow[]) => void;
};

export function EntitlementBuilder({ rows, onChange }: Props) {
  function updateRow(index: number, patch: Partial<EntitlementRow>) {
    onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-stone-800">Direitos do plano</p>
          <p className="text-xs text-stone-500">
            Defina o que o plano entrega (ex.: créditos, nível, assinatura).
          </p>
        </div>
        <button
          type="button"
          onClick={() =>
            onChange([...rows, { key: '', value: '', kind: 'string' }])
          }
          className="inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-stone-700 transition hover:bg-stone-50"
        >
          <Plus className="size-3.5" aria-hidden />
          Linha
        </button>
      </div>

      <div className="space-y-2">
        {rows.map((row, index) => (
          <div
            key={`ent-${index}`}
            className="grid grid-cols-1 gap-2 rounded-xl border border-stone-100 bg-stone-50/80 p-2 sm:grid-cols-[1fr_7rem_1fr_auto]"
          >
            <input
              value={row.key}
              onChange={(e) => updateRow(index, { key: e.target.value })}
              placeholder="chave (ex.: creditos)"
              className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm outline-none ring-emerald-200 focus:ring-2"
            />
            <select
              value={row.kind}
              onChange={(e) =>
                updateRow(index, {
                  kind: e.target.value as EntitlementRow['kind'],
                })
              }
              className="rounded-lg border border-stone-200 bg-white px-2 py-2 text-sm outline-none ring-emerald-200 focus:ring-2"
            >
              <option value="number">Número</option>
              <option value="boolean">Sim/Não</option>
              <option value="string">Texto</option>
            </select>
            {row.kind === 'boolean' ? (
              <select
                value={row.value === 'true' ? 'true' : 'false'}
                onChange={(e) => updateRow(index, { value: e.target.value })}
                className="rounded-lg border border-stone-200 bg-white px-2 py-2 text-sm outline-none ring-emerald-200 focus:ring-2"
              >
                <option value="true">sim</option>
                <option value="false">não</option>
              </select>
            ) : (
              <input
                value={row.value}
                onChange={(e) => updateRow(index, { value: e.target.value })}
                placeholder={row.kind === 'number' ? '10' : 'valor'}
                className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm outline-none ring-emerald-200 focus:ring-2"
              />
            )}
            <button
              type="button"
              onClick={() => onChange(rows.filter((_, i) => i !== index))}
              className="inline-flex items-center justify-center rounded-lg border border-stone-200 bg-white px-2 py-2 text-stone-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
              aria-label="Remover linha"
            >
              <Trash2 className="size-4" aria-hidden />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
