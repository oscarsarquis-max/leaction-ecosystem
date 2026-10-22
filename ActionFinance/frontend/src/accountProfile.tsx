import { useEffect, useRef, useState } from "react";
import {
  companyQuery,
  freezeWrite,
  isUnknownWriteOutcome,
  request,
  sendPending,
  type AccountContact,
  type ApiError,
  type FinancialAccount,
  type PendingWrite,
} from "./api";
import { formatDateBr, parseSignedBrlInput } from "./money";
import { canWriteAccounts } from "./session";

export type AccountTab = "dados" | "movimentos" | "acesso";

const RETURN_KEY = "af-account-return";

export function accountTab(): AccountTab {
  const value = new URLSearchParams(window.location.search).get("aba");
  if (value === "movimentos" || value === "acesso") {
    return value;
  }
  return "dados";
}

export function rememberAccountReturn(id: string, tab: AccountTab) {
  sessionStorage.setItem(RETURN_KEY, JSON.stringify({ id, tab }));
}

export function accountReturnPath(id: string): string {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(RETURN_KEY) || "null") as { id?: string; tab?: string } | null;
    if (parsed?.id === id && (parsed.tab === "movimentos" || parsed.tab === "acesso")) {
      return `/financial-accounts/${id}?aba=${parsed.tab}`;
    }
  } catch {
    return `/financial-accounts/${id}`;
  }
  return `/financial-accounts/${id}`;
}

export function maskAccountNumber(value: string | null | undefined): string {
  const text = (value ?? "").trim();
  if (!text) {
    return "";
  }
  if (text.length <= 4) {
    return "••••";
  }
  return `••••${text.slice(-4)}`;
}

export function modalityLabel(value: string | null | undefined): string {
  return {
    CHECKING: "Conta corrente",
    SAVINGS: "Poupança",
    INVESTMENT: "Investimento",
    PAYMENT: "Conta de pagamento",
  }[value ?? ""] ?? "";
}

export function roleLabel(value: string | null | undefined): string {
  return {
    ACCOUNT_MANAGER: "Gerente da conta",
    BRANCH_MANAGER: "Gerente da agência",
    SERVICE: "Atendimento",
    OTHER: "Outra função",
  }[value ?? ""] ?? "Função não informada";
}

export function associationLabel(value: string | null | undefined): string {
  return {
    ACCOUNT: "Conta",
    BRANCH: "Agência",
    INSTITUTION: "Instituição",
  }[value ?? ""] ?? "";
}

function shown(value: string | null | undefined): string {
  const text = (value ?? "").trim();
  return text || "Não informado";
}

