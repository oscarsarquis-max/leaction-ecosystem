import { useEffect, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { CrmEvents, trackEvent } from '../lib/tracking'

const CMS_CACHE_KEY = 'school_acesso_cms_v5'
const CMS_CONFIG_KEY = 'inove4us-school'

function safeNextPath(raw) {
  if (!raw || typeof raw !== 'string') return null
  const t = raw.trim()
  if (!t.startsWith('/') || t.startsWith('//')) return null
  if (t.startsWith('/acesso')) return null
  return t
}

function normalizeCmsText(text) {
  return String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/\u2028|\u2029/g, '\n')
    .replace(/\\n/g, '\n')
}

function countBreaks(text) {
  return (normalizeCmsText(text).match(/\n/g) || []).length
}

function pickColumnBody(column) {
  const sub = normalizeCmsText(column?.subtitle || '').trim()
  const desc = normalizeCmsText(column?.description || '').trim()
  if (!sub) return desc
  if (!desc) return sub
  const sb = countBreaks(sub)
  const db = countBreaks(desc)
  if (db !== sb) return db > sb ? desc : sub
  return desc.length >= sub.length ? desc : sub
}

function columnVisible(col) {
  if (!col || typeof col !== 'object') return false
  if (col.visibility === false || col.visible === false) return false
  const title = String(col.title || '').trim()
  const desc = pickColumnBody(col)
  return Boolean(title || desc || col.image_url || col.image_path)
}

function Lines({ text }) {
  const lines = normalizeCmsText(text).split('\n')
  return lines.map((line, i) => (
    <span key={i}>
      {i > 0 ? <br /> : null}
      {line}
    </span>
  ))
}

function CmsBodyText({ text, className = '', style }) {
  const raw = normalizeCmsText(text).trim()
  if (!raw) return null

  const hasBullets = /(?:^|\n)\s*[•\-\*]\s+\S/.test(raw)
  if (!hasBullets) {
    return (
      <p className={`text-sm leading-relaxed ${className}`} style={style}>
        <Lines text={raw} />
      </p>
    )
  }

  const blocks = []
  let para = []
  let bullets = []

  const flushPara = () => {
    if (!para.length) return
    blocks.push({ type: 'p', text: para.join('\n') })
    para = []
  }
  const flushBullets = () => {
    if (!bullets.length) return
    blocks.push({ type: 'ul', items: bullets })
    bullets = []
  }

  for (const line of raw.split('\n')) {
    const m = line.match(/^\s*([•\-\*])\s+(.+)$/)
    if (m) {
      flushPara()
      bullets.push(m[2].trim())
      continue
    }
    flushBullets()
    if (!line.trim()) {
      flushPara()
      continue
    }
    para.push(line)
  }
  flushPara()
  flushBullets()

  return (
    <div className={`space-y-2 text-sm leading-relaxed ${className}`} style={style}>
      {blocks.map((b, i) =>
        b.type === 'ul' ? (
          <ul key={i} className="list-disc space-y-1 pl-4">
            {b.items.map((item, j) => (
              <li key={j}>{item}</li>
            ))}
          </ul>
        ) : (
          <p key={i}>
            <Lines text={b.text} />
          </p>
        ),
      )}
    </div>
  )
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
    /* ignore */
  }
}

