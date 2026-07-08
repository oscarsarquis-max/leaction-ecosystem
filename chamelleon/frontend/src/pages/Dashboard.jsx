import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import ScoreComparativeTable from '../components/ScoreComparativeTable';
import DiagnosticScoreCharts from '../components/DiagnosticScoreCharts';
import JourneyStepper from '../components/JourneyStepper';
import { buildSectorLegendLabel, extractSetorialPresente } from '../utils/diagnosticScores';
import { resolveJourneyFlags } from '../utils/journeyState';
import { useAuth } from '../context/AuthContext';
import { getMyLatestResult } from '../services/api';
import { generateTdPlan } from '../services/tdApi';

function MaturityGauge({ score, max = 4 }) {
  const pct = Math.min(100, Math.max(0, (score / max) * 100));
  const angle = (pct / 100) * 180;
  const radius = 70;
  const cx = 90;
  const cy = 90;
  const needleX = cx + radius * Math.cos((Math.PI * (180 - angle)) / 180);
  const needleY = cy - radius * Math.sin((Math.PI * (180 - angle)) / 180);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 180 110" className="h-36 w-56">
        <path
          d="M 20 90 A 70 70 0 0 1 160 90"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d="M 20 90 A 70 70 0 0 1 160 90"
          fill="none"
          stroke="url(#gaugeGradient)"
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${(angle / 180) * 220} 220`}
        />
        <defs>
          <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#4ade80" />
            <stop offset="100%" stopColor="#16a34a" />
          </linearGradient>
        </defs>
        <line x1={cx} y1={cy} x2={needleX} y2={needleY} stroke="#15803d" strokeWidth="3" />
        <circle cx={cx} cy={cy} r="6" fill="#15803d" />
      </svg>
      <p className="text-4xl font-bold text-slate-900">{score?.toFixed?.(2) ?? score}</p>
      <p className="text-sm text-slate-500">de {max}.0 — score global</p>
    </div>
  );
}

function GenesisPanel({ flags, onGenerate, generating, error }) {
  if (flags.isPlanoConcluido) {
    return (
      <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
        <h3 className="text-lg font-bold text-emerald-900">Plano de Transformação gerado</h3>
        <p className="mt-2 text-sm text-emerald-800">
          Acesse o Plano Diretor e o Kanban de Implementação na Área de Transformação Digital.
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          <Link
            to="/td/plan"
            className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark"
          >
            Plano Diretor TD
          </Link>
          <Link
            to="/td/kanban"
            className="rounded-lg border border-chameleon/30 px-4 py-2 text-sm font-semibold text-chameleon-dark hover:bg-chameleon/5"
          >
            Kanban TD
          </Link>
        </div>
        {(flags.podeAtualizarPlano || flags.mostrarBotaoGenese) && (
          <button
            type="button"
            onClick={onGenerate}
            disabled={generating}
            className="mt-4 text-sm font-medium text-emerald-900 underline disabled:opacity-50"
          >
            {generating ? 'Atualizando…' : 'Regenerar plano com IA'}
          </button>
        )}
      </section>
    );
  }

  if (flags.isEmProcessamento || generating) {
    return (
      <section className="rounded-xl border border-violet-200 bg-violet-50 p-6 text-center">
        <p className="text-sm text-violet-800">
          O Motor PanelDX está gerando seu plano (PENDENTE / PROCESSANDO)…
        </p>
      </section>
    );
  }

  if (!flags.isAvaliacaoOk) return null;

  return (
    <section className="rounded-xl border border-violet-200 bg-gradient-to-br from-violet-50 to-amber-50 p-8 text-center shadow-sm">
      <h3 className="text-xl font-bold text-[#4A2E80]">Avaliação completa registrada</h3>
      <p className="mx-auto mt-3 max-w-xl text-sm text-slate-600">
        Revise gráficos e matriz acima. Quando contexto e contratação estiverem OK, inicie a Gênese
        IA para gerar o backlog e o Kanban de Transformação Digital (domínios oficiais PanelDX).
      </p>
      {!flags.isContextoOk && (
        <p className="mt-3 text-sm text-amber-800">
          Pendente:{' '}
          <Link to="/meus-dados" className="font-semibold underline">
            contexto institucional
          </Link>
        </p>
      )}
      {!flags.isProjetoOk && (
        <p className="mt-1 text-sm text-amber-800">
          Pendente: contratação da ferramenta (simule em Meus Dados).
        </p>
      )}
      {flags.isErroIa && (
        <p className="mt-3 text-sm text-red-700">
          A última Gênese falhou (ERRO_IA). Você pode tentar novamente.
        </p>
      )}
      {error && (
        <p className="mt-3 text-sm text-red-700">{error}</p>
      )}
      <button
        type="button"
        disabled={!flags.podeGerarPlano && !flags.isErroIa}
        onClick={onGenerate}
        className="mt-6 rounded-lg bg-gradient-to-r from-amber-400 to-amber-600 px-8 py-3 text-sm font-bold text-black shadow disabled:cursor-not-allowed disabled:opacity-50"
        title={
          flags.podeGerarPlano || flags.isErroIa
            ? 'Iniciar Gênese IA (Motor PanelDX)'
            : 'Complete contexto e contratação antes da Gênese'
        }
      >
        Gerar Plano de Transformação Digital
      </button>
    </section>
  );
}

export default function Dashboard() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isLead, isExecutor, frameworkId, loading: authLoading, refreshProfile, journey } =
    useAuth();
  const journeyFlags = resolveJourneyFlags(journey);
  const stateResult = location.state?.assessmentResult;
  const forbidden = location.state?.forbidden;

  const [loadedResult, setLoadedResult] = useState(null);
  const [loadingResult, setLoadingResult] = useState(isLead && !stateResult);
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [genesisError, setGenesisError] = useState('');
  const retriedFrameworkRef = useRef(false);

  const result = stateResult || loadedResult;

  async function handleGenerateTdPlan() {
    setGeneratingPlan(true);
    setGenesisError('');
    try {
      await generateTdPlan({ force: true });
      await refreshProfile();
      navigate('/td/plan');
    } catch (err) {
      setGenesisError(err.message || 'Falha na Gênese do plano de TD.');
      await refreshProfile();
    } finally {
      setGeneratingPlan(false);
    }
  }

  useEffect(() => {
    if (!authLoading && isLead && !frameworkId && !retriedFrameworkRef.current) {
      retriedFrameworkRef.current = true;
      refreshProfile();
    }
  }, [authLoading, isLead, frameworkId, refreshProfile]);

  useEffect(() => {
    if (stateResult?.submission_id) {
      refreshProfile();
    }
  }, [stateResult?.submission_id, refreshProfile]);

  useEffect(() => {
    if (!isLead || stateResult || authLoading) return undefined;
    if (!frameworkId) {
      setLoadingResult(false);
      return undefined;
    }

    let cancelled = false;
    setLoadingResult(true);
    getMyLatestResult()
      .then((data) => {
        if (!cancelled && data.result) setLoadedResult(data.result);
      })
      .catch(() => {
        if (!cancelled) setLoadedResult(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingResult(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isLead, stateResult, frameworkId, authLoading]);

  const axisEntries = useMemo(
    () => Object.entries(result?.scores_por_eixo || {}),
    [result],
  );

  const hasComparativeScores =
    result?.scores_detalhe_presente?.pdom_scores &&
    Object.keys(result.scores_detalhe_presente.pdom_scores).length > 0;

  const sectorLegendLabel = buildSectorLegendLabel(
    result?.sector,
    result?.sector_dimension_label,
  );
  const scoresSetorialPresente = extractSetorialPresente(result || {});

  if (loadingResult) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm text-slate-500">Carregando seu resultado...</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="space-y-6">
        {isLead && <JourneyStepper steps={journeyFlags.steps} />}
        {forbidden && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Acesso negado para o seu perfil nesta área.
          </div>
        )}
        {isLead && !frameworkId && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Nenhum framework ativo está vinculado ao seu tenant. O administrador precisa publicar
            o framework do setor no Estúdio de Criação (Builder).
          </div>
        )}
        <section className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h2 className="text-2xl font-bold text-slate-800">
            {isLead ? 'Meu Resultado' : 'Painel de Maturidade'}
          </h2>
          <p className="mt-2 text-slate-500">
            {isLead
              ? 'Responda ao questionário completo para avançar para AVALIACAO OK e liberar a análise de maturidade.'
              : isExecutor
                ? 'Como executor, o seu foco será a sala de execução (em breve). Consulte avaliações via o gestor lead.'
                : 'Ainda não há diagnóstico nesta sessão. Consulte a listagem de avaliações para ver resultados dos clientes.'}
          </p>
          {isLead && frameworkId && (
            <Link
              to="/diagnostico"
              className="mt-6 inline-flex rounded-lg bg-chameleon px-6 py-3 text-sm font-semibold text-white hover:bg-chameleon-dark"
            >
              Iniciar Diagnóstico
            </Link>
          )}
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {isLead && <JourneyStepper steps={journeyFlags.steps} />}

      <section className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">
            {isLead ? 'Meu Resultado' : 'Resultados do Diagnóstico'}
          </h2>
          <p className="mt-1 text-slate-500">
            Framework: <span className="font-medium">{result.framework_id}</span>
            {journeyFlags.statusIa && (
              <span className="ml-2 rounded bg-violet-100 px-2 py-0.5 text-xs font-semibold text-violet-800">
                {journeyFlags.statusIa}
              </span>
            )}
          </p>
        </div>
        {isLead && result?.submission_id && result?.has_diagnostic_report && (
          <Link
            to={`/relatorio/${result.submission_id}`}
            className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark"
          >
            Ver relatório completo
          </Link>
        )}
        {isLead && (
          <Link
            to="/diagnostico"
            className="rounded-lg border border-chameleon/30 bg-chameleon/5 px-4 py-2 text-sm font-semibold text-chameleon-dark hover:bg-chameleon/10"
          >
            Ver questionário respondido
          </Link>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-1">
          <p className="text-sm font-medium text-slate-500">Score Global</p>
          <div className="mt-2">
            <MaturityGauge score={result.score_global} />
          </div>
        </article>

        <article className="rounded-xl border border-chameleon/30 bg-chameleon/5 p-6 shadow-sm lg:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-chameleon-dark">
            Nível de Maturidade
          </p>
          <h3 className="mt-2 text-3xl font-bold text-slate-900">{result.nivel_maturidade}</h3>
          {result.maturity_level_description && (
            <p className="mt-3 text-sm leading-relaxed text-slate-600">
              {result.maturity_level_description}
            </p>
          )}
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-white/80 p-4">
              <p className="text-xs text-slate-500">Realidade (P)</p>
              <p className="mt-1 text-2xl font-bold text-slate-800">
                {result.score_geral_presente?.toFixed?.(2) ?? '—'}
              </p>
            </div>
            <div className="rounded-lg bg-white/80 p-4">
              <p className="text-xs text-slate-500">Ambição (F)</p>
              <p className="mt-1 text-2xl font-bold text-slate-800">
                {result.score_geral_futuro?.toFixed?.(2) ?? '—'}
              </p>
            </div>
            <div className="rounded-lg bg-white/80 p-4">
              <p className="text-xs text-slate-500">Gap</p>
              <p className="mt-1 text-2xl font-bold text-amber-700">
                {result.score_geral_gap?.toFixed?.(2) ?? '—'}
              </p>
            </div>
          </div>
          <div className="mt-6">
            <div className="rounded-lg bg-white/80 p-4">
              <p className="text-xs text-slate-500">Eixos avaliados</p>
              <p className="mt-1 text-2xl font-bold text-chameleon-dark">{axisEntries.length}</p>
            </div>
          </div>
        </article>
      </section>

      {isLead && (
        <GenesisPanel
          flags={journeyFlags}
          onGenerate={handleGenerateTdPlan}
          generating={generatingPlan}
          error={genesisError}
        />
      )}

      {hasComparativeScores && (
        <DiagnosticScoreCharts
          scoresPresente={result.scores_detalhe_presente}
          scoresFuturo={result.scores_detalhe_futuro}
          scoresGap={result.scores_detalhe_gap}
          scoresSetorialPresente={scoresSetorialPresente}
          sectorDimensionLabel={result.sector_dimension_label}
          sectorLegendLabel={sectorLegendLabel}
        />
      )}

      {hasComparativeScores ? (
        <ScoreComparativeTable
          scoreGeralPresente={result.score_geral_presente}
          scoreGeralFuturo={result.score_geral_futuro}
          scoreGeralGap={result.score_geral_gap}
          scoresPresente={result.scores_detalhe_presente}
          scoresFuturo={result.scores_detalhe_futuro}
          scoresGap={result.scores_detalhe_gap}
          sectorDimensionLabel={result.sector_dimension_label}
          domainLabels={result.domain_labels}
          title="Scores por Eixo — Presente, Futuro e Gap"
        />
      ) : (
        axisEntries.length > 0 && (
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-800">Scores por Eixo</h3>
            <div className="mt-5 space-y-4">
              {axisEntries.map(([axis, score]) => (
                <div key={axis}>
                  <div className="mb-1 flex justify-between gap-4 text-sm">
                    <span className="font-medium text-slate-700">{axis}</span>
                    <span className="shrink-0 font-semibold text-chameleon-dark">{score}</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-chameleon-light to-chameleon"
                      style={{ width: `${Math.min(100, (score / 4) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )
      )}
    </div>
  );
}
