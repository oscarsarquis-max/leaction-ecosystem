import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ShieldCheck, FileText, Loader2, AlertCircle } from 'lucide-react'
import TopBar from '../components/TopBar.jsx'
import { criarRoteiro, verificarStatusRoteiro } from '../services/api.js'
import { useUiText } from '../contexts/UiContentContext.jsx'

const POLL_INTERVAL = 3000 // ms

const ESTADOS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
  'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
  'SP', 'SE', 'TO',
]

function Cadastro() {
  const navigate = useNavigate()
  const location = useLocation()
  const avisoPrivacidade = useUiText(
    'cadastro.privacidade',
    'Usamos seus dados apenas para enviar o roteiro de aulas por e-mail e, se você autorizar, novidades sobre metodologias inov-ativas.',
  )
  // Dados acumulados das telas anteriores (Home -> Resultado -> aqui)
  const { desafio, opcoes, nivel, formato, participantes, sintese,
    metodologia, justificativa } = location.state || {}

  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [estado, setEstado] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')

  // Guarda o id do setInterval do polling para limpeza segura.
  const pollRef = useRef(null)
  const envioEmAndamentoRef = useRef(false)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  const podeEnviar =
    nome.trim().length > 1 && emailValido && estado !== '' && !enviando

  const pararPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const irParaRoteiro = (resultado) => {
    navigate('/roteiro', {
      state: {
        nome: nome.trim(),
        email: email.trim(),
        roteiroId: resultado.roteiroId,
        metodologia: resultado.metodologia_recomendada,
        justificativa: resultado.justificativa,
        passos: resultado.passos,
        desafio,
        opcoes,
        nivel,
        formato,
        participantes,
        sintese,
      },
    })
  }

  // Consulta o status a cada POLL_INTERVAL até concluir ou falhar.
  const iniciarPolling = (roteiroId) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await verificarStatusRoteiro(roteiroId)
        if (res.status === 'Concluido') {
          pararPolling()
          irParaRoteiro(res)
        } else if (res.status === 'Erro') {
          pararPolling()
          setEnviando(false)
          setErro('Não foi possível gerar o roteiro. Por favor, tente novamente.')
        }
        // 'Pendente': mantém o spinner e continua aguardando
      } catch (err) {
        pararPolling()
        setEnviando(false)
        const detalhe =
          err?.response?.data?.detalhe || err?.message || 'Erro desconhecido'
        setErro(`Falha ao consultar o status: ${detalhe}`)
      }
    }, POLL_INTERVAL)
  }

  const enviar = async (e) => {
    e.preventDefault()
    if (!podeEnviar || envioEmAndamentoRef.current) return

    envioEmAndamentoRef.current = true
    setEnviando(true)
    setErro('')

    const payload = {
      nome: nome.trim(),
      email: email.trim(),
      estado,
      desafio,
      opcoes,
      nivel,
      formato,
      participantes,
      sintese,
      metodologia,
      justificativa,
    }

    try {
      // 202 Accepted -> tarefa enfileirada; inicia o polling de status.
      const { roteiroId } = await criarRoteiro(payload)
      iniciarPolling(roteiroId)
    } catch (err) {
      const detalhe =
        err?.response?.data?.detalhe ||
        err?.response?.data?.erro ||
        err?.message ||
        'Erro desconhecido'
      setErro(`Não foi possível gerar o roteiro: ${detalhe}`)
      setEnviando(false)
      envioEmAndamentoRef.current = false
    }
  }

  return (
    <form className="page" onSubmit={enviar}>
      <TopBar showBack backTo={-1} />

      <header>
        <span className="section-label">Quase lá</span>
        <h1 className="page-title">Para onde enviamos seu roteiro?</h1>
        <p className="page-subtitle">
          Preencha seus dados para gerar e receber o roteiro de aulas
          personalizado.
        </p>
      </header>

      <div className="field">
        <label htmlFor="nome">Nome completo</label>
        <input
          id="nome"
          className="input"
          type="text"
          placeholder="Seu nome"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
        />
      </div>

      <div className="field">
        <label htmlFor="email">E-mail</label>
        <input
          id="email"
          className="input"
          type="email"
          placeholder="voce@escola.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>

      <div className="field">
        <label htmlFor="estado">Estado de atuação</label>
        <select
          id="estado"
          className="select"
          value={estado}
          onChange={(e) => setEstado(e.target.value)}
        >
          <option value="">Selecione</option>
          {ESTADOS.map((uf) => (
            <option key={uf} value={uf}>
              {uf}
            </option>
          ))}
        </select>
      </div>

      <p className="notice">
        <ShieldCheck className="icon" size={18} />
        {avisoPrivacidade}
      </p>

      {erro && (
        <p className="notice error-notice">
          <AlertCircle className="icon" size={18} />
          {erro}
        </p>
      )}

      <button type="submit" className="btn btn-primary" disabled={!podeEnviar}>
        {enviando ? (
          <>
            <Loader2 size={18} className="spin" />
            Gerando seu roteiro...
          </>
        ) : (
          <>
            <FileText size={18} />
            Enviar cadastro e gerar Roteiro de Aulas
          </>
        )}
      </button>
    </form>
  )
}

export default Cadastro
