import { forwardRef, useEffect, useId, useImperativeHandle, useMemo, useRef, useState } from "react";

const LIMITE_RESULTADOS = 50;

function normalizarTexto(valor) {
  return String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function rotuloColaborador(colaborador) {
  if (!colaborador) {
    return "";
  }

  if (colaborador.label) {
    return colaborador.label;
  }

  const nome = colaborador.nome || "Colaborador";
  const matricula = colaborador.matricula ? ` (${colaborador.matricula})` : "";
  return `${nome}${matricula}`;
}

function colaboradorCoincide(colaborador, termo) {
  const termoNormalizado = normalizarTexto(termo);
  if (!termoNormalizado) {
    return true;
  }

  const campos = [
    colaborador.nome,
    colaborador.matricula,
    colaborador.funcao,
    colaborador.papel,
    colaborador.subpapel,
    colaborador.codsetor,
    rotuloColaborador(colaborador),
  ];

  return campos.some((campo) => normalizarTexto(campo).includes(termoNormalizado));
}

function textoCorrespondeSelecao(colaborador, termo) {
  if (!colaborador) {
    return false;
  }

  const termoNormalizado = normalizarTexto(termo);
  if (!termoNormalizado) {
    return false;
  }

  return [
    colaborador.matricula,
    colaborador.nome,
    rotuloColaborador(colaborador),
  ].some((campo) => normalizarTexto(campo) === termoNormalizado);
}

const ColaboradorAutocomplete = forwardRef(function ColaboradorAutocomplete(
  {
    colaboradores = [],
    valorSelecionado = "",
    onSelect,
    onClear,
    onInvalidateSelection,
    disabled = false,
    placeholder = "Digite nome ou matrícula...",
  },
  ref
) {
  const listboxId = useId();
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  const [termo, setTermo] = useState("");
  const [aberto, setAberto] = useState(false);
  const [indiceAtivo, setIndiceAtivo] = useState(-1);

  const colaboradorSelecionado = useMemo(
    () => colaboradores.find((item) => item.matricula === valorSelecionado) ?? null,
    [colaboradores, valorSelecionado]
  );

  useImperativeHandle(ref, () => ({
    getTermoBusca: () => String(termo || "").trim(),
  }));

  useEffect(() => {
    if (colaboradorSelecionado) {
      setTermo(rotuloColaborador(colaboradorSelecionado));
      return;
    }

    if (!valorSelecionado) {
      setTermo("");
    }
  }, [colaboradorSelecionado, valorSelecionado]);

  const resultados = useMemo(() => {
    const filtrados = colaboradores.filter((item) => colaboradorCoincide(item, termo));
    return filtrados.slice(0, LIMITE_RESULTADOS);
  }, [colaboradores, termo]);

  useEffect(() => {
    function handleClickFora(event) {
      if (!containerRef.current?.contains(event.target)) {
        setAberto(false);
        setIndiceAtivo(-1);

        if (colaboradorSelecionado) {
          setTermo(rotuloColaborador(colaboradorSelecionado));
        }
      }
    }

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, [colaboradorSelecionado]);

  const handleChange = (event) => {
    const novoTermo = event.target.value;
    setTermo(novoTermo);
    setAberto(true);
    setIndiceAtivo(-1);

    if (!novoTermo.trim()) {
      onClear?.();
      return;
    }

    if (colaboradorSelecionado && !textoCorrespondeSelecao(colaboradorSelecionado, novoTermo)) {
      onInvalidateSelection?.();
    }
  };

  const handleSelect = (colaborador) => {
    setTermo(rotuloColaborador(colaborador));
    setAberto(false);
    setIndiceAtivo(-1);
    onSelect?.(colaborador);
  };

  const handleKeyDown = (event) => {
    if (!aberto && (event.key === "ArrowDown" || event.key === "Enter")) {
      setAberto(true);
      return;
    }

    if (event.key === "Escape") {
      setAberto(false);
      setIndiceAtivo(-1);
      if (colaboradorSelecionado) {
        setTermo(rotuloColaborador(colaboradorSelecionado));
      }
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIndiceAtivo((indice) => Math.min(indice + 1, resultados.length - 1));
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setIndiceAtivo((indice) => Math.max(indice - 1, 0));
      return;
    }

    if (event.key === "Enter" && indiceAtivo >= 0 && resultados[indiceAtivo]) {
      event.preventDefault();
      handleSelect(resultados[indiceAtivo]);
      return;
    }

    if (event.key === "Enter" && resultados.length === 1) {
      event.preventDefault();
      handleSelect(resultados[0]);
    }
  };

  const exibirLista = aberto && !disabled;
  const termoVazio = !termo.trim();

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={exibirLista}
          aria-controls={listboxId}
          aria-autocomplete="list"
          autoComplete="off"
          disabled={disabled}
          value={termo}
          onChange={handleChange}
          onFocus={() => setAberto(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 pr-9 text-sm text-brand-cinza focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-verde/20 disabled:cursor-not-allowed disabled:bg-gray-50"
        />

        {termo && !disabled && (
          <button
            type="button"
            onClick={() => {
              setTermo("");
              setAberto(false);
              setIndiceAtivo(-1);
              onClear?.();
              inputRef.current?.focus();
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-brand-cinza/50 transition hover:bg-gray-100 hover:text-brand-cinza"
            aria-label="Limpar colaborador selecionado"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {exibirLista && (
        <ul
          id={listboxId}
          role="listbox"
          className="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
        >
          {termoVazio && (
            <li className="px-3 py-2 text-xs text-brand-cinza/70">
              Digite para filtrar entre {colaboradores.length.toLocaleString("pt-BR")} colaboradores
            </li>
          )}

          {resultados.length === 0 ? (
            <li className="px-3 py-3 text-sm text-brand-cinza/70">
              Nenhum colaborador encontrado para &quot;{termo}&quot;.
            </li>
          ) : (
            resultados.map((colaborador, indice) => {
              const ativo = indice === indiceAtivo;
              return (
                <li key={colaborador.id_colaborador ?? colaborador.matricula} role="option">
                  <button
                    type="button"
                    aria-selected={ativo}
                    onMouseEnter={() => setIndiceAtivo(indice)}
                    onClick={() => handleSelect(colaborador)}
                    className={`flex w-full flex-col gap-0.5 px-3 py-2 text-left transition ${
                      ativo ? "bg-brand-verde/10 text-brand-verde" : "text-brand-cinza hover:bg-gray-50"
                    }`}
                  >
                    <span className="text-sm font-medium">{colaborador.nome}</span>
                    <span className="text-xs text-brand-cinza/70">
                      {colaborador.matricula}
                      {colaborador.funcao ? ` · ${colaborador.funcao}` : ""}
                    </span>
                  </button>
                </li>
              );
            })
          )}

          {resultados.length === LIMITE_RESULTADOS && (
            <li className="border-t border-gray-100 px-3 py-2 text-xs text-brand-cinza/60">
              Mostrando os primeiros {LIMITE_RESULTADOS} resultados. Refine a busca.
            </li>
          )}
        </ul>
      )}
    </div>
  );
});

export default ColaboradorAutocomplete;
