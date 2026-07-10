import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import ScoreComparativeTable from '../components/ScoreComparativeTable';
import DiagnosticScoreCharts from '../components/DiagnosticScoreCharts';
import JourneyStepper from '../components/JourneyStepper';
import { buildSectorLegendLabel, extractSetorialPresente } from '../utils/diagnosticScores';
import { getDiagnosticReport } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { resolveJourneyFlags } from '../utils/journeyState';

function KpiCard({ label, value, sub }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-bold text-slate-900">{value ?? '—'}</p>
      {sub && <p className="mt-1 text-sm text-slate-500">{sub}</p>}
    </div>
  );
}

export default function DiagnosticReport() {
  const { submissionId } = useParams();
  const { journey } = useAuth();
  const journeyFlags = resolveJourneyFlags(journey);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDiagnosticReport(submissionId)
      .then((data) => {
        if (!cancelled) setReport(data.report);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Erro ao carregar relatório.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [submissionId]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
        <p className="text-slate-500">Carregando relatório de diagnóstico...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="space-y-4">
        <Link to="/" className="text-sm font-medium text-chameleon-dark hover:underline">
          ← Voltar ao painel
        </Link>
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800">
          {error || 'Relatório não encontrado.'}
        </div>
      </div>
    );
  }

  const movement = report.movimento_principal || {};
  const sectorLegendLabel = buildSectorLegendLabel(report.sector, report.sector_dimension_label);
  const scoresSetorialPresente = extractSetorialPresente(report);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/" className="text-sm font-medium text-chameleon-dark hover:underline">
            ← Voltar ao painel
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Relatório de Diagnóstico</h1>
          <p className="mt-1 text-slate-500">
            {report.cliente} · {report.sector} · {report.framework_id}
          </p>
        </div>
        <div className="rounded-lg bg-chameleon/10 px-4 py-2 text-sm font-semibold text-chameleon-dark">
          {report.nivel_maturidade}
        </div>
      </div>

      <JourneyStepper steps={journeyFlags.steps} />

      {report.baseline_snapshot && report.evolution && (
        <section className="rounded-xl border border-sky-200 bg-sky-50 p-6">
          <h2 className="text-lg font-semibold text-sky-900">Evolução vs. diagnóstico original</h2>
          <p className="mt-1 text-sm text-sky-800">
            Baseline capturado em{' '}
            {report.baseline_snapshot.captured_at
              ? new Date(report.baseline_snapshot.captured_at).toLocaleString('pt-BR')
              : '—'}
            . Atualize Realidade (Presente) no questionário para refletir o progresso do projeto.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-white/90 p-4">
              <p className="text-xs text-slate-500">Realidade (P) — original</p>
              <p className="text-xl font-bold text-slate-700">
                {report.baseline_snapshot.score_geral_presente?.toFixed?.(2) ?? '—'}
              </p>
              <p className="mt-1 text-xs text-slate-500">Atual</p>
              <p className="text-2xl font-bold text-slate-900">
                {report.score_geral_presente?.toFixed?.(2) ?? '—'}
                {report.evolution.score_geral_presente_delta != null && (
                  <span
                    className={`ml-2 text-sm font-semibold ${
                      report.evolution.score_geral_presente_delta >= 0
                        ? 'text-emerald-700'
                        : 'text-red-600'
                    }`}
                  >
                    {report.evolution.score_geral_presente_delta >= 0 ? '+' : ''}
                    {report.evolution.score_geral_presente_delta}
                  </span>
                )}
              </p>
            </div>
            <div className="rounded-lg bg-white/90 p-4">
              <p className="text-xs text-slate-500">Gap — original</p>
              <p className="text-xl font-bold text-slate-700">
                {report.baseline_snapshot.score_geral_gap?.toFixed?.(2) ?? '—'}
              </p>
              <p className="mt-1 text-xs text-slate-500">Atual</p>
              <p className="text-2xl font-bold text-amber-800">
                {report.score_geral_gap?.toFixed?.(2) ?? '—'}
                {report.evolution.score_geral_gap_delta != null && (
                  <span className="ml-2 text-sm font-semibold text-slate-600">
                    {report.evolution.score_geral_gap_delta >= 0 ? '+' : ''}
                    {report.evolution.score_geral_gap_delta}
                  </span>
                )}
              </p>
            </div>
            <div className="rounded-lg bg-white/90 p-4">
              <p className="text-xs text-slate-500">Score global — original</p>
              <p className="text-xl font-bold text-slate-700">
                {report.baseline_snapshot.score_global?.toFixed?.(2) ?? '—'}
              </p>
              <p className="mt-1 text-xs text-slate-500">Atual</p>
              <p className="text-2xl font-bold text-chameleon-dark">
                {report.score_global?.toFixed?.(2) ?? '—'}
                {report.evolution.score_global_delta != null && (
                  <span
                    className={`ml-2 text-sm font-semibold ${
                      report.evolution.score_global_delta >= 0
                        ? 'text-emerald-700'
                        : 'text-red-600'
                    }`}
                  >
                    {report.evolution.score_global_delta >= 0 ? '+' : ''}
                    {report.evolution.score_global_delta}
                  </span>
                )}
              </p>
            </div>
          </div>
          <Link
            to="/my-assessment"
            className="mt-4 inline-flex text-sm font-semibold text-chameleon-dark underline"
          >
            Atualizar respostas de Realidade no questionário
          </Link>
        </section>
      )}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Realidade (Presente)" value={report.score_geral_presente?.toFixed?.(2)} />
        <KpiCard label="Ambição (Futuro)" value={report.score_geral_futuro?.toFixed?.(2)} />
        <KpiCard
          label="Gap de Transformação"
          value={report.score_geral_gap?.toFixed?.(2)}
          sub="Futuro − Presente"
        />
        <KpiCard
          label="Gap Setorial"
          value={report.score_setorial?.gap?.toFixed?.(2)}
          sub="Dimensão operacional"
        />
      </section>

      {movement.nome && (
        <section className="rounded-xl border border-chameleon/20 bg-chameleon/5 p-6">
          <h2 className="text-lg font-semibold text-chameleon-dark">Movimento Estratégico</h2>
          <p className="mt-2 font-medium text-slate-900">{movement.nome}</p>
          <p className="mt-2 text-sm text-slate-600">{movement.estagio_descricao}</p>
          <p className="mt-2 text-sm text-slate-600">{movement.implicacoes_diagnostico}</p>
        </section>
      )}

      <DiagnosticScoreCharts
        scoresPresente={report.scores_detalhe_presente}
        scoresFuturo={report.scores_detalhe_futuro}
        scoresGap={report.scores_detalhe_gap}
        scoresSetorialPresente={scoresSetorialPresente}
        sectorDimensionLabel={report.sector_dimension_label}
        sectorLegendLabel={sectorLegendLabel}
      />

      <ScoreComparativeTable
        scoreGeralPresente={report.score_geral_presente}
        scoreGeralFuturo={report.score_geral_futuro}
        scoreGeralGap={report.score_geral_gap}
        scoresPresente={report.scores_detalhe_presente}
        scoresFuturo={report.scores_detalhe_futuro}
        scoresGap={report.scores_detalhe_gap}
        sectorDimensionLabel={report.sector_dimension_label}
        domainLabels={report.domain_labels}
      />
    </div>
  );
}
