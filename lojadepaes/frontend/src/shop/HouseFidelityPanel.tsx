import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from "react";
import { BreadStrokeIcon, GiftStrokeIcon } from "../components/HeaderIcons";
import { formatCents } from "../lib/money";
import { ApiError } from "../services/http";
import { BakeCalendar } from "./BakeCalendar";
import { goStorefront, saveOrderToken } from "./checkoutApi";
import { readStoredContact, writeStoredContact } from "./contactStorage";
import {
  HOUSE_FIDELITY_COPY as COPY,
  STAMP_MARKS,
  demoFromLocation,
  filledStamps,
  formatCpf,
  isValidCpf,
  rememberDemoState,
  type HouseFidelityStatus,
} from "./houseFidelity";
import {
  fetchHouseFidelity,
  fetchHouseFidelityRewards,
  logoutHouseFidelity,
  redeemHouseFidelity,
  submitHouseFidelityResume,
  submitHouseFidelitySignup,
  verifyHouseFidelity,
  verifyHouseFidelityLink,
  type FidelityReward,
} from "./houseFidelityApi";
import { fetchOperations } from "./operationsApi";

type FormMode = "signup" | "resume" | "verify" | "redeem" | null;

function actionError(error: unknown): string {
  if (error instanceof ApiError && error.message && error.message !== "resposta-invalida") {
    return error.message;
  }
  return "Não foi possível continuar agora. A compra segue disponível sem cadastro.";
}

function headlineNodes() {
  const emphasis = COPY.headlineEmphasis;
  const base = COPY.headline.replace(emphasis, "").trimEnd();
  return (
    <>
      {base} <em>{emphasis}</em>
    </>
  );
}

