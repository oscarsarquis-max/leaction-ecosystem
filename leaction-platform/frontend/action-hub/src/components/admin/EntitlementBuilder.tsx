'use client';

import { Plus, Trash2 } from 'lucide-react';

export type EntitlementRow = {
  key: string;
  value: string;
  kind: 'string' | 'number' | 'boolean';
};

export function entitlementsFromMeta(
  meta: Record<string, unknown> | null | undefined
): EntitlementRow[] {
  const source =
    meta && typeof meta.entitlements === 'object' && meta.entitlements
      ? (meta.entitlements as Record<string, unknown>)
      : meta && typeof meta === 'object'
        ? meta
        : {};

  const rows: EntitlementRow[] = [];
  for (const [key, raw] of Object.entries(source)) {
    if (key === 'entitlements' || key === 'features_bullets') continue;
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
    : [{ key: 'credits', value: '10', kind: 'number' }];
}

export function metaFromEntitlements(rows: EntitlementRow[]): Record<string, unknown> {
  const entitlements: Record<string, unknown> = {};
  for (const row of rows) {
    const key = row.key.trim();
    if (!key) continue;
    if (row.kind === 'boolean') {
      entitlements[key] = ['true', '1', 'yes', 'sim'].includes(
        row.value.trim().toLowerCase()
      );
    } else if (row.kind === 'number') {
      const n = Number(row.value);
      entitlements[key] = Number.isFinite(n) ? n : 0;
    } else {
      entitlements[key] = row.value;
    }
  }
  return { entitlements };
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
          <p className="text-sm font-semibold text-stone-800">Features / Entitlements</p>
          <p className="text-xs text-stone-500">
            Defina o que o plano entrega (ex.: credits, premium_features).
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
              placeholder="chave (ex: credits)"
              className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm outline-none ring-orange-200 focus:ring-2"
            />
            <select
              value={row.kind}
              onChange={(e) =>
                updateRow(index, {
                  kind: e.target.value as EntitlementRow['kind'],
                })
              }
              className="rounded-lg border border-stone-200 bg-white px-2 py-2 text-sm outline-none ring-orange-200 focus:ring-2"
            >
              <option value="number">Número</option>
              <option value="boolean">Boolean</option>
              <option value="string">Texto</option>
            </select>
            {row.kind === 'boolean' ? (
              <select
                value={row.value === 'true' ? 'true' : 'false'}
                onChange={(e) => updateRow(index, { value: e.target.value })}
                className="rounded-lg border border-stone-200 bg-white px-2 py-2 text-sm outline-none ring-orange-200 focus:ring-2"
              >
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            ) : (
              <input
                value={row.value}
                onChange={(e) => updateRow(index, { value: e.target.value })}
                placeholder={row.kind === 'number' ? '10' : 'valor'}
                className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm outline-none ring-orange-200 focus:ring-2"
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
