import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/errors";
import { RecipeAiMentor } from "../components/RecipeAiMentor";
import { useOrganization } from "../session/OrganizationContext";

export function RecipeAiWizardPage({ mode }: { mode: "create" | "adapt" }) {
  const { api, hasPermission } = useOrganization();
  const navigate = useNavigate();
  const [mentorStep, setMentorStep] = useState(mode === "adapt" ? 2 : 1);
  const [minimized, setMinimized] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!hasPermission("recipe.ai.propose")) {
    return <p>Este papel não gera propostas.</p>;
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    setMentorStep(4);
    try {
      const created = await api.catalogCommand<{ data: { id: string } }>("/recipe-ai/proposals", {
        body: {
          intent: mode === "adapt" ? "adapt_recipe" : "create_recipe",
          objective: String(data.get("objective") ?? ""),
          product_type: String(data.get("product_type") ?? "") || null,
          yield_units: data.get("yield_units") ? Number(data.get("yield_units")) : null,
          technical_traits: String(data.get("technical_traits") ?? "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          required_components: String(data.get("required_components") ?? "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          forbidden_components: String(data.get("forbidden_components") ?? "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          allergens_to_avoid: String(data.get("allergens_to_avoid") ?? "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          process_limits: String(data.get("process_limits") ?? "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          base_formulation_version_id: String(data.get("base_version") ?? "") || null,
          jurisdiction: String(data.get("jurisdiction") ?? "") || null,
          notes: String(data.get("notes") ?? "") || null,
        },
        idempotencyKey: crypto.randomUUID(),
      });
      setMentorStep(6);
      navigate(`/receitas/assistente/${created.data.id}`);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Não foi possível gerar a proposta.";
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stage">
      <div>
        <h1>{mode === "adapt" ? "Adaptar receita" : "Criar com assistência"}</h1>
        <p className="lede">
          <span className="badge">Assistido por IA</span> Entrada guiada. Sem chat livre. Evite
          dados pessoais ou comerciais desnecessários.
        </p>
        <form className="panel" onSubmit={(event) => void submit(event)}>
          {mode === "adapt" ? (
            <label>
              Versão-base
              <input name="base_version" required placeholder="Identificador da versão" />
            </label>
          ) : null}
          <label>
            Objetivo
            <textarea name="objective" required maxLength={2000} rows={3} />
          </label>
          <label>
            Tipo de produto
            <input name="product_type" maxLength={200} />
          </label>
          <label>
            Rendimento ou quantidade
            <input name="yield_units" type="number" min={1} />
          </label>
          <label>
            Características técnicas
            <input name="technical_traits" placeholder="separar por vírgula" />
          </label>
          <label>
            Componentes obrigatórios
            <input name="required_components" />
          </label>
          <label>
            Componentes proibidos
            <input name="forbidden_components" />
          </label>
          <label>
            Alergênicos a evitar
            <input name="allergens_to_avoid" />
          </label>
          <p className="meta">Não prometemos ausência de alergênico.</p>
          <label>
            Limites do processo
            <input name="process_limits" />
          </label>
          <label>
            Jurisdição
            <input name="jurisdiction" />
          </label>
          <label>
            Observações
            <textarea name="notes" maxLength={1000} rows={2} />
          </label>
          {error ? <p role="alert">{error}</p> : null}
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Buscando evidências…" : "Gerar proposta"}
          </button>
        </form>
      </div>
      <RecipeAiMentor
        step={mentorStep}
        minimized={minimized}
        onMinimize={() => setMinimized(true)}
        onResume={() => setMinimized(false)}
        onCancel={() => navigate("/receitas/assistente")}
      />
    </div>
  );
}
