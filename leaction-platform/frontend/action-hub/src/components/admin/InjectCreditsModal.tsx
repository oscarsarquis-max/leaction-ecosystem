'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import {
  injectAdminCredits,
  type AdminApp,
} from '@/lib/admin-api';

const REASON_OPTIONS = [
  'Feedback de Produto',
  'Reporte de Bug',
  'Cortesia Comercial',
  'Outros',
] as const;

type Props = {
  open: boolean;
  token: string | null;
  apps: AdminApp[];
  /** Se informado, o select de app fica desabilitado/oculto. */
  lockedAppId?: string;
  onClose: () => void;
  onSuccess?: (message: string) => void;
};

export function InjectCreditsModal({
  open,
  token,
  apps,
  lockedAppId = '',
  onClose,
  onSuccess,
}: Props) {
  const activeApps = useMemo(
    () => apps.filter((a) => a.active !== false),
    [apps]
  );

  const [appId, setAppId] = useState('');
  const [email, setEmail] = useState('');
  const [amount, setAmount] = useState('10');
  const [reasonOption, setReasonOption] = useState<string>(REASON_OPTIONS[0]);
  const [reasonOther, setReasonOther] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setEmail('');
    setAmount('10');
    setReasonOption(REASON_OPTIONS[0]);
    setReasonOther('');
    const preferred =
      lockedAppId ||
      activeApps[0]?.app_id ||
      apps[0]?.app_id ||
      '';
    setAppId(preferred);
  }, [open, lockedAppId, activeApps, apps]);

  if (!open) return null;

  const appLocked = Boolean(lockedAppId);
  const reason =
    reasonOption === 'Outros' ? reasonOther.trim() : reasonOption.trim();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (!token) throw new Error('Sessão administrativa ausente.');
      const subject = email.trim().toLowerCase();
      const credits = Number.parseInt(String(amount), 10);
      if (!subject || !subject.includes('@')) {
        throw new Error('Informe um e-mail de usuário válido.');
      }
      if (!appId.trim()) {
        throw new Error('Selecione a aplicação.');
      }
      if (!Number.isFinite(credits) || credits <= 0) {
        throw new Error('Quantidade de créditos deve ser um inteiro positivo.');
      }
      if (!reason) {
        throw new Error(
          reasonOption === 'Outros'
            ? 'Descreva o motivo em Outros.'
            : 'Informe o motivo da injeção.'
        );
      }

      await injectAdminCredits(token, {
        app_id: appId.trim(),
        subject_id: subject,
        amount: credits,
        reason,
      });

      onSuccess?.(
        'Créditos injetados com sucesso! O webhook foi enfileirado.'
      );
      onClose();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ||
        (err as Error)?.message ||
        'Falha ao injetar créditos';
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
        aria-labelledby="inject-credits-title"
        className="relative z-10 flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl sm:rounded-2xl"
      >
        <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
          <div>
            <h2
              id="inject-credits-title"
              className="text-lg font-bold text-stone-900"
            >
              Injeção Manual de Créditos (Bounty/Cortesia)
            </h2>
            <p className="mt-0.5 text-xs text-stone-500">
              Soma créditos no Hub e enfileira CREDITS_GRANTED para a app.
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
                E-mail do Usuário
              </span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="usuario@empresa.com"
                className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
              />
            </label>

            <label className="block space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Quantidade de Créditos
              </span>
              <input
                type="number"
                min={1}
                step={1}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
                className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
              />
            </label>

            <label className="block space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Motivo
              </span>
              <select
                value={reasonOption}
                onChange={(e) => setReasonOption(e.target.value)}
                className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
              >
                {REASON_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </label>

            {reasonOption === 'Outros' ? (
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                  Descreva o motivo
                </span>
                <input
                  type="text"
                  value={reasonOther}
                  onChange={(e) => setReasonOther(e.target.value)}
                  required
                  placeholder="Ex.: Compensação por indisponibilidade"
                  className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
                />
              </label>
            ) : null}

            {appLocked ? (
              <input type="hidden" value={appId} readOnly />
            ) : (
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                  ID da Aplicação
                </span>
                <select
                  value={appId}
                  onChange={(e) => setAppId(e.target.value)}
                  required
                  className="w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm outline-none ring-orange-200 focus:ring-2"
                >
                  {activeApps.length === 0 ? (
                    <option value="">Nenhuma app ativa</option>
                  ) : (
                    activeApps.map((app) => (
                      <option key={app.app_id} value={app.app_id}>
                        {app.name} ({app.app_id})
                      </option>
                    ))
                  )}
                </select>
              </label>
            )}

            {appLocked && appId ? (
              <p className="rounded-xl border border-stone-100 bg-stone-50 px-3 py-2 text-xs text-stone-600">
                Aplicação:{' '}
                <span className="font-mono font-semibold text-stone-800">
                  {appId}
                </span>
              </p>
            ) : null}

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
              disabled={saving}
              className="rounded-xl px-4 py-2 text-sm font-semibold text-stone-600 transition hover:bg-stone-100 disabled:opacity-60"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:opacity-60"
            >
              {saving ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : null}
              Injetar Créditos
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
