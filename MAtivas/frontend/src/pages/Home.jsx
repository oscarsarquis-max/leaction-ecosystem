import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition.js'
import {
  Mic,
  Square,
  Target,
  Sparkles,
  Send,
  Lightbulb,
  ExternalLink,
} from 'lucide-react'
import TopBar from '../components/TopBar.jsx'
import capaLivro from '../assets/capa-livro.png'
import fotoAndrea from '../assets/foto-andrea.jpeg'
import { useUiContent } from '../contexts/UiContentContext.jsx'

const QUICK_OPTIONS = [
  { label: 'Falta de engajamento', Icon: Target, cor: 'purple' },
  { label: 'Uso de IA', Icon: Sparkles, cor: 'blue' },
]

const MAX_CHARS = 800

function Home() {
  const navigate = useNavigate()
  const location = useLocation()
  const { texto, imagem } = useUiContent()
  const [desafio, setDesafio] = useState('')
  const [selecionadas, setSelecionadas] = useState([])

  const handleTranscript = useCallback((text) => setDesafio(text), [])

  const { listening, error: erroVoz, toggle: toggleVoz, stop: pararVoz } = useSpeechRecognition({
    onResult: handleTranscript,
    lang: 'pt-BR',
    maxChars: MAX_CHARS,
  })

  useEffect(() => {
    pararVoz()
    setDesafio('')
    setSelecionadas([])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.key])

  useEffect(() => () => pararVoz(), [pararVoz])

  const toggleOpcao = (opcao) => {
    setSelecionadas((prev) =>
      prev.includes(opcao) ? prev.filter((o) => o !== opcao) : [...prev, opcao],
    )
  }

  const podeEnviar = desafio.trim().length > 0 || selecionadas.length > 0

  const enviar = () => {
    pararVoz()
    navigate('/resultado', {
      state: { desafio: desafio.trim(), opcoes: selecionadas },
    })
  }

  return (
    <div className="page">
      <TopBar />

      <header>
        <h1 className="page-title">
          {texto('home.titulo', 'Olá, Professor(a)! Como posso ajudar na sua próxima aula?')}
        </h1>
        <p className="page-subtitle">
          {texto(
            'home.subtitulo',
            'Conte qual desafio você está enfrentando em sala e receba uma metodologia inov-ativa sob medida, com um roteiro pronto para aplicar.',
          )}
        </p>
      </header>

      <div className="card challenge-card">
        <span className="section-label">Conte seu desafio</span>

        <button
          type="button"
          className={`audio-btn${listening ? ' recording' : ''}`}
          onClick={() => toggleVoz(desafio)}
          aria-pressed={listening}
          aria-label={listening ? 'Parar gravação de voz' : 'Falar sobre seu desafio'}
        >
          <span className="audio-circle">
            {listening ? <Square size={28} fill="currentColor" /> : <Mic size={30} />}
          </span>
          <span>
            {listening ? 'Gravando... toque para parar' : 'Fale sobre seu desafio'}
          </span>
        </button>

        {erroVoz && <p className="audio-error">{erroVoz}</p>}

        <div className="divider">ou escreva abaixo</div>

        <div className="textarea-wrap">
          <textarea
            id="desafio"
            className="textarea"
            placeholder="Ex: Meus alunos não participam das discussões em grupo..."
            maxLength={MAX_CHARS}
            value={desafio}
            onChange={(e) => setDesafio(e.target.value)}
          />
          <span className="char-count">
            {desafio.length}/{MAX_CHARS}
          </span>
        </div>
      </div>

      <div className="field">
        <span className="section-label">Seleção rápida</span>
        <div className="chip-grid chip-grid--duo">
          {QUICK_OPTIONS.map(({ label, Icon, cor }) => (
            <button
              key={label}
              type="button"
              className={`chip-card${selecionadas.includes(label) ? ' selected' : ''}`}
              onClick={() => toggleOpcao(label)}
            >
              <span className={`chip-ico ${cor}`}>
                <Icon size={22} />
              </span>
              {label}
            </button>
          ))}
        </div>
      </div>

      <button
        type="button"
        className="btn btn-primary"
        disabled={!podeEnviar}
        onClick={enviar}
      >
        <Send size={18} />
        Enviar meu desafio
      </button>

      <button type="button" className="hint-box" onClick={() => navigate('/exemplo')}>
        <Lightbulb className="icon" size={20} />
        Veja um exemplo de resposta que você receberá
      </button>

      <div className="card book-strip">
        <img
          className="book-strip-cover"
          src={imagem('assets.capa_livro', capaLivro)}
          alt={texto('home.livro_titulo', 'Metodologias inov-ativas na educação')}
        />
        <div className="book-strip-text">
          <span className="book-strip-title">
            {texto('home.livro_titulo', 'Metodologias inov-ativas na educação')}
          </span>
          <span className="muted">
            {texto(
              'home.livro_descricao',
              'As metodologias sugeridas são baseadas nesta obra de Andrea Filatro.',
            )}
          </span>
        </div>
      </div>

      <div className="author">
        <img
          className="author-photo"
          src={imagem('assets.foto_andrea', fotoAndrea)}
          alt="Andrea Filatro"
        />
        <span className="author-text">
          <span className="author-thanks">Uma realização de</span>
          <span className="author-name">Andrea Filatro</span>
          <a
            className="author-link"
            href="https://www.andreafilatro.com.br"
            target="_blank"
            rel="noopener noreferrer"
          >
            www.andreafilatro.com.br
            <ExternalLink size={13} />
          </a>
        </span>
      </div>
    </div>
  )
}

export default Home
