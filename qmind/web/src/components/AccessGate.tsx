type Props = {
  status: "anonymous" | "invalid_session";
  onLogin: () => void;
};

/**
 * Primeira tela do produto — obrigatória antes de qualquer conteúdo da organização.
 * Linguagem pt-BR; marca dominante; CTA único.
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
            ? "Sua sessão expirou. Entre de novo para retomar as avaliações da sua organização."
            : "Espaço da consultoria e da organização cliente. O QMind conduz o percurso da preparação ao relatório — sem misturar dados entre empresas."}
        </p>

        <ul className="qmind-login__points" aria-label="O que acontece depois de entrar">
          <li>Escolher a organização ativa</li>
          <li>Ver o mapa do percurso e a próxima ação</li>
          <li>Continuar a avaliação em linguagem de negócio</li>
        </ul>

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
          <span className="qmind-login__build">UI access-gate-2026-08-06a</span>
        </p>
      </div>
    </div>
  );
}
