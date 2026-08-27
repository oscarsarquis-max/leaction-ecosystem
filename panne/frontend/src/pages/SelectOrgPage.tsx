import { useNavigate } from "react-router-dom";
import { AssistantAvatar } from "../assistant/AssistantAvatar";
import { GlobalAssistant } from "../assistant/GlobalAssistant";
import { useAssistant } from "../assistant/AssistantContext";
import { useOrganization } from "../session/OrganizationContext";

export function SelectOrgPage() {
  const { associations, selectOrganization } = useOrganization();
  const navigate = useNavigate();
  const { open } = useAssistant();

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
      <AssistantAvatar />
      {open ? <GlobalAssistant /> : null}
    </main>
  );
}
