import { useCallback, useEffect, useMemo, useState } from "react";
import {
  companyQuery,
  request,
  type ApiError,
  type ImportBatch,
  type PartyCandidate,
  type PartyDetail,
  type PartyPage,
} from "./api";
import { canWriteCatalogs, getSession } from "./session";
import { PageHeader } from "./ui/PageHeader";

const FILTER_KEY = "af.partyFilters";

type PartyFilters = {
  q: string;
  relation: string;
  status: string;
  documentPending: string;
  origin: string;
  page: number;
  size: number;
};

const defaultFilters = (): PartyFilters => ({
  q: "",
  relation: "ALL",
  status: "ALL",
  documentPending: "ALL",
  origin: "ALL",
  page: 0,
  size: 20,
});

function loadFilters(): PartyFilters {
  try {
    const raw = sessionStorage.getItem(FILTER_KEY);
    return raw ? { ...defaultFilters(), ...JSON.parse(raw) } : defaultFilters();
  } catch {
    return defaultFilters();
  }
}

function saveFilters(filters: PartyFilters) {
  sessionStorage.setItem(FILTER_KEY, JSON.stringify(filters));
}

function roleLabel(role: string): string {
  return { CUSTOMER: "Cliente", SUPPLIER: "Fornecedor", BOTH: "Cliente e fornecedor" }[role] ?? role;
}

function originLabel(origin: string): string {
  return { MANUAL: "Manual", FILE: "Arquivo", SYSTEM: "Sistema" }[origin] ?? origin;
}

function personLabel(kind: string): string {
  return { LEGAL: "Pessoa jurídica", NATURAL: "Pessoa física", UNSPECIFIED: "Não informada" }[kind] ?? kind;
}

function unitLabel(kind: string): string {
  return {
    STORE: "Loja",
    DEPOT: "Depósito",
    WAREHOUSE: "Armazém",
    LOCAL_PRODUCER: "Produtor local",
    OFFICE: "Escritório",
    OTHER: "Outro",
  }[kind] ?? kind;
}

