import { Link } from 'react-router-dom';
import SegSenseLogo from '../components/SegSenseLogo';
import RouteFocus from '../components/RouteFocus';
import './home.css';

export default function SegSenseHomePage() {
  return (
    <div className="home-page">
      <RouteFocus />
      <a className="skip-link" href="#conteudo">
        Ir para o conteúdo
      </a>
      <header className="home-top">
        <SegSenseLogo surface="public" />
        <nav className="home-nav" aria-label="Principal">
          <a href="#capacidades">O que já opera</a>
          <a href="#cooperacao">Com quem coopera</a>
          <Link to="/demonstracao/icatu">Demonstração Icatu (não oficial)</Link>
          <Link to="/demonstracao/mvp-integrado">MVP integrado sintético</Link>
        </nav>
      </header>
      <main id="conteudo" className="home-main" tabIndex={-1}>
        <section className="home-hero" aria-labelledby="home-title">
          <p className="home-kicker">Posicionamento do SegSense</p>
          <h1 id="home-title">Do contexto percebido à jornada de proteção</h1>
          <p className="home-lede">
            SegSense distribui oportunidades contextualizadas e compõe jornadas explicáveis de
            proteção, cooperando com seguradoras e intermediários autorizados.
          </p>
          <p className="home-gain">
            Hoje o ganho é ligar um conteúdo ou canal a um convite governado, com finalidade clara
            e manifestação local. Isso ainda não é taxa de conversão comprovada, recomendação
            automática nem criação de seguro.
          </p>
          <div className="home-actions">
            <a className="button-primary" href="#capacidades">
              Ver o que já opera
            </a>
            <Link className="button-secondary" to="/demonstracao/mvp-integrado">
              Ver MVP integrado sintético
            </Link>
            <Link className="button-secondary" to="/demonstracao/icatu">
              Ver cenário demonstrativo Icatu
            </Link>
          </div>
          <ul className="home-now-later">
            <li>
              <span className="demo-badge demo-badge--live">Hoje</span>
              Contexto editorial verificável, governança da oportunidade e convite local.
            </li>
            <li>
              <span className="demo-badge demo-badge--future">Depois de contratos</span>
              Composição de jornadas com catálogos, regras e participantes autorizados.
            </li>
          </ul>
        </section>

        <section id="capacidades" className="home-grid" aria-labelledby="capacidades-title">
          <h2 id="capacidades-title">Três capacidades distintas</h2>
          <article className="home-card">
            <p className="demo-badge demo-badge--live">Hoje</p>
            <h3>Origem e contexto editorial</h3>
            <p>
              Publicador, canal e oportunidade versionada descrevem de onde a pessoa chegou. Esse
              contexto é editorial e verificável. Não é o perfil do visitante.
            </p>
          </article>
          <article className="home-card">
            <p className="demo-badge demo-badge--live">Hoje</p>
            <h3>Governança, finalidade e manifestação</h3>
            <p>
              A oportunidade só vira convite depois de aprovação. O aviso de finalidade é
              versionado. A manifestação fica no SegSense e não é enviada a seguradora.
            </p>
          </article>
          <article className="home-card">
            <p className="demo-badge demo-badge--future">Depois de contratos</p>
            <h3>Composição explicável</h3>
            <p>
              Combinar jornadas e serviços autorizados depende de catálogos, regras, participantes
              e contratos. Isso ainda não opera.
            </p>
          </article>
        </section>

        <section id="cooperacao" className="home-card" aria-labelledby="cooperacao-title">
          <h2 id="cooperacao-title">Com quem o SegSense coopera</h2>
          <p>
            Seguradoras e intermediários autorizados decidem cobertura, preço, subscrição, emissão
            e atendimento. O SegSense organiza o contexto, o convite e a evidência local. Cada um
            preserva o próprio papel.
          </p>
        </section>

        <section className="home-card" aria-labelledby="contrato-title">
          <h2 id="contrato-title">O que ainda depende de contrato</h2>
          <p>
            Catálogo de API autorizado, instrumento comercial e regulatório, homologação e textos
            jurídicos. Sem isso não há cotação, elegibilidade, emissão nem produto novo no ar.
          </p>
        </section>

        <section className="home-card" aria-labelledby="produto-title">
          <h2 id="produto-title">Como um produto novo poderia surgir</h2>
          <p>
            Um produto securitário inédito só nasce em co-desenvolvimento com a seguradora:
            atuária, jurídico, subscrição, condições e registro ou aprovação cabíveis. O SegSense
            pode revelar demanda contextual e apresentar uma experiência composta. Não cria
            cobertura, prêmio ou apólice por conta própria.
          </p>
          <ul className="home-levels">
            <li>Contextualizar uma oferta existente — hipótese de apresentação, não contratação.</li>
            <li>Configurar produto dentro de regras autorizadas — futuro, com catálogo real.</li>
            <li>Compor experiências com contratos distintos — cada um com aceite próprio.</li>
            <li>Co-desenvolver produto verdadeiramente novo — decisão da seguradora, não da plataforma.</li>
          </ul>
        </section>

        <section id="limites-tecnicos" className="home-card home-card--technical" aria-labelledby="limites-title">
          <h2 id="limites-title">Limites técnicos desta etapa</h2>
          <p>
            O SegSense é uma aplicação independente. O Satellite Contract V1 existe na Spider em
            local-demo (DEMO ONLY) e é usado pela rota do MVP integrado sintético. Esta página de
            posicionamento não dispara essa chamada. Não é cotação, produção nem integração Icatu.
          </p>
        </section>
      </main>
      <footer className="home-foot">
        <p>
          A área administrativa existe em outro endereço e continua indisponível sem identidade.
          Esta página não pede login nem coleta dados.
        </p>
      </footer>
    </div>
  );
}
