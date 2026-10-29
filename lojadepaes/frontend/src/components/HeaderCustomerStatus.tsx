import { useEffect, useId, useState, type FormEvent, type MouseEvent } from "react";
import { cancelLibrarySubscription, identifyLibrary, verifyLibrary } from "../features/baker-library/libraryApi";
import { fetchHouseFidelity, logoutHouseFidelity } from "../shop/houseFidelityApi";

type Situation = {
  identified: boolean;
  name?: string | null;
  assinatura?: {
    label: string;
    status: string;
    status_label: string;
    authorized: boolean;
    cancelable?: boolean;
    cancel_policy?: string | null;
  };
  consultas_ia?: {
    label: string;
    credits?: number | null;
    monthly_credits?: number | null;
    pack_credits?: number | null;
    pack_expires?: boolean;
  };
  fidelidade?: { label: string; enrolled: boolean; bread_credits: number; stamps_label?: string | null };
  plans_href?: string | null;
  message?: string | null;
};

const STATUS_LABEL: Record<string, string> = {
  active: "ativa",
  pending: "pendente",
  cancelled_with_access: "renovação cancelada, acesso vigente",
  none: "sem assinatura",
};

type IdKind = "email" | "cpf";

function onlyDigits(value: string): string {
  return value.replace(/\D/g, "").slice(0, 11);
}

function isValidCpf(value: string): boolean {
  const digits = onlyDigits(value);
  if (digits.length !== 11 || new Set(digits).size === 1) {
    return false;
  }
  const numbers = digits.split("").map(Number);
  const check = (limit: number) => {
    const total = numbers.slice(0, limit).reduce((sum, item, index) => sum + item * (limit + 1 - index), 0);
    const rest = (total * 10) % 11;
    return (rest === 10 ? 0 : rest) === numbers[limit];
  };
  return check(9) && check(10);
}

