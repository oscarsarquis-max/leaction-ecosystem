import { useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

function LogoutButton({ className = "" }) {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <button
      type="button"
      onClick={handleLogout}
      title="Encerrar sessão"
      className={`inline-flex items-center gap-1.5 rounded-lg border border-white/25 bg-white/10 px-3 py-2 text-sm font-medium text-white transition hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-brand-laranja focus:ring-offset-2 focus:ring-offset-brand-verde ${className}`}
    >
      <LogOut className="h-4 w-4 shrink-0" strokeWidth={2} />
      Sair
    </button>
  );
}

export default LogoutButton;
