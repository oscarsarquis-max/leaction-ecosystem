'use client';

import { FormEvent, useEffect, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import { updateAdminApp, type AdminApp } from '@/lib/admin-api';

type Props = {
  open: boolean;
  token: string | null;
  app: AdminApp | null;
  onClose: () => void;
  onSuccess?: (message: string) => void;
};

export function AppEditModal({ open, token, app, onClose, onSuccess }: Props) {
  const [name, setName] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [active, setActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !app) return;
    setError(null);
    setName(app.name || '');
    setWebhookUrl(app.webhook_url || '');
    setActive(Boolean(app.active));
  }, [open, app]);

  if (!open || !app) return null;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!app) return;
    const targetId = app.app_id;
    setSaving(true);
    setError(null);
    try {
      if (!token) throw new Error('Sessão administrativa ausente.');
      await updateAdminApp(token, targetId, {
        name: name.trim(),
        webhook_url: webhookUrl.trim() || null,
        active,
      });
      onSuccess?.(
        `Aplicação ${targetId} atualizada. Webhook e status sincronizados.`
      );
      onClose();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ||
        (err as Error)?.message ||
        'Falha ao atualizar aplicação';
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
        aria-labelledby="app-edit-title"
        className="relative z-10 flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl sm:rounded-2xl"
      >
        <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
          <div>
            <h2
              id="app-edit-title"
              className="text-lg font-bold text-stone-900"
            >
              Integrar aplicação
            </h2>
            <p className="mt-0.5 font-mono text-xs text-stone-500">
              {app.app_id}
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
            <label className="block space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Nome
              </span>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
              />
            </label>

            <label className="block space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Webhook URL (créditos / avisos)
              </span>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="http://127.0.0.1:5010/api/webhooks/actionhub"
                className="w-full rounded-xl border border-stone-200 px-3 py-2.5 font-mono text-xs outline-none ring-orange-200 focus:ring-2"
              />
              <p className="text-[11px] text-stone-500">
                inove4us local: Flask em{' '}
                <code className="rounded bg-stone-100 px-1">:5010</code>
                /api/webhooks/actionhub
              </p>
            </label>

            <label className="flex items-center gap-2 text-sm text-stone-700">
              <input
                type="checkbox"
                checked={active}
                onChange={(e) => setActive(e.target.checked)}
                className="size-4 rounded border-stone-300 text-orange-600 focus:ring-orange-500"
              />
              Aplicação ativa (aceita checkout e webhooks)
            </label>

            {error ? (
              <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                {error}
              </p>
            ) : null}
          </div>

          <div className="flex justify-end gap-2 border-t border-stone-100 px-5 py-4">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="rounded-xl border border-stone-200 px-4 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50 disabled:opacity-60"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-orange-600 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-700 disabled:opacity-60"
            >
              {saving ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : null}
              Salvar integração
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
