type Props = {
  status: "anonymous" | "invalid_session";
  onLogin: () => void;
};

/**
 * Login limpo (design system): fundo #F8FAFC, card branco, logo PNG centralizada, CTA largo.
 * Sem gradientes. Marcador de build no rodapé para confirmar deploy.
 */
export function AccessGate({ status, onLogin }: Props) {
  const line =
    status === "invalid_session"
      ? "Sua sessão expirou. Entre novamente para retomar de onde parou."
      : "Entre para acessar as avaliações da sua organização. O QMind conduz o percurso passo a passo.";

  return (
    <div className="qmind-login" data-testid="access-gate">
      <div className="qmind-login__card">
        <img
          src="/qmind-logo-light.png"
          alt="QMind"
          width={360}
          height={148}
          decoding="async"
          className="qmind-login__logo"
        />

        <p className="qmind-login__text">{line}</p>

        <button
          type="button"
          onClick={onLogin}
          className="qmind-login__cta"
          data-testid="login-cta"
        >
          Entrar
        </button>

        <p className="qmind-login__meta">
          Acesso por convite · sessão segura
          <br />
          <span className="qmind-login__build">UI access-gate-2026-08-05c</span>
        </p>
      </div>
    </div>
  );
}
