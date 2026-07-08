import { useState } from 'react'

import { useLocation, useNavigate } from 'react-router-dom'

import { jsPDF } from 'jspdf'

import {

  ClipboardList,

  Users,

  Target,

  MessageCircle,

  Megaphone,

  CheckCircle,

  Download,

  BookOpen,

  Mail,

  Send,

  Clock,

  Loader2,

  Check,

  AlertCircle,

  Lightbulb,

  ListChecks,

} from 'lucide-react'

import TopBar from '../components/TopBar.jsx'
import EmailRoteiroModal from '../components/EmailRoteiroModal.jsx'
import Toast from '../components/Toast.jsx'
import { enviarFeedback } from '../services/api.js'

import capaLivro from '../assets/capa-livro.png'
import { useUiContent } from '../contexts/UiContentContext.jsx'

const METODOLOGIA = 'Aprendizagem Colaborativa'



const VISUAL = [

  { Icon: Users, cor: 'purple' },

  { Icon: Target, cor: 'pink' },

  { Icon: MessageCircle, cor: 'blue' },

  { Icon: Megaphone, cor: 'green' },

  { Icon: CheckCircle, cor: 'purple' },

]



const PASSOS_PADRAO = [
  {
    titulo: 'Apresente a situação-problema',
    descricao:
      'Escolha uma situação relacionada ao tema do curso ou disciplina e contextualize-a em aspectos históricos, sociais, técnicos, econômicos, culturais, éticos ou profissionais.',
    tempo: '15 min',
  },
  {
    titulo: 'Estabeleça um contrato didático com e entre os estudantes',
    descricao:
      'Defina com a turma as regras de trabalho, prazos, produtos esperados, critérios de participação e instrumentos de avaliação.',
    tempo: '10 min',
  },
  {
    titulo: 'Oriente a exploração inicial',
    descricao:
      'Ofereça referências, casos, dados ou exemplos para apoiar a investigação sem entregar a solução.',
    tempo: '15 min',
  },
  {
    titulo: 'Promova a discussão coletiva',
    descricao:
      'Organize a socialização das pesquisas individuais e estimule argumentação, escuta e negociação de caminhos de solução.',
    tempo: '20 min',
  },
  {
    titulo: 'Conduza a avaliação da aprendizagem e do processo',
    descricao:
      'Avalie domínio conceitual, participação e colaboração; proponha autoavaliação ou reflexão final sobre o processo.',
    tempo: '10 min',
  },
]



function montarTextoDesafio(desafio, opcoes, sintese) {

  const partes = []

  if (desafio?.trim()) partes.push(desafio.trim())

  if (opcoes?.length) partes.push(opcoes.join(', '))

  if (!partes.length && sintese) partes.push(sintese)

  return partes.join(' · ')

}



