import type { MouseEventHandler } from "react";
import { OFFICIAL_LOGO } from "../features/bread-builder/catalog";

type LogoProps = {
  href: string;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
};

export function Logo({ href, onClick }: LogoProps) {
  return (
    <a className="brand" href={href} onClick={onClick}>
      <span className="logo-window">
        <img src={OFFICIAL_LOGO} alt="Loja de Pães — Boulangerie" />
      </span>
    </a>
  );
}
