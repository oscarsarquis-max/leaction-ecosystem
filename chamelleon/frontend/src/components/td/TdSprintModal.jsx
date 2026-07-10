import { useEffect, useMemo, useState } from 'react';
import { TD_STAGE } from '../../constants/td';
import { formatSprintBlockLabel } from '../../constants/td';

/**
 * Modal de execução de Sprint — espelho PanelDX (bloco × dimensão-domínio + entregável).
 * Editável quando a sprint está em Execução (acompanhamento da efetivação).
 */
export default function TdSprintModal({ sprint, onClose, onSave, saving = false }) {
  const editable = sprint?.kanban_stage === TD_STAGE.EXECUCAO;

  const goals = sprint?.goals_payload || {};
  const block = useMemo(() => formatSprintBlockLabel(sprint), [sprint]);
  const dod = goals.criteria_dod || {};
  const required = Array.isArray(dod.required) ? dod.required : [];
  const education = Array.isArray(dod.context_education) ? dod.context_education : [];
  const activities = Array.isArray(goals.atividades_taticas) ? goals.atividades_taticas : [];
  const metrics = goals.metrics_scores && typeof goals.metrics_scores === 'object'
    ? Object.entries(goals.metrics_scores)
    : [];

  const [objetivo, setObjetivo] = useState('');
  const [execNotes, setExecNotes] = useState('');
  const [realv, setRealv] = useState(0);

  useEffect(() => {
    if (!sprint) return;
    setObjetivo(goals.objetivo || sprint.description || goals.desc_sprn || '');
    setExecNotes(goals.exec_notes || '');
    setRealv(Number(goals.realv_sprn || 0));
  }, [sprint, goals.objetivo, goals.desc_sprn, goals.exec_notes, goals.realv_sprn, sprint?.description]);

  if (!sprint) return null;

  const target = Number(goals.targv_sprn || 10);
  const progress = target > 0 ? Math.min(100, Math.round((realv / target) * 100)) : 0;

  async function handleSave() {
    if (!onSave) return;
    await onSave({
      goals_payload: {
        objetivo,
        desc_sprn: objetivo,
        exec_notes: execNotes,
        realv_sprn: Number(realv) || 0,
      },
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="td-sprint-modal-title"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-slate-200 bg-white px-6 py-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Painel de Execução · {sprint.paneldx_domain}
            </p>
            <h2 id="td-sprint-modal-title" className="mt-1 text-xl font-bold text-slate-900">
              {goals.name_sprn || sprint.title}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {goals.onda || sprint.kanban_stage}
              {goals.stat_sprn ? ` · ${goals.stat_sprn}` : ''}
              {goals.week_sprn ? ` · ${goals.week_sprn} semana(s)` : ''}
            </p>
          </div>
          <div className="flex gap-2">
            {editable && onSave && (
              <button
                type="button"
                disabled={saving}
                onClick={handleSave}
                className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {saving ? 'Salvando…' : 'Salvar execução'}
              </button>
            )}
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              onClick={onClose}
            >
              Fechar
            </button>
          </div>
        </header>

        {block && (
          <section className="border-b border-violet-100 bg-violet-50/50 px-6 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-700">
              Acoplamento metodológico (dimensão × domínio → bloco → entregável)
            </p>
            <p className="mt-1 text-sm font-semibold text-violet-950">{block.dimBlock}</p>
            {block.pair && <p className="mt-0.5 text-xs text-violet-800">{block.pair}</p>}
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-violet-900">
              {block.meta.deliverableName && (
                <span>
                  <span className="font-semibold">Entregável:</span> {block.meta.deliverableName}
                </span>
              )}
              {block.meta.gapFp != null && !Number.isNaN(Number(block.meta.gapFp)) && (
                <span>
                  <span className="font-semibold">Gap F−P:</span>{' '}
                  {Number(block.meta.gapFp).toFixed(2)}
                </span>
              )}
              {block.meta.legacyIdBloc != null && (
                <span>
                  <span className="font-semibold">Bloco #</span>
                  {block.meta.legacyIdBloc}
                </span>
              )}
            </div>
          </section>
        )}

        <div className="grid gap-6 p-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="space-y-5">
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Objetivo / Descrição
              </h3>
              {editable ? (
                <textarea
                  value={objetivo}
                  onChange={(e) => setObjetivo(e.target.value)}
                  rows={4}
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              ) : (
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
                  {goals.objetivo || sprint.description || goals.desc_sprn || '—'}
                </p>
              )}
              {goals.justificativa_baseada_no_relatorio && (
                <p className="mt-3 rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600">
                  <span className="font-semibold">Justificativa: </span>
                  {goals.justificativa_baseada_no_relatorio}
                </p>
              )}
            </section>

            <section className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Definição do Entregável
                </h3>
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
                  {goals.derv_defi || '—'}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Competências
                </h3>
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
                  {goals.derv_comp || '—'}
                </p>
              </div>
            </section>

            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Atividades Táticas (Vetor)
              </h3>
              {activities.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">Sem atividades registradas.</p>
              ) : (
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-700">
                  {activities.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ol>
              )}
            </section>

            {editable && (
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Notas de execução
                </h3>
                <textarea
                  value={execNotes}
                  onChange={(e) => setExecNotes(e.target.value)}
                  rows={3}
                  placeholder="Evidências, ritos, impedimentos e efetivação no Gemba…"
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </section>
            )}

            <section className="rounded-xl border border-amber-200 bg-amber-50/60 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-900">
                SWOT ({goals.swot_type || 'Fraqueza'})
              </h3>
              <p className="mt-2 whitespace-pre-wrap text-sm text-amber-950">
                {goals.swot_justification || '—'}
              </p>
            </section>
          </div>

          <aside className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-slate-700">Progresso</span>
                <span className="font-semibold text-slate-900">{progress}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-slate-800 transition-all"
                  style={{ width: `${Math.max(progress, progress > 0 ? 8 : 0)}%` }}
                />
              </div>
              {editable ? (
                <label className="mt-3 block text-xs text-slate-600">
                  Realizado (pts)
                  <input
                    type="number"
                    min={0}
                    max={target}
                    value={realv}
                    onChange={(e) => setRealv(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                  />
                </label>
              ) : (
                <p className="mt-2 text-xs text-slate-500">
                  Realizado {realv} / Meta {target} pts · mínimo recomendado 80%
                </p>
              )}
            </div>

            <div className="rounded-xl border border-slate-200 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Definition of Done
              </h3>
              <p className="mt-3 text-[11px] font-semibold uppercase text-slate-500">Required</p>
              <ul className="mt-1 space-y-1 text-sm text-slate-700">
                {required.length === 0 && <li className="text-slate-400">—</li>}
                {required.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-emerald-600">✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[11px] font-semibold uppercase text-slate-500">
                Context / Education
              </p>
              <ul className="mt-1 space-y-1 text-sm text-slate-700">
                {education.length === 0 && <li className="text-slate-400">—</li>}
                {education.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-slate-400">○</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {metrics.length > 0 && (
              <div className="rounded-xl border border-slate-200 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Métricas
                </h3>
                <ul className="mt-2 space-y-1 text-sm text-slate-700">
                  {metrics.map(([name, value]) => (
                    <li key={name} className="flex justify-between gap-2">
                      <span>{name}</span>
                      <span className="font-medium">{String(value)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="rounded-xl border border-slate-200 p-4 text-xs text-slate-500">
              <p>
                Origem:{' '}
                <span className="font-medium text-slate-700">
                  {sprint.origin_type === 'kaizen_emergent' ? 'Kaizen Emergente' : 'Baseline'}
                </span>
              </p>
              <p className="mt-1">
                Estágio:{' '}
                <span className="font-medium text-slate-700">{sprint.kanban_stage}</span>
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

/** Toast simples para feedback de gênese. */
export function TdToast({ message, tone = 'dark', onClose }) {
  useEffect(() => {
    if (!message) return undefined;
    const timer = setTimeout(() => onClose?.(), 4000);
    return () => clearTimeout(timer);
  }, [message, onClose]);

  if (!message) return null;
  const styles =
    tone === 'error'
      ? 'border-red-200 bg-red-50 text-red-900'
      : tone === 'success'
        ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
        : 'border-slate-200 bg-slate-900 text-white';

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 max-w-sm rounded-xl border px-4 py-3 text-sm shadow-lg ${styles}`}
      role="status"
    >
      <div className="flex items-start gap-3">
        <p className="flex-1">{message}</p>
        <button type="button" className="shrink-0 opacity-70 hover:opacity-100" onClick={onClose}>
          ×
        </button>
      </div>
    </div>
  );
}
