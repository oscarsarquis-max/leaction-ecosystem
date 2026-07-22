import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Target, FileText, Loader2, Layers } from 'lucide-react'

import TopBar from '../components/TopBar.jsx'
import { diagnosticarMetodologia } from '../services/api.js'
import { FORMATOS_AULA, NIVEIS_ENSINO } from '../data/niveisEnsino.js'
import { useUiContent } from '../contexts/UiContentContext.jsx'

/** Lock-in sempre no primeiro match da árvore (sem alternativas / fusão / escolha). */
function resolverMatch(diagnostico) {
  if (!diagnostico) return null
  const mp = diagnostico.match_perfeito || {}
  const metodologia = mp.nome || diagnostico.metodologia
  if (!metodologia) return null
  return {
    via: 'match_perfeito',
    metodologia,
    justificativa: mp.justificativa || diagnostico.justificativa,
    categoria: mp.categoria || diagnostico.grupo,
  }
}

function MatchCard({ badge, title, subtitle, body }) {
  return (
    <div className="diag-option diag-option--selected diag-option--match" aria-live="polite">
      <div className="diag-option__head">
        <span className="diag-option__badge">{badge}</span>
      </div>
      <p className="diag-option__title">
        <Layers size={18} style={{ verticalAlign: 'middle', marginRight: 6 }} />
        {title}
      </p>
      {subtitle ? <p className="diag-option__subtitle">{subtitle}</p> : null}
      {body ? <p className="muted diag-option__body">{body}</p> : null}
    </div>
  )
}

