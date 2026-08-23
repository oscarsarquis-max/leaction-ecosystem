import { useState } from "react";
import { useNavigate } from "react-router-dom";
import logoCompleto from "../../images/aprovados/horizontal-claro.png";
import { useAuth } from "../auth/AuthContext";
import { config } from "../config";

export function LoginPage() {
  const { login, provider } = useAuth();
  const navigate = useNavigate();
  const [erro, setErro] = useState<string | null>(null);

  async function handleLogin() {
    setErro(null);
    try {
      await login();
      if (provider.name === "fake") {
        navigate("/producao", { replace: true });
      }
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Falha ao entrar.");
    }
  }

  return (
    <main className="login-card">
      <img className="login-brand" src={logoCompleto} alt="Panne" />
      <h1>Entrar na Panne</h1>
      <p>
        A autorização visual usa as permissões de `/api/v1/me`. Grupos do provedor de identidade não
        autorizam sozinhos.
      </p>
      {provider.name === "fake" ? (
        <p className="meta">Ambiente de desenvolvimento com provedor falso explícito.</p>
      ) : (
        <p className="meta">OIDC Authorization Code com PKCE. Sem segredo no navegador.</p>
      )}
      <button type="button" className="primary" onClick={() => void handleLogin()}>
        {provider.name === "fake" ? "Entrar em desenvolvimento" : "Entrar"}
      </button>
      {config.authProvider === "oidc" && !config.oidcIssuer ? (
        <p role="alert">Configure o emissor e o client ID antes de autenticar.</p>
      ) : null}
      {erro ? <p role="alert">{erro}</p> : null}
    </main>
  );
}
