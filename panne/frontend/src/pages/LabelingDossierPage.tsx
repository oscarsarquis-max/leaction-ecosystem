import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { isCancelledError } from "../api/errors";
import type { LabelingDossier } from "../api/types";
import { ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { LabelingMentor } from "../components/LabelingMentor";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  completenessLabel,
  dossierStatusLabel,
  evidenceResultLabel,
  findingRuleLabel,
  mandatoryCodeLabel,
  nutrientLabel,
  parseTriStateFormValue,
  physicalStateLabel,
  PHYSICAL_STATE_LABEL,
  REGULATORY_CATEGORY_LABEL,
  regulatoryCategoryLabel,
  salesChannelLabel,
  SALES_CHANNEL_LABEL,
  triStateFormValue,
  triStateLabel,
  UNCATALOGED_OPTION_LABEL,
} from "../language/labeling";
import { formatOperationalQuantity } from "../language/quantities";
import { useOrganization } from "../session/OrganizationContext";

const PROFILE_FIELDS = [
  ["jurisdiction", "Jurisdição"],
  ["evaluation_date", "Data da avaliação"],
  ["packed_food", "Alimento embalado"],
  ["packed_away_from_consumer", "Embalado na ausência do consumidor"],
  ["packed_at_point_of_sale", "Embalado no ponto de venda"],
  ["packed_on_request", "Embalado a pedido"],
  ["same_establishment", "Mesmo estabelecimento"],
  ["sales_channel", "Canal de venda"],
  ["food_service", "Serviço de alimentação"],
  ["physical_state", "Estado físico"],
  ["ready_to_eat", "Pronto para consumo"],
  ["regulatory_category_code", "Categoria regulatória"],
  ["net_content_g", "Conteúdo líquido (g)"],
  ["servings_per_package", "Porções por embalagem"],
  ["purpose", "Finalidade"],
  ["destination_market", "Mercado de destino"],
] as const;

const BOOLEAN_PROFILE_FIELDS = new Set([
  "packed_food",
  "packed_away_from_consumer",
  "packed_at_point_of_sale",
  "packed_on_request",
  "same_establishment",
  "food_service",
  "ready_to_eat",
]);

const ENUM_PROFILE_FIELDS: Record<string, Record<string, string>> = {
  sales_channel: SALES_CHANNEL_LABEL,
  physical_state: PHYSICAL_STATE_LABEL,
  regulatory_category_code: REGULATORY_CATEGORY_LABEL,
};

function tone(status: string) {
  if (status === "reviewed") return "info" as const;
  if (status === "invalidated") return "erro" as const;
  if (status === "evaluated") return "atencao" as const;
  return "neutro" as const;
}

function actionNeededPhrase(needed: boolean): string {
  return needed ? "Ação necessária" : "Sem ação pendente";
}

function profileDisplayValue(name: string, value: unknown): string {
  if (BOOLEAN_PROFILE_FIELDS.has(name)) return triStateLabel(value);
  if (name === "sales_channel") return salesChannelLabel(value == null ? null : String(value));
  if (name === "physical_state") return physicalStateLabel(value == null ? null : String(value));
  if (name === "regulatory_category_code") {
    return regulatoryCategoryLabel(value == null ? null : String(value));
  }
  if (value == null || value === "") return "Não informado";
  if (name === "net_content_g") {
    return formatOperationalQuantity(String(value), "g");
  }
  return String(value);
}

function profileEnumOptions(name: string, current: unknown): Array<{ value: string; label: string }> {
  const catalog = ENUM_PROFILE_FIELDS[name] ?? {};
  const options = Object.entries(catalog).map(([value, label]) => ({ value, label }));
  const raw = current == null || current === "" ? "" : String(current);
  if (raw && !catalog[raw]) {
    options.push({ value: raw, label: UNCATALOGED_OPTION_LABEL });
  }
  return options;
}

function mandatoryDisplayValue(code: string, value: string | null | undefined): string {
  if (value == null || value === "") return "pendente";
  if (code === "conteudo_liquido" || code === "net_content_g" || code === "mandatory_conteudo_liquido") {
    return formatOperationalQuantity(value, "g");
  }
  return value;
}