export function HeaderCustomerStatus() {
  const [situation, setSituation] = useState<Situation | null>(null);
  const [open, setOpen] = useState(false);
  const [idKind, setIdKind] = useState<IdKind>("email");
  const [email, setEmail] = useState("");
  const [cpf, setCpf] = useState("");
  const [code, setCode] = useState("");
  const [hint, setHint] = useState<string | null>(null);
  const [busy, setBusy] = useState<"enter" | "code" | "cancel" | "logout" | null>(null);
  const panelId = useId();
  const emailFieldId = useId();
  const cpfFieldId = useId();
  const codeFieldId = useId();

  useEffect(() => {
    let cancelled = false;
    if (typeof fetch !== "function") {
      setSituation({ identified: false });
      return;
    }
    fetch("/api/v1/conta/situacao", { credentials: "include" })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (!cancelled && payload) setSituation(payload);
      })
      .catch(() => {
        if (!cancelled) setSituation({ identified: false });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshSituation() {
    const [next, fidelity] = await Promise.all([
      fetch("/api/v1/conta/situacao", { credentials: "include" }).then((response) => response.json()),
      fetchHouseFidelity().catch(() => null),
    ]);
    setSituation(next);
    if (fidelity && next) {
      setSituation({
        ...next,
        fidelidade: {
          ...next.fidelidade,
          enrolled: Boolean(fidelity.participant) || next.fidelidade?.enrolled,
          bread_credits: fidelity.participant?.credits ?? next.fidelidade?.bread_credits ?? 0,
          stamps_label: fidelity.participant?.progress_label ?? next.fidelidade?.stamps_label,
        },
      });
    }
  }

  async function onReceiveCode() {
    if (idKind === "cpf") {
      if (!isValidCpf(cpf)) {
        setHint("Informe um CPF válido. Este campo é o documento, não o código de acesso.");
        return;
      }
    } else if (!email.trim()) {
      setHint("Informe o e-mail cadastrado para receber o código.");
      return;
    }
    setBusy("code");
    setHint(null);
    try {
      const result =
        idKind === "cpf"
          ? await identifyLibrary({ cpf: onlyDigits(cpf) })
          : await identifyLibrary({ email: email.trim() });
      setHint(
        result.email_masked
          ? `Código enviado para ${result.email_masked}. Ele vale por 15 minutos e só pode ser usado uma vez.`
          : result.message || "Se o cadastro existir, o código foi enviado ao e-mail cadastrado.",
      );
    } catch {
      setHint("Não foi possível enviar o código agora. Tente de novo em instantes.");
    } finally {
      setBusy(null);
    }
  }

  async function onEnter(event: FormEvent) {
    event.preventDefault();
    if (!code.trim()) {
      setHint("Informe o código de acesso. Se ainda não tiver, use Receber código.");
      return;
    }
    if (idKind === "cpf") {
      if (!isValidCpf(cpf)) {
        setHint("Informe um CPF válido. Este campo é o documento, não o código de acesso.");
        return;
      }
    } else if (!email.trim()) {
      setHint("Informe o e-mail cadastrado e o código para entrar. Se ainda não tiver código, use Receber código.");
      return;
    }
    setBusy("enter");
    setHint(null);
    try {
      await verifyLibrary(
        idKind === "cpf" ? { cpf: onlyDigits(cpf), code: code.trim() } : { email: email.trim(), code: code.trim() },
      );
      await refreshSituation();
      setOpen(false);
      setCode("");
    } catch {
      setHint("Código inválido, expirado ou já usado. Use Receber código se precisar de outro. Isso não inicia o envio sozinho.");
    } finally {
      setBusy(null);
    }
  }

  async function onCancelRenewal() {
    if (!situation?.assinatura?.cancelable) {
      return;
    }
    if (!window.confirm("Cancelar só a renovação automática? O período já pago continua até o vencimento.")) {
      return;
    }
    setBusy("cancel");
    setHint(null);
    try {
      const result = await cancelLibrarySubscription();
      setHint(result.message || "A renovação automática foi cancelada.");
      await refreshSituation();
    } catch {
      setHint("Não foi possível cancelar a renovação agora. Tente de novo em instantes.");
    } finally {
      setBusy(null);
    }
  }

  async function onLogout() {
    setBusy("logout");
    setHint(null);
    try {
      await logoutHouseFidelity();
      setSituation({ identified: false });
      setCode("");
      setOpen(false);
    } catch {
      setHint("Não foi possível sair agora. Tente de novo em instantes.");
    } finally {
      setBusy(null);
    }
  }

  function goToAdmin(event: MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    setOpen(false);
    window.location.hash = "acesso";
    window.requestAnimationFrame(() => {
      const form = document.getElementById("acesso");
      const field = form?.querySelector<HTMLElement>("input:not([aria-hidden='true']), button[type='submit']");
      field?.focus();
    });
  }

  const identified = Boolean(situation?.identified);
  const status = situation?.assinatura?.status || "none";
  const statusLabel = situation?.assinatura?.status_label || STATUS_LABEL[status] || STATUS_LABEL.none;
  const ai = situation?.consultas_ia?.credits;
  const monthly = situation?.consultas_ia?.monthly_credits;
  const pack = situation?.consultas_ia?.pack_credits;
  const bread = situation?.fidelidade?.bread_credits ?? 0;
  const enrolled = Boolean(situation?.fidelidade?.enrolled);

  return (
    <div className={`header-customer${identified ? " is-identified" : ""}`}>
      <button
        type="button"
        className="header-customer-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        {identified ? (
          <span className="header-customer-summary">
            <span>
              <strong>Assinatura</strong> {statusLabel}
            </span>
            <span>
              <strong>Mensal</strong> {typeof monthly === "number" ? monthly : typeof ai === "number" ? ai : "—"}
            </span>
            <span>
              <strong>Avulso</strong> {typeof pack === "number" ? pack : "—"}
            </span>
            <span>
              <strong>Fidelidade</strong> {enrolled ? `${bread} crédito${bread === 1 ? "" : "s"} de pão` : "sem adesão"}
            </span>
          </span>
        ) : (
          "Identifique-se"
        )}
      </button>
      {open ? (
        <div id={panelId} className="header-customer-panel" role="dialog" aria-label="Situação da conta">
          {identified ? (
            <>
              <p>
                <strong>Assinatura:</strong> {statusLabel}
              </p>
              <p>
                <strong>Consultas do mês:</strong>{" "}
                {typeof monthly === "number" ? monthly : typeof ai === "number" ? ai : "indisponível agora"}
              </p>
              <p>
                <strong>Pacote avulso:</strong> {typeof pack === "number" ? pack : "indisponível agora"}
                {typeof pack === "number" ? " · sem vencimento" : ""}
              </p>
              <p>
                <strong>Fidelidade / créditos de pão:</strong>{" "}
                {enrolled ? `${bread} crédito${bread === 1 ? "" : "s"} de pão` : "sem adesão à fidelidade"}
              </p>
              {situation?.assinatura?.cancelable ? (
                <button type="button" className="text-button" disabled={busy === "cancel"} onClick={() => void onCancelRenewal()}>
                  {busy === "cancel" ? "Cancelando renovação…" : "Gerenciar assinatura"}
                </button>
              ) : null}
              {situation?.plans_href ? (
                <a href={situation.plans_href}>Ver planos</a>
              ) : null}
              <button type="button" className="text-button" disabled={busy !== null} onClick={() => void onLogout()}>
                {busy === "logout" ? "Saindo…" : "Sair"}
              </button>
            </>
          ) : (
            <form onSubmit={(event) => void onEnter(event)}>
              <p>
                Entre com o e-mail ou o CPF cadastrado e um código ainda válido. Receber código envia um
                código temporário só ao e-mail do cadastro.
              </p>
              <fieldset className="header-customer-idkind">
                <legend>Como se identificar</legend>
                <label>
                  <input
                    type="radio"
                    name="customer-idkind"
                    checked={idKind === "email"}
                    onChange={() => setIdKind("email")}
                  />
                  E-mail
                </label>
                <label>
                  <input
                    type="radio"
                    name="customer-idkind"
                    checked={idKind === "cpf"}
                    onChange={() => setIdKind("cpf")}
                  />
                  CPF
                </label>
              </fieldset>
              {idKind === "email" ? (
                <label htmlFor={emailFieldId}>
                  E-mail cadastrado
                  <input
                    id={emailFieldId}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    type="email"
                    autoComplete="username"
                    inputMode="email"
                    name="customer-email"
                  />
                </label>
              ) : (
                <label htmlFor={cpfFieldId}>
                  CPF do cadastro
                  <input
                    id={cpfFieldId}
                    value={cpf}
                    onChange={(event) => setCpf(onlyDigits(event.target.value))}
                    inputMode="numeric"
                    autoComplete="off"
                    name="cpf"
                    placeholder="Somente o documento"
                  />
                </label>
              )}
              <label htmlFor={codeFieldId}>
                Código de acesso
                <input
                  id={codeFieldId}
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  name="one-time-code"
                  placeholder="Código recebido por e-mail"
                />
              </label>
              <div className="header-customer-actions">
                <button type="submit" className="primary" disabled={busy !== null}>
                  {busy === "enter" ? "Entrando…" : "Entrar"}
                </button>
                <button type="button" className="text-button" disabled={busy !== null} onClick={() => void onReceiveCode()}>
                  {busy === "code" ? "Enviando…" : "Receber código"}
                </button>
              </div>
              <a className="header-admin-link" href="#acesso" onClick={goToAdmin}>
                Acesso administrativo
              </a>
            </form>
          )}
          {hint ? <p role="status">{hint}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
