import { useEffect, useId, useRef, useState } from 'react'
import mermaid from 'mermaid'

let mermaidReady = false

function ensureMermaid() {
  if (mermaidReady) return
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: 'neutral',
    flowchart: { curve: 'basis', htmlLabels: true },
  })
  mermaidReady = true
}

/**
 * Renderiza diagrama Mermaid de arquitetura (SDD).
 */
export default function ArchitectureMermaid({
  source,
  title = 'Arquitetura',
  className = '',
}) {
  const reactId = useId().replace(/:/g, '')
  const hostRef = useRef(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const code = String(source || '').trim()
    if (!code || !hostRef.current) {
      if (hostRef.current) hostRef.current.innerHTML = ''
      setError(null)
      return undefined
    }

    let cancelled = false
    ensureMermaid()
    const renderId = `sdd-arch-${reactId}-${Date.now()}`

    ;(async () => {
      try {
        const { svg } = await mermaid.render(renderId, code)
        if (cancelled || !hostRef.current) return
        hostRef.current.innerHTML = svg
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err?.message || 'Falha ao renderizar diagrama')
        if (hostRef.current) hostRef.current.innerHTML = ''
      }
    })()

    return () => {
      cancelled = true
    }
  }, [source, reactId])

  if (!String(source || '').trim()) return null

  return (
    <figure className={`text-left ${className}`}>
      <figcaption className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
        {title}
      </figcaption>
      <div
        ref={hostRef}
        className="overflow-x-auto rounded-lg bg-slate-50/80 p-3 [&_svg]:mx-auto [&_svg]:max-w-full"
      />
      {error ? (
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-[11px] text-amber-800">
          {String(source).trim()}
          {'\n\n'}({error})
        </pre>
      ) : null}
    </figure>
  )
}
