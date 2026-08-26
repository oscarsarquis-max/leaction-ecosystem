import { useEffect, useState } from "react";
import { useAssistant } from "../assistant/AssistantContext";

const BUY_STEPS = [
  "Verificar necessidade",
  "Revisar cobertura e lacunas",
  "Confirmar quantidade e embalagem",
  "Criar requisição",
  "Registrar cotações",
  "Comparar sem escolher automaticamente",
  "Obter aprovação humana",
  "Emitir pedido interno",
  "Receber",
  "Atualizar preço observado, se confirmado",
];

const COUNT_STEPS = [
  "Escolher local e data de corte",
  "Congelar o escopo",
  "Contar",
  "Revisar divergências",
  "Segunda contagem quando exigida",
  "Aprovar",
  "Gerar ajustes",
  "Fechar o inventário",
];

function Mentor({
  storageKey,
  title,
  steps,
  step,
}: {
  storageKey: string;
  title: string;
  steps: string[];
  step: number;
}) {
  const { setFlow, openAssistant } = useAssistant();
  const [mode, setMode] = useState<"aberto" | "minimizado" | "dispensado">("aberto");
  useEffect(() => {
    const stored = localStorage.getItem(storageKey);
    if (stored === "minimizado" || stored === "dispensado") setMode(stored);
  }, [storageKey]);
  useEffect(() => {
    setFlow({
      code: storageKey,
      title,
      steps,
      step,
      note: "Orientação apenas. O assistente não publica, não aprova e não movimenta estoque.",
    });
    return () => setFlow(null);
  }, [setFlow, storageKey, title, steps, step]);
  function persist(next: typeof mode) {
    setMode(next);
    localStorage.setItem(storageKey, next);
  }
  if (mode === "dispensado") return null;
  if (mode === "minimizado") {
    return (
      <p className="meta">
        <button type="button" className="ghost" onClick={() => persist("aberto")}>
          Reabrir assistente
        </button>
      </p>
    );
  }
  const progress = Math.round(((step + 1) / steps.length) * 100);
  return (
    <section className="mentor-inline panel" aria-labelledby={storageKey}>
      <h2 id={storageKey}>{title}</h2>
      <p>Assistente determinístico. A IA não movimenta, não ajusta, não aprova e não compra.</p>
      <div
        className="progress"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progresso do assistente"
      >
        <span style={{ width: `${progress}%` }} />
      </div>
      <ol>
        {steps.map((label, index) => (
          <li key={label} aria-current={index === step ? "step" : undefined}>
            {label}
          </li>
        ))}
      </ol>
      <p>
        <button type="button" className="ghost" onClick={openAssistant}>
          Abrir no assistente
        </button>{" "}
        <button type="button" className="ghost" onClick={() => persist("minimizado")}>
          Minimizar
        </button>{" "}
        <button type="button" className="ghost" onClick={() => persist("dispensado")}>
          Dispensar
        </button>
      </p>
    </section>
  );
}

export function PurchaseMentor({ step }: { step: number }) {
  return (
    <Mentor
      storageKey="panne.procurement.mentor"
      title="Assistente de reposição e compra"
      steps={BUY_STEPS}
      step={step}
    />
  );
}

export function CountMentor({ step }: { step: number }) {
  return (
    <Mentor
      storageKey="panne.inventory.count.mentor"
      title="Assistente de inventário"
      steps={COUNT_STEPS}
      step={step}
    />
  );
}
