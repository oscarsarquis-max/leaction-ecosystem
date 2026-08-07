/** Zonas RBAC — espelha school_gestor_perfis.zona */

export const ZONAS = {
  administrativo: 'administrativo',
  operacional: 'operacional',
  pedagogico: 'pedagogico',
}

export const ZONA_LABEL = {
  administrativo: 'Administrativo',
  operacional: 'Operacional',
  pedagogico: 'Pedagógico',
}

/** Itens de navegação: exige ao menos uma das zonas listadas. */
export const NAV_ITEMS = [
  { to: '/', label: 'Radar Pedagógico', end: true, zonas: [ZONAS.pedagogico] },
  { to: '/equipe', label: 'Minha Equipe', zonas: [ZONAS.administrativo] },
  { to: '/secretaria', label: 'Secretaria Acadêmica', zonas: [ZONAS.operacional] },
  {
    to: '/editor-pedagogico',
    label: 'Editor Pedagógico',
    zonas: [ZONAS.pedagogico],
  },
]

export function normalizeZonas(zonas) {
  if (!Array.isArray(zonas)) return []
  return [...new Set(zonas.map((z) => String(z || '').trim()).filter(Boolean))]
}

export function hasAnyZona(userZonas, required) {
  const have = new Set(normalizeZonas(userZonas))
  if (!required || required.length === 0) return have.size > 0
  return required.some((z) => have.has(z))
}

export function filterNavByZonas(userZonas) {
  return NAV_ITEMS.filter((item) => hasAnyZona(userZonas, item.zonas))
}

export function firstAccessiblePath(userZonas) {
  const items = filterNavByZonas(userZonas)
  return items[0]?.to || '/acesso'
}

export function pathAllowed(pathname, userZonas) {
  const path = pathname === '' ? '/' : pathname
  const item = NAV_ITEMS.find((n) =>
    n.end ? path === n.to : path === n.to || path.startsWith(`${n.to}/`),
  )
  if (!item) return hasAnyZona(userZonas, Object.values(ZONAS))
  return hasAnyZona(userZonas, item.zonas)
}
