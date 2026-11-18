type Opcao<T extends string> = { valor: T; rotulo: string };

type Props<T extends string> = {
  rotulo: string;
  opcoes: Opcao<T>[];
  valor: T;
  onChange: (valor: T) => void;
};

/** Filtros em "chips": um grupo de botões em que um está marcado. */
export function Chips<T extends string>({ rotulo, opcoes, valor, onChange }: Props<T>) {
  return (
    <div className="gestao-chips" role="group" aria-label={rotulo}>
      {opcoes.map((opcao) => (
        <button
          key={opcao.valor}
          type="button"
          className={opcao.valor === valor ? "chip-filtro on" : "chip-filtro"}
          aria-pressed={opcao.valor === valor}
          onClick={() => onChange(opcao.valor)}
        >
          {opcao.rotulo}
        </button>
      ))}
    </div>
  );
}
