import logo from "../assets/logo-loja-de-paes-transparente.png";

type Props = {
  /** Altura em px: ~40 na lateral, ~32 na barra do celular, ~72 no login. */
  altura: number;
  className?: string;
};

/** Logo da Loja de Pães. O arquivo original não é alterado; esta é a versão sem fundo creme. */
export function Marca({ altura, className }: Props) {
  return (
    <img
      className={["gestao-logo", className].filter(Boolean).join(" ")}
      src={logo}
      alt="Loja de Pães"
      height={altura}
      style={{ height: altura, width: "auto" }}
      draggable={false}
    />
  );
}
