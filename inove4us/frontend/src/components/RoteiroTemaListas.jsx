import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import {
  rotuloBnccOption,
  bnccOptionValue,
  filtraBnccPorBusca,
} from '../lib/ementaTopicos'

/**
 * Listas BNCC + Ementa independentes + caixa de selecionados.
 * BNCC e Ementa podem coexistir. Scroll da lista não reseta ao escolher.
 */
export default function RoteiroTemaListas({
  bnccTemas = [],
  ementaTopicos = [],
  selecionadoBncc = null,
  selecionadoEmenta = '',
  onEscolher,
  onRemover,
  onGerar,
  gerarBusy = false,
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

  const bnccCodigo = String(selecionadoBncc?.habilidade_codigo || '').trim()
  const ementaValor = String(selecionadoEmenta || '').trim()
  const temBnccSel = Boolean(bnccCodigo)
  const temEmentaSel = Boolean(ementaValor)

  const bnccOpcoes = useMemo(
    () => bnccFiltrado.filter((b) => (b.habilidade_codigo || '') !== bnccCodigo),
    [bnccFiltrado, bnccCodigo],
  )
  const ementaOpcoes = useMemo(
    () => ementaTopicos.filter((t) => t !== ementaValor),
    [ementaTopicos, ementaValor],
  )

  useLayoutEffect(() => {
    const el = bnccScrollRef.current
    if (el) el.scrollTop = bnccScrollTop.current
  }, [bnccCodigo, bnccOpcoes.length])

  if (!temBncc && !temEmenta) return null

  const lembrarScroll = () => {
    bnccScrollTop.current = bnccScrollRef.current?.scrollTop || 0
  }

  return (
    <div className="space-y-3">
      <span className="field-label">Tema da aula</span>
      <p className="text-[12px] leading-relaxed text-bordo-soft">
        Escolha o tema BNCC (obrigatório para gerar conteúdo). A ementa da escola
        é só referência — as duas podem ficar selecionadas juntas.
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
                      : 'Tema BNCC já está na caixa de selecionados.'}
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
              {ementaOpcoes.map((t) => (
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
              ))}
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
            {temBnccSel ? (
              <li className="flex items-start justify-between gap-2 rounded-lg bg-white px-2 py-1.5 text-[12px] text-bordo-deep">
                <span>
                  <span className="font-bold text-bordo">[BNCC]</span>{' '}
                  {rotuloBnccOption(selecionadoBncc, { lista: bnccTemas, max: 220 })}
                </span>
                <button
                  type="button"
                  className="shrink-0 text-[11px] font-semibold text-bordo hover:underline"
                  onClick={() => onRemover?.('bncc')}
                >
                  Remover
                </button>
              </li>
            ) : null}
            {temEmentaSel ? (
              <li className="flex items-start justify-between gap-2 rounded-lg bg-white px-2 py-1.5 text-[12px] text-bordo-deep">
                <span>
                  <span className="font-bold text-bordo">[EMENTA]</span> {ementaValor}
                </span>
                <button
                  type="button"
                  className="shrink-0 text-[11px] font-semibold text-bordo hover:underline"
                  onClick={() => onRemover?.('ementa')}
                >
                  Remover
                </button>
              </li>
            ) : null}
          </ul>
        )}
      </div>

      <div>
        <span
          className="inline-block"
          title={
            temBnccSel
              ? 'Gera o conteúdo sugerido a partir do tema BNCC (a ementa não entra na IA).'
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
            {gerarBusy ? 'Gerando conteúdo…' : 'Gerar conteúdo sugerido'}
          </button>
        </span>
        {!temBnccSel ? (
          <p className="mt-1 text-[12px] text-amber-800">
            Selecione um tema BNCC para gerar. A ementa sozinha não gera conteúdo.
          </p>
        ) : (
          <p className="mt-1 text-[12px] text-bordo-soft">
            A geração usa só o BNCC. A ementa fica visível como referência da escola.
          </p>
        )}
        {gerarErro ? (
          <p className="mt-1 text-[12px] text-amber-800">{gerarErro}</p>
        ) : null}
      </div>
    </div>
  )
}
