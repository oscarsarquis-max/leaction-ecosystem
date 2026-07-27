import { useEffect, useMemo, useRef, useState } from 'react'
import { Braces, ChevronDown, ChevronUp, PencilLine } from 'lucide-react'
import CopyableBlock from './CopyableBlock'
import CursorPromptPreview, { extractCursorPrompt } from './CursorPromptPreview'
import FixedTextField from './FixedTextField'
import HtmlPreview, { extractHtmlCode } from './HtmlPreview'

function cloneJson(value) {
  if (value == null) return value
  return JSON.parse(JSON.stringify(value))
}

function stringifyPretty(value) {
  if (value == null) return ''
  return JSON.stringify(value, null, 2)
}

function unwrapArtifact(raw) {
  if (!raw || typeof raw !== 'object') return raw
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

function EditableField({
  label,
  value,
  editable,
  onChange,
  multiline = true,
  rows = 3,
}) {
  if (!editable) {
    return (
      <Section title={label}>
        {value ? (
          <p className="whitespace-pre-wrap break-words">{value}</p>
        ) : (
          <p className="italic text-slate-500">—</p>
        )}
      </Section>
    )
  }
  return (
    <Section title={label}>
      <textarea
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        className="w-full resize-y rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:ring-2 focus:ring-amber-400"
      />
    </Section>
  )
}

function KeyValueBlock({ data, editable, onChangeField }) {
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
          <dd className="mt-1">
            {editable ? (
              <textarea
                value={String(value)}
                onChange={(e) => onChangeField?.(key, e.target.value)}
                rows={2}
                className="w-full resize-y rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:ring-2 focus:ring-amber-400"
              />
            ) : (
              <span className="whitespace-pre-wrap text-sm text-slate-800">{String(value)}</span>
            )}
          </dd>
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

function setField(data, key, value) {
  return { ...(data || {}), [key]: value }
}

function MethodologyView({ data, editable, onPatch }) {
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
    'observacoes',
    'observações',
    'recomendacoes',
    'recomendações',
  ])
  const notasKey = ['notas', 'notes', 'observacoes', 'observações', 'recomendacoes', 'recomendações'].find(
    (k) => data?.[k] != null,
  ) || 'notas'
  const notasRaw = data?.[notasKey] ?? ''
  const notas = Array.isArray(notasRaw)
    ? notasRaw.filter(Boolean).join('\n')
    : String(notasRaw || '')
  const principios = asList(data.principios || data.principles)
  const principiosText = principios
    .map((item) => (typeof item === 'string' ? item : JSON.stringify(item)))
    .join('\n')

  return (
    <div className="space-y-4">
      <EditableField
        label="Metodologia"
        value={data.metodologia || data.methodology || ''}
        editable={editable}
        rows={2}
        onChange={(v) => onPatch(setField(data, data.metodologia != null ? 'metodologia' : 'methodology', v))}
      />
      <EditableField
        label="Notas"
        value={notas}
        editable={editable}
        rows={4}
        onChange={(v) => onPatch(setField(data, notasKey, v))}
      />
      <EditableField
        label="Objetivo"
        value={data.objetivo || data.objective || data.objetivo_geral || ''}
        editable={editable}
        rows={3}
        onChange={(v) => {
          const key =
            data.objetivo != null
              ? 'objetivo'
              : data.objective != null
                ? 'objective'
                : 'objetivo_geral'
          onPatch(setField(data, key, v))
        }}
      />
      {editable ? (
        <EditableField
          label="Princípios (um por linha)"
          value={principiosText}
          editable
          rows={4}
          onChange={(v) => {
            const lines = v.split('\n').map((s) => s.trim()).filter(Boolean)
            const key = data.principios != null ? 'principios' : data.principles != null ? 'principles' : 'principios'
            onPatch(setField(data, key, lines))
          }}
        />
      ) : (
        <Section title="Princípios">
          <BulletList items={data.principios || data.principles} />
        </Section>
      )}
      <KeyValueBlock
        data={rest}
        editable={editable}
        onChangeField={(key, value) => onPatch(setField(data, key, value))}
      />
    </div>
  )
}

