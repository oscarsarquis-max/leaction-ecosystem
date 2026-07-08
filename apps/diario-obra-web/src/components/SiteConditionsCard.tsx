import BigSwitch from './ui/BigSwitch';
import YesNoToggle from './ui/YesNoToggle';

interface Props {
  delayWaitingMaterial: boolean;
  delayRework: boolean;
  delayLackOfFront: boolean;
  endShiftClean: boolean | null;
  endShiftToolsStored: boolean | null;
  endShiftLooseMaterials: boolean | null;
  onDelayWaitingMaterial: (v: boolean) => void;
  onDelayRework: (v: boolean) => void;
  onDelayLackOfFront: (v: boolean) => void;
  onEndShiftClean: (v: boolean) => void;
  onEndShiftToolsStored: (v: boolean) => void;
  onEndShiftLooseMaterials: (v: boolean) => void;
  disabled?: boolean;
}

export default function SiteConditionsCard({
  delayWaitingMaterial,
  delayRework,
  delayLackOfFront,
  endShiftClean,
  endShiftToolsStored,
  endShiftLooseMaterials,
  onDelayWaitingMaterial,
  onDelayRework,
  onDelayLackOfFront,
  onEndShiftClean,
  onEndShiftToolsStored,
  onEndShiftLooseMaterials,
  disabled = false,
}: Props) {
  return (
    <section className="mt-6 rounded-2xl border-2 border-amber-200 bg-amber-50/60 p-4 shadow-sm">
      <h3 className="text-base font-bold text-amber-950">Atrasos e Condições do Canteiro</h3>
      <p className="mt-1 text-sm text-amber-900/80">
        Marque o que aconteceu hoje no canteiro — linguagem direta, sem enrolação.
      </p>

      <div className="mt-4 space-y-3">
        <BigSwitch
          label="Equipe ficou parada esperando material?"
          checked={delayWaitingMaterial}
          onChange={onDelayWaitingMaterial}
          disabled={disabled}
        />
        <BigSwitch
          label="Tivemos que refazer algum serviço hoje (Retrabalho)?"
          checked={delayRework}
          onChange={onDelayRework}
          disabled={disabled}
        />
        <BigSwitch
          label="Faltou frente de trabalho?"
          checked={delayLackOfFront}
          onChange={onDelayLackOfFront}
          disabled={disabled}
        />
      </div>

      <div className="my-5 border-t border-amber-300/80" />
      <p className="text-sm font-bold uppercase tracking-wide text-amber-950">
        Fechamento do Canteiro
      </p>
      <p className="mt-1 text-xs text-amber-900/70">Obrigatório para assinar o RDO.</p>

      <div className="mt-3 space-y-3">
        <YesNoToggle
          label="O canteiro ficou limpo e organizado?"
          value={endShiftClean}
          onChange={onEndShiftClean}
          disabled={disabled}
        />
        <YesNoToggle
          label="As ferramentas foram recolhidas?"
          value={endShiftToolsStored}
          onChange={onEndShiftToolsStored}
          disabled={disabled}
        />
        <YesNoToggle
          label="Ficou material solto no tempo?"
          value={endShiftLooseMaterials}
          onChange={onEndShiftLooseMaterials}
          disabled={disabled}
        />
      </div>
    </section>
  );
}

export function endShiftComplete(
  clean: boolean | null,
  tools: boolean | null,
  loose: boolean | null,
): boolean {
  return clean !== null && tools !== null && loose !== null;
}
