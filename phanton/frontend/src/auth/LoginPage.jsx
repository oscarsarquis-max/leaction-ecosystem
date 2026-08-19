import { useState } from 'react'
import { Beaker, Loader2, Lock } from 'lucide-react'
import { useAuth } from './AuthContext'

export default function LoginPage() {
  const { login, setError, error } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [localError, setLocalError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setLocalError(null)
    setError?.(null)
    try {
      await login(username.trim(), password)
      if (typeof window !== 'undefined' && window.location.search) {
        window.history.replaceState({}, '', window.location.pathname)
      }
    } catch (err) {
      const msg =
        err.response?.data?.detail || err.message || 'Falha no login'
      setLocalError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-100 via-teal-50 to-slate-200 px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-2xl border border-teal-200 bg-white/90 p-8 shadow-lg backdrop-blur"
      >
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-teal-700 text-white">
            <Beaker className="h-6 w-6" />
          </div>
          <h1 className="font-display text-2xl font-semibold text-slate-950">
            Phanton
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Acesso por usuário e senha. Contas{' '}
            <code className="text-xs">restricted_tester</code> só veem a
            Simulação Mativas.
          </p>
        </div>

        <label className="block text-sm">
          <span className="font-semibold text-slate-700">Usuário</span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-teal-400"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>

        <label className="mt-3 block text-sm">
          <span className="font-semibold text-slate-700">Senha</span>
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-teal-400"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {(localError || error) && (
          <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {localError || error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy || !username.trim() || !password}
          className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Lock className="h-4 w-4" />
          )}
          Entrar
        </button>
      </form>
    </div>
  )
}
