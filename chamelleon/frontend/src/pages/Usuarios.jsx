import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createAdminUser,
  deactivateAdminUser,
  getAdminUserAccess,
  listAdminTenantOptions,
  listAdminUsers,
  regenerateAdminUserCode,
  updateAdminUser,
} from '../services/api';
import { ROLE_LABELS } from '../config/rbac';

const EMPTY_FORM = {
  name: '',
  email: '',
  password: '',
  system_role: 'led',
  tenant_id: '',
  is_active: true,
};

const ROLE_OPTIONS = [
  { value: 'sysadmin', label: 'Administrador' },
  { value: 'led', label: 'Lead (Gestor)' },
  { value: 'consultor', label: 'Consultor' },
  { value: 'executor', label: 'Executor' },
];

export default function Usuarios() {
  const [users, setUsers] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [tenantFilter, setTenantFilter] = useState('');
  const [includeInactive, setIncludeInactive] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [accessInfo, setAccessInfo] = useState(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set('q', search.trim());
      if (roleFilter) params.set('system_role', roleFilter);
      if (tenantFilter) params.set('tenant_id', tenantFilter);
      params.set('incluir_inativos', includeInactive ? '1' : '0');
      const data = await listAdminUsers(params.toString());
      setUsers(data.users || []);
    } catch (err) {
      setError(err.message || 'Não foi possível carregar utilizadores.');
      setUsers([]);
    } finally {
      setLoading(false);
    }
  }, [search, roleFilter, tenantFilter, includeInactive]);

  useEffect(() => {
    listAdminTenantOptions()
      .then((data) => setTenants(data.tenants || []))
      .catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    const timer = setTimeout(loadUsers, 300);
    return () => clearTimeout(timer);
  }, [loadUsers]);

  const teamRole = useMemo(
    () => ['sysadmin', 'consultor', 'executor'].includes(form.system_role),
    [form.system_role],
  );

  function openCreate() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setAccessInfo(null);
    setModalOpen(true);
  }

  function openEdit(user) {
    setEditingId(user.user_id);
    setForm({
      name: user.name || '',
      email: user.email || '',
      password: '',
      system_role: user.system_role || 'led',
      tenant_id: user.tenant_id || '',
      is_active: user.is_active !== false,
    });
    setAccessInfo(null);
    setModalOpen(true);
  }

  async function showAccess(userId) {
    try {
      const data = await getAdminUserAccess(userId);
      setAccessInfo(data);
    } catch (err) {
      setError(err.message || 'Erro ao consultar credenciais.');
    }
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const payload = {
        name: form.name,
        email: form.email,
        system_role: form.system_role,
        tenant_id: form.tenant_id || undefined,
        is_active: form.is_active,
      };
      if (form.password) payload.password = form.password;

      if (editingId) {
        await updateAdminUser(editingId, payload);
        setMessage('Utilizador atualizado.');
      } else {
        const result = await createAdminUser(payload);
        setMessage(
          result.access_code
            ? `${result.message} Código (dev): ${result.access_code}`
            : result.message || 'Utilizador criado.',
        );
      }
      setModalOpen(false);
      loadUsers();
    } catch (err) {
      setError(err.message || 'Erro ao guardar utilizador.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(userId) {
    if (!window.confirm('Desativar este utilizador?')) return;
    try {
      await deactivateAdminUser(userId);
      setMessage('Utilizador desativado.');
      loadUsers();
    } catch (err) {
      setError(err.message || 'Erro ao desativar.');
    }
  }

  async function handleRegenerateCode(userId) {
    try {
      const result = await regenerateAdminUserCode(userId);
      setMessage(
        result.access_code
          ? `${result.message} Novo código (dev): ${result.access_code}`
          : result.message,
      );
      loadUsers();
    } catch (err) {
      setError(err.message || 'Erro ao reenviar código.');
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Gestão Global de Utilizadores</h2>
          <p className="mt-1 text-sm text-slate-500">
            Identidades e papéis de sistema — equivalente à gestão administrativa do legado.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark"
        >
          + Novo utilizador
        </button>
      </header>

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar nome ou e-mail..."
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        />
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="">Todos os papéis</option>
          {ROLE_OPTIONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
        <select
          value={tenantFilter}
          onChange={(e) => setTenantFilter(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="">Todas as empresas</option>
          {tenants.map((t) => (
            <option key={t.tenant_id} value={t.tenant_id}>
              {t.name}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
          />
          Incluir inativos
        </label>
      </div>

      {message && (
        <p className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
          {message}
        </p>
      )}
      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-100 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Nome</th>
              <th className="px-4 py-3">E-mail</th>
              <th className="px-4 py-3">Empresa</th>
              <th className="px-4 py-3">Papel</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  Carregando...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  Nenhum utilizador encontrado.
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.user_id} className="hover:bg-slate-50/80">
                  <td className="px-4 py-3 font-medium text-slate-800">{user.name}</td>
                  <td className="px-4 py-3 text-slate-600">{user.email}</td>
                  <td className="px-4 py-3 text-slate-600">{user.tenant_name || '—'}</td>
                  <td className="px-4 py-3">
                    {ROLE_LABELS[user.system_role] || user.system_role || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        user.is_active
                          ? 'rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800'
                          : 'rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-600'
                      }
                    >
                      {user.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => showAccess(user.user_id)}
                        className="text-xs text-chameleon hover:underline"
                      >
                        Acesso
                      </button>
                      <button
                        type="button"
                        onClick={() => openEdit(user)}
                        className="text-xs text-slate-600 hover:underline"
                      >
                        Editar
                      </button>
                      {user.has_lead_access && user.is_active && (
                        <button
                          type="button"
                          onClick={() => handleRegenerateCode(user.user_id)}
                          className="text-xs text-amber-700 hover:underline"
                        >
                          Novo LA-*
                        </button>
                      )}
                      {user.is_active && (
                        <button
                          type="button"
                          onClick={() => handleDeactivate(user.user_id)}
                          className="text-xs text-red-600 hover:underline"
                        >
                          Desativar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {accessInfo && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">Credenciais — {accessInfo.email}</p>
          {accessInfo.access_code && <p className="mt-1">Código LA-*: {accessInfo.access_code}</p>}
          {accessInfo.dev_password_hint && (
            <p className="mt-1">Senha dev: {accessInfo.dev_password_hint}</p>
          )}
          {accessInfo.has_password && !accessInfo.dev_password_hint && (
            <p className="mt-1">Possui senha definida (não exibida).</p>
          )}
        </div>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            onSubmit={handleSave}
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
          >
            <h3 className="text-lg font-bold text-slate-800">
              {editingId ? 'Editar utilizador' : 'Novo utilizador'}
            </h3>
            <div className="mt-4 space-y-3">
              <input
                required
                placeholder="Nome"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
              <input
                required
                type="email"
                placeholder="E-mail"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
              <select
                value={form.system_role}
                onChange={(e) => setForm((f) => ({ ...f, system_role: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
              {!teamRole && (
                <select
                  required
                  value={form.tenant_id}
                  onChange={(e) => setForm((f) => ({ ...f, tenant_id: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  <option value="">Empresa / tenant do lead</option>
                  {tenants.map((t) => (
                    <option key={t.tenant_id} value={t.tenant_id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              )}
              <input
                type="password"
                placeholder={editingId ? 'Nova senha (opcional)' : teamRole ? 'Senha *' : 'Senha (opcional para lead)'}
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
              {editingId && (
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                  />
                  Ativo
                </label>
              )}
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {saving ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
