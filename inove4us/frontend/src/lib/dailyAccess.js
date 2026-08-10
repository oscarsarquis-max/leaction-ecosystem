/**
 * Freemium solo: Dia a Dia só navegação (listagem).
 * Registro liberado para institucional, Profissional ou Mentor.
 */
export function canRegisterDailyAula(user) {
  if (!user) return false
  if (user.is_institutional) return true
  const tier = String(user.plan_tier || 'starter').trim().toLowerCase()
  if (tier === 'profissional' || tier === 'mentor') return true
  const quota = user.aulas_mes
  if (quota && quota.ilimitado) return true
  if (quota && typeof quota.bloqueado === 'boolean') return !quota.bloqueado
  return false
}
