import { useRef, useState } from "react";

const RESEND_SECONDS = 60;
const MAX_ATTEMPTS = 5;
const MAX_RESENDS = 3;

type Props = {
  requestCode: (email: string) => Promise<{ notice: string; advance: boolean }>;
  confirmCode: (code: string) => Promise<void>;
  resendCode: () => Promise<{ notice: string; advance: boolean }>;
};

export function EmailCodeForm({ requestCode, confirmCode, resendCode }: Props) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [wait, setWait] = useState(0);
  const [attempts, setAttempts] = useState(0);
  const [resends, setResends] = useState(0);
  const timer = useRef<number | null>(null);

  function armCooldown() {
    setWait(RESEND_SECONDS);
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(() => {
      setWait((current) => {
        if (current <= 1) {
          if (timer.current) window.clearInterval(timer.current);
          return 0;
        }
        return current - 1;
      });
    }, 1000);
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const result = await requestCode(email);
      setNotice(result.notice);
      if (result.advance) {
        setStep("code");
        setAttempts(0);
        setResends(0);
        armCooldown();
      }
    } finally {
      setPending(false);
    }
  }

  async function confirm(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await confirmCode(code);
      setCode("");
    } catch (caught) {
      setCode("");
      const next = attempts + 1;
      setAttempts(next);
      const message = caught instanceof Error ? caught.message : "O código não foi aceito.";
      setError(next >= MAX_ATTEMPTS ? "Houve tentativas demais. Peça outro código." : message);
    } finally {
      setPending(false);
    }
  }

  async function resend() {
    if (wait > 0 || resends >= MAX_RESENDS) return;
    setError(null);
    setPending(true);
    try {
      const result = await resendCode();
      setNotice(result.notice);
      setResends((current) => current + 1);
      setAttempts(0);
      armCooldown();
    } finally {
      setPending(false);
    }
  }

  if (step === "email") {
    return (
      <form onSubmit={(event) => void send(event)}>
        <p>O acesso é por um código enviado ao seu e-mail. Ele expira, vale uma vez e não fica gravado neste aparelho.</p>
        <label>
          E-mail
          <input
            type="email"
            autoComplete="username"
            inputMode="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <button type="submit" className="primary" disabled={pending}>
          {pending ? "Enviando…" : "Receber código"}
        </button>
        {notice ? <p role="status">{notice}</p> : null}
      </form>
    );
  }

  return (
    <form onSubmit={(event) => void confirm(event)}>
      {notice ? <p role="status">{notice}</p> : null}
      <label>
        Código
        <input
          inputMode="numeric"
          autoComplete="one-time-code"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          required
        />
      </label>
      <button type="submit" className="primary" disabled={pending || attempts >= MAX_ATTEMPTS}>
        {pending ? "Confirmando…" : "Confirmar código"}
      </button>
      <button type="button" className="ghost" disabled={pending || wait > 0 || resends >= MAX_RESENDS} onClick={() => void resend()}>
        {wait > 0 ? `Enviar outro código em ${wait}s` : "Enviar outro código"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
    </form>
  );
}