function todayLocal(): string {
  const date = new Date();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function countryLabel(value: string | null | undefined): string {
  if ((value ?? "").trim().toUpperCase() === "BR") {
    return "Brasil";
  }
  return shown(value);
}

type DraftContact = {
  personName: string;
  role: string;
  email: string;
  phone: string;
  primaryContact: boolean;
  association: string;
};

function emptyContact(): DraftContact {
  return { personName: "", role: "ACCOUNT_MANAGER", email: "", phone: "", primaryContact: false, association: "ACCOUNT" };
}

function profileOf(account: FinancialAccount | null | undefined) {
  return account?.profile ?? null;
}

export function bankIdentityMissing(account: FinancialAccount): boolean {
  if (account.type !== "BANK") {
    return false;
  }
  const profile = profileOf(account);
  return !profile?.institutionName?.trim() || !profile.accountNumber?.trim() || !profile.modality?.trim();
}

type ConfirmedImport = {
  id: string;
  status: string;
  periodFrom?: string | null;
  periodTo?: string | null;
  rejectedCount?: number;
  fileName?: string;
};

export function AccountDataTab({
  account,
  revealed,
  onToggleNumber,
  onEdit,
  onStatus,
  statusBusy,
}: {
  account: FinancialAccount;
  revealed: boolean;
  onToggleNumber: () => void;
  onEdit: (focus?: "contacts") => void;
  onStatus: () => void;
  statusBusy: boolean;
}) {
  const profile = profileOf(account);
  const contacts = profile?.contacts ?? [];
  const missing = bankIdentityMissing(account);
  const canEdit = canWriteAccounts();
  const number = profile?.accountNumber?.trim() ?? "";
  const branch = [profile?.branchNumber, profile?.branchDigit].filter(Boolean).join("-");
  const accountLine = [number, profile?.accountDigit].filter(Boolean).join("-");
  const next = missing
    ? { title: "Próximo passo", text: "Banco, número e modalidade ainda não foram informados.", action: "Completar dados", run: () => onEdit() }
    : { title: "Próximo passo", text: "O cadastro não comprova acesso ao banco.", action: "Ver acesso e importação", run: () => onEdit() };
  return (
    <div className="ac-layout">
      <div className="ac-main">
        {missing ? (
          <section className="ac-card ac-call">
            <h2>Complete os dados desta conta</h2>
            <p>O apelido não define instituição, número, modalidade nem titularidade.</p>
            {canEdit ? <button type="button" onClick={() => onEdit()}>Completar dados</button> : <p>Você pode consultar estes dados. Quem altera a conta completa a identificação.</p>}
          </section>
        ) : null}
        <section className="ac-card" aria-label="Identificação">
          <h2>Identificação</h2>
          <dl className="ac-facts">
            <div><dt>Banco ou instituição</dt><dd>{shown(profile?.institutionName)}</dd></div>
            <div><dt>Código do banco</dt><dd>{shown(profile?.bankCode)}</dd></div>
            <div><dt>Modalidade</dt><dd>{profile?.modality ? modalityLabel(profile.modality) : "Não informado"}</dd></div>
            <div><dt>Agência</dt><dd>{branch ? (revealed ? branch : maskAccountNumber(profile?.branchNumber)) : "Não informado"}</dd></div>
            <div>
              <dt>Número da conta</dt>
              <dd>
                {number ? (revealed ? accountLine : maskAccountNumber(number)) : "Não informado"}
                {number ? (
                  <button type="button" className="secondary ac-inline" onClick={onToggleNumber}>
                    {revealed ? "Ocultar" : "Mostrar número"}
                  </button>
                ) : null}
              </dd>
            </div>
            <div><dt>Moeda</dt><dd>BRL · Real</dd></div>
            <div><dt>País</dt><dd>{countryLabel(profile?.countryCode)}</dd></div>
            <div><dt>Apelido</dt><dd>{shown(account.name)}</dd></div>
            <div><dt>Código interno</dt><dd>{account.code}<span className="ac-kind">Não é o número bancário.</span></dd></div>
          </dl>
          {profile?.modality === "INVESTMENT" ? (
            <p className="ac-meta">Investimento é a modalidade do cadastro. Isso não transforma a posição em dinheiro disponível.</p>
          ) : null}
        </section>
        <section className="ac-card" aria-label="Contatos do banco">
          <h2>Contatos do banco</h2>
          <dl className="ac-facts">
            <div><dt>E-mail institucional</dt><dd>{shown(profile?.institutionEmail)}</dd></div>
            <div><dt>Telefone de atendimento</dt><dd>{shown(profile?.institutionPhone)}</dd></div>
          </dl>
          {contacts.length === 0 ? <p>Nenhum contato informado</p> : (
            <ul className="ac-contacts">
              {contacts.map((contact) => (
                <li key={contact.id || contact.personName}>
                  <strong>{contact.personName}</strong>
                  {contact.primaryContact ? <span className="ac-kind">Principal</span> : null}
                  <span className="ac-kind">{roleLabel(contact.role)} · {associationLabel(contact.association)}</span>
                  <span className="ac-kind">{shown(contact.email)} · {shown(contact.phone)}</span>
                </li>
              ))}
            </ul>
          )}
          {canEdit ? <button type="button" className="secondary" onClick={() => onEdit("contacts")}>Adicionar contato</button> : null}
        </section>
        <section className="ac-card ac-status-card" aria-label="Situação da conta">
          <h2>Situação da conta</h2>
          <p>{account.active ? "Ativa para novos registros." : "Inativa para novos registros."} Inativar impede novos registros nesta conta. Movimentos e extratos já gravados permanecem.</p>
          {canEdit ? (
            <button type="button" className="secondary" disabled={statusBusy} onClick={onStatus}>
              {account.active ? "Inativar" : "Reativar"}
            </button>
          ) : null}
        </section>
      </div>
      <aside className="ac-side" aria-label="Resumo da conta">
        <section className="ac-card">
          <h2>Resumo</h2>
          <dl className="ac-facts ac-facts-one">
            <div><dt>Empresa</dt><dd>{shown(account.companyName)}</dd></div>
            <div><dt>Moeda</dt><dd>BRL · Real</dd></div>
            <div><dt>Situação</dt><dd>{account.active ? "Ativa" : "Inativa"}</dd></div>
          </dl>
          {account.updatedAt ? <p className="ac-meta">Alterada em {formatDateBr(account.updatedAt.slice(0, 10))}.</p> : null}
        </section>
        <section className="ac-card">
          <h2>{next.title}</h2>
          <p>{next.text}</p>
          {missing ? (
            canEdit ? <button type="button" onClick={next.run}>{next.action}</button> : null
          ) : (
            <button type="button" onClick={() => {
              const url = new URL(window.location.href);
              url.searchParams.set("aba", "acesso");
              window.history.pushState(null, "", `${url.pathname}${url.search}`);
              window.dispatchEvent(new PopStateEvent("popstate"));
            }}>Ver acesso e importação</button>
          )}
        </section>
      </aside>
    </div>
  );
}

export function AccountAccessTab({
  account,
  imports,
  onImport,
}: {
  account: FinancialAccount;
  imports: ConfirmedImport[] | null;
  onImport: () => void;
}) {
  const latest = imports?.[0];
  const links = account.originLinks ?? [];
  return (
    <div className="ac-layout">
      <div className="ac-main">
        <section className="ac-card" aria-label="Importação por arquivo">
          <h2>Importação por arquivo</h2>
          <p>O cadastro da conta não comprova acesso bancário. O Finance lê o relatório de liquidação do Mercado Pago, em CSV com ponto e vírgula, e o CSV de laboratório, com vírgula e as colunas DATE, SOURCE_ID e RECORD_TYPE.</p>
          {latest ? (
            <p>
              Última importação confirmada{latest.fileName ? `: ${latest.fileName}` : ""}.
              {latest.periodFrom && latest.periodTo ? ` Período ${formatDateBr(latest.periodFrom)} a ${formatDateBr(latest.periodTo)}.` : ""}
              {` ${latest.rejectedCount || 0} em revisão.`}
            </p>
          ) : imports ? <p>Nenhuma importação confirmada nesta conta.</p> : <p>Consultando importações…</p>}
          <button type="button" onClick={onImport}>Importar extrato</button>
        </section>
        <section className="ac-card" aria-label="Vínculos de origem">
          <h2>Vínculos de origem</h2>
          {links.length === 0 ? (
            <p>Nenhum vínculo de origem confirmado. O número bancário cadastrado não substitui essa referência.</p>
          ) : links.map((link) => (
            <p key={link.createdAt + link.originLabel}>
              <strong>{link.originLabel}</strong>
              <span className="ac-kind">{link.provenance}</span>
            </p>
          ))}
        </section>
        <section className="ac-card" aria-label="Conexão automática">
          <h2>Conexão automática</h2>
          <p><strong>Conexão automática ainda não disponível.</strong> Não há conector autorizado para consultar o banco. Importe um arquivo compatível. Nenhuma senha bancária é pedida aqui.</p>
        </section>
      </div>
      <aside className="ac-side">
        <section className="ac-card">
          <h2>Como os dados chegam</h2>
          <p>Arquivo importado e conexão automática são caminhos diferentes. Os dois preservam o extrato já gravado.</p>
        </section>
      </aside>
    </div>
  );
}

export function AccountEditor({
  mode,
  initial,
  companyName,
  initialType,
  onDirty,
  onCancel,
  onSaved,
}: {
  mode: "create" | "edit";
  initial?: FinancialAccount | null;
  companyName: string;
  initialType?: string;
  onDirty: (value: boolean) => void;
  onCancel: () => void;
  onSaved: (account: FinancialAccount) => void;
}) {
  const profile = profileOf(initial);
  const [type, setType] = useState(initial?.type || initialType || "");
  const [institution, setInstitution] = useState(profile?.institutionName || "");
  const [number, setNumber] = useState(profile?.accountNumber || "");
  const [modality, setModality] = useState(profile?.modality || "");
  const [nickname, setNickname] = useState(mode === "edit" ? initial?.name || "" : "");
  const [country, setCountry] = useState(profile?.countryCode || "");
  const [bankCode, setBankCode] = useState(profile?.bankCode || "");
  const [branch, setBranch] = useState(profile?.branchNumber || "");
  const [branchDigit, setBranchDigit] = useState(profile?.branchDigit || "");
  const [accountDigit, setAccountDigit] = useState(profile?.accountDigit || "");
  const [email, setEmail] = useState(profile?.institutionEmail || "");
  const [phone, setPhone] = useState(profile?.institutionPhone || "");
  const [contacts, setContacts] = useState<DraftContact[]>(
    (profile?.contacts ?? []).map((contact) => ({
      personName: contact.personName,
      role: contact.role,
      email: contact.email || "",
      phone: contact.phone || "",
      primaryContact: contact.primaryContact,
      association: contact.association,
    })),
  );
  const [openedOn, setOpenedOn] = useState(mode === "edit" ? initial?.openedOn || "" : todayLocal());
  const [opening, setOpening] = useState("");
  const [more, setMore] = useState(window.location.hash === "#contatos");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const [conflict, setConflict] = useState("");
  const [snapshot, setSnapshot] = useState("");
  const [version, setVersion] = useState(initial?.version ?? 0);
  const pending = useRef<PendingWrite | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);

  useEffect(() => {
    if (window.location.hash === "#contatos") {
      document.getElementById("contatos")?.focus();
    }
  }, []);

  const previewName = nickname.trim()
    || (type === "BANK" && institution.trim() ? `${institution.trim()} ${maskAccountNumber(number)}`.trim() : "")
    || "Conta sem apelido";

  const patchContact = (index: number, patch: Partial<DraftContact>) => {
    setContacts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  };

  const buildProfile = () => ({
    institutionName: institution.trim(),
    bankCode: bankCode.trim(),
    modality: type === "BANK" ? modality : "",
    branchNumber: branch.trim(),
    branchDigit: branchDigit.trim(),
    accountNumber: number.trim(),
    accountDigit: accountDigit.trim(),
    countryCode: country.trim().toUpperCase(),
    institutionEmail: email.trim(),
    institutionPhone: phone.trim(),
    contacts: contacts
      .filter((contact) => contact.personName.trim())
      .map((contact) => ({
        personName: contact.personName.trim(),
        role: contact.role,
        email: contact.email.trim(),
        phone: contact.phone.trim(),
        primaryContact: contact.primaryContact,
        association: contact.association,
      })),
  });

  const clientErrors = (): Record<string, string> => {
    const next: Record<string, string> = {};
    if (!type) {
      next.type = "Escolha banco, caixa físico ou outra conta.";
    }
    if (type === "BANK") {
      const creating = mode === "create";
      const any = institution.trim() || number.trim() || modality;
      if (creating || any) {
        if (!institution.trim()) next.institutionName = "Informe o banco ou a instituição.";
        if (!number.trim()) next.accountNumber = "Informe o número da conta.";
        if (!modality) next.modality = "Escolha a modalidade.";
      }
    }
    if (type === "CASH" && (institution.trim() || number.trim() || modality || bankCode.trim() || branch.trim())) {
      next.type = "Caixa físico é identificado pelo nome e não usa dados bancários.";
    }
    if ((type === "CASH" || type === "OTHER") && !nickname.trim()) {
      next.name = "Informe o nome da conta.";
    }
    if (type === "OTHER" && (number.trim() || modality || bankCode.trim() || branch.trim())) {
      next.type = "Outra conta não usa número, agência nem modalidade bancária.";
    }
    if (number.trim() && !/^[0-9A-Za-z][0-9A-Za-z./-]{0,31}$/.test(number.trim())) {
      next.accountNumber = "Use letras, números e os sinais . - /. O número não é a chave interna.";
    }
    if (mode === "create" && !openedOn) {
      next.openedOn = "Informe a data de início do controle.";
    }
    if (opening.trim()) {
      const parsed = parseSignedBrlInput(opening);
      if (parsed.error || parsed.minor == null) {
        next.openingBalanceMinor = parsed.error ?? "Informe o saldo em reais, como 1.234,56, ou deixe em branco.";
      }
    }
    const emailOk = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
    if (email.trim() && !emailOk(email)) {
      next.institutionEmail = "Informe um e-mail institucional válido ou deixe em branco.";
    }
    const filled = contacts.filter((contact) => contact.personName.trim());
    if (filled.filter((contact) => contact.primaryContact).length > 1) {
      next.contacts = "Marque apenas um contato principal.";
    }
    contacts.forEach((contact, index) => {
      if (contact.email.trim() && !emailOk(contact.email)) {
        next[`contacts.${index}.email`] = "Informe um e-mail profissional válido ou deixe em branco.";
      }
    });
    return next;
  };

  const focusFirst = (next: Record<string, string>) => {
    const optional = ["name", "countryCode", "bankCode", "branchNumber", "branchDigit", "accountDigit", "institutionEmail", "institutionPhone", "contacts"];
    if (Object.keys(next).some((key) => optional.includes(key) || key.startsWith("contacts"))) {
      setMore(true);
    }
    const order = ["institutionName", "accountNumber", "modality", "type", "name", "openedOn", "openingBalanceMinor", "institutionEmail", "bankCode", "branchNumber", "contacts"];
    const first = order.find((key) => next[key]) || Object.keys(next)[0];
    window.setTimeout(() => {
      const node = formRef.current?.querySelector<HTMLElement>(`[data-field="${first}"]`);
      node?.focus();
    }, 0);
  };

  const send = (existing?: PendingWrite | null, nextVersion = version) => {
    const found = existing ? {} : clientErrors();
    if (!existing && Object.keys(found).length > 0) {
      setErrors(found);
      setFormError("");
      focusFirst(found);
      return;
    }
    let openingMinor: string | null = null;
    if (opening.trim()) {
      openingMinor = parseSignedBrlInput(opening).minor ?? null;
    }
    setBusy(true);
    setFormError("");
    setErrors({});
    const body = mode === "create"
      ? { name: nickname.trim(), type, openedOn, openingBalanceMinor: openingMinor, profile: buildProfile() }
      : { name: nickname.trim(), version: nextVersion, profile: buildProfile() };
    pending.current = freezeWrite(
      mode === "create"
        ? `/api/v1/financial-accounts?${companyQuery()}`
        : `/api/v1/financial-accounts/${initial?.id}?${companyQuery()}`,
      mode === "create" ? "POST" : "PATCH",
      body,
      existing,
    );
    void sendPending<FinancialAccount>(pending.current)
      .then((account) => {
        pending.current = null;
        setUnknownResult(false);
        setConflict("");
        onDirty(false);
        onSaved(account);
      })
      .catch((caught: ApiError) => {
        if (caught.code === "VERSION_CONFLICT") {
          pending.current = null;
          setUnknownResult(false);
          setConflict(caught.message || "Esta conta foi alterada por outra pessoa. Confira os dados atuais antes de salvar de novo.");
          return;
        }
        if (isUnknownWriteOutcome(caught)) {
          setUnknownResult(true);
          setFormError("Não foi possível confirmar o resultado. Tente novamente para repetir a mesma operação.");
          return;
        }
        pending.current = null;
        setUnknownResult(false);
        const fields = caught.fields ?? {};
        if (Object.keys(fields).length > 0) {
          setErrors(fields);
          focusFirst(fields);
          setFormError("");
          return;
        }
        setFormError(caught.message);
      })
      .finally(() => setBusy(false));
  };

  const reviewCurrent = () => {
    if (!initial) {
      return;
    }
    void request<FinancialAccount>(`/api/v1/financial-accounts/${initial.id}?${companyQuery()}`)
      .then((account) => {
        const saved = account.profile;
        setVersion(account.version);
        setSnapshot(`${account.name}. ${saved?.institutionName || "Instituição não informada"}. ${saved?.accountNumber ? maskAccountNumber(saved.accountNumber) : "Número não informado"}. Versão conferida.`);
      })
      .catch((caught: ApiError) => setFormError(caught.message));
  };

  const bank = type === "BANK";
  const named = type === "CASH" || type === "OTHER";

  return (
    <div className="ac-layout">
      <form
        ref={formRef}
        className="ac-form"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          if (unknownResult) {
            return;
          }
          send(null);
        }}
        onChange={() => onDirty(true)}
      >
        <p className="ac-meta">A conta fica na empresa {companyName || "selecionada"}. Os lançamentos usam BRL · Real.</p>
        <label className="ac-field">
          Tipo
          <select data-field="type" value={type} aria-invalid={Boolean(errors.type)} disabled={mode === "edit" || unknownResult} onChange={(event) => setType(event.target.value)}>
            <option value="">Selecione</option>
            <option value="BANK">Banco ou instituição de pagamento</option>
            <option value="CASH">Caixa físico</option>
            <option value="OTHER">Outra conta</option>
          </select>
          {errors.type ? <span className="error" role="alert">{errors.type}</span> : null}
        </label>
        <span className="ac-kind">
          {type === "CASH"
            ? "Caixa físico é identificado pelo nome. Não pede banco, agência nem número."
            : type === "OTHER"
              ? "Outra conta tem identificação própria e não precisa imitar uma conta bancária."
              : "Banco pede a instituição, o número e a modalidade. A modalidade é explícita, também para conta de pagamento."}
        </span>
        {bank ? (
          <>
            <label className="ac-field ac-span">
              Banco ou instituição
              <input data-field="institutionName" value={institution} aria-invalid={Boolean(errors.institutionName)} disabled={unknownResult} maxLength={120} onChange={(event) => setInstitution(event.target.value)} />
              {errors.institutionName ? <span className="error" role="alert">{errors.institutionName}</span> : null}
            </label>
            <div className="ac-pair">
              <label className="ac-field">
                Número da conta
                <input data-field="accountNumber" value={number} aria-invalid={Boolean(errors.accountNumber)} disabled={unknownResult} maxLength={32} inputMode="text" onChange={(event) => setNumber(event.target.value)} />
                {errors.accountNumber ? <span className="error" role="alert">{errors.accountNumber}</span> : null}
              </label>
              <label className="ac-field">
                Modalidade
                <select data-field="modality" value={modality} aria-invalid={Boolean(errors.modality)} disabled={unknownResult} onChange={(event) => setModality(event.target.value)}>
                  <option value="">Selecione</option>
                  <option value="CHECKING">Conta corrente</option>
                  <option value="SAVINGS">Poupança</option>
                  <option value="INVESTMENT">Investimento</option>
                  <option value="PAYMENT">Conta de pagamento</option>
                </select>
                {errors.modality ? <span className="error" role="alert">{errors.modality}</span> : null}
              </label>
            </div>
          </>
        ) : null}
        {named ? (
          <label className="ac-field">
            Nome
            <input data-field="name" value={nickname} aria-invalid={Boolean(errors.name)} disabled={unknownResult} maxLength={100} onChange={(event) => setNickname(event.target.value)} />
            {errors.name ? <span className="error" role="alert">{errors.name}</span> : null}
          </label>
        ) : null}
        <p className="ac-field ac-static"><span>Moeda</span><strong>BRL · Real</strong><span className="ac-kind">O Finance registra os valores em real.</span></p>
        {mode === "create" ? (
          <>
          <label className="ac-field">
            Início do controle
            <input data-field="openedOn" type="date" value={openedOn} aria-invalid={Boolean(errors.openedOn)} disabled={unknownResult} onChange={(event) => setOpenedOn(event.target.value)} />
            {errors.openedOn ? <span className="error" role="alert">{errors.openedOn}</span> : null}
          </label>
          <span className="ac-kind">É a data em que o controle começa nesta empresa, não a abertura no banco.</span>
          </>
        ) : (
          <p className="ac-field ac-static"><span>Início do controle</span><strong>{openedOn ? formatDateBr(openedOn) : "Não informado"}</strong><span className="ac-kind">Esta data não muda ao salvar o cadastro.</span></p>
        )}
        {mode === "create" ? (
          <>
          <label className="ac-field">
            Saldo inicial
            <input data-field="openingBalanceMinor" value={opening} aria-invalid={Boolean(errors.openingBalanceMinor)} disabled={unknownResult} placeholder="Pode completar depois" onChange={(event) => setOpening(event.target.value)} />
            {errors.openingBalanceMinor ? <span className="error" role="alert">{errors.openingBalanceMinor}</span> : null}
          </label>
          <span className="ac-kind">Opcional e separado da identificação. Em branco, a posição continua não apurada. Zero informado permanece zero.</span>
          </>
        ) : null}
        <details className="ac-more" open={more} onToggle={(event) => setMore((event.target as HTMLDetailsElement).open)}>
          <summary>Mais informações</summary>
          <div className="ac-more-body">
            {bank ? (
              <>
              <label className="ac-field">
                Apelido
                <input data-field="name" value={nickname} aria-invalid={Boolean(errors.name)} disabled={unknownResult} maxLength={100} onChange={(event) => setNickname(event.target.value)} />
                {errors.name ? <span className="error" role="alert">{errors.name}</span> : null}
              </label>
              <span className="ac-kind">Se ficar em branco, a conta aparece com a instituição e o número mascarado.</span>
              </>
            ) : type === "OTHER" ? (
              <label className="ac-field">
                Identificação
                <input value={institution} disabled={unknownResult} maxLength={120} onChange={(event) => setInstitution(event.target.value)} />
                <span className="ac-kind">Opcional. Não é um número bancário.</span>
              </label>
            ) : null}
            <label className="ac-field">
              País
              <input data-field="countryCode" value={country} aria-invalid={Boolean(errors.countryCode)} disabled={unknownResult} maxLength={2} onChange={(event) => setCountry(event.target.value.toUpperCase())} />
              {errors.countryCode ? <span className="error" role="alert">{errors.countryCode}</span> : null}
            </label>
            {bank ? (
              <>
                <label className="ac-field">
                  Código do banco
                  <input data-field="bankCode" value={bankCode} aria-invalid={Boolean(errors.bankCode)} disabled={unknownResult} inputMode="numeric" onChange={(event) => setBankCode(event.target.value)} />
                  {errors.bankCode ? <span className="error" role="alert">{errors.bankCode}</span> : null}
                </label>
                <div className="ac-pair">
                  <label className="ac-field">
                    Agência
                    <input data-field="branchNumber" value={branch} aria-invalid={Boolean(errors.branchNumber)} disabled={unknownResult} inputMode="numeric" onChange={(event) => setBranch(event.target.value)} />
                    {errors.branchNumber ? <span className="error" role="alert">{errors.branchNumber}</span> : null}
                  </label>
                  <label className="ac-field">
                    Dígito da agência
                    <input data-field="branchDigit" value={branchDigit} aria-invalid={Boolean(errors.branchDigit)} disabled={unknownResult} onChange={(event) => setBranchDigit(event.target.value)} />
                    {errors.branchDigit ? <span className="error" role="alert">{errors.branchDigit}</span> : null}
                  </label>
                </div>
                <label className="ac-field">
                  Dígito da conta
                  <input data-field="accountDigit" value={accountDigit} aria-invalid={Boolean(errors.accountDigit)} disabled={unknownResult} onChange={(event) => setAccountDigit(event.target.value)} />
                  {errors.accountDigit ? <span className="error" role="alert">{errors.accountDigit}</span> : null}
                </label>
                <label className="ac-field">
                  E-mail institucional
                  <input data-field="institutionEmail" type="email" value={email} aria-invalid={Boolean(errors.institutionEmail)} disabled={unknownResult} onChange={(event) => setEmail(event.target.value)} />
                  {errors.institutionEmail ? <span className="error" role="alert">{errors.institutionEmail}</span> : null}
                </label>
                <label className="ac-field">
                  Telefone de atendimento
                  <input data-field="institutionPhone" value={phone} aria-invalid={Boolean(errors.institutionPhone)} disabled={unknownResult} onChange={(event) => setPhone(event.target.value)} />
                  {errors.institutionPhone ? <span className="error" role="alert">{errors.institutionPhone}</span> : null}
                </label>
              </>
            ) : null}
            <div id="contatos" tabIndex={-1}>
              <h2>Contatos</h2>
              <p className="ac-meta">Opcionais. Gerente da conta e gerente da agência são funções diferentes. Nada disso envia mensagem.</p>
              {contacts.length === 0 ? <p>Nenhum contato informado</p> : null}
              {contacts.map((contact, index) => (
                <fieldset key={index} className="ac-contact-edit">
                  <legend>Contato {index + 1}</legend>
                  <label className="ac-field">Nome<input value={contact.personName} disabled={unknownResult} maxLength={80} onChange={(event) => patchContact(index, { personName: event.target.value })} /></label>
                  <label className="ac-field">
                    Função
                    <select value={contact.role} disabled={unknownResult} onChange={(event) => patchContact(index, { role: event.target.value })}>
                      <option value="ACCOUNT_MANAGER">Gerente da conta</option>
                      <option value="BRANCH_MANAGER">Gerente da agência</option>
                      <option value="SERVICE">Atendimento</option>
                      <option value="OTHER">Outra função</option>
                    </select>
                  </label>
                  <label className="ac-field">
                    E-mail profissional
                    <input data-field={`contacts.${index}.email`} type="email" value={contact.email} aria-invalid={Boolean(errors[`contacts.${index}.email`])} disabled={unknownResult} onChange={(event) => patchContact(index, { email: event.target.value })} />
                    {errors[`contacts.${index}.email`] ? <span className="error" role="alert">{errors[`contacts.${index}.email`]}</span> : null}
                  </label>
                  <label className="ac-field">Telefone ou ramal<input value={contact.phone} disabled={unknownResult} onChange={(event) => patchContact(index, { phone: event.target.value })} /></label>
                  <label className="ac-field">
                    Associação
                    <select value={contact.association} disabled={unknownResult} onChange={(event) => patchContact(index, { association: event.target.value })}>
                      <option value="ACCOUNT">Conta</option>
                      <option value="BRANCH">Agência</option>
                      <option value="INSTITUTION">Instituição</option>
                    </select>
                  </label>
                  <label className="ac-check">
                    <input
                      type="checkbox"
                      checked={contact.primaryContact}
                      disabled={unknownResult}
                      onChange={(event) => patchContact(index, { primaryContact: event.target.checked })}
                    />
                    Contato principal
                  </label>
                  <button type="button" className="secondary" onClick={() => setContacts((current) => current.filter((_, itemIndex) => itemIndex !== index))}>Remover contato</button>
                </fieldset>
              ))}
              {errors.contacts ? <p className="error" role="alert">{errors.contacts}</p> : null}
              <button type="button" className="secondary" disabled={unknownResult} onClick={() => { setContacts((current) => [...current, emptyContact()]); setMore(true); }}>Adicionar contato</button>
            </div>
          </div>
        </details>
        {formError ? <p className="error" role="alert">{formError}</p> : null}
        {conflict ? (
          <div className="error" role="alert">
            <p>{conflict}</p>
            <button type="button" className="secondary" onClick={reviewCurrent}>Conferir dados atuais</button>
            {snapshot ? <p>{snapshot} O preenchimento desta tela foi mantido.</p> : null}
            {snapshot ? (
              <button type="button" disabled={busy} onClick={() => send(null, version)}>Salvar o que está neste formulário</button>
            ) : null}
          </div>
        ) : null}
        <div className="ac-actions">
          <button type="submit" disabled={busy || unknownResult}>{busy ? "Salvando…" : "Salvar"}</button>
          <button type="button" className="secondary" onClick={onCancel}>Cancelar</button>
          {unknownResult ? (
            <button type="button" disabled={busy || !pending.current} onClick={() => send(pending.current)}>Tentar novamente</button>
          ) : null}
        </div>
      </form>
      <aside className="ac-side" aria-label="Prévia da conta">
        <section className="ac-card">
          <h2>Prévia</h2>
          <p>{previewName}</p>
          <p>{number.trim() ? maskAccountNumber(number) : "Número ainda não informado"}</p>
          <p>{modality ? modalityLabel(modality) : type === "CASH" ? "Caixa físico" : type === "OTHER" ? "Outra conta" : "Modalidade ainda não escolhida"}</p>
          <p>BRL · Real</p>
          <p className="ac-meta">A prévia só mostra o que está nesta tela. Nada é gravado antes de salvar.</p>
        </section>
      </aside>
    </div>
  );
}

export type { AccountContact };
