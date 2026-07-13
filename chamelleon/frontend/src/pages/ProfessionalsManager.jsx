import { useCallback, useEffect, useMemo, useState } from 'react';
import { PROFESSIONAL_ROLES, professionalRoleLabel } from '../constants/capacity';
import {
  createProfessional,
  deleteProfessional,
  listProfessionals,
  updateProfessional,
} from '../services/tdApi';

const EMPTY = {
  name: '',
  email: '',
  role: 'Dev',
  observations: '',
  is_active: true,
};

const DEFAULT_LICENSES = {
  used: 0,
  limit: 8,
  remaining: 8,
  plan_label: 'Plano Básico',
  at_limit: false,
};

export default function ProfessionalsManager() {
  const [items, setItems] = useState([]);
  const [licenses, setLicenses] = useState(DEFAULT_LICENSES);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ message: '', tone: 'success' });
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await listProfessionals();
      setItems(res.professionals || []);
      setLicenses({ ...DEFAULT_LICENSES, ...(res.licenses || {}) });
    } catch (err) {
      setError(err.message || 'Erro ao carregar o pool de talentos.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!toast.message) return undefined;
    const timer = setTimeout(() => setToast({ message: '', tone: 'success' }), 5000);
    return () => clearTimeout(timer);
  }, [toast.message]);

  const usagePct = useMemo(() => {
    const limit = Number(licenses.limit) || 8;
    const used = Number(licenses.used) || 0;
    return Math.min(100, Math.round((used / limit) * 100));
  }, [licenses]);

  const atLimit = Boolean(licenses.at_limit) || (licenses.used || 0) >= (licenses.limit || 8);
  const canCreate = !atLimit || Boolean(editingId);

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        role: form.role,
        observations: form.observations.trim(),
        is_active: Boolean(form.is_active),
      };
      if (!payload.name) {
        setError('Informe o nome do profissional.');
        return;
      }
      if (!editingId && !payload.email) {
        setError('Informe o e-mail corporativo.');
        return;
      }
      if (editingId) {
        const res = await updateProfessional(editingId, payload);
        if (res.licenses) setLicenses({ ...DEFAULT_LICENSES, ...res.licenses });
        setToast({ message: 'Profissional atualizado.', tone: 'success' });
      } else {
        if (atLimit) {
          setError(
            `Limite de licenças atingido (${licenses.limit}/${licenses.limit}). Faça upgrade do seu plano para adicionar mais profissionais.`,
          );
          return;
        }
        const res = await createProfessional(payload);
        if (res.licenses) setLicenses({ ...DEFAULT_LICENSES, ...res.licenses });
        setToast({
          message:
            res.message ||
            'Profissional registado! As credenciais de acesso foram enviadas para o e-mail informado.',
          tone: 'success',
        });
      }
      setForm(EMPTY);
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err.message || 'Erro ao salvar profissional.');
      if (err.status === 402) {
        await load();
      }
    } finally {
      setSaving(false);
    }
  }

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      name: item.name || '',
      email: item.email || '',
      role: item.role || 'Dev',
      observations: item.observations || '',
      is_active: item.is_active !== false,
    });
    setError('');
  }

  async function handleDeactivate(item) {
    if (!window.confirm(`Desativar ${item.name}? A licença será liberada.`)) return;
    try {
      const res = await deleteProfessional(item.id);
      if (res.licenses) setLicenses({ ...DEFAULT_LICENSES, ...res.licenses });
      setToast({ message: `${item.name} desativado(a).`, tone: 'success' });
      if (editingId === item.id) {
        setEditingId(null);
        setForm(EMPTY);
      }
      await load();
    } catch (err) {
      setError(err.message || 'Erro ao desativar.');
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Gestão Operacional
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Pool de Talentos</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Cadastre profissionais com e-mail corporativo. Cada cadastro consome uma licença e gera
          conta de acesso automaticamente.
        </p>
      </header>

      <section className="rounded-2xl border border-chameleon/20 bg-gradient-to-r from-chameleon/10 to-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wide text-chameleon-dark">
              Uso de licenças
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-900">
              Licenças utilizadas: {licenses.used ?? 0} de {licenses.limit ?? 8} (
              {licenses.plan_label || 'Plano Básico'})
            </p>
          </div>
          <p className="text-xs text-slate-500">
            {atLimit ? 'Limite atingido' : `${licenses.remaining ?? 0} disponível(is)`}
          </p>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className={`h-full rounded-full transition-all ${
              atLimit ? 'bg-amber-500' : 'bg-chameleon'
            }`}
            style={{ width: `${usagePct}%` }}
          />
        </div>
      </section>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Carregando…</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">
              {editingId ? 'Editar profissional' : 'Novo profissional'}
            </h2>
            {!editingId && atLimit && (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                Limite de licenças atingido. Desative um profissional ou faça upgrade do plano.
              </p>
            )}
            <label className="block text-xs font-semibold text-slate-600">
              Nome
              <input
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Nome completo"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              E-mail Corporativo
              <input
                required={!editingId}
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="nome@empresa.com"
                disabled={Boolean(editingId && form.email)}
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Cargo / papel
              <select
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {PROFESSIONAL_ROLES.map((role) => (
                  <option key={role.value} value={role.value}>
                    {role.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Observações (opcional)
              <textarea
                value={form.observations}
                onChange={(e) => setForm((f) => ({ ...f, observations: e.target.value }))}
                rows={3}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Notas internas, alocação preferencial, etc."
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-700 select-none">
              <input
                type="checkbox"
                className="sr-only"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
              />
              <span
                aria-hidden="true"
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-colors ${
                  form.is_active
                    ? 'border-[#16a34a] bg-[#16a34a]'
                    : 'border-slate-300 bg-white'
                }`}
              >
                {form.is_active && (
                  <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 text-white" fill="currentColor" aria-hidden="true">
                    <path d="M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z" />
                  </svg>
                )}
              </span>
              Ativo no pool
            </label>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saving || !canCreate}
                className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-50"
              >
                {saving
                  ? 'Salvando…'
                  : editingId
                    ? 'Atualizar'
                    : 'Adicionar Novo Profissional'}
              </button>
              {editingId && (
                <button
                  type="button"
                  onClick={() => {
                    setEditingId(null);
                    setForm(EMPTY);
                  }}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancelar
                </button>
              )}
            </div>
          </form>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-4 py-3">
              <h2 className="text-sm font-bold text-slate-800">
                Profissionais ({items.length})
              </h2>
            </div>
            <ul className="divide-y divide-slate-100">
              {items.length === 0 && (
                <li className="px-4 py-8 text-center text-sm text-slate-500">
                  Nenhum profissional cadastrado.
                </li>
              )}
              {items.map((item) => (
                <li
                  key={item.id}
                  className="flex items-start justify-between gap-3 px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{item.name}</p>
                    <p className="text-xs text-slate-500">
                      {professionalRoleLabel(item.role)}
                      {item.email ? ` · ${item.email}` : ''}
                      {!item.is_active && (
                        <span className="ml-2 rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-600">
                          Inativo
                        </span>
                      )}
                    </p>
                    {item.observations && (
                      <p className="mt-1 line-clamp-2 text-[11px] text-slate-400">
                        {item.observations}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      onClick={() => startEdit(item)}
                      className="text-xs font-semibold text-chameleon-dark hover:underline"
                    >
                      Editar
                    </button>
                    {item.is_active && (
                      <button
                        type="button"
                        onClick={() => handleDeactivate(item)}
                        className="text-xs font-semibold text-red-700 hover:underline"
                      >
                        Desativar
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {toast.message && (
        <div
          className={`fixed bottom-6 right-6 z-50 max-w-sm rounded-xl border px-4 py-3 text-sm shadow-lg ${
            toast.tone === 'error'
              ? 'border-red-200 bg-red-50 text-red-900'
              : 'border-emerald-200 bg-emerald-50 text-emerald-900'
          }`}
          role="status"
        >
          <div className="flex items-start gap-3">
            <p className="flex-1">{toast.message}</p>
            <button
              type="button"
              className="shrink-0 opacity-70 hover:opacity-100"
              onClick={() => setToast({ message: '', tone: 'success' })}
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
