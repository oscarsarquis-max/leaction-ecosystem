import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { Logo } from "../../components/Logo";
import { ApiError } from "../../services/http";
import { B2B_CATEGORIES, submitPartnerLead, validEmail, validWhatsapp, type PartnerLead } from "./b2bApi";
import "./b2b.css";

const HERO_IMAGE = `/images/${encodeURIComponent("vitrine da loja.png")}`;

const EMPTY: PartnerLead = {
  name: "",
  brand: "",
  category: "",
  city: "",
  whatsapp: "",
  email: "",
  link: "",
  message: "",
  consent: false,
  website: "",
};

type Errors = Partial<Record<keyof PartnerLead, string>>;

const STEPS = [
  { title: "Você se apresenta", text: "Conte sobre a sua marca e os seus produtos no formulário abaixo." },
  { title: "A Loja avalia", text: "Provamos e avaliamos qualidade, apresentação e como combinam com os nossos pães." },
  { title: "Entra nas combos", text: "Seu produto aparece com a sua marca ao lado do pão certo, em combos montadas pela casa." },
  { title: "Você vende e entrega", text: "O cliente paga a sua parte direto a você. Você entrega com a sua logística." },
];

const BENEFITS = [
  { title: "Sua marca em evidência", text: "Selo com o seu nome em cada produto e uma página só sua: “A Loja de Pães apresenta”." },
  { title: "Clientes que já compram", text: "Quem encomenda pão de fermentação natural procura o que vai à mesa com ele." },
  { title: "Recebe direto", text: "O pagamento da sua parte cai na sua conta do Mercado Pago, sem esperar repasse." },
  { title: "Sem mensalidade", text: "Você só paga a taxa combo de R$ 2,50 quando vende um pedido." },
];

const FAQ = [
  {
    q: "Quanto custa?",
    a: "Não há adesão nem mensalidade. Em cada pedido vendido em combo, uma taxa combo de R$ 2,50 é descontada da sua parte. O cliente não vê essa taxa.",
  },
  {
    q: "Quem entrega?",
    a: "Cada um entrega o seu: a Loja entrega o pão e você entrega o seu produto, no prazo e nas regiões que você informar.",
  },
  {
    q: "Como eu recebo?",
    a: "Você conecta a sua conta do Mercado Pago ao portal do parceiro. O cliente paga a sua parte direto nessa conta.",
  },
  {
    q: "A Loja vende produtos que concorrem com os meus?",
    a: "Não. A Loja faz pão; os complementos vêm dos parceiros. Por categoria, a parceria pode ser exclusiva, parcial ou sem exclusividade.",
  },
];

function validate(lead: PartnerLead): Errors {
  const errors: Errors = {};
  if (!lead.name.trim()) errors.name = "Informe o seu nome.";
  if (!lead.brand.trim()) errors.brand = "Informe o nome da marca ou empresa.";
  if (!lead.category) errors.category = "Escolha a categoria principal.";
  if (!lead.city.trim()) errors.city = "Informe a cidade.";
  if (!validWhatsapp(lead.whatsapp)) errors.whatsapp = "Informe o WhatsApp com DDD.";
  if (!validEmail(lead.email)) errors.email = "Informe um e-mail válido.";
  if (!lead.message.trim()) errors.message = "Conte um pouco sobre os seus produtos.";
  if (!lead.consent) errors.consent = "Precisamos da sua autorização para entrar em contato.";
  return errors;
}