function CmsSideColumn({ column, side, loading }) {
  if (loading && !columnVisible(column)) {
    return (
      <aside
        className={`hidden w-[min(100%,17.5rem)] shrink-0 md:block ${
          side === 'left' ? 'order-1' : 'order-3'
        }`}
        aria-hidden="true"
      >
        <div className="flex h-full min-h-[28rem] flex-col overflow-hidden rounded-3xl border border-school-100 bg-school-50/80 shadow-panel">
          <div className="h-36 shrink-0 animate-pulse bg-school-100" />
          <div className="flex flex-1 flex-col gap-3 p-5">
            <div className="h-3 w-16 animate-pulse rounded bg-school-100" />
            <div className="h-5 w-3/4 animate-pulse rounded bg-school-100" />
            <div className="h-3 w-full animate-pulse rounded bg-school-50" />
            <div className="h-3 w-5/6 animate-pulse rounded bg-school-50" />
          </div>
        </div>
      </aside>
    )
  }

  if (!columnVisible(column)) return null

  const title = String(column.title || '').trim()
  const subtitle = pickColumnBody(column)
  const pill = String(column.pill_text || column.badge_text || '').trim()
  const image = String(column.image_url || column.image_path || '').trim()
  const ctaText = String(column.cta_text || column.button_text || column.link_text || '').trim()
  const ctaUrl = String(column.cta_url || column.button_url || column.link_url || '').trim()
  const bgStart = column.bg_color_start || '#062e28'
  const bgEnd = column.bg_color_end || '#0f6b5c'
  const titleColor = column.title_color || '#ffffff'
  const subtitleColor = column.subtitle_color || 'rgba(255,255,255,0.88)'
  const pillBg = column.pill_bg_color || '#0c574b'
  const pillFg = column.pill_text_color || '#ffffff'
  const btnBg = column.button_bg_color || '#0f6b5c'
  const btnFg = column.button_text_color || '#ffffff'

  return (
    <aside
      className={`hidden w-[min(100%,17.5rem)] shrink-0 md:block ${
        side === 'left' ? 'order-1' : 'order-3'
      }`}
      aria-label={side === 'left' ? 'Conteúdo institucional' : 'Como começar'}
    >
      <article
        className="flex h-full min-h-[28rem] flex-col rounded-3xl border border-school-100/70 shadow-panel"
        style={{
          background: `linear-gradient(160deg, ${bgStart} 0%, ${bgEnd} 100%)`,
        }}
      >
        {image ? (
          <div className="relative h-36 shrink-0 overflow-hidden rounded-t-3xl">
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
            <h2
              className="whitespace-pre-line text-xl font-semibold leading-snug"
              style={{ color: titleColor }}
            >
              {title}
            </h2>
          ) : null}
          {subtitle ? (
            <CmsBodyText text={subtitle} className="min-w-0 break-words" style={{ color: subtitleColor }} />
          ) : null}
          {ctaText && ctaUrl ? (
            <a
              href={ctaUrl}
              className="mt-auto inline-flex shrink-0 items-center justify-center rounded-xl px-3 py-2 text-sm font-semibold transition hover:opacity-90"
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

/**
 * Página de acesso B2B — mesmo modelo do inove4us (/acesso + 2 colunas CMS Hub),
 * adaptada ao visual school (teal / IBM Plex).
 */
export default function Acesso() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = safeNextPath(searchParams.get('next'))
  const { authenticated, setUser, booting } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
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
        const res = await fetch(
          `/api/cms/site?config_key=${encodeURIComponent(CMS_CONFIG_KEY)}`,
          { credentials: 'include' },
        )
        const data = await res.json().catch(() => ({}))
        if (cancelled) return
        const landing = data?.landing_page_data || {}
        const columns = Array.isArray(landing.columns) ? landing.columns : []
        const col1 =
          landing.coluna1 && typeof landing.coluna1 === 'object' ? landing.coluna1 : null
        const col0 = columns[0] && typeof columns[0] === 'object' ? columns[0] : null
        const nextLeft =
          !col1
            ? col0
            : !col0
              ? col1
              : countBreaks(pickColumnBody(col1)) >= countBreaks(pickColumnBody(col0))
                ? col1
                : col0
        const nextRight = columns[1] || null
        const hero = landing.hero && typeof landing.hero === 'object' ? landing.hero : {}
        const heroCta =
          landing.hero_cta && typeof landing.hero_cta === 'object' ? landing.hero_cta : {}
        const line = normalizeCmsText(
          hero.subtitle ||
            hero.description ||
            heroCta.subtitle ||
            heroCta.description ||
            '',
        ).trim()
        if (columnVisible(nextLeft) || columnVisible(nextRight)) {
          setLeftCol(nextLeft)
          setRightCol(nextRight)
          setHeroLine(line)
          writeCmsCache(nextLeft, nextRight, line)
        }
      } catch {
        /* mantém cache */
      } finally {
        if (!cancelled) setCmsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (!booting && authenticated) {
    return <Navigate to={nextPath || '/'} replace />
  }

  async function handleLogin(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível entrar')
      setUser(body.user)
      void trackEvent(CrmEvents.LOGIN_SUCESSO, {
        url: '/acesso',
        idUsuario: body.user?.id ?? null,
      })
      navigate(nextPath || '/', { replace: true })
    } catch (err) {
      setError(err.message || 'Erro ao entrar')
    } finally {
      setBusy(false)
    }
  }

  const hasLeft = columnVisible(leftCol)
  const hasRight = columnVisible(rightCol)
  const showSides = cmsLoading || hasLeft || hasRight

  return (
    <main className="flex min-h-screen items-center justify-center bg-panel px-4 py-10 sm:px-6 sm:py-14">
      <div
        className={`relative flex w-full items-stretch gap-4 ${
          showSides ? 'max-w-6xl justify-center' : 'max-w-4xl'
        }`}
      >
        <CmsSideColumn column={leftCol} side="left" loading={cmsLoading} />

        {!cmsLoading && !hasLeft ? (
          <div
            className="pointer-events-none relative z-0 hidden w-[42%] shrink-0 overflow-hidden rounded-l-[1.75rem] md:block"
            aria-hidden="true"
            style={{
              background:
                'linear-gradient(160deg, #062e28 0%, #0f6b5c 55%, #d5efe8 100%)',
            }}
          >
            <div
              className="absolute inset-0"
              style={{
                background:
                  'linear-gradient(90deg, rgba(243,245,247,0) 0%, rgba(243,245,247,0.15) 40%, rgba(243,245,247,0.75) 78%, #f3f5f7 100%)',
              }}
            />
          </div>
        ) : null}

        <div
          className="pointer-events-none absolute inset-x-0 top-0 z-0 h-40 overflow-hidden rounded-t-3xl md:hidden"
          aria-hidden="true"
          style={{
            background: 'linear-gradient(160deg, #062e28 0%, #0f6b5c 100%)',
          }}
        >
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-panel/40 to-panel" />
        </div>

        <div
          className={`relative z-10 order-2 w-full rounded-3xl border border-school-100 bg-white/95 p-8 shadow-panel backdrop-blur-sm md:max-w-lg ${
            !cmsLoading && !hasLeft ? 'md:-ml-14' : ''
          }`}
        >
          <div className="mb-6 flex flex-col items-center text-center">
            <img
              src="/images/logo-inove4us-school.png"
              alt="inove4us School"
              className="h-44 w-auto max-w-full object-contain sm:h-52"
            />
            <p className="mt-2 text-xs font-semibold uppercase tracking-[0.18em] text-school-600">
              Torre de Controle
            </p>
            {heroLine ? (
              <CmsBodyText text={heroLine} className="mt-2 max-w-sm text-muted" />
            ) : (
              <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">
                Governança pedagógica da escola — metodologias, PEI e calendário.
              </p>
            )}
          </div>

          <h1 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Acesso</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Entre com o e-mail e a senha do gestor. Um login, zonas conforme o seu perfil.
          </p>

          <form onSubmit={handleLogin} className="mt-8 space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                E-mail
              </span>
              <input
                type="email"
                required
                autoFocus
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="gestor@escola.edu.br"
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
                Senha
              </span>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
              />
            </label>
            {error ? (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={busy || booting}
              className="w-full rounded-lg bg-school-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-school-600 disabled:opacity-60"
            >
              {busy ? 'Entrando…' : 'Entrar'}
            </button>
          </form>
        </div>

        <CmsSideColumn column={rightCol} side="right" loading={cmsLoading} />
      </div>
    </main>
  )
}
