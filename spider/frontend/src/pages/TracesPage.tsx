import { useEffect, useState } from "react";
import { apiGet } from "../api";

type TraceRow = {
  id: string;
  correlationId: string;
  productCode: string;
  status: string;
  startedAt: string;
  finishedAt: string | null;
  errorSummary: string | null;
};

export function TracesPage() {
  const [rows, setRows] = useState<TraceRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    apiGet<TraceRow[]>("/api/v1/traces/recent")
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <section className="panel">
      <h2>Traces recentes</h2>
      <p className="muted">Audit log técnico (tb_audit_trace).</p>
      <button type="button" onClick={load}>
        Atualizar
      </button>
      {error ? <p className="bad">{error}</p> : null}
      <table>
        <thead>
          <tr>
            <th>Correlation</th>
            <th>Produto</th>
            <th>Status</th>
            <th>Início</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>
                <code>{r.correlationId}</code>
              </td>
              <td>{r.productCode}</td>
              <td className={r.status === "completed" ? "ok" : "bad"}>
                {r.status}
              </td>
              <td>{r.startedAt}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
