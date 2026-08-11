import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const AuthContext = createContext(null)

const STORAGE_KEY = 'school_auth_user_v1'

function readStored() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

function writeStored(user) {
  try {
    if (user) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    else sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

export function AuthProvider({ children }) {
  const [user, setUserState] = useState(() => readStored())
  const [booting, setBooting] = useState(true)

  const setUser = useCallback((next) => {
    setUserState(next)
    writeStored(next)
  }, [])

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
    } catch {
      /* ignore */
    }
    setUser(null)
  }, [setUser])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/auth/me', { credentials: 'include' })
        if (res.ok) {
          const body = await res.json()
          if (!cancelled && body.user) setUser(body.user)
        } else if (!cancelled && !readStored()) {
          setUser(null)
        }
      } catch {
        /* mantém cache de sessão */
      } finally {
        if (!cancelled) setBooting(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [setUser])

  const value = useMemo(
    () => ({
      user,
      setUser,
      logout,
      booting,
      authenticated: Boolean(user),
    }),
    [user, setUser, logout, booting],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth fora de AuthProvider')
  return ctx
}

/** Instituição da sessão do gestor — nunca usar UUID fixo / VITE_INSTITUICAO_ID. */
export function useInstituicaoId() {
  const { user } = useAuth()
  return user?.instituicao_id || null
}
