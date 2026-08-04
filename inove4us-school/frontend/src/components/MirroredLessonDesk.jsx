/**
 * MirroredLessonDesk — Mesa do professor espelhada no School (somente leitura).
 *
 * =============================================================================
 * CONTRATO TÉCNICO (S2S School ↔ B2C)
 * =============================================================================
 *
 * Fonte de dados:
 *   Tabela PostgreSQL `school_planos_aula_espelhados` (DB `inove4us_school`).
 *   Campo principal: `mesa_payload_json` (JSONB) — snapshot completo da Mesa
 *   executada no B2C (vetor Dia a Dia ou Desafio), entregue via webhook
 *   `LESSON_RECORD_SYNC` em POST /api/webhooks/b2c.
 *
 * Objetivo de produto:
 *   O coordenador / pedagogo visualiza TODOS os elementos da aula (cards,
 *   status, adaptações do professor) centralizados no School, SEM redirecionar
 *   o usuário para o app B2C do professor. Isolamento total de banco e de UI.
 *
 * Modo de renderização:
 *   Read-only. Este componente NÃO persiste edições, NÃO chama APIs de escrita
 *   do B2C e NÃO deve expor controles de “salvar / gerar / executar”.
 *   Interações visuais (expandir card, filtrar) são apenas de navegação local.
 *
 * Shape esperado de `mesa` (espelho do payload B2C — evolutivo):
 *   {
 *     id | plano_id?: string,
 *     titulo?: string,
 *     tipo_aula?: 'dia_a_dia' | 'desafio',
 *     status?: string,
 *     metodologia_nome?: string,
 *     cards?: Array<{
 *       id?: string,
 *       titulo?: string,
 *       status?: string,
 *       objetivo?: string,
 *       mecanica_passo_a_passo?: string,
 *       duracao_minutos?: number
 *     }>,
 *     has_teacher_adaptations?: boolean,
 *     adaptations?: unknown,
 *     ...demais chaves preservadas no JSONB
 *   }
 *
 * Props:
 *   - mesa: objeto JSON (ou null) vindo de `school_planos_aula_espelhados.mesa_payload_json`
 *   - meta: metadados do espelho (status School, semana, professor, etc.) — opcional
 *   - className: classes utilitárias opcionais
 *
 * Próximos incrementos (fora deste esqueleto):
 *   - Fetch GET /api/planos-espelhados/:id
 *   - Paridade visual com a Mesa B2C (tokens / layout)
 *   - Destaque de cards com adaptação (link com school_curadoria_metodologias)
 * =============================================================================
 */

const TIPO_LABEL = {
  dia_a_dia: 'Dia a Dia',
  desafio: 'Desafio',
}

const STATUS_LABEL = {
  pendente: 'Pendente',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
  em_andamento: 'Em andamento',
  concluido: 'Concluído',
  done: 'Concluído',
}

function asCards(mesa) {
  if (!mesa || typeof mesa !== 'object') return []
  const raw =
    mesa.cards ||
    mesa.etapas ||
    mesa.passos ||
    mesa.kanban_cards ||
    mesa.steps ||
    []
  return Array.isArray(raw) ? raw : []
}

function labelStatus(raw) {
  const key = String(raw || '').trim().toLowerCase()
  return STATUS_LABEL[key] || raw || '—'
}

function labelTipo(raw) {
  const key = String(raw || '').trim().toLowerCase()
  return TIPO_LABEL[key] || raw || 'Aula'
}

/**
 * @param {{
 *   mesa?: Record<string, unknown> | null,
 *   meta?: {
 *     status?: string,
 *     semana_referencia?: string,
 *     professor_nome?: string,
 *     metodologia_nome?: string,
 *     tipo_aula?: string,
 *     origem_plano_b2c_id?: string,
 *   },
 *   className?: string,
 * }} props
 */
