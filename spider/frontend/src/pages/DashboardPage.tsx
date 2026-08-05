export function DashboardPage() {
  return (
    <section className="panel">
      <h2>Painel operacional</h2>
      <p className="muted">
        O Spider orquestra chamadas aos sistemas legados (cadastro, crédito, …)
        sem se tornar o sistema de registro. Use <strong>Rotas</strong> para ver
        o mapa de produto, <strong>Traces</strong> para auditoria e{" "}
        <strong>Testar</strong> para disparar uma orquestração local.
      </p>
      <ul className="muted">
        <li>API: <code>http://localhost:8080</code></li>
        <li>Mocks: cadastro <code>:8091</code> · crédito <code>:8092</code></li>
        <li>Postgres técnico: <code>localhost:5432/spider_orchestrator</code></li>
      </ul>
    </section>
  );
}
