import { useRef, useState } from "react";
import {
  INTEGRATION_CRITERIA,
  INTEGRATION_MODES,
  SYSTEM_PORTS,
} from "../content.js";
import {
  EvidencePanel,
  ExpandableDetail,
  FlowNode,
  SectionEyebrow,
  SectionHeading,
  StatusIndicator,
} from "../primitives.jsx";

const KIND_EYEBROW = {
  business: "Negócio",
  integration: "Integração",
  technology: "Tecnologia",
};

const SERVICENOW_CHAIN = [
  "CREATE_REVIEW_CASE",
  "Capability Resolver",
  "ServiceNow Route",
  "ServiceNow Adapter",
  "ServiceNow",
];

function StageLane({ nodes, modeId, selectedDetail, onSelect, testId }) {
  return (
    <ol className="sx-istage-lane" data-testid={testId}>
      {nodes.map((node, index) => (
        <li key={node.anchor || `${modeId}-${node.id}`} className={node.anchor ? "is-anchor" : "is-mid"}>
          {index > 0 ? (
            <span className="sx-down" aria-hidden="true">
              ↓
            </span>
          ) : null}
          <FlowNode
            kind={node.kind}
            interactive={Boolean(node.detail)}
            selected={selectedDetail === node.detail}
            status={KIND_EYEBROW[node.kind]}
            onClick={node.detail ? () => onSelect(node.detail) : undefined}
            testId={node.detail ? `integration-node-${node.detail}` : undefined}
          >
            {node.label}
          </FlowNode>
        </li>
      ))}
    </ol>
  );
}

function CapabilityDetail() {
  return (
    <EvidencePanel label="Business Capability">
      <div data-testid="integration-detail">
        <h3>CHECK_CUSTOMER_REGISTRATION</h3>
        <p>
          <b>Significado.</b> Verificar cadastro do cliente.
        </p>
        <p>
          <b>O que ela não determina.</b> Qual sistema será utilizado.
        </p>
        <p>
          <b>Possíveis executores.</b> API corporativa, sistema cadastral, legado, ServiceNow ou
          outro executor elegível.
        </p>
        <p>A capability descreve a necessidade. O Resolver determina a tecnologia.</p>
      </div>
    </EvidencePanel>
  );
}

function ResolverDetail() {
  return (
    <EvidencePanel label="Capability Resolver">
      <div data-testid="integration-detail">
        <p>
          <b>Entrada.</b> Business Capability requerida pelo Execution Plan.
        </p>
        <p>
          <b>Responsabilidade.</b> Encontrar uma Route disponível para execução.
        </p>
        <p>
          <b>Saída.</b> Route / Adapter / Target.
        </p>
        <p>
          <b>Importante.</b> A versão atual resolve disponibilidade e rotas conforme o catálogo
          existente. Custo e compliance ainda não participam do algoritmo.
        </p>
      </div>
    </EvidencePanel>
  );
}

