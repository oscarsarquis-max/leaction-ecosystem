import { useEffect, useRef, useState } from 'react'
import { ExternalLink, Eye, EyeOff } from 'lucide-react'
import CopyableBlock from './CopyableBlock'
import FixedTextField from './FixedTextField'

const INTERACT_STYLE_MARKER = 'data-phanton-interact="1"'
const TAB_SCRIPT_MARKER = 'data-phanton-tabs="1"'

const INTERACT_STYLE_BLOCK = `<style ${INTERACT_STYLE_MARKER}>
/* Phanton: overlays decorativos não roubam clique; controles sempre clicáveis */
body::before, body::after, html::before, html::after {
  pointer-events: none !important;
}
.overlay, .backdrop, .bg-overlay, .background-overlay, .hero-overlay,
.glow, .particles, .bg-layer, [aria-hidden="true"] {
  pointer-events: none !important;
}
button, a, input, select, textarea, summary,
[role="button"], [onclick], [tabindex]:not([tabindex="-1"]),
nav, .btn, .card, .tab, .nav-btn, .axis-card, .method-card, .tab-btn {
  pointer-events: auto !important;
  position: relative;
  z-index: 5;
  cursor: pointer;
}
.tab-content.hidden { display: none !important; }
.tab-content.block { display: block !important; }
.tab-btn.is-active, .tab-btn[aria-selected="true"] {
  background: #fff !important;
  color: #0369a1 !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}
</style>`

const TAB_SWITCH_SCRIPT = `<script ${TAB_SCRIPT_MARKER}>
(function () {
  function switchTab(id) {
    var key = String(id || '');
    document.querySelectorAll('.tab-content').forEach(function (el) {
      var match =
        el.id === 'content-' + key ||
        el.id === 'panel-' + key ||
        el.getAttribute('data-tab') === key;
      el.classList.toggle('hidden', !match);
      el.classList.toggle('block', !!match);
      el.hidden = !match;
    });
    document.querySelectorAll('.tab-btn, [data-tab-target]').forEach(function (btn) {
      var btnKey =
        btn.getAttribute('data-tab-target') ||
        String(btn.id || '').replace(/^tab-/, '');
      var active = btnKey === key;
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
      btn.classList.toggle('is-active', active);
    });
  }
  window.switchTab = switchTab;
  window.showSlide = window.showSlide || function (n) {
    var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
    if (!slides.length) return;
    var i = ((n % slides.length) + slides.length) % slides.length;
    slides.forEach(function (s, idx) { s.classList.toggle('active', idx === i); });
  };
})();
</script>`

function looksLikeHtml(text) {
  if (typeof text !== 'string') return false
  const t = text.trim()
  return /^<!DOCTYPE\s+html/i.test(t) || /^<html\b/i.test(t)
}

function closeTruncatedHtml(html) {
  if (/<\/html\s*>/i.test(html)) return html
  const openDivs = Math.max(
    0,
    Math.min(
      60,
      (html.match(/<div\b/gi) || []).length - (html.match(/<\/div\s*>/gi) || []).length,
    ),
  )
  let out = html.replace(/\s*$/, '')
  if (openDivs) out += `\n${'</div>\n'.repeat(openDivs)}`
  if (!/<\/body\s*>/i.test(out)) out += '\n</body>'
  out += '\n</html>'
  return out
}

function injectBeforeBodyEnd(html, snippet) {
  if (/<\/body\s*>/i.test(html)) {
    return html.replace(/<\/body\s*>/i, `${snippet}\n</body>`)
  }
  if (/<\/html\s*>/i.test(html)) {
    return html.replace(/<\/html\s*>/i, `${snippet}\n</html>`)
  }
  return `${html.trimEnd()}\n${snippet}\n`
}

function injectStyleBlock(html, styleBlock, marker) {
  if (html.includes(marker)) return html
  if (/<\/head\s*>/i.test(html)) {
    return html.replace(/<\/head\s*>/i, `${styleBlock}\n</head>`)
  }
  if (/<body\b/i.test(html)) {
    return html.replace(/<body\b([^>]*)>/i, `<body$1>\n${styleBlock}`)
  }
  return `${styleBlock}\n${html}`
}

/**
 * Repara HTML truncado / sem switchTab / com overlays que engolem clique.
 * Assim o preview funciona mesmo em entregas antigas cortadas pelo limite de tokens.
 */
