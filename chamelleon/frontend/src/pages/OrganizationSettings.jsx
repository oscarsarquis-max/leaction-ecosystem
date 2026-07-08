import { useCallback, useEffect, useMemo, useState } from 'react';
import { getSession } from '../services/session';
import {
  createOperationalUser,
  listOperationalSites,
  listOperationalUsers,
  regenerateOperationalUserCode,
  updateOperationalUser,
} from '../services/operationalApi';
import { ROLE_LABELS } from '../config/rbac';
import { getIndustryLabels } from '../utils/industryLabels';

const EMPTY_USER = {
  name: '',
  email: '',
  password: '',
  system_role: 'executor',
  site_id: '',
};

const ROLE_OPTIONS = [
  { value: 'led', label: 'Lead (Gestor)' },
  { value: 'executor', label: 'Executor' },
  { value: 'consultor', label: 'Consultor' },
];

export default function OrganizationSettings() {
  const [sites, setSites] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [userForm, setUserForm] = useState(EMPTY_USER);
  const [editingUserId, setEditingUserId] = useState(null);
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [sitesRes, usersRes] = await Promise.all([
        listOperationalSites(),
        listOperationalUsers(),
      ]);
      setSites(sitesRes.sites || []);
      setUsers(usersRes.users || []);
    } catch (err) {
      setError(err.message || 'Erro ao carregar gestão de acessos.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const selectedUserSite = useMemo(
    () => sites.find((s) => s.id === userForm.site_id),
    [sites, userForm.site_id],
  );
  const userSiteLabels = useMemo(
    () => getIndustryLabels(selectedUserSite?.industry_type),
    [selectedUserSite],
  );

  async function handleSaveUser(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const payload = {
        name: userForm.name,
        email: userForm.email,
        password: userForm.password,
        system_role: userForm.system_role,
        site_id: userForm.site_id || null,
        operational_site_id: userForm.site_id || null,
        tenant_id: getSession()?.tenantId,
      };
      if (editingUserId) {
        const res = await updateOperationalUser(editingUserId, payload);
        setMessage(res.message || 'Utilizador atualizado.');
      } else {
        const res = await createOperationalUser(payload);
        setMessage(
          res.access_code
            ? `Utilizador criado. Código: ${res.access_code}`
            : res.message || 'Utilizador criado.',
        );
      }
      setUserForm(EMPTY_USER);
      setEditingUserId(null);
      await loadData();
    } catch (err) {
      setError(err.message || 'Erro ao salvar utilizador.');
    } finally {
      setSaving(false);
    }
  }

  async function handleRegenerateCode(userId) {
    try {
      const res = await regenerateOperationalUserCode(userId);
      setMessage(
        res.access_code ? `Novo código: ${res.access_code}` : res.message || 'Código regenerado.',
      );
      await loadData();
    } catch (err) {
      setError(err.message || 'Erro ao regenerar código.');
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Configurações da Organização</h1>
        <p className="mt-1 text-sm text-slate-600">
          Gestão de usuários e acessos do tenant. Unidades operacionais ficam em Área Operacional.
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {message}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Carregando…</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <form
            onSubmit={handleSaveUser}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-lg font-semibold text-slate-900">
              {editingUserId ? 'Editar acesso' : 'Novo utilizador'}
            </h2>
            <div className="mt-4 space-y-3">
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Nome</span>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={userForm.name}
                  onChange={(e) => setUserForm({ ...userForm, name: e.target.value })}
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">E-mail</span>
                <input
                  type="email"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={userForm.email}
                  onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Papel</span>
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={userForm.system_role}
                  onChange={(e) => setUserForm({ ...userForm, system_role: e.target.value })}
                >
                  {ROLE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">
                  {userSiteLabels.unit} vinculado(a)
                </span>
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={userForm.site_id}
                  onChange={(e) => setUserForm({ ...userForm, site_id: e.target.value })}
                >
                  <option value="">— Todas / central —</option>
                  {sites.map((site) => {
                    const siteLabels = getIndustryLabels(site.industry_type);
                    return (
                      <option key={site.id} value={site.id}>
                        {site.name} ({siteLabels.unit})
                      </option>
                    );
                  })}
                </select>
              </label>
              {userForm.system_role !== 'led' && (
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Senha inicial</span>
                  <input
                    type="password"
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                    value={userForm.password}
                    onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                    required={!editingUserId}
                  />
                </label>
              )}
            </div>
            <button
              type="submit"
              disabled={saving}
              className="mt-4 rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-60"
            >
              {saving ? 'Salvando…' : editingUserId ? 'Atualizar' : 'Criar e gerar acesso'}
            </button>
            {editingUserId && (
              <button
                type="button"
                className="ml-2 mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm"
                onClick={() => {
                  setEditingUserId(null);
                  setUserForm(EMPTY_USER);
                }}
              >
                Cancelar
              </button>
            )}
          </form>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Equipe vinculada</h2>
            <ul className="mt-4 divide-y divide-slate-100">
              {users.map((user) => (
                <li key={user.user_id} className="py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-slate-900">{user.name}</p>
                      <p className="text-xs text-slate-500">
                        {user.email} · {ROLE_LABELS[user.system_role] || user.system_role}
                      </p>
                      {user.operational_site_name && (
                        <p className="text-xs text-slate-500">📍 {user.operational_site_name}</p>
                      )}
                      {user.access_code && (
                        <p className="mt-1 font-mono text-sm text-chameleon-dark">{user.access_code}</p>
                      )}
                    </div>
                    <div className="flex flex-col gap-1 text-right">
                      <button
                        type="button"
                        className="text-xs text-chameleon-dark hover:underline"
                        onClick={() => {
                          setEditingUserId(user.user_id);
                          setUserForm({
                            name: user.name,
                            email: user.email,
                            password: '',
                            system_role: user.system_role,
                            site_id: user.operational_site_id || '',
                          });
                        }}
                      >
                        Editar
                      </button>
                      {user.system_role === 'led' && (
                        <button
                          type="button"
                          className="text-xs text-slate-600 hover:underline"
                          onClick={() => handleRegenerateCode(user.user_id)}
                        >
                          Novo código
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
