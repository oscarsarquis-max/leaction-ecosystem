import { Link, useParams } from 'react-router-dom';
import SegSenseLogo from '../components/SegSenseLogo';
import RouteFocus from '../components/RouteFocus';
import {
  FAMILY_SOURCE_PATH,
  FIRES_SOURCE_PATH,
  INCOME_SOURCE_PATH,
  REVOKED_SOURCE_PATH,
} from './demoJourneyInputs';
import '../demonstration/demonstration.css';
import './integrated-mvp.css';

const PAGES: Record<
  string,
  { title: string; source: string; version: string; excerpt: string; revoked?: boolean }
> = {
  'continuidade-familiar': {
    title: 'Continuidade financeira da família (sintético)',
    source: 'Registro editorial SegSense',
    version: 'demo-editorial-v1',
    excerpt:
      'Famílias organizam a vida em torno da renda de quem trabalha. Um evento inesperado pode interromper essa continuidade. Texto sintético autorizado; não é artigo integral.',
  },
  'interrupcao-renda': {
    title: 'Interrupção da renda do trabalho (sintético)',
    source: 'Registro editorial SegSense',
    version: 'demo-income-v1',
    excerpt:
      'Se o trabalho para, a renda mensal pode cessar enquanto contas continuam. Texto sintético autorizado; não é artigo integral.',
  },
  'proximidade-incendios': {
    title: 'Incêndios próximos de uma região hipotética (sintético)',
    source: 'Registro editorial SegSense',
    version: 'demo-fires-v1',
    excerpt:
      'Em uma região hipotética, relatos descrevem incêndios em áreas próximas. O texto é editorial e sintético. Não prova que um imóvel específico está exposto, não autoriza inferir endereço e não agrava preço.',
  },
  revogada: {
    title: 'Fonte sintética revogada',
    source: 'Registro editorial SegSense',
    version: 'demo-revoked-v1',
    excerpt: 'Esta fonte foi revogada e não pode originar contexto.',
    revoked: true,
  },
};

export default function GovernedSourcePage() {
  const { slug } = useParams();
  const page = slug ? PAGES[slug] : undefined;
  return (
    <div className="demo-page mvp-page">
      <RouteFocus />
      <header className="demo-banner mvp-watermark" role="banner">
        <p className="demo-disclaimer">
          DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO
        </p>
      </header>
      <header className="demo-top mvp-top">
        <Link to="/" aria-label="Voltar à apresentação">
          <SegSenseLogo surface="public" />
        </Link>
        <nav className="mvp-nav">
          <Link to="/demonstracao/mvp-integrado">Voltar à jornada</Link>
        </nav>
      </header>
      <main className="demo-main mvp-main" tabIndex={-1}>
        {page ? (
          <article className="demo-card">
            {page.revoked ? <p className="demo-badge">Fonte revogada</p> : <p className="demo-badge">Fonte governada sintética</p>}
            <h1>{page.title}</h1>
            <p>
              {page.source} · versão {page.version}
            </p>
            <p>{page.excerpt}</p>
            <p>Isto não é artigo integral, produto Icatu nem prova de que o visitante se encaixa na situação.</p>
          </article>
        ) : (
          <p className="demo-card" role="alert">
            Fonte não encontrada. Use {FAMILY_SOURCE_PATH}, {INCOME_SOURCE_PATH}, {FIRES_SOURCE_PATH} ou {REVOKED_SOURCE_PATH}.
          </p>
        )}
      </main>
    </div>
  );
}
