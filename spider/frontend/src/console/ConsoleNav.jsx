const GROUPS = [
  {
    id: "home",
    label: null,
    items: [{ id: "home", label: "Home" }],
  },
  {
    id: "executions",
    label: "Execuções",
    items: [
      { id: "executions", label: "Execuções" },
      { id: "detail", label: "Detalhe" },
      { id: "overview", label: "Visão geral" },
    ],
  },
  {
    id: "operation",
    label: "Operação",
    items: [
      { id: "operational-health", label: "Cockpit Operacional" },
      { id: "worker-runtime", label: "Runtime de Workers" },
      { id: "capacity", label: "Capacidade & Resiliência" },
    ],
  },
  {
    id: "tests",
    label: "Testes & demonstração",
    items: [
      { id: "lab", label: "Laboratório Mock" },
      { id: "failure-lab", label: "Failure Lab" },
    ],
  },
  {
    id: "platform",
    label: "Plataforma",
    items: [
      { id: "implementation", label: "Implementação" },
      { id: "presentation", label: "Apresentação" },
    ],
  },
];

export function ConsoleNav({ view, onChange }) {
  return (
    <nav className="console-nav console-nav-grouped" aria-label="Navegação principal">
      {GROUPS.map((group) => (
        <div key={group.id} className="nav-group" data-testid={`nav-group-${group.id}`}>
          {group.label ? <p className="nav-group-label">{group.label}</p> : null}
          <div className="nav-group-items">
            {group.items.map((item) => (
              <button
                key={item.id}
                type="button"
                className={view === item.id ? "nav-btn active" : "nav-btn"}
                onClick={() => onChange(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </nav>
  );
}