function Roteiro() {

  const navigate = useNavigate()

  const location = useLocation()

  const { texto, imagem, formatar } = useUiContent()

  const {

    nome,

    email,

    roteiroId,

    metodologia,

    justificativa,

    passos,

    desafio,

    opcoes,

    nivel,

    formato,

    participantes,

    sintese,

    veioDoLivro,

  } = location.state || {}



  const metodologiaNome = metodologia || METODOLOGIA

  const listaPassos = Array.isArray(passos) && passos.length > 0 ? passos : PASSOS_PADRAO

  const textoDesafio = montarTextoDesafio(desafio, opcoes, sintese)



  const [feedback, setFeedback] = useState('')

  const [statusFeedback, setStatusFeedback] = useState('idle')

  const [erroFeedback, setErroFeedback] = useState('')

  const [livroVisitado, setLivroVisitado] = useState(Boolean(veioDoLivro))

  const [modalEmailAberto, setModalEmailAberto] = useState(false)
  const [toastVisivel, setToastVisivel] = useState(false)



  const baixarPDF = () => {

    const doc = new jsPDF({ unit: 'pt', format: 'a4' })

    const margin = 48

    const larguraUtil = doc.internal.pageSize.getWidth() - margin * 2

    const alturaPagina = doc.internal.pageSize.getHeight()

    let y = margin



    const novaPaginaSeNecessario = (altura) => {

      if (y + altura > alturaPagina - margin) {

        doc.addPage()

        y = margin

      }

    }



    const escreverBloco = (texto, { size = 11, style = 'normal', cor = [33, 33, 33], espaco = 6 } = {}) => {

      doc.setFont('helvetica', style)

      doc.setFontSize(size)

      doc.setTextColor(...cor)

      const linhas = doc.splitTextToSize(texto, larguraUtil)

      const alturaLinha = size * 1.35

      linhas.forEach((linha) => {

        novaPaginaSeNecessario(alturaLinha)

        doc.text(linha, margin, y)

        y += alturaLinha

      })

      y += espaco

    }



    escreverBloco('Metodologias Inov-ativas — Roteiro de Aulas', {

      size: 18,

      style: 'bold',

      cor: [79, 70, 229],

      espaco: 4,

    })



    if (textoDesafio) {

      escreverBloco('Contexto do seu relato', { size: 12, style: 'bold' })

      escreverBloco(`Desafio: ${textoDesafio}`, { size: 11, espaco: 4 })

      if (nivel) escreverBloco(`Nível de ensino: ${nivel}`, { size: 11, espaco: 4 })

      if (formato) escreverBloco(`Modalidade: ${formato}`, { size: 11, espaco: 4 })

      if (participantes) escreverBloco(`Participantes: ${participantes}`, { size: 11, espaco: 10 })

    }



    escreverBloco(`Metodologia recomendada: ${metodologiaNome}`, {

      size: 13,

      style: 'bold',

      cor: [225, 29, 72],

      espaco: 10,

    })



    if (justificativa) {

      escreverBloco('Por que esta metodologia?', { size: 12, style: 'bold' })

      escreverBloco(justificativa, { size: 11, style: 'normal', espaco: 14 })

    }



    escreverBloco('Passo a passo', { size: 12, style: 'bold', espaco: 8 })

    listaPassos.forEach((passo, i) => {

      const titulo = `${i + 1}. ${passo.titulo || ''}`.trim()

      const tempo = passo.tempo ? `  (${passo.tempo})` : ''

      escreverBloco(`${titulo}${tempo}`, { size: 11, style: 'bold', espaco: 2 })

      escreverBloco(passo.descricao || passo.desc || '', { size: 11, style: 'normal', espaco: 10 })

    })



    escreverBloco(

      'Roteiro baseado nas estratégias do livro "Metodologias inov-ativas na educação", de Andrea Filatro.',

      { size: 9, style: 'italic', cor: [120, 120, 120], espaco: 0 },

    )



    doc.save(`roteiro-inov-ativas${roteiroId ? `-${roteiroId}` : ''}.pdf`)

  }



  const enviarMensagem = async (e) => {

    e.preventDefault()

    if (!feedback.trim()) return



    if (!roteiroId) {

      setStatusFeedback('erro')

      setErroFeedback('Roteiro não identificado. Gere um roteiro pelo fluxo para enviar feedback.')

      return

    }



    setStatusFeedback('enviando')

    setErroFeedback('')

    try {

      await enviarFeedback(roteiroId, feedback.trim())

      setStatusFeedback('enviado')

      setFeedback('')

    } catch (err) {

      const detalhe =

        err?.response?.data?.detalhe ||

        err?.response?.data?.erro ||

        err?.message ||

        'Erro desconhecido'

      setStatusFeedback('erro')

      setErroFeedback(`Não foi possível enviar: ${detalhe}`)

    }

  }



  const irParaLivro = () => {

    setLivroVisitado(true)

    navigate('/livro', { state: { email, fromRoteiro: true } })

  }



  return (

    <div className="page">

      <TopBar showBack backTo={-1} />



      {email && (
        <div className="email-banner">
          <Mail className="icon" size={18} />
          <span>
            {texto(
              'roteiro.email_aviso',
              'Você pode receber uma cópia deste roteiro no e-mail:',
            )}{' '}
            <strong>{email}</strong>
          </span>
        </div>
      )}



      <div className="roteiro-grid">

        <div className="roteiro-intro">

          <h1 className="page-title">Olá, {nome || 'Professor(a)'}.</h1>

          <p>

            Com base no desafio que você compartilhou, elaboramos um Roteiro de

            Aulas inspirado na metodologia{' '}

            <strong style={{ color: 'var(--color-primary)' }}>{metodologiaNome}.</strong>

          </p>

          <p>

            Esperamos que ele ajude você a promover mais participação,

            engajamento e protagonismo dos estudantes.

          </p>

          <img

            className="capa-livro"

            src={imagem('assets.capa_livro', capaLivro)}

            alt="Capa do livro Metodologias inov-ativas na educação"

          />

        </div>



        <div>

          <div className="card">

            <div className="roteiro-head">

              <span className="roteiro-head-icon">

                <ClipboardList size={24} />

              </span>

              <span>

                <span className="roteiro-head-title">Seu Roteiro de Aulas</span>
                <br />
                <span className="roteiro-head-sub">
                  Metodologia recomendada: {metodologiaNome}
                </span>

              </span>

            </div>



            {textoDesafio && (

              <div className="rationale contexto-roteiro">

                <span className="rationale-title">

                  <ListChecks size={16} /> Contexto do seu relato

                </span>

                <ul className="contexto-lista">

                  <li>

                    <strong>Desafio:</strong> {textoDesafio}

                  </li>

                  {nivel && (

                    <li>

                      <strong>Nível de ensino:</strong> {nivel}

                    </li>

                  )}

                  {formato && (

                    <li>

                      <strong>Modalidade:</strong> {formato}

                    </li>

                  )}

                  {participantes && (

                    <li>

                      <strong>Participantes:</strong> {participantes}

                    </li>

                  )}

                </ul>

              </div>

            )}



            {justificativa && (

              <div className="rationale">

                <span className="rationale-title">

                  <Lightbulb size={16} /> Por que esta metodologia?

                </span>

                <p className="rationale-text">{formatar(justificativa)}</p>

              </div>

            )}



            <h3 className="steps-heading">Passo a passo</h3>

            <div className="steps">

              {listaPassos.map((passo, i) => {

                const { Icon, cor } = VISUAL[i] || VISUAL[0]

                return (

                  <div className="step" key={passo.titulo || i}>

                    <div className="step-index">{i + 1}</div>

                    <div className={`step-icon ${cor}`}>

                      <Icon size={22} />

                    </div>

                    <div className="step-body">

                      <span className="step-title">{passo.titulo}</span>

                      {passo.tempo && (

                        <span className="step-time">

                          <Clock size={13} /> {passo.tempo}

                        </span>

                      )}

                      <span className="step-desc">

                        {passo.descricao || passo.desc}

                      </span>

                    </div>

                  </div>

                )

              })}

            </div>

          </div>



          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: 14 }}
            onClick={baixarPDF}
          >
            <Download size={18} />
            Download do Roteiro de Aulas
          </button>

          {roteiroId && (
            <button
              type="button"
              className="btn btn-secondary"
              style={{ marginTop: 10, width: '100%' }}
              onClick={() => setModalEmailAberto(true)}
            >
              <Mail size={18} />
              Reenviar por E-mail
            </button>
          )}

        </div>

      </div>



      {!livroVisitado && (

        <div className="book-banner">

          <BookOpen className="book-banner-icon" size={28} />

          <p>

            Este Roteiro de Aulas foi baseado nas estratégias{' '}

            <strong>Faça Fácil</strong> do livro{' '}

            <span className="book-title">
              {texto('roteiro.livro_titulo', 'Metodologias inov-ativas na educação.')}
            </span>

          </p>

          <button

            type="button"

            className="btn btn-secondary btn-inline"

            onClick={irParaLivro}

          >

            <BookOpen size={18} />

            Conheça o livro

          </button>

        </div>

      )}



      <form className="feedback" onSubmit={enviarMensagem}>

        <div className="feedback-top">

          <span className="feedback-circle">

            <Mail size={26} />

          </span>

          <span>

            <span className="feedback-title">

              Compartilhe sua experiência com a autora

            </span>

            <br />

            <span className="feedback-sub">

              Adoraria saber como foi aplicar o roteiro de aulas na sua prática.

            </span>

          </span>

        </div>



        {statusFeedback === 'enviado' ? (

          <div className="feedback-ok">

            <Check size={18} /> Mensagem enviada. Muito obrigada!

          </div>

        ) : (

          <div className="feedback-form">

            <input

              className="input"

              type="text"

              placeholder="Escreva sua mensagem..."

              value={feedback}

              onChange={(e) => setFeedback(e.target.value)}

              disabled={statusFeedback === 'enviando'}

            />

            <button

              type="submit"

              className="icon-btn"

              aria-label="Enviar mensagem"

              disabled={!feedback.trim() || statusFeedback === 'enviando'}

            >

              {statusFeedback === 'enviando' ? (

                <Loader2 size={20} className="spin" />

              ) : (

                <Send size={20} />

              )}

            </button>

          </div>

        )}



        {statusFeedback === 'erro' && (

          <span className="feedback-erro">

            <AlertCircle size={14} /> {erroFeedback}

          </span>

        )}

      </form>

      <EmailRoteiroModal
        aberto={modalEmailAberto}
        onFechar={() => setModalEmailAberto(false)}
        emailInicial={email || ''}
        projectId={roteiroId}
        onSucesso={() => setToastVisivel(true)}
      />

      <Toast
        mensagem="Roteiro enviado com sucesso!"
        visivel={toastVisivel}
        onOcultar={() => setToastVisivel(false)}
      />
    </div>

  )

}



export default Roteiro


