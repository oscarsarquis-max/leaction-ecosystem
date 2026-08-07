import { useEffect, useState } from 'react'

const STATUS_LABEL = {
  rascunho: 'Rascunho',
  aguardando_assinaturas: 'Aguardando assinaturas',
  ativo: 'Ativa',
  arquivado: 'Arquivada',
}

function formatarData(iso) {
  if (!iso) return null
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return String(iso)
  }
}

function statusLabel(status) {
  return STATUS_LABEL[status] || status || '—'
}

function AuditoriaLinha({ assinado, data, papel }) {
  if (assinado && data) {
    return (
      <p className="text-sm text-emerald-800">
        ✅ Assinado por {papel} em {formatarData(data)}
      </p>
    )
  }
  if (assinado) {
    return (
      <p className="text-sm text-emerald-800">
        ✅ Assinado por {papel} (sem carimbo registrado)
      </p>
    )
  }
  return (
    <p className="text-sm text-slate-500">⏳ Pendente assinatura de {papel}</p>
  )
}

function CampoReadOnly({ label, value, highlight }) {
  return (
    <div
      className={
        highlight
          ? 'rounded-lg border border-violet-200 bg-violet-50/50 p-3'
          : 'rounded-lg border border-slate-100 bg-slate-50/60 p-3'
      }
    >
      <p
        className={`text-xs font-semibold uppercase tracking-wide ${
          highlight ? 'text-violet-800' : 'text-muted'
        }`}
      >
        {label}
      </p>
      <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
        {value?.trim() ? value : '—'}
      </pre>
    </div>
  )
}

/**
 * Overlay read-only do documento de uma versão (AEE ou PEI).
 */
function VisualizacaoDocumento({ tipo, doc, onVoltar }) {
  const titulo =
    tipo === 'aee'
      ? `Matriz AEE — ${doc.condicao_categoria} · Versão ${doc.versao}`
      : `PEI — ${doc.nome_completo} · Versão ${doc.versao}`

  return (
    <div className="flex max-h-[85vh] flex-col">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
            Somente leitura
          </p>
          <h3 className="text-lg font-bold text-ink">{titulo}</h3>
          <p className="text-sm text-muted">
            Status: {statusLabel(doc.status)}
          </p>
        </div>
        <button
          type="button"
          onClick={onVoltar}
          className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold hover:bg-slate-50"
        >
          ← Voltar ao histórico
        </button>
      </header>

      <div className="space-y-3 overflow-y-auto px-5 py-4">
        <div className="rounded-lg border border-slate-100 bg-white p-3">
          <AuditoriaLinha
            assinado={doc.assinado_coordenador}
            data={doc.data_assinatura_coordenador}
            papel="Coordenação"
          />
          <AuditoriaLinha
            assinado={doc.assinado_psicopedagogo}
            data={doc.data_assinatura_psicopedagogo}
            papel="Psicopedagogia"
          />
        </div>

        {tipo === 'aee' ? (
          <>
            <CampoReadOnly label="Texto geral / política da escola" value={doc.texto_escola} />
            <CampoReadOnly
              label="Campos de Experiência (Adaptações Metodológicas)"
              value={doc.campos_experiencia_metodologica}
              highlight
            />
          </>
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              <CampoReadOnly label="Matrícula" value={doc.matricula} />
              <CampoReadOnly label="Responsável" value={doc.nome_responsavel} />
              <CampoReadOnly label="Condição AEE" value={doc.condicao_categoria} />
              <CampoReadOnly
                label="Matriz AEE vinculada"
                value={doc.aee_versao != null ? `v${doc.aee_versao}` : '—'}
              />
            </div>
            <CampoReadOnly
              label="Perfil atual / habilidades"
              value={doc.perfil_atual_habilidades}
            />
            <CampoReadOnly
              label="Barreiras identificadas"
              value={doc.barreiras_identificadas}
            />
            <CampoReadOnly
              label="Metas de desenvolvimento"
              value={doc.metas_desenvolvimento}
            />
            <CampoReadOnly label="Recursos assistivos" value={doc.recursos_assistivos} />
            <CampoReadOnly
              label="Critérios de avaliação flexibilizados"
              value={doc.criterios_avaliacao_flexibilizados}
            />
            <CampoReadOnly
              label="Campos de Experiência (Adaptação Metodológica Individual)"
              value={doc.experiencias_adaptadas_individuais}
              highlight
            />
          </>
        )}
      </div>
    </div>
  )
}

/**
 * Modal de histórico de versões (AEE por condição ou PEI por aluno).
 *
 * @param {'aee'|'pei'} tipo
 * @param {string} titulo
 * @param {string} fetchUrl — endpoint que retorna { versoes: [...] }
 * @param {() => void} onClose
 */
export default function ModalHistoricoVersoes({ tipo, titulo, fetchUrl, onClose }) {
  const [versoes, setVersoes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [doc, setDoc] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const res = await fetch(fetchUrl, { credentials: 'include' })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha ao carregar histórico')
        if (!cancelled) setVersoes(Array.isArray(body.versoes) ? body.versoes : [])
      } catch (e) {
        if (!cancelled) setError(e.message || 'Erro ao carregar histórico')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [fetchUrl])

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') {
        if (doc) setDoc(null)
        else onClose?.()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [doc, onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-historico-titulo"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.()
      }}
    >
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl">
        {doc ? (
          <VisualizacaoDocumento tipo={tipo} doc={doc} onVoltar={() => setDoc(null)} />
        ) : (
          <>
            <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
              <div>
                <h2 id="modal-historico-titulo" className="text-lg font-bold text-ink">
                  ⏱️ Histórico de Versões
                </h2>
                <p className="mt-0.5 text-sm text-muted">{titulo}</p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg px-2 py-1 text-lg text-slate-500 hover:bg-slate-100"
                aria-label="Fechar"
              >
                ×
              </button>
            </header>

            <div className="overflow-y-auto px-5 py-4">
              {loading ? (
                <p className="text-sm text-muted">Carregando histórico…</p>
              ) : null}
              {error ? (
                <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {error}
                </p>
              ) : null}
              {!loading && !error && !versoes.length ? (
                <p className="text-sm text-muted">Nenhuma versão registrada.</p>
              ) : null}

              <ul className="space-y-3">
                {versoes.map((v) => (
                  <li
                    key={v.id}
                    className="rounded-xl border border-slate-200 bg-slate-50/40 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-bold text-ink">
                          Versão {v.versao} ({statusLabel(v.status)})
                        </p>
                        <p className="mt-0.5 text-xs text-muted">
                          Criada em {formatarData(v.created_at) || '—'}
                        </p>
                        <div className="mt-2 space-y-0.5">
                          <AuditoriaLinha
                            assinado={v.assinado_coordenador}
                            data={v.data_assinatura_coordenador}
                            papel="Coordenação"
                          />
                          <AuditoriaLinha
                            assinado={v.assinado_psicopedagogo}
                            data={v.data_assinatura_psicopedagogo}
                            papel="Psicopedagogia"
                          />
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setDoc(v)}
                        className="rounded-xl bg-violet-600 px-3 py-2 text-sm font-bold text-white hover:bg-violet-700"
                      >
                        Visualizar Documento
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
