import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import logoCompleto from "../../images/aprovados/horizontal-claro.png";
import fallbackImage from "../../images/aprovados/compacto-escuro.png";
import { AssistantAvatar } from "../assistant/AssistantAvatar";
import { GlobalAssistant } from "../assistant/GlobalAssistant";
import { useAssistant } from "../assistant/AssistantContext";
import { useAuth } from "../auth/AuthContext";
import { config } from "../config";
import { DEMO_PROFILES } from "../demo/profiles";
import { StaticLoginEditorialProvider } from "../editorial/staticProvider";
import type { LoginEditorialColumn, LoginEditorialPayload } from "../editorial/schema";

function EditorialImage({ column }: { column: LoginEditorialColumn }) {
  const [failed, setFailed] = useState(!column.image.url);
  return failed ? (
    <img className="media-fallback" src={fallbackImage} alt={column.image.alt || "Marca Panne"} />
  ) : (
    <img src={column.image.url} alt={column.image.alt} onError={() => setFailed(true)} />
  );
}

function EditorialColumn({ column }: { column: LoginEditorialColumn }) {
  return (
    <article className="login-col">
      <EditorialImage column={column} />
      <div className="login-col-body">
        <p className="meta">{column.eyebrow}</p>
        <h2>{column.title}</h2>
        <p>{column.summary}</p>
        {column.sections.map((item) => (
          <p key={item} className="meta">{item}</p>
        ))}
        {column.cta ? (
          <a className="ghost" href={column.cta.url}>{column.cta.label}</a>
        ) : null}
      </div>
    </article>
  );
}

export function LoginPage() {
  const { login, provider } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { openAssistant, open } = useAssistant();
  const [demoSubject, setDemoSubject] = useState(DEMO_PROFILES[0].subject);
  const [erro, setErro] = useState<string | null>(
    location.state && typeof location.state === "object" && "expired" in location.state
      ? "Sessão expirada. Entre de novo."
      : null,
  );
  const [loading, setLoading] = useState(false);
  const [editorial, setEditorial] = useState<LoginEditorialPayload | null>(null);
  const [editorialReady, setEditorialReady] = useState(false);

  useEffect(() => {
    const mode = new URLSearchParams(window.location.search).get("editorial");
    const providerMode = mode === "indisponivel" ? "unavailable" : mode === "invalido" ? "invalid" : "ok";
    void new StaticLoginEditorialProvider(providerMode).load().then((payload) => {
      setEditorial(payload);
      setEditorialReady(true);
    });
  }, []);

  async function handleLogin() {
    setErro(null);
    setLoading(true);
    try {
      if (config.demoMode && provider.name === "fake") {
        sessionStorage.setItem("panne.demoSubject", demoSubject);
      }
      await login();
      if (provider.name === "fake") {
        navigate("/producao", { replace: true });
      }
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Falha ao entrar.");
    } finally {
      setLoading(false);
    }
  }

  const left = editorial?.columns.find((row) => row.placement === "left");
  const right = editorial?.columns.find((row) => row.placement === "right");

  return (
    <main className="login-stage">
      {left ? <EditorialColumn column={left} /> : editorialReady ? null : <div className="login-col skeleton" aria-hidden />}
      <section className="login-center">
        <img className="login-brand" src={logoCompleto} alt="Panne" />
        <h1>Entrar na Panne</h1>
        <p>A autorização usa as permissões da sessão. O conteúdo ao lado não altera o acesso.</p>
        {config.demoMode ? <p className="demo-banner">Ambiente de demonstração</p> : null}
        {provider.name === "fake" ? (
          <p className="meta">Ambiente de desenvolvimento com provedor falso explícito.</p>
        ) : (
          <p className="meta">OIDC Authorization Code com PKCE. Sem segredo no navegador.</p>
        )}
        {config.demoMode && provider.name === "fake" ? (
          <label>
            Perfil de demonstração
            <select value={demoSubject} onChange={(event) => setDemoSubject(event.target.value)}>
              {DEMO_PROFILES.map((row) => (
                <option key={row.subject} value={row.subject}>
                  {row.label}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <button type="button" className="primary" disabled={loading} onClick={() => void handleLogin()}>
          {loading ? "Entrando…" : provider.name === "fake" ? "Entrar em desenvolvimento" : "Entrar"}
        </button>
        <p>
          <button type="button" className="ghost" onClick={openAssistant}>
            Ajuda para entrar
          </button>
        </p>
        {config.authProvider === "oidc" && !config.oidcIssuer ? (
          <p role="alert">Configure o emissor e o client ID antes de autenticar.</p>
        ) : null}
        {erro ? <p role="alert">{erro}</p> : null}
        {editorialReady && !editorial ? <p className="meta">As colunas editoriais são opcionais.</p> : null}
      </section>
      {right ? <EditorialColumn column={right} /> : editorialReady ? null : <div className="login-col skeleton" aria-hidden />}
      <AssistantAvatar publicMode />
      {open ? <GlobalAssistant publicMode /> : null}
    </main>
  );
}
