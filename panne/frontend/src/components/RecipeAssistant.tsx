import type { Completeness } from "../api/types";

const STEPS: Array<{ id: string; label: string; codes: string[] }> = [
  { id: "objetivo", label: "Objetivo e produto", codes: ["identidade"] },
  { id: "componentes", label: "Componentes", codes: ["componentes"] },
  { id: "percentual", label: "Quantidades e percentual", codes: ["farinha", "ingredientes"] },
  { id: "processo", label: "Processo", codes: ["etapas"] },
  { id: "rendimento", label: "Rendimento, perda e porção", codes: ["rendimento"] },
  { id: "calculo", label: "Cálculo técnico", codes: ["nutricao"] },
  { id: "trial", label: "Ensaio", codes: ["trial"] },
  { id: "revisao", label: "Revisão e aprovação", codes: ["aprovacao"] },
  { id: "publicacao", label: "Publicação", codes: ["referencias"] },
];

export function RecipeAssistant({
  completeness,
  minimized,
  onMinimize,
  onDismiss,
}: {
  completeness: Completeness | null;
  minimized?: boolean;
  onMinimize: () => void;
  onDismiss: () => void;
}) {
  const pending = completeness?.items ?? [];
  const blocking = pending.filter((item) => item.blocking);
  const current = blocking[0] ?? pending[0];
  const currentIndex = current
    ? STEPS.findIndex((step) => step.codes.includes(current.code))
    : completeness?.ready_to_publish
      ? 8
      : 7;
  const done = STEPS.filter(
    (step) => step.codes.length > 0 && !pending.some((item) => step.codes.includes(item.code)),
  ).length;
  const progress = completeness?.complete_dossier ? 100 : Math.round((done / STEPS.length) * 100);
  if (minimized) {
    return (
      <p className="meta">
        <button type="button" className="ghost" onClick={onMinimize}>
          Reabrir assistente
        </button>
      </p>
    );
  }
  return (
    <div className="drawer-assist panel" role="dialog" aria-labelledby="rec-ass-title">
      <h2 id="rec-ass-title">Assistente de receita</h2>
      <p>Objetivo: concluir a receita sem inteligência artificial. Completude não é conformidade.</p>
      <div
        className="progress"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progresso da receita"
      >
        <span style={{ width: `${progress}%` }} />
      </div>
      <ol>
        {STEPS.map((step, index) => (
          <li key={step.id} aria-current={index === currentIndex ? "step" : undefined}>
            {step.label}
          </li>
        ))}
      </ol>
      <p>Próxima ação: {current?.label ?? "Revisar, aprovar e publicar com decisão humana."}</p>
      <p>Bloqueios: {blocking.length ? blocking.map((item) => item.label).join(" ") : "nenhum"}</p>
      <p>Ajuda: o percentual do padeiro não precisa somar 100%. Publicação é humana.</p>
      <div>
        <button type="button" onClick={onMinimize}>
          Minimizar
        </button>
        <button type="button" onClick={onDismiss}>
          Dispensar ajuda
        </button>
      </div>
    </div>
  );
}
