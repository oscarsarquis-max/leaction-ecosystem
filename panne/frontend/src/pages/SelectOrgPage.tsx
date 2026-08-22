import { useNavigate } from "react-router-dom";
import { useOrganization } from "../session/OrganizationContext";

export function SelectOrgPage() {
  const { associations, selectOrganization } = useOrganization();
  const navigate = useNavigate();

  async function choose(id: string) {
    await selectOrganization(id);
    navigate("/producao", { replace: true });
  }

  return (
    <main className="feedback">
      <h1>Escolha a organização</h1>
      <p>Há mais de uma associação ativa. A API continua validando o contexto.</p>
      <ul>
        {associations.map((item) => (
          <li key={item.organization_id}>
            <button type="button" className="primary" onClick={() => void choose(item.organization_id)}>
              {item.display_name || item.slug}
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
