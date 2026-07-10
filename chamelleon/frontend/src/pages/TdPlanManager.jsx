import { useCallback, useEffect, useMemo, useState } from 'react';
import GenesisProgressOverlay from '../components/td/GenesisProgressOverlay';
import TdReadinessChecklist from '../components/td/TdReadinessChecklist';
import TdSprintModal, { TdToast } from '../components/td/TdSprintModal';
import {
  extractTopGaps,
  formatSprintBlockLabel,
  groupSprintsByDimensionDomain,
  TD_STAGE,
} from '../constants/td';
import { useAuth } from '../context/AuthContext';
import { useGenesisProgress } from '../hooks/useGenesisProgress';
import { readContextFromJourney } from '../utils/businessContext';
import { buildGenesisHints } from '../utils/genesisHints';
import { generateTdPlan, getTdPlan, getTdReadinessStatus, listTdSprints, promoteTdSprintToPlanning } from '../services/tdApi';

export default function TdPlanManager() {
  const { journey, refreshProfile } = useAuth();
  const [plan, setPlan] = useState(null);
  const [backlog, setBacklog] = useState([]);
  const [allSprints, setAllSprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ message: '', tone: 'dark' });
  const [selected, setSelected] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [readinessLoading, setReadinessLoading] = useState(true);

  const statusIa = (journey?.status_ia || '').toUpperCase();
  const isProcessing = statusIa === 'PENDENTE' || statusIa === 'PROCESSANDO';
  const iaReady = readiness?.is_ready === true;
  const contextValues = readContextFromJourney(journey?.context_data);

  const loadReadiness = useCallback(async () => {
    setReadinessLoading(true);
    try {
      const data = await getTdReadinessStatus();
      setReadiness(data);
    } catch {
      setReadiness(null);
    } finally {
      setReadinessLoading(false);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [planRes, backlogRes] = await Promise.all([
        getTdPlan(),
        listTdSprints(TD_STAGE.BACKLOG),
      ]);
      const activePlan = planRes.plan || null;
      setPlan(activePlan);
      const planSprints = activePlan?.sprints || [];
      setAllSprints(planSprints);
      setBacklog(
        planSprints.length > 0
          ? planSprints.filter((s) => s.kanban_stage === TD_STAGE.BACKLOG)
          : backlogRes.sprints || [],
      );
    } catch (err) {
      setError(err.message || 'Erro ao carregar o Plano Diretor de TD.');
      setPlan(null);
      setBacklog([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const snapshotGaps = useMemo(() => extractTopGaps(plan?.survey_snapshot), [plan?.survey_snapshot]);

  const genesisHints = useMemo(
    () => buildGenesisHints({ contextValues, gaps: snapshotGaps }),
    [contextValues, snapshotGaps],
  );

  const genesis = useGenesisProgress({
    hints: genesisHints,
    onComplete: async () => {
      setGenerating(false);
      if (typeof refreshProfile === 'function') {
        await refreshProfile({ background: true });
      }
      await load();
      await loadReadiness();
      setToast({
        message: 'Plano de Transformação Digital gerado com sucesso.',
        tone: 'success',
      });
    },
    onError: async (message) => {
      setError(message);
      setGenerating(false);
      setToast({ message, tone: 'error' });
      if (typeof refreshProfile === 'function') {
        await refreshProfile({ background: true });
      }
    },
  });

  useEffect(() => {
    load();
    loadReadiness();
  }, [load, loadReadiness]);

  const gaps = useMemo(
    () => extractTopGaps(plan?.survey_snapshot),
    [plan?.survey_snapshot],
  );
  const grouped = useMemo(() => groupSprintsByDimensionDomain(backlog), [backlog]);
  const kanbanCount = useMemo(
    () => allSprints.filter((s) => s.kanban_stage !== TD_STAGE.BACKLOG && s.kanban_stage !== TD_STAGE.CONCLUIDA).length,
    [allSprints],
  );

  async function handlePromoteToPlanning(sprintId) {
    setError('');
    try {
      await promoteTdSprintToPlanning(sprintId);
      await load();
      setToast({
        message: 'Sprint promovida para a coluna Planejadas no Kanban.',
        tone: 'success',
      });
    } catch (err) {
      setError(err.message || 'Não foi possível promover a sprint.');
      setToast({ message: err.message || 'Falha ao promover.', tone: 'error' });
    }
  }

  async function handleGenerateAiPlan() {
    if (generating || genesis.active || isProcessing || !iaReady) return;
    setGenerating(true);
    setError('');
    genesis.start(() => generateTdPlan({ force: true }));
  }

  useEffect(() => {
    if (generating || genesis.active) return;
    if (isProcessing) {
      setGenerating(true);
      genesis.resume();
    }
  }, [isProcessing, generating, genesis.active, genesis.resume]);

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
            Uma sprint por par dimensão×domínio com gap F−P positivo, acoplada ao bloco e
            entregável do framework. As 12 de maior gap entram no Kanban (3 em execução imediata);
            o restante fica aqui até você promover para Planejadas.
          </p>
          {allSprints.length > 0 && (
            <p className="mt-2 text-xs text-slate-500">
              {allSprints.length} sprint(s) no plano · {backlog.length} em backlog ·{' '}
              {kanbanCount} no Kanban
            </p>
          )}
          {statusIa && (
            <p className="mt-2 text-xs font-medium text-slate-500">
              status_ia: <span className="text-slate-800">{statusIa}</span>
            </p>
          )}
        </div>
        <div className="flex w-full max-w-sm flex-col gap-3 sm:w-auto">
          <TdReadinessChecklist readiness={readiness} loading={readinessLoading} />
          <button
            type="button"
            onClick={handleGenerateAiPlan}
            disabled={generating || genesis.active || isProcessing || !iaReady}
            className={`rounded-xl px-5 py-3 text-sm font-semibold text-white shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
              iaReady
                ? 'bg-slate-900 ring-2 ring-amber-300 ring-offset-2 hover:bg-slate-800 hover:shadow-md'
                : 'bg-slate-900'
            }`}
          >
            {generating || genesis.active || isProcessing
              ? 'Gerando plano…'
              : plan
                ? 'Gerar/Atualizar Plano de TD com IA'
                : 'Gerar Plano de TD com IA'}
          </button>
        </div>
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
            <h2 className="text-lg font-semibold text-slate-900">Backlog geral (todas as pendências)</h2>
            <p className="mt-1 text-sm text-slate-600">
              Sprints fora do Kanban (após as 12 priorizadas). Use{' '}
              <span className="font-medium">Colocar em planejamento</span> para enviar à coluna
              Planejadas quando houver vaga (máx. 12 no quadro).
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
            {grouped.map(({ dimensionName, domainName, sprints }) => (
              <div key={`${dimensionName}|${domainName}`}>
                <div className="mb-3 flex items-center gap-2">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
                    {dimensionName ? `${dimensionName} × ` : ''}
                    {domainName}
                  </h3>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                    {sprints.length}
                  </span>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {sprints.map((sprint) => {
                    const block = formatSprintBlockLabel(sprint);
                    return (
                      <article
                        key={sprint.id}
                        className="rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm"
                      >
                        <button
                          type="button"
                          onClick={() => setSelected(sprint)}
                          className="w-full text-left"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h4 className="font-semibold text-slate-900">{sprint.title}</h4>
                            <span className="shrink-0 rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                              {sprint.origin_type === 'kaizen_emergent' ? 'Emergente' : 'Baseline'}
                            </span>
                          </div>
                          {block?.dimBlock && (
                            <p className="mt-2 text-xs font-medium text-violet-800">{block.dimBlock}</p>
                          )}
                          {block?.meta?.deliverableName && (
                            <p className="mt-1 text-[11px] text-slate-500">
                              Entregável: {block.meta.deliverableName}
                            </p>
                          )}
                          {block?.meta?.gapFp != null && (
                            <p className="mt-1 text-xs font-semibold text-amber-700">
                              Gap F−P: {Number(block.meta.gapFp).toFixed(2)}
                            </p>
                          )}
                          {sprint.description && (
                            <p className="mt-2 line-clamp-3 text-sm text-slate-600">
                              {sprint.description}
                            </p>
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => handlePromoteToPlanning(sprint.id)}
                          className="mt-3 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-100"
                        >
                          Colocar em planejamento (Kanban)
                        </button>
                      </article>
                    );
                  })}
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
      <GenesisProgressOverlay
        visible={genesis.active}
        progress={genesis.progress}
        statusMessage={genesis.statusMessage}
        subtitle={genesis.subtitle}
        currentHint={genesis.currentHint}
        hintIndex={genesis.hintIndex}
        hintCount={genesis.hintCount}
      />
    </div>
  );
}
