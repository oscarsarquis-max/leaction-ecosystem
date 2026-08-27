import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { useOrganization } from "../session/OrganizationContext";

function useList(kind: "assessments" | "candidates" | "sources") {
  const { api, active } = useOrganization();
  const [state, setState] = useState<
    | { kind: "carregando" }
    | { kind: "ok"; items: Array<Record<string, unknown>> }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const orgId = active?.organization_id ?? null;
  useEffect(() => {
    if (!orgId) return;
    let alive = true;
    setState({ kind: "carregando" });
    const request =
      kind === "assessments"
        ? api.listLabelingAssessments()
        : kind === "candidates"
          ? api.listLabelingCandidates()
          : api.listLabelingSources();
    request
      .then((page) => {
        if (alive) setState({ kind: "ok", items: page.items as Array<Record<string, unknown>> });
      })
      .catch((error) => {
        if (alive) setState({ kind: "erro", error });
      });
    return () => {
      alive = false;
    };
  }, [api, orgId, kind]);
  return state;
}

function Frame({
  title,
  lede,
  state,
  render,
}: {
  title: string;
  lede: string;
  state: ReturnType<typeof useList>;
  render: (item: Record<string, unknown>) => string;
}) {
  return (
    <div className="stage">
      <div>
        <h1>{title}</h1>
        <p className="lede">{lede}</p>
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} /> : null}
        {state.kind === "ok" && state.items.length === 0 ? <EmptyState>Nada para exibir.</EmptyState> : null}
        {state.kind === "ok" ? (
          <ul className="list">
            {state.items.map((item, index) => (
              <li key={String(item.id ?? index)}>{render(item)}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

export function LabelingAssessmentsPage() {
  return (
    <Frame
      title="Avaliações"
      lede="Cada avaliação é um recorte técnico. A soma dos achados não vira selo de conformidade."
      state={useList("assessments")}
      render={(item) => String(item.proposal_summary ?? item.status)}
    />
  );
}

export function LabelingCandidatesPage() {
  return (
    <Frame
      title="Rótulos candidatos"
      lede="Versões para conferência. Não são arte-final nem rótulo aprovado."
      state={useList("candidates")}
      render={(item) => String(item.watermark ?? "Candidato sem marca d'água")}
    />
  );
}

export function LabelingSourcesPage() {
  return (
    <Frame
      title="Fontes e normas"
      lede="Atos vigentes. Material de orientação não substitui a norma."
      state={useList("sources")}
      render={(item) =>
        `${String(item.title ?? "—")} · ${String(item.force ?? "—")} · acesso ${String(item.accessed_at ?? "—")}`
      }
    />
  );
}
