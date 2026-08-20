import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ROLE_CONSULTOR,
  ROLE_EXECUTOR,
  ROLE_LABELS,
  ROLE_LED,
  ROLE_SQUAD_MEMBER,
} from '../config/rbac';
import { listOperationalSites } from '../services/operationalApi';
import {
  createProfessional,
  deleteProfessional,
  listProfessionalRoles,
  listProfessionals,
  updateProfessional,
} from '../services/tdApi';
import ProfessionalCompliancePanel from '../components/ProfessionalCompliancePanel';

const ACCESS_OPTIONS = [
  { value: ROLE_LED, label: ROLE_LABELS[ROLE_LED] },
  { value: ROLE_CONSULTOR, label: ROLE_LABELS[ROLE_CONSULTOR] },
  { value: ROLE_EXECUTOR, label: ROLE_LABELS[ROLE_EXECUTOR] },
  { value: ROLE_SQUAD_MEMBER, label: ROLE_LABELS[ROLE_SQUAD_MEMBER] },
];

const ROLE_GROUP_LABELS = {
  squad: 'Papéis de Squad (Transformação Digital)',
  Construcao: 'Papéis Operacionais de Campo (Construção)',
};

function roleGroupLabel(group) {
  return ROLE_GROUP_LABELS[group] || `Papéis Operacionais de Campo (${group})`;
}

