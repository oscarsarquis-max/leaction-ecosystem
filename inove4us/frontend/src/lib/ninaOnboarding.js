/** Flag local espelha o servidor (cache). Fonte da verdade: ctdi_clie.nina_onboarding_done. */
export function ninaOnboardingStorageKey(userId) {
  return `i4_nina_onboarding_v3_${userId || 'anon'}`
}

export function readNinaOnboardingDone(userId) {
  try {
    return localStorage.getItem(ninaOnboardingStorageKey(userId)) === '1'
  } catch {
    return false
  }
}

export function writeNinaOnboardingDone(userId) {
  try {
    localStorage.setItem(ninaOnboardingStorageKey(userId), '1')
  } catch {
    /* ignore quota / private mode */
  }
}

export function clearNinaOnboardingLocal(userId) {
  try {
    localStorage.removeItem(ninaOnboardingStorageKey(userId))
  } catch {
    /* ignore */
  }
}

/** Força o tour no próximo mount (sobrevive ao redirect pós-login). */
export function requestNinaOnboardingReplay(userId) {
  try {
    clearNinaOnboardingLocal(userId)
    sessionStorage.setItem('i4_force_nina_onboarding', '1')
  } catch {
    /* ignore */
  }
}

/**
 * Consome pedido de replay (?reset_onboarding=1 ou sessionStorage).
 * @returns {boolean} true se deve reabrir o onboarding
 */
export function consumeNinaOnboardingReplay(userId) {
  let force = false
  try {
    if (sessionStorage.getItem('i4_force_nina_onboarding') === '1') {
      force = true
      sessionStorage.removeItem('i4_force_nina_onboarding')
    }
    const sp = new URLSearchParams(window.location.search)
    if (sp.get('reset_onboarding') === '1') {
      force = true
      // Remove da URL para não reabrir o tour a cada render/navegação.
      sp.delete('reset_onboarding')
      const qs = sp.toString()
      const next = `${window.location.pathname}${qs ? `?${qs}` : ''}${window.location.hash || ''}`
      window.history.replaceState(null, '', next)
    }
  } catch {
    /* ignore */
  }
  if (force) {
    clearNinaOnboardingLocal(userId)
  }
  return force
}
