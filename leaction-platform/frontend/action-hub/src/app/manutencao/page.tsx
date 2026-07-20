export const dynamic = 'force-dynamic';

export default function ManutencaoPage() {
  return (
    <main
      style={{
        minHeight: '100vh',
        margin: 0,
        display: 'grid',
        placeItems: 'center',
        padding: 24,
        background:
          'radial-gradient(circle at 20% 20%, rgba(14,165,233,0.12), transparent 40%), radial-gradient(circle at 80% 0%, rgba(16,185,129,0.10), transparent 35%), linear-gradient(160deg, #0f172a 0%, #1e293b 100%)',
        color: '#e2e8f0',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
      }}
    >
      <section
        style={{
          width: 'min(560px, 100%)',
          background: 'rgba(15,23,42,0.85)',
          border: '1px solid rgba(148,163,184,0.25)',
          borderLeft: '6px solid #38bdf8',
          borderRadius: 20,
          padding: '36px 32px',
          textAlign: 'center',
          boxShadow: '0 20px 50px rgba(0,0,0,0.35)',
        }}
      >
        <p style={{ margin: '0 0 8px', letterSpacing: '0.12em', fontSize: 12, color: '#7dd3fc' }}>
          ACTION HUB
        </p>
        <h1 style={{ margin: '0 0 12px', fontSize: '1.75rem', fontWeight: 800 }}>
          Em preparação
        </h1>
        <p style={{ margin: 0, color: '#94a3b8', lineHeight: 1.6 }}>
          Estamos finalizando o lançamento. Em breve o sistema estará disponível para todos os
          clientes.
        </p>
      </section>
    </main>
  );
}
