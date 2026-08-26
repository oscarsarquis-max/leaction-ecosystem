import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import axios from 'axios'

const STORAGE_KEY = 'phanton_auth_token'

const AuthContext = createContext(null)

/** Interceptor global: todas as chamadas axios levam Bearer se houver sessão. */
let _interceptorId = null
function ensureAxiosAuthInterceptor() {
  if (_interceptorId != null) return
  _interceptorId = axios.interceptors.request.use((config) => {
    const t = localStorage.getItem(STORAGE_KEY)
    if (t) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${t}`
    }
    return config
  })
}

export function AuthProvider({ apiBase, children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY) || '')
  const [user, setUser] = useState(null)
  const [booting, setBooting] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    ensureAxiosAuthInterceptor()
  }, [])

  const clearSession = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setToken('')
    setUser(null)
  }, [])

  const applyToken = useCallback(
    async (nextToken) => {
      if (!nextToken) {
        clearSession()
        return null
      }
      const { data } = await axios.get(`${apiBase}/api/auth/me`, {
        headers: { Authorization: `Bearer ${nextToken}` },
        timeout: 15000,
      })
      localStorage.setItem(STORAGE_KEY, nextToken)
      setToken(nextToken)
      setUser(data)
      return data
    },
    [apiBase, clearSession],
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setBooting(true)
      try {
        const saved = localStorage.getItem(STORAGE_KEY) || ''
        if (saved) {
          await applyToken(saved)
        } else if (!cancelled) {
          setUser(null)
        }
      } catch {
        if (!cancelled) clearSession()
      } finally {
        if (!cancelled) setBooting(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps -- boot once

  const login = useCallback(
    async (username, password) => {
      setError(null)
      const { data } = await axios.post(
        `${apiBase}/api/auth/login`,
        { username, password },
        { timeout: 20000 },
      )
      await applyToken(data.access_token)
      return data.user
    },
    [apiBase, applyToken],
  )

  const register = useCallback(
    async ({ codigo, nome, email, senha }) => {
      setError(null)
      const { data } = await axios.post(
        `${apiBase}/api/auth/register`,
        { codigo, nome, email, senha },
        { timeout: 20000 },
      )
      return data
    },
    [apiBase],
  )

  const logout = useCallback(async () => {
    try {
      if (token) {
        await axios.post(
          `${apiBase}/api/auth/logout`,
          {},
          { headers: { Authorization: `Bearer ${token}` }, timeout: 10000 },
        )
      }
    } catch {
      /* ignore */
    }
    clearSession()
  }, [apiBase, token, clearSession])

  const authHeaders = useMemo(() => {
    if (!token) return {}
    return { Authorization: `Bearer ${token}` }
  }, [token])

  const value = useMemo(
    () => ({
      token,
      user,
      booting,
      error,
      setError,
      login,
      register,
      logout,
      clearSession,
      authHeaders,
      isRestricted:
        user?.role === 'restricted_tester' || user?.nivel === 'usuario_executor',
      isAdmin: user?.role === 'admin',
      isAuthenticated: Boolean(user),
    }),
    [token, user, booting, error, login, register, logout, clearSession, authHeaders],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth fora de AuthProvider')
  return ctx
}

export function createAuthedAxios(apiBase) {
  // Instância própria precisa do interceptor — axios.create() NÃO herda
  // o interceptor do axios default (onde AuthProvider registra).
  const client = axios.create()
  client.interceptors.request.use((config) => {
    const t = localStorage.getItem(STORAGE_KEY)
    if (t) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${t}`
    }
    return config
  })
  void apiBase
  return client
}

export { STORAGE_KEY }
