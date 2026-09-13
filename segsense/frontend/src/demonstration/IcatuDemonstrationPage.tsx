import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import SegSenseLogo from '../components/SegSenseLogo';
import RouteFocus from '../components/RouteFocus';
import { apiBaseUrl } from '../api/systemInfo';
import {
  DemonstrationAbsenceError,
  fetchPublishedDemonstration,
  type PublishedDemonstration,
} from '../api/demonstration';
import './demonstration.css';

const DISCLAIMER =
  'Demonstração conceitual. Não é uma oferta de seguro, integração oficial ou serviço da Icatu.';

export default function IcatuDemonstrationPage() {
  const [editorial, setEditorial] = useState<PublishedDemonstration | null>(null);
  const [editorialState, setEditorialState] = useState<'idle' | 'loading' | 'absent' | 'unavailable'>(
    'loading',
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchPublishedDemonstration(apiBaseUrl(), 'icatu-demonstracao', controller.signal)
      .then((payload) => {
        setEditorial(payload);
        setEditorialState(payload ? 'idle' : 'absent');
      })
      .catch((error: unknown) => {
        if (error instanceof DemonstrationAbsenceError) {
          setEditorialState('unavailable');
          return;
        }
        setEditorialState('unavailable');
      });
    return () => {
      controller.abort();
    };
  }, []);

  return (
    <div className="demo-page">
      <RouteFocus />
      <a className="skip-link" href="#conteudo">
        Ir para o conteúdo
      </a>
      <header className="demo-banner" role="banner">
        <p className="demo-disclaimer">{DISCLAIMER}</p>
      </header>
      <header className="demo-top">
        <Link to="/" className="demo-home-link">
          <SegSenseLogo surface="public" />
        </Link>
        <p className="demo-kicker">Cenário demonstrativo não oficial</p>
      </header>
      <main id="conteudo" className="demo-main" tabIndex={-1}>
        <section className="demo-hero" aria-labelledby="demo-title">
          <p className="demo-eyebrow">SegSense + Icatu Seguros — cenário demonstrativo não oficial</p>
          <h1 id="demo-title">Como um conteúdo vira um convite compreensível</h1>
          <p className="demo-lede">
            Fonte contextual, convite com finalidade e manifestação local. A Icatu é provedora
            potencial de um cenário futuro, não parceira certificada nem executor selecionado.
          </p>
          <a className="button-primary demo-cta" href="#mecanismo">
            Explorar como funcionaria
          </a>
          <p className="demo-footnote">{DISCLAIMER}</p>
        </section>

        <section id="origem" className="demo-card">
          <h2>Ponto de origem</h2>
          <p className="demo-illustration-label">Ilustração. Texto fictício e secundário.</p>
          <article className="demo-article">
            <p className="demo-kicker">Artigo digital ilustrativo</p>
            <h3>Continuidade financeira da família diante de um imprevisto</h3>
            <p>
              Um texto genérico pode despertar a pergunta sobre proteção. Ele descreve um tema
              editorial, não o perfil do visitante, e não indica produto, cobertura, preço ou
              possibilidade de contratação da Icatu.
            </p>
            <p>
              <a className="demo-inert-link" href="#mecanismo">
                Continuar no SegSense (não cria sessão)
              </a>
            </p>
          </article>
        </section>

        <section id="mecanismo" className="demo-card">
          <h2>O mecanismo, em três passos</h2>
          <ol className="demo-steps">
            <li>
              <span className="demo-badge demo-badge--live">Já operante</span>
              Fonte contextual: publicador, oportunidade aprovada e link.
            </li>
            <li>
              <span className="demo-badge demo-badge--live">Já operante</span>
              Convite compreensível: aviso de finalidade versionado.
            </li>
            <li>
              <span className="demo-badge demo-badge--live">Já operante</span>
              Manifestação local, sem envio a Spider, Icatu ou mock.
            </li>
          </ol>
        </section>

        <section className="demo-card" aria-labelledby="fronteiras-title">
          <h2 id="fronteiras-title">Fronteiras futuras, separadas</h2>
          <FrontierDiagram />
          <ul className="demo-frontiers">
            <li>
              <span className="demo-badge demo-badge--blocked">Esta página não chama a Spider</span>
              Esta demonstração Icatu permanece editorial e local. O Satellite Contract V1 existe
              na Spider para o MVP integrado sintético; esta rota não o utiliza. Contrato comercial
              Icatu continua ausente.
            </li>
            <li>
              <span className="demo-badge demo-badge--future">Hipótese futura</span>
              Um provedor autorizado poderia substituir o Test Double. Esta página não chama o
              mock. A Icatu real não recebeu dados.
            </li>
          </ul>
        </section>

        <section className="demo-card" aria-labelledby="editorial-title">
          <h2 id="editorial-title">Cenário editorial publicado</h2>
          {editorialState === 'loading' ? (
            <p>Verificando se há conteúdo editorial publicado…</p>
          ) : null}
          {editorialState === 'absent' ? (
            <p>Não há história administrada publicada. A narrativa institucional acima permanece.</p>
          ) : null}
          {editorialState === 'unavailable' ? (
            <p>Conteúdo editorial adicional indisponível.</p>
          ) : null}
          {editorial ? (
            <div>
              <p>
                Versão {editorial.revisionNumber}, publicada em {editorial.publishedAt}.
              </p>
              <p>{editorial.scopeNote}</p>
              {editorial.blocks.map((block) => (
                <article key={block.position}>
                  <h3>{block.title}</h3>
                  <p>{block.body}</p>
                </article>
              ))}
              {editorial.references.length > 0 ? (
                <ul>
                  {editorial.references.map((reference) => (
                    <li key={reference.url}>
                      <a href={reference.url} rel="noopener noreferrer" target="_blank">
                        Fonte pública consultada em {reference.consultedOn}
                      </a>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}

function FrontierDiagram() {
  return (
    <figure className="demo-diagram">
      <svg viewBox="0 0 640 160" role="img" aria-labelledby="demo-diagram-title">
        <title id="demo-diagram-title">Três fronteiras distintas nesta página Icatu</title>
        <rect x="8" y="24" width="180" height="112" rx="16" className="demo-diagram-live" />
        <text x="98" y="70" textAnchor="middle">
          SegSense
        </text>
        <text x="98" y="94" textAnchor="middle">
          operante
        </text>
        <rect x="230" y="24" width="180" height="112" rx="16" className="demo-diagram-blocked" />
        <text x="320" y="70" textAnchor="middle">
          Spider
        </text>
        <text x="320" y="94" textAnchor="middle">
          não usada aqui
        </text>
        <rect x="452" y="24" width="180" height="112" rx="16" className="demo-diagram-future" />
        <text x="542" y="70" textAnchor="middle">
          Mock
        </text>
        <text x="542" y="94" textAnchor="middle">
          não usado aqui
        </text>
      </svg>
      <figcaption>Ilustração das fronteiras. Não representa tráfego real.</figcaption>
    </figure>
  );
}
