import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/errors";
import { useAuth } from "../auth/AuthContext";
import { useOrganization } from "../session/OrganizationContext";

const WELCOME_KEY = "panne.welcome";

function suggestCode(value: string): string {
  const plain = value.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  return plain
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

export function FirstAccess() {
  const { me, reload, api } = useOrganization();
  const { logout } = useAuth();
  const navigate = useNavigate();
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
  const [nature, setNature] = useState<"integrated" | "specialized">("integrated");
  const [capabilities, setCapabilities] = useState<string[]>(["sale", "stock", "production"]);
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const suggested = useMemo(() => suggestCode(tradeName), [tradeName]);
  const code = codeTouched ? organizationCode : suggested || organizationCode;
  const placeCode = establishmentTouched ? establishmentCode : suggested || establishmentCode;

  function toggleCapability(value: string) {
    setCapabilities((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  }

  async function leave() {
    await logout();
    navigate("/entrar", { replace: true });
  }

  async function finish(client: string, establishment: string) {
    try {
      sessionStorage.setItem(WELCOME_KEY, JSON.stringify({ client, establishment }));
    } catch {
      /* a confirmação também aparece na resposta */
    }
    api.clear();
    await reload();
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const created = await api.startClient({
        trade_name: tradeName,
        holder_kind: holderKind,
        holder_name: holderName,
        holder_fiscal_id: fiscalId,
        formalization_state: holderKind === "legal_entity" ? "formalized" : formalization,
        legal_name: holderKind === "legal_entity" ? legalName : null,
        organization_code: code,
        establishment_name: establishmentName,
        establishment_code: placeCode,
        establishment_nature: nature,
        capabilities,
        accept_commercial_condition: accepted,
      });
      await finish(created.display_name, created.establishment_name);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Não foi possível concluir o cadastro.");
    } finally {
      setPending(false);
    }
  }

  async function continueInvite() {
    setError(null);
    setPending(true);
    try {
      const created = await api.acceptInvitation();
      await finish(created.display_name, created.display_name);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Não foi possível continuar o convite.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="first-access">
      <h1>Primeiro acesso</h1>
      {state === "convidado" ? (
        <>
          <p>
            Há um convite para você entrar em {me?.invite_organization_name || "um cliente da Panne"}.
          </p>
          <button type="button" className="primary" disabled={pending} onClick={() => void continueInvite()}>
            Continuar convite
          </button>
        </>
      ) : null}
      {state === "sem_autorizacao" ? (
        <p>Sua conta ainda não tem autorização da Panne para cadastrar um cliente.</p>
      ) : null}
      {state === "autorizacao_expirada" ? (
        <p>A autorização para cadastrar este cliente expirou. Fale com a Panne.</p>
      ) : null}
      {state === "autorizacao_usada" ? <p>Esta autorização já foi utilizada.</p> : null}
      {state === "autorizacao_de_outra_conta" ? (
        <p>Esta autorização não corresponde a esta conta.</p>
      ) : null}
      {state === "email_nao_confirmado" ? (
        <p>Não foi possível confirmar o e-mail desta conta. Saia e entre de novo.</p>
      ) : null}
      {state === "autorizado" ? (
        <form onSubmit={(event) => void submit(event)}>
          <p>Cadastre o cliente da Panne e o primeiro estabelecimento. A Panne continua sendo a fornecedora do sistema.</p>
          <p>{me?.commercial_condition_label}</p>
          <label>
            Nome comercial
            <input value={tradeName} onChange={(event) => setTradeName(event.target.value)} required autoComplete="organization" />
          </label>
          <fieldset>
            <legend>Titular</legend>
            <label>
              <input
                type="radio"
                name="holder"
                checked={holderKind === "natural_person"}
                onChange={() => setHolderKind("natural_person")}
              />
              Pessoa física
            </label>
            <label>
              <input
                type="radio"
                name="holder"
                checked={holderKind === "legal_entity"}
                onChange={() => setHolderKind("legal_entity")}
              />
              Pessoa jurídica
            </label>
          </fieldset>
          <label>
            Nome do titular
            <input value={holderName} onChange={(event) => setHolderName(event.target.value)} required autoComplete="name" />
          </label>
          {holderKind === "natural_person" ? (
            <fieldset>
              <legend>Formalização</legend>
              <label>
                <input
                  type="radio"
                  name="formalization"
                  checked={formalization === "not_formalized"}
                  onChange={() => setFormalization("not_formalized")}
                />
                Ainda sem empresa formalizada
              </label>
              <label>
                <input
                  type="radio"
                  name="formalization"
                  checked={formalization === "self_employed"}
                  onChange={() => setFormalization("self_employed")}
                />
                Atuo em nome próprio
              </label>
            </fieldset>
          ) : (
            <label>
              Razão social
              <input value={legalName} onChange={(event) => setLegalName(event.target.value)} required />
            </label>
          )}
          <label>
            {holderKind === "legal_entity" ? "CNPJ" : "CPF do titular"}
            <input
              value={fiscalId}
              onChange={(event) => setFiscalId(event.target.value)}
              required
              inputMode="numeric"
              autoComplete="off"
              aria-describedby="fiscal-hint"
            />
          </label>
          <p id="fiscal-hint" className="meta">
            O identificador fica no cadastro do cliente e não volta completo para a tela.
          </p>
          <label>
            Código do cliente
            <input
              value={code}
              onChange={(event) => {
                setCodeTouched(true);
                setOrganizationCode(event.target.value);
              }}
              required
            />
          </label>
          <label>
            Nome do estabelecimento
            <input value={establishmentName} onChange={(event) => setEstablishmentName(event.target.value)} required />
          </label>
          <label>
            Código do estabelecimento
            <input
              value={placeCode}
              onChange={(event) => {
                setEstablishmentTouched(true);
                setEstablishmentCode(event.target.value);
              }}
              required
            />
          </label>
          <label>
            Natureza
            <select value={nature} onChange={(event) => setNature(event.target.value as "integrated" | "specialized")}>
              <option value="integrated">Um lugar com as capacidades escolhidas</option>
              <option value="specialized">Estabelecimento especializado</option>
            </select>
          </label>
          <fieldset>
            <legend>Capacidades iniciais</legend>
            {[
              ["sale", "Venda"],
              ["stock", "Estoque"],
              ["production", "Produção"],
            ].map(([value, label]) => (
              <label key={value}>
                <input
                  type="checkbox"
                  checked={capabilities.includes(value)}
                  onChange={() => toggleCapability(value)}
                />
                {label}
              </label>
            ))}
          </fieldset>
          <label>
            <input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} required />
            Aceito a condição comercial apresentada
          </label>
          <button type="submit" className="primary" disabled={pending}>
            {pending ? "Cadastrando…" : "Cadastrar cliente"}
          </button>
        </form>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
      <p>
        <button type="button" className="ghost" onClick={() => void leave()}>
          Sair
        </button>
      </p>
      <p>Se você não reconhece esta situação, saia da conta e fale com o suporte da Panne.</p>
    </main>
  );
}
