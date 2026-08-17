import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { CHECKBOX_CLASS } from '../lib/buttons'
import { hasAnyZona, ZONAS } from '../lib/rbac'
import {
  BLOCO_D,
  BLOCOS,
  FEEDBACK,
  OPCOES_CHECKPOINT,
  PASSOS_NUMERADOS,
  TIPOS_ROTEIRO,
} from '../lib/roteiroGuiadoContent'
import './RoteiroGuiado.css'

const FONTS_HREF =
  'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap'

const DEBOUNCE_MS = 800

function useRoteiroFonts() {
  useEffect(() => {
    const id = 'roteiro-fonts'
    if (document.getElementById(id)) return undefined
    const link = document.createElement('link')
    link.id = id
    link.rel = 'stylesheet'
    link.href = FONTS_HREF
    document.head.appendChild(link)
    return undefined
  }, [])
}

function RichText({ text }) {
  const parts = []
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g
  let last = 0
  let m
  let key = 0
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    const token = m[1]
    if (token.startsWith('**')) {
      parts.push(<strong key={key++}>{token.slice(2, -2)}</strong>)
    } else {
      parts.push(<em key={key++}>{token.slice(1, -1)}</em>)
    }
    last = m.index + token.length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

function emptyResposta() {
  return { concluido: false, observacao: '' }
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR')
  } catch {
    return iso
  }
}

