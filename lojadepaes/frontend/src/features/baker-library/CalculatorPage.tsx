import { useMemo, useState, type FormEvent } from "react";
import { DeepenPanel } from "./DeepenPanel";
import { computeFormula, type CalculatorResult } from "./libraryApi";

const MODES = [
  { id: "from_flour", label: "A partir da farinha" },
  { id: "scale_flour", label: "Escalar para outra farinha" },
  { id: "scale_dough", label: "Escalar para um peso de massa" },
  { id: "convert_levain", label: "Converter PFF e peso do levain" },
] as const;

export function CalculatorPage() {
  const [mode, setMode] = useState<(typeof MODES)[number]["id"]>("from_flour");
  const [flour, setFlour] = useState("1000");
  const [targetFlour, setTargetFlour] = useState("500");
  const [targetDough, setTargetDough] = useState("860");
  const [hydration, setHydration] = useState("70");
  const [salt, setSalt] = useState("2");
  const [pff, setPff] = useState("20");
  const [levainWeight, setLevainWeight] = useState("400");
  const [levainHydration, setLevainHydration] = useState("100");
  const [levainMode, setLevainMode] = useState<"pff" | "weight">("pff");
  const [result, setResult] = useState<CalculatorResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const payload = useMemo(
    () => ({
      mode,
      flour_g: Number(flour),
      target_flour_g: Number(targetFlour),
      target_dough_g: Number(targetDough),
      hydration_pct: Number(hydration),
      salt_pct: Number(salt),
      preferment_flour_pct: Number(pff),
      levain_weight_g: Number(levainWeight),
      levain_hydration_pct: Number(levainHydration),
      levain_mode: levainMode,
    }),
    [mode, flour, targetFlour, targetDough, hydration, salt, pff, levainWeight, levainHydration, levainMode],
  );

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(await computeFormula(payload));
    } catch (reason: unknown) {
      const detail = reason && typeof reason === "object" && "message" in reason ? String((reason as { message: string }).message) : "";
      setError(detail || "Não foi possível calcular agora.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="library-page library-calc">
      <p className="eyebrow">CALCULADORA DO PADEIRO</p>
      <h1>Porcentagem de padeiro</h1>
      <p>
        Contas determinísticas, sem modelo. A farinha total é 100%. O levain já está dentro dessa
        farinha e da hidratação — não some o potinho outra vez.
      </p>
      <form className="library-calc-form" onSubmit={(event) => void onSubmit(event)}>
        <fieldset>
          <legend>Modo</legend>
          {MODES.map((item) => (
            <label key={item.id}>
              <input
                type="radio"
                name="mode"
                checked={mode === item.id}
                onChange={() => setMode(item.id)}
              />
              {item.label}
            </label>
          ))}
        </fieldset>
        <label>
          Farinha total (g)
          <input value={flour} onChange={(event) => setFlour(event.target.value)} inputMode="decimal" />
        </label>
        {mode === "scale_flour" ? (
          <label>
            Nova farinha (g)
            <input value={targetFlour} onChange={(event) => setTargetFlour(event.target.value)} inputMode="decimal" />
          </label>
        ) : null}
        {mode === "scale_dough" ? (
          <label>
            Massa alvo (g)
            <input value={targetDough} onChange={(event) => setTargetDough(event.target.value)} inputMode="decimal" />
          </label>
        ) : null}
        <label>
          Hidratação (%)
          <input value={hydration} onChange={(event) => setHydration(event.target.value)} inputMode="decimal" />
        </label>
        <label>
          Sal (%)
          <input value={salt} onChange={(event) => setSalt(event.target.value)} inputMode="decimal" />
        </label>
        <label>
          Hidratação do levain (%)
          <input value={levainHydration} onChange={(event) => setLevainHydration(event.target.value)} inputMode="decimal" />
        </label>
        <fieldset>
          <legend>Como entra o levain</legend>
          <label>
            <input type="radio" name="levain" checked={levainMode === "pff"} onChange={() => setLevainMode("pff")} />
            Farinha prefermentada (PFF)
          </label>
          <label>
            <input type="radio" name="levain" checked={levainMode === "weight"} onChange={() => setLevainMode("weight")} />
            Peso do levain
          </label>
        </fieldset>
        {levainMode === "pff" ? (
          <label>
            PFF (%)
            <input value={pff} onChange={(event) => setPff(event.target.value)} inputMode="decimal" />
          </label>
        ) : (
          <label>
            Peso do levain (g)
            <input value={levainWeight} onChange={(event) => setLevainWeight(event.target.value)} inputMode="decimal" />
          </label>
        )}
        <button type="submit" className="primary" disabled={busy}>
          Calcular
        </button>
      </form>
      {error ? <p role="alert">{error}</p> : null}
      {result ? (
        <section className="library-calc-result" aria-live="polite">
          <h2>Resultado</h2>
          <p>
            Massa final: <strong>{result.totals.dough_g} g</strong>. Mistura: {result.final_mix.flour_g} g de
            farinha, {result.final_mix.water_g} g de água, {result.final_mix.salt_g} g de sal e{" "}
            {result.final_mix.levain_g} g de levain.
          </p>
          <p>
            Levain: {result.levain.flour_g} g de farinha + {result.levain.water_g} g de água (PFF{" "}
            {result.preferment_flour_pct}%).
          </p>
          {result.notes.map((note) => (
            <p key={note}>{note}</p>
          ))}
        </section>
      ) : null}
      <p>
        <a href="/biblioteca/o-comeco">O começo</a>
        {" · "}
        <a href="/biblioteca/as-maos-na-massa">As mãos na massa</a>
      </p>
      <DeepenPanel
        articleId="calculadora"
        articleVersion={1}
        calculatorMode={mode}
        returnTo="/biblioteca/calculadora"
      />
    </main>
  );
}