function countLabel(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function classificationLabel(code: string): string {
  return (
    {
      NEW: "Novo",
      DUPLICATE: "Possível duplicado",
      CONFLICT: "Conflito",
      INVALID: "Inválido",
    }[code] ?? code
  );
}

function resultLabel(code: string | null | undefined): string {
  if (!code) {
    return "—";
  }
  return (
    {
      CREATED: "Criado",
      UPDATED: "Atualizado",
      SKIPPED: "Não gravada",
      REJECTED: "Recusada",
    }[code] ?? code
  );
}

function createLabel(relation: string): string {
  if (relation === "SUPPLIER") {
    return "Cadastrar fornecedor";
  }
  if (relation === "CUSTOMER") {
    return "Cadastrar cliente";
  }
  return "Cadastrar";
}

function defaultRole(relation: string): { customer: boolean; supplier: boolean } {
  if (relation === "SUPPLIER") {
    return { customer: false, supplier: true };
  }
  return { customer: true, supplier: false };
}

function fieldError(error: ApiError | null, key: string): string {
  return error?.fields?.[key] ?? "";
}

export function CounterpartiesRouter({
  path,
  onDirty,
  onNavigate,
}: {
  path: string;
  onDirty: (value: boolean) => void;
  onNavigate: (to: string) => void;
}) {
  if (path.endsWith("/import")) {
    return <PartyImportPage onNavigate={onNavigate} />;
  }
  if (path.endsWith("/new")) {
    return <PartyFormPage mode="create" onDirty={onDirty} onNavigate={onNavigate} />;
  }
  const match = path.match(/\/catalogs\/counterparties\/([^/]+)$/);
  if (match && match[1] !== "counterparties") {
    return <PartyFormPage mode="edit" id={match[1]} onDirty={onDirty} onNavigate={onNavigate} />;
  }
  return <PartyListPage onNavigate={onNavigate} />;
}

function PartyListPage({ onNavigate }: { onNavigate: (to: string) => void }) {
  const [filters, setFilters] = useState<PartyFilters>(loadFilters);
  const [data, setData] = useState<PartyPage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const companyId = getSession()?.companyId;

  const apply = (patch: Partial<PartyFilters>) => {
    setFilters((current) => {
      const next = { ...current, ...patch, page: patch.page ?? 0 };
      saveFilters(next);
      return next;
    });
  };

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (filters.q) params.set("q", filters.q);
    params.set("relation", filters.relation);
    params.set("status", filters.status);
    if (filters.documentPending !== "ALL") params.set("documentPending", filters.documentPending === "YES" ? "true" : "false");
    params.set("origin", filters.origin);
    params.set("page", String(filters.page));
    params.set("size", String(filters.size));
    void request<PartyPage>(`/api/v1/catalogs/parties?${companyQuery(params.toString())}`)
      .then(setData)
      .catch((caught: ApiError) => setError(caught.message))
      .finally(() => setLoading(false));
  }, [companyId, filters]);

  useEffect(() => {
    load();
  }, [load]);

  const emptyCatalog = data && data.totalItems === 0 && !filters.q && filters.relation === "ALL" && filters.status === "ALL" && filters.documentPending === "ALL" && filters.origin === "ALL";
  const emptyResults = data && data.totalItems === 0 && !emptyCatalog;

  return (
    <section>
      <PageHeader
        title="Clientes e fornecedores"
        hint="Busca consulta a lista. O cadastro abre em página própria, mesmo sem nome na busca."
        action={
          canWriteCatalogs() ? (
            <div className="page-actions">
              <button type="button" className="secondary" onClick={() => onNavigate("/catalogs/counterparties/import")}>
                Importar arquivo
              </button>
              <button type="button" onClick={() => onNavigate("/catalogs/counterparties/new")}>
                {createLabel(filters.relation)}
              </button>
            </div>
          ) : null
        }
      />
      <form
        className="filters"
        role="search"
        onSubmit={(event) => {
          event.preventDefault();
          apply({ q: filters.q, page: 0 });
        }}
      >
        <label>
          Buscar
          <input
            value={filters.q}
            onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))}
            placeholder="Nome, nome fantasia, documento ou ID externo"
          />
        </label>
        <label>
          Relação
          <select value={filters.relation} onChange={(event) => apply({ relation: event.target.value })}>
            <option value="ALL">Todos</option>
            <option value="CUSTOMER">Clientes</option>
            <option value="SUPPLIER">Fornecedores</option>
            <option value="BOTH">Cliente e fornecedor</option>
          </select>
        </label>
        <label>
          Situação
          <select value={filters.status} onChange={(event) => apply({ status: event.target.value })}>
            <option value="ALL">Todas</option>
            <option value="ACTIVE">Ativos</option>
            <option value="INACTIVE">Inativos</option>
          </select>
        </label>
        <label>
          Identificação
          <select value={filters.documentPending} onChange={(event) => apply({ documentPending: event.target.value })}>
            <option value="ALL">Todas</option>
            <option value="YES">Documento pendente</option>
            <option value="NO">Com documento</option>
          </select>
        </label>
        <label>
          Origem
          <select value={filters.origin} onChange={(event) => apply({ origin: event.target.value })}>
            <option value="ALL">Todas</option>
            <option value="MANUAL">Manual</option>
            <option value="FILE">Arquivo</option>
            <option value="SYSTEM">Sistema</option>
          </select>
        </label>
        <button type="submit">Buscar</button>
        <button type="button" className="secondary filter-clear" onClick={() => apply(defaultFilters())}>
          Limpar
        </button>
      </form>
      {error ? (
        <p className="error" role="alert">
          {error}{" "}
          <button type="button" onClick={load}>
            Tentar novamente
          </button>
        </p>
      ) : null}
      {loading ? <p>Carregando cadastros…</p> : null}
      {emptyCatalog ? (
        <p>
          Nenhum cliente ou fornecedor cadastrado nesta empresa.
          {canWriteCatalogs() ? (
            <>
              {" "}
              <button type="button" className="link" onClick={() => onNavigate("/catalogs/counterparties/new")}>
                {createLabel(filters.relation)}
              </button>
            </>
          ) : null}
        </p>
      ) : null}
      {emptyResults ? (
        <p>
          Nenhum resultado para esta busca. Os inativos continuam pesquisáveis.
          <button type="button" className="link" onClick={() => apply(defaultFilters())}>
            Limpar filtros
          </button>
        </p>
      ) : null}
      {data && data.items.length > 0 ? (
        <>
          <table className="desktop-table">
            <thead>
              <tr>
                <th>Nome e documento</th>
                <th>Relação</th>
                <th>Localidade</th>
                <th>Situação</th>
                <th>Origem</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <a
                      href={`/catalogs/counterparties/${item.id}`}
                      onClick={(event) => {
                        event.preventDefault();
                        onNavigate(`/catalogs/counterparties/${item.id}`);
                      }}
                    >
                      {item.name}
                    </a>
                    <p className="muted">
                      {item.documentDisplay ?? "Documento pendente"}
                      {item.tradeName ? ` · ${item.tradeName}` : ""}
                    </p>
                  </td>
                  <td>{roleLabel(item.role)}</td>
                  <td>{item.locality || "—"}</td>
                  <td>{item.active ? "Ativo" : "Inativo"}</td>
                  <td>{originLabel(item.originKind)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="cards catalog-cards">
            {data.items.map((item) => (
              <li key={`card-${item.id}`}>
                <a
                  href={`/catalogs/counterparties/${item.id}`}
                  onClick={(event) => {
                    event.preventDefault();
                    onNavigate(`/catalogs/counterparties/${item.id}`);
                  }}
                >
                  <strong>{item.name}</strong>
                  <p>{roleLabel(item.role)} · {item.active ? "Ativo" : "Inativo"}</p>
                  <p className="muted">{item.documentDisplay ?? "Documento pendente"} · {item.locality || "sem localidade"}</p>
                </a>
              </li>
            ))}
          </ul>
          <p className="pager">
            {data.page * data.size + 1}–{Math.min((data.page + 1) * data.size, data.totalItems)} de {data.totalItems}
            <button type="button" className="secondary" disabled={data.page === 0} onClick={() => apply({ page: data.page - 1 })}>
              Anterior
            </button>
            <button type="button" className="secondary" disabled={(data.page + 1) * data.size >= data.totalItems} onClick={() => apply({ page: data.page + 1 })}>
              Próximo
            </button>
          </p>
        </>
      ) : null}
    </section>
  );
}

