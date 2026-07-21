import { useMemo, useState } from 'react'
import { Braces, ChevronDown, ChevronUp } from 'lucide-react'
import CopyableBlock from './CopyableBlock'
import CursorPromptPreview, { extractCursorPrompt } from './CursorPromptPreview'
import FixedTextField from './FixedTextField'
import HtmlPreview, { extractHtmlCode } from './HtmlPreview'

function unwrapArtifact(raw) {
  if (!raw || typeof raw !== 'object') return raw
  // Envelope do state_engine: { status, artifact_data, meta, ... }
  if (raw.artifact_data !== undefined && (raw.status || raw.phase || raw.capability || raw.meta)) {
    return raw.artifact_data
  }
  return raw
}

function asList(value) {
  if (Array.isArray(value)) return value
  if (value == null) return []
  return [value]
}

function Section({ title, children }) {
  if (children == null || children === false) return null
  return (
    <section className="space-y-2">
      {title ? (
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h4>
      ) : null}
      <div className="text-sm leading-relaxed text-slate-800">{children}</div>
    </section>
  )
}

function BulletList({ items }) {
  const list = asList(items).filter((item) => item != null && item !== '')
  if (!list.length) return null
  return (
    <ul className="list-disc space-y-1 pl-5">
      {list.map((item, index) => (
        <li key={index}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
      ))}
    </ul>
  )
}

