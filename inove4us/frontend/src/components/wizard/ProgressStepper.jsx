import BrandLogo from '../BrandLogo'

const STEPS = [
  { id: 1, label: 'Problema' },
  { id: 2, label: 'Estruturação' },
  { id: 3, label: 'Hipóteses' },
  { id: 4, label: 'EduScrum' },
]

export default function ProgressStepper({ currentStep }) {
  return (
    <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/90 backdrop-blur-md print:hidden">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3 sm:px-6">
        <a href="/mesa-do-inovador" className="shrink-0" aria-label="inove4us — Mesa do Inovador">
          <BrandLogo
            variant="internal"
            className="h-24 w-auto max-w-[280px] object-contain sm:max-w-[320px]"
          />
        </a>

        <nav aria-label="Progresso do fluxo" className="min-w-0 flex-1">
          <ol className="flex items-center justify-between gap-1 sm:gap-2">
            {STEPS.map((step, index) => {
              const done = currentStep > step.id
              const active = currentStep === step.id
              return (
                <li key={step.id} className="flex min-w-0 flex-1 items-center">
                  <div className="flex min-w-0 flex-1 flex-col items-center gap-1.5">
                    <div
                      className={[
                        'flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold transition',
                        active
                          ? 'bg-brand-600 text-white shadow-soft ring-4 ring-brand-200'
                          : done
                            ? 'bg-bordo text-white'
                            : 'bg-brand-100 text-brand-400',
                      ].join(' ')}
                      aria-current={active ? 'step' : undefined}
                    >
                      {done ? '✓' : step.id}
                    </div>
                    <span
                      className={[
                        'truncate text-[10px] font-semibold uppercase tracking-wide sm:text-xs',
                        active
                          ? 'text-brand-600'
                          : done
                            ? 'text-bordo'
                            : 'text-brand-300',
                      ].join(' ')}
                    >
                      {step.label}
                    </span>
                  </div>
                  {index < STEPS.length - 1 && (
                    <div
                      className={[
                        'mx-1 hidden h-0.5 flex-1 rounded-full sm:block',
                        currentStep > step.id ? 'bg-bordo' : 'bg-brand-100',
                      ].join(' ')}
                      aria-hidden
                    />
                  )}
                </li>
              )
            })}
          </ol>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-brand-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-bordo to-brand-600 transition-all duration-500"
              style={{ width: `${((currentStep - 1) / (STEPS.length - 1)) * 100}%` }}
            />
          </div>
        </nav>
      </div>
    </header>
  )
}
