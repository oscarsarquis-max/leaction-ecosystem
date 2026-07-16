import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import BrandLogo from '../components/BrandLogo'
import DictationField from '../components/DictationField'

export default function Acesso() {
  const navigate = useNavigate()
  const { setUser } = useAuth()
  const [step, setStep] = useState('email') // email | lead | code
  const [email, setEmail] = useState('')
  const [nome, setNome] = useState('')
  const [empresa, setEmpresa] = useState('')
  const [code, setCode] = useState('')
  const [hint, setHint] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function enterSession(user) {
    setUser(user)
    navigate('/mesa-do-inovador', { replace: true })
  }

  async function handleCheckEmail(e) {
    e.preventDefault()
    setError('')
    setHint('')
    setBusy(true)
    try {
      const data = await api.checkEmail(email.trim())
      if (data.status === 'granted') {
        enterSession(data.user)
        return
      }
      setStep('lead')
    } catch (err) {
      setError(err.message || 'Não foi possível validar o e-mail.')
    } finally {
      setBusy(false)
    }
  }

  async function handleRegisterLead(e) {
    e.preventDefault()
    setError('')
    setHint('')
    setBusy(true)
    try {
      const data = await api.registerLead({
        nome: nome.trim(),
        email: email.trim(),
        empresa: empresa.trim(),
      })
      if (data.status === 'granted') {
        enterSession(data.user)
        return
      }
      setCode('')
      setStep('code')
      setHint('Enviamos um código para o seu e-mail. Digite-o abaixo para validar o acesso.')
    } catch (err) {
      setError(err.message || 'Não foi possível concluir o cadastro.')
    } finally {
      setBusy(false)
    }
  }

  async function handleVerifyCode(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const data = await api.verifyCode(email.trim(), code.trim())
      enterSession(data.user)
    } catch (err) {
      setError(err.message || 'Código inválido.')
    } finally {
      setBusy(false)
    }
  }

  const subtitle =
    step === 'email'
      ? 'Informe seu e-mail. Se houver solicitação ativa, o acesso é liberado na hora.'
      : step === 'lead'
        ? 'Cadastro rápido. Em seguida geramos e enviamos o código de acesso.'
        : 'Digite o código que enviamos para o seu e-mail.'

  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6 py-16">
      <div className="rounded-3xl border border-brand-100 bg-white/85 p-8 shadow-soft backdrop-blur">
        <div className="mb-6 flex flex-col items-center text-center">
          <BrandLogo
            variant="access"
            className="h-56 w-auto max-w-full rounded-2xl object-contain shadow-soft ring-1 ring-brand-100 sm:h-64"
            alt="INOVE4US — tecnologia e inovação"
          />
          <p className="mt-4 text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">
            Inovação e Agilidade
          </p>
        </div>
        <h1 className="font-display text-3xl font-bold tracking-tight text-bordo sm:text-4xl">
          Acesso
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-bordo-soft/90">{subtitle}</p>

        {step === 'email' ? (
          <form onSubmit={handleCheckEmail} className="mt-8 space-y-4">
            <div>
              <label htmlFor="email" className="field-label">
                E-mail
              </label>
              <DictationField
                id="email"
                type="email"
                required
                autoFocus
                autoComplete="email"
                value={email}
                onChange={setEmail}
                className="field-input"
                placeholder="voce@empresa.com"
                continuous={false}
              />
            </div>
            {error ? (
              <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-700">{error}</p>
            ) : null}
            <button type="submit" className="btn-primary w-full" disabled={busy}>
              {busy ? 'Verificando…' : 'Continuar'}
            </button>
          </form>
        ) : null}

        {step === 'lead' ? (
          <form onSubmit={handleRegisterLead} className="mt-8 space-y-4">
            <div>
              <label htmlFor="nome" className="field-label">
                Nome
              </label>
              <DictationField
                id="nome"
                type="text"
                required
                autoFocus
                value={nome}
                onChange={setNome}
                className="field-input"
                placeholder="Seu nome completo"
                continuous={false}
              />
            </div>
            <div>
              <label htmlFor="email-lead" className="field-label">
                E-mail
              </label>
              <DictationField
                id="email-lead"
                type="email"
                required
                value={email}
                onChange={setEmail}
                className="field-input"
                continuous={false}
              />
            </div>
            <div>
              <label htmlFor="empresa" className="field-label">
                Empresa <span className="font-normal normal-case tracking-normal text-brand-400">(opcional)</span>
              </label>
              <DictationField
                id="empresa"
                type="text"
                value={empresa}
                onChange={setEmpresa}
                className="field-input"
                placeholder="Instituição ou empresa"
                continuous={false}
              />
              <p className="mt-1.5 text-xs leading-snug text-bordo-soft/80">
                Se você for inovador solo ou ainda não tiver vínculo institucional, deixe em branco.
              </p>
            </div>
            {error ? (
              <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-700">{error}</p>
            ) : null}
            <div className="flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                className="btn-ghost w-full"
                disabled={busy}
                onClick={() => {
                  setStep('email')
                  setError('')
                  setHint('')
                }}
              >
                Voltar
              </button>
              <button type="submit" className="btn-primary w-full" disabled={busy}>
                {busy ? 'Enviando…' : 'Gerar e enviar código'}
              </button>
            </div>
          </form>
        ) : null}

        {step === 'code' ? (
          <form onSubmit={handleVerifyCode} className="mt-8 space-y-4">
            <div>
              <label htmlFor="email-code" className="field-label">
                E-mail
              </label>
              <DictationField
                id="email-code"
                type="email"
                required
                value={email}
                onChange={setEmail}
                className="field-input"
                continuous={false}
              />
            </div>
            <div>
              <label htmlFor="code" className="field-label">
                Código de acesso
              </label>
              <DictationField
                id="code"
                type="text"
                required
                autoFocus
                autoComplete="one-time-code"
                value={code}
                onChange={(v) => setCode(String(v || '').toUpperCase())}
                className="field-input tracking-widest"
                placeholder="LA-XXXXXX"
                continuous={false}
              />
            </div>
            {hint ? (
              <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-bordo-soft">{hint}</p>
            ) : null}
            {error ? (
              <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-700">{error}</p>
            ) : null}
            <div className="flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                className="btn-ghost w-full"
                disabled={busy}
                onClick={() => {
                  setStep('lead')
                  setError('')
                }}
              >
                Voltar
              </button>
              <button type="submit" className="btn-primary w-full" disabled={busy}>
                {busy ? 'Validando…' : 'Entrar'}
              </button>
            </div>
          </form>
        ) : null}
      </div>
    </main>
  )
}
