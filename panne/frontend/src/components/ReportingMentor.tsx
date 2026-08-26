import { useEffect, useState } from "react";
import { useAssistant } from "../assistant/AssistantContext";

const STEPS = [
  "Escolher o objetivo da análise",
  "Escolher o relatório",
  "Definir período e filtros",
  "Verificar cobertura",
  "Interpretar indicadores",
  "Abrir detalhes",
  "Comparar períodos ou referências",
  "Salvar visão",
  "Criar snapshot",
  "Exportar ou imprimir",
];

const KEY = "panne.reporting.mentor";

export function ReportingMentor({ step, notes }: { step: number; notes: string[] }) {
  const { setFlow, openAssistant } = useAssistant();
  const [mode, setMode] = useState<"aberto" | "minimizado" | "dispensado">("aberto");
  useEffect(() => {
    const stored = localStorage.getItem(KEY);
    if (stored === "minimizado" || stored === "dispensado") setMode(stored);
  }, []);
  const notesNote = notes.join(" ") || "Ausência não é zero. O assistente não exporta sozinho.";
  useEffect(() => {
    setFlow({
      code: KEY,
      title: "Assistente de análise",
      steps: STEPS,
      step,
      note: notesNote,
    });
    return () => setFlow(null);
  }, [setFlow, step, notesNote]);
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
  return (
    <section className="mentor-inline panel" aria-labelledby="rep-mentor">
      <h2 id="rep-mentor">Assistente de análise</h2>
      <ol>
        {STEPS.map((item, index) => (
          <li key={item}>
            {index === step ? <strong>{item}</strong> : item}
          </li>
        ))}
      </ol>
      <p>Ausência não é zero. Percentual sem denominador fica indisponível, não 0%.</p>
      <p>Markup não é margem bruta. Margem bruta não é contribuição. Margem estimada não é venda.</p>
      <p>Variação não é causa. Este painel não é tempo real: use a data de corte.</p>
      {notes.length ? (
        <ul>
          {notes.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
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
