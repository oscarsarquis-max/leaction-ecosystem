import { NavLink, Outlet } from "react-router-dom";
import "@/execution/execution.css";

const LINKS = [
  { to: "/execution", end: true, label: "Board" },
  { to: "/execution/sprints", label: "Sprints" },
  { to: "/execution/squads", label: "Squads" },
  { to: "/execution/ceremonies", label: "Cerimônias" },
] as const;

export function ExecutionLayout() {
  return (
    <div>
      <header className="mb-6">
        <h1 className="font-display text-2xl text-[var(--qm-ink)]">Execução</h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--qm-muted)]">
          Acompanhe ações de melhoria em sprints: o que está em andamento, o que
          bloqueia e o próximo passo de cada card.
        </p>
      </header>

      <nav className="execution-subnav" aria-label="Seções de execução">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={"end" in link ? link.end : undefined}
            className={({ isActive }) => (isActive ? "is-active" : undefined)}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  );
}
