import { useState, type FormEvent } from "react";
import { Button } from "../admin/shell/Button";
import { PartnerApiError, partnerApi, type PartnerSession } from "./partnerApi";

type Props = {
  mode: "invite" | "login";
  onSignedIn: (session: PartnerSession) => void;
};

function inviteToken(): string {
  return new URLSearchParams(window.location.search).get("token")?.trim() ?? "";
}

export function PartnerAccess({ mode, onSignedIn }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const token = mode === "invite" ? inviteToken() : "";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (mode === "invite") {
      if (password.length < 8) {
        setError("A senha precisa de pelo menos 8 caracteres.");
        return;
      }
      if (password !== confirm) {
        setError("As duas senhas não são iguais.");
        return;
      }
    }
    setBusy(true);
    try {
      const session = mode === "invite" ? await partnerApi.accept(token, password) : await partnerApi.login(email, password);
      if (mode === "invite") {
        window.history.replaceState({}, "", "/parceiro");
      }
      onSignedIn(session);
    } catch (reason) {
      setError(reason instanceof PartnerApiError ? reason.message : "Não foi possível entrar.");
    } finally {
      setBusy(false);
    }
  }

  if (mode === "invite" && !token) {
    return (
      <section className="ptn-center admin-card">
        <h1 className="ptn-h1">Convite incompleto</h1>
        <p className="mkt-muted">Abra o link exatamente como ele chegou. Se não der certo, peça um novo convite à Loja de Pães.</p>
        <a className="mkt-link" href="/parceiro/entrar">
          Já tenho senha
        </a>
      </section>
    );
  }

  const invite = mode === "invite";
  return (
    <section className="ptn-center admin-card">
      <div className="ptn-access-head">
        <h1 className="ptn-h1">{invite ? "Crie sua senha" : "Entrar no portal"}</h1>
        <p className="mkt-muted">
          {invite
            ? "Bem-vindo ao marketplace da Loja de Pães. Crie a senha para cadastrar seus produtos."
            : "Use o e-mail do convite e a senha que você criou."}
        </p>
      </div>
      <form className="ptn-access-form" onSubmit={(event) => void submit(event)} noValidate>
        {invite ? null : (
          <label className="mkt-field">
            E-mail
            <input
              className="mkt-input"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
        )}
        <label className="mkt-field">
          {invite ? "Senha (mínimo de 8 caracteres)" : "Senha"}
          <input
            className="mkt-input"
            type="password"
            autoComplete={invite ? "new-password" : "current-password"}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {invite ? (
          <label className="mkt-field">
            Repita a senha
            <input
              className="mkt-input"
              type="password"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
            />
          </label>
        ) : null}
        {error ? (
          <p className="mkt-alert" role="alert">
            {error}
          </p>
        ) : null}
        <Button type="submit" variant="primary" disabled={busy}>
          {busy ? "Entrando…" : invite ? "Criar senha e entrar" : "Entrar"}
        </Button>
      </form>
      {invite ? null : (
        <p className="mkt-muted">Esqueceu a senha? Peça à Loja de Pães um novo convite.</p>
      )}
    </section>
  );
}
