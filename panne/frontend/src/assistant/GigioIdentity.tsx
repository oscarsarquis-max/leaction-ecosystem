/**
 * Identidade pública do orientador da Panne.
 * Identificadores técnicos internos (assistant.*) permanecem; a superfície mostra Gigio.
 */
import gigioAvatar from "../../images/avatar_gigio.png";

export const GIGIO_NAME = "Gigio";
export const GIGIO_ALT = "Gigio, assistente da Panne";
export const GIGIO_AVATAR_SRC = gigioAvatar;

type GigioIdentityProps = {
  /** Texto sob o nome (orientação curta). */
  caption?: string | null;
  /** Tamanho visual do avatar. */
  size?: "sm" | "md" | "lg";
  /** Classe extra no wrapper. */
  className?: string;
  /** Esconde o nome quando o contexto já o anunciou. */
  hideName?: boolean;
};

export function GigioIdentity({
  caption = null,
  size = "md",
  className = "",
  hideName = false,
}: GigioIdentityProps) {
  return (
    <div className={`gigio-identity gigio-identity--${size} ${className}`.trim()}>
      <img
        className="gigio-identity__avatar"
        src={GIGIO_AVATAR_SRC}
        alt={GIGIO_ALT}
        width={size === "lg" ? 96 : size === "sm" ? 40 : 64}
        height={size === "lg" ? 96 : size === "sm" ? 40 : 64}
        decoding="async"
      />
      <div className="gigio-identity__copy">
        {hideName ? null : <p className="gigio-identity__name">{GIGIO_NAME}</p>}
        {caption ? <p className="gigio-identity__caption">{caption}</p> : null}
      </div>
    </div>
  );
}
