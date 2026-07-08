import { useCallback, useEffect, useMemo, useState } from 'react';
import TdSprintModal, { TdToast } from '../components/td/TdSprintModal';
import {
  extractTopGaps,
  groupSprintsByDomain,
  TD_STAGE,
} from '../constants/td';
import { useAuth } from '../context/AuthContext';
import { generateTdPlan, getTdPlan, listTdSprints } from '../services/tdApi';

export default function TdPlanManager() {
  const { journey, refreshProfile } = useAuth();
  const [plan, setPlan] = useState(null);
  const [backlog, setBacklog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ message: '', tone: 'dark' });
  const [selected, setSelected] = useState(null);

  const statusIa = (journey?.status_ia || '').toUpperCase();
  const isProcessing = statusIa === 'PENDENTE' || statusIa === 'PROCESSANDO';

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [planRes, backlogRes] = await Promise.all([
        getTdPlan(),
        listTdSprints(TD_STAGE.BACKLOG),
      ]);
      setPlan(planRes.plan || null);
      setBacklog(backlogRes.sprints || []);
    } catch (err) {
      setError(err.message || 'Erro ao carregar o Plano Diretor de TD.');
      setPlan(null);
      setBacklog([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const gaps = useMemo(
    () => extractTopGaps(plan?.survey_snapshot),
    [plan?.survey_snapshot],
  );
  const grouped = useMemo(() => groupSprintsByDomain(backlog), [backlog]);

  async function handleGenerateAiPlan() {
    if (generating || isProcessing) return;
    setGenerating(true);
    setError('');
    setToast({ message: 'Gênese em andamento — Motor PanelDX…', tone: 'dark' });
    try {
      const result = await generateTdPlan({ force: true });
      setPlan(result.plan || null);
      if (typeof refreshProfile === 'function') {
        await refreshProfile();
      }
      await load();
      setToast({
        message: result.message || `Plano gerado (${result.generated_count || 0} sprints).`,
        tone: 'success',
      });
    } catch (err) {
      setError(err.message || 'Falha na Gênese do plano de TD.');
      setToast({ message: err.message || 'Falha na Gênese.', tone: 'error' });
      if (typeof refreshProfile === 'function') {
        await refreshProfile();
      }
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Transformação Digital
          </p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">
            Plano Diretor e Backlog
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">
            Motor de Decisão Tática PanelDX. A geração acontece sob comando do usuário e migra a
            jornada: PENDENTE → PROCESSANDO → CONCLUIDO.
          </p>
          {statusIa && (
            <p className="mt-2 text-xs font-medium text-slate-500">
              status_ia: <span className="text-slate-800">{statusIa}</span>
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={handleGenerateAiPlan}
          disabled={generating || isProcessing}
          className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {generating || isProcessing
            ? 'Gerando plano…'
            : plan
              ? 'Gerar/Atualizar Plano de TD com IA'
              : 'Gerar Plano de TD com IA'}
        </button>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <section className="rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-6 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Maiores gaps da organização
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Domínios oficiais PanelDX: Estratégia, Cultura, Processos, Tecnologia, Dados e
              Clientes.
            </p>
          </div>
          {plan?.created_at && (
            <p className="text-xs text-slate-500">
              Plano desde {new Date(plan.created_at).toLocaleDateString('pt-BR')}
            </p>
          )}
        </div>

        {loading ? (
          <p className="mt-6 text-sm text-slate-500">Carregando gaps…</p>
        ) : gaps.length === 0 ? (
          <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-white px-4 py-8 text-center text-sm text-slate-500">
            Nenhum snapshot disponível. Conclua a avaliação e execute a Gênese IA.
          </div>
        ) : (
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {gaps.map((gap) => (
              <article
                key={gap.domain}
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Domínio PanelDX
                </p>
                <h3 className="mt-1 font-semibold text-slate-900">{gap.domain}</h3>
                <div className="mt-3 flex items-baseline gap-3">
                  {gap.gap != null && !Number.isNaN(gap.gap) && (
                    <p className="text-2xl font-bold text-amber-700">{gap.gap.toFixed(1)}</p>
                  )}
                  <p className="text-xs text-slate-500">
                    {gap.score != null && !Number.isNaN(gap.score)
                      ? `Score atual: ${gap.score.toFixed(1)}`
                      : 'Gap priorizado'}
                  </p>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Backlog de sprints</h2>
            <p className="mt-1 text-sm text-slate-600">
              Sprints em <span className="font-medium">Backlog</span>, agrupadas por domínio. Clique
              para abrir o painel de execução (padrão PanelDX).
            </p>
          </div>
          <p className="text-xs font-medium text-slate-500">
            {backlog.length} sprint{backlog.length === 1 ? '' : 's'}
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Carregando backlog…</p>
        ) : grouped.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
            Nenhuma sprint em Backlog. Execute a Gênese para materializar o plano e o Kanban.
          </div>
        ) : (
          <div className="space-y-6">
            {grouped.map(({ domain, sprints }) => (
              <div key={domain}>
                <div className="mb-3 flex items-center gap-2">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
                    {domain}
                  </h3>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                    {sprints.length}
                  </span>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {sprints.map((sprint) => (
                    <button
                      key={sprint.id}
                      type="button"
                      onClick={() => setSelected(sprint)}
                      className="rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-slate-400 hover:shadow"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-semibold text-slate-900">{sprint.title}</h4>
                        <span className="shrink-0 rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                          {sprint.origin_type === 'kaizen_emergent' ? 'Emergente' : 'Baseline'}
                        </span>
                      </div>
                      {sprint.description && (
                        <p className="mt-2 line-clamp-3 text-sm text-slate-600">
                          {sprint.description}
                        </p>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <TdSprintModal sprint={selected} onClose={() => setSelected(null)} />
      <TdToast
        message={toast.message}
        tone={toast.tone}
        onClose={() => setToast({ message: '', tone: 'dark' })}
      />
    </div>
  );
}
