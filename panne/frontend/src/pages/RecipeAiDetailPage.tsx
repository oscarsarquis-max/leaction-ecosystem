import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { RecipeAiChange, RecipeAiProposal } from "../api/types";
import { ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { RecipeAiMentor } from "../components/RecipeAiMentor";
import { useOrganization } from "../session/OrganizationContext";

function kindLabel(kind: RecipeAiChange["change_kind"]): string {
  if (kind === "added") return "adicionado";
  if (kind === "removed") return "removido";
  if (kind === "changed") return "alterado";
  return "não resolvido";
}

export function RecipeAiDetailPage() {
  const { proposalId = "" } = useParams();
  const { api, hasPermission } = useOrganization();
  const [proposal, setProposal] = useState<RecipeAiProposal | null>(null);
  const [grounding, setGrounding] = useState<Array<Record<string, string | null>>>([]);
  const [error, setError] = useState<unknown>(null);
  const [filter, setFilter] = useState("todos");
  const [comment, setComment] = useState("");
  const [minimized, setMinimized] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    Promise.all([api.getRecipeAiProposal(proposalId), api.getRecipeAiGrounding(proposalId)])
      .then(([detail, ground]) => {
        if (!alive) return;
        setProposal(detail.data);
        setGrounding(ground.data.results ?? []);
      })
      .catch((err) => {
        if (alive) setError(err);
      });
    return () => {
      alive = false;
    };
  }, [api, proposalId]);

  const changes = useMemo(() => {
    const rows = proposal?.changes ?? [];
    if (filter === "todos") return rows;
    return rows.filter((item) => item.change_kind === filter);
  }, [filter, proposal]);

  const mentorStep =
    proposal?.status === "materialized"
      ? 9
      : proposal?.status === "accepted"
        ? 8
        : proposal?.status === "grounding_insufficient"
          ? 4
          : 7;

  async function decideChange(changeKey: string, decision: "accepted" | "rejected") {
    if (!proposal) return;
    setBusy(true);
    try {
      const updated = await api.catalogCommand<{ data: RecipeAiProposal; row_version: number }>(
        `/recipe-ai/proposals/${proposal.id}/changes`,
        {
          body: { decisions: [{ change_key: changeKey, decision }] },
          ifMatch: proposal.row_version,
        },
      );
      setProposal(updated.data);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function review(decision: "accepted" | "rejected") {
    if (!proposal) return;
    setBusy(true);
    try {
      const updated = await api.catalogCommand<{ data: RecipeAiProposal; row_version: number }>(
        `/recipe-ai/proposals/${proposal.id}/review`,
        {
          body: { decision, confirm: decision === "accepted", notes: comment },
          idempotencyKey: crypto.randomUUID(),
          ifMatch: proposal.row_version,
        },
      );
      setProposal(updated.data);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function materialize() {
    if (!proposal) return;
    setBusy(true);
    try {
      const updated = await api.catalogCommand<{ data: RecipeAiProposal; row_version: number }>(
        `/recipe-ai/proposals/${proposal.id}/materialize`,
        {
          idempotencyKey: crypto.randomUUID(),
          ifMatch: proposal.row_version,
        },
      );
      setProposal(updated.data);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (error && !proposal) {
    return (
      <ErrorState error={error instanceof ApiError ? error : new Error("Falha ao abrir proposta")} />
    );
  }
  if (!proposal) return <LoadingState />;

  const unresolved = (proposal.items ?? []).filter((item) => item.resolution_status !== "resolved");
  const blocked =
    proposal.status === "grounding_insufficient" ||
    proposal.status === "validation_failed" ||
    unresolved.length > 0;

  return (
    <div className="stage">
      <div>
        <h1>{proposal.title}</h1>
        <p className="lede">
          <span className="badge">Assistido por IA</span>{" "}
          <StatusBadge tone="atencao" label={proposal.status_label} />
        </p>
        {error instanceof ApiError ? <p role="alert">{error.message}</p> : null}
        <section className="panel">
          <h2>Objetivo</h2>
          <p>{proposal.objective_summary}</p>
          <p>Hipóteses visíveis: rendimento e perda não são fatos oficiais.</p>
        </section>
        <section className="panel">
          <h2>Grounding e fontes</h2>
          {proposal.status === "grounding_insufficient" ? (
            <p role="alert">Grounding insuficiente. A geração não foi concluída.</p>
          ) : null}
          {grounding.length === 0 ? <p>Nenhum fragmento listado.</p> : null}
          <ul>
            {grounding.map((item, index) => (
              <li key={`${item.locator}-${index}`}>
                {item.title} · {item.source_kind} · {item.locator}
              </li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <h2>Comparação</h2>
          <div className="filters">
            {["todos", "added", "removed", "changed", "unresolved"].map((code) => (
              <button
                key={code}
                type="button"
                aria-pressed={filter === code}
                onClick={() => setFilter(code)}
              >
                {code === "todos" ? "todas" : kindLabel(code as RecipeAiChange["change_kind"])}
              </button>
            ))}
          </div>
          <ul>
            {changes.map((item) => (
              <li key={item.change_key}>
                {kindLabel(item.change_kind)} · {item.path} · {item.decision}
                {hasPermission("recipe.ai.review") && item.decision === "pending" ? (
                  <>
                    <button type="button" disabled={busy} onClick={() => void decideChange(item.change_key, "accepted")}>
                      Aceitar
                    </button>
                    <button type="button" disabled={busy} onClick={() => void decideChange(item.change_key, "rejected")}>
                      Rejeitar
                    </button>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
          <h3>Citações</h3>
          <ul>
            {(proposal.citations ?? []).map((item) => (
              <li key={item.id}>{item.claim_path}</li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <h2>Itens não resolvidos</h2>
          {unresolved.length === 0 ? <p>Nenhum.</p> : null}
          <ul>
            {unresolved.map((item) => (
              <li key={item.id}>{item.proposed_ingredient_name} — a IA não cria ingrediente.</li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <h2>Revisão</h2>
          <label>
            Comentário humano
            <textarea value={comment} onChange={(event) => setComment(event.target.value)} rows={2} />
          </label>
          {hasPermission("recipe.ai.review") ? (
            <div>
              <button type="button" className="primary" disabled={busy || blocked} onClick={() => void review("accepted")}>
                Aceitar em conjunto
              </button>
              <button type="button" disabled={busy} onClick={() => void review("rejected")}>
                Rejeitar integralmente
              </button>
            </div>
          ) : null}
          {hasPermission("recipe.ai.materialize") ? (
            <button
              type="button"
              disabled={busy || blocked || proposal.status === "materialized"}
              onClick={() => void materialize()}
            >
              Materializar rascunho
            </button>
          ) : null}
          {proposal.status === "materialized" && proposal.materialized ? (
            <p>
              Resultado materializado:{" "}
              <Link to={`/receitas/${proposal.materialized.formulation_id}`}>
                abrir rascunho
              </Link>
            </p>
          ) : null}
        </section>
      </div>
      <RecipeAiMentor
        step={mentorStep}
        minimized={minimized}
        onMinimize={() => setMinimized(true)}
        onResume={() => setMinimized(false)}
        onCancel={() => undefined}
      />
    </div>
  );
}
