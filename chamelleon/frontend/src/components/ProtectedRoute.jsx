import { Navigate, useLocation } from 'react-router-dom';
import { canAccessRoute } from '../config/rbac';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children, roles }) {
  const { systemRole, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-slate-500">
        Carregando perfil...
      </div>
    );
  }

  const allowed = roles
    ? roles.includes(systemRole)
    : canAccessRoute(systemRole, location.pathname);

  if (!allowed) {
    return <Navigate to="/" replace state={{ forbidden: true }} />;
  }

  return children;
}
