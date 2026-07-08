import { Info, Lightbulb } from "lucide-react";

function MetricTooltip({ icon: Icon, label, text, hoverClass }) {
  if (!text) {
    return null;
  }

  return (
    <button
      type="button"
      className={`group relative rounded-md p-1 text-gray-400 transition-colors ${hoverClass}`}
      aria-label={label}
    >
      <Icon className="h-4 w-4" strokeWidth={2} />

      <span
        role="tooltip"
        className="pointer-events-none invisible absolute bottom-full right-0 z-50 mb-2 w-64 rounded-lg bg-gray-800 px-3 py-2 text-left text-xs font-normal leading-relaxed text-white opacity-0 shadow-xl transition-all duration-150 group-hover:visible group-hover:opacity-100 sm:w-72"
      >
        <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-brand-laranja">
          {label}
        </span>
        <span className="block whitespace-normal">{text}</span>
        <span
          className="absolute -bottom-1 right-3 h-2 w-2 rotate-45 bg-gray-800"
          aria-hidden="true"
        />
      </span>
    </button>
  );
}

export function IndicadorTooltips({ explicacao, importancia }) {
  if (!explicacao && !importancia) {
    return null;
  }

  return (
    <div className="relative z-50 flex shrink-0 items-center gap-1">
      <MetricTooltip
        icon={Info}
        label="Explicação"
        text={explicacao}
        hoverClass="hover:text-brand-laranja"
      />
      <MetricTooltip
        icon={Lightbulb}
        label="Importância"
        text={importancia}
        hoverClass="hover:text-brand-verde"
      />
    </div>
  );
}
