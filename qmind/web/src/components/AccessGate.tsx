type Props = {
  status: "anonymous" | "invalid_session";
  onLogin: () => void;
};

/**
 * Primeira tela do produto — obrigatória antes de qualquer conteúdo.
 * Só identidade + CTA. Sem tutorial de jornada (isso fica depois do login).
 */
export function AccessGate({ status, onLogin }: Props) {
  const expired = status === "invalid_session";

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

        <h1 className="qmind-login__title">Entrar no QMind</h1>

        <p className="qmind-login__text">
          {expired
            ? "Sua sessão expirou. Entre de novo para retomar o trabalho na sua organização."
            : "Consultoria de qualidade para organizações. Padrão de auto-consultoria, gerenciamento e controle da qualidade."}
        </p>

        <button
          type="button"
          onClick={onLogin}
          className="qmind-login__cta"
          data-testid="login-cta"
          autoFocus
        >
          Entrar
        </button>

        <p className="qmind-login__meta">
          Acesso por convite · sessão segura
          <br />
          <span className="qmind-login__build">UI access-gate-2026-08-06d</span>
        </p>
      </div>
    </div>
  );
}
