function professorInitials(nameOrEmail) {
  const s = String(nameOrEmail || '').trim()
  if (!s) return '?'
  if (s.includes('@')) {
    const local = s.split('@')[0].replace(/[^a-zA-Z0-9]/g, '')
    return (local.slice(0, 2) || '?').toUpperCase()
  }
  const parts = s.split(/\s+/).filter(Boolean)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

/**
 * Chip único da relação professor ↔ turma ↔ disciplina.
 * badgeTone: "disciplina" (rosa) | "turma" (verde-água)
 */
export default function ProfessorChip({ nome, email, badge, badgeTone = 'disciplina' }) {
  const label = nome || email || 'Professor'
  return (
    <span className="inline-flex max-w-full items-center gap-2 rounded-full border border-slate-200 bg-white py-1 pl-1 pr-2.5 shadow-sm">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber-200 text-[10px] font-bold text-amber-950">
        {professorInitials(label)}
      </span>
      <span className="truncate text-xs font-semibold text-ink">{label}</span>
      {badge ? (
        <span
          className={[
            'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold',
            badgeTone === 'turma' ? 'bg-teal-50 text-teal-800' : 'bg-rose-50 text-rose-800',
          ].join(' ')}
        >
          {badge}
        </span>
      ) : null}
    </span>
  )
}
