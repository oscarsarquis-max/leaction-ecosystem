import type { DemoJourneyProjection } from '../api/demoProtectionJourney';
import { isConfirmedPreProposal } from '../api/demoProtectionJourney';
import { humanJourneyStatus } from './humanJourneyStatus';

function present(value: string | null | undefined): value is string {
  return Boolean(value) && value !== 'null';
}

export default function SimulationEvidencePanel({
  projection,
  errorMessage,
  idempotencyKey,
  attemptSerial,
}: {
  projection: DemoJourneyProjection | null;
  errorMessage: string | null;
  idempotencyKey: string;
  attemptSerial: number;
}) {
  const origin = projection?.originProvenance;
  const channel = origin?.channel ?? origin?.attributes?.channel;
  const items = projection?.items ?? [];
  const pending = projection?.pendingForBroker ?? [];
  const confirmed = projection ? isConfirmedPreProposal(projection) : false;

  return (
    <section className="demo-card mvp-evidence" aria-labelledby="evidence-title" data-attempt={attemptSerial}>
      <h2 id="evidence-title">Evidências desta simulação</h2>
      <p className="mvp-evidence-note">
        Somente a interação corrente. A ordem dos cartões não é uma cronologia auditável. Cartões
        sem evidência canônica desta resposta não aparecem.
      </p>

      <article>
        <h3>Tentativa corrente</h3>
        <p>Chave de idempotência gerada neste navegador: {idempotencyKey}</p>
        {projection ? (
          <>
            <p>Resultado confirmado na resposta do SegSense: {humanJourneyStatus(projection.status)}</p>
            {present(projection.generatedAt) ? (
              <p>
                Registrado no SegSense em {projection.generatedAt} (persistência do BFF; não é o
                horário de recebimento na Spider).
              </p>
            ) : null}
            {present(projection.messageCreatedAt) ? (
              <p>Mensagem criada em {projection.messageCreatedAt} (UTC da interação corrente).</p>
            ) : null}
            {present(projection.objectiveDeclaredAt) ? (
              <p>
                Intenção confirmada em {projection.objectiveDeclaredAt} (UTC da confirmação efetiva).
              </p>
            ) : null}
            {present(projection.correlationId) ? <p>Correlação desta resposta: {projection.correlationId}</p> : null}
          </>
        ) : (
          <p>
            {errorMessage ?? 'A solicitação foi enviada; o SegSense não devolveu uma projeção.'} Sem
            decisão da Spider nesta tentativa.
          </p>
        )}
      </article>

      {projection && (channel || origin?.sourceType) ? (
        <article>
          <h3>Proveniência do contexto</h3>
          <p>
            A Spider validou as contribuições estruturadas desta interação. Não verificou a vida real
            do visitante e não interpretou o texto original.
          </p>
          <p>
            {origin?.sourceType ?? channel}
            {origin?.purpose ? ` · ${origin.purpose}` : ''}
          </p>
          {present(origin?.sourceId) ? <p>Origem principal: {origin.sourceId}</p> : null}
          {present(origin?.sourceTimestamp) && origin.sourceType === 'SATELLITE_GOVERNED' ? (
            <p>
              Timestamp editorial da fonte: {origin.sourceTimestamp} (publicação imutável do registro,
              não o horário desta mensagem).
            </p>
          ) : null}
          {present(projection.editorialSourceTimestamp) ? (
            <p>Publicação da fonte editorial: {projection.editorialSourceTimestamp}</p>
          ) : null}
        </article>
      ) : null}

      {projection && present(projection.declaredObjective) ? (
        <article>
          <h3>Objetivo enviado</h3>
          <p>Valor efetivamente registrado pelo BFF nesta resposta: {projection.declaredObjective}</p>
        </article>
      ) : null}

      {projection && present(projection.spiderDecisionId) && present(projection.explanation) ? (
        <article>
          <h3>Decisão da Spider</h3>
          <p>{projection.explanation}</p>
          <p>Identificador da decisão: {projection.spiderDecisionId}</p>
        </article>
      ) : null}

      {projection && confirmed && present(projection.capabilityId) && present(projection.providerRequestId) ? (
        <article>
          <h3>Capability despachada</h3>
          <p>
            Evidência canônica nesta resposta: {projection.capabilityId} · pedido{' '}
            {projection.providerRequestId}
          </p>
        </article>
      ) : null}

      {projection && confirmed && present(projection.mockResultId) ? (
        <article>
          <h3>Retorno do Test Double</h3>
          <p>
            Itens ilustrativos do Test Double (não são produtos disponíveis nem catálogo Icatu).
            Referência: {projection.mockResultId}
          </p>
          {present(projection.mockOrigin) ? <p>Origem: {projection.mockOrigin}</p> : null}
          <p>
            {items.length} item(ns) ilustrativos nesta resposta. Os títulos visíveis estão no bloco
            Possibilidades; aqui só a referência técnica.
          </p>
          {pending.length > 0 ? (
            <div>
              <p>Pendências para avaliação humana</p>
              <ul>
                {pending.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </article>
      ) : null}

      <aside>
        <h3>Fora desta demonstração</h3>
        <p>
          Intent Contract pleno, CTX-004, Eligibility Gate, plano/execução do Data Plane, callback,
          IdP, seguradora autorizada e cotação vinculante não existem nesta fatia. Não há{' '}
          <code>planId</code> nem <code>executionId</code>.
        </p>
      </aside>
    </section>
  );
}
