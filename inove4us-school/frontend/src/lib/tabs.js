/** Estilo unificado das abas selecionadas no School (verde escuro). */
export const TAB_ACTIVE = 'bg-school-700 text-white'
export const TAB_INACTIVE =
  'bg-transparent text-muted hover:bg-slate-50 hover:text-ink'

export function tabClassName(active) {
  return [
    'rounded-t-lg px-4 py-2.5 text-sm font-semibold transition',
    active ? TAB_ACTIVE : TAB_INACTIVE,
  ].join(' ')
}

/** Variante compacta (secretarias / filtros). */
export function tabClassNameCompact(active) {
  return [
    'rounded-lg px-3 py-2 text-sm font-semibold transition',
    active ? TAB_ACTIVE : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
  ].join(' ')
}
