import { useId, useState } from "react";

function TooltipDefinicao({ id, pos, explicacao, importancia }) {
  return (
    <div
      id={id}
      role="tooltip"
      className="pointer-events-none fixed z-[200] w-72 max-w-[calc(100vw-2rem)] rounded-lg bg-gray-800 px-3 py-2 text-left text-xs font-normal leading-relaxed text-white shadow-xl"
      style={{ top: pos.top, left: pos.left }}
    >
      {explicacao && (
        <>
          <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-brand-laranja">
            Definição
          </span>
          <p className="whitespace-normal">{explicacao}</p>
        </>
      )}
      {importancia && (
        <p
          className={`whitespace-normal text-[11px] text-white/90 ${
            explicacao ? "mt-2 border-t border-white/10 pt-2" : ""
          }`}
        >
          <span className="font-semibold uppercase tracking-wide text-brand-verde">
            Importância:{" "}
          </span>
          {importancia}
        </p>
      )}
    </div>
  );
}

export function IndicadorNomeComDefinicao({
  nome,
  explicacao,
  importancia,
  className = "",
}) {
  const [pos, setPos] = useState(null);
  const tooltipId = useId();
  const temDefinicao = Boolean(explicacao || importancia);

  function mostrarTooltip(event) {
    if (!temDefinicao) {
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    const larguraTooltip = 288;
    const margem = 16;

    setPos({
      top: rect.bottom + 6,
      left: Math.max(margem, Math.min(rect.left, window.innerWidth - larguraTooltip - margem)),
    });
  }

  function ocultarTooltip() {
    setPos(null);
  }

  if (!nome) {
    return <span className={className}>—</span>;
  }

  return (
    <>
      <span
        className={`${className} ${
          temDefinicao ? "cursor-help border-b border-dotted border-brand-cinza/40" : ""
        }`}
        onMouseEnter={mostrarTooltip}
        onMouseLeave={ocultarTooltip}
        onFocus={mostrarTooltip}
        onBlur={ocultarTooltip}
        tabIndex={temDefinicao ? 0 : undefined}
        aria-describedby={temDefinicao && pos ? tooltipId : undefined}
      >
        {nome}
      </span>
      {pos && temDefinicao && (
        <TooltipDefinicao
          id={tooltipId}
          pos={pos}
          explicacao={explicacao}
          importancia={importancia}
        />
      )}
    </>
  );
}

export function buildDefinicoesIndicadores(metricas = []) {
  const map = {};

  metricas.forEach((metrica) => {
    const cod = metrica.cod_indicador || metrica.indicador?.cod_indicador;
    if (!cod || map[cod]) {
      return;
    }

    map[cod] = {
      explicacao:
        metrica.explicacao ??
        metrica.indicador?.explicacao ??
        metrica.descricao?.explicacao ??
        null,
      importancia:
        metrica.importancia ??
        metrica.indicador?.importancia ??
        metrica.descricao?.importancia ??
        null,
    };
  });

  return map;
}

export function resolverDefinicaoIndicador(indicador, definicoes = {}) {
  if (!indicador) {
    return { explicacao: null, importancia: null };
  }

  const codigo = indicador.cod_indicador;
  const porCodigo = codigo && definicoes[codigo];

  return {
    explicacao: indicador.explicacao ?? porCodigo?.explicacao ?? null,
    importancia: indicador.importancia ?? porCodigo?.importancia ?? null,
  };
}
