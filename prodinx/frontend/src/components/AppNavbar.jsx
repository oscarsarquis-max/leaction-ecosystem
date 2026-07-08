import { Link, useLocation } from "react-router-dom";
import { SlidersHorizontal } from "lucide-react";
import LogoutButton from "./LogoutButton";

const NAV_ITEMS = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Métricas", to: "/dashboard#metricas" },
  { label: "Detalhes", to: "/detalhes" },
  { label: "Importações", to: "/importacoes" },
  {
    label: "Parâmetros",
    to: "/parametros",
    icon: SlidersHorizontal,
    title: "Configurações de IAPS",
  },
];

function isNavItemActive(pathname, item) {
  if (item.to === "/dashboard") {
    return pathname === "/dashboard";
  }

  if (item.to === "/dashboard#metricas") {
    return pathname === "/dashboard";
  }

  return pathname === item.to || pathname.startsWith(`${item.to}/`);
}

function AppNavbar() {
  const location = useLocation();

  return (
    <nav className="flex flex-wrap items-center gap-1 sm:gap-2">
      {NAV_ITEMS.map((item) => {
        const ativo = isNavItemActive(location.pathname, item);
        const Icon = item.icon;

        return (
          <Link
            key={item.label}
            to={item.to}
            title={item.title || item.label}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
              ativo
                ? "bg-brand-laranja text-white"
                : "text-white/80 hover:bg-white/10 hover:text-white"
            }`}
          >
            {Icon && <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />}
            {item.label}
          </Link>
        );
      })}
      <LogoutButton />
    </nav>
  );
}

export default AppNavbar;