const EMPTY = {
  name: '',
  email: '',
  role: 'Dev',
  system_role: ROLE_SQUAD_MEMBER,
  operational_site_id: '',
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

function roleLabelFromCatalog(catalog, role) {
  return catalog.find((r) => r.value === role)?.label || role || '—';
}

function groupRoles(catalog) {
  const groups = new Map();
  for (const role of catalog) {
    const key = role.group || 'squad';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(role);
  }
  const ordered = [];
  if (groups.has('squad')) {
    ordered.push(['squad', groups.get('squad')]);
    groups.delete('squad');
  }
  for (const [key, items] of groups) {
    ordered.push([key, items]);
  }
  return ordered;
}

export default function ProfessionalsManager() {
  const [items, setItems] = useState([]);
  const [sites, setSites] = useState([]);
  const [roleCatalog, setRoleCatalog] = useState([]);
  const [licenses, setLicenses] = useState(DEFAULT_LICENSES);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ message: '', tone: 'success' });
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  /** Completar papel funcional de quem já tem acesso (sem Professional). */
  const [completingUser, setCompletingUser] = useState(null);
  const [saving, setSaving] = useState(false);
  const [complianceProfessional, setComplianceProfessional] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [res, sitesRes, rolesRes] = await Promise.all([
        listProfessionals(),
        listOperationalSites().catch(() => ({ sites: [] })),
        listProfessionalRoles().catch(() => ({ roles: [] })),
      ]);
      setItems(res.professionals || []);
      setLicenses({ ...DEFAULT_LICENSES, ...(res.licenses || {}) });
      setSites(sitesRes.sites || []);
      const roles = rolesRes.roles || [];
      setRoleCatalog(roles);
      setForm((prev) => {
        if (roles.length && !roles.some((r) => r.value === prev.role)) {
          return { ...prev, role: roles[0].value };
        }
        return prev;
      });
    } catch (err) {
      setError(err.message || 'Erro ao carregar a equipe.');
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
  const roleGroups = useMemo(() => groupRoles(roleCatalog), [roleCatalog]);
  const fieldRoleValues = useMemo(
    () => new Set(roleCatalog.filter((r) => r.group && r.group !== 'squad').map((r) => r.value)),
    [roleCatalog],
  );
  const accessLocked = Boolean(completingUser);

  function resetForm() {
    setEditingId(null);
    setCompletingUser(null);
    setForm({
      ...EMPTY,
      role: roleCatalog[0]?.value || 'Dev',
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        role: form.role,
        system_role: form.system_role,
        operational_site_id: form.operational_site_id || null,
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
        setToast({ message: 'Membro da equipe atualizado.', tone: 'success' });
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
          message: completingUser
            ? 'Papel funcional definido.'
            : res.message ||
              'Membro registado! As credenciais de acesso foram enviadas para o e-mail informado.',
          tone: 'success',
        });
      }
      resetForm();
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
    setCompletingUser(null);
    setEditingId(item.id);
    setForm({
      name: item.name || '',
      email: item.email || '',
      role: item.role || roleCatalog[0]?.value || 'Dev',
      system_role: item.system_role || ROLE_SQUAD_MEMBER,
      operational_site_id: item.operational_site_id || '',
      observations: item.observations || '',
      is_active: item.is_active !== false,
    });
    setError('');
  }

  function startCompleteFunctionalRole(item) {
    setEditingId(null);
    setCompletingUser({ user_id: item.user_id, email: item.email });
    setForm({
      name: item.name || '',
      email: item.email || '',
      role: roleCatalog[0]?.value || 'Dev',
      system_role: item.system_role || ROLE_SQUAD_MEMBER,
      operational_site_id: item.operational_site_id || '',
      observations: '',
      is_active: item.is_active !== false,
    });
    setError('');
  }

  async function handleDeactivate(item) {
    if (!item.id) return;
    if (!window.confirm(`Desativar ${item.name}? A licença será liberada.`)) return;
    try {
      const res = await deleteProfessional(item.id);
      if (res.licenses) setLicenses({ ...DEFAULT_LICENSES, ...res.licenses });
      setToast({ message: `${item.name} desativado(a).`, tone: 'success' });
      if (editingId === item.id) resetForm();
      await load();
    } catch (err) {
      setError(err.message || 'Erro ao desativar.');
    }
  }

  const formTitle = completingUser
    ? 'Definir papel funcional'
    : editingId
      ? 'Editar membro'
      : 'Novo membro';

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Gestão Operacional
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Meu Time</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Cadastre o papel funcional e o acesso ao sistema no mesmo formulário. Responsabilidade
          do gestor operacional.
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
            <p className="mt-0.5 text-[11px] text-slate-500">
              Conta todos os papéis, inclusive equipe de campo.
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
              {formTitle}
            </h2>
            {completingUser && (
              <p className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-900">
                Esta pessoa já tem acesso. Defina só o papel funcional — nome, e-mail e acesso
                permanecem como estão.
              </p>
            )}
            {!editingId && !completingUser && atLimit && (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                Limite de licenças atingido. Desative um membro ou faça upgrade do plano.
              </p>
            )}
            <label className="block text-xs font-semibold text-slate-600">
              Nome
              <input
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
                placeholder="Nome completo"
                readOnly={accessLocked}
                disabled={accessLocked}
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              E-mail Corporativo
              <input
                required={!editingId}
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
                placeholder="nome@empresa.com"
                disabled={Boolean(editingId && form.email) || accessLocked}
                readOnly={accessLocked}
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Papel funcional
              <select
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {roleGroups.map(([group, roles]) => (
                  <optgroup key={group} label={roleGroupLabel(group)}>
                    {roles.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Acesso ao sistema
              <select
                value={form.system_role}
                onChange={(e) => setForm((f) => ({ ...f, system_role: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
                disabled={accessLocked}
              >
                {ACCESS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Unidade operacional (opcional)
              <select
                value={form.operational_site_id}
                onChange={(e) =>
                  setForm((f) => ({ ...f, operational_site_id: e.target.value }))
                }
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
                disabled={accessLocked}
              >
                <option value="">— Não vinculado —</option>
                {sites.map((site) => (
                  <option key={site.id} value={site.id}>
                    {site.name}
                  </option>
                ))}
              </select>
            </label>
            {!completingUser && (
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
            )}
            {!completingUser && (
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
                Ativo na equipe
              </label>
            )}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saving || !canCreate}
                className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-50"
              >
                {saving
                  ? 'Salvando…'
                  : completingUser
                    ? 'Definir papel'
                    : editingId
                      ? 'Atualizar'
                      : 'Adicionar à equipe'}
              </button>
              {(editingId || completingUser) && (
                <button
                  type="button"
                  onClick={resetForm}
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
                Membros ({items.length})
              </h2>
            </div>
            <ul className="divide-y divide-slate-100">
              {items.length === 0 && (
                <li className="px-4 py-8 text-center text-sm text-slate-500">
                  Nenhum membro com acesso neste tenant.
                </li>
              )}
              {items.map((item) => {
                const key = item.id || item.user_id || item.email;
                const hasRole = item.has_functional_role !== false && Boolean(item.role);
                return (
                  <li
                    key={key}
                    className="flex items-start justify-between gap-3 px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{item.name}</p>
                      <p className="text-xs text-slate-500">
                        {hasRole
                          ? roleLabelFromCatalog(roleCatalog, item.role)
                          : 'Papel funcional: não definido'}
                        {item.email ? ` · ${item.email}` : ''}
                        {!item.is_active && (
                          <span className="ml-2 rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-600">
                            Inativo
                          </span>
                        )}
                      </p>
                      <p className="mt-0.5 text-[11px] text-slate-500">
                        Acesso:{' '}
                        {item.role_label ||
                          ROLE_LABELS[item.system_role] ||
                          item.system_role ||
                          '—'}
                        {item.operational_site_name
                          ? ` · ${item.operational_site_name}`
                          : ''}
                      </p>
                      <p className="mt-0.5 text-[11px] text-slate-400">
                        {item.system_role === ROLE_LED
                          ? item.access_code
                            ? `Código: ${item.access_code}`
                            : 'Acesso por código LA-*'
                          : item.has_password === false
                            ? 'Sem senha cadastrada'
                            : 'Acesso por senha'}
                      </p>
                      {item.observations && (
                        <p className="mt-1 line-clamp-2 text-[11px] text-slate-400">
                          {item.observations}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-2">
                      {hasRole ? (
                        <>
                          <button
                            type="button"
                            onClick={() => startEdit(item)}
                            className="text-xs font-semibold text-chameleon-dark hover:underline"
                          >
                            Editar
                          </button>
                          {fieldRoleValues.has(item.role) && item.id && (
                            <button
                              type="button"
                              onClick={() => setComplianceProfessional(item)}
                              className="text-xs font-semibold text-sky-700 hover:underline"
                            >
                              Conformidade
                            </button>
                          )}
                          {item.is_active && item.id && (
                            <button
                              type="button"
                              onClick={() => handleDeactivate(item)}
                              className="text-xs font-semibold text-red-700 hover:underline"
                            >
                              Desativar
                            </button>
                          )}
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => startCompleteFunctionalRole(item)}
                          className="text-xs font-semibold text-chameleon-dark hover:underline"
                        >
                          Definir papel funcional
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}

      {complianceProfessional && (
        <ProfessionalCompliancePanel
          professional={complianceProfessional}
          onClose={() => setComplianceProfessional(null)}
        />
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
