const CONTEXTO_OPTIONS = [
  { value: 'indefinido', label: 'Indefinido (preciso decidir)' },
  { value: 'single_tenant', label: 'Single-tenant — uso interno / uma empresa' },
  { value: 'multi_tenant', label: 'Multi-tenant — produto para várias empresas' },
]

function listToText(items) {
  if (!Array.isArray(items) || !items.length) return ''
  return items.join('\n')
}

function textToList(text) {
  return String(text || '')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
}

function stakeholdersToText(items) {
  if (!Array.isArray(items) || !items.length) return ''
  return items
    .map((s) => `${s.papel || ''}: ${s.descricao || ''}`.replace(/^:\s*/, '').trim())
    .filter(Boolean)
    .join('\n')
}

function textToStakeholders(text) {
  return String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const idx = line.indexOf(':')
      if (idx === -1) return { papel: line, descricao: '' }
      return {
        papel: line.slice(0, idx).trim() || 'stakeholder',
        descricao: line.slice(idx + 1).trim(),
      }
    })
}

const fieldClass =
  'mt-1.5 w-full border-0 border-b border-slate-300 bg-transparent px-0 py-2 text-sm leading-relaxed text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-emerald-500'
const monoFieldClass = `${fieldClass} font-mono text-xs`
const selectClass =
  'mt-1.5 w-full border-0 border-b border-slate-300 bg-transparent px-0 py-2 text-sm text-slate-900 outline-none focus:border-emerald-500'

function Field({ label, hint, children }) {
  return (
    <label className="block text-left">
      <span className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
        {label}
      </span>
      {hint ? (
        <span className="mt-0.5 block text-[11px] leading-snug text-slate-400">
          {hint}
        </span>
      ) : null}
      {children}
    </label>
  )
}

function Section({ title, children }) {
  return (
    <section className="space-y-4">
      <h4 className="font-display text-sm font-semibold text-slate-900">{title}</h4>
      <div className="space-y-4">{children}</div>
    </section>
  )
}

/**
 * Rascunho editável de requisitos (software_saas) — fluxo tipográfico, sem cards.
 */
export default function RequirementsDraftPanel({ value, onChange }) {
  if (!value) return null

  const ctx = value.contexto_de_uso || { tipo: 'indefinido', justificativa: '' }

  const patch = (partial) => {
    onChange({ ...value, ...partial })
  }

  const patchCtx = (partial) => {
    patch({
      contexto_de_uso: { ...ctx, ...partial },
    })
  }

  return (
    <div className="mt-4 border-t border-slate-200 pt-4 text-left">
      <header className="mb-5">
        <p className="font-display text-sm font-semibold text-slate-950">
          Requisitos estruturados
        </p>
        <p className="mt-1 max-w-prose text-xs leading-relaxed text-slate-500">
          Revise antes de gerar o Spec. Itens vagos ou &quot;indefinido&quot; tendem a
          ser assumidos sozinhos pelo pipeline — corrija aqui.
        </p>
      </header>

      <div className="space-y-7">
        <Section title="1 · Escopo">
          <Field label="Propósito">
            <textarea
              className={fieldClass}
              rows={3}
              value={value.proposito_escopo || ''}
              onChange={(e) => patch({ proposito_escopo: e.target.value })}
            />
          </Field>
        </Section>

        <Section title="2 · Contexto de uso">
          <Field label="Modelo">
            <select
              className={selectClass}
              value={ctx.tipo || 'indefinido'}
              onChange={(e) => patchCtx({ tipo: e.target.value })}
            >
              {CONTEXTO_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Justificativa">
            <textarea
              className={fieldClass}
              rows={2}
              value={ctx.justificativa || ''}
              onChange={(e) => patchCtx({ justificativa: e.target.value })}
            />
          </Field>
          {(ctx.tipo || 'indefinido') === 'indefinido' ? (
            <p className="text-xs leading-relaxed text-amber-800">
              Contexto ainda indefinido — escolha single ou multi-tenant antes de
              gerar o Spec para evitar que a SDD invente isolamento por tenant.
            </p>
          ) : null}
        </Section>

        <Section title="3 · Pessoas">
          <Field
            label="Partes interessadas"
            hint="Uma por linha — formato papel: descrição"
          >
            <textarea
              className={monoFieldClass}
              rows={3}
              value={stakeholdersToText(value.partes_interessadas)}
              onChange={(e) =>
                patch({ partes_interessadas: textToStakeholders(e.target.value) })
              }
            />
          </Field>
        </Section>

        <Section title="4 · Requisitos">
          <Field label="Funcionais" hint="Um por linha">
            <textarea
              className={monoFieldClass}
              rows={5}
              value={listToText(value.requisitos_funcionais)}
              onChange={(e) =>
                patch({ requisitos_funcionais: textToList(e.target.value) })
              }
            />
          </Field>
          <Field label="Não-funcionais" hint="Um por linha">
            <textarea
              className={monoFieldClass}
              rows={4}
              value={listToText(value.requisitos_nao_funcionais)}
              onChange={(e) =>
                patch({ requisitos_nao_funcionais: textToList(e.target.value) })
              }
            />
          </Field>
        </Section>

        <Section title="5 · Limites e conexões">
          <Field label="Restrições e premissas" hint="Um por linha">
            <textarea
              className={monoFieldClass}
              rows={3}
              value={listToText(value.restricoes_premissas)}
              onChange={(e) =>
                patch({ restricoes_premissas: textToList(e.target.value) })
              }
            />
          </Field>
          <Field label="Interfaces e integrações" hint="Um por linha">
            <textarea
              className={monoFieldClass}
              rows={3}
              value={listToText(value.interfaces_integracoes)}
              onChange={(e) =>
                patch({ interfaces_integracoes: textToList(e.target.value) })
              }
            />
          </Field>
        </Section>
      </div>
    </div>
  )
}
