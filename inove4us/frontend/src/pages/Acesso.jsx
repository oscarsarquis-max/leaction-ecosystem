import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { requestNinaOnboardingReplay } from '../lib/ninaOnboarding'
import BrandLogo from '../components/BrandLogo'
import DictationField from '../components/DictationField'

const CMS_CACHE_KEY = 'i4_acesso_cms_v1'

function safeNextPath(raw) {
  if (!raw || typeof raw !== 'string') return null
  const t = raw.trim()
  if (!t.startsWith('/') || t.startsWith('//')) return null
  if (t.startsWith('/acesso')) return null
  return t
}

function columnVisible(col) {
  if (!col || typeof col !== 'object') return false
  if (col.visibility === false || col.visible === false) return false
  const title = String(col.title || '').trim()
  const desc = String(col.description || col.subtitle || '').trim()
  return Boolean(title || desc || col.image_url || col.image_path)
}

function readCmsCache() {
  try {
    const raw = sessionStorage.getItem(CMS_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return null
    return parsed
  } catch {
    return null
  }
}

function writeCmsCache(left, right, heroLine) {
  try {
    sessionStorage.setItem(
      CMS_CACHE_KEY,
      JSON.stringify({
        left: left || null,
        right: right || null,
        heroLine: heroLine || '',
        savedAt: Date.now(),
      }),
    )
  } catch {
    /* ignore quota */
  }
}

function CmsSideColumn({ column, side, loading }) {
  if (loading && !columnVisible(column)) {
    return (
      <aside
        className={`hidden w-[min(100%,17.5rem)] shrink-0 lg:block ${
          side === 'left' ? 'order-1' : 'order-3'
        }`}
        aria-hidden="true"
      >
        <div className="flex h-full min-h-[28rem] flex-col overflow-hidden rounded-3xl border border-brand-100/60 bg-brand-50/80 shadow-soft">
          <div className="h-36 shrink-0 animate-pulse bg-brand-100" />
          <div className="flex flex-1 flex-col gap-3 p-5">
            <div className="h-3 w-16 animate-pulse rounded bg-brand-200" />
            <div className="h-5 w-3/4 animate-pulse rounded bg-brand-200" />
            <div className="h-3 w-full animate-pulse rounded bg-brand-100" />
            <div className="h-3 w-5/6 animate-pulse rounded bg-brand-100" />
          </div>
        </div>
      </aside>
    )
  }

  if (!columnVisible(column)) return null

  const title = String(column.title || '').trim()
  const subtitle = String(column.description || column.subtitle || '').trim()
  const pill = String(column.pill_text || column.badge_text || '').trim()
  const image = String(column.image_url || column.image_path || '').trim()
  const ctaText = String(column.cta_text || column.button_text || column.link_text || '').trim()
  const ctaUrl = String(column.cta_url || column.button_url || column.link_url || '').trim()
  const bgStart = column.bg_color_start || '#450a0a'
  const bgEnd = column.bg_color_end || '#7f1d1d'
  const titleColor = column.title_color || '#ffffff'
  const subtitleColor = column.subtitle_color || 'rgba(255,255,255,0.85)'
  const pillBg = column.pill_bg_color || '#b91c1c'
  const pillFg = column.pill_text_color || '#ffffff'
  const btnBg = column.button_bg_color || '#b91c1c'
  const btnFg = column.button_text_color || '#ffffff'

  return (
    <aside
      className={`hidden w-[min(100%,17.5rem)] shrink-0 lg:block ${
        side === 'left' ? 'order-1' : 'order-3'
      }`}
      aria-label={side === 'left' ? 'Conteúdo institucional' : 'Como começar'}
    >
      <article
        className="flex h-full min-h-[28rem] flex-col overflow-hidden rounded-3xl border border-brand-100/60 shadow-soft"
        style={{
          background: `linear-gradient(160deg, ${bgStart} 0%, ${bgEnd} 100%)`,
        }}
      >
        {image ? (
          <div className="relative h-36 shrink-0 overflow-hidden">
            <img src={image} alt="" className="h-full w-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
          </div>
        ) : null}
        <div className="flex flex-1 flex-col gap-3 p-5">
          {pill ? (
            <span
              className="inline-flex w-fit rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider"
              style={{ backgroundColor: pillBg, color: pillFg }}
            >
              {pill}
            </span>
          ) : null}
          {title ? (
            <h2 className="font-display text-xl font-bold leading-snug" style={{ color: titleColor }}>
              {title}
            </h2>
          ) : null}
          {subtitle ? (
            <p className="text-sm leading-relaxed" style={{ color: subtitleColor }}>
              {subtitle}
            </p>
          ) : null}
          {ctaText && ctaUrl ? (
            <a
              href={ctaUrl}
              className="mt-auto inline-flex items-center justify-center rounded-xl px-3 py-2 text-sm font-semibold transition hover:opacity-90"
              style={{ backgroundColor: btnBg, color: btnFg }}
              target={ctaUrl.startsWith('http') ? '_blank' : undefined}
              rel={ctaUrl.startsWith('http') ? 'noreferrer' : undefined}
            >
              {ctaText}
            </a>
          ) : null}
        </div>
      </article>
    </aside>
  )
}

export default function Acesso() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = safeNextPath(searchParams.get('next'))
  const { setUser } = useAuth()
  const [step, setStep] = useState('email') // email | lead | code
  const [email, setEmail] = useState('')
  const [nome, setNome] = useState('')
  const [empresa, setEmpresa] = useState('')
  const [code, setCode] = useState('')
  const [hint, setHint] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const cached = readCmsCache()
  const [leftCol, setLeftCol] = useState(() => cached?.left || null)
  const [rightCol, setRightCol] = useState(() => cached?.right || null)
  const [heroLine, setHeroLine] = useState(() => cached?.heroLine || '')
  const [cmsLoading, setCmsLoading] = useState(
    () => !(columnVisible(cached?.left) || columnVisible(cached?.right)),
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await api.getCmsSite('inove4us')
        if (cancelled) return
        const landing = data?.landing_page_data || {}
        const columns = Array.isArray(landing.columns) ? landing.columns : []
        const col1 = landing.coluna1 && typeof landing.coluna1 === 'object' ? landing.coluna1 : null
        const nextLeft = col1 || columns[0] || null
        const nextRight = columns[1] || null
        const hero = landing.hero && typeof landing.hero === 'object' ? landing.hero : {}
        const line = String(hero.description || hero.subtitle || '').trim()

        const hasContent = columnVisible(nextLeft) || columnVisible(nextRight)
        if (hasContent) {
          setLeftCol(nextLeft)
          setRightCol(nextRight)
          setHeroLine(line)
          writeCmsCache(nextLeft, nextRight, line)
        }
        // Falha/vazio: mantém cache anterior — evita sumir/aparecer as colunas
      } catch {
        // mantém cache / estado atual
      } finally {
        if (!cancelled) setCmsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  function enterSession(user) {
    setUser(user)
    try {
      const sp = new URLSearchParams(window.location.search)
      if (sp.get('reset_onboarding') === '1' && user?.id_clie) {
        requestNinaOnboardingReplay(user.id_clie)
      }
    } catch {
      /* ignore */
    }
    navigate(nextPath || '/mesa-do-inovador', { replace: true })
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

  const salaImg = encodeURI('/imagens/sala de aula inove4us.jpeg')
  const hasLeft = columnVisible(leftCol)
  const hasRight = columnVisible(rightCol)
  // Layout estável em lg: reserva laterais enquanto carrega ou se houver conteúdo
  const showSides = cmsLoading || hasLeft || hasRight

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6 sm:py-14">
      <div
        className={`relative flex w-full items-stretch gap-4 ${
          showSides ? 'max-w-6xl justify-center' : 'max-w-4xl'
        }`}
      >
        <CmsSideColumn column={leftCol} side="left" loading={cmsLoading} />

        {/* Foto de atmosfera só quando já sabemos que não há coluna esquerda */}
        {!cmsLoading && !hasLeft ? (
          <div
            className="pointer-events-none relative z-0 hidden w-[46%] shrink-0 overflow-hidden rounded-l-[1.75rem] md:block"
            aria-hidden="true"
          >
            <img
              src={salaImg}
              alt=""
              className="absolute inset-0 h-full w-full object-cover object-center"
            />
            <div
              className="absolute inset-0"
              style={{
                background:
                  'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.08) 38%, rgba(255,255,255,0.55) 68%, rgba(255,255,255,0.92) 88%, #fff 100%)',
              }}
            />
            <div
              className="absolute inset-0"
              style={{
                background:
                  'linear-gradient(180deg, rgba(127,29,29,0.18) 0%, transparent 40%, rgba(69,10,10,0.12) 100%)',
              }}
            />
          </div>
        ) : null}

        {/* Mobile: faixa de atmosfera atrás da caixa */}
        <div
          className="pointer-events-none absolute inset-x-0 top-0 z-0 h-44 overflow-hidden rounded-t-3xl md:hidden"
          aria-hidden="true"
        >
          <img src={salaImg} alt="" className="h-full w-full object-cover object-[center_30%]" />
          <div className="absolute inset-0 bg-gradient-to-b from-white/25 via-white/70 to-white" />
        </div>

        <div
          className={`relative z-10 order-2 w-full rounded-3xl border border-brand-100 bg-white/92 p-8 shadow-soft backdrop-blur-sm md:max-w-lg md:bg-white/88 ${
            !cmsLoading && !hasLeft ? 'md:-ml-16' : ''
          }`}
        >
          <div className="mb-6 flex flex-col items-center text-center">
            <BrandLogo
              variant="access"
              className="h-56 w-auto max-w-full rounded-2xl object-contain shadow-soft ring-1 ring-brand-100 sm:h-64"
              alt="INOVE4US — tecnologia e inovação"
            />
            <p className="mt-4 text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">
              Inovação na hora que precisa
            </p>
            {heroLine ? (
              <p className="mt-2 max-w-sm text-sm leading-relaxed text-bordo-soft/90">{heroLine}</p>
            ) : null}
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
                  Empresa{' '}
                  <span className="font-normal normal-case tracking-normal text-brand-400">
                    (opcional)
                  </span>
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

        <CmsSideColumn column={rightCol} side="right" loading={cmsLoading} />
      </div>
    </main>
  )
}
