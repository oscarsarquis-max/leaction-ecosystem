import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import { ErrorState, LoadingState } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { formatOperationalQuantity } from "../language/quantities";
import {
  formatBakersPercentage,
  recipeIdentityLabel,
  recipeVersionLabel,
} from "../language/recipes";
import { useOrganization } from "../session/OrganizationContext";

export function RecipeSheetPage() {
  const { recipeId, versionId } = useParams();
  const { api, active } = useOrganization();
  const [state, setState] = useState<
    | { kind: "carregando" }
    | { kind: "ok"; payload: Record<string, unknown> }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });

  const orgId = active?.organization_id ?? null;
  useEffect(() => {
    if (!orgId || !recipeId || !versionId) return;
    let alive = true;
    setState({ kind: "carregando" });
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
  }, [api, orgId, recipeId, versionId]);

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") {
    return <ErrorState error={state.error instanceof ApiError ? state.error : new Error("Falha")} />;
  }
  const payload = state.payload;
  const identity = (payload.identity ?? {}) as Record<string, string>;
  const version = (payload.version ?? {}) as Record<string, string | number>;
  const components = (payload.components ?? []) as Array<
    Record<string, string | number | boolean | Record<string, string> | null>
  >;
  const steps = (payload.steps ?? []) as Array<Record<string, string | number>>;
  const contentHash = String(payload.payload_sha256 ?? "");
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
        Código {identity.code} · situação {recipeIdentityLabel(String(identity.status ?? ""))} · versão{" "}
        {recipeVersionLabel(String(version.status ?? ""))}
        {contentHash ? " · conteúdo registrado" : ""}
      </p>
      <TechnicalAuditDetails
        rows={[
          {
            label: "Hash do conteúdo",
            value: contentHash || "—",
            copyable: Boolean(contentHash),
          },
        ]}
      />
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
          {components.map((item, index) => {
            const unitObj = item.unit as { code?: string; symbol?: string } | null;
            const unit = unitObj?.symbol || unitObj?.code || "g";
            return (
              <tr key={index}>
                <td>{String(item.sequence)}</td>
                <td>{String(item.label ?? "Ingrediente indisponível")}</td>
                <td>{formatOperationalQuantity(String(item.net_quantity ?? ""), unit)}</td>
                <td>{formatOperationalQuantity(String(item.gross_quantity ?? ""), unit)}</td>
                <td>
                  {formatBakersPercentage(
                    item.bakers_percentage == null ? null : String(item.bakers_percentage),
                  )}
                </td>
              </tr>
            );
          })}
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
