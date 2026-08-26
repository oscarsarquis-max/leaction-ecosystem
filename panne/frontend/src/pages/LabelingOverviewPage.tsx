import { Link } from "react-router-dom";
import { StatusBadge } from "../components/Feedback";
import { useOrganization } from "../session/OrganizationContext";

export function LabelingOverviewPage() {
  const { hasPermission } = useOrganization();
  return (
    <div className="stage">
      <div>
        <div className="page-head">
          <div>
            <h1>Conformidade</h1>
            <p className="lede">
              Propostas técnicas para revisão humana. O sistema não declara conformidade e não emite certificado.
            </p>
          </div>
        </div>
        <div className="cards">
          <article className="card">
            <h2>Dossiês</h2>
            <p>Perfil de aplicabilidade, avaliação e candidato de rótulo.</p>
            {hasPermission("labeling.read") ? (
              <Link className="primary" to="/conformidade/dossies">
                Abrir dossiês
              </Link>
            ) : null}
          </article>
          <article className="card">
            <h2>Avaliações</h2>
            <p>Achados determinísticos com evidência e fonte.</p>
            <Link to="/conformidade/avaliacoes">Ver avaliações</Link>
          </article>
          <article className="card">
            <h2>Rótulos candidatos</h2>
            <p>Versões para conferência e impressão A4.</p>
            <Link to="/conformidade/rotulos">Ver candidatos</Link>
          </article>
          <article className="card">
            <h2>Fontes e normas</h2>
            <p>Atos vigentes. Orientação não substitui a norma.</p>
            <Link to="/conformidade/fontes">Abrir fontes</Link>
          </article>
        </div>
      </div>
      <aside className="panel">
        <h2>Limite deste recorte</h2>
        <p>
          <StatusBadge tone="atencao" label="proposta técnica" />
        </p>
        <p>Não há selo automático de conformidade. Revisão humana é obrigatória.</p>
      </aside>
    </div>
  );
}
