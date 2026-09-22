import { Navigate } from "react-router-dom";
import { LoadingState } from "../components/Feedback";
import { useOrganization } from "../session/OrganizationContext";
import { landingPathForRoles } from "./landing";

export function LandingRedirect() {
  const { active, me, status } = useOrganization();
  if (status.kind === "carregando") return <LoadingState />;
  return <Navigate to={landingPathForRoles(active?.roles ?? me?.roles)} replace />;
}
