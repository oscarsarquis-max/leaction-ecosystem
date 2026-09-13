import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import SegSenseLogo from '../components/SegSenseLogo';
import RouteFocus from '../components/RouteFocus';
import { apiBaseUrl } from '../api/systemInfo';
import {
  isConfirmedPreProposal,
  submitDemoProtectionJourney,
  type DemoJourneyProjection,
} from '../api/demoProtectionJourney';
import { ApiClientError } from '../api/errors';
import '../demonstration/demonstration.css';
import './integrated-mvp.css';

const WATERMARK =
  'DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO';
const ALLOWED = 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS';

export default function IntegratedMvpPage() {
  const [confirmed, setConfirmed] = useState(false);
  const [phase, setPhase] = useState<'form' | 'awaiting' | 'done'>('form');
  const [result, setResult] = useState<DemoJourneyProjection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);

  async function submit(event: { preventDefault: () => void }) {
    event.preventDefault();
    if (!confirmed) {
      setError('Confirme que os dados são sintéticos e que isto não é cotação.');
      return;
    }
    setError(null);
    setResult(null);
    setPhase('awaiting');
    try {
      const projection = await submitDemoProtectionJourney(apiBaseUrl(), ALLOWED, idempotencyKey);
      setResult(projection);
      setPhase('done');
    } catch (caught) {
      setResult(null);
      setPhase('done');
      if (caught instanceof ApiClientError) {
        setError(caught.message);
        return;
      }
      setError('A jornada integrada está indisponível. A UI não inventa pré-proposta.');
    }
  }

  const preProposal = result && isConfirmedPreProposal(result) ? result : null;

  return (
    <div className="demo-page mvp-page">
      <RouteFocus />
      <a className="skip-link" href="#conteudo">
        Ir para o conteúdo
      </a>
      <header className="demo-banner mvp-watermark" role="banner">
        <p className="demo-disclaimer">{WATERMARK}</p>
      </header>
      <header className="demo-top mvp-top">
        <Link to="/" aria-label="SegSense — voltar à apresentação pública">
          <SegSenseLogo surface="public" />
        </Link>
        <nav className="mvp-nav">
          <Link to="/">Apresentação SegSense</Link>
          {' · '}
          <Link to="/demonstracao/icatu">Cenário Icatu (não oficial, separado)</Link>
        </nav>
      </header>
      <main id="conteudo" className="demo-main mvp-main" tabIndex={-1}>
        <section className="demo-card mvp-hero" aria-labelledby="mvp-title">
          <p className="demo-badge demo-badge--live">MVP integrado sintético</p>
          {phase === 'form' && !result ? (
            <p className="mvp-kind">Configuração local — ainda não houve envio nesta página.</p>
          ) : null}
          <h1 id="mvp-title">Continuidade financeira da família — cenário demonstrativo</h1>
          <p className="mvp-promise">
            Depois do envio, esta tela só mostra decisão, capability e itens se a resposta canônica
            da Spider os confirmar. Dados do cenário são sintéticos. Não é cotação, proposta Icatu
            nem produção.
          </p>
        </section>

        <form className="demo-card mvp-action" onSubmit={(event) => { void submit(event); }} aria-labelledby="objective-title">
          <h2 id="objective-title">Próximo passo</h2>
          <p>
            Objetivo desta reunião: entender opções ilustrativas de proteção familiar. SegSense,
            Spider e o mock permanecem runtimes distintos.
            {phase === 'form' && !result ? ' O envio ainda não ocorreu.' : ''}
          </p>
          <label className="mvp-confirm">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => {
                setConfirmed(event.target.checked);
              }}
            />
            Confirmo que não informei dados pessoais e que o resultado não é cotação nem proposta
            de contratação.
          </label>
          <button className="button-primary" type="submit" disabled={phase === 'awaiting'}>
            Enviar à Spider
          </button>
        </form>

        {phase === 'awaiting' ? (
          <p className="demo-card mvp-awaiting" aria-live="polite">
            Aguardando resposta da Spider…
          </p>
        ) : null}
        {error ? (
          <p className="demo-card" role="alert">
            {error}
          </p>
        ) : null}
        {preProposal ? <PreProposal projection={preProposal} /> : null}
        {result && !preProposal ? (
          <p className="demo-card" role="alert">
            {humanStatus(result.status)}. {result.explanation}
          </p>
        ) : null}

        <details className="demo-card mvp-secondary">
          <summary>Peça editorial e limites desta demonstração</summary>
          <article>
            <h2>Quando um imprevisto altera o orçamento familiar</h2>
            <p>
              Famílias organizam a vida em torno da renda de quem trabalha. Um evento inesperado
              pode interromper essa continuidade. Esta página não descreve um cliente real.
            </p>
          </article>
          <p>
            Origem esperada após o envio: publicação editorial sintética do SegSense, versão
            governada no servidor. O navegador não envia URL, token nem texto livre como prova de
            contexto. Nenhum dado segue à Icatu.
          </p>
        </details>
      </main>
    </div>
  );
}

