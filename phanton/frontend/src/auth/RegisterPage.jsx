import { useState } from 'react'
import { Beaker, Loader2, UserPlus } from 'lucide-react'
import { useAuth } from './AuthContext'

export default function RegisterPage({ onGoLogin }) {
  const { register, setError, error } = useAuth()
  const [codigo, setCodigo] = useState('')
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [busy, setBusy] = useState(false)
  const [localError, setLocalError] = useState(null)
  const [okMsg, setOkMsg] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setLocalError(null)
    setOkMsg(null)
    setError?.(null)
    try {
      await register({
        codigo: codigo.trim(),
        nome: nome.trim(),
        email: email.trim(),
        senha,
      })
      setOkMsg('Conta criada. Entre com o e-mail e a senha.')
      setTimeout(() => onGoLogin?.(), 1200)
    } catch (err) {
      const msg =
        err.response?.data?.detail || err.message || 'Falha no cadastro'
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
            Criar conta
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Use o código de acesso que você recebeu. O login continua local no
            Phanton.
          </p>
        </div>

        <label className="block text-sm">
          <span className="font-semibold text-slate-700">Código de acesso</span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-teal-400"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            autoComplete="one-time-code"
            required
          />
        </label>

        <label className="mt-3 block text-sm">
          <span className="font-semibold text-slate-700">Nome</span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-teal-400"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            autoComplete="name"
            required
          />
        </label>

        <label className="mt-3 block text-sm">
          <span className="font-semibold text-slate-700">E-mail</span>
          <input
            type="email"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-teal-400"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </label>

        <label className="mt-3 block text-sm">
          <span className="font-semibold text-slate-700">Senha</span>
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-teal-400"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            autoComplete="new-password"
            required
            minLength={4}
          />
        </label>

        {okMsg ? (
          <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {okMsg}
          </p>
        ) : null}

        {(localError || error) && (
          <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {localError || error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy || !codigo.trim() || !nome.trim() || !email.trim() || !senha}
          className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <UserPlus className="h-4 w-4" />
          )}
          Cadastrar
        </button>

        <button
          type="button"
          onClick={() => onGoLogin?.()}
          className="mt-3 w-full text-center text-sm font-medium text-teal-800 hover:underline"
        >
          Já tenho conta — entrar
        </button>
      </form>
    </div>
  )
}
