import { useCallback, useEffect, useMemo, useState } from 'react';
import { listOperationalUsers } from '../../services/operationalApi';
import {
  convertRecurrenceSignal,
  dismissRecurrenceSignal,
  listCorrectiveActionProjects,
  listRecurrenceSignals,
  markRecurrenceSignalSeen,
  updateCorrectiveActionProject,
} from '../../services/complianceApi';

const ACTIVE_SIGNAL_STATUSES = new Set(['Novo', 'Visto']);

export default function RecurrenceAndCapPanel({
  siteFilter,
  subTab,
  onError,
  onToast,
}) {
  const [signals, setSignals] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSignalId, setSelectedSignalId] = useState(null);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [convertOpen, setConvertOpen] = useState(false);
  const [users, setUsers] = useState([]);
  const [convertForm, setConvertForm] = useState({
    title: '',
    owner_user_id: '',
    due_date: '',
    root_cause_notes: '',
  });
  const [busy, setBusy] = useState(false);
  const [closeEvidence, setCloseEvidence] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [sigRes, capRes] = await Promise.all([
        listRecurrenceSignals({
          operationalSiteId: siteFilter || undefined,
        }),
        listCorrectiveActionProjects(),
      ]);
      setSignals(sigRes.recurrence_signals || []);
      let caps = capRes.corrective_action_projects || [];
      if (siteFilter) {
        caps = caps.filter((p) => p.operational_site_id === siteFilter);
      }
      setProjects(caps);
    } catch (err) {
      onError?.(err.message || 'Erro ao carregar recorrências.');
    } finally {
      setLoading(false);
    }
  }, [siteFilter, onError]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    listOperationalUsers()
      .then((res) => setUsers(res.users || []))
      .catch(() => setUsers([]));
  }, []);

  const activeSignals = useMemo(
    () => signals.filter((s) => ACTIVE_SIGNAL_STATUSES.has(s.status)),
    [signals],
  );

  const selectedSignal = useMemo(
    () => signals.find((s) => s.id === selectedSignalId) || null,
    [signals, selectedSignalId],
  );

  const selectedProject = useMemo(
    () => projects.find((p) => p.id === selectedProjectId) || null,
    [projects, selectedProjectId],
  );

  async function openSignal(signal) {
    setSelectedSignalId(signal.id);
    if (signal.status !== 'Novo') return;
    try {
      const res = await markRecurrenceSignalSeen(signal.id);
      const updated = res.recurrence_signal || res;
      setSignals((prev) => prev.map((s) => (s.id === signal.id ? { ...s, ...updated } : s)));
    } catch {
      /* best-effort silencioso */
    }
  }

  async function handleDismiss(signal) {
    if (!window.confirm('Dispensar este sinal de recorrência?')) return;
    setBusy(true);
    try {
      await dismissRecurrenceSignal(signal.id);
      onToast?.('Sinal dispensado.');
      setSelectedSignalId(null);
      await load();
    } catch (err) {
      onError?.(err.message || 'Erro ao dispensar.');
    } finally {
      setBusy(false);
    }
  }

  function openConvert(signal) {
    setSelectedSignalId(signal.id);
    setConvertForm({
      title: `Ação corretiva — ${signal.category}${signal.operational_site_name ? ` (${signal.operational_site_name})` : ''}`,
      owner_user_id: '',
      due_date: '',
      root_cause_notes: '',
    });
    setConvertOpen(true);
  }

  async function submitConvert(event) {
    event.preventDefault();
    if (!selectedSignalId) return;
    setBusy(true);
    try {
      await convertRecurrenceSignal(selectedSignalId, convertForm);
      onToast?.('Projeto de ação corretiva aberto.');
      setConvertOpen(false);
      setSelectedSignalId(null);
      await load();
    } catch (err) {
      onError?.(err.message || 'Erro ao converter sinal.');
    } finally {
      setBusy(false);
    }
  }

  async function concludeProject(project) {
    setBusy(true);
    try {
      await updateCorrectiveActionProject(project.id, {
        status: 'Concluido',
        closed_evidence: closeEvidence.trim(),
      });
      onToast?.('Projeto concluído.');
      setCloseEvidence('');
      setSelectedProjectId(null);
      await load();
    } catch (err) {
      onError?.(err.message || 'Erro ao concluir projeto.');
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-500">
        Carregando…
      </div>
    );
  }

  if (subTab === 'projects') {
    return (
      <div className="space-y-4">
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Título</th>
                <th className="px-3 py-2">Categoria</th>
                <th className="px-3 py-2">Canteiro</th>
                <th className="px-3 py-2">Dono</th>
                <th className="px-3 py-2">Prazo</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {projects.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-slate-500">
                    Nenhum projeto de ação corretiva.
                  </td>
                </tr>
              )}
              {projects.map((project) => (
                <tr
                  key={project.id}
                  className={`cursor-pointer hover:bg-slate-50 ${
                    selectedProjectId === project.id ? 'bg-slate-50' : ''
                  }`}
                  onClick={() => {
                    setSelectedProjectId(project.id);
                    setCloseEvidence(project.closed_evidence || '');
                  }}
                >
                  <td className="px-3 py-3 font-medium text-slate-800">{project.title}</td>
                  <td className="px-3 py-3 text-xs">{project.category}</td>
                  <td className="px-3 py-3 text-xs text-slate-600">
                    {project.operational_site_name || '—'}
                  </td>
                  <td className="px-3 py-3 text-xs">{project.owner_name || '—'}</td>
                  <td className="px-3 py-3 text-xs">{project.due_date || '—'}</td>
                  <td className="px-3 py-3 text-xs">{project.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedProject && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">{selectedProject.title}</h3>
            <p className="mt-1 text-xs text-slate-500">
              {selectedProject.category} · {selectedProject.operational_site_name || 'Sem canteiro'} ·{' '}
              {selectedProject.status}
            </p>
            {selectedProject.root_cause_notes && (
              <p className="mt-3 text-sm text-slate-700 whitespace-pre-wrap">
                {selectedProject.root_cause_notes}
              </p>
            )}
            <div className="mt-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                NCs vinculadas
              </p>
              <ul className="mt-1 space-y-1 text-sm text-slate-700">
                {(selectedProject.linked_non_conformities || []).map((nc) => (
                  <li key={nc.id}>
                    {nc.title}{' '}
                    <span className="text-xs text-slate-400">({nc.status})</span>
                  </li>
                ))}
                {(selectedProject.linked_non_conformities || []).length === 0 && (
                  <li className="text-slate-400">Nenhuma NC vinculada.</li>
                )}
              </ul>
            </div>
            {selectedProject.status !== 'Concluido' && (
              <div className="mt-4 space-y-2 border-t border-slate-100 pt-3">
                <label className="block text-xs font-medium text-slate-600">
                  Evidência de conclusão
                  <textarea
                    className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                    rows={3}
                    value={closeEvidence}
                    onChange={(e) => setCloseEvidence(e.target.value)}
                    placeholder="Descreva a evidência da ação corretiva…"
                  />
                </label>
                <button
                  type="button"
                  disabled={busy || !closeEvidence.trim()}
                  onClick={() => concludeProject(selectedProject)}
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
                >
                  Concluir projeto
                </button>
              </div>
            )}
            {selectedProject.status === 'Concluido' && selectedProject.closed_evidence && (
              <p className="mt-3 text-sm text-slate-600">
                <span className="font-medium">Evidência:</span> {selectedProject.closed_evidence}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
              <th className="px-3 py-2">Categoria</th>
              <th className="px-3 py-2">Canteiro</th>
              <th className="px-3 py-2">Ocorrências</th>
              <th className="px-3 py-2">Período</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Contexto normativo</th>
              <th className="px-3 py-2">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {activeSignals.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-slate-500">
                  Nenhum sinal de recorrência ativo (padrão categoria + canteiro).
                </td>
              </tr>
            )}
            {activeSignals.map((signal) => (
              <tr
                key={signal.id}
                className={`cursor-pointer hover:bg-slate-50 ${
                  selectedSignalId === signal.id ? 'bg-amber-50/60' : ''
                }`}
                onClick={() => openSignal(signal)}
              >
                <td className="px-3 py-3 font-medium text-slate-800">{signal.category}</td>
                <td className="px-3 py-3 text-xs text-slate-600">
                  {signal.operational_site_name || '—'}
                </td>
                <td className="px-3 py-3 text-xs">{signal.occurrence_count}</td>
                <td className="px-3 py-3 text-xs text-slate-600">
                  {signal.window_start} → {signal.window_end}
                </td>
                <td className="px-3 py-3 text-xs">{signal.status}</td>
                <td className="px-3 py-3 text-xs text-slate-500">
                  {signal.norm_context || '—'}
                </td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-1" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => openConvert(signal)}
                      className="rounded border border-slate-300 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-100"
                    >
                      Abrir projeto
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleDismiss(signal)}
                      className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-500 hover:bg-slate-50"
                    >
                      Dispensar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedSignal && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 text-sm">
          <p className="font-semibold text-slate-900">
            Padrão identificado: {selectedSignal.category}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {selectedSignal.occurrence_count} ocorrências no período{' '}
            {selectedSignal.window_start} – {selectedSignal.window_end}
            {selectedSignal.norm_context ? ` · ${selectedSignal.norm_context}` : ''}
          </p>
          <ul className="mt-2 space-y-1 text-xs text-slate-700">
            {(selectedSignal.linked_non_conformities || []).map((nc) => (
              <li key={nc.id}>
                {nc.title} <span className="text-slate-400">({nc.status})</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {convertOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4">
          <form
            onSubmit={submitConvert}
            className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl"
          >
            <h3 className="text-sm font-semibold text-slate-900">
              Abrir projeto de ação corretiva
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              Decisão humana — o sistema só sinaliza o padrão; o projeto não abre sozinho.
            </p>
            <label className="mt-3 block text-xs font-medium text-slate-600">
              Título
              <input
                required
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={convertForm.title}
                onChange={(e) => setConvertForm((f) => ({ ...f, title: e.target.value }))}
              />
            </label>
            <label className="mt-3 block text-xs font-medium text-slate-600">
              Responsável
              <select
                required
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={convertForm.owner_user_id}
                onChange={(e) =>
                  setConvertForm((f) => ({ ...f, owner_user_id: e.target.value }))
                }
              >
                <option value="">Selecionar…</option>
                {users.map((u) => (
                  <option key={u.user_id} value={u.user_id}>
                    {u.name}
                    {u.system_role ? ` (${u.system_role})` : ''}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-3 block text-xs font-medium text-slate-600">
              Prazo
              <input
                required
                type="date"
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={convertForm.due_date}
                onChange={(e) => setConvertForm((f) => ({ ...f, due_date: e.target.value }))}
              />
            </label>
            <label className="mt-3 block text-xs font-medium text-slate-600">
              Notas de causa raiz (opcional)
              <textarea
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                rows={3}
                value={convertForm.root_cause_notes}
                onChange={(e) =>
                  setConvertForm((f) => ({ ...f, root_cause_notes: e.target.value }))
                }
              />
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                onClick={() => setConvertOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={busy}
                className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
              >
                Criar projeto
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
