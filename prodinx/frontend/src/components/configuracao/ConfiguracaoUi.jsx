export function AlertaFeedback({ tipo, mensagem, onFechar }) {
  if (!mensagem) {
    return null;
  }

  const classes =
    tipo === "sucesso"
      ? "border-brand-verde/30 bg-brand-verde/10 text-brand-verde"
      : "border-brand-vermelho/30 bg-brand-vermelho/10 text-brand-vermelho";

  return (
    <div
      className={`flex items-start justify-between gap-3 rounded-xl border px-4 py-3 text-sm font-medium ${classes}`}
      role="alert"
    >
      <span>{mensagem}</span>
      {onFechar && (
        <button
          type="button"
          onClick={onFechar}
          className="shrink-0 text-xs uppercase tracking-wide opacity-70 hover:opacity-100"
        >
          Fechar
        </button>
      )}
    </div>
  );
}

export function IndicadorSoma({ valor, rotulo, tolerancia = 0.5 }) {
  const valido = Math.abs(valor - 100) <= tolerancia;

  return (
    <div
      className={`rounded-lg px-3 py-2 text-sm font-semibold ${
        valido
          ? "bg-brand-verde/10 text-brand-verde"
          : "bg-brand-vermelho/10 text-brand-vermelho"
      }`}
    >
      {rotulo}: {valor.toFixed(1)}%
      {!valido && " · deve totalizar 100%"}
    </div>
  );
}
