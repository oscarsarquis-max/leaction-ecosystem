import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { PartyPopper, Check, Loader2, AlertCircle } from 'lucide-react'
import TopBar from '../components/TopBar.jsx'
import { atualizarLivro } from '../services/api.js'
import capaLivro from '../assets/capa-livro.png'
import { useUiContent } from '../contexts/UiContentContext.jsx'

const OPCOES = [
  'Livro físico',
  'Versão digital',
  'Acesso por biblioteca',
  'Ainda não conheço',
  'Quero conhecer',
]

function Livro() {
  const navigate = useNavigate()
  const location = useLocation()
  const { email, fromRoteiro } = location.state || {}
  const { texto, imagem } = useUiContent()

  const [resposta, setResposta] = useState('')
  const [ecossistema, setEcossistema] = useState(false)
  const [salvo, setSalvo] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')

  const salvar = async (e) => {
    e.preventDefault()
    if (!resposta) return

    setEnviando(true)
    setErro('')

    try {
      // Só persiste se houver e-mail (professor já cadastrado no fluxo).
      if (email) {
        await atualizarLivro({
          email,
          status_livro: resposta,
          opt_in_ecossistema: ecossistema,
        })
      }
      setSalvo(true)
    } catch (err) {
      const detalhe =
        err?.response?.data?.detalhe ||
        err?.response?.data?.erro ||
        err?.message ||
        'Erro desconhecido'
      setErro(`Não foi possível salvar: ${detalhe}`)
    } finally {
      setEnviando(false)
    }
  }

  if (salvo) {
    return (
      <div className="page">
        <TopBar />
        <header>
          <span className="section-label">
            <PartyPopper size={16} /> Tudo certo
          </span>
          <h1 className="page-title">Obrigado por participar!</h1>
          <p className="page-subtitle">
            Suas respostas foram salvas
            {ecossistema
              ? ' e você agora faz parte do Ecossistema de Metodologias Inov-ativas.'
              : '.'}{' '}
            Bons estudos e ótima aula!
          </p>
        </header>

        <button
          type="button"
          className="btn btn-primary"
          onClick={() => navigate('/', { replace: true, state: { resetHome: true } })}
        >
          Criar um novo roteiro
        </button>
      </div>
    )
  }

  return (
    <form className="page" onSubmit={salvar}>
      <TopBar showBack backTo={-1} />

      <header>
        <span className="section-label">Sobre o livro</span>
        {!fromRoteiro && (
          <div className="livro-head">
            <img
              className="livro-capa"
              src={imagem('assets.capa_livro', capaLivro)}
              alt={texto('livro.titulo', 'Metodologias inov-ativas na educação')}
            />
            <h1 className="page-title">
              {texto('livro.titulo', 'Você já conhece o livro Metodologias inov-ativas na educação?')}
            </h1>
          </div>
        )}
        {fromRoteiro && (
          <h1 className="page-title">
            Conte-nos sobre sua relação com o livro
          </h1>
        )}
        <p className="page-subtitle">
          Sua resposta nos ajuda a recomendar os melhores conteúdos para você.
        </p>
      </header>

      <div className="option-list">
        {OPCOES.map((opcao) => (
          <label
            key={opcao}
            className={`option${resposta === opcao ? ' checked' : ''}`}
          >
            <input
              type="radio"
              name="livro"
              value={opcao}
              checked={resposta === opcao}
              onChange={(e) => setResposta(e.target.value)}
            />
            {opcao}
          </label>
        ))}
      </div>

      <label className={`option${ecossistema ? ' checked' : ''}`}>
        <input
          type="checkbox"
          checked={ecossistema}
          onChange={(e) => setEcossistema(e.target.checked)}
        />
        {texto('livro.ecossistema', 'Quero fazer parte do Ecossistema de Metodologias Inov-ativas')}
      </label>

      {erro && (
        <p className="notice error-notice">
          <AlertCircle className="icon" size={18} />
          {erro}
        </p>
      )}

      <button
        type="submit"
        className="btn btn-primary"
        disabled={!resposta || enviando}
      >
        {enviando ? (
          <>
            <Loader2 size={18} className="spin" />
            Salvando...
          </>
        ) : (
          <>
            <Check size={18} />
            Salvar e continuar
          </>
        )}
      </button>
    </form>
  )
}

export default Livro
