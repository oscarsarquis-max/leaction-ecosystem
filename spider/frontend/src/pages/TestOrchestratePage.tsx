import { useState } from "react";
import { apiPost } from "../api";

export function TestOrchestratePage() {
  const [productCode, setProductCode] = useState("CONTA_DIGITAL_ONBOARDING");
  const [customerExternalId, setCustomerExternalId] = useState("CLI-1001");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  return (
    <section className="panel">
      <h2>Testar orquestração</h2>
      <p className="muted">
        Dispara cadastro → crédito nos mocks locais e grava trace no Postgres.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          void apiPost(
            "/api/v1/orchestrate",
            {
              productCode,
              customerExternalId,
              context: { canal: "painel-local" },
            },
            crypto.randomUUID(),
          )
            .then((data) => setResult(JSON.stringify(data, null, 2)))
            .catch((err: Error) => setError(err.message))
            .finally(() => setBusy(false));
        }}
      >
        <label>
          Código do produto
          <input
            value={productCode}
            onChange={(e) => setProductCode(e.target.value)}
          />
        </label>
        <label>
          ID externo do cliente
          <input
            value={customerExternalId}
            onChange={(e) => setCustomerExternalId(e.target.value)}
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Executando…" : "Orquestrar"}
        </button>
      </form>
      {error ? <p className="bad">{error}</p> : null}
      {result ? <pre>{result}</pre> : null}
    </section>
  );
}
