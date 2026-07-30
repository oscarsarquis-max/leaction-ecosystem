import { FilePlus2, History, Loader2, RotateCcw } from 'lucide-react'

function formatWhen(value) {
  if (!value) return '—'
  try {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return String(value)
    return d.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return String(value)
  }
}

function statusTone(status) {
  const s = String(status || '').toUpperCase()
  if (s === 'COMPLETED' || s === 'APPROVED' || s === 'ACCEPTED') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-800'
  }
  if (s === 'RUNNING' || s === 'AWAITING_APPROVAL' || s === 'PENDING') {
    return 'border-amber-200 bg-amber-50 text-amber-900'
  }
  if (s === 'ERROR' || s === 'FAILED') {
    return 'border-red-200 bg-red-50 text-red-800'
  }
  return 'border-slate-200 bg-slate-50 text-slate-700'
}

export default function RunHistory({
  items = [],
  total = 0,
  loading = false,
  activeRunId = null,
  onSelect,
  onRefresh,
  onNewCreation,
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="text-left">
          <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
            Histórico
          </p>
          <h2 className="font-display mt-1 text-xl font-semibold text-slate-950">
            Pipelines salvos
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Banco de runs: clique para recuperar. Use Nova criação para limpar o painel
            e começar do zero (o histórico permanece).
            {total ? ` · ${total} registrado${total === 1 ? '' : 's'}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onNewCreation}
            className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-900 transition hover:border-emerald-400 hover:bg-emerald-100"
          >
            <FilePlus2 className="h-3.5 w-3.5" />
            Nova criação
          </button>
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RotateCcw className="h-3.5 w-3.5" />
            )}
            Atualizar
          </button>
        </div>
      </div>

      {loading && !items.length ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Carregando histórico…
        </div>
      ) : null}

      {!loading && !items.length ? (
        <div className="mt-4 flex items-start gap-3 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm text-slate-500">
          <History className="mt-0.5 h-4 w-4 shrink-0" />
          Nenhum pipeline salvo ainda. Inicie um run para começar o histórico.
        </div>
      ) : null}

      {items.length ? (
        <ul className="mt-4 max-h-80 space-y-2 overflow-y-auto pr-1">
          {items.map((item) => {
            const selected = String(activeRunId) === String(item.run_id)
            return (
              <li key={item.run_id}>
                <button
                  type="button"
                  onClick={() => onSelect?.(item.run_id)}
                  className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                    selected
                      ? 'border-indigo-400 bg-indigo-50 shadow-[0_0_0_1px_rgba(99,102,241,0.25)]'
                      : 'border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/40'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-display text-sm font-semibold text-slate-900">
                        {item.title || 'Pipeline'}
                      </p>
                      <p className="mt-0.5 font-mono text-[11px] text-slate-500">
                        {String(item.run_id).slice(0, 8)}…
                        {item.version ? (
                          <>
                            <span className="mx-1.5 text-slate-300">·</span>
                            v{item.version}
                          </>
                        ) : null}
                        <span className="mx-1.5 text-slate-300">·</span>
                        {formatWhen(item.created_at)}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${statusTone(
                          item.status,
                        )}`}
                      >
                        {item.status}
                      </span>
                      {item.acceptance_status === 'accepted' ? (
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                          aceito
                        </span>
                      ) : null}
                    </div>
                  </div>
                  {item.description ? (
                    <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-600">
                      {item.description}
                    </p>
                  ) : null}
                  <p className="mt-2 text-[11px] font-medium text-slate-500">
                    {item.approved_count}/{item.phase_count} fases aprovadas
                    {item.phases?.length
                      ? ` · ${item.phases.filter((p) => p.has_artifact).length} com resultado`
                      : ''}
                  </p>
                </button>
              </li>
            )
          })}
        </ul>
      ) : null}
    </section>
  )
}
