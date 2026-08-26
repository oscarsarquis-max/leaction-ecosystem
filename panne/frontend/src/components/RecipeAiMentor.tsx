import { useEffect } from "react";
import { useAssistant } from "../assistant/AssistantContext";

const STEPS = [
  "Finalidade",
  "Objetivo e restrições",
  "Receita-base",
  "Fontes",
  "Grounding",
  "Geração",
  "Validação",
  "Comparação",
  "Revisão",
  "Rascunho criado",
];

export function RecipeAiMentor({
  step,
  minimized,
  onMinimize,
  onResume,
  onCancel,
}: {
  step: number;
  minimized?: boolean;
  onMinimize: () => void;
  onResume: () => void;
  onCancel: () => void;
}) {
  const progress = Math.round(((step + 1) / STEPS.length) * 100);
  const { setFlow, openAssistant } = useAssistant();
  useEffect(() => {
    setFlow({
      code: "panne.recipe.ai.mentor",
      title: "Mentoria do assistente",
      steps: STEPS,
      step,
      note: "A IA não publica, não aprova e não cria ingrediente.",
    });
    return () => setFlow(null);
  }, [setFlow, step]);
  if (minimized) {
    return (
      <p className="meta">
        <button type="button" className="ghost" onClick={onResume}>
          Retomar mentoria
        </button>
      </p>
    );
  }
  return (
    <div className="mentor-inline panel" role="dialog" aria-labelledby="ai-mentor-title">
      <h2 id="ai-mentor-title">Mentoria do assistente</h2>
      <p>
        <span className="badge">Assistido por IA</span> A IA não publica, não aprova e não cria
        ingrediente.
      </p>
      <div
        className="progress"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progresso da mentoria"
      >
        <span style={{ width: `${progress}%` }} />
      </div>
      <ol>
        {STEPS.map((label, index) => (
          <li key={label} aria-current={index === step ? "step" : undefined}>
            {label}
          </li>
        ))}
      </ol>
      <p>Etapa atual: {STEPS[step]}</p>
      <div>
        <button type="button" className="ghost" onClick={openAssistant}>
          Abrir no assistente
        </button>
        <button type="button" onClick={onMinimize}>
          Minimizar
        </button>
        <button type="button" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
