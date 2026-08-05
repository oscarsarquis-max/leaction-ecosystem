import { useEffect, useState } from "react";
import { apiGet } from "../api";

type RouteRow = {
  id: string;
  productCode: string;
  name: string;
  description: string;
  enabled: boolean;
  version: number;
};

export function RoutesPage() {
  const [rows, setRows] = useState<RouteRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<RouteRow[]>("/api/v1/routes")
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <section className="panel">
      <h2>Rotas de produto</h2>
      <p className="muted">Configuração em tb_product_routes (banco técnico).</p>
      {error ? <p className="bad">{error}</p> : null}
      <table>
        <thead>
          <tr>
            <th>Produto</th>
            <th>Nome</th>
            <th>Versão</th>
            <th>Ativa</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.productCode}</td>
              <td>
                <div>{r.name}</div>
                <div className="muted">{r.description}</div>
              </td>
              <td>{r.version}</td>
              <td className={r.enabled ? "ok" : "bad"}>
                {r.enabled ? "sim" : "não"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
