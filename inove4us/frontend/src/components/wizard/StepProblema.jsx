import DictationField from '../DictationField'

const EXEMPLO_CONTEXTO =
  '1º ano do Ensino Médio · turma de 35 alunos · 4 aulas de 50 min · concurso Bairro Sustentável'

const EXEMPLO_PROBLEMA = `Contexto: Sou professor(a) do 1º ano do Ensino Médio (turma de 35 alunos). A Prefeitura da nossa cidade acabou de lançar o concurso "Bairro Sustentável", focado em soluções criativas para problemas ambientais urbanos. O prêmio é um fundo de financiamento para a ideia vencedora.

O Desafio da Turma: Precisamos formar equipes de 5 alunos. Cada equipe deverá: 1) Identificar um problema ambiental real no entorno da escola (ex: descarte irregular de lixo, falta de arborização, desperdício de água), 2) Criar uma solução inovadora e de baixo custo, e 3) Montar uma apresentação persuasiva e dinâmica para defender a ideia para a banca da prefeitura.

A Dor do Professor (Meu Problema): Meus alunos têm muita dificuldade com trabalho em equipe (geralmente um aluno faz tudo e os outros só colocam o nome). Além disso, eles são dispersos na fase de criação e muito tímidos ou desorganizados na hora de apresentar projetos em público. Tenho apenas 4 aulas de 50 minutos para fazer tudo isso acontecer. Preciso de uma metodologia que engaje, defina responsabilidades claras para cada membro da equipe e os prepare para uma apresentação de impacto.`

const PLACEHOLDER_PROBLEMA = `Contexto: Sou professor(a) do … (série, tamanho da turma). Descreva o cenário, projeto ou concurso em que a turma está inserida.

O Desafio da Turma: O que os alunos precisam entregar (etapas, equipes, prazo, banca/público).

A Dor do Professor (Meu Problema): Qual a dificuldade real em sala (equipe, engajamento, apresentação, tempo…) e o que você precisa da metodologia.`

export default function StepProblema({
  problema,
  contexto,
  onProblemaChange,
  onContextoChange,
  onSubmit,
  busy,
  error,
}) {
  function usarExemplo() {
    onProblemaChange(EXEMPLO_PROBLEMA)
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
          Declare a dor real da sua turma. Iremos estruturar o seu problema, sugerir
          melhorias e ajudar a implementá-las de forma ágil. Você também pode ditar pelo
          microfone.
        </p>
      </div>

      <div className="space-y-5 rounded-2xl border border-brand-200 bg-white/90 p-6 shadow-soft">
        <div>
          <div className="mb-1.5 flex flex-wrap items-end justify-between gap-2">
            <label htmlFor="problema" className="field-label !mb-0">
              Declaração do problema
            </label>
            <button
              type="button"
              onClick={usarExemplo}
              disabled={busy}
              className="text-xs font-semibold text-brand-700 underline-offset-2 hover:underline disabled:opacity-50"
            >
              Usar exemplo (Bairro Sustentável)
            </button>
          </div>
          <DictationField
            as="textarea"
            id="problema"
            rows={12}
            className="field-input resize-y whitespace-pre-wrap"
            placeholder={PLACEHOLDER_PROBLEMA}
            value={problema}
            onChange={onProblemaChange}
          />
          <p className="mt-1.5 text-xs text-bordo-soft">
            Estrutura sugerida: Contexto → Desafio da Turma → Dor do Professor.
          </p>
        </div>

        <div>
          <label htmlFor="contexto" className="field-label">
            Localização / contexto
          </label>
          <DictationField
            id="contexto"
            type="text"
            className="field-input"
            placeholder="Ex.: 1º ano EM · 35 alunos · 4 aulas de 50 min · concurso Bairro Sustentável"
            value={contexto}
            onChange={onContextoChange}
          />
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
