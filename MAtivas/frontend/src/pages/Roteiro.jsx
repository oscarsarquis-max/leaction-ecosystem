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

  Heart,

} from 'lucide-react'

import TopBar from '../components/TopBar.jsx'
import EmailRoteiroModal from '../components/EmailRoteiroModal.jsx'
import Toast from '../components/Toast.jsx'
import { curtirRoteiro, enviarFeedback } from '../services/api.js'

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
      'Escolha uma situação relacionada ao tema do curso ou disciplina e contextualize-a em aspectos históricos, sociais, técnicos, econômicos, culturais, éticos ou profissionais. Formule perguntas disparadoras, como: "O que já sabemos sobre o problema?", "O que ainda precisamos descobrir?", "Quais hipóteses iniciais parecem plausíveis?", "Que evidências podem confirmar, revisar ou refutar essas hipóteses?" e "Que critérios usaremos para escolher uma solução?".',
    tempo: '15 min',
  },
  {
    titulo: 'Estabeleça um contrato didático com e entre os estudantes',
    descricao:
      'Defina com a turma as regras de trabalho, prazos, produtos esperados, critérios de participação, formas de registro, organização dos grupos, fontes de pesquisa e instrumentos de avaliação. O contrato didático ajuda os estudantes a compreenderem o que eles devem produzir, como devem colaborar e como serão avaliados.',
    tempo: '10 min',
  },
  {
    titulo: 'Oriente a exploração inicial',
    descricao:
      'Ofereça referências, casos, dados, fontes, vídeos, textos, bases de informação ou exemplos. O objetivo é apoiar a investigação sem entregar a solução para o problema. Nessa etapa, ajude os estudantes a identificar conceitos-chave, lacunas de conhecimento e focos de pesquisa.',
    tempo: '15 min',
  },
  {
    titulo: 'Acompanhe a pesquisa e a produção individual',
    descricao:
      'Peça que cada estudante pesquise em fontes teóricas, técnicas, empíricas ou digitais e produza uma síntese individual com achados, dúvidas, hipóteses ou proposta inicial de solução. Durante esse processo, sugira fontes, apoie a leitura crítica, oriente registros e provoque aprofundamento conceitual.',
    tempo: '20 min',
  },
  {
    titulo: 'Promova a discussão coletiva',
    descricao:
      'Organize a socialização das pesquisas individuais. Estimule a comparação de descobertas, a argumentação, a escuta, a identificação de convergências e divergências e a negociação de caminhos de solução. Essa etapa transforma a pesquisa individual em construção coletiva.',
    tempo: '20 min',
  },
  {
    titulo: 'Oriente a produção coletiva',
    descricao:
      'Apoie os grupos na construção da proposta de solução. Monitore a colaboração, a coerência conceitual, a integração das contribuições individuais e a justificativa das escolhas. A produção pode assumir diferentes formatos, como proposta, plano de ação, relatório, protótipo, apresentação, diagnóstico ou solução técnica.',
    tempo: '20 min',
  },
  {
    titulo: 'Coordene a apresentação e a avaliação da produção',
    descricao:
      'Organize a apresentação das soluções e aplique uma rubrica de avaliação ou outro instrumento de sua preferência. Considere critérios como pertinência da solução, fundamentação, viabilidade, criatividade, clareza, aplicabilidade e qualidade técnica. Ofereça feedback para que os estudantes possam revisar ou aprimorar a proposta.',
    tempo: '15 min',
  },
  {
    titulo: 'Conduza a avaliação da aprendizagem e do processo',
    descricao:
      'Avalie domínio conceitual, raciocínio, investigação, participação, argumentação, colaboração e contribuição individual para o grupo. Proponha autoavaliação e/ou avaliação por pares e/ou finalize com uma reflexão sobre o processo, sistematizando aprendizados e possíveis novas problematizações.',
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
  const [curtido, setCurtido] = useState(false)
  const [curtindo, setCurtindo] = useState(false)



  const baixarPDF = async () => {
    const PRIMARY = [79, 70, 229]
    const PRIMARY_DARK = [59, 40, 204]
    const PRIMARY_SOFT = [243, 240, 255]
    const SECONDARY = [225, 29, 72]
    const TEXT = [51, 51, 51]
    const MUTED = [107, 114, 128]
    const BORDER = [233, 231, 245]

    const carregarImagem = (src) =>
      new Promise((resolve) => {
        if (!src) {
          resolve(null)
          return
        }
        const img = new Image()
        img.crossOrigin = 'anonymous'
        img.onload = () => resolve(img)
        img.onerror = () => resolve(null)
        img.src = src
      })

    const [logoImg, capaImg] = await Promise.all([
      carregarImagem('/brand/logo.png'),
      carregarImagem(imagem('assets.capa_livro', capaLivro)),
    ])

    const doc = new jsPDF({ unit: 'pt', format: 'a4' })
    const pageW = doc.internal.pageSize.getWidth()
    const pageH = doc.internal.pageSize.getHeight()
    const margin = 42
    const contentW = pageW - margin * 2
    let y = margin

    const garantirEspaco = (altura) => {
      if (y + altura > pageH - margin) {
        doc.addPage()
        y = margin
      }
    }

    const textoMultilinha = (texto, x, maxW, { size = 11, style = 'normal', cor = TEXT, leading = 1.45 } = {}) => {
      doc.setFont('helvetica', style)
      doc.setFontSize(size)
      doc.setTextColor(...cor)
      const linhas = doc.splitTextToSize(String(texto || ''), maxW)
      const lineH = size * leading
      linhas.forEach((linha) => {
        garantirEspaco(lineH)
        doc.text(linha, x, y)
        y += lineH
      })
      return linhas.length * lineH
    }

    const caixaSuave = (titulo, linhasConteudo) => {
      const pad = 12
      const titleSize = 11
      const bodySize = 10
      const innerW = contentW - pad * 2 - 8
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(titleSize)
      const titleLines = doc.splitTextToSize(titulo, innerW)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(bodySize)
      const bodyLines = linhasConteudo.flatMap((linha) => doc.splitTextToSize(linha, innerW))
      const boxH =
        pad * 2 +
        titleLines.length * titleSize * 1.35 +
        6 +
        bodyLines.length * bodySize * 1.45
      garantirEspaco(boxH + 10)
      doc.setFillColor(...PRIMARY_SOFT)
      doc.setDrawColor(...BORDER)
      doc.roundedRect(margin + 4, y, contentW - 8, boxH, 8, 8, 'FD')
      const startY = y
      y += pad + titleSize
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(titleSize)
      doc.setTextColor(...PRIMARY_DARK)
      titleLines.forEach((linha) => {
        doc.text(linha, margin + 4 + pad, y)
        y += titleSize * 1.35
      })
      y += 4
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(bodySize)
      doc.setTextColor(...TEXT)
      bodyLines.forEach((linha) => {
        doc.text(linha, margin + 4 + pad, y)
        y += bodySize * 1.45
      })
      y = Math.max(y, startY + boxH) + 10
    }

    // Logo
    if (logoImg) {
      const logoH = 36
      const logoW = (logoImg.width / logoImg.height) * logoH
      garantirEspaco(logoH + 16)
      doc.addImage(logoImg, 'PNG', margin, y, Math.min(logoW, 200), logoH)
      y += logoH + 18
    }

    // Saudação
    textoMultilinha(`Olá, ${nome || 'Professor(a)'}.`, margin, contentW, {
      size: 18,
      style: 'bold',
      cor: TEXT,
      leading: 1.25,
    })
    y += 8

    // Intro
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(11)
    doc.setTextColor(...MUTED)
    const introPrefix =
      'Com base no desafio que você compartilhou, elaboramos um Roteiro de Aulas inspirado na metodologia '
    const introLines = doc.splitTextToSize(introPrefix + metodologiaNome + '.', contentW)
    introLines.forEach((linha, idx) => {
      garantirEspaco(16)
      if (idx === introLines.length - 1 && linha.includes(metodologiaNome)) {
        const before = linha.slice(0, linha.lastIndexOf(metodologiaNome))
        const after = linha.slice(linha.lastIndexOf(metodologiaNome) + metodologiaNome.length)
        let x = margin
        if (before) {
          doc.setTextColor(...MUTED)
          doc.setFont('helvetica', 'normal')
          doc.text(before, x, y)
          x += doc.getTextWidth(before)
        }
        doc.setTextColor(...PRIMARY)
        doc.setFont('helvetica', 'bold')
        doc.text(metodologiaNome, x, y)
        x += doc.getTextWidth(metodologiaNome)
        if (after) {
          doc.setTextColor(...MUTED)
          doc.setFont('helvetica', 'normal')
          doc.text(after, x, y)
        }
      } else {
        doc.setTextColor(...MUTED)
        doc.setFont('helvetica', 'normal')
        doc.text(linha, margin, y)
      }
      y += 16
    })
    y += 8

    // Disclaimer + capa (como no e-mail)
    const disclaimer = texto(
      'roteiro.disclaimer_ia',
      'Este Roteiro foi gerado por inteligência artificial com base na obra Metodologias inov-ativas na educação. Você conhece sua turma melhor do que ninguém. Analise, adapte e enriqueça as propostas antes de utilizá-las.',
    )
    const capaW = 90
    const capaGap = 14
    const textW = capaImg ? contentW - capaW - capaGap : contentW
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(10)
    const discLines = doc.splitTextToSize(disclaimer, textW)
    const discH = discLines.length * 14
    const capaH = capaImg ? (capaImg.height / capaImg.width) * capaW : 0
    const blockH = Math.max(discH, capaH)
    garantirEspaco(blockH + 16)
    const blockTop = y
    doc.setTextColor(...MUTED)
    discLines.forEach((linha, i) => {
      doc.text(linha, margin, blockTop + 10 + i * 14)
    })
    if (capaImg) {
      doc.addImage(capaImg, 'PNG', margin + textW + capaGap, blockTop, capaW, capaH)
    }
    y = blockTop + blockH + 18

    // Card do roteiro
    const cardPad = 16
    const cardX = margin
    const cardInnerW = contentW - cardPad * 2
    garantirEspaco(80)

    // Cabeçalho do card
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(15)
    doc.setTextColor(...PRIMARY_DARK)
    doc.text('Seu Roteiro de Aulas', cardX + cardPad, y + 14)
    y += 30
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(11)
    doc.setTextColor(...SECONDARY)
    textoMultilinha(`Metodologia recomendada: ${metodologiaNome}`, cardX + cardPad, cardInnerW, {
      size: 11,
      style: 'bold',
      cor: SECONDARY,
      leading: 1.35,
    })
    y += 8

    if (textoDesafio || nivel || formato || participantes) {
      const ctxLinhas = [`Desafio: ${textoDesafio || '—'}`]
      if (nivel) ctxLinhas.push(`Nível de ensino: ${nivel}`)
      if (formato) ctxLinhas.push(`Modalidade: ${formato}`)
      if (participantes) ctxLinhas.push(`Participantes: ${participantes}`)
      caixaSuave('Contexto do seu relato', ctxLinhas)
    }

    if (justificativa) {
      caixaSuave('Por que esta metodologia?', [justificativa])
    }

    textoMultilinha('Passo a passo', cardX + cardPad, cardInnerW, {
      size: 12,
      style: 'bold',
      cor: PRIMARY,
      leading: 1.3,
    })
    y += 8

    listaPassos.forEach((passo, i) => {
      const num = i + 1
      const titulo = passo.titulo || `Passo ${num}`
      const desc = passo.descricao || passo.desc || ''
      const tempo = passo.tempo || ''

      doc.setFont('helvetica', 'bold')
      doc.setFontSize(11)
      const titleLines = doc.splitTextToSize(titulo, cardInnerW - 36)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(10)
      const descLines = doc.splitTextToSize(desc, cardInnerW - 36)
      const stepH =
        Math.max(22, titleLines.length * 14) +
        (tempo ? 14 : 0) +
        descLines.length * 13 +
        14

      garantirEspaco(stepH)

      // número
      doc.setFillColor(...PRIMARY)
      doc.roundedRect(cardX + cardPad, y, 22, 22, 5, 5, 'F')
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(11)
      doc.setTextColor(255, 255, 255)
      doc.text(String(num), cardX + cardPad + 11, y + 15, { align: 'center' })

      let ty = y + 14
      const tx = cardX + cardPad + 32
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(11)
      doc.setTextColor(...TEXT)
      titleLines.forEach((linha) => {
        doc.text(linha, tx, ty)
        ty += 14
      })
      if (tempo) {
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(9)
        doc.setTextColor(...MUTED)
        doc.text(`Tempo: ${tempo}`, tx, ty)
        ty += 14
      }
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(10)
      doc.setTextColor(...MUTED)
      descLines.forEach((linha) => {
        doc.text(linha, tx, ty)
        ty += 13
      })
      y = Math.max(y + 28, ty) + 10
    })

    y += 6
    textoMultilinha(
      'Roteiro baseado nas estratégias do livro "Metodologias inov-ativas na educação", de Andrea Filatro.',
      cardX + cardPad,
      cardInnerW,
      { size: 9, style: 'italic', cor: MUTED, leading: 1.45 },
    )

    if (roteiroId) {
      y += 10
      textoMultilinha(`Referência do roteiro: #${roteiroId}`, cardX + cardPad, cardInnerW, {
        size: 8,
        style: 'normal',
        cor: [148, 163, 184],
        leading: 1.3,
      })
    }

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

  const handleCurtir = async () => {
    if (curtindo) return
    const proximo = !curtido
    setCurtido(proximo)
    if (!roteiroId) return

    setCurtindo(true)
    try {
      await curtirRoteiro(roteiroId, proximo)
    } catch {
      setCurtido(!proximo)
    } finally {
      setCurtindo(false)
    }
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
            {texto(
              'roteiro.disclaimer_ia',
              'Este Roteiro foi gerado por inteligência artificial com base na obra Metodologias inov-ativas na educação. Você conhece sua turma melhor do que ninguém. Analise, adapte e enriqueça as propostas antes de utilizá-las.',
            )}
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

          <div className="roteiro-like-wrap">
            <button
              type="button"
              className={`roteiro-like${curtido ? ' roteiro-like--on' : ''}`}
              onClick={handleCurtir}
              disabled={curtindo}
              aria-pressed={curtido}
              aria-label={curtido ? 'Roteiro curtido' : 'Curtir roteiro'}
              title={curtido ? 'Curtido' : 'Curtir'}
            >
              <Heart size={28} strokeWidth={2} fill={curtido ? 'currentColor' : 'none'} />
            </button>
          </div>

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


