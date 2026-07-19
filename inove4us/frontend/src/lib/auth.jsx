import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { api } from './api'

const AuthContext = createContext(null)

const POLL_MS = 20_000
const PAID_POLL_MS = 1_000
const PAID_POLL_MAX_MS = 90_000

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const data = await api.me()
      const next = data.authenticated ? data.user || null : null
      setUser(next)
      return next
    } catch {
      setUser(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const applyCredits = useCallback((creditos) => {
    if (creditos == null || !Number.isFinite(Number(creditos))) return
    setUser((prev) =>
      prev ? { ...prev, creditos_ia: Number(creditos) } : prev,
    )
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  // Mantém saldo alinhado ao banco enquanto a sessão estiver ativa
  useEffect(() => {
    if (!user?.id_clie) return undefined

    const syncIfVisible = () => {
      if (document.visibilityState === 'visible') {
        void refresh()
      }
    }

    const onVisibility = () => {
      if (document.visibilityState === 'visible') void refresh()
    }

    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('focus', syncIfVisible)

    const intervalId = window.setInterval(syncIfVisible, POLL_MS)

    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('focus', syncIfVisible)
      window.clearInterval(intervalId)
    }
  }, [user?.id_clie, refresh])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setUser(null)
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{ user, setUser, loading, refresh, applyCredits, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

/**
 * Sincroniza créditos em toda navegação e, após checkout (?paid=1), faz polling
 * até o webhook do Hub refletir o novo saldo.
 */
export function AuthBalanceSync() {
  const { user, refresh } = useAuth()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const paidReturn = searchParams.get('paid') === '1'
  const baselineRef = useRef(null)

  // A cada mudança de rota, busca saldo fresco no banco
  useEffect(() => {
    if (!user?.id_clie) return undefined
    void refresh()
  }, [location.pathname, user?.id_clie, refresh])

  // Retorno do checkout: polling agressivo até o saldo subir
  useEffect(() => {
    if (!paidReturn || !user?.id_clie) return undefined

    let cancelled = false
    const started = Date.now()

    try {
      const stored = sessionStorage.getItem('i4_credits_before_checkout')
      if (stored != null) baselineRef.current = Number(stored)
    } catch {
      baselineRef.current = Number(user.creditos_ia)
    }
    if (!Number.isFinite(baselineRef.current)) {
      baselineRef.current = Number(user.creditos_ia)
    }

    async function tick() {
      const next = await refresh()
      if (cancelled) return true
      const fresh = Number(next?.creditos_ia)
      const baseline = baselineRef.current
      const updated =
        Number.isFinite(baseline) && Number.isFinite(fresh) && fresh > baseline
      if (updated || Date.now() - started >= PAID_POLL_MAX_MS) {
        try {
          sessionStorage.removeItem('i4_credits_before_checkout')
        } catch {
          /* ignore */
        }
        const nextParams = new URLSearchParams(searchParams)
        nextParams.delete('paid')
        setSearchParams(nextParams, { replace: true })
        return true
      }
      return false
    }

    let timerId
    ;(async () => {
      const done = await tick()
      if (done || cancelled) return
      timerId = window.setInterval(async () => {
        const doneNow = await tick()
        if (doneNow && timerId) window.clearInterval(timerId)
      }, PAID_POLL_MS)
    })()

    return () => {
      cancelled = true
      if (timerId) window.clearInterval(timerId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- paid return cycle
  }, [paidReturn, user?.id_clie, refresh])

  return null
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}