export function ensureHtmlClickable(html) {
  let text = typeof html === 'string' ? html.trim() : ''
  if (!text || !looksLikeHtml(text)) return text

  text = closeTruncatedHtml(text)

  const needsTabs =
    text.includes('switchTab(') &&
    !text.includes('function switchTab') &&
    !text.includes(TAB_SCRIPT_MARKER)
  if (needsTabs) {
    text = injectBeforeBodyEnd(text, TAB_SWITCH_SCRIPT)
  }

  return injectStyleBlock(text, INTERACT_STYLE_BLOCK, INTERACT_STYLE_MARKER)
}

export function extractHtmlCode(artifactData) {
  if (!artifactData || typeof artifactData !== 'object') return null

  const candidates = [
    artifactData.html_code,
    artifactData.html,
    artifactData.format === 'html' ? artifactData.delivery : null,
    artifactData.artifact_data?.html_code,
    artifactData.artifact_data?.html,
    artifactData.artifact_data?.format === 'html'
      ? artifactData.artifact_data?.delivery
      : null,
    looksLikeHtml(artifactData.delivery) ? artifactData.delivery : null,
    looksLikeHtml(artifactData.artifact_data?.delivery)
      ? artifactData.artifact_data.delivery
      : null,
  ]

  for (const value of candidates) {
    if (typeof value === 'string' && value.trim() && looksLikeHtml(value)) {
      return value.trim()
    }
  }
  return null
}

export default function HtmlPreview({
  htmlCode,
  title = 'Entrega final',
  editable = false,
  onChange,
}) {
  const [showPreview, setShowPreview] = useState(true)
  const [blobUrl, setBlobUrl] = useState(null)
  const iframeRef = useRef(null)
  const blobUrlRef = useRef(null)

  useEffect(() => {
    if (!htmlCode || !String(htmlCode).trim()) {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
      setBlobUrl(null)
      return undefined
    }

    const delay = editable ? 450 : 0
    const timer = window.setTimeout(() => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current)
      const safeHtml = ensureHtmlClickable(htmlCode)
      const blob = new Blob([safeHtml], { type: 'text/html;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      blobUrlRef.current = url
      setBlobUrl(url)
    }, delay)

    return () => window.clearTimeout(timer)
  }, [htmlCode, editable])

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!showPreview || !blobUrl) return undefined
    const timer = window.setTimeout(() => {
      try {
        iframeRef.current?.focus()
        iframeRef.current?.contentWindow?.focus()
      } catch {
        /* ignore */
      }
    }, 150)
    return () => window.clearTimeout(timer)
  }, [showPreview, blobUrl])

  if (!htmlCode && !editable) return null

  const openInNewTab = () => {
    if (!htmlCode) return
    const safeHtml = ensureHtmlClickable(htmlCode)
    const blob = new Blob([safeHtml], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const win = window.open(url, '_blank')
    if (!win) {
      URL.revokeObjectURL(url)
      return
    }
    window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
  }

  return (
    <div className="mt-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setShowPreview((v) => !v)}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500"
        >
          {showPreview ? (
            <>
              <EyeOff className="h-4 w-4" />
              Ocultar visualização
            </>
          ) : (
            <>
              <Eye className="h-4 w-4" />
              Visualizar entrega
            </>
          )}
        </button>
        <button
          type="button"
          onClick={openInNewTab}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-indigo-400 hover:text-indigo-700"
        >
          <ExternalLink className="h-4 w-4" />
          Abrir em nova aba
        </button>
        {showPreview ? (
          <p className="text-xs text-slate-500">
            Clique na área da apresentação para usar teclado e botões.
          </p>
        ) : null}
      </div>

      {showPreview && blobUrl ? (
        <div className="relative z-10 overflow-hidden rounded-2xl border border-indigo-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 bg-indigo-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-indigo-800">
            {title} — interativo
          </div>
          <iframe
            ref={iframeRef}
            title={title}
            src={blobUrl}
            sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups"
            className="pointer-events-auto relative z-10 h-[640px] w-full border-0 bg-white"
            tabIndex={0}
          />
        </div>
      ) : null}

      <CopyableBlock
        label="Copiar HTML"
        buttonClassName="border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-400 hover:bg-slate-700 hover:text-white"
        text={htmlCode || ''}
      >
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Código HTML{editable ? ' (editável)' : ''}
        </p>
        <FixedTextField
          value={htmlCode || ''}
          readOnly={!editable}
          onChange={editable ? (e) => onChange?.(e.target.value) : undefined}
          aria-label="Código HTML gerado"
          className={editable ? 'h-72 border-amber-400 focus:ring-amber-400' : ''}
        />
      </CopyableBlock>
    </div>
  )
}
