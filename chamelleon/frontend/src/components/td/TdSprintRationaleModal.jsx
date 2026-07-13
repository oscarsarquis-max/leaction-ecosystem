import { formatSprintBlockLabel } from '../../constants/td';

/**
 * Extrai o dossiê de auditoria da escolha da sprint pela IA Master (gênese).
 */
export function getSprintSelectionAudit(sprint) {
  const goals = sprint?.goals_payload || {};
  const block = formatSprintBlockLabel(sprint);
  const justificativa = String(
    goals.justificativa_baseada_no_relatorio ||
      goals.swot_justification ||
      goals.selection_rationale ||
      '',
  ).trim();
  const gapRaw = sprint?.gap_fp ?? goals.gap_fp ?? block?.meta?.gapFp;
  const gapFp =
    gapRaw != null && gapRaw !== '' && !Number.isNaN(Number(gapRaw))
      ? Number(gapRaw)
      : null;

  return {
    title: goals.name_sprn || sprint?.title || 'Sprint',
    justificativa:
      justificativa ||
      (sprint?.origin_type === 'kaizen_emergent'
        ? 'Sprint emergente do Gemba (Kaizen) — priorizada por causa raiz operacional, não pela ordenação de gap da gênese baseline.'
        : 'Justificativa textual da IA Master não foi materializada neste registro. Consulte gap F−P, onda e acoplamento metodológico abaixo.'),
    objetivo: String(goals.objetivo || sprint?.description || goals.desc_sprn || '').trim(),
    gapFp,
    scorePresente: goals.score_presente ?? null,
    scoreFuturo: goals.score_futuro ?? null,
    onda: goals.onda || null,
    priorityRank: goals.priority_rank ?? null,
    swotType: goals.swot_type || null,
    swotJustification: String(goals.swot_justification || '').trim(),
    pair: block?.pair || sprint?.paneldx_domain || null,
    dimBlock: block?.dimBlock || null,
    deliverableName: block?.meta?.deliverableName || goals.name_derv || null,
    originType: sprint?.origin_type || 'baseline',
    kanbanStage: sprint?.kanban_stage || null,
    hasAiJustification: Boolean(justificativa),
  };
}

/**
 * Modal de auditoria — motivo criterioso da escolha da sprint pela IA Master.
 */
export default function TdSprintRationaleModal({ sprint, onClose }) {
  if (!sprint) return null;
  const audit = getSprintSelectionAudit(sprint);

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="td-sprint-rationale-title"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-chameleon/20 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="border-b border-chameleon/15 bg-gradient-to-r from-chameleon/10 to-white px-5 py-4">
          <p className="text-[11px] font-bold uppercase tracking-wide text-chameleon-dark">
            Auditoria · Escolha da IA Master
          </p>
          <h2 id="td-sprint-rationale-title" className="mt-1 text-lg font-bold text-slate-900">
            {audit.title}
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Motivo criterioso da inclusão desta sprint no plano / Kanban na gênese do TD.
          </p>
        </header>

        <div className="space-y-4 px-5 py-4 text-sm">
          <section className="rounded-xl border border-chameleon/25 bg-chameleon/5 p-4">
            <h3 className="text-[11px] font-black uppercase tracking-wide text-chameleon-dark">
              Justificativa da IA Master
            </h3>
            <p className="mt-2 whitespace-pre-wrap leading-relaxed text-slate-800">
              {audit.justificativa}
            </p>
            {!audit.hasAiJustification && (
              <p className="mt-2 text-xs text-amber-800">
                Registro sem texto explícito de justificativa — critérios quantitativos abaixo.
              </p>
            )}
          </section>

          {audit.objetivo && (
            <section>
              <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-500">
                Objetivo materializado
              </h3>
              <p className="mt-1 whitespace-pre-wrap text-slate-700">{audit.objetivo}</p>
            </section>
          )}

          <section className="grid gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 sm:grid-cols-2">
            {audit.pair && (
              <p>
                <span className="font-semibold text-slate-500">Par dim×domínio:</span>{' '}
                {audit.pair}
              </p>
            )}
            {audit.dimBlock && (
              <p className="sm:col-span-2">
                <span className="font-semibold text-slate-500">Bloco:</span> {audit.dimBlock}
              </p>
            )}
            {audit.deliverableName && (
              <p className="sm:col-span-2">
                <span className="font-semibold text-slate-500">Entregável:</span>{' '}
                {audit.deliverableName}
              </p>
            )}
            {audit.gapFp != null && (
              <p>
                <span className="font-semibold text-slate-500">Gap F−P:</span>{' '}
                {audit.gapFp.toFixed(2)}
              </p>
            )}
            {audit.scorePresente != null && (
              <p>
                <span className="font-semibold text-slate-500">Presente:</span>{' '}
                {Number(audit.scorePresente).toFixed(2)}
              </p>
            )}
            {audit.scoreFuturo != null && (
              <p>
                <span className="font-semibold text-slate-500">Futuro:</span>{' '}
                {Number(audit.scoreFuturo).toFixed(2)}
              </p>
            )}
            {audit.priorityRank != null && (
              <p>
                <span className="font-semibold text-slate-500">Rank de prioridade:</span>{' '}
                {audit.priorityRank}
              </p>
            )}
            {audit.onda && (
              <p className="sm:col-span-2">
                <span className="font-semibold text-slate-500">Onda:</span> {audit.onda}
              </p>
            )}
            {audit.swotType && (
              <p>
                <span className="font-semibold text-slate-500">SWOT:</span> {audit.swotType}
              </p>
            )}
            <p>
              <span className="font-semibold text-slate-500">Origem:</span>{' '}
              {audit.originType === 'kaizen_emergent' ? 'Kaizen / Gemba' : 'Baseline (gênese)'}
            </p>
            {audit.kanbanStage && (
              <p>
                <span className="font-semibold text-slate-500">Estágio atual:</span>{' '}
                {audit.kanbanStage}
              </p>
            )}
          </section>

          {audit.swotJustification &&
            audit.swotJustification !== audit.justificativa && (
              <section>
                <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-500">
                  Qualificação SWOT
                </h3>
                <p className="mt-1 whitespace-pre-wrap text-slate-700">
                  {audit.swotJustification}
                </p>
              </section>
            )}
        </div>

        <footer className="border-t border-slate-100 px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Fechar
          </button>
        </footer>
      </div>
    </div>
  );
}

/** Botão no card — auditoria da escolha da sprint pela IA Master. */
export function TdSprintRationaleLink({ sprint, onOpen, className = '' }) {
  return (
    <button
      type="button"
      title="Auditoria: motivo da escolha pela IA Master na criação do plano"
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        onOpen?.(sprint);
      }}
      className={`mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border border-chameleon/40 bg-chameleon/10 px-2.5 py-1.5 text-[11px] font-bold text-chameleon-dark hover:bg-chameleon/20 ${className}`}
    >
      Por que esta sprint?
    </button>
  );
}