function verifyTokenFromHash(hash = window.location.hash): string | null {
  const raw = hash.replace(/^#/, "");
  if (!raw.startsWith("fidelidade-verificar=")) {
    return null;
  }
  return decodeURIComponent(raw.slice("fidelidade-verificar=".length));
}

export function HouseFidelityPanel() {
  const stored = useMemo(() => readStoredContact(), []);
  const [preview, setPreview] = useState(false);
  const [status, setStatus] = useState<HouseFidelityStatus | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [name, setName] = useState(stored.name);
  const [email, setEmail] = useState(stored.email);
  const [cpf, setCpf] = useState("");
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rewards, setRewards] = useState<FidelityReward[]>([]);
  const [rewardGaps, setRewardGaps] = useState<{ name: string }[]>([]);
  const [redeemVariant, setRedeemVariant] = useState("");
  const [redeemDate, setRedeemDate] = useState<string | null>(null);
  const titleId = useId();
  const nameId = useId();
  const emailId = useId();
  const cpfId = useId();
  const resumeId = useId();
  const codeId = useId();
  const firstFieldRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetchOperations()
      .then((operations) => {
        if (cancelled) {
          return;
        }
        const protectedPreview = operations.preview_protection === true;
        setPreview(protectedPreview);
        const demo = demoFromLocation(protectedPreview);
        return fetchHouseFidelity(protectedPreview && demo !== "visitor" ? demo : undefined);
      })
      .then((payload) => {
        if (!cancelled && payload) {
          setStatus(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const openFromHash = () => {
      if (window.location.hash === "#fidelidade-cadastro") {
        setFormMode("signup");
      }
      const token = verifyTokenFromHash();
      if (token) {
        setSending(true);
        verifyHouseFidelityLink(token)
          .then((payload) => {
            setStatus(payload);
            setMessage(payload.message ?? "Cadastro confirmado.");
            setFormMode(null);
          })
          .catch((reason: unknown) => setError(actionError(reason)))
          .finally(() => setSending(false));
      }
    };
    openFromHash();
    window.addEventListener("hashchange", openFromHash);
    return () => window.removeEventListener("hashchange", openFromHash);
  }, []);

  useEffect(() => {
    if (!formMode) {
      return;
    }
    firstFieldRef.current?.focus();
  }, [formMode]);

  const participant = status?.participant ?? null;
  const filled = filledStamps(participant);
  const stampsAreProgress = Boolean(participant);
  const verified = status?.verified === true;

  function openForm(mode: FormMode) {
    setFormMode(mode);
    setError(null);
    if (mode !== "verify") {
      setMessage(null);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (sending) {
      return;
    }
    setSending(true);
    setError(null);
    try {
      if (formMode === "signup") {
        if (!isValidCpf(cpf)) {
          setError("Informe um CPF válido. Ele identifica a participação, mas não abre saldo sozinho.");
          return;
        }
        const result = await submitHouseFidelitySignup(name, email, cpf);
        writeStoredContact(result.contact_name ?? name, result.contact_email ?? email);
        rememberDemoState("visitor", preview);
        setStatus(result);
        setMessage(result.message ?? COPY.verifyHelp);
        setCpf("");
        setFormMode("verify");
        return;
      }
      if (formMode === "resume") {
        const result = await submitHouseFidelityResume(email);
        writeStoredContact(name || stored.name, result.contact_email ?? email);
        rememberDemoState("visitor", preview);
        setStatus(result);
        setMessage(result.message ?? COPY.verifyHelp);
        setFormMode("verify");
        return;
      }
      if (formMode === "verify") {
        const result = await verifyHouseFidelity(email, code);
        setStatus(result);
        setMessage(result.message ?? (result.confirmed ? "Cadastro confirmado." : COPY.verifyHelp));
        setCode("");
        setFormMode(null);
        return;
      }
      if (formMode === "redeem") {
        if (!redeemVariant || !redeemDate) {
          setError("Escolha o pão de 500 g e uma data.");
          return;
        }
        const order = await redeemHouseFidelity({
          variant_id: redeemVariant,
          requested_date: redeemDate,
          idempotency_key: `redeem-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        });
        if (order.access_token) {
          saveOrderToken(order.public_reference, order.access_token);
        }
        goStorefront(`/pedido/${order.public_reference}`);
      }
    } catch (reason: unknown) {
      setError(actionError(reason));
    } finally {
      setSending(false);
    }
  }

  async function openRedeem() {
    setError(null);
    setSending(true);
    try {
      const payload = await fetchHouseFidelityRewards();
      setRewards(payload.items);
      setRewardGaps(payload.gaps);
      setFormMode("redeem");
    } catch (reason: unknown) {
      setError(actionError(reason));
    } finally {
      setSending(false);
    }
  }

  async function handleLogout() {
    await logoutHouseFidelity();
    setStatus((current) =>
      current
        ? { ...current, verified: false, participant: preview ? current.participant : null, cpf_masked: null, name: null, can_redeem: false }
        : current,
    );
    setMessage(null);
    setFormMode(null);
  }

  return (
    <article id="fidelidade" className="house-fidelity" aria-labelledby={titleId}>
      <p className="house-fidelity-eyebrow">{COPY.eyebrow}</p>
      <h3 id={titleId} className="house-fidelity-title">
        {headlineNodes()}
      </h3>
      <p className="house-fidelity-lead">{COPY.lead}</p>
      {!verified ? (
        <div className="house-fidelity-actions">
          <button type="button" className="primary house-fidelity-cta" onClick={() => openForm("signup")}>
            {COPY.primaryCta}
          </button>
          <button type="button" className="text-button house-fidelity-link" onClick={() => openForm("resume")}>
            {COPY.secondaryCta}
          </button>
        </div>
      ) : (
        <div className="house-fidelity-actions">
          <p className="house-fidelity-invite">
            {status?.name} · CPF {status?.cpf_masked}
          </p>
          <button type="button" className="text-button house-fidelity-link" onClick={() => void handleLogout()}>
            Sair da conta
          </button>
          {status?.can_redeem ? (
            <button type="button" className="primary house-fidelity-cta" onClick={() => void openRedeem()}>
              Resgatar pão de 500 g
            </button>
          ) : null}
        </div>
      )}
      <ol
        className="house-fidelity-stamps"
        aria-label={
          stampsAreProgress
            ? participant?.progress_label
            : "Ilustração de quatro pedidos; não representa saldo de cliente"
        }
      >
        {STAMP_MARKS.map((mark, index) => {
          const done = stampsAreProgress && index < filled;
          return (
            <li
              key={mark.id}
              className={`house-fidelity-stamp${mark.gift ? " is-gift" : ""}${done ? " is-done" : ""}`}
            >
              {mark.gift ? <GiftStrokeIcon size={22} /> : <BreadStrokeIcon size={22} />}
              <span>{mark.label}</span>
            </li>
          );
        })}
      </ol>
      {participant ? (
        <p className="house-fidelity-progress">
          {participant.progress_label} · {participant.remaining_label} A contagem recomeça em{" "}
          {participant.restart_label} · {participant.credits_label}
        </p>
      ) : null}
      <p className="house-fidelity-invite">{COPY.invite}</p>
      {formMode ? (
        <form ref={formRef} className="house-fidelity-form" onSubmit={handleSubmit} noValidate>
          {formMode === "signup" ? (
            <>
              <label htmlFor={nameId}>
                Nome
                <input
                  ref={firstFieldRef}
                  id={nameId}
                  name="name"
                  autoComplete="name"
                  maxLength={160}
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
              <label htmlFor={emailId}>
                E-mail
                <input
                  id={emailId}
                  name="email"
                  type="email"
                  autoComplete="email"
                  maxLength={254}
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <label htmlFor={cpfId}>
                CPF
                <input
                  id={cpfId}
                  name="cpf"
                  inputMode="numeric"
                  autoComplete="off"
                  maxLength={14}
                  required
                  value={cpf}
                  onChange={(event) => setCpf(formatCpf(event.target.value))}
                />
              </label>
              <p className="house-fidelity-help">{COPY.cpfHelp}</p>
              <p className="house-fidelity-help">{COPY.privacy}</p>
            </>
          ) : null}
          {formMode === "resume" ? (
            <>
              <label htmlFor={resumeId}>
                E-mail do cadastro
                <input
                  ref={firstFieldRef}
                  id={resumeId}
                  name="email"
                  type="email"
                  autoComplete="email"
                  maxLength={254}
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <p className="house-fidelity-help">{COPY.resumeHelp}</p>
            </>
          ) : null}
          {formMode === "verify" ? (
            <>
              <label htmlFor={codeId}>
                Código de verificação
                <input
                  ref={firstFieldRef}
                  id={codeId}
                  name="code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  required
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                />
              </label>
              <p className="house-fidelity-help">{COPY.verifyHelp}</p>
            </>
          ) : null}
          {formMode === "redeem" ? (
            <>
              {rewardGaps.length > 0 ? (
                <p className="house-fidelity-help">
                  Falta apresentação de 500 g em: {rewardGaps.map((item) => item.name).join(", ")}. O
                  resgate fica fechado até A Loja completar o cadastro.
                </p>
              ) : (
                <>
                  <fieldset>
                    <legend>Pão de 500 g</legend>
                    {rewards.map((item) => (
                      <label key={item.variant_id}>
                        <input
                          type="radio"
                          name="reward"
                          checked={redeemVariant === item.variant_id}
                          onChange={() => setRedeemVariant(item.variant_id)}
                        />
                        {item.name} · {item.presentation} · de {formatCents(item.original_cents)} para{" "}
                        {formatCents(item.due_cents)}
                      </label>
                    ))}
                  </fieldset>
                  <BakeCalendar
                    lines={
                      redeemVariant
                        ? [{ kind: "product", variant_id: redeemVariant, quantity: 1 }]
                        : []
                    }
                    selectedDate={redeemDate}
                    onSelectDate={setRedeemDate}
                    layout="checkout"
                  />
                  <p className="house-fidelity-help">{status?.benefit ?? COPY.howApproved}</p>
                </>
              )}
            </>
          ) : null}
          {error ? (
            <p className="house-fidelity-error" role="alert">
              {error}
            </p>
          ) : null}
          <div className="house-fidelity-form-actions">
            {formMode !== "redeem" || rewardGaps.length === 0 ? (
              <button type="submit" className="primary" disabled={sending}>
                {sending
                  ? "Enviando…"
                  : formMode === "signup"
                    ? "Enviar cadastro"
                    : formMode === "resume"
                      ? "Continuar"
                      : formMode === "verify"
                        ? "Confirmar código"
                        : "Pedir o pão de presente"}
              </button>
            ) : null}
            <button type="button" className="text-button" onClick={() => setFormMode(null)}>
              Fechar
            </button>
          </div>
        </form>
      ) : null}
      {message ? (
        <p className="house-fidelity-message" role="status">
          {message}
        </p>
      ) : null}
      <p className="house-fidelity-foot">{COPY.footer}</p>
      <details className="house-fidelity-how">
        <summary>{COPY.howTitle}</summary>
        <p>{status?.how_it_works ?? COPY.howApproved}</p>
        <p>{COPY.howRestart}</p>
      </details>
    </article>
  );
}