function Resultado() {
  const navigate = useNavigate()
  const location = useLocation()
  const { texto } = useUiContent()
  const { desafio, opcoes = [] } = location.state || {}

  const [nivel, setNivel] = useState('')
  const [formato, setFormato] = useState('')
  const [participantes, setParticipantes] = useState('')
  const [contextoAuto, setContextoAuto] = useState({})

  const [diagnostico, setDiagnostico] = useState(null)
  const [carregandoDiag, setCarregandoDiag] = useState(false)
  const [erroDiag, setErroDiag] = useState(null)
  const avancouRef = useRef(false)

  const sintese = useMemo(() => {
    if (desafio && desafio.length > 0) return desafio
    if (opcoes.length > 0) return opcoes.join(', ')
    return 'engajamento e participação dos alunos nas atividades em grupo'
  }, [desafio, opcoes])

  useEffect(() => {
    const temEntrada = (desafio && desafio.length > 0) || opcoes.length > 0
    if (!temEntrada) return

    let ativo = true
    setCarregandoDiag(true)
    setErroDiag(null)
    avancouRef.current = false

    diagnosticarMetodologia({
      desafio,
      opcoes,
      sintese,
      nivel: nivel || undefined,
      formato: formato || undefined,
    })
      .then((res) => {
        if (!ativo) return
        setDiagnostico(res)
        const ctx = res?.contexto || {}
        setContextoAuto(ctx)
        if (ctx.nivel) setNivel(ctx.nivel)
        if (ctx.formato) setFormato(ctx.formato)
        if (ctx.participantes) setParticipantes(String(ctx.participantes))
      })
      .catch((err) => {
        if (!ativo) return
        setDiagnostico(null)
        setErroDiag(err?.response?.data?.erro || 'Não foi possível gerar o diagnóstico.')
      })
      .finally(() => {
        if (ativo) setCarregandoDiag(false)
      })

    return () => {
      ativo = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desafio, opcoes, sintese])

  const precisaNivel = !contextoAuto.nivel
  const precisaFormato = !contextoAuto.formato
  const precisaParticipantes = !contextoAuto.participantes
  const precisaContexto = precisaNivel || precisaFormato || precisaParticipantes

  const escolha = resolverMatch(diagnostico)
  const contextoPreenchido =
    (!precisaNivel || Boolean(nivel)) &&
    (!precisaFormato || Boolean(formato)) &&
    (!precisaParticipantes || Boolean(String(participantes).trim()))
  const podeGerar = Boolean(escolha?.metodologia) && contextoPreenchido

  const match = diagnostico?.match_perfeito
  let badgeNum = 0

  const irParaCadastro = () => {
    if (!escolha || avancouRef.current) return
    avancouRef.current = true
    navigate('/cadastro', {
      state: {
        desafio,
        opcoes,
        nivel,
        formato,
        participantes,
        sintese,
        metodologia: escolha.metodologia,
        justificativa: escolha.justificativa,
        via_escolhida: escolha.via,
        metodologias_fusao: null,
        categoria: escolha.categoria,
      },
    })
  }

  // Só avança sozinho quando o contexto já veio completo do diagnóstico
  // (sem formulário). Se o professor preencheu campos, espera o clique no botão.
  useEffect(() => {
    if (precisaContexto || !podeGerar || carregandoDiag) return
    irParaCadastro()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [precisaContexto, podeGerar, carregandoDiag, escolha?.metodologia])

  return (
    <div className="page">
      <TopBar showBack backTo="/" />

      <header>
        <span className="section-label">Resultado personalizado</span>
        <h1 className="page-title">Entendemos seu desafio</h1>
      </header>

      <div className="card card-soft">
        <span className="card-title">
          <Target size={18} /> Síntese do desafio
        </span>
        <p>
          Registramos que seu relato está relacionado a <strong>{sintese}</strong>.
        </p>
      </div>

      {precisaContexto && (
        <div className="card">
          <span className="card-title">Para personalizar seu roteiro</span>
          <p className="muted">
            {Object.keys(contextoAuto).some((k) => contextoAuto[k])
              ? 'Complete apenas as informações que ainda não identificamos no seu relato:'
              : 'Responda às perguntas complementares para deixar a aula alinhada à sua turma:'}{' '}
            <span className="req-hint">(* obrigatório)</span>
          </p>

          {precisaNivel && (
            <div className="numbered">
              <div className="num-badge">{++badgeNum}</div>
              <div className="field">
                <label htmlFor="nivel">
                  Nível de ensino <span className="req" aria-hidden="true">*</span>
                </label>
                <select
                  id="nivel"
                  className="select"
                  value={nivel}
                  required
                  aria-required="true"
                  onChange={(e) => setNivel(e.target.value)}
                >
                  <option value="">Selecione</option>
                  {NIVEIS_ENSINO.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {precisaFormato && (
            <div className="numbered">
              <div className="num-badge">{++badgeNum}</div>
              <div className="field">
                <label htmlFor="formato">
                  Formato da aula <span className="req" aria-hidden="true">*</span>
                </label>
                <select
                  id="formato"
                  className="select"
                  value={formato}
                  required
                  aria-required="true"
                  onChange={(e) => setFormato(e.target.value)}
                >
                  <option value="">Selecione</option>
                  {FORMATOS_AULA.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {precisaParticipantes && (
            <div className="numbered">
              <div className="num-badge">{++badgeNum}</div>
              <div className="field">
                <label htmlFor="participantes">
                  Quantidade de participantes <span className="req" aria-hidden="true">*</span>
                </label>
                <input
                  id="participantes"
                  className="input"
                  type="number"
                  min="1"
                  required
                  aria-required="true"
                  placeholder="Ex: 30"
                  value={participantes}
                  onChange={(e) => setParticipantes(e.target.value)}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {!precisaContexto && match?.nome && !carregandoDiag && (
        <div className="card card-alt">
          <p className="muted">
            Identificamos a metodologia mais adequada ao seu relato. Em seguida, geramos o roteiro
            com ela.
          </p>
        </div>
      )}

      <div className="card methodology">
        <span className="section-label">Árvore de decisão · Biblioteca Inov-ativas</span>

        {carregandoDiag ? (
          <p className="muted methodology-loading">
            <Loader2 size={16} className="spin" /> Navegando na árvore de metodologias...
          </p>
        ) : erroDiag ? (
          <p className="muted">{erroDiag}</p>
        ) : match?.nome ? (
          <>
            <p className="muted" style={{ marginBottom: 12 }}>
              {texto(
                'resultado.arvore_intro',
                'Metodologia recomendada para o seu desafio. Seguiremos com ela para gerar o roteiro.',
              )}
            </p>

            <MatchCard
              badge="Metodologia recomendada"
              title={match.nome}
              subtitle={match.categoria}
              body={match.justificativa}
            />

            {podeGerar && !precisaContexto && (
              <p className="muted methodology-loading" style={{ marginTop: 14 }}>
                <Loader2 size={16} className="spin" /> Preparando a geração do roteiro...
              </p>
            )}
          </>
        ) : (
          <p className="muted">
            {texto(
              'resultado.previa_fallback',
              'Ao gerar seu roteiro, identificaremos o grupo e a metodologia inov-ativa mais adequados ao seu desafio.',
            )}
          </p>
        )}
      </div>

      {precisaContexto && escolha?.metodologia && (
        <button
          type="button"
          className="btn btn-primary"
          disabled={!podeGerar || carregandoDiag}
          onClick={irParaCadastro}
        >
          <FileText size={18} />
          {podeGerar
            ? 'Continuar para o roteiro'
            : 'Preencha os campos obrigatórios (*) para continuar'}
        </button>
      )}

      <button type="button" className="link-subtle" onClick={() => navigate('/')}>
        Começar de novo
      </button>
    </div>
  )
}

export default Resultado
