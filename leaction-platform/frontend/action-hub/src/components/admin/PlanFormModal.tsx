'use client';

import { FormEvent, useEffect, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import {
  type CatalogPlan,
  type CatalogPlanType,
  type PlanUpsertBody,
} from '@/lib/admin-api';
import {
  EntitlementBuilder,
  entitlementsFromMeta,
  metaFromEntitlements,
  type EntitlementRow,
} from '@/components/admin/EntitlementBuilder';

type Props = {
  open: boolean;
  appId: string;
  plan?: CatalogPlan | null;
  onClose: () => void;
  onSave: (body: PlanUpsertBody & { app_id: string }) => Promise<void>;
};

const TYPE_OPTIONS: Array<{ value: CatalogPlanType; label: string }> = [
  { value: 'plan', label: 'Assinatura Mensal' },
  { value: 'credit_pack', label: 'Pacote de Créditos' },
];

function featuresToBullets(features: unknown): string {
  if (!Array.isArray(features)) return '';
  return features
    .map((f) => (typeof f === 'string' ? f : JSON.stringify(f)))
    .join('\n');
}

export function PlanFormModal({ open, appId, plan, onClose, onSave }: Props) {
  const editing = Boolean(plan?.id);
  const [name, setName] = useState('');
  const [sku, setSku] = useState('');
  const [type, setType] = useState<CatalogPlanType>('credit_pack');
  const [price, setPrice] = useState('0');
  const [active, setActive] = useState(true);
  const [bullets, setBullets] = useState('');
  const [rows, setRows] = useState<EntitlementRow[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (plan) {
      setName(plan.name || '');
      setSku(plan.sku || '');
      setType(
        plan.type === 'plan' || plan.type === 'credit_pack'
          ? plan.type
          : 'credit_pack'
      );
      setPrice(String(plan.price ?? 0));
      setActive(Boolean(plan.active));
      setBullets(featuresToBullets(plan.features));
      setRows(entitlementsFromMeta(plan.meta_json));
    } else {
      setName('');
      setSku('');
      setType('credit_pack');
      setPrice('29.90');
      setActive(true);
      setBullets('');
      setRows([{ key: 'credits', value: '10', kind: 'number' }]);
    }
  }, [open, plan]);

  if (!open) return null;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const priceNum = Number(String(price).replace(',', '.'));
      if (!name.trim() || !sku.trim()) {
        throw new Error('Nome e SKU são obrigatórios.');
      }
      if (!Number.isFinite(priceNum) || priceNum < 0) {
        throw new Error('Preço inválido.');
      }
      const features = bullets
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      const meta_json = metaFromEntitlements(rows);
      await onSave({
        app_id: appId,
        name: name.trim(),
        sku: sku.trim(),
        type,
        price: priceNum,
        currency: 'BRL',
        features,
        meta_json,
        active,
      });
      onClose();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ||
        (err as Error)?.message ||
        'Falha ao salvar plano';
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-stone-950/40 p-0 sm:items-center sm:p-4">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Fechar"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="plan-form-title"
        className="relative z-10 flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl sm:rounded-2xl"
      >
        <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
          <div>
            <h2 id="plan-form-title" className="text-lg font-bold text-stone-900">
              {editing ? 'Editar plano' : 'Novo plano / pacote'}
            </h2>
            <p className="text-xs text-stone-500">
              App: <span className="font-mono">{appId}</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-stone-500 transition hover:bg-stone-100 hover:text-stone-800"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <div className="space-y-4 overflow-y-auto px-5 py-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block space-y-1.5 sm:col-span-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                  Nome do plano
                </span>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
                  placeholder="Ex.: Pacote 100 créditos"
                />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                  SKU
                </span>
                <input
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                  required
                  disabled={editing}
                  className="w-full rounded-xl border border-stone-200 px-3 py-2.5 font-mono text-sm outline-none ring-orange-200 focus:ring-2 disabled:bg-stone-50"
                  placeholder="INOVE4US_CREDITS_100"
                />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                  Tipo
                </span>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value as CatalogPlanType)}
                  className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
                >
                  {TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                  Preço (BRL)
                </span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  required
                  className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
                />
              </label>
              <label className="flex items-center gap-2 self-end rounded-xl border border-stone-200 px-3 py-2.5 text-sm">
                <input
                  type="checkbox"
                  checked={active}
                  onChange={(e) => setActive(e.target.checked)}
                  className="size-4 rounded border-stone-300 text-orange-600 focus:ring-orange-500"
                />
                <span className="font-medium text-stone-700">Ativo na vitrine</span>
              </label>
            </div>

            <label className="block space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Features (uma por linha)
              </span>
              <textarea
                value={bullets}
                onChange={(e) => setBullets(e.target.value)}
                rows={3}
                className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
                placeholder={'Acesso premium\nSuporte prioritário'}
              />
            </label>

            <EntitlementBuilder rows={rows} onChange={setRows} />

            {error ? (
              <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                {error}
              </div>
            ) : null}
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-stone-100 px-5 py-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl px-4 py-2 text-sm font-semibold text-stone-600 transition hover:bg-stone-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:opacity-60"
            >
              {saving ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
              {editing ? 'Salvar alterações' : 'Criar plano'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
