import { useEffect } from "react";
import type { Completeness } from "../api/types";
import { useAssistant } from "../assistant/AssistantContext";

const STEPS: Array<{ id: string; label: string; codes: string[] }> = [
  { id: "identificacao", label: "Identificação", codes: ["identificacao", "identidade_inativa"] },
  { id: "composicao", label: "Unidade e composição", codes: ["base_nutricional", "composicao"] },
  { id: "nutricao", label: "Nutrição por 100 g", codes: ["nutricao", "nutricao_incompleta", "nutricao_loq"] },
  { id: "alergenicos", label: "Alergênicos", codes: ["alergenico_pendente"] },
  { id: "fontes", label: "Fontes", codes: ["fonte_pendente"] },
  { id: "fornecedores", label: "Fornecedores", codes: ["fornecedor"] },
  { id: "revisao", label: "Revisão", codes: [] },
  { id: "publicacao", label: "Publicação humana", codes: [] },
];

export function IngredientAssistant({
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
      ? 7
      : 6;
  const done = STEPS.filter(
    (step) => step.codes.length > 0 && !pending.some((item) => step.codes.includes(item.code)),
  ).length;
  const progress = completeness?.complete_dossier
    ? 100
    : Math.round((done / STEPS.length) * 100);
  const { setFlow, openAssistant } = useAssistant();
  useEffect(() => {
    setFlow({
      code: "panne.ingredient.assistant",
      title: "Assistente de ingrediente",
      steps: STEPS.map((step) => step.label),
      step: Math.max(0, currentIndex),
      note: "Concluir o dossiê sem apagar o que já foi digitado. Sem inteligência artificial.",
    });
    return () => setFlow(null);
  }, [setFlow, currentIndex]);
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
    <aside className="mentor-inline panel" role="dialog" aria-labelledby="ass-title">
      <h2 id="ass-title">Assistente de ingrediente</h2>
      <p>Objetivo: concluir o dossiê sem apagar o que já foi digitado. Sem inteligência artificial.</p>
      <div
        className="progress"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progresso do dossiê"
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
      <p>Próxima ação: {current?.label ?? "Revisar e publicar com decisão humana."}</p>
      <p>Bloqueios: {blocking.length ? blocking.map((item) => item.label).join(" ") : "nenhum"}</p>
      <p>Ajuda: ausência não é zero; abaixo do LQ não vira zero; publicação é humana.</p>
      <div>
        <button type="button" className="ghost" onClick={openAssistant}>
          Abrir no assistente
        </button>
        <button type="button" onClick={onMinimize}>
          Minimizar
        </button>
        <button type="button" onClick={onDismiss}>
          Dispensar ajuda
        </button>
      </div>
    </aside>
  );
}
