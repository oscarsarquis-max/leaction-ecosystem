import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import DictationField from './DictationField'

function hojeISO() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : String(n))
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function formatHora(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const p = (n) => (n < 10 ? `0${n}` : String(n))
  return `${p(d.getHours())}:${p(d.getMinutes())}`
}

function diarioParaTexto(entries) {
  if (!Array.isArray(entries) || !entries.length) return ''
  return entries
    .map((e) => {
      const card = e.card || 'Card'
      const trajeto =
        e.deLabel || e.paraLabel
          ? `${e.deLabel || e.de || '?'} → ${e.paraLabel || e.para || '?'}`
          : ''
      const hora = formatHora(e.em)
      const head = [card, trajeto, hora].filter(Boolean).join(' · ')
      return `• ${head}\n  ${e.nota || ''}`
    })
    .join('\n\n')
}

/**
 * Pós-execução da aula: diário de bordo (notas das movimentações) +
 * sugestão opcional à coordenação (curadoria School só no fechamento).
 */
export default function RelatoAulaModal({
  aula,
  missao,
  onCancel,
  onSubmit,
  busy,
  temAlunosPei: temAlunosPeiProp,
  diarioBordo = [],
  metodologiaNome = '',
  aulaContexto = '',
}) {
  const [ocorrenciaTipo, setOcorrenciaTipo] = useState('concluida')
  const [ocorrenciaNota, setOcorrenciaNota] = useState('')
  const [relatoExtra, setRelatoExtra] = useState('')
  const [participantes, setParticipantes] = useState('')
  const [criarProximo, setCriarProximo] = useState(false)
  const [dataProximo, setDataProximo] = useState(hojeISO())
  const [tituloProximo, setTituloProximo] = useState('')
  const [sugestaoCoord, setSugestaoCoord] = useState('')
  const [adaptouPei, setAdaptouPei] = useState(false)
  const [peiAdaptacaoTexto, setPeiAdaptacaoTexto] = useState('')
  const [peiAlunoNome, setPeiAlunoNome] = useState('')
  const [error, setError] = useState('')

  const temAlunosPei = Boolean(
    temAlunosPeiProp ??
      aula?.tem_alunos_pei ??
      aula?.meta_json?.tem_alunos_pei ??
      (Array.isArray(aula?.kanban_pei) && aula.kanban_pei.length > 0),
  )

  const diarioEntries = useMemo(
    () => (Array.isArray(diarioBordo) ? diarioBordo : []),
    [diarioBordo],
  )
  const diarioTexto = useMemo(() => diarioParaTexto(diarioEntries), [diarioEntries])

  useEffect(() => {
    setOcorrenciaTipo('concluida')
    setOcorrenciaNota('')
    setRelatoExtra('')
    setParticipantes('')
    setCriarProximo(false)
    setDataProximo(hojeISO())
    setTituloProximo(missao ? `Continuidade · ${missao}`.slice(0, 180) : '')
    setSugestaoCoord('')
    setAdaptouPei(false)
    setPeiAdaptacaoTexto('')
    setPeiAlunoNome(
      String(
        aula?.meta_json?.aluno_nome ||
          aula?.aluno_nome ||
          '',
      ).trim(),
    )
    setError('')
  }, [aula, missao])

  useEffect(() => {
    if (!aula) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [aula])

  if (!aula || typeof document === 'undefined') return null

  function handleSubmit(e) {
    e.preventDefault()
    const sugestao = sugestaoCoord.trim()
    const relatoSala = [diarioTexto, relatoExtra.trim()].filter(Boolean).join('\n\n').trim()
    if (!relatoSala && !diarioEntries.length) {
      setError(
        'Não há anotações do diário de bordo. Mova cards na mesa com observação ou acrescente uma nota de síntese.',
      )
      return
    }
    if (!participantes.trim()) {
      setError('Informe quem participou.')
      return
    }
    if (
      (ocorrenciaTipo === 'interrompida' || ocorrenciaTipo === 'substituicao') &&
      !ocorrenciaNota.trim()
    ) {
      setError(
        ocorrenciaTipo === 'interrompida'
          ? 'Descreva o que faltou e por quê.'
          : 'Descreva o que substituiu o planejado.',
      )
      return
    }
    if (criarProximo && !dataProximo) {
      setError('Informe a data do próximo evento.')
      return
    }
    if (adaptouPei && !peiAdaptacaoTexto.trim()) {
      setError('Descreva o que funcionou melhor no PEI nesta metodologia.')
      return
    }
    if (adaptouPei && !peiAlunoNome.trim()) {
      setError('Informe o nome do aluno a que a adaptação de PEI se refere.')
      return
    }
    onSubmit?.({
      relato_sala: relatoSala || 'Aula concluída (diário de bordo registrado na mesa).',
      participantes: participantes.trim(),
      ocorrencia_tipo: ocorrenciaTipo,
      ocorrencia_nota: ocorrenciaNota.trim(),
      criar_proximo: ocorrenciaTipo !== 'interrompida' && criarProximo,
      data_proximo: criarProximo ? dataProximo : undefined,
      titulo_proximo: criarProximo ? (tituloProximo || '').trim() : undefined,
      has_teacher_adaptations: Boolean(sugestao),
      teacher_adaptation_text: sugestao || undefined,
      sugestao_coordenacao: sugestao || undefined,
      texto_sugestao: sugestao || undefined,
      metodologia_usada: metodologiaNome || undefined,
      aula_contexto: aulaContexto || undefined,
      has_pei_adaptations: adaptouPei,
      pei_adaptation_text: adaptouPei ? peiAdaptacaoTexto.trim() : undefined,
      aluno_nome: adaptouPei ? peiAlunoNome.trim() : undefined,
    })
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center overflow-y-auto bg-bordo-deep/55 p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="relato-aula-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onCancel?.()
      }}
    >
      <form
        onSubmit={handleSubmit}
        className="my-2 w-full max-w-lg rounded-2xl border border-brand-200 bg-white p-5 shadow-soft sm:my-4"
        style={{ maxHeight: 'min(92vh, 920px)', overflowY: 'auto' }}
      >
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
          Encerramento da aula
        </p>
        <h2 id="relato-aula-title" className="mt-1 font-display text-xl font-bold text-bordo-deep">
          Fechamento da aula
        </h2>
        <p className="mt-2 text-sm text-bordo-soft">
          Como a aula aconteceu? Nenhuma opção altera a agenda automaticamente — é só um
          registro honesto. A curadoria só recebe sugestão se você escrever na área 2.
        </p>

        <fieldset className="mt-4 rounded-xl border border-brand-100 bg-white p-3">
          <legend className="px-1 text-[10px] font-bold uppercase tracking-[0.16em] text-brand-600">
            Aconteceu como planejado?
          </legend>
          <div className="mt-2 space-y-2">
            {[
              { id: 'concluida', label: 'Concluída', hint: 'Seguiu o planejado até o fim.' },
              {
                id: 'interrompida',
                label: 'Interrompida / parcial',
                hint: 'Não deu tempo. Fica aguardando continuação — sem remarcar sozinha.',
              },
              {
                id: 'substituicao',
                label: 'Substituição',
                hint: 'O planejado não foi seguido; outra coisa foi feita no lugar.',
              },
              {
                id: 'trabalho_monitorado',
                label: 'Trabalho monitorado',
                hint: 'Acompanhamento ou trabalho independente, sem a metodologia planejada.',
              },
            ].map((opt) => (
              <label
                key={opt.id}
                className="flex cursor-pointer items-start gap-2 rounded-lg border border-brand-100 px-3 py-2"
              >
                <input
                  type="radio"
                  name="ocorrencia_tipo"
                  className="mt-1 accent-bordo"
                  checked={ocorrenciaTipo === opt.id}
                  onChange={() => {
                    setOcorrenciaTipo(opt.id)
                    if (opt.id === 'interrompida') setCriarProximo(false)
                  }}
                />
                <span>
                  <span className="block text-sm font-bold text-bordo">{opt.label}</span>
                  <span className="block text-xs text-bordo-soft">{opt.hint}</span>
                </span>
              </label>
            ))}
          </div>
          {ocorrenciaTipo !== 'concluida' ? (
            <div className="mt-3">
              <label className="block text-xs font-bold uppercase tracking-wide text-bordo">
                {ocorrenciaTipo === 'interrompida'
                  ? 'O que faltou, e por quê?'
                  : ocorrenciaTipo === 'substituicao'
                    ? 'O que foi feito no lugar?'
                    : 'Nota (opcional)'}
              </label>
              <div className="mt-1.5">
                <DictationField
                  as="textarea"
                  rows={3}
                  className="field-input min-h-[72px] resize-y"
                  value={ocorrenciaNota}
                  onChange={setOcorrenciaNota}
                  placeholder={
                    ocorrenciaTipo === 'interrompida'
                      ? 'Ex.: Faltou o último card — o ensaio acabou atrasando…'
                      : ocorrenciaTipo === 'substituicao'
                        ? 'Ex.: Troquei pelo debate porque a turma pediu…'
                        : 'Se quiser, descreva o que observou.'
                  }
                />
              </div>
            </div>
          ) : null}
        </fieldset>

        {/* Área 1 — Anotações Gerais (diário de bordo) */}
        <section className="mt-4 rounded-xl border border-brand-100 bg-brand-50/40 p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-brand-600">
            Área 1 · Anotações gerais
          </p>
          <h3 className="mt-1 text-sm font-bold text-bordo">Diário de bordo</h3>
          <p className="mt-0.5 text-xs text-bordo-soft">
            Notas registradas nas transições dos cards (somente leitura).
          </p>
          {diarioEntries.length ? (
            <ul className="mt-3 max-h-48 space-y-2 overflow-y-auto pr-0.5">
              {diarioEntries.map((e, i) => (
                <li
                  key={`${e.card}-${e.em || i}-${i}`}
                  className="rounded-lg border border-brand-100 bg-white px-3 py-2 text-sm text-bordo"
                >
                  <p className="text-[10px] font-bold uppercase tracking-wide text-bordo-soft">
                    {e.card}
                    {e.deLabel || e.paraLabel
                      ? ` · ${e.deLabel || e.de || '?'} → ${e.paraLabel || e.para || '?'}`
                      : ''}
                    {formatHora(e.em) ? ` · ${formatHora(e.em)}` : ''}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed">{e.nota}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 rounded-lg border border-dashed border-brand-200 bg-white px-3 py-4 text-center text-xs text-bordo-soft">
              Nenhuma observação de movimentação ainda. Você pode acrescentar uma síntese
              abaixo.
            </p>
          )}

          <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-bordo">
            Síntese adicional (opcional)
          </label>
          <div className="mt-1.5">
            <DictationField
              as="textarea"
              rows={3}
              className="field-input min-h-[80px] resize-y"
              value={relatoExtra}
              onChange={setRelatoExtra}
              placeholder="Digite ou dite um complemento ao diário…"
            />
          </div>
        </section>

        <label className="mt-4 block text-xs font-bold uppercase tracking-wide text-bordo">
          Quem participou
        </label>
        <div className="mt-1.5">
          <DictationField
            as="textarea"
            rows={3}
            className="field-input min-h-[80px] resize-y"
            value={participantes}
            onChange={setParticipantes}
            placeholder="Nomes, turmas, papéis (líder, guardião…)…"
          />
        </div>

        {/* Área 2 — Sugestão para a Coordenação */}
        <section className="mt-4 rounded-xl border border-violet-200 bg-violet-50/50 p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-violet-700">
            Área 2 · Sugestão para a coordenação
          </p>
          <label className="mt-1 block text-sm font-bold text-bordo">
            Teve alguma ideia de adaptação metodológica para esta aula que a coordenação
            deveria incluir no padrão da escola?
          </label>
          <p className="mt-0.5 text-xs text-bordo-soft">
            Opcional. Se preenchido, a sugestão vai para a curadoria da escola neste fechamento.
            {metodologiaNome ? ` Metodologia: ${metodologiaNome}.` : ''}
          </p>
          <div className="mt-2">
            <DictationField
              as="textarea"
              rows={4}
              className="field-input min-h-[100px] resize-y"
              value={sugestaoCoord}
              onChange={setSugestaoCoord}
              placeholder="Ex.: Incluir rotina visual no passo 2; encurtar o ciclo de feedback…"
            />
          </div>
        </section>

        {temAlunosPei ? (
          <>
            <label className="mt-4 flex cursor-pointer items-start gap-2 rounded-xl border border-emerald-100 bg-emerald-50/60 px-3 py-3">
              <input
                type="checkbox"
                className="mt-1 accent-emerald-600"
                checked={adaptouPei}
                onChange={(e) => {
                  setAdaptouPei(e.target.checked)
                  if (!e.target.checked) {
                    setPeiAdaptacaoTexto('')
                    setPeiAlunoNome('')
                  }
                }}
              />
              <span className="text-sm text-bordo">
                <span className="font-bold">
                  Adaptei a execução do PEI para o(s) aluno(s)
                </span>
                <span className="mt-0.5 block text-xs text-bordo-soft">
                  Envia feedback de trincheira para a curadoria do PEI na escola.
                </span>
              </span>
            </label>
            {adaptouPei ? (
              <div className="mt-3 space-y-3">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wide text-bordo">
                    Nome do aluno
                  </label>
                  <input
                    type="text"
                    className="field-input mt-1.5"
                    value={peiAlunoNome}
                    onChange={(e) => setPeiAlunoNome(e.target.value)}
                    placeholder="Ex.: João Pedro"
                    required={adaptouPei}
                    autoComplete="off"
                  />
                  <p className="mt-1 text-[11px] text-bordo-soft">
                    Identifica o aluno na fila de curadoria da escola (best-effort por nome).
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wide text-bordo">
                    O que funcionou melhor para o aluno nesta metodologia?
                  </label>
                  <div className="mt-1.5">
                    <DictationField
                      as="textarea"
                      rows={3}
                      className="field-input min-h-[90px] resize-y"
                      value={peiAdaptacaoTexto}
                      onChange={setPeiAdaptacaoTexto}
                      placeholder="Ex.: Apoio visual curto + tempo extra na estação de entrega…"
                    />
                  </div>
                </div>
              </div>
            ) : null}
          </>
        ) : null}

        {ocorrenciaTipo === 'interrompida' ? (
          <p className="mt-4 rounded-xl border border-amber-100 bg-amber-50/70 px-3 py-3 text-xs text-bordo">
            Esta aula fica aguardando continuação. Juntar objetivos ou agendar a Parte 2
            aparece na <span className="font-bold">próxima aula</span> da mesma turma e
            disciplina — nunca sozinho.
          </p>
        ) : (
          <label className="mt-4 flex cursor-pointer items-start gap-2 rounded-xl border border-brand-100 bg-brand-50/50 px-3 py-3">
            <input
              type="checkbox"
              className="mt-1 accent-bordo"
              checked={criarProximo}
              onChange={(e) => setCriarProximo(e.target.checked)}
            />
            <span className="text-sm text-bordo">
              <span className="font-bold">Criar novo evento a partir deste</span>
              <span className="mt-0.5 block text-xs text-bordo-soft">
                Fica vinculado no mapa de realizações como desdobramento.
              </span>
            </span>
          </label>
        )}

        {criarProximo ? (
          <div className="mt-3 space-y-3 rounded-xl border border-brand-100 bg-white p-3">
            <div>
              <label className="text-xs font-bold uppercase tracking-wide text-bordo">Data</label>
              <input
                type="date"
                className="field-input mt-1"
                value={dataProximo}
                onChange={(e) => setDataProximo(e.target.value)}
                required={criarProximo}
              />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-wide text-bordo">
                Título do próximo evento
              </label>
              <input
                className="field-input mt-1"
                value={tituloProximo}
                onChange={(e) => setTituloProximo(e.target.value)}
                placeholder="Ex.: Retomada · validação com a turma"
              />
            </div>
          </div>
        ) : null}

        {error ? <p className="mt-3 text-xs font-semibold text-brand-700">{error}</p> : null}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="btn-ghost !px-4 !py-2 text-sm"
            onClick={onCancel}
            disabled={busy}
          >
            Cancelar
          </button>
          <button type="submit" className="btn-primary !px-4 !py-2 text-sm" disabled={busy}>
            {busy ? 'Salvando…' : 'Concluir realização'}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  )
}
