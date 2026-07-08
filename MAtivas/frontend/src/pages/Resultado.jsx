import { useEffect, useMemo, useState } from 'react'

import { useLocation, useNavigate } from 'react-router-dom'

import { Target, FileText, Loader2, Layers } from 'lucide-react'

import TopBar from '../components/TopBar.jsx'

import { diagnosticarMetodologia } from '../services/api.js'

import { FORMATOS_AULA, NIVEIS_ENSINO } from '../data/niveisEnsino.js'
import { useUiContent } from '../contexts/UiContentContext.jsx'



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

    diagnosticarMetodologia({ desafio, opcoes, sintese })

      .then((res) => {

        if (!ativo) return

        setDiagnostico(res)

        const ctx = res?.contexto || {}

        setContextoAuto(ctx)

        if (ctx.nivel) setNivel(ctx.nivel)

        if (ctx.formato) setFormato(ctx.formato)

        if (ctx.participantes) setParticipantes(String(ctx.participantes))

      })

      .catch(() => {

        if (ativo) setDiagnostico(null)

      })

      .finally(() => {

        if (ativo) setCarregandoDiag(false)

      })

    return () => {

      ativo = false

    }

  }, [desafio, opcoes, sintese])



  const precisaNivel = !contextoAuto.nivel

  const precisaFormato = !contextoAuto.formato

  const precisaParticipantes = !contextoAuto.participantes

  const precisaContexto = precisaNivel || precisaFormato || precisaParticipantes



  let badgeNum = 0



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

          Registramos que seu relato está relacionado a{' '}

          <strong>{sintese}</strong>.

        </p>

      </div>



      {precisaContexto && (

        <div className="card">

          <span className="card-title">Para personalizar seu roteiro</span>

          <p className="muted">

            {Object.keys(contextoAuto).some((k) => contextoAuto[k])

              ? 'Complete apenas as informações que ainda não identificamos no seu relato:'

              : 'Responda às perguntas complementares para deixar a aula alinhada à sua turma:'}

          </p>



          {precisaNivel && (

            <div className="numbered">

              <div className="num-badge">{++badgeNum}</div>

              <div className="field">

                <label htmlFor="nivel">Nível de ensino</label>

                <select

                  id="nivel"

                  className="select"

                  value={nivel}

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

                <label htmlFor="formato">Formato da aula</label>

                <select

                  id="formato"

                  className="select"

                  value={formato}

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

                <label htmlFor="participantes">Quantidade de participantes</label>

                <input

                  id="participantes"

                  className="input"

                  type="number"

                  min="1"

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

            Identificamos no seu relato o nível de ensino, a modalidade e a

            quantidade de participantes. Você pode seguir para gerar o roteiro.

          </p>

        </div>

      )}



      <div className="card methodology">

        <span className="section-label">Direção metodológica</span>

        {carregandoDiag ? (

          <p className="muted methodology-loading">

            <Loader2 size={16} className="spin" /> Analisando seu desafio...

          </p>

        ) : diagnostico?.grupo_titulo ? (

          <>

            <p className="methodology-name">

              <Layers size={18} style={{ verticalAlign: 'middle', marginRight: 6 }} />

              {diagnostico.grupo_titulo}

            </p>

            <p className="muted">{diagnostico.grupo_descricao}</p>

            <p className="muted" style={{ marginTop: 8 }}>

              {texto(
                'resultado.grupo_nota',
                'A metodologia específica será definida na geração do seu roteiro, dentro deste grupo da Biblioteca de Metodologias Inov-ativas.',
              )}

            </p>

          </>

        ) : (

          <p className="muted">

            {texto(
              'resultado.previa_fallback',
              'Ao gerar seu roteiro, identificaremos o grupo e a metodologia inov-ativa mais adequados ao seu desafio — com uma justificativa para a sua turma.',
            )}

          </p>

        )}

      </div>



      <button

        type="button"

        className="btn btn-primary"

        onClick={() =>

          navigate('/cadastro', {

            state: {

              desafio,

              opcoes,

              nivel,

              formato,

              participantes,

              sintese,

              metodologia: diagnostico?.metodologia,

              justificativa: diagnostico?.justificativa,

            },

          })

        }

      >

        <FileText size={18} />

        Gerar Roteiro de Aulas personalizado

      </button>



      <button type="button" className="link-subtle" onClick={() => navigate('/')}>

        Começar de novo

      </button>

    </div>

  )

}



export default Resultado


