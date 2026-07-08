import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function GuestRoute({ children }) {
  const { autenticado } = useAuth();

  if (autenticado) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export default GuestRoute;
