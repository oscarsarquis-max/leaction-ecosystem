import { useEffect, useRef } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { ZONAS, firstAccessiblePath, hasAnyZona } from '../lib/rbac'
import './Market.css'

const FONTS_HREF =
  'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700;800&display=swap'

function useMarketFonts() {
  useEffect(() => {
    const id = 'market-fonts'
    if (document.getElementById(id)) return undefined
    const link = document.createElement('link')
    link.id = id
    link.rel = 'stylesheet'
    link.href = FONTS_HREF
    document.head.appendChild(link)
    return undefined
  }, [])
}

function useRevealOnScroll(rootRef, enabled) {
  useEffect(() => {
    if (!enabled || !rootRef.current) return undefined
    const els = rootRef.current.querySelectorAll('.reveal')
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('in')
            io.unobserve(e.target)
          }
        })
      },
      { threshold: 0.12 },
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [enabled, rootRef])
}

function MarketBlocked() {
  useMarketFonts()
  const { user } = useAuth()
  const fallback = firstAccessiblePath(user?.zonas || [])

  return (
    <div className="market-blocked">
      <div className="mark">inove4us · school</div>
      <h1>Área restrita — conteúdo de posicionamento estratégico</h1>
      <p>
        Esta página exige a zona Administrativo. Sua sessão está autenticada, mas não tem
        permissão para visualizar este material.
      </p>
      {fallback && fallback !== '/acesso' ? (
        <Link to={fallback}>Voltar ao painel</Link>
      ) : (
        <Link to="/acesso">Ir para o acesso</Link>
      )}
    </div>
  )
}

