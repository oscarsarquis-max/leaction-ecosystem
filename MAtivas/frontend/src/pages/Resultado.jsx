import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Target,
  FileText,
  Loader2,
  Layers,
  GitBranch,
  Sparkles,
  CheckCircle2,
  MessageSquare,
} from 'lucide-react'

import TopBar from '../components/TopBar.jsx'
import { diagnosticarMetodologia, refinarDiagnostico } from '../services/api.js'
import { FORMATOS_AULA, NIVEIS_ENSINO } from '../data/niveisEnsino.js'
import { useUiContent } from '../contexts/UiContentContext.jsx'

/**
 * Monta o payload de lock-in (metodologia + justificativa) conforme a via
 * escolhida pelo professor na árvore de decisão ou no diálogo de refino.
 */
function resolverViaSelecionada(diagnostico, viaId, sugestoesRefino) {
  if (!viaId) return null

  if (viaId.startsWith('ref:') && sugestoesRefino?.length) {
    const idx = Number(viaId.split(':')[1])
    const s = sugestoesRefino[idx]
    if (!s) return null
    const isFusao = s.tipo === 'fusao'
    return {
      via: isFusao ? 'fusao_estrategica' : 'sugestao_refinada',
      metodologia: s.nome,
      justificativa: s.justificativa,
      categoria: s.categoria,
      metodologias_fusao: isFusao ? s.metodologias || null : null,
    }
  }

  if (!diagnostico) return null

  if (viaId === 'match') {
    const mp = diagnostico.match_perfeito || {}
    return {
      via: 'match_perfeito',
      metodologia: mp.nome || diagnostico.metodologia,
      justificativa: mp.justificativa || diagnostico.justificativa,
      categoria: mp.categoria || diagnostico.grupo,
    }
  }

  if (viaId.startsWith('alt:')) {
    const idx = Number(viaId.split(':')[1])
    const alt = (diagnostico.alternativas_mesmo_ramo || [])[idx]
    if (!alt) return null
    return {
      via: 'alternativa_mesmo_ramo',
      metodologia: alt.nome,
      justificativa: alt.justificativa,
      categoria: alt.categoria,
    }
  }

  if (viaId === 'fusao') {
    const fusao = diagnostico.fusao_estrategica || {}
    const mets = fusao.metodologias || []
    const nomeFusao = fusao.nome || mets.join(' + ')
    const sinergia = fusao.sinergia || ''
    const justificativa = [
      sinergia,
      mets.length >= 2 ? `Fusão estratégica entre ${mets[0]} e ${mets[1]}.` : null,
    ]
      .filter(Boolean)
      .join(' ')

    return {
      via: 'fusao_estrategica',
      metodologia: nomeFusao,
      justificativa,
      categoria: (fusao.categorias || []).join(' + ') || null,
      metodologias_fusao: mets,
    }
  }

  return null
}