function PreProposal({ projection }: { projection: DemoJourneyProjection }) {
  const items = projection.items ?? [];
  const pending = projection.pendingForBroker ?? [];
  const origin = projection.originProvenance;
  return (
    <section className="demo-card mvp-preproposal" aria-labelledby="preproposal-title">
      <p className="mvp-watermark">{projection.watermark || WATERMARK}</p>
      <h2 id="preproposal-title">Pré-proposta demonstrativa</h2>
      <p>Marca: SegSense. Isto não é proposta Icatu, cotação nem apólice.</p>
      <dl className="mvp-conversation">
        {origin?.channel || origin?.sourceType ? (
          <div>
            <dt>Contexto e finalidade confirmados pela Spider</dt>
            <dd>
              {origin?.channel ?? origin?.sourceType}
              {origin?.purpose ? ` · ${origin.purpose}` : ''}
            </dd>
          </div>
        ) : null}
        <div>
          <dt>Objetivo declarado neste envio</dt>
          <dd>Entender opções ilustrativas de proteção familiar</dd>
        </div>
        {projection.explanation ? (
          <div>
            <dt>Explicação devolvida pela Spider</dt>
            <dd>{projection.explanation}</dd>
          </div>
        ) : null}
      </dl>
      {projection.mockResultId && items.length > 0 ? (
        <div>
          <h3>Itens ilustrativos confirmados pelo retorno do provedor</h3>
          <ul>
            {items.map((item) => (
              <li key={item.code}>
                {item.title} {item.notOfferable ? '(não ofertável)' : ''}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {projection.mockResultId && pending.length > 0 ? (
        <div>
          <h3>Pendências para avaliação humana</h3>
          <ul>
            {pending.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {projection.mockOrigin ? <p>Origem dos itens: {projection.mockOrigin}</p> : null}
      <details>
        <summary>IDs de correlação e prova técnica</summary>
        <dl>
          <div>
            <dt>Identificador SegSense</dt>
            <dd>{projection.id}</dd>
          </div>
          {projection.generatedAt ? (
            <div>
              <dt>Registrado em</dt>
              <dd>{projection.generatedAt}</dd>
            </div>
          ) : null}
          {projection.spiderDecisionId ? (
            <div>
              <dt>Decisão Spider</dt>
              <dd>{projection.spiderDecisionId}</dd>
            </div>
          ) : null}
          <div>
            <dt>Correlação</dt>
            <dd>{projection.correlationId}</dd>
          </div>
          {projection.mockResultId ? (
            <div>
              <dt>Referência do provedor</dt>
              <dd>{projection.mockResultId}</dd>
            </div>
          ) : null}
          {projection.capabilityId ? (
            <div>
              <dt>Capability despachada</dt>
              <dd>{projection.capabilityId}</dd>
            </div>
          ) : null}
          {projection.providerRequestId ? (
            <div>
              <dt>Pedido ao provedor</dt>
              <dd>{projection.providerRequestId}</dd>
            </div>
          ) : null}
          {projection.satelliteId && projection.satelliteRole && projection.satelliteContractVersion ? (
            <div>
              <dt>Satélite usado neste envio</dt>
              <dd>
                {projection.satelliteId} · {projection.satelliteRole} · contrato {projection.satelliteContractVersion}
              </dd>
            </div>
          ) : null}
          {projection.spiderPath ? (
            <div>
              <dt>Caminho técnico</dt>
              <dd>{projection.spiderPath}</dd>
            </div>
          ) : null}
        </dl>
      </details>
      <button className="button-secondary" type="button" onClick={() => { window.print(); }}>
        Imprimir esta demonstração
      </button>
    </section>
  );
}

function humanStatus(status: string): string {
  switch (status) {
    case 'PRE_PROPOSAL_AVAILABLE':
      return 'Pré-proposta demonstrativa disponível';
    case 'REJECTED':
      return 'Objetivo não permitido';
    case 'MOCK_UNAVAILABLE':
      return 'Provedor ilustrativo indisponível';
    case 'SPIDER_UNAVAILABLE':
      return 'Spider indisponível';
    case 'INCOMPLETE_CANONICAL':
      return 'A resposta da Spider não confirmou decisão e retorno de provedor';
    default:
      return status;
  }
}