function Field({
  id,
  label,
  error,
  hint,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={error ? "b2b-field has-error" : "b2b-field"}>
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && !error ? (
        <p className="b2b-hint" id={`${id}-hint`}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="b2b-error" id={`${id}-error`}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function B2BPage() {
  const uid = useId();
  const [lead, setLead] = useState<PartnerLead>(EMPTY);
  const [errors, setErrors] = useState<Errors>({});
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "closed" | "failed">("idle");
  const formRef = useRef<HTMLFormElement>(null);
  const doneRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previousTitle = document.title;
    document.title = "Seja parceiro — Loja de Pães";
    const robots = document.createElement("meta");
    robots.name = "robots";
    robots.content = "noindex, nofollow";
    document.head.appendChild(robots);
    return () => {
      document.title = previousTitle;
      robots.remove();
    };
  }, []);

  useEffect(() => {
    if (status === "sent") doneRef.current?.focus();
  }, [status]);

  const fid = (name: keyof PartnerLead) => `${uid}-${name}`;
  const describedBy = (name: keyof PartnerLead, hint = false) =>
    errors[name] ? `${fid(name)}-error` : hint ? `${fid(name)}-hint` : undefined;

  function set<K extends keyof PartnerLead>(key: K, value: PartnerLead[K]) {
    setLead((current) => ({ ...current, [key]: value }));
    if (errors[key]) setErrors((current) => ({ ...current, [key]: undefined }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found = validate(lead);
    setErrors(found);
    const first = Object.keys(found)[0] as keyof PartnerLead | undefined;
    if (first) {
      formRef.current?.querySelector<HTMLElement>(`#${CSS.escape(fid(first))}`)?.focus();
      return;
    }
    setStatus("sending");
    try {
      await submitPartnerLead(lead);
      setStatus("sent");
    } catch (reason) {
      setStatus(reason instanceof ApiError && reason.status === 404 ? "closed" : "failed");
    }
  }

  return (
    <div className="b2b">
      <div className="b2b-top">
        <Logo href="/" />
        <a className="b2b-top-cta" href="#b2b-form">
          Quero ser parceiro
        </a>
      </div>

      <main className="b2b-main">
        <section className="b2b-hero" aria-labelledby="b2b-title">
          <div className="b2b-hero-text">
            <p className="b2b-eyebrow">Loja de Pães · Parceiros</p>
            <h1 id="b2b-title">
              Seu produto à mesa, <em>ao lado do nosso pão.</em>
            </h1>
            <p className="b2b-lead">
              Selecionamos produtores para acompanhar os pães da casa. Você aparece com a sua marca, vende junto com o pão
              e recebe direto na sua conta.
            </p>
            <div className="b2b-hero-actions">
              <a className="b2b-button" href="#b2b-form">
                Quero ser parceiro
              </a>
              <a className="b2b-link" href="#b2b-como">
                Como funciona
              </a>
            </div>
          </div>
          <figure className="b2b-hero-figure">
            <img src={HERO_IMAGE} alt="A vitrine da Loja de Pães com pães de fermentação natural" />
            <figcaption>
              <span className="b2b-sample-kicker">Combinação da casa</span>
              <strong>Fermentação natural + o seu queijo</strong>
              <span className="b2b-sample-badge">por Sua Marca</span>
            </figcaption>
          </figure>
        </section>

        <section className="b2b-section" id="b2b-como" aria-labelledby="b2b-como-title">
          <h2 id="b2b-como-title">Como funciona</h2>
          <ol className="b2b-steps">
            {STEPS.map((step, index) => (
              <li key={step.title}>
                <span className="b2b-step-n" aria-hidden="true">
                  {index + 1}
                </span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="b2b-section" aria-labelledby="b2b-ganha-title">
          <h2 id="b2b-ganha-title">O que você ganha</h2>
          <ul className="b2b-benefits">
            {BENEFITS.map((item) => (
              <li key={item.title}>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="b2b-section b2b-split" aria-labelledby="b2b-quem-title">
          <div>
            <h2 id="b2b-quem-title">Quem procuramos</h2>
            <p className="b2b-muted">
              Produtores e marcas da região, com produtos que fazem sentido ao lado de um bom pão.
            </p>
            <ul className="b2b-chips" aria-label="Categorias">
              {B2B_CATEGORIES.filter(([key]) => key !== "outro").map(([key, label]) => (
                <li key={key}>{label}</li>
              ))}
            </ul>
          </div>
          <ul className="b2b-checks" aria-label="O que você precisa ter">
            <li>Produção própria ou curadoria cuidadosa</li>
            <li>Fotos do produto e preço definido</li>
            <li>Entrega própria nas regiões que você atende</li>
            <li>Conta no Mercado Pago para receber</li>
          </ul>
        </section>

        <section className="b2b-section" aria-labelledby="b2b-faq-title">
          <h2 id="b2b-faq-title">Perguntas frequentes</h2>
          <div className="b2b-faq">
            {FAQ.map((item) => (
              <details key={item.q}>
                <summary>{item.q}</summary>
                <p>{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="b2b-section b2b-form-section" id="b2b-form" aria-labelledby="b2b-form-title">
          <div className="b2b-form-intro">
            <h2 id="b2b-form-title">Quero ser parceiro</h2>
            <p className="b2b-muted">Respondemos em até 3 dias úteis pelo WhatsApp ou e-mail que você informar.</p>
            <p className="b2b-safe">
              <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="currentColor" strokeWidth="2" />
                <path d="M8 11V8a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              Seus dados ficam só com a Loja de Pães e servem apenas para falarmos sobre a parceria.
            </p>
          </div>

          {status === "sent" ? (
            <div className="b2b-done" role="status" tabIndex={-1} ref={doneRef}>
              <h3>Recebemos a sua apresentação.</h3>
              <p>
                Obrigado, {lead.name.trim().split(/\s+/)[0]}. Vamos conhecer a {lead.brand.trim()} e responder em até 3 dias
                úteis.
              </p>
            </div>
          ) : (
            <form className="b2b-form" onSubmit={(event) => void submit(event)} noValidate ref={formRef}>
              <div className="b2b-grid">
                <Field id={fid("name")} label="Seu nome" error={errors.name}>
                  <input
                    id={fid("name")}
                    autoComplete="name"
                    maxLength={120}
                    value={lead.name}
                    aria-invalid={Boolean(errors.name)}
                    aria-describedby={describedBy("name")}
                    onChange={(event) => set("name", event.target.value)}
                  />
                </Field>
                <Field id={fid("brand")} label="Marca ou empresa" error={errors.brand}>
                  <input
                    id={fid("brand")}
                    autoComplete="organization"
                    maxLength={120}
                    value={lead.brand}
                    aria-invalid={Boolean(errors.brand)}
                    aria-describedby={describedBy("brand")}
                    onChange={(event) => set("brand", event.target.value)}
                  />
                </Field>
                <Field id={fid("category")} label="Categoria principal" error={errors.category}>
                  <select
                    id={fid("category")}
                    value={lead.category}
                    aria-invalid={Boolean(errors.category)}
                    aria-describedby={describedBy("category")}
                    onChange={(event) => set("category", event.target.value)}
                  >
                    <option value="">Escolha</option>
                    {B2B_CATEGORIES.map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field id={fid("city")} label="Cidade" error={errors.city}>
                  <input
                    id={fid("city")}
                    autoComplete="address-level2"
                    maxLength={80}
                    value={lead.city}
                    aria-invalid={Boolean(errors.city)}
                    aria-describedby={describedBy("city")}
                    onChange={(event) => set("city", event.target.value)}
                  />
                </Field>
                <Field id={fid("whatsapp")} label="WhatsApp" error={errors.whatsapp} hint="Com DDD, ex.: (85) 99999-0000">
                  <input
                    id={fid("whatsapp")}
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel"
                    maxLength={20}
                    value={lead.whatsapp}
                    aria-invalid={Boolean(errors.whatsapp)}
                    aria-describedby={describedBy("whatsapp", true)}
                    onChange={(event) => set("whatsapp", event.target.value)}
                  />
                </Field>
                <Field id={fid("email")} label="E-mail" error={errors.email}>
                  <input
                    id={fid("email")}
                    type="email"
                    autoComplete="email"
                    maxLength={254}
                    value={lead.email}
                    aria-invalid={Boolean(errors.email)}
                    aria-describedby={describedBy("email")}
                    onChange={(event) => set("email", event.target.value)}
                  />
                </Field>
              </div>
              <Field id={fid("link")} label="Instagram ou site (opcional)" hint="Ajuda a conhecermos a sua marca">
                <input
                  id={fid("link")}
                  maxLength={200}
                  value={lead.link}
                  aria-describedby={describedBy("link", true)}
                  onChange={(event) => set("link", event.target.value)}
                />
              </Field>
              <Field id={fid("message")} label="Conte sobre os seus produtos" error={errors.message}>
                <textarea
                  id={fid("message")}
                  rows={4}
                  maxLength={1500}
                  value={lead.message}
                  aria-invalid={Boolean(errors.message)}
                  aria-describedby={describedBy("message")}
                  onChange={(event) => set("message", event.target.value)}
                />
              </Field>
              <div className="b2b-hp" aria-hidden="true">
                <label htmlFor={fid("website")}>Não preencha</label>
                <input
                  id={fid("website")}
                  tabIndex={-1}
                  autoComplete="off"
                  value={lead.website}
                  onChange={(event) => set("website", event.target.value)}
                />
              </div>
              <div className={errors.consent ? "b2b-consent has-error" : "b2b-consent"}>
                <input
                  id={fid("consent")}
                  type="checkbox"
                  checked={lead.consent}
                  aria-invalid={Boolean(errors.consent)}
                  aria-describedby={describedBy("consent")}
                  onChange={(event) => set("consent", event.target.checked)}
                />
                <label htmlFor={fid("consent")}>Autorizo a Loja de Pães a entrar em contato sobre a parceria.</label>
                {errors.consent ? (
                  <p className="b2b-error" id={`${fid("consent")}-error`}>
                    {errors.consent}
                  </p>
                ) : null}
              </div>
              {status === "failed" ? (
                <p className="b2b-alert" role="alert">
                  Não foi possível enviar agora. Tente de novo em instantes.
                </p>
              ) : null}
              {status === "closed" ? (
                <p className="b2b-alert" role="alert">
                  As inscrições de parceiros estão fechadas no momento.
                </p>
              ) : null}
              <button type="submit" className="b2b-button" disabled={status === "sending"}>
                {status === "sending" ? "Enviando…" : "Enviar apresentação"}
              </button>
            </form>
          )}
        </section>
      </main>

      <div className="b2b-foot">
        <p>Loja de Pães · Boulangerie</p>
        <a href="/">Conheça a loja</a>
      </div>
    </div>
  );
}
