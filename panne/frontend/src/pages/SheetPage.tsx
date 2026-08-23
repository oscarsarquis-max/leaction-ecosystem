import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import logoCompleto from "../../images/aprovados/horizontal-escuro.png";
import type { SheetIssue } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { formatDecimal, statusLabel } from "../format";
import { useOrganization } from "../session/OrganizationContext";

function text(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "";
}

export function SheetPage() {
  const { orderId = "", issueId = "" } = useParams();
  const { api } = useOrganization();
  const [issue, setIssue] = useState<SheetIssue | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api
      .getSheet(orderId, issueId)
      .then((response) => setIssue(response.data))
      .catch(setError);
  }, [api, issueId, orderId]);

  if (error) return <ErrorState error={error} />;
  if (!issue) return <LoadingState>Carregando ficha…</LoadingState>;

  const payload = issue.canonical_payload;
  const order = payload.order ?? {};
  const materials = Array.isArray(payload.materials) ? payload.materials : [];
  const steps = Array.isArray(payload.steps) ? payload.steps : [];
  const batches = Array.isArray(payload.batches) ? payload.batches : [];
  const policy = payload.policy && typeof payload.policy === "object" ? payload.policy : {};
  const replaced = Boolean(issue.previous_issue_id);
  const cancelled = issue.order_status_at_issue === "cancelled";

  return (
    <article className="sheet">
      <div className="no-print">
        <p>
          <Link to={`/ordens/${orderId}`}>← Ordem</Link>
        </p>
        <button type="button" className="primary" onClick={() => window.print()}>
          Imprimir
        </button>
      </div>
      <header className="sheet-running">
        <img className="sheet-brand" src={logoCompleto} alt="Panne" />
        <div>
          <strong>Panne</strong> · ficha {issue.issue_number} · {order.public_code ?? orderId}
        </div>
      </header>
      {replaced || cancelled ? (
        <p className="sheet-warning">
          {cancelled ? "Ordem cancelada na emissão. " : ""}
          {replaced ? "Esta emissão substitui uma emissão anterior." : ""}
        </p>
      ) : null}
      <h1>Ficha de produção {order.public_code ?? ""}</h1>
      <p>
        Empresa:{" "}
        {payload.organization?.display_name ||
          payload.organization?.slug ||
          "não informado"}
      </p>
      <p>
        Estabelecimento:{" "}
        {payload.establishment?.display_name ||
          payload.establishment?.code ||
          "não informado"}
      </p>
      <p>Finalidade: {issue.purpose}</p>
      <p>Estado na emissão: {statusLabel(issue.order_status_at_issue)}</p>
      <p>Emissão anterior: {issue.previous_issue_id ?? "nenhuma"}</p>
      <p>Produto: não informado no payload canônico</p>
      <p>Quantidade alvo: {formatDecimal(text(order.target_quantity) || null)}</p>
      <section>
        <h2>Hashes e versões</h2>
        <p className="hashes">
          payload {issue.payload_sha256} · snapshot {text(order.snapshot_hash) || "—"} · materiais{" "}
          {text(order.materials_hash) || "—"} · etapas {text(order.steps_hash) || "—"} · política{" "}
          {text(order.policy_hash) || "—"} · schema {text(payload.schema_version) || "—"}
        </p>
      </section>
      <section>
        <h2>Bateladas</h2>
        {batches.map((batch, index) => (
          <p key={index}>
            {text(batch.operational_code)} · {formatDecimal(text(batch.target) || null)} ·{" "}
            {statusLabel(text(batch.status))}
          </p>
        ))}
      </section>
      <section>
        <h2>Ingredientes e quantidades</h2>
        <table>
          <thead>
            <tr>
              <th>Seq.</th>
              <th>Nome</th>
              <th>Bruto</th>
              <th>Líquido</th>
              <th>Unidade</th>
            </tr>
          </thead>
          <tbody>
            {materials.map((item, index) => (
              <tr key={index}>
                <td>{text(item.sequence)}</td>
                <td>{text(item.name)}</td>
                <td>{formatDecimal(text(item.gross) || null)}</td>
                <td>{formatDecimal(text(item.net) || null)}</td>
                <td>{text(item.unit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section>
        <h2>Etapas, tempos e temperaturas</h2>
        {steps.map((step, index) => (
          <p key={index}>
            {text(step.sequence)}. {text(step.title)} — {text(step.instructions) || "sem instrução no payload"}
          </p>
        ))}
      </section>
      <section>
        <h2>Alertas e apontamento</h2>
        <p>
          Alertas operacionais:{" "}
          {text((payload as { alerts?: unknown }).alerts) || "não presentes nesta emissão"}
        </p>
        <p>
          Campos de apontamento:{" "}
          {text((payload as { annotation_fields?: unknown }).annotation_fields) ||
            "não presentes nesta emissão"}
        </p>
        <p>Política: {text(policy.algorithm_code)} {text(policy.algorithm_version)}</p>
      </section>
      <section>
        <h2>Responsável, data e hora</h2>
        <p>
          {payload.issuer?.display_name || "não informado"}
          {payload.issuer?.issued_at ? ` · ${payload.issuer.issued_at}` : ""}
        </p>
      </section>
    </article>
  );
}