export default function MirroredLessonDesk({ mesa = null, meta = {}, className = '' }) {
  const data = mesa && typeof mesa === 'object' ? mesa : null
  const cards = asCards(data)
  const titulo =
    (data && (data.titulo || data.title || data.nome)) ||
    meta.metodologia_nome ||
    'Mesa espelhada'
  const tipo = labelTipo((data && data.tipo_aula) || meta.tipo_aula)
  const status = labelStatus((data && data.status) || meta.status)
  const metodologia =
    (data && (data.metodologia_nome || data.metodologia)) ||
    meta.metodologia_nome ||
    '—'
  const hasAdapt =
    Boolean(data && data.has_teacher_adaptations) ||
    Boolean(data && (data.adaptations || data.teacher_adaptations))

  return (
    <section
      className={`mirrored-lesson-desk ${className}`.trim()}
      aria-label="Mesa do professor (somente leitura)"
      data-readonly="true"
      data-source="school_planos_aula_espelhados.mesa_payload_json"
    >
      {/* Banner de isolamento: deixa explícito que não há deep-link para o B2C */}
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Mesa espelhada · somente leitura
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">{titulo}</h2>
          <p className="mt-1 text-sm text-slate-600">
            Visualização centralizada no School — sem redirecionamento ao app do professor.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">{tipo}</span>
          <span className="rounded bg-amber-50 px-2 py-1 text-amber-800">{status}</span>
          {hasAdapt ? (
            <span className="rounded bg-violet-50 px-2 py-1 text-violet-800">
              Adaptação do professor
            </span>
          ) : null}
        </div>
      </header>

      <dl className="mb-4 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
        <div>
          <dt className="text-xs uppercase text-slate-500">Metodologia</dt>
          <dd>{metodologia}</dd>
        </div>
        {meta.semana_referencia ? (
          <div>
            <dt className="text-xs uppercase text-slate-500">Semana</dt>
            <dd>{meta.semana_referencia}</dd>
          </div>
        ) : null}
        {meta.professor_nome ? (
          <div>
            <dt className="text-xs uppercase text-slate-500">Professor</dt>
            <dd>{meta.professor_nome}</dd>
          </div>
        ) : null}
        {meta.origem_plano_b2c_id ? (
          <div>
            <dt className="text-xs uppercase text-slate-500">Origem B2C</dt>
            <dd className="font-mono text-xs">{meta.origem_plano_b2c_id}</dd>
          </div>
        ) : null}
      </dl>

      {!data ? (
        <p className="rounded border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
          Nenhum JSON de mesa disponível em <code>mesa_payload_json</code>.
          Aguardando evento <code>LESSON_RECORD_SYNC</code>.
        </p>
      ) : cards.length === 0 ? (
        <p className="rounded border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
          Payload recebido, mas sem lista de cards/etapas reconhecível.
          O JSON bruto permanece disponível para inspeção no próximo incremento.
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((card, idx) => {
            const c = card && typeof card === 'object' ? card : { titulo: String(card) }
            const cardTitle =
              c.titulo || c.titulo_do_card || c.title || c.nome || `Card ${idx + 1}`
            const cardStatus = labelStatus(c.status)
            const body =
              c.mecanica_passo_a_passo ||
              c.como_executar_detalhado ||
              c.objetivo ||
              c.texto ||
              ''
            return (
              <li
                key={c.id || `${cardTitle}-${idx}`}
                className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">{cardTitle}</h3>
                  <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                    {cardStatus}
                  </span>
                </div>
                {body ? (
                  <p className="text-xs leading-relaxed text-slate-600 line-clamp-6">{body}</p>
                ) : (
                  <p className="text-xs italic text-slate-400">Sem detalhe neste card.</p>
                )}
                {c.duracao_minutos != null ? (
                  <p className="mt-2 text-[11px] text-slate-500">{c.duracao_minutos} min</p>
                ) : null}
              </li>
            )
          })}
        </ul>
      )}

      {/*
        IMPORTANTE: não adicionar botões de edição / sync / “abrir no B2C”.
        Qualquer curadoria de adaptação deve ir para school_curadoria_metodologias
        via fluxo pedagógico do School — não via este desk.
      */}
    </section>
  )
}
