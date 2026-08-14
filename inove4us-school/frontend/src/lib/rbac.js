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

/**
 * administrativo → operacional + pedagógico (mesma regra do backend auth_guards).
 * operacional ↛ pedagógico e vice-versa.
 */
const ZONA_IMPLIES = {
  [ZONAS.administrativo]: new Set([
    ZONAS.administrativo,
    ZONAS.operacional,
    ZONAS.pedagogico,
  ]),
  [ZONAS.operacional]: new Set([ZONAS.operacional]),
  [ZONAS.pedagogico]: new Set([ZONAS.pedagogico]),
}

/** Itens de navegação (header horizontal): exige ao menos uma das zonas listadas. */
export const NAV_ITEMS = [
  { to: '/', label: 'Radar Pedagógico', end: true, zonas: [ZONAS.pedagogico] },
  {
    to: '/editor-pedagogico',
    label: 'Editor Pedagógico',
    zonas: [ZONAS.pedagogico],
  },
  { to: '/secretaria', label: 'Secretaria Acadêmica', zonas: [ZONAS.operacional] },
  { to: '/equipe', label: 'Minha Equipe', zonas: [ZONAS.administrativo] },
]

/** Rotas autenticadas fora do menu — qualquer zona ativa. */
export const OPEN_AUTH_PATHS = [
  { to: '/roteiro-guiado', zonas: [ZONAS.administrativo, ZONAS.operacional, ZONAS.pedagogico] },
]

export function normalizeZonas(zonas) {
  if (!Array.isArray(zonas)) return []
  return [...new Set(zonas.map((z) => String(z || '').trim()).filter(Boolean))]
}

/** Zonas efetivas após implicação de administrativo. */
export function effectiveZonas(userZonas) {
  const have = new Set()
  for (const z of normalizeZonas(userZonas)) {
    const implied = ZONA_IMPLIES[z]
    if (implied) {
      for (const x of implied) have.add(x)
    } else {
      have.add(z)
    }
  }
  return have
}

export function hasAnyZona(userZonas, required) {
  const have = effectiveZonas(userZonas)
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
  const open = OPEN_AUTH_PATHS.find(
    (n) => path === n.to || path.startsWith(`${n.to}/`),
  )
  if (open) return hasAnyZona(userZonas, open.zonas)
  const item = NAV_ITEMS.find((n) =>
    n.end ? path === n.to : path === n.to || path.startsWith(`${n.to}/`),
  )
  if (!item) return hasAnyZona(userZonas, Object.values(ZONAS))
  return hasAnyZona(userZonas, item.zonas)
}
