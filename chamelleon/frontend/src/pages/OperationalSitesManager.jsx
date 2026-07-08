import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createOperationalSite,
  deleteOperationalSite,
  listOperationalSites,
  listOperationalUsers,
  syncOperationalSiteSatellite,
  updateOperationalSite,
} from '../services/operationalApi';
import {
  getIndustryLabels,
  getLabelsFromSites,
  INDUSTRY_TYPE_OPTIONS,
} from '../utils/industryLabels';

const EMPTY_SITE = {
  name: '',
  location: '',
  industry_type: 'Construcao',
  manager_id: '',
};

export default function OperationalSitesManager() {
  const [sites, setSites] = useState([]);
  const [managers, setManagers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [siteForm, setSiteForm] = useState(EMPTY_SITE);
  const [editingSiteId, setEditingSiteId] = useState(null);
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
      setManagers(
        (usersRes.users || []).filter((u) => u.system_role === 'led' && u.is_active !== false),
      );
    } catch (err) {
      setError(err.message || 'Erro ao carregar unidades operacionais.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const listLabels = useMemo(() => getLabelsFromSites(sites), [sites]);
  const formLabels = useMemo(
    () => getIndustryLabels(siteForm.industry_type),
    [siteForm.industry_type],
  );

  async function handleSaveSite(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const payload = {
        ...siteForm,
        manager_id: siteForm.manager_id || null,
      };
      const labels = getIndustryLabels(payload.industry_type);
      if (editingSiteId) {
        await updateOperationalSite(editingSiteId, payload);
        setMessage(`${labels.unit} atualizado(a).`);
      } else {
        const res = await createOperationalSite(payload);
        if (res.site?.sync_warning) {
          setMessage(res.site.sync_warning);
        } else if (res.site?.satellite_site_id) {
          setMessage(`${labels.unit} criado(a) e sincronizado(a) com o Diário de Obra.`);
        } else {
          setMessage(`${labels.unit} criado(a) com sucesso.`);
        }
      }
      setSiteForm(EMPTY_SITE);
      setEditingSiteId(null);
      await loadData();
    } catch (err) {
      setError(err.message || 'Erro ao salvar unidade.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivateSite(site) {
    const labels = getIndustryLabels(site?.industry_type);
    if (!window.confirm(`Desativar este(a) ${labels.unit.toLowerCase()}?`)) return;
    try {
      await deleteOperationalSite(site.id);
      setMessage(`${labels.unit} desativado(a).`);
      await loadData();
    } catch (err) {
      setError(err.message || `Erro ao desativar ${labels.unit.toLowerCase()}.`);
    }
  }

  async function handleSyncSatellite(siteId) {
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const res = await syncOperationalSiteSatellite(siteId);
      setMessage(res.site?.message || 'Sincronização concluída.');
      await loadData();
    } catch (err) {
      setError(err.message || 'Falha ao sincronizar com o Diário de Obra.');
      await loadData();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Gestão de Unidades</h1>
        <p className="mt-1 text-sm text-slate-600">
          Cadastre e mantenha {listLabels.unitPlural.toLowerCase()} do tenant. Os rótulos
          adaptam-se ao setor de cada unidade.
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
            onSubmit={handleSaveSite}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-lg font-semibold text-slate-900">
              {editingSiteId ? `Editar ${formLabels.unit}` : `Novo(a) ${formLabels.unit}`}
            </h2>
            <div className="mt-4 space-y-3">
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Setor (indústria)</span>
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={siteForm.industry_type}
                  onChange={(e) => setSiteForm({ ...siteForm, industry_type: e.target.value })}
                >
                  {INDUSTRY_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <span className="mt-1 block text-xs text-slate-500">
                  Define os rótulos da interface (ex.: Canteiro, Loja, Squad).
                </span>
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">{formLabels.nameColumn}</span>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={siteForm.name}
                  onChange={(e) => setSiteForm({ ...siteForm, name: e.target.value })}
                  required
                  placeholder={`Ex.: ${formLabels.unit} Centro`}
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Localização</span>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={siteForm.location}
                  onChange={(e) => setSiteForm({ ...siteForm, location: e.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">{formLabels.manager}</span>
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  value={siteForm.manager_id}
                  onChange={(e) => setSiteForm({ ...siteForm, manager_id: e.target.value })}
                >
                  <option value="">— Não definido —</option>
                  {managers.map((u) => (
                    <option key={u.user_id} value={u.user_id}>
                      {u.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-60"
              >
                {saving
                  ? 'Salvando…'
                  : editingSiteId
                    ? 'Atualizar'
                    : `Criar ${formLabels.unit.toLowerCase()}`}
              </button>
              {editingSiteId && (
                <button
                  type="button"
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm"
                  onClick={() => {
                    setEditingSiteId(null);
                    setSiteForm(EMPTY_SITE);
                  }}
                >
                  Cancelar
                </button>
              )}
            </div>
          </form>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">
              {listLabels.unitPlural} cadastrado(a)s
            </h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[420px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-1 py-2 font-semibold">{listLabels.nameColumn}</th>
                    <th className="px-1 py-2 font-semibold">Setor</th>
                    <th className="px-1 py-2 font-semibold">Status</th>
                    <th className="px-1 py-2 font-semibold text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sites.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-4 text-slate-500">
                        Nenhum(a) {listLabels.unit.toLowerCase()} cadastrado(a).
                      </td>
                    </tr>
                  )}
                  {sites.map((site) => {
                    const siteLabels = getIndustryLabels(site.industry_type);
                    return (
                      <tr key={site.id}>
                        <td className="px-1 py-3 align-top">
                          <p className="font-medium text-slate-900">{site.name}</p>
                          {site.location && (
                            <p className="text-xs text-slate-500">{site.location}</p>
                          )}
                        </td>
                        <td className="px-1 py-3 align-top text-xs text-slate-600">
                          {site.industry_type || '—'}
                          <p className="mt-0.5 text-slate-400">{siteLabels.unit}</p>
                        </td>
                        <td className="px-1 py-3 align-top text-xs">
                          {site.satellite_site_id ? (
                            <span className="text-emerald-700">
                              Satélite ({String(site.satellite_site_id).slice(0, 8)}…)
                            </span>
                          ) : String(site.industry_type || '')
                              .toLowerCase()
                              .startsWith('constr') ? (
                            <span className="text-amber-700">Pendente sync</span>
                          ) : (
                            <span className="text-slate-500">Hub only</span>
                          )}
                        </td>
                        <td className="px-1 py-3 align-top">
                          <div className="flex flex-col items-end gap-1">
                            <button
                              type="button"
                              className="text-xs font-medium text-chameleon-dark hover:underline"
                              onClick={() => {
                                setEditingSiteId(site.id);
                                setSiteForm({
                                  name: site.name,
                                  location: site.location || '',
                                  industry_type: site.industry_type,
                                  manager_id: site.manager_id || '',
                                });
                              }}
                            >
                              Editar
                            </button>
                            {!site.satellite_site_id &&
                              String(site.industry_type || '')
                                .toLowerCase()
                                .startsWith('constr') && (
                                <button
                                  type="button"
                                  className="text-xs font-medium text-sky-700 hover:underline"
                                  disabled={saving}
                                  onClick={() => handleSyncSatellite(site.id)}
                                >
                                  Sincronizar satélite
                                </button>
                              )}
                            <button
                              type="button"
                              className="text-xs font-medium text-red-600 hover:underline"
                              onClick={() => handleDeactivateSite(site)}
                            >
                              Desativar
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