function formulationHeader(dossier: LabelingDossier): string | null {
  const parts: string[] = [];
  const name = dossier.formulation?.display_name?.trim();
  const code = dossier.formulation?.code?.trim();
  if (name) parts.push(name);
  if (code) parts.push(code);
  if (dossier.formulation_version?.version_number != null) {
    parts.push(`versão ${dossier.formulation_version.version_number}`);
  }
  return parts.length ? parts.join(" · ") : null;
}

type Loaded = { dossier: LabelingDossier; row: number };

export function LabelingDossierPage() {
  const { dossierId = "" } = useParams();
  const location = useLocation();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [left, setLeft] = useState("");
  const [right, setRight] = useState("");
  const [compare, setCompare] = useState<string | null>(null);
  const [mentorOpen, setMentorOpen] = useState(true);
  const [actionError, setActionError] = useState<unknown>(null);

  const { state, reload, loading } = useAsyncResource<Loaded>(
    async () => {
      const envelope = await api.getLabelingDossier(dossierId);
      return {
        dossier: envelope.data,
        row: envelope.row_version ?? envelope.data.row_version ?? 1,
      };
    },
    [api, dossierId, orgId],
    Boolean(dossierId && orgId),
  );

  // Troca de organização: limpa estado local ligado à entidade anterior.
  useEffect(() => {
    setLeft("");
    setRight("");
    setCompare(null);
    setActionError(null);
    setMentorOpen(true);
  }, [orgId, dossierId]);

  const pending = useMemo(() => {
    if (state.kind !== "ok") return [];
    return (state.data.dossier.current?.mandatory ?? [])
      .filter((item) => item.status === "pending")
      .map((item) => mandatoryCodeLabel(item.code, item.label));
  }, [state]);

  const commandsEnabled = state.kind === "ok" && !loading;

  async function command(path: string, body?: unknown) {
    if (!commandsEnabled || state.kind !== "ok") return;
    try {
      await api.catalogCommand(path, {
        body,
        idempotencyKey: crypto.randomUUID(),
        ifMatch: state.data.row,
      });
      setActionError(null);
      reload();
    } catch (error) {
      if (isCancelledError(error)) return;
      setActionError(error);
    }
  }

  if (actionError) {
    return (
      <ErrorState
        error={actionError}
        onRetry={() => {
          setActionError(null);
          reload();
        }}
      />
    );
  }
  if (state.kind === "carregando") {
    return <LoadingState>Carregando dossiê da organização ativa…</LoadingState>;
  }
  if (state.kind === "erro") {
    return (
      <div className="stage">
        <ErrorState error={state.error} onRetry={reload} />
        <p>
          <Link to="/conformidade/dossies">Voltar à lista de dossiês desta organização</Link>
        </p>
      </div>
    );
  }

  const { dossier, row } = state.data;
  const current = dossier.current;
  const print = location.pathname.endsWith("/imprimir");
  const formulationLine = formulationHeader(dossier);
  const nutritionLines = current?.nutrition?.lines ?? [];
  const findings = current?.findings ?? [];
  const warnings = current?.warnings ?? [];
  const mandatory = current?.mandatory ?? [];
  const nutrientsHigh = (current?.front_of_pack?.nutrients_high ?? []).map((code) => nutrientLabel(code));

  return (
    <div className={print ? "sheet labeling-print" : "stage"}>
      <div>
        <h1>Dossiê de rotulagem</h1>
        {formulationLine ? <p className="lede">{formulationLine}</p> : null}
        <p className="lede">
          <StatusBadge tone={tone(dossier.status)} label={dossierStatusLabel(dossier.status)} /> {dossier.disclaimer}
        </p>
        {print ? (
          <p className="watermark">{current?.candidate?.watermark}</p>
        ) : hasPermission("labeling.render") ? (
          <p>
            <Link to={`/conformidade/dossies/${dossier.id}/imprimir`}>Visualizar impressão A4</Link>
          </p>
        ) : null}
        {print ? (
          <button type="button" className="no-print" onClick={() => window.print()}>
            Imprimir conferência
          </button>
        ) : null}

        <TechnicalAuditDetails
          title="Identificadores do dossiê"
          purpose="IDs internos para suporte e auditoria. Não são necessários no dia a dia."
          rows={[
            { label: "Identificador do dossiê", value: dossier.id, copyable: true },
            { label: "Identificador da formulação", value: dossier.formulation_id, copyable: true },
            {
              label: "Identificador da versão da formulação",
              value: dossier.formulation_version_id,
              copyable: true,
            },
            ...(dossier.formulation?.id
              ? [{ label: "ID da receita enriquecida", value: dossier.formulation.id, copyable: true }]
              : []),
            ...(current?.version?.id
              ? [{ label: "Identificador da versão do dossiê", value: current.version.id, copyable: true }]
              : []),
            ...(current?.candidate?.payload_sha256
              ? [
                  {
                    label: "Hash do candidato",
                    value: current.candidate.payload_sha256,
                    copyable: true,
                  },
                ]
              : []),
          ]}
        />

        <section>
          <h2>Perfil de aplicabilidade</h2>
          <p>
            Completude: {completenessLabel(String(dossier.profile?.completeness ?? ""))}. Categoria exige
            confirmação humana.
          </p>
          {hasPermission("labeling.candidate.edit") && !print ? (
            <form
              className="grid-2"
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                const payload: Record<string, unknown> = {
                  category_confirmed: data.get("category_confirmed") === "on",
                };
                for (const [name] of PROFILE_FIELDS) {
                  const value = data.get(name);
                  if (BOOLEAN_PROFILE_FIELDS.has(name)) {
                    payload[name] = parseTriStateFormValue(value);
                  } else if (name === "servings_per_package") {
                    payload[name] = value ? Number(value) : null;
                  } else if (name === "net_content_g") {
                    const raw = String(value ?? "").trim();
                    payload[name] = raw || null;
                  } else {
                    const raw = String(value ?? "").trim();
                    payload[name] = raw || null;
                  }
                }
                void command(`/labeling/dossiers/${dossier.id}/profile`, payload);
              }}
            >
              {PROFILE_FIELDS.map(([name, label]) => {
                const current = dossier.profile?.[name];
                if (BOOLEAN_PROFILE_FIELDS.has(name)) {
                  return (
                    <label key={name}>
                      {label}
                      <select name={name} defaultValue={triStateFormValue(current)} aria-label={label}>
                        <option value="">Não informado</option>
                        <option value="true">Sim</option>
                        <option value="false">Não</option>
                      </select>
                    </label>
                  );
                }
                if (name in ENUM_PROFILE_FIELDS) {
                  const options = profileEnumOptions(name, current);
                  return (
                    <label key={name}>
                      {label}
                      <select
                        name={name}
                        defaultValue={current == null || current === "" ? "" : String(current)}
                        aria-label={label}
                      >
                        <option value="">Não informado</option>
                        {options.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  );
                }
                if (name === "net_content_g") {
                  return (
                    <label key={name}>
                      {label}
                      <span className="meta"> {profileDisplayValue(name, current)}</span>
                      <input
                        name={name}
                        inputMode="decimal"
                        defaultValue={
                          current == null || current === ""
                            ? ""
                            : formatOperationalQuantity(String(current), "g").replace(/\s*g$/i, "")
                        }
                        aria-label={label}
                      />
                    </label>
                  );
                }
                return (
                  <label key={name}>
                    {label}
                    <input
                      name={name}
                      defaultValue={current == null || current === "" ? "" : String(current)}
                      aria-label={label}
                    />
                  </label>
                );
              })}
              <label>
                <input
                  type="checkbox"
                  name="category_confirmed"
                  defaultChecked={Boolean(dossier.profile?.category_confirmed)}
                />
                Categoria confirmada por pessoa autorizada
              </label>
              <button type="submit" className="primary" disabled={!commandsEnabled}>
                Gravar perfil
              </button>
            </form>
          ) : (
            <dl className="profile-readonly">
              {PROFILE_FIELDS.map(([name, label]) => {
                const raw = dossier.profile?.[name];
                const display = profileDisplayValue(name, raw);
                const enumCatalog = ENUM_PROFILE_FIELDS[name];
                const uncataloged =
                  enumCatalog &&
                  raw != null &&
                  raw !== "" &&
                  !enumCatalog[String(raw)];
                return (
                  <div key={name}>
                    <dt>{label.replace(/ \(g\)$/, "")}</dt>
                    <dd>
                      {display}
                      {uncataloged ? (
                        <TechnicalAuditDetails
                          title="Código do valor"
                          purpose="Código técnico ainda sem rótulo operacional catalogado."
                          rows={[{ label: "Código", value: String(raw), copyable: true }]}
                        />
                      ) : null}
                    </dd>
                  </div>
                );
              })}
            </dl>
          )}
        </section>

        <section>
          <h2>Tabela nutricional candidata</h2>
          <p>Cálculo técnico permanece intacto. Abaixo está a projeção regulatória.</p>
          <table>
            <thead>
              <tr>
                <th>Nutriente</th>
                <th>Técnico/100 g</th>
                <th>Declarado/100 g</th>
                <th>Porção</th>
                <th>%VD</th>
              </tr>
            </thead>
            <tbody>
              {nutritionLines.map((line) => (
                <tr key={line.nutrient_code}>
                  <td>{nutrientLabel(line.nutrient_code)}</td>
                  <td>{line.technical_per_100g ?? "ausente"}</td>
                  <td>{line.presented ?? "sem evidência"}</td>
                  <td>{line.declared_per_serving ?? "—"}</td>
                  <td>{line.daily_value_percent ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>
            Porção:{" "}
            {current?.nutrition?.portion_g
              ? formatOperationalQuantity(current.nutrition.portion_g, "g")
              : "não confirmada"}{" "}
            · {current?.nutrition?.household_measure ?? "medida caseira pendente"}
          </p>
          <TechnicalAuditDetails
            title="Códigos de nutrientes"
            purpose="Códigos técnicos da tabela nutricional para auditoria."
            rows={nutritionLines.map((line) => ({
              label: nutrientLabel(line.nutrient_code),
              value: line.nutrient_code,
              copyable: true,
            }))}
          />
        </section>

        <section>
          <h2>Lupa candidata</h2>
          <p>{current?.front_of_pack?.disclaimer}</p>
          <div className="lupa" aria-label="Representação candidata da lupa">
            <strong>ALTO EM</strong>
            <p>{nutrientsHigh.join(", ") || "conclusão incompleta"}</p>
          </div>
          <p>
            Açúcares: {evidenceResultLabel(current?.front_of_pack?.added_sugars_result)}. Saturada:{" "}
            {evidenceResultLabel(current?.front_of_pack?.saturated_fat_result)}. Sódio:{" "}
            {evidenceResultLabel(current?.front_of_pack?.sodium_result)}.
          </p>
        </section>

        <section>
          <h2>Ingredientes e advertências</h2>
          <ol>
            {(current?.ingredients ?? []).map((item) => (
              <li key={item.sequence}>
                {item.display_name}
                {item.compound
                  ? ` (composto: ${item.components.map((part) => part.name).join(", ") || item.gap})`
                  : ""}
              </li>
            ))}
          </ol>
          <ul>
            {warnings.map((item) => (
              <li key={item.code}>
                {item.statement} · {evidenceResultLabel(item.result)}
              </li>
            ))}
          </ul>
          {warnings.length ? (
            <TechnicalAuditDetails
              title="Códigos das advertências"
              purpose="Códigos técnicos das advertências para auditoria."
              rows={warnings.map((item, index) => ({
                label: `Advertência ${index + 1}`,
                value: item.code,
                copyable: true,
              }))}
            />
          ) : null}
        </section>

        <section>
          <h2>Informações obrigatórias</h2>
          {hasPermission("labeling.candidate.edit") && !print ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                void command(`/labeling/dossiers/${dossier.id}/mandatory`, {
                  items: mandatory.map((item) => ({
                    code: item.code,
                    value: String(data.get(item.code) || "") || null,
                    claim: data.get(`${item.code}_claim`) === "on",
                  })),
                });
              }}
            >
              <ul>
                {mandatory.map((item) => (
                  <li key={item.code}>
                    <label>
                      {mandatoryCodeLabel(item.code, item.label)}
                      {item.code === "conteudo_liquido" || item.code === "net_content_g" ? (
                        <span className="meta"> {mandatoryDisplayValue(item.code, item.value)}</span>
                      ) : null}
                      <input
                        name={item.code}
                        defaultValue={
                          item.code === "conteudo_liquido" || item.code === "net_content_g"
                            ? formatOperationalQuantity(item.value, "g").replace(/\s*g$/i, "")
                            : (item.value ?? "")
                        }
                      />
                      <span>
                        <input type="checkbox" name={`${item.code}_claim`} /> alegação — exige revisão
                        específica
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
              <button type="submit" disabled={!commandsEnabled}>
                Gravar pendências
              </button>
            </form>
          ) : (
            <ul>
              {mandatory.map((item) => (
                <li key={item.code}>
                  {mandatoryCodeLabel(item.code, item.label)}: {mandatoryDisplayValue(item.code, item.value)}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h2>Achados</h2>
          <ul>
            {findings.map((item) => (
              <li key={item.rule_code}>
                <strong>{findingRuleLabel(item.rule_code)}</strong> · {evidenceResultLabel(item.result)}:{" "}
                {item.explanation} ({item.source_locator}) · {actionNeededPhrase(item.action_needed)}
                <TechnicalAuditDetails
                  title="Código da regra"
                  purpose="Identificador técnico da regra avaliada."
                  rows={[{ label: "Código da regra", value: item.rule_code, copyable: true }]}
                />
              </li>
            ))}
          </ul>
        </section>

        {print ? (
          <>
            <p className="meta">
              Versão {current?.version.version_number} · não é rótulo aprovado
            </p>
            <TechnicalAuditDetails
              title="Hash da versão impressa"
              purpose="Hash de conteúdo para conferência técnica. Não substitui a revisão humana."
              rows={[
                {
                  label: "Hash do conteúdo",
                  value: current?.version.content_hash ?? "—",
                  copyable: Boolean(current?.version.content_hash),
                },
                {
                  label: "Versão (número)",
                  value: String(current?.version.version_number ?? "—"),
                },
                {
                  label: "Status da versão",
                  value: current?.version.status ?? "—",
                },
              ]}
            />
          </>
        ) : (
          <>
            <div className="toolbar">
              {hasPermission("labeling.evaluate") ? (
                <button
                  type="button"
                  className="primary"
                  disabled={!commandsEnabled}
                  onClick={() => void command(`/labeling/dossiers/${dossier.id}/evaluate`)}
                >
                  Executar avaliação
                </button>
              ) : null}
              {hasPermission("labeling.review") ? (
                <button
                  type="button"
                  disabled={!commandsEnabled}
                  onClick={() =>
                    void command(`/labeling/dossiers/${dossier.id}/review`, { decision: "accepted" })
                  }
                >
                  Registrar revisão humana
                </button>
              ) : null}
              {hasPermission("labeling.invalidate") ? (
                <button
                  type="button"
                  disabled={!commandsEnabled}
                  onClick={() =>
                    void command(`/labeling/dossiers/${dossier.id}/invalidate`, {
                      reason: "invalidação auditável",
                    })
                  }
                >
                  Invalidar versão
                </button>
              ) : null}
            </div>
            <section>
              <h2>Comparar versões</h2>
              <label>
                Esquerda
                <select value={left} onChange={(event) => setLeft(event.target.value)}>
                  <option value="">selecione</option>
                  {(dossier.versions ?? []).map((item) => (
                    <option key={item.id} value={item.id}>
                      Versão {item.version_number} · {dossierStatusLabel(item.status)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Direita
                <select value={right} onChange={(event) => setRight(event.target.value)}>
                  <option value="">selecione</option>
                  {(dossier.versions ?? []).map((item) => (
                    <option key={item.id} value={item.id}>
                      Versão {item.version_number} · {dossierStatusLabel(item.status)}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={!left || !right}
                onClick={() => {
                  api
                    .compareLabelingVersions(dossier.id, left, right)
                    .then((body) => setCompare(JSON.stringify(body.data, null, 2)))
                    .catch((error) => {
                      if (isCancelledError(error)) return;
                      setActionError(error);
                    });
                }}
              >
                Comparar
              </button>
              {compare ? <pre>{compare}</pre> : null}
            </section>
            <TechnicalAuditDetails
              title="Controle de concorrência"
              purpose="Versão de linha usada nas gravações (If-Match)."
              rows={[{ label: "row_version", value: String(row), copyable: true }]}
            />
          </>
        )}
      </div>
      {print || !mentorOpen ? null : (
        <LabelingMentor step={pending.length ? 7 : current?.candidate ? 10 : current ? 9 : 1} pending={pending} />
      )}
      {print ? null : (
        <p className="meta">
          <button type="button" className="ghost" onClick={() => setMentorOpen((open) => !open)}>
            {mentorOpen ? "Ocultar assistente" : "Mostrar assistente"}
          </button>
        </p>
      )}
    </div>
  );
}
