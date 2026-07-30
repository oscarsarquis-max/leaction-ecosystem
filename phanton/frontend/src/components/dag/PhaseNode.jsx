import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import { AlertTriangle, CheckCircle2, Circle, Loader2, ShieldCheck } from 'lucide-react'

const STATUS_STYLES = {
  pending: {
    border: 'border-slate-300',
    card: 'bg-white/95 opacity-70',
    title: 'text-slate-600',
    badge: 'bg-slate-100 text-slate-500 border-slate-200',
    Icon: Circle,
    iconClass: 'text-slate-400',
  },
  running: {
    border: 'border-sky-400 animate-pulse',
    card: 'bg-sky-50/95',
    title: 'text-slate-900',
    badge: 'bg-sky-100 text-sky-800 border-sky-300',
    Icon: Loader2,
    iconClass: 'text-sky-600 animate-spin',
  },
  awaiting: {
    border: 'border-amber-400',
    card: 'bg-amber-50/95 shadow-[0_0_20px_rgba(245,158,11,0.25)]',
    title: 'text-slate-900',
    badge: 'bg-amber-100 text-amber-900 border-amber-300',
    Icon: ShieldCheck,
    iconClass: 'text-amber-700',
  },
  success: {
    border: 'border-emerald-400',
    card: 'bg-emerald-50/95',
    title: 'text-slate-900',
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    Icon: CheckCircle2,
    iconClass: 'text-emerald-600',
  },
  approved: {
    border: 'border-emerald-400',
    card: 'bg-emerald-50/95',
    title: 'text-slate-900',
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    Icon: CheckCircle2,
    iconClass: 'text-emerald-600',
  },
  error: {
    border: 'border-red-400',
    card: 'bg-red-50/95',
    title: 'text-slate-900',
    badge: 'bg-red-100 text-red-800 border-red-300',
    Icon: AlertTriangle,
    iconClass: 'text-red-600',
  },
}

function PhaseNode({ data }) {
  const statusKey = String(data?.status || 'pending').toLowerCase()
  const style = STATUS_STYLES[statusKey] || STATUS_STYLES.pending
  const Icon = style.Icon
  const title = data?.title || data?.label || 'Fase'
  const capability = data?.capability || '—'

  return (
    <div
      className={`min-w-[200px] max-w-[240px] cursor-pointer rounded-xl border-2 px-3.5 py-3 shadow-sm backdrop-blur transition hover:brightness-[0.98] ${style.border} ${style.card}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-slate-400"
      />

      <div className="flex items-start gap-2.5">
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-slate-200/80 bg-white/80">
          <Icon className={`h-4 w-4 ${style.iconClass}`} />
        </div>
        <div className="min-w-0 flex-1 text-left">
          <p className={`font-display text-sm font-semibold leading-snug ${style.title}`}>
            {title}
          </p>
          <p className="mt-0.5 truncate font-mono text-[10px] uppercase tracking-wide text-slate-500">
            {capability}
          </p>
          <span
            className={`mt-2 inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold capitalize ${style.badge}`}
          >
            {statusKey}
          </span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-slate-400"
      />
    </div>
  )
}

export default memo(PhaseNode)
