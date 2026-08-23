import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import { ErrorState, LoadingState } from "../components/Feedback";
import { useOrganization } from "../session/OrganizationContext";

export function RecipeSheetPage() {
  const { recipeId, versionId } = useParams();
  const { api, active } = useOrganization();
  const [state, setState] = useState<
    | { kind: "carregando" }
    | { kind: "ok"; payload: Record<string, unknown> }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });

  useEffect(() => {
    if (!active || !recipeId || !versionId) return;
    let alive = true;
    api
      .getRecipeSheet(recipeId, versionId)
      .then((response) => {
        if (alive) setState({ kind: "ok", payload: response.data });
      })
      .catch((error) => {
        if (alive) setState({ kind: "erro", error });
      });
    return () => {
      alive = false;
    };
  }, [api, active, recipeId, versionId]);

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") {
    return <ErrorState error={state.error instanceof ApiError ? state.error : new Error("Falha")} />;
  }
  const payload = state.payload;
  const identity = (payload.identity ?? {}) as Record<string, string>;
  const version = (payload.version ?? {}) as Record<string, string | number>;
  const components = (payload.components ?? []) as Array<Record<string, string | number | boolean>>;
  const steps = (payload.steps ?? []) as Array<Record<string, string | number>>;
  return (
    <article className="sheet">
      <div className="sheet-running">
        <span>{identity.display_name}</span>
        <span>v{String(version.version_number ?? "")}</span>
      </div>
      <h1>Ficha técnica</h1>
      <p className="sheet-warning">
        {(payload.disclaimer as string) || "Prévia técnica incompleta e não validada regulatoriamente."}
      </p>
      <p>
        Código {identity.code} · situação {String(version.status ?? "")} · hash{" "}
        {String(payload.payload_sha256 ?? "")}
      </p>
      <h2>Componentes</h2>
      <table>
        <thead>
          <tr>
            <th>Seq.</th>
            <th>Componente</th>
            <th>Líquido</th>
            <th>Bruto</th>
            <th>%</th>
          </tr>
        </thead>
        <tbody>
          {components.map((item, index) => (
            <tr key={index}>
              <td>{String(item.sequence)}</td>
              <td>{String(item.label ?? "")}</td>
              <td>{String(item.net_quantity ?? "")}</td>
              <td>{String(item.gross_quantity ?? "")}</td>
              <td>{String(item.bakers_percentage ?? "—")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h2>Processo</h2>
      <ol>
        {steps.map((step, index) => (
          <li key={index}>
            <strong>{String(step.title)}</strong> — {String(step.instructions)}
          </li>
        ))}
      </ol>
      <p className="no-print">
        <button type="button" className="primary" onClick={() => window.print()}>
          Imprimir A4
        </button>
      </p>
    </article>
  );
}
