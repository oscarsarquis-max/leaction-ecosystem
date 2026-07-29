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

/**
 * Painel editável do rascunho 29148 (software_saas).
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
    <div className="mt-3 rounded-xl border border-sky-300 bg-sky-50/80 p-4 text-left">
      <p className="font-display text-xs font-semibold uppercase tracking-[0.16em] text-sky-800">
        Requisitos estruturados (rascunho)
      </p>
      <p className="mt-1 text-xs text-sky-900/80">
        Revise antes de gerar o Spec. Campos vagos ou &quot;indefinido&quot; são o que o
        pipeline tende a assumir sozinho — corrija aqui.
      </p>

      <label className="mt-3 block text-xs font-semibold text-slate-700">
        Propósito / escopo
        <textarea
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
          rows={3}
          value={value.proposito_escopo || ''}
          onChange={(e) => patch({ proposito_escopo: e.target.value })}
        />
      </label>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="block text-xs font-semibold text-slate-700">
          Contexto de uso
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            value={ctx.tipo || 'indefinido'}
            onChange={(e) => patchCtx({ tipo: e.target.value })}
          >
            {CONTEXTO_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-semibold text-slate-700">
          Justificativa do contexto
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            rows={3}
            value={ctx.justificativa || ''}
            onChange={(e) => patchCtx({ justificativa: e.target.value })}
          />
        </label>
      </div>

      {(ctx.tipo || 'indefinido') === 'indefinido' ? (
        <p className="mt-2 rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-2 text-xs text-amber-950">
          Contexto ainda indefinido — escolha single ou multi-tenant antes de gerar o Spec
          para evitar que a SDD invente isolamento por tenant.
        </p>
      ) : null}

      <label className="mt-3 block text-xs font-semibold text-slate-700">
        Partes interessadas (uma por linha: papel: descrição)
        <textarea
          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900"
          rows={3}
          value={stakeholdersToText(value.partes_interessadas)}
          onChange={(e) =>
            patch({ partes_interessadas: textToStakeholders(e.target.value) })
          }
        />
      </label>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="block text-xs font-semibold text-slate-700">
          Requisitos funcionais (1 por linha)
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900"
            rows={5}
            value={listToText(value.requisitos_funcionais)}
            onChange={(e) =>
              patch({ requisitos_funcionais: textToList(e.target.value) })
            }
          />
        </label>
        <label className="block text-xs font-semibold text-slate-700">
          Requisitos não-funcionais (1 por linha)
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900"
            rows={5}
            value={listToText(value.requisitos_nao_funcionais)}
            onChange={(e) =>
              patch({ requisitos_nao_funcionais: textToList(e.target.value) })
            }
          />
        </label>
        <label className="block text-xs font-semibold text-slate-700">
          Restrições / premissas
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900"
            rows={4}
            value={listToText(value.restricoes_premissas)}
            onChange={(e) =>
              patch({ restricoes_premissas: textToList(e.target.value) })
            }
          />
        </label>
        <label className="block text-xs font-semibold text-slate-700">
          Interfaces / integrações
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900"
            rows={4}
            value={listToText(value.interfaces_integracoes)}
            onChange={(e) =>
              patch({ interfaces_integracoes: textToList(e.target.value) })
            }
          />
        </label>
      </div>
    </div>
  )
}
