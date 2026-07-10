import { Link } from 'react-router-dom';

function CheckIcon({ done }) {
  return (
    <span
      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
        done ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
      }`}
      aria-hidden
    >
      {done ? '✓' : '✕'}
    </span>
  );
}

export default function TdReadinessChecklist({ readiness, loading }) {
  if (loading || !readiness || readiness.is_ready) {
    return null;
  }

  const surveyPct = Math.round(readiness.survey_progress_pct || 0);

  return (
    <section className="rounded-2xl border border-amber-300 bg-gradient-to-br from-amber-50 to-orange-50/80 p-5 shadow-sm">
      <h2 className="text-base font-semibold text-amber-950">Calibração da IA incompleta</h2>
      <p className="mt-1 text-sm text-amber-900/90">
        Antes de gerar o Plano Diretor, complete os dados-base abaixo. A IA precisa de contexto
        real e diagnóstico fechado para priorizar as sprints corretamente.
      </p>

      <ul className="mt-4 space-y-3">
        <li className="flex items-start gap-3 rounded-xl border border-white/80 bg-white/70 px-4 py-3">
          <CheckIcon done={readiness.context_filled} />
          <div className="min-w-0 flex-1">
            <p className="font-medium text-slate-900">Contexto organizacional</p>
            <p className="mt-0.5 text-xs text-slate-600">
              Mercado, clientes e clima institucional (mín. 40 caracteres cada).
            </p>
            {!readiness.context_filled && (
              <Link
                to="/meus-dados"
                className="mt-2 inline-flex rounded-lg bg-amber-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-900"
              >
                Preencher agora
              </Link>
            )}
          </div>
        </li>

        <li className="flex items-start gap-3 rounded-xl border border-white/80 bg-white/70 px-4 py-3">
          <CheckIcon done={readiness.survey_completed} />
          <div className="min-w-0 flex-1">
            <p className="font-medium text-slate-900">Diagnóstico PanelDX</p>
            <p className="mt-0.5 text-xs text-slate-600">
              {readiness.survey_completed
                ? 'Questionário concluído.'
                : `${surveyPct}% concluído — responda todas as dimensões (Presente e Futuro).`}
            </p>
            {!readiness.survey_completed && (
              <Link
                to="/my-assessment"
                className="mt-2 inline-flex rounded-lg bg-amber-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-900"
              >
                Continuar avaliação
              </Link>
            )}
          </div>
        </li>
      </ul>
    </section>
  );
}