function ServiceNowDetail({ criterionId, onCriterion }) {
  const criterion = INTEGRATION_CRITERIA.find((item) => item.id === criterionId);
  return (
    <EvidencePanel label="Exemplo ServiceNow">
      <div data-testid="integration-detail">
        <p className="sx-sn-badges">
          <StatusIndicator tone="prepared">Proposta de integração</StatusIndicator>
          <StatusIndicator tone="future">Não implementada</StatusIndicator>
        </p>
        <ol className="sx-istage-example">
          {SERVICENOW_CHAIN.map((step, index) => (
            <li key={step}>
              <b>{step}</b>
              {index < SERVICENOW_CHAIN.length - 1 ? (
                <span className="sx-down" aria-hidden="true">
                  ↓
                </span>
              ) : null}
            </li>
          ))}
        </ol>
        <p>
          Neste modelo, ServiceNow atua como executor de uma Business Capability. O Spider
          preserva contexto, planejamento e autoridade canônica de decisão.
        </p>
        <p className="sx-label">Antes de uma integração real</p>
        <p className="sx-copy">Uma futura decisão de executor deverá considerar:</p>
        <div className="sx-criteria" data-testid="integration-criteria">
          {INTEGRATION_CRITERIA.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`sx-criterion${criterionId === item.id ? " is-on" : ""}`}
              aria-pressed={criterionId === item.id}
              onClick={() => onCriterion(item.id === criterionId ? null : item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        {criterion ? <p className="sx-criterion-text">{criterion.text}</p> : null}
        <p className="sx-copy">Critérios arquiteturais — não implementados no Resolver atual.</p>
        <p className="sx-copy">
          <b>Evolução em estudo:</b> formalização de uma etapa de elegibilidade anterior à
          resolução.
        </p>
        <p className="sx-makebuy" data-testid="integration-makebuy">
          <span>Make — possuir o diferencial.</span>
          <span>Buy — reutilizar commodity.</span>
          <strong>Integrate — usar o melhor executor preservando o Control Plane.</strong>
        </p>
      </div>
    </EvidencePanel>
  );
}

export default function IntegrationChapter() {
  const [modeId, setModeId] = useState("limited");
  const [detail, setDetail] = useState(null);
  const [criterionId, setCriterionId] = useState(null);
  const modeTabs = useRef([]);
  const mode = INTEGRATION_MODES.find((item) => item.id === modeId) ?? INTEGRATION_MODES[1];

  const selectMode = (id) => {
    setModeId(id);
    const index = INTEGRATION_MODES.findIndex((item) => item.id === id);
    modeTabs.current[index]?.focus();
  };

  const onModeKey = (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const index = INTEGRATION_MODES.findIndex((item) => item.id === modeId);
    const delta = event.key === "ArrowRight" ? 1 : INTEGRATION_MODES.length - 1;
    selectMode(INTEGRATION_MODES[(index + delta) % INTEGRATION_MODES.length].id);
  };

  const selectDetail = (next) => {
    setDetail((current) => (current === next ? null : next));
    if (next !== "servicenow") setCriterionId(null);
  };

  return (
    <section className="sx-chapter" id="integracao" data-testid="hub-integration">
      <div className="sx-container">
        <SectionEyebrow>06 — Integração</SectionEyebrow>
        <SectionHeading>Integração sem ruptura.</SectionHeading>
        <p className="sx-intro">
          O Spider preserva sua arquitetura mesmo quando o ambiente possui sistemas com diferentes
          níveis de modernização. A camada de integração absorve as diferenças tecnológicas.
        </p>

        <div
          className="sx-segment"
          role="tablist"
          aria-label="Cenário de integração"
          data-testid="integration-mode"
          onKeyDown={onModeKey}
        >
          {INTEGRATION_MODES.map((item, index) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={modeId === item.id}
              className={`sx-segment-btn${modeId === item.id ? " is-on" : ""}`}
              ref={(node) => {
                modeTabs.current[index] = node;
              }}
              tabIndex={modeId === item.id ? 0 : -1}
              onClick={() => selectMode(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="sx-istage" data-testid="integration-stage">
          <header className="sx-istage-head-in">
            <p className="sx-istage-title">Como o sistema chega ao Spider</p>
            <p className="sx-label">Perspectiva de integração</p>
            <div
              className="sx-comm-strip"
              title="A estratégia de integração depende da capacidade real do sistema; os protocolos não representam o mesmo nível de aderência arquitetural."
            >
              <p className="sx-label">Formas de comunicação que podem existir no ambiente</p>
              <ul className="sx-comm-chips">
                {SYSTEM_PORTS.map((port) => (
                  <li key={port}>{port}</li>
                ))}
              </ul>
              <p className="sx-comm-hint">
                A estratégia de integração depende da capacidade real do sistema; os protocolos
                não representam o mesmo nível de aderência arquitetural.
              </p>
            </div>
          </header>

          <header className="sx-istage-head-out">
            <p className="sx-istage-title">Como o Spider chega ao sistema</p>
            <p className="sx-label">Perspectiva de execução</p>
          </header>

          <div className="sx-istage-in">
            <StageLane
              nodes={mode.systemSide}
              modeId={modeId}
              selectedDetail={detail}
              onSelect={selectDetail}
              testId="integration-system-side"
            />
            <span className="sx-converge" aria-hidden="true">
              →
            </span>
          </div>

          <div className="sx-istage-core" data-testid="integration-spider">
            <span className="sx-spider-core">SPIDER</span>
          </div>

          <div className="sx-istage-out">
            <span className="sx-depart" aria-hidden="true">
              ↓
            </span>
            <StageLane
              nodes={mode.spiderSide}
              modeId={modeId}
              selectedDetail={detail}
              onSelect={selectDetail}
              testId="integration-spider-side"
            />
          </div>

          <div className="sx-insight" data-testid="integration-insight">
            <p className="sx-insight-quote">
              <b>{mode.insightLead}</b> {mode.insightBody}
            </p>
            <p className="sx-insight-meta">
              {mode.meta.map((item) => (
                <span key={item.label}>
                  <b>{item.label}:</b> {item.value}
                </span>
              ))}
            </p>
          </div>
        </div>

        {detail === "capability" ? <CapabilityDetail /> : null}
        {detail === "resolver" ? <ResolverDetail /> : null}

        <ExpandableDetail
          open={detail === "servicenow"}
          label="Ver exemplo com ServiceNow"
          testId="integration-servicenow"
          onToggle={() => selectDetail("servicenow")}
        >
          <ServiceNowDetail criterionId={criterionId} onCriterion={setCriterionId} />
        </ExpandableDetail>
      </div>
    </section>
  );
}