function ResearchView({ data, editable, onPatch }) {
  const achados = asList(data.achados || data.findings || data).filter(
    (item) => item && typeof item === 'object',
  )

  if (!achados.length && typeof data === 'object' && !Array.isArray(data)) {
    return (
      <KeyValueBlock
        data={data}
        editable={editable}
        onChangeField={(key, value) => onPatch(setField(data, key, value))}
      />
    )
  }

  const listKey = data.achados != null ? 'achados' : data.findings != null ? 'findings' : 'achados'

  const updateAchado = (index, field, value) => {
    const next = achados.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    onPatch({ ...data, [listKey]: next })
  }

  return (
    <div className="space-y-4">
      {data.nome || data.fase ? (
        editable ? (
          <EditableField
            label="Nome"
            value={data.nome || data.fase || ''}
            editable
            rows={1}
            onChange={(v) => onPatch(setField(data, data.nome != null ? 'nome' : 'fase', v))}
          />
        ) : (
          <p className="text-sm text-slate-600">{data.nome || data.fase}</p>
        )
      ) : null}
      <div className="space-y-3">
        {achados.map((item, index) => {
          const link = item.url || item.fonte || item.link
          if (!editable) {
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
          }
          return (
            <article
              key={index}
              className="space-y-2 rounded-xl border border-amber-200 bg-amber-50/40 p-3"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                Achado {index + 1}
              </p>
              <input
                value={item.titulo || item.title || ''}
                onChange={(e) =>
                  updateAchado(index, item.titulo != null ? 'titulo' : 'title', e.target.value)
                }
                className="w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-amber-400"
                placeholder="Título"
              />
              <textarea
                value={item.resumo || item.summary || ''}
                onChange={(e) =>
                  updateAchado(index, item.resumo != null ? 'resumo' : 'summary', e.target.value)
                }
                rows={3}
                className="w-full resize-y rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-400"
                placeholder="Resumo"
              />
              <textarea
                value={
                  item.relacao_com_pedido ||
                  item.relacao_com_metodologia ||
                  item.relacao ||
                  ''
                }
                onChange={(e) => {
                  const field =
                    item.relacao_com_pedido != null
                      ? 'relacao_com_pedido'
                      : item.relacao_com_metodologia != null
                        ? 'relacao_com_metodologia'
                        : 'relacao'
                  updateAchado(index, field, e.target.value)
                }}
                rows={2}
                className="w-full resize-y rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-400"
                placeholder="Relação"
              />
              <input
                value={link || ''}
                onChange={(e) => {
                  const field =
                    item.url != null ? 'url' : item.fonte != null ? 'fonte' : 'link'
                  updateAchado(index, field, e.target.value)
                }}
                className="w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-amber-400"
                placeholder="URL / fonte"
              />
            </article>
          )
        })}
      </div>
    </div>
  )
}

function SynthesisView({ data, editable, onPatch }) {
  const cards = asList(data.dinamica_passo_a_passo || data.cards || data.passos)
  const pontos = asList(data.pontos_chave || data.key_points)
  const requisitos = asList(data.requisitos_para_implementacao || data.requisitos)

  const updateListField = (keys, text) => {
    const lines = text.split('\n').map((s) => s.trim()).filter(Boolean)
    const key = keys.find((k) => data[k] != null) || keys[0]
    onPatch(setField(data, key, lines))
  }

  return (
    <div className="space-y-4">
      <EditableField
        label="Resumo da síntese"
        value={data.resumo_sintese || data.resumo || data.summary || ''}
        editable={editable}
        rows={4}
        onChange={(v) => {
          const key =
            data.resumo_sintese != null
              ? 'resumo_sintese'
              : data.resumo != null
                ? 'resumo'
                : 'resumo_sintese'
          onPatch(setField(data, key, v))
        }}
      />
      {editable ? (
        <>
          <EditableField
            label="Pontos-chave (um por linha)"
            value={pontos.map((p) => (typeof p === 'string' ? p : JSON.stringify(p))).join('\n')}
            editable
            rows={4}
            onChange={(v) => updateListField(['pontos_chave', 'key_points'], v)}
          />
          <EditableField
            label="Requisitos (um por linha)"
            value={requisitos
              .map((p) => (typeof p === 'string' ? p : JSON.stringify(p)))
              .join('\n')}
            editable
            rows={4}
            onChange={(v) =>
              updateListField(['requisitos_para_implementacao', 'requisitos'], v)
            }
          />
        </>
      ) : (
        <>
          <Section title="Pontos-chave">
            <BulletList items={data.pontos_chave || data.key_points} />
          </Section>
          <Section title="Requisitos para implementação">
            <BulletList items={data.requisitos_para_implementacao || data.requisitos} />
          </Section>
        </>
      )}
      {cards.length ? (
        <Section title="Passo a passo">
          <div className="space-y-3">
            {cards.map((card, index) => {
              if (!editable) {
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
              }

              const cardsKey =
                data.dinamica_passo_a_passo != null
                  ? 'dinamica_passo_a_passo'
                  : data.cards != null
                    ? 'cards'
                    : 'passos'

              if (typeof card === 'string') {
                return (
                  <textarea
                    key={index}
                    value={card}
                    onChange={(e) => {
                      const next = cards.map((c, i) => (i === index ? e.target.value : c))
                      onPatch(setField(data, cardsKey, next))
                    }}
                    rows={2}
                    className="w-full resize-y rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-400"
                  />
                )
              }

              return (
                <article
                  key={index}
                  className="space-y-2 rounded-xl border border-amber-200 bg-amber-50/40 p-3"
                >
                  <input
                    value={card.titulo_do_card || card.titulo || card.title || ''}
                    onChange={(e) => {
                      const field =
                        card.titulo_do_card != null
                          ? 'titulo_do_card'
                          : card.titulo != null
                            ? 'titulo'
                            : 'title'
                      const next = cards.map((c, i) =>
                        i === index ? { ...c, [field]: e.target.value } : c,
                      )
                      onPatch(setField(data, cardsKey, next))
                    }}
                    className="w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-amber-400"
                    placeholder="Título do passo"
                  />
                  <textarea
                    value={
                      card.como_executar_detalhado || card.descricao || card.description || ''
                    }
                    onChange={(e) => {
                      const field =
                        card.como_executar_detalhado != null
                          ? 'como_executar_detalhado'
                          : card.descricao != null
                            ? 'descricao'
                            : 'description'
                      const next = cards.map((c, i) =>
                        i === index ? { ...c, [field]: e.target.value } : c,
                      )
                      onPatch(setField(data, cardsKey, next))
                    }}
                    rows={3}
                    className="w-full resize-y rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-400"
                    placeholder="Como executar"
                  />
                </article>
              )
            })}
          </div>
        </Section>
      ) : null}
    </div>
  )
}

