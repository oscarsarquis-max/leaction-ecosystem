import { getConfig } from "@/config/env";

type Props = {
  status: "anonymous" | "invalid_session";
  onLogin: () => void;
};

/**
 * Tela de entrada explícita — nunca autentica sozinha.
 * Em AUTH_MODE=dev o CTA deixa claro que é usuário de desenvolvimento.
 */
export function AccessGate({ status, onLogin }: Props) {
  const expired = status === "invalid_session";
  const isDevAuth = getConfig().authMode === "dev";

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
            : isDevAuth
              ? "Ambiente local: a autenticação só começa quando você escolher entrar como usuário de desenvolvimento. Em produção o acesso é pelo Cognito e pela membership."
              : "Acesso por convite. Você entra com Cognito; só visualiza organizações em que possui membership ativa."}
        </p>

        <button
          type="button"
          onClick={onLogin}
          className="qmind-login__cta"
          data-testid="login-cta"
        >
          {isDevAuth
            ? "Entrar como usuário de desenvolvimento"
            : "Entrar com Cognito"}
        </button>

        <p className="qmind-login__meta">
          {isDevAuth
            ? "Modo desenvolvimento · sessão apenas em memória · clique obrigatório"
            : "Acesso por convite · sessão segura Cognito"}
        </p>
      </div>
    </div>
  );
}
