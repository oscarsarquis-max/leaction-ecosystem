import { useNavigate } from 'react-router-dom'
import { Target, Sparkles, BookOpen, ArrowLeft } from 'lucide-react'
import TopBar from '../components/TopBar.jsx'
import { useUiText } from '../contexts/UiContentContext.jsx'

function Exemplo() {
  const navigate = useNavigate()
  const titulo = useUiText('exemplo.titulo', 'Veja como a plataforma responde')

  return (
    <div className="page">
      <TopBar showBack backTo="/" />

      <header>
        <span className="section-label">Exemplo de resposta</span>
        <h1 className="page-title">{titulo}</h1>
        <p className="page-subtitle">
          Este é um exemplo do que você recebe ao enviar um desafio real.
        </p>
      </header>

      <div className="card card-soft">
        <span className="card-title">
          <Target size={18} /> Desafio enviado
        </span>
        <p>
          “Meus alunos do 8º ano não se engajam nas atividades em grupo e poucos
          participam das discussões.”
        </p>
      </div>

      <div className="card">
        <span className="card-title">
          <Sparkles size={18} /> Entendemos seu desafio
        </span>
        <p className="muted">
          O baixo engajamento em atividades coletivas costuma estar ligado à
          falta de papéis claros e de um objetivo comum entre os estudantes.
        </p>
      </div>

      <div className="card methodology">
        <span className="section-label">Metodologia recomendada</span>
        <p className="methodology-name">Aprendizagem Colaborativa</p>
        <p className="muted">
          Distribui responsabilidades entre os alunos e cria interdependência
          positiva, aumentando a participação de todos.
        </p>
      </div>

      <div className="card card-alt">
        <span className="card-title">
          <BookOpen size={18} /> Roteiro resumido
        </span>
        <ul style={{ paddingLeft: '1.1rem', color: 'var(--color-muted)' }}>
          <li>Organize grupos de 4 com papéis definidos.</li>
          <li>Lance um desafio único com meta compartilhada.</li>
          <li>Feche com socialização das soluções.</li>
        </ul>
      </div>

      <button
        type="button"
        className="btn btn-primary"
        onClick={() => navigate('/')}
      >
        <ArrowLeft size={18} />
        Voltar e criar o meu
      </button>
    </div>
  )
}

export default Exemplo