function KeyValueBlock({ data }) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null
  const entries = Object.entries(data).filter(
    ([, value]) => value != null && value !== '' && typeof value !== 'object',
  )
  if (!entries.length) return null
  return (
    <dl className="space-y-3">
      {entries.map(([key, value]) => (
        <div key={key}>
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {String(key).replaceAll('_', ' ')}
          </dt>
          <dd className="mt-1 whitespace-pre-wrap text-sm text-slate-800">{String(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

function pickRest(data, exclude) {
  const rest = {}
  Object.entries(data || {}).forEach(([key, value]) => {
    if (!exclude.includes(key)) rest[key] = value
  })
  return rest
}

function MethodologyView({ data }) {
  const rest = pickRest(data, [
    'metodologia',
    'methodology',
    'objetivo',
    'objective',
    'objetivo_geral',
    'principios',
    'principles',
    'notas',
    'notes',
  ])
  return (
    <div className="space-y-4">
      <Section title="Metodologia">
        <p className="font-medium text-slate-900">{data.metodologia || data.methodology || '—'}</p>
      </Section>
      <Section title="Objetivo">
        <p>{data.objetivo || data.objective || data.objetivo_geral || null}</p>
      </Section>
      <Section title="Princípios">
        <BulletList items={data.principios || data.principles} />
      </Section>
      <Section title="Notas">
        <p className="whitespace-pre-wrap">{data.notas || data.notes || null}</p>
      </Section>
      <KeyValueBlock data={rest} />
    </div>
  )
}

function ResearchView({ data }) {
  const achados = asList(data.achados || data.findings || data)
    .filter((item) => item && typeof item === 'object')

  if (!achados.length && typeof data === 'object' && !Array.isArray(data)) {
    return <KeyValueBlock data={data} />
  }

  return (
    <div className="space-y-4">
      {data.nome || data.fase ? (
        <p className="text-sm text-slate-600">
          {data.nome || data.fase}
        </p>
      ) : null}
      <div className="space-y-3">
        {achados.map((item, index) => {
          const link = item.url || item.fonte || item.link
          return (
            <article
              key={index}
              className="rounded-xl border border-slate-200 bg-white/80 p-3"
            >
              <h5 className="font-display text-sm font-semibold text-slate-900">
                {item.titulo || item.title || `Achado ${index + 1}`}
              </h5>
              {item.resumo || item.summary ? (
                <p className="mt-1 text-sm text-slate-700">{item.resumo || item.summary}</p>
              ) : null}
              {item.relacao_com_pedido || item.relacao_com_metodologia || item.relacao ? (
                <p className="mt-2 text-xs text-slate-500">
                  <span className="font-semibold">Relação: </span>
                  {item.relacao_com_pedido || item.relacao_com_metodologia || item.relacao}
                </p>
              ) : null}
              {link ? (
                <a
                  href={link}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block break-all text-xs font-medium text-indigo-700 hover:underline"
                >
                  {link}
                </a>
              ) : null}
            </article>
          )
        })}
      </div>
    </div>
  )
}

function SynthesisView({ data }) {
  const cards = asList(data.dinamica_passo_a_passo || data.cards || data.passos)
  return (
    <div className="space-y-4">
      <Section title="Resumo da síntese">
        <p className="whitespace-pre-wrap">
          {data.resumo_sintese || data.resumo || data.summary || null}
        </p>
      </Section>
      <Section title="Pontos-chave">
        <BulletList items={data.pontos_chave || data.key_points} />
      </Section>
      <Section title="Requisitos para implementação">
        <BulletList items={data.requisitos_para_implementacao || data.requisitos} />
      </Section>
      {cards.length ? (
        <Section title="Passo a passo">
          <div className="space-y-3">
            {cards.map((card, index) => {
              if (typeof card === 'string') {
                return (
                  <article key={index} className="rounded-xl border border-slate-200 bg-white/80 p-3">
                    <p className="text-sm">{card}</p>
                  </article>
                )
              }
              return (
                <article key={index} className="rounded-xl border border-slate-200 bg-white/80 p-3">
                  <h5 className="font-display text-sm font-semibold text-slate-900">
                    {card.titulo_do_card || card.titulo || card.title || `Passo ${index + 1}`}
                  </h5>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                    {card.como_executar_detalhado || card.descricao || card.description || ''}
                  </p>
                </article>
              )
            })}
          </div>
        </Section>
      ) : null}
    </div>
  )
}

function GenericDescriptiveView({ data }) {
  if (data == null) return <p className="text-sm text-slate-500">Sem artefato.</p>
  if (typeof data === 'string') {
    return <p className="whitespace-pre-wrap text-sm text-slate-800">{data}</p>
  }
  if (Array.isArray(data)) {
    if (data.every((item) => item && typeof item === 'object' && (item.titulo || item.title))) {
      return <ResearchView data={{ achados: data }} />
    }
    return <BulletList items={data} />
  }
  if (typeof data === 'object') {
    if (data.erro || data.error) {
      return (
        <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {String(data.erro || data.error)}
        </p>
      )
    }
    if (data.metodologia || data.principios || data.objetivo) {
      return <MethodologyView data={data} />
    }
    if (data.achados || data.findings) {
      return <ResearchView data={data} />
    }
    if (data.resumo_sintese || data.dinamica_passo_a_passo || data.pontos_chave) {
      return <SynthesisView data={data} />
    }
    return (
      <div className="space-y-3">
        <KeyValueBlock data={data} />
        {Object.entries(data).map(([key, value]) => {
          if (value == null || typeof value !== 'object') return null
          return (
            <Section key={key} title={String(key).replaceAll('_', ' ')}>
              {Array.isArray(value) ? (
                <BulletList items={value} />
              ) : (
                <pre className="overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-2 text-xs text-slate-700">
                  {JSON.stringify(value, null, 2)}
                </pre>
              )}
            </Section>
          )
        })}
      </div>
    )
  }
  return <p className="text-sm text-slate-700">{String(data)}</p>
}

export default function ArtifactView({ artifactData, phaseId, name }) {
  const [showJson, setShowJson] = useState(false)

  const cursorPrompt = useMemo(() => extractCursorPrompt(artifactData), [artifactData])
  const htmlCode = useMemo(
    () => (cursorPrompt ? null : extractHtmlCode(artifactData)),
    [artifactData, cursorPrompt],
  )
  const inner = useMemo(() => unwrapArtifact(artifactData), [artifactData])
  const jsonText = useMemo(
    () => (artifactData ? JSON.stringify(artifactData, null, 2) : ''),
    [artifactData],
  )

  if (!artifactData) return null

  return (
    <div className="mt-4 space-y-3">
      <div className="rounded-xl border border-slate-200/80 bg-white/70 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Resultado
        </p>

        {cursorPrompt ? (
          <CursorPromptPreview
            prompt={cursorPrompt}
            title={`Prompt Cursor — ${name || phaseId}`}
          />
        ) : null}

        {!cursorPrompt && htmlCode ? (
          <HtmlPreview htmlCode={htmlCode} title={`Frontend — ${name || phaseId}`} />
        ) : null}

        {!cursorPrompt && !htmlCode ? <GenericDescriptiveView data={inner} /> : null}
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setShowJson((open) => !open)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
        >
          <Braces className="h-3.5 w-3.5" />
          {showJson ? 'Ocultar JSON' : 'Ver JSON'}
          {showJson ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>

      {showJson ? (
        <CopyableBlock
          label="Copiar JSON"
          buttonClassName="border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-400 hover:bg-slate-700 hover:text-white"
          text={jsonText}
        >
          <FixedTextField value={jsonText} aria-label={`Artefato JSON ${phaseId}`} />
        </CopyableBlock>
      ) : null}
    </div>
  )
}
