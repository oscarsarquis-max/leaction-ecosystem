import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import type { LabelingDossier } from "../api/types";
import { ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { LabelingMentor } from "../components/LabelingMentor";
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

export function LabelingDossierPage() {
  const { dossierId = "" } = useParams();
  const location = useLocation();
  const { api, hasPermission } = useOrganization();
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; data: LabelingDossier; row: number } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const [left, setLeft] = useState("");
  const [right, setRight] = useState("");
  const [compare, setCompare] = useState<string | null>(null);
  const [mentorOpen, setMentorOpen] = useState(true);

  function load() {
    setState({ kind: "carregando" });
    api
      .getLabelingDossier(dossierId)
      .then((envelope) => setState({ kind: "ok", data: envelope.data, row: envelope.row_version ?? 1 }))
      .catch((error) => setState({ kind: "erro", error }));
  }

  useEffect(() => {
    setState({ kind: "carregando" });
    api
      .getLabelingDossier(dossierId)
      .then((envelope) => setState({ kind: "ok", data: envelope.data, row: envelope.row_version ?? 1 }))
      .catch((error) => setState({ kind: "erro", error }));
  }, [api, dossierId]);

  const pending = useMemo(() => {
    if (state.kind !== "ok") return [];
    return (state.data.current?.mandatory ?? [])
      .filter((item) => item.status === "pending")
      .map((item) => item.label);
  }, [state]);

  async function command(path: string, body?: unknown) {
    if (state.kind !== "ok") return;
    try {
      await api.catalogCommand(path, {
        body,
        idempotencyKey: crypto.randomUUID(),
        ifMatch: state.row,
      });
      load();
    } catch (error) {
      setState({ kind: "erro", error });
    }
  }

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  const dossier = state.data;
  const current = dossier.current;
  const print = location.pathname.endsWith("/imprimir");

  return (
    <div className={print ? "sheet labeling-print" : "stage"}>
      <div>
        <h1>Dossiê de rotulagem</h1>
        <p className="lede">
          <StatusBadge tone="atencao" label="proposta técnica para revisão" /> {dossier.disclaimer}
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

        <section>
          <h2>Perfil de aplicabilidade</h2>
          <p>Completude: {String(dossier.profile?.completeness ?? "incomplete")}. Categoria exige confirmação humana.</p>
          {hasPermission("labeling.candidate.edit") && !print ? (
            <form
              className="grid-2"
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                const payload: Record<string, unknown> = { category_confirmed: data.get("category_confirmed") === "on" };
                for (const [name] of PROFILE_FIELDS) {
                  const value = data.get(name);
                  payload[name] = value === "true" ? true : value === "false" ? false : value || null;
                  if (["packed_food","packed_away_from_consumer","packed_at_point_of_sale","packed_on_request","same_establishment","food_service","ready_to_eat"].includes(name)) {
                    payload[name] = value === "true" ? true : value === "false" ? false : null;
                  }
                  if (name === "servings_per_package") payload[name] = value ? Number(value) : null;
                }
                void command(`/labeling/dossiers/${dossier.id}/profile`, payload);
              }}
            >
              {PROFILE_FIELDS.map(([name, label]) => (
                <label key={name}>
                  {label}
                  <input name={name} defaultValue={String(dossier.profile?.[name] ?? "")} />
                </label>
              ))}
              <label>
                <input type="checkbox" name="category_confirmed" defaultChecked={Boolean(dossier.profile?.category_confirmed)} />
                Categoria confirmada por pessoa autorizada
              </label>
              <button type="submit" className="primary">
                Gravar perfil
              </button>
            </form>
          ) : null}
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
              {(current?.nutrition?.lines ?? []).map((line) => (
                <tr key={line.nutrient_code}>
                  <td>{line.nutrient_code}</td>
                  <td>{line.technical_per_100g ?? "ausente"}</td>
                  <td>{line.presented ?? "sem evidência"}</td>
                  <td>{line.declared_per_serving ?? "—"}</td>
                  <td>{line.daily_value_percent ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>Porção: {current?.nutrition?.portion_g ?? "não confirmada"} g · {current?.nutrition?.household_measure ?? "medida caseira pendente"}</p>
        </section>

        <section>
          <h2>Lupa candidata</h2>
          <p>{current?.front_of_pack?.disclaimer}</p>
          <div className="lupa" aria-label="Representação candidata da lupa">
            <strong>ALTO EM</strong>
            <p>{current?.front_of_pack?.nutrients_high.join(", ") || "conclusão incompleta"}</p>
          </div>
          <p>
            Açúcares: {current?.front_of_pack?.added_sugars_result}. Saturada: {current?.front_of_pack?.saturated_fat_result}.
            Sódio: {current?.front_of_pack?.sodium_result}.
          </p>
        </section>

        <section>
          <h2>Ingredientes e advertências</h2>
          <ol>
            {(current?.ingredients ?? []).map((item) => (
              <li key={item.sequence}>
                {item.display_name}
                {item.compound ? ` (composto: ${item.components.map((part) => part.name).join(", ") || item.gap})` : ""}
              </li>
            ))}
          </ol>
          <ul>
            {(current?.warnings ?? []).map((item) => (
              <li key={item.code}>
                {item.statement} · {item.result}
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h2>Informações obrigatórias</h2>
          {hasPermission("labeling.candidate.edit") && !print ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                void command(`/labeling/dossiers/${dossier.id}/mandatory`, {
                  items: (current?.mandatory ?? []).map((item) => ({
                    code: item.code,
                    value: String(data.get(item.code) || "") || null,
                    claim: data.get(`${item.code}_claim`) === "on",
                  })),
                });
              }}
            >
              {(current?.mandatory ?? []).map((item) => (
                <label key={item.code}>
                  {item.label}
                  <input name={item.code} defaultValue={item.value ?? ""} />
                  <span>
                    <input type="checkbox" name={`${item.code}_claim`} /> alegação — exige revisão específica
                  </span>
                </label>
              ))}
              <button type="submit">Gravar pendências</button>
            </form>
          ) : (
            <ul>
              {(current?.mandatory ?? []).map((item) => (
                <li key={item.code}>
                  {item.label}: {item.value || "pendente"}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h2>Achados</h2>
          <ul>
            {(current?.findings ?? []).map((item) => (
              <li key={item.rule_code}>
                <strong>{item.result}</strong> · {item.rule_code}: {item.explanation} ({item.source_locator})
              </li>
            ))}
          </ul>
        </section>

        {print ? (
          <p className="meta">
            Versão {current?.version.version_number} · {current?.version.content_hash} · não é rótulo aprovado
          </p>
        ) : (
          <>
            <div className="toolbar">
              {hasPermission("labeling.evaluate") ? (
                <button type="button" className="primary" onClick={() => void command(`/labeling/dossiers/${dossier.id}/evaluate`)}>
                  Executar avaliação
                </button>
              ) : null}
              {hasPermission("labeling.review") ? (
                <button type="button" onClick={() => void command(`/labeling/dossiers/${dossier.id}/review`, { decision: "accepted" })}>
                  Registrar revisão humana
                </button>
              ) : null}
              {hasPermission("labeling.invalidate") ? (
                <button type="button" onClick={() => void command(`/labeling/dossiers/${dossier.id}/invalidate`, { reason: "invalidação auditável" })}>
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
                      {item.version_number}
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
                      {item.version_number}
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
                    .catch((error) => setState({ kind: "erro", error }));
                }}
              >
                Comparar
              </button>
              {compare ? <pre>{compare}</pre> : null}
            </section>
          </>
        )}
      </div>
      {print || !mentorOpen ? null : (
        <LabelingMentor
          step={pending.length ? 7 : current?.candidate ? 10 : current ? 9 : 1}
          pending={pending}
        />
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
