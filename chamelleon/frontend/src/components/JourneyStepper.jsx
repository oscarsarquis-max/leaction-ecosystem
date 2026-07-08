export default function JourneyStepper({ steps = [] }) {
  if (!steps.length) return null;

  return (
    <section className="rounded-xl border border-violet-100 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-wider text-amber-600">Jornada PanelDX</p>
      <h2 className="mt-1 text-lg font-bold text-[#4A2E80]">Progresso da transformação</h2>
      <ol className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step, index) => (
          <li
            key={step.id}
            className={[
              'rounded-lg border px-4 py-3',
              step.done
                ? 'border-emerald-200 bg-emerald-50'
                : 'border-slate-200 bg-slate-50',
            ].join(' ')}
          >
            <div className="flex items-start gap-3">
              <span
                className={[
                  'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                  step.done ? 'bg-emerald-600 text-white' : 'bg-slate-300 text-slate-700',
                ].join(' ')}
              >
                {step.done ? '✓' : index + 1}
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-800">{step.label}</p>
                <p className="mt-0.5 text-xs text-slate-500">{step.status_target}</p>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