type Draft = {
  name: string;
  tradeName: string;
  personKind: string;
  customer: boolean;
  supplier: boolean;
  active: boolean;
  documentCountry: string;
  documentType: string;
  documentNumber: string;
  notes: string;
  units: { id?: string; name: string; unitKind: string; primary: boolean; documentCountry: string; documentType: string; documentNumber: string }[];
  addresses: {
    id?: string;
    country: string;
    postalCode: string;
    street: string;
    number: string;
    noNumber: boolean;
    complement: string;
    district: string;
    municipality: string;
    region: string;
    usage: string;
  }[];
  contacts: { id?: string; name: string; roleTitle: string; email: string; phone: string; primary: boolean }[];
  supplies: { id?: string; description: string; supplyCategory: string; notes: string }[];
};

function emptyDraft(): Draft {
  const role = defaultRole(loadFilters().relation);
  return {
    name: "",
    tradeName: "",
    personKind: "UNSPECIFIED",
    customer: role.customer,
    supplier: role.supplier,
    active: true,
    documentCountry: "BR",
    documentType: "",
    documentNumber: "",
    notes: "",
    units: [],
    addresses: [],
    contacts: [],
    supplies: [],
  };
}

function PartyFormPage({
  mode,
  id,
  onDirty,
  onNavigate,
}: {
  mode: "create" | "edit";
  id?: string;
  onDirty: (value: boolean) => void;
  onNavigate: (to: string) => void;
}) {
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [detail, setDetail] = useState<PartyDetail | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const [candidates, setCandidates] = useState<PartyCandidate[]>([]);
  const writable = canWriteCatalogs();
  const filters = useMemo(loadFilters, []);

  useEffect(() => {
    if (mode !== "edit" || !id) {
      return;
    }
    void request<PartyDetail>(`/api/v1/catalogs/parties/${id}?${companyQuery()}`)
      .then((party) => {
        setDetail(party);
        setDraft({
          name: party.name,
          tradeName: party.tradeName ?? "",
          personKind: party.personKind,
          customer: party.role === "CUSTOMER" || party.role === "BOTH",
          supplier: party.role === "SUPPLIER" || party.role === "BOTH",
          active: party.active,
          documentCountry: party.documentCountry ?? "BR",
          documentType: party.documentType ?? "",
          documentNumber: party.documentNumber ?? "",
          notes: party.notes ?? "",
          units: party.units.filter((unit) => unit.active).map((unit) => ({
            id: unit.id,
            name: unit.name,
            unitKind: unit.unitKind,
            primary: unit.primary,
            documentCountry: unit.documentCountry ?? "",
            documentType: unit.documentType ?? "",
            documentNumber: unit.documentNumber ?? "",
          })),
          addresses: party.addresses.filter((address) => address.active).map((address) => ({
            id: address.id,
            country: address.country,
            postalCode: address.postalCode ?? "",
            street: address.street ?? "",
            number: address.number ?? "",
            noNumber: address.noNumber,
            complement: address.complement ?? "",
            district: address.district ?? "",
            municipality: address.municipality ?? "",
            region: address.region ?? "",
            usage: address.usage,
          })),
          contacts: party.contacts.filter((contact) => contact.active).map((contact) => ({
            id: contact.id,
            name: contact.name,
            roleTitle: contact.roleTitle ?? "",
            email: contact.email ?? "",
            phone: contact.phone ?? "",
            primary: contact.primary,
          })),
          supplies: party.supplies.filter((supply) => supply.active).map((supply) => ({
            id: supply.id,
            description: supply.description,
            supplyCategory: supply.supplyCategory ?? "",
            notes: supply.notes ?? "",
          })),
        });
      })
      .catch((caught: ApiError) => setError(caught));
  }, [id, mode]);

  const change = (patch: Partial<Draft>) => {
    setDraft((current) => ({ ...current, ...patch }));
    onDirty(true);
  };

  const lookup = () => {
    const params = new URLSearchParams();
    if (draft.name) params.set("name", draft.name);
    if (draft.documentType && draft.documentNumber) {
      params.set("documentCountry", draft.documentCountry || "BR");
      params.set("documentType", draft.documentType);
      params.set("documentNumber", draft.documentNumber);
    }
    if (id) params.set("exceptId", id);
    void request<PartyCandidate[]>(`/api/v1/catalogs/party-candidates?${companyQuery(params.toString())}`)
      .then(setCandidates)
      .catch(() => setCandidates([]));
  };

  const submit = () => {
    setBusy(true);
    setError(null);
    const body = {
      name: draft.name,
      tradeName: draft.tradeName || null,
      personKind: draft.personKind,
      customer: draft.customer,
      supplier: draft.supplier,
      active: draft.active,
      documentCountry: draft.documentNumber ? draft.documentCountry || "BR" : "",
      documentType: draft.documentNumber ? draft.documentType : "",
      documentNumber: draft.documentNumber,
      notes: draft.notes || null,
      version: detail?.version,
      units: draft.units,
      addresses: draft.addresses,
      contacts: draft.contacts,
      supplies: draft.supplies,
    };
    const path = mode === "create" ? `/api/v1/catalogs/parties?${companyQuery()}` : `/api/v1/catalogs/parties/${id}?${companyQuery()}`;
    void request<PartyDetail>(path, {
      method: mode === "create" ? "POST" : "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then((saved) => {
        onDirty(false);
        onNavigate(`/catalogs/counterparties/${saved.id}`);
      })
      .catch((caught: ApiError) => setError(caught))
      .finally(() => setBusy(false));
  };

  const submitLabel = mode === "create"
    ? draft.supplier && !draft.customer
      ? "Cadastrar fornecedor"
      : draft.customer && !draft.supplier
        ? "Cadastrar cliente"
        : "Cadastrar cliente e fornecedor"
    : "Salvar alterações";

  return (
    <section className="party-page">
      <p>
        <button type="button" className="link" onClick={() => onNavigate("/catalogs/counterparties")}>
          Voltar à lista
        </button>
      </p>
      <PageHeader
        title={mode === "create" ? createLabel(filters.relation) : draft.name || "Cadastro"}
        hint="Nome e relação bastam para gravar. Documento e endereço podem ficar incompletos."
      />
      {error ? (
        <div className="error-box" role="alert">
          <p>{error.message}</p>
          {error.fields ? (
            <ul>
              {Object.entries(error.fields).map(([key, message]) => (
                <li key={key}>{message}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
      {detail ? (
        <aside className="party-completeness">
          <p>{detail.completeness.paymentNote}</p>
          <p className="muted">
            Código {detail.code} · origem {originLabel(detail.originKind)}
            {detail.referencedByTitles ? " · referenciado por títulos" : ""}
          </p>
        </aside>
      ) : null}
      {candidates.length > 0 ? (
        <aside className="party-candidates" aria-live="polite">
          <p>Cadastros semelhantes nesta empresa. A homonímia não impede gravar; documento igual impede duplicar.</p>
          <ul>
            {candidates.map((item) => (
              <li key={item.id}>
                <button type="button" className="link" onClick={() => onNavigate(`/catalogs/counterparties/${item.id}`)}>
                  Abrir {item.name}
                </button>
                {" "}
                {roleLabel(item.role)} · {item.documentDisplay ?? "sem documento"} · {item.matchKind === "DOCUMENT" ? "mesmo documento" : "nome semelhante"}
              </li>
            ))}
          </ul>
        </aside>
      ) : null}
      <form
        className="form party-form"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        onChange={() => onDirty(true)}
      >
        <fieldset>
          <legend>Identificação</legend>
          <div className="party-id-grid">
            <label>
              Tipo de pessoa
              <select value={draft.personKind} onChange={(event) => change({ personKind: event.target.value })} disabled={!writable}>
                <option value="UNSPECIFIED">Não informada</option>
                <option value="LEGAL">Pessoa jurídica</option>
                <option value="NATURAL">Pessoa física</option>
              </select>
            </label>
            <fieldset className="choice-set">
              <legend>Relação</legend>
              <label className="check">
                <input type="checkbox" checked={draft.customer} onChange={(event) => change({ customer: event.target.checked })} disabled={!writable} />
                Cliente
              </label>
              <label className="check">
                <input type="checkbox" checked={draft.supplier} onChange={(event) => change({ supplier: event.target.checked })} disabled={!writable} />
                Fornecedor
              </label>
              {fieldError(error, "role") ? <span className="field-error">{fieldError(error, "role")}</span> : null}
            </fieldset>
            <label className="span-2">
              Razão social ou nome
              <input value={draft.name} onChange={(event) => change({ name: event.target.value })} onBlur={lookup} disabled={!writable} />
              {fieldError(error, "name") ? <span className="field-error">{fieldError(error, "name")}</span> : null}
            </label>
            <label className="span-2">
              Nome fantasia
              <input value={draft.tradeName} onChange={(event) => change({ tradeName: event.target.value })} disabled={!writable} />
            </label>
            <div className="span-2">
              <p className="hint">Documento opcional. CPF com 11 dígitos; CNPJ com 14 posições e dígitos verificadores. Pode completar depois.</p>
              <div className="party-doc-grid">
                <label>
                  País do documento
                  <input value={draft.documentCountry} onChange={(event) => change({ documentCountry: event.target.value.toUpperCase() })} disabled={!writable} maxLength={2} />
                </label>
                <label>
                  Tipo do documento
                  <select value={draft.documentType} onChange={(event) => change({ documentType: event.target.value })} disabled={!writable}>
                    <option value="">Não informado</option>
                    <option value="CNPJ">CNPJ</option>
                    <option value="CPF">CPF</option>
                    <option value="OTHER">Outro</option>
                  </select>
                </label>
                <label>
                  Número do documento
                  <input
                    value={writable ? draft.documentNumber : (detail?.documentDisplay ?? "")}
                    onChange={(event) => change({ documentNumber: event.target.value })}
                    onBlur={lookup}
                    disabled={!writable}
                    placeholder="Opcional"
                  />
                  {fieldError(error, "documentNumber") ? <span className="field-error">{fieldError(error, "documentNumber")}</span> : null}
                </label>
              </div>
            </div>
            {mode === "edit" ? (
              <label className="check span-2">
                <input type="checkbox" checked={draft.active} onChange={(event) => change({ active: event.target.checked })} disabled={!writable} />
                Cadastro ativo
              </label>
            ) : null}
          </div>
        </fieldset>
        <fieldset>
          <legend>Unidades</legend>
          <p className="hint">Informe documento da unidade só quando ela tiver identificação própria. A matriz não é copiada automaticamente.</p>
          {draft.units.map((unit, index) => (
            <div key={unit.id ?? `u-${index}`} className="party-repeat">
              <label>
                Nome da unidade
                <input value={unit.name} onChange={(event) => {
                  const units = draft.units.slice();
                  units[index] = { ...unit, name: event.target.value };
                  change({ units });
                }} disabled={!writable} />
              </label>
              <label>
                Tipo
                <select value={unit.unitKind} onChange={(event) => {
                  const units = draft.units.slice();
                  units[index] = { ...unit, unitKind: event.target.value };
                  change({ units });
                }} disabled={!writable}>
                  <option value="STORE">Loja</option>
                  <option value="DEPOT">Depósito</option>
                  <option value="WAREHOUSE">Armazém</option>
                  <option value="LOCAL_PRODUCER">Produtor local</option>
                  <option value="OFFICE">Escritório</option>
                  <option value="OTHER">Outro</option>
                </select>
              </label>
              <label>
                Documento próprio
                <input value={unit.documentNumber} onChange={(event) => {
                  const units = draft.units.slice();
                  units[index] = { ...unit, documentNumber: event.target.value, documentType: unit.documentType || "CNPJ", documentCountry: unit.documentCountry || "BR" };
                  change({ units });
                }} disabled={!writable} />
              </label>
              <label className="check">
                <input type="checkbox" checked={unit.primary} onChange={(event) => {
                  const units = draft.units.map((item, at) => ({ ...item, primary: at === index && event.target.checked }));
                  change({ units });
                }} disabled={!writable} />
                Unidade principal
              </label>
            </div>
          ))}
          {writable ? (
            <button type="button" className="secondary" onClick={() => change({ units: [...draft.units, { name: "", unitKind: "STORE", primary: draft.units.length === 0, documentCountry: "", documentType: "", documentNumber: "" }] })}>
              Adicionar unidade
            </button>
          ) : null}
        </fieldset>
        <fieldset>
          <legend>Endereço</legend>
          <p className="hint">O endereço pode ficar incompleto e ser completado depois. CEP no formato 00000-000.</p>
          {draft.addresses.map((address, index) => (
            <div key={address.id ?? `a-${index}`} className="party-address-grid">
              <label>
                País
                <input value={address.country} onChange={(event) => {
                  const addresses = draft.addresses.slice();
                  addresses[index] = { ...address, country: event.target.value.toUpperCase() };
                  change({ addresses });
                }} disabled={!writable} maxLength={2} />
              </label>
              <label>
                CEP ou código postal
                <input value={address.postalCode} onChange={(event) => {
                  const addresses = draft.addresses.slice();
                  addresses[index] = { ...address, postalCode: event.target.value };
                  change({ addresses });
                }} disabled={!writable} />
              </label>
              <label className="span-2">
                Logradouro
                <input value={address.street} onChange={(event) => {
                  const addresses = draft.addresses.slice();
                  addresses[index] = { ...address, street: event.target.value };
                  change({ addresses });
                }} disabled={!writable} />
              </label>
              <label>
                Número
                <input value={address.number} onChange={(event) => {
                  const addresses = draft.addresses.slice();
                  addresses[index] = { ...address, number: event.target.value };
                  change({ addresses });
                }} disabled={!writable || address.noNumber} />
              </label>
              <label className="check">
                <input type="checkbox" checked={address.noNumber} onChange={(event) => {
                  const addresses = draft.addresses.slice();
                  addresses[index] = { ...address, noNumber: event.target.checked, number: event.target.checked ? "" : address.number };
                  change({ addresses });
                }} disabled={!writable} />
                Sem número
              </label>
              <label>
                Complemento
                <input value={address.complement} onChange={(event) => {
                  const addresses = draft.addresses.slice();
                  addresses[index] = { ...address, complement: event.target.value };
                  change({ addresses });
                }} disabled={!writable} />
              </label>
              <label>
                Bairro
                <input value={address.district} onChange={(event) => {
                  const addresses = draft.addresses.slice();
                  addresses[index] = { ...address, district: event.target.value };
                  change({ addresses });
                }} disabled={!writable} />
              </label>
              <label>
                Município
                <input value={address.municipality} onChange={(event) => {
                  const addresses = draft.addresses.slice();
                  addresses[index] = { ...address, municipality: event.target.value };
                  change({ addresses });
                }} disabled={!writable} />
              </label>
              <label>
                UF ou região
                <input value={address.region} onChange={(event) => {
                  const addresses = draft.addresses.slice();
                  addresses[index] = { ...address, region: event.target.value };
                  change({ addresses });
                }} disabled={!writable} />
              </label>
            </div>
          ))}
          {writable ? (
            <button type="button" className="secondary" onClick={() => change({ addresses: [...draft.addresses, { country: "BR", postalCode: "", street: "", number: "", noNumber: false, complement: "", district: "", municipality: "", region: "", usage: "MAIN" }] })}>
              Adicionar endereço
            </button>
          ) : null}
        </fieldset>
        <fieldset>
          <legend>Contatos</legend>
          {draft.contacts.map((contact, index) => (
            <div key={contact.id ?? `c-${index}`} className="party-repeat">
              <label>
                Nome
                <input value={contact.name} onChange={(event) => {
                  const contacts = draft.contacts.slice();
                  contacts[index] = { ...contact, name: event.target.value };
                  change({ contacts });
                }} disabled={!writable} />
              </label>
              <label>
                Função
                <input value={contact.roleTitle} onChange={(event) => {
                  const contacts = draft.contacts.slice();
                  contacts[index] = { ...contact, roleTitle: event.target.value };
                  change({ contacts });
                }} disabled={!writable} />
              </label>
              <label>
                E-mail
                <input value={contact.email} onChange={(event) => {
                  const contacts = draft.contacts.slice();
                  contacts[index] = { ...contact, email: event.target.value };
                  change({ contacts });
                }} disabled={!writable} />
              </label>
              <label>
                Telefone
                <input value={contact.phone} onChange={(event) => {
                  const contacts = draft.contacts.slice();
                  contacts[index] = { ...contact, phone: event.target.value };
                  change({ contacts });
                }} disabled={!writable} />
              </label>
            </div>
          ))}
          {writable ? (
            <button type="button" className="secondary" onClick={() => change({ contacts: [...draft.contacts, { name: "", roleTitle: "", email: "", phone: "", primary: draft.contacts.length === 0 }] })}>
              Adicionar contato
            </button>
          ) : null}
        </fieldset>
        <fieldset>
          <legend>Fornecimentos</legend>
          <p className="hint">Descreva o que esta pessoa fornece. Não substitui categoria financeira nem estoque.</p>
          {draft.supplies.map((supply, index) => (
            <div key={supply.id ?? `s-${index}`} className="party-repeat">
              <label>
                Produto ou serviço
                <input value={supply.description} onChange={(event) => {
                  const supplies = draft.supplies.slice();
                  supplies[index] = { ...supply, description: event.target.value };
                  change({ supplies });
                }} disabled={!writable} />
              </label>
              <label>
                Categoria de fornecimento
                <input value={supply.supplyCategory} onChange={(event) => {
                  const supplies = draft.supplies.slice();
                  supplies[index] = { ...supply, supplyCategory: event.target.value };
                  change({ supplies });
                }} disabled={!writable} />
              </label>
            </div>
          ))}
          {writable ? (
            <button type="button" className="secondary" onClick={() => change({ supplies: [...draft.supplies, { description: "", supplyCategory: "", notes: "" }] })}>
              Adicionar fornecimento
            </button>
          ) : null}
        </fieldset>
        {detail ? (
          <fieldset>
            <legend>Origem e histórico</legend>
            <p>Origem {originLabel(detail.originKind)}. Identidades externas e histórico não são editáveis aqui.</p>
            {detail.externalIdentities.length > 0 ? (
              <ul>
                {detail.externalIdentities.map((item) => (
                  <li key={item.id}>{item.originSystem} · {item.externalId}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">Nenhum vínculo externo registrado.</p>
            )}
            <ul className="history">
              {detail.history.map((item) => (
                <li key={item.id}>{item.action} · {item.actorDisplayName ?? "operador"}</li>
              ))}
            </ul>
          </fieldset>
        ) : null}
        <div className="actions">
          <button type="button" className="secondary" disabled={busy} onClick={() => onNavigate("/catalogs/counterparties")}>
            Cancelar
          </button>
          {writable ? (
            <button type="submit" disabled={busy}>
              {submitLabel}
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}

function PartyImportPage({ onNavigate }: { onNavigate: (to: string) => void }) {
  const [filename, setFilename] = useState("");
  const [csvText, setCsvText] = useState("");
  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  const preview = () => {
    setBusy(true);
    setError("");
    void request<ImportBatch>(`/api/v1/catalogs/party-imports?${companyQuery()}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, csvText }),
    })
      .then((next) => {
        setBatch(next);
        const initial: Record<string, boolean> = {};
        next.lines.forEach((line) => {
          initial[line.id] = line.selected;
        });
        setSelected(initial);
      })
      .catch((caught: ApiError) => setError(caught.message))
      .finally(() => setBusy(false));
  };

  const eligibleSelected = batch
    ? batch.lines.filter((line) => Boolean(selected[line.id]) && line.classification !== "INVALID" && !line.result)
    : [];
  const confirmBlocked = !batch || Boolean(batch.report) || eligibleSelected.length === 0;
  const confirmReason = !batch
    ? ""
    : batch.report
      ? ""
      : eligibleSelected.length === 0
        ? "Selecione ao menos uma linha válida para confirmar. Linhas inválidas não entram."
        : "";

  const confirm = () => {
    if (!batch || confirmBlocked) {
      return;
    }
    setBusy(true);
    setError("");
    void request<ImportBatch>(`/api/v1/catalogs/party-imports/${batch.id}/confirm?${companyQuery()}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lines: batch.lines.map((line) => ({
          id: line.id,
          selected: Boolean(selected[line.id]),
          resolution: line.classification === "DUPLICATE" || line.classification === "CONFLICT" ? "ENRICH" : "CREATE",
        })),
      }),
    })
      .then(setBatch)
      .catch((caught: ApiError) => setError(caught.message))
      .finally(() => setBusy(false));
  };

  return (
    <section className="party-page">
      <p>
        <button type="button" className="link" onClick={() => onNavigate("/catalogs/counterparties")}>
          Voltar à lista
        </button>
      </p>
      <PageHeader
        title="Importar arquivo CSV"
        hint="O envio só gera prévia. Nada é gravado até a confirmação. Aceita o CSV do modelo; XLSX não é suportado."
      />
      <p>
        <a href="/api/v1/catalogs/party-imports/template">Baixar modelo sem dados pessoais reais</a>
      </p>
      <form
        className="form"
        onSubmit={(event) => {
          event.preventDefault();
          preview();
        }}
      >
        <label>
          Arquivo CSV
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) {
                return;
              }
              setFilename(file.name);
              void file.text().then(setCsvText);
              setBatch(null);
            }}
          />
        </label>
        <div className="actions">
          <button type="submit" disabled={busy || !csvText}>
            Validar arquivo
          </button>
        </div>
      </form>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {batch ? (
        <div className="party-import">
          <p>
            {countLabel(batch.totalLines, "linha", "linhas")} · {countLabel(batch.newCount, "novo", "novos")} · {countLabel(batch.duplicateCount, "possível duplicado", "possíveis duplicados")} · {countLabel(batch.conflictCount, "conflito", "conflitos")} · {countLabel(batch.invalidCount, "inválido", "inválidos")}.
            Gravação {batch.atomicity === "PER_LINE" ? "por linha" : batch.atomicity}.
          </p>
          <table className="desktop-table">
            <thead>
              <tr>
                <th>Incluir</th>
                <th>Linha</th>
                <th>Classificação</th>
                <th>Nome</th>
                <th>Documento</th>
                <th>Mensagem</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              {batch.lines.map((line) => (
                <tr key={line.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={Boolean(selected[line.id])}
                      disabled={line.classification === "INVALID" || Boolean(line.result)}
                      onChange={(event) => setSelected((current) => ({ ...current, [line.id]: event.target.checked }))}
                      aria-label={`Incluir linha ${line.lineNo}`}
                    />
                  </td>
                  <td>{line.lineNo}</td>
                  <td>{classificationLabel(line.classification)}</td>
                  <td>{line.name}</td>
                  <td>{line.documentDisplay ?? "—"}</td>
                  <td>{line.errorMessage ?? "—"}</td>
                  <td>{resultLabel(line.result)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="cards catalog-cards party-import-cards">
            {batch.lines.map((line) => (
              <li key={`card-${line.id}`}>
                <div className="import-line-head">
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={Boolean(selected[line.id])}
                      disabled={line.classification === "INVALID" || Boolean(line.result)}
                      onChange={(event) => setSelected((current) => ({ ...current, [line.id]: event.target.checked }))}
                      aria-label={`Incluir linha ${line.lineNo}`}
                    />
                    Incluir
                  </label>
                  <strong>Linha {line.lineNo}</strong>
                  <span>{classificationLabel(line.classification)}</span>
                </div>
                <p><strong>{line.name}</strong></p>
                <p className="muted">Documento {line.documentDisplay ?? "pendente"}</p>
                <p>{line.errorMessage ?? "Sem motivo adicional."}</p>
                <p>Resultado {resultLabel(line.result)}</p>
              </li>
            ))}
          </ul>
          {batch.report ? <p role="status">{batch.report.summary}</p> : null}
          {!batch.report ? (
            <>
              {confirmReason ? <p className="hint" role="status">{confirmReason}</p> : null}
              <button type="button" disabled={busy || confirmBlocked} onClick={confirm} title={confirmReason || undefined}>
                Confirmar linhas selecionadas
              </button>
            </>
          ) : (
            <button type="button" onClick={() => onNavigate("/catalogs/counterparties")}>
              Voltar à lista
            </button>
          )}
        </div>
      ) : null}
    </section>
  );
}

export { personLabel, unitLabel };
