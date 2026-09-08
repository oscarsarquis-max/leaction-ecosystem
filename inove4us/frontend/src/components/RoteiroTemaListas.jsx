import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import {
  rotuloBnccOption,
  bnccOptionValue,
  filtraBnccPorBusca,
} from '../lib/ementaTopicos'

/**
 * Listas BNCC + Ementa independentes + caixa de selecionados (N de cada).
 */
export default function RoteiroTemaListas({
  bnccTemas = [],
  ementaTopicos = [],
  selecionadosBncc = [],
  selecionadosEmenta = [],
  onEscolher,
  onRemover,
  onGerar,
  gerarBusy = false,
  gerarProgresso = '',
  gerarErro = '',
}) {
  const temBncc = bnccTemas.length > 0
  const temEmenta = ementaTopicos.length > 0
  const [busca, setBusca] = useState('')
  const bnccScrollRef = useRef(null)
  const bnccScrollTop = useRef(0)

  const bnccFiltrado = useMemo(
    () => filtraBnccPorBusca(bnccTemas, busca),
    [bnccTemas, busca],
  )

  const bnccCodigos = useMemo(
    () =>
      new Set(
        (selecionadosBncc || [])
          .map((b) => String(b?.habilidade_codigo || '').trim())
          .filter(Boolean),
      ),
    [selecionadosBncc],
  )
  const ementaSet = useMemo(
    () => new Set((selecionadosEmenta || []).map((t) => String(t).trim()).filter(Boolean)),
    [selecionadosEmenta],
  )

  const temBnccSel = bnccCodigos.size > 0
  const temEmentaSel = ementaSet.size > 0

  const bnccOpcoes = useMemo(
    () => bnccFiltrado.filter((b) => !bnccCodigos.has(b.habilidade_codigo || '')),
    [bnccFiltrado, bnccCodigos],
  )
  const ementaOpcoes = useMemo(
    () => ementaTopicos.filter((t) => !ementaSet.has(t)),
    [ementaTopicos, ementaSet],
  )

  useLayoutEffect(() => {
    const el = bnccScrollRef.current
    if (el) el.scrollTop = bnccScrollTop.current
  }, [bnccCodigos.size, bnccOpcoes.length])

  if (!temBncc && !temEmenta) return null

  const lembrarScroll = () => {
    bnccScrollTop.current = bnccScrollRef.current?.scrollTop || 0
  }

  return (
    <div className="space-y-3">
      <span className="field-label">Tema da aula</span>
      <p className="text-[12px] leading-relaxed text-bordo-soft">
        Pode escolher mais de um tema BNCC (obrigatório para gerar conteúdo) e
        mais de um tópico da ementa. As duas listas não se desmarcam.
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-brand-100 bg-white/80 p-2">
          <p className="px-1 pb-1 text-[11px] font-semibold uppercase tracking-wide text-bordo-soft">
            BNCC (catálogo)
          </p>
          {temBncc ? (
            <>
              <input
                type="search"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar por palavra (ex.: frações)"
                className="field-input mb-2 min-h-10 text-[13px]"
                aria-label="Buscar tema BNCC"
              />
              <ul
                ref={bnccScrollRef}
                className="max-h-56 overflow-y-auto pr-1"
                onScroll={(e) => {
                  bnccScrollTop.current = e.currentTarget.scrollTop
                }}
              >
                {bnccOpcoes.length === 0 ? (
                  <li className="px-1 py-2 text-[12px] text-bordo-soft">
                    {busca.trim()
                      ? 'Nenhum tema com essa busca.'
                      : 'Todos os temas BNCC deste recorte já estão selecionados.'}
                  </li>
                ) : (
                  bnccOpcoes.map((b) => {
                    const value = bnccOptionValue(b)
                    return (
                      <li key={b.habilidade_codigo || value}>
                        <button
                          type="button"
                          title={b.texto_oficial || `${b.habilidade_codigo || ''} — ${b.tema || ''}`}
                          onClick={() => {
                            lembrarScroll()
                            onEscolher?.({
                              fonte: 'bncc',
                              value,
                              tema: b.tema || '',
                              habilidade_codigo: b.habilidade_codigo || '',
                              texto_oficial: b.texto_oficial || '',
                            })
                          }}
                          className="mb-1 w-full rounded-lg px-2 py-1.5 text-left text-[12px] leading-snug text-bordo-deep hover:bg-brand-50"
                        >
                          {rotuloBnccOption(b, { lista: bnccTemas })}
                        </button>
                      </li>
                    )
                  })
                )}
              </ul>
            </>
          ) : (
            <p className="px-1 py-2 text-[12px] text-bordo-soft">
              Sem temas BNCC aprovados neste recorte.
            </p>
          )}
        </div>
        <div className="rounded-xl border border-brand-100 bg-white/80 p-2">
          <p className="px-1 pb-1 text-[11px] font-semibold uppercase tracking-wide text-bordo-soft">
            Ementa da escola
          </p>
          {temEmenta ? (
            <ul className="max-h-56 overflow-y-auto pr-1">
              {ementaOpcoes.length === 0 ? (
                <li className="px-1 py-2 text-[12px] text-bordo-soft">
                  Todos os tópicos da ementa já estão selecionados.
                </li>
              ) : (
                ementaOpcoes.map((t) => (
                <li key={t}>
                  <button
                    type="button"
                    onClick={() =>
                      onEscolher?.({
                        fonte: 'ementa',
                        value: t,
                        tema: t,
                        habilidade_codigo: '',
                        texto_oficial: '',
                      })
                    }
                    className="mb-1 w-full rounded-lg px-2 py-1.5 text-left text-[12px] leading-snug text-bordo-deep hover:bg-brand-50"
                  >
                    {t}
                  </button>
                </li>
              ))
              )}
            </ul>
          ) : (
            <p className="px-1 py-2 text-[12px] text-bordo-soft">
              A escola ainda não digitou tópicos nesta ementa.
            </p>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-bordo/30 bg-brand-50/50 p-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-bordo">
          Temas selecionados
        </p>
        {!temBnccSel && !temEmentaSel ? (
          <p className="mt-2 text-[12px] text-bordo-soft">Nenhum tema selecionado ainda.</p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {(selecionadosBncc || []).map((item) => (
              <li
                key={`bncc-${item.habilidade_codigo}`}
                className="flex items-start justify-between gap-2 rounded-lg bg-white px-2 py-1.5 text-[12px] text-bordo-deep"
              >
                <span>
                  <span className="font-bold text-bordo">[BNCC]</span>{' '}
                  {rotuloBnccOption(item, { lista: bnccTemas, max: 220 })}
                </span>
                <button
                  type="button"
                  className="shrink-0 text-[11px] font-semibold text-bordo hover:underline"
                  onClick={() => onRemover?.('bncc', item.habilidade_codigo)}
                >
                  Remover
                </button>
              </li>
            ))}
            {(selecionadosEmenta || []).map((t) => (
              <li
                key={`ementa-${t}`}
                className="flex items-start justify-between gap-2 rounded-lg bg-white px-2 py-1.5 text-[12px] text-bordo-deep"
              >
                <span>
                  <span className="font-bold text-bordo">[EMENTA]</span> {t}
                </span>
                <button
                  type="button"
                  className="shrink-0 text-[11px] font-semibold text-bordo hover:underline"
                  onClick={() => onRemover?.('ementa', t)}
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <span
          className="inline-block"
          title={
            temBnccSel
              ? 'Gera o conteúdo de cada tema BNCC em sequência (a ementa não entra na IA).'
              : 'Selecione um tema BNCC para gerar o conteúdo sugerido.'
          }
        >
          <button
            type="button"
            data-testid="gerar-conteudo-sugerido"
            disabled={!temBnccSel || gerarBusy}
            onClick={() => onGerar?.()}
            className="rounded-xl bg-bordo px-4 py-2.5 text-sm font-bold text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-50"
          >
            {gerarBusy
              ? gerarProgresso || 'Gerando conteúdo…'
              : 'Gerar conteúdo sugerido'}
          </button>
        </span>
        {!temBnccSel ? (
          <p className="mt-1 text-[12px] text-amber-800">
            Selecione pelo menos um tema BNCC para gerar. A ementa sozinha não gera
            conteúdo.
          </p>
        ) : (
          <p className="mt-1 text-[12px] text-bordo-soft">
            Cada tema BNCC gera o próprio bloco (cache por habilidade × turma). A
            ementa não entra na IA.
          </p>
        )}
        {gerarErro ? (
          <p className="mt-1 text-[12px] text-amber-800">{gerarErro}</p>
        ) : null}
      </div>
    </div>
  )
}
