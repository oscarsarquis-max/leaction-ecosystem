import { useEffect, useId, useState, type FormEvent } from "react";
import { ApiError, requestJson } from "../services/http";
import { EyeOffStrokeIcon, EyeStrokeIcon } from "./HeaderIcons";

const LOGIN = "admin@lojadepaes.com.br";

function tokenFromPath(): string {
  const match = window.location.pathname.match(/^\/ativar\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : "";
}

function errorText(error: unknown): string {
  if (error instanceof ApiError && error.message && error.message !== "resposta-invalida") {
    return error.message;
  }
  return "Não foi possível concluir a ativação agora.";
}

export function ActivatePasswordPage() {
  const token = tokenFromPath();
  const passwordId = useId();
  const confirmId = useId();
  const [ready, setReady] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLookupError("Este link de ativação não é válido.");
      return;
    }
    requestJson<{ username: string }>(`/api/v1/admin/activate/${encodeURIComponent(token)}`)
      .then(() => {
        setReady(true);
      })
      .catch((reason: unknown) => {
        setLookupError(errorText(reason));
      });
  }, [token]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await requestJson("/api/v1/admin/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password, confirm }),
      });
      setDone(true);
    } catch (reason: unknown) {
      setFormError(errorText(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="activate-page">
      <p className="eyebrow">Loja de Pães</p>
      <h1>Defina sua senha</h1>
      <p className="activate-login">
        Login <strong>{LOGIN}</strong>
      </p>
      {lookupError ? <p role="alert">{lookupError}</p> : null}
      {done ? (
        <div>
          <p>Senha salva. Entre no cabeçalho com o login acima.</p>
          <a className="primary activate-next" href="/#acesso">
            Ir para o acesso
          </a>
        </div>
      ) : null}
      {ready && !done ? (
        <form className="activate-form" onSubmit={handleSubmit} autoComplete="on">
          <label htmlFor={passwordId}>
            Senha
            <span className="activate-field">
              <input
                id={passwordId}
                name="new-password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                minLength={10}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                type="button"
                className="text-button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              >
                {showPassword ? <EyeOffStrokeIcon /> : <EyeStrokeIcon />}
              </button>
            </span>
          </label>
          <label htmlFor={confirmId}>
            Confirmar senha
            <span className="activate-field">
              <input
                id={confirmId}
                name="confirm-password"
                type={showConfirm ? "text" : "password"}
                autoComplete="new-password"
                required
                minLength={10}
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
              />
              <button
                type="button"
                className="text-button"
                onClick={() => setShowConfirm((value) => !value)}
                aria-label={showConfirm ? "Ocultar confirmação" : "Mostrar confirmação"}
              >
                {showConfirm ? <EyeOffStrokeIcon /> : <EyeStrokeIcon />}
              </button>
            </span>
          </label>
          {formError ? (
            <p role="alert" className="activate-error">
              {formError}
            </p>
          ) : null}
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Salvando…" : "Salvar senha"}
          </button>
        </form>
      ) : null}
    </main>
  );
}
