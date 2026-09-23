import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import logoHorizontal from "../../images/aprovados/horizontal-escuro.png";
import { ApiError } from "../api/errors";
import { useAuth } from "../auth/AuthContext";
import { useOrganization } from "../session/OrganizationContext";

const WELCOME_KEY = "panne.welcome";
const CODE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const ACTIVITIES = [
  { id: "sale", label: "Vendas", hint: "Atende pedidos e registra o que sai." },
  { id: "stock", label: "Estoque", hint: "Guarda e controla o que entra e sai." },
  { id: "production", label: "Produção", hint: "Prepara o que será vendido ou separado." },
] as const;

type Field =
  | "trade"
  | "holderName"
  | "fiscal"
  | "legal"
  | "place"
  | "activities"
  | "organization"
  | "establishment"
  | "form";

type Created = { client: string; place: string };

function suggestCode(value: string): string {
  const plain = value.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  return plain
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

function digits(value: string): string {
  return value.replace(/\D/g, "");
}

function maskCpf(raw: string): string {
  const value = digits(raw).slice(0, 11);
  if (value.length <= 3) return value;
  if (value.length <= 6) return `${value.slice(0, 3)}.${value.slice(3)}`;
  if (value.length <= 9) return `${value.slice(0, 3)}.${value.slice(3, 6)}.${value.slice(6)}`;
  return `${value.slice(0, 3)}.${value.slice(3, 6)}.${value.slice(6, 9)}-${value.slice(9)}`;
}

function maskCnpj(raw: string): string {
  const value = digits(raw).slice(0, 14);
  if (value.length <= 2) return value;
  if (value.length <= 5) return `${value.slice(0, 2)}.${value.slice(2)}`;
  if (value.length <= 8) return `${value.slice(0, 2)}.${value.slice(2, 5)}.${value.slice(5)}`;
  if (value.length <= 12) return `${value.slice(0, 2)}.${value.slice(2, 5)}.${value.slice(5, 8)}/${value.slice(8)}`;
  return `${value.slice(0, 2)}.${value.slice(2, 5)}.${value.slice(5, 8)}/${value.slice(8, 12)}-${value.slice(12)}`;
}

function checkDigit(base: string, weights: number[]): number {
  const total = weights.reduce((sum, weight, index) => sum + Number(base[index]) * weight, 0);
  const rest = total % 11;
  return rest < 2 ? 0 : 11 - rest;
}

function validCpf(raw: string): boolean {
  const value = digits(raw);
  if (value.length !== 11 || /^(\d)\1+$/.test(value)) return false;
  const first = checkDigit(value, [10, 9, 8, 7, 6, 5, 4, 3, 2]);
  const second = checkDigit(value, [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]);
  return first === Number(value[9]) && second === Number(value[10]);
}

function validCnpj(raw: string): boolean {
  const value = digits(raw);
  if (value.length !== 14 || /^(\d)\1+$/.test(value)) return false;
  const first = checkDigit(value, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  const second = checkDigit(value, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  return first === Number(value[12]) && second === Number(value[13]);
}

function validCode(value: string): boolean {
  return value.length >= 2 && value.length <= 48 && CODE.test(value);
}

function activityNames(selected: string[]): string[] {
  return ACTIVITIES.filter((item) => selected.includes(item.id)).map((item) => item.label);
}

function placeSentence(names: string[]): string {
  if (names.length <= 1) return `Este local é dedicado a ${names[0]?.toLowerCase() ?? "uma atividade"}.`;
  if (names.length === 2) return `Neste local acontecem ${names[0].toLowerCase()} e ${names[1].toLowerCase()}.`;
  return "Neste local acontecem vendas, estoque e produção.";
}

export function FirstAccess() {
  const { me, reload, api } = useOrganization();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const sending = useRef(false);
  const state = me?.access_state ?? "sem_autorizacao";
  const [holderKind, setHolderKind] = useState<"natural_person" | "legal_entity">("natural_person");
  const [formalization, setFormalization] = useState<"not_formalized" | "self_employed">("not_formalized");
  const [tradeName, setTradeName] = useState("");
  const [holderName, setHolderName] = useState("");
  const [fiscalId, setFiscalId] = useState("");
  const [legalName, setLegalName] = useState("");
  const [organizationCode, setOrganizationCode] = useState("");
  const [codeTouched, setCodeTouched] = useState(false);
  const [establishmentName, setEstablishmentName] = useState("");
  const [establishmentCode, setEstablishmentCode] = useState("");
  const [establishmentTouched, setEstablishmentTouched] = useState(false);
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [codesOpen, setCodesOpen] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [pending, setPending] = useState(false);
  const [created, setCreated] = useState<Created | null>(null);

  const suggestedOrg = useMemo(() => suggestCode(tradeName), [tradeName]);
  const suggestedPlace = useMemo(() => suggestCode(establishmentName), [establishmentName]);
  const organization = codeTouched ? organizationCode : suggestedOrg;
  const placeCode = establishmentTouched ? establishmentCode : suggestedPlace;
  const names = activityNames(capabilities);
  const natural = holderKind === "natural_person";

  function toggleCapability(value: string) {
    setCapabilities((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
    setErrors((current) => ({ ...current, activities: undefined }));
  }

  async function leave() {
    api.clear();
    await logout();
    navigate("/entrar", { replace: true });
  }

  function validate(): boolean {
    const next: Partial<Record<Field, string>> = {};
    if (tradeName.trim().length < 2) next.trade = "Informe o nome que aparecerá na Panne.";
    if (holderName.trim().length < 2) next.holderName = "Informe o seu nome.";
    if (natural) {
      if (!validCpf(fiscalId)) next.fiscal = "Informe um CPF válido.";
    } else {
      if (legalName.trim().length < 2) next.legal = "Informe a razão social da empresa.";
      if (!validCnpj(fiscalId)) next.fiscal = "Informe um CNPJ válido.";
    }
    if (establishmentName.trim().length < 2) next.place = "Informe o nome do primeiro local.";
    if (capabilities.length === 0) next.activities = "Escolha ao menos uma atividade deste local.";
    if (!validCode(organization)) {
      next.organization = "Use letras minúsculas, números e hífen. Mínimo de dois caracteres.";
    }
    if (!validCode(placeCode)) {
      next.establishment = "Use letras minúsculas, números e hífen. Mínimo de dois caracteres.";
    }
    setErrors(next);
    if (next.organization || next.establishment) setCodesOpen(true);
    const first = (Object.keys(next) as Field[]).find((key) => next[key]);
    if (first) {
      const target =
        first === "activities"
          ? "atividade-vendas"
          : first === "organization"
            ? "identificador-negocio"
            : first === "establishment"
              ? "identificador-local"
              : first;
      window.setTimeout(() => document.getElementById(target)?.focus(), 0);
    }
    return !first;
  }

  function applyServer(message: string) {
    if (message.includes("código")) {
      setCodesOpen(true);
      setErrors({
        organization: message,
        form: "O identificador interno precisa ser outro. O restante do cadastro foi mantido.",
      });
      window.setTimeout(() => document.getElementById("identificador-negocio")?.focus(), 0);
      return;
    }
    if (message.includes("CPF") || message.includes("CNPJ")) {
      setErrors({ fiscal: message });
      window.setTimeout(() => document.getElementById("fiscal")?.focus(), 0);
      return;
    }
    if (message.includes("razão social")) {
      setErrors({ legal: message });
      window.setTimeout(() => document.getElementById("legal")?.focus(), 0);
      return;
    }
    setErrors({ form: message });
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (sending.current || pending) return;
    if (!validate()) return;
    sending.current = true;
    setPending(true);
    setErrors({});
    try {
      const result = await api.startClient({
        trade_name: tradeName.trim(),
        holder_kind: holderKind,
        holder_name: holderName.trim(),
        holder_fiscal_id: digits(fiscalId),
        formalization_state: natural ? formalization : "formalized",
        legal_name: natural ? null : legalName.trim(),
        organization_code: organization,
        establishment_name: establishmentName.trim(),
        establishment_code: placeCode,
        establishment_nature: capabilities.length > 1 ? "integrated" : "specialized",
        capabilities,
        accept_commercial_condition: true,
      });
      setCreated({ client: result.display_name, place: result.establishment_name });
    } catch (caught) {
      sending.current = false;
      setPending(false);
      if (caught instanceof ApiError && caught.code === "nao_autenticado") {
        setErrors({ form: "Sua entrada expirou. Saia e entre de novo com o mesmo código." });
        return;
      }
      applyServer(caught instanceof ApiError ? caught.message : "Não foi possível criar o espaço. Tente de novo.");
    }
  }

  async function finish() {
    if (!created) return;
    sessionStorage.setItem(WELCOME_KEY, JSON.stringify({ client: created.client, establishment: created.place }));
    api.clear();
    await reload();
  }

  const blocked =
    state === "autorizacao_expirada"
      ? "A autorização desta conta venceu. Peça uma nova à Panne e entre de novo com o mesmo e-mail."
      : state === "autorizacao_usada"
        ? "Esta autorização já foi usada para criar um negócio. Se precisar de outro espaço, fale com a Panne."
        : state === "autorizacao_de_outra_conta"
          ? "Esta autorização está ligada a outra conta. Saia e entre com a conta que recebeu o acesso."
          : state === "email_nao_confirmado"
            ? "O e-mail desta conta ainda não foi confirmado. Confirme o e-mail e entre de novo."
            : state === "autorizado"
              ? null
              : "Esta conta ainda não pode cadastrar um negócio. Peça a autorização à Panne e entre de novo.";

  return (
    <main className="setup">
      <div className="setup-frame">
        <header className="setup-header">
          <img src={logoHorizontal} alt="Panne" className="setup-mark" />
          <div className="setup-heading">
            <h1>{created ? "Seu espaço está pronto" : state === "convidado" ? "Você foi convidado" : "Vamos configurar seu negócio"}</h1>
            <p>
              {created
                ? "O negócio e o primeiro local já existem. O próximo passo é o painel inicial."
                : state === "convidado"
                  ? "Você entra em um negócio que já existe. Este passo não cria outro."
                  : "Diga o nome do negócio, quem responde por ele e o que acontece no primeiro local."}
            </p>
            {me?.account_email ? <p className="setup-email">{me.account_email}</p> : null}
          </div>
          <button type="button" className="ghost setup-leave" onClick={() => void leave()}>
            Sair
          </button>
        </header>

        {created ? (
          <section className="setup-panel" aria-live="polite">
            <h2>O que foi criado</h2>
            <dl className="setup-review">
              <div>
                <dt>Negócio</dt>
                <dd>{created.client}</dd>
              </div>
              <div>
                <dt>Local</dt>
                <dd>{created.place}</dd>
              </div>
            </dl>
            <button type="button" className="primary setup-submit" onClick={() => void finish()}>
              Ir para o painel
            </button>
          </section>
        ) : state === "convidado" ? (
          <InvitePanel name={me?.invite_organization_name} />
        ) : blocked ? (
          <section className="setup-panel">
            <p role="alert">{blocked}</p>
          </section>
        ) : (
          <form className="setup-panel" onSubmit={(event) => void submit(event)} noValidate>
            <section className="setup-block" aria-labelledby="negocio-titulo">
              <h2 id="negocio-titulo">Seu negócio</h2>
              <label htmlFor="trade">
                Nome que aparecerá na Panne
                <input
                  id="trade"
                  value={tradeName}
                  autoComplete="organization"
                  aria-invalid={Boolean(errors.trade)}
                  aria-describedby={errors.trade ? "trade-erro" : undefined}
                  onChange={(event) => {
                    setTradeName(event.target.value);
                    setErrors((current) => ({ ...current, trade: undefined }));
                  }}
                />
              </label>
              {errors.trade ? (
                <p id="trade-erro" className="setup-error" role="alert">
                  {errors.trade}
                </p>
              ) : null}

              <fieldset>
                <legend>Quem responde pelo negócio</legend>
                <div className="setup-options">
                  <label className="setup-choice">
                    <input
                      type="radio"
                      name="titular"
                      checked={natural}
                      onChange={() => {
                        setHolderKind("natural_person");
                        setFiscalId("");
                        setErrors({});
                      }}
                    />
                    <span>
                      <strong>Pessoa física</strong>
                      <small>Você responde pessoalmente por este negócio.</small>
                    </span>
                  </label>
                  <label className="setup-choice">
                    <input
                      type="radio"
                      name="titular"
                      checked={!natural}
                      onChange={() => {
                        setHolderKind("legal_entity");
                        setFiscalId("");
                        setErrors({});
                      }}
                    />
                    <span>
                      <strong>Pessoa jurídica</strong>
                      <small>O negócio está em nome de uma empresa.</small>
                    </span>
                  </label>
                </div>
              </fieldset>

              <label htmlFor="holderName">
                Seu nome
                <input
                  id="holderName"
                  value={holderName}
                  autoComplete="name"
                  aria-invalid={Boolean(errors.holderName)}
                  aria-describedby={errors.holderName ? "holder-erro" : undefined}
                  onChange={(event) => {
                    setHolderName(event.target.value);
                    setErrors((current) => ({ ...current, holderName: undefined }));
                  }}
                />
              </label>
              {errors.holderName ? (
                <p id="holder-erro" className="setup-error" role="alert">
                  {errors.holderName}
                </p>
              ) : null}

              {natural ? (
                <fieldset>
                  <legend>Situação do negócio</legend>
                  <div className="setup-options">
                    <label className="setup-choice">
                      <input
                        type="radio"
                        name="formalizacao"
                        checked={formalization === "not_formalized"}
                        onChange={() => setFormalization("not_formalized")}
                      />
                      <span>
                        <strong>Ainda sem empresa</strong>
                        <small>Pode ser formalizado depois, neste mesmo espaço, sem perder o histórico.</small>
                      </span>
                    </label>
                    <label className="setup-choice">
                      <input
                        type="radio"
                        name="formalizacao"
                        checked={formalization === "self_employed"}
                        onChange={() => setFormalization("self_employed")}
                      />
                      <span>
                        <strong>Em meu nome</strong>
                        <small>Você já atua em seu próprio nome.</small>
                      </span>
                    </label>
                  </div>
                </fieldset>
              ) : (
                <>
                  <label htmlFor="legal">
                    Razão social
                    <input
                      id="legal"
                      value={legalName}
                      aria-invalid={Boolean(errors.legal)}
                      aria-describedby={errors.legal ? "legal-erro" : undefined}
                      onChange={(event) => {
                        setLegalName(event.target.value);
                        setErrors((current) => ({ ...current, legal: undefined }));
                      }}
                    />
                  </label>
                  {errors.legal ? (
                    <p id="legal-erro" className="setup-error" role="alert">
                      {errors.legal}
                    </p>
                  ) : null}
                </>
              )}

              <label htmlFor="fiscal">
                {natural ? "CPF" : "CNPJ"}
                <input
                  id="fiscal"
                  inputMode="numeric"
                  autoComplete="off"
                  value={fiscalId}
                  aria-invalid={Boolean(errors.fiscal)}
                  aria-describedby={errors.fiscal ? "fiscal-erro" : "fiscal-ajuda"}
                  onChange={(event) => {
                    setFiscalId(natural ? maskCpf(event.target.value) : maskCnpj(event.target.value));
                    setErrors((current) => ({ ...current, fiscal: undefined }));
                  }}
                />
              </label>
              <p id="fiscal-ajuda" className="setup-hint">
                Usado só para identificar o titular. Depois de salvo, o número completo não volta a aparecer.
              </p>
              {errors.fiscal ? (
                <p id="fiscal-erro" className="setup-error" role="alert">
                  {errors.fiscal}
                </p>
              ) : null}
            </section>

            <section className="setup-block" aria-labelledby="local-titulo">
              <h2 id="local-titulo">Primeiro local de operação</h2>
              <p className="setup-hint">
                Um mesmo local pode reunir vendas, estoque e produção. Outros locais podem ser cadastrados depois.
              </p>
              <label htmlFor="place">
                Nome do local
                <input
                  id="place"
                  value={establishmentName}
                  aria-invalid={Boolean(errors.place)}
                  aria-describedby={errors.place ? "place-erro" : undefined}
                  onChange={(event) => {
                    setEstablishmentName(event.target.value);
                    setErrors((current) => ({ ...current, place: undefined }));
                  }}
                />
              </label>
              {errors.place ? (
                <p id="place-erro" className="setup-error" role="alert">
                  {errors.place}
                </p>
              ) : null}
              <fieldset>
                <legend>O que acontece neste local</legend>
                <div className="setup-options">
                  {ACTIVITIES.map((item) => (
                    <label className="setup-choice" key={item.id}>
                      <input
                        id={item.id === "sale" ? "atividade-vendas" : undefined}
                        type="checkbox"
                        checked={capabilities.includes(item.id)}
                        onChange={() => toggleCapability(item.id)}
                      />
                      <span>
                        <strong>{item.label}</strong>
                        <small>{item.hint}</small>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
              {errors.activities ? (
                <p className="setup-error" role="alert">
                  {errors.activities}
                </p>
              ) : null}
            </section>

            <section className="setup-block" aria-labelledby="revisao-titulo">
              <h2 id="revisao-titulo">Revisar e criar</h2>
              <dl className="setup-review">
                <div>
                  <dt>Negócio</dt>
                  <dd>{tradeName.trim() || "Ainda sem nome"}</dd>
                </div>
                <div>
                  <dt>Titular</dt>
                  <dd>
                    {natural
                      ? formalization === "not_formalized"
                        ? "Pessoa física, ainda sem empresa"
                        : "Pessoa física, em seu nome"
                      : legalName.trim()
                        ? `Pessoa jurídica, ${legalName.trim()}`
                        : "Pessoa jurídica"}
                  </dd>
                </div>
                <div>
                  <dt>Local</dt>
                  <dd>{establishmentName.trim() || "Ainda sem nome"}</dd>
                </div>
                <div>
                  <dt>Atividades</dt>
                  <dd>{names.length ? placeSentence(names) : "Nenhuma atividade escolhida"}</dd>
                </div>
                <div>
                  <dt>Condição desta conta</dt>
                  <dd>{me?.commercial_condition_label || "Definida pela Panne para esta conta."}</dd>
                </div>
              </dl>
              <p className="setup-hint">
                A condição foi atribuída pela Panne e não pode ser alterada aqui. Ao criar, você entra no painel inicial.
              </p>
              {errors.form ? (
                <p className="setup-error" role="alert">
                  {errors.form}
                </p>
              ) : null}
              <button type="submit" className="primary setup-submit" disabled={pending} aria-busy={pending}>
                {pending ? "Criando seu espaço…" : "Criar meu espaço na Panne"}
              </button>
            </section>

            <details
              className="setup-advanced"
              open={codesOpen}
              onToggle={(event) => setCodesOpen((event.currentTarget as HTMLDetailsElement).open)}
            >
              <summary>Identificador interno</summary>
              <p className="setup-hint">
                A Panne sugere um identificador a partir dos nomes. Altere só se precisar de outro.
              </p>
              <label htmlFor="identificador-negocio">
                Identificador do negócio
                <input
                  id="identificador-negocio"
                  value={organization}
                  spellCheck={false}
                  aria-invalid={Boolean(errors.organization)}
                  aria-describedby={errors.organization ? "org-erro" : undefined}
                  onChange={(event) => {
                    setCodeTouched(true);
                    setOrganizationCode(suggestCode(event.target.value));
                    setErrors((current) => ({ ...current, organization: undefined, form: undefined }));
                  }}
                />
              </label>
              {errors.organization ? (
                <p id="org-erro" className="setup-error" role="alert">
                  {errors.organization}
                </p>
              ) : null}
              <label htmlFor="identificador-local">
                Identificador do local
                <input
                  id="identificador-local"
                  value={placeCode}
                  spellCheck={false}
                  aria-invalid={Boolean(errors.establishment)}
                  aria-describedby={errors.establishment ? "est-erro" : undefined}
                  onChange={(event) => {
                    setEstablishmentTouched(true);
                    setEstablishmentCode(suggestCode(event.target.value));
                    setErrors((current) => ({ ...current, establishment: undefined }));
                  }}
                />
              </label>
              {errors.establishment ? (
                <p id="est-erro" className="setup-error" role="alert">
                  {errors.establishment}
                </p>
              ) : null}
            </details>

            <details className="setup-help">
              <summary>Ajuda</summary>
              <p>
                O primeiro local pode vender, guardar estoque e produzir ao mesmo tempo. Se o identificador sugerido já
                existir, abra Identificador interno e escolha outro. A condição da conta permanece a que a Panne definiu.
              </p>
            </details>
          </form>
        )}

        <aside className="setup-aside">
          <p>Quem se cadastra é a pessoa desta conta.</p>
          <p>O primeiro local pode reunir vendas, estoque e produção.</p>
          <p>Ao concluir, o negócio e o local passam a existir e você entra no painel inicial.</p>
        </aside>
      </div>
    </main>
  );
}

function InvitePanel({ name }: { name?: string | null }) {
  const { api, reload } = useOrganization();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const sending = useRef(false);

  async function accept() {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    setError(null);
    try {
      const result = await api.acceptInvitation();
      sessionStorage.setItem(
        WELCOME_KEY,
        JSON.stringify({ client: result.display_name, establishment: result.establishment_name }),
      );
      api.clear();
      await reload();
    } catch (caught) {
      sending.current = false;
      setPending(false);
      setError(caught instanceof ApiError ? caught.message : "Não foi possível entrar neste negócio.");
    }
  }

  return (
    <section className="setup-panel">
      <h2>{name || "Negócio convidado"}</h2>
      <p>Confirme para entrar neste negócio. Nenhum outro espaço será criado.</p>
      {error ? (
        <p className="setup-error" role="alert">
          {error}
        </p>
      ) : null}
      <button type="button" className="primary setup-submit" disabled={pending} onClick={() => void accept()}>
        {pending ? "Entrando…" : "Entrar neste negócio"}
      </button>
    </section>
  );
}
