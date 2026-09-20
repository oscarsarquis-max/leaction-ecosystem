import { OFFICIAL_LOGO } from "../features/bread-builder/catalog";

type LogoProps = {
  href: string;
};

export function Logo({ href }: LogoProps) {
  return (
    <a className="brand" href={href}>
      <span className="logo-window">
        <img src={OFFICIAL_LOGO} alt="Loja de Pães — Boulangerie" />
      </span>
    </a>
  );
}
