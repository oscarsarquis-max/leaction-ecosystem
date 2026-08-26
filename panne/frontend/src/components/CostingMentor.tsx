import { useEffect, useState } from "react";
import { useAssistant } from "../assistant/AssistantContext";

const STEPS = [
  "Escolher produto, formulação ou ordem",
  "Selecionar tipo de custo",
  "Confirmar política e data",
  "Verificar preços dos ingredientes",
  "Revisar premissas adicionais",
  "Verificar rendimento",
  "Calcular",
  "Revisar lacunas e composição",
  "Simular preço",
  "Revisar e, com permissão, publicar",
];

const KEY = "panne.costing.mentor";

export function CostingMentor({ step, pending }: { step: number; pending: string[] }) {
  const { setFlow, openAssistant } = useAssistant();
  const [mode, setMode] = useState<"aberto" | "minimizado" | "dispensado">("aberto");
  useEffect(() => {
    const stored = localStorage.getItem(KEY);
    if (stored === "minimizado" || stored === "dispensado") setMode(stored);
  }, []);
  const pendingNote = pending.length ? pending.join(" · ") : "nenhuma listada";
  useEffect(() => {
    setFlow({
      code: KEY,
      title: "Assistente de custos e preços",
      steps: STEPS,
      step,
      note: `Pendências: ${pendingNote}. O assistente não publica preço.`,
    });
    return () => setFlow(null);
  }, [setFlow, step, pendingNote]);
  function persist(next: typeof mode) {
    setMode(next);
    localStorage.setItem(KEY, next);
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
  const progress = Math.round(((step + 1) / STEPS.length) * 100);
  return (
    <div className="mentor-inline panel" role="dialog" aria-labelledby="cost-mentor">
      <h2 id="cost-mentor">Assistente de custos e preços</h2>
      <p>
        Markup incide sobre o custo. Margem bruta incide sobre o preço. Margem de contribuição
        desconta custos e despesas variáveis. Não são sinônimos.
      </p>
      <div
        className="progress"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progresso do custeio"
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
      <p>Próxima ação: {STEPS[step]}.</p>
      <p>Pendências: {pending.length ? pending.join(" · ") : "nenhuma listada"}</p>
      <p className="meta">Gamificação educativa coletiva: completude e qualidade dos dados. Sem ranking individual.</p>
      <div>
        <button type="button" className="ghost" onClick={openAssistant}>
          Abrir no assistente
        </button>
        <button type="button" onClick={() => persist("minimizado")}>
          Minimizar
        </button>
        <button type="button" onClick={() => persist("dispensado")}>
          Dispensar ajuda
        </button>
      </div>
    </div>
  );
}
