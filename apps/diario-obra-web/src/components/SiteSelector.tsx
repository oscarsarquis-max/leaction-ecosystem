import { useEffect, useState } from 'react';
import { getDefaultTenantId, listSites } from '../api/rdoApi';
import type { ProjectSite } from '../types';
import NewSiteModal from './NewSiteModal';

interface Props {
  onSelect: (site: ProjectSite) => void;
}

export default function SiteSelector({ onSelect }: Props) {
  const [sites, setSites] = useState<ProjectSite[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const tenantId = getDefaultTenantId();

  async function loadSites() {
    setLoading(true);
    setError('');
    try {
      const data = await listSites(tenantId);
      setSites(data);
      if (data.length && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao carregar canteiros.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSites();
  }, []);

  const selectedSite = sites.find((s) => s.id === selectedId);

  return (
    <div className="flex flex-1 flex-col px-4 py-6">
      <div className="rounded-2xl border border-emerald-100 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900">Selecione o canteiro</h2>
        <p className="mt-1 text-sm text-slate-500">
          Escolha onde você está registrando o diário de hoje.
        </p>

        {loading ? (
          <p className="mt-6 text-center text-sm text-slate-500">Carregando canteiros…</p>
        ) : (
          <>
            <label className="mt-5 block">
              <span className="mb-2 block text-sm font-semibold uppercase tracking-wide text-emerald-800">
                Canteiro ativo
              </span>
              <select
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                className="w-full rounded-2xl border-2 border-emerald-600 bg-emerald-50 px-4 py-4 text-lg font-semibold text-slate-900 outline-none focus:ring-4 focus:ring-emerald-200"
              >
                <option value="" disabled>
                  {sites.length ? 'Selecione…' : 'Nenhum canteiro cadastrado'}
                </option>
                {sites.map((site) => (
                  <option key={site.id} value={site.id}>
                    {site.name}
                    {site.location ? ` — ${site.location}` : ''}
                  </option>
                ))}
              </select>
            </label>

            {selectedSite?.rt_engineer_name && (
              <p className="mt-3 text-sm text-slate-600">
                RT: <span className="font-medium">{selectedSite.rt_engineer_name}</span>
              </p>
            )}
          </>
        )}

        {error && (
          <div className="mt-4 space-y-2 rounded-xl border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-800">
            <p>{error}</p>
            <button
              type="button"
              onClick={loadSites}
              className="min-h-10 w-full rounded-lg bg-white px-3 py-2 font-semibold text-red-700 ring-1 ring-red-200"
            >
              Tentar novamente
            </button>
          </div>
        )}

        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="mt-5 w-full min-h-12 rounded-xl border-2 border-dashed border-emerald-400 bg-emerald-50 py-3 text-sm font-bold text-emerald-800"
        >
          + Novo Canteiro
        </button>

        <button
          type="button"
          disabled={!selectedId}
          onClick={() => selectedSite && onSelect(selectedSite)}
          className="mt-4 w-full min-h-14 rounded-2xl bg-emerald-600 text-lg font-bold text-white shadow-lg disabled:cursor-not-allowed disabled:opacity-50 active:bg-emerald-700"
        >
          Iniciar RDO do dia
        </button>
      </div>

      <NewSiteModal
        open={modalOpen}
        tenantId={tenantId}
        onClose={() => setModalOpen(false)}
        onCreated={(site) => {
          setSites((prev) => [...prev, site]);
          setSelectedId(site.id);
        }}
      />
    </div>
  );
}
