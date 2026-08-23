import { useEffect, useState } from "react";

const STEPS = [
  "Identificar produto",
  "Confirmar mercado e canal",
  "Descrever a embalagem",
  "Confirmar categoria e porção",
  "Verificar dados nutricionais",
  "Revisar ingredientes",
  "Revisar advertências",
  "Preencher informações obrigatórias",
  "Executar avaliação",
  "Revisar achados",
  "Gerar candidato",
];

const KEY = "panne.labeling.mentor";

export function LabelingMentor({
  step,
  pending,
}: {
  step: number;
  pending: string[];
}) {
  const [mode, setMode] = useState<"aberto" | "minimizado" | "dispensado">("aberto");
  useEffect(() => {
    const stored = localStorage.getItem(KEY);
    if (stored === "minimizado" || stored === "dispensado") setMode(stored);
  }, []);
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
    <div className="drawer-assist panel" role="dialog" aria-labelledby="lab-mentor">
      <h2 id="lab-mentor">Assistente de rotulagem</h2>
      <p>Guia determinístico. Não declara aprovação nem conformidade.</p>
      <div
        className="progress"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progresso da rotulagem"
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
      <div>
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
