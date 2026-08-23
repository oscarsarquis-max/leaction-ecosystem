import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { RecipeCard } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { LabelingMentor } from "../components/LabelingMentor";
import { useOrganization } from "../session/OrganizationContext";

export function LabelingCreatePage() {
  const { api, hasPermission } = useOrganization();
  const navigate = useNavigate();
  const [recipes, setRecipes] = useState<RecipeCard[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .listRecipes()
      .then((page) => setRecipes(page.items))
      .catch(setError);
  }, [api]);

  if (!hasPermission("labeling.dossier.create")) {
    return <ErrorState error={new ApiError("nao_autorizado", "Não autorizado.", 403)} />;
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    try {
      const created = await api.catalogCommand<{ data: { id: string } }>("/labeling/dossiers", {
        body: { formulation_version_id: String(data.get("formulation_version_id")) },
        idempotencyKey: crypto.randomUUID(),
      });
      navigate(`/conformidade/dossies/${created.data.id}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stage">
      <div>
        <h1>Novo dossiê</h1>
        <p className="lede">A criação não avalia nem aprova o rótulo.</p>
        {recipes == null && error == null ? <LoadingState /> : null}
        {error ? <ErrorState error={error} /> : null}
        {recipes ? (
          <form className="stack" onSubmit={submit}>
            <label>
              Versão da receita
              <select name="formulation_version_id" required>
                {recipes.map((item) => (
                  <option key={item.id} value={item.current_version?.id ?? ""}>
                    {item.display_name} · versão {item.current_version?.version_number}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit" className="primary" disabled={busy}>
              Criar dossiê
            </button>
          </form>
        ) : null}
      </div>
      <LabelingMentor step={0} pending={["produto ainda não vinculado"]} />
    </div>
  );
}
