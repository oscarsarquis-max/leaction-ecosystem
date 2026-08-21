import { useEffect, useMemo, useState } from "react";
import { getImplementationStatus } from "./api";

const STATUS_LABEL = {
  VERIFIED: { text: "Verificado", icon: "✓" },
  IMPLEMENTED: { text: "Implementado", icon: "●" },
  IN_PROGRESS: { text: "Em progresso", icon: "…" },
  PLANNED: { text: "Planejado", icon: "○" },
  BLOCKED: { text: "Bloqueado", icon: "!" },
  DEPRECATED: { text: "Depreciado", icon: "–" },
};

const JOURNEY_GROUPS = [
  "GROUP_A_VISIBILITY_OBSERVABILITY",
  "GROUP_B_RUNTIME_OPERATIONS",
  "GROUP_C_PLATFORM_READINESS",
  "GROUP_D_REAL_INTEGRATION",
];

const GROUP_LABEL = {
  GROUP_A_VISIBILITY_OBSERVABILITY: "A · Visibilidade e observabilidade (015–018)",
  GROUP_B_RUNTIME_OPERATIONS: "B · Operações de runtime (019–021)",
  GROUP_C_PLATFORM_READINESS: "C · Prontidão de plataforma (022–024)",
  GROUP_D_REAL_INTEGRATION: "D · Integração real (025–026)",
};

const INTEGRATION_NOTE = {
  MOCK_ONLY: "Mock only",
  SIMULATED_INFRASTRUCTURE: "Simulado (planejado)",
  CORPORATE_SANDBOX: "Sandbox corporativo (planejado — não ativo)",
  REAL_PILOT: "Piloto real (planejado — não ativo)",
  PRODUCTION: "PROIBIDO neste roadmap",
};

export default function ImplementationCockpit() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    const c = new AbortController();
    setStatus("loading");
    getImplementationStatus({ signal: c.signal })
      .then((d) => {
        setData(d);
        setError(null);
        setStatus("ok");
      })
      .catch((e) => {
        if (e.name === "AbortError") return;
        setError(e);
        setStatus("error");
      });
    return () => c.abort();
  }, []);

  const journeyCaps = useMemo(() => {
    return (data?.capabilities || []).filter((c) => JOURNEY_GROUPS.includes(c.groupCode));
  }, [data]);

  const byGroup = useMemo(() => {
    const map = {};
    for (const code of JOURNEY_GROUPS) map[code] = [];
    for (const cap of journeyCaps) {
      (map[cap.groupCode] ||= []).push(cap);
    }
    return map;
  }, [journeyCaps]);

  if (status === "loading") return <p role="status">Carregando manifesto…</p>;
  if (status === "error") {
    return (
      <p className="error" role="alert">
        Falha ao carregar implementação: {error?.message || "erro"}. O manifesto não é importado no
        browser — apenas via API.
      </p>
    );
  }

  const journeyGroupsMeta = (data.groups || []).filter((g) => g.journey);

  return (
    <section className="panel-card" aria-labelledby="impl-title">
      <div className="detail-head">
        <h2 id="impl-title">Cockpit da implementação</h2>
        <span className="pill mock-badge" title="Boundary ativa">
          BOUNDARY ATIVA · {data.mockRealBoundary || "MOCK_ONLY"}
        </span>
      </div>
      <p className="muted">
        Prompt atual: <strong>{data.currentPrompt}</strong> · grupo atual{" "}
        <strong>{data.currentGroup}</strong> · próximo planejado{" "}
        <strong>SPIDER-PROMPT-016</strong> · produto {data.productVersion}
      </p>
      <div className="stat-row">
        <div>
          <span className="muted">Baseline backend</span>
          <strong>
            {data.baseline?.backendTests} (fail {data.baseline?.failures}/err {data.baseline?.errors}
            /skip {data.baseline?.skipped})
          </strong>
        </div>
        <div>
          <span className="muted">Baseline frontend</span>
          <strong>{data.baseline?.frontendTests}</strong>
        </div>
        <div>
          <span className="muted">Governança</span>
          <strong>{data.governanceMode}</strong>
        </div>
      </div>

      <h3>Jornada oficial 015–026</h3>
      <ul className="state-counts" aria-label="Contagens por grupo">
        {journeyGroupsMeta.map((g) => (
          <li key={g.groupCode}>
            <span className="pill">{GROUP_LABEL[g.groupCode] || g.groupCode}</span>{" "}
            <strong>
              {g.verified}/{g.denominator} VERIFIED
            </strong>
            {" · "}
            {g.planned}/{g.denominator} PLANNED
          </li>
        ))}
      </ul>
      <p className="muted">
        Transições: A→B após 018 · B→C após 021 · C→D após 024 (READY_FOR_PILOT). CORPORATE_SANDBOX
        (025) e REAL_PILOT (026) são planejados — não ativos. Nenhum item é PRODUCTION.
      </p>

      {JOURNEY_GROUPS.map((group) => (
        <div key={group} className="impl-group">
          <h3>{GROUP_LABEL[group] || group}</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Status</th>
                  <th scope="col">Capability</th>
                  <th scope="col">Runtime</th>
                  <th scope="col">Integração planejada</th>
                  <th scope="col">Deps</th>
                </tr>
              </thead>
              <tbody>
                {(byGroup[group] || []).map((c) => {
                  const st = STATUS_LABEL[c.status] || { text: c.status, icon: "?" };
                  const current = c.promptRef === data.currentPrompt;
                  const next = c.promptRef === "SPIDER-PROMPT-016";
                  return (
                    <tr
                      key={c.capabilityCode}
                      className={current ? "row-current" : next ? "row-next" : ""}
                    >
                      <td>
                        <span className={`status-chip status-${c.status.toLowerCase()}`}>
                          <span aria-hidden="true">{st.icon}</span> {st.text}
                          {current ? " · atual" : ""}
                          {next ? " · próximo" : ""}
                        </span>
                      </td>
                      <td>
                        <strong>{c.promptRef}</strong>
                        <div>{c.title}</div>
                        <div className="muted">{c.objective}</div>
                      </td>
                      <td>
                        <span className="pill">{c.runtimeAvailability}</span>
                      </td>
                      <td>
                        <span className="pill">{c.integrationLevel}</span>
                        <div className="muted">
                          {INTEGRATION_NOTE[c.integrationLevel] || c.integrationLevel}
                        </div>
                      </td>
                      <td className="muted">{(c.dependencies || []).join(", ") || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      <h3>Flags efetivas (redigidas)</h3>
      <pre className="code-block">{JSON.stringify(data.effectiveFlags, null, 2)}</pre>
      <h3>Fronteira</h3>
      <p className="muted">
        Boundary ativa: <strong>MOCK_ONLY</strong>. Sandbox/piloto constam no manifesto como
        planejados e só entram após gates do roadmap oficial.
      </p>
    </section>
  );
}