export default function RoteiroGuiado() {
  useRoteiroFonts()
  const { user } = useAuth()
  const isAdmin = hasAnyZona(user?.zonas || [], [ZONAS.administrativo])
  const [searchParams, setSearchParams] = useSearchParams()

  const [tipo, setTipo] = useState(() => searchParams.get('tipo') || 'homologacao')
  const [sessaoId, setSessaoId] = useState(() => searchParams.get('sessao') || '')
  const [sessoes, setSessoes] = useState([])
  const [respostas, setRespostas] = useState({})
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [saveState, setSaveState] = useState('idle')
  const [historico, setHistorico] = useState([])
  const [histErro, setHistErro] = useState('')

  const tipoRef = useRef(tipo)
  const timersRef = useRef({})
  const pendingRef = useRef(0)

  tipoRef.current = tipo

  const loadSessoes = useCallback(async () => {
    try {
      const res = await fetch('/api/homologacao/sessoes', { credentials: 'include' })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        setSessoes([])
        return
      }
      setSessoes(body.itens || [])
    } catch {
      setSessoes([])
    }
  }, [])

  const load = useCallback(async (tipoAlvo, sessaoAlvo) => {
    setLoading(true)
    setErro('')
    try {
      const qs = new URLSearchParams({ tipo: tipoAlvo })
      if (tipoAlvo === 'homologacao' && sessaoAlvo) qs.set('sessao_id', sessaoAlvo)
      const res = await fetch(`/api/roteiro-guiado?${qs}`, {
        credentials: 'include',
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(body.error || 'Não foi possível carregar o roteiro.')
      }
      setRespostas(body.respostas || {})
      setSaveState('idle')
    } catch (e) {
      setErro(e.message || 'Erro ao carregar.')
      setRespostas({})
    } finally {
      setLoading(false)
    }
  }, [])

  const loadHistorico = useCallback(async (tipoAlvo) => {
    if (!isAdmin) return
    setHistErro('')
    try {
      const res = await fetch(
        `/api/roteiro-guiado/historico?tipo=${encodeURIComponent(tipoAlvo)}`,
        { credentials: 'include' },
      )
      const body = await res.json().catch(() => ({}))
      if (res.status === 403) {
        setHistorico([])
        return
      }
      if (!res.ok) {
        throw new Error(body.error || 'Não foi possível carregar o histórico.')
      }
      setHistorico(body.itens || [])
    } catch (e) {
      setHistErro(e.message || 'Erro ao carregar histórico.')
      setHistorico([])
    }
  }, [isAdmin])

  useEffect(() => {
    Object.values(timersRef.current).forEach((t) => clearTimeout(t))
    timersRef.current = {}
    if (tipo === 'homologacao') loadSessoes()
    load(tipo, sessaoId)
    loadHistorico(tipo)
  }, [tipo, sessaoId, load, loadHistorico, loadSessoes])

  useEffect(() => {
    const next = new URLSearchParams(searchParams)
    if (tipo) next.set('tipo', tipo)
    if (tipo === 'homologacao' && sessaoId) next.set('sessao', sessaoId)
    else next.delete('sessao')
    setSearchParams(next, { replace: true })
  }, [tipo, sessaoId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const prev = document.title
    document.title = 'Roteiro Guiado · inove4us School'
    return () => {
      document.title = prev
      Object.values(timersRef.current).forEach((t) => clearTimeout(t))
    }
  }, [])

  const flushPasso = useCallback(async (passoId, snapshotTipo, payload) => {
    pendingRef.current += 1
    setSaveState('saving')
    try {
      const res = await fetch(`/api/roteiro-guiado/${encodeURIComponent(passoId)}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tipo: snapshotTipo,
          sessao_id: snapshotTipo === 'homologacao' ? sessaoId || undefined : undefined,
          concluido: Boolean(payload.concluido),
          observacao: payload.observacao || '',
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(body.error || 'Falha ao salvar.')
      }
    } catch (e) {
      pendingRef.current = Math.max(0, pendingRef.current - 1)
      setSaveState('error')
      setErro(e.message || 'Falha ao salvar.')
      return
    }
    pendingRef.current = Math.max(0, pendingRef.current - 1)
    if (tipoRef.current === snapshotTipo) {
      setSaveState(pendingRef.current === 0 ? 'saved' : 'saving')
    }
  }, [sessaoId])

  const scheduleSave = useCallback(
    (passoId, nextRespostas) => {
      const snapshotTipo = tipoRef.current
      const payload = nextRespostas[passoId] || emptyResposta()
      if (timersRef.current[passoId]) clearTimeout(timersRef.current[passoId])
      timersRef.current[passoId] = setTimeout(() => {
        delete timersRef.current[passoId]
        flushPasso(passoId, snapshotTipo, payload)
      }, DEBOUNCE_MS)
    },
    [flushPasso],
  )

  const patchLocal = (passoId, patch) => {
    if (tipo === 'homologacao' && !sessaoId) {
      setErro('Selecione a sessão de homologação antes de marcar passos.')
      return
    }
    setRespostas((prev) => {
      const atual = prev[passoId] || emptyResposta()
      const nextItem = { ...atual, ...patch }
      const next = { ...prev, [passoId]: nextItem }
      scheduleSave(passoId, next)
      return next
    })
  }

  const get = (passoId) => respostas[passoId] || emptyResposta()

  const hoje = new Date().toLocaleDateString('pt-BR')
  const concluidos = PASSOS_NUMERADOS.filter((id) => get(id).concluido).length
  const saveLabel =
    saveState === 'saving'
      ? 'salvando...'
      : saveState === 'saved'
        ? 'salvo'
        : saveState === 'error'
          ? 'não foi possível salvar'
          : ''

  const controleSessaoTo = sessaoId
    ? `/homologacao?sessao=${encodeURIComponent(sessaoId)}`
    : '/homologacao'

  return (
    <div className="roteiro-page">
      {tipo === 'homologacao' ? (
        <div className="roteiro-voltar">
          <Link to={controleSessaoTo} className="roteiro-voltar-link">
            ← Voltar ao controle da sessão
          </Link>
          <span className="roteiro-voltar-hint">
            Pausar, registrar interrupção ou impressões sem perder o que já marcou.
          </span>
        </div>
      ) : null}

      <span className="roteiro-badge">ROTEIRO GUIADO · VOCÊ NO COMANDO</span>
      <h1 className="roteiro-serif">Conheça o inove4us</h1>
      <p className="roteiro-sub">
        Um passeio guiado por Escola → Professor → Ponte — para você testar com as próprias
        mãos, no seu ritmo.
      </p>

      <div className="roteiro-tipo" role="group" aria-label="Tipo do roteiro">
        {TIPOS_ROTEIRO.map((opt) => (
          <button
            key={opt.id}
            type="button"
            aria-pressed={tipo === opt.id}
            onClick={() => setTipo(opt.id)}
          >
            {opt.label}
          </button>
        ))}
      </div>
      {tipo === 'homologacao' ? (
        <div className="roteiro-sessao-bar">
          <label className="roteiro-obs-label" htmlFor="sessao-homolog">
            Sessão de homologação
          </label>
          <div className="roteiro-sessao-row">
            <select
              id="sessao-homolog"
              value={sessaoId}
              onChange={(e) => setSessaoId(e.target.value)}
            >
              <option value="">Selecione…</option>
              {sessoes.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.codigo} · {s.status} · {(s.roteiro && s.roteiro.percentual) || 0}%
                </option>
              ))}
            </select>
            <Link to={controleSessaoTo} className="roteiro-voltar-link">
              Controle da sessão
            </Link>
          </div>
          {!sessaoId ? (
            <p className="roteiro-save erro" style={{ marginTop: '0.5rem' }}>
              Para gravar homologação, escolha (ou crie) uma sessão em Homologação.
            </p>
          ) : null}
        </div>
      ) : null}

      <p className={`roteiro-save ${saveState === 'saving' ? 'saving' : ''} ${saveState === 'saved' ? 'saved' : ''} ${saveState === 'error' ? 'erro' : ''}`}>
        {saveLabel}
      </p>

      <table className="roteiro-info">
        <tbody>
          <tr>
            <th>Data</th>
            <td>{hoje}</td>
          </tr>
          <tr>
            <th>Seu nome</th>
            <td>{user?.nome || '—'}</td>
          </tr>
          <tr>
            <th>Link da Escola</th>
            <td>
              <a href="https://school.inove4us.com.br" target="_blank" rel="noreferrer">
                https://school.inove4us.com.br
              </a>
            </td>
          </tr>
          <tr>
            <th>Link do Professor</th>
            <td>
              <a href="https://inove4us.com.br" target="_blank" rel="noreferrer">
                https://inove4us.com.br
              </a>
            </td>
          </tr>
          <tr>
            <th>Login</th>
            <td>{user?.email || 'Sessão autenticada nesta aba'}</td>
          </tr>
        </tbody>
      </table>

      <p>
        Este roteiro leva cerca de <strong>60 a 90 minutos</strong>. Você pode fazer
        sozinho(a), representando as duas pontas (escola e professor), ou dividir com um(a)
        colega. Vá marcando as caixas conforme for testando. Se travar em algum ponto, não se
        preocupe — anote e continue; no final há um espaço só para isso.
      </p>
      <p className="roteiro-sub">
        Tudo que você vai ver aqui é um ambiente de testes, separado da operação real da
        escola — pode explorar à vontade.
      </p>
      <p className="roteiro-save">
        {concluidos} de {PASSOS_NUMERADOS.length} passos numerados concluídos
      </p>

      {erro ? <p className="roteiro-save erro">{erro}</p> : null}
      {loading ? <p className="roteiro-sub">Carregando respostas salvas…</p> : null}

      {BLOCOS.map((bloco) => (
        <section key={bloco.id}>
          <div className="roteiro-bloco-head" style={{ background: bloco.cor }}>
            {bloco.titulo}
          </div>
          <p>{bloco.intro}</p>
          {bloco.passos.map((passo) => {
            const st = get(passo.id)
            return (
              <div className="roteiro-passo" key={passo.id}>
                <h3>{passo.titulo}</h3>
                <ul className="roteiro-itens">
                  {passo.itens.map((item) => (
                    <li key={item}>
                      <RichText text={item} />
                    </li>
                  ))}
                </ul>
                <label className="roteiro-check">
                  <input
                    type="checkbox"
                    className={CHECKBOX_CLASS}
                    checked={Boolean(st.concluido)}
                    onChange={(e) => patchLocal(passo.id, { concluido: e.target.checked })}
                  />
                  Marquei este passo
                </label>
                <label className="roteiro-obs-label" htmlFor={`obs-${passo.id}`}>
                  Observações
                </label>
                <textarea
                  id={`obs-${passo.id}`}
                  className="roteiro-obs"
                  value={st.observacao || ''}
                  onChange={(e) => patchLocal(passo.id, { observacao: e.target.value })}
                  placeholder="Anote o que passou, travou ou ficou em dúvida."
                />
              </div>
            )
          })}
          {bloco.checkpoint ? (
            <div className="roteiro-checkpt">
              <p>Ponto de checagem — {bloco.checkpoint.pergunta}</p>
              <div className="roteiro-radios">
                {OPCOES_CHECKPOINT.map((opt) => (
                  <label key={opt}>
                    <input
                      type="radio"
                      className={CHECKBOX_CLASS}
                      name={bloco.checkpoint.id}
                      checked={(get(bloco.checkpoint.id).observacao || '') === opt}
                      onChange={() =>
                        patchLocal(bloco.checkpoint.id, { concluido: true, observacao: opt })
                      }
                    />
                    {opt}
                  </label>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ))}

      <section>
        <div className="roteiro-bloco-head" style={{ background: BLOCO_D.cor }}>
          {BLOCO_D.titulo}
        </div>
        <ul className="roteiro-d">
          {BLOCO_D.itens.map((item) => (
            <li key={item}>
              <RichText text={item} />
            </li>
          ))}
        </ul>
      </section>

      <section>
        <div className="roteiro-bloco-head" style={{ background: '#1e2a4a' }}>
          Sua opinião (5 minutos, não pule)
        </div>
        <p>{FEEDBACK.intro}</p>
        <table className="roteiro-fb-table">
          <thead>
            <tr>
              <th>Pergunta</th>
              <th>Sua resposta</th>
            </tr>
          </thead>
          <tbody>
            {FEEDBACK.perguntas.map((q) => {
              const st = get(q.id)
              return (
                <tr key={q.id}>
                  <td>{q.pergunta}</td>
                  <td>
                    {q.tipo === 'radio' ? (
                      <div className="roteiro-radios">
                        {(q.opcoes || []).map((opt) => (
                          <label key={opt}>
                            <input
                              type="radio"
                              className={CHECKBOX_CLASS}
                              name={q.id}
                              checked={(st.observacao || '') === opt}
                              onChange={() =>
                                patchLocal(q.id, { concluido: true, observacao: opt })
                              }
                            />
                            {opt}
                          </label>
                        ))}
                      </div>
                    ) : (
                      <textarea
                        value={st.observacao || ''}
                        onChange={(e) =>
                          patchLocal(q.id, {
                            observacao: e.target.value,
                            concluido: Boolean(e.target.value.trim()),
                          })
                        }
                      />
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <h3>{FEEDBACK.notas.titulo}</h3>
        <textarea
          className="roteiro-obs"
          style={{ minHeight: '8rem' }}
          value={get(FEEDBACK.notas.id).observacao || ''}
          onChange={(e) =>
            patchLocal(FEEDBACK.notas.id, {
              observacao: e.target.value,
              concluido: Boolean(e.target.value.trim()),
            })
          }
        />
      </section>

      <p className="roteiro-sub" style={{ marginTop: '1.5rem' }}>
        Dúvidas durante o percurso? Anote na caixa acima — o técnico da sessão também pode
        ajudar.
      </p>
      {tipo === 'homologacao' ? (
        <div className="roteiro-voltar roteiro-voltar-fim">
          <Link to={controleSessaoTo} className="roteiro-voltar-link">
            ← Voltar ao controle da sessão
          </Link>
          <span className="roteiro-voltar-hint">
            Precisa parar agora? Registre a interrupção e retome depois sem criar outra sessão.
          </span>
        </div>
      ) : null}
      <p className="roteiro-save">inove4us — Roteiro Guiado</p>

      {isAdmin ? (
        <section className="roteiro-hist">
          <h2>Acompanhamento nesta instituição</h2>
          {histErro ? <p className="roteiro-save erro">{histErro}</p> : null}
          {historico.length === 0 && !histErro ? (
            <p className="roteiro-sub">Ainda não há respostas gravadas neste tipo.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Gestor</th>
                  <th>Instituição</th>
                  <th>Tipo</th>
                  <th>Sessão / progresso</th>
                  <th>Atualizado</th>
                </tr>
              </thead>
              <tbody>
                {historico.map((row) => (
                  <tr key={`${row.gestor_id}-${row.tipo}`}>
                    <td>
                      {row.gestor}
                      <br />
                      <span className="roteiro-save">{row.email}</span>
                    </td>
                    <td>{row.instituicao}</td>
                    <td>{row.tipo === 'treinamento' ? 'Treinamento' : 'Homologação'}</td>
                    <td>
                      {row.sessao_codigo || '—'}
                      <br />
                      {row.percentual}% ({row.passos_concluidos}/{row.passos_total})
                    </td>
                    <td>{formatDate(row.atualizado_em)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ) : null}
    </div>
  )
}