function MarketContent() {
  const rootRef = useRef(null)
  useMarketFonts()
  useRevealOnScroll(rootRef, true)

  useEffect(() => {
    const prev = document.title
    document.title = 'inove4us — Ecossistema | /market'
    return () => {
      document.title = prev
    }
  }, [])

  return (
    <div className="market-page" ref={rootRef}>
      <nav className="market-nav" aria-label="Navegação da hotpage">
        <div className="inner">
          <div className="logo">inove4us</div>
          <div className="links">
            <a className="b2c" href="#b2c">
              Inove4Us · professor
            </a>
            <a className="b2b" href="#b2b">
              school · gestão
            </a>
            <a className="bridge" href="#bridge">
              a ponte
            </a>
          </div>
          <div className="tag">/market</div>
        </div>
      </nav>

      <section className="hero">
        <div className="container">
          <div className="eyebrow reveal">Ecossistema inove4us · posicionamento</div>
          <h1 className="reveal">
            Uma <em>trincheira</em> para o professor. Uma <em>torre de controle</em> para a
            escola.
          </h1>
          <p className="lead reveal">
            Dois produtos, uma só verdade pedagógica: o que o professor executa na ponta é
            exatamente o que a gestão enxerga, audita e evolui no centro.
          </p>

          <div className="split reveal">
            <div className="side b2c">
              <img
                className="brand-logo"
                src="/images/logo-inove.png"
                alt="Inove4Us — ferramenta do professor"
              />
              <div className="kicker">01 — B2C</div>
              <h3>Inove4Us</h3>
              <p className="concept">
                A ferramenta do professor. Remove a carga burocrática das costas do docente
                para que ele foque exclusivamente na execução da aula e na observação dos
                alunos.
              </p>
            </div>
            <div className="side b2b">
              <img
                className="brand-logo"
                src="/images/logo-inove4us-school.png"
                alt="inove4us school — ferramenta da escola"
              />
              <div className="kicker">02 — B2B</div>
              <h3>inove4us school</h3>
              <p className="concept">
                A ferramenta da escola. Governança, compliance jurídico e visão de exceção
                sobre tudo o que acontece em sala — sem tirar autonomia do professor.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="block b2c-block" id="b2c">
        <div className="container">
          <div className="head reveal">
            <img
              className="brand-logo"
              src="/images/logo-inove.png"
              alt="Inove4Us — ferramenta do professor"
            />
            <div className="kicker">Inove4Us — a ferramenta do professor</div>
            <h2>A Trincheira e a Mesa de Operação</h2>
            <p>
              O objetivo é um só: tirar a burocracia do caminho para que o professor foque na
              aula e nos alunos — nunca no preenchimento de formulário.
            </p>
          </div>

          <div className="subhead reveal">Princípios norteadores</div>
          <div className="grid3">
            <div className="card reveal">
              <span className="num">Fricção zero</span>
              <h4>Operação invisível</h4>
              <p>
                A simples movimentação dos cards no Kanban gera o &quot;Diário de Bordo&quot;
                automaticamente. Documentar não é uma tarefa extra — é consequência de
                executar.
              </p>
            </div>
            <div className="card reveal">
              <span className="num">Empatia visual</span>
              <h4>Proteção do espaço do professor</h4>
              <p>
                O ambiente — a &quot;Mesa&quot; — é dele. O design protege esse espaço de
                qualquer sensação de vigilância ou cobrança externa.
              </p>
            </div>
            <div className="card reveal">
              <span className="num">Protagonismo</span>
              <h4>Voz no momento certo</h4>
              <p>
                O professor pode sugerir mudanças na metodologia (Curadoria) exatamente no
                instante em que a aula termina — quando a percepção ainda está viva.
              </p>
            </div>
          </div>

          <div className="subhead reveal">Diferenciais para o professor</div>
          <div className="diff-row">
            <div className="diff reveal">
              <span className="tag">IA</span>
              <h4>Roteiro &quot;mastigado&quot; por IA</h4>
              <p>Um roteiro único, em Markdown, pronto para dar aula — sem montagem manual.</p>
            </div>
            <div className="diff reveal">
              <span className="tag">Inclusão</span>
              <h4>Amparo direto no card</h4>
              <p>
                Adaptações de PEI chegam junto da aula, no próprio card — não em um documento
                separado que ninguém abre.
              </p>
            </div>
            <div className="diff reveal">
              <span className="tag">Comunicação</span>
              <h4>Avisos pinados na mesa</h4>
              <p>
                Comunicação direta da escola, fixada no topo da mesa de trabalho — visível sem
                precisar procurar.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="block b2b-block" id="b2b">
        <div className="container">
          <div className="head reveal">
            <img
              className="brand-logo"
              src="/images/logo-inove4us-school.png"
              alt="inove4us school — ferramenta da escola"
            />
            <div className="kicker">inove4us school — a ferramenta da escola</div>
            <h2>A Torre de Controle e o Radar Pedagógico</h2>
            <p>
              Governança sobre o que acontece em cada sala de aula, sem burocratizar o
              professor — visão de exceção, não vigilância linha a linha.
            </p>
          </div>

          <div className="subhead reveal">Princípios norteadores</div>
          <div className="grid3">
            <div className="card reveal">
              <span className="num">Governança</span>
              <h4>Compliance jurídico by design</h4>
              <p>
                Separação formal AEE/PEI e uma &quot;Máquina do Tempo&quot; — histórico
                imutável, assinaturas com timestamp — que blinda a escola de passivos legais e
                atende exigências do MEC.
              </p>
            </div>
            <div className="card reveal">
              <span className="num">Exceção</span>
              <h4>Gestão pelo que importa</h4>
              <p>
                O Grafo destaca em lilás exatamente as sugestões de curadoria que pedem atenção
                — a gestão vê o desvio, não o volume.
              </p>
            </div>
            <div className="card reveal">
              <span className="num">Disclosure</span>
              <h4>Complexidade sob demanda</h4>
              <p>
                Acordeões colapsados, pílulas de status, filtros poderosos: a informação densa
                fica disponível, mas nunca despejada de uma vez.
              </p>
            </div>
          </div>

          <div className="subhead reveal">Diferenciais para a escola e a gestão</div>
          <div className="diff-row">
            <div className="diff reveal">
              <span className="tag">Espelho</span>
              <h4>Espelhamento absoluto</h4>
              <p>
                O Radar mostra exatamente o mesmo card que o professor vê na mesa — o mesmo{' '}
                <em>TeacherCardPreview</em>, sem tradução nem perda de contexto.
              </p>
            </div>
            <div className="diff reveal">
              <span className="tag">Curadoria</span>
              <h4>Evolução curricular viva</h4>
              <p>
                Curadoria da escola → IA reescreve → novo padrão já disponível no dia seguinte.
                A metodologia da escola nunca fica parada no tempo.
              </p>
            </div>
            <div className="diff reveal">
              <span className="tag">Onboarding</span>
              <h4>Funil financeiro automático</h4>
              <p>
                Webhook Action-Sponge conduz onboarding e cobrança ponta a ponta, sem
                intervenção manual da equipe.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="block bridge-block" id="bridge">
        <div className="container">
          <div className="head reveal">
            <div className="kicker">a ponte entre os dois mundos</div>
            <h2>A Matriz Metodológica Inclusiva</h2>
            <p>
              O maior diferencial do ecossistema: tratar a inclusão como algo vivo, não como um
              PDF arquivado numa gaveta.
            </p>
          </div>

          <div className="matrix reveal">
            <div className="node">
              <div className="lab">Base</div>
              <h4>Metodologia canônica</h4>
            </div>
            <div className="op">×</div>
            <div className="node">
              <div className="lab">Condição</div>
              <h4>Limitação da deficiência</h4>
            </div>
            <div className="op">×</div>
            <div className="node">
              <div className="lab">Indivíduo</div>
              <h4>Barreiras do aluno</h4>
            </div>
            <div className="result">
              <div className="lab">a IA traduz</div>
              <h4>Metodologia de aula prática, na palma da mão do professor</h4>
            </div>
          </div>

          <p className="bridge-para reveal">
            O PEI deixa de ser um documento que se assina e se guarda. Ele{' '}
            <strong>cruza</strong> a metodologia oficial da escola com a condição do aluno e
            com suas barreiras específicas — e o resultado chega pronto para uso, dentro do
            mesmo card que o professor já abre todos os dias.
          </p>
        </div>
      </section>

      <section className="closing">
        <div className="container">
          <div className="eyebrow reveal">inove4us</div>
          <h2 className="reveal">
            Um ecossistema. Duas experiências. Uma só verdade pedagógica.
          </h2>
          <p className="reveal">
            O que acontece na trincheira chega íntegro à torre de controle — e o que a torre de
            controle decide chega íntegro à trincheira.
          </p>
          <div className="dots reveal">
            <span />
            <span />
            <span />
          </div>
        </div>
      </section>

      <footer className="market-footer">
        Proposta visual — hotpage /market · uso interno, gestão inove4us school
      </footer>
    </div>
  )
}

export default function Market() {
  const { authenticated, booting, user } = useAuth()
  const location = useLocation()

  if (booting) {
    return (
      <div className="market-blocked">
        <p>Carregando…</p>
      </div>
    )
  }

  if (!authenticated) {
    const next = `${location.pathname}${location.search}`
    const q = next && next !== '/acesso' ? `?next=${encodeURIComponent(next)}` : ''
    return <Navigate to={`/acesso${q}`} replace />
  }

  if (!hasAnyZona(user?.zonas || [], [ZONAS.administrativo])) {
    return <MarketBlocked />
  }

  return <MarketContent />
}
