import { useState } from "react";
import { ACCESS_EXPLANATION } from "./emailCode";

type Props = {
  signIn: (email: string, code: string) => Promise<void>;
  requestChange: (email: string) => Promise<void>;
  confirmChange: (email: string, confirmation: string) => Promise<void>;
};

export function EmailCodeForm({ signIn, requestChange, confirmChange }: Props) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [mode, setMode] = useState<"enter" | "change" | "confirm">("enter");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function enter(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await signIn(email, code);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "O acesso não foi aceito.");
    } finally {
      setCode("");
      setPending(false);
    }
  }

  async function askChange(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await requestChange(email);
      setNotice("Se este endereço puder entrar na Panne, enviamos a confirmação da alteração. O código atual não é reenviado.");
      setMode("confirm");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível solicitar a alteração.");
    } finally {
      setPending(false);
    }
  }

  async function confirm(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await confirmChange(email, confirmation);
      setNotice("Se a confirmação for válida, a Panne envia um código novo e o anterior deixa de valer.");
      setMode("enter");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "A alteração não foi concluída.");
    } finally {
      setConfirmation("");
      setPending(false);
    }
  }

  if (mode === "change") {
    return (
      <form onSubmit={(event) => void askChange(event)}>
        <p>A alteração pede uma confirmação enviada ao e-mail. O código atual não é reenviado e deixa de valer só depois da troca.</p>
        <label>
          E-mail
          <input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <button type="submit" className="primary" disabled={pending}>Solicitar alteração do código</button>
        <button type="button" className="ghost" onClick={() => setMode("enter")}>Voltar</button>
        {error ? <p role="alert">{error}</p> : null}
      </form>
    );
  }

  if (mode === "confirm") {
    return (
      <form onSubmit={(event) => void confirm(event)}>
        {notice ? <p role="status">{notice}</p> : null}
        <label>
          Confirmação recebida por e-mail
          <input autoComplete="off" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required />
        </label>
        <button type="submit" className="primary" disabled={pending}>Confirmar alteração</button>
        {error ? <p role="alert">{error}</p> : null}
      </form>
    );
  }

  return (
    <form onSubmit={(event) => void enter(event)}>
      <p>{ACCESS_EXPLANATION}</p>
      <p>A sessão neste navegador pode expirar. O código continua o mesmo.</p>
      <label>
        E-mail
        <input type="email" autoComplete="username" inputMode="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
      </label>
      <label>
        Código
        <input type="password" autoComplete="off" value={code} onChange={(event) => setCode(event.target.value)} required />
      </label>
      <button type="submit" className="primary" disabled={pending}>{pending ? "Entrando…" : "Entrar"}</button>
      <button type="button" className="ghost" onClick={() => { setError(null); setMode("change"); }}>
        Solicitar alteração do código
      </button>
      {notice ? <p role="status">{notice}</p> : null}
      {error ? <p role="alert">{error}</p> : null}
    </form>
  );
}
