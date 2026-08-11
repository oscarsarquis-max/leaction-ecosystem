import DictationField from '../DictationField'
import FieldHelp from '../FieldHelp'
import VinculoPedagogicoSelector from '../VinculoPedagogicoSelector'

const EXEMPLO_PROBLEMA =
  'Meus alunos do 1º ano têm dificuldade com trabalho em equipe e ficam dispersos na fase de criação. Preciso engajá-los num desafio real do bairro, com papéis claros e uma entrega pública.'

const EXEMPLO_OBJETIVO =
  'Que as equipes identifiquem um problema ambiental no entorno da escola, proponham uma solução de baixo custo e defendam a ideia perante uma banca.'

const EXEMPLO_TURMA = '1º ano do Ensino Médio · 35 alunos'
const EXEMPLO_DURACAO = '4 aulas'
const EXEMPLO_CONTEXTO = 'Escola pública · concurso municipal Bairro Sustentável'

const DURACAO_SUGESTOES = ['4 aulas', '6 aulas', '8 aulas', '1 mês', '1 semestre']

export default function StepProblema({
  problema,
  objetivo,
  turmaNivel,
  duracao,
  contexto,
  disciplinaId,
  onProblemaChange,
  onObjetivoChange,
  onTurmaNivelChange,
  onDuracaoChange,
  onContextoChange,
  onDisciplinaChange,
  onSubmit,
  busy,
  error,
}) {
  function usarExemplo() {
    onProblemaChange(EXEMPLO_PROBLEMA)
    onObjetivoChange?.(EXEMPLO_OBJETIVO)
    onTurmaNivelChange?.(EXEMPLO_TURMA)
    onDuracaoChange?.(EXEMPLO_DURACAO)
    onContextoChange(EXEMPLO_CONTEXTO)
  }

  return (
    <section className="mx-auto max-w-2xl animate-fade-in">
      <div className="mb-8 text-center">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-brand-600">
          Etapa 1
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep sm:text-4xl">
          O Problema
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-bordo-soft sm:text-base">
          Descreva a situação central da turma. Não é preciso colar o plano de aulas completo —
          os detalhes opcionais abaixo ajudam a orientar a análise.
        </p>
      </div>

      <div className="space-y-5 rounded-2xl border border-brand-200 bg-white/90 p-6 shadow-soft">
        <VinculoPedagogicoSelector
          disciplinaId={disciplinaId}
          onChange={onDisciplinaChange}
          autoDefault
        />

        <div>
          <div className="mb-1.5 flex flex-wrap items-end justify-between gap-2">
            <label htmlFor="problema" className="field-label !mb-0">
              Problema / situação a enfrentar
            </label>
            <button
              type="button"
              onClick={usarExemplo}
              disabled={busy}
              className="text-xs font-semibold text-brand-700 underline-offset-2 hover:underline disabled:opacity-50"
            >
              Usar exemplo
            </button>
          </div>
          <DictationField
            as="textarea"
            id="problema"
            rows={7}
            className="field-input resize-y whitespace-pre-wrap"
            placeholder="Descreva a situação ou problema que os alunos deverão enfrentar."
            value={problema}
            onChange={onProblemaChange}
          />
          <FieldHelp tip="Foque na dor ou no desafio real — evite colar cronograma, fases e lista de aulas aqui.">
            Descreva a situação ou problema que os alunos deverão enfrentar. Deixe o planejamento
            detalhado para depois.
          </FieldHelp>
        </div>

        <div className="space-y-4 rounded-xl border border-brand-100 bg-brand-50/40 p-4">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-bordo-soft">
            Detalhes opcionais
          </p>

          <div>
            <label htmlFor="objetivo" className="field-label">
              Objetivo / resultado esperado
            </label>
            <DictationField
              as="textarea"
              id="objetivo"
              rows={3}
              className="field-input resize-y"
              placeholder="O que você gostaria que os alunos resolvessem, criassem, investigassem ou compreendessem?"
              value={objetivo}
              onChange={onObjetivoChange}
            />
            <p className="mt-1 text-xs text-bordo-soft">
              O que você espera que eles consigam resolver, criar, investigar ou compreender?
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="turmaNivel" className="field-label">
                Turma / nível
              </label>
              <DictationField
                id="turmaNivel"
                type="text"
                className="field-input"
                placeholder="Ex.: 8º ano, 2º ano do Ensino Médio, graduação"
                value={turmaNivel}
                onChange={onTurmaNivelChange}
              />
            </div>
            <div>
              <label htmlFor="duracao" className="field-label">
                Duração
              </label>
              <DictationField
                id="duracao"
                type="text"
                className="field-input"
                list="wizard-duracao-sugestoes"
                placeholder="Ex.: 6 aulas, 1 mês, 1 semestre"
                value={duracao}
                onChange={onDuracaoChange}
              />
              <datalist id="wizard-duracao-sugestoes">
                {DURACAO_SUGESTOES.map((item) => (
                  <option key={item} value={item} />
                ))}
              </datalist>
            </div>
          </div>

          <div>
            <label htmlFor="contexto" className="field-label">
              Contexto
            </label>
            <DictationField
              id="contexto"
              type="text"
              className="field-input"
              placeholder="Ex.: escola pública, comunidade do entorno, laboratório, bairro"
              value={contexto}
              onChange={onContextoChange}
            />
          </div>
        </div>

        {error && (
          <p className="rounded-xl border border-brand-300 bg-brand-50 px-3 py-2 text-sm text-bordo">
            {error}
          </p>
        )}

        <button
          type="button"
          className="btn-primary w-full sm:w-auto"
          disabled={busy || problema.trim().length < 12}
          onClick={onSubmit}
        >
          {busy ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Estruturando…
            </>
          ) : (
            <>
              <i className="fa-solid fa-wand-magic-sparkles" />
              Estruturar com a inove4us
            </>
          )}
        </button>
      </div>
    </section>
  )
}