function GenericDescriptiveView({ data, editable, onPatch }) {
  if (data == null) return <p className="text-sm text-slate-500">Sem artefato.</p>
  if (typeof data === 'string') {
    if (!editable) {
      return <p className="whitespace-pre-wrap text-sm text-slate-800">{data}</p>
    }
    return (
      <textarea
        value={data}
        onChange={(e) => onPatch(e.target.value)}
        rows={8}
        className="w-full resize-y rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-400"
      />
    )
  }
  if (Array.isArray(data)) {
    if (data.every((item) => item && typeof item === 'object' && (item.titulo || item.title))) {
      return (
        <ResearchView
          data={{ achados: data }}
          editable={editable}
          onPatch={(next) => onPatch(next.achados || next)}
        />
      )
    }
    if (!editable) return <BulletList items={data} />
    return (
      <EditableField
        label="Itens (um por linha)"
        value={data.map((item) => (typeof item === 'string' ? item : JSON.stringify(item))).join('\n')}
        editable
        rows={6}
        onChange={(v) =>
          onPatch(
            v
              .split('\n')
              .map((s) => s.trim())
              .filter(Boolean),
          )
        }
      />
    )
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
      return <MethodologyView data={data} editable={editable} onPatch={onPatch} />
    }
    if (data.achados || data.findings) {
      return <ResearchView data={data} editable={editable} onPatch={onPatch} />
    }
    if (data.resumo_sintese || data.dinamica_passo_a_passo || data.pontos_chave) {
      return <SynthesisView data={data} editable={editable} onPatch={onPatch} />
    }
    return (
      <div className="space-y-3">
        <KeyValueBlock
          data={data}
          editable={editable}
          onChangeField={(key, value) => onPatch(setField(data, key, value))}
        />
        {Object.entries(data).map(([key, value]) => {
          if (value == null || typeof value !== 'object') return null
          return (
            <Section key={key} title={String(key).replaceAll('_', ' ')}>
              {Array.isArray(value) ? (
                editable ? (
                  <textarea
                    value={JSON.stringify(value, null, 2)}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value)
                        onPatch(setField(data, key, parsed))
                      } catch {
                        /* ignore until valid */
                      }
                    }}
                    rows={6}
                    className="w-full resize-y rounded-lg border border-amber-300 bg-white p-2 font-mono text-xs outline-none focus:ring-2 focus:ring-amber-400"
                  />
                ) : (
                  <BulletList items={value} />
                )
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

/** Atualiza campos de entrega HTML/Markdown no artefato. */
function patchDeliveryFields(artifact, text, { isHtml }) {
  const next = cloneJson(artifact) || {}
  const target =
    next.artifact_data && typeof next.artifact_data === 'object' ? next.artifact_data : next

  target.delivery = text
  if (isHtml) {
    target.html_code = text
    target.format = 'html'
    delete target.cursor_prompt
  } else {
    target.format = 'markdown'
    target.cursor_prompt = text
    delete target.html_code
  }

  if (next.artifact_data && typeof next.artifact_data === 'object') {
    next.delivery = text
    if (isHtml) {
      next.html_code = text
      next.format = 'html'
      delete next.cursor_prompt
    } else {
      next.format = 'markdown'
      next.cursor_prompt = text
      delete next.html_code
    }
  }

  return next
}

export default function ArtifactView({
  artifactData,
  phaseId,
  name,
  editable = false,
  onChange,
}) {
  const [draft, setDraft] = useState(() => cloneJson(artifactData))
  const [jsonText, setJsonText] = useState(() => stringifyPretty(artifactData))
  const [jsonError, setJsonError] = useState(null)
  const [showJson, setShowJson] = useState(Boolean(editable))
  const dirtyRef = useRef(false)
  const baselineRef = useRef(stringifyPretty(artifactData))

  // Sincroniza com o servidor sem apagar edições locais
  useEffect(() => {
    const incoming = stringifyPretty(artifactData)
    if (dirtyRef.current && editable) return
    if (incoming === baselineRef.current) return
    baselineRef.current = incoming
    dirtyRef.current = false
    setDraft(cloneJson(artifactData))
    setJsonText(incoming)
    setJsonError(null)
  }, [artifactData, editable])

  useEffect(() => {
    if (editable) setShowJson(true)
  }, [editable])

  const commitDraft = (next) => {
    dirtyRef.current = true
    setDraft(next)
    setJsonText(stringifyPretty(next))
    setJsonError(null)
    onChange?.(next)
  }

  const handleJsonEdit = (text) => {
    setJsonText(text)
    dirtyRef.current = true
    try {
      const parsed = JSON.parse(text)
      setDraft(parsed)
      setJsonError(null)
      onChange?.(parsed)
    } catch (err) {
      setJsonError(err.message || 'JSON inválido')
    }
  }

  const htmlCode = useMemo(() => extractHtmlCode(draft), [draft])
  const deliveryMd = useMemo(
    () => (htmlCode ? null : extractCursorPrompt(draft)),
    [draft, htmlCode],
  )
  const inner = useMemo(() => unwrapArtifact(draft), [draft])

  if (!artifactData && !draft) return null

  const handleInnerPatch = (nextInner) => {
    const current = cloneJson(draft) || {}
    if (
      current.artifact_data !== undefined &&
      (current.status || current.phase || current.capability || current.meta)
    ) {
      commitDraft({ ...current, artifact_data: nextInner })
      return
    }
    commitDraft(nextInner)
  }

  return (
    <div className="mt-4 space-y-3">
      {editable ? (
        <div className="flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <PencilLine className="h-3.5 w-3.5 shrink-0" />
          Resultado editável — alterações atualizam o JSON da fase e serão salvas na aprovação.
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200/80 bg-white/70 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Resultado
        </p>

        {htmlCode ? (
          <HtmlPreview
            htmlCode={htmlCode}
            title={`Entrega — ${name || phaseId}`}
            editable={editable}
            onChange={(text) => commitDraft(patchDeliveryFields(draft, text, { isHtml: true }))}
          />
        ) : null}

        {!htmlCode && deliveryMd ? (
          <CursorPromptPreview
            prompt={deliveryMd}
            title={`Entrega — ${name || phaseId}`}
            editable={editable}
            onChange={(text) => commitDraft(patchDeliveryFields(draft, text, { isHtml: false }))}
          />
        ) : null}

        {!htmlCode && !deliveryMd ? (
          <GenericDescriptiveView
            data={inner}
            editable={editable}
            onPatch={handleInnerPatch}
          />
        ) : null}
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
        <div className="space-y-2">
          <CopyableBlock
            label="Copiar JSON"
            buttonClassName="border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-400 hover:bg-slate-700 hover:text-white"
            text={jsonText}
          >
            <FixedTextField
              value={jsonText}
              readOnly={!editable}
              onChange={editable ? (e) => handleJsonEdit(e.target.value) : undefined}
              aria-label={`Artefato JSON ${phaseId}`}
              className={editable ? 'border-amber-400 focus:ring-amber-400' : ''}
            />
          </CopyableBlock>
          {jsonError ? (
            <p className="text-xs text-red-600">JSON inválido: {jsonError}</p>
          ) : editable ? (
            <p className="text-xs text-slate-500">
              Edite o resultado acima ou o JSON — ambos ficam sincronizados.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
