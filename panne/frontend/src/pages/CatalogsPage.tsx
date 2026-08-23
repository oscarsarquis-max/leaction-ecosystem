import { useEffect, useState } from "react";
import type { CatalogItem } from "../api/types";
import { LoadingState } from "../components/Feedback";
import { useOrganization } from "../session/OrganizationContext";

export function CatalogsPage() {
  const { api, active } = useOrganization();
  const [units, setUnits] = useState<CatalogItem[] | null>(null);
  const [nutrients, setNutrients] = useState<CatalogItem[]>([]);
  const [allergens, setAllergens] = useState<CatalogItem[]>([]);
  const [sources, setSources] = useState<CatalogItem[]>([]);

  useEffect(() => {
    if (!active) return;
    void Promise.all([
      api.getCatalogUnits(),
      api.getCatalogNutrients(),
      api.getCatalogAllergens(),
      api.getCatalogSources(),
    ]).then(([unitPage, nutrientPage, allergenPage, sourcePage]) => {
      setUnits(unitPage.data);
      setNutrients(nutrientPage.data);
      setAllergens(allergenPage.data);
      setSources(sourcePage.data);
    });
  }, [api, active]);

  if (!units) return <LoadingState />;
  return (
    <div className="stage">
      <div>
        <h1>Fontes técnicas e catálogos</h1>
        <p className="lede">Catálogo global é somente leitura. A organização não faz CRUD livre aqui.</p>
        <section className="panel">
          <h2>Unidades</h2>
          <p>{units.map((item) => item.code).join(", ") || "nenhuma"}</p>
        </section>
        <section className="panel">
          <h2>Nutrientes</h2>
          <p>{nutrients.map((item) => item.name ?? item.code).join(", ") || "nenhum"}</p>
        </section>
        <section className="panel">
          <h2>Alergênicos</h2>
          <p>{allergens.map((item) => item.name ?? item.code).join(", ") || "nenhum"}</p>
        </section>
        <section className="panel">
          <h2>Fontes visíveis</h2>
          <p>{sources.map((item) => item.title ?? item.code).join(", ") || "nenhuma"}</p>
        </section>
      </div>
      <aside className="panel">
        <h2>Acesso</h2>
        <p>somente leitura · restrito à sessão autenticada</p>
      </aside>
    </div>
  );
}