function OptionCard({ selected, onSelect, badge, title, subtitle, body, icon: Icon, accent }) {
  return (
    <button
      type="button"
      className={`diag-option ${selected ? 'diag-option--selected' : ''} ${accent ? `diag-option--${accent}` : ''}`}
      onClick={onSelect}
      aria-pressed={selected}
    >
      <div className="diag-option__head">
        <span className="diag-option__badge">{badge}</span>
        {selected && <CheckCircle2 size={18} className="diag-option__check" />}
      </div>
      <p className="diag-option__title">
        {Icon ? <Icon size={18} style={{ verticalAlign: 'middle', marginRight: 6 }} /> : null}
        {title}
      </p>
      {subtitle ? <p className="diag-option__subtitle">{subtitle}</p> : null}
      {body ? <p className="muted diag-option__body">{body}</p> : null}
    </button>
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
  const [viaSelecionada, setViaSelecionada] = useState(null)

  const [feedback, setFeedback] = useState('')
  const [carregandoRefino, setCarregandoRefino] = useState(false)
  const [erroRefino, setErroRefino] = useState(null)
  const [respostaDialogo, setRespostaDialogo] = useState(null)
  const [sugestoesRefino, setSugestoesRefino] = useState(null)

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
    setViaSelecionada(null)
    setSugestoesRefino(null)
    setRespostaDialogo(null)
    setFeedback('')
    setErroRefino(null)

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
        if (res?.match_perfeito?.nome) {
          setViaSelecionada('match')
        }
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

  const escolha = resolverViaSelecionada(diagnostico, viaSelecionada, sugestoesRefino)
  const contextoPreenchido =
    (!precisaNivel || Boolean(nivel)) &&
    (!precisaFormato || Boolean(formato)) &&
    (!precisaParticipantes || Boolean(String(participantes).trim()))
  const podeGerar = Boolean(escolha?.metodologia) && contextoPreenchido

  const match = diagnostico?.match_perfeito
  const alternativas = diagnostico?.alternativas_mesmo_ramo || []
  const fusao = diagnostico?.fusao_estrategica

  // Abordagem em discussão para o diálogo (prioriza a seleção atual)
  const abordagemDialogo = useMemo(() => {
    if (escolha?.metodologia) return escolha
    if (match?.nome) {
      return {
        metodologia: match.nome,
        justificativa: match.justificativa,
        categoria: match.categoria,
      }
    }
    return null
  }, [escolha, match])

  let badgeNum = 0

  const enviarFeedback = async () => {
    if (!abordagemDialogo?.metodologia || feedback.trim().length < 8) return
    setCarregandoRefino(true)
    setErroRefino(null)
    try {
      const res = await refinarDiagnostico({
        desafio,
        opcoes,
        sintese,
        nivel: nivel || undefined,
        formato: formato || undefined,
        abordagem_atual: abordagemDialogo.metodologia,
        categoria_atual: abordagemDialogo.categoria,
        justificativa_atual: abordagemDialogo.justificativa,
        feedback: feedback.trim(),
      })
      setRespostaDialogo(res.resposta_dialogo || null)
      setSugestoesRefino(res.sugestoes || [])
      if (res.sugestoes?.length) {
        setViaSelecionada('ref:0')
      }
    } catch (err) {
      setErroRefino(
        err?.response?.data?.erro || 'Não foi possível gerar novas sugestões. Tente novamente.',
      )
    } finally {
      setCarregandoRefino(false)
    }
  }

  const irParaCadastro = () => {
    if (!escolha) return
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
        metodologias_fusao: escolha.metodologias_fusao || null,
        categoria: escolha.categoria,
      },
    })
  }

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

      {!precisaContexto && (
        <div className="card card-alt">
          <p className="muted">
            Identificamos no seu relato o nível de ensino, a modalidade e a quantidade de
            participantes. Escolha abaixo a via metodológica — ou dialogue se algo não se adequa.
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
                'Selecione a via que deseja seguir. Se algum aspecto não se adequar à sua realidade, use o diálogo abaixo para gerar novas sugestões.',
              )}
            </p>

            <OptionCard
              selected={viaSelecionada === 'match'}
              onSelect={() => setViaSelecionada('match')}
              badge="Match perfeito"
              accent="match"
              icon={Layers}
              title={match.nome}
              subtitle={match.categoria}
              body={match.justificativa}
            />

            {alternativas.length > 0 && (
              <div className="diag-section">
                <h2 className="diag-section__title">
                  <GitBranch size={16} /> Outras abordagens viáveis
                </h2>
                <p className="muted diag-section__hint">
                  Colaterais do mesmo ramo ({match.categoria})
                </p>
                <div className="diag-options-grid">
                  {alternativas.map((alt, idx) => (
                    <OptionCard
                      key={`${alt.nome}-${idx}`}
                      selected={viaSelecionada === `alt:${idx}`}
                      onSelect={() => setViaSelecionada(`alt:${idx}`)}
                      badge={`Alternativa ${idx + 1}`}
                      accent="alt"
                      title={alt.nome}
                      subtitle={alt.categoria}
                      body={alt.justificativa}
                    />
                  ))}
                </div>
              </div>
            )}

            {fusao?.nome && (
              <div className="diag-section">
                <h2 className="diag-section__title">
                  <Sparkles size={16} /> Fusão estratégica sugerida
                </h2>
                <OptionCard
                  selected={viaSelecionada === 'fusao'}
                  onSelect={() => setViaSelecionada('fusao')}
                  badge="Fusão"
                  accent="fusao"
                  icon={Sparkles}
                  title={fusao.nome}
                  subtitle={
                    (fusao.metodologias || []).length
                      ? (fusao.metodologias || []).join(' + ')
                      : null
                  }
                  body={fusao.sinergia}
                />
              </div>
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

      {match?.nome && abordagemDialogo?.metodologia && (
        <div className="card diag-dialogo">
          <span className="card-title">
            <MessageSquare size={18} /> Dialogar com a IA
          </span>
          <p className="muted">
            Abordagem em discussão: <strong>{abordagemDialogo.metodologia}</strong>
            {abordagemDialogo.categoria ? ` · ${abordagemDialogo.categoria}` : ''}
          </p>
          <p className="muted" style={{ marginBottom: 10 }}>
            Conte qual aspecto dessa abordagem <strong>não se adequa</strong> à realidade da sua
            turma ou do seu contexto. Geraremos novas sugestões, cada uma com justificativa.
          </p>
          <div className="field">
            <label htmlFor="feedback-dialogo">O que não se adequa?</label>
            <textarea
              id="feedback-dialogo"
              className="textarea diag-dialogo__textarea"
              rows={4}
              maxLength={1200}
              placeholder="Ex.: não temos tempo para ciclos longos; a turma é muito grande para dinâmicas imersivas; falta laboratório..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              disabled={carregandoRefino}
            />
          </div>
          {erroRefino && <p className="diag-dialogo__erro">{erroRefino}</p>}
          <button
            type="button"
            className="btn btn-secondary"
            disabled={carregandoRefino || feedback.trim().length < 8}
            onClick={enviarFeedback}
          >
            {carregandoRefino ? (
              <>
                <Loader2 size={16} className="spin" /> Gerando novas sugestões...
              </>
            ) : (
              <>
                <MessageSquare size={16} /> Gerar novas sugestões
              </>
            )}
          </button>
        </div>
      )}

      {(respostaDialogo || (sugestoesRefino && sugestoesRefino.length > 0)) && (
        <div className="card methodology diag-refino">
          <span className="section-label">Sugestões ajustadas ao seu feedback</span>
          {respostaDialogo && <p className="diag-refino__resposta">{respostaDialogo}</p>}
          <p className="muted" style={{ marginBottom: 12 }}>
            Selecione uma das opções abaixo. Cada sugestão traz a justificativa do ajuste.
          </p>
          <div className="diag-options-grid">
            {(sugestoesRefino || []).map((s, idx) => (
              <OptionCard
                key={`ref-${s.nome}-${idx}`}
                selected={viaSelecionada === `ref:${idx}`}
                onSelect={() => setViaSelecionada(`ref:${idx}`)}
                badge={s.tipo === 'fusao' ? 'Fusão ajustada' : `Sugestão ${idx + 1}`}
                accent={s.tipo === 'fusao' ? 'fusao' : 'refino'}
                icon={s.tipo === 'fusao' ? Sparkles : Layers}
                title={s.nome}
                subtitle={
                  s.tipo === 'fusao' && s.metodologias?.length
                    ? s.metodologias.join(' + ')
                    : s.categoria
                }
                body={s.justificativa}
              />
            ))}
          </div>
        </div>
      )}

      <button
        type="button"
        className="btn btn-primary"
        disabled={!podeGerar || carregandoDiag || carregandoRefino}
        onClick={irParaCadastro}
      >
        <FileText size={18} />
        {podeGerar
          ? 'Gerar Roteiro de Aulas com a via escolhida'
          : !contextoPreenchido
            ? 'Preencha os campos obrigatórios (*) para continuar'
            : 'Selecione uma via para continuar'}
      </button>

      <button type="button" className="link-subtle" onClick={() => navigate('/')}>
        Começar de novo
      </button>
    </div>
  )
}

export default Resultado
